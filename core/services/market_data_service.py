#!/usr/bin/env python3
"""
Market Data Service
Handles all market data orchestration and RSI management
Single Responsibility: Market data coordination
"""

import time
from typing import Dict, Any, Optional
from loguru import logger
from core.constants import technical_constants
from core.market_data_manager import market_data_manager
from core.analysis.trend_manager import trend_manager

class MarketDataService:
    """Market data orchestration service - handles all data coordination"""
    
    def __init__(self, historical_data_coordinator, hyperliquid_api, hyperliquid_websocket):
        self.historical_data_coordinator = historical_data_coordinator
        self.hyperliquid_api = hyperliquid_api
        self.hyperliquid_websocket = hyperliquid_websocket
        
        # RSI state (simple Yahoo-based system)
        self.yahoo_rsi_value = None
        self.rsi_initialized = False
        
        # Price caching for WebSocket
        self._cached_websocket_price = None
        self._last_price_update = 0
        
        # Emergency price fallback
        self._last_known_good_price = None
        self._last_known_good_time = 0
        
        logger.info("📊 Market Data Service initialized - Data orchestration")
    
    def initialize_yahoo_rsi(self):
        """Simple Yahoo Finance RSI initialization"""
        try:
            # Get 5-minute data for RSI calculation
            candles_5m = self.historical_data_coordinator.yahoo_fetcher.get_klines("BTC-USD", "5m", 30)
            if candles_5m and len(candles_5m) >= 15:
                # Calculate RSI using centralized MarketDataManager
                self.yahoo_rsi_value = market_data_manager.calculate_rsi_from_candles(candles_5m)
                self.rsi_initialized = True
                logger.success(f"📊 Yahoo RSI initialized: {self.yahoo_rsi_value:.2f}")
            else:
                logger.warning("⚠️ Not enough Yahoo 5m data for RSI, using default")
                self.yahoo_rsi_value = technical_constants.RSI_NEUTRAL
                self.rsi_initialized = True
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Yahoo RSI: {e}")
            self.yahoo_rsi_value = technical_constants.RSI_NEUTRAL
            self.rsi_initialized = True
    
    def get_yahoo_baseline_rsi_data(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Simple Yahoo Finance RSI data for trading decisions"""
        try:
            # Initialize Yahoo RSI if not already done
            if not self.rsi_initialized:
                self.initialize_yahoo_rsi()
            
            # Return simple RSI data structure
            return {
                "rsi": self.yahoo_rsi_value,
                "rsi_value": self.yahoo_rsi_value,
                "rsi_trend": self._get_rsi_trend(self.yahoo_rsi_value),
                "rsi_signal": self._get_rsi_signal(self.yahoo_rsi_value),
                "momentum": self._get_rsi_trend(self.yahoo_rsi_value),
                "confidence": 0.9 if self.yahoo_rsi_value is not None else 0.3,
                "data_source": "yahoo_finance_simple",
                "hyperliquid_price": hyperliquid_price or 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo RSI data: {e}")
            return self._get_default_rsi_data(hyperliquid_price, str(e))
    
    def get_yahoo_analysis(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get market analysis from Yahoo Finance using centralized MarketDataManager"""
        try:
            # Use centralized MarketDataManager for Yahoo data analysis
            analysis = market_data_manager.get_yahoo_data_with_analysis(
                self.historical_data_coordinator.yahoo_fetcher, "BTC", hyperliquid_price
            )
            
            if "error" not in analysis:
                logger.info(f"[CHART] Yahoo Finance analysis: ${analysis.get('current_price', 0):,.2f} - Market data retrieved")
                return analysis
            else:
                logger.error(f"❌ Yahoo Finance analysis failed: {analysis.get('error', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo Finance analysis: {e}")
            return {}
    
    def get_hyperliquid_price(self) -> Optional[float]:
        """Get current price with robust fallback strategy"""
        try:
            # PRIMARY: WebSocket cached price (real-time stream) 
            if (hasattr(self, '_cached_websocket_price') and 
                self._cached_websocket_price is not None and
                time.time() - self._last_price_update < 30):  # Price must be recent (30s)
                self._update_last_known_good_price(self._cached_websocket_price)
                return self._cached_websocket_price
            
            # SECONDARY: Direct WebSocket query
            if self.hyperliquid_websocket:
                ws_price = self.hyperliquid_websocket.get_current_price()
                if ws_price and ws_price > 0:
                    self._update_last_known_good_price(ws_price)
                    return ws_price
            
            # TERTIARY: HTTP API call
            logger.warning("⚠️ WebSocket price unavailable - using HTTP API fallback")
            hyperliquid_data = market_data_manager.get_hyperliquid_data(self.hyperliquid_api, "BTC")
            api_price = hyperliquid_data.get("current_price")
            
            if api_price:
                logger.warning(f"📡 HTTP API price: ${api_price:.2f} (WebSocket fallback)")
                self._update_last_known_good_price(api_price)
                return api_price
            
            # QUATERNARY: Yahoo Finance fallback (real-time data)
            logger.warning("🚨 Hyperliquid completely down - using Yahoo Finance fallback")
            yahoo_price = self._get_yahoo_realtime_price()
            if yahoo_price:
                logger.warning(f"📊 Yahoo Finance price: ${yahoo_price:.2f} (Emergency fallback)")
                return yahoo_price
            
            # EMERGENCY: Last known good price (if recent)
            if self._last_known_good_price and time.time() - self._last_known_good_time < 300:  # 5 minutes
                logger.error(f"🚨 Using last known good price: ${self._last_known_good_price:.2f} (Emergency fallback)")
                return self._last_known_good_price
            
            logger.error("🚨 ALL PRICE SOURCES FAILED - no price available")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get price: {e}")
            
            # Try emergency fallback
            if self._last_known_good_price and time.time() - self._last_known_good_time < 300:
                logger.error(f"🚨 Exception fallback - using last known price: ${self._last_known_good_price:.2f}")
                return self._last_known_good_price
            
            return None
    
    def get_weekly_trend_analysis(self) -> Dict[str, Any]:
        """Get weekly trend analysis for session context"""
        try:
            # Get weekly data directly
            candles_1d = self.historical_data_coordinator.yahoo_fetcher.get_klines("BTC-USD", "1d", 30)
            
            if not candles_1d or len(candles_1d) < 7:
                return {"error": "Insufficient weekly data", "weekly_trend": "UNKNOWN"}
            
            # Calculate weekly trend
            weekly_trend = trend_manager.calculate_trend(candles_1d, "1d")
            return weekly_trend
            
        except Exception as e:
            logger.error(f"❌ Weekly trend analysis failed: {e}")
            return {"error": str(e), "weekly_trend": "UNKNOWN"}
    
    def get_data_update_status(self) -> Dict[str, Any]:
        """Get data update status for monitoring"""
        try:
            # Use centralized MarketDataManager cache status
            return market_data_manager.get_cache_status()
        except Exception as e:
            logger.error(f"❌ Failed to get data update status: {e}")
            return {"status": "ERROR", "error": str(e)}
    
    def update_cached_websocket_price(self, price: float):
        """Update cached WebSocket price"""
        self._cached_websocket_price = price
        self._last_price_update = time.time()
        self._update_last_known_good_price(price)
    
    def _update_last_known_good_price(self, price: float):
        """Update emergency fallback price cache"""
        self._last_known_good_price = price
        self._last_known_good_time = time.time()
    
    def _get_yahoo_realtime_price(self) -> Optional[float]:
        """Get real-time price from Yahoo Finance as ultimate fallback"""
        try:
            # Get latest 1-minute candle for most recent price
            candles_1m = self.historical_data_coordinator.yahoo_fetcher.get_klines("BTC-USD", "1m", 1)
            if candles_1m and len(candles_1m) > 0:
                latest_close = float(candles_1m[-1]["close"])
                logger.info(f"📊 Yahoo Finance real-time price: ${latest_close:.2f}")
                return latest_close
            
            # If 1m fails, try 5m candle
            candles_5m = self.historical_data_coordinator.yahoo_fetcher.get_klines("BTC-USD", "5m", 1) 
            if candles_5m and len(candles_5m) > 0:
                latest_close = float(candles_5m[-1]["close"])
                logger.info(f"📊 Yahoo Finance 5m price: ${latest_close:.2f}")
                return latest_close
                
            return None
            
        except Exception as e:
            logger.error(f"❌ Yahoo Finance price fallback failed: {e}")
            return None
    
    def _get_rsi_trend(self, rsi_value: float) -> str:
        """Simple RSI trend determination"""
        if rsi_value is None:
            return "NEUTRAL"
        elif rsi_value >= 70:
            return "OVERBOUGHT"
        elif rsi_value <= 30:
            return "OVERSOLD"
        elif rsi_value >= 60:
            return "BULLISH"
        elif rsi_value <= 40:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def _get_rsi_signal(self, rsi_value: float) -> str:
        """Simple RSI signal determination"""
        if rsi_value is None:
            return "NEUTRAL"
        elif rsi_value >= 70:
            return "SELL"
        elif rsi_value <= 30:
            return "BUY"
        else:
            return "NEUTRAL"
    
    def _get_default_rsi_data(self, hyperliquid_price: float = None, error: str = "unknown") -> Dict[str, Any]:
        """Get default RSI data structure when calculation fails"""
        return {
            "rsi": technical_constants.RSI_NEUTRAL,
            "rsi_trend": "NEUTRAL",
            "rsi_signal": "HOLD", 
            "momentum": "NEUTRAL",
            "confidence": 0.3,
            "data_source": "fallback_default",
            "error": error,
            "hyperliquid_price": hyperliquid_price or 0.0
        }