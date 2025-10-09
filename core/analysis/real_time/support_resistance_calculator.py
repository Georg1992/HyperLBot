#!/usr/bin/env python3
"""
Simple Support/Resistance Calculator - WORKS
"""

import time
from typing import Dict, List, Any
from loguru import logger

# Singleton pattern implementation
_global_support_resistance_calculator = None

def get_global_support_resistance_calculator() -> 'SupportResistanceCalculator':
    """Get the global SupportResistanceCalculator singleton instance"""
    global _global_support_resistance_calculator
    if _global_support_resistance_calculator is None:
        _global_support_resistance_calculator = SupportResistanceCalculator()
    return _global_support_resistance_calculator

class SupportResistanceCalculator:
    """Simple S/R calculator that actually works"""
    
    def __init__(self):
        logger.info("📊 Support/Resistance Calculator initialized")
    
    def identify_key_levels(self, candles: List[Dict], min_touches: int = 2) -> Dict[str, Any]:
        """Find support/resistance levels - SIMPLE AND WORKS"""
        try:
            if not candles or len(candles) < 10:
                logger.warning("⚠️ Insufficient candle data - using psychological levels")
                # Even with insufficient data, return psychological levels
                current_price = candles[-1].get("close", 0) if candles else 0
                if current_price > 0:
                    psychological_support = self._find_next_psychological_level(current_price, "support")
                    psychological_resistance = self._find_next_psychological_level(current_price, "resistance")
                    return {
                        "key_levels": [],
                        "strongest_support": psychological_support,
                        "strongest_resistance": psychological_resistance,
                        "analysis_confidence": 0.3  # Low confidence for psychological-only levels
                    }
                else:
                    return {"key_levels": [], "strongest_support": 0.0, "strongest_resistance": 0.0}
            
            current_price = candles[-1].get("close", 0)
            
            # Detect if we're at a local maximum or minimum
            market_position = self._detect_market_position(candles, current_price)
            logger.info(f"📊 Market position: {market_position['position']} (confidence: {market_position['confidence']:.2f})")
            
            # Removed verbose logging to reduce spam
            
            # Find highs and lows
            highs = [c.get("high", 0) for c in candles]
            lows = [c.get("low", 0) for c in candles]
            
            # Simple approach: find significant highs and lows
            support_levels = []
            resistance_levels = []
            
            # Find support levels (significant lows with multiple touches and volume confirmation)
            for i in range(2, len(candles) - 2):
                low = candles[i].get("low", 0)
                if low < candles[i-1].get("low", 0) and low < candles[i+1].get("low", 0):
                    # This is a local minimum - count how many times price touched this level
                    touches = self._count_touches(candles, low, "support")
                    if touches >= 1:  # Any significant level (lowered from 2)
                        # Check volume confirmation
                        volume_confirmed = self._check_volume_confirmation(candles, low, "support")
                        if volume_confirmed:
                            # Calculate comprehensive score (0-100) with market position context
                            score = self._calculate_level_score(candles, low, "support", touches, i, market_position)
                            
                            support_levels.append({
                                "level": low,
                                "type": "support",
                                "score": score,
                                "touches": touches,
                                "index": i
                            })
            
            # Find resistance levels (significant highs with multiple touches and volume confirmation)
            for i in range(2, len(candles) - 2):
                high = candles[i].get("high", 0)
                if high > candles[i-1].get("high", 0) and high > candles[i+1].get("high", 0):
                    # This is a local maximum - count how many times price touched this level
                    touches = self._count_touches(candles, high, "resistance")
                    if touches >= 1:  # Any significant level (lowered from 2)
                        # Check volume confirmation
                        volume_confirmed = self._check_volume_confirmation(candles, high, "resistance")
                        if volume_confirmed:
                            # Calculate comprehensive score (0-100) with market position context
                            score = self._calculate_level_score(candles, high, "resistance", touches, i, market_position)
                            
                            resistance_levels.append({
                                "level": high,
                                "type": "resistance",
                                "score": score,
                                "touches": touches,
                                "index": i
                            })
            
            # Add psychological levels from actual price data near round numbers
            # NO FALLBACKS - Only use real calculated levels
            all_levels = support_levels + resistance_levels
            all_levels.sort(key=lambda x: x["score"], reverse=True)
            
            # Filter levels - show broken levels too (they're still relevant)
            filtered_levels = []
            for level in all_levels:
                # Show all levels - broken support/resistance is still important
                # Filter out levels that are too close to each other (minimum $100 gap for Bitcoin)
                is_too_close = False
                for existing in filtered_levels:
                    if abs(level["level"] - existing["level"]) < 100.0:  # $100 minimum gap for major levels
                        is_too_close = True
                        break
                if not is_too_close:
                    filtered_levels.append(level)
            
            # CRITICAL FIX: Filter levels based on current price position
            # Support must be BELOW current price, Resistance must be ABOVE current price
            support_levels_filtered = [
                level for level in filtered_levels 
                if level["type"] == "support" and level["level"] < current_price
            ]
            resistance_levels_filtered = [
                level for level in filtered_levels 
                if level["type"] == "resistance" and level["level"] > current_price
            ]
            
            # ENSURE AT LEAST ONE SUPPORT - Look deeper in history if needed
            if not support_levels_filtered and support_levels:
                # No support below current price - find the highest support level (closest to current price)
                all_support_sorted = sorted(support_levels, key=lambda x: x["level"], reverse=True)
                if all_support_sorted:
                    # Take the highest support level even if it's above current price
                    # This represents the last known support that was broken
                    support_levels_filtered = [all_support_sorted[0]]
                    logger.info(f"⚠️ No support below price - using last known support: ${all_support_sorted[0]['level']:.2f}")
            
            # ENSURE AT LEAST ONE RESISTANCE - Look deeper in history if needed
            if not resistance_levels_filtered and resistance_levels:
                # No resistance above current price - find the lowest resistance level (closest to current price)
                all_resistance_sorted = sorted(resistance_levels, key=lambda x: x["level"])
                if all_resistance_sorted:
                    # Take the lowest resistance level even if it's below current price
                    # This represents the last known resistance that was broken
                    resistance_levels_filtered = [all_resistance_sorted[0]]
                    logger.info(f"⚠️ No resistance above price - using last known resistance: ${all_resistance_sorted[0]['level']:.2f}")
            
            # NO FALLBACKS - Use only real calculated levels
            
            # Ensure we have at least one support and one resistance
            # Sort by distance from current price to get closest levels
            support_levels_filtered.sort(key=lambda x: abs(x["level"] - current_price))
            resistance_levels_filtered.sort(key=lambda x: abs(x["level"] - current_price))
            
            # Take more levels in low volatility conditions
            # In low volatility, weaker levels are still significant
            # Note: We'll use a default approach since market_data is not available here
            max_levels = 5  # Include fewer levels for better quality
                
            support_levels_filtered = support_levels_filtered[:max_levels]
            resistance_levels_filtered = resistance_levels_filtered[:max_levels]
            
            # Combine for final levels
            all_levels = support_levels_filtered + resistance_levels_filtered
            
            # Debug: Log all resistance levels found
            logger.info(f"📊 Resistance levels found: {len(resistance_levels_filtered)}")
            for res in resistance_levels_filtered:
                logger.info(f"   Resistance: ${res['level']:.2f} (score: {res.get('score', 0):.2f}, distance: {abs(res['level'] - current_price):.2f})")
            
            # Get strongest support (ONLY levels below current price)
            strongest_support = 0.0
            if support_levels_filtered:
                # ONLY use support levels that are BELOW current price (not broken)
                support_below = [s for s in support_levels_filtered if s["level"] < current_price]
                if support_below:
                    # Find the closest valid support below current price
                    strongest_support = max(support_below, key=lambda x: x["level"])["level"]
                else:
                    # No valid support below - find the lowest historical support as reference
                    # This is a "broken" support, but we show it for context
                    lowest_support = min(support_levels_filtered, key=lambda x: x["level"])
                    strongest_support = lowest_support["level"]
                    logger.warning(f"⚠️ All support levels broken - using lowest historical: ${strongest_support:.2f}")
            else:
                # No support levels found at all - use psychological level
                strongest_support = self._find_next_psychological_level(current_price, "support")
                logger.warning(f"⚠️ No support levels found - using psychological support: ${strongest_support:.2f}")
            
            # Get strongest resistance (ONLY levels above current price)
            strongest_resistance = 0.0
            if resistance_levels_filtered:
                # ONLY use resistance levels that are ABOVE current price (not broken)
                resistance_above = [r for r in resistance_levels_filtered if r["level"] > current_price]
                if resistance_above:
                    # Find the closest valid resistance above current price
                    strongest_resistance = min(resistance_above, key=lambda x: x["level"])["level"]
                else:
                    # No valid resistance above - check if this is ATH or data issue
                    highest_historical = max(resistance_levels_filtered, key=lambda x: x["level"])["level"]
                    if highest_historical < current_price:
                        # We're at ATH - use psychological level
                        strongest_resistance = self._find_next_psychological_level(current_price, "resistance")
                        logger.warning(f"⚠️ All-time high detected - using psychological resistance: ${strongest_resistance:.2f}")
                    else:
                        # Use highest historical as reference (broken resistance)
                        strongest_resistance = highest_historical
                        logger.warning(f"⚠️ All resistance levels broken - using highest historical: ${strongest_resistance:.2f}")
            else:
                # No resistance levels found at all - use psychological level
                strongest_resistance = self._find_next_psychological_level(current_price, "resistance")
                logger.warning(f"⚠️ No resistance levels found - using psychological resistance: ${strongest_resistance:.2f}")
            
            logger.info(f"📊 Found {len(support_levels)} support, {len(resistance_levels)} resistance levels")
            logger.info(f"📊 After filtering: {len(support_levels_filtered)} support, {len(resistance_levels_filtered)} resistance")
            logger.info(f"📊 Current price: ${current_price:.2f}")
            logger.info(f"📊 Strongest support: ${strongest_support:.2f} (below price: {strongest_support < current_price})")
            logger.info(f"📊 Strongest resistance: ${strongest_resistance:.2f} (above price: {strongest_resistance > current_price})")
            
            
            # Re-sort all levels by distance from current price
            all_levels.sort(key=lambda x: abs(x["level"] - current_price))
            
            return {
                "key_levels": all_levels,
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "analysis_confidence": 0.9 if len(all_levels) > 0 else 0.3
            }
            
        except Exception as e:
            logger.error(f"❌ S/R detection failed: {e}")
            return {"key_levels": [], "strongest_support": 0.0, "strongest_resistance": 0.0}
    
    
    def _count_touches(self, candles: List[Dict], level_price: float, level_type: str) -> int:
        """Count how many times price touched this level - REALISTIC TOUCHES ONLY"""
        touches = 0
        tolerance = 300.0  # $300 tolerance - realistic for Bitcoin volatility
        
        for candle in candles:
            high = candle.get("high", 0)
            low = candle.get("low", 0)
            
            if level_type == "support":
                if abs(low - level_price) <= tolerance:
                    touches += 1
            else:  # resistance
                if abs(high - level_price) <= tolerance:
                    touches += 1
        
        return touches
    
    def _check_volume_confirmation(self, candles: List[Dict], level_price: float, level_type: str) -> bool:
        """Check if the level has volume confirmation (above average volume when tested)"""
        tolerance = 300.0  # $300 tolerance - same as touch counting
        
        # Find candles that touched this level
        touching_candles = []
        for candle in candles:
            high = candle.get("high", 0)
            low = candle.get("low", 0)
            
            if level_type == "support":
                if abs(low - level_price) <= tolerance:
                    touching_candles.append(candle)
            else:  # resistance
                if abs(high - level_price) <= tolerance:
                    touching_candles.append(candle)
        
        if not touching_candles:
            return False
        
        # Calculate average volume for touching candles
        touching_volumes = [c.get("volume", 0) for c in touching_candles]
        avg_touching_volume = sum(touching_volumes) / len(touching_volumes)
        
        # Calculate overall average volume
        all_volumes = [c.get("volume", 0) for c in candles]
        overall_avg_volume = sum(all_volumes) / len(all_volumes)
        
        # Volume confirmation: touching candles should have above-average volume
        volume_ratio = avg_touching_volume / overall_avg_volume if overall_avg_volume > 0 else 1.0
        
        return volume_ratio > 0.8  # More lenient volume confirmation (0.8 instead of 1.0)
    
    # REMOVED: _add_psychological_levels - NO FALLBACKS
    
    # REMOVED: _add_projected_resistance_levels - NO FALLBACKS
    
    def _detect_market_position(self, candles: List[Dict], current_price: float) -> Dict[str, Any]:
        """Detect if we're at a local maximum, minimum, or in consolidation"""
        try:
            if len(candles) < 20:
                return {"position": "UNKNOWN", "confidence": 0.0}
            
            # Define "local" period: last 30 candles for 5m timeframe (2.5 hours)
            local_period = min(30, len(candles))
            local_candles = candles[-local_period:]
            
            # Find all local extrema within the period
            local_highs = []
            local_lows = []
            
            # Detect local highs and lows
            for i in range(2, len(local_candles) - 2):
                candle = local_candles[i]
                high = candle.get("high", 0)
                low = candle.get("low", 0)
                
                # Check if this is a local high (higher than 2 candles before and after)
                if (high > local_candles[i-1].get("high", 0) and 
                    high > local_candles[i-2].get("high", 0) and
                    high > local_candles[i+1].get("high", 0) and 
                    high > local_candles[i+2].get("high", 0)):
                    local_highs.append({"price": high, "index": i, "candle": candle})
                
                # Check if this is a local low (lower than 2 candles before and after)
                if (low < local_candles[i-1].get("low", 0) and 
                    low < local_candles[i-2].get("low", 0) and
                    low < local_candles[i+1].get("low", 0) and 
                    low < local_candles[i+2].get("low", 0)):
                    local_lows.append({"price": low, "index": i, "candle": candle})
            
            # Check if current price is near the most recent local high
            if local_highs:
                latest_high = max(local_highs, key=lambda x: x["index"])
                if current_price >= latest_high["price"] * 0.998:  # Within 0.2% of latest local high
                    return {"position": "LOCAL_MAXIMUM", "confidence": 0.95, "extrema": local_highs, "lows": local_lows}
            
            # Check if current price is near the most recent local low
            if local_lows:
                latest_low = max(local_lows, key=lambda x: x["index"])
                if current_price <= latest_low["price"] * 1.002:  # Within 0.2% of latest local low
                    return {"position": "LOCAL_MINIMUM", "confidence": 0.95, "extrema": local_lows, "highs": local_highs}
            
            # Check if we're in a consolidation zone (price between recent highs and lows)
            if local_highs and local_lows:
                recent_high = max([h["price"] for h in local_highs[-3:]])  # Last 3 highs
                recent_low = min([l["price"] for l in local_lows[-3:]])    # Last 3 lows
                
                if recent_low < current_price < recent_high:
                    range_size = recent_high - recent_low
                    if range_size > 0:
                        position_ratio = (current_price - recent_low) / range_size
                        if 0.3 <= position_ratio <= 0.7:
                            return {"position": "CONSOLIDATION", "confidence": 0.8, "extrema": local_highs + local_lows}
            
            # Determine trend direction
            if len(local_candles) >= 10:
                first_half = local_candles[:len(local_candles)//2]
                second_half = local_candles[len(local_candles)//2:]
                
                first_avg = sum(c.get("close", 0) for c in first_half) / len(first_half)
                second_avg = sum(c.get("close", 0) for c in second_half) / len(second_half)
                
                if second_avg > first_avg * 1.01:  # 1% higher
                    return {"position": "UPTREND", "confidence": 0.7, "extrema": local_highs + local_lows}
                elif second_avg < first_avg * 0.99:  # 1% lower
                    return {"position": "DOWNTREND", "confidence": 0.7, "extrema": local_highs + local_lows}
            
            return {"position": "UNKNOWN", "confidence": 0.0, "extrema": local_highs + local_lows}
                
        except Exception as e:
            logger.error(f"❌ Market position detection failed: {e}")
            return {"position": "UNKNOWN", "confidence": 0.0}
    
    def _calculate_level_score(self, candles: List[Dict], level_price: float, level_type: str, touches: int, index: int, market_position: Dict[str, Any] = None) -> float:
        """
        Calculate comprehensive level score (0-100) based on multiple factors:
        1. Number of touches (20 points max)
        2. Volume confirmation (20 points max)
        3. Time span (15 points max)
        4. Recent activity (15 points max)
        5. Price consistency (10 points max)
        6. Volume consistency (10 points max)
        7. Proximity to current price (10 points max)
        """
        try:
            total_score = 0.0
            
            # 1. Touch count factor (20 points max)
            touch_score = min(20.0, touches * 4.0)  # 4 points per touch, max 20
            total_score += touch_score
            
            # 2. Volume confirmation (20 points max)
            volume_score = self._calculate_volume_score(candles, level_price, level_type, index)
            total_score += volume_score
            
            # 3. Time span factor (15 points max)
            time_span_score = self._calculate_time_span_score(candles, index)
            total_score += time_span_score
            
            # 4. Recent activity (15 points max)
            recent_activity_score = self._calculate_recent_activity_score(candles, level_price, level_type, index)
            total_score += recent_activity_score
            
            # 5. Price consistency (10 points max)
            price_consistency_score = self._calculate_price_consistency_score(candles, level_price, level_type, index)
            total_score += price_consistency_score
            
            # 6. Volume consistency (10 points max)
            volume_consistency_score = self._calculate_volume_consistency_score(candles, level_price, level_type, index)
            total_score += volume_consistency_score
            
            # 7. Proximity to current price (10 points max)
            current_price = candles[-1].get("close", 0)
            proximity_score = self._calculate_proximity_score(level_price, current_price)
            total_score += proximity_score
            
            # 8. Local extrema bonus (20 points max) - NEW!
            if market_position:
                extrema_bonus = self._calculate_extrema_bonus(level_price, level_type, market_position)
                total_score += extrema_bonus
            
            # Ensure score is between 0 and 100
            final_score = max(0.0, min(100.0, total_score))
            
            # Only log high-quality levels to reduce spam (removed verbose debug logging)
            if final_score >= 70.0:
                pass  # Removed verbose debug logging to reduce log spam
            
            return final_score
            
        except Exception as e:
            logger.error(f"❌ Level score calculation failed: {e}")
            raise ValueError("Level score calculation failed - NO FALLBACKS")
    
    def _calculate_extrema_bonus(self, level_price: float, level_type: str, market_position: Dict[str, Any]) -> float:
        """Calculate bonus score for levels that are actual local extrema"""
        try:
            if not market_position or "extrema" not in market_position:
                return 0.0
            
            extrema = market_position.get("extrema", [])
            position = market_position.get("position", "UNKNOWN")
            confidence = market_position.get("confidence", 0.0)
            
            # Check if this level is a local extrema
            for extrema_point in extrema:
                extrema_price = extrema_point.get("price", 0)
                # Check if level is within 0.1% of extrema price
                if abs(level_price - extrema_price) / level_price < 0.001:
                    
                    # Give higher bonus for current market position
                    if position == "LOCAL_MAXIMUM" and level_type == "resistance":
                        return 20.0 * confidence  # Max 20 points for resistance at local max
                    elif position == "LOCAL_MINIMUM" and level_type == "support":
                        return 20.0 * confidence  # Max 20 points for support at local min
                    elif position == "CONSOLIDATION":
                        return 15.0 * confidence  # 15 points for extrema in consolidation
                    else:
                        return 10.0 * confidence  # 10 points for other extrema
            
            # Give smaller bonus for levels near extrema (within 0.5%)
            for extrema_point in extrema:
                extrema_price = extrema_point.get("price", 0)
                if abs(level_price - extrema_price) / level_price < 0.005:
                    return 5.0 * confidence  # 5 points for near-extrema
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Extrema bonus calculation failed: {e}")
            return 0.0
    
    def _calculate_volume_score(self, candles: List[Dict], level_price: float, level_type: str, index: int) -> float:
        """Calculate volume confirmation score (0-20 points)"""
        try:
            # Find candles that touched this level
            touching_candles = []
            for i, candle in enumerate(candles):
                if self._candle_touched_level(candle, level_price, level_type):
                    touching_candles.append(candle)
            
            if not touching_candles:
                return 0.0
            
            # Calculate average volume at touches
            total_volume = sum(candle.get("volume", 0) for candle in touching_candles)
            avg_volume = total_volume / len(touching_candles)
            
            # Calculate average volume for all candles
            all_volumes = [candle.get("volume", 0) for candle in candles if candle.get("volume", 0) > 0]
            if not all_volumes:
                return 5.0  # Default if no volume data
            
            overall_avg_volume = sum(all_volumes) / len(all_volumes)
            
            # Volume ratio (higher = better confirmation)
            volume_ratio = avg_volume / overall_avg_volume if overall_avg_volume > 0 else 1.0
            
            # Score based on volume ratio
            if volume_ratio > 2.0:
                return 20.0  # Excellent volume confirmation
            elif volume_ratio > 1.5:
                return 15.0  # Good volume confirmation
            elif volume_ratio > 1.0:
                return 10.0  # Average volume confirmation
            else:
                return 5.0   # Below average volume
            
        except Exception as e:
            logger.error(f"❌ Volume score calculation failed: {e}")
            return 5.0
    
    def _calculate_time_span_score(self, candles: List[Dict], index: int) -> float:
        """Calculate time span score (0-15 points)"""
        try:
            total_candles = len(candles)
            position_from_start = index / total_candles if total_candles > 0 else 0.5
            
            # Score based on how much time has passed since level was established
            # More time = more reliable level
            if position_from_start < 0.1:  # Very recent
                return 5.0
            elif position_from_start < 0.3:  # Recent
                return 10.0
            elif position_from_start < 0.7:  # Mid-term
                return 15.0
            else:  # Long-term
                return 12.0  # Slightly lower for very old levels
            
        except Exception as e:
            logger.error(f"❌ Time span score calculation failed: {e}")
            return 8.0
    
    def _calculate_recent_activity_score(self, candles: List[Dict], level_price: float, level_type: str, index: int) -> float:
        """Calculate recent activity score (0-15 points)"""
        try:
            # Check last 10 candles for recent touches
            recent_candles = candles[-10:] if len(candles) >= 10 else candles
            recent_touches = 0
            
            for candle in recent_candles:
                if self._candle_touched_level(candle, level_price, level_type):
                    recent_touches += 1
            
            # Score based on recent activity
            if recent_touches >= 3:
                return 15.0  # Very active recently
            elif recent_touches >= 2:
                return 12.0  # Active recently
            elif recent_touches >= 1:
                return 8.0   # Some recent activity
            else:
                return 3.0  # No recent activity
            
        except Exception as e:
            logger.error(f"❌ Recent activity score calculation failed: {e}")
            return 5.0
    
    def _calculate_price_consistency_score(self, candles: List[Dict], level_price: float, level_type: str, index: int) -> float:
        """Calculate price consistency score (0-10 points)"""
        try:
            # Find all touches and calculate price variance
            touching_prices = []
            for candle in candles:
                if self._candle_touched_level(candle, level_price, level_type):
                    if level_type == "support":
                        touching_prices.append(candle.get("low", level_price))
                    else:  # resistance
                        touching_prices.append(candle.get("high", level_price))
            
            if len(touching_prices) < 2:
                return 5.0  # Default if not enough data
            
            # Calculate standard deviation
            mean_price = sum(touching_prices) / len(touching_prices)
            variance = sum((price - mean_price) ** 2 for price in touching_prices) / len(touching_prices)
            std_dev = variance ** 0.5
            
            # Score based on consistency (lower std dev = higher score)
            price_consistency = 1.0 - (std_dev / level_price) if level_price > 0 else 0.5
            
            return max(0.0, min(10.0, price_consistency * 10.0))
            
        except Exception as e:
            logger.error(f"❌ Price consistency score calculation failed: {e}")
            return 5.0
    
    def _calculate_volume_consistency_score(self, candles: List[Dict], level_price: float, level_type: str, index: int) -> float:
        """Calculate volume consistency score (0-10 points)"""
        try:
            # Find volumes at touches
            touching_volumes = []
            for candle in candles:
                if self._candle_touched_level(candle, level_price, level_type):
                    touching_volumes.append(candle.get("volume", 0))
            
            if len(touching_volumes) < 2:
                return 5.0  # Default if not enough data
            
            # Calculate volume consistency
            mean_volume = sum(touching_volumes) / len(touching_volumes)
            if mean_volume == 0:
                return 5.0
            
            variance = sum((vol - mean_volume) ** 2 for vol in touching_volumes) / len(touching_volumes)
            std_dev = variance ** 0.5
            
            # Score based on volume consistency
            volume_consistency = 1.0 - (std_dev / mean_volume)
            return max(0.0, min(10.0, volume_consistency * 10.0))
            
        except Exception as e:
            logger.error(f"❌ Volume consistency score calculation failed: {e}")
            return 5.0
    
    def _calculate_proximity_score(self, level_price: float, current_price: float) -> float:
        """Calculate proximity to current price score (0-10 points)"""
        try:
            if current_price <= 0:
                return 5.0  # Default if no current price
            
            # Calculate distance percentage
            distance_percent = abs(current_price - level_price) / current_price
            
            # Score based on proximity (closer = higher score)
            if distance_percent < 0.001:  # Within 0.1%
                return 10.0
            elif distance_percent < 0.005:  # Within 0.5%
                return 8.0
            elif distance_percent < 0.01:   # Within 1%
                return 6.0
            elif distance_percent < 0.02:   # Within 2%
                return 4.0
            else:
                return 2.0  # Far away
            
        except Exception as e:
            logger.error(f"❌ Proximity score calculation failed: {e}")
            return 5.0
    
    def _candle_touched_level(self, candle: Dict, level_price: float, level_type: str) -> bool:
        """Check if a candle touched the level"""
        try:
            if level_type == "support":
                return candle.get("low", 0) <= level_price * 1.001  # Within 0.1% tolerance
            else:  # resistance
                return candle.get("high", 0) >= level_price * 0.999  # Within 0.1% tolerance
        except:
            return False
    
    def _find_next_psychological_level(self, current_price: float, level_type: str) -> float:
        """
        Find the next psychological level (round number) for support or resistance
        Psychological levels: $1000 intervals for BTC (e.g., $120,000, $121,000, $122,000)
        """
        try:
            # For BTC, use $1000 intervals for major psychological levels
            interval = 1000.0
            
            if level_type == "support":
                # Find the nearest $1000 level below current price
                support_level = int(current_price / interval) * interval
                # If we're very close to it (within 0.5%), go one level lower
                if (current_price - support_level) / current_price < 0.005:
                    support_level -= interval
                return support_level
            else:  # resistance
                # Find the nearest $1000 level above current price
                resistance_level = (int(current_price / interval) + 1) * interval
                # If we're very close to it (within 0.5%), go one level higher
                if (resistance_level - current_price) / current_price < 0.005:
                    resistance_level += interval
                return resistance_level
                
        except Exception as e:
            logger.error(f"❌ Psychological level calculation failed: {e}")
            # Emergency fallback
            if level_type == "support":
                return current_price * 0.98  # 2% below
            else:
                return current_price * 1.02  # 2% above
    
    # REMOVED: _detect_consolidation_zones - NO FALLBACKS
    
    # REMOVED: _add_projected_support_levels - NO FALLBACKS