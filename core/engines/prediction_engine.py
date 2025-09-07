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
            
            # Step 3: Check if we have any directional signal (let trading manager decide on confidence)
            overall_direction = aggregated_signal.get("overall_direction", "NEUTRAL")
            if overall_direction == "NEUTRAL":
                # Try to find the strongest individual signal for weak market conditions
                strongest_signal = self._find_strongest_individual_signal(primary_signals)
                if strongest_signal:
                    logger.info(f"🔄 Using strongest individual signal: {strongest_signal['direction']} ({strongest_signal['confidence']:.1%})")
                    # Create a modified aggregated signal based on strongest individual signal
                    aggregated_signal = {
                        "overall_direction": strongest_signal["direction"],
                        "overall_confidence": strongest_signal["confidence"] * 0.7,  # Reduce confidence for weak signals
                        "quality_rating": "FAIR",
                        "quality_score": strongest_signal["confidence"] * 0.5,
                        "signal_components": {strongest_signal["type"]: strongest_signal},
                        "overall_reasoning": f"Based on strongest signal: {strongest_signal['type']}"
                    }
                else:
                    logger.debug(f"📊 No directional signal - skipping prediction generation")
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
            entry_price = self._calculate_entry_price(overall_direction, current_price, strategy_name)
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
    
    
    def _calculate_entry_price(self, direction: str, current_price: float, strategy_name: str) -> float:
        """Calculate optimal entry price based on direction and strategy"""
        try:
            if direction == "BUY":
                # For buy orders, try to get slightly better price
                if strategy_name == "range_trading":
                    return current_price * 0.9995  # 0.05% below current price
                else:
                    return current_price * 0.999  # 0.1% below current price
            else:  # SELL
                # For sell orders, try to get slightly better price
                if strategy_name == "range_trading":
                    return current_price * 1.0005  # 0.05% above current price
                else:
                    return current_price * 1.001  # 0.1% above current price
                    
        except Exception as e:
            logger.error(f"❌ Entry price calculation failed: {e}")
            return current_price
    
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
                    # Use psychological support levels for range trading
                    strong_support = nearest_levels.get("strong_support", {})
                    if strong_support and strong_support.get("level", 0) < entry_price:
                        stop_loss = strong_support["level"] * 0.999  # Slightly below support
                    else:
                        stop_loss = entry_price * 0.995  # 0.5% stop loss
                else:
                    stop_loss = entry_price * 0.98  # 2% stop loss for other strategies
                
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
                    # Use psychological resistance levels for range trading
                    strong_resistance = nearest_levels.get("strong_resistance", {})
                    if strong_resistance and strong_resistance.get("level", 0) > entry_price:
                        stop_loss = strong_resistance["level"] * 1.001  # Slightly above resistance
                    else:
                        stop_loss = entry_price * 1.005  # 0.5% stop loss
                else:
                    stop_loss = entry_price * 1.02  # 2% stop loss for other strategies
                
                # Calculate take profit (below entry)
                if strategy_name == "range_trading":
                    # Use more conservative take profit for range trading
                    take_profit = entry_price * 0.998  # 0.2% take profit for range trading
                else:
                    take_profit = entry_price * 0.995  # 0.5% take profit for other strategies
            
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
