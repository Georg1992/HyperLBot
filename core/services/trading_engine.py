#!/usr/bin/env python3
"""
Trading Engine Service
Handles core trading decisions and logic
Single Responsibility: Trading decision making
"""

from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger

class TradingEngine:
    """Pure execution engine - executes trades based on signals from AI system"""
    
    def __init__(self, config, strategy_config, trade_quality_manager, position_lifecycle_manager, variability_analyzer):
        self.config = config
        self.strategy_config = strategy_config
        self.trade_quality_manager = trade_quality_manager
        self.position_lifecycle_manager = position_lifecycle_manager
        self.variability_analyzer = variability_analyzer
        
        # Trading state
        self.last_trade_time = 0
        
        logger.info("🧠 Trading Engine initialized - Pure execution engine (no strategy decisions)")
    
    def get_open_positions(self):
        """Get open positions (delegate to position lifecycle manager)"""
        return self.position_lifecycle_manager.get_open_positions()
    
    
    
