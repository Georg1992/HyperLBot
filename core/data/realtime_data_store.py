#!/usr/bin/env python3
"""
Real-Time Data Store
Pure in-memory data storage for trading bot state
Single Responsibility: Store and retrieve current trading data
"""

import time
import threading
from typing import Dict, Any, List, Optional
from loguru import logger
from collections import deque
from datetime import datetime


class RealTimeDataStore:
    """
    Pure in-memory data store for real-time trading data
    Single Responsibility: Store and retrieve current state data
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for shared state"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.data_lock = threading.RLock()
        
        # Initialize data limits
        self.MAX_TRADES = 100
        self.MAX_SIGNALS = 50
        self.MAX_ACTIVITY = 50
        
        # Initialize core trading state
        self._reset_to_default_state()
        
        # Historical data (in-memory for speed)
        self.recent_trades = deque(maxlen=self.MAX_TRADES)
        self.recent_signals = deque(maxlen=self.MAX_SIGNALS)
        self.recent_activity = deque(maxlen=self.MAX_ACTIVITY)
        self.open_positions = []
        
        logger.success("🏪 Real-Time Data Store initialized")
    
    def _reset_to_default_state(self):
        """Reset to default trading state"""
        self.current_state = {
            "session": {
                "session_id": f"session_{int(time.time())}",
                "start_time": datetime.now().isoformat(),
                "status": "ACTIVE",
                "strategy": "unknown",
                "initial_balance": 120.0,
                "current_balance": 120.0,
                "balance_change": 0.0,
                "balance_change_pct": 0.0,
                "last_balance_update": datetime.now().isoformat(),
                "bot_version": "Advanced Trading Bot v4.0",
                "open_positions_count": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0
            },
            "market": {
                "current_price": 0.0,
                "trend": "UNKNOWN",
                "market_condition": "UNKNOWN",
                "last_update": datetime.now().isoformat(),
                "rsi": 50.0,
                "volume_depth": 0.0,
                "orderbook_imbalance": 0.0,
                "volatility_5m": 0.0,
                "volatility_1h": 0.0,
                "support": 0.0,
                "resistance": 0.0,
                "volume_category": "UNKNOWN",
                "volume_trend": "UNKNOWN",
                "data_source": "none"
            },
            "predictions": [],
            "positions": {
                "open_positions": [],
                "simulated_positions": [],
                "last_update": 0
            },
            "orders": {
                "open_orders": [],
                "simulated_orders": [],
                "last_update": 0
            },
            "balance": {
                "real_account_value": 0.0,
                "real_available_margin": 0.0,
                "real_total_margin_used": 0.0,
                "real_unrealized_pnl": 0.0,
                "real_withdrawal_balance": 0.0,
                "real_margin_usage_pct": 0.0,
                "simulated_balance": 120.0,
                "simulated_balance_change": 0.0,
                "balance_source": "mixed",
                "last_update": 0
            },
            "global_volume": {
                "global_volume_per_second": 0.0,
                "status": "unavailable",
                "last_update": 0
            },
            "blockchain_sentiment": {
                "overall_sentiment": "UNKNOWN",
                "confidence": 0.0,
                "last_update": 0
            }
        }
    
    # SESSION DATA METHODS
    def get_session_data(self) -> Dict[str, Any]:
        """Get current session data"""
        with self.data_lock:
            return self.current_state["session"].copy()
    
    def update_session_data(self, updates: Dict[str, Any]):
        """Update session data"""
        with self.data_lock:
            self.current_state["session"].update(updates)
            logger.debug(f"🔄 Session data updated: {list(updates.keys())}")
    
    def set_session_status(self, status: str):
        """Update session status"""
        with self.data_lock:
            self.current_state["session"]["status"] = status
            logger.debug(f"📊 Session status: {status}")
    
    # MARKET DATA METHODS
    def get_market_data(self) -> Dict[str, Any]:
        """Get current market data"""
        with self.data_lock:
            return self.current_state["market"].copy()
    
    def update_market_data(self, market_data: Dict[str, Any]):
        """Update market data"""
        with self.data_lock:
            self.current_state["market"].update(market_data)
            self.current_state["market"]["last_update"] = datetime.now().isoformat()
            logger.debug(f"📊 Market data updated: {list(market_data.keys())}")
    
    # BALANCE METHODS
    def get_balance_data(self) -> Dict[str, Any]:
        """Get current balance data"""
        with self.data_lock:
            return self.current_state["balance"].copy()
    
    def update_balance(self, new_balance: float, reason: str = "Trade execution"):
        """Update current balance"""
        with self.data_lock:
            old_balance = self.current_state["session"]["current_balance"]
            initial_balance = self.current_state["session"]["initial_balance"]
            
            self.current_state["session"]["current_balance"] = new_balance
            self.current_state["session"]["balance_change"] = new_balance - initial_balance
            self.current_state["session"]["balance_change_pct"] = ((new_balance - initial_balance) / initial_balance) * 100
            self.current_state["session"]["last_balance_update"] = datetime.now().isoformat()
            
            balance_change = new_balance - old_balance
            logger.debug(f"💰 Balance: ${old_balance:.2f} → ${new_balance:.2f} ({balance_change:+.2f}) - {reason}")
    
    def update_simulated_balance(self, new_balance: float, change: float):
        """Update simulated balance"""
        with self.data_lock:
            self.current_state["balance"]["simulated_balance"] = new_balance
            self.current_state["balance"]["simulated_balance_change"] = change
            self.current_state["balance"]["last_update"] = time.time()
            
            # If not using real balance, update session balance with simulated
            if self.current_state["balance"]["balance_source"] != "real":
                self.current_state["session"]["current_balance"] = new_balance
                self.current_state["session"]["balance_change"] = change
                self.current_state["session"]["balance_change_pct"] = (
                    (change / self.current_state["session"]["initial_balance"] * 100)
                    if self.current_state["session"]["initial_balance"] > 0 else 0
                )
                self.current_state["balance"]["balance_source"] = "simulated"
            
            logger.debug(f"🎮 Simulated balance: ${new_balance:.2f} (Change: ${change:.2f})")
    
    # PREDICTIONS METHODS
    def get_predictions(self) -> List[Dict[str, Any]]:
        """Get current predictions"""
        with self.data_lock:
            return self.current_state["predictions"].copy()
    
    def update_predictions(self, predictions_data: List[Dict[str, Any]]):
        """Update current trading predictions"""
        with self.data_lock:
            self.current_state["predictions"] = predictions_data
            logger.debug(f"🎯 Predictions updated: {len(predictions_data)} predictions")
    
    # POSITIONS METHODS
    def get_positions_data(self) -> Dict[str, Any]:
        """Get positions data"""
        with self.data_lock:
            return self.current_state["positions"].copy()
    
    def update_real_positions(self, positions: List[Dict[str, Any]]):
        """Update real positions from Hyperliquid"""
        with self.data_lock:
            self.current_state["positions"]["open_positions"] = positions
            self.current_state["positions"]["last_update"] = time.time()
            self.current_state["session"]["open_positions_count"] = len(positions)
            logger.debug(f"🔄 Real positions updated: {len(positions)} positions")
    
    def add_simulated_position(self, position: Dict[str, Any]):
        """Add a simulated position"""
        with self.data_lock:
            if "timestamp" not in position:
                position["timestamp"] = time.time()
            position["source"] = "simulation"
            
            self.current_state["positions"]["simulated_positions"].append(position)
            self.current_state["positions"]["last_update"] = time.time()
            logger.debug(f"📈 Simulated position added: {position['side']} {position['size']} {position['symbol']}")
    
    # ORDERS METHODS
    def get_orders_data(self) -> Dict[str, Any]:
        """Get orders data"""
        with self.data_lock:
            return self.current_state["orders"].copy()
    
    def update_real_orders(self, orders: List[Dict[str, Any]]):
        """Update real orders from Hyperliquid"""
        with self.data_lock:
            self.current_state["orders"]["open_orders"] = orders
            self.current_state["orders"]["last_update"] = time.time()
            logger.debug(f"🔄 Real orders updated: {len(orders)} orders")
    
    # VOLUME AND SENTIMENT METHODS
    def update_global_volume(self, volume_data: Dict[str, Any]):
        """Update global volume data"""
        with self.data_lock:
            self.current_state["global_volume"] = {
                "global_volume_per_second": volume_data.get("global_volume_per_second", 0.0),
                "volume_by_exchange": volume_data.get("volume_by_exchange", {}),
                "coverage_ratio": volume_data.get("coverage_ratio", 0.0),
                "successful_exchanges": volume_data.get("successful_exchanges", 0),
                "total_exchanges": volume_data.get("total_exchanges", 6),
                "status": volume_data.get("status", "unavailable"),
                "last_update": time.time()
            }
            logger.debug("🌍 Global volume data updated")
    
    def update_blockchain_sentiment(self, sentiment_data: Dict[str, Any]):
        """Update blockchain sentiment data"""
        with self.data_lock:
            self.current_state["blockchain_sentiment"] = {
                "overall_sentiment": sentiment_data.get("overall_sentiment", "UNKNOWN"),
                "confidence": sentiment_data.get("confidence", 0.0),
                "indicators": sentiment_data.get("indicators", {}),
                "last_update": time.time()
            }
            logger.debug("🧠 Blockchain sentiment updated")
    
    # HISTORICAL DATA METHODS
    def add_trade_record(self, trade_record: Dict[str, Any]):
        """Add trade to recent trades"""
        with self.data_lock:
            trade_record["timestamp"] = time.time()
            self.recent_trades.append(trade_record)
            
            # Update session statistics
            session = self.current_state["session"]
            session["total_trades"] += 1
            if trade_record.get("was_profitable", False):
                session["winning_trades"] += 1
            else:
                session["losing_trades"] += 1
            
            logger.debug(f"📊 Trade recorded: {trade_record.get('side', 'UNKNOWN')} {trade_record.get('pnl', 0):+.2f}")
    
    def add_signal_record(self, signal_record: Dict[str, Any]):
        """Add signal to recent signals"""
        with self.data_lock:
            signal_record["timestamp"] = time.time()
            self.recent_signals.append(signal_record)
            logger.debug(f"🎯 Signal recorded: {signal_record.get('signal_type', 'UNKNOWN')}")
    
    def add_activity_record(self, activity_record: Dict[str, Any]):
        """Add activity to recent activity"""
        with self.data_lock:
            activity_record["timestamp"] = time.time()
            activity_record["datetime"] = datetime.now().isoformat()
            self.recent_activity.append(activity_record)
            logger.debug(f"📊 Activity recorded: {activity_record.get('message', '')}")
    
    def get_recent_trades(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades"""
        with self.data_lock:
            return list(self.recent_trades)[-count:]
    
    def get_recent_signals(self, count: int = 8) -> List[Dict[str, Any]]:
        """Get recent signals"""
        with self.data_lock:
            return list(self.recent_signals)[-count:]
    
    def get_recent_activity(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent activity"""
        with self.data_lock:
            return list(self.recent_activity)[-count:]
    
    # COMPREHENSIVE STATE ACCESS
    def get_complete_state(self) -> Dict[str, Any]:
        """Get complete current state"""
        with self.data_lock:
            return {
                "session": self.current_state["session"].copy(),
                "market": self.current_state["market"].copy(),
                "predictions": self.current_state["predictions"].copy(),
                "positions": self.current_state["positions"].copy(),
                "orders": self.current_state["orders"].copy(),
                "balance": self.current_state["balance"].copy(),
                "global_volume": self.current_state["global_volume"].copy(),
                "blockchain_sentiment": self.current_state["blockchain_sentiment"].copy(),
                "recent_trades": list(self.recent_trades)[-10:],
                "recent_signals": list(self.recent_signals)[-8:],
                "recent_activity": list(self.recent_activity)[-5:],
                "open_positions": self.open_positions.copy(),
                "timestamp": time.time()
            }
    
    # UTILITY METHODS
    def clear_historical_data(self):
        """Clear all historical data"""
        with self.data_lock:
            self.recent_trades.clear()
            self.recent_signals.clear()
            self.recent_activity.clear()
            self.open_positions.clear()
            logger.info("🧹 Historical data cleared")
    
    def reset_session(self, session_id: str = None, strategy: str = "standard", initial_balance: float = 120.0):
        """Reset to fresh session state"""
        with self.data_lock:
            if session_id is None:
                session_id = f"session_{int(time.time())}"
            
            # Clear historical data
            self.clear_historical_data()
            
            # Reset to default state with new session info
            self._reset_to_default_state()
            self.current_state["session"]["session_id"] = session_id
            self.current_state["session"]["strategy"] = strategy
            self.current_state["session"]["initial_balance"] = initial_balance
            self.current_state["session"]["current_balance"] = initial_balance
            self.current_state["balance"]["simulated_balance"] = initial_balance
            
            logger.success(f"🔄 Session reset: {session_id} ({strategy})")


# Global instance (singleton)
realtime_data_store = RealTimeDataStore()