"""
Machine Learning Module for HyperLBot
=====================================
Comprehensive ML system for trading predictions and signal enhancement
"""

# All imports commented out to avoid circular dependencies
# Import directly where needed instead

__all__ = [
    # Core prediction system
    'RealtimePredictionEngine',
    'global_realtime_prediction_engine',
    'RealtimePrediction',
    
    # Confidence optimization system
    'ConfidenceOptimizer',
    'global_confidence_optimizer',
    'ConfidenceCalculator', 
    'global_confidence_calculator',
    
    # Specialized components
    'DirectionRecognizer',
    'global_direction_recognizer',
    'EntryPriceCalculator',
    'global_entry_price_calculator',
    
    # Bayesian fusion
    'BayesianFusion',
    'global_bayesian_fusion',
    'Signal'
]
