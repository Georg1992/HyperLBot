#!/usr/bin/env python3
"""
Centralized Market Data Manager
Eliminates redundant calculations and provides single source of truth for all market data
"""

import time
import statistics
from typing import Dict, List, Any, Optional
from loguru import logger

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
            volume_data = hyperliquid_api.get_enhanced_volume_analysis(symbol)
            volatility_data = hyperliquid_api.get_enhanced_volatility_analysis(symbol)
            ultimate_pressure_data = hyperliquid_api.get_enhanced_ultimate_pressure(symbol)
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
        """Centralized RSI calculation to eliminate redundant calculations"""
        cache_key = f"rsi_{periods}_{hash(str(candles[-periods:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < periods + 1:
                return {"rsi": None, "trend": "NEUTRAL", "signal": "NEUTRAL"}
            
            # Calculate price changes
            closes = [candle["close"] for candle in candles]
            changes = []
            
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                changes.append(change)
            
            if len(changes) < periods:
                return {"rsi": None, "trend": "NEUTRAL", "signal": "NEUTRAL"}
            
            # Calculate gains and losses
            gains = [change if change > 0 else 0 for change in changes]
            losses = [-change if change < 0 else 0 for change in changes]
            
            # Calculate average gain and loss using Wilder's smoothing
            avg_gain = sum(gains[-periods:]) / periods
            avg_loss = sum(losses[-periods:]) / periods
            
            # Calculate RS and RSI
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Determine trend and signal
            if rsi > 70:
                trend = "OVERBOUGHT"
                signal = "SELL"
            elif rsi < 30:
                trend = "OVERSOLD"
                signal = "BUY"
            else:
                trend = "NEUTRAL"
                signal = "NEUTRAL"
            
            result = {
                "rsi": round(rsi, 2),
                "trend": trend,
                "signal": signal,
                "avg_gain": avg_gain,
                "avg_loss": avg_loss,
                "rs": rs if avg_loss > 0 else None
            }
            
            self._cache_data(cache_key, result, self._indicator_cache_duration)
            return result
            
        except Exception as e:
            logger.error(f"❌ RSI calculation failed: {e}")
            return {"rsi": None, "trend": "NEUTRAL", "signal": "NEUTRAL"}
    
    def calculate_trend(self, candles: List[Dict], periods: int = 5) -> Dict[str, Any]:
        """Centralized trend calculation to eliminate redundant calculations"""
        cache_key = f"trend_{periods}_{hash(str(candles[-periods:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < periods:
                return {"trend": "SIDEWAYS", "strength": 0, "direction": 0}
            
            # Get recent closes
            recent_closes = [candle["close"] for candle in candles[-periods:]]
            
            # Calculate trend direction
            first_price = recent_closes[0]
            last_price = recent_closes[-1]
            price_change = last_price - first_price
            price_change_pct = (price_change / first_price) * 100
            
            # Calculate trend strength based on consistency
            up_moves = 0
            down_moves = 0
            
            for i in range(1, len(recent_closes)):
                if recent_closes[i] > recent_closes[i-1]:
                    up_moves += 1
                elif recent_closes[i] < recent_closes[i-1]:
                    down_moves += 1
            
            total_moves = up_moves + down_moves
            if total_moves == 0:
                strength = 0
            else:
                strength = max(up_moves, down_moves) / total_moves
            
            # Determine trend
            if price_change_pct > 1.0 and strength > 0.6:
                trend = "UPTREND"
                direction = 1
            elif price_change_pct < -1.0 and strength > 0.6:
                trend = "DOWNTREND"
                direction = -1
            else:
                trend = "SIDEWAYS"
                direction = 0
            
            result = {
                "trend": trend,
                "strength": round(strength, 3),
                "direction": direction,
                "price_change_pct": round(price_change_pct, 2),
                "up_moves": up_moves,
                "down_moves": down_moves
            }
            
            self._cache_data(cache_key, result, self._indicator_cache_duration)
            return result
            
        except Exception as e:
            logger.error(f"❌ Trend calculation failed: {e}")
            return {"trend": "SIDEWAYS", "strength": 0, "direction": 0}
    
    def calculate_volatility(self, candles: List[Dict], periods: int = 20) -> float:
        """Centralized volatility calculation to eliminate redundant calculations"""
        cache_key = f"volatility_{periods}_{hash(str(candles[-periods:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < periods:
                return 0.0
            
            recent_candles = candles[-periods:]
            returns = []
            
            for i in range(1, len(recent_candles)):
                prev_close = recent_candles[i-1]["close"]
                curr_close = recent_candles[i]["close"]
                ret = abs((curr_close - prev_close) / prev_close)
                returns.append(ret)
            
            if not returns:
                return 0.0
            
            # Calculate traditional volatility (baseline)
            baseline_volatility = statistics.mean(returns)
            
            # Calculate recent volatility (last 25% of periods) for spike detection
            recent_period_count = max(3, periods // 4)
            recent_returns = returns[-recent_period_count:]
            recent_volatility = statistics.mean(recent_returns) if recent_returns else baseline_volatility
            
            # Weight recent volatility more heavily to catch spikes
            if recent_volatility > baseline_volatility * 1.5:
                enhanced_volatility = baseline_volatility * 0.7 + recent_volatility * 0.3
            else:
                enhanced_volatility = baseline_volatility * 0.8 + recent_volatility * 0.2
            
            result = round(enhanced_volatility, 6)
            self._cache_data(cache_key, result, self._indicator_cache_duration)
            return result
            
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
