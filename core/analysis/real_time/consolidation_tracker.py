#!/usr/bin/env python3
"""
Consolidation Tracker
Detects and tracks price consolidation periods (sideways movement in ranges)

Features:
- Detects consolidation ranges (support/resistance boundaries)
- Tracks consolidation duration
- Measures range tightness (coiling)
- Detects consolidation breakouts
- Predicts breakout direction based on volume, pressure, momentum
- Integrates with reactive engine for breakout trades
"""

import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from loguru import logger
from core.constants import TechnicalAnalysisConstants


@dataclass
class ConsolidationRange:
    """Consolidation range data"""
    upper_bound: float  # Resistance level
    lower_bound: float  # Support level
    range_width_pct: float  # Range width as percentage
    started_at: float  # Timestamp when consolidation started
    duration_minutes: float  # How long consolidation has lasted
    touch_count_upper: int  # Number of touches on upper bound
    touch_count_lower: int  # Number of touches on lower bound
    avg_volume: float  # Average volume during consolidation
    volatility: float  # Volatility during consolidation
    coiling_score: float  # 0-100, higher = tighter range (coiling)
    breakout_probability: float  # 0-100, probability of breakout
    expected_direction: Optional[str] = None  # "LONG" or "SHORT" if breakout likely


@dataclass
class ConsolidationBreakout:
    """Consolidation breakout signal"""
    direction: str  # "LONG" or "SHORT"
    confidence: float  # 0.0-100.0
    entry_price: float  # Current price (market order)
    stop_loss: float
    take_profit: float
    range_upper: float  # Original range upper bound
    range_lower: float  # Original range lower bound
    range_width: float  # Range width
    duration_minutes: float  # How long consolidation lasted
    reasoning: List[str]
    detected_at: float


