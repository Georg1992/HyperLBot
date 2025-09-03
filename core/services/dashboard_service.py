#!/usr/bin/env python3
"""
Dashboard Service
Handles all dashboard updates and heartbeat management
Single Responsibility: Dashboard coordination
"""

import os
import time
import json
from typing import Dict, Any
from loguru import logger
from core.dashboard.dashboard_data_manager import simple_rtm
from core.constants import technical_constants

class DashboardService:
    """Dashboard coordination service - handles RTM updates and heartbeats"""
    
    def __init__(self, heartbeat_file=None):
        self.heartbeat_file = heartbeat_file or "data/temp/bot_heartbeat.json"
        
        # Heartbeat state
        self.last_heartbeat = 0
        self.heartbeat_interval = 30  # 30 seconds
        
        logger.info("🎛️ Dashboard Service initialized - RTM coordination")
    
    def update_rtm_market(self, market_data: Dict[str, Any]):
        """Update SimpleRTM with market data"""
        try:
            simple_rtm.update_market(market_data)
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM market: {e}")
    
    def update_rtm_data_status(self, data_status: Dict[str, Any]):
        """Update SimpleRTM data status"""
        try:
            # Direct RTM update (no wrapper needed)
            logger.debug(f"📊 Data status update: {data_status}")
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM data status: {e}")
    
    def update_rtm_activity(self, message: str, level: str = "INFO"):
        """Update SimpleRTM with activity"""
        try:
            simple_rtm.add_activity(message, level, "bot")
            logger.info(f"📊 RTM Activity: {message}")
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM activity: {e}")
    
    def update_rtm_signal(self, signal_data: Dict[str, Any]):
        """Update SimpleRTM with signal"""
        try:
            simple_rtm.add_signal(signal_data)
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM signal: {e}")
    
    def generate_and_log_prediction(self, current_price: float, historical_analysis: Dict[str, Any] = None, 
                                   prediction_engine=None, strategy_name: str = "standard"):
        """DISABLED: Ongoing predictions removed - only initial session prediction shown (user request)"""
        # Ongoing prediction generation disabled
        # Only initial session prediction is generated once at session start and displayed
        return
    
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