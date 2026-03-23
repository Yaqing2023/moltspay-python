"""
Solana wallet management.

Handles ed25519 keypair generation and storage for Solana chains.
Stored separately from EVM wallet in wallet-solana.json.
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False

from .exceptions import WalletError

DEFAULT_SOLANA_WALLET_PATH = Path.home() / ".moltspay" / "wallet-solana.json"


@dataclass
class SolanaWalletData:
    """Solana wallet data."""
    public_key: str
    secret_key: str  # Base58 encoded
    created_at: str


def check_solana_available():
    """Check if Solana dependencies are installed."""
    if not SOLANA_AVAILABLE:
        raise WalletError(
            "Solana support requires 'solders' package. "
            "Install with: pip install solders"
        )


def generate_solana_keypair() -> Tuple[str, str]:
    """
    Generate a new Solana ed25519 keypair.
    
    Returns:
        Tuple of (public_key, secret_key) as base58 strings
    """
    check_solana_available()
    
    keypair = Keypair()
    public_key = str(keypair.pubkey())
    # Secret key as base58
    secret_key = base64.b64encode(bytes(keypair)).decode('utf-8')
    
    return public_key, secret_key


def load_solana_wallet(
    wallet_path: Optional[str] = None
) -> Optional[SolanaWalletData]:
    """
    Load Solana wallet from file.
    
    Args:
        wallet_path: Path to wallet file (default: ~/.moltspay/wallet-solana.json)
    
    Returns:
        SolanaWalletData if found, None otherwise
    """
    path = Path(wallet_path) if wallet_path else DEFAULT_SOLANA_WALLET_PATH
    
    if not path.exists():
        return None
    
    try:
        with open(path) as f:
            data = json.load(f)
        
        return SolanaWalletData(
            public_key=data["publicKey"],
            secret_key=data["secretKey"],
            created_at=data.get("createdAt", ""),
        )
    except Exception as e:
        raise WalletError(f"Failed to load Solana wallet: {e}")


def save_solana_wallet(
    wallet_data: SolanaWalletData,
    wallet_path: Optional[str] = None,
) -> Path:
    """
    Save Solana wallet to file.
    
    Args:
        wallet_data: Wallet data to save
        wallet_path: Path to wallet file
    
    Returns:
        Path where wallet was saved
    """
    path = Path(wallet_path) if wallet_path else DEFAULT_SOLANA_WALLET_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "publicKey": wallet_data.public_key,
        "secretKey": wallet_data.secret_key,
        "createdAt": wallet_data.created_at,
    }
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Secure permissions
    os.chmod(path, 0o600)
    
    return path


def create_solana_wallet(
    wallet_path: Optional[str] = None,
) -> SolanaWalletData:
    """
    Create a new Solana wallet.
    
    Args:
        wallet_path: Path to save wallet (default: ~/.moltspay/wallet-solana.json)
    
    Returns:
        Created wallet data
    """
    check_solana_available()
    
    public_key, secret_key = generate_solana_keypair()
    
    wallet_data = SolanaWalletData(
        public_key=public_key,
        secret_key=secret_key,
        created_at=datetime.utcnow().isoformat() + "Z",
    )
    
    save_solana_wallet(wallet_data, wallet_path)
    
    return wallet_data


def get_solana_keypair(wallet_data: SolanaWalletData) -> "Keypair":
    """
    Get Solana Keypair object from wallet data.
    
    Supports both base58 (Node.js SDK) and base64 (Python SDK) encoded keys.
    
    Args:
        wallet_data: Wallet data with secret key
    
    Returns:
        solders.Keypair object
    """
    check_solana_available()
    
    secret_key = wallet_data.secret_key
    
    # Try base58 first (Node.js SDK format)
    try:
        from solders.keypair import Keypair
        # base58 decode - the Node.js SDK stores as base58
        import base58
        secret_bytes = base58.b58decode(secret_key)
        if len(secret_bytes) == 64:
            return Keypair.from_bytes(secret_bytes)
    except Exception:
        pass
    
    # Fallback to base64 (Python SDK format)
    try:
        secret_bytes = base64.b64decode(secret_key)
        if len(secret_bytes) == 64:
            return Keypair.from_bytes(secret_bytes)
    except Exception:
        pass
    
    raise WalletError(
        f"Failed to decode Solana secret key. "
        f"Expected 64 bytes in base58 or base64 format, got {len(secret_key)} chars."
    )


class SolanaWallet:
    """Solana wallet wrapper for MoltsPay."""
    
    def __init__(
        self,
        wallet_path: Optional[str] = None,
        create_if_missing: bool = True,
    ):
        """
        Initialize Solana wallet.
        
        Args:
            wallet_path: Path to wallet file
            create_if_missing: Create wallet if it doesn't exist
        """
        check_solana_available()
        
        self._path = Path(wallet_path) if wallet_path else DEFAULT_SOLANA_WALLET_PATH
        self._data: Optional[SolanaWalletData] = None
        self._keypair: Optional[Keypair] = None
        
        # Try to load existing wallet
        self._data = load_solana_wallet(str(self._path))
        
        if self._data is None and create_if_missing:
            self._data = create_solana_wallet(str(self._path))
        
        if self._data:
            self._keypair = get_solana_keypair(self._data)
    
    @property
    def exists(self) -> bool:
        """Check if wallet exists."""
        return self._data is not None
    
    @property
    def public_key(self) -> str:
        """Get wallet public key (address)."""
        if not self._data:
            raise WalletError("Solana wallet not initialized")
        return self._data.public_key
    
    @property
    def address(self) -> str:
        """Alias for public_key."""
        return self.public_key
    
    @property
    def keypair(self) -> "Keypair":
        """Get the Keypair object for signing."""
        if not self._keypair:
            raise WalletError("Solana wallet not initialized")
        return self._keypair
    
    def sign(self, message: bytes) -> bytes:
        """
        Sign a message.
        
        Args:
            message: Message bytes to sign
        
        Returns:
            Signature bytes
        """
        if not self._keypair:
            raise WalletError("Solana wallet not initialized")
        
        from solders.signature import Signature
        sig = self._keypair.sign_message(message)
        return bytes(sig)
