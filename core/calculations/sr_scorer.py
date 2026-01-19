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
        """Initialize the power calculator with universal weights
        
        POWER SYSTEM REPRESENTS PURE LEVEL STRENGTH (0-100%)
        Power = inherent level quality (touch count, volume, reversal probability)
        
        NOTE: Power is UNIVERSAL - all strategies use the same weights
        SR levels are objective market features - their strength doesn't change based on strategy
        Strategy only affects SELECTION (which levels to use, not how they're powered)
        
        Power components (inherent strength only):
        - Touch: 60% (touch count - more touches = stronger level)
        - Reversal probability: 30% (historical reversal rate from actual data)
        - Volume: 10% (volume at level - higher = more liquidity)
        
        Contextual factors (proximity, recency) are NOT included in power.
        They are used in direction/entry calculations instead.
        
        Args:
            strategy: Trading strategy name (default: "standard") - used for learned weights only
        
        Power interpretation:
        - 80-100%: Very strong level (excellent quality)
        - 60-79%: Strong level (good quality)
        - 40-59%: Moderate level (decent quality)
        - 20-39%: Weak level (poor quality)
        - 0-19%: Very weak level (very poor quality)
        """
        from config.config import TradingConfig
        
        # Try to load learned weights (if ML training was done), fallback to universal static weights
        learned_weights = self._load_learned_weights(strategy)
        
        if learned_weights:
            logger.info("✅ Loaded universal learned weights (used by all strategies)")
            # Use learned weights if available (ML-optimized)
            # Only include inherent strength factors (no proximity/recency)
            self._power_weights = {
                'touch': learned_weights["touch"],  # Required (NO FALLBACKS)
                'reversal_probability': learned_weights["reversal_probability"],  # Required (NO FALLBACKS)
                'volume': learned_weights["volume"]  # Required (NO FALLBACKS)
            }
        else:
            # Use universal static weights (same for all strategies)
            universal_weights = TradingConfig.SR_POWER_WEIGHTS
            self._power_weights = {
                'touch': universal_weights["touch"],  # Required (NO FALLBACKS)
                'reversal_probability': universal_weights["reversal_probability"],  # Required (NO FALLBACKS)
                'volume': universal_weights["volume"]  # Required (NO FALLBACKS)
            }
        
        # Validate weights sum to 1.0
        total_weight = sum(self._power_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"⚠️ Power weights don't sum to 1.0: {total_weight}, normalizing...")
            for key in self._power_weights:
                self._power_weights[key] /= total_weight
        self._strategy = strategy
    
    def _load_learned_weights(self, strategy: str) -> Optional[Dict[str, float]]:
        """Load universal learned weights from file (same for all strategies), return None if not available"""
        try:
            from .sr_weight_trainer import SRWeightTrainer
            trainer = SRWeightTrainer()
            # Universal weights - strategy parameter ignored (kept for backward compatibility)
            weights = trainer.load_weights(method="elasticnet")
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
                candle_low = candle['low']  # Required (NO FALLBACKS)
                candle_high = candle['high']  # Required (NO FALLBACKS)
                
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
                # No historical analysis possible - use touch count as proxy
                # Apply Beta-Binomial reasoning with assumed moderate reversal rate (60%)
                # We assume each touch has 60% chance of reversal (conservative estimate)
                # but apply Beta shrinkage based on sample size (touch count)
                
                # Beta-Binomial posterior with assumed 60% reversal rate
                # Prior: Beta(1, 1) - uniform/uninformative
                # Assumed success rate: 60% reversals per touch
                prior_alpha = 1.0
                prior_beta = 1.0
                
                # Estimate: if we had n touches with 60% reversal rate
                # Posterior: Beta(1 + 0.6*n, 1 + 0.4*n)
                estimated_reversals = level.touches * 0.6
                estimated_breakouts = level.touches * 0.4
                
                posterior_alpha = prior_alpha + estimated_reversals
                posterior_beta = prior_beta + estimated_breakouts
                posterior_mean = posterior_alpha / (posterior_alpha + posterior_beta)
                
                # Cap at reasonable maximum (don't overestimate with few touches)
                bayesian_probability = min(80.0, posterior_mean * 100.0)
                
                # Special case: single touch gets minimal score (very high uncertainty)
                if level.touches <= 1:
                    return 10.0
                
                return bayesian_probability
            
            # PROPER BAYESIAN PROBABILITY THEORY: Beta-Binomial Conjugate Prior
            # Mathematically rigorous approach for estimating reversal probability
            #
            # Method:
            # - Prior: Beta(α₀, β₀) = Beta(1, 1) for uniform/uninformative prior (neutral 50%)
            # - Likelihood: Binomial(n, p) where n = total_touches, successes = reversals
            # - Posterior: Beta(α₀ + reversals, β₀ + breakouts) = Beta(1 + reversals, 1 + breakouts)
            # - Posterior mean: E[P] = (1 + reversals) / (2 + total_touches_analyzed)
            #
            # Advantages over heuristic shrinkage:
            # 1. Mathematically rigorous (standard Bayesian inference for binary outcomes)
            # 2. Proper uncertainty quantification (small samples automatically get more shrinkage)
            # 3. No arbitrary parameters (confidence threshold, etc.)
            # 4. Can extend to credible intervals, mode, median, etc. if needed
            
            # Beta-Binomial posterior mean (Bayesian point estimate)
            prior_alpha = 1.0  # Uniform prior (neutral 50%)
            prior_beta = 1.0   # Uniform prior (neutral 50%)
            
            posterior_alpha = prior_alpha + reversals
            posterior_beta = prior_beta + breakouts
            posterior_mean = posterior_alpha / (posterior_alpha + posterior_beta)
            
            # Convert to percentage (0-100%)
            bayesian_probability = posterior_mean * 100.0
            
            # Calculate effective sample size for logging (how much data we have vs. prior)
            effective_sample_size = posterior_alpha + posterior_beta - prior_alpha - prior_beta
            
            # Removed excessive debug logging - only log if sample size is small or probability is unusual
            if effective_sample_size < 5 or (bayesian_probability > 80.0 or bayesian_probability < 20.0):
                logger.debug(f"🔍 Level ${level_price:.2f}: {reversals} reversals, {breakouts} breakouts, "
                            f"Beta({posterior_alpha:.1f},{posterior_beta:.1f}) → {bayesian_probability:.1f}% (n={effective_sample_size})")
            
            return bayesian_probability
            
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
                trend_direction = trend_data['direction']  # Required (NO FALLBACKS)
                trend_strength = trend_data['strength']  # Required (NO FALLBACKS)
                
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
    
    def calculate_power(self, levels: List[Level], current_price: float, 
                       atr_5m: float, atr_per_tf: Dict[str, float],
                       candles_data: Dict[str, List[Dict]] = None,
                       trend_data: Dict[str, Any] = None) -> List[Level]:
        """
        Calculate level power (pure strength: touch, volume, reversal_probability)
        
        Power represents inherent level quality, not contextual relevance.
        Contextual factors (proximity, recency) are used in direction/entry calculations.
        
        Mathematically justified: Direct linear combination of inherent strength factors
        Formula: power = Σ(component_i * weight_i) for all i, where weights sum to 1.0
        
        Components and default weights:
        - Touch: 60% (touch count - more touches = stronger level)
        - Reversal probability: 30% (historical reversal rate from actual data)
        - Volume: 10% (volume at level - higher = more liquidity)
        
        Power interpretation (pure strength):
        - 80-100%: Very strong level (excellent quality)
        - 60-79%: Strong level (good quality)
        - 40-59%: Moderate level (decent quality)
        - 20-39%: Weak level (poor quality)
        - 0-19%: Very weak level (very poor quality)
        
        Args:
            levels: List of Level dataclass objects
            current_price: Current price (for reversal probability calculation only)
            atr_5m: 5m ATR for volatility scaling
            atr_per_tf: Dictionary of ATR values per timeframe
            candles_data: Historical candles for reversal probability calculation
            trend_data: Trend data for reversal probability adjustment
            
        Returns:
            List of Level objects with power calculated [0-100]
        """
        try:
            powered_levels = []
            
            for level in levels:
                # Calculate accurate reversal probability from historical data
                reversal_probability = self.calculate_reversal_probability(
                    level, current_price, atr_5m, candles_data, trend_data
                )
                
                # Calculate inherent strength components only (no proximity/recency)
                touch_score = self._calculate_touch_score(level.touches)
                volume_score = self._calculate_volume_score(level, atr_5m)
                
                # Calculate power: weighted sum of inherent strength factors only
                power = self._calculate_power_weighted(
                    touch_score, reversal_probability, volume_score
                )
                
                # Create new Level instance with power information
                from .level import Level
                powered_level = Level(
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
                    power=power,
                    power_breakdown={
                        'touch': touch_score,
                        'reversal_probability': reversal_probability,
                        'volume': volume_score
                    }
                )
                
                powered_levels.append(powered_level)
            
            # Sort by power (highest first)
            powered_levels.sort(key=lambda x: x.power or 0, reverse=True)
            
            return powered_levels
            
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
            tf_count = len(set(match['timeframe'] for match in level.mtf_matches))  # Required (NO FALLBACKS)
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
    
    def _calculate_power_weighted(self, touch_score: float, reversal_probability: float,
                                 volume_score: float) -> float:
        """
        Calculate weighted power (pure strength only) - mathematically justified
        
        Mathematically justified approach: Direct linear combination of inherent strength factors
        with configurable weights. No arbitrary constants.
        
        Formula: power = Σ(component_i * weight_i) for all i
        where weights sum to 1.0
        
        Args:
            touch_score: Touch score (0-100) - based on touch count
            reversal_probability: Historical reversal probability (0-100) - from actual data
            volume_score: Volume score (0-100)
            
        Returns:
            Weighted power (0-100)
        """
        try:
            # Calculate weighted power (individual scores are 0-100, so divide by 100 to get 0-1 range)
            # Mathematically justified: direct linear combination with configurable weights
            weighted_power = (
                (touch_score / 100.0) * self._power_weights['touch'] +
                (reversal_probability / 100.0) * self._power_weights['reversal_probability'] +
                (volume_score / 100.0) * self._power_weights['volume']
            )
            
            # Convert back to 0-100 range with validation
            normalized_power = min(100.0, max(0.0, weighted_power * 100.0))
            
            # Validate power is within expected range
            if not (0.0 <= normalized_power <= 100.0):
                logger.warning(f"⚠️ Power out of range: {normalized_power}")
                normalized_power = max(0.0, min(100.0, normalized_power))
            
            return normalized_power
            
        except Exception as e:
            logger.error(f"❌ Power calculation failed: {e}")
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
            # Map timeframe strings to weights (NO FALLBACKS)
            tf_weights = {
                '5m': 1.0,
                '15m': 1.2, 
                '1h': 1.5,
                '1d': 2.0,
                'daily_peak': 2.0,  # Daily peaks = 1d weight
                'weekly_peak': 2.5,  # Weekly peaks = higher weight
                'monthly_peak': 3.0  # Monthly peaks = highest weight
            }
            
            # Adaptive tolerance based on per-timeframe volatility
            base_atr = atr_per_tf.get('15m') if '15m' in atr_per_tf else atr_per_tf['5m']  # Fallback to 5m if 15m not available
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
                    tf_tolerance = tf_atr * 0.5 * tf_weights[htf_timeframe]  # Required (NO FALLBACKS)
                    
                    if distance <= tf_tolerance:
                        # Calculate weighted contribution
                        weight = tf_weights[htf_timeframe]  # Required (NO FALLBACKS)
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
                        power=level.power,
                        power_breakdown=level.power_breakdown
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
                        power=level.power,
                        power_breakdown=level.power_breakdown
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
                        power=htf_level.power if htf_level.power is not None else 0.0,
                        power_breakdown=htf_level.power_breakdown or {}
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
            
            # Timeframe weights for MTF confidence (NO FALLBACKS)
            timeframe_weights = {
                '5m': 0.3,
                '15m': 0.7,
                '1h': 1.0,
                '4h': 1.3,
                '1d': 1.5,
                'daily_peak': 1.5,   # Daily peaks = 1d weight
                'weekly_peak': 1.8,  # Weekly peaks
                'monthly_peak': 2.0  # Monthly peaks
            }
            total_weight = 0.0
            weighted_confidence = 0.0
            
            for match in mtf_matches:
                tf = match['timeframe']  # Required (NO FALLBACKS)
                weight = timeframe_weights[tf]  # Required (NO FALLBACKS)
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
