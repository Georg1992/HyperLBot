#!/usr/bin/env python3
"""
ML Feature Validator
Validates that all ML-ready features are present and in expected ranges
Used for ensuring feature consistency before ML model training
"""

from typing import Dict, Any, Optional
from loguru import logger


class MLFeatureValidator:
    """Validates ML-ready features in predictions"""
    
    # Expected feature ranges for validation
    FEATURE_RANGES = {
        "long_score": (0.0, 100.0),
        "short_score": (0.0, 100.0),
        "score_diff": (0.0, 100.0),  # Absolute difference, so 0-100
        "fill_probability": (0.0, 100.0),
        "liquidation_safety": (0.0, 100.0),
        "level_strength": (0.0, 100.0),
        "spread_penalty": (0.0, 20.0),  # Max penalty is 20.0
        "entry_distance_to_nearest_psych_level_pct": (0.0, 10.0),  # Reasonable max distance
        "combined_score": (0.0, 100.0),
        "entry_score": (0.0, 100.0)
    }
    
    # Required features for ML training
    REQUIRED_FEATURES = [
        "long_score",
        "short_score",
        "score_diff",
        "fill_probability",
        "liquidation_safety",
        "level_strength",
        "spread_penalty"
    ]
    
    # Optional features (exposed but may not always be present)
    OPTIONAL_FEATURES = [
        "entry_distance_to_nearest_psych_level_pct",
        "factor_scores",
        "synergy_multipliers",
        "proximity_factor",
        "level_strength_raw"
    ]
    
    @classmethod
    def validate_prediction_features(cls, prediction: Dict[str, Any], strict: bool = False) -> tuple[bool, list[str]]:
        """
        Validate that prediction contains all required ML-ready features
        
        Args:
            prediction: Prediction dictionary (from direction/entry calculation)
            strict: If True, also validate optional features and ranges
            
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        is_valid = True
        
        # Check required features
        for feature in cls.REQUIRED_FEATURES:
            if feature not in prediction:
                warnings.append(f"Missing required ML feature: {feature}")
                is_valid = False
            elif strict:
                # Validate feature is in expected range
                value = prediction[feature]
                if feature in cls.FEATURE_RANGES:
                    min_val, max_val = cls.FEATURE_RANGES[feature]
                    if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                        warnings.append(f"Feature '{feature}' out of range: {value} (expected [{min_val}, {max_val}])")
                        is_valid = False
        
        # Check optional features if strict mode
        if strict:
            for feature in cls.OPTIONAL_FEATURES:
                if feature not in prediction:
                    warnings.append(f"Missing optional ML feature: {feature}")
                elif feature in cls.FEATURE_RANGES:
                    value = prediction[feature]
                    min_val, max_val = cls.FEATURE_RANGES[feature]
                    if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                        warnings.append(f"Optional feature '{feature}' out of range: {value} (expected [{min_val}, {max_val}])")
        
        return is_valid, warnings
    
    @classmethod
    def validate_direction_features(cls, direction_result: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate direction calculation features
        
        Args:
            direction_result: Result from _score_direction()
            
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        is_valid = True
        
        # Required direction features
        required = ["direction", "long_score", "short_score", "score_diff"]
        for feature in required:
            if feature not in direction_result:
                warnings.append(f"Missing direction feature: {feature}")
                is_valid = False
        
        # Validate score_diff matches long_score - short_score
        if "long_score" in direction_result and "short_score" in direction_result and "score_diff" in direction_result:
            expected_diff = abs(direction_result["long_score"] - direction_result["short_score"])
            actual_diff = direction_result["score_diff"]
            if abs(expected_diff - actual_diff) > 0.01:  # Allow small floating point error
                warnings.append(f"score_diff mismatch: expected {expected_diff:.2f}, got {actual_diff:.2f}")
        
        # Optional features (for ML)
        optional = ["factor_scores", "synergy_multipliers"]
        for feature in optional:
            if feature not in direction_result:
                warnings.append(f"Missing optional direction feature: {feature} (ML training may be limited)")
        
        return is_valid, warnings
    
    @classmethod
    def validate_entry_features(cls, entry_breakdown: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate entry calculation features
        
        Args:
            entry_breakdown: Breakdown from _determine_optimal_entry_price()
            
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        is_valid = True
        
        # Required entry features
        required = ["entry_price", "fill_probability", "liquidation_safety", "level_strength", "spread_penalty", "combined_score"]
        for feature in required:
            if feature not in entry_breakdown:
                warnings.append(f"Missing entry feature: {feature}")
                is_valid = False
            elif feature in cls.FEATURE_RANGES:
                value = entry_breakdown[feature]
                min_val, max_val = cls.FEATURE_RANGES[feature]
                if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                    warnings.append(f"Entry feature '{feature}' out of range: {value} (expected [{min_val}, {max_val}])")
                    is_valid = False
        
        return is_valid, warnings
    
    @classmethod
    def log_validation_results(cls, is_valid: bool, warnings: list[str], context: str = "prediction"):
        """
        Log validation results
        
        Args:
            is_valid: Whether validation passed
            warnings: List of warning messages
            context: Context for logging (e.g., "direction", "entry", "prediction")
        """
        if is_valid and not warnings:
            logger.debug(f"✅ ML feature validation passed for {context}")
        elif warnings:
            for warning in warnings:
                logger.warning(f"⚠️ ML feature validation warning ({context}): {warning}")
            if not is_valid:
                logger.error(f"❌ ML feature validation failed for {context} - missing required features")
