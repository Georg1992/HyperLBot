#!/usr/bin/env python3
"""
Position Manager Module
Handles position management and analysis
"""

import time
import json
from typing import Dict, Any, List, Optional
from loguru import logger
from core.constants import constants
from core.execution.trading_execution import TradingExecution

class PositionManager:
    """Handles position management and analysis"""
    
    def __init__(self, bot_instance=None):
        self.bot_instance = bot_instance
        if bot_instance:
            self.trading_execution = TradingExecution(bot_instance)
        else:
            self.trading_execution = None
        logger.info("💰 Position Manager initialized")
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        try:
            if self.trading_execution:
                return self.trading_execution.get_open_positions()
            elif self.bot_instance:
                return self.bot_instance.get_open_positions()
            else:
                return []
        except Exception as e:
            logger.error(f"❌ Failed to get open positions: {e}")
            return []
    
    def get_position_by_id(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get position by ID"""
        try:
            positions = self.get_open_positions()
            for position in positions:
                if position.get("id") == position_id:
                    return position
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get position by ID {position_id}: {e}")
            return None
    
    def get_positions_by_side(self, side: str) -> List[Dict[str, Any]]:
        """Get positions by side (LONG/SHORT)"""
        try:
            positions = self.get_open_positions()
            return [pos for pos in positions if pos.get("side") == side]
        except Exception as e:
            logger.error(f"❌ Failed to get positions by side {side}: {e}")
            return []
    
    def get_total_position_value(self) -> float:
        """Get total value of all open positions"""
        try:
            positions = self.get_open_positions()
            total_value = 0.0
            
            for position in positions:
                size = position.get("size", 0)
                entry_price = position.get("entry_price", 0)
                total_value += size * entry_price
            
            return total_value
        except Exception as e:
            logger.error(f"❌ Failed to calculate total position value: {e}")
            return 0.0
    
    def get_position_pnl(self, position: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Calculate P&L for a position"""
        try:
            side = position.get("side", "UNKNOWN")
            size = position.get("size", 0)
            entry_price = position.get("entry_price", 0)
            
            if side == "LONG":
                pnl = (current_price - entry_price) * size
                pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
            elif side == "SHORT":
                pnl = (entry_price - current_price) * size
                pnl_pct = ((entry_price - current_price) / entry_price) * 100 if entry_price > 0 else 0
            else:
                pnl = 0
                pnl_pct = 0
            
            return {
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "side": side,
                "size": size,
                "entry_price": entry_price,
                "current_price": current_price
            }
        except Exception as e:
            logger.error(f"❌ Failed to calculate position P&L: {e}")
            return {
                "pnl": 0,
                "pnl_pct": 0,
                "side": "UNKNOWN",
                "size": 0,
                "entry_price": 0,
                "current_price": current_price
            }
    
    def get_total_pnl(self, current_price: float) -> Dict[str, Any]:
        """Calculate total P&L for all positions"""
        try:
            positions = self.get_open_positions()
            total_pnl = 0.0
            total_pnl_pct = 0.0
            position_pnls = []
            
            for position in positions:
                pnl_data = self.get_position_pnl(position, current_price)
                total_pnl += pnl_data["pnl"]
                position_pnls.append({
                    "id": position.get("id"),
                    "side": position.get("side"),
                    "pnl": pnl_data["pnl"],
                    "pnl_pct": pnl_data["pnl_pct"]
                })
            
            # Calculate weighted average P&L percentage
            total_value = self.get_total_position_value()
            if total_value > 0:
                total_pnl_pct = (total_pnl / total_value) * 100
            
            return {
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
                "total_position_value": total_value,
                "position_count": len(positions),
                "position_pnls": position_pnls
            }
        except Exception as e:
            logger.error(f"❌ Failed to calculate total P&L: {e}")
            return {
                "total_pnl": 0,
                "total_pnl_pct": 0,
                "total_position_value": 0,
                "position_count": 0,
                "position_pnls": []
            }
    
    def should_close_position(self, position: Dict[str, Any], current_price: float, 
                            prediction_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if a position should be closed"""
        try:
            # Get position P&L
            pnl_data = self.get_position_pnl(position, current_price)
            pnl = pnl_data["pnl"]
            pnl_pct = pnl_data["pnl_pct"]
            
            # Get prediction
            prediction = prediction_analysis.get("best_prediction", {})
            prediction_side = prediction.get("side", "UNKNOWN")
            position_side = position.get("side", "UNKNOWN")
            
            # Check stop loss
            stop_price = position.get("stop_price", 0)
            if stop_price > 0:
                if position_side == "LONG" and current_price <= stop_price:
                    return {
                        "should_close": True,
                        "reason": "Stop loss triggered",
                        "pnl": pnl,
                        "pnl_pct": pnl_pct
                    }
                elif position_side == "SHORT" and current_price >= stop_price:
                    return {
                        "should_close": True,
                        "reason": "Stop loss triggered",
                        "pnl": pnl,
                        "pnl_pct": pnl_pct
                    }
            
            # Check take profit
            target_price = position.get("target_price", 0)
            if target_price > 0:
                if position_side == "LONG" and current_price >= target_price:
                    return {
                        "should_close": True,
                        "reason": "Take profit reached",
                        "pnl": pnl,
                        "pnl_pct": pnl_pct
                    }
                elif position_side == "SHORT" and current_price <= target_price:
                    return {
                        "should_close": True,
                        "reason": "Take profit reached",
                        "pnl": pnl,
                        "pnl_pct": pnl_pct
                    }
            
            # Check signal reversal
            if prediction_side != "UNKNOWN" and prediction_side != position_side:
                confidence = prediction.get("confidence", 0)
                if confidence > 0.7:  # High confidence reversal
                    return {
                        "should_close": True,
                        "reason": f"Signal reversal: {prediction_side}",
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "confidence": confidence
                    }
            
            # Check time-based exit
            entry_time = position.get("entry_time", 0)
            if entry_time > 0:
                time_held = time.time() - entry_time
                max_hold_time = constants.MAX_HOLD_TIME
                if time_held > max_hold_time:
                    return {
                        "should_close": True,
                        "reason": f"Max hold time exceeded: {time_held/3600:.1f}h",
                        "pnl": pnl,
                        "pnl_pct": pnl_pct
                    }
            
            return {
                "should_close": False,
                "reason": "Position conditions met",
                "pnl": pnl,
                "pnl_pct": pnl_pct
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to determine if position should close: {e}")
            return {
                "should_close": False,
                "reason": f"Error: {str(e)}",
                "pnl": 0,
                "pnl_pct": 0
            }
    
    def close_position(self, position_id: str, reason: str = "Manual close") -> bool:
        """Close a specific position"""
        try:
            if self.trading_execution:
                return self.trading_execution.close_paper_position(position_id, reason)
            elif self.bot_instance:
                # Find position and close it through bot
                positions = self.bot_instance.get_open_positions()
                for position in positions:
                    if position.get("id") == position_id:
                        return self.bot_instance.close_paper_position(position, reason, 0)  # 0 as exit_price placeholder
                return False
            else:
                return False
        except Exception as e:
            logger.error(f"❌ Failed to close position {position_id}: {e}")
            return False
    
    def close_all_positions(self, reason: str = "Bulk close") -> Dict[str, Any]:
        """Close all open positions"""
        try:
            positions = self.get_open_positions()
            closed_count = 0
            failed_count = 0
            
            for position in positions:
                position_id = position.get("id")
                if self.close_position(position_id, reason):
                    closed_count += 1
                else:
                    failed_count += 1
            
            return {
                "total_positions": len(positions),
                "closed_count": closed_count,
                "failed_count": failed_count,
                "success": failed_count == 0
            }
        except Exception as e:
            logger.error(f"❌ Failed to close all positions: {e}")
            return {
                "total_positions": 0,
                "closed_count": 0,
                "failed_count": 0,
                "success": False,
                "error": str(e)
            }
    
    def get_position_summary(self, current_price: float) -> Dict[str, Any]:
        """Get summary of all positions"""
        try:
            positions = self.get_open_positions()
            total_pnl_data = self.get_total_pnl(current_price)
            
            # Count positions by side
            long_positions = len([p for p in positions if p.get("side") == "LONG"])
            short_positions = len([p for p in positions if p.get("side") == "SHORT"])
            
            return {
                "total_positions": len(positions),
                "long_positions": long_positions,
                "short_positions": short_positions,
                "total_pnl": total_pnl_data["total_pnl"],
                "total_pnl_pct": total_pnl_data["total_pnl_pct"],
                "total_position_value": total_pnl_data["total_position_value"],
                "average_pnl_per_position": total_pnl_data["total_pnl"] / len(positions) if positions else 0,
                "positions": positions
            }
        except Exception as e:
            logger.error(f"❌ Failed to get position summary: {e}")
            return {
                "total_positions": 0,
                "long_positions": 0,
                "short_positions": 0,
                "total_pnl": 0,
                "total_pnl_pct": 0,
                "total_position_value": 0,
                "average_pnl_per_position": 0,
                "positions": []
            }
