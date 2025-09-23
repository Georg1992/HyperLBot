#!/usr/bin/env python3
"""
Yahoo Finance API Client
Provides historical BTC/USD data that aligns with Hyperliquid BTC/USD perpetuals
NOTE: This API is for HISTORICAL DATA ONLY. Real-time pricing should come from Hyperliquid.
"""

import time
import yfinance as yf
from typing import Dict, List, Any, Optional
from loguru import logger
# # from datetime import datetime, timedelta  # Removed unused import  # Removed unused import
from core.constants import data_constants, technical_constants, time_constants, magic_numbers
from core.external.yahoo_momentum_analyzer import momentum_analyzer
# from core.market_data_manager import market_data_manager  # Removed unused import

class YahooAPI:
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


# Global instance to eliminate duplicate instances across the codebase
yahoo_api = YahooAPI()

