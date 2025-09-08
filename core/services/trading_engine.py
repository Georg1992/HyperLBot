#!/usr/bin/env python3
"""
Trading Engine Service
Handles core trading decisions and logic
Single Responsibility: Trading decision making
"""

import time
from typing import Dict, Any, Optional
from loguru import logger
from core.constants import technical_constants
from core.market_data_manager import market_data_manager

class TradingEngine:
    """Pure execution engine - executes trades based on signals from PredictionEngine/ReactiveEngine"""
    
    def __init__(self, config, strategy_config, trade_quality_manager, position_lifecycle_manager, variability_analyzer):
        self.config = config
        self.strategy_config = strategy_config
        self.trade_quality_manager = trade_quality_manager
        self.position_lifecycle_manager = position_lifecycle_manager
        self.variability_analyzer = variability_analyzer
        
        # Trading state
        self.last_trade_time = 0
        
        logger.info("🧠 Trading Engine initialized - Pure execution engine (no strategy decisions)")
    
    def should_trade(self, hyperliquid_price: float, yahoo_analysis: Dict[str, Any], hyperliquid_api, strategy_name: str = "standard", 
                    prediction_signal: Dict[str, Any] = None, reactive_signal: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Pure execution engine - executes trades based on signals from PredictionEngine/ReactiveEngine
        
        RESPONSIBILITY: Only execute trades, not make trading decisions
        INPUT: Trading signals from prediction/reaction engines
        OUTPUT: Execution decision (should_trade, side, size, etc.)
        """
        if not yahoo_analysis or "error" in yahoo_analysis:
            return {"should_trade": False, "reason": "No market analysis available"}
        
        # 1. CHECK TIME INTERVAL (execution constraint)
        current_time = time.time()
        min_interval = self.strategy_config["min_interval"]
        if current_time - self.last_trade_time < min_interval:
            return {"should_trade": False, "reason": f"Too soon since last trade (need {min_interval}s)"}
        
        # 2. GATHER MARKET DATA (for engines to use)
        hyperliquid_data = market_data_manager.get_hyperliquid_data(hyperliquid_api, "BTC")
        volume_data = hyperliquid_data.get("volume_data", {})
        pressure_data = hyperliquid_data.get("pressure_data", {})
        
        # Update variability analyzer
        orderbook_depth = volume_data.get("volume_depth", 100)
        self.variability_analyzer.add_price_data(hyperliquid_price, volume=orderbook_depth)
        
        # 3. BUILD MARKET DATA FOR ENGINES
        market_data = yahoo_analysis.copy()
        market_data["hyperliquid_volume"] = volume_data
        market_data["hyperliquid_pressure"] = pressure_data
        market_data["current_price"] = hyperliquid_price
        market_data["timestamp"] = current_time
        
        # 4. EVALUATE SIGNALS FROM PREDICTION AND REACTIVE ENGINES
        execution_decision = self._evaluate_trading_signals(
            prediction_signal, reactive_signal, hyperliquid_price, market_data
        )
        
        return execution_decision
    
    def _evaluate_trading_signals(self, prediction_signal: Dict[str, Any], reactive_signal: Dict[str, Any], 
                                 current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate signals from Prediction Engine and Reactive Engine
        Priority: Reactive Engine (emergency) > Prediction Engine (planned)
        """
        try:
            # 1. CHECK REACTIVE ENGINE SIGNAL (HIGHEST PRIORITY - EMERGENCY)
            if reactive_signal and self._is_valid_reactive_signal(reactive_signal):
                return self._process_reactive_signal(reactive_signal, current_price, market_data)
            
            # 2. CHECK PREDICTION ENGINE SIGNAL (SECOND PRIORITY - PLANNED)
            if prediction_signal and self._is_valid_prediction_signal(prediction_signal):
                return self._process_prediction_signal(prediction_signal, current_price, market_data)
            
            # 3. NO VALID SIGNALS
            return {
                "should_trade": False,
                "reason": "No valid signals from engines",
                "signal_source": "none"
            }
            
        except Exception as e:
            logger.error(f"❌ Signal evaluation failed: {e}")
            return {
                "should_trade": False,
                "reason": f"Signal evaluation error: {e}",
                "signal_source": "error"
            }
    
    def _is_valid_reactive_signal(self, reactive_signal: Dict[str, Any]) -> bool:
        """Check if reactive signal is valid for execution"""
        try:
            if not reactive_signal:
                return False
            
            # Check required fields
            required_fields = ["direction", "confidence", "urgency", "execution_type"]
            for field in required_fields:
                if field not in reactive_signal:
                    return False
            
            # Check confidence threshold (reactive signals need high confidence)
            confidence = reactive_signal.get("confidence", 0)
            if confidence < 0.6:  # 60% minimum confidence for reactive signals
                return False
            
            # Check urgency (only execute HIGH and CRITICAL urgency)
            urgency = reactive_signal.get("urgency", "")
            if urgency not in ["HIGH", "CRITICAL"]:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Reactive signal validation failed: {e}")
            return False
    
    def _is_valid_prediction_signal(self, prediction_signal: Dict[str, Any]) -> bool:
        """Check if prediction signal is valid for execution"""
        try:
            if not prediction_signal:
                return False
            
            # Check required fields (new format)
            required_fields = ["direction", "confidence", "entry_price", "stop_loss", "take_profit", "position_size"]
            for field in required_fields:
                if field not in prediction_signal:
                    return False
            
            # Check confidence threshold (prediction signals need very high confidence)
            confidence = prediction_signal.get("confidence", 0)
            if confidence < 0.7:  # 70% minimum confidence for prediction signals
                return False
            
            # Check that prices are valid
            entry_price = prediction_signal.get("entry_price", 0)
            stop_loss = prediction_signal.get("stop_loss", 0)
            take_profit = prediction_signal.get("take_profit", 0)
            position_size = prediction_signal.get("position_size", 0)
            
            if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0 or position_size <= 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Prediction signal validation failed: {e}")
            return False
    
    def _process_reactive_signal(self, reactive_signal: Dict[str, Any], current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process reactive signal for emergency execution"""
        try:
            direction = reactive_signal.get("direction", "").upper()
            confidence = reactive_signal.get("confidence", 0)
            urgency = reactive_signal.get("urgency", "")
            execution_type = reactive_signal.get("execution_type", "MARKET_ORDER")
            size_percentage = reactive_signal.get("size_percentage", 0.2)
            reasoning = reactive_signal.get("reasoning", "Reactive signal")
            
            # Calculate position size based on urgency and confidence
            base_size = 0.001  # Base size in BTC
            size_multiplier = size_percentage  # 0.2 to 0.8 based on urgency
            
            if urgency == "CRITICAL":
                size_multiplier = min(0.8, size_percentage)
            elif urgency == "HIGH":
                size_multiplier = min(0.6, size_percentage)
            else:
                size_multiplier = min(0.4, size_percentage)
            
            position_size = base_size * size_multiplier
            
            # Determine order type
            if execution_type == "MARKET_ORDER":
                order_type = "market"
                entry_price = current_price  # Market order uses current price
            else:
                order_type = "limit"
                # Use the entry price from the prediction engine - don't override it!
                entry_price = reactive_signal.get("entry_price", current_price)
            
            logger.info(f"⚡ REACTIVE EXECUTION: {direction} {position_size:.4f} BTC at ${entry_price:,.2f} ({urgency} urgency, {confidence:.1%} confidence)")
            
            return {
                "should_trade": True,
                "side": direction,
                "size": position_size,
                "entry_price": entry_price,
                "order_type": order_type,
                "leverage": 30,  # Default leverage
                "reason": f"Reactive signal: {reasoning}",
                "signal_source": "reactive_engine",
                "confidence": confidence,
                "urgency": urgency,
                "execution_type": execution_type
            }
            
        except Exception as e:
            logger.error(f"❌ Reactive signal processing failed: {e}")
            return {
                "should_trade": False,
                "reason": f"Reactive signal processing error: {e}",
                "signal_source": "reactive_engine"
            }
    
    def _process_prediction_signal(self, prediction_signal: Dict[str, Any], current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process prediction signal for planned execution"""
        try:
            direction = prediction_signal.get("direction", "").upper()
            confidence = prediction_signal.get("confidence", 0)
            reasoning = prediction_signal.get("reasoning", "Prediction signal")
            
            # Extract prediction details (new format)
            entry_price = prediction_signal.get("entry_price", current_price)
            stop_loss = prediction_signal.get("stop_loss", 0)
            take_profit = prediction_signal.get("take_profit", 0)
            position_size = prediction_signal.get("position_size", 0.001)
            
            # Prediction signals always use limit orders for better prices
            order_type = "limit"
            
            logger.info(f"🎯 PREDICTION EXECUTION: {direction} {position_size:.4f} BTC at ${entry_price:,.2f} ({confidence:.1%} confidence)")
            logger.info(f"   Stop Loss: ${stop_loss:,.2f}, Take Profit: ${take_profit:,.2f}")
            
            return {
                "should_trade": True,
                "side": direction,
                "size": position_size,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "order_type": order_type,
                "leverage": 30,  # Default leverage
                "reason": f"Prediction signal: {reasoning}",
                "signal_source": "prediction_engine",
                "confidence": confidence,
                "urgency": "NORMAL"
            }
            
        except Exception as e:
            logger.error(f"❌ Prediction signal processing failed: {e}")
            return {
                "should_trade": False,
                "reason": f"Prediction signal processing error: {e}",
                "signal_source": "prediction_engine"
            }
    
    def place_paper_trade(self, side: str, size: float = 0.001, leverage: int = 30, signal_data: Dict = None) -> bool:
        """Place a paper trade (delegate to position lifecycle manager)"""
        self.last_trade_time = time.time()
        return self.position_lifecycle_manager.place_paper_trade(side, size, leverage, signal_data)
    
    def close_paper_position(self, position: Dict, exit_reason: str, exit_price: float):
        """Close a paper position (delegate to position lifecycle manager)"""
        self.position_lifecycle_manager.close_paper_position(position, exit_reason, exit_price)
    
    def check_position_exits(self, hyperliquid_price: float, current_analysis: Dict[str, Any] = None):
        """Check positions for exit conditions (delegate to position lifecycle manager)"""
        self.position_lifecycle_manager.check_position_exits(hyperliquid_price, current_analysis)
    
    def get_open_positions(self):
        """Get open positions (delegate to position lifecycle manager)"""
        return self.position_lifecycle_manager.get_open_positions()
    
    
    