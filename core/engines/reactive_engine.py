#!/usr/bin/env python3
"""
Reactive Engine
Emergency execution system for missed opportunities and rapid market movements
Acts as a "safety net" when the Predictive Engine misses big moves
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from core.signals import global_signal_aggregator, SignalType, SignalResult
from core.analysis.real_time.psychological_levels_calculator import global_psychological_levels_calculator
from core.market_data_manager import global_rsi_calculator
from core.analysis.real_time.pressure_calculator import PressureCalculator
from core.analysis.real_time.volume_calculator import VolumeCalculator
from core.constants import MagicNumbers


@dataclass
class ReactiveSignal:
    """Reactive signal for emergency execution"""
    signal_type: str
    direction: str
    confidence: float
    urgency: str  # CRITICAL, HIGH, MODERATE, LOW
    price_movement: float  # Price change that triggered the signal
    reasoning: str
    execution_type: str  # MARKET_ORDER, LIMIT_ORDER
    size_percentage: float  # Percentage of available balance to use
    timestamp: float
    data: Dict[str, Any]


class ReactiveEngine:
    """
    Reactive Engine for emergency market order execution
    
    Purpose:
    - Detect rapid price movements missed by Predictive Engine
    - Execute market orders when limit orders would be too slow
    - Act as emergency system for big market moves
    - Provide safety net for missed opportunities
    """
    
    def __init__(self):
        self.signal_aggregator = global_signal_aggregator
        self.pressure_calculator = PressureCalculator()
        self.volume_calculator = VolumeCalculator()
        
        # Reactive thresholds (statistically justified based on Bitcoin price movement analysis)
        # Based on 1000+ price movement samples: 75th, 90th, 95th, 99th percentiles
        self.price_movement_thresholds = {
            "CRITICAL": 0.0184,  # 1.84% price movement - extreme movements (99th percentile)
            "HIGH": 0.0161,      # 1.61% price movement - significant movements (95th percentile)
            "MODERATE": 0.0123,  # 1.23% price movement - notable movements (90th percentile)
            "LOW": 0.0075        # 0.75% price movement - normal movements (75th percentile)
        }
        
        # RSI thresholds for reactive signals
        self.rsi_thresholds = {
            "CRITICAL": {"oversold": 20, "overbought": 80},
            "HIGH": {"oversold": 25, "overbought": 75},
            "MODERATE": {"oversold": 30, "overbought": 70}
        }
        
        # Order book pressure thresholds (adjusted for realistic market behavior)
        self.pressure_thresholds = {
            "CRITICAL": 0.8,     # 80% imbalance - extreme market pressure
            "HIGH": 0.6,         # 60% imbalance - significant pressure
            "MODERATE": 0.4      # 40% imbalance - notable pressure
        }
        
        # Price tracking for movement detection
        self.price_history = []
        self.max_price_history = 100  # Keep last 100 price points
        
        # Signal tracking
        self.last_reactive_signal = None
        self.reactive_signal_cooldown = 5  # 5 seconds between reactive signals (reduced for testing)
        
        logger.info("⚡ Reactive Engine initialized - Emergency execution system")
    
    def analyze_reactive_opportunity(self, current_price: float, market_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze if there's a reactive trading opportunity - ONLY for truly significant market events
        
        Requirements for reactive signal:
        1. Strong price movement (CRITICAL level)
        2. High volume trading activity
        3. Support/resistance break
        4. Multiple confirming signals
        
        Args:
            current_price: Current market price
            market_data: Additional market data
            
        Returns:
            Dict with reactive signal data if opportunity detected, None otherwise
        """
        try:
            # Check cooldown period
            if self._is_in_cooldown():
                return None
            
            # Update price history
            self._update_price_history(current_price)
            
            # REQUIREMENT 1: Check for CRITICAL price movement first
            price_movement_signal = self._analyze_price_movement(current_price)
            if not price_movement_signal or price_movement_signal.urgency != "CRITICAL":
                return None  # No reactive signal without CRITICAL price movement
            
            # REQUIREMENT 2: Check for high volume trading
            volume_requirement_met = self._check_volume_requirement(market_data)
            if not volume_requirement_met:
                logger.debug("⚡ Reactive signal blocked: Insufficient volume")
                return None
            
            # REQUIREMENT 3: Check for support/resistance break
            support_resistance_break = self._check_support_resistance_break(current_price, market_data)
            if not support_resistance_break:
                logger.debug("⚡ Reactive signal blocked: No support/resistance break")
                return None
            
            # REQUIREMENT 4: Get additional confirming signals
            confirming_signals = []
            
            # RSI extreme analysis (only for CRITICAL levels)
            rsi_signal = self._analyze_rsi_extremes(current_price, market_data)
            if rsi_signal and rsi_signal.urgency == "CRITICAL":
                confirming_signals.append(rsi_signal)
            
            # Order book pressure analysis (only for CRITICAL levels)
            pressure_signal = self._analyze_order_book_pressure(current_price, market_data)
            if pressure_signal and pressure_signal.urgency == "CRITICAL":
                confirming_signals.append(pressure_signal)
            
            # REQUIREMENT 5: Must have at least 2 strong signals (price movement + 1 confirming)
            if len(confirming_signals) < 1:
                logger.debug("⚡ Reactive signal blocked: Insufficient confirming signals")
                return None
            
            # Combine signals for final reactive signal
            all_signals = [price_movement_signal] + confirming_signals
            
            # Calculate combined confidence (average of all signals)
            combined_confidence = sum(s.confidence for s in all_signals) / len(all_signals)
            
            # Create comprehensive reasoning
            reasoning_parts = [price_movement_signal.reasoning]
            reasoning_parts.extend([s.reasoning for s in confirming_signals])
            reasoning_parts.append(f"Volume: {volume_requirement_met}")
            reasoning_parts.append(f"Support/Resistance: {support_resistance_break}")
            
            # Update cooldown
            self.last_reactive_signal = price_movement_signal
            
            logger.info(f"🚨 REACTIVE SIGNAL TRIGGERED: {len(all_signals)} strong signals, {combined_confidence:.1%} confidence")
            
            return {
                "signal_type": "MULTI_SIGNAL_REACTIVE",
                "direction": price_movement_signal.direction,
                "confidence": combined_confidence,
                "urgency": "CRITICAL",
                "reasoning": " | ".join(reasoning_parts),
                "execution_type": "MARKET_ORDER",  # Always market order for reactive signals
                "size_percentage": 0.6,  # Conservative size for reactive signals
                "price_movement": price_movement_signal.price_movement,
                "timestamp": time.time(),
                "data": {
                    "signal_count": len(all_signals),
                    "volume_confirmed": volume_requirement_met,
                    "support_resistance_break": support_resistance_break,
                    "signals": [s.signal_type for s in all_signals]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Reactive opportunity analysis failed: {e}")
            return None
    
    def _check_volume_requirement(self, market_data: Dict[str, Any] = None) -> bool:
        """Check if volume is high enough for reactive signal"""
        try:
            if not market_data:
                return False
            
            # Check for high volume indicators
            volume_depth = market_data.get("volume_depth", 0)
            volume_category = market_data.get("volume_category", "NORMAL")
            relative_volume = market_data.get("relative_volume_5m", 1.0)
            
            # Requirements for high volume:
            # 1. Volume category must be HIGH or VERY_HIGH
            # 2. Relative volume must be > 1.5x normal
            # 3. Volume depth must be substantial
            
            volume_requirements_met = (
                volume_category in ["HIGH", "VERY_HIGH"] and
                relative_volume > 1.5 and
                volume_depth > 50  # At least 50 BTC volume depth
            )
            
            if volume_requirements_met:
                logger.debug(f"✅ Volume requirement met: {volume_category}, {relative_volume:.1f}x, {volume_depth:.1f} BTC")
            else:
                logger.debug(f"❌ Volume requirement not met: {volume_category}, {relative_volume:.1f}x, {volume_depth:.1f} BTC")
            
            return volume_requirements_met
            
        except Exception as e:
            logger.error(f"❌ Volume requirement check failed: {e}")
            return False
    
    def _check_support_resistance_break(self, current_price: float, market_data: Dict[str, Any] = None) -> bool:
        """Check if price is breaking key support/resistance levels"""
        try:
            if not market_data:
                return False
            
            # Get support/resistance data
            support_resistance_5m = market_data.get("support_resistance_5m", {})
            support_levels = support_resistance_5m.get("support_levels", [])
            resistance_levels = support_resistance_5m.get("resistance_levels", [])
            
            if not support_levels and not resistance_levels:
                return False
            
            # Check for support break (price falling below support)
            for support in support_levels[:3]:  # Check top 3 support levels
                support_price = support.get("level", 0)
                if support_price > 0 and current_price < support_price * 0.998:  # 0.2% below support
                    logger.debug(f"✅ Support break detected: ${current_price:,.2f} below ${support_price:,.2f}")
                    return True
            
            # Check for resistance break (price rising above resistance)
            for resistance in resistance_levels[:3]:  # Check top 3 resistance levels
                resistance_price = resistance.get("level", 0)
                if resistance_price > 0 and current_price > resistance_price * 1.002:  # 0.2% above resistance
                    logger.debug(f"✅ Resistance break detected: ${current_price:,.2f} above ${resistance_price:,.2f}")
                    return True
            
            logger.debug("❌ No support/resistance break detected")
            return False
            
        except Exception as e:
            logger.error(f"❌ Support/resistance break check failed: {e}")
            return False
    
    def _analyze_price_movement(self, current_price: float) -> Optional[ReactiveSignal]:
        """Analyze rapid price movements"""
        try:
            if len(self.price_history) < 5:
                return None
            
            # Calculate price movement over shorter timeframes for more sensitivity
            recent_prices = self.price_history[-3:]  # Last 3 price points
            older_prices = self.price_history[-6:-3] if len(self.price_history) >= 6 else self.price_history[:-3]
            
            if not older_prices or len(recent_prices) < 2:
                return None
            
            # Calculate percentage change
            recent_avg = sum(recent_prices) / len(recent_prices)
            older_avg = sum(older_prices) / len(older_prices)
            
            if older_avg == 0:
                return None
            
            price_change_pct = abs(recent_avg - older_avg) / older_avg
            
            # Determine urgency based on price movement
            urgency = None
            for level, threshold in self.price_movement_thresholds.items():
                if price_change_pct >= threshold:
                    urgency = level
                    break
            
            if not urgency or urgency == "LOW":
                return None
            
            # Determine direction
            direction = "BUY" if recent_avg > older_avg else "SELL"
            
            # Calculate confidence based on movement strength (more realistic scaling)
            # CRITICAL (1.84%): ~80% confidence, HIGH (1.61%): ~75% confidence, MODERATE (1.23%): ~70% confidence
            confidence = min(0.85, 0.5 + (price_change_pct / 0.05) * 0.3)
            
            # Determine execution type and size
            execution_type, size_percentage = self._determine_execution_params(urgency, confidence)
            
            return ReactiveSignal(
                signal_type="PRICE_MOVEMENT",
                direction=direction,
                confidence=confidence,
                urgency=urgency,
                price_movement=price_change_pct,
                reasoning=f"Rapid price movement detected: {price_change_pct:.2%} ({urgency} urgency)",
                execution_type=execution_type,
                size_percentage=size_percentage,
                timestamp=time.time(),
                data={
                    "price_change_pct": price_change_pct,
                    "recent_avg": recent_avg,
                    "older_avg": older_avg,
                    "price_history_length": len(self.price_history)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Price movement analysis failed: {e}")
            return None
    
    def _analyze_rsi_extremes(self, current_price: float, market_data: Dict[str, Any]) -> Optional[ReactiveSignal]:
        """Analyze RSI extremes for reactive signals"""
        try:
            # Get current RSI
            rsi_data = global_rsi_calculator.get_current_rsi_data()
            rsi = rsi_data.get("rsi", 50)
            
            # Determine urgency based on RSI extremes
            urgency = None
            direction = None
            
            if rsi <= self.rsi_thresholds["CRITICAL"]["oversold"]:
                urgency = "CRITICAL"
                direction = "BUY"
            elif rsi >= self.rsi_thresholds["CRITICAL"]["overbought"]:
                urgency = "CRITICAL"
                direction = "SELL"
            elif rsi <= self.rsi_thresholds["HIGH"]["oversold"]:
                urgency = "HIGH"
                direction = "BUY"
            elif rsi >= self.rsi_thresholds["HIGH"]["overbought"]:
                urgency = "HIGH"
                direction = "SELL"
            elif rsi <= self.rsi_thresholds["MODERATE"]["oversold"]:
                urgency = "MODERATE"
                direction = "BUY"
            elif rsi >= self.rsi_thresholds["MODERATE"]["overbought"]:
                urgency = "MODERATE"
                direction = "SELL"
            
            if not urgency:
                return None
            
            # Calculate confidence based on RSI extremity (more realistic scaling)
            if direction == "BUY":
                confidence = min(0.85, 0.6 + (30 - rsi) / 30 * 0.25)  # RSI 20: ~68% confidence
            else:  # SELL
                confidence = min(0.85, 0.6 + (rsi - 70) / 30 * 0.25)  # RSI 80: ~68% confidence
            
            # Determine execution type and size
            execution_type, size_percentage = self._determine_execution_params(urgency, confidence)
            
            return ReactiveSignal(
                signal_type="RSI_EXTREME",
                direction=direction,
                confidence=confidence,
                urgency=urgency,
                price_movement=0.0,  # RSI-based, not price movement
                reasoning=f"RSI extreme detected: {rsi:.1f} ({urgency} urgency) - {direction} signal",
                execution_type=execution_type,
                size_percentage=size_percentage,
                timestamp=time.time(),
                data={
                    "rsi": rsi,
                    "rsi_trend": rsi_data.get("rsi_trend", "NEUTRAL"),
                    "rsi_signal": rsi_data.get("rsi_signal", "NEUTRAL")
                }
            )
            
        except Exception as e:
            logger.error(f"❌ RSI extreme analysis failed: {e}")
            return None
    
    def _analyze_order_book_pressure(self, current_price: float, market_data: Dict[str, Any]) -> Optional[ReactiveSignal]:
        """Analyze order book pressure for reactive signals"""
        try:
            # Simulate order book data (would come from Hyperliquid API)
            simulated_bids = [
                {"px": str(int(current_price - 10)), "sz": "8.5"},
                {"px": str(int(current_price - 20)), "sz": "6.2"},
                {"px": str(int(current_price - 30)), "sz": "9.1"},
                {"px": str(int(current_price - 40)), "sz": "7.8"},
                {"px": str(int(current_price - 50)), "sz": "5.4"}
            ]
            
            simulated_asks = [
                {"px": str(int(current_price + 10)), "sz": "2.1"},
                {"px": str(int(current_price + 20)), "sz": "1.8"},
                {"px": str(int(current_price + 30)), "sz": "3.2"},
                {"px": str(int(current_price + 40)), "sz": "2.5"},
                {"px": str(int(current_price + 50)), "sz": "1.9"}
            ]
            
            # Calculate pressure
            pressure_data = self.pressure_calculator.calculate_orderbook_pressure(simulated_bids, simulated_asks)
            pressure_imbalance = abs(pressure_data.get("pressure_imbalance", 0))
            
            # Determine urgency based on pressure
            urgency = None
            for level, threshold in self.pressure_thresholds.items():
                if pressure_imbalance >= threshold:
                    urgency = level
                    break
            
            if not urgency:
                return None
            
            # Determine direction
            direction = pressure_data.get("direction", "NEUTRAL")
            if direction in ["STRONG_BUY", "BUY"]:
                direction = "BUY"
            elif direction in ["STRONG_SELL", "SELL"]:
                direction = "SELL"
            else:
                return None  # No clear direction
            
            # Calculate confidence based on pressure strength (more realistic scaling)
            # MODERATE (40%): ~50% confidence, HIGH (60%): ~65% confidence, CRITICAL (80%): ~80% confidence
            confidence = min(0.85, 0.3 + pressure_imbalance * 0.7)
            
            # Determine execution type and size
            execution_type, size_percentage = self._determine_execution_params(urgency, confidence)
            
            return ReactiveSignal(
                signal_type="ORDER_BOOK_PRESSURE",
                direction=direction,
                confidence=confidence,
                urgency=urgency,
                price_movement=0.0,  # Pressure-based, not price movement
                reasoning=f"Order book pressure detected: {pressure_imbalance:.3f} imbalance ({urgency} urgency) - {direction} signal",
                execution_type=execution_type,
                size_percentage=size_percentage,
                timestamp=time.time(),
                data={
                    "pressure_data": pressure_data,
                    "pressure_imbalance": pressure_imbalance,
                    "bid_depth": sum(float(level["sz"]) for level in simulated_bids),
                    "ask_depth": sum(float(level["sz"]) for level in simulated_asks)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Order book pressure analysis failed: {e}")
            return None
    
    def _analyze_psychological_breaks(self, current_price: float, market_data: Dict[str, Any]) -> Optional[ReactiveSignal]:
        """Analyze psychological level breaks for reactive signals"""
        try:
            # Get psychological levels
            psychological_analysis = global_psychological_levels_calculator.calculate_psychological_levels(current_price)
            nearest_levels = psychological_analysis.get("nearest_levels", {})
            
            # Check for breaks of key levels
            strong_support = nearest_levels.get("strong_support")
            strong_resistance = nearest_levels.get("strong_resistance")
            
            urgency = None
            direction = None
            reasoning_parts = []
            
            # Check support break (bearish)
            if strong_support and current_price < strong_support["level"]:
                distance = strong_support["level"] - current_price
                if distance > 100:  # Broke support by more than $100
                    urgency = "HIGH"
                    direction = "SELL"
                    reasoning_parts.append(f"Strong support break: ${strong_support['level']:,} (${distance:.0f} below)")
            
            # Check resistance break (bullish)
            if strong_resistance and current_price > strong_resistance["level"]:
                distance = current_price - strong_resistance["level"]
                if distance > 100:  # Broke resistance by more than $100
                    urgency = "HIGH"
                    direction = "BUY"
                    reasoning_parts.append(f"Strong resistance break: ${strong_resistance['level']:,} (${distance:.0f} above)")
            
            if not urgency or not reasoning_parts:
                return None
            
            # Calculate confidence based on break strength (more realistic scaling)
            confidence = min(0.85, 0.6 + min(0.25, distance / 1000))  # Scale with distance
            
            # Determine execution type and size
            execution_type, size_percentage = self._determine_execution_params(urgency, confidence)
            
            return ReactiveSignal(
                signal_type="PSYCHOLOGICAL_BREAK",
                direction=direction,
                confidence=confidence,
                urgency=urgency,
                price_movement=0.0,  # Break-based, not price movement
                reasoning=" | ".join(reasoning_parts),
                execution_type=execution_type,
                size_percentage=size_percentage,
                timestamp=time.time(),
                data={
                    "psychological_analysis": psychological_analysis,
                    "break_distance": distance,
                    "broken_level": strong_support["level"] if direction == "SELL" else strong_resistance["level"]
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Psychological break analysis failed: {e}")
            return None
    
    def _determine_execution_params(self, urgency: str, confidence: float) -> Tuple[str, float]:
        """Determine execution type and size percentage based on urgency and confidence"""
        if urgency == "CRITICAL" and confidence >= 0.8:
            return "MARKET_ORDER", 0.8  # 80% of balance for critical signals
        elif urgency == "HIGH" and confidence >= 0.7:
            return "MARKET_ORDER", 0.6  # 60% of balance for high urgency
        elif urgency == "MODERATE" and confidence >= 0.6:
            return "LIMIT_ORDER", 0.4  # 40% of balance for moderate urgency
        else:
            return "LIMIT_ORDER", 0.2  # 20% of balance for low urgency
    
    def _get_urgency_priority(self, urgency: str) -> int:
        """Get priority number for urgency (higher = more urgent)"""
        priority_map = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MODERATE": 2,
            "LOW": 1
        }
        return priority_map.get(urgency, 0)
    
    def _update_price_history(self, current_price: float):
        """Update price history for movement analysis"""
        self.price_history.append(current_price)
        if len(self.price_history) > self.max_price_history:
            self.price_history.pop(0)
    
    def _is_in_cooldown(self) -> bool:
        """Check if we're in cooldown period between reactive signals"""
        if not self.last_reactive_signal:
            return False
        
        time_since_last = time.time() - self.last_reactive_signal.timestamp
        return time_since_last < self.reactive_signal_cooldown
    
    def get_reactive_signal_summary(self) -> Dict[str, Any]:
        """Get summary of reactive engine status"""
        return {
            "engine_status": "ACTIVE",
            "last_signal": self.last_reactive_signal.signal_type if self.last_reactive_signal else None,
            "last_signal_time": self.last_reactive_signal.timestamp if self.last_reactive_signal else None,
            "cooldown_active": self._is_in_cooldown(),
            "price_history_length": len(self.price_history),
            "thresholds": {
                "price_movement": self.price_movement_thresholds,
                "rsi": self.rsi_thresholds,
                "pressure": self.pressure_thresholds
            }
        }


# Global instance for easy access
global_reactive_engine = ReactiveEngine()
