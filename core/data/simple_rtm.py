#!/usr/bin/env python3
"""
Simple RTM for existing dashboard
Provides the exact data structure the dashboard expects
Clear data flow: Bot → SimpleRTM → Dashboard
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

class SimpleRTM:
    """Simple Real-Time Manager - Single source of truth for dashboard data"""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._data_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'temp', 'simple_rtm_data.json')
        
        # Ensure temp directory exists
        os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
        
        # Initialize with default data
        self._data = {
            "session": {
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
                "last_updated": None
            },
            "market": {
                "current_price": 97500.0,
                "trend": "NEUTRAL",
                "rsi": None,  # Use None instead of 50.0 for proper N/A handling
                "volume_depth": 0.0,
                "volume_category": "UNKNOWN",
                "order_flow": "NEUTRAL",
                "depth_analysis": "UNKNOWN",
                "volatility_5m": 0.0,
                "volatility_category": "UNKNOWN",
                "volatility_trend": "UNKNOWN",
                "spread_volatility": 0.0,
                "ultimate_pressure": {
                    "direction": "NEUTRAL",
                    "confidence": "50%",
                    "strength": 0.5,
                    "trend": "NEUTRAL"
                },
                "trend_analysis": {
                    "overall_trend": "UNKNOWN",
                    "alignment_score": 0.0,
                    "timeframes": {
                        "1m": {"trend": "UNKNOWN", "strength": 0, "confidence": 0},
                        "5m": {"trend": "UNKNOWN", "strength": 0, "confidence": 0},
                        "1h": {"trend": "UNKNOWN", "strength": 0, "confidence": 0}
                    },
                    "reversal_analysis": {
                        "reversal_probability": 0.0,
                        "signals": []
                    }
                },
                "data_update_status": {
                    "yahoo_analysis": {"last_update": 0, "next_update": 0, "time_until_update": 0},
                    "rsi_data": {"last_update": 0, "next_update": 0, "time_until_update": 0},
                    "trend_data": {"last_update": 0, "next_update": 0, "time_until_update": 0},
                    "hourly_data": {"last_update": 0, "next_update": 0, "time_until_update": 0},
                    "daily_data": {"last_update": 0, "next_update": 0, "time_until_update": 0}
                },
                "last_updated": None
            },
            "logs": [],
            "predictions": [],
            "trades": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Load existing data if file exists
        self._load_data()
        
        logger.info("🚀 Simple RTM initialized - File-based storage for cross-process sharing")
    
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
    

    
    def update_market(self, market_data: Dict[str, Any]):
        """Update market data"""
        with self._lock:
            # Update basic market data
            self._data["market"].update(market_data)
            
            # Handle trend analysis data separately
            if "trend_analysis" in market_data:
                self._data["market"]["trend_analysis"] = market_data["trend_analysis"]
            
            self._data["market"]["last_updated"] = datetime.now().isoformat()
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
    
    def update_data_status(self, data_status: Dict[str, Any]):
        """Update data update status"""
        with self._lock:
            self._data["market"]["data_update_status"] = data_status
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
                "price": signal_data.get("price", 0) or 0
            }
            self._data["predictions"].append(signal)
            
            # Keep only last 50 signals
            if len(self._data["predictions"]) > 50:
                self._data["predictions"] = self._data["predictions"][-50:]
            
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
            
            confidence = signal_data.get('confidence', 0) or 0
            logger.debug(f"✅ Signal added: {signal_data.get('type', 'UNKNOWN')} {confidence}%")
    
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
            logger.debug(f"✅ Trade added: {trade_data.get('side', 'UNKNOWN')} {size} BTC")
    
    def get_data(self) -> Dict[str, Any]:
        """Get raw data - Dashboard reads directly from this"""
        with self._lock:
            return self._data.copy()
    
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

# Global instance
simple_rtm = SimpleRTM()
