#!/usr/bin/env python3
"""
Liquidation Calculator - Calculate liquidation prices for leveraged positions
Based on Hyperliquid liquidation formula: https://hyperliquid.gitbook.io/hyperliquid-docs/trading/liquidations
"""

from typing import Dict, Tuple
from loguru import logger

from config.config import TradingConfig


class LiquidationCalculator:
    """
    Calculate liquidation prices for leveraged positions on Hyperliquid
    
    Formula from Hyperliquid docs:
    liq_price = price - side * margin_available / position_size / (1 - l * side)
    Where l = 1 / MAINTENANCE_LEVERAGE
    
    For 40x leverage: maintenance margin = 1/40 = 2.5% = 0.025
    """
    
    def __init__(self, leverage: int = None):
        """
        Initialize liquidation calculator
        
        Args:
            leverage: Leverage multiplier (default from TradingConfig)
        """
        self.leverage = leverage or TradingConfig.LEVERAGE
        self.maintenance_margin_rate = 1.0 / self.leverage  # For 40x: 0.025 (2.5%)
        
    def calculate_liquidation_price(self, entry_price: float, side: str = "LONG") -> float:
        """
        Calculate liquidation price for a position at entry price with configured leverage
        
        Simplified formula for isolated margin:
        - Long: liq_price = entry_price * (1 - maintenance_margin_rate)
        - Short: liq_price = entry_price * (1 + maintenance_margin_rate)
        
        Args:
            entry_price: Entry price for the position
            side: "LONG" or "SHORT"
            
        Returns:
            Liquidation price
        """
        try:
            if entry_price <= 0:
                return 0.0
            
            side_upper = side.upper()
            if side_upper == "LONG":
                # Long position: liquidated when price drops by maintenance margin
                liquidation_price = entry_price * (1.0 - self.maintenance_margin_rate)
            elif side_upper == "SHORT":
                # Short position: liquidated when price rises by maintenance margin
                liquidation_price = entry_price * (1.0 + self.maintenance_margin_rate)
            else:
                logger.warning(f"⚠️ Invalid side '{side}', defaulting to LONG")
                liquidation_price = entry_price * (1.0 - self.maintenance_margin_rate)
            
            return liquidation_price
            
        except Exception as e:
            logger.error(f"❌ Liquidation price calculation failed: {e}")
            return 0.0
    
    def calculate_liquidation_prices_for_levels(self, support_level: float, resistance_level: float, 
                                                 current_price: float) -> Dict[str, float]:
        """
        Calculate liquidation prices for trading at support/resistance levels
        
        Args:
            support_level: Support level price (for LONG entries)
            resistance_level: Resistance level price (for SHORT entries)
            current_price: Current price
            
        Returns:
            Dictionary with liquidation prices for LONG and SHORT at each level
        """
        try:
            results = {}
            
            # Liquidation price if entering LONG at support level
            if support_level > 0 and support_level < current_price:
                results['long_at_support'] = self.calculate_liquidation_price(support_level, "LONG")
                results['long_at_support_entry'] = support_level
            
            # Liquidation price if entering SHORT at resistance level
            if resistance_level > 0 and resistance_level > current_price:
                results['short_at_resistance'] = self.calculate_liquidation_price(resistance_level, "SHORT")
                results['short_at_resistance_entry'] = resistance_level
            
            # Liquidation price if entering LONG at current price
            results['long_at_current'] = self.calculate_liquidation_price(current_price, "LONG")
            results['long_at_current_entry'] = current_price
            
            # Liquidation price if entering SHORT at current price
            results['short_at_current'] = self.calculate_liquidation_price(current_price, "SHORT")
            results['short_at_current_entry'] = current_price
            
            results['leverage'] = self.leverage
            results['maintenance_margin_rate'] = self.maintenance_margin_rate
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Liquidation prices calculation failed: {e}")
            return {}
    
    def get_liquidation_distance_pct(self, entry_price: float, side: str = "LONG") -> float:
        """
        Get liquidation distance as percentage from entry price
        
        Args:
            entry_price: Entry price
            side: "LONG" or "SHORT"
            
        Returns:
            Percentage distance to liquidation (e.g., 2.5 for 2.5%)
        """
        liquidation_price = self.calculate_liquidation_price(entry_price, side)
        if entry_price <= 0:
            return 0.0
        
        if side.upper() == "LONG":
            distance_pct = ((entry_price - liquidation_price) / entry_price) * 100.0
        else:
            distance_pct = ((liquidation_price - entry_price) / entry_price) * 100.0
        
        return distance_pct

