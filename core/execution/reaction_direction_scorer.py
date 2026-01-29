#!/usr/bin/env python3
"""
Reaction direction scorer – microstructure-heavy, uses only unified_data.
Produces long_score and short_score (0..100) for market_follow_through candidates.
Deterministic, replay-safe (timestamp from unified_data only).
"""

from typing import Dict, Any, Tuple

from config.config import TradingConfig


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _weights() -> Dict[str, float]:
    w = getattr(TradingConfig, "REACTION_DIRECTION_WEIGHTS", None)
    if not w or not isinstance(w, dict):
        raise ValueError("REACTION_DIRECTION_WEIGHTS missing or invalid (NO FALLBACKS)")
    return w


def _factor_imbalance(ud: Dict[str, Any]) -> float:
    """Orderbook imbalance bias -> [-1, 1]. Positive = buy bias."""
    ob = ud.get("orderbook_analysis") or ud.get("orderbook") or {}
    imb = ob.get("order_imbalance") or {}
    b = imb.get("bias")
    if b is None:
        return 0.0
    return _clamp(float(b), -1.0, 1.0)


def _factor_pressure(ud: Dict[str, Any]) -> float:
    """Pressure net_pressure / direction -> [-1, 1]. Positive = buy."""
    pr = ud.get("pressure") or {}
    net = pr.get("net_pressure")
    if net is not None:
        return _clamp(float(net), -1.0, 1.0)
    direction = (pr.get("direction") or "").upper()
    if direction in ("STRONG_BUY", "BUY"):
        return _clamp(float(pr.get("strength") or 0.5), 0.0, 1.0)
    if direction in ("STRONG_SELL", "SELL"):
        return _clamp(-float(pr.get("strength") or 0.5), -1.0, 0.0)
    return 0.0


def _factor_spread_penalty(ud: Dict[str, Any], current_price: float) -> float:
    """Wide spread penalty -> [0, 1]. 0 = no penalty, 1 = max penalty."""
    ob = ud.get("orderbook_analysis") or ud.get("orderbook") or {}
    spread = ob.get("bid_ask_spread") or {}
    pct = spread.get("percentage")
    if pct is None:
        return 0.0
    pct = float(pct)
    wide = float(getattr(TradingConfig, "REACTION_SPREAD_WIDE_PCT", 0.05))
    if wide <= 0:
        return 0.0
    return _clamp(pct / wide, 0.0, 1.0)


def _factor_level_proximity(
    ud: Dict[str, Any], current_price: float, atr_5m: float
) -> float:
    """
    Nearest S/R context -> [-1, 1]. Near support = positive (long bias),
    near resistance = negative (short bias). Do NOT use for entry price.
    """
    sr = ud.get("support_resistance") or {}
    levels = sr.get("levels") or []
    meta = (sr.get("metadata") or {})
    atr = float(meta.get("atr_5m") or 0.0) or atr_5m
    if atr <= 0 or not levels:
        return 0.0
    max_atr = float(getattr(TradingConfig, "REACTION_LEVEL_PROXIMITY_ATR", 3.0))
    supports = [l for l in levels if float(l.get("price_level") or 0) < current_price]
    resistances = [l for l in levels if float(l.get("price_level") or 0) > current_price]
    supports.sort(key=lambda l: current_price - float(l.get("price_level") or 0))
    resistances.sort(key=lambda l: float(l.get("price_level") or 0) - current_price)
    near_sup = (
        (current_price - float(supports[0]["price_level"])) / atr
        if supports else float("inf")
    )
    near_res = (
        (float(resistances[0]["price_level"]) - current_price) / atr
        if resistances else float("inf")
    )
    if near_sup > max_atr and near_res > max_atr:
        return 0.0
    if near_sup < near_res:
        return _clamp(1.0 - near_sup / max_atr, 0.0, 1.0)
    return _clamp(-(1.0 - near_res / max_atr), -1.0, 0.0)


def _factor_volatility_momentum(ud: Dict[str, Any], atr_5m: float) -> float:
    """
    Volatility burst / momentum -> [0, 1]. Range vs ATR; higher = more momentum.
    Used as magnitude scale, not direction.
    """
    vol = ud.get("volatility") or {}
    vp = vol.get("volatility_percentage") or vol.get("volatility_5m")
    if vp is None:
        return 0.0
    vp = float(vp)
    cp = float(ud.get("current_price") or 0.0)
    if cp <= 0 or atr_5m <= 0:
        return 0.0
    atr_pct = (atr_5m / cp) * 100.0
    if atr_pct <= 0:
        return 0.0
    ratio = vp / atr_pct
    thresh = float(getattr(TradingConfig, "REACTION_VOLATILITY_ATR_RATIO", 1.5))
    if ratio < thresh:
        return 0.0
    return _clamp((ratio - thresh) / (2.0 - thresh), 0.0, 1.0)


def score_reaction_direction(
    unified_data: Dict[str, Any],
    current_price: float,
    atr_5m: float,
    strategy: str,
) -> Tuple[float, float, str, Dict[str, Any]]:
    """
    Compute long_score and short_score (0..100), reasoning, and breakdown.
    Uses only current-tick unified_data. Deterministic, replay-safe.
    """
    ud = unified_data
    w = _weights()
    # Validate weights sum to 1.0
    total = sum(w.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"REACTION_DIRECTION_WEIGHTS must sum to 1.0 (got {total}) (NO FALLBACKS)"
        )

    imb = _factor_imbalance(ud)
    press = _factor_pressure(ud)
    spread_pen = _factor_spread_penalty(ud, current_price)
    level = _factor_level_proximity(ud, current_price, atr_5m)
    vol_mom = _factor_volatility_momentum(ud, atr_5m)

    directional = (
        w.get("orderbook_imbalance", 0.0) * imb
        + w.get("pressure", 0.0) * press
        + w.get("level_proximity", 0.0) * level
    )
    directional = _clamp(directional, -1.0, 1.0)
    scale = 1.0 + 0.5 * vol_mom
    effective = _clamp(directional * scale * (1.0 - spread_pen * w.get("spread_penalty", 0.0)), -1.0, 1.0)

    long_score = _clamp(50.0 + 50.0 * effective, 0.0, 100.0)
    short_score = _clamp(50.0 - 50.0 * effective, 0.0, 100.0)

    reasons = []
    if imb != 0:
        reasons.append(f"imbalance={imb:.2f}")
    if press != 0:
        reasons.append(f"pressure={press:.2f}")
    if level != 0:
        reasons.append(f"level_proximity={level:.2f}")
    if spread_pen > 0:
        reasons.append(f"spread_penalty={spread_pen:.2f}")
    if vol_mom > 0:
        reasons.append(f"vol_momentum={vol_mom:.2f}")
    reasoning = "; ".join(reasons) if reasons else "neutral"

    breakdown = {
        "imbalance": imb,
        "pressure": press,
        "spread_penalty": spread_pen,
        "level_proximity": level,
        "volatility_momentum": vol_mom,
        "directional": directional,
        "effective": effective,
        "long_score": long_score,
        "short_score": short_score,
    }
    return long_score, short_score, reasoning, breakdown
