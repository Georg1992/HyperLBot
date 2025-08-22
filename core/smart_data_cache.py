#!/usr/bin/env python3
"""
Smart Data Cache for Trading Bot
Intelligent data fetching that loads historical data once and incrementally updates
Eliminates redundant API calls and improves performance significantly
"""

import time
import json
from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime, timedelta
from collections import deque
import threading

class SmartDataCache:
    """
    Intelligent data cache for trading bot
    - Fetches historical data ONCE at session start
    - Only fetches NEW candles during trading
    - Maintains rolling buffers for all timeframes
    - Drastically reduces API calls
    """
    
    def __init__(self, yahoo_fetcher, hyperliquid_api):
        self.yahoo_fetcher = yahoo_fetcher
        self.hyperliquid_api = hyperliquid_api
        
        # Rolling candle buffers (thread-safe)
        self.cache_lock = threading.Lock()
        self.candle_buffers = {
            "1m": deque(maxlen=120),   # 2 hours of 1m candles
            "5m": deque(maxlen=144),   # 12 hours of 5m candles  
            "1h": deque(maxlen=168),   # 7 days of 1h candles
            "1d": deque(maxlen=60)     # 60 days of 1d candles
        }
        
        # Timestamp tracking for each timeframe (uses open_time from Yahoo Finance)
        self.last_candle_time = {
            "1m": 0,
            "5m": 0, 
            "1h": 0,
            "1d": 0
        }
        
        # Cache status
        self.cache_initialized = False
        self.initialization_time = 0
        self.total_api_calls_saved = 0
        
        # Market analysis cache (derived data)
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
        
        # Performance tracking
        self.performance_stats = {
            "initial_data_fetch_time": 0,
            "average_update_time": 0,
            "api_calls_made": 0,
            "api_calls_saved": 0,
            "cache_hit_ratio": 0.0
        }
        
        logger.info("🧠 Smart Data Cache initialized - Ready for intelligent fetching")
    
    def initialize_historical_data(self, symbol: str = "BTC") -> bool:
        """
        ONE-TIME: Fetch all historical data needed for trading
        This runs once at session start
        """
        logger.info("📚 INITIALIZING HISTORICAL DATA - This happens only once per session...")
        start_time = time.time()
        
        try:
            with self.cache_lock:
                # Fetch initial datasets for all timeframes
                logger.info("   📊 Fetching 1-minute candles (120 candles, 2 hours)...")
                candles_1m = self.yahoo_fetcher.get_1m_klines(symbol, 120)
                if candles_1m and len(candles_1m) >= 20:  # Realistic threshold
                    self.candle_buffers["1m"].extend(candles_1m)
                    self.last_candle_time["1m"] = candles_1m[-1]["open_time"]
                    logger.success(f"      ✅ 1m candles: {len(candles_1m)} loaded")
                else:
                    logger.warning("      ⚠️ Insufficient 1m candle data")
                
                logger.info("   📈 Fetching 5-minute candles (144 candles, 12 hours)...")
                candles_5m = self.yahoo_fetcher.get_klines(symbol, "5m", 144)
                if candles_5m and len(candles_5m) >= 20:  # Realistic threshold  
                    self.candle_buffers["5m"].extend(candles_5m)
                    self.last_candle_time["5m"] = candles_5m[-1]["open_time"]
                    logger.success(f"      ✅ 5m candles: {len(candles_5m)} loaded")
                else:
                    logger.warning("      ⚠️ Insufficient 5m candle data")
                
                logger.info("   📊 Fetching 1-hour candles (168 candles, 7 days)...")
                candles_1h = self.yahoo_fetcher.get_klines(symbol, "1h", 168)
                if candles_1h and len(candles_1h) >= 20:  # Realistic threshold
                    self.candle_buffers["1h"].extend(candles_1h)
                    self.last_candle_time["1h"] = candles_1h[-1]["open_time"]
                    logger.success(f"      ✅ 1h candles: {len(candles_1h)} loaded")
                else:
                    logger.warning("      ⚠️ Insufficient 1h candle data")
                
                logger.info("   📅 Fetching daily candles (60 candles, 2 months)...")
                candles_1d = self.yahoo_fetcher.get_klines(symbol, "1d", 60)
                if candles_1d and len(candles_1d) >= 15:  # Realistic threshold
                    self.candle_buffers["1d"].extend(candles_1d)
                    self.last_candle_time["1d"] = candles_1d[-1]["open_time"]
                    logger.success(f"      ✅ 1d candles: {len(candles_1d)} loaded")
                else:
                    logger.warning("      ⚠️ Insufficient 1d candle data")
                
                # Run initial analysis
                self._update_analysis_cache()
                
                self.cache_initialized = True
                self.initialization_time = time.time() - start_time
                
                logger.success(f"🚀 HISTORICAL DATA INITIALIZATION COMPLETE")
                logger.info(f"   ⏱️  Total time: {self.initialization_time:.2f} seconds")
                logger.info(f"   📊 Candles loaded: 1m:{len(self.candle_buffers['1m'])}, 5m:{len(self.candle_buffers['5m'])}, 1h:{len(self.candle_buffers['1h'])}, 1d:{len(self.candle_buffers['1d'])}")
                logger.info("   🎯 Ready for incremental updates during trading")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Historical data initialization failed: {e}")
            return False
    
    def update_latest_candles(self, symbol: str = "BTC") -> Dict[str, Any]:
        """
        INCREMENTAL: Only fetch NEW candles we don't have yet
        This runs frequently during trading (every 5-30 seconds)
        """
        if not self.cache_initialized:
            logger.warning("⚠️ Cache not initialized - call initialize_historical_data() first")
            return {"success": False, "reason": "Cache not initialized"}
        
        update_start = time.time()
        updates_made = {}
        
        try:
            with self.cache_lock:
                current_time = time.time() * 1000  # Convert to milliseconds for comparison
                
                # Check each timeframe for new candles
                for timeframe in ["1m", "5m", "1h", "1d"]:
                    last_time = self.last_candle_time[timeframe]
                    time_diff = (current_time - last_time) / 1000  # Convert back to seconds
                    
                    # Determine if we need new candles
                    should_update = False
                    if timeframe == "1m" and time_diff > 60:      # >1 minute
                        should_update = True
                    elif timeframe == "5m" and time_diff > 300:   # >5 minutes
                        should_update = True
                    elif timeframe == "1h" and time_diff > 3600:  # >1 hour
                        should_update = True
                    elif timeframe == "1d" and time_diff > 86400: # >1 day
                        should_update = True
                    
                    if should_update:
                        logger.info(f"🔄 Fetching new {timeframe} candles (last: {time_diff/60:.1f}min ago)")
                        
                        # Fetch only new candles (usually just 1-2 candles)
                        if timeframe == "1m":
                            new_candles = self.yahoo_fetcher.get_1m_klines(symbol, 5)  # Last 5 candles
                        else:
                            new_candles = self.yahoo_fetcher.get_klines(symbol, timeframe, 3)  # Last 3 candles
                        
                        if new_candles:
                            # Filter out candles we already have
                            truly_new_candles = [
                                candle for candle in new_candles 
                                if candle["open_time"] > last_time
                            ]
                            
                            if truly_new_candles:
                                # Add only new candles to buffer
                                for candle in truly_new_candles:
                                    self.candle_buffers[timeframe].append(candle)
                                
                                # Update last timestamp
                                self.last_candle_time[timeframe] = truly_new_candles[-1]["open_time"]
                                
                                updates_made[timeframe] = len(truly_new_candles)
                                self.performance_stats["api_calls_made"] += 1
                                
                                logger.success(f"      ✅ Added {len(truly_new_candles)} new {timeframe} candles")
                            else:
                                # We have the latest data already
                                self.performance_stats["api_calls_saved"] += 1
                                self.total_api_calls_saved += 1
                                logger.debug(f"      💾 {timeframe} data already current (saved API call)")
                
                # Update analysis if we got new data
                if updates_made:
                    self._update_analysis_cache()
                    
                    # Update cache hit ratio
                    total_checks = self.performance_stats["api_calls_made"] + self.performance_stats["api_calls_saved"]
                    self.performance_stats["cache_hit_ratio"] = self.performance_stats["api_calls_saved"] / total_checks if total_checks > 0 else 0
                
                update_time = time.time() - update_start
                self.performance_stats["average_update_time"] = update_time
                
                return {
                    "success": True,
                    "updates_made": updates_made,
                    "update_time": update_time,
                    "cache_hit_ratio": self.performance_stats["cache_hit_ratio"],
                    "api_calls_saved": self.total_api_calls_saved
                }
                
        except Exception as e:
            logger.error(f"❌ Incremental update failed: {e}")
            return {"success": False, "reason": str(e)}
    
    def get_candles(self, timeframe: str, count: int = None) -> List[Dict[str, Any]]:
        """
        Get candles from cache (no API calls)
        Much faster than fetching from Yahoo Finance every time
        """
        with self.cache_lock:
            if timeframe not in self.candle_buffers:
                logger.warning(f"⚠️ Invalid timeframe: {timeframe}")
                return []
            
            buffer = self.candle_buffers[timeframe]
            if not buffer:
                logger.warning(f"⚠️ No {timeframe} candles in cache")
                return []
            
            if count is None:
                return list(buffer)
            else:
                return list(buffer)[-count:]  # Return last N candles
    
    def get_latest_candle(self, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get the most recent candle for a timeframe"""
        with self.cache_lock:
            buffer = self.candle_buffers.get(timeframe, [])
            return buffer[-1] if buffer else None
    
    def get_market_analysis(self, symbol: str = "BTC", current_price: float = None) -> Dict[str, Any]:
        """
        Get comprehensive market analysis using cached data
        Much faster than recalculating every time
        """
        with self.cache_lock:
            # Check if analysis is still fresh (update every 30 seconds)
            current_time = time.time()
            if current_time - self.analysis_cache["last_analysis_update"] < 30:
                # Return cached analysis
                self.performance_stats["api_calls_saved"] += 1
                logger.debug("💾 Using cached market analysis (saved computation)")
                
                analysis = self.analysis_cache.copy()
                if current_price:
                    analysis["current_price"] = current_price
                return analysis
            
            # Update analysis with latest cached candles
            return self._update_analysis_cache(current_price)
    
    def _update_analysis_cache(self, current_price: float = None) -> Dict[str, Any]:
        """Update market analysis using cached candle data"""
        try:
            analysis = {}
            
            # Get candles from cache (no API calls!)
            candles_5m = list(self.candle_buffers["5m"])
            candles_1h = list(self.candle_buffers["1h"])
            candles_1d = list(self.candle_buffers["1d"])
            
            if len(candles_5m) >= 15:
                # 5-minute analysis
                analysis["candles_5m"] = candles_5m
                analysis["support_resistance_5m"] = self._calculate_support_resistance(candles_5m)
                analysis["trend_5m"] = self._calculate_trend(candles_5m)
                analysis["volatility_5m"] = self._calculate_volatility(candles_5m)
                
                logger.debug(f"📊 5m analysis: {len(candles_5m)} candles, trend: {analysis['trend_5m'].get('trend', 'UNKNOWN')}")
            
            if len(candles_1h) >= 15:
                # 1-hour analysis
                analysis["candles_1h"] = candles_1h
                analysis["support_resistance_1h"] = self._calculate_support_resistance(candles_1h)
                analysis["trend_1h"] = self._calculate_trend(candles_1h)
                analysis["volatility_1h"] = self._calculate_volatility(candles_1h)
                
                logger.debug(f"📈 1h analysis: {len(candles_1h)} candles, trend: {analysis['trend_1h'].get('trend', 'UNKNOWN')}")
            
            if len(candles_1d) >= 10:
                # Daily analysis
                analysis["candles_1d"] = candles_1d
                analysis["trend_1d"] = self._calculate_trend(candles_1d)
                
                logger.debug(f"📅 1d analysis: {len(candles_1d)} candles, trend: {analysis['trend_1d'].get('trend', 'UNKNOWN')}")
            
            # Current price integration
            if current_price:
                analysis["current_price"] = current_price
                analysis["hyperliquid_price"] = current_price
                
                # Price vs analysis comparison
                if analysis.get("support_resistance_5m"):
                    support = analysis["support_resistance_5m"].get("support", 0)
                    resistance = analysis["support_resistance_5m"].get("resistance", 0)
                    if support > 0 and resistance > 0:
                        range_position = (current_price - support) / (resistance - support)
                        analysis["range_position"] = range_position
                        logger.debug(f"💰 Price position: {range_position:.1%} of range")
            
            # Determine overall market condition
            volatility_5m = analysis.get("volatility_5m", 0)
            if volatility_5m > 0.008:
                analysis["market_condition"] = "HIGH_VOLATILITY_OPTIMAL"
            elif volatility_5m > 0.004:
                analysis["market_condition"] = "MEDIUM_VOLATILITY_OPTIMAL"
            elif volatility_5m > 0.002:
                analysis["market_condition"] = "LOW_VOLATILITY_OPTIMAL"
            else:
                analysis["market_condition"] = "LOW_VOLATILITY_CHOPPY"
            
            # Cache the analysis
            self.analysis_cache.update(analysis)
            self.analysis_cache["last_analysis_update"] = time.time()
            
            computation_time = time.time() - (current_time if 'current_time' in locals() else time.time())
            logger.info(f"🧮 Market analysis updated in {computation_time:.3f}s using cached data")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Analysis update error: {e}")
            return self.analysis_cache.copy()
    
    def _calculate_support_resistance(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate support and resistance from cached candles"""
        if len(candles) < 10:
            return {"support": 0, "resistance": 0}
        
        try:
            # Get recent highs and lows
            recent_candles = candles[-20:] if len(candles) >= 20 else candles
            highs = [c["high"] for c in recent_candles]
            lows = [c["low"] for c in recent_candles]
            
            # Simple support/resistance calculation
            resistance = max(highs[-10:] if len(highs) >= 10 else highs)
            support = min(lows[-10:] if len(lows) >= 10 else lows)
            
            return {
                "support": support,
                "resistance": resistance,
                "range_size": resistance - support,
                "calculation_method": "cached_data"
            }
            
        except Exception as e:
            logger.debug(f"Support/resistance calculation error: {e}")
            return {"support": 0, "resistance": 0}
    
    def _calculate_trend(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend from cached candles"""
        if len(candles) < 5:
            return {"trend": "UNKNOWN", "strength": 0.0}
        
        try:
            # Get recent closes
            recent_closes = [c["close"] for c in (candles[-10:] if len(candles) >= 10 else candles)]
            
            # Calculate trend
            first_price = recent_closes[0]
            last_price = recent_closes[-1]
            price_change = (last_price - first_price) / first_price
            
            # Determine trend (using crypto-appropriate thresholds)
            if price_change > 0.002:    # >0.2%
                trend = "STRONG_UP"
            elif price_change > 0.0005: # >0.05%
                trend = "UP"
            elif price_change > 0.0001: # >0.01%
                trend = "WEAK_UP"
            elif price_change < -0.002:   # <-0.2%
                trend = "STRONG_DOWN"
            elif price_change < -0.0005:  # <-0.05%
                trend = "DOWN"
            elif price_change < -0.0001:  # <-0.01%
                trend = "WEAK_DOWN"
            else:
                trend = "SIDEWAYS"
            
            return {
                "trend": trend,
                "strength": abs(price_change),
                "price_change_pct": price_change,
                "calculation_method": "cached_data"
            }
            
        except Exception as e:
            logger.debug(f"Trend calculation error: {e}")
            return {"trend": "UNKNOWN", "strength": 0.0}
    
    def _calculate_volatility(self, candles: List[Dict[str, Any]]) -> float:
        """Calculate volatility from cached candles"""
        if len(candles) < 5:
            return 0.003  # Default volatility
        
        try:
            # Get recent closes
            recent_closes = [c["close"] for c in (candles[-20:] if len(candles) >= 20 else candles)]
            
            # Calculate returns
            returns = [(recent_closes[i] - recent_closes[i-1]) / recent_closes[i-1] 
                      for i in range(1, len(recent_closes))]
            
            # Calculate volatility (standard deviation of returns)
            import statistics
            volatility = statistics.stdev(returns) if len(returns) > 1 else 0.003
            
            return max(0.0001, min(0.05, volatility))  # Cap between 0.01% and 5%
            
        except Exception as e:
            logger.debug(f"Volatility calculation error: {e}")
            return 0.003
    
    def get_cache_performance(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_checks = self.performance_stats["api_calls_made"] + self.performance_stats["api_calls_saved"]
        
        return {
            "cache_initialized": self.cache_initialized,
            "initialization_time": self.initialization_time,
            "candle_counts": {tf: len(buffer) for tf, buffer in self.candle_buffers.items()},
            "last_candle_times": self.last_candle_time.copy(),
            "api_calls_made": self.performance_stats["api_calls_made"],
            "api_calls_saved": self.performance_stats["api_calls_saved"],
            "cache_hit_ratio": self.performance_stats["cache_hit_ratio"],
            "total_api_calls_saved": self.total_api_calls_saved,
            "average_update_time": self.performance_stats["average_update_time"]
        }
    
    def is_data_stale(self, timeframe: str, max_age_minutes: int = 30) -> bool:
        """Check if data for a timeframe is stale"""
        last_time = self.last_candle_time.get(timeframe, 0)
        age_minutes = ((time.time() * 1000) - last_time) / (60 * 1000)  # Convert to minutes
        return age_minutes > max_age_minutes
    
    def get_data_freshness(self) -> Dict[str, Any]:
        """Get data freshness report"""
        current_time = time.time() * 1000  # Convert to milliseconds
        freshness = {}
        
        for timeframe in ["1m", "5m", "1h", "1d"]:
            last_time = self.last_candle_time[timeframe]
            age_minutes = (current_time - last_time) / (60 * 1000)  # Convert to minutes
            
            if timeframe == "1m" and age_minutes < 2:
                status = "FRESH"
            elif timeframe == "5m" and age_minutes < 10:
                status = "FRESH"
            elif timeframe == "1h" and age_minutes < 120:
                status = "FRESH"
            elif timeframe == "1d" and age_minutes < 1440:
                status = "FRESH"
            else:
                status = "STALE"
            
            freshness[timeframe] = {
                "status": status,
                "age_minutes": age_minutes,
                "candle_count": len(self.candle_buffers[timeframe]),
                "last_update": datetime.fromtimestamp(last_time / 1000).strftime("%H:%M:%S") if last_time > 0 else "Never"
            }
        
        return freshness