#!/usr/bin/env python3
"""
Real-Time Prediction Engine - Modular & Clean
Continuously analyzes market and generates predictions with growing confidence
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from loguru import logger
from core.ml.probability_engine import get_global_probability_engine, ExpectedValue
from core.ml.bayesian_fusion import get_global_bayesian_fusion, Signal
from core.ml.multitimeframe_probability import get_global_multitimeframe_probability
from core.ml.calibration_tracker import get_global_calibration_tracker


@dataclass
class RealtimePrediction:
    """Real-time prediction with confidence tracking"""
    
    # CORE PREDICTION (required fields first)
    direction: str              # "LONG", "SHORT", "NEUTRAL"
    confidence: float           # 0.0 to 1.0
    entry_price: float          # Optimal entry price (close to market)
    
    # TARGETS (required fields)
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    
    # CONFIDENCE TRACKING (required fields)
    base_confidence: float      # Initial confidence
    
    # MARKET CONTEXT (required fields)
    current_price: float
    score: float               # Raw prediction score (-1.0 to 1.0)
    
    # OPTIONAL FIELDS (with defaults)
    confidence_boosts: List[Tuple[str, float]] = field(default_factory=list)
    confidence_history: List[float] = field(default_factory=list)
    
    # TIMING
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    
    # REASONING
    reasoning: List[str] = field(default_factory=list)
    
    # PROBABILITY & EXPECTED VALUE
    expected_value: Optional[float] = None  # EV as percentage
    expected_value_dollars: Optional[float] = None  # EV in dollars
    win_probability: Optional[float] = None  # P(win)
    ev_reasoning: Optional[str] = None  # EV explanation
    should_trade_ev: Optional[bool] = None  # EV-based trade decision
    
    # BAYESIAN FUSION
    bayesian_confidence: Optional[float] = None  # Fused probability from Bayesian
    bayesian_reasoning: Optional[str] = None  # Bayesian fusion explanation
    
    # MULTI-TIMEFRAME ADJUSTMENT
    timeframe_adjusted_confidence: Optional[float] = None  # Adjusted for expected hold time
    timeframe_reasoning: Optional[str] = None  # Timeframe adjustment explanation
    expected_hold_time_seconds: Optional[float] = None  # Expected trade duration
    
    # CALIBRATION
    calibrated_confidence: Optional[float] = None  # Historically calibrated confidence
    calibration_adjustment: Optional[float] = None  # +/- adjustment from calibration
    
    # KELLY POSITION SIZING
    kelly_position_pct: Optional[float] = None  # Kelly-optimal position size %
    kelly_position_dollars: Optional[float] = None  # Kelly position in dollars
    
    # FINAL CONFIDENCE - incorporates all factors
    final_confidence: Optional[float] = None  # Final confidence after all processing
    
    # EXECUTION
    ready_to_execute: bool = False
    execution_reason: str = ""
    
    @property
    def age_seconds(self) -> float:
        """How old is this prediction"""
        return time.time() - self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/dashboard"""
        return {
            "direction": self.direction,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward_ratio": self.risk_reward_ratio,
            "current_price": self.current_price,
            "score": self.score,
            "age_seconds": self.age_seconds,
            "reasoning": self.reasoning,
            "ready_to_execute": self.ready_to_execute,
            "confidence_boosts": [{"reason": r, "boost": b} for r, b in self.confidence_boosts],
            # EV data
            "expected_value": self.expected_value,
            "expected_value_dollars": self.expected_value_dollars,
            "win_probability": self.win_probability,
            "ev_reasoning": self.ev_reasoning,
            "should_trade_ev": self.should_trade_ev,
            # Bayesian data
            "bayesian_confidence": self.bayesian_confidence,
            "bayesian_reasoning": self.bayesian_reasoning,
            # Timeframe data
            "timeframe_adjusted_confidence": self.timeframe_adjusted_confidence,
            "timeframe_reasoning": self.timeframe_reasoning,
            "expected_hold_time_seconds": self.expected_hold_time_seconds,
            # Calibration data
            "calibrated_confidence": self.calibrated_confidence,
            "calibration_adjustment": self.calibration_adjustment,
            # Kelly position sizing
            "kelly_position_pct": self.kelly_position_pct,
            "kelly_position_dollars": self.kelly_position_dollars,
            # Final confidence - incorporates all factors
            "final_confidence": self.final_confidence
        }


