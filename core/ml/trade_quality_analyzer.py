"""
Trade Quality Analysis System
Analyzes completed trades against perfect imaginary trades to improve AI learning
"""

import time
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TradeQualityMetrics:
    """Trade quality analysis metrics"""
    direction_accuracy: float  # 0.0-1.0, was direction correct?
    entry_timing_accuracy: float  # 0.0-1.0, how close to predicted entry?
    take_profit_accuracy: float  # 0.0-1.0, how close to predicted TP?
    stop_loss_accuracy: float  # 0.0-1.0, was SL needed?
    profit_efficiency: float  # 0.0-1.0, actual vs perfect profit
    overall_quality: float  # 0.0-1.0, weighted average
    perfect_trade_score: float  # 0.0-1.0, how close to perfect trade
    learning_insights: List[str]  # Key insights for AI learning

class TradeQualityAnalyzer:
    """Analyzes trade quality by comparing actual vs perfect imaginary trades"""
    
    def __init__(self):
        self.quality_history: List[Dict[str, Any]] = []
        logger.info("🎯 Trade Quality Analyzer initialized")
    
    def analyze_trade_quality(self, trade_data: Dict[str, Any], 
                            market_timeline: List[Dict[str, Any]]) -> TradeQualityMetrics:
        """
        Analyze trade quality by comparing actual trade vs perfect imaginary trade
        
        Args:
            trade_data: Completed trade data
            market_timeline: Price data from entry to close
            
        Returns:
            TradeQualityMetrics with detailed analysis
        """
        try:
            logger.info(f"🔍 Analyzing trade quality for trade {trade_data.get('trade_id', 'unknown')}")
            
            # Extract trade details
            direction = trade_data.get("direction", "BUY")
            entry_price = trade_data.get("entry_price", 0)
            take_profit = trade_data.get("take_profit", 0)
            stop_loss = trade_data.get("stop_loss", 0)
            actual_result = trade_data.get("result", 0)  # Actual P&L
            
            # Find perfect imaginary trade
            perfect_trade = self._find_perfect_trade(
                direction, entry_price, market_timeline
            )
            
            # Calculate quality metrics
            metrics = self._calculate_quality_metrics(
                trade_data, perfect_trade, market_timeline
            )
            
            # Generate learning insights
            insights = self._generate_learning_insights(metrics, trade_data, perfect_trade)
            metrics.learning_insights = insights
            
            # Store for learning
            self._store_quality_analysis(trade_data, metrics, perfect_trade)
            
            logger.info(f"✅ Trade quality analysis complete: {metrics.overall_quality:.1%} quality, {metrics.perfect_trade_score:.1%} perfect score")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Trade quality analysis failed: {e}")
            return self._create_default_metrics()
    
    def _find_perfect_trade(self, direction: str, entry_price: float, 
                           market_timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find the perfect imaginary trade in the given timeline"""
        try:
            if not market_timeline:
                return {"perfect_profit": 0, "perfect_tp": entry_price, "perfect_sl": entry_price}
            
            # Find the best possible outcome
            if direction == "BUY":
                # For BUY: find highest price after entry
                max_price = max(candle.get("high", entry_price) for candle in market_timeline)
                perfect_tp = max_price
                perfect_profit = max(0, max_price - entry_price)
            else:  # SELL
                # For SELL: find lowest price after entry
                min_price = min(candle.get("low", entry_price) for candle in market_timeline)
                perfect_tp = min_price
                perfect_profit = max(0, entry_price - min_price)
            
            # Perfect stop loss (never hit in the timeline)
            perfect_sl = entry_price  # No stop loss needed
            
            return {
                "perfect_profit": perfect_profit,
                "perfect_tp": perfect_tp,
                "perfect_sl": perfect_sl,
                "direction": direction,
                "entry_price": entry_price
            }
            
        except Exception as e:
            logger.error(f"❌ Perfect trade analysis failed: {e}")
            return {"perfect_profit": 0, "perfect_tp": entry_price, "perfect_sl": entry_price}
    
    def _calculate_quality_metrics(self, trade_data: Dict[str, Any], 
                                 perfect_trade: Dict[str, Any], 
                                 market_timeline: List[Dict[str, Any]]) -> TradeQualityMetrics:
        """Calculate detailed quality metrics"""
        try:
            # Direction accuracy (was the direction correct?)
            direction_accuracy = self._calculate_direction_accuracy(trade_data, market_timeline)
            
            # Entry timing accuracy (how close to predicted entry?)
            entry_timing_accuracy = self._calculate_entry_timing_accuracy(trade_data, market_timeline)
            
            # Take profit accuracy (how close to perfect TP?)
            take_profit_accuracy = self._calculate_take_profit_accuracy(trade_data, perfect_trade)
            
            # Stop loss accuracy (was SL needed?)
            stop_loss_accuracy = self._calculate_stop_loss_accuracy(trade_data, market_timeline)
            
            # Profit efficiency (actual vs perfect profit)
            profit_efficiency = self._calculate_profit_efficiency(trade_data, perfect_trade)
            
            # Overall quality (weighted average)
            overall_quality = (
                direction_accuracy * 0.3 +
                entry_timing_accuracy * 0.2 +
                take_profit_accuracy * 0.2 +
                stop_loss_accuracy * 0.1 +
                profit_efficiency * 0.2
            )
            
            # Perfect trade score (how close to perfect trade)
            perfect_trade_score = self._calculate_perfect_trade_score(
                direction_accuracy, take_profit_accuracy, profit_efficiency
            )
            
            return TradeQualityMetrics(
                direction_accuracy=direction_accuracy,
                entry_timing_accuracy=entry_timing_accuracy,
                take_profit_accuracy=take_profit_accuracy,
                stop_loss_accuracy=stop_loss_accuracy,
                profit_efficiency=profit_efficiency,
                overall_quality=overall_quality,
                perfect_trade_score=perfect_trade_score,
                learning_insights=[]
            )
            
        except Exception as e:
            logger.error(f"❌ Quality metrics calculation failed: {e}")
            return self._create_default_metrics()
    
    def _calculate_direction_accuracy(self, trade_data: Dict[str, Any], 
                                    market_timeline: List[Dict[str, Any]]) -> float:
        """Calculate if the direction was correct"""
        try:
            direction = trade_data.get("direction", "BUY")
            entry_price = trade_data.get("entry_price", 0)
            
            if not market_timeline or entry_price == 0:
                return 0.5
            
            # Check if price moved in predicted direction
            final_price = market_timeline[-1].get("close", entry_price)
            
            if direction == "BUY":
                return 1.0 if final_price > entry_price else 0.0
            else:  # SELL
                return 1.0 if final_price < entry_price else 0.0
                
        except Exception as e:
            logger.error(f"❌ Direction accuracy calculation failed: {e}")
            return 0.5
    
    def _calculate_entry_timing_accuracy(self, trade_data: Dict[str, Any], 
                                       market_timeline: List[Dict[str, Any]]) -> float:
        """Calculate how close the entry was to the predicted price"""
        try:
            predicted_entry = trade_data.get("predicted_entry_price", 0)
            actual_entry = trade_data.get("entry_price", 0)
            
            if predicted_entry == 0 or actual_entry == 0:
                return 0.5
            
            # Calculate accuracy based on price difference
            price_diff = abs(actual_entry - predicted_entry) / predicted_entry
            accuracy = max(0.0, 1.0 - (price_diff * 10))  # 10% price diff = 0% accuracy
            
            return accuracy
            
        except Exception as e:
            logger.error(f"❌ Entry timing accuracy calculation failed: {e}")
            return 0.5
    
    def _calculate_take_profit_accuracy(self, trade_data: Dict[str, Any], 
                                      perfect_trade: Dict[str, Any]) -> float:
        """Calculate how close the TP was to the perfect TP"""
        try:
            actual_tp = trade_data.get("take_profit", 0)
            perfect_tp = perfect_trade.get("perfect_tp", 0)
            entry_price = trade_data.get("entry_price", 0)
            
            if actual_tp == 0 or perfect_tp == 0 or entry_price == 0:
                return 0.5
            
            # Calculate accuracy based on how close to perfect TP
            if perfect_tp > entry_price:  # BUY trade
                actual_progress = (actual_tp - entry_price) / (perfect_tp - entry_price)
            else:  # SELL trade
                actual_progress = (entry_price - actual_tp) / (entry_price - perfect_tp)
            
            accuracy = max(0.0, min(1.0, actual_progress))
            
            return accuracy
            
        except Exception as e:
            logger.error(f"❌ Take profit accuracy calculation failed: {e}")
            return 0.5
    
    def _calculate_stop_loss_accuracy(self, trade_data: Dict[str, Any], 
                                    market_timeline: List[Dict[str, Any]]) -> float:
        """Calculate if the stop loss was needed"""
        try:
            stop_loss = trade_data.get("stop_loss", 0)
            entry_price = trade_data.get("entry_price", 0)
            direction = trade_data.get("direction", "BUY")
            
            if stop_loss == 0 or entry_price == 0:
                return 1.0  # No SL set, assume it was correct
            
            # Check if price ever went below/above SL
            if direction == "BUY":
                min_price = min(candle.get("low", entry_price) for candle in market_timeline)
                return 1.0 if min_price >= stop_loss else 0.0
            else:  # SELL
                max_price = max(candle.get("high", entry_price) for candle in market_timeline)
                return 1.0 if max_price <= stop_loss else 0.0
                
        except Exception as e:
            logger.error(f"❌ Stop loss accuracy calculation failed: {e}")
            return 0.5
    
    def _calculate_profit_efficiency(self, trade_data: Dict[str, Any], 
                                   perfect_trade: Dict[str, Any]) -> float:
        """Calculate profit efficiency (actual vs perfect profit)"""
        try:
            actual_profit = trade_data.get("result", 0)
            perfect_profit = perfect_trade.get("perfect_profit", 0)
            
            if perfect_profit == 0:
                return 1.0 if actual_profit >= 0 else 0.0
            
            efficiency = actual_profit / perfect_profit
            return max(0.0, min(1.0, efficiency))
            
        except Exception as e:
            logger.error(f"❌ Profit efficiency calculation failed: {e}")
            return 0.5
    
    def _calculate_perfect_trade_score(self, direction_accuracy: float, 
                                     take_profit_accuracy: float, 
                                     profit_efficiency: float) -> float:
        """Calculate how close to a perfect trade"""
        try:
            # Perfect trade requires all key elements to be excellent
            perfect_score = (
                direction_accuracy * 0.4 +
                take_profit_accuracy * 0.4 +
                profit_efficiency * 0.2
            )
            
            return perfect_score
            
        except Exception as e:
            logger.error(f"❌ Perfect trade score calculation failed: {e}")
            return 0.5
    
    def _generate_learning_insights(self, metrics: TradeQualityMetrics, 
                                  trade_data: Dict[str, Any], 
                                  perfect_trade: Dict[str, Any]) -> List[str]:
        """Generate learning insights for AI improvement"""
        try:
            insights = []
            
            # Direction insights
            if metrics.direction_accuracy < 0.5:
                insights.append("Direction was wrong - analyze signal quality")
            elif metrics.direction_accuracy > 0.8:
                insights.append("Direction was correct - reinforce signal patterns")
            
            # Take profit insights
            if metrics.take_profit_accuracy < 0.5:
                insights.append("TP was too conservative - aim for higher targets")
            elif metrics.take_profit_accuracy > 0.9:
                insights.append("TP was well positioned - maintain strategy")
            
            # Profit efficiency insights
            if metrics.profit_efficiency < 0.3:
                insights.append("Missed significant profit opportunity - optimize TP/SL")
            elif metrics.profit_efficiency > 0.8:
                insights.append("Excellent profit capture - replicate setup")
            
            # Perfect trade insights
            if metrics.perfect_trade_score > 0.9:
                insights.append("Near-perfect trade - use as template for future trades")
            elif metrics.perfect_trade_score < 0.3:
                insights.append("Poor trade quality - avoid similar setups")
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Learning insights generation failed: {e}")
            return ["Analysis failed - manual review needed"]
    
    def _store_quality_analysis(self, trade_data: Dict[str, Any], 
                               metrics: TradeQualityMetrics, 
                               perfect_trade: Dict[str, Any]):
        """Store quality analysis for AI learning"""
        try:
            analysis_data = {
                "trade_id": trade_data.get("trade_id", "unknown"),
                "timestamp": time.time(),
                "metrics": {
                    "direction_accuracy": metrics.direction_accuracy,
                    "entry_timing_accuracy": metrics.entry_timing_accuracy,
                    "take_profit_accuracy": metrics.take_profit_accuracy,
                    "stop_loss_accuracy": metrics.stop_loss_accuracy,
                    "profit_efficiency": metrics.profit_efficiency,
                    "overall_quality": metrics.overall_quality,
                    "perfect_trade_score": metrics.perfect_trade_score
                },
                "perfect_trade": perfect_trade,
                "learning_insights": metrics.learning_insights
            }
            
            self.quality_history.append(analysis_data)
            
            logger.debug(f"📊 Stored quality analysis for trade {trade_data.get('trade_id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store quality analysis: {e}")
    
    def _create_default_metrics(self) -> TradeQualityMetrics:
        """Create default metrics when analysis fails"""
        return TradeQualityMetrics(
            direction_accuracy=0.5,
            entry_timing_accuracy=0.5,
            take_profit_accuracy=0.5,
            stop_loss_accuracy=0.5,
            profit_efficiency=0.5,
            overall_quality=0.5,
            perfect_trade_score=0.5,
            learning_insights=["Analysis failed - manual review needed"]
        )
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learning insights from all trades"""
        try:
            if not self.quality_history:
                return {"message": "No trades analyzed yet"}
            
            # Calculate average metrics
            avg_quality = sum(t["metrics"]["overall_quality"] for t in self.quality_history) / len(self.quality_history)
            avg_perfect_score = sum(t["metrics"]["perfect_trade_score"] for t in self.quality_history) / len(self.quality_history)
            
            # Count perfect trades (score > 0.9)
            perfect_trades = sum(1 for t in self.quality_history if t["metrics"]["perfect_trade_score"] > 0.9)
            
            return {
                "total_trades_analyzed": len(self.quality_history),
                "average_quality": avg_quality,
                "average_perfect_score": avg_perfect_score,
                "perfect_trades_count": perfect_trades,
                "perfect_trades_percentage": (perfect_trades / len(self.quality_history)) * 100
            }
            
        except Exception as e:
            logger.error(f"❌ Learning summary generation failed: {e}")
            return {"error": "Failed to generate learning summary"}

# Global instance for easy access
trade_quality_analyzer = TradeQualityAnalyzer()
