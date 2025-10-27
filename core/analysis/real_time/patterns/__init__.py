#!/usr/bin/env python3
"""
Pattern Detection Modules
Contains specialized pattern detectors for different pattern categories
"""

from .base_detector import BasePatternDetector
from .candlestick_detector import CandlestickPatternDetector
from .reversal_detector import ReversalPatternDetector
from .triangle_detector import TrianglePatternDetector
from .channel_detector import ChannelPatternDetector
from .wedge_detector import WedgePatternDetector
from .continuation_detector import ContinuationPatternDetector
from .trend_detector import TrendPatternDetector

__all__ = [
    'BasePatternDetector',
    'CandlestickPatternDetector', 
    'ReversalPatternDetector',
    'TrianglePatternDetector',
    'ChannelPatternDetector',
    'WedgePatternDetector',
    'ContinuationPatternDetector',
    'TrendPatternDetector'
]
