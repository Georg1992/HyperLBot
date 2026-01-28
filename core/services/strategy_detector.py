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
        
        CRITICAL FIX: Simplified logic - uses StrategyManager as single source of truth.
        StrategyManager.detect_optimal_strategy() always returns self.current_strategy.
        Use strategy_manager.last_optimal_strategy to access optimal recommendation.
        
        Args:
            unified_data: Unified market data dictionary (must contain "timestamp")
            session_manager: SessionManager instance (optional)
            
        Returns:
            Current strategy name (from strategy_manager.current_strategy)
            
        Raises:
            ValueError: If strategy detection fails (NO FALLBACKS)
        """
        try:
            if not self.strategy_manager:
                raise ValueError("Strategy Manager not available - cannot detect strategy (NO FALLBACKS)")
            
            # CRITICAL FIX: Store previous strategy before detection
            previous_strategy = self.strategy_manager.current_strategy

            # Detect optimal strategy using comprehensive unified data
            # CRITICAL: detect_optimal_strategy() always returns self.current_strategy (source of truth)
            # The optimal recommendation is stored in strategy_manager.last_optimal_strategy
            actual_strategy = self.strategy_manager.detect_optimal_strategy(unified_data)
            
            # Get optimal strategy for logging (may differ from actual_strategy if cooldown blocked)
            optimal_strategy = self.strategy_manager.last_optimal_strategy

            # CRITICAL FIX: Simplified logic - only check if strategy actually changed
            if actual_strategy != previous_strategy:
                # Strategy actually changed (cooldown passed or no cooldown)
                logger.info(
                    f"🎯 Strategy updated: {previous_strategy} → {actual_strategy}"
                )
                logger.info(f"   📊 Market conditions: volatility={unified_data['volatility_category']}, trend={unified_data['trend']['direction']}")  # Required (NO FALLBACKS)
                
                # Update session manager with new strategy
                if session_manager and session_manager.current_session_data:
                    session_manager.current_session_data["strategy"] = actual_strategy
            elif optimal_strategy != actual_strategy:
                # Optimal strategy differs from current (cooldown blocked switch)
                logger.debug(
                    f"📊 Optimal strategy '{optimal_strategy}' detected but cooldown active "
                    f"(current: {actual_strategy}) - using '{actual_strategy}' for state, '{optimal_strategy}' for predictions"
                )
                # Don't update session manager state - strategy state unchanged
            else:
                # Strategy unchanged - ensure session manager has correct strategy
                if session_manager and session_manager.current_session_data:
                    current_session_strategy = session_manager.current_session_data.get("strategy")
                    if current_session_strategy != actual_strategy:
                        session_manager.current_session_data["strategy"] = actual_strategy
            
            # CRITICAL FIX: Expose both state_strategy and prediction_strategy
            # state_strategy: cooldown-protected persistent state (current_strategy)
            # prediction_strategy: optimal strategy for this tick (may differ during cooldown)
            unified_data["state_strategy"] = actual_strategy
            unified_data["strategy"] = actual_strategy  # Backwards compatibility
            
            # Set prediction_strategy to optimal if it differs from state, otherwise use state
            optimal_strategy = self.strategy_manager.last_optimal_strategy
            if optimal_strategy != actual_strategy:
                unified_data["prediction_strategy"] = optimal_strategy
                cooldown_blocked = True
            else:
                unified_data["prediction_strategy"] = actual_strategy
                cooldown_blocked = False
            
            # Log strategy routing clearly
            logger.info(
                f"📊 Strategy routing: state_strategy={actual_strategy}, "
                f"prediction_strategy={unified_data['prediction_strategy']}, "
                f"cooldown_blocked={cooldown_blocked}, "
                f"reason={self.strategy_manager.last_selection_reason}"
            )
            
            return actual_strategy

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
