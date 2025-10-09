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
        Detect the optimal strategy using ML-powered analysis
        
        Args:
            market_data: Current market data (price, volatility, trend, volume, etc.)
            historical_context: Historical context from session manager
            
        Returns:
            str: Optimal strategy name
        """
        try:
            # Import ML Strategy Selector
            from core.ml.strategy_selector import global_ml_strategy_selector
            
            # Get ML strategy recommendation
            recommendation = global_ml_strategy_selector.select_strategy(
                market_data
            )
            
            optimal_strategy = recommendation.strategy
            confidence = recommendation.confidence
            reasoning = recommendation.reasoning
            
            # Log ML strategy selection
            logger.info(f"🤖 ML Strategy Analysis: {optimal_strategy} (confidence: {confidence:.3f})")
            logger.info(f"   📊 Reasoning: {reasoning}")
            
            # CRITICAL: Validate ML strategy against rule-based logic
            rule_based_strategy = self._rule_based_strategy(market_data, historical_context)
            
            # If ML and rules disagree significantly, use rule-based (more reliable)
            if optimal_strategy != rule_based_strategy:
                logger.warning(f"⚠️ ML/Rule mismatch: ML={optimal_strategy}, Rules={rule_based_strategy}")
                
                # Use rule-based if confidence is low or strategies are incompatible
                if confidence < 0.7 or self._are_strategies_incompatible(optimal_strategy, market_data):
                    logger.warning(f"🔄 Overriding ML with rule-based strategy: {rule_based_strategy}")
                    optimal_strategy = rule_based_strategy
                else:
                    logger.info(f"✅ ML strategy validated with high confidence ({confidence:.3f})")
            
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
            # Use rule-based selection when ML fails
            return self._rule_based_strategy(market_data, historical_context)
    
    def get_current_strategy_config(self) -> Dict[str, Any]:
        """Get current strategy configuration"""
        return self.current_strategy_config.copy()
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for specific strategy"""
        return self.strategy_configs.get(strategy_name, self.strategy_configs["standard"]).copy()
    
    
    
    def _analyze_market_conditions(self, volatility_5m: float, volatility_category: str, 
                                 trend: str, volume_category: str, rsi: float, 
                                 historical_context: Dict[str, Any] = None) -> str:
        """Analyze market conditions using DISTINCT, NON-OVERLAPPING strategy conditions"""
        
        # DISTINCT STRATEGY CONDITIONS (rule-based logic)
        
        # 1. SPIKE HUNTING - EXTREME volatility only (highest priority)
        if volatility_category == "EXTREME" and volatility_5m > 0.05:  # >5% volatility
            logger.info(f"🎯 Strategy: EXTREME volatility ({volatility_5m:.3f}) → spike_hunting")
            return "spike_hunting"
        
        # 2. SCALPING - MODERATE volatility + perfect liquidity conditions
        elif (volatility_category == "MODERATE" and 
              0.005 <= volatility_5m <= 0.02 and  # 0.5% - 2% volatility
              30 <= rsi <= 70 and  # Avoid extreme RSI zones
              volume_category in ["NORMAL", "HIGH", "VERY_HIGH"]):
            logger.info(f"🎯 Strategy: MODERATE volatility ({volatility_5m:.3f}) + good conditions → scalping")
            return "scalping"
        
        # 3. HIGH VOLATILITY - HIGH volatility but not extreme
        elif (volatility_category == "HIGH" and 
              0.02 < volatility_5m <= 0.05 and  # 2% - 5% volatility
              trend not in ["STRONG_UPTREND", "STRONG_DOWNTREND"]):  # Not strong trending
            logger.info(f"🎯 Strategy: HIGH volatility ({volatility_5m:.3f}) without strong trend → high_volatility")
            return "high_volatility"
        
        # 4. TREND FOLLOWING - MODERATE volatility + STRONG trend
        elif (volatility_category == "MODERATE" and 
              0.01 <= volatility_5m <= 0.02 and  # 1% - 2% volatility
              trend in ["STRONG_UPTREND", "STRONG_DOWNTREND"] and
              volume_category in ["HIGH", "VERY_HIGH"]):  # Need volume for trends
            logger.info(f"🎯 Strategy: STRONG trend ({trend}) + MODERATE volatility ({volatility_5m:.3f}) → trend_following")
            return "trend_following"
        
        # 5. LOW VOLATILITY RANGE - LOW/VERY_LOW volatility
        elif volatility_category in ["LOW", "VERY_LOW"] and volatility_5m < 0.01:  # <1% volatility
            logger.info(f"🎯 Strategy: {volatility_category} volatility ({volatility_5m:.3f}) → low_volatility_range")
            return "low_volatility_range"
        
        # 6. STANDARD - Everything else (default)
        else:
            logger.info(f"🎯 Strategy: Standard conditions ({volatility_category} volatility {volatility_5m:.3f}, {trend} trend) → standard")
            return "standard"
    
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
    
    def _rule_based_strategy(self, market_data: Dict[str, Any], historical_context: Dict[str, Any] = None) -> str:
        """Rule-based strategy selection when ML is unavailable"""
        try:
            current_price = market_data.get("current_price", 0)
            volatility_5m = market_data.get("volatility_5m", 0.0)
            volatility_category = market_data.get("volatility_5m_category", "MODERATE")
            trend = market_data.get("trend_5m", {}).get("trend", "NEUTRAL")
            volume_category = market_data.get("hyperliquid_volume", {}).get("volume_category", "NORMAL")
            rsi = market_data.get("rsi_5m", 50.0)
            
            logger.info(f"🎯 FALLBACK Strategy Detection: Analyzing market conditions at ${current_price:.2f}")
            logger.info(f"   📊 Volatility: {volatility_5m:.4f} ({volatility_category})")
            logger.info(f"   📈 Trend: {trend}")
            logger.info(f"   📊 Volume: {volume_category}")
            logger.info(f"   📊 RSI: {rsi:.1f}")
            
            # Strategy detection logic based on market conditions
            optimal_strategy = self._analyze_market_conditions(
                volatility_5m, volatility_category, trend, volume_category, rsi, historical_context
            )
            
            # Check if strategy switch is needed and allowed
            if optimal_strategy != self.current_strategy:
                if self._can_switch_strategy():
                    logger.info(f"🔄 Fallback Strategy switch: {self.current_strategy} → {optimal_strategy}")
                    self._switch_strategy(optimal_strategy)
                else:
                    logger.info(f"⏳ Fallback Strategy switch blocked (cooldown): {self.current_strategy} → {optimal_strategy}")
            
            return self.current_strategy
            
        except Exception as e:
            logger.error(f"❌ Fallback strategy detection failed: {e}")
            return self.current_strategy
    
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
    
