#!/usr/bin/env python3
"""
MoltsPay Wallet Status Demo

Shows all wallet addresses and status (EVM + Solana).
Consistent with Node.js CLI: `moltspay status`

Usage:
    python demos/wallet_status_demo.py
"""

from moltspay import MoltsPay


def main():
    print("=" * 60)
    print("MoltsPay Wallet Status")
    print("=" * 60)

    # Initialize client (chain doesn't matter for status)
    client = MoltsPay()

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

    # Wallet file locations
    print("\n📁 Wallet Files")
    print("   EVM: ~/.moltspay/wallet.json")
    print("   Solana: ~/.moltspay/wallet-solana.json")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
