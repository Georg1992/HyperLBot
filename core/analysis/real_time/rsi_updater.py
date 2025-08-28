#!/usr/bin/env python3
"""
Real-Time RSI Updater
Continuously updates RSI with live Hyperliquid price data
"""

import time
import threading
from typing import Optional, Callable
from loguru import logger
from core.analysis.real_time.rsi_calculator import real_time_rsi_calculator
from core.hyperliquid_api import HyperliquidAPI

class RealTimeRSIUpdater:
    """Real-time RSI updater that continuously fetches Hyperliquid prices"""
    
    def __init__(self, update_interval: float = 1.0):
        self.update_interval = update_interval
        self.hyperliquid_api = HyperliquidAPI()
        self.is_running = False
        self.update_thread = None
        self.last_price = None
        self.last_rsi = None
        self.callback = None
        
        logger.info(f"📊 Real-time RSI Updater initialized (interval: {update_interval}s)")
    
    def start(self, callback: Optional[Callable] = None) -> None:
        """Start the real-time RSI updater"""
        if self.is_running:
            logger.warning("⚠️ RSI updater is already running")
            return
        
        self.callback = callback
        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("🚀 Real-time RSI updater started")
    
    def stop(self) -> None:
        """Stop the real-time RSI updater"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
        logger.info("⏹️ Real-time RSI updater stopped")
    
    def _update_loop(self) -> None:
        """Main update loop"""
        while self.is_running:
            try:
                # Get current Hyperliquid price
                current_price = self.hyperliquid_api.get_current_price()
                
                if current_price and current_price > 0:
                    # Add price to RSI calculator
                    real_time_rsi_calculator.add_price(current_price)
                    
                    # Get updated RSI
                    rsi_result = real_time_rsi_calculator.calculate_rsi()
                    current_rsi = rsi_result.get("rsi")
                    
                    # Check if RSI changed significantly
                    if (self.last_price != current_price or 
                        (self.last_rsi is None) or 
                        abs(current_rsi - self.last_rsi) > 0.1):
                        
                        logger.debug(f"📈 RSI Update: Price: {current_price:.2f} → RSI: {current_rsi:.2f}")
                        
                        # Call callback if provided
                        if self.callback:
                            self.callback({
                                "price": current_price,
                                "rsi": current_rsi,
                                "trend": rsi_result.get("trend"),
                                "signal": rsi_result.get("signal"),
                                "timestamp": time.time()
                            })
                    
                    self.last_price = current_price
                    self.last_rsi = current_rsi
                
                # Wait for next update
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"❌ RSI update error: {e}")
                time.sleep(self.update_interval)
    
    def get_current_rsi(self) -> Optional[float]:
        """Get the current RSI value"""
        return real_time_rsi_calculator.get_cached_rsi()
    
    def get_rsi_data(self) -> dict:
        """Get complete RSI data"""
        return real_time_rsi_calculator.calculate_rsi()
    
    def get_status(self) -> dict:
        """Get updater status"""
        return {
            "is_running": self.is_running,
            "update_interval": self.update_interval,
            "last_price": self.last_price,
            "last_rsi": self.last_rsi,
            "calculator_status": real_time_rsi_calculator.get_status()
        }

# Global instance
real_time_rsi_updater = RealTimeRSIUpdater()
