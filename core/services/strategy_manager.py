#!/usr/bin/env python3
"""
Strategy Manager
Centralized strategy detection, selection, and management
Single Responsibility: Strategy decision making and configuration
"""

import time
from typing import Dict, Any, Optional, List
from loguru import logger
from config.config import TradingConfig


class StrategyManager:
    """
    Centralized strategy management component
    
    RESPONSIBILITIES:
    1. Detect optimal strategy based on market conditions
    2. Manage strategy switching during session
    3. Provide strategy-specific configurations to engines
    4. Validate strategy appropriateness for current conditions
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.strategy_configs = config.STRATEGY_CONFIGS
        
        # Current strategy state
        self.current_strategy = "standard"
        self.current_strategy_config = self.strategy_configs["standard"]
        self.last_strategy_switch = 0
        self.strategy_switch_cooldown = 300  # 5 minutes between switches
        
        # Strategy performance tracking
        self.strategy_performance = {}
        self.strategy_usage_count = {}
        
        # Initialize performance tracking
        for strategy_name in self.strategy_configs.keys():
            self.strategy_performance[strategy_name] = {
                "total_trades": 0,
                "successful_trades": 0,
                "total_profit": 0.0,
                "last_used": 0
            }
            self.strategy_usage_count[strategy_name] = 0
        
        logger.info("🎯 Strategy Manager initialized - Centralized strategy management")
        logger.info(f"   🎯 Current strategy: {self.current_strategy}")
    
    def detect_optimal_strategy(self, market_data: Dict[str, Any], historical_context: Dict[str, Any] = None) -> str:
        """
        Detect the optimal strategy using ML-powered analysis (SINGLE SOURCE OF TRUTH)
        
        Args:
            market_data: Current market data (price, volatility, trend, volume, etc.)
            historical_context: Historical context from session manager
            
        Returns:
            str: Current active strategy name
        """
        try:
            # Import ML Strategy Selector
            from core.ml.strategy_selector import global_ml_strategy_selector
            
            # Enrich market data with historical context for better ML decisions
            enriched_data = self._enrich_market_data(market_data, historical_context)
            
            # Get ML strategy recommendation (SINGLE SOURCE OF TRUTH)
            recommendation = global_ml_strategy_selector.select_strategy(enriched_data)
            
            optimal_strategy = recommendation.strategy
            confidence = recommendation.confidence
            reasoning = recommendation.reasoning
            
            # Log ML strategy selection
            logger.info(f"🤖 ML Strategy Decision: {optimal_strategy} (confidence: {confidence:.3f})")
            logger.info(f"   📊 Reasoning: {reasoning}")
            
            # Validate strategy is not incompatible with current market conditions
            if self._are_strategies_incompatible(optimal_strategy, market_data):
                logger.warning(f"⚠️ Strategy {optimal_strategy} incompatible with market conditions")
                logger.warning(f"   Falling back to 'standard' strategy")
                optimal_strategy = "standard"
            
            # Check if strategy switch is needed and allowed
            if optimal_strategy != self.current_strategy:
                if self._can_switch_strategy():
                    logger.info(f"🔄 Strategy switch: {self.current_strategy} → {optimal_strategy}")
                    self._switch_strategy(optimal_strategy)
                    
                    # Record strategy selection for learning
                    self._record_strategy_selection(optimal_strategy, market_data, recommendation)
                else:
                    logger.info(f"⏳ Strategy switch blocked (cooldown): {self.current_strategy} → {optimal_strategy}")
            else:
                # Still record for learning even if no switch
                self._record_strategy_selection(optimal_strategy, market_data, recommendation)
            
            return self.current_strategy
            
        except Exception as e:
            logger.error(f"❌ ML strategy detection failed: {e}")
            logger.error(f"   Using current strategy: {self.current_strategy}")
            return self.current_strategy
    
    def get_current_strategy_config(self) -> Dict[str, Any]:
        """Get current strategy configuration"""
        return self.current_strategy_config.copy()
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for specific strategy"""
        return self.strategy_configs.get(strategy_name, self.strategy_configs["standard"]).copy()
    
    def _enrich_market_data(self, market_data: Dict[str, Any], historical_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enrich market data with historical context and derived metrics for better ML decisions
        
        Args:
            market_data: Current market data
            historical_context: Historical context from session manager
            
        Returns:
            Dict: Enriched market data with additional context
        """
        enriched = market_data.copy()
        
        # Add historical context if available
        if historical_context:
            enriched["historical_context"] = historical_context
            
            # Add recent strategy performance if available
            if "strategy_performance" in historical_context:
                enriched["strategy_performance"] = historical_context["strategy_performance"]
        
        # Add current strategy info for context
        enriched["current_strategy"] = self.current_strategy
        enriched["time_in_strategy"] = time.time() - self.last_strategy_switch
        
        # Add strategy usage statistics
        enriched["strategy_usage"] = self.strategy_usage_count.copy()
        
        return enriched
    
    
    def _are_strategies_incompatible(self, strategy: str, market_data: Dict[str, Any]) -> bool:
        """
        Validate if a strategy is incompatible with current market conditions
        Returns True if strategy SHOULD NOT be used
        """
        try:
            trend = market_data.get("trend", "SIDEWAYS")
            volatility_5m = market_data.get("volatility_5m", 0)
            volatility_category = market_data.get("volatility_category", "LOW")
            volume_category = market_data.get("volume_category", "LOW")
            
            # TREND FOLLOWING incompatibility checks
            if strategy == "trend_following":
                # CRITICAL: Trend Following requires STRONG trend
                if trend not in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
                    logger.warning(f"❌ INCOMPATIBLE: trend_following requires STRONG trend, got {trend}")
                    return True
                # Requires HIGH/VERY_HIGH volume
                if volume_category not in ["HIGH", "VERY_HIGH"]:
                    logger.warning(f"❌ INCOMPATIBLE: trend_following requires HIGH volume, got {volume_category}")
                    return True
                # Requires MODERATE volatility
                if volatility_category not in ["MODERATE"]:
                    logger.warning(f"❌ INCOMPATIBLE: trend_following requires MODERATE volatility, got {volatility_category}")
                    return True
            
            # SPIKE HUNTING incompatibility checks
            elif strategy == "spike_hunting":
                if volatility_category != "EXTREME":
                    logger.warning(f"❌ INCOMPATIBLE: spike_hunting requires EXTREME volatility, got {volatility_category}")
                    return True
            
            # SCALPING incompatibility checks
            elif strategy == "scalping":
                if volatility_category != "MODERATE":
                    logger.warning(f"❌ INCOMPATIBLE: scalping requires MODERATE volatility, got {volatility_category}")
                    return True
                if volume_category == "VERY_LOW":
                    logger.warning(f"❌ INCOMPATIBLE: scalping requires decent volume, got {volume_category}")
                    return True
            
            # HIGH VOLATILITY incompatibility checks
            elif strategy == "high_volatility":
                if volatility_category != "HIGH":
                    logger.warning(f"❌ INCOMPATIBLE: high_volatility requires HIGH volatility, got {volatility_category}")
                    return True
                # Should NOT be used with strong trends (that's trend following territory)
                if trend in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
                    logger.warning(f"❌ INCOMPATIBLE: high_volatility conflicts with STRONG trend {trend}")
                    return True
            
            # RANGE TRADING incompatibility checks
            elif strategy == "range_trading":
                if volatility_category in ["EXTREME"]:
                    logger.warning(f"❌ INCOMPATIBLE: range_trading not suitable for EXTREME volatility, got {volatility_category}")
                    return True
            
            # LOW VOLATILITY RANGE incompatibility checks
            elif strategy == "low_volatility_range":
                if volatility_category not in ["LOW", "VERY_LOW"]:
                    logger.warning(f"❌ INCOMPATIBLE: low_volatility_range requires LOW volatility, got {volatility_category}")
                    return True
            
            # Strategy is compatible
            return False
            
        except Exception as e:
            logger.error(f"❌ Strategy compatibility check failed: {e}")
            return False  # Allow strategy if check fails
    
    def _can_switch_strategy(self) -> bool:
        """Check if strategy switching is allowed (cooldown period)"""
        current_time = time.time()
        time_since_last_switch = current_time - self.last_strategy_switch
        return time_since_last_switch >= self.strategy_switch_cooldown
    
    def _switch_strategy(self, new_strategy: str):
        """Switch to new strategy"""
        try:
            old_strategy = self.current_strategy
            self.current_strategy = new_strategy
            self.current_strategy_config = self.strategy_configs.get(new_strategy, self.strategy_configs["standard"])
            self.last_strategy_switch = time.time()
            
            logger.info(f"🔄 Strategy switched: {old_strategy} → {new_strategy}")
            logger.info(f"   📊 New config: {self.current_strategy_config}")
            
            # Update trading logger with new strategy
            try:
                from core.logging.trading_logger import get_global_trading_logger
                trading_logger = get_global_trading_logger()
                if trading_logger:
                    trading_logger.update_strategy(new_strategy)
            except Exception as e:
                logger.warning(f"⚠️ Could not update trading logger strategy: {e}")
            
            # Update prediction engine confidence threshold
            try:
                from core.ml.realtime_prediction_engine import get_global_prediction_engine
                prediction_engine = get_global_prediction_engine()
                if prediction_engine:
                    prediction_engine.update_confidence_threshold(new_strategy)
            except Exception as e:
                logger.warning(f"⚠️ Could not update prediction engine threshold: {e}")
            
            # Notify SessionManager of strategy change for dashboard update
            self._notify_session_strategy_change(new_strategy)
            
        except Exception as e:
            logger.error(f"❌ Strategy switch failed: {e}")
            # Revert to previous strategy
            self.current_strategy = "standard"
            self.current_strategy_config = self.strategy_configs["standard"]
    
    def force_strategy(self, strategy_name: str) -> bool:
        """Force switch to specific strategy (bypass cooldown)"""
        try:
            if strategy_name not in self.strategy_configs:
                logger.error(f"❌ Unknown strategy: {strategy_name}")
                return False
            
            self._switch_strategy(strategy_name)
            logger.info(f"🔧 Strategy forced to: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Force strategy failed: {e}")
            return False
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategies"""
        return list(self.strategy_configs.keys())
    
    def get_strategy_description(self, strategy_name: str) -> str:
        """Get human-readable description of strategy"""
        descriptions = {
            "standard": "Balanced strategy for normal market conditions",
            "low_volatility_range": "Optimized for LOW and VERY_LOW volatility, range-bound markets with support/resistance",
            "high_volatility": "Designed for high volatility, trending markets",
            "spike_hunting": "Specialized for extreme volatility and price spikes",
            "trend_following": "Optimized for strong trending markets with momentum confirmation",
            "scalping": "High-frequency scalping for small, quick profits with tight risk management",
        }
        return descriptions.get(strategy_name, "Unknown strategy")
    
    def _record_strategy_selection(self, strategy: str, market_data: Dict[str, Any], recommendation) -> None:
        """Record strategy selection for ML learning"""
        try:
            from core.ml.strategy_selector import global_ml_strategy_selector
            
            # Record the strategy selection (without outcome yet)
            # The outcome will be recorded later when trades are executed
            selection_record = {
                "strategy": strategy,
                "market_conditions": market_data,
                "confidence": recommendation.confidence,
                "reasoning": recommendation.reasoning,
                "timestamp": time.time()
            }
            
            # Store for later outcome recording
            if not hasattr(self, 'pending_strategy_outcomes'):
                self.pending_strategy_outcomes = []
            
            self.pending_strategy_outcomes.append(selection_record)
            
            # Keep only recent records
            if len(self.pending_strategy_outcomes) > 100:
                self.pending_strategy_outcomes = self.pending_strategy_outcomes[-100:]
            
            logger.debug(f"📊 Strategy selection recorded: {strategy} (confidence: {recommendation.confidence:.3f})")
            
        except Exception as e:
            logger.error(f"❌ Strategy selection recording failed: {e}")
    
    def record_strategy_outcome(self, strategy: str, outcome: Dict[str, Any]) -> None:
        """Record the outcome of a strategy for ML learning"""
        try:
            from core.ml.strategy_selector import global_ml_strategy_selector
            
            # Find the most recent selection for this strategy
            if hasattr(self, 'pending_strategy_outcomes'):
                for record in reversed(self.pending_strategy_outcomes):
                    if record["strategy"] == strategy:
                        # Record outcome with ML strategy selector
                        global_ml_strategy_selector.record_strategy_outcome(
                            strategy, record["market_conditions"], outcome
                        )
                        
                        # Remove from pending
                        self.pending_strategy_outcomes.remove(record)
                        break
            
            # Also update local performance tracking
            if strategy not in self.strategy_performance:
                self.strategy_performance[strategy] = {
                    "total_trades": 0,
                    "successful_trades": 0,
                    "total_profit": 0.0,
                    "last_used": 0
                }
            
            perf = self.strategy_performance[strategy]
            perf["total_trades"] += 1
            perf["last_used"] = time.time()
            
            # Calculate success and profit
            profit = outcome.get("profit", 0.0)
            success = outcome.get("success", profit > 0)
            
            if success:
                perf["successful_trades"] += 1
            
            perf["total_profit"] += profit
            
            logger.info(f"📊 Strategy outcome recorded: {strategy} - Profit: {profit:.4f}, Success: {success}")
            
        except Exception as e:
            logger.error(f"❌ Strategy outcome recording failed: {e}")
    
    def get_ml_strategy_performance(self) -> Dict[str, Any]:
        """Get ML strategy performance statistics"""
        try:
            from core.ml.strategy_selector import global_ml_strategy_selector
            return global_ml_strategy_selector.get_strategy_performance()
        except Exception as e:
            logger.error(f"❌ Failed to get ML strategy performance: {e}")
            return {"error": str(e)}
    
    def _notify_session_strategy_change(self, new_strategy: str):
        """Notify SessionManager of strategy change for dashboard update"""
        try:
            # Import here to avoid circular imports
            from core.session.session_manager import session_manager
            
            # Update session data with new strategy
            if hasattr(session_manager, 'current_session_data') and session_manager.current_session_data:
                session_manager.current_session_data["strategy"] = new_strategy
                
                # Sync updated session data to dashboard
                # Get dashboard service and update
                from core.services.system_initializer import get_system_initializer
                system_initializer = get_system_initializer()
                dashboard_service = system_initializer.singleton_systems.get("dashboard_service")
                if dashboard_service:
                    dashboard_service.sync_from_session_manager(session_manager.current_session_data)
                    dashboard_service.add_activity(f"🔄 Strategy switched to: {new_strategy}", "INFO", "strategy")
                
                logger.info(f"📊 Dashboard notified of strategy change: {new_strategy}")
            
        except Exception as e:
            logger.error(f"❌ Failed to notify session of strategy change: {e}")
    
