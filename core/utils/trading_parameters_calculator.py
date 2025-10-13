#!/usr/bin/env python3
"""
Trading Parameters Calculator
Single source of truth for stop loss, take profit, and position sizing calculations
"""

from typing import Dict, Any, Tuple
from loguru import logger
from core.constants import MagicNumbers

class TradingParametersCalculator:
    """Centralized calculator for all trading parameters"""
    
    def __init__(self):
        self.magic_numbers = MagicNumbers()
    
    def calculate_stop_loss_take_profit(
        self, 
        entry_price: float, 
        direction: str, 
        strategy: str = "standard",
        risk_reward_ratio: float = None
    ) -> Tuple[float, float, float]:
        """
        Calculate stop loss and take profit for any direction and strategy
        
        Args:
            entry_price: Entry price
            direction: "LONG" or "SHORT"
            strategy: Strategy name
            risk_reward_ratio: Custom R/R ratio (optional)
            
        Returns:
            Tuple of (stop_loss, take_profit, actual_rr_ratio)
        """
        # Strategy-specific parameters - 40X LEVERAGE OPTIMIZED
        if strategy == "scalping":
            stop_percent = 0.001  # 0.1% stop
            rr = 2.0
        elif strategy == "trend_following":
            stop_percent = 0.002  # 0.2% stop
            rr = 2.5
        elif strategy == "range_trading":
            stop_percent = 0.0015  # 0.15% stop
            rr = 2.0
        elif strategy == "low_volatility_range":
            stop_percent = 0.001  # 0.1% stop
            rr = 2.0
        elif strategy == "high_volatility":
            stop_percent = 0.003  # 0.3% stop
            rr = 2.0
        elif strategy == "spike_hunting":
            stop_percent = 0.005  # 0.5% stop
            rr = 3.0
        elif strategy == "breakout":
            stop_percent = 0.002  # 0.2% stop
            rr = 2.0
        else:  # standard
            stop_percent = 0.002  # 0.2% stop
            rr = 2.0
        
        # Use custom R/R if provided
        if risk_reward_ratio is not None:
            rr = risk_reward_ratio
        
        # Calculate stop loss and take profit
        if direction.upper() == "LONG":
            stop_loss = entry_price * (1 - stop_percent)
            take_profit = entry_price * (1 + (stop_percent * rr))
        else:  # SHORT
            stop_loss = entry_price * (1 + stop_percent)
            take_profit = entry_price * (1 - (stop_percent * rr))
        
        return round(stop_loss, 2), round(take_profit, 2), rr
    
    def calculate_position_size(
        self,
        confidence: float,
        account_balance: float,
        strategy: str = "standard",
        current_price: float = None
    ) -> Dict[str, float]:
        """
        Calculate position size based on confidence and strategy
        
        Args:
            confidence: Trade confidence (0-1)
            account_balance: Available balance
            strategy: Strategy name
            current_price: Current price (for BTC calculation)
            
        Returns:
            Dict with position size in BTC and USD
        """
        # Strategy-specific base position sizes (% of account)
        base_percentages = {
            "scalping": 0.20,      # 20%
            "trend_following": 0.15, # 15%
            "range_trading": 0.12,   # 12%
            "low_volatility_range": 0.10, # 10%
            "high_volatility": 0.10, # 10%
            "spike_hunting": 0.15,   # 15%
            "breakout": 0.08,        # 8%
            "standard": 0.10         # 10%
        }
        
        base_percent = base_percentages.get(strategy, 0.10)
        
        # Scale by confidence
        confidence_multiplier = max(0.3, min(1.0, confidence))  # 30%-100% of base
        
        # Calculate final position size
        position_usd = account_balance * base_percent * confidence_multiplier
        
        # Convert to BTC if price provided
        position_btc = position_usd / current_price if current_price else 0.0
        
        return {
            "position_usd": round(position_usd, 2),
            "position_btc": round(position_btc, 6),
            "base_percentage": base_percent,
            "confidence_multiplier": confidence_multiplier
        }
    
    def calculate_pnl(
        self,
        entry_price: float,
        exit_price: float,
        position_size_btc: float,
        direction: str,
        leverage: float = 40.0
    ) -> Dict[str, float]:
        """
        Calculate P&L for a trade
        
        Args:
            entry_price: Entry price
            exit_price: Exit price
            position_size_btc: Position size in BTC
            direction: "LONG" or "SHORT"
            leverage: Leverage used
            
        Returns:
            Dict with P&L calculations
        """
        # Calculate price change
        if direction.upper() == "LONG":
            price_change = exit_price - entry_price
        else:  # SHORT
            price_change = entry_price - exit_price
        
        # Calculate P&L
        raw_pnl = price_change * position_size_btc * leverage
        pnl_percentage = (price_change / entry_price) * 100 * leverage
        
        return {
            "raw_pnl": round(raw_pnl, 2),
            "pnl_percentage": round(pnl_percentage, 2),
            "price_change": round(price_change, 2),
            "is_profitable": raw_pnl > 0
        }

# Global instance
_global_trading_calculator = None

def get_global_trading_calculator() -> TradingParametersCalculator:
    """Get the global trading parameters calculator instance"""
    global _global_trading_calculator
    if _global_trading_calculator is None:
        _global_trading_calculator = TradingParametersCalculator()
    return _global_trading_calculator
