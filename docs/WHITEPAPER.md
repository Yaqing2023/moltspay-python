# MoltsPay: A Protocol for Autonomous Agent-to-Agent Payments

**Version 1.0 | March 2026**

**Authors:** Zen7 Labs 

**Abstract:** As AI agents become increasingly autonomous, they require the ability to transact economically without human intervention. This paper introduces MoltsPay, an open-source protocol and SDK enabling AI agents to hold funds, make payments, and receive payments using cryptocurrency. Built on the x402 HTTP payment standard and leveraging gasless transaction infrastructure, MoltsPay provides a practical solution for agent-to-agent commerce. We describe the protocol architecture, security model, and reference implementations in Python and TypeScript.

---

## 1. Introduction

### 1.1 The Economic Agent Problem

The rapid advancement of large language models (LLMs) and autonomous AI agents has created a new class of software entities capable of complex, goal-directed behavior. These agents can browse the web, write code, schedule meetings, and perform multi-step tasks with minimal human oversight.

However, current AI agents face a fundamental limitation: **they cannot participate in economic transactions**. When an agent encounters a paid API, a premium data source, or another agent offering services for a fee, it must either:

1. Fail the task entirely
2. Request human intervention to complete payment
3. Rely on pre-negotiated API keys with fixed quotas

None of these options support true autonomous operation. As agents become more capable and are deployed at scale, this economic limitation becomes a critical bottleneck.

### 1.2 Requirements for Agent Payments

An effective agent payment system must satisfy several requirements:

- **Programmable**: Payments must be executable via code without human interaction
- **Permissionless**: Agents should not require bank accounts, credit checks, or identity verification
- **Low-latency**: Transactions must complete in seconds, not days
- **Low-cost**: Fees must be negligible for micro-transactions
- **Secure**: Spending must be bounded and auditable
- **Interoperable**: The system must work across different agent frameworks and platforms

### 1.3 Contribution

This paper presents MoltsPay, a protocol satisfying all of the above requirements. Our contributions include:

1. A protocol specification for HTTP-native agent payments based on the x402 standard
2. A gasless transaction architecture eliminating the need for agents to hold native blockchain tokens
3. A spending limit mechanism providing cryptographic guarantees on maximum expenditure
4. Open-source reference implementations in Python and TypeScript
5. A service discovery mechanism enabling agents to find and evaluate paid services

---

## 2. Background

### 2.1 HTTP 402 Payment Required

The HTTP 402 status code was reserved in the original HTTP/1.1 specification (RFC 2616) for "future use" in digital payment systems. The x402 protocol (x402.org) provides a modern implementation of this concept:

```
Client                              Server
   |                                   |
   |  GET /api/video-generation        |
   |---------------------------------->|
   |                                   |
   |  402 Payment Required             |
   |  X-Payment-Address: 0x...         |
   |  X-Payment-Amount: 1.00           |
   |  X-Payment-Currency: USDC         |
   |<----------------------------------|
   |                                   |
   |  GET /api/video-generation        |
   |  X-Payment-Signature: <sig>       |
   |---------------------------------->|
   |                                   |
   |  200 OK                           |
   |  {video_url: "..."}               |
   |<----------------------------------|
```

This approach makes payments a native part of the HTTP request/response cycle, requiring no out-of-band payment flows.

### 2.2 Stablecoins and Layer 2 Networks

Cryptocurrency volatility makes it unsuitable for everyday transactions. Stablecoins—tokens pegged to fiat currencies—solve this problem. MoltsPay supports two major stablecoins:

- **USDC** (USD Coin) - Regulated reserves, 1:1 USD peg, issued by Circle
- **USDT** (Tether) - Largest stablecoin by market cap, widely accepted

Layer 2 (L2) networks provide scalability improvements over Ethereum mainnet:

| Network | Chain ID | Avg. Fee | Confirmation Time |
|---------|----------|----------|-------------------|
| Ethereum L1 | 1 | $2-50 | 12 seconds |
| **Base** | 8453 | $0.001-0.01 | 2 seconds |
| **Polygon** | 137 | $0.01-0.05 | 2 seconds |
| Base Sepolia (testnet) | 84532 | Free | 2 seconds |

MoltsPay supports Base and Polygon mainnets, plus Base Sepolia for testing. Each chain has pre-configured contract addresses for USDC and USDT.

### 2.3 Gasless Transactions

Traditional blockchain transactions require the sender to hold native tokens (ETH) to pay for gas. This creates friction for AI agents, which would need to manage two token balances.

