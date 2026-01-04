#!/usr/bin/env python3
"""
SRDetector - Handles swing point detection and level clustering
CHANGELOG: Added Level dataclass support, TF-specific sensitivity, ATR-normalized filtering,
           improved volume calculation with precomputed rolling averages
"""

import time
from typing import Dict, List, Any
from loguru import logger

from .level import Level


class SRDetector:
    """
    Detector for Support/Resistance swing points and clustering with Level dataclass support
    
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
        
        # TF-specific default sensitivity
        self._tf_sensitivity = {
            "5m": 2,
            "15m": 3,
            "1h": 4,
            "1d": 5
        }
        
    def detect_swing_points(self, candles: List[Dict], current_price: float, 
                          n: int = None, timeframe: str = "5m", atr: float = None) -> List[Level]:
        """
        Detect swing points using adaptive algorithm with TF-specific sensitivity
        
        Args:
            candles: List of candle dictionaries
            current_price: Current price for validation
            n: Number of candles on each side for swing detection (auto-calculated if None)
            timeframe: Timeframe for adaptive parameters
            atr: ATR value for normalized filtering
            
        Returns:
            List of Level dataclass objects
        """
        try:
            # Use TF-specific default sensitivity
            if n is None:
                n = self._tf_sensitivity.get(timeframe, 2)
            
            if len(candles) < n * 2 + 1:
                return []
            
            # Adaptive parameters based on timeframe
            adaptive_params = self._get_adaptive_params(timeframe)
            
            # Precompute rolling average volumes for efficiency
            avg_volumes = self._precompute_rolling_volumes(candles)
            
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
                if self._is_swing_high(candles, i, n, adaptive_params, atr):
                    level = Level(
                        level=high,
                        level_type='resistance',
                        touches=1,
                        cluster_size=1,
                        weighted_touches=1.0,
                        strength=self._calculate_swing_strength(candles, i, 'high', adaptive_params, avg_volumes),
                        timestamp=candle.get('timestamp', time.time()),
                        timeframe_distribution={timeframe: 1},
                        merged_from=1
                    )
                    swing_points.append(level)
                
                # Check for swing low
                if self._is_swing_low(candles, i, n, adaptive_params, atr):
                    level = Level(
                        level=low,
                        level_type='support',
                        touches=1,
                        cluster_size=1,
                        weighted_touches=1.0,
                        strength=self._calculate_swing_strength(candles, i, 'low', adaptive_params, avg_volumes),
                        timestamp=candle.get('timestamp', time.time()),
                        timeframe_distribution={timeframe: 1},
                        merged_from=1
                    )
                    swing_points.append(level)
            
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
                "min_swing_size": 0.0005,  # 0.05% minimum swing (more sensitive)
                "min_swing_size_norm": 0.2,  # More sensitive ATR normalization
                "atr_multiplier": 0.3,    # ATR multiplier for noise filtering
                "volume_threshold": 0.5,   # Volume threshold for significance (more lenient)
                "wick_ratio": 0.4         # Maximum wick ratio (more lenient)
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
    
    def _precompute_rolling_volumes(self, candles: List[Dict], window: int = 20) -> List[float]:
        """
        Precompute rolling average volumes for efficiency
        
        Args:
            candles: List of candle dictionaries
            window: Rolling window size
            
        Returns:
            List of rolling average volumes
        """
        if len(candles) < window:
            return [candle.get('volume', 0) for candle in candles]
        
        avg_volumes = []
        for i in range(len(candles)):
            start_idx = max(0, i - window + 1)
            end_idx = i + 1
            window_candles = candles[start_idx:end_idx]
            
            if window_candles:
                avg_volume = sum(candle.get('volume', 0) for candle in window_candles) / len(window_candles)
                avg_volumes.append(avg_volume)
            else:
                avg_volumes.append(candles[i].get('volume', 0))
        
        return avg_volumes
    
    def _calculate_distinct_touches(self, points: List[Dict]) -> int:
        """
        Calculate distinct touches avoiding same-bar touches
        
        Args:
            points: List of swing points
            
        Returns:
            Number of distinct touches
        """
        try:
            if not points:
                return 0
            
            # Sort by timestamp
            sorted_points = sorted(points, key=lambda x: x.get('timestamp', 0))
            
            distinct_touches = 1  # First point counts
            min_time_delta = 180  # 3 minutes minimum between touches (more flexible)
            
            for i in range(1, len(sorted_points)):
                current_time = sorted_points[i].get('timestamp', 0)
                prev_time = sorted_points[i-1].get('timestamp', 0)
                
                # More flexible time delta - also check if levels are significantly different
                current_level = sorted_points[i].get('level', 0)
                prev_level = sorted_points[i-1].get('level', 0)
                level_diff = abs(current_level - prev_level)
                
                # Count as distinct if either time or level difference is significant
                if (current_time - prev_time >= min_time_delta) or (level_diff > 10.0):  # $10+ difference
                    distinct_touches += 1
            
            return distinct_touches
            
        except Exception as e:
            logger.error(f"❌ Distinct touches calculation failed: {e}")
            return len(points)  # Fallback to simple count
    
    def _is_swing_high(self, candles: List[Dict], index: int, n: int, params: Dict[str, Any], atr: float = None) -> bool:
        """
        Check if candle at index is a swing high with ATR-normalized filtering
        
        Args:
            candles: List of candles
            index: Current candle index
            n: Number of candles on each side
            params: Adaptive parameters
            atr: ATR value for normalized filtering
            
        Returns:
            True if swing high
        """
        try:
            current_high = candles[index].get('high', 0)
            if current_high <= 0:
                return False
            
            # Check if current high is higher than surrounding candles
            n_int = int(n)  # Ensure n is integer for range()
            for i in range(max(0, index - n_int), min(len(candles), index + n_int + 1)):
                if i != index:
                    other_high = candles[i].get('high', 0)
                    if other_high >= current_high:
                        return False
            
            # Apply adaptive filters with ATR normalization
            if not self._passes_adaptive_filters(candles, index, 'high', params, atr):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _is_swing_low(self, candles: List[Dict], index: int, n: int, params: Dict[str, Any], atr: float = None) -> bool:
        """
        Check if candle at index is a swing low with ATR-normalized filtering
        
        Args:
            candles: List of candles
            index: Current candle index
            n: Number of candles on each side
            params: Adaptive parameters
            atr: ATR value for normalized filtering
            
        Returns:
            True if swing low
        """
        try:
            current_low = candles[index].get('low', 0)
            if current_low <= 0:
                return False
            
            # Check if current low is lower than surrounding candles
            n_int = int(n)  # Ensure n is integer for range()
            for i in range(max(0, index - n_int), min(len(candles), index + n_int + 1)):
                if i != index:
                    other_low = candles[i].get('low', 0)
                    if other_low <= current_low:
                        return False
            
            # Apply adaptive filters with ATR normalization
            if not self._passes_adaptive_filters(candles, index, 'low', params, atr):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _passes_adaptive_filters(self, candles: List[Dict], index: int, 
                                swing_type: str, params: Dict[str, Any], atr: float = None) -> bool:
        """
        Apply adaptive filters with ATR-normalized checks to reduce noise
        
        Args:
            candles: List of candles
            index: Current candle index
            swing_type: 'high' or 'low'
            params: Adaptive parameters
            atr: ATR value for normalized filtering
            
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
            
            # Calculate swing size with ATR normalization
            swing_size = high - low
            if atr and atr > 0:
                swing_size_norm = swing_size / atr
                min_swing_size_norm = params.get('min_swing_size_norm', 0.2)  # More sensitive for psychological levels
                if swing_size_norm < min_swing_size_norm:
                    return False
            else:
                # Fallback to percentage-based check
                swing_size_pct = swing_size / close
                if swing_size_pct < params.get('min_swing_size', 0.001):
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
                if avg_volume > 0 and volume < avg_volume * params.get('volume_threshold', 0.5):  # More lenient for psychological levels
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _calculate_swing_strength(self, candles: List[Dict], index: int, 
                                 swing_type: str, params: Dict[str, Any], avg_volumes: List[float] = None) -> float:
        """
        Calculate swing point strength using precomputed volume averages
        
        Args:
            candles: List of candles
            index: Current candle index
            swing_type: 'high' or 'low'
            params: Adaptive parameters
            avg_volumes: Precomputed rolling average volumes
            
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
            
            # Volume strength using precomputed averages
            volume_score = 50.0  # Default
            if volume > 0 and avg_volumes and index < len(avg_volumes):
                avg_volume = avg_volumes[index]
                if avg_volume > 0:
                    volume_ratio = volume / avg_volume
                    volume_score = min(100.0, volume_ratio * 50)
            elif volume > 0:
                # Fallback to inline calculation
                avg_volume = sum(c.get('volume', 0) for c in candles[max(0, index-10):index+1]) / 11
                if avg_volume > 0:
                    volume_ratio = volume / avg_volume
                    volume_score = min(100.0, volume_ratio * 50)
            
            # Combine scores
            strength = (size_score * 0.7 + volume_score * 0.3)
            return min(100.0, max(0.0, strength))
            
        except Exception:
            return 50.0  # Default strength
    
    def cluster_levels(self, swing_points: List[Level], cluster_tolerance: float) -> List[Level]:
        """
        Cluster nearby swing points using optimized binary search algorithm
        
        Args:
            swing_points: List of Level dataclass objects
            cluster_tolerance: Distance tolerance for clustering
            
        Returns:
            List of clustered Level dataclass objects with timeframe_distribution
        """
        try:
            if not swing_points:
                return []
            
            # Sort by level price for binary search optimization
            sorted_points = sorted(swing_points, key=lambda x: x.level)
            
            clusters = []
            current_cluster = [sorted_points[0]]
            
            for i in range(1, len(sorted_points)):
                current_point = sorted_points[i]
                last_point = current_cluster[-1]
                
                # Check if points are close enough to cluster
                if abs(current_point.level - last_point.level) <= cluster_tolerance:
                    current_cluster.append(current_point)
                else:
                    # Finalize current cluster
                    if current_cluster:
                        clusters.append(self._create_cluster(current_cluster))
                    current_cluster = [current_point]
            
            # Add final cluster
            if current_cluster:
                clusters.append(self._create_cluster(current_cluster))
            
            # Post-clustering deduplication to catch any remaining duplicates
            clusters = self._deduplicate_clusters(clusters, cluster_tolerance * 0.5)
            
            logger.debug(f"📊 CLUSTERING: {len(swing_points)} points → {len(clusters)} levels (tolerance: {cluster_tolerance:.2f})")
            return clusters
            
        except Exception as e:
            logger.error(f"❌ Level clustering failed: {e}")
            return swing_points  # Return original if clustering fails
    
    def _create_cluster(self, points: List[Level]) -> Level:
        """
        Create a cluster from multiple Level objects
        
        Args:
            points: List of Level objects to cluster
            
        Returns:
            Single Level object representing the cluster
        """
        try:
            if not points:
                return None
            
            if len(points) == 1:
                return points[0]
            
            # Calculate weighted average level and aggregate weighted touches
            total_weight = sum(p.weighted_touches for p in points)
            total_weighted_touches = sum(p.weighted_touches for p in points)
            
            if total_weight > 0:
                weighted_level = sum(p.level * p.weighted_touches for p in points) / total_weight
            else:
                weighted_level = sum(p.level for p in points) / len(points)
            
            # Aggregate timeframe distribution
            timeframe_distribution = {}
            for point in points:
                for tf, count in point.timeframe_distribution.items():
                    timeframe_distribution[tf] = timeframe_distribution.get(tf, 0) + count
            
            # Calculate distinct touches
            distinct_touches = self._calculate_distinct_touches([{
                'timestamp': p.timestamp,
                'level': p.level
            } for p in points])
            
            # Use the strongest point's type and timestamp
            strongest_point = max(points, key=lambda x: x.strength)
            
            return Level(
                level=weighted_level,
                level_type=strongest_point.level_type,
                touches=distinct_touches,
                cluster_size=len(points),
                weighted_touches=total_weighted_touches,
                strength=max(p.strength for p in points),
                timestamp=strongest_point.timestamp,
                timeframe_distribution=timeframe_distribution,
                merged_from=len(points)
            )
            
        except Exception as e:
            logger.error(f"❌ Cluster creation failed: {e}")
            return points[0] if points else None
    
    def _deduplicate_clusters(self, clusters: List[Level], tolerance: float) -> List[Level]:
        """
        Remove duplicate clusters that are too close to each other
        
        Args:
            clusters: List of clustered Level objects
            tolerance: Distance tolerance for deduplication
            
        Returns:
            Deduplicated list of Level objects
        """
        try:
            if len(clusters) <= 1:
                return clusters
            
            # Sort by strength score (keep strongest)
            sorted_clusters = sorted(clusters, key=lambda x: x.strength, reverse=True)
            deduplicated = []
            
            for cluster in sorted_clusters:
                is_duplicate = False
                for existing in deduplicated:
                    if abs(cluster.level - existing.level) <= tolerance:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    deduplicated.append(cluster)
            
            logger.debug(f"📊 DEDUPLICATION: {len(clusters)} → {len(deduplicated)} clusters")
            return deduplicated
            
        except Exception as e:
            logger.error(f"❌ Cluster deduplication failed: {e}")
            return clusters
    
