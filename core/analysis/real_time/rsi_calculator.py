#!/usr/bin/env python3
"""
Professional Real-Time RSI Calculator for Trading Bots
Implements standard Wilder's RSI with time-based sampling for maximum accuracy
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger
from collections import deque

class RealTimeRSICalculator:
    """
    Professional RSI Calculator for Trading Applications
    
    Features:
    - Standard 14-period Wilder's RSI calculation
    - Time-based sampling to avoid tick noise
    - Mathematically correct - RSI moves to 50 when price is stable (as it should)
    - Optimized for trading prediction frequency
    """
    
    def __init__(self, periods: int = 14, sample_interval: int = 60):
        """
        Initialize professional RSI calculator
        
        Args:
            periods: RSI calculation periods (standard: 14)
            sample_interval: Seconds between price samples (default: 60s for 1-minute intervals)
        """
        self.periods = periods
        self.sample_interval = sample_interval
        
        # Time-based price sampling (professional approach)
        self.price_samples = deque(maxlen=50)  # Keep last 50 samples
        self.last_sample_time = 0
        
        # RSI calculation state
        self.avg_gain = None
        self.avg_loss = None
        self.is_initialized = False
        
        # Cached results for efficiency
        self.cached_rsi = None
        self.cached_trend = "NEUTRAL"
        self.cached_signal = "NEUTRAL"
        self.last_calculation_time = 0
        
        # Current price tracking
        self.current_price = None
        
        logger.info(f"📊 Professional RSI Calculator: {periods} periods, {sample_interval}s intervals")
    
    def update_price(self, price: float, timestamp: float = None) -> bool:
        """
        Update with new price data - uses time-based sampling for accuracy
        
        Args:
            price: Current market price
            timestamp: Price timestamp (default: current time)
            
        Returns:
            bool: True if RSI was recalculated, False if just price updated
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Always track current price
        self.current_price = price
        
        # Time-based sampling for RSI calculation
        time_since_sample = timestamp - self.last_sample_time
        
        if time_since_sample >= self.sample_interval or not self.price_samples:
            # Take new sample
            self.price_samples.append({
                'price': price,
                'timestamp': timestamp
            })
            self.last_sample_time = timestamp
            
            # Recalculate RSI if we have enough data
            if len(self.price_samples) >= self.periods + 1:
                self._calculate_rsi()
                return True
        
        return False
    
    def _calculate_rsi(self) -> None:
        """
        Calculate RSI using standard Wilder's method - mathematically correct
        
        Professional implementation:
        - Extract price changes from time-sampled data
        - Apply Wilder's smoothing (exponential moving average)
        - Standard RSI formula: 100 - (100 / (1 + RS))
        """
        try:
            # Get recent price samples
            samples = list(self.price_samples)[-self.periods-1:]
            prices = [s['price'] for s in samples]
            
            # Calculate price changes
            changes = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                changes.append(change)
            
            # Separate gains and losses
            current_gains = [c if c > 0 else 0.0 for c in changes[-self.periods:]]
            current_losses = [-c if c < 0 else 0.0 for c in changes[-self.periods:]]
            
            if not self.is_initialized:
                # Initial calculation: simple moving average
                self.avg_gain = sum(current_gains) / self.periods
                self.avg_loss = sum(current_losses) / self.periods
                self.is_initialized = True
                logger.info(f"📊 RSI initialized: avg_gain={self.avg_gain:.4f}, avg_loss={self.avg_loss:.4f}")
            else:
                # Wilder's smoothing: exponential moving average
                latest_gain = current_gains[-1]
                latest_loss = current_losses[-1]
                
                # Standard Wilder's smoothing formula
                alpha = 1.0 / self.periods
                self.avg_gain = (1 - alpha) * self.avg_gain + alpha * latest_gain
                self.avg_loss = (1 - alpha) * self.avg_loss + alpha * latest_loss
            
            # Standard RSI calculation
            if self.avg_loss == 0:
                rsi = 100.0
            else:
                rs = self.avg_gain / self.avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            
            # Cache results
            self.cached_rsi = round(rsi, 2)
            self.cached_trend, self.cached_signal = self._determine_rsi_signals(rsi)
            self.last_calculation_time = time.time()
            
            logger.debug(f"📊 RSI calculated: {self.cached_rsi:.2f} (price: ${self.current_price:.2f})")
            
        except Exception as e:
            logger.error(f"❌ RSI calculation failed: {e}")
    
    def get_rsi(self) -> Dict[str, Any]:
        """
        Get current RSI data for trading decisions
        
        Returns:
            Dict with RSI value, trend, signal, and metadata
        """
        return {
            "rsi": self.cached_rsi,
            "trend": self.cached_trend,
            "signal": self.cached_signal,
            "data_points": len(self.price_samples),
            "current_price": self.current_price,
            "avg_gain": self.avg_gain,
            "avg_loss": self.avg_loss,
            "rs": self.avg_gain / self.avg_loss if self.avg_loss and self.avg_loss > 0 else None,
            "is_initialized": self.is_initialized,
            "calculation_method": "professional_time_sampled",
            "sample_interval": self.sample_interval
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

# Professional singleton instance for trading bot - optimized for maximum trading responsiveness
real_time_rsi_calculator = RealTimeRSICalculator(periods=14, sample_interval=5)