#!/usr/bin/env python3
"""
Volatility Analyzer Module
Handles complex volatility calculations and analysis methods
"""

import time
from typing import Dict, List, Any
from loguru import logger


class VolatilityAnalyzer:
    """
    Analyzes volatility using multiple methods and strategies.
    Handles complex volatility calculations and threshold analysis.
    """
    
    def __init__(self):
        logger.debug("📊 VolatilityAnalyzer initialized")
    
    def calculate_weighted_volatility(self, candles: List[Dict]) -> Dict[str, Any]:
        """
        Calculate weighted volatility with emphasis on recent candles.
        Uses shorter window (last 10 candles) for faster change detection.
        
        Args:
            candles: List of candle dictionaries
        
        Returns:
            Dictionary with weighted volatility analysis
        """
        try:
            if len(candles) < 1:
                return {"weighted_volatility": 0.0, "max_volatility": 0.0, "current_volatility": 0.0}
            
            # Use last 15 candles (balanced: faster response but keeps trend context)
            recent_candles = candles[-15:] if len(candles) >= 15 else candles
            weighted_volatilities = []
            total_weight = 0
            
            for i, candle in enumerate(recent_candles):
                if candle["close"] > 0 and candle["high"] > 0 and candle["low"] > 0:
                    range_vol = (candle["high"] - candle["low"]) / candle["close"]
                    # Give exponentially more weight to recent candles (moderate increase for faster response)
                    weight = (i + 1) ** 2.7  # Slightly increased from 2.5 to 2.7 for better recent emphasis
                    weighted_volatilities.append(range_vol * weight)
                    total_weight += weight
            
            if not weighted_volatilities or total_weight == 0:
                return {"weighted_volatility": 0.0, "max_volatility": 0.0, "current_volatility": 0.0}
            
            # Calculate weighted average
            weighted_avg_volatility = sum(weighted_volatilities) / total_weight
            
            # Calculate maximum volatility from recent window
            max_volatility = max(weighted_volatilities) / max(weight for weight in [(i + 1) ** 2.7 for i in range(len(recent_candles))])
            
            # Current candle volatility (most recent)
            current_volatility = 0.0
            if len(candles) >= 1:
                current_candle = candles[-1]
                if current_candle["close"] > 0 and current_candle["high"] > 0 and current_candle["low"] > 0:
                    current_volatility = (current_candle["high"] - current_candle["low"]) / current_candle["close"]
            
            return {
                "weighted_volatility": weighted_avg_volatility,
                "max_volatility": max_volatility,
                "current_volatility": current_volatility,
                "volatility_count": len(weighted_volatilities)
            }
            
        except Exception as e:
            logger.error(f"❌ Weighted volatility calculation failed: {e}")
            return {"weighted_volatility": 0.0, "max_volatility": 0.0, "current_volatility": 0.0}
    
    def detect_volatility_spikes(self, current_volatility: float, threshold: float = 0.01) -> Dict[str, Any]:
        """
        Detect volatility spikes in current market conditions.
        
        Args:
            current_volatility: Current volatility value
            threshold: Spike detection threshold (default: 1%)
        
        Returns:
            Dictionary with spike detection results
        """
        try:
            is_spike = current_volatility > threshold
            spike_intensity = "NONE"
            
            if is_spike:
                if current_volatility > threshold * 3:
                    spike_intensity = "EXTREME"
                elif current_volatility > threshold * 2:
                    spike_intensity = "HIGH"
                else:
                    spike_intensity = "MODERATE"
            
            return {
                "is_spike": is_spike,
                "spike_intensity": spike_intensity,
                "threshold": threshold,
                "current_volatility": current_volatility
            }
            
        except Exception as e:
            logger.error(f"❌ Volatility spike detection failed: {e}")
            return {"is_spike": False, "spike_intensity": "NONE", "threshold": threshold, "current_volatility": 0.0}
    
    def calculate_primary_volatility(self, basic_vol: float, weighted_vol: float, current_vol: float, 
                                   is_spike: bool) -> float:
        """
        Calculate primary volatility using multiple methods.
        
        Args:
            basic_vol: Basic volatility from range analysis
            weighted_vol: Weighted average volatility
            current_vol: Current candle volatility
            is_spike: Whether current volatility is a spike
        
        Returns:
            Primary volatility value
        """
        try:
            if is_spike:
                # During spikes, prioritize current volatility almost entirely
                primary_volatility = (current_vol * 0.99) + (weighted_vol * 0.01)
            else:
                # Normal conditions: slightly increased current weight for faster response
                # 96% current (was 95%) - balanced: responsive but not too reactive to noise
                primary_volatility = (current_vol * 0.96) + (weighted_vol * 0.04)
            
            # Use the higher of primary or basic volatility
            final_volatility = max(primary_volatility, basic_vol)
            
            return final_volatility
            
        except Exception as e:
            logger.error(f"❌ Primary volatility calculation failed: {e}")
            return max(basic_vol, weighted_vol, current_vol)
