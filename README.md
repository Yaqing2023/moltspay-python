# MoltsPay Python SDK

[![PyPI version](https://img.shields.io/pypi/v/moltspay.svg)](https://pypi.org/project/moltspay/)
[![Python versions](https://img.shields.io/pypi/pyversions/moltspay.svg)](https://pypi.org/project/moltspay/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**Python SDK for MoltsPay - Agent-to-Agent Payments.**

MoltsPay enables AI agents to pay each other for services using the [x402 protocol](https://www.x402.org/) - HTTP-native payments with USDC stablecoins. No gas fees, no complex wallet management.

## What is MoltsPay?

MoltsPay is blockchain payment infrastructure designed for AI agents. It solves a fundamental problem: **how do autonomous AI agents pay for services?**

- 🤖 **Agent-to-Agent Commerce** - AI agents can autonomously discover, pay for, and use services
- 💨 **Gasless Payments** - Uses EIP-2612 permits, no ETH needed
- 🔗 **x402 Protocol** - HTTP 402 Payment Required - payments as native HTTP flow
- 🔒 **Spending Limits** - Set per-transaction and daily limits for safety
- 🌐 **Multi-Chain** - Base and Polygon supported
- 🦜 **LangChain Ready** - Drop-in tools for LangChain agents

## Installation

```bash
pip install moltspay
```

For LangChain integration:
```bash
pip install moltspay[langchain]
```

## Quick Start

```python
from moltspay import MoltsPay

# Initialize (auto-creates wallet if not exists)
client = MoltsPay()
print(f"Wallet address: {client.address}")

# Discover services from a provider
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

### Auto Wallet Management

Wallet is automatically created on first run and stored at `~/.moltspay/wallet.json`. Compatible with Node.js CLI.

```python
from moltspay import MoltsPay

client = MoltsPay()
print(f"Address: {client.address}")
print(f"Balance: {client.balance()} USDC")
```

### Spending Limits

Control your agent's spending with built-in limits:

```python
from moltspay import MoltsPay

client = MoltsPay()

# Check current limits
limits = client.limits()
print(f"Max per tx: {limits.max_per_tx}")
print(f"Max per day: {limits.max_per_day}")
print(f"Spent today: {limits.spent_today}")

# Update limits
client.set_limits(max_per_tx=20, max_per_day=200)
```

### Multi-Chain Support

MoltsPay supports multiple chains. Default is Base, but you can use Polygon:

```python
from moltspay import MoltsPay

# Default: Base
client = MoltsPay()

# Use Polygon
client = MoltsPay(chain='polygon')

# Pay on Polygon
result = client.pay(
    "https://juai8.com/zen7",
    "text-to-video",
    prompt="a cat dancing"
)
```

**Supported Chains:**

| Chain | Network ID | Token |
|-------|------------|-------|
| Base | eip155:8453 | USDC |
| Polygon | eip155:137 | USDC |

Both chains are gasless - the CDP facilitator handles all on-chain settlement.

### Async Support

Full async/await support for high-performance applications:

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

### Error Handling

Comprehensive exception types for robust error handling:

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

Use MoltsPay as tools in your LangChain agents - let your AI autonomously pay for services!

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

### Available Tools

Two tools available for different use cases:

```python
from moltspay.integrations.langchain import get_moltspay_tools

tools = get_moltspay_tools()  # Returns both tools
```

| Tool | Description |
|------|-------------|
| `MoltsPayTool` | Pay for and execute services |
| `MoltsPayDiscoverTool` | Discover available services and prices |

## CLI Compatibility

Wallet format is fully compatible with the Node.js CLI:

```bash
# Create wallet with Node CLI
npx moltspay init --chain base

# Use same wallet in Python
python -c "from moltspay import MoltsPay; print(MoltsPay().address)"
```

## How x402 Works

```
Your Agent                     Service Provider              Blockchain
    │                               │                           │
    │ Request service               │                           │
    │ ──────────────────────────>   │                           │
    │                               │                           │
    │ 402 + price + wallet          │                           │
    │ <──────────────────────────   │                           │
    │                               │                           │
    │ [Sign payment - NO GAS]       │                           │
    │                               │                           │
    │ Request + signed payment      │                           │
    │ ──────────────────────────>   │ Verify & settle           │
    │                               │ ─────────────────────────>│
    │                               │                           │
    │ 200 OK + result               │                           │
    │ <──────────────────────────   │                           │
```

**Your agent never pays gas** - the CDP facilitator handles all on-chain settlement.

## Use Cases

- **AI Assistants** - Let your assistant pay for premium APIs
- **Autonomous Agents** - Agents that can spend within limits
- **Multi-Agent Systems** - Agents paying other agents for services
- **AI Pipelines** - Pay-per-use for expensive compute steps

## Running a Server (Accepting Payments)

Want to accept payments for your AI services? See the **[Server Guide](docs/SERVER.md)**.

Quick start:

```bash
# Install
pip install moltspay

# Create skill structure
mkdir my_skill && cd my_skill
# Add moltspay.services.json and __init__.py (see docs)

# Start server
moltspay-server ./my_skill --port 8402
```

## Related Projects

- [moltspay (Node.js)](https://github.com/Yaqing2023/moltspay) - Node.js SDK and CLI
- [x402 Protocol](https://www.x402.org/) - The HTTP payment standard

## Links

- **Website:** https://moltspay.com
- **PyPI:** https://pypi.org/project/moltspay/
- **npm (Node.js):** https://www.npmjs.com/package/moltspay
- **GitHub:** https://github.com/Yaqing2023/moltspay-python

## License

MIT
