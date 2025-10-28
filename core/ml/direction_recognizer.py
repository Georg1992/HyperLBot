#!/usr/bin/env python3
"""
Direction Recognizer - SRP Compliant
Single Responsibility: Recognize market direction using technical analysis
"""

from typing import Dict, Any, List, Tuple, Optional
from loguru import logger


class DirectionRecognizer:
    """
    Single Responsibility: Recognize market direction using technical analysis
    
    WEIGHTS (optimized for high-leverage range trading):
    - RSI: 35% (PRIMARY - mean reversion signals)
    - S/R: 35% (Price position relative to key levels)
    - Patterns: 20% (Chart pattern setups)
    - Trend: 10% (15min: 3%, 2-hour: 7%)
    - Pressure: ~5% (Confirmation only)
    """
    
    def __init__(self):
        logger.info("🎯 Direction Recognizer initialized")
    
    def recognize_direction(self, market_data: Dict[str, Any], forced_direction: Optional[str] = None) -> Tuple[str, float, List[str]]:
        """
        Recognize market direction using multiple signals
        
        Returns:
            (direction, score, reasoning)
            - direction: "LONG" or "SHORT" (never NEUTRAL)
            - score: -1.0 (strong SHORT) to +1.0 (strong LONG)
            - reasoning: List of human-readable reasons
        """
        score = 0.0
        reasoning = []
        
        # Check if we're in a low-volatility range trading scenario
        volatility_category = market_data.get("volatility_category", "MODERATE")
        volatility_5m = market_data.get("volatility_5m", 0.0)
        is_range_trading = volatility_category in ["LOW", "VERY_LOW"] and volatility_5m < 0.01
        
        # 1. RSI ANALYSIS (Weight: 35% - PRIMARY for short-term mean reversion)
        rsi_score, rsi_reasoning = self._analyze_rsi(market_data, is_range_trading)
        score += rsi_score
        reasoning.extend(rsi_reasoning)
        
        # 2. DUAL-TIMEFRAME TREND ANALYSIS (Weight: 10%)
        trend_score, trend_reasoning = self._analyze_trends(market_data)
        score += trend_score
        reasoning.extend(trend_reasoning)
        
        # 3. SUPPORT/RESISTANCE (Weight: 35% for range trading, 30% for momentum)
        sr_score, sr_reasoning = self._analyze_support_resistance(market_data, is_range_trading)
        score += sr_score
        reasoning.extend(sr_reasoning)
        
        # 4. PATTERN ANALYSIS (Weight: up to 20% - pattern-specific)
        pattern_score, pattern_reasoning = self._analyze_patterns(market_data, is_range_trading)
        score += pattern_score
        reasoning.extend(pattern_reasoning)
        
        # Normalize score to -1.0 to 1.0 (before pressure confirmation)
        score = max(-1.0, min(1.0, score))
        
        # Determine initial direction (without pressure)
        if forced_direction:
            direction = forced_direction
            reasoning.append(f"🎯 Forced direction: {forced_direction}")
        elif score >= 0:
            direction = "LONG"
        else:
            direction = "SHORT"
        
        # 5. ORDERBOOK PRESSURE - MOMENTUM CONFIRMATION ONLY
        pressure_score, pressure_reasoning = self._analyze_pressure(market_data, direction)
        score += pressure_score
        reasoning.extend(pressure_reasoning)
        
        # Final normalization after pressure confirmation
        score = max(-1.0, min(1.0, score))
        
        logger.info(f"🎯 Direction: {direction} (score: {score:+.3f})")
        
        return direction, score, reasoning
    
    def _analyze_rsi(self, market_data: Dict[str, Any], is_range_trading: bool) -> Tuple[float, List[str]]:
        """Analyze RSI signals"""
        rsi_data = market_data.get("rsi", {})
        rsi = rsi_data.get("rsi", 50) if isinstance(rsi_data, dict) else rsi_data
        score = 0.0
        reasoning = []
        
        if is_range_trading:
            # For range trading: More sensitive RSI thresholds
            if rsi < 30:
                score += 0.35
                reasoning.append(f"🔴 RSI oversold ({rsi:.1f}) - STRONG BUY signal (range trading)")
            elif rsi < 45:
                score += 0.20
                reasoning.append(f"🟠 RSI below neutral ({rsi:.1f}) - bullish bias (range trading)")
            elif rsi < 55:
                score += 0.10
                reasoning.append(f"🟡 RSI slightly bullish ({rsi:.1f}) - weak long signal")
            elif rsi > 70:
                score -= 0.35
                reasoning.append(f"🔴 RSI overbought ({rsi:.1f}) - STRONG SELL signal (range trading)")
            elif rsi > 55:
                score -= 0.20
                reasoning.append(f"🟠 RSI above neutral ({rsi:.1f}) - bearish bias (range trading)")
            elif rsi > 45:
                score -= 0.10
                reasoning.append(f"🟡 RSI slightly bearish ({rsi:.1f}) - weak short signal")
            else:
                reasoning.append(f"⚪ RSI neutral ({rsi:.1f}) - range trading")
        else:
            # Original momentum trading thresholds
            if rsi < 25:
                score += 0.35
                reasoning.append(f"🔴 RSI extremely oversold ({rsi:.1f}) - STRONG BUY signal")
            elif rsi < 30:
                score += 0.25
                reasoning.append(f"🟠 RSI oversold ({rsi:.1f}) - strong reversal signal")
            elif rsi < 40:
                score += 0.15
                reasoning.append(f"🟡 RSI below neutral ({rsi:.1f}) - bullish bias")
            elif rsi > 75:
                score -= 0.35
                reasoning.append(f"🔴 RSI extremely overbought ({rsi:.1f}) - STRONG SELL signal")
            elif rsi > 70:
                score -= 0.25
                reasoning.append(f"🟠 RSI overbought ({rsi:.1f}) - strong reversal signal")
            elif rsi > 60:
                score -= 0.15
                reasoning.append(f"🟡 RSI above neutral ({rsi:.1f}) - bearish bias")
            else:
                reasoning.append(f"⚪ RSI neutral ({rsi:.1f})")
        
        return score, reasoning
    
    def _analyze_trends(self, market_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Analyze trend signals"""
        score = 0.0
        reasoning = []
        
        trend_short = market_data.get("trend_short", "SIDEWAYS")
        trend_medium = market_data.get("trend_medium", "SIDEWAYS")
        
        # Short-term trend - Momentum confirmation (3% weight)
        if "STRONG_UPTREND" in trend_short:
            score += 0.03
            reasoning.append("📈 Strong short-term momentum (15min)")
        elif "STRONG_DOWNTREND" in trend_short:
            score -= 0.03
            reasoning.append("📉 Strong short-term momentum (15min)")
        
        # Medium-term trend - Intraday direction (7% weight)
        if "STRONG_UPTREND" in trend_medium:
            score += 0.07
            reasoning.append("📈 Strong 2-hour uptrend")
        elif "UPTREND" in trend_medium and "WEAK" not in trend_medium:
            score += 0.04
            reasoning.append("📈 2-hour uptrend")
        elif "STRONG_DOWNTREND" in trend_medium:
            score -= 0.07
            reasoning.append("📉 Strong 2-hour downtrend")
        elif "DOWNTREND" in trend_medium and "WEAK" not in trend_medium:
            score -= 0.04
            reasoning.append("📉 2-hour downtrend")
        
        return score, reasoning
    
    def _analyze_support_resistance(self, market_data: Dict[str, Any], is_range_trading: bool) -> Tuple[float, List[str]]:
        """Analyze support/resistance signals"""
        score = 0.0
        reasoning = []
        
        current_price = market_data.get("current_price", 0)
        support_resistance = market_data.get("support_resistance", {})
        nearest_support = support_resistance.get("nearest_support", {})
        nearest_resistance = support_resistance.get("nearest_resistance", {})
        
        if nearest_support and nearest_resistance and current_price:
            support_price = nearest_support.get("price", 0)
            resistance_price = nearest_resistance.get("price", 0)
            
            if support_price and resistance_price:
                # Calculate position in range
                range_size = resistance_price - support_price
                if range_size > 0:
                    position_in_range = (current_price - support_price) / range_size
                    
                    if is_range_trading:
                        # For range trading: More sensitive thresholds and higher weights
                        if position_in_range < 0.20:  # Within 20% of support
                            score += 0.35
                            reasoning.append(f"🟢 Near support ${support_price:,.0f} - strong bounce potential (range trading)")
                        elif position_in_range < 0.35:  # Within 35% of support
                            score += 0.25
                            reasoning.append(f"🟢 Approaching support ${support_price:,.0f} - bounce potential")
                        elif position_in_range < 0.50:  # Lower half of range
                            score += 0.15
                            reasoning.append(f"🟡 Lower half of range - bullish bias")
                        elif position_in_range > 0.80:  # Within 20% of resistance
                            score -= 0.35
                            reasoning.append(f"🔴 Near resistance ${resistance_price:,.0f} - strong rejection risk (range trading)")
                        elif position_in_range > 0.65:  # Within 35% of resistance
                            score -= 0.25
                            reasoning.append(f"🔴 Approaching resistance ${resistance_price:,.0f} - rejection risk")
                        elif position_in_range > 0.50:  # Upper half of range
                            score -= 0.15
                            reasoning.append(f"🟡 Upper half of range - bearish bias")
                    else:
                        # Original momentum trading thresholds
                        if position_in_range < 0.15:
                            score += 0.30
                            reasoning.append(f"🟢 Near support ${support_price:,.0f} - bounce potential")
                        elif position_in_range < 0.30:
                            score += 0.18
                            reasoning.append(f"🟢 Approaching support ${support_price:,.0f}")
                        elif position_in_range > 0.85:
                            score -= 0.30
                            reasoning.append(f"🔴 Near resistance ${resistance_price:,.0f} - rejection risk")
                        elif position_in_range > 0.70:
                            score -= 0.18
                            reasoning.append(f"🔴 Approaching resistance ${resistance_price:,.0f}")
        
        return score, reasoning
    
    def _analyze_patterns(self, market_data: Dict[str, Any], is_range_trading: bool) -> Tuple[float, List[str]]:
        """Analyze pattern signals"""
        score = 0.0
        reasoning = []
        
        pattern_analysis = market_data.get("pattern_analysis", {})
        patterns_dict = pattern_analysis.get("patterns", {})
        
        # Pattern weights from PatternRecognitionEngine
        pattern_weights = {
            # Tier 1: Strong Reversal Patterns (18-20%)
            "HEAD_SHOULDERS": 0.20, "INVERSE_HEAD_SHOULDERS": 0.20,
            "DOUBLE_TOP": 0.18, "DOUBLE_BOTTOM": 0.18,
            # Tier 2: Triangle Patterns (14-16%)
            "ASCENDING_TRIANGLE": 0.16, "DESCENDING_TRIANGLE": 0.16,
            "SYMMETRIC_TRIANGLE": 0.14,
            # Tier 3: Wedge Patterns (14-16%)
            "FALLING_WEDGE": 0.16, "RISING_WEDGE": 0.16,
            # Tier 4: Engulfing Patterns (15%)
            "BULLISH_ENGULFING": 0.15, "BEARISH_ENGULFING": 0.15,
            # Tier 5: Three Soldiers/Crows (14%)
            "THREE_WHITE_SOLDIERS": 0.14, "THREE_BLACK_CROWS": 0.14,
            # Tier 6: Hammer/Shooting Star (12%)
            "HAMMER": 0.12, "INVERTED_HAMMER": 0.12,
            "SHOOTING_STAR": 0.12, "HANGING_MAN": 0.12,
            # Tier 7: Channel Patterns (10-12%)
            "ASCENDING_CHANNEL": 0.12, "DESCENDING_CHANNEL": 0.12,
            "HORIZONTAL_CHANNEL": 0.10,
            # Tier 8: Continuation Patterns (10%)
            "BULLISH_CONTINUATION": 0.10, "BEARISH_CONTINUATION": 0.10,
            "TREND_CHANGE": 0.10,
            # Tier 9: Doji Patterns (8%)
            "DOJI": 0.08, "DRAGONFLY_DOJI": 0.08, "GRAVESTONE_DOJI": 0.08,
        }
        
        # Apply pattern-specific weights
        pattern_score = 0
        for pattern_type, pattern_list in patterns_dict.items():
            if isinstance(pattern_list, list):
                for pattern in pattern_list:
                    pattern_name = pattern.get("pattern", "")
                    pattern_direction = pattern.get("direction", "NEUTRAL")
                    pattern_confidence = pattern.get("confidence", 0.5)
                    pattern_weight = pattern_weights.get(pattern_name, 0.10)  # Default 10%
                    
                    if pattern_direction == "BULLISH":
                        pattern_contribution = pattern_weight * pattern_confidence
                        pattern_score += pattern_contribution
                        reasoning.append(f"🟢 {pattern_name} (bullish, +{pattern_contribution*100:.1f}%)")
                    elif pattern_direction == "BEARISH":
                        pattern_contribution = pattern_weight * pattern_confidence
                        pattern_score -= pattern_contribution
                        reasoning.append(f"🔴 {pattern_name} (bearish, -{pattern_contribution*100:.1f}%)")
                    elif pattern_name == "TREND_CHANGE":
                        # Handle trend changes differently for range trading
                        if is_range_trading:
                            pattern_contribution = pattern_weight * pattern_confidence * 0.5  # Reduce impact
                            pattern_score += pattern_contribution
                            reasoning.append(f"🔄 {pattern_name} (trend change, +{pattern_contribution*100:.1f}%)")
                        else:
                            pattern_contribution = pattern_weight * pattern_confidence
                            pattern_score -= pattern_contribution
                            reasoning.append(f"🔄 {pattern_name} (trend change, -{pattern_contribution*100:.1f}%)")
                    elif pattern_direction == "NEUTRAL" and pattern_name == "DOJI":
                        reasoning.append(f"⚪ {pattern_name} (indecision)")
        
        # Apply pattern score (capped at ±0.20 to prevent over-weighting)
        pattern_score = max(-0.20, min(0.20, pattern_score))
        score += pattern_score
        
        return score, reasoning
    
    def _analyze_pressure(self, market_data: Dict[str, Any], direction: str) -> Tuple[float, List[str]]:
        """Analyze orderbook pressure signals"""
        score = 0.0
        reasoning = []
        
        pressure_data = market_data.get("pressure_data", {})
        pressure = pressure_data.get("direction", "NEUTRAL")
        
        # Check if pressure CONFIRMS the direction
        if direction == "LONG":
            if pressure == "STRONG_BUY":
                score += 0.05  # Reduced weight - confirmation only
                reasoning.append("✅ Strong buy pressure confirms LONG momentum")
            elif pressure == "BUY":
                score += 0.03
                reasoning.append("✅ Buy pressure confirms LONG momentum")
            elif pressure in ["SELL", "STRONG_SELL"]:
                reasoning.append("⚠️ Sell pressure contradicts LONG signal (caution)")
            else:
                reasoning.append("⚪ Neutral pressure (no confirmation)")
        
        elif direction == "SHORT":
            if pressure == "STRONG_SELL":
                score -= 0.05  # Reduced weight - confirmation only
                reasoning.append("✅ Strong sell pressure confirms SHORT momentum")
            elif pressure == "SELL":
                score -= 0.03
                reasoning.append("✅ Sell pressure confirms SHORT momentum")
            elif pressure in ["BUY", "STRONG_BUY"]:
                reasoning.append("⚠️ Buy pressure contradicts SHORT signal (caution)")
            else:
                reasoning.append("⚪ Neutral pressure (no confirmation)")
        
        return score, reasoning


# Global singleton
_global_direction_recognizer = None

def get_global_direction_recognizer() -> DirectionRecognizer:
    """Get global direction recognizer singleton"""
    global _global_direction_recognizer
    if _global_direction_recognizer is None:
        _global_direction_recognizer = DirectionRecognizer()
    return _global_direction_recognizer
