"""
BNB Chain payment facilitator.

Handles payments on BNB Chain (mainnet and testnet) using approval-based flow.

Flow:
1. User must have pre-approved the spender (one-time, requires BNB for gas)
2. Client signs EIP-712 payment intent
3. Server calls transferFrom to execute payment
"""

import base64
import json
import time
from typing import Any, Dict, Optional
from dataclasses import dataclass

import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

from ..chains import CHAINS


# ERC20 ABI for allowance check
ERC20_ALLOWANCE_ABI = [
    {
        "name": "allowance",
        "type": "function",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
    }
]


def check_allowance(
    token_address: str,
    owner: str,
    spender: str,
    rpc_url: str,
) -> int:
    """Check ERC20 allowance for a spender."""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    token = w3.eth.contract(
        address=Web3.to_checksum_address(token_address),
        abi=ERC20_ALLOWANCE_ABI,
    )
    return token.functions.allowance(
        Web3.to_checksum_address(owner),
        Web3.to_checksum_address(spender),
    ).call()


def check_native_balance(address: str, rpc_url: str) -> int:
    """Check native BNB balance."""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    return w3.eth.get_balance(Web3.to_checksum_address(address))


def sign_payment_intent(
    account: Account,
    to: str,
    amount: int,
    token: str,
    service: str,
    chain_id: int,
) -> Dict[str, Any]:
    """Sign EIP-712 payment intent for BNB."""
    nonce = int(time.time() * 1000)
    deadline = int(time.time() * 1000) + 3600000  # 1 hour in milliseconds
    
    intent = {
        "from": account.address,
        "to": to,
        "amount": str(amount),
        "token": token,
        "service": service,
        "nonce": nonce,
        "deadline": deadline,
    }
    
    domain = {
        "name": "MoltsPay",
        "version": "1",
        "chainId": chain_id,
    }
    
    types = {
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
    }
    
    typed_data = {
        "types": types,
        "primaryType": "PaymentIntent",
        "domain": domain,
        "message": intent,
    }
    
    signable = encode_typed_data(full_message=typed_data)
    signed = account.sign_message(signable)
    
    return {
        "intent": {
            **intent,
            "signature": "0x" + signed.signature.hex(),
        },
        "chainId": chain_id,
    }


def handle_bnb_payment(
    server_url: str,
    service: str,
    params: Dict[str, Any],
    payment_details: Dict[str, Any],
    private_key: str,
    chain_name: str,
) -> Dict[str, Any]:
    """
    Handle BNB Chain payment flow.
    
    Args:
        server_url: Service endpoint URL
        service: Service ID
        params: Request parameters
        payment_details: Payment requirements (to, amount, token, spender)
        private_key: Wallet private key
        chain_name: Chain name ('bnb' or 'bnb_testnet')
    
    Returns:
        Service response after successful payment
    
    Raises:
        Exception: If approval is missing or insufficient balance
    """
    chain = CHAINS[chain_name]
    account = Account.from_key(private_key)
    
    to = payment_details["to"]
    amount = int(payment_details["amount"])
    token_address = payment_details["token"]
    spender = payment_details["spender"]
    
    # Determine token symbol and decimals
    token_symbol = "USDC"
    token_decimals = 18
    for sym, config in chain["tokens"].items():
        if config["address"].lower() == token_address.lower():
            token_symbol = sym
            token_decimals = config["decimals"]
            break
    
    amount_display = amount / (10 ** token_decimals)
    
    print(f"[MoltsPay] BNB Payment: ${amount_display} {token_symbol} to {to[:10]}...")
    
    # Check allowance
    allowance = check_allowance(
        token_address=token_address,
        owner=account.address,
        spender=spender,
        rpc_url=chain["rpc"],
    )
    
    if allowance < amount:
        # Check BNB balance for approval
        native_balance = check_native_balance(account.address, chain["rpc"])
        min_gas = 500000000000000  # 0.0005 BNB in wei
        
        if native_balance < min_gas:
            native_bnb = native_balance / 1e18
            is_testnet = chain_name == "bnb_testnet"
            
            if is_testnet:
                raise Exception(
                    f"❌ Insufficient tBNB for approval transaction\n\n"
                    f"   Current tBNB: {native_bnb:.4f}\n"
                    f"   Required:     ~0.001 tBNB\n\n"
                    f"   Get testnet tokens: moltspay faucet --chain bnb_testnet\n"
                    f"   (Gives USDC + tBNB for gas)"
                )
            else:
                raise Exception(
                    f"❌ Insufficient BNB for approval transaction\n\n"
                    f"   Current BNB: {native_bnb:.4f}\n"
                    f"   Required:    ~0.001 BNB (~$0.60)\n\n"
                    f"   Fund your wallet with BNB first."
                )
        
        raise Exception(
            f"Insufficient allowance for {spender[:10]}...\n"
            f"Run: moltspay approve --chain {chain_name} --spender {spender}"
        )
    
    # Sign payment intent
    print(f"[MoltsPay] Signing BNB payment intent...")
    payload_data = sign_payment_intent(
        account=account,
        to=to,
        amount=amount,
        token=token_address,
        service=service,
        chain_id=chain["chainId"],
    )
    
    # Build x402 payload
    network = f"eip155:{chain['chainId']}"
    payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": network,
        "payload": payload_data,
        "accepted": {
            "scheme": "exact",
            "network": network,
            "asset": token_address,
            "amount": str(amount),
            "payTo": to,
            "maxTimeoutSeconds": 300,
        },
    }
    
    payment_header = base64.b64encode(json.dumps(payload).encode()).decode()
    
    # Send request with payment
    print(f"[MoltsPay] Sending BNB payment request...")
    
    with httpx.Client(timeout=120) as client:
        response = client.post(
            f"{server_url}/execute",
            headers={
                "Content-Type": "application/json",
                "X-Payment": payment_header,
            },
            json={"service": service, "params": params, "chain": chain_name},
        )
    
    result = response.json()
    
    if not response.is_success:
        raise Exception(result.get("error", "BNB payment failed"))
    
    print(f"[MoltsPay] Success! BNB payment settled.")
    
    return result.get("result", result)