class RealtimePredictionEngine:
    """
    Real-time prediction engine with modular components:
    1. Direction Recognition
    2. Entry Price Calculation
    3. Confidence Calculation
    
    SINGLETON PATTERN: Maintains ONE active prediction and updates its fields
    """
    
    def __init__(self):
        # SINGLETON PREDICTION - Single source of truth
        self.active_prediction: Optional[RealtimePrediction] = None
        
        # Configuration - will be updated based on active strategy
        self.confidence_threshold = 0.60  # Default: Execute when confidence >= 60%
        self.min_tracking_confidence = 0.50  # Start tracking at 50%
        self.max_prediction_age = 300  # 5 minutes max
        
        # Performance tracking
        self.updates_count = 0
        self.predictions_executed = 0
        self.direction_changes = 0
        
        logger.info("🧠 Real-time Prediction Engine initialized - Continuous tracking")
        logger.info(f"   📊 Default confidence threshold: {self.confidence_threshold:.1%}")
        logger.info(f"   🎯 Strategy: Try both LONG/SHORT directions and pick highest confidence")
        logger.info(f"   ⚡ Reactive: Adjusts prediction fields continuously with market")
    
    def update_confidence_threshold(self, strategy: str) -> None:
        """Update confidence threshold based on active strategy"""
        from config.config import Config
        
        strategy_config = Config.STRATEGY_CONFIGS.get(strategy, {})
        new_threshold = strategy_config.get("confidence_threshold", 0.60)
        
        logger.info(f"🔧 Threshold update requested: strategy={strategy}, current={self.confidence_threshold:.1%}, new={new_threshold:.1%}")
        
        if new_threshold != self.confidence_threshold:
            logger.info(f"🎯 Confidence threshold updated: {self.confidence_threshold:.1%} → {new_threshold:.1%} (strategy: {strategy})")
            self.confidence_threshold = new_threshold
            self.min_tracking_confidence = max(0.50, new_threshold - 0.10)  # 10% below execution threshold
        else:
            logger.info(f"✅ Threshold already correct: {self.confidence_threshold:.1%} for strategy {strategy}")
    
    def _find_optimal_direction(self, market_data: Dict[str, Any]) -> tuple:
        """
        Try both LONG and SHORT directions and return the one with highest confidence
        
        Returns:
            tuple: (best_direction, best_score, best_confidence, best_reasoning)
        """
        try:
            # Try LONG direction
            long_direction, long_score, long_reasoning = self.recognize_direction(market_data, forced_direction="LONG")
            long_confidence, _, _, _ = self.calculate_confidence(
                direction=long_direction,
                score=long_score,
                market_data=market_data
            )
            
            # Try SHORT direction
            short_direction, short_score, short_reasoning = self.recognize_direction(market_data, forced_direction="SHORT")
            short_confidence, _, _, _ = self.calculate_confidence(
                direction=short_direction,
                score=short_score,
                market_data=market_data
            )
            
            # Compare confidences and pick the best
            if long_confidence > short_confidence:
                best_direction = "LONG"
                best_score = long_score
                best_confidence = long_confidence
                best_reasoning = f"LONG chosen (LONG: {long_confidence:.1%}, SHORT: {short_confidence:.1%}) - {'; '.join(long_reasoning)}"
                logger.debug(f"🎯 Direction selection: LONG ({long_confidence:.1%}) > SHORT ({short_confidence:.1%})")
            else:
                best_direction = "SHORT"
                best_score = short_score
                best_confidence = short_confidence
                best_reasoning = f"SHORT chosen (SHORT: {short_confidence:.1%}, LONG: {long_confidence:.1%}) - {'; '.join(short_reasoning)}"
                logger.debug(f"🎯 Direction selection: SHORT ({short_confidence:.1%}) > LONG ({long_confidence:.1%})")
            
            return best_direction, best_score, best_confidence, best_reasoning
            
        except Exception as e:
            logger.error(f"❌ Optimal direction selection failed: {e}")
            # Fallback to original method
            direction, score, reasoning = self.recognize_direction(market_data)
            confidence, _, _, _ = self.calculate_confidence(
                direction=direction,
                score=score,
                market_data=market_data
            )
            return direction, score, confidence, reasoning
    
    def update_prediction(self, market_data: Dict[str, Any], strategy: str = "standard") -> str:
        """
        Update singleton prediction based on current market conditions
        ALWAYS recalculates direction, entry price, and confidence on every call
        
        Args:
            market_data: Unified market data from session orchestrator
            strategy: Current trading strategy
            
        Returns:
            Action: "EXECUTE", "UPDATED", "CREATED", "CANCELLED", "NO_SIGNAL"
        """
        try:
            current_price = market_data.get("current_price", 0)
            if not current_price or current_price <= 0:
                return "NO_SIGNAL"
            
            # MODULE 1: OPTIMAL DIRECTION SELECTION (try both directions for best confidence)
            best_direction, best_score, best_confidence, best_reasoning = self._find_optimal_direction(market_data)
            
            direction = best_direction
            score = best_score
            direction_reasoning = best_reasoning
            confidence = best_confidence
            
            # MODULE 2: ENTRY PRICE CALCULATION
            entry_price = self.calculate_entry_price(
                current_price=current_price,
                direction=direction,
                market_data=market_data
            )
            
            # Calculate targets first (needed for EV calculation)
            stop_loss, take_profit, risk_reward = self._calculate_targets(
                entry_price=entry_price,
                direction=direction,
                score=score,
                strategy=strategy,
                market_data=market_data
            )
            
            # MODULE 3: EXPECTED VALUE CALCULATION (calculate before confidence)
            ev_result = self._calculate_expected_value(
                confidence=0.5,  # Use base confidence for initial EV calculation
                entry_price=entry_price,
                take_profit=take_profit,
                stop_loss=stop_loss,
                position_size=1000.0  # Default position size for EV calculation
            )
            
            # Add EV to market data for confidence calculation
            market_data_with_ev = market_data.copy()
            market_data_with_ev["expected_value"] = ev_result.ev_percent
            
            # MODULE 4: CONFIDENCE CALCULATION (now includes EV)
            final_confidence, base_confidence, boosts, confidence_reasoning = self.calculate_confidence(
                direction=direction,
                score=score,
                market_data=market_data_with_ev  # Include EV in confidence calculation
            )
            confidence = final_confidence  # Use the detailed calculation
            
            # MODULE 5: BAYESIAN FUSION (combine all signals probabilistically)
            bayesian_result = self._apply_bayesian_fusion(
                direction=direction,
                market_data=market_data,
                base_confidence=confidence
            )
            
            # FIXED: Range trading should have reduced Bayesian fusion weight
            # Range trading is more conservative and should rely more on main analysis
            if strategy == "range_trading" and bayesian_result:
                # Range trading: 90% main + 10% bayesian (very conservative)
                main_weight = 0.90
                bayesian_weight = 0.10
                adjusted_confidence = (confidence * main_weight) + (bayesian_result['confidence'] * bayesian_weight)
                logger.debug(f"🔍 Range Trading Bayesian: main={confidence:.1%} + bayesian={bayesian_result['confidence']:.1%} = {adjusted_confidence:.1%}")
                confidence = adjusted_confidence
            
            # MODULE 6: MULTI-TIMEFRAME ADJUSTMENT
            timeframe_result = self._apply_timeframe_adjustment(
                confidence=bayesian_result['confidence'] if bayesian_result else confidence,
                strategy=strategy
            )
            
            # MODULE 7: CALIBRATION ADJUSTMENT
            calibrated_result = self._apply_calibration(
                confidence=timeframe_result['confidence'] if timeframe_result else confidence
            )
            
            # MODULE 8: KELLY POSITION SIZING
            kelly_result = self._calculate_kelly_position(
                confidence=calibrated_result['confidence'] if calibrated_result else confidence,
                entry_price=entry_price,
                take_profit=take_profit,
                stop_loss=stop_loss,
                capital=10000.0  # Default capital for position size calculation
            )
            
            # Use the final calibrated confidence
            final_confidence = calibrated_result['confidence'] if calibrated_result else confidence
            
            # NO ACTIVE PREDICTION - Create new one
            if not self.active_prediction:
                self.active_prediction = RealtimePrediction(
                    direction=direction,
                    confidence=final_confidence,  # Use calibrated confidence
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=risk_reward,
                    base_confidence=base_confidence,
                    confidence_boosts=boosts,
                    confidence_history=[final_confidence],
                    current_price=current_price,
                    score=score,
                    reasoning=direction_reasoning + "; " + "; ".join(confidence_reasoning),
                    # EV data
                    expected_value=ev_result.ev_percent,
                    expected_value_dollars=ev_result.ev_dollars,
                    win_probability=ev_result.win_probability,
                    ev_reasoning=ev_result.reasoning,
                    should_trade_ev=ev_result.should_trade,
                    # Bayesian data
                    bayesian_confidence=bayesian_result.get('confidence') if bayesian_result else None,
                    bayesian_reasoning=bayesian_result.get('reasoning') if bayesian_result else None,
                    # Timeframe data
                    timeframe_adjusted_confidence=timeframe_result.get('confidence') if timeframe_result else None,
                    timeframe_reasoning=timeframe_result.get('reasoning') if timeframe_result else None,
                    expected_hold_time_seconds=timeframe_result.get('expected_hold_time') if timeframe_result else None,
                    # Calibration data
                    calibrated_confidence=calibrated_result.get('confidence') if calibrated_result else None,
                    calibration_adjustment=calibrated_result.get('adjustment') if calibrated_result else None,
                    # Kelly position sizing
                    kelly_position_pct=kelly_result.get('position_pct') if kelly_result else None,
                    kelly_position_dollars=kelly_result.get('position_dollars') if kelly_result else None,
                    # FINAL CONFIDENCE - incorporates all factors
                    final_confidence=final_confidence
                )
                bayesian_conf_str = f"{bayesian_result.get('confidence', 0):.1%}" if bayesian_result else "N/A"
                logger.info(f"🎯 NEW prediction: {direction} @ ${entry_price:,.2f} ({final_confidence:.1%}) | EV: {ev_result.ev_percent:+.2%} | Bayesian: {bayesian_conf_str}")
                return "CREATED"
            
            # ACTIVE PREDICTION EXISTS - Update fields
            old_direction = self.active_prediction.direction
            old_confidence = self.active_prediction.confidence
            
            # Check if direction changed
            if direction != old_direction:
                logger.warning(f"🔄 Direction changed: {old_direction} → {direction}")
                self.direction_changes += 1
                
                # Reset prediction with new direction
                self.active_prediction = RealtimePrediction(
                    direction=direction,
                    confidence=confidence,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=risk_reward,
                    base_confidence=base_confidence,
                    confidence_boosts=boosts,
                    confidence_history=[confidence],
                    current_price=current_price,
                    score=score,
                    reasoning=direction_reasoning + "; " + "; ".join(confidence_reasoning),
                    # EV data
                    expected_value=ev_result.ev_percent,
                    expected_value_dollars=ev_result.ev_dollars,
                    win_probability=ev_result.win_probability,
                    ev_reasoning=ev_result.reasoning,
                    should_trade_ev=ev_result.should_trade
                )
                return "CREATED"
            
            # UPDATE EXISTING PREDICTION FIELDS
            self.active_prediction.confidence = confidence
            self.active_prediction.entry_price = entry_price
            self.active_prediction.stop_loss = stop_loss
            self.active_prediction.take_profit = take_profit
            self.active_prediction.risk_reward_ratio = risk_reward
            self.active_prediction.base_confidence = base_confidence
            self.active_prediction.confidence_boosts = boosts
            self.active_prediction.confidence_history.append(confidence)
            self.active_prediction.current_price = current_price
            self.active_prediction.score = score
            self.active_prediction.reasoning = direction_reasoning + "; " + "; ".join(confidence_reasoning)
            self.active_prediction.last_updated = time.time()
            # Update EV data
            self.active_prediction.expected_value = ev_result.ev_percent
            self.active_prediction.expected_value_dollars = ev_result.ev_dollars
            self.active_prediction.win_probability = ev_result.win_probability
            self.active_prediction.ev_reasoning = ev_result.reasoning
            self.active_prediction.should_trade_ev = ev_result.should_trade
            # Update Bayesian data
            self.active_prediction.bayesian_confidence = bayesian_result.get('confidence') if bayesian_result else None
            self.active_prediction.bayesian_reasoning = bayesian_result.get('reasoning') if bayesian_result else None
            # Update timeframe data
            self.active_prediction.timeframe_adjusted_confidence = timeframe_result.get('confidence') if timeframe_result else None
            self.active_prediction.timeframe_reasoning = timeframe_result.get('reasoning') if timeframe_result else None
            self.active_prediction.expected_hold_time_seconds = timeframe_result.get('expected_hold_time') if timeframe_result else None
            # Update calibration data
            self.active_prediction.calibrated_confidence = calibrated_result.get('confidence') if calibrated_result else None
            self.active_prediction.calibration_adjustment = calibrated_result.get('adjustment') if calibrated_result else None
            # Update Kelly position sizing
            self.active_prediction.kelly_position_pct = kelly_result.get('position_pct') if kelly_result else None
            self.active_prediction.kelly_position_dollars = kelly_result.get('position_dollars') if kelly_result else None
            # Update FINAL CONFIDENCE - incorporates all factors
            self.active_prediction.final_confidence = final_confidence
            
            self.updates_count += 1
            
            # Check if ready to execute
            if confidence >= self.confidence_threshold:
                self.active_prediction.ready_to_execute = True
                self.active_prediction.execution_reason = f"Confidence {confidence:.1%} >= {self.confidence_threshold:.1%}"
                logger.success(f"✅ EXECUTE: {direction} @ ${entry_price:,.2f} ({confidence:.1%})")
                return "EXECUTE"
            
            # Log confidence change
            if confidence > old_confidence:
                logger.info(f"📈 Confidence: {old_confidence:.1%} → {confidence:.1%} (+{confidence - old_confidence:.1%})")
            elif confidence < old_confidence:
                logger.info(f"📉 Confidence: {old_confidence:.1%} → {confidence:.1%} ({confidence - old_confidence:.1%})")
            
            # Check if prediction is too old
            if self.active_prediction.age_seconds > self.max_prediction_age:
                logger.warning(f"⏰ Prediction expired: {self.active_prediction.age_seconds:.0f}s old")
                self.active_prediction = None
                return "CANCELLED"
            
            return "UPDATED"
            
        except Exception as e:
            logger.error(f"❌ Prediction update failed: {e}")
            return "NO_SIGNAL"
    
    # ==========================================
    # MODULE 1: DIRECTION RECOGNITION
    # ==========================================
    
    def recognize_direction(self, market_data: Dict[str, Any], forced_direction: Optional[str] = None) -> Tuple[str, float, List[str]]:
        """
        Recognize market direction using multiple signals
        
        WEIGHTS (optimized for high-leverage range trading):
        - RSI: 35% (PRIMARY - mean reversion signals)
        - S/R: 35% (Price position relative to key levels)
        - Patterns: 20% (Chart pattern setups)
        - Trend: 10% (15min: 3%, 2-hour: 7%)
        - Pressure: ~5% (Confirmation only)
        
        Trends:
        - Short-term (15min): Momentum confirmation
        - Medium-term (2-hour): Intraday trend direction
        - 7-day status: Confidence adjustment only (±5%)
        
        Returns:
            (direction, score, reasoning)
            - direction: "LONG" or "SHORT" (never NEUTRAL)
            - score: -1.0 (strong SHORT) to +1.0 (strong LONG)
            - reasoning: List of human-readable reasons
        """
        score = 0.0
        reasoning = []
        
        # Check if we're in a low-volatility range trading scenario
        volatility_category = market_data.get("volatility_category", "MODERATE")
        volatility_5m = market_data.get("volatility_5m", 0.0)
        is_range_trading = volatility_category in ["LOW", "VERY_LOW"] and volatility_5m < 0.01
        
        # 1. RSI ANALYSIS (Weight: 35% - PRIMARY for short-term mean reversion)
        rsi = market_data.get("rsi", 50)
        
        if is_range_trading:
            # For range trading: More sensitive RSI thresholds
            if rsi < 30:
                score += 0.35
                reasoning.append(f"🔴 RSI oversold ({rsi:.1f}) - STRONG BUY signal (range trading)")
            elif rsi < 45:
                score += 0.20
                reasoning.append(f"🟠 RSI below neutral ({rsi:.1f}) - bullish bias (range trading)")
            elif rsi < 55:
                score += 0.10
                reasoning.append(f"🟡 RSI slightly bullish ({rsi:.1f}) - weak long signal")
            elif rsi > 70:
                score -= 0.35
                reasoning.append(f"🔴 RSI overbought ({rsi:.1f}) - STRONG SELL signal (range trading)")
            elif rsi > 55:
                score -= 0.20
                reasoning.append(f"🟠 RSI above neutral ({rsi:.1f}) - bearish bias (range trading)")
            elif rsi > 45:
                score -= 0.10
                reasoning.append(f"🟡 RSI slightly bearish ({rsi:.1f}) - weak short signal")
            else:
                reasoning.append(f"⚪ RSI neutral ({rsi:.1f}) - range trading")
        else:
            # Original momentum trading thresholds
            if rsi < 25:
                score += 0.35
                reasoning.append(f"🔴 RSI extremely oversold ({rsi:.1f}) - STRONG BUY signal")
            elif rsi < 30:
                score += 0.25
                reasoning.append(f"🟠 RSI oversold ({rsi:.1f}) - strong reversal signal")
            elif rsi < 40:
                score += 0.15
                reasoning.append(f"🟡 RSI below neutral ({rsi:.1f}) - bullish bias")
            elif rsi > 75:
                score -= 0.35
                reasoning.append(f"🔴 RSI extremely overbought ({rsi:.1f}) - STRONG SELL signal")
            elif rsi > 70:
                score -= 0.25
                reasoning.append(f"🟠 RSI overbought ({rsi:.1f}) - strong reversal signal")
            elif rsi > 60:
                score -= 0.15
                reasoning.append(f"🟡 RSI above neutral ({rsi:.1f}) - bearish bias")
            else:
                reasoning.append(f"⚪ RSI neutral ({rsi:.1f})")
        
        # 2. DUAL-TIMEFRAME TREND ANALYSIS
        # Short-term (15min) - Momentum confirmation (3%)
        # Medium-term (2-hour) - Intraday trend direction (7%)
        # Total: 10% weight
        
        trend_short = market_data.get("trend_short", "SIDEWAYS")
        trend_medium = market_data.get("trend_medium", "SIDEWAYS")
        
        # Short-term trend - Momentum confirmation (3% weight)
        if "STRONG_UPTREND" in trend_short:
            score += 0.03
            reasoning.append("📈 Strong short-term momentum (15min)")
        elif "STRONG_DOWNTREND" in trend_short:
            score -= 0.03
            reasoning.append("📉 Strong short-term momentum (15min)")
        
        # Medium-term trend - Intraday direction (7% weight)
        if "STRONG_UPTREND" in trend_medium:
            score += 0.07
            reasoning.append("📈 Strong 2-hour uptrend")
        elif "UPTREND" in trend_medium and "WEAK" not in trend_medium:
            score += 0.04
            reasoning.append("📈 2-hour uptrend")
        elif "STRONG_DOWNTREND" in trend_medium:
            score -= 0.07
            reasoning.append("📉 Strong 2-hour downtrend")
        elif "DOWNTREND" in trend_medium and "WEAK" not in trend_medium:
            score -= 0.04
            reasoning.append("📉 2-hour downtrend")
        
        # 3. SUPPORT/RESISTANCE (Weight: 35% for range trading, 30% for momentum)
        current_price = market_data.get("current_price", 0)
        support_resistance = market_data.get("support_resistance", {})
        nearest_support = support_resistance.get("nearest_support", {})
        nearest_resistance = support_resistance.get("nearest_resistance", {})
        
        if nearest_support and nearest_resistance:
            support_price = nearest_support.get("price", 0)
            resistance_price = nearest_resistance.get("price", 0)
            
            if support_price and resistance_price and current_price:
                # Calculate position in range
                range_size = resistance_price - support_price
                if range_size > 0:
                    position_in_range = (current_price - support_price) / range_size
                    
                    if is_range_trading:
                        # For range trading: More sensitive thresholds and higher weights
                        if position_in_range < 0.20:  # Within 20% of support
                            score += 0.35
                            reasoning.append(f"🟢 Near support ${support_price:,.0f} - strong bounce potential (range trading)")
                        elif position_in_range < 0.35:  # Within 35% of support
                            score += 0.25
                            reasoning.append(f"🟢 Approaching support ${support_price:,.0f} - bounce potential")
                        elif position_in_range < 0.50:  # Lower half of range
                            score += 0.15
                            reasoning.append(f"🟡 Lower half of range - bullish bias")
                        elif position_in_range > 0.80:  # Within 20% of resistance
                            score -= 0.35
                            reasoning.append(f"🔴 Near resistance ${resistance_price:,.0f} - strong rejection risk (range trading)")
                        elif position_in_range > 0.65:  # Within 35% of resistance
                            score -= 0.25
                            reasoning.append(f"🔴 Approaching resistance ${resistance_price:,.0f} - rejection risk")
                        elif position_in_range > 0.50:  # Upper half of range
                            score -= 0.15
                            reasoning.append(f"🟡 Upper half of range - bearish bias")
                    else:
                        # Original momentum trading thresholds
                        if position_in_range < 0.15:
                            score += 0.30
                            reasoning.append(f"🟢 Near support ${support_price:,.0f} - bounce potential")
                        elif position_in_range < 0.30:
                            score += 0.18
                            reasoning.append(f"🟢 Approaching support ${support_price:,.0f}")
                        elif position_in_range > 0.85:
                            score -= 0.30
                            reasoning.append(f"🔴 Near resistance ${resistance_price:,.0f} - rejection risk")
                        elif position_in_range > 0.70:
                            score -= 0.18
                            reasoning.append(f"🔴 Approaching resistance ${resistance_price:,.0f}")
        
        # 4. PATTERN ANALYSIS (Weight: up to 20% - pattern-specific)
        pattern_analysis = market_data.get("pattern_analysis", {})
        patterns_dict = pattern_analysis.get("patterns", {})
        
        # Pattern weights from PatternRecognitionEngine
        pattern_weights = {
            # Tier 1: Strong Reversal Patterns (18-20%)
            "HEAD_SHOULDERS": 0.20, "INVERSE_HEAD_SHOULDERS": 0.20,
            "DOUBLE_TOP": 0.18, "DOUBLE_BOTTOM": 0.18,
            # Tier 2: Triangle Patterns (14-16%)
            "ASCENDING_TRIANGLE": 0.16, "DESCENDING_TRIANGLE": 0.16,
            "SYMMETRICAL_TRIANGLE": 0.14,
            # Tier 3: Wedge Patterns (14-16%)
            "FALLING_WEDGE": 0.16, "RISING_WEDGE": 0.16,
            # Tier 4: Engulfing Patterns (15%)
            "BULLISH_ENGULFING": 0.15, "BEARISH_ENGULFING": 0.15,
            # Tier 5: Three Soldiers/Crows (14%)
            "THREE_WHITE_SOLDIERS": 0.14, "THREE_BLACK_CROWS": 0.14,
            # Tier 6: Hammer/Shooting Star (12%)
            "HAMMER": 0.12, "INVERTED_HAMMER": 0.12,
            "SHOOTING_STAR": 0.12, "HANGING_MAN": 0.12,
            # Tier 7: Channel Patterns (10-12%)
            "ASCENDING_CHANNEL": 0.12, "DESCENDING_CHANNEL": 0.12,
            "HORIZONTAL_CHANNEL": 0.10,
            # Tier 8: Continuation Patterns (10%)
            "BULLISH_CONTINUATION": 0.10, "BEARISH_CONTINUATION": 0.10,
            "TREND_CHANGE": 0.10,
            # Tier 9: Doji Patterns (8%)
            "DOJI": 0.08, "DRAGONFLY_DOJI": 0.08, "GRAVESTONE_DOJI": 0.08,
        }
        
        # Apply pattern-specific weights
        pattern_score = 0
        pattern_count = 0
        for pattern_type, pattern_list in patterns_dict.items():
            if isinstance(pattern_list, list):
                for pattern in pattern_list:
                    pattern_name = pattern.get("pattern", "")
                    pattern_direction = pattern.get("direction", "NEUTRAL")
                    pattern_confidence = pattern.get("confidence", 0.5)
                    pattern_weight = pattern_weights.get(pattern_name, 0.10)  # Default 10%
                    
                    if pattern_direction == "BULLISH":
                        pattern_contribution = pattern_weight * pattern_confidence
                        pattern_score += pattern_contribution
                        reasoning.append(f"🟢 {pattern_name} (bullish, +{pattern_contribution*100:.1f}%)")
                        pattern_count += 1
                    elif pattern_direction == "BEARISH":
                        pattern_contribution = pattern_weight * pattern_confidence
                        pattern_score -= pattern_contribution
                        reasoning.append(f"🔴 {pattern_name} (bearish, -{pattern_contribution*100:.1f}%)")
                        pattern_count += 1
                    elif pattern_name == "TREND_CHANGE":
                        # FIXED: TREND_CHANGE patterns should be handled differently for range trading
                        if is_range_trading:
                            # For range trading, trend changes can be mean reversion opportunities
                            pattern_contribution = pattern_weight * pattern_confidence * 0.5  # Reduce impact
                            if pattern_direction == "BULLISH" and direction == "LONG":
                                pattern_score += pattern_contribution
                                reasoning.append(f"🔄 {pattern_name} (trend change, +{pattern_contribution*100:.1f}%)")
                            elif pattern_direction == "BEARISH" and direction == "SHORT":
                                pattern_score += pattern_contribution
                                reasoning.append(f"🔄 {pattern_name} (trend change, +{pattern_contribution*100:.1f}%)")
                            else:
                                # Trend change against direction - still opportunity for range trading
                                pattern_contribution = pattern_weight * pattern_confidence * 0.3  # Smaller boost
                                pattern_score += pattern_contribution
                                reasoning.append(f"🔄 {pattern_name} (mean reversion opportunity, +{pattern_contribution*100:.1f}%)")
                        else:
                            # For momentum strategies, trend changes are penalties
                            pattern_contribution = pattern_weight * pattern_confidence
                            pattern_score -= pattern_contribution
                            reasoning.append(f"🔄 {pattern_name} (trend change, -{pattern_contribution*100:.1f}%)")
                        pattern_count += 1
                    elif pattern_direction == "NEUTRAL" and pattern_name == "DOJI":
                        # Doji reduces confidence but doesn't affect direction much
                        reasoning.append(f"⚪ {pattern_name} (indecision)")
        
        # Apply pattern score (capped at ±0.20 to prevent over-weighting)
        pattern_score = max(-0.20, min(0.20, pattern_score))
        score += pattern_score
        
        # Normalize score to -1.0 to 1.0 (before pressure confirmation)
        score = max(-1.0, min(1.0, score))
        
        # Determine initial direction (without pressure)
        # ALWAYS choose LONG or SHORT - never NEUTRAL
        if forced_direction:
            # Use forced direction for confidence comparison
            direction = forced_direction
            reasoning.append(f"🎯 Forced direction: {forced_direction}")
        elif score >= 0:
            direction = "LONG"
        else:
            direction = "SHORT"
        
        # 5. ORDERBOOK PRESSURE - MOMENTUM CONFIRMATION ONLY
        # Only applies as confirmation, not to create direction
        pressure_data = market_data.get("pressure_data", {})
        pressure = pressure_data.get("direction", "NEUTRAL")
        
        # Check if pressure CONFIRMS the direction
        if direction == "LONG":
            if pressure == "STRONG_BUY":
                score += 0.05  # Reduced weight - confirmation only
                reasoning.append("✅ Strong buy pressure confirms LONG momentum")
            elif pressure == "BUY":
                score += 0.03
                reasoning.append("✅ Buy pressure confirms LONG momentum")
            elif pressure in ["SELL", "STRONG_SELL"]:
                # Pressure contradicts direction - warning but don't flip
                reasoning.append("⚠️ Sell pressure contradicts LONG signal (caution)")
            else:
                reasoning.append("⚪ Neutral pressure (no confirmation)")
        
        elif direction == "SHORT":
            if pressure == "STRONG_SELL":
                score -= 0.05  # Reduced weight - confirmation only
                reasoning.append("✅ Strong sell pressure confirms SHORT momentum")
            elif pressure == "SELL":
                score -= 0.03
                reasoning.append("✅ Sell pressure confirms SHORT momentum")
            elif pressure in ["BUY", "STRONG_BUY"]:
                # Pressure contradicts direction - warning but don't flip
                reasoning.append("⚠️ Buy pressure contradicts SHORT signal (caution)")
            else:
                reasoning.append("⚪ Neutral pressure (no confirmation)")
        
        # Final normalization after pressure confirmation
        score = max(-1.0, min(1.0, score))
        
        logger.info(f"🎯 Direction: {direction} (score: {score:+.3f})")
        
        return direction, score, reasoning
    
    # ==========================================
    # MODULE 2: ENTRY PRICE CALCULATION
    # ==========================================
    
    def calculate_entry_price(self, current_price: float, direction: str, 
                             market_data: Dict[str, Any]) -> float:
        """
        Calculate optimal entry price close to current market price
        Entry should be achievable within 1-2 minutes
        
        Returns:
            entry_price: Optimal limit order price
        """
        volatility = market_data.get("volatility_5m", 0.01)
        pressure = market_data.get("pressure_data", {}).get("direction", "NEUTRAL")
        volume_category = market_data.get("volume_category", "NORMAL")
        
        # Calculate base offset based on volatility
        if volatility < 0.005:  # VERY LOW volatility
            base_offset_pct = 0.0003  # 0.03% (very tight)
        elif volatility < 0.01:  # LOW volatility
            base_offset_pct = 0.0005  # 0.05%
        elif volatility < 0.02:  # MODERATE volatility
            base_offset_pct = 0.001   # 0.1%
        elif volatility < 0.03:  # HIGH volatility
            base_offset_pct = 0.0015  # 0.15%
        else:  # EXTREME volatility
            base_offset_pct = 0.002   # 0.2%
        
        # Adjust offset based on market pressure and volume
        if direction == "LONG":
            # For LONG: Want to buy below current price
            
            # If strong buy pressure + high volume, use tighter offset (price moving up)
            if pressure in ["BUY", "STRONG_BUY"] and volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
                offset_pct = base_offset_pct * 0.5  # Closer to market
                logger.debug(f"📍 Tight entry: Strong buying pressure")
            else:
                offset_pct = base_offset_pct
            
            entry_price = current_price * (1 - offset_pct)
            
            # Check if near support - align with support level
            support_resistance = market_data.get("support_resistance", {})
            nearest_support = support_resistance.get("nearest_support", {}).get("price", 0)
            
            if nearest_support:
                distance_to_support = abs(entry_price - nearest_support) / current_price
                if distance_to_support < 0.002:  # Within 0.2%
                    entry_price = nearest_support
                    logger.info(f"📍 Entry aligned with support: ${entry_price:,.2f}")
        
        else:  # SHORT
            # For SHORT: Want to sell above current price
            
            if pressure in ["SELL", "STRONG_SELL"] and volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
                offset_pct = base_offset_pct * 0.5
                logger.debug(f"📍 Tight entry: Strong selling pressure")
            else:
                offset_pct = base_offset_pct
            
            entry_price = current_price * (1 + offset_pct)
            
            # Check if near resistance - align with resistance level
            support_resistance = market_data.get("support_resistance", {})
            nearest_resistance = support_resistance.get("nearest_resistance", {}).get("price", 0)
            
            if nearest_resistance:
                distance_to_resistance = abs(entry_price - nearest_resistance) / current_price
                if distance_to_resistance < 0.002:
                    entry_price = nearest_resistance
                    logger.info(f"📍 Entry aligned with resistance: ${entry_price:,.2f}")
        
        logger.info(f"📍 Entry price: ${entry_price:,.2f} (offset: {abs(entry_price - current_price) / current_price:.3%})")
        
        return round(entry_price, 2)
    
    # ==========================================
    # MODULE 3: CONFIDENCE CALCULATION
    # ==========================================
    
    def calculate_confidence(self, direction: str, score: float, 
                           market_data: Dict[str, Any]) -> Tuple[float, float, List[Tuple[str, float]], List[str]]:
        """
        Calculate prediction confidence with boost system
        
        Returns:
            (final_confidence, base_confidence, boosts, reasoning)
        """
        # SCIENTIFIC BASE CONFIDENCE CALCULATION
        # Use sigmoid function to map score to confidence: C_base = tanh(|score|)
        # This provides smooth, bounded mapping from [-∞, +∞] to [0, 1]
        # Sigmoid ensures: score=0 → confidence=0, score=1 → confidence≈0.76, score=2 → confidence≈0.96
        import math
        base_confidence = math.tanh(abs(score))  # Sigmoid mapping for scientific accuracy
        
        confidence_boosts = []
        reasoning = []
        
        # Get ALL market metrics
        trend = market_data.get("trend", "SIDEWAYS")
        rsi = market_data.get("rsi", 50)
        volume_category = market_data.get("volume_category", "NORMAL")
        pressure = market_data.get("pressure_data", {}).get("direction", "NEUTRAL")
        pressure_strength = market_data.get("pressure_data", {}).get("strength", 0.0)
        volatility_category = market_data.get("volatility_category", "MODERATE")
        volatility_5m = market_data.get("volatility_5m", 0.0)
        market_status = market_data.get("market_conditions_analysis", {}).get("market_status", "NEUTRAL")
        market_quality = market_data.get("market_conditions_analysis", {}).get("market_quality", "UNKNOWN")
        sentiment = market_data.get("market_conditions_analysis", {}).get("sentiment", "NEUTRAL")
        pattern_setup = market_data.get("pattern_analysis", {}).get("market_setup", {}).get("setup", "")
        pattern_count = market_data.get("pattern_analysis", {}).get("pattern_count", 0)
        overall_pattern_confidence = market_data.get("pattern_analysis", {}).get("overall_confidence", 0.0)
        
        # Check if we're in a low-volatility range trading scenario
        is_range_trading = volatility_category in ["LOW", "VERY_LOW"] and volatility_5m < 0.01
        
        # Cross-asset and funding data
        cross_asset = market_data.get("cross_asset_analysis", {})
        funding_analysis = market_data.get("funding_analysis", {})
        funding_sentiment = funding_analysis.get("sentiment", "NEUTRAL")
        
        # Volume profile
        volume_profile = market_data.get("volume_profile_analysis", {})
        poc_distance = volume_profile.get("poc_distance_pct", 0.0) if volume_profile else 0.0
        
        # Global volume (Binance)
        global_volume_category = market_data.get("global_volume_category", "NORMAL")
        
        # ============================================================================
        # CONFIDENCE CALCULATION: Weighted aggregation of market factors
        # ============================================================================
        # WEIGHTS EXPLANATION:
        #   20% - Expected Value (profitability - most important)
        #   15% - RSI Signal (technical strength)
        #   10% - Volume Confirmation (market participation)
        #   8%  - Orderbook Pressure (momentum with volume)
        #   6%  - Pattern Confirmation (technical setup)
        #   5%  - Macro Trend (7-day alignment)
        #   10% - S/R Proximity (entry/exit quality)
        #   8%  - Market Quality (tradability)
        #   8%  - Range Trading (optimal for 40x leverage)
        #   -12% - Volatility Penalty (risk management)
        #   10% - Minor factors (sentiment, funding, correlations)
        # 
        # Total possible boost: ~80% | Total possible penalty: ~25%
        # ============================================================================
        
        # CORE FACTOR 1: Expected Value (20% weight - profitability)
        # Simple logic: Positive EV = good trade, Negative EV = bad trade
        ev_percent = market_data.get("expected_value", 0.0) or 0.0
        
        if ev_percent > 0.1:      # > 0.1% EV = Very good trade
            ev_boost = 0.20
            confidence_boosts.append(("Excellent EV", ev_boost))
            reasoning.append(f"✅ Strong positive EV +{ev_percent:.2%} (+{ev_boost:.0%})")
        elif ev_percent > 0.05:   # > 0.05% EV = Good trade
            ev_boost = 0.10
            confidence_boosts.append(("Good EV", ev_boost))
            reasoning.append(f"✅ Positive EV +{ev_percent:.2%} (+{ev_boost:.0%})")
        elif ev_percent < -0.05:  # < -0.05% EV = Bad trade
            ev_boost = -0.25
            confidence_boosts.append(("Negative EV", ev_boost))
            reasoning.append(f"❌ Negative EV {ev_percent:.2%} ({ev_boost:.0%})")
        # EV between -0.05% and +0.05% = neutral, no adjustment
        
        # CORE FACTOR 2: RSI Signal Strength
        # Simple logic: RSI extremes favor mean reversion trades
        rsi_boost = 0.0
        if direction == "LONG" and rsi < 30:     # Very oversold
            rsi_boost = 0.15
            confidence_boosts.append(("RSI very oversold", rsi_boost))
            reasoning.append(f"✅ RSI {rsi:.0f} very oversold (+{rsi_boost:.0%})")
        elif direction == "SHORT" and rsi > 70:  # Very overbought
            rsi_boost = 0.15
            confidence_boosts.append(("RSI very overbought", rsi_boost))
            reasoning.append(f"✅ RSI {rsi:.0f} very overbought (+{rsi_boost:.0%})")
        elif direction == "LONG" and rsi < 40:   # Oversold
            rsi_boost = 0.08
            confidence_boosts.append(("RSI oversold", rsi_boost))
            reasoning.append(f"✅ RSI {rsi:.0f} oversold (+{rsi_boost:.0%})")
        elif direction == "SHORT" and rsi > 60:  # Overbought
            rsi_boost = 0.08
            confidence_boosts.append(("RSI overbought", rsi_boost))
            reasoning.append(f"✅ RSI {rsi:.0f} overbought (+{rsi_boost:.0%})")
        
        # CORE FACTOR 3: Volume Confirmation
        # Simple logic: High volume = strong signal, Low volume = weak signal
        # EXCEPTION: Range trading strategies work well in low volume
        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            boost = 0.10
            confidence_boosts.append(("High volume", boost))
            reasoning.append(f"✅ High volume confirms move (+{boost:.0%})")
        elif volume_category in ["LOW", "VERY_LOW"]:
            # Don't penalize low volume if we're in range trading scenario
            if not is_range_trading:
                boost = -0.05
                confidence_boosts.append(("Low volume", boost))
                reasoning.append(f"⚠️ Low volume weakens signal ({boost:.0%})")
            else:
                # Low volume is actually ideal for range trading
                reasoning.append(f"ℹ️ Low volume - normal for range trading")
        
        # CORE FACTOR 4: Orderbook Pressure (only with high volume)
        # High volume + aligned pressure = strong momentum
        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            if (direction == "LONG" and pressure in ["BUY", "STRONG_BUY"]) or \
               (direction == "SHORT" and pressure in ["SELL", "STRONG_SELL"]):
                boost = 0.08
                confidence_boosts.append(("Strong momentum", boost))
                reasoning.append(f"✅ High volume + {pressure} pressure (+{boost:.0%})")
            elif (direction == "LONG" and pressure in ["SELL", "STRONG_SELL"]) or \
                 (direction == "SHORT" and pressure in ["BUY", "STRONG_BUY"]):
                penalty = -0.08
                confidence_boosts.append(("Conflicting pressure", penalty))
                reasoning.append(f"❌ High volume + opposite pressure ({penalty:.0%})")
        
        # CORE FACTOR 5: Pattern Confirmation
        if (direction == "LONG" and "BULLISH" in pattern_setup) or \
           (direction == "SHORT" and "BEARISH" in pattern_setup):
            boost = 0.06
            confidence_boosts.append(("Pattern confirmation", boost))
            reasoning.append(f"✅ Pattern confirms {direction} (+{boost:.0%})")
        
        # CORE FACTOR 6: Macro Trend Alignment (7-day trend)
        # Range trading is less affected by macro trends (trades mean reversion)
        if (direction == "LONG" and market_status == "BULLISH") or \
           (direction == "SHORT" and market_status == "BEARISH"):
            boost = 0.05
            confidence_boosts.append(("Trend aligned", boost))
            reasoning.append(f"✅ 7-day trend supports {direction} (+{boost:.0%})")
        elif (direction == "LONG" and market_status == "BEARISH") or \
             (direction == "SHORT" and market_status == "BULLISH"):
            # FIXED: Range trading should NOT be penalized for counter-trend trades
            # Range trading strategies are designed for mean reversion
            if is_range_trading:
                # For range trading, counter-trend trades are opportunities but not huge boosts
                boost = 0.01  # Small boost for mean reversion opportunity
                confidence_boosts.append(("Mean reversion opportunity", boost))
                reasoning.append(f"✅ Range trading - mean reversion opportunity (+{boost:.0%})")
            else:
                # Only apply penalty to momentum strategies
                penalty = -0.05
                confidence_boosts.append(("Trend opposed", penalty))
                reasoning.append(f"⚠️ Fighting trend ({penalty:.0%})")
        
        # CORE FACTOR 7: Support/Resistance Proximity (10% weight - entry/exit quality)
        current_price = market_data.get("current_price", 0)
        support_resistance = market_data.get("support_resistance", {})
        
        if direction == "LONG":
            nearest_support = support_resistance.get("nearest_support", {}).get("price", 0)
            if nearest_support and current_price:
                distance_pct = abs(current_price - nearest_support) / current_price
                if distance_pct < 0.01:  # Within 1%
                    boost = 0.10
                    confidence_boosts.append(("Near support", boost))
                    reasoning.append(f"✅ Price near support ${nearest_support:,.0f} (+{boost:.0%})")
        elif direction == "SHORT":
            nearest_resistance = support_resistance.get("nearest_resistance", {}).get("price", 0)
            if nearest_resistance and current_price:
                distance_pct = abs(current_price - nearest_resistance) / current_price
                if distance_pct < 0.01:
                    boost = 0.10
                    confidence_boosts.append(("Near resistance", boost))
                    reasoning.append(f"✅ Price near resistance ${nearest_resistance:,.0f} (+{boost:.0%})")
        
        # CORE FACTOR 8: Market Quality (8% weight - tradability)
        if market_quality == "EXCELLENT":
            boost = 0.08
            confidence_boosts.append(("Excellent market", boost))
            reasoning.append(f"✅ Excellent market quality (+{boost:.0%})")
        elif market_quality == "GOOD":
            boost = 0.04
            confidence_boosts.append(("Good market", boost))
            reasoning.append(f"✅ Good market quality (+{boost:.0%})")
        elif market_quality == "POOR":
            penalty = -0.10
            confidence_boosts.append(("Poor market", penalty))
            reasoning.append(f"❌ Poor market quality ({penalty:.0%})")
        
        # SECONDARY FACTOR 1: Range Trading Moderation (range trading should be more conservative)
        if is_range_trading:
            # Range trading is inherently more conservative - smaller boosts
            boost = 0.03  # Reduced from 8% to 3%
            confidence_boosts.append(("Range trading", boost))
            reasoning.append(f"✅ Range trading - conservative mean reversion (+{boost:.0%})")
            
            # RSI extremes are good for range trading but not as strong as momentum strategies
            if direction == "LONG" and rsi < 30:
                boost = 0.02  # Reduced from 5% to 2%
                confidence_boosts.append(("RSI extreme for range trading", boost))
                reasoning.append(f"✅ RSI {rsi:.0f} - good for range trading mean reversion (+{boost:.0%})")
            elif direction == "SHORT" and rsi > 70:
                boost = 0.02  # Reduced from 5% to 2%
                confidence_boosts.append(("RSI extreme for range trading", boost))
                reasoning.append(f"✅ RSI {rsi:.0f} - good for range trading mean reversion (+{boost:.0%})")
            
            # High volume in range trading is less significant than in momentum strategies
            if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
                boost = 0.01  # Reduced from 3% to 1%
                confidence_boosts.append(("High volume for range trading", boost))
                reasoning.append(f"✅ High volume - moderate mean reversion signal (+{boost:.0%})")
        
        # SECONDARY FACTOR 2: Volatility Penalty (reduces risk in chaotic markets)
        if volatility_category == "EXTREME":
            penalty = -0.12
            confidence_boosts.append(("Extreme volatility", penalty))
            reasoning.append(f"❌ Extreme volatility - high risk ({penalty:.0%})")
        elif volatility_category == "HIGH":
            penalty = -0.06
            confidence_boosts.append(("High volatility", penalty))
            reasoning.append(f"⚠️ High volatility ({penalty:.0%})")
        
        # MINOR FACTORS (3-4% each - fine-tuning)
        
        # Market sentiment alignment
        if (direction == "LONG" and sentiment in ["GREED", "EXTREME_GREED"]) or \
           (direction == "SHORT" and sentiment in ["FEAR", "EXTREME_FEAR"]):
            boost = 0.03
            confidence_boosts.append(("Sentiment aligned", boost))
            reasoning.append(f"✅ Sentiment {sentiment} (+{boost:.0%})")
        
        # Funding rate alignment
        if funding_sentiment != "NEUTRAL":
            if (direction == "LONG" and funding_sentiment == "BULLISH") or \
               (direction == "SHORT" and funding_sentiment == "BEARISH"):
                boost = 0.03
                confidence_boosts.append(("Funding aligned", boost))
                reasoning.append(f"✅ Funding {funding_sentiment} (+{boost:.0%})")
        
        # Global volume confirmation
        if global_volume_category in ["HIGH", "VERY_HIGH"]:
            boost = 0.03
            confidence_boosts.append(("High global volume", boost))
            reasoning.append(f"✅ High global volume (+{boost:.0%})")
        
        # Volume profile - Price near POC
        if isinstance(poc_distance, (int, float)) and poc_distance and abs(poc_distance) < 0.01:
            boost = 0.03
            confidence_boosts.append(("Near POC", boost))
            reasoning.append(f"✅ Price near POC (+{boost:.0%})")
        
        # Cross-asset correlation (minor, 2% weight)
        if cross_asset:
            dxy_corr = cross_asset.get("dxy_correlation", 0)
            if isinstance(dxy_corr, (int, float)):
                if direction == "LONG" and dxy_corr < -0.5:
                    boost = 0.02
                    confidence_boosts.append(("DXY correlation", boost))
                    reasoning.append(f"✅ DXY correlation (+{boost:.0%})")
                elif direction == "SHORT" and dxy_corr > 0.5:
                    boost = 0.02
                    confidence_boosts.append(("DXY correlation", boost))
                    reasoning.append(f"✅ DXY correlation (+{boost:.0%})")
        
        # FIXED: Pattern conflict handling for range trading
        if pattern_count >= 2:
            if (direction == "LONG" and "BEARISH" in pattern_setup) or \
               (direction == "SHORT" and "BULLISH" in pattern_setup):
                # For range trading, conflicting patterns can be mean reversion opportunities
                if is_range_trading:
                    # Range trading can benefit from conflicting patterns (mean reversion)
                    boost = 0.01  # Very small boost for mean reversion setup
                    confidence_boosts.append(("Mean reversion setup", boost))
                    reasoning.append(f"✅ Range trading - mean reversion setup (+{boost:.0%})")
                else:
                    # Only apply penalty to momentum strategies
                    penalty = -0.05
                    confidence_boosts.append(("Conflicting patterns", penalty))
                    reasoning.append(f"⚠️ Pattern conflict ({penalty:.0%})")
        
        # ============================================================================
        # FINAL CONFIDENCE CALCULATION
        # ============================================================================
        # Formula: C_final = C_base + Σ(all_boosts_and_penalties)
        # C_base = tanh(|score|) - base confidence from ML model
        # All factors are additive and independent
        # Final confidence is bounded [0, 1] for probability interpretation
        # ============================================================================
        
        final_confidence = base_confidence
        for reason, boost in confidence_boosts:
            final_confidence += boost
        
        # Apply bounds [0, 1]
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        # Log confidence calculation
        if confidence_boosts:
            boosts_count = len([b for r, b in confidence_boosts if b > 0])
            penalties_count = len([b for r, b in confidence_boosts if b < 0])
            logger.info(f"📊 Confidence: {base_confidence:.1%} → {final_confidence:.1%} ({boosts_count} boosts, {penalties_count} penalties)")
        
        return final_confidence, base_confidence, confidence_boosts, reasoning
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    def _calculate_targets(self, entry_price: float, direction: str, score: float,
                          strategy: str, market_data: Dict[str, Any]) -> Tuple[float, float, float]:
        """Calculate stop loss, take profit, and risk/reward ratio - OPTIMIZED FOR 40X LEVERAGE"""
        
        # Strategy-specific risk parameters - 40X LEVERAGE OPTIMIZED
        if strategy == "scalping":
            stop_loss_pct = 0.001  # 0.1% (tight for 40x leverage)
            risk_reward = 2.0
        elif strategy == "spike_hunting":
            stop_loss_pct = 0.005  # 0.5% (reduced from 2% for 40x leverage)
            risk_reward = 3.0
        elif strategy == "trend_following":
            stop_loss_pct = 0.002  # 0.2% (tight for 40x leverage)
            risk_reward = 2.5
        elif strategy == "high_volatility":
            stop_loss_pct = 0.003  # 0.3% (reduced from 1.5% for 40x leverage)
            risk_reward = 2.0
        elif strategy == "range_trading":
            stop_loss_pct = 0.0015  # 0.15% (tight for range trading with 40x leverage)
            risk_reward = 2.0
        elif strategy == "low_volatility_range":
            stop_loss_pct = 0.001  # 0.1% (very tight for low volatility with 40x leverage)
            risk_reward = 2.0
        else:  # standard
            stop_loss_pct = 0.002  # 0.2% (reduced from 1% for 40x leverage)
            risk_reward = 2.0
        
        # Adjust based on score strength
        score_strength = abs(score)
        if score_strength > 0.7:
            risk_reward *= 1.2  # Wider targets for strong signals
        
        if direction == "LONG":
            stop_loss = entry_price * (1 - stop_loss_pct)
            take_profit = entry_price * (1 + (stop_loss_pct * risk_reward))
        else:  # SHORT
            stop_loss = entry_price * (1 + stop_loss_pct)
            take_profit = entry_price * (1 - (stop_loss_pct * risk_reward))
        
        return round(stop_loss, 2), round(take_profit, 2), risk_reward
    
    # ==========================================
    # MODULE 4: EXPECTED VALUE CALCULATION
    # ==========================================
    
    def _calculate_expected_value(
        self,
        confidence: float,
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        position_size: float
    ) -> ExpectedValue:
        """
        Calculate expected value for the trade using probability engine
        
        Args:
            confidence: Win probability (0-1)
            entry_price: Entry price
            take_profit: Take profit price
            stop_loss: Stop loss price
            position_size: Position size in dollars
            
        Returns:
            ExpectedValue object with detailed calculation
        """
        prob_engine = get_global_probability_engine()
        
        ev_result = prob_engine.calculate_expected_value(
            confidence=confidence,
            entry_price=entry_price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            position_size=position_size
        )
        
        return ev_result
    
    def _apply_bayesian_fusion(self, direction: str, market_data: Dict[str, Any], base_confidence: float) -> Optional[Dict[str, Any]]:
        """
        Apply Bayesian signal fusion to combine multiple market signals
        
        Returns:
            Dict with fused confidence and reasoning
        """
        try:
            bayesian = get_global_bayesian_fusion()
            
            # Convert market metrics to Bayesian signals
            signals = []
            
            # RSI signal
            rsi = market_data.get("rsi", 50)
            if rsi:
                rsi_signal = bayesian.calculate_signal_from_metric("RSI", rsi, "RSI", direction)
                if rsi_signal:
                    signals.append(rsi_signal)
                    logger.debug(f"🔍 Bayesian RSI signal: {rsi_signal.probability:.1%} confidence")
                else:
                    logger.debug(f"🔍 Bayesian RSI signal: None (RSI={rsi})")
            
            # Volume signal
            volume_category = market_data.get("volume_category", "MODERATE")
            if volume_category:
                volume_signal = bayesian.calculate_signal_from_metric("Volume", volume_category, "VOLUME", direction)
                if volume_signal:
                    signals.append(volume_signal)
                    logger.debug(f"🔍 Bayesian Volume signal: {volume_signal.probability:.1%} confidence")
                else:
                    logger.debug(f"🔍 Bayesian Volume signal: None (Volume={volume_category})")
            
            # Trend signals - use multiple timeframes and pick the highest confidence
            trend_5m = market_data.get("trend", "SIDEWAYS")
            trend_5m_data = market_data.get("trend_5m", {})
            trend_short = trend_5m_data.get("trend_short", "SIDEWAYS")
            trend_medium = trend_5m_data.get("trend_medium", "SIDEWAYS")
            
            # Calculate confidence for each timeframe
            trend_signals = []
            
            # 5m trend
            if trend_5m:
                trend_5m_signal = bayesian.calculate_signal_from_metric("Trend_5m", trend_5m, "TREND", direction)
                if trend_5m_signal:
                    trend_signals.append(trend_5m_signal)
                    logger.debug(f"🔍 Bayesian Trend_5m signal: {trend_5m_signal.probability:.1%} confidence")
            
            # Short-term trend (1m equivalent)
            if trend_short:
                trend_short_signal = bayesian.calculate_signal_from_metric("Trend_Short", trend_short, "TREND", direction)
                if trend_short_signal:
                    trend_signals.append(trend_short_signal)
                    logger.debug(f"🔍 Bayesian Trend_Short signal: {trend_short_signal.probability:.1%} confidence")
            
            # Medium-term trend (1h equivalent)
            if trend_medium:
                trend_medium_signal = bayesian.calculate_signal_from_metric("Trend_Medium", trend_medium, "TREND", direction)
                if trend_medium_signal:
                    trend_signals.append(trend_medium_signal)
                    logger.debug(f"🔍 Bayesian Trend_Medium signal: {trend_medium_signal.probability:.1%} confidence")
            
            # Use the trend signal with the highest confidence
            if trend_signals:
                best_trend_signal = max(trend_signals, key=lambda x: x.probability)
                signals.append(best_trend_signal)
                logger.debug(f"🔍 Best trend signal: {best_trend_signal.name} with {best_trend_signal.probability:.1%} confidence")
            else:
                logger.debug(f"🔍 No valid trend signals found")
            
            if not signals:
                logger.warning(f"⚠️ No Bayesian signals created for {direction}")
                return None
            
            # Fuse signals
            fused = bayesian.fuse_signals(signals, direction)
            logger.debug(f"🔍 Bayesian Fusion: {len(signals)} signals → {fused.posterior_probability:.1%}")
            
            return {
                'confidence': fused.posterior_probability,
                'reasoning': fused.reasoning
            }
        except Exception as e:
            logger.warning(f"⚠️ Bayesian fusion failed: {e}")
            return None
    
    def _apply_timeframe_adjustment(self, confidence: float, strategy: str) -> Optional[Dict[str, Any]]:
        """
        Adjust confidence based on expected holding timeframe
        
        Returns:
            Dict with adjusted confidence and reasoning
        """
        try:
            mtf = get_global_multitimeframe_probability()
            
            # Estimate expected hold time based on strategy
            hold_time_map = {
                "scalping": 300,  # 5 minutes
                "standard": 1800,  # 30 minutes
                "range_trading": 3600,  # 1 hour
                "trend_following": 7200,  # 2 hours
                "breakout": 900  # 15 minutes
            }
            
            expected_hold_time = hold_time_map.get(strategy, 1800)
            
            # Get probability adjustment
            adjusted_conf, reasoning = mtf.get_probability_adjustment(confidence, expected_hold_time)
            
            return {
                'confidence': adjusted_conf,
                'reasoning': reasoning,
                'expected_hold_time': expected_hold_time
            }
        except Exception as e:
            logger.warning(f"⚠️ Timeframe adjustment failed: {e}")
            return None
    
    def _apply_calibration(self, confidence: float) -> Optional[Dict[str, Any]]:
        """
        Apply historical calibration to adjust confidence
        
        Returns:
            Dict with calibrated confidence and adjustment
        """
        try:
            calibration = get_global_calibration_tracker()
            
            # Get calibrated confidence (returns tuple: (calibrated_conf, reasoning))
            calibrated_conf, reasoning = calibration.get_calibration_adjustment(confidence)
            adjustment = calibrated_conf - confidence
            
            return {
                'confidence': calibrated_conf,
                'adjustment': adjustment,
                'reasoning': reasoning
            }
        except Exception as e:
            logger.warning(f"⚠️ Calibration adjustment failed: {e}")
            return None
    
    def _calculate_kelly_position(
        self, 
        confidence: float, 
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        capital: float
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate Kelly-optimal position size
        
        Returns:
            Dict with position size in % and dollars
        """
        try:
            prob_engine = get_global_probability_engine()
            
            kelly_result = prob_engine.calculate_kelly_position_size(
                confidence=confidence,
                entry_price=entry_price,
                take_profit=take_profit,
                stop_loss=stop_loss,
                total_capital=capital
            )
            
            return {
                'position_pct': kelly_result['position_size_pct'],
                'position_dollars': kelly_result['position_size_dollars']
            }
        except Exception as e:
            logger.warning(f"⚠️ Kelly position calculation failed: {e}")
            return None
    
    def get_active_prediction(self) -> Optional[RealtimePrediction]:
        """Get the current active prediction (singleton)"""
        return self.active_prediction
    
    def clear_prediction(self):
        """Clear active prediction (after execution or manual reset)"""
        logger.info("🗑️ Clearing active prediction")
        self.active_prediction = None


# Global singleton
_global_realtime_prediction_engine = None

def get_global_realtime_prediction_engine() -> RealtimePredictionEngine:
    """Get global real-time prediction engine singleton"""
    global _global_realtime_prediction_engine
    if _global_realtime_prediction_engine is None:
        _global_realtime_prediction_engine = RealtimePredictionEngine()
    return _global_realtime_prediction_engine
