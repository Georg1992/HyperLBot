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
            
            # Calculate Yahoo's avg_gain and avg_loss from the RSI value
            if yahoo_rsi == 100:
                self.yahoo_baseline_avg_gain = 1.0
                self.yahoo_baseline_avg_loss = 0.0
            elif yahoo_rsi == 0:
                self.yahoo_baseline_avg_gain = 0.0
                self.yahoo_baseline_avg_loss = 1.0
            else:
                # Reverse calculate RS from RSI
                rs = (100.0 - yahoo_rsi) / yahoo_rsi
                # We need to estimate avg_gain and avg_loss
                # For initialization, we'll use a reasonable ratio
                self.yahoo_baseline_avg_gain = rs * 0.01  # Small base value
                self.yahoo_baseline_avg_loss = 0.01
            
            # Initialize with Yahoo values
            self.avg_gain = self.yahoo_baseline_avg_gain
            self.avg_loss = self.yahoo_baseline_avg_loss
            self.cached_rsi = yahoo_rsi
            self.is_initialized = True
            
            # Add Yahoo prices to history
            for price in yahoo_prices:
                self.price_history.append(price)
            
            self.cached_trend, self.cached_signal = self._determine_rsi_signals(yahoo_rsi)
            self.last_calculation_time = time.time()
            
            logger.success(f"📊 RSI initialized with Yahoo baseline: {yahoo_rsi:.2f}")
            logger.info(f"   Yahoo avg_gain: {self.yahoo_baseline_avg_gain:.6f}")
            logger.info(f"   Yahoo avg_loss: {self.yahoo_baseline_avg_loss:.6f}")
            logger.info(f"   Price history: {len(self.price_history)} prices")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize RSI with Yahoo data: {e}")
            return False
    
    def update_price(self, price: float) -> bool:
        """
        Update with new Hyperliquid price and recalculate RSI
        
        Args:
            price: Current Hyperliquid price
            
        Returns:
            bool: True if RSI was recalculated
        """
        if not self.is_initialized:
            logger.warning("⚠️ RSI not initialized with Yahoo data yet")
            return False
        
        # Update current price
        self.current_price = price
        
        # Add to price history
        self.price_history.append(price)
        
        # Need at least 2 prices to calculate change
        if len(self.price_history) < 2:
            return False
        
        # Calculate price change
        current_price = price
        previous_price = self.price_history[-2]
        price_change = current_price - previous_price
        
        # Calculate gain and loss
        gain = price_change if price_change > 0 else 0.0
        loss = -price_change if price_change < 0 else 0.0
        
        # Update averages using Wilder's smoothing
        alpha = 1.0 / self.periods
        self.avg_gain = (1 - alpha) * self.avg_gain + alpha * gain
        self.avg_loss = (1 - alpha) * self.avg_loss + alpha * loss
        
        # Calculate new RSI
        if self.avg_loss == 0:
            new_rsi = 100.0
        else:
            rs = self.avg_gain / self.avg_loss
            new_rsi = 100.0 - (100.0 / (1.0 + rs))
        
        # Update cached values
        self.cached_rsi = round(new_rsi, 2)
        self.cached_trend, self.cached_signal = self._determine_rsi_signals(new_rsi)
        self.last_calculation_time = time.time()
        
        logger.debug(f"📊 RSI updated: {self.cached_rsi:.2f} (price: ${price:.2f}, change: {price_change:+.2f})")
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

# Global instance
real_time_rsi_calculator = RealTimeRSICalculator(periods=14)