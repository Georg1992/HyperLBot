#!/usr/bin/env python3
"""
Confidence service – shared placeholder for ML-based confidence.
Both PredictionEngine and ReactiveEngine call this; for now it always returns None.
"""

from typing import Dict, Any, Optional


def predict(feature_vector: Dict[str, Any]) -> Optional[float]:
    """
    Placeholder for ML confidence prediction.
    Returns None until confidence is implemented.
    Both engines must call this but keep confidence=None, executable=False,
    execution_gate_reason="confidence_not_implemented".
    """
    return None
