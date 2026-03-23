#!/usr/bin/env python3
"""
BNB Chain Approve Demo

BNB Chain requires ERC20 approve() because BNB tokens don't support EIP-2612 permit.
This approval only needs to be done once per spender.

Usage:
    python bnb_approve_demo.py
    python bnb_approve_demo.py --chain bnb          # mainnet
    python bnb_approve_demo.py --spender 0x...      # custom spender
"""

import argparse
import sys
import os

# Add src to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from moltspay.wallet import Wallet
from moltspay.chains import CHAINS

# Default spender (MoltsPay faucet wallet)
DEFAULT_SPENDER = "0x145E00f48b98E2829f803Be53418230e47943a8A"


def main():
    parser = argparse.ArgumentParser(description="BNB Approve Demo")
    parser.add_argument("--chain", default="bnb_testnet", help="Chain (bnb or bnb_testnet)")
    parser.add_argument("--spender", default=DEFAULT_SPENDER, help="Spender address")
    args = parser.parse_args()
    
    chain = args.chain
    spender = args.spender
    
    print(f"\n{'='*60}")
    print(f"BNB Approve Demo")
    print(f"{'='*60}")
    print(f"Chain: {chain}")
    print(f"Spender: {spender}")
    
    if not chain.startswith("bnb"):
        print("❌ This demo is only for BNB chain (bnb or bnb_testnet)")
        return 1
    
    try:
        from web3 import Web3
        
        wallet = Wallet(chain=chain)
        chain_config = CHAINS[chain]
        
        print(f"Wallet: {wallet.address}")
        
        w3 = Web3(Web3.HTTPProvider(chain_config["rpc"]))
        account = wallet._account
        
        # Check BNB balance for gas
        bnb_balance = w3.eth.get_balance(account.address)
        bnb_balance_eth = w3.from_wei(bnb_balance, 'ether')
        print(f"BNB Balance: {bnb_balance_eth} {'tBNB' if 'testnet' in chain else 'BNB'}")
        
        if bnb_balance == 0:
            print("\n❌ No BNB for gas!")
            if "testnet" in chain:
                print("   Get tBNB from faucet: python -m moltspay faucet --chain bnb_testnet")
            else:
                print("   Buy a small amount of BNB (~$0.10) and send to your wallet:")
                print(f"   {wallet.address}")
            return 1
        
        # ERC20 ABI
        erc20_abi = [
            {
                "name": "approve",
                "type": "function",
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                ],
                "outputs": [{"type": "bool"}],
            },
            {
                "name": "allowance",
                "type": "function",
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "spender", "type": "address"},
                ],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
            },
        ]
        
        print(f"\n{'─'*60}")
        
        for token_name, token_config in chain_config["tokens"].items():
            token_address = token_config["address"]
            token = w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=erc20_abi,
            )
            
            # Check current allowance
            current_allowance = token.functions.allowance(
                account.address,
                Web3.to_checksum_address(spender)
            ).call()
            
            if current_allowance > 0:
                print(f"✅ {token_name}: Already approved")
                continue
            
            print(f"⏳ {token_name}: Approving...")
            
            nonce = w3.eth.get_transaction_count(account.address)
            max_amount = 2**256 - 1
            
            tx = token.functions.approve(
                Web3.to_checksum_address(spender),
                max_amount,
            ).build_transaction({
                "chainId": chain_config["chainId"],
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce,
            })
            
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt["status"] == 1:
                print(f"✅ {token_name}: Approved! tx: {tx_hash.hex()}")
            else:
                print(f"❌ {token_name}: Failed")
                return 1
            
            # Increment nonce for next token
            nonce += 1
        
        print(f"\n{'='*60}")
        print("✅ Done! You can now pay on BNB chain.")
        print(f"{'='*60}\n")
        return 0
        
    except ImportError:
        print("❌ web3 not installed. Run: pip install web3")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
