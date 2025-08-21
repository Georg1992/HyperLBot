#!/usr/bin/env python3
"""
Prediction Engine for Trading Bot
Generates price predictions using technical analysis
"""

import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from collections import deque

# Import core module to setup paths
import core

from config import TradingConfig

class PredictionEngine:
    """Advanced prediction engine with reactive and predictive modes"""
    
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
        
        # Reactive types for high volatility
        self.REACTIVE_TYPES = {
            "FAST_BREAKOUT": "BUY/SELL",
            "MOMENTUM_SURGE": "BUY/SELL",
            "VOLATILITY_SPIKE": "BUY/SELL",
            "PRICE_ACCELERATION": "BUY/SELL"
        }
        
        logger.info("🎯 Enhanced Prediction Engine initialized")
    
    def build_price_prediction(self, binance_analysis: Dict[str, Any], current_price: float, strategy_name: str = "standard") -> Dict[str, Any]:
        """Build price prediction based on market volatility and strategy"""
        try:
            # Determine if we should use reactive or predictive approach
            if strategy_name == "high_volatility":
                return self._build_reactive_prediction(binance_analysis, current_price)
            else:
                return self._build_predictive_prediction(binance_analysis, current_price)
                
        except Exception as e:
            logger.error(f"Error building price prediction: {e}")
            return {"has_prediction": False, "reason": f"Prediction error: {str(e)}"}
    
    def _build_reactive_prediction(self, binance_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Build reactive prediction for high volatility markets - catch fast movements"""
        try:
            # Extract data
            candles_5m = binance_analysis.get("candles_5m", [])
            candles_1h = binance_analysis.get("candles_1h", [])
            trend_5m = binance_analysis.get("trend_5m", {})
            trend_1h = binance_analysis.get("trend_1h", {})
            
            if len(candles_5m) < 5 or len(candles_1h) < 5:
                return {"has_prediction": False, "reason": "Insufficient data for reactive analysis"}
            
            # Calculate reactive indicators
            volatility_5m = self._get_volatility_5m(binance_analysis)
            price_acceleration = self._calculate_price_acceleration(candles_5m)
            momentum_surge = self._detect_momentum_surge(candles_5m, trend_5m)
            volume_spike = self._detect_volume_spike(candles_5m)
            
            # Build reactive signals
            reactive_signals = []
            
            # 1. FAST BREAKOUT DETECTION
            if price_acceleration > 0.001:  # Much more sensitive to acceleration
                # Determine direction based on recent price action
                recent_prices = [candle["close"] for candle in candles_5m[-3:]]
                if recent_prices[-1] > recent_prices[0]:
                    signal = {
                        "type": "FAST_BREAKOUT",
                        "entry_price": current_price * 0.995,  # Enter well below current price for BUY
                        "side": "BUY",
                        "confidence": min(0.9, 0.6 + (price_acceleration * 50)),
                        "timeframe": 5,  # Very short timeframe
                        "reason": f"Fast upward breakout detected (acceleration: {price_acceleration:.3f}) - enter below current",
                        "reactive_factor": "price_acceleration"
                    }
                else:
                    signal = {
                        "type": "FAST_BREAKOUT",
                        "entry_price": current_price * 1.005,  # Enter well above current price for SELL
                        "side": "SELL",
                        "confidence": min(0.9, 0.6 + (price_acceleration * 50)),
                        "timeframe": 5,
                        "reason": f"Fast downward breakout detected (acceleration: {price_acceleration:.3f}) - enter above current",
                        "reactive_factor": "price_acceleration"
                    }
                reactive_signals.append(signal)
            
            # 2. MOMENTUM SURGE DETECTION
            if momentum_surge["detected"]:
                if momentum_surge["direction"] == "UP":
                    entry_price = current_price * 0.995  # Enter well below current for BUY
                else:
                    entry_price = current_price * 1.005  # Enter well above current for SELL
                    
                signal = {
                    "type": "MOMENTUM_SURGE",
                    "entry_price": entry_price,
                    "side": "BUY" if momentum_surge["direction"] == "UP" else "SELL",
                    "confidence": min(0.85, 0.5 + momentum_surge["strength"]),
                    "timeframe": 8,
                    "reason": f"Momentum surge detected ({momentum_surge['direction']}, strength: {momentum_surge['strength']:.2f}) - enter at better price",
                    "reactive_factor": "momentum_surge"
                }
                reactive_signals.append(signal)
            
            # 3. VOLATILITY SPIKE DETECTION
            if volatility_5m > 0.003:  # Much more sensitive to volatility
                # Look for reversal opportunities in high volatility
                recent_highs = [candle["high"] for candle in candles_5m[-3:]]
                recent_lows = [candle["low"] for candle in candles_5m[-3:]]
                
                if current_price > max(recent_highs) * 0.998:  # Near recent high
                    signal = {
                        "type": "VOLATILITY_SPIKE",
                        "entry_price": current_price * 0.9995,
                        "side": "SELL",
                        "confidence": min(0.8, 0.4 + (volatility_5m * 20)),
                        "timeframe": 6,
                        "reason": f"Volatility spike - potential reversal from high (volatility: {volatility_5m:.3f})",
                        "reactive_factor": "volatility_spike"
                    }
                    reactive_signals.append(signal)
                elif current_price < min(recent_lows) * 1.002:  # Near recent low
                    signal = {
                        "type": "VOLATILITY_SPIKE",
                        "entry_price": current_price * 1.0005,
                        "side": "BUY",
                        "confidence": min(0.8, 0.4 + (volatility_5m * 20)),
                        "timeframe": 6,
                        "reason": f"Volatility spike - potential reversal from low (volatility: {volatility_5m:.3f})",
                        "reactive_factor": "volatility_spike"
                    }
                    reactive_signals.append(signal)
            
            # 4. VOLUME SPIKE DETECTION
            if volume_spike["detected"]:  # Only trigger when actual volume spike is detected
                # Volume spike often precedes significant moves
                if volume_spike["direction"] == "UP":
                    entry_price = current_price * 0.995  # Enter well below current for BUY
                else:
                    entry_price = current_price * 1.005  # Enter well above current for SELL
                    
                signal = {
                    "type": "PRICE_ACCELERATION",
                    "entry_price": entry_price,
                    "side": "BUY" if volume_spike["direction"] == "UP" else "SELL",
                    "confidence": min(0.75, 0.5 + volume_spike["strength"]),
                    "timeframe": 7,
                    "reason": f"Volume spike detected ({volume_spike['direction']}, strength: {volume_spike['strength']:.2f}) - enter at better price",
                    "reactive_factor": "volume_spike"
                }
                reactive_signals.append(signal)
            
            # Select best reactive signal
            if reactive_signals:
                # Get support/resistance for validation
                support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
                support_5m = support_resistance_5m.get("support", current_price * 0.99)
                resistance_5m = support_resistance_5m.get("resistance", current_price * 1.01)
                
                # Validate and fix entry prices for reactive signals
                for signal in reactive_signals:
                    signal = self._validate_entry_price(signal, current_price, support_5m, resistance_5m)
                
                best_signal = max(reactive_signals, key=lambda x: x["confidence"])
                
                return {
                    "has_prediction": True,
                    "prediction_mode": "REACTIVE",
                    "best_prediction": best_signal,
                    "all_predictions": reactive_signals,
                    "volatility_5m": volatility_5m,
                    "price_acceleration": price_acceleration,
                    "momentum_surge": momentum_surge,
                    "volume_spike": volume_spike,
                    "reactive_factors": [signal["reactive_factor"] for signal in reactive_signals]
                }
            else:
                return {"has_prediction": False, "reason": "No reactive signals detected"}
                
        except Exception as e:
            logger.error(f"Error building reactive prediction: {e}")
            return {"has_prediction": False, "reason": f"Reactive prediction error: {str(e)}"}
    
    def _build_predictive_prediction(self, binance_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Build predictive prediction for standard/low volatility markets - technical analysis based"""
        try:
            # Extract data from Binance analysis
            candles_5m = binance_analysis.get("candles_5m", [])
            candles_1h = binance_analysis.get("candles_1h", [])
            trend_5m = binance_analysis.get("trend_5m", {})
            trend_1h = binance_analysis.get("trend_1h", {})
            support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
            
            # Extract real-time Hyperliquid data for enhanced predictions
            hyperliquid_volume = binance_analysis.get("hyperliquid_volume", {})
            hyperliquid_rsi = binance_analysis.get("hyperliquid_rsi", {})
            
            # Get current market conditions from Hyperliquid
            current_rsi = hyperliquid_rsi.get("rsi_estimate", 50.0)
            is_oversold = hyperliquid_rsi.get("is_oversold", False)
            is_overbought = hyperliquid_rsi.get("is_overbought", False)
            
            liquidity_metrics = hyperliquid_volume.get("liquidity_metrics", {})
            total_depth = liquidity_metrics.get("total_depth", 0)
            depth_imbalance = liquidity_metrics.get("depth_imbalance", 0)
            
            logger.info(f"📊 Real-time Market Context: RSI={current_rsi:.1f}, Depth={total_depth:.1f}BTC, Imbalance={depth_imbalance*100:+.1f}%")
            
            if len(candles_5m) < 10 or len(candles_1h) < 10:
                return {"has_prediction": False, "reason": "Insufficient candlestick data"}
            
            support_5m = support_resistance_5m.get("support", 0)
            resistance_5m = support_resistance_5m.get("resistance", 0)
            range_size_5m = support_resistance_5m.get("range", 0)
            
            # Minimum range requirement - make it very lenient
            min_range_percentage = self.strategy_config["min_range_percentage"] * 0.1  # Reduce requirement by 90%
            if range_size_5m < current_price * min_range_percentage:
                # Instead of returning no prediction, try to generate basic predictions
                logger.info(f"Range small ({range_size_5m/current_price*100:.1f}%) but attempting basic predictions")
            
            # Calculate volatility for prediction confidence
            volatility_5m = self._get_volatility_5m(binance_analysis)
            volatility_1h = self._get_volatility_1h(binance_analysis)
            
            # Build predictions based on market conditions
            predictions = []
            
            # 1. BREAKOUT PREDICTIONS - Smart direction analysis
            if current_price > resistance_5m * 0.998:  # Near resistance
                # Analyze whether to expect breakout or reversion
                breakout_probability = self._analyze_breakout_probability(trend_1h, trend_5m, volatility_5m, range_size_5m)
                
                if breakout_probability > 0.6:  # High probability of breakout
                    # Predict potential breakout above resistance - wait for pullback to support
                    breakout_prediction = {
                        "type": "BREAKOUT_ABOVE",
                        "entry_price": support_5m * 1.001,  # Enter near support level, below current price
                        "side": "BUY",
                        "confidence": self._calculate_breakout_confidence(trend_1h, trend_5m, volatility_5m),
                        "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                        "reason": f"High probability breakout above ${resistance_5m:,.2f} - enter at support ${support_5m:,.2f}",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "breakout_probability": breakout_probability,
                        "current_price": current_price,
                        "prediction_timestamp": time.time()
                    }
                    predictions.append(breakout_prediction)
                else:  # Higher probability of reversion
                    # Predict potential reversion from resistance
                    reversion_prediction = {
                        "type": "REVERSION_FROM_RESISTANCE",
                        "entry_price": current_price,  # Enter at resistance level for immediate reversal
                        "side": "SELL",
                        "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m),
                        "timeframe": self._calculate_reversion_timeframe(volatility_5m),
                        "reason": f"High probability reversion from ${resistance_5m:,.2f} - enter at resistance",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "breakout_probability": breakout_probability
                    }
                    predictions.append(reversion_prediction)
            
            elif current_price < support_5m * 1.002:  # Near support
                # Analyze whether to expect breakout or reversion
                breakdown_probability = self._analyze_breakdown_probability(trend_1h, trend_5m, volatility_5m, range_size_5m)
                
                if breakdown_probability > 0.6:  # High probability of breakdown
                    # Predict potential breakout below support - wait for bounce to resistance
                    breakout_prediction = {
                        "type": "BREAKOUT_BELOW",
                        "entry_price": resistance_5m * 0.999,  # Enter near resistance level, above current price
                        "side": "SELL",
                        "confidence": self._calculate_breakout_confidence(trend_1h, trend_5m, volatility_5m),
                        "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                        "reason": f"High probability breakdown below ${support_5m:,.2f} - enter at resistance ${resistance_5m:,.2f}",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "breakdown_probability": breakdown_probability
                    }
                    predictions.append(breakout_prediction)
                else:  # Higher probability of bounce
                    # Predict potential reversion from support
                    reversion_prediction = {
                        "type": "REVERSION_FROM_SUPPORT",
                        "entry_price": support_5m * 1.0005,  # Slightly above support
                        "side": "BUY",
                        "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m),
                        "timeframe": self._calculate_reversion_timeframe(volatility_5m),
                        "reason": f"High probability bounce from ${support_5m:,.2f} - enter at support",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "breakdown_probability": breakdown_probability
                    }
                    predictions.append(reversion_prediction)
            
            # 2. MOMENTUM PREDICTIONS - Smart direction analysis
            if trend_1h.get("trend") == "UP" and trend_5m.get("trend") == "UP":
                # Strong upward momentum - analyze if it's sustainable
                momentum_strength = self._analyze_momentum_strength(trend_1h, trend_5m, volatility_5m)
                
                if momentum_strength > 0.7:  # Strong momentum
                    momentum_prediction = {
                        "type": "MOMENTUM_UP",
                        "entry_price": support_5m * 1.001,  # Enter at support level, well below current price
                        "side": "BUY",
                        "confidence": self._calculate_momentum_confidence(trend_1h, trend_5m, volatility_5m),
                        "timeframe": self._calculate_momentum_timeframe(volatility_5m),
                        "reason": f"Strong upward momentum (strength: {momentum_strength:.2f}) - enter at support ${support_5m:,.2f}",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "momentum_strength": momentum_strength
                    }
                    predictions.append(momentum_prediction)
                else:  # Weak momentum - might reverse
                    momentum_prediction = {
                        "type": "MOMENTUM_REVERSION",
                        "entry_price": current_price,  # Enter at current price for reversal
                        "side": "SELL",
                        "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m),
                        "timeframe": self._calculate_reversion_timeframe(volatility_5m),
                        "reason": f"Weak upward momentum (strength: {momentum_strength:.2f}) - expect reversal",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "momentum_strength": momentum_strength
                }
                predictions.append(momentum_prediction)
            
            elif trend_1h.get("trend") == "DOWN" and trend_5m.get("trend") == "DOWN":
                # Strong downward momentum - analyze if it's sustainable
                momentum_strength = self._analyze_momentum_strength(trend_1h, trend_5m, volatility_5m)
                
                if momentum_strength > 0.7:  # Strong momentum
                    momentum_prediction = {
                        "type": "MOMENTUM_DOWN",
                        "entry_price": resistance_5m * 0.999,  # Enter at resistance level, well above current price
                        "side": "SELL",
                        "confidence": self._calculate_momentum_confidence(trend_1h, trend_5m, volatility_5m),
                        "timeframe": self._calculate_momentum_timeframe(volatility_5m),
                        "reason": f"Strong downward momentum (strength: {momentum_strength:.2f}) - enter at resistance ${resistance_5m:,.2f}",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "momentum_strength": momentum_strength
                    }
                    predictions.append(momentum_prediction)
                else:  # Weak momentum - might reverse
                    momentum_prediction = {
                        "type": "MOMENTUM_REVERSION",
                        "entry_price": current_price,  # Enter at current price for reversal
                        "side": "BUY",
                        "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m),
                        "timeframe": self._calculate_reversion_timeframe(volatility_5m),
                        "reason": f"Weak downward momentum (strength: {momentum_strength:.2f}) - expect reversal",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "momentum_strength": momentum_strength
                }
                predictions.append(momentum_prediction)
            
            # 3. RANGE-BOUND ANALYSIS - When price is in the middle of range
            if support_5m < current_price < resistance_5m and range_size_5m > current_price * 0.01:
                # Price is in the middle of a significant range - analyze direction
                range_direction = self._analyze_range_direction(trend_1h, trend_5m, volatility_5m, current_price, support_5m, resistance_5m)
                
                if range_direction["direction"] == "UP":
                    range_prediction = {
                        "type": "RANGE_BREAKOUT_UP",
                        "entry_price": support_5m * 1.001,  # Enter at support level, well below current price
                        "side": "BUY",
                        "confidence": range_direction["confidence"],
                        "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                        "reason": f"Range analysis suggests upward move (confidence: {range_direction['confidence']:.2f}) - enter at support ${support_5m:,.2f}",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "range_position": (current_price - support_5m) / (resistance_5m - support_5m)
                    }
                    predictions.append(range_prediction)
                else:
                    range_prediction = {
                        "type": "RANGE_BREAKOUT_DOWN",
                        "entry_price": resistance_5m * 0.999,  # Enter at resistance level, well above current price
                        "side": "SELL",
                        "confidence": range_direction["confidence"],
                        "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                        "reason": f"Range analysis suggests downward move (confidence: {range_direction['confidence']:.2f}) - enter at resistance ${resistance_5m:,.2f}",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "range_position": (current_price - support_5m) / (resistance_5m - support_5m)
                    }
                    predictions.append(range_prediction)
            
            # Select best prediction based on confidence
            if predictions:
                # Validate and fix entry prices to ensure they're logical
                for prediction in predictions:
                    prediction = self._validate_entry_price(prediction, current_price, support_5m, resistance_5m)
                
                best_prediction = max(predictions, key=lambda x: x["confidence"])
                
                return {
                    "has_prediction": True,
                    "prediction_mode": "PREDICTIVE",
                    "best_prediction": best_prediction,
                    "all_predictions": predictions,
                    "volatility_5m": volatility_5m,
                    "volatility_1h": volatility_1h,
                    "range_size": range_size_5m,
                    "support": support_5m,
                    "resistance": resistance_5m
                }
            else:
                # Generate basic predictions even with small ranges
                basic_predictions = self._generate_basic_predictions(current_price, support_5m, resistance_5m, trend_5m, trend_1h, volatility_5m)
                if basic_predictions:
                    return {
                        "has_prediction": True,
                        "prediction_mode": "BASIC",
                        "best_prediction": basic_predictions[0],
                        "all_predictions": basic_predictions,
                        "volatility_5m": volatility_5m,
                        "volatility_1h": volatility_1h,
                        "range_size": range_size_5m,
                        "support": support_5m,
                        "resistance": resistance_5m
                    }
                else:
                    return {"has_prediction": False, "reason": "No valid predictions found"}
                
        except Exception as e:
            logger.error(f"Error building predictive prediction: {e}")
            return {"has_prediction": False, "reason": f"Predictive prediction error: {str(e)}"}
    
    def _generate_basic_predictions(self, current_price: float, support: float, resistance: float, trend_5m: Dict, trend_1h: Dict, volatility: float) -> List[Dict]:
        """Generate basic predictions even with small ranges - focus on current price action"""
        try:
            predictions = []
            
            # 1. CURRENT PRICE POSITION ANALYSIS
            # Check if price is near key levels (like 112,500 support)
            key_levels = self._identify_key_levels(current_price)
            
            for level in key_levels:
                distance_to_level = abs(current_price - level["price"]) / current_price
                
                if distance_to_level < 0.002:  # Within 0.2% of key level
                    if level["type"] == "SUPPORT" and current_price > level["price"]:
                        # Price approaching support from above - potential bounce
                        prediction = {
                            "type": "SUPPORT_BOUNCE",
                            "entry_price": level["price"] * 1.001,  # Just above support
                            "side": "BUY",
                            "confidence": 0.65 + (level["strength"] * 0.2),
                            "timeframe": 15,
                            "reason": f"Approaching key support at ${level['price']:,.0f} - expect bounce",
                            "support": level["price"],
                            "resistance": resistance,
                            "prediction_mode": "KEY_LEVEL_ANALYSIS",
                            "key_level": level
                        }
                        predictions.append(prediction)
                        
                    elif level["type"] == "RESISTANCE" and current_price < level["price"]:
                        # Price approaching resistance from below - potential rejection
                        prediction = {
                            "type": "RESISTANCE_REJECTION",
                            "entry_price": level["price"] * 0.999,  # Just below resistance
                            "side": "SELL",
                            "confidence": 0.65 + (level["strength"] * 0.2),
                            "timeframe": 15,
                            "reason": f"Approaching key resistance at ${level['price']:,.0f} - expect rejection",
                            "support": support,
                            "resistance": level["price"],
                            "prediction_mode": "KEY_LEVEL_ANALYSIS",
                            "key_level": level
                        }
                        predictions.append(prediction)
             
            # 2. PRICE MOMENTUM ANALYSIS (even with small ranges)
            if trend_5m.get("trend") == "UP" and trend_1h.get("trend") == "UP":
                # Both timeframes showing upward momentum
                prediction = {
                    "type": "MOMENTUM_CONTINUATION",
                    "entry_price": current_price * 0.998,  # Enter slightly below current
                    "side": "BUY",
                    "confidence": 0.6 + (trend_5m.get("strength", 0.5) * 0.2),
                    "timeframe": 10,
                    "reason": f"Strong upward momentum on both 5m and 1h timeframes",
                    "support": support,
                    "resistance": resistance,
                    "prediction_mode": "MOMENTUM_ANALYSIS"
                }
                predictions.append(prediction)
                 
            elif trend_5m.get("trend") == "DOWN" and trend_1h.get("trend") == "DOWN":
                # Both timeframes showing downward momentum
                prediction = {
                    "type": "MOMENTUM_CONTINUATION",
                    "entry_price": current_price * 1.002,  # Enter slightly above current
                    "side": "SELL",
                    "confidence": 0.6 + (trend_5m.get("strength", 0.5) * 0.2),
                    "timeframe": 10,
                    "reason": f"Strong downward momentum on both 5m and 1h timeframes",
                    "support": support,
                    "resistance": resistance,
                    "prediction_mode": "MOMENTUM_ANALYSIS"
                }
                predictions.append(prediction)
             
            # 3. RANGE POSITION ANALYSIS
            if support > 0 and resistance > 0:
                range_size = resistance - support
                position_in_range = (current_price - support) / range_size if range_size > 0 else 0.5
                 
                if position_in_range < 0.3:  # Near bottom of range
                    prediction = {
                        "type": "RANGE_BOTTOM_BOUNCE",
                        "entry_price": support * 1.001,
                        "side": "BUY",
                        "confidence": 0.55,
                        "timeframe": 12,
                        "reason": f"Near bottom of range (${support:,.0f} - ${resistance:,.0f}) - expect bounce",
                        "support": support,
                        "resistance": resistance,
                        "prediction_mode": "RANGE_ANALYSIS",
                        "position_in_range": position_in_range
                    }
                    predictions.append(prediction)
                     
                elif position_in_range > 0.7:  # Near top of range
                    prediction = {
                        "type": "RANGE_TOP_REJECTION",
                        "entry_price": resistance * 0.999,
                        "side": "SELL",
                        "confidence": 0.55,
                        "timeframe": 12,
                        "reason": f"Near top of range (${support:,.0f} - ${resistance:,.0f}) - expect rejection",
                        "support": support,
                        "resistance": resistance,
                        "prediction_mode": "RANGE_ANALYSIS",
                        "position_in_range": position_in_range
                    }
                    predictions.append(prediction)
             
            # 4. VOLATILITY-BASED PREDICTIONS
            if volatility > 0.002:  # Lower threshold for volatility predictions
                # In high volatility, look for reversal opportunities
                if trend_5m.get("trend") == "UP":
                    prediction = {
                        "type": "VOLATILITY_REVERSAL",
                        "entry_price": current_price * 1.001,
                        "side": "SELL",
                        "confidence": 0.5,
                        "timeframe": 8,
                        "reason": f"High volatility ({volatility:.3f}) - expect reversal from upward move",
                        "support": support,
                        "resistance": resistance,
                        "prediction_mode": "VOLATILITY_ANALYSIS"
                    }
                    predictions.append(prediction)
                else:
                    prediction = {
                        "type": "VOLATILITY_REVERSAL",
                        "entry_price": current_price * 0.999,
                        "side": "BUY",
                        "confidence": 0.5,
                        "timeframe": 8,
                        "reason": f"High volatility ({volatility:.3f}) - expect reversal from downward move",
                        "support": support,
                        "resistance": resistance,
                        "prediction_mode": "VOLATILITY_ANALYSIS"
                    }
                    predictions.append(prediction)
             
            # 5. FALLBACK PREDICTION - Always provide at least one prediction
            if not predictions:
                # Generate a simple prediction based on current trend
                if trend_5m.get("trend") == "UP":
                    prediction = {
                        "type": "TREND_FOLLOWING",
                        "entry_price": current_price * 0.999,
                        "side": "BUY",
                        "confidence": 0.4,
                        "timeframe": 15,
                        "reason": f"Following 5m uptrend - enter below current price",
                        "support": support,
                        "resistance": resistance,
                        "prediction_mode": "TREND_FOLLOWING"
                    }
                else:
                    prediction = {
                        "type": "TREND_FOLLOWING",
                        "entry_price": current_price * 1.001,
                        "side": "SELL",
                        "confidence": 0.4,
                        "timeframe": 15,
                        "reason": f"Following 5m downtrend - enter above current price",
                        "support": support,
                        "resistance": resistance,
                        "prediction_mode": "TREND_FOLLOWING"
                    }
                predictions.append(prediction)
             
            return predictions
             
        except Exception as e:
            logger.error(f"Error generating basic predictions: {e}")
            return []
    
    def _identify_key_levels(self, current_price: float) -> List[Dict]:
        """Identify key psychological and technical levels near current price"""
        try:
            levels = []
             
            # Major psychological levels (round numbers)
            major_levels = [110000, 111000, 112000, 113000, 114000, 115000, 116000, 117000, 118000, 119000, 120000]
             
            for level in major_levels:
                distance = abs(current_price - level) / current_price
                if distance < 0.02:  # Within 2% of major level
                    if current_price > level:
                        levels.append({
                            "price": level,
                            "type": "SUPPORT",
                            "strength": 0.8,
                            "description": f"Major support at ${level:,}"
                        })
                    else:
                        levels.append({
                            "price": level,
                            "type": "RESISTANCE", 
                            "strength": 0.8,
                            "description": f"Major resistance at ${level:,}"
                        })
             
            # Mid-levels (like 112,500)
            mid_levels = [110500, 111500, 112500, 113500, 114500, 115500, 116500, 117500, 118500, 119500]
             
            for level in mid_levels:
                distance = abs(current_price - level) / current_price
                if distance < 0.015:  # Within 1.5% of mid-level
                    if current_price > level:
                        levels.append({
                            "price": level,
                            "type": "SUPPORT",
                            "strength": 0.7,
                            "description": f"Mid-level support at ${level:,}"
                        })
                    else:
                        levels.append({
                            "price": level,
                            "type": "RESISTANCE",
                            "strength": 0.7,
                            "description": f"Mid-level resistance at ${level:,}"
                        })
             
            # Fibonacci levels (if we have recent high/low)
            # For now, use approximate levels based on current price
            fib_levels = [
                current_price * 0.95,  # 0.236 retracement
                current_price * 0.97,  # 0.382 retracement
                current_price * 1.03,  # 0.618 extension
                current_price * 1.05   # 0.786 extension
            ]
             
            for i, level in enumerate(fib_levels):
                distance = abs(current_price - level) / current_price
                if distance < 0.01:  # Within 1% of Fibonacci level
                    fib_names = ["0.236", "0.382", "0.618", "0.786"]
                    if current_price > level:
                        levels.append({
                            "price": level,
                            "type": "SUPPORT",
                            "strength": 0.6,
                            "description": f"Fibonacci {fib_names[i]} support at ${level:,.0f}"
                        })
                    else:
                        levels.append({
                            "price": level,
                            "type": "RESISTANCE",
                            "strength": 0.6,
                            "description": f"Fibonacci {fib_names[i]} resistance at ${level:,.0f}"
                        })
             
            return levels
             
        except Exception as e:
            logger.error(f"Error identifying key levels: {e}")
            return []
    
    def _validate_entry_price(self, prediction: Dict, current_price: float, support: float, resistance: float) -> Dict:
        """Validate and fix entry prices to ensure they're logical"""
        try:
            entry_price = prediction.get("entry_price", 0)
            side = prediction.get("side", "UNKNOWN")
            
            # For BUY orders: entry price should be below current price
            if side == "BUY" and entry_price >= current_price:
                # Set entry price to support level or 0.5% below current
                new_entry = min(support * 1.001, current_price * 0.995)
                prediction["entry_price"] = new_entry
                prediction["reason"] += f" (adjusted entry to ${new_entry:,.2f})"
                logger.warning(f"Fixed BUY entry price from ${entry_price:,.2f} to ${new_entry:,.2f} (current: ${current_price:,.2f})")
            
            # For SELL orders: entry price should be above current price
            elif side == "SELL" and entry_price <= current_price:
                # Set entry price to resistance level or 0.5% above current
                new_entry = max(resistance * 0.999, current_price * 1.005)
                prediction["entry_price"] = new_entry
                prediction["reason"] += f" (adjusted entry to ${new_entry:,.2f})"
                logger.warning(f"Fixed SELL entry price from ${entry_price:,.2f} to ${new_entry:,.2f} (current: ${current_price:,.2f})")
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error validating entry price: {e}")
            return prediction
    
    def _calculate_price_acceleration(self, candles_5m: List) -> float:
        """Calculate price acceleration (rate of change of price changes)"""
        try:
            if len(candles_5m) < 4:
                return 0.0
            
            # Calculate price changes
            prices = [candle["close"] for candle in candles_5m[-4:]]
            price_changes = []
            
            for i in range(1, len(prices)):
                change = (prices[i] - prices[i-1]) / prices[i-1]
                price_changes.append(change)
            
            # Calculate acceleration (change in rate of change)
            if len(price_changes) >= 2:
                acceleration = abs(price_changes[-1] - price_changes[-2])
                return acceleration
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating price acceleration: {e}")
            return 0.0
    
    def _detect_momentum_surge(self, candles_5m: List, trend_5m: Dict) -> Dict[str, Any]:
        """Detect momentum surge in recent candles"""
        try:
            if len(candles_5m) < 5:
                return {"detected": False, "direction": "UNKNOWN", "strength": 0.0}
            
            # Calculate recent momentum
            recent_prices = [candle["close"] for candle in candles_5m[-5:]]
            recent_volumes = [candle["volume"] for candle in candles_5m[-5:]]
            
            # Calculate price momentum
            price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            # Calculate volume momentum
            avg_volume = sum(recent_volumes[:-1]) / len(recent_volumes[:-1])
            current_volume = recent_volumes[-1]
            volume_surge = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Detect surge conditions
            if abs(price_momentum) > 0.002 and volume_surge > 1.2:  # 0.2% price move + 20% volume increase (much more sensitive)
                direction = "UP" if price_momentum > 0 else "DOWN"
                strength = min(1.0, abs(price_momentum) * 100 + (volume_surge - 1.0) * 0.5)
                
                return {
                    "detected": True,
                    "direction": direction,
                    "strength": strength,
                    "price_momentum": price_momentum,
                    "volume_surge": volume_surge
                }
            else:
                return {"detected": False, "direction": "UNKNOWN", "strength": 0.0}
                
        except Exception as e:
            logger.error(f"Error detecting momentum surge: {e}")
            return {"detected": False, "direction": "UNKNOWN", "strength": 0.0}
    
    def _detect_volume_spike(self, candles_5m: List) -> Dict[str, Any]:
        """Detect volume spike in recent candles"""
        try:
            if len(candles_5m) < 6:
                return {"detected": False, "direction": "UNKNOWN", "strength": 0.0}
            
            # Calculate recent volumes
            recent_volumes = [candle["volume"] for candle in candles_5m[-6:]]
            recent_prices = [candle["close"] for candle in candles_5m[-6:]]
            
            # Calculate average volume (excluding current)
            avg_volume = sum(recent_volumes[:-1]) / len(recent_volumes[:-1])
            current_volume = recent_volumes[-1]
            
            # Detect volume spike
            if current_volume > avg_volume * 1.3:  # 30% increase (much more sensitive)
                # Determine direction based on price action
                price_change = (recent_prices[-1] - recent_prices[-2]) / recent_prices[-2]
                direction = "UP" if price_change > 0 else "DOWN"
                strength = min(1.0, (current_volume / avg_volume - 1.0) * 0.5)
                
                return {
                    "detected": True,
                    "direction": direction,
                    "strength": strength,
                    "volume_ratio": current_volume / avg_volume,
                    "price_change": price_change
                }
            else:
                return {"detected": False, "direction": "UNKNOWN", "strength": 0.0}
                
        except Exception as e:
            logger.error(f"Error detecting volume spike: {e}")
            return {"detected": False, "direction": "UNKNOWN", "strength": 0.0}
    
    def _get_volatility_5m(self, binance_analysis: Dict[str, Any]) -> float:
        """Calculate 5-minute volatility"""
        try:
            candles_5m = binance_analysis.get("candles_5m", [])
            if len(candles_5m) < 10:
                return 0.003  # Default volatility
            
            # Calculate price changes
            price_changes = []
            for i in range(1, min(10, len(candles_5m))):
                # Access close price using dictionary key, not array index
                prev_close = candles_5m[i-1]["close"]
                curr_close = candles_5m[i]["close"]
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
                # Access close price using dictionary key, not array index
                prev_close = candles_1h[i-1]["close"]
                curr_close = candles_1h[i]["close"]
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
    
    def _analyze_breakout_probability(self, trend_1h: Dict, trend_5m: Dict, volatility: float, range_size: float) -> float:
        """Analyze probability of breakout vs reversion from resistance"""
        base_probability = 0.5
        
        # Trend alignment - strong trends favor breakouts
        if trend_1h.get("trend") == "UP" and trend_5m.get("trend") == "UP":
            base_probability += 0.2
        elif trend_1h.get("trend") == "DOWN" and trend_5m.get("trend") == "DOWN":
            base_probability -= 0.2
        
        # Trend strength
        trend_strength_1h = trend_1h.get("strength", 0.5)
        trend_strength_5m = trend_5m.get("strength", 0.5)
        avg_strength = (trend_strength_1h + trend_strength_5m) / 2
        base_probability += (avg_strength - 0.5) * 0.3
        
        # Volatility - moderate volatility favors breakouts
        if 0.002 < volatility < 0.005:
            base_probability += 0.1
        elif volatility > 0.008:
            base_probability -= 0.1
        
        # Range size - larger ranges favor breakouts
        range_percentage = range_size / 114000  # Assuming current BTC price
        if range_percentage > 0.015:
            base_probability += 0.1
        elif range_percentage < 0.005:
            base_probability -= 0.1
        
        return min(0.95, max(0.05, base_probability))
    
    def _analyze_breakdown_probability(self, trend_1h: Dict, trend_5m: Dict, volatility: float, range_size: float) -> float:
        """Analyze probability of breakdown vs bounce from support"""
        base_probability = 0.5
        
        # Trend alignment - strong trends favor breakdowns
        if trend_1h.get("trend") == "DOWN" and trend_5m.get("trend") == "DOWN":
            base_probability += 0.2
        elif trend_1h.get("trend") == "UP" and trend_5m.get("trend") == "UP":
            base_probability -= 0.2
        
        # Trend strength
        trend_strength_1h = trend_1h.get("strength", 0.5)
        trend_strength_5m = trend_5m.get("strength", 0.5)
        avg_strength = (trend_strength_1h + trend_strength_5m) / 2
        base_probability += (avg_strength - 0.5) * 0.3
        
        # Volatility - moderate volatility favors breakdowns
        if 0.002 < volatility < 0.005:
            base_probability += 0.1
        elif volatility > 0.008:
            base_probability -= 0.1
        
        # Range size - larger ranges favor breakdowns
        range_percentage = range_size / 114000  # Assuming current BTC price
        if range_percentage > 0.015:
            base_probability += 0.1
        elif range_percentage < 0.005:
            base_probability -= 0.1
        
        return min(0.95, max(0.05, base_probability))
    
    def _analyze_momentum_strength(self, trend_1h: Dict, trend_5m: Dict, volatility: float) -> float:
        """Analyze the strength and sustainability of momentum"""
        base_strength = 0.5
        
        # Trend alignment strength
        if trend_1h.get("trend") == trend_5m.get("trend"):
            base_strength += 0.2
        
        # Individual trend strengths
        trend_strength_1h = trend_1h.get("strength", 0.5)
        trend_strength_5m = trend_5m.get("strength", 0.5)
        avg_strength = (trend_strength_1h + trend_strength_5m) / 2
        base_strength += avg_strength * 0.2
        
        # Volatility adjustment - moderate volatility is good for momentum
        if 0.002 < volatility < 0.006:
            base_strength += 0.1
        elif volatility > 0.008:
            base_strength -= 0.1
        
        return min(1.0, max(0.0, base_strength))
    
    def _analyze_range_direction(self, trend_1h: Dict, trend_5m: Dict, volatility: float, current_price: float, support: float, resistance: float) -> Dict[str, Any]:
        """Analyze which direction price is likely to break from a range"""
        # Calculate position within range
        range_size = resistance - support
        if range_size <= 0:
            return {"direction": "NEUTRAL", "confidence": 0.5}
        
        position_in_range = (current_price - support) / range_size
        
        # Base confidence starts at 0.5
        confidence = 0.5
        
        # Trend analysis
        if trend_1h.get("trend") == "UP" and trend_5m.get("trend") == "UP":
            confidence += 0.2
            direction = "UP"
        elif trend_1h.get("trend") == "DOWN" and trend_5m.get("trend") == "DOWN":
            confidence += 0.2
            direction = "DOWN"
        else:
            # Mixed trends - use position in range
            if position_in_range > 0.6:  # Closer to resistance
                direction = "DOWN"
                confidence += 0.1
            elif position_in_range < 0.4:  # Closer to support
                direction = "UP"
                confidence += 0.1
            else:
                direction = "NEUTRAL"
        
        # Position in range adjustment
        if direction == "UP" and position_in_range < 0.3:
            confidence += 0.1  # Near support, good for upward break
        elif direction == "DOWN" and position_in_range > 0.7:
            confidence += 0.1  # Near resistance, good for downward break
        
        # Volatility adjustment
        if 0.002 < volatility < 0.006:
            confidence += 0.05  # Moderate volatility is good for breakouts
        elif volatility > 0.008:
            confidence -= 0.05  # High volatility can be unpredictable
        
        return {
            "direction": direction,
            "confidence": min(0.95, max(0.1, confidence)),
            "position_in_range": position_in_range
        }
    
    def is_prediction_valid(self, prediction: Dict[str, Any], current_price: float) -> bool:
        """Check if prediction is still valid given current price"""
        entry_price = prediction["entry_price"]
        price_diff = abs(current_price - entry_price) / current_price
        
        # Prediction is valid if price is within 0.5% of entry
        return price_diff < 0.005
    
    def calculate_prediction_win_probability(self, prediction: Dict[str, Any], prediction_analysis: Dict[str, Any]) -> float:
        """Calculate win probability for a prediction"""
        base_probability = prediction["confidence"]
        
        # Adjust based on prediction mode
        prediction_mode = prediction_analysis.get("prediction_mode", "PREDICTIVE")
        
        if prediction_mode == "REACTIVE":
            # Reactive predictions have different probability calculations
            reactive_factor = prediction.get("reactive_factor", "")
            
            if reactive_factor == "price_acceleration":
                base_probability += 0.05  # Higher probability for acceleration
            elif reactive_factor == "momentum_surge":
                base_probability += 0.03  # Good probability for momentum
            elif reactive_factor == "volume_spike":
                base_probability += 0.02  # Moderate probability for volume
            elif reactive_factor == "volatility_spike":
                base_probability -= 0.02  # Lower probability for volatility spikes
        
        # Adjust based on volatility
        volatility_5m = prediction_analysis.get("volatility_5m", 0.003)
        if volatility_5m < 0.002:
            base_probability += 0.05  # More predictable in low volatility
        elif volatility_5m > 0.005:
            base_probability -= 0.05  # Less predictable in high volatility
        
        # Adjust based on range size (for predictive mode)
        if prediction_mode == "PREDICTIVE":
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
            prediction_mode = prediction_analysis.get("prediction_mode", "PREDICTIVE")
            
            # Check if prediction is still valid
            if not self.is_prediction_valid(prediction, current_price):
                return {"should_place_order": False, "reason": "Prediction no longer valid"}
            
            # Calculate win probability
            win_probability = self.calculate_prediction_win_probability(prediction, prediction_analysis)
            
            # Different confidence thresholds for different modes
            if prediction_mode == "REACTIVE":
                confidence_threshold = 0.5  # Lower threshold for reactive trades
            else:
                confidence_threshold = self.strategy_config.get("confidence_threshold", 0.6)
            
            if prediction["confidence"] < confidence_threshold:
                return {"should_place_order": False, "reason": f"Confidence too low ({prediction['confidence']:.2f} < {confidence_threshold})"}
            
            # Calculate target and stop prices
            entry_price = prediction["entry_price"]
            side = prediction["side"]
            
            # Different parameters for different modes
            if prediction_mode == "REACTIVE":
                # Reactive trades: tighter stops, smaller targets
                profit_target_pct = self.strategy_config.get("profit_target", 0.01) * 0.5  # Half the normal target
                stop_loss_pct = self.strategy_config.get("stop_loss", 0.005) * 0.7  # Tighter stop
            else:
                # Predictive trades: normal parameters
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
                "prediction_mode": prediction_mode,
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
