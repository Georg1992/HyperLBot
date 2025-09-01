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
            
            # Initial period: Simple Moving Average (SMA) for first calculation
            initial_gains = [change if change > 0 else 0 for change in price_changes[:periods]]
            initial_losses = [-change if change < 0 else 0 for change in price_changes[:periods]]
            
            initial_avg_gain = sum(initial_gains) / periods if initial_gains else 0
            initial_avg_loss = sum(initial_losses) / periods if initial_losses else 0
            
            # Apply Wilder's smoothing for remaining periods (SCIENTIFIC METHOD)
            wilder_avg_gain = initial_avg_gain
            wilder_avg_loss = initial_avg_loss
            
            # Process remaining price changes with Wilder's smoothing
            for i in range(periods, len(price_changes)):
                change = price_changes[i]
                gain = change if change > 0 else 0
                loss = -change if change < 0 else 0
                
                # Wilder's smoothing formula (scientifically accurate)
                wilder_avg_gain = ((wilder_avg_gain * (periods - 1)) + gain) / periods
                wilder_avg_loss = ((wilder_avg_loss * (periods - 1)) + loss) / periods
            
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
            self.last_price = closes[-1]  # Store last price for incremental updates
            
            # Store price history for continuous updates
            self.price_history.extend(closes)
            self.rsi_initialized = True
            
            logger.success(f"🔬 Scientific baseline RSI calculated: {self.baseline_rsi:.2f} (Wilder's method, ready for every-tick updates)")
            return self.baseline_rsi
            
        except Exception as e:
            logger.error(f"❌ Scientific baseline RSI calculation failed: {e}")
            return technical_constants.RSI_NEUTRAL
    
    def update_realtime_rsi_on_candle_close(self, new_candle_close: float, candle_timestamp: float) -> Dict[str, Any]:
        """
        Update RSI scientifically on 5-minute candle close (NOT on price ticks)
        SCIENTIFIC METHOD: Only update RSI when a complete 5-minute candle closes
        Reference: Chart RSI ~44.79 - this method should produce similar accuracy
        """
        try:
            if not self.rsi_initialized:
                logger.warning("⚠️ RSI not initialized - use calculate_yahoo_baseline_rsi() first")
                return self._get_default_rsi_data()
            
            # Only update on new candle (prevent multiple updates for same candle)
            current_candle_time = int(candle_timestamp / 300) * 300  # Round to 5-minute boundary
            if current_candle_time <= self.last_candle_time:
                # Same candle - return current RSI without updating
                return self.get_current_rsi_data()
            
            self.last_candle_time = current_candle_time
            
            # Add new candle close to history
            self.candle_closes.append(new_candle_close)
            
            # Calculate price change from previous candle close
            if len(self.candle_closes) >= 2:
                price_change = self.candle_closes[-1] - self.candle_closes[-2]
                
                # Separate into gain and loss
                gain = price_change if price_change > 0 else 0.0
                loss = -price_change if price_change < 0 else 0.0
                
                # Apply Wilder's smoothing (SCIENTIFIC METHOD)
                # Wilder's formula: New_EMA = ((periods-1) × Previous_EMA + Current_Value) / periods
                self.wilder_avg_gain = ((self.wilder_avg_gain * (self.periods - 1)) + gain) / self.periods
                self.wilder_avg_loss = ((self.wilder_avg_loss * (self.periods - 1)) + loss) / self.periods
                
                # Calculate RSI using Wilder's smoothed averages
                if self.wilder_avg_loss == 0:
                    self.current_rsi = 100.0
                else:
                    rs = self.wilder_avg_gain / self.wilder_avg_loss
                    self.current_rsi = 100 - (100 / (1 + rs))
                
                self.current_rsi = round(self.current_rsi, 2)
                
                logger.debug(f"🔬 Scientific RSI updated: {self.current_rsi:.2f} (baseline: {self.baseline_rsi:.2f})")
            
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
                "candle_close_used": new_candle_close,
                "candle_timestamp": candle_timestamp,
                "timestamp": time.time(),
                "wilder_avg_gain": round(self.wilder_avg_gain, 6),
                "wilder_avg_loss": round(self.wilder_avg_loss, 6),
                "data_source": "scientific_wilder_smoothing"
            }
            
        except Exception as e:
            logger.error(f"❌ Scientific real-time RSI update failed: {e}")
            return self._get_default_rsi_data()
    
    def update_realtime_rsi(self, new_price: float) -> Dict[str, Any]:
        """
        DEPRECATED: Use update_realtime_rsi_on_candle_close() for scientific accuracy
        This method is kept for backward compatibility but should not be used
        """
        logger.warning("⚠️ update_realtime_rsi() is deprecated - use update_realtime_rsi_on_candle_close() for scientific accuracy")
        return self.get_current_rsi_data()
    
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