#!/usr/bin/env python3
"""Tests for 5m volatility pipeline: spike detection, adaptive blending, classification, determinism."""

import copy
import pytest
from config.config import TradingConfig

from core.calculations.volatility_analyzer import VolatilityAnalyzer
from core.calculations.volatility_classifier import VolatilityClassifier
from core.calculations.volatility_calculator import VolatilityCalculator


def _candle(high: float, low: float, close: float) -> dict:
    return {"high": high, "low": low, "close": close}


def _make_candles(n: int, base: float = 90_000.0, range_pct: float = 0.002) -> list:
    """n candles with fixed range% around base."""
    out = []
    for i in range(n):
        r = base * range_pct * 0.5
        low = base - r + (i * 0.00001 * base)
        high = low + base * range_pct
        close = (high + low) / 2
        out.append(_candle(high, low, close))
    return out


class _MockVolatilityDataProvider:
    """Minimal provider for calculate_candle_volatility; no fetch."""

    def calculate_basic_volatility(self, candles: list, period_minutes: int = 15) -> dict:
        n = max(1, period_minutes // 5)
        recent = candles[-n:] if len(candles) >= n else candles
        if not recent:
            return {"volatility": 0.0, "range": 0.0, "avg_price": 0.0}
        highs = [c["high"] for c in recent if c.get("high", 0) > 0]
        lows = [c["low"] for c in recent if c.get("low", 0) > 0]
        closes = [c["close"] for c in recent if c.get("close", 0) > 0]
        if not highs or not lows or not closes:
            return {"volatility": 0.0, "range": 0.0, "avg_price": 0.0}
        r = max(highs) - min(lows)
        avg = sum(closes) / len(closes)
        vol = r / avg if avg > 0 else 0.0
        return {"volatility": vol, "range": r, "avg_price": avg}


class TestVolatilityBlending:
    """Blend weights from ratio tiers."""

    def test_ratio_base_weight(self):
        cfg = TradingConfig
        w_base = float(getattr(cfg, "VOL_BLEND_W_BASE", 0.65))
        analyzer = VolatilityAnalyzer()
        basic, weighted, current = 0.002, 0.002, 0.002
        baseline = max(weighted, basic, 1e-12)
        ratio = current / baseline
        assert ratio >= 1.0 - 1e-9 and ratio <= 1.0 + 1e-9
        primary, _, r = analyzer.calculate_primary_volatility(
            basic, weighted, current, False, "NONE"
        )
        assert r >= 1.0 - 1e-9 and r <= 1.0 + 1e-9
        expected = w_base * current + (1.0 - w_base) * weighted
        expected = max(expected, basic)
        assert abs(primary - expected) < 1e-9

    def test_ratio_high_weight(self):
        w_high = float(getattr(TradingConfig, "VOL_BLEND_W_HIGH", 0.85))
        analyzer = VolatilityAnalyzer()
        basic, weighted = 0.001, 0.001
        current = 0.0016
        baseline = max(weighted, basic, 1e-12)
        ratio = current / baseline
        assert 1.5 <= ratio < 2.5
        primary, _, _ = analyzer.calculate_primary_volatility(
            basic, weighted, current, False, "NONE"
        )
        expected = w_high * current + (1.0 - w_high) * weighted
        expected = max(expected, basic)
        assert abs(primary - expected) < 1e-9

    def test_ratio_strong_weight(self):
        w_strong = float(getattr(TradingConfig, "VOL_BLEND_W_STRONG", 0.95))
        analyzer = VolatilityAnalyzer()
        basic, weighted = 0.001, 0.001
        current = 0.003
        baseline = max(weighted, basic, 1e-12)
        ratio = current / baseline
        assert ratio >= 2.5
        primary, _, _ = analyzer.calculate_primary_volatility(
            basic, weighted, current, False, "NONE"
        )
        expected = w_strong * current + (1.0 - w_strong) * weighted
        expected = max(expected, basic)
        assert abs(primary - expected) < 1e-9


class TestVolatilitySpikeDetection:
    """Relative and absolute spike rules."""

    def test_relative_spike_triggers(self):
        analyzer = VolatilityAnalyzer()
        mult = float(getattr(TradingConfig, "VOL_SPIKE_MULTIPLIER_5M", 2.0))
        weighted, basic = 0.005, 0.004
        current = weighted * mult + 0.0001
        out = analyzer.detect_volatility_spikes(current, weighted, basic)
        assert out["is_spike"] is True
        assert out["spike_intensity"] in ("MODERATE", "HIGH", "EXTREME")

    def test_absolute_spike_triggers_when_weighted_tiny(self):
        analyzer = VolatilityAnalyzer()
        abs_thresh = float(getattr(TradingConfig, "VOL_ABS_SPIKE_THRESHOLD_5M", 0.010))
        weighted, basic = 0.006, 0.005
        current = abs_thresh + 0.0001
        assert current < weighted * 2.0
        out = analyzer.detect_volatility_spikes(current, weighted, basic)
        assert out["is_spike"] is True

    def test_no_spike_when_below_both(self):
        analyzer = VolatilityAnalyzer()
        weighted, basic = 0.003, 0.003
        current = 0.004
        out = analyzer.detect_volatility_spikes(current, weighted, basic)
        assert current < 0.01 and current < weighted * 2.0
        assert out["is_spike"] is False
        assert out["spike_intensity"] == "NONE"


class TestVolatilityClassification:
    """Config-driven thresholds at boundaries."""

    def test_low_mod_boundary(self):
        cl = VolatilityClassifier()
        low_max = float(getattr(TradingConfig, "VOL_LVL_LOW_MAX", 0.0015))
        mod_max = float(getattr(TradingConfig, "VOL_LVL_MOD_MAX", 0.0030))
        assert cl.classify_volatility_level(low_max)["level"] == "LOW"
        assert cl.classify_volatility_level(low_max + 1e-9)["level"] == "MODERATE"
        assert cl.classify_volatility_level(mod_max)["level"] == "MODERATE"

    def test_mod_high_boundary(self):
        cl = VolatilityClassifier()
        mod_max = float(getattr(TradingConfig, "VOL_LVL_MOD_MAX", 0.0030))
        high_max = float(getattr(TradingConfig, "VOL_LVL_HIGH_MAX", 0.0060))
        assert cl.classify_volatility_level(mod_max + 1e-9)["level"] == "HIGH"
        assert cl.classify_volatility_level(high_max)["level"] == "HIGH"

    def test_high_extreme_boundary(self):
        cl = VolatilityClassifier()
        high_max = float(getattr(TradingConfig, "VOL_LVL_HIGH_MAX", 0.0060))
        assert cl.classify_volatility_level(high_max + 1e-9)["level"] == "EXTREME"

    def test_classifier_thresholds_match_config(self):
        """Classifier uses TradingConfig VOL_LVL_* only (single source of truth)."""
        cl = VolatilityClassifier()
        low_max = float(getattr(TradingConfig, "VOL_LVL_LOW_MAX", 0.0015))
        mod_max = float(getattr(TradingConfig, "VOL_LVL_MOD_MAX", 0.0030))
        high_max = float(getattr(TradingConfig, "VOL_LVL_HIGH_MAX", 0.0060))
        out = cl.classify_volatility_level(0.002)
        t = out["thresholds"]
        assert t["LOW_MAX"] == low_max
        assert t["MOD_MAX"] == mod_max
        assert t["HIGH_MAX"] == high_max


class TestVolatilityDeterminism:
    """Same input => same output."""

    def test_same_candles_same_result(self):
        mock_dp = _MockVolatilityDataProvider()
        calc = VolatilityCalculator(symbol="BTC", data_provider=mock_dp)
        candles = _make_candles(20, base=90_000.0, range_pct=0.002)
        r1 = calc.calculate_candle_volatility(candles, "5m", "standard")
        r2 = calc.calculate_candle_volatility(candles, "5m", "standard")
        assert r1["volatility_5m"] == r2["volatility_5m"]
        assert r1["volatility_category"] == r2["volatility_category"]
        assert r1["spike_intensity"] == r2["spike_intensity"]

    def test_output_keys_unchanged(self):
        mock_dp = _MockVolatilityDataProvider()
        calc = VolatilityCalculator(symbol="BTC", data_provider=mock_dp)
        candles = _make_candles(20)
        out = calc.calculate_candle_volatility(candles, "5m", "standard")
        for k in ("volatility", "volatility_5m", "volatility_percentage", "level",
                  "category", "volatility_category", "spike_intensity"):
            assert k in out
        assert out["volatility"] == out["volatility_5m"]
        assert out["volatility_percentage"] == out["volatility_5m"] * 100
        assert out["level"] in ("LOW", "MODERATE", "HIGH", "EXTREME")
        assert out["spike_intensity"] in ("NONE", "MODERATE", "HIGH", "EXTREME")


class TestVolatilityMonotonicity:
    """Increase current (fixed weighted/basic) => increase primary."""

    def test_primary_increases_with_current(self):
        mock_dp = _MockVolatilityDataProvider()
        calc = VolatilityCalculator(symbol="BTC", data_provider=mock_dp)
        base = 90_000.0
        range_pct = 0.002
        candles = _make_candles(20, base=base, range_pct=range_pct)
        primary_prev = -1.0
        for extra in (0.0, 0.0005, 0.001, 0.002):
            cand = copy.deepcopy(candles)
            c = cand[-1]
            r = base * (range_pct + extra) * 0.5
            c["low"] = c["close"] - r
            c["high"] = c["close"] + r
            out = calc.calculate_candle_volatility(cand, "5m", "standard")
            primary = out["volatility_5m"]
            assert primary >= primary_prev
            primary_prev = primary
