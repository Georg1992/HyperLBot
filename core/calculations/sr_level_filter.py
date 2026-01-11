#!/usr/bin/env python3
"""
SR Level Filter Module
Handles all filtering logic for S/R levels based on different use cases
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from .base_calculator import BaseCalculator


class SRLevelFilter(BaseCalculator):
    """
    SR Level Filter - Centralized filtering logic for S/R levels
    
    Responsibilities:
    - Filter levels for entry setup generation (strategy-specific)
    - Filter levels for dashboard display
    - Filter levels for strategy selection
    - Filter levels for stop loss placement
    - Any other filtering needs
    
    This module ensures all filtering logic is in one place, making it:
    - Easier to maintain
    - More testable
    - More consistent
    - Better separation of concerns (calculator calculates, filter filters)
    """
    
    def __init__(self, symbol: str = "BTC"):
        """
        Initialize SR Level Filter
        
        Args:
            symbol: Trading symbol (default: "BTC")
        """
        super().__init__(symbol)
        logger.debug(f"SR Level Filter initialized for {symbol}")
    
    def filter_for_entry_setup(
        self,
        all_levels: List[Dict[str, Any]],
        current_price: float,
        strategy: str,
        direction: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter S/R levels for entry setup generation based on strategy requirements
        
        This replaces the top_2_support/top_2_resistance filtering that was in the calculator.
        Each module can now filter levels based on its specific needs.
        
        Args:
            all_levels: All available S/R levels from calculator
            current_price: Current market price
            strategy: Trading strategy name
            direction: Optional direction filter ("LONG" or "SHORT")
            
        Returns:
            Dictionary with "support" and "resistance" lists of filtered levels
        """
        from config.config import TradingConfig
        
        # Get strategy-specific configuration for SELECTION (not scoring)
        strategy_config = TradingConfig.SR_LEVEL_SELECTION.get(
            strategy or "standard", 
            TradingConfig.SR_LEVEL_SELECTION["standard"]
        )
        max_levels_per_side = strategy_config["max_levels_per_side"]
        min_level_distance_pct = strategy_config["min_level_distance_pct"]
        max_distance_pct = strategy_config.get("max_distance_pct", 0.10)
        
        # Filter for active levels in correct position relative to current price
        active_support_candidates = [
            level for level in all_levels
            if level.get("type") == "support"
            and level.get("price_level", 0) < current_price
            and level.get("status") == "active"
        ]
        
        active_resistance_candidates = [
            level for level in all_levels
            if level.get("type") == "resistance"
            and level.get("price_level", 0) > current_price
            and level.get("status") == "active"
        ]
        
        # Sort by strength score (universal scoring)
        active_support_candidates.sort(key=lambda x: x.get("strength_score", 0), reverse=True)
        active_resistance_candidates.sort(key=lambda x: x.get("strength_score", 0), reverse=True)
        
        # Apply strategy-specific proximity filtering (justified by expected price movement)
        if max_distance_pct > 0:
            max_distance = current_price * max_distance_pct
            active_support_candidates = [
                level for level in active_support_candidates
                if (current_price - level.get("price_level", 0)) <= max_distance
            ]
            active_resistance_candidates = [
                level for level in active_resistance_candidates
                if (level.get("price_level", 0) - current_price) <= max_distance
            ]
        
        # Apply minimum distance between levels filter
        filtered_support = []
        filtered_resistance = []
        
        for level in active_support_candidates:
            level_price = level.get("price_level", 0)
            # Check if too close to any already selected level
            too_close = any(
                abs(level_price - existing.get("price_level", 0)) <= current_price * min_level_distance_pct
                for existing in filtered_support
            )
            if not too_close and len(filtered_support) < max_levels_per_side:
                filtered_support.append(level)
        
        for level in active_resistance_candidates:
            level_price = level.get("price_level", 0)
            # Check if too close to any already selected level
            too_close = any(
                abs(level_price - existing.get("price_level", 0)) <= current_price * min_level_distance_pct
                for existing in filtered_resistance
            )
            if not too_close and len(filtered_resistance) < max_levels_per_side:
                filtered_resistance.append(level)
        
        # Apply direction filter if specified
        if direction == "LONG":
            return {"support": filtered_support, "resistance": []}
        elif direction == "SHORT":
            return {"support": [], "resistance": filtered_resistance}
        else:
            return {"support": filtered_support, "resistance": filtered_resistance}
    
    def filter_for_display(
        self,
        all_levels: List[Dict[str, Any]],
        current_price: float,
        max_levels: int = 2
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter S/R levels for dashboard display
        
        Args:
            all_levels: All available S/R levels
            current_price: Current market price
            max_levels: Maximum number of levels per side to display
            
        Returns:
            Dictionary with "support" and "resistance" lists
        """
        # Filter for active levels
        active_support = [
            level for level in all_levels
            if level.get("type") == "support"
            and level.get("price_level", 0) < current_price
            and level.get("status") == "active"
        ]
        
        active_resistance = [
            level for level in all_levels
            if level.get("type") == "resistance"
            and level.get("price_level", 0) > current_price
            and level.get("status") == "active"
        ]
        
        # Sort by strength score and take top N
        active_support.sort(key=lambda x: x.get("strength_score", 0), reverse=True)
        active_resistance.sort(key=lambda x: x.get("strength_score", 0), reverse=True)
        
        return {
            "support": active_support[:max_levels],
            "resistance": active_resistance[:max_levels]
        }
    
    def filter_for_strategy_selection(
        self,
        all_levels: List[Dict[str, Any]],
        current_price: float,
        max_levels: int = 2
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter S/R levels for strategy selection
        
        Args:
            all_levels: All available S/R levels
            current_price: Current market price
            max_levels: Maximum number of levels per side to use
            
        Returns:
            Dictionary with "support" and "resistance" lists
        """
        # Same logic as display filter (top N active levels by score)
        return self.filter_for_display(all_levels, current_price, max_levels)
    
    def filter_for_scoring(
        self,
        all_levels: List[Dict[str, Any]],
        current_price: float,
        max_levels: int = 2
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter S/R levels for factor scoring (e.g., in prediction engine)
        
        Args:
            all_levels: All available S/R levels
            current_price: Current market price
            max_levels: Maximum number of levels per side to use for scoring
            
        Returns:
            Dictionary with "support" and "resistance" lists
        """
        # Same logic as display filter (top N active levels by score)
        return self.filter_for_display(all_levels, current_price, max_levels)
