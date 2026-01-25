#!/usr/bin/env python3
"""
Momentum Breakout Detector
Detects strong momentum moves BEFORE they happen using multiple signals

Detection Logic:
1. Price near strong S/R level (0.3-1% away)
2. Building orderbook pressure (STRONG_BUY or STRONG_SELL)
3. Volume surge (above percentile threshold)
4. Price acceleration (momentum building)
5. RSI momentum alignment
6. Volatility spike (EXTREME category)

All signals must align for high-confidence breakout prediction
"""

import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from loguru import logger
from core.constants import TechnicalAnalysisConstants


@dataclass
class MomentumSignal:
    """Momentum breakout signal"""
    direction: str  # "LONG" or "SHORT"
    confidence: float  # 0.0-100.0
    entry_price: float  # Current market price (market order)
    stop_loss: float
    take_profit: float
    reasoning: List[str]
    detected_at: float
    breakout_level: Optional[float] = None  # S/R level that's about to break
    expected_move_pct: float = 0.0  # Expected move percentage based on historical breakouts
    risk_reward_ratio: float = 0.0  # Actual R:R for position sizing


class MomentumDetector:
    """
    Detects momentum breakouts before they happen
    
    Monitors:
    - Price proximity to strong S/R levels
    - Orderbook pressure buildup
    - Volume surge patterns
    - Price acceleration
    - RSI momentum
    - Volatility conditions
    
    Returns high-confidence signals when multiple factors align
    """
    
    def __init__(self):
        logger.info("⚡ Momentum Detector initialized")
        self._recent_signals: List[MomentumSignal] = []
        self._signal_cooldown = 300  # 5 minutes between signals for same direction
    
    def detect_momentum(
        self,
        unified_data: Dict[str, Any],
        current_price: float,
        atr_5m: float
    ) -> Optional[MomentumSignal]:
        """
        Detect momentum breakout opportunity
        
        Args:
            unified_data: Complete market analysis data
            current_price: Current market price
            atr_5m: 5-minute ATR for distance calculations
            
        Returns:
            MomentumSignal if high-confidence breakout detected, None otherwise
        """
        try:
            # Get required data (NO FALLBACKS - unified_data must have all keys)
            sr_data = unified_data["support_resistance"]
            pressure_data = unified_data["pressure"]
            volume_data = unified_data["volume"]
            rsi_data = unified_data["rsi"]
            volatility_data = unified_data["volatility"]
            trend_data = unified_data["trend"]
            
            if not all([sr_data, pressure_data, volume_data]):
                return None
            
            # Get S/R levels (NO FALLBACKS)
            levels = sr_data["levels"]
            if not levels:
                return None
            
            # Filter for active levels near current price (NO FALLBACKS)
            active_support = [
                level for level in levels
                if level["type"] == "support"
                and level["status"] == "active"
                and level["price_level"] < current_price
            ]
            
            active_resistance = [
                level for level in levels
                if level["type"] == "resistance"
                and level["status"] == "active"
                and level["price_level"] > current_price
            ]
            
            # Check for LONG breakout (breakout above resistance)
            long_signal = self._check_long_breakout(
                current_price=current_price,
                resistance_levels=active_resistance,
                pressure_data=pressure_data,
                volume_data=volume_data,
                rsi_data=rsi_data,
                volatility_data=volatility_data,
                trend_data=trend_data,
                atr_5m=atr_5m
            )
            
            # Check for SHORT breakout (breakdown below support)
            short_signal = self._check_short_breakout(
                current_price=current_price,
                support_levels=active_support,
                pressure_data=pressure_data,
                volume_data=volume_data,
                rsi_data=rsi_data,
                volatility_data=volatility_data,
                trend_data=trend_data,
                atr_5m=atr_5m
            )
            
            # Return best signal (highest confidence)
            if long_signal and short_signal:
                return long_signal if long_signal.confidence >= short_signal.confidence else short_signal
            elif long_signal:
                return long_signal
            elif short_signal:
                return short_signal
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Momentum detection failed: {e}")
            return None
    
    def _check_long_breakout(
        self,
        current_price: float,
        resistance_levels: List[Dict[str, Any]],
        pressure_data: Dict[str, Any],
        volume_data: Dict[str, Any],
        rsi_data: Dict[str, Any],
        volatility_data: Dict[str, Any],
        trend_data: Dict[str, Any],
        atr_5m: float
    ) -> Optional[MomentumSignal]:
        """Check for LONG breakout (breakout above resistance)"""
        if not resistance_levels:
            return None
        
        # Find closest strong resistance (NO FALLBACKS)
        resistance_levels.sort(key=lambda x: (x["price_level"] - current_price, -x["strength_score"]))
        
        for resistance in resistance_levels:
            level_price = resistance["price_level"]
            level_strength = resistance["strength_score"]
            
            if level_price <= 0 or level_price <= current_price:
                continue
            
            # Check if price is within breakout range (0.3-1% from resistance)
            distance_to_level = (level_price - current_price) / current_price
            if distance_to_level < 0.003 or distance_to_level > 0.01:  # 0.3% to 1%
                continue
            
            # Only consider strong levels (strength >= 60)
            if level_strength < 60:
                continue
            
            # Build signal factors
            factors = []
            confidence = 0.0
            
            # 1. S/R proximity (20 points)
            if distance_to_level < 0.005:  # Within 0.5%
                confidence += 20.0
                factors.append(f"Price near strong resistance ${level_price:.2f} ({distance_to_level*100:.2f}% away)")
            else:
                confidence += 15.0
                factors.append(f"Price approaching resistance ${level_price:.2f} ({distance_to_level*100:.2f}% away)")
            
            # 2. Orderbook pressure (25 points)
            pressure_direction = pressure_data["direction"]  # Required (NO FALLBACKS)
            pressure_strength = pressure_data["strength"]  # Required (NO FALLBACKS)
            net_pressure = pressure_data["net_pressure"]  # Required (NO FALLBACKS)
            
            if pressure_direction in ["STRONG_BUY", "BUY"] and pressure_strength > 0.7:
                confidence += 25.0
                factors.append(f"Strong buy pressure (strength: {pressure_strength:.2f})")
            elif pressure_direction == "BUY" and pressure_strength > 0.5:
                confidence += 15.0
                factors.append(f"Buy pressure building (strength: {pressure_strength:.2f})")
            elif net_pressure > 0.3:
                confidence += 10.0
                factors.append(f"Buy pressure detected (net: {net_pressure:.3f})")
            else:
                factors.append("No significant buy pressure")
            
            # 3. Volume surge (20 points) + Volume momentum boost (up to 10 points)
            volume_category = volume_data["category"]  # Required (NO FALLBACKS)
            volume_value = volume_data["volume_5m"]  # Required (NO FALLBACKS)
            volume_percentile = volume_data["percentile"]  # Required (NO FALLBACKS)
            volume_momentum = volume_data["volume_momentum"]  # Numeric momentum for entry timing
            
            volume_score = 0.0
            if volume_category in ["HIGH", "VERY_HIGH"] and volume_percentile > 75:
                volume_score = 20.0
                factors.append(f"Volume surge ({volume_category}, {volume_percentile:.0f}th percentile)")
            elif volume_percentile > 60:
                volume_score = 10.0
                factors.append(f"Above-average volume ({volume_percentile:.0f}th percentile)")
            else:
                factors.append(f"Normal volume ({volume_percentile:.0f}th percentile)")
            
            # Volume momentum boost: Strong acceleration increases entry confidence
            if volume_momentum > 0.2:  # Strong positive momentum (>20% increase)
                momentum_boost = min(10.0, volume_momentum * 30.0)  # Up to 10 points
                volume_score += momentum_boost
                factors.append(f"Strong volume momentum ({volume_momentum*100:.1f}% acceleration)")
            elif volume_momentum > 0.1:  # Moderate momentum (>10% increase)
                momentum_boost = min(5.0, volume_momentum * 25.0)  # Up to 5 points
                volume_score += momentum_boost
                factors.append(f"Moderate volume momentum ({volume_momentum*100:.1f}% acceleration)")
            elif volume_momentum < -0.1:  # Declining volume (negative momentum)
                volume_score -= 5.0
                factors.append(f"Volume declining ({volume_momentum*100:.1f}% deceleration)")
            
            confidence += volume_score
            
            # 4. Price acceleration (15 points)
            trend_direction = trend_data["direction"] if "direction" in trend_data else "SIDEWAYS"
            trend_strength_raw = trend_data["strength"] if "strength" in trend_data else 0.0
            try:
                trend_strength = abs(float(trend_strength_raw)) if trend_strength_raw is not None else 0.0
            except (ValueError, TypeError):
                trend_strength = 0.0
            
            if trend_direction == "BULLISH" and trend_strength > 0.005:  # 0.5% strength
                confidence += 15.0
                factors.append(f"Bullish momentum ({trend_strength*100:.2f}% strength)")
            elif trend_direction == "BULLISH":
                confidence += 8.0
                factors.append("Slight bullish bias")
            else:
                factors.append(f"Trend: {trend_direction}")
            
            # 5. RSI momentum (10 points)
            rsi_value = rsi_data["rsi"]  # Required (NO FALLBACKS) - RSI calculator returns "rsi" key, not "value"
            if TechnicalAnalysisConstants.RSI_NEUTRAL < rsi_value < TechnicalAnalysisConstants.RSI_OVERBOUGHT:  # Bullish but not overbought
                confidence += 10.0
                factors.append(f"RSI bullish ({rsi_value:.1f})")
            elif rsi_value >= TechnicalAnalysisConstants.RSI_OVERBOUGHT:
                confidence -= 5.0  # Overbought - reduce confidence
                factors.append(f"RSI overbought ({rsi_value:.1f})")
            else:
                factors.append(f"RSI: {rsi_value:.1f}")
            
            # 6. Volatility check (10 points)
            volatility_category = volatility_data["category"] if "category" in volatility_data else "NORMAL"
            if volatility_category in ["HIGH", "EXTREME"]:
                confidence += 10.0
                factors.append(f"High volatility ({volatility_category})")
            else:
                factors.append(f"Volatility: {volatility_category}")
            
            # Minimum confidence threshold
            if confidence < 60.0:
                logger.debug(f"⚡ LONG breakout signal too weak: {confidence:.1f}% (resistance @ ${level_price:.2f})")
                continue
            
            # Calculate stop loss and take profit
            # Stop: below support (or 2xATR, whichever is more conservative)
            stop_loss = max(
                current_price - (atr_5m * 2.0),  # Risk-based: 2xATR
                current_price * 0.99  # Max 1% stop
            )
            
            # Take profit: above resistance + buffer (or 1.5x risk, whichever is larger)
            risk = current_price - stop_loss
            profit_target_min = current_price + (risk * 1.5)  # 1.5:1 R:R minimum
            profit_target_breakout = level_price + (atr_5m * 0.5)  # Above resistance + buffer
            take_profit = max(profit_target_min, profit_target_breakout)
            
            # Expected move based on level strength (stronger levels = bigger moves)
            expected_move_pct = min(
                (level_strength / 100.0) * 0.02,  # Up to 2% for 100% strength
                0.025  # Cap at 2.5%
            )
            
            # Calculate risk:reward ratio for position sizing
            risk = abs(current_price - stop_loss)
            reward = abs(take_profit - current_price)
            risk_reward_ratio = reward / risk if risk > 0 else 0.0
            
            signal = MomentumSignal(
                direction="LONG",
                confidence=min(confidence, 100.0),
                entry_price=current_price,  # Market order at current price
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=factors,
                detected_at=time.time(),
                breakout_level=level_price,
                expected_move_pct=expected_move_pct,
                risk_reward_ratio=risk_reward_ratio
            )
            
            # Check cooldown
            if self._is_in_cooldown(signal):
                logger.debug(f"⚡ LONG signal in cooldown (resistance @ ${level_price:.2f})")
                return None
            
            logger.info(f"⚡ LONG breakout detected! Resistance @ ${level_price:.2f}, confidence: {confidence:.1f}%")
            self._recent_signals.append(signal)
            return signal
        
        return None
    
    def _check_short_breakout(
        self,
        current_price: float,
        support_levels: List[Dict[str, Any]],
        pressure_data: Dict[str, Any],
        volume_data: Dict[str, Any],
        rsi_data: Dict[str, Any],
        volatility_data: Dict[str, Any],
        trend_data: Dict[str, Any],
        atr_5m: float
    ) -> Optional[MomentumSignal]:
        """Check for SHORT breakout (breakdown below support)"""
        if not support_levels:
            return None
        
        # Find closest strong support (NO FALLBACKS)
        support_levels.sort(key=lambda x: (current_price - x["price_level"], -x["strength_score"]))
        
        for support in support_levels:
            level_price = support["price_level"]
            level_strength = support["strength_score"]
            
            if level_price <= 0 or level_price >= current_price:
                continue
            
            # Check if price is within breakdown range (0.3-1% from support)
            distance_to_level = (current_price - level_price) / current_price
            if distance_to_level < 0.003 or distance_to_level > 0.01:  # 0.3% to 1%
                continue
            
            # Only consider strong levels (strength >= 60)
            if level_strength < 60:
                continue
            
            # Build signal factors (mirror of LONG logic)
            factors = []
            confidence = 0.0
            
            # 1. S/R proximity (20 points)
            if distance_to_level < 0.005:
                confidence += 20.0
                factors.append(f"Price near strong support ${level_price:.2f} ({distance_to_level*100:.2f}% away)")
            else:
                confidence += 15.0
                factors.append(f"Price approaching support ${level_price:.2f} ({distance_to_level*100:.2f}% away)")
            
            # 2. Orderbook pressure (25 points)
            pressure_direction = pressure_data["direction"]  # Required (NO FALLBACKS)
            pressure_strength = pressure_data["strength"]  # Required (NO FALLBACKS)
            net_pressure = pressure_data["net_pressure"]  # Required (NO FALLBACKS)
            
            if pressure_direction in ["STRONG_SELL", "SELL"] and pressure_strength > 0.7:
                confidence += 25.0
                factors.append(f"Strong sell pressure (strength: {pressure_strength:.2f})")
            elif pressure_direction == "SELL" and pressure_strength > 0.5:
                confidence += 15.0
                factors.append(f"Sell pressure building (strength: {pressure_strength:.2f})")
            elif net_pressure < -0.3:
                confidence += 10.0
                factors.append(f"Sell pressure detected (net: {net_pressure:.3f})")
            else:
                factors.append("No significant sell pressure")
            
            # 3. Volume surge (20 points)
            volume_category = volume_data["category"]  # Required (NO FALLBACKS)
            volume_percentile = volume_data["percentile"]  # Required (NO FALLBACKS)
            
            if volume_category in ["HIGH", "VERY_HIGH"] and volume_percentile > 75:
                confidence += 20.0
                factors.append(f"Volume surge ({volume_category}, {volume_percentile:.0f}th percentile)")
            elif volume_percentile > 60:
                confidence += 10.0
                factors.append(f"Above-average volume ({volume_percentile:.0f}th percentile)")
            else:
                factors.append(f"Normal volume ({volume_percentile:.0f}th percentile)")
            
            # 4. Price acceleration (15 points)
            trend_direction = trend_data["direction"]  # Required (NO FALLBACKS)
            trend_strength_raw = trend_data["strength"]  # Required (NO FALLBACKS)
            try:
                trend_strength = abs(float(trend_strength_raw)) if trend_strength_raw is not None else 0.0
            except (ValueError, TypeError):
                trend_strength = 0.0
            
            if trend_direction == "BEARISH" and trend_strength > 0.005:
                confidence += 15.0
                factors.append(f"Bearish momentum ({trend_strength*100:.2f}% strength)")
            elif trend_direction == "BEARISH":
                confidence += 8.0
                factors.append("Slight bearish bias")
            else:
                factors.append(f"Trend: {trend_direction}")
            
            # 5. RSI momentum (10 points)
            rsi_value = rsi_data["rsi"]  # Required (NO FALLBACKS) - RSI calculator returns "rsi" key, not "value"
            if TechnicalAnalysisConstants.RSI_OVERSOLD < rsi_value < TechnicalAnalysisConstants.RSI_NEUTRAL:  # Bearish but not oversold
                confidence += 10.0
                factors.append(f"RSI bearish ({rsi_value:.1f})")
            elif rsi_value <= TechnicalAnalysisConstants.RSI_OVERSOLD:
                confidence -= 5.0  # Oversold - reduce confidence
                factors.append(f"RSI oversold ({rsi_value:.1f})")
            else:
                factors.append(f"RSI: {rsi_value:.1f}")
            
            # 6. Volatility check (10 points)
            volatility_category = volatility_data["category"]  # Required (NO FALLBACKS)
            if volatility_category in ["HIGH", "EXTREME"]:
                confidence += 10.0
                factors.append(f"High volatility ({volatility_category})")
            else:
                factors.append(f"Volatility: {volatility_category}")
            
            # Minimum confidence threshold
            if confidence < 60.0:
                logger.debug(f"⚡ SHORT breakdown signal too weak: {confidence:.1f}% (support @ ${level_price:.2f})")
                continue
            
            # Calculate stop loss and take profit
            # Stop: above support (or 2xATR, whichever is more conservative)
            stop_loss = min(
                current_price + (atr_5m * 2.0),  # Risk-based: 2xATR
                current_price * 1.01  # Max 1% stop
            )
            
            # Take profit: below support - buffer (or 1.5x risk, whichever is larger)
            risk = stop_loss - current_price
            profit_target_min = current_price - (risk * 1.5)  # 1.5:1 R:R minimum
            profit_target_breakdown = level_price - (atr_5m * 0.5)  # Below support - buffer
            take_profit = min(profit_target_min, profit_target_breakdown)
            
            # Expected move
            expected_move_pct = min(
                (level_strength / 100.0) * 0.02,
                0.025
            )
            
            # Calculate risk:reward ratio for position sizing
            risk = abs(stop_loss - current_price)
            reward = abs(current_price - take_profit)
            risk_reward_ratio = reward / risk if risk > 0 else 0.0
            
            signal = MomentumSignal(
                direction="SHORT",
                confidence=min(confidence, 100.0),
                entry_price=current_price,  # Market order at current price
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=factors,
                detected_at=time.time(),
                breakout_level=level_price,
                expected_move_pct=expected_move_pct,
                risk_reward_ratio=risk_reward_ratio
            )
            
            # Check cooldown
            if self._is_in_cooldown(signal):
                logger.debug(f"⚡ SHORT signal in cooldown (support @ ${level_price:.2f})")
                return None
            
            logger.info(f"⚡ SHORT breakdown detected! Support @ ${level_price:.2f}, confidence: {confidence:.1f}%")
            self._recent_signals.append(signal)
            return signal
        
        return None
    
    def _is_in_cooldown(self, signal: MomentumSignal) -> bool:
        """Check if signal is in cooldown period"""
        current_time = time.time()
        for recent_signal in reversed(self._recent_signals[-10:]):  # Check last 10 signals
            if recent_signal.direction == signal.direction:
                time_since = current_time - recent_signal.detected_at
                if time_since < self._signal_cooldown:
                    return True
        return False