# MoltsPay Python SDK

Python SDK for MoltsPay - Agent-to-Agent Payments.

## Installation

```bash
pip install moltspay
```

## Quick Start

```python
from moltspay import MoltsPay

# Initialize (auto-creates wallet if not exists)
client = MoltsPay()
print(f"Wallet address: {client.address}")

# Discover services
services = client.discover("https://juai8.com/zen7")
for svc in services:
    print(f"{svc.id}: {svc.price} {svc.currency}")

# Pay for a service
result = client.pay(
    "https://juai8.com/zen7",
    "text-to-video",
    prompt="a cat dancing on the beach"
)
print(result.result)
```

## Features

- **Auto wallet management** - Creates wallet on first run, compatible with Node.js CLI
- **Spending limits** - Set per-transaction and daily limits
- **x402 protocol** - Native support for HTTP 402 payment flow
- **Gasless payments** - Uses EIP-2612 permits, no ETH needed for clients
- **LangChain integration** - Use as a tool in LangChain agents

## Wallet Management

```python
from moltspay import MoltsPay

# Wallet auto-created at ~/.moltspay/wallet.json
client = MoltsPay()

# Check limits
limits = client.limits()
print(f"Max per tx: {limits.max_per_tx}")
print(f"Spent today: {limits.spent_today}")

# Update limits
client.set_limits(max_per_tx=20, max_per_day=200)
```

## Async Support

```python
import asyncio
from moltspay import AsyncMoltsPay

async def main():
    async with AsyncMoltsPay() as client:
        result = await client.pay(
            "https://juai8.com/zen7",
            "text-to-video",
            prompt="a cat dancing"
        )
        print(result.result)

asyncio.run(main())
```

## Error Handling

```python
from moltspay import MoltsPay, InsufficientFunds, LimitExceeded, PaymentError

client = MoltsPay()

try:
    result = client.pay(...)
except InsufficientFunds as e:
    print(f"Need {e.required} USDC, have {e.balance}")
except LimitExceeded as e:
    print(f"Exceeds {e.limit_type} limit: {e.amount} > {e.limit}")
except PaymentError as e:
    print(f"Payment failed: {e}")
```

## LangChain Integration

Use MoltsPay as a tool in your LangChain agents:

```bash
pip install moltspay[langchain]
```

```python
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from moltspay.integrations.langchain import MoltsPayTool

llm = ChatOpenAI(model="gpt-4")
tools = [MoltsPayTool()]

agent = initialize_agent(
    tools, 
    llm, 
    agent=AgentType.OPENAI_FUNCTIONS,
    verbose=True
)

# Agent can now pay for AI services!
result = agent.run("Generate a video of a cat dancing on the beach")
```

Two tools available:
- `MoltsPayTool` - Pay for and execute services
- `MoltsPayDiscoverTool` - Discover available services and prices

```python
from moltspay.integrations.langchain import get_moltspay_tools

tools = get_moltspay_tools()  # Returns both tools
```

## CLI Compatibility

Wallet format is compatible with Node.js CLI:

```bash
# Create wallet with Node CLI
npx moltspay init --chain base

# Use same wallet in Python
python -c "from moltspay import MoltsPay; print(MoltsPay().address)"
```

## Links

- **Docs:** https://moltspay.com
- **NPM (Node.js):** https://npmjs.com/package/moltspay
- **GitHub:** https://github.com/Yaqing2023/moltspay-python

## License

MIT
