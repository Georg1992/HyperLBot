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
from core.constants import data_constants, volume_constants, technical_constants, time_constants, magic_numbers
from core.external.yahoo_momentum_analyzer import momentum_analyzer
from core.market_data_manager import market_data_manager

class YahooDataFetcher:
    """
    Yahoo Finance data fetcher for BTC/USD historical data
    Provides real historical candlestick data aligned with Hyperliquid BTC/USD perpetuals
    NOTE: For real-time pricing, use Hyperliquid API exclusively
    """
    
    def __init__(self):
        self.symbol = "BTC-USD"
        # Note: Caching removed - now handled by MarketDataManager for centralization
        
        logger.info("🔗 Yahoo Finance Data Fetcher initialized for BTC-USD (HISTORICAL DATA ONLY)")
        logger.info("📊 Real-time pricing should come from Hyperliquid API")
        logger.info("📦 Simplified fetcher - caching handled by MarketDataManager")
    
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
        """Get candlestick data from Yahoo Finance (no caching - handled by MarketDataManager)"""
        try:
            
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
            
            # Individual candle retrieval logging removed - consolidated at analysis level
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to get {interval} klines from Yahoo Finance: {e}")
            return []
    
    # Redundant wrapper methods removed - use get_klines() directly
    # Eliminated: get_5m_klines, get_1m_klines, get_1h_klines
    
    # REMOVED: get_current_price method - Real-time pricing should come from Hyperliquid
    
    def get_ticker_data(self, symbol: str = "BTC") -> Optional[Dict[str, Any]]:
        """Get ticker-like data from Yahoo Finance (historical context only, no caching)"""
        try:
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
            candles_1m = self.get_klines(symbol, "1m", 120)  # 2 hours of 1m data for immediate momentum
            candles_5m = self.get_klines(symbol, "5m", 12)   # 1 hour of 5m data (core prediction analysis)
            candles_1h = self.get_klines(symbol, "1h", 84)   # 3.5 days of 1h data (daily trend context)
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
            
            # Simplified to raw data + basic analysis only (complex calculations in MarketDataManager)
            
            # Basic analysis with raw data + volume/momentum (no circular dependencies)
            analysis = {
                "timestamp": time.time(),
                "symbol": symbol,
                "current_price": current_price,  # Hyperliquid price for trading
                "yahoo_last_close": yahoo_last_close,  # Yahoo Finance historical close
                "price_difference": price_difference,  # Absolute difference
                "price_difference_pct": price_difference_pct,  # Percentage difference
                
                # Raw candle data (primary responsibility of YahooDataFetcher)
                "candles_1m": candles_1m,  # Full 120 1-min candles (2 hours)
                "candles_5m": candles_5m,  # Full 12 5-min candles (1 hour)
                "candles_1h": candles_1h,  # Full 84 1-hour candles (3.5 days)
                "candles_1d": candles_1d,  # Full 45 daily candles (6 weeks)
                "ticker": ticker,
                
                # Basic momentum analysis only (volume categorization removed - conflicts with orderbook)
                "momentum_data": momentum_analyzer.analyze_momentum(candles_5m),
                
                # For complex indicators, use market_data_manager.get_yahoo_data_with_analysis()
                "data_source": "yahoo_finance_raw_data"
            }
            
            logger.success(f"✅ Yahoo Finance market analysis completed for {symbol}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in Yahoo Finance market analysis: {e}")
            return {"error": str(e)}
    
    # _determine_market_condition() REMOVED - unused trend logic, replaced by TrendCalculator
    
    def test_connection(self) -> bool:
        """Test connection to Yahoo Finance (historical data only)"""
        try:
            # Test with historical data instead of current price
            candles = self.get_klines("BTC-USD", "5m", 10)
            if candles and len(candles) > 0:
                logger.success("✅ Yahoo Finance connection successful (historical data)")
                return True
            else:
                logger.error("❌ Yahoo Finance connection failed - no historical data")
                return False
        except Exception as e:
            logger.error(f"❌ Yahoo Finance connection error: {e}")
            return False

    # Volume categorization logic REMOVED - moved to VolumeCalculator for clean architecture
    # YahooDataFetcher now focuses on raw data fetching only
    
    # get_realtime_momentum_analysis removed - unused dead code

def main():
    """Test the Yahoo Finance data fetcher"""
    logger.info("🔍 Testing Yahoo Finance Data Fetcher (HISTORICAL DATA ONLY)")
    logger.info("=" * 60)
    
    fetcher = YahooDataFetcher()
    
    # Test connection
    if not fetcher.test_connection():
        logger.error("❌ Cannot connect to Yahoo Finance")
        return
    
    # Test raw data fetching (YahooDataFetcher now focuses on raw data only)
    logger.info("📊 Testing raw data fetching...")
    candles_5m = fetcher.get_klines("BTC-USD", "5m", 10)
    
    if candles_5m:
        logger.success("✅ Raw candle data fetched successfully!")
        logger.info(f"5m Candles: {len(candles_5m)}")
        logger.info(f"Latest close: ${candles_5m[-1]['close']:,.2f}")
        
        # Test centralized analysis via MarketDataManager
        logger.info("📊 Testing centralized analysis...")
        
        mock_hyperliquid_price = magic_numbers.TEST_BTC_PRICE
        analysis = market_data_manager.get_yahoo_data_with_analysis(fetcher, "BTC", mock_hyperliquid_price)
        
        if "error" not in analysis:
            logger.success("✅ Centralized analysis successful!")
            logger.info(f"Current Price: ${analysis['current_price']:,.2f}")
            logger.info(f"RSI: {analysis.get('rsi_5m', 'N/A')}")
            logger.info(f"Volatility: {analysis.get('volatility_5m', 'N/A')}")
            logger.info(f"Data Source: {analysis['data_source']}")
        else:
            logger.error(f"❌ Centralized analysis failed: {analysis['error']}")
    else:
        logger.error("❌ Failed to fetch raw candle data")

# Global instance to eliminate duplicate instances across the codebase
yahoo_data_fetcher = YahooDataFetcher()

if __name__ == "__main__":
    main()
