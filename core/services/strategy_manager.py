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
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.strategy_configs = config.STRATEGY_CONFIGS
        
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
    
    @staticmethod
    def _safe_get(data: Any, key: str, default: Any) -> Any:
        """Safely get value from dict, return default if not dict or key missing"""
        return data[key] if isinstance(data, dict) and key in data else default
    
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
            if recommendation.confidence < 0.3:
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
            logger.error(f"   Using current strategy: {self.current_strategy}")
            return self.current_strategy
    
    def _select_strategy_business_logic(self, market_data: Dict[str, Any]):
        """Sophisticated strategy selection using multi-factor scoring with dynamic confidence"""
        try:
            # Extract all available market data
            data = self._extract_market_data(market_data)
            
            # Score all strategies
            strategy_scores = {}
            for strategy_name in self.strategy_configs.keys():
                score, factors = self._score_strategy(strategy_name, data)
                # Ensure score is always a float - handle all types safely
                try:
                    score = float(score) if score is not None else 0.0
                except (ValueError, TypeError):
                    score = 0.0
                strategy_scores[strategy_name] = {
                    "score": score,
                    "factors": factors
                }
            
            # Select best strategy - ensure safe float conversion
            def safe_get_score(item):
                try:
                    if not isinstance(item, tuple) or len(item) < 2:
                        return 0.0
                    score_data = item[1]
                    if not isinstance(score_data, dict):
                        return 0.0
                    score_val = score_data["score"] if "score" in score_data else 0.0
                    return float(score_val) if score_val is not None else 0.0
                except (ValueError, TypeError, AttributeError, IndexError):
                    return 0.0
            
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
        trend_data = market_data["trend"]
        rsi_data = market_data["rsi"]
        sr_data = market_data["support_resistance"]
        orderbook_data = market_data["orderbook_analysis"]
        pressure_data = market_data["pressure"]
        funding_data = market_data["funding_analysis"]
        market_conditions = market_data["market_conditions"]
        
        # Extract detailed values using safe get helper - ensure numeric types are floats
        trend_strength_raw = self._safe_get(trend_data, "strength", 0.5)
        try:
            trend_strength = float(trend_strength_raw) if trend_strength_raw is not None else 0.5
        except (ValueError, TypeError):
            trend_strength = 0.5
        
        rsi_trend = self._safe_get(rsi_data, "rsi_trend", "NEUTRAL")
        rsi_signal = self._safe_get(rsi_data, "rsi_signal", "NEUTRAL")
        
        rsi_momentum_raw = self._safe_get(rsi_data, "rsi_momentum", 0.0)
        try:
            rsi_momentum = float(rsi_momentum_raw) if rsi_momentum_raw is not None else 0.0
        except (ValueError, TypeError):
            rsi_momentum = 0.0
        
        # STRATEGY INDEPENDENCE: S/R levels NOT used for strategy selection
        # Strategy selection is based purely on market conditions (volatility, trend, volume, RSI, pressure)
        # S/R level filtering happens AFTER strategy is selected in PredictionEngine
        current_price = float(market_data["current_price"])  # Required (NO FALLBACKS) - will raise if invalid
        
        # Orderbook data - ensure numeric types are floats
        spread_pct_raw = self._safe_get(orderbook_data, "spread_percentage", 0.0)
        try:
            spread_pct = float(spread_pct_raw) if spread_pct_raw is not None else 0.0
        except (ValueError, TypeError):
            spread_pct = 0.0
        
        liquidity_score_raw = self._safe_get(orderbook_data, "liquidity_score", 0.5)
        try:
            liquidity_score = float(liquidity_score_raw) if liquidity_score_raw is not None else 0.5
        except (ValueError, TypeError):
            liquidity_score = 0.5
        
        # Pressure data - ensure numeric types are floats
        net_pressure_raw = self._safe_get(pressure_data, "net_pressure", 0.0)
        try:
            net_pressure = float(net_pressure_raw) if net_pressure_raw is not None else 0.0
        except (ValueError, TypeError):
            net_pressure = 0.0
        
        pressure_ratio_raw = self._safe_get(pressure_data, "pressure_ratio", 1.0)
        try:
            pressure_ratio = float(pressure_ratio_raw) if pressure_ratio_raw is not None else 1.0
        except (ValueError, TypeError):
            pressure_ratio = 1.0
        
        # Funding data
        funding_trend = self._safe_get(funding_data, "trend", {})
        funding_direction = self._safe_get(funding_trend, "direction", "STABLE")
        
        funding_strength_raw = self._safe_get(funding_trend, "strength", 0.0)
        try:
            funding_strength = float(funding_strength_raw) if funding_strength_raw is not None else 0.0
        except (ValueError, TypeError):
            funding_strength = 0.0
        
        # Market conditions
        market_condition = self._safe_get(market_conditions, "condition", "NEUTRAL")
        risk_level = self._safe_get(market_conditions, "risk_level", "MEDIUM")
        
        # Pattern data
        patterns_data = market_data["patterns"]  # Required (NO FALLBACKS)
        patterns_nested = self._safe_get(patterns_data, "patterns_nested", {})
        patterns_flat = self._safe_get(patterns_data, "patterns", [])
        
        pattern_confidence_raw = self._safe_get(patterns_data, "overall_confidence", 0.0)
        try:
            pattern_confidence = float(pattern_confidence_raw) if pattern_confidence_raw is not None else 0.0
        except (ValueError, TypeError):
            pattern_confidence = 0.0
        
        # Extract pattern categories for strategy selection
        reversal_patterns = self._safe_get(patterns_nested, "reversal_patterns", [])
        continuation_patterns = self._safe_get(patterns_nested, "continuation_patterns", [])
        triangle_patterns = self._safe_get(patterns_nested, "triangle_patterns", [])
        channel_patterns = self._safe_get(patterns_nested, "channel_patterns", [])
        wedge_patterns = self._safe_get(patterns_nested, "wedge_patterns", [])
        trend_patterns = self._safe_get(patterns_nested, "trend_patterns", [])
        
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
            "market_condition": market_condition,
            "risk_level": risk_level,
            # Pattern data for strategy selection
            "pattern_confidence": pattern_confidence,
            "reversal_patterns": reversal_patterns,
            "continuation_patterns": continuation_patterns,
            "triangle_patterns": triangle_patterns,
            "channel_patterns": channel_patterns,
            "wedge_patterns": wedge_patterns,
            "trend_patterns": trend_patterns
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
        
        scorer = strategy_scorers[strategy_name] if strategy_name in strategy_scorers else self._score_standard
        return scorer(data)
    
    def _score_scalping(self, data: Dict[str, Any]) -> tuple:
        """Score scalping strategy - requires tight spreads, moderate volatility, good RSI"""
        score = 0.0
        factors = []
        
        # Volatility: MODERATE is ideal (30 points)
        if data["volatility_category"] == "MODERATE":
            score += 30.0
            factors.append("Moderate volatility")
        elif data["volatility_category"] in ["LOW", "HIGH"]:
            score += 15.0
            factors.append(f"{data['volatility_category']} volatility (suboptimal)")
        else:
            score -= 20.0
            factors.append(f"{data['volatility_category']} volatility (poor)")
        
        # RSI: 30-70 is ideal (25 points)
        try:
            rsi = float(data["rsi_value"]) if "rsi_value" in data and data["rsi_value"] is not None else 50.0
        except (ValueError, TypeError):
            rsi = 50.0
        if 30 <= rsi <= 70:
            score += 25.0
            factors.append(f"RSI {rsi:.1f} (good)")
        elif 20 <= rsi < 30 or 70 < rsi <= 80:
            score += 10.0
            factors.append(f"RSI {rsi:.1f} (acceptable)")
        else:
            score -= 15.0
            factors.append(f"RSI {rsi:.1f} (extreme)")
        
        # Spread: Tight spread is critical (30 points)
        spread = float(data["spread_pct"])  # Required (NO FALLBACKS) - will raise if invalid
        if spread < 0.0001:  # <0.01%
            score += 30.0
            factors.append(f"Tight spread ({spread*100:.3f}%)")
        elif spread < 0.0005:  # <0.05%
            score += 15.0
            factors.append(f"Moderate spread ({spread*100:.3f}%)")
        else:
            score -= 25.0
            factors.append(f"Wide spread ({spread*100:.3f}%) - HIGH SLIPPAGE RISK")
        
        # Volume: Need decent volume (15 points)
        vol_cat = data["volume_category"]
        if vol_cat in ["NORMAL", "HIGH", "VERY_HIGH"]:
            score += 15.0
            factors.append(f"{vol_cat} volume")
        elif vol_cat == "LOW":
            score += 5.0
            factors.append("Low volume")
        else:
            score -= 10.0
            factors.append(f"{vol_cat} volume (insufficient)")
        
        # RSI momentum: Neutral/positive momentum (10 points)
        rsi_momentum = float(data["rsi_momentum"])  # Required (NO FALLBACKS) - will raise if invalid
        if -0.1 <= rsi_momentum <= 0.2:
            score += 10.0
            factors.append("Stable RSI momentum")
        else:
            score -= 5.0
            factors.append("Volatile RSI momentum")
        
        return max(0.0, score), factors
    
    def _score_spike_hunting(self, data: Dict[str, Any]) -> tuple:
        """Score spike hunting - requires extreme volatility + high volume"""
        score = 0.0
        factors = []
        
        # Volatility: EXTREME is required (40 points)
        vol_5m = float(data["volatility_5m"])  # Required (NO FALLBACKS) - will raise if invalid
        if vol_5m > 0.05 or data["volatility_category"] == "EXTREME":
            score += 40.0
            factors.append(f"Extreme volatility ({vol_5m*100:.2f}%)")
        elif data["volatility_category"] in ["HIGH", "VERY_HIGH"]:
            score += 20.0
            factors.append(f"High volatility ({vol_5m*100:.2f}%)")
        else:
            score -= 30.0
            factors.append(f"{data['volatility_category']} volatility (insufficient)")
        
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
        
        # Funding: Alignment with trend (20 points)
        funding_dir = data["funding_direction"]
        if data["trend_direction"] == "BULLISH" and funding_dir == "INCREASING":
            score += 20.0
            factors.append("Funding aligns with bullish trend")
        elif data["trend_direction"] == "BEARISH" and funding_dir == "DECREASING":
            score += 20.0
            factors.append("Funding aligns with bearish trend")
        elif funding_dir == "STABLE":
            score += 10.0
            factors.append("Stable funding")
        else:
            score -= 15.0
            factors.append(f"Funding misaligned ({funding_dir})")
        
        # Volume: High volume confirms trend (15 points)
        vol_cat = data["volume_category"]
        if vol_cat in ["HIGH", "VERY_HIGH", "EXTREME"]:
            score += 15.0
            factors.append(f"{vol_cat} volume confirms trend")
        elif vol_cat == "NORMAL":
            score += 10.0
            factors.append("Normal volume")
        else:
            score -= 10.0
            factors.append(f"{vol_cat} volume (weak)")
        
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
        
        # RSI: Wide range acceptable (20 points)
        try:
            rsi = float(data["rsi_value"]) if "rsi_value" in data and data["rsi_value"] is not None else 50.0
        except (ValueError, TypeError):
            rsi = 50.0
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
        if spread < 0.001:  # <0.1%
            score += 15.0
            factors.append(f"Excellent spread ({spread*100:.3f}%)")
        elif spread < 0.005:  # <0.5%
            score += 10.0
            factors.append(f"Good spread ({spread*100:.3f}%)")
        else:
            score += 5.0
            factors.append(f"Acceptable spread ({spread*100:.3f}%)")
        
        # Trend: Clear trend helps (15 points)
        trend_15m = data.get("trend_15m", "SIDEWAYS")
        trend_1h = data.get("trend_1h", "SIDEWAYS")
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
        best_score_data = strategy_scores[best_strategy] if best_strategy in strategy_scores else {}
        best_score = float(best_score_data["score"]) if "score" in best_score_data and isinstance(best_score_data["score"], (int, float, str)) else 0.0
        try:
            best_score = float(best_score)
        except (ValueError, TypeError):
            best_score = 0.0
        
        # Get 2nd best score - ensure all scores are float before sorting
        def safe_float_score(item):
            try:
                score_val = item[1]["score"] if "score" in item[1] else 0.0
                return float(score_val) if score_val is not None else 0.0
            except (ValueError, TypeError):
                return 0.0
        
        sorted_scores = sorted(strategy_scores.items(), key=safe_float_score, reverse=True)
        if len(sorted_scores) > 1:
            try:
                second_score_data = sorted_scores[1][1]
                second_score = float(second_score_data["score"]) if "score" in second_score_data and isinstance(second_score_data["score"], (int, float, str)) else 0.0
                second_score = float(second_score)
            except (ValueError, TypeError, IndexError, KeyError):
                second_score = 0.0
        else:
            second_score = 0.0
        
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
        if confidence >= 0.7:
            conf_level = "high"
        elif confidence >= 0.5:
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
            
            for strategy_name in self.strategy_configs.keys():
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
            volatility_5m = self._last_market_data["volatility_5m"]  # Required (NO FALLBACKS)
            if volatility_5m > 0.03:  # High volatility (>3%)
                cooldown = 60  # 1 minute for high volatility
            elif volatility_5m > 0.01:  # Moderate volatility (1-3%)
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
            self.current_strategy_config = self.strategy_configs[new_strategy] if new_strategy in self.strategy_configs else self.strategy_configs["standard"]
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
        return descriptions[strategy_name] if strategy_name in descriptions else f"Unknown strategy: {strategy_name}"  # NO FALLBACKS
    
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
            success = outcome["success"] if "success" in outcome else profit > 0
            
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
                dashboard_service = system_initializer.singleton_systems["dashboard_service"] if "dashboard_service" in system_initializer.singleton_systems else None
                if dashboard_service:
                    dashboard_service.update_session_data(session_manager_instance.current_session_data)
                    logger.info(f"🔄 Strategy switched to: {new_strategy}")
                
                logger.info(f"📊 Dashboard notified of strategy change: {new_strategy}")
            
        except Exception as e:
            logger.error(f"❌ Failed to notify session of strategy change: {e}")
    
