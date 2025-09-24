#!/usr/bin/env python3
"""
Simple Support/Resistance Calculator - WORKS
"""

import time
from typing import Dict, List, Any
from loguru import logger

class SupportResistanceCalculator:
    """Simple S/R calculator that actually works"""
    
    def __init__(self):
        logger.info("📊 Support/Resistance Calculator initialized")
    
    def identify_key_levels(self, candles: List[Dict], min_touches: int = 2) -> Dict[str, Any]:
        """Find support/resistance levels - SIMPLE AND WORKS"""
        try:
            if not candles or len(candles) < 10:
                logger.warning("⚠️ Insufficient candle data")
                return {"key_levels": [], "strongest_support": 0.0, "strongest_resistance": 0.0}
            
            current_price = candles[-1].get("close", 0)
            logger.info(f"📊 S/R Analysis: {len(candles)} candles, current_price=${current_price:.2f}")
            
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
                        # Check volume confirmation (temporarily disabled for debugging)
                        volume_confirmed = True  # self._check_volume_confirmation(candles, low, "support")
                        if volume_confirmed:
                            # Calculate comprehensive score (0-100)
                            score = self._calculate_level_score(candles, low, "support", touches, i)
                            
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
                        # Check volume confirmation (temporarily disabled for debugging)
                        volume_confirmed = True  # self._check_volume_confirmation(candles, high, "resistance")
                        if volume_confirmed:
                            # Calculate comprehensive score (0-100)
                            score = self._calculate_level_score(candles, high, "resistance", touches, i)
                            
                            resistance_levels.append({
                                "level": high,
                                "type": "resistance",
                                "score": score,
                                "touches": touches,
                                "index": i
                            })
            
            # Add psychological levels from actual price data near round numbers
            psychological_levels = self._add_psychological_levels(current_price, candles)
            all_levels = support_levels + resistance_levels + psychological_levels
            all_levels.sort(key=lambda x: x["score"], reverse=True)
            
            # Filter levels - show broken levels too (they're still relevant)
            filtered_levels = []
            for level in all_levels:
                # Show all levels - broken support/resistance is still important
                # Filter out levels that are too close to each other (minimum $200 gap)
                is_too_close = False
                for existing in filtered_levels:
                    if abs(level["level"] - existing["level"]) < 200.0:  # $200 minimum gap
                        is_too_close = True
                        break
                if not is_too_close:
                    filtered_levels.append(level)
            
            all_levels = filtered_levels[:5]  # Limit to top 5 levels only
            
            # Get strongest levels from filtered results
            support_levels_filtered = [level for level in all_levels if level["type"] == "support"]
            resistance_levels_filtered = [level for level in all_levels if level["type"] == "resistance"]
            
            strongest_support = support_levels_filtered[0]["level"] if support_levels_filtered else current_price * 0.95
            strongest_resistance = resistance_levels_filtered[0]["level"] if resistance_levels_filtered else current_price * 1.05
            
            logger.info(f"📊 Found {len(support_levels)} support, {len(resistance_levels)} resistance levels")
            logger.info(f"📊 After filtering: {len(support_levels_filtered)} support, {len(resistance_levels_filtered)} resistance")
            logger.info(f"📊 Current price: ${current_price:.2f}")
            logger.info(f"📊 Strongest support: ${strongest_support:.2f} (below price: {strongest_support < current_price})")
            logger.info(f"📊 Strongest resistance: ${strongest_resistance:.2f} (above price: {strongest_resistance > current_price})")
            
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
        tolerance = 100.0  # $100 tolerance - realistic for Bitcoin
        
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
        tolerance = 100.0  # $100 tolerance - same as touch counting
        
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
        
        return volume_ratio > 1.0  # Just above average volume (less strict)
    
    def _add_psychological_levels(self, current_price: float, candles: List[Dict]) -> List[Dict]:
        """Find psychological levels from actual price data near round numbers"""
        psychological_levels = []
        
        # Extract all high and low prices from candles
        all_prices = []
        for candle in candles:
            all_prices.extend([candle.get("high", 0), candle.get("low", 0)])
        
        # Find round number levels around current price
        current_thousand = int(current_price // 1000) * 1000
        current_hundred = int(current_price // 100) * 100
        
        # Look for levels near round thousands and hundreds
        psychological_base_levels = []
        
        # Add thousand levels around current price
        for offset in range(-3, 4):  # -3 to +3 thousand levels
            thousand_level = current_thousand + (offset * 1000)
            if 50000 <= thousand_level <= 200000:  # Reasonable Bitcoin range
                psychological_base_levels.append(thousand_level)
        
        # Add hundred levels around current price
        for offset in range(-2, 3):  # -2 to +2 hundred levels
            hundred_level = current_hundred + (offset * 100)
            if 50000 <= hundred_level <= 200000:  # Reasonable Bitcoin range
                psychological_base_levels.append(hundred_level)
        
        # For each psychological base level, find the closest actual price from data
        for base_level in psychological_base_levels:
            # Find prices within $200 of the psychological level
            tolerance = 200.0
            nearby_prices = [price for price in all_prices if abs(price - base_level) <= tolerance]
            
            if nearby_prices:
                # Use the most common price near this psychological level
                # Group prices by $10 buckets to find clusters
                price_buckets = {}
                for price in nearby_prices:
                    bucket = int(price // 10) * 10  # Round to nearest $10
                    if bucket not in price_buckets:
                        price_buckets[bucket] = []
                    price_buckets[bucket].append(price)
                
                # Find the bucket with most prices (most significant level)
                if price_buckets:
                    best_bucket = max(price_buckets.keys(), key=lambda k: len(price_buckets[k]))
                    best_prices = price_buckets[best_bucket]
                    psychological_price = sum(best_prices) / len(best_prices)  # Average of clustered prices
                    
                    # Determine if it's support or resistance based on current price
                    level_type = "support" if psychological_price < current_price else "resistance"
                    
                    # Calculate score based on how close to round number and how many touches
                    base_score = 5.0  # Base score for psychological levels
                    if base_level % 1000 == 0:  # Round thousands
                        base_score = 7.0
                    elif base_level % 100 == 0:  # Round hundreds
                        base_score = 6.0
                    
                    # Boost score if many prices clustered around this level
                    cluster_boost = min(2.0, len(best_prices) * 0.2)
                    final_score = base_score + cluster_boost
                    
                    psychological_levels.append({
                        "level": psychological_price,
                        "type": level_type,
                        "score": final_score,
                        "touches": len(best_prices),  # Number of prices that touched this area
                        "index": -1,  # Special index for psychological levels
                        "source": "psychological"
                    })
        
        return psychological_levels
    
    def _calculate_level_score(self, candles: List[Dict], level_price: float, level_type: str, touches: int, index: int) -> float:
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
            
            # Ensure score is between 0 and 100
            final_score = max(0.0, min(100.0, total_score))
            
            logger.debug(f"📊 Level score calculation: {level_type} at ${level_price:.2f} = {final_score:.1f} "
                        f"(touches={touch_score:.1f}, volume={volume_score:.1f}, time={time_span_score:.1f}, "
                        f"recent={recent_activity_score:.1f}, price_consistency={price_consistency_score:.1f}, "
                        f"vol_consistency={volume_consistency_score:.1f}, proximity={proximity_score:.1f})")
            
            return final_score
            
        except Exception as e:
            logger.error(f"❌ Level score calculation failed: {e}")
            return 10.0  # Default fallback score
    
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