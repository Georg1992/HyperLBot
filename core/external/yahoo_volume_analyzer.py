#!/usr/bin/env python3
"""
Yahoo Finance Volume Analyzer
Handles volume analysis, spike detection, and volume categorization
"""

import time
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
from core.constants import volume_constants, time_constants

class YahooVolumeAnalyzer:
    """Volume analysis and spike detection for Yahoo Finance data"""
    
    def __init__(self):
        logger.info("📊 Yahoo Volume Analyzer initialized")
    
    def analyze_volume_data(self, candles: List[Dict], symbol: str = "BTC") -> Dict[str, Any]:
        """Analyze volume data from candles"""
        try:
            if not candles or len(candles) < 5:
                return {
                    "current_volume": 0,
                    "volume_category": volume_constants.VOLUME_CATEGORY_UNKNOWN,
                    "avg_volume": 0,
                    "volume_trend": "UNKNOWN",
                    "error": "insufficient_data",
                    "data_source": "yahoo_finance"
                }
            
            # Extract volume data
            volumes = [candle["volume"] for candle in candles if candle.get("volume", 0) > 0]
            if not volumes:
                return {
                    "current_volume": 0,
                    "volume_category": volume_constants.VOLUME_CATEGORY_UNKNOWN,
                    "avg_volume": 0,
                    "volume_trend": "UNKNOWN",
                    "error": "no_volume_data",
                    "data_source": "yahoo_finance"
                }
            
            # Calculate current volume (most recent)
            current_volume = volumes[-1] if volumes else 0
            
            # Calculate average volume
            recent_volumes = volumes[-5:]  # Last 5 candles
            avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
            
            # Use actual Yahoo volume (no scaling to match Hyperliquid)
            current_volume = current_volume
            avg_volume = avg_volume
            
            # Categorize volume based on actual Yahoo Finance ranges (more realistic for BTC)
            volume_category = self._categorize_volume(current_volume)
            
            # Determine volume trend
            volume_trend = self._calculate_volume_trend(volumes)
            
            return {
                "current_volume": current_volume,
                "volume_category": volume_category,
                "avg_volume": avg_volume,
                "volume_trend": volume_trend,
                "recent_volumes": recent_volumes,
                "data_source": "yahoo_finance",
                # Add basic spike detection fields for dashboard compatibility
                "has_spike": False,
                "spike_severity": "NORMAL",
                "is_immediate_spike": False,
                "spike_reason": "",
                "volume_source": "yahoo_finance_basic"
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze volume data: {e}")
            return {
                "current_volume": 0,
                "volume_category": "ERROR",
                "avg_volume": 0,
                "volume_trend": "ERROR",
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    
    def _categorize_volume(self, current_volume: float) -> str:
        """Categorize volume using standardized thresholds and consistent naming"""
        if current_volume >= volume_constants.TRADING_VOLUME_EXTREMELY_HIGH:
            return volume_constants.VOLUME_CATEGORY_EXTREMELY_HIGH
        elif current_volume >= volume_constants.TRADING_VOLUME_VERY_HIGH:
            return volume_constants.VOLUME_CATEGORY_VERY_HIGH
        elif current_volume >= volume_constants.TRADING_VOLUME_HIGH:
            return volume_constants.VOLUME_CATEGORY_HIGH
        elif current_volume >= volume_constants.TRADING_VOLUME_ABOVE_AVERAGE:
            return volume_constants.VOLUME_CATEGORY_ABOVE_AVERAGE
        elif current_volume >= volume_constants.TRADING_VOLUME_NORMAL:
            return volume_constants.VOLUME_CATEGORY_NORMAL
        elif current_volume >= volume_constants.TRADING_VOLUME_BELOW_AVERAGE:
            return volume_constants.VOLUME_CATEGORY_BELOW_AVERAGE
        elif current_volume >= volume_constants.TRADING_VOLUME_LOW:
            return volume_constants.VOLUME_CATEGORY_LOW
        elif current_volume >= volume_constants.TRADING_VOLUME_VERY_LOW:
            return volume_constants.VOLUME_CATEGORY_VERY_LOW
        else:
            return volume_constants.VOLUME_CATEGORY_EXTREMELY_LOW
    
    def _calculate_volume_trend(self, volumes: List[float]) -> str:
        """Calculate volume trend over time"""
        if len(volumes) < 3:
            return "UNKNOWN"
        
        recent_avg = sum(volumes[-3:]) / 3
        older_avg = sum(volumes[-6:-3]) / 3 if len(volumes) >= 6 else recent_avg
        
        if recent_avg > older_avg * 1.1:
            return "INCREASING"
        elif recent_avg < older_avg * 0.9:
            return "DECREASING"
        else:
            return "STABLE"
    
    def detect_volume_spike(self, candles_1m: List[Dict], candles_5m: List[Dict]) -> Dict[str, Any]:
        """Detect volume spikes in real-time"""
        try:
            if not candles_1m or not candles_5m:
                return {
                    "has_spike": False,
                    "spike_severity": "NORMAL",
                    "is_immediate_spike": False,
                    "spike_reason": "",
                    "estimated_current_volume": 0,
                    "recent_avg_volume": 0
                }
            
            # Get current time
            now = datetime.now()
            current_minute = now.minute
            
            # Find current 5-minute period
            period_start = now.replace(second=0, microsecond=0)
            period_start = period_start.replace(minute=(current_minute // 5) * 5)
            
            # Get candles for current 5-minute period
            period_candles = []
            for candle in candles_1m:
                candle_time = datetime.fromtimestamp(candle["open_time"] / time_constants.MILLISECONDS_IN_SECOND)
                if candle_time >= period_start:
                    period_candles.append(candle)
            
            # Calculate current period volume
            period_volume = sum(c["volume"] for c in period_candles if c.get("volume", 0) > 0)
            
            # Get current minute's volume (if available)
            current_minute_candles = [c for c in period_candles 
                                    if datetime.fromtimestamp(c["open_time"] / time_constants.MILLISECONDS_IN_SECOND).minute == current_minute]
            if current_minute_candles:
                current_minute_volume = current_minute_candles[0]["volume"]
            else:
                current_minute_volume = 0
            
            # Calculate time progress in current 5-minute period
            time_elapsed = (now - period_start).total_seconds()
            period_progress = min(time_elapsed / time_constants.SECONDS_IN_MINUTE * 5, 1.0)  # 5 minutes
            
            # Real-time volume estimation for immediate spike detection
            if period_progress > 0:
                estimated_current_volume = period_volume / period_progress
            else:
                estimated_current_volume = period_volume
            
            # Compare against recent average
            recent_avg = sum([c["volume"] for c in candles_1m[-20:] if c["volume"] > 0]) / 20
            if recent_avg > 0 and estimated_current_volume > recent_avg * volume_constants.VOLUME_SURGE_MULTIPLIER:  # 300% of average
                is_immediate_spike = True
                spike_reason = f"VOLUME SPIKE: {estimated_current_volume:.0f} vs avg {recent_avg:.0f}"
                spike_severity = "HIGH"
            else:
                is_immediate_spike = False
                spike_reason = ""
                spike_severity = "NORMAL"
            
            return {
                "has_spike": is_immediate_spike,
                "spike_severity": spike_severity,
                "is_immediate_spike": is_immediate_spike,
                "spike_reason": spike_reason,
                "estimated_current_volume": estimated_current_volume,
                "recent_avg_volume": recent_avg,
                "period_volume": period_volume,
                "current_minute_volume": current_minute_volume,
                "period_progress": period_progress
            }
            
        except Exception as e:
            logger.error(f"Failed to detect volume spike: {e}")
            return {
                "has_spike": False,
                "spike_severity": "ERROR",
                "is_immediate_spike": False,
                "spike_reason": f"Error: {str(e)}",
                "estimated_current_volume": 0,
                "recent_avg_volume": 0
            }

# Global instance
volume_analyzer = YahooVolumeAnalyzer()
