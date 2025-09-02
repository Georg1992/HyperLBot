#!/usr/bin/env python3
"""
Clean Prediction Engine
======================
SIMPLIFIED: Only generates initial session prediction (limit order + stop/take profit)

PURPOSE: Create ONE prediction at session start for dashboard display
FOCUS: Clean limit order structure with historical context
REMOVED: All complex ongoing prediction logic (user request: clean redundant logic)
"""

import time
from typing import Dict, Any, Tuple
from datetime import datetime
from loguru import logger
from config.config import TradingConfig
from core.constants import technical_constants


class PredictionEngine:
    """CLEAN prediction engine - only initial session predictions"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        self.config = TradingConfig()
        self.session_manager = None  # Will be set by SessionOrchestrator for historical context
        
        logger.info("🎯 Clean Prediction Engine initialized - Initial session predictions only")
    
    def set_session_manager(self, session_manager):
        """Set session manager reference for accessing historical context (for enhanced predictions)"""
        self.session_manager = session_manager
    
    def get_historical_context(self) -> Dict[str, Any]:
        """Get session historical context for enhanced prediction decisions"""
        if self.session_manager and self.session_manager.has_historical_context():
            return self.session_manager.get_historical_context()
        return {}
    
    def generate_initial_session_prediction(self, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate initial prediction for session start (limit order with stop/take profit)
        
        PURPOSE: Create ONE prediction at session beginning for dashboard display
        OUTPUT: Limit order structure with entry, stop loss, take profit (all limit orders)
        """
        try:
            logger.info("🎯 Generating initial session prediction...")
            
            # Get historical context for enhanced prediction
            historical_context = self.get_historical_context()
            
            # Get current market conditions
            rsi_value = market_data.get("rsi", 50.0)
            trend = market_data.get("trend", "NEUTRAL")
            volatility_5m = market_data.get("volatility_5m", 0.0)
            volatility_category = market_data.get("volatility_category", "MODERATE")
            
            # Determine trade direction using historical context + current conditions
            direction, reasoning = self._determine_initial_direction(
                current_price, rsi_value, trend, volatility_category, historical_context
            )
            
            # Calculate limit order prices (entry + stop + take profit)
            order_prices = self._calculate_limit_order_structure(
                current_price, direction, volatility_5m, historical_context
            )
            
            # Build comprehensive initial prediction
            initial_prediction = {
                "prediction_type": "INITIAL_SESSION_PREDICTION",
                "timestamp": time.time(),
                "datetime": datetime.now().isoformat(),
                "market_analysis": {
                    "current_price": current_price,
                    "rsi": rsi_value,
                    "trend": trend,
                    "volatility_category": volatility_category,
                    "volatility_5m": volatility_5m
                },
                "order_structure": {
                    "direction": direction,
                    "entry_price": order_prices["entry"],
                    "stop_loss": order_prices["stop_loss"],
                    "take_profit": order_prices["take_profit"],
                    "order_type": "LIMIT_ORDER",
                    "stop_type": "LIMIT_ORDER",
                    "take_type": "LIMIT_ORDER"  # Limit order to avoid fees
                },
                "reasoning": reasoning,
                "historical_context_used": historical_context.get("market_regime", {}).get("regime", "UNKNOWN"),
                "confidence": self._calculate_initial_confidence(rsi_value, trend, historical_context),
                "session_strategy": historical_context.get("strategy_recommendations", {}).get("primary", "standard")
            }
            
            logger.success(f"✅ Initial prediction: {direction} @ ${order_prices['entry']:.2f} (Stop: ${order_prices['stop_loss']:.2f}, Take: ${order_prices['take_profit']:.2f})")
            return initial_prediction
            
        except Exception as e:
            logger.error(f"❌ Initial session prediction failed: {e}")
            return self._get_default_initial_prediction(current_price)
    
    def _determine_initial_direction(self, current_price: float, rsi: float, trend: str, 
                                   volatility_category: str, historical_context: Dict) -> Tuple[str, str]:
        """Determine initial trade direction using historical context + current conditions"""
        try:
            # Get historical insights
            market_regime = historical_context.get("market_regime", {}).get("regime", "UNKNOWN")
            major_levels = historical_context.get("major_levels", {})
            support_levels = major_levels.get("support", [])
            resistance_levels = major_levels.get("resistance", [])
            
            # Enhanced direction logic with historical context
            if market_regime in ["RANGING", "TIGHT_RANGING"]:
                # Range trading logic: Buy near support, sell near resistance
                if support_levels and any(abs(current_price - level) / level < 0.02 for level in support_levels):
                    return "BUY", f"Near historical support in {market_regime} regime (RSI: {rsi:.1f})"
                elif resistance_levels and any(abs(current_price - level) / level < 0.02 for level in resistance_levels):
                    return "SELL", f"Near historical resistance in {market_regime} regime (RSI: {rsi:.1f})"
            
            # RSI-based decision with trend confirmation
            if rsi <= 35 and trend in ["UPTREND", "WEAK_UPTREND", "SIDEWAYS"]:
                return "BUY", f"RSI oversold ({rsi:.1f}) with {trend} context"
            elif rsi >= 65 and trend in ["DOWNTREND", "WEAK_DOWNTREND", "SIDEWAYS"]:
                return "SELL", f"RSI overbought ({rsi:.1f}) with {trend} context"
            
            # Default: Slight bias based on RSI
            if rsi < 50:
                return "BUY", f"Slight RSI bias ({rsi:.1f}) - bullish lean"
            else:
                return "SELL", f"Slight RSI bias ({rsi:.1f}) - bearish lean"
                
        except Exception as e:
            logger.error(f"❌ Initial direction determination failed: {e}")
            return "BUY", "Default buy direction due to error"
    
    def _calculate_limit_order_structure(self, current_price: float, direction: str, 
                                       volatility_5m: float, historical_context: Dict) -> Dict[str, float]:
        """Calculate limit order prices (entry, stop loss, take profit)"""
        try:
            # Dynamic risk management based on volatility
            if volatility_5m < 0.001:  # Very low volatility
                stop_distance_pct = 0.003  # 0.3%
                take_distance_pct = 0.006  # 0.6% (2:1 R/R)
                entry_buffer_pct = 0.0005  # 0.05% buffer from current price
            elif volatility_5m < 0.005:  # Low volatility
                stop_distance_pct = 0.005  # 0.5%
                take_distance_pct = 0.010  # 1.0% (2:1 R/R)
                entry_buffer_pct = 0.001   # 0.1% buffer
            else:  # Moderate+ volatility
                stop_distance_pct = 0.008  # 0.8%
                take_distance_pct = 0.016  # 1.6% (2:1 R/R)
                entry_buffer_pct = 0.002   # 0.2% buffer
            
            if direction == "BUY":
                entry_price = current_price * (1 - entry_buffer_pct)  # Buy slightly below current
                stop_loss = entry_price * (1 - stop_distance_pct)
                take_profit = entry_price * (1 + take_distance_pct)
            else:  # SELL
                entry_price = current_price * (1 + entry_buffer_pct)  # Sell slightly above current
                stop_loss = entry_price * (1 + stop_distance_pct)
                take_profit = entry_price * (1 - take_distance_pct)
            
            return {
                "entry": round(entry_price, 2),
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Limit order calculation failed: {e}")
            # Safe fallback
            return {
                "entry": current_price,
                "stop_loss": current_price * (0.995 if direction == "BUY" else 1.005),
                "take_profit": current_price * (1.01 if direction == "BUY" else 0.99)
            }
    
    def _calculate_initial_confidence(self, rsi: float, trend: str, historical_context: Dict) -> float:
        """Calculate confidence for initial prediction"""
        try:
            base_confidence = 0.5  # Start with 50%
            
            # RSI confidence (extreme values = higher confidence)
            if rsi <= 30 or rsi >= 70:
                base_confidence += 0.2
            elif rsi <= 40 or rsi >= 60:
                base_confidence += 0.1
            
            # Trend confidence
            if trend in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
                base_confidence += 0.15
            elif trend in ["UPTREND", "DOWNTREND"]:
                base_confidence += 0.1
            
            # Historical context confidence
            market_regime = historical_context.get("market_regime", {})
            if market_regime.get("confidence", 0) > 0.7:
                base_confidence += 0.1
            
            return min(0.95, max(0.2, base_confidence))  # Cap between 20% and 95%
            
        except Exception as e:
            logger.error(f"❌ Initial confidence calculation failed: {e}")
            return 0.5
    
    def _get_default_initial_prediction(self, current_price: float) -> Dict[str, Any]:
        """Default initial prediction when analysis fails"""
        return {
            "prediction_type": "INITIAL_SESSION_PREDICTION",
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "market_analysis": {"current_price": current_price},
            "order_structure": {
                "direction": "BUY",
                "entry_price": current_price * 0.999,
                "stop_loss": current_price * 0.995,
                "take_profit": current_price * 1.01,
                "order_type": "LIMIT_ORDER",
                "stop_type": "LIMIT_ORDER", 
                "take_type": "LIMIT_ORDER"
            },
            "reasoning": "Default prediction due to analysis error",
            "confidence": 0.3,
            "session_strategy": "standard"
        }

# CLEANED: All redundant prediction logic removed
# Removed methods:
# - generate_structured_prediction() (complex ongoing predictions)
# - build_price_prediction() (compatibility wrapper)
# - _determine_trade_direction() (complex direction logic)
# - _calculate_position_size() (position sizing)
# - _calculate_confidence() (complex confidence calculation)
# - _detect_market_regime() (regime detection)
# - _calculate_win_probability() (probability calculation)
# - _get_default_prediction() (default prediction)
# 
# FOCUS: Only initial session prediction with limit order structure