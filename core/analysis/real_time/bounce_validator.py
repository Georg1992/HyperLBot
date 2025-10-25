#!/usr/bin/env python3
"""
Bounce Validator Module
Validates that price levels are actual support/resistance by checking bounce behavior
"""

import time
from typing import Dict, Any, List
from loguru import logger

# Singleton pattern implementation
_global_bounce_validator = None

# Factory function for backward compatibility
def create_bounce_validator() -> 'BounceValidator':
    """
    Factory function to create BounceValidator with dependency injection
    
    Returns:
        Configured BounceValidator instance
    """
    return BounceValidator()

def get_global_bounce_validator() -> 'BounceValidator':
    """Get the global BounceValidator singleton instance"""
    global _global_bounce_validator
    if _global_bounce_validator is None:
        _global_bounce_validator = create_bounce_validator()
    return _global_bounce_validator

class BounceValidator:
    """Validates that price levels show actual bounce behavior (not just touchpoints)"""
    
    def __init__(self):
        logger.info("📊 Bounce Validator initialized")
    
    def validate_bounce_behavior(self, cluster: List[Dict], level_price: float, candles: List[Dict] = None) -> float:
        """Validate that price actually bounced off this level and measure its strength"""
        try:
            if len(cluster) < 2:
                return 0.0  # Need at least 2 touches to validate bounce behavior
            
            touches = len(cluster)
            base_score = 0.0
            
            # 1. TOUCH FREQUENCY STRENGTH (0-40 points)
            # More touches = stronger level - more generous scoring
            touch_strength = min(40, touches * 8)  # 5 touches = 40 points
            base_score += touch_strength
            
            # 2. TIME SPAN STRENGTH (0-20 points)
            # Levels that held over longer periods are stronger
            if len(cluster) > 1:
                time_span = max(p["timestamp"] for p in cluster) - min(p["timestamp"] for p in cluster)
                time_strength = min(20, time_span / 3600 * 2)  # 10 hours = 20 points
                base_score += time_strength
            
            # 3. VOLUME STRENGTH (0-30 points)
            # Higher volume at the level = stronger resistance - more generous scoring
            total_volume = sum(p.get("volume", 0) for p in cluster)
            if total_volume > 0:
                avg_volume = total_volume / touches
                volume_strength = min(30, avg_volume / 1000 * 30)  # 1000 avg volume = 30 points (more generous)
                base_score += volume_strength
            else:
                # Give some points even for zero volume (not all data has volume)
                base_score += 10
            
            # 4. BOUNCE STRENGTH ANALYSIS (0-25 points)
            # If we have candle data, analyze actual bounce behavior
            bounce_strength = 0
            if candles and len(candles) > 10:
                bounce_strength = self._analyze_bounce_strength(cluster, level_price, candles)
                base_score += bounce_strength
            
            # Convert to 0-1 scale - updated max score
            max_possible_score = 115  # 40 + 20 + 30 + 25 (updated scoring)
            final_score = min(1.0, base_score / max_possible_score)
            
            return final_score
            
        except Exception as e:
            logger.error(f"❌ Bounce validation failed: {e}")
            return 0.0  # Return 0 if validation fails
    
    def _analyze_bounce_strength(self, cluster: List[Dict], level_price: float, candles: List[Dict]) -> float:
        """Analyze actual bounce strength from candle data with detailed rejection metrics"""
        try:
            bounce_strength = 0
            tolerance = 100  # $100 tolerance for level detection
            
            # Find candles that touched the level
            touching_candles = []
            for candle in candles:
                high = float(candle.get("high", 0))
                low = float(candle.get("low", 0))
                
                # Check if candle touched the level
                if abs(high - level_price) <= tolerance or abs(low - level_price) <= tolerance:
                    touching_candles.append(candle)
            
            if len(touching_candles) < 2:
                return 0
            
            # Analyze bounce behavior for each touch with detailed rejection data
            total_rejection_volume = 0
            total_rejection_magnitude = 0
            rejection_count = 0
            
            for i, touch_candle in enumerate(touching_candles):
                touch_high = float(touch_candle.get("high", 0))
                touch_low = float(touch_candle.get("low", 0))
                touch_close = float(touch_candle.get("close", 0))
                touch_volume = float(touch_candle.get("volume", 0))
                
                # Determine if this was a resistance or support touch
                is_resistance_touch = abs(touch_high - level_price) <= tolerance
                is_support_touch = abs(touch_low - level_price) <= tolerance
                
                if is_resistance_touch:
                    # For resistance: analyze rejection candle data
                    rejection_data = self._analyze_resistance_rejection(touch_candle, candles, level_price)
                    if rejection_data["is_valid_rejection"]:
                        bounce_strength += rejection_data["strength"]
                        total_rejection_volume += rejection_data["rejection_volume"]
                        total_rejection_magnitude += rejection_data["rejection_magnitude"]
                        rejection_count += 1
                        
                        # Log detailed rejection data
                
                elif is_support_touch:
                    # For support: analyze rejection candle data
                    rejection_data = self._analyze_support_rejection(touch_candle, candles, level_price)
                    if rejection_data["is_valid_rejection"]:
                        bounce_strength += rejection_data["strength"]
                        total_rejection_volume += rejection_data["rejection_volume"]
                        total_rejection_magnitude += rejection_data["rejection_magnitude"]
                        rejection_count += 1
                        
                        # Log detailed rejection data
            
            # Calculate average rejection metrics
            if rejection_count > 0:
                avg_rejection_volume = total_rejection_volume / rejection_count
                avg_rejection_magnitude = total_rejection_magnitude / rejection_count
                
            
            # Average bounce strength
            avg_bounce_strength = bounce_strength / len(touching_candles) if touching_candles else 0
            return min(25, avg_bounce_strength)  # Cap at 25 points
            
        except Exception as e:
            logger.error(f"❌ Bounce strength analysis failed: {e}")
            return 0
    
    def _analyze_resistance_rejection(self, touch_candle: Dict, candles: List[Dict], level_price: float) -> Dict[str, Any]:
        """Analyze resistance rejection with detailed metrics from rejection candle"""
        try:
            touch_timestamp = touch_candle.get("timestamp", 0)
            touch_high = float(touch_candle.get("high", 0))
            touch_close = float(touch_candle.get("close", 0))
            touch_volume = float(touch_candle.get("volume", 0))
            
            # Find subsequent candles (next 3-5 candles)
            subsequent_candles = []
            for candle in candles:
                if candle.get("timestamp", 0) > touch_timestamp:
                    subsequent_candles.append(candle)
                    if len(subsequent_candles) >= 5:  # Look at next 5 candles
                        break
            
            if not subsequent_candles:
                return {"is_valid_rejection": False, "strength": 0, "rejection_volume": 0, "rejection_magnitude": 0}
            
            # Calculate rejection metrics
            max_drop = 0
            rejection_volume = touch_volume  # Volume from the rejection candle
            rejection_magnitude = 0
            
            # Check if this was actually a rejection (close below the level)
            is_rejection = touch_close < level_price
            
            if is_rejection:
                # Calculate how much price dropped after touching resistance
                for candle in subsequent_candles:
                    candle_low = float(candle.get("low", 0))
                    drop = touch_high - candle_low
                    max_drop = max(max_drop, drop)
                
                rejection_magnitude = max_drop
                
                # Calculate strength based on multiple factors
                # 1. Rejection magnitude (how far price dropped)
                magnitude_score = min(10, max_drop / 20)  # $20 per point, max 10 points
                
                # 2. Volume at rejection (higher volume = stronger rejection)
                volume_score = min(5, touch_volume / 1000)  # 1000 volume = 5 points, max 5 points
                
                # 3. Close position (how far below level it closed)
                close_distance = level_price - touch_close
                close_score = min(5, close_distance / 50)  # $50 below = 5 points, max 5 points
                
                total_strength = magnitude_score + volume_score + close_score
                
                return {
                    "is_valid_rejection": True,
                    "strength": total_strength,
                    "rejection_volume": rejection_volume,
                    "rejection_magnitude": rejection_magnitude,
                    "close_distance": close_distance,
                    "magnitude_score": magnitude_score,
                    "volume_score": volume_score,
                    "close_score": close_score
                }
            else:
                return {"is_valid_rejection": False, "strength": 0, "rejection_volume": 0, "rejection_magnitude": 0}
            
        except Exception as e:
            logger.error(f"❌ Resistance rejection analysis failed: {e}")
            return {"is_valid_rejection": False, "strength": 0, "rejection_volume": 0, "rejection_magnitude": 0}
    
    def _analyze_support_rejection(self, touch_candle: Dict, candles: List[Dict], level_price: float) -> Dict[str, Any]:
        """Analyze support rejection with detailed metrics from rejection candle"""
        try:
            touch_timestamp = touch_candle.get("timestamp", 0)
            touch_low = float(touch_candle.get("low", 0))
            touch_close = float(touch_candle.get("close", 0))
            touch_volume = float(touch_candle.get("volume", 0))
            
            # Find subsequent candles (next 3-5 candles)
            subsequent_candles = []
            for candle in candles:
                if candle.get("timestamp", 0) > touch_timestamp:
                    subsequent_candles.append(candle)
                    if len(subsequent_candles) >= 5:  # Look at next 5 candles
                        break
            
            if not subsequent_candles:
                return {"is_valid_rejection": False, "strength": 0, "rejection_volume": 0, "rejection_magnitude": 0}
            
            # Calculate rejection metrics
            max_rise = 0
            rejection_volume = touch_volume  # Volume from the rejection candle
            rejection_magnitude = 0
            
            # Check if this was actually a rejection (close above the level)
            is_rejection = touch_close > level_price
            
            if is_rejection:
                # Calculate how much price rose after touching support
                for candle in subsequent_candles:
                    candle_high = float(candle.get("high", 0))
                    rise = candle_high - touch_low
                    max_rise = max(max_rise, rise)
                
                rejection_magnitude = max_rise
                
                # Calculate strength based on multiple factors
                # 1. Rejection magnitude (how far price rose)
                magnitude_score = min(10, max_rise / 20)  # $20 per point, max 10 points
                
                # 2. Volume at rejection (higher volume = stronger rejection)
                volume_score = min(5, touch_volume / 1000)  # 1000 volume = 5 points, max 5 points
                
                # 3. Close position (how far above level it closed)
                close_distance = touch_close - level_price
                close_score = min(5, close_distance / 50)  # $50 above = 5 points, max 5 points
                
                total_strength = magnitude_score + volume_score + close_score
                
                return {
                    "is_valid_rejection": True,
                    "strength": total_strength,
                    "rejection_volume": rejection_volume,
                    "rejection_magnitude": rejection_magnitude,
                    "close_distance": close_distance,
                    "magnitude_score": magnitude_score,
                    "volume_score": volume_score,
                    "close_score": close_score
                }
            else:
                return {"is_valid_rejection": False, "strength": 0, "rejection_volume": 0, "rejection_magnitude": 0}
            
        except Exception as e:
            logger.error(f"❌ Support rejection analysis failed: {e}")
            return {"is_valid_rejection": False, "strength": 0, "rejection_volume": 0, "rejection_magnitude": 0}
    
    def is_valid_sr_level(self, cluster: List[Dict], level_price: float, min_bounce_ratio: float = 0.05, candles: List[Dict] = None) -> bool:
        """Check if a level passes bounce validation threshold"""
        bounce_score = self.validate_bounce_behavior(cluster, level_price, candles)
        is_valid = bounce_score >= min_bounce_ratio
        
        return is_valid
