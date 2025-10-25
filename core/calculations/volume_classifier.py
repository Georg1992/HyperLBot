#!/usr/bin/env python3
"""
Volume Classifier - Clean implementation
Handles volume classification and recommendations
"""

import time
from typing import Dict, List, Any
from loguru import logger


class VolumeClassifier:
    """Classifier for volume analysis"""
    
    def __init__(self):
        logger.debug("VolumeClassifier initialized")
    
    def categorize_volume(self, current_volume: float, relative_volume: float) -> Dict[str, Any]:
        """Categorize volume level"""
        try:
            if relative_volume > 2.0:
                level = "VERY_HIGH"
                description = "Extremely high volume detected"
            elif relative_volume > 1.5:
                level = "HIGH"
                description = "High volume detected"
            elif relative_volume > 0.8:
                level = "NORMAL"
                description = "Normal volume levels"
            elif relative_volume > 0.5:
                level = "LOW"
                description = "Low volume detected"
            else:
                level = "VERY_LOW"
                description = "Very low volume detected"
            
            return {
                "level": level,
                "description": description,
                "relative_volume": relative_volume
            }
        except Exception as e:
            logger.error(f"❌ Failed to categorize volume: {e}")
            return {"level": "UNKNOWN", "description": "Volume analysis failed"}
    
    def determine_volume_implications(self, level: str, momentum: Dict, anomaly: Dict) -> Dict[str, Any]:
        """Determine volume implications"""
        try:
            implications = []
            
            if level == "VERY_HIGH":
                implications.extend(["High volatility expected", "Strong price movement likely"])
            elif level == "HIGH":
                implications.extend(["Increased volatility", "Moderate price movement"])
            elif level == "LOW":
                implications.extend(["Reduced volatility", "Limited price movement"])
            elif level == "VERY_LOW":
                implications.extend(["Very low volatility", "Minimal price movement"])
            
            if momentum.get("trend") == "INCREASING":
                implications.append("Volume momentum building")
            elif momentum.get("trend") == "DECREASING":
                implications.append("Volume momentum declining")
            
            if anomaly.get("is_anomaly"):
                implications.append(f"Volume anomaly detected: {anomaly.get('severity', 'UNKNOWN')}")
            
            return {
                "implications": implications,
                "trading_suitable": level in ["NORMAL", "HIGH", "VERY_HIGH"],
                "risk_level": "HIGH" if level == "VERY_HIGH" else "MEDIUM" if level == "HIGH" else "LOW"
            }
        except Exception as e:
            logger.error(f"❌ Failed to determine volume implications: {e}")
            return {"implications": ["Analysis failed"], "trading_suitable": False, "risk_level": "UNKNOWN"}
    
    def get_volume_recommendations(self, level: str, momentum: Dict, anomaly: Dict) -> List[str]:
        """Get volume-based recommendations"""
        try:
            recommendations = []
            
            if level == "VERY_HIGH":
                recommendations.extend(["Consider position sizing", "Monitor for volatility spikes"])
            elif level == "HIGH":
                recommendations.extend(["Good trading conditions", "Watch for trend continuation"])
            elif level == "NORMAL":
                recommendations.extend(["Standard trading conditions", "Monitor for volume changes"])
            elif level == "LOW":
                recommendations.extend(["Reduced position sizes", "Wait for volume confirmation"])
            elif level == "VERY_LOW":
                recommendations.extend(["Avoid trading", "Wait for volume increase"])
            
            if momentum.get("trend") == "INCREASING":
                recommendations.append("Volume momentum building - consider entries")
            elif momentum.get("trend") == "DECREASING":
                recommendations.append("Volume momentum declining - consider exits")
            
            if anomaly.get("is_anomaly"):
                recommendations.append("Volume anomaly detected - use caution")
            
            return recommendations
        except Exception as e:
            logger.error(f"❌ Failed to get volume recommendations: {e}")
            return ["Volume analysis failed - use caution"]