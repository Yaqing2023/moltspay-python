#!/usr/bin/env python3
"""
MoltsPay Multi-Chain Purchase Demo
===================================

Demonstrates purchasing services on different chains:
- base, polygon (EVM mainnet)
- base_sepolia, bnb_testnet (EVM testnet)
- solana, solana_devnet (Solana)
- tempo_moderato (Tempo)

Install:
    pip install moltspay

Usage:
    python cat_prompt_purchase_demo.py                        # Base (default)
    python cat_prompt_purchase_demo.py --chain base_sepolia   # Base Sepolia testnet
    python cat_prompt_purchase_demo.py --chain solana_devnet  # Solana devnet
    python cat_prompt_purchase_demo.py --chain bnb_testnet    # BNB testnet
"""

import argparse
from moltspay import MoltsPay

# Multi-chain test service
PROVIDER_URL = "https://moltspay.com/a/yaqing2023"
SERVICE_ID = "38dd4058-bb94-43d3-b5a6-e2d32cca7b22"  # Multi-Chain Cat ($0.01)

# Chains supported by the Multi-Chain Cat service
SUPPORTED_CHAINS = [
    "base", "polygon",           # EVM mainnet
    "bnb", "bnb_testnet",        # BNB
    "solana", "solana_devnet",   # Solana
    "tempo_moderato",            # Tempo
]


def main():
    parser = argparse.ArgumentParser(description="MoltsPay Multi-Chain Purchase Demo")
    parser.add_argument(
        "--chain",
        default="base",
        choices=SUPPORTED_CHAINS,
        help="Chain to use for payment",
    )
    args = parser.parse_args()
    
    chain = args.chain
    is_testnet = chain in ("bnb_testnet", "solana_devnet", "tempo_moderato")
    
    print("=" * 55)
    print("MoltsPay Multi-Chain Purchase Demo")
    print("=" * 55)
    print()
    print(f"Chain: {chain}" + (" (testnet)" if is_testnet else ""))
    print(f"Service: Multi-Chain Cat ($0.01 USDC)")
    print()
    
    # Initialize client on the specified chain
    client = MoltsPay(chain=chain, timeout=60.0)
    
    # Show appropriate wallet
    if chain in ("solana", "solana_devnet"):
        address = client.solana_address
        print(f"🟣 Solana Wallet: {address}")
    else:
        address = client.evm_address
        print(f"🔷 EVM Wallet: {address}")
    print()
    
    # Discover services
    print("Step 1: Discover Services")
    print("-" * 40)
    try:
        services = client.discover(PROVIDER_URL)
        for svc in services:
            chains_list = svc.chains or ["base"]
            chains = ", ".join(chains_list[:3]) + ("..." if len(chains_list) > 3 else "")
            print(f"  • {svc.name}: ${svc.price} ({chains})")
    except Exception as e:
        print(f"  ⚠️ Could not discover: {e}")
    print()
    
    # Check balance first
    print("Step 2: Check Balance")
    print("-" * 40)
    if chain in ("solana", "solana_devnet"):
        balances = client.get_solana_balances(chain)
        print(f"  USDC: {balances['usdc']:.2f}")
        print(f"  SOL:  {balances['sol']:.4f}")
        if balances['usdc'] < 0.01:
            print()
            print("  ⚠️ Insufficient balance!")
            if chain == "solana_devnet":
                print("  💡 Get test USDC: python demos/testnet_faucet_demo.py --chain solana_devnet")
            return
    else:
        balance = client.balance(chain)
        print(f"  USDC: {balance.usdc:.2f}")
        if balance.usdc < 0.01:
            print()
            print("  ⚠️ Insufficient balance!")
            if is_testnet:
                print(f"  💡 Get test USDC: python demos/testnet_faucet_demo.py --chain {chain}")
            return
    print()
    
    # Purchase service
    print("Step 3: Purchase Service")
    print("-" * 40)
    print(f"  Calling: {PROVIDER_URL}")
    print(f"  Service: {SERVICE_ID}")
    print()
    
    result = client.pay(PROVIDER_URL, SERVICE_ID, chain=chain)
    
    if result.success:
        print("=" * 55)
        print("✅ SUCCESS!")
        print("=" * 55)
        print(f"  Amount: ${result.amount} USDC")
        print(f"  Chain:  {chain}")
        if result.tx_hash:
            print(f"  TX:     {result.tx_hash[:20]}...")
        if result.explorer_url:
            print(f"  Explorer: {result.explorer_url}")
        if result.result:
            print()
            print("  Response:")
            print(f"    {result.result}")
    else:
        print("=" * 55)
        print("❌ FAILED")
        print("=" * 55)
        print(f"  Error: {result.error}")
        
        if "insufficient" in str(result.error).lower():
            print()
            print("  💡 Get more USDC:")
            if is_testnet:
                print(f"     python demos/testnet_faucet_demo.py --chain {chain}")
            else:
                print(f"     python demos/fund_wallet_demo.py 10 --chain {chain}")
    
    print()


if __name__ == "__main__":
    main()
