#!/usr/bin/env python3
"""
Execution Gate
Centralized gate for determining if a prediction can be executed
"""

from typing import Tuple
from core.execution.prediction_engine import TradingPrediction


def is_executable(prediction: TradingPrediction) -> Tuple[bool, str]:
    """
    Determine if a prediction can be executed
    
    Args:
        prediction: TradingPrediction object
        
    Returns:
        Tuple of (executable: bool, reason: str)
    """
    # For now, predictions are not executable until confidence is implemented
    if prediction.confidence is None:
        return (False, "confidence_not_implemented")
    
    # Future: Add additional gates here
    # - Minimum confidence threshold
    # - Risk limits
    # - Market conditions
    # - Position limits
    
    return (prediction.executable, prediction.execution_gate_reason)
