#!/usr/bin/env python3
"""
MoltsPay Wallet Status Demo

Shows all wallet addresses and balances (EVM + Solana).
Consistent with Node.js CLI: `moltspay status`

Usage:
    python demos/wallet_status_demo.py
    python demos/wallet_status_demo.py --json
"""

import argparse
import json
from moltspay import MoltsPay


def main():
    parser = argparse.ArgumentParser(description="MoltsPay Wallet Status")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Initialize client
    client = MoltsPay()

    if args.json:
        # JSON output
        output = {
            "evm_address": client.evm_address,
            "solana_address": client.solana_address,
            "balances": client.get_all_balances(),
            "limits": {
                "max_per_tx": client.limits().max_per_tx,
                "max_per_day": client.limits().max_per_day,
                "spent_today": client.limits().spent_today,
            }
        }
        
        # Add Solana balances
        try:
            output["solana_balances"] = {
                "devnet": client.get_solana_balances("solana_devnet"),
                "mainnet": client.get_solana_balances("solana"),
            }
        except Exception:
            pass
        
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    print("\n📊 MoltsPay Wallet Status\n")
    print(f"   Address: {client.evm_address}")
    print("")
    print("   Balances:")
    
    # Get all EVM balances
    all_balances = client.get_all_balances()
    
    # Chain display names
    chain_names = {
        "base": "Base",
        "polygon": "Polygon", 
        "base_sepolia": "Base Sepolia",
        "bnb": "BNB",
        "bnb_testnet": "BNB Testnet",
    }
    
    for chain, balances in all_balances.items():
        chain_label = chain_names.get(chain, chain).ljust(14)
        usdc = balances.get("usdc", 0.0)
        usdt = balances.get("usdt", 0.0)
        native = balances.get("native", 0.0)
        
        # BNB chains: show gas warning if low
        if chain in ("bnb", "bnb_testnet"):
            warning = " ⚠️ Low gas" if native < 0.0005 else ""
            print(f"     {chain_label} {usdc:.2f} USDC | {usdt:.2f} USDT | {native:.4f} BNB{warning}")
        else:
            print(f"     {chain_label} {usdc:.2f} USDC | {usdt:.2f} USDT")
    
    # Spending limits
    limits = client.limits()
    print("")
    print("   Spending Limits:")
    print(f"     Per Transaction: ${limits.max_per_tx:.2f}")
    print(f"     Daily:           ${limits.max_per_day:.2f}")
    print(f"     Spent Today:     ${limits.spent_today:.2f}")
    
    # Solana wallet (if exists)
    solana_addr = client.solana_address
    if solana_addr:
        print("")
        print("   ─────────────────────────────────")
        print(f"   🟣 Solana: {solana_addr}")
        
        # Devnet balances
        try:
            devnet = client.get_solana_balances("solana_devnet")
            print(f"     Devnet:    {devnet['sol']:.4f} SOL | {devnet['usdc']:.2f} USDC")
        except Exception:
            print("     Devnet:    (unable to fetch)")
        
        # Mainnet balances
        try:
            mainnet = client.get_solana_balances("solana")
            print(f"     Mainnet:   {mainnet['sol']:.4f} SOL | {mainnet['usdc']:.2f} USDC")
        except Exception:
            print("     Mainnet:   (unable to fetch)")
    
    print("")


if __name__ == "__main__":
    main()
