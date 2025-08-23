#!/usr/bin/env python3
"""
Signal Weight Optimizer - Statistical Weight Calculation
Dynamically optimizes signal weights based on historical performance
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from loguru import logger
import time
from collections import deque, defaultdict
from dataclasses import dataclass
import json
import os

@dataclass
class SignalPerformance:
    """Track performance metrics for a signal source"""
    signal_name: str
    total_signals: int
    correct_predictions: int
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    avg_confidence: float
    win_rate: float
    last_updated: float

class SignalWeightOptimizer:
    """Optimize signal weights based on statistical performance"""
    
    def __init__(self, lookback_periods: int = 100):
        self.lookback_periods = lookback_periods
        
        # Performance tracking
        self.signal_history = deque(maxlen=1000)
        self.performance_metrics = {}
        
        # Base weights (conservative starting point)
        self.base_weights = {
            "ml_prediction": 0.20,           # Reduced from 25%
            "btc_patterns": 0.25,            # Increased - Bitcoin-specific patterns are crucial
            "traditional_prediction": 0.20,  # Increased - proven methods
            "ultimate_pressure": 0.20,       # Increased - real-time data is valuable
            "whale_analytics": 0.08,          # Slightly reduced but still important
            "blockchain_data": 0.03,          # Reduced - less immediate impact
            "global_volume": 0.02,            # Reduced - often redundant
            "variability_analysis": 0.02      # Reduced - more of a filter than signal
        }
        
        # Performance-adjusted weights (start with base)
        self.optimized_weights = self.base_weights.copy()
        
        # Weight constraints
        self.min_weight = 0.01  # Minimum 1%
        self.max_weight = 0.40  # Maximum 40%
        
        # Market regime tracking
        self.regime_weights = {
            "bull_market": self.base_weights.copy(),
            "bear_market": self.base_weights.copy(),
            "sideways_market": self.base_weights.copy(),
            "high_volatility": self.base_weights.copy(),
            "low_volatility": self.base_weights.copy()
        }
        
        logger.info("🎯 Signal Weight Optimizer initialized with statistical approach")
    
    def record_signal_performance(self, signal_name: str, prediction: Dict[str, Any], 
                                actual_outcome: Dict[str, Any], market_regime: str = "normal"):
        """Record signal performance for weight optimization"""
        try:
            performance_record = {
                "timestamp": time.time(),
                "signal_name": signal_name,
                "predicted_direction": prediction.get("direction", "UNKNOWN"),
                "predicted_confidence": prediction.get("confidence", 0),
                "actual_direction": actual_outcome.get("direction", "UNKNOWN"),
                "actual_return": actual_outcome.get("return", 0),
                "market_regime": market_regime,
                "correct": self._is_prediction_correct(prediction, actual_outcome),
                "prediction_quality": self._calculate_prediction_quality(prediction, actual_outcome)
            }
            
            self.signal_history.append(performance_record)
            
            # Update performance metrics
            self._update_performance_metrics(signal_name)
            
            # Reoptimize weights every 10 signals
            if len(self.signal_history) % 10 == 0:
                self._reoptimize_weights()
            
        except Exception as e:
            logger.error(f"Error recording signal performance: {e}")
    
    def get_optimized_weights(self, market_regime: str = "normal") -> Dict[str, float]:
        """Get current optimized weights for given market regime"""
        if market_regime in self.regime_weights:
            return self.regime_weights[market_regime].copy()
        return self.optimized_weights.copy()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        report = {
            "total_signals_recorded": len(self.signal_history),
            "signal_performance": {},
            "weight_evolution": self._get_weight_evolution(),
            "regime_analysis": self._get_regime_analysis(),
            "optimization_recommendations": self._get_optimization_recommendations()
        }
        
        for signal_name, perf in self.performance_metrics.items():
            report["signal_performance"][signal_name] = {
                "win_rate": f"{perf.win_rate:.1%}",
                "sharpe_ratio": f"{perf.sharpe_ratio:.2f}",
                "total_signals": perf.total_signals,
                "avg_confidence": f"{perf.avg_confidence:.1f}%",
                "current_weight": f"{self.optimized_weights.get(signal_name, 0):.1%}"
            }
        
        return report
    
    def _is_prediction_correct(self, prediction: Dict[str, Any], outcome: Dict[str, Any]) -> bool:
        """Determine if prediction was correct"""
        pred_dir = prediction.get("direction", "").upper()
        actual_dir = outcome.get("direction", "").upper()
        
        if pred_dir in ["BUY", "BULLISH", "UP"] and actual_dir in ["BUY", "BULLISH", "UP"]:
            return True
        elif pred_dir in ["SELL", "BEARISH", "DOWN"] and actual_dir in ["SELL", "BEARISH", "DOWN"]:
            return True
        
        return False
    
    def _calculate_prediction_quality(self, prediction: Dict[str, Any], outcome: Dict[str, Any]) -> float:
        """Calculate quality score (0-1) based on prediction accuracy and magnitude"""
        base_score = 1.0 if self._is_prediction_correct(prediction, outcome) else 0.0
        
        # Adjust for confidence
        confidence = prediction.get("confidence", 50) / 100
        
        # Adjust for magnitude of actual return
        actual_return = abs(outcome.get("return", 0))
        magnitude_bonus = min(0.2, actual_return * 5)  # Up to 20% bonus
        
        return min(1.0, base_score + (confidence * 0.1) + magnitude_bonus)
    
    def _update_performance_metrics(self, signal_name: str):
        """Update performance metrics for a signal"""
        # Get recent performance for this signal
        recent_signals = [s for s in self.signal_history 
                         if s["signal_name"] == signal_name][-self.lookback_periods:]
        
        if len(recent_signals) < 5:  # Need minimum signals
            return
        
        # Calculate metrics
        total_signals = len(recent_signals)
        correct_predictions = sum(1 for s in recent_signals if s["correct"])
        win_rate = correct_predictions / total_signals
        
        returns = [s["actual_return"] for s in recent_signals]
        avg_return = np.mean(returns)
        std_return = np.std(returns) if len(returns) > 1 else 0.001
        sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        
        # Calculate max drawdown
        cumulative_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        # Average confidence
        confidences = [s["predicted_confidence"] for s in recent_signals]
        avg_confidence = np.mean(confidences)
        
        # Store performance
        self.performance_metrics[signal_name] = SignalPerformance(
            signal_name=signal_name,
            total_signals=total_signals,
            correct_predictions=correct_predictions,
            total_return=sum(returns),
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            avg_confidence=avg_confidence,
            win_rate=win_rate,
            last_updated=time.time()
        )
    
    def _reoptimize_weights(self):
        """Reoptimize weights based on performance metrics"""
        try:
            if len(self.performance_metrics) < 3:  # Need minimum signals
                return
            
            # Calculate performance scores
            performance_scores = {}
            
            for signal_name, perf in self.performance_metrics.items():
                # Composite score: 40% win rate + 30% Sharpe + 20% return + 10% confidence
                score = (
                    perf.win_rate * 0.4 +
                    min(1.0, max(0, perf.sharpe_ratio / 2)) * 0.3 +  # Normalize Sharpe
                    min(1.0, max(0, perf.total_return / 0.1)) * 0.2 +  # Normalize return
                    (perf.avg_confidence / 100) * 0.1
                )
                
                # Penalty for high drawdown
                score *= (1 - min(0.5, abs(perf.max_drawdown)))
                
                performance_scores[signal_name] = max(0.1, score)  # Minimum score
            
            # Calculate new weights
            total_score = sum(performance_scores.values())
            new_weights = {}
            
            for signal_name, score in performance_scores.items():
                # Blend with base weight (70% performance, 30% base)
                performance_weight = score / total_score
                base_weight = self.base_weights.get(signal_name, 0.1)
                
                blended_weight = performance_weight * 0.7 + base_weight * 0.3
                
                # Apply constraints
                constrained_weight = max(self.min_weight, min(self.max_weight, blended_weight))
                new_weights[signal_name] = constrained_weight
            
            # Normalize to sum to 1.0
            total_weight = sum(new_weights.values())
            self.optimized_weights = {k: v/total_weight for k, v in new_weights.items()}
            
            logger.info("🔄 Signal weights reoptimized based on performance")
            self._log_weight_changes()
            
        except Exception as e:
            logger.error(f"Weight optimization error: {e}")
    
    def _log_weight_changes(self):
        """Log significant weight changes"""
        logger.info("📊 Updated Signal Weights:")
        for signal, weight in sorted(self.optimized_weights.items(), key=lambda x: x[1], reverse=True):
            perf = self.performance_metrics.get(signal)
            if perf:
                logger.info(f"   {signal}: {weight:.1%} (Win Rate: {perf.win_rate:.1%}, Sharpe: {perf.sharpe_ratio:.2f})")
            else:
                logger.info(f"   {signal}: {weight:.1%} (No performance data)")
    
    def _get_weight_evolution(self) -> List[Dict]:
        """Get weight evolution over time"""
        # This would track weight changes over time
        return []
    
    def _get_regime_analysis(self) -> Dict[str, Any]:
        """Analyze performance by market regime"""
        regime_analysis = {}
        
        for regime in ["bull_market", "bear_market", "sideways_market", "high_volatility", "low_volatility"]:
            regime_signals = [s for s in self.signal_history if s.get("market_regime") == regime]
            
            if regime_signals:
                correct = sum(1 for s in regime_signals if s["correct"])
                total = len(regime_signals)
                regime_analysis[regime] = {
                    "signal_count": total,
                    "accuracy": correct / total if total > 0 else 0,
                    "avg_return": np.mean([s["actual_return"] for s in regime_signals])
                }
        
        return regime_analysis
    
    def _get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations"""
        recommendations = []
        
        # Check for underperforming signals
        for signal_name, perf in self.performance_metrics.items():
            if perf.win_rate < 0.4:
                recommendations.append(f"⚠️ {signal_name} has low win rate ({perf.win_rate:.1%}) - consider reducing weight")
            
            if perf.sharpe_ratio < 0:
                recommendations.append(f"⚠️ {signal_name} has negative Sharpe ratio - review signal logic")
            
            if perf.total_signals < 10:
                recommendations.append(f"📊 {signal_name} needs more data points for reliable optimization")
        
        # Check for high performers
        top_performer = max(self.performance_metrics.items(), key=lambda x: x[1].win_rate, default=None)
        if top_performer and top_performer[1].win_rate > 0.7:
            recommendations.append(f"🎯 {top_performer[0]} is performing excellently ({top_performer[1].win_rate:.1%}) - consider increasing weight")
        
        return recommendations
    
    def save_performance_data(self, filepath: str = "signal_performance.json"):
        """Save performance data for persistence"""
        try:
            data = {
                "performance_metrics": {k: vars(v) for k, v in self.performance_metrics.items()},
                "optimized_weights": self.optimized_weights,
                "base_weights": self.base_weights,
                "last_updated": time.time()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"💾 Signal performance data saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save performance data: {e}")
    
    def load_performance_data(self, filepath: str = "signal_performance.json"):
        """Load performance data from file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Restore performance metrics
                for signal_name, perf_data in data.get("performance_metrics", {}).items():
                    self.performance_metrics[signal_name] = SignalPerformance(**perf_data)
                
                # Restore weights
                self.optimized_weights = data.get("optimized_weights", self.base_weights)
                
                logger.info(f"📂 Signal performance data loaded from {filepath}")
                
        except Exception as e:
            logger.error(f"Failed to load performance data: {e}")