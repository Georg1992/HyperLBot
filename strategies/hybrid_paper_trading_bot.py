#!/usr/bin/env python3
"""
Hybrid Paper Trading Bot
Combines Binance candlestick data for analysis with Hyperliquid market data for execution
"""

import time
import json
import random
import statistics
from typing import Dict, Any, Optional, List
from loguru import logger
import sys
import os
# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, 'core'))
sys.path.insert(0, os.path.join(project_root, 'data'))
sys.path.insert(0, os.path.join(project_root, 'strategies'))

from hyperliquid_api import HyperliquidAPI
from external_data_fetcher import ExternalDataFetcher
from config import TradingConfig
from fee_manager import FeeManager
from variability_analyzer import VariabilityAnalyzer
from trading_logger import TradingLogger
from whale_integration import WhaleIntegration, integrate_whale_analytics_into_signal

class HybridPaperTradingBot:
    def __init__(self, initial_balance: float = 120.0, strategy_name: str = "standard"):
        self.config = TradingConfig()
        self.strategy_name = strategy_name
        self.strategy_config = self.config.STRATEGY_CONFIGS.get(strategy_name, self.config.STRATEGY_CONFIGS["standard"])
        self.hyperliquid_api = None
        self.binance_fetcher = ExternalDataFetcher()
        self.connected = False
        
        # Paper trading state
        self.paper_balance = initial_balance
        self.initial_balance = initial_balance
        self.open_positions = []
        self.closed_positions = []
        self.trade_history = []
        
        # Market data storage
        self.binance_analysis = {}
        self.weekly_trend_analysis = {}
        self.hyperliquid_price = 0
        self.last_trade_time = 0
        self.min_interval = 300  # 5 minutes in seconds
        
        # Analysis components
        self.fee_manager = FeeManager()
        self.variability_analyzer = VariabilityAnalyzer(lookback_periods=100)
        self.trading_logger = TradingLogger("hybrid_paper_trading_logs")
        
        # Whale analytics integration
        self.whale_integration = WhaleIntegration(enabled=self.config.WHALE_ANALYTICS_ENABLED)
        
        # Enhanced analysis frequency
        self.price_update_interval = 5  # Update price every 5 seconds
        self.market_analysis_interval = 10  # Market analysis every 10 seconds
        self.signal_check_interval = 30  # Check for signals every 30 seconds
        self.candle_update_interval = 300  # Update candles every 5 minutes
        self.hourly_analysis_interval = 3600  # Hourly analysis every hour
        
        self.last_price_update = 0
        self.last_market_analysis = 0
        self.last_signal_check = 0
        self.last_candle_update = 0
        self.last_hourly_analysis = 0
        
        # Leverage settings (respecting Hyperliquid 40x limit)
        self.leverage_settings = {
            "base_leverage": 30,
            "max_leverage": 40,  # Hyperliquid limit
            "min_leverage": 20,
            "cascade_leverage": 40,
            "momentum_leverage": 38
        }
        
        logger.info(f"📊 Hybrid Paper Trading Bot initialized with ${initial_balance:.2f} balance")
        if self.whale_integration.is_available():
            logger.info("🐋 Whale analytics integration enabled")
        else:
            logger.info("🐋 Whale analytics integration disabled")
    
    def connect(self) -> bool:
        """Connect to both Hyperliquid and Binance APIs"""
        try:
            logger.info("🔌 Connecting to Hyperliquid and Binance...")
            
            # Test Binance connection
            if not self.binance_fetcher.test_connection():
                logger.error("❌ Failed to connect to Binance")
                return False
            
            # Test Hyperliquid connection
            if not self.config.WALLET_ADDRESS or not self.config.WALLET_PRIVATE_KEY:
                logger.error("❌ Wallet credentials not found")
                return False
            
            self.hyperliquid_api = HyperliquidAPI(self.config.WALLET_ADDRESS, self.config.WALLET_PRIVATE_KEY)
            account_info = self.hyperliquid_api.get_account_info()
            logger.success(f"✅ Successfully connected to both APIs!")
            
            if 'data' in account_info and 'marginSummary' in account_info['data']:
                margin = account_info['data']['marginSummary']
                account_value = margin.get('accountValue', 0)
                logger.info(f"💰 Real Account Value: ${account_value:.2f} USD")
                logger.info(f"📊 Paper Trading Balance: ${self.paper_balance:.2f} USD")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            self.trading_logger.log_error({
                "type": "connection_error",
                "message": str(e),
                "details": {"account_info": account_info if 'account_info' in locals() else None}
            })
            return False
    
    def get_weekly_trend_analysis(self) -> Dict[str, Any]:
        """Get weekly trend analysis for overall market context"""
        try:
            logger.info("📅 Analyzing weekly trend for overall market context...")
            
            # Get 1-week candlestick data (7 days * 24 hours = 168 candles)
            weekly_candles = self.binance_fetcher.get_binance_klines("BTCUSDT", "1h", 168)
            
            if not weekly_candles or len(weekly_candles) < 24:
                logger.error("❌ Insufficient weekly data for trend analysis")
                return {"error": "Insufficient weekly data"}
            
            # Calculate weekly trend
            week_start_price = weekly_candles[0]["close"]
            week_end_price = weekly_candles[-1]["close"]
            weekly_change = (week_end_price - week_start_price) / week_start_price
            
            # Calculate weekly volatility
            weekly_returns = []
            for i in range(1, len(weekly_candles)):
                prev_close = weekly_candles[i-1]["close"]
                curr_close = weekly_candles[i]["close"]
                ret = (curr_close - prev_close) / prev_close
                weekly_returns.append(ret)
            
            weekly_volatility = statistics.stdev(weekly_returns) if len(weekly_returns) > 1 else 0
            
            # Find weekly high and low
            weekly_high = max([candle["high"] for candle in weekly_candles])
            weekly_low = min([candle["low"] for candle in weekly_candles])
            weekly_range = weekly_high - weekly_low
            
            # Determine weekly trend strength
            if weekly_change > 0.05:  # 5% weekly gain
                weekly_trend = "STRONG_BULL"
                trend_strength = "VERY_STRONG"
            elif weekly_change > 0.02:  # 2% weekly gain
                weekly_trend = "BULL"
                trend_strength = "STRONG"
            elif weekly_change > 0.005:  # 0.5% weekly gain
                weekly_trend = "WEAK_BULL"
                trend_strength = "WEAK"
            elif weekly_change < -0.05:  # 5% weekly loss
                weekly_trend = "STRONG_BEAR"
                trend_strength = "VERY_STRONG"
            elif weekly_change < -0.02:  # 2% weekly loss
                weekly_trend = "BEAR"
                trend_strength = "STRONG"
            elif weekly_change < -0.005:  # 0.5% weekly loss
                weekly_trend = "WEAK_BEAR"
                trend_strength = "WEAK"
            else:
                weekly_trend = "SIDEWAYS"
                trend_strength = "NEUTRAL"
            
            # Calculate momentum indicators
            recent_candles = weekly_candles[-24:]  # Last 24 hours
            recent_change = (recent_candles[-1]["close"] - recent_candles[0]["close"]) / recent_candles[0]["close"]
            
            # Determine if recent momentum aligns with weekly trend
            momentum_alignment = "ALIGNED"
            if (weekly_trend in ["BULL", "STRONG_BULL", "WEAK_BULL"] and recent_change < -0.01) or \
               (weekly_trend in ["BEAR", "STRONG_BEAR", "WEAK_BEAR"] and recent_change > 0.01):
                momentum_alignment = "DIVERGING"
            
            weekly_analysis = {
                "weekly_trend": weekly_trend,
                "trend_strength": trend_strength,
                "weekly_change_pct": weekly_change * 100,
                "weekly_volatility": weekly_volatility,
                "weekly_high": weekly_high,
                "weekly_low": weekly_low,
                "weekly_range": weekly_range,
                "week_start_price": week_start_price,
                "week_end_price": week_end_price,
                "recent_24h_change": recent_change * 100,
                "momentum_alignment": momentum_alignment,
                "candles_analyzed": len(weekly_candles),
                "analysis_timestamp": time.time()
            }
            
            logger.success(f"✅ Weekly trend analysis completed:")
            logger.info(f"   Weekly Trend: {weekly_trend} ({weekly_change*100:.2f}%)")
            logger.info(f"   Trend Strength: {trend_strength}")
            logger.info(f"   Weekly Range: ${weekly_low:,.2f} - ${weekly_high:,.2f}")
            logger.info(f"   Recent 24h: {recent_change*100:.2f}% ({momentum_alignment})")
            
            return weekly_analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get weekly trend analysis: {e}")
            return {"error": str(e)}
    
    def get_binance_analysis(self) -> Dict[str, Any]:
        """Get comprehensive market analysis from Binance"""
        try:
            analysis = self.binance_fetcher.get_market_analysis("BTCUSDT")
            
            if "error" not in analysis:
                logger.info(f"📊 Binance analysis: ${analysis['current_price']:,.2f} - {analysis['market_condition']}")
                return analysis
            else:
                logger.error(f"❌ Binance analysis failed: {analysis['error']}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Failed to get Binance analysis: {e}")
            return {}
    
    def get_hyperliquid_price(self) -> Optional[float]:
        """Get current price from Hyperliquid"""
        try:
            market_data = self.hyperliquid_api.get_market_data("BTC")
            
            if market_data and 'levels' in market_data and len(market_data['levels']) >= 2:
                bids = market_data['levels'][0]
                asks = market_data['levels'][1]
                
                if bids and asks:
                    best_bid = float(bids[0]['px'])
                    best_ask = float(asks[0]['px'])
                    mid_price = (best_bid + best_ask) / 2
                    
                    # Update variability analyzer with new price data
                    current_time = time.time()
                    if current_time - self.last_price_update >= self.price_update_interval:
                        self.variability_analyzer.add_price_data(mid_price, volume=1000)
                        self.last_price_update = current_time
                    
                    return mid_price
            
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid price: {e}")
            return None
    
    def should_trade(self, hyperliquid_price: float, binance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if we should place a trade based on hybrid analysis with weekly trend context"""
        if not binance_analysis or "error" in binance_analysis:
            return {"should_trade": False, "reason": "No Binance analysis available"}
        
        # Auto-detect market volatility and adjust strategy
        current_strategy = self._auto_detect_strategy(binance_analysis, hyperliquid_price)
        if current_strategy != self.strategy_name:
            logger.info(f"🔄 Auto-switching strategy: {self.strategy_name} → {current_strategy}")
            
            # Log strategy switch to JSON files
            self.trading_logger.log_analysis({
                "type": "strategy_switch",
                "timestamp": time.time(),
                "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "previous_strategy": self.strategy_name,
                "new_strategy": current_strategy,
                "reason": "auto_detection",
                "market_condition": binance_analysis.get("market_condition", "UNKNOWN"),
                "hyperliquid_price": hyperliquid_price,
                "volatility_5m": self._get_volatility_5m(binance_analysis),
                "volatility_1h": self._get_volatility_1h(binance_analysis),
                "range_percentage": self._get_range_percentage(binance_analysis, hyperliquid_price)
            })
            
            self.strategy_name = current_strategy
            self.strategy_config = self.config.STRATEGY_CONFIGS.get(current_strategy, self.config.STRATEGY_CONFIGS["standard"])
        
        # Check if enough time has passed since last trade
        current_time = time.time()
        min_interval = self.strategy_config["min_interval"]
        if current_time - self.last_trade_time < min_interval:
            return {"should_trade": False, "reason": f"Too soon since last trade (need {min_interval}s)"}
        
        # Get variability analysis
        variability_decision = self.variability_analyzer.should_trade_based_on_variability(0.5)
        if not variability_decision["should_trade"]:
            return {
                "should_trade": False, 
                "reason": f"Variability analysis: {variability_decision['reason']}"
            }
        
        # Extract data from Binance analysis
        candles_5m = binance_analysis.get("candles_5m", [])
        candles_1h = binance_analysis.get("candles_1h", [])
        trend_5m = binance_analysis.get("trend_5m", {})
        trend_1h = binance_analysis.get("trend_1h", {})
        support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
        
        if len(candles_5m) < 10 or len(candles_1h) < 10:
            return {"should_trade": False, "reason": "Insufficient candlestick data"}
        
        # Strategy: Trade breakouts and reversions with 1-hour confirmation
        support_5m = support_resistance_5m.get("support", 0)
        resistance_5m = support_resistance_5m.get("resistance", 0)
        range_size_5m = support_resistance_5m.get("range", 0)
        
        # Minimum range requirement (avoid choppy markets)
        min_range_percentage = self.strategy_config["min_range_percentage"]
        if range_size_5m < hyperliquid_price * min_range_percentage:
            return {"should_trade": False, "reason": f"Range too small (need {min_range_percentage*100:.1f}%, have {range_size_5m/hyperliquid_price*100:.1f}%)"}
        
        # Get optimal trading parameters from variability analysis
        variability_analysis = variability_decision["analysis"]
        optimal_params = variability_analysis["optimal_trading_params"]
        
        # Adjust leverage to respect strategy and Hyperliquid limits
        max_leverage = min(self.strategy_config["max_leverage"], self.leverage_settings["max_leverage"])
        optimal_params["leverage"] = min(optimal_params["leverage"], max_leverage)
        
        # Apply weekly trend context to trading decisions
        weekly_context = self._apply_weekly_trend_context(hyperliquid_price, support_5m, resistance_5m)
        if not weekly_context["should_proceed"]:
            return {
                "should_trade": False,
                "reason": f"Weekly trend context: {weekly_context['reason']}"
            }
        
        # Breakout strategy with 1-hour confirmation and weekly trend context
        if hyperliquid_price > resistance_5m * 1.0005:  # Break above resistance
            # Check if 1-hour trend supports the breakout
            if trend_1h.get("trend") == "UP" or trend_1h.get("strength", 0) < 0.3:
                # Check weekly trend context
                weekly_context = self._apply_weekly_trend_context(hyperliquid_price, support_5m, resistance_5m)
                
                # In strong bull market, avoid shorting breakouts
                if weekly_context.get("preferred_direction") == "BUY" and weekly_context.get("risk_level") == "HIGH":
                    return {"should_trade": False, "reason": "Strong bull market - avoiding short on breakout"}
                
                target_price = hyperliquid_price * (1 - self.strategy_config["profit_target"])
                
                # Check if trade is profitable after fees
                profitability = self.fee_manager.is_trade_profitable(
                    hyperliquid_price, target_price, optimal_params["position_size"], optimal_params["leverage"]
                )
                
                if not profitability["is_profitable"]:
                    return {"should_trade": False, "reason": f"Trade not profitable after fees (margin: {profitability['profit_margin']:.2f}%)"}
                
                signal_data = {
                    "should_trade": True,
                    "side": "SELL",  # Short the breakout
                    "reason": f"Breakout above resistance ${resistance_5m:,.2f} (1h trend: {trend_1h.get('trend', 'UNKNOWN')}, weekly: {weekly_context.get('reason', 'N/A')})",
                    "target": target_price,
                    "stop": hyperliquid_price * (1 + self.strategy_config["stop_loss"]),
                    "profitability": profitability,
                    "variability_analysis": variability_analysis,
                    "optimal_params": optimal_params,
                    "binance_analysis": binance_analysis,
                    "hyperliquid_price": hyperliquid_price,
                    "support_5m": support_5m,
                    "resistance_5m": resistance_5m,
                    "trend_5m": trend_5m.get("trend", "UNKNOWN"),
                    "trend_1h": trend_1h.get("trend", "UNKNOWN"),
                    "hourly_confidence": trend_1h.get("strength", 0),
                    "range_size": range_size_5m,
                    "weekly_context": weekly_context
                }
                
                # Add whale confirmation to signal
                signal_data = integrate_whale_analytics_into_signal(signal_data, self.whale_integration)
                
                # Log whale analysis
                self.whale_integration.log_whale_analysis(self.trading_logger)
                
                # Log the signal
                self.trading_logger.log_signal(signal_data)
                
                return signal_data
        
        elif hyperliquid_price < support_5m * 0.9995:  # Break below support
            # Check if 1-hour trend supports the breakout
            if trend_1h.get("trend") == "DOWN" or trend_1h.get("strength", 0) < 0.3:
                # Check weekly trend context
                weekly_context = self._apply_weekly_trend_context(hyperliquid_price, support_5m, resistance_5m)
                
                # In strong bear market, avoid longing breakdowns
                if weekly_context.get("preferred_direction") == "SELL" and weekly_context.get("risk_level") == "HIGH":
                    return {"should_trade": False, "reason": "Strong bear market - avoiding long on breakdown"}
                
                target_price = hyperliquid_price * (1 + self.strategy_config["profit_target"])
                
                # Check if trade is profitable after fees
                profitability = self.fee_manager.is_trade_profitable(
                    hyperliquid_price, target_price, optimal_params["position_size"], optimal_params["leverage"]
                )
                
                if not profitability["is_profitable"]:
                    return {"should_trade": False, "reason": f"Trade not profitable after fees (margin: {profitability['profit_margin']:.2f}%)"}
                
                signal_data = {
                    "should_trade": True,
                    "side": "BUY",  # Long the breakout
                    "reason": f"Breakout below support ${support_5m:,.2f} (1h trend: {trend_1h.get('trend', 'UNKNOWN')}, weekly: {weekly_context.get('reason', 'N/A')})",
                    "target": target_price,
                    "stop": hyperliquid_price * (1 - self.strategy_config["stop_loss"]),
                    "profitability": profitability,
                    "variability_analysis": variability_analysis,
                    "optimal_params": optimal_params,
                    "binance_analysis": binance_analysis,
                    "hyperliquid_price": hyperliquid_price,
                    "support_5m": support_5m,
                    "resistance_5m": resistance_5m,
                    "trend_5m": trend_5m.get("trend", "UNKNOWN"),
                    "trend_1h": trend_1h.get("trend", "UNKNOWN"),
                    "hourly_confidence": trend_1h.get("strength", 0),
                    "range_size": range_size_5m,
                    "weekly_context": weekly_context
                }
                
                # Add whale confirmation to signal
                signal_data = integrate_whale_analytics_into_signal(signal_data, self.whale_integration)
                
                # Log whale analysis
                self.whale_integration.log_whale_analysis(self.trading_logger)
                
                # Log the signal
                self.trading_logger.log_signal(signal_data)
                
                return signal_data
        
        # Mean reversion strategy with 1-hour confirmation and weekly trend context
        elif hyperliquid_price > resistance_5m * 0.999:  # Near resistance
            # Check if 1-hour trend supports reversion
            if trend_1h.get("trend") == "DOWN" or trend_1h.get("strength", 0) < 0.3:
                # Check weekly trend context
                weekly_context = self._apply_weekly_trend_context(hyperliquid_price, support_5m, resistance_5m)
                
                # In strong bull market, be cautious about shorting near resistance
                if weekly_context.get("preferred_direction") == "BUY" and weekly_context.get("risk_level") == "HIGH":
                    return {"should_trade": False, "reason": "Strong bull market - avoiding short near resistance"}
                
                target_price = hyperliquid_price * (1 - optimal_params["profit_target"] * 0.8)
                
                # Check if trade is profitable after fees
                profitability = self.fee_manager.is_trade_profitable(
                    hyperliquid_price, target_price, optimal_params["position_size"], optimal_params["leverage"]
                )
                
                if not profitability["is_profitable"]:
                    return {"should_trade": False, "reason": f"Trade not profitable after fees (margin: {profitability['profit_margin']:.2f}%)"}
                
                signal_data = {
                    "should_trade": True,
                    "side": "SELL",  # Short the reversal
                    "reason": f"Reversion from resistance ${resistance_5m:,.2f} (1h trend: {trend_1h.get('trend', 'UNKNOWN')}, weekly: {weekly_context.get('reason', 'N/A')})",
                    "target": target_price,
                    "stop": hyperliquid_price * (1 + optimal_params["stop_loss"] * 0.8),
                    "profitability": profitability,
                    "variability_analysis": variability_analysis,
                    "optimal_params": optimal_params,
                    "binance_analysis": binance_analysis,
                    "hyperliquid_price": hyperliquid_price,
                    "support_5m": support_5m,
                    "resistance_5m": resistance_5m,
                    "trend_5m": trend_5m.get("trend", "UNKNOWN"),
                    "trend_1h": trend_1h.get("trend", "UNKNOWN"),
                    "hourly_confidence": trend_1h.get("strength", 0),
                    "range_size": range_size_5m,
                    "weekly_context": weekly_context
                }
                
                # Add whale confirmation to signal
                signal_data = integrate_whale_analytics_into_signal(signal_data, self.whale_integration)
                
                # Log whale analysis
                self.whale_integration.log_whale_analysis(self.trading_logger)
                
                # Log the signal
                self.trading_logger.log_signal(signal_data)
                
                return signal_data
        
        elif hyperliquid_price < support_5m * 1.001:  # Near support
            # Check if 1-hour trend supports reversion
            if trend_1h.get("trend") == "UP" or trend_1h.get("strength", 0) < 0.3:
                # Check weekly trend context
                weekly_context = self._apply_weekly_trend_context(hyperliquid_price, support_5m, resistance_5m)
                
                # In strong bear market, be cautious about longing near support
                if weekly_context.get("preferred_direction") == "SELL" and weekly_context.get("risk_level") == "HIGH":
                    return {"should_trade": False, "reason": "Strong bear market - avoiding long near support"}
                
                target_price = hyperliquid_price * (1 + optimal_params["profit_target"] * 0.8)
                
                # Check if trade is profitable after fees
                profitability = self.fee_manager.is_trade_profitable(
                    hyperliquid_price, target_price, optimal_params["position_size"], optimal_params["leverage"]
                )
                
                if not profitability["is_profitable"]:
                    return {"should_trade": False, "reason": f"Trade not profitable after fees (margin: {profitability['profit_margin']:.2f}%)"}
                
                signal_data = {
                    "should_trade": True,
                    "side": "BUY",  # Long the reversal
                    "reason": f"Reversion from support ${support_5m:,.2f} (1h trend: {trend_1h.get('trend', 'UNKNOWN')}, weekly: {weekly_context.get('reason', 'N/A')})",
                    "target": target_price,
                    "stop": hyperliquid_price * (1 - optimal_params["stop_loss"] * 0.8),
                    "profitability": profitability,
                    "variability_analysis": variability_analysis,
                    "optimal_params": optimal_params,
                    "binance_analysis": binance_analysis,
                    "hyperliquid_price": hyperliquid_price,
                    "support_5m": support_5m,
                    "resistance_5m": resistance_5m,
                    "trend_5m": trend_5m.get("trend", "UNKNOWN"),
                    "trend_1h": trend_1h.get("trend", "UNKNOWN"),
                    "hourly_confidence": trend_1h.get("strength", 0),
                    "range_size": range_size_5m,
                    "weekly_context": weekly_context
                }
                
                # Add whale confirmation to signal
                signal_data = integrate_whale_analytics_into_signal(signal_data, self.whale_integration)
                
                # Log whale analysis
                self.whale_integration.log_whale_analysis(self.trading_logger)
                
                # Log the signal
                self.trading_logger.log_signal(signal_data)
                
                return signal_data
        
        # Log no signal
        weekly_context = self._apply_weekly_trend_context(hyperliquid_price, support_5m, resistance_5m)
        no_signal_data = {
            "should_trade": False,
            "reason": "No clear signal with 1h confirmation",
            "hyperliquid_price": hyperliquid_price,
            "support_5m": support_5m,
            "resistance_5m": resistance_5m,
            "trend_5m": trend_5m.get("trend", "UNKNOWN"),
            "trend_1h": trend_1h.get("trend", "UNKNOWN"),
            "hourly_confidence": trend_1h.get("strength", 0),
            "range_size": range_size_5m,
            "weekly_context": weekly_context
        }
        self.trading_logger.log_signal(no_signal_data)
        
        return no_signal_data
    
    def _apply_weekly_trend_context(self, current_price: float, support: float, resistance: float) -> Dict[str, Any]:
        """Apply weekly trend context to trading decisions"""
        if not self.weekly_trend_analysis or "error" in self.weekly_trend_analysis:
            return {"should_proceed": True, "reason": "No weekly analysis available"}
        
        weekly_trend = self.weekly_trend_analysis.get("weekly_trend", "UNKNOWN")
        trend_strength = self.weekly_trend_analysis.get("trend_strength", "NEUTRAL")
        weekly_high = self.weekly_trend_analysis.get("weekly_high", 0)
        weekly_low = self.weekly_trend_analysis.get("weekly_low", 0)
        momentum_alignment = self.weekly_trend_analysis.get("momentum_alignment", "UNKNOWN")
        
        # Strong weekly trends should influence trading direction
        if trend_strength in ["VERY_STRONG", "STRONG"]:
            if weekly_trend in ["STRONG_BULL", "BULL"]:
                # In strong bull market, prefer long trades and avoid shorting near weekly high
                if current_price > weekly_high * 0.995:  # Near weekly high
                    return {
                        "should_proceed": False,
                        "reason": "Strong bull market - avoiding shorts near weekly high"
                    }
                # Prefer long trades in bull market
                return {
                    "should_proceed": True,
                    "reason": "Strong bull market - favoring long positions",
                    "preferred_direction": "BUY"
                }
            
            elif weekly_trend in ["STRONG_BEAR", "BEAR"]:
                # In strong bear market, prefer short trades and avoid longing near weekly low
                if current_price < weekly_low * 1.005:  # Near weekly low
                    return {
                        "should_proceed": False,
                        "reason": "Strong bear market - avoiding longs near weekly low"
                    }
                # Prefer short trades in bear market
                return {
                    "should_proceed": True,
                    "reason": "Strong bear market - favoring short positions",
                    "preferred_direction": "SELL"
                }
        
        # Check for momentum divergence
        if momentum_alignment == "DIVERGING":
            if weekly_trend in ["BULL", "STRONG_BULL"] and current_price < support * 0.998:
                return {
                    "should_proceed": False,
                    "reason": "Bull market momentum diverging - avoiding shorts"
                }
            elif weekly_trend in ["BEAR", "STRONG_BEAR"] and current_price > resistance * 1.002:
                return {
                    "should_proceed": False,
                    "reason": "Bear market momentum diverging - avoiding longs"
                }
        
        # Weekly range considerations
        weekly_range = weekly_high - weekly_low
        current_position_in_range = (current_price - weekly_low) / weekly_range if weekly_range > 0 else 0.5
        
        # Avoid trades at extreme ends of weekly range unless strong signals
        if current_position_in_range > 0.95:  # Near weekly high
            return {
                "should_proceed": True,
                "reason": "Near weekly high - cautious trading",
                "risk_level": "HIGH"
            }
        elif current_position_in_range < 0.05:  # Near weekly low
            return {
                "should_proceed": True,
                "reason": "Near weekly low - cautious trading",
                "risk_level": "HIGH"
            }
        
        return {
            "should_proceed": True,
            "reason": "Weekly trend context allows trading",
            "risk_level": "NORMAL"
        }
    
    def _auto_detect_strategy(self, binance_analysis: Dict[str, Any], current_price: float) -> str:
        """Auto-detect market volatility and return appropriate strategy"""
        try:
            # Get market condition from Binance analysis
            market_condition = binance_analysis.get("market_condition", "UNKNOWN")
            
            # Get volatility indicators
            candles_5m = binance_analysis.get("candles_5m", [])
            candles_1h = binance_analysis.get("candles_1h", [])
            
            if len(candles_5m) < 10 or len(candles_1h) < 10:
                return self.strategy_name  # Keep current strategy if insufficient data
            
            # Calculate 5-minute volatility
            prices_5m = [candle["close"] for candle in candles_5m[-20:]]  # Last 20 candles
            returns_5m = []
            for i in range(1, len(prices_5m)):
                ret = abs((prices_5m[i] - prices_5m[i-1]) / prices_5m[i-1])
                returns_5m.append(ret)
            
            volatility_5m = statistics.mean(returns_5m) if returns_5m else 0
            
            # Calculate 1-hour volatility
            prices_1h = [candle["close"] for candle in candles_1h[-24:]]  # Last 24 candles
            returns_1h = []
            for i in range(1, len(prices_1h)):
                ret = abs((prices_1h[i] - prices_1h[i-1]) / prices_1h[i-1])
                returns_1h.append(ret)
            
            volatility_1h = statistics.mean(returns_1h) if returns_1h else 0
            
            # Get range size
            support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
            range_size = support_resistance_5m.get("range", 0)
            range_percentage = (range_size / current_price) if current_price > 0 else 0
            
            # Strategy selection logic
            if market_condition == "LOW_VOLATILITY" or volatility_5m < 0.001 or range_percentage < 0.003:
                # Low volatility conditions
                logger.info(f"📊 Low volatility detected: 5m={volatility_5m*100:.3f}%, 1h={volatility_1h*100:.3f}%, range={range_percentage*100:.2f}%")
                return "low_volatility"
            
            elif market_condition == "HIGH_VOLATILITY" or volatility_5m > 0.005 or volatility_1h > 0.01 or range_percentage > 0.01:
                # High volatility conditions
                logger.info(f"📊 High volatility detected: 5m={volatility_5m*100:.3f}%, 1h={volatility_1h*100:.3f}%, range={range_percentage*100:.2f}%")
                return "high_volatility"
            
            else:
                # Medium volatility conditions
                logger.info(f"📊 Medium volatility detected: 5m={volatility_5m*100:.3f}%, 1h={volatility_1h*100:.3f}%, range={range_percentage*100:.2f}%")
                return "standard"
                
        except Exception as e:
            logger.error(f"❌ Error in auto-strategy detection: {e}")
            return self.strategy_name  # Keep current strategy on error
    
    def _get_volatility_5m(self, binance_analysis: Dict[str, Any]) -> float:
        """Extract 5-minute volatility from analysis"""
        try:
            candles_5m = binance_analysis.get("candles_5m", [])
            if len(candles_5m) < 10:
                return 0.0
            
            prices_5m = [candle["close"] for candle in candles_5m[-20:]]
            returns_5m = []
            for i in range(1, len(prices_5m)):
                ret = abs((prices_5m[i] - prices_5m[i-1]) / prices_5m[i-1])
                returns_5m.append(ret)
            
            return statistics.mean(returns_5m) if returns_5m else 0.0
        except:
            return 0.0
    
    def _get_volatility_1h(self, binance_analysis: Dict[str, Any]) -> float:
        """Extract 1-hour volatility from analysis"""
        try:
            candles_1h = binance_analysis.get("candles_1h", [])
            if len(candles_1h) < 10:
                return 0.0
            
            prices_1h = [candle["close"] for candle in candles_1h[-24:]]
            returns_1h = []
            for i in range(1, len(prices_1h)):
                ret = abs((prices_1h[i] - prices_1h[i-1]) / prices_1h[i-1])
                returns_1h.append(ret)
            
            return statistics.mean(returns_1h) if returns_1h else 0.0
        except:
            return 0.0
    
    def _get_range_percentage(self, binance_analysis: Dict[str, Any], current_price: float) -> float:
        """Extract range percentage from analysis"""
        try:
            support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
            range_size = support_resistance_5m.get("range", 0)
            return (range_size / current_price) if current_price > 0 else 0.0
        except:
            return 0.0
    
    def simulate_trade_execution(self, side: str, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Simulate trade execution with realistic Hyperliquid slippage and fees"""
        # Get Hyperliquid order book for realistic slippage
        try:
            market_data = self.hyperliquid_api.get_market_data("BTC")
            if market_data and 'levels' in market_data and len(market_data['levels']) >= 2:
                bids = market_data['levels'][0]
                asks = market_data['levels'][1]
                
                if bids and asks:
                    best_bid = float(bids[0]['px'])
                    best_ask = float(asks[0]['px'])
                    spread = best_ask - best_bid
                    
                    # Calculate realistic slippage based on order book depth
                    if side == "BUY":
                        execution_price = best_ask + (spread * 0.1)  # Slight slippage for buy
                    else:
                        execution_price = best_bid - (spread * 0.1)  # Slight slippage for sell
                else:
                    # Fallback slippage
                    slippage = random.uniform(0.0001, 0.0005)
                    if side == "BUY":
                        execution_price = price * (1 + slippage)
                    else:
                        execution_price = price * (1 - slippage)
            else:
                # Fallback slippage
                slippage = random.uniform(0.0001, 0.0005)
                if side == "BUY":
                    execution_price = price * (1 + slippage)
                else:
                    execution_price = price * (1 - slippage)
        except:
            # Fallback slippage
            slippage = random.uniform(0.0001, 0.0005)
            if side == "BUY":
                execution_price = price * (1 + slippage)
            else:
                execution_price = price * (1 - slippage)
        
        # Calculate fees using Hyperliquid fee structure
        fees = self.fee_manager.calculate_order_fees(size, execution_price, "LIMIT")
        
        # Calculate position value
        position_value = size * execution_price * leverage
        
        # Check if we have enough balance
        if position_value > self.paper_balance:
            return {
                "success": False,
                "error": "Insufficient balance for position"
            }
        
        # Deduct fees from balance
        self.paper_balance -= fees["total_cost"]
        
        return {
            "success": True,
            "execution_price": execution_price,
            "slippage": abs(execution_price - price) / price,
            "fees": fees,
            "position_value": position_value,
            "remaining_balance": self.paper_balance
        }
    
    def place_paper_trade(self, side: str, size: float = 0.001, leverage: int = 30, signal_data: Dict = None) -> bool:
        """Place a paper trade using Hyperliquid execution prices"""
        try:
            hyperliquid_price = self.get_hyperliquid_price()
            if not hyperliquid_price:
                return False
            
            # Use optimal parameters from variability analysis if available
            if signal_data and "optimal_params" in signal_data:
                optimal_params = signal_data["optimal_params"]
                size = optimal_params["position_size"]
                leverage = optimal_params["leverage"]
            
            # Ensure leverage doesn't exceed Hyperliquid limit
            leverage = min(leverage, self.leverage_settings["max_leverage"])
            
            logger.info(f"📝 Placing HYBRID PAPER {side} trade:")
            logger.info(f"   Hyperliquid Price: ${hyperliquid_price:,.2f}")
            logger.info(f"   Size: {size}")
            logger.info(f"   Leverage: {leverage}x")
            logger.info(f"   Paper Balance: ${self.paper_balance:.2f}")
            
            # Simulate trade execution with Hyperliquid data
            execution_result = self.simulate_trade_execution(side, size, hyperliquid_price, leverage)
            
            if not execution_result["success"]:
                logger.error(f"❌ Paper trade failed: {execution_result['error']}")
                return False
            
            # Create position record
            position = {
                "trade_id": f"hybrid_trade_{len(self.trade_history) + 1}",
                "side": side,
                "entry_price": execution_result["execution_price"],
                "size": size,
                "leverage": leverage,
                "entry_time": time.time(),
                "entry_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "fees": execution_result["fees"],
                "signal_data": signal_data,
                "target_price": signal_data.get("target") if signal_data else None,
                "stop_price": signal_data.get("stop") if signal_data else None,
                "status": "OPEN"
            }
            
            # Add to open positions
            self.open_positions.append(position)
            
            # Prepare trade data for logging
            trade_data = {
                "trade_id": position["trade_id"],
                "side": side,
                "price": execution_result["execution_price"],
                "size": size,
                "leverage": leverage,
                "order_type": "LIMIT",
                "fees": execution_result["fees"],
                "signal_data": signal_data,
                "order_result": {"status": "ok", "paper_trade": True, "hybrid": True},
                "hyperliquid_price": hyperliquid_price,
                "support": signal_data.get("support_5m") if signal_data else None,
                "resistance": signal_data.get("resistance_5m") if signal_data else None,
                "trend_5m": signal_data.get("trend_5m") if signal_data else None,
                "trend_1h": signal_data.get("trend_1h") if signal_data else None,
                "variability_score": signal_data.get("variability_analysis", {}).get("current_variability_score") if signal_data else None,
                "market_condition": signal_data.get("binance_analysis", {}).get("market_condition") if signal_data else None,
                "signal_reason": signal_data.get("reason") if signal_data else None,
                "profit_target": signal_data.get("target") if signal_data else None,
                "stop_loss": signal_data.get("stop") if signal_data else None,
                "risk_level": signal_data.get("variability_analysis", {}).get("risk_level") if signal_data else "STANDARD"
            }
            
            # Log the trade
            self.trading_logger.log_trade(trade_data)
            
            self.trade_history.append(trade_data)
            self.fee_manager.record_trade_fees(trade_data)
            self.last_trade_time = time.time()
            
            logger.success(f"✅ HYBRID PAPER {side} trade placed successfully!")
            logger.info(f"   Execution Price: ${execution_result['execution_price']:,.2f}")
            logger.info(f"   Slippage: {execution_result['slippage']*100:.3f}%")
            logger.info(f"   Fees: ${execution_result['fees']['total_cost']:.4f}")
            logger.info(f"   Remaining Balance: ${execution_result['remaining_balance']:.2f}")
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Failed to place hybrid paper trade: {e}")
            self.trading_logger.log_error({
                "type": "hybrid_paper_trade_error",
                "message": str(e),
                "details": {
                    "side": side,
                    "size": size,
                    "leverage": leverage,
                    "signal_data": signal_data
                }
            })
            return False
    
    def check_position_exits(self, hyperliquid_price: float):
        """Check if any open positions should be closed"""
        positions_to_close = []
        
        for position in self.open_positions:
            entry_price = position["entry_price"]
            side = position["side"]
            target_price = position["target_price"]
            stop_price = position["stop_price"]
            
            # Check for target hit
            if target_price:
                if (side == "BUY" and hyperliquid_price >= target_price) or (side == "SELL" and hyperliquid_price <= target_price):
                    positions_to_close.append((position, "TARGET_HIT", target_price))
                    continue
            
            # Check for stop loss
            if stop_price:
                if (side == "BUY" and hyperliquid_price <= stop_price) or (side == "SELL" and hyperliquid_price >= stop_price):
                    positions_to_close.append((position, "STOP_LOSS", stop_price))
                    continue
            
            # Check for time-based exit (1 hour max)
            if time.time() - position["entry_time"] > 3600:  # 1 hour
                positions_to_close.append((position, "TIME_EXIT", hyperliquid_price))
                continue
        
        # Close positions
        for position, exit_reason, exit_price in positions_to_close:
            self.close_paper_position(position, exit_reason, exit_price)
    
    def close_paper_position(self, position: Dict, exit_reason: str, exit_price: float):
        """Close a paper trading position"""
        entry_price = position["entry_price"]
        side = position["side"]
        size = position["size"]
        leverage = position["leverage"]
        
        # Calculate P&L
        if side == "BUY":
            price_change = (exit_price - entry_price) / entry_price
        else:
            price_change = (entry_price - exit_price) / entry_price
        
        # Apply leverage
        pnl_pct = price_change * leverage
        pnl_amount = size * entry_price * leverage * pnl_pct
        
        # Calculate fees
        exit_fees = self.fee_manager.calculate_order_fees(size, exit_price, "LIMIT")
        total_fees = position["fees"]["total_cost"] + exit_fees["total_cost"]
        
        # Net P&L
        net_pnl = pnl_amount - total_fees
        
        # Update balance
        self.paper_balance += net_pnl
        
        # Update position
        position.update({
            "exit_price": exit_price,
            "exit_time": time.time(),
            "exit_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_reason": exit_reason,
            "pnl_pct": pnl_pct,
            "pnl_amount": pnl_amount,
            "total_fees": total_fees,
            "net_pnl": net_pnl,
            "status": "CLOSED",
            "was_profitable": net_pnl > 0
        })
        
        # Move to closed positions
        self.open_positions.remove(position)
        self.closed_positions.append(position)
        
        # Update trade result in logger
        self.trading_logger.update_trade_result(position["trade_id"], {
            "exit_price": exit_price,
            "profit_loss": pnl_amount,
            "profit_loss_pct": pnl_pct,
            "fees_paid": total_fees,
            "net_profit_loss": net_pnl,
            "holding_time": position["exit_time"] - position["entry_time"],
            "exit_reason": exit_reason,
            "was_profitable": net_pnl > 0
        })
        
        logger.info(f"📊 Position closed: {position['trade_id']}")
        logger.info(f"   {side} {size} @ ${entry_price:,.2f} → ${exit_price:,.2f}")
        logger.info(f"   P&L: {pnl_pct*100:.2f}% (${pnl_amount:.4f})")
        logger.info(f"   Net P&L: ${net_pnl:.4f} (fees: ${total_fees:.4f})")
        logger.info(f"   Reason: {exit_reason}")
        logger.info(f"   Paper Balance: ${self.paper_balance:.2f}")
    
    def run_hybrid_paper_trading(self, max_trades: int = 10, check_interval: int = 30):
        """Run the hybrid paper trading bot"""
        if not self.connected:
            logger.error("❌ Not connected to APIs")
            return
        
        # Get weekly trend analysis before starting
        logger.info("📅 Getting weekly trend analysis for session context...")
        weekly_analysis = self.get_weekly_trend_analysis()
        
        if "error" not in weekly_analysis:
            self.weekly_trend_analysis = weekly_analysis
            logger.success("✅ Weekly trend analysis loaded successfully!")
        else:
            logger.warning("⚠️ Could not get weekly trend analysis, proceeding without it")
            self.weekly_trend_analysis = {}
        
        logger.info(f"🤖 Starting Hybrid Paper Trading Bot")
        logger.info(f"   Initial Balance: ${self.initial_balance:.2f}")
        logger.info(f"   Max Trades: {max_trades}")
        logger.info(f"   Check Interval: {check_interval} seconds")
        logger.info(f"   Max Leverage: {self.leverage_settings['max_leverage']}x")
        logger.info(f"   Analysis: Binance candlesticks + Hyperliquid execution")
        logger.info(f"   Analysis Frequency: Price every {self.price_update_interval}s, Signals every {self.signal_check_interval}s")
        logger.info(f"   Strategy: Auto-Detection (Standard/Low/High Volatility)")
        logger.info(f"   Weekly Context: {self.weekly_trend_analysis.get('weekly_trend', 'UNKNOWN')} ({self.weekly_trend_analysis.get('weekly_change_pct', 0):.2f}%)")
        logger.info(f"   Whale Analytics: {'Enabled' if self.whale_integration.is_available() else 'Disabled'}")
        logger.info(f"   Logging: Comprehensive hybrid paper trading logs enabled")
        logger.info("=" * 50)
        
        trades_placed = 0
        
        while trades_placed < max_trades:
            try:
                current_time = time.time()
                
                # Update Hyperliquid price data frequently
                hyperliquid_price = self.get_hyperliquid_price()
                if not hyperliquid_price:
                    logger.warning("⚠️ Could not get Hyperliquid price, retrying...")
                    time.sleep(check_interval)
                    continue
                
                # Check for position exits
                self.check_position_exits(hyperliquid_price)
                
                # Update Binance analysis periodically
                if current_time - self.last_candle_update >= self.candle_update_interval:
                    binance_analysis = self.get_binance_analysis()
                    if binance_analysis:
                        self.binance_analysis = binance_analysis
                        self.last_candle_update = current_time
                        
                        # Log analysis
                        self.trading_logger.log_analysis({
                            "type": "hybrid_analysis_update",
                            "timeframe": "5m",
                            "support_resistance": binance_analysis.get("support_resistance_5m", {}),
                            "trend_analysis": binance_analysis.get("trend_5m", {}),
                            "market_condition": binance_analysis.get("market_condition", "UNKNOWN"),
                            "hyperliquid_price": hyperliquid_price,
                            "binance_price": binance_analysis.get("current_price", 0)
                        })
                
                # Check for signals periodically
                if current_time - self.last_signal_check >= self.signal_check_interval:
                    if not self.binance_analysis:
                        logger.warning("⚠️ Could not get Binance analysis, retrying...")
                        time.sleep(check_interval)
                        continue
                    
                    # Analyze market using hybrid data
                    signal = self.should_trade(hyperliquid_price, self.binance_analysis)
                    
                    if signal["should_trade"]:
                        logger.info(f"📊 Hybrid signal detected: {signal['reason']}")
                        logger.info(f"   Hyperliquid Price: ${hyperliquid_price:,.2f}")
                        logger.info(f"   Binance Price: ${self.binance_analysis.get('current_price', 0):,.2f}")
                        logger.info(f"   Action: {signal['side']}")
                        
                        # Place the hybrid paper trade
                        if self.place_paper_trade(signal['side'], signal_data=signal):
                            trades_placed += 1
                            logger.info(f"   Hybrid Paper Trade {trades_placed}/{max_trades} completed")
                        else:
                            logger.error("   Hybrid paper trade placement failed")
                    
                    else:
                        logger.info(f"⏳ No hybrid signal: {signal['reason']}")
                    
                    self.last_signal_check = current_time
                
                # Wait before next check
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in hybrid paper trading loop: {e}")
                self.trading_logger.log_error({
                    "type": "hybrid_paper_trading_loop_error",
                    "message": str(e),
                    "details": {"trades_placed": trades_placed, "max_trades": max_trades}
                })
                time.sleep(check_interval)
        
        # Close any remaining open positions
        hyperliquid_price = self.get_hyperliquid_price()
        if hyperliquid_price:
            for position in self.open_positions[:]:  # Copy list to avoid modification during iteration
                self.close_paper_position(position, "SESSION_END", hyperliquid_price)
        
        logger.info("=" * 50)
        logger.success(f"🎯 Hybrid Paper Trading session completed!")
        logger.info(f"   Total trades placed: {trades_placed}")
        logger.info(f"   Final Balance: ${self.paper_balance:.2f}")
        logger.info(f"   Total P&L: ${self.paper_balance - self.initial_balance:.2f}")
        logger.info(f"   Return: {((self.paper_balance - self.initial_balance) / self.initial_balance * 100):.2f}%")
        
        # Generate comprehensive trading report
        trading_report = self.trading_logger.generate_trading_report()
        logger.info(f"📊 Hybrid Paper Trading Report Generated:")
        logger.info(f"   Session ID: {trading_report['session_info']['session_id']}")
        logger.info(f"   Total Trades: {trading_report['trade_analysis']['total_trades']}")
        logger.info(f"   Win Rate: {trading_report['trade_analysis']['win_rate']}")
        logger.info(f"   Net Profit: {trading_report['trade_analysis']['net_profit']}")
        logger.info(f"   Total Fees: {trading_report['trade_analysis']['total_fees']}")
        
        # Show strategy insights
        insights = self.trading_logger.get_strategy_insights()
        if insights["recommendations"]:
            logger.info(f"💡 Strategy Recommendations:")
            for rec in insights["recommendations"]:
                logger.info(f"   • {rec}")
        
        # Export data to CSV for external analysis
        self.trading_logger.export_to_csv()

def main():
    """Main function to run the hybrid paper trading bot"""
    logger.info("🚀 Hybrid Paper Trading Bot Starting...")
    
    # Initialize hybrid paper trading bot with $120 starting balance
    bot = HybridPaperTradingBot(initial_balance=120.0)
    
    # Connect to both Hyperliquid and Binance
    if not bot.connect():
        logger.error("❌ Failed to connect to APIs")
        return
    
    # Run hybrid paper trading
    # Parameters: max_trades, check_interval_seconds
    bot.run_hybrid_paper_trading(
        max_trades=5,      # Place 5 trades maximum
        check_interval=30  # Check every 30 seconds
    )

if __name__ == "__main__":
    main()
