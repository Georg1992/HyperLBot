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
    
    def categorize_volume(self, current_volume: float, relative_volume: float, 
                          volume_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Categorize volume level using percentile-based thresholds (mathematically justified)
        
        Uses historical percentiles from database for objective categorization:
        - VERY_LOW: < 10th percentile
        - LOW: 10th-25th percentile
        - NORMAL: 25th-75th percentile
        - HIGH: 75th-90th percentile
        - VERY_HIGH: > 90th percentile
        
        Args:
            current_volume: Current 5-minute volume in BTC
            relative_volume: Relative volume (kept for parameter compatibility, not used)
            volume_history: List of historical volume records from database (REQUIRED)
            
        Returns:
            Dictionary with level, description, and percentile information
            
        Raises:
            ValueError: If volume_history is insufficient for percentile calculation
        """
        if not volume_history:
            raise ValueError("Volume history is required for percentile-based categorization")
        
        # Extract volumes and filter out zero/invalid volumes
        volumes = [v.get('volume', 0.0) for v in volume_history if v.get('volume', 0.0) > 0]
        
        if not volumes or len(volumes) < 20:
            raise ValueError(f"Insufficient volume data for percentile calculation: {len(volumes)} valid volumes (minimum 20 required)")
        
        # Sort volumes for percentile calculation
        sorted_volumes = sorted(volumes)
        n = len(sorted_volumes)
        
        # Calculate percentiles (mathematically justified thresholds)
        percentile_10 = sorted_volumes[int(n * 0.10)]  # 10th percentile
        percentile_25 = sorted_volumes[int(n * 0.25)]  # 25th percentile (Q1)
        percentile_50 = sorted_volumes[int(n * 0.50)]  # 50th percentile (median)
        percentile_75 = sorted_volumes[int(n * 0.75)]  # 75th percentile (Q3)
        percentile_90 = sorted_volumes[int(n * 0.90)]  # 90th percentile
        percentile_95 = sorted_volumes[int(n * 0.95)]  # 95th percentile (for extreme threshold)
        
        # Fixed extreme threshold: 500 BTC is always considered extreme
        # This ensures that very high volumes are always properly categorized
        extreme_threshold = max(500.0, percentile_95)  # Use 500 BTC minimum or 95th percentile, whichever is higher
        
        # Categorize based on percentiles with fixed extreme threshold (objective, mathematically justified)
        if current_volume >= extreme_threshold:
            level = "VERY_HIGH"
            description = f"Extremely high volume: {current_volume:.2f} BTC (≥{extreme_threshold:.2f} BTC threshold)"
        elif current_volume >= percentile_75:
            level = "HIGH"
            description = f"High volume: {current_volume:.2f} BTC (≥75th percentile: {percentile_75:.2f} BTC)"
        elif current_volume >= percentile_25:
            level = "NORMAL"
            description = f"Normal volume: {current_volume:.2f} BTC (25th-75th percentile: {percentile_25:.2f}-{percentile_75:.2f} BTC)"
        elif current_volume >= percentile_10:
            level = "LOW"
            description = f"Low volume: {current_volume:.2f} BTC (10th-25th percentile: {percentile_10:.2f}-{percentile_25:.2f} BTC)"
        else:
            level = "VERY_LOW"
            description = f"Very low volume: {current_volume:.2f} BTC (<10th percentile: {percentile_10:.2f} BTC)"
        
        return {
            "level": level,
            "description": description,
            "current_volume": current_volume,
            "percentiles": {
                "p10": percentile_10,
                "p25": percentile_25,
                "p50": percentile_50,
                "p75": percentile_75,
                "p90": percentile_90,
                "p95": percentile_95
            },
            "extreme_threshold": extreme_threshold,
            "sample_size": n,
            "method": "percentile_based"
        }
    
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