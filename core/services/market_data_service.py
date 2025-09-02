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
# trend_manager import removed - using TrendCalculator via MarketDataManager (proper SRP)

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
        
# Emergency price fallback removed - keeping it simple (Hyperliquid only)
        
        logger.info("📊 Market Data Service initialized - Data orchestration")
    
    def initialize_yahoo_rsi(self):
        """Initialize Yahoo Finance baseline RSI using RSICalculator"""
        try:
            # Get 5-minute data for RSI baseline calculation (user likes this value)
            candles_5m = self.historical_data_coordinator.yahoo_fetcher.get_klines("BTC-USD", "5m", 30)
            if candles_5m and len(candles_5m) >= 15:
                # Calculate baseline RSI using global RSICalculator (single source)
                from core.market_data_manager import global_rsi_calculator
                self.yahoo_rsi_value = global_rsi_calculator.calculate_yahoo_baseline_rsi(candles_5m)
                self.rsi_initialized = True
                logger.success(f"📊 Yahoo baseline RSI initialized: {self.yahoo_rsi_value:.2f} (global RSI calculator)")
            else:
                logger.warning("⚠️ Not enough Yahoo 5m data for RSI baseline, using default")
                self.yahoo_rsi_value = technical_constants.RSI_NEUTRAL
                self.rsi_initialized = True
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Yahoo baseline RSI: {e}")
            self.yahoo_rsi_value = technical_constants.RSI_NEUTRAL
            self.rsi_initialized = True
    
    def get_yahoo_baseline_rsi_data(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get current RSI data (baseline + real-time updates) for trading decisions"""
        try:
            # Initialize Yahoo baseline RSI if not already done
            if not self.rsi_initialized:
                self.initialize_yahoo_rsi()
            
            # Get current RSI data from global RSICalculator (single source)
            from core.market_data_manager import global_rsi_calculator
            rsi_data = global_rsi_calculator.get_current_rsi_data()
            
            # Return comprehensive RSI data structure
            return {
                "rsi": rsi_data.get("rsi", self.yahoo_rsi_value),
                "rsi_value": rsi_data.get("rsi", self.yahoo_rsi_value),
                "rsi_baseline": rsi_data.get("rsi_baseline", self.yahoo_rsi_value),
                "rsi_trend": rsi_data.get("rsi_trend", "NEUTRAL"),
                "rsi_signal": rsi_data.get("rsi_signal", "NEUTRAL"),
                "rsi_momentum": rsi_data.get("rsi_momentum", 0.0),
                "momentum": rsi_data.get("rsi_trend", "NEUTRAL"),  # Backward compatibility
                "confidence": 0.9 if rsi_data.get("initialized", False) else 0.3,
                "data_source": rsi_data.get("data_source", "rsi_calculator"),
                "hyperliquid_price": hyperliquid_price or 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get RSI data: {e}")
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
                
                # YAHOO CORRECTION POINT: Calibrate real-time RSI when fresh Yahoo arrives
                yahoo_rsi = analysis.get("rsi_5m")
                if yahoo_rsi:
                    from core.market_data_manager import global_rsi_calculator
                    
                    # Check accuracy of real-time RSI before correction
                    if global_rsi_calculator.rsi_initialized:
                        current_realtime_rsi = global_rsi_calculator.current_rsi
                        accuracy_gap = abs(current_realtime_rsi - yahoo_rsi)
                        
                        logger.info(f"📊 Yahoo correction: Real-time {current_realtime_rsi:.2f} → Yahoo {yahoo_rsi:.2f} (gap: {accuracy_gap:.2f})")
                        
                        # Correct real-time RSI to Yahoo value (correction point)
                        global_rsi_calculator.current_rsi = yahoo_rsi
                        global_rsi_calculator.baseline_rsi = yahoo_rsi
                        
                        # Log accuracy assessment
                        if accuracy_gap <= 1.0:
                            logger.info("✅ Real-time RSI accuracy: EXCELLENT")
                        elif accuracy_gap <= 2.0:
                            logger.info("✅ Real-time RSI accuracy: GOOD")
                        else:
                            logger.warning(f"⚠️ Real-time RSI accuracy: NEEDS IMPROVEMENT")
                
                return analysis
            else:
                logger.error(f"❌ Yahoo Finance analysis failed: {analysis.get('error', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo Finance analysis: {e}")
            return {}
    
    def get_hyperliquid_price(self) -> Optional[float]:
        """Get current price from Hyperliquid ONLY (simple and focused)"""
        try:
            # PRIMARY: WebSocket cached price (real-time stream) 
            if (hasattr(self, '_cached_websocket_price') and 
                self._cached_websocket_price is not None and
                time.time() - self._last_price_update < 30):  # Price must be recent (30s)
                return self._cached_websocket_price
            
            # SECONDARY: Direct WebSocket query
            if self.hyperliquid_websocket:
                ws_price = self.hyperliquid_websocket.get_current_price()
                if ws_price and ws_price > 0:
                    return ws_price
            
            # FALLBACK: HTTP API call
            logger.warning("⚠️ WebSocket price unavailable - using HTTP API fallback")
            hyperliquid_data = market_data_manager.get_hyperliquid_data(self.hyperliquid_api, "BTC")
            api_price = hyperliquid_data.get("current_price")
            
            if api_price:
                logger.warning(f"📡 HTTP API price: ${api_price:.2f} (WebSocket fallback)")
                return api_price
            
            logger.error("❌ Hyperliquid price unavailable")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid price: {e}")
            return None
    
    def get_weekly_trend_analysis(self) -> Dict[str, Any]:
        """Get weekly trend analysis for session context"""
        try:
            # Get weekly data directly
            candles_1d = self.historical_data_coordinator.yahoo_fetcher.get_klines("BTC-USD", "1d", 30)
            
            if not candles_1d or len(candles_1d) < 7:
                return {"error": "Insufficient weekly data", "weekly_trend": "UNKNOWN"}
            
            # Calculate weekly trend using MarketDataManager (proper delegation)
            weekly_trend = market_data_manager.calculate_trend(candles_1d, "1d")
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
    
    # Volatility categorization moved to MarketDataManager (proper location for data analysis)
    
    def update_cached_websocket_price(self, price: float):
        """Update cached WebSocket price (simple)"""
        self._cached_websocket_price = price
        self._last_price_update = time.time()
    
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