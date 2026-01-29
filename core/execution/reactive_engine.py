#!/usr/bin/env python3
"""
Reactive Engine – best MARKET reaction (market_follow_through / breakout).
Always outputs LONG or SHORT (never NONE). Same high-level contract as PredictionEngine.
Confidence/executable decided later; entry always current_price (market).
"""

from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from config.config import TradingConfig

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
from .momentum_detector import MomentumDetector
from .reaction_direction_scorer import score_reaction_direction


def _require_key(data: Dict[str, Any], key: str, context: str = "") -> Any:
    if key not in data:
        raise KeyError(f"Required key '{key}' missing ({context})")
    return data[key]


def _get_sr_stop_level(
    unified_data: Dict[str, Any],
    current_price: float,
    atr_5m: float,
    direction: str,
) -> float:
    """Nearest S/R stop level for direction, or ATR-based synthetic when no levels."""
    sr = unified_data.get("support_resistance") or {}
    levels = sr.get("levels") or []
    if atr_5m <= 0:
        raise ValueError("atr_5m must be positive (NO FALLBACKS)")
    if direction == "LONG":
        supports = [l for l in levels if float(l.get("price_level") or 0) < current_price]
        supports.sort(key=lambda l: current_price - float(l.get("price_level") or 0))
        if supports:
            return float(supports[0]["price_level"])
        return current_price - 2.0 * atr_5m
    else:
        resistances = [l for l in levels if float(l.get("price_level") or 0) > current_price]
        resistances.sort(key=lambda l: float(l.get("price_level") or 0) - current_price)
        if resistances:
            return float(resistances[0]["price_level"])
        return current_price + 2.0 * atr_5m


def _get_spread_pct(unified_data: Dict[str, Any]) -> float:
    ob = unified_data.get("orderbook_analysis") or unified_data.get("orderbook") or {}
    spread = ob.get("bid_ask_spread") or {}
    pct = spread.get("percentage")
    if pct is None:
        return float(getattr(TradingConfig, "DEFAULT_SPREAD_PCT", 0.01))
    return float(pct)


