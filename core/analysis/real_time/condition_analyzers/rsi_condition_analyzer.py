#!/usr/bin/env python3
"""
RSI Condition Analyzer - SRP Compliant
Single Responsibility: Analyze RSI conditions for trading suitability
"""

from typing import Dict, Any
from loguru import logger


class RSIConditionAnalyzer:
    """Analyzes RSI conditions - follows SRP"""
    
    def __init__(self):
        pass
    
    def analyze_rsi_conditions(self, rsi: float) -> Dict[str, Any]:
        """Analyze RSI conditions using PASSED DATA - NO REDUNDANT FETCHING"""
        try:
            # Use passed parameter directly - data already fetched once
            current_rsi = rsi
            
            # Determine signal from RSI value
            if current_rsi < 30:
                rsi_signal = "OVERSOLD"
            elif current_rsi > 70:
                rsi_signal = "OVERBOUGHT"
            else:
                rsi_signal = "NEUTRAL"
            
            # Note: Trend and momentum require historical data - not available from single value
            rsi_trend = "UNKNOWN"
            rsi_momentum = 0.0
            
            # Handle None RSI values - no placeholders
            if current_rsi is None:
                return {
                    "factors": ["RSI: N/A (Data unavailable)"],
                    "risk_factors": ["RSI data unavailable"],
                    "positive_factors": [],
                    "rsi_value": None,
                    "rsi_zone": "UNKNOWN",
                    "rsi_trend": "UNKNOWN",
                    "rsi_momentum": 0.0,
                    "suitable_for_trading": False
                }
            
            # Convert to condition analyzer format
            factors = [f"RSI: {current_rsi:.1f} ({rsi_signal})"]
            risk_factors = []
            positive_factors = []
            
            # Analyze RSI signal
            if rsi_signal == "OVERSOLD":
                positive_factors.append("RSI oversold - potential buying opportunity")
            elif rsi_signal == "OVERBOUGHT":
                risk_factors.append("RSI overbought - potential selling pressure")
            elif rsi_signal == "NEUTRAL":
                factors.append("RSI in neutral zone")
            
            # Analyze RSI trend
            if rsi_trend == "BULLISH":
                positive_factors.append("RSI showing bullish momentum")
            elif rsi_trend == "BEARISH":
                risk_factors.append("RSI showing bearish momentum")
            
            # Determine trading suitability
            suitable_for_trading = rsi_signal in ["OVERSOLD", "NEUTRAL"] or (30 <= current_rsi <= 70)
            
            return {
                "factors": factors,
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "rsi_value": current_rsi,
                "rsi_zone": rsi_signal,
                "rsi_trend": rsi_trend,
                "rsi_momentum": rsi_momentum,
                "suitable_for_trading": suitable_for_trading
            }
        except Exception as e:
            logger.error(f"❌ RSI condition analysis failed: {e}")
            return {
                "factors": ["RSI analysis failed"],
                "risk_factors": ["Analysis error"],
                "positive_factors": [],
                "rsi_value": None,
                "rsi_zone": "UNKNOWN",
                "rsi_trend": "UNKNOWN",
                "rsi_momentum": 0.0,
                "suitable_for_trading": False
            }
    
