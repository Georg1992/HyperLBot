#!/usr/bin/env python3
"""
Order Lifecycle Management System
=================================
Manages the complete lifecycle of trading orders from PENDING → FILLED → CLOSED
"""

import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from loguru import logger
from collections import defaultdict

@dataclass
class OrderData:
    """Complete order data structure"""
    order_id: str
    prediction_id: str
    side: str  # BUY or SELL
    size: float
    limit_price: float
    current_price: float
    status: str  # PENDING, FILLED, CANCELLED, EXPIRED
    created_at: float
    filled_at: Optional[float] = None
    filled_price: Optional[float] = None
    timeout: float = 0.0
    strategy: str = "standard"
    confidence: float = 0.0
    expected_value: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = None

@dataclass
class PositionData:
    """Position data after order is filled"""
    position_id: str
    order_id: str
    side: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    status: str  # OPEN, CLOSED
    opened_at: float
    closed_at: Optional[float] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # STOP_LOSS, TAKE_PROFIT, MANUAL, TIMEOUT
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str = "standard"
    confidence: float = 0.0
    metadata: Dict[str, Any] = None

class OrderLifecycleManager:
    """Manages complete order lifecycle from placement to closure"""
    
    def __init__(self, order_timeout_minutes: int = 20):
        self.order_timeout_minutes = order_timeout_minutes
        self.order_timeout_seconds = order_timeout_minutes * 60
        
        # Order tracking
        self.pending_orders: Dict[str, OrderData] = {}
        self.filled_orders: Dict[str, OrderData] = {}
        self.cancelled_orders: Dict[str, OrderData] = {}
        
        # Position tracking
        self.active_positions: Dict[str, PositionData] = {}
        self.closed_positions: List[PositionData] = []
        
        # Performance tracking
        self.total_orders_placed = 0
        self.total_orders_filled = 0
        self.total_orders_cancelled = 0
        self.total_orders_expired = 0
        
        logger.info(f"🔄 Order Lifecycle Manager initialized (timeout: {order_timeout_minutes}min)")
    
    def place_limit_order(self, prediction: Dict[str, Any], current_price: float) -> str:
        """
        Place a new limit order based on prediction
        
        Args:
            prediction: Prediction data with entry_price, side, etc.
            current_price: Current market price
            
        Returns:
            order_id: Unique identifier for the order
        """
        try:
            # Generate unique order ID
            order_id = f"order_{uuid.uuid4().hex[:8]}"
            prediction_id = prediction.get("id", f"pred_{uuid.uuid4().hex[:8]}")
            
            # Extract order parameters
            side = prediction.get("side", "BUY")
            size = prediction.get("size", 0.001)  # Default 0.001 BTC
            limit_price = prediction.get("entry_price", current_price)
            strategy = prediction.get("strategy", "standard")
            confidence = prediction.get("calibrated_confidence", 0.0)
            expected_value = prediction.get("expected_value", 0.0)
            stop_loss = prediction.get("stop_loss")
            take_profit = prediction.get("take_profit")
            
            # Calculate timeout
            timeout = time.time() + self.order_timeout_seconds
            
            # Create order data
            order = OrderData(
                order_id=order_id,
                prediction_id=prediction_id,
                side=side,
                size=size,
                limit_price=limit_price,
                current_price=current_price,
                status="PENDING",
                created_at=time.time(),
                timeout=timeout,
                strategy=strategy,
                confidence=confidence,
                expected_value=expected_value,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata=prediction.copy()
            )
            
            # Store pending order
            self.pending_orders[order_id] = order
            self.total_orders_placed += 1
            
            logger.info(f"📋 LIMIT ORDER PLACED: {side} {size} BTC @ ${limit_price:,.2f}")
            logger.info(f"   Order ID: {order_id}")
            logger.info(f"   Current Price: ${current_price:,.2f}")
            logger.info(f"   Strategy: {strategy} (confidence: {confidence:.1%})")
            logger.info(f"   Timeout: {self.order_timeout_minutes} minutes")
            
            return order_id
            
        except Exception as e:
            logger.error(f"❌ Failed to place limit order: {e}")
            return ""
    
    def check_order_fills(self, current_price: float) -> List[str]:
        """
        Check if any pending orders should be filled based on current price
        
        Args:
            current_price: Current market price
            
        Returns:
            List of filled order IDs
        """
        filled_orders = []
        
        try:
            for order_id, order in list(self.pending_orders.items()):
                # Check if order should be filled
                should_fill = self._should_fill_order(order, current_price)
                
                if should_fill:
                    filled_order_id = self._fill_order(order_id, current_price)
                    if filled_order_id:
                        filled_orders.append(filled_order_id)
                
                # Check for timeout
                elif time.time() > order.timeout:
                    self._expire_order(order_id)
                    
        except Exception as e:
            logger.error(f"❌ Error checking order fills: {e}")
        
        return filled_orders
    
    def _should_fill_order(self, order: OrderData, current_price: float) -> bool:
        """Determine if an order should be filled based on current price"""
        try:
            if order.side == "BUY":
                # Buy order: fill when price drops to or below limit price
                return current_price <= order.limit_price
            else:  # SELL
                # Sell order: fill when price rises to or above limit price
                return current_price >= order.limit_price
                
        except Exception as e:
            logger.error(f"❌ Error checking order fill condition: {e}")
            return False
    
    def _fill_order(self, order_id: str, fill_price: float) -> Optional[str]:
        """Fill a pending order and create position"""
        try:
            if order_id not in self.pending_orders:
                logger.warning(f"⚠️ Order {order_id} not found in pending orders")
                return None
            
            order = self.pending_orders[order_id]
            
            # Update order status
            order.status = "FILLED"
            order.filled_at = time.time()
            order.filled_price = fill_price
            order.current_price = fill_price
            
            # Move to filled orders
            self.filled_orders[order_id] = order
            del self.pending_orders[order_id]
            
            # Create position
            position_id = self._create_position(order, fill_price)
            
            self.total_orders_filled += 1
            
            logger.info(f"✅ ORDER FILLED: {order.side} {order.size} BTC @ ${fill_price:,.2f}")
            logger.info(f"   Order ID: {order_id}")
            logger.info(f"   Position ID: {position_id}")
            logger.info(f"   Fill Price vs Limit: ${fill_price:,.2f} vs ${order.limit_price:,.2f}")
            
            return order_id
            
        except Exception as e:
            logger.error(f"❌ Failed to fill order {order_id}: {e}")
            return None
    
    def _create_position(self, order: OrderData, fill_price: float) -> str:
        """Create a new position from filled order"""
        try:
            position_id = f"pos_{uuid.uuid4().hex[:8]}"
            
            position = PositionData(
                position_id=position_id,
                order_id=order.order_id,
                side=order.side,
                size=order.size,
                entry_price=fill_price,
                current_price=fill_price,
                unrealized_pnl=0.0,  # No P&L at entry
                status="OPEN",
                opened_at=time.time(),
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                strategy=order.strategy,
                confidence=order.confidence,
                metadata=order.metadata
            )
            
            self.active_positions[position_id] = position
            
            logger.info(f"📈 POSITION OPENED: {position.side} {position.size} BTC @ ${fill_price:,.2f}")
            logger.info(f"   Position ID: {position_id}")
            logger.info(f"   Stop Loss: ${position.stop_loss:,.2f}" if position.stop_loss else "   Stop Loss: None")
            logger.info(f"   Take Profit: ${position.take_profit:,.2f}" if position.take_profit else "   Take Profit: None")
            
            return position_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create position: {e}")
            return ""
    
    def _expire_order(self, order_id: str) -> None:
        """Expire a timed-out order"""
        try:
            if order_id not in self.pending_orders:
                return
            
            order = self.pending_orders[order_id]
            order.status = "EXPIRED"
            
            # Move to cancelled orders
            self.cancelled_orders[order_id] = order
            del self.pending_orders[order_id]
            
            self.total_orders_expired += 1
            
            logger.warning(f"⏰ ORDER EXPIRED: {order.side} {order.size} BTC @ ${order.limit_price:,.2f}")
            logger.warning(f"   Order ID: {order_id}")
            logger.warning(f"   Timeout: {self.order_timeout_minutes} minutes")
            
        except Exception as e:
            logger.error(f"❌ Failed to expire order {order_id}: {e}")
    
    def update_position_prices(self, current_price: float) -> List[str]:
        """
        Update all active positions with current price and check for exits
        
        Args:
            current_price: Current market price
            
        Returns:
            List of closed position IDs
        """
        closed_positions = []
        
        try:
            for position_id, position in list(self.active_positions.items()):
                # Update current price and P&L
                position.current_price = current_price
                position.unrealized_pnl = self._calculate_unrealized_pnl(position)
                
                # Check for exit conditions
                should_close = self._should_close_position(position, current_price)
                
                if should_close:
                    exit_reason = self._get_exit_reason(position, current_price)
                    closed_position_id = self._close_position(position_id, current_price, exit_reason)
                    if closed_position_id:
                        closed_positions.append(closed_position_id)
                        
        except Exception as e:
            logger.error(f"❌ Error updating position prices: {e}")
        
        return closed_positions
    
    def _calculate_unrealized_pnl(self, position: PositionData) -> float:
        """Calculate unrealized P&L for a position"""
        try:
            if position.side == "BUY":
                # Long position: profit when price goes up
                pnl = (position.current_price - position.entry_price) * position.size
            else:  # SELL
                # Short position: profit when price goes down
                pnl = (position.entry_price - position.current_price) * position.size
            
            return pnl
            
        except Exception as e:
            logger.error(f"❌ Error calculating P&L: {e}")
            return 0.0
    
    def _should_close_position(self, position: PositionData, current_price: float) -> bool:
        """Determine if a position should be closed"""
        try:
            # Check stop loss
            if position.stop_loss:
                if position.side == "BUY" and current_price <= position.stop_loss:
                    return True
                elif position.side == "SELL" and current_price >= position.stop_loss:
                    return True
            
            # Check take profit
            if position.take_profit:
                if position.side == "BUY" and current_price >= position.take_profit:
                    return True
                elif position.side == "SELL" and current_price <= position.take_profit:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking position exit conditions: {e}")
            return False
    
    def _get_exit_reason(self, position: PositionData, current_price: float) -> str:
        """Determine the reason for position closure"""
        try:
            # Check stop loss first (more urgent)
            if position.stop_loss:
                if position.side == "BUY" and current_price <= position.stop_loss:
                    return "STOP_LOSS"
                elif position.side == "SELL" and current_price >= position.stop_loss:
                    return "STOP_LOSS"
            
            # Check take profit
            if position.take_profit:
                if position.side == "BUY" and current_price >= position.take_profit:
                    return "TAKE_PROFIT"
                elif position.side == "SELL" and current_price <= position.take_profit:
                    return "TAKE_PROFIT"
            
            return "UNKNOWN"
            
        except Exception as e:
            logger.error(f"❌ Error determining exit reason: {e}")
            return "ERROR"
    
    def _close_position(self, position_id: str, exit_price: float, exit_reason: str) -> Optional[str]:
        """Close an active position"""
        try:
            if position_id not in self.active_positions:
                logger.warning(f"⚠️ Position {position_id} not found in active positions")
                return None
            
            position = self.active_positions[position_id]
            
            # Update position status
            position.status = "CLOSED"
            position.closed_at = time.time()
            position.exit_price = exit_price
            position.exit_reason = exit_reason
            position.current_price = exit_price
            
            # Calculate final P&L
            final_pnl = self._calculate_unrealized_pnl(position)
            position.unrealized_pnl = final_pnl
            
            # Move to closed positions
            self.closed_positions.append(position)
            del self.active_positions[position_id]
            
            logger.info(f"🏁 POSITION CLOSED: {position.side} {position.size} BTC @ ${exit_price:,.2f}")
            logger.info(f"   Position ID: {position_id}")
            logger.info(f"   Exit Reason: {exit_reason}")
            logger.info(f"   Final P&L: ${final_pnl:,.2f}")
            logger.info(f"   Duration: {(position.closed_at - position.opened_at) / 60:.1f} minutes")
            
            return position_id
            
        except Exception as e:
            logger.error(f"❌ Failed to close position {position_id}: {e}")
            return None
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current state for dashboard display"""
        try:
            return {
                "pending_orders": [asdict(order) for order in self.pending_orders.values()],
                "active_positions": [asdict(position) for position in self.active_positions.values()],
                "closed_positions": [asdict(position) for position in self.closed_positions[-20:]],  # Last 20
                "statistics": {
                    "total_orders_placed": self.total_orders_placed,
                    "total_orders_filled": self.total_orders_filled,
                    "total_orders_cancelled": self.total_orders_cancelled,
                    "total_orders_expired": self.total_orders_expired,
                    "fill_rate": self.total_orders_filled / max(1, self.total_orders_placed),
                    "active_positions_count": len(self.active_positions),
                    "pending_orders_count": len(self.pending_orders)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting dashboard data: {e}")
            return {}
    
    def can_place_order(self, side: str) -> bool:
        """Check if we can place a new order in the given direction"""
        try:
            # Check for conflicting active positions
            for position in self.active_positions.values():
                if position.side != side:
                    logger.debug(f"🚫 Cannot place {side} order: conflicting {position.side} position active")
                    return False
            
            # Check for conflicting pending orders
            for order in self.pending_orders.values():
                if order.side != side:
                    logger.debug(f"🚫 Cannot place {side} order: conflicting {order.side} order pending")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking order placement: {e}")
            return False
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for ML learning"""
        try:
            if not self.closed_positions:
                return {"message": "No completed trades yet"}
            
            # Calculate performance metrics
            total_trades = len(self.closed_positions)
            winning_trades = len([p for p in self.closed_positions if p.unrealized_pnl > 0])
            losing_trades = len([p for p in self.closed_positions if p.unrealized_pnl < 0])
            
            total_pnl = sum(p.unrealized_pnl for p in self.closed_positions)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "avg_pnl": avg_pnl,
                "fill_rate": self.total_orders_filled / max(1, self.total_orders_placed),
                "avg_trade_duration": sum((p.closed_at - p.opened_at) for p in self.closed_positions) / total_trades if total_trades > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating performance summary: {e}")
            return {}

# Global instance
_global_order_lifecycle_manager = None

def get_global_order_lifecycle_manager() -> OrderLifecycleManager:
    """Get global OrderLifecycleManager instance"""
    global _global_order_lifecycle_manager
    if _global_order_lifecycle_manager is None:
        _global_order_lifecycle_manager = OrderLifecycleManager()
    return _global_order_lifecycle_manager
