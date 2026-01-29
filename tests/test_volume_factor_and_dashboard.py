#!/usr/bin/env python3
"""
Tests for volume factor (active when volume exists) and dashboard always showing
reaction/prediction.
"""

import pytest


def _minimal_ud():
    return {
        "current_price": 90_000.0,
        "timestamp": 1000000.0,
        "support_resistance": {"levels": [], "metadata": {"atr_5m": 500.0}},
        "pressure": {"direction": "NEUTRAL", "strength": 0.5, "net_pressure": 0.0},
        "volume": {
            "category": "NORMAL",
            "percentile": 50.0,
            "trend": "NEUTRAL",
            "volume_trend_strength": 0.0,
            "volume_anomaly": {"is_anomaly": False, "severity": "NORMAL"},
        },
        "volume_category": "NORMAL",
        "rsi": {"rsi": 50.0, "rsi_trend": "NEUTRAL", "rsi_signal": "NEUTRAL", "rsi_momentum": 0.0},
        "volatility": {"category": "NORMAL", "volatility_percentage": 0.5},
        "trend": {
            "direction": "NEUTRAL",
            "strength": 0.5,
            "detailed_timeframes": {"trend_15m": "SIDEWAYS", "trend_1h": "SIDEWAYS", "trend_4h": "SIDEWAYS", "trend_24h": "SIDEWAYS"},
        },
        "patterns": {"patterns": [], "patterns_nested": {"reversal_patterns": [], "continuation_patterns": [], "triangle_patterns": [], "channel_patterns": [], "wedge_patterns": [], "trend_patterns": [], "candlestick_patterns": []}, "overall_quality": 0.0},
        "market_conditions": {"condition": "FAIR", "risk_level": "MODERATE", "sentiment_data": {"value": 50}},
        "cross_asset_analysis": {},
        "state_strategy": "standard",
        "prediction_strategy": "standard",
        "strategy": "standard",
    }


class TestVolumeFactor:
    """Volume factor stays active when volume exists; no missing_data from volume."""

    def test_score_volume_factor_minimal_keys_no_raise(self):
        from core.execution.prediction_engine import PredictionEngine

        eng = PredictionEngine()
        # Minimal volume_data as might come from cache; missing trend_strength/anomaly
        volume_data = {"category": "NORMAL", "trend": "NEUTRAL"}
        vol_long, vol_short, reasons = eng._score_volume_factor(volume_data, "NORMAL")
        assert isinstance(vol_long, (int, float))
        assert isinstance(vol_short, (int, float))
        assert isinstance(reasons, list)

    def test_score_volume_factor_very_low_returns_penalty(self):
        from core.execution.prediction_engine import PredictionEngine

        eng = PredictionEngine()
        volume_data = {
            "volume_trend_strength": 0.0,
            "trend": "NEUTRAL",
            "volume_anomaly": {"is_anomaly": False, "severity": "NORMAL"},
        }
        vol_long, vol_short, reasons = eng._score_volume_factor(volume_data, "VERY_LOW")
        assert vol_long < 0 and vol_short < 0
        assert any("Low volume" in r for r in reasons)

    def test_direction_volume_active_when_volume_exists(self):
        """When unified_data has volume (as in real sessions), volume factor is active, not missing_data."""
        from core.execution.prediction_engine import PredictionEngine

        eng = PredictionEngine()
        ud = _minimal_ud()
        dr = eng._score_direction(ud, "standard")
        assert "breakdown_direction" in dr
        inactive = dr["breakdown_direction"].get("inactive_factors") or {}
        assert "volume" not in inactive, (
            "volume should be active when unified_data has volume; got inactive_factors=%s" % inactive
        )


class TestDashboardReactionPrediction:
    """Dashboard always exposes reaction and prediction when provided; no filtering by executable."""

    def test_dashboard_includes_reaction_when_provided(self):
        from unittest.mock import MagicMock
        from core.services.dashboard_service import DashboardService

        mock_h = MagicMock()
        mock_h.prepare_chart_data.return_value = {"candles": [], "ongoing": {}}
        svc = DashboardService(historical_service=mock_h)
        market = {
            "current_price": 90_000.0,
            "patterns": {},
            "prediction": {"direction": "LONG", "entry_price": 90_000.0, "executable": False, "confidence": None},
            "reaction": {
                "direction": "LONG",
                "setup_type": "market_follow_through",
                "entry_price": 90_000.0,
                "executable": False,
                "confidence": None,
            },
        }
        svc.update_market_data(market)
        data = svc.get_data()
        assert "reaction" in data
        assert data["reaction"] is not None
        assert data["reaction"].get("direction") == "LONG"
        assert "prediction" in data
        assert data["prediction"] is not None
        assert data["prediction"].get("direction") == "LONG"
