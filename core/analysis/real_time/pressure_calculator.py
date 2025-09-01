#!/usr/bin/env python3
"""
Pressure Calculator Module
Centralized market pressure calculations from orderbook data
"""

from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class PressureCalculator:
    """Centralized market pressure calculation system"""
    
    def __init__(self):
        logger.info("📊 Pressure Calculator initialized")
    
    def calculate_orderbook_pressure(self, bids: List[Dict], asks: List[Dict]) -> Dict[str, Any]:
        """Calculate market pressure from orderbook data"""
        try:
            if not bids or not asks:
                return self._get_default_pressure()
            
            # Calculate depth metrics
            bid_depth_5 = sum(float(level.get('sz', 0)) for level in bids[:5])
            ask_depth_5 = sum(float(level.get('sz', 0)) for level in asks[:5])
            bid_depth_10 = sum(float(level.get('sz', 0)) for level in bids[:10])
            ask_depth_10 = sum(float(level.get('sz', 0)) for level in asks[:10])
            
            total_depth_5 = bid_depth_5 + ask_depth_5
            total_depth_10 = bid_depth_10 + ask_depth_10
            
            if total_depth_5 == 0:
                return self._get_default_pressure()
            
            # Calculate pressure metrics
            bid_pressure_ratio = bid_depth_5 / total_depth_5
            ask_pressure_ratio = ask_depth_5 / total_depth_5
            pressure_imbalance = bid_pressure_ratio - ask_pressure_ratio
            
            # Calculate depth concentration (how much of depth is in top 5 vs top 10)
            depth_concentration = total_depth_5 / total_depth_10 if total_depth_10 > 0 else 1.0
            
            # Determine pressure direction and strength
            direction, strength = self._categorize_pressure_direction(pressure_imbalance, depth_concentration)
            confidence = self._calculate_pressure_confidence(total_depth_5, pressure_imbalance)
            trend = self._determine_pressure_trend(pressure_imbalance, depth_concentration)
            
            return {
                "direction": direction,
                "confidence": confidence,
                "strength": strength,
                "trend": trend,
                "bid_pressure_ratio": round(bid_pressure_ratio, 3),
                "ask_pressure_ratio": round(ask_pressure_ratio, 3),
                "pressure_imbalance": round(pressure_imbalance, 4),
                "depth_concentration": round(depth_concentration, 3),
                "bid_depth_5": round(bid_depth_5, 2),
                "ask_depth_5": round(ask_depth_5, 2),
                "total_depth_5": round(total_depth_5, 2),
                "data_source": "live_orderbook_calculation"
            }
            
        except Exception as e:
            logger.error(f"❌ Orderbook pressure calculation failed: {e}")
            return self._get_default_pressure()
    
    def _categorize_pressure_direction(self, pressure_imbalance: float, depth_concentration: float) -> Tuple[str, float]:
        """Categorize pressure direction and strength"""
        try:
            # Determine direction based on imbalance
            abs_imbalance = abs(pressure_imbalance)
            
            if pressure_imbalance > 0.25:  # Strong bid pressure
                direction = "STRONG_BUY"
                strength = min(0.9, 0.5 + abs_imbalance)
            elif pressure_imbalance > 0.1:  # Moderate bid pressure
                direction = "BUY"
                strength = 0.5 + (abs_imbalance * 2)
            elif pressure_imbalance < -0.25:  # Strong ask pressure
                direction = "STRONG_SELL"
                strength = min(0.9, 0.5 + abs_imbalance)
            elif pressure_imbalance < -0.1:  # Moderate ask pressure
                direction = "SELL"
                strength = 0.5 + (abs_imbalance * 2)
            else:  # Balanced pressure
                direction = "NEUTRAL"
                strength = 0.5 - (abs_imbalance * 2)
            
            # Adjust strength based on depth concentration
            if depth_concentration > 0.8:  # High concentration = stronger signal
                strength = min(0.95, strength * 1.2)
            elif depth_concentration < 0.6:  # Low concentration = weaker signal
                strength = max(0.1, strength * 0.8)
            
            return direction, round(strength, 3)
            
        except Exception as e:
            logger.warning(f"Pressure direction categorization failed: {e}")
            return "NEUTRAL", 0.5
    
    def _calculate_pressure_confidence(self, total_depth: float, pressure_imbalance: float) -> str:
        """Calculate confidence percentage for pressure reading"""
        try:
            # Base confidence on depth and imbalance strength
            depth_factor = min(1.0, total_depth / 20.0)  # 20 BTC = 100% depth confidence
            imbalance_factor = min(1.0, abs(pressure_imbalance) * 4)  # 0.25 imbalance = 100%
            
            # Combine factors for overall confidence
            confidence_score = (depth_factor * 0.6) + (imbalance_factor * 0.4)
            confidence_pct = int(confidence_score * 100)
            
            return f"{confidence_pct}%"
            
        except Exception as e:
            logger.warning(f"Pressure confidence calculation failed: {e}")
            return "50%"
    
    def _determine_pressure_trend(self, pressure_imbalance: float, depth_concentration: float) -> str:
        """Determine pressure trend based on orderbook characteristics"""
        try:
            abs_imbalance = abs(pressure_imbalance)
            
            if abs_imbalance > 0.2 and depth_concentration > 0.75:
                return "BUILDING"  # Pressure building with concentration
            elif abs_imbalance > 0.15:
                return "INCREASING"  # Pressure increasing
            elif abs_imbalance < 0.05:
                return "BALANCED"  # Very balanced orderbook
            else:
                return "NEUTRAL"  # Normal pressure levels
                
        except Exception as e:
            logger.warning(f"Pressure trend determination failed: {e}")
            return "NEUTRAL"
    
    def _get_default_pressure(self) -> Dict[str, Any]:
        """Get default pressure data when calculation fails"""
        return {
            "direction": "NEUTRAL",
            "confidence": "0%",
            "strength": 0.0,
            "trend": "UNKNOWN",
            "bid_pressure_ratio": 0.5,
            "ask_pressure_ratio": 0.5,
            "pressure_imbalance": 0.0,
            "depth_concentration": 0.0,
            "bid_depth_5": 0.0,
            "ask_depth_5": 0.0,
            "total_depth_5": 0.0,
            "data_source": "default_fallback"
        }