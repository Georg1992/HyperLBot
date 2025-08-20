#!/usr/bin/env python3
"""
External Data Fetcher for Candlestick Data
Fetches candlestick data from Binance API and combines with Hyperliquid market data
"""

import requests
import time
import json
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime, timedelta

class ExternalDataFetcher:
    def __init__(self):
        self.binance_base_url = "https://api.binance.com/api/v3"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_binance_klines(self, symbol: str = "BTCUSDT", interval: str = "5m", limit: int = 100) -> List[Dict[str, Any]]:
        """Get candlestick data from Binance API"""
        try:
            endpoint = f"{self.binance_base_url}/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            logger.info(f"📊 Fetching {limit} {interval} candles for {symbol} from Binance...")
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert Binance format to standard format
            candles = []
            for candle in data:
                candles.append({
                    "open_time": candle[0],
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                    "close_time": candle[6],
                    "quote_volume": float(candle[7]),
                    "trades": int(candle[8]),
                    "taker_buy_base": float(candle[9]),
                    "taker_buy_quote": float(candle[10])
                })
            
            logger.success(f"✅ Retrieved {len(candles)} candles from Binance")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to get Binance klines: {e}")
            return []
    
    def get_binance_1h_klines(self, symbol: str = "BTCUSDT", limit: int = 24) -> List[Dict[str, Any]]:
        """Get 1-hour candlestick data from Binance"""
        return self.get_binance_klines(symbol, "1h", limit)
    
    def get_binance_5m_klines(self, symbol: str = "BTCUSDT", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 5-minute candlestick data from Binance"""
        return self.get_binance_klines(symbol, "5m", limit)
    
    def get_binance_1m_klines(self, symbol: str = "BTCUSDT", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 1-minute candlestick data from Binance"""
        return self.get_binance_klines(symbol, "1m", limit)
    
    def get_binance_ticker(self, symbol: str = "BTCUSDT") -> Optional[Dict[str, Any]]:
        """Get current ticker data from Binance"""
        try:
            endpoint = f"{self.binance_base_url}/ticker/24hr"
            params = {"symbol": symbol}
            
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"📊 Retrieved Binance ticker for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to get Binance ticker: {e}")
            return None
    
    def get_binance_orderbook(self, symbol: str = "BTCUSDT", limit: int = 20) -> Optional[Dict[str, Any]]:
        """Get order book data from Binance"""
        try:
            endpoint = f"{self.binance_base_url}/depth"
            params = {
                "symbol": symbol,
                "limit": limit
            }
            
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"📊 Retrieved Binance orderbook for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to get Binance orderbook: {e}")
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
        import statistics
        volatility = statistics.stdev(returns)
        return volatility
    
    def get_market_analysis(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Get comprehensive market analysis from Binance data"""
        try:
            # Get different timeframe data
            candles_1m = self.get_binance_1m_klines(symbol, 100)
            candles_5m = self.get_binance_5m_klines(symbol, 100)
            candles_1h = self.get_binance_1h_klines(symbol, 24)
            ticker = self.get_binance_ticker(symbol)
            
            if not candles_5m or not candles_1h:
                return {"error": "Could not fetch candlestick data"}
            
            # Calculate indicators
            support_resistance_5m = self.calculate_support_resistance(candles_5m)
            support_resistance_1h = self.calculate_support_resistance(candles_1h)
            
            trend_5m = self.calculate_trend(candles_5m)
            trend_1h = self.calculate_trend(candles_1h)
            
            volatility_5m = self.calculate_volatility(candles_5m)
            volatility_1h = self.calculate_volatility(candles_1h)
            
            current_price = candles_5m[-1]["close"] if candles_5m else 0
            
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
            
            logger.success(f"✅ Market analysis completed for {symbol}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in market analysis: {e}")
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
        """Test connection to Binance API"""
        try:
            ticker = self.get_binance_ticker("BTCUSDT")
            if ticker:
                logger.success("✅ Binance API connection successful")
                return True
            else:
                logger.error("❌ Binance API connection failed")
                return False
        except Exception as e:
            logger.error(f"❌ Binance API connection error: {e}")
            return False

def main():
    """Test the external data fetcher"""
    logger.info("🔍 Testing External Data Fetcher")
    logger.info("=" * 50)
    
    fetcher = ExternalDataFetcher()
    
    # Test connection
    if not fetcher.test_connection():
        logger.error("❌ Cannot connect to Binance API")
        return
    
    # Test market analysis
    logger.info("📊 Getting market analysis...")
    analysis = fetcher.get_market_analysis("BTCUSDT")
    
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
