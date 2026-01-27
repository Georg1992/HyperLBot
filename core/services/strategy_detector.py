#!/usr/bin/env python3
"""
Strategy Detector - Single Responsibility: Strategy Detection and Selection
Extracted from SessionOrchestrator for SRP compliance
"""

from typing import Dict, Any
from loguru import logger


class StrategyDetector:
    """Handles strategy detection and selection logic"""
    
    def __init__(self, strategy_manager, prediction_engine):
        """
        Initialize Strategy Detector
        
        Args:
            strategy_manager: StrategyManager instance
            prediction_engine: PredictionEngine instance
        """
        self.strategy_manager = strategy_manager
        self.prediction_engine = prediction_engine
    
    def detect_and_update_strategy(self, unified_data: Dict[str, Any], session_manager=None) -> str:
        """
        Detect and update strategy based on unified market data
        
        Args:
            unified_data: Unified market data dictionary
            session_manager: SessionManager instance (optional)
            
        Returns:
            Current strategy name
            
        Raises:
            ValueError: If strategy detection fails (NO FALLBACKS)
        """
        try:
            if not self.strategy_manager:
                raise ValueError("Strategy Manager not available - cannot detect strategy (NO FALLBACKS)")
            
            # Strategy is None initially (set in get_unified_analysis_data), use current_strategy from manager
            current_strategy = self.strategy_manager.current_strategy  # Use manager's current strategy

            # Detect optimal strategy using comprehensive unified data
            # NOTE: This may return optimal strategy for predictions even if cooldown blocks actual switch
            new_strategy = self.strategy_manager.detect_optimal_strategy(unified_data)
            
            # CRITICAL FIX: Check if strategy actually changed (not just returned for predictions)
            # If cooldown blocked the switch, current_strategy wasn't updated, so don't log as "updated"
            actual_current_strategy = self.strategy_manager.current_strategy

            if new_strategy != actual_current_strategy:
                # Strategy actually changed (cooldown passed or no cooldown)
                logger.info(
                    f"🎯 Strategy updated: {actual_current_strategy} → {new_strategy}"
                )
                logger.info(f"   📊 Market conditions: volatility={unified_data['volatility_category']}, trend={unified_data['trend']['direction']}")  # Required (NO FALLBACKS)
                
                # Update session manager with new strategy
                if session_manager and session_manager.current_session_data:
                    session_manager.current_session_data["strategy"] = new_strategy
                
                return new_strategy
            elif new_strategy != current_strategy:
                # Strategy would change but cooldown blocked it - using optimal for predictions only
                logger.debug(
                    f"📊 Optimal strategy '{new_strategy}' detected but cooldown active "
                    f"(current: {actual_current_strategy}) - using for predictions only"
                )
                # Don't update session manager - strategy state unchanged
                return actual_current_strategy
            else:
                # Even if unchanged, ensure session manager has the correct strategy
                if session_manager:
                    current_session_strategy = session_manager.current_session_data["strategy"]  # Required (NO FALLBACKS)
                    if current_session_strategy != current_strategy:
                        session_manager.current_session_data["strategy"] = current_strategy
                return current_strategy

        except Exception as e:
            logger.warning(f"⚠️ Strategy detection failed: {e}")
            raise  # NO FALLBACKS - detection failure should raise
    
    def filter_sr_levels_for_dashboard(self, unified_data: Dict[str, Any], 
                                      current_price: float, current_strategy: str) -> None:
        """
        Filter S/R levels for dashboard display based on current strategy
        
        Modifies unified_data in place
        """
        try:
            # get_support_resistance_analysis() guarantees valid dict or raises - trust API contract
            sr_data = unified_data["support_resistance"]
            from core.calculations.sr_level_filter import SRLevelFilter
            from config.config import TradingConfig
            
            # Get strategy-specific max_levels
            if current_strategy not in TradingConfig.SR_LEVEL_SELECTION:
                return
            
            strategy_config = TradingConfig.SR_LEVEL_SELECTION[current_strategy]
            max_levels = strategy_config["max_levels_per_side"]
            
            # Filter levels for dashboard (strategy-aware)
            level_filter = SRLevelFilter()
            all_levels = sr_data["levels"]
            sr_metadata = sr_data["metadata"]
            
            filtered_levels = level_filter.filter_for_display(
                all_levels=all_levels,
                current_price=current_price,
                max_levels=max_levels,  # Strategy-specific (scalping=1, swing=3)
                strategy=current_strategy,
                sr_metadata=sr_metadata  # Pass metadata for ATR calculation
            )
            
            # Update S/R data with strategy-filtered levels for dashboard
            if filtered_levels is not None:
                sr_data["key_levels"] = filtered_levels["support"] + filtered_levels["resistance"]
                sr_data["top_support"] = filtered_levels["support"]
                sr_data["top_resistance"] = filtered_levels["resistance"]
            
        except Exception as e:
            logger.error(f"❌ S/R level filtering failed: {e}")
            # Don't modify unified_data on error - keep original levels
