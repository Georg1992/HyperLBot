#!/usr/bin/env python3
"""
Enhanced Session Manager
Handles trading session lifecycle management
Automatically syncs with SimpleRTM for real-time dashboard updates
Single Responsibility: Session lifecycle and state management
"""

import time
import threading
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime

from core.data.real_time_manager import simple_rtm


class SessionManager:
    """
    Manages trading session lifecycle with RTM integration
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
        
        logger.success("📅 Enhanced Session Manager initialized")
    
    def start_session(self, session_id: str = None, strategy: str = "standard", initial_balance: float = None) -> str:
        from core.constants import MagicNumbers
        if initial_balance is None:
            initial_balance = MagicNumbers.FALLBACK_BALANCE
        """Start a new trading session"""
        with self.session_lock:
            try:
                # Generate session ID if not provided
                if session_id is None:
                    session_id = f"session_{int(time.time())}"
                
                # Close any existing session first (but don't clear RTM yet)
                self._close_existing_session()
                
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
                    "win_rate": 0.0,
                    "balance_change": 0.0,
                    "balance_change_pct": 0.0,
                    "session_time": "0m"  # Pre-calculated session time
                }
                
                # Calculate and update session time before syncing
                self._update_session_time()
                
                # Sync to RTM immediately
                simple_rtm.sync_from_session_manager(self.current_session_data)
                
                # Add startup activity to SimpleRTM
                simple_rtm.add_activity(f"🚀 Trading session started - {strategy} strategy initialized", "SUCCESS", "session")
                
                logger.success(f"🚀 Trading session started: {session_id} ({strategy})")
                return session_id
                
            except Exception as e:
                logger.error(f"Error starting session: {e}")
                raise
    
    def _close_existing_session(self):
        """Close any existing active session"""
        try:
            # Check RTM for any active sessions
            from core.data.real_time_manager import simple_rtm
            rtm_data = simple_rtm.get_data()
            rtm_session = rtm_data.get("session", {})
            
            # Check for ANY existing session (ACTIVE or COMPLETED) that needs cleanup
            if rtm_session.get("session_id") != "no_session" and rtm_session.get("session_id"):
                logger.info(f"🔄 Found existing session in RTM: {rtm_session.get('session_id')}")
                logger.info(f"   Status: {rtm_session.get('status')}")
                logger.info(f"   Balance: ${rtm_session.get('current_balance', 0):.2f}")
                
                # Clear any existing session data to ensure clean start
                simple_rtm.clear_session_data()
                logger.info("🧹 Cleared existing session data for fresh start")
            
            # Close current session if exists
            if self.current_session_id:
                logger.info(f"🔄 Closing existing session: {self.current_session_id}")
                self.end_session()
                
            # Also check for orphaned sessions in database
            self._close_orphaned_sessions()
            
            logger.info("✅ Session cleanup completed - ready for new session")
            
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
                
                # Update final session time
                self._update_session_time()
                
                # Sync to RTM
                simple_rtm.sync_from_session_manager(self.current_session_data)
                
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
    
    def _check_active_session(self, operation_name: str = "operation") -> bool:
        """Check if session is active - simple helper to reduce code duplication"""
        if not self.current_session_id:
            logger.warning(f"⚠️ No active session to {operation_name}")
            return False
        return True
    
    def update_session_balance(self, new_balance: float, reason: str = "Trade execution"):
        """Update session balance"""
        with self.session_lock:
            try:
                if not self._check_active_session("update balance"):
                    return
                
                # Update internal session data
                if hasattr(self, 'current_session_data') and self.current_session_data:
                    self.current_session_data["current_balance"] = new_balance
                    balance_change = new_balance - self.current_session_data.get("initial_balance", 0)
                    self.current_session_data["balance_change"] = balance_change
                    self.current_session_data["balance_change_pct"] = (balance_change / self.current_session_data.get("initial_balance", 1)) * 100
                
                # Update session time before syncing
                self._update_session_time()
                
                # Sync to RTM
                simple_rtm.sync_from_session_manager(self.current_session_data)
                
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
                
                # Update session time before syncing
                self._update_session_time()
                
                # Sync to RTM
                simple_rtm.sync_from_session_manager(self.current_session_data)
                
                # Add trade activity
                side = trade_data.get("side", "UNKNOWN")
                pnl = trade_data.get("pnl", 0)
                pnl_pct = trade_data.get("pnl_pct", 0)
                
                simple_rtm.add_activity(f"📊 Trade completed: {side} {pnl:+.2f} ({pnl_pct*100:+.1f}%)", "SUCCESS" if trade_data.get("was_profitable", False) else "WARNING", "trade")
                
                logger.info(f"📊 Trade added to session: {trade_data.get('trade_id')}")
                
            except Exception as e:
                logger.error(f"Error adding trade to session: {e}")
    
    def _update_session_time(self):
        """Calculate and update session time - SessionManager responsibility, NOT dashboard"""
        try:
            if not hasattr(self, 'current_session_data') or not self.current_session_data:
                return
                
            start_time = self.current_session_data.get("start_time")
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    elapsed = datetime.now() - start_dt
                    total_seconds = elapsed.total_seconds()
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    seconds = int(total_seconds % 60)
                    
                    # More granular time display for better user experience
                    if hours > 0:
                        session_time = f"{hours}h {minutes}m"
                    elif minutes > 0:
                        session_time = f"{minutes}m {seconds}s"
                    else:
                        session_time = f"{seconds}s"
                    
                    self.current_session_data["session_time"] = session_time
                except Exception as e:
                    logger.error(f"Session time calculation error: {e}")
                    self.current_session_data["session_time"] = "0s"
            else:
                self.current_session_data["session_time"] = "0m"
                
        except Exception as e:
            logger.error(f"Error updating session time: {e}")
    
    def update_session_time_if_active(self):
        """Update session time if session is active - called periodically by bot"""
        with self.session_lock:
            try:
                if not self.current_session_id or not hasattr(self, 'current_session_data'):
                    return False
                    
                if self.current_session_data.get("status") != "ACTIVE":
                    return False
                
                # Update session time
                self._update_session_time()
                
                # Sync to RTM
                from core.data.real_time_manager import simple_rtm
                simple_rtm.sync_from_session_manager(self.current_session_data)
                
                return True
                
            except Exception as e:
                logger.error(f"Error updating session time: {e}")
                return False
    
    def coordinate_with_account_data(self):
        """Coordinate session data with current account data for balance consistency"""
        with self.session_lock:
            try:
                if not self.current_session_id:
                    return
                
                # Get current account data for coordination (not overwriting)
                from core.account_manager import account_manager
                account_data = account_manager.get_account_summary()
                
                if account_data and hasattr(self, 'current_session_data'):
                    # Only update balance if account balance differs significantly
                    account_balance = account_data.get("current_balance", 0.0)
                    session_balance = self.current_session_data.get("current_balance", 0.0)
                    
                    # Small tolerance for floating point differences
                    if abs(account_balance - session_balance) > 0.01:
                        logger.info(f"🔄 Coordinating session balance: ${session_balance:.2f} → ${account_balance:.2f}")
                        self.update_session_balance(account_balance, "Account data coordination")
                    
            except Exception as e:
                logger.error(f"Error coordinating with account data: {e}")

# Global instance (singleton)
session_manager = SessionManager()