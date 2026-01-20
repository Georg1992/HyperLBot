#!/usr/bin/env python3
"""
Position Sizer - Unified position sizing logic for all execution engines

Single Responsibility: Calculate position sizes based on:
- Current balance
- Strategy configuration (base position_size %)
- Risk:Reward ratio (dynamic scaling)
- Leverage

Used by BOTH:
- PredictionEngine (limit orders at S/R levels)
- ReactiveEngine (market orders on momentum)
"""

from typing import Dict, Any
from loguru import logger
from config.config import TradingConfig


class PositionSizer:
    """
    Calculates position sizes for all execution engines
    
    Two sides of one coin:
    - Predictions: Strategic entries at S/R levels
    - Reactions: Opportunistic entries on momentum
    
    Both use identical position sizing logic for consistency
    """
    
    def __init__(self):
        logger.debug("💰 Position Sizer initialized")
    
    @staticmethod
    def calculate_rr_multiplier(rr_ratio: float) -> float:
        """
        Calculate position size multiplier based on Risk:Reward ratio
        
        Logic: Trade smaller on low R:R, bigger on high R:R
        - R:R < 0.8: Dangerous (0.5x)
        - R:R 0.8-1.2: Acceptable (0.5x-0.8x)
        - R:R 1.2-1.5: Good (0.8x-1.0x)
        - R:R 1.5-2.5: Excellent (1.0x)
        - R:R 2.5+: Outstanding (1.0x-1.5x)
        
        Args:
            rr_ratio: Achieved risk:reward ratio
            
        Returns:
            Multiplier to apply to base position_size (0.5 to 1.5)
        """
        rr_config = TradingConfig.RR_POSITION_MULTIPLIERS
        min_rr = rr_config["min_rr"]
        low_rr = rr_config["low_rr"]
        good_rr = rr_config["good_rr"]
        excellent_rr = rr_config["excellent_rr"]
        max_mult = rr_config["max_multiplier"]
        min_mult = rr_config["min_multiplier"]
        
        if rr_ratio < min_rr:
            # Dangerous R:R - minimum size
            return min_mult
        elif rr_ratio < low_rr:
            # Low R:R (0.8-1.2) - scale from 0.5x to 0.8x
            progress = (rr_ratio - min_rr) / (low_rr - min_rr)
            return min_mult + (0.8 - min_mult) * progress
        elif rr_ratio < good_rr:
            # Acceptable R:R (1.2-1.5) - scale from 0.8x to 1.0x
            progress = (rr_ratio - low_rr) / (good_rr - low_rr)
            return 0.8 + 0.2 * progress
        elif rr_ratio < excellent_rr:
            # Good R:R (1.5-2.5) - keep at 1.0x (base size)
            return 1.0
        else:
            # Excellent R:R (2.5+) - scale from 1.0x to 1.5x (capped)
            progress = min((rr_ratio - excellent_rr) / 2.5, 1.0)  # Cap at R:R 5.0
            return 1.0 + (max_mult - 1.0) * progress
    
    @staticmethod
    def calculate_position_size(
        balance: float,
        base_position_size_pct: float,
        risk_reward_ratio: float,
        leverage: int,
        entry_price: float
    ) -> Dict[str, Any]:
        """
        Calculate position size in BTC based on all parameters
        
        Formula:
        1. Get R:R multiplier (0.5x - 1.5x)
        2. Adjust position size: base_size × rr_multiplier
        3. Calculate position value: balance × adjusted_size × leverage
        4. Convert to BTC: position_value / entry_price
        
        Args:
            balance: Current account balance (USD)
            base_position_size_pct: Base position size from strategy config (0.0-1.0)
            risk_reward_ratio: Achieved R:R ratio
            leverage: Trading leverage (e.g., 40)
            entry_price: Entry price for the trade
            
        Returns:
            Dict with:
                - position_size_btc: Position size in BTC
                - position_value_usd: Position value in USD
                - base_position_size_pct: Base % from config
                - adjusted_position_size_pct: Adjusted % after R:R scaling
                - rr_multiplier: R:R multiplier applied
                - balance: Balance used in calculation
        """
        if balance <= 0:
            raise ValueError(f"Invalid balance: ${balance:.2f} (must be positive)")
        if base_position_size_pct <= 0 or base_position_size_pct > 1.0:
            raise ValueError(f"Invalid base_position_size_pct: {base_position_size_pct} (must be 0-1)")
        if leverage <= 0:
            raise ValueError(f"Invalid leverage: {leverage} (must be positive)")
        if entry_price <= 0:
            raise ValueError(f"Invalid entry_price: ${entry_price:.2f} (must be positive)")
        
        # Calculate R:R multiplier
        rr_multiplier = PositionSizer.calculate_rr_multiplier(risk_reward_ratio)
        
        # Adjust position size based on R:R
        adjusted_position_size_pct = base_position_size_pct * rr_multiplier
        
        # Calculate position value in USD (accounts for leverage)
        position_value_usd = balance * adjusted_position_size_pct * leverage
        
        # Convert to BTC
        position_size_btc = position_value_usd / entry_price
        
        logger.info(
            f"💰 Position sizing: Balance=${balance:.2f}, "
            f"Base={base_position_size_pct*100:.1f}%, R:R={risk_reward_ratio:.2f} → multiplier={rr_multiplier:.2f}x, "
            f"Adjusted={adjusted_position_size_pct*100:.1f}%, "
            f"Leverage={leverage}x → {position_size_btc:.4f} BTC (${position_value_usd:.2f})"
        )
        
        return {
            "position_size_btc": position_size_btc,
            "position_value_usd": position_value_usd,
            "base_position_size_pct": base_position_size_pct,
            "adjusted_position_size_pct": adjusted_position_size_pct,
            "rr_multiplier": rr_multiplier,
            "balance": balance,
            "leverage": leverage,
            "entry_price": entry_price,
            "risk_reward_ratio": risk_reward_ratio
        }
    
    @staticmethod
    def get_balance_from_simulator() -> float:
        """
        Get current balance from Hyperliquid simulator
        
        Returns:
            Current balance in USD
        """
        try:
            from core.services.system_initializer import get_system_initializer
            system_initializer = get_system_initializer()
            hyperliquid_simulator = system_initializer.singleton_systems["hyperliquid_simulator"] if "hyperliquid_simulator" in system_initializer.singleton_systems else None
            
            if hyperliquid_simulator and hasattr(hyperliquid_simulator, 'get_balance'):
                return hyperliquid_simulator.get_balance()
            else:
                logger.warning("⚠️ Could not access simulator balance - using default")
                return 10000.0  # Default for testing
        except Exception as e:
            logger.warning(f"⚠️ Error getting balance: {e} - using default")
            return 10000.0  # Default for testing
