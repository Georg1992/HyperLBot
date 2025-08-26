#!/usr/bin/env python3
"""
Session Manager
Handles trading session lifecycle management
Single Responsibility: Session lifecycle and state management
"""

import time
import threading
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime

from core.data.simple_rtm import simple_rtm


class SessionManager:
    """
    Manages trading session lifecycle
    Single Responsibility: Session creation, management, and cleanup
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for session management"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.session_lock = threading.RLock()
        self.current_session_id = None
        
        logger.success("📅 Session Manager initialized")
    
    def start_session(self, session_id: str = None, strategy: str = "standard", initial_balance: float = 120.0) -> str:
        """Start a new trading session"""
        with self.session_lock:
            try:
                # Generate session ID if not provided
                if session_id is None:
                    session_id = f"session_{int(time.time())}"
                
                # Close any existing session first
                self._close_existing_session()
                
                # Session data is managed by SessionManager (source of truth)
                # Account data is managed by AccountManager (source of truth)
                # SimpleRTM will read from them automatically
                
                self.current_session_id = session_id
                
                # Store session data
                self.current_session_data = {
                    "session_id": session_id,
                    "start_time": datetime.now().isoformat(),
                    "status": "ACTIVE",
                    "strategy": strategy,
                    "initial_balance": initial_balance,
                    "current_balance": initial_balance,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_pnl": 0.0,
                    "win_rate": 0.0
                }
                
                # Add startup activity to SimpleRTM
                simple_rtm.add_activity(f"🚀 Trading session started - {strategy} strategy initialized", "SUCCESS", "session")
                
                # DO NOT initialize market data - it should be updated by the bot during operation
                # Market data is real-time and should not be reset when starting sessions
                
                # Session data is managed by SessionManager (source of truth)
                # SimpleRTM reads from SessionManager automatically
                
                logger.success(f"🚀 Trading session started: {session_id} ({strategy})")
                return session_id
                
            except Exception as e:
                logger.error(f"Error starting session: {e}")
                raise
    
    def _close_existing_session(self):
        """Close any existing active session"""
        try:
            if self.current_session_id:
                logger.info(f"🔄 Closing existing session: {self.current_session_id}")
                self.end_session()
                
            # Also check for orphaned sessions in database
            self._close_orphaned_sessions()
            
        except Exception as e:
            logger.error(f"Error closing existing session: {e}")
    
    def end_session(self) -> bool:
        """End the current trading session"""
        with self.session_lock:
            try:
                if not self.current_session_id:
                    logger.warning("⚠️ No active session to close")
                    return False
                
                # Use internal session data to avoid circular dependency
                if hasattr(self, 'current_session_data') and self.current_session_data:
                    session_data = self.current_session_data.copy()
                else:
                    session_data = {
                        "session_id": self.current_session_id,
                        "start_time": datetime.now().isoformat(),
                        "status": "COMPLETED",
                        "strategy": "unknown"
                    }
                
                # Mark session as completed
                end_time = datetime.now().isoformat()
                session_data["status"] = "COMPLETED"
                session_data["end_time"] = end_time
                
                # Calculate duration
                if "start_time" in session_data:
                    try:
                        start_time = datetime.fromisoformat(session_data["start_time"])
                        end_time_dt = datetime.now()
                        duration = end_time_dt - start_time
                        session_data["duration_minutes"] = round(duration.total_seconds() / 60, 2)
                    except:
                        session_data["duration_minutes"] = 0.0
                
                # Update internal session data
                self.current_session_data = session_data
                
                # Add completion activity
                simple_rtm.add_activity(f"🏁 Trading session completed - {session_data.get('duration_minutes', 0):.1f} minutes", "SUCCESS", "session")
                
                logger.success(f"✅ Session ended: {self.current_session_id}")
                logger.info(f"   Duration: {session_data.get('duration_minutes', 0):.1f} minutes")
                logger.info(f"   Final Balance: ${session_data.get('current_balance', 0):.2f}")
                logger.info(f"   Total Trades: {session_data.get('total_trades', 0)}")
                
                self.current_session_id = None
                return True
                
            except Exception as e:
                logger.error(f"Error ending session: {e}")
                return False
    
    def _close_orphaned_sessions(self):
        """Close any orphaned sessions - simplified for SimpleRTM"""
        try:
            # SimpleRTM handles session cleanup automatically
            # No need for complex database operations
            logger.debug("✅ Session cleanup handled by SimpleRTM")
                
        except Exception as e:
            logger.error(f"Error in session cleanup: {e}")
    
    def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current session"""
        with self.session_lock:
            if not self.current_session_id:
                return None
            
            try:
                return self.current_session_data
                
            except Exception as e:
                logger.error(f"Error getting session info: {e}")
                return None
    
    def get_current_session_data(self) -> Dict[str, Any]:
        """Get current session data for dashboard"""
        with self.session_lock:
            try:
                if not self.current_session_id or not hasattr(self, 'current_session_data'):
                    return {
                        "session_id": "no_session",
                        "start_time": datetime.now().isoformat(),
                        "status": "INACTIVE",
                        "strategy": "none",
                        "initial_balance": 0.0,
                        "current_balance": 0.0,
                        "balance_change": 0.0,
                        "balance_change_pct": 0.0,
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0
                    }
                
                return self.current_session_data
                
            except Exception as e:
                logger.error(f"Error getting session data: {e}")
                return {
                    "session_id": "error",
                    "start_time": datetime.now().isoformat(),
                    "status": "ERROR",
                    "strategy": "error",
                    "initial_balance": 0.0,
                    "current_balance": 0.0,
                    "balance_change": 0.0,
                    "balance_change_pct": 0.0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0
                }
    
    def is_session_active(self) -> bool:
        """Check if there's an active session"""
        return self.current_session_id is not None
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get current session statistics"""
        with self.session_lock:
            try:
                if not self.current_session_id:
                    return {"error": "No active session"}
                
                # Return internal session data - no dependency on SimpleRTM
                return self.current_session_data
                
            except Exception as e:
                logger.error(f"Error getting session statistics: {e}")
                return {"error": str(e)}
    
    def update_session_balance(self, new_balance: float, reason: str = "Trade execution"):
        """Update session balance"""
        with self.session_lock:
            try:
                if not self.current_session_id:
                    logger.warning("⚠️ No active session to update balance")
                    return
                
                # Balance updates are handled by AccountManager (source of truth)
                # SimpleRTM will read the updated balance automatically
                
                # Update internal session data
                if hasattr(self, 'current_session_data') and self.current_session_data:
                    self.current_session_data["current_balance"] = new_balance
                    balance_change = new_balance - self.current_session_data.get("initial_balance", 0)
                    self.current_session_data["balance_change"] = balance_change
                    self.current_session_data["balance_change_pct"] = (balance_change / self.current_session_data.get("initial_balance", 1)) * 100
                
                # Add activity record to SimpleRTM
                simple_rtm.add_activity(f"💰 Balance updated: ${new_balance:.2f} ({balance_change:+.2f}) - {reason}", "INFO", "account")
                
        
                
            except Exception as e:
                logger.error(f"Error updating session balance: {e}")
    
    def add_session_trade(self, trade_data: Dict[str, Any]):
        """Add a trade to the current session"""
        with self.session_lock:
            try:
                if not self.current_session_id:
                    logger.warning("⚠️ No active session to add trade")
                    return
                
                # Add trade to SimpleRTM
                simple_rtm.add_trade(trade_data)
                
                # Update internal session data
                if hasattr(self, 'current_session_data') and self.current_session_data:
                    self.current_session_data["total_trades"] = self.current_session_data.get("total_trades", 0) + 1
                    if trade_data.get("was_profitable", False):
                        self.current_session_data["winning_trades"] = self.current_session_data.get("winning_trades", 0) + 1
                    else:
                        self.current_session_data["losing_trades"] = self.current_session_data.get("losing_trades", 0) + 1
                    
                    # Update win rate
                    total_trades = self.current_session_data["total_trades"]
                    winning_trades = self.current_session_data["winning_trades"]
                    self.current_session_data["win_rate"] = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                # Add trade activity
                side = trade_data.get("side", "UNKNOWN")
                pnl = trade_data.get("pnl", 0)
                pnl_pct = trade_data.get("pnl_pct", 0)
                
                simple_rtm.add_activity(f"📊 Trade completed: {side} {pnl:+.2f} ({pnl_pct*100:+.1f}%)", "SUCCESS" if trade_data.get("was_profitable", False) else "WARNING", "trade")
                
                logger.info(f"📊 Trade added to session: {trade_data.get('trade_id')}")
                
            except Exception as e:
                logger.error(f"Error adding trade to session: {e}")
    
    # Session data is managed by SessionManager (source of truth)
    # SimpleRTM reads from SessionManager automatically


# Global instance (singleton)
session_manager = SessionManager()