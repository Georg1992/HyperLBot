#!/usr/bin/env python3
"""
Data Manager Coordinator
Coordinates all data management components and maintains the original API
Single Responsibility: Coordinate data management components
"""

import time
import json
import os
import threading
from typing import Dict, Any, List, Optional, Callable
from loguru import logger
from datetime import datetime

# Import all the new components
from core.data.realtime_data_store import realtime_data_store
from core.data.database_manager import database_manager
from core.session.session_manager import session_manager
from core.data.data_publisher import data_publisher
from core.data.performance_tracker import performance_tracker


class DataManagerCoordinator:
    """
    Coordinates all data management components
    Single Responsibility: Coordinate and orchestrate data management
    Maintains compatibility with the original RealTimeTradingDataManager API
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for shared coordination"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.coordinator_lock = threading.RLock()
        
        # Initialize account manager reference
        try:
            from core.account_manager import account_manager
            self.account_manager = account_manager
        except ImportError:
            self.account_manager = None
            logger.warning("⚠️ Account manager not available")
        
        logger.success("🎯 Data Manager Coordinator initialized - All components integrated")
    
    # ===============================
    # SESSION MANAGEMENT METHODS
    # ===============================
    
    def start_session(self, session_id: str = None, strategy: str = "standard") -> str:
        """Start a new trading session"""
        try:
            # Get initial balance from current session or default
            current_session = realtime_data_store.get_session_data()
            initial_balance = current_session.get("initial_balance", 120.0)
            
            # Start session through session manager
            session_id = session_manager.start_session(session_id, strategy, initial_balance)
            
            # Publish session started event
            session_data = realtime_data_store.get_session_data()
            data_publisher.publish_session_started(session_data)
            
            logger.success(f"🚀 Coordinated session start: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error coordinating session start: {e}")
            raise
    
    def end_session(self):
        """End current trading session"""
        try:
            # Get session data before ending
            session_data = realtime_data_store.get_session_data()
            
            # End session through session manager
            success = session_manager.end_session()
            
            if success:
                # Publish session ended event
                data_publisher.publish_session_ended(session_data)
                logger.success("🏁 Coordinated session end")
            
        except Exception as e:
            logger.error(f"Error coordinating session end: {e}")
    
    # ===============================
    # BALANCE MANAGEMENT METHODS
    # ===============================
    
    def update_balance(self, new_balance: float, reason: str = "Trade execution"):
        """Update current balance with full coordination"""
        try:
            # Update balance in data store
            realtime_data_store.update_balance(new_balance, reason)
            
            # Update performance tracking
            performance_tracker.update_balance_tracking(new_balance)
            
            # Update account manager if available
            if self.account_manager and self.account_manager.account_data:
                balance_change = new_balance - self.account_manager.account_data.get("current_balance", new_balance)
                self.account_manager.update_balance(new_balance, balance_change)
            
            # Publish balance update event
            balance_data = {
                "new_balance": new_balance,
                "reason": reason,
                "timestamp": time.time()
            }
            data_publisher.publish_balance_updated(balance_data)
            
            logger.debug(f"💰 Coordinated balance update: ${new_balance:.2f} - {reason}")
            
        except Exception as e:
            logger.error(f"Error coordinating balance update: {e}")
    
    def update_simulated_balance(self, new_balance: float, change: float):
        """Update simulated balance"""
        try:
            # Update in data store
            realtime_data_store.update_simulated_balance(new_balance, change)
            
            # Update performance tracking
            performance_tracker.update_balance_tracking(new_balance)
            
            # Update account manager if available
            if self.account_manager and self.account_manager.account_data:
                self.account_manager.update_balance(new_balance, change)
            
            # Publish simulated balance update event
            balance_data = {"balance": new_balance, "change": change}
            data_publisher.publish_event("simulated_balance_update", balance_data)
            
            logger.debug(f"🎮 Coordinated simulated balance update: ${new_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Error coordinating simulated balance update: {e}")
    
    # ===============================
    # MARKET DATA METHODS
    # ===============================
    
    def update_market_data(self, market_data: Dict[str, Any]):
        """Update market data with coordination"""
        try:
            # Update in data store
            realtime_data_store.update_market_data(market_data)
            
            # Save snapshot to database (optional, for historical tracking)
            if market_data.get("current_price", 0) > 0:
                database_manager.save_market_data_snapshot(market_data)
            
            # Publish market update event
            data_publisher.publish_market_update(market_data)
            
            logger.debug(f"📊 Coordinated market data update: {list(market_data.keys())}")
            
        except Exception as e:
            logger.error(f"Error coordinating market data update: {e}")
    
    # ===============================
    # TRADE MANAGEMENT METHODS
    # ===============================
    
    def add_trade(self, trade_data: Dict[str, Any]):
        """Add a new trade with full coordination"""
        try:
            # Add to data store
            realtime_data_store.add_trade_record(trade_data)
            
            # Save to database
            database_manager.save_trade(trade_data)
            
            # Update account manager if available
            if self.account_manager and self.account_manager.account_data:
                self.account_manager.add_trade(trade_data)
            
            # Update performance metrics
            recent_trades = realtime_data_store.get_recent_trades(50)
            performance_tracker.update_metrics_from_trades(recent_trades)
            
            # Add to session through session manager
            session_manager.add_session_trade(trade_data)
            
            # Publish trade added event
            data_publisher.publish_trade_added(trade_data)
            
            logger.success(f"📊 Coordinated trade addition: {trade_data.get('trade_id')}")
            
        except Exception as e:
            logger.error(f"Error coordinating trade addition: {e}")
    
    def add_trading_signal(self, signal_data: Dict[str, Any]):
        """Add a new trading signal"""
        try:
            # Add to data store
            realtime_data_store.add_signal_record(signal_data)
            
            # Save to database
            database_manager.save_signal(signal_data)
            
            # Publish signal added event
            data_publisher.publish_signal_added(signal_data)
            
            logger.debug(f"🎯 Coordinated signal addition: {signal_data.get('signal_type')}")
            
        except Exception as e:
            logger.error(f"Error coordinating signal addition: {e}")
    
    def add_activity(self, activity_data: Dict[str, Any]):
        """Add general bot activity"""
        try:
            # Add to data store
            realtime_data_store.add_activity_record(activity_data)
            
            # Publish activity added event
            data_publisher.publish_activity_added(activity_data)
            
            logger.debug(f"📊 Coordinated activity addition: {activity_data.get('message', '')}")
            
        except Exception as e:
            logger.error(f"Error coordinating activity addition: {e}")
    
    # ===============================
    # POSITIONS AND ORDERS METHODS
    # ===============================
    
    def update_real_positions(self, positions: List[Dict[str, Any]]):
        """Update real positions from Hyperliquid"""
        try:
            # Update in data store
            realtime_data_store.update_real_positions(positions)
            
            # Publish positions update event
            data_publisher.publish_positions_update(positions)
            
            logger.debug(f"🔄 Coordinated real positions update: {len(positions)} positions")
            
        except Exception as e:
            logger.error(f"Error coordinating real positions update: {e}")
    
    def update_real_orders(self, orders: List[Dict[str, Any]]):
        """Update real orders from Hyperliquid"""
        try:
            # Update in data store
            realtime_data_store.update_real_orders(orders)
            
            # Publish orders update event
            data_publisher.publish_event("orders_update", orders)
            
            logger.debug(f"🔄 Coordinated real orders update: {len(orders)} orders")
            
        except Exception as e:
            logger.error(f"Error coordinating real orders update: {e}")
    
    def add_simulated_position(self, position: Dict[str, Any]):
        """Add a simulated position"""
        try:
            # Add to data store
            realtime_data_store.add_simulated_position(position)
            
            # Publish simulated position event
            data_publisher.publish_event("simulated_position_added", position)
            
            logger.debug(f"📈 Coordinated simulated position addition")
            
        except Exception as e:
            logger.error(f"Error coordinating simulated position addition: {e}")
    
    # ===============================
    # PREDICTIONS AND VOLUME METHODS
    # ===============================
    
    def update_predictions(self, predictions_data: List[Dict[str, Any]]):
        """Update current trading predictions"""
        try:
            # Update in data store
            realtime_data_store.update_predictions(predictions_data)
            
            # Publish predictions update event
            data_publisher.publish_predictions_updated(predictions_data)
            
            logger.debug(f"🎯 Coordinated predictions update: {len(predictions_data)} predictions")
            
        except Exception as e:
            logger.error(f"Error coordinating predictions update: {e}")
    
    def update_global_volume(self, volume_data: Dict[str, Any]):
        """Update global volume data"""
        try:
            # Update in data store
            realtime_data_store.update_global_volume(volume_data)
            
            # Publish global volume update event
            data_publisher.publish_event("global_volume_updated", volume_data)
            
            logger.debug("🌍 Coordinated global volume update")
            
        except Exception as e:
            logger.error(f"Error coordinating global volume update: {e}")
    
    def update_blockchain_sentiment(self, sentiment_data: Dict[str, Any]):
        """Update blockchain sentiment data"""
        try:
            # Update in data store
            realtime_data_store.update_blockchain_sentiment(sentiment_data)
            
            # Publish blockchain sentiment update event
            data_publisher.publish_event("blockchain_sentiment_updated", sentiment_data)
            
            logger.debug("🧠 Coordinated blockchain sentiment update")
            
        except Exception as e:
            logger.error(f"Error coordinating blockchain sentiment update: {e}")
    
    # ===============================
    # DATA ACCESS METHODS
    # ===============================
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get complete current state for dashboard"""
        try:
            # Get base state from data store
            state = realtime_data_store.get_complete_state()
            
            # Add performance metrics
            state["performance"] = performance_tracker.get_performance_metrics()
            
            # Add performance summary
            state["performance_summary"] = performance_tracker.get_performance_summary()
            
            return state
            
        except Exception as e:
            logger.error(f"Error getting current state: {e}")
            return {}
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get current session data"""
        return realtime_data_store.get_session_data()
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get current market data"""
        return realtime_data_store.get_market_data()
    
    def get_recent_trades(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades"""
        return realtime_data_store.get_recent_trades(count)
    
    def get_recent_signals(self, count: int = 8) -> List[Dict[str, Any]]:
        """Get recent signals"""
        return realtime_data_store.get_recent_signals(count)
    
    def get_recent_activity(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent activity"""
        return realtime_data_store.get_recent_activity(count)
    
    # ===============================
    # SUBSCRIBER MANAGEMENT METHODS
    # ===============================
    
    def subscribe_to_updates(self, callback: Callable, event_types: List[str] = None):
        """Subscribe to real-time updates"""
        return data_publisher.subscribe_to_updates(callback, event_types)
    
    def unsubscribe_from_updates(self, callback: Callable = None, subscriber_index: int = None):
        """Unsubscribe from updates"""
        data_publisher.unsubscribe_from_updates(callback, subscriber_index)
    
    # ===============================
    # DATABASE AND ANALYTICS METHODS
    # ===============================
    
    def get_historical_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical trades from database"""
        return database_manager.get_historical_trades(limit)
    
    def get_performance_analysis(self, days: int = 7) -> Dict[str, Any]:
        """Get performance analysis for specified period"""
        return database_manager.get_performance_analysis(days)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return performance_tracker.get_performance_metrics()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get formatted performance summary"""
        return performance_tracker.get_performance_summary()
    
    # ===============================
    # FILE SHARING METHODS (for compatibility)
    # ===============================
    
    def _save_to_json_file(self):
        """Save current state to JSON file for cross-process sharing"""
        try:
            # Get current state
            state = realtime_data_store.get_complete_state()
            
            # Create simplified state for file sharing
            file_state = {
                "session": state["session"],
                "market": state["market"],
                "predictions": state["predictions"],
                "recent_activity": state["recent_activity"],
                "recent_signals": state["recent_signals"],
                "recent_trades": state["recent_trades"],
                "last_update": time.time()
            }
            
            # Save to JSON file
            json_file_path = "data/cache/rtm_state.json"
            with open(json_file_path, 'w') as f:
                json.dump(file_state, f, indent=2, default=str)
                
            logger.debug("💾 State saved to JSON file")
                
        except Exception as e:
            logger.debug(f"Error saving to JSON file: {e}")
    
    def _load_from_json_file(self):
        """Load state from JSON file if available (for compatibility)"""
        try:
            json_file_path = "data/cache/rtm_state.json"
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r') as f:
                    loaded_state = json.load(f)
                
                # Update current state with loaded data (but skip trades to prevent phantoms)
                if "session" in loaded_state:
                    realtime_data_store.update_session_data(loaded_state["session"])
                if "market" in loaded_state:
                    realtime_data_store.update_market_data(loaded_state["market"])
                if "predictions" in loaded_state:
                    realtime_data_store.update_predictions(loaded_state["predictions"])
                
                logger.info(f"✅ Loaded state from {json_file_path}")
            
        except Exception as e:
            logger.error(f"Error loading state from JSON file: {e}")
    
    # ===============================
    # UTILITY METHODS
    # ===============================
    
    def clear_all_data(self):
        """Clear all in-memory data (for testing)"""
        try:
            realtime_data_store.clear_historical_data()
            performance_tracker.reset_metrics()
            logger.warning("🧹 All coordinated data cleared")
            
        except Exception as e:
            logger.error(f"Error clearing all data: {e}")
    
    def export_to_json(self, filepath: str):
        """Export current state to JSON file"""
        try:
            state = self.get_current_state()
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            logger.success(f"📁 Coordinated state exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Export error: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            return {
                "coordinator_active": True,
                "session_active": session_manager.is_session_active(),
                "current_session": session_manager.get_current_session_info(),
                "subscriber_stats": data_publisher.get_subscriber_stats(),
                "performance_metrics": performance_tracker.get_performance_metrics(),
                "database_stats": database_manager.get_database_stats(),
                "data_store_counts": {
                    "recent_trades": len(realtime_data_store.get_recent_trades(1000)),
                    "recent_signals": len(realtime_data_store.get_recent_signals(1000)),
                    "recent_activity": len(realtime_data_store.get_recent_activity(1000))
                },
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}


# Global instance (singleton) - maintains compatibility
trading_data_manager = DataManagerCoordinator()