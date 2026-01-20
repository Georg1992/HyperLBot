#!/usr/bin/env python3
"""
Recency Calculator - Single source of truth for recency factor calculations
Strategy-aware recency calculation with consistent logic
"""

from typing import Dict, Any, Optional
from loguru import logger
from config.config import TradingConfig
from core.utils.time_utils import calculate_hours_since_touch


class RecencyCalculator:
    """
    Unified recency calculation with strategy-aware configuration
    
    Single source of truth for all recency factor calculations.
    Uses strategy-specific thresholds for consistent behavior.
    """
    
    @staticmethod
    def calculate_recency_factor(
        last_touch_timestamp: float,
        strategy: str = "standard",
        current_time: Optional[float] = None
    ) -> float:
        """
        Calculate recency factor using strategy-specific thresholds
        
        Args:
            last_touch_timestamp: Timestamp of last touch (0 if never touched)
            strategy: Trading strategy name
            current_time: Optional current time (uses time.time() if None)
            
        Returns:
            Recency factor (0.55-1.0) where 1.0 = very recent, lower = older
        """
        hours_since_touch = calculate_hours_since_touch(last_touch_timestamp, current_time)
        
        # Get strategy-specific recency configuration
        strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy] if strategy in TradingConfig.STRATEGY_CONFIGS else {}
        recency_config = strategy_config["recency_config"] if "recency_config" in strategy_config else {
            "very_recent_hours": 24.0,
            "recent_hours": 72.0,
            "old_hours": 168.0
        })
        
        very_recent_hours = recency_config["very_recent_hours"]  # Required (NO FALLBACKS)
        recent_hours = recency_config["recent_hours"]  # Required (NO FALLBACKS)
        old_hours = recency_config["old_hours"]  # Required (NO FALLBACKS)
        
        # Strategy-specific recency weighting
        if hours_since_touch <= very_recent_hours:
            return 1.0  # Full weight for very recent
        elif hours_since_touch <= recent_hours:
            return 0.85  # Slight reduction
        elif hours_since_touch <= old_hours:
            return 0.70  # Moderate reduction
        else:
            return 0.55  # Significant reduction for old levels
    
    @staticmethod
    def calculate_entry_recency_factor(
        last_touch_timestamp: float,
        strategy: str = "standard",
        current_time: Optional[float] = None
    ) -> float:
        """
        Calculate recency factor for entry scoring (slightly different thresholds)
        
        Args:
            last_touch_timestamp: Timestamp of last touch (0 if never touched)
            strategy: Trading strategy name
            current_time: Optional current time (uses time.time() if None)
            
        Returns:
            Recency factor (0.85-1.0) for entry scoring
        """
        hours_since_touch = calculate_hours_since_touch(last_touch_timestamp, current_time)
        
        # Get strategy-specific recency configuration
        strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy] if strategy in TradingConfig.STRATEGY_CONFIGS else {}
        recency_config = strategy_config["recency_config"] if "recency_config" in strategy_config else {
            "very_recent_hours": 24.0,
            "recent_hours": 72.0,
            "old_hours": 168.0
        })
        
        very_recent_hours = recency_config["very_recent_hours"]  # Required (NO FALLBACKS)
        recent_hours = recency_config["recent_hours"]  # Required (NO FALLBACKS)
        old_hours = recency_config["old_hours"]  # Required (NO FALLBACKS)
        
        # Entry-specific recency weighting (slightly more lenient)
        if hours_since_touch <= very_recent_hours:
            return 1.0
        elif hours_since_touch <= recent_hours:
            return 0.95
        elif hours_since_touch <= old_hours:
            return 0.90
        else:
            return 0.85
