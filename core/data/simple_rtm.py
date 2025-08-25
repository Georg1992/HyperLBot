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
                "rsi": 50.0,
                "volume_depth": 0.0,
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
    
    def update_session(self, session_data: Dict[str, Any]):
        """Update session information"""
        with self._lock:
            self._data["session"].update(session_data)
            self._data["session"]["last_updated"] = datetime.now().isoformat()
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
            
            session_id = session_data.get('session_id', 'unknown')
            logger.debug(f"✅ Session updated: {session_id}")
    
    def update_account(self, account_data: Dict[str, Any]):
        """Update account information"""
        with self._lock:
            self._data["session"].update(account_data)
            self._data["session"]["last_updated"] = datetime.now().isoformat()
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
            
            current_balance = account_data.get('current_balance', 0) or 0
            logger.debug(f"✅ Account updated: ${current_balance:.2f}")
    
    def update_market(self, market_data: Dict[str, Any]):
        """Update market data"""
        with self._lock:
            self._data["market"].update(market_data)
            self._data["market"]["last_updated"] = datetime.now().isoformat()
            self._data["timestamp"] = datetime.now().isoformat()
            self._save_data()
            
            current_price = market_data.get('current_price', 0) or 0
            logger.debug(f"✅ Market updated: ${current_price:.2f}")
    
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
            
            logger.debug(f"✅ Activity added: {message}")
    
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
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        with self._lock:
            # Reload data from file to get latest updates
            self._load_data()
            
            # Calculate session time
            start_time = self._data["session"].get("start_time")
            session_time = "0m"
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    elapsed = datetime.now() - start_dt
                    hours = int(elapsed.total_seconds() // 3600)
                    minutes = int((elapsed.total_seconds() % 3600) // 60)
                    if hours > 0:
                        session_time = f"{hours}h {minutes}m"
                    else:
                        session_time = f"{minutes}m"
                except:
                    session_time = "0m"
            
            # Format data for dashboard
            dashboard_data = {
                "session": {
                    "session_id": self._data["session"]["session_id"],
                    "status": self._data["session"]["status"],
                    "strategy": self._data["session"]["strategy"],
                    "session_time": session_time,
                    "start_time": self._data["session"]["start_time"],
                    "current_balance": self._data["session"]["current_balance"],
                    "initial_balance": self._data["session"]["initial_balance"],
                    "total_pnl": self._data["session"]["total_pnl"],
                    "win_rate": self._data["session"]["win_rate"],
                    "total_trades": self._data["session"]["total_trades"]
                },
                "market": {
                    "current_price": self._data["market"]["current_price"],
                    "trend": self._data["market"]["trend"],
                    "rsi": self._data["market"]["rsi"],
                    "volume_depth": self._data["market"]["volume_depth"]
                },
                "logs": self._data["logs"],
                "predictions": self._data["predictions"],
                "trades": self._data["trades"],
                "orderbook": {"bids": [], "asks": []},  # Placeholder
                "global_volume": {"volume": 0.0},  # Placeholder
                "timestamp": self._data["timestamp"],
                "data_source": "SimpleRTM",
                "connection_status": "✅ Connected"
            }
            
            return dashboard_data
    
    def clear_data(self):
        """Clear all data"""
        with self._lock:
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
                    "rsi": 50.0,
                    "volume_depth": 0.0,
                    "last_updated": None
                },
                "logs": [],
                "predictions": [],
                "trades": [],
                "timestamp": datetime.now().isoformat()
            }
            self._save_data()
            logger.info("🧹 SimpleRTM data cleared")

# Global instance
simple_rtm = SimpleRTM()
