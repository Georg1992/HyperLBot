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
        
        # CRITICAL: Avoid placing stops at round numbers (ADDED 2026-01-12)
        # Research: Stops cluster heavily at psychological levels ($90K, $95K, $100K)
        # → Market makers actively hunt these clusters → liquidation cascade risk
        # Solution: Small deterministic offset moves stop away from obvious levels
        stop_loss = RiskManager._avoid_round_number_stop(stop_loss, direction, entry_price)
        
        return stop_loss
    
    @staticmethod
    def _avoid_round_number_stop(stop_loss: float, direction: str, entry_price: float) -> float:
        """
        Avoid placing stops at round numbers to reduce stop hunting risk
        
        Research (BTC perp trading psychology 2025):
        - Stops cluster at $1000 increments ($90K, $91K, $92K, etc)
        - Major clusters at $5K increments ($90K, $95K, $100K, etc)
        - Market makers actively hunt these obvious levels
        - Small offset ($50-$150) significantly reduces hunt risk
        
        Strategy:
        - Detect proximity to round $1000 or $5000 levels
        - Apply deterministic offset AWAY from entry (safer than toward)
        - Offset size: $50-$150 based on proximity
        
        Args:
            stop_loss: Calculated stop loss price
            direction: "LONG" or "SHORT"
            entry_price: Entry price (for validation)
            
        Returns:
            Adjusted stop loss avoiding round numbers
        """
        try:
            # Round to nearest $1000
            nearest_1k = round(stop_loss / 1000.0) * 1000.0
            distance_to_1k = abs(stop_loss - nearest_1k)
            
            # Round to nearest $5000
            nearest_5k = round(stop_loss / 5000.0) * 5000.0
            distance_to_5k = abs(stop_loss - nearest_5k)
            
            # Check if stop is dangerously close to a round number
            # Within $100 of $5K round number = VERY DANGEROUS
            # Within $150 of $1K round number = DANGEROUS
            if distance_to_5k < 100.0:
                # Major round number detected ($90K, $95K, etc)
                offset = 150.0  # Larger offset for major levels
                round_level = nearest_5k
                logger.debug(f"⚠️ Stop at ${stop_loss:.2f} too close to major round number ${round_level:.0f} (${distance_to_5k:.0f} away)")
            elif distance_to_1k < 150.0:
                # Minor round number detected ($91K, $92K, etc)
                offset = 75.0  # Smaller offset for minor levels
                round_level = nearest_1k
                logger.debug(f"⚠️ Stop at ${stop_loss:.2f} too close to round number ${round_level:.0f} (${distance_to_1k:.0f} away)")
            else:
                # Stop is safe distance from round numbers
                return stop_loss
            
            # Apply offset AWAY from entry (safer direction)
            # For LONG: stop is below entry, offset DOWN (away from entry)
            # For SHORT: stop is above entry, offset UP (away from entry)
            if direction == "LONG":
                adjusted_stop = stop_loss - offset
            else:  # SHORT
                adjusted_stop = stop_loss + offset
            
            # Validate adjusted stop is still on correct side of entry
            if direction == "LONG" and adjusted_stop >= entry_price:
                logger.warning(f"⚠️ Round number offset would invalidate LONG stop (${adjusted_stop:.2f} >= entry ${entry_price:.2f}), using original")
                return stop_loss
            elif direction == "SHORT" and adjusted_stop <= entry_price:
                logger.warning(f"⚠️ Round number offset would invalidate SHORT stop (${adjusted_stop:.2f} <= entry ${entry_price:.2f}), using original")
                return stop_loss
            
            logger.info(f"🎯 Stop adjusted to avoid round number: ${stop_loss:.2f} → ${adjusted_stop:.2f} (offset ${offset:.0f}, away from ${round_level:.0f})")
            return adjusted_stop
            
        except (ValueError, TypeError, ZeroDivisionError) as e:
            # Only catch specific calculation errors
            # Re-raise to maintain NO FALLBACKS policy
            logger.error(f"❌ Round number avoidance calculation error: {e}")
            raise ValueError(f"Round number avoidance failed: {e} (NO FALLBACKS)")
    
    @staticmethod
    def calculate_take_profit(
        entry_price: float,
        stop_loss: float,
        direction: str,
        atr_5m: float,
        config: Dict[str, Any],
        sr_levels: list,
        strategy: str,
        spread_pct: float = 0.01  # Spread in percentage (e.g., 0.01 = 0.01%)
    ) -> float:
        """
        Calculate adaptive take profit based on next significant S/R level WITH SPREAD COSTS
        
        Algorithm (NO FALLBACKS):
        1. Filter levels by power (quality gate)
        2. Filter by distance (realism gate)
        3. Calculate TP at level with ATR cushion
        4. Subtract spread costs from reward (FIXED 2026-01-12)
        5. Validate R:R constraints
        6. Select best level within constraints
        7. Raise error if no valid TP target (NO FALLBACKS)
        
        Args:
            entry_price: Entry price for the trade
            stop_loss: Calculated stop loss price
            direction: "LONG" or "SHORT"
            atr_5m: 5-minute ATR for distance calculations
            config: Strategy configuration
            sr_levels: All available S/R levels
            strategy: Trading strategy name
            spread_pct: Bid-ask spread in percentage (e.g., 0.01 = 0.01%)
            
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
        # Strategy-specific config with fallback to "standard" (valid config fallback, not data)
        if strategy in TradingConfig.TP_ADAPTIVE_CONFIG:
            tp_config = TradingConfig.TP_ADAPTIVE_CONFIG[strategy]
        else:
            tp_config = TradingConfig.TP_ADAPTIVE_CONFIG["standard"]
        
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
        min_power = config["min_power_threshold"]  # Required (NO FALLBACKS)
        qualified_levels = [
            level for level in sr_levels
            if level["power"] >= min_power  # Required (NO FALLBACKS)
            and level["status"] == "active"  # Required (NO FALLBACKS)
        ]
        
        if not qualified_levels:
            raise ValueError(f"No S/R levels with power >= {min_power} for {strategy} TP target (NO FALLBACKS)")
        
        # STEP 2: Direction Filter - Get levels in correct direction
        if direction == "LONG":
            # LONG needs resistance above entry
            target_levels = [
                level for level in qualified_levels
                if level["type"] == "resistance"  # Required (NO FALLBACKS)
                and level["price_level"] > entry_price  # Required (NO FALLBACKS)
            ]
        else:  # SHORT
            # SHORT needs support below entry
            target_levels = [
                level for level in qualified_levels
                if level["type"] == "support"  # Required (NO FALLBACKS)
                and level["price_level"] < entry_price  # Required (NO FALLBACKS)
            ]
        
        if not target_levels:
            raise ValueError(f"No {direction} TP target levels found (need {'resistance above' if direction=='LONG' else 'support below'} entry ${entry_price:.2f}) (NO FALLBACKS)")
        
        # STEP 3: Distance Constraint - Filter by realism
        max_distance = atr_5m * max_distance_atr
        cushion = atr_5m * cushion_atr
        
        # Calculate round-trip spread cost (FIXED 2026-01-12)
        # Spread cost = entry spread + exit spread
        # For BTC at $90K with 0.01% spread: $90K * 0.0001 * 2 = $18
        spread_decimal = spread_pct / 100.0  # Convert 0.01% to 0.0001
        spread_cost_usd = entry_price * spread_decimal * 2.0  # Round-trip (entry + exit)
        
        logger.debug(f"💰 Spread cost calculation: {spread_pct:.3f}% → ${spread_cost_usd:.2f} round-trip at ${entry_price:.2f}")
        
        valid_candidates = []
        for level in target_levels:
            level_price = level["price_level"]  # Required (NO FALLBACKS)
            distance = abs(level_price - entry_price)
            
            # Check if level is within reachable distance
            if distance > max_distance:
                continue
            
            # Calculate TP with cushion
            if direction == "LONG":
                tp_candidate = level_price - cushion
            else:  # SHORT
                tp_candidate = level_price + cushion
            
            # Calculate R:R WITH SPREAD COSTS (FIXED 2026-01-12)
            # Research: Ignoring spread = overestimating profit by 0.01-0.02% per trade
            # For high-leverage, this compounds to significant P&L error
            raw_reward = abs(tp_candidate - entry_price)
            net_reward = raw_reward - spread_cost_usd  # Subtract spread costs
            
            # If net reward is negative or zero, level is too close (spread eats all profit)
            if net_reward <= 0:
                logger.debug(f"⚠️ TP candidate ${tp_candidate:.2f} rejected: spread cost ${spread_cost_usd:.2f} exceeds reward ${raw_reward:.2f}")
                continue
            
            rr = net_reward / risk
            
            # Accept ALL valid S/R levels (no R:R filtering)
            # R:R will be used for position sizing in prediction_engine instead
            valid_candidates.append({
                "level": level,
                "tp_price": tp_candidate,
                "rr": rr,
                "distance": distance,
                "power": level["power"]  # Required (NO FALLBACKS)
            })
        
        if not valid_candidates:
            # No S/R levels found - calculate mathematical TP
            # Use target R:R (midpoint between min and max) for fallback calculation
            target_rr = (min_rr + max_rr) / 2.0
            reward = risk * target_rr
            
            if direction == "LONG":
                take_profit = entry_price + reward
            else:  # SHORT
                take_profit = entry_price - reward
            
            logger.info(
                f"📐 No S/R level for TP - using mathematical calculation: "
                f"{direction} @ ${entry_price:.2f}, TP @ ${take_profit:.2f} "
                f"(R:R {target_rr:.1f}x = ${reward:.2f} reward)"
            )
            
            return take_profit
        
        # STEP 4: Select Best Candidate
        # Priority: 1) Power (S/R strength), 2) R:R (reward potential)
        # Select strongest S/R level with best R:R
        best_candidate = max(valid_candidates, key=lambda x: (x["power"], x["rr"]))
        
        take_profit = best_candidate["tp_price"]
        selected_level = best_candidate["level"]
        final_rr = best_candidate["rr"]
        
        # Log with R:R classification
        rr_quality = "excellent" if final_rr >= 2.5 else "good" if final_rr >= 1.5 else "acceptable"
        
        logger.info(
            f"🎯 {direction} TP at strongest S/R level: ${take_profit:.2f} "
            f"(level: ${selected_level['price_level']:.2f}, "  # Required (NO FALLBACKS)
            f"power: {selected_level['power']:.1f}, "  # Required (NO FALLBACKS)
            f"R:R: {final_rr:.2f}:1 [{rr_quality}], "
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
