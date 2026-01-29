#!/usr/bin/env python3
"""Tests for MomentumProcessor: always-emit reaction, always LONG or SHORT."""

import pytest
from core.services.momentum_processor import MomentumProcessor, build_stub_reaction


def _minimal_unified_data():
    return {
        "current_price": 90_000.0,
        "timestamp": 1000000.0,
        "strategy": "standard",
        "prediction_strategy": "standard",
    }


class TestBuildStubReaction:
    def test_stub_always_long(self):
        ud = _minimal_unified_data()
        stub = build_stub_reaction(ud, 90_000.0, "standard", "no_reaction")
        assert stub["direction"] == "LONG"
        assert stub["setup_type"] == "market_follow_through"
        assert stub["entry_price"] == 90_000.0
        assert stub["confidence"] is None
        assert stub["executable"] is False
        assert stub["status"] == "NOT_EXECUTABLE"
        assert stub["strategy"] == "standard"
        assert stub["candidate_score"] == 0.0
        assert "breakdown" in stub and "reason" in stub["breakdown"]
        assert "reasoning" in stub
        assert stub["engine_type"] == "reaction"
        assert stub["entry_type"] == "market"

    def test_stub_reason_varies(self):
        ud = _minimal_unified_data()
        r = build_stub_reaction(ud, 1.0, "std", "no_reaction")
        assert "No reaction available" in r["reasoning"]
        r2 = build_stub_reaction(ud, 1.0, "std", "engine_unavailable")
        assert "engine_unavailable" in r2["reasoning"]


class TestMomentumProcessorAlwaysEmits:
    def test_no_engine_sets_stub(self):
        mp = MomentumProcessor(reactive_engine=None)
        ud = _minimal_unified_data()
        out = mp.process_momentum_signals(ud, 90_000.0, "standard")
        assert "reaction" in ud
        assert ud["reaction"] is out
        assert out["direction"] in ("LONG", "SHORT")
        assert out["status"] == "NOT_EXECUTABLE"

    def test_with_engine_always_long_or_short(self):
        from core.execution.reactive_engine import ReactiveEngine

        engine = ReactiveEngine()
        mp = MomentumProcessor(reactive_engine=engine)
        ud = _minimal_unified_data()
        ud["support_resistance"] = {"levels": [], "metadata": {"atr_5m": 500.0}}
        ud["pressure"] = {"direction": "NEUTRAL", "strength": 0.5, "net_pressure": 0.0}
        ud["volume"] = {"category": "NORMAL", "percentile": 50.0, "trend": "NEUTRAL"}
        ud["rsi"] = {"rsi": 50.0}
        ud["volatility"] = {"category": "NORMAL", "volatility_percentage": 0.5}
        ud["trend"] = {"direction": "NEUTRAL", "strength": 0.5}
        ud["state_strategy"] = ud["prediction_strategy"] = "standard"
        out = mp.process_momentum_signals(ud, 90_000.0, "standard")
        assert "reaction" in ud
        assert ud["reaction"] is out
        assert out["direction"] in ("LONG", "SHORT")
        assert out["direction"] != "NONE"
        assert "status" in out
        assert "strategy" in out
        assert "candidate_score" in out
        assert "breakdown" in out
