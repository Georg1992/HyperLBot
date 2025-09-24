#!/usr/bin/env python3
"""
Clean Prediction Manager
========================
Refactored prediction engine with clean architecture and advanced entry price calculation.

ARCHITECTURE:
1. Base Confidence = Probability Theory + Global Market Conditions
2. Signal Multipliers = All other signals (RSI, volume, volatility, etc.)
3. Strategy-Specific Thresholds = Different confidence requirements per strategy
4. Advanced Entry Price = Reversal detection, S/R, psychological levels
5. Single Active Prediction = Replace existing prediction, evolve or discard
"""

import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from loguru import logger

@dataclass
class TradingPrediction:
    """Clean trading prediction structure"""
    prediction_id: str
    direction: str  # BUY/SELL
    entry_price: float
    target_price: float
    stop_loss: float
    size_btc: float
    leverage: float
    
    # Clean confidence system
    base_confidence: float  # Probability theory + global market conditions
    signal_multiplier: float  # All other signals as multipliers
    market_multiplier: float  # Market conditions as multipliers
    final_confidence: float  # Final calculated confidence
    
    # Entry price details
    entry_reasoning: str  # Why this entry price was chosen
    entry_strength: float  # Strength of the entry level (0.0-1.0)
    
    # Prediction metadata
    strategy: str
    timestamp: float
    is_active: bool = True
    is_discarded: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TradingPrediction to dictionary"""
        return {
            "prediction_id": self.prediction_id,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "size_btc": self.size_btc,
            "leverage": self.leverage,
            "base_confidence": self.base_confidence,
            "signal_multiplier": self.signal_multiplier,
            "market_multiplier": self.market_multiplier,
            "final_confidence": self.final_confidence,
            "confidence": self.final_confidence,  # Add confidence field for dashboard compatibility
            "entry_reasoning": self.entry_reasoning,
            "entry_strength": self.entry_strength,
            "reasoning": self.entry_reasoning,  # Add reasoning field for dashboard compatibility
            "strategy": self.strategy,
            "timestamp": self.timestamp,
            "is_active": self.is_active,
            "is_discarded": self.is_discarded
        }

class PredictionManager:
    """
    Clean prediction manager with single active prediction and advanced entry price calculation
    """
    
    def __init__(self):
        self.current_prediction: Optional[TradingPrediction] = None
        self.prediction_history: List[TradingPrediction] = []
        
        # Strategy-specific confidence thresholds
        self.strategy_thresholds = {
            "scalping": 0.55,        # Lower threshold - quick trades
            "trend_following": 0.65,  # Medium threshold - trend-based
            "range_trading": 0.60,    # Medium threshold - range-based
            "liquidation_hunting": 0.70,  # Higher threshold - high-risk strategy
            "spike_hunting": 0.75,   # High threshold - volatile strategy
            "standard": 0.60         # Default threshold
        }
        
        logger.info("🧠 Clean Prediction Manager initialized")
    
    def generate_prediction(self, current_price: float, market_data: Dict[str, Any], 
                          global_conditions: Dict[str, Any], strategy: str = "standard") -> Optional[TradingPrediction]:
        """
        Generate a new trading prediction using clean architecture
        
        Args:
            current_price: Current market price
            market_data: Comprehensive market data
            global_conditions: Global market conditions (7-day trend, etc.)
            strategy: Trading strategy name
            
        Returns:
            TradingPrediction or None if no valid prediction
        """
        try:
            logger.debug(f"🧠 Generating prediction for {strategy} strategy")
            
            # 1. CALCULATE BASE CONFIDENCE (Probability Theory + Global Market Conditions)
            base_confidence = self._calculate_base_confidence(market_data, global_conditions)
            # Always generate prediction, even with low confidence
            if base_confidence < 0.3:
                logger.debug(f"📊 Low base confidence: {base_confidence:.3f} - will use forced direction if needed")
            
            # 2. DETERMINE DIRECTION
            direction = self._determine_direction(market_data, global_conditions)
            forced_direction = False
            if direction not in ["BUY", "SELL"]:
                # Force a direction based on available signals with low confidence
                direction = self._force_direction_from_signals(market_data, global_conditions)
                forced_direction = True
                logger.debug(f"📊 Forced direction: {direction} (low confidence)")
            
            # 3. CALCULATE ADVANCED ENTRY PRICE
            entry_price, entry_reasoning, entry_strength = self._calculate_entry_price(
                direction, current_price, market_data
            )
            if not entry_price or not self._validate_entry_price(direction, entry_price, current_price):
                logger.debug(f"📊 Invalid entry price: {entry_price}")
                return None
            
            # 4. CALCULATE TARGET AND STOP LOSS
            target_price, stop_loss = self._calculate_target_and_stop_loss(
                direction, entry_price, current_price, market_data
            )
            
            # 5. CALCULATE POSITION SIZE
            size_btc, leverage = self._calculate_position_size(
                entry_price, target_price, stop_loss, market_data, strategy
            )
            
            # 6. CALCULATE SIGNAL MULTIPLIERS
            signal_multiplier = self._calculate_signal_multipliers(market_data)
            
            # 7. CALCULATE MARKET CONDITIONS MULTIPLIER
            market_multiplier = self._calculate_market_conditions_multiplier(global_conditions, direction)
            
            # 8. CALCULATE FINAL CONFIDENCE
            final_confidence = base_confidence * signal_multiplier * market_multiplier
            
            # If this was a forced direction, reduce confidence significantly
            if forced_direction:
                final_confidence *= 0.3  # Reduce confidence to 30% of calculated value
                logger.debug(f"📊 Forced direction confidence reduced: {final_confidence:.3f}")
            
            final_confidence = min(1.0, max(0.0, final_confidence))
            
            # 9. CREATE PREDICTION
            prediction = TradingPrediction(
                prediction_id=str(uuid.uuid4()),
                direction=direction,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                size_btc=size_btc,
                leverage=leverage,
                base_confidence=base_confidence,
                signal_multiplier=signal_multiplier,
                market_multiplier=market_multiplier,
                final_confidence=final_confidence,
                entry_reasoning=entry_reasoning,
                entry_strength=entry_strength,
                strategy=strategy,
                timestamp=time.time()
            )
            
            # 10. REPLACE CURRENT PREDICTION (single active prediction)
            self.current_prediction = prediction
            
            logger.info(f"🎯 Generated {direction} prediction: Entry=${entry_price:.2f}, "
                       f"Target=${target_price:.2f}, Stop=${stop_loss:.2f}, "
                       f"Confidence={final_confidence:.3f}")
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Prediction generation failed: {e}")
            return None
    
    def update_prediction_confidence(self, current_price: float, market_data: Dict[str, Any], 
                                   global_conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update current prediction confidence based on real-time market behavior
        
        Returns:
            Dict with execution decision or None if prediction continues
        """
        try:
            if not self.current_prediction or self.current_prediction.is_discarded:
                return None
            
            # Update signal multipliers
            signal_multiplier = self._calculate_signal_multipliers(market_data)
            
            # Update market conditions multiplier
            market_multiplier = self._calculate_market_conditions_multiplier(
                global_conditions, self.current_prediction.direction
            )
            
            # Recalculate final confidence
            final_confidence = (
                self.current_prediction.base_confidence * 
                signal_multiplier * 
                market_multiplier
            )
            final_confidence = min(1.0, max(0.0, final_confidence))
            
            # Update prediction
            self.current_prediction.signal_multiplier = signal_multiplier
            self.current_prediction.market_multiplier = market_multiplier
            self.current_prediction.final_confidence = final_confidence
            
            # Check strategy-specific threshold
            threshold = self.strategy_thresholds.get(self.current_prediction.strategy, 0.60)
            
            if final_confidence >= threshold:
                # Execute prediction
                self.current_prediction.is_active = False
                return {
                    "action": "execute",
                    "prediction": self.current_prediction,
                    "confidence": final_confidence,
                    "threshold": threshold
                }
            elif final_confidence < 0.3:
                # Discard prediction
                self.current_prediction.is_discarded = True
                self.current_prediction.is_active = False
                self.prediction_history.append(self.current_prediction)
                self.current_prediction = None
                return {
                    "action": "discard",
                    "reason": "confidence_too_low",
                    "confidence": final_confidence
                }
            
            # Continue monitoring
            return {
                "action": "continue",
                "confidence": final_confidence,
                "threshold": threshold
            }
            
        except Exception as e:
            logger.error(f"❌ Prediction confidence update failed: {e}")
            return None
    
    def _calculate_base_confidence(self, market_data: Dict[str, Any], global_conditions: Dict[str, Any]) -> float:
        """
        Calculate base confidence using probability theory + global market conditions
        """
        try:
            # 1. STATISTICAL PROBABILITY (Historical performance of similar setups)
            statistical_probability = self._calculate_statistical_probability(market_data)
            
            # 2. GLOBAL MARKET CONDITIONS MULTIPLIER
            global_multiplier = self._calculate_global_market_multiplier(global_conditions)
            
            # 3. BASE CONFIDENCE = Statistical probability adjusted for global conditions
            base_confidence = statistical_probability * global_multiplier
            
            logger.debug(f"📊 Base confidence: {statistical_probability:.3f} * {global_multiplier:.3f} = {base_confidence:.3f}")
            
            return base_confidence
            
        except Exception as e:
            logger.error(f"❌ Base confidence calculation failed: {e}")
            return 0.0
    
    def _calculate_statistical_probability(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate statistical probability based on historical performance of similar setups
        """
        try:
            # Get signal strength and alignment
            signal_strength = self._calculate_signal_strength(market_data)
            signal_alignment = self._calculate_signal_alignment(market_data)
            
            # Calculate probability based on signal quality
            probability = (signal_strength * 0.6) + (signal_alignment * 0.4)
            
            # Adjust for market volatility (higher volatility = lower probability)
            volatility = market_data.get("volatility_5m", 0.0)
            volatility_adjustment = max(0.7, 1.0 - (volatility * 10))  # Penalty for high volatility
            
            probability *= volatility_adjustment
            
            return min(0.95, max(0.1, probability))
            
        except Exception as e:
            logger.error(f"❌ Statistical probability calculation failed: {e}")
            return 0.5  # Default neutral probability
    
    def _calculate_global_market_multiplier(self, global_conditions: Dict[str, Any]) -> float:
        """
        Calculate global market conditions multiplier
        """
        try:
            multiplier = 1.0
            
            # 7-day market trend
            market_status = global_conditions.get("market_status", "NEUTRAL")
            if market_status == "BULLISH":
                multiplier *= 1.1  # Slight boost for bullish market
            elif market_status == "BEARISH":
                multiplier *= 0.9  # Slight penalty for bearish market
            
            # Market quality
            quality = global_conditions.get("condition", "FAIR")
            quality_multipliers = {
                "EXCELLENT": 1.2,
                "GOOD": 1.1,
                "FAIR": 1.0,
                "POOR": 0.8
            }
            multiplier *= quality_multipliers.get(quality, 1.0)
            
            # Risk level
            risk_level = global_conditions.get("risk_level", "MODERATE")
            risk_multipliers = {
                "LOW": 1.1,
                "MODERATE": 1.0,
                "HIGH": 0.9,
                "EXTREME": 0.8
            }
            multiplier *= risk_multipliers.get(risk_level, 1.0)
            
            return min(1.5, max(0.5, multiplier))  # Clamp between 0.5 and 1.5
            
        except Exception as e:
            logger.error(f"❌ Global market multiplier calculation failed: {e}")
            return 1.0
    
    def _calculate_entry_price(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> Tuple[Optional[float], str, float]:
        """
        Calculate advanced entry price using reversal detection, S/R, and psychological levels
        """
        try:
            # PRIORITY 1: Reversal patterns
            reversal_entry, reversal_reasoning, reversal_strength = self._find_reversal_entry(
                direction, current_price, market_data
            )
            if reversal_entry and reversal_strength > 0.7:
                return reversal_entry, f"Reversal: {reversal_reasoning}", reversal_strength
            
            # PRIORITY 2: Support/Resistance with volume confirmation
            sr_entry, sr_reasoning, sr_strength = self._find_sr_entry(
                direction, current_price, market_data
            )
            if sr_entry and sr_strength > 0.6:
                return sr_entry, f"S/R: {sr_reasoning}", sr_strength
            
            # PRIORITY 3: Psychological levels
            psych_entry, psych_reasoning, psych_strength = self._find_psychological_entry(
                direction, current_price, market_data
            )
            if psych_entry and psych_strength > 0.4:
                return psych_entry, f"Psychological: {psych_reasoning}", psych_strength
            
            # FALLBACK: Volatility-based entry
            fallback_entry, fallback_reasoning = self._calculate_fallback_entry(
                direction, current_price, market_data
            )
            if fallback_entry:
                return fallback_entry, f"Volatility: {fallback_reasoning}", 0.3
            
            return None, "No valid entry point found", 0.0
            
        except Exception as e:
            logger.error(f"❌ Entry price calculation failed: {e}")
            return None, f"Error: {str(e)}", 0.0
    
    def _find_reversal_entry(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> Tuple[Optional[float], str, float]:
        """Find entry point based on reversal patterns"""
        try:
            # Check for reversal patterns
            pattern_data = market_data.get("pattern_analysis", {})
            reversal_patterns = pattern_data.get("reversal_patterns", [])
            
            if reversal_patterns:
                for pattern in reversal_patterns:
                    pattern_type = pattern.get("pattern", "")
                    confidence = pattern.get("confidence", 0.0)
                    pattern_price = pattern.get("price", 0.0)
                    
                    if confidence > 0.8 and pattern_price > 0:
                        # Validate direction alignment
                        if ((direction == "BUY" and pattern_type in ["HAMMER", "DOJI", "BULLISH_ENGULFING"]) or
                            (direction == "SELL" and pattern_type in ["SHOOTING_STAR", "BEARISH_ENGULFING"])):
                            
                            if self._validate_entry_price(direction, pattern_price, current_price):
                                return pattern_price, f"{pattern_type} reversal (confidence: {confidence:.2f})", confidence
            
            # Check for RSI reversal signals
            rsi = market_data.get("rsi", 50.0)
            if direction == "BUY" and rsi < 30:  # Oversold
                volatility = market_data.get("volatility_5m", 0.0)
                reversal_entry = current_price * (1 - volatility * 0.5)
                
                if self._validate_entry_price(direction, reversal_entry, current_price):
                    return reversal_entry, f"RSI oversold reversal (RSI: {rsi:.1f})", 0.7
            
            elif direction == "SELL" and rsi > 70:  # Overbought
                volatility = market_data.get("volatility_5m", 0.0)
                reversal_entry = current_price * (1 + volatility * 0.5)
                
                if self._validate_entry_price(direction, reversal_entry, current_price):
                    return reversal_entry, f"RSI overbought reversal (RSI: {rsi:.1f})", 0.7
            
            return None, "No reversal detected", 0.0
            
        except Exception as e:
            logger.error(f"❌ Reversal detection failed: {e}")
            return None, f"Error: {str(e)}", 0.0
    
    def _find_sr_entry(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> Tuple[Optional[float], str, float]:
        """Find entry point based on support/resistance levels"""
        try:
            sr_data = market_data.get("support_resistance", {})
            key_levels = sr_data.get("key_levels", [])
            
            if not key_levels:
                return None, "No S/R levels", 0.0
            
            # Get volume data for confirmation
            volume_data = market_data.get("volume_data", {})
            volume_category = volume_data.get("volume_category", "NORMAL")
            
            if direction == "BUY":
                support_levels = [level for level in key_levels 
                                if level.get("type") == "support" and level.get("level", 0) < current_price]
                support_levels.sort(key=lambda x: x.get("score", 0), reverse=True)
                
                for level in support_levels:
                    level_price = level.get("level", 0)
                    level_score = level.get("score", 0)
                    
                    if level_score > 0.6 and self._validate_entry_price(direction, level_price, current_price):
                        # Volume confirmation
                        volume_multiplier = 1.0
                        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
                            volume_multiplier = 1.2
                        
                        strength = level_score * volume_multiplier
                        return level_price, f"Support with volume confirmation (score: {level_score:.2f})", min(0.9, strength)
            
            elif direction == "SELL":
                resistance_levels = [level for level in key_levels 
                                  if level.get("type") == "resistance" and level.get("level", 0) > current_price]
                resistance_levels.sort(key=lambda x: x.get("score", 0), reverse=True)
                
                for level in resistance_levels:
                    level_price = level.get("level", 0)
                    level_score = level.get("score", 0)
                    
                    if level_score > 0.6 and self._validate_entry_price(direction, level_price, current_price):
                        # Volume confirmation
                        volume_multiplier = 1.0
                        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
                            volume_multiplier = 1.2
                        
                        strength = level_score * volume_multiplier
                        return level_price, f"Resistance with volume confirmation (score: {level_score:.2f})", min(0.9, strength)
            
            return None, "No strong S/R levels", 0.0
            
        except Exception as e:
            logger.error(f"❌ S/R entry detection failed: {e}")
            return None, f"Error: {str(e)}", 0.0
    
    def _find_psychological_entry(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> Tuple[Optional[float], str, float]:
        """Find entry point based on psychological levels"""
        try:
            psych_data = market_data.get("psychological_levels", {})
            nearest_levels = psych_data.get("nearest_levels", {})
            
            if not nearest_levels:
                return None, "No psychological levels", 0.0
            
            trend = market_data.get("trend", "NEUTRAL")
            volatility = market_data.get("volatility_5m", 0.0)
            
            if direction == "BUY":
                support_levels = [
                    nearest_levels.get("strong_support"),
                    nearest_levels.get("moderate_support"),
                    nearest_levels.get("weak_support")
                ]
                
                for level in support_levels:
                    if level and level < current_price:
                        distance_pct = (current_price - level) / current_price
                        if distance_pct < 0.02:  # Within 2%
                            if self._validate_entry_price(direction, level, current_price):
                                strength = 0.4
                                if trend == "DOWNTREND":
                                    strength += 0.2
                                if volatility > 0.001:
                                    strength += 0.1
                                
                                return level, f"Psychological support (trend: {trend})", min(0.7, strength)
            
            elif direction == "SELL":
                resistance_levels = [
                    nearest_levels.get("strong_resistance"),
                    nearest_levels.get("moderate_resistance"),
                    nearest_levels.get("weak_resistance")
                ]
                
                for level in resistance_levels:
                    if level and level > current_price:
                        distance_pct = (level - current_price) / current_price
                        if distance_pct < 0.02:  # Within 2%
                            if self._validate_entry_price(direction, level, current_price):
                                strength = 0.4
                                if trend == "UPTREND":
                                    strength += 0.2
                                if volatility > 0.001:
                                    strength += 0.1
                                
                                return level, f"Psychological resistance (trend: {trend})", min(0.7, strength)
            
            return None, "No psychological opportunities", 0.0
            
        except Exception as e:
            logger.error(f"❌ Psychological entry detection failed: {e}")
            return None, f"Error: {str(e)}", 0.0
    
    def _calculate_fallback_entry(self, direction: str, current_price: float, market_data: Dict[str, Any]) -> Tuple[Optional[float], str]:
        """Calculate fallback entry price based on volatility and market conditions"""
        try:
            volatility = market_data.get("volatility_5m", 0.001)
            rsi = market_data.get("rsi_5m", 50)
            trend = market_data.get("trend_5m", "NEUTRAL")
            volume = market_data.get("volume_5m", 0)
            
            # Build comprehensive reasoning
            reasoning_parts = []
            
            # Volatility analysis
            if volatility < 0.001:
                reasoning_parts.append("Low volatility market")
            elif volatility > 0.01:
                reasoning_parts.append("High volatility market")
            else:
                reasoning_parts.append("Moderate volatility market")
            
            # RSI analysis
            if rsi < 30:
                reasoning_parts.append("Oversold conditions (RSI<30)")
            elif rsi > 70:
                reasoning_parts.append("Overbought conditions (RSI>70)")
            elif 40 <= rsi <= 60:
                reasoning_parts.append("Neutral RSI conditions")
            
            # Trend analysis
            if trend == "UP":
                reasoning_parts.append("Uptrend detected")
            elif trend == "DOWN":
                reasoning_parts.append("Downtrend detected")
            else:
                reasoning_parts.append("Sideways market")
            
            # Volume analysis
            if volume > 0:
                reasoning_parts.append(f"Volume: {volume:.0f}")
            
            # Combine reasoning
            comprehensive_reasoning = " | ".join(reasoning_parts)
            
            if direction == "BUY":
                entry_price = current_price * (1 - volatility * 0.5)
                if self._validate_entry_price(direction, entry_price, current_price):
                    return entry_price, f"Comprehensive analysis: {comprehensive_reasoning}"
            
            elif direction == "SELL":
                entry_price = current_price * (1 + volatility * 0.5)
                if self._validate_entry_price(direction, entry_price, current_price):
                    return entry_price, f"Comprehensive analysis: {comprehensive_reasoning}"
            
            return None, "No fallback entry possible"
            
        except Exception as e:
            logger.error(f"❌ Fallback entry calculation failed: {e}")
            return None, f"Error: {str(e)}"
    
    def _validate_entry_price(self, direction: str, entry_price: float, current_price: float) -> bool:
        """Validate that entry price makes sense for the direction"""
        try:
            if direction == "BUY":
                return entry_price < current_price
            elif direction == "SELL":
                return entry_price > current_price
            return False
        except Exception as e:
            logger.error(f"❌ Entry price validation failed: {e}")
            return False
    
    def _determine_direction(self, market_data: Dict[str, Any], global_conditions: Dict[str, Any]) -> str:
        """Determine trading direction based on signals and market conditions"""
        try:
            buy_signals = 0
            sell_signals = 0
            
            # RSI signals
            rsi = market_data.get("rsi", 50.0)
            if rsi < 35:
                buy_signals += 2
            elif rsi > 65:
                sell_signals += 2
            elif rsi < 45:
                buy_signals += 1
            elif rsi > 55:
                sell_signals += 1
            
            # Trend signals
            trend = market_data.get("trend", "NEUTRAL")
            if trend in ["UPTREND", "STRONG_UPTREND"]:
                buy_signals += 1
            elif trend in ["DOWNTREND", "STRONG_DOWNTREND"]:
                sell_signals += 1
            
            # Pattern signals - reversal patterns are bullish, continuation patterns are bearish
            pattern_data = market_data.get("pattern_analysis", {})
            reversal_patterns = pattern_data.get("reversal_patterns", [])
            continuation_patterns = pattern_data.get("continuation_patterns", [])
            
            # Reversal patterns are bullish (price reversing from downtrend)
            buy_signals += len(reversal_patterns)
            # Continuation patterns are bearish (price continuing downtrend)
            sell_signals += len(continuation_patterns)
            
            # Global market conditions
            market_status = global_conditions.get("market_status", "NEUTRAL")
            if market_status == "BULLISH":
                buy_signals += 1
            elif market_status == "BEARISH":
                sell_signals += 1
            
            logger.debug(f"🔍 Direction signals: BUY={buy_signals}, SELL={sell_signals}")
            
            # Determine direction
            if buy_signals > sell_signals and buy_signals >= 2:
                return "BUY"
            elif sell_signals > buy_signals and sell_signals >= 2:
                return "SELL"
            else:
                return "NEUTRAL"
                
        except Exception as e:
            logger.error(f"❌ Direction determination failed: {e}")
            return "NEUTRAL"
    
    def _force_direction_from_signals(self, market_data: Dict[str, Any], global_conditions: Dict[str, Any]) -> str:
        """Force a direction when no clear signal is available - use weak signals with low confidence"""
        try:
            # Get basic market indicators
            rsi = market_data.get("rsi", 50)
            trend = market_data.get("trend_5m", "NEUTRAL")
            volatility = market_data.get("volatility_5m", 0.001)
            
            # Simple fallback logic
            if rsi < 40:  # Oversold
                return "BUY"
            elif rsi > 60:  # Overbought
                return "SELL"
            elif trend == "UP":
                return "BUY"
            elif trend == "DOWN":
                return "SELL"
            else:
                # Default to BUY with very low confidence
                return "BUY"
                
        except Exception as e:
            logger.error(f"❌ Force direction failed: {e}")
            return "BUY"  # Default fallback
    
    def _calculate_target_and_stop_loss(self, direction: str, entry_price: float, 
                                      current_price: float, market_data: Dict[str, Any]) -> Tuple[float, float]:
        """Calculate target price and stop loss"""
        try:
            volatility = market_data.get("volatility_5m", 0.001)
            
            if direction == "BUY":
                target_price = entry_price * (1 + volatility * 2)
                stop_loss = entry_price * (1 - volatility * 1)
            else:  # SELL
                target_price = entry_price * (1 - volatility * 2)
                stop_loss = entry_price * (1 + volatility * 1)
            
            return target_price, stop_loss
            
        except Exception as e:
            logger.error(f"❌ Target and stop loss calculation failed: {e}")
            return entry_price * 1.01, entry_price * 0.99
    
    def _calculate_position_size(self, entry_price: float, target_price: float, stop_loss: float, 
                               market_data: Dict[str, Any], strategy: str) -> Tuple[float, float]:
        """Calculate position size and leverage"""
        try:
            # Calculate risk/reward ratio
            if entry_price > 0:
                risk = abs(entry_price - stop_loss) / entry_price
                reward = abs(target_price - entry_price) / entry_price
                risk_reward = reward / risk if risk > 0 else 1.0
            else:
                risk_reward = 1.0
            
            # Base position size (1% of account)
            base_size = 0.01
            
            # Adjust for strategy
            strategy_multipliers = {
                "scalping": 0.5,
                "trend_following": 1.0,
                "range_trading": 0.8,
                "liquidation_hunting": 0.3,
                "spike_hunting": 0.4,
                "standard": 1.0
            }
            
            size_multiplier = strategy_multipliers.get(strategy, 1.0)
            size_btc = base_size * size_multiplier
            
            # Calculate leverage based on risk
            if risk < 0.01:
                leverage = 10.0
            elif risk < 0.02:
                leverage = 5.0
            else:
                leverage = 2.0
            
            return size_btc, leverage
            
        except Exception as e:
            logger.error(f"❌ Position size calculation failed: {e}")
            return 0.01, 5.0
    
    def _calculate_signal_multipliers(self, market_data: Dict[str, Any]) -> float:
        """Calculate signal multipliers for all other signals"""
        try:
            multiplier = 1.0
            
            # RSI multiplier
            rsi = market_data.get("rsi", 50.0)
            if isinstance(rsi, (int, float)):
                if rsi < 25 or rsi > 75:
                    multiplier *= 1.2
                elif rsi < 35 or rsi > 65:
                    multiplier *= 1.1
                elif 45 <= rsi <= 55:
                    multiplier *= 0.9
            
            # Volume multiplier - handle both dict and direct values
            volume_data = market_data.get("volume_data", {})
            if isinstance(volume_data, dict):
                volume_category = volume_data.get("volume_category", "NORMAL")
            else:
                # If volume_data is not a dict, treat it as a direct value
                volume_category = "NORMAL"
            
            if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
                multiplier *= 1.1
            elif volume_category in ["LOW", "VERY_LOW"]:
                multiplier *= 0.9
            
            # Volatility multiplier
            volatility = market_data.get("volatility_5m", 0.0)
            if isinstance(volatility, (int, float)):
                if 0.0005 <= volatility <= 0.002:
                    multiplier *= 1.1
                elif volatility > 0.005:
                    multiplier *= 0.8
                elif volatility < 0.0001:
                    multiplier *= 0.9
            
            # Trend multiplier
            trend = market_data.get("trend", "NEUTRAL")
            if isinstance(trend, str):
                if trend in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
                    multiplier *= 1.1
                elif trend == "SIDEWAYS":
                    multiplier *= 0.9
            
            return min(1.5, max(0.5, multiplier))
            
        except Exception as e:
            logger.error(f"❌ Signal multipliers calculation failed: {e}")
            return 1.0
    
    def _calculate_market_conditions_multiplier(self, global_conditions: Dict[str, Any], direction: str) -> float:
        """Calculate market conditions multiplier"""
        try:
            multiplier = 1.0
            
            # Market status alignment
            market_status = global_conditions.get("market_status", "NEUTRAL")
            if (market_status == "BULLISH" and direction == "BUY") or (market_status == "BEARISH" and direction == "SELL"):
                multiplier *= 1.2
            elif (market_status == "BEARISH" and direction == "BUY") or (market_status == "BULLISH" and direction == "SELL"):
                multiplier *= 0.8
            
            # Market quality
            quality = global_conditions.get("condition", "FAIR")
            quality_multipliers = {
                "EXCELLENT": 1.3,
                "GOOD": 1.1,
                "FAIR": 1.0,
                "POOR": 0.7
            }
            multiplier *= quality_multipliers.get(quality, 1.0)
            
            # Risk level
            risk_level = global_conditions.get("risk_level", "MODERATE")
            risk_multipliers = {
                "LOW": 1.2,
                "MODERATE": 1.0,
                "HIGH": 0.8,
                "EXTREME": 0.6
            }
            multiplier *= risk_multipliers.get(risk_level, 1.0)
            
            return min(1.5, max(0.5, multiplier))
            
        except Exception as e:
            logger.error(f"❌ Market conditions multiplier calculation failed: {e}")
            return 1.0
    
    def _calculate_signal_strength(self, market_data: Dict[str, Any]) -> float:
        """Calculate overall signal strength"""
        try:
            strength = 0.0
            count = 0
            
            # RSI strength
            rsi = market_data.get("rsi", 50.0)
            if rsi < 30 or rsi > 70:
                strength += 0.8
                count += 1
            elif rsi < 40 or rsi > 60:
                strength += 0.6
                count += 1
            
            # Trend strength
            trend = market_data.get("trend", "NEUTRAL")
            if "STRONG" in trend:
                strength += 0.9
                count += 1
            elif trend in ["UPTREND", "DOWNTREND"]:
                strength += 0.7
                count += 1
            
            # Pattern strength
            pattern_data = market_data.get("pattern_analysis", {})
            patterns = pattern_data.get("reversal_patterns", []) + pattern_data.get("continuation_patterns", [])
            if patterns:
                avg_confidence = sum(p.get("confidence", 0) for p in patterns) / len(patterns)
                strength += avg_confidence
                count += 1
            
            return strength / count if count > 0 else 0.5
            
        except Exception as e:
            logger.error(f"❌ Signal strength calculation failed: {e}")
            return 0.5
    
    def _calculate_signal_alignment(self, market_data: Dict[str, Any]) -> float:
        """Calculate signal alignment"""
        try:
            # This would analyze how well different signals align
            return 0.7
            
        except Exception as e:
            logger.error(f"❌ Signal alignment calculation failed: {e}")
            return 0.5
    
    def get_current_prediction(self) -> Optional[TradingPrediction]:
        """Get the current active prediction"""
        return self.current_prediction
    
    def get_prediction_history(self, limit: int = 10) -> List[TradingPrediction]:
        """Get prediction history"""
        return self.prediction_history[-limit:] if self.prediction_history else []
    
    def clear_current_prediction(self):
        """Clear the current prediction"""
        if self.current_prediction:
            self.current_prediction.is_active = False
            self.prediction_history.append(self.current_prediction)
            self.current_prediction = None

# Global instance
global_prediction_manager = PredictionManager()
