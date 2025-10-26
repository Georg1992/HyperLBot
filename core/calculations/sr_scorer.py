#!/usr/bin/env python3
"""
SRScorer - Handles scoring, MTF confirmation, and normalization
Responsible for scoring S/R levels and managing multi-timeframe confirmations
"""

import time
from typing import Dict, List, Any, Tuple
from loguru import logger


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
        """Initialize the scorer"""
        self._scoring_weights = {
            'mtf': 0.25,        # Increased from 0.20 to 0.25 (+0.05)
            'proximity': 0.35,  # Reduced from 0.40 to 0.35 (-5%)
            'touch': 0.20,
            'volume': 0.15,
            'recency': 0.05
        }
        
    def score_levels_enhanced(self, levels: List[Dict], current_price: float, 
                             atr_5m: float, atr_15m: float) -> List[Dict]:
        """
        Enhanced scoring of S/R levels with bias reduction and normalization
        
        Args:
            levels: List of level dictionaries
            current_price: Current price for proximity calculation
            atr_5m: 5m ATR for volatility scaling
            atr_15m: 15m ATR for MTF calculations
            
        Returns:
            List of scored level dictionaries
        """
        try:
            scored_levels = []
            
            for level in levels:
                # Calculate individual score components (0-100)
                mtf_score = self._calculate_mtf_score_enhanced(level)
                proximity_score = self._calculate_proximity_score_enhanced(
                    level['level'], current_price, atr_5m)
                touch_score = self._calculate_touch_score(level.get('touches', 0))
                volume_score = self._calculate_volume_score(level, atr_5m)
                recency_score = self._calculate_recency_score(level)
                
                # Calculate weighted score with normalization
                weighted_score = self._calculate_weighted_score(
                    mtf_score, proximity_score, touch_score, volume_score, recency_score)
                
                # Add score breakdown for debugging
                level['score'] = weighted_score
                level['score_breakdown'] = {
                    'mtf': mtf_score,
                    'proximity': proximity_score,
                    'touch': touch_score,
                    'volume': volume_score,
                    'recency': recency_score,
                    'weighted': weighted_score
                }
                
                scored_levels.append(level)
            
            # Sort by score (highest first)
            scored_levels.sort(key=lambda x: x['score'], reverse=True)
            
            logger.debug(f"📊 Scored {len(scored_levels)} levels")
            return scored_levels
            
        except Exception as e:
            logger.error(f"❌ Level scoring failed: {e}")
            return levels
    
    def _calculate_mtf_score_enhanced(self, level: Dict) -> float:
        """
        Calculate multi-timeframe confirmation score
        
        Args:
            level: Level dictionary
            
        Returns:
            MTF score (0-100)
        """
        try:
            mtf_count = level.get('mtf_count', 0)
            mtf_confidence = level.get('mtf_confidence', 0.0)
            timeframe_distribution = level.get('timeframe_distribution', {})
            
            if mtf_count == 0:
                return 0.0
            
            # Base score from MTF count
            base_score = min(100.0, mtf_count * 25.0)  # 25 points per MTF confirmation
            
            # Confidence multiplier
            confidence_multiplier = 0.5 + (mtf_confidence * 0.5)  # 0.5 to 1.0
            
            # Timeframe weighting (1h > 15m > 5m)
            timeframe_weights = {'1h': 1.0, '15m': 0.7, '5m': 0.3}
            timeframe_bonus = 0.0
            
            for tf, count in timeframe_distribution.items():
                weight = timeframe_weights.get(tf, 0.3)
                timeframe_bonus += count * weight * 10.0
            
            # Calculate final score
            final_score = (base_score * confidence_multiplier) + timeframe_bonus
            return min(100.0, max(0.0, final_score))
            
        except Exception as e:
            logger.error(f"❌ MTF score calculation failed: {e}")
            return 0.0
    
    def _calculate_proximity_score_enhanced(self, level_price: float, 
                                          current_price: float, atr_5m: float) -> float:
        """
        Calculate proximity score with ATR bias reduction
        
        Args:
            level_price: Level price
            current_price: Current price
            atr_5m: 5m ATR for volatility scaling
            
        Returns:
            Proximity score (0-100)
        """
        try:
            if current_price <= 0 or level_price <= 0:
                return 0.0
            
            distance = abs(level_price - current_price)
            
            # More aggressive proximity scoring to prioritize closer levels
            if atr_5m > 0:
                # Normalize distance by ATR
                normalized_distance = distance / atr_5m
                
                # More sensitive scoring for closer levels
                if normalized_distance < 0.5:
                    # Very close levels (within 0.5 ATR) get maximum score
                    score = 100.0
                elif normalized_distance < 1.0:
                    # Close levels (within 1 ATR) get high score
                    score = 90.0 * (1.0 - (normalized_distance - 0.5) * 0.2)
                elif normalized_distance < 2.0:
                    # Medium distance levels get moderate score
                    score = 70.0 * (1.0 - (normalized_distance - 1.0) * 0.3)
                elif normalized_distance < 3.0:
                    # Far levels get low score
                    score = 40.0 * (1.0 - (normalized_distance - 2.0) * 0.4)
                else:
                    # Very far levels get minimal score
                    score = max(0.0, 20.0 - (normalized_distance - 3.0) * 5.0)
            else:
                # Fallback to simple distance calculation (more aggressive)
                score = max(0.0, 100.0 - distance / 50.0)  # Reduced divisor for more sensitivity
            
            return min(100.0, max(0.0, score))
            
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
    
    def _calculate_volume_score(self, level: Dict, atr_14: float) -> float:
        """
        Calculate volume confirmation score
        
        Args:
            level: Level dictionary
            atr_14: ATR for volume scaling
            
        Returns:
            Volume score (0-100)
        """
        try:
            # Simplified volume scoring based on level activity
            touches = level.get('touches', 0)
            weighted_touches = level.get('weighted_touches', 0)
            merged_from = level.get('merged_from', 1)
            
            # Base score from touch activity
            base_score = min(100.0, (touches * 20.0) + (weighted_touches * 10.0))
            
            # Bonus for merged levels (more significant)
            merge_bonus = min(20.0, merged_from * 5.0)
            
            total_score = base_score + merge_bonus
            return min(100.0, max(0.0, total_score))
            
        except Exception as e:
            logger.error(f"❌ Volume score calculation failed: {e}")
            return 50.0
    
    def _calculate_recency_score(self, level: Dict) -> float:
        """
        Calculate recency score
        
        Args:
            level: Level dictionary
            
        Returns:
            Recency score (0-100)
        """
        try:
            timestamp = level.get('timestamp', time.time())
            current_time = time.time()
            
            # Calculate age in hours
            age_hours = (current_time - timestamp) / 3600
            
            # Score based on age (newer is better)
            if age_hours < 1:
                return 100.0
            elif age_hours < 6:
                return 80.0
            elif age_hours < 24:
                return 60.0
            elif age_hours < 72:
                return 40.0
            elif age_hours < 168:  # 1 week
                return 20.0
            else:
                return 0.0
                
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
            
            # Convert back to 0-100 range
            normalized_score = min(100.0, max(0.0, weighted_score * 100.0))
            return normalized_score
            
        except Exception as e:
            logger.error(f"❌ Weighted score calculation failed: {e}")
            return 50.0
    
    def align_mtf_levels(self, clustered_levels: List[Dict], higher_tf_levels: List[Dict], 
                        atr_15m: float) -> List[Dict]:
        """
        Align levels across timeframes with ATR-based tolerance
        
        Args:
            clustered_levels: 5m clustered levels
            higher_tf_levels: Higher timeframe levels
            atr_15m: 15m ATR for tolerance calculation
            
        Returns:
            List of aligned levels
        """
        try:
            if not higher_tf_levels:
                return clustered_levels
            
            tolerance = atr_15m * 0.5  # Use 15m ATR for alignment tolerance
            aligned_levels = []
            
            for level in clustered_levels:
                level_price = level['level']
                mtf_matches = []
                
                # Find matching higher timeframe levels
                for htf_level in higher_tf_levels:
                    htf_price = htf_level['level']
                    if abs(htf_price - level_price) <= tolerance:
                        mtf_matches.append({
                            'level': htf_price,
                            'timeframe': htf_level.get('timeframe', 'unknown'),
                            'distance': abs(htf_price - level_price)
                        })
                
                # Add MTF information to level
                if mtf_matches:
                    level['mtf_matches'] = mtf_matches
                    level['mtf_count'] = len(mtf_matches)
                    level['mtf_confidence'] = self._calculate_mtf_confidence(mtf_matches)
                    level['multi_tf'] = True
                else:
                    level['mtf_matches'] = []
                    level['mtf_count'] = 0
                    level['mtf_confidence'] = 0.0
                    level['multi_tf'] = False
                
                aligned_levels.append(level)
            
            logger.debug(f"📊 Aligned {len(aligned_levels)} levels with MTF")
            return aligned_levels
            
        except Exception as e:
            logger.error(f"❌ MTF alignment failed: {e}")
            return clustered_levels
    
    def _calculate_mtf_confidence(self, mtf_matches: List[Dict]) -> float:
        """
        Calculate MTF confidence based on timeframe importance
        
        Args:
            mtf_matches: List of MTF matches
            
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
            
            if total_weight > 0:
                return min(1.0, weighted_confidence / total_weight)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"❌ MTF confidence calculation failed: {e}")
            return 0.0
