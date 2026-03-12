#!/usr/bin/env python3
"""
MoltsPay Python Client Demo - Actual Payment on Polygon

This demo actually tries to pay for a service using Polygon.
Will fail if wallet has no USDC balance (expected for testing).

Usage:
    cd ~/clawd/projects/moltspay-python
    source .venv/bin/activate
    python demos/polygon_pay_demo.py
"""

from moltspay import MoltsPay
from moltspay.wallet import CHAINS


def main():
    print("=" * 60)
    print("MoltsPay Python Client - Actual Payment Demo (Polygon)")
    print("=" * 60)
    
    # Create client with Polygon
    print("\n🔐 Creating MoltsPay client (Polygon)...")
    client = MoltsPay(chain="polygon")
    print(f"   Wallet address: {client.address}")
    print(f"   Chain: polygon (chain_id: {CHAINS['polygon']['chain_id']})")
    
    # Check balance (if method exists)
    try:
        balance = client.get_balance()
        print(f"   Balance: {balance}")
    except Exception as e:
        print(f"   Balance check: {e}")
    
    # Service info
    provider_url = "https://moltspay.com/a/yaqing2023"
    service_id = "38dd4058-bb94-43d3-b5a6-e2d32cca7b22"  # Multi-Chain Cat
    
    print(f"\n💳 Attempting to pay for service...")
    print(f"   Provider: {provider_url}")
    print(f"   Service: {service_id}")
    print(f"   Price: $0.01 USDC")
    
    try:
        result = client.pay(
            provider_url,
            service_id,
            prompt="A fluffy cat sitting on a rainbow"
        )
        print(f"\n✅ Payment successful!")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"\n❌ Payment failed (expected if no balance):")
        print(f"   Error: {e}")
        print(f"\n💡 To actually pay, fund your wallet:")
        print(f"   Send USDC on Polygon to: {client.address}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
