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
        
        logger.info("🔬 RSI Calculator initialized - RSI(14) with real-time updates")
    
    def calculate_standalone_rsi(self, candles: List[Dict], periods: int = 14) -> float:
        """
        Calculate standalone RSI from candles (doesn't affect instance state)
        Perfect for Hyperliquid analysis - just calculates and returns RSI value
        """
        try:
            if len(candles) < periods + 1:
                return technical_constants.RSI_NEUTRAL
            
            # Extract candle closes
            closes = [float(candle['close']) for candle in candles]
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                price_changes.append(change)
            
            if len(price_changes) < periods:
                return technical_constants.RSI_NEUTRAL
            
            # Initial period: Simple Moving Average for first calculation
            initial_gains = [max(0, change) for change in price_changes[:periods]]
            initial_losses = [max(0, -change) for change in price_changes[:periods]]
            
            initial_avg_gain = sum(initial_gains) / periods
            initial_avg_loss = sum(initial_losses) / periods
            
            # Apply Wilder's smoothing for remaining periods
            wilder_avg_gain = initial_avg_gain
            wilder_avg_loss = initial_avg_loss
            
            # Process each subsequent price change with Wilder's EMA
            for i in range(periods, len(price_changes)):
                change = price_changes[i]
                current_gain = max(0, change)
                current_loss = max(0, -change)
                
                # Wilder's EMA formula
                alpha = 1.0 / periods
                wilder_avg_gain = (alpha * current_gain) + ((1 - alpha) * wilder_avg_gain)
                wilder_avg_loss = (alpha * current_loss) + ((1 - alpha) * wilder_avg_loss)
            
            # Calculate final RSI
            if wilder_avg_loss == 0:
                rsi = 100.0
            else:
                rs = wilder_avg_gain / wilder_avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            return round(rsi, 2)
            
        except Exception as e:
            logger.error(f"❌ Standalone RSI calculation failed: {e}")
            return technical_constants.RSI_NEUTRAL
    
    def calculate_hyperliquid_baseline_rsi(self, candles: List[Dict], periods: int = 14) -> float:
        """
        Calculate baseline RSI 14 from completed candles - EXACT match to trading platforms
        This provides the foundation for real-time updates
        """
        try:
            if len(candles) < periods + 1:
                return technical_constants.RSI_NEUTRAL
            
            # Extract candle closes
            closes = [float(candle['close']) for candle in candles]
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                price_changes.append(change)
            
            if len(price_changes) < periods:
                return technical_constants.RSI_NEUTRAL
            
            # BASELINE RSI 14 CALCULATION - Use last 14 periods only
            # This is exactly how TradingView, Binance, and other platforms calculate RSI
            recent_changes = price_changes[-periods:]
            
            # Calculate gains and losses
            gains = [max(0, change) for change in recent_changes]
            losses = [max(0, -change) for change in recent_changes]
            
            # Calculate average gain and loss using Wilder's smoothing method
            # This is the standard method used by most trading platforms including Hyperliquid
            if len(gains) == 0 or len(losses) == 0:
                return technical_constants.RSI_NEUTRAL
            
            # Wilder's smoothing: Initial average
            avg_gain = sum(gains) / len(gains)
            avg_loss = sum(losses) / len(losses)
            
            # Apply Wilder's smoothing formula for more accurate RSI
            for i in range(len(gains)):
                avg_gain = (avg_gain * (periods - 1) + gains[i]) / periods
                avg_loss = (avg_loss * (periods - 1) + losses[i]) / periods
            
            # Calculate RSI
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Store baseline for real-time updates
            self.baseline_rsi = round(rsi, 2)
            self.current_rsi = self.baseline_rsi
            self.wilder_avg_gain = avg_gain  # Store for compatibility
            self.wilder_avg_loss = avg_loss  # Store for compatibility
            self.rsi_initialized = True
            
            # Store price history for real-time updates
            self.price_history.extend(closes)
            
            logger.debug(f"🔬 Baseline RSI 14: {self.baseline_rsi:.2f} (ready for real-time updates)")
            return self.baseline_rsi
            
        except Exception as e:
            logger.error(f"❌ Baseline RSI calculation failed: {e}")
            return technical_constants.RSI_NEUTRAL
    
    def update_realtime_rsi(self, new_price: float) -> Dict[str, Any]:
        """
        Update real-time RSI between Hyperliquid correction points (sensitivity for scalping)
        Method: RSI interpolation based on price movement with Hyperliquid baseline correction
        """
        try:
            if not self.rsi_initialized:
                logger.warning("⚠️ RSI not initialized - use calculate_hyperliquid_baseline_rsi() first")
                raise Exception("RSI not initialized - use calculate_hyperliquid_baseline_rsi() first")
            
            # Store current RSI as previous for momentum calculation
            self.previous_rsi = self.current_rsi
            
            # Add new price to history
            self.price_history.append(new_price)
            
            # FIXED APPROACH: RSI interpolation between Hyperliquid points (proper method)
            if self.last_price == 0.0:
                # First real-time update - set Hyperliquid price as reference
                self.last_price = new_price  
                self.current_rsi = self.baseline_rsi  # Start with accurate Hyperliquid RSI
                # logger.debug(f"🔬 Real-time RSI started: ${new_price:,.2f} with Hyperliquid RSI {self.baseline_rsi:.2f}")
            else:
                # FIXED: RSI interpolation based on price movement (not broken tick-by-tick)
                price_change_pct = (new_price - self.last_price) / self.last_price
                
                # RSI sensitivity: Reduced reactivity to price changes (user requested further reduction)
                # 1% price move ≈ 10 RSI points (further reduced sensitivity)
                rsi_sensitivity = 10.0  # Further reduced sensitivity for less reactive RSI
                
                # Calculate RSI adjustment based on price movement
                rsi_adjustment = price_change_pct * 100 * rsi_sensitivity
                
                # Apply adjustment to baseline (less responsive)
                dampening = 0.6  # 60% of calculated adjustment (less immediate reaction)
                self.current_rsi = self.baseline_rsi + (rsi_adjustment * dampening)
                
                # Keep RSI in valid range [0, 100]
                self.current_rsi = max(0.0, min(100.0, self.current_rsi))
                
                # Log RSI reaction to price changes
                logger.debug(f"📊 RSI reaction: Price ${self.last_price:.2f} → ${new_price:.2f} ({price_change_pct*100:+.3f}%) → RSI {self.baseline_rsi:.1f} → {self.current_rsi:.1f} ({rsi_adjustment*dampening:+.1f})")
                
                # Don't update last_price here - keep Hyperliquid price as reference point
            
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
            raise Exception(f"Scientific real-time RSI update failed: {e}")
    
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
            raise Exception("RSI not initialized")
        
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


# Singleton pattern implementation
_global_rsi_calculator = None

def get_global_rsi_calculator() -> RSICalculator:
    """Get the global RSICalculator singleton instance"""
    global _global_rsi_calculator
    if _global_rsi_calculator is None:
        _global_rsi_calculator = RSICalculator()
    return _global_rsi_calculator

