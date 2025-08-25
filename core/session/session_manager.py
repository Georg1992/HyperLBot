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

from core.data.realtime_data_store import realtime_data_store
from core.data.database_manager import database_manager


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
                
                # Reset data store to fresh session state
                realtime_data_store.reset_session(session_id, strategy, initial_balance)
                
                # Initialize session in data store
                session_data = {
                    "session_id": session_id,
                    "start_time": datetime.now().isoformat(),
                    "status": "ACTIVE",
                    "strategy": strategy,
                    "initial_balance": initial_balance,
                    "current_balance": initial_balance,
                    "balance_change": 0.0,
                    "balance_change_pct": 0.0,
                    "last_balance_update": datetime.now().isoformat(),
                    "bot_version": "Advanced Trading Bot v4.0",
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_pnl": 0.0,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": 0.0,
                    "max_drawdown": 0.0,
                    "win_rate": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "sharpe_ratio": 0.0,
                    "total_volume": 0.0,
                    "total_fees": 0.0
                }
                
                realtime_data_store.update_session_data(session_data)
                
                # Save session to database
                database_manager.save_session({
                    "session_id": session_id,
                    "start_time": session_data["start_time"],
                    "strategy": strategy,
                    "initial_balance": initial_balance,
                    "final_balance": initial_balance,  # Will be updated on close
                    "balance_change": 0.0,
                    "balance_change_pct": 0.0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "status": "ACTIVE"
                })
                
                self.current_session_id = session_id
                
                # Add startup activity
                realtime_data_store.add_activity_record({
                    "message": f"🚀 Trading session started - {strategy} strategy initialized",
                    "type": "session_start",
                    "level": "SUCCESS"
                })
                
                # Initialize basic market data
                realtime_data_store.update_market_data({
                    "current_price": 0,
                    "trend": "INITIALIZING",
                    "market_condition": "STARTING",
                    "data_source": "session_initialization"
                })
                
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
                
                # Get current session data
                session_data = realtime_data_store.get_session_data()
                
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
                
                # Update session in data store
                realtime_data_store.update_session_data(session_data)
                realtime_data_store.set_session_status("COMPLETED")
                
                # Save final session state to database
                database_manager.save_session({
                    "session_id": session_data["session_id"],
                    "start_time": session_data.get("start_time"),
                    "end_time": end_time,
                    "strategy": session_data.get("strategy"),
                    "initial_balance": session_data.get("initial_balance"),
                    "final_balance": session_data.get("current_balance"),
                    "balance_change": session_data.get("balance_change"),
                    "balance_change_pct": session_data.get("balance_change_pct"),
                    "total_trades": session_data.get("total_trades"),
                    "winning_trades": session_data.get("winning_trades"),
                    "losing_trades": session_data.get("losing_trades"),
                    "status": "COMPLETED"
                })
                
                # Add completion activity
                realtime_data_store.add_activity_record({
                    "message": f"🏁 Trading session completed - {session_data.get('duration_minutes', 0):.1f} minutes",
                    "type": "session_end",
                    "level": "SUCCESS"
                })
                
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
        """Close any orphaned sessions in database"""
        try:
            # Get recent sessions from database
            recent_sessions = database_manager.get_recent_sessions(10)
            
            orphaned_count = 0
            for session in recent_sessions:
                if session.get("status") == "ACTIVE":
                    # Check if session is old (more than 2 hours)
                    if session.get("start_time"):
                        start_time = datetime.fromisoformat(session["start_time"])
                        age_hours = (datetime.now() - start_time).total_seconds() / 3600
                        
                        if age_hours > 2:  # Session older than 2 hours
                            # Mark as orphaned
                            orphaned_session = session.copy()
                            orphaned_session["status"] = "ORPHANED"
                            orphaned_session["end_time"] = datetime.now().isoformat()
                            
                            database_manager.save_session(orphaned_session)
                            orphaned_count += 1
                            
                            logger.info(f"   Closed orphaned session: {session['session_id']}")
            
            if orphaned_count > 0:
                logger.success(f"✅ Closed {orphaned_count} orphaned sessions")
                
        except Exception as e:
            logger.error(f"Error closing orphaned sessions: {e}")
    
    def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current session"""
        with self.session_lock:
            if not self.current_session_id:
                return None
            
            try:
                session_data = realtime_data_store.get_session_data()
                return session_data
                
            except Exception as e:
                logger.error(f"Error getting session info: {e}")
                return None
    
    def is_session_active(self) -> bool:
        """Check if there's an active session"""
        return self.current_session_id is not None
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get current session statistics"""
        with self.session_lock:
            try:
                if not self.current_session_id:
                    return {"error": "No active session"}
                
                session_data = realtime_data_store.get_session_data()
                recent_trades = realtime_data_store.get_recent_trades(50)
                
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
                
                # Update balance in data store
                realtime_data_store.update_balance(new_balance, reason)
                
                # Add activity record
                session_data = realtime_data_store.get_session_data()
                balance_change = session_data.get("balance_change", 0)
                
                realtime_data_store.add_activity_record({
                    "message": f"💰 Balance updated: ${new_balance:.2f} ({balance_change:+.2f}) - {reason}",
                    "type": "balance_update",
                    "level": "INFO"
                })
                
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
                
                # Add trade to data store
                realtime_data_store.add_trade_record(trade_data)
                
                # Save trade to database
                database_manager.save_trade(trade_data)
                
                # Update session statistics
                session_data = realtime_data_store.get_session_data()
                
                # Add trade activity
                side = trade_data.get("side", "UNKNOWN")
                pnl = trade_data.get("pnl", 0)
                pnl_pct = trade_data.get("pnl_pct", 0)
                
                realtime_data_store.add_activity_record({
                    "message": f"📊 Trade completed: {side} {pnl:+.2f} ({pnl_pct*100:+.1f}%)",
                    "type": "trade_completed",
                    "level": "SUCCESS" if trade_data.get("was_profitable", False) else "WARNING"
                })
                
                logger.info(f"📊 Trade added to session: {trade_data.get('trade_id')}")
                
            except Exception as e:
                logger.error(f"Error adding trade to session: {e}")


# Global instance (singleton)
session_manager = SessionManager()