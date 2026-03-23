"""
BNB Chain Facilitator - Pay-for-success payments on BNB Smart Chain.

Flow:
1. Client pre-approves server wallet (one-time)
2. Client signs EIP-712 intent (no gas, just signature)
3. Server verifies intent signature
4. Server executes service
5. Success → Server calls transferFrom (server pays gas)
6. Failure → No transfer, client keeps money

Environment variables:
    BNB_SERVER_PRIVATE_KEY - Server wallet private key for executing transferFrom
"""

import os
import time
from typing import Optional, Dict, Any, List

from .base import BaseFacilitator, VerifyResult, SettleResult, HealthCheckResult
from ..types import TOKEN_ADDRESSES

# EIP-712 Domain
EIP712_DOMAIN_NAME = "MoltsPay"
EIP712_DOMAIN_VERSION = "1"

# Chain configs
BNB_CHAINS = {
    56: {  # BNB Mainnet
        "name": "BNB Smart Chain",
        "rpc": "https://bsc-dataseed.binance.org",
        "network": "eip155:56",
    },
    97: {  # BNB Testnet
        "name": "BNB Testnet",
        "rpc": "https://data-seed-prebsc-1-s1.binance.org:8545",
        "network": "eip155:97",
    },
}


class BNBFacilitator(BaseFacilitator):
    """
    BNB Chain Facilitator for pay-for-success payments.
    
    Handles EIP-712 signed intents and executes transferFrom on success.
    Server wallet (relayer) must have BNB for gas.
    """
    
    @property
    def name(self) -> str:
        return "bnb"
    
    @property
    def display_name(self) -> str:
        return "BNB Smart Chain"
    
    @property
    def supported_networks(self) -> List[str]:
        return ["eip155:56", "eip155:97"]
    
    def __init__(self, server_private_key: Optional[str] = None):
        """
        Initialize BNB Facilitator.
        
        Args:
            server_private_key: Private key for relayer wallet. 
                               Defaults to BNB_SERVER_PRIVATE_KEY env.
        """
        self.server_private_key = server_private_key or os.environ.get("BNB_SERVER_PRIVATE_KEY", "")
        self._spender_address: Optional[str] = None
        
        if self.server_private_key:
            self._spender_address = self._derive_address(self.server_private_key)
            print(f"[BNBFacilitator] Relayer wallet: {self._spender_address}")
        else:
            print("[BNBFacilitator] WARNING: No BNB_SERVER_PRIVATE_KEY configured")
    
    def _derive_address(self, private_key: str) -> str:
        """Derive address from private key."""
        try:
            from eth_account import Account
            key = private_key if private_key.startswith("0x") else f"0x{private_key}"
            account = Account.from_key(key)
            return account.address
        except Exception as e:
            print(f"[BNBFacilitator] Failed to derive address: {e}")
            return ""
    
    def get_spender_address(self) -> Optional[str]:
        """Get the spender address for approval."""
        return self._spender_address
    
    async def verify(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> VerifyResult:
        """
        Verify BNB payment intent signature.
        
        The payload should contain an EIP-712 signed intent with:
        - from, to, amount, token, service, nonce, deadline, signature
        """
        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data
            
            # Extract intent from payload
            intent = payment_payload.get("payload", {}).get("intent")
            if not intent:
                return VerifyResult(valid=False, error="Missing intent in payment payload")
            
            chain_id = payment_payload.get("payload", {}).get("chainId")
            if not chain_id or chain_id not in BNB_CHAINS:
                return VerifyResult(valid=False, error=f"Unsupported chainId: {chain_id}")
            
            # Check deadline (in milliseconds)
            deadline = intent.get("deadline", 0)
            if deadline < int(time.time() * 1000):
                return VerifyResult(valid=False, error="Intent expired")
            
            # Verify signature
            typed_data = self._build_typed_data(intent, chain_id)
            
            try:
                signable = encode_typed_data(full_message=typed_data)
                recovered = Account.recover_message(signable, signature=intent["signature"])
            except Exception as e:
                return VerifyResult(valid=False, error=f"Signature recovery failed: {e}")
            
            if recovered.lower() != intent["from"].lower():
                return VerifyResult(valid=False, error="Invalid signature")
            
            # Verify recipient matches
            pay_to = requirements.get("payTo", "")
            if intent["to"].lower() != pay_to.lower():
                return VerifyResult(valid=False, error=f"Recipient mismatch: {intent['to']} != {pay_to}")
            
            # Verify amount
            required_amount = int(requirements.get("amount", 0))
            intent_amount = int(intent.get("amount", 0))
            if intent_amount < required_amount:
                return VerifyResult(valid=False, error=f"Insufficient amount: {intent_amount} < {required_amount}")
            
            # Verify token
            network = BNB_CHAINS[chain_id]["network"]
            expected_token = requirements.get("asset", "").lower()
            intent_token = intent.get("token", "").lower()
            if intent_token != expected_token:
                return VerifyResult(valid=False, error=f"Token mismatch: {intent_token} != {expected_token}")
            
            # Check allowance
            allowance_ok = await self._check_allowance(
                intent["from"],
                intent["token"],
                intent_amount,
                chain_id,
            )
            if not allowance_ok:
                return VerifyResult(valid=False, error="Insufficient allowance. Client needs to approve spender.")
            
            return VerifyResult(valid=True, details={"intent": intent, "chainId": chain_id})
            
        except ImportError:
            return VerifyResult(valid=False, error="eth_account not installed")
        except Exception as e:
            return VerifyResult(valid=False, error=f"Verification error: {e}")
    
    async def settle(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> SettleResult:
        """
        Settle BNB payment by executing transferFrom.
        """
        if not self.server_private_key:
            return SettleResult(success=False, error="Server wallet not configured (BNB_SERVER_PRIVATE_KEY)")
        
        try:
            from web3 import Web3
            from eth_account import Account
            
            # First verify
            verify_result = await self.verify(payment_payload, requirements)
            if not verify_result.valid:
                return SettleResult(success=False, error=verify_result.error)
            
            intent = payment_payload["payload"]["intent"]
            chain_id = payment_payload["payload"]["chainId"]
            chain_config = BNB_CHAINS[chain_id]
            
            # Connect to RPC
            w3 = Web3(Web3.HTTPProvider(chain_config["rpc"]))
            
            # Prepare account
            key = self.server_private_key if self.server_private_key.startswith("0x") else f"0x{self.server_private_key}"
            account = Account.from_key(key)
            
            # ERC20 transferFrom ABI
            transfer_from_abi = [{
                "name": "transferFrom",
                "type": "function",
                "inputs": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                ],
                "outputs": [{"type": "bool"}],
            }]
            
            token = w3.eth.contract(
                address=Web3.to_checksum_address(intent["token"]),
                abi=transfer_from_abi,
            )
            
            # Build transaction
            nonce = w3.eth.get_transaction_count(account.address)
            
            tx = token.functions.transferFrom(
                Web3.to_checksum_address(intent["from"]),
                Web3.to_checksum_address(intent["to"]),
                int(intent["amount"]),
            ).build_transaction({
                "chainId": chain_id,
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce,
            })
            
            # Sign and send
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt["status"] != 1:
                return SettleResult(success=False, error="Transaction failed on-chain")
            
            return SettleResult(
                success=True,
                transaction=tx_hash.hex(),
                status="settled",
            )
            
        except ImportError:
            return SettleResult(success=False, error="web3 not installed")
        except Exception as e:
            return SettleResult(success=False, error=f"Settlement error: {e}")
    
    async def health_check(self) -> HealthCheckResult:
        """Check BNB RPC connectivity."""
        import time
        start = time.time()
        try:
            from web3 import Web3
            # Check testnet RPC
            w3 = Web3(Web3.HTTPProvider(BNB_CHAINS[97]["rpc"]))
            chain_id = w3.eth.chain_id
            latency = int((time.time() - start) * 1000)
            
            if chain_id != 97:
                return HealthCheckResult(healthy=False, error=f"Wrong chainId: {chain_id}")
            
            return HealthCheckResult(healthy=True, latency_ms=latency)
        except Exception as e:
            return HealthCheckResult(healthy=False, error=str(e))
    
    def _build_typed_data(self, intent: Dict[str, Any], chain_id: int) -> Dict[str, Any]:
        """Build EIP-712 typed data for signature verification."""
        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
                "PaymentIntent": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "token", "type": "address"},
                    {"name": "service", "type": "string"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                ],
            },
            "primaryType": "PaymentIntent",
            "domain": {
                "name": EIP712_DOMAIN_NAME,
                "version": EIP712_DOMAIN_VERSION,
                "chainId": chain_id,
            },
            "message": {
                "from": intent["from"],
                "to": intent["to"],
                "amount": int(intent["amount"]),
                "token": intent["token"],
                "service": intent["service"],
                "nonce": int(intent["nonce"]),
                "deadline": int(intent["deadline"]),
            },
        }
    
    async def _check_allowance(
        self,
        owner: str,
        token: str,
        amount: int,
        chain_id: int,
    ) -> bool:
        """Check if owner has approved enough allowance for spender."""
        if not self._spender_address:
            return False
        
        try:
            from web3 import Web3
            
            chain_config = BNB_CHAINS[chain_id]
            w3 = Web3(Web3.HTTPProvider(chain_config["rpc"]))
            
            allowance_abi = [{
                "name": "allowance",
                "type": "function",
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "spender", "type": "address"},
                ],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
            }]
            
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(token),
                abi=allowance_abi,
            )
            
            allowance = contract.functions.allowance(
                Web3.to_checksum_address(owner),
                Web3.to_checksum_address(self._spender_address),
            ).call()
            
            return allowance >= amount
            
        except Exception as e:
            print(f"[BNBFacilitator] Allowance check failed: {e}")
            return False
