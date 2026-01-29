"""
Decision module – shared models and base engine for PredictionEngine and ReactiveEngine.
"""

from .models import (
    DecisionContext,
    DirectionResult,
    EntryResult,
    RiskResult,
    DecisionResult,
    FEATURE_VECTOR_REQUIRED_KEYS,
    validate_feature_schema,
    default_feature_vector,
)
from .base_engine import BaseDecisionEngine

__all__ = [
    "DecisionContext",
    "DirectionResult",
    "EntryResult",
    "RiskResult",
    "DecisionResult",
    "FEATURE_VECTOR_REQUIRED_KEYS",
    "validate_feature_schema",
    "default_feature_vector",
    "BaseDecisionEngine",
]
