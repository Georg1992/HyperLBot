#!/usr/bin/env python3
"""
Base decision engine – shared pipeline for PredictionEngine and ReactiveEngine.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from .models import (
    DecisionContext,
    DirectionResult,
    EntryResult,
    RiskResult,
    DecisionResult,
    default_feature_vector,
    validate_feature_schema,
)


class BaseDecisionEngine(ABC):
    """
    Base pipeline: build_context -> compute_direction -> compute_entry -> compute_sl_tp
    -> build_feature_vector -> build_result.
    Engines override compute_direction, compute_entry, compute_sl_tp (and optionally
    build_feature_vector). build_result is shared; always sets confidence=None,
    executable=False, execution_gate_reason.
    """

    @abstractmethod
    def engine_type(self) -> str:
        """'prediction' or 'reaction'."""
        pass

    @abstractmethod
    def entry_type(self) -> str:
        """'limit' or 'market'."""
        pass

    def build_context(
        self,
        unified_data: Dict[str, Any],
        strategy_used_by_engine: str,
    ) -> DecisionContext:
        """Build DecisionContext from unified_data and strategy."""
        current_price = float(unified_data.get("current_price", 0.0) or 0.0)
        timestamp = float(unified_data.get("timestamp", 0.0) or 0.0)
        sr = unified_data.get("support_resistance") or {}
        meta = sr.get("metadata") or {}
        atr_5m = float(meta.get("atr_5m", 0.0) or 0.0)
        atr_pct = (atr_5m / current_price) if current_price > 0 else 0.0
        state_strategy = unified_data.get("state_strategy", strategy_used_by_engine)
        prediction_strategy = unified_data.get("prediction_strategy", strategy_used_by_engine)
        return DecisionContext(
            unified_data=unified_data,
            strategy_used_by_engine=strategy_used_by_engine,
            current_price=current_price,
            atr_5m=atr_5m,
            atr_pct=atr_pct,
            state_strategy=state_strategy,
            prediction_strategy=prediction_strategy,
            timestamp=timestamp,
        )

    @abstractmethod
    def compute_direction(self, context: DecisionContext) -> DirectionResult:
        """Compute direction (and for reaction: best candidate)."""
        pass

    @abstractmethod
    def compute_entry(
        self,
        context: DecisionContext,
        direction: DirectionResult,
    ) -> EntryResult:
        """Compute best entry (limit or market)."""
        pass

    @abstractmethod
    def compute_sl_tp(
        self,
        context: DecisionContext,
        entry: EntryResult,
    ) -> RiskResult:
        """Compute stop loss, take profit, R:R."""
        pass

    def build_feature_vector(
        self,
        context: DecisionContext,
        direction: DirectionResult,
        entry: EntryResult,
        risk: RiskResult,
    ) -> Dict[str, Any]:
        """Build feature vector; override to add engine-specific values."""
        fv = default_feature_vector()
        fv["timestamp"] = context.timestamp
        fv["long_score"] = direction.long_score
        fv["short_score"] = direction.short_score
        fv["score_diff"] = direction.score_diff
        if self.engine_type() == "prediction":
            fv["engine_prediction"] = 1.0
            fv["engine_reaction"] = 0.0
            fv["entry_limit"] = 1.0
            fv["entry_market"] = 0.0
        else:
            fv["engine_prediction"] = 0.0
            fv["engine_reaction"] = 1.0
            fv["entry_limit"] = 0.0
            fv["entry_market"] = 1.0
        return fv

    def _timing_from_iv_squeeze(self, iv_squeeze: Any) -> tuple:
        """Compute (timing_score, timing_reason) from iv_squeeze. No gate."""
        if not iv_squeeze or not isinstance(iv_squeeze, dict):
            return 0.0, "no_squeeze"
        strength = float(iv_squeeze.get("squeeze_strength") or 0.0)
        if iv_squeeze.get("squeeze_released"):
            return min(1.0, strength), "squeeze_release"
        if iv_squeeze.get("is_squeeze"):
            return strength * 0.5, "volatility_compression"
        return 0.0, "no_squeeze"

    def build_result(
        self,
        context: DecisionContext,
        direction: DirectionResult,
        entry: EntryResult,
        risk: RiskResult,
        feature_vector: Dict[str, Any],
    ) -> DecisionResult:
        """Build DecisionResult. Always confidence=None, executable=False."""
        validate_feature_schema(feature_vector)
        breakdown = {**(entry.breakdown or {}), "entry_score": entry.entry_score}
        if direction.breakdown_direction:
            breakdown = {**breakdown, **direction.breakdown_direction}
        iv = context.unified_data.get("iv_squeeze")
        timing_score, timing_reason = self._timing_from_iv_squeeze(iv)
        return DecisionResult(
            engine_type=self.engine_type(),
            entry_type=self.entry_type(),
            setup_type=entry.setup_type,
            state_strategy=context.state_strategy,
            prediction_strategy=context.prediction_strategy,
            strategy_used_by_engine=context.strategy_used_by_engine,
            direction=entry.direction,
            entry_price=entry.entry_price,
            stop_loss=risk.stop_loss,
            take_profit=risk.take_profit,
            rr_ratio=risk.rr_ratio,
            long_score=direction.long_score,
            short_score=direction.short_score,
            score_diff=direction.score_diff,
            confidence=None,
            executable=False,
            execution_gate_reason="confidence_not_implemented",
            breakdown=breakdown,
            feature_vector=feature_vector,
            timestamp=context.timestamp,
            reasoning=entry.reasoning or direction.reasoning,
            timing_score=timing_score,
            timing_reason=timing_reason,
        )

    def run(
        self,
        unified_data: Dict[str, Any],
        strategy_used_by_engine: str,
    ) -> DecisionResult:
        """Full pipeline: context -> direction -> entry -> risk -> fv -> result."""
        context = self.build_context(unified_data, strategy_used_by_engine)
        direction = self.compute_direction(context)
        entry = self.compute_entry(context, direction)
        risk = self.compute_sl_tp(context, entry)
        fv = self.build_feature_vector(context, direction, entry, risk)
        from core.ml.confidence_service import predict as confidence_predict
        confidence_predict(fv)  # no-op for now; both engines call, keep confidence=None
        return self.build_result(context, direction, entry, risk, fv)
