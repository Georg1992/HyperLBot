#!/usr/bin/env python3
"""
Entry Price Calculator - SRP Compliant
Single Responsibility: Calculate optimal entry prices for trades
"""

from typing import Dict, Any
from loguru import logger


class EntryPriceCalculator:
    """
    Single Responsibility: Calculate optimal entry prices for trades
    
    Features:
    - Volatility-based offset calculation
    - Market pressure adjustment
    - Support/resistance alignment
    - Achievable within 1-2 minutes
    """
    
    def __init__(self):
        logger.info("📍 Entry Price Calculator initialized")
    
    def calculate_entry_price(self, current_price: float, direction: str, 
                             market_data: Dict[str, Any]) -> float:
        """
        Calculate optimal entry price close to current market price
        Entry should be achievable within 1-2 minutes
        
        Returns:
            entry_price: Optimal limit order price
        """
        volatility = market_data.get("volatility_5m", 0.01)
        pressure = market_data.get("pressure_data", {}).get("direction", "NEUTRAL")
        volume_category = market_data.get("volume_category", "NORMAL")
        
        # Calculate base offset based on volatility
        base_offset_pct = self._calculate_base_offset(volatility)
        
        # Adjust offset based on market pressure and volume
        if direction == "LONG":
            entry_price = self._calculate_long_entry(
                current_price, base_offset_pct, pressure, volume_category, market_data
            )
        else:  # SHORT
            entry_price = self._calculate_short_entry(
                current_price, base_offset_pct, pressure, volume_category, market_data
            )
        
        logger.info(f"📍 Entry price: ${entry_price:,.2f} (offset: {abs(entry_price - current_price) / current_price:.3%})")
        
        return round(entry_price, 2)
    
    def _calculate_base_offset(self, volatility: float) -> float:
        """Calculate base offset percentage based on volatility"""
        if volatility < 0.005:  # VERY LOW volatility
            return 0.0003  # 0.03% (very tight)
        elif volatility < 0.01:  # LOW volatility
            return 0.0005  # 0.05%
        elif volatility < 0.02:  # MODERATE volatility
            return 0.001   # 0.1%
        elif volatility < 0.03:  # HIGH volatility
            return 0.0015  # 0.15%
        else:  # EXTREME volatility
            return 0.002   # 0.2%
    
    def _calculate_long_entry(self, current_price: float, base_offset_pct: float,
                             pressure: str, volume_category: str, market_data: Dict[str, Any]) -> float:
        """Calculate LONG entry price"""
        # If strong buy pressure + high volume, use tighter offset (price moving up)
        if pressure in ["BUY", "STRONG_BUY"] and volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            offset_pct = base_offset_pct * 0.5  # Closer to market
            logger.debug(f"📍 Tight entry: Strong buying pressure")
        else:
            offset_pct = base_offset_pct
        
        entry_price = current_price * (1 - offset_pct)
        
        # Check if near support - align with support level
        support_resistance = market_data.get("support_resistance", {})
        nearest_support = support_resistance.get("nearest_support", {}).get("price", 0)
        
        if nearest_support:
            distance_to_support = abs(entry_price - nearest_support) / current_price
            if distance_to_support < 0.002:  # Within 0.2%
                entry_price = nearest_support
                logger.info(f"📍 Entry aligned with support: ${entry_price:,.2f}")
        
        return entry_price
    
    def _calculate_short_entry(self, current_price: float, base_offset_pct: float,
                              pressure: str, volume_category: str, market_data: Dict[str, Any]) -> float:
        """Calculate SHORT entry price"""
        if pressure in ["SELL", "STRONG_SELL"] and volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            offset_pct = base_offset_pct * 0.5
            logger.debug(f"📍 Tight entry: Strong selling pressure")
        else:
            offset_pct = base_offset_pct
        
        entry_price = current_price * (1 + offset_pct)
        
        # Check if near resistance - align with resistance level
        support_resistance = market_data.get("support_resistance", {})
        nearest_resistance = support_resistance.get("nearest_resistance", {}).get("price", 0)
        
        if nearest_resistance:
            distance_to_resistance = abs(entry_price - nearest_resistance) / current_price
            if distance_to_resistance < 0.002:
                entry_price = nearest_resistance
                logger.info(f"📍 Entry aligned with resistance: ${entry_price:,.2f}")
        
        return entry_price


# Global singleton
_global_entry_price_calculator = None

def get_global_entry_price_calculator() -> EntryPriceCalculator:
    """Get global entry price calculator singleton"""
    global _global_entry_price_calculator
    if _global_entry_price_calculator is None:
        _global_entry_price_calculator = EntryPriceCalculator()
    return _global_entry_price_calculator
