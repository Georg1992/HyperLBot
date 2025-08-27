#!/usr/bin/env python3
"""
Prediction Confidence Module
Contains confidence calculation methods extracted from prediction_engine.py
"""

import numpy as np
from typing import Dict, Any
from loguru import logger

class PredictionConfidence:
    """Confidence calculation methods for prediction engine"""
    
    def __init__(self):
        """Initialize confidence calculation system"""
        # Initialize confidence smoothing variables for stability
        self._last_reversion_confidence = 0.5
        self._last_momentum_confidence = 0.6
        self._last_breakout_confidence = 0.5
        
        logger.info("🎯 Prediction Confidence system initialized")
    
    def calculate_breakout_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float, rsi: float = 50, volume_depth: float = 0, depth_imbalance: float = 0, trend_1d: Dict = {}) -> float:
        """Calculate confidence for breakout predictions with enhanced smoothing"""
        try:
            # Extract trend strengths
            trend_1h_strength = trend_1h.get("strength", 0.5)
            trend_5m_strength = trend_5m.get("strength", 0.5)
            trend_1d_strength = trend_1d.get("strength", 0.5) if trend_1d else 0.5
            
            # Extract trend directions
            trend_1h_direction = trend_1h.get("direction", "NEUTRAL")
            trend_5m_direction = trend_5m.get("direction", "NEUTRAL")
            trend_1d_direction = trend_1d.get("direction", "NEUTRAL") if trend_1d else "NEUTRAL"
            
            # Base confidence from trend alignment
            base_confidence = 0.0
            
            # Strong alignment across timeframes
            if (trend_1h_direction == "UPTREND" and trend_5m_direction == "UPTREND" and 
                trend_1d_direction in ["UPTREND", "NEUTRAL"]):
                base_confidence = 0.7
            elif (trend_1h_direction == "DOWNTREND" and trend_5m_direction == "DOWNTREND" and 
                  trend_1d_direction in ["DOWNTREND", "NEUTRAL"]):
                base_confidence = 0.7
            # Medium alignment (5m and 1h aligned)
            elif (trend_1h_direction == "UPTREND" and trend_5m_direction == "UPTREND"):
                base_confidence = 0.6
            elif (trend_1h_direction == "DOWNTREND" and trend_5m_direction == "DOWNTREND"):
                base_confidence = 0.6
            # Weak alignment (only 5m trend)
            elif trend_5m_direction in ["UPTREND", "DOWNTREND"]:
                base_confidence = 0.4
            else:
                base_confidence = 0.2
            
            # Volatility adjustment (higher volatility = higher confidence for breakouts)
            volatility_multiplier = min(2.0, 1.0 + (volatility * 10))  # Cap at 2x
            base_confidence *= volatility_multiplier
            
            # RSI adjustment
            rsi_multiplier = 1.0
            if rsi < 30:  # Oversold - bullish breakout more likely
                if trend_5m_direction == "UPTREND":
                    rsi_multiplier = 1.2
                else:
                    rsi_multiplier = 0.8
            elif rsi > 70:  # Overbought - bearish breakout more likely
                if trend_5m_direction == "DOWNTREND":
                    rsi_multiplier = 1.2
                else:
                    rsi_multiplier = 0.8
            
            base_confidence *= rsi_multiplier
            
            # Volume depth adjustment
            if volume_depth > 0:
                depth_multiplier = min(1.5, 1.0 + (volume_depth * 0.1))
                base_confidence *= depth_multiplier
            
            # Depth imbalance adjustment
            if abs(depth_imbalance) > 0.1:
                imbalance_multiplier = 1.0 + (abs(depth_imbalance) * 0.5)
                base_confidence *= imbalance_multiplier
            
            # Apply smoothing to prevent wild swings
            smoothed_confidence = (base_confidence * 0.7) + (self._last_breakout_confidence * 0.3)
            self._last_breakout_confidence = smoothed_confidence
            
            # Ensure confidence is within bounds
            final_confidence = max(0.1, min(0.95, smoothed_confidence))
            
            return final_confidence
            
        except Exception as e:
            logger.error(f"Breakout confidence calculation failed: {e}")
            return 0.3  # Conservative fallback
    
    def calculate_reversion_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float, rsi: float = 50, volume_depth: float = 0, depth_imbalance: float = 0, trend_1d: Dict = {}) -> float:
        """Calculate confidence for reversion predictions with enhanced smoothing"""
        try:
            # Extract trend strengths
            trend_1h_strength = trend_1h.get("strength", 0.5)
            trend_5m_strength = trend_5m.get("strength", 0.5)
            trend_1d_strength = trend_1d.get("strength", 0.5) if trend_1d else 0.5
            
            # Extract trend directions
            trend_1h_direction = trend_1h.get("direction", "NEUTRAL")
            trend_5m_direction = trend_5m.get("direction", "NEUTRAL")
            trend_1d_direction = trend_1d.get("direction", "NEUTRAL") if trend_1d else "NEUTRAL"
            
            # Base confidence from trend divergence (reversion signal)
            base_confidence = 0.0
            
            # Strong reversion signal (opposite trends)
            if (trend_1h_direction == "UPTREND" and trend_5m_direction == "DOWNTREND"):
                base_confidence = 0.6
            elif (trend_1h_direction == "DOWNTREND" and trend_5m_direction == "UPTREND"):
                base_confidence = 0.6
            # Medium reversion signal (one neutral)
            elif (trend_1h_direction == "NEUTRAL" and trend_5m_direction in ["UPTREND", "DOWNTREND"]):
                base_confidence = 0.5
            elif (trend_5m_direction == "NEUTRAL" and trend_1h_direction in ["UPTREND", "DOWNTREND"]):
                base_confidence = 0.5
            # Weak reversion signal
            else:
                base_confidence = 0.3
            
            # Volatility adjustment (lower volatility = higher confidence for reversions)
            volatility_multiplier = max(0.5, 1.0 - (volatility * 5))  # Floor at 0.5x
            base_confidence *= volatility_multiplier
            
            # RSI adjustment for reversion
            rsi_multiplier = 1.0
            if rsi < 30:  # Oversold - bullish reversion more likely
                if trend_5m_direction == "DOWNTREND":
                    rsi_multiplier = 1.3  # Strong reversion signal
                else:
                    rsi_multiplier = 0.9
            elif rsi > 70:  # Overbought - bearish reversion more likely
                if trend_5m_direction == "UPTREND":
                    rsi_multiplier = 1.3  # Strong reversion signal
                else:
                    rsi_multiplier = 0.9
            elif 40 <= rsi <= 60:  # Neutral RSI - good for reversions
                rsi_multiplier = 1.1
            
            base_confidence *= rsi_multiplier
            
            # Volume depth adjustment (lower volume = higher reversion confidence)
            if volume_depth > 0:
                depth_multiplier = max(0.7, 1.0 - (volume_depth * 0.05))
                base_confidence *= depth_multiplier
            
            # Depth imbalance adjustment
            if abs(depth_imbalance) > 0.1:
                imbalance_multiplier = 1.0 + (abs(depth_imbalance) * 0.3)
                base_confidence *= imbalance_multiplier
            
            # Apply smoothing to prevent wild swings
            smoothed_confidence = (base_confidence * 0.7) + (self._last_reversion_confidence * 0.3)
            self._last_reversion_confidence = smoothed_confidence
            
            # Ensure confidence is within bounds
            final_confidence = max(0.1, min(0.95, smoothed_confidence))
            
            return final_confidence
            
        except Exception as e:
            logger.error(f"Reversion confidence calculation failed: {e}")
            return 0.3  # Conservative fallback
    
    def calculate_momentum_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float, rsi: float = 50, volume_depth: float = 0, depth_imbalance: float = 0) -> float:
        """Calculate confidence for momentum predictions with enhanced smoothing"""
        try:
            # Extract trend strengths
            trend_1h_strength = trend_1h.get("strength", 0.5)
            trend_5m_strength = trend_5m.get("strength", 0.5)
            
            # Extract trend directions
            trend_1h_direction = trend_1h.get("direction", "NEUTRAL")
            trend_5m_direction = trend_5m.get("direction", "NEUTRAL")
            
            # Base confidence from momentum alignment
            base_confidence = 0.0
            
            # Strong momentum (aligned trends with high strength)
            if (trend_1h_direction == trend_5m_direction and 
                trend_5m_direction in ["UPTREND", "DOWNTREND"] and
                trend_5m_strength > 0.6):
                base_confidence = 0.7
            # Medium momentum (aligned trends)
            elif trend_1h_direction == trend_5m_direction and trend_5m_direction in ["UPTREND", "DOWNTREND"]:
                base_confidence = 0.6
            # Weak momentum (only 5m trend)
            elif trend_5m_direction in ["UPTREND", "DOWNTREND"]:
                base_confidence = 0.4
            else:
                base_confidence = 0.2
            
            # Volatility adjustment (moderate volatility = good for momentum)
            volatility_multiplier = 1.0
            if 0.001 <= volatility <= 0.005:  # Sweet spot for momentum
                volatility_multiplier = 1.2
            elif volatility > 0.01:  # Too volatile
                volatility_multiplier = 0.7
            elif volatility < 0.0005:  # Too stable
                volatility_multiplier = 0.8
            
            base_confidence *= volatility_multiplier
            
            # RSI adjustment for momentum
            rsi_multiplier = 1.0
            if 30 <= rsi <= 70:  # Good range for momentum
                rsi_multiplier = 1.1
            elif rsi < 20 or rsi > 80:  # Extreme levels - momentum may reverse
                rsi_multiplier = 0.7
            
            base_confidence *= rsi_multiplier
            
            # Volume depth adjustment (higher volume = higher momentum confidence)
            if volume_depth > 0:
                depth_multiplier = min(1.3, 1.0 + (volume_depth * 0.1))
                base_confidence *= depth_multiplier
            
            # Depth imbalance adjustment
            if abs(depth_imbalance) > 0.1:
                imbalance_multiplier = 1.0 + (abs(depth_imbalance) * 0.4)
                base_confidence *= imbalance_multiplier
            
            # Apply smoothing to prevent wild swings
            smoothed_confidence = (base_confidence * 0.7) + (self._last_momentum_confidence * 0.3)
            self._last_momentum_confidence = smoothed_confidence
            
            # Ensure confidence is within bounds
            final_confidence = max(0.1, min(0.95, smoothed_confidence))
            
            return final_confidence
            
        except Exception as e:
            logger.error(f"Momentum confidence calculation failed: {e}")
            return 0.3  # Conservative fallback
