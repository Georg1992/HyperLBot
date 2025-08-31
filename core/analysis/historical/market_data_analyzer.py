#!/usr/bin/env python3
"""
Market Data Analyzer Module
Handles market data analysis and RSI calculations
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger
from core.constants import magic_numbers
from core.external.yahoo_data_fetcher import yahoo_data_fetcher
from core.external.yahoo_momentum_analyzer import momentum_analyzer
from core.market_data_manager import market_data_manager
# Complex session tracking imports removed - over-engineered for minimal benefit

class MarketDataAnalyzer:
    """Handles market data analysis and RSI calculations with session context"""
    
    def __init__(self):
        # Use global instances to eliminate duplicate objects and ensure consistency
        self.yahoo_fetcher = yahoo_data_fetcher
        self.momentum_analyzer = momentum_analyzer
        # Complex session tracking removed - over-engineered for minimal benefit
        logger.info("📊 Market Data Analyzer initialized - simplified for essential analysis only")
    
    def get_current_price(self) -> Optional[float]:
        """Get current price from Yahoo Finance (historical context only)"""
        try:
            # Get the most recent 5-minute candle
            candles = self.get_5m_candles("BTC", 1)
            if candles and len(candles) > 0:
                return candles[0]['close']
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get current price: {e}")
            return None
    
    def _calculate_sma(self, candles: List[Dict], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(candles) < period:
            return 0.0
        
        prices = [c['close'] for c in candles[-period:]]
        return sum(prices) / len(prices)
    
    def _determine_market_condition(self, sma_5m: float, sma_20m: float, current_price: float) -> str:
        """Determine market condition based on moving averages and current price"""
        if sma_5m == 0 or sma_20m == 0:
            return "NEUTRAL"
        
        if current_price > sma_5m > sma_20m:
            return "BULLISH"
        elif current_price < sma_5m < sma_20m:
            return "BEARISH"
        elif sma_5m > sma_20m:
            return "BULLISH"
        elif sma_5m < sma_20m:
            return "BEARISH"
        else:
            return "SIDEWAYS"
    
    # get_yahoo_analysis removed - duplicates TradingBot.get_yahoo_analysis() and YahooDataFetcher.get_market_analysis()
    # Use YahooDataFetcher.get_market_analysis() for authoritative Yahoo data
    
    def get_candles(self, symbol: str, interval: str, count: int) -> List[Dict[str, Any]]:
        """Get candles for any timeframe"""
        try:
            return self.yahoo_fetcher.get_klines(symbol, interval, count)
        except Exception as e:
            logger.error(f"❌ Failed to get {interval} candles: {e}")
            return []
    
    def get_1m_candles(self, symbol: str = "BTC", count: int = 10) -> List[Dict[str, Any]]:
        """Get 1-minute candles"""
        return self.get_candles(symbol, "1m", count)
    
    def get_5m_candles(self, symbol: str = "BTC", count: int = 10) -> List[Dict[str, Any]]:
        """Get 5-minute candles"""
        return self.get_candles(symbol, "5m", count)
    
    def get_1h_candles(self, symbol: str = "BTC", count: int = 10) -> List[Dict[str, Any]]:
        """Get 1-hour candles"""
        return self.get_candles(symbol, "1h", count)
    
    def get_1d_candles(self, symbol: str = "BTC", count: int = 10) -> List[Dict[str, Any]]:
        """Get 1-day candles"""
        return self.get_candles(symbol, "1d", count)
    
    def test_connection(self) -> bool:
        """Test Yahoo Finance connection"""
        try:
            test_candles = self.get_5m_candles("BTC", 5)
            return test_candles and len(test_candles) > 0
        except Exception as e:
            logger.error(f"❌ Yahoo Finance connection test failed: {e}")
            return False
    
    # get_weekly_trend_analysis removed - duplicates TradingBot.get_weekly_trend_analysis()
    # Use TradingBot.get_weekly_trend_analysis() for consistency
    
    # analyze_entry_point removed - duplicates PredictionEngine.analyze_entry_point()
    # Use PredictionEngine.analyze_entry_point() for authoritative entry analysis
    
    # calculate_prediction_win_probability removed - duplicates PredictionEngine.calculate_win_probability()
    # Use PredictionEngine.calculate_win_probability() for authoritative probability calculation
    
    def get_update_status(self) -> Dict[str, Any]:
        """Get update status for dashboard using centralized MarketDataManager"""
        try:
            # Use centralized cache status from MarketDataManager (BEST implementation)
            return market_data_manager.get_cache_status()
        except Exception as e:
            logger.error(f"❌ Failed to get update status: {e}")
            return {
                "last_update": time.time(),
                "status": "ERROR",
                "error": str(e)
            }
    
    # Complex session tracking methods removed - over-engineered for minimal benefit
    # start_session_tracking, add_session_data_point, get_session_analysis eliminated
    
    def get_analysis(self, current_price: float, volume: float, rsi: float, volatility: float) -> Dict[str, Any]:
        """Get minimal analysis - simplified to essential fields only"""
        try:
            # Minimal analysis with only fields needed by prediction engine
            analysis = {
                # Core fields required by prediction engine
                "current_price": current_price,
                "rsi": rsi,  # Use the actual RSI value passed in
                "trend": "NEUTRAL",  # Simplified - no complex session tracking needed
                # volume_category removed - TradingBot uses orderbook depth categorization directly
                "volatility_5m": volatility,  # Use the actual volatility value passed in
                
                # Minimal context
                "analysis_type": "simplified",
                "data_source": "direct_params",
                "timestamp": time.time()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get analysis: {e}")
            # Return fallback with required fields
            return {
                "current_price": current_price,
                "rsi": rsi,
                "trend": "NEUTRAL",
                # volume_category removed - TradingBot uses orderbook depth categorization only
                "volatility_5m": volatility,
                "market_condition": "NEUTRAL",
                "analysis_type": "fallback",
                "data_source": "fallback",
                "timestamp": time.time()
            }
    
    def _get_trend(self, yahoo_analysis: Dict[str, Any], session_context: Dict[str, Any]) -> str:
        """Get trend combining Yahoo and session data"""
        try:
            # Use session trend if available and session is mature
            if session_context.get("data_points", 0) >= 20:
                session_trend = session_context.get("session_trend", "NEUTRAL")
                if session_trend != "UNKNOWN":
                    return session_trend
            
            # Fall back to Yahoo trend
            return yahoo_analysis.get("market_condition", "NEUTRAL")
            
        except Exception as e:
            logger.error(f"❌ Failed to get trend: {e}")
            return "NEUTRAL"
    
    # Volume category methods removed - TradingBot now uses orderbook depth categorization directly
    # This eliminates conflict between trading volume categorization (USD scale) and orderbook depth (BTC scale)
    
    def end_session_tracking(self):
        """End session tracking"""
        self.session_manager.end_session()
        logger.info("🛑 Session tracking ended")
