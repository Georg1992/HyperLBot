#!/usr/bin/env python3
"""
Trade State Manager
Robust trade persistence and state management for bot sessions
"""

import os
import json
import time
import threading
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
from loguru import logger


class TradeStateManager:
    """Manages trade state persistence and real-time synchronization"""
    
    def __init__(self):
        self.lock = threading.RLock()
        
        # Separate storage files for different data types
        self.files = {
            "open_positions": "data/open_positions.json",
            "trade_history": "data/accounts/trade_history.json", 
            "pending_orders": "data/accounts/pending_orders.json",
            "session_state": "data/accounts/session_state.json"
        }
        
        # Ensure data directories exist
        os.makedirs("data/accounts", exist_ok=True)
        os.makedirs("data/cache", exist_ok=True)
        os.makedirs("data/temp", exist_ok=True)
        os.makedirs("data/logs", exist_ok=True)
        
        # Trade data validation schema
        self.trade_schema = {
            "required_fields": [
                "trade_id", "account_id", "symbol", "side", "entry_price", "size", 
                "entry_time", "status", "strategy", "confidence"
            ],
            "optional_fields": [
                "exit_price", "exit_time", "stop_loss", "take_profit",
                "pnl", "pnl_pct", "fees", "exit_reason", "leverage"
            ],
            "defaults": {
                "symbol": "BTC",
                "leverage": 1.0,
                "fees": 0.0,
                "pnl": 0.0,
                "pnl_pct": 0.0,
                "exit_reason": "UNKNOWN",
                "confidence": 0.0,
                "account_id": "default_account",
                "strategy": "standard"
            }
        }
        
        logger.info("📊 Trade State Manager initialized")
    
    def validate_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean trade data"""
        try:
            # Check required fields
            for field in self.trade_schema["required_fields"]:
                if field not in trade or trade[field] is None:
                    if field in self.trade_schema["defaults"]:
                        trade[field] = self.trade_schema["defaults"][field]
                    else:
                        raise ValueError(f"Missing required field: {field}")
            
            # Apply defaults for missing optional fields
            for field, default_value in self.trade_schema["defaults"].items():
                if field not in trade or trade[field] is None:
                    trade[field] = default_value
            
            # Ensure numeric fields are proper numbers
            numeric_fields = ["entry_price", "size", "leverage", "confidence", "pnl", "pnl_pct", "fees"]
            for field in numeric_fields:
                if field in trade:
                    try:
                        trade[field] = float(trade[field]) if trade[field] is not None else 0.0
                    except (ValueError, TypeError):
                        trade[field] = 0.0
            
            # Ensure timestamps are present
            if "entry_time" not in trade or not trade["entry_time"]:
                trade["entry_time"] = time.time()
            
            # Generate trade_id if missing
            if not trade.get("trade_id"):
                trade["trade_id"] = f"trade_{int(time.time())}_{trade.get('side', 'unknown')}"
            
            return trade
            
        except Exception as e:
            logger.error(f"Trade validation failed: {e}")
            logger.error(f"Trade data: {trade}")
            return None
    
    def load_open_positions(self, account_id: str = None) -> List[Dict[str, Any]]:
        """Load open positions with validation, optionally filtered by account"""
        with self.lock:
            try:
                if os.path.exists(self.files["open_positions"]):
                    with open(self.files["open_positions"], 'r') as f:
                        positions = json.load(f)
                    
                    # Validate and clean each position
                    valid_positions = []
                    for pos in positions:
                        validated_pos = self.validate_trade(pos)
                        if validated_pos and validated_pos.get("status") == "OPEN":
                            # Filter by account if specified
                            if account_id and validated_pos.get("account_id") != account_id:
                                continue
                            
                            # Check if position isn't too old (24 hours max)
                            entry_time = validated_pos.get("entry_time", 0)
                            if time.time() - entry_time < 86400:
                                valid_positions.append(validated_pos)
                            else:
                                logger.warning(f"⚠️ Removing stale position: {validated_pos.get('trade_id')}")
                    
                    logger.info(f"📂 Loaded {len(valid_positions)} valid open positions{f' for account {account_id}' if account_id else ''}")
                    return valid_positions
                
                return []
                
            except Exception as e:
                logger.error(f"Error loading open positions: {e}")
                return []
    
    def save_open_positions(self, positions: List[Dict[str, Any]]):
        """Save open positions"""
        with self.lock:
            try:
                # Validate all positions before saving
                valid_positions = []
                for pos in positions:
                    validated_pos = self.validate_trade(pos)
                    if validated_pos and validated_pos.get("status") == "OPEN":
                        valid_positions.append(validated_pos)
                
                with open(self.files["open_positions"], 'w') as f:
                    json.dump(valid_positions, f, indent=2)
                
                logger.debug(f"💾 Saved {len(valid_positions)} open positions")
                
            except Exception as e:
                logger.error(f"Error saving open positions: {e}")
    
    def load_trade_history(self, limit: int = 100, account_id: str = None) -> List[Dict[str, Any]]:
        """Load trade history with validation, optionally filtered by account"""
        with self.lock:
            try:
                if os.path.exists(self.files["trade_history"]):
                    with open(self.files["trade_history"], 'r') as f:
                        trades = json.load(f)
                    
                    # Validate and clean each trade
                    valid_trades = []
                    for trade in trades:
                        validated_trade = self.validate_trade(trade)
                        if validated_trade:
                            # Filter by account if specified
                            if account_id and validated_trade.get("account_id") != account_id:
                                continue
                            valid_trades.append(validated_trade)
                    
                    # Sort by entry time (newest first) and limit
                    valid_trades.sort(key=lambda x: x.get("entry_time", 0), reverse=True)
                    
                    logger.info(f"📂 Loaded {len(valid_trades[:limit])} trade history entries{f' for account {account_id}' if account_id else ''}")
                    return valid_trades[:limit]
                
                return []
                
            except Exception as e:
                logger.error(f"Error loading trade history: {e}")
                return []
    
    def save_completed_trade(self, trade: Dict[str, Any]):
        """Save a completed trade to history"""
        with self.lock:
            try:
                # Validate trade data
                validated_trade = self.validate_trade(trade)
                if not validated_trade:
                    logger.error("❌ Cannot save invalid trade to history")
                    return False
                
                # Ensure trade is marked as completed
                validated_trade["status"] = "CLOSED"
                validated_trade["completion_time"] = time.time()
                
                # Load existing history
                trade_history = self.load_trade_history(1000)  # Keep last 1000 trades
                
                # Add new trade
                trade_history.insert(0, validated_trade)
                
                # Save back to file
                with open(self.files["trade_history"], 'w') as f:
                    json.dump(trade_history, f, indent=2)
                
                logger.info(f"💾 Saved completed trade to history: {validated_trade['trade_id']}")
                return True
                
            except Exception as e:
                logger.error(f"Error saving completed trade: {e}")
                return False
    
    def update_position(self, trade_id: str, updates: Dict[str, Any]) -> bool:
        """Update an open position"""
        with self.lock:
            try:
                positions = self.load_open_positions()
                
                # Find and update position
                updated = False
                for i, pos in enumerate(positions):
                    if pos.get("trade_id") == trade_id:
                        # Apply updates
                        for key, value in updates.items():
                            pos[key] = value
                        
                        # Re-validate updated position
                        validated_pos = self.validate_trade(pos)
                        if validated_pos:
                            positions[i] = validated_pos
                            updated = True
                        break
                
                if updated:
                    self.save_open_positions(positions)
                    logger.info(f"✅ Updated position: {trade_id}")
                    return True
                else:
                    logger.warning(f"⚠️ Position not found for update: {trade_id}")
                    return False
                
            except Exception as e:
                logger.error(f"Error updating position: {e}")
                return False
    
    def close_position(self, trade_id: str, exit_data: Dict[str, Any]) -> bool:
        """Close a position and move to history"""
        with self.lock:
            try:
                positions = self.load_open_positions()
                
                # Find position to close
                position_to_close = None
                remaining_positions = []
                
                for pos in positions:
                    if pos.get("trade_id") == trade_id:
                        position_to_close = pos.copy()
                        # Apply exit data
                        position_to_close.update(exit_data)
                        position_to_close["status"] = "CLOSED"
                        position_to_close["exit_time"] = time.time()
                    else:
                        remaining_positions.append(pos)
                
                if position_to_close:
                    # Save to history
                    if self.save_completed_trade(position_to_close):
                        # Update open positions (remove closed position)
                        self.save_open_positions(remaining_positions)
                        logger.success(f"✅ Closed position: {trade_id}")
                        return True
                    else:
                        logger.error(f"❌ Failed to save closed position to history")
                        return False
                else:
                    logger.warning(f"⚠️ Position not found for closing: {trade_id}")
                    return False
                
            except Exception as e:
                logger.error(f"Error closing position: {e}")
                return False
    
    def cleanup_phantom_trades(self):
        """Remove phantom/incomplete trades"""
        with self.lock:
            try:
                logger.info("🧹 Cleaning up phantom trades...")
                
                # Clean open positions
                positions = self.load_open_positions()
                original_count = len(positions)
                
                # Filter out phantom trades
                clean_positions = []
                for pos in positions:
                    if (pos.get("entry_price", 0) > 0 and 
                        pos.get("size", 0) > 0 and 
                        pos.get("trade_id") and 
                        pos.get("symbol")):
                        clean_positions.append(pos)
                    else:
                        logger.warning(f"🗑️ Removing phantom position: {pos}")
                
                if len(clean_positions) != original_count:
                    self.save_open_positions(clean_positions)
                    logger.success(f"✅ Cleaned {original_count - len(clean_positions)} phantom positions")
                
                # Clean trade history
                trade_history = self.load_trade_history(1000)
                original_history_count = len(trade_history)
                
                clean_history = []
                for trade in trade_history:
                    if (trade.get("entry_price", 0) > 0 and 
                        trade.get("size", 0) > 0 and 
                        trade.get("trade_id") and 
                        trade.get("symbol")):
                        clean_history.append(trade)
                    else:
                        logger.warning(f"🗑️ Removing phantom trade from history: {trade.get('trade_id', 'unknown')}")
                
                if len(clean_history) != original_history_count:
                    with open(self.files["trade_history"], 'w') as f:
                        json.dump(clean_history, f, indent=2)
                    logger.success(f"✅ Cleaned {original_history_count - len(clean_history)} phantom trades from history")
                
            except Exception as e:
                logger.error(f"Error during phantom trade cleanup: {e}")
    
    def get_dashboard_trade_data(self, account_id: str = None) -> List[Dict[str, Any]]:
        """Get formatted trade data for dashboard display, optionally filtered by account"""
        try:
            # Get recent completed trades
            trade_history = self.load_trade_history(50, account_id)
            
            # Get current open positions  
            open_positions = self.load_open_positions(account_id)
            
            # Combine and format for dashboard
            dashboard_trades = []
            
            # Add completed trades
            for trade in trade_history:
                dashboard_trade = {
                    "id": trade.get("trade_id", "unknown"),
                    "side": trade.get("side", "UNKNOWN"),
                    "symbol": trade.get("symbol", "BTC"),
                    "status": "CLOSED",
                    "entry_price": trade.get("entry_price", 0),
                    "exit_price": trade.get("exit_price", 0),
                    "size": trade.get("size", 0),
                    "timestamp": datetime.fromtimestamp(trade.get("entry_time", time.time())).isoformat(),
                    "type": "MARKET",
                    "pnl": trade.get("pnl", 0),
                    "pnl_pct": trade.get("pnl_pct", 0),
                    "confidence": trade.get("confidence", 0) * 100,
                    "exit_reason": trade.get("exit_reason", "UNKNOWN"),
                    "holding_time": trade.get("exit_time", 0) - trade.get("entry_time", 0),
                    "account_id": trade.get("account_id", "unknown")
                }
                dashboard_trades.append(dashboard_trade)
            
            # Add open positions
            for pos in open_positions:
                dashboard_trade = {
                    "id": pos.get("trade_id", "unknown"),
                    "side": pos.get("side", "UNKNOWN"),
                    "symbol": pos.get("symbol", "BTC"),
                    "status": "OPEN",
                    "entry_price": pos.get("entry_price", 0),
                    "exit_price": 0,
                    "size": pos.get("size", 0),
                    "timestamp": datetime.fromtimestamp(pos.get("entry_time", time.time())).isoformat(),
                    "type": "MARKET",
                    "pnl": pos.get("pnl", 0),
                    "pnl_pct": pos.get("pnl_pct", 0),
                    "confidence": pos.get("confidence", 0) * 100,
                    "exit_reason": "OPEN",
                    "holding_time": time.time() - pos.get("entry_time", time.time()),
                    "account_id": pos.get("account_id", "unknown")
                }
                dashboard_trades.append(dashboard_trade)
            
            # Sort by timestamp (newest first)
            dashboard_trades.sort(key=lambda x: x["timestamp"], reverse=True)
            
    
            return dashboard_trades[:50]  # Return last 50 trades
            
        except Exception as e:
            logger.error(f"Error getting dashboard trade data: {e}")
            return []


# Global trade state manager instance
trade_state_manager = TradeStateManager()
