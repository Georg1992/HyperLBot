#!/usr/bin/env python3
"""
Dynamic Prediction Engine
========================
ENHANCED: Generates initial predictions AND updates them based on market changes

PURPOSE: Create dynamic predictions that adapt to market conditions
FOCUS: Clean limit order structure with historical context + real-time updates
FEATURES: 
- Initial session prediction
- Dynamic prediction updates based on market condition changes
- Signal detection for prediction updates
- Strategy-aware prediction generation
"""

import time
from typing import Dict, Any, Tuple, List
from datetime import datetime
from loguru import logger
from config.config import TradingConfig
from core.constants import technical_constants


class PredictionEngine:
    """Dynamic prediction engine - initial predictions + real-time updates"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        self.config = TradingConfig()
        self.session_manager = None  # Will be set by SessionOrchestrator for historical context
        
        # Track last prediction for comparison
        self.last_prediction = None
        self.last_market_conditions = None
        self.last_update_time = 0
        
        logger.info("🎯 Dynamic Prediction Engine initialized - Initial + real-time updates")
    
    def set_session_manager(self, session_manager):
        """Set session manager reference for accessing historical context (for enhanced predictions)"""
        self.session_manager = session_manager
    
    def get_historical_context(self) -> Dict[str, Any]:
        """Get session historical context for enhanced prediction decisions"""
        if self.session_manager and self.session_manager.has_historical_context():
            return self.session_manager.get_historical_context()
        return {}
    
    def should_update_prediction(self, current_price: float, market_data: Dict[str, Any], strategy_name: str = "standard") -> bool:
        """
        Determine if prediction should be updated based on market changes
        
        Returns True if:
        1. Market conditions have changed significantly
        2. Price has moved significantly from last prediction
        3. RSI has crossed key thresholds
        4. Support/resistance levels have been broken
        5. Strategy has changed
        """
        try:
            current_time = time.time()
            
            # Don't update too frequently (minimum 5 seconds between updates for testing)
            if current_time - self.last_update_time < 5:
                logger.debug(f"⏰ Update throttled: {current_time - self.last_update_time:.1f}s since last update")
                return False
            
            # If no previous prediction, always generate initial one
            if not self.last_prediction:
                return True
            
            # Check for significant price movement
            last_order_structure = self.last_prediction.get("order_structure", {})
            last_price = last_order_structure.get("entry_price", current_price)
            price_change_pct = abs(current_price - last_price) / last_price
            
            # Update if price moved more than 0.015% (significant for range trading)
            if price_change_pct > 0.00015:
                logger.info(f"🔄 Price change detected: {price_change_pct:.3%} - updating prediction")
                return True
            
            # Check for RSI threshold crossings
            current_rsi = market_data.get("rsi", 50)
            last_rsi = self.last_market_conditions.get("rsi", 50) if self.last_market_conditions else 50
            
            # Update if RSI crossed key thresholds (30, 50, 70)
            rsi_thresholds = [30, 50, 70]
            for threshold in rsi_thresholds:
                if (last_rsi < threshold < current_rsi) or (last_rsi > threshold > current_rsi):
                    logger.info(f"🔄 RSI threshold crossed: {last_rsi:.1f} → {current_rsi:.1f} (threshold: {threshold})")
                    return True
            
            # Check for support/resistance breaks
            historical_context = self.get_historical_context()
            if historical_context:
                major_levels = historical_context.get("major_levels", {})
                support_levels = major_levels.get("support", [])
                resistance_levels = major_levels.get("resistance", [])
                
                # Check if price broke through any major levels
                for level in support_levels + resistance_levels:
                    if abs(current_price - level) / level < 0.0005:  # Within 0.05% of level
                        logger.info(f"🔄 Price near major level: ${current_price:,.2f} ≈ ${level:,.2f}")
                        return True
            
            # Check for volatility regime changes
            current_volatility = market_data.get("volatility_category", "MODERATE")
            last_volatility = self.last_market_conditions.get("volatility_category", "MODERATE") if self.last_market_conditions else "MODERATE"
            
            if current_volatility != last_volatility:
                logger.info(f"🔄 Volatility regime changed: {last_volatility} → {current_volatility}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking prediction update conditions: {e}")
            return True  # Default to updating on error
    
    def generate_dynamic_prediction(self, current_price: float, market_data: Dict[str, Any], strategy_name: str = "standard") -> Dict[str, Any]:
        """
        Generate dynamic prediction that adapts to current market conditions
        
        This method:
        1. Checks if prediction should be updated
        2. Generates new prediction if conditions changed
        3. Returns updated prediction or keeps existing one
        """
        try:
            # Check if we should update the prediction
            if not self.should_update_prediction(current_price, market_data, strategy_name):
                # Return existing prediction if no update needed
                if self.last_prediction:
                    logger.debug("📊 No significant market changes - keeping existing prediction")
                    return self.last_prediction
            
            # Generate new prediction
            logger.info("🔄 Generating updated prediction based on market changes...")
            
            new_prediction = self.generate_initial_session_prediction(current_price, market_data, strategy_name)
            
            # Update tracking variables
            self.last_prediction = new_prediction
            self.last_market_conditions = {
                "rsi": market_data.get("rsi", 50),
                "volatility_category": market_data.get("volatility_category", "MODERATE"),
                "trend": market_data.get("trend", "SIDEWAYS"),
                "current_price": current_price
            }
            self.last_update_time = time.time()
            
            # Mark as dynamic update
            new_prediction["prediction_type"] = "DYNAMIC_UPDATE"
            new_prediction["update_reason"] = "Market conditions changed"
            
            # Extract key values for logging
            order_structure = new_prediction.get("order_structure", {})
            direction = order_structure.get("direction", "UNKNOWN")
            entry = order_structure.get("entry_price", 0)
            
            logger.info(f"✅ Dynamic prediction updated: {direction} at ${entry:,.2f}")
            
            return new_prediction
            
        except Exception as e:
            logger.error(f"❌ Error generating dynamic prediction: {e}")
            # Return last prediction on error
            return self.last_prediction or {}
    
    def generate_initial_session_prediction(self, current_price: float, market_data: Dict[str, Any], strategy_name: str = "standard") -> Dict[str, Any]:
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
            
            # MARKET CONDITIONS CHECK (ensure conditions are tradable)
            from strategies.market_conditions_analyzer import global_conditions_analyzer
            
            conditions_analysis = global_conditions_analyzer.analyze_trading_conditions(
                market_data={
                    "current_price": current_price,
                    "rsi": rsi_value,
                    "trend": trend,
                    "volatility_5m": volatility_5m,
                    "volatility_category": volatility_category,
                    "volume_category": market_data.get("volume_category", "NORMAL")  # Use actual volume data
                },
                historical_context=historical_context,
                strategy_name=strategy_name
            )
            
            # Determine trade direction using historical context + current conditions + market conditions
            direction, reasoning = self._determine_initial_direction(
                current_price, rsi_value, trend, volatility_category, historical_context, conditions_analysis
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
                "session_strategy": historical_context.get("strategy_recommendations", {}).get("primary", "standard"),
                "market_conditions": {
                    "is_tradable": conditions_analysis["is_tradable"],
                    "condition": conditions_analysis["condition"],
                    "risk_level": conditions_analysis["risk_level"],
                    "main_factors": conditions_analysis["reasons"][:3]  # Top 3 factors
                }
            }
            
            logger.success(f"✅ Initial prediction: {direction} @ ${order_prices['entry']:.2f} (Stop: ${order_prices['stop_loss']:.2f}, Take: ${order_prices['take_profit']:.2f})")
            return initial_prediction
            
        except Exception as e:
            logger.error(f"❌ Initial session prediction failed: {e}")
            return self._get_default_initial_prediction(current_price)
    
    def _determine_initial_direction(self, current_price: float, rsi: float, trend: str, 
                                   volatility_category: str, historical_context: Dict, conditions_analysis: Dict) -> Tuple[str, str]:
        """Determine initial trade direction using historical context + current conditions + market conditions"""
        try:
            # Get market conditions assessment
            market_condition = conditions_analysis.get("condition", "UNKNOWN")
            is_tradable = conditions_analysis.get("is_tradable", False)
            
            # ADJUST STRATEGY based on market conditions
            if not is_tradable:
                # For untradable conditions, provide conservative prediction with warning
                direction = "BUY" if rsi < 50 else "SELL"
                return direction, f"⚠️ UNTRADABLE conditions ({market_condition}) - Conservative {direction} bias only"
            
            # Get historical insights
            market_regime = historical_context.get("market_regime", {}).get("regime", "UNKNOWN")
            major_levels = historical_context.get("major_levels", {})
            support_levels = major_levels.get("support", [])
            resistance_levels = major_levels.get("resistance", [])
            
            # EXCELLENT/GOOD CONDITIONS: Enhanced trading logic
            if market_condition in ["EXCELLENT", "GOOD"]:
                # Strong directional bias with good conditions
                if rsi <= 30 and trend in ["UPTREND", "STRONG_UPTREND"]:
                    return "BUY", f"🎯 Strong BUY: Oversold RSI ({rsi:.1f}) + {trend} in {market_condition} conditions"
                elif rsi >= 70 and trend in ["DOWNTREND", "STRONG_DOWNTREND"]:
                    return "SELL", f"🎯 Strong SELL: Overbought RSI ({rsi:.1f}) + {trend} in {market_condition} conditions"
            
            # Range trading for ranging markets
            if market_regime in ["RANGING", "TIGHT_RANGING"]:
                # Check proximity to support/resistance levels
                near_support = support_levels and any(abs(current_price - level) / level < 0.02 for level in support_levels)
                near_resistance = resistance_levels and any(abs(current_price - level) / level < 0.02 for level in resistance_levels)
                
                # Enhanced range trading logic with price action consideration
                if near_resistance and rsi >= 50:
                    # Near resistance + RSI not oversold = SELL opportunity
                    return "SELL", f"Range trade: Near resistance in {market_regime} regime (RSI: {rsi:.1f})"
                elif near_support and rsi <= 50:
                    # Near support + RSI not overbought = BUY opportunity  
                    return "BUY", f"Range trade: Near support in {market_regime} regime (RSI: {rsi:.1f})"
                elif near_resistance:
                    # Near resistance but RSI oversold = wait or weak SELL
                    return "SELL", f"Range trade: Near resistance but RSI oversold (RSI: {rsi:.1f})"
                elif near_support:
                    # Near support but RSI overbought = wait or weak BUY
                    return "BUY", f"Range trade: Near support but RSI overbought (RSI: {rsi:.1f})"
            
            # Standard RSI-based decision with trend confirmation  
            if rsi <= 35 and trend in ["UPTREND", "WEAK_UPTREND", "SIDEWAYS"]:
                return "BUY", f"RSI oversold ({rsi:.1f}) + {trend} bias"
            elif rsi >= 65 and trend in ["DOWNTREND", "WEAK_DOWNTREND", "SIDEWAYS"]:
                return "SELL", f"RSI overbought ({rsi:.1f}) + {trend} bias"
            
            # Marginal conditions: Conservative bias
            if market_condition == "MARGINAL":
                direction = "BUY" if rsi < 50 else "SELL"
                return direction, f"Marginal conditions - Conservative {direction} (RSI: {rsi:.1f})"
            
            # Default: RSI-based bias
            if rsi < 50:
                return "BUY", f"Bullish RSI bias ({rsi:.1f})"
            else:
                return "SELL", f"Bearish RSI bias ({rsi:.1f})"
                
        except Exception as e:
            logger.error(f"❌ Initial direction determination failed: {e}")
            return "BUY", "Default buy direction due to error"
    
    def _calculate_range_trading_levels(self, current_price: float, direction: str, 
                                      support_levels: List[float], resistance_levels: List[float]) -> Dict[str, float]:
        """Calculate range trading levels using actual support/resistance levels"""
        try:
            # Find the nearest support and resistance levels
            nearest_support = min(support_levels, key=lambda x: abs(x - current_price)) if support_levels else None
            
            # Filter resistance levels to only include those above current price
            valid_resistance_levels = [level for level in resistance_levels if level > current_price]
            nearest_resistance = min(valid_resistance_levels, key=lambda x: abs(x - current_price)) if valid_resistance_levels else None
            
            # For BUY orders in range trading
            if direction == "BUY":
                # Entry: slightly below current price
                entry_price = current_price * 0.9999  # 0.01% below current
                
                # Stop loss: below the nearest support level
                if nearest_support and nearest_support < current_price:
                    stop_loss = nearest_support * 0.999  # 0.1% below support
                else:
                    stop_loss = current_price * 0.995  # 0.5% below current (fallback)
                
                # Take profit: at the nearest resistance level (aggressive for range trading)
                if nearest_resistance and nearest_resistance > current_price:
                    take_profit = nearest_resistance * 0.9998  # 0.02% below resistance (very aggressive)
                else:
                    # Fallback: use a reasonable take profit above current price
                    take_profit = current_price * 1.002  # 0.2% above current (better fallback)
            
            # For SELL orders in range trading
            else:  # SELL
                # Entry: slightly above current price
                entry_price = current_price * 1.0001  # 0.01% above current
                
                # Stop loss: above the nearest resistance level
                if nearest_resistance and nearest_resistance > current_price:
                    stop_loss = nearest_resistance * 1.001  # 0.1% above resistance
                else:
                    stop_loss = current_price * 1.005  # 0.5% above current (fallback)
                
                # Take profit: at the nearest support level (aggressive for range trading)
                if nearest_support and nearest_support < current_price:
                    # For range trading, target very close to the actual support level
                    take_profit = nearest_support * 1.0002  # 0.02% above support (very aggressive)
                else:
                    take_profit = current_price * 0.998  # 0.2% below current (better fallback)
            
            logger.info(f"🎯 Range Trading Levels: Entry=${entry_price:.2f}, Stop=${stop_loss:.2f}, Take=${take_profit:.2f}")
            logger.info(f"   Support: {nearest_support}, Resistance: {nearest_resistance}")
            
            return {
                "entry": round(entry_price, 2),
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Range trading levels calculation failed: {e}")
            # Fallback to percentage-based calculation
            return self._calculate_percentage_based_levels(current_price, direction)
    
    def _calculate_percentage_based_levels(self, current_price: float, direction: str) -> Dict[str, float]:
        """Fallback percentage-based calculation"""
        if direction == "BUY":
            entry_price = current_price * 0.9999
            stop_loss = current_price * 0.995
            take_profit = current_price * 1.001
        else:  # SELL
            entry_price = current_price * 1.0001
            stop_loss = current_price * 1.005
            take_profit = current_price * 0.999
        
        return {
            "entry": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2)
        }
    
    def _calculate_limit_order_structure(self, current_price: float, direction: str, 
                                       volatility_5m: float, historical_context: Dict) -> Dict[str, float]:
        """Calculate limit order prices (entry, stop loss, take profit)"""
        try:
            # Dynamic risk management based on volatility (using centralized constants)
            from core.constants import VariabilityConstants
            
            # Check if we have support/resistance levels for range trading
            major_levels = historical_context.get("major_levels", {})
            support_levels = major_levels.get("support", [])
            resistance_levels = major_levels.get("resistance", [])
            
            # For VERY_LOW volatility (range trading), use support/resistance levels if available
            if volatility_5m <= VariabilityConstants.VOLATILITY_5M_VERY_LOW and (support_levels or resistance_levels):
                return self._calculate_range_trading_levels(
                    current_price, direction, support_levels, resistance_levels
                )
            
            # Fallback to percentage-based calculations
            if volatility_5m <= VariabilityConstants.VOLATILITY_5M_VERY_LOW:  # Very low volatility
                stop_distance_pct = 0.0005  # 0.05% (very tight stops for ranging)
                take_distance_pct = 0.001   # 0.1% (very small targets for ranging)
                entry_buffer_pct = 0.0001   # 0.01% buffer from current price
            elif volatility_5m < VariabilityConstants.VOLATILITY_5M_MODERATE:  # Low volatility
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