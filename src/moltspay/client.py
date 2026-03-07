"""MoltsPay client - main interface."""

from typing import Any, Optional, List

from .wallet import Wallet
from .x402 import X402Client, AsyncX402Client
from .models import Service, Balance, Limits, PaymentResult, TokenSymbol
from .exceptions import InsufficientFunds, LimitExceeded, PaymentError


class MoltsPay:
    """
    MoltsPay client for paying for agent services.
    
    Usage:
        from moltspay import MoltsPay
        
        # Initialize (auto-creates wallet if not exists)
        client = MoltsPay()
        
        # Pay for a service
        result = client.pay(
            "https://juai8.com/zen7",
            "text-to-video",
            prompt="a cat dancing"
        )
        print(result.result)
    """
    
    def __init__(
        self,
        wallet_path: Optional[str] = None,
        private_key: Optional[str] = None,
        chain: str = "base",
        timeout: float = 60.0,
    ):
        """
        Initialize MoltsPay client.
        
        Args:
            wallet_path: Path to wallet file (default: ~/.moltspay/wallet.json)
            private_key: Private key (if provided, ignores wallet_path)
            chain: Blockchain network ("base" or "base_sepolia")
            timeout: HTTP timeout in seconds
        """
        self._wallet = Wallet(
            wallet_path=wallet_path,
            private_key=private_key,
            chain=chain,
        )
        self._x402 = X402Client(timeout=timeout)
        self._chain = chain
    
    @property
    def address(self) -> str:
        """Get wallet address."""
        return self._wallet.address
    
    def discover(self, service_url: str) -> List[Service]:
        """
        Discover available services from a provider.
        
        Args:
            service_url: Base URL of the service provider
        
        Returns:
            List of available services
        """
        return self._x402.discover_services(service_url)
    
    def balance(self) -> Balance:
        """
        Get wallet balance.
        
        Note: This requires RPC call. For now returns placeholder.
        TODO: Implement actual balance check via RPC.
        """
        # TODO: Query actual balance from chain
        return Balance(
            address=self._wallet.address,
            usdc=0.0,  # Placeholder
            usdt=0.0,  # Placeholder
            eth=0.0,   # Placeholder
            chain=self._chain,
        )
    
    def limits(self) -> Limits:
        """Get current spending limits."""
        return self._wallet.limits
    
    def set_limits(self, max_per_tx: float = None, max_per_day: float = None):
        """
        Update spending limits.
        
        Args:
            max_per_tx: Maximum amount per transaction
            max_per_day: Maximum daily spending
        """
        self._wallet.set_limits(max_per_tx=max_per_tx, max_per_day=max_per_day)
    
    def pay(
        self,
        service_url: str,
        service_id: str,
        token: str = "USDC",
        **params,
    ) -> PaymentResult:
        """
        Pay for and call a service.
        
        Args:
            service_url: Base URL of the service provider
            service_id: Service ID to call
            token: Token to pay with ("USDC" or "USDT", default: "USDC")
            **params: Service parameters
        
        Returns:
            PaymentResult with service response
        
        Raises:
            InsufficientFunds: Not enough balance
            LimitExceeded: Transaction exceeds limits
            PaymentError: Payment or service failed
        """
        # Normalize token
        token = token.upper()
        if token not in ("USDC", "USDT"):
            raise PaymentError(f"Unsupported token: {token}. Use USDC or USDT.")
        
        # USDT requires gas for on-chain approval (no EIP-2612 support)
        if token == "USDT":
            bal = self.balance()
            if bal.native < 0.0001:
                raise PaymentError(
                    f"USDT requires ETH for gas (~$0.01 on Base). "
                    f"Your ETH balance: {bal.native:.6f} ETH. "
                    f"Please add a small amount of ETH to your wallet, or use USDC (gasless)."
                )
            import warnings
            warnings.warn("USDT requires gas (~$0.01). USDC is gasless and recommended.", UserWarning)
        
        # Discover service to get price
        services = self.discover(service_url)
        service = next((s for s in services if s.id == service_id), None)
        
        if not service:
            raise PaymentError(f"Service not found: {service_id}")
        
        # Check if token is accepted
        accepted = service.accepts
        if token not in accepted:
            raise PaymentError(f"Token {token} not accepted. Accepted: {', '.join(accepted)}")
        
        # Check limits
        ok, error = self._wallet.check_limits(service.price)
        if not ok:
            if "per-transaction" in error:
                raise LimitExceeded("per_tx", self._wallet.limits.max_per_tx, service.price)
            else:
                raise LimitExceeded("daily", self._wallet.limits.max_per_day, service.price)
        
        try:
            # Execute x402 payment flow
            result = self._x402.pay_and_call(
                service_url,
                service_id,
                params,
                self._wallet._account,
                token=token,
            )
            
            # Record spend on success
            self._wallet.record_spend(service.price)
            
            return PaymentResult(
                success=True,
                amount=service.price,
                token=token,
                service_id=service_id,
                result=result,
            )
            
        except PaymentError:
            raise
        except Exception as e:
            return PaymentResult(
                success=False,
                amount=service.price,
                token=token,
                service_id=service_id,
                error=str(e),
            )
    
    def close(self):
        """Close the client."""
        self._x402.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


