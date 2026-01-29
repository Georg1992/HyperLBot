#!/usr/bin/env python3
"""
Volatility Analyzer Module
Handles complex volatility calculations, relative+absolute spike detection, and adaptive blending.
Deterministic; no wall-clock time.
"""

from typing import Dict, List, Any, Tuple
from loguru import logger


def _get_vol_config() -> Dict[str, float]:
    from config.config import TradingConfig
    return {
        "eps": float(getattr(TradingConfig, "VOL_EPS", 1e-12)),
        "abs_spike": float(getattr(TradingConfig, "VOL_ABS_SPIKE_THRESHOLD_5M", 0.010)),
        "spike_mult": float(getattr(TradingConfig, "VOL_SPIKE_MULTIPLIER_5M", 2.0)),
        "ratio_mod": float(getattr(TradingConfig, "VOL_SPIKE_RATIO_MODERATE", 2.0)),
        "ratio_high": float(getattr(TradingConfig, "VOL_SPIKE_RATIO_HIGH", 3.0)),
        "w_strong": float(getattr(TradingConfig, "VOL_BLEND_W_STRONG", 0.95)),
        "w_high": float(getattr(TradingConfig, "VOL_BLEND_W_HIGH", 0.85)),
        "w_med": float(getattr(TradingConfig, "VOL_BLEND_W_MED", 0.75)),
        "w_base": float(getattr(TradingConfig, "VOL_BLEND_W_BASE", 0.65)),
        "r_strong": float(getattr(TradingConfig, "VOL_BLEND_RATIO_STRONG", 2.5)),
        "r_high": float(getattr(TradingConfig, "VOL_BLEND_RATIO_HIGH", 1.5)),
        "r_med": float(getattr(TradingConfig, "VOL_BLEND_RATIO_MED", 1.1)),
    }


def _validate_vol_config(c: Dict[str, float]) -> None:
    for k, v in c.items():
        if k.startswith("w_") and (v < 0.0 or v > 1.0):
            raise ValueError(f"VOL config weight {k}={v} must be in [0,1] (NO FALLBACKS)")
    for r in ("r_strong", "r_high", "r_med", "spike_mult", "ratio_mod", "ratio_high"):
        if c[r] < 1.0:
            raise ValueError(f"VOL config ratio {r}={c[r]} must be >= 1 (NO FALLBACKS)")


class VolatilityAnalyzer:
    """
    Analyzes volatility using weighted metrics, relative+absolute spike detection,
    and adaptive blending. Deterministic.
    """

    def __init__(self):
        _validate_vol_config(_get_vol_config())
        logger.debug("📊 VolatilityAnalyzer initialized")

    def calculate_weighted_volatility(self, candles: List[Dict]) -> Dict[str, Any]:
        """
        Calculate weighted volatility with emphasis on recent candles.
        Uses last 15 candles. Deterministic.
        """
        try:
            if len(candles) < 1:
                return {"weighted_volatility": 0.0, "max_volatility": 0.0, "current_volatility": 0.0}

            recent_candles = candles[-15:] if len(candles) >= 15 else candles
            weighted_volatilities = []
            total_weight = 0.0

            for i, candle in enumerate(recent_candles):
                if candle["close"] > 0 and candle["high"] > 0 and candle["low"] > 0:
                    range_vol = (candle["high"] - candle["low"]) / candle["close"]
                    weight = (i + 1) ** 2.7
                    weighted_volatilities.append(range_vol * weight)
                    total_weight += weight

            if not weighted_volatilities or total_weight == 0:
                return {"weighted_volatility": 0.0, "max_volatility": 0.0, "current_volatility": 0.0}

            weighted_avg = sum(weighted_volatilities) / total_weight
            weights = [(i + 1) ** 2.7 for i in range(len(recent_candles))]
            max_vol = max(weighted_volatilities) / max(weights) if weights else 0.0

            current_volatility = 0.0
            if candles:
                c = candles[-1]
                if c["close"] > 0 and c["high"] > 0 and c["low"] > 0:
                    current_volatility = (c["high"] - c["low"]) / c["close"]

            return {
                "weighted_volatility": weighted_avg,
                "max_volatility": max_vol,
                "current_volatility": current_volatility,
                "volatility_count": len(weighted_volatilities),
            }
        except Exception as e:
            logger.error(f"❌ Weighted volatility calculation failed: {e}")
            raise

    def detect_volatility_spikes(
        self,
        current_volatility: float,
        weighted_volatility: float,
        basic_volatility: float,
    ) -> Dict[str, Any]:
        """
        Relative + absolute spike detection. Regime-aware.
        baseline = max(weighted, basic, eps). relative_spike iff weighted > eps and
        current >= weighted * multiplier. absolute_spike iff current >= abs threshold.
        is_spike = relative_spike OR absolute_spike.
        Intensity from ratio = current / baseline: MODERATE < ratio_mod, HIGH < ratio_high, else EXTREME.
        """
        try:
            cfg = _get_vol_config()
            _validate_vol_config(cfg)
            eps = cfg["eps"]
            abs_thresh = cfg["abs_spike"]
            mult = cfg["spike_mult"]
            ratio_mod = cfg["ratio_mod"]
            ratio_high = cfg["ratio_high"]

            baseline = max(weighted_volatility, basic_volatility, eps)
            ratio = current_volatility / baseline if baseline > 0 else 0.0

            relative_spike = (
                weighted_volatility > eps
                and current_volatility >= weighted_volatility * mult
            )
            absolute_spike = current_volatility >= abs_thresh
            is_spike = relative_spike or absolute_spike

            spike_intensity = "NONE"
            if is_spike:
                if ratio < ratio_mod:
                    spike_intensity = "MODERATE"
                elif ratio < ratio_high:
                    spike_intensity = "HIGH"
                else:
                    spike_intensity = "EXTREME"

            return {
                "is_spike": is_spike,
                "spike_intensity": spike_intensity,
                "baseline": baseline,
                "ratio": ratio,
                "current_volatility": current_volatility,
            }
        except Exception as e:
            logger.error(f"❌ Volatility spike detection failed: {e}")
            raise

    def calculate_primary_volatility(
        self,
        basic_vol: float,
        weighted_vol: float,
        current_vol: float,
        is_spike: bool,
        spike_intensity: str,
    ) -> Tuple[float, float, float]:
        """
        Adaptive blending from current/baseline ratio. Baseline = max(weighted, basic, eps).
        current_weight by ratio tiers (config); primary = current_weight*current + (1-current_weight)*weighted;
        primary = max(primary, basic). Returns (primary, baseline, ratio) for logging.
        """
        try:
            cfg = _get_vol_config()
            _validate_vol_config(cfg)
            eps = cfg["eps"]
            w_strong = cfg["w_strong"]
            w_high = cfg["w_high"]
            w_med = cfg["w_med"]
            w_base = cfg["w_base"]
            r_strong = cfg["r_strong"]
            r_high = cfg["r_high"]
            r_med = cfg["r_med"]

            baseline = max(weighted_vol, basic_vol, eps)
            ratio = current_vol / baseline if baseline > 0 else 0.0

            if ratio >= r_strong:
                current_weight = w_strong
            elif ratio >= r_high:
                current_weight = w_high
            elif ratio >= r_med:
                current_weight = w_med
            else:
                current_weight = w_base

            weighted_weight = 1.0 - current_weight
            primary = current_weight * current_vol + weighted_weight * weighted_vol
            primary = max(primary, basic_vol)

            return (primary, baseline, ratio)
        except Exception as e:
            logger.error(f"❌ Primary volatility calculation failed: {e}")
            raise
