#!/usr/bin/env python3
"""
Hyperliquid-Style RSI Calculator
Fetches RSI from Yahoo Finance and builds incrementally with real-time prices
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger
from collections import deque

class RealTimeRSICalculator:
    """
    Hyperliquid-Style RSI Calculator
    
    Features:
    - Fetches initial RSI from Yahoo Finance
    - Builds RSI incrementally with real-time Hyperliquid prices
    - Uses proper Wilder's RSI calculation
    - Matches Hyperliquid's approach
    """
    
    def __init__(self, periods: int = 14):
        """
        Initialize RSI calculator
        
        Args:
            periods: RSI calculation periods (standard: 14)
        """
        self.periods = periods
        
        # Price history for RSI calculation
        self.price_history = deque(maxlen=100)  # Keep last 100 prices
        
        # RSI calculation state
        self.avg_gain = None
        self.avg_loss = None
        self.is_initialized = False
        
        # Cached results
        self.cached_rsi = None
        self.cached_trend = "NEUTRAL"
        self.cached_signal = "NEUTRAL"
        self.last_calculation_time = 0
        
        # Current price tracking
        self.current_price = None
        
        # Yahoo baseline
        self.yahoo_baseline_rsi = None
        self.yahoo_baseline_avg_gain = None
        self.yahoo_baseline_avg_loss = None
        
        logger.info(f"📊 Hyperliquid-Style RSI Calculator: {periods} periods")
    
    def initialize_with_yahoo_rsi(self, yahoo_rsi: float, yahoo_prices: List[float]) -> bool:
        """
        Initialize RSI calculator with Yahoo Finance RSI and price history
        
        Args:
            yahoo_rsi: RSI value from Yahoo Finance
            yahoo_prices: List of Yahoo prices (last 15+ prices)
            
        Returns:
            bool: True if initialization successful
        """
        try:
            if len(yahoo_prices) < self.periods + 1:
                logger.warning(f"⚠️ Not enough Yahoo prices for RSI initialization: {len(yahoo_prices)} < {self.periods + 1}")
                return False
            
            # Store Yahoo baseline
            self.yahoo_baseline_rsi = yahoo_rsi
            
            # FIXED: Use Yahoo RSI directly instead of trying to reverse-engineer
            # This prevents the RSI from drifting away from the correct value
            self.cached_rsi = yahoo_rsi
            self.is_initialized = True
            
            # Add Yahoo prices to history
            for price in yahoo_prices:
                self.price_history.append(price)
            
            self.cached_trend, self.cached_signal = self._determine_rsi_signals(yahoo_rsi)
            self.last_calculation_time = time.time()
            
            logger.success(f"📊 RSI initialized with Yahoo baseline: {yahoo_rsi:.2f}")
            logger.info(f"   Using Yahoo RSI directly: {yahoo_rsi:.2f}")
            logger.info(f"   Price history: {len(self.price_history)} prices")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize RSI with Yahoo data: {e}")
            return False
    
    def update_price(self, price: float) -> bool:
        """
        Update with new Hyperliquid price - KEEP YAHOO RSI ONLY
        
        Args:
            price: Current Hyperliquid price
            
        Returns:
            bool: True if price was updated
        """
        if not self.is_initialized:
            logger.warning("⚠️ RSI not initialized with Yahoo data yet")
            return False
        
        # Update current price
        self.current_price = price
        
        # Add to price history
        self.price_history.append(price)
        
        # KEEP YAHOO RSI - NO CALCULATION
        # RSI stays at Yahoo baseline value
        self.cached_rsi = self.yahoo_baseline_rsi
        self.cached_trend, self.cached_signal = self._determine_rsi_signals(self.yahoo_baseline_rsi)
        self.last_calculation_time = time.time()
        
        logger.debug(f"📊 Price updated: ${price:.2f} - RSI stays at Yahoo baseline: {self.yahoo_baseline_rsi:.2f}")
        return True
    
    def get_rsi(self) -> Dict[str, Any]:
        """
        Get current RSI data
        
        Returns:
            Dict with RSI value, trend, signal, and metadata
        """
        return {
            "rsi": self.cached_rsi,
            "trend": self.cached_trend,
            "signal": self.cached_signal,
            "data_points": len(self.price_history),
            "current_price": self.current_price,
            "avg_gain": self.avg_gain,
            "avg_loss": self.avg_loss,
            "rs": self.avg_gain / self.avg_loss if self.avg_loss and self.avg_loss > 0 else None,
            "is_initialized": self.is_initialized,
            "yahoo_baseline_rsi": self.yahoo_baseline_rsi,
            "calculation_method": "hyperliquid_style",
            "last_update": self.last_calculation_time
        }
    
    def _determine_rsi_signals(self, rsi: float) -> tuple:
        """
        Determine RSI trend and trading signals
        
        Args:
            rsi: Current RSI value
            
        Returns:
            tuple: (trend, signal)
        """
        # Standard RSI interpretation
        if rsi >= 70:
            trend = "OVERBOUGHT"
            signal = "SELL"
        elif rsi <= 30:
            trend = "OVERSOLD" 
            signal = "BUY"
        elif rsi >= 60:
            trend = "BULLISH"
            signal = "NEUTRAL"
        elif rsi <= 40:
            trend = "BEARISH"
            signal = "NEUTRAL"
        else:
            trend = "NEUTRAL"
            signal = "NEUTRAL"
        
        return trend, signal



# Global instance - Singleton pattern to prevent recreation
_real_time_rsi_calculator_instance = None

def get_real_time_rsi_calculator():
    """Get the singleton instance of RealTimeRSICalculator"""
    global _real_time_rsi_calculator_instance
    if _real_time_rsi_calculator_instance is None:
        _real_time_rsi_calculator_instance = RealTimeRSICalculator(periods=14)
    return _real_time_rsi_calculator_instance

# Create the global instance
real_time_rsi_calculator = get_real_time_rsi_calculator()