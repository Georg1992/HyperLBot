#!/usr/bin/env python3
"""
Real-Time RSI Calculator
Calculates RSI using real-time Hyperliquid price data with proper Wilder's smoothing
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger
from collections import deque

class RealTimeRSICalculator:
    """Real-time RSI calculator using Hyperliquid price data with proper Wilder's smoothing"""
    
    def __init__(self, periods: int = 14, max_prices: int = 100):
        self.periods = periods
        self.max_prices = max_prices
        self.price_history = deque(maxlen=max_prices)
        self.last_calculation = 0
        self.cached_rsi = None
        self.cached_trend = "NEUTRAL"
        self.cached_signal = "NEUTRAL"
        
        # Wilder's smoothing variables
        self.avg_gain = None
        self.avg_loss = None
        self.is_initialized = False
        
        logger.info(f"📊 Real-time RSI Calculator initialized (periods: {periods})")
    
    def add_price(self, price: float, timestamp: float = None) -> None:
        """Add a new price to the calculation window - NO THROTTLING for real-time updates"""
        if timestamp is None:
            timestamp = time.time()
        
        self.price_history.append({
            'price': price,
            'timestamp': timestamp
        })
        
        # Clear cache to force recalculation
        self.cached_rsi = None
    
    def calculate_rsi(self) -> Dict[str, Any]:
        """Calculate RSI using proper Wilder's smoothing"""
        if len(self.price_history) < self.periods + 1:
            return {
                "rsi": None,
                "trend": "NEUTRAL",
                "signal": "NEUTRAL",
                "error": "insufficient_data",
                "data_points": len(self.price_history),
                "periods_required": self.periods + 1
            }
        
        try:
            # Get recent prices
            prices = [p['price'] for p in list(self.price_history)[-self.periods-1:]]
            
            # Calculate price changes
            changes = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                changes.append(change)
            
            if len(changes) < self.periods:
                return {
                    "rsi": None,
                    "trend": "NEUTRAL",
                    "signal": "NEUTRAL",
                    "error": "insufficient_changes",
                    "data_points": len(changes),
                    "periods_required": self.periods
                }
            
            # Calculate gains and losses
            gains = [change if change > 0 else 0 for change in changes]
            losses = [-change if change < 0 else 0 for change in changes]
            
            # Use proper Wilder's smoothing
            if not self.is_initialized:
                # First calculation: use simple average
                self.avg_gain = sum(gains[-self.periods:]) / self.periods
                self.avg_loss = sum(losses[-self.periods:]) / self.periods
                self.is_initialized = True
            else:
                # Subsequent calculations: use Wilder's smoothing
                # New Avg Gain = (Previous Avg Gain × 13 + Current Gain) ÷ 14
                # New Avg Loss = (Previous Avg Loss × 13 + Current Loss) ÷ 14
                current_gain = gains[-1] if gains else 0
                current_loss = losses[-1] if losses else 0
                
                self.avg_gain = (self.avg_gain * (self.periods - 1) + current_gain) / self.periods
                self.avg_loss = (self.avg_loss * (self.periods - 1) + current_loss) / self.periods
            
            # Calculate RS and RSI
            if self.avg_loss == 0:
                rsi = 100.0
            else:
                rs = self.avg_gain / self.avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Determine trend and signal
            if rsi > 70:
                trend = "OVERBOUGHT"
                signal = "SELL"
            elif rsi < 30:
                trend = "OVERSOLD"
                signal = "BUY"
            else:
                trend = "NEUTRAL"
                signal = "NEUTRAL"
            
            result = {
                "rsi": round(rsi, 2),
                "trend": trend,
                "signal": signal,
                "avg_gain": self.avg_gain,
                "avg_loss": self.avg_loss,
                "rs": rs if self.avg_loss > 0 else None,
                "data_points": len(self.price_history),
                "periods_used": self.periods,
                "latest_price": prices[-1] if prices else None,
                "price_change": changes[-1] if changes else None,
                "calculation_timestamp": time.time()
            }
            
            # Cache the result
            self.cached_rsi = result["rsi"]
            self.cached_trend = result["trend"]
            self.cached_signal = result["signal"]
            self.last_calculation = time.time()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Real-time RSI calculation failed: {e}")
            return {
                "rsi": None,
                "trend": "NEUTRAL",
                "signal": "NEUTRAL",
                "error": str(e),
                "data_points": len(self.price_history)
            }
    
    def initialize_with_yahoo_data(self) -> None:
        """Initialize RSI calculator with Yahoo Finance data for starting values"""
        try:
            from data.yahoo_data_fetcher import YahooDataFetcher
            
            # Get Yahoo Finance data for initialization
            yahoo_fetcher = YahooDataFetcher()
            candles = yahoo_fetcher.get_5m_klines("BTC", 72)  # 6 hours of data (72 * 5min = 360min = 6h)
            
            if candles and len(candles) >= self.periods + 1:
                # Extract closing prices
                prices = [candle['close'] for candle in candles]
                
                # Clear existing data
                self.price_history.clear()
                self.is_initialized = False
                self.avg_gain = None
                self.avg_loss = None
                
                # Add historical prices to initialize the calculator
                for i, price in enumerate(prices):
                    timestamp = time.time() - (len(prices) - i) * 300  # 5-minute intervals
                    self.price_history.append({
                        'price': price,
                        'timestamp': timestamp
                    })
                
                # Calculate initial RSI to set up Wilder's smoothing
                initial_rsi = self.calculate_rsi()
                logger.info(f"📊 Initialized RSI calculator with Yahoo data: RSI {initial_rsi.get('rsi', 'N/A')}")
                
            else:
                logger.warning("⚠️ Insufficient Yahoo data for RSI initialization")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize with Yahoo data: {e}")
    
    def get_cached_rsi(self) -> Optional[float]:
        """Get the cached RSI value"""
        return self.cached_rsi
    
    def get_status(self) -> Dict[str, Any]:
        """Get calculator status"""
        return {
            "price_history_length": len(self.price_history),
            "periods_required": self.periods + 1,
            "has_sufficient_data": len(self.price_history) >= self.periods + 1,
            "is_initialized": self.is_initialized,
            "last_calculation": self.last_calculation,
            "cached_rsi": self.cached_rsi,
            "cached_trend": self.cached_trend,
            "cached_signal": self.cached_signal,
            "avg_gain": self.avg_gain,
            "avg_loss": self.avg_loss
        }

# Global instance for real-time RSI calculation
real_time_rsi_calculator = RealTimeRSICalculator()
