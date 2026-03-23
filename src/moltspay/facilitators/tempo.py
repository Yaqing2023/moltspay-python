"""
Tempo/MPP (Machine Payments Protocol) facilitator.

Handles payments on Tempo Moderato testnet using the MPP protocol.
Unlike x402, MPP requires an on-chain transaction before retrying with credential.

Flow:
1. Server returns 402 with WWW-Authenticate: Payment id="...", method="tempo", request="..."
2. Client executes TIP-20 transfer on-chain
3. Client retries request with Authorization: Payment <credential> containing txHash
"""

import base64
import json
import re
import time
from typing import Any, Dict, Optional
from dataclasses import dataclass

import httpx
from eth_account import Account
from web3 import Web3

from ..chains import CHAINS


@dataclass
class MPPPaymentRequest:
    """Parsed MPP payment request from WWW-Authenticate header."""
    challenge_id: str
    method: str
    realm: str
    amount: int
    currency: str
    recipient: str
    chain_id: int


def parse_www_authenticate(header: str) -> MPPPaymentRequest:
    """Parse WWW-Authenticate: Payment header."""
    def get_param(key: str) -> Optional[str]:
        match = re.search(rf'{key}="([^"]+)"', header, re.IGNORECASE)
        return match.group(1) if match else None
    
    challenge_id = get_param("id")
    method = get_param("method")
    realm = get_param("realm")
    request_b64 = get_param("request")
    
    if method != "tempo":
        raise ValueError(f"Unsupported payment method: {method}")
    
    if not request_b64:
        raise ValueError("Missing request in WWW-Authenticate")
    
    # Decode payment request
    request_json = base64.b64decode(request_b64).decode("utf-8")
    payment_request = json.loads(request_json)
    
    return MPPPaymentRequest(
        challenge_id=challenge_id or "",
        method=method,
        realm=realm or "",
        amount=int(payment_request["amount"]),
        currency=payment_request["currency"],
        recipient=payment_request["recipient"],
        chain_id=payment_request.get("methodDetails", {}).get("chainId", 42431),
    )


def build_credential(
    challenge_id: str,
    realm: str,
    payment_request: dict,
    tx_hash: str,
    sender: str,
    chain_id: int,
) -> str:
    """Build MPP credential for Authorization header."""
    credential = {
        "challenge": {
            "id": challenge_id,
            "realm": realm,
            "method": "tempo",
            "intent": "charge",
            "request": payment_request,
        },
        "payload": {"hash": tx_hash, "type": "hash"},
        "source": f"did:pkh:eip155:{chain_id}:{sender}",
    }
    
    # Base64url encode (no padding)
    credential_json = json.dumps(credential)
    credential_b64 = base64.b64encode(credential_json.encode()).decode()
    credential_b64 = credential_b64.replace("+", "-").replace("/", "_").rstrip("=")
    
    return credential_b64


# TIP-20 Transfer ABI (same as ERC-20)
TIP20_TRANSFER_ABI = [
    {
        "name": "transfer",
        "type": "function",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"type": "bool"}],
    }
]


def execute_tip20_transfer(
    private_key: str,
    recipient: str,
    amount: int,
    token_address: str,
    rpc_url: str,
    chain_id: int,
) -> str:
    """Execute TIP-20 token transfer on Tempo."""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    account = Account.from_key(private_key)
    
    # Create contract instance
    token = w3.eth.contract(
        address=Web3.to_checksum_address(token_address),
        abi=TIP20_TRANSFER_ABI,
    )
    
    # Build transaction
    nonce = w3.eth.get_transaction_count(account.address)
    
    tx = token.functions.transfer(
        Web3.to_checksum_address(recipient),
        amount,
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
        raise Exception("Transaction failed")
    
    return tx_hash.hex()


def handle_mpp_payment(
    server_url: str,
    service: str,
    params: Dict[str, Any],
    www_auth_header: str,
    private_key: str,
) -> Dict[str, Any]:
    """
    Handle MPP (Machine Payments Protocol) payment flow.
    
    Args:
        server_url: Service endpoint URL
        service: Service ID
        params: Request parameters
        www_auth_header: WWW-Authenticate header from 402 response
        private_key: Wallet private key (hex string with 0x prefix)
    
    Returns:
        Service response after successful payment
    """
    # Parse payment request
    payment_req = parse_www_authenticate(www_auth_header)
    
    chain = CHAINS["tempo_moderato"]
    amount_display = payment_req.amount / 1e6
    
    print(f"[MoltsPay] MPP Payment: ${amount_display} to {payment_req.recipient[:10]}...")
    
    # Execute transfer on Tempo
    print(f"[MoltsPay] Sending transaction on Tempo...")
    tx_hash = execute_tip20_transfer(
        private_key=private_key,
        recipient=payment_req.recipient,
        amount=payment_req.amount,
        token_address=payment_req.currency,
        rpc_url=chain["rpc"],
        chain_id=chain["chainId"],
    )
    
    print(f"[MoltsPay] Transaction: {tx_hash}")
    
    # Build credential
    account = Account.from_key(private_key)
    original_request = {
        "amount": payment_req.amount,
        "currency": payment_req.currency,
        "recipient": payment_req.recipient,
        "methodDetails": {"chainId": payment_req.chain_id},
    }
    
    credential = build_credential(
        challenge_id=payment_req.challenge_id,
        realm=payment_req.realm,
        payment_request=original_request,
        tx_hash=tx_hash if tx_hash.startswith("0x") else f"0x{tx_hash}",
        sender=account.address,
        chain_id=payment_req.chain_id,
    )
    
    # Retry with credential
    print(f"[MoltsPay] Retrying with credential...")
    
    with httpx.Client(timeout=120) as client:
        response = client.post(
            f"{server_url}/execute",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Payment {credential}",
            },
            json={"service": service, "params": params, "chain": "tempo_moderato"},
        )
    
    result = response.json()
    
    if not response.is_success:
        raise Exception(result.get("error", "Payment verification failed"))
    
    print(f"[MoltsPay] Success! Tempo payment settled.")
    
    return result.get("result", result)
