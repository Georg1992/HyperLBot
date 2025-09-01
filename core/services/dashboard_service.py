#!/usr/bin/env python3
"""
Dashboard Service
Handles all dashboard updates and heartbeat management
Single Responsibility: Dashboard coordination
"""

import os
import time
import json
from typing import Dict, Any
from loguru import logger
from core.dashboard.dashboard_data_manager import simple_rtm

class DashboardService:
    """Dashboard coordination service - handles RTM updates and heartbeats"""
    
    def __init__(self, rtm_updater, heartbeat_file=None):
        self.rtm_updater = rtm_updater
        self.heartbeat_file = heartbeat_file or "data/temp/bot_heartbeat.json"
        
        # Heartbeat state
        self.last_heartbeat = 0
        self.heartbeat_interval = 30  # 30 seconds
        
        logger.info("🎛️ Dashboard Service initialized - RTM coordination")
    
    def update_rtm_market(self, market_data: Dict[str, Any]):
        """Update SimpleRTM with market data"""
        try:
            self.rtm_updater.update_simple_rtm_market_data(market_data)
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM market: {e}")
    
    def update_rtm_data_status(self, data_status: Dict[str, Any]):
        """Update SimpleRTM data status"""
        try:
            self.rtm_updater.update_simple_rtm_analysis_data(data_status)
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM data status: {e}")
    
    def update_rtm_activity(self, message: str, level: str = "INFO"):
        """Update SimpleRTM with activity"""
        try:
            simple_rtm.add_activity(message, level, "bot")
            logger.info(f"📊 RTM Activity: {message}")
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM activity: {e}")
    
    def update_rtm_signal(self, signal_data: Dict[str, Any]):
        """Update SimpleRTM with signal"""
        try:
            self.rtm_updater.update_simple_rtm_prediction_data({"best_prediction": signal_data})
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM signal: {e}")
    
    def generate_and_log_prediction(self, current_price: float, historical_analysis: Dict[str, Any] = None, 
                                   prediction_engine=None, strategy_name: str = "standard"):
        """Generate structured prediction and log to dashboard"""
        try:
            if not prediction_engine:
                logger.warning("⚠️ No prediction engine available")
                return
            
            # Throttle predictions to every 5 seconds
            current_time = time.time()
            if not hasattr(self, '_last_prediction_time'):
                self._last_prediction_time = 0
            
            prediction_interval = 5  # seconds
            if current_time - self._last_prediction_time < prediction_interval:
                return
            
            # Generate prediction (fix argument mismatch - method expects market_data dict)
            # Build market_data structure for prediction engine
            market_data_for_prediction = {
                "current_price": current_price,
                "rsi": historical_analysis.get("rsi_5m") if historical_analysis else 50.0,
                "trend": historical_analysis.get("trend_5m", {}).get("trend", "NEUTRAL") if historical_analysis else "NEUTRAL",
                "volume_category": "NORMAL",  # Default for predictions
                "volatility_5m": historical_analysis.get("volatility_5m", 0.0) if historical_analysis else 0.0
            }
            
            prediction = prediction_engine.generate_structured_prediction(
                market_data_for_prediction, historical_analysis
            )
            
            if prediction:
                # Extract prediction data
                direction = prediction.get("side", "HOLD")
                size_btc = prediction.get("size", 0.001)
                size_usd = prediction.get("size_usd", 0)
                entry_price = prediction.get("entry_price", current_price)
                rsi_value = prediction.get("rsi_at_prediction", technical_constants.RSI_NEUTRAL)
                trend_value = prediction.get("trend_at_prediction", "NEUTRAL")
                confidence = prediction.get("confidence", 0.3)
                
                # Log prediction to activity (dashboard)
                prediction_message = (
                    f"🔮 {direction} Signal | "
                    f"Size: {size_btc:.4f} BTC (${size_usd:.0f}) | "
                    f"Entry: ${entry_price:.2f} | "
                    f"RSI: {rsi_value} | "
                    f"TREND: {trend_value} | "
                    f"Confidence: {confidence:.1%}"
                )
                
                self.update_rtm_activity(prediction_message, "INFO")
                
                # Store prediction in SimpleRTM for dashboard predictions panel (COMPLETE structure)
                prediction_for_dashboard = {
                    "type": "prediction",
                    "side": direction,
                    "price": entry_price,
                    "size": size_btc,
                    "confidence": confidence,
                    "timestamp": current_time,
                    
                    # COMPLETE prediction data for dashboard (exact fields expected)
                    "prediction_data": {
                        "direction": direction,
                        "entry_price": entry_price,
                        "size_btc": size_btc,
                        "size_usd": size_usd,
                        "rsi_at_prediction": rsi_value,
                        "trend_at_prediction": trend_value,
                        "confidence": confidence,
                        "reasoning": prediction.get("reasoning", f"{direction} signal based on market analysis")
                    }
                }
                
                simple_rtm.add_signal(prediction_for_dashboard)
                
                self._last_prediction_time = current_time
                logger.debug(f"🎯 Generated prediction: {direction} @ ${entry_price:.2f} (RSI: {rsi_value}, Trend: {trend_value})")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate prediction: {e}")
    
    def create_initial_heartbeat(self, session_manager=None, strategy_name: str = "standard", paper_balance: float = 0.0):
        """Create initial heartbeat file immediately when bot starts"""
        self._write_heartbeat(is_initial=True, session_manager=session_manager, 
                             strategy_name=strategy_name, paper_balance=paper_balance)
    
    def update_heartbeat(self, session_manager=None, strategy_name: str = "standard", paper_balance: float = 0.0):
        """Update bot heartbeat to indicate it's still running"""
        current_time = time.time()
        if current_time - self.last_heartbeat >= self.heartbeat_interval:
            self._write_heartbeat(is_initial=False, session_manager=session_manager,
                                 strategy_name=strategy_name, paper_balance=paper_balance)
    
    def cleanup_heartbeat(self):
        """Clean up heartbeat file when bot stops"""
        try:
            if os.path.exists(self.heartbeat_file):
                os.remove(self.heartbeat_file)
        except Exception as e:
            logger.error(f"❌ Could not cleanup heartbeat: {e}")
    
    def _write_heartbeat(self, is_initial: bool = False, session_manager=None, 
                        strategy_name: str = "standard", paper_balance: float = 0.0):
        """Write heartbeat file - consolidated logic"""
        try:
            current_time = time.time()
            heartbeat_data = {
                "bot_running": True,
                "last_heartbeat": current_time,
                "session_id": getattr(session_manager, 'current_session_id', None) if session_manager else None,
                "strategy": strategy_name,
                "balance": paper_balance
            }
            
            # Ensure temp directory exists
            os.makedirs(os.path.dirname(self.heartbeat_file), exist_ok=True)
            
            with open(self.heartbeat_file, 'w') as f:
                json.dump(heartbeat_data, f, indent=2)
            
            self.last_heartbeat = current_time
            
            if is_initial:
                logger.info("💓 Initial bot heartbeat created")
                
        except Exception as e:
            logger.error(f"❌ Could not {'create' if is_initial else 'update'} heartbeat: {e}")