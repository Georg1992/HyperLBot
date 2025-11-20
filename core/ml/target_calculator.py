#!/usr/bin/env python3
"""
Target Calculator - SRP Compliant
Single Responsibility: Calculate stop loss, take profit, and risk/reward ratios
"""

from typing import Dict, Any, Tuple
from loguru import logger


class TargetCalculator:
    """
    Single Responsibility: Calculate stop loss, take profit, and risk/reward ratios
    
    Features:
    - Strategy-specific risk parameters
    - Score-based adjustments
    - Leverage-aware calculations
    - Support/Resistance alignment (future enhancement)
    """
    
    def __init__(self):
        logger.info("🎯 Target Calculator initialized")
    
    def calculate_targets(self, entry_price: float, direction: str, score: float,
                          strategy: str, market_data: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        Calculate stop loss, take profit, and risk/reward ratio
        
        Args:
            entry_price: Entry price for the trade
            direction: Trade direction ("LONG" or "SHORT")
            score: Prediction score (-1.0 to +1.0)
            strategy: Trading strategy name
            market_data: Market data dictionary
            
        Returns:
            tuple: (stop_loss, take_profit, risk_reward_ratio)
        """
        # Strategy-specific risk parameters - OPTIMIZED FOR 40X LEVERAGE
        risk_params = self._get_strategy_risk_params(strategy)
        stop_loss_pct = risk_params["stop_loss_pct"]
        base_risk_reward = risk_params["risk_reward"]
        
        # Adjust based on score strength
        score_strength = abs(score)
        if score_strength > 0.7:
            base_risk_reward *= 1.2  # Wider targets for strong signals
            logger.debug(f"📊 Score strength {score_strength:.2f} > 0.7, increasing R:R to {base_risk_reward:.1f}")
        
        # Future enhancement: Consider S/R levels in target calculation
        # support_levels = market_data.get("sr", {}).get("support_levels", [])
        # resistance_levels = market_data.get("sr", {}).get("resistance_levels", [])
        
        # Calculate stop loss and take profit
        if direction == "LONG":
            stop_loss = entry_price * (1 - stop_loss_pct)
            take_profit = entry_price * (1 + (stop_loss_pct * base_risk_reward))
        else:  # SHORT
            stop_loss = entry_price * (1 + stop_loss_pct)
            take_profit = entry_price * (1 - (stop_loss_pct * base_risk_reward))
        
        # Round to 2 decimal places
        stop_loss = round(stop_loss, 2)
        take_profit = round(take_profit, 2)
        
        logger.debug(f"🎯 Targets: Stop=${stop_loss:,.2f} Take=${take_profit:,.2f} R:R={base_risk_reward:.1f}")
        
        return stop_loss, take_profit, base_risk_reward
    
    def _get_strategy_risk_params(self, strategy: str) -> Dict[str, float]:
        """
        Get strategy-specific risk parameters
        
        Returns:
            dict with stop_loss_pct and risk_reward
        """
        # Strategy-specific risk parameters - 40X LEVERAGE OPTIMIZED
        strategy_params = {
            "scalping": {
                "stop_loss_pct": 0.001,  # 0.1% (tight for 40x leverage)
                "risk_reward": 2.0
            },
            "spike_hunting": {
                "stop_loss_pct": 0.005,  # 0.5% (reduced from 2% for 40x leverage)
                "risk_reward": 3.0
            },
            "trend_following": {
                "stop_loss_pct": 0.002,  # 0.2% (tight for 40x leverage)
                "risk_reward": 2.5
            },
            "high_volatility": {
                "stop_loss_pct": 0.003,  # 0.3% (reduced from 1.5% for 40x leverage)
                "risk_reward": 2.0
            },
            "range_trading": {
                "stop_loss_pct": 0.0015,  # 0.15% (tight for range trading with 40x leverage)
                "risk_reward": 2.0
            },
            "low_volatility_range": {
                "stop_loss_pct": 0.001,  # 0.1% (very tight for low volatility with 40x leverage)
                "risk_reward": 2.0
            },
            "breakout": {
                "stop_loss_pct": 0.002,  # 0.2% (tight for breakouts with 40x leverage)
                "risk_reward": 2.5
            },
            "standard": {
                "stop_loss_pct": 0.002,  # 0.2% (reduced from 1% for 40x leverage)
                "risk_reward": 2.0
            }
        }
        
        # Default to standard if strategy not found
        return strategy_params.get(strategy, strategy_params["standard"])


# Factory function for dependency injection
def create_target_calculator() -> TargetCalculator:
    """
    Factory function to create TargetCalculator with dependency injection
    
    Returns:
        Configured TargetCalculator instance
    """
    return TargetCalculator()

# Global instance for backward compatibility (DEPRECATED - use create_target_calculator)
_global_target_calculator = None

def get_global_target_calculator() -> TargetCalculator:
    """Get global target calculator singleton (DEPRECATED - use create_target_calculator)"""
    global _global_target_calculator
    if _global_target_calculator is None:
        _global_target_calculator = TargetCalculator()
    return _global_target_calculator
