#!/usr/bin/env python3
"""
Yahoo Finance Data Fetcher for Historical BTC/USD Data
Provides real historical candlestick data that aligns with Hyperliquid BTC/USD perpetuals
NOTE: This fetcher is for HISTORICAL DATA ONLY. Real-time pricing should come from Hyperliquid.
"""

import time
import json
import yfinance as yf
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import statistics
from core.constants import data_constants, volume_constants, technical_constants, time_constants
from core.external.yahoo_volume_analyzer import volume_analyzer
from core.external.yahoo_momentum_analyzer import momentum_analyzer

class YahooDataFetcher:
    """
    Yahoo Finance data fetcher for BTC/USD historical data
    Provides real historical candlestick data aligned with Hyperliquid BTC/USD perpetuals
    NOTE: For real-time pricing, use Hyperliquid API exclusively
    """
    
    def __init__(self):
        self.symbol = "BTC-USD"
        self.cache = {}
        self.cache_duration = data_constants.YAHOO_CACHE_DURATION
        
        # Optimized data manager - periodic update tracking
        self.last_yahoo_update = 0
        self.last_1h_update = 0
        self.last_daily_update = 0
        
        # Update intervals (in seconds)
        self.yahoo_update_interval = data_constants.YAHOO_UPDATE_INTERVAL
        self.hourly_update_interval = data_constants.HOURLY_UPDATE_INTERVAL
        self.daily_update_interval = data_constants.DAILY_UPDATE_INTERVAL
        
        # Stored analysis data
        self.cached_yahoo_analysis = {}
        self.cached_1h_data = {}
        self.cached_daily_data = {}
        
        logger.info("🔗 Yahoo Finance Data Fetcher initialized for BTC-USD (HISTORICAL DATA ONLY)")
        logger.info("📊 Real-time pricing should come from Hyperliquid API")
        logger.info("⚡ Optimized data manager: Periodic updates enabled")
    
    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """Get cached data if still valid"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_duration:
                return data
        return None
    
    def _cache_data(self, key: str, data: Dict):
        """Cache data with timestamp"""
        self.cache[key] = (data, time.time())
    
    def _should_update_data(self, last_update: float, interval: int) -> bool:
        """Check if data should be updated based on interval"""
        return time.time() - last_update > interval
    
    def get_optimized_market_analysis(self, symbol: str = "BTC", hyperliquid_price: float = None) -> Dict[str, Any]:
        """
        Get optimized market analysis with periodic updates
        Only fetches new data when intervals are exceeded
        """
        current_time = time.time()
        
        # Check if we need a full Yahoo analysis update
        if self._should_update_data(self.last_yahoo_update, self.yahoo_update_interval):
            logger.info("📊 Updating Yahoo Finance market analysis (periodic update)")
            self.cached_yahoo_analysis = self.get_market_analysis(symbol, hyperliquid_price)
            self.last_yahoo_update = current_time
        
        return self.cached_yahoo_analysis
    
    def get_optimized_1h_data(self, symbol: str = "BTC") -> Dict[str, Any]:
        """
        Get optimized 1-hour data with 15-minute update interval
        """
        current_time = time.time()
        
        if self._should_update_data(self.last_1h_update, self.hourly_update_interval):
            logger.info("📊 Updating 1-hour data (15-minute interval)")
            candles_1h = self.get_1h_klines(symbol, 84)
            if candles_1h:
                from core.market_data_manager import market_data_manager
                self.cached_1h_data = {
                    "candles": candles_1h,
                    "trend": market_data_manager.calculate_trend(candles_1h),
                    "support_resistance": market_data_manager.calculate_support_resistance(candles_1h),
                    "volatility": market_data_manager.calculate_volatility(candles_1h)
                }
            else:
                self.cached_1h_data = {}
            self.last_1h_update = current_time
        
        return self.cached_1h_data
    
    def get_optimized_daily_data(self, symbol: str = "BTC") -> Dict[str, Any]:
        """
        Get optimized daily data with 1-hour update interval
        """
        current_time = time.time()
        
        if self._should_update_data(self.last_daily_update, self.daily_update_interval):
            logger.info("📊 Updating daily data (1-hour interval)")
            candles_1d = self.get_klines(symbol, "1d", 45)
            if candles_1d:
                from core.market_data_manager import market_data_manager
                self.cached_daily_data = {
                    "candles": candles_1d,
                    "trend": market_data_manager.calculate_trend(candles_1d),
                    "support_resistance": market_data_manager.calculate_support_resistance(candles_1d),
                    "volatility": market_data_manager.calculate_volatility(candles_1d)
                }
            else:
                self.cached_daily_data = {}
            self.last_daily_update = current_time
        
        return self.cached_daily_data
    
    def get_update_status(self) -> Dict[str, Any]:
        """Get status of all data updates"""
        current_time = time.time()
        return {
            "yahoo_analysis": {
                "last_update": self.last_yahoo_update,
                "next_update": self.last_yahoo_update + self.yahoo_update_interval,
                "time_until_update": max(0, (self.last_yahoo_update + self.yahoo_update_interval) - current_time)
            },
            "hourly_data": {
                "last_update": self.last_1h_update,
                "next_update": self.last_1h_update + self.hourly_update_interval,
                "time_until_update": max(0, (self.last_1h_update + self.hourly_update_interval) - current_time)
            },
            "daily_data": {
                "last_update": self.last_daily_update,
                "next_update": self.last_daily_update + self.daily_update_interval,
                "time_until_update": max(0, (self.last_daily_update + self.daily_update_interval) - current_time)
            }
        }
    
    def _convert_yf_to_standard(self, yf_data) -> List[Dict[str, Any]]:
        """Convert yfinance DataFrame to standard candlestick format"""
        if yf_data is None or yf_data.empty:
            return []
        
        candles = []
        for index, row in yf_data.iterrows():
            candle = {
                "open_time": int(index.timestamp() * data_constants.MILLISECONDS_IN_SECOND),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
                "close_time": int(index.timestamp() * data_constants.MILLISECONDS_IN_SECOND) + data_constants.CANDLE_CLOSE_OFFSET
            }
            candles.append(candle)
        
        return candles
    
    def get_klines(self, symbol: str = "BTC", interval: str = "5m", limit: int = 100) -> List[Dict[str, Any]]:
        """Get candlestick data from Yahoo Finance"""
        try:
            cache_key = f"klines_{symbol}_{interval}_{limit}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Convert interval to Yahoo Finance format
            interval_map = {
                "1m": "1m",
                "5m": "5m", 
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d"
            }
            
            yf_interval = interval_map.get(interval, "5m")
            
            # Calculate period based on interval and limit
            # Use more generous periods that were working before
            if interval == "1m":
                period = "7d"  # 7 days for 1m data
            elif interval == "5m":
                period = "60d"  # 60 days for 5m data
            elif interval == "15m":
                period = "90d"  # 90 days for 15m data
            elif interval == "30m":
                period = "180d"  # 180 days for 30m data
            elif interval == "1h":
                period = "1y"  # 1 year for 1h data
            elif interval == "4h":
                period = "2y"  # 2 years for 4h data
            elif interval == "1d":
                period = "5y"  # 5 years for 1d data
            else:
                period = "60d"  # Default to 60 days
            
            # Get data from Yahoo Finance
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period=period, interval=yf_interval)
            
            if data.empty:
                logger.warning(f"⚠️ No data received from Yahoo Finance for {symbol} {interval}")
                return []
            
            # Convert to standard format
            candles = self._convert_yf_to_standard(data)
            
            # Limit to requested number of candles (most recent)
            if len(candles) > limit:
                candles = candles[-limit:]
            
            # Cache the result
            self._cache_data(cache_key, candles)
            
            logger.info(f"✅ Retrieved {len(candles)} {interval} candles from Yahoo Finance")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to get {interval} klines from Yahoo Finance: {e}")
            return []
    
    def get_5m_klines(self, symbol: str = "BTC", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 5-minute candlestick data from Yahoo Finance"""
        return self.get_klines(symbol, "5m", limit)
    
    def get_1m_klines(self, symbol: str = "BTC", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 1-minute candlestick data from Yahoo Finance"""
        return self.get_klines(symbol, "1m", limit)
    
    def get_1h_klines(self, symbol: str = "BTC", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 1-hour candlestick data from Yahoo Finance"""
        return self.get_klines(symbol, "1h", limit)
    
    # REMOVED: get_current_price method - Real-time pricing should come from Hyperliquid
    
    def get_ticker_data(self, symbol: str = "BTC") -> Optional[Dict[str, Any]]:
        """Get ticker-like data from Yahoo Finance (historical context only)"""
        try:
            cache_key = f"ticker_{symbol}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            
            # Use previous close as reference (not current price)
            previous_close = info.get('previousClose', 0)
            
            ticker_data = {
                "symbol": symbol,
                "priceChange": 0,  # No real-time price change
                "priceChangePercent": 0,  # No real-time price change
                "lastPrice": previous_close,  # Use previous close for historical context
                "volume": info.get('regularMarketVolume', 0),
                "quoteVolume": info.get('regularMarketVolume', 0) * previous_close,
                "count": 0  # Not provided by Yahoo Finance
            }
            
            self._cache_data(cache_key, ticker_data)
            return ticker_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get ticker data from Yahoo Finance: {e}")
            return None
    
    def _analyze_consecutive_candles(self, recent_candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze recent consecutive candle patterns to detect immediate trend changes
        Returns trend override if 3+ consecutive candles show clear direction
        """
        if len(recent_candles) < 3:
            return None
        
        # Check candle colors (red vs green)
        candle_colors = []
        for candle in recent_candles:
            if candle["close"] > candle["open"]:
                candle_colors.append("green")
            elif candle["close"] < candle["open"]:
                candle_colors.append("red")
            else:
                candle_colors.append("neutral")  # Doji
        
        # Count consecutive patterns
        consecutive_green = 0
        consecutive_red = 0
        
        # Count from the end (most recent)
        for color in reversed(candle_colors):
            if color == "green":
                consecutive_green += 1
                if consecutive_red > 0:
                    break
            elif color == "red":
                consecutive_red += 1
                if consecutive_green > 0:
                    break
            else:
                break  # Neutral candle breaks the pattern
        
        # Calculate price change over the consecutive pattern
        if consecutive_green >= 3:
            # 3+ consecutive green candles = immediate uptrend
            pattern_start = len(recent_candles) - consecutive_green
            price_change = (recent_candles[-1]["close"] - recent_candles[pattern_start]["open"]) / recent_candles[pattern_start]["open"]
            
            if price_change > technical_constants.TREND_STRENGTH_HIGH:  # 1% gain over consecutive greens
                return {
                    "trend": "UP",
                    "strength": min(abs(price_change), technical_constants.VOLATILITY_MAX_CAP),
                    "direction": 1,
                    "raw_change": price_change,
                    "pattern_type": f"consecutive_green_{consecutive_green}",
                    "pattern_override": True
                }
            elif price_change > technical_constants.PRICE_CHANGE_MINOR:  # 0.05% gain - weak up
                return {
                    "trend": "WEAK_UP",
                    "strength": min(abs(price_change) * 2, technical_constants.VOLATILITY_MAX_CAP),
                    "direction": 1,
                    "raw_change": price_change,
                    "pattern_type": f"consecutive_green_{consecutive_green}_weak",
                    "pattern_override": True
                }
            else:
                # Price barely moved despite consecutive greens = sideways
                return {
                    "trend": "SIDEWAYS",
                    "strength": technical_constants.TREND_STRENGTH_LOW,
                    "direction": 0,
                    "raw_change": price_change,
                    "pattern_type": f"consecutive_green_{consecutive_green}_sideways",
                    "pattern_override": True
                }
        
        elif consecutive_red >= 3:
            # 3+ consecutive red candles = immediate downtrend
            pattern_start = len(recent_candles) - consecutive_red
            price_change = (recent_candles[-1]["close"] - recent_candles[pattern_start]["open"]) / recent_candles[pattern_start]["open"]
            
            if price_change < -technical_constants.TREND_STRENGTH_HIGH:  # 1% loss over consecutive reds
                return {
                    "trend": "DOWN", 
                    "strength": min(abs(price_change), technical_constants.VOLATILITY_MAX_CAP),
                    "direction": -1,
                    "raw_change": price_change,
                    "pattern_type": f"consecutive_red_{consecutive_red}",
                    "pattern_override": True
                }
            elif price_change < -technical_constants.PRICE_CHANGE_MINOR:  # 0.05% loss - weak down
                return {
                    "trend": "WEAK_DOWN",
                    "strength": min(abs(price_change) * 2, technical_constants.VOLATILITY_MAX_CAP),
                    "direction": -1,
                    "raw_change": price_change,
                    "pattern_type": f"consecutive_red_{consecutive_red}_weak", 
                    "pattern_override": True
                }
            else:
                # Price barely moved despite consecutive reds = sideways
                return {
                    "trend": "SIDEWAYS",
                    "strength": technical_constants.TREND_STRENGTH_LOW,
                    "direction": 0,
                    "raw_change": price_change,
                    "pattern_type": f"consecutive_red_{consecutive_red}_sideways",
                    "pattern_override": True
                }
        
        # No significant consecutive pattern found
        return None
    
    def get_market_analysis(self, symbol: str = "BTC", hyperliquid_price: float = None) -> Dict[str, Any]:
        """
        Get comprehensive market analysis from Yahoo Finance (HISTORICAL DATA ONLY)
        NOTE: hyperliquid_price parameter should be provided for current price context
        """
        try:
            # Get different timeframe data - COMPLETE optimal multi-timeframe configuration
            candles_1m = self.get_1m_klines(symbol, 120)  # 2 hours of 1m data for immediate momentum
            candles_5m = self.get_5m_klines(symbol, 60)   # 5 hours of 5m data (core prediction analysis)
            candles_1h = self.get_1h_klines(symbol, 84)   # 3.5 days of 1h data (daily trend context)
            candles_1d = self.get_klines(symbol, "1d", 45) # 6 weeks of 1d data (weekly/monthly trend context)
            ticker = self.get_ticker_data(symbol)
            
            if not candles_5m or not candles_1h or not candles_1d:
                return {"error": "Could not fetch candlestick data from Yahoo Finance"}
            
            # Get Yahoo Finance historical close price for comparison
            yahoo_last_close = candles_5m[-1]["close"] if candles_5m else 0
            
            # Use Hyperliquid price if provided, otherwise use last close from historical data
            if hyperliquid_price is not None:
                current_price = hyperliquid_price
                logger.info(f"📊 Using Hyperliquid price: ${current_price:,.2f}")
                
                # Calculate price difference between Hyperliquid and Yahoo Finance
                price_difference = abs(hyperliquid_price - yahoo_last_close)
                price_difference_pct = (price_difference / yahoo_last_close * 100) if yahoo_last_close > 0 else 0
                
                logger.info(f"📊 Yahoo last close: ${yahoo_last_close:,.2f}")
                logger.info(f"📊 Price difference: ${price_difference:,.2f} ({price_difference_pct:.3f}%)")
            else:
                # Fallback to last close price from historical data
                current_price = yahoo_last_close
                price_difference = 0
                price_difference_pct = 0
                logger.warning(f"⚠️ No Hyperliquid price provided, using last close: ${current_price:,.2f}")
            
            # Calculate indicators using centralized market data manager
            from core.market_data_manager import market_data_manager
            support_resistance_5m = market_data_manager.calculate_support_resistance(candles_5m)
            support_resistance_1h = market_data_manager.calculate_support_resistance(candles_1h)
            
            # Multi-timeframe trend analysis using advanced trend manager
            from core.analysis.trend_manager import trend_manager
            multi_trend_analysis = trend_manager.get_multi_timeframe_trend(
                candles_1m, candles_5m, candles_1h
            )
            trend_5m = multi_trend_analysis["timeframes"]["5m"]
            trend_1h = multi_trend_analysis["timeframes"]["1h"]
            trend_1d = multi_trend_analysis["timeframes"]["1h"]  # Use 1h for daily context
            
            # Multi-timeframe volatility analysis
            volatility_5m = market_data_manager.calculate_volatility(candles_5m)
            volatility_1h = market_data_manager.calculate_volatility(candles_1h)
            volatility_1d = market_data_manager.calculate_volatility(candles_1d)
            
            # Daily support/resistance for major levels
            support_resistance_1d = market_data_manager.calculate_support_resistance(candles_1d)
            
            analysis = {
                "timestamp": time.time(),
                "symbol": symbol,
                "current_price": current_price,  # Hyperliquid price for trading
                "yahoo_last_close": yahoo_last_close,  # Yahoo Finance historical close
                "price_difference": price_difference,  # Absolute difference
                "price_difference_pct": price_difference_pct,  # Percentage difference
                "candles_1m": candles_1m,  # Full 120 1-min candles (2 hours)
                "candles_5m": candles_5m,  # Full 60 5-min candles (5 hours)
                "candles_1h": candles_1h,  # Full 84 1-hour candles (3.5 days)
                "candles_1d": candles_1d,  # Full 45 daily candles (6 weeks)
                "support_resistance_5m": support_resistance_5m,
                "support_resistance_1h": support_resistance_1h,
                "support_resistance_1d": support_resistance_1d,  # Major weekly/monthly levels
                "trend_5m": trend_5m,     # Short-term trend (5h)
                "trend_1h": trend_1h,     # Daily trend (3.5d)
                "trend_1d": trend_1d,     # Weekly/monthly trend (6w)
                "multi_trend_analysis": multi_trend_analysis,  # Advanced trend analysis
                "volatility_5m": volatility_5m,
                "volatility_1h": volatility_1h,
                "volatility_1d": volatility_1d,
                "ticker": ticker,
                "market_condition": self._determine_market_condition(trend_5m, trend_1h, volatility_5m),
                "data_source": "Yahoo Finance (Historical) + Hyperliquid (Real-time Price)"
            }
            
            logger.success(f"✅ Yahoo Finance market analysis completed for {symbol}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in Yahoo Finance market analysis: {e}")
            return {"error": str(e)}
    
    def _determine_market_condition(self, trend_5m: Dict, trend_1h: Dict, volatility: float) -> str:
        """Determine overall market condition with crypto-appropriate thresholds"""
        # Volatility thresholds for crypto markets
        if volatility > 0.008:  # 0.8% volatility (reduced from 2.0%)
            return "HIGH_VOLATILITY"
        elif volatility > 0.006:  # 0.6% volatility  
            return "ELEVATED_VOLATILITY"
        
        # Strong trends
        if trend_5m["strength"] > technical_constants.TREND_STRENGTH_HIGH and trend_1h["strength"] > technical_constants.TREND_STRENGTH_MEDIUM:
            if trend_5m["trend"] == trend_1h["trend"]:
                return "STRONG_TREND"
            else:
                return "MIXED_SIGNALS"
        
        # Medium volatility (was missing this range)
        if volatility > 0.003:  # 0.3% volatility
            return "MEDIUM_VOLATILITY"
        
        # Low volatility  
        if volatility < 0.002:  # 0.2% volatility (reduced from 0.5%)
            return "LOW_VOLATILITY"
        
        return "NORMAL"
    
    def test_connection(self) -> bool:
        """Test connection to Yahoo Finance (historical data only)"""
        try:
            # Test with historical data instead of current price
            candles = self.get_5m_klines("BTC", 10)
            if candles and len(candles) > 0:
                logger.success("✅ Yahoo Finance connection successful (historical data)")
                return True
            else:
                logger.error("❌ Yahoo Finance connection failed - no historical data")
                return False
        except Exception as e:
            logger.error(f"❌ Yahoo Finance connection error: {e}")
            return False


            
            # Extract volume data from candles
            volumes = [candle.get("volume", 0) for candle in candles_5m]
            
            # Use most recent completed candle (not the current incomplete one)
            if len(volumes) >= 2 and volumes[-1] == 0:
                current_volume = volumes[-2]  # Use previous completed candle
                logger.info("Using previous completed candle for volume (current candle incomplete)")
            else:
                current_volume = volumes[-1] if volumes else 0
            
            # Calculate average volume from recent candles
            recent_volumes = volumes[-5:]  # Last 5 candles
            avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
            
            # Use actual Yahoo volume (no scaling to match Hyperliquid)
            current_volume = current_volume
            avg_volume = avg_volume
            
            # Categorize volume based on actual Yahoo Finance ranges (more realistic for BTC)
            if current_volume >= volume_constants.VOLUME_ULTRA_HIGH:  # 500K+
                volume_category = "EXTREMELY_HIGH"
            elif current_volume >= 200000:  # 200K+
                volume_category = "VERY_HIGH"
            elif current_volume >= volume_constants.VOLUME_HIGH:  # 100K+
                volume_category = "HIGH"
            elif current_volume >= volume_constants.VOLUME_MEDIUM:  # 50K+
                volume_category = "ABOVE_AVERAGE"
            elif current_volume >= 20000:  # 20K+
                volume_category = "NORMAL"
            elif current_volume >= volume_constants.VOLUME_LOW:  # 10K+
                volume_category = "BELOW_AVERAGE"
            elif current_volume >= 5000:  # 5K+
                volume_category = "LOW"
            elif current_volume >= 2000:  # 2K+
                volume_category = "VERY_LOW"
            else:
                volume_category = "EXTREMELY_LOW"
            
            # Determine volume trend
            if len(volumes) >= 3:
                recent_avg = sum(volumes[-3:]) / 3
                older_avg = sum(volumes[-6:-3]) / 3 if len(volumes) >= 6 else recent_avg
                
                if recent_avg > older_avg * 1.1:
                    volume_trend = "INCREASING"
                elif recent_avg < older_avg * 0.9:
                    volume_trend = "DECREASING"
                else:
                    volume_trend = "STABLE"
            else:
                volume_trend = "UNKNOWN"
            
            return {
                "current_volume": current_volume,
                "volume_category": volume_category,
                "avg_volume": avg_volume,
                "volume_trend": volume_trend,
                "recent_volumes": recent_volumes,
                "data_source": "yahoo_finance",
                # Add basic spike detection fields for dashboard compatibility
                "has_spike": False,
                "spike_severity": "NORMAL",
                "is_immediate_spike": False,
                "spike_reason": "",
                "volume_source": "yahoo_finance_basic"
            }
            
        except Exception as e:
            logger.error(f"Failed to get current 5m volume: {e}")
            return {
                "current_volume": 0,
                "volume_category": "ERROR",
                "avg_volume": 0,
                "volume_trend": "ERROR",
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    
    def get_market_summary(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get market summary including day high/low, averages, and trends"""
        try:
            cache_key = f"summary_{symbol}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Get daily data for summary
            daily_candles = self.get_klines(symbol, "1d", data_constants.DAILY_CANDLES_COUNT)
            if not daily_candles:
                return {
                    "error": "No daily data available",
                    "data_source": "yahoo_finance"
                }
            
            # Get 5m data for intraday analysis
            intraday_candles = self.get_klines(symbol, "5m", data_constants.INTRADAY_CANDLES_COUNT)
            
            # Calculate daily statistics
            today_candle = daily_candles[-1] if daily_candles else None
            yesterday_candle = daily_candles[-2] if len(daily_candles) > 1 else None
            
            # Calculate moving averages
            closes = [c["close"] for c in daily_candles]
            ma_20 = sum(closes[-20:]) / min(20, len(closes)) if closes else 0
            ma_50 = sum(closes[-50:]) / min(50, len(closes)) if closes else 0
            
            # Calculate intraday range
            if intraday_candles:
                intraday_high = max(c["high"] for c in intraday_candles)
                intraday_low = min(c["low"] for c in intraday_candles)
                intraday_range = intraday_high - intraday_low
                intraday_range_pct = (intraday_range / intraday_low) * 100 if intraday_low > 0 else 0
            else:
                intraday_high = intraday_low = intraday_range = intraday_range_pct = 0
            
            summary = {
                "current_price": today_candle["close"] if today_candle else 0,
                "day_open": today_candle["open"] if today_candle else 0,
                "day_high": today_candle["high"] if today_candle else 0,
                "day_low": today_candle["low"] if today_candle else 0,
                "previous_close": yesterday_candle["close"] if yesterday_candle else 0,
                "day_change": (today_candle["close"] - yesterday_candle["close"]) if today_candle and yesterday_candle else 0,
                "day_change_pct": ((today_candle["close"] - yesterday_candle["close"]) / yesterday_candle["close"] * 100) if today_candle and yesterday_candle and yesterday_candle["close"] > 0 else 0,
                "ma_20": ma_20,
                "ma_50": ma_50,
                "intraday_high": intraday_high,
                "intraday_low": intraday_low,
                "intraday_range": intraday_range,
                "intraday_range_pct": intraday_range_pct,
                "data_source": "yahoo_finance",
                "update_frequency": "5_seconds"
            }
            
            # Cache the summary
            self._cache_data(cache_key, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get market summary: {e}")
            return {
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    
    def get_realtime_volume(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get real-time volume using the volume analyzer module"""
        try:
            cache_key = f"realtime_volume_{symbol}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Get 1-minute and 5-minute candles
            candles_1m = self.get_klines(symbol, "1m", 60)
            candles_5m = self.get_klines(symbol, "5m", 10)
            
            if not candles_1m or not candles_5m:
                return {
                    "error": "No candle data available",
                    "data_source": "yahoo_finance"
                }
            
            # Use volume analyzer for spike detection
            volume_data = volume_analyzer.detect_volume_spike(candles_1m, candles_5m)
            
            # Add additional metadata
            volume_data.update({
                "data_source": "yahoo_finance_1m_aggregation",
                "update_frequency": "5_seconds",
                "yahoo_5m_volume": candles_5m[-1]["volume"] if candles_5m else 0
            })
            
            # Cache for 5 seconds
            self._cache_data(cache_key, volume_data)
            
            # Log immediate spike detection
            if volume_data.get("is_immediate_spike", False):
                logger.warning(f"🚨 IMMEDIATE VOLUME SPIKE DETECTED: {volume_data.get('spike_reason', '')}")
                logger.warning(f"   Current: {volume_data.get('estimated_current_volume', 0):.0f}")
            
            return volume_data
            
        except Exception as e:
            logger.error(f"Failed to get real-time volume: {e}")
            return {
                "error": str(e),
                "data_source": "yahoo_finance"
            }

    def get_realtime_momentum_analysis(self, symbol: str = "BTC", current_price: float = None) -> Dict[str, Any]:
        """
        Get real-time momentum analysis using the momentum analyzer module
        """
        try:
            # Get recent 5-minute candles for momentum calculation
            candles_5m = self.get_5m_klines(symbol, 10)  # Last 10 candles (50 minutes)
            if not candles_5m or len(candles_5m) < 3:
                return {"momentum": "NEUTRAL", "strength": 0, "direction": 0}
            
            # Use momentum analyzer for analysis
            momentum_data = momentum_analyzer.analyze_momentum(candles_5m, symbol)
            
            # Calculate RSI from Yahoo data
            yahoo_rsi = self.calculate_rsi_from_candles(candles_5m)
            
            result = {
                **momentum_data,
                "rsi": yahoo_rsi,
                "data_source": "yahoo_finance_momentum_analysis"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate real-time momentum: {e}")
            return {"momentum": "NEUTRAL", "strength": 0, "direction": 0, "error": str(e)}
    
    def calculate_rsi_from_candles(self, candles: List[Dict], periods: int = 14) -> float:
        """
        Calculate RSI from Yahoo Finance candles using Wilder's method
        
        Args:
            candles: List of candle data with 'close' prices
            periods: RSI calculation periods (default: 14)
            
        Returns:
            float: RSI value
        """
        try:
            if len(candles) < periods + 1:
                logger.warning(f"⚠️ Not enough candles for RSI calculation: {len(candles)} < {periods + 1}")
                return 50.0  # Neutral RSI
            
            # Extract close prices
            prices = [candle['close'] for candle in candles]
            
            # Calculate price changes
            changes = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                changes.append(change)
            
            # Calculate gains and losses
            gains = [c if c > 0 else 0.0 for c in changes]
            losses = [-c if c < 0 else 0.0 for c in changes]
            
            # Use Wilder's smoothing (same as incremental calculation)
            alpha = 1.0 / periods
            
            # Initialize with first period's simple average
            avg_gain = sum(gains[:periods]) / periods
            avg_loss = sum(losses[:periods]) / periods
            
            # Apply Wilder's smoothing to remaining periods
            for i in range(periods, len(gains)):
                avg_gain = (1 - alpha) * avg_gain + alpha * gains[i]
                avg_loss = (1 - alpha) * avg_loss + alpha * losses[i]
            
            # Calculate RSI
            if avg_loss == 0:
                return 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
                return round(rsi, 2)
                
        except Exception as e:
            logger.error(f"❌ Failed to calculate RSI from candles: {e}")
            return 50.0  # Neutral RSI


def main():
    """Test the Yahoo Finance data fetcher"""
    logger.info("🔍 Testing Yahoo Finance Data Fetcher (HISTORICAL DATA ONLY)")
    logger.info("=" * 60)
    
    fetcher = YahooDataFetcher()
    
    # Test connection
    if not fetcher.test_connection():
        logger.error("❌ Cannot connect to Yahoo Finance")
        return
    
    # Test market analysis with mock Hyperliquid price
    logger.info("📊 Getting market analysis...")
    mock_hyperliquid_price = 45000.0  # Mock price for testing
    analysis = fetcher.get_market_analysis("BTC", hyperliquid_price=mock_hyperliquid_price)
    
    if "error" not in analysis:
        logger.success("✅ Market analysis successful!")
        logger.info(f"Current Price (Hyperliquid): ${analysis['current_price']:,.2f}")
        logger.info(f"5m Trend: {analysis['trend_5m']['trend']} ({analysis['trend_5m']['strength']*100:.2f}%)")
        logger.info(f"1h Trend: {analysis['trend_1h']['trend']} ({analysis['trend_1h']['strength']*100:.2f}%)")
        logger.info(f"5m Support: ${analysis['support_resistance_5m']['support']:,.2f}")
        logger.info(f"5m Resistance: ${analysis['support_resistance_5m']['resistance']:,.2f}")
        logger.info(f"Market Condition: {analysis['market_condition']}")
        logger.info(f"Data Source: {analysis['data_source']}")
        logger.info(f"5m Candles: {len(analysis['candles_5m'])}")
        logger.info(f"1h Candles: {len(analysis['candles_1h'])}")
    else:
        logger.error(f"❌ Market analysis failed: {analysis['error']}")


if __name__ == "__main__":
    main()
