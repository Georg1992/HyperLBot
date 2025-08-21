#!/usr/bin/env python3
"""
Prediction Engine Module
Handles price prediction, entry point calculation, and timeframe estimation
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger
import sys
import os

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, 'core'))

from config import TradingConfig

class PredictionEngine:
    """Advanced prediction engine for trading entry points"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        self.config = TradingConfig()
        
        # Prediction types
        self.PREDICTION_TYPES = {
            "BREAKOUT_ABOVE": "BUY",
            "BREAKOUT_BELOW": "SELL", 
            "REVERSION_FROM_RESISTANCE": "SELL",
            "REVERSION_FROM_SUPPORT": "BUY",
            "MOMENTUM_UP": "BUY",
            "MOMENTUM_DOWN": "SELL"
        }
        
        logger.info("🎯 Prediction Engine initialized")
    
    def build_price_prediction(self, binance_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Build price prediction and identify potential entry points"""
        try:
            # Extract data from Binance analysis
            candles_5m = binance_analysis.get("candles_5m", [])
            candles_1h = binance_analysis.get("candles_1h", [])
            trend_5m = binance_analysis.get("trend_5m", {})
            trend_1h = binance_analysis.get("trend_1h", {})
            support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
            
            if len(candles_5m) < 10 or len(candles_1h) < 10:
                return {"has_prediction": False, "reason": "Insufficient candlestick data"}
            
            support_5m = support_resistance_5m.get("support", 0)
            resistance_5m = support_resistance_5m.get("resistance", 0)
            range_size_5m = support_resistance_5m.get("range", 0)
            
            # Minimum range requirement
            min_range_percentage = self.strategy_config["min_range_percentage"]
            if range_size_5m < current_price * min_range_percentage:
                return {"has_prediction": False, "reason": f"Range too small (need {min_range_percentage*100:.1f}%, have {range_size_5m/current_price*100:.1f}%)"}
            
            # Calculate volatility for prediction confidence
            volatility_5m = self._get_volatility_5m(binance_analysis)
            volatility_1h = self._get_volatility_1h(binance_analysis)
            
            # Build predictions based on market conditions
            predictions = []
            
            # 1. BREAKOUT PREDICTIONS
            if current_price > resistance_5m * 0.998:  # Near resistance
                # Predict potential breakout above resistance
                breakout_prediction = {
                    "type": "BREAKOUT_ABOVE",
                    "entry_price": resistance_5m * 1.0005,  # Slightly above resistance
                    "side": "BUY",
                    "confidence": self._calculate_breakout_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                    "reason": f"Potential breakout above ${resistance_5m:,.2f}",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(breakout_prediction)
            
            elif current_price < support_5m * 1.002:  # Near support
                # Predict potential breakout below support
                breakout_prediction = {
                    "type": "BREAKOUT_BELOW",
                    "entry_price": support_5m * 0.9995,  # Slightly below support
                    "side": "SELL",
                    "confidence": self._calculate_breakout_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                    "reason": f"Potential breakout below ${support_5m:,.2f}",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(breakout_prediction)
            
            # 2. REVERSION PREDICTIONS
            if current_price > resistance_5m * 0.999:  # Very near resistance
                # Predict potential reversion from resistance
                reversion_prediction = {
                    "type": "REVERSION_FROM_RESISTANCE",
                    "entry_price": resistance_5m * 0.9995,  # Slightly below resistance
                    "side": "SELL",
                    "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_reversion_timeframe(volatility_5m),
                    "reason": f"Potential reversion from ${resistance_5m:,.2f}",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(reversion_prediction)
            
            elif current_price < support_5m * 1.001:  # Very near support
                # Predict potential reversion from support
                reversion_prediction = {
                    "type": "REVERSION_FROM_SUPPORT",
                    "entry_price": support_5m * 1.0005,  # Slightly above support
                    "side": "BUY",
                    "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_reversion_timeframe(volatility_5m),
                    "reason": f"Potential reversion from ${support_5m:,.2f}",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(reversion_prediction)
            
            # 3. MOMENTUM PREDICTIONS
            if trend_1h.get("trend") == "UP" and trend_5m.get("trend") == "UP":
                # Strong upward momentum
                momentum_prediction = {
                    "type": "MOMENTUM_UP",
                    "entry_price": current_price * 1.0005,  # Slightly above current
                    "side": "BUY",
                    "confidence": self._calculate_momentum_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_momentum_timeframe(volatility_5m),
                    "reason": "Strong upward momentum",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(momentum_prediction)
            
            elif trend_1h.get("trend") == "DOWN" and trend_5m.get("trend") == "DOWN":
                # Strong downward momentum
                momentum_prediction = {
                    "type": "MOMENTUM_DOWN",
                    "entry_price": current_price * 0.9995,  # Slightly below current
                    "side": "SELL",
                    "confidence": self._calculate_momentum_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_momentum_timeframe(volatility_5m),
                    "reason": "Strong downward momentum",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(momentum_prediction)
            
            # Select best prediction based on confidence
            if predictions:
                best_prediction = max(predictions, key=lambda x: x["confidence"])
                
                return {
                    "has_prediction": True,
                    "best_prediction": best_prediction,
                    "all_predictions": predictions,
                    "volatility_5m": volatility_5m,
                    "volatility_1h": volatility_1h,
                    "range_size": range_size_5m,
                    "support": support_5m,
                    "resistance": resistance_5m
                }
            else:
                return {"has_prediction": False, "reason": "No valid predictions found"}
                
        except Exception as e:
            logger.error(f"Error building price prediction: {e}")
            return {"has_prediction": False, "reason": f"Prediction error: {str(e)}"}
    
    def _get_volatility_5m(self, binance_analysis: Dict[str, Any]) -> float:
        """Calculate 5-minute volatility"""
        try:
            candles_5m = binance_analysis.get("candles_5m", [])
            if len(candles_5m) < 10:
                return 0.003  # Default volatility
            
            # Calculate price changes
            price_changes = []
            for i in range(1, min(10, len(candles_5m))):
                prev_close = float(candles_5m[i-1][4])
                curr_close = float(candles_5m[i][4])
                change = abs(curr_close - prev_close) / prev_close
                price_changes.append(change)
            
            return sum(price_changes) / len(price_changes) if price_changes else 0.003
            
        except Exception as e:
            logger.error(f"Error calculating 5m volatility: {e}")
            return 0.003
    
    def _get_volatility_1h(self, binance_analysis: Dict[str, Any]) -> float:
        """Calculate 1-hour volatility"""
        try:
            candles_1h = binance_analysis.get("candles_1h", [])
            if len(candles_1h) < 10:
                return 0.005  # Default volatility
            
            # Calculate price changes
            price_changes = []
            for i in range(1, min(10, len(candles_1h))):
                prev_close = float(candles_1h[i-1][4])
                curr_close = float(candles_1h[i][4])
                change = abs(curr_close - prev_close) / prev_close
                price_changes.append(change)
            
            return sum(price_changes) / len(price_changes) if price_changes else 0.005
            
        except Exception as e:
            logger.error(f"Error calculating 1h volatility: {e}")
            return 0.005
    
    def _calculate_breakout_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float) -> float:
        """Calculate confidence for breakout predictions"""
        base_confidence = 0.5
        
        # Trend alignment bonus
        if trend_1h.get("trend") == trend_5m.get("trend"):
            base_confidence += 0.2
        
        # Trend strength bonus
        trend_strength = trend_1h.get("strength", 0.5)
        base_confidence += trend_strength * 0.1
        
        # Volatility adjustment
        if volatility < 0.002:  # Low volatility = more predictable
            base_confidence += 0.1
        elif volatility > 0.005:  # High volatility = less predictable
            base_confidence -= 0.1
        
        return min(0.95, max(0.1, base_confidence))
    
    def _calculate_reversion_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float) -> float:
        """Calculate confidence for reversion predictions"""
        base_confidence = 0.4  # Lower base for reversions
        
        # Trend divergence bonus (reversion more likely when trends diverge)
        if trend_1h.get("trend") != trend_5m.get("trend"):
            base_confidence += 0.15
        
        # Volatility adjustment
        if volatility < 0.002:  # Low volatility = more predictable reversions
            base_confidence += 0.1
        elif volatility > 0.005:  # High volatility = less predictable
            base_confidence -= 0.1
        
        return min(0.9, max(0.1, base_confidence))
    
    def _calculate_momentum_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float) -> float:
        """Calculate confidence for momentum predictions"""
        base_confidence = 0.6  # Higher base for momentum
        
        # Strong trend alignment
        if trend_1h.get("trend") == trend_5m.get("trend"):
            base_confidence += 0.2
        
        # Trend strength bonus
        trend_strength = trend_1h.get("strength", 0.5)
        base_confidence += trend_strength * 0.15
        
        # Volatility adjustment
        if volatility < 0.003:  # Moderate volatility = good for momentum
            base_confidence += 0.1
        elif volatility > 0.006:  # High volatility = less predictable
            base_confidence -= 0.1
        
        return min(0.95, max(0.1, base_confidence))
    
    def _calculate_breakout_timeframe(self, volatility: float, range_size: float) -> int:
        """Calculate expected timeframe for breakout"""
        # Base timeframe: 15-30 minutes
        base_timeframe = 20
        
        # Adjust based on volatility
        if volatility < 0.002:
            base_timeframe += 10  # Slower in low volatility
        elif volatility > 0.005:
            base_timeframe -= 5   # Faster in high volatility
        
        # Adjust based on range size
        range_percentage = range_size / 114000  # Assuming current BTC price
        if range_percentage < 0.005:  # Small range
            base_timeframe += 5
        elif range_percentage > 0.01:  # Large range
            base_timeframe -= 5
        
        return max(10, min(60, base_timeframe))  # Between 10-60 minutes
    
    def _calculate_reversion_timeframe(self, volatility: float) -> int:
        """Calculate expected timeframe for reversion"""
        # Reversions typically happen faster than breakouts
        base_timeframe = 15
        
        # Adjust based on volatility
        if volatility < 0.002:
            base_timeframe += 5
        elif volatility > 0.005:
            base_timeframe -= 3
        
        return max(8, min(45, base_timeframe))  # Between 8-45 minutes
    
    def _calculate_momentum_timeframe(self, volatility: float) -> int:
        """Calculate expected timeframe for momentum continuation"""
        # Momentum trades can be faster
        base_timeframe = 12
        
        # Adjust based on volatility
        if volatility < 0.002:
            base_timeframe += 3
        elif volatility > 0.005:
            base_timeframe -= 2
        
        return max(5, min(30, base_timeframe))  # Between 5-30 minutes
    
    def is_prediction_valid(self, prediction: Dict[str, Any], current_price: float) -> bool:
        """Check if prediction is still valid given current price"""
        entry_price = prediction["entry_price"]
        price_diff = abs(current_price - entry_price) / current_price
        
        # Prediction is valid if price is within 0.5% of entry
        return price_diff < 0.005
    
    def calculate_prediction_win_probability(self, prediction: Dict[str, Any], prediction_analysis: Dict[str, Any]) -> float:
        """Calculate win probability for a prediction"""
        base_probability = prediction["confidence"]
        
        # Adjust based on volatility
        volatility_5m = prediction_analysis.get("volatility_5m", 0.003)
        if volatility_5m < 0.002:
            base_probability += 0.05  # More predictable in low volatility
        elif volatility_5m > 0.005:
            base_probability -= 0.05  # Less predictable in high volatility
        
        # Adjust based on range size
        range_size = prediction_analysis.get("range_size", 0)
        if range_size > 0:
            range_percentage = range_size / 114000
            if range_percentage > 0.01:  # Large range
                base_probability += 0.03
            elif range_percentage < 0.005:  # Small range
                base_probability -= 0.02
        
        return min(0.95, max(0.1, base_probability))
    
    def analyze_entry_point(self, prediction_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Analyze entry point and determine if order should be placed"""
        try:
            if not prediction_analysis.get("has_prediction", False):
                return {"should_place_order": False, "reason": "No valid prediction"}
            
            prediction = prediction_analysis["best_prediction"]
            
            # Check if prediction is still valid
            if not self.is_prediction_valid(prediction, current_price):
                return {"should_place_order": False, "reason": "Prediction no longer valid"}
            
            # Calculate win probability
            win_probability = self.calculate_prediction_win_probability(prediction, prediction_analysis)
            
            # Check confidence threshold
            confidence_threshold = self.strategy_config.get("confidence_threshold", 0.6)
            if prediction["confidence"] < confidence_threshold:
                return {"should_place_order": False, "reason": f"Confidence too low ({prediction['confidence']:.2f} < {confidence_threshold})"}
            
            # Calculate target and stop prices
            entry_price = prediction["entry_price"]
            side = prediction["side"]
            
            # Get strategy-specific parameters
            profit_target_pct = self.strategy_config.get("profit_target", 0.01)
            stop_loss_pct = self.strategy_config.get("stop_loss", 0.005)
            
            if side == "BUY":
                target_price = entry_price * (1 + profit_target_pct)
                stop_price = entry_price * (1 - stop_loss_pct)
            else:  # SELL
                target_price = entry_price * (1 - profit_target_pct)
                stop_price = entry_price * (1 + stop_loss_pct)
            
            # Calculate profitability (simplified)
            potential_profit = abs(target_price - entry_price) * 0.001  # Assuming 0.001 BTC position
            potential_loss = abs(stop_price - entry_price) * 0.001
            risk_reward_ratio = potential_profit / potential_loss if potential_loss > 0 else 0
            
            return {
                "should_place_order": True,
                "entry_price": entry_price,
                "target_price": target_price,
                "stop_price": stop_price,
                "side": side,
                "prediction_type": prediction["type"],
                "confidence": prediction["confidence"],
                "win_probability": win_probability,
                "timeframe": prediction["timeframe"],
                "reason": prediction["reason"],
                "risk_reward_ratio": risk_reward_ratio,
                "volatility_5m": prediction_analysis.get("volatility_5m", 0),
                "range_size": prediction_analysis.get("range_size", 0)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing entry point: {e}")
            return {"should_place_order": False, "reason": f"Analysis error: {str(e)}"}
