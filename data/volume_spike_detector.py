#!/usr/bin/env python3
"""
Real-time Volume Spike Detector
Detects unusual volume activity by analyzing 1-minute candles and comparing against historical patterns
"""

import time
import statistics
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.yahoo_data_fetcher import YahooDataFetcher

class VolumeSpikeDetector:
    """
    Detects real-time volume spikes by analyzing 1-minute candles
    and comparing against historical volume patterns
    """
    
    def __init__(self):
        self.yahoo_fetcher = YahooDataFetcher()
        self.volume_history = []  # Store recent volume data for baseline calculation
        self.spike_thresholds = {
            "mild_spike": 1.5,      # 50% above average
            "moderate_spike": 2.0,   # 100% above average (2x)
            "high_spike": 3.0,       # 200% above average (3x)
            "extreme_spike": 5.0     # 400% above average (5x)
        }
        self.baseline_periods = {
            "short_term": 10,    # 10 minutes for immediate spikes
            "medium_term": 30,   # 30 minutes for trend spikes
            "long_term": 60      # 1 hour for major spikes
        }
        
        logger.info("📊 Volume Spike Detector initialized")
    
    def get_volume_baseline(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Calculate volume baseline from historical 1-minute candles"""
        try:
            # Get 1-minute candles for baseline calculation (last 2 hours)
            candles_1m = self.yahoo_fetcher.get_1m_klines(symbol, 120)
            if not candles_1m or len(candles_1m) < 30:
                return {
                    "error": "Insufficient 1-minute data for baseline calculation",
                    "data_source": "yahoo_finance"
                }
            
            # Extract volumes and filter out zeros (incomplete candles)
            volumes = [c["volume"] for c in candles_1m if c["volume"] > 0]
            
            if len(volumes) < 10:
                return {
                    "error": "Insufficient valid volume data",
                    "data_source": "yahoo_finance"
                }
            
            # Calculate baseline statistics
            baseline = {
                "mean_volume": statistics.mean(volumes),
                "median_volume": statistics.median(volumes),
                "std_volume": statistics.stdev(volumes) if len(volumes) > 1 else 0,
                "min_volume": min(volumes),
                "max_volume": max(volumes),
                "volume_count": len(volumes),
                "data_source": "yahoo_finance_1m_baseline",
                "timestamp": time.time()
            }
            
            # Calculate percentiles for different spike levels
            sorted_volumes = sorted(volumes)
            baseline["p75_volume"] = sorted_volumes[int(len(sorted_volumes) * 0.75)]
            baseline["p90_volume"] = sorted_volumes[int(len(sorted_volumes) * 0.90)]
            baseline["p95_volume"] = sorted_volumes[int(len(sorted_volumes) * 0.95)]
            baseline["p99_volume"] = sorted_volumes[int(len(sorted_volumes) * 0.99)]
            
            return baseline
            
        except Exception as e:
            logger.error(f"Failed to calculate volume baseline: {e}")
            return {
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    
    def detect_current_volume_spike(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Detect if current volume represents a spike compared to baseline"""
        try:
            # Get current real-time volume
            realtime_volume = self.yahoo_fetcher.get_realtime_volume(symbol)
            if "error" in realtime_volume:
                return realtime_volume
            
            # Get volume baseline
            baseline = self.get_volume_baseline(symbol)
            if "error" in baseline:
                return baseline
            
            # Get current estimated volume
            current_volume = realtime_volume.get("estimated_current_volume", 0)
            period_progress = realtime_volume.get("period_progress", 0)
            
            # Normalize current volume to 1-minute equivalent for comparison
            if period_progress > 0:
                normalized_current_volume = current_volume / (period_progress / 100 * 5)  # Convert to 1-min equivalent
            else:
                normalized_current_volume = current_volume
            
            # Calculate spike ratios
            mean_volume = baseline["mean_volume"]
            median_volume = baseline["median_volume"]
            
            if mean_volume > 0:
                spike_ratio_mean = normalized_current_volume / mean_volume
            else:
                spike_ratio_mean = 0
                
            if median_volume > 0:
                spike_ratio_median = normalized_current_volume / median_volume
            else:
                spike_ratio_median = 0
            
            # Determine spike severity
            spike_severity = "NORMAL"
            spike_description = "Normal volume activity"
            
            if spike_ratio_mean >= self.spike_thresholds["extreme_spike"]:
                spike_severity = "EXTREME"
                spike_description = "Extreme volume spike detected!"
            elif spike_ratio_mean >= self.spike_thresholds["high_spike"]:
                spike_severity = "HIGH"
                spike_description = "High volume spike detected"
            elif spike_ratio_mean >= self.spike_thresholds["moderate_spike"]:
                spike_severity = "MODERATE"
                spike_description = "Moderate volume spike detected"
            elif spike_ratio_mean >= self.spike_thresholds["mild_spike"]:
                spike_severity = "MILD"
                spike_description = "Mild volume spike detected"
            
            # Check against percentile thresholds
            percentile_alerts = []
            if normalized_current_volume >= baseline["p99_volume"]:
                percentile_alerts.append("99th percentile")
            elif normalized_current_volume >= baseline["p95_volume"]:
                percentile_alerts.append("95th percentile")
            elif normalized_current_volume >= baseline["p90_volume"]:
                percentile_alerts.append("90th percentile")
            elif normalized_current_volume >= baseline["p75_volume"]:
                percentile_alerts.append("75th percentile")
            
            # Calculate volume acceleration (rate of change)
            volume_acceleration = 0
            if len(self.volume_history) >= 2:
                recent_volumes = self.volume_history[-5:]  # Last 5 data points
                if len(recent_volumes) >= 2:
                    volume_acceleration = (recent_volumes[-1] - recent_volumes[0]) / len(recent_volumes)
            
            # Update volume history
            self.volume_history.append(normalized_current_volume)
            if len(self.volume_history) > 20:  # Keep last 20 data points
                self.volume_history.pop(0)
            
            spike_analysis = {
                "timestamp": time.time(),
                "current_volume": current_volume,
                "normalized_current_volume": normalized_current_volume,
                "period_progress": period_progress,
                "spike_ratio_mean": spike_ratio_mean,
                "spike_ratio_median": spike_ratio_median,
                "spike_severity": spike_severity,
                "spike_description": spike_description,
                "percentile_alerts": percentile_alerts,
                "volume_acceleration": volume_acceleration,
                "baseline_mean": mean_volume,
                "baseline_median": median_volume,
                "baseline_std": baseline["std_volume"],
                "is_spike": spike_severity != "NORMAL",
                "data_source": "yahoo_finance_1m_spike_detection",
                "update_frequency": "5_seconds"
            }
            
            # Log significant spikes
            if spike_severity in ["HIGH", "EXTREME"]:
                logger.warning(f"🚨 {spike_severity} VOLUME SPIKE: {spike_ratio_mean:.1f}x average volume!")
                logger.warning(f"   Current: {normalized_current_volume:.0f}, Average: {mean_volume:.0f}")
            
            return spike_analysis
            
        except Exception as e:
            logger.error(f"Failed to detect volume spike: {e}")
            return {
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    
    def get_volume_trend_analysis(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Analyze volume trends over different time periods"""
        try:
            # Get 1-minute candles for trend analysis
            candles_1m = self.yahoo_fetcher.get_1m_klines(symbol, 120)
            if not candles_1m:
                return {
                    "error": "No 1-minute data available",
                    "data_source": "yahoo_finance"
                }
            
            # Filter out zero volumes (incomplete candles)
            valid_candles = [c for c in candles_1m if c["volume"] > 0]
            
            if len(valid_candles) < 10:
                return {
                    "error": "Insufficient valid volume data",
                    "data_source": "yahoo_finance"
                }
            
            # Analyze different time periods
            trend_analysis = {}
            
            for period_name, period_minutes in self.baseline_periods.items():
                if len(valid_candles) >= period_minutes:
                    period_candles = valid_candles[-period_minutes:]
                    period_volumes = [c["volume"] for c in period_candles]
                    
                    # Split into halves for trend comparison
                    first_half = period_volumes[:len(period_volumes)//2]
                    second_half = period_volumes[len(period_volumes)//2:]
                    
                    if first_half and second_half:
                        first_avg = statistics.mean(first_half)
                        second_avg = statistics.mean(second_half)
                        
                        if first_avg > 0:
                            trend_ratio = second_avg / first_avg
                        else:
                            trend_ratio = 1.0
                        
                        trend_analysis[period_name] = {
                            "period_minutes": period_minutes,
                            "first_half_avg": first_avg,
                            "second_half_avg": second_avg,
                            "trend_ratio": trend_ratio,
                            "trend_direction": "INCREASING" if trend_ratio > 1.1 else "DECREASING" if trend_ratio < 0.9 else "STABLE",
                            "trend_strength": abs(trend_ratio - 1.0)
                        }
            
            return {
                "timestamp": time.time(),
                "trend_analysis": trend_analysis,
                "total_valid_candles": len(valid_candles),
                "data_source": "yahoo_finance_1m_trend_analysis"
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze volume trends: {e}")
            return {
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    
    def get_comprehensive_volume_analysis(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get comprehensive volume analysis including spike detection and trends"""
        try:
            # Get real-time volume data
            realtime_volume = self.yahoo_fetcher.get_realtime_volume(symbol)
            
            # Get spike detection
            spike_analysis = self.detect_current_volume_spike(symbol)
            
            # Get trend analysis
            trend_analysis = self.get_volume_trend_analysis(symbol)
            
            # Combine all analyses
            comprehensive_analysis = {
                "timestamp": time.time(),
                "realtime_volume": realtime_volume,
                "spike_analysis": spike_analysis,
                "trend_analysis": trend_analysis,
                "summary": {
                    "has_spike": spike_analysis.get("is_spike", False) if "error" not in spike_analysis else False,
                    "spike_severity": spike_analysis.get("spike_severity", "UNKNOWN") if "error" not in spike_analysis else "UNKNOWN",
                    "volume_trend": trend_analysis.get("trend_analysis", {}).get("short_term", {}).get("trend_direction", "UNKNOWN") if "error" not in trend_analysis else "UNKNOWN",
                    "current_volume": realtime_volume.get("estimated_current_volume", 0) if "error" not in realtime_volume else 0,
                    "period_progress": realtime_volume.get("period_progress", 0) if "error" not in realtime_volume else 0
                },
                "data_source": "yahoo_finance_comprehensive_volume_analysis"
            }
            
            return comprehensive_analysis
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive volume analysis: {e}")
            return {
                "error": str(e),
                "data_source": "yahoo_finance"
            }


def main():
    """Test the volume spike detector"""
    logger.info("🔍 Testing Volume Spike Detector")
    logger.info("=" * 60)
    
    detector = VolumeSpikeDetector()
    
    # Test baseline calculation
    logger.info("📊 Testing volume baseline calculation...")
    baseline = detector.get_volume_baseline("BTC")
    
    if "error" not in baseline:
        logger.success("✅ Baseline calculation successful!")
        logger.info(f"Mean volume: {baseline['mean_volume']:.0f}")
        logger.info(f"Median volume: {baseline['median_volume']:.0f}")
        logger.info(f"95th percentile: {baseline['p95_volume']:.0f}")
    else:
        logger.error(f"❌ Baseline calculation failed: {baseline['error']}")
        return
    
    # Test spike detection
    logger.info("🚨 Testing volume spike detection...")
    spike_analysis = detector.detect_current_volume_spike("BTC")
    
    if "error" not in spike_analysis:
        logger.success("✅ Spike detection successful!")
        logger.info(f"Current volume: {spike_analysis['normalized_current_volume']:.0f}")
        logger.info(f"Spike ratio: {spike_analysis['spike_ratio_mean']:.2f}x")
        logger.info(f"Spike severity: {spike_analysis['spike_severity']}")
        logger.info(f"Description: {spike_analysis['spike_description']}")
    else:
        logger.error(f"❌ Spike detection failed: {spike_analysis['error']}")
    
    # Test comprehensive analysis
    logger.info("📈 Testing comprehensive volume analysis...")
    comprehensive = detector.get_comprehensive_volume_analysis("BTC")
    
    if "error" not in comprehensive:
        logger.success("✅ Comprehensive analysis successful!")
        summary = comprehensive["summary"]
        logger.info(f"Has spike: {summary['has_spike']}")
        logger.info(f"Spike severity: {summary['spike_severity']}")
        logger.info(f"Volume trend: {summary['volume_trend']}")
        logger.info(f"Current volume: {summary['current_volume']:.0f}")
        logger.info(f"Period progress: {summary['period_progress']}%")
    else:
        logger.error(f"❌ Comprehensive analysis failed: {comprehensive['error']}")


if __name__ == "__main__":
    main()
