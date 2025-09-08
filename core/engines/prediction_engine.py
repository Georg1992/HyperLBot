#!/usr/bin/env python3
"""
Prediction Engine
Generates high-quality trading predictions based on signal analysis
Uses the signal system for perfect prediction generation
"""

import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from core.signals import global_signal_aggregator, SignalType
from core.analysis.real_time.psychological_levels_calculator import global_psychological_levels_calculator
from core.market_data_manager import global_rsi_calculator
from core.constants import MagicNumbers


@dataclass
class PredictionResult:
    """Result of a prediction generation"""
    direction: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    reasoning: str
    signal_analysis: Dict[str, Any]
    timestamp: float
    strategy_used: str


class PredictionEngine:
    """
    Signal-Based Prediction Engine
    
    Purpose:
    - Generate planned trades based on signal analysis
    - Use limit orders for better execution prices
    - Provide comprehensive risk management
    - Support/resistance level integration
    - Historical context integration
    """
    
    def __init__(self):
        self.signal_aggregator = global_signal_aggregator
        
        # Prediction tracking
        self.last_prediction = None
        self.last_signals = None
        self.last_aggregated_signal = None
        self.last_update_time = 0
        self.prediction_cooldown = 10  # 10 seconds between predictions
        
        # Dynamic tracking
        self.signal_change_threshold = 0.05  # 5% change triggers re-evaluation (more sensitive)
        self.confidence_change_threshold = 0.02  # 2% confidence change triggers update (more sensitive)
        self.entry_price_tolerance = 0.002  # 0.2% tolerance for entry price validity
        
        # Quality thresholds
        self.min_confidence_threshold = 0.7  # 70% minimum confidence
        self.high_confidence_threshold = 0.85  # 85% for high-quality predictions
        
        # Session manager for historical context
        self.session_manager = None
        
        logger.info("🎯 Dynamic Signal-Based Prediction Engine initialized")
    
    def set_session_manager(self, session_manager):
        """Set session manager reference for accessing historical context"""
        self.session_manager = session_manager
    
    def get_historical_context(self) -> Dict[str, Any]:
        """Get session historical context for enhanced prediction decisions"""
        if self.session_manager and self.session_manager.has_historical_context():
            return self.session_manager.get_historical_context()
        return {}
    
    def track_signals_and_adjust_prediction(self, current_price: float, market_data: Dict[str, Any] = None, 
                                          strategy_name: str = "standard") -> Optional[Dict[str, Any]]:
        """
        Track signals and adjust existing prediction or generate new one if needed
        
        This method:
        1. Generates current signals
        2. Compares with last signals
        3. Adjusts confidence or generates new prediction if significant changes detected
        """
        try:
            market_data = market_data or {}
            
            # Step 1: Generate current signals
            current_signals = self.signal_aggregator.generate_primary_signals(current_price, market_data)
            current_aggregated = self.signal_aggregator.aggregate_signals(current_signals)
            
            # Step 2: If no previous prediction, generate initial one
            if not self.last_prediction:
                return self.generate_prediction(current_price, market_data, strategy_name)
            
            # Step 3: Check if current prediction is still valid
            prediction_validity = self._check_prediction_validity(current_price)
            
            # Step 4: Check for significant signal changes
            signal_changes = self._analyze_signal_changes(current_signals, current_aggregated)
            
            # Step 5: Determine if we need a new prediction
            needs_new_prediction = (
                signal_changes["significant_change"] or
                not prediction_validity["is_valid"] or
                prediction_validity["price_moved_away"] or
                self._should_regenerate_prediction(current_price, current_aggregated)
            )
            
            if needs_new_prediction:
                logger.info(f"🔄 Significant signal changes detected: {signal_changes['change_summary']}")
                
                # Generate new prediction with updated signals
                new_prediction = self._generate_prediction_from_signal(
                    current_aggregated, current_price, market_data, strategy_name
                )
                
                if new_prediction:
                    # Update tracking
                    self.last_prediction = new_prediction
                    self.last_signals = current_signals
                    self.last_aggregated_signal = current_aggregated
                    self.last_update_time = time.time()
                    
                    new_prediction["prediction_type"] = "SIGNAL_ADJUSTED"
                    new_prediction["adjustment_reason"] = signal_changes["change_summary"]
                    
                    logger.info(f"🎯 PREDICTION ADJUSTED: {new_prediction['direction']} at ${new_prediction['entry_price']:,.2f} ({new_prediction['confidence']:.1%} confidence)")
                    return new_prediction
            
            # Step 4: Adjust confidence of existing prediction if moderate changes
            elif signal_changes["confidence_change"] > self.confidence_change_threshold:
                adjusted_prediction = self._adjust_prediction_confidence(
                    signal_changes["confidence_change"], signal_changes["change_summary"]
                )
                
                if adjusted_prediction:
                    logger.info(f"📊 PREDICTION CONFIDENCE ADJUSTED: {adjusted_prediction['confidence']:.1%} ({signal_changes['confidence_change']:+.1%})")
                    return adjusted_prediction
            
            # Step 5: Return existing prediction if no significant changes
            logger.debug("📊 No significant signal changes - keeping existing prediction")
            return self.last_prediction
            
        except Exception as e:
            logger.error(f"❌ Signal tracking and adjustment failed: {e}")
            return self.last_prediction
    
    def _check_prediction_validity(self, current_price: float) -> Dict[str, Any]:
        """Check if the current prediction is still valid based on price movement"""
        try:
            if not self.last_prediction:
                return {"is_valid": False, "price_moved_away": False, "reason": "No prediction"}
            
            entry_price = self.last_prediction.get("entry_price", 0)
            direction = self.last_prediction.get("direction", "NEUTRAL")
            
            if entry_price == 0:
                return {"is_valid": False, "price_moved_away": False, "reason": "Invalid entry price"}
            
            # Calculate price deviation from entry
            price_deviation = abs(current_price - entry_price) / entry_price
            
            # Check if price has moved too far from entry level
            price_moved_away = price_deviation > self.entry_price_tolerance
            
            # Determine validity based on direction and price movement
            is_valid = True
            reason = "Prediction still valid"
            
            if price_moved_away:
                if direction == "BUY" and current_price < entry_price * (1 - self.entry_price_tolerance):
                    # Price moved down for a BUY prediction - still valid (better entry)
                    is_valid = True
                    reason = "Price moved down for BUY - better entry opportunity"
                elif direction == "SELL" and current_price > entry_price * (1 + self.entry_price_tolerance):
                    # Price moved up for a SELL prediction - still valid (better entry)
                    is_valid = True
                    reason = "Price moved up for SELL - better entry opportunity"
                else:
                    # Price moved against the prediction direction
                    is_valid = False
                    reason = f"Price moved {price_deviation:.1%} away from entry - prediction invalidated"
            
            return {
                "is_valid": is_valid,
                "price_moved_away": price_moved_away,
                "price_deviation": price_deviation,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"❌ Prediction validity check failed: {e}")
            return {"is_valid": False, "price_moved_away": True, "reason": f"Error: {e}"}
    
    def _should_regenerate_prediction(self, current_price: float, current_aggregated: Dict) -> bool:
        """Determine if we should regenerate prediction based on market conditions"""
        try:
            if not self.last_prediction:
                return True
            
            # Check if enough time has passed (force regeneration every 5 minutes)
            time_since_last = time.time() - self.last_update_time
            if time_since_last > 300:  # 5 minutes
                logger.info("🔄 Forcing prediction regeneration - 5 minutes elapsed")
                return True
            
            # Check if confidence has dropped significantly
            current_confidence = current_aggregated.get("overall_confidence", 0.0)
            last_confidence = self.last_prediction.get("confidence", 0.0)
            confidence_drop = last_confidence - current_confidence
            
            if confidence_drop > 0.1:  # 10% confidence drop
                logger.info(f"🔄 Confidence dropped {confidence_drop:.1%} - regenerating prediction")
                return True
            
            # Check if market conditions have changed significantly
            current_quality = current_aggregated.get("quality_rating", "POOR")
            if current_quality in ["EXCELLENT", "GOOD"] and self.last_prediction.get("confidence", 0) < 0.6:
                logger.info(f"🔄 Market conditions improved to {current_quality} - regenerating prediction")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Prediction regeneration check failed: {e}")
            return False
    
    def _analyze_signal_changes(self, current_signals: Dict, current_aggregated: Dict) -> Dict[str, Any]:
        """Analyze changes between current and last signals"""
        try:
            if not self.last_signals or not self.last_aggregated_signal:
                return {
                    "significant_change": True,
                    "confidence_change": 0.0,
                    "change_summary": "Initial signal analysis"
                }
            
            # Compare overall direction
            last_direction = self.last_aggregated_signal.get("overall_direction", "NEUTRAL")
            current_direction = current_aggregated.get("overall_direction", "NEUTRAL")
            direction_changed = last_direction != current_direction
            
            # Compare overall confidence
            last_confidence = self.last_aggregated_signal.get("overall_confidence", 0.0)
            current_confidence = current_aggregated.get("overall_confidence", 0.0)
            confidence_change = current_confidence - last_confidence
            
            # Compare individual signal changes
            signal_changes = []
            for signal_type, current_signal in current_signals.items():
                if signal_type in self.last_signals:
                    last_signal = self.last_signals[signal_type]
                    
                    # Check direction change
                    if last_signal.direction != current_signal.direction:
                        signal_changes.append(f"{signal_type}: {last_signal.direction}→{current_signal.direction}")
                    
                    # Check confidence change
                    conf_change = current_signal.confidence - last_signal.confidence
                    if abs(conf_change) > self.signal_change_threshold:
                        signal_changes.append(f"{signal_type} confidence: {conf_change:+.1%}")
            
            # Determine if changes are significant
            significant_change = (
                direction_changed or
                abs(confidence_change) > self.confidence_change_threshold or
                len(signal_changes) >= 2  # Multiple signal changes
            )
            
            change_summary = "; ".join(signal_changes) if signal_changes else "Minor signal fluctuations"
            
            return {
                "significant_change": significant_change,
                "confidence_change": confidence_change,
                "direction_changed": direction_changed,
                "signal_changes": signal_changes,
                "change_summary": change_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Signal change analysis failed: {e}")
            return {
                "significant_change": True,
                "confidence_change": 0.0,
                "change_summary": "Error in analysis - regenerating prediction"
            }
    
    def _adjust_prediction_confidence(self, confidence_change: float, change_summary: str) -> Optional[Dict[str, Any]]:
        """Adjust the confidence of the existing prediction"""
        try:
            if not self.last_prediction:
                return None
            
            # Create adjusted prediction
            adjusted_prediction = self.last_prediction.copy()
            
            # Adjust confidence
            new_confidence = max(0.1, min(0.95, adjusted_prediction["confidence"] + confidence_change))
            adjusted_prediction["confidence"] = new_confidence
            
            # Update reasoning
            original_reasoning = adjusted_prediction.get("reasoning", "")
            adjusted_prediction["reasoning"] = f"{original_reasoning} | Confidence adjusted: {confidence_change:+.1%} ({change_summary})"
            
            # Update timestamp
            adjusted_prediction["timestamp"] = time.time()
            adjusted_prediction["prediction_type"] = "CONFIDENCE_ADJUSTED"
            adjusted_prediction["adjustment_reason"] = change_summary
            
            # Update tracking
            self.last_prediction = adjusted_prediction
            self.last_update_time = time.time()
            
            return adjusted_prediction
            
        except Exception as e:
            logger.error(f"❌ Prediction confidence adjustment failed: {e}")
            return None
    
    def generate_prediction(self, current_price: float, market_data: Dict[str, Any] = None, 
                          strategy_name: str = "standard") -> Optional[Dict[str, Any]]:
        """
        Generate a high-quality trading prediction based on signal analysis
        
        Args:
            current_price: Current market price
            market_data: Additional market data
            strategy_name: Trading strategy to use
            
        Returns:
            Dict with prediction data if high-quality prediction found, None otherwise
        """
        try:
            # Check cooldown period
            if self._is_in_cooldown():
                return None
            
            market_data = market_data or {}
            
            # Step 1: Generate primary signals
            primary_signals = self.signal_aggregator.generate_primary_signals(current_price, market_data)
            
            # Step 2: Aggregate signals
            aggregated_signal = self.signal_aggregator.aggregate_signals(primary_signals)
            
            # Step 3: Check if we have any directional signal with market context validation
            overall_direction = aggregated_signal.get("overall_direction", "NEUTRAL")
            overall_confidence = aggregated_signal.get("overall_confidence", 0.0)
            
            logger.debug(f"📊 Signal direction: {overall_direction} with confidence: {overall_confidence:.1%}")
            
            if overall_direction == "NEUTRAL":
                # Try to find the strongest individual signal for weak market conditions
                strongest_signal = self._find_strongest_individual_signal(primary_signals)
                if strongest_signal and strongest_signal["confidence"] > 0.4:  # Higher threshold
                    # Validate individual signal against market context
                    individual_validation = self._validate_signal_against_market_context(
                        strongest_signal["direction"], current_price, market_data
                    )
                    
                    if individual_validation["valid"]:
                        logger.info(f"🔄 Using strongest individual signal: {strongest_signal['direction']} ({strongest_signal['confidence']:.1%})")
                        # Create a modified aggregated signal based on strongest individual signal
                        aggregated_signal = {
                            "overall_direction": strongest_signal["direction"],
                            "overall_confidence": strongest_signal["confidence"] * 0.8,  # Less reduction for validated signals
                            "quality_rating": "FAIR",
                            "quality_score": strongest_signal["confidence"] * 0.6,
                            "signal_components": {strongest_signal["type"]: strongest_signal},
                            "overall_reasoning": f"Based on strongest signal: {strongest_signal['type']} - {individual_validation['reason']}"
                        }
                    else:
                        logger.debug(f"📊 Strongest individual signal invalidated: {individual_validation['reason']}")
                        return None
                else:
                    logger.debug(f"📊 No strong enough directional signal - skipping prediction generation")
                    return None
            else:
                # For directional signals, validate against market context
                logger.debug(f"📊 Validating directional signal: {overall_direction}")
                market_context_validation = self._validate_signal_against_market_context(
                    overall_direction, current_price, market_data
                )
                
                if not market_context_validation["valid"]:
                    logger.debug(f"📊 Signal invalidated by market context: {market_context_validation['reason']}")
                    return None
            
            # Step 4: Generate prediction based on aggregated signal
            prediction = self._generate_prediction_from_signal(
                aggregated_signal, current_price, market_data, strategy_name
            )
            
            if prediction:
                # Update tracking
                self.last_prediction = prediction
                self.last_signals = primary_signals
                self.last_aggregated_signal = aggregated_signal
                self.last_update_time = time.time()
                
                logger.info(f"🎯 PREDICTION GENERATED: {prediction['direction']} at ${prediction['entry_price']:,.2f} ({prediction['confidence']:.1%} confidence)")
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Prediction generation failed: {e}")
            return None
    
    def _find_strongest_individual_signal(self, primary_signals: Dict) -> Optional[Dict[str, Any]]:
        """Find the strongest individual signal when overall direction is neutral"""
        try:
            strongest_signal = None
            highest_confidence = 0.0
            
            for signal_type, signal_data in primary_signals.items():
                if signal_data.direction != "NEUTRAL" and signal_data.confidence > highest_confidence:
                    highest_confidence = signal_data.confidence
                    strongest_signal = {
                        "type": signal_type.name if hasattr(signal_type, 'name') else str(signal_type),
                        "direction": signal_data.direction,
                        "confidence": signal_data.confidence,
                        "strength": signal_data.strength
                    }
            
            return strongest_signal if highest_confidence > 0.3 else None  # Minimum 30% confidence
            
        except Exception as e:
            logger.error(f"❌ Error finding strongest individual signal: {e}")
            return None
    
    def _generate_prediction_from_signal(self, aggregated_signal: Dict[str, Any], 
                                       current_price: float, market_data: Dict[str, Any], 
                                       strategy_name: str) -> Optional[Dict[str, Any]]:
        """Generate prediction from aggregated signal"""
        try:
            overall_direction = aggregated_signal.get("overall_direction", "NEUTRAL")
            overall_confidence = aggregated_signal.get("overall_confidence", 0.0)
            signal_components = aggregated_signal.get("signal_components", {})
            
            # Skip neutral signals
            if overall_direction == "NEUTRAL":
                logger.debug("📊 Neutral signal - no prediction generated")
                return None
            
            # Get historical context for enhanced prediction
            historical_context = self.get_historical_context()
            
            # Calculate prediction parameters
            entry_price = self._calculate_entry_price(overall_direction, current_price, strategy_name, market_data)
            stop_loss, take_profit = self._calculate_risk_levels(
                overall_direction, entry_price, current_price, strategy_name, market_data
            )
            position_size = self._calculate_position_size(overall_confidence, strategy_name)
            
            # Generate comprehensive reasoning
            reasoning = self._generate_prediction_reasoning(
                aggregated_signal, signal_components, overall_direction, overall_confidence
            )
            
            # Create prediction result
            prediction = {
                "direction": overall_direction,
                "confidence": overall_confidence,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "position_size": position_size,
                "reasoning": reasoning,
                "signal_analysis": {
                    "quality_rating": aggregated_signal.get("quality_rating", "UNKNOWN"),
                    "quality_score": aggregated_signal.get("quality_score", 0.0),
                    "signal_components": signal_components,
                    "overall_reasoning": aggregated_signal.get("overall_reasoning", "")
                },
                "timestamp": time.time(),
                "strategy_used": strategy_name,
                "prediction_type": "SIGNAL_BASED"
            }
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Prediction generation from signal failed: {e}")
            return None
    
    
    def _calculate_entry_price(self, direction: str, current_price: float, strategy_name: str, market_data: Dict[str, Any] = None) -> float:
        """Calculate optimal entry price based on direction, strategy, and market context"""
        try:
            market_data = market_data or {}
            
            # Get recent price action for better entry timing
            recent_price_action = self._analyze_recent_price_action(current_price, market_data)
            
            if direction == "BUY":
                # For buy orders, entry should be at or below current price
                if recent_price_action.get("trend") == "DOWN" and recent_price_action.get("reversal_signal"):
                    # Buying the dip - use current price or slightly below
                    return current_price * 0.9995
                elif strategy_name == "range_trading":
                    # Range trading - buy near support levels
                    support_level = recent_price_action.get("support_level", current_price * 0.998)
                    # Ensure entry price is never above current price for BUY
                    if support_level and support_level < current_price:
                        return max(current_price * 0.999, support_level)
                    else:
                        return current_price * 0.999  # Default to slightly below current price
                else:
                    # Trend following - buy on breakouts (at current price)
                    return current_price
            else:  # SELL
                # For sell orders, entry should be at or above current price
                if recent_price_action.get("trend") == "UP" and recent_price_action.get("rejection_signal"):
                    # Selling the rejection - use current price or slightly above
                    return current_price * 1.0005
                elif strategy_name == "range_trading":
                    # Range trading - sell near resistance levels, but be realistic
                    resistance_level = recent_price_action.get("resistance_level", current_price * 1.002)
                    # For downtrending markets, use current price or very close to it
                    if resistance_level and resistance_level > current_price * 1.005:  # Only if resistance is significantly higher
                        return min(current_price * 1.001, resistance_level)
                    else:
                        return current_price  # Use current price for downtrending markets
                else:
                    # Trend following - sell on breakdowns (at current price)
                    return current_price
                    
        except Exception as e:
            logger.error(f"❌ Entry price calculation failed: {e}")
            return current_price
    
    def _analyze_recent_price_action(self, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze recent price action for better entry timing"""
        try:
            # Get recent price data
            recent_candles = market_data.get("recent_candles", [])
            if not recent_candles or len(recent_candles) < 3:
                return {"trend": "UNKNOWN", "reversal_signal": False, "rejection_signal": False}
            
            # Analyze last 3 candles for trend and reversal patterns
            last_3_candles = recent_candles[-3:]
            
            # Calculate trend
            first_price = last_3_candles[0].get("close", current_price)
            last_price = last_3_candles[-1].get("close", current_price)
            price_change = (last_price - first_price) / first_price
            
            trend = "UP" if price_change > 0.002 else "DOWN" if price_change < -0.002 else "SIDEWAYS"
            
            # Look for reversal signals
            reversal_signal = False
            rejection_signal = False
            
            if len(last_3_candles) >= 2:
                # Check for hammer/doji patterns (reversal signals)
                last_candle = last_3_candles[-1]
                high = last_candle.get("high", 0)
                low = last_candle.get("low", 0)
                close = last_candle.get("close", 0)
                open_price = last_candle.get("open", 0)
                
                if high > 0 and low > 0:
                    body_size = abs(close - open_price)
                    total_range = high - low
                    
                    if total_range > 0:
                        body_ratio = body_size / total_range
                        
                        # Hammer pattern (small body, long lower wick) - bullish reversal
                        if body_ratio < 0.3 and (close - low) > (high - close) * 2:
                            reversal_signal = True
                        
                        # Shooting star pattern (small body, long upper wick) - bearish reversal
                        elif body_ratio < 0.3 and (high - close) > (close - low) * 2:
                            rejection_signal = True
            
            # Get support/resistance levels
            support_resistance = market_data.get("support_resistance_5m", {})
            support_levels = support_resistance.get("support_levels", [])
            resistance_levels = support_resistance.get("resistance_levels", [])
            
            # Find nearest levels
            support_level = None
            resistance_level = None
            
            for support in support_levels[:3]:
                level = support.get("level", 0)
                if level > 0 and level < current_price:
                    support_level = level
                    break
            
            for resistance in resistance_levels[:3]:
                level = resistance.get("level", 0)
                if level > 0 and level > current_price:
                    resistance_level = level
                    break
            
            return {
                "trend": trend,
                "reversal_signal": reversal_signal,
                "rejection_signal": rejection_signal,
                "support_level": support_level,
                "resistance_level": resistance_level,
                "price_change": price_change
            }
            
        except Exception as e:
            logger.error(f"❌ Recent price action analysis failed: {e}")
            return {"trend": "UNKNOWN", "reversal_signal": False, "rejection_signal": False}
    
    def _validate_signal_against_market_context(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate signal direction against current market context"""
        try:
            # Get recent price action analysis
            price_action = self._analyze_recent_price_action(current_price, market_data)
            
            # Get trend information
            trend_5m = market_data.get("trend_5m", {})
            trend_direction = trend_5m.get("direction", "UNKNOWN")
            trend_strength = trend_5m.get("strength", 0.0)
            
            # Get RSI for overbought/oversold validation
            rsi_5m = market_data.get("rsi_5m", 50)
            
            # Validation rules - more flexible for range trading
            if direction == "BUY":
                # BUY signal validation
                if price_action.get("trend") == "DOWN" and price_action.get("reversal_signal"):
                    return {"valid": True, "reason": "Buying the dip with reversal signal"}
                elif rsi_5m < 30 and trend_direction == "DOWN":
                    return {"valid": True, "reason": "Oversold conditions with downtrend"}
                elif price_action.get("trend") == "UP" and trend_strength > 0.6:
                    return {"valid": True, "reason": "Strong uptrend continuation"}
                elif rsi_5m < 40 and price_action.get("support_level") and current_price <= price_action.get("support_level", 0) * 1.002:
                    return {"valid": True, "reason": "Near support level with oversold RSI"}
                elif rsi_5m < 50:  # More flexible - allow BUY if RSI is below neutral
                    return {"valid": True, "reason": "RSI below neutral - potential buying opportunity"}
                elif price_action.get("trend") == "DOWN":  # Allow buying dips
                    return {"valid": True, "reason": "Buying the dip"}
                elif rsi_5m < 60:  # Even more flexible for range trading
                    return {"valid": True, "reason": "RSI below 60 - range trading opportunity"}
                else:
                    return {"valid": False, "reason": "BUY signal not supported by market context"}
            
            elif direction == "SELL":
                # SELL signal validation
                if price_action.get("trend") == "UP" and price_action.get("rejection_signal"):
                    return {"valid": True, "reason": "Selling the rejection with bearish signal"}
                elif rsi_5m > 70 and trend_direction == "UP":
                    return {"valid": True, "reason": "Overbought conditions with uptrend"}
                elif price_action.get("trend") == "DOWN" and trend_strength > 0.6:
                    return {"valid": True, "reason": "Strong downtrend continuation"}
                elif rsi_5m > 60 and price_action.get("resistance_level") and current_price >= price_action.get("resistance_level", float('inf')) * 0.998:
                    return {"valid": True, "reason": "Near resistance level with overbought RSI"}
                elif rsi_5m > 50:  # More flexible - allow SELL if RSI is above neutral
                    return {"valid": True, "reason": "RSI above neutral - potential selling opportunity"}
                elif price_action.get("trend") == "UP":  # Allow selling rallies
                    return {"valid": True, "reason": "Selling the rally"}
                elif rsi_5m > 40:  # Even more flexible for range trading
                    return {"valid": True, "reason": "RSI above 40 - range trading opportunity"}
                else:
                    return {"valid": False, "reason": "SELL signal not supported by market context"}
            
            elif direction == "NEUTRAL":
                # NEUTRAL signals are always invalid for prediction generation
                return {"valid": False, "reason": "NEUTRAL signals cannot generate predictions"}
            
            else:
                return {"valid": False, "reason": f"Unknown direction: {direction}"}
            
        except Exception as e:
            logger.error(f"❌ Signal validation failed: {e}")
            return {"valid": False, "reason": "Validation error"}
    
    def _calculate_risk_levels(self, direction: str, entry_price: float, current_price: float, 
                             strategy_name: str, market_data: Dict[str, Any]) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels"""
        try:
            # Get psychological levels for better risk management
            psychological_analysis = global_psychological_levels_calculator.calculate_psychological_levels(current_price)
            nearest_levels = psychological_analysis.get("nearest_levels", {})
            
            if direction == "BUY":
                # Calculate stop loss (below entry)
                if strategy_name == "range_trading":
                    # Use psychological support levels for range trading, but cap the stop loss
                    strong_support = nearest_levels.get("strong_support", {})
                    if strong_support and strong_support.get("level", 0) < entry_price:
                        # Use support level but cap at reasonable distance (max 1% below entry)
                        support_stop = strong_support["level"] * 0.999
                        max_stop = entry_price * 0.99  # Max 1% stop loss
                        stop_loss = max(support_stop, max_stop)
                    else:
                        stop_loss = entry_price * 0.995  # 0.5% stop loss
                else:
                    stop_loss = entry_price * 0.99  # 1% stop loss for other strategies (reduced from 2%)
                
                # Calculate take profit (above entry)
                if strategy_name == "range_trading":
                    # Use psychological resistance levels for range trading
                    strong_resistance = nearest_levels.get("strong_resistance", {})
                    if strong_resistance and strong_resistance.get("level", 0) > entry_price:
                        take_profit = strong_resistance["level"] * 0.999  # Slightly below resistance
                    else:
                        take_profit = entry_price * 1.005  # 0.5% take profit
                else:
                    take_profit = entry_price * 1.02  # 2% take profit for other strategies
                    
            else:  # SELL
                # Calculate stop loss (above entry)
                if strategy_name == "range_trading":
                    # Use psychological resistance levels for range trading, but cap the stop loss
                    strong_resistance = nearest_levels.get("strong_resistance", {})
                    if strong_resistance and strong_resistance.get("level", 0) > entry_price:
                        # Use resistance level but cap at reasonable distance (max 1% above entry)
                        resistance_stop = strong_resistance["level"] * 1.001
                        max_stop = entry_price * 1.01  # Max 1% stop loss
                        stop_loss = min(resistance_stop, max_stop)
                    else:
                        stop_loss = entry_price * 1.005  # 0.5% stop loss
                else:
                    stop_loss = entry_price * 1.01  # 1% stop loss for other strategies (reduced from 2%)
                
                # Calculate take profit (below entry) - FIXED RISK/REWARD
                if strategy_name == "range_trading":
                    # Range trading needs better risk/reward - at least 1:1.5
                    take_profit = entry_price * 0.9925  # 0.75% take profit (1.5x the 0.5% stop loss)
                else:
                    take_profit = entry_price * 0.99  # 1% take profit (2x the 0.5% stop loss)
            
            return stop_loss, take_profit
            
        except Exception as e:
            logger.error(f"❌ Risk level calculation failed: {e}")
            # Fallback to simple percentage-based levels
            if direction == "BUY":
                return entry_price * 0.98, entry_price * 1.02
            else:
                return entry_price * 1.02, entry_price * 0.98
    
    def _calculate_position_size(self, confidence: float, strategy_name: str) -> float:
        """Calculate position size based on confidence and strategy"""
        try:
            base_size = 0.001  # Base size in BTC
            
            # Scale size based on confidence
            confidence_multiplier = min(1.0, confidence)
            
            # Adjust for strategy
            if strategy_name == "range_trading":
                # Range trading uses smaller positions
                strategy_multiplier = 0.8
            elif strategy_name == "trend_following":
                # Trend following uses larger positions
                strategy_multiplier = 1.2
            else:
                # Standard strategy
                strategy_multiplier = 1.0
            
            position_size = base_size * confidence_multiplier * strategy_multiplier
            
            return round(position_size, 6)  # Round to 6 decimal places
            
        except Exception as e:
            logger.error(f"❌ Position size calculation failed: {e}")
            return 0.001  # Fallback to base size
    
    def _generate_prediction_reasoning(self, aggregated_signal: Dict[str, Any], 
                                     signal_components: Dict[str, Any], 
                                     direction: str, confidence: float) -> str:
        """Generate comprehensive reasoning for the prediction"""
        try:
            reasoning_parts = []
            
            # Add overall signal analysis
            quality_rating = aggregated_signal.get("quality_rating", "UNKNOWN")
            reasoning_parts.append(f"Signal Quality: {quality_rating}")
            
            # Add confidence level
            if confidence >= 0.9:
                confidence_level = "Very High"
            elif confidence >= 0.8:
                confidence_level = "High"
            elif confidence >= 0.7:
                confidence_level = "Good"
            else:
                confidence_level = "Moderate"
            
            reasoning_parts.append(f"Confidence: {confidence_level} ({confidence:.1%})")
            
            # Add primary signal contributions
            primary_signals = []
            for signal_type, component in signal_components.items():
                if component.get("weighted_confidence", 0) > 0.1:  # Significant contribution
                    signal_direction = component.get("direction", "NEUTRAL")
                    signal_confidence = component.get("confidence", 0)
                    primary_signals.append(f"{signal_type}: {signal_direction} ({signal_confidence:.1%})")
            
            if primary_signals:
                reasoning_parts.append(f"Primary Signals: {' | '.join(primary_signals)}")
            
            # Add direction reasoning
            reasoning_parts.append(f"Direction: {direction}")
            
            return " | ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"❌ Reasoning generation failed: {e}")
            return f"Signal-based {direction} prediction ({confidence:.1%} confidence)"
    
    def _is_in_cooldown(self) -> bool:
        """Check if we're in cooldown period between predictions"""
        if not self.last_prediction:
            return False
        
        time_since_last = time.time() - self.last_update_time
        return time_since_last < self.prediction_cooldown
    
    def get_prediction_summary(self) -> Dict[str, Any]:
        """Get summary of prediction engine status"""
        return {
            "engine_status": "ACTIVE",
            "last_prediction": self.last_prediction is not None,
            "last_prediction_time": self.last_update_time,
            "cooldown_active": self._is_in_cooldown(),
            "min_confidence_threshold": self.min_confidence_threshold,
            "high_confidence_threshold": self.high_confidence_threshold,
            "prediction_cooldown": self.prediction_cooldown
        }


# Global instance for easy access
global_prediction_engine = PredictionEngine()
