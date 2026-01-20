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
from typing import Dict, Any
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
        
        # Initialize dashboard data structure - ESSENTIAL DATA ONLY
        self._data = {
            "session": {},
            "market": {},
            "chart": {},
            "trades": [],  # Initialize trades list for pending orders and executed trades
            "logs": [],    # Initialize logs list
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
        """Load dashboard data from file - only if fresh"""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, 'r') as f:
                    file_data = json.load(f)
                
                # Check if data is fresh (less than 5 minutes old)
                last_update = file_data["last_update"] if "last_update" in file_data else None
                if last_update:
                    try:
                        from datetime import datetime
                        file_time = datetime.fromisoformat(last_update)
                        current_time = datetime.now()
                        time_diff = (current_time - file_time).total_seconds()
                        
                        # Only load data if it's less than 30 seconds old (very fresh)
                        if time_diff < 30:  # 30 seconds
                            self._data = file_data
                        else:
                            # Keep the initialized structure, don't load stale data
                            pass
                    except Exception as e:
                        logger.warning(f"⚠️ Could not parse file timestamp: {e}")
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
                # Prepare candle data structure for dashboard
                candle_data = self._prepare_candle_data(market_data)
                if candle_data:
                    market_data["candleData"] = candle_data
                
                # Filter out non-market data keys before updating market section
                # unified_data contains session_data, trading_data, ml_data, etc. which shouldn't be in market dict
                non_market_keys = {
                    "session_data", "trading_data", "ml_data", "raw_data_access"
                }
                
                # Extract only market-related data (exclude non-market keys)
                market_dict = {k: v for k, v in market_data.items() if k not in non_market_keys}
                
                # Log if we're getting empty data
                if len(market_dict) == 0:
                    logger.warning(f"⚠️ update_market_data received EMPTY data! Keys in market_data: {list(market_data.keys())[:20]}")
                
                # Update nested market section with filtered data
                self._data["market"].update(market_dict)
                
                # Surface prediction to top-level for UI consumption (always set, even None)
                pred_obj = market_data["prediction"] if "prediction" in market_data else None
                self._data["prediction"] = pred_obj
                
                self._save_data()
                # WebSocket emission happens automatically via file monitoring
                # RSI removed - not working properly
        except Exception as e:
            logger.error(f"❌ Could not update market data: {e}")
    
    def _prepare_candle_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare candle data structure for dashboard chart"""
        try:
            # Get pattern data from market data
            patterns = market_data["patterns"] if "patterns" in market_data else {}
            
            # Get current price for chart data preparation
            current_price = market_data["current_price"] if "current_price" in market_data else 0.0
            if not current_price or current_price <= 0:
                raise ValueError("No valid current price for chart data preparation - NO FALLBACKS")
            
            # Call historical_data_service.prepare_chart_data() to get actual candles
            # This handles UTC-based 5-minute boundaries and proper candle display
            from core.services.historical_data_service import get_global_historical_data_service
            historical_service = get_global_historical_data_service()
            
            # prepare_chart_data returns complete chart data with historical candles, ongoing candle, and pattern analysis
            # NO FALLBACKS - prepare_chart_data raises on error
            candle_data = historical_service.prepare_chart_data(current_price, patterns)
            return candle_data
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare candle data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Re-raise to fail fast - NO FALLBACKS
            raise
    
    
    def update_session_data(self, session_data: Dict[str, Any]):
        """Update session data"""
        try:
            with self._lock:
                self._data["session"] = session_data.copy()
                self._save_data()
        except Exception as e:
            logger.error(f"❌ Could not update session data: {e}")
    
    def update_chart_data(self, chart_data: Dict[str, Any]):
        """Update chart data"""
        try:
            with self._lock:
                self._data["chart"] = chart_data.copy()
                self._save_data()
        except Exception as e:
            logger.error(f"❌ Could not update chart data: {e}")
    
    def get_data(self) -> Dict[str, Any]:
        """Get all dashboard data"""
        with self._lock:
            return self._data.copy()
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get session data"""
        with self._lock:
            return (self._data["session"] if "session" in self._data else {}).copy()
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get market data"""
        with self._lock:
            return (self._data["market"] if "market" in self._data else {}).copy()
    
    def get_chart_data(self) -> Dict[str, Any]:
        """Get chart data"""
        with self._lock:
            return (self._data["chart"] if "chart" in self._data else {}).copy()
    
    def clear_session_data(self):
        """Clear session data"""
        try:
            with self._lock:
                self._data["session"] = {}
                self._save_data()
                logger.info("🧹 Session data cleared - session ended")
        except Exception as e:
            logger.error(f"❌ Could not clear session data: {e}")
    
    def clear_stale_data(self):
        """Clear all stale data when starting a new session"""
        try:
            with self._lock:
                # Reset to fresh data structure
                self._data = {
                    "session": {},
                    "market": {},
                    "chart": {},
                    "trades": [],  # Initialize trades list
                    "logs": [],    # Initialize logs list
                    "last_update": datetime.now().isoformat()
                }
                self._save_data()
                
                # Also delete the old data file to prevent loading stale data
                if os.path.exists(self._data_file):
                    os.remove(self._data_file)
                    logger.debug("🗑️ Removed stale dashboard data file")
                
                logger.info("🧹 Stale dashboard data cleared - fresh session started")
        except Exception as e:
            logger.error(f"❌ Could not clear stale data: {e}")
    
    def check_bot_heartbeat(self) -> bool:
        """Check if bot heartbeat is fresh"""
        try:
            if not os.path.exists(self.heartbeat_file):
                return False
            
            with open(self.heartbeat_file, 'r') as f:
                heartbeat_data = json.load(f)
            
            last_heartbeat = heartbeat_data["last_heartbeat"] if "last_heartbeat" in heartbeat_data else 0
            current_time = time.time()
            
            # Consider heartbeat stale if older than 2 minutes
            is_fresh = (current_time - last_heartbeat) < 120
            
            if not is_fresh:
                logger.warning("⚠️ Bot heartbeat is stale - bot may have stopped")
            
            return is_fresh
        except Exception as e:
            logger.error(f"❌ Could not check bot heartbeat: {e}")
            return False
    
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


# Factory function for dependency injection with singleton pattern
_global_dashboard_service = None

def create_dashboard_service(heartbeat_file=None) -> DashboardService:
    """
    Factory function to create DashboardService with singleton pattern
    Prevents redundant initializations
    
    Args:
        heartbeat_file: Optional heartbeat file path
    
    Returns:
        Configured DashboardService instance (singleton)
    """
    global _global_dashboard_service
    if _global_dashboard_service is None:
        _global_dashboard_service = DashboardService(heartbeat_file=heartbeat_file)
        logger.info("🎛️ DashboardService singleton created")
    return _global_dashboard_service
