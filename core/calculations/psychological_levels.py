#!/usr/bin/env python3
"""
Psychological Levels Calculator

Detects and scores psychological/round number levels that traders use as reference points.
Especially important for all-time highs where historical swing points may be limited.

Examples: $90,000, $95,000, $100,000, $105,000, etc.
"""

import math
from typing import Dict, List, Any, Optional
from loguru import logger

from .level import Level


class PsychologicalLevelsCalculator:
    """
    Calculate psychological (round number) support/resistance levels
    
    These are levels that traders psychologically use as reference points:
    - Major round numbers: $90k, $95k, $100k, $105k, etc.
    - Half-levels: $92.5k, $97.5k (for very high prices)
    - Quarter-levels: $91.25k, $93.75k (for extreme prices)
    """
    
    def __init__(self):
        """Initialize psychological levels calculator"""
        self.logger = logger
    
    def calculate_psychological_levels(self, current_price: float, 
                                       long_liquidation: float,
                                       short_liquidation: float,
                                       lookback_days: int = 30) -> List[Level]:
        """
        Calculate psychological levels around current price within liquidation range
        
        Strategy:
        1. Generate round number levels near current price
        2. Filter by liquidation range (safe for trading)
        3. Score based on proximity, roundness, and historical significance
        4. Return as Level objects compatible with S/R system
        
        Args:
            current_price: Current market price
            long_liquidation: LONG liquidation price (for support filtering)
            short_liquidation: SHORT liquidation price (for resistance filtering)
            lookback_days: Days to look back for historical significance (default: 30)
            
        Returns:
            List of Level objects representing psychological levels
        """
        try:
            psychological_levels = []
            
            # Determine price magnitude for appropriate round number intervals
            price_magnitude = self._get_price_magnitude(current_price)
            
            # Generate round number levels around current price
            round_levels = self._generate_round_levels(current_price, price_magnitude)
            
            # Filter by liquidation range and classify as support/resistance
            for level_price in round_levels:
                # Determine if this is support or resistance
                if level_price < current_price:
                    # Support level: must be >= long_liquidation
                    if level_price >= long_liquidation:
                        level_type = "support"
                    else:
                        continue  # Too close to liquidation, skip
                elif level_price > current_price:
                    # Resistance level: must be <= short_liquidation
                    if level_price <= short_liquidation:
                        level_type = "resistance"
                    else:
                        continue  # Too close to liquidation, skip
                else:
                    # Exactly at current price, skip
                    continue
                
                # Calculate score for this psychological level
                score = self._calculate_psychological_score(
                    level_price, current_price, level_type, price_magnitude
                )
                
                # Create Level object (psychological levels have special characteristics)
                psychological_level = Level(
                    level=level_price,
                    level_type=level_type,
                    touches=1,  # Psychological levels are conceptual, not based on touches
                    cluster_size=1,
                    weighted_touches=1.0,
                    strength=self._calculate_roundness_strength(level_price, price_magnitude),
                    timestamp=0.0,  # Psychological levels don't have timestamps
                    timeframe_distribution={},
                    mtf_matches=[],
                    mtf_count=0,
                    mtf_confidence=0.0,
                    merged_from=1,
                    score=score,
                    score_breakdown={
                        "psychological": True,
                        "roundness": self._get_roundness_score(level_price, price_magnitude),
                        "proximity": self._get_proximity_score(level_price, current_price),
                        "magnitude": price_magnitude
                    }
                )
                
                psychological_levels.append(psychological_level)
            
            # Sort by score (highest first)
            psychological_levels.sort(key=lambda x: x.score or 0, reverse=True)
            
            logger.info(f"🧠 Generated {len(psychological_levels)} psychological levels "
                      f"(support: {sum(1 for l in psychological_levels if l.level_type == 'support')}, "
                      f"resistance: {sum(1 for l in psychological_levels if l.level_type == 'resistance')})")
            
            return psychological_levels
            
        except Exception as e:
            logger.error(f"❌ Psychological levels calculation failed: {e}")
            return []
    
    def _get_price_magnitude(self, price: float) -> int:
        """
        Determine appropriate round number interval based on price magnitude
        
        Fixed intervals (from smallest to strongest):
        - $500: Smallest level
        - $1,000: Stronger level
        - $2,500: Stronger level
        - $5,000: Stronger level
        - $10,000: Stronger level
        - $100,000: Strongest level
        
        Args:
            price: Current price
            
        Returns:
            Round number interval (500, 1000, 2500, 5000, 10000, or 100000)
        """
        # Determine which interval to use based on price magnitude
        if price < 50000:
            return 1000  # Use $1k intervals for prices < $50k
        elif price < 100000:
            return 2500  # Use $2.5k intervals for prices $50k-$100k
        elif price < 500000:
            return 5000  # Use $5k intervals for prices $100k-$500k
        elif price < 1000000:
            return 10000  # Use $10k intervals for prices $500k-$1M
        else:
            return 100000  # Use $100k intervals for prices > $1M
    
    def _generate_round_levels(self, current_price: float, interval: int) -> List[float]:
        """
        Generate round number levels around current price using fixed intervals
        
        Fixed intervals (from smallest to strongest):
        - $500: Smallest level
        - $1,000: Stronger level
        - $2,500: Stronger level
        - $5,000: Stronger level
        - $10,000: Stronger level
        - $100,000: Strongest level
        
        Generates levels:
        - Below current price (support): 2-3 levels
        - Above current price (resistance): 2-3 levels
        
        Args:
            current_price: Current market price
            interval: Round number interval (500, 1000, 2500, 5000, 10000, or 100000)
            
        Returns:
            List of round number prices
        """
        levels = []
        
        # Calculate base round number (round down to nearest interval)
        base_level = math.floor(current_price / interval) * interval
        
        # Generate levels below current price (support candidates)
        # Look 2-3 intervals below
        for i in range(1, 4):
            level = base_level - (i * interval)
            if level > 0:
                levels.append(level)
        
        # Generate levels above current price (resistance candidates)
        # Look 2-3 intervals above
        for i in range(1, 4):
            level = base_level + (i * interval)
            levels.append(level)
        
        # Sort and return
        levels.sort()
        return levels
    
    def _calculate_psychological_score(self, level_price: float, current_price: float,
                                       level_type: str, interval: int) -> float:
        """
        Calculate score for psychological level
        
        Scoring factors:
        1. Roundness: How "round" the number is (major round numbers score higher)
        2. Proximity: Closer to current price = higher score
        3. Magnitude: Higher price levels get slightly more weight
        
        Args:
            level_price: Psychological level price
            current_price: Current market price
            level_type: "support" or "resistance"
            interval: Round number interval
            
        Returns:
            Score (0-100)
        """
        # Base score from roundness
        roundness_score = self._get_roundness_score(level_price, interval)
        
        # Proximity score (exponential decay with distance)
        proximity_score = self._get_proximity_score(level_price, current_price)
        
        # Combine: roundness (60%) + proximity (40%)
        # Roundness is more important for psychological levels
        combined_score = (roundness_score * 0.6) + (proximity_score * 0.4)
        
        return min(100.0, max(0.0, combined_score))
    
    def _get_roundness_score(self, price: float, interval: int) -> float:
        """
        Calculate roundness score based on interval strength
        
        Fixed intervals (from smallest to strongest):
        - $500: Smallest level (lowest score)
        - $1,000: Stronger level
        - $2,500: Stronger level
        - $5,000: Stronger level
        - $10,000: Stronger level
        - $100,000: Strongest level (highest score)
        
        Args:
            price: Price level
            interval: Round number interval (500, 1000, 2500, 5000, 10000, or 100000)
            
        Returns:
            Roundness score (0-100) based on interval strength
        """
        # Score based on interval strength (larger interval = stronger level)
        if interval == 500:
            return 20.0  # Smallest level
        elif interval == 1000:
            return 40.0  # Stronger level
        elif interval == 2500:
            return 60.0  # Stronger level
        elif interval == 5000:
            return 75.0  # Stronger level
        elif interval == 10000:
            return 90.0  # Stronger level
        elif interval == 100000:
            return 100.0  # Strongest level
        else:
            # Fallback for any other interval
            return 50.0
    
    def _get_proximity_score(self, level_price: float, current_price: float) -> float:
        """
        Calculate proximity score using exponential decay
        
        Closer levels get exponentially higher scores
        
        Args:
            level_price: Psychological level price
            current_price: Current market price
            
        Returns:
            Proximity score (0-100)
        """
        import math
        
        distance = abs(level_price - current_price)
        distance_pct = (distance / current_price) * 100.0 if current_price > 0 else 100.0
        
        # Exponential decay: k = 0.3 means:
        # - 0% distance: score = 100
        # - 1% distance: score ≈ 74
        # - 2% distance: score ≈ 55
        # - 5% distance: score ≈ 22
        k = 0.3
        proximity_score = 100.0 * math.exp(-k * distance_pct)
        
        return min(100.0, max(0.0, proximity_score))
    
    def _calculate_roundness_strength(self, price: float, interval: int) -> float:
        """
        Calculate strength based on roundness (for Level.strength field)
        
        Args:
            price: Price level
            interval: Round number interval
            
        Returns:
            Strength score (0-100)
        """
        return self._get_roundness_score(price, interval)

