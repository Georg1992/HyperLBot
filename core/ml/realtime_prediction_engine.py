#!/usr/bin/env python3
"""
Real-Time Prediction Engine - Modular & Clean
Continuously analyzes market and generates predictions with growing confidence
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from core.ml.bayesian_fusion import get_global_bayesian_fusion, Signal
from core.ml.direction_recognizer import get_global_direction_recognizer
from core.ml.entry_price_calculator import create_entry_price_calculator
from core.ml.target_calculator import create_target_calculator
from core.ml.probability_engine import ExpectedValue, get_global_probability_engine


class PredictionPhase(Enum):
    """Prediction lifecycle phases"""
    MONITORING = "MONITORING"   # Confidence < threshold, building up
    BUILDING = "BUILDING"       # Confidence >= threshold, entry price finalized
    TRACKING = "TRACKING"       # Order placed, tracking execution


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
    
    # Note: All old confidence systems removed - only Bayesian fusion remains
    
    # SINGLE CONFIDENCE - incorporates all factors (simplified)
    # This is the only confidence field that matters for execution
    
    # EXECUTION
    ready_to_execute: bool = False
    execution_reason: str = ""
    
    # LIFECYCLE PHASE
    phase: str = "MONITORING"  # MONITORING, BUILDING, TRACKING
    order_id: Optional[str] = None  # Set when order is placed (TRACKING phase)
    
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
            "phase": self.phase,
            "order_id": self.order_id,
            "confidence_boosts": [{"reason": r, "boost": b} for r, b in self.confidence_boosts],
            # EV data
            "expected_value": self.expected_value,
            "expected_value_dollars": self.expected_value_dollars,
            "win_probability": self.win_probability,
            "ev_reasoning": self.ev_reasoning,
            "should_trade_ev": self.should_trade_ev,
            # Bayesian data (ONLY confidence system now)
            "bayesian_confidence": self.bayesian_confidence,
            "bayesian_reasoning": self.bayesian_reasoning
            # Note: confidence field above contains the final confidence value from Bayesian fusion
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
        from config.config import TradingConfig
        
        strategy_config = TradingConfig.STRATEGY_CONFIGS.get(strategy, {})
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
        Determine optimal direction by testing both LONG and SHORT to find highest confidence
        This is THE PRIMARY DIRECTION SELECTION method - chooses direction that maximizes confidence
        
        Strategy:
        1. Get natural direction from DirectionRecognizer (based on technical analysis)
        2. Calculate Bayesian confidence for BOTH directions (LONG and SHORT)
        3. Use combined score: DirectionRecognizer score (60%) + Bayesian confidence (40%)
        4. Pick direction with HIGHEST CONFIDENCE (primary criterion - what determines execution)
        5. Return the Bayesian result from the winning direction to avoid recalculation
        
        NOTE: This is called EVERY prediction update cycle to ensure we always pick the best direction
        
        Returns:
            tuple: (best_direction, best_score, best_confidence, best_reasoning, bayesian_result)
        """
        try:
            direction_recognizer = get_global_direction_recognizer()
            
            # Step 1: Get natural direction from technical analysis (without forcing)
            natural_direction, natural_score, natural_reasoning = direction_recognizer.recognize_direction(market_data, forced_direction=None)
            
            # Step 2: Calculate Bayesian confidence for both directions
            long_bayesian_result = self._apply_bayesian_fusion("LONG", market_data, 0.5)
            if not long_bayesian_result:
                raise RuntimeError("Bayesian fusion failed for LONG direction")
            long_confidence = long_bayesian_result['confidence']
            
            short_bayesian_result = self._apply_bayesian_fusion("SHORT", market_data, 0.5)
            if not short_bayesian_result:
                raise RuntimeError("Bayesian fusion failed for SHORT direction")
            short_confidence = short_bayesian_result['confidence']
            
            # Step 3: Calculate combined scores for both directions
            # DirectionRecognizer score (normalized to 0-1): (score + 1) / 2 gives 0-1 range
            long_technical_score = (natural_score + 1.0) / 2.0 if natural_direction == "LONG" else (1.0 - natural_score) / 2.0
            short_technical_score = (1.0 - natural_score) / 2.0 if natural_direction == "LONG" else (natural_score + 1.0) / 2.0
            
            # Combined score: 60% technical analysis, 40% Bayesian confidence
            long_combined = (long_technical_score * 0.60) + (long_confidence * 0.40)
            short_combined = (short_technical_score * 0.60) + (short_confidence * 0.40)
            
            # Step 4: Pick best direction based on HIGHEST CONFIDENCE (primary criterion)
            # We prioritize confidence because that's what determines execution readiness
            # Combined score is secondary - used for logging and context
            if long_confidence > short_confidence:
                # LONG has higher confidence - choose it
                best_direction = "LONG"
                best_score = natural_score if natural_direction == "LONG" else -natural_score
                best_confidence = long_confidence
                best_bayesian_result = long_bayesian_result
                best_reasoning = [
                    f"🎯 LONG chosen | Conf:{long_confidence:.1%} > SHORT:{short_confidence:.1%} | Combined:{long_combined:.1%} vs {short_combined:.1%}",
                    f"   Natural direction: {natural_direction} (score: {natural_score:+.3f})"
                ] + natural_reasoning
                logger.info(f"🎯 Direction: LONG | Confidence:{long_confidence:.1%} > SHORT:{short_confidence:.1%} | Combined:{long_combined:.1%} vs {short_combined:.1%}")
            else:
                # SHORT has higher or equal confidence - choose it
                best_direction = "SHORT"
                best_score = -natural_score if natural_direction == "LONG" else natural_score
                best_confidence = short_confidence
                best_bayesian_result = short_bayesian_result
                best_reasoning = [
                    f"🎯 SHORT chosen | Conf:{short_confidence:.1%} >= LONG:{long_confidence:.1%} | Combined:{short_combined:.1%} vs {long_combined:.1%}",
                    f"   Natural direction: {natural_direction} (score: {natural_score:+.3f})"
                ] + natural_reasoning
                logger.info(f"🎯 Direction: SHORT | Confidence:{short_confidence:.1%} >= LONG:{long_confidence:.1%} | Combined:{short_combined:.1%} vs {long_combined:.1%}")
            
            return best_direction, best_score, best_confidence, best_reasoning, best_bayesian_result
            
        except Exception as e:
            logger.error(f"❌ Optimal direction selection failed: {e}")
            raise RuntimeError(f"Direction selection failed: {e}")
    
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
            
            # ============================================================
            # MODULE 1: DIRECTION SELECTION (FIRST - chooses highest confidence)
            # ============================================================
            # This MUST be first: choose direction that maximizes confidence
            # We test both LONG and SHORT to find which gives higher confidence
            best_direction, best_score, best_confidence, best_reasoning, bayesian_result = self._find_optimal_direction(market_data)
            
            direction = best_direction
            score = best_score
            direction_reasoning_list = best_reasoning  # This is now a List[str]
            
            # Use the Bayesian confidence already calculated in _find_optimal_direction
            # This avoids redundant calculation
            if not bayesian_result:
                raise RuntimeError("Bayesian fusion result missing from direction selection")
            
            confidence = bayesian_result['confidence']
            confidence_reasoning_str = bayesian_result['reasoning']  # String from Bayesian
            final_confidence = confidence
            
            logger.info(f"🎯 Direction: {direction} | Confidence: {confidence:.1%} (from optimal direction selection)")
            
            # MODULE 2: ENTRY PRICE CALCULATION
            # Always recalculate entry_price (including TRACKING phase) to potentially improve confidence
            entry_price_calculator = create_entry_price_calculator()
            entry_price = entry_price_calculator.calculate_entry_price(
                current_price=current_price,
                direction=direction,
                market_data=market_data
            )
            
            # Store old entry_price for comparison (in any phase)
            old_entry_price = self.active_prediction.entry_price if self.active_prediction else None
            
            # MODULE 3: TARGET CALCULATION (stop loss, take profit, risk/reward)
            target_calculator = create_target_calculator()
            stop_loss, take_profit, risk_reward = target_calculator.calculate_targets(
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
            
            # DEBUG: Log confidence vs threshold for troubleshooting
            threshold = self.confidence_threshold
            if confidence >= threshold:
                logger.info(f"✅ CONFIDENCE SUFFICIENT: {confidence:.1%} >= {threshold:.1%} (READY TO TRADE)")
            else:
                logger.warning(f"⚠️ CONFIDENCE INSUFFICIENT: {confidence:.1%} < {threshold:.1%} (NO TRADE)")
            
            # REFACTORED: Use dedicated methods for SRP compliance
            if not self.active_prediction:
                return self._create_new_prediction(
                    direction, score, confidence, final_confidence, entry_price, stop_loss, take_profit,
                    risk_reward, 0.5, [], current_price, direction_reasoning_list, confidence_reasoning_str,
                    ev_result, bayesian_result, strategy
                )
            
            # Check for direction change
            if direction != self.active_prediction.direction:
                logger.warning(f"🔄 Direction changed: {self.active_prediction.direction} → {direction}")
                self.direction_changes += 1
                return self._create_new_prediction(
                    direction, score, confidence, final_confidence, entry_price, stop_loss, take_profit,
                    risk_reward, 0.5, [], current_price, direction_reasoning_list, confidence_reasoning_str,
                    ev_result, bayesian_result, strategy
                )
            
            # Update existing prediction (all phases: MONITORING, BUILDING, or TRACKING)
            # Entry price is recalculated in all phases to potentially improve confidence
            return self._update_existing_prediction(
                confidence, final_confidence, entry_price, stop_loss, take_profit, risk_reward,
                0.5, [], current_price, score, direction_reasoning_list, confidence_reasoning_str,
                ev_result, bayesian_result, strategy, old_entry_price
            )
            
        except Exception as e:
            logger.error(f"❌ Prediction update failed: {e}")
            raise RuntimeError(f"Prediction update failed: {e}")
    
    def _build_reasoning_list(self, direction_reasoning_list: List[str], confidence_reasoning_str: str,
                             ev_result: Any, bayesian_result: Optional[Dict]) -> List[str]:
        """
        Build reasoning list with ONLY Bayesian confidence reasoning (as it was working before)
        
        Args:
            direction_reasoning_list: List of direction analysis reasons (not used)
            confidence_reasoning_str: Bayesian confidence reasoning (string) - THIS IS WHAT WE WANT
            ev_result: Expected value result object (not used)
            bayesian_result: Bayesian fusion result dict (not used, already extracted in confidence_reasoning_str)
            
        Returns:
            List with single Bayesian confidence reasoning string for dashboard display
        """
        # Only return Bayesian confidence reasoning (what was working before)
        if confidence_reasoning_str:
            return [confidence_reasoning_str]
        
        # Fallback if no reasoning available
        return ["📋 Confidence analysis in progress..."]
    
    def _create_new_prediction(self, direction: str, score: float, confidence: float, final_confidence: float,
                              entry_price: float, stop_loss: float, take_profit: float, risk_reward: float,
                              base_confidence: float, boosts: List[Tuple[str, float]], current_price: float,
                              direction_reasoning_list: List[str], confidence_reasoning_str: str, ev_result: Any,
                              bayesian_result: Optional[Dict], strategy: str) -> str:
        """Create a new prediction (SRP: single responsibility)"""
        # Use the final calibrated confidence as the single confidence value
        single_confidence = final_confidence
        
        # Determine initial phase based on confidence
        initial_phase = PredictionPhase.BUILDING.value if single_confidence >= self.confidence_threshold else PredictionPhase.MONITORING.value
        
        self.active_prediction = RealtimePrediction(
            direction=direction,
            confidence=single_confidence,  # Single confidence field
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward,
            base_confidence=base_confidence,
            confidence_boosts=boosts,
            confidence_history=[single_confidence],
            current_price=current_price,
            score=score,
            reasoning=self._build_reasoning_list(direction_reasoning_list, confidence_reasoning_str, ev_result, bayesian_result),
            phase=initial_phase,  # Set initial phase
            order_id=None,  # No order yet
            # EV data
            expected_value=ev_result.ev_percent,
            expected_value_dollars=ev_result.ev_dollars,
            win_probability=ev_result.win_probability,
            ev_reasoning=ev_result.reasoning,
            should_trade_ev=ev_result.should_trade,
            # Bayesian data (ONLY confidence system now)
            bayesian_confidence=bayesian_result['confidence'] if bayesian_result else None,
            bayesian_reasoning=bayesian_result['reasoning'] if bayesian_result else None
        )
        
        bayesian_conf_str = f"{bayesian_result['confidence']:.1%}" if bayesian_result else "N/A"
        logger.info(f"🎯 NEW prediction ({initial_phase}): {direction} @ ${entry_price:,.2f} ({final_confidence:.1%}) | EV: {ev_result.ev_percent:+.2%} | Bayesian: {bayesian_conf_str}")
        return "CREATED" if initial_phase == PredictionPhase.MONITORING.value else "EXECUTE"
            
    def _update_existing_prediction(self, confidence: float, final_confidence: float, entry_price: float,
                                   stop_loss: float, take_profit: float, risk_reward: float,
                                   base_confidence: float, boosts: List[Tuple[str, float]], current_price: float,
                                   score: float, direction_reasoning_list: List[str], confidence_reasoning_str: str,
                                   ev_result: Any, bayesian_result: Optional[Dict], strategy: str,
                                   old_entry_price: Optional[float] = None) -> str:
        """Update existing prediction (SRP: single responsibility)"""
        old_confidence = self.active_prediction.confidence
            
        # Use the final calibrated confidence as the single confidence value
        single_confidence = final_confidence
        
        # Update core fields
        self.active_prediction.confidence = single_confidence  # Single confidence field
        
        # Entry price: always recalculated to potentially improve confidence
        # old_entry_price parameter is passed from caller
        old_entry_for_comparison = old_entry_price if (old_entry_price is not None) else self.active_prediction.entry_price
        
        if self.active_prediction.phase == PredictionPhase.BUILDING.value:
            # BUILDING phase: verify entry price is in perfect position before execution
            # Use new entry_price if it improves confidence or is closer to current_price
            entry_distance_new = abs(entry_price - current_price)
            entry_distance_old = abs(old_entry_for_comparison - current_price)
            
            if entry_distance_new < entry_distance_old or single_confidence > old_confidence:
                # New entry price is better (closer to current_price or higher confidence)
                self.active_prediction.entry_price = entry_price
                logger.info(f"🏗️ BUILDING: Entry price verified/updated ${old_entry_for_comparison:,.2f} → ${entry_price:,.2f} (perfect position)")
            else:
                # Keep old entry price (it's in better position)
                entry_price = old_entry_for_comparison
                logger.debug(f"🏗️ BUILDING: Keeping entry price ${entry_price:,.2f} (optimal position verified)")
        else:
            # MONITORING or TRACKING: always update entry_price to potentially improve confidence
            if entry_price != old_entry_for_comparison:
                logger.debug(f"📊 Entry price recalculated: ${old_entry_for_comparison:,.2f} → ${entry_price:,.2f} (phase: {self.active_prediction.phase})")
            self.active_prediction.entry_price = entry_price
        
        self.active_prediction.stop_loss = stop_loss
        self.active_prediction.take_profit = take_profit
        self.active_prediction.risk_reward_ratio = risk_reward
        self.active_prediction.base_confidence = base_confidence
        self.active_prediction.confidence_boosts = boosts
        self.active_prediction.confidence_history.append(single_confidence)  # Single confidence
        self.active_prediction.current_price = current_price
        self.active_prediction.score = score
        self.active_prediction.reasoning = self._build_reasoning_list(direction_reasoning_list, confidence_reasoning_str, ev_result, bayesian_result)
        self.active_prediction.last_updated = time.time()
        
        # Update EV data
        self.active_prediction.expected_value = ev_result.ev_percent
        self.active_prediction.expected_value_dollars = ev_result.ev_dollars
        self.active_prediction.win_probability = ev_result.win_probability
        self.active_prediction.ev_reasoning = ev_result.reasoning
        self.active_prediction.should_trade_ev = ev_result.should_trade
        
        # Update Bayesian data (ONLY confidence system now)
        self.active_prediction.bayesian_confidence = bayesian_result['confidence'] if bayesian_result else None
        self.active_prediction.bayesian_reasoning = bayesian_result['reasoning'] if bayesian_result else None
        
        # Note: All old confidence systems removed - only Bayesian fusion remains
        
        # Note: Single confidence field already contains the final calibrated confidence
        
        self.updates_count += 1
        
        # PHASE TRANSITION: MONITORING -> BUILDING when confidence meets threshold
        current_phase = self.active_prediction.phase
        if current_phase == PredictionPhase.MONITORING.value and single_confidence >= self.confidence_threshold:
            # Enter BUILDING phase - entry price is recalculated above, now finalize
            self.active_prediction.phase = PredictionPhase.BUILDING.value
            logger.info(f"🏗️ Entering BUILDING phase: Entry price recalculated to ${entry_price:,.2f} (confidence: {single_confidence:.1%})")
        
        # If in BUILDING phase, ready to execute
        if self.active_prediction.phase == PredictionPhase.BUILDING.value:
            if self._check_execution_readiness(single_confidence):
                return "EXECUTE"
        
        # Log confidence changes
        self._log_confidence_change(old_confidence, single_confidence)  # Use single confidence field
        
        # Check prediction age
        if self._check_prediction_age():
            return "CANCELLED"
        
        return "UPDATED"
            
    def _check_execution_readiness(self, confidence: float) -> bool:
        """Check if prediction is ready for execution (SRP: single responsibility)"""
        if confidence >= self.confidence_threshold:
            self.active_prediction.ready_to_execute = True
            self.active_prediction.execution_reason = f"Confidence {confidence:.1%} >= {self.confidence_threshold:.1%}"
            logger.success(f"✅ EXECUTE: {self.active_prediction.direction} @ ${self.active_prediction.entry_price:,.2f} ({confidence:.1%})")
            return True
        return False
    
    def _log_confidence_change(self, old_confidence: float, new_confidence: float) -> None:
        """Log confidence changes (SRP: single responsibility)"""
        if new_confidence > old_confidence:
            logger.info(f"📈 Confidence: {old_confidence:.1%} → {new_confidence:.1%} (+{new_confidence - old_confidence:.1%})")
        elif new_confidence < old_confidence:
            logger.info(f"📉 Confidence: {old_confidence:.1%} → {new_confidence:.1%} ({new_confidence - old_confidence:.1%})")
    
    def enter_tracking_phase(self, order_id: str) -> bool:
        """
        Enter TRACKING phase after order is placed
        Entry price continues to be recalculated to potentially improve confidence
        """
        if not self.active_prediction:
            logger.warning("⚠️ Cannot enter TRACKING phase: No active prediction")
            return False
        
        if self.active_prediction.phase == PredictionPhase.TRACKING.value:
            logger.debug(f"📊 Already in TRACKING phase for order {order_id}")
            return True
        
        self.active_prediction.phase = PredictionPhase.TRACKING.value
        self.active_prediction.order_id = order_id
        
        logger.info(f"📊 Entered TRACKING phase: Order {order_id} | Entry price will continue to be recalculated to improve confidence")
        return True
    
    def _check_prediction_age(self) -> bool:
        """Check if prediction is too old (SRP: single responsibility)"""
        if self.active_prediction.age_seconds > self.max_prediction_age:
            logger.warning(f"⏰ Prediction expired: {self.active_prediction.age_seconds:.0f}s old")
            self.active_prediction = None
            return True
        return False
    
    # ==========================================
    # MODULE 1: DIRECTION RECOGNITION (DELEGATED)
    # ==========================================
    # Direction recognition is now handled by DirectionRecognizer class
    
    # ==========================================
    # MODULE 3: CONFIDENCE CALCULATION
    # ==========================================
    
    # All confidence calculation is now handled by Bayesian fusion only
    # This eliminates the 8 competing confidence systems that were causing conflicts
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    # Target calculation is now handled by TargetCalculator module
    # See core/ml/target_calculator.py
    
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
            rsi_data = market_data.get("rsi", {})
            rsi = rsi_data.get("rsi", 50) if isinstance(rsi_data, dict) else rsi_data
            if rsi and isinstance(rsi, (int, float)):
                rsi_signal = bayesian.calculate_signal_from_metric("RSI", rsi, "RSI", direction)
                if rsi_signal:
                    signals.append(rsi_signal)
            
            # Volume signal
            volume_data = market_data.get("volume", {})
            volume_category = volume_data.get("category", "MODERATE") if isinstance(volume_data, dict) else str(volume_data)
            if volume_category:
                volume_signal = bayesian.calculate_signal_from_metric("Volume", volume_category, "VOLUME", direction)
                if volume_signal:
                    signals.append(volume_signal)
            
            # Trend signals - use multiple timeframes and pick the highest confidence
            trend_data = market_data.get("trend", {})
            trend_5m = trend_data.get("direction", "SIDEWAYS") if isinstance(trend_data, dict) else str(trend_data)
            
            # Get detailed timeframes from the trend data
            detailed_timeframes = trend_data.get("detailed_timeframes", {})
            trend_15m = detailed_timeframes.get("trend_15m", "UNKNOWN")
            trend_1h = detailed_timeframes.get("trend_1h", "UNKNOWN")
            trend_4h = detailed_timeframes.get("trend_4h", "UNKNOWN")
            trend_24h = detailed_timeframes.get("trend_24h", "UNKNOWN")
            
            # Calculate confidence for each timeframe
            trend_signals = []
            
            # 15m trend (short-term)
            if trend_15m and trend_15m != "UNKNOWN":
                trend_15m_signal = bayesian.calculate_signal_from_metric("Trend_15m", trend_15m, "TREND", direction)
                if trend_15m_signal:
                    trend_signals.append(trend_15m_signal)
            
            # 1h trend (medium-term)
            if trend_1h and trend_1h != "UNKNOWN":
                trend_1h_signal = bayesian.calculate_signal_from_metric("Trend_1h", trend_1h, "TREND", direction)
                if trend_1h_signal:
                    trend_signals.append(trend_1h_signal)
            
            # 4h trend (medium-long-term)
            if trend_4h and trend_4h != "UNKNOWN":
                trend_4h_signal = bayesian.calculate_signal_from_metric("Trend_4h", trend_4h, "TREND", direction)
                if trend_4h_signal:
                    trend_signals.append(trend_4h_signal)
            
            # 24h trend (long-term)
            if trend_24h and trend_24h != "UNKNOWN":
                trend_24h_signal = bayesian.calculate_signal_from_metric("Trend_24h", trend_24h, "TREND", direction)
                if trend_24h_signal:
                    trend_signals.append(trend_24h_signal)
            
            # Add all trend signals to Bayesian fusion (don't pick just one)
            # This allows Bayesian fusion to properly weigh multiple timeframe trends
            for trend_signal in trend_signals:
                signals.append(trend_signal)
            
            # 4. VOLATILITY SIGNAL
            volatility_data = market_data.get("volatility", {})
            volatility_category = volatility_data.get("level", "MODERATE") if isinstance(volatility_data, dict) else str(volatility_data)
            if volatility_category:
                volatility_signal = bayesian.calculate_signal_from_metric("Volatility", volatility_category, "VOLATILITY", direction)
                if volatility_signal:
                    signals.append(volatility_signal)
            
            # 5. SUPPORT/RESISTANCE SIGNAL
            support_resistance = market_data.get("support_resistance", {})
            if support_resistance:
                # Add current price to S/R data for signal conversion
                current_price = market_data.get("current_price", 0)
                if current_price > 0:
                    support_resistance["current_price"] = current_price
                    sr_signal = bayesian.calculate_signal_from_metric("Support_Resistance", support_resistance, "SUPPORT_RESISTANCE", direction)
                    if sr_signal:
                        signals.append(sr_signal)
            
            # 6. PRESSURE SIGNAL
            pressure_data = market_data.get("pressure_data", {})
            if pressure_data:
                pressure_signal = bayesian.calculate_signal_from_metric("Pressure", pressure_data, "PRESSURE", direction)
                if pressure_signal:
                    signals.append(pressure_signal)
            
            # 7. PATTERN SIGNAL
            pattern_analysis = market_data.get("pattern_analysis", {})
            if pattern_analysis:
                pattern_signal = bayesian.calculate_signal_from_metric("Pattern", pattern_analysis, "PATTERN", direction)
                if pattern_signal:
                    signals.append(pattern_signal)
            
            # 8. VOLUME PROFILE SIGNAL
            volume_profile_analysis = market_data.get("volume_profile_analysis", {})
            if volume_profile_analysis:
                volume_profile_signal = bayesian.calculate_signal_from_metric("Volume_Profile", volume_profile_analysis, "VOLUME_PROFILE", direction)
                if volume_profile_signal:
                    signals.append(volume_profile_signal)
            
            # 9. FUNDING RATE SIGNAL
            funding_analysis = market_data.get("funding_analysis", {})
            if funding_analysis and "error" not in funding_analysis:
                funding_signal = bayesian.calculate_signal_from_metric("Funding_Rate", funding_analysis, "FUNDING_RATE", direction)
                if funding_signal:
                    signals.append(funding_signal)
            
            # 10. CROSS-ASSET CORRELATION SIGNAL
            cross_asset_analysis = market_data.get("cross_asset_analysis", {})
            if cross_asset_analysis and "error" not in cross_asset_analysis:
                cross_asset_signal = bayesian.calculate_signal_from_metric("Cross_Asset", cross_asset_analysis, "CROSS_ASSET", direction)
                if cross_asset_signal:
                    signals.append(cross_asset_signal)
            
            # 11. MARKET CONDITIONS SIGNAL
            market_conditions_analysis = market_data.get("market_conditions_analysis", {})
            if market_conditions_analysis:
                market_conditions_signal = bayesian.calculate_signal_from_metric("Market_Conditions", market_conditions_analysis, "MARKET_CONDITIONS", direction)
                if market_conditions_signal:
                    signals.append(market_conditions_signal)
            
            if not signals:
                logger.warning(f"⚠️ No Bayesian signals created for {direction} - using base rate")
                # Return base rate when no signals are available
                return {
                    'confidence': 0.5,  # Base rate
                    'reasoning': f"No signals available for {direction} - using base rate (50%)"
                }
            
            # Fuse signals
            fused = bayesian.fuse_signals(signals, direction)
            logger.debug(f"🔍 Bayesian Fusion: {len(signals)} signals → {fused.posterior_probability:.1%}")
            
            return {
                'confidence': fused.posterior_probability,
                'reasoning': fused.reasoning
            }
        except Exception as e:
            logger.error(f"❌ Bayesian fusion failed: {e}")
            raise RuntimeError(f"Bayesian fusion failed: {e}")
    
    
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
