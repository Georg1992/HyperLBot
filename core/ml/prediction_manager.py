#!/usr/bin/env python3
"""
ML Prediction Manager
====================
Manages multiple concurrent ML predictions and displays the highest confidence one
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class TradingPrediction:
    """Clean trading prediction structure"""
    prediction_id: str
    direction: str  # BUY/SELL/HOLD
    entry_price: float
    size_btc: float
    size_usd: float
    stop_loss: float
    target_price: float
    confidence: float
    timestamp: float
    reasoning: str
    signal_strength: Dict[str, float]  # Individual signal strengths
    execution_type: str = "LIMIT_ORDER"  # LIMIT_ORDER or MARKET_ORDER
    urgency: str = "NORMAL"  # NORMAL, HIGH, CRITICAL


    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for dashboard display"""
        return {
            "prediction_id": self.prediction_id,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "size_btc": self.size_btc,
            "size_usd": self.size_usd,
            "stop_loss": self.stop_loss,
            "target_price": self.target_price,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "reasoning": self.reasoning,
            "signal_strength": self.signal_strength,
            "risk_reward_ratio": self.calculate_risk_reward_ratio(),
            "age_seconds": time.time() - self.timestamp
        }
    
    def calculate_risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio"""
        if self.direction == "HOLD":
            return 0.0
        
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.target_price - self.entry_price)
        
        if risk == 0:
            return 0.0
        
        return reward / risk

class PredictionManager:
    """
    Manages multiple concurrent ML predictions
    Shows only the highest confidence prediction on dashboard
    """
    
    def __init__(self):
        self.active_predictions: Dict[str, TradingPrediction] = {}
        self.prediction_history: List[TradingPrediction] = []
        self.max_concurrent_predictions = 5
        self.max_history = 100
        self.min_confidence_threshold = 0.2  # Lowered for testing
        self.max_prediction_age = 300  # 5 minutes
        
        # Dynamic prediction management
        self.best_prediction: Optional[TradingPrediction] = None
        self.prediction_update_threshold = 0.05  # 5% improvement needed to update
        self.entry_price_optimization_enabled = True  # Allow entry price updates for better profit
        
        # Dynamic confidence adjustment parameters
        self.confidence_adjustment_rate = 0.05  # 5% adjustment per significant move
        self.price_movement_threshold = 0.001  # 0.1% price movement threshold
        self.max_confidence_boost = 0.15  # Maximum 15% confidence boost
        self.min_confidence_penalty = 0.10  # Maximum 10% confidence penalty
        
        logger.info("🎯 ML Prediction Manager initialized")
    
    def update_best_prediction(self, new_prediction: TradingPrediction, current_price: float, 
                              market_data: Dict[str, Any]) -> bool:
        """
        Update the best prediction with new signals if it improves win rate or profit potential
        
        Args:
            new_prediction: New prediction from analysis
            current_price: Current market price
            market_data: Current market data
            
        Returns:
            bool: True if prediction was updated, False otherwise
        """
        try:
            if not self.best_prediction:
                # No existing prediction, use new one
                self.best_prediction = new_prediction
                logger.info("🎯 Set initial best prediction")
                return True
            
            # Compare predictions
            current_confidence = self.best_prediction.confidence
            new_confidence = new_prediction.confidence
            
            # Check if new prediction is significantly better
            confidence_improvement = new_confidence - current_confidence
            
            # Check if entry price optimization is beneficial
            entry_optimization = self._evaluate_entry_price_optimization(
                self.best_prediction, new_prediction, current_price, market_data
            )
            
            # Update if significantly better confidence or better entry price
            should_update = (
                confidence_improvement >= self.prediction_update_threshold or
                entry_optimization["should_update"]
            )
            
            if should_update:
                old_prediction = self.best_prediction
                self.best_prediction = new_prediction
                
                # Add update reasoning to prediction
                update_reasons = []
                if confidence_improvement >= self.prediction_update_threshold:
                    update_reasons.append(f"confidence +{confidence_improvement:.1%}")
                if entry_optimization["should_update"]:
                    update_reasons.append(f"entry price optimization ({entry_optimization['reason']})")
                
                # Update reasoning in the prediction
                self.best_prediction.reasoning += f" | Updated: {', '.join(update_reasons)}"
                
                logger.info(f"🔄 Updated best prediction: {', '.join(update_reasons)}")
                logger.debug(f"   Old: {old_prediction.confidence:.3f} confidence")
                logger.debug(f"   New: {new_confidence:.3f} confidence")
                
                return True
            else:
                logger.debug(f"📊 New prediction not better enough: {confidence_improvement:.1%} < {self.prediction_update_threshold:.1%}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update best prediction: {e}")
            return False
    
    def _evaluate_entry_price_optimization(self, current_prediction: TradingPrediction, 
                                         new_prediction: TradingPrediction, 
                                         current_price: float, 
                                         market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate if entry price optimization would improve profit potential
        
        Returns:
            Dict with should_update, reason, and profit_improvement
        """
        try:
            if not self.entry_price_optimization_enabled:
                return {"should_update": False, "reason": "optimization disabled"}
            
            current_entry = current_prediction.entry_price
            new_entry = new_prediction.entry_price
            direction = new_prediction.direction
            
            # Calculate potential profit improvement
            if direction == "BUY":
                # For BUY: lower entry price = better profit
                if new_entry < current_entry:
                    profit_improvement = (current_entry - new_entry) / current_entry
                    if profit_improvement > 0.001:  # 0.1% improvement
                        return {
                            "should_update": True,
                            "reason": f"better BUY entry (-{profit_improvement:.1%})",
                            "profit_improvement": profit_improvement
                        }
            else:  # SELL
                # For SELL: higher entry price = better profit
                if new_entry > current_entry:
                    profit_improvement = (new_entry - current_entry) / current_entry
                    if profit_improvement > 0.001:  # 0.1% improvement
                        return {
                            "should_update": True,
                            "reason": f"better SELL entry (+{profit_improvement:.1%})",
                            "profit_improvement": profit_improvement
                        }
            
            return {"should_update": False, "reason": "no significant improvement"}
            
        except Exception as e:
            logger.error(f"❌ Entry price optimization evaluation failed: {e}")
            return {"should_update": False, "reason": f"evaluation error: {e}"}
    
    def get_best_prediction(self) -> Optional[TradingPrediction]:
        """Get the current best prediction"""
        return self.best_prediction
    
    def clear_best_prediction(self):
        """Clear the best prediction (after execution or timeout)"""
        self.best_prediction = None
        logger.debug("🧹 Cleared best prediction")
    
    def update_prediction_confidence(self, prediction_id: str, current_price: float) -> Optional[TradingPrediction]:
        """
        Update prediction confidence based on price movement toward/away from entry price
        """
        try:
            if prediction_id not in self.active_predictions:
                return None
            
            prediction = self.active_predictions[prediction_id]
            entry_price = prediction.entry_price
            current_confidence = prediction.confidence
            
            # Calculate price movement percentage
            price_movement = abs(current_price - entry_price) / entry_price
            
            # Only adjust if price moved significantly
            if price_movement < self.price_movement_threshold:
                return prediction
            
            # Determine if price is moving toward or away from entry
            if prediction.direction == "BUY":
                # For BUY: price moving down (toward entry) is good, up (away) is bad
                price_trend = (entry_price - current_price) / entry_price
            else:  # SELL
                # For SELL: price moving up (toward entry) is good, down (away) is bad
                price_trend = (current_price - entry_price) / entry_price
            
            # Calculate confidence adjustment
            if price_trend > 0:  # Price moving toward entry (favorable)
                confidence_boost = min(
                    self.max_confidence_boost,
                    price_trend * self.confidence_adjustment_rate * 100
                )
                new_confidence = min(0.95, current_confidence + confidence_boost)
                adjustment_reason = f"Price moving toward entry (+{confidence_boost*100:.1f}%)"
            else:  # Price moving away from entry (unfavorable)
                confidence_penalty = min(
                    self.min_confidence_penalty,
                    abs(price_trend) * self.confidence_adjustment_rate * 100
                )
                new_confidence = max(0.1, current_confidence - confidence_penalty)
                adjustment_reason = f"Price moving away from entry (-{confidence_penalty*100:.1f}%)"
            
            # Update prediction confidence
            old_confidence = prediction.confidence
            prediction.confidence = new_confidence
            
            logger.debug(f"🎯 {prediction_id} confidence adjusted: {old_confidence:.3f} → {new_confidence:.3f} ({adjustment_reason})")
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Failed to update prediction confidence: {e}")
            return None
    
    def generate_prediction(self, current_price: float, market_data: Dict[str, Any], 
                          signals: Dict[str, Any], strategy: str = "standard") -> Optional[TradingPrediction]:
        """
        Generate a new trading prediction based on all available signals and strategy
        
        Args:
            current_price: Current market price
            market_data: Comprehensive market data
            signals: All available signals from signal aggregator
            strategy: Selected trading strategy (scalping, trend_following, etc.)
            
        Returns:
            TradingPrediction if conditions are met, None otherwise
        """
        try:
            # Analyze all signals to determine if we should generate a prediction
            signal_analysis = self._analyze_all_signals(signals, market_data)
            
            # Only generate prediction if we have strong enough signals
            if signal_analysis["overall_confidence"] < self.min_confidence_threshold:
                logger.debug(f"🔍 Insufficient signal strength: {signal_analysis['overall_confidence']:.2f}")
                return None
            
            # Determine trading direction
            direction = self._determine_direction(signal_analysis, current_price, market_data)
            
            # If direction is HOLD, don't create a prediction
            if direction == "HOLD":
                logger.debug("🔍 Market conditions not suitable for trading - HOLD")
                return None
            
            # Calculate trading parameters
            trading_params = self._calculate_trading_parameters(
                direction, current_price, market_data, signal_analysis, strategy
            )
            
            # Create prediction
            prediction = TradingPrediction(
                prediction_id=str(uuid.uuid4()),
                direction=direction,
                entry_price=trading_params["entry_price"],
                size_btc=trading_params["size_btc"],
                size_usd=trading_params["size_usd"],
                stop_loss=trading_params["stop_loss"],
                target_price=trading_params["target_price"],
                confidence=signal_analysis["overall_confidence"],
                timestamp=time.time(),
                reasoning=signal_analysis["reasoning"],
                signal_strength=signal_analysis["individual_signals"]
            )
            
            # Add to active predictions
            self.active_predictions[prediction.prediction_id] = prediction
            
            # Clean up old predictions
            self._cleanup_old_predictions()
            
            logger.info(f"🎯 Generated {direction} prediction: {prediction.confidence:.2f} confidence, "
                       f"Entry: ${prediction.entry_price:.2f}, Target: ${prediction.target_price:.2f}")
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Failed to generate prediction: {e}")
            return None
    
    def _analyze_all_signals(self, signals: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze all available signals from signal aggregator and determine their importance"""
        try:
            individual_signals = {}
            total_weight = 0.0
            weighted_confidence = 0.0
            
            # Process signals from signal aggregator
            if signals:
                for signal_type, signal_result in signals.items():
                    if hasattr(signal_result, 'direction') and hasattr(signal_result, 'confidence') and hasattr(signal_result, 'weight'):
                        # Convert SignalResult to dictionary format
                        signal_dict = {
                            "signal": signal_result.direction,  # Fixed: use 'direction' not 'signal'
                            "confidence": signal_result.confidence,
                            "weight": signal_result.weight,
                            "reasoning": getattr(signal_result, 'reasoning', f"{signal_type} signal")
                        }
                        individual_signals[str(signal_type)] = signal_dict
                        weighted_confidence += signal_result.confidence * signal_result.weight
                        total_weight += signal_result.weight
                        
                        logger.debug(f"🔍 Processed signal {signal_type}: {signal_result.direction} "
                                   f"(confidence: {signal_result.confidence:.2f}, weight: {signal_result.weight:.2f})")
            
            # If no signals from aggregator, fall back to internal analysis
            if not individual_signals:
                logger.debug("🔍 No signals from aggregator, using internal analysis")
                
                # RSI Signal Analysis
                rsi = market_data.get("rsi", 50.0)
                rsi_signal = self._analyze_rsi_signal(rsi, market_data)
                individual_signals["rsi"] = rsi_signal
                weighted_confidence += rsi_signal["confidence"] * rsi_signal["weight"]
                total_weight += rsi_signal["weight"]
                
                # Trend Signal Analysis
                trend = market_data.get("trend_analysis", {}).get("overall_trend", "NEUTRAL")
                trend_signal = self._analyze_trend_signal(trend, market_data)
                individual_signals["trend"] = trend_signal
                weighted_confidence += trend_signal["confidence"] * trend_signal["weight"]
                total_weight += trend_signal["weight"]
                
                # Volume Signal Analysis
                volume_category = market_data.get("trading_volume_category", "NORMAL")
                volume_signal = self._analyze_volume_signal(volume_category, market_data)
                individual_signals["volume"] = volume_signal
                weighted_confidence += volume_signal["confidence"] * volume_signal["weight"]
                total_weight += volume_signal["weight"]
                
                # Volatility Signal Analysis
                volatility_category = market_data.get("volatility_5m_category", "MODERATE")
                volatility_signal = self._analyze_volatility_signal(volatility_category, market_data)
                individual_signals["volatility"] = volatility_signal
                weighted_confidence += volatility_signal["confidence"] * volatility_signal["weight"]
                total_weight += volatility_signal["weight"]
                
                # Support/Resistance Signal Analysis
                sr_data = market_data.get("support_resistance", {})
                sr_signal = self._analyze_sr_signal(sr_data, market_data.get("current_price", 0))
                individual_signals["support_resistance"] = sr_signal
                weighted_confidence += sr_signal["confidence"] * sr_signal["weight"]
                total_weight += sr_signal["weight"]
                
                # Pattern Signal Analysis
                pattern_data = market_data.get("pattern_analysis", {})
                pattern_signal = self._analyze_pattern_signal(pattern_data)
                individual_signals["pattern"] = pattern_signal
                weighted_confidence += pattern_signal["confidence"] * pattern_signal["weight"]
                total_weight += pattern_signal["weight"]
                
                # Pressure Signal Analysis
                pressure_data = market_data.get("pressure", {})
                pressure_signal = self._analyze_pressure_signal(pressure_data)
                individual_signals["pressure"] = pressure_signal
                weighted_confidence += pressure_signal["confidence"] * pressure_signal["weight"]
                total_weight += pressure_signal["weight"]
            
            # Calculate win probability (true confidence) based on historical performance
            # Note: We don't have entry price yet, so we'll calculate it without proximity adjustment
            overall_confidence = self._calculate_win_probability(individual_signals, market_data)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(individual_signals, overall_confidence)
            
            logger.debug(f"🔍 Signal analysis complete: {len(individual_signals)} signals, "
                        f"overall_confidence: {overall_confidence:.3f}")
            
            return {
                "overall_confidence": overall_confidence,
                "individual_signals": individual_signals,
                "reasoning": reasoning,
                "total_signals": len(individual_signals)
            }
            
        except Exception as e:
            logger.error(f"❌ Signal analysis failed: {e}")
            return {
                "overall_confidence": 0.0,
                "individual_signals": {},
                "reasoning": "Signal analysis failed",
                "total_signals": 0
            }
    
    def _analyze_rsi_signal(self, rsi: float, market_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze RSI signal strength based on market context and situation"""
        # Dynamic weight based on market volatility - more volatile = higher RSI importance
        volatility = market_context.get("volatility_5m", 0.001) if market_context else 0.001
        base_weight = 0.15
        volatility_multiplier = min(2.0, 1.0 + (volatility * 100))  # Scale with volatility
        weight = base_weight * volatility_multiplier
        
        # Analyze RSI in context of recent price action and market conditions
        recent_trend = market_context.get("trend_analysis", {}).get("overall_trend", "NEUTRAL") if market_context else "NEUTRAL"
        price_momentum = market_context.get("price_momentum", 0.0) if market_context else 0.0
        
        # Calculate dynamic confidence based on how extreme RSI is and market context
        rsi_extremity = abs(rsi - 50) / 50  # How far from neutral (0-1)
        
        # Adjust confidence based on market context
        if recent_trend == "BULLISH" and rsi < 50:
            # RSI below 50 in uptrend = momentum weakening = SELL opportunity
            confidence = 0.4 + (rsi_extremity * 0.4)  # 0.4-0.8 range
            signal = "SELL"
            reasoning = f"RSI {rsi:.1f} in bullish trend - momentum weakening, potential sell opportunity"
        elif recent_trend == "BEARISH" and rsi > 50:
            # RSI above 50 in downtrend = momentum weakening = BUY opportunity  
            confidence = 0.4 + (rsi_extremity * 0.4)  # 0.4-0.8 range
            signal = "BUY"
            reasoning = f"RSI {rsi:.1f} in bearish trend - momentum weakening, potential buy opportunity"
        elif rsi < 25:
            # CRITICAL oversold - MAXIMUM BUY signal
            confidence = 0.95  # Maximum confidence
            signal = "BUY"
            reasoning = f"RSI {rsi:.1f} critically oversold - maximum buy signal"
        elif rsi < 30:
            # Extreme oversold - STRONG BUY signal
            if price_momentum < -0.01:  # Strong downward momentum
                confidence = 0.7  # Still strong confidence even with momentum
                signal = "BUY"
                reasoning = f"RSI {rsi:.1f} extremely oversold - strong buy signal despite momentum"
            else:
                confidence = 0.9  # Very high confidence - clear oversold
                signal = "BUY"
                reasoning = f"RSI {rsi:.1f} extremely oversold - very strong buy signal"
        elif rsi > 75:
            # CRITICAL overbought - MAXIMUM SELL signal
            confidence = 0.95  # Maximum confidence
            signal = "SELL"
            reasoning = f"RSI {rsi:.1f} critically overbought - maximum sell signal"
        elif rsi > 70:
            # Extreme overbought - STRONG SELL signal
            if price_momentum > 0.01:  # Strong upward momentum
                confidence = 0.7  # Still strong confidence even with momentum
                signal = "SELL"
                reasoning = f"RSI {rsi:.1f} extremely overbought - strong sell signal despite momentum"
            else:
                confidence = 0.9  # Very high confidence - clear overbought
                signal = "SELL"
                reasoning = f"RSI {rsi:.1f} extremely overbought - very strong sell signal"
        else:
            # Neutral RSI - analyze in context
            if rsi_extremity > 0.2:  # Somewhat extreme
                confidence = 0.3 + (rsi_extremity * 0.3)  # 0.3-0.6 range
                signal = "BUY" if rsi < 50 else "SELL"  # RSI < 50 = bearish momentum = BUY opportunity, RSI > 50 = bullish momentum = SELL opportunity
                reasoning = f"RSI {rsi:.1f} showing {signal.lower()} bias in neutral market"
            else:
                confidence = 0.2
                signal = "NEUTRAL"
                reasoning = f"RSI {rsi:.1f} neutral - no clear directional bias"
        
        return {
            "signal": signal,
            "confidence": confidence,
            "weight": weight,
            "reasoning": reasoning
        }
    
    def _analyze_trend_signal(self, trend: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trend signal strength"""
        weight = 0.20  # 20% weight
        
        trend_strength = market_data.get("trend_analysis", {}).get("alignment_score", 0.5)
        
        if trend == "BULLISH" and trend_strength > 0.7:
            return {
                "signal": "BUY",
                "confidence": 0.8,
                "weight": weight,
                "reasoning": f"Strong bullish trend (alignment: {trend_strength:.2f})"
            }
        elif trend == "BEARISH" and trend_strength > 0.7:
            return {
                "signal": "SELL",
                "confidence": 0.8,
                "weight": weight,
                "reasoning": f"Strong bearish trend (alignment: {trend_strength:.2f})"
            }
        elif trend == "BULLISH":
            return {
                "signal": "BUY",
                "confidence": 0.6,
                "weight": weight,
                "reasoning": f"Weak bullish trend (alignment: {trend_strength:.2f})"
            }
        elif trend == "BEARISH":
            return {
                "signal": "SELL",
                "confidence": 0.6,
                "weight": weight,
                "reasoning": f"Weak bearish trend (alignment: {trend_strength:.2f})"
            }
        else:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.3,
                "weight": weight,
                "reasoning": f"Neutral trend (alignment: {trend_strength:.2f})"
            }
    
    def _analyze_volume_signal(self, volume_category: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze volume signal strength"""
        weight = 0.15  # 15% weight
        
        volume_spike = market_data.get("volume_spike", {}).get("has_spike", False)
        
        if volume_category in ["HIGH", "VERY_HIGH", "EXTREMELY_HIGH"] and volume_spike:
            return {
                "signal": "NEUTRAL",  # Volume alone doesn't indicate direction
                "confidence": 0.7,
                "weight": weight,
                "reasoning": f"High volume with spike - increased activity"
            }
        elif volume_category in ["HIGH", "VERY_HIGH", "EXTREMELY_HIGH"]:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.5,
                "weight": weight,
                "reasoning": f"High volume ({volume_category}) - good liquidity"
            }
        elif volume_category in ["LOW", "VERY_LOW"]:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.2,
                "weight": weight,
                "reasoning": f"Low volume ({volume_category}) - poor liquidity"
            }
        else:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.4,
                "weight": weight,
                "reasoning": f"Normal volume ({volume_category})"
            }
    
    def _analyze_volatility_signal(self, volatility_category: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze volatility signal strength"""
        weight = 0.10  # 10% weight
        
        if volatility_category in ["HIGH", "VERY_HIGH"]:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.6,
                "weight": weight,
                "reasoning": f"High volatility ({volatility_category}) - breakout potential"
            }
        elif volatility_category in ["LOW", "VERY_LOW"]:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.3,
                "weight": weight,
                "reasoning": f"Low volatility ({volatility_category}) - consolidation"
            }
        else:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.4,
                "weight": weight,
                "reasoning": f"Moderate volatility ({volatility_category})"
            }
    
    def _analyze_sr_signal(self, sr_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Analyze support/resistance signal strength"""
        weight = 0.20  # 20% weight
        
        if not sr_data or not sr_data.get("key_levels"):
            return {
                "signal": "NEUTRAL",
                "confidence": 0.2,
                "weight": weight,
                "reasoning": "No S/R levels available"
            }
        
        key_levels = sr_data["key_levels"]
        strongest_support = sr_data.get("strongest_support", 0)
        strongest_resistance = sr_data.get("strongest_resistance", 0)
        
        # Check proximity to key levels
        support_distance = abs(current_price - strongest_support) / current_price if strongest_support > 0 else 1.0
        resistance_distance = abs(current_price - strongest_resistance) / current_price if strongest_resistance > 0 else 1.0
        
        # If close to support, potential buy signal
        if support_distance < 0.005:  # Within 0.5%
            return {
                "signal": "BUY",
                "confidence": 0.7,
                "weight": weight,
                "reasoning": f"Near strong support (${strongest_support:.0f}) - potential bounce"
            }
        # If close to resistance, potential sell signal
        elif resistance_distance < 0.005:  # Within 0.5%
            return {
                "signal": "SELL",
                "confidence": 0.7,
                "weight": weight,
                "reasoning": f"Near strong resistance (${strongest_resistance:.0f}) - potential rejection"
            }
        else:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.4,
                "weight": weight,
                "reasoning": "Between S/R levels - no clear signal"
            }
    
    def _analyze_pattern_signal(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze pattern signal strength"""
        weight = 0.10  # 10% weight
        
        if not pattern_data or not pattern_data.get("patterns"):
            return {
                "signal": "NEUTRAL",
                "confidence": 0.2,
                "weight": weight,
                "reasoning": "No patterns detected"
            }
        
        patterns = pattern_data["patterns"]
        market_setup = pattern_data.get("market_setup", {})
        
        bullish_patterns = market_setup.get("bullish_patterns", 0)
        bearish_patterns = market_setup.get("bearish_patterns", 0)
        overall_confidence = pattern_data.get("overall_confidence", 0.0)
        
        if bullish_patterns > bearish_patterns and overall_confidence > 0.7:
            return {
                "signal": "BUY",
                "confidence": 0.7,
                "weight": weight,
                "reasoning": f"Bullish patterns ({bullish_patterns}) with high confidence"
            }
        elif bearish_patterns > bullish_patterns and overall_confidence > 0.7:
            return {
                "signal": "SELL",
                "confidence": 0.7,
                "weight": weight,
                "reasoning": f"Bearish patterns ({bearish_patterns}) with high confidence"
            }
        else:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.4,
                "weight": weight,
                "reasoning": f"Mixed patterns (bullish: {bullish_patterns}, bearish: {bearish_patterns})"
            }
    
    def _analyze_pressure_signal(self, pressure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market pressure signal strength"""
        weight = 0.10  # 10% weight
        
        if not pressure_data:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.2,
                "weight": weight,
                "reasoning": "No pressure data available"
            }
        
        direction = pressure_data.get("direction", "NEUTRAL")
        confidence = pressure_data.get("confidence", 0.5)
        strength = pressure_data.get("strength", 0.0)
        
        if direction == "BULLISH" and confidence > 0.7 and strength > 0.3:
            return {
                "signal": "BUY",
                "confidence": 0.7,
                "weight": weight,
                "reasoning": f"Strong bullish pressure (confidence: {confidence:.2f})"
            }
        elif direction == "BEARISH" and confidence > 0.7 and strength > 0.3:
            return {
                "signal": "SELL",
                "confidence": 0.7,
                "weight": weight,
                "reasoning": f"Strong bearish pressure (confidence: {confidence:.2f})"
            }
        else:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.4,
                "weight": weight,
                "reasoning": f"Neutral pressure ({direction}, confidence: {confidence:.2f})"
            }
    
    def _generate_reasoning(self, individual_signals: Dict[str, Any], overall_confidence: float) -> str:
        """Generate human-readable reasoning for the prediction"""
        try:
            # Count signal directions
            buy_signals = sum(1 for sig in individual_signals.values() if sig["signal"] == "BUY")
            sell_signals = sum(1 for sig in individual_signals.values() if sig["signal"] == "SELL")
            neutral_signals = sum(1 for sig in individual_signals.values() if sig["signal"] == "NEUTRAL")
            
            # Get strongest signals
            strong_signals = [sig for sig in individual_signals.values() if sig["confidence"] > 0.6]
            
            if overall_confidence > 0.7:
                confidence_level = "High"
            elif overall_confidence > 0.5:
                confidence_level = "Moderate"
            else:
                confidence_level = "Low"
            
            reasoning_parts = [
                f"{confidence_level} confidence ({overall_confidence:.2f})",
                f"Buy signals: {buy_signals}, Sell signals: {sell_signals}, Neutral: {neutral_signals}"
            ]
            
            if strong_signals:
                strong_reasons = [sig["reasoning"] for sig in strong_signals[:2]]  # Top 2 reasons
                reasoning_parts.extend(strong_reasons)
            
            return " | ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"❌ Failed to generate reasoning: {e}")
            return f"Analysis confidence: {overall_confidence:.2f}"
    
    def _determine_direction(self, signal_analysis: Dict[str, Any], current_price: float, 
                           market_data: Dict[str, Any]) -> str:
        """Determine trading direction based on signal analysis"""
        try:
            individual_signals = signal_analysis["individual_signals"]
            overall_confidence = signal_analysis["overall_confidence"]
            
            # Count directional signals
            buy_signals = [sig for sig in individual_signals.values() if sig["signal"] == "BUY"]
            sell_signals = [sig for sig in individual_signals.values() if sig["signal"] == "SELL"]
            
            # Calculate weighted scores
            buy_score = sum(sig["confidence"] * sig["weight"] for sig in buy_signals)
            sell_score = sum(sig["confidence"] * sig["weight"] for sig in sell_signals)
            
            logger.debug(f"🔍 Signal analysis: buy_score={buy_score:.3f}, sell_score={sell_score:.3f}, "
                        f"buy_signals={len(buy_signals)}, sell_signals={len(sell_signals)}")
            
            # Debug: Show individual signals
            for signal_name, signal_data in individual_signals.items():
                logger.debug(f"🔍 Signal {signal_name}: {signal_data['signal']} "
                           f"(confidence: {signal_data['confidence']:.2f}, weight: {signal_data['weight']:.2f})")
            
            # Let AI decide based on all available data - analyze the situation intelligently
            
            # Calculate signal strength ratio and market conviction
            total_signal_strength = buy_score + sell_score
            if total_signal_strength == 0:
                return "HOLD"  # No signals at all
            
            # Calculate relative strength and conviction
            buy_conviction = buy_score / total_signal_strength
            sell_conviction = sell_score / total_signal_strength
            conviction_difference = abs(buy_conviction - sell_conviction)
            
            # Analyze market conditions for context
            volatility = market_data.get("volatility_5m", 0.001)
            trend_strength = market_data.get("trend_analysis", {}).get("alignment_score", 0.5)
            
            # Dynamic threshold based on market conditions
            # In high volatility, need higher conviction
            # In strong trends, can act on lower conviction
            base_threshold = 0.15  # Base conviction threshold
            volatility_adjustment = volatility * 50  # Higher vol = higher threshold
            trend_adjustment = (1.0 - trend_strength) * 0.1  # Stronger trend = lower threshold
            dynamic_threshold = base_threshold + volatility_adjustment - trend_adjustment
            
            # Make intelligent decision based on conviction and market context
            if buy_conviction > sell_conviction and conviction_difference > dynamic_threshold:
                return "BUY"
            elif sell_conviction > buy_conviction and conviction_difference > dynamic_threshold:
                return "SELL"
            else:
                # Analyze if we should wait for better setup
                if conviction_difference < dynamic_threshold * 0.5:
                    return "HOLD"  # Too close to call
                else:
                    # Some conviction but not enough - could be a weak signal
                    return "HOLD"
                
        except Exception as e:
            logger.error(f"❌ Failed to determine direction: {e}")
            return "HOLD"
    
    
    def _calculate_trading_parameters(self, direction: str, current_price: float, 
                                    market_data: Dict[str, Any], signal_analysis: Dict[str, Any], strategy: str = "standard") -> Dict[str, Any]:
        """Calculate trading parameters based on market analysis, risk assessment, and strategy"""
        try:
            # Get account balance from market data or use default
            account_balance = market_data.get("account_balance", 455.0)
            
            # Strategy-specific parameter calculation
            if strategy == "scalping":
                return self._calculate_scalping_parameters(direction, current_price, market_data, signal_analysis, account_balance)
            elif strategy == "trend_following":
                return self._calculate_trend_parameters(direction, current_price, market_data, signal_analysis, account_balance)
            elif strategy == "high_volatility":
                return self._calculate_high_vol_parameters(direction, current_price, market_data, signal_analysis, account_balance)
            else:
                # Default/standard strategy parameters
                return self._calculate_standard_parameters(direction, current_price, market_data, signal_analysis, account_balance)
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate trading parameters: {e}")
            return {
                "entry_price": current_price,
                "size_btc": 0.0,
                "size_usd": 0.0,
                "stop_loss": current_price,
                "target_price": current_price
            }
    
    def _calculate_scalping_parameters(self, direction: str, current_price: float, market_data: Dict[str, Any], 
                                     signal_analysis: Dict[str, Any], account_balance: float) -> Dict[str, Any]:
        """Calculate scalping-specific trading parameters using hybrid position sizing"""
        try:
            from core.ml.hybrid_position_sizer import hybrid_position_sizer
            
            # Use hybrid position sizing system
            position_result = hybrid_position_sizer.calculate_optimal_position_size(
                direction=direction,
                current_price=current_price,
                market_data=market_data,
                signal_analysis=signal_analysis,
                account_balance=account_balance,
                strategy="scalping"
            )
            
            return {
                "entry_price": current_price,  # Will be calculated by hybrid system
                "size_btc": position_result.position_size_btc,
                "size_usd": position_result.position_size_usd,
                "stop_loss": position_result.stop_loss,
                "target_price": position_result.target_price,
                "leverage": position_result.leverage,
                "risk_percent": position_result.final_risk_percent
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate scalping parameters: {e}")
            return self._get_default_parameters(direction, current_price, account_balance)
    
    def _calculate_trend_parameters(self, direction: str, current_price: float, market_data: Dict[str, Any], 
                                  signal_analysis: Dict[str, Any], account_balance: float) -> Dict[str, Any]:
        """Calculate trend-following specific trading parameters using hybrid position sizing"""
        try:
            from core.ml.hybrid_position_sizer import hybrid_position_sizer
            
            # Use hybrid position sizing system
            position_result = hybrid_position_sizer.calculate_optimal_position_size(
                direction=direction,
                current_price=current_price,
                market_data=market_data,
                signal_analysis=signal_analysis,
                account_balance=account_balance,
                strategy="trend_following"
            )
            
            return {
                "entry_price": current_price,  # Will be calculated by hybrid system
                "size_btc": position_result.position_size_btc,
                "size_usd": position_result.position_size_usd,
                "stop_loss": position_result.stop_loss,
                "target_price": position_result.target_price,
                "leverage": position_result.leverage,
                "risk_percent": position_result.final_risk_percent
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate trend parameters: {e}")
            return self._get_default_parameters(direction, current_price, account_balance)
    
    def _calculate_high_vol_parameters(self, direction: str, current_price: float, market_data: Dict[str, Any], 
                                     signal_analysis: Dict[str, Any], account_balance: float) -> Dict[str, Any]:
        """Calculate high volatility specific trading parameters using hybrid position sizing"""
        try:
            from core.ml.hybrid_position_sizer import hybrid_position_sizer
            
            # Use hybrid position sizing system
            position_result = hybrid_position_sizer.calculate_optimal_position_size(
                direction=direction,
                current_price=current_price,
                market_data=market_data,
                signal_analysis=signal_analysis,
                account_balance=account_balance,
                strategy="high_volatility"
            )
            
            return {
                "entry_price": current_price,  # Will be calculated by hybrid system
                "size_btc": position_result.position_size_btc,
                "size_usd": position_result.position_size_usd,
                "stop_loss": position_result.stop_loss,
                "target_price": position_result.target_price,
                "leverage": position_result.leverage,
                "risk_percent": position_result.final_risk_percent
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate high vol parameters: {e}")
            return self._get_default_parameters(direction, current_price, account_balance)
    
    def _calculate_standard_parameters(self, direction: str, current_price: float, market_data: Dict[str, Any], 
                                     signal_analysis: Dict[str, Any], account_balance: float) -> Dict[str, Any]:
        """Calculate standard trading parameters using hybrid position sizing"""
        try:
            from core.ml.hybrid_position_sizer import hybrid_position_sizer
            
            # Use hybrid position sizing system
            position_result = hybrid_position_sizer.calculate_optimal_position_size(
                direction=direction,
                current_price=current_price,
                market_data=market_data,
                signal_analysis=signal_analysis,
                account_balance=account_balance,
                strategy="standard"
            )
            
            return {
                "entry_price": current_price,  # Will be calculated by hybrid system
                "size_btc": position_result.position_size_btc,
                "size_usd": position_result.position_size_usd,
                "stop_loss": position_result.stop_loss,
                "target_price": position_result.target_price,
                "leverage": position_result.leverage,
                "risk_percent": position_result.final_risk_percent
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate standard parameters: {e}")
            return self._get_default_parameters(direction, current_price, account_balance)
    
    def _cleanup_old_predictions(self):
        """Remove old predictions"""
        try:
            current_time = time.time()
            
            # Remove expired predictions
            expired_ids = [
                pred_id for pred_id, prediction in self.active_predictions.items()
                if current_time - prediction.timestamp > self.max_prediction_age
            ]
            
            for pred_id in expired_ids:
                prediction = self.active_predictions.pop(pred_id)
                self.prediction_history.append(prediction)
                logger.debug(f"🗑️ Expired prediction: {prediction.direction} (age: {current_time - prediction.timestamp:.0f}s)")
            
            # Limit concurrent predictions
            if len(self.active_predictions) > self.max_concurrent_predictions:
                # Remove oldest predictions
                sorted_predictions = sorted(
                    self.active_predictions.items(),
                    key=lambda x: x[1].timestamp
                )
                
                excess_count = len(self.active_predictions) - self.max_concurrent_predictions
                for i in range(excess_count):
                    pred_id, prediction = sorted_predictions[i]
                    self.active_predictions.pop(pred_id)
                    self.prediction_history.append(prediction)
                    logger.debug(f"🗑️ Removed excess prediction: {prediction.direction}")
            
            # Limit history size
            if len(self.prediction_history) > self.max_history:
                self.prediction_history = self.prediction_history[-self.max_history:]
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old predictions: {e}")
    
    def get_highest_confidence_prediction(self) -> Optional[TradingPrediction]:
        """Get the prediction with the highest confidence"""
        try:
            if not self.active_predictions:
                return None
            
            highest_confidence_pred = max(
                self.active_predictions.values(),
                key=lambda p: p.confidence
            )
            
            return highest_confidence_pred
            
        except Exception as e:
            logger.error(f"❌ Failed to get highest confidence prediction: {e}")
            return None
    
    def get_all_active_predictions(self) -> List[TradingPrediction]:
        """Get all active predictions sorted by confidence"""
        try:
            return sorted(
                self.active_predictions.values(),
                key=lambda p: p.confidence,
                reverse=True
            )
        except Exception as e:
            logger.error(f"❌ Failed to get active predictions: {e}")
            return []
    
    def remove_prediction(self, prediction_id: str) -> bool:
        """Remove a specific prediction"""
        try:
            if prediction_id in self.active_predictions:
                prediction = self.active_predictions.pop(prediction_id)
                self.prediction_history.append(prediction)
                logger.info(f"🗑️ Removed prediction: {prediction.direction} (confidence: {prediction.confidence:.2f})")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Failed to remove prediction: {e}")
            return False
    
    def get_prediction_stats(self) -> Dict[str, Any]:
        """Get prediction statistics"""
        try:
            active_count = len(self.active_predictions)
            history_count = len(self.prediction_history)
            
            if active_count > 0:
                avg_confidence = sum(p.confidence for p in self.active_predictions.values()) / active_count
                directions = [p.direction for p in self.active_predictions.values()]
                direction_counts = {d: directions.count(d) for d in set(directions)}
            else:
                avg_confidence = 0.0
                direction_counts = {}
            
            return {
                "active_predictions": active_count,
                "history_count": history_count,
                "avg_confidence": avg_confidence,
                "direction_counts": direction_counts,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get prediction stats: {e}")
            return {
                "active_predictions": 0,
                "history_count": 0,
                "avg_confidence": 0.0,
                "direction_counts": {},
                "timestamp": time.time()
            }
    
    def _calculate_entry_price(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> float:
        """Calculate entry price for limit orders based on reversal points and market conditions"""
        try:
            # PRIORITY 1: Look for reversal points first
            reversal_entry = self._find_reversal_entry_point(direction, current_price, market_data)
            if reversal_entry:
                logger.info(f"🎯 Using reversal entry point: ${reversal_entry:.2f} for {direction}")
                return reversal_entry
            
            # PRIORITY 2: Look for support/resistance levels
            sr_entry = self._find_sr_entry_point(direction, current_price, market_data)
            if sr_entry:
                logger.info(f"🎯 Using S/R entry point: ${sr_entry:.2f} for {direction}")
                return sr_entry
            
            # PRIORITY 3: Use psychological levels
            psych_entry = self._find_psychological_entry_point(direction, current_price, market_data)
            if psych_entry:
                logger.info(f"🎯 Using psychological entry point: ${psych_entry:.2f} for {direction}")
                return psych_entry
            
            # FALLBACK: Small adjustment from current price
            if direction == "BUY":
                entry_price = current_price * 0.999  # 0.1% below current
            elif direction == "SELL":
                entry_price = current_price * 1.001  # 0.1% above current
            else:
                entry_price = current_price
                
            logger.info(f"🎯 Using fallback entry point: ${entry_price:.2f} for {direction}")
            return entry_price
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate entry price: {e}")
            # Fallback to current price with small adjustment
            if direction == "BUY":
                return current_price * 0.999
            elif direction == "SELL":
                return current_price * 1.001
            else:
                return current_price
    
    def _find_reversal_entry_point(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> Optional[float]:
        """Find entry price based on reversal patterns and signals"""
        try:
            # Check for reversal patterns
            pattern_data = market_data.get("pattern_analysis", {})
            reversal_patterns = pattern_data.get("reversal_patterns", [])
            
            if reversal_patterns:
                for pattern in reversal_patterns:
                    pattern_type = pattern.get("pattern", "")
                    confidence = pattern.get("confidence", 0.0)
                    pattern_high = pattern.get("pattern_high", 0)
                    pattern_low = pattern.get("pattern_low", 0)
                    
                    # Only use high-confidence reversal patterns
                    if confidence < 0.7:
                        continue
                    
                    if direction == "BUY":
                        # Look for bullish reversal patterns
                        if pattern_type in ["DOUBLE_BOTTOM", "INVERSE_HEAD_SHOULDERS", "FALLING_WEDGE"]:
                            # Entry at the reversal point (pattern low)
                            if pattern_low > 0 and pattern_low < current_price:
                                return pattern_low
                    
                    elif direction == "SELL":
                        # Look for bearish reversal patterns
                        if pattern_type in ["DOUBLE_TOP", "HEAD_SHOULDERS", "RISING_WEDGE"]:
                            # Entry at the reversal point (pattern high)
                            if pattern_high > 0 and pattern_high > current_price:
                                return pattern_high
            
            # Check for RSI reversal signals
            rsi = market_data.get("rsi", 50.0)
            if direction == "BUY" and rsi < 30:  # Oversold reversal
                # Entry slightly above the oversold level
                return current_price * 0.998  # 0.2% below current for oversold reversal
            elif direction == "SELL" and rsi > 70:  # Overbought reversal
                # Entry slightly below the overbought level
                return current_price * 1.002  # 0.2% above current for overbought reversal
            
            # Check for trend reversal signals
            trend_analysis = market_data.get("trend_analysis", {})
            trend_strength = trend_analysis.get("strength", 0.5)
            overall_trend = trend_analysis.get("overall_trend", "NEUTRAL")
            
            # Look for trend exhaustion (strong trend losing momentum)
            if trend_strength > 0.8 and direction != overall_trend:
                # Trend is strong but we're betting against it (reversal play)
                if direction == "BUY" and overall_trend == "BEARISH":
                    return current_price * 0.997  # 0.3% below for bearish reversal
                elif direction == "SELL" and overall_trend == "BULLISH":
                    return current_price * 1.003  # 0.3% above for bullish reversal
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Reversal entry point detection failed: {e}")
            return None
    
    def _find_sr_entry_point(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> Optional[float]:
        """Find entry price based on support/resistance levels"""
        try:
            sr_data = market_data.get("support_resistance", {})
            support_levels = sr_data.get("key_levels", [])
            
            if direction == "BUY":
                # Look for support levels below current price
                support_below = [level for level in support_levels 
                               if level.get("type") == "support" and level.get("level", 0) < current_price]
                
                if support_below:
                    # Use the highest support level below current price
                    best_support = max(support_below, key=lambda x: x.get("level", 0))
                    return best_support.get("level", None)
                    
            elif direction == "SELL":
                # Look for resistance levels above current price
                resistance_above = [level for level in support_levels 
                                  if level.get("type") == "resistance" and level.get("level", 0) > current_price]
                
                if resistance_above:
                    # Use the lowest resistance level above current price
                    best_resistance = min(resistance_above, key=lambda x: x.get("level", 0))
                    return best_resistance.get("level", None)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ S/R entry point detection failed: {e}")
            return None
    
    def _find_psychological_entry_point(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> Optional[float]:
        """Find entry price based on psychological levels"""
        try:
            # Get psychological levels
            psych_data = market_data.get("psychological_levels", {})
            nearest_levels = psych_data.get("nearest_levels", {})
            
            if direction == "BUY":
                # Look for psychological support levels
                support_levels = [
                    nearest_levels.get("strong_support"),
                    nearest_levels.get("moderate_support")
                ]
                
                for level_data in support_levels:
                    if level_data and level_data.get("level", 0) < current_price:
                        return level_data.get("level", None)
                        
            elif direction == "SELL":
                # Look for psychological resistance levels
                resistance_levels = [
                    nearest_levels.get("strong_resistance"),
                    nearest_levels.get("moderate_resistance")
                ]
                
                for level_data in resistance_levels:
                    if level_data and level_data.get("level", 0) > current_price:
                        return level_data.get("level", None)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Psychological entry point detection failed: {e}")
            return None
    
    def _calculate_win_probability(self, individual_signals: Dict[str, Any], market_data: Dict[str, Any], entry_price: float = None, current_price: float = None) -> float:
        """
        Calculate the actual win probability (confidence) based on:
        1. Historical performance of similar signal combinations
        2. Market conditions and volatility
        3. Signal strength and alignment
        4. Risk factors
        5. Time-based factors
        6. Market microstructure factors
        7. Execution quality factors
        """
        try:
            # CORE LOGIC: Base confidence from entry price proximity probability
            entry_proximity_probability = self._calculate_entry_proximity_probability(entry_price, current_price, market_data)
            
            # Base win probability from historical data (secondary factor)
            base_win_rate = self._get_historical_win_rate(individual_signals, market_data)
            
            # Adjust for current market conditions
            market_adjustment = self._calculate_market_adjustment(market_data)
            
            # Adjust for signal alignment
            alignment_adjustment = self._calculate_signal_alignment(individual_signals)
            
            # Adjust for risk factors
            risk_adjustment = self._calculate_risk_adjustment(market_data)
            
            # NEW: Time-based factors
            time_adjustment = self._calculate_time_adjustment(market_data)
            
            # NEW: Market microstructure factors
            microstructure_adjustment = self._calculate_microstructure_adjustment(market_data)
            
            # NEW: Execution quality factors
            execution_adjustment = self._calculate_execution_adjustment(market_data, entry_price, current_price)
            
            # Calculate final win probability with entry proximity as primary factor
            # Entry proximity is the core probability, other factors are adjustments
            win_probability = (entry_proximity_probability * market_adjustment * alignment_adjustment * 
                             risk_adjustment * time_adjustment * microstructure_adjustment * 
                             execution_adjustment)
            
            # Ensure it's within realistic bounds (0.1 to 0.95)
            win_probability = max(0.1, min(0.95, win_probability))
            
            logger.debug(f"🎯 Win probability calculation: entry_proximity={entry_proximity_probability:.3f}, "
                        f"market={market_adjustment:.3f}, alignment={alignment_adjustment:.3f}, "
                        f"risk={risk_adjustment:.3f}, time={time_adjustment:.3f}, "
                        f"microstructure={microstructure_adjustment:.3f}, execution={execution_adjustment:.3f}, "
                        f"final={win_probability:.3f}")
            
            return win_probability
            
        except Exception as e:
            logger.error(f"❌ Win probability calculation failed: {e}")
            return 0.5  # Default to 50% if calculation fails
    
    def _calculate_entry_proximity_probability(self, entry_price: float, current_price: float, market_data: Dict[str, Any]) -> float:
        """
        Calculate base confidence based on probability that current price will reach entry price and reverse
        
        Args:
            entry_price: The predicted entry price (e.g., support/resistance level)
            current_price: Current market price
            market_data: Market data including volatility, momentum, etc.
            
        Returns:
            Probability (0.0 to 1.0) that price will reach entry and reverse
        """
        try:
            if not entry_price or not current_price or entry_price <= 0:
                return 0.5  # Default if no valid entry price
            
            # Calculate distance percentage
            distance_percent = abs(current_price - entry_price) / current_price
            
            # Base probability from distance (closer = higher probability)
            if distance_percent < 0.001:  # Within 0.1% - very close
                base_probability = 0.9
            elif distance_percent < 0.005:  # Within 0.5% - close
                base_probability = 0.8
            elif distance_percent < 0.01:  # Within 1% - moderate
                base_probability = 0.7
            elif distance_percent < 0.02:  # Within 2% - far
                base_probability = 0.5
            else:  # More than 2% - very far
                base_probability = 0.3
            
            # Adjust for market momentum (is price moving toward or away from entry?)
            momentum = market_data.get("price_momentum", 0.0)
            volatility = market_data.get("volatility_5m", 0.001)
            
            # If price is moving toward entry, increase probability
            # If price is moving away from entry, decrease probability
            if current_price > entry_price:  # Price above entry (for BUY at support)
                if momentum < 0:  # Price falling toward support
                    momentum_boost = abs(momentum) * 0.2  # Up to 20% boost
                else:  # Price rising away from support
                    momentum_penalty = momentum * 0.1  # Up to 10% penalty
                    momentum_boost = -momentum_penalty
            else:  # Price below entry (for SELL at resistance)
                if momentum > 0:  # Price rising toward resistance
                    momentum_boost = momentum * 0.2  # Up to 20% boost
                else:  # Price falling away from resistance
                    momentum_penalty = abs(momentum) * 0.1  # Up to 10% penalty
                    momentum_boost = -momentum_penalty
            
            # Adjust for volatility (higher volatility = more likely to reach entry)
            volatility_adjustment = min(0.2, volatility * 20)  # Up to 20% boost for high volatility
            
            # Calculate final probability
            final_probability = base_probability + momentum_boost + volatility_adjustment
            
            # Ensure it's within realistic bounds
            final_probability = max(0.1, min(0.95, final_probability))
            
            logger.debug(f"🎯 Entry proximity probability: distance={distance_percent:.4f}, "
                        f"base={base_probability:.3f}, momentum_boost={momentum_boost:.3f}, "
                        f"volatility_adj={volatility_adjustment:.3f}, final={final_probability:.3f}")
            
            return final_probability
            
        except Exception as e:
            logger.error(f"❌ Entry proximity probability calculation failed: {e}")
            return 0.5  # Default to 50% if calculation fails
    
    def update_prediction_confidence(self, prediction: Dict[str, Any], current_price: float, market_data: Dict[str, Any]) -> float:
        """
        Update prediction confidence based on how well the market is following the predicted direction
        Only applies during AI's predicted timeframe
        
        Args:
            prediction: Current prediction dictionary
            current_price: Current market price
            market_data: Current market data
            
        Returns:
            Updated confidence value
        """
        try:
            direction = prediction.get("direction", "BUY")
            entry_price = prediction.get("entry_price", 0)
            initial_confidence = prediction.get("confidence", 0.5)
            
            # Calculate how well the market is following the prediction
            market_behavior_score = self._calculate_market_behavior_score(
                direction, entry_price, current_price, market_data
            )
            
            # NEW: Check for conflicting signals and signal reinforcement
            signal_analysis = self._analyze_signal_alignment(direction, market_data)
            signal_conflict_penalty = signal_analysis["conflict_penalty"]
            signal_reinforcement_boost = signal_analysis["reinforcement_boost"]
            
            # Adjust confidence based on market behavior and signal alignment
            # If market is behaving as predicted, increase confidence
            # If market is going against prediction, decrease confidence
            # If signals conflict with prediction, decrease confidence
            # If signals reinforce prediction, increase confidence
            behavior_adjustment = 0.5 + (market_behavior_score * 0.5)  # 0.5 to 1.0 multiplier
            conflict_adjustment = 1.0 - signal_conflict_penalty  # 0.0 to 1.0 multiplier
            reinforcement_adjustment = 1.0 + signal_reinforcement_boost  # 1.0 to 1.3 multiplier
            
            updated_confidence = initial_confidence * behavior_adjustment * conflict_adjustment * reinforcement_adjustment
            
            # Ensure confidence stays within reasonable bounds
            updated_confidence = max(0.1, min(0.95, updated_confidence))
            
            # Update the prediction
            prediction["confidence"] = updated_confidence
            
            logger.debug(f"🔄 Updated prediction confidence: {updated_confidence:.3f} "
                        f"(behavior: {market_behavior_score:.3f}, conflict: {signal_conflict_penalty:.3f}, "
                        f"reinforcement: {signal_reinforcement_boost:.3f}, behavior_adj: {behavior_adjustment:.3f}, "
                        f"conflict_adj: {conflict_adjustment:.3f}, reinforcement_adj: {reinforcement_adjustment:.3f})")
            
            return updated_confidence
            
        except Exception as e:
            logger.error(f"❌ Failed to update prediction confidence: {e}")
            return prediction.get("confidence", 0.5)
    
    def _analyze_signal_alignment(self, prediction_direction: str, market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Analyze signal alignment with prediction direction, tracking processed signals
        
        Args:
            prediction_direction: BUY or SELL
            market_data: Current market data with signals
            
        Returns:
            Dictionary with conflict_penalty and reinforcement_boost
        """
        try:
            # Get current signals from market data
            current_signals = market_data.get("current_signals", {})
            
            if not current_signals:
                return {"conflict_penalty": 0.0, "reinforcement_boost": 0.0}
            
            # Get previously processed signals for this prediction
            prediction_id = market_data.get("prediction_id", "unknown")
            processed_signals = self._get_processed_signals(prediction_id)
            
            # Analyze new signals only
            new_buy_signals = 0
            new_sell_signals = 0
            new_neutral_signals = 0
            total_new_signals = 0
            
            for signal_type, signal_data in current_signals.items():
                if isinstance(signal_data, dict) and "direction" in signal_data:
                    # Create signal identifier
                    signal_id = f"{signal_type}_{signal_data.get('timestamp', time.time())}"
                    
                    # Skip if already processed
                    if signal_id in processed_signals:
                        continue
                    
                    direction = signal_data["direction"]
                    confidence = signal_data.get("confidence", 0.5)
                    weight = signal_data.get("weight", 1.0)
                    
                    # Weight the signal by its confidence and weight
                    signal_strength = confidence * weight
                    total_new_signals += signal_strength
                    
                    if direction == "BUY":
                        new_buy_signals += signal_strength
                    elif direction == "SELL":
                        new_sell_signals += signal_strength
                    else:  # NEUTRAL
                        new_neutral_signals += signal_strength
                    
                    # Mark signal as processed
                    self._mark_signal_processed(prediction_id, signal_id)
            
            if total_new_signals == 0:
                return {"conflict_penalty": 0.0, "reinforcement_boost": 0.0}
            
            # Calculate new signal distribution
            new_buy_ratio = new_buy_signals / total_new_signals
            new_sell_ratio = new_sell_signals / total_new_signals
            new_neutral_ratio = new_neutral_signals / total_new_signals
            
            # Calculate conflict penalty and reinforcement boost
            if prediction_direction == "BUY":
                # For BUY predictions: penalty from new SELL signals, boost from new BUY signals
                conflict_penalty = new_sell_ratio * 0.3  # 0.0 to 0.3 penalty
                reinforcement_boost = new_buy_ratio * 0.2  # 0.0 to 0.2 boost
                
                # Extra penalty if new SELL signals are stronger than new BUY
                if new_sell_ratio > new_buy_ratio:
                    conflict_penalty += (new_sell_ratio - new_buy_ratio) * 0.2
                    
            else:  # SELL prediction
                # For SELL predictions: penalty from new BUY signals, boost from new SELL signals
                conflict_penalty = new_buy_ratio * 0.3  # 0.0 to 0.3 penalty
                reinforcement_boost = new_sell_ratio * 0.2  # 0.0 to 0.2 boost
                
                # Extra penalty if new BUY signals are stronger than new SELL
                if new_buy_ratio > new_sell_ratio:
                    conflict_penalty += (new_buy_ratio - new_sell_ratio) * 0.2
            
            # Cap the values
            conflict_penalty = min(0.5, conflict_penalty)
            reinforcement_boost = min(0.3, reinforcement_boost)
            
            logger.debug(f"🔍 Signal alignment analysis: pred={prediction_direction}, "
                        f"new_buy={new_buy_ratio:.3f}, new_sell={new_sell_ratio:.3f}, "
                        f"new_neutral={new_neutral_ratio:.3f}, conflict={conflict_penalty:.3f}, "
                        f"reinforcement={reinforcement_boost:.3f}")
            
            return {
                "conflict_penalty": conflict_penalty,
                "reinforcement_boost": reinforcement_boost
            }
            
        except Exception as e:
            logger.error(f"❌ Signal alignment analysis failed: {e}")
            return {"conflict_penalty": 0.0, "reinforcement_boost": 0.0}
    
    def _get_processed_signals(self, prediction_id: str) -> set:
        """Get set of processed signal IDs for a prediction"""
        try:
            if not hasattr(self, 'processed_signals'):
                self.processed_signals = {}
            
            return self.processed_signals.get(prediction_id, set())
            
        except Exception as e:
            logger.error(f"❌ Failed to get processed signals: {e}")
            return set()
    
    def _mark_signal_processed(self, prediction_id: str, signal_id: str):
        """Mark a signal as processed for a prediction"""
        try:
            if not hasattr(self, 'processed_signals'):
                self.processed_signals = {}
            
            if prediction_id not in self.processed_signals:
                self.processed_signals[prediction_id] = set()
            
            self.processed_signals[prediction_id].add(signal_id)
            
            # Clean up old processed signals (keep only last 50 per prediction)
            if len(self.processed_signals[prediction_id]) > 50:
                # Remove oldest signals (simple cleanup)
                signals_list = list(self.processed_signals[prediction_id])
                self.processed_signals[prediction_id] = set(signals_list[-50:])
            
        except Exception as e:
            logger.error(f"❌ Failed to mark signal as processed: {e}")
    
    def transfer_confidence_to_trade(self, prediction: Dict[str, Any], trade_id: str) -> float:
        """
        Transfer confidence from prediction to trade when order is filled
        
        Args:
            prediction: The prediction that led to the trade
            trade_id: The trade ID
            
        Returns:
            Initial trade confidence
        """
        try:
            # Get the final confidence from the prediction
            trade_confidence = prediction.get("confidence", 0.5)
            
            # Store the confidence transfer for learning
            self._store_confidence_transfer(prediction, trade_id, trade_confidence)
            
            logger.info(f"🔄 Confidence transferred: prediction → trade {trade_id} = {trade_confidence:.3f}")
            
            return trade_confidence
            
        except Exception as e:
            logger.error(f"❌ Failed to transfer confidence to trade: {e}")
            return 0.5
    
    def _store_confidence_transfer(self, prediction: Dict[str, Any], trade_id: str, confidence: float):
        """Store confidence transfer data for learning"""
        try:
            transfer_data = {
                "trade_id": trade_id,
                "prediction_id": prediction.get("prediction_id", "unknown"),
                "initial_confidence": confidence,
                "prediction_signals": prediction.get("signal_strength", {}),
                "prediction_reasoning": prediction.get("reasoning", ""),
                "timestamp": time.time()
            }
            
            # Store in learning data
            if not hasattr(self, 'confidence_transfers'):
                self.confidence_transfers = []
            
            self.confidence_transfers.append(transfer_data)
            
            logger.debug(f"📊 Stored confidence transfer: trade {trade_id} = {confidence:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store confidence transfer: {e}")
    
    def analyze_trade_quality_on_close(self, trade_data: Dict[str, Any], 
                                     market_timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze trade quality when trade is closed and update learning
        
        Args:
            trade_data: Completed trade data
            market_timeline: Price data from entry to close
            
        Returns:
            Quality analysis results
        """
        try:
            from core.ml.trade_quality_analyzer import trade_quality_analyzer
            
            # Analyze trade quality
            quality_metrics = trade_quality_analyzer.analyze_trade_quality(
                trade_data, market_timeline
            )
            
            # Update learning based on quality analysis
            self._update_learning_from_trade_quality(trade_data, quality_metrics)
            
            logger.info(f"📊 Trade quality analysis complete: {quality_metrics.overall_quality:.1%} quality, {quality_metrics.perfect_trade_score:.1%} perfect score")
            
            return {
                "quality_metrics": quality_metrics,
                "learning_insights": quality_metrics.learning_insights,
                "analysis_complete": True
            }
            
        except Exception as e:
            logger.error(f"❌ Trade quality analysis failed: {e}")
            return {"analysis_complete": False, "error": str(e)}
    
    def _update_learning_from_trade_quality(self, trade_data: Dict[str, Any], 
                                          quality_metrics) -> None:
        """Update AI learning based on trade quality analysis"""
        try:
            # Store quality data for learning
            if not hasattr(self, 'trade_quality_history'):
                self.trade_quality_history = []
            
            quality_data = {
                "trade_id": trade_data.get("trade_id", "unknown"),
                "timestamp": time.time(),
                "quality_metrics": {
                    "direction_accuracy": quality_metrics.direction_accuracy,
                    "entry_timing_accuracy": quality_metrics.entry_timing_accuracy,
                    "take_profit_accuracy": quality_metrics.take_profit_accuracy,
                    "stop_loss_accuracy": quality_metrics.stop_loss_accuracy,
                    "profit_efficiency": quality_metrics.profit_efficiency,
                    "overall_quality": quality_metrics.overall_quality,
                    "perfect_trade_score": quality_metrics.perfect_trade_score
                },
                "learning_insights": quality_metrics.learning_insights
            }
            
            self.trade_quality_history.append(quality_data)
            
            # Update signal weights based on performance
            self._update_signal_weights_from_quality(quality_metrics)
            
            # Update confidence thresholds based on performance
            self._update_confidence_thresholds_from_quality(quality_metrics)
            
            logger.debug(f"🧠 Updated learning from trade quality: {quality_metrics.overall_quality:.1%} quality")
            
        except Exception as e:
            logger.error(f"❌ Failed to update learning from trade quality: {e}")
    
    def _update_signal_weights_from_quality(self, quality_metrics) -> None:
        """Update signal weights based on trade quality performance"""
        try:
            # If trade was high quality, increase weights for signals that performed well
            if quality_metrics.overall_quality > 0.8:
                # Increase weights for well-performing signals
                logger.debug("📈 High quality trade - increasing signal weights")
            elif quality_metrics.overall_quality < 0.3:
                # Decrease weights for poorly-performing signals
                logger.debug("📉 Low quality trade - decreasing signal weights")
            
            # This would integrate with the signal aggregator to adjust weights
            
        except Exception as e:
            logger.error(f"❌ Failed to update signal weights: {e}")
    
    def _update_confidence_thresholds_from_quality(self, quality_metrics) -> None:
        """Update confidence thresholds based on trade quality performance"""
        try:
            # If trades are consistently high quality, we can lower thresholds
            # If trades are consistently low quality, we should raise thresholds
            
            if quality_metrics.perfect_trade_score > 0.9:
                # Perfect trade - we can be more aggressive
                logger.debug("🎯 Perfect trade - considering lower confidence thresholds")
            elif quality_metrics.perfect_trade_score < 0.3:
                # Poor trade - we should be more conservative
                logger.debug("⚠️ Poor trade - considering higher confidence thresholds")
            
            # This would integrate with the execution layer to adjust thresholds
            
        except Exception as e:
            logger.error(f"❌ Failed to update confidence thresholds: {e}")
    
    def _calculate_market_behavior_score(self, direction: str, entry_price: float, current_price: float, market_data: Dict[str, Any]) -> float:
        """
        Calculate how well the market is behaving according to the prediction
        Only applies during AI's predicted timeframe
        
        Returns:
            Score from 0.0 (completely wrong) to 1.0 (perfectly following prediction)
        """
        try:
            # Check if we're still within AI's predicted timeframe
            predicted_time_to_entry = market_data.get("predicted_time_to_entry_seconds", 300)
            time_elapsed = market_data.get("prediction_age_seconds", 0)
            
            # If we've exceeded the predicted timeframe, don't adjust based on price movement
            if time_elapsed > predicted_time_to_entry:
                logger.debug(f"🎯 Exceeded predicted timeframe: {time_elapsed}s/{predicted_time_to_entry}s, no price movement adjustments")
                return 0.5  # Neutral score - no adjustments
            
            # During predicted timeframe - calculate market behavior score
            if direction == "BUY":
                # For BUY: current price should be moving towards entry price from below
                if current_price <= entry_price:
                    # Price is at or below entry - good for BUY
                    price_score = 1.0
                else:
                    # Price is above entry - not ideal for BUY
                    price_score = max(0.0, 1.0 - ((current_price - entry_price) / entry_price) * 2)
            else:  # SELL
                # For SELL: current price should be moving towards entry price from above
                if current_price >= entry_price:
                    # Price is at or above entry - good for SELL
                    price_score = 1.0
                else:
                    # Price is below entry - not ideal for SELL
                    price_score = max(0.0, 1.0 - ((entry_price - current_price) / entry_price) * 2)
            
            # Also consider recent price momentum (only during predicted timeframe)
            recent_momentum = market_data.get("price_momentum", 0.0)
            momentum_score = 0.5 + (recent_momentum * 0.5) if direction == "BUY" else 0.5 - (recent_momentum * 0.5)
            momentum_score = max(0.0, min(1.0, momentum_score))
            
            # Combine price and momentum scores
            behavior_score = (price_score * 0.7) + (momentum_score * 0.3)
            
            logger.debug(f"🎯 Market behavior (within timeframe): direction={direction}, price_score={price_score:.3f}, momentum_score={momentum_score:.3f}, final={behavior_score:.3f}")
            
            return behavior_score
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate market behavior score: {e}")
            return 0.5  # Neutral score if calculation fails
    
    def _calculate_time_adjustment(self, market_data: Dict[str, Any]) -> float:
        """Calculate time-based confidence adjustment based on AI's predicted entry timeframe"""
        try:
            import time
            
            # Get AI's predicted timeframe for entry
            predicted_time_to_entry = market_data.get("predicted_time_to_entry_seconds", 300)  # Default 5 minutes
            time_elapsed = market_data.get("prediction_age_seconds", 0)
            
            # Market session factor (always applies)
            session_factor = self._get_session_factor()
            
            # Check if we're still within AI's predicted timeframe
            if time_elapsed <= predicted_time_to_entry:
                # During AI's predicted timeframe - no time decay, just session factor
                time_adjustment = session_factor
                logger.debug(f"⏰ Within predicted timeframe: {time_elapsed}s/{predicted_time_to_entry}s, session={session_factor:.3f}")
            else:
                # After AI's predicted timeframe - apply time decay
                time_overdue = time_elapsed - predicted_time_to_entry
                decay_factor = max(0.1, 1.0 - (time_overdue / (predicted_time_to_entry * 2)))  # 50% decay after 2x predicted time
                time_adjustment = session_factor * decay_factor
                logger.debug(f"⏰ Exceeded predicted timeframe: {time_elapsed}s/{predicted_time_to_entry}s, overdue={time_overdue}s, decay={decay_factor:.3f}")
            
            return max(0.1, min(1.2, time_adjustment))
            
        except Exception as e:
            logger.error(f"❌ Time adjustment calculation failed: {e}")
            return 1.0
    
    def _calculate_microstructure_adjustment(self, market_data: Dict[str, Any]) -> float:
        """Calculate market microstructure confidence adjustment"""
        try:
            # Bid-ask spread factor
            spread = market_data.get("bid_ask_spread", 0.0)
            spread_factor = max(0.5, 1.0 - (spread / 0.001))  # Penalty for wide spreads
            
            # Market depth factor
            depth = market_data.get("market_depth", 0.0)
            depth_factor = min(1.2, depth / 10.0)  # Boost for deep markets
            
            # Order flow factor
            order_flow = market_data.get("order_flow_imbalance", 0.0)
            flow_factor = 0.8 + (abs(order_flow) * 0.4)  # Boost for strong order flow
            
            # Liquidity factor
            liquidity = market_data.get("liquidity_score", 0.5)
            liquidity_factor = 0.5 + liquidity  # 0.5 to 1.5 range
            
            # Combine microstructure factors
            microstructure_adjustment = (spread_factor * 0.3) + (depth_factor * 0.3) + (flow_factor * 0.2) + (liquidity_factor * 0.2)
            
            logger.debug(f"🔬 Microstructure: spread={spread_factor:.3f}, depth={depth_factor:.3f}, flow={flow_factor:.3f}, liquidity={liquidity_factor:.3f}, final={microstructure_adjustment:.3f}")
            
            return max(0.4, min(1.3, microstructure_adjustment))
            
        except Exception as e:
            logger.error(f"❌ Microstructure adjustment calculation failed: {e}")
            return 1.0
    
    def _calculate_execution_adjustment(self, market_data: Dict[str, Any], entry_price: float, current_price: float) -> float:
        """Calculate execution quality confidence adjustment"""
        try:
            # Slippage risk factor
            slippage_risk = market_data.get("slippage_risk", 0.0)
            slippage_factor = max(0.6, 1.0 - (slippage_risk * 2))  # Penalty for high slippage risk
            
            # Execution speed factor
            execution_speed = market_data.get("execution_speed_ms", 1000)
            speed_factor = max(0.7, 1.0 - (execution_speed / 5000))  # Penalty for slow execution
            
            # Market impact factor
            market_impact = market_data.get("market_impact", 0.0)
            impact_factor = max(0.8, 1.0 - (market_impact * 5))  # Penalty for high market impact
            
            # Fill probability factor
            fill_probability = market_data.get("fill_probability", 0.8)
            fill_factor = 0.5 + (fill_probability * 0.5)  # 0.5 to 1.0 range
            
            # Entry price distance factor (closer = better execution)
            distance_factor = 1.0
            if entry_price and current_price:
                price_distance = abs(entry_price - current_price) / current_price
                distance_factor = max(0.7, 1.0 - (price_distance * 10))  # Penalty for far entry points
            
            # Combine execution factors
            execution_adjustment = (slippage_factor * 0.25) + (speed_factor * 0.25) + (impact_factor * 0.25) + (fill_factor * 0.15) + (distance_factor * 0.1)
            
            logger.debug(f"⚡ Execution: slippage={slippage_factor:.3f}, speed={speed_factor:.3f}, impact={impact_factor:.3f}, fill={fill_factor:.3f}, distance={distance_factor:.3f}, final={execution_adjustment:.3f}")
            
            return max(0.5, min(1.2, execution_adjustment))
            
        except Exception as e:
            logger.error(f"❌ Execution adjustment calculation failed: {e}")
            return 1.0
    
    def _get_session_factor(self) -> float:
        """Get market session confidence factor"""
        try:
            import datetime
            
            current_hour = datetime.datetime.now().hour
            
            # Asian session (0-8 UTC) - Lower volatility, more predictable
            if 0 <= current_hour < 8:
                return 1.1
            # European session (8-16 UTC) - Good volatility, reliable
            elif 8 <= current_hour < 16:
                return 1.0
            # US session (16-24 UTC) - High volatility, more unpredictable
            elif 16 <= current_hour < 24:
                return 0.9
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"❌ Session factor calculation failed: {e}")
            return 1.0
    
    def _get_historical_win_rate(self, signals: Dict[str, Any], market_data: Dict[str, Any]) -> float:
        """Get historical win rate for similar signal combinations"""
        try:
            # For now, use a simplified approach based on signal strength
            # In a real system, this would query historical performance data
            
            signal_strengths = []
            for signal_name, signal_data in signals.items():
                if isinstance(signal_data, dict) and "confidence" in signal_data:
                    signal_strengths.append(signal_data["confidence"])
            
            if not signal_strengths:
                return 0.5  # Default 50% if no signals
            
            # Average signal strength as base win rate
            avg_strength = sum(signal_strengths) / len(signal_strengths)
            
            # Convert to win rate (0.3-0.8 range)
            base_win_rate = 0.3 + (avg_strength * 0.5)
            
            return base_win_rate
            
        except Exception as e:
            logger.error(f"❌ Historical win rate calculation failed: {e}")
            return 0.5
    
    def _calculate_market_adjustment(self, market_data: Dict[str, Any]) -> float:
        """Adjust win probability based on current market conditions"""
        try:
            adjustment = 1.0
            
            # Volatility adjustment
            volatility_category = market_data.get("volatility_5m_category", "MODERATE")
            if volatility_category == "VERY_LOW":
                adjustment *= 0.9  # Lower win rate in boring markets
            elif volatility_category == "LOW":
                adjustment *= 0.95
            elif volatility_category == "HIGH":
                adjustment *= 1.1  # Higher win rate in volatile markets
            elif volatility_category == "EXTREME":
                adjustment *= 1.2  # Much higher win rate in extreme volatility
            
            # Volume adjustment
            volume_category = market_data.get("trading_volume_category", "NORMAL")
            if volume_category == "VERY_LOW":
                adjustment *= 0.85  # Lower win rate with low volume
            elif volume_category == "HIGH":
                adjustment *= 1.05  # Higher win rate with high volume
            
            # Trend strength adjustment
            trend_analysis = market_data.get("trend_analysis", {})
            trend_strength = trend_analysis.get("strength", 0.5)
            if trend_strength > 0.7:  # Strong trend
                adjustment *= 1.1
            elif trend_strength < 0.3:  # Weak trend
                adjustment *= 0.9
            
            return max(0.5, min(1.5, adjustment))  # Clamp between 0.5x and 1.5x
            
        except Exception as e:
            logger.error(f"❌ Market adjustment calculation failed: {e}")
            return 1.0
    
    def _calculate_signal_alignment(self, signals: Dict[str, Any]) -> float:
        """Adjust win probability based on signal alignment"""
        try:
            if not signals:
                return 0.8  # Lower confidence with no signals
            
            # Count signals by direction
            buy_signals = 0
            sell_signals = 0
            neutral_signals = 0
            
            for signal_name, signal_data in signals.items():
                if isinstance(signal_data, dict) and "signal" in signal_data:
                    signal_direction = signal_data["signal"]
                    if signal_direction == "BUY":
                        buy_signals += 1
                    elif signal_direction == "SELL":
                        sell_signals += 1
                    else:
                        neutral_signals += 1
            
            total_signals = buy_signals + sell_signals + neutral_signals
            if total_signals == 0:
                return 0.8
            
            # Calculate alignment (how many signals agree)
            max_direction = max(buy_signals, sell_signals, neutral_signals)
            alignment_ratio = max_direction / total_signals
            
            # Convert to adjustment factor (0.7 to 1.3)
            alignment_adjustment = 0.7 + (alignment_ratio * 0.6)
            
            return alignment_adjustment
            
        except Exception as e:
            logger.error(f"❌ Signal alignment calculation failed: {e}")
            return 1.0
    
    def _calculate_risk_adjustment(self, market_data: Dict[str, Any]) -> float:
        """Adjust win probability based on risk factors"""
        try:
            adjustment = 1.0
            
            # RSI risk adjustment
            rsi = market_data.get("rsi", 50.0)
            if rsi < 20 or rsi > 80:  # Extreme RSI
                adjustment *= 0.9  # Slightly lower confidence in extreme conditions
            
            # Support/Resistance risk
            sr_data = market_data.get("support_resistance", {})
            if sr_data:
                current_price = market_data.get("current_price", 0)
                support_levels = sr_data.get("support_levels", [])
                resistance_levels = sr_data.get("resistance_levels", [])
                
                # Check if price is near key levels (higher risk)
                for level in support_levels + resistance_levels:
                    level_price = level.get("level", 0)
                    if level_price > 0:
                        distance = abs(current_price - level_price) / current_price
                        if distance < 0.01:  # Within 1% of key level
                            adjustment *= 0.95  # Slightly lower confidence near key levels
            
            # Volatility risk
            volatility_5m = market_data.get("volatility_5m", 0.0)
            if volatility_5m > 0.01:  # High volatility
                adjustment *= 0.9  # Lower confidence in high volatility
            
            return max(0.7, min(1.2, adjustment))  # Clamp between 0.7x and 1.2x
            
        except Exception as e:
            logger.error(f"❌ Risk adjustment calculation failed: {e}")
            return 1.0

# Global instance
global_prediction_manager = PredictionManager()
