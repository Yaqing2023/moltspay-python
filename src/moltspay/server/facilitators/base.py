"""Base Facilitator interface for MoltsPay Server."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class VerifyResult:
    """Result of payment verification."""
    valid: bool
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class SettleResult:
    """Result of payment settlement."""
    success: bool
    transaction: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Result of health check."""
    healthy: bool
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class BaseFacilitator(ABC):
    """
    Abstract base class for payment facilitators.
    
    Each facilitator handles payment verification and settlement
    for specific blockchain networks.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Facilitator identifier (e.g., 'cdp', 'bnb', 'tempo', 'solana')."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name."""
        pass
    
    @property
    @abstractmethod
    def supported_networks(self) -> List[str]:
        """List of supported network identifiers (e.g., ['eip155:8453', 'eip155:137'])."""
        pass
    
    def supports_network(self, network: str) -> bool:
        """Check if this facilitator supports the given network."""
        return network in self.supported_networks
    
    @abstractmethod
    async def verify(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> VerifyResult:
        """
        Verify a payment.
        
        Args:
            payment_payload: The payment data from the client
            requirements: The payment requirements (amount, recipient, etc.)
            
        Returns:
            VerifyResult with valid=True if payment is valid
        """
        pass
    
    @abstractmethod
    async def settle(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> SettleResult:
        """
        Settle a payment (execute the actual transfer).
        
        Args:
            payment_payload: The payment data from the client
            requirements: The payment requirements
            
        Returns:
            SettleResult with success=True and transaction hash if successful
        """
        pass
    
    async def health_check(self) -> HealthCheckResult:
        """
        Check if the facilitator is healthy and can process payments.
        
        Returns:
            HealthCheckResult with healthy=True if operational
        """
        return HealthCheckResult(healthy=True)
