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
