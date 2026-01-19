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
        leverage: int = None
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
            leverage: Leverage multiplier (uses TradingConfig.LEVERAGE if not provided)
            
        Returns:
            Calculated stop loss price
            
        Raises:
            ValueError: If stop loss calculation is invalid
        """
        # Use config leverage if not provided
        if leverage is None:
            from config.config import TradingConfig
            leverage = TradingConfig.LEVERAGE
        
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
        
        # Calculate risk management minimum distance
        # Mathematically justified base: 2.0 × ATR (standard for 95% coverage)
        atr_base_multiplier = 2.0
        base_atr_stop_distance = atr_5m * atr_base_multiplier
        
        # Minimum stop distance = strategy_multiplier × 2.0 × ATR
        # ATR already incorporates volatility; strategy multiplier provides additional adjustment
        min_stop_distance = base_atr_stop_distance * stop_loss_multiplier
        
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
        config: Dict[str, Any],
        sr_levels: list,
        strategy: str
    ) -> float:
        """
        Calculate adaptive take profit based on next significant S/R level
        
        Algorithm (NO FALLBACKS):
        1. Filter levels by power (quality gate)
        2. Filter by distance (realism gate)
        3. Calculate TP at level with ATR cushion
        4. Validate R:R constraints
        5. Select best level within constraints
        6. Raise error if no valid TP target (NO FALLBACKS)
        
        Args:
            entry_price: Entry price for the trade
            stop_loss: Calculated stop loss price
            direction: "LONG" or "SHORT"
            atr_5m: 5-minute ATR for distance calculations
            config: Strategy configuration
            sr_levels: All available S/R levels
            strategy: Trading strategy name
            
        Returns:
            Calculated take profit price at next significant S/R level
            
        Raises:
            ValueError: If no valid TP target found (NO FALLBACKS)
        """
        if entry_price <= 0:
            raise ValueError(f"Invalid entry_price: {entry_price} - must be positive (NO FALLBACKS)")
        if atr_5m <= 0:
            raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
        if not sr_levels:
            raise ValueError("No S/R levels provided for TP calculation (NO FALLBACKS)")
        
        # Get adaptive TP configuration
        from config.config import TradingConfig
        tp_config = TradingConfig.TP_ADAPTIVE_CONFIG.get(strategy, TradingConfig.TP_ADAPTIVE_CONFIG["standard"])
        
        min_rr = tp_config["min_rr"]
        max_rr = tp_config["max_rr"]
        cushion_atr = tp_config["cushion_atr"]
        max_distance_atr = tp_config["max_distance_atr"]
        
        # Calculate risk for R:R validation
        if direction == "LONG":
            risk = entry_price - stop_loss
        else:  # SHORT
            risk = stop_loss - entry_price
        
        if risk <= 0:
            raise ValueError(f"Invalid risk: ${risk:.2f} (stop_loss must be on correct side of entry)")
        
        # STEP 1: Quality Gate - Filter by power threshold
        min_power = config.get("min_power_threshold", 30.0)
        qualified_levels = [
            level for level in sr_levels
            if level.get("power", 0) >= min_power
            and level.get("status") == "active"
        ]
        
        if not qualified_levels:
            raise ValueError(f"No S/R levels with power >= {min_power} for {strategy} TP target (NO FALLBACKS)")
        
        # STEP 2: Direction Filter - Get levels in correct direction
        if direction == "LONG":
            # LONG needs resistance above entry
            target_levels = [
                level for level in qualified_levels
                if level.get("type") == "resistance"
                and level.get("price_level", 0) > entry_price
            ]
        else:  # SHORT
            # SHORT needs support below entry
            target_levels = [
                level for level in qualified_levels
                if level.get("type") == "support"
                and level.get("price_level", 0) < entry_price
            ]
        
        if not target_levels:
            raise ValueError(f"No {direction} TP target levels found (need {'resistance above' if direction=='LONG' else 'support below'} entry ${entry_price:.2f}) (NO FALLBACKS)")
        
        # STEP 3: Distance Constraint - Filter by realism
        max_distance = atr_5m * max_distance_atr
        cushion = atr_5m * cushion_atr
        
        valid_candidates = []
        for level in target_levels:
            level_price = level.get("price_level", 0)
            distance = abs(level_price - entry_price)
            
            # Check if level is within reachable distance
            if distance > max_distance:
                continue
            
            # Calculate TP with cushion
            if direction == "LONG":
                tp_candidate = level_price - cushion
            else:  # SHORT
                tp_candidate = level_price + cushion
            
            # Calculate R:R
            reward = abs(tp_candidate - entry_price)
            rr = reward / risk
            
            # Validate R:R constraints
            if min_rr <= rr <= max_rr:
                valid_candidates.append({
                    "level": level,
                    "tp_price": tp_candidate,
                    "rr": rr,
                    "distance": distance,
                    "power": level.get("power", 0)
                })
        
        if not valid_candidates:
            # Detailed error for debugging
            too_close = sum(1 for l in target_levels if abs(l["price_level"] - entry_price) / risk < min_rr)  # Required (NO FALLBACKS)
            too_far = sum(1 for l in target_levels if abs(l["price_level"] - entry_price) > max_distance)  # Required (NO FALLBACKS)
            rr_invalid = len(target_levels) - too_close - too_far
            
            raise ValueError(
                f"No valid {direction} TP target found for {strategy} (NO FALLBACKS). "
                f"Available levels: {len(target_levels)}, "
                f"too_close (R:R<{min_rr}): {too_close}, "
                f"too_far (>{max_distance_atr}×ATR): {too_far}, "
                f"R:R invalid: {rr_invalid}. "
                f"Entry: ${entry_price:.2f}, Risk: ${risk:.2f}, "
                f"Min R:R: {min_rr}, Max R:R: {max_rr}"
            )
        
        # STEP 4: Select Best Candidate - Highest R:R within constraints
        # (Higher R:R = better, as long as it's realistic)
        best_candidate = max(valid_candidates, key=lambda x: x["rr"])
        
        take_profit = best_candidate["tp_price"]
        selected_level = best_candidate["level"]
        final_rr = best_candidate["rr"]
        
        logger.info(
            f"🎯 {direction} TP at next S/R level: ${take_profit:.2f} "
            f"(level: ${selected_level['price_level']:.2f}, "  # Required (NO FALLBACKS)
            f"power: {selected_level['power']:.1f}, "  # Required (NO FALLBACKS)
            f"R:R: {final_rr:.2f}:1, "
            f"cushion: ${cushion:.2f})"
        )
        
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
    
    # REMOVED: _get_profit_target_multiplier() - Old fixed multiplier approach
    # Now using adaptive TP based on next S/R level
    
    # REMOVED: _calculate_volatility_multiplier() - Old fixed multiplier approach
    # Now using adaptive TP based on next S/R level with strategy-specific constraints
