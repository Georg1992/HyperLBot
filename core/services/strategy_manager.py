#!/usr/bin/env python3
"""
Strategy Manager
Centralized strategy detection, selection, and management
Single Responsibility: Strategy decision making and configuration
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from config.config import TradingConfig
# CRITICAL: time module removed - all timestamps must come from market_data for determinism


class SimpleRecommendation:
    """Recommendation data structure for strategy selection"""
    def __init__(self, strategy: str, reasoning: str, confidence: float):
        self.strategy = strategy
        self.reasoning = reasoning
        self.confidence = confidence


class StrategyManager:
    """
    Centralized strategy management component
    
    RESPONSIBILITIES:
    1. Detect optimal strategy based on market conditions
    2. Manage strategy switching during session
    3. Provide strategy-specific configurations to engines
    4. Validate strategy appropriateness for current conditions
    """
    
    # Float precision epsilon for score comparisons (prevents non-determinism in tie-breaking)
    SCORE_EPSILON = 0.01  # For score comparisons (scores are typically 0-100 range)
    
    def __init__(self, config: TradingConfig = None):
        # TradingConfig is a class with static attributes, not an instance
        # If config is provided, use it; otherwise use TradingConfig class directly
        if config is None:
            self.config = TradingConfig
        else:
            self.config = config
        self.strategy_configs = self.config.STRATEGY_CONFIGS
        
        # Current strategy state
        self.current_strategy = "standard"
        self.current_strategy_config = self.strategy_configs["standard"]
        self.last_strategy_switch = 0.0  # Initialize to 0.0 (will be set on first switch with data timestamp)
        self.strategy_switch_cooldown = TradingConfig.STRATEGY_SWITCH_COOLDOWN_DEFAULT
        
        # Track optimal strategy for logging/UI (separate from current_strategy state)
        self.last_optimal_strategy = "standard"
        self.last_selection_reason = ""  # Reason for strategy selection (tie-break/cooldown)
        
        # Strategy performance tracking
        self.strategy_performance = {}
        self._last_market_data = None
        self.pending_strategy_outcomes = []
        
        # Analysis-only strategies (not tradeable)
        self._analysis_only_strategies = {"comprehensive_analysis"}
        
        # Initialize performance tracking
        for strategy_name in self.strategy_configs.keys():
            self.strategy_performance[strategy_name] = {
                "total_trades": 0,
                "successful_trades": 0,
                "total_profit": 0.0,
                "last_used": 0.0  # Changed to 0.0 for consistency with timestamp type
            }
        
        logger.info("🎯 Strategy Manager initialized - Centralized strategy management")
        logger.info(f"   🎯 Current strategy: {self.current_strategy}")
    
    
    def detect_optimal_strategy(self, market_data: Dict[str, Any]) -> str:
        """
        Detect the optimal strategy using ML-powered analysis (SINGLE SOURCE OF TRUTH)
        
        CRITICAL: This method is replay-deterministic. All time-based operations use
        market_data["timestamp"] instead of time.time() to ensure identical inputs
        produce identical outputs for ML training.
        
        Args:
            market_data: Current market data (price, volatility, trend, volume, etc.)
                MUST contain "timestamp" key for deterministic cooldown (NO FALLBACKS)
            
        Returns:
            str: Current active strategy name (self.current_strategy)
                Note: Use self.last_optimal_strategy to access the optimal recommendation
                if it differs from current_strategy (e.g., due to cooldown)
        
        Raises:
            ValueError: If market_data["timestamp"] is missing (NO FALLBACKS)
        """
        try:
            # CRITICAL FIX: Extract and validate timestamp for deterministic cooldown
            data_timestamp = self._get_data_timestamp(market_data)
            
            # Pure business logic strategy selection (no ML for now)
            recommendation = self._select_strategy_business_logic(market_data)
            
            # If recommendation is None, data isn't ready yet - keep current strategy
            if recommendation is None:
                logger.debug("⏳ Funding data not ready yet - keeping current strategy")
                return self.current_strategy
            
            optimal_strategy = recommendation.strategy
            reasoning = recommendation.reasoning
            
            # Store optimal strategy for logging/UI (separate from current_strategy state)
            self.last_optimal_strategy = optimal_strategy
            
            # Store market data for dynamic cooldown calculation
            self._last_market_data = market_data.copy()
            
            # Log business logic strategy selection
            logger.info(f"📊 Business Logic Strategy Decision: {optimal_strategy}")
            logger.info(f"   📊 Reasoning: {reasoning}")
            
            # Validate strategy compatibility (redundant check removed - scoring handles this)
            # Only check if confidence is too low (<0.3) - might indicate data issues
            # Use confidence threshold from config (configurable for optimization)
            if recommendation.confidence < TradingConfig.CONFIDENCE_THRESHOLDS["low"]:
                logger.warning(f"⚠️ Low confidence ({recommendation.confidence:.2f}) for {optimal_strategy}, checking alternatives")
                # Find next best strategy
                optimal_strategy = self._find_next_best_strategy_by_score(market_data, optimal_strategy)
                self.last_optimal_strategy = optimal_strategy
                logger.info(f"🔄 Selected alternative strategy: {optimal_strategy}")
            
            # Check if strategy switch is needed and allowed
            cooldown_blocked = False
            if optimal_strategy != self.current_strategy:
                if self._can_switch_strategy(data_timestamp):
                    logger.info(f"🔄 Strategy switch: {self.current_strategy} → {optimal_strategy}")
                    self._switch_strategy(optimal_strategy, data_timestamp)
                    self.last_selection_reason = f"Strategy switch: {self.current_strategy} → {optimal_strategy}"
                    
                    # Record strategy selection for learning
                    self._record_strategy_selection(optimal_strategy, market_data, recommendation, data_timestamp)
                else:
                    cooldown_blocked = True
                    logger.warning(
                        f"⏳ Strategy switch blocked (cooldown): {self.current_strategy} → {optimal_strategy}. "
                        f"Optimal strategy '{optimal_strategy}' available for predictions but state unchanged."
                    )
                    self.last_selection_reason = f"Cooldown blocked switch: {self.current_strategy} → {optimal_strategy} (optimal available for predictions)"
                    # Record strategy selection even if switch blocked
                    self._record_strategy_selection(optimal_strategy, market_data, recommendation, data_timestamp)
            else:
                # Still record for learning even if no switch
                self.last_selection_reason = f"Optimal strategy unchanged: {optimal_strategy}"
                self._record_strategy_selection(optimal_strategy, market_data, recommendation, data_timestamp)
            
            # CRITICAL FIX: Always return self.current_strategy (source of truth)
            # Use self.last_optimal_strategy if you need the optimal recommendation
            return self.current_strategy
            
        except Exception as e:
            logger.error(f"❌ Strategy detection failed: {e}")
            raise  # NO FALLBACKS - detection failure must raise
    
    def _get_data_timestamp(self, market_data: Dict[str, Any]) -> float:
        """
        Extract and validate timestamp from market_data for deterministic operations
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            float: Timestamp value
            
        Raises:
            ValueError: If timestamp is missing or invalid (NO FALLBACKS)
        """
        if "timestamp" not in market_data:
            raise ValueError(
                "market_data must contain 'timestamp' for deterministic strategy selection (NO FALLBACKS). "
                "This ensures replay determinism for ML training."
            )
        
        timestamp = market_data["timestamp"]
        try:
            timestamp_float = float(timestamp)
            if timestamp_float <= 0:
                raise ValueError(f"Invalid timestamp: {timestamp_float} (must be positive, NO FALLBACKS)")
            return timestamp_float
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid timestamp type in market_data: {type(timestamp)} - must be numeric (NO FALLBACKS)") from e
    
    def _select_strategy_business_logic(self, market_data: Dict[str, Any]) -> Optional['SimpleRecommendation']:
        """
        Sophisticated strategy selection using multi-factor scoring with dynamic confidence
        
        Returns:
            StrategyRecommendation or None if data isn't ready yet
        """
        try:
            # Extract all available market data
            # Returns None if funding data isn't ready yet
            data = self._extract_market_data(market_data)
            if data is None:
                return None  # Data not ready - skip strategy selection for this iteration
            
            # Score all tradeable strategies (exclude analysis-only strategies)
            strategy_scores = {}
            tradeable_strategies = [s for s in self.strategy_configs.keys() if s not in self._analysis_only_strategies]
            for strategy_name in tradeable_strategies:
                # Validate strategy config has required keys (NO FALLBACKS)
                if strategy_name not in self.strategy_configs:
                    logger.error(f"❌ Strategy '{strategy_name}' missing from config - skipping (NO FALLBACKS)")
                    continue
                config = self.strategy_configs[strategy_name]
                required_keys = ["direction_weights", "entry_proximity_config"]
                missing_keys = [k for k in required_keys if k not in config]
                if missing_keys:
                    logger.error(f"❌ Strategy '{strategy_name}' missing config keys: {missing_keys} - skipping (NO FALLBACKS)")
                    continue
                
                # _score_strategy() guarantees (float, list) tuple - trust API contract
                score, factors = self._score_strategy(strategy_name, data)
                strategy_scores[strategy_name] = {
                    "score": score,
                    "factors": factors
                }
            
            # Select best strategy with explicit tie-breaking
            # CRITICAL FIX: Use explicit tie-breaking instead of relying on max() insertion order
            # This ensures deterministic, semantically meaningful selection when scores are equal
            def safe_get_score(item):
                # item is (strategy_name, score_dict) tuple from sorted()
                score_data = item[1]
                return float(score_data["score"])  # score_dict always has "score" key (guaranteed by _score_strategy)
            
            # Find maximum score
            max_score = max(safe_get_score(item) for item in strategy_scores.items())
            
            # Find all strategies with maximum score (potential ties)
            tied_strategies = [
                (name, score_data) for name, score_data in strategy_scores.items()
                if abs(float(score_data["score"]) - max_score) < self.SCORE_EPSILON
            ]
            
            # If only one strategy has max score, use it
            if len(tied_strategies) == 1:
                best_strategy = tied_strategies[0]
            else:
                # Multiple strategies tied - use explicit tie-breaking
                logger.debug(f"📊 {len(tied_strategies)} strategies tied at score {max_score:.2f}, using tie-breaking")
                best_strategy = self._break_strategy_tie(tied_strategies, data)
            
            strategy_name = best_strategy[0]
            score_data = best_strategy[1]
            
            # Calculate dynamic confidence based on:
            # 1. Score magnitude (higher = more confident)
            # 2. Data quality (missing data = lower confidence)
            # 3. Score gap (bigger gap from 2nd place = more confident)
            confidence = self._calculate_confidence(strategy_scores, strategy_name, data)
            
            # Build reasoning from factors
            reasoning = self._build_reasoning(strategy_name, score_data["factors"], confidence)
            
            logger.info(f"📊 Selected: {strategy_name} (score: {score_data['score']:.2f}, confidence: {confidence:.2f})")
            
            return SimpleRecommendation(strategy_name, reasoning, confidence)
                
        except Exception as e:
            logger.error(f"❌ Strategy selection failed: {e}")
            raise
    
    def _extract_market_data(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract and normalize all available market data (NO FALLBACKS)
        
        Returns:
            Dict with extracted market data, or None if funding data isn't ready yet
        """
        # Basic data (flattened) - ensure numeric types are floats
        volatility_category = market_data["volatility_category"]  # Required (NO FALLBACKS)
        trend_direction = market_data["trend_direction"]  # Required (NO FALLBACKS)
        volume_category = market_data["volume_category"]  # Required (NO FALLBACKS)
        
        # Required fields - will raise if missing or invalid (NO FALLBACKS)
        volatility_5m = float(market_data["volatility_5m"])
        rsi_value = float(market_data["rsi_value"])
        
        # Extended data (nested) - Required (NO FALLBACKS)
        # Validate at service boundary (market_data comes from MarketDataService)
        trend_data = market_data["trend"]  # Required (NO FALLBACKS) - will raise KeyError if missing
        trend_detailed = trend_data["detailed_timeframes"]  # Required (NO FALLBACKS) - will raise KeyError if missing
        trend_15m = trend_detailed["trend_15m"]
        trend_1h = trend_detailed["trend_1h"]
        rsi_data = market_data["rsi"]
        volatility_data = market_data["volatility"]  # Get full volatility data for spike_intensity
        volume_data = market_data["volume"]  # Get full volume data for volume_trend_strength and volume_anomaly
        sr_data = market_data["support_resistance"]
        orderbook_data = market_data["orderbook_analysis"]
        pressure_data = market_data["pressure"]
        funding_data = market_data["funding_analysis"]
        market_conditions = market_data["market_conditions"]
        
        # Extract detailed values - NO FALLBACKS
        trend_strength_raw = trend_data["strength"]
        trend_strength = float(trend_strength_raw)
        
        rsi_trend = rsi_data["rsi_trend"]
        rsi_signal = rsi_data["rsi_signal"]
        
        rsi_momentum_raw = rsi_data["rsi_momentum"]
        rsi_momentum = float(rsi_momentum_raw)
        
        # STRATEGY INDEPENDENCE: S/R levels NOT used for strategy selection
        # Strategy selection is based purely on market conditions (volatility, trend, volume, RSI, pressure)
        # S/R level filtering happens AFTER strategy is selected in PredictionEngine
        current_price = float(market_data["current_price"])  # Required (NO FALLBACKS) - will raise if invalid
        
        # Orderbook data - NO FALLBACKS
        # Orderbook analyzer returns nested structure: bid_ask_spread.percentage, liquidity_depth.depth_score
        bid_ask_spread = orderbook_data["bid_ask_spread"]
        spread_pct_raw = bid_ask_spread["percentage"]
        spread_pct = float(spread_pct_raw)
        
        liquidity_depth = orderbook_data["liquidity_depth"]
        liquidity_score_raw = liquidity_depth["depth_score"]
        liquidity_score = float(liquidity_score_raw)
        
        # Pressure data - NO FALLBACKS
        net_pressure_raw = pressure_data["net_pressure"]
        net_pressure = float(net_pressure_raw)
        
        pressure_ratio_raw = pressure_data["pressure_ratio"]
        pressure_ratio = float(pressure_ratio_raw)
        
        # Funding data - Required for strategy selection (NO FALLBACKS)
        # Funding analyzer only includes trend/volatility when history is sufficient (5+ data points)
        # Strategy selection requires all data to be ready - wait until funding history is sufficient
        funding_trend = funding_data.get("funding_trend")  # May not be present if insufficient history
        funding_volatility_data = funding_data.get("funding_volatility")  # May not be present if insufficient history
        
        # CRITICAL: All funding data must be available before strategy selection
        # If trend/volatility not available, return None to signal we need to wait
        # This ensures strategy selection only happens when all required data is ready
        if not funding_trend or not funding_volatility_data:
            return None  # Signal to caller that data isn't ready yet - wait for more funding history
        
        funding_direction = funding_trend["direction"]  # Required (NO FALLBACKS)
        
        funding_strength_raw = funding_trend["strength"]
        try:
            funding_strength = float(funding_strength_raw)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid funding_strength value: {funding_strength_raw} - NO FALLBACKS")
        
        # Funding volatility for risk management - NO FALLBACKS
        funding_volatility_category = funding_volatility_data["category"]
        
        # Market conditions - NO FALLBACKS
        market_condition = market_conditions["condition"]
        risk_level = market_conditions["risk_level"]
        
        # Volatility spike intensity (for spike_hunting strategy) - NO FALLBACKS
        spike_intensity = volatility_data["spike_intensity"]
        
        # Volume data - NO FALLBACKS
        volume_trend_strength_raw = volume_data["volume_trend_strength"]
        volume_trend_strength = float(volume_trend_strength_raw)
        
        volume_anomaly = volume_data["volume_anomaly"]
        
        # Pattern data - NO FALLBACKS
        patterns_data = market_data["patterns"]
        patterns_nested = patterns_data["patterns_nested"]
        patterns_flat = patterns_data["patterns"]
        
        # Use overall_quality (pattern quality), NOT prediction confidence - NO FALLBACKS
        pattern_quality_raw = patterns_data["overall_quality"]
        pattern_quality = float(pattern_quality_raw)
        
        # Extract pattern categories for strategy selection - NO FALLBACKS
        reversal_patterns = patterns_nested["reversal_patterns"]
        continuation_patterns = patterns_nested["continuation_patterns"]
        triangle_patterns = patterns_nested["triangle_patterns"]
        channel_patterns = patterns_nested["channel_patterns"]
        wedge_patterns = patterns_nested["wedge_patterns"]
        trend_patterns = patterns_nested["trend_patterns"]
        
        return {
            "volatility_category": volatility_category,
            "volatility_5m": volatility_5m,
            "trend_direction": trend_direction,
            "trend_strength": trend_strength,
            "volume_category": volume_category,
            "rsi_value": rsi_value,
            "rsi_trend": rsi_trend,
            "rsi_signal": rsi_signal,
            "rsi_momentum": rsi_momentum,
            "current_price": current_price,
            "spread_pct": spread_pct,
            "liquidity_score": liquidity_score,
            "net_pressure": net_pressure,
            "pressure_ratio": pressure_ratio,
            "funding_direction": funding_direction,
            "funding_strength": funding_strength,
            "funding_trend": funding_trend,  # Full trend data including rate_change
            "funding_volatility_category": funding_volatility_category,  # For risk management
            "volume_trend_strength": volume_trend_strength,  # For strategy selection
            "volume_anomaly": volume_anomaly,  # For risk management
            "market_condition": market_condition,
            "risk_level": risk_level,
            "spike_intensity": spike_intensity,  # Used by spike_hunting strategy
            # Pattern data for strategy selection
            "pattern_quality": pattern_quality,  # Pattern detection quality, NOT prediction confidence
            "reversal_patterns": reversal_patterns,
            "continuation_patterns": continuation_patterns,
            "triangle_patterns": triangle_patterns,
            "channel_patterns": channel_patterns,
            "wedge_patterns": wedge_patterns,
            "trend_patterns": trend_patterns,
            "trend_15m": trend_15m,
            "trend_1h": trend_1h
        }
    
    def _has_pattern_in_list(self, pattern_list: List[Dict[str, Any]], pattern_names: List[str]) -> bool:
        """Helper method to check if any pattern in list matches pattern_names"""
        if not pattern_list or not isinstance(pattern_list, list):
            return False
        for pattern in pattern_list:
            if not isinstance(pattern, dict):
                continue
            pattern_name = pattern["pattern"].upper()  # Required (NO FALLBACKS)
            if any(name.upper() in pattern_name for name in pattern_names):
                return True
        return False
    
    def _score_strategy(self, strategy_name: str, data: Dict[str, Any]) -> tuple:
        """Score a strategy based on all available market data"""
        strategy_scorers = {
            "scalping": self._score_scalping,
            "spike_hunting": self._score_spike_hunting,
            "trend_following": self._score_trend_following,
            "breakout": self._score_breakout,
            "range_trading": self._score_range_trading,
            "low_volatility_range": self._score_low_volatility_range,
            "high_volatility": self._score_high_volatility,
            "standard": self._score_standard
        }
        
        if strategy_name not in strategy_scorers:
            raise ValueError(f"Unknown strategy: {strategy_name} - must be one of {list(strategy_scorers.keys())} (NO FALLBACKS)")
        scorer = strategy_scorers[strategy_name]
        return scorer(data)
    
    def _score_scalping(self, data: Dict[str, Any]) -> tuple:
        """Score scalping strategy - requires tight spreads, HIGH liquidity, MODERATE volatility, neutral RSI"""
        score = 0.0
        factors = []
        
        # Volatility: MODERATE is REQUIRED (40 points) - scalping needs predictable moves
        if data["volatility_category"] == "MODERATE":
            score += 40.0
            factors.append("Moderate volatility (ideal)")
        elif data["volatility_category"] == "LOW":
            score += 10.0
            factors.append("Low volatility (marginal)")
        else:
            score -= 30.0
            factors.append(f"{data['volatility_category']} volatility (unsuitable for scalping)")
        
        # RSI: 40-60 is ideal (MUCH STRICTER - neutral zone only) (25 points) - NO FALLBACKS
        rsi = float(data["rsi_value"])
        if 40 <= rsi <= 60:
            score += 25.0
            factors.append(f"RSI {rsi:.1f} (neutral - ideal)")
        elif 35 <= rsi < 40 or 60 < rsi <= 65:
            score += 10.0
            factors.append(f"RSI {rsi:.1f} (acceptable)")
        else:
            score -= 15.0
            factors.append(f"RSI {rsi:.1f} (directional - use trend/breakout)")
        
        # Spread: Tight spread is CRITICAL (35 points) - scalping lives on tight spreads
        spread = float(data["spread_pct"])  # Required (NO FALLBACKS) - will raise if invalid
        # Use spread thresholds from config (configurable for optimization)
        if spread < TradingConfig.SPREAD_THRESHOLDS["excellent"]:
            score += 35.0
            factors.append(f"Excellent spread ({spread*100:.3f}%)")
        elif spread < TradingConfig.SPREAD_THRESHOLDS["good"]:
            score += 10.0
            factors.append(f"Moderate spread ({spread*100:.3f}%) - marginal")
        else:
            score -= 30.0
            factors.append(f"Wide spread ({spread*100:.3f}%) - SCALPING IMPOSSIBLE")
        
        # Liquidity: HIGH liquidity REQUIRED (20 points) - scalping needs immediate fills
        liquidity_score = float(data["liquidity_score"])  # Required (NO FALLBACKS)
        if liquidity_score >= 0.7:
            score += 20.0
            factors.append(f"High liquidity (score: {liquidity_score:.2f})")
        elif liquidity_score >= 0.5:
            score += 5.0
            factors.append(f"Moderate liquidity (score: {liquidity_score:.2f}) - marginal")
        else:
            score -= 20.0
            factors.append(f"Low liquidity (score: {liquidity_score:.2f}) - RISKY")
        
        # Volume: HIGH volume REQUIRED (15 points)
        vol_cat = data["volume_category"]
        if vol_cat in ["HIGH", "VERY_HIGH"]:
            score += 15.0
            factors.append(f"{vol_cat} volume (ideal)")
        elif vol_cat == "NORMAL":
            score += 5.0
            factors.append("Normal volume (marginal)")
        else:
            score -= 15.0
            factors.append(f"{vol_cat} volume (insufficient)")
        
        # Trend: Weak/sideways preferred (15 points) - scalping needs range-bound conditions
        if data["trend_direction"] == "SIDEWAYS":
            score += 15.0
            factors.append("Sideways trend (ideal for scalping)")
        else:
            trend_strength = float(data["trend_strength"])  # Required (NO FALLBACKS)
            if trend_strength < 0.5:
                score += 5.0
                factors.append(f"Weak {data['trend_direction']} trend (acceptable)")
            else:
                score -= 15.0
                factors.append(f"Strong {data['trend_direction']} trend (use trend_following)")
        
        return max(0.0, score), factors
    
    def _score_spike_hunting(self, data: Dict[str, Any]) -> tuple:
        """Score spike hunting - requires extreme volatility + high volume"""
        score = 0.0
        factors = []
        
        # Volatility spike intensity check (uses config min_spike_severity: "HIGH")
        spike_intensity = data["spike_intensity"]
        spike_config = self.strategy_configs["spike_hunting"]
        min_severity = spike_config["min_spike_severity"]
        
        # Severity hierarchy: NONE < MODERATE < HIGH < EXTREME
        severity_levels = {"NONE": 0, "MODERATE": 1, "HIGH": 2, "EXTREME": 3}
        spike_level = severity_levels[spike_intensity]
        min_level = severity_levels[min_severity]
        
        vol_5m = float(data["volatility_5m"])  # Required (NO FALLBACKS) - will raise if invalid
        
        # Volatility: Check spike intensity first, then fallback to category/value
        if spike_level >= min_level:
            if spike_intensity == "EXTREME":
                score += 40.0
                factors.append(f"Extreme volatility spike ({vol_5m*100:.2f}%)")
            elif spike_intensity == "HIGH":
                score += 35.0
                factors.append(f"High volatility spike ({vol_5m*100:.2f}%)")
            else:  # MODERATE
                score += 25.0
                factors.append(f"Moderate volatility spike ({vol_5m*100:.2f}%)")
        elif vol_5m > 0.05 or data["volatility_category"] == "EXTREME":
            # Fallback: high value or EXTREME category even without spike detection
            score += 30.0
            factors.append(f"Extreme volatility ({vol_5m*100:.2f}%) - no spike detected")
        elif data["volatility_category"] in ["HIGH", "VERY_HIGH"]:
            score += 15.0
            factors.append(f"High volatility ({vol_5m*100:.2f}%) - insufficient spike")
        else:
            score -= 30.0
            factors.append(f"{data['volatility_category']} volatility (insufficient for spike hunting)")
        
        # Volume: HIGH/VERY_HIGH required (30 points)
        vol_cat = data["volume_category"]
        if vol_cat in ["HIGH", "VERY_HIGH", "EXTREME"]:
            score += 30.0
            factors.append(f"{vol_cat} volume")
        elif vol_cat == "NORMAL":
            score += 10.0
            factors.append("Normal volume (suboptimal)")
        else:
            score -= 20.0
            factors.append(f"{vol_cat} volume (insufficient)")
        
        # Market condition: Acceptable risk (10 points)
        if data["risk_level"] in ["LOW", "MEDIUM"]:
            score += 10.0
            factors.append(f"{data['risk_level']} risk")
        else:
            score -= 5.0
            factors.append(f"{data['risk_level']} risk")
        
        # Funding volatility risk check: High funding volatility indicates market instability
        funding_volatility_cat = data["funding_volatility_category"]
        if funding_volatility_cat == "UNKNOWN":
            factors.append("Funding volatility data insufficient (neutral)")
        elif funding_volatility_cat == "HIGH":
            score -= 15.0
            factors.append("High funding volatility (market instability - avoid spike hunting)")
        elif funding_volatility_cat == "MEDIUM":
            score -= 5.0
            factors.append("Moderate funding volatility (increased risk)")
        
        return max(0.0, score), factors
    
    def _score_trend_following(self, data: Dict[str, Any]) -> tuple:
        """Score trend following - requires strong trend + funding alignment + volume + continuation patterns"""
        score = 0.0
        factors = []
        
        # Trend: Strong trend required (30 points)
        if data["trend_direction"] in ["BULLISH", "BEARISH"]:
            score += 20.0
            factors.append(f"{data['trend_direction']} trend")
            # Trend strength bonus - ensure float conversion
            trend_strength = float(data["trend_strength"])  # Required (NO FALLBACKS) - will raise if invalid
            if trend_strength > 0.7:
                score += 10.0
                factors.append(f"Strong trend (strength: {trend_strength:.2f})")
            elif trend_strength > 0.5:
                score += 5.0
                factors.append(f"Moderate trend (strength: {trend_strength:.2f})")
            else:
                score -= 5.0
                factors.append(f"Weak trend (strength: {trend_strength:.2f})")
        else:
            score -= 25.0
            factors.append(f"{data['trend_direction']} trend (no trend)")
        
        # Patterns: Continuation patterns confirm trend (25 points)
        if self._has_pattern_in_list(data["continuation_patterns"], ["BULLISH_CONTINUATION", "BEARISH_CONTINUATION"]):
            score += 25.0
            factors.append("Continuation pattern (trend confirmation)")
        elif self._has_pattern_in_list(data["trend_patterns"], ["TREND"]):
            score += 15.0
            factors.append("Trend pattern detected")
        elif self._has_pattern_in_list(data["triangle_patterns"], ["ASCENDING_TRIANGLE", "DESCENDING_TRIANGLE"]):
            score += 10.0
            factors.append("Trending triangle pattern")
        else:
            score += 5.0
            factors.append("No continuation patterns")
        
        # Funding: Alignment with trend (20 points) + Rate change momentum (up to 5 points)
        funding_dir = data["funding_direction"]
        funding_trend = data["funding_trend"]
        funding_rate_change_raw = funding_trend["rate_change"]
        # Ensure funding_rate_change is always a float (NO FALLBACKS)
        try:
            funding_rate_change = float(funding_rate_change_raw)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid funding_rate_change value: {funding_rate_change_raw} (expected float, got {type(funding_rate_change_raw).__name__}) - NO FALLBACKS")
        
        funding_score = 0.0
        # Handle UNKNOWN funding direction (insufficient history) - neutral scoring
        if funding_dir == "UNKNOWN":
            factors.append("Funding data insufficient (neutral)")
        # Funding data is available - score normally
        elif data["trend_direction"] == "BULLISH" and funding_dir == "INCREASING":
            funding_score = 20.0
            factors.append("Funding aligns with bullish trend")
        elif data["trend_direction"] == "BEARISH" and funding_dir == "DECREASING":
            funding_score = 20.0
            factors.append("Funding aligns with bearish trend")
        elif funding_dir == "STABLE":
            funding_score = 10.0
            factors.append("Stable funding")
        else:
            funding_score = -15.0
            factors.append(f"Funding misaligned ({funding_dir})")
            
        # Funding rate change momentum: Strong rate change confirms trend
        # Skip if funding direction is UNKNOWN (insufficient history)
        if funding_dir != "UNKNOWN":
            funding_thresholds = TradingConfig.FUNDING_RATE_CHANGE_THRESHOLDS
            
            if data["trend_direction"] == "BULLISH" and funding_rate_change > funding_thresholds["significant_increase"]:
                funding_score += 5.0
                factors.append(f"Funding rate increasing ({funding_rate_change*10000:.2f} bps)")
            elif data["trend_direction"] == "BEARISH" and funding_rate_change < funding_thresholds["significant_decrease"]:
                funding_score += 5.0
                factors.append(f"Funding rate decreasing ({funding_rate_change*10000:.2f} bps)")
            elif abs(funding_rate_change) < funding_thresholds["very_stable"]:
                funding_score += 2.0
                factors.append("Funding rate stable")
        
        score += funding_score
        
        # Volume: High volume confirms trend (15 points) + Volume trend strength bonus (up to 10 points)
        vol_cat = data["volume_category"]
        volume_trend_strength = data["volume_trend_strength"]  # Strength of volume trend (0.0-1.0)
        
        volume_score = 0.0
        if vol_cat in ["HIGH", "VERY_HIGH", "EXTREME"]:
            volume_score = 15.0
            factors.append(f"{vol_cat} volume confirms trend")
        elif vol_cat == "NORMAL":
            volume_score = 10.0
            factors.append("Normal volume")
        else:
            volume_score = -10.0
            factors.append(f"{vol_cat} volume (weak)")
        
        # Volume trend strength bonus: Strong volume trend increases confidence
        volume_thresholds = TradingConfig.VOLUME_TREND_STRENGTH_THRESHOLDS
        
        if volume_trend_strength > volume_thresholds["very_strong"]:
            volume_score += 10.0
            factors.append(f"Very strong volume trend (strength: {volume_trend_strength:.2f})")
        elif volume_trend_strength > volume_thresholds["moderate"]:
            volume_score += 5.0
            factors.append(f"Moderate volume trend (strength: {volume_trend_strength:.2f})")
        elif volume_trend_strength < volume_thresholds["weak"]:
            volume_score -= 5.0
            factors.append(f"Weak volume trend (strength: {volume_trend_strength:.2f})")
        
        score += volume_score
        
        # Volatility: Moderate to high (10 points)
        if data["volatility_category"] in ["MODERATE", "HIGH"]:
            score += 10.0
            factors.append(f"{data['volatility_category']} volatility")
        elif data["volatility_category"] == "EXTREME":
            score -= 10.0
            factors.append("Extreme volatility (too risky)")
        else:
            score += 5.0
            factors.append(f"{data['volatility_category']} volatility (low)")
        
        # RSI momentum: Aligned with trend (10 points)
        rsi_momentum_check = float(data["rsi_momentum"])  # Required (NO FALLBACKS) - will raise if invalid
        if (data["trend_direction"] == "BULLISH" and rsi_momentum_check > 0) or \
           (data["trend_direction"] == "BEARISH" and rsi_momentum_check < 0):
            score += 10.0
            factors.append("RSI momentum aligned")
        else:
            score -= 5.0
            factors.append("RSI momentum misaligned")
        
        return max(0.0, score), factors
    
    def _score_breakout(self, data: Dict[str, Any]) -> tuple:
        """Score breakout - requires pressure buildup + volume surge + volatility"""
        score = 0.0
        factors = []
        
        # Pressure: Strong directional pressure indicates breakout potential (30 points)
        net_pressure = data["net_pressure"]
        pressure_strength = abs(net_pressure)
        if pressure_strength > 0.4:
            score += 30.0
            factors.append(f"Extreme pressure buildup ({net_pressure:+.2f})")
        elif pressure_strength > 0.25:
            score += 20.0
            factors.append(f"Strong pressure ({net_pressure:+.2f})")
        elif pressure_strength > 0.1:
            score += 10.0
            factors.append(f"Moderate pressure ({net_pressure:+.2f})")
        else:
            score -= 15.0
            factors.append("Weak pressure (no breakout momentum)")
        
        # Volume: Need surge for breakout confirmation (25 points)
        if data["volume_category"] in ["VERY_HIGH", "EXTREME"]:
            score += 25.0
            factors.append(f"{data['volume_category']} volume (breakout surge)")
        elif data["volume_category"] == "HIGH":
            score += 15.0
            factors.append("High volume (good)")
        elif data["volume_category"] == "NORMAL":
            score += 5.0
            factors.append("Normal volume (acceptable)")
        else:
            score -= 15.0
            factors.append(f"{data['volume_category']} volume (insufficient for breakout)")
        
        # Volatility: Moderate to high (20 points)
        if data["volatility_category"] in ["MODERATE", "HIGH"]:
            score += 20.0
            factors.append(f"{data['volatility_category']} volatility")
        elif data["volatility_category"] in ["LOW", "VERY_LOW"]:
            score -= 15.0
            factors.append(f"{data['volatility_category']} volatility (insufficient)")
        else:
            score += 5.0
            factors.append(f"{data['volatility_category']} volatility")
        
        # Trend: Trending helps (15 points)
        if data["trend_direction"] in ["BULLISH", "BEARISH"]:
            score += 15.0
            factors.append(f"{data['trend_direction']} trend")
        else:
            score += 5.0
            factors.append("Sideways trend")
        
        # Volume: Confirms breakout (10 points)
        if data["volume_category"] in ["NORMAL", "HIGH", "VERY_HIGH"]:
            score += 10.0
            factors.append(f"{data['volume_category']} volume")
        else:
            score -= 5.0
            factors.append(f"{data['volume_category']} volume (weak)")
        
        return max(0.0, score), factors
    
    def _score_range_trading(self, data: Dict[str, Any]) -> tuple:
        """Score range trading - requires S/R levels + sideways trend + range patterns"""
        score = 0.0
        factors = []
        
        # Patterns: Range patterns strongly indicate range trading (30 points)
        if self._has_pattern_in_list(data["channel_patterns"], ["CHANNEL", "HORIZONTAL_CHANNEL"]):
            score += 30.0
            factors.append("Channel pattern detected (strong range signal)")
        elif self._has_pattern_in_list(data["triangle_patterns"], ["SYMMETRICAL_TRIANGLE"]):
            score += 20.0
            factors.append("Symmetrical triangle (range-bound)")
        elif self._has_pattern_in_list(data["wedge_patterns"], ["WEDGE"]):
            score += 15.0
            factors.append("Wedge pattern (range potential)")
        else:
            score += 5.0
            factors.append("No range patterns")
        
        # Trend: Sideways required (30 points)
        if data["trend_direction"] == "SIDEWAYS":
            score += 30.0
            factors.append("Sideways trend")
        else:
            score -= 20.0
            factors.append(f"{data['trend_direction']} trend (not sideways)")
        
        # Volatility: Moderate to low (20 points)
        if data["volatility_category"] in ["MODERATE", "LOW"]:
            score += 20.0
            factors.append(f"{data['volatility_category']} volatility")
        elif data["volatility_category"] == "VERY_LOW":
            score += 10.0
            factors.append("Very low volatility")
        else:
            score -= 10.0
            factors.append(f"{data['volatility_category']} volatility (too high)")
        
        # Volume: Normal is fine (10 points)
        if data["volume_category"] in ["NORMAL", "HIGH"]:
            score += 10.0
            factors.append(f"{data['volume_category']} volume")
        else:
            score += 5.0
            factors.append(f"{data['volume_category']} volume")
        
        return max(0.0, score), factors
    
    def _score_low_volatility_range(self, data: Dict[str, Any]) -> tuple:
        """Score low volatility range - requires LOW volatility + sideways trend + range patterns"""
        score = 0.0
        factors = []
        
        # Volatility: LOW/VERY_LOW required (40 points)
        if data["volatility_category"] in ["LOW", "VERY_LOW"]:
            score += 40.0
            factors.append(f"{data['volatility_category']} volatility")
        else:
            score -= 30.0
            factors.append(f"{data['volatility_category']} volatility (too high)")
        
        # Trend: Sideways required (30 points)
        if data["trend_direction"] == "SIDEWAYS":
            score += 30.0
            factors.append("Sideways trend")
        else:
            score -= 20.0
            factors.append(f"{data['trend_direction']} trend (not sideways)")
        
        # Patterns: Range patterns confirm low volatility range (20 points)
        if self._has_pattern_in_list(data["channel_patterns"], ["CHANNEL", "HORIZONTAL_CHANNEL"]):
            score += 20.0
            factors.append("Channel pattern (range confirmation)")
        elif self._has_pattern_in_list(data["triangle_patterns"], ["SYMMETRICAL_TRIANGLE"]):
            score += 15.0
            factors.append("Symmetrical triangle (range potential)")
        else:
            score += 5.0
            factors.append("No range patterns")
        
        # Volume: Low is acceptable (10 points)
        if data["volume_category"] in ["LOW", "NORMAL"]:
            score += 10.0
            factors.append(f"{data['volume_category']} volume")
        else:
            score += 5.0
            factors.append(f"{data['volume_category']} volume")
        
        return max(0.0, score), factors
    
    def _score_high_volatility(self, data: Dict[str, Any]) -> tuple:
        """Score high volatility strategy"""
        score = 0.0
        factors = []
        
        # Volatility: HIGH+ required (40 points)
        if data["volatility_category"] in ["HIGH", "VERY_HIGH", "EXTREME"]:
            score += 40.0
            factors.append(f"{data['volatility_category']} volatility")
        else:
            score -= 30.0
            factors.append(f"{data['volatility_category']} volatility (insufficient)")
        
        # Trend: Sideways or weak trend (20 points)
        if data["trend_direction"] == "SIDEWAYS":
            score += 20.0
            factors.append("Sideways trend")
        else:
            trend_strength_check = float(data["trend_strength"])  # Required (NO FALLBACKS) - will raise if invalid
            if trend_strength_check < 0.5:
                score += 10.0
                factors.append("Weak trend")
            else:
                score -= 10.0
                factors.append(f"Strong {data['trend_direction']} trend (use trend_following)")
        
        # Volume: Moderate to high (20 points)
        if data["volume_category"] in ["NORMAL", "HIGH", "VERY_HIGH"]:
            score += 20.0
            factors.append(f"{data['volume_category']} volume")
        else:
            score += 5.0
            factors.append(f"{data['volume_category']} volume")
        
        # Market condition: Acceptable risk (20 points)
        if data["risk_level"] in ["LOW", "MEDIUM"]:
            score += 20.0
            factors.append(f"{data['risk_level']} risk")
        else:
            score -= 10.0
            factors.append(f"{data['risk_level']} risk")
        
        return max(0.0, score), factors
    
    def _score_standard(self, data: Dict[str, Any]) -> tuple:
        """Score standard strategy - balanced medium-term trades (1-4h holds)"""
        score = 0.0
        factors = []
        
        # Volatility: MODERATE or LOW-MODERATE preferred (30 points)
        if data["volatility_category"] == "MODERATE":
            score += 30.0
            factors.append("Moderate volatility (ideal)")
        elif data["volatility_category"] == "LOW":
            score += 20.0
            factors.append("Low volatility (acceptable)")
        elif data["volatility_category"] == "HIGH":
            score += 15.0
            factors.append("High volatility (manageable)")
        else:
            score -= 10.0
            factors.append(f"{data['volatility_category']} volatility (poor)")
        
        # Volume: NORMAL/HIGH preferred (20 points)
        vol_cat = data["volume_category"]
        if vol_cat in ["NORMAL", "HIGH"]:
            score += 20.0
            factors.append(f"{vol_cat} volume (good)")
        elif vol_cat == "VERY_HIGH":
            score += 15.0
            factors.append("Very high volume (acceptable)")
        elif vol_cat == "LOW":
            score += 10.0
            factors.append("Low volume (suboptimal)")
        else:
            score -= 10.0
            factors.append(f"{vol_cat} volume (poor)")
        
        # RSI: Wide range acceptable (20 points) - NO FALLBACKS
        rsi = float(data["rsi_value"])
        if 35 <= rsi <= 65:
            score += 20.0
            factors.append(f"RSI {rsi:.1f} (neutral - ideal)")
        elif 25 <= rsi < 35 or 65 < rsi <= 75:
            score += 15.0
            factors.append(f"RSI {rsi:.1f} (directional opportunity)")
        else:
            score += 5.0
            factors.append(f"RSI {rsi:.1f} (extreme - careful)")
        
        # Spread: Wider spread acceptable than scalping (15 points)
        try:
            spread = float(data["spread_pct"])
        except (ValueError, TypeError):
            spread = 1.0
        # Use spread thresholds from config
        if spread < TradingConfig.SPREAD_THRESHOLDS["acceptable"]:
            score += 15.0
            factors.append(f"Excellent spread ({spread*100:.3f}%)")
        elif spread < TradingConfig.SPREAD_THRESHOLDS["poor"]:
            score += 10.0
            factors.append(f"Good spread ({spread*100:.3f}%)")
        else:
            score += 5.0
            factors.append(f"Acceptable spread ({spread*100:.3f}%)")
        
        # Trend: Clear trend helps (15 points)
        trend_15m = data["trend_15m"]
        trend_1h = data["trend_1h"]
        if trend_15m != "SIDEWAYS" and trend_15m == trend_1h:
            score += 15.0
            factors.append(f"Strong trend alignment ({trend_15m})")
        elif trend_15m != "SIDEWAYS" or trend_1h != "SIDEWAYS":
            score += 10.0
            factors.append("Some trend present")
        else:
            score += 5.0
            factors.append("Sideways (range trading)")
        
        return max(0.0, score), factors
    
    def _calculate_confidence(self, strategy_scores: Dict[str, Dict], best_strategy: str, data: Dict[str, Any]) -> float:
        """Calculate dynamic confidence based on score quality and data completeness"""
        # Ensure best_score is float
        # NO FALLBACKS
        if best_strategy not in strategy_scores:
            raise ValueError(f"Strategy '{best_strategy}' not found in strategy_scores - NO FALLBACKS")
        best_score_data = strategy_scores[best_strategy]
        best_score = float(best_score_data["score"])
        try:
            best_score = float(best_score)
        except (ValueError, TypeError):
            best_score = 0.0
        
        # Get 2nd best score
        # Edge case: If only one strategy exists, second_score = 0.0
        if len(strategy_scores) == 1:
            score_gap = best_score  # Only one strategy, gap = score itself
            gap_confidence = min(0.3, score_gap / 50.0)
        else:
            # strategy_scores items are (strategy_name, score_dict) tuples - trust API contract
            def safe_float_score(item):
                # score_dict always has "score" key with float value (guaranteed by _score_strategy)
                return float(item[1]["score"])
            
            sorted_scores = sorted(strategy_scores.items(), key=safe_float_score, reverse=True)
            if len(sorted_scores) > 1:
                # sorted_scores[1] is (strategy_name, score_dict) tuple - trust API contract
                second_score_data = sorted_scores[1][1]
                # score_dict always has "score" key (guaranteed by _score_strategy)
                second_score = float(second_score_data["score"])
            else:
                second_score = 0.0  # Fallback if somehow only one strategy in sorted list
            
            # Gap confidence: bigger gap = more confident (0-0.3)
            score_gap = best_score - second_score
            gap_confidence = min(0.3, score_gap / 50.0)
        
        # Base confidence from score magnitude (0-0.5)
        score_confidence = min(0.5, best_score / 100.0)
        
        # Data quality confidence: check if critical data is available (0-0.2)
        data_quality = 0.2
        missing_critical = []
        
        if data["current_price"] <= 0:
            missing_critical.append("price")
            data_quality -= 0.05
        if data["volatility_category"] == "UNKNOWN":
            missing_critical.append("volatility")
            data_quality -= 0.05
        if data["trend_direction"] == "UNKNOWN":
            missing_critical.append("trend")
            data_quality -= 0.05
        rsi_value_check = float(data["rsi_value"])  # Required (NO FALLBACKS) - will raise if invalid
        if rsi_value_check <= 0:
            missing_critical.append("rsi")
            data_quality -= 0.05
        
        data_quality = max(0.0, data_quality)
        
        # Total confidence
        total_confidence = score_confidence + gap_confidence + data_quality
        total_confidence = min(0.95, max(0.1, total_confidence))  # Clamp between 0.1 and 0.95
        
        return round(total_confidence, 3)
    
    def _build_reasoning(self, strategy: str, factors: List[str], confidence: float) -> str:
        """Build human-readable reasoning from factors"""
        # Use confidence thresholds from config
        if confidence >= TradingConfig.CONFIDENCE_THRESHOLDS["high"]:
            conf_level = "high"
        elif confidence >= TradingConfig.CONFIDENCE_THRESHOLDS["medium"]:
            conf_level = "moderate"
        else:
            conf_level = "low"
        
        factors_str = ", ".join(factors[:5])  # Limit to 5 factors
        return f"{strategy} ({conf_level} confidence: {confidence:.2f}) - {factors_str}"
    
    def _break_strategy_tie(self, tied_strategies: List[tuple], data: Dict[str, Any]) -> tuple:
        """
        Intelligent tie-breaking when multiple strategies have the same score
        
        Priority order:
        1. Current strategy (prefer stability - avoid unnecessary switches)
        2. Strategy with better historical performance (if available)
        3. More specific strategy (e.g., "scalping" over "standard" when conditions match)
        4. Default to "standard" as fallback
        
        Args:
            tied_strategies: List of (strategy_name, score_data) tuples with equal scores
            data: Market data dict (for context)
            
        Returns:
            (strategy_name, score_data) tuple of the selected strategy
        """
        if not tied_strategies:
            raise ValueError("No strategies provided for tie-breaking (NO FALLBACKS)")
        if len(tied_strategies) == 1:
            return tied_strategies[0]
        
        # Priority 1: Prefer current strategy (stability)
        current_strategy_name = self.current_strategy
        for strategy_tuple in tied_strategies:
            if strategy_tuple[0] == current_strategy_name:
                logger.debug(f"📊 Tie broken: Preferring current strategy '{current_strategy_name}' (stability)")
                return strategy_tuple
        
        # Priority 2: Prefer strategy with better historical performance
        # CRITICAL FIX: ML-safe + replay-deterministic performance tie-breaking
        # Only use performance-based tie-break if explicitly enabled and sufficient data exists
        from config.config import TradingConfig
        
        if TradingConfig.ENABLE_PERFORMANCE_TIEBREAK:
            # Calculate performance score: win_rate * (1 + profit_factor)
            best_performance = -1.0
            best_performance_strategy = None
            
            for strategy_tuple in tied_strategies:
                strategy_name = strategy_tuple[0]
                if strategy_name in self.strategy_performance:
                    perf = self.strategy_performance[strategy_name]
                    total_trades = perf["total_trades"]
                    
                    # CRITICAL: Only use performance if sufficient trades for statistical significance
                    if total_trades >= TradingConfig.MIN_PERF_TRADES:
                        win_rate = perf["successful_trades"] / total_trades
                        # Normalize profit (assume average profit per trade is reasonable)
                        avg_profit = perf["total_profit"] / total_trades if total_trades > 0 else 0.0
                        profit_factor = min(1.0, abs(avg_profit) / 100.0)  # Normalize to [0, 1]
                        performance_score = win_rate * (1.0 + profit_factor)
                        
                        if performance_score > best_performance:
                            best_performance = performance_score
                            best_performance_strategy = strategy_tuple
            
            if best_performance_strategy and best_performance > 0:
                logger.debug(f"📊 Tie broken: Preferring '{best_performance_strategy[0]}' (performance: {best_performance:.3f}, trades: {self.strategy_performance[best_performance_strategy[0]]['total_trades']})")
                return best_performance_strategy
        else:
            logger.debug("📊 Performance tie-break disabled (ENABLE_PERFORMANCE_TIEBREAK=False) - skipping for ML determinism")
        
        # Priority 3: Prefer more specific strategies over generic "standard"
        # Specific strategies: scalping, spike_hunting, low_volatility_range, etc.
        # Generic strategies: standard
        # CRITICAL FIX: Explicit priority order ensures deterministic tie-breaking
        # Order: most specific → least specific → generic
        specific_strategies_priority = ["scalping", "spike_hunting", "low_volatility_range", "high_volatility", 
                              "trend_following", "breakout", "range_trading"]
        
        # CRITICAL FIX: Use explicit priority order for deterministic tie-breaking
        # Check strategies in priority order (most specific first)
        for priority_strategy in specific_strategies_priority:
            for strategy_tuple in tied_strategies:
                if strategy_tuple[0] == priority_strategy:
                    logger.debug(f"📊 Tie broken: Preferring specific strategy '{priority_strategy}' (priority order)")
                    return strategy_tuple
        
        # Priority 4: Default to "standard" if available, otherwise first in list
        for strategy_tuple in tied_strategies:
            if strategy_tuple[0] == "standard":
                logger.debug(f"📊 Tie broken: Defaulting to 'standard' strategy")
                return strategy_tuple
        
        # Fallback: Return first strategy (deterministic - first in tied list)
        logger.debug(f"📊 Tie broken: Using first strategy '{tied_strategies[0][0]}' (fallback)")
        return tied_strategies[0]
    
    def get_current_strategy_config(self) -> Dict[str, Any]:
        """Get current strategy configuration"""
        return self.current_strategy_config.copy()
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for specific strategy"""
        if strategy_name not in self.strategy_configs:
            raise ValueError(f"Unknown strategy: {strategy_name} - NO FALLBACKS")
        return self.strategy_configs[strategy_name].copy()
    
    
    def _find_next_best_strategy_by_score(self, market_data: Dict[str, Any], rejected_strategy: str) -> str:
        """Find next best strategy by re-scoring (excluding rejected)"""
        try:
            data = self._extract_market_data(market_data)
            strategy_scores = {}
            
            # Exclude analysis-only strategies and rejected strategy
            tradeable_strategies = [s for s in self.strategy_configs.keys() if s not in self._analysis_only_strategies]
            for strategy_name in tradeable_strategies:
                if strategy_name == rejected_strategy:
                    continue  # Skip rejected strategy
                score, factors = self._score_strategy(strategy_name, data)
                strategy_scores[strategy_name] = score
            
            if strategy_scores:
                # CRITICAL FIX: Use explicit tie-breaking instead of relying on max() insertion order
                max_score = max(score for score in strategy_scores.values())
                tied_strategies = [
                    (name, score) for name, score in strategy_scores.items()
                    if abs(score - max_score) < self.SCORE_EPSILON
                ]
                
                if len(tied_strategies) == 1:
                    best_name, best_score = tied_strategies[0]
                else:
                    # Multiple strategies tied - use explicit tie-breaking
                    logger.debug(f"📊 {len(tied_strategies)} alternative strategies tied at score {max_score:.2f}, using tie-breaking")
                    # Convert to same format as _break_strategy_tie expects: (name, {"score": score})
                    tied_strategies_formatted = [(name, {"score": score}) for name, score in tied_strategies]
                    best_tuple = self._break_strategy_tie(tied_strategies_formatted, data)
                    best_name = best_tuple[0]
                    best_score = best_tuple[1]["score"]
                
                logger.info(f"✅ Alternative strategy: {best_name} (score: {best_score:.2f})")
                return best_name
            
            return "standard"
        except Exception as e:
            logger.error(f"❌ Error finding alternative strategy: {e}")
            return "standard"
    
    def _can_switch_strategy(self, data_timestamp: float) -> bool:
        """
        Check if strategy switching is allowed (dynamic cooldown based on volatility)
        
        CRITICAL: Uses data_timestamp instead of time.time() for replay determinism.
        
        Args:
            data_timestamp: Timestamp from market_data (for deterministic cooldown)
            
        Returns:
            bool: True if switching is allowed, False if cooldown is active
        """
        # CRITICAL FIX: Use data_timestamp instead of time.time()
        # Initialize last_strategy_switch on first call if not set
        if self.last_strategy_switch == 0.0:
            # First call - allow switch and initialize timestamp
            self.last_strategy_switch = data_timestamp
            return True
        
        time_since_last_switch = data_timestamp - self.last_strategy_switch
        
        # Dynamic cooldown based on market volatility
        # Get current volatility from the last market data if available
        if self._last_market_data:
            volatility_5m = self._last_market_data["volatility_5m"]  # Required (NO FALLBACKS)
            volatility_thresholds = TradingConfig.VOLATILITY_THRESHOLDS
            
            if volatility_5m > volatility_thresholds["high"]:
                cooldown = TradingConfig.STRATEGY_SWITCH_COOLDOWN_HIGH_VOLATILITY
            elif volatility_5m > volatility_thresholds["moderate"]:
                cooldown = TradingConfig.STRATEGY_SWITCH_COOLDOWN_MODERATE_VOLATILITY
            else:  # Low volatility (<1%)
                cooldown = TradingConfig.STRATEGY_SWITCH_COOLDOWN_LOW_VOLATILITY
        else:
            cooldown = self.strategy_switch_cooldown  # Default from config
        
        return time_since_last_switch >= cooldown
    
    def _switch_strategy(self, new_strategy: str, data_timestamp: float) -> None:
        """
        Switch to new strategy
        
        CRITICAL: Uses data_timestamp instead of time.time() for replay determinism.
        
        Args:
            new_strategy: Strategy name to switch to
            data_timestamp: Timestamp from market_data (for deterministic state tracking)
        """
        try:
            old_strategy = self.current_strategy
            self.current_strategy = new_strategy
            # NO FALLBACKS
            if new_strategy not in self.strategy_configs:
                raise ValueError(f"Strategy '{new_strategy}' not found in strategy_configs - NO FALLBACKS")
            self.current_strategy_config = self.strategy_configs[new_strategy]
            
            # CRITICAL FIX: Use data_timestamp instead of time.time()
            self.last_strategy_switch = data_timestamp
            
            logger.info(f"🔄 Strategy switched: {old_strategy} → {new_strategy}")
            logger.info(f"   📊 New config: {self.current_strategy_config}")
            
            # Note: Trading logger and prediction engine updates are handled elsewhere
            # Strategy switch completed successfully
            
            # Notify SessionManager of strategy change for dashboard update
            self._notify_session_strategy_change(new_strategy)
            
        except Exception as e:
            logger.error(f"❌ Strategy switch failed: {e}")
            # Revert to previous strategy
            self.current_strategy = "standard"
            self.current_strategy_config = self.strategy_configs["standard"]
    
    def force_strategy(self, strategy_name: str, data_timestamp: Optional[float] = None) -> bool:
        """
        Force switch to specific strategy (bypass cooldown)
        
        Args:
            strategy_name: Strategy name to force
            data_timestamp: Optional timestamp (if None, uses current time for non-deterministic mode)
                For deterministic mode, always provide timestamp from market_data
        """
        try:
            if strategy_name not in self.strategy_configs:
                logger.error(f"❌ Unknown strategy: {strategy_name}")
                return False
            
            # CRITICAL FIX: Require timestamp for determinism (NO FALLBACKS)
            if data_timestamp is None:
                raise ValueError("force_strategy requires data_timestamp for deterministic strategy selection (NO FALLBACKS)")
            
            self._switch_strategy(strategy_name, data_timestamp)
            logger.info(f"🔧 Strategy forced to: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Force strategy failed: {e}")
            return False
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategies"""
        return list(self.strategy_configs.keys())
    
    def get_strategy_description(self, strategy_name: str) -> str:
        """Get human-readable description of strategy"""
        descriptions = {
            "standard": "Balanced strategy for normal market conditions",
            "low_volatility_range": "Optimized for LOW and VERY_LOW volatility, range-bound markets with support/resistance",
            "high_volatility": "Designed for high volatility, trending markets",
            "spike_hunting": "Specialized for extreme volatility and price spikes",
            "trend_following": "Optimized for strong trending markets with momentum confirmation",
            "scalping": "High-frequency scalping for small, quick profits with tight risk management",
        }
        if strategy_name not in descriptions:
            raise ValueError(f"Unknown strategy: {strategy_name} - must be one of {list(descriptions.keys())} (NO FALLBACKS)")
        return descriptions[strategy_name]
    
    def _record_strategy_selection(self, strategy: str, market_data: Dict[str, Any], 
                                  recommendation, data_timestamp: float) -> None:
        """
        Record strategy selection for ML learning
        
        CRITICAL: Uses data_timestamp instead of time.time() for replay determinism.
        
        Args:
            strategy: Strategy name that was selected
            market_data: Market data dictionary
            recommendation: Strategy recommendation object
            data_timestamp: Timestamp from market_data (for deterministic records)
        """
        try:
            # Record the strategy selection (without outcome yet)
            # The outcome will be recorded later when trades are executed
            selection_record = {
                "strategy": strategy,
                "market_conditions": market_data,
                "confidence": recommendation.confidence,
                "reasoning": recommendation.reasoning,
                "timestamp": data_timestamp  # CRITICAL FIX: Use data_timestamp instead of time.time()
            }
            
            # Store for later outcome recording
            self.pending_strategy_outcomes.append(selection_record)
            
            # Keep only recent records
            if len(self.pending_strategy_outcomes) > 100:
                self.pending_strategy_outcomes = self.pending_strategy_outcomes[-100:]
            
        except Exception as e:
            logger.error(f"❌ Strategy selection recording failed: {e}")
    
    def record_strategy_outcome(self, strategy: str, outcome: Dict[str, Any], 
                               data_timestamp: Optional[float] = None) -> None:
        """
        Record the outcome of a strategy for ML learning
        
        CRITICAL: Uses data_timestamp instead of time.time() for replay determinism.
        If data_timestamp is not provided, uses timestamp from outcome dict or raises.
        
        Args:
            strategy: Strategy name
            outcome: Outcome dictionary (must contain "profit" and "success")
            data_timestamp: Optional timestamp from market_data (preferred for determinism)
                If None, attempts to extract from outcome["timestamp"]
        """
        try:
            # Extract timestamp for deterministic tracking
            if data_timestamp is None:
                if "timestamp" in outcome:
                    data_timestamp = float(outcome["timestamp"])
                else:
                    raise ValueError(
                        "record_strategy_outcome requires data_timestamp or outcome['timestamp'] "
                        "for deterministic tracking (NO FALLBACKS)"
                    )
            
            # Find the most recent selection for this strategy
            for record in reversed(self.pending_strategy_outcomes):
                    if record["strategy"] == strategy:
                        logger.debug(f"Strategy outcome recorded: {strategy}")
                        
                        # Remove from pending
                        self.pending_strategy_outcomes.remove(record)
                        break
            
            # Also update local performance tracking
            if strategy not in self.strategy_performance:
                self.strategy_performance[strategy] = {
                    "total_trades": 0,
                    "successful_trades": 0,
                    "total_profit": 0.0,
                    "last_used": 0.0
                }
            
            perf = self.strategy_performance[strategy]
            perf["total_trades"] += 1
            perf["last_used"] = data_timestamp  # CRITICAL FIX: Use data_timestamp instead of time.time()
            
            # Calculate success and profit
            profit = outcome["profit"]  # Required (NO FALLBACKS)
            success = outcome["success"]  # Required (NO FALLBACKS)
            
            if success:
                perf["successful_trades"] += 1
            
            perf["total_profit"] += profit
            
            logger.info(f"📊 Strategy outcome recorded: {strategy} - Profit: {profit:.4f}, Success: {success}")
            
        except Exception as e:
            logger.error(f"❌ Strategy outcome recording failed: {e}")
    
    def get_ml_strategy_performance(self) -> Dict[str, Any]:
        """Get ML strategy performance statistics"""
        try:
            return {"message": "ML performance tracking not implemented yet"}
        except Exception as e:
            logger.error(f"❌ Failed to get ML strategy performance: {e}")
            return {"error": str(e)}
    
    
    def _notify_session_strategy_change(self, new_strategy: str):
        """Notify SessionManager of strategy change for dashboard update"""
        try:
            # Import here to avoid circular imports
            from core.session.session_manager import get_global_session_manager
            
            session_manager_instance = get_global_session_manager()
            
            # Update session data with new strategy
            if session_manager_instance.current_session_data:
                session_manager_instance.current_session_data["strategy"] = new_strategy
                
                # Sync updated session data to dashboard
                # Get dashboard service and update
                from core.services.system_initializer import get_system_initializer
                system_initializer = get_system_initializer()
                dashboard_service = system_initializer.get_singleton_system("dashboard_service")  # Required (NO FALLBACKS)
                if dashboard_service:
                    dashboard_service.update_session_data(session_manager_instance.current_session_data)
                    logger.info(f"🔄 Strategy switched to: {new_strategy}")
                
                logger.info(f"📊 Dashboard notified of strategy change: {new_strategy}")
            
        except Exception as e:
            logger.error(f"❌ Failed to notify session of strategy change: {e}")
    
