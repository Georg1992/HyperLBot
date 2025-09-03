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
    """Core trading decision engine - focused on trading logic only"""
    
    def __init__(self, config, strategy_config, prediction_engine, trade_quality_manager, position_lifecycle_manager, variability_analyzer):
        self.config = config
        self.strategy_config = strategy_config
        self.prediction_engine = prediction_engine
        self.trade_quality_manager = trade_quality_manager
        self.position_lifecycle_manager = position_lifecycle_manager
        self.variability_analyzer = variability_analyzer
        
        # Trading state
        self.strategy_name = strategy_config.get("name", "standard")
        self.last_trade_time = 0
        
        logger.info("🧠 Trading Engine initialized - Trade execution only")
    
    def should_trade(self, hyperliquid_price: float, yahoo_analysis: Dict[str, Any], hyperliquid_api) -> Dict[str, Any]:
        """Core trading decision logic"""
        if not yahoo_analysis or "error" in yahoo_analysis:
            return {"should_trade": False, "reason": "No market analysis available"}
        
        # 1. DETECT STRATEGY AND MARKET CONDITIONS
        current_strategy = self._auto_detect_strategy(yahoo_analysis, hyperliquid_price)
        if current_strategy != self.strategy_name:
            logger.info(f"🔄 Auto-switching strategy: {self.strategy_name} → {current_strategy}")
            self.strategy_name = current_strategy
            self.strategy_config = self.config.STRATEGY_CONFIGS.get(current_strategy, self.config.STRATEGY_CONFIGS["standard"])
        
        # 2. CHECK TIME INTERVAL
        current_time = time.time()
        min_interval = self.strategy_config["min_interval"]
        if current_time - self.last_trade_time < min_interval:
            return {"should_trade": False, "reason": f"Too soon since last trade (need {min_interval}s)"}
        
        # 3. GATHER MARKET INTELLIGENCE
        hyperliquid_data = market_data_manager.get_hyperliquid_data(hyperliquid_api, "BTC")
        
        volume_data = hyperliquid_data.get("volume_data", {})
        pressure_data = hyperliquid_data.get("pressure_data", {})
        # volatility_data removed - using 5m candle volatility instead of orderbook volatility
        
        # Update variability analyzer (use real orderbook depth, not fake volume estimate)
        orderbook_depth = volume_data.get("volume_depth", 100)
        self.variability_analyzer.add_price_data(hyperliquid_price, volume=orderbook_depth)
        
        # 4. BUILD COMPREHENSIVE ANALYSIS
        analysis = yahoo_analysis.copy()
        analysis["hyperliquid_volume"] = volume_data
        # hyperliquid_volatility removed - using 5m candle volatility from Yahoo analysis instead
        analysis["hyperliquid_pressure"] = pressure_data
        analysis["timestamp"] = current_time
        
        # MARKET CONDITIONS CHECK (determine if market is tradable)
        from strategies.market_conditions_analyzer import global_conditions_analyzer
        
        conditions_analysis = global_conditions_analyzer.analyze_trading_conditions(
            market_data={
                "current_price": hyperliquid_price,
                "rsi": analysis.get("yahoo_analysis", {}).get("rsi_5m", 50.0),
                "trend": analysis.get("yahoo_analysis", {}).get("trend_5m", {}).get("trend", "NEUTRAL"),
                "volatility_5m": analysis.get("yahoo_analysis", {}).get("volatility_5m", 0.0),
                "volatility_category": analysis.get("yahoo_analysis", {}).get("volatility_5m_category", "MODERATE"),
                "volume_category": analysis.get("hyperliquid_volume", {}).get("volume_category", "NORMAL"),
                "timestamp": current_time
            },
            historical_context={}  # Will add session manager context later
        )
        
        # BLOCK TRADING if conditions are untradable
        if not conditions_analysis["is_tradable"]:
            untradable_reason = global_conditions_analyzer.get_untradable_condition_summary(conditions_analysis)
            return {"should_trade": False, "reason": f"⚠️ {untradable_reason}"}
        
        # TRADING LOGIC STILL DISABLED for now (but conditions check is active)
        return {"should_trade": False, "reason": f"Trading disabled - Conditions: {conditions_analysis['condition']} ({conditions_analysis['confidence']:.0%})"}
    
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
    
    def _auto_detect_strategy(self, yahoo_analysis: Dict[str, Any], current_price: float) -> str:
        """Auto-detect optimal strategy based on market conditions + historical context"""
        try:
            volatility_5m = yahoo_analysis.get("volatility_5m", 0.0)
            trend_5m = yahoo_analysis.get("trend_5m", {}).get("trend", "NEUTRAL")
            
            # Simple strategy detection (enhanced decisions moved to Predictor/Reactor)
            if volatility_5m > 0.25:  # High volatility
                return "high_volatility"
            elif volatility_5m < 0.05:  # Low volatility
                return "low_volatility"
            elif trend_5m in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
                return "trend_following"
            else:
                return "standard"
                
        except Exception as e:
            logger.error(f"❌ Strategy auto-detection failed: {e}")
            return "standard"
    
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