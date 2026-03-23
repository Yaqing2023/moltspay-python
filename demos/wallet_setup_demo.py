#!/usr/bin/env python3
"""
MoltsPay Wallet Setup Demo
==========================

Demonstrates how to create wallets and set spending limits.
Shows both EVM (Base/Polygon) and Solana wallets.

Install:
    pip install moltspay

Usage:
    python wallet_setup_demo.py
"""

from moltspay import MoltsPay


def main():
    print("=" * 55)
    print("MoltsPay Wallet Setup Demo")
    print("=" * 55)
    print()
    
    # --- Step 1: Initialize Client (auto-creates wallets) ---
    print("Step 1: Initialize Client")
    print("-" * 40)
    
    client = MoltsPay()
    print(f"✓ Wallets ready")
    print()
    
    # --- Step 2: Show Wallet Addresses ---
    print("Step 2: Wallet Addresses")
    print("-" * 40)
    
    print(f"  🔷 EVM (Base/Polygon/BNB):")
    print(f"     {client.evm_address}")
    
    solana_addr = client.solana_address
    if solana_addr:
        print(f"  🟣 Solana:")
        print(f"     {solana_addr}")
    else:
        print(f"  🟣 Solana: (not initialized)")
    print()
    
    # --- Step 3: View Current Limits ---
    print("Step 3: Spending Limits")
    print("-" * 40)
    
    limits = client.limits()
    print(f"  Max per transaction: ${limits.max_per_tx:.2f}")
    print(f"  Max per day:         ${limits.max_per_day:.2f}")
    print(f"  Spent today:         ${limits.spent_today:.2f}")
    print()
    
    # --- Step 4: Set New Limits ---
    print("Step 4: Update Limits")
    print("-" * 40)
    
    client.set_limits(max_per_tx=10, max_per_day=100)
    print(f"✓ Set max per transaction: $10.00")
    print(f"✓ Set max per day: $100.00")
    print()
    
    # --- Step 5: Wallet Files ---
    print("Step 5: Wallet Files")
    print("-" * 40)
    print("  📁 EVM:    ~/.moltspay/wallet.json")
    print("  📁 Solana: ~/.moltspay/wallet-solana.json")
    print()
    print("  ⚠️  IMPORTANT: Back up these files!")
    print("     They contain your private keys.")
    print()
    
    print("=" * 55)
    print("Setup complete!")
    print("=" * 55)
    print()
    print("Next steps:")
    print("  • Check balances:  python demos/wallet_status_demo.py")
    print("  • Get test USDC:   python demos/testnet_faucet_demo.py")
    print("  • Fund wallet:     python demos/fund_wallet_demo.py 10")
    print()


if __name__ == "__main__":
    main()
