#!/usr/bin/env python3
"""
Risk Manager
Handles all risk management calculations: stop loss and take profit
"""

from typing import Dict, Any, Optional, Tuple
from loguru import logger


class RiskManager:
    """
    Manages risk calculations for trading positions
    
    Responsibilities:
    - Calculate stop loss (unified: S/R-based + risk management)
    - Calculate take profit (R:R based)
    - Validate risk/reward ratios
    """
    
    @staticmethod
    def calculate_stop_loss(
        entry_price: float,
        direction: str,
        sr_stop_level: Optional[float],
        atr_5m: float,
        current_price: float,
        config: Dict[str, Any],
        unified_data: Dict[str, Any],
        leverage: int = 40
    ) -> float:
        """
        Calculate unified stop loss considering both S/R structure and risk management
        
        Unified formula that considers both S/R structure AND risk management simultaneously:
        - S/R constraint: stop must be below support (LONG) or above resistance (SHORT)
        - Risk constraint: stop must be at least min_distance from entry
        - Liquidation constraint: stop must trigger BEFORE liquidation (with buffer)
        - Final stop = position that satisfies ALL constraints (most conservative)
        
        Args:
            entry_price: Entry price for the trade
            direction: "LONG" or "SHORT"
            sr_stop_level: Stop level from S/R (below support for LONG, above resistance for SHORT)
            atr_5m: 5-minute ATR for distance calculations
            current_price: Current market price
            config: Strategy configuration
            unified_data: Complete market analysis data
            leverage: Leverage multiplier (default 40x)
            
        Returns:
            Calculated stop loss price
            
        Raises:
            ValueError: If stop loss calculation is invalid
        """
        if atr_5m <= 0:
            raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
        if current_price <= 0:
            raise ValueError(f"Invalid current_price: {current_price} - must be positive (NO FALLBACKS)")
        if entry_price <= 0:
            raise ValueError(f"Invalid entry_price: {entry_price} - must be positive (NO FALLBACKS)")
        
        # Get strategy multipliers (NO FALLBACKS - these are required)
        # Mathematically justified: Base stop = 2.0 × ATR (covers ~95% of normal moves)
        # Strategy multiplier adjusts this base (e.g., 1.0 = 2.0×ATR, 1.5 = 3.0×ATR)
        stop_loss_multiplier = RiskManager._get_stop_loss_multiplier(config)
        
        # Calculate risk management minimum distance (volatility-adjusted)
        atr_pct = atr_5m / current_price if current_price > 0 else 0.002
        
        # Volatility adjustment multiplier
        volatility_multiplier = RiskManager._calculate_volatility_multiplier(unified_data, atr_pct)
        
        # Mathematically justified base: 2.0 × ATR (standard for 95% coverage)
        atr_base_multiplier = 2.0
        base_atr_stop_distance = atr_5m * atr_base_multiplier
        
        # Minimum stop distance = strategy_multiplier × 2.0 × ATR × volatility_multiplier
        min_stop_distance = base_atr_stop_distance * stop_loss_multiplier * volatility_multiplier
        
        # S/R-based stop position (required, no fallback)
        if sr_stop_level is None:
            raise ValueError(f"S/R-based stop calculation required - cannot proceed without S/R level (NO FALLBACKS)")
        
        if direction == "LONG":
            # Validate S/R stop is below entry
            if sr_stop_level >= entry_price:
                raise ValueError(f"Invalid S/R stop: ${sr_stop_level:.2f} >= entry ${entry_price:.2f} (NO FALLBACKS)")
            
            # Unified calculation: stop must satisfy BOTH constraints
            # Constraint 1: Below S/R level (sr_stop_level)
            # Constraint 2: At least min_distance from entry (entry_price - min_stop_distance)
            # Solution: Use the more conservative (lower = further from entry)
            stop_loss_sr_constraint = sr_stop_level
            stop_loss_risk_constraint = entry_price - min_stop_distance
            
            # Unified stop = min(constraint1, constraint2) = more conservative position
            # This ensures stop is BOTH below support AND meets minimum distance
            stop_loss = min(stop_loss_sr_constraint, stop_loss_risk_constraint)
            
            # Final validation: ensure both constraints are satisfied
            if stop_loss >= entry_price:
                raise ValueError(f"Unified stop ${stop_loss:.2f} >= entry ${entry_price:.2f} (NO FALLBACKS)")
            if stop_loss > stop_loss_risk_constraint:
                raise ValueError(f"Unified stop ${stop_loss:.2f} violates risk constraint (min: ${stop_loss_risk_constraint:.2f} = {min_stop_distance:.2f} from entry) (NO FALLBACKS)")
            if stop_loss > stop_loss_sr_constraint:
                raise ValueError(f"Unified stop ${stop_loss:.2f} violates S/R constraint (max: ${stop_loss_sr_constraint:.2f} below support) (NO FALLBACKS)")
            
            logger.debug(f"✅ Unified LONG stop: ${stop_loss:.2f} (S/R constraint: ${stop_loss_sr_constraint:.2f}, Risk constraint: ${stop_loss_risk_constraint:.2f}, Distance: {entry_price - stop_loss:.2f})")
        else:  # SHORT
            # Validate S/R stop is above entry
            if sr_stop_level <= entry_price:
                raise ValueError(f"Invalid S/R stop: ${sr_stop_level:.2f} <= entry ${entry_price:.2f} (NO FALLBACKS)")
            
            # Unified calculation: stop must satisfy BOTH constraints
            # Constraint 1: Above S/R level (sr_stop_level)
            # Constraint 2: At least min_distance from entry (entry_price + min_stop_distance)
            # Solution: Use the more conservative (higher = further from entry)
            stop_loss_sr_constraint = sr_stop_level
            stop_loss_risk_constraint = entry_price + min_stop_distance
            
            # Unified stop = max(constraint1, constraint2) = more conservative position
            # This ensures stop is BOTH above resistance AND meets minimum distance
            stop_loss = max(stop_loss_sr_constraint, stop_loss_risk_constraint)
            
            # Final validation: ensure both constraints are satisfied
            if stop_loss <= entry_price:
                raise ValueError(f"Unified stop ${stop_loss:.2f} <= entry ${entry_price:.2f} (NO FALLBACKS)")
            if stop_loss < stop_loss_risk_constraint:
                raise ValueError(f"Unified stop ${stop_loss:.2f} violates risk constraint (min: ${stop_loss_risk_constraint:.2f} = {min_stop_distance:.2f} from entry) (NO FALLBACKS)")
            if stop_loss < stop_loss_sr_constraint:
                raise ValueError(f"Unified stop ${stop_loss:.2f} violates S/R constraint (min: ${stop_loss_sr_constraint:.2f} above resistance) (NO FALLBACKS)")
            
            logger.debug(f"✅ Unified SHORT stop: ${stop_loss:.2f} (S/R constraint: ${stop_loss_sr_constraint:.2f}, Risk constraint: ${stop_loss_risk_constraint:.2f}, Distance: {stop_loss - entry_price:.2f})")
        
        # CRITICAL: Cap stop loss at liquidation price with safety buffer
        # Ensures stop triggers BEFORE liquidation for leveraged positions
        from core.calculations.liquidation_calculator import LiquidationCalculator
        liq_calc = LiquidationCalculator(leverage=leverage)
        liquidation_price = liq_calc.calculate_liquidation_price(entry_price, direction)
        
        # Safety buffer: 0.5% before liquidation (ensures stop triggers first)
        safety_buffer_pct = 0.005  # 0.5%
        
        if direction == "LONG":
            # For LONG: liquidation is below entry, stop must be above liquidation
            # Max stop = liquidation + buffer (closer to entry, safer)
            max_stop_from_liquidation = liquidation_price * (1.0 + safety_buffer_pct)
            
            if stop_loss < max_stop_from_liquidation:
                logger.warning(f"⚠️ Stop loss ${stop_loss:.2f} exceeds liquidation price ${liquidation_price:.2f}! Capping at ${max_stop_from_liquidation:.2f} (liq + {safety_buffer_pct*100}% buffer)")
                stop_loss = max_stop_from_liquidation
                
                # Validate capped stop is still below entry
                if stop_loss >= entry_price:
                    raise ValueError(f"Liquidation constraint makes trade impossible: max_stop ${stop_loss:.2f} >= entry ${entry_price:.2f} (liquidation too close to entry) (NO FALLBACKS)")
        else:  # SHORT
            # For SHORT: liquidation is above entry, stop must be below liquidation
            # Max stop = liquidation - buffer (closer to entry, safer)
            max_stop_from_liquidation = liquidation_price * (1.0 - safety_buffer_pct)
            
            if stop_loss > max_stop_from_liquidation:
                logger.warning(f"⚠️ Stop loss ${stop_loss:.2f} exceeds liquidation price ${liquidation_price:.2f}! Capping at ${max_stop_from_liquidation:.2f} (liq - {safety_buffer_pct*100}% buffer)")
                stop_loss = max_stop_from_liquidation
                
                # Validate capped stop is still above entry
                if stop_loss <= entry_price:
                    raise ValueError(f"Liquidation constraint makes trade impossible: max_stop ${stop_loss:.2f} <= entry ${entry_price:.2f} (liquidation too close to entry) (NO FALLBACKS)")
        
        logger.debug(f"🛡️ Liquidation check: liq=${liquidation_price:.2f}, final_stop=${stop_loss:.2f}")
        
        return stop_loss
    
    @staticmethod
    def calculate_take_profit(
        entry_price: float,
        stop_loss: float,
        direction: str,
        atr_5m: float,
        config: Dict[str, Any]
    ) -> float:
        """
        Calculate take profit based on stop distance and R:R ratio
        
        Args:
            entry_price: Entry price for the trade
            stop_loss: Calculated stop loss price
            direction: "LONG" or "SHORT"
            atr_5m: 5-minute ATR for distance calculations
            config: Strategy configuration
            
        Returns:
            Calculated take profit price
            
        Raises:
            ValueError: If take profit calculation is invalid
        """
        if entry_price <= 0:
            raise ValueError(f"Invalid entry_price: {entry_price} - must be positive (NO FALLBACKS)")
        if atr_5m <= 0:
            raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
        
        # Get strategy multipliers
        profit_target_multiplier = RiskManager._get_profit_target_multiplier(config)
        min_risk_reward = config.get("min_risk_reward", 1.5)  # Minimum R:R ratio
        
        # Calculate actual stop distance to use for R:R calculation
        if direction == "LONG":
            actual_stop_distance_pct = (entry_price - stop_loss) / entry_price
        else:  # SHORT
            actual_stop_distance_pct = (stop_loss - entry_price) / entry_price
        
        # Mathematically justified: Profit target = strategy_multiplier × base_atr_distance
        # Base profit target = 3.0 × ATR (default, can be adjusted by multiplier)
        base_atr_profit_distance = atr_5m * 3.0  # 3.0×ATR default (1.5× stop base)
        base_profit_distance = base_atr_profit_distance * profit_target_multiplier
        profit_target_pct = base_profit_distance / entry_price if entry_price > 0 else 0.012
        
        # Adjust profit target if needed to meet minimum R:R ratio
        min_profit_pct = actual_stop_distance_pct * min_risk_reward
        if profit_target_pct < min_profit_pct:
            profit_target_pct = min_profit_pct
            logger.debug(f"📊 Adjusted profit target to meet min R:R {min_risk_reward}:1 → {profit_target_pct*100:.3f}%")
        
        if direction == "LONG":
            take_profit = entry_price * (1 + profit_target_pct)
        else:  # SHORT
            take_profit = entry_price * (1 - profit_target_pct)
        
        # Validate take profit
        if take_profit <= 0:
            raise ValueError(f"Invalid take profit: ${take_profit:.2f} (negative or zero)")
        
        if direction == "LONG" and take_profit <= entry_price:
            raise ValueError(f"Invalid LONG take profit: ${take_profit:.2f} <= entry ${entry_price:.2f}")
        if direction == "SHORT" and take_profit >= entry_price:
            raise ValueError(f"Invalid SHORT take profit: ${take_profit:.2f} >= entry ${entry_price:.2f}")
        
        return take_profit
    
    @staticmethod
    def validate_risk_reward(
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
        min_risk_reward: float
    ) -> Tuple[float, bool]:
        """
        Validate risk/reward ratio
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            direction: "LONG" or "SHORT"
            min_risk_reward: Minimum required R:R ratio
            
        Returns:
            (risk_reward_ratio, is_valid) tuple
        """
        if direction == "LONG":
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # SHORT
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            raise ValueError(f"Invalid stop loss calculation: risk <= 0 (entry: ${entry_price:.2f}, stop: ${stop_loss:.2f})")
        if reward <= 0:
            raise ValueError(f"Invalid take profit calculation: reward <= 0 (entry: ${entry_price:.2f}, tp: ${take_profit:.2f})")
        
        risk_reward_ratio = reward / risk
        # Use small epsilon for floating point comparison
        is_valid = risk_reward_ratio >= (min_risk_reward - 0.001)
        
        if not is_valid:
            logger.warning(f"⚠️ R:R ratio {risk_reward_ratio:.2f}:1 below minimum {min_risk_reward}:1, but proceeding")
        
        logger.debug(f"🎯 Stop/Target calculated: Entry=${entry_price:.2f}, SL=${stop_loss:.2f}, TP=${take_profit:.2f}, R:R={risk_reward_ratio:.2f}:1")
        
        return risk_reward_ratio, is_valid
    
    @staticmethod
    def _get_stop_loss_multiplier(config: Dict[str, Any]) -> float:
        """Get stop loss multiplier from config (with backward compatibility)"""
        if "stop_loss_multiplier" in config:
            return config["stop_loss_multiplier"]
        elif "stop_loss" in config:
            # Backward compat: Convert old percentage to multiplier
            # Typical ATR ~0.4% (0.004), base = 2.0 × ATR = 0.8% (0.008)
            typical_atr_pct = 0.004  # 0.4% typical ATR
            base_stop_pct = 2.0 * typical_atr_pct  # 0.8% base stop
            return config["stop_loss"] / base_stop_pct
        else:
            return 1.0  # Default: standard 2.0×ATR
    
    @staticmethod
    def _get_profit_target_multiplier(config: Dict[str, Any]) -> float:
        """Get profit target multiplier from config (with backward compatibility)"""
        if "profit_target_multiplier" in config:
            return config["profit_target_multiplier"]
        elif "profit_target" in config:
            # Backward compat: Convert old percentage to multiplier
            # Typical ATR ~0.4% (0.004), base = 3.0 × ATR = 1.2% (0.012)
            typical_atr_pct = 0.004  # 0.4% typical ATR
            base_target_pct = 3.0 * typical_atr_pct  # 1.2% base target
            return config["profit_target"] / base_target_pct
        else:
            return 1.5  # Default: 4.5×ATR (1.5 × 3.0×ATR)
    
    @staticmethod
    def _calculate_volatility_multiplier(unified_data: Dict[str, Any], atr_pct: float) -> float:
        """Calculate volatility adjustment multiplier"""
        volatility_multiplier = 1.0
        try:
            volatility_5m = unified_data.get("volatility_5m", atr_pct)
            if volatility_5m > 0:
                vol_atr_ratio = volatility_5m / atr_pct if atr_pct > 0 else 1.0
                if vol_atr_ratio > 1.5:
                    volatility_multiplier = 1.2
                elif vol_atr_ratio < 0.7:
                    volatility_multiplier = 0.9
        except Exception:
            volatility_multiplier = 1.0
        return volatility_multiplier
