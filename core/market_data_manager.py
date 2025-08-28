#!/usr/bin/env python3
"""
Centralized Market Data Manager
Eliminates redundant calculations and provides single source of truth for all market data
"""

import time
import statistics
from typing import Dict, List, Any, Optional
from loguru import logger
# Removed volatility_calculator import as it was deleted

class MarketDataManager:
    """Centralized market data manager to eliminate redundant calculations"""
    
    def __init__(self):
        # Cache for market data to avoid redundant API calls
        self._market_data_cache = {}
        self._cache_timestamps = {}
        self._cache_duration = 5  # 5 seconds cache for real-time data
        
        # Cache for calculated indicators
        self._indicator_cache = {}
        self._indicator_timestamps = {}
        self._indicator_cache_duration = 60  # 1 minute for calculated indicators
        
        # Volatility calculation will be done inline
        
        logger.info("📊 Market Data Manager initialized - Centralized data management")
    
    def _get_cached_data(self, key: str, cache_duration: int) -> Optional[Dict]:
        """Get cached data if still valid"""
        if key in self._market_data_cache:
            timestamp = self._cache_timestamps.get(key, 0)
            if time.time() - timestamp < cache_duration:
                return self._market_data_cache[key]
        return None
    
    def _cache_data(self, key: str, data: Dict, cache_duration: int):
        """Cache data with timestamp"""
        self._market_data_cache[key] = data
        self._cache_timestamps[key] = time.time()
    
    def get_hyperliquid_data(self, hyperliquid_api, symbol: str = "BTC") -> Dict[str, Any]:
        """Get all Hyperliquid data with caching to avoid redundant API calls"""
        cache_key = f"hyperliquid_{symbol}"
        cached_data = self._get_cached_data(cache_key, self._cache_duration)
        
        if cached_data:
            return cached_data
        
        try:
            # Fetch all Hyperliquid data in one call
            volume_data = hyperliquid_api.get_volume_analysis(symbol)
            volatility_data = hyperliquid_api.get_volatility_analysis(symbol)
            ultimate_pressure_data = hyperliquid_api.get_ultimate_pressure(symbol)
            current_price = hyperliquid_api.get_current_price(symbol)
            
            data = {
                "volume_data": volume_data or {},
                "volatility_data": volatility_data or {},
                "ultimate_pressure_data": ultimate_pressure_data or {},
                "current_price": current_price,
                "timestamp": time.time()
            }
            
            self._cache_data(cache_key, data, self._cache_duration)
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid data: {e}")
            return {
                "volume_data": {},
                "volatility_data": {},
                "ultimate_pressure_data": {},
                "current_price": None,
                "timestamp": time.time()
            }
    
    def calculate_rsi(self, candles: List[Dict], periods: int = 14) -> Dict[str, Any]:
        """
        Centralized RSI calculation using standard Wilder's smoothing method
        This matches the RSI calculation used by Hyperliquid and other major platforms
        """
        cache_key = f"rsi_{periods}_{hash(str(candles[-periods*2:]))}"  # Use more candles for cache key
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            # Need at least periods + 1 candles for RSI calculation
            if len(candles) < periods + 1:
                logger.warning(f"⚠️ Insufficient candles for RSI: {len(candles)} (need {periods + 1})")
                return {"rsi": None, "trend": "NEUTRAL", "signal": "NEUTRAL", "error": "insufficient_data"}
            
            # Extract closing prices
            closes = [float(candle["close"]) for candle in candles if candle.get("close")]
            
            if len(closes) < periods + 1:
                logger.warning(f"⚠️ Insufficient valid closing prices: {len(closes)} (need {periods + 1})")
                return {"rsi": None, "trend": "NEUTRAL", "signal": "NEUTRAL", "error": "insufficient_closes"}
            
            # Calculate price changes (deltas)
            deltas = []
            for i in range(1, len(closes)):
                delta = closes[i] - closes[i-1]
                deltas.append(delta)
            
            if len(deltas) < periods:
                logger.warning(f"⚠️ Insufficient price deltas for RSI: {len(deltas)} (need {periods})")
                return {"rsi": None, "trend": "NEUTRAL", "signal": "NEUTRAL", "error": "insufficient_deltas"}
            
            # Separate gains and losses
            gains = [delta if delta > 0 else 0.0 for delta in deltas]
            losses = [abs(delta) if delta < 0 else 0.0 for delta in deltas]
            
            # Calculate initial averages using SMA for first calculation
            if len(gains) >= periods and len(losses) >= periods:
                # Initial averages (SMA of first period)
                initial_avg_gain = sum(gains[:periods]) / periods
                initial_avg_loss = sum(losses[:periods]) / periods
                
                # Apply Wilder's smoothing for remaining periods
                avg_gain = initial_avg_gain
                avg_loss = initial_avg_loss
                
                # If we have more data, apply Wilder's smoothing
                for i in range(periods, len(gains)):
                    avg_gain = ((avg_gain * (periods - 1)) + gains[i]) / periods
                    avg_loss = ((avg_loss * (periods - 1)) + losses[i]) / periods
            else:
                # Fallback to simple averages if not enough data
                avg_gain = sum(gains[-periods:]) / periods
                avg_loss = sum(losses[-periods:]) / periods
            
            # Calculate RS and RSI
            if avg_loss == 0.0:
                # All gains, no losses = maximum RSI
                rsi = 100.0
                rs = float('inf')
            elif avg_gain == 0.0:
                # All losses, no gains = minimum RSI  
                rsi = 0.0
                rs = 0.0
            else:
                # Normal calculation
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            
            # Ensure RSI is within bounds
            rsi = max(0.0, min(100.0, rsi))
            
            # Determine trend and signal based on standard RSI levels
            if rsi >= 70:
                trend = "OVERBOUGHT"
                signal = "SELL"
            elif rsi <= 30:
                trend = "OVERSOLD" 
                signal = "BUY"
            elif rsi >= 60:
                trend = "STRONG"
                signal = "NEUTRAL"
            elif rsi <= 40:
                trend = "WEAK"
                signal = "NEUTRAL"
            else:
                trend = "NEUTRAL"
                signal = "NEUTRAL"
            
            result = {
                "rsi": round(rsi, 2),
                "trend": trend,
                "signal": signal,
                "avg_gain": round(avg_gain, 6),
                "avg_loss": round(avg_loss, 6),
                "rs": round(rs, 4) if rs != float('inf') else None,
                "data_points": len(candles),
                "periods_used": periods,
                "calculation_method": "wilders_smoothing"
            }
            
            self._cache_data(cache_key, result, self._indicator_cache_duration)
            logger.debug(f"✅ RSI calculated: {rsi:.2f} ({trend}) from {len(candles)} candles")
            return result
            
        except Exception as e:
            logger.error(f"❌ RSI calculation failed: {e}")
            return {"rsi": None, "trend": "NEUTRAL", "signal": "NEUTRAL", "error": str(e)}
    
    def calculate_trend(self, candles: List[Dict], periods: int = 5) -> Dict[str, Any]:
        """Use trend manager for advanced trend calculation"""
        from core.trend_manager import trend_manager
        return trend_manager.calculate_trend(candles, periods)
    
    def calculate_volatility(self, candles: List[Dict], periods: int = 20) -> float:
        """Centralized volatility calculation using standard deviation"""
        cache_key = f"volatility_{periods}_{hash(str(candles[-periods:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < periods:
                return 0.0
            
            # Calculate volatility using standard deviation of price changes
            recent_candles = candles[-periods:]
            closes = [float(candle["close"]) for candle in recent_candles if candle.get("close")]
            
            if len(closes) < 2:
                return 0.0
            
            # Calculate percentage price changes
            price_changes = []
            for i in range(1, len(closes)):
                change = (closes[i] - closes[i-1]) / closes[i-1]
                price_changes.append(change)
            
            if not price_changes:
                return 0.0
            
            # Calculate standard deviation
            mean_change = sum(price_changes) / len(price_changes)
            variance = sum((change - mean_change) ** 2 for change in price_changes) / len(price_changes)
            volatility = variance ** 0.5
            
            self._cache_data(cache_key, volatility, self._indicator_cache_duration)
            return volatility
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation failed: {e}")
            return 0.0
    
    def calculate_support_resistance(self, candles: List[Dict], lookback: int = 20) -> Dict[str, float]:
        """Centralized support/resistance calculation to eliminate redundant calculations"""
        cache_key = f"support_resistance_{lookback}_{hash(str(candles[-lookback:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < lookback:
                return {"support": 0.0, "resistance": 0.0}
            
            recent_candles = candles[-lookback:]
            highs = [candle["high"] for candle in recent_candles]
            lows = [candle["low"] for candle in recent_candles]
            
            resistance = max(highs)
            support = min(lows)
            
            result = {
                "support": round(support, 2),
                "resistance": round(resistance, 2)
            }
            
            self._cache_data(cache_key, result, self._indicator_cache_duration)
            return result
            
        except Exception as e:
            logger.error(f"❌ Support/resistance calculation failed: {e}")
            return {"support": 0.0, "resistance": 0.0}
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status for monitoring"""
        current_time = time.time()
        status = {
            "market_data_cache": {},
            "indicator_cache": {},
            "total_cached_items": len(self._market_data_cache) + len(self._indicator_cache)
        }
        
        for key, timestamp in self._cache_timestamps.items():
            age = current_time - timestamp
            if key in self._market_data_cache:
                status["market_data_cache"][key] = {
                    "age_seconds": round(age, 1),
                    "valid": age < self._cache_duration
                }
            else:
                status["indicator_cache"][key] = {
                    "age_seconds": round(age, 1),
                    "valid": age < self._indicator_cache_duration
                }
        
        return status

# Global instance
market_data_manager = MarketDataManager()
