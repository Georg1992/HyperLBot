#!/usr/bin/env python3
"""
Simulated Account Manager
Handles creation, loading, and persistence of simulated trading accounts
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

class SimulatedAccountManager:
    """Manages simulated trading account data and persistence"""
    
    def __init__(self):
        self.account_file = "data/sessions/simulated_account.json"
        self.account_data = None
    
    def account_exists(self) -> bool:
        """Check if a simulated account file exists"""
        return os.path.exists(self.account_file)
    
    def create_account(self, initial_balance: float) -> Dict[str, Any]:
        """Create a new simulated account with initial balance"""
        account_data = {
            "account_id": f"sim_account_{int(time.time())}",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "initial_balance": initial_balance,
            "current_balance": initial_balance,
            "total_deposits": initial_balance,
            "total_withdrawals": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "open_positions": [],
            "trade_history": [],
            "session_history": [],
            "account_status": "active"
        }
        
        self.account_data = account_data
        self._save_account()
        logger.success(f"✅ Created new simulated account with balance: ${initial_balance:.2f}")
        return account_data
    
    def load_account(self) -> Optional[Dict[str, Any]]:
        """Load existing simulated account data"""
        try:
            if not self.account_exists():
                return None
            
            with open(self.account_file, 'r') as f:
                self.account_data = json.load(f)
            
            logger.success(f"✅ Loaded existing simulated account (Balance: ${self.account_data['current_balance']:.2f})")
            return self.account_data
            
        except Exception as e:
            logger.error(f"❌ Error loading account: {e}")
            return None
    
    def save_account(self):
        """Save current account data to file"""
        if self.account_data:
            self._save_account()
    
    def _save_account(self):
        """Internal method to save account data"""
        try:
            self.account_data["last_updated"] = datetime.now().isoformat()
            with open(self.account_file, 'w') as f:
                json.dump(self.account_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Error saving account: {e}")
    
    def update_balance(self, new_balance: float, pnl_change: float = 0.0):
        """Update account balance and PnL"""
        if self.account_data:
            old_balance = self.account_data["current_balance"]
            self.account_data["current_balance"] = new_balance
            self.account_data["total_pnl"] += pnl_change
            
            if pnl_change > 0:
                self.account_data["realized_pnl"] += pnl_change
            else:
                self.account_data["unrealized_pnl"] += pnl_change
            
            logger.info(f"💰 Account balance updated: ${old_balance:.2f} → ${new_balance:.2f} (PnL: ${pnl_change:.2f})")
            self._save_account()
    
    def add_trade(self, trade_data: Dict[str, Any]):
        """Add a completed trade to account history"""
        if self.account_data:
            self.account_data["total_trades"] += 1
            
            if trade_data.get("pnl", 0) > 0:
                self.account_data["winning_trades"] += 1
            else:
                self.account_data["losing_trades"] += 1
            
            self.account_data["trade_history"].append({
                **trade_data,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 100 trades to prevent file bloat
            if len(self.account_data["trade_history"]) > 100:
                self.account_data["trade_history"] = self.account_data["trade_history"][-100:]
            
            self._save_account()
    
    def add_session(self, session_data: Dict[str, Any]):
        """Add session data to account history"""
        if self.account_data:
            self.account_data["session_history"].append({
                **session_data,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 50 sessions
            if len(self.account_data["session_history"]) > 50:
                self.account_data["session_history"] = self.account_data["session_history"][-50:]
            
            self._save_account()
    
    def update_open_positions(self, positions: list):
        """Update open positions in account"""
        if self.account_data:
            self.account_data["open_positions"] = positions
            self._save_account()
    
    def reset_account(self) -> bool:
        """Delete existing account file to allow creation of new account"""
        try:
            if self.account_exists():
                os.remove(self.account_file)
                self.account_data = None
                logger.success("✅ Existing account deleted - ready for new account creation")
                return True
            else:
                logger.warning("⚠️ No existing account to reset")
                return False
        except Exception as e:
            logger.error(f"❌ Error resetting account: {e}")
            return False
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get a summary of account performance"""
        if not self.account_data:
            return {}
        
        total_trades = self.account_data["total_trades"]
        win_rate = (self.account_data["winning_trades"] / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "account_id": self.account_data["account_id"],
            "current_balance": self.account_data["current_balance"],
            "initial_balance": self.account_data["initial_balance"],
            "total_pnl": self.account_data["total_pnl"],
            "total_trades": total_trades,
            "winning_trades": self.account_data["winning_trades"],
            "losing_trades": self.account_data["losing_trades"],
            "win_rate": win_rate,
            "open_positions_count": len(self.account_data["open_positions"]),
            "created_at": self.account_data["created_at"],
            "last_updated": self.account_data["last_updated"]
        }

# Global instance
account_manager = SimulatedAccountManager()
