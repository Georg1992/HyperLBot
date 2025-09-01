#!/usr/bin/env python3
"""
Centralized Market Data Manager
Eliminates redundant calculations and provides single source of truth for all market data
"""

import time
import statistics
from typing import Dict, List, Any, Optional
from loguru import logger
from core.analysis.real_time.volatility_calculator import VolatilityCalculator
from core.analysis.trend_manager import trend_manager
from core.constants import technical_constants

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
        
        # Initialize volatility calculator
        self.volatility_calculator = VolatilityCalculator()
        
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
        # Check if hyperliquid_api is None - show explicit error instead of crashing
        if hyperliquid_api is None:
            logger.error(f"❌ HyperliquidAPI is None - cannot fetch data for {symbol}")
            return {
                "volume_data": {},
                # volatility_data removed - using 5m candle volatility instead of orderbook volatility
                "pressure_data": {},
                "current_price": None,
                "timestamp": time.time(),
                "error": "HyperliquidAPI not initialized"
            }
        
        cache_key = f"hyperliquid_{symbol}"
        cached_data = self._get_cached_data(cache_key, self._cache_duration)
        
        if cached_data:
            return cached_data
        
        try:
            # Get Hyperliquid data (removed volatility_data - using 5m candle volatility instead)
            volume_data = hyperliquid_api.get_volume_analysis(symbol)
            pressure_data = hyperliquid_api.get_pressure(symbol)
            
            
            return {
                "volume_data": volume_data or {},
                # volatility_data removed - using 5m candle volatility instead of orderbook volatility
                "pressure_data": pressure_data or {},
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid data: {e}")
            return {
                "volume_data": {},
                "volatility_data": {},
                "pressure_data": {},
                "current_price": None,
                "timestamp": time.time()
            }
    
    def calculate_trend(self, candles: List[Dict], periods: int = 5) -> Dict[str, Any]:
        """Use trend manager for advanced trend calculation"""
        return trend_manager.calculate_trend(candles, periods)
    
    def calculate_volatility(self, candles: List[Dict], periods: int = 20) -> float:
        """Centralized volatility calculation using VolatilityCalculator"""
        cache_key = f"volatility_{periods}_{hash(str(candles[-periods:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < periods:
                return 0.0
            
            # Use the centralized volatility calculator
            result = self.volatility_calculator.calculate_candle_volatility(candles[-periods:], "5m")
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
    
    def calculate_rsi_from_candles(self, candles: List[Dict], periods: int = 14) -> float:
        """
        Calculate RSI from candlestick data (moved from YahooDataFetcher for consolidation)
        Eliminates circular dependency and centralizes calculations
        """
        cache_key = f"rsi_{periods}_{hash(str(candles[-periods-1:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < periods + 1:
                return technical_constants.RSI_NEUTRAL
            
            # Calculate price changes
            closes = [float(candle['close']) for candle in candles[-(periods + 1):]]
            changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            
            # Separate gains and losses
            gains = [change if change > 0 else 0 for change in changes]
            losses = [-change if change < 0 else 0 for change in changes]
            
            # Calculate average gain and loss
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            # Avoid division by zero
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Cache and return result
            self._cache_data(cache_key, rsi, self._indicator_cache_duration)
            return round(rsi, 2)
            
        except Exception as e:
            logger.error(f"❌ RSI calculation failed: {e}")
            return technical_constants.RSI_NEUTRAL

    def _categorize_5m_volatility_for_trading(self, volatility_5m: float) -> tuple:
        """Categorize 5m volatility for trading decisions (proper location for data analysis)"""
        try:
            # Categorize based on 5-minute trading relevance
            if volatility_5m > 0.015:      # > 1.5%
                category = "EXTREME"
                trend = "VOLATILE"
            elif volatility_5m > 0.008:    # > 0.8%  
                category = "HIGH"
                trend = "ACTIVE"
            elif volatility_5m > 0.004:    # > 0.4%
                category = "MODERATE" 
                trend = "NORMAL"
            elif volatility_5m > 0.002:    # > 0.2%
                category = "LOW"
                trend = "QUIET"
            else:                          # < 0.2%
                category = "VERY_LOW"
                trend = "BORING"
            
            return category, trend
            
        except Exception as e:
            logger.error(f"❌ 5m volatility categorization failed: {e}")
            return "ERROR", "ERROR"

    def get_yahoo_data_with_analysis(self, yahoo_fetcher, symbol: str = "BTC", hyperliquid_price: float = None) -> Dict[str, Any]:
        """
        Get Yahoo data with centralized analysis calculations
        This method consolidates Yahoo data fetching with MarketDataManager calculations
        Eliminates circular dependency by having MarketDataManager orchestrate the process
        """
        cache_key = f"yahoo_analysis_{symbol}_{int(time.time() / 300)}"  # 5-minute cache
        cached_result = self._get_cached_data(cache_key, self._cache_duration)
        
        if cached_result:
            return cached_result
            
        try:
            # Get raw candle data from Yahoo (no calculations)
            candles_1m = yahoo_fetcher.get_klines(f"{symbol}-USD", "1m", 120)  
            candles_5m = yahoo_fetcher.get_klines(f"{symbol}-USD", "5m", 60)
            candles_1h = yahoo_fetcher.get_klines(f"{symbol}-USD", "1h", 84)
            candles_1d = yahoo_fetcher.get_klines(f"{symbol}-USD", "1d", 45)
            
            if not candles_5m:
                return {"error": "No Yahoo candle data available"}
                
            # Do all calculations centrally here instead of in YahooDataFetcher
            current_price = hyperliquid_price or candles_5m[-1]["close"]
            
            # Calculate indicators using centralized methods
            support_resistance_5m = self.calculate_support_resistance(candles_5m)
            support_resistance_1h = self.calculate_support_resistance(candles_1h) if candles_1h else {"support": 0, "resistance": 0}
            support_resistance_1d = self.calculate_support_resistance(candles_1d) if candles_1d else {"support": 0, "resistance": 0}
            
            volatility_5m = self.calculate_volatility(candles_5m)
            volatility_1h = self.calculate_volatility(candles_1h) if candles_1h else 0.0
            volatility_1d = self.calculate_volatility(candles_1d) if candles_1d else 0.0
            
            # Add 5-minute trading categorization (proper location for data analysis)
            volatility_5m_category, volatility_5m_trend = self._categorize_5m_volatility_for_trading(volatility_5m)
            
            # Get trend analysis using centralized trend manager
            trend_5m = self.calculate_trend(candles_5m) if candles_5m else {"trend": "NEUTRAL"}
            trend_1h = self.calculate_trend(candles_1h) if candles_1h else {"trend": "NEUTRAL"}
            
            # Calculate RSI using centralized method
            rsi_5m = self.calculate_rsi_from_candles(candles_5m)
            
            # Build consolidated analysis
            analysis = {
                "timestamp": time.time(),
                "symbol": symbol,
                "current_price": current_price,
                "yahoo_last_close": candles_5m[-1]["close"],
                
                # Raw candle data
                "candles_1m": candles_1m or [],
                "candles_5m": candles_5m or [],
                "candles_1h": candles_1h or [],
                "candles_1d": candles_1d or [],
                
                # Calculated indicators (centralized)
                "support_resistance_5m": support_resistance_5m,
                "support_resistance_1h": support_resistance_1h,
                "support_resistance_1d": support_resistance_1d,
                "volatility_5m": volatility_5m,
                "volatility_5m_category": volatility_5m_category,
                "volatility_5m_trend": volatility_5m_trend,
                "volatility_1h": volatility_1h,
                "volatility_1d": volatility_1d,
                "trend_5m": trend_5m,
                "trend_1h": trend_1h,
                "rsi_5m": rsi_5m,
                
                "data_source": "centralized_market_data_manager"
            }
            
            # Cache result and return
            self._cache_data(cache_key, analysis, self._cache_duration)
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo data with analysis: {e}")
            return {"error": str(e)}

    def clear_cache(self, cache_type: str = "all"):
        """Clear cache to force fresh data (useful when constants change)"""
        if cache_type in ["all", "market_data"]:
            self._market_data_cache.clear()
            self._cache_timestamps.clear()
            logger.info("🧹 MarketDataManager cache cleared - will get fresh data")
        
        if cache_type in ["all", "indicators"]:
            self._indicator_cache.clear()
            self._indicator_timestamps.clear()
            logger.info("🧹 MarketDataManager indicator cache cleared")

    def get_cache_status(self) -> Dict[str, Any]:
        """Get simplified cache status for monitoring"""
        return {
            "market_data_entries": len(self._market_data_cache),
            "indicator_entries": len(self._indicator_cache),
            "total_entries": len(self._market_data_cache) + len(self._indicator_cache),
            "cache_age_range": f"{min(time.time() - t for t in self._cache_timestamps.values()):.1f}-{max(time.time() - t for t in self._cache_timestamps.values()):.1f}s" if self._cache_timestamps else "empty"
        }

# Global instance
market_data_manager = MarketDataManager()
