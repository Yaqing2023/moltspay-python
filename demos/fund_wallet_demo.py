#!/usr/bin/env python3
"""
Demo: Fund wallet via QR code

This demo shows how to fund your MoltsPay wallet using a debit card or Apple Pay.
No crypto knowledge needed - just scan the QR code and pay!

Usage:
    python demos/fund_wallet_demo.py [amount] [--chain base|polygon]

Examples:
    python demos/fund_wallet_demo.py 10           # Fund $10 on Base
    python demos/fund_wallet_demo.py 20 --chain polygon  # Fund $20 on Polygon
"""

import sys
from moltspay import MoltsPay


def main():
    # Parse arguments
    amount = 10.0  # Default $10
    chain = "base"  # Default chain
    
    args = sys.argv[1:]
    if args:
        try:
            amount = float(args[0])
        except ValueError:
            pass
    
    if "--chain" in args:
        idx = args.index("--chain")
        if idx + 1 < len(args):
            chain = args[idx + 1]
    
    # Initialize client (auto-creates wallet if not exists)
    client = MoltsPay(chain=chain)
    
    print(f"🔑 Wallet initialized")
    print(f"   Address: {client.address}")
    print(f"   Chain: {chain}")
    
    # Generate funding QR code
    # This calls the MoltsPay server API - no CDP credentials needed locally!
    result = client.fund_qr(amount, chain)
    
    if result.success:
        print("✅ Scan the QR code above with your phone")
        print("   Pay with US debit card or Apple Pay")
        print("   USDC will arrive in ~2 minutes")
    else:
        print(f"❌ Error: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
