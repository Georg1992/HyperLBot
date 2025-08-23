#!/usr/bin/env python3
"""
Real-Time P&L Tracker
Tracks open positions and calculates real-time unrealized P&L
"""

import time
import json
from typing import Dict, Any, List, Optional
from loguru import logger
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict

@dataclass
class OpenPosition:
    """Open trading position with real-time P&L tracking"""
    position_id: str
    symbol: str
    side: str  # BUY or SELL
    entry_price: float
    size: float  # Position size in BTC
    entry_time: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: float = 1.0
    entry_value: float = 0.0  # USD value at entry
    
    def __post_init__(self):
        if self.entry_value == 0.0:
            self.entry_value = self.entry_price * self.size

class RealTimePnLTracker:
    """Track and calculate real-time P&L for open positions"""
    
    def __init__(self, initial_balance: float = 120.0):
        self.initial_balance = initial_balance
        self.realized_pnl = 0.0  # Closed trades P&L
        self.open_positions: Dict[str, OpenPosition] = {}
        
        # P&L tracking
        self.pnl_history = []
        self.max_balance = initial_balance
        self.max_drawdown = 0.0
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        logger.info(f"💰 Real-Time P&L Tracker initialized with ${initial_balance:.2f}")
    
    def add_position(self, position: OpenPosition) -> bool:
        """Add new open position"""
        try:
            self.open_positions[position.position_id] = position
            logger.info(f"📈 Added position: {position.side} {position.size:.4f} BTC @ ${position.entry_price:,.2f}")
            return True
        except Exception as e:
            logger.error(f"Failed to add position: {e}")
            return False
    
    def close_position(self, position_id: str, exit_price: float, exit_time: float = None) -> Dict[str, Any]:
        """Close position and calculate realized P&L"""
        if position_id not in self.open_positions:
            logger.warning(f"Position {position_id} not found")
            return {"success": False, "error": "Position not found"}
        
        position = self.open_positions[position_id]
        exit_time = exit_time or time.time()
        
        # Calculate realized P&L
        if position.side == "BUY":
            pnl = (exit_price - position.entry_price) * position.size
        else:  # SELL
            pnl = (position.entry_price - exit_price) * position.size
        
        # Apply leverage
        pnl *= position.leverage
        
        # Update realized P&L
        self.realized_pnl += pnl
        
        # Update trade statistics
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Calculate trade duration
        duration = exit_time - position.entry_time
        
        # Remove from open positions
        del self.open_positions[position_id]
        
        trade_result = {
            "success": True,
            "position_id": position_id,
            "side": position.side,
            "symbol": position.symbol,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "size": position.size,
            "pnl": pnl,
            "pnl_percentage": (pnl / position.entry_value) * 100,
            "duration": duration,
            "duration_minutes": duration / 60,
            "realized_pnl": self.realized_pnl
        }
        
        logger.info(f"💰 Closed position: {pnl:+.2f} USD ({trade_result['pnl_percentage']:+.2f}%) in {trade_result['duration_minutes']:.1f}m")
        
        return trade_result
    
    def calculate_unrealized_pnl(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """Calculate unrealized P&L for all open positions"""
        total_unrealized = 0.0
        position_pnls = {}
        
        for pos_id, position in self.open_positions.items():
            current_price = current_prices.get(position.symbol, position.entry_price)
            
            # Calculate unrealized P&L
            if position.side == "BUY":
                unrealized = (current_price - position.entry_price) * position.size
            else:  # SELL
                unrealized = (position.entry_price - current_price) * position.size
            
            # Apply leverage
            unrealized *= position.leverage
            
            # Calculate percentage
            unrealized_pct = (unrealized / position.entry_value) * 100
            
            position_pnls[pos_id] = {
                "position": position,
                "current_price": current_price,
                "unrealized_pnl": unrealized,
                "unrealized_pct": unrealized_pct,
                "current_value": position.entry_value + unrealized
            }
            
            total_unrealized += unrealized
        
        return {
            "total_unrealized_pnl": total_unrealized,
            "position_details": position_pnls,
            "total_positions": len(self.open_positions)
        }
    
    def get_current_balance(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """Get current balance including unrealized P&L"""
        unrealized_data = self.calculate_unrealized_pnl(current_prices)
        unrealized_pnl = unrealized_data["total_unrealized_pnl"]
        
        current_balance = self.initial_balance + self.realized_pnl + unrealized_pnl
        total_pnl = self.realized_pnl + unrealized_pnl
        total_pnl_pct = (total_pnl / self.initial_balance) * 100
        
        # Update max balance and drawdown
        if current_balance > self.max_balance:
            self.max_balance = current_balance
        
        current_drawdown = (self.max_balance - current_balance) / self.max_balance
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Add to P&L history
        pnl_snapshot = {
            "timestamp": time.time(),
            "balance": current_balance,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_pnl,
            "open_positions": len(self.open_positions)
        }
        self.pnl_history.append(pnl_snapshot)
        
        # Keep only last 1000 snapshots
        if len(self.pnl_history) > 1000:
            self.pnl_history = self.pnl_history[-1000:]
        
        return {
            "current_balance": current_balance,
            "initial_balance": self.initial_balance,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_pnl,
            "total_pnl_percentage": total_pnl_pct,
            "max_balance": self.max_balance,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percentage": self.max_drawdown * 100,
            "open_positions_count": len(self.open_positions),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            "balance_source": "real_time_pnl",
            "last_updated": time.time()
        }
    
    def get_position_summary(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get summary of all open positions with current P&L"""
        unrealized_data = self.calculate_unrealized_pnl(current_prices)
        position_summaries = []
        
        for pos_id, position in self.open_positions.items():
            pnl_data = unrealized_data["position_details"].get(pos_id, {})
            
            summary = {
                "position_id": pos_id,
                "symbol": position.symbol,
                "side": position.side,
                "size": position.size,
                "entry_price": position.entry_price,
                "current_price": pnl_data.get("current_price", position.entry_price),
                "unrealized_pnl": pnl_data.get("unrealized_pnl", 0),
                "unrealized_pct": pnl_data.get("unrealized_pct", 0),
                "entry_time": position.entry_time,
                "duration": time.time() - position.entry_time,
                "duration_hours": (time.time() - position.entry_time) / 3600,
                "stop_loss": position.stop_loss,
                "take_profit": position.take_profit,
                "leverage": position.leverage,
                "entry_value": position.entry_value,
                "current_value": pnl_data.get("current_value", position.entry_value)
            }
            
            position_summaries.append(summary)
        
        # Sort by unrealized P&L (best performing first)
        position_summaries.sort(key=lambda x: x["unrealized_pnl"], reverse=True)
        
        return position_summaries
    
    def check_stop_loss_take_profit(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """Check if any positions hit stop loss or take profit"""
        triggered_positions = []
        
        for pos_id, position in self.open_positions.items():
            current_price = current_prices.get(position.symbol, position.entry_price)
            
            should_close = False
            trigger_reason = ""
            
            if position.side == "BUY":
                if position.stop_loss and current_price <= position.stop_loss:
                    should_close = True
                    trigger_reason = "stop_loss"
                elif position.take_profit and current_price >= position.take_profit:
                    should_close = True
                    trigger_reason = "take_profit"
            else:  # SELL
                if position.stop_loss and current_price >= position.stop_loss:
                    should_close = True
                    trigger_reason = "stop_loss"
                elif position.take_profit and current_price <= position.take_profit:
                    should_close = True
                    trigger_reason = "take_profit"
            
            if should_close:
                triggered_positions.append({
                    "position_id": pos_id,
                    "position": position,
                    "current_price": current_price,
                    "trigger_reason": trigger_reason,
                    "trigger_price": position.stop_loss if trigger_reason == "stop_loss" else position.take_profit
                })
        
        return triggered_positions
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        if not self.pnl_history:
            return {"error": "No P&L history available"}
        
        # Calculate metrics from P&L history
        balances = [snapshot["balance"] for snapshot in self.pnl_history]
        returns = [(balances[i] - balances[i-1]) / balances[i-1] for i in range(1, len(balances))]
        
        if returns:
            avg_return = sum(returns) / len(returns)
            volatility = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = avg_return / volatility if volatility > 0 else 0
        else:
            avg_return = volatility = sharpe_ratio = 0
        
        return {
            "total_return": (balances[-1] - balances[0]) / balances[0] * 100,
            "avg_daily_return": avg_return * 100,
            "volatility": volatility * 100,
            "sharpe_ratio": sharpe_ratio,
            "max_balance": self.max_balance,
            "max_drawdown_pct": self.max_drawdown * 100,
            "profit_factor": self._calculate_profit_factor(),
            "total_trades": self.total_trades,
            "win_rate": (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            "avg_trade_duration": self._calculate_avg_trade_duration()
        }
    
    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        if not self.pnl_history:
            return 1.0
        
        gross_profit = sum(max(0, snapshot["total_pnl"] - (self.pnl_history[i-1]["total_pnl"] if i > 0 else 0)) 
                          for i, snapshot in enumerate(self.pnl_history))
        gross_loss = sum(max(0, -(snapshot["total_pnl"] - (self.pnl_history[i-1]["total_pnl"] if i > 0 else 0))) 
                        for i, snapshot in enumerate(self.pnl_history))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def _calculate_avg_trade_duration(self) -> float:
        """Calculate average trade duration in minutes"""
        # This would require storing closed trade data
        return 0.0  # Placeholder
    
    def export_data(self) -> Dict[str, Any]:
        """Export all tracking data"""
        return {
            "initial_balance": self.initial_balance,
            "realized_pnl": self.realized_pnl,
            "open_positions": {k: asdict(v) for k, v in self.open_positions.items()},
            "pnl_history": self.pnl_history[-100:],  # Last 100 snapshots
            "performance_metrics": self.get_performance_metrics(),
            "export_timestamp": time.time()
        }