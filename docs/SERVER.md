# Running a MoltsPay Server (Accepting Payments)

This guide explains how to set up a MoltsPay server to accept x402 payments for your AI services.

## Quick Start

```bash
# Install
pip install moltspay

# Create your skill directory
mkdir my_skill
cd my_skill

# Create service definition and Python code (see below)
# ...

# Start server
moltspay-server ./my_skill --port 8402
```

## Skill Structure

A skill is a directory containing:

```
my_skill/
├── moltspay.services.json    # Service definitions (pricing, params)
└── __init__.py               # Python functions
```

### moltspay.services.json

```json
{
  "provider": {
    "name": "My AI Service",
    "description": "Amazing AI capabilities",
    "wallet": "0xYourWalletAddress",
    "chain": "base"
  },
  "services": [
    {
      "id": "text-to-video",
      "name": "Text to Video",
      "description": "Generate video from text prompt",
      "price": 0.99,
      "currency": "USDC",
      "function": "generate_video",
      "input": {
        "prompt": {
          "type": "string",
          "required": true,
          "description": "Text prompt for video generation"
        },
        "duration": {
          "type": "number",
          "required": false,
          "description": "Video duration in seconds (default: 5)"
        }
      },
      "output": {
        "video_url": {
          "type": "string",
          "description": "URL to generated video"
        }
      }
    }
  ]
}
```

### __init__.py

```python
import asyncio

async def generate_video(params: dict) -> dict:
    """Generate video from text prompt."""
    prompt = params.get("prompt")
    duration = params.get("duration", 5)
    
    # Your video generation logic here
    # ...
    
    return {
        "video_url": "https://example.com/video.mp4",
        "duration": duration,
    }

# Sync functions also work
def simple_service(params: dict) -> dict:
    return {"result": "Hello!"}
```

## Environment Setup

### 1. Create CDP Account (Required for Mainnet)

1. Go to https://portal.cdp.coinbase.com/
2. Create a project
3. Generate API keys (copy both Key ID and Secret)

### 2. Create ~/.moltspay/.env

```bash
mkdir -p ~/.moltspay
cp .env.example ~/.moltspay/.env
# Edit ~/.moltspay/.env with your credentials
```

**~/.moltspay/.env:**

```bash
# Network: 'true' for Base mainnet, 'false' for testnet
USE_MAINNET=true

# CDP Credentials (required for mainnet)
CDP_API_KEY_ID=your-key-id-here
CDP_API_KEY_SECRET=your-secret-here
```

### 3. Your Wallet

Set your receiving wallet address in `moltspay.services.json`:

```json
{
  "provider": {
    "wallet": "0xYourEthereumAddress"
  }
}
```

This is where you'll receive USDC payments. You can use any Ethereum-compatible wallet (MetaMask, Coinbase Wallet, etc.) on Base network.

## Running the Server

### Basic Usage

```bash
# Single skill
moltspay-server ./my_skill

# Multiple skills
moltspay-server ./video_gen ./transcription ./image_gen

# Custom port
moltspay-server ./my_skill --port 3000

# Explicit mainnet/testnet
moltspay-server ./my_skill --mainnet
moltspay-server ./my_skill --testnet
```

### Programmatic Usage

```python
from moltspay.server import MoltsPayServer

# Load skills and start server
server = MoltsPayServer(
    "./video_gen",
    "./transcription",
    port=8402,
    use_mainnet=True,
)
server.listen()
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/services` | GET | List available services |
| `/.well-known/agent-services.json` | GET | Standard discovery endpoint |
| `/execute` | POST | Execute service (requires x402 payment) |
| `/health` | GET | Health check |

## Payment Flow

```
Client                          Your Server                    CDP Facilitator
  │                                 │                               │
  │ POST /execute (no payment)      │                               │
  │ ─────────────────────────────>  │                               │
  │                                 │                               │
  │ 402 + payment requirements      │                               │
  │ <─────────────────────────────  │                               │
  │                                 │                               │
  │ [Client signs payment]          │                               │
  │                                 │                               │
  │ POST /execute + X-Payment       │                               │
  │ ─────────────────────────────>  │                               │
  │                                 │ Verify payment                │
  │                                 │ ─────────────────────────────>│
  │                                 │                               │
  │                                 │ ✓ Valid                       │
  │                                 │ <─────────────────────────────│
  │                                 │                               │
  │                                 │ [Execute skill]               │
  │                                 │                               │
  │                                 │ Settle payment                │
  │                                 │ ─────────────────────────────>│
  │                                 │                               │
  │ 200 OK + result                 │                               │
  │ <─────────────────────────────  │                               │
```

**Key Points:**
- Your server never touches private keys
- You don't pay gas fees (CDP facilitator handles settlement)
- Payments are verified before execution
- Settlement happens after successful execution (pay-on-success)

## Production Deployment

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;
    
    location /zen7/ {
        proxy_pass http://127.0.0.1:8402/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Systemd Service

```ini
[Unit]
Description=MoltsPay Server
After=network.target

[Service]
User=myuser
WorkingDirectory=/home/myuser/skills
ExecStart=/usr/local/bin/moltspay-server ./video_gen --port 8402
Restart=always
RestartSec=5
Environment=HOME=/home/myuser

[Install]
WantedBy=multi-user.target
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install moltspay

COPY my_skill/ ./my_skill/
COPY .env /root/.moltspay/.env

EXPOSE 8402
CMD ["moltspay-server", "./my_skill", "--port", "8402"]
```

## Testing

### Test Discovery

```bash
curl http://localhost:8402/.well-known/agent-services.json | jq .
```

### Test with MoltsPay Client

```python
from moltspay import MoltsPay

client = MoltsPay()
result = client.pay(
    "http://localhost:8402",
    "text-to-video",
    prompt="a cat dancing"
)
print(result.result)
```

### Test with CLI

```bash
# Node.js CLI
npx moltspay pay http://localhost:8402 text-to-video --prompt "a cat dancing"
```

## Accepting Multiple Currencies

You can accept both USDC and USDT:

```json
{
  "services": [{
    "id": "my-service",
    "price": 0.99,
    "currency": "USDC",
    "acceptedCurrencies": ["USDC", "USDT"],
    ...
  }]
}
```

## Troubleshooting

### "CDP credentials required for mainnet"

You're running with `USE_MAINNET=true` but haven't set CDP credentials:

```bash
# Check ~/.moltspay/.env has:
CDP_API_KEY_ID=your-key-id
CDP_API_KEY_SECRET=your-secret
```

### "Function 'xxx' not found"

Make sure your function name in `moltspay.services.json` matches the function in `__init__.py`:

```json
{"function": "my_function"}  // Must match...
```

```python
def my_function(params):  // ...this function name
    ...
```

### Payment verification failed

- Check your wallet address is correct
- Ensure you're on the right network (mainnet vs testnet)
- Verify CDP credentials are valid

## Links

- **MoltsPay Docs:** https://moltspay.com/docs
- **x402 Protocol:** https://www.x402.org/
- **CDP Portal:** https://portal.cdp.coinbase.com/
- **GitHub:** https://github.com/Yaqing2023/moltspay-python
