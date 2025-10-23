#!/usr/bin/env python3
"""
Pressure Calculator Module
Centralized market pressure calculations from orderbook data
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from core.constants import MagicNumbers

# Singleton pattern implementation
_global_pressure_calculator = None

def get_global_pressure_calculator() -> 'PressureCalculator':
    """Get the global PressureCalculator singleton instance"""
    global _global_pressure_calculator
    if _global_pressure_calculator is None:
        _global_pressure_calculator = PressureCalculator()
    return _global_pressure_calculator

class PressureCalculator:
    """Centralized market pressure calculation system"""
    
    def __init__(self):
        logger.info("📊 Pressure Calculator initialized")
    
    def calculate_orderbook_pressure(self, bids: List[Dict], asks: List[Dict]) -> Dict[str, Any]:
        """Calculate market pressure from orderbook data"""
        try:
            if not bids or not asks:
                logger.error("❌ No orderbook data available for pressure calculation")
                raise Exception("No orderbook data available")
            
            # Calculate depth metrics
            bid_depth_5 = sum(float(level.get('sz', 0)) for level in bids[:5])
            ask_depth_5 = sum(float(level.get('sz', 0)) for level in asks[:5])
            bid_depth_10 = sum(float(level.get('sz', 0)) for level in bids[:10])
            ask_depth_10 = sum(float(level.get('sz', 0)) for level in asks[:10])
            
            total_depth_5 = bid_depth_5 + ask_depth_5
            total_depth_10 = bid_depth_10 + ask_depth_10
            
            if total_depth_5 == 0:
                logger.error("❌ No orderbook depth available for pressure calculation")
                raise Exception("No orderbook depth available")
            
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
            raise Exception(f"Orderbook pressure calculation failed: {e}")
    
    def _categorize_pressure_direction(self, pressure_imbalance: float, depth_concentration: float) -> Tuple[str, float]:
        """Categorize pressure direction and strength"""
        try:
            # Determine direction based on imbalance (using constants)
            abs_imbalance = abs(pressure_imbalance)
            
            if pressure_imbalance > MagicNumbers.PRESSURE_STRONG_THRESHOLD:  # Strong bid pressure
                direction = "STRONG_BUY"
                strength = min(MagicNumbers.PRESSURE_MAX_STRENGTH, MagicNumbers.DEFAULT_STRENGTH + abs_imbalance)
            elif pressure_imbalance > MagicNumbers.PRESSURE_MODERATE_THRESHOLD:  # Moderate bid pressure
                direction = "BUY"
                strength = MagicNumbers.DEFAULT_STRENGTH + (abs_imbalance * 2)
            elif pressure_imbalance < -MagicNumbers.PRESSURE_STRONG_THRESHOLD:  # Strong ask pressure
                direction = "STRONG_SELL"
                strength = min(MagicNumbers.PRESSURE_MAX_STRENGTH, MagicNumbers.DEFAULT_STRENGTH + abs_imbalance)
            elif pressure_imbalance < -MagicNumbers.PRESSURE_MODERATE_THRESHOLD:  # Moderate ask pressure
                direction = "SELL"
                strength = MagicNumbers.DEFAULT_STRENGTH + (abs_imbalance * 2)
            else:  # Balanced pressure
                direction = "NEUTRAL"
                strength = MagicNumbers.DEFAULT_STRENGTH - (abs_imbalance * 2)
            
            # Adjust strength based on depth concentration (using constants)
            if depth_concentration > MagicNumbers.PRESSURE_HIGH_CONCENTRATION:  # High concentration = stronger signal
                strength = min(MagicNumbers.PRESSURE_MAX_STRENGTH, strength * 1.2)
            elif depth_concentration < MagicNumbers.PRESSURE_LOW_CONCENTRATION:  # Low concentration = weaker signal
                strength = max(MagicNumbers.PRESSURE_MIN_STRENGTH, strength * 0.8)
            
            return direction, round(strength, 3)
            
        except Exception as e:
            logger.warning(f"Pressure direction categorization failed: {e}")
            return "NEUTRAL", MagicNumbers.DEFAULT_STRENGTH
    
    def _calculate_pressure_confidence(self, total_depth: float, pressure_imbalance: float) -> float:
        """Calculate confidence score for pressure reading (0.0 to 1.0)"""
        try:
            # Base confidence on depth and imbalance strength (using constants)
            depth_factor = min(1.0, total_depth / MagicNumbers.PRESSURE_DEPTH_REFERENCE)  # Reference depth = 100% confidence
            imbalance_factor = min(1.0, abs(pressure_imbalance) * (1 / MagicNumbers.PRESSURE_STRONG_THRESHOLD))  # Strong threshold = 100%
            
            # Combine factors for overall confidence (60% depth weight, 40% imbalance weight)
            confidence_score = (depth_factor * 0.6) + (imbalance_factor * 0.4)
            
            return round(confidence_score, 3)
            
        except Exception as e:
            logger.warning(f"Pressure confidence calculation failed: {e}")
            return 0.0  # Return 0.0 for errors
    
    def _determine_pressure_trend(self, pressure_imbalance: float, depth_concentration: float) -> str:
        """Determine pressure trend based on orderbook characteristics"""
        try:
            abs_imbalance = abs(pressure_imbalance)
            
            # Use constants for thresholds
            building_imbalance_threshold = MagicNumbers.PRESSURE_STRONG_THRESHOLD * 0.8  # 80% of strong threshold
            increasing_imbalance_threshold = MagicNumbers.PRESSURE_MODERATE_THRESHOLD * 1.5  # 150% of moderate threshold
            balanced_imbalance_threshold = MagicNumbers.PRESSURE_MODERATE_THRESHOLD * 0.5  # 50% of moderate threshold
            
            if abs_imbalance > building_imbalance_threshold and depth_concentration > (MagicNumbers.PRESSURE_HIGH_CONCENTRATION * 0.95):
                return "BUILDING"  # Pressure building with concentration
            elif abs_imbalance > increasing_imbalance_threshold:
                return "INCREASING"  # Pressure increasing
            elif abs_imbalance < balanced_imbalance_threshold:
                return "BALANCED"  # Very balanced orderbook
            else:
                return "NEUTRAL"  # Normal pressure levels
                
        except Exception as e:
            logger.warning(f"Pressure trend determination failed: {e}")
            return "NEUTRAL"
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        """
        Get latest pressure analysis for MarketDataService coordination
        
        Returns:
            Dict with pressure analysis using real orderbook data
        """
        try:
            # Get real orderbook data from MarketDataService
            from core.services.system_initializer import get_system_initializer
            system_initializer = get_system_initializer()
            market_data_service = system_initializer.singleton_systems.get('market_data_service')
            
            if not market_data_service:
                logger.error("❌ MarketDataService not available for pressure analysis")
                return {
                    "direction": "N/A",
                    "confidence": 0.0,
                    "strength": "N/A", 
                    "trend": "N/A",
                    "timestamp": time.time(),
                    "data_type": "pressure",
                    "status": "NO_SERVICE"
                }
            
            # Get orderbook data
            orderbook_data = market_data_service.get_orderbook_analysis()
            if not orderbook_data or orderbook_data.get('error'):
                logger.warning("⚠️ No orderbook data available for pressure analysis")
                return {
                    "direction": "N/A",
                    "confidence": 0.0,
                    "strength": "N/A", 
                    "trend": "N/A",
                    "timestamp": time.time(),
                    "data_type": "pressure",
                    "status": "NO_ORDERBOOK_DATA"
                }
            
            # Calculate pressure from real orderbook data
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            
            if not bids or not asks:
                logger.warning("⚠️ Empty orderbook data for pressure analysis")
                return {
                    "direction": "N/A",
                    "confidence": 0.0,
                    "strength": "N/A", 
                    "trend": "N/A",
                    "timestamp": time.time(),
                    "data_type": "pressure",
                    "status": "EMPTY_ORDERBOOK"
                }
            
            # Calculate real pressure analysis
            pressure_result = self.calculate_orderbook_pressure(bids, asks)
            return pressure_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest pressure analysis: {e}")
            return {
                "direction": "N/A",
                "confidence": 0.0,
                "strength": "N/A",
                "trend": "N/A", 
                "timestamp": time.time(),
                "data_type": "pressure",
                "status": "ERROR",
                "error": str(e)
            }
    
