#!/usr/bin/env python3
"""
Data Publisher
Handles WebSocket and subscriber notifications for real-time updates
Single Responsibility: Event publishing and subscriber management
"""

import threading
from typing import Dict, Any, List, Callable
from loguru import logger


class DataPublisher:
    """
    Manages real-time data publishing to subscribers
    Single Responsibility: Event publishing and subscriber notifications
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for publisher management"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.publisher_lock = threading.RLock()
        
        # Subscriber management
        self.subscribers = []
        self.event_handlers = {}
        
        # Event types for organization
        self.EVENT_TYPES = {
            "session_started",
            "session_ended", 
            "balance_updated",
            "market_update",
            "positions_update",
            "orders_update",
            "trade_added",
            "signal_added",
            "activity_added",
            "predictions_updated",
            "simulated_position_added",
            "simulated_position_closed",
            "simulated_balance_update",
            "global_volume_updated",
            "blockchain_sentiment_updated"
        }
        
        logger.success("📡 Data Publisher initialized")
    
    def subscribe_to_updates(self, callback: Callable, event_types: List[str] = None):
        """Subscribe to real-time updates"""
        with self.publisher_lock:
            try:
                subscriber_info = {
                    "callback": callback,
                    "event_types": event_types or list(self.EVENT_TYPES),  # Subscribe to all by default
                    "active": True,
                    "error_count": 0
                }
                
                self.subscribers.append(subscriber_info)
                
                logger.info(f"📡 New subscriber added - {len(self.subscribers)} total subscribers")
                logger.debug(f"   Subscribed to events: {event_types or 'ALL'}")
                
                return len(self.subscribers) - 1  # Return subscriber index
                
            except Exception as e:
                logger.error(f"Error adding subscriber: {e}")
                return None
    
    def unsubscribe_from_updates(self, callback: Callable = None, subscriber_index: int = None):
        """Unsubscribe from updates"""
        with self.publisher_lock:
            try:
                removed = False
                
                if subscriber_index is not None and 0 <= subscriber_index < len(self.subscribers):
                    # Remove by index
                    self.subscribers[subscriber_index]["active"] = False
                    removed = True
                elif callback is not None:
                    # Remove by callback
                    for subscriber in self.subscribers:
                        if subscriber["callback"] == callback:
                            subscriber["active"] = False
                            removed = True
                            break
                
                if removed:
                    # Clean up inactive subscribers
                    self.subscribers = [s for s in self.subscribers if s["active"]]
                    logger.info(f"📡 Subscriber removed - {len(self.subscribers)} total subscribers")
                else:
                    logger.warning("⚠️ Subscriber not found for removal")
                
            except Exception as e:
                logger.error(f"Error removing subscriber: {e}")
    
    def publish_event(self, event_type: str, data: Any):
        """Publish an event to all interested subscribers"""
        with self.publisher_lock:
            if event_type not in self.EVENT_TYPES:
                logger.warning(f"⚠️ Unknown event type: {event_type}")
            
            if not self.subscribers:
                logger.debug(f"📡 No subscribers for event: {event_type}")
                return
            
            # Track notifications
            successful_notifications = 0
            failed_notifications = 0
            
            # Notify all interested subscribers
            for i, subscriber in enumerate(self.subscribers[:]):  # Copy list to avoid modification during iteration
                try:
                    if not subscriber["active"]:
                        continue
                    
                    # Check if subscriber is interested in this event type
                    if event_type not in subscriber["event_types"]:
                        continue
                    
                    # Call subscriber callback
                    subscriber["callback"](event_type, data)
                    successful_notifications += 1
                    
                    # Reset error count on successful notification
                    subscriber["error_count"] = 0
                    
                except Exception as e:
                    failed_notifications += 1
                    subscriber["error_count"] += 1
                    
                    logger.error(f"📡 Subscriber {i} notification error: {e}")
                    
                    # Remove subscriber if too many errors
                    if subscriber["error_count"] >= 5:
                        logger.warning(f"⚠️ Removing subscriber {i} due to repeated errors")
                        subscriber["active"] = False
            
            # Clean up inactive subscribers
            active_count_before = len(self.subscribers)
            self.subscribers = [s for s in self.subscribers if s["active"]]
            removed_count = active_count_before - len(self.subscribers)
            
            if removed_count > 0:
                logger.info(f"🧹 Removed {removed_count} inactive subscribers")
            
            logger.debug(f"📡 Event '{event_type}': {successful_notifications} notified, {failed_notifications} failed")
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add a specific handler for an event type"""
        with self.publisher_lock:
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
            
            self.event_handlers[event_type].append(handler)
            logger.debug(f"📡 Handler added for event: {event_type}")
    
    def remove_event_handler(self, event_type: str, handler: Callable):
        """Remove a specific handler for an event type"""
        with self.publisher_lock:
            if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
                self.event_handlers[event_type].remove(handler)
                logger.debug(f"📡 Handler removed for event: {event_type}")
    
    def publish_with_handlers(self, event_type: str, data: Any):
        """Publish event to both subscribers and specific handlers"""
        # Publish to subscribers
        self.publish_event(event_type, data)
        
        # Execute specific handlers
        with self.publisher_lock:
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        handler(data)
                    except Exception as e:
                        logger.error(f"📡 Event handler error for {event_type}: {e}")
    
    def get_subscriber_stats(self) -> Dict[str, Any]:
        """Get statistics about subscribers"""
        with self.publisher_lock:
            active_subscribers = [s for s in self.subscribers if s["active"]]
            
            # Count subscribers by event types
            event_subscription_counts = {}
            for event_type in self.EVENT_TYPES:
                count = sum(1 for s in active_subscribers if event_type in s["event_types"])
                event_subscription_counts[event_type] = count
            
            return {
                "total_subscribers": len(active_subscribers),
                "inactive_subscribers": len(self.subscribers) - len(active_subscribers),
                "event_handlers": {event_type: len(handlers) for event_type, handlers in self.event_handlers.items()},
                "event_subscription_counts": event_subscription_counts,
                "supported_events": list(self.EVENT_TYPES)
            }
    
    def clear_all_subscribers(self):
        """Clear all subscribers (useful for testing)"""
        with self.publisher_lock:
            subscriber_count = len(self.subscribers)
            self.subscribers.clear()
            self.event_handlers.clear()
            
            logger.warning(f"🧹 Cleared {subscriber_count} subscribers and all event handlers")
    
    # Convenience methods for common events
    def publish_session_started(self, session_data: Dict[str, Any]):
        """Publish session started event"""
        self.publish_event("session_started", session_data)
    
    def publish_session_ended(self, session_data: Dict[str, Any]):
        """Publish session ended event"""
        self.publish_event("session_ended", session_data)
    
    def publish_balance_updated(self, balance_data: Dict[str, Any]):
        """Publish balance updated event"""
        self.publish_event("balance_updated", balance_data)
    
    def publish_market_update(self, market_data: Dict[str, Any]):
        """Publish market data update"""
        self.publish_event("market_update", market_data)
    
    def publish_trade_added(self, trade_data: Dict[str, Any]):
        """Publish trade added event"""
        self.publish_event("trade_added", trade_data)
    
    def publish_signal_added(self, signal_data: Dict[str, Any]):
        """Publish signal added event"""
        self.publish_event("signal_added", signal_data)
    
    def publish_activity_added(self, activity_data: Dict[str, Any]):
        """Publish activity added event"""
        self.publish_event("activity_added", activity_data)
    
    def publish_predictions_updated(self, predictions_data: List[Dict[str, Any]]):
        """Publish predictions updated event"""
        self.publish_event("predictions_updated", predictions_data)
    
    def publish_positions_update(self, positions_data: List[Dict[str, Any]]):
        """Publish positions update event"""
        self.publish_event("positions_update", positions_data)


# Global instance (singleton)
data_publisher = DataPublisher()