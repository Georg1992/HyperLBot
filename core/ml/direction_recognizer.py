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
        Recognize market direction using multiple signals with proper weighting
        
        Returns:
            (direction, score, reasoning)
            - direction: "LONG" or "SHORT" (never NEUTRAL)
            - score: -1.0 (strong SHORT) to +1.0 (strong LONG) - normalized weighted score
            - reasoning: List of human-readable reasons
        """
        reasoning = []
        
        # Check if we're in a low-volatility range trading scenario
        volatility_category = market_data.get("volatility_category", "MODERATE")
        volatility_5m = market_data.get("volatility_5m", 0.0)
        is_range_trading = volatility_category in ["LOW", "VERY_LOW"] and volatility_5m < 0.01
        
        # Define weights based on market regime
        if is_range_trading:
            # Range trading: RSI and S/R are most important (mean reversion)
            weights = {
                "rsi": 0.30,
                "sr": 0.30,
                "pattern": 0.18,
                "psychological": 0.12,  # Psychological levels important in ranging markets
                "trend": 0.05,  # Less important in ranging markets
                "pressure": 0.05
            }
        else:
            # Trending: Trends and S/R matter more (momentum)
            weights = {
                "rsi": 0.25,
                "sr": 0.25,
                "pattern": 0.15,
                "psychological": 0.10,  # Psychological levels also matter in trends
                "trend": 0.15,  # More important in trending markets
                "pressure": 0.10
            }
        
        # Collect raw scores from each analysis (normalized to -1.0 to +1.0)
        rsi_score_raw, rsi_reasoning = self._analyze_rsi(market_data, is_range_trading)
        trend_score_raw, trend_reasoning = self._analyze_trends(market_data)
        sr_score_raw, sr_reasoning = self._analyze_support_resistance(market_data, is_range_trading)
        pattern_score_raw, pattern_reasoning = self._analyze_patterns(market_data, is_range_trading)
        psychological_score_raw, psychological_reasoning = self._analyze_psychological_levels(market_data, is_range_trading)
        
        # Normalize raw scores to [-1.0, +1.0] range
        # RSI typically gives ±0.35, normalize to ±1.0
        rsi_score = max(-1.0, min(1.0, rsi_score_raw / 0.35 if abs(rsi_score_raw) > 0 else 0.0))
        # Trend typically gives ±0.10, normalize to ±1.0
        trend_score = max(-1.0, min(1.0, trend_score_raw / 0.10 if abs(trend_score_raw) > 0 else 0.0))
        # S/R typically gives ±0.35, normalize to ±1.0
        sr_score = max(-1.0, min(1.0, sr_score_raw / 0.35 if abs(sr_score_raw) > 0 else 0.0))
        # Pattern already capped at ±0.20, normalize to ±1.0
        pattern_score = max(-1.0, min(1.0, pattern_score_raw / 0.20 if abs(pattern_score_raw) > 0 else 0.0))
        # Psychological typically gives ±0.20, normalize to ±1.0
        psychological_score = max(-1.0, min(1.0, psychological_score_raw / 0.20 if abs(psychological_score_raw) > 0 else 0.0))
        
        # Calculate weighted score
        weighted_score = (
            rsi_score * weights["rsi"] +
            sr_score * weights["sr"] +
            pattern_score * weights["pattern"] +
            psychological_score * weights["psychological"] +
            trend_score * weights["trend"]
        )
        
        # Determine initial direction (before pressure confirmation)
        if forced_direction:
            direction = forced_direction
            reasoning.append(f"🎯 Forced direction: {forced_direction}")
        elif weighted_score >= 0:
            direction = "LONG"
        else:
            direction = "SHORT"
        
        # Add pressure confirmation (affects confidence, not base direction much)
        pressure_score_raw, pressure_reasoning = self._analyze_pressure(market_data, direction)
        # Pressure is small, normalize and apply with small weight
        pressure_score = max(-1.0, min(1.0, pressure_score_raw / 0.05 if abs(pressure_score_raw) > 0 else 0.0))
        
        # Final weighted score with pressure
        final_score = weighted_score + (pressure_score * weights["pressure"])
        
        # Clamp final score
        final_score = max(-1.0, min(1.0, final_score))
        
        # Add all reasoning
        reasoning.extend(rsi_reasoning)
        reasoning.extend(sr_reasoning)
        reasoning.extend(pattern_reasoning)
        reasoning.extend(psychological_reasoning)
        reasoning.extend(trend_reasoning)
        reasoning.extend(pressure_reasoning)
        
        # Add summary
        score_str = f"{final_score:+.3f}"
        reasoning.append(f"📊 Final weighted score: {score_str} | RSI:{weights['rsi']:.0%} S/R:{weights['sr']:.0%} Pattern:{weights['pattern']:.0%} Psychological:{weights['psychological']:.0%} Trend:{weights['trend']:.0%} Pressure:{weights['pressure']:.0%}")
        
        logger.info(f"🎯 Direction: {direction} (weighted score: {final_score:+.3f}, regime: {'RANGE' if is_range_trading else 'TREND'})")
        
        return direction, final_score, reasoning
    
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
    
    def _analyze_psychological_levels(self, market_data: Dict[str, Any], is_range_trading: bool) -> Tuple[float, List[str]]:
        """
        Analyze psychological price levels (round numbers, significant thresholds)
        
        Psychological levels are important because:
        - Traders place orders at round numbers ($100k, $105k, etc.)
        - These levels often act as support/resistance
        - Price can bounce or get stuck near these levels
        """
        score = 0.0
        reasoning = []
        
        current_price = market_data.get("current_price", 0)
        if not current_price or current_price <= 0:
            return score, reasoning
        
        # Detect psychological levels based on current price range
        # For BTC, psychological levels are typically:
        # - Major round numbers: 100k, 110k, 120k, etc.
        # - Half-way points: 105k, 115k, 125k, etc.
        # - Smaller round numbers when price is high: 102k, 103k, 107k, etc.
        
        # Determine the magnitude for round numbers based on price
        if current_price >= 100000:
            # For prices >= 100k, round to nearest 1k, 2.5k, 5k, 10k
            round_levels = [
                1000,    # Every 1k: 100k, 101k, 102k...
                2500,    # Every 2.5k: 100k, 102.5k, 105k...
                5000,    # Every 5k: 100k, 105k, 110k...
                10000,   # Every 10k: 100k, 110k, 120k...
            ]
        elif current_price >= 10000:
            # For prices 10k-100k, round to nearest 100, 250, 500, 1000
            round_levels = [
                100,     # Every 100
                250,     # Every 250
                500,     # Every 500
                1000,    # Every 1k
            ]
        else:
            # For lower prices, round to nearest 10, 25, 50, 100
            round_levels = [
                10,
                25,
                50,
                100,
            ]
        
        # Find nearest psychological levels above and below
        nearest_support_psych = None
        nearest_resistance_psych = None
        min_distance_support = float('inf')
        min_distance_resistance = float('inf')
        
        for round_level in round_levels:
            # Find levels below (support)
            level_below = (current_price // round_level) * round_level
            distance_below = current_price - level_below
            if 0 < distance_below < min_distance_support and level_below > 0:
                nearest_support_psych = level_below
                min_distance_support = distance_below
            
            # Find levels above (resistance)
            level_above = ((current_price // round_level) + 1) * round_level
            distance_above = level_above - current_price
            if 0 < distance_above < min_distance_resistance:
                nearest_resistance_psych = level_above
                min_distance_resistance = distance_above
        
        # Calculate proximity as percentage of price
        if nearest_support_psych:
            proximity_to_support_pct = (current_price - nearest_support_psych) / current_price
        else:
            proximity_to_support_pct = 1.0
        
        if nearest_resistance_psych:
            proximity_to_resistance_pct = (nearest_resistance_psych - current_price) / current_price
        else:
            proximity_to_resistance_pct = 1.0
        
        # Stronger signal when very close to psychological level
        # Use ATR or volatility for proximity threshold
        volatility_5m = market_data.get("volatility_5m", 0.01)
        atr_threshold = max(0.002, volatility_5m * 0.5)  # Within 50% of ATR
        
        if is_range_trading:
            # In range trading, psychological levels are very important
            if proximity_to_support_pct <= atr_threshold * 2:  # Within 2x ATR of support
                strength = 1.0 - (proximity_to_support_pct / (atr_threshold * 2))
                score += 0.20 * strength
                reasoning.append(f"🧠 Near psychological SUPPORT ${nearest_support_psych:,.0f} ({proximity_to_support_pct:.2%} away) - strong bounce potential")
            elif proximity_to_support_pct <= atr_threshold * 4:  # Within 4x ATR
                score += 0.10
                reasoning.append(f"🧠 Approaching psychological SUPPORT ${nearest_support_psych:,.0f} ({proximity_to_support_pct:.2%} away)")
            
            if proximity_to_resistance_pct <= atr_threshold * 2:  # Within 2x ATR of resistance
                strength = 1.0 - (proximity_to_resistance_pct / (atr_threshold * 2))
                score -= 0.20 * strength
                reasoning.append(f"🧠 Near psychological RESISTANCE ${nearest_resistance_psych:,.0f} ({proximity_to_resistance_pct:.2%} away) - strong rejection risk")
            elif proximity_to_resistance_pct <= atr_threshold * 4:  # Within 4x ATR
                score -= 0.10
                reasoning.append(f"🧠 Approaching psychological RESISTANCE ${nearest_resistance_psych:,.0f} ({proximity_to_resistance_pct:.2%} away)")
        else:
            # In trending markets, psychological levels act as magnets
            if proximity_to_support_pct <= atr_threshold * 3:
                strength = 1.0 - (proximity_to_support_pct / (atr_threshold * 3))
                score += 0.15 * strength
                reasoning.append(f"🧠 Near psychological SUPPORT ${nearest_support_psych:,.0f} ({proximity_to_support_pct:.2%} away) - support magnet")
            elif proximity_to_support_pct <= atr_threshold * 5:
                score += 0.08
                reasoning.append(f"🧠 Approaching psychological SUPPORT ${nearest_support_psych:,.0f}")
            
            if proximity_to_resistance_pct <= atr_threshold * 3:
                strength = 1.0 - (proximity_to_resistance_pct / (atr_threshold * 3))
                score -= 0.15 * strength
                reasoning.append(f"🧠 Near psychological RESISTANCE ${nearest_resistance_psych:,.0f} ({proximity_to_resistance_pct:.2%} away) - resistance magnet")
            elif proximity_to_resistance_pct <= atr_threshold * 5:
                score -= 0.08
                reasoning.append(f"🧠 Approaching psychological RESISTANCE ${nearest_resistance_psych:,.0f}")
        
        # Cap psychological score to prevent over-weighting
        score = max(-0.20, min(0.20, score))
        
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
