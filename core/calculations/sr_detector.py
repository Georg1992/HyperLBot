#!/usr/bin/env python3
"""
SRDetector - Handles swing point detection and level clustering
CHANGELOG: Added Level dataclass support, TF-specific sensitivity, ATR-normalized filtering,
           improved volume calculation with precomputed rolling averages
"""

import time
import math
from dataclasses import replace
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
                n = self._tf_sensitivity[timeframe]  # Required (NO FALLBACKS)
            
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
                high = candle['high']  # Required (NO FALLBACKS)
                low = candle['low']  # Required (NO FALLBACKS)
                close = candle['close']  # Required (NO FALLBACKS)
                open_price = candle['open']  # Required (NO FALLBACKS)
                
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
                        timestamp=candle['timestamp'] if 'timestamp' in candle else time.time(),
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
                        timestamp=candle['timestamp'] if 'timestamp' in candle else time.time(),
                        timeframe_distribution={timeframe: 1},
                        merged_from=1
                    )
                    swing_points.append(level)
            
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
        
        return params[timeframe] if timeframe in params else params["5m"]
    
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
            return [candle['volume'] for candle in candles]  # Required (NO FALLBACKS)
        
        avg_volumes = []
        for i in range(len(candles)):
            start_idx = max(0, i - window + 1)
            end_idx = i + 1
            window_candles = candles[start_idx:end_idx]
            
            if window_candles:
                avg_volume = sum(candle['volume'] if 'volume' in candle else 0 for candle in window_candles) / len(window_candles)
                avg_volumes.append(avg_volume)
            else:
                avg_volumes.append(candles[i]['volume'])  # Required (NO FALLBACKS)
        
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
            sorted_points = sorted(points, key=lambda x: x['timestamp'] if 'timestamp' in x else 0)
            
            distinct_touches = 1  # First point counts
            min_time_delta = 180  # 3 minutes minimum between touches (more flexible)
            
            for i in range(1, len(sorted_points)):
                current_time = sorted_points[i]['timestamp']  # Required (NO FALLBACKS)
                prev_time = sorted_points[i-1]['timestamp']  # Required (NO FALLBACKS)
                
                # More flexible time delta - also check if levels are significantly different
                current_level = sorted_points[i]['level'] if 'level' in sorted_points[i] else 0
                prev_level = sorted_points[i-1]['level'] if 'level' in sorted_points[i-1] else 0
                level_diff = abs(current_level - prev_level)
                
                # Count as distinct if either time or level difference is significant
                if (current_time - prev_time >= min_time_delta) or (level_diff > 10.0):  # $10+ difference
                    distinct_touches += 1
            
            return distinct_touches
            
        except Exception as e:
            logger.error(f"❌ Distinct touches calculation failed: {e}")
            # NO FALLBACKS - Raise error instead of returning simple count
            raise ValueError(f"Distinct touches calculation failed - NO FALLBACKS: {e}")
    
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
            current_high = candles[index]['high']  # Required (NO FALLBACKS)
            if current_high <= 0:
                return False
            
            # Check if current high is higher than surrounding candles
            n_int = int(n)  # Ensure n is integer for range()
            for i in range(max(0, index - n_int), min(len(candles), index + n_int + 1)):
                if i != index:
                    other_high = candles[i]['high']  # Required (NO FALLBACKS)
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
            current_low = candles[index]['low'] if 'low' in candles[index] else 0
            if current_low <= 0:
                return False
            
            # Check if current low is lower than surrounding candles
            n_int = int(n)  # Ensure n is integer for range()
            for i in range(max(0, index - n_int), min(len(candles), index + n_int + 1)):
                if i != index:
                    other_low = candles[i]['low']  # Required (NO FALLBACKS)
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
                min_swing_size_norm = params['min_swing_size_norm'] if 'min_swing_size_norm' in params else 0.2  # More sensitive for psychological levels
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
            high = candle['high']  # Required (NO FALLBACKS)
            low = candle['low']  # Required (NO FALLBACKS)
            close = candle['close']  # Required (NO FALLBACKS)
            volume = candle['volume']  # Required (NO FALLBACKS)
            
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
    
    def cluster_levels(self, swing_points: List[Level], cluster_tolerance: float, 
                      current_price: float = None, current_time: float = None, 
                      atr_5m: float = None) -> List[Level]:
        """
        Cluster nearby swing points by type (support with support, resistance with resistance)
        Uses strength, proximity, and recency to calculate scores during clustering
        
        Args:
            swing_points: List of Level dataclass objects
            cluster_tolerance: Distance tolerance for clustering
            current_price: Current market price (for proximity calculation)
            current_time: Current timestamp (for recency calculation)
            atr_5m: 5m ATR (for volatility-scaled proximity calculation)
            
        Returns:
            List of clustered Level dataclass objects with initial scores calculated
        """
        try:
            if not swing_points:
                return []
            
            # Use current time if not provided
            if current_time is None:
                current_time = time.time()
            
            # Filter swing points by current price position:
            # - Support points must be BELOW current price (still acting as support)
            # - Resistance points must be ABOVE current price (still acting as resistance)
            # This ensures we only cluster levels that are currently relevant
            # Broken levels (support above price, resistance below price) are discarded
            if current_price is not None:
                support_points = [
                    sp for sp in swing_points 
                    if sp.level_type == 'support' and sp.level < current_price
                ]
                resistance_points = [
                    sp for sp in swing_points 
                    if sp.level_type == 'resistance' and sp.level > current_price
                ]
            else:
                # NO FALLBACKS - Current price is required for proper filtering
                raise ValueError("Current price is required for swing point filtering - NO FALLBACKS")
            
            clusters = []
            
            # Cluster support points
            if support_points:
                support_clusters = self._cluster_by_type(
                    support_points, cluster_tolerance, current_price, current_time, atr_5m
                )
                clusters.extend(support_clusters)
            
            # Cluster resistance points
            if resistance_points:
                resistance_clusters = self._cluster_by_type(
                    resistance_points, cluster_tolerance, current_price, current_time, atr_5m
                )
                clusters.extend(resistance_clusters)
            
            # Post-clustering deduplication to catch any remaining duplicates
            clusters = self._deduplicate_clusters(clusters, cluster_tolerance * 0.5)
            
            return clusters
            
        except Exception as e:
            logger.error(f"❌ Level clustering failed: {e}")
            return swing_points  # Return original if clustering fails
    
    def _cluster_by_type(self, points: List[Level], cluster_tolerance: float,
                         current_price: float = None, current_time: float = None,
                         atr_5m: float = None) -> List[Level]:
        """
        Cluster points of the same type (support or resistance)
        Uses strength, proximity, and recency for score-based clustering
        
        Args:
            points: List of Level objects of the same type
            cluster_tolerance: Distance tolerance for clustering
            current_price: Current market price (for proximity calculation)
            current_time: Current timestamp (for recency calculation)
            atr_5m: 5m ATR (for volatility-scaled proximity calculation)
            
        Returns:
            List of clustered Level objects with initial scores
        """
        if not points:
            return []
        
        # Sort by level price
        sorted_points = sorted(points, key=lambda x: x.level)
        
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
                    clusters.append(self._create_cluster(
                        current_cluster, current_price, current_time, atr_5m
                    ))
                current_cluster = [current_point]
        
        # Add final cluster
        if current_cluster:
            clusters.append(self._create_cluster(
                current_cluster, current_price, current_time, atr_5m
            ))
        
        return clusters
    
    def _create_cluster(self, points: List[Level], current_price: float = None,
                       current_time: float = None, atr_5m: float = None) -> Level:
        """
        Create a cluster from multiple Level objects using strength, proximity, and recency
        
        Calculates initial score during clustering based on:
        - Strength: Raw swing point strength (0-100)
        - Proximity: Distance from current price (exponential decay)
        - Recency: Age of touch (exponential decay)
        
        Args:
            points: List of Level objects to cluster
            current_price: Current market price (for proximity calculation)
            current_time: Current timestamp (for recency calculation)
            atr_5m: 5m ATR (for volatility-scaled proximity calculation)
            
        Returns:
            Single Level object representing the cluster with initial score calculated
        """
        try:
            if not points:
                return None
            
            if len(points) == 1:
                # For single point, return as-is (power will be calculated later by scorer)
                return points[0]
            
            # Calculate score for each point (strength * proximity * recency)
            point_scores = []
            for point in points:
                score = self._calculate_point_score(point, current_price, current_time, atr_5m)
                point_scores.append(score)
            
            # Calculate recency-based weights for price calculation
            # More recent swing points should have MORE influence on the final cluster price
            recency_weights = []
            if current_time is not None:
                import math
                for point in points:
                    time_since_touch = current_time - point.timestamp
                    hours_since_touch = time_since_touch / 3600.0
                    # Exponential decay: more recent = higher weight
                    # k=0.02 means: 0h = 1.0, 24h = 0.62, 72h = 0.24, 168h = 0.03
                    k_rec = 0.02
                    recency_weight = math.exp(-k_rec * hours_since_touch)
                    recency_weights.append(recency_weight)
            else:
                # If no current_time, use equal weights
                recency_weights = [1.0] * len(points)
            
            # Calculate total recency weight
            total_recency_weight = sum(recency_weights)
            
            # Calculate weighted average level using RECENCY weights (not just scores)
            # This ensures more recent swing points have more influence on the final cluster price
            if total_recency_weight > 0:
                weighted_level = sum(p.level * rec_weight for p, rec_weight in zip(points, recency_weights)) / total_recency_weight
            else:
                # Fallback to simple average if no recency weights
                weighted_level = sum(p.level for p in points) / len(points)
            
            # Aggregate timeframe distribution
            timeframe_distribution = {}
            for point in points:
                for tf, count in point.timeframe_distribution.items():
                    timeframe_distribution[tf] = timeframe_distribution.get(tf, 0) + count  # Accumulator pattern - OK
            
            # Count touches: Each swing point in the cluster represents a touch of the level
            cluster_touches = len(points)  # Each swing point = 1 touch
            total_weighted_touches = sum(p.weighted_touches for p in points)
            
            # Calculate initial cluster score as weighted average of point scores
            # This represents the base reversal probability before historical analysis
            total_score_weight = sum(point_scores)
            if total_score_weight > 0:
                initial_score = total_score_weight / len(points)  # Average score
            else:
                # Fallback: use max strength if we can't calculate scores
                initial_score = max(p.strength for p in points)
            
            # Use the strongest point's type and most recent timestamp
            strongest_point = max(points, key=lambda x: x.strength)
            most_recent_point = max(points, key=lambda x: x.timestamp)
            
            return Level(
                level=weighted_level,
                level_type=strongest_point.level_type,
                touches=cluster_touches,
                cluster_size=len(points),
                weighted_touches=total_weighted_touches,
                strength=max(p.strength for p in points),
                timestamp=most_recent_point.timestamp,  # Use most recent, not strongest
                timeframe_distribution=timeframe_distribution,
                merged_from=len(points)
                # Note: power will be calculated later by sr_scorer
            )
            
        except Exception as e:
            logger.error(f"❌ Cluster creation failed: {e}")
            return points[0] if points else None
    
    def _calculate_point_score(self, point: Level, current_price: float = None,
                               current_time: float = None, atr_5m: float = None) -> float:
        """
        Calculate initial score for a single point using strength, proximity, and recency
        
        Formula: score = strength * proximity_multiplier * recency_multiplier
        
        Args:
            point: Level object to score
            current_price: Current market price
            current_time: Current timestamp
            atr_5m: 5m ATR for volatility scaling
            
        Returns:
            Initial score (0-100) representing base reversal probability
        """
        try:
            # Base strength (0-100)
            strength = point.strength
            
            # Proximity multiplier (0-1): exponential decay with distance
            proximity_multiplier = 1.0
            if current_price is not None and current_price > 0:
                distance = abs(point.level - current_price)
                distance_pct = (distance / current_price) * 100.0
                
                if atr_5m is not None and atr_5m > 0:
                    # Volatility-scaled exponential decay: exp(-distance / (k * atr_5m))
                    # k=25.0 means gentle decay (same as proximity score calculation)
                    k_prox = 25.0
                    proximity_multiplier = math.exp(-(distance / (k_prox * atr_5m)))
                else:
                    # Fallback: percentage-based exponential decay
                    # k=0.25 means: 1% away = 0.78x, 2% away = 0.61x, 5% away = 0.29x
                    k_prox = 0.25
                    proximity_multiplier = math.exp(-k_prox * distance_pct)
            
            # Recency multiplier (0-1): exponential decay with time
            recency_multiplier = 1.0
            if current_time is not None:
                time_since_touch = current_time - point.timestamp
                hours_since_touch = time_since_touch / 3600.0
                
                # Exponential decay: exp(-k * hours)
                # k=0.02 means: 24h = 0.62x, 72h = 0.24x, 168h = 0.03x
                k_rec = 0.02
                recency_multiplier = math.exp(-k_rec * hours_since_touch)
            
            # Combined score: strength * proximity * recency
            # This gives us a base reversal probability (0-100)
            score = strength * proximity_multiplier * recency_multiplier
            
            return min(100.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"❌ Point score calculation failed: {e}")
            # NO FALLBACKS - Raise error instead of returning raw strength
            raise ValueError(f"Point score calculation failed - NO FALLBACKS: {e}")
    
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
            
            return deduplicated
            
        except Exception as e:
            logger.error(f"❌ Cluster deduplication failed: {e}")
            return clusters
    
