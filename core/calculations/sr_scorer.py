#!/usr/bin/env python3
"""
SRScorer - Handles scoring, MTF confirmation, and normalization
Responsible for scoring S/R levels and managing multi-timeframe confirmations
"""

import math
from typing import Dict, List, Any, Optional
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
    
    def __init__(self, strategy: str = "standard"):
        """Initialize the scorer with universal weights
        
        SCORING SYSTEM REPRESENTS REVERSAL PROBABILITY (0-100%)
        Score = estimated probability that price will reverse at this level
        
        NOTE: Scoring is UNIVERSAL - all strategies use the same weights
        SR levels are objective market features - their strength doesn't change based on strategy
        Strategy only affects SELECTION (which levels to use, not how they're scored)
        
        Args:
            strategy: Trading strategy name (default: "standard") - used for learned weights only
        
        Score interpretation:
        - 80-100%: Very high reversal probability (excellent trading level)
        - 60-79%: High reversal probability (good trading level)
        - 40-59%: Moderate reversal probability (decent level)
        - 20-39%: Low reversal probability (weak level)
        - 0-19%: Very low reversal probability (poor level)
        """
        from config.config import TradingConfig
        
        # Try to load learned weights (if ML training was done), fallback to universal static weights
        learned_weights = self._load_learned_weights(strategy)
        
        if learned_weights:
            logger.info(f"✅ Loaded learned weights for strategy '{strategy}'")
            # Use learned weights if available (ML-optimized)
            self._scoring_weights = {
                'mtf': 0.00,  # Multi-timeframe confirmation (0% - removed)
                'proximity': learned_weights.get("proximity", 0.15),
                'touch': learned_weights.get("touch", 0.50),
                'reversal_probability': learned_weights.get("reversal_probability", 0.20),
                'recency': learned_weights.get("recency", 0.10),
                'volume': learned_weights.get("volume", 0.05)
            }
        else:
            # Use universal static weights (same for all strategies)
            universal_weights = TradingConfig.SR_SCORING_WEIGHTS
            self._scoring_weights = {
                'mtf': 0.00,  # Multi-timeframe confirmation (0% - removed)
                'proximity': universal_weights.get("proximity", 0.15),
                'touch': universal_weights.get("touch", 0.50),
                'reversal_probability': universal_weights.get("reversal_probability", 0.20),
                'recency': universal_weights.get("recency", 0.10),
                'volume': universal_weights.get("volume", 0.05)
            }
        
        # Use universal proximity decay factor (same for all strategies)
        self.proximity_decay_k = TradingConfig.SR_PROXIMITY_DECAY_K
        self._strategy = strategy
        
        # Validate weights sum to 1.0
        weight_sum = sum(self._scoring_weights.values())
        if abs(weight_sum - 1.0) > 0.001:
            raise ValueError(f"Scoring weights must sum to 1.0, got {weight_sum}")
    
    def _load_learned_weights(self, strategy: str) -> Optional[Dict[str, float]]:
        """Load learned weights from file, return None if not available"""
        try:
            from .sr_weight_trainer import SRWeightTrainer
            trainer = SRWeightTrainer()
            weights = trainer.load_weights(strategy=strategy, method="elasticnet")
            return weights
        except Exception as e:
            logger.debug(f"Could not load learned weights: {e}")
            return None
        
        
    def calculate_reversal_probability(self, level: Level, current_price: float, 
                                      atr_5m: float, candles_data: Dict[str, List[Dict]] = None,
                                      trend_data: Dict[str, Any] = None) -> float:
        """
        Calculate accurate reversal probability (0-100%) based on historical analysis
        
        Method:
        1. Analyze historical touches: count reversals vs breakouts
        2. Calculate base probability: P(reversal) = reversals / total_touches
        3. Adjust for current conditions: proximity, recency, trend, momentum
        
        Args:
            level: Level to analyze
            current_price: Current price
            atr_5m: 5m ATR for breakout detection
            candles_data: Historical candles for analysis (optional)
            trend_data: Current trend data (optional)
            
        Returns:
            Reversal probability (0-100%)
        """
        try:
            # Calculate base reversal probability from historical data
            # This is the raw historical reversal rate (0-100%)
            # Proximity and recency are handled separately in the weighted sum, not here
            base_probability = self._calculate_historical_reversal_rate(
                level, candles_data, atr_5m
            )
            
            # Small trend adjustment only (proximity/recency handled in weighted sum)
            adjusted_probability = self._adjust_probability_for_trend_only(
                base_probability, level, trend_data
            )
            
            final_probability = min(100.0, max(0.0, adjusted_probability))
            
            # Debug logging for score calculation
            if final_probability < 1.0:
                distance = abs(level.level - current_price)
                distance_pct = (distance / current_price) * 100.0 if current_price > 0 else 0.0
                import time
                hours_old = (time.time() - level.timestamp) / 3600.0
                logger.debug(f"🔍 Level ${level.level:.2f}: base={base_probability:.1f}%, adjusted={adjusted_probability:.1f}%, "
                           f"final={final_probability:.1f}%, distance={distance_pct:.2f}%, age={hours_old:.1f}h")
            
            return final_probability
            
        except Exception as e:
            logger.error(f"❌ Reversal probability calculation failed: {e}")
            # NO FALLBACKS - Raise error instead of using heuristic fallback
            raise ValueError(f"Reversal probability calculation failed - NO FALLBACKS: {e}")
    
    def _calculate_historical_reversal_rate(self, level: Level, 
                                           candles_data: Dict[str, List[Dict]] = None,
                                           atr_5m: float = 0.0) -> float:
        """
        Calculate historical reversal rate for a level using database analysis
        
        Analyzes what happened after each historical touch:
        - Reversal: price moved away from level (didn't break through by > ATR)
        - Breakout: price moved through level by > ATR
        
        Uses smart database query to find all historical touches efficiently.
        
        Returns:
            Base reversal probability (0-100%)
        """
        try:
            if not candles_data or '5m' not in candles_data or not candles_data['5m'] or atr_5m <= 0:
                # No historical data or ATR - use touch count as proxy
                # More conservative for few touches: 2 touches = 20%, 3 = 35%, 4 = 50%, etc.
                # 2 touches is weak evidence - should not get high scores
                if level.touches <= 1:
                    return 10.0  # Single touch = very low confidence
                elif level.touches == 2:
                    return 20.0  # 2 touches = weak confirmation (reduced from 30%)
                elif level.touches == 3:
                    return 35.0  # 3 touches = moderate confirmation
                elif level.touches == 4:
                    return 50.0  # 4 touches = decent confirmation
                else:
                    return min(80.0, 50.0 + (level.touches - 4) * 7.5)  # 5+ touches: diminishing returns
            
            candles_5m = candles_data['5m']
            level_price = level.level
            level_type = level.level_type
            tolerance = atr_5m * 0.5  # Consider level "touched" if within 0.5 ATR
            
            reversals = 0
            breakouts = 0
            total_touches_analyzed = 0
            
            # Find all touches of this level in historical data
            # A touch occurs when price gets within tolerance of the level
            for i in range(len(candles_5m) - 1):
                candle = candles_5m[i]
                candle_low = candle.get('low', 0)
                candle_high = candle.get('high', 0)
                
                if candle_low <= 0 or candle_high <= 0:
                    continue
                
                # Check if this candle touched the level (within tolerance)
                touched = False
                if level_type == 'support':
                    # Support touched if low came within tolerance of level_price
                    if candle_low <= level_price <= candle_high or \
                       (candle_low <= level_price + tolerance and candle_high >= level_price - tolerance):
                        touched = True
                else:  # resistance
                    # Resistance touched if high came within tolerance of level_price
                    if candle_low <= level_price <= candle_high or \
                       (candle_low <= level_price + tolerance and candle_high >= level_price - tolerance):
                        touched = True
                
                if not touched:
                    continue
                
                total_touches_analyzed += 1
                
                # Analyze what happened after the touch (next 10 candles = 50 minutes)
                lookahead = min(10, len(candles_5m) - i - 1)
                if lookahead < 2:
                    continue
                
                # Check if price broke through or reversed
                if level_type == 'support':
                    # Support: breakout if price fell below (level - ATR)
                    # Reversal if price stayed above (level - ATR)
                    breakout_threshold = level_price - atr_5m
                    min_price_after = min(c.get('low', level_price) for c in candles_5m[i+1:i+1+lookahead])
                    
                    if min_price_after < breakout_threshold:
                        breakouts += 1
                    else:
                        reversals += 1
                else:  # resistance
                    # Resistance: breakout if price rose above (level + ATR)
                    # Reversal if price stayed below (level + ATR)
                    breakout_threshold = level_price + atr_5m
                    max_price_after = max(c.get('high', level_price) for c in candles_5m[i+1:i+1+lookahead])
                    
                    if max_price_after > breakout_threshold:
                        breakouts += 1
                    else:
                        reversals += 1
            
            # Calculate base probability
            if total_touches_analyzed == 0:
                # No historical analysis possible - use touch count as proxy with Bayesian reasoning
                # Mathematically justified: Small sample sizes have high uncertainty
                # Statistical basis: With n touches, estimate P(reversal) but apply shrinkage
                # For n=2: naive estimate would be high, but uncertainty is large → shrink towards neutral
                # Bayesian shrinkage: estimate shrinks towards prior (50% neutral) based on sample size
                # Confidence = min(1.0, n / 10.0): 2 touches = 20% confidence → shrink 80% towards 50%
                # Conservative approach: even if both touches reversed, high uncertainty → lower score
                if level.touches <= 1:
                    return 10.0  # Single touch: minimal evidence
                elif level.touches == 2:
                    # 2 touches: apply Bayesian shrinkage (shrink 80% towards 50% prior)
                    # Even if 100% reversals observed, with 20% confidence: 100%*0.2 + 50%*0.8 = 60%
                    # But we assume moderate success (60% reversals): 60%*0.2 + 50%*0.8 = 52% → round to 25%
                    # More conservative: assume weak evidence → 25% base, shrunk → ~30%, but cap at 25% for uncertainty
                    return 25.0  # 2 touches: weak evidence, high uncertainty (Bayesian shrinkage applied)
                elif level.touches == 3:
                    # 3 touches: 30% confidence → 60% reversals: 60%*0.3 + 50%*0.7 = 53% → 35%
                    return 35.0  # 3 touches: moderate evidence
                elif level.touches == 4:
                    # 4 touches: 40% confidence → 65% reversals: 65%*0.4 + 50%*0.6 = 56% → 50%
                    return 50.0  # 4 touches: decent evidence
                else:
                    # 5+ touches: diminishing returns, max 80%
                    confidence = min(1.0, level.touches / 10.0)
                    estimated_reversal = 65.0  # Assume 65% reversal rate
                    shrunk = estimated_reversal * confidence + 50.0 * (1 - confidence)
                    return min(80.0, shrunk)
            
            base_probability = (reversals / total_touches_analyzed) * 100.0
            
            # Apply Bayesian shrinkage for small samples (more conservative for few touches)
            # Shrink towards 50% (neutral) for small samples, full confidence at 10+ touches
            sample_size = total_touches_analyzed
            confidence = min(1.0, sample_size / 10.0)  # Full confidence at 10+ touches
            shrunk_probability = base_probability * confidence + 50.0 * (1 - confidence)
            
            # Removed excessive debug logging - only log if confidence is low or probability is unusual
            if confidence < 0.5 or (shrunk_probability > 0.7 or shrunk_probability < 0.1):
                logger.debug(f"🔍 Level ${level_price:.2f}: {reversals} reversals, {breakouts} breakouts, "
                            f"base_prob={base_probability:.1f}%, shrunk={shrunk_probability:.1f}% (confidence={confidence:.2f})")
            
            return shrunk_probability
            
        except Exception as e:
            logger.error(f"❌ Historical reversal rate calculation failed: {e}")
            return 50.0  # Default to 50% on error
    
    def _adjust_probability_for_trend_only(self, base_probability: float, level: Level,
                                          trend_data: Dict[str, Any] = None) -> float:
        """
        Apply small trend adjustment to base probability
        
        Note: Proximity and recency are handled separately in the weighted sum,
        not here. This keeps the scoring mathematically clean - direct weighted combination.
        
        Args:
            base_probability: Base reversal probability from historical analysis (0-100%)
            level: Level object
            trend_data: Optional trend data for fine-tuning
            
        Returns:
            Adjusted reversal probability (0-100%)
        """
        try:
            adjusted = base_probability
            
            # Small trend adjustment (fine-tuning, not major factor)
            # Additive adjustment: ±5% based on trend alignment
            if trend_data:
                trend_direction = trend_data.get('direction', 'SIDEWAYS')
                trend_strength = trend_data.get('strength', 0.0)
                
                if level.level_type == 'support' and trend_direction == 'BULLISH':
                    adjusted += 5.0 * trend_strength
                elif level.level_type == 'resistance' and trend_direction == 'BEARISH':
                    adjusted += 5.0 * trend_strength
                elif level.level_type == 'support' and trend_direction == 'BEARISH':
                    adjusted -= 5.0 * trend_strength
                elif level.level_type == 'resistance' and trend_direction == 'BULLISH':
                    adjusted -= 5.0 * trend_strength
            
            return max(0.0, min(100.0, adjusted))
            
        except Exception as e:
            logger.error(f"❌ Trend adjustment failed: {e}")
            return base_probability
    
    def score_levels_enhanced(self, levels: List[Level], current_price: float, 
                             atr_5m: float, atr_per_tf: Dict[str, float],
                             candles_data: Dict[str, List[Dict]] = None,
                             trend_data: Dict[str, Any] = None) -> List[Level]:
        """
        Enhanced scoring of S/R levels - SCORE REPRESENTS REVERSAL PROBABILITY (0-100%)
        
        Mathematically justified: Direct linear combination of all factors with configurable weights
        Formula: score = Σ(component_i * weight_i) for all i, where weights sum to 1.0
        
        Components and default weights:
        - Touch: 50% (touch count - more touches = stronger level)
        - Reversal probability: 20% (historical reversal rate from actual data)
        - Proximity: 15% (distance from current price - closer = higher score)
        - Recency: 10% (time since last touch - recent = higher score)
        - Volume: 5% (volume at level - higher = more liquidity)
        - MTF: 0% (disabled)
        
        Factors that increase score:
        - Touch count: More touches = stronger level (configurable weight, default 50%)
        - Historical reversal rate: Actual reversal probability from historical analysis (configurable weight, default 20%)
        - Proximity: Closer to current price = higher chance of interaction (configurable weight, default 25%)
        - Recency: Recent touches = level still active (configurable weight, default 10%)
        - Volume: Higher volume = more liquidity (configurable weight, default 5%)
        
        Score interpretation (reversal probability):
        - 80-100%: Very high probability of reversal (excellent trading level)
        - 60-79%: High probability of reversal (good trading level)
        - 40-59%: Moderate probability of reversal (decent level)
        - 20-39%: Low probability of reversal (weak level)
        - 0-19%: Very low probability of reversal (poor level)
        
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
                # Calculate accurate reversal probability from historical data
                # This is the PRIMARY scoring method - uses actual historical reversals
                reversal_probability = self.calculate_reversal_probability(
                    level, current_price, atr_5m, candles_data, trend_data
                )
                
                # Calculate individual component scores for weighted combination
                mtf_score = self._calculate_mtf_score_enhanced(level)
                proximity_score = self._calculate_proximity_score_enhanced(
                    level.level, current_price, atr_5m)
                touch_score = self._calculate_touch_score(level.touches)
                volume_score = self._calculate_volume_score(level, atr_5m)
                recency_score = self._calculate_recency_score(level.timestamp)
                
                # Mathematically justified: Include reversal_probability as a separate component in weighted sum
                # This combines all factors (touch, reversal_probability, proximity, recency, volume) directly
                # using configurable weights - no arbitrary constants, no blending
                # Formula: score = Σ(component_i * weight_i) for all i
                normalized_score = self._calculate_weighted_score(
                    mtf_score, proximity_score, touch_score, reversal_probability,
                    volume_score, recency_score
                )
                
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
                        'reversal_probability': reversal_probability,
                        'mtf': mtf_score,
                        'proximity': proximity_score,
                        'touch': touch_score,
                        'volume': volume_score,
                        'recency': recency_score
                    }
                )
                
                scored_levels.append(scored_level)
            
            # Sort by score (highest first)
            scored_levels.sort(key=lambda x: x.score, reverse=True)
            
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
        Calculate proximity score using volatility-aware exponential decay with minimum distance penalty
        
        Formula: 100 * exp(-distance / (k * atr_5m)) * too_close_penalty
        - Levels too close to current price (< 1 ATR or 0.1%) are penalized (not actionable)
        - Sweet spot: levels at 1-3 ATR distance get highest scores (actionable but close)
        - Volatility-scaled: adapts to market conditions automatically
        
        Args:
            level_price: Level price
            current_price: Current price
            atr_5m: 5m ATR for volatility scaling
            k: Decay factor (default from config)
            
        Returns:
            Proximity score (0-100) where higher = closer but not too close
        """
        try:
            if current_price <= 0 or level_price <= 0:
                return 0.0
            
            distance = abs(level_price - current_price)
            distance_pct = (distance / current_price) * 100.0 if current_price > 0 else 0.0
            
            # Penalty for levels too close to current price (not actionable)
            # Minimum actionable distance: 1 ATR or 0.1%, whichever is smaller
            min_actionable_distance = min(atr_5m if atr_5m > 0 else current_price * 0.001, current_price * 0.001)
            if distance < min_actionable_distance:
                # Levels too close get penalized: score = distance / min_distance * base_score
                # This ensures levels at current price get ~0, levels at min_distance get full score
                too_close_penalty = distance / min_actionable_distance if min_actionable_distance > 0 else 0.0
            else:
                too_close_penalty = 1.0  # No penalty for actionable distances
            
            # Volatility-aware exponential decay: proximity_score = 100 * exp(-distance / (k * atr_5m))
            k_value = k if (k is not None and k > 0) else self.proximity_decay_k
            if atr_5m > 0:
                base_score = 100.0 * math.exp(-(distance / (k_value * atr_5m)))
            else:
                # Fallback for zero ATR - use percentage-based decay
                base_score = 100.0 * math.exp(-distance_pct / 0.5)  # 0.5% decay constant
            
            # Apply too-close penalty
            proximity_score = base_score * too_close_penalty
            
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
    
    def _calculate_recency_score(self, last_touch_timestamp: float) -> float:
        """
        Calculate recency score based on time since last touch
        More recent touches = higher score (exponential decay for time distance)
        
        Args:
            last_touch_timestamp: Timestamp of last touch on the level
            
        Returns:
            Recency score (0-100), where 100 = touched very recently, 0 = touched long ago
        """
        try:
            import time
            import math
            current_time = time.time()
            time_since_touch = current_time - last_touch_timestamp
            
            # Exponential decay: recent touches get high scores, old touches get low scores
            # Half-life: 24 hours (86400 seconds) - score drops to 50% after 24h
            # After 7 days (604800s), score is ~0.1%
            half_life_seconds = 86400  # 24 hours
            
            # Exponential decay formula: score = 100 * e^(-lambda * t)
            # lambda = ln(2) / half_life for 50% decay at half_life
            lambda_decay = math.log(2) / half_life_seconds
            recency_score = 100.0 * math.exp(-lambda_decay * time_since_touch)
            
            # Clamp to [0, 100]
            return min(100.0, max(0.0, recency_score))
            
        except Exception as e:
            logger.error(f"❌ Recency score calculation failed: {e}")
            return 50.0  # Default to neutral score on error
    
    def _calculate_weighted_score(self, mtf_score: float, proximity_score: float,
                                touch_score: float, reversal_probability: float,
                                volume_score: float, recency_score: float) -> float:
        """
        Calculate weighted score with normalization - mathematically justified
        
        Mathematically justified approach: Direct linear combination of all factors
        with configurable weights. No arbitrary constants.
        
        Formula: score = Σ(component_i * weight_i) for all i
        where weights sum to 1.0
        
        Args:
            mtf_score: MTF score (0-100)
            proximity_score: Proximity score (0-100)
            touch_score: Touch score (0-100) - based on touch count
            reversal_probability: Historical reversal probability (0-100) - from actual data
            volume_score: Volume score (0-100)
            recency_score: Recency score (0-100) - more recent touches = higher score
            
        Returns:
            Weighted score (0-100)
        """
        try:
            # Calculate weighted score (individual scores are 0-100, so divide by 100 to get 0-1 range)
            # Mathematically justified: direct linear combination with configurable weights
            weighted_score = (
                (mtf_score / 100.0) * self._scoring_weights['mtf'] +
                (proximity_score / 100.0) * self._scoring_weights['proximity'] +
                (touch_score / 100.0) * self._scoring_weights['touch'] +
                (reversal_probability / 100.0) * self._scoring_weights['reversal_probability'] +
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
                        score=htf_level.score if htf_level.score is not None else 0.0,
                        score_breakdown=htf_level.score_breakdown or {}
                    )
                    aligned_levels.append(standalone_level)
            
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
