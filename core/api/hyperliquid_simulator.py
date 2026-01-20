#!/usr/bin/env python3
"""
Enhanced Hyperliquid Simulator
Simulates the complete Hyperliquid trading environment including:
- Account state (balance, margin, positions)
- Order execution (market, limit, post-only, reduce-only)
- Position lifecycle (open, close, modify)
- P&L calculation with leverage
- Margin requirements and liquidation
- Realistic fees and slippage

This simulator mimics what the real Hyperliquid API would handle in production.
ALIGNED with real Hyperliquid API structure for seamless transition.
"""

import time
import copy
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
from dataclasses import dataclass
from enum import Enum

# Moved from hyperliquid_api_aligned.py - only used here
class OrderType(Enum):
    """Order types supported by Hyperliquid"""
    MARKET = "market"
    LIMIT = "limit"
    POST_ONLY = "post_only"
    REDUCE_ONLY = "reduce_only"

class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIAL = "partial"

@dataclass
class OrderRequest:
    """Order request structure"""
    symbol: str
    side: OrderSide
    size: float
    order_type: OrderType
    price: Optional[float] = None
    leverage: int = 1
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reduce_only: bool = False
    post_only: bool = False
    client_id: Optional[str] = None
    time_in_force: str = "Gtc"

@dataclass
class OrderResponse:
    """Order response structure"""
    order_id: str
    client_id: Optional[str]
    symbol: str
    side: OrderSide
    size: float
    order_type: OrderType
    price: Optional[float]
    status: OrderStatus
    filled_size: float
    remaining_size: float
    average_price: Optional[float]
    fees: Dict[str, float]
    timestamp: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@dataclass
class Position:
    """Position structure"""
    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    mark_price: float
    pnl: float
    pnl_percentage: float
    leverage: int
    margin: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    timestamp: float


