#!/usr/bin/env python3
"""
SRDetector - Handles swing point detection and level clustering
Responsible for identifying significant price levels and merging nearby levels
"""

import time
from typing import Dict, List, Any, Tuple
from loguru import logger


class SRDetector:
    """
    Detector for Support/Resistance swing points and clustering
    
    Responsibilities:
    - Detect swing points using adaptive algorithms
    - Cluster nearby levels to reduce noise
    - Handle multi-timeframe swing detection
    - Optimize detection for 5m BTC trading
    """
    
    def __init__(self):
        """Initialize the detector"""
        self._swing_cache = {}
        self._last_detection_time = {}
        
    def detect_swing_points(self, candles: List[Dict], current_price: float, 
                          n: int = 2, timeframe: str = "5m") -> List[Dict]:
        """
        Detect swing points using adaptive algorithm
        
        Args:
            candles: List of candle dictionaries
            current_price: Current price for validation
            n: Number of candles on each side for swing detection
            timeframe: Timeframe for adaptive parameters
            
        Returns:
            List of swing point dictionaries
        """
        try:
            if len(candles) < n * 2 + 1:
                return []
            
            # Adaptive parameters based on timeframe
            adaptive_params = self._get_adaptive_params(timeframe)
            
            swing_points = []
            
            # Use adaptive swing detection
            for i in range(n, len(candles) - n):
                candle = candles[i]
                high = candle.get('high', 0)
                low = candle.get('low', 0)
                close = candle.get('close', 0)
                open_price = candle.get('open', 0)
                
                if high <= 0 or low <= 0 or close <= 0 or open_price <= 0:
                    continue
                
                # Check for swing high
                if self._is_swing_high(candles, i, n, adaptive_params):
                    swing_points.append({
                        'level': high,
                        'type': 'resistance',
                        'timestamp': candle.get('timestamp', time.time()),
                        'candle_index': i,
                        'timeframe': timeframe,
                        'strength': self._calculate_swing_strength(candles, i, 'high', adaptive_params)
                    })
                
                # Check for swing low
                if self._is_swing_low(candles, i, n, adaptive_params):
                    swing_points.append({
                        'level': low,
                        'type': 'support',
                        'timestamp': candle.get('timestamp', time.time()),
                        'candle_index': i,
                        'timeframe': timeframe,
                        'strength': self._calculate_swing_strength(candles, i, 'low', adaptive_params)
                    })
            
            logger.debug(f"📊 Detected {len(swing_points)} swing points for {timeframe}")
            return swing_points
            
        except Exception as e:
            logger.error(f"❌ Swing point detection failed: {e}")
            return []
    
    def _get_adaptive_params(self, timeframe: str) -> Dict[str, Any]:
        """
        Get adaptive parameters based on timeframe
        
        Args:
            timeframe: Timeframe string
            
        Returns:
            Dictionary of adaptive parameters
        """
        params = {
            "5m": {
                "min_swing_size": 0.001,  # 0.1% minimum swing
                "atr_multiplier": 0.5,    # ATR multiplier for noise filtering
                "volume_threshold": 0.8,   # Volume threshold for significance
                "wick_ratio": 0.3         # Maximum wick ratio
            },
            "15m": {
                "min_swing_size": 0.002,  # 0.2% minimum swing
                "atr_multiplier": 0.7,
                "volume_threshold": 0.7,
                "wick_ratio": 0.4
            },
            "1h": {
                "min_swing_size": 0.005,  # 0.5% minimum swing
                "atr_multiplier": 1.0,
                "volume_threshold": 0.6,
                "wick_ratio": 0.5
            }
        }
        
        return params.get(timeframe, params["5m"])
    
    def _is_swing_high(self, candles: List[Dict], index: int, n: int, params: Dict[str, Any]) -> bool:
        """
        Check if candle at index is a swing high
        
        Args:
            candles: List of candles
            index: Current candle index
            n: Number of candles on each side
            params: Adaptive parameters
            
        Returns:
            True if swing high
        """
        try:
            current_high = candles[index].get('high', 0)
            if current_high <= 0:
                return False
            
            # Check if current high is higher than surrounding candles
            for i in range(max(0, index - n), min(len(candles), index + n + 1)):
                if i != index:
                    other_high = candles[i].get('high', 0)
                    if other_high >= current_high:
                        return False
            
            # Apply adaptive filters
            if not self._passes_adaptive_filters(candles, index, 'high', params):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _is_swing_low(self, candles: List[Dict], index: int, n: int, params: Dict[str, Any]) -> bool:
        """
        Check if candle at index is a swing low
        
        Args:
            candles: List of candles
            index: Current candle index
            n: Number of candles on each side
            params: Adaptive parameters
            
        Returns:
            True if swing low
        """
        try:
            current_low = candles[index].get('low', 0)
            if current_low <= 0:
                return False
            
            # Check if current low is lower than surrounding candles
            for i in range(max(0, index - n), min(len(candles), index + n + 1)):
                if i != index:
                    other_low = candles[i].get('low', 0)
                    if other_low <= current_low:
                        return False
            
            # Apply adaptive filters
            if not self._passes_adaptive_filters(candles, index, 'low', params):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _passes_adaptive_filters(self, candles: List[Dict], index: int, 
                                swing_type: str, params: Dict[str, Any]) -> bool:
        """
        Apply adaptive filters to reduce noise
        
        Args:
            candles: List of candles
            index: Current candle index
            swing_type: 'high' or 'low'
            params: Adaptive parameters
            
        Returns:
            True if passes filters
        """
        try:
            candle = candles[index]
            high = candle.get('high', 0)
            low = candle.get('low', 0)
            close = candle.get('close', 0)
            open_price = candle.get('open', 0)
            volume = candle.get('volume', 0)
            
            if high <= 0 or low <= 0 or close <= 0 or open_price <= 0:
                return False
            
            # Calculate swing size
            swing_size = (high - low) / close if swing_type == 'high' else (high - low) / close
            
            # Check minimum swing size
            if swing_size < params.get('min_swing_size', 0.001):
                return False
            
            # Check wick ratio (avoid small wicks)
            body_size = abs(close - open_price)
            total_size = high - low
            if total_size > 0:
                wick_ratio = (total_size - body_size) / total_size
                if wick_ratio > params.get('wick_ratio', 0.3):
                    return False
            
            # Volume check (if available)
            if volume > 0:
                # Calculate average volume for context
                avg_volume = sum(c.get('volume', 0) for c in candles[max(0, index-10):index+1]) / 11
                if avg_volume > 0 and volume < avg_volume * params.get('volume_threshold', 0.8):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _calculate_swing_strength(self, candles: List[Dict], index: int, 
                                 swing_type: str, params: Dict[str, Any]) -> float:
        """
        Calculate swing point strength
        
        Args:
            candles: List of candles
            index: Current candle index
            swing_type: 'high' or 'low'
            params: Adaptive parameters
            
        Returns:
            Strength score (0-100)
        """
        try:
            candle = candles[index]
            high = candle.get('high', 0)
            low = candle.get('low', 0)
            close = candle.get('close', 0)
            volume = candle.get('volume', 0)
            
            if high <= 0 or low <= 0 or close <= 0:
                return 0.0
            
            # Base strength from swing size
            swing_size = (high - low) / close
            size_score = min(100.0, swing_size * 10000)  # Scale to 0-100
            
            # Volume strength (if available)
            volume_score = 50.0  # Default
            if volume > 0:
                avg_volume = sum(c.get('volume', 0) for c in candles[max(0, index-10):index+1]) / 11
                if avg_volume > 0:
                    volume_ratio = volume / avg_volume
                    volume_score = min(100.0, volume_ratio * 50)
            
            # Combine scores
            strength = (size_score * 0.7 + volume_score * 0.3)
            return min(100.0, max(0.0, strength))
            
        except Exception:
            return 50.0  # Default strength
    
    def cluster_levels(self, swing_points: List[Dict], cluster_tolerance: float) -> List[Dict]:
        """
        Cluster nearby swing points to reduce noise
        
        Args:
            swing_points: List of swing point dictionaries
            cluster_tolerance: Distance tolerance for clustering
            
        Returns:
            List of clustered level dictionaries
        """
        try:
            if not swing_points:
                return []
            
            # Sort by level price
            sorted_points = sorted(swing_points, key=lambda x: x['level'])
            
            clusters = []
            current_cluster = [sorted_points[0]]
            
            for i in range(1, len(sorted_points)):
                current_point = sorted_points[i]
                last_point = current_cluster[-1]
                
                # Check if points are close enough to cluster
                if abs(current_point['level'] - last_point['level']) <= cluster_tolerance:
                    current_cluster.append(current_point)
                else:
                    # Finalize current cluster
                    if current_cluster:
                        clusters.append(self._create_cluster(current_cluster))
                    current_cluster = [current_point]
            
            # Add final cluster
            if current_cluster:
                clusters.append(self._create_cluster(current_cluster))
            
            logger.debug(f"📊 Clustered {len(swing_points)} points into {len(clusters)} levels")
            return clusters
            
        except Exception as e:
            logger.error(f"❌ Level clustering failed: {e}")
            return swing_points  # Return original if clustering fails
    
    def _create_cluster(self, points: List[Dict]) -> Dict[str, Any]:
        """
        Create a cluster from multiple swing points
        
        Args:
            points: List of swing points to cluster
            
        Returns:
            Clustered level dictionary
        """
        try:
            if not points:
                return {}
            
            # Calculate weighted average level
            total_weight = sum(p.get('strength', 50) for p in points)
            if total_weight == 0:
                total_weight = len(points)
            
            weighted_level = sum(p['level'] * p.get('strength', 50) for p in points) / total_weight
            
            # Determine cluster type (majority vote)
            support_count = sum(1 for p in points if p['type'] == 'support')
            resistance_count = sum(1 for p in points if p['type'] == 'resistance')
            cluster_type = 'support' if support_count >= resistance_count else 'resistance'
            
            # Calculate cluster metrics
            touches = len(points)
            avg_strength = sum(p.get('strength', 50) for p in points) / len(points)
            latest_timestamp = max(p.get('timestamp', 0) for p in points)
            
            return {
                'level': weighted_level,
                'type': cluster_type,
                'touches': touches,
                'strength': avg_strength,
                'timestamp': latest_timestamp,
                'merged_from': len(points),
                'timeframe_distribution': self._calculate_timeframe_distribution(points),
                'weighted_touches': sum(p.get('strength', 50) for p in points) / 50
            }
            
        except Exception as e:
            logger.error(f"❌ Cluster creation failed: {e}")
            return points[0] if points else {}
    
    def _calculate_timeframe_distribution(self, points: List[Dict]) -> Dict[str, int]:
        """
        Calculate timeframe distribution for clustered points
        
        Args:
            points: List of swing points
            
        Returns:
            Dictionary of timeframe counts
        """
        distribution = {}
        for point in points:
            tf = point.get('timeframe', '5m')
            distribution[tf] = distribution.get(tf, 0) + 1
        return distribution
