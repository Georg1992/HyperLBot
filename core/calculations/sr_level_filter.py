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
    
    def calculate_level_score(
        self,
        level: Dict[str, Any],
        current_price: float,
        current_time: float,
        atr_pct: float,
        strategy: str = "standard"
    ) -> float:
        """
        Calculate level quality score with STRATEGY-AWARE WEIGHTS.
        
        All factors are objective (calculated from market data), but WEIGHTS
        are strategy-specific to reflect what matters most for each trading style.
        
        Factors considered (strategy-weighted):
        1. Power (inherent strength: touches + volume + reversals)
        2. Proximity (distance from current price)
        3. Recency (how recently was it touched)
        4. MTF Confirmation (multiple timeframe alignment)
        5. Touch Count (how well-tested is this level)
        6. Cluster Size (how much evidence merged into this level)
        
        Args:
            level: Level dictionary with all metadata
            current_price: Current market price
            current_time: Current timestamp
            atr_pct: ATR as percentage (for distance normalization)
            strategy: Trading strategy (determines factor weights)
            
        Returns:
            Strategy-aware quality score (0-100)
        """
        try:
            if "price_level" not in level:
                raise ValueError(f"Level missing 'price_level' - required field (NO FALLBACKS)")
            level_price = level["price_level"]
            if level_price <= 0 or current_price <= 0:
                raise ValueError(f"Invalid prices: level={level_price}, current={current_price}")
            
            # ===================================================================
            # FACTOR 1: POWER (inherent strength)
            # Weight: Strategy-aware (15-60%)
            # ===================================================================
            if "power" not in level:
                raise ValueError(f"Level missing 'power' - required field (NO FALLBACKS)")
            power = level["power"]
            power = max(0.0, min(100.0, float(power)))  # Clamp 0-100
            power_score = power  # Already 0-100
            
            # ===================================================================
            # FACTOR 2: PROXIMITY (distance from current price)
            # Weight: Strategy-aware (5-45%)
            # ===================================================================
            distance_pct = abs(level_price - current_price) / current_price
            distance_atr = distance_pct / atr_pct if atr_pct > 0 else 999
            
            # Proximity scoring: 0 ATR = 100, 1 ATR = 85, 2 ATR = 70, 5 ATR = 40, 10+ ATR = 10
            if distance_atr <= 0.5:
                proximity_score = 100.0
            elif distance_atr <= 1.0:
                proximity_score = 100.0 - (distance_atr - 0.5) * 30  # 100 -> 85
            elif distance_atr <= 2.0:
                proximity_score = 85.0 - (distance_atr - 1.0) * 15   # 85 -> 70
            elif distance_atr <= 5.0:
                proximity_score = 70.0 - (distance_atr - 2.0) * 10   # 70 -> 40
            elif distance_atr <= 10.0:
                proximity_score = 40.0 - (distance_atr - 5.0) * 6    # 40 -> 10
            else:
                proximity_score = 10.0  # Very distant
            
            proximity_score = max(0.0, min(100.0, proximity_score))
            
            # ===================================================================
            # FACTOR 3: RECENCY (how recently touched)
            # Weight: Strategy-aware (5-25%)
            # ===================================================================
            if "last_touch_timestamp" not in level:
                raise ValueError(f"Level missing 'last_touch_timestamp' - required field (NO FALLBACKS)")
            last_touch = level["last_touch_timestamp"]
            
            hours_since_touch = (current_time - last_touch) / 3600.0
            
            # Recency scoring: <12h = 100, <24h = 90, <72h = 70, <168h = 50, <720h = 30, older = 10
            if hours_since_touch <= 12:
                recency_score = 100.0
            elif hours_since_touch <= 24:
                recency_score = 100.0 - (hours_since_touch - 12) * 0.83  # 100 -> 90
            elif hours_since_touch <= 72:
                recency_score = 90.0 - (hours_since_touch - 24) * 0.42   # 90 -> 70
            elif hours_since_touch <= 168:  # 1 week
                recency_score = 70.0 - (hours_since_touch - 72) * 0.21   # 70 -> 50
            elif hours_since_touch <= 720:  # 1 month
                recency_score = 50.0 - (hours_since_touch - 168) * 0.036 # 50 -> 30
            else:
                recency_score = max(10.0, 30.0 - (hours_since_touch - 720) * 0.01)  # Decay to 10
            
            recency_score = max(0.0, min(100.0, recency_score))
            
            # ===================================================================
            # FACTOR 4: MTF CONFIRMATION (multi-timeframe alignment)
            # Weight: Strategy-aware (8-20%)
            # ===================================================================
            mtf_confidence = level["mtf_confidence"] if "mtf_confidence" in level else 0.0  # Optional MTF data
            mtf_count = level["mtf_count"] if "mtf_count" in level else 0  # Optional MTF data
            
            # MTF scoring: confidence (0-1) * 100, with bonus for multiple TFs
            mtf_base_score = mtf_confidence * 100.0
            mtf_count_bonus = min(20.0, mtf_count * 5.0)  # Up to 20 bonus points
            mtf_score = min(100.0, mtf_base_score + mtf_count_bonus)
            
            # ===================================================================
            # FACTOR 5: TOUCH COUNT (how well-tested)
            # Uses volume-weighted touches (NO FALLBACKS)
            # ===================================================================
            weighted_touches = level.get("weighted_touches")
            if weighted_touches is None:
                raise ValueError(f"Level missing weighted_touches - required field (NO FALLBACKS)")
            
            effective_touches = weighted_touches
            
            # Touch scoring: 1 = 20, 2 = 40, 3 = 60, 5 = 80, 8+ = 100
            if effective_touches >= 8:
                touch_score = 100.0
            elif effective_touches >= 5:
                touch_score = 80.0 + (effective_touches - 5) * 6.67  # 80 -> 100
            elif effective_touches >= 3:
                touch_score = 60.0 + (effective_touches - 3) * 10    # 60 -> 80
            elif effective_touches >= 2:
                touch_score = 40.0 + (effective_touches - 2) * 20    # 40 -> 60
            else:
                touch_score = effective_touches * 20.0               # 0 -> 40
            
            touch_score = max(0.0, min(100.0, touch_score))
            
            # ===================================================================
            # FACTOR 6: CLUSTER SIZE (evidence consolidation)
            # Weight: 5% - Larger clusters indicate strong convergence
            # ===================================================================
            cluster_size = level["cluster_size"] if "cluster_size" in level else 1  # Optional cluster data
            
            # Cluster scoring: 1 = 30, 2 = 50, 3 = 70, 5 = 85, 10+ = 100
            if cluster_size >= 10:
                cluster_score = 100.0
            elif cluster_size >= 5:
                cluster_score = 85.0 + (cluster_size - 5) * 3.0  # 85 -> 100
            elif cluster_size >= 3:
                cluster_score = 70.0 + (cluster_size - 3) * 7.5  # 70 -> 85
            elif cluster_size >= 2:
                cluster_score = 50.0 + (cluster_size - 2) * 20   # 50 -> 70
            else:
                cluster_score = 30.0 + (cluster_size - 1) * 20   # 30 -> 50
            
            cluster_score = max(0.0, min(100.0, cluster_score))
            
            # ===================================================================
            # COMPOSITE SCORE (strategy-aware weighted combination)
            # ===================================================================
            from config.config import TradingConfig
            
            # Get strategy-specific weights
            weights = TradingConfig.SR_LEVEL_SCORING_WEIGHTS.get(
                strategy,
                TradingConfig.SR_LEVEL_SCORING_WEIGHTS["standard"]
            )
            
            composite_score = (
                power_score * weights["power"] +
                proximity_score * weights["proximity"] +
                recency_score * weights["recency"] +
                mtf_score * weights["mtf"] +
                touch_score * weights["touches"] +
                cluster_score * weights["cluster"]
            )
            
            # Log breakdown for debugging (only if score is significant)
            if composite_score > 50:
                logger.debug(
                    f"[{strategy}] Level @${level_price:.2f}: score={composite_score:.1f} "
                    f"(power={power_score:.0f}*{weights['power']:.2f}, "
                    f"prox={proximity_score:.0f}*{weights['proximity']:.2f}, "
                    f"rec={recency_score:.0f}*{weights['recency']:.2f}, "
                    f"mtf={mtf_score:.0f}*{weights['mtf']:.2f}, "
                    f"touch={touch_score:.0f}*{weights['touches']:.2f}, "
                    f"clust={cluster_score:.0f}*{weights['cluster']:.2f})"
                )
            
            return composite_score
            
        except Exception as e:
            logger.error(f"❌ Universal level scoring failed: {e}")
            return 0.0
    
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
        max_distance_pct = strategy_config["max_distance_pct"]  # Required (NO FALLBACKS)
        
        # Filter for active levels in correct position relative to current price
        active_support_candidates = [
            level for level in all_levels
            if "type" in level and level["type"] == "support"
            and "price_level" in level and level["price_level"] is not None
            and level["price_level"] < current_price
            and "status" in level and level["status"] == "active"
        ]
        
        active_resistance_candidates = [
            level for level in all_levels
            if level.get("type") == "resistance"
            and level.get("price_level") is not None
            and level.get("price_level") > current_price
            and level.get("status") == "active"
        ]
        
        # Sort by STRATEGY-AWARE QUALITY SCORE
        import time
        current_time = time.time()
        
        # Get ATR from levels metadata (REQUIRED)
        atr_pct = None
        if active_support_candidates or active_resistance_candidates:
            for level in (active_support_candidates + active_resistance_candidates):
                if "atr_pct" in level:
                    atr_pct = level["atr_pct"]
                    break
        
        if atr_pct is None:
            raise ValueError("No ATR data found in levels metadata (NO FALLBACKS)")
        
        # Calculate strategy-aware score for each level
        for level in active_support_candidates:
            level["_level_score"] = self.calculate_level_score(
                level, current_price, current_time, atr_pct, strategy
            )
        
        for level in active_resistance_candidates:
            level["_level_score"] = self.calculate_level_score(
                level, current_price, current_time, atr_pct, strategy
            )
        
        # Sort by strategy-aware score
        active_support_candidates.sort(key=lambda x: x["_level_score"], reverse=True)  # Required internal field (NO FALLBACKS)
        active_resistance_candidates.sort(key=lambda x: x["_level_score"], reverse=True)  # Required internal field (NO FALLBACKS)
        
        # Apply strategy-specific proximity filtering (justified by expected price movement)
        if max_distance_pct > 0:
            max_distance = current_price * max_distance_pct
            active_support_candidates = [
                level for level in active_support_candidates
                if (current_price - level["price_level"]) <= max_distance
            ]
            active_resistance_candidates = [
                level for level in active_resistance_candidates
                if (level["price_level"] - current_price) <= max_distance
            ]
        
        # Apply minimum distance between levels filter
        filtered_support = []
        filtered_resistance = []
        
        for level in active_support_candidates:
            level_price = level["price_level"]
            # Check if too close to any already selected level
            too_close = any(
                abs(level_price - existing["price_level"]) <= current_price * min_level_distance_pct
                for existing in filtered_support
            )
            if not too_close and len(filtered_support) < max_levels_per_side:
                filtered_support.append(level)
        
        for level in active_resistance_candidates:
            level_price = level["price_level"]
            # Check if too close to any already selected level
            too_close = any(
                abs(level_price - existing["price_level"]) <= current_price * min_level_distance_pct
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
        max_levels: int = 2,
        strategy: str = "standard"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter S/R levels for dashboard display
        
        Args:
            all_levels: All available S/R levels
            current_price: Current market price
            max_levels: Maximum number of levels per side to display
            strategy: Trading strategy (for scoring weights)
            
        Returns:
            Dictionary with "support" and "resistance" lists
        """
        # Filter for active levels
        active_support = [
            level for level in all_levels
            if "type" in level and level["type"] == "support"
            and "price_level" in level and level["price_level"] is not None
            and level["price_level"] < current_price
            and "status" in level and level["status"] == "active"
        ]
        
        active_resistance = [
            level for level in all_levels
            if level.get("type") == "resistance"
            and level.get("price_level") is not None
            and level.get("price_level") > current_price
            and level.get("status") == "active"
        ]
        
        # Sort by STRATEGY-AWARE QUALITY SCORE
        import time
        current_time = time.time()
        
        # Get ATR from levels metadata (REQUIRED)
        atr_pct = None
        if active_support or active_resistance:
            for level in (active_support + active_resistance):
                if "atr_pct" in level:
                    atr_pct = level["atr_pct"]
                    break
        
        if atr_pct is None:
            raise ValueError("No ATR data found in levels metadata (NO FALLBACKS)")
        
        # Calculate strategy-aware score for each level
        for level in active_support:
            level["_level_score"] = self.calculate_level_score(
                level, current_price, current_time, atr_pct, strategy
            )
        
        for level in active_resistance:
            level["_level_score"] = self.calculate_level_score(
                level, current_price, current_time, atr_pct, strategy
            )
        
        # Sort by strategy-aware score and take top N
        active_support.sort(key=lambda x: x["_level_score"], reverse=True)  # Required internal field (NO FALLBACKS)
        active_resistance.sort(key=lambda x: x["_level_score"], reverse=True)  # Required internal field (NO FALLBACKS)
        
        return {
            "support": active_support[:max_levels],
            "resistance": active_resistance[:max_levels]
        }
    
    def filter_for_strategy_selection(
        self,
        all_levels: List[Dict[str, Any]],
        current_price: float,
        max_levels: int = 2,
        strategy: str = "standard"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter S/R levels for strategy selection
        
        Args:
            all_levels: All available S/R levels
            current_price: Current market price
            max_levels: Maximum number of levels per side to use
            strategy: Trading strategy (for scoring weights)
            
        Returns:
            Dictionary with "support" and "resistance" lists
        """
        # Same logic as display filter (top N active levels by score)
        return self.filter_for_display(all_levels, current_price, max_levels, strategy)
    
    def filter_for_scoring(
        self,
        all_levels: List[Dict[str, Any]],
        current_price: float,
        max_levels: int = 2,
        strategy: str = "standard"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter S/R levels for factor scoring (e.g., in prediction engine)
        
        Args:
            all_levels: All available S/R levels
            current_price: Current market price
            max_levels: Maximum number of levels per side to use for scoring
            strategy: Trading strategy (for scoring weights)
            
        Returns:
            Dictionary with "support" and "resistance" lists
        """
        # Same logic as display filter (top N active levels by score)
        return self.filter_for_display(all_levels, current_price, max_levels, strategy)
