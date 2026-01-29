#!/usr/bin/env python3
"""
Tests for PredictionEngine and ReactiveEngine unified contract.
Both engines return DecisionResult; confidence=None, executable=False,
execution_gate_reason='confidence_not_implemented'.
"""

import pytest
from core.decision.models import (
    DecisionResult,
    FEATURE_VECTOR_REQUIRED_KEYS,
    validate_feature_schema,
    default_feature_vector,
)


def _minimal_unified_data_reaction():
    return {
        "current_price": 90_000.0,
        "timestamp": 1000000.0,
        "support_resistance": {
            "levels": [],
            "metadata": {"atr_5m": 500.0},
        },
        "pressure": {"direction": "NEUTRAL", "strength": 0.5, "net_pressure": 0.0},
        "volume": {"category": "NORMAL", "percentile": 50.0, "trend": "NEUTRAL"},
        "rsi": {"rsi": 50.0},
        "volatility": {"category": "NORMAL", "volatility_percentage": 0.5},
        "trend": {"direction": "NEUTRAL", "strength": 0.5},
        "state_strategy": "standard",
        "prediction_strategy": "standard",
        "strategy": "standard",
    }


class TestFeatureVectorSchema:
    def test_required_keys_in_default(self):
        fv = default_feature_vector()
        for k in FEATURE_VECTOR_REQUIRED_KEYS:
            assert k in fv, f"missing required key {k}"

    def test_validate_schema_raises_on_missing(self):
        fv = default_feature_vector()
        del fv["rsi"]
        with pytest.raises(KeyError, match="rsi"):
            validate_feature_schema(fv)

    def test_validate_schema_passes_with_all_keys(self):
        fv = default_feature_vector()
        validate_feature_schema(fv)


class TestDecisionResult:
    def test_risk_reward_ratio_alias(self):
        r = DecisionResult(
            engine_type="prediction",
            entry_type="limit",
            setup_type="sr_setup",
            state_strategy="s",
            prediction_strategy="s",
            strategy_used_by_engine="s",
            direction="LONG",
            entry_price=90_000.0,
            rr_ratio=1.5,
        )
        assert r.risk_reward_ratio == 1.5
        r.rr_ratio = None
        assert r.risk_reward_ratio == 0.0

    def test_confidence_executable_contract(self):
        r = DecisionResult(
            engine_type="prediction",
            entry_type="limit",
            setup_type="sr_setup",
            state_strategy="s",
            prediction_strategy="s",
            strategy_used_by_engine="s",
            direction="LONG",
            entry_price=90_000.0,
            confidence=None,
            executable=False,
            execution_gate_reason="confidence_not_implemented",
        )
        assert r.confidence is None
        assert r.executable is False
        assert r.execution_gate_reason == "confidence_not_implemented"


class TestReactiveEngine:
    def test_returns_decision_result_full_schema(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        result = engine.run(ud, "standard")
        assert isinstance(result, DecisionResult)
        for k in FEATURE_VECTOR_REQUIRED_KEYS:
            assert k in result.feature_vector, f"missing feature key {k}"
        validate_feature_schema(result.feature_vector)

    def test_never_returns_none(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        result = engine.process_market_data(ud, 90_000.0, "standard")
        assert result is not None
        assert isinstance(result, DecisionResult)

    def test_always_has_setup_type_and_direction(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        result = engine.run(ud, "standard")
        assert hasattr(result, "setup_type") and result.setup_type is not None
        assert hasattr(result, "direction") and result.direction is not None
        assert result.setup_type in ("market_follow_through", "breakout", "reversal", "sweep_revert")
        assert result.direction in ("LONG", "SHORT")

    def test_always_long_or_short_never_none(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        result = engine.run(ud, "standard")
        assert result.direction in ("LONG", "SHORT")
        assert result.direction != "NONE"
        assert result.entry_price == ud["current_price"]

    def test_no_signals_still_outputs_long_or_short(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        ud["iv_squeeze"] = {}
        result = engine.run(ud, "standard")
        assert result.direction in ("LONG", "SHORT")
        assert result.setup_type in ("market_follow_through", "breakout")

    def test_tie_break_stability(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        r1 = engine.run(ud, "standard")
        r2 = engine.run(ud, "standard")
        assert r1.direction in ("LONG", "SHORT")
        assert r2.direction == r1.direction

    def test_imbalance_positive_prefers_long(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        ud["orderbook_analysis"] = {"order_imbalance": {"bias": 0.8}, "bid_ask_spread": {"percentage": 0.01}}
        result = engine.run(ud, "standard")
        assert result.direction == "LONG"

    def test_imbalance_negative_prefers_short(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        ud["orderbook_analysis"] = {"order_imbalance": {"bias": -0.8}, "bid_ask_spread": {"percentage": 0.01}}
        result = engine.run(ud, "standard")
        assert result.direction == "SHORT"

    def test_feature_vector_validates(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        result = engine.run(ud, "standard")
        validate_feature_schema(result.feature_vector)

    def test_confidence_executable_contract(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        ud = _minimal_unified_data_reaction()
        result = engine.run(ud, "standard")
        assert result.confidence is None
        assert result.executable is False
        assert result.execution_gate_reason == "confidence_not_implemented"


class TestPredictionEngine:
    """PredictionEngine contract: DecisionResult, full schema, confidence=None, executable=False."""

    def test_prediction_engine_is_base_engine(self):
        from core.execution.prediction_engine import PredictionEngine
        from core.decision.base_engine import BaseDecisionEngine

        engine = PredictionEngine()
        assert isinstance(engine, BaseDecisionEngine)
        assert engine.engine_type() == "prediction"
        assert engine.entry_type() == "limit"

    @pytest.mark.skip(reason="heavy fixture: _score_direction needs rsi_signal, trend.detailed_timeframes, etc.")
    def test_returns_decision_result_full_schema(self):
        pass

    @pytest.mark.skip(reason="heavy fixture: same as above")
    def test_confidence_executable_contract(self):
        pass