class ConsolidationTracker:
    """
    Tracks price consolidation periods and detects breakouts
    
    Consolidation Detection:
    - Price moving sideways between support and resistance
    - Low volatility (price contained in range)
    - Multiple touches on range boundaries
    - Decreasing range width (coiling) = higher breakout probability
    
    Breakout Detection:
    - Price breaks above upper bound (LONG) or below lower bound (SHORT)
    - Volume surge confirms breakout
    - Orderbook pressure in breakout direction
    - Momentum acceleration
    """
    
    def __init__(self, symbol: str = "BTC"):
        self.symbol = symbol
        self._current_consolidation: Optional[ConsolidationRange] = None
        self._recent_breakouts: List[ConsolidationBreakout] = []
        self._price_history: List[Tuple[float, float]] = []  # (price, timestamp)
        self._max_history = 100  # Keep last 100 price points
        self._min_consolidation_duration = 15  # Minimum 15 minutes to be considered consolidation
        self._max_range_width_pct = 0.02  # 2% max range width for consolidation
        self._min_range_width_pct = 0.001  # 0.1% min range width
        self._historical_analyzed = False  # Track if we've analyzed historical data
        
        logger.info("📊 Consolidation Tracker initialized")
    
    def detect_consolidation(
        self,
        unified_data: Dict[str, Any],
        current_price: float,
        current_time: float
    ) -> Optional[ConsolidationRange]:
        """
        Detect if price is currently in consolidation
        
        Args:
            unified_data: Complete market analysis data
            current_price: Current market price
            current_time: Current timestamp
            
        Returns:
            ConsolidationRange if consolidation detected, None otherwise
        """
        try:
            # Analyze historical data on first call to detect existing consolidation
            if not self._historical_analyzed:
                self._analyze_historical_consolidation(unified_data, current_price, current_time)
                self._historical_analyzed = True
            
            # Get required data
            sr_data = unified_data.get("support_resistance", {})
            trend_data = unified_data.get("trend", {})
            volatility_data = unified_data.get("volatility", {})
            volume_data = unified_data.get("volume", {})
            
            if not all([sr_data, trend_data, volatility_data]):
                return None
            
            # Check if trend is sideways (required for consolidation)
            trend_direction = trend_data.get("direction", "SIDEWAYS")
            if trend_direction != "SIDEWAYS":
                # If we had a consolidation, check if it broke
                if self._current_consolidation:
                    self._check_consolidation_breakout(current_price, current_time)
                self._current_consolidation = None
                return None
            
            # Get S/R levels
            levels = sr_data.get("levels", [])
            if not levels:
                return None
            
            # Find closest support and resistance
            active_support = [
                level for level in levels
                if level.get("type") == "support"
                and level.get("status") == "active"
                and level.get("price_level", 0) < current_price
            ]
            
            active_resistance = [
                level for level in levels
                if level.get("type") == "resistance"
                and level.get("status") == "active"
                and level.get("price_level", 0) > current_price
            ]
            
            if not active_support or not active_resistance:
                return None
            
            # Get closest support and resistance
            closest_support = max(active_support, key=lambda x: x.get("price_level", 0))
            closest_resistance = min(active_resistance, key=lambda x: x.get("price_level", 0))
            
            support_price = closest_support.get("price_level", 0)
            resistance_price = closest_resistance.get("price_level", 0)
            
            if support_price <= 0 or resistance_price <= 0:
                return None
            
            # Check if price is within range
            if current_price < support_price or current_price > resistance_price:
                # Price outside range - consolidation broken or not started
                if self._current_consolidation:
                    self._check_consolidation_breakout(current_price, current_time)
                self._current_consolidation = None
                return None
            
            # Calculate range width
            range_width = resistance_price - support_price
            range_width_pct = range_width / current_price
            
            # Check if range is valid for consolidation
            if range_width_pct < self._min_range_width_pct or range_width_pct > self._max_range_width_pct:
                return None
            
            # Check volatility (should be low for consolidation)
            volatility_category = volatility_data.get("category", "NORMAL")
            volatility_value = volatility_data.get("volatility_5m", 0.0)
            
            if volatility_category in ["HIGH", "EXTREME", "VERY_HIGH"]:
                return None  # Too volatile for consolidation
            
            # Update or create consolidation
            if self._current_consolidation:
                # Update existing consolidation
                self._update_consolidation(
                    support_price, resistance_price, range_width_pct,
                    current_price, current_time, unified_data
                )
            else:
                # Create new consolidation
                self._current_consolidation = ConsolidationRange(
                    upper_bound=resistance_price,
                    lower_bound=support_price,
                    range_width_pct=range_width_pct,
                    started_at=current_time,
                    duration_minutes=0.0,
                    touch_count_upper=1,
                    touch_count_lower=1,
                    avg_volume=volume_data.get("volume_5m", 0.0),
                    volatility=volatility_value,
                    coiling_score=0.0,
                    breakout_probability=0.0
                )
            
            # Update price history
            self._price_history.append((current_price, current_time))
            if len(self._price_history) > self._max_history:
                self._price_history.pop(0)
            
            # Calculate consolidation metrics
            self._calculate_consolidation_metrics(current_time, unified_data)
            
            return self._current_consolidation
            
        except Exception as e:
            logger.error(f"❌ Consolidation detection failed: {e}")
            return None
    
    def _update_consolidation(
        self,
        support_price: float,
        resistance_price: float,
        range_width_pct: float,
        current_price: float,
        current_time: float,
        unified_data: Dict[str, Any]
    ):
        """Update existing consolidation range"""
        if not self._current_consolidation:
            return
        
        # Check if boundaries changed (range expanded/contracted)
        tolerance = current_price * 0.0005  # 0.05% tolerance
        
        if abs(resistance_price - self._current_consolidation.upper_bound) > tolerance:
            self._current_consolidation.touch_count_upper += 1
            self._current_consolidation.upper_bound = resistance_price
        
        if abs(support_price - self._current_consolidation.lower_bound) > tolerance:
            self._current_consolidation.touch_count_lower += 1
            self._current_consolidation.lower_bound = support_price
        
        # Update range width
        self._current_consolidation.range_width_pct = range_width_pct
        
        # Update duration
        self._current_consolidation.duration_minutes = (current_time - self._current_consolidation.started_at) / 60.0
        
        # Update volume (rolling average)
        volume_data = unified_data.get("volume", {})
        current_volume = volume_data.get("volume_5m", 0.0)
        if current_volume > 0:
            # Simple rolling average
            self._current_consolidation.avg_volume = (
                self._current_consolidation.avg_volume * 0.9 + current_volume * 0.1
            )
        
        # Update volatility
        volatility_data = unified_data.get("volatility", {})
        self._current_consolidation.volatility = volatility_data.get("volatility_5m", 0.0)
    
    def _calculate_consolidation_metrics(
        self,
        current_time: float,
        unified_data: Dict[str, Any]
    ):
        """Calculate consolidation metrics (coiling score, breakout probability)"""
        if not self._current_consolidation:
            return
        
        # Calculate coiling score (0-100)
        # Higher score = tighter range (more coiling) = higher breakout probability
        range_width = self._current_consolidation.range_width_pct
        
        # Coiling: range getting tighter over time
        if len(self._price_history) >= 20:
            # Compare recent range to earlier range
            recent_prices = [p[0] for p in self._price_history[-10:]]
            earlier_prices = [p[0] for p in self._price_history[-20:-10]]
            
            recent_range = max(recent_prices) - min(recent_prices)
            earlier_range = max(earlier_prices) - min(earlier_prices)
            
            if earlier_range > 0:
                coiling_ratio = recent_range / earlier_range
                # If recent range is smaller, we're coiling
                coiling_score = max(0.0, min(100.0, (1.0 - coiling_ratio) * 100.0))
            else:
                coiling_score = 50.0  # Neutral
        else:
            # Not enough history - use range width as proxy
            # Smaller range = higher coiling score
            coiling_score = max(0.0, min(100.0, (1.0 - range_width * 100) * 50.0))
        
        self._current_consolidation.coiling_score = coiling_score
        
        # Calculate breakout probability (0-100)
        # Factors:
        # 1. Duration (longer = higher probability)
        # 2. Coiling score (tighter = higher probability)
        # 3. Touch count (more touches = stronger boundaries = higher breakout probability)
        # 4. Volume (decreasing volume = accumulation/distribution = higher probability)
        
        duration_score = min(100.0, (self._current_consolidation.duration_minutes / 60.0) * 50.0)  # Max 50 points
        coiling_score_points = coiling_score * 0.3  # 30 points max
        touch_score = min(30.0, (self._current_consolidation.touch_count_upper + 
                                 self._current_consolidation.touch_count_lower) * 3.0)  # Max 30 points
        
        # Volume analysis (decreasing volume = accumulation/distribution)
        volume_data = unified_data.get("volume", {})
        volume_trend = volume_data.get("trend", "STABLE")
        volume_score = 10.0 if volume_trend == "DECREASING" else 5.0  # 10 points max
        
        breakout_probability = duration_score + coiling_score_points + touch_score + volume_score
        self._current_consolidation.breakout_probability = min(100.0, breakout_probability)
        
        # Predict breakout direction
        pressure_data = unified_data.get("pressure", {})
        pressure_direction = pressure_data.get("direction", "NEUTRAL")
        net_pressure = pressure_data.get("net_pressure", 0.0)
        
        if pressure_direction in ["STRONG_BUY", "BUY"] and net_pressure > 0.3:
            self._current_consolidation.expected_direction = "LONG"
        elif pressure_direction in ["STRONG_SELL", "SELL"] and net_pressure < -0.3:
            self._current_consolidation.expected_direction = "SHORT"
        else:
            # Use RSI for direction hint
            rsi_data = unified_data.get("rsi", {})
            rsi_value = rsi_data.get("value", 50.0)
            if rsi_value > 55:
                self._current_consolidation.expected_direction = "LONG"
            elif rsi_value < 45:
                self._current_consolidation.expected_direction = "SHORT"
            else:
                self._current_consolidation.expected_direction = None
    
    def _check_consolidation_breakout(
        self,
        current_price: float,
        current_time: float
    ) -> Optional[ConsolidationBreakout]:
        """Check if consolidation has broken out"""
        if not self._current_consolidation:
            return None
        
        range_upper = self._current_consolidation.upper_bound
        range_lower = self._current_consolidation.lower_bound
        range_width = range_upper - range_lower
        
        # Check for breakout above upper bound
        if current_price > range_upper:
            # LONG breakout
            breakout_pct = (current_price - range_upper) / range_upper
            
            # Require minimum breakout (0.1% above upper bound)
            if breakout_pct >= 0.001:
                return ConsolidationBreakout(
                    direction="LONG",
                    confidence=self._calculate_breakout_confidence("LONG", breakout_pct),
                    entry_price=current_price,
                    stop_loss=range_lower - (range_width * 0.1),  # Below lower bound
                    take_profit=range_upper + (range_width * 1.5),  # Target: range width * 1.5
                    range_upper=range_upper,
                    range_lower=range_lower,
                    range_width=range_width,
                    duration_minutes=self._current_consolidation.duration_minutes,
                    reasoning=[
                        f"Consolidation breakout LONG (duration: {self._current_consolidation.duration_minutes:.1f} min)",
                        f"Range: ${range_lower:.2f} - ${range_upper:.2f}",
                        f"Breakout: {breakout_pct*100:.2f}% above upper bound",
                        f"Coiling score: {self._current_consolidation.coiling_score:.1f}",
                        f"Breakout probability: {self._current_consolidation.breakout_probability:.1f}%"
                    ],
                    detected_at=current_time
                )
        
        # Check for breakdown below lower bound
        elif current_price < range_lower:
            # SHORT breakout
            breakdown_pct = (range_lower - current_price) / range_lower
            
            # Require minimum breakdown (0.1% below lower bound)
            if breakdown_pct >= 0.001:
                return ConsolidationBreakout(
                    direction="SHORT",
                    confidence=self._calculate_breakout_confidence("SHORT", breakdown_pct),
                    entry_price=current_price,
                    stop_loss=range_upper + (range_width * 0.1),  # Above upper bound
                    take_profit=range_lower - (range_width * 1.5),  # Target: range width * 1.5
                    range_upper=range_upper,
                    range_lower=range_lower,
                    range_width=range_width,
                    duration_minutes=self._current_consolidation.duration_minutes,
                    reasoning=[
                        f"Consolidation breakdown SHORT (duration: {self._current_consolidation.duration_minutes:.1f} min)",
                        f"Range: ${range_lower:.2f} - ${range_upper:.2f}",
                        f"Breakdown: {breakdown_pct*100:.2f}% below lower bound",
                        f"Coiling score: {self._current_consolidation.coiling_score:.1f}",
                        f"Breakout probability: {self._current_consolidation.breakout_probability:.1f}%"
                    ],
                    detected_at=current_time
                )
        
        return None
    
    def _calculate_breakout_confidence(
        self,
        direction: str,
        breakout_pct: float
    ) -> float:
        """Calculate breakout confidence based on consolidation metrics"""
        if not self._current_consolidation:
            return 50.0
        
        confidence = 50.0  # Base confidence
        
        # Duration factor (longer consolidation = higher confidence)
        duration_factor = min(20.0, self._current_consolidation.duration_minutes / 3.0)
        confidence += duration_factor
        
        # Coiling factor (tighter range = higher confidence)
        coiling_factor = self._current_consolidation.coiling_score * 0.2
        confidence += coiling_factor
        
        # Touch count factor (more touches = stronger boundaries = higher confidence)
        touch_factor = min(15.0, (self._current_consolidation.touch_count_upper + 
                                  self._current_consolidation.touch_count_lower) * 2.0)
        confidence += touch_factor
        
        # Breakout magnitude (larger breakout = higher confidence)
        breakout_factor = min(15.0, breakout_pct * 10000.0)  # 0.15% = 15 points
        confidence += breakout_factor
        
        return min(100.0, confidence)
    
    def detect_breakout(
        self,
        unified_data: Dict[str, Any],
        current_price: float,
        current_time: float
    ) -> Optional[ConsolidationBreakout]:
        """
        Detect consolidation breakout
        
        Args:
            unified_data: Complete market analysis data
            current_price: Current market price
            current_time: Current timestamp
            
        Returns:
            ConsolidationBreakout if breakout detected, None otherwise
        """
        try:
            # First, update consolidation detection
            consolidation = self.detect_consolidation(unified_data, current_price, current_time)
            
            # If no consolidation, check if we just broke out of previous consolidation
            if not consolidation and self._current_consolidation:
                breakout = self._check_consolidation_breakout(current_price, current_time)
                if breakout:
                    # Consolidation broken - clear it
                    self._recent_breakouts.append(breakout)
                    if len(self._recent_breakouts) > 10:
                        self._recent_breakouts.pop(0)
                    self._current_consolidation = None
                    return breakout
            
            # If we have consolidation, check if it's breaking now
            if self._current_consolidation:
                breakout = self._check_consolidation_breakout(current_price, current_time)
                if breakout:
                    # Validate breakout with volume and pressure
                    volume_data = unified_data.get("volume", {})
                    pressure_data = unified_data.get("pressure", {})
                    
                    volume_category = volume_data.get("category", "NORMAL")
                    pressure_direction = pressure_data.get("direction", "NEUTRAL")
                    
                    # Breakout must be confirmed by volume or pressure
                    volume_confirmed = volume_category in ["HIGH", "VERY_HIGH"]
                    pressure_confirmed = (breakout.direction == "LONG" and pressure_direction in ["STRONG_BUY", "BUY"]) or \
                                       (breakout.direction == "SHORT" and pressure_direction in ["STRONG_SELL", "SELL"])
                    
                    if volume_confirmed or pressure_confirmed:
                        # Consolidation broken - clear it
                        self._recent_breakouts.append(breakout)
                        if len(self._recent_breakouts) > 10:
                            self._recent_breakouts.pop(0)
                        self._current_consolidation = None
                        return breakout
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Breakout detection failed: {e}")
            return None
    
    def _analyze_historical_consolidation(
        self,
        unified_data: Dict[str, Any],
        current_price: float,
        current_time: float
    ) -> None:
        """
        Analyze historical candles to detect existing consolidation
        
        Uses S/R levels as boundaries (already calculated and validated) and historical data only for:
        1. Calculating true consolidation start time (when price entered the range)
        2. Coiling detection (range getting tighter over time)
        3. Initializing price history
        
        This avoids duplicating S/R level calculations - we use their metadata (touch counts, strength).
        """
        try:
            # Get S/R levels from unified_data (already calculated)
            sr_data = unified_data.get("support_resistance", {})
            levels = sr_data.get("levels", [])
            
            if not levels:
                return
            
            # Find closest support and resistance
            active_support = [
                level for level in levels
                if level.get("type") == "support"
                and level.get("status") == "active"
                and level.get("price_level", 0) < current_price
            ]
            
            active_resistance = [
                level for level in levels
                if level.get("type") == "resistance"
                and level.get("status") == "active"
                and level.get("price_level", 0) > current_price
            ]
            
            if not active_support or not active_resistance:
                return
            
            closest_support = max(active_support, key=lambda x: x.get("price_level", 0))
            closest_resistance = min(active_resistance, key=lambda x: x.get("price_level", 0))
            
            support_price = closest_support.get("price_level", 0)
            resistance_price = closest_resistance.get("price_level", 0)
            
            if support_price <= 0 or resistance_price <= 0:
                return
            
            # Check if price is currently in range
            if current_price < support_price or current_price > resistance_price:
                return  # Not in consolidation range
            
            # Calculate range width
            range_width = resistance_price - support_price
            range_width_pct = range_width / current_price
            
            if range_width_pct < self._min_range_width_pct or range_width_pct > self._max_range_width_pct:
                return
            
            # Use S/R level metadata (already calculated - no need to recalculate)
            touch_count_upper = closest_resistance.get("touches", 0)
            touch_count_lower = closest_support.get("touches", 0)
            
            # Get historical data service only for duration and coiling
            from core.services.historical_data_service import create_historical_data_service
            historical_service = create_historical_data_service()
            
            # Fetch last 4-6 hours of 5m candles (48-72 candles) for duration/coiling only
            candles_5m = historical_service.get_5m_candles(self.symbol, 72)
            
            if not candles_5m or len(candles_5m) < 12:
                # Not enough historical data - use S/R metadata only
                logger.debug("📊 Insufficient historical candles - using S/R metadata only")
                return
            
            # Find when price entered the range (for duration calculation)
            consolidation_start_time = None
            prices_in_range = []
            
            # Go backwards through candles to find when consolidation started
            for i in range(len(candles_5m) - 1, -1, -1):
                candle = candles_5m[i]
                high = candle.get("high", 0)
                low = candle.get("low", 0)
                close = candle.get("close", 0)
                timestamp = candle.get("timestamp", 0)
                
                # Check if candle is within range
                if low >= support_price and high <= resistance_price:
                    prices_in_range.append(close)
                    
                    # Update consolidation start time (earliest candle in range)
                    if consolidation_start_time is None:
                        consolidation_start_time = timestamp
                else:
                    # Price broke out of range - consolidation ended
                    if consolidation_start_time is not None:
                        break
            
            # Require minimum candles in range to consider it consolidation
            if len(prices_in_range) < 12:  # At least 1 hour (12 x 5min)
                return
            
            # Calculate duration from historical data
            if consolidation_start_time:
                duration_minutes = (current_time - consolidation_start_time) / 60.0
            else:
                duration_minutes = len(prices_in_range) * 5  # Estimate: 5 min per candle
            
            # Only create consolidation if duration meets minimum
            if duration_minutes < self._min_consolidation_duration:
                return
            
            # Calculate coiling score from historical data (range getting tighter)
            if len(prices_in_range) >= 20:
                recent_prices = prices_in_range[-10:]
                earlier_prices = prices_in_range[-20:-10]
                
                recent_range = max(recent_prices) - min(recent_prices)
                earlier_range = max(earlier_prices) - min(earlier_prices)
                
                if earlier_range > 0:
                    coiling_ratio = recent_range / earlier_range
                    coiling_score = max(0.0, min(100.0, (1.0 - coiling_ratio) * 100.0))
                else:
                    coiling_score = 50.0
            else:
                coiling_score = max(0.0, min(100.0, (1.0 - range_width_pct * 100) * 50.0))
            
            # Get volume and volatility from unified_data (already calculated)
            volume_data = unified_data.get("volume", {})
            volatility_data = unified_data.get("volatility", {})
            
            # Create consolidation using S/R metadata + historical duration/coiling
            self._current_consolidation = ConsolidationRange(
                upper_bound=resistance_price,
                lower_bound=support_price,
                range_width_pct=range_width_pct,
                started_at=consolidation_start_time or (current_time - duration_minutes * 60),
                duration_minutes=duration_minutes,
                touch_count_upper=touch_count_upper,  # From S/R level metadata
                touch_count_lower=touch_count_lower,  # From S/R level metadata
                avg_volume=volume_data.get("volume_5m", 0.0),  # From unified_data
                volatility=volatility_data.get("volatility_5m", 0.0),  # From unified_data
                coiling_score=coiling_score,  # Calculated from historical prices
                breakout_probability=0.0  # Will be calculated in _calculate_consolidation_metrics
            )
            
            # Initialize price history from historical candles
            for candle in candles_5m[-min(100, len(candles_5m)):]:
                close = candle.get("close", 0)
                timestamp = candle.get("timestamp", 0)
                if close > 0 and timestamp > 0:
                    self._price_history.append((close, timestamp))
            
            logger.info(f"📊 Historical consolidation detected: ${support_price:.2f} - ${resistance_price:.2f} "
                       f"(duration: {duration_minutes:.1f} min, touches: {touch_count_upper + touch_count_lower} from S/R levels)")
            
        except Exception as e:
            logger.debug(f"Could not analyze historical consolidation: {e}")
            # Don't raise - continue with real-time detection only
    
    def get_current_consolidation(self) -> Optional[ConsolidationRange]:
        """Get current consolidation range if active"""
        return self._current_consolidation
    
    def get_consolidation_info(self) -> Dict[str, Any]:
        """Get consolidation information for dashboard/analysis"""
        if not self._current_consolidation:
            return {
                "active": False,
                "status": "No consolidation detected"
            }
        
        return {
            "active": True,
            "upper_bound": self._current_consolidation.upper_bound,
            "lower_bound": self._current_consolidation.lower_bound,
            "range_width_pct": self._current_consolidation.range_width_pct,
            "duration_minutes": self._current_consolidation.duration_minutes,
            "coiling_score": self._current_consolidation.coiling_score,
            "breakout_probability": self._current_consolidation.breakout_probability,
            "expected_direction": self._current_consolidation.expected_direction,
            "touch_count_upper": self._current_consolidation.touch_count_upper,
            "touch_count_lower": self._current_consolidation.touch_count_lower
        }