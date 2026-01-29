#!/usr/bin/env python3
"""
Prediction Engine
Generates trading predictions based on unified market data and current strategy
"""

import math
from dataclasses import dataclass
# CRITICAL: time module removed - all timestamps must come from unified_data for determinism
from typing import Dict, Any, Optional, Literal
from loguru import logger
from config.config import TradingConfig
from core.constants import technical_constants
from .position_sizer import PositionSizeCalculator
from core.decision.base_engine import BaseDecisionEngine
from core.decision.models import (
    DecisionContext,
    DirectionResult,
    EntryResult,
    RiskResult,
    default_feature_vector,
    fill_ivs_feature_vector,
    rsi_trend_to_numeric,
)


@dataclass
class TradingPrediction:
    """Trading prediction/signal structure"""
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: Optional[float]  # 0.0 - 100.0 (percentage) - None if not implemented
    reasoning: str
    strategy: str
    timestamp: float
    risk_reward_ratio: float = 0.0  # Actual R:R achieved (for position sizing)
    position_size_btc: Optional[float] = None  # Position size in BTC (calculated if balance provided)
    position_size_usd: Optional[float] = None  # Position value in USD (calculated if balance provided)
    executable: bool = False  # Whether prediction can be executed (requires confidence)
    execution_gate_reason: str = "confidence_not_implemented"  # Reason why execution is blocked


