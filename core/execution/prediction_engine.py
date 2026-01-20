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
from .position_sizer import PositionSizer


@dataclass
class TradingPrediction:
    """Trading prediction/signal structure"""
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0.0 - 100.0 (percentage)
    reasoning: str
    strategy: str
    timestamp: float
    risk_reward_ratio: float = 0.0  # Actual R:R achieved (for position sizing)


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
            "standard": self._predict_standard,
            "scalping": self._predict_scalping,
            "swing_trading": self._predict_swing_trading,
            "trend_following": self._predict_trend_following,
            "breakout": self._predict_breakout,
            "range_trading": self._predict_range_trading,
            "low_volatility_range": self._predict_low_volatility_range,
            "high_volatility": self._predict_high_volatility,
            "spike_hunting": self._predict_spike_hunting,
        }
        
        method = strategy_methods[strategy] if strategy in strategy_methods else self._predict_standard
        return method(unified_data, strategy_config)
    
    def _predict_standard(self, unified_data: Dict[str, Any], config: Dict[str, Any], strategy: str = "standard") -> Optional[TradingPrediction]:
        """
        Standard strategy prediction logic (also used as base for other strategies)
        
        Uses hybrid approach with contextual direction scoring:
        1. Generate all potential setups (both LONG and SHORT)
        2. Score each setup with: entry_quality + contextual_direction_support
           - Entry quality: SR strength, proximity, reversal probability, etc.
           - Contextual direction: considers entry proximity, level strength, and alignment
        3. Select best overall combination
        4. Calculate stop loss and take profit from config
        """
        # Generate and score all potential setups (both LONG and SHORT)
        all_setups = self._generate_all_setups(unified_data, strategy, config)
        if not all_setups:
            logger.debug(f"⏸️ No valid setups found for {strategy} strategy")
            return None
        
        # Select best overall setup (highest combined score)
        best_setup = max(all_setups, key=lambda x: x["total_score"])  # Required (NO FALLBACKS)
        
        direction = best_setup["direction"]
        entry_price = best_setup["entry_price"]
        entry_score = best_setup["entry_score"]
        direction_score = best_setup["direction_score"]
        total_score = best_setup["total_score"]
        
        logger.debug(f"📊 Best setup: {direction} @ ${entry_price:.2f} (entry: {entry_score:.1f}, direction: {direction_score:.1f}, total: {total_score:.1f})")
        
        # Calculate stop_loss and take_profit with sophisticated logic
        # This already calculates R:R ratio internally, so we capture it
        best_setup_level_data = best_setup["level_data"]  # Required (NO FALLBACKS)
        best_setup_type = best_setup["setup_type"]  # Required (NO FALLBACKS)
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
        combined_reasoning = f"{best_setup['direction_reasoning']}. Entry: {best_setup['entry_reasoning']}"
        
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
    
    @staticmethod
    def calculate_position_size(
        balance: float,
        base_position_size_pct: float,
        risk_reward_ratio: float,
        leverage: int,
        entry_price: float
    ) -> Dict[str, Any]:
        """
        Calculate position size using shared PositionSizer
        
        DELEGATED to PositionSizer for unified logic across all execution engines
        (Predictions and Reactions use identical sizing)
        
        Args:
            balance: Current account balance
            base_position_size_pct: Base position size from strategy config
            risk_reward_ratio: Achieved R:R ratio
            leverage: Trading leverage
            entry_price: Entry price for the trade
            
        Returns:
            Position sizing result with all calculated values
        """
        return PositionSizer.calculate_position_size(
            balance=balance,
            base_position_size_pct=base_position_size_pct,
            risk_reward_ratio=risk_reward_ratio,
            leverage=leverage,
            entry_price=entry_price
        )
    
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
        return self._predict_standard(unified_data, config, "scalping")
    
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
            if liquidity_score < 0.5:
                logger.debug(f"⏸️ Insufficient liquidity for scalping: {liquidity_score:.2f}")
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
        """Swing trading strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "swing_trading")
    
    def _predict_trend_following(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Trend following strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "trend_following")
    
    def _predict_breakout(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Breakout strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "breakout")
    
    def _predict_range_trading(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Range trading strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "range_trading")
    
    def _predict_low_volatility_range(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Low volatility range strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "low_volatility_range")
    
    def _predict_high_volatility(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """High volatility strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "high_volatility")
    
    def _predict_spike_hunting(self, unified_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Spike hunting strategy prediction logic - uses strategy-specific direction/entry weights"""
        return self._predict_standard(unified_data, config, "spike_hunting")
    
    def _determine_direction(self, unified_data: Dict[str, Any], strategy: str) -> Optional[Dict[str, Any]]:
        """
        Determine trade direction using unified scoring framework (global - no entry context)
        
        NOTE: This method returns GLOBAL direction scores (not contextual).
        For entry-specific direction scoring, use _score_direction_for_entry instead.
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
        Score patterns factor for direction determination
        
        Returns:
            (patterns_long_score, patterns_short_score, reasons)
        """
        patterns_nested = self._require_key(patterns_data, "patterns_nested", "patterns factor scoring")
        reversal_patterns = self._require_key(patterns_nested, "reversal_patterns", "patterns factor scoring")
        continuation_patterns = self._require_key(patterns_nested, "continuation_patterns", "patterns factor scoring")
        
        patterns_long = 0.0
        patterns_short = 0.0
        reasons = []
        
        bullish_reversals = [p for p in reversal_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BULLISH"]
        if bullish_reversals:
            patterns_long = 100.0
            reasons.append(f"Bullish reversal pattern detected ({len(bullish_reversals)})")
        
        bearish_reversals = [p for p in reversal_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BEARISH"]
        if bearish_reversals:
            patterns_short = 100.0
            reasons.append(f"Bearish reversal pattern detected ({len(bearish_reversals)})")
        
        bullish_continuations = [p for p in continuation_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BULLISH"]
        if bullish_continuations:
            patterns_long += 50.0
            reasons.append(f"Bullish continuation pattern ({len(bullish_continuations)})")
        
        bearish_continuations = [p for p in continuation_patterns if isinstance(p, dict) and "direction" in p and p["direction"] == "BEARISH"]
        if bearish_continuations:
            patterns_short += 50.0
            reasons.append(f"Bearish continuation pattern ({len(bearish_continuations)})")
        
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
        
        # For limit orders, entry should be AT or very close to the S/R level (distance ≈ 0)
        # This ensures the limit order can fill when price reaches the level
        
        if setup_type in ["support_level", "resistance_level"]:
            # For direct S/R level entries: entry should be optimally offset from the level
            # LONG at support: entry at or slightly above support - catches bounce
            # SHORT at resistance: entry at or slightly below resistance - catches bounce down
            if setup_type == "support_level":
                # LONG: entry should be at or slightly ABOVE support
                if distance_pct == 0.0:  # Exactly at support (0% offset) - ideal
                    score = min(100.0, score * 1.2)  # 20% bonus for entry exactly at support
                    reasons.append(f"Entry exactly at support (0% offset) - optimal (power: {level_power:.1f})")
                elif 0.0 < distance_pct <= optimal_threshold:  # Optimal range: 0% to 0.5×ATR above support
                    score = min(100.0, score * 1.1)  # 10% bonus for optimal offset above support
                    reasons.append(f"Optimal entry above support @ {distance_pct*100:.3f}% (≤{optimal_threshold*100:.3f}%, power: {level_power:.1f})")
                elif distance_pct <= acceptable_threshold:  # Still acceptable: 0.5×ATR to 1.25×ATR
                    score = min(100.0, score * 1.0)  # No bonus/penalty
                    reasons.append(f"Entry above support @ {distance_pct*100:.3f}% (≤{acceptable_threshold*100:.3f}%, power: {level_power:.1f})")
                else:
                    score = max(0.0, score * 0.8)  # Penalty if too far from support
                    reasons.append(f"Entry too far from support ({distance_pct*100:.3f}% > {too_far_threshold*100:.3f}%)")
            else:  # resistance_level
                # SHORT: entry should be at or slightly BELOW resistance
                # distance_pct = abs(entry_price - level_price) / current_price
                # For resistance: entry_price <= level_price (at or below), so distance is positive (from abs)
                if distance_pct == 0.0:  # Exactly at resistance (0% offset) - ideal
                    score = min(100.0, score * 1.2)  # 20% bonus for entry exactly at resistance
                    reasons.append(f"Entry exactly at resistance (0% offset) - optimal (power: {level_power:.1f})")
                elif 0.0 < distance_pct <= optimal_threshold:  # Optimal range: 0% to 0.5×ATR below resistance
                    score = min(100.0, score * 1.1)  # 10% bonus for optimal offset below resistance
                    reasons.append(f"Optimal entry below resistance @ {distance_pct*100:.3f}% (≤{optimal_threshold*100:.3f}%, power: {level_power:.1f})")
                elif distance_pct <= acceptable_threshold:  # Still acceptable: 0.5×ATR to 1.25×ATR
                    score = min(100.0, score * 1.0)  # No bonus/penalty
                    reasons.append(f"Entry below resistance @ {distance_pct*100:.3f}% (≤{acceptable_threshold*100:.3f}%, power: {level_power:.1f})")
                else:
                    score = max(0.0, score * 0.8)  # Penalty if too far from resistance
                    reasons.append(f"Entry too far from resistance ({distance_pct*100:.3f}% > {too_far_threshold*100:.3f}%)")
        
        else:
            # Unknown setup type - use default scoring with ATR-based threshold
            near_threshold = atr_pct * 2.5  # 2.5×ATR = reasonable "near" distance
            if distance_pct < near_threshold:
                reasons.append(f"S/R level reference (power: {level_power:.1f}, distance: {distance_pct*100:.3f}%)")
            else:
                score = max(0.0, score * 0.8)  # Penalty
                reasons.append(f"Far from S/R level (distance: {distance_pct*100:.3f}% > {near_threshold*100:.3f}%)")
        
        return score, reasons
    
    def _score_entry_rsi_factor(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        rsi_data: Dict[str, Any]
    ) -> tuple[float, list]:
        """
        Score RSI alignment factor for entry setup
        
        Returns:
            (rsi_score, reasons)
        """
        rsi_value = self._require_key(rsi_data, "rsi", "entry RSI factor scoring")
        rsi_trend = self._require_key(rsi_data, "rsi_trend", "entry RSI factor scoring")
        
        score = 0.0
        reasons = []
        
        # Entry price relative to current price
        price_diff_pct = (entry_price - current_price) / current_price if current_price > 0 else 0.0
        
        # Get ATR for mathematically justified thresholds (NO FALLBACKS)
        # Note: This method doesn't have unified_data parameter, so ATR-based threshold cannot be used
        # Use fixed threshold as fallback (not ideal, but method signature limitation)
        # TODO: Refactor method to accept unified_data parameter for ATR-based threshold
        significant_diff_threshold = 0.0025  # 0.25% = reasonable threshold (should be 1.25×ATR if available)
        
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
        volume_category: str
    ) -> tuple[float, list]:
        """
        Score volume confirmation factor for entry setup
        
        Returns:
            (volume_score, reasons)
        """
        score = 0.0
        reasons = []
        
        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            score = 100.0
            reasons.append(f"High volume confirms entry ({volume_category})")
        elif volume_category in ["NORMAL"]:
            score = 50.0
            reasons.append("Normal volume")
        else:
            score = 20.0
            reasons.append(f"Low volume ({volume_category})")
        
        return score, reasons
    
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
        too_close_threshold = atr_pct * 0.25  # 0.25×ATR
        optimal_max_threshold = atr_pct * 1.25  # 1.25×ATR
        moderate_max_threshold = atr_pct * 2.5  # 2.5×ATR
        far_max_threshold = atr_pct * 5.0  # 5×ATR
        
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
        This is the base method - use _score_direction_for_entry for entry-specific scoring.
        
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
            # NOTE: S/R is NOT used for direction scoring (only for entry/exit determination)
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
            
            # S/R REMOVED FROM DIRECTION SCORING
            # S/R levels determine WHERE to enter/exit, NOT direction
            # Direction is determined by: trend, momentum, pressure, volume
            
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
    
    def _score_direction_for_entry(
        self,
        unified_data: Dict[str, Any],
        strategy: str,
        entry_price: float,
        entry_direction: str,
        level_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Score direction with entry-specific context (contextual direction scoring)
        
        Considers:
        1. Base direction signals (trend, RSI, pressure, etc.)
        2. Entry level proximity (direction signals weighted by distance to entry)
        3. Entry level strength (stronger levels align better with direction)
        4. Alignment check (how well this specific entry level aligns with direction signals)
        
        Args:
            unified_data: Complete market analysis data
            strategy: Trading strategy name
            entry_price: Entry price for this setup
            entry_direction: "LONG" or "SHORT" - the direction of this entry
            level_data: Optional S/R level data for this entry
            
        Returns:
            Dict with "direction", "reasoning", "long_score", "short_score" (contextualized)
        """
        try:
            # Get base direction scores (global market conditions)
            base_direction_result = self._score_direction(unified_data, strategy)
            if not base_direction_result:
                return None
            
            base_long_score = base_direction_result["long_score"]  # Required (NO FALLBACKS)
            base_short_score = base_direction_result["short_score"]  # Required (NO FALLBACKS)
            
            # Initialize contextual scores (start with base scores)
            contextual_long_score = base_long_score
            contextual_short_score = base_short_score
            
            current_price = self._require_key(unified_data, "current_price", "contextual direction scoring")
            if current_price <= 0 or entry_price <= 0:
                raise ValueError(f"Invalid prices: current_price={current_price}, entry_price={entry_price}")
            
            # Calculate entry level context factors
            proximity_factor = 1.0  # Default: no proximity adjustment
            recency_factor = 1.0    # Default: no recency adjustment
            strength_factor = 1.0   # Default: no strength adjustment
            alignment_factor = 1.0  # Default: no alignment adjustment
            distance_atr = 0.0
            level_strength = 0.0
            
            if level_data:
                level_price = level_data["price_level"]  # Required (NO FALLBACKS)
                from core.utils.level_utils import get_level_power
                level_power = get_level_power(level_data, default=None)  # Will raise if missing (NO FALLBACKS)
                last_touch_timestamp = level_data["last_touch_timestamp"]  # Required (NO FALLBACKS)
                
                # 1. PROXIMITY FACTOR: Direction signals more relevant when entry is closer to current price
                # Closer entries = direction signals are more immediately relevant
                # Further entries = direction signals may change before price reaches entry
                try:
                    atr_pct = self._get_atr_pct(unified_data, current_price)
                    from core.calculations.proximity_calculator import ProximityCalculator
                    from core.utils.distance_utils import calculate_distance_pct, calculate_distance_atr as calc_dist_atr
                    
                    proximity_factor = ProximityCalculator.calculate_proximity_factor(
                        entry_price=entry_price,
                        reference_price=current_price,
                        atr_pct=atr_pct,
                        strategy=strategy,
                        context="direction"
                    )
                    
                    # Calculate distance in ATR units for reasoning
                    distance_pct_val = calculate_distance_pct(entry_price, current_price, current_price)
                    distance_atr = calc_dist_atr(distance_pct_val, atr_pct)
                except Exception:
                    proximity_factor = 1.0  # Default if calculation fails
                    distance_atr = 0.0
                
                # 2. RECENCY FACTOR: More recent touches = level still active and relevant
                # Recent levels are more likely to still be valid support/resistance
                from core.calculations.recency_calculator import RecencyCalculator
                recency_factor = RecencyCalculator.calculate_recency_factor(
                    last_touch_timestamp=last_touch_timestamp,
                    strategy=strategy
                )
                
                # 3. POWER FACTOR: Stronger entry levels align better with direction signals
                # Strong support + strong LONG signals = better than weak support + strong LONG signals
                # Normalize power (0-100) to factor (0.7-1.3)
                power_normalized = level_power / 100.0  # 0.0 to 1.0
                strength_factor = 0.7 + (power_normalized * 0.6)  # Range: 0.7 to 1.3
                level_strength = level_power
                
                # 4. ALIGNMENT FACTOR: Check how well this specific entry level aligns with direction signals
                # For LONG at support: if LONG signals are strong, alignment is good
                # For SHORT at resistance: if SHORT signals are strong, alignment is good
                # For LONG at support: if SHORT signals are strong, alignment is poor (conflict)
                setup_type = level_data["setup_type"]  # Required (NO FALLBACKS)
                
                if entry_direction == "LONG" and setup_type == "support_level":
                    # LONG at support: good alignment if LONG signals > SHORT signals
                    direction_diff = base_long_score - base_short_score
                    if direction_diff > 20.0:  # Strong LONG preference
                        alignment_factor = 1.2  # Boost for good alignment
                    elif direction_diff > 10.0:  # Moderate LONG preference
                        alignment_factor = 1.1
                    elif direction_diff < -20.0:  # Strong SHORT preference (conflict)
                        alignment_factor = 0.6  # Penalize conflict
                    elif direction_diff < -10.0:  # Moderate SHORT preference (conflict)
                        alignment_factor = 0.75
                    else:  # Neutral
                        alignment_factor = 1.0
                
                elif entry_direction == "SHORT" and setup_type == "resistance_level":
                    # SHORT at resistance: good alignment if SHORT signals > LONG signals
                    direction_diff = base_short_score - base_long_score
                    if direction_diff > 20.0:  # Strong SHORT preference
                        alignment_factor = 1.2  # Boost for good alignment
                    elif direction_diff > 10.0:  # Moderate SHORT preference
                        alignment_factor = 1.1
                    elif direction_diff < -20.0:  # Strong LONG preference (conflict)
                        alignment_factor = 0.6  # Penalize conflict
                    elif direction_diff < -10.0:  # Moderate LONG preference (conflict)
                        alignment_factor = 0.75
                    else:  # Neutral
                        alignment_factor = 1.0
                else:
                    # Other setups: neutral alignment
                    alignment_factor = 1.0
            
            # Apply contextual factors to BOTH direction scores (FIXED Issue #6)
            # Problem: Old logic only applied factors to entry_direction, kept opposite as base → biased
            # Solution: Apply boost to entry_direction, apply decay to opposite direction → fair comparison
            #
            # Rationale:
            # - LONG at strong support: LONG score boosted by proximity/strength/recency
            #                          SHORT score penalized (far from resistance, conflict)
            # - SHORT at strong resistance: SHORT score boosted by proximity/strength/recency
            #                              LONG score penalized (far from support, conflict)
            
            if entry_direction == "LONG":
                # LONG at support: boost LONG, decay SHORT
                contextual_long_score = base_long_score * proximity_factor * recency_factor * strength_factor * alignment_factor
                # Apply inverse decay to SHORT (opposing direction)
                # If proximity_factor is 1.5 (boost), SHORT gets 1/1.5 = 0.67 (decay)
                inverse_proximity = 1.0 / proximity_factor if proximity_factor > 0 else 1.0
                inverse_strength = 1.0 / strength_factor if strength_factor > 0 else 1.0
                contextual_short_score = base_short_score * inverse_proximity * inverse_strength
            else:  # SHORT
                # SHORT at resistance: boost SHORT, decay LONG
                contextual_short_score = base_short_score * proximity_factor * recency_factor * strength_factor * alignment_factor
                # Apply inverse decay to LONG (opposing direction)
                inverse_proximity = 1.0 / proximity_factor if proximity_factor > 0 else 1.0
                inverse_strength = 1.0 / strength_factor if strength_factor > 0 else 1.0
                contextual_long_score = base_long_score * inverse_proximity * inverse_strength
            
            # Generate contextual reasoning
            reasoning_parts = []
            if proximity_factor < 1.0:
                reasoning_parts.append(f"proximity-adjusted (distance: {distance_atr:.1f}×ATR)")
            if strength_factor > 1.0:
                reasoning_parts.append(f"strength-boosted (level: {level_strength:.1f})")
            elif strength_factor < 1.0:
                reasoning_parts.append(f"strength-penalized (level: {level_strength:.1f})")
            if alignment_factor > 1.0:
                reasoning_parts.append("aligned")
            elif alignment_factor < 1.0:
                reasoning_parts.append("conflict-penalized")
            
            base_reasoning = base_direction_result["reasoning"]  # Required (NO FALLBACKS)
            if reasoning_parts:
                contextual_reasoning = f"{base_reasoning} [{', '.join(reasoning_parts)}]"
            else:
                contextual_reasoning = base_reasoning
            
            # Determine direction from contextual scores
            if contextual_long_score > contextual_short_score:
                direction = "LONG"
            elif contextual_short_score > contextual_long_score:
                direction = "SHORT"
            else:
                direction = entry_direction  # Use entry direction as tiebreaker
            
            return {
                "direction": direction,
                "reasoning": contextual_reasoning,
                "long_score": contextual_long_score,
                "short_score": contextual_short_score,
                "base_long_score": base_long_score,
                "base_short_score": base_short_score,
                "proximity_factor": proximity_factor,
                "strength_factor": strength_factor,
                "alignment_factor": alignment_factor
            }
            
        except Exception as e:
            logger.error(f"❌ Contextual direction scoring failed: {e}")
            return None
    
    def _get_strategy_timeframe_weights(self, strategy: str) -> Dict[str, float]:
        """
        Get strategy-specific timeframe weights
        
        Different strategies care about different timeframes:
        - Scalping: 15m (high), 1h (medium), 4h (low), 24h (none)
        - Swing Trading: 4h (high), 24h (high), 1h (medium), 15m (low)
        - Trend Following: All timeframes, but 4h/24h weighted higher
        - Range Trading: 1h (high), 4h (medium), 15m (low), 24h (low)
        - Breakout: 1h (high), 4h (high), 15m (medium), 24h (low)
        """
        timeframe_weights_map = {
            "scalping": {
                "trend_15m": 0.50,  # 50% - Most important for scalping
                "trend_1h": 0.30,   # 30% - Medium importance
                "trend_4h": 0.15,   # 15% - Low importance
                "trend_24h": 0.05   # 5% - Minimal importance
            },
            "swing_trading": {
                "trend_15m": 0.10,  # 10% - Less important
                "trend_1h": 0.25,   # 25% - Medium importance
                "trend_4h": 0.35,   # 35% - High importance
                "trend_24h": 0.30   # 30% - High importance
            },
            "trend_following": {
                "trend_15m": 0.15,  # 15% - Low importance
                "trend_1h": 0.25,   # 25% - Medium importance
                "trend_4h": 0.30,   # 30% - High importance
                "trend_24h": 0.30   # 30% - High importance
            },
            "range_trading": {
                "trend_15m": 0.20,  # 20% - Low importance (ranges are medium-term)
                "trend_1h": 0.40,   # 40% - High importance
                "trend_4h": 0.30,   # 30% - Medium importance
                "trend_24h": 0.10   # 10% - Low importance
            },
            "breakout": {
                "trend_15m": 0.25,  # 25% - Medium importance
                "trend_1h": 0.35,   # 35% - High importance
                "trend_4h": 0.30,   # 30% - High importance
                "trend_24h": 0.10   # 10% - Low importance
            },
            "low_volatility_range": {
                "trend_15m": 0.30,  # 30% - Medium importance
                "trend_1h": 0.40,   # 40% - High importance
                "trend_4h": 0.20,   # 20% - Medium importance
                "trend_24h": 0.10   # 10% - Low importance
            },
            "high_volatility": {
                "trend_15m": 0.20,  # 20% - Low importance
                "trend_1h": 0.30,   # 30% - Medium importance
                "trend_4h": 0.30,   # 30% - Medium importance
                "trend_24h": 0.20   # 20% - Medium importance
            },
            "spike_hunting": {
                "trend_15m": 0.40,  # 40% - High importance (spikes are short-term)
                "trend_1h": 0.35,   # 35% - High importance
                "trend_4h": 0.20,   # 20% - Medium importance
                "trend_24h": 0.05   # 5% - Low importance
            },
            "standard": {
                "trend_15m": 0.20,  # 20% - Balanced approach
                "trend_1h": 0.30,   # 30% - Primary timeframe
                "trend_4h": 0.30,   # 30% - Primary timeframe
                "trend_24h": 0.20   # 20% - Secondary timeframe
            }
        }
        
        return timeframe_weights_map[strategy] if strategy in timeframe_weights_map else {
            "trend_15m": 0.25,
            "trend_1h": 0.25,
            "trend_4h": 0.25,
            "trend_24h": 0.25
        }
    
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
        # Placeholder: Return fixed value until confidence calculation is implemented
        # TODO: Implement full confidence calculation using:
        #   - Entry quality: setup_data["entry_breakdown"] (power, proximity, recency)
        #   - Direction strength: setup_data["direction_breakdown"] (scores, factors, score_diff)
        #   - Setup alignment: alignment_factor from direction_breakdown
        #   - Risk/Reward: rr_ratio, stop_loss_pct, take_profit_pct
        #   - Market conditions: unified_data (volatility, trend, market_conditions, volume_category)
        #   - Strategy-specific factors: strategy config
        return 50.0
    
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
                rsi_score, reasons = self._score_entry_rsi_factor(entry_price, current_price, direction, rsi_data)
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
            
            # NOTE: 
            # - Volume: included in SR power (10% weight)
            # - Distance/proximity: scored separately in _score_entry_sr_factor based on entry offset from level
            # - Recency: handled in direction scoring, not entry scoring
            
            # Removed excessive debug logging - only log top scores
            if total_score >= 70.0:  # Only log high-scoring setups
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
    
    def _generate_all_setups(
        self,
        unified_data: Dict[str, Any],
        strategy: str,
        config: Dict[str, Any]
    ) -> list[Dict[str, Any]]:
        """
        Generate and score all potential setups (both LONG and SHORT)
        
        Hybrid approach: evaluates all entry setups for both directions,
        scores each with entry_quality + direction_support, and returns
        all valid setups sorted by total score.
        
        Returns:
            List of setup dictionaries with total_score, entry_score, direction_score, etc.
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
            filtered_levels = level_filter.filter_for_entry_setup(
                all_levels=all_levels,
                current_price=current_price,
                strategy=strategy
            )
            top_support = filtered_levels["support"]
            top_resistance = filtered_levels["resistance"]
            
            all_setups = []
            
            # Contextual direction scoring: direction scores are calculated per entry level
            # This considers entry proximity, strength, and alignment with direction signals
            # No global direction scoring - each entry gets its own contextual direction score
            
            # For each potential entry setup, evaluate for appropriate direction(s)
            # All entries must be at specific S/R levels (for limit orders)
            # IMPORTANT: Limit orders can only fill if entry_price is reachable:
            #   - LONG: entry_price must be <= current_price (buying at or below current price)
            #   - SHORT: entry_price must be >= current_price (selling at or above current price)
            # Breakout/breakdown entries don't make sense with limit orders (would require stop-limit or market orders)
            
            # 1. Support Level Entry (LONG - buying at support, limit order)
            # Entry price determined by optimizing entry scoring factors (power, proximity, recency)
            for support in top_support:
                level_price = self._require_key(support, "price_level", "setup generation")
                if level_price <= 0 or level_price >= current_price:
                    continue
                
                # Determine optimal entry price based on entry scoring factors
                # Generate candidate entry prices and select the one with best entry score
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
                
                # Evaluate as LONG setup at support level (limit order below current price = fillable)
                support_with_type = {**support, "setup_type": "support_level"}
                # Pass entry_data to preserve entry_score and breakdown
                setup_long = self._evaluate_complete_setup(
                    entry_price=entry_price,
                    setup_type="support_level",
                    direction="LONG",
                    unified_data=unified_data,
                    level_data=support_with_type,
                    strategy=strategy,
                    config=config,
                    direction_result=None,  # Will be calculated contextually inside _evaluate_complete_setup
                    entry_data=entry_data  # Pass entry data to avoid recalculation
                )
                if setup_long:
                    all_setups.append(setup_long)
            
            # 2. Resistance Level Entry (SHORT - selling at resistance, limit order)
            # Entry price determined by optimizing entry scoring factors (power, proximity, recency)
            for resistance in top_resistance:
                level_price = self._require_key(resistance, "price_level", "setup generation")
                if level_price <= 0 or level_price <= current_price:
                    continue
                
                # Determine optimal entry price based on entry scoring factors
                # Generate candidate entry prices and select the one with best entry score
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
                
                # Evaluate as SHORT setup at resistance level (limit order above current price = fillable)
                resistance_with_type = {**resistance, "setup_type": "resistance_level"}
                # Pass entry_data to preserve entry_score and breakdown
                setup_short = self._evaluate_complete_setup(
                    entry_price=entry_price,
                    setup_type="resistance_level",
                    direction="SHORT",
                    unified_data=unified_data,
                    level_data=resistance_with_type,
                    strategy=strategy,
                    config=config,
                    direction_result=None,  # Will be calculated contextually inside _evaluate_complete_setup
                    entry_data=entry_data  # Pass entry data to avoid recalculation
                )
                if setup_short:
                    all_setups.append(setup_short)
            
            # NOTE: Breakout (LONG above resistance) and Breakdown (SHORT below support) entries
            # are removed because they don't work with limit orders:
            # - Breakout LONG above resistance: If current price is below resistance, a limit order
            #   above resistance won't fill until price breaks through AND reaches that level (too late)
            # - Breakdown SHORT below support: If current price is above support, a limit order
            #   below support won't fill until price breaks down AND reaches that level (too late)
            # 
            # For breakout/breakdown strategies, we would need:
            # - Stop-limit orders (not currently implemented)
            # - Market orders (not using limit orders only)
            # - Or wait for price to be AT the level before entering (would be support/resistance level entry, not breakout)
            
            logger.debug(f"📊 Generated {len(all_setups)} potential setups for {strategy}")
            return all_setups
            
        except Exception as e:
            logger.error(f"❌ Setup generation failed: {e}")
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
        Determine optimal entry price by optimizing entry scoring factors
        
        Uses the same factors as entry scoring (power, proximity, recency) to find
        the entry price that maximizes entry score, rather than calculating independently.
        
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
            
            # FIXED Issue #5: Entry price candidates circular logic
            # Problem: Generated 4 candidates, scored by proximity to S/R, candidate AT level always won
            # Solution: Use level price directly (optimal entry point)
            # Rationale:
            #   - S/R levels are already optimal entry points (tested by market)
            #   - Proximity scoring makes "at level" the best choice anyway
            #   - Spread/slippage should be handled by order type (limit vs market), not entry offset
            
            # Use level price directly as entry (no candidate generation needed)
            entry_price = level_price
            
            # Validate entry price
            if entry_price <= 0:
                logger.warning(f"⚠️ Invalid entry price: ${entry_price:.2f}")
                return None
            if setup_type == "support_level" and entry_price >= current_price:
                logger.warning(f"⚠️ LONG entry ${entry_price:.2f} >= current ${current_price:.2f}")
                return None
            if setup_type == "resistance_level" and entry_price <= current_price:
                logger.warning(f"⚠️ SHORT entry ${entry_price:.2f} <= current ${current_price:.2f}")
                return None
            
            # Calculate entry quality factors (for reasoning)
            level_data_with_type = {**level_data, "setup_type": setup_type}
            level_power = level_data["power"]  # Required (NO FALLBACKS)
            
            # Calculate recency factor - using unified calculator
            last_touch_timestamp = level_data["last_touch_timestamp"]  # Required (NO FALLBACKS)
            from core.calculations.recency_calculator import RecencyCalculator
            recency_factor = RecencyCalculator.calculate_entry_recency_factor(
                last_touch_timestamp=last_touch_timestamp,
                strategy=strategy
            )
            
            # Calculate entry quality score (proximity to S/R level)
            sr_score, _ = self._score_entry_sr_factor(
                entry_price=entry_price,
                current_price=current_price,
                direction=direction,
                level_data=level_data_with_type,
                unified_data=unified_data,
                strategy=strategy
            )
            
            # Calculate fill probability (proximity to current price)
            from core.utils.distance_utils import calculate_distance_pct, calculate_distance_atr
            distance_to_current_pct = calculate_distance_pct(entry_price, current_price, current_price)
            distance_to_current_atr = calculate_distance_atr(distance_to_current_pct, atr_pct)
            # Convert distance to probability (closer = higher probability)
            # 0 ATR = 100%, 3 ATR = 40%, 6+ ATR = 10%
            fill_probability_score = max(10, 100 - (distance_to_current_atr / 6.0) * 90)
            
            # Calculate combined entry score
            entry_score = (level_power + sr_score + fill_probability_score) / 3.0 * recency_factor
            
            # Distance metrics for breakdown (entry is AT level)
            distance_from_level = 0.0
            distance_pct = 0.0
            
            entry_breakdown = {
                "strength_score": level_power,
                "entry_quality_score": sr_score,
                "fill_probability_score": fill_probability_score,
                "recency_factor": recency_factor,
                "distance_atr": 0.0,
                "distance_pct": distance_pct,
                "hours_since_touch": hours_since_touch,
                "setup_type": setup_type
            }
            
            return {
                "entry_price": entry_price,
                "entry_score": entry_score,
                "entry_breakdown": entry_breakdown
            }
            
        except Exception as e:
            logger.error(f"❌ Optimal entry price determination failed: {e}")
            return None
    
    def _evaluate_complete_setup(
        self,
        entry_price: float,
        setup_type: str,
        direction: str,
        unified_data: Dict[str, Any],
        level_data: Optional[Dict[str, Any]],
        strategy: str,
        config: Dict[str, Any],
        direction_result: Optional[Dict[str, Any]] = None,
        entry_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a complete setup: entry quality + contextual direction support
        
        Combines entry scoring with contextual direction scoring to get total setup score.
        Direction scoring is now contextual - considers entry proximity, strength, and alignment.
        
        Args:
            direction_result: Optional pre-calculated direction result (for backward compatibility).
                            If None, will calculate contextual direction score for this entry.
        
        Returns:
            Dict with entry_price, direction, entry_score, direction_score, total_score, etc.
        """
        try:
            # Calculate contextual direction score for this specific entry
            # This considers entry proximity, level strength, and alignment with direction signals
            if direction_result is None:
                direction_result = self._score_direction_for_entry(
                    unified_data=unified_data,
                    strategy=strategy,
                    entry_price=entry_price,
                    entry_direction=direction,
                    level_data=level_data
                )
            
            if not direction_result:
                return None
            
            # Use entry_score from entry_data if available (avoid recalculation)
            # Otherwise calculate it
            if entry_data and "entry_score" in entry_data:
                entry_score = entry_data["entry_score"]  # Required (NO FALLBACKS)
                entry_breakdown = entry_data["entry_breakdown"]  # Required (NO FALLBACKS)
                # Still need reasoning, so calculate entry_result but use cached score
                entry_result = self._score_entry_setup(
                    entry_price=entry_price,
                    setup_type=setup_type,
                    direction=direction,
                    unified_data=unified_data,
                    level_data=level_data,
                    strategy=strategy,
                    config=config
                )
                entry_reasoning = entry_result["reasoning"] if entry_result and "reasoning" in entry_result else ""  # Optional field
            else:
                # Score entry quality (fallback if entry_data not provided)
                entry_result = self._score_entry_setup(
                    entry_price=entry_price,
                    setup_type=setup_type,
                    direction=direction,
                    unified_data=unified_data,
                    level_data=level_data,
                    strategy=strategy,
                    config=config
                )
                
                if not entry_result:
                    return None
                
                entry_score = entry_result["score"]  # Required (NO FALLBACKS)
                entry_reasoning = entry_result["reasoning"]  # Required (NO FALLBACKS)
                # Create entry_breakdown from level_data if not provided
                level_power = level_data["power"] if level_data and "power" in level_data else 50.0
                entry_breakdown = {
                    "power": level_power,
                    "proximity_factor": 1.0,  # Default, would need calculation
                    "recency_factor": 1.0,   # Default, would need calculation
                    "setup_type": setup_type
                }
            
            # Get contextual direction score for this direction
            long_score = direction_result["long_score"]  # Required (NO FALLBACKS)
            short_score = direction_result["short_score"]  # Required (NO FALLBACKS)
            base_long_score = direction_result["base_long_score"] if "base_long_score" in direction_result else long_score
            base_short_score = direction_result["base_short_score"] if "base_short_score" in direction_result else short_score
            
            # Check if contextual factors were applied
            proximity_factor = direction_result["proximity_factor"] if "proximity_factor" in direction_result else 1.0
            strength_factor = direction_result["strength_factor"] if "strength_factor" in direction_result else 1.0
            alignment_factor = direction_result["alignment_factor"] if "alignment_factor" in direction_result else 1.0
            recency_factor = direction_result["recency_factor"] if "recency_factor" in direction_result else 1.0
            
            # Generate direction-specific reasoning with contextual information
            if direction == "LONG":
                direction_score = long_score
                if abs(long_score - base_long_score) > 0.1:  # Contextual factors applied
                    direction_reasoning = f"LONG signal (contextual: {long_score:.1f} vs base: {base_long_score:.1f}, SHORT: {short_score:.1f})"
                else:
                    direction_reasoning = f"LONG signal (score: {long_score:.1f} vs {short_score:.1f})"
            else:  # SHORT
                direction_score = short_score
                if abs(short_score - base_short_score) > 0.1:  # Contextual factors applied
                    direction_reasoning = f"SHORT signal (contextual: {short_score:.1f} vs base: {base_short_score:.1f}, LONG: {long_score:.1f})"
                else:
                    direction_reasoning = f"SHORT signal (score: {short_score:.1f} vs {long_score:.1f})"
            
            # Log contextual factors if they significantly affected the score
            if proximity_factor != 1.0 or strength_factor != 1.0 or alignment_factor != 1.0:
                logger.debug(f"📊 Contextual direction factors for {direction} @ ${entry_price:.2f}: "
                           f"proximity={proximity_factor:.2f}, strength={strength_factor:.2f}, alignment={alignment_factor:.2f}")
            
            # Normalize scores (both are on similar scales, but we can weight them)
            # Entry quality: 50% weight, Direction support: 50% weight
            # Entry score already includes SR score (50% weight) which considers all SR factors
            # So the SR system's ranking is naturally respected through entry_score
            entry_weight = 0.5
            direction_weight = 0.5
            
            # Calculate total score (weighted combination)
            # No artificial bonuses - SR score is already the primary factor in entry_score
            total_score = (entry_score * entry_weight) + (direction_score * direction_weight)
            
            # Calculate score difference for confidence
            score_diff = abs(long_score - short_score)
            
            # Build direction breakdown
            direction_breakdown = {
                "base_long_score": base_long_score,
                "base_short_score": base_short_score,
                "proximity_factor": proximity_factor,
                "strength_factor": strength_factor,
                "alignment_factor": alignment_factor,
                "recency_factor": recency_factor,
                "score_diff": score_diff,
                "final_long_score": long_score,
                "final_short_score": short_score
            }
            
            return {
                "entry_price": entry_price,
                "direction": direction,
                "setup_type": setup_type,
                "entry_score": entry_score,
                "direction_score": direction_score,
                "total_score": total_score,
                "entry_reasoning": entry_reasoning,
                "direction_reasoning": direction_reasoning,
                "long_score": long_score,
                "short_score": short_score,
                "score_diff": score_diff,
                "entry_breakdown": entry_breakdown,
                "direction_breakdown": direction_breakdown,
                "level_data": level_data  # Include level_data for stop loss calculation
            }
            
        except Exception as e:
            logger.error(f"❌ Complete setup evaluation failed: {e}")
            return None
    
    def _determine_entry_price(
        self, 
        unified_data: Dict[str, Any], 
        direction: str,
        strategy: str,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        DEPRECATED: This method is kept for backward compatibility but is not used.
        
        New approach: Use _generate_all_setups() which evaluates all setups (both LONG and SHORT)
        and selects the best overall combination (hybrid approach).
        
        Entry setups analyzed (all for limit orders at S/R levels):
        1. S/R Level Entry: Enter at support (LONG) or resistance (SHORT)
        2. Breakout Entry: Enter above resistance (LONG)
        3. Breakdown Entry: Enter below support (SHORT)
        
        Args:
            unified_data: Complete market analysis data
            direction: "LONG" or "SHORT"
            strategy: Current trading strategy
            config: Strategy configuration
            
        Returns:
            Dict with "entry_price" and "reasoning", or None if no valid setup
        """
        try:
            current_price = self._require_key(unified_data, "current_price", "entry determination")
            if current_price <= 0:
                logger.warning("⚠️ Invalid current price for entry determination")
                return None
            
            # Extract market data
            sr_data = unified_data["support_resistance"]  # Required (NO FALLBACKS)
            
            # Get all levels and filter for entry setup
            all_levels = self._require_key(sr_data, "levels", "setup generation")
            from core.calculations.sr_level_filter import SRLevelFilter
            level_filter = SRLevelFilter()
            filtered_levels = level_filter.filter_for_entry_setup(
                all_levels=all_levels,
                current_price=current_price,
                strategy=strategy,
                direction=direction
            )
            top_support = filtered_levels["support"]
            top_resistance = filtered_levels["resistance"]
            
            # Generate and score potential entry setups
            scored_setups = []
            
            # All entries must be at specific S/R levels (for limit orders only, no current_price entries)
            if direction == "LONG":
                # 1. Support Level Entry (limit order at support)
                for support in top_support:
                    level_price = self._require_key(support, "price_level", "setup generation")
                    if level_price <= 0 or level_price >= current_price:
                        continue
                    
                    support_with_type = {**support, "setup_type": "support_level"}
                    setup_result = self._score_entry_setup(
                        entry_price=level_price,
                        setup_type="support_level",
                        direction=direction,
                        unified_data=unified_data,
                        level_data=support_with_type,
                        strategy=strategy,
                        config=config
                    )
                    if setup_result:
                        scored_setups.append(setup_result)
                
                # NOTE: Breakout entries removed - limit orders can't fill above resistance
                # when current price is below resistance (would require stop-limit or market orders)
            
            else:  # SHORT
                # 1. Resistance Level Entry (limit order at resistance)
                for resistance in top_resistance:
                    level_price = self._require_key(resistance, "price_level", "setup generation")
                    if level_price <= 0 or level_price <= current_price:
                        continue
                    
                    resistance_with_type = {**resistance, "setup_type": "resistance_level"}
                    setup_result = self._score_entry_setup(
                        entry_price=level_price,
                        setup_type="resistance_level",
                        direction=direction,
                        unified_data=unified_data,
                        level_data=resistance_with_type,
                        strategy=strategy,
                        config=config
                    )
                    if setup_result:
                        scored_setups.append(setup_result)
                
                # NOTE: Breakdown entries removed - limit orders can't fill below support
                # when current price is above support (would require stop-limit or market orders)
            
            if not scored_setups:
                logger.debug(f"⏸️ No valid entry setups found for {direction}")
                return None
            
            # Sort by score (highest first) and select best setup
            scored_setups.sort(key=lambda x: x["score"] if "score" in x else 0.0, reverse=True)
            best_setup = scored_setups[0]
            
            logger.debug(f"📊 Entry determined: ${best_setup['entry_price']:.2f} (type: {best_setup['setup_type']}, score: {best_setup['score']:.1f})")  # Required (NO FALLBACKS)
            
            return {
                "entry_price": best_setup["entry_price"],
                "reasoning": best_setup["reasoning"]
            }
            
        except Exception as e:
            logger.error(f"❌ Entry price determination failed: {e}")
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
                            # Place stop with noise buffer (0.25×ATR) to avoid false breaks
                            noise_buffer = atr_5m * 0.25
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
            
            # 3. Calculate adaptive take profit at next S/R level (delegated to RiskManager)
            take_profit = RiskManager.calculate_take_profit(
                entry_price=entry_price,
                stop_loss=stop_loss,
                direction=direction,
                atr_5m=atr_5m,
                config=config,
                sr_levels=all_levels,  # Pass all levels for adaptive TP selection
                strategy=strategy
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