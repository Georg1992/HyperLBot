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

from typing import Dict, Any, Optional
from loguru import logger
from config.config import TradingConfig


class PositionSizeCalculator:
    """
    Calculates position sizes for all execution engines
    
    Two sides of one coin:
    - Predictions: Strategic entries at S/R levels
    - Reactions: Opportunistic entries on momentum
    
    Both use identical position sizing logic for consistency
    """
    # NOTE: All methods are @staticmethod - no instance needed, no __init__ required
    
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
        entry_price: float,
        stop_loss: float = None,
        direction: str = "LONG",
        confidence: Optional[float] = None  # 0.0-100.0, will be used for confidence-based sizing when implemented
    ) -> Dict[str, Any]:
        """
        Calculate position size in BTC with LIQUIDATION RISK PROTECTION
        
        Formula (FIXED for high-leverage BTC perps):
        1. Get R:R multiplier (0.5x - 1.5x)
        2. Calculate liquidation safety factor
        3. Calculate confidence multiplier (when confidence is implemented)
        4. Adjust position size: base_size × rr_multiplier × liq_safety_factor × confidence_multiplier
        5. Calculate position value: balance × adjusted_size × leverage
        6. Convert to BTC: position_value / entry_price
        
        CRITICAL: Position sizing happens AFTER confidence calculation
        - Confidence will influence position size (high confidence → larger size, low confidence → smaller size)
        - For now, confidence is optional and not used (confidence_multiplier = 1.0)
        
        CRITICAL FIX: Position sizing now considers liquidation distance
        - Problem: High R:R → large position → liq closer to SL → wick hits liq before SL
        - Solution: Reduce size if SL is <40% of distance to liquidation
        
        Args:
            balance: Current account balance (USD)
            base_position_size_pct: Base position size from strategy config (0.0-1.0)
            risk_reward_ratio: Achieved R:R ratio
            leverage: Trading leverage (e.g., 40)
            entry_price: Entry price for the trade
            stop_loss: Stop loss price (REQUIRED for liquidation risk calc)
            direction: Trade direction ("LONG" or "SHORT")
            confidence: Optional confidence (0.0-100.0) - will be used for confidence-based sizing when implemented
            
        Returns:
            Dict with:
                - position_size_btc: Position size in BTC
                - position_value_usd: Position value in USD
                - base_position_size_pct: Base % from config
                - adjusted_position_size_pct: Adjusted % after all scaling
                - rr_multiplier: R:R multiplier applied
                - liquidation_safety_factor: Liquidation risk reduction factor
                - confidence_multiplier: Confidence-based multiplier (currently 1.0, will be implemented)
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
        
        # CONFIDENCE-BASED POSITION SIZING (TO BE IMPLEMENTED)
        # When confidence is implemented, it will influence position size:
        # - High confidence (70%+) → scale up position size
        # - Medium confidence (50-70%) → base position size
        # - Low confidence (<50%) → scale down position size
        # For now, confidence is optional and not used
        confidence_multiplier = 1.0  # Placeholder: will be calculated from confidence when implemented
        if confidence is not None:
            # TODO: Implement confidence-based position sizing
            # confidence_multiplier = calculate_confidence_multiplier(confidence)
            pass
        
        # Calculate R:R multiplier
        rr_multiplier = PositionSizeCalculator.calculate_rr_multiplier(risk_reward_ratio)
        
        # CRITICAL: Calculate liquidation safety factor (NEW)
        liquidation_safety_factor = 1.0  # Default: no reduction
        
        if stop_loss is not None and stop_loss > 0:
            from core.calculations.liquidation_calculator import LiquidationCalculator
            liq_calc = LiquidationCalculator(leverage=leverage)
            liquidation_price = liq_calc.calculate_liquidation_price(entry_price, direction)
            
            # Calculate distances
            if direction.upper() == "LONG":
                # LONG: entry > SL > liquidation
                sl_distance = entry_price - stop_loss
                liq_distance = entry_price - liquidation_price
                # Buffer zone: distance from SL to liquidation
                buffer_zone = stop_loss - liquidation_price
            else:  # SHORT
                # SHORT: liquidation > SL > entry
                sl_distance = stop_loss - entry_price
                liq_distance = liquidation_price - entry_price
                # Buffer zone: distance from SL to liquidation
                buffer_zone = liquidation_price - stop_loss
            
            # Calculate SL position as % of total liquidation distance
            if liq_distance > 0:
                sl_liq_ratio = sl_distance / liq_distance
                buffer_pct = (buffer_zone / liq_distance) * 100.0
                
                # LIQUIDATION RISK REDUCTION LOGIC (Research-backed for 40x BTC perps)
                # Based on professional risk management for high-leverage trading
                #
                # Safe SL placement: 30-50% of distance to liquidation
                # - SL at 50%+ of liq distance: SAFE (buffer_pct ≥ 50% → 1.0x, no reduction)
                # - SL at 30-50% of liq distance: ACCEPTABLE (buffer_pct 30-50% → 0.8-1.0x)
                # - SL at 15-30% of liq distance: RISKY (buffer_pct 15-30% → 0.5-0.8x)
                # - SL at <15% of liq distance: DANGEROUS (buffer_pct <15% → 0.3-0.5x)
                #
                # Why: Wicks on BTC perps can easily be 0.5-1.0% even in normal conditions
                # With 40x leverage (1.226% to liq), tight SL = high liquidation risk
                
                if buffer_pct >= 50.0:
                    # SAFE: SL has ≥50% buffer to liquidation
                    liquidation_safety_factor = 1.0  # No reduction
                elif buffer_pct >= 30.0:
                    # ACCEPTABLE: 30-50% buffer (linear scale 0.8 → 1.0)
                    liquidation_safety_factor = 0.8 + ((buffer_pct - 30.0) / 20.0) * 0.2
                elif buffer_pct >= 15.0:
                    # RISKY: 15-30% buffer (linear scale 0.5 → 0.8)
                    liquidation_safety_factor = 0.5 + ((buffer_pct - 15.0) / 15.0) * 0.3
                else:
                    # DANGEROUS: <15% buffer (linear scale 0.3 → 0.5)
                    liquidation_safety_factor = max(0.3, 0.3 + (buffer_pct / 15.0) * 0.2)
                
                logger.info(
                    f"🛡️ Liquidation risk check: Entry=${entry_price:.2f}, SL=${stop_loss:.2f}, Liq=${liquidation_price:.2f} | "
                    f"SL distance={sl_distance:.2f} ({sl_liq_ratio*100:.1f}% of liq distance), "
                    f"Buffer to liq={buffer_zone:.2f} ({buffer_pct:.1f}%) → "
                    f"safety_factor={liquidation_safety_factor:.2f}x"
                )
        else:
            logger.warning("⚠️ No stop loss provided - skipping liquidation risk check (NOT RECOMMENDED)")
        
        # Adjust position size based on R:R, liquidation safety, AND confidence (when implemented)
        adjusted_position_size_pct = base_position_size_pct * rr_multiplier * liquidation_safety_factor * confidence_multiplier
        
        # Calculate position value in USD (accounts for leverage)
        position_value_usd = balance * adjusted_position_size_pct * leverage
        
        # Convert to BTC
        position_size_btc = position_value_usd / entry_price
        
        confidence_str = f", Conf={confidence:.1f}%" if confidence is not None else ""
        logger.info(
            f"💰 Position sizing: Balance=${balance:.2f}, "
            f"Base={base_position_size_pct*100:.1f}%, R:R={risk_reward_ratio:.2f} → rr_mult={rr_multiplier:.2f}x, "
            f"Liq safety={liquidation_safety_factor:.2f}x, "
            f"Conf mult={confidence_multiplier:.2f}x{confidence_str} → "
            f"Adjusted={adjusted_position_size_pct*100:.1f}%, "
            f"Leverage={leverage}x → {position_size_btc:.4f} BTC (${position_value_usd:.2f})"
        )
        
        return {
            "position_size_btc": position_size_btc,
            "position_value_usd": position_value_usd,
            "base_position_size_pct": base_position_size_pct,
            "adjusted_position_size_pct": adjusted_position_size_pct,
            "rr_multiplier": rr_multiplier,
            "liquidation_safety_factor": liquidation_safety_factor,
            "confidence_multiplier": confidence_multiplier,
            "confidence": confidence,  # Include confidence in return for reference
            "balance": balance,
            "leverage": leverage,
            "entry_price": entry_price,
            "risk_reward_ratio": risk_reward_ratio,
            "stop_loss": stop_loss,
            "direction": direction
        }
    
    @staticmethod
    def get_balance_from_simulator() -> float:
        """
        Get current balance from Hyperliquid simulator
        
        Returns:
            Current balance in USD
            
        Raises:
            ValueError: If simulator is not available or balance cannot be accessed (NO FALLBACKS)
        """
        from core.services.system_initializer import get_system_initializer
        system_initializer = get_system_initializer()
        
        # Require simulator to be available (NO FALLBACKS)
        if "hyperliquid_simulator" not in system_initializer.singleton_systems:
            raise ValueError(
                "Hyperliquid simulator not available - cannot get balance (NO FALLBACKS). "
                "Ensure simulator is initialized before accessing balance."
            )
        
        hyperliquid_simulator = system_initializer.get_singleton_system("hyperliquid_simulator")
        
        if not hyperliquid_simulator:
            raise ValueError(
                "Hyperliquid simulator instance is None - cannot get balance (NO FALLBACKS)"
            )
        
        if not hasattr(hyperliquid_simulator, 'get_balance'):
            raise ValueError(
                f"Hyperliquid simulator does not have 'get_balance' method (NO FALLBACKS). "
                f"Simulator type: {type(hyperliquid_simulator)}"
            )
        
        try:
            balance = hyperliquid_simulator.get_balance()
            if balance is None:
                raise ValueError("Simulator get_balance() returned None (NO FALLBACKS)")
            return balance
        except Exception as e:
            raise ValueError(
                f"Failed to get balance from simulator: {e} (NO FALLBACKS)"
            ) from e
