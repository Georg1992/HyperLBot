#!/usr/bin/env python3
"""
Real-Time Trading Data Manager (Compatibility Layer)
Redirects to the new refactored Data Manager Coordinator
This maintains 100% backward compatibility with existing code
"""

from loguru import logger

# Import the new coordinator
from core.data.data_manager_coordinator import trading_data_manager as _new_coordinator

# Compatibility class that redirects all calls to the new coordinator
class RealTimeTradingDataManager:
    """
    Compatibility wrapper for the refactored data management system
    All methods redirect to the new coordinator to maintain backward compatibility
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for compatibility"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        logger.success("🔄 Real-Time Data Manager (Compatibility Layer) initialized")
    
    # Redirect all method calls to the new coordinator
    def __getattr__(self, name):
        """Redirect all attribute access to the new coordinator"""
        return getattr(_new_coordinator, name)
    
    @property
    def current_state(self):
        """Compatibility property for current_state access"""
        return _new_coordinator.get_current_state()


# Create the compatibility instance
trading_data_manager = RealTimeTradingDataManager()

# Also create the old variable name for maximum compatibility
RealTimeTradingDataManager._instance = trading_data_manager

logger.info("🔄 Compatibility layer active - all calls redirected to new architecture")