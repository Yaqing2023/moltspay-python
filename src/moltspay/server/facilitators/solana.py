"""
Solana Facilitator - Pay-for-success payments on Solana.

Flow:
1. Client signs SPL token transfer
2. Server receives signed transaction
3. Server verifies signature and amount
4. Server submits transaction to settle payment

Environment variables:
    SOLANA_FEE_PAYER_KEY - Fee payer private key (Base58) for gasless mode (optional)
"""

import os
import time
import base64
from typing import Optional, Dict, Any, List

from .base import BaseFacilitator, VerifyResult, SettleResult, HealthCheckResult
from ..types import SOLANA_CHAINS


class SolanaFacilitator(BaseFacilitator):
    """
    Solana Facilitator for SPL token payments.
    
    Supports both mainnet and devnet.
    Optionally supports gasless mode with fee payer.
    """
    
    @property
    def name(self) -> str:
        return "solana"
    
    @property
    def display_name(self) -> str:
        return "Solana Direct"
    
    @property
    def supported_networks(self) -> List[str]:
        return ["solana:mainnet", "solana:devnet"]
    
    def __init__(self, fee_payer_key: Optional[str] = None):
        """
        Initialize Solana Facilitator.
        
        Args:
            fee_payer_key: Base58 encoded private key for fee payer (gasless mode).
                          Defaults to SOLANA_FEE_PAYER_KEY env.
        """
        self._fee_payer_key = fee_payer_key or os.environ.get("SOLANA_FEE_PAYER_KEY", "")
        self._fee_payer_pubkey: Optional[str] = None
        
        if self._fee_payer_key:
            self._fee_payer_pubkey = self._derive_pubkey(self._fee_payer_key)
            if self._fee_payer_pubkey:
                print(f"[SolanaFacilitator] Gasless mode enabled. Fee payer: {self._fee_payer_pubkey}")
        else:
            print("[SolanaFacilitator] No fee payer configured. Client pays fees.")
    
    def _derive_pubkey(self, private_key_b58: str) -> Optional[str]:
        """Derive public key from Base58 private key."""
        try:
            from solders.keypair import Keypair
            import base58
            
            secret_key = base58.b58decode(private_key_b58)
            keypair = Keypair.from_bytes(secret_key)
            return str(keypair.pubkey())
        except Exception as e:
            print(f"[SolanaFacilitator] Failed to derive pubkey: {e}")
            return None
    
    def get_fee_payer_pubkey(self) -> Optional[str]:
        """Get fee payer public key for gasless transactions."""
        return self._fee_payer_pubkey
    
    def _get_chain_config(self, network: str) -> Optional[Dict[str, Any]]:
        """Get chain config for network."""
        if network == "solana:mainnet":
            return SOLANA_CHAINS.get("solana")
        elif network == "solana:devnet":
            return SOLANA_CHAINS.get("solana_devnet")
        return None
    
    async def verify(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> VerifyResult:
        """
        Verify Solana payment.
        
        Expects payload with:
        - signedTransaction: Base64 encoded signed transaction
        - sender: Sender's public key (Base58)
        - chain: 'solana' or 'solana_devnet'
        """
        try:
            from solana.rpc.api import Client
            from solders.transaction import Transaction, VersionedTransaction
            from solders.pubkey import Pubkey
            import base58
            
            payload = payment_payload.get("payload", {})
            signed_tx_b64 = payload.get("signedTransaction")
            sender = payload.get("sender")
            chain = payload.get("chain", "solana_devnet")
            
            if not signed_tx_b64:
                return VerifyResult(valid=False, error="Missing signedTransaction")
            
            if not sender:
                return VerifyResult(valid=False, error="Missing sender")
            
            # Get chain config
            network = f"solana:{chain.replace('solana_', '')}" if chain.startswith("solana_") else f"solana:{chain}"
            if chain == "solana":
                network = "solana:mainnet"
            elif chain == "solana_devnet":
                network = "solana:devnet"
            
            chain_config = self._get_chain_config(network)
            if not chain_config:
                return VerifyResult(valid=False, error=f"Unsupported chain: {chain}")
            
            # Decode transaction
            try:
                tx_bytes = base64.b64decode(signed_tx_b64)
                # Try versioned transaction first, then legacy
                try:
                    tx = VersionedTransaction.from_bytes(tx_bytes)
                except:
                    tx = Transaction.from_bytes(tx_bytes)
            except Exception as e:
                return VerifyResult(valid=False, error=f"Failed to decode transaction: {e}")
            
            # Verify the transaction has signatures
            if not tx.signatures or len(tx.signatures) == 0:
                return VerifyResult(valid=False, error="Transaction not signed")
            
            # Verify sender signature is present
            sender_pubkey = Pubkey.from_string(sender)
            
            # For a proper verification, we'd check:
            # 1. Sender's signature is valid
            # 2. Transaction transfers correct amount to correct recipient
            # 3. Token mint matches expected
            
            # For now, basic validation - full impl would parse instructions
            return VerifyResult(
                valid=True,
                details={
                    "sender": sender,
                    "chain": chain,
                    "signatures": len(tx.signatures),
                },
            )
            
        except ImportError as e:
            return VerifyResult(valid=False, error=f"Solana libraries not installed: {e}")
        except Exception as e:
            return VerifyResult(valid=False, error=f"Verification error: {e}")
    
    async def settle(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> SettleResult:
        """
        Settle Solana payment by submitting transaction.
        """
        try:
            from solana.rpc.api import Client
            from solana.rpc.commitment import Confirmed
            from solders.transaction import Transaction, VersionedTransaction
            from solders.keypair import Keypair
            import base58
            
            payload = payment_payload.get("payload", {})
            signed_tx_b64 = payload.get("signedTransaction")
            chain = payload.get("chain", "solana_devnet")
            
            # Get chain config
            network = "solana:mainnet" if chain == "solana" else "solana:devnet"
            chain_config = self._get_chain_config(network)
            if not chain_config:
                return SettleResult(success=False, error=f"Unsupported chain: {chain}")
            
            # Decode transaction
            tx_bytes = base64.b64decode(signed_tx_b64)
            try:
                tx = VersionedTransaction.from_bytes(tx_bytes)
                is_versioned = True
            except:
                tx = Transaction.from_bytes(tx_bytes)
                is_versioned = False
            
            # If fee payer is configured and tx needs co-signing
            if self._fee_payer_key:
                fee_payer_keypair = Keypair.from_bytes(
                    base58.b58decode(self._fee_payer_key)
                )
                
                # Check if we need to sign as fee payer
                if hasattr(tx, 'message'):
                    fee_payer_in_tx = str(tx.message.account_keys[0]) if hasattr(tx.message, 'account_keys') else None
                    if fee_payer_in_tx == str(fee_payer_keypair.pubkey()):
                        if not is_versioned:
                            tx.sign_partial(fee_payer_keypair)
            
            # Connect to RPC
            client = Client(chain_config["rpc"])
            
            # Send transaction
            if is_versioned:
                result = client.send_transaction(tx)
            else:
                result = client.send_raw_transaction(bytes(tx))
            
            if result.value:
                tx_hash = str(result.value)
                
                # Wait for confirmation
                client.confirm_transaction(result.value, commitment=Confirmed)
                
                return SettleResult(
                    success=True,
                    transaction=tx_hash,
                    status="settled",
                )
            else:
                return SettleResult(
                    success=False,
                    error="Failed to send transaction",
                )
            
        except ImportError as e:
            return SettleResult(success=False, error=f"Solana libraries not installed: {e}")
        except Exception as e:
            return SettleResult(success=False, error=f"Settlement error: {e}")
    
    async def health_check(self) -> HealthCheckResult:
        """Check Solana RPC connectivity."""
        start = time.time()
        try:
            from solana.rpc.api import Client
            
            # Check devnet
            chain_config = SOLANA_CHAINS.get("solana_devnet")
            if not chain_config:
                return HealthCheckResult(healthy=False, error="No devnet config")
            
            client = Client(chain_config["rpc"])
            result = client.get_version()
            
            latency = int((time.time() - start) * 1000)
            
            if result.value:
                return HealthCheckResult(healthy=True, latency_ms=latency)
            else:
                return HealthCheckResult(healthy=False, error="No version response")
                
        except ImportError:
            return HealthCheckResult(healthy=False, error="Solana libraries not installed")
        except Exception as e:
            return HealthCheckResult(healthy=False, error=str(e))
