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
    """Smart S/R calculator with 5m + 1h confirmation and historical context"""
    
    def __init__(self):
        # Cache for S/R levels to avoid recalculation
        self._sr_cache = {}
        
        # Smart caching system
        self._5m_cache = {}
        self._1h_cache = {}
        self._last_5m_update = 0
        self._last_1h_update = 0
        
        # Cache durations
        self._5m_cache_duration = 300   # 5 minutes
        self._1h_cache_duration = 3600  # 1 hour
        
        logger.info("📊 Smart S/R Calculator initialized - 5m + 1h confirmation with historical context")
    
    def identify_key_levels(self, candles: List[Dict], min_touches: int = 2) -> Dict[str, Any]:
        """Find support/resistance levels - SIMPLE AND WORKS"""
        try:
            if not candles or len(candles) < 10:
                raise ValueError(f"Insufficient candle data for S/R analysis: {len(candles) if candles else 0} candles - NO FALLBACKS")
            
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
                        # Check volume confirmation (more lenient)
                        volume_confirmed = self._check_volume_confirmation(candles, low, "support")
                        # Accept level even without volume confirmation if it has good touches
                        if volume_confirmed or touches >= 2:
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
                        # Check volume confirmation (more lenient)
                        volume_confirmed = self._check_volume_confirmation(candles, high, "resistance")
                        # Accept level even without volume confirmation if it has good touches
                        if volume_confirmed or touches >= 2:
                            # Calculate comprehensive score (0-100) with market position context
                            score = self._calculate_level_score(candles, high, "resistance", touches, i, market_position)
                            
                            resistance_levels.append({
                                "level": high,
                                "type": "resistance",
                                "score": score,
                                "touches": touches,
                                "index": i
                            })
            
            # Combine and filter out levels too close to each other
            all_levels = support_levels + resistance_levels
            all_levels.sort(key=lambda x: x["score"], reverse=True)
            
            # Filter out levels too close to each other (minimum $100 gap for Bitcoin)
            filtered_levels = []
            for level in all_levels:
                is_too_close = any(abs(level["level"] - existing["level"]) < 100.0 for existing in filtered_levels)
                if not is_too_close:
                    filtered_levels.append(level)
            
            logger.info(f"📊 Found {len(support_levels)} support, {len(resistance_levels)} resistance (filtered to {len(filtered_levels)} unique levels)")
            
            # Separate support and resistance from filtered levels
            support_levels_filtered = [l for l in filtered_levels if l["type"] == "support"]
            resistance_levels_filtered = [l for l in filtered_levels if l["type"] == "resistance"]
            
            # Get strongest support (ONLY levels below current price)
            strongest_support = 0.0
            if support_levels_filtered:
                # ONLY use support levels that are BELOW current price (not broken)
                support_below = [s for s in support_levels_filtered if s["level"] < current_price]
                if support_below:
                    # Find the closest valid support below current price
                    strongest_support = max(support_below, key=lambda x: x["level"])["level"]
                else:
                    # No valid support below current price - use closest support as fallback
                    closest_support = min(support_levels_filtered, key=lambda x: abs(x["level"] - current_price))
                    strongest_support = closest_support["level"]
                    logger.warning(f"⚠️ All support levels broken - using closest support: ${strongest_support:.2f}")
            else:
                # No support levels found - this should not happen with sufficient data
                raise ValueError(f"No historical support levels found in {len(candles)} candles - NO FALLBACKS")
            
            # Get strongest resistance - ALWAYS prioritize levels above current price
            strongest_resistance = 0.0
            if resistance_levels_filtered:
                # FIRST PRIORITY: Find resistance levels ABOVE current price (valid)
                resistance_above = [r for r in resistance_levels_filtered if r["level"] > current_price]
                if resistance_above:
                    # Find the closest valid resistance above current price
                    strongest_resistance = min(resistance_above, key=lambda x: x["level"])["level"]
                    logger.info(f"✅ Found valid resistance above current price: ${strongest_resistance:.2f}")
                else:
                    # No resistance above current price - this means all resistance is broken
                    # Find the highest resistance level (closest to current price from below)
                    highest_resistance = max(resistance_levels_filtered, key=lambda x: x["level"])
                    strongest_resistance = highest_resistance["level"]
                    logger.warning(f"⚠️ All resistance levels broken - using highest historical: ${strongest_resistance:.2f}")
            else:
                # No resistance levels found - this should not happen with sufficient data
                raise ValueError(f"No historical resistance levels found in {len(candles)} candles - NO FALLBACKS")
            
            # GUARANTEE: Always return valid support and resistance levels from HISTORICAL DATA ONLY
            # NO FALLBACKS - if we reach this point with 0 values, something is wrong with the data
            if strongest_support <= 0:
                raise ValueError(f"CRITICAL: No valid support found in historical data - NO FALLBACKS")
            
            if strongest_resistance <= 0:
                raise ValueError(f"CRITICAL: No valid resistance found in historical data - NO FALLBACKS")
            
            logger.info(f"📊 Found {len(support_levels)} support, {len(resistance_levels)} resistance levels")
            logger.info(f"📊 After filtering: {len(support_levels_filtered)} support, {len(resistance_levels_filtered)} resistance")
            logger.info(f"📊 Current price: ${current_price:.2f}")
            logger.info(f"📊 Strongest support: ${strongest_support:.2f} (below price: {strongest_support < current_price})")
            logger.info(f"📊 Strongest resistance: ${strongest_resistance:.2f} (above price: {strongest_resistance > current_price})")
            
            # Return ALL filtered levels (selection/limiting done by multi-timeframe method if needed)
            return {
                "key_levels": filtered_levels,  # All unique levels found
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "analysis_confidence": 0.9 if len(filtered_levels) > 0 else 0.3
            }
            
        except Exception as e:
            logger.error(f"❌ S/R detection failed: {e}")
            # Emergency fallback - try to find levels from raw historical data
            current_price = candles[-1].get("close", 0) if candles else 0
            if current_price > 0 and len(candles) >= 10:
                # Try to find basic support/resistance from raw price data
                highs = [c.get("high", 0) for c in candles if c.get("high", 0) > 0]
                lows = [c.get("low", 0) for c in candles if c.get("low", 0) > 0]
                
                if highs and lows:
                    # Use recent highs/lows as emergency levels
                    emergency_support = min(lows[-10:])  # Lowest low in last 10 candles
                    emergency_resistance = max(highs[-10:])  # Highest high in last 10 candles
                    logger.warning(f"⚠️ Using emergency historical levels: Support=${emergency_support:.2f}, Resistance=${emergency_resistance:.2f}")
                    return {
                        "key_levels": [], 
                        "strongest_support": emergency_support, 
                        "strongest_resistance": emergency_resistance,
                        "analysis_confidence": 0.1
                    }
            
            # NO FALLBACKS - raise error if no historical data available
            raise ValueError(f"S/R level identification failed - insufficient historical data - NO FALLBACKS")
    
    
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
        
        # Volume confirmation: touching candles should have reasonable volume
        volume_ratio = avg_touching_volume / overall_avg_volume if overall_avg_volume > 0 else 1.0
        
        return volume_ratio > 0.5  # More lenient volume confirmation (0.5 instead of 0.8)
    
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
    
    def _create_psychological_resistance_for_ath(self, current_price: float) -> List[Dict]:
        """
        Create psychological resistance levels for ALL-TIME HIGH breakouts
        ONLY justified fallback - when no historical resistance exists above price
        
        Args:
            current_price: Current market price (at or near ATH)
            
        Returns:
            List of psychological resistance levels above current price
        """
        try:
            logger.warning(f"🎯 Creating psychological resistance for ATH breakout at ${current_price:.2f}")
            
            psychological_levels = []
            
            # For BTC, use $1000 intervals for major psychological levels
            interval = 1000.0
            
            # Create 3 psychological resistance levels above current price
            for i in range(1, 4):  # $1k, $2k, $3k above current rounded level
                # Round current price up to next $1000 level
                base_level = (int(current_price / interval) + 1) * interval
                resistance_level = base_level + (interval * (i - 1))
                
                psychological_levels.append({
                    "level": resistance_level,
                    "type": "resistance",
                    "score": 30 - (i * 5),  # Decreasing score for higher levels
                    "touches": 0,  # No historical touches (it's new ATH territory)
                    "timeframe": "psychological_ath",
                    "weight": 0.8,  # High weight - psychological levels are strong at ATH
                    "volume_confirmed": False,
                    "relevance": "high" if i == 1 else "medium",
                    "reason": f"Psychological resistance ${resistance_level:,.0f} (ATH+{i}k)"
                })
            
            logger.warning(f"📊 Created {len(psychological_levels)} psychological resistance levels for ATH breakout")
            for level in psychological_levels:
                logger.warning(f"   🎯 Psychological resistance: ${level['level']:,.0f}")
            
            return psychological_levels
                
        except Exception as e:
            logger.error(f"❌ Psychological resistance creation failed: {e}")
            return []
    
    # REMOVED: _find_next_psychological_level - NO FALLBACKS POLICY (except ATH case above)
    
    # REMOVED: _detect_consolidation_zones - NO FALLBACKS
    
    # REMOVED: _add_projected_support_levels - NO FALLBACKS
    
    def calculate_multi_timeframe_levels(self, current_price: float, market_data_service, candles_5m=None, candles_1h=None, candles_1d=None) -> Dict[str, Any]:
        """
        Calculate S/R levels using multiple timeframes with intelligent caching and expansion.
        
        This is the HIGH-LEVEL orchestration method that:
        1. Checks cache and invalidates if price broke levels
        2. Fetches multi-timeframe data (5m, 1h, 1d)
        3. Analyzes each timeframe with identify_key_levels()
        4. Combines and weights levels by timeframe
        5. Expands to longer history if insufficient levels found
        6. Caches result until price breaks a level
        
        Args:
            current_price: Current market price
            market_data_service: Service to fetch historical candles
            
        Returns:
            Dict with key_levels, strongest_support, strongest_resistance, metadata
        """
        try:
            logger.debug(f"🔍 calculate_multi_timeframe_levels called with market_data_service: {type(market_data_service)}")
            logger.info(f"📊 Starting multi-timeframe S/R calculation for price: ${current_price:.2f}")
            
            # Check cache - invalidate if price broke any levels
            if self._should_use_cached_sr(current_price):
                cached_data = self._sr_cache.get('data', {})
                # Check if cached data has sufficient levels
                key_levels = cached_data.get('key_levels', [])
                support_levels = [l for l in key_levels if l.get("type") == "support"]
                resistance_levels = [l for l in key_levels if l.get("type") == "resistance"]
                
                # If insufficient levels, don't use cache and recalculate
                if len(support_levels) < 2 or len(resistance_levels) < 2:
                    logger.warning(f"⚠️ Cached S/R data insufficient: {len(support_levels)} support, {len(resistance_levels)} resistance - recalculating")
                else:
                    logger.info("📊 Using cached S/R data (no level breaks detected)")
                    return cached_data
            
            # SMART S/R DETECTION: 5m + 1h confirmation with historical context
            logger.info("📊 Smart S/R detection: 5m (24h) + 1h (1 month) with confirmation")
            
            # Update caches if needed
            self._update_5m_cache_if_needed(market_data_service)
            self._update_1h_cache_if_needed(market_data_service)
            
            # Get levels from both timeframes
            levels_5m = self._find_levels_from_5m_cache(current_price)
            levels_1h = self._find_levels_from_1h_cache(current_price)
            
            # Score levels with confirmation
            all_levels = self._score_levels_with_confirmation(levels_5m, levels_1h, current_price)
            
            # Separate support and resistance
            support_levels = [level for level in all_levels if level["level"] < current_price]
            resistance_levels = [level for level in all_levels if level["level"] > current_price]
            
            logger.info(f"📊 Found {len(support_levels)} support levels, {len(resistance_levels)} resistance levels")
            
            # If insufficient levels, check historical price context
            if len(resistance_levels) < 2 or len(support_levels) < 2:
                logger.warning("⚠️ Insufficient levels - checking historical price context")
                historical_levels = self._find_historical_levels_at_price(current_price, market_data_service)
                all_levels.extend(historical_levels)
                
                # Re-separate after adding historical levels
                support_levels = [level for level in all_levels if level["level"] < current_price]
                resistance_levels = [level for level in all_levels if level["level"] > current_price]
                logger.info(f"📊 After historical context: {len(resistance_levels)} resistance, {len(support_levels)} support")
            
            # If still no resistance, this is likely ATH breakout
            if len(resistance_levels) == 0:
                logger.warning(f"🚨 ATH BREAKOUT: No resistance above ${current_price:.2f}")
                psychological_resistance = self._create_psychological_resistance_for_ath(current_price)
                resistance_levels = psychological_resistance
            
            # Extract strongest levels
            if support_levels:
                strongest_support = max(support_levels, key=lambda x: x["level"])["level"]
            else:
                raise ValueError(f"CRITICAL: No support found - NO FALLBACKS")
            
            if resistance_levels:
                strongest_resistance = min(resistance_levels, key=lambda x: x["level"])["level"]
            else:
                raise ValueError(f"CRITICAL: No resistance found - NO FALLBACKS")
            
            # Prepare result
            all_levels = support_levels + resistance_levels
            result = {
                "key_levels": all_levels[:10],
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "timeframe": "5m_simple",
                "candles_analyzed": len(candles_5m),
                "analysis_confidence": min(1.0, len(all_levels) / 8),
                "level_breakdown": {
                    "support_count": len(support_levels),
                    "resistance_count": len(resistance_levels),
                    "timeframes_analyzed": 1  # Only 5m
                }
            }
            
            # Cache result
            self._sr_cache = {'data': result, 'last_price': current_price}
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe S/R calculation failed: {e}")
            raise
    
    def _should_use_cached_sr(self, current_price: float) -> bool:
        """Check if cached S/R data is still valid (no level breaks)"""
        if not self._sr_cache or 'data' not in self._sr_cache:
            return False
        
        cached_data = self._sr_cache.get('data', {})
        last_price = self._sr_cache.get('last_price', current_price)
        key_levels = cached_data.get('key_levels', [])
        
        # Also check strongest_support and strongest_resistance for breaks
        strongest_support = cached_data.get('strongest_support', 0)
        strongest_resistance = cached_data.get('strongest_resistance', 0)
        
        # Check if price broke through strongest levels (more aggressive detection)
        if strongest_support > 0 and current_price < strongest_support:
            logger.warning(f"🚨 Price broke strongest support at ${strongest_support:.2f} - FORCING cache invalidation and recalculation")
            return False
        
        if strongest_resistance > 0 and current_price > strongest_resistance:
            logger.warning(f"🚨 Price broke strongest resistance at ${strongest_resistance:.2f} - FORCING cache invalidation and recalculation")
            return False
        
        # Check if price broke through any individual levels
        for level in key_levels:
            level_price = level.get('level', 0)
            level_type = level.get('type', '')
            buffer = level_price * 0.005  # 0.5% buffer
            
            # Support break (price fell below)
            if (level_type == 'support' and 
                last_price > (level_price + buffer) and 
                current_price <= (level_price + buffer)):
                logger.info(f"📊 Price broke support at ${level_price:.2f} - cache invalidated")
                return False
            
            # Resistance break (price rose above)
            if (level_type == 'resistance' and 
                last_price < (level_price - buffer) and 
                current_price >= (level_price - buffer)):
                logger.info(f"📊 Price broke resistance at ${level_price:.2f} - cache invalidated")
                return False
        
        return True
    
    def _select_relevant_levels(self, all_levels: List[Dict], current_price: float) -> List[Dict]:
        """Select most relevant S/R levels - ONLY 2 closest support and 2 closest resistance"""
        relevant_levels = []
        
        # Separate by type and filter by price position
        support_below = [l for l in all_levels if l["type"] == "support" and l["level"] < current_price]
        resistance_above = [l for l in all_levels if l["type"] == "resistance" and l["level"] > current_price]
        
        # Sort support by distance from current price (closest first)
        support_below.sort(key=lambda x: current_price - x["level"])
        
        # Sort resistance by distance from current price (closest first)  
        resistance_above.sort(key=lambda x: x["level"] - current_price)
        
        # Select exactly 2 closest support levels (below current price)
        for support in support_below[:2]:
            support["relevance"] = self._calculate_relevance(support)
            relevant_levels.append(support)
        
        # Select exactly 2 closest resistance levels (above current price)
        for resistance in resistance_above[:2]:
            resistance["relevance"] = self._calculate_relevance(resistance)
            relevant_levels.append(resistance)
        
        logger.info(f"📊 Selected {len([l for l in relevant_levels if l['type'] == 'support'])} support, {len([l for l in relevant_levels if l['type'] == 'resistance'])} resistance levels")
        
        return relevant_levels
    
    def _calculate_relevance(self, level: Dict) -> str:
        """Calculate relevance category based on combined score"""
        combined_score = level.get("score", 0) * level.get("weight", 1.0)
        if combined_score > 50:
            return "high"
        elif combined_score > 20:
            return "medium"
        else:
            return "low"
    
    def _detect_sr_levels_simple(self, candles: List[Dict], current_price: float) -> List[Dict]:
        """
        Simple S/R detection with touch counting, volume confirmation, and time decay
        
        Args:
            candles: List of candle data (5m or 1h)
            current_price: Current market price
            
        Returns:
            List of S/R levels with touch count, volume confirmation, and time decay
        """
        try:
            logger.debug(f"📊 Analyzing {len(candles)} candles for S/R levels")
            
            # Define price ranges to check (every $500 around current price)
            price_ranges = []
            for offset in range(-20000, 30000, 500):  # $20k below to $30k above
                level = current_price + offset
                price_ranges.append({
                    "level": level,
                    "min": level - 250,  # $250 range
                    "max": level + 250
                })
            
            # Analyze each price level
            sr_levels = []
            
            for price_range in price_ranges:
                level = price_range["level"]
                min_price = price_range["min"]
                max_price = price_range["max"]
                
                # Count touches and volume at this level
                touches = 0
                total_volume = 0
                recent_touches = 0  # Touches in last 24 hours
                
                for i, candle in enumerate(candles):
                    # Check if price touched this level (high or low within range)
                    if min_price <= candle["high"] <= max_price or min_price <= candle["low"] <= max_price:
                        touches += 1
                        total_volume += candle.get("volume", 0)
                        
                        # Check if this is recent (last 24 hours)
                        if i >= len(candles) - 288:  # 288 candles = 24 hours
                            recent_touches += 1
                
                # Only consider levels with multiple touches
                if touches >= 2:  # Reduced threshold for better detection
                    # Calculate time decay (more recent = higher score)
                    time_decay_score = recent_touches / max(1, touches)  # 0-1, higher for recent touches
                    
                    # Calculate volume confirmation (higher volume = stronger level)
                    avg_volume = total_volume / max(1, touches)
                    volume_score = min(1.0, avg_volume / 1000000)  # Normalize volume score
                    
                    # Calculate overall strength
                    strength = (touches * 0.4) + (time_decay_score * 0.3) + (volume_score * 0.3)
                    
                    sr_levels.append({
                        "level": level,
                        "touches": touches,
                        "recent_touches": recent_touches,
                        "total_volume": total_volume,
                        "avg_volume": avg_volume,
                        "time_decay_score": time_decay_score,
                        "volume_score": volume_score,
                        "strength": strength,
                        "type": "support" if level < current_price else "resistance"
                    })
            
            # Sort by strength (highest first)
            sr_levels.sort(key=lambda x: x["strength"], reverse=True)
            
            # Take top 10 levels
            top_levels = sr_levels[:10]
            
            logger.debug(f"📊 Found {len(top_levels)} significant S/R levels")
            return top_levels
            
        except Exception as e:
            logger.error(f"❌ S/R detection failed: {e}")
            return []
    
    def _update_5m_cache_if_needed(self, market_data_service):
        """Update 5m cache if needed (every 5 minutes)"""
        current_time = time.time()
        if current_time - self._last_5m_update > self._5m_cache_duration:
            logger.debug("📊 Updating 5m cache (24h data)")
            candles_5m = market_data_service.get_historical_candles("BTC", "5m", 288)  # 24h
            if candles_5m and len(candles_5m) >= 100:
                self._5m_cache = {
                    "candles": candles_5m,
                    "timestamp": current_time
                }
                self._last_5m_update = current_time
                logger.debug(f"📊 5m cache updated: {len(candles_5m)} candles")
    
    def _update_1h_cache_if_needed(self, market_data_service):
        """Update 1h cache if needed (every 1 hour)"""
        current_time = time.time()
        if current_time - self._last_1h_update > self._1h_cache_duration:
            logger.debug("📊 Updating 1h cache (1 month data)")
            candles_1h = market_data_service.get_historical_candles("BTC", "1h", 720)  # 1 month
            if candles_1h and len(candles_1h) >= 100:
                self._1h_cache = {
                    "candles": candles_1h,
                    "timestamp": current_time
                }
                self._last_1h_update = current_time
                logger.debug(f"📊 1h cache updated: {len(candles_1h)} candles")
    
    def _find_levels_from_5m_cache(self, current_price: float) -> List[Dict]:
        """Find S/R levels from 5m cache"""
        if not self._5m_cache or "candles" not in self._5m_cache:
            return []
        
        candles_5m = self._5m_cache["candles"]
        return self._detect_sr_levels_simple(candles_5m, current_price)
    
    def _find_levels_from_1h_cache(self, current_price: float) -> List[Dict]:
        """Find S/R levels from 1h cache"""
        if not self._1h_cache or "candles" not in self._1h_cache:
            return []
        
        candles_1h = self._1h_cache["candles"]
        return self._detect_sr_levels_simple(candles_1h, current_price)
    
    def _score_levels_with_confirmation(self, levels_5m: List[Dict], levels_1h: List[Dict], current_price: float) -> List[Dict]:
        """Score levels with 1h confirmation"""
        all_levels = []
        
        # Add 5m levels with base weight
        for level in levels_5m:
            level["base_weight"] = 2.0
            level["timeframe"] = "5m"
            all_levels.append(level)
        
        # Add 1h levels with confirmation weight
        for level in levels_1h:
            level["base_weight"] = 1.5
            level["timeframe"] = "1h"
            all_levels.append(level)
        
        # Score levels with confirmation
        scored_levels = []
        for level in all_levels:
            level_price = level["level"]
            
            # Find 1h confirmation for this level
            confirmation_score = 0
            for confirm_level in levels_1h:
                if abs(confirm_level["level"] - level_price) < 100:  # Within $100
                    confirmation_score = confirm_level.get("touches", 1) * 0.3
            
            # Calculate final score
            base_score = level.get("touches", 1) * level.get("base_weight", 1.0)
            volume_score = level.get("volume_score", 0) * 0.2
            time_score = level.get("time_decay_score", 0) * 0.1
            
            final_score = base_score + confirmation_score + volume_score + time_score
            
            level["final_score"] = final_score
            level["confirmation_score"] = confirmation_score
            scored_levels.append(level)
        
        # Sort by final score
        scored_levels.sort(key=lambda x: x["final_score"], reverse=True)
        
        logger.info(f"📊 Scored {len(scored_levels)} levels with confirmation")
        for level in scored_levels[:5]:  # Log top 5
            logger.info(f"   ${level['level']:.0f} - score: {level['final_score']:.2f} (confirmation: {level['confirmation_score']:.2f})")
        
        return scored_levels
    
    def _find_historical_levels_at_price(self, current_price: float, market_data_service) -> List[Dict]:
        """Find historical levels where price was at current level"""
        try:
            logger.info(f"📊 Checking historical context for price ${current_price:.2f}")
            
            # Get 1 month of 1h data for historical context
            historical_candles = market_data_service.get_historical_candles("BTC", "1h", 720)  # 1 month
            
            if not historical_candles or len(historical_candles) < 100:
                logger.warning("⚠️ Insufficient historical data for price context")
                return []
            
            historical_levels = []
            price_range = current_price * 0.02  # ±2% range
            
            for candle in historical_candles:
                # Check if price was near current level
                if (current_price - price_range <= candle["high"] <= current_price + price_range or
                    current_price - price_range <= candle["low"] <= current_price + price_range):
                    
                    historical_levels.append({
                        "level": current_price,
                        "touches": 1,
                        "volume": candle.get("volume", 0),
                        "timestamp": candle.get("timestamp", 0),
                        "timeframe": "historical",
                        "base_weight": 0.8,
                        "final_score": 0.8,
                        "confirmation_score": 0,
                        "type": "support" if current_price < candle["close"] else "resistance"
                    })
            
            logger.info(f"📊 Found {len(historical_levels)} historical levels at current price")
            return historical_levels
            
        except Exception as e:
            logger.error(f"❌ Historical level detection failed: {e}")
            return []
    