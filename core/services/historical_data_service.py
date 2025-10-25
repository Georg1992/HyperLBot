#!/usr/bin/env python3
"""
Historical Data Service
Centralized historical candle data fetching and management
Single Responsibility: Historical data source for all components
"""

import time
import datetime as dt
from typing import Dict, Any, List, Optional
from loguru import logger


class HistoricalDataService:
    """Centralized service for all historical candle data"""
    
    def __init__(self):
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        logger.info("📊 Historical Data Service initialized - Single source for all candle data")
    
    def get_historical_candles(self, symbol: str, timeframe: str, count: int) -> List[Dict]:
        """
        Get historical candles - single source of truth for all candle data
        Calls HyperliquidAPI directly (no MarketDataService dependency)
        
        Args:
            symbol: Trading symbol (e.g., "BTC")
            timeframe: Candle timeframe (e.g., "5m", "1h", "1d")
            count: Number of candles to fetch
            
        Returns:
            List of historical candles
        """
        try:
            # Check cache first using centralized system
            cache_key = f"historical_candles_{symbol}_{timeframe}_{count}"
            cached_data = self._cache.get(cache_key)
            if cached_data:
                logger.debug(f"📊 Using cached {timeframe} candles for {symbol}")
                return cached_data
            
            logger.debug(f"📊 Fetching {count} {timeframe} candles for {symbol} from HyperliquidAPI")
            
            # Call HyperliquidAPI directly - single source of truth
            from core.api.hyperliquid_api import get_hyperliquid_api
            hyperliquid_api = get_hyperliquid_api()
            candles = hyperliquid_api.get_historical_candles(symbol, timeframe, count)
            
            if not candles:
                logger.warning(f"⚠️ No {timeframe} candles available for {symbol}")
                return []
            
            # Cache the result using centralized system
            self._cache.set(cache_key, candles, ttl=60)  # 1 minute cache
            
            logger.debug(f"📊 Retrieved {len(candles)} {timeframe} candles for {symbol}")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch {timeframe} candles for {symbol}: {e}")
            return []
    
    def get_1m_candles(self, symbol: str, count: int) -> List[Dict]:
        """Get 1-minute candles"""
        return self.get_historical_candles(symbol, "1m", count)
    
    def get_5m_candles(self, symbol: str, count: int) -> List[Dict]:
        """Get 5-minute candles"""
        return self.get_historical_candles(symbol, "5m", count)
    
    def get_1h_candles(self, symbol: str, count: int) -> List[Dict]:
        """Get 1-hour candles"""
        return self.get_historical_candles(symbol, "1h", count)
    
    def get_1d_candles(self, symbol: str, count: int) -> List[Dict]:
        """Get 1-day candles"""
        return self.get_historical_candles(symbol, "1d", count)
    
    def invalidate_cache(self, symbol: str, timeframe: str):
        """Invalidate cache for specific symbol and timeframe"""
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"🗑️ Invalidated cache for {symbol} {timeframe}")
    
    def prepare_chart_data(self, current_price: float, pattern_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Prepare complete chart data structure for dashboard
        
        Args:
            current_price: Current market price
            pattern_analysis: Pattern analysis data to include
            
        Returns:
            Dict with chart data structure
        """
        try:
            # Get the current 5m candle start time (UTC synchronized)
            candle_start_timestamp = self._get_5m_candle_start_time()
            
            # HistoricalDataService fetches its own candles (single responsibility)
            chart_candles_5m = self.get_5m_candles("BTC", 20)
            
            # NO FALLBACKS - Must have candles
            if not chart_candles_5m or len(chart_candles_5m) == 0:
                logger.error("❌ NO CANDLES AVAILABLE - NO FALLBACKS")
                return {}
            
            # Get real-time volume from the last candle if available
            real_time_volume = 0.0
            if chart_candles_5m and len(chart_candles_5m) > 0:
                real_time_volume = chart_candles_5m[-1].get("volume", 0.0)
            
            # NO FALLBACKS - Use exactly the candles provided
            # Remove the last candle if it's the current ongoing one (same timestamp as our ongoing candle)
            if len(chart_candles_5m) > 0:
                last_candle_timestamp = chart_candles_5m[-1]["timestamp"]
                if abs(last_candle_timestamp - candle_start_timestamp) < 300:  # Within 5 minutes
                    chart_candles_5m = chart_candles_5m[:-1]  # Remove the ongoing candle from historical data
            
            logger.debug(f"📊 Chart data prepared using fetched candles: {len(chart_candles_5m)} historical")
            
            # Create ongoing candle using utility method
            ongoing_candle = self._create_ongoing_candle(
                current_price, chart_candles_5m, real_time_volume, candle_start_timestamp
            )
            
            # Create exactly 20 candles: 19 historical + 1 ongoing
            chart_candles_with_ongoing = chart_candles_5m.copy()
            chart_candles_with_ongoing.append(ongoing_candle)
            
            # Prepare chart data structure
            return {
                "historical": chart_candles_with_ongoing,  # Include ongoing candle in historical array
                "ongoing": ongoing_candle,  # Keep separate for reference
                "predicted": [],
                "pattern_analysis": pattern_analysis or {}
            }
            
        except Exception as e:
            logger.error(f"❌ Chart data preparation failed: {e}")
            return {}
    
    def _get_5m_candle_start_time(self) -> float:
        """
        Get the current 5-minute candle start time (UTC synchronized)
        
        Returns:
            Timestamp of current 5m candle start
        """
        from core.utils.time_utils import get_5m_candle_start_time
        return get_5m_candle_start_time()
    
    def _create_ongoing_candle(self, current_price: float, chart_candles_5m: List[Dict], 
                              real_time_volume: float, candle_start_timestamp: float) -> Dict[str, Any]:
        """
        Create ongoing candle structure with proper price movement
        
        Args:
            current_price: Current market price
            chart_candles_5m: Historical 5m candles for reference
            real_time_volume: Current 5m candle volume
            candle_start_timestamp: Timestamp of candle start
            
        Returns:
            Dict with ongoing candle data
        """
        current_time = time.time()
        
        # Get the open price from the last completed candle
        if chart_candles_5m and len(chart_candles_5m) > 0:
            open_price = chart_candles_5m[-1]["close"]  # Open of current candle = close of previous
        else:
            # Fallback: use current price as open (should not happen with proper data)
            open_price = current_price
        
        # Calculate proper high and low based on price movement
        high_price = max(open_price, current_price)
        low_price = min(open_price, current_price)
        
        # Ensure we have a proper candle structure
        if high_price == low_price:
            # If no price movement, create a small range to show the candle
            price_range = current_price * 0.0001  # 0.01% range
            high_price = current_price + price_range
            low_price = current_price - price_range
        
        return {
            "open": open_price,      # Price at start of 5m period
            "close": current_price,  # Current price as close
            "high": high_price,      # Highest price in current period
            "low": low_price,        # Lowest price in current period
            "volume": real_time_volume if real_time_volume > 0 else (chart_candles_5m[-1]["volume"] if chart_candles_5m else 0),
            "timestamp": candle_start_timestamp,
            "is_ongoing": True,
            "trades_count": 0,
            "last_trade_time": current_time
        }


# Singleton pattern implementation
_global_historical_data_service = None

def get_global_historical_data_service() -> HistoricalDataService:
    """Get the global HistoricalDataService singleton instance"""
    global _global_historical_data_service
    if _global_historical_data_service is None:
        _global_historical_data_service = HistoricalDataService()
    return _global_historical_data_service

# Backward compatibility
def get_global_chart_data_service() -> HistoricalDataService:
    """Backward compatibility - returns HistoricalDataService"""
    return get_global_historical_data_service()
