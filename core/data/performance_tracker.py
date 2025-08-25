#!/usr/bin/env python3
"""
Performance Tracker
Handles performance metrics calculation and tracking
Single Responsibility: Performance analysis and metrics computation
"""

import time
import threading
from typing import Dict, Any, List
from loguru import logger
from collections import deque


class PerformanceTracker:
    """
    Tracks and calculates trading performance metrics
    Single Responsibility: Performance metrics calculation and analysis
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for performance tracking"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.tracker_lock = threading.RLock()
        
        # Performance metrics storage
        self.performance_metrics = {
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "avg_trade_duration": 0.0,
            "last_updated": time.time()
        }
        
        # Historical metrics for trend analysis
        self.metrics_history = deque(maxlen=100)  # Keep last 100 metric snapshots
        
        # Balance tracking for drawdown calculation
        self.balance_history = deque(maxlen=1000)  # Keep last 1000 balance updates
        self.peak_balance = 0.0
        
        logger.success("📊 Performance Tracker initialized")
    
    def update_metrics_from_trades(self, trades: List[Dict[str, Any]]):
        """Update performance metrics based on trade list"""
        with self.tracker_lock:
            try:
                if not trades:
                    return self.performance_metrics.copy()
                
                # Separate profitable and losing trades
                profitable_trades = [t for t in trades if t.get("was_profitable", False)]
                losing_trades = [t for t in trades if not t.get("was_profitable", False)]
                
                # Basic metrics
                total_trades = len(trades)
                winning_trades = len(profitable_trades)
                losing_trades_count = len(losing_trades)
                
                # PnL calculations
                total_pnl = sum(t.get("pnl", 0) for t in trades)
                total_wins = sum(t.get("pnl", 0) for t in profitable_trades)
                total_losses = abs(sum(t.get("pnl", 0) for t in losing_trades))
                
                # Average calculations
                avg_win = total_wins / winning_trades if winning_trades > 0 else 0.0
                avg_loss = total_losses / losing_trades_count if losing_trades_count > 0 else 0.0
                
                # Win rate
                win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0
                
                # Profit factor
                profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0.0
                
                # Consecutive wins/losses
                max_consecutive_wins, max_consecutive_losses = self._calculate_consecutive_streaks(trades)
                
                # Largest win/loss
                largest_win = max((t.get("pnl", 0) for t in profitable_trades), default=0.0)
                largest_loss = min((t.get("pnl", 0) for t in losing_trades), default=0.0)
                
                # Average trade duration
                durations = [t.get("holding_time", 0) for t in trades if t.get("holding_time", 0) > 0]
                avg_trade_duration = sum(durations) / len(durations) if durations else 0.0
                
                # Sharpe ratio (simplified calculation)
                sharpe_ratio = self._calculate_sharpe_ratio(trades)
                
                # Update metrics
                self.performance_metrics.update({
                    "total_pnl": total_pnl,
                    "win_rate": win_rate,
                    "avg_win": avg_win,
                    "avg_loss": avg_loss,
                    "profit_factor": profit_factor,
                    "sharpe_ratio": sharpe_ratio,
                    "max_consecutive_wins": max_consecutive_wins,
                    "max_consecutive_losses": max_consecutive_losses,
                    "largest_win": largest_win,
                    "largest_loss": largest_loss,
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades_count,
                    "avg_trade_duration": avg_trade_duration,
                    "last_updated": time.time()
                })
                
                # Store snapshot in history
                self.metrics_history.append(self.performance_metrics.copy())
                
                logger.debug(f"📊 Performance metrics updated: {total_trades} trades, {win_rate:.1%} win rate")
                return self.performance_metrics.copy()
                
            except Exception as e:
                logger.error(f"Error updating performance metrics: {e}")
                return self.performance_metrics.copy()
    
    def update_balance_tracking(self, current_balance: float):
        """Update balance tracking for drawdown calculation"""
        with self.tracker_lock:
            try:
                # Add to balance history
                balance_record = {
                    "balance": current_balance,
                    "timestamp": time.time()
                }
                self.balance_history.append(balance_record)
                
                # Update peak balance
                if current_balance > self.peak_balance:
                    self.peak_balance = current_balance
                
                # Calculate current drawdown
                if self.peak_balance > 0:
                    current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
                    
                    # Update max drawdown
                    if current_drawdown > self.performance_metrics["max_drawdown"]:
                        self.performance_metrics["max_drawdown"] = current_drawdown
                
                logger.debug(f"💰 Balance tracking updated: ${current_balance:.2f} (Peak: ${self.peak_balance:.2f})")
                
            except Exception as e:
                logger.error(f"Error updating balance tracking: {e}")
    
    def _calculate_consecutive_streaks(self, trades: List[Dict[str, Any]]) -> tuple:
        """Calculate maximum consecutive wins and losses"""
        if not trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        # Sort trades by timestamp
        sorted_trades = sorted(trades, key=lambda x: x.get("entry_time", 0))
        
        for trade in sorted_trades:
            if trade.get("was_profitable", False):
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def _calculate_sharpe_ratio(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate simplified Sharpe ratio"""
        try:
            if len(trades) < 2:
                return 0.0
            
            # Get PnL percentages
            returns = [t.get("pnl_pct", 0) for t in trades if t.get("pnl_pct") is not None]
            
            if not returns:
                return 0.0
            
            # Calculate mean and standard deviation
            mean_return = sum(returns) / len(returns)
            
            if len(returns) < 2:
                return 0.0
            
            variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = variance ** 0.5
            
            # Sharpe ratio (assuming risk-free rate of 0)
            sharpe = mean_return / std_dev if std_dev > 0 else 0.0
            
            return sharpe
            
        except Exception as e:
            logger.debug(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self.tracker_lock:
            return self.performance_metrics.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get formatted performance summary"""
        with self.tracker_lock:
            metrics = self.performance_metrics.copy()
            
            # Add formatted versions
            summary = {
                "raw_metrics": metrics,
                "formatted": {
                    "total_pnl": f"${metrics['total_pnl']:.2f}",
                    "win_rate": f"{metrics['win_rate']:.1%}",
                    "profit_factor": f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] != float('inf') else "∞",
                    "max_drawdown": f"{metrics['max_drawdown']:.1%}",
                    "sharpe_ratio": f"{metrics['sharpe_ratio']:.2f}",
                    "avg_win": f"${metrics['avg_win']:.2f}",
                    "avg_loss": f"${metrics['avg_loss']:.2f}",
                    "trade_summary": f"{metrics['winning_trades']}W / {metrics['losing_trades']}L / {metrics['total_trades']}T"
                },
                "quality_assessment": self._assess_performance_quality(metrics)
            }
            
            return summary
    
    def _assess_performance_quality(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of trading performance"""
        try:
            # Quality scoring
            quality_score = 0
            max_score = 100
            
            # Win rate component (25 points)
            win_rate = metrics.get("win_rate", 0)
            if win_rate >= 0.6:
                quality_score += 25
            elif win_rate >= 0.5:
                quality_score += 20
            elif win_rate >= 0.4:
                quality_score += 15
            elif win_rate >= 0.3:
                quality_score += 10
            
            # Profit factor component (25 points)
            profit_factor = metrics.get("profit_factor", 0)
            if profit_factor >= 2.0:
                quality_score += 25
            elif profit_factor >= 1.5:
                quality_score += 20
            elif profit_factor >= 1.2:
                quality_score += 15
            elif profit_factor >= 1.0:
                quality_score += 10
            
            # Total PnL component (25 points)
            total_pnl = metrics.get("total_pnl", 0)
            if total_pnl > 0:
                quality_score += 25
            elif total_pnl > -10:
                quality_score += 15
            elif total_pnl > -25:
                quality_score += 10
            
            # Drawdown component (25 points)
            max_drawdown = metrics.get("max_drawdown", 0)
            if max_drawdown <= 0.05:  # ≤5%
                quality_score += 25
            elif max_drawdown <= 0.10:  # ≤10%
                quality_score += 20
            elif max_drawdown <= 0.15:  # ≤15%
                quality_score += 15
            elif max_drawdown <= 0.20:  # ≤20%
                quality_score += 10
            
            # Determine quality grade
            if quality_score >= 85:
                grade = "EXCELLENT"
            elif quality_score >= 70:
                grade = "GOOD"
            elif quality_score >= 55:
                grade = "FAIR"
            elif quality_score >= 40:
                grade = "POOR"
            else:
                grade = "VERY_POOR"
            
            return {
                "score": quality_score,
                "max_score": max_score,
                "percentage": quality_score / max_score,
                "grade": grade,
                "components": {
                    "win_rate_score": min(25, max(0, (win_rate - 0.3) * 25 / 0.3)),
                    "profit_factor_score": min(25, max(0, (profit_factor - 1.0) * 25 / 1.0)),
                    "pnl_positive": total_pnl > 0,
                    "drawdown_acceptable": max_drawdown <= 0.15
                }
            }
            
        except Exception as e:
            logger.error(f"Error assessing performance quality: {e}")
            return {"score": 0, "grade": "ERROR"}
    
    def get_metrics_trend(self, lookback_periods: int = 10) -> Dict[str, Any]:
        """Get trend analysis of performance metrics"""
        with self.tracker_lock:
            if len(self.metrics_history) < 2:
                return {"error": "Insufficient data for trend analysis"}
            
            # Get recent metrics
            recent_metrics = list(self.metrics_history)[-lookback_periods:]
            
            if len(recent_metrics) < 2:
                return {"error": "Insufficient data for trend analysis"}
            
            # Calculate trends
            first = recent_metrics[0]
            last = recent_metrics[-1]
            
            trends = {}
            for key in ["total_pnl", "win_rate", "profit_factor", "max_drawdown"]:
                if key in first and key in last:
                    first_val = first[key]
                    last_val = last[key]
                    
                    if first_val != 0:
                        change = (last_val - first_val) / abs(first_val)
                        trends[key] = {
                            "change_pct": change,
                            "direction": "IMPROVING" if change > 0.05 else "DECLINING" if change < -0.05 else "STABLE",
                            "first_value": first_val,
                            "last_value": last_val
                        }
            
            return {
                "periods_analyzed": len(recent_metrics),
                "trends": trends,
                "overall_trend": self._determine_overall_trend(trends)
            }
    
    def _determine_overall_trend(self, trends: Dict[str, Any]) -> str:
        """Determine overall performance trend"""
        improving = 0
        declining = 0
        
        for trend_data in trends.values():
            direction = trend_data.get("direction", "STABLE")
            if direction == "IMPROVING":
                improving += 1
            elif direction == "DECLINING":
                declining += 1
        
        if improving > declining:
            return "IMPROVING"
        elif declining > improving:
            return "DECLINING"
        else:
            return "STABLE"
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        with self.tracker_lock:
            self.performance_metrics = {
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "avg_trade_duration": 0.0,
                "last_updated": time.time()
            }
            
            self.metrics_history.clear()
            self.balance_history.clear()
            self.peak_balance = 0.0
            
            logger.info("🧹 Performance metrics reset")


# Global instance (singleton)
performance_tracker = PerformanceTracker()