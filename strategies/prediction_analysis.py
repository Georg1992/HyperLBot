#!/usr/bin/env python3
"""
Prediction Analysis Module
Contains analysis and validation methods extracted from prediction_engine.py
"""

import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

class PredictionAnalysis:
    """Analysis and validation methods for prediction engine"""
    
    def __init__(self):
        """Initialize prediction analysis system"""
        logger.info("🎯 Prediction Analysis system initialized")
    
    def validate_prediction_scenario(self, prediction: Dict[str, Any], candles_5m: List, current_price: float) -> Dict[str, Any]:
        """Validate prediction against recent price action"""
        try:
            if not candles_5m or len(candles_5m) < 10:
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "reason": "Insufficient candle data for validation",
                    "validation_score": 0.0
                }
            
            prediction_type = prediction.get("type", "UNKNOWN")
            entry_price = prediction.get("entry_price", current_price)
            expected_direction = prediction.get("side", "HOLD")
            
            # Extract recent price data
            recent_prices = [float(candle.get("close", 0)) for candle in candles_5m[-10:] if candle.get("close")]
            recent_highs = [float(candle.get("high", 0)) for candle in candles_5m[-10:] if candle.get("high")]
            recent_lows = [float(candle.get("low", 0)) for candle in candles_5m[-10:] if candle.get("low")]
            
            if not recent_prices or len(recent_prices) < 5:
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "reason": "Insufficient price data for validation",
                    "validation_score": 0.0
                }
            
            # Validate based on prediction type
            if prediction_type == "BREAKOUT_ABOVE":
                return self._validate_breakout_scenario(prediction, recent_prices, recent_highs, expected_direction)
            elif prediction_type == "BREAKOUT_BELOW":
                return self._validate_breakout_scenario(prediction, recent_prices, recent_lows, expected_direction)
            elif prediction_type == "REVERSION_FROM_RESISTANCE":
                return self._validate_resistance_rejection_scenario(prediction, recent_prices, recent_highs, expected_direction)
            elif prediction_type == "REVERSION_FROM_SUPPORT":
                return self._validate_support_bounce_scenario(prediction, recent_prices, recent_lows, expected_direction)
            elif prediction_type == "MOMENTUM_UP":
                return self._validate_momentum_continuation_scenario(prediction, recent_prices, expected_direction)
            elif prediction_type == "MOMENTUM_DOWN":
                return self._validate_momentum_continuation_scenario(prediction, recent_prices, expected_direction)
            else:
                return self._validate_generic_scenario(prediction, recent_prices, expected_direction)
                
        except Exception as e:
            logger.error(f"Prediction validation failed: {e}")
            return {
                "is_valid": False,
                "confidence": 0.0,
                "reason": f"Validation error: {str(e)}",
                "validation_score": 0.0
            }
    
    def _validate_support_bounce_scenario(self, prediction: Dict, recent_prices: List, recent_lows: List, expected_direction: str) -> Dict[str, Any]:
        """Validate support bounce prediction"""
        try:
            if not recent_prices or len(recent_prices) < 5:
                return {"is_valid": False, "confidence": 0.0, "reason": "Insufficient data", "validation_score": 0.0}
            
            entry_price = prediction.get("entry_price", recent_prices[-1])
            
            # Check if price is near recent lows (support)
            recent_min = min(recent_lows) if recent_lows else min(recent_prices)
            price_near_support = abs(entry_price - recent_min) / recent_min < 0.01  # Within 1%
            
            # Check if price is showing bounce pattern
            last_3_prices = recent_prices[-3:]
            if len(last_3_prices) >= 3:
                price_trend = (last_3_prices[-1] - last_3_prices[0]) / last_3_prices[0]
                is_bouncing = price_trend > 0.002  # 0.2% upward movement
            else:
                is_bouncing = False
            
            # Calculate validation score
            validation_score = 0.0
            if price_near_support:
                validation_score += 0.4
            if is_bouncing:
                validation_score += 0.4
            if expected_direction == "BUY":
                validation_score += 0.2
            
            is_valid = validation_score >= 0.6
            confidence = min(0.95, validation_score)
            
            reason = "Support bounce validation"
            if not price_near_support:
                reason += " - Price not near support"
            if not is_bouncing:
                reason += " - No bounce pattern detected"
            
            return {
                "is_valid": is_valid,
                "confidence": confidence,
                "reason": reason,
                "validation_score": validation_score,
                "price_near_support": price_near_support,
                "is_bouncing": is_bouncing
            }
            
        except Exception as e:
            logger.error(f"Support bounce validation failed: {e}")
            return {"is_valid": False, "confidence": 0.0, "reason": f"Error: {str(e)}", "validation_score": 0.0}
    
    def _validate_resistance_rejection_scenario(self, prediction: Dict, recent_prices: List, recent_highs: List, expected_direction: str) -> Dict[str, Any]:
        """Validate resistance rejection prediction"""
        try:
            if not recent_prices or len(recent_prices) < 5:
                return {"is_valid": False, "confidence": 0.0, "reason": "Insufficient data", "validation_score": 0.0}
            
            entry_price = prediction.get("entry_price", recent_prices[-1])
            
            # Check if price is near recent highs (resistance)
            recent_max = max(recent_highs) if recent_highs else max(recent_prices)
            price_near_resistance = abs(entry_price - recent_max) / recent_max < 0.01  # Within 1%
            
            # Check if price is showing rejection pattern
            last_3_prices = recent_prices[-3:]
            if len(last_3_prices) >= 3:
                price_trend = (last_3_prices[-1] - last_3_prices[0]) / last_3_prices[0]
                is_rejecting = price_trend < -0.002  # 0.2% downward movement
            else:
                is_rejecting = False
            
            # Calculate validation score
            validation_score = 0.0
            if price_near_resistance:
                validation_score += 0.4
            if is_rejecting:
                validation_score += 0.4
            if expected_direction == "SELL":
                validation_score += 0.2
            
            is_valid = validation_score >= 0.6
            confidence = min(0.95, validation_score)
            
            reason = "Resistance rejection validation"
            if not price_near_resistance:
                reason += " - Price not near resistance"
            if not is_rejecting:
                reason += " - No rejection pattern detected"
            
            return {
                "is_valid": is_valid,
                "confidence": confidence,
                "reason": reason,
                "validation_score": validation_score,
                "price_near_resistance": price_near_resistance,
                "is_rejecting": is_rejecting
            }
            
        except Exception as e:
            logger.error(f"Resistance rejection validation failed: {e}")
            return {"is_valid": False, "confidence": 0.0, "reason": f"Error: {str(e)}", "validation_score": 0.0}
    
    def _validate_momentum_continuation_scenario(self, prediction: Dict, recent_prices: List, expected_direction: str) -> Dict[str, Any]:
        """Validate momentum continuation prediction"""
        try:
            if not recent_prices or len(recent_prices) < 5:
                return {"is_valid": False, "confidence": 0.0, "reason": "Insufficient data", "validation_score": 0.0}
            
            # Check momentum direction
            last_5_prices = recent_prices[-5:]
            if len(last_5_prices) >= 5:
                momentum_trend = (last_5_prices[-1] - last_5_prices[0]) / last_5_prices[0]
                
                if expected_direction == "BUY":
                    momentum_aligned = momentum_trend > 0.003  # 0.3% upward momentum
                elif expected_direction == "SELL":
                    momentum_aligned = momentum_trend < -0.003  # 0.3% downward momentum
                else:
                    momentum_aligned = False
            else:
                momentum_aligned = False
            
            # Check recent price consistency
            last_3_prices = recent_prices[-3:]
            if len(last_3_prices) >= 3:
                recent_trend = (last_3_prices[-1] - last_3_prices[0]) / last_3_prices[0]
                consistent_momentum = abs(recent_trend) > 0.001  # 0.1% consistent movement
            else:
                consistent_momentum = False
            
            # Calculate validation score
            validation_score = 0.0
            if momentum_aligned:
                validation_score += 0.5
            if consistent_momentum:
                validation_score += 0.3
            if expected_direction in ["BUY", "SELL"]:
                validation_score += 0.2
            
            is_valid = validation_score >= 0.6
            confidence = min(0.95, validation_score)
            
            reason = "Momentum continuation validation"
            if not momentum_aligned:
                reason += " - Momentum not aligned with direction"
            if not consistent_momentum:
                reason += " - Inconsistent recent movement"
            
            return {
                "is_valid": is_valid,
                "confidence": confidence,
                "reason": reason,
                "validation_score": validation_score,
                "momentum_aligned": momentum_aligned,
                "consistent_momentum": consistent_momentum,
                "momentum_trend": momentum_trend if len(last_5_prices) >= 5 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Momentum continuation validation failed: {e}")
            return {"is_valid": False, "confidence": 0.0, "reason": f"Error: {str(e)}", "validation_score": 0.0}
    
    def _validate_breakout_scenario(self, prediction: Dict, recent_prices: List, recent_extremes: List, expected_direction: str) -> Dict[str, Any]:
        """Validate breakout prediction"""
        try:
            if not recent_prices or len(recent_prices) < 5:
                return {"is_valid": False, "confidence": 0.0, "reason": "Insufficient data", "validation_score": 0.0}
            
            entry_price = prediction.get("entry_price", recent_prices[-1])
            
            # Check if price is near recent extremes
            if expected_direction == "BUY":
                recent_extreme = max(recent_extremes) if recent_extremes else max(recent_prices)
                near_extreme = abs(entry_price - recent_extreme) / recent_extreme < 0.005  # Within 0.5%
            else:
                recent_extreme = min(recent_extremes) if recent_extremes else min(recent_prices)
                near_extreme = abs(entry_price - recent_extreme) / recent_extreme < 0.005  # Within 0.5%
            
            # Check for breakout pattern
            last_3_prices = recent_prices[-3:]
            if len(last_3_prices) >= 3:
                if expected_direction == "BUY":
                    breakout_pattern = last_3_prices[-1] > recent_extreme
                else:
                    breakout_pattern = last_3_prices[-1] < recent_extreme
            else:
                breakout_pattern = False
            
            # Calculate validation score
            validation_score = 0.0
            if near_extreme:
                validation_score += 0.4
            if breakout_pattern:
                validation_score += 0.4
            if expected_direction in ["BUY", "SELL"]:
                validation_score += 0.2
            
            is_valid = validation_score >= 0.6
            confidence = min(0.95, validation_score)
            
            reason = "Breakout validation"
            if not near_extreme:
                reason += " - Price not near extreme"
            if not breakout_pattern:
                reason += " - No breakout pattern detected"
            
            return {
                "is_valid": is_valid,
                "confidence": confidence,
                "reason": reason,
                "validation_score": validation_score,
                "near_extreme": near_extreme,
                "breakout_pattern": breakout_pattern
            }
            
        except Exception as e:
            logger.error(f"Breakout validation failed: {e}")
            return {"is_valid": False, "confidence": 0.0, "reason": f"Error: {str(e)}", "validation_score": 0.0}
    
    def _validate_generic_scenario(self, prediction: Dict, recent_prices: List, expected_direction: str) -> Dict[str, Any]:
        """Validate generic prediction scenario"""
        try:
            if not recent_prices or len(recent_prices) < 3:
                return {"is_valid": False, "confidence": 0.0, "reason": "Insufficient data", "validation_score": 0.0}
            
            entry_price = prediction.get("entry_price", recent_prices[-1])
            
            # Basic price movement validation
            last_3_prices = recent_prices[-3:]
            if len(last_3_prices) >= 3:
                price_movement = (last_3_prices[-1] - last_3_prices[0]) / last_3_prices[0]
                
                if expected_direction == "BUY":
                    movement_aligned = price_movement > 0.001  # 0.1% upward
                elif expected_direction == "SELL":
                    movement_aligned = price_movement < -0.001  # 0.1% downward
                else:
                    movement_aligned = True  # HOLD is always valid
            else:
                movement_aligned = True
            
            # Calculate validation score
            validation_score = 0.5  # Base score for generic scenario
            if movement_aligned:
                validation_score += 0.3
            if expected_direction in ["BUY", "SELL", "HOLD"]:
                validation_score += 0.2
            
            is_valid = validation_score >= 0.6
            confidence = min(0.95, validation_score)
            
            reason = "Generic scenario validation"
            if not movement_aligned:
                reason += " - Price movement not aligned with direction"
            
            return {
                "is_valid": is_valid,
                "confidence": confidence,
                "reason": reason,
                "validation_score": validation_score,
                "movement_aligned": movement_aligned
            }
            
        except Exception as e:
            logger.error(f"Generic validation failed: {e}")
            return {"is_valid": False, "confidence": 0.0, "reason": f"Error: {str(e)}", "validation_score": 0.0}
    
    def analyze_entry_point(self, prediction_analysis: Dict[str, Any], current_price: float, candles_5m: List = None) -> Dict[str, Any]:
        """Analyze optimal entry point for prediction"""
        try:
            if not candles_5m or len(candles_5m) < 5:
                return {
                    "optimal_entry": current_price,
                    "entry_confidence": 0.5,
                    "entry_reason": "Insufficient data for entry analysis",
                    "stop_loss": current_price * 0.99,
                    "take_profit": current_price * 1.01
                }
            
            prediction_type = prediction_analysis.get("type", "UNKNOWN")
            expected_direction = prediction_analysis.get("side", "HOLD")
            
            # Extract recent price data
            recent_prices = [float(candle.get("close", 0)) for candle in candles_5m[-5:] if candle.get("close")]
            recent_highs = [float(candle.get("high", 0)) for candle in candles_5m[-5:] if candle.get("high")]
            recent_lows = [float(candle.get("low", 0)) for candle in candles_5m[-5:] if candle.get("low")]
            
            if not recent_prices:
                return {
                    "optimal_entry": current_price,
                    "entry_confidence": 0.5,
                    "entry_reason": "No price data available",
                    "stop_loss": current_price * 0.99,
                    "take_profit": current_price * 1.01
                }
            
            # Calculate optimal entry based on prediction type
            if prediction_type == "BREAKOUT_ABOVE":
                optimal_entry = max(recent_highs) if recent_highs else current_price
                entry_confidence = 0.7
                entry_reason = "Breakout above resistance"
                stop_loss = optimal_entry * 0.995  # 0.5% below entry
                take_profit = optimal_entry * 1.015  # 1.5% above entry
                
            elif prediction_type == "BREAKOUT_BELOW":
                optimal_entry = min(recent_lows) if recent_lows else current_price
                entry_confidence = 0.7
                entry_reason = "Breakout below support"
                stop_loss = optimal_entry * 1.005  # 0.5% above entry
                take_profit = optimal_entry * 0.985  # 1.5% below entry
                
            elif prediction_type == "REVERSION_FROM_RESISTANCE":
                optimal_entry = max(recent_highs) if recent_highs else current_price
                entry_confidence = 0.6
                entry_reason = "Reversion from resistance"
                stop_loss = optimal_entry * 1.01  # 1% above entry
                take_profit = optimal_entry * 0.99  # 1% below entry
                
            elif prediction_type == "REVERSION_FROM_SUPPORT":
                optimal_entry = min(recent_lows) if recent_lows else current_price
                entry_confidence = 0.6
                entry_reason = "Reversion from support"
                stop_loss = optimal_entry * 0.99  # 1% below entry
                take_profit = optimal_entry * 1.01  # 1% above entry
                
            elif prediction_type in ["MOMENTUM_UP", "MOMENTUM_DOWN"]:
                optimal_entry = current_price
                entry_confidence = 0.5
                entry_reason = "Momentum continuation"
                if expected_direction == "BUY":
                    stop_loss = current_price * 0.995
                    take_profit = current_price * 1.01
                else:
                    stop_loss = current_price * 1.005
                    take_profit = current_price * 0.99
                    
            else:
                optimal_entry = current_price
                entry_confidence = 0.5
                entry_reason = "Generic entry point"
                stop_loss = current_price * 0.99
                take_profit = current_price * 1.01
            
            return {
                "optimal_entry": optimal_entry,
                "entry_confidence": entry_confidence,
                "entry_reason": entry_reason,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "current_price": current_price,
                "prediction_type": prediction_type
            }
            
        except Exception as e:
            logger.error(f"Entry point analysis failed: {e}")
            return {
                "optimal_entry": current_price,
                "entry_confidence": 0.3,
                "entry_reason": f"Analysis error: {str(e)}",
                "stop_loss": current_price * 0.99,
                "take_profit": current_price * 1.01
            }
    
    def calculate_prediction_win_probability(self, prediction: Dict[str, Any], prediction_analysis: Dict[str, Any]) -> float:
        """Calculate win probability for prediction"""
        try:
            # Base probability from prediction confidence
            base_confidence = prediction.get("confidence", 0.5)
            
            # Adjust based on validation results
            validation_score = prediction_analysis.get("validation_score", 0.5)
            
            # Adjust based on market conditions
            market_condition = prediction_analysis.get("market_condition", "UNKNOWN")
            market_multiplier = 1.0
            if market_condition == "TRENDING":
                market_multiplier = 1.1
            elif market_condition == "VOLATILE":
                market_multiplier = 0.9
            elif market_condition == "SIDEWAYS":
                market_multiplier = 0.8
            
            # Calculate final probability
            win_probability = (base_confidence * 0.6 + validation_score * 0.4) * market_multiplier
            
            # Ensure probability is within bounds
            return max(0.1, min(0.95, win_probability))
            
        except Exception as e:
            logger.error(f"Win probability calculation failed: {e}")
            return 0.5  # Conservative fallback
