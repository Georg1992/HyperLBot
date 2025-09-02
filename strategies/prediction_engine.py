#!/usr/bin/env python3
"""
Prediction Engine for Trading Bot
Generates price predictions using technical analysis
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

# Import core module to setup paths
import core

from config.config import TradingConfig
from core.constants import volume_constants

class PredictionEngine:
    """Clean prediction engine focused on generating structured trading predictions"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        self.config = TradingConfig()
        self.session_manager = None  # Will be set by SessionOrchestrator for historical context
        
        # Standardized high volume categories for consistent usage
        self.high_volume_categories = [
            volume_constants.VOLUME_CATEGORY_HIGH,
            volume_constants.VOLUME_CATEGORY_VERY_HIGH,
            volume_constants.VOLUME_CATEGORY_EXTREMELY_HIGH
        ]
        
        logger.info("🎯 Clean Prediction Engine initialized")
    
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
    
    def generate_structured_prediction(self, market_data: Dict[str, Any], historical_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate structured trading prediction with exact format:
        - BUY/SELL direction
        - Size (BTC/USD)
        - Entry Price
        - RSI Value (at prediction time) - FROM REAL RSI CALCULATOR
        - TREND value
        """
        try:
            current_price = market_data.get("current_price", 0)
            
            # Get RSI from market data (Yahoo 5m candle analysis - simple!)
            from core.constants import technical_constants
            rsi_value = market_data.get("rsi", technical_constants.RSI_NEUTRAL)
            
            # Prediction engine using calibrated real-time RSI (clean, no spam logging)
            
            trend = market_data.get("trend", "NEUTRAL")
            volume_category = market_data.get("volume_category", "NORMAL")
            volatility_5m = market_data.get("volatility_5m", 0.0)
            
            # Use historical context if provided for confidence
            confidence = 0.3  # Start with low confidence as requested
            
            if historical_analysis:
                confidence = self._calculate_confidence(market_data, historical_analysis)
            
            # Determine trade direction based on market conditions
            direction, entry_price, reasoning = self._determine_trade_direction(
                current_price, rsi_value, trend, volume_category, volatility_5m
            )
            
            # Calculate position size based on confidence and volatility
            size_btc, size_usd = self._calculate_position_size(
                current_price, confidence, volatility_5m
            )
            
            # Create structured prediction
            prediction = {
                "direction": direction,  # BUY/SELL
                "size_btc": round(size_btc, 6),  # Size in BTC
                "size_usd": round(size_usd, 2),  # Size in USD
                "entry_price": round(entry_price, 2),  # Entry Price
                "rsi_at_prediction": round(rsi_value, 1),  # RSI at prediction time
                "trend_at_prediction": trend,  # TREND value
                "confidence": round(confidence, 3),
                "reasoning": reasoning,
                "prediction_timestamp": time.time(),
                "prediction_time": time.strftime("%H:%M:%S"),
                "current_price": current_price,
                "market_context": {
                    "volume_category": volume_category,
                    "volatility_5m": round(volatility_5m * 100, 2),  # As percentage
                    "market_regime": self._detect_market_regime(rsi_value, trend, volatility_5m)
                }
            }
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Failed to generate structured prediction: {e}")
            return self._get_default_prediction(market_data.get("current_price", 0))
    
    def build_price_prediction(self, yahoo_analysis: Dict[str, Any], current_price: float, strategy_name: str = "standard") -> Dict[str, Any]:
        """
        Build price prediction from Yahoo analysis - compatibility method for trading bot
        """
        try:
            # Convert Yahoo analysis to market data format for structured prediction
            from core.market_data_manager import global_rsi_calculator
            from core.constants import technical_constants
            rsi_data = global_rsi_calculator.get_current_rsi_data()
            current_rsi = rsi_data.get("rsi", yahoo_analysis.get("rsi_5m", technical_constants.RSI_NEUTRAL))
            
            market_data = {
                "current_price": current_price,
                "rsi": current_rsi,  # Use real-time RSI (no more hardcoded 50.0)
                "trend": yahoo_analysis.get("trend_5m", {}).get("trend", "NEUTRAL"),
                # volume_category removed - uses orderbook depth categorization from TradingBot instead
                "volatility_5m": yahoo_analysis.get("volatility_5m", 0.0),
                "market_condition": yahoo_analysis.get("market_condition", "NEUTRAL")
            }
            
            # Generate structured prediction
            prediction = self.generate_structured_prediction(market_data, yahoo_analysis)
            
            # Convert to expected format for trading bot
            return {
                "has_prediction": True,
                "confidence": prediction.get("confidence", 0.3),
                "direction": prediction.get("direction", "HOLD"),
                "entry_price": prediction.get("entry_price", current_price),
                "target_price": current_price * 1.01 if prediction.get("direction") == "BUY" else current_price * 0.99,
                "stop_price": current_price * 0.99 if prediction.get("direction") == "BUY" else current_price * 1.01,
                "reason": prediction.get("reasoning", "Standard prediction"),
                "prediction_data": prediction
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to build price prediction: {e}")
            return {
                "has_prediction": False,
                "confidence": 0.0,
                "reason": f"Prediction failed: {str(e)}"
            }
    
    def analyze_entry_point(self, prediction_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Analyze entry point using prediction analysis
        """
        try:
            if not prediction_analysis.get("has_prediction", False):
                return {
                    "should_place_order": False,
                    "reason": "No valid prediction",
                    "side": "HOLD",
                    "entry_price": current_price,
                    "target_price": current_price,
                    "stop_price": current_price,
                    "confidence": 0.0,
                    "variability_threshold": 0.0
                }
            
            direction = prediction_analysis.get("direction", "HOLD")
            entry_price = prediction_analysis.get("entry_price", current_price)
            confidence = prediction_analysis.get("confidence", 0.0)
            
            # Calculate target and stop prices
            if direction == "BUY":
                target_price = entry_price * 1.01  # 1% target
                stop_price = entry_price * 0.99   # 1% stop
            elif direction == "SELL":
                target_price = entry_price * 0.99  # 1% target
                stop_price = entry_price * 1.01   # 1% stop
            else:
                return {
                    "should_place_order": False,
                    "reason": "No clear direction",
                    "side": "HOLD",
                    "entry_price": current_price,
                    "target_price": current_price,
                    "stop_price": current_price,
                    "confidence": 0.0,
                    "variability_threshold": 0.0
                }
            
            # Determine if we should place order based on confidence
            should_place = confidence > 0.3 and direction in ["BUY", "SELL"]
            
            return {
                "should_place_order": should_place,
                "reason": prediction_analysis.get("reason", "Standard analysis"),
                "side": direction,
                "entry_price": entry_price,
                "target_price": target_price,
                "stop_price": stop_price,
                "confidence": confidence,
                "variability_threshold": 0.5  # Default threshold
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze entry point: {e}")
            return {
                "should_place_order": False,
                "reason": f"Analysis failed: {str(e)}",
                "side": "HOLD",
                "entry_price": current_price,
                "target_price": current_price,
                "stop_price": current_price,
                "confidence": 0.0,
                "variability_threshold": 0.0
            }
    
    def calculate_win_probability(self, prediction: Dict[str, Any], prediction_analysis: Dict[str, Any]) -> float:
        """
        Calculate win probability from prediction and analysis
        """
        try:
            # Base probability on confidence
            base_probability = prediction_analysis.get("confidence", 0.0)
            
            # Adjust based on market conditions
            market_condition = prediction_analysis.get("prediction_data", {}).get("market_context", {}).get("market_regime", "NEUTRAL")
            
            if market_condition == "TRENDING":
                base_probability *= 1.1  # 10% boost for trending markets
            elif market_condition == "VOLATILE":
                base_probability *= 0.9  # 10% reduction for volatile markets
            
            # Cap at 95% maximum
            return min(base_probability, 0.95)
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate win probability: {e}")
            return 0.5  # Default 50% probability
    
    def _determine_trade_direction(self, current_price: float, rsi: float, trend: str, volume_category: str, volatility: float) -> Tuple[str, float, str]:
        """Determine optimal trade direction, entry price, and reasoning"""
        try:
            # RSI-based signals (classic oversold/overbought)
            if rsi <= 30 and trend in ["UPTREND", "WEAK_UPTREND"]:
                return "BUY", current_price * 0.999, f"RSI oversold ({rsi:.1f}) + {trend} alignment"
            
            if rsi >= 70 and trend in ["DOWNTREND", "WEAK_DOWNTREND"]:
                return "SELL", current_price * 1.001, f"RSI overbought ({rsi:.1f}) + {trend} alignment"
            
            # Trend-following signals using standardized volume categories
            if trend == "UPTREND" and volume_category in self.high_volume_categories:
                return "BUY", current_price * 0.9995, f"Strong {trend} + {volume_category} volume"
            
            if trend == "DOWNTREND" and volume_category in self.high_volume_categories:
                return "SELL", current_price * 1.0005, f"Strong {trend} + {volume_category} volume"
            
            # Volatility-based opportunities
            if volatility > 0.02 and rsi < 50:  # High volatility + bearish RSI
                return "SELL", current_price * 1.0003, f"High volatility ({volatility*100:.1f}%) + bearish RSI"
            
            if volatility > 0.02 and rsi > 50:  # High volatility + bullish RSI
                return "BUY", current_price * 0.9997, f"High volatility ({volatility*100:.1f}%) + bullish RSI"
            
            # Default: Neutral with slight bias based on RSI
            if rsi < 50:
                return "BUY", current_price * 0.9998, f"Slight RSI bias ({rsi:.1f}) - waiting for opportunity"
            else:
                return "SELL", current_price * 1.0002, f"Slight RSI bias ({rsi:.1f}) - waiting for opportunity"
            
        except Exception as e:
            logger.error(f"❌ Trade direction determination failed: {e}")
            return "BUY", current_price, "Default prediction due to error"
    
    def _calculate_position_size(self, current_price: float, confidence: float, volatility: float) -> Tuple[float, float]:
        """Calculate position size based on confidence and market volatility"""
        try:
            from core.constants import MagicNumbers
            # Base position size (conservative for testing)
            base_usd = MagicNumbers.DEFAULT_POSITION_SIZE_USD  # Default position size
            
            # Adjust for confidence (0.3-1.0 range)
            confidence_multiplier = max(0.5, confidence)  # Minimum 0.5x, maximum 1.0x
            
            # Adjust for volatility (reduce size in high volatility)
            volatility_multiplier = max(0.5, 1.0 - volatility * 2)  # Reduce size if volatile
            
            # Calculate final USD size
            size_usd = base_usd * confidence_multiplier * volatility_multiplier
            
            # Convert to BTC
            size_btc = size_usd / current_price if current_price > 0 else 0
            
            return size_btc, size_usd
            
        except Exception as e:
            logger.error(f"❌ Position size calculation failed: {e}")
            return MagicNumbers.DEFAULT_POSITION_SIZE_BTC, MagicNumbers.DEFAULT_POSITION_SIZE_USD  # Safe defaults
    
    def _calculate_confidence(self, market_data: Dict[str, Any], historical_analysis: Dict[str, Any]) -> float:
        """Calculate confidence using both real-time and historical data"""
        try:
            from core.constants import MagicNumbers
            base_confidence = 0.3  # Start low as requested
            
            # Get RSI from market data (Yahoo 5m candle analysis - simple!)
            from core.constants import technical_constants
            rsi = market_data.get("rsi", technical_constants.RSI_NEUTRAL)
            trend = market_data.get("trend", "NEUTRAL")
            volume_category = market_data.get("volume_category", "NORMAL")
            
            # RSI extreme values increase confidence
            if rsi <= 25 or rsi >= 75:
                base_confidence += 0.3  # Strong RSI signal
            elif rsi <= 30 or rsi >= 70:
                base_confidence += 0.2  # Moderate RSI signal
            
            # Trend alignment increases confidence
            if trend in ["UPTREND", "DOWNTREND"]:
                base_confidence += 0.2
            elif trend in ["WEAK_UPTREND", "WEAK_DOWNTREND"]:
                base_confidence += 0.1
            
            # Volume confirmation increases confidence using standardized categories
            if volume_category in self.high_volume_categories:
                base_confidence += 0.15
            
            # Cap confidence at 0.85 (conservative maximum)
            return min(0.85, base_confidence)
            
        except Exception as e:
            logger.error(f"❌ Confidence calculation failed: {e}")
            return 0.3  # Safe default
    
    def _detect_market_regime(self, rsi: float, trend: str, volatility: float) -> str:
        """Detect current market regime for prediction context"""
        try:
            if volatility > 0.03:  # > 3% volatility
                return "VOLATILE"
            elif trend in ["UPTREND", "DOWNTREND"]:
                return "TRENDING"
            elif rsi > 45 and rsi < 55:
                return "RANGING"
            else:
                return "TRANSITIONAL"
        except:
            return "UNKNOWN"
    
    def _get_default_prediction(self, current_price: float) -> Dict[str, Any]:
        """Generate safe default prediction when analysis fails"""
        from core.constants import MagicNumbers, technical_constants
        return {
            "direction": "BUY",
            "size_btc": 0.001,
            "size_usd": MagicNumbers.DEFAULT_POSITION_SIZE_USD,
            "entry_price": current_price * 0.999 if current_price > 0 else 18500,
            "rsi_at_prediction": technical_constants.RSI_NEUTRAL,
            "trend_at_prediction": "NEUTRAL",
            "confidence": 0.1,
            "reasoning": "Default low-confidence prediction",
            "prediction_timestamp": time.time(),
            "prediction_time": time.strftime("%H:%M:%S"),
            "current_price": current_price,
            "market_context": {
                "volume_category": "UNKNOWN",
                "volatility_5m": 0.0,
                "market_regime": "UNKNOWN"
            }
        }
