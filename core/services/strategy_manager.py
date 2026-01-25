#!/usr/bin/env python3
"""
Strategy Manager
Centralized strategy detection, selection, and management
Single Responsibility: Strategy decision making and configuration
"""

import time
from typing import Dict, Any, List
from loguru import logger
from config.config import TradingConfig


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
        self.last_strategy_switch = 0
        self.strategy_switch_cooldown = 300  # 5 minutes between switches
        
        # Strategy performance tracking
        self.strategy_performance = {}
        self.strategy_usage_count = {}
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
                "last_used": 0
            }
            self.strategy_usage_count[strategy_name] = 0
        
        logger.info("🎯 Strategy Manager initialized - Centralized strategy management")
        logger.info(f"   🎯 Current strategy: {self.current_strategy}")
    
    
    def detect_optimal_strategy(self, market_data: Dict[str, Any]) -> str:
        """
        Detect the optimal strategy using ML-powered analysis (SINGLE SOURCE OF TRUTH)
        
        Args:
            market_data: Current market data (price, volatility, trend, volume, etc.)
            
        Returns:
            str: Current active strategy name
        """
        try:
            # Pure business logic strategy selection (no ML for now)
            recommendation = self._select_strategy_business_logic(market_data)
            optimal_strategy = recommendation.strategy
            reasoning = recommendation.reasoning
            
            # Store market data for dynamic cooldown calculation
            self._last_market_data = market_data.copy()
            
            # Log business logic strategy selection
            logger.info(f"📊 Business Logic Strategy Decision: {optimal_strategy}")
            logger.info(f"   📊 Reasoning: {reasoning}")
            
            # Validate strategy compatibility (redundant check removed - scoring handles this)
            # Only check if confidence is too low (<0.3) - might indicate data issues
            # Use confidence threshold from config (configurable for optimization)
            from config.config import TradingConfig
            if recommendation.confidence < TradingConfig.CONFIDENCE_THRESHOLDS["low"]:
                logger.warning(f"⚠️ Low confidence ({recommendation.confidence:.2f}) for {optimal_strategy}, checking alternatives")
                # Find next best strategy
                optimal_strategy = self._find_next_best_strategy_by_score(market_data, optimal_strategy)
                logger.info(f"🔄 Selected alternative strategy: {optimal_strategy}")
            
            # Check if strategy switch is needed and allowed
            if optimal_strategy != self.current_strategy:
                if self._can_switch_strategy():
                    logger.info(f"🔄 Strategy switch: {self.current_strategy} → {optimal_strategy}")
                    self._switch_strategy(optimal_strategy)
                    
                    # Record strategy selection for learning
                    self._record_strategy_selection(optimal_strategy, market_data, recommendation)
                else:
                    logger.info(f"⏳ Strategy switch blocked (cooldown): {self.current_strategy} → {optimal_strategy}")
            else:
                # Still record for learning even if no switch
                self._record_strategy_selection(optimal_strategy, market_data, recommendation)
            
            return self.current_strategy
            
        except Exception as e:
            logger.error(f"❌ Strategy detection failed: {e}")
            raise  # NO FALLBACKS - detection failure must raise
    
    def _select_strategy_business_logic(self, market_data: Dict[str, Any]):
        """Sophisticated strategy selection using multi-factor scoring with dynamic confidence"""
        try:
            # Extract all available market data
            data = self._extract_market_data(market_data)
            
            # Score all tradeable strategies (exclude analysis-only strategies)
            strategy_scores = {}
            tradeable_strategies = [s for s in self.strategy_configs.keys() if s not in self._analysis_only_strategies]
            for strategy_name in tradeable_strategies:
                # _score_strategy() guarantees (float, list) tuple - trust API contract
                score, factors = self._score_strategy(strategy_name, data)
                strategy_scores[strategy_name] = {
                    "score": score,
                    "factors": factors
                }
            
            # Select best strategy
            # sorted() returns list of (strategy_name, score_dict) tuples - trust API contract
            def safe_get_score(item):
                # item is (strategy_name, score_dict) tuple from sorted()
                score_data = item[1]
                return float(score_data["score"])  # score_dict always has "score" key (guaranteed by _score_strategy)
            
            best_strategy = max(strategy_scores.items(), key=safe_get_score)
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
    
    def _extract_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize all available market data (NO FALLBACKS)"""
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
        
        # Funding data - NO FALLBACKS
        # Funding analyzer returns funding_trend key, not trend
        funding_trend = funding_data["funding_trend"]  # Required (NO FALLBACKS)
        funding_direction = funding_trend["direction"]  # Required (NO FALLBACKS)
        
        funding_strength_raw = funding_trend["strength"]
        try:
            funding_strength = float(funding_strength_raw)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid funding_strength value: {funding_strength_raw} - NO FALLBACKS")
        
        # Funding volatility for risk management - NO FALLBACKS
        funding_volatility_data = funding_data["funding_volatility"]
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
        if funding_volatility_cat == "HIGH":
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
        if data["trend_direction"] == "BULLISH" and funding_dir == "INCREASING":
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
        from config.config import TradingConfig
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
            raise ValueError("No second strategy found - NO FALLBACKS")
        
        # Base confidence from score magnitude (0-0.5)
        score_confidence = min(0.5, best_score / 100.0)
        
        # Gap confidence: bigger gap = more confident (0-0.3)
        score_gap = best_score - second_score
        gap_confidence = min(0.3, score_gap / 50.0)
        
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
                best = max(strategy_scores.items(), key=lambda x: x[1])
                logger.info(f"✅ Alternative strategy: {best[0]} (score: {best[1]:.2f})")
                return best[0]
            
            return "standard"
        except Exception as e:
            logger.error(f"❌ Error finding alternative strategy: {e}")
            return "standard"
    
    def _can_switch_strategy(self) -> bool:
        """Check if strategy switching is allowed (dynamic cooldown based on volatility)"""
        current_time = time.time()
        time_since_last_switch = current_time - self.last_strategy_switch
        
        # Dynamic cooldown based on market volatility
        # Get current volatility from the last market data if available
        if self._last_market_data:
            from config.config import TradingConfig
            volatility_5m = self._last_market_data["volatility_5m"]  # Required (NO FALLBACKS)
            volatility_thresholds = TradingConfig.VOLATILITY_THRESHOLDS
            
            if volatility_5m > volatility_thresholds["high"]:
                cooldown = 60  # 1 minute for high volatility
            elif volatility_5m > volatility_thresholds["moderate"]:
                cooldown = 180  # 3 minutes for moderate volatility
            else:  # Low volatility (<1%)
                cooldown = 300  # 5 minutes for low volatility
        else:
            cooldown = self.strategy_switch_cooldown  # Default 5 minutes
        
        return time_since_last_switch >= cooldown
    
    def _switch_strategy(self, new_strategy: str):
        """Switch to new strategy"""
        try:
            old_strategy = self.current_strategy
            self.current_strategy = new_strategy
            # NO FALLBACKS
            if new_strategy not in self.strategy_configs:
                raise ValueError(f"Strategy '{new_strategy}' not found in strategy_configs - NO FALLBACKS")
            self.current_strategy_config = self.strategy_configs[new_strategy]
            self.last_strategy_switch = time.time()
            
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
    
    def force_strategy(self, strategy_name: str) -> bool:
        """Force switch to specific strategy (bypass cooldown)"""
        try:
            if strategy_name not in self.strategy_configs:
                logger.error(f"❌ Unknown strategy: {strategy_name}")
                return False
            
            self._switch_strategy(strategy_name)
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
    
    def _record_strategy_selection(self, strategy: str, market_data: Dict[str, Any], recommendation) -> None:
        """Record strategy selection for ML learning"""
        try:
            
            # Record the strategy selection (without outcome yet)
            # The outcome will be recorded later when trades are executed
            selection_record = {
                "strategy": strategy,
                "market_conditions": market_data,
                "confidence": recommendation.confidence,
                "reasoning": recommendation.reasoning,
                "timestamp": time.time()
            }
            
            # Store for later outcome recording
            self.pending_strategy_outcomes.append(selection_record)
            
            # Keep only recent records
            if len(self.pending_strategy_outcomes) > 100:
                self.pending_strategy_outcomes = self.pending_strategy_outcomes[-100:]
            
        except Exception as e:
            logger.error(f"❌ Strategy selection recording failed: {e}")
    
    def record_strategy_outcome(self, strategy: str, outcome: Dict[str, Any]) -> None:
        """Record the outcome of a strategy for ML learning"""
        try:
            
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
                    "last_used": 0
                }
            
            perf = self.strategy_performance[strategy]
            perf["total_trades"] += 1
            perf["last_used"] = time.time()
            
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
    
