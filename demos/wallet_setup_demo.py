#!/usr/bin/env python3
"""
MoltsPay Wallet Setup Demo
==========================

Demonstrates how to create a wallet and set spending limits
using the MoltsPay Python SDK.

Install:
    pip install moltspay

Usage:
    python wallet_setup_demo.py
"""

from moltspay import MoltsPay


def main():
    print("=" * 50)
    print("MoltsPay Wallet Setup Demo")
    print("=" * 50)
    print()
    
    # --- Step 1: Initialize Client (auto-creates wallet) ---
    print("Step 1: Initialize Client")
    print("-" * 30)
    
    client = MoltsPay()
    print(f"✓ Wallet ready")
    print(f"  Address: {client.address}")
    print()
    
    # --- Step 2: View Current Limits ---
    print("Step 2: Current Spending Limits")
    print("-" * 30)
    
    limits = client.limits()
    print(f"  Max per transaction: ${limits.max_per_tx} USDC")
    print(f"  Max per day: ${limits.max_per_day} USDC")
    print(f"  Spent today: ${limits.spent_today} USDC")
    print()
    
    # --- Step 3: Set New Limits ---
    print("Step 3: Setting New Limits")
    print("-" * 30)
    
    client.set_limits(max_per_tx=5, max_per_day=50)
    print(f"✓ Set max per transaction: $5.00 USDC")
    print(f"✓ Set max per day: $50.00 USDC")
    print()
    
    # --- Step 4: Verify New Limits ---
    print("Step 4: Verify New Limits")
    print("-" * 30)
    
    limits = client.limits()
    print(f"  Max per transaction: ${limits.max_per_tx} USDC")
    print(f"  Max per day: ${limits.max_per_day} USDC")
    print()
    
    # --- Step 5: Check Balance ---
    print("Step 5: Check Balance")
    print("-" * 30)
    
    balance = client.balance()
    print(f"  Balance: ${balance} USDC")
    print()
    
    print("=" * 50)
    print("Wallet setup complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Fund your wallet with USDC on Base")
    print(f"     Send to: {client.address}")
    print("  2. Use client.pay() to purchase services")
    print()
    print("Wallet file: ~/.moltspay/wallet.json")


if __name__ == "__main__":
    main()
