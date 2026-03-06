"""x402 protocol client implementation."""

import base64
import json
import os
import time
from typing import Any, Optional, List, Callable
from dataclasses import dataclass

import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data

from .models import Service
from .exceptions import PaymentError


@dataclass
class PaymentRequired:
    """Parsed 402 Payment Required response."""
    x402_version: int
    accepts: List[dict]
    resource: dict
    raw: dict


def parse_402_response(response: httpx.Response) -> PaymentRequired:
    """Parse 402 Payment Required response."""
    # Try X-Payment-Required header first (base64 encoded)
    header = response.headers.get("X-Payment-Required")
    if header:
        try:
            data = json.loads(base64.b64decode(header))
            return PaymentRequired(
                x402_version=data.get("x402Version", 2),
                accepts=data.get("accepts", []),
                resource=data.get("resource", {}),
                raw=data,
            )
        except (json.JSONDecodeError, Exception):
            pass
    
    # Try response body
    try:
        body = response.json()
        data = body.get("x402", body)
        return PaymentRequired(
            x402_version=data.get("x402Version", 2),
            accepts=data.get("accepts", []),
            resource=data.get("resource", {}),
            raw=data,
        )
    except Exception:
        raise PaymentError("Could not parse 402 response")


def sign_eip3009_authorization(
    account: Account,
    pay_to: str,
    amount: str,
    asset: str,
    chain_id: int,
    token_name: str,
    token_version: str,
    timeout_seconds: int = 300,
) -> dict:
    """Sign EIP-3009 TransferWithAuthorization for gasless USDC transfer."""
    nonce = "0x" + os.urandom(32).hex()
    valid_after = int(time.time()) - 60
    valid_before = int(time.time()) + timeout_seconds
    
    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": token_name,
            "version": token_version,
            "chainId": chain_id,
            "verifyingContract": asset,
        },
        "message": {
            "from": account.address,
            "to": pay_to,
            "value": int(amount),
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": bytes.fromhex(nonce[2:]),
        },
    }
    
    signable = encode_typed_data(full_message=typed_data)
    signed = account.sign_message(signable)
    
    return {
        "authorization": {
            "from": account.address,
            "to": pay_to,
            "value": amount,
            "validAfter": str(valid_after),
            "validBefore": str(valid_before),
            "nonce": nonce,
        },
        "signature": "0x" + signed.signature.hex(),
    }


def build_payment_payload(
    account: Account,
    payment_required: PaymentRequired,
) -> str:
    """Build and encode x402 payment payload."""
    req = payment_required.accepts[0]
    chain_id = int(req["network"].split(":")[1])
    
    payment = sign_eip3009_authorization(
        account=account,
        pay_to=req["payTo"],
        amount=req["amount"],
        asset=req["asset"],
        chain_id=chain_id,
        token_name=req["extra"]["name"],
        token_version=req["extra"]["version"],
        timeout_seconds=req.get("maxTimeoutSeconds", 300),
    )
    
    payload = {
        "x402Version": 2,
        "payload": payment,
        "accepted": req,
        "resource": payment_required.resource,
    }
    
    return base64.b64encode(json.dumps(payload).encode()).decode()


class X402Client:
    """Low-level x402 protocol client."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def discover_services(self, base_url: str) -> List[Service]:
        """Discover available services from a provider."""
        url = f"{base_url.rstrip('/')}/.well-known/agent-services.json"
        
        try:
            response = self._client.get(url)
            response.raise_for_status()
            data = response.json()
            
            services = []
            for svc in data.get("services", data if isinstance(data, list) else []):
                services.append(Service(
                    id=svc.get("id", ""),
                    name=svc.get("name"),
                    description=svc.get("description"),
                    price=float(svc.get("price", 0)),
                    currency=svc.get("currency", "USDC"),
                    parameters=svc.get("parameters"),
                ))
            return services
            
        except httpx.HTTPError as e:
            raise PaymentError(f"Failed to discover services: {e}")
    
    def call_service(
        self,
        base_url: str,
        service_id: str,
        params: dict,
        payment_header: Optional[str] = None,
    ) -> httpx.Response:
        """Call a service endpoint."""
        url = f"{base_url.rstrip('/')}/execute"
        body = {"service": service_id, **params}
        
        headers = {"Content-Type": "application/json"}
        if payment_header:
            headers["X-PAYMENT"] = payment_header
        
        return self._client.post(url, json=body, headers=headers)
    
    def pay_and_call(
        self,
        base_url: str,
        service_id: str,
        params: dict,
        account: Account,
    ) -> Any:
        """
        Full x402 flow: call, get 402, sign payment, retry.
        
        Args:
            base_url: Service base URL
            service_id: Service ID to call
            params: Service parameters
            account: eth-account Account for signing
        
        Returns:
            Service response data
        """
        # First call - expect 402
        response = self.call_service(base_url, service_id, params)
        
        # If not 402, return directly
        if response.status_code != 402:
            if response.status_code >= 400:
                raise PaymentError(f"Service error: {response.status_code} {response.text}")
            return response.json()
        
        # Parse 402 response
        payment_req = parse_402_response(response)
        
        # Build and sign payment
        payment_header = build_payment_payload(account, payment_req)
        
        # Retry with payment
        response = self.call_service(base_url, service_id, params, payment_header)
        
        if response.status_code >= 400:
            raise PaymentError(f"Payment failed: {response.status_code} {response.text}")
        
        return response.json()


class AsyncX402Client:
    """Async version of x402 protocol client."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    async def discover_services(self, base_url: str) -> List[Service]:
        """Discover available services from a provider."""
        url = f"{base_url.rstrip('/')}/.well-known/agent-services.json"
        
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()
            
            services = []
            for svc in data.get("services", data if isinstance(data, list) else []):
                services.append(Service(
                    id=svc.get("id", ""),
                    name=svc.get("name"),
                    description=svc.get("description"),
                    price=float(svc.get("price", 0)),
                    currency=svc.get("currency", "USDC"),
                    parameters=svc.get("parameters"),
                ))
            return services
            
        except httpx.HTTPError as e:
            raise PaymentError(f"Failed to discover services: {e}")
    
    async def call_service(
        self,
        base_url: str,
        service_id: str,
        params: dict,
        payment_header: Optional[str] = None,
    ) -> httpx.Response:
        """Call a service endpoint."""
        url = f"{base_url.rstrip('/')}/execute"
        body = {"service": service_id, **params}
        
        headers = {"Content-Type": "application/json"}
        if payment_header:
            headers["X-PAYMENT"] = payment_header
        
        return await self._client.post(url, json=body, headers=headers)
    
    async def pay_and_call(
        self,
        base_url: str,
        service_id: str,
        params: dict,
        account: Account,
    ) -> Any:
        """Full x402 flow (async version)."""
        response = await self.call_service(base_url, service_id, params)
        
        if response.status_code != 402:
            if response.status_code >= 400:
                raise PaymentError(f"Service error: {response.status_code} {response.text}")
            return response.json()
        
        payment_req = parse_402_response(response)
        payment_header = build_payment_payload(account, payment_req)
        
        response = await self.call_service(base_url, service_id, params, payment_header)
        
        if response.status_code >= 400:
            raise PaymentError(f"Payment failed: {response.status_code} {response.text}")
        
        return response.json()
