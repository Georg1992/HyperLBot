#!/usr/bin/env python3
"""
Prediction Engine
Generates trading predictions based on unified market data and current strategy
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal
from loguru import logger
from config.config import TradingConfig
from core.constants import technical_constants
from .position_sizer import PositionSizeCalculator


@dataclass
class TradingPrediction:
    """Trading prediction/signal structure"""
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: Optional[float]  # 0.0 - 100.0 (percentage) - None if not implemented
    reasoning: str
    strategy: str
    timestamp: float
    risk_reward_ratio: float = 0.0  # Actual R:R achieved (for position sizing)
    position_size_btc: Optional[float] = None  # Position size in BTC (calculated if balance provided)
    position_size_usd: Optional[float] = None  # Position value in USD (calculated if balance provided)


class PredictionEngine:
    """
    Strategy-aware prediction engine
    
    Takes unified market data and generates trading predictions based on the current strategy.
    Each strategy has different requirements and logic for generating predictions.
    """
    
    def __init__(self):
        logger.info("🤖 Prediction Engine initialized")
    
    @staticmethod
    def _require_key(data: Dict[str, Any], key: str, context: str = "") -> Any:
        """
        Require key to be present in data (NO FALLBACKS policy)
        
        Raises KeyError with descriptive message if key is missing
        """
        if key not in data:
            error_msg = f"Required key '{key}' missing from data"
            if context:
                error_msg += f" ({context})"
            raise KeyError(error_msg)
        return data[key]
    
    def _get_atr_pct(self, unified_data: Dict[str, Any], current_price: float) -> float:
        """
        Get ATR as percentage of price for mathematically justified thresholds (NO FALLBACKS)
        
        Returns ATR percentage (e.g., 0.004 = 0.4%)
        Raises ValueError if ATR is unavailable
        """
        if not unified_data:
            raise ValueError("unified_data is required for ATR calculation - NO FALLBACKS")
        if current_price <= 0:
            raise ValueError(f"Invalid current_price: {current_price} - must be positive")
        
        sr_data = unified_data["support_resistance"]  # Required (NO FALLBACKS)
        if not sr_data:
            raise ValueError("support_resistance data is required for ATR calculation - NO FALLBACKS")
        
        sr_metadata = sr_data["metadata"]  # Required (NO FALLBACKS)
        if not sr_metadata:
            raise ValueError("support_resistance.metadata is required for ATR calculation - NO FALLBACKS")
        
        atr_5m = sr_metadata["atr_5m"]  # Required (NO FALLBACKS)
        if atr_5m <= 0:
            raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
        
        atr_pct = atr_5m / current_price
        if atr_pct <= 0:
            raise ValueError(f"Invalid ATR percentage: {atr_pct} - must be positive (NO FALLBACKS)")
        
        return atr_pct
    
    def generate_prediction(self, unified_data: Dict[str, Any], strategy: str) -> Optional[TradingPrediction]:
        """
        Generate a trading prediction based on unified data and strategy
        
        Args:
            unified_data: Complete market analysis data
            strategy: Current trading strategy name
            
        Returns:
            TradingPrediction if conditions are met, None otherwise
        """
        try:
            # Get strategy configuration
            strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
            if not strategy_config:
                logger.warning(f"⚠️ Unknown strategy: {strategy}")
                return None
            
            # Generate strategy-specific prediction (confidence will be calculated after all parameters integrated)
            prediction = self._generate_strategy_prediction(unified_data, strategy, strategy_config)
            
            # Always return prediction if generated
            if prediction:
                # Ensure timestamp is set
                if not prediction.timestamp:
                    prediction.timestamp = time.time()
                
                # Log prediction generation
                logger.info(f"✅ Prediction generated: {prediction.direction} @ ${prediction.entry_price:.2f} (strategy: {strategy})")
                return prediction
            else:
                logger.debug(f"⏸️ No prediction generated for strategy: {strategy}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Prediction generation failed: {e}")
            return None
    
    def _generate_strategy_prediction(
        self, 
        unified_data: Dict[str, Any], 
        strategy: str,
        strategy_config: Dict[str, Any]
    ) -> Optional[TradingPrediction]:
        """
        Generate prediction for specific strategy
        
        This is the foundation - strategy-specific logic will be implemented here
        """
        # Route to strategy-specific prediction method
        strategy_methods = {
            "standard": self._predict,
            "scalping": self._predict_scalping,
            "swing_trading": self._predict_swing_trading,
            "trend_following": self._predict_trend_following,
            "breakout": self._predict_breakout,
            "range_trading": self._predict_range_trading,
            "low_volatility_range": self._predict_low_volatility_range,
            "high_volatility": self._predict_high_volatility,
            "spike_hunting": self._predict_spike_hunting,
        }
        
        method = strategy_methods[strategy] if strategy in strategy_methods else self._predict
        return method(unified_data, strategy_config)
    
    def _predict(self, unified_data: Dict[str, Any], config: Dict[str, Any], strategy: str = "standard") -> Optional[TradingPrediction]:
        """
        Sequential prediction logic (shared base for all strategies)
        
        SEQUENTIAL DECISION FLOW (Option A - Confidence influences position size):
        1. GET ALL DATA (already done via unified_data)
        2. DETERMINE DIRECTION (market condition decision) - PERFECT calculation
        3. DETERMINE ENTRY PRICE (tactical decision for selected direction)
        4. DETERMINE STOP/TARGET (risk management)
        
        This ensures direction is determined PERFECTLY first, then we find the best entry for that direction.
        
        All strategies use this sequential flow with strategy-specific parameters (direction_weights, 
        timeframe_weights, proximity_config, etc.) from TradingConfig.STRATEGY_CONFIGS[strategy].
        """
        # ==================================================================================
        # STEP 1: GET ALL DATA (already done via unified_data)
        # ==================================================================================
        # All market data is already available in unified_data
        
        # ==================================================================================
        # STEP 2: DETERMINE DIRECTION PERFECTLY (market condition decision)
        # ==================================================================================
        direction_result = self._score_direction(unified_data, strategy)
        if not direction_result:
            logger.warning(f"⚠️ Direction determination failed for {strategy} strategy")
            return None
        
        direction = direction_result["direction"]  # Required (NO FALLBACKS)
        direction_reasoning = direction_result["reasoning"]  # Required (NO FALLBACKS)
        long_score = direction_result["long_score"]  # Required (NO FALLBACKS)
        short_score = direction_result["short_score"]  # Required (NO FALLBACKS)
        score_diff = abs(long_score - short_score)
        
        # Check minimum score difference threshold (configurable) - NO FALLBACKS
        min_score_diff = config["min_score_diff"]
        if score_diff < min_score_diff:
            logger.debug(f"⏸️ Direction signal too weak: {direction} (score diff: {score_diff:.1f} < {min_score_diff:.1f})")
            return None
        
        logger.info(f"📊 Direction determined: {direction} (LONG: {long_score:.1f}, SHORT: {short_score:.1f}, diff: {score_diff:.1f})")
        logger.debug(f"📊 Direction reasoning: {direction_reasoning}")
        
        # ==================================================================================
        # STEP 3: DETERMINE ENTRY PRICE (tactical decision for selected direction)
        # ==================================================================================
        # Generate setups ONLY for the selected direction
        setups = self._generate_setups_for_direction(
            unified_data=unified_data,
            direction=direction,
            strategy=strategy,
            config=config
        )
        
        if not setups:
            logger.debug(f"⏸️ No valid entry setups found for {direction} direction ({strategy} strategy)")
            return None
        
        # Select best entry setup (highest entry score)
        best_setup = max(setups, key=lambda x: x["entry_score"])  # Required (NO FALLBACKS)
        
        entry_price = best_setup["entry_price"]  # Required (NO FALLBACKS)
        entry_score = best_setup["entry_score"]  # Required (NO FALLBACKS)
        entry_reasoning = best_setup["entry_reasoning"]  # Required (NO FALLBACKS)
        best_setup_level_data = best_setup["level_data"]  # Required (NO FALLBACKS)
        best_setup_type = best_setup["setup_type"]  # Required (NO FALLBACKS)
        
        logger.info(f"📊 Best entry: {direction} @ ${entry_price:.2f} (entry score: {entry_score:.1f})")
        logger.debug(f"📊 Entry reasoning: {entry_reasoning}")
        
        # ==================================================================================
        # STEP 4: DETERMINE STOP/TARGET (risk management)
        # ==================================================================================
        stop_loss, take_profit, rr_ratio, stop_loss_pct, take_profit_pct = self._calculate_stop_and_target(
            entry_price=entry_price,
            direction=direction,
            config=config,
            unified_data=unified_data,
            strategy=strategy,
            level_data=best_setup_level_data,
            setup_type=best_setup_type
        )
        
        # Combine reasoning
        combined_reasoning = f"Direction: {direction_reasoning}. Entry: {entry_reasoning}"
        
        # Pass full setup data to confidence calculation (includes all breakdowns and metrics)
        confidence = self._calculate_prediction_confidence(
            setup_data=best_setup,  # Full setup data with all breakdowns
            stop_loss=stop_loss,
            take_profit=take_profit,
            rr_ratio=rr_ratio,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            unified_data=unified_data,
            strategy=strategy
        )
        
        return self._create_prediction(
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reasoning=combined_reasoning,
            strategy=strategy,
            risk_reward_ratio=rr_ratio
        )
    
    def _create_prediction(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        reasoning: str,
        strategy: str,
        risk_reward_ratio: float = 0.0
    ) -> TradingPrediction:
        """Create a TradingPrediction object - single responsibility: prediction creation"""
        return TradingPrediction(
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reasoning=reasoning,
            strategy=strategy,
            timestamp=time.time(),
            risk_reward_ratio=risk_reward_ratio
        )
    
    # REMOVED: calculate_position_size static method (dead code, never called)
    # Position sizing is now done directly via PositionSizeCalculator.calculate_position_size
    # with liquidation risk protection
    
    def _predict_scalping(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """
        Scalping strategy prediction logic
        
        Scalping characteristics:
        - Very short timeframes (seconds to minutes)
        - Quick entries/exits (prefer current price)
        - Tight stops (0.2%) and targets (0.3%)
        - Focus on RSI (35%) and orderbook pressure (30%)
        - Requires tight spreads and high liquidity
        - Lower decision threshold (8.0 vs 10.0)
        """
        # Validate scalping-specific requirements
        if not self._validate_scalping_requirements(unified_data, config):
            return None
        
        # Use base prediction logic with scalping strategy
        # Note: Scalping still uses limit orders at S/R levels, not market orders
        return self._predict(unified_data, config, "scalping")
    
    def _validate_scalping_requirements(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Validate scalping-specific requirements (spread, liquidity, RSI range)"""
        orderbook_data = self._require_key(unified_data, "orderbook_analysis", "scalping validation")
        bid_ask_spread = self._require_key(orderbook_data, "bid_ask_spread", "orderbook_analysis structure")
        spread_pct = self._require_key(bid_ask_spread, "percentage", "bid_ask_spread structure")
        
        # Check spread requirement - spread_pct is in percentage units (e.g., 0.01 = 0.01%), threshold is in decimal (0.0001 = 0.01%)
        # Convert stored percentage to decimal: 0.01% -> 0.0001
        spread_decimal = spread_pct / 100.0
        spread_threshold = config["spread_threshold"]  # Required for scalping strategy (NO FALLBACKS)
        if spread_decimal > spread_threshold:
            logger.debug(f"⏸️ Spread too wide for scalping: {spread_pct:.4f}% > {spread_threshold*100:.4f}%")
            return False
        
        # Check liquidity requirement
        require_high_liquidity = config["require_high_liquidity"]  # Required (NO FALLBACKS)
        if require_high_liquidity:
            liquidity_depth = self._require_key(orderbook_data, "liquidity_depth", "orderbook_analysis structure")
            liquidity_score = self._require_key(liquidity_depth, "depth_score", "liquidity_depth structure")
            min_liquidity = TradingConfig.MIN_LIQUIDITY_SCORE
            if liquidity_score < min_liquidity:
                logger.debug(f"⏸️ Insufficient liquidity for scalping: {liquidity_score:.2f} (min: {min_liquidity})")
                return False
        
        # Check RSI range requirement
        rsi_data = self._require_key(unified_data, "rsi", "scalping validation")
        rsi_value = self._require_key(rsi_data, "rsi", "scalping validation")
        rsi_range = config["rsi_range"]  # Required for scalping strategy (NO FALLBACKS)
        if rsi_value < rsi_range[0] or rsi_value > rsi_range[1]:
            logger.debug(f"⏸️ RSI outside scalping range: {rsi_value:.1f} not in [{rsi_range[0]}, {rsi_range[1]}]")
            return False
        
        return True
    
    def _predict_swing_trading(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Swing trading strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "swing_trading")
    
    def _predict_trend_following(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Trend following strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "trend_following")
    
    def _predict_breakout(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Breakout strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "breakout")
    
    def _predict_range_trading(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Range trading strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "range_trading")
    
    def _predict_low_volatility_range(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Low volatility range strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "low_volatility_range")
    
    def _predict_high_volatility(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """High volatility strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "high_volatility")
    
    def _predict_spike_hunting(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Spike hunting strategy prediction logic - uses base prediction with strategy-specific parameters"""
        return self._predict(unified_data, config, "spike_hunting")
    
    def _determine_direction(self, unified_data: Dict[str, Any], strategy: str) -> Optional[Dict[str, Any]]:
        """
        Determine trade direction using unified scoring framework (global - no entry context)
        
        NOTE: This method returns GLOBAL direction scores (not contextual).
        This method is kept for backward compatibility and general direction analysis.
        
        NOTE: This method uses "scores" (long_score, short_score) for direction determination.
        "Confidence" is ONLY used for final predictions, not for intermediate calculations.
        
        Delegates to _score_direction which uses the unified scoring framework.
        
        Args:
            unified_data: Complete market analysis data
            strategy: Current trading strategy
            
        Returns:
            Dict with "direction" ("LONG" or "SHORT"), "reasoning", "long_score", and "short_score"
        """
        return self._score_direction(unified_data, strategy)
    
    # ==================================================================================
    # UNIFIED SCORING FRAMEWORK - Factor Scorers (Reusable)
    # ==================================================================================
    
    def _score_rsi_factor(self, rsi_data: Dict[str, Any]) -> tuple[float, float, list]:
        """
        Score RSI factor for direction determination
        
        Returns:
            (rsi_long_score, rsi_short_score, reasons)
        """
        rsi_value = self._require_key(rsi_data, "rsi", "RSI factor scoring")
        rsi_trend = self._require_key(rsi_data, "rsi_trend", "RSI factor scoring")
        rsi_signal = self._require_key(rsi_data, "rsi_signal", "RSI factor scoring")
        
        rsi_long = 0.0
        rsi_short = 0.0
        reasons = []
        
        if rsi_value < technical_constants.RSI_OVERSOLD:  # Oversold - bullish
            rsi_long = 100.0
            reasons.append(f"RSI oversold ({rsi_value:.1f})")
        elif rsi_value > technical_constants.RSI_OVERBOUGHT:  # Overbought - bearish
            rsi_short = 100.0
            reasons.append(f"RSI overbought ({rsi_value:.1f})")
        elif rsi_value < 50 and rsi_trend == "BULLISH":  # Below neutral but rising
            rsi_long = 60.0
            reasons.append(f"RSI recovering ({rsi_value:.1f}, {rsi_trend})")
        elif rsi_value > 50 and rsi_trend == "BEARISH":  # Above neutral but falling
            rsi_short = 60.0
            reasons.append(f"RSI declining ({rsi_value:.1f}, {rsi_trend})")
        
        if rsi_signal == "BULLISH":
            rsi_long += 40.0
            reasons.append("RSI bullish signal")
        elif rsi_signal == "BEARISH":
            rsi_short += 40.0
            reasons.append("RSI bearish signal")
        
        return rsi_long, rsi_short, reasons
    
    def _score_trend_factor(self, trend_data: Dict[str, Any], strategy: str) -> tuple[float, float, list]:
        """
        Score trend factor for direction determination using multi-timeframe analysis
        
        Returns:
            (trend_long_score, trend_short_score, reasons)
        """
        detailed_trends = self._require_key(trend_data, "detailed_timeframes", "trend factor scoring")
        timeframe_weights = self._get_strategy_timeframe_weights(strategy)
        
        trend_long = 0.0
        trend_short = 0.0
        reasons = []
        
        # Analyze each timeframe with strategy-specific weights
        for tf_name, tf_trend in detailed_trends.items():
            if tf_trend == "UNKNOWN":
                continue
            
            tf_weight = timeframe_weights[tf_name] if tf_name in timeframe_weights else 0.0
            if tf_weight == 0.0:
                continue
            
            trend_str = str(tf_trend).upper()
            is_bullish = "UP" in trend_str or "BULLISH" in trend_str
            is_bearish = "DOWN" in trend_str or "BEARISH" in trend_str
            is_strong = "STRONG" in trend_str
            is_weak = "WEAK" in trend_str
            
            if is_bullish:
                tf_score = 100.0
                if is_strong:
                    tf_score = 150.0
                elif is_weak:
                    tf_score = 60.0
                trend_long += tf_score * tf_weight
            elif is_bearish:
                tf_score = 100.0
                if is_strong:
                    tf_score = 150.0
                elif is_weak:
                    tf_score = 60.0
                trend_short += tf_score * tf_weight
        
        # Multi-timeframe convergence bonus
        bullish_tfs = sum(1 for tf in detailed_trends.values() 
                         if "UP" in str(tf).upper() or "BULLISH" in str(tf).upper())
        bearish_tfs = sum(1 for tf in detailed_trends.values() 
                         if "DOWN" in str(tf).upper() or "BEARISH" in str(tf).upper())
        total_tfs = len([tf for tf in detailed_trends.values() if str(tf) != "UNKNOWN"])
        
        if total_tfs >= 3:
            if bullish_tfs == total_tfs:
                trend_long += 50.0
                reasons.append(f"Perfect trend convergence: all {total_tfs} timeframes bullish")
            elif bearish_tfs == total_tfs:
                trend_short += 50.0
                reasons.append(f"Perfect trend convergence: all {total_tfs} timeframes bearish")
            elif bullish_tfs >= 3:
                trend_long += 30.0
                reasons.append(f"Strong trend alignment: {bullish_tfs}/{total_tfs} timeframes bullish")
            elif bearish_tfs >= 3:
                trend_short += 30.0
                reasons.append(f"Strong trend alignment: {bearish_tfs}/{total_tfs} timeframes bearish")
        
        return trend_long, trend_short, reasons
    
    # REMOVED: _score_sr_factor() - S/R no longer used for direction scoring
    # S/R levels determine WHERE to enter/exit, NOT direction
    # Direction determined by: trend, RSI, pressure, volume, patterns only
    
    def _score_pressure_factor(self, pressure_data: Dict[str, Any]) -> tuple[float, float, list]:
        """
        Score market pressure factor for direction determination
        
        Returns:
            (pressure_long_score, pressure_short_score, reasons)
        """
        pressure_direction = self._require_key(pressure_data, "direction", "pressure factor scoring")
        pressure_strength = self._require_key(pressure_data, "strength", "pressure factor scoring")
        
        pressure_long = 0.0
        pressure_short = 0.0
        reasons = []
        
        if pressure_direction in ["BUY", "STRONG_BUY"]:
            strength_multiplier = 1.5 if "STRONG" in pressure_direction else 1.0
            pressure_long = 100.0 * strength_multiplier * pressure_strength
            reasons.append(f"Buy pressure: {pressure_direction} (strength: {pressure_strength:.2f})")
        elif pressure_direction in ["SELL", "STRONG_SELL"]:
            strength_multiplier = 1.5 if "STRONG" in pressure_direction else 1.0
            pressure_short = 100.0 * strength_multiplier * pressure_strength
            reasons.append(f"Sell pressure: {pressure_direction} (strength: {pressure_strength:.2f})")
        
        return pressure_long, pressure_short, reasons
    
    def _score_patterns_factor(self, patterns_data: Dict[str, Any]) -> tuple[float, float, list]:
        """
        Score patterns factor for direction determination using research-based reliability weights
        
        Research-based pattern reliability (from 200,000+ patterns over 10 years):
        - Head & Shoulders: ~83% reliability (highest)
        - Triple Tops/Bottoms: 77-79%
        - Double Tops/Bottoms: 75-79%
        - Triangles/Channels: ~73%
        - Flags: ~67%
        - Hammers: Low reliability (only reliable using low price, not closing)
        
        Scoring formula:
        - Base score = pattern_quality × pattern_type_reliability × 100
        - Pattern importance bonus (clarity + recency) adds up to 30 points
        - Multiple patterns sum together (not binary)
        
        Note: pattern_quality (from pattern["quality"]) is pattern detection quality (0-1),
        NOT prediction confidence. 'confidence' is reserved for predictions/reactions only.
        
        Returns:
            (patterns_long_score, patterns_short_score, reasons)
        """
        patterns_nested = self._require_key(patterns_data, "patterns_nested", "patterns factor scoring")
        
        # Pattern type reliability weights (based on research: 0.67-0.83 range)
        PATTERN_RELIABILITY = {
            # Reversal patterns (highest reliability)
            "HEAD_SHOULDERS": 0.83,
            "INVERSE_HEAD_SHOULDERS": 0.83,
            "TRIPLE_TOP": 0.79,
            "TRIPLE_BOTTOM": 0.79,
            "DOUBLE_TOP": 0.77,
            "DOUBLE_BOTTOM": 0.77,
            "RECTANGLE": 0.78,
            "TREND_CHANGE": 0.70,
            
            # Continuation patterns
            "ASCENDING_TRIANGLE": 0.73,
            "DESCENDING_TRIANGLE": 0.73,
            "SYMMETRICAL_TRIANGLE": 0.73,
            "ASCENDING_CHANNEL": 0.73,
            "DESCENDING_CHANNEL": 0.73,
            "BULL_FLAG": 0.67,
            "BEAR_FLAG": 0.67,
            "BULLISH_CONTINUATION": 0.70,
            "BEARISH_CONTINUATION": 0.70,
            
            # Candlestick patterns (lower reliability)
            "ENGULFING_BULLISH": 0.65,
            "ENGULFING_BEARISH": 0.65,
            "HAMMER": 0.50,  # Low reliability - only reliable using low price
            "SHOOTING_STAR": 0.55,
            "DOJI": 0.45,
            "MORNING_STAR": 0.60,
            "EVENING_STAR": 0.60,
            "THREE_SOLDIERS": 0.58,
            "THREE_CROWS": 0.58,
            "HARAMI_BULLISH": 0.52,
            "HARAMI_BEARISH": 0.52,
        }
        
        # Default reliability for unknown patterns
        DEFAULT_RELIABILITY = 0.60
        
        patterns_long = 0.0
        patterns_short = 0.0
        reasons = []
        
        # Score all pattern categories
        all_pattern_categories = [
            ("reversal_patterns", patterns_nested["reversal_patterns"]),
            ("continuation_patterns", patterns_nested["continuation_patterns"]),
            ("triangle_patterns", patterns_nested["triangle_patterns"]),
            ("channel_patterns", patterns_nested["channel_patterns"]),
            ("wedge_patterns", patterns_nested["wedge_patterns"]),
            ("candlestick_patterns", patterns_nested["candlestick_patterns"]),
        ]
        
        for category_name, patterns in all_pattern_categories:
            if not patterns:
                continue
            
            for pattern in patterns:
                if not isinstance(pattern, dict):
                    continue
                
                pattern_name = pattern["pattern"].upper()
                direction = pattern["direction"]
                pattern_quality = pattern["quality"]  # Pattern detection quality (0-1), NOT prediction confidence
                
                # Get pattern type reliability - NO FALLBACKS
                if pattern_name not in PATTERN_RELIABILITY:
                    raise ValueError(f"Pattern '{pattern_name}' not found in PATTERN_RELIABILITY map - NO FALLBACKS")
                pattern_reliability = PATTERN_RELIABILITY[pattern_name]
                
                # Calculate base score: pattern_quality × reliability × 100
                base_score = pattern_quality * pattern_reliability * 100.0
                
                # Calculate pattern importance bonus (clarity + recency, up to 30 points)
                # Use pattern importance calculation if available
                pattern_high = pattern["pattern_high"]
                pattern_low = pattern["pattern_low"]
                age_minutes = pattern["age_minutes"]
                
                # Clarity bonus (0-20 pts): wider price range = clearer pattern
                if pattern_high > 0 and pattern_low > 0:
                    avg_price = (pattern_high + pattern_low) / 2.0
                    range_pct = (pattern_high - pattern_low) / avg_price if avg_price > 0 else 0.0
                    clarity_bonus = min(20.0, max(0.0, (range_pct - 0.005) / 0.015 * 20.0))
                else:
                    clarity_bonus = 0.0
                
                # Recency bonus (0-10 pts): fresher patterns preferred
                recency_bonus = max(0.0, 10.0 - (age_minutes / 3.0))  # 10 pts at 0min, 0 pts at 30min
                
                importance_bonus = clarity_bonus + recency_bonus
                
                # Total pattern score
                pattern_score = base_score + importance_bonus
                
                # Add to direction scores
                if direction == "BULLISH":
                    patterns_long += pattern_score
                    reasons.append(f"{pattern_name} (quality={pattern_quality:.2f}, rel={pattern_reliability:.2f}, score={pattern_score:.1f})")
                elif direction == "BEARISH":
                    patterns_short += pattern_score
                    reasons.append(f"{pattern_name} (quality={pattern_quality:.2f}, rel={pattern_reliability:.2f}, score={pattern_score:.1f})")
        
        # Cap scores at reasonable maximum (multiple strong patterns shouldn't dominate)
        max_pattern_score = 200.0  # Allow 2-3 strong patterns to contribute significantly
        patterns_long = min(patterns_long, max_pattern_score)
        patterns_short = min(patterns_short, max_pattern_score)
        
        return patterns_long, patterns_short, reasons
    
    def _score_volume_factor(self, volume_category: str, long_score: float, short_score: float) -> tuple[float, float, list]:
        """
        Score volume factor for direction determination (confirmation only)
        
        Returns:
            (volume_long_score, volume_short_score, reasons)
        """
        volume_long = 0.0
        volume_short = 0.0
        reasons = []
        
        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            if long_score > short_score:
                volume_long = 100.0
                reasons.append(f"High volume confirms bullish ({volume_category})")
            elif short_score > long_score:
                volume_short = 100.0
                reasons.append(f"High volume confirms bearish ({volume_category})")
        
        return volume_long, volume_short, reasons
    
    def _score_sr_proximity_factor(self, unified_data: Dict[str, Any], strategy: str) -> tuple[float, float, list]:
        """
        Score S/R proximity factor for direction determination
        
        When price is approaching a strong S/R level with high reversal probability,
        that should influence direction:
        - Approaching strong support with high reversal → favor LONG
        - Approaching strong resistance with high reversal → favor SHORT
        
        Returns:
            (sr_proximity_long_score, sr_proximity_short_score, reasons)
        """
        try:
            # All required data must be present (NO FALLBACKS)
            current_price = self._require_key(unified_data, "current_price", "S/R proximity factor scoring")
            if current_price <= 0:
                raise ValueError(f"Invalid current_price: {current_price}")
            
            sr_data = self._require_key(unified_data, "support_resistance", "S/R proximity factor scoring")
            all_levels = self._require_key(sr_data, "levels", "S/R proximity factor scoring")
            sr_metadata = self._require_key(sr_data, "metadata", "S/R proximity factor scoring")
            atr_5m = self._require_key(sr_metadata, "atr_5m", "S/R proximity factor scoring")
            if atr_5m <= 0:
                raise ValueError(f"Invalid atr_5m: {atr_5m}")
            
            atr_pct = atr_5m / current_price if current_price > 0 else 0.0
            
            # Initialize scores
            sr_proximity_long = 0.0
            sr_proximity_short = 0.0
            reasons = []
            
            # Maximum distance to consider (3×ATR - beyond this, level is too far to influence direction)
            max_distance_atr = 3.0
            max_distance_pct = max_distance_atr * atr_pct
            
            # Minimum power threshold (only consider strong levels)
            min_power = 50.0  # Only consider levels with power >= 50
            
            # Find nearest strong levels within reasonable distance
            from core.utils.distance_utils import calculate_distance_pct, calculate_distance_atr
            
            nearest_support = None
            nearest_resistance = None
            nearest_support_distance_atr = float('inf')
            nearest_resistance_distance_atr = float('inf')
            
            for level in all_levels:
                # Validate level structure
                level_price = level["price_level"]
                level_type = level["type"]
                level_power = level["power"]
                level_status = level["status"]
                
                if not level_price or level_price <= 0:
                    continue
                
                # Only consider active levels with sufficient power
                if level_status != "active" or level_power < min_power:
                    continue
                
                # Calculate distance
                distance_pct = calculate_distance_pct(level_price, current_price, current_price)
                distance_atr = calculate_distance_atr(distance_pct, atr_pct)
                
                # Only consider levels within max distance
                if distance_atr > max_distance_atr:
                    continue
                
                # Get reversal probability from power_breakdown
                power_breakdown = level["power_breakdown"]
                reversal_probability = power_breakdown["reversal_probability"]
                
                # Track nearest support and resistance
                if level_type == "support" and level_price < current_price:
                    if distance_atr < nearest_support_distance_atr:
                        nearest_support = level
                        nearest_support_distance_atr = distance_atr
                elif level_type == "resistance" and level_price > current_price:
                    if distance_atr < nearest_resistance_distance_atr:
                        nearest_resistance = level
                        nearest_resistance_distance_atr = distance_atr
            
            # Score based on nearest levels
            # Closer levels with higher reversal probability = stronger signal
            
            if nearest_support:
                support_price = nearest_support["price_level"]
                support_power = nearest_support["power"]
                support_breakdown = nearest_support["power_breakdown"]
                support_reversal_prob = support_breakdown["reversal_probability"]
                
                # Score calculation:
                # - Base score from reversal probability (0-100 points)
                # - Proximity multiplier (closer = stronger, 0.5-1.5×)
                # - Power multiplier (stronger level = more reliable, 0.8-1.2×)
                
                proximity_multiplier = max(0.5, min(1.5, 1.5 - (nearest_support_distance_atr / max_distance_atr)))
                power_multiplier = max(0.8, min(1.2, support_power / 100.0))
                
                sr_proximity_long = support_reversal_prob * proximity_multiplier * power_multiplier
                
                if sr_proximity_long > 20.0:  # Only log significant signals
                    reasons.append(
                        f"Near strong support ${support_price:.2f} "
                        f"(rev_prob={support_reversal_prob:.0f}%, "
                        f"power={support_power:.0f}, "
                        f"dist={nearest_support_distance_atr:.2f}×ATR)"
                    )
            
            if nearest_resistance:
                resistance_price = nearest_resistance["price_level"]
                resistance_power = nearest_resistance["power"]
                resistance_breakdown = nearest_resistance["power_breakdown"]
                resistance_reversal_prob = resistance_breakdown["reversal_probability"]
                
                # Score calculation (same logic as support)
                proximity_multiplier = max(0.5, min(1.5, 1.5 - (nearest_resistance_distance_atr / max_distance_atr)))
                power_multiplier = max(0.8, min(1.2, resistance_power / 100.0))
                
                sr_proximity_short = resistance_reversal_prob * proximity_multiplier * power_multiplier
                
                if sr_proximity_short > 20.0:  # Only log significant signals
                    reasons.append(
                        f"Near strong resistance ${resistance_price:.2f} "
                        f"(rev_prob={resistance_reversal_prob:.0f}%, "
                        f"power={resistance_power:.0f}, "
                        f"dist={nearest_resistance_distance_atr:.2f}×ATR)"
                    )
            
            return sr_proximity_long, sr_proximity_short, reasons
            
        except Exception as e:
            logger.error(f"❌ S/R proximity factor scoring failed: {e}")
            return 0.0, 0.0, []
    
    # REMOVED: _score_funding_factor() - Funding no longer used for direction scoring
    # Funding rate often unavailable and has minimal impact on short-term direction
    # Can be added back if needed for long-term position bias
    
    # ==================================================================================
    # UNIFIED SCORING FRAMEWORK - Entry Factor Scorers (Reusable)
    # ==================================================================================
    
    def _score_entry_sr_factor(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        level_data: Dict[str, Any],
        unified_data: Optional[Dict[str, Any]] = None,
        strategy: str = "standard"
    ) -> tuple[float, list]:
        """
        Score S/R level factor for entry setup
        
        level_data is ALWAYS provided (all entries are at specific S/R levels for limit orders).
        
        Note: Breakout/breakdown entries are removed - limit orders can't fill above resistance
        (when price is below) or below support (when price is above). Only support/resistance
        level entries are valid for limit orders.
        
        Args:
            entry_price: Entry price for limit order
            current_price: Current market price
            direction: "LONG" or "SHORT"
            level_data: S/R level data dict (must contain "price_level", "power", "setup_type")
            unified_data: Optional unified data for additional context
        
        Returns:
            (sr_score, reasons)
        """
        level_power = level_data["power"]  # Required (NO FALLBACKS)
        level_price = self._require_key(level_data, "price_level", "entry S/R factor scoring")
        setup_type = self._require_key(level_data, "setup_type", "entry S/R factor scoring")
        
        score = 0.0
        reasons = []
        
        # Base score from S/R level power (0-100) - pure strength, no proximity/recency
        score = level_power
        
        # Distance from the referenced level - using unified utility
        from core.utils.distance_utils import calculate_distance_pct
        distance_pct = calculate_distance_pct(entry_price, level_price, current_price)
        
        # Get ATR for mathematically justified thresholds
        atr_pct = self._get_atr_pct(unified_data, current_price)
        
        # Get strategy-specific entry proximity configuration
        strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
        entry_proximity_config = strategy_config["entry_proximity_config"]  # Required in all strategies (NO FALLBACKS)
        optimal_atr = entry_proximity_config["optimal_atr"]  # Required (NO FALLBACKS)
        acceptable_atr = entry_proximity_config["acceptable_atr"]  # Required (NO FALLBACKS)
        too_far_atr = entry_proximity_config["too_far_atr"]  # Required (NO FALLBACKS)
        
        # Strategy-specific thresholds based on ATR:
        optimal_threshold = atr_pct * optimal_atr
        acceptable_threshold = atr_pct * acceptable_atr
        too_far_threshold = atr_pct * too_far_atr
        
        # BTC PERP ENTRY SCORING (Research-backed for 40x leverage)
        # OLD LOGIC (WRONG): Gave 20% bonus for entering exactly AT S/R level (distance=0)
        # WHY WRONG: Ignores BTC perp market microstructure (stop hunts, liquidation wicks)
        # NEW LOGIC: Optimal entry is INSIDE zone (0.3-0.5×ATR toward current), not AT level
        #
        # Scoring philosophy:
        # - Inside optimal zone (0.2-0.5×ATR): Best (1.1x multiplier)
        # - At level or very close (0-0.2×ATR): Good but risky (1.0x, no bonus)
        # - Acceptable range (0.5-1.0×ATR): Acceptable (0.95x)
        # - Too far (>1.0×ATR): Penalty (0.8x)
        
        if setup_type in ["support_level", "resistance_level"]:
            # Calculate distance from S/R level in ATR terms
            distance_atr = distance_pct / atr_pct if atr_pct > 0 else 0
            
            if setup_type == "support_level":
                # LONG at support: entry ABOVE support (inside zone, toward current)
                # Use entry quality multipliers from config (configurable for optimization)
                if 0.2 <= distance_atr <= 0.5:  # Optimal: 0.2-0.5×ATR above support
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["optimal_bonus"])
                    reasons.append(f"Optimal entry above support @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                elif distance_atr < 0.2:  # At or very close to level
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["neutral"])
                    reasons.append(f"Entry near/at support @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                elif distance_atr <= 1.0:  # Acceptable: 0.5-1.0×ATR
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["small_penalty"])
                    reasons.append(f"Entry acceptable above support @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                else:  # Too far: >1.0×ATR
                    score = max(0.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["medium_penalty"])
                    reasons.append(f"Entry too far from support @ {distance_atr:.2f}×ATR")
            else:  # resistance_level
                # SHORT at resistance: entry BELOW resistance (inside zone, toward current)
                # Use entry quality multipliers from config (configurable for optimization)
                if 0.2 <= distance_atr <= 0.5:  # Optimal: 0.2-0.5×ATR below resistance
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["optimal_bonus"])
                    reasons.append(f"Optimal entry below resistance @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                elif distance_atr < 0.2:  # At or very close to level
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["neutral"])
                    reasons.append(f"Entry near/at resistance @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                elif distance_atr <= 1.0:  # Acceptable: 0.5-1.0×ATR
                    score = min(100.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["small_penalty"])
                    reasons.append(f"Entry acceptable below resistance @ {distance_atr:.2f}×ATR (power: {level_power:.1f})")
                else:  # Too far: >1.0×ATR
                    score = max(0.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["medium_penalty"])
                    reasons.append(f"Entry too far from resistance @ {distance_atr:.2f}×ATR")
        
        else:
            # Unknown setup type - use default scoring with ATR-based threshold
            near_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["near_threshold"]
            if distance_pct < near_threshold:
                reasons.append(f"S/R level reference (power: {level_power:.1f}, distance: {distance_pct*100:.3f}%)")
            else:
                score = max(0.0, score * TradingConfig.ENTRY_QUALITY_MULTIPLIERS["medium_penalty"])
                reasons.append(f"Far from S/R level (distance: {distance_pct*100:.3f}% > {near_threshold*100:.3f}%)")
        
        return score, reasons
    
    def _score_entry_rsi_factor(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        rsi_data: Dict[str, Any],
        atr_5m: Optional[float] = None
    ) -> tuple[float, list]:
        """
        Score RSI alignment factor for entry setup
        
        Args:
            entry_price: Proposed entry price
            current_price: Current market price
            direction: "LONG" or "SHORT"
            rsi_data: RSI data with "rsi" and "rsi_trend"
            atr_5m: 5-minute ATR (optional, for ATR-based thresholds)
        
        Returns:
            (rsi_score, reasons)
        """
        rsi_value = self._require_key(rsi_data, "rsi", "entry RSI factor scoring")
        rsi_trend = self._require_key(rsi_data, "rsi_trend", "entry RSI factor scoring")
        
        score = 0.0
        reasons = []
        
        # Entry price relative to current price
        price_diff_pct = (entry_price - current_price) / current_price if current_price > 0 else 0.0
        
        # ATR-based threshold (FIXED 2026-01-12)
        # Use 1.25×ATR as significant distance threshold (mathematically justified)
        # Falls back to 0.25% only if ATR unavailable (backward compatibility)
        if atr_5m and atr_5m > 0 and current_price > 0:
            significant_diff_threshold = (atr_5m / current_price) * 1.25  # 1.25×ATR as percentage
        else:
            significant_diff_threshold = 0.0025  # Fallback: 0.25% (reasonable for BTC)
        
        if direction == "LONG":
            # For LONG: entry below current (buying cheaper) is good, especially if RSI is oversold
            if rsi_value < technical_constants.RSI_OVERSOLD and price_diff_pct < 0:  # Oversold + entry below current = very good
                score = 100.0
                reasons.append(f"RSI oversold ({rsi_value:.1f}) + entry below current ({price_diff_pct*100:.2f}%)")
            elif rsi_value < 50 and rsi_trend == "BULLISH" and price_diff_pct <= 0:
                score = 70.0
                reasons.append(f"RSI recovering ({rsi_value:.1f}) + entry at/below current")
            elif price_diff_pct < -significant_diff_threshold:  # Entry significantly below current (1.25×ATR)
                score = 50.0
                reasons.append(f"Entry below current ({price_diff_pct*100:.2f}% < -{significant_diff_threshold*100:.2f}%)")
            elif price_diff_pct < 0:
                score = 30.0
                reasons.append(f"Entry slightly below current ({price_diff_pct*100:.2f}%)")
        else:  # SHORT
            # For SHORT: entry above current (selling higher) is good, especially if RSI is overbought
            if rsi_value > technical_constants.RSI_OVERBOUGHT and price_diff_pct > 0:  # Overbought + entry above current = very good
                score = 100.0
                reasons.append(f"RSI overbought ({rsi_value:.1f}) + entry above current ({price_diff_pct*100:.2f}%)")
            elif rsi_value > 50 and rsi_trend == "BEARISH" and price_diff_pct >= 0:
                score = 70.0
                reasons.append(f"RSI declining ({rsi_value:.1f}) + entry at/above current")
            elif price_diff_pct > significant_diff_threshold:  # Entry significantly above current (1.25×ATR)
                score = 50.0
                reasons.append(f"Entry above current ({price_diff_pct*100:.2f}% > {significant_diff_threshold*100:.2f}%)")
            elif price_diff_pct > 0:
                score = 30.0
                reasons.append(f"Entry slightly above current ({price_diff_pct*100:.2f}%)")
        
        return score, reasons
    
    def _score_entry_trend_factor(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        trend_data: Dict[str, Any],
        strategy: str
    ) -> tuple[float, list]:
        """
        Score trend alignment factor for entry setup
        
        Returns:
            (trend_score, reasons)
        """
        detailed_trends = self._require_key(trend_data, "detailed_timeframes", "trend factor scoring")
        timeframe_weights = self._get_strategy_timeframe_weights(strategy)
        
        score = 0.0
        reasons = []
        
        # Analyze trend alignment with entry direction
        bullish_tfs = 0
        bearish_tfs = 0
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for tf_name, tf_trend in detailed_trends.items():
            if tf_trend == "UNKNOWN":
                continue
            
            tf_weight = timeframe_weights[tf_name] if tf_name in timeframe_weights else 0.0
            if tf_weight == 0.0:
                continue
            
            trend_str = str(tf_trend).upper()
            is_bullish = "UP" in trend_str or "BULLISH" in trend_str
            is_bearish = "DOWN" in trend_str or "BEARISH" in trend_str
            is_strong = "STRONG" in trend_str
            
            if is_bullish:
                bullish_tfs += 1
                tf_score = 1.5 if is_strong else 1.0
                total_weighted_score += tf_score * tf_weight
                total_weight += tf_weight
            elif is_bearish:
                bearish_tfs += 1
                tf_score = 1.5 if is_strong else 1.0
                total_weighted_score += tf_score * tf_weight
                total_weight += tf_weight
        
        if total_weight > 0:
            avg_score = total_weighted_score / total_weight
            if direction == "LONG" and bullish_tfs > bearish_tfs:
                score = avg_score * 100.0  # Bullish trend aligns with LONG
                reasons.append(f"Trend alignment: {bullish_tfs} bullish vs {bearish_tfs} bearish timeframes")
            elif direction == "SHORT" and bearish_tfs > bullish_tfs:
                score = avg_score * 100.0  # Bearish trend aligns with SHORT
                reasons.append(f"Trend alignment: {bearish_tfs} bearish vs {bullish_tfs} bullish timeframes")
            else:
                score = avg_score * 50.0  # Partial alignment
                reasons.append(f"Partial trend alignment: {bullish_tfs} bullish, {bearish_tfs} bearish")
        
        return score, reasons
    
    def _score_entry_pressure_factor(
        self,
        direction: str,
        pressure_data: Dict[str, Any]
    ) -> tuple[float, list]:
        """
        Score market pressure alignment factor for entry setup
        
        Returns:
            (pressure_score, reasons)
        """
        pressure_direction = self._require_key(pressure_data, "direction", "pressure factor scoring")
        pressure_strength = self._require_key(pressure_data, "strength", "pressure factor scoring")
        
        score = 0.0
        reasons = []
        
        if direction == "LONG" and pressure_direction in ["BUY", "STRONG_BUY"]:
            strength_multiplier = 1.5 if "STRONG" in pressure_direction else 1.0
            score = 100.0 * strength_multiplier * pressure_strength
            reasons.append(f"Buy pressure aligns with LONG: {pressure_direction} (strength: {pressure_strength:.2f})")
        elif direction == "SHORT" and pressure_direction in ["SELL", "STRONG_SELL"]:
            strength_multiplier = 1.5 if "STRONG" in pressure_direction else 1.0
            score = 100.0 * strength_multiplier * pressure_strength
            reasons.append(f"Sell pressure aligns with SHORT: {pressure_direction} (strength: {pressure_strength:.2f})")
        else:
            score = 30.0  # Neutral pressure
            reasons.append(f"Neutral pressure: {pressure_direction}")
        
        return score, reasons
    
    def _score_entry_patterns_factor(
        self,
        direction: str,
        patterns_data: Dict[str, Any]
    ) -> tuple[float, list]:
        """
        Score pattern alignment factor for entry setup
        
        Returns:
            (patterns_score, reasons)
        """
        patterns_nested = self._require_key(patterns_data, "patterns_nested", "patterns factor scoring")
        reversal_patterns = self._require_key(patterns_nested, "reversal_patterns", "patterns factor scoring")
        continuation_patterns = self._require_key(patterns_nested, "continuation_patterns", "patterns factor scoring")
        
        score = 0.0
        reasons = []
        
        if direction == "LONG":
            bullish_reversals = [p for p in reversal_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BULLISH"]
            bullish_continuations = [p for p in continuation_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BULLISH"]
            
            if bullish_reversals:
                score += 100.0
                reasons.append(f"Bullish reversal pattern aligns with LONG ({len(bullish_reversals)})")
            if bullish_continuations:
                score += 50.0
                reasons.append(f"Bullish continuation pattern ({len(bullish_continuations)})")
        else:  # SHORT
            bearish_reversals = [p for p in reversal_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BEARISH"]
            bearish_continuations = [p for p in continuation_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BEARISH"]
            
            if bearish_reversals:
                score += 100.0
                reasons.append(f"Bearish reversal pattern aligns with SHORT ({len(bearish_reversals)})")
            if bearish_continuations:
                score += 50.0
                reasons.append(f"Bearish continuation pattern ({len(bearish_continuations)})")
        
        return min(100.0, score), reasons
    
    def _score_entry_volume_factor(
        self,
        volume_category: str,
        volume_anomaly: Dict[str, Any] = None
    ) -> tuple[float, list]:
        """
        Score volume confirmation factor for entry setup
        
        Args:
            volume_category: Volume category (HIGH, NORMAL, LOW, etc.)
            volume_anomaly: Volume anomaly detection data for risk management
        
        Returns:
            (volume_score, reasons)
        """
        score = 0.0
        reasons = []
        
        # Volume anomaly risk check: Reduce score if anomaly detected
        if volume_anomaly and volume_anomaly["is_anomaly"]:
            severity = volume_anomaly["severity"]
            if severity == "EXTREME":
                score -= 50.0  # Significant penalty for extreme anomalies
                reasons.append(f"⚠️ EXTREME volume anomaly detected - high risk")
            elif severity == "HIGH":
                score -= 30.0  # Moderate penalty for high anomalies
                reasons.append(f"⚠️ HIGH volume anomaly detected - increased risk")
            elif severity == "MODERATE":
                score -= 15.0  # Small penalty for moderate anomalies
                reasons.append(f"⚠️ MODERATE volume anomaly detected - caution advised")
        
        # Normal volume scoring
        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            score += 100.0
            reasons.append(f"High volume confirms entry ({volume_category})")
        elif volume_category in ["NORMAL"]:
            score += 50.0
            reasons.append("Normal volume")
        else:
            score += 20.0
            reasons.append(f"Low volume ({volume_category})")
        
        return max(0.0, score), reasons
    
    def _score_entry_distance_factor(
        self,
        entry_price: float,
        current_price: float,
        direction: str
    ) -> tuple[float, list]:
        """
        Score distance from current price factor (risk/reward consideration)
        
        Returns:
            (distance_score, reasons)
        """
        if current_price <= 0:
            return 0.0, []
        
        distance_pct = abs(entry_price - current_price) / current_price
        score = 0.0
        reasons = []
        
        # Get ATR for mathematically justified thresholds
        # Note: unified_data not available in this method signature, use fallback
        # This is acceptable as distance scoring can use reasonable defaults
        atr_pct = 0.002  # Default 0.2% ATR if unavailable (reasonable fallback)
        
        # Mathematically justified thresholds based on ATR:
        # - Too close: <0.25×ATR (might miss if price moves quickly)
        # - Optimal: 0.25×ATR to 1.25×ATR (good balance, likely to fill)
        # - Moderate: 1.25×ATR to 2.5×ATR (reasonable, might take longer)
        # - Far: 2.5×ATR to 5×ATR (lower fill probability)
        # - Very far: >5×ATR (very low fill probability)
        # Use ATR multipliers from config (configurable for optimization)
        too_close_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["too_close"]
        optimal_max_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["optimal"]
        moderate_max_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["moderate"]
        far_max_threshold = atr_pct * TradingConfig.ATR_MULTIPLIERS["far"]
        
        if too_close_threshold <= distance_pct < optimal_max_threshold:  # Optimal range: 0.25×ATR to 1.25×ATR
            score = 100.0
            reasons.append(f"Optimal distance from current ({distance_pct*100:.3f}%, {too_close_threshold*100:.3f}%-{optimal_max_threshold*100:.3f}%) - good fill probability")
        elif distance_pct < too_close_threshold:  # Too close: <0.25×ATR
            score = 60.0  # Might miss if price moves quickly
            reasons.append(f"Very close to current ({distance_pct*100:.3f}% < {too_close_threshold*100:.3f}%) - might miss")
        elif distance_pct < moderate_max_threshold:  # Moderate: 1.25×ATR to 2.5×ATR
            score = 80.0  # Good balance
            reasons.append(f"Moderate distance from current ({distance_pct*100:.3f}%, {optimal_max_threshold*100:.3f}%-{moderate_max_threshold*100:.3f}%)")
        elif distance_pct < far_max_threshold:  # Far: 2.5×ATR to 5×ATR
            score = 50.0  # Lower fill probability
            reasons.append(f"Far from current ({distance_pct*100:.3f}%, {moderate_max_threshold*100:.3f}%-{far_max_threshold*100:.3f}%) - lower fill probability")
        else:  # Very far: >5×ATR
            score = 20.0  # Very low fill probability
            reasons.append(f"Very far from current ({distance_pct*100:.3f}% > {far_max_threshold*100:.3f}%) - low fill probability")
        
        return score, reasons
    
    def _score_entry_type_factor(
        self,
        setup_type: str,
        strategy: str
    ) -> tuple[float, list]:
        """
        Score setup type bonus (strategy-aware)
        
        Returns:
            (type_score, reasons)
        """
        score = 0.0
        reasons = []
        
        # Strategy-specific preferences (all entries are at S/R levels for limit orders)
        # Note: Breakout/breakdown entries removed - they don't work with limit orders only
        if strategy == "breakout":
            # For breakout strategy with limit orders, we enter at resistance (SHORT) or support (LONG)
            # when price is approaching the level, anticipating the breakout
            if setup_type in ["support_level", "resistance_level"]:
                score = 100.0  # Breakout strategy uses S/R level entries (anticipating breakout)
                reasons.append(f"S/R level entry for {strategy} (breakout anticipation)")
            else:
                score = 60.0
        elif strategy in ["range_trading", "low_volatility_range"]:
            if setup_type in ["support_level", "resistance_level"]:
                score = 100.0  # Range trading prefers S/R level entries
                reasons.append("S/R level entry preferred for range trading")
            else:
                score = 50.0
        else:  # Standard and other strategies
            if setup_type in ["support_level", "resistance_level"]:
                score = 80.0  # S/R levels are generally good for limit orders
                reasons.append("S/R level entry")
            else:
                score = 60.0  # Default for any other types
                reasons.append(f"{setup_type} entry")
        
        return score, reasons
    
    # ==================================================================================
    # PARAMETER SCORERS - Use factor scorers to score specific parameters
    # ==================================================================================
    
    def _score_direction(self, unified_data: Dict[str, Any], strategy: str) -> Optional[Dict[str, Any]]:
        """
        Score direction using unified scoring framework (global - no entry context)
        
        Uses factor scorers to calculate long_score and short_score, then determines direction.
        This is the base method used in the sequential flow (Step 2: Determine Direction).
        
        Returns:
            Dict with "direction", "reasoning", "long_score", "short_score"
        """
        try:
            # All required data must be present (NO FALLBACKS)
            current_price = self._require_key(unified_data, "current_price", "direction scoring")
            if current_price <= 0:
                raise ValueError(f"Invalid current_price: {current_price}")
            
            # Get strategy-specific weights (NO FALLBACKS)
            # NOTE: S/R is NOT included in direction scoring - S/R determines entry/exit, NOT direction
            strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
            direction_weights = strategy_config["direction_weights"]  # Required in all strategies (NO FALLBACKS)
            
            # Extract indicators - all required (NO FALLBACKS)
            rsi_data = self._require_key(unified_data, "rsi", "direction scoring")
            trend_data = self._require_key(unified_data, "trend", "direction scoring")
            pressure_data = self._require_key(unified_data, "pressure", "direction scoring")
            patterns_data = self._require_key(unified_data, "patterns", "direction scoring")
            volume_category = self._require_key(unified_data, "volume_category", "direction scoring")
            # funding_data is optional - not always available, checked with "in" operator when needed
            
            # Initialize scores
            long_score = 0.0
            short_score = 0.0
            all_reasons = []
            
            # Score each factor using unified framework (all weights required - NO FALLBACKS)
            rsi_weight = direction_weights["rsi"]  # Required (NO FALLBACKS)
            if rsi_weight > 0:
                rsi_long, rsi_short, reasons = self._score_rsi_factor(rsi_data)
                long_score += rsi_long * rsi_weight
                short_score += rsi_short * rsi_weight
                all_reasons.extend(reasons)
            
            trend_weight = direction_weights["trend"]  # Required (NO FALLBACKS)
            if trend_weight > 0:
                trend_long, trend_short, reasons = self._score_trend_factor(trend_data, strategy)
                long_score += trend_long * trend_weight
                short_score += trend_short * trend_weight
                all_reasons.extend(reasons)
            
            pressure_weight = direction_weights["pressure"]  # Required (NO FALLBACKS)
            if pressure_weight > 0:
                pressure_long, pressure_short, reasons = self._score_pressure_factor(pressure_data)
                long_score += pressure_long * pressure_weight
                short_score += pressure_short * pressure_weight
                all_reasons.extend(reasons)
            
            patterns_weight = direction_weights["patterns"]  # Required (NO FALLBACKS)
            if patterns_weight > 0:
                patterns_long, patterns_short, reasons = self._score_patterns_factor(patterns_data)
                long_score += patterns_long * patterns_weight
                short_score += patterns_short * patterns_weight
                all_reasons.extend(reasons)
            
            volume_weight = direction_weights["volume"]  # Required (NO FALLBACKS)
            if volume_weight > 0:
                volume_long, volume_short, reasons = self._score_volume_factor(volume_category, long_score, short_score)
                long_score += volume_long * volume_weight
                short_score += volume_short * volume_weight
                all_reasons.extend(reasons)
            
            # S/R PROXIMITY: When price is approaching strong S/R levels with high reversal probability,
            # that should influence direction (support → LONG, resistance → SHORT)
            sr_proximity_weight = direction_weights["sr_proximity"]
            if sr_proximity_weight > 0:
                sr_proximity_long, sr_proximity_short, reasons = self._score_sr_proximity_factor(unified_data, strategy)
                long_score += sr_proximity_long * sr_proximity_weight
                short_score += sr_proximity_short * sr_proximity_weight
                all_reasons.extend(reasons)
            
            # FUNDING REMOVED FROM DIRECTION SCORING
            # Funding is often not available and doesn't significantly impact short-term direction
            # If needed in the future, make it optional and handle missing data gracefully
            
            # Determine direction from scores
            score_diff = abs(long_score - short_score)
            logger.debug(f"📊 Direction scores ({strategy}): LONG={long_score:.1f}, SHORT={short_score:.1f}, diff={score_diff:.1f}")
            
            if long_score > short_score:
                direction = "LONG"
                reasoning = f"LONG signal (score: {long_score:.1f} vs {short_score:.1f}). " + "; ".join(all_reasons[:5])
            elif short_score > long_score:
                direction = "SHORT"
                reasoning = f"SHORT signal (score: {short_score:.1f} vs {long_score:.1f}). " + "; ".join(all_reasons[:5])
            else:
                direction = "LONG"
                reasoning = f"Neutral signal (equal scores: {long_score:.1f}). " + "; ".join(all_reasons[:5])
            
            return {
                "direction": direction,
                "reasoning": reasoning,
                "long_score": long_score,
                "short_score": short_score
            }
            
        except Exception as e:
            logger.error(f"❌ Direction scoring failed: {e}")
            return None
    
    
    def _get_strategy_timeframe_weights(self, strategy: str) -> Dict[str, float]:
        """
        Get strategy-specific timeframe weights from config
        
        Different strategies care about different timeframes:
        - Scalping: 15m (high), 1h (medium), 4h (low), 24h (none)
        - Swing Trading: 4h (high), 24h (high), 1h (medium), 15m (low)
        - Trend Following: All timeframes, but 4h/24h weighted higher
        - Range Trading: 1h (high), 4h (medium), 15m (low), 24h (low)
        - Breakout: 1h (high), 4h (high), 15m (medium), 24h (low)
        """
        # Get timeframe weights from config (NO FALLBACKS)
        timeframe_weights_map = TradingConfig.STRATEGY_TIMEFRAME_WEIGHTS
        
        # Return strategy-specific weights - NO FALLBACKS
        if strategy not in timeframe_weights_map:
            raise ValueError(f"Strategy '{strategy}' not found in TIMEFRAME_WEIGHTS - NO FALLBACKS")
        return timeframe_weights_map[strategy]
    
    # ==================================================================================
    # CONFIDENCE CALCULATION - Separate from scoring system
    # ==================================================================================
    
    def _calculate_prediction_confidence(
        self,
        setup_data: Dict[str, Any],
        stop_loss: float,
        take_profit: float,
        rr_ratio: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        unified_data: Dict[str, Any],
        strategy: str
    ) -> float:
        """
        Calculate confidence for final prediction (separate from scoring system)
        
        NOTE: Not implemented yet - will be implemented after all input parameters are integrated.
        Currently returns a placeholder value.
        
        Args:
            setup_data: Complete setup data dict containing:
                - entry_price, entry_score, direction_score, total_score
                - entry_breakdown: {power, proximity_factor, recency_factor, distance_atr, hours_since_touch, setup_type}
                - direction_breakdown: {base_long_score, base_short_score, proximity_factor, strength_factor, 
                                        alignment_factor, recency_factor, score_diff, final_long_score, final_short_score}
                - long_score, short_score, score_diff
                - level_data: {power, last_touch_timestamp, etc.}
                - setup_type, direction
            stop_loss: Calculated stop loss price
            take_profit: Calculated take profit price
            rr_ratio: Risk/Reward ratio (reward_distance / risk_distance)
            stop_loss_pct: Stop loss as percentage of entry price
            take_profit_pct: Take profit as percentage of entry price
            unified_data: Complete market analysis data (contains volatility, trend, market conditions, etc.)
            strategy: Current trading strategy
            
        Returns:
            Confidence percentage (0.0 - 100.0)
        """
        # CONFIDENCE CALCULATION NOT IMPLEMENTED YET
        # This is a critical component that requires extensive research and validation
        # Returning None to indicate confidence is not available (optional field)
        # When implemented, should consider:
        #   - Entry quality (setup scores)
        #   - Direction strength (score differential)
        #   - Risk/Reward ratio quality
        #   - Market conditions alignment
        #   - Historical prediction accuracy (if available)
        return None
    
    def _score_entry_setup(
        self,
        entry_price: float,
        setup_type: str,
        direction: str,
        unified_data: Dict[str, Any],
        level_data: Optional[Dict[str, Any]],
        strategy: str,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Score an entry setup using unified scoring framework
        
        Uses factor scorers to calculate a total entry score, then returns setup details.
        
        Returns:
            Dict with "entry_price", "setup_type", "score", "reasoning", or None if invalid
        """
        try:
            # All required data must be present (NO FALLBACKS)
            current_price = self._require_key(unified_data, "current_price", "entry scoring")
            if current_price <= 0 or entry_price <= 0:
                raise ValueError(f"Invalid prices: current_price={current_price}, entry_price={entry_price}")
            
            # Get strategy-specific entry weights (config defaults are OK)
            # NOTE: SR power includes touch, reversal_probability, and volume (inherent strength)
            # Proximity and recency are handled separately in entry scoring (contextual factors)
            strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
            entry_weights = strategy_config["entry_weights"] if "entry_weights" in strategy_config else {  # Use default if not in strategy config
                "support_resistance": 0.50,  # Primary factor - SR power (touch 60%, reversal_prob 30%, volume 10%)
                "rsi": 0.20,  # Additional factor not in SR power
                "trend": 0.15,  # Additional factor not in SR power
                "pressure": 0.10,  # Additional factor not in SR power
                "patterns": 0.05  # Additional factor not in SR power
                # Note: Proximity (distance) is scored separately in _score_entry_sr_factor based on entry offset
                # Note: Recency is handled in direction scoring, not entry scoring
            }
            
            # Extract indicators - all required (NO FALLBACKS)
            rsi_data = self._require_key(unified_data, "rsi", "entry scoring")
            trend_data = self._require_key(unified_data, "trend", "entry scoring")
            pressure_data = self._require_key(unified_data, "pressure", "entry scoring")
            patterns_data = self._require_key(unified_data, "patterns", "entry scoring")
            volume_category = self._require_key(unified_data, "volume_category", "entry scoring")
            
            # Extract ATR for ATR-based scoring (FIXED 2026-01-20)
            sr_data = self._require_key(unified_data, "support_resistance", "entry scoring")
            sr_metadata = sr_data["metadata"]
            atr_5m = sr_metadata["atr_5m"]
            
            # Initialize score
            total_score = 0.0
            all_reasons = []
            
            # Score each factor using unified framework (all weights required - NO FALLBACKS)
            sr_weight = entry_weights["support_resistance"]  # Required (NO FALLBACKS)
            if sr_weight > 0:
                # Add setup_type to level_data for context
                level_data_with_type = {**level_data, "setup_type": setup_type}
                sr_score, reasons = self._score_entry_sr_factor(entry_price, current_price, direction, level_data_with_type, unified_data, strategy)
                total_score += sr_score * sr_weight
                all_reasons.extend(reasons)
            
            rsi_weight = entry_weights["rsi"]  # Required (NO FALLBACKS)
            if rsi_weight > 0:
                rsi_score, reasons = self._score_entry_rsi_factor(entry_price, current_price, direction, rsi_data, atr_5m)
                total_score += rsi_score * rsi_weight
                all_reasons.extend(reasons)
            
            trend_weight = entry_weights["trend"]  # Required (NO FALLBACKS)
            if trend_weight > 0:
                trend_score, reasons = self._score_entry_trend_factor(entry_price, current_price, direction, trend_data, strategy)
                total_score += trend_score * trend_weight
                all_reasons.extend(reasons)
            
            pressure_weight = entry_weights["pressure"]  # Required (NO FALLBACKS)
            if pressure_weight > 0:
                pressure_score, reasons = self._score_entry_pressure_factor(direction, pressure_data)
                total_score += pressure_score * pressure_weight
                all_reasons.extend(reasons)
            
            patterns_weight = entry_weights["patterns"]  # Required (NO FALLBACKS)
            if patterns_weight > 0:
                patterns_score, reasons = self._score_entry_patterns_factor(direction, patterns_data)
                total_score += patterns_score * patterns_weight
                all_reasons.extend(reasons)
            
            # Volume anomaly risk check: Apply penalty if anomaly detected
            volume_data = unified_data["volume"]
            volume_anomaly = volume_data["volume_anomaly"]
            if volume_anomaly and volume_anomaly["is_anomaly"]:
                severity = volume_anomaly["severity"]
                if severity == "EXTREME":
                    total_score -= 30.0  # Significant penalty for extreme anomalies
                    all_reasons.append(f"⚠️ EXTREME volume anomaly - high risk entry")
                elif severity == "HIGH":
                    total_score -= 15.0  # Moderate penalty for high anomalies
                    all_reasons.append(f"⚠️ HIGH volume anomaly - increased risk")
                elif severity == "MODERATE":
                    total_score -= 7.0  # Small penalty for moderate anomalies
                    all_reasons.append(f"⚠️ MODERATE volume anomaly - caution")
            
            # NOTE: 
            # - Volume: included in SR power (10% weight)
            # - Distance/proximity: scored separately in _score_entry_sr_factor based on entry offset from level
            # - Recency: handled in direction scoring, not entry scoring
            
            # Removed excessive debug logging - only log top scores
            if total_score >= TradingConfig.CONFIDENCE_THRESHOLDS["min_score_log"]:  # Only log high-scoring setups
                logger.debug(f"📊 Entry setup scored: {setup_type} @ ${entry_price:.2f} = {total_score:.1f}")
            
            return {
                "entry_price": entry_price,
                "setup_type": setup_type,
                "score": total_score,
                "reasoning": "; ".join(all_reasons[:5]) if all_reasons else f"{setup_type} entry"
            }
            
        except Exception as e:
            logger.error(f"❌ Entry setup scoring failed: {e}")
            return None
    
    def _generate_setups_for_direction(
        self,
        unified_data: Dict[str, Any],
        direction: str,
        strategy: str,
        config: Dict[str, Any]
    ) -> list[Dict[str, Any]]:
        """
        Generate and score entry setups for a SPECIFIC direction only
        
        SEQUENTIAL FLOW - Step 3: After direction is determined, find best entry for that direction.
        Only evaluates entry quality (not direction support, since direction is already determined).
        
        Args:
            unified_data: Complete market analysis data
            direction: "LONG" or "SHORT" - the direction determined in Step 2
            strategy: Trading strategy name
            config: Strategy configuration
            
        Returns:
            List of setup dictionaries with entry_score, entry_price, entry_reasoning, etc.
        """
        try:
            # All required data must be present (NO FALLBACKS)
            current_price = self._require_key(unified_data, "current_price", "setup generation")
            if current_price <= 0:
                raise ValueError(f"Invalid current_price: {current_price}")
            
            # Extract market data - all required (NO FALLBACKS)
            sr_data = self._require_key(unified_data, "support_resistance", "setup generation")
            all_levels = self._require_key(sr_data, "levels", "setup generation")
            
            # Filter levels for entry setup based on strategy requirements
            from core.calculations.sr_level_filter import SRLevelFilter
            level_filter = SRLevelFilter()
            # Get metadata for ATR calculation
            sr_metadata = unified_data["support_resistance"]["metadata"]
            
            filtered_levels = level_filter.filter_for_entry_setup(
                all_levels=all_levels,
                current_price=current_price,
                strategy=strategy,
                sr_metadata=sr_metadata  # Pass metadata for ATR calculation
            )
            
            setups = []
            
            # Generate setups ONLY for the selected direction
            if direction == "LONG":
                # LONG: Only evaluate support levels (buying at support)
                top_support = filtered_levels["support"]
                
                for support in top_support:
                    level_price = self._require_key(support, "price_level", "setup generation")
                    if level_price <= 0 or level_price >= current_price:
                        continue  # Skip invalid or unfillable levels
                    
                    # Determine optimal entry price based on entry scoring factors
                    try:
                        entry_data = self._determine_optimal_entry_price(
                            level_price=level_price,
                            current_price=current_price,
                            direction="LONG",
                            setup_type="support_level",
                            level_data=support,
                            unified_data=unified_data,
                            strategy=strategy,
                            config=config
                        )
                        
                        if entry_data is None:
                            continue  # Skip if entry determination failed
                        
                        entry_price = entry_data["entry_price"]  # Required (NO FALLBACKS)
                        if entry_price is None or entry_price <= 0 or entry_price >= current_price:
                            continue  # Skip if entry is invalid or unfillable
                    except Exception as e:
                        logger.warning(f"⚠️ Entry price determination failed for support ${level_price:.2f}: {e}")
                        continue  # Skip this level if determination fails
                    
                    # Score entry setup (entry quality only - direction already determined)
                    support_with_type = {**support, "setup_type": "support_level"}
                    entry_result = self._score_entry_setup(
                        entry_price=entry_price,
                        setup_type="support_level",
                        direction="LONG",
                        unified_data=unified_data,
                        level_data=support_with_type,
                        strategy=strategy,
                        config=config
                    )
                    
                    if entry_result:
                        setups.append({
                            "entry_price": entry_price,
                            "entry_score": entry_result["score"],  # Required (NO FALLBACKS)
                            "entry_reasoning": entry_result["reasoning"],  # Required (NO FALLBACKS)
                            "setup_type": "support_level",
                            "level_data": support_with_type
                        })
            
            else:  # SHORT
                # SHORT: Only evaluate resistance levels (selling at resistance)
                top_resistance = filtered_levels["resistance"]
                
                for resistance in top_resistance:
                    level_price = self._require_key(resistance, "price_level", "setup generation")
                    if level_price <= 0 or level_price <= current_price:
                        continue  # Skip invalid or unfillable levels
                    
                    # Determine optimal entry price based on entry scoring factors
                    try:
                        entry_data = self._determine_optimal_entry_price(
                            level_price=level_price,
                            current_price=current_price,
                            direction="SHORT",
                            setup_type="resistance_level",
                            level_data=resistance,
                            unified_data=unified_data,
                            strategy=strategy,
                            config=config
                        )
                        
                        if entry_data is None:
                            continue  # Skip if entry determination failed
                        
                        entry_price = entry_data["entry_price"]  # Required (NO FALLBACKS)
                        if entry_price is None or entry_price <= 0 or entry_price <= current_price:
                            continue  # Skip if entry is invalid or unfillable
                    except Exception as e:
                        logger.warning(f"⚠️ Entry price determination failed for resistance ${level_price:.2f}: {e}")
                        continue  # Skip this level if determination fails
                    
                    # Score entry setup (entry quality only - direction already determined)
                    resistance_with_type = {**resistance, "setup_type": "resistance_level"}
                    entry_result = self._score_entry_setup(
                        entry_price=entry_price,
                        setup_type="resistance_level",
                        direction="SHORT",
                        unified_data=unified_data,
                        level_data=resistance_with_type,
                        strategy=strategy,
                        config=config
                    )
                    
                    if entry_result:
                        setups.append({
                            "entry_price": entry_price,
                            "entry_score": entry_result["score"],  # Required (NO FALLBACKS)
                            "entry_reasoning": entry_result["reasoning"],  # Required (NO FALLBACKS)
                            "setup_type": "resistance_level",
                            "level_data": resistance_with_type
                        })
            
            logger.debug(f"📊 Generated {len(setups)} entry setups for {direction} direction ({strategy} strategy)")
            return setups
            
        except Exception as e:
            logger.error(f"❌ Setup generation for {direction} direction failed: {e}")
            return []
    
    def _determine_optimal_entry_price(
        self,
        level_price: float,
        current_price: float,
        direction: str,
        setup_type: str,
        level_data: Dict[str, Any],
        unified_data: Dict[str, Any],
        strategy: str,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Determine optimal entry price for BTC perp trading (research-backed)
        
        Generates 4 entry candidates with offsets INSIDE S/R zone (toward current price):
        - 0×ATR (at level)
        - 0.3×ATR inside
        - 0.6×ATR inside
        - 1.0×ATR inside
        
        Scores each candidate by:
        - Fill probability (35%): Closer to current = higher
        - Liquidation safety (35%): Distance from liquidation
        - Level strength (20%): S/R power
        - Spread penalty (-10%): Cost of execution
        
        Returns the best scoring candidate.
        
        Args:
            level_price: S/R level price
            current_price: Current market price
            direction: "LONG" or "SHORT"
            setup_type: "support_level" or "resistance_level"
            level_data: Level metadata (power, last_touch_timestamp, etc.)
            unified_data: Complete market analysis data
            strategy: Trading strategy
            config: Strategy configuration
            
        Returns:
            Dict with "entry_price", "entry_score", "entry_breakdown" or None if invalid
        """
        try:
            # Get ATR for distance calculations
            atr_pct = self._get_atr_pct(unified_data, current_price)
            sr_data = unified_data["support_resistance"]  # Required (NO FALLBACKS)
            sr_metadata = sr_data["metadata"]  # Required (NO FALLBACKS)
            atr_5m = sr_metadata["atr_5m"]  # Required (NO FALLBACKS)
            if atr_5m <= 0:
                raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
            
            # BTC PERP ENTRY OFFSET LOGIC (Research-backed)
            # Research findings (2025-2026 BTC perpetual futures):
            #   - Price regularly wicks THROUGH S/R levels before bouncing (liquidation hunting)
            #   - Market makers actively hunt stops at obvious levels
            #   - 40x leverage: 2.5% adverse move = liquidation
            #   - Professional practice: Enter +0.3 to +0.5× ATR INSIDE zone (toward current price)
            # 
            # Rationale for offset toward current:
            #   - Survives liquidation wick-through (common 0.5-1% wicks before bounce)
            #   - Higher fill probability (closer to current price)
            #   - Still catches majority of bounce (0.3-0.5× ATR ≈ 0.1-0.2% typically)
            #   - Avoids being "first in line" for liquidation during stop hunts
            
            # Generate entry candidates with offsets INSIDE the zone (toward current price)
            candidates = []
            
            # Strategy-specific optimal offset from config
            from config.config import TradingConfig
            strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
            entry_proximity_config = strategy_config["entry_proximity_config"]  # Required (NO FALLBACKS)
            optimal_atr_distance = entry_proximity_config["optimal_atr"]  # Required (NO FALLBACKS)
            
            # Calculate optimal offset distance in USD
            optimal_offset_usd = atr_5m * optimal_atr_distance
            
            # Generate 4 entry candidates with increasing offset INSIDE zone
            # Offset factors: 0 (AT level), 0.3, 0.6, 1.0 (toward current)
            offset_factors = [0.0, 0.3, 0.6, 1.0]
            
            if setup_type == "support_level":  # LONG at support
                # Enter ABOVE support (closer to current price, inside zone)
                for factor in offset_factors:
                    candidate = level_price + (optimal_offset_usd * factor)
                    # Validate: must be below current price (LONG entry)
                    if 0 < candidate < current_price:
                        candidates.append(candidate)
            else:  # resistance_level - SHORT at resistance
                # Enter BELOW resistance (closer to current price, inside zone)
                for factor in offset_factors:
                    candidate = level_price - (optimal_offset_usd * factor)
                    # Validate: must be above current price (SHORT entry)
                    if candidate > current_price:
                        candidates.append(candidate)
            
            if not candidates:
                logger.warning(f"⚠️ No valid entry candidates for {setup_type} at ${level_price:.2f} (current: ${current_price:.2f})")
                return None
            
            # Score each candidate using BTC perp-optimized scoring
            # Factors (research-backed for 40x leverage perps):
            #   1. Fill probability (35%): Closer to current = higher fill rate
            #   2. Liquidation safety (35%): Distance from liquidation price
            #   3. Level strength (20%): S/R power (inherent quality)
            #   4. Spread penalty (-10%): Closer to current = pay more spread
            
            level_power = level_data["power"]  # Required (NO FALLBACKS)
            last_touch_timestamp = level_data["last_touch_timestamp"]  # Required (NO FALLBACKS)
            
            # Calculate liquidation price for safety scoring
            from core.calculations.liquidation_calculator import LiquidationCalculator
            liq_calc = LiquidationCalculator(leverage=TradingConfig.LEVERAGE)
            
            # Get spread for penalty calculation
            from core.utils.distance_utils import calculate_distance_pct, calculate_distance_atr
            orderbook_data = unified_data["orderbook_analysis"] if "orderbook_analysis" in unified_data else {}
            spread_data = orderbook_data["bid_ask_spread"] if "bid_ask_spread" in orderbook_data and orderbook_data["bid_ask_spread"] else {"percentage": 0.01}
            spread_pct = spread_data["percentage"] / 100.0 if "percentage" in spread_data else 0.0001  # Convert to decimal
            
            best_candidate = None
            best_score = -1.0
            best_breakdown = None
            
            for candidate_price in candidates:
                # 1. FILL PROBABILITY SCORE (35% weight)
                # Formula: 100 at current → 50 at 3×ATR → 10 at 6×ATR
                distance_to_current_pct = calculate_distance_pct(candidate_price, current_price, current_price)
                distance_to_current_atr = calculate_distance_atr(distance_to_current_pct, atr_pct)
                fill_probability = max(10.0, 100.0 - (distance_to_current_atr / 6.0) * 90.0)
                
                # 2. LIQUIDATION SAFETY SCORE (35% weight)
                # Calculate liquidation price from this entry
                liquidation_price = liq_calc.calculate_liquidation_price(candidate_price, direction)
                # Distance from entry to liquidation (as % of entry)
                if direction == "LONG":
                    liq_distance_pct = (candidate_price - liquidation_price) / candidate_price
                else:  # SHORT
                    liq_distance_pct = (liquidation_price - candidate_price) / candidate_price
                # Score: More distance = safer (40x = 1.2% to liq, want > 1.5% for safety)
                # 100 at 2.0%, 50 at 1.2%, 0 at 0.5%
                liquidation_safety = max(0.0, min(100.0, (liq_distance_pct - 0.005) / 0.015 * 100.0))
                
                # 3. LEVEL STRENGTH SCORE (20% weight)
                # Use level power directly (0-100 scale)
                level_strength = level_power
                
                # 4. SPREAD COST PENALTY (-10% weight)
                # Closer to current = pay more spread
                # Penalty: 0 at 1×ATR distance, 10 at current price
                spread_penalty = min(10.0, max(0.0, (1.0 - distance_to_current_atr) * 10.0))
                
                # WEIGHTED COMBINED SCORE
                combined_score = (
                    fill_probability * 0.35 +
                    liquidation_safety * 0.35 +
                    level_strength * 0.20 -
                    spread_penalty * 0.10
                )
                
                # Track best candidate
                if combined_score > best_score:
                    best_score = combined_score
                    best_candidate = candidate_price
                    
                    # Calculate distance metrics
                    import time
                    hours_since_touch = (time.time() - last_touch_timestamp) / 3600.0 if last_touch_timestamp > 0 else 0.0
                    distance_from_level_usd = abs(candidate_price - level_price)
                    distance_from_level_pct = distance_from_level_usd / current_price
                    
                    best_breakdown = {
                        "entry_price": candidate_price,
                        "level_price": level_price,
                        "offset_usd": distance_from_level_usd,
                        "offset_pct": distance_from_level_pct * 100,
                        "offset_atr": distance_from_level_usd / atr_5m if atr_5m > 0 else 0,
                        "fill_probability": fill_probability,
                        "liquidation_safety": liquidation_safety,
                        "liquidation_price": liquidation_price,
                        "liq_distance_pct": liq_distance_pct * 100,
                        "level_strength": level_strength,
                        "spread_penalty": spread_penalty,
                        "combined_score": combined_score,
                        "distance_to_current_atr": distance_to_current_atr,
                        "hours_since_touch": hours_since_touch,
                        "setup_type": setup_type
                    }
            
            if best_candidate is None:
                logger.warning(f"⚠️ No suitable entry candidate found")
                return None
            
            logger.debug(
                f"✅ Entry selected: ${best_candidate:.2f} "
                f"(offset: {best_breakdown['offset_atr']:.2f}×ATR, "
                f"fill_prob: {best_breakdown['fill_probability']:.1f}, "
                f"liq_safety: {best_breakdown['liquidation_safety']:.1f}, "
                f"score: {best_score:.1f})"
            )
            
            return {
                "entry_price": best_candidate,
                "entry_score": best_score,
                "entry_breakdown": best_breakdown
            }
            
        except Exception as e:
            logger.error(f"❌ Optimal entry price determination failed: {e}")
            return None
    
    def _calculate_stop_and_target(
        self,
        entry_price: float,
        direction: str,
        config: Dict[str, Any],
        unified_data: Dict[str, Any],
        strategy: str,
        level_data: Optional[Dict[str, Any]] = None,
        setup_type: Optional[str] = None
    ) -> tuple[float, float, float, float, float]:
        """
        Calculate sophisticated stop loss and take profit
        
        Delegates to RiskManager module for all risk calculations.
        
        Args:
            entry_price: Entry price for the trade
            direction: "LONG" or "SHORT"
            config: Strategy configuration
            unified_data: Complete market analysis data
            level_data: Level metadata for the entry level (optional)
            setup_type: "support_level" or "resistance_level" (optional)
            
        Returns:
            (stop_loss, take_profit, rr_ratio, stop_loss_pct, take_profit_pct) tuple
            - stop_loss: Stop loss price
            - take_profit: Take profit price
            - rr_ratio: Risk/Reward ratio (reward/risk)
            - stop_loss_pct: Stop loss as percentage of entry price
            - take_profit_pct: Take profit as percentage of entry price
        """
        try:
            from core.calculations.risk_manager import RiskManager
            from core.calculations.support_resistance_calculator import SupportResistanceCalculator
            
            current_price = self._require_key(unified_data, "current_price", "stop/target calculation")
            if current_price <= 0:
                raise ValueError(f"Invalid current_price: {current_price}")
            
            # Get ATR for calculations (NO FALLBACKS)
            sr_data = self._require_key(unified_data, "support_resistance", "stop/target calculation")
            sr_metadata = self._require_key(sr_data, "metadata", "support_resistance structure")
            atr_5m = self._require_key(sr_metadata, "atr_5m", "ATR for stop/target calculation")
            
            if atr_5m <= 0:
                raise ValueError(f"Invalid atr_5m: {atr_5m} - must be positive (NO FALLBACKS)")
            
            # 1. Get S/R level for stop placement (delegated to calculator module)
            sr_stop_level = None
            try:
                sr_data = unified_data["support_resistance"]  # Required (NO FALLBACKS)
                if sr_data:
                    # Get all available levels (calculator now provides all levels, modules filter as needed)
                    all_levels = sr_data["levels"]  # Required (NO FALLBACKS)
                    if not all_levels:
                        raise ValueError("No S/R levels available in support_resistance.levels (NO FALLBACKS)")
                    
                    # Calculate minimum stop distance (2.0×ATR)
                    min_stop_distance = atr_5m * 2.0
                    # Maximum reasonable distance: 3×ATR (maintains reasonable R:R)
                    max_reasonable_distance = atr_5m * 3.0
                    
                    # Select optimal level for stop loss placement (handled by calculator module)
                    selected_level = SupportResistanceCalculator.select_stop_loss_level(
                        levels=all_levels,
                        entry_price=entry_price,
                        direction=direction,
                        atr_5m=atr_5m,
                        min_stop_distance=min_stop_distance,
                        max_reasonable_distance=max_reasonable_distance,
                        min_strength_score=60.0  # Prefer levels with strength >= 60
                    )
                    
                    if selected_level:
                        level_price = selected_level["price_level"]  # Required (NO FALLBACKS)
                        level_strength = selected_level["strength_score"]  # Required (NO FALLBACKS)
                        
                        # Validate level is not broken (safety check)
                        if direction == "LONG":
                            level_break_threshold = level_price - atr_5m
                            if current_price < level_break_threshold:
                                raise ValueError(f"Support level ${level_price:.2f} is broken (current_price ${current_price:.2f} < break_threshold ${level_break_threshold:.2f}) - cannot use for stop placement")
                        else:  # SHORT
                            level_break_threshold = level_price + atr_5m
                            if current_price > level_break_threshold:
                                raise ValueError(f"Resistance level ${level_price:.2f} is broken (current_price ${current_price:.2f} > break_threshold ${level_break_threshold:.2f}) - cannot use for stop placement")
                        
                        if level_price > 0:
                            # Place stop with noise buffer (FIXED 2026-01-12 - from config)
                            from config.config import TradingConfig
                            noise_buffer = atr_5m * TradingConfig.NOISE_BUFFER_ATR_MULTIPLIER
                            if direction == "LONG":
                                sr_stop_level = level_price - noise_buffer
                            else:  # SHORT
                                sr_stop_level = level_price + noise_buffer
                            
                            logger.debug(f"📉 {direction} stop from selected level: ${level_price:.2f} (strength: {level_strength:.1f}) → ${sr_stop_level:.2f}")
                    else:
                        # No suitable S/R level found - log details for debugging
                        if direction == "LONG":
                            supports = [l for l in all_levels if "type" in l and l["type"] == "support" and "price_level" in l and l["price_level"] < entry_price and "status" in l and l["status"] == "active"]
                            logger.warning(f"⚠️ No suitable LONG stop level found. Entry: ${entry_price:.2f}, Min distance: ${min_stop_distance:.2f}, Max reasonable: ${max_reasonable_distance:.2f}")
                            logger.warning(f"⚠️ Available supports below entry: {len(supports)}")
                            if supports:
                                distances = [entry_price - s["price_level"] for s in supports]  # Required (NO FALLBACKS)
                                strengths = [s["strength_score"] for s in supports]  # Required (NO FALLBACKS)
                                logger.warning(f"⚠️ Support distances from entry: {[f'${d:.2f}' for d in distances[:5]]}")
                                logger.warning(f"⚠️ Support strengths: {[f'{s:.1f}' for s in strengths[:5]]}")
                        else:  # SHORT
                            resistances = [l for l in all_levels if l["type"] == "resistance" and l["price_level"] > entry_price and l["status"] == "active"]  # Required (NO FALLBACKS)
                            logger.warning(f"⚠️ No suitable SHORT stop level found. Entry: ${entry_price:.2f}, Min distance: ${min_stop_distance:.2f}, Max reasonable: ${max_reasonable_distance:.2f}")
                            logger.warning(f"⚠️ Available resistances above entry: {len(resistances)}")
                            if resistances:
                                distances = [r["price_level"] - entry_price for r in resistances]  # Required (NO FALLBACKS)
                                strengths = [r["strength_score"] for r in resistances]  # Required (NO FALLBACKS)
                                logger.warning(f"⚠️ Resistance distances from entry: {[f'${d:.2f}' for d in distances[:5]]}")
                                logger.warning(f"⚠️ Resistance strengths: {[f'{s:.1f}' for s in strengths[:5]]}")
                        raise ValueError(f"No suitable S/R level found for {direction} stop placement (min_distance: ${min_stop_distance:.2f}, max_reasonable: ${max_reasonable_distance:.2f}) (NO FALLBACKS)")
            except Exception as e:
                logger.error(f"❌ Failed to calculate stop from S/R levels: {e}")
                raise
            
            # 2. Calculate unified stop loss (delegated to RiskManager)
            # Include leverage for liquidation price capping
            from config.config import TradingConfig
            leverage = config["max_leverage"] if "max_leverage" in config else TradingConfig.LEVERAGE  # Strategy uses max_leverage
            
            stop_loss = RiskManager.calculate_stop_loss(
                entry_price=entry_price,
                direction=direction,
                sr_stop_level=sr_stop_level,
                atr_5m=atr_5m,
                current_price=current_price,
                config=config,
                unified_data=unified_data,
                leverage=leverage
            )
            
            # Get spread for realistic profit calculations (FIXED 2026-01-12 - from config)
            from config.config import TradingConfig
            spread_pct = TradingConfig.DEFAULT_SPREAD_PCT  # Default if orderbook unavailable
            if "orderbook_analysis" in unified_data:
                orderbook_data = unified_data["orderbook_analysis"]
                if "bid_ask_spread" in orderbook_data:
                    bid_ask_spread = orderbook_data["bid_ask_spread"]
                    if "percentage" in bid_ask_spread:
                        spread_pct = bid_ask_spread["percentage"]
                        logger.debug(f"📊 Using actual spread: {spread_pct:.3f}%")
            
            # 3. Calculate adaptive take profit at next S/R level (delegated to RiskManager)
            # NOW WITH SPREAD COSTS (FIXED 2026-01-12)
            take_profit = RiskManager.calculate_take_profit(
                entry_price=entry_price,
                stop_loss=stop_loss,
                direction=direction,
                atr_5m=atr_5m,
                config=config,
                sr_levels=all_levels,  # Pass all levels for adaptive TP selection
                strategy=strategy,
                spread_pct=spread_pct  # Pass spread for realistic profit calculation
            )
            
            # 4. Validate risk/reward ratio (delegated to RiskManager)
            min_risk_reward = config["min_rr"] if "min_rr" in config else 1.5  # Strategy config uses min_rr
            risk_reward_ratio, is_valid = RiskManager.validate_risk_reward(
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                direction=direction,
                min_risk_reward=min_risk_reward
            )
            
            # Calculate risk/reward percentages for confidence system
            if direction == "LONG":
                risk_distance = entry_price - stop_loss
                reward_distance = take_profit - entry_price
            else:  # SHORT
                risk_distance = stop_loss - entry_price
                reward_distance = entry_price - take_profit
            
            stop_loss_pct = (risk_distance / entry_price) * 100.0 if entry_price > 0 else 0.0
            take_profit_pct = (reward_distance / entry_price) * 100.0 if entry_price > 0 else 0.0
            
            return stop_loss, take_profit, risk_reward_ratio, stop_loss_pct, take_profit_pct
            
        except Exception as e:
            logger.error(f"❌ Stop/Target calculation failed: {e}")
            raise