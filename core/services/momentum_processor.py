#!/usr/bin/env python3
"""
Momentum Processor – process reaction decisions (ReactiveEngine).
Stores DecisionResult as unified_data["reaction"] and logs per unified contract.
Always produces a reaction (engine output or stub); structure aligned with prediction.
"""

from typing import Dict, Any, Optional
from loguru import logger


def build_stub_reaction(
    unified_data: Dict[str, Any],
    current_price: float,
    current_strategy: str,
    reason: str = "no_reaction",
) -> Dict[str, Any]:
    """Stub when engine missing/error. Always LONG (low-quality); never NONE."""
    ts = float(unified_data.get("timestamp") or 0.0)
    strategy = (
        unified_data.get("prediction_strategy")
        or unified_data.get("strategy")
        or current_strategy
        or "standard"
    )
    reasoning = "No reaction available." if reason == "no_reaction" else f"Reaction unavailable: {reason}"
    return {
        "engine_type": "reaction",
        "entry_type": "market",
        "setup_type": "market_follow_through",
        "state_strategy": strategy,
        "prediction_strategy": strategy,
        "strategy_used_by_engine": strategy,
        "strategy": strategy,
        "direction": "LONG",
        "entry_price": current_price,
        "stop_loss": None,
        "take_profit": None,
        "rr_ratio": None,
        "confidence": None,
        "executable": False,
        "execution_gate_reason": "confidence_not_implemented",
        "status": "NOT_EXECUTABLE",
        "timestamp": ts,
        "reasoning": reasoning,
        "candidate_score": 0.0,
        "breakdown": {"reason": reason, "entry_score": 0.0},
    }


class MomentumProcessor:
    """Handles reaction decisions via ReactiveEngine (market setups). Always emits unified_data["reaction"]."""

    def __init__(self, reactive_engine=None):
        self.reactive_engine = reactive_engine

    def process_momentum_signals(
        self,
        unified_data: Dict[str, Any],
        current_price: float,
        current_strategy: str,
    ) -> Dict[str, Any]:
        """
        Run ReactiveEngine, store DecisionResult as unified_data["reaction"], log one line.
        No execution. Always produces a reaction (best including "none", or stub when engine missing/error).
        """
        if not self.reactive_engine:
            stub = build_stub_reaction(
                unified_data, current_price, current_strategy, "engine_unavailable"
            )
            unified_data["reaction"] = stub
            return stub
        try:
            result = self.reactive_engine.process_market_data(
                unified_data=unified_data,
                current_price=current_price,
                current_strategy=current_strategy,
            )
            if result is None:
                stub = build_stub_reaction(
                    unified_data, current_price, current_strategy, "no_reaction"
                )
                unified_data["reaction"] = stub
                return stub
            bd = getattr(result, "breakdown", None) or {}
            candidate_score = float(bd.get("entry_score") or bd.get("long_score") or bd.get("short_score") or 0.0)
            status = "READY" if result.executable else "NOT_EXECUTABLE"
            strategy = result.strategy_used_by_engine or current_strategy or "standard"
            reaction = {
                "engine_type": result.engine_type,
                "entry_type": result.entry_type,
                "setup_type": result.setup_type,
                "state_strategy": result.state_strategy,
                "prediction_strategy": result.prediction_strategy,
                "strategy_used_by_engine": strategy,
                "strategy": strategy,
                "direction": result.direction,
                "entry_price": result.entry_price,
                "stop_loss": result.stop_loss,
                "take_profit": result.take_profit,
                "rr_ratio": result.rr_ratio,
                "confidence": result.confidence,
                "executable": result.executable,
                "execution_gate_reason": result.execution_gate_reason,
                "status": status,
                "timestamp": result.timestamp,
                "reasoning": result.reasoning,
                "candidate_score": candidate_score,
                "breakdown": bd,
            }
            unified_data["reaction"] = reaction
            iv = (unified_data or {}).get("iv_squeeze") or {}
            logger.info(
                f"state_strategy={result.state_strategy} prediction_strategy={result.prediction_strategy} "
                f"strategy_used_by_engine={strategy} | "
                f"engine_type={result.engine_type} setup_type={result.setup_type} direction={result.direction} "
                f"entry_type={result.entry_type} entry_price={result.entry_price} rr_ratio={result.rr_ratio} "
                f"executable={result.executable} confidence={result.confidence} | "
                f"squeeze_released={bool(iv.get('squeeze_released'))} squeeze_strength={float(iv.get('squeeze_strength') or 0):.2f} "
                f"squeeze_boost_L={float(bd.get('squeeze_boost_long') or 0):.2f} squeeze_boost_S={float(bd.get('squeeze_boost_short') or 0):.2f} "
                f"candidate_score={candidate_score:.2f}"
            )
            return reaction
        except Exception as e:
            logger.warning(f"⚠️ Reactive engine check failed: {e}")
            stub = build_stub_reaction(
                unified_data, current_price, current_strategy, "error"
            )
            stub["reasoning"] = f"Reaction unavailable: {e!s}"
            unified_data["reaction"] = stub
            return stub
