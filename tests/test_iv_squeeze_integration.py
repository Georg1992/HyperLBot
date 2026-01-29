#!/usr/bin/env python3
"""
Tests for IV Squeeze timing-only integration.
- release_timestamp, FeatureVector ivs_*, ReactiveEngine boost, timing_score, determinism.
"""

import pytest
from core.decision.models import (
    FEATURE_VECTOR_REQUIRED_KEYS,
    default_feature_vector,
    fill_ivs_feature_vector,
    validate_feature_schema,
)


def _minimal_unified():
    return {
        "current_price": 90_000.0,
        "timestamp": 1000000.0,
        "support_resistance": {"levels": [], "metadata": {"atr_5m": 500.0}},
        "pressure": {"direction": "NEUTRAL", "strength": 0.5, "net_pressure": 0.0},
        "volume": {"category": "NORMAL", "percentile": 50.0, "trend": "NEUTRAL"},
        "rsi": {"rsi": 50.0},
        "volatility": {"category": "NORMAL", "volatility_percentage": 0.5},
        "trend": {"direction": "NEUTRAL", "strength": 0.5},
        "state_strategy": "standard",
        "prediction_strategy": "standard",
        "strategy": "standard",
    }


def test_ivs_keys_in_schema():
    for k in ("ivs_is_squeeze", "ivs_strength", "ivs_duration_minutes", "ivs_released", "ivs_release_age_minutes"):
        assert k in FEATURE_VECTOR_REQUIRED_KEYS, k
    fv = default_feature_vector()
    for k in FEATURE_VECTOR_REQUIRED_KEYS:
        assert k in fv, k


def test_fill_ivs_missing_non_strict():
    ud = _minimal_unified()
    ud.pop("timestamp", None)
    ud["timestamp"] = 1000000.0
    fv = default_feature_vector()
    fill_ivs_feature_vector(fv, ud, strict_ivs=False)
    assert fv["ivs_is_squeeze"] == 0
    assert fv["ivs_strength"] == 0.0
    assert fv["ivs_duration_minutes"] == 0.0
    assert fv["ivs_released"] == 0
    assert fv["ivs_release_age_minutes"] == 0.0


def test_fill_ivs_missing_strict_raises():
    ud = _minimal_unified()
    fv = default_feature_vector()
    with pytest.raises(KeyError, match="iv_squeeze"):
        fill_ivs_feature_vector(fv, ud, strict_ivs=True)


def test_fill_ivs_released():
    ud = _minimal_unified()
    ud["iv_squeeze"] = {
        "is_squeeze": False,
        "squeeze_strength": 0.8,
        "duration_minutes": 0.0,
        "squeeze_released": True,
        "release_timestamp": 999000.0,
    }
    ud["timestamp"] = 1000000.0
    fv = default_feature_vector()
    fill_ivs_feature_vector(fv, ud, strict_ivs=False)
    assert fv["ivs_is_squeeze"] == 0
    assert fv["ivs_strength"] == 0.8
    assert fv["ivs_released"] == 1
    assert fv["ivs_release_age_minutes"] == pytest.approx(1000.0 / 60.0, rel=1e-6)


def test_fill_ivs_deterministic():
    ud = _minimal_unified()
    ud["iv_squeeze"] = {"is_squeeze": True, "squeeze_strength": 0.5, "duration_minutes": 2.0, "squeeze_released": False, "release_timestamp": None}
    ud["timestamp"] = 1000000.0
    fv1 = default_feature_vector()
    fv2 = default_feature_vector()
    fill_ivs_feature_vector(fv1, ud, strict_ivs=False)
    fill_ivs_feature_vector(fv2, ud, strict_ivs=False)
    for k in ("ivs_is_squeeze", "ivs_strength", "ivs_duration_minutes", "ivs_released", "ivs_release_age_minutes"):
        assert fv1[k] == fv2[k], k


def test_reactive_engine_breakout_boost_when_squeeze_released():
    from core.execution.reactive_engine import ReactiveEngine
    from core.decision.models import DecisionContext

    ud = _minimal_unified()
    ud["iv_squeeze"] = {
        "is_squeeze": False,
        "squeeze_strength": 0.7,
        "duration_minutes": 0.0,
        "squeeze_released": True,
        "release_timestamp": 999000.0,
    }
    engine = ReactiveEngine()
    ctx = engine.build_context(ud, "standard")
    candidates = engine._generate_reaction_candidates(ctx)
    breakout_long = next(c for c in candidates if c["setup_type"] == "breakout" and c["direction"] == "LONG")
    boost = engine._squeeze_timing_boost(breakout_long, ctx)
    assert boost > 0
    none_c = next(c for c in candidates if c["setup_type"] == "none")
    assert engine._squeeze_timing_boost(none_c, ctx) == 0.0


def test_reactive_engine_no_boost_when_not_released():
    from core.execution.reactive_engine import ReactiveEngine

    ud = _minimal_unified()
    ud["iv_squeeze"] = {"is_squeeze": True, "squeeze_strength": 0.5, "duration_minutes": 2.0, "squeeze_released": False, "release_timestamp": None}
    engine = ReactiveEngine()
    ctx = engine.build_context(ud, "standard")
    candidates = engine._generate_reaction_candidates(ctx)
    breakout = next(c for c in candidates if c["setup_type"] == "breakout" and c["direction"] == "LONG")
    assert engine._squeeze_timing_boost(breakout, ctx) == 0.0


def test_prediction_engine_iv_squeeze_only_in_feature_vector():
    from pathlib import Path

    path = Path("core/execution/prediction_engine.py")
    lines = path.read_text().splitlines()
    assert any("fill_ivs_feature_vector" in ln for ln in lines)
    assert any("fill_ivs_feature_vector" in ln for ln in lines[140:200])  # in build_feature_vector
    for i in range(1779, min(3100, len(lines))):
        assert "iv_squeeze" not in lines[i] and "fill_ivs" not in lines[i], (
            f"direction/entry logic must not use iv_squeeze/fill_ivs (line {i+1})"
        )
