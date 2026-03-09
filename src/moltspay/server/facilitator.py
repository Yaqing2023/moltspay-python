"""
CDP Facilitator - Coinbase Developer Platform x402 payment verification/settlement.

Environment variables (from ~/.moltspay/.env):
    USE_MAINNET=true          - Use Base mainnet (requires CDP keys)
    CDP_API_KEY_ID=xxx        - Coinbase Developer Platform API key ID
    CDP_API_KEY_SECRET=xxx    - CDP API key secret
"""

import os
import time
import hmac
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import httpx

from .types import X402PaymentPayload, X402PaymentRequirements, VerifyResult, SettleResult, X402_VERSION


# CDP Facilitator URLs
CDP_MAINNET_URL = "https://api.cdp.coinbase.com/platform/v2/x402"
CDP_TESTNET_URL = "https://www.x402.org/facilitator"


def load_env_file() -> None:
    """Load environment variables from .env files."""
    env_paths = [
        Path.cwd() / ".env",
        Path.home() / ".moltspay" / ".env",
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            try:
                content = env_path.read_text()
                for line in content.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    # Don't override existing env vars
                    if key not in os.environ:
                        os.environ[key] = value
                print(f"[MoltsPay] Loaded config from {env_path}")
                break
            except Exception:
                pass


class CDPFacilitator:
    """
    Coinbase Developer Platform x402 Facilitator.
    
    Handles payment verification and settlement via Coinbase's x402 facilitator.
    Supports both mainnet (Base) and testnet (Base Sepolia).
    """
    
    name = "cdp"
    display_name = "Coinbase CDP"
    
    def __init__(
        self,
        use_mainnet: Optional[bool] = None,
        api_key_id: Optional[str] = None,
        api_key_secret: Optional[str] = None,
    ):
        """
        Initialize CDP Facilitator.
        
        Args:
            use_mainnet: Use mainnet (True) or testnet (False). Defaults to USE_MAINNET env.
            api_key_id: CDP API Key ID. Defaults to CDP_API_KEY_ID env.
            api_key_secret: CDP API Key Secret. Defaults to CDP_API_KEY_SECRET env.
        """
        # Load env files first
        load_env_file()
        
        # Determine mainnet vs testnet
        if use_mainnet is None:
            use_mainnet = os.environ.get("USE_MAINNET", "").lower() == "true"
        self.use_mainnet = use_mainnet
        
        # Get credentials
        self.api_key_id = api_key_id or os.environ.get("CDP_API_KEY_ID")
        self.api_key_secret = api_key_secret or os.environ.get("CDP_API_KEY_SECRET")
        
        # Set endpoint
        self.endpoint = CDP_MAINNET_URL if use_mainnet else CDP_TESTNET_URL
        
        # Supported networks
        self.supported_networks = (
            ["eip155:8453"] if use_mainnet 
            else ["eip155:8453", "eip155:84532"]
        )
        
        # HTTP client
        self._client = httpx.Client(timeout=30.0)
        
        # Warn if mainnet without credentials
        if self.use_mainnet and (not self.api_key_id or not self.api_key_secret):
            print("[CDPFacilitator] WARNING: Mainnet mode but missing CDP credentials!")
            print("[CDPFacilitator] Set CDP_API_KEY_ID and CDP_API_KEY_SECRET in ~/.moltspay/.env")
    
    def close(self):
        """Close HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def _get_auth_headers(
        self,
        method: str,
        url_path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Generate authentication headers for CDP API requests.
        
        CDP uses JWT-style authentication with API keys.
        """
        if not self.use_mainnet:
            # Testnet (x402.org) doesn't require auth
            return {}
        
        if not self.api_key_id or not self.api_key_secret:
            raise ValueError("CDP credentials required for mainnet")
        
        # Generate timestamp
        timestamp = str(int(time.time()))
        
        # Build message to sign
        body_str = json.dumps(body, separators=(",", ":")) if body else ""
        message = f"{timestamp}{method.upper()}{url_path}{body_str}"
        
        # Sign with HMAC-SHA256
        signature = hmac.new(
            self.api_key_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return {
            "CB-ACCESS-KEY": self.api_key_id,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
        }
    
    def verify(
        self,
        payment_payload: X402PaymentPayload,
        requirements: X402PaymentRequirements,
    ) -> VerifyResult:
        """
        Verify payment signature with CDP facilitator.
        
        Args:
            payment_payload: The x402 payment payload from client
            requirements: The payment requirements for this service
            
        Returns:
            VerifyResult with verification status
        """
        try:
            request_body = {
                "x402Version": X402_VERSION,
                "paymentPayload": {
                    "x402Version": payment_payload.x402Version,
                    "payload": payment_payload.payload,
                    "accepted": payment_payload.accepted,
                    "resource": payment_payload.resource,
                },
                "paymentRequirements": {
                    "scheme": requirements.scheme,
                    "network": requirements.network,
                    "asset": requirements.asset,
                    "amount": requirements.amount,
                    "payTo": requirements.payTo,
                    "maxTimeoutSeconds": requirements.maxTimeoutSeconds,
                    "extra": requirements.extra,
                },
            }
            
            headers = {"Content-Type": "application/json"}
            
            if self.use_mainnet:
                auth_headers = self._get_auth_headers(
                    "POST",
                    "/platform/v2/x402/verify",
                    request_body,
                )
                headers.update(auth_headers)
            
            response = self._client.post(
                f"{self.endpoint}/verify",
                headers=headers,
                json=request_body,
            )
            
            result = response.json()
            
            if not response.is_success or not result.get("isValid"):
                return VerifyResult(
                    valid=False,
                    error=result.get("invalidReason") or result.get("error") or "Verification failed",
                    details=result,
                    facilitator=self.name,
                )
            
            return VerifyResult(
                valid=True,
                details=result,
                facilitator=self.name,
            )
            
        except Exception as e:
            return VerifyResult(
                valid=False,
                error=f"Facilitator error: {e}",
                facilitator=self.name,
            )
    
    def settle(
        self,
        payment_payload: X402PaymentPayload,
        requirements: X402PaymentRequirements,
    ) -> SettleResult:
        """
        Settle payment on-chain via CDP facilitator.
        
        Args:
            payment_payload: The x402 payment payload from client
            requirements: The payment requirements for this service
            
        Returns:
            SettleResult with settlement status and transaction hash
        """
        try:
            request_body = {
                "x402Version": X402_VERSION,
                "paymentPayload": {
                    "x402Version": payment_payload.x402Version,
                    "payload": payment_payload.payload,
                    "accepted": payment_payload.accepted,
                    "resource": payment_payload.resource,
                },
                "paymentRequirements": {
                    "scheme": requirements.scheme,
                    "network": requirements.network,
                    "asset": requirements.asset,
                    "amount": requirements.amount,
                    "payTo": requirements.payTo,
                    "maxTimeoutSeconds": requirements.maxTimeoutSeconds,
                    "extra": requirements.extra,
                },
            }
            
            headers = {"Content-Type": "application/json"}
            
            if self.use_mainnet:
                auth_headers = self._get_auth_headers(
                    "POST",
                    "/platform/v2/x402/settle",
                    request_body,
                )
                headers.update(auth_headers)
            
            response = self._client.post(
                f"{self.endpoint}/settle",
                headers=headers,
                json=request_body,
            )
            
            result = response.json()
            
            if not response.is_success or not result.get("success"):
                return SettleResult(
                    success=False,
                    error=result.get("error") or result.get("errorReason") or "Settlement failed",
                    facilitator=self.name,
                )
            
            return SettleResult(
                success=True,
                transaction=result.get("transaction"),
                status=result.get("status", "settled"),
                facilitator=self.name,
            )
            
        except Exception as e:
            return SettleResult(
                success=False,
                error=f"Settlement error: {e}",
                facilitator=self.name,
            )
    
    def health_check(self) -> Dict[str, Any]:
        """Check if facilitator is reachable."""
        try:
            # Simple connectivity check
            response = self._client.head(
                self.endpoint.replace("/x402", ""),
                timeout=5.0,
            )
            return {"healthy": True, "status_code": response.status_code}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def get_config_summary(self) -> str:
        """Get configuration summary for logging."""
        mode = "mainnet" if self.use_mainnet else "testnet"
        has_creds = bool(self.api_key_id and self.api_key_secret)
        return f"CDP Facilitator ({mode}, credentials: {'yes' if has_creds else 'no'})"
