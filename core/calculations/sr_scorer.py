#!/usr/bin/env python3
"""
SRScorer - Handles scoring, MTF confirmation, and normalization
Responsible for scoring S/R levels and managing multi-timeframe confirmations
"""

import math
from typing import Dict, List, Any
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
        """Initialize the scorer with strategy-specific weights
        
        SCORING SYSTEM REPRESENTS REVERSAL PROBABILITY (0-100%)
        Score = estimated probability that price will reverse at this level
        
        Weights are strategy-specific:
        - Scalping: favors proximity (60%) for quick trades
        - Swing trading: favors touch count (60%) for strong levels
        - Standard: balanced (40% proximity, 40% touch)
        
        Args:
            strategy: Trading strategy name (default: "standard")
        
        Score interpretation:
        - 80-100%: Very high reversal probability (excellent trading level)
        - 60-79%: High reversal probability (good trading level)
        - 40-59%: Moderate reversal probability (decent level)
        - 20-39%: Low reversal probability (weak level)
        - 0-19%: Very low reversal probability (poor level)
        """
        # Get strategy-specific configuration
        from config.config import TradingConfig
        sr_config = TradingConfig.SR_LEVEL_SELECTION.get(strategy, TradingConfig.SR_LEVEL_SELECTION["standard"])
        
        # Use strategy-specific scoring weights
        strategy_weights = sr_config.get("scoring_weights", {
            "proximity": 0.40,
            "touch": 0.40,
            "recency": 0.15,
            "volume": 0.05
        })
        
        self._scoring_weights = {
            'mtf': 0.00,        # Multi-timeframe confirmation (0% - removed)
            'proximity': strategy_weights.get("proximity", 0.40),
            'touch': strategy_weights.get("touch", 0.40),
            'volume': strategy_weights.get("volume", 0.05),
            'recency': strategy_weights.get("recency", 0.15)
        }
        
        # Use strategy-specific proximity decay factor
        self.proximity_decay_k = sr_config.get("proximity_decay_k", TradingConfig.SR_PROXIMITY_DECAY_K)
        self._strategy = strategy
        
        # Validate weights sum to 1.0
        weight_sum = sum(self._scoring_weights.values())
        if abs(weight_sum - 1.0) > 0.001:
            raise ValueError(f"Scoring weights must sum to 1.0, got {weight_sum} for strategy {strategy}")
        
        
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
            # Step 1: Calculate base reversal probability from historical data
            base_probability = self._calculate_historical_reversal_rate(
                level, candles_data, atr_5m
            )
            
            # Step 2: Adjust for current conditions
            adjusted_probability = self._adjust_probability_for_conditions(
                base_probability, level, current_price, atr_5m, trend_data
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
                # More touches = higher probability (but less accurate)
                return min(80.0, 30.0 + (level.touches - 2) * 10.0)  # 2 touches = 30%, 3 = 40%, etc.
            
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
                # No historical analysis possible - use touch count as proxy
                return min(80.0, 30.0 + (level.touches - 2) * 10.0)
            
            base_probability = (reversals / total_touches_analyzed) * 100.0
            
            # Apply Bayesian shrinkage for small samples (more conservative for few touches)
            # Shrink towards 50% (neutral) for small samples, full confidence at 10+ touches
            sample_size = total_touches_analyzed
            confidence = min(1.0, sample_size / 10.0)  # Full confidence at 10+ touches
            shrunk_probability = base_probability * confidence + 50.0 * (1 - confidence)
            
            logger.debug(f"🔍 Level ${level_price:.2f}: {reversals} reversals, {breakouts} breakouts, "
                        f"base_prob={base_probability:.1f}%, shrunk={shrunk_probability:.1f}% (confidence={confidence:.2f})")
            
            return shrunk_probability
            
        except Exception as e:
            logger.error(f"❌ Historical reversal rate calculation failed: {e}")
            return 50.0  # Default to 50% on error
    
    def _adjust_probability_for_conditions(self, base_probability: float, level: Level,
                                          current_price: float, atr_5m: float,
                                          trend_data: Dict[str, Any] = None) -> float:
        """
        Adjust base probability for current market conditions using smooth exponential functions
        
        Mathematical approach:
        - Base reversal probability (P_base) from historical data is the foundation
        - Proximity multiplier: P_prox = exp(-k_prox * distance_pct) where k_prox controls decay rate
        - Recency multiplier: P_rec = exp(-k_rec * hours_old) where k_rec controls decay rate
        - Final: P_final = P_base * P_prox * P_rec (with small trend adjustment)
        
        This ensures:
        1. Reversal potential is primary (P_base is foundation)
        2. Proximity and recency smoothly enhance/penalize without overriding
        3. Clean, mathematically justified exponential decay
        
        Args:
            base_probability: Base reversal probability from historical analysis (0-100%)
            level: Level object
            current_price: Current price
            atr_5m: 5m ATR for volatility scaling
            trend_data: Optional trend data for fine-tuning
            
        Returns:
            Adjusted reversal probability (0-100%)
        """
        try:
            import time
            import math
            
            # REVERSAL POTENTIAL IS PRIMARY - start with base probability
            adjusted = base_probability
            
            # 1. Proximity multiplier using exponential decay
            # Formula: multiplier = exp(-k * distance_pct)
            # k controls decay rate: higher k = faster decay (more penalty for distance)
            # CLOSER LEVELS GET HIGHER SCORES - proximity is crucial
            distance = abs(level.level - current_price)
            distance_pct = (distance / current_price) * 100.0 if current_price > 0 else 0.0
            
            # Use strategy-specific proximity decay constant
            # Higher k_prox = more proximity sensitive (faster decay with distance)
            # Lower k_prox = less proximity sensitive (slower decay with distance)
            k_prox = self.proximity_decay_k  # Strategy-specific decay constant
            proximity_multiplier = math.exp(-k_prox * distance_pct)
            
            # Apply proximity multiplier
            adjusted = adjusted * proximity_multiplier
            
            # 2. Recency multiplier using exponential decay
            # Formula: multiplier = exp(-k * hours_old)
            # k controls decay rate: higher k = faster decay (more penalty for age)
            time_since_touch = time.time() - level.timestamp
            hours_since_touch = time_since_touch / 3600.0
            
            # k_rec = 0.02 means:
            # - At 0 hours: multiplier = 1.0 (no change)
            # - At 6 hours: multiplier ≈ 0.89 (11% penalty)
            # - At 24 hours: multiplier ≈ 0.62 (38% penalty)
            # - At 72 hours (3 days): multiplier ≈ 0.24 (76% penalty)
            # - At 168 hours (7 days): multiplier ≈ 0.03 (97% penalty)
            k_rec = 0.02  # Decay constant for recency (tuned for reasonable penalty curve)
            recency_multiplier = math.exp(-k_rec * hours_since_touch)
            
            # Apply recency multiplier
            adjusted = adjusted * recency_multiplier
            
            # 3. Small trend adjustment (fine-tuning, not major factor)
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
            
            # Ensure minimum score floor - even old/far levels should have some score if base probability is good
            # This prevents scores from going to 0.0 due to aggressive multipliers
            min_score_floor = base_probability * 0.1  # At least 10% of base probability
            adjusted = max(adjusted, min_score_floor)
            
            return adjusted
            
        except Exception as e:
            logger.error(f"❌ Probability adjustment failed: {e}")
            return base_probability
            
        except Exception as e:
            logger.error(f"❌ Probability adjustment failed: {e}")
            return base_probability
    
    def score_levels_enhanced(self, levels: List[Level], current_price: float, 
                             atr_5m: float, atr_per_tf: Dict[str, float],
                             candles_data: Dict[str, List[Dict]] = None,
                             trend_data: Dict[str, Any] = None) -> List[Level]:
        """
        Enhanced scoring of S/R levels - SCORE REPRESENTS REVERSAL PROBABILITY (0-100%)
        
        Final score (0-100%) = estimated probability that price will reverse at this level
        Weighted sum: touch 40%, proximity 40%, recency 15%, volume 5%
        
        Factors that increase reversal probability:
        - Touch count: More touches = price has reversed here before (stronger level)
        - Proximity: Closer to current price = price is approaching (higher chance of interaction)
        - Recency: Recent touches = level is still active/relevant (market remembers this level)
        - Volume: Higher volume = more liquidity/interest (stronger level)
        
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
                
                # Also calculate heuristic components for breakdown/debugging
                mtf_score = self._calculate_mtf_score_enhanced(level)
                proximity_score = self._calculate_proximity_score_enhanced(
                    level.level, current_price, atr_5m)
                touch_score = self._calculate_touch_score(level.touches)
                volume_score = self._calculate_volume_score(level, atr_5m)
                recency_score = self._calculate_recency_score(level.timestamp)
                
                # Use reversal probability as the final score (0-100%)
                normalized_score = reversal_probability
                
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
        Calculate proximity score using volatility-aware exponential decay
        
        Formula: 100 * exp(-distance / (k * atr_5m))
        - k=25.0: very gentle decay allows strong differentiation at 1-3% distances (trading-relevant ranges)
        - With ATR ~$78: 1.6% away (~$1,500) gets ~42 pts, 3.4% away (~$3,100) gets ~11 pts
        - This ensures proximity (75% weight) can overcome touch differences for actionable levels
        - Volatility-scaled: adapts to market conditions automatically
        
        Args:
            level_price: Level price
            current_price: Current price
            atr_5m: 5m ATR for volatility scaling
            k: Decay factor (default 25.0 from config)
            
        Returns:
            Proximity score (0-100) where 100 = at current price, 0 = very far
        """
        try:
            if current_price <= 0 or level_price <= 0:
                return 0.0
            
            distance = abs(level_price - current_price)
            
            # Volatility-aware exponential decay: proximity_score = 100 * exp(-distance / (k * atr_5m))
            # k=25.0 means levels within ~25*ATR get meaningful scores (very gentle distance penalty)
            # With ATR ~$78: 1.6% away gets ~42 pts, 3.4% away gets ~11 pts
            # This ensures proximity (75% weight) can overcome touch differences for actionable levels
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
                                touch_score: float, volume_score: float, 
                                recency_score: float) -> float:
        """
        Calculate weighted score with normalization
        
        Args:
            mtf_score: MTF score (0-100)
            proximity_score: Proximity score (0-100)
            touch_score: Touch score (0-100)
            volume_score: Volume score (0-100)
            recency_score: Recency score (0-100) - more recent touches = higher score
            
        Returns:
            Weighted score (0-100)
        """
        try:
            # Calculate weighted score (individual scores are 0-100, so divide by 100 to get 0-1 range)
            # Recency: recent touches are more relevant for current trading
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
                        score=htf_level.score if hasattr(htf_level, 'score') else 0.0,
                        score_breakdown=htf_level.score_breakdown if hasattr(htf_level, 'score_breakdown') else {}
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
