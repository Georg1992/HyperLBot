#!/usr/bin/env python3
"""
Volume Calculator Module
Centralized volume calculations and analysis for trading decisions
"""

from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
# from core.constants import MagicNumbers  # Removed unused import


class VolumeCalculator:
    """Centralized volume calculation and analysis system"""
    
    def __init__(self):
        logger.info("📊 Volume Calculator initialized")
    
    def calculate_relative_volume(self, current_volume: float, historical_volumes: List[float]) -> float:
        """Calculate relative volume (current vs historical average)"""
        try:
            if not historical_volumes or len(historical_volumes) < 5:
                return 1.0  # Default neutral relative volume
            
            historical_avg = sum(historical_volumes) / len(historical_volumes)
            if historical_avg == 0:
                return 1.0
                
            relative_volume = current_volume / historical_avg
            return round(relative_volume, 3)
            
        except Exception as e:
            logger.warning(f"Relative volume calculation failed: {e}")
            return 1.0
    
    def calculate_volume_momentum(self, volumes: List[float]) -> Dict[str, Any]:
        """Calculate volume momentum and acceleration"""
        try:
            if len(volumes) < 6:
                return {
                    "momentum": 0.0,
                    "acceleration": 0.0,
                    "trend": "UNKNOWN"
                }
            
            # Recent vs older volume comparison
            recent_volumes = volumes[-3:]  # Last 3 periods
            older_volumes = volumes[-6:-3]  # Previous 3 periods
            
            recent_avg = sum(recent_volumes) / len(recent_volumes)
            older_avg = sum(older_volumes) / len(older_volumes)
            
            # Calculate momentum (rate of change)
            if older_avg > 0:
                momentum = (recent_avg - older_avg) / older_avg
            else:
                momentum = 0.0
            
            # Calculate acceleration (change in momentum)
            if len(volumes) >= 9:
                earlier_volumes = volumes[-9:-6]
                earlier_avg = sum(earlier_volumes) / len(earlier_volumes)
                
                if earlier_avg > 0:
                    previous_momentum = (older_avg - earlier_avg) / earlier_avg
                    acceleration = momentum - previous_momentum
                else:
                    acceleration = 0.0
            else:
                acceleration = 0.0
            
            # Determine trend
            if momentum > 0.15:  # 15% increase
                trend = "ACCELERATING"
            elif momentum > 0.05:  # 5% increase
                trend = "INCREASING"
            elif momentum < -0.15:  # 15% decrease
                trend = "DECLINING"
            elif momentum < -0.05:  # 5% decrease
                trend = "DECREASING"
            else:
                trend = "STABLE"
            
            return {
                "momentum": round(momentum, 4),
                "acceleration": round(acceleration, 4),
                "trend": trend
            }
            
        except Exception as e:
            logger.warning(f"Volume momentum calculation failed: {e}")
            return {
                "momentum": 0.0,
                "acceleration": 0.0,
                "trend": "ERROR"
            }
    
    
    # Old volume smoothing method removed - using CoinGecko volume data instead
    
    # Old relative volume analysis method removed - using CoinGecko volume data instead
    
    def detect_volume_spike_from_binance(self, current_volume_btc: float, historical_volumes: List[float]) -> Dict[str, Any]:
        """
        Detect volume spikes using Binance real-time volume data
        
        Args:
            current_volume_btc: Current volume in BTC from Binance WebSocket
            historical_volumes: List of recent volumes for comparison
        
        Returns:
            Dict with volume spike analysis
        """
        try:
            if not historical_volumes or len(historical_volumes) < 5:
                # Use realistic Bitcoin volume thresholds for real-time trading (per minute)
                if current_volume_btc >= 100:  # 100+ BTC per minute (EXTREMELY high - major market event)
                    volume_category = "EXTREMELY_HIGH"
                elif current_volume_btc >= 50:  # 50+ BTC per minute (massive spike)
                    volume_category = "VERY_HIGH"
                elif current_volume_btc >= 20:  # 20+ BTC per minute (high activity)
                    volume_category = "HIGH"
                elif current_volume_btc >= 10:  # 10+ BTC per minute (above average)
                    volume_category = "ABOVE_AVERAGE"
                elif current_volume_btc >= 5:  # 5+ BTC per minute (normal)
                    volume_category = "NORMAL"
                elif current_volume_btc >= 2:  # 2+ BTC per minute (low)
                    volume_category = "LOW"
                else:  # <2 BTC per minute (very low)
                    volume_category = "VERY_LOW"
                
                return {
                    "volume_spike_detected": False,
                    "volume_ratio": 1.0,
                    "volume_category": volume_category,
                    "current_volume_btc": current_volume_btc,
                    "average_volume_btc": current_volume_btc,
                    "data_source": "binance_estimated"
                }
            
            # Calculate average volume from historical data
            avg_volume = sum(historical_volumes) / len(historical_volumes)
            volume_ratio = current_volume_btc / avg_volume if avg_volume > 0 else 1.0
            
            # Detect volume spikes based on ratio
            if volume_ratio >= 3.0:  # 3x+ normal volume
                volume_category = "EXTREMELY_HIGH"
                volume_spike_detected = True
            elif volume_ratio >= 2.0:  # 2x+ normal volume
                volume_category = "VERY_HIGH"
                volume_spike_detected = True
            elif volume_ratio >= 1.5:  # 1.5x+ normal volume
                volume_category = "HIGH"
                volume_spike_detected = True
            elif volume_ratio >= 0.8:  # 0.8x+ normal volume
                volume_category = "NORMAL"
                volume_spike_detected = False
            elif volume_ratio >= 0.5:  # 0.5x+ normal volume
                volume_category = "BELOW_AVERAGE"
                volume_spike_detected = False
            else:  # < 0.5x normal volume
                volume_category = "LOW"
                volume_spike_detected = False
            
            return {
                "volume_spike_detected": volume_spike_detected,
                "volume_ratio": round(volume_ratio, 2),
                "volume_category": volume_category,
                "current_volume_btc": current_volume_btc,
                "average_volume_btc": round(avg_volume, 2),
                "data_source": "binance"
            }
            
        except Exception as e:
            logger.warning(f"Volume spike detection failed: {e}")
            return {
                "volume_spike_detected": False,
                "volume_ratio": 1.0,
                "volume_category": "ERROR",
                "current_volume_btc": current_volume_btc,
                "average_volume_btc": 0,
                "data_source": "error"
            }
    
    # Old volume spike detection method removed - using Binance real-time volume spike detection instead
    
    # Old Yahoo volume categorization removed - using Binance real-time volume data instead