class AsyncMoltsPay:
    """
    Async version of MoltsPay client.
    
    Usage:
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
    """
    
    def __init__(
        self,
        wallet_path: Optional[str] = None,
        private_key: Optional[str] = None,
        chain: str = "base",
        timeout: float = 60.0,
    ):
        self._wallet = Wallet(
            wallet_path=wallet_path,
            private_key=private_key,
            chain=chain,
        )
        self._x402 = AsyncX402Client(timeout=timeout)
        self._chain = chain
    
    @property
    def address(self) -> str:
        return self._wallet.address
    
    async def discover(self, service_url: str) -> List[Service]:
        """Discover available services."""
        return await self._x402.discover_services(service_url)
    
    def balance(self) -> Balance:
        """Get wallet balance (sync - no RPC call yet)."""
        return Balance(
            address=self._wallet.address,
            usdc=0.0,
            usdt=0.0,
            eth=0.0,
            chain=self._chain,
        )
    
    def limits(self) -> Limits:
        """Get spending limits."""
        return self._wallet.limits
    
    def set_limits(self, max_per_tx: float = None, max_per_day: float = None):
        """Update spending limits."""
        self._wallet.set_limits(max_per_tx=max_per_tx, max_per_day=max_per_day)
    
    async def pay(
        self,
        service_url: str,
        service_id: str,
        token: str = "USDC",
        **params,
    ) -> PaymentResult:
        """
        Pay for and call a service (async).
        
        Args:
            service_url: Base URL of the service provider
            service_id: Service ID to call
            token: Token to pay with ("USDC" or "USDT", default: "USDC")
            **params: Service parameters
        """
        # Normalize token
        token = token.upper()
        if token not in ("USDC", "USDT"):
            raise PaymentError(f"Unsupported token: {token}. Use USDC or USDT.")
        
        # USDT requires gas for on-chain approval (no EIP-2612 support)
        if token == "USDT":
            bal = await self.balance()
            if bal.native < 0.0001:
                raise PaymentError(
                    f"USDT requires ETH for gas (~$0.01 on Base). "
                    f"Your ETH balance: {bal.native:.6f} ETH. "
                    f"Please add a small amount of ETH to your wallet, or use USDC (gasless)."
                )
            import warnings
            warnings.warn("USDT requires gas (~$0.01). USDC is gasless and recommended.", UserWarning)
        
        services = await self.discover(service_url)
        service = next((s for s in services if s.id == service_id), None)
        
        if not service:
            raise PaymentError(f"Service not found: {service_id}")
        
        # Check if token is accepted
        accepted = service.accepts
        if token not in accepted:
            raise PaymentError(f"Token {token} not accepted. Accepted: {', '.join(accepted)}")
        
        ok, error = self._wallet.check_limits(service.price)
        if not ok:
            if "per-transaction" in error:
                raise LimitExceeded("per_tx", self._wallet.limits.max_per_tx, service.price)
            else:
                raise LimitExceeded("daily", self._wallet.limits.max_per_day, service.price)
        
        try:
            result = await self._x402.pay_and_call(
                service_url,
                service_id,
                params,
                self._wallet._account,
                token=token,
            )
            
            self._wallet.record_spend(service.price)
            
            return PaymentResult(
                success=True,
                amount=service.price,
                token=token,
                service_id=service_id,
                result=result,
            )
            
        except PaymentError:
            raise
        except Exception as e:
            return PaymentResult(
                success=False,
                amount=service.price,
                token=token,
                service_id=service_id,
                error=str(e),
            )
    
    async def close(self):
        """Close the client."""
        await self._x402.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
