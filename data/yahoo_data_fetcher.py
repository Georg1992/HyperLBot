#!/usr/bin/env python3
"""
Yahoo Finance Data Fetcher for Historical BTC/USD Data
Provides real historical candlestick data that aligns with Hyperliquid BTC/USD perpetuals
"""

import time
import json
import yfinance as yf
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import sys
import os
import statistics

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class YahooDataFetcher:
    """
    Yahoo Finance data fetcher for BTC/USD historical data
    Provides real historical candlestick data aligned with Hyperliquid BTC/USD perpetuals
    """
    
    def __init__(self):
        self.symbol = "BTC-USD"
        self.cache = {}
        self.cache_duration = 30  # 30 seconds cache
        
        logger.info("🔗 Yahoo Finance Data Fetcher initialized for BTC-USD")
    
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
    
    def _convert_yf_to_standard(self, yf_data) -> List[Dict[str, Any]]:
        """Convert yfinance DataFrame to standard candlestick format"""
        try:
            candles = []
            
            for index, row in yf_data.iterrows():
                timestamp = int(index.timestamp() * 1000)  # Convert to milliseconds
                
                candle = {
                    "open_time": timestamp,
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": float(row['Volume']),
                    "close_time": timestamp + (5 * 60 * 1000),  # Add 5 minutes for 5m candles
                    "quote_volume": float(row['Volume']) * float(row['Close']),
                    "trades": 0,  # Not provided by Yahoo Finance
                    "taker_buy_base": float(row['Volume']) * 0.5,  # Estimate
                    "taker_buy_quote": float(row['Volume']) * float(row['Close']) * 0.5  # Estimate
                }
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to convert Yahoo Finance data: {e}")
            return []
    
    def get_klines(self, symbol: str = "BTC", interval: str = "5m", limit: int = 100) -> List[Dict[str, Any]]:
        """Get candlestick data from Yahoo Finance API"""
        try:
            cache_key = f"klines_{symbol}_{interval}_{limit}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            logger.info(f"📊 Fetching {limit} {interval} candles for {symbol} from Yahoo Finance...")
            
            # Map interval formats
            yf_interval = self._map_interval(interval)
            
            # Calculate period based on interval and limit
            period_days = self._calculate_period(interval, limit)
            
            # Fetch data from Yahoo Finance
            ticker = yf.Ticker(self.symbol)
            yf_data = ticker.history(period=f"{period_days}d", interval=yf_interval)
            
            if yf_data.empty:
                logger.error(f"❌ No data received from Yahoo Finance for {self.symbol}")
                return []
            
            # Convert to standard format
            candles = self._convert_yf_to_standard(yf_data)
            
            # Limit to requested number of candles
            if len(candles) > limit:
                candles = candles[-limit:]
            
            self._cache_data(cache_key, candles)
            logger.success(f"✅ Retrieved {len(candles)} real BTC/USD candles from Yahoo Finance")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo Finance data: {e}")
            return []
    
    def _map_interval(self, interval: str) -> str:
        """Map our interval format to Yahoo Finance format"""
        interval_map = {
            "1m": "1m",
            "5m": "5m", 
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d"
        }
        return interval_map.get(interval, "5m")
    
    def _calculate_period(self, interval: str, limit: int) -> int:
        """Calculate how many days of data we need"""
        interval_minutes = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440
        }
        
        minutes_needed = interval_minutes.get(interval, 5) * limit
        days_needed = max(1, int(minutes_needed / 1440) + 1)
        
        # Yahoo Finance limitations
        if days_needed > 60:
            days_needed = 60
            
        return days_needed
    
    def get_1h_klines(self, symbol: str = "BTC", limit: int = 24) -> List[Dict[str, Any]]:
        """Get 1-hour candlestick data from Yahoo Finance"""
        return self.get_klines(symbol, "1h", limit)
    
    def get_5m_klines(self, symbol: str = "BTC", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 5-minute candlestick data from Yahoo Finance"""
        return self.get_klines(symbol, "5m", limit)
    
    def get_1m_klines(self, symbol: str = "BTC", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 1-minute candlestick data from Yahoo Finance"""
        return self.get_klines(symbol, "1m", limit)
    
    def get_current_price(self, symbol: str = "BTC") -> Optional[float]:
        """Get current price from Yahoo Finance"""
        try:
            cache_key = f"price_{symbol}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            
            current_price = info.get('regularMarketPrice') or info.get('previousClose')
            
            if current_price:
                self._cache_data(cache_key, current_price)
                return float(current_price)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get current price from Yahoo Finance: {e}")
            return None
    
    def get_ticker_data(self, symbol: str = "BTC") -> Optional[Dict[str, Any]]:
        """Get ticker-like data from Yahoo Finance"""
        try:
            cache_key = f"ticker_{symbol}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            
            current_price = info.get('regularMarketPrice', 0)
            previous_close = info.get('previousClose', 0)
            
            price_change = current_price - previous_close if current_price and previous_close else 0
            price_change_pct = (price_change / previous_close * 100) if previous_close else 0
            
            ticker_data = {
                "symbol": symbol,
                "priceChange": price_change,
                "priceChangePercent": price_change_pct,
                "lastPrice": current_price,
                "volume": info.get('regularMarketVolume', 0),
                "quoteVolume": info.get('regularMarketVolume', 0) * current_price,
                "count": 0  # Not provided by Yahoo Finance
            }
            
            self._cache_data(cache_key, ticker_data)
            return ticker_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get ticker data from Yahoo Finance: {e}")
            return None
    
    def calculate_support_resistance(self, candles: List[Dict[str, Any]], lookback: int = 20) -> Dict[str, float]:
        """Calculate support and resistance levels from candlestick data"""
        if len(candles) < lookback:
            return {"support": 0, "resistance": 0, "range": 0}
        
        recent_candles = candles[-lookback:]
        highs = [candle["high"] for candle in recent_candles]
        lows = [candle["low"] for candle in recent_candles]
        
        resistance = max(highs)
        support = min(lows)
        range_size = resistance - support
        
        return {
            "support": support,
            "resistance": resistance,
            "range": range_size
        }
    
    def calculate_trend(self, candles: List[Dict[str, Any]], periods: int = 5) -> Dict[str, Any]:
        """Calculate trend direction and strength"""
        if len(candles) < periods:
            return {"trend": "NEUTRAL", "strength": 0, "direction": 0}
        
        recent_candles = candles[-periods:]
        closes = [candle["close"] for candle in recent_candles]
        
        # Calculate trend direction
        first_close = closes[0]
        last_close = closes[-1]
        price_change = (last_close - first_close) / first_close
        
        # Determine trend
        if price_change > 0.001:  # 0.1% uptrend
            trend = "UP"
        elif price_change < -0.001:  # 0.1% downtrend
            trend = "DOWN"
        else:
            trend = "NEUTRAL"
        
        # Calculate trend strength
        strength = abs(price_change)
        
        return {
            "trend": trend,
            "strength": strength,
            "direction": price_change,
            "first_close": first_close,
            "last_close": last_close
        }
    
    def calculate_volatility(self, candles: List[Dict[str, Any]], periods: int = 20) -> float:
        """Calculate price volatility"""
        if len(candles) < periods:
            return 0.0
        
        recent_candles = candles[-periods:]
        returns = []
        
        for i in range(1, len(recent_candles)):
            prev_close = recent_candles[i-1]["close"]
            curr_close = recent_candles[i]["close"]
            ret = (curr_close - prev_close) / prev_close
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Calculate standard deviation of returns
        volatility = statistics.stdev(returns)
        return volatility
    
    def get_market_analysis(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get comprehensive market analysis from Yahoo Finance data"""
        try:
            # Get different timeframe data
            candles_1m = self.get_1m_klines(symbol, 100)
            candles_5m = self.get_5m_klines(symbol, 100)
            candles_1h = self.get_1h_klines(symbol, 24)
            ticker = self.get_ticker_data(symbol)
            current_price = self.get_current_price(symbol)
            
            if not candles_5m or not candles_1h:
                return {"error": "Could not fetch candlestick data from Yahoo Finance"}
            
            if not current_price:
                # Fallback to last close price
                current_price = candles_5m[-1]["close"] if candles_5m else 0
            
            # Calculate indicators
            support_resistance_5m = self.calculate_support_resistance(candles_5m)
            support_resistance_1h = self.calculate_support_resistance(candles_1h)
            
            trend_5m = self.calculate_trend(candles_5m)
            trend_1h = self.calculate_trend(candles_1h)
            
            volatility_5m = self.calculate_volatility(candles_5m)
            volatility_1h = self.calculate_volatility(candles_1h)
            
            analysis = {
                "timestamp": time.time(),
                "symbol": symbol,
                "current_price": current_price,
                "candles_1m": candles_1m[-10:] if candles_1m else [],  # Last 10 1-min candles
                "candles_5m": candles_5m[-20:] if candles_5m else [],  # Last 20 5-min candles
                "candles_1h": candles_1h[-10:] if candles_1h else [],  # Last 10 1-hour candles
                "support_resistance_5m": support_resistance_5m,
                "support_resistance_1h": support_resistance_1h,
                "trend_5m": trend_5m,
                "trend_1h": trend_1h,
                "volatility_5m": volatility_5m,
                "volatility_1h": volatility_1h,
                "ticker": ticker,
                "market_condition": self._determine_market_condition(trend_5m, trend_1h, volatility_5m)
            }
            
            logger.success(f"✅ Yahoo Finance market analysis completed for {symbol}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in Yahoo Finance market analysis: {e}")
            return {"error": str(e)}
    
    def _determine_market_condition(self, trend_5m: Dict, trend_1h: Dict, volatility: float) -> str:
        """Determine overall market condition"""
        # High volatility
        if volatility > 0.02:  # 2% volatility
            return "HIGH_VOLATILITY"
        
        # Strong trends
        if trend_5m["strength"] > 0.01 and trend_1h["strength"] > 0.005:
            if trend_5m["trend"] == trend_1h["trend"]:
                return "STRONG_TREND"
            else:
                return "MIXED_SIGNALS"
        
        # Low volatility
        if volatility < 0.005:  # 0.5% volatility
            return "LOW_VOLATILITY"
        
        return "NORMAL"
    
    def test_connection(self) -> bool:
        """Test connection to Yahoo Finance"""
        try:
            current_price = self.get_current_price("BTC")
            if current_price and current_price > 0:
                logger.success("✅ Yahoo Finance connection successful")
                return True
            else:
                logger.error("❌ Yahoo Finance connection failed - no price data")
                return False
        except Exception as e:
            logger.error(f"❌ Yahoo Finance connection error: {e}")
            return False


def main():
    """Test the Yahoo Finance data fetcher"""
    logger.info("🔍 Testing Yahoo Finance Data Fetcher")
    logger.info("=" * 50)
    
    fetcher = YahooDataFetcher()
    
    # Test connection
    if not fetcher.test_connection():
        logger.error("❌ Cannot connect to Yahoo Finance")
        return
    
    # Test market analysis
    logger.info("📊 Getting market analysis...")
    analysis = fetcher.get_market_analysis("BTC")
    
    if "error" not in analysis:
        logger.success("✅ Market analysis successful!")
        logger.info(f"Current Price: ${analysis['current_price']:,.2f}")
        logger.info(f"5m Trend: {analysis['trend_5m']['trend']} ({analysis['trend_5m']['strength']*100:.2f}%)")
        logger.info(f"1h Trend: {analysis['trend_1h']['trend']} ({analysis['trend_1h']['strength']*100:.2f}%)")
        logger.info(f"5m Support: ${analysis['support_resistance_5m']['support']:,.2f}")
        logger.info(f"5m Resistance: ${analysis['support_resistance_5m']['resistance']:,.2f}")
        logger.info(f"Market Condition: {analysis['market_condition']}")
        logger.info(f"5m Candles: {len(analysis['candles_5m'])}")
        logger.info(f"1h Candles: {len(analysis['candles_1h'])}")
    else:
        logger.error(f"❌ Market analysis failed: {analysis['error']}")


if __name__ == "__main__":
    main()
