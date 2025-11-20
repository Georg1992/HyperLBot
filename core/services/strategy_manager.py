#!/usr/bin/env python3
"""
Strategy Manager
Centralized strategy detection, selection, and management
Single Responsibility: Strategy decision making and configuration
"""

import time
from typing import Dict, Any, List
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
    
    def detect_optimal_strategy(self, market_data: Dict[str, Any]) -> str:
        """
        Detect the optimal strategy using ML-powered analysis (SINGLE SOURCE OF TRUTH)
        
        Args:
            market_data: Current market data (price, volatility, trend, volume, etc.)
            
        Returns:
            str: Current active strategy name
        """
        try:
            # Pure business logic strategy selection (no ML for now)
            recommendation = self._select_strategy_business_logic(market_data)
            optimal_strategy = recommendation.strategy
            reasoning = recommendation.reasoning
            
            # Store market data for dynamic cooldown calculation
            self._last_market_data = market_data.copy()
            
            # Log business logic strategy selection
            logger.info(f"📊 Business Logic Strategy Decision: {optimal_strategy}")
            logger.info(f"   📊 Reasoning: {reasoning}")
            
            # Validate strategy is not incompatible with current market conditions
            # Use same market_data to ensure consistency with ML model
            if self._are_strategies_incompatible(optimal_strategy, market_data):
                logger.warning(f"⚠️ Strategy {optimal_strategy} incompatible with market conditions")
                # Find next best strategy instead of fallback
                optimal_strategy = self._find_next_best_strategy(market_data, optimal_strategy)
                logger.info(f"🔄 Selected alternative strategy: {optimal_strategy}")
            
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
            logger.error(f"❌ Strategy detection failed: {e}")
            logger.error(f"   Using current strategy: {self.current_strategy}")
            return self.current_strategy
    
    def _select_strategy_business_logic(self, market_data: Dict[str, Any]) -> str:
        """Select strategy using pure business logic (no ML) - Complete implementation"""
        try:
            # Extract market conditions from unified data structure (using flattened fields)
            volatility_category = market_data.get("volatility_category", "MODERATE")
            trend_direction = market_data.get("trend_direction", "SIDEWAYS")
            volume_category = market_data.get("volume_category", "MODERATE")
            volatility_5m = market_data.get("volatility_5m", 0.0)
            rsi_value = market_data.get("rsi_value", 50.0)
            
            logger.debug(f"📊 Strategy selection inputs: volatility={volatility_category}, trend={trend_direction}, volume={volume_category}, vol_5m={volatility_5m:.3f}, rsi={rsi_value:.1f}")
            
            # Complete business logic strategy selection with all strategies
            # Priority 1: Spike Hunting (EXTREME volatility + high volume)
            if volatility_5m > 0.05 or volatility_category == "EXTREME":  # 5%+ volatility
                if volume_category in ["HIGH", "VERY_HIGH"]:
                    strategy = "spike_hunting"
                    reasoning = f"Extreme volatility ({volatility_5m:.1%}) + high volume"
                else:
                    strategy = "high_volatility"
                    reasoning = f"Extreme volatility ({volatility_5m:.1%}) + moderate volume"
            
            # Priority 2: Scalping (MODERATE volatility + good RSI + decent volume)
            elif volatility_category == "MODERATE" and 30 <= rsi_value <= 70 and volume_category in ["NORMAL", "HIGH", "VERY_HIGH"]:
                strategy = "scalping"
                reasoning = f"Moderate volatility + good RSI ({rsi_value:.1f}) + decent volume"
            
            # Priority 3: High Volatility (HIGH volatility + no strong trend)
            elif volatility_category in ["HIGH", "VERY_HIGH"]:
                if trend_direction in ["BULLISH", "BEARISH"]:
                    strategy = "trend_following"
                    reasoning = f"High volatility ({volatility_category}) + strong trend ({trend_direction})"
                else:
                    strategy = "high_volatility"
                    reasoning = f"High volatility ({volatility_category}) + sideways trend"
            
            # Priority 4: Trend Following (strong trend + high volume + moderate volatility)
            elif trend_direction in ["BULLISH", "BEARISH"] and volume_category in ["HIGH", "VERY_HIGH"] and volatility_category in ["MODERATE", "HIGH"]:
                strategy = "trend_following"
                reasoning = f"Strong trend ({trend_direction}) + high volume + {volatility_category} volatility"
            
            # Priority 5: Breakout (moderate-high volatility + trending conditions)
            elif volatility_category in ["MODERATE", "HIGH"] and trend_direction in ["BULLISH", "BEARISH"] and volume_category in ["NORMAL", "HIGH", "VERY_HIGH"]:
                strategy = "breakout"
                reasoning = f"Breakout conditions: {volatility_category} volatility + {trend_direction} trend"
            
            # Priority 6: Range Trading (moderate volatility + sideways trend)
            elif volatility_category in ["MODERATE", "LOW"] and trend_direction == "SIDEWAYS":
                strategy = "range_trading"
                reasoning = f"Range trading: {volatility_category} volatility + sideways trend"
            
            # Priority 7: Low Volatility Range (LOW/VERY_LOW volatility + sideways)
            elif volatility_category in ["LOW", "VERY_LOW"]:
                if trend_direction == "SIDEWAYS":
                    strategy = "low_volatility_range"
                    reasoning = f"Low volatility range: {volatility_category} + sideways trend"
                else:
                    strategy = "range_trading"
                    reasoning = f"Low volatility + trending market: {trend_direction}"
            
            # Fallback: Standard strategy
            else:
                strategy = "standard"
                reasoning = f"Standard fallback: {volatility_category} volatility + {trend_direction} trend + {volume_category} volume"
            
            # Create simple recommendation object
            class SimpleRecommendation:
                def __init__(self, strategy, reasoning):
                    self.strategy = strategy
                    self.reasoning = reasoning
                    self.confidence = 0.8  # Fixed confidence for business logic
            
            return SimpleRecommendation(strategy, reasoning)
                
        except Exception as e:
            logger.warning(f"⚠️ Business logic strategy selection failed: {e}")
            # Create fallback recommendation
            class SimpleRecommendation:
                def __init__(self, strategy, reasoning):
                    self.strategy = strategy
                    self.reasoning = reasoning
                    self.confidence = 0.5  # Lower confidence for fallback
            
            return SimpleRecommendation("standard", "Fallback due to error")
    
    def get_current_strategy_config(self) -> Dict[str, Any]:
        """Get current strategy configuration"""
        return self.current_strategy_config.copy()
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for specific strategy"""
        return self.strategy_configs.get(strategy_name, self.strategy_configs["standard"]).copy()
    
    
    def _are_strategies_incompatible(self, strategy: str, market_data: Dict[str, Any]) -> bool:
        """
        Validate if a strategy is incompatible with current market conditions
        Returns True if strategy SHOULD NOT be used
        """
        try:
            # Use flattened fields as single source of truth; fall back to nested if needed
            trend_direction = market_data.get("trend_direction")
            if not trend_direction:
                trend_data = market_data.get("trend", {})
                trend_direction = trend_data.get("direction", "SIDEWAYS") if isinstance(trend_data, dict) else str(trend_data)
            volatility_5m = market_data.get("volatility_5m", 0)
            volatility_category = market_data.get("volatility_category", "LOW")
            volume_category = market_data.get("volume_category", "LOW")
            
            # TREND FOLLOWING incompatibility checks
            if strategy == "trend_following":
                if trend_direction not in ["BULLISH", "BEARISH"]:
                    logger.warning(f"❌ INCOMPATIBLE: trend_following requires trending market, got {trend_direction}")
                    return True
                if volume_category in ["VERY_LOW"]:
                    logger.warning(f"❌ INCOMPATIBLE: trend_following requires decent volume, got {volume_category}")
                    return True
                if volatility_category == "EXTREME":
                    logger.warning(f"❌ INCOMPATIBLE: trend_following too risky in EXTREME volatility, got {volatility_category}")
                    return True
            
            # SPIKE HUNTING incompatibility checks
            elif strategy == "spike_hunting":
                if not (volatility_5m > 0.05 or volatility_category == "EXTREME"):
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
                if volatility_category not in ["HIGH", "VERY_HIGH", "EXTREME"]:
                    logger.warning(f"❌ INCOMPATIBLE: high_volatility requires HIGH+ volatility, got {volatility_category}")
                    return True
                if trend_direction in ["BULLISH", "BEARISH"] and volatility_category != "EXTREME":
                    logger.warning(f"❌ INCOMPATIBLE: high_volatility conflicts with strong trend {trend_direction}")
                    return True
            
            # RANGE TRADING incompatibility checks
            elif strategy == "range_trading":
                if trend_direction != "SIDEWAYS":
                    logger.warning(f"❌ INCOMPATIBLE: range_trading expects sideways market, got {trend_direction}")
                    return True
            
            # BREAKOUT incompatibility checks
            elif strategy == "breakout":
                if volatility_category in ["VERY_LOW", "LOW"]:
                    logger.warning(f"❌ INCOMPATIBLE: breakout requires higher volatility, got {volatility_category}")
                    return True
            
            # LOW VOLATILITY RANGE incompatibility checks
            elif strategy == "low_volatility_range":
                if volatility_category not in ["LOW", "VERY_LOW"] or trend_direction != "SIDEWAYS":
                    logger.warning(f"❌ INCOMPATIBLE: low_volatility_range requires LOW volatility and SIDEWAYS, got {volatility_category} + {trend_direction}")
                    return True
            
            # Strategy is compatible
            return False
            
        except Exception as e:
            logger.error(f"❌ Strategy compatibility check failed: {e}")
            return False  # Allow strategy if check fails
    
    def _can_switch_strategy(self) -> bool:
        """Check if strategy switching is allowed (dynamic cooldown based on volatility)"""
        current_time = time.time()
        time_since_last_switch = current_time - self.last_strategy_switch
        
        # Dynamic cooldown based on market volatility
        # Get current volatility from the last market data if available
        if hasattr(self, '_last_market_data'):
            volatility_5m = self._last_market_data.get("volatility_5m", 0.0)
            if volatility_5m > 0.03:  # High volatility (>3%)
                cooldown = 60  # 1 minute for high volatility
            elif volatility_5m > 0.01:  # Moderate volatility (1-3%)
                cooldown = 180  # 3 minutes for moderate volatility
            else:  # Low volatility (<1%)
                cooldown = 300  # 5 minutes for low volatility
        else:
            cooldown = self.strategy_switch_cooldown  # Default 5 minutes
        
        return time_since_last_switch >= cooldown
    
    def _switch_strategy(self, new_strategy: str):
        """Switch to new strategy"""
        try:
            old_strategy = self.current_strategy
            self.current_strategy = new_strategy
            self.current_strategy_config = self.strategy_configs.get(new_strategy, self.strategy_configs["standard"])
            self.last_strategy_switch = time.time()
            
            logger.info(f"🔄 Strategy switched: {old_strategy} → {new_strategy}")
            logger.info(f"   📊 New config: {self.current_strategy_config}")
            
            # Note: Trading logger and prediction engine updates are handled elsewhere
            # Strategy switch completed successfully
            
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
            
            # Find the most recent selection for this strategy
            if hasattr(self, 'pending_strategy_outcomes'):
                for record in reversed(self.pending_strategy_outcomes):
                    if record["strategy"] == strategy:
                        logger.debug(f"Strategy outcome recorded: {strategy}")
                        
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
            return {"message": "ML performance tracking not implemented yet"}
        except Exception as e:
            logger.error(f"❌ Failed to get ML strategy performance: {e}")
            return {"error": str(e)}
    
    def _find_next_best_strategy(self, market_data: Dict[str, Any], rejected_strategy: str) -> str:
        """Find the next best strategy when the primary choice is incompatible"""
        try:
            # Strategy priority list (excluding the rejected strategy)
            strategy_priorities = [
                "spike_hunting", "scalping", "high_volatility", "trend_following", 
                "breakout", "range_trading", "low_volatility_range", "standard"
            ]
            
            # Remove rejected strategy from priorities
            if rejected_strategy in strategy_priorities:
                strategy_priorities.remove(rejected_strategy)
            
            # Test each strategy in priority order
            for strategy in strategy_priorities:
                if not self._are_strategies_incompatible(strategy, market_data):
                    logger.info(f"✅ Found compatible alternative: {strategy}")
                    return strategy
            
            # If no strategy is compatible, return standard (last resort)
            logger.warning("⚠️ No compatible strategy found, using standard as last resort")
            return "standard"
            
        except Exception as e:
            logger.error(f"❌ Error finding next best strategy: {e}")
            return "standard"
    
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
                    dashboard_service.update_session_data(session_manager.current_session_data)
                    logger.info(f"🔄 Strategy switched to: {new_strategy}")
                
                logger.info(f"📊 Dashboard notified of strategy change: {new_strategy}")
            
        except Exception as e:
            logger.error(f"❌ Failed to notify session of strategy change: {e}")
    
