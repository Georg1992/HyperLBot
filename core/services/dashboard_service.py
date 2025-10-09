#!/usr/bin/env python3
"""
Dashboard Service
Handles all dashboard updates, data management, and heartbeat
Single Responsibility: Complete dashboard coordination
"""

import os
import time
import json
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger

class DashboardService:
    """Complete dashboard service - handles all dashboard data and communications"""
    
    _global_instance = None
    
    def __init__(self, heartbeat_file=None):
        self.heartbeat_file = heartbeat_file or "data/temp/bot_heartbeat.json"
        self._lock = threading.RLock()
        self._data_file = os.path.join("data", "temp", "dashboard_data.json")
        
        # Ensure temp directory exists
        os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
        
        # Heartbeat state
        self.last_heartbeat = 0
        self.heartbeat_interval = 30  # 30 seconds
        
        # Initialize dashboard data structure
        self._data = {
            "session": {},
            "account": {},
            "market": {},
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
        
        # Set global instance
        DashboardService._global_instance = self
        
        # Load existing data if file exists
        self._load_data()
        
        logger.info("🎛️ Dashboard Service initialized - Complete dashboard coordination")
    
    @classmethod
    def get_global_instance(cls):
        """Get the global dashboard service instance"""
        return cls._global_instance
    
    def _load_data(self):
        """Load dashboard data from file"""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, 'r') as f:
                    self._data = json.load(f)
                logger.debug("📊 Dashboard data loaded from file")
        except Exception as e:
            logger.warning(f"⚠️ Could not load dashboard data: {e}")
    
    def _save_data(self):
        """Save dashboard data to file"""
        try:
            with self._lock:
                self._data["last_update"] = datetime.now().isoformat()
                with open(self._data_file, 'w') as f:
                    json.dump(self._data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Could not save dashboard data: {e}")
    
    def update_market_data(self, market_data: Dict[str, Any]):
        """Update dashboard with market data"""
        try:
            with self._lock:
                self._data["market"].update(market_data)
                self._save_data()
                # Trigger WebSocket emission
                self._trigger_websocket_emission()
        except Exception as e:
            logger.error(f"❌ Could not update market data: {e}")
    
    def _trigger_websocket_emission(self):
        """Trigger WebSocket emission to update dashboard"""
        try:
            # The dashboard will automatically detect data changes through its monitoring loop
            # The data has been saved to file, so the dashboard's _start_data_monitoring will pick it up
            logger.debug("📡 Market data updated - WebSocket emission triggered")
        except Exception as e:
            logger.error(f"❌ Could not trigger WebSocket emission: {e}")
    
    def update_data_status(self, data_status: Dict[str, Any]):
        """Update dashboard data status"""
        try:
            with self._lock:
                if "data_sources" not in self._data:
                    self._data["data_sources"] = {}
                self._data["data_sources"].update(data_status)
                self._save_data()
        except Exception as e:
            logger.error(f"❌ Could not update data status: {e}")
    
    def add_activity(self, message: str, level: str = "INFO", source: str = "bot"):
        """Add activity to dashboard"""
        try:
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
                
                self._save_data()
                # Trigger WebSocket emission to update dashboard
                self._trigger_websocket_emission()
        except Exception as e:
            logger.error(f"❌ Could not add activity: {e}")
    
    def add_signal(self, signal_data: Dict[str, Any]):
        """Add signal to dashboard"""
        try:
            with self._lock:
                signal_data["timestamp"] = datetime.now().isoformat()
                if "signals" not in self._data:
                    self._data["signals"] = []
                self._data["signals"].append(signal_data)
                
                # Keep only last 50 signals
                if len(self._data["signals"]) > 50:
                    self._data["signals"] = self._data["signals"][-50:]
                
                self._save_data()
                # Trigger WebSocket emission to update dashboard
                self._trigger_websocket_emission()
        except Exception as e:
            logger.error(f"❌ Could not add signal: {e}")
    
    def add_prediction(self, prediction_data: Dict[str, Any]):
        """Add prediction to dashboard"""
        try:
            with self._lock:
                prediction_data["timestamp"] = datetime.now().isoformat()
                self._data["predictions"].append(prediction_data)
                
                # Keep only last 20 predictions
                if len(self._data["predictions"]) > 20:
                    self._data["predictions"] = self._data["predictions"][-20:]
                
                self._save_data()
                # Trigger WebSocket emission to update dashboard
                self._trigger_websocket_emission()
        except Exception as e:
            logger.error(f"❌ Could not add prediction: {e}")
    
    def add_trade(self, trade_data: Dict[str, Any]):
        """Add trade to dashboard"""
        try:
            with self._lock:
                trade_data["timestamp"] = datetime.now().isoformat()
                self._data["trades"].append(trade_data)
                
                # Keep only last 100 trades
                if len(self._data["trades"]) > 100:
                    self._data["trades"] = self._data["trades"][-100:]
                
                self._save_data()
                # Trigger WebSocket emission to update dashboard
                self._trigger_websocket_emission()
        except Exception as e:
            logger.error(f"❌ Could not add trade: {e}")
    
    def sync_from_account_manager(self, account_data: Dict[str, Any]):
        """Sync account data from AccountManager"""
        try:
            with self._lock:
                self._data["account"] = account_data.copy()
                self._data["data_sources"]["account_manager_synced"] = True
                self._data["data_sources"]["last_sync_time"] = datetime.now().isoformat()
                self._save_data()
        except Exception as e:
            logger.error(f"❌ Could not sync account data: {e}")
    
    def sync_from_session_manager(self, session_data: Dict[str, Any]):
        """Sync session data from SessionManager"""
        try:
            with self._lock:
                self._data["session"] = session_data.copy()
                self._data["data_sources"]["session_manager_synced"] = True
                self._data["data_sources"]["last_sync_time"] = datetime.now().isoformat()
                self._save_data()
        except Exception as e:
            logger.error(f"❌ Could not sync session data: {e}")
    
    def get_data(self) -> Dict[str, Any]:
        """Get all dashboard data"""
        with self._lock:
            return self._data.copy()
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get session data"""
        with self._lock:
            return self._data.get("session", {}).copy()
    
    def get_account_data(self) -> Dict[str, Any]:
        """Get account data"""
        with self._lock:
            return self._data.get("account", {}).copy()
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get market data"""
        with self._lock:
            return self._data.get("market_data", {}).copy()
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """Get trades data"""
        with self._lock:
            return self._data.get("trades", []).copy()
    
    def clear_presentation_data(self):
        """Clear presentation data (logs, predictions, trades only - market data preserved)"""
        try:
            with self._lock:
                self._data["logs"] = []
                self._data["predictions"] = []
                self._data["trades"] = []
                self._save_data()
                logger.info("🧹 Dashboard presentation data cleared (logs, predictions, trades only - market data preserved)")
        except Exception as e:
            logger.error(f"❌ Could not clear presentation data: {e}")
    
    def clear_session_data(self):
        """Clear session data"""
        try:
            with self._lock:
                self._data["session"] = {}
                self._data["data_sources"]["session_manager_synced"] = False
                self._save_data()
                logger.info("🧹 Session data cleared - session ended")
        except Exception as e:
            logger.error(f"❌ Could not clear session data: {e}")
    
    def check_bot_heartbeat(self) -> bool:
        """Check if bot heartbeat is fresh"""
        try:
            if not os.path.exists(self.heartbeat_file):
                return False
            
            with open(self.heartbeat_file, 'r') as f:
                heartbeat_data = json.load(f)
            
            last_heartbeat = heartbeat_data.get("last_heartbeat", 0)
            current_time = time.time()
            
            # Consider heartbeat stale if older than 2 minutes
            is_fresh = (current_time - last_heartbeat) < 120
            
            if not is_fresh:
                logger.warning("⚠️ Bot heartbeat is stale - bot may have stopped")
            
            return is_fresh
        except Exception as e:
            logger.error(f"❌ Could not check bot heartbeat: {e}")
            return False
    
    def auto_cleanup_stale_sessions(self):
        """Auto-cleanup stale sessions"""
        try:
            # Check if session is stale (older than 1 hour)
            session_data = self.get_session_data()
            if session_data.get("session_id") and session_data.get("session_id") != "no_session":
                session_start = session_data.get("start_time")
                if session_start:
                    try:
                        from datetime import datetime
                        start_time = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
                        current_time = datetime.now()
                        time_diff = (current_time - start_time).total_seconds()
                        
                        if time_diff > 3600:  # 1 hour
                            logger.info("🧹 Auto-cleaning stale session")
                            self.clear_session_data()
                    except Exception:
                        pass  # Ignore parsing errors
        except Exception as e:
            logger.error(f"❌ Could not auto-cleanup stale sessions: {e}")
    
    def create_initial_heartbeat(self, session_manager=None, strategy_name: str = "standard", paper_balance: float = 0.0):
        """Create initial heartbeat file immediately when bot starts"""
        self._write_heartbeat(is_initial=True, session_manager=session_manager, 
                             strategy_name=strategy_name, paper_balance=paper_balance)
    
    def update_heartbeat(self, session_manager=None, strategy_name: str = "standard", paper_balance: float = 0.0):
        """Update bot heartbeat to indicate it's still running"""
        current_time = time.time()
        if current_time - self.last_heartbeat >= self.heartbeat_interval:
            self._write_heartbeat(is_initial=False, session_manager=session_manager,
                                 strategy_name=strategy_name, paper_balance=paper_balance)
    
    def cleanup_heartbeat(self):
        """Clean up heartbeat file when bot stops"""
        try:
            if os.path.exists(self.heartbeat_file):
                os.remove(self.heartbeat_file)
        except Exception as e:
            logger.error(f"❌ Could not cleanup heartbeat: {e}")
    
    def _write_heartbeat(self, is_initial: bool = False, session_manager=None, 
                        strategy_name: str = "standard", paper_balance: float = 0.0):
        """Write heartbeat file - consolidated logic"""
        try:
            current_time = time.time()
            heartbeat_data = {
                "bot_running": True,
                "last_heartbeat": current_time,
                "session_id": getattr(session_manager, 'current_session_id', None) if session_manager else None,
                "strategy": strategy_name,
                "balance": paper_balance
            }
            
            # Ensure temp directory exists
            os.makedirs(os.path.dirname(self.heartbeat_file), exist_ok=True)
            
            with open(self.heartbeat_file, 'w') as f:
                json.dump(heartbeat_data, f, indent=2)
            
            self.last_heartbeat = current_time
            
            if is_initial:
                logger.info("💓 Initial bot heartbeat created")
                
        except Exception as e:
            logger.error(f"❌ Could not {'create' if is_initial else 'update'} heartbeat: {e}")
