"""
CDP Facilitator - Coinbase Developer Platform x402 payment verification/settlement.

Supports Base, Polygon, and testnets via Coinbase's x402 facilitator service.

Environment variables (from ~/.moltspay/.env):
    USE_MAINNET=true          - Use mainnet endpoints (requires CDP keys)
    CDP_API_KEY_ID=xxx        - Coinbase Developer Platform API key ID
    CDP_API_KEY_SECRET=xxx    - CDP API key secret
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx

# Import CDP SDK auth (optional - only needed for mainnet)
try:
    from cdp.auth import get_auth_headers, GetAuthHeadersOptions
    HAS_CDP_SDK = True
except ImportError:
    HAS_CDP_SDK = False

from .base import BaseFacilitator, VerifyResult, SettleResult, HealthCheckResult
from ..types import X402_VERSION


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
                break
            except Exception:
                pass


class CDPFacilitator(BaseFacilitator):
    """
    Coinbase Developer Platform x402 Facilitator.
    
    Handles payment verification and settlement via Coinbase's x402 facilitator.
    Supports Base, Polygon (mainnet and testnet).
    """
    
    @property
    def name(self) -> str:
        return "cdp"
    
    @property
    def display_name(self) -> str:
        return "Coinbase CDP"
    
    @property
    def supported_networks(self) -> List[str]:
        return ["eip155:8453", "eip155:137", "eip155:84532"]
    
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
        
        # HTTP client
        self._client = httpx.Client(timeout=30.0)
        
        # Warn if mainnet without credentials or SDK
        if self.use_mainnet:
            if not HAS_CDP_SDK:
                print("[CDPFacilitator] WARNING: Mainnet requires cdp-sdk. Run: pip install cdp-sdk")
            if not self.api_key_id or not self.api_key_secret:
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
        """Generate authentication headers for CDP API requests."""
        if not self.use_mainnet:
            return {}
        
        if not HAS_CDP_SDK:
            raise RuntimeError("cdp-sdk required for mainnet. Run: pip install cdp-sdk")
        
        if not self.api_key_id or not self.api_key_secret:
            raise ValueError("CDP credentials required for mainnet")
        
        headers = get_auth_headers(GetAuthHeadersOptions(
            api_key_id=self.api_key_id,
            api_key_secret=self.api_key_secret,
            request_method=method,
            request_host="api.cdp.coinbase.com",
            request_path=url_path,
            request_body=body,
        ))
        
        return headers
    
    async def verify(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> VerifyResult:
        """Verify payment signature with CDP facilitator."""
        try:
            request_body = {
                "x402Version": X402_VERSION,
                "paymentPayload": payment_payload,
                "paymentRequirements": requirements,
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
                )
            
            return VerifyResult(valid=True, details=result)
            
        except Exception as e:
            return VerifyResult(valid=False, error=f"Facilitator error: {e}")
    
    async def settle(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> SettleResult:
        """Settle payment on-chain via CDP facilitator."""
        try:
            request_body = {
                "x402Version": X402_VERSION,
                "paymentPayload": payment_payload,
                "paymentRequirements": requirements,
            }
            
            # Debug logging
            import json
            print(f"[CDP DEBUG] Endpoint: {self.endpoint}/settle")
            print(f"[CDP DEBUG] Mainnet: {self.use_mainnet}")
            print(f"[CDP DEBUG] Request body:")
            print(json.dumps(request_body, indent=2))
            
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
            
            # Debug logging
            print(f"[CDP DEBUG] Response status: {response.status_code}")
            print(f"[CDP DEBUG] Response body:")
            print(json.dumps(result, indent=2))
            
            if not response.is_success or not result.get("success"):
                return SettleResult(
                    success=False,
                    error=result.get("error") or result.get("errorReason") or "Settlement failed",
                )
            
            return SettleResult(
                success=True,
                transaction=result.get("transaction"),
                status=result.get("status", "settled"),
            )
            
        except Exception as e:
            return SettleResult(success=False, error=f"Settlement error: {e}")
    
    async def health_check(self) -> HealthCheckResult:
        """Check if facilitator is reachable."""
        import time
        start = time.time()
        try:
            response = self._client.head(
                self.endpoint.replace("/x402", ""),
                timeout=5.0,
            )
            latency = int((time.time() - start) * 1000)
            return HealthCheckResult(healthy=True, latency_ms=latency)
        except Exception as e:
            return HealthCheckResult(healthy=False, error=str(e))
