#!/usr/bin/env python3
"""
RSI Calculator Module
Centralized RSI calculations for both baseline and real-time updates
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from collections import deque
from core.constants import technical_constants, MagicNumbers


class RSICalculator:
    """Centralized RSI calculation system for baseline and real-time updates"""
    
    def __init__(self):
        # Scientific RSI calculation state (reference chart: RSI updates every tick)
        self.periods = 14
        self.price_history = deque(maxlen=200)  # Store price history for calculations
        
        # Wilder's smoothing state (scientifically accurate)
        self.wilder_avg_gain = 0.0
        self.wilder_avg_loss = 0.0
        self.alpha = 1.0 / self.periods  # Wilder's smoothing constant
        
        # RSI values and state
        self.current_rsi = technical_constants.RSI_NEUTRAL
        self.baseline_rsi = technical_constants.RSI_NEUTRAL
        self.previous_rsi = technical_constants.RSI_NEUTRAL
        self.rsi_initialized = False
        self.last_price = 0.0
        
        logger.info("🔬 RSI Calculator initialized - Scientific every-tick Wilder's smoothing")
    
    def calculate_yahoo_baseline_rsi(self, candles: List[Dict], periods: int = 14) -> float:
        """
        Calculate scientifically accurate baseline RSI using Wilder's smoothing
        Reference: Chart shows RSI ~44.79 - this is the scientific standard to match
        """
        try:
            if len(candles) < periods + 1:
                return technical_constants.RSI_NEUTRAL
            
            # Extract candle closes (scientific RSI uses close prices only)
            closes = [float(candle['close']) for candle in candles]
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                price_changes.append(change)
            
            if len(price_changes) < periods:
                return technical_constants.RSI_NEUTRAL
            
            # SCIENTIFIC METHOD: Use exact Wilder's RSI calculation
            # First, get initial period using Simple Moving Average
            initial_gains = [max(0, change) for change in price_changes[:periods]]
            initial_losses = [max(0, -change) for change in price_changes[:periods]]
            
            # Calculate initial averages (SMA for first period)
            initial_avg_gain = sum(initial_gains) / periods
            initial_avg_loss = sum(initial_losses) / periods
            
            # Apply Wilder's smoothing for all remaining periods
            wilder_avg_gain = initial_avg_gain
            wilder_avg_loss = initial_avg_loss
            
            # Process each subsequent price change with Wilder's EMA
            for i in range(periods, len(price_changes)):
                change = price_changes[i]
                current_gain = max(0, change)
                current_loss = max(0, -change)
                
                # Wilder's EMA formula: EMA = α × Current + (1-α) × Previous_EMA
                # Where α = 1/periods (Wilder's smoothing constant)
                alpha = 1.0 / periods
                wilder_avg_gain = (alpha * current_gain) + ((1 - alpha) * wilder_avg_gain)
                wilder_avg_loss = (alpha * current_loss) + ((1 - alpha) * wilder_avg_loss)
            
            # Calculate final RSI using Wilder's smoothed averages
            if wilder_avg_loss == 0:
                rsi = 100.0
            else:
                rs = wilder_avg_gain / wilder_avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Initialize state for real-time updates
            self.baseline_rsi = round(rsi, 2)
            self.current_rsi = self.baseline_rsi
            self.previous_rsi = self.baseline_rsi
            self.wilder_avg_gain = wilder_avg_gain
            self.wilder_avg_loss = wilder_avg_loss
            self.last_price = 0.0  # Will be set on first real-time update (prevents discontinuity)
            
            # Store price history for continuous updates
            self.price_history.extend(closes)
            self.rsi_initialized = True
            
            logger.success(f"🔬 Scientific baseline RSI calculated: {self.baseline_rsi:.2f} (Wilder's method, ready for every-tick updates)")
            return self.baseline_rsi
            
        except Exception as e:
            logger.error(f"❌ Scientific baseline RSI calculation failed: {e}")
            return technical_constants.RSI_NEUTRAL
    
    def update_realtime_rsi(self, new_price: float) -> Dict[str, Any]:
        """
        Update RSI scientifically on EVERY price tick (as shown in reference chart)
        SCIENTIFIC METHOD: Wilder's smoothing applied to each price change
        Reference chart shows: Continuous RSI updates with smooth line graph
        """
        try:
            if not self.rsi_initialized:
                logger.warning("⚠️ RSI not initialized - use calculate_yahoo_baseline_rsi() first")
                return self._get_default_rsi_data()
            
            # Store current RSI as previous for momentum calculation
            self.previous_rsi = self.current_rsi
            
            # Add new price to history
            self.price_history.append(new_price)
            
            # Handle first real-time update (prevent Yahoo-Hyperliquid price discontinuity)
            if self.last_price == 0.0:
                # First real-time update - set current price as baseline, no RSI change
                self.last_price = new_price
                logger.debug(f"🔬 First real-time price set: ${new_price:,.2f} (no RSI update to prevent discontinuity)")
            else:
                # Regular real-time update
                price_change = new_price - self.last_price
                
                # Separate into gain and loss
                current_gain = max(0, price_change)
                current_loss = max(0, -price_change)
                
                # Apply Wilder's EMA smoothing to EVERY price tick (SCIENTIFIC METHOD)
                # Wilder's EMA formula: EMA = α × Current + (1-α) × Previous_EMA
                alpha = 1.0 / self.periods  # Wilder's smoothing constant
                self.wilder_avg_gain = (alpha * current_gain) + ((1 - alpha) * self.wilder_avg_gain)
                self.wilder_avg_loss = (alpha * current_loss) + ((1 - alpha) * self.wilder_avg_loss)
                
                # Calculate RSI using Wilder's smoothed averages
                if self.wilder_avg_loss == 0:
                    self.current_rsi = 100.0
                else:
                    rs = self.wilder_avg_gain / self.wilder_avg_loss
                    self.current_rsi = 100 - (100 / (1 + rs))
                
                self.current_rsi = round(self.current_rsi, 4)  # Higher precision for smooth updates
                
                # Update last price for next calculation
                self.last_price = new_price
            
            # Get comprehensive RSI analysis
            rsi_trend = self._get_rsi_trend(self.current_rsi)
            rsi_signal = self._get_rsi_signal(self.current_rsi)
            rsi_momentum = self._calculate_rsi_momentum()
            
            return {
                "rsi": self.current_rsi,
                "rsi_baseline": self.baseline_rsi,
                "rsi_trend": rsi_trend,
                "rsi_signal": rsi_signal,
                "rsi_momentum": rsi_momentum,
                "periods": self.periods,
                "price_used": new_price,
                "price_change": new_price - self.last_price if self.last_price > 0 else 0.0,
                "timestamp": time.time(),
                "wilder_avg_gain": round(self.wilder_avg_gain, 8),
                "wilder_avg_loss": round(self.wilder_avg_loss, 8),
                "data_source": "scientific_every_tick_wilder"
            }
            
        except Exception as e:
            logger.error(f"❌ Scientific real-time RSI update failed: {e}")
            return self._get_default_rsi_data()
    
    def _get_rsi_trend(self, rsi_value: float) -> str:
        """Determine RSI trend using constants"""
        if rsi_value >= technical_constants.RSI_OVERBOUGHT:
            return "OVERBOUGHT"
        elif rsi_value >= technical_constants.RSI_BULLISH:
            return "BULLISH" 
        elif rsi_value <= technical_constants.RSI_OVERSOLD:
            return "OVERSOLD"
        elif rsi_value <= technical_constants.RSI_BEARISH:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def _get_rsi_signal(self, rsi_value: float) -> str:
        """Determine RSI signal using constants"""
        if rsi_value >= technical_constants.RSI_OVERBOUGHT:
            return "SELL"
        elif rsi_value <= technical_constants.RSI_OVERSOLD:
            return "BUY"
        else:
            return "NEUTRAL"
    
    def _calculate_rsi_momentum(self) -> float:
        """Calculate RSI momentum (rate of RSI change)"""
        try:
            # Simple RSI momentum - compare current to baseline
            if self.baseline_rsi and self.current_rsi:
                momentum = (self.current_rsi - self.baseline_rsi) / 50.0  # Normalize to -1 to 1
                return round(momentum, 4)
            return 0.0
        except Exception as e:
            logger.warning(f"RSI momentum calculation failed: {e}")
            return 0.0
    
    def get_current_rsi_data(self) -> Dict[str, Any]:
        """Get current RSI data for trading decisions"""
        if not self.rsi_initialized:
            return self._get_default_rsi_data()
        
        return {
            "rsi": self.current_rsi,
            "rsi_baseline": self.baseline_rsi,
            "rsi_trend": self._get_rsi_trend(self.current_rsi),
            "rsi_signal": self._get_rsi_signal(self.current_rsi),
            "rsi_momentum": self._calculate_rsi_momentum(),
            "periods": self.periods,
            "initialized": self.rsi_initialized,
            "data_source": "rsi_calculator"
        }
    
    def _get_default_rsi_data(self) -> Dict[str, Any]:
        """Get default RSI data when calculation fails"""
        return {
            "rsi": technical_constants.RSI_NEUTRAL,
            "rsi_baseline": technical_constants.RSI_NEUTRAL,
            "rsi_trend": "NEUTRAL",
            "rsi_signal": "NEUTRAL", 
            "rsi_momentum": 0.0,
            "periods": self.periods,
            "initialized": False,
            "data_source": "default_fallback"
        }