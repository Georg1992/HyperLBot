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
        
        # Track last price for incremental updates
        self.last_price = None
        
        # RSI smoothing to reduce noise
        self.rsi_smoothing_factor = 0.2  # Lower = more smoothing
        self.smoothed_rsi = None
        self.min_price_change_threshold = 10.0  # Minimum $10 change to update RSI
        
        logger.info(f"📊 Real-time RSI Calculator initialized (periods: {periods})")
    
    def add_price(self, price: float, timestamp: float = None) -> None:
        """Add a new price to the calculation window - incremental RSI update"""
        if timestamp is None:
            timestamp = time.time()
        
        # PREVENT DUPLICATE PRICE UPDATES - major cause of RSI fluctuations
        if self.last_price is not None and abs(price - self.last_price) < 0.01:
            logger.debug(f"📊 Skipping duplicate price update: {price} (same as last: {self.last_price})")
            return
        
        # Calculate RSI incrementally if we have a previous price
        if self.last_price is not None and self.is_initialized:
            price_change = price - self.last_price
            
            # Skip tiny price changes that add noise
            if abs(price_change) < self.min_price_change_threshold:
                logger.debug(f"📊 Skipping tiny price change: {price_change:+.2f} (threshold: {self.min_price_change_threshold})")
                # Still update last_price but don't recalculate RSI
                self.last_price = price
                return
            
            # Calculate gain/loss from this single price change
            gain = price_change if price_change > 0 else 0.0
            loss = -price_change if price_change < 0 else 0.0
            
            # Update Wilder's smoothed averages with just this new gain/loss
            self.avg_gain = (self.avg_gain * (self.periods - 1) + gain) / self.periods
            self.avg_loss = (self.avg_loss * (self.periods - 1) + loss) / self.periods
            
            # Calculate new RSI immediately
            if self.avg_loss == 0:
                new_rsi = 100.0
            else:
                rs = self.avg_gain / self.avg_loss
                new_rsi = 100.0 - (100.0 / (1.0 + rs))
            
            # Apply exponential smoothing to reduce noise
            if self.smoothed_rsi is None:
                self.smoothed_rsi = new_rsi
            else:
                self.smoothed_rsi = (self.rsi_smoothing_factor * new_rsi + 
                                   (1 - self.rsi_smoothing_factor) * self.smoothed_rsi)
            
            # Cache the smoothed result
            self.cached_rsi = round(self.smoothed_rsi, 2)
            self.cached_trend, self.cached_signal = self._get_rsi_trend_signal(self.smoothed_rsi)
            
            logger.debug(f"📊 RSI updated: {price} → Raw RSI {new_rsi:.2f} → Smoothed RSI {self.cached_rsi:.2f} (change: {price_change:+.2f})")
        
        # Store the price and update last_price
        self.price_history.append({
            'price': price,
            'timestamp': timestamp
        })
        self.last_price = price
    
    def calculate_rsi(self) -> Dict[str, Any]:
        """Calculate RSI - uses incremental updates when possible, full calculation for initialization"""
        
        # Check if we have enough data
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
            # If not initialized, do full calculation for setup
            if not self.is_initialized:
                return self._initialize_rsi()
            
            # If already initialized, return cached incremental result
            if self.cached_rsi is not None:
                return {
                    "rsi": self.cached_rsi,
                    "trend": self.cached_trend,
                    "signal": self.cached_signal,
                    "avg_gain": self.avg_gain,
                    "avg_loss": self.avg_loss,
                    "rs": self.avg_gain / self.avg_loss if self.avg_loss > 0 else None,
                    "data_points": len(self.price_history),
                    "periods_used": self.periods,
                    "latest_price": self.last_price,
                    "calculation_timestamp": time.time(),
                    "calculation_method": "incremental_update"
                }
            
            # Fallback: force initialization if somehow we get here
            return self._initialize_rsi()
            
        except Exception as e:
            logger.error(f"❌ Real-time RSI calculation failed: {e}")
            return {
                "rsi": None,
                "trend": "NEUTRAL",
                "signal": "NEUTRAL",
                "error": str(e),
                "data_points": len(self.price_history)
            }
    
    def _initialize_rsi(self) -> Dict[str, Any]:
        """Initialize RSI with full calculation from historical data"""
        try:
            # Get enough prices for initialization
            prices = [p['price'] for p in list(self.price_history)[-self.periods-1:]]
            
            # Calculate all initial price changes
            changes = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                changes.append(change)
            
            if len(changes) < self.periods:
                return {
                    "rsi": None,
                    "trend": "NEUTRAL", 
                    "signal": "NEUTRAL",
                    "error": "insufficient_changes_for_init",
                    "data_points": len(changes),
                    "periods_required": self.periods
                }
            
            # Calculate initial gains and losses
            gains = [change if change > 0 else 0.0 for change in changes[-self.periods:]]
            losses = [-change if change < 0 else 0.0 for change in changes[-self.periods:]]
            
            # Initialize Wilder's smoothed averages
            self.avg_gain = sum(gains) / self.periods
            self.avg_loss = sum(losses) / self.periods
            self.is_initialized = True
            
            # Set last price for future incremental updates
            self.last_price = prices[-1]
            
            # Calculate initial RSI
            if self.avg_loss == 0:
                rsi = 100.0
            else:
                rs = self.avg_gain / self.avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            
            # Cache results
            self.cached_rsi = round(rsi, 2)
            self.cached_trend, self.cached_signal = self._get_rsi_trend_signal(rsi)
            self.last_calculation = time.time()
            
            logger.info(f"📊 RSI initialized: {self.cached_rsi:.2f} from {len(changes)} price changes")
            
            return {
                "rsi": self.cached_rsi,
                "trend": self.cached_trend,
                "signal": self.cached_signal,
                "avg_gain": self.avg_gain,
                "avg_loss": self.avg_loss,
                "rs": rs if self.avg_loss > 0 else None,
                "data_points": len(self.price_history),
                "periods_used": self.periods,
                "latest_price": self.last_price,
                "calculation_timestamp": self.last_calculation,
                "calculation_method": "initialization"
            }
            
        except Exception as e:
            logger.error(f"❌ RSI initialization failed: {e}")
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
            candles = yahoo_fetcher.get_5m_klines("BTC", 576)  # 48 hours of data (576 * 5min = 2880min = 48h)
            
            if candles and len(candles) >= self.periods + 1:
                # Extract closing prices
                prices = [candle['close'] for candle in candles]
                
                # Clear existing data
                self.price_history.clear()
                self.is_initialized = False
                self.avg_gain = None
                self.avg_loss = None
                self.last_price = None
                self.cached_rsi = None
                
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
    
    def _get_rsi_trend_signal(self, rsi: float) -> tuple:
        """Get RSI trend and signal based on value"""
        if rsi >= 70:
            return "OVERBOUGHT", "SELL"
        elif rsi <= 30:
            return "OVERSOLD", "BUY"
        elif rsi >= 60:
            return "STRONG", "NEUTRAL"
        elif rsi <= 40:
            return "WEAK", "NEUTRAL"
        else:
            return "NEUTRAL", "NEUTRAL"

# Global instance for real-time RSI calculation
real_time_rsi_calculator = RealTimeRSICalculator()
