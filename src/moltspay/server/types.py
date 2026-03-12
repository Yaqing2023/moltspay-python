"""Type definitions for MoltsPay Server."""

from typing import Any, Callable, Awaitable, Optional, List, Dict, Literal, Union
from dataclasses import dataclass, field
from pydantic import BaseModel


# Type alias for skill handlers
SkillHandler = Callable[[Dict[str, Any]], Awaitable[Any]]
SyncSkillHandler = Callable[[Dict[str, Any]], Any]


class ServiceInput(BaseModel):
    """Service input parameter definition."""
    type: str = "string"
    required: bool = False
    description: Optional[str] = None


class ServiceConfig(BaseModel):
    """Service configuration from moltspay.services.json."""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    currency: str = "USDC"
    acceptedCurrencies: Optional[List[str]] = None
    function: str
    input: Dict[str, ServiceInput] = {}
    output: Dict[str, Any] = {}

    @property
    def accepted_currencies(self) -> List[str]:
        """Get list of accepted currencies."""
        return self.acceptedCurrencies or [self.currency]


class ChainConfig(BaseModel):
    """Chain configuration for multi-chain support."""
    chain: str  # "base" or "polygon"
    network: str  # "eip155:8453" or "eip155:137"
    tokens: List[str] = ["USDC"]  # ["USDC", "USDT"]


class ProviderConfig(BaseModel):
    """Provider configuration from moltspay.services.json."""
    name: str
    description: Optional[str] = None
    wallet: str
    chain: str = "base"  # deprecated, for backward compat
    chains: Optional[List[ChainConfig]] = None  # multi-chain support


class ServicesManifest(BaseModel):
    """Full services manifest structure."""
    provider: ProviderConfig
    services: List[ServiceConfig]


@dataclass
class RegisteredSkill:
    """A registered skill with its handler."""
    id: str
    config: ServiceConfig
    handler: Union[SkillHandler, SyncSkillHandler]


@dataclass
class X402PaymentRequirements:
    """x402 payment requirements."""
    scheme: str
    network: str
    asset: str
    amount: str
    payTo: str
    maxTimeoutSeconds: int = 300
    extra: Dict[str, str] = field(default_factory=dict)


@dataclass
class X402PaymentPayload:
    """Parsed x402 payment payload."""
    x402Version: int
    payload: Dict[str, Any]
    accepted: Optional[Dict[str, Any]] = None
    resource: Optional[Dict[str, Any]] = None
    scheme: Optional[str] = None
    network: Optional[str] = None


@dataclass
class VerifyResult:
    """Result of payment verification."""
    valid: bool
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    facilitator: Optional[str] = None


@dataclass
class SettleResult:
    """Result of payment settlement."""
    success: bool
    transaction: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    facilitator: Optional[str] = None


# Token contract addresses by network
TOKEN_ADDRESSES: Dict[str, Dict[str, str]] = {
    "eip155:8453": {  # Base mainnet
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    },
    "eip155:137": {  # Polygon mainnet
        "USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    },
}

# EIP-712 domain info for tokens
TOKEN_DOMAINS: Dict[str, Dict[str, str]] = {
    "USDC": {"name": "USD Coin", "version": "2"},
    "USDT": {"name": "Tether USD", "version": "2"},
}

# x402 protocol version
X402_VERSION = 2
