"""
Tempo Testnet Facilitator - Direct on-chain verification for Tempo Moderato.

Supports both x402 and MPP (Machine Payments Protocol).

MPP Flow:
1. Server returns 402 with WWW-Authenticate: Payment header
2. Client pays on-chain
3. Client sends Authorization: Payment <credential> header
4. Server verifies tx on-chain and executes service

No CDP or third-party facilitator needed - direct chain verification.
"""

import os
import time
import base64
import json
import secrets
from typing import Optional, Dict, Any, List

from .base import BaseFacilitator, VerifyResult, SettleResult, HealthCheckResult
from ..types import TOKEN_ADDRESSES

# Tempo Moderato config
TEMPO_CHAIN_ID = 42431
TEMPO_RPC = "https://rpc.moderato.tempo.xyz"
TEMPO_NETWORK = "eip155:42431"

# Transfer event signature
TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


class TempoFacilitator(BaseFacilitator):
    """
    Tempo Testnet Facilitator.
    
    Verifies TIP-20 token transfers directly on Tempo Moderato (chainId 42431).
    Supports both x402 and MPP protocols.
    """
    
    @property
    def name(self) -> str:
        return "tempo"
    
    @property
    def display_name(self) -> str:
        return "Tempo Testnet"
    
    @property
    def supported_networks(self) -> List[str]:
        return [TEMPO_NETWORK]
    
    def __init__(self):
        """Initialize Tempo Facilitator."""
        self.rpc_url = TEMPO_RPC
        self.chain_id = TEMPO_CHAIN_ID
    
    async def verify(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> VerifyResult:
        """
        Verify Tempo payment by checking transaction on-chain.
        
        Expects payload with txHash.
        """
        try:
            # Extract txHash from payload
            payload = payment_payload.get("payload", {})
            tx_hash = payload.get("txHash")
            
            if not tx_hash:
                return VerifyResult(valid=False, error="Missing txHash in payment payload")
            
            # Get transaction receipt
            receipt = await self._get_transaction_receipt(tx_hash)
            
            if not receipt:
                return VerifyResult(valid=False, error="Transaction not found")
            
            if receipt.get("status") != "0x1":
                return VerifyResult(valid=False, error="Transaction failed")
            
            # Find Transfer event
            transfer_log = None
            for log in receipt.get("logs", []):
                topics = log.get("topics", [])
                if topics and topics[0] == TRANSFER_EVENT_TOPIC:
                    transfer_log = log
                    break
            
            if not transfer_log:
                return VerifyResult(valid=False, error="No Transfer event found")
            
            # Parse Transfer event
            # Transfer(address indexed from, address indexed to, uint256 value)
            topics = transfer_log.get("topics", [])
            data = transfer_log.get("data", "0x")
            
            if len(topics) < 3:
                return VerifyResult(valid=False, error="Invalid Transfer event")
            
            from_addr = "0x" + topics[1][-40:]
            to_addr = "0x" + topics[2][-40:]
            amount = int(data, 16) if data != "0x" else 0
            
            # Verify recipient
            pay_to = requirements.get("payTo", "").lower()
            if to_addr.lower() != pay_to:
                return VerifyResult(valid=False, error=f"Recipient mismatch: {to_addr} != {pay_to}")
            
            # Verify amount
            required_amount = int(requirements.get("amount", 0))
            if amount < required_amount:
                return VerifyResult(valid=False, error=f"Insufficient amount: {amount} < {required_amount}")
            
            # Verify token
            token_addr = transfer_log.get("address", "").lower()
            expected_token = requirements.get("asset", "").lower()
            if token_addr != expected_token:
                return VerifyResult(valid=False, error=f"Token mismatch: {token_addr} != {expected_token}")
            
            return VerifyResult(
                valid=True,
                details={
                    "txHash": tx_hash,
                    "from": from_addr,
                    "to": to_addr,
                    "amount": amount,
                    "token": token_addr,
                },
            )
            
        except Exception as e:
            return VerifyResult(valid=False, error=f"Verification error: {e}")
    
    async def settle(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> SettleResult:
        """
        Settle Tempo payment.
        
        For Tempo, the payment is already on-chain, so settle just verifies again.
        """
        verify_result = await self.verify(payment_payload, requirements)
        
        if not verify_result.valid:
            return SettleResult(success=False, error=verify_result.error)
        
        tx_hash = payment_payload.get("payload", {}).get("txHash", "")
        
        return SettleResult(
            success=True,
            transaction=tx_hash,
            status="settled",
        )
    
    async def health_check(self) -> HealthCheckResult:
        """Check Tempo RPC connectivity."""
        start = time.time()
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_chainId",
                        "params": [],
                        "id": 1,
                    },
                    timeout=5.0,
                )
                
                data = response.json()
                chain_id = int(data.get("result", "0x0"), 16)
                latency = int((time.time() - start) * 1000)
                
                if chain_id != self.chain_id:
                    return HealthCheckResult(healthy=False, error=f"Wrong chainId: {chain_id}")
                
                return HealthCheckResult(healthy=True, latency_ms=latency)
                
        except Exception as e:
            return HealthCheckResult(healthy=False, error=str(e))
    
    async def _get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction receipt from Tempo RPC."""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_getTransactionReceipt",
                        "params": [tx_hash],
                        "id": 1,
                    },
                    timeout=10.0,
                )
                
                data = response.json()
                return data.get("result")
                
        except Exception as e:
            print(f"[TempoFacilitator] Failed to get receipt: {e}")
            return None
    
    # ========== MPP Protocol Support ==========
    
    def generate_mpp_challenge(
        self,
        service_id: str,
        service_name: str,
        price: float,
        wallet: str,
        provider_name: str,
    ) -> Dict[str, str]:
        """
        Generate MPP WWW-Authenticate challenge.
        
        Returns dict with 'header' (the full WWW-Authenticate value)
        and 'challenge_id' for tracking.
        """
        challenge_id = secrets.token_urlsafe(24)
        amount_units = str(int(price * 1e6))  # USDC has 6 decimals
        token_address = TOKEN_ADDRESSES.get(TEMPO_NETWORK, {}).get("USDC", "")
        
        mpp_request = {
            "amount": amount_units,
            "currency": token_address,
            "methodDetails": {
                "chainId": self.chain_id,
                "feePayer": True,
            },
            "recipient": wallet,
        }
        
        request_encoded = base64.b64encode(
            json.dumps(mpp_request).encode()
        ).decode()
        
        expires_at = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(time.time() + 300)  # 5 minutes
        )
        
        header = (
            f'Payment id="{challenge_id}", '
            f'realm="{provider_name}", '
            f'method="tempo", '
            f'intent="charge", '
            f'request="{request_encoded}", '
            f'description="{service_name}", '
            f'expires="{expires_at}"'
        )
        
        return {
            "header": header,
            "challenge_id": challenge_id,
        }
    
    def parse_mpp_credential(self, auth_header: str) -> Optional[Dict[str, Any]]:
        """
        Parse MPP Authorization header.
        
        Format: "Payment <base64url-encoded-credential>"
        
        Returns parsed credential or None if invalid.
        """
        if not auth_header.lower().startswith("payment "):
            return None
        
        try:
            credential_b64 = auth_header[8:].strip()
            # Handle base64url encoding
            credential_b64 = credential_b64.replace("-", "+").replace("_", "/")
            # Add padding if needed
            padding = 4 - len(credential_b64) % 4
            if padding != 4:
                credential_b64 += "=" * padding
            
            decoded = base64.b64decode(credential_b64).decode("utf-8")
            return json.loads(decoded)
            
        except Exception as e:
            print(f"[TempoFacilitator] Failed to parse MPP credential: {e}")
            return None
    
    def extract_tx_hash_from_credential(self, credential: Dict[str, Any]) -> Optional[str]:
        """Extract txHash from MPP credential."""
        payload = credential.get("payload", {})
        
        if payload.get("type") == "hash":
            return payload.get("hash")
        
        # For 'transaction' type, we'd need to submit the tx
        # For now, only support 'hash' (push mode)
        return None
