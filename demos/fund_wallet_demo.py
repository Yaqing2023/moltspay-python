#!/usr/bin/env python3
"""
Demo: Fund wallet via Coinbase Onramp

This demo shows how to fund your MoltsPay wallet using a debit card or Apple Pay.
No crypto knowledge needed - just scan the QR code and pay!

Supported chains:
    - base (Base mainnet)
    - polygon (Polygon mainnet)
    - solana (Solana mainnet)

For testnets, use testnet_faucet_demo.py instead.

Usage:
    python demos/fund_wallet_demo.py [amount] [--chain base|polygon|solana]

Examples:
    python demos/fund_wallet_demo.py 10                    # Fund $10 on Base
    python demos/fund_wallet_demo.py 20 --chain polygon    # Fund $20 on Polygon
    python demos/fund_wallet_demo.py 15 --chain solana     # Fund $15 on Solana
"""

import argparse
from moltspay import MoltsPay


SUPPORTED_CHAINS = ["base", "polygon", "solana"]


def main():
    parser = argparse.ArgumentParser(description="Fund MoltsPay wallet via Coinbase Onramp")
    parser.add_argument("amount", type=float, nargs="?", default=10.0, help="Amount in USD (min $5)")
    parser.add_argument("--chain", default="base", choices=SUPPORTED_CHAINS, help="Chain to fund")
    args = parser.parse_args()
    
    amount = args.amount
    chain = args.chain
    
    if amount < 5:
        print("❌ Minimum funding amount is $5")
        return
    
    # Initialize client
    client = MoltsPay(chain=chain)
    
    # Get appropriate wallet address
    if chain == "solana":
        address = client.solana_address
        if not address:
            print("❌ No Solana wallet found. Run a command with --chain solana first.")
            return
    else:
        address = client.evm_address
    
    print(f"\n💳 Fund your MoltsPay wallet\n")
    print(f"   Wallet:  {address}")
    print(f"   Chain:   {chain.capitalize()}")
    print(f"   Amount:  ${amount:.2f}")
    print()
    
    # Generate funding QR code
    result = client.fund_qr(amount, chain)
    
    if result.success:
        print("\n✅ Scan the QR code above with your phone")
        print("   Pay with US debit card or Apple Pay")
        print("   USDC will arrive in ~2 minutes")
    else:
        print(f"\n❌ Error: {result.error}")
        
        # Chain-specific hints
        if chain == "solana":
            print("\n💡 Alternative: Transfer USDC directly to your Solana wallet")
            print(f"   Address: {address}")
        elif "testnet" in chain:
            print("\n💡 For testnets, use the faucet instead:")
            print(f"   python demos/testnet_faucet_demo.py --chain {chain}")
    
    print()


if __name__ == "__main__":
    main()