ERC-4337 (Account Abstraction) and paymaster infrastructure enable "gasless" transactions where a third party sponsors gas fees. MoltsPay leverages Coinbase's paymaster service, allowing agents to transact using only USDC.

---

## 3. Protocol Specification

### 3.1 Service Discovery

MoltsPay services advertise their capabilities via a well-known endpoint. The configuration follows the official JSON Schema at `https://moltspay.com/schemas/services.json`.

```
GET /.well-known/agent-services.json

{
  "provider": {
    "name": "Zen7 Video Generation",
    "description": "AI-powered video generation service",
    "wallet": "0xb8d6f2441e8f8dfB6288A74Cf73804cDd0484E0C",
    "chain": "base",
    "chains": ["base", "base_sepolia", "polygon"]
  },
  "services": [
    {
      "id": "text-to-video",
      "name": "Text to Video",
      "description": "Generate video from text prompt",
      "function": "textToVideo",
      "price": 0.99,
      "currency": "USDC",
      "input": {
        "prompt": {"type": "string", "required": true, "description": "Text description"},
        "duration": {"type": "number", "default": 5}
      },
      "output": {
        "video_url": {"type": "string", "description": "Generated video URL"}
      }
    }
  ]
}
```

**Schema Reference:** `https://moltspay.com/schemas/services.json`

**Provider Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✓ | Provider display name |
| `wallet` | ✓ | Ethereum address to receive payments (0x...) |
| `description` | | Provider description |
| `chain` | | Default blockchain network (default: `base`) |
| `chains` | | Multi-chain support array |

**Service Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `id` | ✓ | Unique identifier (lowercase, hyphens allowed) |
| `price` | ✓ | Price in currency units |
| `currency` | ✓ | Payment currency: `USDC`, `USDT`, or `DAI` |
| `name` | | Human-readable name |
| `description` | | Service description |
| `function` | | Function name exported from index.js |
| `input` | | Input parameters schema |
| `output` | | Output schema |

**Supported Chains:**

| Chain | Chain ID | Tokens |
|-------|----------|--------|
| `base` | 8453 | USDC, USDT, DAI |
| `polygon` | 137 | USDC, USDT, DAI |
| `base_sepolia` | 84532 | USDC (testnet) |

This enables agents to programmatically discover available services, validate inputs, and understand outputs.

### 3.2 Payment Flow

The complete payment flow consists of four phases:

**Phase 1: Discovery**
```python
services = client.discover("https://api.example.com")
# Returns list of available services with prices
```

**Phase 2: Request**
```
POST /execute
Content-Type: application/json

{"service": "text-to-video", "prompt": "A sunset over mountains"}
```

**Phase 3: Payment Challenge**
```
HTTP/1.1 402 Payment Required
X-Payment-Address: 0xb8d6f2441e8f8dfB6288A74Cf73804cDd0484E0C
X-Payment-Amount: 0.99
X-Payment-Currency: USDC
X-Payment-Chain: base
X-Payment-Nonce: abc123
```

**Phase 4: Signed Request**
```
POST /execute
Content-Type: application/json
X-Payment-Signature: 0x<eip712_signature>
X-Payment-Nonce: abc123

{"service": "text-to-video", "prompt": "A sunset over mountains"}
```

The server verifies the signature, submits the transaction to the blockchain via the paymaster, and returns the result upon confirmation.

### 3.3 Signature Scheme

MoltsPay uses EIP-712 typed structured data signing with chain-aware configuration:

```javascript
// Chain configurations
const CHAINS = {
  base: { chainId: 8453, usdc: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" },
  polygon: { chainId: 137, usdc: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359" },
  base_sepolia: { chainId: 84532, usdc: "0x036CbD53842c5426634e7929541eC2318f3dCF7e" }
};

const chain = CHAINS[selectedChain];

const domain = {
  name: "MoltsPay",
  version: "1",
  chainId: chain.chainId,
  verifyingContract: chain.usdc  // or chain.usdt for USDT payments
};

const types = {
  Payment: [
    { name: "to", type: "address" },
    { name: "amount", type: "uint256" },
    { name: "nonce", type: "bytes32" },
    { name: "deadline", type: "uint256" }
  ]
};

const signature = await wallet.signTypedData(domain, types, {
  to: serverWallet,
  amount: parseUnits("0.99", 6),
  nonce: serverNonce,
  deadline: Math.floor(Date.now() / 1000) + 300
});
```

