#!/usr/bin/env python3
"""
SRScorer - Handles scoring, MTF confirmation, and normalization
Responsible for scoring S/R levels and managing multi-timeframe confirmations
"""

import time
import math
from typing import Dict, List, Any, Tuple
from loguru import logger

from .level import Level


class SRScorer:
    """
    Scorer for Support/Resistance levels with MTF confirmation
    
    Responsibilities:
    - Score levels using multiple factors
    - Handle multi-timeframe confirmation
    - Normalize scores to prevent bias
    - Manage MTF alignment and merging
    """
    
    def __init__(self):
        """Initialize the scorer with validated weights"""
        self._scoring_weights = {
            'mtf': 0.10,        # Multi-timeframe confirmation
            'proximity': 0.60,  # Distance from current price (increased for reachability)
            'touch': 0.15,      # Number of touches
            'volume': 0.10,     # Volume confirmation
            'recency': 0.05     # Time-based decay
        }
        
        # Validate weights sum to 1.0
        weight_sum = sum(self._scoring_weights.values())
        if abs(weight_sum - 1.0) > 0.001:
            raise ValueError(f"Scoring weights must sum to 1.0, got {weight_sum}")
        
        logger.debug(f"📊 SRScorer initialized with weights: {self._scoring_weights}")
        
    def score_levels_enhanced(self, levels: List[Level], current_price: float, 
                             atr_5m: float, atr_per_tf: Dict[str, float]) -> List[Level]:
        """
        Enhanced scoring of S/R levels with bias reduction and normalization
        
        Args:
            levels: List of Level dataclass objects
            current_price: Current price for proximity calculation
            atr_5m: 5m ATR for volatility scaling
            atr_per_tf: Dictionary of ATR values per timeframe
            
        Returns:
            List of scored Level dataclass objects with normalized scores [0-100]
        """
        try:
            scored_levels = []
            
            for level in levels:
                # Calculate individual score components (0-100)
                mtf_score = self._calculate_mtf_score_enhanced(level)
                proximity_score = self._calculate_proximity_score_enhanced(
                    level.level, current_price, atr_5m)
                touch_score = self._calculate_touch_score(level.touches)
                volume_score = self._calculate_volume_score(level, atr_5m)
                recency_score = self._calculate_recency_score(level)
                
                # Calculate weighted score with normalization
                weighted_score = self._calculate_weighted_score(
                    mtf_score, proximity_score, touch_score, volume_score, recency_score)
                
                # Normalize and clamp score to [0,100]
                normalized_score = min(100.0, max(0.0, weighted_score))
                
                # Create new Level instance with score information
                from .level import Level
                scored_level = Level(
                    level=level.level,
                    level_type=level.level_type,
                    touches=level.touches,
                    cluster_size=level.cluster_size,
                    weighted_touches=level.weighted_touches,
                    strength=level.strength,
                    timestamp=level.timestamp,
                    timeframe_distribution=level.timeframe_distribution,
                    mtf_matches=level.mtf_matches,
                    mtf_count=level.mtf_count,
                    mtf_confidence=level.mtf_confidence,
                    merged_from=level.merged_from,
                    score=normalized_score,
                    score_breakdown={
                        'mtf': mtf_score,
                        'proximity': proximity_score,
                        'touch': touch_score,
                        'volume': volume_score,
                        'recency': recency_score,
                        'weighted': normalized_score
                    }
                )
                
                scored_levels.append(scored_level)
            
            # Sort by score (highest first)
            scored_levels.sort(key=lambda x: x.score, reverse=True)
            
            logger.debug(f"📊 Scored {len(scored_levels)} levels")
            return scored_levels
            
        except Exception as e:
            logger.error(f"❌ Level scoring failed: {e}")
            return levels
    
    def _calculate_mtf_score_enhanced(self, level: Level) -> float:
        """
        Calculate multi-timeframe confirmation score using weighted system
        
        Args:
            level: Level dataclass object
            
        Returns:
            MTF score (0-100)
        """
        try:
            mtf_count = level.mtf_count
            mtf_confidence = level.mtf_confidence
            
            if mtf_count == 0:
                return 0.0
            
            # Base score from MTF confidence (0-100 scale)
            base_score = mtf_confidence * 100.0
            
            # Timeframe diversity bonus (more timeframes = higher score)
            tf_count = len(set(match.get('timeframe', '5m') for match in level.mtf_matches))
            diversity_bonus = min(30.0, tf_count * 10.0)
            
            # Confidence multiplier (0.5 to 1.0)
            confidence_multiplier = 0.5 + (mtf_confidence * 0.5)
            
            # Calculate final score
            final_score = (base_score * confidence_multiplier) + diversity_bonus
            return min(100.0, max(0.0, final_score))
            
        except Exception as e:
            logger.error(f"❌ MTF score calculation failed: {e}")
            return 0.0
    
    def _calculate_proximity_score_enhanced(self, level_price: float, 
                                          current_price: float, atr_5m: float, k: float = 5.0) -> float:
        """
        Calculate proximity score using volatility-aware exponential decay
        
        This implements a volatility-scaled exponential decay function that:
        - Gives higher scores to levels closer to current price
        - Scales the decay based on market volatility (ATR)
        - Uses exponential decay for smooth, continuous scoring
        - Prevents double-counting distance penalties
        
        Formula: proximity_score = 100 * exp(-distance / (k * atr_5m))
        Where:
        - distance = abs(level_price - current_price)
        - k = decay factor (default 5.0 for moderate distance penalty)
        - atr_5m = 5-minute ATR for volatility scaling
        
        Args:
            level_price: Level price
            current_price: Current price
            atr_5m: 5m ATR for volatility scaling
            k: Decay factor (default 5.0) - higher values = less penalty for distance
            
        Returns:
            Proximity score (0-100) where 100 = level at current price, 0 = very far away
        """
        try:
            if current_price <= 0 or level_price <= 0:
                return 0.0
            
            distance = abs(level_price - current_price)
            
            # Volatility-aware exponential decay: proximity_score = 100 * exp(-distance / (k * atr_5m))
            # k=5.0 means levels within 5*ATR get significant scores, providing moderate distance penalty
            if atr_5m > 0:
                proximity_score = 100.0 * math.exp(-(distance / (k * atr_5m)))
            else:
                # Fallback for zero ATR - use fixed distance penalty
                proximity_score = max(0.0, 100.0 - distance / 50.0)
            
            return min(100.0, max(0.0, proximity_score))
            
        except Exception as e:
            logger.error(f"❌ Proximity score calculation failed: {e}")
            return 50.0
    
    def _calculate_touch_score(self, touches: int) -> float:
        """
        Calculate touch count score
        
        Args:
            touches: Number of touches
            
        Returns:
            Touch score (0-100)
        """
        try:
            if touches <= 0:
                return 0.0
            elif touches == 1:
                return 20.0
            elif touches == 2:
                return 40.0
            elif touches == 3:
                return 60.0
            elif touches == 4:
                return 80.0
            else:
                return min(100.0, 80.0 + (touches - 4) * 5.0)
                
        except Exception as e:
            logger.error(f"❌ Touch score calculation failed: {e}")
            return 0.0
    
    def _calculate_volume_score(self, level: Level, atr_14: float) -> float:
        """
        Calculate volume confirmation score around S/R areas
        
        Args:
            level: Level dataclass object
            atr_14: ATR for volume scaling
            
        Returns:
            Volume score (0-100)
        """
        try:
            touches = level.touches
            weighted_touches = level.weighted_touches
            merged_from = level.merged_from
            
            # Base score from touch activity (indicates volume at level)
            base_score = min(80.0, (touches * 15.0) + (weighted_touches * 8.0))
            
            # Bonus for merged levels (more significant = more volume)
            merge_bonus = min(20.0, merged_from * 4.0)
            
            # Volume spike bonus for levels with high activity
            if touches >= 3:
                volume_spike_bonus = min(15.0, (touches - 2) * 5.0)
            else:
                volume_spike_bonus = 0.0
            
            # MTF confirmation bonus (multiple timeframes = more volume)
            mtf_count = level.mtf_count
            mtf_volume_bonus = min(10.0, mtf_count * 2.5)
            
            total_score = base_score + merge_bonus + volume_spike_bonus + mtf_volume_bonus
            return min(100.0, max(0.0, total_score))
            
        except Exception as e:
            logger.error(f"❌ Volume score calculation failed: {e}")
            return 50.0
    
    def _calculate_recency_score(self, level: Level) -> float:
        """
        Calculate recency score with decay function for recent levels
        
        Args:
            level: Level dataclass object
            
        Returns:
            Recency score (0-100)
        """
        try:
            timestamp = level.timestamp
            current_time = time.time()
            
            # Calculate age in seconds
            age_seconds = current_time - timestamp
            
            # Decay function: weight *= exp(-Δt / 7200) where 7200 = 2 hours
            # This gives more weight to recent levels
            decay_factor = 7200  # 2 hours in seconds
            recency_multiplier = max(0.1, math.exp(-age_seconds / decay_factor))
            
            # Base recency score (0-100)
            if age_seconds < 3600:  # Less than 1 hour
                base_score = 100.0
            elif age_seconds < 14400:  # Less than 4 hours
                base_score = 80.0
            elif age_seconds < 86400:  # Less than 1 day
                base_score = 60.0
            elif age_seconds < 259200:  # Less than 3 days
                base_score = 40.0
            elif age_seconds < 604800:  # Less than 1 week
                base_score = 20.0
            else:
                base_score = 0.0
            
            # Apply decay function
            final_score = base_score * recency_multiplier
            return min(100.0, max(0.0, final_score))
                
        except Exception as e:
            logger.error(f"❌ Recency score calculation failed: {e}")
            return 50.0
    
    def _calculate_weighted_score(self, mtf_score: float, proximity_score: float,
                                touch_score: float, volume_score: float, 
                                recency_score: float) -> float:
        """
        Calculate weighted score with normalization
        
        Args:
            mtf_score: MTF score (0-100)
            proximity_score: Proximity score (0-100)
            touch_score: Touch score (0-100)
            volume_score: Volume score (0-100)
            recency_score: Recency score (0-100)
            
        Returns:
            Weighted score (0-100)
        """
        try:
            # Calculate weighted score (individual scores are 0-100, so divide by 100 to get 0-1 range)
            weighted_score = (
                (mtf_score / 100.0) * self._scoring_weights['mtf'] +
                (proximity_score / 100.0) * self._scoring_weights['proximity'] +
                (touch_score / 100.0) * self._scoring_weights['touch'] +
                (volume_score / 100.0) * self._scoring_weights['volume'] +
                (recency_score / 100.0) * self._scoring_weights['recency']
            )
            
            # Convert back to 0-100 range with validation
            normalized_score = min(100.0, max(0.0, weighted_score * 100.0))
            
            # Validate score is within expected range
            if not (0.0 <= normalized_score <= 100.0):
                logger.warning(f"⚠️ Score out of range: {normalized_score}")
                normalized_score = max(0.0, min(100.0, normalized_score))
            
            return normalized_score
            
        except Exception as e:
            logger.error(f"❌ Weighted score calculation failed: {e}")
            return 50.0
    
    def align_mtf_levels(self, clustered_levels: List[Level], higher_tf_levels: List[Level], 
                        atr_per_tf: Dict[str, float]) -> List[Level]:
        """
        Align levels across timeframes with ATR% normalized tolerance
        
        Args:
            clustered_levels: 5m clustered Level objects
            higher_tf_levels: Higher timeframe Level objects
            atr_per_tf: Dictionary of ATR values per timeframe
            
        Returns:
            List of aligned Level objects with MTF confirmation
        """
        try:
            if not higher_tf_levels:
                logger.debug("📊 No higher timeframe levels for MTF alignment")
                return clustered_levels
            
            # Timeframe weights (higher = more important)
            tf_weights = {
                '5m': 1.0,
                '15m': 1.2, 
                '1h': 1.5,
                '1d': 2.0
            }
            
            # Adaptive tolerance based on per-timeframe volatility
            base_atr = atr_per_tf.get('15m', atr_per_tf.get('5m', 100.0))
            aligned_levels = []
            
            for level in clustered_levels:
                level_price = level.level
                mtf_matches = []
                weighted_score = 0.0
                
                # Check all timeframes for confirmation
                for htf_level in higher_tf_levels:
                    htf_price = htf_level.level
                    htf_timeframe = list(htf_level.timeframe_distribution.keys())[0] if htf_level.timeframe_distribution else '5m'
                    distance = abs(htf_price - level_price)
                    
                    # Use timeframe-specific ATR for tolerance (ATR% normalized)
                    tf_atr = atr_per_tf.get(htf_timeframe, base_atr)
                    tf_tolerance = tf_atr * 0.5 * tf_weights.get(htf_timeframe, 1.0)
                    
                    if distance <= tf_tolerance:
                        # Calculate weighted contribution
                        weight = tf_weights.get(htf_timeframe, 1.0)
                        distance_factor = max(0.1, 1.0 - (distance / tf_tolerance))
                        contribution = weight * distance_factor
                        
                        mtf_matches.append({
                            'level': htf_price,
                            'timeframe': htf_timeframe,
                            'distance': distance,
                            'weight': weight,
                            'contribution': contribution
                        })
                        
                        weighted_score += contribution
                
                # Add MTF information to level
                if mtf_matches and weighted_score >= 1.0:  # Require at least 1.0 weighted score
                    # Calculate MTF confidence with distance factor
                    distance = min(match['distance'] for match in mtf_matches)
                    mtf_confidence = self._calculate_mtf_confidence(
                        mtf_matches, distance, tf_tolerance, level_price
                    )
                    
                    # Create new Level instance with MTF information
                    from .level import Level
                    updated_level = Level(
                        level=level.level,
                        level_type=level.level_type,
                        touches=level.touches,
                        cluster_size=level.cluster_size,
                        weighted_touches=level.weighted_touches,
                        strength=level.strength,
                        timestamp=level.timestamp,
                        timeframe_distribution=level.timeframe_distribution,
                        mtf_matches=mtf_matches,
                        mtf_count=len(mtf_matches),
                        mtf_confidence=mtf_confidence,
                        merged_from=level.merged_from,
                        score=level.score,
                        score_breakdown=level.score_breakdown
                    )
                    
                    # Count timeframes represented
                    tf_count = len(set(match['timeframe'] for match in mtf_matches))
                    
                    logger.debug(f"📊 MTF CONFIRMED: Level ${level_price:.0f} - {len(mtf_matches)} matches, "
                               f"weighted_score={weighted_score:.2f}, timeframes={tf_count}")
                    
                    aligned_levels.append(updated_level)
                else:
                    # Create new Level instance without MTF information
                    from .level import Level
                    updated_level = Level(
                        level=level.level,
                        level_type=level.level_type,
                        touches=level.touches,
                        cluster_size=level.cluster_size,
                        weighted_touches=level.weighted_touches,
                        strength=level.strength,
                        timestamp=level.timestamp,
                        timeframe_distribution=level.timeframe_distribution,
                        mtf_matches=[],
                        mtf_count=0,
                        mtf_confidence=0.0,
                        merged_from=level.merged_from,
                        score=level.score,
                        score_breakdown=level.score_breakdown
                    )
                    
                    aligned_levels.append(updated_level)
            
            # Log MTF statistics
            confirmed_count = sum(1 for level in aligned_levels if level.mtf_count > 0)
            logger.debug(f"📊 MTF ALIGNMENT: {confirmed_count}/{len(aligned_levels)} levels confirmed across timeframes")
            
            return aligned_levels
            
        except Exception as e:
            logger.error(f"❌ MTF alignment failed: {e}")
            return clustered_levels
    
    def _calculate_mtf_confidence(self, mtf_matches: List[Dict], distance: float = 0.0, 
                                 atr_tolerance: float = 0.0, price: float = 0.0) -> float:
        """
        Calculate MTF confidence considering distance factor
        
        Args:
            mtf_matches: List of MTF matches
            distance: Distance from current price
            atr_tolerance: ATR-based tolerance
            price: Current price for percentage calculation
            
        Returns:
            MTF confidence (0-1)
        """
        try:
            if not mtf_matches:
                return 0.0
            
            timeframe_weights = {'1h': 1.0, '15m': 0.7, '5m': 0.3}
            total_weight = 0.0
            weighted_confidence = 0.0
            
            for match in mtf_matches:
                tf = match.get('timeframe', '5m')
                weight = timeframe_weights.get(tf, 0.3)
                total_weight += weight
                weighted_confidence += weight
            
            base_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
            
            # Apply distance factor: distance_factor = max(0, 1 - (distance / max(atrtolerance, price*small_pct)))
            if distance > 0 and (atr_tolerance > 0 or price > 0):
                small_pct = price * 0.001  # 0.1% of price
                max_tolerance = max(atr_tolerance, small_pct)
                distance_factor = max(0.0, 1.0 - (distance / max_tolerance))
                base_confidence *= distance_factor
            
            return min(1.0, max(0.0, base_confidence))
                
        except Exception as e:
            logger.error(f"❌ MTF confidence calculation failed: {e}")
            return 0.0