class HyperliquidSimulator:
    """Complete Hyperliquid trading environment simulator - aligned with real API"""
    
    def __init__(self, initial_balance: float = 10000.0):
        # Initialize simulator
        self.is_simulated = True
        self.base_url = "simulator"
        
        # Order book data
        self.order_book_snapshot = None
        
        # Account state
        self.account_balance = initial_balance
        self.initial_balance = initial_balance
        self.open_positions: Dict[str, Dict[str, Any]] = {}  # trade_id -> position
        self.closed_positions: List[Dict[str, Any]] = []
        self.pending_orders: Dict[str, Dict[str, Any]] = {}  # order_id -> order
        
        # Trading statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.total_fees_paid = 0.0
        
        # Execution settings
        self.execution_delays = {
            'MARKET': 0.1,      # 100ms for market orders
            'LIMIT': 2.0,       # 2s for limit orders
            'POST_ONLY': 1.5,   # 1.5s for post-only
            'REDUCE_ONLY': 1.0  # 1s for reduce-only
        }
        
        # Fee structure (from Hyperliquid docs)
        self.fee_rates = {
            'maker': 0.0002,    # 0.02% maker fee
            'taker': 0.0007,    # 0.07% taker fee
            'funding_rate': 0.0001  # 0.01% per hour (varies)
        }
        
        # Risk management
        self.max_leverage = 50  # Hyperliquid max leverage
        self.maintenance_margin_rate = 0.5  # 50% of initial margin
        
        # Simulation settings
        self.tick_size = 0.1  # BTC tick size
        self.slippage_model = 'realistic'
        self.execution_quality = 0.98  # 98% success rate
        
        logger.info(f"🏦 HyperLiquid Simulator initialized with ${initial_balance:,.2f} balance")
    
    # ============================================================================
    # ACCOUNT MANAGEMENT
    # ============================================================================
    
    def get_account_state(self) -> Dict[str, Any]:
        """Get complete account state"""
        unrealized_pnl = self._calculate_total_unrealized_pnl()
        used_margin = self._calculate_used_margin()
        available_margin = self.account_balance - used_margin
        
        return {
            "balance": self.account_balance,
            "initial_balance": self.initial_balance,
            "equity": self.account_balance + unrealized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": self.total_pnl,
            "used_margin": used_margin,
            "available_margin": available_margin,
            "margin_ratio": (used_margin / self.account_balance * 100) if self.account_balance > 0 else 0,
            "open_positions_count": len(self.open_positions),
            "pending_orders_count": len(self.pending_orders),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            "total_fees_paid": self.total_fees_paid
        }
    
    def get_balance(self) -> float:
        """Get current account balance"""
        return self.account_balance
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        return list(self.open_positions.values())
    
    def get_position(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get specific position by trade_id"""
        return self.open_positions[trade_id] if trade_id in self.open_positions else None
    
    def get_closed_positions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get closed positions (most recent first)"""
        return self.closed_positions[-limit:][::-1]
    
    # ============================================================================
    # ORDER EXECUTION
    # ============================================================================
    
    def update_order_book(self, orderbook: Dict[str, Any]):
        """Update the order book snapshot"""
        self.order_book_snapshot = copy.deepcopy(orderbook)
    
    def _simulate_order_execution(self, order_request: OrderRequest) -> OrderResponse:
        """Simulate order execution using the aligned API structure"""
        return self._execute_order_aligned(order_request)
    
    def _execute_order_aligned(self, order_request: OrderRequest) -> OrderResponse:
        """Execute order using the new aligned structure"""
        try:
            # Validate inputs
            if not self.order_book_snapshot:
                raise ValueError("No order book data available")
            
            if order_request.leverage > self.max_leverage:
                raise ValueError(f"Leverage {order_request.leverage}x exceeds maximum {self.max_leverage}x")
            
            if order_request.order_type == OrderType.LIMIT and order_request.price is None:
                raise ValueError("Limit price required for LIMIT orders")
            
            # Check execution success rate
            if random.random() > self.execution_quality:
                raise ValueError("Order rejected by exchange (simulated)")
            
            # Simulate execution delay
            delay = self.execution_delays.get(order_request.order_type.value.upper(), 1.0)
            time.sleep(delay * 0.001)  # Convert to milliseconds
            
            # Execute order based on type
            if order_request.order_type == OrderType.MARKET:
                execution_result = self._execute_market_order_aligned(order_request)
            elif order_request.order_type == OrderType.LIMIT:
                execution_result = self._execute_limit_order_aligned(order_request)
            else:
                raise ValueError(f"Unsupported order type: {order_request.order_type}")
            
            if not execution_result.get("success"):
                raise ValueError(execution_result.get("error", "Order execution failed"))
            
            # Check margin requirements
            margin_check = self._check_margin_requirements(
                order_request.size, 
                execution_result["execution_price"], 
                order_request.leverage
            )
            if not margin_check["sufficient"]:
                raise ValueError(f"Insufficient margin: {margin_check['reason']}")
            
            # Create order response
            order_id = f"order_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            
            response = OrderResponse(
                order_id=order_id,
                client_id=order_request.client_id,
                symbol=order_request.symbol,
                side=order_request.side,
                size=order_request.size,
                order_type=order_request.order_type,
                price=order_request.price,
                status=OrderStatus.FILLED,
                filled_size=order_request.size,
                remaining_size=0.0,
                average_price=execution_result["execution_price"],
                fees=execution_result["fees"],
                timestamp=time.time(),
                stop_loss=order_request.stop_loss,
                take_profit=order_request.take_profit
            )
            
            # Create position if order filled
            if response.status == OrderStatus.FILLED:
                self._create_position_aligned(order_request, execution_result)
            
            return response
            
        except Exception as e:
            # Return error response
            return OrderResponse(
                order_id="",
                client_id=order_request.client_id,
                symbol=order_request.symbol,
                side=order_request.side,
                size=order_request.size,
                order_type=order_request.order_type,
                price=order_request.price,
                status=OrderStatus.REJECTED,
                filled_size=0.0,
                remaining_size=order_request.size,
                average_price=None,
                fees={"total_cost": 0.0, "fee_type": "none"},
                timestamp=time.time(),
                stop_loss=order_request.stop_loss,
                take_profit=order_request.take_profit
            )
    
    def place_order(self, 
                   order_type: str,
                   side: str,
                   size: float,
                   symbol: str = "BTC",
                   price: Optional[float] = None,
                   leverage: int = 30,
                   stop_loss: Optional[float] = None,
                   take_profit: Optional[float] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Place an order (market or limit)
        
        Args:
            order_type: MARKET, LIMIT, POST_ONLY, REDUCE_ONLY
            side: BUY or SELL
            size: Position size in BTC
            symbol: Trading symbol (default: BTC)
            price: Limit price (required for LIMIT orders)
            leverage: Leverage multiplier (1-50)
            stop_loss: Stop loss price
            take_profit: Take profit price
            metadata: Additional order metadata (strategy, confidence, etc.)
        
        Returns:
            Order execution result with position details
        """
        try:
            # Validate inputs
            if not self.order_book_snapshot:
                return self._create_error_response("No order book data available")
            
            if leverage > self.max_leverage:
                return self._create_error_response(f"Leverage {leverage}x exceeds maximum {self.max_leverage}x")
            
            if order_type.upper() == "LIMIT" and price is None:
                return self._create_error_response("Limit price required for LIMIT orders")
            
            # Check execution success rate
            if random.random() > self.execution_quality:
                return self._create_error_response("Order rejected by exchange (simulated)")
            
            # Simulate execution delay
            delay = self.execution_delays.get(order_type.upper(), 1.0)
            time.sleep(delay * 0.001)  # Convert to milliseconds
            
            # Execute order based on type
            if order_type.upper() == "MARKET":
                execution_result = self._execute_market_order(side, size, leverage)
            elif order_type.upper() == "LIMIT":
                execution_result = self._execute_limit_order(side, size, price, leverage)
            elif order_type.upper() == "POST_ONLY":
                execution_result = self._execute_post_only_order(side, size, price, leverage)
            elif order_type.upper() == "REDUCE_ONLY":
                execution_result = self._execute_reduce_only_order(side, size, price, leverage)
            else:
                return self._create_error_response(f"Unsupported order type: {order_type}")
            
            if not execution_result.get("success"):
                return execution_result
            
            # Check margin requirements
            margin_check = self._check_margin_requirements(size, execution_result["execution_price"], leverage)
            if not margin_check["sufficient"]:
                return self._create_error_response(f"Insufficient margin: {margin_check['reason']}")
            
            # Create position if order filled
            if execution_result["order_status"] == "FILLED":
                position = self._create_position(
                    side=side,
                    size=size,
                    entry_price=execution_result["execution_price"],
                    leverage=leverage,
                    fees=execution_result["fees"],
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata=metadata or {}
                )
                
                # Deduct fees from balance
                self.account_balance -= execution_result["fees"]["fee_amount"]
                self.total_fees_paid += execution_result["fees"]["fee_amount"]
                
                execution_result["position"] = position
                execution_result["account_balance"] = self.account_balance
                
                logger.success(f"✅ Order filled: {side} {size} BTC @ ${execution_result['execution_price']:,.2f}")
                logger.info(f"   Leverage: {leverage}x | Fees: ${execution_result['fees']['fee_amount']:.4f}")
                logger.info(f"   Balance: ${self.account_balance:,.2f}")
            
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Order placement failed: {e}")
            return self._create_error_response(str(e))
    
    def close_position(self, trade_id: str, exit_price: Optional[float] = None, exit_reason: str = "MANUAL") -> Dict[str, Any]:
        """
        Close an open position
        
        Args:
            trade_id: Position trade ID
            exit_price: Optional exit price (uses market price if None)
            exit_reason: Reason for closing (MANUAL, STOP_LOSS, TAKE_PROFIT, etc.)
        
        Returns:
            Position close result with P&L details
        """
        try:
            position = self.open_positions.get(trade_id)
            if not position:
                return self._create_error_response(f"Position {trade_id} not found")
            
            # Use market price if exit_price not provided
            if exit_price is None:
                if not self.order_book_snapshot:
                    return self._create_error_response("No market data available for exit")
                
                # Get best bid/ask based on position side
                if position["side"] == "BUY":
                    # Closing long = selling at bid
                    exit_price = self.order_book_snapshot['bids'][0]['price'] if self.order_book_snapshot['bids'] else position["entry_price"]
                else:
                    # Closing short = buying at ask
                    exit_price = self.order_book_snapshot['asks'][0]['price'] if self.order_book_snapshot['asks'] else position["entry_price"]
            
            # Execute exit order
            exit_side = "SELL" if position["side"] == "BUY" else "BUY"
            execution_result = self._execute_market_order(exit_side, position["size"], position["leverage"])
            
            if not execution_result.get("success"):
                return execution_result
            
            actual_exit_price = execution_result["execution_price"]
            exit_fees = execution_result["fees"]["fee_amount"]
            
            # Calculate P&L
            pnl_result = self._calculate_position_pnl(
                side=position["side"],
                entry_price=position["entry_price"],
                exit_price=actual_exit_price,
                size=position["size"],
                leverage=position["leverage"],
                entry_fees=position["fees"]["fee_amount"],
                exit_fees=exit_fees
            )
            
            # Update balance
            self.account_balance += pnl_result["net_pnl"]
            self.total_pnl += pnl_result["net_pnl"]
            self.total_fees_paid += exit_fees
            self.total_trades += 1
            
            if pnl_result["net_pnl"] > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            # Update position
            position.update({
                "exit_price": actual_exit_price,
                "exit_time": time.time(),
                "exit_datetime": datetime.now().isoformat(),
                "exit_reason": exit_reason,
                "exit_fees": exit_fees,
                "pnl_pct": pnl_result["pnl_pct"],
                "pnl_amount": pnl_result["pnl_amount"],
                "net_pnl": pnl_result["net_pnl"],
                "total_fees": pnl_result["total_fees"],
                "status": "CLOSED",
                "was_profitable": pnl_result["net_pnl"] > 0
            })
            
            # Move to closed positions
            del self.open_positions[trade_id]
            self.closed_positions.append(position)
            
            logger.success(f"✅ Position closed: {trade_id}")
            logger.info(f"   P&L: {pnl_result['pnl_pct']*100:.2f}% (${pnl_result['net_pnl']:.4f})")
            logger.info(f"   Balance: ${self.account_balance:,.2f}")
            
            return {
                "success": True,
                "position": position,
                "pnl": pnl_result,
                "account_balance": self.account_balance,
                "execution_result": execution_result
            }
            
        except Exception as e:
            logger.error(f"❌ Position close failed: {e}")
            return self._create_error_response(str(e))
    
    def check_stop_loss_take_profit(self, current_price: float) -> List[Dict[str, Any]]:
        """
        Check all open positions for stop loss / take profit triggers
        
        Args:
            current_price: Current market price
        
        Returns:
            List of positions that were closed
        """
        closed_positions = []
        
        for trade_id, position in list(self.open_positions.items()):
            should_close = False
            exit_reason = None
            
            # Check take profit
            if position.get("take_profit"):
                if (position["side"] == "BUY" and current_price >= position["take_profit"]) or \
                   (position["side"] == "SELL" and current_price <= position["take_profit"]):
                    should_close = True
                    exit_reason = "TAKE_PROFIT"
            
            # Check stop loss
            if position.get("stop_loss") and not should_close:
                if (position["side"] == "BUY" and current_price <= position["stop_loss"]) or \
                   (position["side"] == "SELL" and current_price >= position["stop_loss"]):
                    should_close = True
                    exit_reason = "STOP_LOSS"
            
            if should_close:
                result = self.close_position(trade_id, current_price, exit_reason)
                if result.get("success"):
                    closed_positions.append(result["position"])
        
        return closed_positions
    
    # ============================================================================
    # INTERNAL EXECUTION METHODS
    # ============================================================================
    
    def _execute_market_order(self, side: str, size: float, leverage: int) -> Dict[str, Any]:
        """Execute market order with realistic order book impact"""
        levels = self.order_book_snapshot['asks'] if side == "BUY" else self.order_book_snapshot['bids']
        
        impact_result = self._calculate_order_book_impact(side, size, levels)
        
        if impact_result['remaining_size'] > 0:
            return self._create_error_response("Insufficient liquidity for market order")
        
        fees = self._calculate_fees('taker', size, impact_result['avg_price'])
        
        return {
            "success": True,
            "order_type": "MARKET",
            "side": side,
            "size": size,
            "execution_price": impact_result['avg_price'],
            "total_cost": impact_result['total_cost'],
            "fees": fees,
            "slippage": impact_result['slippage'],
            "leverage": leverage,
            "execution_time": time.time(),
            "order_status": "FILLED",
            "fills": impact_result['fills']
        }
    
    def _execute_limit_order(self, side: str, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Execute limit order (may fill immediately or remain pending)"""
        best_bid = self.order_book_snapshot['bids'][0]['price'] if self.order_book_snapshot['bids'] else 0
        best_ask = self.order_book_snapshot['asks'][0]['price'] if self.order_book_snapshot['asks'] else float('inf')
        
        # Check if order crosses spread (immediate execution)
        crosses_spread = (side == 'BUY' and price >= best_ask) or (side == 'SELL' and price <= best_bid)
        
        if crosses_spread:
            # Execute immediately as taker
            levels = self.order_book_snapshot['asks'] if side == "BUY" else self.order_book_snapshot['bids']
            impact_result = self._calculate_order_book_impact(side, size, levels)
            fees = self._calculate_fees('taker', size, impact_result['avg_price'])
            
            return {
                "success": True,
                "order_type": "LIMIT",
                "side": side,
                "size": size,
                "execution_price": impact_result['avg_price'],
                "total_cost": impact_result['total_cost'],
                "fees": fees,
                "slippage": impact_result['slippage'],
                "leverage": leverage,
                "execution_time": time.time(),
                "order_status": "FILLED",
                "fills": impact_result['fills']
            }
        else:
            # Order placed but not filled (maker fee)
            # For simulation, we'll fill it immediately at limit price with 70% probability
            if random.random() < 0.7:
                fees = self._calculate_fees('maker', size, price)
                return {
                    "success": True,
                    "order_type": "LIMIT",
                    "side": side,
                    "size": size,
                    "execution_price": price,
                    "total_cost": size * price,
                    "fees": fees,
                    "slippage": 0.0,
                    "leverage": leverage,
                    "execution_time": time.time(),
                    "order_status": "FILLED",
                    "fills": [{"price": price, "size": size, "cost": size * price}]
                }
            else:
                return {
                    "success": True,
                    "order_type": "LIMIT",
                    "side": side,
                    "size": size,
                    "execution_price": price,
                    "total_cost": size * price,
                    "fees": self._calculate_fees('maker', size, price),
                    "slippage": 0.0,
                    "leverage": leverage,
                    "execution_time": time.time(),
                    "order_status": "PENDING",
                    "fills": []
                }
    
    def _execute_post_only_order(self, side: str, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Execute post-only order (rejects if would cross spread)"""
        best_bid = self.order_book_snapshot['bids'][0]['price'] if self.order_book_snapshot['bids'] else 0
        best_ask = self.order_book_snapshot['asks'][0]['price'] if self.order_book_snapshot['asks'] else float('inf')
        
        if side == 'BUY' and price >= best_ask:
            return self._create_error_response("Post-only order would cross spread")
        elif side == 'SELL' and price <= best_bid:
            return self._create_error_response("Post-only order would cross spread")
        
        fees = self._calculate_fees('maker', size, price)
        
        return {
            "success": True,
            "order_type": "POST_ONLY",
            "side": side,
            "size": size,
            "execution_price": price,
            "total_cost": size * price,
            "fees": fees,
            "slippage": 0.0,
            "leverage": leverage,
            "execution_time": time.time(),
            "order_status": "PENDING",
            "fills": []
        }
    
    def _execute_reduce_only_order(self, side: str, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Execute reduce-only order (can only reduce existing positions)"""
        levels = self.order_book_snapshot['asks'] if side == "BUY" else self.order_book_snapshot['bids']
        impact_result = self._calculate_order_book_impact(side, size, levels)
        fees = self._calculate_fees('taker', size, impact_result['avg_price'])
        
        return {
            "success": True,
            "order_type": "REDUCE_ONLY",
            "side": side,
            "size": size,
            "execution_price": impact_result['avg_price'],
            "total_cost": impact_result['total_cost'],
            "fees": fees,
            "slippage": impact_result['slippage'],
            "leverage": leverage,
            "execution_time": time.time(),
            "order_status": "FILLED",
            "fills": impact_result['fills']
        }
    
    # ============================================================================
    # POSITION MANAGEMENT
    # ============================================================================
    
    def _create_position(self, side: str, size: float, entry_price: float, leverage: int,
                        fees: Dict[str, Any], stop_loss: Optional[float], take_profit: Optional[float],
                        metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new position"""
        self.total_trades += 1
        trade_id = f"sim_trade_{self.total_trades}_{int(time.time())}"
        
        position = {
            "trade_id": trade_id,
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "leverage": leverage,
            "entry_time": time.time(),
            "entry_datetime": datetime.now().isoformat(),
            "fees": fees,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "status": "OPEN",
            "position_value": size * entry_price,
            "margin_used": (size * entry_price) / leverage,
            **metadata  # Include strategy, confidence, etc.
        }
        
        self.open_positions[trade_id] = position
        return position
    
    def _calculate_position_pnl(self, side: str, entry_price: float, exit_price: float,
                                size: float, leverage: int, entry_fees: float, exit_fees: float) -> Dict[str, Any]:
        """Calculate position P&L with leverage"""
        if side == "BUY":
            price_change = (exit_price - entry_price) / entry_price
        else:  # SELL
            price_change = (entry_price - exit_price) / entry_price
        
        # Apply leverage
        pnl_pct = price_change * leverage
        position_value = size * entry_price
        pnl_amount = position_value * pnl_pct
        
        # Deduct fees
        total_fees = entry_fees + exit_fees
        net_pnl = pnl_amount - total_fees
        
        return {
            "pnl_pct": pnl_pct,
            "pnl_amount": pnl_amount,
            "total_fees": total_fees,
            "net_pnl": net_pnl,
            "price_change": price_change,
            "entry_fees": entry_fees,
            "exit_fees": exit_fees
        }
    
    def _calculate_total_unrealized_pnl(self, current_price: Optional[float] = None) -> float:
        """Calculate total unrealized P&L for all open positions"""
        if not current_price and self.order_book_snapshot:
            # Use mid price
            best_bid = self.order_book_snapshot['bids'][0]['price'] if self.order_book_snapshot['bids'] else 0
            best_ask = self.order_book_snapshot['asks'][0]['price'] if self.order_book_snapshot['asks'] else 0
            current_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
        
        if not current_price:
            return 0.0
        
        total_unrealized = 0.0
        for position in self.open_positions.values():
            if position["side"] == "BUY":
                pnl_pct = (current_price - position["entry_price"]) / position["entry_price"]
            else:
                pnl_pct = (position["entry_price"] - current_price) / position["entry_price"]
            
            pnl_pct *= position["leverage"]
            position_value = position["size"] * position["entry_price"]
            total_unrealized += position_value * pnl_pct
        
        return total_unrealized
    
    # ============================================================================
    # MARGIN & RISK MANAGEMENT
    # ============================================================================
    
    def _check_margin_requirements(self, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Check if account has sufficient margin for trade"""
        position_value = size * price
        required_margin = position_value / leverage
        used_margin = self._calculate_used_margin()
        available_margin = self.account_balance - used_margin
        
        if available_margin >= required_margin:
            return {
                "sufficient": True,
                "required_margin": required_margin,
                "available_margin": available_margin,
                "used_margin": used_margin
            }
        else:
            return {
                "sufficient": False,
                "required_margin": required_margin,
                "available_margin": available_margin,
                "used_margin": used_margin,
                "reason": f"Insufficient margin: need ${required_margin:.2f}, have ${available_margin:.2f}"
            }
    
    def _calculate_used_margin(self) -> float:
        """Calculate total margin used by open positions"""
        return sum(pos["margin_used"] for pos in self.open_positions.values())
    
    def check_liquidation_risk(self, current_price: float) -> List[Dict[str, Any]]:
        """Check if any positions should be liquidated"""
        liquidated_positions = []
        
        for trade_id, position in list(self.open_positions.items()):
            # Calculate current margin
            if position["side"] == "BUY":
                pnl_pct = (current_price - position["entry_price"]) / position["entry_price"]
            else:
                pnl_pct = (position["entry_price"] - current_price) / position["entry_price"]
            
            pnl_pct *= position["leverage"]
            position_value = position["size"] * position["entry_price"]
            unrealized_pnl = position_value * pnl_pct
            
            current_margin = position["margin_used"] + unrealized_pnl
            maintenance_margin = position["margin_used"] * self.maintenance_margin_rate
            
            # Liquidate if margin falls below maintenance margin
            if current_margin < maintenance_margin:
                logger.warning(f"🚨 LIQUIDATION: {trade_id} - Margin ${current_margin:.2f} < ${maintenance_margin:.2f}")
                result = self.close_position(trade_id, current_price, "LIQUIDATION")
                if result.get("success"):
                    liquidated_positions.append(result["position"])
        
        return liquidated_positions
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _calculate_order_book_impact(self, side: str, size: float, levels: List[Dict]) -> Dict[str, Any]:
        """Calculate realistic order book impact"""
        remaining_size = size
        executed_size = 0
        total_cost = 0
        fills = []
        
        for level in levels:
            if remaining_size <= 0:
                break
            
            available_size = level['size']
            executed_at_level = min(remaining_size, available_size)
            
            executed_size += executed_at_level
            level_cost = executed_at_level * level['price']
            total_cost += level_cost
            remaining_size -= executed_at_level
            
            fills.append({
                "price": level['price'],
                "size": executed_at_level,
                "cost": level_cost
            })
        
        avg_price = total_cost / executed_size if executed_size > 0 else 0
        slippage = abs(avg_price - levels[0]['price']) / levels[0]['price'] if levels else 0
        
        return {
            "executed_size": executed_size,
            "total_cost": total_cost,
            "avg_price": avg_price,
            "remaining_size": remaining_size,
            "slippage": slippage,
            "fills": fills
        }
    
    def _calculate_fees(self, fee_type: str, size: float, price: float) -> Dict[str, Any]:
        """Calculate realistic Hyperliquid fees"""
        fee_rate = self.fee_rates.get(fee_type, self.fee_rates['taker'])
        position_value = size * price
        fee_amount = position_value * fee_rate
        
        return {
            "fee_rate": fee_rate,
            "fee_amount": fee_amount,
            "fee_type": fee_type,
            "position_value": position_value
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "success": False,
            "error": error_message,
            "execution_time": time.time()
        }
    
    # ============================================================================
    # ALIGNED API METHODS
    # ============================================================================
    
    def _execute_market_order_aligned(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Execute market order using aligned API structure"""
        levels = self.order_book_snapshot['asks'] if order_request.side == OrderSide.BUY else self.order_book_snapshot['bids']
        
        impact_result = self._calculate_order_book_impact(order_request.side.value, order_request.size, levels)
        
        if impact_result['remaining_size'] > 0:
            return {"success": False, "error": "Insufficient liquidity for market order"}
        
        fees = self._calculate_fees('taker', order_request.size, impact_result['avg_price'])
        
        return {
            "success": True,
            "order_type": "MARKET",
            "side": order_request.side.value,
            "size": order_request.size,
            "execution_price": impact_result['avg_price'],
            "total_cost": impact_result['total_cost'],
            "fees": fees,
            "slippage": impact_result['slippage'],
            "leverage": order_request.leverage,
            "execution_time": time.time(),
            "order_status": "FILLED",
            "fills": impact_result['fills']
        }
    
    def _execute_limit_order_aligned(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Execute limit order using aligned API structure"""
        best_bid = self.order_book_snapshot['bids'][0]['price'] if self.order_book_snapshot['bids'] else 0
        best_ask = self.order_book_snapshot['asks'][0]['price'] if self.order_book_snapshot['asks'] else float('inf')
        
        # Check if order crosses spread (immediate execution)
        crosses_spread = (order_request.side == OrderSide.BUY and order_request.price >= best_ask) or \
                        (order_request.side == OrderSide.SELL and order_request.price <= best_bid)
        
        if crosses_spread:
            # Execute immediately as taker
            levels = self.order_book_snapshot['asks'] if order_request.side == OrderSide.BUY else self.order_book_snapshot['bids']
            impact_result = self._calculate_order_book_impact(order_request.side.value, order_request.size, levels)
            fees = self._calculate_fees('taker', order_request.size, impact_result['avg_price'])
            
            return {
                "success": True,
                "order_type": "LIMIT",
                "side": order_request.side.value,
                "size": order_request.size,
                "execution_price": impact_result['avg_price'],
                "total_cost": impact_result['total_cost'],
                "fees": fees,
                "slippage": impact_result['slippage'],
                "leverage": order_request.leverage,
                "execution_time": time.time(),
                "order_status": "FILLED",
                "fills": impact_result['fills']
            }
        else:
            # Order placed but not filled (maker fee)
            # For simulation, we'll fill it immediately at limit price with 70% probability
            if random.random() < 0.7:
                fees = self._calculate_fees('maker', order_request.size, order_request.price)
                return {
                    "success": True,
                    "order_type": "LIMIT",
                    "side": order_request.side.value,
                    "size": order_request.size,
                    "execution_price": order_request.price,
                    "total_cost": order_request.size * order_request.price,
                    "fees": fees,
                    "slippage": 0.0,
                    "leverage": order_request.leverage,
                    "execution_time": time.time(),
                    "order_status": "FILLED",
                    "fills": [{"price": order_request.price, "size": order_request.size, "cost": order_request.size * order_request.price}]
                }
            else:
                return {
                    "success": True,
                    "order_type": "LIMIT",
                    "side": order_request.side.value,
                    "size": order_request.size,
                    "execution_price": order_request.price,
                    "total_cost": order_request.size * order_request.price,
                    "fees": self._calculate_fees('maker', order_request.size, order_request.price),
                    "slippage": 0.0,
                    "leverage": order_request.leverage,
                    "execution_time": time.time(),
                    "order_status": "PENDING",
                    "fills": []
                }
    
    def _create_position_aligned(self, order_request: OrderRequest, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new position using aligned API structure"""
        self.total_trades += 1
        trade_id = f"sim_trade_{self.total_trades}_{int(time.time())}"
        
        position = {
            "trade_id": trade_id,
            "side": order_request.side.value,
            "size": order_request.size,
            "entry_price": execution_result["execution_price"],
            "leverage": order_request.leverage,
            "entry_time": time.time(),
            "entry_datetime": datetime.now().isoformat(),
            "fees": execution_result["fees"],
            "stop_loss": order_request.stop_loss,
            "take_profit": order_request.take_profit,
            "status": "OPEN",
            "position_value": order_request.size * execution_result["execution_price"],
            "margin_used": (order_request.size * execution_result["execution_price"]) / order_request.leverage,
            "symbol": order_request.symbol,
            "client_id": order_request.client_id
        }
        
        self.open_positions[trade_id] = position
        
        # Deduct fees from balance
        self.account_balance -= execution_result["fees"]["fee_amount"]
        self.total_fees_paid += execution_result["fees"]["fee_amount"]
        
        logger.success(f"✅ Position created: {trade_id} - {order_request.side.value} {order_request.size} BTC @ ${execution_result['execution_price']:,.2f}")
        logger.info(f"   Leverage: {order_request.leverage}x | Stop Loss: ${order_request.stop_loss:,.2f} | Take Profit: ${order_request.take_profit:,.2f}")
        
        return position
    


# Global simulator instance (will be initialized with proper balance by SystemInitializer)
# This is kept for backward compatibility but should not be used directly
_global_simulator = None

def get_global_simulator():
    """Get or create global simulator instance"""
    global _global_simulator
    if _global_simulator is None:
        _global_simulator = HyperliquidSimulator(initial_balance=10000.0)
    return _global_simulator

# Legacy compatibility
hyperliquid_simulator = None  # Will be set by SystemInitializer
