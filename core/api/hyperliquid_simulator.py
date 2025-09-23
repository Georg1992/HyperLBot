#!/usr/bin/env python3
"""
Hyperliquid Simulator
Mimics real Hyperliquid trading behavior for accurate paper trading simulation
"""

import time
import copy
import random
from typing import Dict, List, Optional, Any
# # from datetime import datetime, timedelta  # Removed unused import  # Removed unused import
# from loguru import logger  # Removed unused import

class HyperliquidSimulator:
    """Hyperliquid trading simulator with realistic behavior"""
    
    def __init__(self):
        self.order_book_snapshot = None
        self.execution_delays = {
            'market': 0.1,      # 100ms for market orders
            'limit': 2.0,       # 2s for limit orders
            'post_only': 1.5,   # 1.5s for post-only
            'reduce_only': 1.0  # 1s for reduce-only
        }
        
        # Fee structure (from Hyperliquid docs)
        self.fee_rates = {
            'maker': 0.0002,    # 0.02% maker fee
            'taker': 0.0007,    # 0.07% taker fee
            'funding_rate': 0.0001  # 0.01% per hour (varies)
        }
        
        # Order book tick size
        self.tick_size = 0.1  # BTC tick size
        
        # Simulation settings
        self.slippage_model = 'realistic'  # 'none', 'fixed', 'realistic'
        self.execution_quality = 0.95  # 95% success rate for orders
        
    def update_order_book(self, orderbook: Dict[str, Any]):
        """Update the order book snapshot"""
        self.order_book_snapshot = copy.deepcopy(orderbook)

    
    def simulate_order_execution(self, 
                               order_type: str, 
                               side: str, 
                               size: float, 
                               price: Optional[float] = None,
                               leverage: int = 30) -> Dict[str, Any]:
        """Simulate realistic order execution"""
        
        if not self.order_book_snapshot:
            return self._create_error_response("No order book data available")
        
        # Check execution success rate
        if random.random() > self.execution_quality:
            return self._create_error_response("Order rejected by exchange")
        
        # Simulate execution delay
        delay = self.execution_delays.get(order_type.lower(), 1.0)
        time.sleep(delay * 0.001)  # Convert to milliseconds for simulation
        
        if order_type.upper() == "MARKET":
            return self._simulate_market_execution(side, size, leverage)
        elif order_type.upper() == "LIMIT":
            return self._simulate_limit_execution(side, size, price, leverage)
        elif order_type.upper() == "POST_ONLY":
            return self._simulate_post_only_execution(side, size, price, leverage)
        elif order_type.upper() == "REDUCE_ONLY":
            return self._simulate_reduce_only_execution(side, size, price, leverage)
        else:
            return self._create_error_response(f"Unsupported order type: {order_type}")
    
    def _simulate_market_execution(self, side: str, size: float, leverage: int) -> Dict[str, Any]:
        """Simulate market order execution"""
        
        levels = self.order_book_snapshot['bids'] if side == 'BUY' else self.order_book_snapshot['asks']
        
        # Calculate execution impact
        impact_result = self._calculate_order_book_impact(side, size, levels)
        
        if impact_result['remaining_size'] > 0:
            return self._create_error_response("Insufficient liquidity for market order")
        
        # Calculate fees (market orders are always taker)
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
    
    def _simulate_limit_execution(self, side: str, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Simulate limit order execution"""
        
        # Check if limit price is reachable
        best_bid = self.order_book_snapshot['bids'][0]['price'] if self.order_book_snapshot['bids'] else 0
        best_ask = self.order_book_snapshot['asks'][0]['price'] if self.order_book_snapshot['asks'] else float('inf')
        
        if side == 'BUY' and price < best_ask:
            # Limit buy below ask - may not execute immediately
            execution_probability = 0.3  # 30% chance of immediate execution
            if random.random() > execution_probability:
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
        
        elif side == 'SELL' and price > best_bid:
            # Limit sell above bid - may not execute immediately
            execution_probability = 0.3  # 30% chance of immediate execution
            if random.random() > execution_probability:
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
        
        # Order executes immediately (crosses spread)
        levels = self.order_book_snapshot['bids'] if side == 'BUY' else self.order_book_snapshot['asks']
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
    
    def _simulate_post_only_execution(self, side: str, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Simulate post-only order execution"""
        
        # Check if order would cross spread
        best_bid = self.order_book_snapshot['bids'][0]['price'] if self.order_book_snapshot['bids'] else 0
        best_ask = self.order_book_snapshot['asks'][0]['price'] if self.order_book_snapshot['asks'] else float('inf')
        
        if side == 'BUY' and price >= best_ask:
            return self._create_error_response("Post-only order would cross spread")
        elif side == 'SELL' and price <= best_bid:
            return self._create_error_response("Post-only order would cross spread")
        
        # Post-only order placed successfully (maker fee)
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
    
    def _simulate_reduce_only_execution(self, side: str, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Simulate reduce-only order execution"""
        
        # Reduce-only orders can only reduce existing positions
        # For simulation, we assume there's an existing position to reduce
        
        levels = self.order_book_snapshot['bids'] if side == 'BUY' else self.order_book_snapshot['asks']
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
    
    def calculate_margin_requirement(self, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Calculate margin requirements"""
        
        position_value = size * price
        required_margin = position_value / leverage
        
        # Maintenance margin (typically 50% of initial margin)
        maintenance_margin = required_margin * 0.5
        
        return {
            "position_value": position_value,
            "leverage": leverage,
            "required_margin": required_margin,
            "maintenance_margin": maintenance_margin,
            "max_position_size": required_margin * leverage / price
        }
    
    def simulate_liquidation(self, position_value: float, current_margin: float, maintenance_margin: float) -> bool:
        """Simulate liquidation check"""
        return current_margin < maintenance_margin
    
    def calculate_funding_rate(self, mark_price: float, index_price: float) -> float:
        """Calculate funding rate based on mark/index price difference"""
        
        # Simplified funding rate calculation
        price_diff = (mark_price - index_price) / index_price
        funding_rate = price_diff * 0.0001  # 0.01% per hour base rate
        
        # Clamp to reasonable range
        funding_rate = max(-0.0075, min(0.0075, funding_rate))  # ±0.75% per hour max
        
        return funding_rate

# Global simulator instance
hyperliquid_simulator = HyperliquidSimulator()