class PredictionEngine(BaseDecisionEngine):
    """
    Strategy-aware prediction engine (limit setups at S/R + psych + ATR).
    Subclasses BaseDecisionEngine; always produces DecisionResult.
    """

    # Float precision epsilon for comparisons (prevents non-determinism)
    FLOAT_EPSILON = 1e-6  # For general float comparisons
    SCORE_EPSILON = 0.01  # For score comparisons (scores are typically 0-100 range)
    WEIGHT_EPSILON = 0.001  # For weight comparisons (weights are typically 0-1 range)

    def engine_type(self) -> str:
        return "prediction"

    def entry_type(self) -> str:
        return "limit"

    def __init__(self):
        # Initialize calibration hooks (optional - won't break if unavailable)
        self._calibration_hooks = None
        try:
            from core.ml.calibration_hooks import CalibrationHooks
            self._calibration_hooks = CalibrationHooks()
            logger.info("🤖 Prediction Engine initialized with calibration hooks")
        except Exception as e:
            logger.debug(f"Calibration hooks not available: {e} - continuing without calibration")
        logger.info("🤖 Prediction Engine initialized")

    def build_context(
        self,
        unified_data: Dict[str, Any],
        strategy_used_by_engine: str,
    ) -> DecisionContext:
        self._require_key(unified_data, "current_price", "build_context")
        self._require_key(unified_data, "timestamp", "build_context")
        return super().build_context(unified_data, strategy_used_by_engine)

    def compute_direction(self, context: DecisionContext) -> DirectionResult:
        dr = self._score_direction(context.unified_data, context.strategy_used_by_engine)
        return DirectionResult(
            direction=dr["direction"],
            long_score=float(dr["long_score"]),
            short_score=float(dr["short_score"]),
            score_diff=float(dr["score_diff"]),
            reasoning=dr["reasoning"],
            factor_scores=dr.get("factor_scores") or {},
            breakdown_direction=dr.get("breakdown_direction"),
        )

    def compute_entry(
        self,
        context: DecisionContext,
        direction: DirectionResult,
    ) -> EntryResult:
        cfg = TradingConfig.STRATEGY_CONFIGS[context.strategy_used_by_engine]
        setups = self._generate_setups_for_direction(
            context.unified_data,
            direction.direction,
            context.strategy_used_by_engine,
            cfg,
        )
        if not setups:
            raise ValueError(
                f"No entry setups for {direction.direction} ({context.strategy_used_by_engine}) - "
                "must always generate at least one (NO FALLBACKS)"
            )
        best = max(setups, key=lambda x: x["entry_score"])
        breakdown = best.get("entry_breakdown") or {}
        breakdown = {**breakdown, "level_data": best["level_data"], "setup_type": best["setup_type"]}
        reasoning = best.get("entry_reasoning") or ""
        return EntryResult(
            entry_price=best["entry_price"],
            setup_type="sr_setup",
            direction=direction.direction,
            breakdown=breakdown,
            entry_score=best["entry_score"],
            reasoning=reasoning,
        )

    def compute_sl_tp(
        self,
        context: DecisionContext,
        entry: EntryResult,
    ) -> RiskResult:
        cfg = TradingConfig.STRATEGY_CONFIGS[context.strategy_used_by_engine]
        level_data = entry.breakdown.get("level_data")
        setup_type = entry.breakdown.get("setup_type")
        sl, tp, rr, sl_pct, tp_pct = self._calculate_stop_and_target(
            entry_price=entry.entry_price,
            direction=entry.direction,
            config=cfg,
            unified_data=context.unified_data,
            strategy=context.strategy_used_by_engine,
            level_data=level_data,
            setup_type=setup_type,
        )
        return RiskResult(stop_loss=sl, take_profit=tp, rr_ratio=rr, breakdown={"stop_loss_pct": sl_pct, "take_profit_pct": tp_pct})

    def build_feature_vector(
        self,
        context: DecisionContext,
        direction: DirectionResult,
        entry: EntryResult,
        risk: RiskResult,
    ) -> Dict[str, Any]:
        fv = default_feature_vector()
        fv["timestamp"] = context.timestamp
        fv["long_score"] = direction.long_score
        fv["short_score"] = direction.short_score
        fv["score_diff"] = direction.score_diff
        fv["engine_prediction"] = 1.0
        fv["engine_reaction"] = 0.0
        fv["entry_limit"] = 1.0
        fv["entry_market"] = 0.0
        fv["setup_type_categorical"] = 4  # sr_setup
        ud = context.unified_data
        rsi_d = ud.get("rsi") or {}
        rsi = rsi_d.get("rsi")
        fv["rsi"] = float(rsi) if rsi is not None else 0.0
        fv["rsi_trend"] = rsi_trend_to_numeric(rsi_d.get("rsi_trend") or rsi_d.get("trend"))
        tr = ud.get("trend") or {}
        fv["trend_strength"] = float(tr.get("strength") or tr.get("strength_score") or 0.0)
        fv["trend_alignment"] = 1.0 if (tr.get("direction") or "").upper() in ("BULLISH", "BEARISH") else 0.0
        vol = ud.get("volatility") or {}
        fv["volatility_atr_pct"] = float(vol.get("volatility_percentage") or vol.get("volatility_5m") or 0.0) / 100.0 if vol else 0.0
        vol_cat = (ud.get("volume") or {}).get("category") or ud.get("volume_category") or ""
        fv["volume_anomaly"] = 1.0 if vol_cat in ("HIGH", "VERY_HIGH") else 0.0
        pr = ud.get("pressure") or {}
        fv["pressure_strength"] = float(pr.get("strength") or 0.0)
        ob = ud.get("orderbook_analysis") or ud.get("orderbook") or {}
        spread = ob.get("spread_pct") or ob.get("spread") or 0.0
        fv["spread_pct"] = float(spread) if spread is not None else 0.0
        bd = entry.breakdown
        fv["sr_strength"] = float(bd.get("level_strength_raw") or bd.get("level_strength") or 0.0)
        fv["sr_distance_atr"] = float(bd.get("distance_to_current_atr") or 0.0)
        fv["psych_distance_pct"] = float(bd.get("entry_distance_to_nearest_psych_level_pct") or 0.0)
        fv["level_source_sr"] = 1.0 if (bd.get("level_source") or "sr") == "sr" else 0.0
        fv["level_source_psych"] = 1.0 if (bd.get("level_source") or "") == "psych" else 0.0
        fill_ivs_feature_vector(fv, ud, strict_ivs=getattr(TradingConfig, "STRICT_IVS_PRESENCE", False))
        return fv
    
    @classmethod
    def _float_eq(cls, a: float, b: float, epsilon: float = None) -> bool:
        """
        Float equality comparison with epsilon tolerance
        
        Args:
            a: First float value
            b: Second float value
            epsilon: Tolerance (defaults to FLOAT_EPSILON)
        
        Returns:
            True if |a - b| < epsilon
        """
        if epsilon is None:
            epsilon = cls.FLOAT_EPSILON
        return abs(a - b) < epsilon
    
    @classmethod
    def _float_zero(cls, a: float, epsilon: float = None) -> bool:
        """
        Check if float is effectively zero
        
        Args:
            a: Float value to check
            epsilon: Tolerance (defaults to FLOAT_EPSILON)
        
        Returns:
            True if |a| < epsilon
        """
        if epsilon is None:
            epsilon = cls.FLOAT_EPSILON
        return abs(a) < epsilon
    
    @staticmethod
    def _require_key(data: Dict[str, Any], key: str, context: str = "") -> Any:
        """
        Require key to be present in data (NO FALLBACKS policy)
        
        Raises KeyError with descriptive message if key is missing
        """
        if key not in data:
            error_msg = f"Required key '{key}' missing from data"
            if context:
                error_msg += f" ({context})"
            raise KeyError(error_msg)
        return data[key]
    
    def _get_atr_pct(self, unified_data: Dict[str, Any], current_price: float) -> float:
        """
        Get ATR as percentage of price for mathematically justified thresholds (NO FALLBACKS)
        
        Returns ATR percentage (e.g., 0.004 = 0.4%)
        Raises ValueError if ATR is unavailable
        """
        if not unified_data:
            raise ValueError("unified_data is required for ATR calculation - NO FALLBACKS")
        if current_price <= 0:
            raise ValueError(f"Invalid current_price: {current_price} - must be positive")
        
        sr_data = unified_data["support_resistance"]  # Required (NO FALLBACKS)
        if not sr_data:
            raise ValueError("support_resistance data is required for ATR calculation - NO FALLBACKS")
        
        sr_metadata = sr_data["metadata"]  # Required (NO FALLBACKS)
        if not sr_metadata:
            raise ValueError("support_resistance.metadata is required for ATR calculation - NO FALLBACKS")
        
        atr_5m = sr_metadata["atr_5m"]  # Required (NO FALLBACKS)
        if atr_5m <= 0:
            raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
        
        atr_pct = atr_5m / current_price
        if atr_pct <= 0:
            raise ValueError(f"Invalid ATR percentage: {atr_pct} - must be positive (NO FALLBACKS)")
        
        # CRITICAL FIX: Validate ATR reasonableness to prevent corrupted calculations
        # ATR should be between 0.01% and 10% of price for BTC (reasonable range)
        # Extremely small ATR (< 0.01%) suggests data corruption or very low volatility
        # Extremely large ATR (> 10%) suggests data corruption or extreme volatility
        MIN_ATR_PCT = 0.0001  # 0.01% minimum
        MAX_ATR_PCT = 0.10    # 10% maximum
        if atr_pct < MIN_ATR_PCT:
            raise ValueError(f"ATR percentage {atr_pct:.6f} ({atr_pct*100:.4f}%) is too small (< {MIN_ATR_PCT*100:.2f}%). "
                           f"This suggests data corruption or invalid ATR calculation.")
        if atr_pct > MAX_ATR_PCT:
            raise ValueError(f"ATR percentage {atr_pct:.6f} ({atr_pct*100:.2f}%) is too large (> {MAX_ATR_PCT*100:.0f}%). "
                           f"This suggests data corruption or extreme market conditions.")
        
        return atr_pct
    
    def generate_prediction(self, unified_data: Dict[str, Any], strategy: str):
        """
        Generate best limit setup (DecisionResult). Always returns; never None.
        Uses run() -> compute_direction -> compute_entry -> compute_sl_tp -> build_result.
        """
        from core.decision.models import DecisionResult

        try:
            if strategy not in TradingConfig.STRATEGY_CONFIGS:
                raise ValueError(f"Unknown strategy: {strategy} - must be in TradingConfig.STRATEGY_CONFIGS (NO FALLBACKS)")
            result = self.run(unified_data, strategy)
            if not isinstance(result, DecisionResult):
                raise ValueError("run() must return DecisionResult (NO FALLBACKS)")
            # Log per unified contract: state_strategy | prediction_strategy | strategy_used_by_engine
            fv = result.feature_vector or {}
            logger.info(
                f"state_strategy={result.state_strategy} prediction_strategy={result.prediction_strategy} "
                f"strategy_used_by_engine={result.strategy_used_by_engine} | "
                f"engine_type={result.engine_type} setup_type={result.setup_type} direction={result.direction} "
                f"entry_type={result.entry_type} entry_price={result.entry_price} rr_ratio={result.rr_ratio} "
                f"executable={result.executable} confidence={result.confidence} | "
                f"ivs_is_squeeze={fv.get('ivs_is_squeeze', 0)} ivs_released={fv.get('ivs_released', 0)} "
                f"timing_score={result.timing_score}"
            )
            return result
        except Exception as e:
            logger.error(f"❌ Prediction generation failed: {e}")
            raise
    
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
            "standard": self._predict,
            "scalping": self._predict_scalping,
            "swing_trading": self._predict_swing_trading,
            "trend_following": self._predict_trend_following,
            "breakout": self._predict_breakout,
            "range_trading": self._predict_range_trading,
            "low_volatility_range": self._predict_low_volatility_range,
            "high_volatility": self._predict_high_volatility,
            "spike_hunting": self._predict_spike_hunting,
        }
        
        method = strategy_methods[strategy] if strategy in strategy_methods else self._predict
        return method(unified_data, strategy_config)
    
    def _predict(self, unified_data: Dict[str, Any], config: Dict[str, Any], strategy: str = "standard") -> Optional[TradingPrediction]:
        """
        Sequential prediction logic (shared base for all strategies)
        
        SEQUENTIAL DECISION FLOW (Option A - Confidence influences position size):
        1. GET ALL DATA (already done via unified_data)
        2. DETERMINE DIRECTION (market condition decision) - PERFECT calculation
        3. DETERMINE ENTRY PRICE (tactical decision for selected direction)
        4. DETERMINE STOP/TARGET (risk management)
        
        This ensures direction is determined PERFECTLY first, then we find the best entry for that direction.
        
        All strategies use this sequential flow with strategy-specific parameters (direction_weights, 
        timeframe_weights, proximity_config, etc.) from TradingConfig.STRATEGY_CONFIGS[strategy].
        """
        # ==================================================================================
        # STEP 1: GET ALL DATA (already done via unified_data)
        # ==================================================================================
        # All market data is already available in unified_data
        
        # ==================================================================================
        # STEP 2: DETERMINE DIRECTION PERFECTLY (market condition decision)
        # ==================================================================================
        # CRITICAL: Direction scoring MUST always return a result (NO FALLBACKS)
        # If it returns None, that's a system error that should propagate
        direction_result = self._score_direction(unified_data, strategy)
        if not direction_result:
            # This should never happen if _score_direction is working correctly
            # If it does, it's a critical error that should stop the bot
            raise ValueError(f"Direction scoring returned None for {strategy} strategy - this indicates a system error (NO FALLBACKS)")
        
        direction = direction_result["direction"]  # Required (NO FALLBACKS)
        direction_reasoning = direction_result["reasoning"]  # Required (NO FALLBACKS)
        long_score = direction_result["long_score"]  # Required (NO FALLBACKS)
        short_score = direction_result["short_score"]  # Required (NO FALLBACKS)
        score_diff = abs(long_score - short_score)
        
        # CRITICAL CHANGE: Always generate predictions, even if weak
        # Confidence will be calculated later to rate weak predictions as low confidence
        # This ensures we always have the "best setup at current moment" even if it's bad
        # NO FALLBACKS - min_score_diff must be in config
        min_score_diff = self._require_key(config, "min_score_diff", "strategy config")
        if score_diff < min_score_diff:
            logger.info(f"⚠️ Direction signal weak for {strategy}: {direction} (LONG: {long_score:.1f}, SHORT: {short_score:.1f}, diff: {score_diff:.1f} < {min_score_diff:.1f}) - generating anyway with low confidence")
        else:
            logger.info(f"📊 Direction determined: {direction} (LONG: {long_score:.1f}, SHORT: {short_score:.1f}, diff: {score_diff:.1f})")
        logger.debug(f"📊 Direction reasoning: {direction_reasoning}")
        
        # ==================================================================================
        # STEP 3: DETERMINE ENTRY PRICE (tactical decision for selected direction)
        # ==================================================================================
        # Generate setups ONLY for the selected direction
        setups = self._generate_setups_for_direction(
            unified_data=unified_data,
            direction=direction,
            strategy=strategy,
            config=config
        )
        
        # CRITICAL: Entry setup generation MUST always return at least one setup (NO FALLBACKS)
        # If no setups found, _generate_setups_for_direction should be fixed to always generate one
        if not setups:
            # This should never happen - _generate_setups_for_direction should always return at least current price entry
            # If it does, it's a critical error that should stop the bot
            raise ValueError(f"No entry setups found for {direction} direction ({strategy} strategy) - _generate_setups_for_direction must always return at least one setup (NO FALLBACKS)")
        
        # Select best entry setup (highest entry score)
        best_setup = max(setups, key=lambda x: x["entry_score"])  # Required (NO FALLBACKS)
        
        entry_price = best_setup["entry_price"]  # Required (NO FALLBACKS)
        entry_score = best_setup["entry_score"]  # Required (NO FALLBACKS)
        entry_reasoning = best_setup["entry_reasoning"]  # Required (NO FALLBACKS)
        best_setup_level_data = best_setup["level_data"]  # Required (NO FALLBACKS)
        best_setup_type = best_setup["setup_type"]  # Required (NO FALLBACKS)
        
        logger.info(f"📊 Best entry: {direction} @ ${entry_price:.2f} (entry score: {entry_score:.1f})")
        logger.debug(f"📊 Entry reasoning: {entry_reasoning}")
        
        # ==================================================================================
        # STEP 4: DETERMINE STOP/TARGET (risk management)
        # ==================================================================================
        stop_loss, take_profit, rr_ratio, stop_loss_pct, take_profit_pct = self._calculate_stop_and_target(
            entry_price=entry_price,
            direction=direction,
            config=config,
            unified_data=unified_data,
            strategy=strategy,
            level_data=best_setup_level_data,
            setup_type=best_setup_type
        )
        
        # Combine reasoning
        combined_reasoning = f"Direction: {direction_reasoning}. Entry: {entry_reasoning}"
        
        # Pass full setup data to confidence calculation (includes all breakdowns and metrics)
        confidence = self._calculate_prediction_confidence(
            setup_data=best_setup,  # Full setup data with all breakdowns
            stop_loss=stop_loss,
            take_profit=take_profit,
            rr_ratio=rr_ratio,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            unified_data=unified_data,
            strategy=strategy
        )
        
        prediction = self._create_prediction(
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reasoning=combined_reasoning,
            strategy=strategy,
            risk_reward_ratio=rr_ratio
        )
        
        # Log prediction for calibration (if hooks available)
        if self._calibration_hooks:
            try:
                direction_scores = {
                    "long_score": long_score,
                    "short_score": short_score,
                    "score_diff": abs(long_score - short_score)
                }
                self._calibration_hooks.log_prediction(
                    prediction, unified_data, direction_scores, entry_score
                )
            except Exception as e:
                logger.debug(f"Failed to log prediction for calibration: {e}")
                # Don't break prediction generation if calibration logging fails
        
        return prediction
    
    def _create_prediction(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        reasoning: str,
        strategy: str,
        risk_reward_ratio: float = 0.0
    ) -> TradingPrediction:
        """Create a TradingPrediction object - single responsibility: prediction creation"""
        # CRITICAL FIX: Use unified_data timestamp instead of time.time() for determinism
        # timestamp will be set in generate_prediction() from unified_data["timestamp"]
        return TradingPrediction(
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reasoning=reasoning,
            strategy=strategy,
            timestamp=0.0,  # Will be set from unified_data["timestamp"] in generate_prediction()
            risk_reward_ratio=risk_reward_ratio,
            executable=False,  # Set explicitly
            execution_gate_reason="confidence_not_implemented"
        )
    
    # REMOVED: calculate_position_size static method (dead code, never called)
    # Position sizing is now done directly via PositionSizeCalculator.calculate_position_size
    # with liquidation risk protection
    
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
        # CRITICAL CHANGE: Always generate predictions, even if scalping requirements aren't met
        # Validation will log warnings but won't block prediction generation
        # Confidence will be calculated later to rate suboptimal conditions as low confidence
        validation_passed = self._validate_scalping_requirements(unified_data, config)
        if not validation_passed:
            logger.warning(f"⚠️ Scalping requirements not met - generating prediction anyway with low confidence")
        
        # Use base prediction logic with scalping strategy
        # Note: Scalping still uses limit orders at S/R levels, not market orders
        return self._predict(unified_data, config, "scalping")
    
    def _validate_scalping_requirements(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Validate scalping-specific requirements (spread, liquidity, RSI range)"""
        orderbook_data = self._require_key(unified_data, "orderbook_analysis", "scalping validation")
        bid_ask_spread = self._require_key(orderbook_data, "bid_ask_spread", "orderbook_analysis structure")
        spread_pct = self._require_key(bid_ask_spread, "percentage", "bid_ask_spread structure")
        
        # Check spread requirement - spread_pct is in percentage units (e.g., 0.01 = 0.01%), threshold is in decimal (0.0001 = 0.01%)
        # Convert stored percentage to decimal: 0.01% -> 0.0001
        spread_decimal = spread_pct / 100.0
        spread_threshold = config["spread_threshold"]  # Required for scalping strategy (NO FALLBACKS)
        if spread_decimal > spread_threshold:
            logger.debug(f"⏸️ Spread too wide for scalping: {spread_pct:.4f}% > {spread_threshold*100:.4f}%")
            return False
        
        # Check liquidity requirement
        require_high_liquidity = config["require_high_liquidity"]  # Required (NO FALLBACKS)
        if require_high_liquidity:
            liquidity_depth = self._require_key(orderbook_data, "liquidity_depth", "orderbook_analysis structure")
            liquidity_score = self._require_key(liquidity_depth, "depth_score", "liquidity_depth structure")
            min_liquidity = TradingConfig.MIN_LIQUIDITY_SCORE
            if liquidity_score < min_liquidity:
                logger.debug(f"⏸️ Insufficient liquidity for scalping: {liquidity_score:.2f} (min: {min_liquidity})")
                return False
        
        # Check RSI range requirement
        rsi_data = self._require_key(unified_data, "rsi", "scalping validation")
        rsi_value = self._require_key(rsi_data, "rsi", "scalping validation")
        rsi_range = config["rsi_range"]  # Required for scalping strategy (NO FALLBACKS)
        if rsi_value < rsi_range[0] or rsi_value > rsi_range[1]:
            logger.debug(f"⏸️ RSI outside scalping range: {rsi_value:.1f} not in [{rsi_range[0]}, {rsi_range[1]}]")
            return False
        
        return True
    
    def _predict_swing_trading(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Swing trading strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "swing_trading")
    
    def _predict_trend_following(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Trend following strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "trend_following")
    
    def _predict_breakout(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Breakout strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "breakout")
    
    def _predict_range_trading(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Range trading strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "range_trading")
    
    def _predict_low_volatility_range(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Low volatility range strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "low_volatility_range")
    
    def _predict_high_volatility(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """High volatility strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "high_volatility")
    
    def _predict_spike_hunting(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Spike hunting strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "spike_hunting")
    
    # ==================================================================================
    # UNIFIED SCORING FRAMEWORK - Factor Scorers (Reusable)
    # ==================================================================================
    
    def _score_rsi_factor(self, rsi_data: Dict[str, Any]) -> tuple[float, float, list]:
        """
        Score RSI factor for direction determination
        
        Returns:
            (rsi_long_score, rsi_short_score, reasons)
        """
        rsi_value = self._require_key(rsi_data, "rsi", "RSI factor scoring")
        rsi_trend = self._require_key(rsi_data, "rsi_trend", "RSI factor scoring")
        rsi_signal = self._require_key(rsi_data, "rsi_signal", "RSI factor scoring")
        
        rsi_long = 0.0
        rsi_short = 0.0
        reasons = []
        
        if rsi_value < technical_constants.RSI_OVERSOLD:  # Oversold - bullish
            rsi_long = 100.0
            reasons.append(f"RSI oversold ({rsi_value:.1f})")
        elif rsi_value > technical_constants.RSI_OVERBOUGHT:  # Overbought - bearish
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
        
        return rsi_long, rsi_short, reasons
    
    def _score_trend_factor(self, trend_data: Dict[str, Any], strategy: str) -> tuple[float, float, list]:
        """
        Score trend factor for direction determination using multi-timeframe analysis
        
        Uses numeric strength and proper trend direction mapping (no string parsing).
        
        Returns:
            (trend_long_score, trend_short_score, reasons)
        """
        detailed_trends = self._require_key(trend_data, "detailed_timeframes", "trend factor scoring")
        trend_strength = float(self._require_key(trend_data, "strength", "trend data structure"))  # Required (NO FALLBACKS)
        timeframe_weights = self._get_strategy_timeframe_weights(strategy)
        
        trend_long = 0.0
        trend_short = 0.0
        reasons = []
        
        # Trend direction mapping (no string parsing - use proper data structure)
        BULLISH_TRENDS = {"STRONG_UPTREND", "UPTREND", "WEAK_UPTREND"}
        BEARISH_TRENDS = {"STRONG_DOWNTREND", "DOWNTREND", "WEAK_DOWNTREND"}
        
        bullish_tfs = 0
        bearish_tfs = 0
        
        # Trend score mapping (no string parsing - direct lookup)
        TREND_SCORE_MAP = {
            "STRONG_UPTREND": 150.0,
            "UPTREND": 100.0,
            "WEAK_UPTREND": 60.0,
            "STRONG_DOWNTREND": 150.0,
            "DOWNTREND": 100.0,
            "WEAK_DOWNTREND": 60.0
        }
        
        # Analyze each timeframe with strategy-specific weights
        for tf_name, tf_trend in detailed_trends.items():
            if tf_trend == "UNKNOWN" or tf_trend == "SIDEWAYS":
                continue
            
            # NO FALLBACKS - if timeframe exists in detailed_trends, it must have a weight
            if tf_name not in timeframe_weights:
                logger.warning(f"⚠️ Timeframe {tf_name} in detailed_trends but not in timeframe_weights - skipping")
                continue
            tf_weight = timeframe_weights[tf_name]
            # CRITICAL FIX: Use epsilon comparison for float zero check (prevents non-determinism)
            if self._float_zero(tf_weight, self.WEIGHT_EPSILON):
                continue
            
            # NO FALLBACKS - trend must be in TREND_SCORE_MAP
            if tf_trend not in TREND_SCORE_MAP:
                raise ValueError(f"Unknown trend direction '{tf_trend}' for timeframe {tf_name} - not in TREND_SCORE_MAP (NO FALLBACKS)")
            tf_score = TREND_SCORE_MAP[tf_trend]
            
            # Apply numeric strength multiplier (0.0-1.0) for more precision
            tf_score *= (0.7 + 0.3 * trend_strength)  # Scale between 70%-100% of base score
            
            # Determine trend direction and accumulate scores
            if tf_trend in BULLISH_TRENDS:
                trend_long += tf_score * tf_weight
                bullish_tfs += 1
            elif tf_trend in BEARISH_TRENDS:
                trend_short += tf_score * tf_weight
                bearish_tfs += 1
        
        # Multi-timeframe convergence bonus (more sophisticated)
        total_tfs = bullish_tfs + bearish_tfs
        if total_tfs >= 3:
            convergence_ratio = max(bullish_tfs, bearish_tfs) / total_tfs
            # CRITICAL FIX: Use epsilon comparison for float equality (prevents non-determinism)
            if self._float_eq(convergence_ratio, 1.0, self.FLOAT_EPSILON):  # Perfect convergence
                bonus = 50.0
                if bullish_tfs == total_tfs:
                    trend_long += bonus
                    reasons.append(f"Perfect convergence: all {total_tfs} timeframes bullish")
                else:
                    trend_short += bonus
                    reasons.append(f"Perfect convergence: all {total_tfs} timeframes bearish")
            elif convergence_ratio >= 0.75:  # Strong alignment (3/4 or more)
                bonus = 30.0
                if bullish_tfs > bearish_tfs:
                    trend_long += bonus
                    reasons.append(f"Strong alignment: {bullish_tfs}/{total_tfs} timeframes bullish")
                else:
                    trend_short += bonus
                    reasons.append(f"Strong alignment: {bearish_tfs}/{total_tfs} timeframes bearish")
        
        return trend_long, trend_short, reasons
    
    # REMOVED: _score_sr_factor() - S/R no longer used for direction scoring
    # S/R levels determine WHERE to enter/exit, NOT direction
    # Direction determined by: trend, RSI, pressure, volume, patterns only
    
    def _score_pressure_factor(self, pressure_data: Dict[str, Any]) -> tuple[float, float, list]:
        """
        Score market pressure factor for direction determination
        
        Returns:
            (pressure_long_score, pressure_short_score, reasons)
        """
        pressure_direction = self._require_key(pressure_data, "direction", "pressure factor scoring")
        pressure_strength = self._require_key(pressure_data, "strength", "pressure factor scoring")
        
        pressure_long = 0.0
        pressure_short = 0.0
        reasons = []
        
        if pressure_direction in ["BUY", "STRONG_BUY"]:
            strength_multiplier = 1.5 if "STRONG" in pressure_direction else 1.0
            pressure_long = 100.0 * strength_multiplier * pressure_strength
            reasons.append(f"Buy pressure: {pressure_direction} (strength: {pressure_strength:.2f})")
        elif pressure_direction in ["SELL", "STRONG_SELL"]:
            strength_multiplier = 1.5 if "STRONG" in pressure_direction else 1.0
            pressure_short = 100.0 * strength_multiplier * pressure_strength
            reasons.append(f"Sell pressure: {pressure_direction} (strength: {pressure_strength:.2f})")
        
        return pressure_long, pressure_short, reasons
    
    def _score_patterns_factor(self, patterns_data: Dict[str, Any]) -> tuple[float, float, list]:
        """
        Score patterns factor for direction determination using research-based reliability weights
        
        Research-based pattern reliability (from 200,000+ patterns over 10 years):
        - Head & Shoulders: ~83% reliability (highest)
        - Triple Tops/Bottoms: 77-79%
        - Double Tops/Bottoms: 75-79%
        - Triangles/Channels: ~73%
        - Flags: ~67%
        - Hammers: Low reliability (only reliable using low price, not closing)
        
        Scoring formula:
        - Base score = pattern_quality × pattern_type_reliability × 100
        - Pattern importance bonus (clarity + recency) adds up to 30 points
        - Multiple patterns sum together (not binary)
        
        Note: pattern_quality (from pattern["quality"]) is pattern detection quality (0-1),
        NOT prediction confidence. 'confidence' is reserved for predictions/reactions only.
        
        Returns:
            (patterns_long_score, patterns_short_score, reasons)
        """
        patterns_nested = self._require_key(patterns_data, "patterns_nested", "patterns factor scoring")
        
        # Pattern type reliability weights (based on research: 0.67-0.83 range)
        PATTERN_RELIABILITY = {
            # Reversal patterns (highest reliability)
            "HEAD_SHOULDERS": 0.83,
            "INVERSE_HEAD_SHOULDERS": 0.83,
            "TRIPLE_TOP": 0.79,
            "TRIPLE_BOTTOM": 0.79,
            "DOUBLE_TOP": 0.77,
            "DOUBLE_BOTTOM": 0.77,
            "RECTANGLE": 0.78,
            "TREND_CHANGE": 0.70,
            
            # Continuation patterns
            "ASCENDING_TRIANGLE": 0.73,
            "DESCENDING_TRIANGLE": 0.73,
            "SYMMETRICAL_TRIANGLE": 0.73,
            "ASCENDING_CHANNEL": 0.73,
            "DESCENDING_CHANNEL": 0.73,
            "BULL_FLAG": 0.67,
            "BEAR_FLAG": 0.67,
            "BULLISH_CONTINUATION": 0.70,
            "BEARISH_CONTINUATION": 0.70,
            
            # Candlestick patterns (lower reliability)
            "ENGULFING_BULLISH": 0.65,
            "ENGULFING_BEARISH": 0.65,
            "HAMMER": 0.50,  # Low reliability - only reliable using low price
            "SHOOTING_STAR": 0.55,
            "DOJI": 0.45,
            "MORNING_STAR": 0.60,
            "EVENING_STAR": 0.60,
            "THREE_SOLDIERS": 0.58,
            "THREE_CROWS": 0.58,
            "HARAMI_BULLISH": 0.52,
            "HARAMI_BEARISH": 0.52,
        }
        
        # Default reliability for unknown patterns
        DEFAULT_RELIABILITY = 0.60
        
        patterns_long = 0.0
        patterns_short = 0.0
        reasons = []
        
        # Score all pattern categories
        all_pattern_categories = [
            ("reversal_patterns", patterns_nested["reversal_patterns"]),
            ("continuation_patterns", patterns_nested["continuation_patterns"]),
            ("triangle_patterns", patterns_nested["triangle_patterns"]),
            ("channel_patterns", patterns_nested["channel_patterns"]),
            ("wedge_patterns", patterns_nested["wedge_patterns"]),
            ("candlestick_patterns", patterns_nested["candlestick_patterns"]),
        ]
        
        for category_name, patterns in all_pattern_categories:
            if not patterns:
                continue
            
            for pattern in patterns:
                if not isinstance(pattern, dict):
                    continue
                
                pattern_name = pattern["pattern"].upper()
                direction = pattern["direction"]
                pattern_quality = pattern["quality"]  # Pattern detection quality (0-1), NOT prediction confidence
                
                # Get pattern type reliability - NO FALLBACKS
                if pattern_name not in PATTERN_RELIABILITY:
                    raise ValueError(f"Pattern '{pattern_name}' not found in PATTERN_RELIABILITY map - NO FALLBACKS")
                pattern_reliability = PATTERN_RELIABILITY[pattern_name]
                
                # Calculate base score: pattern_quality × reliability × 100
                base_score = pattern_quality * pattern_reliability * 100.0
                
                # Calculate pattern importance bonus (clarity + recency, up to 30 points)
                # Use pattern importance calculation if available
                pattern_high = pattern["pattern_high"]
                pattern_low = pattern["pattern_low"]
                age_minutes = pattern["age_minutes"]
                
                # Clarity bonus (0-20 pts): wider price range = clearer pattern
                if pattern_high > 0 and pattern_low > 0:
                    avg_price = (pattern_high + pattern_low) / 2.0
                    range_pct = (pattern_high - pattern_low) / avg_price if avg_price > 0 else 0.0
                    clarity_bonus = min(20.0, max(0.0, (range_pct - 0.005) / 0.015 * 20.0))
                else:
                    clarity_bonus = 0.0
                
                # Recency bonus (0-10 pts): fresher patterns preferred
                recency_bonus = max(0.0, 10.0 - (age_minutes / 3.0))  # 10 pts at 0min, 0 pts at 30min
                
                importance_bonus = clarity_bonus + recency_bonus
                
                # Total pattern score
                pattern_score = base_score + importance_bonus
                
                # Add to direction scores
                if direction == "BULLISH":
                    patterns_long += pattern_score
                    reasons.append(f"{pattern_name} (quality={pattern_quality:.2f}, rel={pattern_reliability:.2f}, score={pattern_score:.1f})")
                elif direction == "BEARISH":
                    patterns_short += pattern_score
                    reasons.append(f"{pattern_name} (quality={pattern_quality:.2f}, rel={pattern_reliability:.2f}, score={pattern_score:.1f})")
        
        # IMPROVED (2026-01-27): Normalize pattern scores to consistent range [0, 100]
        # Increased normalization factor from 2.0 to 3.0 to handle multiple high-quality patterns
        # This allows up to 300 points (3 strong patterns) before normalization, mapping to [0, 100]
        from config.config import TradingConfig
        normalization_factor = TradingConfig.PATTERN_NORMALIZATION_FACTOR
        patterns_long = patterns_long / normalization_factor
        patterns_short = patterns_short / normalization_factor
        # Clamp to [0, 100] range for safety
        patterns_long = max(0.0, min(100.0, patterns_long))
        patterns_short = max(0.0, min(100.0, patterns_short))
        
        return patterns_long, patterns_short, reasons
    
    def _score_volume_factor(self, volume_data: Dict[str, Any], volume_category: str) -> tuple[float, float, list]:
        """
        Score volume factor for direction determination with improved analysis
        
        CRITICAL FIX: Volume scoring is now INDEPENDENT - it scores based on volume direction/trend,
        NOT on pre-volume scores. This removes circular dependency where volume "confirms" a direction
        that volume itself may have influenced.
        
        Volume scoring logic:
        - High volume with bullish trend → LONG score
        - High volume with bearish trend → SHORT score
        - Low volume → penalty to both (reduces confidence)
        - Volume anomaly → penalty (potential reversal)
        
        Args:
            volume_data: Volume analysis data
            volume_category: Volume category (LOW, HIGH, etc.)
        
        Returns:
            (volume_long_score, volume_short_score, reasons)
        """
        volume_long = 0.0
        volume_short = 0.0
        reasons = []
        
        # Volume schema aligned with StrategyManager: volume_trend_strength, trend, volume_anomaly.
        # Use safe .get() so we stay active whenever volume_category exists (canonical);
        # missing nested keys => neutral scoring, never "missing_data" or skip.
        _raw_strength = volume_data.get("volume_trend_strength")
        volume_trend_strength = float(_raw_strength) if _raw_strength is not None else 0.0
        _raw_anomaly = volume_data.get("volume_anomaly")
        volume_anomaly = _raw_anomaly if isinstance(_raw_anomaly, dict) else {"is_anomaly": False, "severity": "NORMAL"}
        
        _raw_trend = volume_data.get("trend")
        volume_trend = _raw_trend if isinstance(_raw_trend, str) else "NEUTRAL"
        # Map trend to direction format
        if volume_trend in ["BULLISH", "UP", "INCREASING", "RISING"]:
            volume_trend_direction = "BULLISH"
        elif volume_trend in ["BEARISH", "DOWN", "DECREASING", "FALLING"]:
            volume_trend_direction = "BEARISH"
        else:
            volume_trend_direction = "NEUTRAL"  # UNKNOWN, SIDEWAYS, etc.
        
        # Get configurable thresholds (NO FALLBACKS - must be in config)
        from config.config import TradingConfig
        volume_thresholds = TradingConfig.VOLUME_TREND_STRENGTH_THRESHOLDS
        very_strong_threshold = volume_thresholds["very_strong"]  # Required (NO FALLBACKS)
        
        # CRITICAL FIX: Score volume INDEPENDENTLY based on volume direction/trend, not pre-scores
        # High volume with bullish trend → LONG score
        # High volume with bearish trend → SHORT score
        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            base_confirmation_score = 100.0
            
            # Determine volume direction from volume_trend_direction or volume trend strength
            # If volume trend is bullish (increasing volume on up moves), score LONG
            # If volume trend is bearish (increasing volume on down moves), score SHORT
            if volume_trend_direction in ["BULLISH", "UP", "INCREASING"]:
                # High volume with bullish trend → LONG
                if volume_trend_strength > very_strong_threshold:
                    bonus_multiplier = TradingConfig.VOLUME_CONFIRMATION_BONUS_MULTIPLIER
                    volume_long = base_confirmation_score * bonus_multiplier
                    reasons.append(f"High volume with strong bullish trend ({volume_category}, strength: {volume_trend_strength:.2f})")
                else:
                    volume_long = base_confirmation_score
                    reasons.append(f"High volume confirms bullish ({volume_category})")
            elif volume_trend_direction in ["BEARISH", "DOWN", "DECREASING"]:
                # High volume with bearish trend → SHORT
                if volume_trend_strength > very_strong_threshold:
                    bonus_multiplier = TradingConfig.VOLUME_CONFIRMATION_BONUS_MULTIPLIER
                    volume_short = base_confirmation_score * bonus_multiplier
                    reasons.append(f"High volume with strong bearish trend ({volume_category}, strength: {volume_trend_strength:.2f})")
                else:
                    volume_short = base_confirmation_score
                    reasons.append(f"High volume confirms bearish ({volume_category})")
            else:
                # NEUTRAL volume trend - high volume is neutral (no directional bias)
                # Still give moderate score to both (volume confirms activity, not direction)
                volume_long = base_confirmation_score * 0.5
                volume_short = base_confirmation_score * 0.5
                reasons.append(f"High volume but neutral trend ({volume_category})")
        elif volume_category in ["LOW", "VERY_LOW"]:
            # Low volume reduces confidence for BOTH directions (not direction-specific)
            # This is a penalty, not a directional signal
            low_volume_penalty = TradingConfig.LOW_VOLUME_PENALTY
            volume_long = -low_volume_penalty
            volume_short = -low_volume_penalty
            reasons.append(f"Low volume reduces confidence ({volume_category})")
        
        # Volume anomaly detection: extreme volume spikes can indicate reversals
        # Apply penalty to BOTH directions (reduces confidence, doesn't favor one direction)
        is_anomaly = bool(volume_anomaly.get("is_anomaly") if isinstance(volume_anomaly, dict) else False)
        if is_anomaly and volume_category in ["VERY_HIGH", "EXTREME"]:
            anomaly_penalty = TradingConfig.VOLUME_ANOMALY_PENALTY
            volume_long -= anomaly_penalty
            volume_short -= anomaly_penalty
            reasons.append("Volume anomaly detected - potential reversal risk")
        
        return volume_long, volume_short, reasons
    
    # REMOVED: _score_funding_factor() - Funding no longer used for direction scoring
    # Funding rate often unavailable and has minimal impact on short-term direction
    
    def _score_market_conditions_factor(self, market_conditions_data: Dict[str, Any]) -> tuple[float, float, list]:
        """
        Score market conditions factor (Fear & Greed Index) for direction determination
        
        Contrarian signals at extremes:
        - Extreme fear (0-20) → bullish reversal signal
        - Extreme greed (80-100) → bearish reversal signal
        - Balanced sentiment (30-70) → neutral
        
        Returns:
            (market_conditions_long_score, market_conditions_short_score, reasons)
        """
        try:
            # NO FALLBACKS - if market_conditions_data is provided, it must have valid sentiment_data
            sentiment_data = self._require_key(market_conditions_data, "sentiment_data", "market_conditions_data structure")
            if not sentiment_data:
                raise ValueError("sentiment_data is empty in market_conditions_data (NO FALLBACKS)")
            
            # Get fear/greed value - must have either index_value or value
            if "index_value" in sentiment_data:
                fear_greed_value = self._require_key(sentiment_data, "index_value", "sentiment_data structure")
            elif "value" in sentiment_data:
                fear_greed_value = self._require_key(sentiment_data, "value", "sentiment_data structure")
            else:
                raise ValueError("sentiment_data must have either 'index_value' or 'value' key (NO FALLBACKS)")
            
            market_conditions_long = 0.0
            market_conditions_short = 0.0
            reasons = []
            
            # Contrarian scoring at extremes
            if fear_greed_value <= 20:  # Extreme fear - bullish reversal
                market_conditions_long = 80.0
                reasons.append(f"Extreme fear ({fear_greed_value}) - contrarian buy signal")
            elif fear_greed_value <= 30:  # High fear - moderate bullish
                market_conditions_long = 50.0
                reasons.append(f"High fear ({fear_greed_value}) - moderate buy signal")
            elif fear_greed_value >= 80:  # Extreme greed - bearish reversal
                market_conditions_short = 80.0
                reasons.append(f"Extreme greed ({fear_greed_value}) - contrarian sell signal")
            elif fear_greed_value >= 70:  # High greed - moderate bearish
                market_conditions_short = 50.0
                reasons.append(f"High greed ({fear_greed_value}) - moderate sell signal")
            # Balanced sentiment (30-70) = neutral (0.0, 0.0)
            
            return market_conditions_long, market_conditions_short, reasons
            
        except Exception as e:
            logger.error(f"❌ Market conditions factor scoring failed: {e}")
            # NO FALLBACKS - if market conditions scoring fails, it's a system error
            raise
    
    def _score_cross_asset_factor(self, cross_asset_data: Dict[str, Any]) -> tuple[float, float, list]:
        """
        Score cross-asset correlation factor for direction determination
        
        Only uses correlations when they are strong (>0.5):
        - DXY rising (dollar strength) → bearish for BTC (negative correlation)
        - DXY falling (dollar weakness) → bullish for BTC
        - Stocks rising → bullish for BTC (if positive correlation)
        - Stocks falling → bearish for BTC (if positive correlation)
        
        Returns:
            (cross_asset_long_score, cross_asset_short_score, reasons)
        """
        try:
            cross_asset_long = 0.0
            cross_asset_short = 0.0
            reasons = []
            
            # DXY correlation (typically negative - dollar strength = BTC weakness)
            if "dxy_correlation" in cross_asset_data:
                dxy_corr = cross_asset_data["dxy_correlation"]
                # NO FALLBACKS - if dxy_correlation exists, it must have these fields
                dxy_correlation_value = self._require_key(dxy_corr, "correlation", "dxy_correlation structure")
                dxy_change = self._require_key(dxy_corr, "dxy_change_pct", "dxy_correlation structure")
                
                # Only use if correlation is strong (>0.5 absolute)
                if abs(dxy_correlation_value) > 0.5:
                    if dxy_correlation_value < 0:  # Negative correlation (typical)
                        # DXY rising (dollar strength) → bearish for BTC
                        if dxy_change > 0.3:  # Significant DXY rise
                            cross_asset_short += 60.0
                            reasons.append(f"DXY strength ({dxy_change:.2f}%) - bearish for BTC (corr: {dxy_correlation_value:.2f})")
                        elif dxy_change < -0.3:  # Significant DXY fall
                            cross_asset_long += 60.0
                            reasons.append(f"DXY weakness ({dxy_change:.2f}%) - bullish for BTC (corr: {dxy_correlation_value:.2f})")
                    else:  # Positive correlation (rare)
                        # DXY rising → bullish for BTC
                        if dxy_change > 0.3:
                            cross_asset_long += 60.0
                            reasons.append(f"DXY strength ({dxy_change:.2f}%) - bullish for BTC (corr: {dxy_correlation_value:.2f})")
                        elif dxy_change < -0.3:
                            cross_asset_short += 60.0
                            reasons.append(f"DXY weakness ({dxy_change:.2f}%) - bearish for BTC (corr: {dxy_correlation_value:.2f})")
            
            # Stock correlation (typically positive - stocks up = BTC up)
            if "stock_correlation" in cross_asset_data:
                stock_corr = cross_asset_data["stock_correlation"]
                # NO FALLBACKS - if stock_correlation exists, it must have correlation field
                stock_correlation_value = self._require_key(stock_corr, "correlation", "stock_correlation structure")
                
                # Get stock change from composite_change or change_percent
                stock_change = 0.0
                if "composite_change" in stock_corr:
                    stock_change = stock_corr["composite_change"]
                elif "change_percent" in stock_corr:
                    stock_change = stock_corr["change_percent"]
                
                # Only use if correlation is strong (>0.5 absolute)
                if abs(stock_correlation_value) > 0.5:
                    if stock_correlation_value > 0:  # Positive correlation (typical)
                        # Stocks rising → bullish for BTC
                        if stock_change > 1.0:  # Significant stock rally
                            cross_asset_long += 50.0
                            reasons.append(f"Stock rally ({stock_change:.2f}%) - bullish for BTC (corr: {stock_correlation_value:.2f})")
                        elif stock_change < -1.0:  # Significant stock selloff
                            cross_asset_short += 50.0
                            reasons.append(f"Stock selloff ({stock_change:.2f}%) - bearish for BTC (corr: {stock_correlation_value:.2f})")
                    else:  # Negative correlation (rare)
                        # Stocks rising → bearish for BTC
                        if stock_change > 1.0:
                            cross_asset_short += 50.0
                            reasons.append(f"Stock rally ({stock_change:.2f}%) - bearish for BTC (corr: {stock_correlation_value:.2f})")
                        elif stock_change < -1.0:
                            cross_asset_long += 50.0
                            reasons.append(f"Stock selloff ({stock_change:.2f}%) - bullish for BTC (corr: {stock_correlation_value:.2f})")
            
            return cross_asset_long, cross_asset_short, reasons
            
        except Exception as e:
            logger.error(f"❌ Cross-asset factor scoring failed: {e}")
            # NO FALLBACKS - if cross-asset scoring fails, it's a system error
            raise
    # Can be added back if needed for long-term position bias
    
    # ==================================================================================
    # UNIFIED SCORING FRAMEWORK - Entry Factor Scorers (Reusable)
    # ==================================================================================
    
    def _score_entry_orderbook_factor(
        self,
        direction: str,
        setup_type: str,
        orderbook_data: Dict[str, Any],
        entry_price: float,
        current_price: float
    ) -> tuple[float, list]:
        """
        Score orderbook imbalance factor for entry setup
        
        Real-time orderbook shows actual liquidity/pressure at price levels:
        - LONG at support: Prefer entries when orderbook shows buying pressure (bids > asks)
        - SHORT at resistance: Prefer entries when orderbook shows selling pressure (asks > bids)
        
        Returns:
            (orderbook_score, reasons)
        """
        try:
            score = 0.0
            reasons = []
            
            # Get orderbook imbalance data
            # NO FALLBACKS - orderbook data must have these fields
            order_imbalance = self._require_key(orderbook_data, "order_imbalance", "orderbook_analysis structure")
            market_pressure = self._require_key(orderbook_data, "market_pressure", "orderbook_analysis structure")
            
            imbalance_category = self._require_key(order_imbalance, "category", "order_imbalance structure")
            imbalance_bias = self._require_key(order_imbalance, "bias", "order_imbalance structure")  # -1 (selling) to +1 (buying)
            pressure_direction = self._require_key(market_pressure, "direction", "market_pressure structure")
            pressure_strength = self._require_key(market_pressure, "strength", "market_pressure structure")
            
            # Score based on direction and setup type alignment
            if direction == "LONG" and setup_type == "support_level":
                # LONG at support: Prefer when orderbook shows buying pressure
                if imbalance_category in ["HEAVY_BUYING", "BUYING_BIAS"]:
                    if pressure_strength == "STRONG":
                        score = 100.0
                        reasons.append(f"Strong buying pressure at support (imbalance: {imbalance_category}, bias: {imbalance_bias:.2f})")
                    elif pressure_strength == "MODERATE":
                        score = 80.0
                        reasons.append(f"Moderate buying pressure at support (imbalance: {imbalance_category})")
                    else:
                        score = 60.0
                        reasons.append(f"Buying bias at support (imbalance: {imbalance_category})")
                elif imbalance_category == "BALANCED":
                    score = 50.0  # Neutral
                    reasons.append("Balanced orderbook at support")
                else:  # SELLING_BIAS or HEAVY_SELLING
                    score = 30.0  # Penalty - selling pressure at support is concerning
                    reasons.append(f"Selling pressure at support (imbalance: {imbalance_category}) - caution")
            
            elif direction == "SHORT" and setup_type == "resistance_level":
                # SHORT at resistance: Prefer when orderbook shows selling pressure
                if imbalance_category in ["HEAVY_SELLING", "SELLING_BIAS"]:
                    if pressure_strength == "STRONG":
                        score = 100.0
                        reasons.append(f"Strong selling pressure at resistance (imbalance: {imbalance_category}, bias: {imbalance_bias:.2f})")
                    elif pressure_strength == "MODERATE":
                        score = 80.0
                        reasons.append(f"Moderate selling pressure at resistance (imbalance: {imbalance_category})")
                    else:
                        score = 60.0
                        reasons.append(f"Selling bias at resistance (imbalance: {imbalance_category})")
                elif imbalance_category == "BALANCED":
                    score = 50.0  # Neutral
                    reasons.append("Balanced orderbook at resistance")
                else:  # BUYING_BIAS or HEAVY_BUYING
                    score = 30.0  # Penalty - buying pressure at resistance is concerning
                    reasons.append(f"Buying pressure at resistance (imbalance: {imbalance_category}) - caution")
            
            else:
                # Unknown setup type - use neutral score
                score = 50.0
                reasons.append("Orderbook alignment (neutral)")
            
            return score, reasons
            
        except Exception as e:
            logger.error(f"❌ Orderbook factor scoring failed: {e}")
            # NO FALLBACKS - if orderbook scoring fails, it's a system error
            raise
    
    def _score_entry_market_conditions_factor(
        self,
        direction: str,
        setup_type: str,
        market_conditions_data: Dict[str, Any],
        level_data: Dict[str, Any]
    ) -> tuple[float, list]:
        """
        Score market conditions factor for entry setup
        
        In extreme sentiment, prefer entries at stronger levels:
        - Extreme fear/greed → prefer higher power levels (more conservative)
        - Balanced sentiment → standard scoring
        
        Returns:
            (market_conditions_score, reasons)
        """
        try:
            score = 0.0
            reasons = []
            
            # NO FALLBACKS - if market_conditions_data is provided, it must have valid sentiment_data
            sentiment_data = self._require_key(market_conditions_data, "sentiment_data", "market_conditions_data structure")
            if not sentiment_data:
                raise ValueError("sentiment_data is empty in market_conditions_data (NO FALLBACKS)")
            
            # Get fear/greed value - must have either index_value or value
            if "index_value" in sentiment_data:
                fear_greed_value = self._require_key(sentiment_data, "index_value", "sentiment_data structure")
            elif "value" in sentiment_data:
                fear_greed_value = self._require_key(sentiment_data, "value", "sentiment_data structure")
            else:
                raise ValueError("sentiment_data must have either 'index_value' or 'value' key (NO FALLBACKS)")
            
            # Get level power for comparison
            # NO FALLBACKS - level_data must have power
            level_power = self._require_key(level_data, "power", "level_data structure")
            
            # In extreme sentiment, prefer stronger levels
            if fear_greed_value <= 20 or fear_greed_value >= 80:  # Extreme fear or greed
                if level_power >= 70:  # Strong level
                    score = 100.0
                    reasons.append(f"Strong level ({level_power:.1f}) in extreme sentiment ({fear_greed_value}) - conservative entry")
                elif level_power >= 50:  # Moderate level
                    score = 70.0
                    reasons.append(f"Moderate level ({level_power:.1f}) in extreme sentiment ({fear_greed_value})")
                else:  # Weak level
                    score = 40.0  # Penalty - weak levels risky in extreme sentiment
                    reasons.append(f"Weak level ({level_power:.1f}) in extreme sentiment ({fear_greed_value}) - higher risk")
            
            elif fear_greed_value <= 30 or fear_greed_value >= 70:  # High fear or greed
                if level_power >= 60:  # Strong level
                    score = 85.0
                    reasons.append(f"Strong level ({level_power:.1f}) in high sentiment ({fear_greed_value})")
                elif level_power >= 40:  # Moderate level
                    score = 60.0
                    reasons.append(f"Moderate level ({level_power:.1f}) in high sentiment ({fear_greed_value})")
                else:  # Weak level
                    score = 45.0  # Small penalty
                    reasons.append(f"Weak level ({level_power:.1f}) in high sentiment ({fear_greed_value})")
            
            else:  # Balanced sentiment (30-70)
                # Standard scoring - no bonus/penalty
                score = 50.0
                reasons.append(f"Balanced sentiment ({fear_greed_value}) - standard entry")
            
            return score, reasons
            
        except Exception as e:
            logger.error(f"❌ Market conditions entry factor scoring failed: {e}")
            # NO FALLBACKS - if market conditions entry scoring fails, it's a system error
            raise
    
    # NOTE: IV Squeeze scoring method removed
    # IV Squeeze is for timing/decisions (WHEN to enter), not entry price accuracy (WHERE to enter)
    # Will be used in confidence calculation when implemented
    # Method kept commented for future use:
    #
    # def _score_entry_iv_squeeze_factor(self, iv_squeeze_data: Dict[str, Any]) -> tuple[float, list]:
    #     """Score IV Squeeze for confidence calculation (future implementation)"""
    #     pass
    
    def _score_entry_sr_factor(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        level_data: Dict[str, Any],
        unified_data: Optional[Dict[str, Any]] = None,
        strategy: str = "standard"
    ) -> tuple[float, list]:
        """
        Score S/R level factor for entry setup
        
        level_data is ALWAYS provided (all entries are at specific S/R levels for limit orders).
        
        Note: Breakout/breakdown entries are removed - limit orders can't fill above resistance
        (when price is below) or below support (when price is above). Only support/resistance
        level entries are valid for limit orders.
        
        Args:
            entry_price: Entry price for limit order
            current_price: Current market price
            direction: "LONG" or "SHORT"
            level_data: S/R level data dict (must contain "price_level", "power", "setup_type")
            unified_data: Optional unified data for additional context
        
        Returns:
            (sr_score, reasons)
        """
        level_power = level_data["power"]  # Required (NO FALLBACKS)
        level_price = self._require_key(level_data, "price_level", "entry S/R factor scoring")
        setup_type = self._require_key(level_data, "setup_type", "entry S/R factor scoring")
        
        score = 0.0
        reasons = []
        
        # Base score from S/R level power (0-100) - pure strength, no proximity/recency
        score = level_power
        
        # Distance from the referenced level - using unified utility
        from core.utils.distance_utils import calculate_distance_pct
        distance_pct = calculate_distance_pct(entry_price, level_price, current_price)
        
        # Get ATR for mathematically justified thresholds
        atr_pct = self._get_atr_pct(unified_data, current_price)
        
        # Get strategy-specific entry proximity configuration
        strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
        entry_proximity_config = strategy_config["entry_proximity_config"]  # Required in all strategies (NO FALLBACKS)
        optimal_atr = entry_proximity_config["optimal_atr"]  # Required (NO FALLBACKS)
        acceptable_atr = entry_proximity_config["acceptable_atr"]  # Required (NO FALLBACKS)
        too_far_atr = entry_proximity_config["too_far_atr"]  # Required (NO FALLBACKS)
        
        # Strategy-specific thresholds based on ATR:
        optimal_threshold = atr_pct * optimal_atr
        acceptable_threshold = atr_pct * acceptable_atr
        too_far_threshold = atr_pct * too_far_atr
        
        # BTC PERP ENTRY SCORING (Research-backed for 40x leverage)
        # OLD LOGIC (WRONG): Gave 20% bonus for entering exactly AT S/R level (distance=0)
        # WHY WRONG: Ignores BTC perp market microstructure (stop hunts, liquidation wicks)
        # NEW LOGIC: Optimal entry is INSIDE zone (0.3-0.5×ATR toward current), not AT level
        #
        # Scoring philosophy:
        # - Inside optimal zone (0.2-0.5×ATR): Best (1.1x multiplier)
        # - At level or very close (0-0.2×ATR): Good but risky (1.0x, no bonus)
        # - Acceptable range (0.5-1.0×ATR): Acceptable (0.95x)
        # - Too far (>1.0×ATR): Penalty (0.8x)
        
        if setup_type in ["support_level", "resistance_level"]:
            # Calculate distance from S/R level in ATR terms
            distance_atr = distance_pct / atr_pct if atr_pct > 0 else 0
            
            if setup_type == "support_level":
                # LONG at support: entry ABOVE support (inside zone, toward current)
                # Use entry quality multipliers from config (configurable for optimization)
                if 0.2 <= distance_atr <= 0.5:  # Optimal: 0.2-0.5×ATR above support
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["optimal_bonus"])
                    reasons.append(f"Optimal entry above support @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                elif distance_atr < 0.2:  # At or very close to level
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["neutral"])
                    reasons.append(f"Entry near/at support @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                elif distance_atr <= 1.0:  # Acceptable: 0.5-1.0×ATR
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["small_penalty"])
                    reasons.append(f"Entry acceptable above support @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                else:  # Too far: >1.0×ATR
                    score = max(0.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["medium_penalty"])
                    reasons.append(f"Entry too far from support @ {distance_atr:.2f}×ATR")
            else:  # resistance_level
                # SHORT at resistance: entry BELOW resistance (inside zone, toward current)
                # Use entry quality multipliers from config (configurable for optimization)
                if 0.2 <= distance_atr <= 0.5:  # Optimal: 0.2-0.5×ATR below resistance
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["optimal_bonus"])
                    reasons.append(f"Optimal entry below resistance @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                elif distance_atr < 0.2:  # At or very close to level
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["neutral"])
                    reasons.append(f"Entry near/at resistance @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                elif distance_atr <= 1.0:  # Acceptable: 0.5-1.0×ATR
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["small_penalty"])
                    reasons.append(f"Entry acceptable below resistance @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                else:  # Too far: >1.0×ATR
                    score = max(0.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["medium_penalty"])
                    reasons.append(f"Entry too far from resistance @ {distance_atr:.2f}×ATR")
        
        else:
            # Unknown setup type - use default scoring with ATR-based threshold
            near_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["near_threshold"]
            if distance_pct < near_threshold:
                reasons.append(f"S/R level reference (power: {level_power:.1f}, distance: {distance_pct*100:.3f}%)")
            else:
                score = max(0.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["medium_penalty"])
                reasons.append(f"Far from S/R level (distance: {distance_pct*100:.3f}% > {near_threshold*100:.3f}%)")
        
        return score, reasons
    
    def _score_entry_rsi_factor(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        rsi_data: Dict[str, Any],
        atr_5m: Optional[float] = None
    ) -> tuple[float, list]:
        """
        Score RSI alignment factor for entry setup
        
        Args:
            entry_price: Proposed entry price
            current_price: Current market price
            direction: "LONG" or "SHORT"
            rsi_data: RSI data with "rsi" and "rsi_trend"
            atr_5m: 5-minute ATR (optional, for ATR-based thresholds)
        
        Returns:
            (rsi_score, reasons)
        """
        rsi_value = self._require_key(rsi_data, "rsi", "entry RSI factor scoring")
        rsi_trend = self._require_key(rsi_data, "rsi_trend", "entry RSI factor scoring")
        
        score = 0.0
        reasons = []
        
        # Entry price relative to current price
        price_diff_pct = (entry_price - current_price) / current_price if current_price > 0 else 0.0
        
        # ATR-based threshold (NO FALLBACKS)
        # Use 1.25×ATR as significant distance threshold (mathematically justified)
        if atr_5m is None or atr_5m <= 0 or current_price <= 0:
            raise ValueError(f"ATR required for RSI entry scoring: atr_5m={atr_5m}, current_price={current_price} (NO FALLBACKS)")
        
        significant_diff_threshold = (atr_5m / current_price) * 1.25  # 1.25×ATR as percentage
        
        if direction == "LONG":
            # For LONG: entry below current (buying cheaper) is good, especially if RSI is oversold
            if rsi_value < technical_constants.RSI_OVERSOLD and price_diff_pct < 0:  # Oversold + entry below current = very good
                score = 100.0
                reasons.append(f"RSI oversold ({rsi_value:.1f}) + entry below current ({price_diff_pct*100:.2f}%)")
            # CRITICAL FIX: Use epsilon comparison for zero check (prevents non-determinism)
            elif rsi_value < 50 and rsi_trend == "BULLISH" and (self._float_zero(price_diff_pct, self.FLOAT_EPSILON) or price_diff_pct < 0):
                score = 70.0
                reasons.append(f"RSI recovering ({rsi_value:.1f}) + entry at/below current")
            elif price_diff_pct < -significant_diff_threshold:  # Entry significantly below current (1.25×ATR)
                score = 50.0
                reasons.append(f"Entry below current ({price_diff_pct*100:.2f}% < -{significant_diff_threshold*100:.2f}%)")
            elif price_diff_pct < 0:
                score = 30.0
                reasons.append(f"Entry slightly below current ({price_diff_pct*100:.2f}%)")
        else:  # SHORT
            # For SHORT: entry above current (selling higher) is good, especially if RSI is overbought
            if rsi_value > technical_constants.RSI_OVERBOUGHT and price_diff_pct > 0:  # Overbought + entry above current = very good
                score = 100.0
                reasons.append(f"RSI overbought ({rsi_value:.1f}) + entry above current ({price_diff_pct*100:.2f}%)")
            # CRITICAL FIX: Use epsilon comparison for zero check (prevents non-determinism)
            elif rsi_value > 50 and rsi_trend == "BEARISH" and (self._float_zero(price_diff_pct, self.FLOAT_EPSILON) or price_diff_pct > 0):
                score = 70.0
                reasons.append(f"RSI declining ({rsi_value:.1f}) + entry at/above current")
            elif price_diff_pct > significant_diff_threshold:  # Entry significantly above current (1.25×ATR)
                score = 50.0
                reasons.append(f"Entry above current ({price_diff_pct*100:.2f}% > {significant_diff_threshold*100:.2f}%)")
            elif price_diff_pct > 0:
                score = 30.0
                reasons.append(f"Entry slightly above current ({price_diff_pct*100:.2f}%)")
        
        return score, reasons
    
    def _score_entry_trend_factor(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        trend_data: Dict[str, Any],
        strategy: str
    ) -> tuple[float, list]:
        """
        Score trend alignment factor for entry setup
        
        Returns:
            (trend_score, reasons)
        """
        detailed_trends = self._require_key(trend_data, "detailed_timeframes", "trend factor scoring")
        timeframe_weights = self._get_strategy_timeframe_weights(strategy)
        
        score = 0.0
        reasons = []
        
        # Analyze trend alignment with entry direction
        bullish_tfs = 0
        bearish_tfs = 0
        total_weighted_score = 0.0
        total_weight = 0.0
        
        # Trend direction mapping (no string parsing - use proper data structure)
        BULLISH_TRENDS = {"STRONG_UPTREND", "UPTREND", "WEAK_UPTREND"}
        BEARISH_TRENDS = {"STRONG_DOWNTREND", "DOWNTREND", "WEAK_DOWNTREND"}
        
        # Trend score mapping (no string parsing - direct lookup)
        TREND_SCORE_MAP = {
            "STRONG_UPTREND": 1.5,
            "UPTREND": 1.0,
            "WEAK_UPTREND": 1.0,
            "STRONG_DOWNTREND": 1.5,
            "DOWNTREND": 1.0,
            "WEAK_DOWNTREND": 1.0
        }
        
        for tf_name, tf_trend in detailed_trends.items():
            if tf_trend == "UNKNOWN" or tf_trend == "SIDEWAYS":
                continue
            
            # NO FALLBACKS - if timeframe exists in detailed_trends, it must have a weight
            if tf_name not in timeframe_weights:
                logger.warning(f"⚠️ Timeframe {tf_name} in detailed_trends but not in timeframe_weights - skipping")
                continue
            tf_weight = timeframe_weights[tf_name]
            # CRITICAL FIX: Use epsilon comparison for float zero check (prevents non-determinism)
            if self._float_zero(tf_weight, self.WEIGHT_EPSILON):
                continue
            
            # NO FALLBACKS - trend must be in TREND_SCORE_MAP
            if tf_trend not in TREND_SCORE_MAP:
                raise ValueError(f"Unknown trend direction '{tf_trend}' for timeframe {tf_name} - not in TREND_SCORE_MAP (NO FALLBACKS)")
            tf_score = TREND_SCORE_MAP[tf_trend]
            
            # Determine trend direction and accumulate
            if tf_trend in BULLISH_TRENDS:
                bullish_tfs += 1
                total_weighted_score += tf_score * tf_weight
                total_weight += tf_weight
            elif tf_trend in BEARISH_TRENDS:
                bearish_tfs += 1
                total_weighted_score += tf_score * tf_weight
                total_weight += tf_weight
        
        if total_weight > 0:
            avg_score = total_weighted_score / total_weight
            if direction == "LONG" and bullish_tfs > bearish_tfs:
                score = avg_score * 100.0  # Bullish trend aligns with LONG
                reasons.append(f"Trend alignment: {bullish_tfs} bullish vs {bearish_tfs} bearish timeframes")
            elif direction == "SHORT" and bearish_tfs > bullish_tfs:
                score = avg_score * 100.0  # Bearish trend aligns with SHORT
                reasons.append(f"Trend alignment: {bearish_tfs} bearish vs {bullish_tfs} bullish timeframes")
            else:
                score = avg_score * 50.0  # Partial alignment
                reasons.append(f"Partial trend alignment: {bullish_tfs} bullish, {bearish_tfs} bearish")
        
        return score, reasons
    
    def _score_entry_pressure_factor(
        self,
        direction: str,
        pressure_data: Dict[str, Any]
    ) -> tuple[float, list]:
        """
        Score market pressure alignment factor for entry setup
        
        Returns:
            (pressure_score, reasons)
        """
        pressure_direction = self._require_key(pressure_data, "direction", "pressure factor scoring")
        pressure_strength = self._require_key(pressure_data, "strength", "pressure factor scoring")
        
        score = 0.0
        reasons = []
        
        # Pressure direction mapping (no string parsing)
        STRONG_BUY_PRESSURES = {"STRONG_BUY"}
        BUY_PRESSURES = {"BUY", "STRONG_BUY"}
        STRONG_SELL_PRESSURES = {"STRONG_SELL"}
        SELL_PRESSURES = {"SELL", "STRONG_SELL"}
        
        if direction == "LONG" and pressure_direction in BUY_PRESSURES:
            strength_multiplier = 1.5 if pressure_direction in STRONG_BUY_PRESSURES else 1.0
            score = 100.0 * strength_multiplier * pressure_strength
            reasons.append(f"Buy pressure aligns with LONG: {pressure_direction} (strength: {pressure_strength:.2f})")
        elif direction == "SHORT" and pressure_direction in SELL_PRESSURES:
            strength_multiplier = 1.5 if pressure_direction in STRONG_SELL_PRESSURES else 1.0
            score = 100.0 * strength_multiplier * pressure_strength
            reasons.append(f"Sell pressure aligns with SHORT: {pressure_direction} (strength: {pressure_strength:.2f})")
        else:
            score = 30.0  # Neutral pressure
            reasons.append(f"Neutral pressure: {pressure_direction}")
        
        return score, reasons
    
    def _score_entry_patterns_factor(
        self,
        direction: str,
        patterns_data: Dict[str, Any]
    ) -> tuple[float, list]:
        """
        Score pattern alignment factor for entry setup
        
        Returns:
            (patterns_score, reasons)
        """
        patterns_nested = self._require_key(patterns_data, "patterns_nested", "patterns factor scoring")
        reversal_patterns = self._require_key(patterns_nested, "reversal_patterns", "patterns factor scoring")
        continuation_patterns = self._require_key(patterns_nested, "continuation_patterns", "patterns factor scoring")
        
        score = 0.0
        reasons = []
        
        if direction == "LONG":
            bullish_reversals = [p for p in reversal_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BULLISH"]
            bullish_continuations = [p for p in continuation_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BULLISH"]
            
            if bullish_reversals:
                score += 100.0
                reasons.append(f"Bullish reversal pattern aligns with LONG ({len(bullish_reversals)})")
            if bullish_continuations:
                score += 50.0
                reasons.append(f"Bullish continuation pattern ({len(bullish_continuations)})")
        else:  # SHORT
            bearish_reversals = [p for p in reversal_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BEARISH"]
            bearish_continuations = [p for p in continuation_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BEARISH"]
            
            if bearish_reversals:
                score += 100.0
                reasons.append(f"Bearish reversal pattern aligns with SHORT ({len(bearish_reversals)})")
            if bearish_continuations:
                score += 50.0
                reasons.append(f"Bearish continuation pattern ({len(bearish_continuations)})")
        
        return min(100.0, score), reasons
    
    def _score_entry_volume_factor(
        self,
        volume_category: str,
        volume_anomaly: Dict[str, Any] = None
    ) -> tuple[float, list]:
        """
        Score volume confirmation factor for entry setup
        
        Args:
            volume_category: Volume category (HIGH, NORMAL, LOW, etc.)
            volume_anomaly: Volume anomaly detection data for risk management
        
        Returns:
            (volume_score, reasons)
        """
        score = 0.0
        reasons = []
        
        # Volume anomaly risk check: Reduce score if anomaly detected
        if volume_anomaly and volume_anomaly["is_anomaly"]:
            severity = volume_anomaly["severity"]
            if severity == "EXTREME":
                score -= 50.0  # Significant penalty for extreme anomalies
                reasons.append(f"⚠️ EXTREME volume anomaly detected - high risk")
            elif severity == "HIGH":
                score -= 30.0  # Moderate penalty for high anomalies
                reasons.append(f"⚠️ HIGH volume anomaly detected - increased risk")
            elif severity == "MODERATE":
                score -= 15.0  # Small penalty for moderate anomalies
                reasons.append(f"⚠️ MODERATE volume anomaly detected - caution advised")
        
        # Normal volume scoring
        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            score += 100.0
            reasons.append(f"High volume confirms entry ({volume_category})")
        elif volume_category in ["NORMAL"]:
            score += 50.0
            reasons.append("Normal volume")
        else:
            score += 20.0
            reasons.append(f"Low volume ({volume_category})")
        
        return max(0.0, score), reasons
    
    def _score_entry_distance_factor(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        unified_data: Dict[str, Any]
    ) -> tuple[float, list]:
        """
        Score distance from current price factor (risk/reward consideration)
        
        Args:
            entry_price: Proposed entry price
            current_price: Current market price
            direction: "LONG" or "SHORT"
            unified_data: Complete market analysis data (required for ATR)
        
        Returns:
            (distance_score, reasons)
        """
        # NO FALLBACKS - current_price must be valid
        if current_price <= 0:
            raise ValueError(f"Invalid current_price: {current_price} - must be positive (NO FALLBACKS)")
        
        distance_pct = abs(entry_price - current_price) / current_price
        score = 0.0
        reasons = []
        
        # Get ATR for mathematically justified thresholds (NO FALLBACKS)
        sr_data = self._require_key(unified_data, "support_resistance", "distance scoring")
        sr_metadata = sr_data["metadata"]
        atr_5m = sr_metadata["atr_5m"]
        if atr_5m <= 0 or current_price <= 0:
            raise ValueError(f"Invalid ATR or price: atr_5m={atr_5m}, current_price={current_price} (NO FALLBACKS)")
        
        atr_pct = atr_5m / current_price
        
        # Mathematically justified thresholds based on ATR:
        # - Too close: <0.25×ATR (might miss if price moves quickly)
        # - Optimal: 0.25×ATR to 1.25×ATR (good balance, likely to fill)
        # - Moderate: 1.25×ATR to 2.5×ATR (reasonable, might take longer)
        # - Far: 2.5×ATR to 5×ATR (lower fill probability)
        # - Very far: >5×ATR (very low fill probability)
        # Use ATR multipliers from config (configurable for optimization)
        too_close_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["too_close"]
        optimal_max_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["optimal"]
        moderate_max_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["moderate"]
        far_max_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["far"]
        
        if too_close_threshold <= distance_pct < optimal_max_threshold:  # Optimal range: 0.25×ATR to 1.25×ATR
            score = 100.0
            reasons.append(f"Optimal distance from current ({distance_pct*100:.3f}%, {too_close_threshold*100:.3f}%-{optimal_max_threshold*100:.3f}%) - good fill probability")
        elif distance_pct < too_close_threshold:  # Too close: <0.25×ATR
            score = 60.0  # Might miss if price moves quickly
            reasons.append(f"Very close to current ({distance_pct*100:.3f}% < {too_close_threshold*100:.3f}%) - might miss")
        elif distance_pct < moderate_max_threshold:  # Moderate: 1.25×ATR to 2.5×ATR
            score = 80.0  # Good balance
            reasons.append(f"Moderate distance from current ({distance_pct*100:.3f}%, {optimal_max_threshold*100:.3f}%-{moderate_max_threshold*100:.3f}%)")
        elif distance_pct < far_max_threshold:  # Far: 2.5×ATR to 5×ATR
            score = 50.0  # Lower fill probability
            reasons.append(f"Far from current ({distance_pct*100:.3f}%, {moderate_max_threshold*100:.3f}%-{far_max_threshold*100:.3f}%) - lower fill probability")
        else:  # Very far: >5×ATR
            score = 20.0  # Very low fill probability
            reasons.append(f"Very far from current ({distance_pct*100:.3f}% > {far_max_threshold*100:.3f}%) - low fill probability")
        
        return score, reasons
    
    def _score_entry_type_factor(
        self,
        setup_type: str,
        strategy: str
    ) -> tuple[float, list]:
        """
        Score setup type bonus (strategy-aware)
        
        Returns:
            (type_score, reasons)
        """
        score = 0.0
        reasons = []
        
        # Strategy-specific preferences (all entries are at S/R levels for limit orders)
        # Note: Breakout/breakdown entries removed - they don't work with limit orders only
        if strategy == "breakout":
            # For breakout strategy with limit orders, we enter at resistance (SHORT) or support (LONG)
            # when price is approaching the level, anticipating the breakout
            if setup_type in ["support_level", "resistance_level"]:
                score = 100.0  # Breakout strategy uses S/R level entries (anticipating breakout)
                reasons.append(f"S/R level entry for {strategy} (breakout anticipation)")
            else:
                score = 60.0
        elif strategy in ["range_trading", "low_volatility_range"]:
            if setup_type in ["support_level", "resistance_level"]:
                score = 100.0  # Range trading prefers S/R level entries
                reasons.append("S/R level entry preferred for range trading")
            else:
                score = 50.0
        else:  # Standard and other strategies
            if setup_type in ["support_level", "resistance_level"]:
                score = 80.0  # S/R levels are generally good for limit orders
                reasons.append("S/R level entry")
            else:
                score = 60.0  # Default for any other types
                reasons.append(f"{setup_type} entry")
        
        return score, reasons
    
    # ==================================================================================
    # PARAMETER SCORERS - Use factor scorers to score specific parameters
    # ==================================================================================
    
    def _score_direction(self, unified_data: Dict[str, Any], strategy: str) -> Optional[Dict[str, Any]]:
        """
        Score direction using unified scoring framework (global - no entry context)
        
        Uses factor scorers to calculate long_score and short_score, then determines direction.
        This is the base method used in the sequential flow (Step 2: Determine Direction).
        
        Returns:
            Dict with "direction", "reasoning", "long_score", "short_score"
        """
        try:
            # All required data must be present (NO FALLBACKS)
            current_price = self._require_key(unified_data, "current_price", "direction scoring")
            if current_price <= 0:
                raise ValueError(f"Invalid current_price: {current_price}")
            
            # Get strategy-specific weights (NO FALLBACKS)
            # NOTE: S/R is NOT included in direction scoring - S/R determines entry/exit, NOT direction
            strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
            direction_weights = strategy_config["direction_weights"]  # Required in all strategies (NO FALLBACKS)
            
            # CRITICAL FIX: Validate and normalize weights to prevent ML training/inference mismatch
            # Weights must sum to 1.0 for consistent score magnitudes across strategies
            total_weight = sum(direction_weights.values())
            # CRITICAL FIX: Use epsilon comparison for float equality (prevents non-determinism)
            if not self._float_eq(total_weight, 1.0, self.WEIGHT_EPSILON):
                weight_error = abs(total_weight - 1.0)
                # Warn if weights are significantly off (more than 10% deviation)
                if weight_error > 0.1:
                    logger.warning(f"⚠️ Direction weights for {strategy} sum to {total_weight:.4f} (error: {weight_error:.4f}) - significant deviation (>10%)")
                logger.warning(f"⚠️ Direction weights for {strategy} sum to {total_weight:.4f}, not 1.0. Normalizing...")
                direction_weights = {k: v / total_weight for k, v in direction_weights.items()}
                logger.debug(f"✅ Normalized weights: {direction_weights}")
            
            # Track which weights are actually used (for optional features that may be missing)
            active_weights = {}
            
            # Extract indicators - all required (NO FALLBACKS)
            rsi_data = self._require_key(unified_data, "rsi", "direction scoring")
            trend_data = self._require_key(unified_data, "trend", "direction scoring")
            pressure_data = self._require_key(unified_data, "pressure", "direction scoring")
            patterns_data = self._require_key(unified_data, "patterns", "direction scoring")
            volume_data = self._require_key(unified_data, "volume", "direction scoring")
            volume_category = unified_data["volume_category"]  # Flattened key for compatibility
            
            # Initialize scores
            long_score = 0.0
            short_score = 0.0
            long_reasons = []  # Track reasons that support LONG
            short_reasons = []  # Track reasons that support SHORT
            
            # Track factor scores for interaction analysis
            # NOTE: RSI, trend, and pressure are correlated (all derived from price movements)
            # They're scored independently and added, which can amplify signals when aligned.
            # Synergy bonus (multiplicative) helps address correlation but doesn't fully eliminate it.
            # For ML training: Consider using interaction terms or PCA to decorrelate features.
            factor_scores = {
                "rsi": {"long": 0.0, "short": 0.0},
                "trend": {"long": 0.0, "short": 0.0},
                "pressure": {"long": 0.0, "short": 0.0},
                "patterns": {"long": 0.0, "short": 0.0},
                "market_conditions": {"long": 0.0, "short": 0.0},
                "cross_asset": {"long": 0.0, "short": 0.0}
            }
            
            # Score each factor using unified framework (all weights required - NO FALLBACKS)
            # Track active weights for renormalization if optional features are missing
            rsi_weight = direction_weights["rsi"]  # Required (NO FALLBACKS)
            if rsi_weight > 0:
                rsi_long, rsi_short, reasons = self._score_rsi_factor(rsi_data)
                factor_scores["rsi"] = {"long": rsi_long, "short": rsi_short}
                long_score += rsi_long * rsi_weight
                short_score += rsi_short * rsi_weight
                active_weights["rsi"] = rsi_weight
                # Add reasons to the direction they support (based on score contribution)
                if rsi_long > rsi_short:
                    long_reasons.extend(reasons)
                elif rsi_short > rsi_long:
                    short_reasons.extend(reasons)
                # If equal, add to both (neutral RSI)
            
            trend_weight = direction_weights["trend"]  # Required (NO FALLBACKS)
            if trend_weight > 0:
                trend_long, trend_short, reasons = self._score_trend_factor(trend_data, strategy)
                factor_scores["trend"] = {"long": trend_long, "short": trend_short}
                long_score += trend_long * trend_weight
                short_score += trend_short * trend_weight
                active_weights["trend"] = trend_weight
                # Add reasons to the direction they support
                if trend_long > trend_short:
                    long_reasons.extend(reasons)
                elif trend_short > trend_long:
                    short_reasons.extend(reasons)
            
            pressure_weight = direction_weights["pressure"]  # Required (NO FALLBACKS)
            if pressure_weight > 0:
                pressure_long, pressure_short, reasons = self._score_pressure_factor(pressure_data)
                factor_scores["pressure"] = {"long": pressure_long, "short": pressure_short}
                long_score += pressure_long * pressure_weight
                short_score += pressure_short * pressure_weight
                active_weights["pressure"] = pressure_weight
                # Add reasons to the direction they support
                if pressure_long > pressure_short:
                    long_reasons.extend(reasons)
                elif pressure_short > pressure_long:
                    short_reasons.extend(reasons)
            
            patterns_weight = direction_weights["patterns"]  # Required (NO FALLBACKS)
            if patterns_weight > 0:
                patterns_long, patterns_short, reasons = self._score_patterns_factor(patterns_data)
                factor_scores["patterns"] = {"long": patterns_long, "short": patterns_short}
                long_score += patterns_long * patterns_weight
                short_score += patterns_short * patterns_weight
                active_weights["patterns"] = patterns_weight
                # Add reasons to the direction they support
                if patterns_long > patterns_short:
                    long_reasons.extend(reasons)
                elif patterns_short > patterns_long:
                    short_reasons.extend(reasons)
            
            # Volume scoring: INDEPENDENT scoring based on volume direction/trend only
            # CRITICAL: Run BEFORE renormalization / inactive_factors so volume is active when present.
            volume_weight = direction_weights["volume"]  # Required (NO FALLBACKS)
            if volume_weight > 0:
                volume_long, volume_short, reasons = self._score_volume_factor(
                    volume_data, volume_category
                )
                factor_scores["volume"] = {"long": volume_long, "short": volume_short}
                long_score += volume_long * volume_weight
                short_score += volume_short * volume_weight
                active_weights["volume"] = volume_weight
                if volume_long > volume_short:
                    long_reasons.extend(reasons)
                elif volume_short > volume_long:
                    short_reasons.extend(reasons)
            
            # S/R PROXIMITY REMOVED FROM DIRECTION SCORING
            # CRITICAL FIX: S/R proximity creates circular dependency:
            # - Direction influenced by S/R proximity → Entry selected from S/R levels → Feedback loop
            # - Direction should be momentum-based (RSI, trend, volume, pressure), not location-based
            # - Entry selection already uses S/R levels, so proximity info is redundant in direction
            # - Removing prevents ML spurious correlations and overconfidence near S/R levels
            # S/R proximity is still used in entry scoring (where it belongs)
            
            # FUNDING REMOVED FROM DIRECTION SCORING
            # Funding is often not available and doesn't significantly impact short-term direction
            # If needed in the future, make it optional and handle missing data gracefully
            
            # Market Conditions (Fear & Greed Index) - Contrarian signals at extremes
            if "market_conditions" in direction_weights:
                market_conditions_weight = direction_weights["market_conditions"]
                if market_conditions_weight > 0:
                    market_conditions_data = self._require_key(unified_data, "market_conditions", "unified_data structure")
                    market_conditions_long, market_conditions_short, reasons = self._score_market_conditions_factor(market_conditions_data)
                    factor_scores["market_conditions"] = {"long": market_conditions_long, "short": market_conditions_short}
                    long_score += market_conditions_long * market_conditions_weight
                    short_score += market_conditions_short * market_conditions_weight
                    active_weights["market_conditions"] = market_conditions_weight
                    # Add reasons to the direction they support
                    if market_conditions_long > market_conditions_short:
                        long_reasons.extend(reasons)
                    elif market_conditions_short > market_conditions_long:
                        short_reasons.extend(reasons)
                else:
                    # Data missing - weight will be redistributed
                    logger.debug(f"⚠️ Market conditions data missing, weight {market_conditions_weight:.4f} will be redistributed")
            
            # Cross-Asset Correlation (DXY, Stocks) - Only when correlation is strong
            # NO FALLBACKS - if weight is specified, data must exist
            if "cross_asset" in direction_weights:
                cross_asset_weight = direction_weights["cross_asset"]
                if cross_asset_weight > 0:
                    cross_asset_data = self._require_key(unified_data, "cross_asset_analysis", "unified_data structure")
                    cross_asset_long, cross_asset_short, reasons = self._score_cross_asset_factor(cross_asset_data)
                    factor_scores["cross_asset"] = {"long": cross_asset_long, "short": cross_asset_short}
                    long_score += cross_asset_long * cross_asset_weight
                    short_score += cross_asset_short * cross_asset_weight
                    active_weights["cross_asset"] = cross_asset_weight
                    # Add reasons to the direction they support
                    if cross_asset_long > cross_asset_short:
                        long_reasons.extend(reasons)
                    elif cross_asset_short > cross_asset_long:
                        short_reasons.extend(reasons)
                else:
                    # Data missing - weight will be redistributed
                    logger.debug(f"⚠️ Cross-asset data missing, weight {cross_asset_weight:.4f} will be redistributed")
            
            # Build inactive_factors after all factor scoring (volume, market_conditions, cross_asset)
            inactive_factors = {}
            for factor_name in direction_weights:
                if factor_name not in active_weights:
                    inactive_factors[factor_name] = "optional_missing" if factor_name in ("market_conditions", "cross_asset") else "missing_data"

            # Renormalize if any weight was missing (before synergies)
            total_active_weight = sum(active_weights.values()) if active_weights else 0.0
            total_expected_weight = sum(direction_weights.values())
            if not self._float_eq(total_active_weight, total_expected_weight, self.WEIGHT_EPSILON) and not self._float_zero(total_expected_weight, self.WEIGHT_EPSILON):
                missing_weight = total_expected_weight - total_active_weight
                scale_factor = total_expected_weight / total_active_weight if not self._float_zero(total_active_weight, self.WEIGHT_EPSILON) else 1.0
                if not self._float_eq(scale_factor, 1.0, self.WEIGHT_EPSILON):
                    inactive_str = ", ".join([f"{k}({v})" for k, v in inactive_factors.items()])
                    logger.debug(
                        f"⚠️ Renormalizing scores: missing {missing_weight:.4f} weight "
                        f"({total_active_weight:.4f}/{total_expected_weight:.4f} active), scaling by {scale_factor:.4f}. "
                        f"Inactive factors: {inactive_str}"
                    )
                    long_score *= scale_factor
                    short_score *= scale_factor
            
            # Detect factor synergies (non-linear interactions)
            synergy_multipliers = self._detect_factor_synergies(factor_scores, rsi_data, trend_data)
            long_score *= synergy_multipliers["long"]
            short_score *= synergy_multipliers["short"]
            if synergy_multipliers["reasons"]:
                if synergy_multipliers["long"] > 1.0:
                    long_reasons.extend(synergy_multipliers["reasons"])
                elif synergy_multipliers["short"] > 1.0:
                    short_reasons.extend(synergy_multipliers["reasons"])
                if synergy_multipliers["long"] < 1.0 or synergy_multipliers["short"] < 1.0:
                    long_reasons.extend([r for r in synergy_multipliers["reasons"] if "Conflict" in r])
                    short_reasons.extend([r for r in synergy_multipliers["reasons"] if "Conflict" in r])
            
            # Final validation: Clamp scores to [0, 100] range after all operations
            # IMPROVED (2026-01-27): Ensure scores remain in expected range
            long_score = max(0.0, min(100.0, long_score))
            short_score = max(0.0, min(100.0, short_score))
            
            # Determine direction from scores with intelligent tie-breaking
            # CRITICAL FIX: Use epsilon comparison for score equality (prevents non-determinism)
            score_diff = abs(long_score - short_score)
            
            # Edge case: All factors neutral (both scores = 0.0)
            if self._float_eq(long_score, 0.0, self.SCORE_EPSILON) and self._float_eq(short_score, 0.0, self.SCORE_EPSILON):
                logger.warning(f"⚠️ All direction factors neutral (both scores = 0.0) - using tie-breaking")
            
            logger.debug(f"📊 Direction scores ({strategy}): LONG={long_score:.1f}, SHORT={short_score:.1f}, diff={score_diff:.1f}")
            
            if long_score > short_score and not self._float_eq(long_score, short_score, self.SCORE_EPSILON):
                direction = "LONG"
                # Only show reasons that support LONG direction
                relevant_reasons = long_reasons[:5] if long_reasons else ["No specific LONG factors"]
                reasoning = f"LONG signal (score: {long_score:.1f} vs {short_score:.1f}). " + "; ".join(relevant_reasons)
            elif short_score > long_score and not self._float_eq(long_score, short_score, self.SCORE_EPSILON):
                direction = "SHORT"
                # Only show reasons that support SHORT direction
                relevant_reasons = short_reasons[:5] if short_reasons else ["No specific SHORT factors"]
                reasoning = f"SHORT signal (score: {short_score:.1f} vs {long_score:.1f}). " + "; ".join(relevant_reasons)
            else:
                # Intelligent tie-breaking: use trend strength and RSI as tie-breakers
                # Scores are effectively equal (within epsilon)
                direction = self._break_tie(long_score, short_score, trend_data, rsi_data)
                # Show reasons from the winning direction
                relevant_reasons = (long_reasons if direction == "LONG" else short_reasons)[:5]
                reasoning = f"Neutral signal (equal scores: {long_score:.1f}), tie-broken by {direction}. " + "; ".join(relevant_reasons if relevant_reasons else ["Tie-broken by trend/RSI"])
            
            # Top factors by |long - short| contribution (for breakdown_direction)
            def _contrib(name: str) -> float:
                fs = factor_scores.get(name) or {}
                lv = float(fs.get("long") or 0.0)
                sv = float(fs.get("short") or 0.0)
                return abs(lv - sv)
            top_factors = sorted(
                [k for k in factor_scores if _contrib(k) > 0],
                key=_contrib,
                reverse=True
            )[:5]

            # Direction strength breakdown (always emit; no suppression for weakness)
            breakdown_direction = {
                "diff": score_diff,
                "normalized_diff": score_diff / 100.0 if score_diff else 0.0,
                "top_factors": top_factors,
                "inactive_factors": inactive_factors,
            }

            # Expose ML-ready features for future model training
            direction_result = {
                "direction": direction,
                "reasoning": reasoning,
                "long_score": long_score,
                "short_score": short_score,
                "score_diff": score_diff,  # ML feature: score difference
                "factor_scores": factor_scores,  # ML feature: individual factor contributions
                "synergy_multipliers": synergy_multipliers,  # ML feature: synergy effects
                "breakdown_direction": breakdown_direction,
            }
            
            # Validate ML features (debug mode - logs warnings but doesn't block)
            try:
                from core.utils.ml_feature_validator import MLFeatureValidator
                is_valid, warnings = MLFeatureValidator.validate_direction_features(direction_result)
                MLFeatureValidator.log_validation_results(is_valid, warnings, "direction")
            except ImportError:
                pass  # Validator not available - skip validation
            
            return direction_result
            
        except Exception as e:
            logger.error(f"❌ Direction scoring failed: {e}")
            # NO FALLBACKS - direction scoring must succeed
            raise
    
    def _detect_factor_synergies(self, factor_scores: Dict[str, Dict[str, float]], 
                                 rsi_data: Dict[str, Any], trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect factor synergies using fixed-percentage multipliers
        
        Changed from absolute bonuses to fixed multipliers for consistent scaling:
        - rsi_trend_alignment: 1.15x (15% boost)
        - momentum_building: 1.10x (10% boost)
        - factor_conflict: 0.90x (10% reduction)
        
        Examples:
        - RSI oversold + strong bullish trend = 1.15x multiplier
        - RSI overbought + strong bearish trend = 1.15x multiplier
        - RSI oversold + bearish trend = 0.90x multiplier (conflict)
        
        Returns:
            Dict with "long", "short" multipliers (default 1.0) and "reasons" list
        """
        synergy_multipliers = {"long": 1.0, "short": 1.0, "reasons": []}
        
        rsi_value = float(self._require_key(rsi_data, "rsi", "rsi data structure"))  # Required (NO FALLBACKS)
        rsi_trend = self._require_key(rsi_data, "rsi_trend", "rsi data structure")  # Required (NO FALLBACKS)
        trend_direction = self._require_key(trend_data, "direction", "trend data structure")  # Required (NO FALLBACKS)
        trend_strength = float(self._require_key(trend_data, "strength", "trend data structure"))  # Required (NO FALLBACKS)
        
        # Get configurable synergy multipliers (NO FALLBACKS)
        from config.config import TradingConfig
        synergy_config = TradingConfig.SYNERGY_MULTIPLIERS
        
        # Synergy 1: RSI oversold + bullish trend = strong buy signal
        if rsi_value < technical_constants.RSI_OVERSOLD and trend_direction == "BULLISH":
            multiplier = synergy_config["rsi_trend_alignment"]  # 1.15x
            # Scale multiplier slightly with trend strength (1.0 to 1.15 range)
            strength_adjusted = 1.0 + (multiplier - 1.0) * trend_strength
            synergy_multipliers["long"] *= strength_adjusted
            synergy_multipliers["reasons"].append(f"Synergy: RSI oversold ({rsi_value:.1f}) + bullish trend (strength: {trend_strength:.2f}) → {strength_adjusted:.2f}x")
        
        # Synergy 2: RSI overbought + bearish trend = strong sell signal
        elif rsi_value > technical_constants.RSI_OVERBOUGHT and trend_direction == "BEARISH":
            multiplier = synergy_config["rsi_trend_alignment"]  # 1.15x
            strength_adjusted = 1.0 + (multiplier - 1.0) * trend_strength
            synergy_multipliers["short"] *= strength_adjusted
            synergy_multipliers["reasons"].append(f"Synergy: RSI overbought ({rsi_value:.1f}) + bearish trend (strength: {trend_strength:.2f}) → {strength_adjusted:.2f}x")
        
        # Synergy 3: RSI recovering + bullish trend = momentum building
        if rsi_value < 50 and rsi_trend == "BULLISH" and trend_direction == "BULLISH":
            multiplier = synergy_config["momentum_building"]  # 1.10x
            strength_adjusted = 1.0 + (multiplier - 1.0) * trend_strength
            synergy_multipliers["long"] *= strength_adjusted
            synergy_multipliers["reasons"].append(f"Synergy: RSI recovering + bullish trend alignment → {strength_adjusted:.2f}x")
        
        # Synergy 4: RSI declining + bearish trend = momentum building
        elif rsi_value > 50 and rsi_trend == "BEARISH" and trend_direction == "BEARISH":
            multiplier = synergy_config["momentum_building"]  # 1.10x
            strength_adjusted = 1.0 + (multiplier - 1.0) * trend_strength
            synergy_multipliers["short"] *= strength_adjusted
            synergy_multipliers["reasons"].append(f"Synergy: RSI declining + bearish trend alignment → {strength_adjusted:.2f}x")
        
        # Conflict detection: RSI and trend oppose each other
        conflict_multiplier = synergy_config["factor_conflict"]  # 0.90x
        if (rsi_value < technical_constants.RSI_OVERSOLD and trend_direction == "BEARISH") or \
           (rsi_value > technical_constants.RSI_OVERBOUGHT and trend_direction == "BULLISH"):
            # Apply conflict reduction to both directions (reduces confidence)
            synergy_multipliers["long"] *= conflict_multiplier
            synergy_multipliers["short"] *= conflict_multiplier
            synergy_multipliers["reasons"].append("Conflict: RSI and trend oppose each other → 0.90x")
        
        # CRITICAL FIX: Clamp synergy multipliers to [0.9, 1.2] range to prevent unrealistic amplification
        # Multiple synergies can stack (e.g., RSI oversold + bullish trend + momentum building)
        # Without clamping, could exceed 1.2x (e.g., 1.15 * 1.10 = 1.265x)
        synergy_multipliers["long"] = max(0.9, min(1.2, synergy_multipliers["long"]))
        synergy_multipliers["short"] = max(0.9, min(1.2, synergy_multipliers["short"]))
        
        return synergy_multipliers
    
    def _break_tie(self, long_score: float, short_score: float, 
                   trend_data: Dict[str, Any], rsi_data: Dict[str, Any]) -> str:
        """
        Intelligent tie-breaking when scores are equal
        
        Uses trend strength and RSI as tie-breakers in order of priority.
        
        Returns:
            "LONG" or "SHORT"
        """
        # Priority 1: Use trend strength and direction
        trend_direction = self._require_key(trend_data, "direction", "trend data structure")  # Required (NO FALLBACKS)
        trend_strength = float(self._require_key(trend_data, "strength", "trend data structure"))  # Required (NO FALLBACKS)
        
        # Get tie-breaking threshold from config
        from config.config import TradingConfig
        from core.constants import TechnicalAnalysisConstants
        tie_break_threshold = TradingConfig.DIRECTION_TIE_BREAK_TREND_STRENGTH_THRESHOLD
        rsi_neutral = TechnicalAnalysisConstants.RSI_NEUTRAL
        
        if trend_direction == "BULLISH" and trend_strength > tie_break_threshold:
            return "LONG"
        elif trend_direction == "BEARISH" and trend_strength > tie_break_threshold:
            return "SHORT"
        
        # Priority 2: Use RSI as tie-breaker
        rsi_value = float(self._require_key(rsi_data, "rsi", "rsi data structure"))  # Required (NO FALLBACKS)
        if rsi_value < rsi_neutral:
            return "LONG"  # RSI below neutral favors long
        elif rsi_value > rsi_neutral:
            return "SHORT"  # RSI above neutral favors short
        
        # Priority 3: Default to LONG (conservative approach)
        return "LONG"
    
    
    def _get_strategy_timeframe_weights(self, strategy: str) -> Dict[str, float]:
        """
        Get strategy-specific timeframe weights from config
        
        Different strategies care about different timeframes:
        - Scalping: 15m (high), 1h (medium), 4h (low), 24h (none)
        - Swing Trading: 4h (high), 24h (high), 1h (medium), 15m (low)
        - Trend Following: All timeframes, but 4h/24h weighted higher
        - Range Trading: 1h (high), 4h (medium), 15m (low), 24h (low)
        - Breakout: 1h (high), 4h (high), 15m (medium), 24h (low)
        """
        # Get timeframe weights from config (NO FALLBACKS)
        timeframe_weights_map = TradingConfig.STRATEGY_TIMEFRAME_WEIGHTS
        
        # Return strategy-specific weights - NO FALLBACKS
        if strategy not in timeframe_weights_map:
            raise ValueError(f"Strategy '{strategy}' not found in TIMEFRAME_WEIGHTS - NO FALLBACKS")
        return timeframe_weights_map[strategy]
    
    # ==================================================================================
    # CONFIDENCE CALCULATION - Separate from scoring system
    # ==================================================================================
    
    def _calculate_prediction_confidence(
        self,
        setup_data: Dict[str, Any],
        stop_loss: float,
        take_profit: float,
        rr_ratio: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        unified_data: Dict[str, Any],
        strategy: str
    ) -> float:
        """
        Calculate confidence for final prediction (separate from scoring system)
        
        NOTE: Not implemented yet - will be implemented after all input parameters are integrated.
        Currently returns a placeholder value.
        
        Args:
            setup_data: Complete setup data dict containing:
                - entry_price, entry_score, direction_score, total_score
                - entry_breakdown: {power, proximity_factor, recency_factor, distance_atr, hours_since_touch, setup_type}
                - direction_breakdown: {base_long_score, base_short_score, proximity_factor, strength_factor, 
                                        alignment_factor, recency_factor, score_diff, final_long_score, final_short_score}
                - long_score, short_score, score_diff
                - level_data: {power, last_touch_timestamp, etc.}
                - setup_type, direction
            stop_loss: Calculated stop loss price
            take_profit: Calculated take profit price
            rr_ratio: Risk/Reward ratio (reward_distance / risk_distance)
            stop_loss_pct: Stop loss as percentage of entry price
            take_profit_pct: Take profit as percentage of entry price
            unified_data: Complete market analysis data (contains volatility, trend, market conditions, etc.)
            strategy: Current trading strategy
            
        Returns:
            Confidence percentage (0.0 - 100.0)
        """
        # CONFIDENCE CALCULATION NOT IMPLEMENTED YET
        # This is a critical component that requires extensive research and validation
        # Returning None to indicate confidence is not available (optional field)
        # When implemented, should consider:
        #   - Entry quality (setup scores)
        #   - Direction strength (score differential)
        #   - Risk/Reward ratio quality
        #   - Market conditions alignment
        #   - Historical prediction accuracy (if available)
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
        Score an entry setup using unified scoring framework
        
        CRITICAL: Entry scoring is LOCATIONAL (S/R, ATR, proximity, fill probability)
        and is INDEPENDENT of direction scores. The 'direction' parameter is used ONLY
        for LONG vs SHORT logic (e.g., LONG entries should be below current price),
        NOT for scoring based on direction strength.
        
        Uses factor scorers to calculate a total entry score, then returns setup details.
        
        Args:
            direction: "LONG" or "SHORT" - used for entry logic only, NOT for scoring
                      (entry scoring is independent of direction scores)
        
        Returns:
            Dict with "entry_price", "setup_type", "score", "reasoning", or None if invalid
        """
        try:
            # All required data must be present (NO FALLBACKS)
            current_price = self._require_key(unified_data, "current_price", "entry scoring")
            if current_price <= 0 or entry_price <= 0:
                raise ValueError(f"Invalid prices: current_price={current_price}, entry_price={entry_price}")
            
            # Get strategy-specific entry weights (config defaults are OK)
            # NOTE: SR power includes touch, reversal_probability, and volume (inherent strength)
            # Proximity and recency are handled separately in entry scoring (contextual factors)
            strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
            entry_weights = strategy_config["entry_weights"] if "entry_weights" in strategy_config else {  # Use default if not in strategy config
                "support_resistance": 0.45,  # Primary factor - SR power (touch 60%, reversal_prob 30%, volume 10%)
                "rsi": 0.18,  # Additional factor not in SR power
                "trend": 0.13,  # Additional factor not in SR power
                "pressure": 0.09,  # Additional factor not in SR power
                "patterns": 0.05,  # Additional factor not in SR power
                "orderbook": 0.07,  # Real-time liquidity/pressure alignment
                "market_conditions": 0.03  # Extreme sentiment → prefer stronger levels
                # Note: IV Squeeze removed - it's for timing/decisions, not entry price accuracy
                # Note: Proximity (distance) is scored separately in _score_entry_sr_factor based on entry offset
                # Note: Recency is handled in direction scoring, not entry scoring
            }
            
            # CRITICAL FIX: Validate and normalize entry weights to prevent ML training/inference mismatch
            # Weights must sum to 1.0 for consistent score magnitudes across strategies
            total_weight = sum(entry_weights.values())
            # CRITICAL FIX: Use epsilon comparison for float equality (prevents non-determinism)
            if not self._float_eq(total_weight, 1.0, self.WEIGHT_EPSILON):
                logger.warning(f"⚠️ Entry weights for {strategy} sum to {total_weight:.4f}, not 1.0. Normalizing...")
                entry_weights = {k: v / total_weight for k, v in entry_weights.items()}
                logger.debug(f"✅ Normalized entry weights: {entry_weights}")
            
            # Extract indicators - all required (NO FALLBACKS)
            rsi_data = self._require_key(unified_data, "rsi", "entry scoring")
            trend_data = self._require_key(unified_data, "trend", "entry scoring")
            pressure_data = self._require_key(unified_data, "pressure", "entry scoring")
            patterns_data = self._require_key(unified_data, "patterns", "entry scoring")
            volume_category = self._require_key(unified_data, "volume_category", "entry scoring")
            
            # Extract ATR for ATR-based scoring (FIXED 2026-01-20)
            sr_data = self._require_key(unified_data, "support_resistance", "entry scoring")
            sr_metadata = sr_data["metadata"]
            atr_5m = sr_metadata["atr_5m"]
            
            # Initialize score
            total_score = 0.0
            all_reasons = []
            
            # Score each factor using unified framework (all weights required - NO FALLBACKS)
            sr_weight = entry_weights["support_resistance"]  # Required (NO FALLBACKS)
            if sr_weight > 0:
                # Add setup_type to level_data for context
                level_data_with_type = {**level_data, "setup_type": setup_type}
                sr_score, reasons = self._score_entry_sr_factor(entry_price, current_price, direction, level_data_with_type, unified_data, strategy)
                total_score += sr_score * sr_weight
                all_reasons.extend(reasons)
            
            rsi_weight = entry_weights["rsi"]  # Required (NO FALLBACKS)
            if rsi_weight > 0:
                rsi_score, reasons = self._score_entry_rsi_factor(entry_price, current_price, direction, rsi_data, atr_5m)
                total_score += rsi_score * rsi_weight
                all_reasons.extend(reasons)
            
            trend_weight = entry_weights["trend"]  # Required (NO FALLBACKS)
            if trend_weight > 0:
                trend_score, reasons = self._score_entry_trend_factor(entry_price, current_price, direction, trend_data, strategy)
                total_score += trend_score * trend_weight
                all_reasons.extend(reasons)
            
            pressure_weight = entry_weights["pressure"]  # Required (NO FALLBACKS)
            if pressure_weight > 0:
                # IMPROVEMENT 4: Avoid double-counting pressure in entry scoring
                # If direction already heavily weighted on pressure, reduce entry weight
                direction_weights = strategy_config.get("direction_weights", {})
                direction_pressure_weight = direction_weights.get("pressure", 0.0)
                
                adjusted_pressure_weight = pressure_weight
                if TradingConfig.PRESSURE_ENTRY_WEIGHT_REDUCTION_ENABLED:
                    if direction_pressure_weight > TradingConfig.PRESSURE_ENTRY_REDUCTION_THRESHOLD:
                        reduction_factor = TradingConfig.PRESSURE_ENTRY_REDUCTION_FACTOR
                        adjusted_pressure_weight = pressure_weight * reduction_factor
                        logger.debug(
                            f"📊 Pressure entry weight reduced: {pressure_weight:.3f} → {adjusted_pressure_weight:.3f} "
                            f"(direction weight: {direction_pressure_weight:.3f} > {TradingConfig.PRESSURE_ENTRY_REDUCTION_THRESHOLD:.3f})"
                        )
                
                pressure_score, reasons = self._score_entry_pressure_factor(direction, pressure_data)
                total_score += pressure_score * adjusted_pressure_weight
                all_reasons.extend(reasons)
            
            patterns_weight = entry_weights["patterns"]  # Required (NO FALLBACKS)
            if patterns_weight > 0:
                patterns_score, reasons = self._score_entry_patterns_factor(direction, patterns_data)
                total_score += patterns_score * patterns_weight
                all_reasons.extend(reasons)
            
            # CRITICAL FIX: Volume anomaly removed from entry scoring
            # Volume anomaly should only affect direction (when to trade), not entry quality (where to trade)
            # Entry scoring should focus on S/R power, proximity, fill probability, liquidation safety
            # Volume anomaly is already considered in direction scoring via volume factor
            
            # Orderbook Imbalance - Real-time liquidity/pressure at entry level
            # NO FALLBACKS - if orderbook weight is specified, data must exist
            if "orderbook" in entry_weights:
                orderbook_weight = entry_weights["orderbook"]
                if orderbook_weight > 0:
                    orderbook_data = self._require_key(unified_data, "orderbook_analysis", "unified_data structure")
                    orderbook_score, reasons = self._score_entry_orderbook_factor(
                        direction, setup_type, orderbook_data, entry_price, current_price
                    )
                    total_score += orderbook_score * orderbook_weight
                    all_reasons.extend(reasons)
            
            # Market Conditions - Prefer stronger entries in extreme sentiment
            # NO FALLBACKS - if market_conditions weight is specified, data must exist
            if "market_conditions" in entry_weights:
                market_conditions_weight = entry_weights["market_conditions"]
                if market_conditions_weight > 0:
                    # NO FALLBACKS - if weight is specified, data must exist
                    market_conditions_data = self._require_key(unified_data, "market_conditions", "unified_data structure")
                    market_conditions_score, reasons = self._score_entry_market_conditions_factor(
                        direction, setup_type, market_conditions_data, level_data
                    )
                    total_score += market_conditions_score * market_conditions_weight
                    all_reasons.extend(reasons)
            
            # NOTE: IV Squeeze removed from entry setup scoring
            # IV Squeeze is for timing/decisions (WHEN to enter), not entry price accuracy (WHERE to enter)
            # Will be used in confidence calculation when implemented
            
            # NOTE: 
            # - Volume: included in SR power (10% weight)
            # - Distance/proximity: scored separately in _score_entry_sr_factor based on entry offset from level
            # - Recency: handled in direction scoring, not entry scoring
            
            # Removed excessive debug logging - only log top scores
            if total_score >= TradingConfig.CONFIDENCE_THRESHOLDS["min_score_log"]:  # Only log high-scoring setups
                logger.debug(f"📊 Entry setup scored: {setup_type} @ ${entry_price:.2f} = {total_score:.1f}")
            
            return {
                "entry_price": entry_price,
                "setup_type": setup_type,
                "score": total_score,
                "reasoning": "; ".join(all_reasons[:5]) if all_reasons else f"{setup_type} entry"
            }
            
        except Exception as e:
            logger.error(f"❌ Entry setup scoring failed: {e}")
            # NO FALLBACKS - entry setup scoring must succeed
            raise
    
    def _generate_setups_for_direction(
        self,
        unified_data: Dict[str, Any],
        direction: str,
        strategy: str,
        config: Dict[str, Any]
    ) -> list[Dict[str, Any]]:
        """
        Generate and score entry setups for a SPECIFIC direction only
        
        SEQUENTIAL FLOW - Step 3: After direction is determined, find best entry for that direction.
        Only evaluates entry quality (not direction support, since direction is already determined).
        
        Args:
            unified_data: Complete market analysis data
            direction: "LONG" or "SHORT" - the direction determined in Step 2
            strategy: Trading strategy name
            config: Strategy configuration
            
        Returns:
            List of setup dictionaries with entry_score, entry_price, entry_reasoning, etc.
        """
        try:
            # All required data must be present (NO FALLBACKS)
            current_price = self._require_key(unified_data, "current_price", "setup generation")
            if current_price <= 0:
                raise ValueError(f"Invalid current_price: {current_price}")
            
            # Extract market data - all required (NO FALLBACKS)
            sr_data = self._require_key(unified_data, "support_resistance", "setup generation")
            all_levels = self._require_key(sr_data, "levels", "setup generation")
            
            # Filter levels for entry setup based on strategy requirements
            from core.calculations.sr_level_filter import SRLevelFilter
            level_filter = SRLevelFilter()
            # Get metadata for ATR calculation
            sr_metadata = unified_data["support_resistance"]["metadata"]
            
            filtered_levels = level_filter.filter_for_entry_setup(
                all_levels=all_levels,
                current_price=current_price,
                strategy=strategy,
                sr_metadata=sr_metadata  # Pass metadata for ATR calculation
            )
            
            setups = []
            pre_filtered_count = 0  # Track levels pre-filtered by max_distance
            
            # Generate setups ONLY for the selected direction
            if direction == "LONG":
                # LONG: Only evaluate support levels (buying at support)
                top_support = filtered_levels["support"]
                
                for support in top_support:
                    level_price = self._require_key(support, "price_level", "setup generation")
                    if level_price <= 0 or level_price >= current_price:
                        continue  # Skip invalid or unfillable levels
                    
                    # Determine optimal entry price based on entry scoring factors
                    try:
                        entry_data = self._determine_optimal_entry_price(
                            level_price=level_price,
                            current_price=current_price,
                            direction="LONG",
                            setup_type="support_level",
                            level_data=support,
                            unified_data=unified_data,
                            strategy=strategy,
                            config=config
                        )
                        
                        if entry_data is None:
                            pre_filtered_count += 1  # Track pre-filtered levels
                            continue  # Skip if entry determination failed
                        
                        entry_price = entry_data["entry_price"]  # Required (NO FALLBACKS)
                        if entry_price is None or entry_price <= 0 or entry_price >= current_price:
                            continue  # Skip if entry is invalid or unfillable
                        
                        # CRITICAL FIX (2026-01-27): Use combined_score from multi-factor scoring
                        # This ensures true optimization across all candidates using fill_prob, liq_safety, level_strength, spread_penalty
                        # The combined_score from _determine_optimal_entry_price is the proper multi-factor score
                        entry_breakdown = entry_data.get("entry_breakdown", {})  # Required (NO FALLBACKS)
                        combined_score = entry_breakdown.get("combined_score", 0.0)  # Required (NO FALLBACKS)
                        
                        # Build entry reasoning from breakdown
                        fill_prob = entry_breakdown.get("fill_probability", 0.0)
                        liq_safety = entry_breakdown.get("liquidation_safety", 0.0)
                        level_strength = entry_breakdown.get("level_strength", 0.0)
                        spread_penalty = entry_breakdown.get("spread_penalty", 0.0)
                        distance_atr = entry_breakdown.get("distance_to_current_atr", 0.0)
                        
                        entry_reasoning = (
                            f"Optimal entry at {distance_atr:.2f}×ATR from current "
                            f"(fill_prob: {fill_prob:.1f}, liq_safety: {liq_safety:.1f}, "
                            f"level_strength: {level_strength:.1f}, spread_penalty: {spread_penalty:.1f})"
                        )
                        
                        # Debug logging: Show candidate score breakdown
                        logger.debug(
                            f"📊 Candidate from level ${level_price:.2f}: entry=${entry_price:.2f}, "
                            f"score={combined_score:.1f} (fill: {fill_prob:.1f}, liq: {liq_safety:.1f}, "
                            f"level: {level_strength:.1f}, spread: {spread_penalty:.1f})"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Entry price determination failed for support ${level_price:.2f}: {e}")
                        continue  # Skip this level if determination fails
                    
                    # Use multi-factor combined_score for entry selection
                    support_with_type = {**support, "setup_type": "support_level"}
                    setups.append({
                        "entry_price": entry_price,
                        "entry_score": combined_score,  # Use multi-factor combined_score
                        "entry_reasoning": entry_reasoning,
                        "setup_type": "support_level",
                        "level_data": support_with_type,
                        "entry_breakdown": entry_breakdown  # Store full breakdown for debugging
                    })
            
            else:  # SHORT
                # SHORT: Only evaluate resistance levels (selling at resistance)
                top_resistance = filtered_levels["resistance"]
                
                for resistance in top_resistance:
                    level_price = self._require_key(resistance, "price_level", "setup generation")
                    if level_price <= 0 or level_price <= current_price:
                        continue  # Skip invalid or unfillable levels
                    
                    # Determine optimal entry price based on entry scoring factors
                    try:
                        entry_data = self._determine_optimal_entry_price(
                            level_price=level_price,
                            current_price=current_price,
                            direction="SHORT",
                            setup_type="resistance_level",
                            level_data=resistance,
                            unified_data=unified_data,
                            strategy=strategy,
                            config=config
                        )
                        
                        if entry_data is None:
                            pre_filtered_count += 1  # Track pre-filtered levels
                            continue  # Skip if entry determination failed
                        
                        entry_price = entry_data["entry_price"]  # Required (NO FALLBACKS)
                        if entry_price is None or entry_price <= 0 or entry_price <= current_price:
                            continue  # Skip if entry is invalid or unfillable
                        
                        # CRITICAL FIX (2026-01-27): Use combined_score from multi-factor scoring
                        # This ensures true optimization across all candidates using fill_prob, liq_safety, level_strength, spread_penalty
                        entry_breakdown = entry_data.get("entry_breakdown", {})  # Required (NO FALLBACKS)
                        combined_score = entry_breakdown.get("combined_score", 0.0)  # Required (NO FALLBACKS)
                        
                        # Build entry reasoning from breakdown
                        fill_prob = entry_breakdown.get("fill_probability", 0.0)
                        liq_safety = entry_breakdown.get("liquidation_safety", 0.0)
                        level_strength = entry_breakdown.get("level_strength", 0.0)
                        spread_penalty = entry_breakdown.get("spread_penalty", 0.0)
                        distance_atr = entry_breakdown.get("distance_to_current_atr", 0.0)
                        
                        entry_reasoning = (
                            f"Optimal entry at {distance_atr:.2f}×ATR from current "
                            f"(fill_prob: {fill_prob:.1f}, liq_safety: {liq_safety:.1f}, "
                            f"level_strength: {level_strength:.1f}, spread_penalty: {spread_penalty:.1f})"
                        )
                        
                        # Debug logging: Show candidate score breakdown
                        logger.debug(
                            f"📊 Candidate from level ${level_price:.2f}: entry=${entry_price:.2f}, "
                            f"score={combined_score:.1f} (fill: {fill_prob:.1f}, liq: {liq_safety:.1f}, "
                            f"level: {level_strength:.1f}, spread: {spread_penalty:.1f})"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Entry price determination failed for resistance ${level_price:.2f}: {e}")
                        continue  # Skip this level if determination fails
                    
                    # Use multi-factor combined_score for entry selection
                    resistance_with_type = {**resistance, "setup_type": "resistance_level"}
                    setups.append({
                        "entry_price": entry_price,
                        "entry_score": combined_score,  # Use multi-factor combined_score
                        "entry_reasoning": entry_reasoning,
                        "setup_type": "resistance_level",
                        "level_data": resistance_with_type,
                        "entry_breakdown": entry_breakdown  # Store full breakdown for debugging
                    })
            
            # CRITICAL: There should ALWAYS be S/R levels (except at all-time high)
            # If no setups found, this indicates a system error in S/R level calculation/filtering
            # NO FALLBACKS - fix the S/R level system, don't create fake entries
            if not setups:
                # NO FALLBACKS - filtered_levels must have support and resistance keys
                support_count = len(self._require_key(filtered_levels, "support", "filtered_levels structure"))
                resistance_count = len(self._require_key(filtered_levels, "resistance", "filtered_levels structure"))
                total_levels = len(all_levels)
                
                raise ValueError(
                    f"No entry setups generated for {direction} direction ({strategy} strategy) - SYSTEM ERROR (NO FALLBACKS). "
                    f"Total S/R levels: {total_levels}, Filtered support: {support_count}, Filtered resistance: {resistance_count}. "
                    f"Current price: ${current_price:.2f}. "
                    f"This indicates S/R level calculation or filtering is broken - there should ALWAYS be levels available."
                )
            
            # Log summary of entry setup generation
            if pre_filtered_count > 0:
                logger.debug(f"📊 Pre-filtered {pre_filtered_count} levels exceeding max_distance_atr for {direction} direction")
            logger.debug(f"📊 Generated {len(setups)} entry setups for {direction} direction ({strategy} strategy)")
            return setups
            
        except Exception as e:
            logger.error(f"❌ Setup generation for {direction} direction failed: {e}")
            # NO FALLBACKS - if setup generation fails, it's a critical error
            raise
    
    def _determine_optimal_entry_price(
        self,
        level_price: float,
        current_price: float,
        direction: str,
        setup_type: str,
        level_data: Dict[str, Any],
        unified_data: Dict[str, Any],
        strategy: str,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Determine optimal entry price for BTC perp trading (research-backed)
        
        Generates 4 entry candidates with offsets INSIDE S/R zone (toward current price):
        - 0×ATR (at level)
        - 0.3×ATR inside
        - 0.6×ATR inside
        - 1.0×ATR inside
        
        Scores each candidate by:
        - Fill probability (30%): Closer to current = higher
        - Liquidation safety (35%): Distance from liquidation
        - Level strength (25%): S/R power
        - Spread penalty (10%): Cost of execution
        
        Returns the best scoring candidate.
        
        Args:
            level_price: S/R level price
            current_price: Current market price
            direction: "LONG" or "SHORT"
            setup_type: "support_level" or "resistance_level"
            level_data: Level metadata (power, last_touch_timestamp, etc.)
            unified_data: Complete market analysis data
            strategy: Trading strategy
            config: Strategy configuration
            
        Returns:
            Dict with "entry_price", "entry_score", "entry_breakdown" or None if invalid
        """
        try:
            # Get ATR for distance calculations
            atr_pct = self._get_atr_pct(unified_data, current_price)
            sr_data = unified_data["support_resistance"]  # Required (NO FALLBACKS)
            sr_metadata = sr_data["metadata"]  # Required (NO FALLBACKS)
            atr_5m = sr_metadata["atr_5m"]  # Required (NO FALLBACKS)
            if atr_5m <= 0:
                raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
            
            # Get strategy config for max_distance check and offset calculation
            from config.config import TradingConfig
            strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
            entry_proximity_config = strategy_config["entry_proximity_config"]  # Required (NO FALLBACKS)
            max_distance_atr = entry_proximity_config.get("max_distance_atr", 5.0)  # Default 5×ATR if not specified
            optimal_atr_distance = entry_proximity_config["optimal_atr"]  # Required (NO FALLBACKS) - needed for adaptive pre-filter validation
            offset_factors = TradingConfig.ENTRY_CANDIDATE_OFFSET_FACTORS
            max_offset_atr = max(offset_factors) * optimal_atr_distance
            
            # Extract level_power early for pre-filtering check
            level_power = level_data["power"]  # Required (NO FALLBACKS)
            
            # Get strategy config for max_distance check and offset calculation
            from config.config import TradingConfig
            strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
            entry_proximity_config = strategy_config["entry_proximity_config"]  # Required (NO FALLBACKS)
            optimal_atr_distance = entry_proximity_config["optimal_atr"]  # Required (NO FALLBACKS)
            offset_factors = TradingConfig.ENTRY_CANDIDATE_OFFSET_FACTORS
            max_offset_atr = max(offset_factors) * optimal_atr_distance
            
            # CRITICAL FIX (2026-01-27): Pre-filter level by max_distance before candidate generation
            # Calculate level distance in ATR to determine if closest candidate would be within max_distance
            from core.utils.distance_utils import calculate_distance_pct, calculate_distance_atr
            level_distance_pct = calculate_distance_pct(level_price, current_price, current_price)
            level_distance_atr = calculate_distance_atr(level_distance_pct, atr_pct)
            
            # Pre-filter: Skip levels where closest candidate (at level_price) exceeds max_distance
            # CRITICAL FIX (2026-01-27): Allow strong levels slightly beyond max_distance to compete
            # This enables strong far levels to compete with weak close levels
            # CRITICAL FIX: Use config instead of hardcoded values
            strength_threshold = TradingConfig.ADAPTIVE_PRE_FILTER_STRENGTH_THRESHOLD
            # Validate config values (NO FALLBACKS)
            if not (0.0 <= strength_threshold <= 1.0):
                raise ValueError(f"Invalid ADAPTIVE_PRE_FILTER_STRENGTH_THRESHOLD: {strength_threshold} (must be 0.0-1.0, NO FALLBACKS)")
            
            distance_extension = TradingConfig.ADAPTIVE_PRE_FILTER_DISTANCE_EXTENSION
            if distance_extension < 1.0:
                raise ValueError(f"Invalid ADAPTIVE_PRE_FILTER_DISTANCE_EXTENSION: {distance_extension} (must be >= 1.0, NO FALLBACKS)")
            
            adaptive_max_distance = max_distance_atr * distance_extension
            
            # CRITICAL FIX: Validate scale consistency for adaptive pre-filter
            # level_power is in range [0, 100], strength_threshold is in range [0, 1.0]
            # Normalize level_power to [0, 1.0] before comparison
            # Power scale: [0-100] from SRScorer.calculate_power() and PsychologicalLevelGenerator
            if level_power > 100.0 or level_power < 0.0:
                raise ValueError(f"Invalid level_power: {level_power} (must be in range [0, 100], NO FALLBACKS)")
            
            # Normalize level_power from [0, 100] to [0, 1.0] for comparison with strength_threshold
            normalized_power = level_power / 100.0
            assert 0.0 <= normalized_power <= 1.0, f"Normalized power out of range: {normalized_power} (from level_power: {level_power})"
            
            if level_distance_atr > max_distance_atr:
                # Adaptive pre-filtering: Allow very strong levels slightly beyond max_distance
                if normalized_power >= strength_threshold and level_distance_atr <= adaptive_max_distance:
                    # CRITICAL FIX: Validate that this level can generate at least one valid candidate
                    # Calculate optimal_offset_usd here (needed for validation)
                    optimal_offset_usd_temp = atr_5m * optimal_atr_distance
                    max_offset_usd = optimal_offset_usd_temp * max(offset_factors)  # Maximum offset in USD
                    
                    if setup_type == "support_level":  # LONG
                        # CRITICAL: Factor=0.0 candidate = level_price itself should always be valid
                        # if level_price < current_price (already checked before calling this method)
                        # So we only need to check distance constraint for adaptive pre-filter
                        closest_candidate_distance_atr = level_distance_atr - max_offset_atr
                        if closest_candidate_distance_atr > max_distance_atr:
                            logger.debug(
                                f"⏭️ Strong support level ${level_price:.2f} (power: {level_power:.2f}) rejected: "
                                f"even closest candidate would be {closest_candidate_distance_atr:.2f}×ATR "
                                f"(exceeds max {max_distance_atr:.2f}×ATR, level_distance: {level_distance_atr:.2f}×ATR, max_offset: {max_offset_atr:.2f}×ATR)"
                            )
                            return None  # Skip this level - cannot generate valid candidates
                    else:  # resistance_level - SHORT
                        # CRITICAL: Factor=0.0 candidate = level_price itself should always be valid
                        # if level_price > current_price (already checked before calling this method)
                        # So we only need to check distance constraint for adaptive pre-filter
                        closest_candidate_distance_atr = level_distance_atr - max_offset_atr
                        if closest_candidate_distance_atr > max_distance_atr:
                            logger.debug(
                                f"⏭️ Strong resistance level ${level_price:.2f} (power: {level_power:.2f}) rejected: "
                                f"even closest candidate would be {closest_candidate_distance_atr:.2f}×ATR "
                                f"(exceeds max {max_distance_atr:.2f}×ATR, level_distance: {level_distance_atr:.2f}×ATR, max_offset: {max_offset_atr:.2f}×ATR)"
                            )
                            return None  # Skip this level - cannot generate valid candidates
                    
                    logger.debug(
                        f"📊 Strong level ${level_price:.2f} (power: {level_power:.2f}, normalized: {normalized_power:.3f}) allowed despite distance "
                        f"{level_distance_atr:.2f}×ATR (max: {max_distance_atr:.2f}×ATR, adaptive: {adaptive_max_distance:.2f}×ATR, threshold: {strength_threshold:.3f})"
                    )
                    # Continue - allow this strong level to generate candidates (at least one will be valid)
                else:
                    logger.debug(
                        f"⏭️ Level ${level_price:.2f} pre-filtered: distance {level_distance_atr:.2f}×ATR exceeds max {max_distance_atr:.2f}×ATR "
                        f"(power: {level_power:.2f}, normalized: {normalized_power:.3f}, threshold: {strength_threshold:.3f})"
                    )
                    return None  # Skip this level - calling code handles None gracefully
            
            # BTC PERP ENTRY OFFSET LOGIC (Research-backed)
            # Research findings (2025-2026 BTC perpetual futures):
            #   - Price regularly wicks THROUGH S/R levels before bouncing (liquidation hunting)
            #   - Market makers actively hunt stops at obvious levels
            #   - 40x leverage: 2.5% adverse move = liquidation
            #   - Professional practice: Enter +0.3 to +0.5× ATR INSIDE zone (toward current price)
            # 
            # Rationale for offset toward current:
            #   - Survives liquidation wick-through (common 0.5-1% wicks before bounce)
            #   - Higher fill probability (closer to current price)
            #   - Still catches majority of bounce (0.3-0.5× ATR ≈ 0.1-0.2% typically)
            #   - Avoids being "first in line" for liquidation during stop hunts
            
            # Generate entry candidates with offsets INSIDE the zone (toward current price)
            candidates = []
            
            # Strategy-specific optimal offset from config (already retrieved above for validation)
            # optimal_atr_distance and offset_factors already calculated above for adaptive pre-filter
            
            # Calculate optimal offset distance in USD
            optimal_offset_usd = atr_5m * optimal_atr_distance
            
            if setup_type == "support_level":  # LONG at support
                # Enter ABOVE support (closer to current price, inside zone)
                for factor in offset_factors:
                    candidate = level_price + (optimal_offset_usd * factor)
                    # Validate: must be below current price (LONG entry)
                    if 0 < candidate < current_price:
                        candidates.append(candidate)
            else:  # resistance_level - SHORT at resistance
                # Enter BELOW resistance (closer to current price, inside zone)
                for factor in offset_factors:
                    candidate = level_price - (optimal_offset_usd * factor)
                    # Validate: must be above current price (SHORT entry)
                    if candidate > current_price:
                        candidates.append(candidate)
            
            # NO FALLBACKS - must always generate at least one candidate
            # If no candidates generated, this indicates a logic error in candidate generation
            # CRITICAL: With factor=0.0, candidate = level_price should always be valid if level_price < current_price (LONG) or level_price > current_price (SHORT)
            if not candidates:
                # Enhanced error message with diagnostic information to identify root cause
                offset_info = f"offset_factors: {offset_factors}, optimal_offset_usd: ${optimal_offset_usd:.2f}"
                if setup_type == "support_level":
                    price_constraint = f"level_price ${level_price:.2f} < current_price ${current_price:.2f}"
                    # Check each offset factor
                    candidate_checks = []
                    for factor in offset_factors:
                        candidate = level_price + (optimal_offset_usd * factor)
                        is_valid = 0 < candidate < current_price
                        candidate_checks.append(f"factor={factor}: ${candidate:.2f} valid={is_valid}")
                    candidates_info = ", ".join(candidate_checks)
                    level_price_valid = 0 < level_price < current_price and level_distance_atr <= max_distance_atr
                    level_price_info = f"level_price itself should be valid: {level_price_valid} (level_distance: {level_distance_atr:.2f}×ATR <= max: {max_distance_atr:.2f}×ATR)"
                else:
                    price_constraint = f"level_price ${level_price:.2f} > current_price ${current_price:.2f}"
                    # Check each offset factor
                    candidate_checks = []
                    for factor in offset_factors:
                        candidate = level_price - (optimal_offset_usd * factor)
                        is_valid = candidate > current_price
                        candidate_checks.append(f"factor={factor}: ${candidate:.2f} valid={is_valid}")
                    candidates_info = ", ".join(candidate_checks)
                    level_price_valid = level_price > current_price and level_distance_atr <= max_distance_atr
                    level_price_info = f"level_price itself should be valid: {level_price_valid} (level_distance: {level_distance_atr:.2f}×ATR <= max: {max_distance_atr:.2f}×ATR)"
                
                raise ValueError(
                    f"No valid entry candidates for {setup_type} at ${level_price:.2f} (current: ${current_price:.2f}) - "
                    f"system error: _determine_optimal_entry_price must always generate candidates (NO FALLBACKS). "
                    f"Level distance: {level_distance_atr:.2f}×ATR, max_distance: {max_distance_atr:.2f}×ATR, "
                    f"{offset_info}, {price_constraint}, {level_price_info}. "
                    f"Candidate checks: {candidates_info}. "
                    f"This indicates candidate generation logic error - fix the root cause."
                )
            
            # Score each candidate using BTC perp-optimized scoring
            # Factors (research-backed for 40x leverage perps):
            #   1. Fill probability (35%): Closer to current = higher fill rate
            #   2. Liquidation safety (35%): Distance from liquidation price
            #   3. Level strength (20%): S/R power (inherent quality)
            #   4. Spread penalty (-10%): Closer to current = pay more spread
            
            # level_power already extracted above for pre-filtering
            last_touch_timestamp = level_data["last_touch_timestamp"]  # Required (NO FALLBACKS)
            
            # Calculate liquidation price for safety scoring
            from core.calculations.liquidation_calculator import LiquidationCalculator
            liq_calc = LiquidationCalculator(leverage=TradingConfig.LEVERAGE)
            
            # Get spread for penalty calculation (NO FALLBACKS)
            from core.utils.distance_utils import calculate_distance_pct, calculate_distance_atr
            orderbook_data = self._require_key(unified_data, "orderbook_analysis", "entry price calculation")
            spread_data = self._require_key(orderbook_data, "bid_ask_spread", "entry price calculation")
            spread_pct = spread_data["percentage"] / 100.0  # Convert to decimal (NO FALLBACKS)
            
            # Maximum distance constraint: reject candidates beyond strategy-specific maximum
            # This prevents selection of entries unlikely to fill
            # NOTE: Level was already pre-filtered above, so at least closest candidate should be within max_distance
            # This filter now serves as a safety check and to prioritize closer candidates
            
            best_candidate = None
            best_score = -1.0
            best_breakdown = None
            candidates_processed = 0
            candidates_rejected = 0
            
            # Filter candidates by max_distance (safety check - level was pre-filtered)
            valid_candidates = []
            for candidate_price in candidates:
                # Calculate distance to current price for filtering
                distance_to_current_pct = calculate_distance_pct(candidate_price, current_price, current_price)
                distance_to_current_atr_temp = calculate_distance_atr(distance_to_current_pct, atr_pct)
                
                # Filter: reject candidates beyond maximum distance
                if distance_to_current_atr_temp > max_distance_atr:
                    candidates_rejected += 1
                    logger.debug(f"⏭️ Candidate ${candidate_price:.2f} rejected: distance {distance_to_current_atr_temp:.2f}×ATR exceeds maximum {max_distance_atr:.2f}×ATR")
                    continue
                
                valid_candidates.append(candidate_price)
            
            # Safety check: After pre-filtering, at least closest candidate should be valid
            if not valid_candidates:
                # This should never happen if pre-filter worked correctly
                raise ValueError(
                    f"System error: Pre-filter passed but no valid candidates for {setup_type} at ${level_price:.2f} "
                    f"(level_distance: {level_distance_atr:.2f}×ATR, max: {max_distance_atr:.2f}×ATR, "
                    f"generated {len(candidates)} candidates, all rejected). "
                    f"Possible causes: (1) ATR calculation error, (2) Level too far despite pre-filter, "
                    f"(3) Candidate generation logic error - NO FALLBACKS"
                )
            
            # Use valid candidates for scoring (replace original candidates list)
            candidates = valid_candidates
            
            # Log summary of candidate filtering
            if candidates_rejected > 0:
                logger.debug(f"📊 Rejected {candidates_rejected} candidates exceeding max_distance_atr ({max_distance_atr:.2f}×ATR) for {setup_type} at ${level_price:.2f}")
            
            for candidate_price in candidates:
                candidates_processed += 1
                # 1. FILL PROBABILITY SCORE (35% weight) - Non-linear exponential decay
                # Formula: Exponential decay from 100 at current → ~50 at 3×ATR → ~10 at 6×ATR
                # More realistic than linear: fill probability drops faster as distance increases
                distance_to_current_pct = calculate_distance_pct(candidate_price, current_price, current_price)
                distance_to_current_atr = calculate_distance_atr(distance_to_current_pct, atr_pct)
                
                # Exponential decay: fill_prob = 100 * exp(-distance_atr / decay_factor)
                # decay_factor = 3.0 means: at 3×ATR, fill_prob ≈ 100 * exp(-1) ≈ 37
                # at 6×ATR, fill_prob ≈ 100 * exp(-2) ≈ 13.5
                # CRITICAL FIX: Add numerical stability bounds to prevent overflow/underflow
                fill_decay_factor = TradingConfig.ENTRY_FILL_DECAY_FACTOR
                if fill_decay_factor <= 0:
                    raise ValueError(f"Invalid fill_decay_factor: {fill_decay_factor} - must be positive")
                if distance_to_current_atr < 0:
                    distance_to_current_atr = 0.0  # Clamp to 0 (shouldn't happen, but safety check)
                
                # Clamp exponent to prevent overflow/underflow
                # exp(-50) ≈ 1.9e-22 (effectively 0), exp(50) ≈ 5.2e+21 (would overflow)
                exponent = -distance_to_current_atr / fill_decay_factor
                exponent = max(-50.0, min(50.0, exponent))  # Clamp to safe range
                fill_probability = 100.0 * math.exp(exponent)
                
                # CRITICAL FIX: Apply sanity caps based on distance to prevent optimistic bias
                # Enforce monotonic decreasing caps: closer entries can have higher fill probability
                if distance_to_current_atr <= 0.5:
                    fill_probability = min(fill_probability, TradingConfig.FILL_PROBABILITY_CAP_AT_0_5_ATR)
                elif distance_to_current_atr >= 3.0:
                    fill_probability = min(fill_probability, TradingConfig.FILL_PROBABILITY_CAP_AT_3_0_ATR)
                elif distance_to_current_atr >= 2.0:
                    fill_probability = min(fill_probability, TradingConfig.FILL_PROBABILITY_CAP_AT_2_0_ATR)
                
                # Clamp result using config values (final bounds)
                fill_probability = max(
                    TradingConfig.FILL_PROBABILITY_MIN,
                    min(TradingConfig.FILL_PROBABILITY_MAX, fill_probability)
                )
                
                # Orderbook depth adjustment: Higher liquidity = better fill probability
                # Orderbook depth is optional - if available, boost fill probability
                # NO FALLBACKS - if liquidity_depth exists, it must have depth_score
                if "liquidity_depth" in orderbook_data:
                    liquidity_depth = orderbook_data["liquidity_depth"]
                    depth_score = self._require_key(liquidity_depth, "depth_score", "liquidity_depth structure")
                    # Boost fill probability by up to configured maximum for high liquidity
                    liquidity_boost = (depth_score / 100.0) * TradingConfig.FILL_PROBABILITY_LIQUIDITY_BOOST_MAX
                    fill_probability = min(TradingConfig.FILL_PROBABILITY_MAX, fill_probability + liquidity_boost)
                
                # 2. LIQUIDATION SAFETY SCORE (35% weight) - Non-linear sigmoid curve
                # Calculate liquidation price from this entry
                liquidation_price = liq_calc.calculate_liquidation_price(candidate_price, direction)
                # Distance from entry to liquidation (as % of entry)
                if direction == "LONG":
                    liq_distance_pct = (candidate_price - liquidation_price) / candidate_price
                else:  # SHORT
                    liq_distance_pct = (liquidation_price - candidate_price) / candidate_price
                
                # Sigmoid curve: More realistic than linear
                # Formula: 100 / (1 + exp(-k * (distance - midpoint)))
                # k controls steepness, midpoint is the inflection point
                # For 40x leverage: want >1.5% for safety, 2.0% is ideal
                # CRITICAL FIX: Add numerical stability bounds to prevent overflow
                liq_safety_midpoint_pct = TradingConfig.LIQUIDATION_SAFETY_MIDPOINT_PCT  # 1.5% default
                liq_safety_steepness = TradingConfig.LIQUIDATION_SAFETY_STEEPNESS  # Controls curve steepness
                if liq_safety_steepness <= 0:
                    raise ValueError(f"Invalid liq_safety_steepness: {liq_safety_steepness} - must be positive")
                
                liq_distance_normalized = (liq_distance_pct - liq_safety_midpoint_pct) * 100  # Convert to basis points
                
                # Clamp exponent to prevent overflow
                # exp(-50) ≈ 1.9e-22 (effectively 0), exp(50) ≈ 5.2e+21 (would overflow)
                exponent = -liq_safety_steepness * liq_distance_normalized
                exponent = max(-50.0, min(50.0, exponent))  # Clamp to safe range
                liquidation_safety = 100.0 / (1.0 + math.exp(exponent))
                liquidation_safety = max(0.0, min(100.0, liquidation_safety))  # Clamp result to [0, 100]
                
                # 3. LEVEL STRENGTH SCORE (25% weight) - RAW POWER (NO PROXIMITY WEIGHTING)
                # CRITICAL FIX (2026-01-27): Removed proximity weighting from level strength
                # Rationale: Fill probability already penalizes distance (30% weight). Double-penalizing in level
                # strength unfairly biases against strong far levels. Raw level power allows strong levels to compete.
                # Level strength represents inherent S/R quality (touches, bounces, time-tested), not proximity.
                level_strength = level_power  # Use raw power, no distance decay
                
                # Proximity factor still calculated for ML feature exposure (exposed but not used in scoring)
                level_strength_decay_factor = TradingConfig.LEVEL_STRENGTH_DECAY_FACTOR
                if level_strength_decay_factor <= 0:
                    raise ValueError(f"Invalid level_strength_decay_factor: {level_strength_decay_factor} - must be positive")
                proximity_exponent = -distance_to_current_atr / level_strength_decay_factor
                proximity_exponent = max(-50.0, min(50.0, proximity_exponent))  # Clamp for numerical stability
                proximity_factor = math.exp(proximity_exponent)
                proximity_factor = max(0.1, min(1.0, proximity_factor))  # Clamp to [0.1, 1.0]
                # NOTE: proximity_factor is exposed in breakdown for ML features but NOT used in level_strength calculation
                
                # 4. SPREAD COST PENALTY (-10% weight) - NON-LINEAR
                # Exponential penalty for very close entries (< 0.5×ATR), linear for far entries
                # Rationale: Spread cost increases non-linearly as distance approaches zero
                spread_close_threshold = TradingConfig.SPREAD_PENALTY_CLOSE_THRESHOLD_ATR
                spread_boost = TradingConfig.SPREAD_PENALTY_EXPONENTIAL_BOOST
                spread_decay = TradingConfig.SPREAD_PENALTY_EXPONENTIAL_DECAY
                spread_max = TradingConfig.SPREAD_PENALTY_MAX
                
                spread_base = TradingConfig.SPREAD_PENALTY_BASE
                
                if distance_to_current_atr < spread_close_threshold:
                    # Exponential boost for very close entries
                    close_exponent = -distance_to_current_atr / spread_decay
                    close_exponent = max(-50.0, min(50.0, close_exponent))  # Clamp for numerical stability
                    close_penalty_boost = spread_boost * math.exp(close_exponent)
                    spread_penalty = spread_base + close_penalty_boost
                    spread_penalty = min(spread_max, spread_penalty)  # Cap at maximum
                else:
                    # Linear penalty for entries beyond threshold
                    spread_penalty = max(0.0, (1.0 - distance_to_current_atr) * spread_base)
                
                # IMPROVED ENTRY SCORING (2026-01-27): Weights sum to 1.0, no normalization needed
                # New weights: 40% fill, 35% liq, 15% level, 10% spread penalty
                entry_weights = TradingConfig.ENTRY_SCORING_WEIGHTS
                fill_weight = entry_weights["fill_probability"]
                liq_weight = entry_weights["liquidation_safety"]
                level_weight = entry_weights["level_strength"]
                spread_weight = entry_weights["spread_penalty"]
                
                # Validate weights sum to 1.0
                weight_sum = fill_weight + liq_weight + level_weight + spread_weight
                if abs(weight_sum - 1.0) > self.WEIGHT_EPSILON:
                    raise ValueError(f"Entry scoring weights must sum to 1.0, got {weight_sum}")
                
                # WEIGHTED COMBINED SCORE (weights already sum to 1.0, no normalization needed)
                combined_score = (
                    fill_probability * fill_weight +
                    liquidation_safety * liq_weight +
                    level_strength * level_weight -
                    spread_penalty * spread_weight
                )
                # Clamp to reasonable range (penalty can make score slightly negative)
                combined_score = max(0.0, min(100.0, combined_score))
                # Assertion for ML validation: ensure score is always in expected range
                assert 0.0 <= combined_score <= 100.0, f"Combined score out of range: {combined_score} (entry: ${candidate_price:.2f})"
                
                # Performance optimization: Early exit if perfect score found (unlikely but possible)
                # This avoids unnecessary scoring of remaining candidates when we have a near-perfect entry
                if combined_score >= 99.9:  # Near-perfect score (within 0.1 of maximum)
                    logger.debug(f"🎯 Near-perfect candidate found: ${candidate_price:.2f} (score: {combined_score:.1f}) - skipping remaining candidates")
                    best_score = combined_score
                    best_candidate = candidate_price
                    # Calculate breakdown for this perfect candidate (reuse code below)
                    # CRITICAL FIX: Use unified_data timestamp (NO FALLBACKS)
                    current_timestamp = self._require_key(unified_data, "timestamp", "entry scoring timestamp")
                    hours_since_touch = (current_timestamp - last_touch_timestamp) / 3600.0 if last_touch_timestamp > 0 else 0.0
                    distance_from_level_usd = abs(candidate_price - level_price)
                    distance_from_level_pct = distance_from_level_usd / current_price
                    
                    best_breakdown = {
                        "entry_price": candidate_price,
                        "level_price": level_price,
                        "offset_usd": distance_from_level_usd,
                        "offset_pct": distance_from_level_pct * 100,
                        "offset_atr": distance_from_level_usd / atr_5m if atr_5m > 0 else 0,
                        "fill_probability": fill_probability,
                        "liquidation_safety": liquidation_safety,
                        "liquidation_price": liquidation_price,
                        "liq_distance_pct": liq_distance_pct * 100,
                        "level_strength": level_strength,
                        "level_strength_raw": level_power,
                        "proximity_factor": proximity_factor,
                        "spread_penalty": spread_penalty,
                        "spread_penalty_breakdown": {
                            "base_penalty": spread_base if distance_to_current_atr < spread_close_threshold else max(0.0, (1.0 - distance_to_current_atr) * spread_base),
                            "exponential_boost": (spread_penalty - spread_base) if distance_to_current_atr < spread_close_threshold else 0.0,
                            "is_close_entry": distance_to_current_atr < spread_close_threshold
                        },
                        "combined_score": combined_score,
                        "distance_to_current_atr": distance_to_current_atr,
                        "hours_since_touch": hours_since_touch,
                        "setup_type": setup_type
                    }
                    break  # Exit loop early - no need to check remaining candidates
                
                # Track best candidate
                if combined_score > best_score:
                    best_score = combined_score
                    best_candidate = candidate_price
                    
                    # Calculate distance metrics
                    # CRITICAL FIX: Use unified_data timestamp (data timestamp), not time.time() (generation time)
                    # This prevents lookahead bias in ML training - timestamp must match prediction timestamp
                    # CRITICAL FIX: Use unified_data timestamp (NO FALLBACKS)
                    current_timestamp = self._require_key(unified_data, "timestamp", "entry scoring timestamp")
                    hours_since_touch = (current_timestamp - last_touch_timestamp) / 3600.0 if last_touch_timestamp > 0 else 0.0
                    distance_from_level_usd = abs(candidate_price - level_price)
                    distance_from_level_pct = distance_from_level_usd / current_price
                    
                    best_breakdown = {
                        "entry_price": candidate_price,
                        "level_price": level_price,
                        "offset_usd": distance_from_level_usd,
                        "offset_pct": distance_from_level_pct * 100,
                        "offset_atr": distance_from_level_usd / atr_5m if atr_5m > 0 else 0,
                        "fill_probability": fill_probability,
                        "liquidation_safety": liquidation_safety,
                        "liquidation_price": liquidation_price,
                        "liq_distance_pct": liq_distance_pct * 100,
                        "level_strength": level_strength,  # Raw level strength (no proximity weighting)
                        "level_strength_raw": level_power,  # Original level power (ML feature)
                        "proximity_factor": proximity_factor,  # Distance decay factor (ML feature)
                        "spread_penalty": spread_penalty,
                        "spread_penalty_breakdown": {
                            "base_penalty": spread_base if distance_to_current_atr < spread_close_threshold else max(0.0, (1.0 - distance_to_current_atr) * spread_base),
                            "exponential_boost": (spread_penalty - spread_base) if distance_to_current_atr < spread_close_threshold else 0.0,
                            "is_close_entry": distance_to_current_atr < spread_close_threshold
                        },
                        "combined_score": combined_score,
                        "distance_to_current_atr": distance_to_current_atr,
                        "hours_since_touch": hours_since_touch,
                        "setup_type": setup_type
                    }
            
            # NO FALLBACKS - must always find best candidate
            # After pre-filtering and candidate validation, at least one candidate should exist
            if best_candidate is None:
                # This should never happen - pre-filter ensures at least closest candidate is valid
                error_msg = (
                    f"System error: No best candidate selected for {setup_type} at ${level_price:.2f} "
                    f"(current: ${current_price:.2f}, level distance: {level_distance_atr:.2f}×ATR). "
                    f"Valid candidates: {len(valid_candidates)}, processed: {candidates_processed}. "
                    f"Max distance: {max_distance_atr:.2f}×ATR. "
                    f"Scoring loop must always find best candidate (NO FALLBACKS)"
                )
                raise ValueError(error_msg)
            
            # Round number avoidance: nudge entry if too close to psychological level
            # If abs(entry - nearest_psych_level) < ATR * 0.2, nudge by ATR * 0.25 away
            original_entry = best_candidate
            psych_nudge_applied = False
            nudge_distance = atr_5m * 0.25  # ATR * 0.25
            threshold_distance = atr_5m * 0.2  # ATR * 0.2
            
            # Find nearest psychological level
            sr_data = unified_data.get("support_resistance", {})
            all_levels = sr_data.get("levels", [])
            psych_levels = [l for l in all_levels if l.get("source") == "psych"]
            
            if psych_levels:
                nearest_psych = min(psych_levels, key=lambda l: abs(l["price_level"] - best_candidate))
                distance_to_psych = abs(best_candidate - nearest_psych["price_level"])
                
                if distance_to_psych < threshold_distance:
                    # Calculate nudged entry
                    if direction == "LONG":
                        # For LONG: nudge down (away from psych level)
                        nudged_entry = best_candidate - nudge_distance
                    else:  # SHORT
                        # For SHORT: nudge up (away from psych level)
                        nudged_entry = best_candidate + nudge_distance
                    
                    # CRITICAL FIX: Validate nudge doesn't violate max_distance_atr constraint
                    nudged_distance_pct = calculate_distance_pct(nudged_entry, current_price, current_price)
                    nudged_distance_atr = calculate_distance_atr(nudged_distance_pct, atr_pct)
                    
                    # Validate: (1) doesn't exceed max_distance, (2) doesn't invalidate entry direction
                    if nudged_distance_atr <= max_distance_atr:
                        if direction == "LONG" and nudged_entry < current_price:
                            best_candidate = nudged_entry
                            psych_nudge_applied = True
                            logger.debug(f"🎯 Entry nudged away from psych level ${nearest_psych['price_level']:.2f}: ${original_entry:.2f} → ${best_candidate:.2f}")
                        elif direction == "SHORT" and nudged_entry > current_price:
                            best_candidate = nudged_entry
                            psych_nudge_applied = True
                            logger.debug(f"🎯 Entry nudged away from psych level ${nearest_psych['price_level']:.2f}: ${original_entry:.2f} → ${best_candidate:.2f}")
                        else:
                            logger.debug(f"⚠️ Psych nudge invalidated entry direction (LONG: {nudged_entry < current_price}, SHORT: {nudged_entry > current_price}), skipping")
                    else:
                        logger.debug(f"⚠️ Psych nudge would exceed max_distance_atr ({nudged_distance_atr:.2f} > {max_distance_atr:.2f}×ATR), skipping")
            
            # Calculate distance to nearest psych level for ML features (exposed but not used yet)
            entry_distance_to_nearest_psych_pct = None
            if psych_levels:
                nearest_psych = min(psych_levels, key=lambda l: abs(l["price_level"] - best_candidate))
                entry_distance_to_nearest_psych_pct = abs(best_candidate - nearest_psych["price_level"]) / current_price if current_price > 0 else None
            
            # Update breakdown with final entry price and psych metrics
            best_breakdown["entry_price"] = best_candidate
            best_breakdown["offset_usd"] = abs(best_candidate - level_price)
            best_breakdown["offset_pct"] = abs(best_candidate - level_price) / current_price * 100 if current_price > 0 else 0.0
            best_breakdown["offset_atr"] = abs(best_candidate - level_price) / atr_5m if atr_5m > 0 else 0.0
            best_breakdown["psych_nudge_applied"] = psych_nudge_applied
            best_breakdown["entry_distance_to_nearest_psych_level_pct"] = entry_distance_to_nearest_psych_pct  # ML feature (exposed but not used)
            
            # Validate ML features (debug mode - logs warnings but doesn't block)
            try:
                from core.utils.ml_feature_validator import MLFeatureValidator
                is_valid, warnings = MLFeatureValidator.validate_entry_features(best_breakdown)
                MLFeatureValidator.log_validation_results(is_valid, warnings, "entry")
            except ImportError:
                pass  # Validator not available - skip validation
            
            # Enhanced debug logging: Show all scoring factors for verification
            logger.debug(
                f"✅ Entry selected: ${best_candidate:.2f} "
                f"(offset: {best_breakdown['offset_atr']:.2f}×ATR, distance: {best_breakdown['distance_to_current_atr']:.2f}×ATR, "
                f"fill_prob: {best_breakdown['fill_probability']:.1f}, liq_safety: {best_breakdown['liquidation_safety']:.1f}, "
                f"level_strength: {best_breakdown['level_strength']:.1f}, spread_penalty: {best_breakdown['spread_penalty']:.1f}, "
                f"combined_score: {best_score:.1f})"
            )
            
            return {
                "entry_price": best_candidate,
                "entry_score": best_score,
                "entry_breakdown": best_breakdown
            }
            
        except Exception as e:
            logger.error(f"❌ Optimal entry price determination failed: {e}")
            # NO FALLBACKS - entry price determination must succeed
            raise
    
    def _calculate_stop_and_target(
        self,
        entry_price: float,
        direction: str,
        config: Dict[str, Any],
        unified_data: Dict[str, Any],
        strategy: str,
        level_data: Optional[Dict[str, Any]] = None,
        setup_type: Optional[str] = None
    ) -> tuple[float, float, float, float, float]:
        """
        Calculate sophisticated stop loss and take profit
        
        CRITICAL: Stop/target calculation uses level_data and setup_type for S/R level
        selection only (where to place stop), NOT for entry score usage. Stop placement
        is based on S/R levels and ATR, independent of entry scoring.
        
        Delegates to RiskManager module for all risk calculations.
        
        Args:
            entry_price: Entry price for the trade
            direction: "LONG" or "SHORT"
            config: Strategy configuration
            unified_data: Complete market analysis data
            level_data: Level metadata for the entry level (optional) - used for S/R level selection only
            setup_type: "support_level" or "resistance_level" (optional) - used for S/R level selection only
            
        Returns:
            (stop_loss, take_profit, rr_ratio, stop_loss_pct, take_profit_pct) tuple
            - stop_loss: Stop loss price
            - take_profit: Take profit price
            - rr_ratio: Risk/Reward ratio (reward/risk)
            - stop_loss_pct: Stop loss as percentage of entry price
            - take_profit_pct: Take profit as percentage of entry price
        """
        try:
            from core.calculations.risk_manager import RiskManager
            from core.calculations.support_resistance_calculator import SupportResistanceCalculator
            
            current_price = self._require_key(unified_data, "current_price", "stop/target calculation")
            if current_price <= 0:
                raise ValueError(f"Invalid current_price: {current_price}")
            
            # Get ATR for calculations (NO FALLBACKS)
            sr_data = self._require_key(unified_data, "support_resistance", "stop/target calculation")
            sr_metadata = self._require_key(sr_data, "metadata", "support_resistance structure")
            atr_5m = self._require_key(sr_metadata, "atr_5m", "ATR for stop/target calculation")
            
            if atr_5m <= 0:
                raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
            
            # 1. Get S/R level for stop placement (delegated to calculator module)
            sr_stop_level = None
            try:
                sr_data = unified_data["support_resistance"]  # Required (NO FALLBACKS)
                if sr_data:
                    # Get all available levels (calculator now provides all levels, modules filter as needed)
                    all_levels = sr_data["levels"]  # Required (NO FALLBACKS)
                    if not all_levels:
                        raise ValueError("No S/R levels available in support_resistance.levels (NO FALLBACKS)")
                    
                    # Calculate minimum stop distance (2.0×ATR)
                    min_stop_distance = atr_5m * 2.0
                    # Maximum reasonable distance: 3×ATR (maintains reasonable R:R)
                    max_reasonable_distance = atr_5m * 3.0
                    
                    # Select optimal level for stop loss placement (handled by calculator module)
                    selected_level = SupportResistanceCalculator.select_stop_loss_level(
                        levels=all_levels,
                        entry_price=entry_price,
                        direction=direction,
                        atr_5m=atr_5m,
                        min_stop_distance=min_stop_distance,
                        max_reasonable_distance=max_reasonable_distance,
                        min_strength_score=60.0  # Prefer levels with strength >= 60
                    )
                    
                    if selected_level:
                        level_price = selected_level["price_level"]  # Required (NO FALLBACKS)
                        level_strength = selected_level["strength_score"]  # Required (NO FALLBACKS)
                        
                        # Validate level is not broken (safety check)
                        if direction == "LONG":
                            level_break_threshold = level_price - atr_5m
                            if current_price < level_break_threshold:
                                raise ValueError(f"Support level ${level_price:.2f} is broken (current_price ${current_price:.2f} < break_threshold ${level_break_threshold:.2f}) - cannot use for stop placement")
                        else:  # SHORT
                            level_break_threshold = level_price + atr_5m
                            if current_price > level_break_threshold:
                                raise ValueError(f"Resistance level ${level_price:.2f} is broken (current_price ${current_price:.2f} > break_threshold ${level_break_threshold:.2f}) - cannot use for stop placement")
                        
                        if level_price > 0:
                            # Place stop with noise buffer (FIXED 2026-01-12 - from config)
                            from config.config import TradingConfig
                            noise_buffer = atr_5m * TradingConfig.NOISE_BUFFER_ATR_MULTIPLIER
                            if direction == "LONG":
                                sr_stop_level = level_price - noise_buffer
                            else:  # SHORT
                                sr_stop_level = level_price + noise_buffer
                            
                            logger.debug(f"📉 {direction} stop from selected level: ${level_price:.2f} (strength: {level_strength:.1f}) → ${sr_stop_level:.2f}")
                    else:
                        # No suitable S/R level found - log details for debugging
                        if direction == "LONG":
                            supports = [l for l in all_levels if "type" in l and l["type"] == "support" and "price_level" in l and l["price_level"] < entry_price and "status" in l and l["status"] == "active"]
                            logger.warning(f"⚠️ No suitable LONG stop level found. Entry: ${entry_price:.2f}, Min distance: ${min_stop_distance:.2f}, Max reasonable: ${max_reasonable_distance:.2f}")
                            logger.warning(f"⚠️ Available supports below entry: {len(supports)}")
                            if supports:
                                distances = [entry_price - s["price_level"] for s in supports]  # Required (NO FALLBACKS)
                                strengths = [s["strength_score"] for s in supports]  # Required (NO FALLBACKS)
                                logger.warning(f"⚠️ Support distances from entry: {[f'${d:.2f}' for d in distances[:5]]}")
                                logger.warning(f"⚠️ Support strengths: {[f'{s:.1f}' for s in strengths[:5]]}")
                        else:  # SHORT
                            resistances = [l for l in all_levels if l["type"] == "resistance" and l["price_level"] > entry_price and l["status"] == "active"]  # Required (NO FALLBACKS)
                            logger.warning(f"⚠️ No suitable SHORT stop level found. Entry: ${entry_price:.2f}, Min distance: ${min_stop_distance:.2f}, Max reasonable: ${max_reasonable_distance:.2f}")
                            logger.warning(f"⚠️ Available resistances above entry: {len(resistances)}")
                            if resistances:
                                distances = [r["price_level"] - entry_price for r in resistances]  # Required (NO FALLBACKS)
                                strengths = [r["strength_score"] for r in resistances]  # Required (NO FALLBACKS)
                                logger.warning(f"⚠️ Resistance distances from entry: {[f'${d:.2f}' for d in distances[:5]]}")
                                logger.warning(f"⚠️ Resistance strengths: {[f'{s:.1f}' for s in strengths[:5]]}")
                        raise ValueError(f"No suitable S/R level found for {direction} stop placement (min_distance: ${min_stop_distance:.2f}, max_reasonable: ${max_reasonable_distance:.2f}) (NO FALLBACKS)")
            except Exception as e:
                logger.error(f"❌ Failed to calculate stop from S/R levels: {e}")
                raise
            
            # 2. Calculate unified stop loss (delegated to RiskManager)
            # Include leverage for liquidation price capping
            # NO FALLBACKS - leverage must be in config or TradingConfig
            from config.config import TradingConfig
            if "max_leverage" in config:
                leverage = config["max_leverage"]
            else:
                leverage = TradingConfig.LEVERAGE  # Use default from TradingConfig (this is OK - it's a system default, not a fallback)
            
            stop_loss = RiskManager.calculate_stop_loss(
                entry_price=entry_price,
                direction=direction,
                sr_stop_level=sr_stop_level,
                atr_5m=atr_5m,
                current_price=current_price,
                config=config,
                unified_data=unified_data,
                leverage=leverage
            )
            
            # Get spread for realistic profit calculations - Required (NO FALLBACKS)
            orderbook_data = self._require_key(unified_data, "orderbook_analysis", "unified_data structure")
            bid_ask_spread = self._require_key(orderbook_data, "bid_ask_spread", "orderbook_analysis structure")
            spread_pct = self._require_key(bid_ask_spread, "percentage", "bid_ask_spread structure")
            logger.debug(f"📊 Using actual spread: {spread_pct:.3f}%")
            
            # 3. Calculate adaptive take profit at next S/R level (delegated to RiskManager)
            # NOW WITH SPREAD COSTS (FIXED 2026-01-12)
            take_profit = RiskManager.calculate_take_profit(
                entry_price=entry_price,
                stop_loss=stop_loss,
                direction=direction,
                atr_5m=atr_5m,
                config=config,
                sr_levels=all_levels,  # Pass all levels for adaptive TP selection
                strategy=strategy,
                spread_pct=spread_pct  # Pass spread for realistic profit calculation
            )
            
            # 4. Validate risk/reward ratio (delegated to RiskManager)
            min_risk_reward = config["min_rr"] if "min_rr" in config else 1.5  # Strategy config uses min_rr
            risk_reward_ratio, is_valid = RiskManager.validate_risk_reward(
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                direction=direction,
                min_risk_reward=min_risk_reward
            )
            
            # Calculate risk/reward percentages for confidence system
            if direction == "LONG":
                risk_distance = entry_price - stop_loss
                reward_distance = take_profit - entry_price
            else:  # SHORT
                risk_distance = stop_loss - entry_price
                reward_distance = entry_price - take_profit
            
            stop_loss_pct = (risk_distance / entry_price) * 100.0 if entry_price > 0 else 0.0
            take_profit_pct = (reward_distance / entry_price) * 100.0 if entry_price > 0 else 0.0
            
            # Calculate distance to nearest psych level for ML features (exposed but not used yet)
            stop_distance_to_nearest_psych_pct = None
            sr_data = unified_data.get("support_resistance", {})
            all_levels = sr_data.get("levels", [])
            psych_levels = [l for l in all_levels if l.get("source") == "psych"]
            
            if psych_levels and current_price > 0:
                nearest_psych = min(psych_levels, key=lambda l: abs(l["price_level"] - stop_loss))
                stop_distance_to_nearest_psych_pct = abs(stop_loss - nearest_psych["price_level"]) / current_price
            
            # Note: ML features (stop_distance_to_nearest_psych_pct, entry_distance_to_nearest_psych_pct)
            # are calculated but not yet used in confidence/prediction
            # They will be available in prediction breakdown for future ML training
            
            return stop_loss, take_profit, risk_reward_ratio, stop_loss_pct, take_profit_pct
            
        except Exception as e:
            logger.error(f"❌ Stop/Target calculation failed: {e}")
            raise