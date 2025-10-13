#!/usr/bin/env python3
"""
Trading Mode Configuration
Controls whether to use simulation or real Hyperliquid API
"""

import os
from typing import Dict, Any

class TradingMode:
    """Trading mode configuration"""
    
    # Trading modes
    SIMULATION = "simulation"
    LIVE = "live"
    
    def __init__(self):
        # Default to simulation mode
        self.mode = os.getenv("TRADING_MODE", self.SIMULATION).lower()
        
        # Validate mode
        if self.mode not in [self.SIMULATION, self.LIVE]:
            self.mode = self.SIMULATION
            print(f"⚠️ Invalid trading mode, defaulting to {self.mode}")
    
    def is_simulation(self) -> bool:
        """Check if running in simulation mode"""
        return self.mode == self.SIMULATION
    
    def is_live(self) -> bool:
        """Check if running in live trading mode"""
        return self.mode == self.LIVE
    
    def get_mode(self) -> str:
        """Get current trading mode"""
        return self.mode
    
    def switch_to_simulation(self):
        """Switch to simulation mode"""
        self.mode = self.SIMULATION
        os.environ["TRADING_MODE"] = self.SIMULATION
        print("🔄 Switched to SIMULATION mode")
    
    def switch_to_live(self):
        """Switch to live trading mode"""
        self.mode = self.LIVE
        os.environ["TRADING_MODE"] = self.LIVE
        print("🚀 Switched to LIVE trading mode")
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration based on current mode"""
        if self.is_simulation():
            return {
                "use_simulator": True,
                "api_url": "simulator",
                "requires_auth": False,
                "risk_level": "low"
            }
        else:
            return {
                "use_simulator": False,
                "api_url": "https://api.hyperliquid.xyz",
                "requires_auth": True,
                "risk_level": "high"
            }

# Global trading mode instance
_global_trading_mode = None

def get_global_trading_mode() -> TradingMode:
    """Get global trading mode instance"""
    global _global_trading_mode
    if _global_trading_mode is None:
        _global_trading_mode = TradingMode()
    return _global_trading_mode

# Convenience functions
def is_simulation_mode() -> bool:
    """Check if running in simulation mode"""
    return get_global_trading_mode().is_simulation()

def is_live_mode() -> bool:
    """Check if running in live trading mode"""
    return get_global_trading_mode().is_live()

def switch_to_simulation():
    """Switch to simulation mode"""
    get_global_trading_mode().switch_to_simulation()

def switch_to_live():
    """Switch to live trading mode"""
    get_global_trading_mode().switch_to_live()