class ReactiveEngine(BaseDecisionEngine):
    """
    Best market-order reaction each tick. Always LONG or SHORT (never NONE).
    Uses microstructure (orderbook, pressure, levels, volatility) + optional breakout boost.
    """

    def __init__(self, api_manager=None):
        self._momentum_detector = MomentumDetector()
        self._api_manager = api_manager
        self._last_direction: Optional[str] = None
        logger.info("⚡ Reactive Engine initialized (always LONG or SHORT)")

    def engine_type(self) -> str:
        return "reaction"

    def entry_type(self) -> str:
        return "market"

    def build_context(
        self,
        unified_data: Dict[str, Any],
        strategy_used_by_engine: str,
    ) -> DecisionContext:
        _require_key(unified_data, "current_price", "build_context")
        _require_key(unified_data, "timestamp", "build_context")
        return super().build_context(unified_data, strategy_used_by_engine)

    def _squeeze_timing_boost(self, direction: str, context: DecisionContext) -> float:
        """Timing-only boost for breakout when squeeze_released. Else 0."""
        if not getattr(TradingConfig, "ENABLE_SQUEEZE_FEATURES", True):
            return 0.0
        iv = context.unified_data.get("iv_squeeze")
        if not iv or not isinstance(iv, dict) or not iv.get("squeeze_released"):
            return 0.0
        strength = float(iv.get("squeeze_strength") or 0.0)
        cap = float(getattr(TradingConfig, "SQUEEZE_BOOST_MAX", 10.0))
        return min(cap, strength * cap)

    def _compute_sl_tp_for_direction(
        self,
        context: DecisionContext,
        direction: str,
        entry_price: float,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Compute stop_loss, take_profit, rr_ratio for LONG/SHORT. Deterministic."""
        ud = context.unified_data
        atr = context.atr_5m
        strategy = context.strategy_used_by_engine or "standard"
        config = (getattr(TradingConfig, "STRATEGY_CONFIGS", None) or {}).get(strategy) or {}
        if not config:
            config = (getattr(TradingConfig, "STRATEGY_CONFIGS", None) or {}).get("standard") or {}
        spread_pct = _get_spread_pct(ud)
        sr = ud.get("support_resistance") or {}
        levels = sr.get("levels") or []

        try:
            from core.calculations.risk_manager import RiskManager

            sr_stop = _get_sr_stop_level(ud, entry_price, atr, direction)
            sl = RiskManager.calculate_stop_loss(
                entry_price=entry_price,
                direction=direction,
                sr_stop_level=sr_stop,
                atr_5m=atr,
                current_price=context.current_price,
                config=config,
                unified_data=ud,
            )
            tp = RiskManager.calculate_take_profit(
                entry_price=entry_price,
                stop_loss=sl,
                direction=direction,
                atr_5m=atr,
                config=config,
                sr_levels=levels,
                strategy=strategy,
                spread_pct=spread_pct,
            )
            risk = abs(entry_price - sl)
            reward = abs(tp - entry_price)
            rr = (reward / risk) if risk > 0 else None
            return sl, tp, rr
        except Exception as e:
            logger.debug(f"Reaction SL/TP computation failed: {e}")
            return None, None, None

    def compute_direction(self, context: DecisionContext) -> DirectionResult:
        ud = context.unified_data
        cp = context.current_price
        atr = context.atr_5m
        strategy = context.strategy_used_by_engine or "standard"

        long_score, short_score, reasoning, breakdown = score_reaction_direction(
            ud, cp, atr, strategy
        )

        breakouts = self._momentum_detector.evaluate_breakouts(ud, cp, atr)
        long_sig = breakouts.get("long")
        short_sig = breakouts.get("short")
        boost_long = self._squeeze_timing_boost("LONG", context) if long_sig else 0.0
        boost_short = self._squeeze_timing_boost("SHORT", context) if short_sig else 0.0

        long_total = min(100.0, max(0.0, long_score + boost_long))
        short_total = min(100.0, max(0.0, short_score + boost_short))

        breakdown["squeeze_boost_long"] = boost_long
        breakdown["squeeze_boost_short"] = boost_short
        breakdown["long_score"] = long_total
        breakdown["short_score"] = short_total

        # Explicit inactive candidates (roadmap); never selected, score -1
        INACTIVE_SCORE = -1.0
        breakdown["inactive_candidates"] = [
            {"setup_type": "reversal", "implemented": False, "score": INACTIVE_SCORE, "score_reason": "not_implemented"},
            {"setup_type": "sweep_revert", "implemented": False, "score": INACTIVE_SCORE, "score_reason": "not_implemented"},
        ]
        breakdown["candidate_scores"] = {"long": long_total, "short": short_total}

        last = self._last_direction or ud.get("last_reaction_direction")
        pressure = (ud.get("pressure") or {}).get("net_pressure")
        pressure_sign = 1 if (pressure is not None and float(pressure) > 0) else -1 if (pressure is not None and float(pressure) < 0) else 0

        if long_total > short_total:
            direction = "LONG"
            best_score = long_total
        elif short_total > long_total:
            direction = "SHORT"
            best_score = short_total
        else:
            if last in ("LONG", "SHORT"):
                direction = last
            elif pressure_sign > 0:
                direction = "LONG"
            elif pressure_sign < 0:
                direction = "SHORT"
            else:
                direction = "LONG"
            best_score = long_total if direction == "LONG" else short_total

        self._last_direction = direction

        why_others_lost = [
            "reversal: not_implemented",
            "sweep_revert: not_implemented",
        ]
        if not (long_sig and direction == "LONG"):
            why_others_lost.append("breakout_long: no momentum signal or direction SHORT")
        if not (short_sig and direction == "SHORT"):
            why_others_lost.append("breakout_short: no momentum signal or direction LONG")

        best = {
            "setup_type": "market_follow_through",
            "direction": direction,
            "entry_price": cp,
            "candidate_score": best_score,
            "stop_loss": None,
            "take_profit": None,
            "rr_ratio": None,
            "breakdown": breakdown,
        }
        if long_sig and direction == "LONG":
            best["setup_type"] = "breakout"
            best["stop_loss"] = getattr(long_sig, "stop_loss", None)
            best["take_profit"] = getattr(long_sig, "take_profit", None)
            best["rr_ratio"] = getattr(long_sig, "risk_reward_ratio", None)
            breakdown = {**breakdown, "reasoning": getattr(long_sig, "reasoning", []) or []}
        elif short_sig and direction == "SHORT":
            best["setup_type"] = "breakout"
            best["stop_loss"] = getattr(short_sig, "stop_loss", None)
            best["take_profit"] = getattr(short_sig, "take_profit", None)
            best["rr_ratio"] = getattr(short_sig, "risk_reward_ratio", None)
            breakdown = {**breakdown, "reasoning": getattr(short_sig, "reasoning", []) or []}
        else:
            sl, tp, rr = self._compute_sl_tp_for_direction(context, direction, cp)
            best["stop_loss"] = sl
            best["take_profit"] = tp
            best["rr_ratio"] = rr

        bd = {**breakdown}
        bd["chosen_candidate"] = {k: v for k, v in best.items() if k != "breakdown"}
        bd["why_others_lost"] = why_others_lost
        best["breakdown"] = bd

        rev = bd.get("reasoning") or reasoning
        if isinstance(rev, list):
            rev = "; ".join(str(x) for x in rev)

        logger.debug(
            f"⚡ reaction top-2: LONG={long_total:.2f} SHORT={short_total:.2f} "
            f"imbalance={breakdown.get('imbalance', 0):.2f} spread_pen={breakdown.get('spread_penalty', 0):.2f}"
        )
        for c in breakdown.get("inactive_candidates", []):
            logger.debug(f"⚡ inactive candidate: {c.get('setup_type')} implemented={c.get('implemented')} score_reason={c.get('score_reason')}")
        logger.info(
            f"⚡ reaction SELECTED: direction={direction} setup_type={best['setup_type']} "
            f"long_score={long_total:.2f} short_score={short_total:.2f} entry_price={cp} "
            f"confidence=None executable=False reason=confidence_not_implemented"
        )

        return DirectionResult(
            direction=direction,
            long_score=long_total if direction == "LONG" else 0.0,
            short_score=short_total if direction == "SHORT" else 0.0,
            score_diff=abs(long_total - short_total),
            reasoning=str(rev),
            reaction_best=best,
        )

    def compute_entry(
        self,
        context: DecisionContext,
        direction: DirectionResult,
    ) -> EntryResult:
        best = direction.reaction_best
        if not best:
            raise ValueError("reaction_best missing (NO FALLBACKS)")
        rev = (best.get("breakdown") or {}).get("reasoning")
        if isinstance(rev, list):
            rev = "; ".join(str(x) for x in rev)
        return EntryResult(
            entry_price=best["entry_price"],
            setup_type=best["setup_type"],
            direction=best["direction"],
            breakdown=best.get("breakdown") or {},
            entry_score=float(best.get("candidate_score") or 0.0),
            reasoning=rev or "",
        )

    def compute_sl_tp(
        self,
        context: DecisionContext,
        entry: EntryResult,
    ) -> RiskResult:
        best = getattr(context, "_reaction_best", None)
        if not best:
            return RiskResult(stop_loss=None, take_profit=None, rr_ratio=None, breakdown={})
        return RiskResult(
            stop_loss=best.get("stop_loss"),
            take_profit=best.get("take_profit"),
            rr_ratio=best.get("rr_ratio"),
            breakdown=best.get("breakdown") or {},
        )

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
        fv["engine_prediction"] = 0.0
        fv["engine_reaction"] = 1.0
        fv["entry_limit"] = 0.0
        fv["entry_market"] = 1.0
        ud = context.unified_data
        sr = ud.get("support_resistance") or {}
        meta = sr.get("metadata") or {}
        atr = float(meta.get("atr_5m") or 0.0)
        cp = context.current_price
        fv["sr_strength"] = 0.0
        fv["sr_distance_atr"] = 0.0
        fv["psych_distance_pct"] = 0.0
        fv["level_source_sr"] = 0.0
        fv["level_source_psych"] = 0.0
        setup = entry.setup_type or "market_follow_through"
        fv["setup_type_categorical"] = {"market_follow_through": 1, "breakout": 2}.get(setup, 1)
        rsi_d = ud.get("rsi") or {}
        fv["rsi"] = float(rsi_d.get("rsi") or 0.0)
        fv["rsi_trend"] = rsi_trend_to_numeric(rsi_d.get("rsi_trend") or rsi_d.get("trend"))
        tr = ud.get("trend") or {}
        fv["trend_strength"] = float(tr.get("strength") or tr.get("strength_score") or 0.0)
        fv["trend_alignment"] = 1.0 if (tr.get("direction") or "").upper() in ("BULLISH", "BEARISH") else 0.0
        vol = ud.get("volatility") or {}
        vp = vol.get("volatility_percentage") or vol.get("volatility_5m") or 0.0
        fv["volatility_atr_pct"] = float(vp) / 100.0 if vp else 0.0
        vol_cat = (ud.get("volume") or {}).get("category") or ud.get("volume_category") or ""
        fv["volume_anomaly"] = 1.0 if vol_cat in ("HIGH", "VERY_HIGH") else 0.0
        pr = ud.get("pressure") or {}
        fv["pressure_strength"] = float(pr.get("strength") or 0.0)
        ob = ud.get("orderbook_analysis") or ud.get("orderbook") or {}
        spread = ob.get("bid_ask_spread") or {}
        pct = spread.get("percentage")
        fv["spread_pct"] = float(pct) if pct is not None else 0.0
        fill_ivs_feature_vector(fv, ud, strict_ivs=getattr(TradingConfig, "STRICT_IVS_PRESENCE", False))
        return fv

    def run(
        self,
        unified_data: Dict[str, Any],
        strategy_used_by_engine: str,
    ):
        from core.decision.models import DecisionResult, validate_feature_schema

        context = self.build_context(unified_data, strategy_used_by_engine)
        direction = self.compute_direction(context)
        context._reaction_best = direction.reaction_best
        entry = self.compute_entry(context, direction)
        risk = self.compute_sl_tp(context, entry)
        fv = self.build_feature_vector(context, direction, entry, risk)
        validate_feature_schema(fv)
        from core.ml.confidence_service import predict as confidence_predict
        confidence_predict(fv)
        return self.build_result(context, direction, entry, risk, fv)

    def process_market_data(
        self,
        unified_data: Dict[str, Any],
        current_price: float,
        current_strategy: Optional[str] = None,
    ):
        """Always return DecisionResult with direction LONG or SHORT (never NONE)."""
        strategy = current_strategy or unified_data.get("prediction_strategy") or unified_data.get("strategy")
        if not strategy:
            raise ValueError("ReactiveEngine requires strategy (NO FALLBACKS)")
        return self.run(unified_data, strategy)
