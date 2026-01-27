#!/usr/bin/env python3
"""
Price Update Handler - Single Responsibility: Handle WebSocket Price Updates
Extracted from MarketDataService for SRP compliance
"""

import time
from typing import Dict, Any, Optional
from loguru import logger
from core.constants import TradingConstants


class PriceUpdateHandler:
    """Handles WebSocket price updates and RSI updates"""
    
    def __init__(self, hyperliquid_websocket=None, hyperliquid_api=None, cache=None):
        """
        Initialize Price Update Handler
        
        Args:
            hyperliquid_websocket: HyperliquidWebSocket instance (optional)
            hyperliquid_api: HyperliquidAPI instance (optional)
            cache: CentralizedCache instance (optional, falls back to global singleton)
        """
        self.hyperliquid_websocket = hyperliquid_websocket
        self.hyperliquid_api = hyperliquid_api
        
        # Dependency injection for cache (DIP compliance)
        if cache is None:
            from core.services.centralized_cache import get_global_centralized_cache
            self._cache = get_global_centralized_cache()
        else:
            self._cache = cache
        
        # Real-time price streaming (single source of truth)
        self._current_price = None
        self._price_timestamp = 0
        self._price_update_interval = TradingConstants.PRICE_UPDATE_INTERVAL
        
        # RSI update throttling for dashboard (prevent spam from rapid price changes)
        self._last_rsi_dashboard_update = 0
        self._rsi_dashboard_update_interval = 0.5  # Update dashboard at most every 500ms
        
        # RSI calculator reference (will be set by MarketDataService)
        self._rsi_calculator = None
    
    def set_rsi_calculator(self, rsi_calculator):
        """Set RSI calculator reference for price updates"""
        self._rsi_calculator = rsi_calculator
    
    def get_current_price(self) -> Optional[float]:
        """
        Get current price (single source of truth)
        
        Fetches from WebSocket if price is stale or not available
        """
        try:
            current_time = time.time()
            # Check if price is stale or not available
            if (self._current_price is None or 
                current_time - self._price_timestamp > self._price_update_interval):
                # Try to get fresh price from WebSocket
                if self.hyperliquid_websocket:
                    new_price = self.hyperliquid_websocket.get_current_price()
                    if new_price and new_price > 0:
                        if new_price != self._current_price:
                            self._current_price = new_price
                            self._price_timestamp = current_time
                # Fallback to API if WebSocket unavailable
                elif self.hyperliquid_api:
                    from config.config import TradingConfig
                    new_price = self.hyperliquid_api.get_current_price(TradingConfig.SYMBOL)
                    if new_price and new_price > 0:
                        self._current_price = new_price
                        self._price_timestamp = current_time
            
            return self._current_price
        except Exception as e:
            logger.debug(f"⚠️ Failed to get current price: {e}")
            return self._current_price  # Return cached price if fetch fails
    
    def get_price_timestamp(self) -> float:
        """Get timestamp of last price update"""
        return self._price_timestamp
    
    def update_current_price(self) -> Optional[float]:
        """
        Update current price from WebSocket (if available)
        
        Returns:
            Current price if available, None otherwise
        """
        try:
            if self.hyperliquid_websocket:
                new_price = self.hyperliquid_websocket.get_current_price()
                if new_price is not None and new_price != self._current_price:
                    self._current_price = new_price
                    self._price_timestamp = time.time()
            return self._current_price
        except Exception as e:
            logger.debug(f"⚠️ Price update check failed (non-critical): {e}")
            return self._current_price
    
    def on_websocket_price_update(self, price_data: Dict[str, Any], market_data_service=None) -> None:
        """
        Callback for WebSocket price updates - update RSI immediately
        
        CRITICAL: This is a high-frequency callback. Errors are logged at debug level
        to avoid spam, but critical errors should still be visible.
        
        Args:
            price_data: Price data from WebSocket
            market_data_service: MarketDataService instance (optional, for updating analysis data)
        """
        try:
            new_price = price_data.get("current_price") if price_data else None
            if new_price and new_price > 0:
                # Update internal price cache
                self._current_price = new_price
                self._price_timestamp = time.time()
                # Update RSI immediately
                self._update_rsi_with_price(new_price, market_data_service=market_data_service)
        except (KeyError, TypeError, ValueError) as e:
            # Handle specific data format errors (non-critical for callback)
            logger.debug(f"⚠️ WebSocket price update callback error (non-critical): {e}")
        except Exception as e:
            # Unexpected errors should be logged (but not spam)
            logger.warning(f"⚠️ Unexpected error in WebSocket price callback: {e}")
    
    def _update_rsi_with_price(self, new_price: float, market_data_service=None) -> None:
        """
        Update RSI immediately when price changes (called from price updates)
        
        CRITICAL: This is called frequently. Errors are handled gracefully but logged.
        
        Args:
            new_price: New price value
            market_data_service: MarketDataService instance (optional, for updating analysis data)
        """
        try:
            if not self._rsi_calculator:
                return  # RSI calculator not available yet
            
            if not self._rsi_calculator.rsi_initialized:
                return  # RSI not initialized yet - will be initialized in get_unified_analysis_data
            
            old_rsi = self._rsi_calculator.current_rsi
            # update_realtime_rsi() returns updated RSI data - store it immediately
            rsi_result = self._rsi_calculator.update_realtime_rsi(new_price)
            new_rsi = self._rsi_calculator.current_rsi
            
            # Store updated RSI data to cache so get_rsi_analysis() returns fresh data
            if market_data_service:
                market_data_service.update_analysis_data("rsi", rsi_result)
            
            # Trigger instant dashboard update if RSI changed significantly (throttled)
            if abs(new_rsi - old_rsi) >= TradingConstants.RSI_CHANGE_THRESHOLD:
                self._trigger_instant_rsi_dashboard_update()
        except (AttributeError, TypeError) as e:
            # Handle specific errors (missing attributes, wrong types) - non-critical
            logger.debug(f"⚠️ RSI update error (non-critical): {e}")
        except Exception as e:
            # Unexpected errors should be logged
            logger.warning(f"⚠️ Unexpected error in RSI update: {e}")
    
    def _trigger_instant_rsi_dashboard_update(self) -> None:
        """
        Trigger instant dashboard update for RSI changes (throttled to prevent spam)
        
        CRITICAL: This is called frequently. Dashboard might not be initialized yet,
        which is acceptable. Errors are handled gracefully.
        """
        try:
            current_time = time.time()
            # Throttle: Update dashboard at most every 500ms
            if current_time - self._last_rsi_dashboard_update < self._rsi_dashboard_update_interval:
                return  # Throttled - not an error
            
            self._last_rsi_dashboard_update = current_time
            
            # Get dashboard instance and trigger immediate update
            from core.dashboard.web_dashboard import EventDrivenTradingDashboard
            dashboard = EventDrivenTradingDashboard.get_global_instance()
            if dashboard:
                dashboard.force_data_update()
            # If dashboard is None, that's okay - it might not be initialized yet
        except (ImportError, AttributeError) as e:
            # Handle specific errors (import issues, missing attributes) - non-critical
            logger.debug(f"⚠️ Dashboard update error (non-critical): {e}")
        except Exception as e:
            # Unexpected errors should be logged
            logger.warning(f"⚠️ Unexpected error in dashboard update trigger: {e}")
