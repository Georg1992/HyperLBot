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
        
        # Initialize confidence smoothing variables for stability
        self._last_reversion_confidence = 0.5
        self._last_momentum_confidence = 0.6
        self._last_breakout_confidence = 0.5
        
        logger.info("🎯 Enhanced Prediction Engine initialized with conservative confidence system")
    
    def _add_prediction_metadata(self, prediction: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Add standard metadata to all predictions"""
        prediction["current_price"] = current_price
        prediction["prediction_timestamp"] = time.time()
        prediction["prediction_datetime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return prediction
    
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
            
            # Get real-time Hyperliquid data for enhanced reactive predictions
            hyperliquid_volume = binance_analysis.get("hyperliquid_volume", {})
            hyperliquid_rsi = binance_analysis.get("hyperliquid_rsi", {})
            
            current_rsi = hyperliquid_rsi.get("rsi", 50.0)  # Use proper RSI calculation
            liquidity_metrics = hyperliquid_volume.get("liquidity_metrics", {})
            total_depth = liquidity_metrics.get("total_depth", 0)
            depth_imbalance = liquidity_metrics.get("depth_imbalance", 0)
            
            # Enhanced volume spike detection with Hyperliquid real-time data
            hyperliquid_volume_spike = self._detect_hyperliquid_volume_activity(liquidity_metrics, depth_imbalance)
            
            logger.info(f"⚡ Reactive Mode: RSI={current_rsi:.1f}, Depth={total_depth:.1f}BTC, Yahoo Vol Spike={volume_spike['detected']}, HL Vol Activity={hyperliquid_volume_spike['detected']}")
            
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
            
            # 5. HYPERLIQUID REAL-TIME VOLUME ACTIVITY DETECTION
            if hyperliquid_volume_spike["detected"]:
                # Real-time volume activity from orderbook depth
                if hyperliquid_volume_spike["direction"] == "DOWN":
                    entry_price = current_price * 1.002  # Enter above current for SELL (selling pressure)
                    side = "SELL"
                elif hyperliquid_volume_spike["direction"] == "UP":
                    entry_price = current_price * 0.998  # Enter below current for BUY (buying pressure)
                    side = "BUY"
                else:  # NEUTRAL - high activity but balanced
                    # Use RSI to determine direction
                    if current_rsi > 55:
                        entry_price = current_price * 1.001
                        side = "SELL"
                    else:
                        entry_price = current_price * 0.999
                        side = "BUY"
                
                signal = {
                    "type": "HYPERLIQUID_VOLUME_ACTIVITY",
                    "entry_price": entry_price,
                    "side": side,
                    "confidence": min(0.85, 0.6 + hyperliquid_volume_spike["strength"]),
                    "timeframe": 5,
                    "reason": f"High orderbook activity detected ({hyperliquid_volume_spike['direction']}, depth: {hyperliquid_volume_spike['total_depth']:.1f}BTC, imbalance: {hyperliquid_volume_spike['imbalance']*100:+.1f}%)",
                    "reactive_factor": "hyperliquid_volume",
                    "rsi_context": current_rsi,
                    "orderbook_depth": hyperliquid_volume_spike["total_depth"],
                    "orderbook_imbalance": hyperliquid_volume_spike["imbalance"]
                }
                reactive_signals.append(signal)
            
            # Select best reactive signal
            if reactive_signals:
                # Get support/resistance for validation
                support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
                support_5m = support_resistance_5m.get("support", current_price * 0.99)
                resistance_5m = support_resistance_5m.get("resistance", current_price * 1.01)
                
                # Validate and fix entry prices for reactive signals
                for i, signal in enumerate(reactive_signals):
                    signal = self._validate_entry_price(signal, current_price, support_5m, resistance_5m, candles_5m)
                    # Add prediction metadata to all signals
                    reactive_signals[i] = self._add_prediction_metadata(signal, current_price)
                
                best_signal = max(reactive_signals, key=lambda x: x["confidence"])
                
                # FINAL VALIDATION: Ensure best signal has valid entry price
                best_signal = self._validate_entry_price(best_signal, current_price, support_5m, resistance_5m, candles_5m)
                
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
            # Extract data from enhanced multi-timeframe analysis
            candles_1m = binance_analysis.get("candles_1m", [])  # 2h immediate momentum
            candles_5m = binance_analysis.get("candles_5m", [])  # 5h core analysis
            candles_1h = binance_analysis.get("candles_1h", [])  # 3.5d daily context
            candles_1d = binance_analysis.get("candles_1d", [])  # 6w weekly/monthly context
            trend_5m = binance_analysis.get("trend_5m", {})      # Short-term trend
            trend_1h = binance_analysis.get("trend_1h", {})      # Daily trend
            trend_1d = binance_analysis.get("trend_1d", {})      # Weekly/monthly trend
            support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
            
            # Extract real-time Hyperliquid data for enhanced predictions
            hyperliquid_volume = binance_analysis.get("hyperliquid_volume", {})
            hyperliquid_rsi = binance_analysis.get("hyperliquid_rsi", {})
            
            # Get current market conditions from Hyperliquid (corrected RSI)
            current_rsi = hyperliquid_rsi.get("rsi", 50.0)  # Use proper RSI calculation
            is_oversold = hyperliquid_rsi.get("is_oversold", False)
            is_overbought = hyperliquid_rsi.get("is_overbought", False)
            
            liquidity_metrics = hyperliquid_volume.get("liquidity_metrics", {})
            total_depth = liquidity_metrics.get("total_depth", 0)
            depth_imbalance = liquidity_metrics.get("depth_imbalance", 0)
            
            logger.info(f"📊 Multi-timeframe Context: RSI={current_rsi:.1f}, 5m={trend_5m.get('trend','?')}, 1h={trend_1h.get('trend','?')}, 1d={trend_1d.get('trend','?')}, Depth={total_depth:.1f}BTC")
            
            # Enhanced data validation for multi-timeframe analysis (increased for 20-period RSI)
            if len(candles_5m) < 45 or len(candles_1h) < 30 or len(candles_1d) < 20:
                return {"has_prediction": False, "reason": f"Insufficient candlestick data - need 45+ 5m ({len(candles_5m)}), 30+ 1h ({len(candles_1h)}), 20+ 1d ({len(candles_1d)}) candles for reliable analysis"}
            
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
                        "entry_price": min(support_5m * 0.9995, current_price * 0.999),  # Below support AND below current price
                        "side": "BUY",
                        "confidence": self._calculate_breakout_confidence(trend_1h, trend_5m, volatility_5m, current_rsi, total_depth, depth_imbalance, trend_1d),
                        "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                        "reason": f"High probability breakout above ${resistance_5m:,.2f} - enter below support ${support_5m:,.2f}",
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
                        "entry_price": resistance_5m * 1.001,  # Enter slightly above resistance for SELL order
                        "side": "SELL",
                        "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m, current_rsi, total_depth, depth_imbalance, trend_1d),
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
                        "confidence": self._calculate_breakout_confidence(trend_1h, trend_5m, volatility_5m, current_rsi, total_depth, depth_imbalance, trend_1d),
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
                        "entry_price": min(support_5m * 0.9995, current_price * 0.999),  # Below support AND below current price
                        "side": "BUY",
                        "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m, current_rsi, total_depth, depth_imbalance, trend_1d),
                        "timeframe": self._calculate_reversion_timeframe(volatility_5m),
                        "reason": f"High probability bounce from ${support_5m:,.2f} - enter below support",
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
                        "entry_price": min(support_5m * 0.9995, current_price * 0.999),  # Below support AND below current price
                        "side": "BUY",
                        "confidence": self._calculate_momentum_confidence(trend_1h, trend_5m, volatility_5m, current_rsi, total_depth, depth_imbalance),
                        "timeframe": self._calculate_momentum_timeframe(volatility_5m),
                        "reason": f"Strong upward momentum (strength: {momentum_strength:.2f}) - enter below support ${support_5m:,.2f}",
                        "support": support_5m,
                        "resistance": resistance_5m,
                        "prediction_mode": "TECHNICAL_ANALYSIS",
                        "momentum_strength": momentum_strength
                    }
                    predictions.append(momentum_prediction)
                else:  # Weak momentum - might reverse
                    momentum_prediction = {
                        "type": "MOMENTUM_REVERSION",
                        "entry_price": current_price * 1.001,  # Enter slightly above current price for SELL order
                        "side": "SELL",
                        "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m, current_rsi, total_depth, depth_imbalance, trend_1d),
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
                        "confidence": self._calculate_momentum_confidence(trend_1h, trend_5m, volatility_5m, current_rsi, total_depth, depth_imbalance),
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
                        "entry_price": current_price * 0.999,  # Enter slightly below current price for BUY order
                        "side": "BUY",
                        "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m, current_rsi, total_depth, depth_imbalance, trend_1d),
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
                        "entry_price": min(support_5m * 0.9995, current_price * 0.999),  # Below support AND below current price
                        "side": "BUY",
                        "confidence": range_direction["confidence"],
                        "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                        "reason": f"Range analysis suggests upward move (confidence: {range_direction['confidence']:.2f}) - enter below support ${support_5m:,.2f}",
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
                for i, prediction in enumerate(predictions):
                    prediction = self._validate_entry_price(prediction, current_price, support_5m, resistance_5m, candles_5m)
                    # Add prediction metadata (RSI and volume data only for internal use, not display)
                    predictions[i] = self._add_prediction_metadata(prediction, current_price)
                
                best_prediction = max(predictions, key=lambda x: x["confidence"])
                
                # FINAL VALIDATION: Ensure best prediction has valid entry price
                best_prediction = self._validate_entry_price(best_prediction, current_price, support_5m, resistance_5m, candles_5m)
                
                # Ensure best prediction has metadata (safety check)
                if "current_price" not in best_prediction:
                    best_prediction = self._add_prediction_metadata(best_prediction, current_price)
                
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
                    # Validate and fix entry prices to ensure they're logical
                    for i, prediction in enumerate(basic_predictions):
                        prediction = self._validate_entry_price(prediction, current_price, support_5m, resistance_5m, candles_5m)
                        # Add prediction metadata
                        basic_predictions[i] = self._add_prediction_metadata(prediction, current_price)
                    
                    # FINAL VALIDATION: Ensure best prediction has valid entry price
                    best_basic = self._validate_entry_price(basic_predictions[0], current_price, support_5m, resistance_5m, candles_5m)
                    
                    # Ensure best prediction has metadata (safety check)
                    if "current_price" not in best_basic:
                        best_basic = self._add_prediction_metadata(best_basic, current_price)
                    
                    return {
                        "has_prediction": True,
                        "prediction_mode": "BASIC",
                        "best_prediction": best_basic,
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
             
            # Add metadata to all predictions before returning
            for i, prediction in enumerate(predictions):
                predictions[i] = self._add_prediction_metadata(prediction, current_price)
             
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
    
    def _validate_entry_price(self, prediction: Dict, current_price: float, support: float, resistance: float, candles_5m: List = None) -> Dict:
        """Smart entry price validation that allows equal prices when price is moving toward entry level"""
        try:
            entry_price = prediction.get("entry_price", 0)
            side = prediction.get("side", "UNKNOWN")
            pred_type = prediction.get("type", "UNKNOWN")
            
            # Additional validation: ensure entry price is reasonable
            if entry_price <= 0:
                logger.error(f"🚨 Invalid entry price: ${entry_price:,.2f} for {pred_type}")
                if side == "BUY":
                    prediction["entry_price"] = current_price * 0.997
                else:
                    prediction["entry_price"] = current_price * 1.003
                return prediction
            
            # SMART VALIDATION: Check if price is moving toward entry level
            price_moving_toward_entry = False
            if candles_5m and len(candles_5m) >= 3:
                # Calculate recent price direction (last 3 candles)
                recent_prices = [candle["close"] for candle in candles_5m[-3:]]
                price_direction = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                
                if side == "BUY" and entry_price >= current_price:
                    # For BUY orders: price should be moving DOWN toward entry level
                    if price_direction < -0.0005:  # Price dropping by at least 0.05%
                        price_moving_toward_entry = True
                        logger.info(f"✅ BUY order: Price moving DOWN toward entry ${entry_price:,.2f} (direction: {price_direction:.4f})")
                
                elif side == "SELL" and entry_price <= current_price:
                    # For SELL orders: price should be moving UP toward entry level
                    if price_direction > 0.0005:  # Price rising by at least 0.05%
                        price_moving_toward_entry = True
                        logger.info(f"✅ SELL order: Price moving UP toward entry ${entry_price:,.2f} (direction: {price_direction:.4f})")
            
            # Apply validation based on price movement
            if side == "BUY" and entry_price >= current_price and not price_moving_toward_entry:
                # Price not moving toward entry - adjust to safe level
                safe_entry = current_price * 0.997
                if support > 0 and support < current_price:
                    safe_entry = min(safe_entry, support * 1.001)
                
                prediction["entry_price"] = safe_entry
                prediction["reason"] += f" (ADJUSTED: price not moving toward entry, set to ${safe_entry:,.2f})"
                logger.warning(f"⚠️ BUY order adjusted: entry ${entry_price:,.2f} >= current ${current_price:,.2f}, price not moving down")
            
            elif side == "SELL" and entry_price <= current_price and not price_moving_toward_entry:
                # Price not moving toward entry - adjust to safe level
                safe_entry = current_price * 1.003
                if resistance > 0 and resistance > current_price:
                    safe_entry = max(safe_entry, resistance * 0.999)
                
                prediction["entry_price"] = safe_entry
                prediction["reason"] += f" (ADJUSTED: price not moving toward entry, set to ${safe_entry:,.2f})"
                logger.warning(f"⚠️ SELL order adjusted: entry ${entry_price:,.2f} <= current ${current_price:,.2f}, price not moving up")
            
            # Add execution timing metadata for equal-price scenarios
            if price_moving_toward_entry:
                prediction["execution_timing"] = "WAIT_FOR_ENTRY"  # Wait for price to reach entry level
                prediction["price_movement_direction"] = "TOWARD_ENTRY"
                logger.info(f"🎯 {pred_type}: Price moving toward entry ${entry_price:,.2f} - execution timing: WAIT_FOR_ENTRY")
            else:
                prediction["execution_timing"] = "IMMEDIATE"  # Can execute immediately
                prediction["price_movement_direction"] = "AWAY_FROM_ENTRY"
            
            return prediction
            
        except Exception as e:
            logger.error(f"🚨 Error in entry price validation: {e}")
            # Emergency fallback: set safe entry prices
            if prediction.get("side") == "BUY":
                prediction["entry_price"] = current_price * 0.997
                prediction["reason"] += " (emergency fallback entry)"
            elif prediction.get("side") == "SELL":
                prediction["entry_price"] = current_price * 1.003
                prediction["reason"] += " (emergency fallback entry)"
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
    
    def _detect_hyperliquid_volume_activity(self, liquidity_metrics: Dict, depth_imbalance: float) -> Dict[str, Any]:
        """Detect high volume activity from Hyperliquid real-time orderbook data"""
        try:
            total_depth = liquidity_metrics.get("total_depth", 0)
            bid_depth = liquidity_metrics.get("bid_depth", 0)
            ask_depth = liquidity_metrics.get("ask_depth", 0)
            
            # Detect high volume activity based on orderbook depth
            volume_activity_detected = False
            activity_strength = 0.0
            direction = "UNKNOWN"
            
            # High total depth indicates active trading
            if total_depth > 80:  # Very high activity threshold
                volume_activity_detected = True
                activity_strength = min(1.0, (total_depth - 80) / 100)  # Scale 80-180 -> 0-1
                
                # Determine direction from imbalance
                if depth_imbalance < -0.3:  # Heavy selling pressure
                    direction = "DOWN"
                elif depth_imbalance > 0.3:  # Heavy buying pressure  
                    direction = "UP"
                else:
                    direction = "NEUTRAL"
                    
            elif total_depth > 50:  # Moderate activity
                volume_activity_detected = True
                activity_strength = min(0.6, (total_depth - 50) / 60)  # Scale 50-110 -> 0-0.6
                direction = "DOWN" if depth_imbalance < -0.2 else "UP" if depth_imbalance > 0.2 else "NEUTRAL"
            
            return {
                "detected": volume_activity_detected,
                "direction": direction,
                "strength": activity_strength,
                "total_depth": total_depth,
                "imbalance": depth_imbalance,
                "data_source": "hyperliquid_orderbook"
            }
            
        except Exception as e:
            logger.error(f"Error detecting Hyperliquid volume activity: {e}")
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
    
    def _calculate_breakout_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float, rsi: float = 50, volume_depth: float = 0, depth_imbalance: float = 0, trend_1d: Dict = {}) -> float:
        """Calculate confidence for breakout predictions with multi-timeframe RSI and volume integration"""
        base_confidence = 0.5
        
        # Multi-timeframe trend alignment analysis
        trend_5m_dir = trend_5m.get("trend", "UNKNOWN")
        trend_1h_dir = trend_1h.get("trend", "UNKNOWN")
        trend_1d_dir = trend_1d.get("trend", "UNKNOWN")
        
        # Short-term trend alignment bonus
        if trend_1h_dir == trend_5m_dir:
            base_confidence += 0.2
            
        # Daily trend support for breakouts (powerful confirmation)
        if trend_1d_dir != "UNKNOWN":
            if trend_1d_dir == trend_5m_dir == trend_1h_dir:
                # All timeframes aligned = very strong breakout potential
                base_confidence += 0.25
            elif trend_1d_dir == trend_5m_dir:
                # Daily supports short-term direction = good breakout potential
                base_confidence += 0.15
            elif trend_1d_dir != trend_5m_dir:
                # Daily contradicts short-term = breakout may fail
                base_confidence -= 0.1
        
        # Trend strength bonus
        trend_strength = trend_1h.get("strength", 0.5)
        base_confidence += trend_strength * 0.1
        
        # Volatility adjustment
        if volatility < 0.002:  # Low volatility = more predictable
            base_confidence += 0.1
        elif volatility > 0.005:  # High volatility = less predictable
            base_confidence -= 0.1
        
        # RSI enhancement for breakouts
        if rsi < 35:  # Oversold - good for upward breakouts
            base_confidence += 0.15
        elif rsi > 65:  # Overbought - good for downward breakouts
            base_confidence += 0.15
        elif 45 <= rsi <= 55:  # Neutral RSI - slightly positive for breakouts
            base_confidence += 0.05
        
        # Volume/liquidity enhancement
        if volume_depth > 50:  # High liquidity supports breakouts
            base_confidence += 0.1
        elif volume_depth < 20:  # Low liquidity = harder breakouts
            base_confidence -= 0.05
            
        # Orderbook imbalance support for breakout direction
        if abs(depth_imbalance) > 0.3:  # Strong directional pressure
            base_confidence += 0.1
        
        # Conservative confidence cap for breakouts  
        return min(0.85, max(0.20, base_confidence))  # Max 85% for breakouts, min 20%
    
    def _calculate_reversion_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float, rsi: float = 50, volume_depth: float = 0, depth_imbalance: float = 0, trend_1d: Dict = {}) -> float:
        """Calculate confidence for reversion predictions with conservative multi-timeframe analysis"""
        base_confidence = 0.35  # More conservative base for reversions (reduced from 0.4)
        
        # Multi-timeframe trend analysis for reversions
        trend_5m_dir = trend_5m.get("trend", "UNKNOWN")
        trend_1h_dir = trend_1h.get("trend", "UNKNOWN") 
        trend_1d_dir = trend_1d.get("trend", "UNKNOWN")
        
        # Conservative trend divergence analysis
        if trend_1h_dir != trend_5m_dir:
            base_confidence += 0.08  # Reduced from 0.15 - more conservative
            
        # Daily trend context - much more conservative
        if trend_1d_dir == "DOWN" and trend_5m_dir == "UP":
            # Daily downtrend with short-term up = moderate reversion probability
            base_confidence += 0.10  # Reduced from 0.18
        elif trend_1d_dir == "UP" and trend_5m_dir == "DOWN":
            # Daily uptrend with short-term down = moderate reversion probability  
            base_confidence += 0.10  # Reduced from 0.18
        elif trend_1d_dir != "UNKNOWN" and trend_1d_dir == trend_5m_dir:
            # Daily trend aligned with short-term = much lower reversion probability
            base_confidence -= 0.12  # Increased penalty from -0.05
            
        # Counter-trend penalty - penalize risky trades against momentum
        if trend_5m_dir == trend_1h_dir == trend_1d_dir:
            # All timeframes aligned = very low reversion probability
            base_confidence -= 0.15
        
        # Conservative volatility adjustment
        if volatility < 0.002:  # Low volatility = slightly more predictable reversions
            base_confidence += 0.05  # Reduced from 0.1
        elif volatility > 0.005:  # High volatility = less predictable
            base_confidence -= 0.08
        
        # Conservative RSI enhancement - much more realistic
        if rsi > 75:  # Extremely overbought - moderate confidence for downward reversion
            base_confidence += 0.12  # Reduced from 0.2
        elif rsi < 25:  # Extremely oversold - moderate confidence for upward reversion
            base_confidence += 0.12  # Reduced from 0.2
        elif rsi > 65 or rsi < 35:  # Moderately extreme levels
            base_confidence += 0.06  # Reduced from 0.1
        elif 40 <= rsi <= 60:  # Neutral RSI = lower reversion probability
            base_confidence -= 0.05  # Penalty for neutral RSI reversions
        
        # Conservative volume enhancement
        if volume_depth > 60:  # Very high liquidity
            base_confidence += 0.05  # Reduced from 0.08
        elif volume_depth > 40:  # High liquidity
            base_confidence += 0.03
        
        # Conservative orderbook imbalance - requires extreme conditions
        if abs(depth_imbalance) > 0.6:  # Only very extreme imbalance
            base_confidence += 0.08  # Reduced from 0.12
        elif abs(depth_imbalance) > 0.4:  # Moderate imbalance
            base_confidence += 0.04
            
        # Risk penalty for counter-trend trades (your key concern!)
        if trend_5m_dir != "UNKNOWN" and trend_1h_dir != "UNKNOWN":
            # If betting against recent momentum, reduce confidence
            if trend_5m_dir == "UP" and trend_1h_dir == "UP":
                # Betting on downward reversion while trends are up = risky
                base_confidence -= 0.10
            elif trend_5m_dir == "DOWN" and trend_1h_dir == "DOWN":
                # Betting on upward reversion while trends are down = risky
                base_confidence -= 0.10
        
        # Stability enhancement - prevent confidence jumping
        # Apply smoothing to make confidence more stable
        if hasattr(self, '_last_reversion_confidence'):
            # Smooth with previous confidence to prevent jumping
            smoothing_factor = 0.3
            base_confidence = (base_confidence * (1 - smoothing_factor)) + (self._last_reversion_confidence * smoothing_factor)
        
        # Store for next calculation
        self._last_reversion_confidence = base_confidence
        
        # Very conservative confidence cap for reversions (much lower than before)
        return min(0.65, max(0.20, base_confidence))  # Max 65% for reversions (was 90%!), min 20%
    
    def _calculate_momentum_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float, rsi: float = 50, volume_depth: float = 0, depth_imbalance: float = 0) -> float:
        """Calculate confidence for momentum predictions with RSI and volume integration"""
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
        
        # RSI enhancement for momentum
        if 40 <= rsi <= 60:  # RSI in momentum-friendly range
            base_confidence += 0.1
        elif rsi < 25 or rsi > 75:  # Extreme RSI may signal momentum continuation
            base_confidence += 0.05
        
        # Conservative volume enhancement for momentum
        if volume_depth > 70:  # Very high liquidity supports strong momentum
            base_confidence += 0.08  # Reduced from 0.12
        elif volume_depth > 40:  # Medium liquidity
            base_confidence += 0.04  # Reduced from 0.06
        
        # Conservative orderbook imbalance for momentum
        if abs(depth_imbalance) > 0.3:  # Strong directional pressure supports momentum
            base_confidence += 0.05  # Reduced from 0.08
        
        # Stability enhancement - prevent confidence jumping
        if hasattr(self, '_last_momentum_confidence'):
            # Smooth with previous confidence to prevent jumping
            smoothing_factor = 0.3
            base_confidence = (base_confidence * (1 - smoothing_factor)) + (self._last_momentum_confidence * smoothing_factor)
        
        # Store for next calculation
        self._last_momentum_confidence = base_confidence
        
        # Conservative confidence cap for momentum
        return min(0.85, max(0.25, base_confidence))  # Max 85% for momentum (was 95%), min 25%
    
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
    
    def validate_prediction_scenario(self, prediction: Dict[str, Any], candles_5m: List, current_price: float) -> Dict[str, Any]:
        """Validate if the market is following the predicted scenario before executing trade"""
        try:
            pred_type = prediction.get("type", "UNKNOWN")
            side = prediction.get("side", "UNKNOWN")
            entry_price = prediction.get("entry_price", 0)
            
            # Initialize validation result
            validation_result = {
                "is_valid": False,
                "confidence": 0.0,
                "reason": "",
                "should_execute": False,
                "validation_stage": "INITIAL"
            }
            
            if not candles_5m or len(candles_5m) < 10:
                validation_result["reason"] = "Insufficient data for validation"
                return validation_result
            
            # Get recent price action for validation
            recent_prices = [candle["close"] for candle in candles_5m[-10:]]
            recent_volumes = [candle["volume"] for candle in candles_5m[-10:]]
            recent_highs = [candle["high"] for candle in candles_5m[-5:]]
            recent_lows = [candle["low"] for candle in candles_5m[-5:]]
            
            # Calculate key metrics
            price_direction = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            price_momentum = (recent_prices[-1] - recent_prices[-3]) / recent_prices[-3]
            avg_volume = sum(recent_volumes[:-1]) / len(recent_volumes[:-1])
            current_volume = recent_volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # VALIDATION LOGIC BASED ON PREDICTION TYPE
            if pred_type == "SUPPORT_BOUNCE" and side == "BUY":
                validation_result = self._validate_support_bounce_scenario(
                    prediction, recent_prices, recent_lows, price_direction, 
                    price_momentum, volume_ratio, current_price, entry_price
                )
            
            elif pred_type == "REVERSION_FROM_RESISTANCE" and side == "SELL":
                validation_result = self._validate_resistance_rejection_scenario(
                    prediction, recent_prices, recent_highs, price_direction,
                    price_momentum, volume_ratio, current_price, entry_price
                )
            
            elif pred_type == "MOMENTUM_UP" and side == "BUY":
                validation_result = self._validate_momentum_continuation_scenario(
                    prediction, recent_prices, price_direction, price_momentum,
                    volume_ratio, current_price, entry_price, "UP"
                )
            
            elif pred_type == "MOMENTUM_DOWN" and side == "SELL":
                validation_result = self._validate_momentum_continuation_scenario(
                    prediction, recent_prices, price_direction, price_momentum,
                    volume_ratio, current_price, entry_price, "DOWN"
                )
            
            elif pred_type == "BREAKOUT_ABOVE" and side == "BUY":
                validation_result = self._validate_breakout_scenario(
                    prediction, recent_prices, recent_highs, price_direction,
                    price_momentum, volume_ratio, current_price, entry_price, "UP"
                )
            
            elif pred_type == "BREAKOUT_BELOW" and side == "SELL":
                validation_result = self._validate_breakout_scenario(
                    prediction, recent_prices, recent_lows, price_direction,
                    price_momentum, volume_ratio, current_price, entry_price, "DOWN"
                )
            
            else:
                # Generic validation for other prediction types
                validation_result = self._validate_generic_scenario(
                    prediction, recent_prices, price_direction, price_momentum,
                    volume_ratio, current_price, entry_price
                )
            
            # Log validation result
            if validation_result["is_valid"]:
                logger.info(f"✅ {pred_type} prediction VALIDATED: {validation_result['reason']}")
                if validation_result["should_execute"]:
                    logger.info(f"🚀 EXECUTING TRADE: {side} at ${entry_price:,.2f}")
            else:
                logger.info(f"❌ {pred_type} prediction INVALIDATED: {validation_result['reason']}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating prediction scenario: {e}")
            return {
                "is_valid": False,
                "confidence": 0.0,
                "reason": f"Validation error: {str(e)}",
                "should_execute": False,
                "validation_stage": "ERROR"
            }
    
    def _validate_support_bounce_scenario(self, prediction: Dict, recent_prices: List, recent_lows: List, 
                                        price_direction: float, price_momentum: float, volume_ratio: float,
                                        current_price: float, entry_price: float) -> Dict[str, Any]:
        """Validate support bounce scenario: price dropping toward support, then bouncing"""
        
        # Stage 1: Check if price is moving toward support (entry price)
        if current_price > entry_price:
            # Price should be moving DOWN toward support
            if price_direction > -0.001:  # Not moving down significantly
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "reason": "Price not moving toward support level",
                    "should_execute": False,
                    "validation_stage": "STAGE1_FAILED"
                }
            
            # Check if we're getting close to support
            distance_to_support = (current_price - entry_price) / current_price
            if distance_to_support > 0.01:  # More than 1% away from support
                return {
                    "is_valid": True,
                    "confidence": 0.3,
                    "reason": f"Price moving toward support (${entry_price:,.2f}), {distance_to_support:.2%} away",
                    "should_execute": False,
                    "validation_stage": "STAGE1_PENDING"
                }
        
        # Stage 2: Check if price reached support and showing bounce signs
        if current_price <= entry_price * 1.002:  # Within 0.2% of support
            # Look for bounce confirmation
            if price_momentum > 0.0005:  # Price starting to move up
                if volume_ratio > 1.2:  # Increased volume on bounce
                    return {
                        "is_valid": True,
                        "confidence": 0.8,
                        "reason": f"Support bounce confirmed at ${entry_price:,.2f} with volume surge",
                        "should_execute": True,
                        "validation_stage": "STAGE2_CONFIRMED"
                    }
                else:
                    return {
                        "is_valid": True,
                        "confidence": 0.6,
                        "reason": f"Support bounce detected at ${entry_price:,.2f}, waiting for volume confirmation",
                        "should_execute": False,
                        "validation_stage": "STAGE2_PENDING"
                    }
            else:
                return {
                    "is_valid": True,
                    "confidence": 0.4,
                    "reason": f"Price at support ${entry_price:,.2f}, waiting for bounce confirmation",
                    "should_execute": False,
                    "validation_stage": "STAGE2_PENDING"
                }
        
        return {
            "is_valid": True,
            "confidence": 0.5,
            "reason": "Support scenario in progress",
            "should_execute": False,
            "validation_stage": "IN_PROGRESS"
        }
    
    def _validate_resistance_rejection_scenario(self, prediction: Dict, recent_prices: List, recent_highs: List,
                                              price_direction: float, price_momentum: float, volume_ratio: float,
                                              current_price: float, entry_price: float) -> Dict[str, Any]:
        """Validate resistance rejection scenario: price rising toward resistance, then rejecting"""
        
        # Stage 1: Check if price is moving toward resistance (entry price)
        if current_price < entry_price:
            # Price should be moving UP toward resistance
            if price_direction < 0.001:  # Not moving up significantly
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "reason": "Price not moving toward resistance level",
                    "should_execute": False,
                    "validation_stage": "STAGE1_FAILED"
                }
            
            # Check if we're getting close to resistance
            distance_to_resistance = (entry_price - current_price) / current_price
            if distance_to_resistance > 0.01:  # More than 1% away from resistance
                return {
                    "is_valid": True,
                    "confidence": 0.3,
                    "reason": f"Price moving toward resistance (${entry_price:,.2f}), {distance_to_resistance:.2%} away",
                    "should_execute": False,
                    "validation_stage": "STAGE1_PENDING"
                }
        
        # Stage 2: Check if price reached resistance and showing rejection signs
        if current_price >= entry_price * 0.998:  # Within 0.2% of resistance
            # Look for rejection confirmation
            if price_momentum < -0.0005:  # Price starting to move down
                if volume_ratio > 1.2:  # Increased volume on rejection
                    return {
                        "is_valid": True,
                        "confidence": 0.8,
                        "reason": f"Resistance rejection confirmed at ${entry_price:,.2f} with volume surge",
                        "should_execute": True,
                        "validation_stage": "STAGE2_CONFIRMED"
                    }
                else:
                    return {
                        "is_valid": True,
                        "confidence": 0.6,
                        "reason": f"Resistance rejection detected at ${entry_price:,.2f}, waiting for volume confirmation",
                        "should_execute": False,
                        "validation_stage": "STAGE2_PENDING"
                    }
            else:
                return {
                    "is_valid": True,
                    "confidence": 0.4,
                    "reason": f"Price at resistance ${entry_price:,.2f}, waiting for rejection confirmation",
                    "should_execute": False,
                    "validation_stage": "STAGE2_PENDING"
                }
        
        return {
            "is_valid": True,
            "confidence": 0.5,
            "reason": "Resistance scenario in progress",
            "should_execute": False,
            "validation_stage": "IN_PROGRESS"
        }
    
    def _validate_momentum_continuation_scenario(self, prediction: Dict, recent_prices: List,
                                               price_direction: float, price_momentum: float, volume_ratio: float,
                                               current_price: float, entry_price: float, expected_direction: str) -> Dict[str, Any]:
        """Validate momentum continuation scenario"""
        
        if expected_direction == "UP":
            # Check if momentum is continuing upward
            if price_direction > 0.002 and price_momentum > 0.001:  # Strong upward momentum
                if volume_ratio > 1.1:  # Good volume support
                    return {
                        "is_valid": True,
                        "confidence": 0.8,
                        "reason": "Strong upward momentum with volume confirmation",
                        "should_execute": True,
                        "validation_stage": "MOMENTUM_CONFIRMED"
                    }
                else:
                    return {
                        "is_valid": True,
                        "confidence": 0.6,
                        "reason": "Upward momentum detected, waiting for volume confirmation",
                        "should_execute": False,
                        "validation_stage": "MOMENTUM_PENDING"
                    }
            else:
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "reason": "Upward momentum not confirmed",
                    "should_execute": False,
                    "validation_stage": "MOMENTUM_FAILED"
                }
        
        else:  # DOWN momentum
            if price_direction < -0.002 and price_momentum < -0.001:  # Strong downward momentum
                if volume_ratio > 1.1:  # Good volume support
                    return {
                        "is_valid": True,
                        "confidence": 0.8,
                        "reason": "Strong downward momentum with volume confirmation",
                        "should_execute": True,
                        "validation_stage": "MOMENTUM_CONFIRMED"
                    }
                else:
                    return {
                        "is_valid": True,
                        "confidence": 0.6,
                        "reason": "Downward momentum detected, waiting for volume confirmation",
                        "should_execute": False,
                        "validation_stage": "MOMENTUM_PENDING"
                    }
            else:
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "reason": "Downward momentum not confirmed",
                    "should_execute": False,
                    "validation_stage": "MOMENTUM_FAILED"
                }
    
    def _validate_breakout_scenario(self, prediction: Dict, recent_prices: List, recent_extremes: List,
                                  price_direction: float, price_momentum: float, volume_ratio: float,
                                  current_price: float, entry_price: float, expected_direction: str) -> Dict[str, Any]:
        """Validate breakout scenario"""
        
        # Check if price is breaking out with volume confirmation
        if expected_direction == "UP":
            if price_direction > 0.003 and price_momentum > 0.002:  # Strong breakout
                if volume_ratio > 1.5:  # High volume breakout
                    return {
                        "is_valid": True,
                        "confidence": 0.9,
                        "reason": "Strong upward breakout with high volume",
                        "should_execute": True,
                        "validation_stage": "BREAKOUT_CONFIRMED"
                    }
                else:
                    return {
                        "is_valid": True,
                        "confidence": 0.7,
                        "reason": "Upward breakout detected, waiting for volume confirmation",
                        "should_execute": False,
                        "validation_stage": "BREAKOUT_PENDING"
                    }
        else:  # DOWN breakout
            if price_direction < -0.003 and price_momentum < -0.002:  # Strong breakdown
                if volume_ratio > 1.5:  # High volume breakdown
                    return {
                        "is_valid": True,
                        "confidence": 0.9,
                        "reason": "Strong downward breakout with high volume",
                        "should_execute": True,
                        "validation_stage": "BREAKOUT_CONFIRMED"
                    }
                else:
                    return {
                        "is_valid": True,
                        "confidence": 0.7,
                        "reason": "Downward breakout detected, waiting for volume confirmation",
                        "should_execute": False,
                        "validation_stage": "BREAKOUT_PENDING"
                    }
        
        return {
            "is_valid": False,
            "confidence": 0.0,
            "reason": "Breakout not confirmed",
            "should_execute": False,
            "validation_stage": "BREAKOUT_FAILED"
        }
    
    def _validate_generic_scenario(self, prediction: Dict, recent_prices: List,
                                 price_direction: float, price_momentum: float, volume_ratio: float,
                                 current_price: float, entry_price: float) -> Dict[str, Any]:
        """Generic validation for other prediction types"""
        
        # Basic validation: check if price is moving in expected direction
        side = prediction.get("side", "UNKNOWN")
        
        if side == "BUY" and entry_price < current_price:
            # For BUY orders below current price, check if price is moving down
            if price_direction < -0.001:
                return {
                    "is_valid": True,
                    "confidence": 0.5,
                    "reason": "Price moving toward BUY entry level",
                    "should_execute": False,
                    "validation_stage": "GENERIC_PENDING"
                }
        
        elif side == "SELL" and entry_price > current_price:
            # For SELL orders above current price, check if price is moving up
            if price_direction > 0.001:
                return {
                    "is_valid": True,
                    "confidence": 0.5,
                    "reason": "Price moving toward SELL entry level",
                    "should_execute": False,
                    "validation_stage": "GENERIC_PENDING"
                }
        
        return {
            "is_valid": False,
            "confidence": 0.0,
            "reason": "Generic scenario not validated",
            "should_execute": False,
            "validation_stage": "GENERIC_FAILED"
        }
    
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
    
    def analyze_entry_point(self, prediction_analysis: Dict[str, Any], current_price: float, candles_5m: List = None) -> Dict[str, Any]:
        """Analyze entry point and determine if order should be placed"""
        try:
            if not prediction_analysis.get("has_prediction", False):
                return {"should_place_order": False, "reason": "No valid prediction"}
            
            prediction = prediction_analysis["best_prediction"]
            prediction_mode = prediction_analysis.get("prediction_mode", "PREDICTIVE")
            
            # PREDICTIVE LOGIC: Validate prediction before execution
            if prediction_mode == "PREDICTIVE":
                validation_result = self._validate_predictive_prediction(prediction, current_price, candles_5m, prediction_analysis)
                if not validation_result["is_valid"]:
                    return {"should_place_order": False, "reason": f"Prediction validation failed: {validation_result['reason']}"}
                
                # If prediction is validated, proceed with execution
                logger.info(f"🎯 PREDICTIVE VALIDATION PASSED: {prediction['type']} - {validation_result['reason']}")
            
            # REACTIVE LOGIC: Direct execution for reactive signals
            elif prediction_mode == "REACTIVE":
                if not self.is_prediction_valid(prediction, current_price, candles_5m):
                    return {"should_place_order": False, "reason": "Reactive prediction no longer valid"}
            
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
    
    def _validate_predictive_prediction(self, prediction: Dict[str, Any], current_price: float, candles_5m: List, prediction_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate predictive prediction by checking if market behavior confirms the prediction"""
        try:
            pred_type = prediction.get("type", "UNKNOWN")
            side = prediction.get("side", "UNKNOWN")
            entry_price = prediction.get("entry_price", 0)
            prediction_time = prediction.get("prediction_timestamp", 0)
            
            if not candles_5m or len(candles_5m) < 6:
                return {"is_valid": False, "reason": "Insufficient market data for validation"}
            
            # Get candles since prediction was made
            current_time = time.time()
            candles_since_prediction = [c for c in candles_5m if c.get("timestamp", 0) > prediction_time]
            
            if len(candles_since_prediction) < 3:
                return {"is_valid": False, "reason": "Not enough time passed since prediction"}
            
            # Analyze market behavior since prediction
            validation_result = self._analyze_prediction_confirmation(prediction, candles_since_prediction, current_price)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating predictive prediction: {e}")
            return {"is_valid": False, "reason": f"Validation error: {str(e)}"}
    
    def _analyze_prediction_confirmation(self, prediction: Dict[str, Any], candles_since_prediction: List, current_price: float) -> Dict[str, Any]:
        """Analyze if market behavior confirms the prediction"""
        try:
            pred_type = prediction.get("type", "UNKNOWN")
            side = prediction.get("side", "UNKNOWN")
            entry_price = prediction.get("entry_price", 0)
            
            # Extract price data
            prices = [candle["close"] for candle in candles_since_prediction]
            volumes = [candle["volume"] for candle in candles_since_prediction]
            
            # Calculate key metrics
            price_trend = (prices[-1] - prices[0]) / prices[0]  # Overall trend since prediction
            price_movement = abs(prices[-1] - entry_price) / entry_price  # Distance to entry
            volume_trend = sum(volumes[-3:]) / sum(volumes[:3]) if len(volumes) >= 6 else 1.0  # Volume trend
            
            # Validation logic based on prediction type
            if pred_type == "SUPPORT_BOUNCE" and side == "BUY":
                # For support bounce BUY: price should be moving toward support level
                if entry_price < current_price:  # Entry below current price
                    # Check if price is moving down toward entry
                    if price_trend < -0.001:  # Price moving down
                        if price_movement < 0.005:  # Close to entry level
                            return {"is_valid": True, "reason": "Price moving toward support level as predicted"}
                        else:
                            return {"is_valid": False, "reason": "Price not close enough to support level"}
                    else:
                        return {"is_valid": False, "reason": "Price not moving toward support level"}
                else:
                    return {"is_valid": False, "reason": "Support bounce entry should be below current price"}
            
            elif pred_type == "REVERSION_FROM_RESISTANCE" and side == "SELL":
                # For resistance reversion SELL: price should be moving toward resistance level
                if entry_price > current_price:  # Entry above current price
                    # Check if price is moving up toward entry
                    if price_trend > 0.001:  # Price moving up
                        if price_movement < 0.005:  # Close to entry level
                            return {"is_valid": True, "reason": "Price moving toward resistance level as predicted"}
                        else:
                            return {"is_valid": False, "reason": "Price not close enough to resistance level"}
                    else:
                        return {"is_valid": False, "reason": "Price not moving toward resistance level"}
                else:
                    return {"is_valid": False, "reason": "Resistance reversion entry should be above current price"}
            
            elif pred_type == "MOMENTUM_UP" and side == "BUY":
                # For momentum UP: price should be showing upward momentum
                if price_trend > 0.002 and volume_trend > 1.1:  # Strong upward momentum with volume
                    return {"is_valid": True, "reason": "Upward momentum confirmed with volume"}
                else:
                    return {"is_valid": False, "reason": "Insufficient upward momentum or volume"}
            
            elif pred_type == "MOMENTUM_REVERSION" and side == "SELL":
                # For momentum reversion SELL: price should be showing reversal signs
                if price_trend < -0.001 and volume_trend > 1.0:  # Downward reversal with volume
                    return {"is_valid": True, "reason": "Momentum reversal confirmed"}
                else:
                    return {"is_valid": False, "reason": "No clear momentum reversal detected"}
            
            elif pred_type == "BREAKOUT_BELOW" and side == "SELL":
                # For breakout below: price should be breaking below support
                if price_trend < -0.003:  # Strong downward movement
                    return {"is_valid": True, "reason": "Breakout below support confirmed"}
                else:
                    return {"is_valid": False, "reason": "No clear breakout below support"}
            
            elif pred_type == "REVERSION_FROM_SUPPORT" and side == "BUY":
                # For support reversion BUY: price should be bouncing from support
                if price_trend > 0.002:  # Upward bounce
                    return {"is_valid": True, "reason": "Support reversion confirmed"}
                else:
                    return {"is_valid": False, "reason": "No clear support reversion"}
            
            elif pred_type == "RANGE_BREAKOUT_UP" and side == "BUY":
                # For range breakout up: price should be breaking above resistance
                if price_trend > 0.003:  # Strong upward breakout
                    return {"is_valid": True, "reason": "Range breakout up confirmed"}
                else:
                    return {"is_valid": False, "reason": "No clear range breakout up"}
            
            elif pred_type == "RANGE_BREAKOUT_DOWN" and side == "SELL":
                # For range breakout down: price should be breaking below support
                if price_trend < -0.003:  # Strong downward breakout
                    return {"is_valid": True, "reason": "Range breakout down confirmed"}
                else:
                    return {"is_valid": False, "reason": "No clear range breakout down"}
            
            # Default case
            return {"is_valid": False, "reason": f"Unknown prediction type: {pred_type}"}
            
        except Exception as e:
            logger.error(f"Error analyzing prediction confirmation: {e}")
            return {"is_valid": False, "reason": f"Analysis error: {str(e)}"}
    
    def is_prediction_valid(self, prediction: Dict[str, Any], current_price: float, candles_5m: List = None) -> bool:
        """Check if prediction is still valid given current price and movement"""
        entry_price = prediction["entry_price"]
        side = prediction.get("side", "UNKNOWN")
        prediction_type = prediction.get("type", "UNKNOWN")
        
        # Basic validity check: price within 1% of entry for predictive logic
        price_diff = abs(current_price - entry_price) / current_price
        if price_diff > 0.01:
            return False
        
        return True
    
    def should_cancel_order(self, prediction: Dict[str, Any], current_price: float, candles_5m: List, order_placed_time: float) -> Dict[str, Any]:
        """Determine if an active limit order should be cancelled based on market conditions"""
        try:
            pred_type = prediction.get("type", "UNKNOWN")
            side = prediction.get("side", "UNKNOWN")
            entry_price = prediction.get("entry_price", 0)
            prediction_time = prediction.get("prediction_timestamp", 0)
            
            # Initialize cancellation result
            cancellation_result = {
                "should_cancel": False,
                "reason": "",
                "urgency": "NORMAL",  # NORMAL, HIGH, CRITICAL
                "market_conditions": {}
            }
            
            if not candles_5m or len(candles_5m) < 6:
                return cancellation_result
            
            # Get candles since order was placed
            current_time = time.time()
            candles_since_order = [c for c in candles_5m if c.get("timestamp", 0) > order_placed_time]
            
            if len(candles_since_order) < 3:
                return cancellation_result  # Not enough time passed
            
            # Analyze market behavior since order placement
            market_analysis = self._analyze_market_conditions_for_cancellation(
                prediction, candles_since_order, current_price, order_placed_time
            )
            
            # Determine if order should be cancelled based on prediction type
            if pred_type == "SUPPORT_BOUNCE" and side == "BUY":
                cancellation_result = self._check_support_bounce_cancellation(
                    prediction, market_analysis, current_price, entry_price
                )
            
            elif pred_type == "REVERSION_FROM_RESISTANCE" and side == "SELL":
                cancellation_result = self._check_resistance_reversion_cancellation(
                    prediction, market_analysis, current_price, entry_price
                )
            
            elif pred_type == "MOMENTUM_UP" and side == "BUY":
                cancellation_result = self._check_momentum_cancellation(
                    prediction, market_analysis, current_price, entry_price, "UP"
                )
            
            elif pred_type == "MOMENTUM_REVERSION" and side == "SELL":
                cancellation_result = self._check_momentum_cancellation(
                    prediction, market_analysis, current_price, entry_price, "DOWN"
                )
            
            elif pred_type == "BREAKOUT_BELOW" and side == "SELL":
                cancellation_result = self._check_breakout_cancellation(
                    prediction, market_analysis, current_price, entry_price, "DOWN"
                )
            
            elif pred_type == "REVERSION_FROM_SUPPORT" and side == "BUY":
                cancellation_result = self._check_support_reversion_cancellation(
                    prediction, market_analysis, current_price, entry_price
                )
            
            else:
                # Generic cancellation logic for other prediction types
                cancellation_result = self._check_generic_cancellation(
                    prediction, market_analysis, current_price, entry_price
                )
            
            # Add market conditions to result
            cancellation_result["market_conditions"] = market_analysis
            
            # Log cancellation decision
            if cancellation_result["should_cancel"]:
                logger.warning(f"🚨 ORDER CANCELLATION RECOMMENDED: {pred_type} {side} - {cancellation_result['reason']} (Urgency: {cancellation_result['urgency']})")
            else:
                logger.info(f"✅ Order remains valid: {pred_type} {side} - Market conditions favorable")
            
            return cancellation_result
            
        except Exception as e:
            logger.error(f"Error checking order cancellation: {e}")
            return {
                "should_cancel": False,
                "reason": f"Error in cancellation check: {str(e)}",
                "urgency": "NORMAL",
                "market_conditions": {}
            }
    
    def _analyze_market_conditions_for_cancellation(self, prediction: Dict[str, Any], candles_since_order: List, current_price: float, order_placed_time: float) -> Dict[str, Any]:
        """Analyze market conditions to determine if order should be cancelled"""
        try:
            # Extract price and volume data
            prices = [candle["close"] for candle in candles_since_order]
            volumes = [candle["volume"] for candle in candles_since_order]
            highs = [candle["high"] for candle in candles_since_order]
            lows = [candle["low"] for candle in candles_since_order]
            
            # Calculate key metrics
            price_trend = (prices[-1] - prices[0]) / prices[0]  # Overall trend since order
            price_momentum = (prices[-1] - prices[-3]) / prices[-3] if len(prices) >= 4 else 0  # Recent momentum
            volume_trend = sum(volumes[-3:]) / sum(volumes[:3]) if len(volumes) >= 6 else 1.0  # Volume trend
            
            # Calculate volatility
            price_changes = [abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            volatility = sum(price_changes) / len(price_changes) if price_changes else 0
            
            # Calculate price extremes
            max_high = max(highs)
            min_low = min(lows)
            price_range = (max_high - min_low) / current_price
            
            # Time since order placement
            time_since_order = time.time() - order_placed_time
            minutes_since_order = time_since_order / 60
            
            return {
                "price_trend": price_trend,
                "price_momentum": price_momentum,
                "volume_trend": volume_trend,
                "volatility": volatility,
                "price_range": price_range,
                "max_high": max_high,
                "min_low": min_low,
                "minutes_since_order": minutes_since_order,
                "candles_analyzed": len(candles_since_order)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions for cancellation: {e}")
            return {}
    
    def _check_support_bounce_cancellation(self, prediction: Dict, market_analysis: Dict, current_price: float, entry_price: float) -> Dict[str, Any]:
        """Check if support bounce BUY order should be cancelled"""
        price_trend = market_analysis.get("price_trend", 0)
        price_momentum = market_analysis.get("price_momentum", 0)
        volume_trend = market_analysis.get("volume_trend", 1.0)
        volatility = market_analysis.get("volatility", 0)
        minutes_since_order = market_analysis.get("minutes_since_order", 0)
        
        # CRITICAL: Price moving away from support (upward) - cancel immediately
        if price_trend > 0.005:  # Price up 0.5% since order
            return {
                "should_cancel": True,
                "reason": f"Price moving UP away from support (trend: {price_trend:.3f}) - support bounce failed",
                "urgency": "CRITICAL"
            }
        
        # HIGH: Price broke below support level significantly
        if current_price < entry_price * 0.995:  # 0.5% below entry
            return {
                "should_cancel": True,
                "reason": f"Price broke below support level (${entry_price:,.2f} -> ${current_price:,.2f})",
                "urgency": "HIGH"
            }
        
        # NORMAL: No volume confirmation after reasonable time
        if minutes_since_order > 10 and volume_trend < 0.8:
            return {
                "should_cancel": True,
                "reason": f"No volume confirmation after {minutes_since_order:.1f} minutes (volume trend: {volume_trend:.2f})",
                "urgency": "NORMAL"
            }
        
        # NORMAL: High volatility suggests unstable market
        if volatility > 0.008:  # Very high volatility
            return {
                "should_cancel": True,
                "reason": f"High volatility ({volatility:.3f}) suggests unstable market conditions",
                "urgency": "NORMAL"
            }
        
        return {"should_cancel": False, "reason": "Support bounce conditions still valid"}
    
    def _check_resistance_reversion_cancellation(self, prediction: Dict, market_analysis: Dict, current_price: float, entry_price: float) -> Dict[str, Any]:
        """Check if resistance reversion SELL order should be cancelled"""
        price_trend = market_analysis.get("price_trend", 0)
        price_momentum = market_analysis.get("price_momentum", 0)
        volume_trend = market_analysis.get("volume_trend", 1.0)
        volatility = market_analysis.get("volatility", 0)
        minutes_since_order = market_analysis.get("minutes_since_order", 0)
        
        # CRITICAL: Price moving away from resistance (downward) - cancel immediately
        if price_trend < -0.005:  # Price down 0.5% since order
            return {
                "should_cancel": True,
                "reason": f"Price moving DOWN away from resistance (trend: {price_trend:.3f}) - resistance reversion failed",
                "urgency": "CRITICAL"
            }
        
        # HIGH: Price broke above resistance level significantly
        if current_price > entry_price * 1.005:  # 0.5% above entry
            return {
                "should_cancel": True,
                "reason": f"Price broke above resistance level (${entry_price:,.2f} -> ${current_price:,.2f})",
                "urgency": "HIGH"
            }
        
        # NORMAL: No volume confirmation after reasonable time
        if minutes_since_order > 10 and volume_trend < 0.8:
            return {
                "should_cancel": True,
                "reason": f"No volume confirmation after {minutes_since_order:.1f} minutes (volume trend: {volume_trend:.2f})",
                "urgency": "NORMAL"
            }
        
        return {"should_cancel": False, "reason": "Resistance reversion conditions still valid"}
    
    def _check_momentum_cancellation(self, prediction: Dict, market_analysis: Dict, current_price: float, entry_price: float, expected_direction: str) -> Dict[str, Any]:
        """Check if momentum order should be cancelled"""
        price_trend = market_analysis.get("price_trend", 0)
        price_momentum = market_analysis.get("price_momentum", 0)
        volume_trend = market_analysis.get("volume_trend", 1.0)
        minutes_since_order = market_analysis.get("minutes_since_order", 0)
        
        if expected_direction == "UP":
            # CRITICAL: Momentum reversed to downward
            if price_trend < -0.003:  # Strong downward reversal
                return {
                    "should_cancel": True,
                    "reason": f"Upward momentum reversed to downward (trend: {price_trend:.3f})",
                    "urgency": "CRITICAL"
                }
            
            # HIGH: No momentum confirmation
            if price_momentum < 0.001 and minutes_since_order > 5:
                return {
                    "should_cancel": True,
                    "reason": f"No upward momentum confirmation after {minutes_since_order:.1f} minutes",
                    "urgency": "HIGH"
                }
        
        else:  # DOWN momentum
            # CRITICAL: Momentum reversed to upward
            if price_trend > 0.003:  # Strong upward reversal
                return {
                    "should_cancel": True,
                    "reason": f"Downward momentum reversed to upward (trend: {price_trend:.3f})",
                    "urgency": "CRITICAL"
                }
            
            # HIGH: No momentum confirmation
            if price_momentum > -0.001 and minutes_since_order > 5:
                return {
                    "should_cancel": True,
                    "reason": f"No downward momentum confirmation after {minutes_since_order:.1f} minutes",
                    "urgency": "HIGH"
                }
        
        # NORMAL: Volume drying up
        if volume_trend < 0.7 and minutes_since_order > 8:
            return {
                "should_cancel": True,
                "reason": f"Volume drying up (trend: {volume_trend:.2f}) after {minutes_since_order:.1f} minutes",
                "urgency": "NORMAL"
            }
        
        return {"should_cancel": False, "reason": f"{expected_direction} momentum conditions still valid"}
    
    def _check_breakout_cancellation(self, prediction: Dict, market_analysis: Dict, current_price: float, entry_price: float, expected_direction: str) -> Dict[str, Any]:
        """Check if breakout order should be cancelled"""
        price_trend = market_analysis.get("price_trend", 0)
        price_momentum = market_analysis.get("price_momentum", 0)
        volume_trend = market_analysis.get("volume_trend", 1.0)
        minutes_since_order = market_analysis.get("minutes_since_order", 0)
        
        if expected_direction == "DOWN":
            # CRITICAL: Breakout failed - price moving up instead
            if price_trend > 0.002:  # Price moving up instead of down
                return {
                    "should_cancel": True,
                    "reason": f"Breakout failed - price moving UP instead of DOWN (trend: {price_trend:.3f})",
                    "urgency": "CRITICAL"
                }
            
            # HIGH: No strong downward movement
            if price_momentum > -0.002 and minutes_since_order > 5:
                return {
                    "should_cancel": True,
                    "reason": f"No strong downward breakout movement after {minutes_since_order:.1f} minutes",
                    "urgency": "HIGH"
                }
        
        else:  # UP breakout
            # CRITICAL: Breakout failed - price moving down instead
            if price_trend < -0.002:  # Price moving down instead of up
                return {
                    "should_cancel": True,
                    "reason": f"Breakout failed - price moving DOWN instead of UP (trend: {price_trend:.3f})",
                    "urgency": "CRITICAL"
                }
            
            # HIGH: No strong upward movement
            if price_momentum < 0.002 and minutes_since_order > 5:
                return {
                    "should_cancel": True,
                    "reason": f"No strong upward breakout movement after {minutes_since_order:.1f} minutes",
                    "urgency": "HIGH"
                }
        
        # NORMAL: No volume confirmation for breakout
        if volume_trend < 1.2 and minutes_since_order > 8:
            return {
                "should_cancel": True,
                "reason": f"No volume confirmation for breakout (volume trend: {volume_trend:.2f})",
                "urgency": "NORMAL"
            }
        
        return {"should_cancel": False, "reason": f"{expected_direction} breakout conditions still valid"}
    
    def _check_support_reversion_cancellation(self, prediction: Dict, market_analysis: Dict, current_price: float, entry_price: float) -> Dict[str, Any]:
        """Check if support reversion BUY order should be cancelled"""
        price_trend = market_analysis.get("price_trend", 0)
        price_momentum = market_analysis.get("price_momentum", 0)
        minutes_since_order = market_analysis.get("minutes_since_order", 0)
        
        # CRITICAL: No bounce from support - price continuing down
        if price_trend < -0.003:  # Strong downward movement
            return {
                "should_cancel": True,
                "reason": f"No bounce from support - price continuing DOWN (trend: {price_trend:.3f})",
                "urgency": "CRITICAL"
            }
        
        # HIGH: No upward momentum after reasonable time
        if price_momentum < 0.001 and minutes_since_order > 8:
            return {
                "should_cancel": True,
                "reason": f"No upward bounce momentum after {minutes_since_order:.1f} minutes",
                "urgency": "HIGH"
            }
        
        return {"should_cancel": False, "reason": "Support reversion conditions still valid"}
    
    def _check_generic_cancellation(self, prediction: Dict, market_analysis: Dict, current_price: float, entry_price: float) -> Dict[str, Any]:
        """Generic cancellation logic for other prediction types"""
        price_trend = market_analysis.get("price_trend", 0)
        minutes_since_order = market_analysis.get("minutes_since_order", 0)
        side = prediction.get("side", "UNKNOWN")
        
        # Check if price moved significantly against the prediction
        if side == "BUY" and price_trend < -0.005:  # Price down 0.5% for BUY order
            return {
                "should_cancel": True,
                "reason": f"Price moved significantly against BUY prediction (trend: {price_trend:.3f})",
                "urgency": "HIGH"
            }
        
        elif side == "SELL" and price_trend > 0.005:  # Price up 0.5% for SELL order
            return {
                "should_cancel": True,
                "reason": f"Price moved significantly against SELL prediction (trend: {price_trend:.3f})",
                "urgency": "HIGH"
            }
        
        # Check if too much time has passed without execution
        if minutes_since_order > 15:  # 15 minutes without execution
            return {
                "should_cancel": True,
                "reason": f"Order not executed after {minutes_since_order:.1f} minutes - market conditions may have changed",
                "urgency": "NORMAL"
            }
        
        return {"should_cancel": False, "reason": "Generic conditions still valid"}