This provides:
- **Multi-chain support**: Same signature scheme works across Base, Polygon, and testnets
- **Multi-token support**: USDC or USDT selectable per transaction
- Replay protection via nonce
- Time-bounded validity via deadline
- Clear user consent (typed data is human-readable in wallet UIs)

### 3.4 Transaction Settlement

MoltsPay supports two settlement modes:

**Immediate Settlement (Default)**
The server submits the transaction immediately upon receiving a valid signature. The request blocks until on-chain confirmation (~2 seconds on Base).

**Optimistic Settlement**
For trusted clients or low-value transactions, the server may return results immediately after signature verification, settling the transaction asynchronously. This reduces latency to <100ms.

---

## 4. Security Model

### 4.1 Spending Limits

MoltsPay enforces spending limits at the wallet level:

```python
client.init_wallet(
    max_per_tx=10.0,      # Maximum per transaction
    max_per_day=100.0     # Maximum per 24-hour period
)
```

These limits are stored in the wallet configuration and enforced client-side before signing. For stronger guarantees, agents can use smart contract wallets with on-chain spending limits.

### 4.2 Threat Model

| Threat | Mitigation |
|--------|------------|
| Malicious service overcharging | Client verifies price before signing; disputes via on-chain evidence |
| Replay attacks | Nonce included in signature; server tracks used nonces |
| Man-in-the-middle | HTTPS required; payment address verified against discovery endpoint |
| Wallet key compromise | Spending limits bound maximum loss; key rotation supported |
| Service non-delivery | On-chain payment receipt enables dispute resolution |

### 4.3 Key Management

Agent wallet keys may be stored in:
1. Environment variables (simple, suitable for trusted environments)
2. Hardware security modules (HSMs) for production deployments
3. Secure enclaves (e.g., AWS Nitro, Intel SGX)

MoltsPay's SDK abstracts key management, allowing drop-in replacement of the signing backend.

---

## 5. Implementation

### 5.1 Client SDK (Python)

```python
from moltspay import MoltsPay

# Initialize client
client = MoltsPay()
client.init_wallet(max_per_tx=10.0, max_per_day=100.0)

# Check balance
balance = client.get_balance()
print(f"Balance: {balance} USDC")

# Pay for service
result = client.pay(
    service_url="https://api.zen7.com",
    service_id="text-to-video",
    prompt="A serene Japanese garden"
)
print(f"Video: {result['video_url']}")
```

### 5.2 Server SDK (TypeScript)

```typescript
import { MoltsPay } from 'moltspay';

const server = new MoltsPay.Server({
  wallet: process.env.WALLET_ADDRESS,
  services: './moltspay.services.json'
});

// Middleware automatically handles 402 flow
app.use('/execute', server.middleware());

app.post('/execute', async (req, res) => {
  // Payment already verified by middleware
  const result = await generateVideo(req.body.prompt);
  res.json(result);
});
```

### 5.3 Framework Integrations

MoltsPay provides native integrations for popular agent frameworks:

**LangChain**
```python
from moltspay.integrations import MoltsPayTool

tools = [MoltsPayTool(client)]
agent = initialize_agent(tools, llm)
```

**CrewAI**
```python
from moltspay.integrations import MoltsPayCrewTool

agent = Agent(
    role="Researcher",
    tools=[MoltsPayCrewTool(client)]
)
```

---

## 6. Economics

### 6.1 Fee Structure

MoltsPay itself charges no protocol fees. Costs consist of:

| Component | Cost |
|-----------|------|
| Network gas (Base) | ~$0.001 per transaction |
| Network gas (Polygon) | ~$0.01 per transaction |
| USDC/USDT transfer | No fee |
| Paymaster sponsorship | Free (Coinbase subsidized on Base) |

Total cost per transaction: **<$0.01**

**Supported Payment Tokens:**
- USDC (USD Coin) - Default, widest support
- USDT (Tether) - Higher liquidity in some markets
- DAI (MakerDAO) - Decentralized stablecoin option

### 6.2 Service Pricing

Service providers set their own prices. Recommended pricing models:

- **Per-request**: Fixed fee per API call (e.g., $0.10 per image analysis)
- **Per-unit**: Fee proportional to output (e.g., $0.05 per second of video)
- **Tiered**: Volume discounts for repeat customers

### 6.3 Market Dynamics

Agent-to-agent payments enable new market structures:

