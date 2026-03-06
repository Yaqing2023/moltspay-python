"""Pydantic models for MoltsPay."""

from typing import Optional, Any
from pydantic import BaseModel


class Service(BaseModel):
    """A service offered by a provider."""
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    price: float
    currency: str = "USDC"
    parameters: Optional[dict] = None


class Balance(BaseModel):
    """Wallet balance."""
    address: str
    usdc: float
    eth: float
    chain: str = "base"


class Limits(BaseModel):
    """Spending limits."""
    max_per_tx: float
    max_per_day: float
    spent_today: float = 0.0
    
    @property
    def remaining_daily(self) -> float:
        return max(0, self.max_per_day - self.spent_today)


class PaymentResult(BaseModel):
    """Result of a payment."""
    success: bool
    tx_hash: Optional[str] = None
    amount: float
    service_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    explorer_url: Optional[str] = None


class WalletData(BaseModel):
    """Wallet file format (compatible with Node.js CLI)."""
    address: str
    privateKey: str
    chain: str = "base"
    encrypted: bool = False
    iv: Optional[str] = None
    salt: Optional[str] = None
    label: Optional[str] = None
    createdAt: Optional[Any] = None  # Can be int (timestamp) or str
    limits: Optional[dict] = None
    spending: Optional[dict] = None
