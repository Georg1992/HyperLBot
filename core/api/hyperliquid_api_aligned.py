#!/usr/bin/env python3
"""
Hyperliquid API Interface - Aligned with Real API
This interface defines the exact structure that real Hyperliquid API would use,
ensuring seamless transition from simulation to live trading.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import time

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
    """Order request structure matching Hyperliquid API"""
    symbol: str
    side: OrderSide
    size: float  # Position size in BTC
    order_type: OrderType
    price: Optional[float] = None  # Required for LIMIT orders
    leverage: int = 1
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reduce_only: bool = False
    post_only: bool = False
    client_id: Optional[str] = None
    time_in_force: str = "Gtc"  # Good Till Cancelled

@dataclass
class OrderResponse:
    """Order response structure matching Hyperliquid API"""
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
    """Position structure matching Hyperliquid API"""
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

class HyperliquidAPIInterface:
    """
    Interface that defines the exact structure for real Hyperliquid API calls.
    This ensures the simulator and real API have identical interfaces.
    """
    
    def __init__(self, is_simulated: bool = True):
        """
        Initialize API interface
        
        Args:
            is_simulated: True for simulator, False for real API
        """
        self.is_simulated = is_simulated
        self.base_url = "https://api.hyperliquid.xyz" if not is_simulated else "simulator"
        
    def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """
        Place an order - identical interface for both simulator and real API
        
        Args:
            order_request: Order request with all parameters
            
        Returns:
            Order response with execution details
        """
        if self.is_simulated:
            return self._simulate_order_execution(order_request)
        else:
            return self._real_order_execution(order_request)
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        if self.is_simulated:
            return self._simulate_order_cancellation(order_id)
        else:
            return self._real_order_cancellation(order_id)
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """Get open orders"""
        if self.is_simulated:
            return self._simulate_get_open_orders(symbol)
        else:
            return self._real_get_open_orders(symbol)
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get open positions"""
        if self.is_simulated:
            return self._simulate_get_positions(symbol)
        else:
            return self._real_get_positions(symbol)
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if self.is_simulated:
            return self._simulate_get_account_info()
        else:
            return self._real_get_account_info()
    
    # Simulation methods (implemented by HyperliquidSimulator)
    def _simulate_order_execution(self, order_request: OrderRequest) -> OrderResponse:
        """To be implemented by HyperliquidSimulator"""
        raise NotImplementedError("To be implemented by simulator")
    
    def _simulate_order_cancellation(self, order_id: str) -> Dict[str, Any]:
        """To be implemented by HyperliquidSimulator"""
        raise NotImplementedError("To be implemented by simulator")
    
    def _simulate_get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """To be implemented by HyperliquidSimulator"""
        raise NotImplementedError("To be implemented by simulator")
    
    def _simulate_get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """To be implemented by HyperliquidSimulator"""
        raise NotImplementedError("To be implemented by simulator")
    
    def _simulate_get_account_info(self) -> Dict[str, Any]:
        """To be implemented by HyperliquidSimulator"""
        raise NotImplementedError("To be implemented by simulator")
    
    # Real API methods (to be implemented when switching to live trading)
    def _real_order_execution(self, order_request: OrderRequest) -> OrderResponse:
        """Real Hyperliquid API order execution"""
        # This will be implemented when switching to live trading
        # Will use actual Hyperliquid API calls
        raise NotImplementedError("Real API not yet implemented")
    
    def _real_order_cancellation(self, order_id: str) -> Dict[str, Any]:
        """Real Hyperliquid API order cancellation"""
        raise NotImplementedError("Real API not yet implemented")
    
    def _real_get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """Real Hyperliquid API get open orders"""
        raise NotImplementedError("Real API not yet implemented")
    
    def _real_get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Real Hyperliquid API get positions"""
        raise NotImplementedError("Real API not yet implemented")
    
    def _real_get_account_info(self) -> Dict[str, Any]:
        """Real Hyperliquid API get account info"""
        raise NotImplementedError("Real API not yet implemented")

# Global API interface instance
_global_api_interface = None

def get_global_api_interface(is_simulated: bool = True) -> HyperliquidAPIInterface:
    """Get global API interface instance"""
    global _global_api_interface
    if _global_api_interface is None:
        _global_api_interface = HyperliquidAPIInterface(is_simulated=is_simulated)
    return _global_api_interface
