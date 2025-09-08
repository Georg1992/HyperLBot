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
from core.constants import VariabilityConstants


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
        logger.info(f"   📊 Available strategies: {list(self.strategy_configs.keys())}")
        logger.info(f"   🎯 Current strategy: {self.current_strategy}")
    
    def detect_optimal_strategy(self, market_data: Dict[str, Any], historical_context: Dict[str, Any] = None) -> str:
        """
        Detect the optimal strategy based on current market conditions
        
        Args:
            market_data: Current market data (price, volatility, trend, volume, etc.)
            historical_context: Historical context from session manager
            
        Returns:
            str: Optimal strategy name
        """
        try:
            current_price = market_data.get("current_price", 0)
            volatility_5m = market_data.get("volatility_5m", 0.0)
            volatility_category = market_data.get("volatility_5m_category", "MODERATE")
            trend = market_data.get("trend_5m", {}).get("trend", "NEUTRAL")
            volume_category = market_data.get("hyperliquid_volume", {}).get("volume_category", "NORMAL")
            rsi = market_data.get("rsi_5m", 50.0)
            
            logger.info(f"🎯 STRATEGY DETECTION: Analyzing market conditions at ${current_price:.2f}")
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
                    logger.info(f"🔄 Strategy switch detected: {self.current_strategy} → {optimal_strategy}")
                    self._switch_strategy(optimal_strategy)
                else:
                    logger.info(f"⏳ Strategy switch blocked (cooldown): {self.current_strategy} → {optimal_strategy}")
            
            return self.current_strategy
            
        except Exception as e:
            logger.error(f"❌ Strategy detection failed: {e}")
            return self.current_strategy
    
    def get_current_strategy_config(self) -> Dict[str, Any]:
        """Get current strategy configuration"""
        return self.current_strategy_config.copy()
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for specific strategy"""
        return self.strategy_configs.get(strategy_name, self.strategy_configs["standard"]).copy()
    
    def update_strategy_performance(self, strategy_name: str, trade_result: Dict[str, Any]):
        """Update strategy performance tracking"""
        try:
            if strategy_name not in self.strategy_performance:
                return
            
            performance = self.strategy_performance[strategy_name]
            performance["total_trades"] += 1
            performance["last_used"] = time.time()
            
            if trade_result.get("success", False):
                performance["successful_trades"] += 1
                performance["total_profit"] += trade_result.get("profit", 0.0)
            
            # Update usage count
            self.strategy_usage_count[strategy_name] += 1
            
            logger.debug(f"📊 Strategy performance updated: {strategy_name} - {performance['successful_trades']}/{performance['total_trades']} successful")
            
        except Exception as e:
            logger.error(f"❌ Strategy performance update failed: {e}")
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all strategies"""
        summary = {}
        for strategy_name, performance in self.strategy_performance.items():
            if performance["total_trades"] > 0:
                success_rate = performance["successful_trades"] / performance["total_trades"]
                avg_profit = performance["total_profit"] / performance["total_trades"]
            else:
                success_rate = 0.0
                avg_profit = 0.0
            
            summary[strategy_name] = {
                "total_trades": performance["total_trades"],
                "success_rate": success_rate,
                "avg_profit": avg_profit,
                "total_profit": performance["total_profit"],
                "usage_count": self.strategy_usage_count[strategy_name],
                "last_used": performance["last_used"]
            }
        
        return summary
    
    def _analyze_market_conditions(self, volatility_5m: float, volatility_category: str, 
                                 trend: str, volume_category: str, rsi: float, 
                                 historical_context: Dict[str, Any] = None) -> str:
        """Analyze market conditions and determine optimal strategy"""
        
        # 1. VOLATILITY-BASED STRATEGY SELECTION
        if volatility_category == "VERY_LOW":
            # Very low volatility - use range trading strategy
            logger.info("🎯 Strategy: VERY_LOW volatility → low_volatility_range")
            return "low_volatility_range"
        
        elif volatility_category == "LOW":
            # Low volatility - use low volatility range strategy
            logger.info("🎯 Strategy: LOW volatility → low_volatility_range")
            return "low_volatility_range"
        
        elif volatility_category == "EXTREME":
            # Extreme volatility - use spike hunting strategy
            logger.info("🎯 Strategy: EXTREME volatility → spike_hunting")
            return "spike_hunting"
        
        elif volatility_category == "HIGH":
            # High volatility - use high volatility strategy
            logger.info("🎯 Strategy: HIGH volatility → high_volatility")
            return "high_volatility"
        
        # 2. TREND-BASED STRATEGY SELECTION (for MODERATE volatility)
        elif volatility_category == "MODERATE":
            if trend in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
                logger.info("🎯 Strategy: MODERATE volatility + STRONG trend → trend_following")
                return "trend_following"
            else:
                logger.info("🎯 Strategy: MODERATE volatility + NEUTRAL trend → standard")
                return "standard"
        
        # 3. VOLUME-BASED STRATEGY SELECTION (fallback)
        elif volume_category == "HIGH":
            logger.info("🎯 Strategy: HIGH volume → high_volatility")
            return "high_volatility"
        
        # 4. DEFAULT STRATEGY
        else:
            logger.info("🎯 Strategy: Default conditions → standard")
            return "standard"
    
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
            "trend_following": "Optimized for strong trending markets"
        }
        return descriptions.get(strategy_name, "Unknown strategy")
    
    def _notify_session_strategy_change(self, new_strategy: str):
        """Notify SessionManager of strategy change for dashboard update"""
        try:
            # Import here to avoid circular imports
            from core.session.session_manager import session_manager
            from core.dashboard.dashboard_data_manager import simple_rtm
            
            # Update session data with new strategy
            if hasattr(session_manager, 'current_session_data') and session_manager.current_session_data:
                session_manager.current_session_data["strategy"] = new_strategy
                
                # Sync updated session data to SimpleRTM for dashboard
                simple_rtm.sync_from_session_manager(session_manager.current_session_data)
                
                # Add activity log for strategy change
                simple_rtm.add_activity(f"🔄 Strategy switched to: {new_strategy}", "INFO", "strategy")
                
                logger.info(f"📊 Dashboard notified of strategy change: {new_strategy}")
            
        except Exception as e:
            logger.error(f"❌ Failed to notify session of strategy change: {e}")
    
