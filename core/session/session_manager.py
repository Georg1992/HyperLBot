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
                
                # Initialize basic market data in SimpleRTM
                simple_rtm.update_market({
                    "current_price": 0,
                    "trend": "INITIALIZING",
                    "rsi": 50.0,
                    "volume_depth": 0.0
                })
                
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
                
                # Get current session data from SimpleRTM
                session_data = simple_rtm.get_dashboard_data()["session"]
                
                # Mark session as completed
                end_time = datetime.now().isoformat()
                session_data["status"] = "COMPLETED"
                session_data["end_time"] = end_time
                
                # Calculate duration
                if "start_time" in session_data:
                    start_time = datetime.fromisoformat(session_data["start_time"])
                    end_time_dt = datetime.now()
                    duration = end_time_dt - start_time
                    session_data["duration_minutes"] = round(duration.total_seconds() / 60, 2)
                
                # Update session in SimpleRTM
                simple_rtm.update_session(session_data)
                
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
                session_data = simple_rtm.get_dashboard_data()["session"]
                return session_data
                
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
                
                session_data = simple_rtm.get_dashboard_data()["session"]
                recent_trades = simple_rtm.get_dashboard_data()["trades"]
                
                # Calculate additional statistics
                if recent_trades:
                    profitable_trades = [t for t in recent_trades if t.get("was_profitable", False)]
                    losing_trades = [t for t in recent_trades if not t.get("was_profitable", False)]
                    
                    total_pnl = sum(t.get("pnl", 0) for t in recent_trades)
                    avg_win = sum(t.get("pnl", 0) for t in profitable_trades) / len(profitable_trades) if profitable_trades else 0
                    avg_loss = sum(t.get("pnl", 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
                    
                    # Update session with calculated stats
                    session_data["total_pnl"] = total_pnl
                    session_data["avg_win"] = avg_win
                    session_data["avg_loss"] = avg_loss
                    session_data["win_rate"] = (len(profitable_trades) / len(recent_trades) * 100) if recent_trades else 0
                
                return session_data
                
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
                
                # Add activity record to SimpleRTM
                session_data = self.get_current_session_data()
                balance_change = new_balance - session_data.get("initial_balance", 0)
                
                simple_rtm.add_activity(f"💰 Balance updated: ${new_balance:.2f} ({balance_change:+.2f}) - {reason}", "INFO", "account")
                
                logger.debug(f"💰 Session balance updated: ${new_balance:.2f} - {reason}")
                
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
                
                # Update session statistics
                session_data = simple_rtm.get_dashboard_data()["session"]
                
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