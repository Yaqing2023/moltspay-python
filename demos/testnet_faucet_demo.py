#!/usr/bin/env python3
"""
MoltsPay Testnet Demo
=====================

Demonstrates the complete testnet flow:
1. Create wallet on Base Sepolia (testnet)
2. Get free USDC from faucet
3. Make a test payment

No real money needed! Perfect for testing your integration.

Install:
    pip install moltspay

Usage:
    python testnet_faucet_demo.py
"""

from moltspay import MoltsPay


# Test service on MoltsPay marketplace (supports base_sepolia testnet)
PROVIDER_URL = "https://moltspay.com/a/yaqing"
SERVICE_ID = "fd6bda18-e994-4370-83e3-235a08307387"  # Text to Video


def main():
    print("=" * 50)
    print("MoltsPay Testnet Demo")
    print("=" * 50)
    print()
    
    # --- Step 1: Initialize on Testnet ---
    print("Step 1: Initialize Wallet (Base Sepolia)")
    print("-" * 40)
    
    client = MoltsPay(chain="base_sepolia", timeout=180.0)  # 3 min for video gen
    print(f"✓ Wallet ready")
    print(f"  Address: {client.address}")
    print(f"  Chain: Base Sepolia (testnet)")
    print()
    
    # --- Step 2: Get Free Testnet USDC ---
    print("Step 2: Request Testnet USDC from Faucet")
    print("-" * 40)
    
    result = client.faucet()
    
    if result.success:
        print(f"✓ Received {result.amount} USDC!")
        print(f"  TX: {result.tx_hash}")
    else:
        print(f"✗ Faucet request failed: {result.error}")
        if "already claimed" in str(result.error).lower():
            print("  (You can only request once per 24 hours)")
        print()
        print("Continuing anyway - you may have USDC from a previous request...")
    print()
    
    # --- Step 3: Discover Services ---
    print("Step 3: Discover Available Services")
    print("-" * 40)
    
    try:
        services = client.discover(PROVIDER_URL)
        for svc in services:
            chains = ", ".join(svc.chains) if svc.chains else "base"
            print(f"  - {svc.name}: ${svc.price} {svc.currency} ({chains})")
        print()
    except Exception as e:
        print(f"  Could not discover services: {e}")
        print()
    
    # --- Step 4: Make Test Payment ---
    print("Step 4: Make Test Payment")
    print("-" * 40)
    print(f"  Provider: {PROVIDER_URL}")
    print(f"  Service: {SERVICE_ID}")
    print()
    
    result = client.pay(
        PROVIDER_URL,
        SERVICE_ID,
        prompt="a robot dancing in the rain"
    )
    
    if result.success:
        print("=" * 50)
        print("SUCCESS!")
        print("=" * 50)
        print(f"  Paid: ${result.amount} USDC (testnet)")
        print(f"  TX: {result.tx_hash}")
        if result.result:
            print(f"  Response: {result.result}")
    else:
        print(f"✗ Payment failed: {result.error}")
        print()
        print("Common issues:")
        print("  - Insufficient balance: run faucet again tomorrow")
        print("  - Service not available on testnet: try a different service")
    
    print()
    print("=" * 50)
    print("Demo complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
