#!/usr/bin/env python3
"""
MoltsPay Testnet Faucet Demo
============================

Demonstrates the testnet faucet on multiple chains:
- base_sepolia (Base Sepolia)
- solana_devnet (Solana Devnet)
- tempo_moderato (Tempo Moderato)
- bnb_testnet (BNB Testnet)

No real money needed! Perfect for testing your integration.

Install:
    pip install moltspay

Usage:
    python testnet_faucet_demo.py                      # Base Sepolia (default)
    python testnet_faucet_demo.py --chain solana_devnet
    python testnet_faucet_demo.py --chain tempo_moderato
    python testnet_faucet_demo.py --chain bnb_testnet
"""

import argparse
from moltspay import MoltsPay


# Chain configurations
CHAIN_INFO = {
    "base_sepolia": {
        "name": "Base Sepolia",
        "token": "USDC",
        "native": "ETH",
    },
    "solana_devnet": {
        "name": "Solana Devnet", 
        "token": "USDC",
        "native": "SOL",
    },
    "tempo_moderato": {
        "name": "Tempo Moderato",
        "token": "pathUSD/alphaUSD/betaUSD/thetaUSD",
        "native": "TEMPO",
    },
    "bnb_testnet": {
        "name": "BNB Testnet",
        "token": "USDC",
        "native": "tBNB",
    },
}


def main():
    parser = argparse.ArgumentParser(description="MoltsPay Testnet Faucet Demo")
    parser.add_argument(
        "--chain",
        default="base_sepolia",
        choices=list(CHAIN_INFO.keys()),
        help="Testnet chain to use",
    )
    args = parser.parse_args()
    
    chain = args.chain
    info = CHAIN_INFO[chain]
    
    print("=" * 55)
    print("MoltsPay Testnet Faucet Demo")
    print("=" * 55)
    print()
    print(f"Chain: {info['name']}")
    print(f"Token: {info['token']}")
    print()
    
    # --- Step 1: Initialize Wallet ---
    print("Step 1: Initialize Wallet")
    print("-" * 40)
    
    client = MoltsPay(chain=chain)
    
    # Show appropriate address
    if chain == "solana_devnet":
        address = client.solana_address
        print(f"✓ Solana wallet ready")
    else:
        address = client.evm_address
        print(f"✓ EVM wallet ready")
    
    print(f"  Address: {address}")
    print(f"  Chain: {info['name']}")
    print()
    
    # --- Step 2: Check Current Balance ---
    print("Step 2: Check Current Balance")
    print("-" * 40)
    
    if chain == "solana_devnet":
        balances = client.get_solana_balances("solana_devnet")
        print(f"  SOL:  {balances['sol']:.4f}")
        print(f"  USDC: {balances['usdc']:.2f}")
    else:
        balance = client.balance(chain)
        print(f"  USDC: {balance.usdc:.2f}")
        if chain == "bnb_testnet":
            print(f"  tBNB: {balance.eth:.4f}")
    print()
    
    # --- Step 3: Request Tokens from Faucet ---
    print("Step 3: Request Tokens from Faucet")
    print("-" * 40)
    
    result = client.faucet()
    
    if result.success:
        print(f"✓ Received {result.amount} {info['token']}!")
        if result.tx_hash:
            print(f"  TX: {result.tx_hash}")
    else:
        print(f"✗ Faucet request failed: {result.error}")
        if "rate" in str(result.error).lower() or "24" in str(result.error):
            print("  (You can only request once per 24 hours)")
        
        # Chain-specific hints
        if chain == "tempo_moderato":
            print()
            print("💡 Alternative: Use Tempo Wallet")
            print("   https://wallet.tempo.xyz")
        elif chain == "bnb_testnet":
            print()
            print("💡 Alternative: Use BNB Chain Faucet")
            print("   https://www.bnbchain.org/en/testnet-faucet")
    print()
    
    # --- Step 4: Verify New Balance ---
    print("Step 4: Verify New Balance")
    print("-" * 40)
    
    if chain == "solana_devnet":
        balances = client.get_solana_balances("solana_devnet")
        print(f"  SOL:  {balances['sol']:.4f}")
        print(f"  USDC: {balances['usdc']:.2f}")
    else:
        balance = client.balance(chain)
        print(f"  USDC: {balance.usdc:.2f}")
        if chain == "bnb_testnet":
            print(f"  tBNB: {balance.eth:.4f}")
    print()
    
    # --- Next Steps ---
    print("=" * 55)
    print("Next Steps")
    print("=" * 55)
    print()
    print("Now you can test payments on this chain:")
    print()
    print(f"  from moltspay import MoltsPay")
    print(f"  ")
    print(f"  client = MoltsPay(chain='{chain}')")
    print(f"  result = client.pay(")
    print(f"      'https://moltspay.com/a/yaqing',")
    print(f"      'text-to-video',")
    print(f"      prompt='a robot dancing'")
    print(f"  )")
    print()


if __name__ == "__main__":
    main()
