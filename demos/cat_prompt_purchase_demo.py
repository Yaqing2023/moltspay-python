#!/usr/bin/env python3
"""
MoltsPay Cat Prompt Purchase Demo
=================================

Demonstrates how to use the MoltsPay Python SDK to purchase 
services from the MoltsPay marketplace.

Install:
    pip install moltspay

Usage:
    python cat_prompt_purchase_demo.py
"""

from moltspay import MoltsPay

# Service to purchase
PROVIDER_URL = "https://moltspay.com/a/jeffwang"
SERVICE_ID = "436864af-758c-416b-aaef-cd129d1a75f1"  # Cat Prompt


def main():
    print("=" * 50)
    print("MoltsPay Python SDK Demo")
    print("=" * 50)
    print()
    
    # Initialize client (auto-creates wallet if needed)
    client = MoltsPay()
    print(f"Wallet: {client.address}")
    print()
    
    # Discover available services
    print("Discovering services...")
    services = client.discover(PROVIDER_URL)
    for svc in services:
        print(f"  - {svc.name}: ${svc.price} {svc.currency}")
    print()
    
    # Purchase the Cat Prompt service
    print(f"Purchasing Cat Prompt...")
    result = client.pay(PROVIDER_URL, SERVICE_ID)
    
    if result.success:
        print()
        print("=" * 50)
        print("SUCCESS!")
        print("=" * 50)
        print(f"Paid: ${result.amount} USDC")
        print(f"Result: {result.result}")
    else:
        print(f"Failed: {result.error}")


if __name__ == "__main__":
    main()
