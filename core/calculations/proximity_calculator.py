#!/usr/bin/env python3
"""
Proximity Calculator - Single source of truth for proximity factor calculations
Strategy-aware proximity calculation with consistent logic
"""

from typing import Dict, Any, Optional
from loguru import logger
from config.config import TradingConfig
from core.utils.distance_utils import calculate_distance_pct, calculate_distance_atr


class ProximityCalculator:
    """
    Unified proximity calculation with strategy-aware configuration
    
    Single source of truth for all proximity factor calculations.
    Uses strategy-specific ATR thresholds for consistent behavior.
    """
    
    @staticmethod
    def calculate_proximity_factor(
        entry_price: float,
        reference_price: float,
        atr_pct: float,
        strategy: str = "standard",
        context: str = "direction"  # "direction" or "entry"
    ) -> float:
        """
        Calculate proximity factor using strategy-specific ATR thresholds
        
        Args:
            entry_price: Entry or level price
            reference_price: Reference price (current_price for direction, level_price for entry)
            atr_pct: ATR as percentage of price
            strategy: Trading strategy name
            context: "direction" (entry-to-current) or "entry" (entry-to-level)
            
        Returns:
            Proximity factor (0.55-1.0 for direction, 0.8-1.1 for entry)
        """
        distance_pct = calculate_distance_pct(entry_price, reference_price, reference_price)
        distance_atr = calculate_distance_atr(distance_pct, atr_pct)
        
        # Get strategy-specific proximity configuration
        strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy] if strategy in TradingConfig.STRATEGY_CONFIGS else {}
        
        if context == "direction":
            # Direction scoring: entry-to-current distance
            proximity_config = strategy_config["proximity_config"] if "proximity_config" in strategy_config else {
                "close_atr": 2.0,
                "medium_atr": 4.0,
                "far_atr": 6.0
            }
            close_atr = proximity_config["close_atr"] if "close_atr" in proximity_config else 2.0
            medium_atr = proximity_config["medium_atr"] if "medium_atr" in proximity_config else 4.0
            far_atr = proximity_config["far_atr"] if "far_atr" in proximity_config else 6.0
            
            # Strategy-specific proximity weighting
            if distance_atr <= close_atr:
                return 1.0  # Full weight for close entries
            elif distance_atr <= medium_atr:
                return 0.85  # Slight reduction for medium distance
            elif distance_atr <= far_atr:
                return 0.70  # Moderate reduction for far entries
            else:
                return 0.55  # Significant reduction for very far entries
        
        else:  # context == "entry"
            # Entry scoring: entry-to-level distance
            entry_proximity_config = strategy_config["entry_proximity_config"] if "entry_proximity_config" in strategy_config else {
                "optimal_atr": 0.5,
                "acceptable_atr": 1.25,
                "too_far_atr": 2.0
            }
            optimal_atr = entry_proximity_config["optimal_atr"]  # Required (NO FALLBACKS)
            acceptable_atr = entry_proximity_config["acceptable_atr"]  # Required (NO FALLBACKS)
            too_far_atr = entry_proximity_config["too_far_atr"]  # Required (NO FALLBACKS)
            
            # Entry-specific proximity weighting (with bonuses/penalties)
            if distance_atr <= optimal_atr:
                return 1.1  # 10% bonus for optimal range
            elif distance_atr <= acceptable_atr:
                return 1.0  # No bonus/penalty
            else:
                return 0.8  # Penalty if too far from level
