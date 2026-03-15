# MoltsPay Python SDK - Testnet Support Plan

## Overview

Add Base Sepolia testnet support to moltspay-python, matching the Node.js SDK functionality.

## Current State Analysis

### ✅ Already Working
- `x402.py` **correctly uses server's `extra` field** for EIP-712 signing:
  ```python
  token_name=req["extra"]["name"],
  token_version=req["extra"]["version"],
  ```
- This means testnet payments should work once chain config is added

### ❌ Missing
1. `base_sepolia` chain configuration in `wallet.py`
2. `faucet()` method to get free testnet USDC
3. Documentation updates

## Implementation Plan

### Phase 1: Chain Configuration (wallet.py)

Add `base_sepolia` to `CHAINS` dict:

```python
CHAINS = {
    "base": { ... },
    "polygon": { ... },
    "base_sepolia": {
        "chain_id": 84532,
        "usdc": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        "usdt": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # Same as USDC on testnet
        "rpc": "https://sepolia.base.org",
        "explorer": "https://sepolia.basescan.org/tx/",
    },
}
```

### Phase 2: Faucet Method (client.py)

Add `faucet()` method to get testnet USDC:

```python
FAUCET_API = "https://moltspay.com/api/v1/faucet"

def faucet(self) -> FaucetResult:
    """
    Request free testnet USDC from MoltsPay faucet.
    
    Returns:
        FaucetResult with transaction info
    
    Limits:
        - 1 USDC per request
        - 1 request per 24 hours per address
    
    Example:
        client = MoltsPay(chain="base_sepolia")
        result = client.faucet()
        if result.success:
            print(f"Received 1 USDC! TX: {result.tx_hash}")
    """
    response = httpx.post(
        FAUCET_API,
        json={"address": self.address},
        timeout=30.0,
    )
    # ... handle response
```

### Phase 3: Models (models.py)

Add `FaucetResult` dataclass:

```python
@dataclass
class FaucetResult:
    success: bool
    amount: float = 1.0
    chain: str = "base_sepolia"
    tx_hash: Optional[str] = None
    error: Optional[str] = None
```

### Phase 4: Update MoltsPay class (client.py)

Update `fund()` to reject testnet chains:

```python
def fund(self, amount: float, chain: str = None) -> FundingResult:
    chain = chain or self._chain
    
    # Testnet doesn't need real funding
    if chain == "base_sepolia":
        return FundingResult(
            success=False,
            amount=amount,
            chain=chain,
            error="Use faucet() for testnet USDC, not fund()"
        )
    # ...
```

### Phase 5: Documentation Updates

1. **README.md** - Add testnet quickstart:
   ```python
   # Testnet usage
   client = MoltsPay(chain="base_sepolia")
   client.faucet()  # Get free testnet USDC
   
   result = client.pay(
       "https://moltspay.com/a/yaqing",
       "text-to-video",
       prompt="test"
   )
   ```

2. **Update docstrings** with testnet examples

## Files to Modify

| File | Changes | Status |
|------|---------|--------|
| `src/moltspay/wallet.py` | Add `base_sepolia` chain config | ✅ Done |
| `src/moltspay/client.py` | Add `faucet()` method, update `fund()` | ✅ Done |
| `src/moltspay/models.py` | Add `FaucetResult` dataclass, `chains` to Service | ✅ Done |
| `src/moltspay/__init__.py` | Export `FaucetResult` | ✅ Done |
| `demos/testnet_faucet_demo.py` | New testnet demo | ✅ Done |
| `README.md` | Add testnet quickstart section | ✅ Done |
| `pyproject.toml` | Bump version to 0.6.0 | ✅ Done |

## Testing

```bash
# Manual test
python -c "
from moltspay import MoltsPay

client = MoltsPay(chain='base_sepolia')
print(f'Wallet: {client.address}')

# Get testnet USDC
result = client.faucet()
print(f'Faucet: {result}')

# Test payment
result = client.pay(
    'https://moltspay.com/a/yaqing',
    'text-to-video',
    prompt='a robot dancing'
)
print(f'Payment: {result}')
"
```

## Version

Bump to next patch version after implementation.

## Notes

- No changes needed to `x402.py` - it already uses server's `extra` field correctly
- Same wallet address works on all chains (EVM address is chain-agnostic)
- Faucet API is already deployed at `https://moltspay.com/api/v1/faucet`
