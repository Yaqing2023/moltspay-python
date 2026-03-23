#!/usr/bin/env python3
"""
MoltsPay Wallet Status Demo

Shows wallet addresses and status for both EVM and Solana chains.
Demonstrates the multi-wallet architecture.

Usage:
    python demos/wallet_status_demo.py
    python demos/wallet_status_demo.py --chain solana_devnet
"""

import argparse
from moltspay import MoltsPay


def main():
    parser = argparse.ArgumentParser(description="MoltsPay Wallet Status")
    parser.add_argument(
        "--chain",
        default="base",
        help="Chain to use (base, polygon, base_sepolia, solana, solana_devnet)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("MoltsPay Wallet Status")
    print("=" * 60)

    # Initialize client
    client = MoltsPay(chain=args.chain)

    # Show current chain
    print(f"\n📍 Current Chain: {args.chain}")
    print(f"   Default Address: {client.address}")

    # EVM Wallet
    print("\n🔷 EVM Wallet (Base/Polygon/BNB)")
    print(f"   Address: {client.evm_address}")
    
    # Show limits
    limits = client.limits()
    print(f"   Max per TX: ${limits.max_per_tx:.2f}")
    print(f"   Max per Day: ${limits.max_per_day:.2f}")
    print(f"   Spent Today: ${limits.spent_today:.2f}")

    # Solana Wallet
    print("\n🟣 Solana Wallet")
    try:
        solana_addr = client.solana_address
        if solana_addr:
            print(f"   Address: {solana_addr}")
        else:
            print("   Status: Not initialized (install 'solders' to enable)")
    except Exception as e:
        print(f"   Status: Error - {e}")

    # Chain-specific info
    print("\n📊 Chain Info")
    is_solana = client._is_solana_chain()
    print(f"   Is Solana Chain: {is_solana}")
    
    if is_solana:
        print("   Protocol: Solana SPL Transfer")
        print("   Explorer: https://solscan.io")
    else:
        print("   Protocol: x402 (gasless)")
        print("   Token: USDC (EIP-2612 permit)")

    # Wallet file locations
    print("\n📁 Wallet Files")
    print("   EVM: ~/.moltspay/wallet.json")
    print("   Solana: ~/.moltspay/wallet-solana.json")

    print("\n" + "=" * 60)
    print("Tip: Use different chains with --chain flag")
    print("  python demos/wallet_status_demo.py --chain solana_devnet")
    print("=" * 60)


if __name__ == "__main__":
    main()
