#!/usr/bin/env python3
"""
Multi-Timeframe Probability Module
Tracks different win rates and probabilities across different holding periods
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from loguru import logger


@dataclass
class TimeframeStats:
    """Statistics for a specific timeframe"""
    timeframe_name: str  # e.g., "1-5min", "5-15min", "15-30min"
    min_duration_seconds: float
    max_duration_seconds: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_return_pct: float
    avg_hold_time_seconds: float
    best_confidence_range: str  # e.g., "75-80%"
    best_confidence_win_rate: float


class MultiTimeframeProbability:
    """Tracks performance across different holding periods"""
    
    def __init__(self, data_dir: str = "data/timeframe_analysis"):
        """
        Initialize Multi-Timeframe Probability Tracker
        
        Args:
            data_dir: Directory to store timeframe data
        """
        self.data_dir = data_dir
        self.stats_file = os.path.join(data_dir, "timeframe_stats.json")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Define timeframe buckets (in seconds)
        self.timeframes = {
            "1-5min": (60, 300),
            "5-15min": (300, 900),
            "15-30min": (900, 1800),
            "30min-1hr": (1800, 3600),
            "1hr-2hr": (3600, 7200),
            "2hr-4hr": (7200, 14400),
            "4hr+": (14400, float('inf'))
        }
        
        # Load historical data
        self.stats = self._load_stats()
        
        logger.info(f"⏱️ Multi-Timeframe Probability initialized")
        logger.info(f"   📁 Data directory: {data_dir}")
        logger.info(f"   📊 Tracking {len(self.timeframes)} timeframes")
    
    def record_trade_outcome(
        self,
        hold_time_seconds: float,
        won: bool,
        return_pct: float,
        confidence: float
    ):
        """
        Record a trade outcome and update timeframe statistics
        
        Args:
            hold_time_seconds: How long the trade lasted
            won: Did the trade win?
            return_pct: Return as percentage
            confidence: Predicted confidence at entry
        """
        # Find matching timeframe
        timeframe_name = self._get_timeframe_bucket(hold_time_seconds)
        
        if timeframe_name not in self.stats:
            # Initialize new timeframe stats
            min_dur, max_dur = self.timeframes[timeframe_name]
            self.stats[timeframe_name] = {
                "timeframe_name": timeframe_name,
                "min_duration_seconds": min_dur,
                "max_duration_seconds": max_dur,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "avg_return_pct": 0.0,
                "total_return_pct": 0.0,
                "avg_hold_time_seconds": 0.0,
                "total_hold_time_seconds": 0.0,
                "confidence_buckets": {}
            }
        
        stats = self.stats[timeframe_name]
        
        # Update stats
        stats["total_trades"] += 1
        if won:
            stats["wins"] += 1
        else:
            stats["losses"] += 1
        
        stats["total_return_pct"] += return_pct
        stats["total_hold_time_seconds"] += hold_time_seconds
        
        # Recalculate averages
        stats["win_rate"] = stats["wins"] / stats["total_trades"]
        stats["avg_return_pct"] = stats["total_return_pct"] / stats["total_trades"]
        stats["avg_hold_time_seconds"] = stats["total_hold_time_seconds"] / stats["total_trades"]
        
        # Track by confidence bucket
        conf_bucket = self._get_confidence_bucket(confidence)
        if conf_bucket not in stats["confidence_buckets"]:
            stats["confidence_buckets"][conf_bucket] = {
                "trades": 0,
                "wins": 0,
                "win_rate": 0.0
            }
        
        conf_stats = stats["confidence_buckets"][conf_bucket]
        conf_stats["trades"] += 1
        if won:
            conf_stats["wins"] += 1
        conf_stats["win_rate"] = conf_stats["wins"] / conf_stats["trades"]
        
        # Save updated stats
        self._save_stats()
        
        logger.info(f"⏱️ Trade recorded: {timeframe_name} | "
                   f"{'WIN' if won else 'LOSS'} | {hold_time_seconds/60:.1f}min")
    
    def get_win_rate_for_timeframe(
        self,
        target_hold_time_seconds: float,
        confidence: Optional[float] = None
    ) -> Tuple[float, int]:
        """
        Get expected win rate for a target holding period
        
        Args:
            target_hold_time_seconds: Expected hold time
            confidence: Optional - filter by confidence level
            
        Returns:
            (win_rate, sample_size)
        """
        timeframe_name = self._get_timeframe_bucket(target_hold_time_seconds)
        
        if timeframe_name not in self.stats:
            return 0.50, 0  # No data, return base rate
        
        stats = self.stats[timeframe_name]
        
        # If confidence specified, use confidence bucket
        if confidence is not None:
            conf_bucket = self._get_confidence_bucket(confidence)
            if conf_bucket in stats["confidence_buckets"]:
                conf_stats = stats["confidence_buckets"][conf_bucket]
                return conf_stats["win_rate"], conf_stats["trades"]
        
        # Otherwise return overall win rate for timeframe
        return stats["win_rate"], stats["total_trades"]
    
    def get_optimal_timeframe(self) -> Tuple[str, float, int]:
        """
        Get the timeframe with highest win rate
        
        Returns:
            (timeframe_name, win_rate, sample_size)
        """
        if not self.stats:
            return "Unknown", 0.50, 0
        
        best_timeframe = None
        best_win_rate = 0.0
        best_sample_size = 0
        
        for timeframe_name, stats in self.stats.items():
            if stats["total_trades"] >= 5:  # Minimum sample size
                if stats["win_rate"] > best_win_rate:
                    best_win_rate = stats["win_rate"]
                    best_timeframe = timeframe_name
                    best_sample_size = stats["total_trades"]
        
        if best_timeframe is None:
            return "Insufficient data", 0.50, 0
        
        return best_timeframe, best_win_rate, best_sample_size
    
    def get_timeframe_report(self) -> Dict[str, Any]:
        """
        Get comprehensive report of all timeframe statistics
        
        Returns:
            Dict with timeframe analysis
        """
        if not self.stats:
            return {
                "total_trades": 0,
                "timeframes": [],
                "message": "No trades recorded yet"
            }
        
        total_trades = sum(stats["total_trades"] for stats in self.stats.values())
        
        timeframe_summaries = []
        for timeframe_name in sorted(self.stats.keys(), 
                                     key=lambda x: self.timeframes[x][0]):
            stats = self.stats[timeframe_name]
            
            if stats["total_trades"] > 0:
                timeframe_summaries.append({
                    "timeframe": timeframe_name,
                    "trades": stats["total_trades"],
                    "win_rate": round(stats["win_rate"], 4),
                    "avg_return_pct": round(stats["avg_return_pct"], 4),
                    "avg_hold_time_minutes": round(stats["avg_hold_time_seconds"] / 60, 1),
                    "wins": stats["wins"],
                    "losses": stats["losses"]
                })
        
        # Find best timeframe
        best_tf, best_wr, best_sample = self.get_optimal_timeframe()
        
        return {
            "total_trades": total_trades,
            "timeframes": timeframe_summaries,
            "best_timeframe": best_tf,
            "best_win_rate": round(best_wr, 4),
            "best_sample_size": best_sample
        }
    
    def get_probability_adjustment(
        self,
        base_probability: float,
        expected_hold_time_seconds: float
    ) -> Tuple[float, str]:
        """
        Adjust probability based on expected holding period
        
        Args:
            base_probability: Base win probability
            expected_hold_time_seconds: Expected trade duration
            
        Returns:
            (adjusted_probability, reasoning)
        """
        timeframe_win_rate, sample_size = self.get_win_rate_for_timeframe(
            expected_hold_time_seconds
        )
        
        if sample_size < 10:
            return base_probability, f"Insufficient data ({sample_size} trades)"
        
        # Blend base probability with timeframe-specific win rate
        # More data = more weight to timeframe win rate
        weight = min(sample_size / 50, 0.5)  # Max 50% weight
        adjusted = base_probability * (1 - weight) + timeframe_win_rate * weight
        
        timeframe_name = self._get_timeframe_bucket(expected_hold_time_seconds)
        
        if abs(adjusted - base_probability) < 0.02:
            reasoning = f"{timeframe_name}: Aligned with historical ({sample_size} trades)"
        elif adjusted > base_probability:
            reasoning = f"{timeframe_name}: Historically outperforms {adjusted - base_probability:+.1%} ({sample_size} trades)"
        else:
            reasoning = f"{timeframe_name}: Historically underperforms {adjusted - base_probability:.1%} ({sample_size} trades)"
        
        return adjusted, reasoning
    
    def _get_timeframe_bucket(self, duration_seconds: float) -> str:
        """Get timeframe bucket name for a duration"""
        for timeframe_name, (min_dur, max_dur) in self.timeframes.items():
            if min_dur <= duration_seconds < max_dur:
                return timeframe_name
        return "4hr+"  # Default for long trades
    
    def _get_confidence_bucket(self, confidence: float) -> str:
        """Get confidence bucket (5% increments)"""
        bucket_index = int(confidence * 100 / 5) * 5
        bucket_index = max(50, min(95, bucket_index))
        return f"{bucket_index}-{bucket_index+5}%"
    
    def _load_stats(self) -> Dict[str, Any]:
        """Load timeframe stats from disk"""
        if not os.path.exists(self.stats_file):
            return {}
        
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Failed to load timeframe stats: {e}")
            return {}
    
    def _save_stats(self):
        """Save timeframe stats to disk"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save timeframe stats: {e}")


# Global singleton instance
_global_multitimeframe_probability = None


def get_global_multitimeframe_probability() -> MultiTimeframeProbability:
    """Get the global MultiTimeframeProbability singleton instance"""
    global _global_multitimeframe_probability
    if _global_multitimeframe_probability is None:
        _global_multitimeframe_probability = MultiTimeframeProbability()
    return _global_multitimeframe_probability

