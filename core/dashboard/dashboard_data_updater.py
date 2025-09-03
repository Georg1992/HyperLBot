#!/usr/bin/env python3
"""
RTM Updater Module
Handles Real-Time Market data updates
"""

import time
from typing import Dict, Any, Optional
from loguru import logger
from core.dashboard.dashboard_data_manager import simple_rtm

class RTMUpdater:
    """Handles Real-Time Market data updates"""
    
    def __init__(self):
        self.rtm = simple_rtm
        logger.info("📡 RTM Updater initialized")
    
    def update_simple_rtm_market_data(self, market_data: Dict[str, Any]) -> None:
        """Update RTM with market data"""
        try:
            # Update market data in RTM using the correct method name
            self.rtm.update_market(market_data)
            
            # Log update
            current_price = market_data.get('current_price', 0)
            # Reduced logging frequency
            
        except Exception as e:
            logger.error(f"❌ Failed to update RTM market data: {e}")
    
    def update_simple_rtm_prediction_data(self, prediction_data: Dict[str, Any]) -> None:
        """Update RTM with prediction data (handles both initial_prediction and best_prediction)"""
        try:
            # Handle initial session prediction
            initial_prediction = prediction_data.get("initial_prediction")
            if initial_prediction:
                order_structure = initial_prediction.get("order_structure", {})
                market_analysis = initial_prediction.get("market_analysis", {})
                
                signal_data = {
                    "type": "INITIAL_PREDICTION",
                    "direction": order_structure.get("direction", "UNKNOWN"),
                    "confidence": initial_prediction.get("confidence", 0),
                    "reasoning": initial_prediction.get("reasoning", ""),
                    "entry_price": order_structure.get("entry_price", 0),
                    "stop_loss": order_structure.get("stop_loss", 0),
                    "take_profit": order_structure.get("take_profit", 0),
                    "size_btc": 0.001,  # Default for initial prediction
                    "size_usd": order_structure.get("entry_price", 0) * 0.001,
                    "rsi": market_analysis.get("rsi", 50),
                    "trend": market_analysis.get("trend", "NEUTRAL"),
                    "prediction_data": {
                        "order_structure": order_structure,
                        "market_analysis": market_analysis,
                        "prediction_type": initial_prediction.get("prediction_type", "INITIAL"),
                        "session_strategy": initial_prediction.get("session_strategy", "standard")
                    }
                }
                self.rtm.add_signal(signal_data)
                logger.success(f"✅ Initial prediction stored: {signal_data['direction']} @ ${signal_data['entry_price']:.2f}")
                return
            
            # Handle ongoing predictions (best_prediction format)
            best_prediction = prediction_data.get("best_prediction", {})
            if best_prediction:
                signal_data = {
                    "type": best_prediction.get("side", "UNKNOWN"),
                    "confidence": best_prediction.get("confidence", 0),
                    "reason": best_prediction.get("reason", ""),
                    "price": best_prediction.get("entry_price", 0)
                }
                self.rtm.add_signal(signal_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to update RTM prediction data: {e}")
    
    def update_simple_rtm_trading_data(self, trading_data: Dict[str, Any]) -> None:
        """Update RTM with trading data"""
        try:
            # Add trade data if available
            if "trade" in trading_data:
                trade_data = trading_data["trade"]
                self.rtm.add_trade(trade_data)
                
                # Log update
                side = trade_data.get("side", "UNKNOWN")
                size = trade_data.get("size", 0)
                # Reduced logging frequency
            
        except Exception as e:
            logger.error(f"❌ Failed to update RTM trading data: {e}")
    
    def update_simple_rtm_session_data(self, session_data: Dict[str, Any]) -> None:
        """Update RTM with session data"""
        try:
            # Session data is handled by the session manager, not directly by RTM
            # Just log the update
            status = session_data.get("status", "UNKNOWN")
            # Reduced logging frequency
            
        except Exception as e:
            logger.error(f"❌ Failed to update RTM session data: {e}")
    
    def update_simple_rtm_account_data(self, account_data: Dict[str, Any]) -> None:
        """Update RTM with account data"""
        try:
            # Account data is handled by the account manager, not directly by RTM
            # Just log the update
            balance = account_data.get("balance", 0)
            # Reduced logging frequency
            
        except Exception as e:
            logger.error(f"❌ Failed to update RTM account data: {e}")
    
    def update_simple_rtm_analysis_data(self, analysis_data: Dict[str, Any]) -> None:
        """Update RTM with analysis data"""
        try:
            # Analysis data is part of market data, so we can update it through market data
            # Just log the update
            trend = analysis_data.get("trend", "UNKNOWN")
            # Try different possible RSI keys
            rsi = analysis_data.get("rsi_value", analysis_data.get("rsi", 0))
            # Handle None RSI values gracefully
            rsi_display = f"{rsi:.1f}" if rsi is not None else "N/A"
            # Reduced logging frequency
            
        except Exception as e:
            logger.error(f"❌ Failed to update RTM analysis data: {e}")
    
    def update_simple_rtm_activity(self, message: str, level: str = "INFO") -> None:
        """Update RTM with activity"""
        try:
            self.rtm.add_activity(message, level, "bot")
            # Reduced logging frequency
        except Exception as e:
            logger.error(f"❌ Failed to update RTM activity: {e}")
    
    def get_rtm_state(self) -> Dict[str, Any]:
        """Get current RTM state"""
        try:
            return self.rtm.get_data()
        except Exception as e:
            logger.error(f"❌ Failed to get RTM state: {e}")
            return {}
    
    def clear_rtm_cache(self) -> None:
        """Clear RTM cache"""
        try:
            self.rtm.clear_presentation_data()
            logger.info("🗑️ RTM cache cleared")
        except Exception as e:
            logger.error(f"❌ Failed to clear RTM cache: {e}")
    
    def update_all_rtm_data(self, 
                           market_data: Dict[str, Any] = None,
                           prediction_data: Dict[str, Any] = None,
                           trading_data: Dict[str, Any] = None,
                           session_data: Dict[str, Any] = None,
                           account_data: Dict[str, Any] = None,
                           analysis_data: Dict[str, Any] = None) -> None:
        """Update all RTM data at once"""
        try:
            if market_data:
                self.update_simple_rtm_market_data(market_data)
            
            if prediction_data:
                self.update_simple_rtm_prediction_data(prediction_data)
            
            if trading_data:
                self.update_simple_rtm_trading_data(trading_data)
            
            if session_data:
                self.update_simple_rtm_session_data(session_data)
            
            if account_data:
                self.update_simple_rtm_account_data(account_data)
            
            if analysis_data:
                self.update_simple_rtm_analysis_data(analysis_data)
                
        except Exception as e:
            logger.error(f"❌ Failed to update all RTM data: {e}")
    
    def validate_rtm_connection(self) -> bool:
        """Validate RTM connection"""
        try:
            state = self.get_rtm_state()
            return state is not None
        except Exception as e:
            logger.error(f"❌ RTM connection validation failed: {e}")
            return False
