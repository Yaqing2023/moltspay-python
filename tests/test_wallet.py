"""Tests for wallet module."""

import os
import json
import tempfile
from pathlib import Path

import pytest

from moltspay.wallet import Wallet, create_wallet, load_wallet, DEFAULT_WALLET_PATH
from moltspay.exceptions import WalletError


class TestWallet:
    """Test Wallet class."""
    
    def test_create_new_wallet(self, tmp_path):
        """Test creating a new wallet."""
        wallet_path = tmp_path / "wallet.json"
        
        wallet = Wallet(wallet_path=str(wallet_path))
        
        assert wallet.address.startswith("0x")
        assert len(wallet.address) == 42
        assert wallet_path.exists()
    
    def test_load_existing_wallet(self, tmp_path):
        """Test loading an existing wallet."""
        wallet_path = tmp_path / "wallet.json"
        
        # Create first
        wallet1 = Wallet(wallet_path=str(wallet_path))
        address1 = wallet1.address
        
        # Load second time
        wallet2 = Wallet(wallet_path=str(wallet_path))
        
        assert wallet2.address == address1
    
    def test_wallet_from_private_key(self):
        """Test creating wallet from private key."""
        # Known test key (DO NOT use in production!)
        test_key = "0x" + "1" * 64
        
        wallet = Wallet(private_key=test_key)
        
        assert wallet.address.startswith("0x")
    
    def test_limits(self, tmp_path):
        """Test spending limits."""
        wallet_path = tmp_path / "wallet.json"
        wallet = Wallet(wallet_path=str(wallet_path))
        
        # Default limits
        limits = wallet.limits
        assert limits.max_per_tx == 10
        assert limits.max_per_day == 100
        
        # Update limits
        wallet.set_limits(max_per_tx=50, max_per_day=500)
        limits = wallet.limits
        assert limits.max_per_tx == 50
        assert limits.max_per_day == 500
    
    def test_check_limits(self, tmp_path):
        """Test limit checking."""
        wallet_path = tmp_path / "wallet.json"
        wallet = Wallet(wallet_path=str(wallet_path))
        wallet.set_limits(max_per_tx=10, max_per_day=100)
        
        # Within limits
        ok, error = wallet.check_limits(5)
        assert ok
        assert error is None
        
        # Exceeds per-tx
        ok, error = wallet.check_limits(15)
        assert not ok
        assert "per-transaction" in error
    
    def test_record_spend(self, tmp_path):
        """Test spending tracking."""
        wallet_path = tmp_path / "wallet.json"
        wallet = Wallet(wallet_path=str(wallet_path))
        wallet.set_limits(max_per_tx=100, max_per_day=50)
        
        wallet.record_spend(20)
        wallet.record_spend(15)
        
        limits = wallet.limits
        assert limits.spent_today == 35
        
        # Should fail - would exceed daily
        ok, error = wallet.check_limits(20)
        assert not ok
        assert "daily" in error.lower()


class TestWalletFunctions:
    """Test module-level functions."""
    
    def test_create_wallet_new(self, tmp_path):
        """Test create_wallet function."""
        wallet_path = tmp_path / "new_wallet.json"
        
        wallet = create_wallet(wallet_path=str(wallet_path))
        
        assert wallet.address.startswith("0x")
        assert wallet_path.exists()
    
    def test_create_wallet_exists_error(self, tmp_path):
        """Test create_wallet fails if exists."""
        wallet_path = tmp_path / "wallet.json"
        
        # Create first
        create_wallet(wallet_path=str(wallet_path))
        
        # Should fail second time
        with pytest.raises(WalletError):
            create_wallet(wallet_path=str(wallet_path))
    
    def test_load_wallet_not_found(self, tmp_path):
        """Test load_wallet fails if not exists."""
        wallet_path = tmp_path / "nonexistent.json"
        
        with pytest.raises(WalletError):
            load_wallet(wallet_path=str(wallet_path))
