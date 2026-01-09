#!/usr/bin/env python3
"""
Prediction Engine
Generates trading predictions based on unified market data and current strategy
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal
from loguru import logger
from config.config import TradingConfig


@dataclass
class TradingPrediction:
    """Trading prediction/signal structure"""
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0.0 - 100.0 (percentage)
    reasoning: str
    strategy: str
    timestamp: float


class PredictionEngine:
    """
    Strategy-aware prediction engine
    
    Takes unified market data and generates trading predictions based on the current strategy.
    Each strategy has different requirements and logic for generating predictions.
    """
    
    def __init__(self):
        logger.info("🤖 Prediction Engine initialized")
    
    @staticmethod
    def _safe_get(data: Any, key: str, default: Any) -> Any:
        """Safely get value from dict, return default if not dict or key missing"""
        return data.get(key, default) if isinstance(data, dict) else default
    
    def generate_prediction(self, unified_data: Dict[str, Any], strategy: str) -> Optional[TradingPrediction]:
        """
        Generate a trading prediction based on unified data and strategy
        
        Args:
            unified_data: Complete market analysis data
            strategy: Current trading strategy name
            
        Returns:
            TradingPrediction if conditions are met, None otherwise
        """
        try:
            # Get strategy configuration
            strategy_config = TradingConfig.STRATEGY_CONFIGS.get(strategy)
            if not strategy_config:
                logger.warning(f"⚠️ Unknown strategy: {strategy}")
                return None
            
            # Get confidence threshold for this strategy
            confidence_threshold = strategy_config.get("confidence_threshold", 0.5)
            
            # Generate strategy-specific prediction
            prediction = self._generate_strategy_prediction(unified_data, strategy, strategy_config)
            
            # Always return prediction if generated (user wants to see highest confidence prediction always)
            if prediction:
                # Ensure timestamp is set
                if not prediction.timestamp:
                    prediction.timestamp = time.time()
                
                # Log prediction (always show, even if below threshold)
                confidence_threshold_pct = confidence_threshold * 100.0
                if prediction.confidence >= confidence_threshold_pct:
                    logger.info(f"✅ Prediction generated: {prediction.direction} @ ${prediction.entry_price:.2f} "
                              f"(confidence: {prediction.confidence:.1f}%, strategy: {strategy})")
                else:
                    logger.info(f"📊 Prediction generated (below threshold): {prediction.direction} @ ${prediction.entry_price:.2f} "
                              f"(confidence: {prediction.confidence:.1f}% < {confidence_threshold_pct:.1f}%, strategy: {strategy})")
                return prediction
            else:
                logger.debug(f"⏸️ No prediction generated for strategy: {strategy}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Prediction generation failed: {e}", exc_info=True)
            return None
    
    def _generate_strategy_prediction(
        self, 
        unified_data: Dict[str, Any], 
        strategy: str,
        strategy_config: Dict[str, Any]
    ) -> Optional[TradingPrediction]:
        """
        Generate prediction for specific strategy
        
        This is the foundation - strategy-specific logic will be implemented here
        """
        # Route to strategy-specific prediction method
        strategy_methods = {
            "standard": self._predict_standard,
            "scalping": self._predict_scalping,
            "swing_trading": self._predict_swing_trading,
            "trend_following": self._predict_trend_following,
            "breakout": self._predict_breakout,
            "range_trading": self._predict_range_trading,
            "low_volatility_range": self._predict_low_volatility_range,
            "high_volatility": self._predict_high_volatility,
            "spike_hunting": self._predict_spike_hunting,
        }
        
        method = strategy_methods.get(strategy, self._predict_standard)
        return method(unified_data, strategy_config)
    
    def _predict_standard(self, unified_data: Dict[str, Any], config: Dict[str, Any], strategy: str = "standard") -> Optional[TradingPrediction]:
        """
        Standard strategy prediction logic (also used as base for other strategies)
        
        This is the core prediction logic that:
        1. Determines direction using strategy-specific weights
        2. Determines entry price using strategy-specific preferences
        3. Calculates stop loss and take profit from config
        """
        # First, determine direction using strategy-specific weights
        direction_result = self._determine_direction(unified_data, strategy)
        if not direction_result:
            logger.debug(f"⏸️ No direction determined for {strategy} strategy")
            return None
        
        direction = direction_result["direction"]
        base_reasoning = direction_result["reasoning"]
        base_confidence = direction_result.get("confidence_pct", 50.0)
        
        # Determine best entry price using strategy-specific preferences
        entry_result = self._determine_entry_price(unified_data, direction, strategy, config)
        if not entry_result:
            logger.debug(f"⏸️ No entry price determined for {direction} direction ({strategy} strategy)")
            return None
        
        entry_price = entry_result["entry_price"]
        entry_confidence = entry_result["confidence"]
        entry_reasoning = entry_result["reasoning"]
        
        # Calculate stop_loss and take_profit from config
        stop_loss, take_profit = self._calculate_stop_and_target(
            entry_price, direction, config, unified_data
        )
        
        # Combine reasoning
        combined_reasoning = f"{base_reasoning}. Entry: {entry_reasoning}"
        
        # Final confidence is average of direction and entry confidence
        final_confidence = (base_confidence + entry_confidence) / 2.0
        
        return self._create_prediction(
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=final_confidence,
            reasoning=combined_reasoning,
            strategy=strategy
        )
    
    def _create_prediction(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        reasoning: str,
        strategy: str
    ) -> TradingPrediction:
        """Create a TradingPrediction object - single responsibility: prediction creation"""
        return TradingPrediction(
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reasoning=reasoning,
            strategy=strategy,
            timestamp=time.time()
        )
    
    def _predict_scalping(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """
        Scalping strategy prediction logic
        
        Scalping characteristics:
        - Very short timeframes (seconds to minutes)
        - Quick entries/exits (prefer current price)
        - Tight stops (0.2%) and targets (0.3%)
        - Focus on RSI (35%) and orderbook pressure (30%)
        - Requires tight spreads and high liquidity
        - Lower decision threshold (8.0 vs 10.0)
        """
        # Validate scalping-specific requirements
        if not self._validate_scalping_requirements(unified_data, config):
            return None
        
        # Use base prediction logic with scalping strategy
        prediction = self._predict_standard(unified_data, config, "scalping")
        
        # Override entry to current price (scalping preference for speed)
        if prediction:
            current_price = unified_data.get("current_price", 0.0)
            if current_price > 0:
                prediction.entry_price = current_price
                prediction.reasoning += ". Current price entry (scalping preference)"
        
        return prediction
    
    def _validate_scalping_requirements(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Validate scalping-specific requirements (spread, liquidity, RSI range)"""
        orderbook_data = unified_data.get("orderbook_analysis", {})
        
        # Check spread requirement
        spread_pct = orderbook_data.get("spread_pct", 1.0)
        spread_threshold = config.get("spread_threshold", 0.0001)
        if spread_pct > spread_threshold:
            logger.debug(f"⏸️ Spread too wide for scalping: {spread_pct*100:.4f}% > {spread_threshold*100:.4f}%")
            return False
        
        # Check liquidity requirement
        require_high_liquidity = config.get("require_high_liquidity", True)
        if require_high_liquidity:
            liquidity = orderbook_data.get("liquidity_score", 0.0)
            if liquidity < 0.5:
                logger.debug(f"⏸️ Insufficient liquidity for scalping: {liquidity:.2f}")
                return False
        
        # Check RSI range requirement
        rsi_data = unified_data.get("rsi", {})
        rsi_value = self._safe_get(rsi_data, "rsi", 50.0)
        rsi_range = config.get("rsi_range", [30, 70])
        if rsi_value < rsi_range[0] or rsi_value > rsi_range[1]:
            logger.debug(f"⏸️ RSI outside scalping range: {rsi_value:.1f} not in [{rsi_range[0]}, {rsi_range[1]}]")
            return False
        
        return True
    
    def _predict_swing_trading(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Swing trading strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "swing_trading")
    
    def _predict_trend_following(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Trend following strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "trend_following")
    
    def _predict_breakout(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Breakout strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "breakout")
    
    def _predict_range_trading(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Range trading strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "range_trading")
    
    def _predict_low_volatility_range(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Low volatility range strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "low_volatility_range")
    
    def _predict_high_volatility(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """High volatility strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "high_volatility")
    
    def _predict_spike_hunting(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Spike hunting strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "spike_hunting")
    
    def _determine_direction(self, unified_data: Dict[str, Any], strategy: str) -> Optional[Dict[str, Any]]:
        """
        Determine trade direction (LONG or SHORT) using all available market data
        
        Strategy-aware direction selection - each strategy weights indicators differently:
        - Scalping: RSI (35%), Pressure (30%), S/R (15%), Trend (10%)
        - Range Trading: S/R (40%), RSI (25%), Pressure (15%), Trend (10%)
        - Breakout: Patterns (30%), Volume (25%), Trend (20%), S/R (15%)
        - Trend Following: Trend (45%), RSI (20%), S/R (15%), Pressure (10%)
        - etc.
        
        Args:
            unified_data: Complete market analysis data
            strategy: Current trading strategy
            
        Returns:
            Dict with "direction" ("LONG" or "SHORT") and "reasoning" string, or None if unclear
        """
        try:
            current_price = unified_data.get("current_price", 0.0)
            if current_price <= 0:
                logger.warning("⚠️ Invalid current price for direction determination")
                return None
            
            # Get strategy-specific weights
            strategy_config = TradingConfig.STRATEGY_CONFIGS.get(strategy, {})
            direction_weights = strategy_config.get("direction_weights", {
                "rsi": 0.25,
                "trend": 0.25,
                "support_resistance": 0.20,
                "pressure": 0.15,
                "patterns": 0.10,
                "volume": 0.05,
                "funding": 0.05
            })
            min_score_diff = strategy_config.get("min_score_diff", 10.0)
            
            # Extract all indicators
            rsi_data = unified_data.get("rsi", {})
            trend_data = unified_data.get("trend", {})
            sr_data = unified_data.get("support_resistance", {})
            pressure_data = unified_data.get("pressure", {})
            patterns_data = unified_data.get("patterns", {})
            funding_data = unified_data.get("funding_analysis", {})
            
            # Initialize scoring
            long_score = 0.0
            short_score = 0.0
            reasons = []
            
            # 1. RSI Analysis
            rsi_weight = direction_weights.get("rsi", 0.0)
            if rsi_weight > 0:
                rsi_value = self._safe_get(rsi_data, "rsi", 50.0)
                rsi_trend = self._safe_get(rsi_data, "rsi_trend", "NEUTRAL")
                rsi_signal = self._safe_get(rsi_data, "rsi_signal", "NEUTRAL")
                
                # Base RSI score (0-100)
                rsi_long = 0.0
                rsi_short = 0.0
                
                if rsi_value < 30:  # Oversold - bullish
                    rsi_long = 100.0
                    reasons.append(f"RSI oversold ({rsi_value:.1f})")
                elif rsi_value > 70:  # Overbought - bearish
                    rsi_short = 100.0
                    reasons.append(f"RSI overbought ({rsi_value:.1f})")
                elif rsi_value < 50 and rsi_trend == "BULLISH":  # Below neutral but rising
                    rsi_long = 60.0
                    reasons.append(f"RSI recovering ({rsi_value:.1f}, {rsi_trend})")
                elif rsi_value > 50 and rsi_trend == "BEARISH":  # Above neutral but falling
                    rsi_short = 60.0
                    reasons.append(f"RSI declining ({rsi_value:.1f}, {rsi_trend})")
                
                if rsi_signal == "BULLISH":
                    rsi_long += 40.0
                    reasons.append("RSI bullish signal")
                elif rsi_signal == "BEARISH":
                    rsi_short += 40.0
                    reasons.append("RSI bearish signal")
                
                # Apply weight
                long_score += rsi_long * rsi_weight
                short_score += rsi_short * rsi_weight
            
            # 2. Trend Analysis - Strategy-aware timeframe weighting
            trend_weight = direction_weights.get("trend", 0.0)
            if trend_weight > 0:
                detailed_trends = self._safe_get(trend_data, "detailed_timeframes", {})
                
                # Strategy-specific timeframe preferences
                timeframe_weights = self._get_strategy_timeframe_weights(strategy)
                
                # Base trend score (0-100)
                trend_long = 0.0
                trend_short = 0.0
                
                # Analyze each timeframe with strategy-specific weights
                for tf_name, tf_trend in detailed_trends.items():
                    if tf_trend == "UNKNOWN":
                        continue
                    
                    tf_weight = timeframe_weights.get(tf_name, 0.0)
                    if tf_weight == 0.0:
                        continue
                    
                    # Parse trend string (e.g., "STRONG_UPTREND", "WEAK_DOWNTREND", "SIDEWAYS")
                    trend_str = str(tf_trend).upper()
                    
                    # Determine direction and strength
                    is_bullish = "UP" in trend_str or "BULLISH" in trend_str
                    is_bearish = "DOWN" in trend_str or "BEARISH" in trend_str
                    is_strong = "STRONG" in trend_str
                    is_weak = "WEAK" in trend_str
                    
                    # Calculate score for this timeframe (0-100)
                    if is_bullish:
                        tf_score = 100.0
                        if is_strong:
                            tf_score = 150.0  # Strong trends get bonus
                        elif is_weak:
                            tf_score = 60.0   # Weak trends get reduced score
                        trend_long += tf_score * tf_weight
                    elif is_bearish:
                        tf_score = 100.0
                        if is_strong:
                            tf_score = 150.0
                        elif is_weak:
                            tf_score = 60.0
                        trend_short += tf_score * tf_weight
                
                # Check for multi-timeframe convergence (all timeframes aligned = stronger signal)
                bullish_tfs = sum(1 for tf in detailed_trends.values() 
                                 if "UP" in str(tf).upper() or "BULLISH" in str(tf).upper())
                bearish_tfs = sum(1 for tf in detailed_trends.values() 
                                 if "DOWN" in str(tf).upper() or "BEARISH" in str(tf).upper())
                total_tfs = len([tf for tf in detailed_trends.values() if str(tf) != "UNKNOWN"])
                
                # Convergence bonus: all timeframes aligned = very strong signal
                if total_tfs >= 3:
                    if bullish_tfs == total_tfs:
                        trend_long += 50.0  # All timeframes bullish = strong convergence
                        reasons.append(f"Perfect trend convergence: all {total_tfs} timeframes bullish")
                    elif bearish_tfs == total_tfs:
                        trend_short += 50.0
                        reasons.append(f"Perfect trend convergence: all {total_tfs} timeframes bearish")
                    elif bullish_tfs >= 3:
                        trend_long += 30.0
                        reasons.append(f"Strong trend alignment: {bullish_tfs}/{total_tfs} timeframes bullish")
                    elif bearish_tfs >= 3:
                        trend_short += 30.0
                        reasons.append(f"Strong trend alignment: {bearish_tfs}/{total_tfs} timeframes bearish")
                
                # Apply overall trend weight
                long_score += trend_long * trend_weight
                short_score += trend_short * trend_weight
            
            # 3. Support/Resistance Analysis
            sr_weight = direction_weights.get("support_resistance", 0.0)
            if sr_weight > 0:
                top_support = self._safe_get(sr_data, "top_2_support", [])
                top_resistance = self._safe_get(sr_data, "top_2_resistance", [])
                
                # Base S/R score (0-100)
                sr_long = 0.0
                sr_short = 0.0
                
                # Check proximity to support (bullish) or resistance (bearish)
                if top_support:
                    closest_support = max(top_support, key=lambda x: self._safe_get(x, "level", x if not isinstance(x, dict) else 0))
                    support_price = self._safe_get(closest_support, "level", closest_support if not isinstance(closest_support, dict) else 0)
                    support_score = self._safe_get(closest_support, "score", 50.0)
                    
                    distance_pct = abs(current_price - support_price) / current_price if support_price > 0 else 1.0
                    if distance_pct < 0.01:  # Within 1% of support
                        sr_long = support_score  # Use S/R score directly (0-100)
                        reasons.append(f"Near strong support @ ${support_price:.2f} (score: {support_score:.1f})")
                
                if top_resistance:
                    closest_resistance = min(top_resistance, key=lambda x: self._safe_get(x, "level", x if not isinstance(x, dict) else float('inf')))
                    resistance_price = self._safe_get(closest_resistance, "level", closest_resistance if not isinstance(closest_resistance, dict) else 0)
                    resistance_score = self._safe_get(closest_resistance, "score", 50.0)
                    
                    distance_pct = abs(current_price - resistance_price) / current_price if resistance_price > 0 else 1.0
                    if distance_pct < 0.01:  # Within 1% of resistance
                        sr_short = resistance_score  # Use S/R score directly (0-100)
                        reasons.append(f"Near strong resistance @ ${resistance_price:.2f} (score: {resistance_score:.1f})")
                
                # Apply weight
                long_score += sr_long * sr_weight
                short_score += sr_short * sr_weight
            
            # 4. Market Pressure Analysis
            pressure_weight = direction_weights.get("pressure", 0.0)
            if pressure_weight > 0:
                pressure_direction = self._safe_get(pressure_data, "direction", "NEUTRAL")
                pressure_strength = self._safe_get(pressure_data, "strength", 0.0)
                
                # Base pressure score (0-100)
                pressure_long = 0.0
                pressure_short = 0.0
                
                if pressure_direction in ["BUY", "STRONG_BUY"]:
                    strength_multiplier = 1.5 if "STRONG" in pressure_direction else 1.0
                    pressure_long = 100.0 * strength_multiplier * pressure_strength
                    reasons.append(f"Buy pressure: {pressure_direction} (strength: {pressure_strength:.2f})")
                elif pressure_direction in ["SELL", "STRONG_SELL"]:
                    strength_multiplier = 1.5 if "STRONG" in pressure_direction else 1.0
                    pressure_short = 100.0 * strength_multiplier * pressure_strength
                    reasons.append(f"Sell pressure: {pressure_direction} (strength: {pressure_strength:.2f})")
                
                # Apply weight
                long_score += pressure_long * pressure_weight
                short_score += pressure_short * pressure_weight
            
            # 5. Pattern Analysis
            patterns_weight = direction_weights.get("patterns", 0.0)
            if patterns_weight > 0:
                patterns_nested = self._safe_get(patterns_data, "patterns_nested", {})
                reversal_patterns = self._safe_get(patterns_nested, "reversal", [])
                continuation_patterns = self._safe_get(patterns_nested, "continuation", [])
                
                # Base pattern score (0-100)
                patterns_long = 0.0
                patterns_short = 0.0
                
                # Check for bullish reversal patterns
                bullish_reversals = [p for p in reversal_patterns if isinstance(p, dict) and p.get("direction") == "BULLISH"]
                if bullish_reversals:
                    patterns_long = 100.0
                    reasons.append(f"Bullish reversal pattern detected ({len(bullish_reversals)})")
                
                # Check for bearish reversal patterns
                bearish_reversals = [p for p in reversal_patterns if isinstance(p, dict) and p.get("direction") == "BEARISH"]
                if bearish_reversals:
                    patterns_short = 100.0
                    reasons.append(f"Bearish reversal pattern detected ({len(bearish_reversals)})")
                
                # Check for bullish continuation patterns
                bullish_continuations = [p for p in continuation_patterns if isinstance(p, dict) and p.get("direction") == "BULLISH"]
                if bullish_continuations:
                    patterns_long += 50.0
                    reasons.append(f"Bullish continuation pattern ({len(bullish_continuations)})")
                
                # Check for bearish continuation patterns
                bearish_continuations = [p for p in continuation_patterns if isinstance(p, dict) and p.get("direction") == "BEARISH"]
                if bearish_continuations:
                    patterns_short += 50.0
                    reasons.append(f"Bearish continuation pattern ({len(bearish_continuations)})")
                
                # Apply weight
                long_score += patterns_long * patterns_weight
                short_score += patterns_short * patterns_weight
            
            # 6. Volume Confirmation
            volume_weight = direction_weights.get("volume", 0.0)
            if volume_weight > 0:
                volume_category = unified_data.get("volume_category", "NORMAL")
                volume_long = 0.0
                volume_short = 0.0
                
                if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
                    # High volume confirms the direction with stronger signal
                    if long_score > short_score:
                        volume_long = 100.0
                        reasons.append(f"High volume confirms bullish ({volume_category})")
                    elif short_score > long_score:
                        volume_short = 100.0
                        reasons.append(f"High volume confirms bearish ({volume_category})")
                
                # Apply weight
                long_score += volume_long * volume_weight
                short_score += volume_short * volume_weight
            
            # 7. Funding Rate Analysis
            funding_weight = direction_weights.get("funding", 0.0)
            if funding_weight > 0:
                funding_trend = self._safe_get(funding_data, "trend", {})
                funding_direction = self._safe_get(funding_trend, "direction", "STABLE")
                
                # Base funding score (0-100)
                funding_long = 0.0
                funding_short = 0.0
                
                if funding_direction == "INCREASING":  # Increasing funding = bullish sentiment
                    funding_long = 100.0
                    reasons.append("Funding rate increasing (bullish sentiment)")
                elif funding_direction == "DECREASING":  # Decreasing funding = bearish sentiment
                    funding_short = 100.0
                    reasons.append("Funding rate decreasing (bearish sentiment)")
                
                # Apply weight
                long_score += funding_long * funding_weight
                short_score += funding_short * funding_weight
            
            # Determine final direction
            score_diff = abs(long_score - short_score)
            
            if score_diff < min_score_diff:
                logger.debug(f"⏸️ Direction unclear ({strategy}): LONG={long_score:.1f} vs SHORT={short_score:.1f} (diff: {score_diff:.1f} < {min_score_diff:.1f})")
                return None
            
            if long_score > short_score:
                direction = "LONG"
                confidence_pct = min(95.0, 50.0 + (long_score - short_score))
                reasoning = f"LONG signal (score: {long_score:.1f} vs {short_score:.1f}). " + "; ".join(reasons[:5])
            else:
                direction = "SHORT"
                confidence_pct = min(95.0, 50.0 + (short_score - long_score))
                reasoning = f"SHORT signal (score: {short_score:.1f} vs {long_score:.1f}). " + "; ".join(reasons[:5])
            
            logger.debug(f"📊 Direction determined: {direction} (LONG: {long_score:.1f}, SHORT: {short_score:.1f})")
            
            return {
                "direction": direction,
                "reasoning": reasoning,
                "long_score": long_score,
                "short_score": short_score,
                "confidence_pct": confidence_pct
            }
            
        except Exception as e:
            logger.error(f"❌ Direction determination failed: {e}")
            return None
    
    def _get_strategy_timeframe_weights(self, strategy: str) -> Dict[str, float]:
        """
        Get strategy-specific timeframe weights
        
        Different strategies care about different timeframes:
        - Scalping: 15m (high), 1h (medium), 4h (low), 24h (none)
        - Swing Trading: 4h (high), 24h (high), 1h (medium), 15m (low)
        - Trend Following: All timeframes, but 4h/24h weighted higher
        - Range Trading: 1h (high), 4h (medium), 15m (low), 24h (low)
        - Breakout: 1h (high), 4h (high), 15m (medium), 24h (low)
        """
        timeframe_weights_map = {
            "scalping": {
                "trend_15m": 0.50,  # 50% - Most important for scalping
                "trend_1h": 0.30,   # 30% - Medium importance
                "trend_4h": 0.15,   # 15% - Low importance
                "trend_24h": 0.05   # 5% - Minimal importance
            },
            "swing_trading": {
                "trend_15m": 0.10,  # 10% - Less important
                "trend_1h": 0.25,   # 25% - Medium importance
                "trend_4h": 0.35,   # 35% - High importance
                "trend_24h": 0.30   # 30% - High importance
            },
            "trend_following": {
                "trend_15m": 0.15,  # 15% - Low importance
                "trend_1h": 0.25,   # 25% - Medium importance
                "trend_4h": 0.30,   # 30% - High importance
                "trend_24h": 0.30   # 30% - High importance
            },
            "range_trading": {
                "trend_15m": 0.20,  # 20% - Low importance (ranges are medium-term)
                "trend_1h": 0.40,   # 40% - High importance
                "trend_4h": 0.30,   # 30% - Medium importance
                "trend_24h": 0.10   # 10% - Low importance
            },
            "breakout": {
                "trend_15m": 0.25,  # 25% - Medium importance
                "trend_1h": 0.35,   # 35% - High importance
                "trend_4h": 0.30,   # 30% - High importance
                "trend_24h": 0.10   # 10% - Low importance
            },
            "low_volatility_range": {
                "trend_15m": 0.30,  # 30% - Medium importance
                "trend_1h": 0.40,   # 40% - High importance
                "trend_4h": 0.20,   # 20% - Medium importance
                "trend_24h": 0.10   # 10% - Low importance
            },
            "high_volatility": {
                "trend_15m": 0.20,  # 20% - Low importance
                "trend_1h": 0.30,   # 30% - Medium importance
                "trend_4h": 0.30,   # 30% - Medium importance
                "trend_24h": 0.20   # 20% - Medium importance
            },
            "spike_hunting": {
                "trend_15m": 0.40,  # 40% - High importance (spikes are short-term)
                "trend_1h": 0.35,   # 35% - High importance
                "trend_4h": 0.20,   # 20% - Medium importance
                "trend_24h": 0.05   # 5% - Low importance
            },
            "standard": {
                "trend_15m": 0.20,  # 20% - Balanced approach
                "trend_1h": 0.30,   # 30% - Primary timeframe
                "trend_4h": 0.30,   # 30% - Primary timeframe
                "trend_24h": 0.20   # 20% - Secondary timeframe
            }
        }
        
        return timeframe_weights_map.get(strategy, {
            "trend_15m": 0.25,
            "trend_1h": 0.25,
            "trend_4h": 0.25,
            "trend_24h": 0.25
        })
    
    def _determine_entry_price(
        self, 
        unified_data: Dict[str, Any], 
        direction: str,
        strategy: str,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Determine best entry price by analyzing multiple setups and choosing highest confidence
        
        Entry setups analyzed:
        1. S/R Level Entry: Enter at support (LONG) or resistance (SHORT)
        2. Current Price Entry: Enter at current price if conditions are good
        3. Breakout Entry: Enter above resistance (LONG) or below support (SHORT)
        4. Pullback Entry: Enter on retest of broken level
        
        Each setup is scored based on:
        - S/R level strength and proximity
        - RSI alignment
        - Volume confirmation
        - Pattern confirmation
        - Pressure alignment
        - Trend alignment
        - Strategy-specific requirements
        
        Args:
            unified_data: Complete market analysis data
            direction: "LONG" or "SHORT"
            strategy: Current trading strategy
            config: Strategy configuration
            
        Returns:
            Dict with "entry_price", "confidence", and "reasoning", or None if no good setup
        """
        try:
            current_price = unified_data.get("current_price", 0.0)
            if current_price <= 0:
                logger.warning("⚠️ Invalid current price for entry determination")
                return None
            
            # Extract market data
            sr_data = unified_data.get("support_resistance", {})
            
            # Get S/R levels
            top_support = self._safe_get(sr_data, "top_2_support", [])
            top_resistance = self._safe_get(sr_data, "top_2_resistance", [])
            
            # Generate potential entry setups
            setups = []
            
            if direction == "LONG":
                # 1. Support Level Entry (enter at support)
                for support in top_support:
                    level_price = self._safe_get(support, "level", support if not isinstance(support, dict) else 0)
                    level_score = self._safe_get(support, "score", 50.0)
                    
                    if level_price > 0 and level_price < current_price:
                        setup = self._score_entry_setup(
                            entry_price=level_price,
                            setup_type="support_level",
                            direction=direction,
                            unified_data=unified_data,
                            level_data=support if isinstance(support, dict) else {"level": level_price, "score": level_score},
                            strategy=strategy,
                            config=config
                        )
                        if setup:
                            setups.append(setup)
                
                # 2. Current Price Entry (if near support or good conditions)
                setup = self._score_entry_setup(
                    entry_price=current_price,
                    setup_type="current_price",
                    direction=direction,
                    unified_data=unified_data,
                    level_data=None,
                    strategy=strategy,
                    config=config
                )
                if setup:
                    setups.append(setup)
                
                # 3. Breakout Entry (above resistance)
                for resistance in top_resistance:
                    level_price = self._safe_get(resistance, "level", resistance if not isinstance(resistance, dict) else 0)
                    level_score = self._safe_get(resistance, "score", 50.0)
                    
                    if level_price > 0 and level_price > current_price:
                        breakout_price = level_price * 1.001
                        setup = self._score_entry_setup(
                            entry_price=breakout_price,
                            setup_type="breakout",
                            direction=direction,
                            unified_data=unified_data,
                            level_data=resistance if isinstance(resistance, dict) else {"level": level_price, "score": level_score},
                            strategy=strategy,
                            config=config
                        )
                        if setup:
                            setups.append(setup)
            
            else:  # SHORT
                # 1. Resistance Level Entry (enter at resistance)
                for resistance in top_resistance:
                    level_price = self._safe_get(resistance, "level", resistance if not isinstance(resistance, dict) else 0)
                    level_score = self._safe_get(resistance, "score", 50.0)
                    
                    if level_price > 0 and level_price > current_price:
                        setup = self._score_entry_setup(
                            entry_price=level_price,
                            setup_type="resistance_level",
                            direction=direction,
                            unified_data=unified_data,
                            level_data=resistance if isinstance(resistance, dict) else {"level": level_price, "score": level_score},
                            strategy=strategy,
                            config=config
                        )
                        if setup:
                            setups.append(setup)
                
                # 2. Current Price Entry (if near resistance or good conditions)
                setup = self._score_entry_setup(
                    entry_price=current_price,
                    setup_type="current_price",
                    direction=direction,
                    unified_data=unified_data,
                    level_data=None,
                    strategy=strategy,
                    config=config
                )
                if setup:
                    setups.append(setup)
                
                # 3. Breakdown Entry (below support)
                for support in top_support:
                    level_price = self._safe_get(support, "level", support if not isinstance(support, dict) else 0)
                    level_score = self._safe_get(support, "score", 50.0)
                    
                    if level_price > 0 and level_price < current_price:
                        breakdown_price = level_price * 0.999
                        setup = self._score_entry_setup(
                            entry_price=breakdown_price,
                            setup_type="breakdown",
                            direction=direction,
                            unified_data=unified_data,
                            level_data=support if isinstance(support, dict) else {"level": level_price, "score": level_score},
                            strategy=strategy,
                            config=config
                        )
                        if setup:
                            setups.append(setup)
            
            if not setups:
                logger.debug(f"⏸️ No valid entry setups found for {direction}")
                return None
            
            # Select setup with highest confidence
            best_setup = max(setups, key=lambda s: s["confidence"])
            
            logger.debug(f"📊 Entry determined: ${best_setup['entry_price']:.2f} "
                        f"(confidence: {best_setup['confidence']:.1f}%, type: {best_setup['setup_type']})")
            
            return best_setup
            
        except Exception as e:
            logger.error(f"❌ Entry price determination failed: {e}")
            return None
    
    def _score_entry_setup(
        self,
        entry_price: float,
        setup_type: str,
        direction: str,
        unified_data: Dict[str, Any],
        level_data: Optional[Dict[str, Any]],
        strategy: str,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Score an entry setup and return confidence
        
        Args:
            entry_price: Proposed entry price
            setup_type: Type of setup (support_level, resistance_level, current_price, breakout, breakdown)
            direction: "LONG" or "SHORT"
            unified_data: Complete market analysis data
            level_data: S/R level data if applicable
            strategy: Current trading strategy
            config: Strategy configuration
            
        Returns:
            Dict with entry_price, confidence, reasoning, setup_type, or None if invalid
        """
        try:
            current_price = unified_data.get("current_price", 0.0)
            if current_price <= 0 or entry_price <= 0:
                return None
            
            # Extract indicators
            rsi_data = unified_data.get("rsi", {})
            trend_data = unified_data.get("trend", {})
            pressure_data = unified_data.get("pressure", {})
            patterns_data = unified_data.get("patterns", {})
            
            confidence = 0.0
            reasons = []
            
            # 1. S/R Level Quality (if setup uses S/R level)
            if level_data and isinstance(level_data, dict):
                level_score = level_data.get("score", 0)
                level_price = level_data.get("level", entry_price)
                
                # Distance from level
                distance_pct = abs(entry_price - level_price) / current_price if level_price > 0 else 0.0
                
                # Strong level close to entry = high confidence
                if distance_pct < 0.005:  # Within 0.5% of level
                    confidence += level_score * 0.40  # 40% weight for level quality
                    reasons.append(f"Strong S/R level (score: {level_score:.1f})")
                elif distance_pct < 0.01:  # Within 1% of level
                    confidence += level_score * 0.30
                    reasons.append(f"Near S/R level (score: {level_score:.1f})")
                else:
                    confidence += level_score * 0.20
                    reasons.append(f"S/R level reference (score: {level_score:.1f})")
            
            # 2. RSI Alignment
            rsi_value = self._safe_get(rsi_data, "rsi", 50.0)
            if direction == "LONG":
                if rsi_value < 40:  # Oversold or recovering
                    confidence += 20.0
                    reasons.append(f"RSI aligned ({rsi_value:.1f} - oversold)")
                elif rsi_value < 50:
                    confidence += 10.0
                    reasons.append(f"RSI favorable ({rsi_value:.1f})")
            else:  # SHORT
                if rsi_value > 60:  # Overbought or declining
                    confidence += 20.0
                    reasons.append(f"RSI aligned ({rsi_value:.1f} - overbought)")
                elif rsi_value > 50:
                    confidence += 10.0
                    reasons.append(f"RSI favorable ({rsi_value:.1f})")
            
            # 3. Trend Alignment
            trend_direction = self._safe_get(trend_data, "direction", "SIDEWAYS")
            if direction == "LONG" and "UP" in trend_direction.upper():
                confidence += 15.0
                reasons.append(f"Trend aligned ({trend_direction})")
            elif direction == "SHORT" and "DOWN" in trend_direction.upper():
                confidence += 15.0
                reasons.append(f"Trend aligned ({trend_direction})")
            
            # 4. Pressure Alignment
            pressure_direction = self._safe_get(pressure_data, "direction", "NEUTRAL")
            if direction == "LONG" and "BUY" in pressure_direction.upper():
                confidence += 10.0
                reasons.append(f"Buy pressure ({pressure_direction})")
            elif direction == "SHORT" and "SELL" in pressure_direction.upper():
                confidence += 10.0
                reasons.append(f"Sell pressure ({pressure_direction})")
            
            # 5. Volume Confirmation
            volume_category = unified_data.get("volume_category", "NORMAL")
            if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
                confidence += 10.0
                reasons.append(f"High volume ({volume_category})")
            
            # 6. Pattern Confirmation
            patterns_nested = self._safe_get(patterns_data, "patterns_nested", {})
            reversal_patterns = self._safe_get(patterns_nested, "reversal", [])
            
            if direction == "LONG":
                bullish_patterns = [p for p in reversal_patterns if isinstance(p, dict) and p.get("direction") == "BULLISH"]
                if bullish_patterns:
                    confidence += 10.0
                    reasons.append(f"Bullish pattern ({len(bullish_patterns)})")
            else:
                bearish_patterns = [p for p in reversal_patterns if isinstance(p, dict) and p.get("direction") == "BEARISH"]
                if bearish_patterns:
                    confidence += 10.0
                    reasons.append(f"Bearish pattern ({len(bearish_patterns)})")
            
            # 7. Setup Type Bonus
            if setup_type in ["support_level", "resistance_level"]:
                confidence += 5.0  # S/R level entries are generally safer
                reasons.append("S/R level entry")
            elif setup_type == "current_price":
                # Current price entry needs strong confirmation
                if confidence < 50.0:
                    return None  # Reject weak current price entries
                reasons.append("Current price entry")
            elif setup_type in ["breakout", "breakdown"]:
                # Breakouts need volume confirmation
                if volume_category not in ["HIGH", "VERY_HIGH", "EXTREME"]:
                    confidence -= 15.0  # Penalty for low volume breakouts
                else:
                    confidence += 5.0
                reasons.append(f"{setup_type} entry")
            
            # Strategy-specific adjustments
            confidence = self._apply_strategy_entry_adjustments(confidence, setup_type, direction, unified_data, strategy, config)
            
            # Cap confidence at 100%
            confidence = min(100.0, max(0.0, confidence))
            
            # Minimum confidence threshold
            min_confidence = 40.0  # Minimum 40% confidence for any entry
            if confidence < min_confidence:
                return None
            
            return {
                "entry_price": entry_price,
                "confidence": confidence,
                "reasoning": "; ".join(reasons[:5]),
                "setup_type": setup_type
            }
            
        except Exception as e:
            logger.error(f"❌ Entry setup scoring failed: {e}")
            return None
    
    def _apply_strategy_entry_adjustments(
        self,
        confidence: float,
        setup_type: str,
        direction: str,
        unified_data: Dict[str, Any],
        strategy: str,
        config: Dict[str, Any]
    ) -> float:
        """
        Apply strategy-specific adjustments to entry confidence
        
        Different strategies have different entry preferences:
        - Scalping: Prefers current price entries, needs tight spreads
        - Range Trading: Prefers S/R level entries, needs range confirmation
        - Breakout: Prefers breakout entries, needs volume confirmation
        - Trend Following: Prefers trend-aligned entries, needs strong trend
        """
        adjusted_confidence = confidence
        
        if strategy == "scalping":
            # Scalping prefers current price entries (faster execution)
            if setup_type == "current_price":
                adjusted_confidence += 10.0
            # Scalping doesn't like breakouts (too slow)
            elif setup_type in ["breakout", "breakdown"]:
                adjusted_confidence -= 10.0
        
        elif strategy == "range_trading":
            # Range trading strongly prefers S/R level entries
            if setup_type in ["support_level", "resistance_level"]:
                adjusted_confidence += 15.0
            # Range trading doesn't like breakouts (contradicts range strategy)
            elif setup_type in ["breakout", "breakdown"]:
                adjusted_confidence -= 20.0
        
        elif strategy == "breakout":
            # Breakout strategy strongly prefers breakout entries
            if setup_type in ["breakout", "breakdown"]:
                adjusted_confidence += 20.0
            # Breakout strategy doesn't like S/R level entries (too conservative)
            elif setup_type in ["support_level", "resistance_level"]:
                adjusted_confidence -= 10.0
        
        elif strategy == "trend_following":
            # Trend following prefers entries aligned with trend
            trend_direction = self._safe_get(unified_data.get("trend", {}), "direction", "SIDEWAYS")
            if direction == "LONG" and "UP" in trend_direction.upper():
                adjusted_confidence += 10.0
            elif direction == "SHORT" and "DOWN" in trend_direction.upper():
                adjusted_confidence += 10.0
            else:
                adjusted_confidence -= 15.0  # Penalty for counter-trend entries
        
        elif strategy == "low_volatility_range":
            # Low vol range strongly prefers S/R level entries
            if setup_type in ["support_level", "resistance_level"]:
                adjusted_confidence += 20.0
            # Doesn't like breakouts in low volatility
            elif setup_type in ["breakout", "breakdown"]:
                adjusted_confidence -= 15.0
        
        return adjusted_confidence
    
    def _calculate_stop_and_target(
        self,
        entry_price: float,
        direction: str,
        config: Dict[str, Any],
        unified_data: Dict[str, Any]
    ) -> tuple[float, float]:
        """
        Calculate stop loss and take profit from strategy config
        
        Uses strategy config values:
        - stop_loss: config["stop_loss"] percentage from entry
        - take_profit: config["profit_target"] percentage from entry
        """
        try:
            stop_loss_pct = config.get("stop_loss", 0.004)  # Default 0.4%
            profit_target_pct = config.get("profit_target", 0.008)  # Default 0.8%
            
            if direction == "LONG":
                stop_loss = entry_price * (1 - stop_loss_pct)
                take_profit = entry_price * (1 + profit_target_pct)
            else:  # SHORT
                stop_loss = entry_price * (1 + stop_loss_pct)
                take_profit = entry_price * (1 - profit_target_pct)
            
            return stop_loss, take_profit
            
        except Exception as e:
            logger.error(f"❌ Stop/Target calculation failed: {e}")
            raise