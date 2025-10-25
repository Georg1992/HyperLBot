#!/usr/bin/env python3
"""
Volume Analyzer - Clean implementation
Handles volume analysis calculations
"""

import time
from typing import Dict, List, Any
from loguru import logger


class VolumeAnalyzer:
    """Analyzer for volume calculations"""
    
    def __init__(self):
        logger.debug("VolumeAnalyzer initialized")
    
    def calculate_volume_momentum(self, volume_history: List[Dict]) -> Dict[str, Any]:
        """Calculate volume momentum"""
        try:
            if len(volume_history) < 2:
                return {"momentum": 0.0, "trend": "UNKNOWN"}
            
            # Simple momentum calculation
            recent_avg = sum(v.get('volume', 0) for v in volume_history[-3:]) / 3
            older_avg = sum(v.get('volume', 0) for v in volume_history[-6:-3]) / 3
            
            momentum = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0.0
            
            trend = "INCREASING" if momentum > 0.1 else "DECREASING" if momentum < -0.1 else "STABLE"
            
            return {
                "momentum": momentum,
                "trend": trend
            }
        except Exception as e:
            logger.error(f"❌ Failed to calculate volume momentum: {e}")
            return {"momentum": 0.0, "trend": "UNKNOWN"}
    
    def calculate_volume_trend_strength(self, volume_history: List[Dict]) -> float:
        """Calculate volume trend strength"""
        try:
            if len(volume_history) < 3:
                return 0.0
            
            # Simple trend strength calculation
            volumes = [v.get('volume', 0) for v in volume_history[-5:]]
            if not volumes:
                return 0.0
            
            # Calculate variance as trend strength indicator
            mean_vol = sum(volumes) / len(volumes)
            variance = sum((v - mean_vol) ** 2 for v in volumes) / len(volumes)
            
            return min(variance / (mean_vol ** 2) if mean_vol > 0 else 0.0, 1.0)
        except Exception as e:
            logger.error(f"❌ Failed to calculate volume trend strength: {e}")
            return 0.0
    
    def calculate_relative_volume(self, current_volume: float, volume_history: List[Dict]) -> float:
        """Calculate relative volume"""
        try:
            if not volume_history:
                return 1.0
            
            # Calculate average volume from history
            avg_volume = sum(v.get('volume', 0) for v in volume_history) / len(volume_history)
            
            if avg_volume == 0:
                return 1.0
            
            return current_volume / avg_volume
        except Exception as e:
            logger.error(f"❌ Failed to calculate relative volume: {e}")
            return 1.0
    
    def detect_volume_anomalies(self, current_volume: float, volume_history: List[Dict]) -> Dict[str, Any]:
        """Detect volume anomalies"""
        try:
            if not volume_history:
                return {"is_anomaly": False, "severity": "NORMAL"}
            
            # Calculate average and standard deviation
            volumes = [v.get('volume', 0) for v in volume_history]
            avg_volume = sum(volumes) / len(volumes)
            variance = sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)
            std_dev = variance ** 0.5
            
            # Check if current volume is anomaly
            if std_dev == 0:
                return {"is_anomaly": False, "severity": "NORMAL"}
            
            z_score = abs(current_volume - avg_volume) / std_dev
            
            if z_score > 3:
                return {"is_anomaly": True, "severity": "HIGH"}
            elif z_score > 2:
                return {"is_anomaly": True, "severity": "MEDIUM"}
            else:
                return {"is_anomaly": False, "severity": "NORMAL"}
        except Exception as e:
            logger.error(f"❌ Failed to detect volume anomalies: {e}")
            return {"is_anomaly": False, "severity": "NORMAL"}