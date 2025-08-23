#!/usr/bin/env python3
"""
Event-Driven Smart Data Cache
Automatically detects new candle data and triggers cascading updates
No more manual polling - everything happens automatically!
"""

import time
import json
import threading
from typing import Dict, Any, List, Optional, Callable
from loguru import logger
from datetime import datetime, timedelta
from collections import deque

class EventDrivenCache:
    """
    Event-driven cache that automatically detects new data and propagates updates
    - Monitors for new candles automatically
    - Triggers callbacks when data changes
    - Eliminates manual polling completely
    """
    
    def __init__(self, yahoo_fetcher, hyperliquid_api):
        self.yahoo_fetcher = yahoo_fetcher
        self.hyperliquid_api = hyperliquid_api
        
        # Thread-safe data storage
        self.cache_lock = threading.Lock()
        self.candle_buffers = {
            "1m": deque(maxlen=120),   # 2 hours of 1m candles
            "5m": deque(maxlen=144),   # 12 hours of 5m candles  
            "1h": deque(maxlen=168),   # 7 days of 1h candles
            "1d": deque(maxlen=60)     # 60 days of 1d candles
        }
        
        # Timestamp tracking for each timeframe
        self.last_candle_time = {
            "1m": 0,
            "5m": 0, 
            "1h": 0,
            "1d": 0
        }
        
        # Event callbacks - other systems register here for notifications
        self.update_callbacks = {
            "candle_update": [],       # Called when new candles arrive
            "analysis_update": [],     # Called when analysis is recalculated
            "data_change": []          # Called for any data change
        }
        
        # Monitoring system
        self.monitoring_active = False
        self.monitor_thread = None
        self.monitor_intervals = {
            "1m": 60,      # Check every 60 seconds for 1m candles
            "5m": 300,     # Check every 5 minutes for 5m candles
            "1h": 1800,    # Check every 30 minutes for 1h candles
            "1d": 3600     # Check every hour for 1d candles
        }
        
        # Performance tracking
        self.auto_updates_count = 0
        self.last_auto_update = 0
        self.callbacks_triggered = 0
        
        # Market analysis cache (auto-updated)
        self.analysis_cache = {
            "support_resistance_5m": {},
            "support_resistance_1h": {},
            "trend_5m": {},
            "trend_1h": {},
            "trend_1d": {},
            "market_condition": "UNKNOWN",
            "volatility_5m": 0.0,
            "volatility_1h": 0.0,
            "last_analysis_update": 0
        }
        
        # Cache status
        self.cache_initialized = False
        self.initialization_time = 0
        
        logger.info("🎯 Event-Driven Cache initialized - Auto-monitoring ready!")
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register a callback function for specific events"""
        if event_type in self.update_callbacks:
            self.update_callbacks[event_type].append(callback)
            logger.info(f"📡 Registered callback for '{event_type}' events")
        else:
            logger.warning(f"⚠️ Unknown event type: {event_type}")
    
    def _trigger_callbacks(self, event_type: str, data: Any = None):
        """Trigger all registered callbacks for an event type"""
        try:
            callbacks = self.update_callbacks.get(event_type, [])
            for callback in callbacks:
                try:
                    if data:
                        callback(event_type, data)
                    else:
                        callback(event_type)
                    self.callbacks_triggered += 1
                except Exception as e:
                    logger.error(f"❌ Callback error for {event_type}: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to trigger callbacks for {event_type}: {e}")
    
    def initialize_historical_data(self, symbol: str = "BTC") -> bool:
        """
        ONE-TIME: Fetch all historical data needed for trading
        Then automatically start monitoring for new data
        """
        logger.info("📚 INITIALIZING EVENT-DRIVEN CACHE - Loading historical data...")
        start_time = time.time()
        
        try:
            with self.cache_lock:
                # Fetch initial datasets for all timeframes
                logger.info("   📊 Fetching 1-minute candles (120 candles, 2 hours)...")
                candles_1m = self.yahoo_fetcher.get_1m_klines(symbol, 120)
                if candles_1m and len(candles_1m) >= 20:
                    self.candle_buffers["1m"].extend(candles_1m)
                    self.last_candle_time["1m"] = candles_1m[-1]["open_time"]
                    logger.success(f"      ✅ 1m candles: {len(candles_1m)} loaded")
                
                logger.info("   📈 Fetching 5-minute candles (144 candles, 12 hours)...")
                candles_5m = self.yahoo_fetcher.get_klines(symbol, "5m", 144)
                if candles_5m and len(candles_5m) >= 20:
                    self.candle_buffers["5m"].extend(candles_5m)
                    self.last_candle_time["5m"] = candles_5m[-1]["open_time"]
                    logger.success(f"      ✅ 5m candles: {len(candles_5m)} loaded")
                
                logger.info("   📊 Fetching 1-hour candles (168 candles, 7 days)...")
                candles_1h = self.yahoo_fetcher.get_klines(symbol, "1h", 168)
                if candles_1h and len(candles_1h) >= 15:
                    self.candle_buffers["1h"].extend(candles_1h)
                    self.last_candle_time["1h"] = candles_1h[-1]["open_time"]
                    logger.success(f"      ✅ 1h candles: {len(candles_1h)} loaded")
                
                logger.info("   📅 Fetching 1-day candles (60 candles, 60 days)...")
                candles_1d = self.yahoo_fetcher.get_klines(symbol, "1d", 60)
                if candles_1d and len(candles_1d) >= 10:
                    self.candle_buffers["1d"].extend(candles_1d)
                    self.last_candle_time["1d"] = candles_1d[-1]["open_time"]
                    logger.success(f"      ✅ 1d candles: {len(candles_1d)} loaded")
                
                # Generate initial analysis
                self._update_analysis_cache()
                
                # Mark as initialized
                self.cache_initialized = True
                self.initialization_time = time.time() - start_time
                
                logger.success(f"🎯 Cache initialized in {self.initialization_time:.2f}s")
                
                # AUTO-START monitoring for new data
                self.start_auto_monitoring(symbol)
                
                # Trigger initialization callback
                self._trigger_callbacks("data_change", {
                    "event": "initialization_complete",
                    "candles_loaded": {
                        "1m": len(self.candle_buffers["1m"]),
                        "5m": len(self.candle_buffers["5m"]),
                        "1h": len(self.candle_buffers["1h"]),
                        "1d": len(self.candle_buffers["1d"])
                    }
                })
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Cache initialization failed: {e}")
            return False
    
    def start_auto_monitoring(self, symbol: str = "BTC"):
        """Start automatic monitoring for new candle data"""
        if self.monitoring_active:
            logger.warning("⚠️ Auto-monitoring already active")
            return
        
        logger.info("🔍 STARTING AUTO-MONITORING - No more manual updates needed!")
        self.monitoring_active = True
        
        def auto_monitor():
            """Background thread that automatically checks for new data"""
            last_check_times = {timeframe: 0 for timeframe in self.monitor_intervals}
            
            while self.monitoring_active:
                try:
                    current_time = time.time()
                    updates_found = False
                    
                    # Check each timeframe based on its interval
                    for timeframe, interval in self.monitor_intervals.items():
                        if current_time - last_check_times[timeframe] >= interval:
                            last_check_times[timeframe] = current_time
                            
                            # Check for new candles
                            new_candles = self._check_for_new_candles(symbol, timeframe)
                            if new_candles:
                                logger.info(f"🔄 AUTO-DETECTED: {len(new_candles)} new {timeframe} candles!")
                                self._process_new_candles(timeframe, new_candles)
                                updates_found = True
                    
                    # Update analysis if any new data was found
                    if updates_found:
                        self._update_analysis_cache()
                        self.auto_updates_count += 1
                        self.last_auto_update = current_time
                        
                        # Trigger update callbacks
                        self._trigger_callbacks("data_change", {
                            "event": "auto_update_complete",
                            "timestamp": current_time,
                            "update_count": self.auto_updates_count
                        })
                    
                    # Smart sleep - less frequent when no updates
                    sleep_time = 30 if updates_found else 60
                    time.sleep(sleep_time)
                    
                except Exception as e:
                    logger.error(f"❌ Auto-monitoring error: {e}")
                    time.sleep(60)  # Wait before retrying
            
            logger.info("🛑 Auto-monitoring stopped")
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=auto_monitor, daemon=True)
        self.monitor_thread.start()
        
        logger.success("✅ Auto-monitoring started - Cache will update automatically!")
    
    def stop_auto_monitoring(self):
        """Stop automatic monitoring"""
        logger.info("🛑 Stopping auto-monitoring...")
        self.monitoring_active = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.success("✅ Auto-monitoring stopped")
    
    def _check_for_new_candles(self, symbol: str, timeframe: str) -> List[Dict]:
        """Check if new candles are available for a specific timeframe"""
        try:
            last_time = self.last_candle_time[timeframe]
            current_time = time.time() * 1000  # Convert to milliseconds
            
            # Determine how far to look back for new candles
            lookback_candles = 3  # Only fetch last few candles
            
            # Fetch recent candles
            if timeframe == "1m":
                recent_candles = self.yahoo_fetcher.get_1m_klines(symbol, lookback_candles)
            else:
                recent_candles = self.yahoo_fetcher.get_klines(symbol, timeframe, lookback_candles)
            
            if not recent_candles:
                return []
            
            # Filter for truly new candles
            new_candles = [
                candle for candle in recent_candles 
                if candle["open_time"] > last_time
            ]
            
            return new_candles
            
        except Exception as e:
            logger.debug(f"Error checking for new {timeframe} candles: {e}")
            return []
    
    def _process_new_candles(self, timeframe: str, new_candles: List[Dict]):
        """Process newly detected candles"""
        try:
            with self.cache_lock:
                # Add new candles to buffer
                for candle in new_candles:
                    self.candle_buffers[timeframe].append(candle)
                
                # Update last timestamp
                if new_candles:
                    self.last_candle_time[timeframe] = new_candles[-1]["open_time"]
                    
                    logger.success(f"      ✅ Added {len(new_candles)} new {timeframe} candles automatically")
                    
                    # Trigger candle update callback
                    self._trigger_callbacks("candle_update", {
                        "timeframe": timeframe,
                        "new_candles": len(new_candles),
                        "total_candles": len(self.candle_buffers[timeframe])
                    })
                
        except Exception as e:
            logger.error(f"❌ Error processing new {timeframe} candles: {e}")
    
    def _update_analysis_cache(self):
        """Update cached analysis based on current candle data"""
        try:
            if not self.cache_initialized:
                return
            
            # Get recent candles for analysis
            candles_5m = list(self.candle_buffers["5m"])
            candles_1h = list(self.candle_buffers["1h"])
            candles_1d = list(self.candle_buffers["1d"])
            
            # Update analysis using Yahoo fetcher's analysis methods
            if len(candles_5m) >= 20:
                analysis_5m = self.yahoo_fetcher._calculate_technical_indicators(candles_5m[-50:])
                self.analysis_cache.update({
                    "trend_5m": analysis_5m.get("trend", {}),
                    "support_resistance_5m": analysis_5m.get("support_resistance", {}),
                    "volatility_5m": analysis_5m.get("volatility", 0.0)
                })
            
            if len(candles_1h) >= 20:
                analysis_1h = self.yahoo_fetcher._calculate_technical_indicators(candles_1h[-100:])
                self.analysis_cache.update({
                    "trend_1h": analysis_1h.get("trend", {}),
                    "support_resistance_1h": analysis_1h.get("support_resistance", {}),
                    "volatility_1h": analysis_1h.get("volatility", 0.0)
                })
            
            if len(candles_1d) >= 10:
                analysis_1d = self.yahoo_fetcher._calculate_technical_indicators(candles_1d[-30:])
                self.analysis_cache.update({
                    "trend_1d": analysis_1d.get("trend", {})
                })
            
            # Determine overall market condition
            volatility_5m = self.analysis_cache.get("volatility_5m", 0.0)
            if volatility_5m > 0.008:
                self.analysis_cache["market_condition"] = "HIGH_VOLATILITY"
            elif volatility_5m > 0.006:
                self.analysis_cache["market_condition"] = "ELEVATED_VOLATILITY"
            elif volatility_5m > 0.003:
                self.analysis_cache["market_condition"] = "MEDIUM_VOLATILITY"
            else:
                self.analysis_cache["market_condition"] = "LOW_VOLATILITY"
            
            self.analysis_cache["last_analysis_update"] = time.time()
            
            # Trigger analysis update callback
            self._trigger_callbacks("analysis_update", self.analysis_cache.copy())
            
        except Exception as e:
            logger.error(f"❌ Analysis cache update failed: {e}")
    
    def get_candles(self, timeframe: str, count: int = None) -> List[Dict]:
        """Get candles for a specific timeframe (thread-safe)"""
        with self.cache_lock:
            candles = list(self.candle_buffers.get(timeframe, []))
            if count:
                return candles[-count:]
            return candles
    
    def get_market_analysis(self) -> Dict[str, Any]:
        """Get the current cached market analysis (thread-safe)"""
        with self.cache_lock:
            return self.analysis_cache.copy()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the event-driven cache"""
        return {
            "cache_initialized": self.cache_initialized,
            "initialization_time": self.initialization_time,
            "monitoring_active": self.monitoring_active,
            "auto_updates_count": self.auto_updates_count,
            "last_auto_update": self.last_auto_update,
            "callbacks_triggered": self.callbacks_triggered,
            "candle_counts": {
                timeframe: len(self.candle_buffers[timeframe])
                for timeframe in self.candle_buffers
            }
        }
    
    def force_update_check(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Manually trigger an update check (for testing)"""
        logger.info("🔄 Manual update check requested...")
        updates_made = {}
        
        for timeframe in self.monitor_intervals:
            new_candles = self._check_for_new_candles(symbol, timeframe)
            if new_candles:
                self._process_new_candles(timeframe, new_candles)
                updates_made[timeframe] = len(new_candles)
        
        if updates_made:
            self._update_analysis_cache()
            self._trigger_callbacks("data_change", {
                "event": "manual_update",
                "updates": updates_made
            })
        
        return {
            "success": True,
            "updates_made": updates_made,
            "message": f"Found updates: {updates_made}" if updates_made else "No new data available"
        }