#!/usr/bin/env python3
"""
Hyperliquid Transition Layer
Ensures seamless transition from simulation to real trading by:
1. Standardizing the API interface
2. Making simulator behavior match real Hyperliquid API
3. Providing easy switching mechanism
"""

from typing import Dict, Any, Optional, List
from loguru import logger

class HyperliquidTransitionLayer:
    """
    Transition layer that ensures simulator and real API have identical behavior
    """
    
    def __init__(self, use_simulator: bool = None):
        """
        Initialize transition layer
        
        Args:
            use_simulator: True for simulation, False for real API. If None, uses config.
        """
        if use_simulator is None:
            from config.trading_mode import get_global_trading_mode
            self.use_simulator = get_global_trading_mode().is_simulation()
        else:
            self.use_simulator = use_simulator
        
        self._initialize_api()
    
    def _initialize_api(self):
        """Initialize the appropriate API (simulator or real)"""
        if self.use_simulator:
            from .hyperliquid_simulator import get_global_simulator
            self.api = get_global_simulator()
            logger.info("🏦 Using Hyperliquid Simulator")
        else:
            # Real API will be implemented when switching to live trading
            from .hyperliquid_api import HyperliquidAPI
            self.api = HyperliquidAPI()
            logger.info("🚀 Using Real Hyperliquid API")
    
    def place_order(
        self,
        order_type: str,
        side: str,
        size: float,
        symbol: str = "BTC",
        price: Optional[float] = None,
        leverage: int = 40,  # Default to 40x leverage
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Place an order with standardized interface
        
        This method ensures both simulator and real API behave identically
        """
        try:
            if self.use_simulator:
                return self._place_simulated_order(
                    order_type, side, size, symbol, price, leverage, 
                    stop_loss, take_profit, client_id
                )
            else:
                return self._place_real_order(
                    order_type, side, size, symbol, price, leverage,
                    stop_loss, take_profit, client_id
                )
        except Exception as e:
            logger.error(f"❌ Order placement failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_id": None
            }
    
    def _place_simulated_order(
        self,
        order_type: str,
        side: str,
        size: float,
        symbol: str,
        price: Optional[float],
        leverage: int,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        client_id: Optional[str]
    ) -> Dict[str, Any]:
        """Place order using simulator with real API structure"""
        
        # Ensure simulator has orderbook data
        if not hasattr(self.api, 'order_book_snapshot') or not self.api.order_book_snapshot:
            logger.warning("⚠️ No orderbook data available for simulator")
            # Create minimal orderbook for simulation
            self.api.order_book_snapshot = {
                'bids': [[price or 50000, 1.0]],
                'asks': [[(price or 50000) + 1, 1.0]]
            }
        
        # Update simulator's orderbook if needed
        if hasattr(self.api, 'update_order_book'):
            self.api.update_order_book(self.api.order_book_snapshot)
        
        # Use the simulator's place_order method with all parameters
        result = self.api.place_order(
            order_type=order_type,
            side=side,
            size=size,
            symbol=symbol,
            price=price,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={"client_id": client_id} if client_id else None
        )
        
        # Standardize response format
        return self._standardize_response(result, stop_loss, take_profit)
    
    def _place_real_order(
        self,
        order_type: str,
        side: str,
        size: float,
        symbol: str,
        price: Optional[float],
        leverage: int,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        client_id: Optional[str]
    ) -> Dict[str, Any]:
        """Place order using real Hyperliquid API"""
        # This will be implemented when switching to live trading
        # For now, return an error
        return {
            "success": False,
            "error": "Real Hyperliquid API not yet implemented",
            "order_id": None
        }
    
    def _standardize_response(self, result: Dict[str, Any], stop_loss: Optional[float] = None, take_profit: Optional[float] = None) -> Dict[str, Any]:
        """Standardize response format for both simulator and real API"""
        if result.get("success", False):
            return {
                "success": True,
                "order_id": result.get("order_id", "unknown"),
                "execution_price": result.get("execution_price", 0.0),
                "execution_time": result.get("execution_time", 0.0),
                "fees": result.get("fees", {}),
                "order_status": result.get("order_status", "FILLED"),
                "slippage": result.get("slippage", 0.0),
                "position_id": result.get("position_id"),
                "stop_loss": stop_loss,  # Use the passed parameters
                "take_profit": take_profit  # Use the passed parameters
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "order_id": None
            }
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get positions with standardized format"""
        try:
            if self.use_simulator:
                return self._get_simulated_positions(symbol)
            else:
                return self._get_real_positions(symbol)
        except Exception as e:
            logger.error(f"❌ Failed to get positions: {e}")
            return []
    
    def _get_simulated_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get positions from simulator"""
        if hasattr(self.api, 'open_positions'):
            positions = []
            for trade_id, position in self.api.open_positions.items():
                if symbol is None or position.get("symbol", "BTC") == symbol:
                    positions.append({
                        "trade_id": trade_id,
                        "symbol": position.get("symbol", "BTC"),
                        "side": position.get("side"),
                        "size": position.get("size", 0.0),
                        "entry_price": position.get("entry_price", 0.0),
                        "current_price": position.get("mark_price", position.get("entry_price", 0.0)),
                        "pnl": position.get("pnl", 0.0),
                        "pnl_percentage": position.get("pnl_percentage", 0.0),
                        "leverage": position.get("leverage", 40),
                        "stop_loss": position.get("stop_loss"),
                        "take_profit": position.get("take_profit"),
                        "status": position.get("status", "OPEN")
                    })
            return positions
        return []
    
    def _get_real_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get positions from real API"""
        # This will be implemented when switching to live trading
        return []
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance with standardized format"""
        try:
            if self.use_simulator:
                return {
                    "balance": getattr(self.api, 'account_balance', 10000.0),
                    "initial_balance": getattr(self.api, 'initial_balance', 10000.0),
                    "total_pnl": getattr(self.api, 'total_pnl', 0.0),
                    "total_trades": getattr(self.api, 'total_trades', 0),
                    "winning_trades": getattr(self.api, 'winning_trades', 0),
                    "losing_trades": getattr(self.api, 'losing_trades', 0)
                }
            else:
                # Real API implementation
                return {"balance": 0.0, "error": "Real API not implemented"}
        except Exception as e:
            logger.error(f"❌ Failed to get account balance: {e}")
            return {"balance": 0.0, "error": str(e)}
    
    def switch_to_real_api(self):
        """Switch from simulator to real API"""
        self.use_simulator = False
        self._initialize_api()
        logger.info("🔄 Switched to Real Hyperliquid API")
    
    def switch_to_simulator(self):
        """Switch from real API to simulator"""
        self.use_simulator = True
        self._initialize_api()
        logger.info("🔄 Switched to Hyperliquid Simulator")

# Global transition layer instance
_global_transition_layer = None

def get_global_transition_layer(use_simulator: bool = True) -> HyperliquidTransitionLayer:
    """Get global transition layer instance"""
    global _global_transition_layer
    if _global_transition_layer is None:
        _global_transition_layer = HyperliquidTransitionLayer(use_simulator=use_simulator)
    return _global_transition_layer
