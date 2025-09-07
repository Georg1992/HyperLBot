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
    
    def should_trade(self, hyperliquid_price: float, yahoo_analysis: Dict[str, Any], hyperliquid_api, strategy_name: str = "standard") -> Dict[str, Any]:
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
        
        # 4. GET SIGNALS FROM PREDICTION AND REACTIVE ENGINES
        # TODO: This will be implemented in next steps
        # Signals will come from external engines (PredictionEngine/ReactiveEngine)
        
        # 5. MARKET CONDITIONS CHECK (safety filter)
        from strategies.market_conditions_analyzer import global_conditions_analyzer
        
        conditions_analysis = global_conditions_analyzer.analyze_trading_conditions(
            market_data={
                "current_price": hyperliquid_price,
                "rsi": market_data.get("rsi_5m", 50.0),
                "trend": market_data.get("trend_5m", {}).get("trend", "NEUTRAL"),
                "volatility_5m": market_data.get("volatility_5m", 0.0),
                "volatility_category": market_data.get("volatility_5m_category", "MODERATE"),
                "volume_category": volume_data.get("volume_category", "NORMAL"),
                "timestamp": current_time
            },
            historical_context={},
            strategy_name=strategy_name
        )
        
        # BLOCK TRADING if conditions are untradable (safety filter)
        if not conditions_analysis["is_tradable"]:
            untradable_reason = global_conditions_analyzer.get_untradable_condition_summary(conditions_analysis)
            return {
                "should_trade": False, 
                "reason": f"⚠️ {untradable_reason}"
            }
        
        # 6. TRADING LOGIC DISABLED - Waiting for external signal integration
        return {
            "should_trade": False, 
            "reason": f"Trading disabled - Waiting for engine integration. Conditions: {conditions_analysis['condition']} ({conditions_analysis['confidence']:.0%})"
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
    
    
    
    def _calculate_smart_limit_price(self, side: str, current_price: float) -> float:
        """Calculate smart limit price with small buffer"""
        try:
            if side.upper() == "BUY":
                # Buy slightly below current price
                return current_price * 0.9995  # 0.05% below
            else:
                # Sell slightly above current price  
                return current_price * 1.0005  # 0.05% above
        except Exception as e:
            logger.error(f"❌ Smart limit price calculation failed: {e}")
            return current_price