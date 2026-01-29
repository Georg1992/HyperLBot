#!/usr/bin/env python3
"""Tests for calibration hooks: nested reads, no silent defaults."""

import pytest

from core.ml.calibration_hooks import CalibrationHooks, _nested_get, _require_calibration_key


def test_nested_get():
    d = {"a": {"b": {"c": 1}}}
    assert _nested_get(d, ["a", "b", "c"]) == 1
    assert _nested_get(d, ["a", "b"]) == {"c": 1}
    assert _nested_get(d, ["a", "x"]) is None
    assert _nested_get(d, ["x"]) is None


def test_require_calibration_key_raises():
    with pytest.raises(ValueError, match="required key missing"):
        _require_calibration_key({}, ["x"], "test")
    with pytest.raises(ValueError, match="required key missing"):
        _require_calibration_key({"a": {}}, ["a", "b"], "test")


def test_extract_calibration_features_required():
    hooks = CalibrationHooks(db_path=":memory:")
    ud = {
        "volatility_category": "MODERATE",
        "volatility_5m": 0.002,
        "trend_direction": "BULLISH",
        "volume_category": "NORMAL",
        "rsi_value": 55.0,
    }
    features, inactive = hooks._extract_calibration_features(ud)
    assert features["volatility_category"] == "MODERATE"
    assert features["volatility_5m"] == 0.002
    assert features["trend_direction"] == "BULLISH"
    assert features["volume_category"] == "NORMAL"
    assert features["rsi_value"] == 55.0


def test_extract_calibration_features_optional_nested():
    hooks = CalibrationHooks(db_path=":memory:")
    ud = {
        "volatility_category": "LOW",
        "volatility_5m": 0.001,
        "trend_direction": "NEUTRAL",
        "volume_category": "LOW",
        "rsi_value": 50.0,
        "trend": {"strength": 0.3},
        "pressure": {"net_pressure": 0.2, "pressure_ratio": 1.1},
        "orderbook_analysis": {
            "bid_ask_spread": {"percentage": 0.02},
            "liquidity_depth": {"depth_score": 0.8},
        },
        "volatility": {"spike_intensity": "NONE"},
        "volume": {"volume_trend_strength": 0.5},
        "market_conditions": {"risk_level": "LOW"},
    }
    features, inactive = hooks._extract_calibration_features(ud)
    assert features["trend_strength"] == 0.3
    assert features["net_pressure"] == 0.2
    assert features["pressure_ratio"] == 1.1
    assert features["spread_pct"] == 0.02
    assert features["liquidity_score"] == 0.8
    assert features["spike_intensity"] == "NONE"
    assert features["volume_trend_strength"] == 0.5
    assert features["risk_level"] == "LOW"


def test_extract_calibration_features_optional_inactive():
    hooks = CalibrationHooks(db_path=":memory:")
    ud = {
        "volatility_category": "LOW",
        "volatility_5m": 0.001,
        "trend_direction": "NEUTRAL",
        "volume_category": "LOW",
        "rsi_value": 50.0,
    }
    features, inactive = hooks._extract_calibration_features(ud)
    assert "inactive_features" in features
    assert "spread_pct" in features["inactive_features"]
    assert features["inactive_features"]["spread_pct"] == "optional_missing"


def test_calibration_consecutive_failures_reset_on_success(tmp_path):
    """Successful log_prediction resets consecutive_failures to 0."""
    from unittest.mock import MagicMock
    hooks = CalibrationHooks(db_path=str(tmp_path / "cal_reset.db"))
    hooks.consecutive_failures = 3
    pred = MagicMock()
    pred.timestamp = 1000.0
    pred.strategy = "standard"
    pred.direction = "LONG"
    pred.entry_price = 50000.0
    pred.stop_loss = 49900.0
    pred.take_profit = 50100.0
    pred.confidence = None
    pred.reasoning = "test"
    ud = {
        "volatility_category": "MODERATE",
        "volatility_5m": 0.002,
        "trend_direction": "BULLISH",
        "volume_category": "NORMAL",
        "rsi_value": 55.0,
    }
    hooks.log_prediction(pred, ud, {"long_score": 0.6, "short_score": 0.4, "score_diff": 0.2}, 0.5)
    assert hooks.consecutive_failures == 0


def test_calibration_consecutive_failures_escalation():
    """Repeated required-key failures increment counter; at threshold raise RuntimeError."""
    from unittest.mock import MagicMock, patch
    from config.config import TradingConfig
    hooks = CalibrationHooks(db_path=":memory:")
    pred = MagicMock()
    pred.timestamp = 1000.0
    pred.strategy = "standard"
    pred.direction = "LONG"
    pred.entry_price = 50000.0
    pred.stop_loss = 49900.0
    pred.take_profit = 50100.0
    pred.confidence = None
    pred.reasoning = "test"
    ud_missing = {"volatility_5m": 0.002}
    with patch.object(TradingConfig, "CALIBRATION_FAILURE_THRESHOLD", 2):
        with pytest.raises(ValueError, match="required key missing"):
            hooks.log_prediction(pred, ud_missing, {"long_score": 0.5, "short_score": 0.5, "score_diff": 0.0}, 0.5)
        assert hooks.consecutive_failures == 1
        with pytest.raises(RuntimeError, match="Calibration disabled: repeated required-key failures"):
            hooks.log_prediction(pred, ud_missing, {"long_score": 0.5, "short_score": 0.5, "score_diff": 0.0}, 0.5)


def test_log_outcome_uses_prediction_timestamp_when_missing(tmp_path):
    """When outcome_timestamp is missing, use prediction timestamp from DB; never 0.0."""
    from unittest.mock import MagicMock
    import os
    db = tmp_path / "cal.db"
    hooks = CalibrationHooks(db_path=str(db))
    pred = MagicMock()
    pred.timestamp = 12345.0
    pred.strategy = "standard"
    pred.direction = "LONG"
    pred.entry_price = 50000.0
    pred.stop_loss = 49900.0
    pred.take_profit = 50100.0
    pred.confidence = None
    pred.reasoning = "test"
    ud = {
        "volatility_category": "MODERATE",
        "volatility_5m": 0.002,
        "trend_direction": "BULLISH",
        "volume_category": "NORMAL",
        "rsi_value": 55.0,
    }
    pid = hooks.log_prediction(pred, ud, {"long_score": 0.6, "short_score": 0.4, "score_diff": 0.2}, 0.5)
    out = {"hit_stop": False, "hit_target": True, "profit_pct": 0.1, "duration_seconds": 60.0, "final_price": 50100.0}
    assert hooks.log_outcome(pid, out) is True
    with hooks._get_connection() as conn:
        row = conn.execute(
            "SELECT outcome_timestamp FROM outcomes WHERE prediction_id = ?", (pid,)
        ).fetchone()
    assert row is not None
    assert row[0] == 12345.0


def test_log_outcome_raises_when_no_timestamp_available(tmp_path):
    """log_outcome raises when outcome_timestamp missing and no prediction in DB (no 0.0 fallback)."""
    hooks = CalibrationHooks(db_path=str(tmp_path / "cal2.db"))
    with pytest.raises(ValueError, match="outcome_timestamp missing and no prediction timestamp"):
        hooks.log_outcome("nonexistent_pred_id", {"hit_stop": False, "hit_target": False})
