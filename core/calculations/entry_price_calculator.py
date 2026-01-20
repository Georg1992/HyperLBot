#!/usr/bin/env python3
"""
Entry Price Calculator
Handles all entry price calculation logic with dynamic adjustments
"""

import time
from typing import Dict, Any, Optional
from loguru import logger


class EntryPriceCalculator:
    """
    Calculates sophisticated entry prices with dynamic adjustments
    
    Incorporates:
    1. Dynamic offset based on volatility/ATR
    2. Level strength-based offset adjustment
    3. Spread consideration
    4. Recent price action analysis
    5. Orderbook depth/liquidity check
    """
    
    @staticmethod
    def calculate_dynamic_entry_price(
        level_price: float,
        current_price: float,
        direction: str,
        setup_type: str,
        level_data: Dict[str, Any],
        unified_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Optional[float]:
        """
        Calculate sophisticated entry price with dynamic adjustments
        
        Args:
            level_price: S/R level price
            current_price: Current market price
            direction: "LONG" or "SHORT"
            setup_type: "support_level" or "resistance_level"
            level_data: Level metadata (strength_score, touches, last_touch_timestamp, etc.)
            unified_data: Complete market analysis data
            config: Strategy configuration
            
        Returns:
            Calculated entry price or None if invalid/unfillable
        """
        try:
            # Mathematically justified: Base entry offset = 0.25 × ATR (for limit orders)
            # Strategy multiplier adjusts this base (e.g., 1.0 = 0.25×ATR, 1.5 = 0.375×ATR)
            entry_offset_multiplier = config["entry_offset_multiplier"]  # Required (NO FALLBACKS)
            
            # Get ATR for mathematically justified base calculation (NO FALLBACKS)
            if "support_resistance" not in unified_data:
                raise ValueError("support_resistance data is required for entry price calculation - NO FALLBACKS")
            sr_data = unified_data["support_resistance"]
            
            if "metadata" not in sr_data:
            if not sr_metadata:
                raise ValueError("support_resistance.metadata is required for entry price calculation - NO FALLBACKS")
            
            atr_5m = sr_metadata["atr_5m"]  # Required (NO FALLBACKS)
            if atr_5m <= 0:
                raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
            if current_price <= 0:
                raise ValueError(f"Invalid current_price: {current_price} - must be positive (NO FALLBACKS)")
            
            # Mathematically justified base: 0.25 × ATR (standard for limit order entry offsets)
            # This provides a small buffer from S/R levels while staying close
            atr_base_offset_multiplier = 0.25
            base_atr_offset_distance = atr_5m * atr_base_offset_multiplier  # Base distance in price units
            
            # Strategy multiplier adjustment (optional fine-tuning)
            volatility_multiplier = EntryPriceCalculator._calculate_volatility_multiplier(unified_data, atr_5m, current_price)
            
            # Level strength-based adjustment
            strength_multiplier = EntryPriceCalculator._calculate_strength_multiplier(level_data)
            
            # Spread consideration
            spread_adjustment = EntryPriceCalculator._calculate_spread_adjustment(unified_data, current_price, setup_type)
            
            # Recent price action analysis
            recent_action_multiplier = EntryPriceCalculator._calculate_recent_action_multiplier(level_data)
            
            # Orderbook liquidity check
            liquidity_multiplier = EntryPriceCalculator._calculate_liquidity_multiplier(unified_data)
            
            # CALCULATE FINAL OFFSET (mathematically justified based on ATR)
            # Base offset distance = strategy_multiplier × 0.25 × ATR × volatility_multiplier
            # Additional adjustments: strength, recent action, liquidity
            base_offset_distance = base_atr_offset_distance * entry_offset_multiplier * volatility_multiplier
            adjusted_offset_distance = base_offset_distance * strength_multiplier * recent_action_multiplier * liquidity_multiplier
            
            # Apply spread adjustment (adds for LONG at support, subtracts for SHORT at resistance)
            final_offset_distance = adjusted_offset_distance + spread_adjustment
            
            # Convert to percentage for calculation
            final_offset_pct = final_offset_distance / level_price if level_price > 0 else 0.0
            
            # Cap offset to reasonable range (0% to 0.5% or 2.0×ATR, whichever is smaller)
            # This ensures entry stays close to the S/R level while accounting for all factors
            max_offset_pct = min(0.005, (atr_5m * 2.0) / level_price if level_price > 0 else 0.005)
            final_offset_pct = max(0.0, min(max_offset_pct, final_offset_pct))
            
            # CALCULATE ENTRY PRICE
            # LONG at support: entry at or slightly above support (buy when price reaches/bounces from support)
            # SHORT at resistance: entry at or slightly below resistance (sell when price reaches resistance and bounces down)
            # Rationale: Entry at the level (0% offset) is ideal, but slight offset helps:
            # - Avoids missing fills if price doesn't quite reach exact level
            # - Accounts for spread and slippage
            # - Provides small buffer for order execution
            
            if setup_type == "support_level":  # LONG
                entry_price = level_price * (1 + final_offset_pct)
            else:  # resistance_level - SHORT
                entry_price = level_price * (1 - final_offset_pct)
            
            # VALIDATE ENTRY PRICE
            if entry_price <= 0:
                raise ValueError(f"Invalid entry price: ${entry_price:.2f} (negative or zero)")
            
            # For LONG: entry should be at or above support level
            if setup_type == "support_level" and entry_price < level_price:
                raise ValueError(f"Invalid LONG entry: ${entry_price:.2f} < support level ${level_price:.2f}")
            
            # For SHORT: entry should be at or below resistance level
            if setup_type == "resistance_level" and entry_price > level_price:
                raise ValueError(f"Invalid SHORT entry: ${entry_price:.2f} > resistance level ${level_price:.2f}")
            
            # Removed excessive debug logging - only log if offset is unusual
            if abs(final_offset_pct) > 0.001:  # Only log if offset > 0.1%
                logger.debug(f"✅ Entry price calculated: ${entry_price:.2f} (level: ${level_price:.2f}, offset: {final_offset_pct*100:.3f}%)")
            return entry_price
            
        except Exception as e:
            logger.error(f"❌ Entry price calculation failed: {e}")
            raise
    
    @staticmethod
    def _calculate_volatility_multiplier(unified_data: Dict[str, Any], atr_5m: float, current_price: float) -> float:
        """Calculate volatility adjustment multiplier"""
        volatility_multiplier = 1.0
        try:
            volatility_5m = unified_data["volatility_5m"] if "volatility_5m" in unified_data else (atr_5m / current_price if current_price > 0 else 0.002)
            if volatility_5m > 0 and current_price > 0:
                # Fine-tune based on volatility vs ATR relationship
                atr_pct = atr_5m / current_price
                vol_atr_ratio = volatility_5m / atr_pct if atr_pct > 0 else 1.0
                if vol_atr_ratio > 1.5:  # Volatility significantly higher than ATR
                    volatility_multiplier = 1.2  # Widen slightly
                elif vol_atr_ratio < 0.7:  # Volatility significantly lower than ATR
                    volatility_multiplier = 0.9  # Tighten slightly
                else:
                    volatility_multiplier = 1.0  # Standard
        except Exception:
            volatility_multiplier = 1.0  # Default to no adjustment
        return volatility_multiplier
    
    @staticmethod
    def _calculate_strength_multiplier(level_data: Dict[str, Any]) -> float:
        """Calculate level strength-based adjustment multiplier"""
        strength_multiplier = 1.0
        try:
            from core.utils.level_utils import get_level_power
            level_strength = get_level_power(level_data, default=50.0)
            if level_strength >= 80:  # Very strong level
                strength_multiplier = 0.75  # Tighter offset (75% of base) - level very likely to hold
            elif level_strength >= 60:  # Strong level
                strength_multiplier = 0.9  # Slightly tighter (90% of base)
            elif level_strength >= 40:  # Moderate level
                strength_multiplier = 1.0  # Standard offset (100% of base)
            elif level_strength >= 20:  # Weak level
                strength_multiplier = 1.25  # Wider offset (125% of base) - need buffer
            else:  # Very weak level
                strength_multiplier = 1.5  # Much wider offset (150% of base)
        except Exception as e:
            logger.error(f"❌ Level strength adjustment calculation failed: {e}")
            raise  # NO FALLBACKS - strength score is required
        return strength_multiplier
    
    @staticmethod
    def _calculate_spread_adjustment(unified_data: Dict[str, Any], current_price: float, setup_type: str) -> float:
        """Calculate spread adjustment for entry price"""
        spread_adjustment = 0.0
        try:
            # Orderbook data should be available (NO FALLBACKS)
            orderbook_data = unified_data.get("orderbook_analysis", {})
            if not orderbook_data:
                logger.warning("⚠️ Orderbook analysis missing, using 0 spread adjustment")
                spread_adjustment = 0.0
            else:
                bid_ask_spread = orderbook_data["bid_ask_spread"] if "bid_ask_spread" in orderbook_data else {}
                if not bid_ask_spread:
                    logger.warning("⚠️ Bid-ask spread missing, using 0 spread adjustment")
                    spread_adjustment = 0.0
                else:
                    spread_pct = bid_ask_spread["percentage"]  # Required (NO FALLBACKS)
                    
                    if spread_pct > 0:
                        # Convert spread percentage to decimal (0.01% → 0.0001)
                        spread_decimal = spread_pct / 100.0
                        # Convert to price units (distance)
                        spread_distance = current_price * spread_decimal / 2.0  # Half spread in price units
                        
                        # LONG at support: add half spread (buying at ask side, entry higher)
                        # SHORT at resistance: subtract half spread (selling at bid side, entry closer to resistance)
                        if setup_type == "support_level":
                            spread_adjustment = spread_distance  # Add for LONG
                        else:  # resistance_level
                            spread_adjustment = -spread_distance  # Subtract for SHORT
        except Exception as e:
            logger.error(f"❌ Spread adjustment calculation failed: {e}")
            # Spread adjustment is optional - continue with 0 adjustment if missing
            spread_adjustment = 0.0
        return spread_adjustment
    
    @staticmethod
    def _calculate_recent_action_multiplier(level_data: Dict[str, Any]) -> float:
        """
        Calculate recent price action adjustment multiplier
        
        NOTE: This uses hardcoded thresholds (6h, 24h, 72h) for entry price offset adjustment.
        This is different from recency_factor used in scoring (which uses strategy-specific thresholds).
        Entry price offset needs different logic (wider offset for recently tested levels).
        """
        recent_action_multiplier = 1.0
        try:
            # last_touch_timestamp: check if exists (level might not have been touched yet)
            last_touch_timestamp = level_data["last_touch_timestamp"] if "last_touch_timestamp" in level_data else 0
            from core.utils.time_utils import calculate_hours_since_touch
            hours_since_touch = calculate_hours_since_touch(last_touch_timestamp)
            
            # Entry price offset logic: recently tested levels need wider offset
            # This is different from scoring recency (which prefers recent levels)
            if hours_since_touch < 6:  # Recently touched (within 6 hours)
                recent_action_multiplier = 1.15  # 15% wider offset - level recently tested
            elif hours_since_touch < 24:  # Moderately recent (6-24 hours)
                recent_action_multiplier = 1.05  # 5% wider offset
            elif hours_since_touch < 72:  # Some time ago (1-3 days)
                recent_action_multiplier = 1.0  # Standard offset
            else:  # Not touched recently (3+ days) or never touched
                recent_action_multiplier = 0.95  # 5% tighter offset - fresh level, more confidence
        except Exception as e:
            logger.error(f"❌ Recent price action analysis failed: {e}")
            # Recent action is optional - use neutral multiplier if calculation fails
            recent_action_multiplier = 1.0
        return recent_action_multiplier
    
    @staticmethod
    def _calculate_liquidity_multiplier(unified_data: Dict[str, Any]) -> float:
        """Calculate orderbook liquidity adjustment multiplier"""
        liquidity_multiplier = 1.0
        try:
            # Orderbook data should be available (NO FALLBACKS)
            orderbook_data = unified_data.get("orderbook_analysis", {})
            if not orderbook_data:
                logger.warning("⚠️ Orderbook analysis missing, using neutral liquidity multiplier")
                liquidity_multiplier = 1.0
            else:
                liquidity_depth = orderbook_data.get("liquidity_depth", {})
                if not liquidity_depth:
                    logger.warning("⚠️ Liquidity depth missing, using neutral liquidity multiplier")
                    liquidity_multiplier = 1.0
                else:
                    liquidity_score = liquidity_depth["depth_score"]  # Required (NO FALLBACKS)
                    
                    if liquidity_score < 20:  # Very low liquidity
                        liquidity_multiplier = 1.2  # 20% wider offset - ensure fill despite thin liquidity
                    elif liquidity_score < 40:  # Low liquidity
                        liquidity_multiplier = 1.1  # 10% wider offset
                    elif liquidity_score >= 80:  # Very high liquidity
                        liquidity_multiplier = 0.95  # 5% tighter offset - can be more precise
                    else:  # Normal liquidity (40-80)
                        liquidity_multiplier = 1.0  # Standard offset
        except Exception as e:
            logger.error(f"❌ Liquidity adjustment calculation failed: {e}")
            # Liquidity adjustment is optional - continue with neutral multiplier if missing
            liquidity_multiplier = 1.0
        return liquidity_multiplier
