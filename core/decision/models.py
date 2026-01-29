#!/usr/bin/env python3
"""
Shared decision models and feature-vector schema for PredictionEngine and ReactiveEngine.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Literal

# ─── Required keys for feature vector (NO FALLBACKS) ─────────────────────────

FEATURE_VECTOR_REQUIRED_KEYS = [
    "engine_prediction",
    "engine_reaction",
    "entry_limit",
    "entry_market",
    "rsi",
    "rsi_trend",
    "trend_strength",
    "trend_alignment",
    "volatility_atr_pct",
    "volume_anomaly",
    "pressure_strength",
    "spread_pct",
    "timestamp",
    "sr_strength",
    "sr_distance_atr",
    "psych_distance_pct",
    "level_source_sr",
    "level_source_psych",
    "long_score",
    "short_score",
    "score_diff",
    "setup_type_categorical",
    "ivs_is_squeeze",
    "ivs_strength",
    "ivs_duration_minutes",
    "ivs_released",
    "ivs_release_age_minutes",
]


def default_feature_vector() -> Dict[str, Any]:
    """Base feature vector with all required keys and numeric defaults."""
    return {
        "engine_prediction": 0.0,
        "engine_reaction": 0.0,
        "entry_limit": 0.0,
        "entry_market": 0.0,
        "rsi": 0.0,
        "rsi_trend": 0.0,
        "trend_strength": 0.0,
        "trend_alignment": 0.0,
        "volatility_atr_pct": 0.0,
        "volume_anomaly": 0.0,
        "pressure_strength": 0.0,
        "spread_pct": 0.0,
        "timestamp": 0.0,
        "sr_strength": 0.0,
        "sr_distance_atr": 0.0,
        "psych_distance_pct": 0.0,
        "level_source_sr": 0.0,
        "level_source_psych": 0.0,
        "long_score": 0.0,
        "short_score": 0.0,
        "score_diff": 0.0,
        "setup_type_categorical": 0,
        "ivs_is_squeeze": 0,
        "ivs_strength": 0.0,
        "ivs_duration_minutes": 0.0,
        "ivs_released": 0,
        "ivs_release_age_minutes": 0.0,
    }


def rsi_trend_to_numeric(val: Any) -> float:
    """
    Map rsi_trend / trend (categorical string or numeric) to feature-vector numeric.
    BULLISH/UP/... -> 1.0, BEARISH/DOWN/... -> -1.0, NEUTRAL/UNKNOWN/... -> 0.0.
    Numeric passed through (clamped to [-1, 1]); None/missing -> 0.0.
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        v = float(val)
        return max(-1.0, min(1.0, v))
    s = (str(val) or "").strip().upper()
    if s in ("BULLISH", "UP", "INCREASING", "RISING"):
        return 1.0
    if s in ("BEARISH", "DOWN", "DECREASING", "FALLING"):
        return -1.0
    return 0.0


def validate_feature_schema(feature_vector: Dict[str, Any]) -> None:
    """
    Validate that feature_vector contains all required keys.
    Raises KeyError if any required key is missing (NO FALLBACKS).
    """
    missing = [k for k in FEATURE_VECTOR_REQUIRED_KEYS if k not in feature_vector]
    if missing:
        raise KeyError(
            f"Feature vector missing required keys (NO FALLBACKS): {missing}"
        )


def fill_ivs_feature_vector(
    fv: Dict[str, Any],
    unified_data: Dict[str, Any],
    strict_ivs: bool = False,
) -> None:
    """
    Populate ivs_* in feature vector from unified_data["iv_squeeze"].
    Timing-only; never use for direction or entry. When iv_squeeze missing:
    strict_ivs -> raise; else set ivs_* = 0.
    """
    iv = unified_data.get("iv_squeeze")
    if not iv or not isinstance(iv, dict):
        if strict_ivs:
            raise KeyError("iv_squeeze missing (STRICT_IVS_PRESENCE)")
        fv["ivs_is_squeeze"] = 0
        fv["ivs_strength"] = 0.0
        fv["ivs_duration_minutes"] = 0.0
        fv["ivs_released"] = 0
        fv["ivs_release_age_minutes"] = 0.0
        return
    ts = float(unified_data.get("timestamp") or 0.0)
    fv["ivs_is_squeeze"] = 1 if iv.get("is_squeeze") else 0
    fv["ivs_strength"] = float(iv.get("squeeze_strength") or 0.0)
    fv["ivs_duration_minutes"] = float(iv.get("duration_minutes") or 0.0)
    fv["ivs_released"] = 1 if iv.get("squeeze_released") else 0
    rt = iv.get("release_timestamp")
    if rt is not None and ts > 0:
        fv["ivs_release_age_minutes"] = max(0.0, (ts - float(rt)) / 60.0)
    else:
        fv["ivs_release_age_minutes"] = 0.0


# ─── Decision models ─────────────────────────────────────────────────────────


@dataclass
class DecisionContext:
    """Unified context: unified_data + strategy + computed helpers."""

    unified_data: Dict[str, Any]
    strategy_used_by_engine: str
    current_price: float = 0.0
    atr_5m: float = 0.0
    atr_pct: float = 0.0
    state_strategy: str = ""
    prediction_strategy: str = ""
    timestamp: float = 0.0


@dataclass
class DirectionResult:
    """Direction scoring result."""

    direction: Literal["LONG", "SHORT", "NONE"]
    long_score: float = 0.0
    short_score: float = 0.0
    score_diff: float = 0.0
    reasoning: str = ""
    factor_scores: Dict[str, Any] = field(default_factory=dict)
    # Reaction-only: best candidate when direction comes from reaction
    reaction_best: Optional[Dict[str, Any]] = None
    # Direction strength breakdown (prediction): diff, normalized_diff, top_factors, inactive_factors
    breakdown_direction: Optional[Dict[str, Any]] = None


@dataclass
class EntryResult:
    """Entry (limit or market) result."""

    entry_price: float = 0.0
    setup_type: str = ""
    direction: Literal["LONG", "SHORT", "NONE"] = "NONE"
    breakdown: Dict[str, Any] = field(default_factory=dict)
    entry_score: float = 0.0
    reasoning: str = ""


@dataclass
class RiskResult:
    """Stop / target / R:R result."""

    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    rr_ratio: Optional[float] = None
    breakdown: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionResult:
    """
    Unified output for both PredictionEngine and ReactiveEngine.
    Same contract: confidence=None, executable=False, execution_gate_reason set.
    """

    engine_type: Literal["prediction", "reaction"]
    entry_type: Literal["limit", "market"]
    setup_type: str
    state_strategy: str
    prediction_strategy: str
    strategy_used_by_engine: str
    direction: Literal["LONG", "SHORT", "NONE"]
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    rr_ratio: Optional[float] = None
    long_score: Optional[float] = None
    short_score: Optional[float] = None
    score_diff: Optional[float] = None
    confidence: Optional[float] = None  # MUST be None until ML
    executable: bool = False  # MUST be False until confidence
    execution_gate_reason: str = "confidence_not_implemented"
    breakdown: Dict[str, Any] = field(default_factory=dict)
    feature_vector: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    reasoning: str = ""
    timing_score: float = 0.0
    timing_reason: str = "no_squeeze"

    @property
    def risk_reward_ratio(self) -> float:
        """Alias for position sizing compatibility."""
        return float(self.rr_ratio or 0.0)
