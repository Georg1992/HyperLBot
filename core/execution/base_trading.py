#!/usr/bin/env python3
"""
Base Trading Class - Common functionality for all trading classes
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from loguru import logger

class BaseTrading(ABC):
    """Base class for all trading implementations"""
    
    def __init__(self):
        self.positions = []
        self.trades = []
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions - common implementation"""
        try:
            open_positions = [pos for pos in self.positions if pos.get('status') == 'OPEN']
            logger.debug(f"📊 Found {len(open_positions)} open positions")
            return open_positions
        except Exception as e:
            logger.error(f"❌ Failed to get open positions: {e}")
            return []
    
    def add_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Add a trade to the history - common implementation"""
        try:
            trade_data['timestamp'] = trade_data.get('timestamp', self._get_current_timestamp())
            self.trades.append(trade_data)
            logger.debug(f"📝 Added trade: {trade_data.get('side', 'UNKNOWN')} {trade_data.get('size', 0)}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add trade: {e}")
            return False
    
    def place_paper_trade(self, side: str, size: float, price: float, **kwargs) -> Dict[str, Any]:
        """Place a paper trade - common implementation"""
        try:
            trade_data = {
                'side': side,
                'size': size,
                'price': price,
                'timestamp': self._get_current_timestamp(),
                'type': 'PAPER',
                **kwargs
            }
            
            # Add to trades
            self.add_trade(trade_data)
            
            # Create position if it's a new position
            position_data = {
                'side': side,
                'size': size,
                'entry_price': price,
                'status': 'OPEN',
                'timestamp': self._get_current_timestamp(),
                **kwargs
            }
            self.positions.append(position_data)
            
            logger.info(f"📊 Paper trade placed: {side} {size} @ {price}")
            return {
                'success': True,
                'trade_id': f"paper_{len(self.trades)}",
                'data': trade_data
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to place paper trade: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp - common utility"""
        import time
        return time.time()
    
    @abstractmethod
    def connect(self) -> bool:
        """Abstract method for connecting - must be implemented by subclasses"""
        pass
