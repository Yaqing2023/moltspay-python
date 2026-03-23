"""
Solana payment facilitator.

Handles SPL token transfers on Solana with pay-for-success model.
Server pays transaction fees, client only signs.

Flow:
1. Client creates and partially signs transfer transaction
2. Server adds fee payer signature and submits
3. Server verifies on-chain and provides service
"""

import base64
import json
from typing import Any, Dict, Optional

import httpx

try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.system_program import TransferParams, transfer
    from solders.transaction import Transaction
    from solders.message import Message
    from solders.hash import Hash
    from solana.rpc.api import Client as SolanaClient
    from spl.token.instructions import (
        TransferCheckedParams,
        transfer_checked,
        get_associated_token_address,
    )
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False

from ..chains import CHAINS
from ..exceptions import PaymentError


def check_solana_available():
    """Check if Solana dependencies are installed."""
    if not SOLANA_AVAILABLE:
        raise PaymentError(
            "Solana support requires 'solders' and 'solana-py' packages. "
            "Install with: pip install solders solana"
        )


def create_spl_transfer_transaction(
    sender_pubkey: "Pubkey",
    recipient_pubkey: "Pubkey",
    amount: int,
    mint: "Pubkey",
    decimals: int,
    rpc_url: str,
    fee_payer: Optional["Pubkey"] = None,
) -> "Transaction":
    """
    Create an SPL token transfer transaction.
    
    Args:
        sender_pubkey: Sender's public key
        recipient_pubkey: Recipient's public key  
        amount: Amount in smallest units
        mint: Token mint address
        decimals: Token decimals
        rpc_url: Solana RPC URL
        fee_payer: Optional fee payer (for gasless mode)
    
    Returns:
        Unsigned transaction
    """
    check_solana_available()
    
    client = SolanaClient(rpc_url)
    
    # Get recent blockhash
    blockhash_resp = client.get_latest_blockhash()
    recent_blockhash = blockhash_resp.value.blockhash
    
    # Get associated token accounts
    sender_ata = get_associated_token_address(sender_pubkey, mint)
    recipient_ata = get_associated_token_address(recipient_pubkey, mint)
    
    # Create transfer instruction
    transfer_ix = transfer_checked(
        TransferCheckedParams(
            program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
            source=sender_ata,
            mint=mint,
            dest=recipient_ata,
            owner=sender_pubkey,
            amount=amount,
            decimals=decimals,
        )
    )
    
    # Build transaction
    actual_fee_payer = fee_payer if fee_payer else sender_pubkey
    
    message = Message.new_with_blockhash(
        [transfer_ix],
        actual_fee_payer,
        recent_blockhash,
    )
    
    return Transaction.new_unsigned(message)


def handle_solana_payment(
    server_url: str,
    service: str,
    params: Dict[str, Any],
    payment_details: Dict[str, Any],
    keypair: "Keypair",
    chain_name: str,
) -> Dict[str, Any]:
    """
    Handle Solana payment flow.
    
    Uses pay-for-success model where server pays fees.
    
    Args:
        server_url: Service endpoint URL
        service: Service ID
        params: Request parameters
        payment_details: Payment requirements (payTo, amount, asset, etc.)
        keypair: Solana Keypair for signing
        chain_name: Chain name ('solana' or 'solana_devnet')
    
    Returns:
        Service response after successful payment
    """
    check_solana_available()
    
    chain = CHAINS[chain_name]
    
    pay_to = payment_details["payTo"]
    amount = int(payment_details["amount"])
    token_address = payment_details["asset"]
    fee_payer_str = payment_details.get("solanaFeePayer")
    
    amount_display = amount / 1e6
    
    print(f"[MoltsPay] Solana Payment: ${amount_display} USDC to {pay_to[:10]}...")
    
    # Parse addresses
    recipient = Pubkey.from_string(pay_to)
    mint = Pubkey.from_string(token_address)
    fee_payer = Pubkey.from_string(fee_payer_str) if fee_payer_str else None
    
    if fee_payer:
        print(f"[MoltsPay] Gasless mode: server pays fees")
    
    # Create transaction
    print(f"[MoltsPay] Creating Solana transaction...")
    tx = create_spl_transfer_transaction(
        sender_pubkey=keypair.pubkey(),
        recipient_pubkey=recipient,
        amount=amount,
        mint=mint,
        decimals=6,  # USDC always 6 decimals
        rpc_url=chain["rpc"],
        fee_payer=fee_payer,
    )
    
    # Sign transaction (partial if gasless)
    if fee_payer:
        tx.partial_sign([keypair], tx.message.recent_blockhash)
    else:
        tx.sign([keypair], tx.message.recent_blockhash)
    
    # Serialize
    signed_tx = base64.b64encode(bytes(tx)).decode('utf-8')
    
    print(f"[MoltsPay] Transaction signed, sending to server...")
    
    # Build x402 payload
    network = "solana:mainnet" if chain_name == "solana" else "solana:devnet"
    payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": network,
        "payload": {
            "signedTransaction": signed_tx,
            "sender": str(keypair.pubkey()),
            "chain": chain_name,
        },
        "accepted": {
            "scheme": "exact",
            "network": network,
            "asset": token_address,
            "amount": str(amount),
            "payTo": pay_to,
            "maxTimeoutSeconds": 300,
        },
    }
    
    payment_header = base64.b64encode(json.dumps(payload).encode()).decode()
    
    # Send request with payment
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
        raise PaymentError(result.get("error", "Solana payment failed"))
    
    print(f"[MoltsPay] Success! Solana payment settled.")
    
    # Print explorer link
    tx_hash = result.get("payment", {}).get("transaction")
    if tx_hash:
        cluster = "" if chain_name == "solana" else "?cluster=devnet"
        print(f"[MoltsPay] TX: https://solscan.io/tx/{tx_hash}{cluster}")
    
    return result.get("result", result)
