#!/usr/bin/env python3
"""
Trade Outcome Recorder - Records trade results for confidence optimization
Feeds trade outcomes back to the confidence optimizer for continuous improvement
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger
from core.ml.confidence_optimizer import get_global_confidence_optimizer, TradeRecord
from core.ml.adaptive_confidence_calculator import get_global_adaptive_calculator


@dataclass
class TradeOutcome:
    """Trade outcome data for optimization"""
    trade_id: str
    direction: str
    entry_price: float
    exit_price: float
    entry_time: float
    exit_time: float
    profit_loss: float
    profit_loss_pct: float
    hold_time_seconds: float
    confidence_at_entry: float
    market_data_at_entry: Dict[str, Any]
    factors_at_entry: Dict[str, float]


class TradeOutcomeRecorder:
    """
    Records trade outcomes and feeds them to the confidence optimizer
    
    Features:
    1. Records trade entry and exit data
    2. Calculates performance metrics
    3. Feeds data to confidence optimizer
    4. Tracks optimization progress
    """
    
    def __init__(self):
        self.optimizer = get_global_confidence_optimizer()
        self.adaptive_calculator = get_global_adaptive_calculator()
        
        # Track pending trades
        self.pending_trades: Dict[str, Dict[str, Any]] = {}
        
        logger.info("📊 Trade Outcome Recorder initialized")
    
    def record_trade_entry(self, trade_id: str, direction: str, entry_price: float,
                          confidence: float, market_data: Dict[str, Any], 
                          factors: Dict[str, float]) -> None:
        """Record trade entry for future outcome tracking"""
        try:
            self.pending_trades[trade_id] = {
                "direction": direction,
                "entry_price": entry_price,
                "entry_time": time.time(),
                "confidence_at_entry": confidence,
                "market_data_at_entry": market_data.copy(),
                "factors_at_entry": factors.copy()
            }
            
            logger.debug(f"📝 Recorded trade entry: {trade_id} {direction} @ ${entry_price:,.2f} ({confidence:.1%})")
            
        except Exception as e:
            logger.error(f"❌ Failed to record trade entry: {e}")
    
    def record_trade_exit(self, trade_id: str, exit_price: float, 
                         exit_reason: str = "MANUAL") -> Optional[TradeOutcome]:
        """Record trade exit and create outcome record"""
        try:
            if trade_id not in self.pending_trades:
                logger.warning(f"⚠️ No pending trade found for ID: {trade_id}")
                return None
            
            trade_data = self.pending_trades[trade_id]
            entry_time = trade_data["entry_time"]
            exit_time = time.time()
            hold_time = exit_time - entry_time
            
            # Calculate P&L
            entry_price = trade_data["entry_price"]
            direction = trade_data["direction"]
            
            if direction == "LONG":
                profit_loss = exit_price - entry_price
            else:  # SHORT
                profit_loss = entry_price - exit_price
            
            profit_loss_pct = profit_loss / entry_price
            
            # Determine outcome
            if profit_loss > 0:
                outcome = "WIN"
            elif profit_loss < 0:
                outcome = "LOSS"
            else:
                outcome = "BREAKEVEN"
            
            # Create trade outcome record
            trade_outcome = TradeOutcome(
                trade_id=trade_id,
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                entry_time=entry_time,
                exit_time=exit_time,
                profit_loss=profit_loss,
                profit_loss_pct=profit_loss_pct,
                hold_time_seconds=hold_time,
                confidence_at_entry=trade_data["confidence_at_entry"],
                market_data_at_entry=trade_data["market_data_at_entry"],
                factors_at_entry=trade_data["factors_at_entry"]
            )
            
            # Feed to optimizer
            self._feed_to_optimizer(trade_outcome)
            
            # Clean up pending trade
            del self.pending_trades[trade_id]
            
            logger.info(f"📊 Trade outcome: {outcome} {direction} {profit_loss_pct:+.2%} (hold: {hold_time/60:.1f}m)")
            
            return trade_outcome
            
        except Exception as e:
            logger.error(f"❌ Failed to record trade exit: {e}")
            return None
    
    def _feed_to_optimizer(self, trade_outcome: TradeOutcome) -> None:
        """Feed trade outcome to the confidence optimizer"""
        try:
            # Create trade record for optimizer
            trade_record = TradeRecord(
                timestamp=trade_outcome.entry_time,
                direction=trade_outcome.direction,
                confidence=trade_outcome.confidence_at_entry,
                market_data=trade_outcome.market_data_at_entry,
                outcome=trade_outcome.profit_loss > 0 and "WIN" or "LOSS",
                profit_loss=trade_outcome.profit_loss,
                hold_time=trade_outcome.hold_time_seconds,
                factors=trade_outcome.factors_at_entry
            )
            
            # Add to optimizer
            self.optimizer.add_trade_record(trade_record)
            
            # Also add to adaptive calculator
            self.adaptive_calculator.record_trade_outcome(trade_record)
            
            logger.debug(f"🔄 Fed trade outcome to optimizer: {trade_outcome.direction} {trade_outcome.profit_loss_pct:+.2%}")
            
        except Exception as e:
            logger.error(f"❌ Failed to feed trade outcome to optimizer: {e}")
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status"""
        try:
            performance_summary = self.adaptive_calculator.get_performance_summary()
            
            return {
                "total_trades": performance_summary.get("total_trades", 0),
                "optimization_available": performance_summary.get("optimization_available", False),
                "optimal_threshold": performance_summary.get("optimal_threshold", 0.6),
                "pending_trades": len(self.pending_trades),
                "model_performance": performance_summary.get("model_performance", {}),
                "range_performance": performance_summary.get("range_performance", {})
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get optimization status: {e}")
            return {
                "total_trades": 0,
                "optimization_available": False,
                "optimal_threshold": 0.6,
                "pending_trades": 0,
                "model_performance": {},
                "range_performance": {}
            }
    
    def trigger_optimization(self) -> bool:
        """Manually trigger confidence optimization"""
        try:
            logger.info("🔄 Manually triggering confidence optimization...")
            self.optimizer.optimize_confidence_calculation()
            logger.success("✅ Manual optimization completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Manual optimization failed: {e}")
            return False
    
    def get_optimal_threshold(self) -> float:
        """Get current optimal confidence threshold"""
        return self.adaptive_calculator.get_optimal_threshold()


# Global recorder instance
_global_trade_outcome_recorder = None

def get_global_trade_outcome_recorder() -> TradeOutcomeRecorder:
    """Get global trade outcome recorder singleton"""
    global _global_trade_outcome_recorder
    if _global_trade_outcome_recorder is None:
        _global_trade_outcome_recorder = TradeOutcomeRecorder()
    return _global_trade_outcome_recorder
