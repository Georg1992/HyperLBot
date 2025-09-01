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
        # RSI calculation state
        self.periods = 14
        self.price_history = deque(maxlen=100)  # Keep last 100 prices for RSI calculation
        self.gains = deque(maxlen=self.periods)
        self.losses = deque(maxlen=self.periods)
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.current_rsi = technical_constants.RSI_NEUTRAL
        self.baseline_rsi = technical_constants.RSI_NEUTRAL
        self.rsi_initialized = False
        
        logger.info("📊 RSI Calculator initialized")
    
    def calculate_yahoo_baseline_rsi(self, candles: List[Dict], periods: int = 14) -> float:
        """
        Calculate baseline RSI from Yahoo Finance candles (initial setup)
        This provides the foundation RSI value that the user likes
        """
        try:
            if len(candles) < periods + 1:
                return technical_constants.RSI_NEUTRAL
            
            # Calculate price changes from candles
            closes = [float(candle['close']) for candle in candles[-(periods + 1):]]
            changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            
            # Separate gains and losses
            gains = [change if change > 0 else 0 for change in changes]
            losses = [-change if change < 0 else 0 for change in changes]
            
            # Calculate average gain and loss
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            # Avoid division by zero
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Initialize real-time RSI state with baseline
            self.baseline_rsi = round(rsi, 2)
            self.current_rsi = self.baseline_rsi
            self.avg_gain = avg_gain
            self.avg_loss = avg_loss
            
            # Initialize price history for real-time updates
            self.price_history.extend([float(candle['close']) for candle in candles[-periods:]])
            self.rsi_initialized = True
            
            logger.success(f"📊 Yahoo baseline RSI calculated: {self.baseline_rsi:.2f} (periods: {periods})")
            return self.baseline_rsi
            
        except Exception as e:
            logger.error(f"❌ Yahoo baseline RSI calculation failed: {e}")
            return technical_constants.RSI_NEUTRAL
    
    def update_realtime_rsi(self, new_price: float) -> Dict[str, Any]:
        """
        Update RSI in real-time using new Hyperliquid price
        Incremental RSI calculation for live trading decisions
        """
        try:
            if not self.rsi_initialized or not self.price_history:
                logger.warning("⚠️ RSI not initialized - use calculate_yahoo_baseline_rsi() first")
                return self._get_default_rsi_data()
            
            # Add new price to history
            self.price_history.append(new_price)
            
            # Calculate price change
            if len(self.price_history) >= 2:
                price_change = self.price_history[-1] - self.price_history[-2]
                
                # Determine gain/loss
                gain = price_change if price_change > 0 else 0.0
                loss = -price_change if price_change < 0 else 0.0
                
                # Update rolling averages using Wilder's smoothing
                smoothing_factor = 1.0 / self.periods
                self.avg_gain = ((self.periods - 1) * self.avg_gain + gain) / self.periods
                self.avg_loss = ((self.periods - 1) * self.avg_loss + loss) / self.periods
                
                # Calculate new RSI
                if self.avg_loss == 0:
                    self.current_rsi = 100.0
                else:
                    rs = self.avg_gain / self.avg_loss
                    self.current_rsi = 100 - (100 / (1 + rs))
                
                self.current_rsi = round(self.current_rsi, 2)
            
            # Get RSI analysis
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
                "timestamp": time.time(),
                "data_source": "realtime_hyperliquid_calculation"
            }
            
        except Exception as e:
            logger.error(f"❌ Real-time RSI update failed: {e}")
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