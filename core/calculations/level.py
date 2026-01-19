#!/usr/bin/env python3
"""
Level dataclass for standardized S/R level representation

CHANGELOG: Production-ready version with computed properties, robust error handling,
           immutable design, deep-copy safety, and comprehensive type safety.
"""

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any


@dataclass(frozen=True)
class Level:
    """
    Immutable dataclass for Support/Resistance levels with comprehensive type safety.
    
    This dataclass represents a single S/R level with all associated metadata,
    scoring information, and multi-timeframe confirmation data.
    
    Fields:
        level: Price level in USD (float)
        level_type: Classification as "support" or "resistance" (Literal)
        touches: Number of distinct touches at this level (int)
        cluster_size: Number of swing points clustered into this level (int)
        weighted_touches: Volume-weighted touch count (float, 0.0-∞)
        strength: Raw swing point strength score (float, 0.0-100.0)
        timestamp: Unix timestamp of latest touch (float)
        timeframe_distribution: Count of touches per timeframe (Dict[str, int])
        mtf_matches: Multi-timeframe confirmation matches (List[Dict], optional)
        mtf_count: Number of MTF confirmations (int, 0-∞)
        mtf_confidence: MTF confidence score (float, 0.0-1.0)
        merged_from: Number of original levels merged into this one (int, 1-∞)
        power: Level power (pure strength: touch, volume, reversal_probability) (float, 0.0-100.0, optional)
        power_breakdown: Component power breakdown (Dict[str, float], optional)
    
    Note:
        - cluster_size: How many swing points were merged together
        - merged_from: How many original levels were combined (same as cluster_size for single levels)
        - strength: Raw swing point strength before MTF weighting
        - power: Pure level strength (inherent quality: touch count, volume, reversal probability)
        - mtf_confidence: Confidence in multi-timeframe confirmation (0.0 = no MTF, 1.0 = perfect MTF)
    """
    
    # Core level data
    level: float
    level_type: Literal["support", "resistance"]
    touches: int
    cluster_size: int
    weighted_touches: float
    strength: float
    timestamp: float
    
    # Timeframe and MTF data
    timeframe_distribution: Dict[str, int] = field(default_factory=dict)
    mtf_matches: List[Dict[str, Any]] = field(default_factory=list)
    mtf_count: int = 0
    mtf_confidence: float = 0.0
    
    # Merging and power data
    merged_from: int = 1
    power: Optional[float] = None  # Pure level strength (touch, volume, reversal_probability)
    power_breakdown: Dict[str, float] = field(default_factory=dict)
    
    @property
    def total_score(self) -> float:
        """
        Computed property that returns a combined score based on strength, weighted_touches, and mtf_confidence.
        
        Formula: total_score = strength * 0.5 + weighted_touches * 0.3 + mtf_confidence * 100 * 0.2
        
        Returns:
            Combined score (float, 0.0-∞)
        """
        return (self.strength * 0.5 + 
                self.weighted_touches * 0.3 + 
                self.mtf_confidence * 100.0 * 0.2)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Level dataclass to dictionary with all fields included.
        
        Returns:
            Dictionary representation with all fields, including optional ones
        """
        result: Dict[str, Any] = {
            'level': self.level,
            'level_type': self.level_type,
            'touches': self.touches,
            'cluster_size': self.cluster_size,
            'weighted_touches': self.weighted_touches,
            'strength': self.strength,
            'timestamp': self.timestamp,
            'timeframe_distribution': copy.deepcopy(self.timeframe_distribution),
            'mtf_matches': copy.deepcopy(self.mtf_matches),
            'mtf_count': self.mtf_count,
            'mtf_confidence': self.mtf_confidence,
            'merged_from': self.merged_from,
            'power': self.power,
            'power_breakdown': copy.deepcopy(self.power_breakdown)
        }
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Level':
        """
        Create Level instance from dictionary with robust error handling and safe numeric conversion.
        
        Args:
            data: Dictionary containing level data
            
        Returns:
            Level instance with data from dictionary
            
        Raises:
            KeyError: If required fields ('level', 'level_type') are missing
            ValueError: If level_type is not 'support' or 'resistance' or numeric conversion fails
        """
        # Validate required fields
        if 'level' not in data:
            raise KeyError("Required field 'level' is missing")
        if 'level_type' not in data:
            raise KeyError("Required field 'level_type' is missing")
        
        # Validate level_type
        level_type = data['level_type']
        if level_type not in ['support', 'resistance']:
            raise ValueError(f"Invalid level_type '{level_type}'. Must be 'support' or 'resistance'")
        
        # Safe numeric conversion with error handling
        def safe_float(value: Any, default: float = 0.0) -> float:
            """Safely convert value to float with fallback to default."""
            if value is None:
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        def safe_int(value: Any, default: int = 0) -> int:
            """Safely convert value to int with fallback to default."""
            if value is None:
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        # Create Level with safe defaults and deep copying
        return cls(
            level=safe_float(data['level']),
            level_type=level_type,
            touches=safe_int(data.get('touches'), 0),
            cluster_size=safe_int(data.get('cluster_size'), 1),
            weighted_touches=safe_float(data.get('weighted_touches'), 0.0),
            strength=safe_float(data.get('strength'), 0.0),
            timestamp=safe_float(data.get('timestamp'), 0.0),
            timeframe_distribution=copy.deepcopy(data.get('timeframe_distribution', {})),
            mtf_matches=copy.deepcopy(data.get('mtf_matches', [])),
            mtf_count=safe_int(data.get('mtf_count'), 0),
            mtf_confidence=safe_float(data.get('mtf_confidence'), 0.0),
            merged_from=safe_int(data.get('merged_from'), 1),
            power=safe_float(data.get('power')) if data.get('power') is not None else (safe_float(data.get('score')) if data.get('score') is not None else None),  # Backward compatibility
            power_breakdown=copy.deepcopy(data.get('power_breakdown', data.get('score_breakdown', {})))  # Backward compatibility
        )
    
    def is_support(self) -> bool:
        """
        Check if this level is a support level.
        
        Returns:
            True if level_type is 'support', False otherwise
        """
        return self.level_type == 'support'
    
    def is_resistance(self) -> bool:
        """
        Check if this level is a resistance level.
        
        Returns:
            True if level_type is 'resistance', False otherwise
        """
        return self.level_type == 'resistance'
    
    def has_mtf_confirmation(self) -> bool:
        """
        Check if this level has multi-timeframe confirmation.
        
        Returns:
            True if mtf_count > 0, False otherwise
        """
        return self.mtf_count > 0
    
    def get_timeframe_count(self) -> int:
        """
        Get the number of different timeframes represented in this level.
        
        Returns:
            Number of unique timeframes in timeframe_distribution
        """
        return len(self.timeframe_distribution)
    
    def get_age_hours(self, current_time: Optional[float] = None) -> float:
        """
        Calculate the age of this level in hours.
        
        Args:
            current_time: Current timestamp (defaults to time.time())
            
        Returns:
            Age in hours (float)
        """
        import time
        if current_time is None:
            current_time = time.time()
        return (current_time - self.timestamp) / 3600.0
    
    def __str__(self) -> str:
        """
        String representation of the Level with safe score display.
        
        Returns:
            Human-readable string representation
        """
        power_str = f"{self.power:.1f}" if self.power is not None else "N/A"
        return (f"Level({self.level_type}@{self.level:.2f}, "
                f"touches={self.touches}, power={power_str}, "
                f"mtf={self.mtf_count})")
    
    def __repr__(self) -> str:
        """
        Complete, readable representation of the Level for debugging.
        
        Returns:
            Detailed string representation suitable for debugging
        """
        return (f"Level(level={self.level}, level_type='{self.level_type}', "
                f"touches={self.touches}, cluster_size={self.cluster_size}, "
                f"weighted_touches={self.weighted_touches}, strength={self.strength}, "
                f"timestamp={self.timestamp}, timeframe_distribution={self.timeframe_distribution}, "
                f"mtf_matches={self.mtf_matches}, mtf_count={self.mtf_count}, "
                f"mtf_confidence={self.mtf_confidence}, merged_from={self.merged_from}, "
                f"power={self.power}, power_breakdown={self.power_breakdown})")