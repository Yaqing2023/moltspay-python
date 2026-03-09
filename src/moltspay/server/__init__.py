"""
MoltsPay Server - Accept x402 payments for your AI services.

Usage:
    # CLI
    moltspay-server ./my_skill --port 8402
    
    # Or with multiple skills
    moltspay-server ./video_gen ./transcription ./image_gen
    
    # Programmatic
    from moltspay.server import MoltsPayServer
    
    server = MoltsPayServer("./my_skill")
    server.listen(8402)

Skill Structure:
    my_skill/
    ├── moltspay.services.json    # Service definitions
    └── __init__.py               # Python functions

Example moltspay.services.json:
    {
      "provider": {
        "name": "My AI Service",
        "wallet": "0xYourWalletAddress"
      },
      "services": [{
        "id": "my-service",
        "name": "My Service",
        "price": 0.99,
        "currency": "USDC",
        "function": "my_function",
        "input": {"prompt": {"type": "string", "required": true}}
      }]
    }

Example __init__.py:
    async def my_function(params):
        prompt = params.get("prompt")
        # Do work...
        return {"result": "..."}

Environment Variables (in ~/.moltspay/.env):
    USE_MAINNET=true              # Use Base mainnet (default: false/testnet)
    CDP_API_KEY_ID=xxx            # CDP API Key ID (required for mainnet)
    CDP_API_KEY_SECRET=xxx        # CDP API Key Secret (required for mainnet)
"""

from .server import MoltsPayServer
from .facilitator import CDPFacilitator
from .types import (
    ServicesManifest,
    ServiceConfig,
    ProviderConfig,
    RegisteredSkill,
    X402PaymentPayload,
    X402PaymentRequirements,
    VerifyResult,
    SettleResult,
)

__all__ = [
    "MoltsPayServer",
    "CDPFacilitator",
    "ServicesManifest",
    "ServiceConfig",
    "ProviderConfig",
    "RegisteredSkill",
    "X402PaymentPayload",
    "X402PaymentRequirements",
    "VerifyResult",
    "SettleResult",
]
