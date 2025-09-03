#!/usr/bin/env python3
"""
Enhanced Simple RTM - Ultimate Central Data Hub
Single source of truth for all dashboard data
Clear data flow: AccountManager + SessionManager → SimpleRTM → Dashboard
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

class SimpleRTM:
    """Real-Time Manager - Single source of truth for all dashboard data"""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._data_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'temp', 'simple_rtm_data.json')
        
        # Ensure temp directory exists
        os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
        
        # Initialize data structure
        self._data = {
            "session": {},
            "account": {},
            "market_data": {},
            "predictions": [],
            "trades": [],
            "logs": [],
            "data_sources": {
                "account_manager_synced": False,
                "session_manager_synced": False,
                "last_sync_time": datetime.now().isoformat()
            },
            "pressure": {
                "direction": "NEUTRAL",
                "confidence": "50%",
                "strength": 0.5,
                "trend": "NEUTRAL"
            },
            "last_update": datetime.now().isoformat()
        }
        
        # Load existing data if file exists
        self._load_data()
        
        logger.info("🚀 Simple RTM initialized - Central data hub")
    
    def _load_data(self):
        """Load data from file"""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, 'r') as f:
                    loaded_data = json.load(f)
                    self._data.update(loaded_data)
                    logger.debug(f"✅ Loaded existing data from {self._data_file}")
        except Exception as e:
            logger.warning(f"⚠️ Could not load existing data: {e}")
    
    def _save_data(self):
        """Save data to file"""
        try:
            with open(self._data_file, 'w') as f:
                json.dump(self._data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Failed to save data: {e}")
    
    def sync_from_account_manager(self, account_data: Dict[str, Any]):
        """Sync data from AccountManager - PERSISTENT DATA"""
        with self._lock:
            try:
                if account_data:
                    self._data["account"].update({
                        "account_id": account_data.get("account_id"),
                        "current_balance": account_data.get("current_balance", 0.0),
                        "initial_balance": account_data.get("initial_balance", 0.0),
                        "total_pnl": account_data.get("total_pnl", 0.0),
                        "total_trades": account_data.get("total_trades", 0),
                        "winning_trades": account_data.get("winning_trades", 0),
                        "losing_trades": account_data.get("losing_trades", 0),
                        "win_rate": account_data.get("win_rate", 0.0),
                        "open_positions_count": account_data.get("open_positions_count", 0),
                        "created_at": account_data.get("created_at"),
                        "last_updated": datetime.now().isoformat()
                    })
                    
                    # AccountManager only updates account data - SessionManager handles session data
                    # This prevents race conditions and maintains clean data separation
                    
                    self._data["data_sources"]["account_manager_synced"] = True
                    self._data["data_sources"]["last_sync_time"] = datetime.now().isoformat()
                    self._data["timestamp"] = datetime.now().isoformat()
                    self._save_data()
                    
                    # Reduced logging frequency
                    
            except Exception as e:
                logger.error(f"❌ Error syncing from AccountManager: {e}")
    
    def sync_from_session_manager(self, session_data: Dict[str, Any]):
        """Sync data from SessionManager - SESSION DATA"""
        with self._lock:
            try:
                if session_data:
                    self._data["session"].update({
                        "session_id": session_data.get("session_id", "no_session"),
                        "status": session_data.get("status", "INACTIVE"),
                        "start_time": session_data.get("start_time"),
                        "strategy": session_data.get("strategy", "standard"),
                        "current_balance": session_data.get("current_balance", 0.0),
                        "initial_balance": session_data.get("initial_balance", 0.0),
                        "total_trades": session_data.get("total_trades", 0),
                        "winning_trades": session_data.get("winning_trades", 0),
                        "losing_trades": session_data.get("losing_trades", 0),
                        "total_pnl": session_data.get("total_pnl", 0.0),
                        "win_rate": session_data.get("win_rate", 0.0),
                        "balance_change": session_data.get("balance_change", 0.0),
                        "balance_change_pct": session_data.get("balance_change_pct", 0.0),
                        "session_time": session_data.get("session_time", "0m"),
                        "last_updated": datetime.now().isoformat()
                    })
                    
                    self._data["data_sources"]["session_manager_synced"] = True
                    self._data["data_sources"]["last_sync_time"] = datetime.now().isoformat()
                    self._data["timestamp"] = datetime.now().isoformat()
                    self._save_data()
                    
                    # Reduced logging frequency
                    
            except Exception as e:
                logger.error(f"❌ Error syncing from SessionManager: {e}")
    
    def update_market(self, market_data: Dict[str, Any]):
        """Update market data"""
        with self._lock:
            # Update basic market data
            self._data["market_data"].update(market_data)
            
            # Handle trend analysis data separately
            if "trend_analysis" in market_data:
                self._data["market_data"]["trend_analysis"] = market_data["trend_analysis"]
            
            self._data["market_data"]["last_updated"] = datetime.now().isoformat()
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
    
    def update_data_status(self, data_status: Dict[str, Any]):
        """Update data update status"""
        with self._lock:
            self._data["market_data"]["data_update_status"] = data_status
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
    
    def add_activity(self, message: str, level: str = "INFO", source: str = "bot"):
        """Add activity log entry"""
        with self._lock:
            activity = {
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "level": level,
                "source": source
            }
            self._data["logs"].append(activity)
            
            # Keep only last 100 activities
            if len(self._data["logs"]) > 100:
                self._data["logs"] = self._data["logs"][-100:]
            
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
    
    def add_signal(self, signal_data: Dict[str, Any]):
        """Add trading signal"""
        with self._lock:
            signal = {
                "timestamp": datetime.now().isoformat(),
                "type": signal_data.get("type", "UNKNOWN"),
                "confidence": signal_data.get("confidence", 0) or 0,
                "reason": signal_data.get("reason", ""),
                "reasoning": signal_data.get("reasoning", ""),  # Add reasoning field
                "price": signal_data.get("price", 0) or 0,
                # FIXED: Store ALL prediction fields for dashboard display
                "direction": signal_data.get("direction", "UNKNOWN"),  # BUY/SELL
                "entry_price": signal_data.get("entry_price", 0),      # Entry price
                "stop_loss": signal_data.get("stop_loss", 0),          # Stop loss 
                "take_profit": signal_data.get("take_profit", 0),      # Take profit
                "size_btc": signal_data.get("size_btc", 0),
                "size_usd": signal_data.get("size_usd", 0),
                "rsi": signal_data.get("rsi", 50),
                "trend": signal_data.get("trend", "NEUTRAL"),
                "prediction_data": signal_data.get("prediction_data", {})
            }
            self._data["predictions"].append(signal)
            
            # Keep only last 50 signals
            if len(self._data["predictions"]) > 50:
                self._data["predictions"] = self._data["predictions"][-50:]
            
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
            
            confidence = signal_data.get('confidence', 0) or 0
            # Reduced logging frequency
    
    def add_trade(self, trade_data: Dict[str, Any]):
        """Add trade entry"""
        with self._lock:
            trade = {
                "timestamp": datetime.now().isoformat(),
                "side": trade_data.get("side", "UNKNOWN"),
                "size": trade_data.get("size", 0) or 0,
                "price": trade_data.get("price", 0) or 0,
                "pnl": trade_data.get("pnl", 0) or 0,
                "status": trade_data.get("status", "OPEN")
            }
            self._data["trades"].append(trade)
            
            # Keep only last 100 trades
            if len(self._data["trades"]) > 100:
                self._data["trades"] = self._data["trades"][-100:]
            
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
            
            size = trade_data.get('size', 0) or 0
            # Reduced logging frequency
    
    def check_bot_heartbeat(self) -> bool:
        """Check if the bot is still running by monitoring heartbeat file"""
        try:
            heartbeat_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'temp', 'bot_heartbeat.json')
            
            if not os.path.exists(heartbeat_file):
                return False
            
            # Check if heartbeat file is recent (within last 60 seconds)
            file_mtime = os.path.getmtime(heartbeat_file)
            current_time = time.time()
            
            if current_time - file_mtime > 60:  # Bot hasn't updated heartbeat in 60 seconds
                logger.warning("⚠️ Bot heartbeat is stale - bot may have stopped")
                return False
            
            # Read heartbeat data
            with open(heartbeat_file, 'r') as f:
                heartbeat_data = json.load(f)
            
            bot_running = heartbeat_data.get("bot_running", False)
            last_heartbeat = heartbeat_data.get("last_heartbeat", 0)
            
            # Check if heartbeat is recent
            if current_time - last_heartbeat > 60:
                logger.warning("⚠️ Bot heartbeat is stale - bot may have stopped")
                return False
            
            return bot_running
            
        except Exception as e:
            logger.error(f"❌ Error checking bot heartbeat: {e}")
            return False
    
    def auto_cleanup_stale_sessions(self):
        """Automatically cleanup sessions if bot has been stopped for a while"""
        try:
            # Only cleanup if session has been running for more than 60 seconds without bot heartbeat
            # This prevents immediate cleanup of fresh sessions
            session_start_time = self._data["session"].get("start_time")
            if not session_start_time:
                return False
                
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(session_start_time.replace('Z', '+00:00'))
                session_age_seconds = (datetime.now() - start_dt).total_seconds()
                
                # Only cleanup sessions older than 60 seconds with no bot heartbeat
                if session_age_seconds > 60 and not self.check_bot_heartbeat():
                    if self._data["session"]["status"] == "ACTIVE":
                        logger.warning("🛑 Bot has been stopped for >60s - automatically ending stale session")
                        self.clear_session_data()
                        logger.info("✅ Stale session automatically cleaned up")
                        return True
            except:
                # If we can't parse start time, use conservative cleanup
                if not self.check_bot_heartbeat():
                    if self._data["session"]["status"] == "ACTIVE":
                        logger.warning("🛑 Bot heartbeat missing - ending session")
                        self.clear_session_data()
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in auto cleanup: {e}")
            return False

    def get_data(self) -> Dict[str, Any]:
        """Get comprehensive data - Dashboard reads ONLY from this"""
        with self._lock:
            data = self._data.copy()
            
            # Map market_data to market for dashboard compatibility
            if "market_data" in data:
                data["market"] = data["market_data"]
            
            return data
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get session data specifically"""
        with self._lock:
            return self._data["session"].copy()
    
    def get_account_data(self) -> Dict[str, Any]:
        """Get account data specifically"""
        with self._lock:
            return self._data["account"].copy()
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get market data specifically"""
        with self._lock:
            return self._data["market_data"].copy()
    
    def clear_presentation_data(self):
        """Clear only presentation data (logs, predictions, trades) - NOT account/session data or market data"""
        with self._lock:
            self._data["logs"] = []
            self._data["predictions"] = []
            self._data["trades"] = []
            # DO NOT reset market data - it should persist and be updated by the bot
            # Market data is real-time and should not be cleared when starting new sessions
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
            logger.info("🧹 SimpleRTM presentation data cleared (logs, predictions, trades only - market data preserved)")
    
    def clear_session_data(self):
        """Clear session-specific data when session ends"""
        with self._lock:
            self._data["session"] = {
                "session_id": "no_session",
                "status": "INACTIVE",
                "start_time": None,
                "strategy": "standard",
                "current_balance": 0.0,
                "initial_balance": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "balance_change": 0.0,
                "balance_change_pct": 0.0,
                "session_time": "0m",
                "last_updated": None
            }
            self._data["data_sources"]["session_manager_synced"] = False
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
            logger.info("🧹 Session data cleared - session ended")

# Global instance
simple_rtm = SimpleRTM()
