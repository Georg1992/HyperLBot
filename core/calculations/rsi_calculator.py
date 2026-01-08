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
    
    
    def calculate_hyperliquid_baseline_rsi(self, candles: List[Dict], periods: int = 14) -> float:
        """
        Calculate baseline RSI 14 from completed candles using WILDER'S SMOOTHING
        This is the STANDARD RSI calculation method used by TradingView and Hyperliquid
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
            
            # WILDER'S SMOOTHING RSI CALCULATION
            # Step 1: Calculate initial average gain and loss (simple average for first period)
            initial_changes = price_changes[:periods]
            initial_gains = [max(0, change) for change in initial_changes]
            initial_losses = [max(0, -change) for change in initial_changes]
            
            # Initial averages (simple average for first calculation)
            avg_gain = sum(initial_gains) / periods
            avg_loss = sum(initial_losses) / periods
            
            # Step 2: Apply Wilder's smoothing to remaining price changes
            # Formula: New_Avg = [(Previous_Avg × (n-1)) + Current_Value] / n
            for i in range(periods, len(price_changes)):
                current_change = price_changes[i]
                current_gain = max(0, current_change)
                current_loss = max(0, -current_change)
                
                # Wilder's smoothing formula
                avg_gain = ((avg_gain * (periods - 1)) + current_gain) / periods
                avg_loss = ((avg_loss * (periods - 1)) + current_loss) / periods
            
            # Calculate RSI using Wilder's smoothed averages
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Store baseline for real-time updates
            self.baseline_rsi = round(rsi, 2)
            self.current_rsi = self.baseline_rsi
            self.wilder_avg_gain = avg_gain  # Store Wilder's smoothed values
            self.wilder_avg_loss = avg_loss  # Store Wilder's smoothed values
            self.rsi_initialized = True
            
            # Store price history for real-time updates
            self.price_history.extend(closes)
            
            logger.debug(f"🔬 Baseline RSI 14: {self.baseline_rsi:.2f} (Wilder's smoothing method)")
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
                
                # RSI sensitivity: Balanced reactivity to price changes for real-time updates
                # 1% price move ≈ 23 RSI points (moderate sensitivity - less fluctuation)
                rsi_sensitivity = 23.0  # Moderate sensitivity to reduce excessive fluctuation
                
                # Calculate RSI adjustment based on price movement
                rsi_adjustment = price_change_pct * 100 * rsi_sensitivity
                
                # Apply adjustment to baseline (smoother reaction to reduce fluctuation)
                dampening = 0.80  # 80% of calculated adjustment (smoother, less immediate reaction)
                self.current_rsi = self.baseline_rsi + (rsi_adjustment * dampening)
                
                # Keep RSI in valid range [0, 100]
                self.current_rsi = max(0.0, min(100.0, self.current_rsi))
                
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
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        """
        Get latest RSI analysis for MarketDataService coordination
        
        Returns:
            Dict with current RSI analysis
        """
        try:
            if not self.rsi_initialized:
                return {
                    "rsi": None,
                    "rsi_trend": "UNKNOWN",
                    "rsi_signal": "NEUTRAL",
                    "rsi_momentum": 0.0,
                    "baseline_rsi": self.baseline_rsi,
                    "initialized": False,
                    "error": "RSI not initialized"
                }
            
            return {
                "rsi": self.current_rsi,
                "rsi_trend": self._get_rsi_trend(self.current_rsi),
                "rsi_signal": self._get_rsi_signal(self.current_rsi),
                "rsi_momentum": self._calculate_rsi_momentum(),
                "baseline_rsi": self.baseline_rsi,
                "initialized": True,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest RSI analysis: {e}")
            return {
                "rsi": None,
                "rsi_trend": "ERROR",
                "rsi_signal": "ERROR",
                "rsi_momentum": 0.0,
                "baseline_rsi": self.baseline_rsi,
                "initialized": False,
                "error": str(e)
            }


# Singleton pattern implementation
_global_rsi_calculator = None

# Factory function for dependency injection
def create_rsi_calculator() -> RSICalculator:
    """
    Factory function to create RSICalculator with dependency injection
    
    Returns:
        Configured RSICalculator instance
    """
    return RSICalculator()

# Deprecated singleton functions removed - use create_rsi_calculator() instead

