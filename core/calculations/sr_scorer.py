#!/usr/bin/env python3
"""
SRScorer - Handles scoring, MTF confirmation, and normalization
Responsible for scoring S/R levels and managing multi-timeframe confirmations
"""

import math
from typing import Dict, List
from loguru import logger

from .level import Level
from config.config import TradingConfig


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
        """Initialize the scorer with validated weights
        
        Weights: proximity 65% (primary), touch 20%, MTF 10%, volume 5%
        Score (0-100) represents trading quality: higher = better for trading at current moment
        Removed recency: time distance doesn't predict trading quality - proximity and strength matter more
        """
        self._scoring_weights = {
            'mtf': 0.10,        # Multi-timeframe confirmation (10%)
            'proximity': 0.65,  # Distance from current price (65% - PRIMARY FACTOR)
            'touch': 0.20,      # Number of touches (20% - strength indicator)
            'volume': 0.05,     # Volume confirmation (5% - execution quality)
            'recency': 0.0      # Removed: time distance doesn't improve trading quality prediction
        }
        
        # Configurable decay factor for proximity
        self.proximity_decay_k = TradingConfig.SR_PROXIMITY_DECAY_K
        
        # Validate weights sum to 1.0
        weight_sum = sum(self._scoring_weights.values())
        if abs(weight_sum - 1.0) > 0.001:
            raise ValueError(f"Scoring weights must sum to 1.0, got {weight_sum}")
        
        logger.debug(f"📊 SRScorer initialized with weights: {self._scoring_weights}")
        logger.debug(f"🔧 SR proximity decay k = {self.proximity_decay_k}")
        
    def score_levels_enhanced(self, levels: List[Level], current_price: float, 
                             atr_5m: float, atr_per_tf: Dict[str, float]) -> List[Level]:
        """
        Enhanced scoring of S/R levels with bias reduction and normalization
        
        Final score (0-100) = weighted sum: proximity 65%, touch 20%, MTF 10%, volume 5%
        Higher score = better level for trading at current moment
        Score interpretation: 80-100 excellent, 60-79 good, 40-59 moderate, 20-39 poor, 0-19 very poor
        
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
                
                # Calculate weighted score with normalization (recency removed)
                weighted_score = self._calculate_weighted_score(
                    mtf_score, proximity_score, touch_score, volume_score, 0.0)
                
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
                                          current_price: float, atr_5m: float, k: float = None) -> float:
        """
        Calculate proximity score using volatility-aware exponential decay
        
        Formula: 100 * exp(-distance / (k * atr_5m))
        - k=2.0: levels within ~2*ATR get significant scores (>36%)
        - 2*ATR ≈ 2 standard deviations (95% of price action)
        - Volatility-scaled: adapts to market conditions automatically
        
        Args:
            level_price: Level price
            current_price: Current price
            atr_5m: 5m ATR for volatility scaling
            k: Decay factor (default 2.0 from config)
            
        Returns:
            Proximity score (0-100) where 100 = at current price, 0 = very far
        """
        try:
            if current_price <= 0 or level_price <= 0:
                return 0.0
            
            distance = abs(level_price - current_price)
            
            # Volatility-aware exponential decay: proximity_score = 100 * exp(-distance / (k * atr_5m))
            # k=2.0 means levels within ~2*ATR get significant scores (moderate distance penalty)
            k_value = k if (k is not None and k > 0) else self.proximity_decay_k
            if atr_5m > 0:
                proximity_score = 100.0 * math.exp(-(distance / (k_value * atr_5m)))
            else:
                # Fallback for zero ATR - use fixed distance penalty
                proximity_score = max(0.0, 100.0 - distance / 50.0)
            
            return min(100.0, max(0.0, proximity_score))
            
        except Exception as e:
            logger.error(f"❌ Proximity score calculation failed: {e}")
            return 50.0
    
    def _calculate_touch_score(self, touches: int) -> float:
        """
        Calculate touch count score with diminishing returns
        
        Scale: 1 touch=20, 2=40, 3=60, 4=80, 5+=80+5*(n-4)
        Rationale: First few touches matter most; 2-3 touches = 95% confidence
        
        Args:
            touches: Number of touches
            
        Returns:
            Touch score (0-100)
        """
        try:
            if touches <= 0:
                return 0.0
            elif touches == 1:
                return 20.0  # Establishes level
            elif touches == 2:
                return 40.0  # Confirms level (2x first touch)
            elif touches == 3:
                return 60.0  # Strong confirmation
            elif touches == 4:
                return 80.0  # Very strong (diminishing returns start)
            else:
                # Diminishing returns: each additional touch adds only 5 points
                return min(100.0, 80.0 + (touches - 4) * 5.0)
                
        except Exception as e:
            logger.error(f"❌ Touch score calculation failed: {e}")
            return 0.0
    
    def _calculate_volume_score(self, level: Level, atr_14: float) -> float:
        """
        Calculate volume confirmation score around S/R areas
        
        Components: base (touches), merge bonus, volume spike (3+ touches), MTF bonus
        Higher volume = better liquidity, less slippage, stronger level
        
        Args:
            level: Level dataclass object
            atr_14: ATR for volume scaling (reserved for future use)
            
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
    
    def _calculate_weighted_score(self, mtf_score: float, proximity_score: float,
                                touch_score: float, volume_score: float, 
                                recency_score: float = 0.0) -> float:
        """
        Calculate weighted score with normalization
        
        Args:
            mtf_score: MTF score (0-100)
            proximity_score: Proximity score (0-100)
            touch_score: Touch score (0-100)
            volume_score: Volume score (0-100)
            recency_score: Recency score (0-100) - deprecated, kept for compatibility
            
        Returns:
            Weighted score (0-100)
        """
        try:
            # Calculate weighted score (individual scores are 0-100, so divide by 100 to get 0-1 range)
            # Recency removed: time distance doesn't predict trading quality
            weighted_score = (
                (mtf_score / 100.0) * self._scoring_weights['mtf'] +
                (proximity_score / 100.0) * self._scoring_weights['proximity'] +
                (touch_score / 100.0) * self._scoring_weights['touch'] +
                (volume_score / 100.0) * self._scoring_weights['volume']
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
            
            # CRITICAL FIX: Include higher timeframe levels that don't match any 5m clustered levels
            # This ensures resistance levels above current price are not lost
            matched_htf_prices = set()
            for level in aligned_levels:
                for match in level.mtf_matches:
                    matched_htf_prices.add(match['level'])
            
            # Add unmatched higher timeframe levels (especially important for resistance above current price)
            for htf_level in higher_tf_levels:
                if htf_level.level not in matched_htf_prices:
                    # Create standalone higher timeframe level
                    from .level import Level
                    standalone_level = Level(
                        level=htf_level.level,
                        level_type=htf_level.level_type,
                        touches=htf_level.touches,
                        cluster_size=htf_level.cluster_size,
                        weighted_touches=htf_level.weighted_touches,
                        strength=htf_level.strength,
                        timestamp=htf_level.timestamp,
                        timeframe_distribution=htf_level.timeframe_distribution,
                        mtf_matches=[{
                            'level': htf_level.level,
                            'timeframe': list(htf_level.timeframe_distribution.keys())[0] if htf_level.timeframe_distribution else '5m',
                            'distance': 0.0,
                            'weight': tf_weights.get(list(htf_level.timeframe_distribution.keys())[0] if htf_level.timeframe_distribution else '5m', 1.0),
                            'contribution': 1.0
                        }],
                        mtf_count=1,
                        mtf_confidence=0.7,  # Default confidence for standalone HTF levels
                        merged_from=htf_level.merged_from,
                        score=htf_level.score if hasattr(htf_level, 'score') else 0.0,
                        score_breakdown=htf_level.score_breakdown if hasattr(htf_level, 'score_breakdown') else {}
                    )
                    aligned_levels.append(standalone_level)
                    logger.debug(f"📊 Added standalone HTF level: ${htf_level.level:.2f} (not matched to 5m clusters)")
            
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