- **Specialization**: Agents focus on core competencies, outsourcing other tasks
- **Price discovery**: Competitive markets emerge for common services
- **Reputation systems**: On-chain payment history enables trust scoring

---

## 7. Related Work

### 7.1 Existing Payment Solutions

| Solution | Programmable | Permissionless | Low-cost | Gasless |
|----------|--------------|----------------|----------|---------|
| Stripe | ✓ | ✗ | ✗ | N/A |
| PayPal | ✓ | ✗ | ✗ | N/A |
| Bitcoin | ✓ | ✓ | ✗ | ✗ |
| Ethereum L1 | ✓ | ✓ | ✗ | ✗ |
| **MoltsPay** | ✓ | ✓ | ✓ | ✓ |

### 7.2 Agent Payment Research

Prior work on agent payments includes:
- Autonomous Economic Agents (AEA) framework by Fetch.ai
- SingularityNET marketplace for AI services
- Ocean Protocol for data marketplaces

MoltsPay differentiates by focusing on simplicity, HTTP-native integration, and compatibility with mainstream agent frameworks.

---

## 8. Future Work

### 8.1 Multi-party Payments

Enabling payment splitting for composite services:
```
Agent A → Service B (50%) + Service C (50%)
```

### 8.2 Streaming Payments

Real-time payment streams for continuous services (e.g., per-token pricing for LLM inference).

### 8.3 Cross-chain Settlement

Supporting additional L2 networks and cross-chain bridges for improved liquidity.

### 8.4 Decentralized Service Registry

On-chain registry of verified services with reputation scores and dispute resolution.

---

## 9. Conclusion

MoltsPay provides a practical solution for AI agent payments, combining the programmability of cryptocurrency with the simplicity of HTTP APIs. By eliminating gas fees and providing built-in spending limits, we enable safe autonomous agent commerce.

The protocol is fully open-source and available at:
- Python SDK: https://pypi.org/project/moltspay/
- TypeScript SDK: https://www.npmjs.com/package/moltspay
- GitHub: https://github.com/Yaqing2023/moltspay-python

We invite the community to build on MoltsPay and contribute to the emerging agent economy.

---

## References

1. RFC 2616 - Hypertext Transfer Protocol -- HTTP/1.1
2. EIP-712 - Typed structured data hashing and signing
3. EIP-4337 - Account Abstraction Using Alt Mempool
4. x402 Protocol Specification - https://x402.org
5. MoltsPay Services Schema - https://moltspay.com/schemas/services.json
6. USDC Technical Documentation - https://developers.circle.com
7. Base Network Documentation - https://docs.base.org

---

## Appendix A: API Reference

### Client Methods

| Method | Description |
|--------|-------------|
| `init_wallet(max_per_tx, max_per_day)` | Initialize agent wallet with spending limits |
| `get_balance()` | Get current USDC balance |
| `discover(url)` | Discover services at URL |
| `pay(service_url, service_id, **params)` | Pay for and execute service |
| `faucet()` | Request testnet USDC (testnet only) |

### Server Configuration (agent-services.json)

**Schema:** `https://moltspay.com/schemas/services.json`

```json
{
  "provider": {
    "name": "string (required)",
    "wallet": "0x... (required)",
    "description": "string",
    "chain": "base | polygon | base_sepolia (default: base)",
    "chains": ["base", "polygon", "base_sepolia"]
  },
  "services": [{
    "id": "string (required, lowercase with hyphens)",
    "price": "number (required)",
    "currency": "USDC | USDT (required)",
    "name": "string",
    "description": "string",
    "function": "string (exported function name)",
    "input": {
      "param_name": {"type": "string|number|boolean", "required": true, "description": "..."}
    },
    "output": {
      "field_name": {"type": "string", "description": "..."}
    }
  }]
}
```

### Supported Chains

| Chain | Chain ID | Network | Tokens |
|-------|----------|---------|--------|
| `base` | 8453 | Base Mainnet | USDC, USDT, DAI |
| `polygon` | 137 | Polygon Mainnet | USDC, USDT, DAI |
| `base_sepolia` | 84532 | Base Sepolia Testnet | USDC |

---

**License:** MIT

**Contact:** support@moltspay.com

**Citation:**
```bibtex
@article{moltspay2026,
  title={MoltsPay: A Protocol for Autonomous Agent-to-Agent Payments},
  author={Zen7 Labs},
  year={2026},
  url={https://github.com/Yaqing2023/moltspay-python}
}
```
