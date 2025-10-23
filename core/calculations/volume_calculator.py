#!/usr/bin/env python3
"""
Volume Calculator Module
Centralized volume calculations and analysis for trading decisions
"""

from typing import Dict, Any, List, Optional, Tuple
import time
from loguru import logger

# Singleton pattern implementation
_global_volume_calculator = None

def get_global_volume_calculator() -> 'VolumeCalculator':
    """Get the global VolumeCalculator singleton instance"""
    global _global_volume_calculator
    if _global_volume_calculator is None:
        _global_volume_calculator = VolumeCalculator()
    return _global_volume_calculator

class VolumeCalculator:
    """Centralized volume calculation and analysis system"""
    
    def __init__(self):
        logger.info("📊 Volume Calculator initialized")
    
    def calculate_hyperliquid_5m_volume(self, hyperliquid_websocket) -> Dict[str, Any]:
        """
        Calculate enhanced 5m volume from Hyperliquid WebSocket data with momentum and correlation analysis
        
        Args:
            hyperliquid_websocket: HyperliquidWebSocket instance
            
        Returns:
            Dict with enhanced 5m volume analysis
        """
        try:
            if not hyperliquid_websocket:
                raise ValueError("Hyperliquid WebSocket not available")
            
            # Get current 5m volume from Hyperliquid
            current_5m_volume = hyperliquid_websocket.get_current_5m_volume()
            
            # Get volume history for momentum analysis
            volume_history = self._get_volume_history()
            
            # Calculate volume momentum
            volume_momentum = self._calculate_volume_momentum(current_5m_volume, volume_history)
            
            # Calculate volume trend strength
            volume_trend_strength = self._calculate_volume_trend_strength(volume_history)
            
            # Calculate volume acceleration
            volume_acceleration = self._calculate_volume_acceleration(volume_history)
            
            # Enhanced categorization with momentum consideration
            volume_category = self._categorize_enhanced_volume(
                current_5m_volume, volume_momentum, volume_trend_strength
            )
            
            return {
                "current_5m_volume": current_5m_volume,
                "volume_category": volume_category,
                "volume_momentum": volume_momentum,
                "volume_trend_strength": volume_trend_strength,
                "volume_acceleration": volume_acceleration,
                "data_source": "hyperliquid_5m",
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate Hyperliquid 5m volume: {e}")
            raise ValueError(f"Hyperliquid 5m volume calculation failed: {e}")
    
    
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
    
    
    def detect_volume_spike_from_hyperliquid(self, current_volume_btc: float, historical_volumes: List[float]) -> Dict[str, Any]:
        """
        Detect volume spikes using Hyperliquid 5m volume data
        
        Args:
            current_volume_btc: Current volume in BTC from Hyperliquid 5m candles
            historical_volumes: List of recent volumes for comparison
        
        Returns:
            Dict with volume spike analysis
        """
        try:
            if not historical_volumes or len(historical_volumes) < 5:
                # Use updated Bitcoin volume thresholds for 5m candle trading volume
                if current_volume_btc >= 500:  # 500+ BTC per 5m candle (EXTREME - major market event)
                    volume_category = "EXTREME"
                elif current_volume_btc >= 150:  # 150+ BTC per 5m candle (very high activity)
                    volume_category = "VERY_HIGH"
                elif current_volume_btc >= 80:  # 80+ BTC per 5m candle (high activity)
                    volume_category = "HIGH"
                elif current_volume_btc >= 20:  # 20+ BTC per 5m candle (moderate activity)
                    volume_category = "MODERATE"
                elif current_volume_btc >= 10:  # 10+ BTC per 5m candle (low activity)
                    volume_category = "LOW"
                else:  # <10 BTC per 5m candle (very low activity)
                    volume_category = "VERY_LOW"
                
                return {
                    "volume_spike_detected": False,
                    "volume_ratio": 1.0,
                    "volume_category": volume_category,
                    "current_volume_btc": current_volume_btc,
                    "average_volume_btc": current_volume_btc,
                    "data_source": "hyperliquid_estimated"
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
    
    def get_latest_analysis(self, hyperliquid_websocket=None) -> Dict[str, Any]:
        """
        Get latest volume analysis for MarketDataService coordination
        
        Args:
            hyperliquid_websocket: HyperliquidWebSocket instance for 5m volume
            
        Returns:
            Dict with volume analysis
        """
        try:
            analysis = {
                "hyperliquid_5m": {},
                "timestamp": time.time()
            }
            
            # Get Hyperliquid 5m volume if available
            if hyperliquid_websocket:
                try:
                    analysis["hyperliquid_5m"] = self.calculate_hyperliquid_5m_volume(hyperliquid_websocket)
                except Exception as e:
                    logger.warning(f"Hyperliquid 5m volume calculation failed: {e}")
                    analysis["hyperliquid_5m"] = {"error": str(e)}
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest volume analysis: {e}")
            return {
                "hyperliquid_5m": {"error": str(e)},
                "timestamp": time.time()
            }
    
    def _get_volume_history(self) -> List[float]:
        """Get volume history for momentum analysis"""
        # This would be implemented to store and retrieve volume history
        # For now, return empty list - will be enhanced with proper storage
        return []
    
    def _calculate_volume_momentum(self, current_volume: float, volume_history: List[float]) -> float:
        """Calculate volume momentum (rate of change)"""
        try:
            if len(volume_history) < 2:
                return 0.0
            
            # Calculate momentum as rate of change
            recent_avg = sum(volume_history[-3:]) / min(3, len(volume_history))
            if recent_avg == 0:
                return 0.0
            
            momentum = (current_volume - recent_avg) / recent_avg
            return max(-1.0, min(1.0, momentum))  # Clamp between -1 and 1
            
        except Exception as e:
            logger.warning(f"Volume momentum calculation failed: {e}")
            return 0.0
    
    def _calculate_volume_trend_strength(self, volume_history: List[float]) -> float:
        """Calculate volume trend strength (consistency of direction)"""
        try:
            if len(volume_history) < 5:
                return 0.0
            
            # Calculate trend strength as consistency of direction
            increases = sum(1 for i in range(1, len(volume_history)) 
                           if volume_history[i] > volume_history[i-1])
            total_changes = len(volume_history) - 1
            
            if total_changes == 0:
                return 0.0
            
            # Return strength as deviation from 0.5 (random)
            strength = abs(increases / total_changes - 0.5) * 2
            return max(0.0, min(1.0, strength))
            
        except Exception as e:
            logger.warning(f"Volume trend strength calculation failed: {e}")
            return 0.0
    
    def _calculate_volume_acceleration(self, volume_history: List[float]) -> float:
        """Calculate volume acceleration (rate of momentum change)"""
        try:
            if len(volume_history) < 3:
                return 0.0
            
            # Calculate acceleration as second derivative
            recent_volumes = volume_history[-3:]
            if len(recent_volumes) < 3:
                return 0.0
            
            # Simple acceleration calculation
            first_diff = recent_volumes[1] - recent_volumes[0]
            second_diff = recent_volumes[2] - recent_volumes[1]
            acceleration = second_diff - first_diff
            
            # Normalize by average volume
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            if avg_volume == 0:
                return 0.0
            
            normalized_acceleration = acceleration / avg_volume
            return max(-1.0, min(1.0, normalized_acceleration))
            
        except Exception as e:
            logger.warning(f"Volume acceleration calculation failed: {e}")
            return 0.0
    
    def _categorize_enhanced_volume(self, current_volume: float, momentum: float, trend_strength: float) -> str:
        """Enhanced volume categorization considering momentum and trend"""
        try:
            # Base categorization
            if current_volume >= 400:
                base_category = "EXTREME"
            elif current_volume >= 150:
                base_category = "HIGH"
            elif current_volume >= 50:
                base_category = "MODERATE"
            elif current_volume >= 20:
                base_category = "LOW"
            else:
                base_category = "VERY_LOW"
            
            # Adjust based on momentum and trend
            if momentum > 0.3 and trend_strength > 0.6:  # Strong upward momentum
                if base_category == "MODERATE":
                    return "HIGH"
                elif base_category == "LOW":
                    return "MODERATE"
            elif momentum < -0.3 and trend_strength > 0.6:  # Strong downward momentum
                if base_category == "HIGH":
                    return "MODERATE"
                elif base_category == "MODERATE":
                    return "LOW"
            
            return base_category
            
        except Exception as e:
            logger.warning(f"Enhanced volume categorization failed: {e}")
            return "UNKNOWN"
