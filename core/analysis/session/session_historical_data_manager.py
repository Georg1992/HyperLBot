#!/usr/bin/env python3
"""
Session Historical Data Manager
Collects and analyzes session-specific data for maximum prediction precision
"""

import time
import statistics
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
from loguru import logger

class SessionHistoricalDataManager:
    """
    Manages session-specific historical data for maximum prediction precision
    - Collects real-time data during session
    - Provides session-specific technical analysis
    - Complements Yahoo historical data with session context
    """
    
    def __init__(self):
        # Session data storage
        self.session_price_history = deque(maxlen=1000)  # 1000 price points
        self.session_volume_history = deque(maxlen=1000)
        self.session_rsi_history = deque(maxlen=1000)
        self.session_volatility_history = deque(maxlen=1000)
        
        # Session metadata
        self.session_start_time = None
        self.session_start_price = None
        self.session_high = None
        self.session_low = None
        
        # Analysis cache for performance
        self._session_context_cache = None
        self._last_analysis_time = 0
        self._analysis_cache_duration = 30  # 30 seconds cache
        
        # Session state
        self.is_active = False
        
        logger.info("📊 Session Historical Data Manager initialized")
    
    def start_session(self, start_price: float):
        """Start a new session and initialize tracking"""
        self.session_start_time = time.time()
        self.session_start_price = start_price
        self.session_high = start_price
        self.session_low = start_price
        self.is_active = True
        
        # Clear previous session data
        self.session_price_history.clear()
        self.session_volume_history.clear()
        self.session_rsi_history.clear()
        self.session_volatility_history.clear()
        
        # Invalidate cache
        self._session_context_cache = None
        
        logger.info(f"🚀 Session started at ${start_price:.2f}")
    
    def add_data_point(self, price: float, volume: float, rsi: float, volatility: float):
        """Add real-time session data point"""
        if not self.is_active:
            logger.warning("⚠️ Session not active, cannot add data point")
            return
        
        timestamp = time.time()
        session_time = timestamp - self.session_start_time
        
        # Create data point
        data_point = {
            "timestamp": timestamp,
            "price": price,
            "volume": volume,
            "rsi": rsi,
            "volatility": volatility,
            "session_time": session_time,
            "session_price_change": (price - self.session_start_price) / self.session_start_price if self.session_start_price else 0
        }
        
        # Add to history
        self.session_price_history.append(data_point)
        self.session_volume_history.append(volume)
        self.session_rsi_history.append(rsi)
        self.session_volatility_history.append(volatility)
        
        # Update session extremes
        if price > self.session_high:
            self.session_high = price
        if price < self.session_low:
            self.session_low = price
        
        # Invalidate cache
        self._session_context_cache = None
    
    def get_session_context(self) -> Dict[str, Any]:
        """Get comprehensive session context for predictions"""
        current_time = time.time()
        
        # Return cached result if still valid
        if (self._session_context_cache and 
            current_time - self._last_analysis_time < self._analysis_cache_duration):
            return self._session_context_cache
        
        if len(self.session_price_history) < 10:
            return {"session_context": "insufficient_data"}
        
        # Extract data arrays
        prices = [p["price"] for p in self.session_price_history]
        volumes = [p["volume"] for p in self.session_price_history]
        rsis = [p["rsi"] for p in self.session_price_history]
        volatilities = [p["volatility"] for p in self.session_price_history]
        
        # Calculate comprehensive session analysis
        session_context = {
            # Basic session info
            "session_start_price": self.session_start_price,
            "session_current_price": prices[-1],
            "session_high": self.session_high,
            "session_low": self.session_low,
            "session_price_change": (prices[-1] - self.session_start_price) / self.session_start_price if self.session_start_price else 0,
            "session_duration": current_time - self.session_start_time,
            "data_points": len(self.session_price_history),
            
            # Technical indicators
            "session_volatility": self._calculate_session_volatility(prices),
            "session_rsi_range": {"min": min(rsis), "max": max(rsis), "current": rsis[-1]},
            "session_volume_trend": self._calculate_volume_trend(volumes),
            
            # Support and resistance
            "session_support_levels": self._find_support_levels(prices),
            "session_resistance_levels": self._find_resistance_levels(prices),
            
            # Trends
            "session_trend": self._calculate_session_trend(prices),
            "session_trend_strength": self._calculate_trend_strength(prices),
            "session_trend_confidence": self._calculate_trend_confidence(prices),
            
            # Patterns
            "session_patterns": self._detect_session_patterns(prices, rsis),
            
            # Market regime
            "session_market_regime": self._detect_session_market_regime(prices, rsis, volatilities),
            
            # Analysis metadata
            "analysis_timestamp": current_time,
            "data_source": "session_historical_data"
        }
        
        # Cache the result
        self._session_context_cache = session_context
        self._last_analysis_time = current_time
        
        return session_context
    
    def _calculate_session_volatility(self, prices: List[float]) -> float:
        """Calculate session volatility"""
        if len(prices) < 2:
            return 0.0
        
        # Calculate percentage changes
        changes = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                change = abs(prices[i] - prices[i-1]) / prices[i-1]
                changes.append(change)
        
        if not changes:
            return 0.0
        
        # Use standard deviation of percentage changes
        return statistics.stdev(changes)
    
    def _calculate_volume_trend(self, volumes: List[float]) -> str:
        """Calculate volume trend"""
        if len(volumes) < 10:
            return "UNKNOWN"
        
        # Calculate volume moving average
        recent_volumes = volumes[-10:]
        avg_volume = statistics.mean(recent_volumes)
        current_volume = volumes[-1]
        
        if current_volume > avg_volume * 1.2:
            return "INCREASING"
        elif current_volume < avg_volume * 0.8:
            return "DECREASING"
        else:
            return "STABLE"
    
    def _find_support_levels(self, prices: List[float]) -> List[float]:
        """Find support levels from session price history"""
        if len(prices) < 10:
            return []
        
        supports = []
        for i in range(1, len(prices) - 1):
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                supports.append(prices[i])
        
        # Return most recent support levels, sorted by price
        return sorted(supports, reverse=True)[:3]
    
    def _find_resistance_levels(self, prices: List[float]) -> List[float]:
        """Find resistance levels from session price history"""
        if len(prices) < 10:
            return []
        
        resistances = []
        for i in range(1, len(prices) - 1):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                resistances.append(prices[i])
        
        # Return most recent resistance levels, sorted by price
        return sorted(resistances)[:3]
    
    def _calculate_session_trend(self, prices: List[float]) -> str:
        """Calculate session trend"""
        if len(prices) < 10:
            return "UNKNOWN"
        
        # Calculate overall session trend
        session_start = prices[0]
        session_current = prices[-1]
        session_change = (session_current - session_start) / session_start
        
        # Calculate recent momentum (last 10 prices)
        recent_prices = prices[-10:]
        recent_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        # Determine trend based on session change and recent momentum
        if session_change > 0.01 and recent_trend > 0.005:
            return "STRONG_UPTREND"
        elif session_change > 0.005:
            return "UPTREND"
        elif session_change < -0.01 and recent_trend < -0.005:
            return "STRONG_DOWNTREND"
        elif session_change < -0.005:
            return "DOWNTREND"
        else:
            return "SIDEWAYS"
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """Calculate trend strength (0.0 to 1.0)"""
        if len(prices) < 10:
            return 0.0
        
        # Calculate linear regression slope
        x = list(range(len(prices)))
        y = prices
        
        # Simple linear regression
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        if n * sum_x2 - sum_x ** 2 == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # Normalize slope to 0-1 range
        max_slope = max(prices) * 0.01  # 1% of max price as max slope
        strength = min(abs(slope) / max_slope, 1.0) if max_slope > 0 else 0.0
        
        return strength
    
    def _calculate_trend_confidence(self, prices: List[float]) -> float:
        """Calculate trend confidence based on consistency"""
        if len(prices) < 10:
            return 0.0
        
        # Calculate how consistent the trend is
        changes = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                change = (prices[i] - prices[i-1]) / prices[i-1]
                changes.append(change)
        
        if not changes:
            return 0.0
        
        # Count consistent moves in the same direction
        positive_moves = sum(1 for c in changes if c > 0)
        negative_moves = sum(1 for c in changes if c < 0)
        
        total_moves = len(changes)
        consistency = max(positive_moves, negative_moves) / total_moves
        
        return consistency
    
    def _detect_session_patterns(self, prices: List[float], rsis: List[float]) -> Dict[str, Any]:
        """Detect session-specific patterns"""
        if len(prices) < 20:
            return {"patterns": "insufficient_data"}
        
        patterns = {
            "price_moves": [],
            "rsi_patterns": [],
            "volatility_spikes": []
        }
        
        # Detect recent price moves
        recent_prices = prices[-5:]
        for i in range(1, len(recent_prices)):
            change = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            patterns["price_moves"].append(change)
        
        # Detect RSI patterns
        recent_rsis = rsis[-5:]
        for i in range(1, len(recent_rsis)):
            rsi_change = recent_rsis[i] - recent_rsis[i-1]
            patterns["rsi_patterns"].append(rsi_change)
        
        return patterns
    
    def _detect_session_market_regime(self, prices: List[float], rsis: List[float], volatilities: List[float]) -> str:
        """Detect session market regime"""
        if len(prices) < 10:
            return "UNKNOWN"
        
        current_volatility = volatilities[-1] if volatilities else 0
        current_rsi = rsis[-1] if rsis else 50
        
        # Determine market regime
        if current_volatility > 0.03:  # > 3% volatility
            return "VOLATILE"
        elif current_rsi > 70:
            return "OVERBOUGHT"
        elif current_rsi < 30:
            return "OVERSOLD"
        elif 45 < current_rsi < 55:
            return "RANGING"
        else:
            return "TRENDING"
    
    def end_session(self):
        """End the current session"""
        self.is_active = False
        logger.info("🛑 Session ended")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary for analysis"""
        if not self.session_price_history:
            return {"error": "No session data available"}
        
        context = self.get_session_context()
        
        return {
            "session_duration": context.get("session_duration", 0),
            "total_data_points": context.get("data_points", 0),
            "price_change": context.get("session_price_change", 0),
            "session_high": context.get("session_high", 0),
            "session_low": context.get("session_low", 0),
            "session_trend": context.get("session_trend", "UNKNOWN"),
            "session_volatility": context.get("session_volatility", 0),
            "session_market_regime": context.get("session_market_regime", "UNKNOWN")
        }
