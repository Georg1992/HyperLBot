#!/usr/bin/env python3
"""
Base Pattern Detector
Abstract base class for all pattern detectors
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from loguru import logger

class BasePatternDetector(ABC):
    """Abstract base class for pattern detectors"""
    
    def __init__(self):
        """Initialize the pattern detector"""
        self.pattern_expiration = {}
        self._setup_pattern_expiration()
    
    @abstractmethod
    def _setup_pattern_expiration(self):
        """Setup pattern expiration times for this detector"""
        pass
    
    @abstractmethod
    def detect_patterns(self, data: Any) -> List[Dict[str, Any]]:
        """
        Detect patterns in the given data
        
        Args:
            data: Input data (candles or prices)
            
        Returns:
            List of detected patterns
        """
        pass
    
    def _calculate_slope(self, data: List[float]) -> float:
        """Calculate slope of data using linear regression"""
        if len(data) < 2:
            return 0.0
        
        n = len(data)
        x_sum = sum(range(n))
        y_sum = sum(data)
        xy_sum = sum(i * data[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        if n * x2_sum - x_sum * x_sum == 0:
            return 0.0
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        return slope
    
    def _find_peaks(self, data: List[float]) -> List[tuple]:
        """Find peaks in data"""
        peaks = []
        for i in range(1, len(data) - 1):
            if data[i] > data[i-1] and data[i] > data[i+1]:
                peaks.append((i, data[i]))
        return peaks
    
    def _find_valleys(self, data: List[float]) -> List[tuple]:
        """Find valleys in data"""
        valleys = []
        for i in range(1, len(data) - 1):
            if data[i] < data[i-1] and data[i] < data[i+1]:
                valleys.append((i, data[i]))
        return valleys
    
    def _find_valley_between(self, data: List[float], start: int, end: int) -> Optional[int]:
        """Find lowest point between two indices"""
        if start >= end or start < 0 or end >= len(data):
            return None
        
        min_val = float('inf')
        min_idx = None
        
        for i in range(start + 1, end):
            if data[i] < min_val:
                min_val = data[i]
                min_idx = i
        
        return min_idx
    
    def _find_peak_between(self, data: List[float], start: int, end: int) -> Optional[int]:
        """Find highest point between two indices"""
        if start >= end or start < 0 or end >= len(data):
            return None
        
        max_val = float('-inf')
        max_idx = None
        
        for i in range(start + 1, end):
            if data[i] > max_val:
                max_val = data[i]
                max_idx = i
        
        return max_idx
    
    def _create_pattern(self, pattern_name: str, pattern_type: str, direction: str, 
                       confidence: float, start_idx: int, end_idx: int, 
                       pattern_high: float, pattern_low: float, 
                       indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Create a standardized pattern dictionary"""
        pattern = {
            "pattern": pattern_name,
            "type": pattern_type,
            "direction": direction,
            "confidence": confidence,
            "start_candle_index": start_idx,
            "end_candle_index": end_idx,
            "pattern_high": pattern_high,
            "pattern_low": pattern_low,
        }
        
        if indices:
            pattern["indices"] = indices
            
        return pattern
