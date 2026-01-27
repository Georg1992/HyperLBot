#!/usr/bin/env python3
"""
Psychological Level Generator

Generates round-number support/resistance levels based on BTC price ranges.
These levels are treated exactly like S/R levels (for entry, stop, take profit).
They do NOT affect direction scoring.
"""

import math
from typing import List, Dict, Any
from loguru import logger


class PsychologicalLevelGenerator:
    """
    Generate psychological (round number) levels for BTC
    
    Levels are generated based on price-appropriate spacing:
    - < $10k: minor=100, major=1000
    - $10k-$50k: minor=500, major=5000
    - > $50k: minor=1000, major=10000
    
    Each level has strength based on divisibility:
    - Base: 0.4
    - +0.2 if divisible by minor
    - +0.2 if divisible by major
    - +0.2 if divisible by (major * 2)
    - Max: 1.0
    """
    
    @staticmethod
    def _get_spacing(current_price: float) -> Dict[str, float]:
        """
        Get minor and major spacing based on current price
        
        Args:
            current_price: Current BTC price
            
        Returns:
            Dict with "minor" and "major" spacing values
        """
        if current_price < 10000:
            return {"minor": 100.0, "major": 1000.0}
        elif current_price < 50000:
            return {"minor": 500.0, "major": 5000.0}
        else:
            return {"minor": 1000.0, "major": 10000.0}
    
    @staticmethod
    def _calculate_strength(price: float, minor: float, major: float) -> float:
        """
        Calculate psychological level strength (0.0-1.0)
        
        Base strength = 0.4
        +0.2 if divisible by minor
        +0.2 if divisible by major
        +0.2 if divisible by (major * 2)
        Clamp to max 1.0
        
        Args:
            price: Level price
            minor: Minor spacing
            major: Major spacing
            
        Returns:
            Strength value (0.0-1.0)
        """
        base_strength = 0.4
        
        # Check divisibility (with small epsilon for float precision)
        EPSILON = 0.01
        
        # Check minor divisibility: price % minor should be ~0 or ~minor
        minor_remainder = abs(price % minor)
        if minor_remainder < EPSILON or abs(minor_remainder - minor) < EPSILON:
            base_strength += 0.2
        
        # Check major divisibility: price % major should be ~0 or ~major
        major_remainder = abs(price % major)
        if major_remainder < EPSILON or abs(major_remainder - major) < EPSILON:
            base_strength += 0.2
        
        # Check (major * 2) divisibility: price % (major*2) should be ~0 or ~(major*2)
        major2 = major * 2.0
        major2_remainder = abs(price % major2)
        if major2_remainder < EPSILON or abs(major2_remainder - major2) < EPSILON:
            base_strength += 0.2
        
        return min(1.0, base_strength)
    
    @staticmethod
    def generate_levels(current_price: float) -> List[Dict[str, Any]]:
        """
        Generate psychological levels ±5% around current price
        
        Args:
            current_price: Current BTC price (must be > 0)
            
        Returns:
            List of level dictionaries conforming to S/R level format:
            {
                "price_level": float,
                "type": "support" | "resistance",
                "strength_score": float (0.0-100.0),  # strength * 100
                "power": float (0.0-100.0),  # strength * 100
                "status": "active",
                "source": "psych",
                "touches": 0,
                "weighted_touches": 0.0,
                "cluster_size": 1,
                "last_touch_timestamp": 0.0,
                "mtf_count": 0,
                "mtf_confidence": 0.0,
                "power_breakdown": {},
                "merged_from": 1,
                "atr_pct": 0.0  # Will be set by caller
            }
        """
        if current_price <= 0:
            raise ValueError(f"Invalid current_price: {current_price} - must be positive (NO FALLBACKS)")
        
        spacing = PsychologicalLevelGenerator._get_spacing(current_price)
        minor = spacing["minor"]
        major = spacing["major"]
        
        # Generate range: ±5% around current price
        price_range_pct = 0.05
        min_price = current_price * (1.0 - price_range_pct)
        max_price = current_price * (1.0 + price_range_pct)
        
        levels = []
        
        # Generate all levels (both minor and major) in range
        # Use set to track prices and avoid duplicates
        seen_prices = set()
        
        # Generate minor levels
        min_minor = math.floor(min_price / minor) * minor
        max_minor = math.ceil(max_price / minor) * minor
        
        price = min_minor
        while price <= max_minor:
            price_float = float(price)
            if min_price <= price_float <= max_price and price_float not in seen_prices:
                seen_prices.add(price_float)
                strength = PsychologicalLevelGenerator._calculate_strength(price_float, minor, major)
                level_type = "support" if price_float < current_price else "resistance"
                
                levels.append({
                    "price_level": price_float,
                    "type": level_type,
                    "strength_score": strength * 100.0,  # Convert to 0-100 range
                    "power": strength * 100.0,  # Same as strength_score for psych levels
                    "status": "active",
                    "source": "psych",
                    "touches": 0,
                    "weighted_touches": 0.0,
                    "cluster_size": 1,
                    "last_touch_timestamp": 0.0,
                    "mtf_count": 0,
                    "mtf_confidence": 0.0,
                    "power_breakdown": {"psychological": strength},
                    "merged_from": 1,
                    "atr_pct": 0.0  # Will be set by integration point
                })
            price += minor
        
        # Generate major levels (may overlap with minor, will dedupe)
        min_major = math.floor(min_price / major) * major
        max_major = math.ceil(max_price / major) * major
        
        price = min_major
        while price <= max_major:
            price_float = float(price)
            if min_price <= price_float <= max_price and price_float not in seen_prices:
                seen_prices.add(price_float)
                strength = PsychologicalLevelGenerator._calculate_strength(price_float, minor, major)
                level_type = "support" if price_float < current_price else "resistance"
                
                levels.append({
                    "price_level": price_float,
                    "type": level_type,
                    "strength_score": strength * 100.0,
                    "power": strength * 100.0,
                    "status": "active",
                    "source": "psych",
                    "touches": 0,
                    "weighted_touches": 0.0,
                    "cluster_size": 1,
                    "last_touch_timestamp": 0.0,
                    "mtf_count": 0,
                    "mtf_confidence": 0.0,
                    "power_breakdown": {"psychological": strength},
                    "merged_from": 1,
                    "atr_pct": 0.0
                })
            price += major
        
        # Sort by price
        levels.sort(key=lambda x: x["price_level"])
        
        logger.debug(f"🧠 Generated {len(levels)} psychological levels around ${current_price:.2f} (range: ${min_price:.2f}-${max_price:.2f})")
        
        return levels
