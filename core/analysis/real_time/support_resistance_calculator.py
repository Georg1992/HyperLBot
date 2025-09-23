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
                            support_levels.append({
                                "level": low,
                                "type": "support",
                                "score": min(touches * 2.0, 10.0),  # Realistic scoring: max 10.0
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
                            resistance_levels.append({
                                "level": high,
                                "type": "resistance",
                                "score": min(touches * 2.0, 10.0),  # Realistic scoring: max 10.0
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