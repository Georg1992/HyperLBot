#!/usr/bin/env python3
"""
Momentum Processor - Single Responsibility: Process Momentum Signals
Extracted from SessionOrchestrator for SRP compliance
"""

from typing import Dict, Any, Optional
from loguru import logger


class MomentumProcessor:
    """Handles momentum signal processing with reactive engine"""
    
    def __init__(self, reactive_engine=None):
        """
        Initialize Momentum Processor
        
        Args:
            reactive_engine: ReactiveEngine instance (optional)
        """
        self.reactive_engine = reactive_engine
    
    def process_momentum_signals(self, unified_data: Dict[str, Any], 
                                 current_price: float, current_strategy: str) -> Optional[Dict[str, Any]]:
        """
        Process momentum signals with reactive engine (market orders)
        
        Args:
            unified_data: Unified market data dictionary
            current_price: Current market price
            current_strategy: Current trading strategy
            
        Returns:
            Momentum result dictionary if trade executed, None otherwise
        """
        if not self.reactive_engine:
            return None
        
        try:
            momentum_result = self.reactive_engine.process_market_data(
                unified_data=unified_data,
                current_price=current_price,
                current_strategy=current_strategy  # Use detected strategy for consistency
            )
            if momentum_result:
                # Momentum result is guaranteed to have direction and entry_price (NO FALLBACKS)
                direction = momentum_result["direction"]  # Required (NO FALLBACKS)
                entry_price = momentum_result["entry_price"]  # Required (NO FALLBACKS)
                logger.info(f"⚡ Momentum trade executed: {direction} @ ${entry_price:.2f}")
                return momentum_result
        except Exception as e:
            logger.warning(f"⚠️ Reactive engine check failed: {e}")
        
        return None
