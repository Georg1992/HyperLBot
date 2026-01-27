#!/usr/bin/env python3
"""
Trend Data Mapper - Single Responsibility: Map Trend Data to Unified Format
Extracted from MarketDataService for SRP compliance
"""

from typing import Dict, Any
from loguru import logger


class TrendDataMapper:
    """Handles trend data transformation and mapping"""
    
    def map_trend_data(self, raw_trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map trend calculator output to unified format - NO FALLBACKS
        
        Args:
            raw_trend_data: Raw trend data from trend calculator
            
        Returns:
            Mapped trend data in unified format
            
        Raises:
            ValueError: If raw_trend_data is invalid
        """
        try:
            if not raw_trend_data or not isinstance(raw_trend_data, dict):
                raise ValueError(f"Invalid raw_trend_data: expected dict, got {type(raw_trend_data)} - NO FALLBACKS")
            
            # Extract all timeframe trends
            trend_15m = raw_trend_data["trend_15m"]  # Required (NO FALLBACKS)
            trend_1h = raw_trend_data["trend_1h"]  # Required (NO FALLBACKS)
            trend_4h = raw_trend_data["trend_4h"]  # Required (NO FALLBACKS)
            trend_24h = raw_trend_data["trend_24h"]  # Required (NO FALLBACKS)
            
            # Extract numeric strength from details (trend calculator returns strength as float 0.0-1.0)
            # NO FALLBACKS - details and strength are required
            details = raw_trend_data["details"]
            trend_1h_details = details["1h"]
            numeric_strength = trend_1h_details["strength"]
            
            # Timestamp is required from trend calculator (NO FALLBACKS)
            if "timestamp" not in raw_trend_data:
                raise ValueError("Trend data missing 'timestamp' key (NO FALLBACKS)")
            
            # Use 1h as primary for strategy decisions, but preserve all timeframes
            primary_trend = trend_1h
            mapped_direction = self.map_trend_to_direction(primary_trend)
            
            # Create unified trend structure with ALL timeframes
            # Use numeric strength (0.0-1.0) instead of string mapping for strategy manager compatibility
            mapped_trend = {
                "direction": mapped_direction,
                "strength": float(numeric_strength),  # Numeric strength for strategy manager (NO FALLBACKS)
                "timeframes": {
                    "short": trend_15m,      # 15m trend
                    "medium": trend_1h,       # 1h trend  
                    "long": trend_24h         # 24h trend
                },
                "detailed_timeframes": {
                    "trend_15m": trend_15m,
                    "trend_1h": trend_1h,
                    "trend_4h": trend_4h,
                    "trend_24h": trend_24h
                },
                "raw_data": raw_trend_data,  # Keep original data for detailed analysis
                "timestamp": raw_trend_data["timestamp"],  # Required (NO FALLBACKS)
                "data_type": "trend"
            }
            
            return mapped_trend
            
        except Exception as e:
            logger.error(f"❌ Trend mapping failed: {e}")
            raise
    
    def map_trend_to_direction(self, trend: str) -> str:
        """
        Map detailed trend to simple direction for strategy manager - NO FALLBACKS
        
        Args:
            trend: Detailed trend string (e.g., "STRONG_UPTREND", "DOWNTREND")
            
        Returns:
            Simple direction string ("BULLISH", "BEARISH", "SIDEWAYS")
            
        Raises:
            ValueError: If trend is invalid or unsupported
        """
        if not trend or trend == "UNKNOWN" or trend is None:
            raise ValueError(f"Invalid trend value: {trend} (NO FALLBACKS)")
            
        trend_mapping = {
            "STRONG_UPTREND": "BULLISH",
            "UPTREND": "BULLISH", 
            "WEAK_UPTREND": "BULLISH",
            "STRONG_DOWNTREND": "BEARISH",
            "DOWNTREND": "BEARISH",
            "WEAK_DOWNTREND": "BEARISH",
            "SIDEWAYS": "SIDEWAYS"
        }
        if trend not in trend_mapping:
            raise ValueError(f"Unsupported trend value: {trend} - must be one of {list(trend_mapping.keys())} (NO FALLBACKS)")
        return trend_mapping[trend]
    
    def map_trend_to_strength(self, trend: str) -> str:
        """
        Map detailed trend to strength level - NO FALLBACKS
        
        Note: This is deprecated, use numeric strength from details instead
        
        Args:
            trend: Detailed trend string
            
        Returns:
            Strength level string ("STRONG", "MODERATE", "WEAK", "NEUTRAL")
            
        Raises:
            ValueError: If trend is invalid or unsupported
        """
        if not trend or trend == "UNKNOWN" or trend is None:
            raise ValueError(f"Invalid trend value: {trend} (NO FALLBACKS)")
            
        strength_mapping = {
            "STRONG_UPTREND": "STRONG",
            "STRONG_DOWNTREND": "STRONG",
            "UPTREND": "MODERATE",
            "DOWNTREND": "MODERATE", 
            "WEAK_UPTREND": "WEAK",
            "WEAK_DOWNTREND": "WEAK",
            "SIDEWAYS": "NEUTRAL"
        }
        if trend not in strength_mapping:
            raise ValueError(f"Unsupported trend value: {trend} - must be one of {list(strength_mapping.keys())} (NO FALLBACKS)")
        return strength_mapping[trend]
