#!/usr/bin/env python3
"""
MoltsPay Python Client Demo - Multi-Chain (Polygon)

This demo shows:
1. Service discovery from MoltsPay marketplace
2. Multi-chain support (using Polygon)
3. Wallet info

Usage:
    cd ~/clawd/projects/moltspay-python
    source .venv/bin/activate
    python demos/polygon_multichain_demo.py
"""

import json
import httpx
from moltspay import MoltsPay
from moltspay.wallet import CHAINS


def main():
    print("=" * 60)
    print("MoltsPay Python Client - Multi-Chain Demo")
    print("=" * 60)
    
    # 1. Show supported chains
    print("\n📋 Supported Chains:")
    for name, config in CHAINS.items():
        print(f"   {name}: chain_id={config['chain_id']}")
        print(f"      USDC: {config['usdc']}")
        if 'usdt' in config:
            print(f"      USDT: {config['usdt']}")
    
    # 2. Create client with Polygon
    print("\n🔐 Creating MoltsPay client (Polygon)...")
    client = MoltsPay(chain="polygon")
    print(f"   Wallet address: {client.address}")
    print(f"   Chain: polygon (chain_id: {CHAINS['polygon']['chain_id']})")
    
    # 3. Discover services
    provider_url = "https://moltspay.com/a/yaqing2023"
    discovery_url = f"{provider_url}/.well-known/agent-services.json"
    
    print(f"\n🔍 Discovering services from:")
    print(f"   {discovery_url}")
    
    response = httpx.get(discovery_url)
    data = response.json()
    
    print(f"\n🏪 Provider: {data['provider']['name']}")
    print(f"   Wallet: {data['provider']['wallet']}")
    print(f"   Supported chains: {', '.join(data['provider'].get('chains', ['base']))}")
    
    print(f"\n📦 Available Services:")
    for svc in data['services']:
        print(f"\n   ✅ {svc['name']}")
        print(f"      ID: {svc['id']}")
        print(f"      Price: ${svc['price']} {svc['currency']}")
        print(f"      Description: {svc.get('description', 'N/A')}")
        print(f"      Chains: {', '.join(svc.get('chains', ['base']))}")
    
    # 4. Show x402 payment flow info
    print("\n💳 x402 Payment Flow (Polygon):")
    print("   1. Client calls service → gets 402 Payment Required")
    print("   2. 402 response includes payment options for ALL supported chains")
    print("   3. Client signs payment with EIP-3009 (gasless)")
    print("   4. Client retries with X-Payment header")
    print("   5. Server verifies + settles via CDP facilitator")
    print("   6. Service executes, result returned")
    
    # 5. Show how to pay (without actually paying)
    print("\n📝 To pay for a service on Polygon:")
    print("""
    from moltspay import MoltsPay
    
    client = MoltsPay(chain="polygon")
    
    # Fund your wallet first!
    # Send USDC on Polygon to: """ + client.address + """
    
    result = client.pay(
        "https://moltspay.com/a/yaqing2023",
        "38dd4058-bb94-43d3-b5a6-e2d32cca7b22",  # Multi-Chain Cat
        prompt="A fluffy cat"
    )
    print(result)
    """)
    
    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
