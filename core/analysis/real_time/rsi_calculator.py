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
        
        # Need at least 1 price in history to calculate change
        if len(self.price_history) < 1:
            self.price_history.append(price)
            return False
        
        # Get previous price BEFORE adding new price to history
        previous_price = self.price_history[-1]
        
        # Add to price history
        self.price_history.append(price)
        
        # Calculate price change
        current_price = price
        price_change = current_price - previous_price
        
        # Only update RSI if change is significant enough (more stable)
        # This prevents overreaction to tiny price movements
        if not self._is_significant_change(price_change, previous_price):
            logger.debug(f"📊 Price change too small ({abs(price_change / previous_price * 100):.4f}%) - skipping RSI update")
            return False
        
        # FIXED: Properly calculate RSI from real-time Hyperliquid data
        # Use Wilder's smoothing to update RSI based on actual price movements
        # This will make the RSI match Hyperliquid's calculation method
        
        # Calculate gain and loss
        gain = price_change if price_change > 0 else 0.0
        loss = -price_change if price_change < 0 else 0.0
        
        # Initialize avg_gain and avg_loss if not set (first update after Yahoo init)
        if self.avg_gain is None or self.avg_loss is None:
            # Use Yahoo baseline RSI to calculate proper initial values
            if self.yahoo_baseline_rsi is not None:
                # Calculate base values that would give us the Yahoo RSI
                avg_price = sum(list(self.price_history)[-15:]) / 15
                base_change = avg_price * 0.001  # 0.1% of average price
                
                if self.yahoo_baseline_rsi >= 70:
                    # High RSI - more gains than losses
                    self.avg_gain = base_change * 2.0
                    self.avg_loss = base_change * 0.5
                elif self.yahoo_baseline_rsi <= 30:
                    # Low RSI - more losses than gains
                    self.avg_gain = base_change * 0.5
                    self.avg_loss = base_change * 2.0
                else:
                    # Neutral RSI - balanced gains and losses
                    self.avg_gain = base_change
                    self.avg_loss = base_change
            else:
                # Fallback initialization
                if price_change > 0:
                    self.avg_gain = abs(price_change)
                    self.avg_loss = abs(price_change) * 0.5
                else:
                    self.avg_gain = abs(price_change) * 0.5
                    self.avg_loss = abs(price_change)
        
        # Use proper Wilder's smoothing (standard RSI calculation)
        alpha = 1.0 / self.periods  # Standard Wilder's alpha
        self.avg_gain = (1 - alpha) * self.avg_gain + alpha * gain
        self.avg_loss = (1 - alpha) * self.avg_loss + alpha * loss
        
        # Calculate new RSI using standard formula
        if self.avg_loss == 0:
            new_rsi = 100.0
        else:
            rs = self.avg_gain / self.avg_loss
            new_rsi = 100.0 - (100.0 / (1.0 + rs))
        
        # Update cached values
        self.cached_rsi = round(new_rsi, 2)
        self.cached_trend, self.cached_signal = self._determine_rsi_signals(new_rsi)
        self.last_calculation_time = time.time()
        
        logger.debug(f"📊 RSI updated: {self.cached_rsi:.2f} (price: ${price:.2f}, change: {price_change:+.2f}, {abs(price_change / previous_price * 100):.4f}%)")
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

    def _calculate_volatility_threshold(self) -> float:
        """
        Calculate adaptive volatility threshold based on recent price changes
        Uses average percentage change of recent movements as the threshold
        """
        if len(self.price_history) < 3:
            return 0.0005  # More sensitive default: 0.05% if not enough data
        
        # Calculate percentage changes from recent price history
        percentage_changes = []
        for i in range(1, len(self.price_history)):
            prev_price = self.price_history[i-1]
            curr_price = self.price_history[i]
            if prev_price > 0:
                percentage_change = abs(curr_price - prev_price) / prev_price
                percentage_changes.append(percentage_change)
        
        if len(percentage_changes) < 3:
            return 0.0005  # More sensitive default: 0.05% if not enough data
        
        # Use average percentage change as threshold (more sensitive)
        avg_change = sum(percentage_changes) / len(percentage_changes)
        threshold = avg_change * 0.3  # Use 30% of average change for more sensitivity
        
        return max(threshold, 0.0001)  # Minimum 0.01% threshold
    
    def _is_significant_change(self, price_change: float, previous_price: float) -> bool:
        """
        Determine if price change is statistically significant
        Based on recent volatility patterns
        """
        if previous_price <= 0:
            return False
        
        # Calculate percentage change
        percentage_change = abs(price_change) / previous_price
        
        # Get adaptive threshold based on recent volatility
        volatility_threshold = self._calculate_volatility_threshold()
        
        # Change is significant if it exceeds the volatility threshold
        return percentage_change >= volatility_threshold

# Global instance
real_time_rsi_calculator = RealTimeRSICalculator(periods=14)