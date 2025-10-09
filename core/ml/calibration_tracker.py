#!/usr/bin/env python3
"""
Confidence Calibration Tracker Module
Tracks historical performance to validate prediction confidence accuracy
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from loguru import logger


@dataclass
class TradeOutcome:
    """Record of a single trade outcome"""
    timestamp: float
    direction: str  # "LONG" or "SHORT"
    predicted_confidence: float  # Predicted win probability
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    won: bool  # Did the trade hit TP (True) or SL (False)
    pnl_percent: float  # Actual P&L as percentage
    pnl_dollars: float  # Actual P&L in dollars
    hold_time_seconds: float  # How long the trade lasted
    market_conditions: Dict[str, Any]  # Market state at time of trade


@dataclass
class CalibrationBucket:
    """Performance statistics for a confidence range"""
    confidence_range: str  # e.g., "70-75%"
    min_confidence: float
    max_confidence: float
    total_trades: int
    wins: int
    losses: int
    actual_win_rate: float
    avg_predicted_confidence: float
    calibration_error: float  # abs(predicted - actual)
    avg_pnl_percent: float
    total_pnl_dollars: float
    avg_hold_time_seconds: float


class CalibrationTracker:
    """Tracks prediction accuracy and calibrates confidence levels"""
    
    def __init__(self, data_dir: str = "data/calibration"):
        """
        Initialize Calibration Tracker
        
        Args:
            data_dir: Directory to store calibration data
        """
        self.data_dir = data_dir
        self.history_file = os.path.join(data_dir, "trade_history.json")
        self.calibration_file = os.path.join(data_dir, "calibration_data.json")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Load historical data
        self.trade_history: List[TradeOutcome] = self._load_history()
        
        # Confidence buckets (5% increments)
        self.bucket_size = 0.05
        self.buckets = self._create_buckets()
        
        # Update calibration statistics
        self._update_calibration()
        
        logger.info(f"📊 Calibration Tracker initialized")
        logger.info(f"   📁 Data directory: {data_dir}")
        logger.info(f"   📈 Historical trades: {len(self.trade_history)}")
    
    def _create_buckets(self) -> Dict[str, CalibrationBucket]:
        """Create confidence buckets for tracking"""
        buckets = {}
        
        # Create buckets: 50-55%, 55-60%, 60-65%, ..., 95-100%
        for i in range(50, 100, 5):
            min_conf = i / 100.0
            max_conf = (i + 5) / 100.0
            bucket_name = f"{i}-{i+5}%"
            
            buckets[bucket_name] = CalibrationBucket(
                confidence_range=bucket_name,
                min_confidence=min_conf,
                max_confidence=max_conf,
                total_trades=0,
                wins=0,
                losses=0,
                actual_win_rate=0.0,
                avg_predicted_confidence=0.0,
                calibration_error=0.0,
                avg_pnl_percent=0.0,
                total_pnl_dollars=0.0,
                avg_hold_time_seconds=0.0
            )
        
        return buckets
    
    def record_trade(
        self,
        direction: str,
        predicted_confidence: float,
        entry_price: float,
        exit_price: float,
        stop_loss: float,
        take_profit: float,
        hold_time_seconds: float,
        position_size: float = 1000.0,
        market_conditions: Optional[Dict[str, Any]] = None
    ) -> TradeOutcome:
        """
        Record a completed trade outcome
        
        Args:
            direction: "LONG" or "SHORT"
            predicted_confidence: Confidence at time of trade entry
            entry_price: Entry price
            exit_price: Exit price (either TP or SL hit)
            stop_loss: Stop loss price
            take_profit: Take profit price
            hold_time_seconds: Duration of trade
            position_size: Position size in dollars
            market_conditions: Market state snapshot
            
        Returns:
            TradeOutcome object
        """
        # Determine if trade won (hit TP) or lost (hit SL)
        if direction == "LONG":
            won = exit_price >= take_profit
            pnl_percent = (exit_price - entry_price) / entry_price
        else:  # SHORT
            won = exit_price <= take_profit
            pnl_percent = (entry_price - exit_price) / entry_price
        
        pnl_dollars = pnl_percent * position_size
        
        outcome = TradeOutcome(
            timestamp=datetime.now().timestamp(),
            direction=direction,
            predicted_confidence=predicted_confidence,
            entry_price=entry_price,
            exit_price=exit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            won=won,
            pnl_percent=pnl_percent,
            pnl_dollars=pnl_dollars,
            hold_time_seconds=hold_time_seconds,
            market_conditions=market_conditions or {}
        )
        
        # Add to history
        self.trade_history.append(outcome)
        
        # Update calibration
        self._update_calibration()
        
        # Save to disk
        self._save_history()
        
        logger.info(f"📊 Trade recorded: {direction} @ ${entry_price:,.2f} → ${exit_price:,.2f} | "
                   f"{'WIN' if won else 'LOSS'} | Predicted: {predicted_confidence:.1%}")
        
        return outcome
    
    def _update_calibration(self):
        """Update calibration statistics for all buckets"""
        # Reset all buckets
        for bucket in self.buckets.values():
            bucket.total_trades = 0
            bucket.wins = 0
            bucket.losses = 0
            bucket.actual_win_rate = 0.0
            bucket.avg_predicted_confidence = 0.0
            bucket.calibration_error = 0.0
            bucket.avg_pnl_percent = 0.0
            bucket.total_pnl_dollars = 0.0
            bucket.avg_hold_time_seconds = 0.0
        
        # Aggregate trades into buckets
        for trade in self.trade_history:
            bucket_name = self._get_bucket_name(trade.predicted_confidence)
            if bucket_name in self.buckets:
                bucket = self.buckets[bucket_name]
                bucket.total_trades += 1
                if trade.won:
                    bucket.wins += 1
                else:
                    bucket.losses += 1
                bucket.total_pnl_dollars += trade.pnl_dollars
        
        # Calculate statistics for each bucket
        for bucket in self.buckets.values():
            if bucket.total_trades > 0:
                bucket.actual_win_rate = bucket.wins / bucket.total_trades
                
                # Calculate average predicted confidence
                bucket_trades = [t for t in self.trade_history 
                               if self._get_bucket_name(t.predicted_confidence) == bucket.confidence_range]
                
                if bucket_trades:
                    bucket.avg_predicted_confidence = sum(t.predicted_confidence for t in bucket_trades) / len(bucket_trades)
                    bucket.calibration_error = abs(bucket.avg_predicted_confidence - bucket.actual_win_rate)
                    bucket.avg_pnl_percent = sum(t.pnl_percent for t in bucket_trades) / len(bucket_trades)
                    bucket.avg_hold_time_seconds = sum(t.hold_time_seconds for t in bucket_trades) / len(bucket_trades)
        
        # Save calibration data
        self._save_calibration()
    
    def _get_bucket_name(self, confidence: float) -> str:
        """Get bucket name for a given confidence level"""
        # Round down to nearest 5%
        bucket_index = int(confidence * 100 / 5) * 5
        bucket_index = max(50, min(95, bucket_index))  # Clamp to 50-95
        return f"{bucket_index}-{bucket_index+5}%"
    
    def get_calibration_report(self) -> Dict[str, Any]:
        """
        Get full calibration report
        
        Returns:
            Dict with calibration statistics
        """
        total_trades = len(self.trade_history)
        
        if total_trades == 0:
            return {
                "total_trades": 0,
                "overall_win_rate": 0.0,
                "overall_calibration_error": 0.0,
                "buckets": [],
                "message": "No trades recorded yet"
            }
        
        total_wins = sum(1 for t in self.trade_history if t.won)
        overall_win_rate = total_wins / total_trades
        
        avg_predicted_confidence = sum(t.predicted_confidence for t in self.trade_history) / total_trades
        overall_calibration_error = abs(avg_predicted_confidence - overall_win_rate)
        
        # Get bucket summaries (only non-empty buckets)
        bucket_summaries = []
        for bucket in self.buckets.values():
            if bucket.total_trades > 0:
                bucket_summaries.append({
                    "confidence_range": bucket.confidence_range,
                    "trades": bucket.total_trades,
                    "wins": bucket.wins,
                    "losses": bucket.losses,
                    "actual_win_rate": round(bucket.actual_win_rate, 4),
                    "predicted_confidence": round(bucket.avg_predicted_confidence, 4),
                    "calibration_error": round(bucket.calibration_error, 4),
                    "avg_pnl_percent": round(bucket.avg_pnl_percent, 4),
                    "total_pnl": round(bucket.total_pnl_dollars, 2),
                    "avg_hold_time_minutes": round(bucket.avg_hold_time_seconds / 60, 1)
                })
        
        # Sort by confidence range
        bucket_summaries.sort(key=lambda x: x["confidence_range"])
        
        return {
            "total_trades": total_trades,
            "overall_win_rate": round(overall_win_rate, 4),
            "overall_calibration_error": round(overall_calibration_error, 4),
            "avg_predicted_confidence": round(avg_predicted_confidence, 4),
            "buckets": bucket_summaries,
            "well_calibrated": overall_calibration_error < 0.05  # Within 5%
        }
    
    def get_calibrated_confidence(self, predicted_confidence: float) -> float:
        """
        Get calibrated confidence based on historical performance
        
        If your 80% predictions only win 70% of the time, this returns 0.70
        
        Args:
            predicted_confidence: Raw predicted confidence
            
        Returns:
            Calibrated confidence based on historical data
        """
        bucket_name = self._get_bucket_name(predicted_confidence)
        
        if bucket_name not in self.buckets:
            return predicted_confidence
        
        bucket = self.buckets[bucket_name]
        
        # If we have enough data in this bucket, use actual win rate
        if bucket.total_trades >= 10:  # Minimum 10 trades for calibration
            return bucket.actual_win_rate
        
        # Not enough data - use raw prediction
        return predicted_confidence
    
    def get_calibration_adjustment(self, predicted_confidence: float) -> Tuple[float, str]:
        """
        Get calibration adjustment for a prediction
        
        Returns:
            (adjusted_confidence, reasoning)
        """
        bucket_name = self._get_bucket_name(predicted_confidence)
        bucket = self.buckets.get(bucket_name)
        
        if not bucket or bucket.total_trades < 10:
            return predicted_confidence, f"Insufficient data ({bucket.total_trades if bucket else 0} trades)"
        
        calibrated = bucket.actual_win_rate
        adjustment = calibrated - predicted_confidence
        
        if abs(adjustment) < 0.02:  # Within 2%
            reasoning = f"Well calibrated ({bucket.total_trades} trades)"
        elif adjustment > 0:
            reasoning = f"Historically outperforms by {adjustment:+.1%} ({bucket.total_trades} trades)"
        else:
            reasoning = f"Historically underperforms by {adjustment:.1%} ({bucket.total_trades} trades)"
        
        return calibrated, reasoning
    
    def _load_history(self) -> List[TradeOutcome]:
        """Load trade history from disk"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                return [TradeOutcome(**trade) for trade in data]
        except Exception as e:
            logger.warning(f"⚠️ Failed to load trade history: {e}")
            return []
    
    def _save_history(self):
        """Save trade history to disk"""
        try:
            with open(self.history_file, 'w') as f:
                data = [asdict(trade) for trade in self.trade_history]
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save trade history: {e}")
    
    def _save_calibration(self):
        """Save calibration data to disk"""
        try:
            report = self.get_calibration_report()
            with open(self.calibration_file, 'w') as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save calibration data: {e}")


# Global singleton instance
_global_calibration_tracker = None


def get_global_calibration_tracker() -> CalibrationTracker:
    """Get the global CalibrationTracker singleton instance"""
    global _global_calibration_tracker
    if _global_calibration_tracker is None:
        _global_calibration_tracker = CalibrationTracker()
    return _global_calibration_tracker

