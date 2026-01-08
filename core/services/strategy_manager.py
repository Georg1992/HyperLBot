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
                strategy_scores[strategy_name] = {
                    "score": score,
                    "factors": factors
                }
            
            # Select best strategy
            best_strategy = max(strategy_scores.items(), key=lambda x: x[1]["score"])
            strategy_name = best_strategy[0]
            score_data = best_strategy[1]
            
            # Calculate dynamic confidence based on:
            # 1. Score magnitude (higher = more confident)
            # 2. Data quality (missing data = lower confidence)
            # 3. Score gap (bigger gap from 2nd place = more confident)
            confidence = self._calculate_confidence(strategy_scores, strategy_name, data)
            
            # Build reasoning from factors
            reasoning = self._build_reasoning(strategy_name, score_data["factors"], confidence)
            
            # Create recommendation object
            class Recommendation:
                def __init__(self, strategy, reasoning, confidence):
                    self.strategy = strategy
                    self.reasoning = reasoning
                    self.confidence = confidence
            
            logger.debug(f"📊 Strategy scores: {[(s, d['score']) for s, d in sorted(strategy_scores.items(), key=lambda x: x[1]['score'], reverse=True)[:3]]}")
            logger.info(f"📊 Selected: {strategy_name} (score: {score_data['score']:.2f}, confidence: {confidence:.2f})")
            
            return Recommendation(strategy_name, reasoning, confidence)
                
        except Exception as e:
            logger.error(f"❌ Strategy selection failed: {e}")
            # Create fallback recommendation with low confidence
            class Recommendation:
                def __init__(self, strategy, reasoning, confidence):
                    self.strategy = strategy
                    self.reasoning = reasoning
                    self.confidence = confidence
            return Recommendation("standard", f"Fallback due to error: {e}", 0.3)
    
    def _extract_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize all available market data"""
        # Basic data (flattened)
        volatility_category = market_data.get("volatility_category", "MODERATE")
        trend_direction = market_data.get("trend_direction", "SIDEWAYS")
        volume_category = market_data.get("volume_category", "MODERATE")
        volatility_5m = market_data.get("volatility_5m", 0.0)
        rsi_value = market_data.get("rsi_value", 50.0)
        
        # Extended data (nested)
        trend_data = market_data.get("trend", {})
        rsi_data = market_data.get("rsi", {})
        sr_data = market_data.get("support_resistance", {})
        orderbook_data = market_data.get("orderbook_analysis", {})
        pressure_data = market_data.get("pressure", {})
        funding_data = market_data.get("funding_analysis", {})
        market_conditions = market_data.get("market_conditions", {})
        
        # Extract detailed values
        trend_strength = trend_data.get("strength", 0.5) if isinstance(trend_data, dict) else 0.5
        rsi_trend = rsi_data.get("rsi_trend", "NEUTRAL") if isinstance(rsi_data, dict) else "NEUTRAL"
        rsi_signal = rsi_data.get("rsi_signal", "NEUTRAL") if isinstance(rsi_data, dict) else "NEUTRAL"
        rsi_momentum = rsi_data.get("rsi_momentum", 0.0) if isinstance(rsi_data, dict) else 0.0
        
        # S/R data
        sr_levels = sr_data.get("levels", []) if isinstance(sr_data, dict) else []
        top_support = sr_data.get("top_2_support", []) if isinstance(sr_data, dict) else []
        top_resistance = sr_data.get("top_2_resistance", []) if isinstance(sr_data, dict) else []
        strongest_support = sr_data.get("strongest_support", 0.0) if isinstance(sr_data, dict) else 0.0
        strongest_resistance = sr_data.get("strongest_resistance", 0.0) if isinstance(sr_data, dict) else 0.0
        current_price = market_data.get("current_price", 0.0)
        
        # Orderbook data
        spread_pct = orderbook_data.get("spread_percentage", 0.0) if isinstance(orderbook_data, dict) else 0.0
        liquidity_score = orderbook_data.get("liquidity_score", 0.5) if isinstance(orderbook_data, dict) else 0.5
        
        # Pressure data
        net_pressure = pressure_data.get("net_pressure", 0.0) if isinstance(pressure_data, dict) else 0.0
        pressure_ratio = pressure_data.get("pressure_ratio", 1.0) if isinstance(pressure_data, dict) else 1.0
        
        # Funding data
        funding_trend = funding_data.get("trend", {}) if isinstance(funding_data, dict) else {}
        funding_direction = funding_trend.get("direction", "STABLE") if isinstance(funding_trend, dict) else "STABLE"
        funding_strength = funding_trend.get("strength", 0.0) if isinstance(funding_trend, dict) else 0.0
        
        # Market conditions
        market_condition = market_conditions.get("condition", "NEUTRAL") if isinstance(market_conditions, dict) else "NEUTRAL"
        risk_level = market_conditions.get("risk_level", "MEDIUM") if isinstance(market_conditions, dict) else "MEDIUM"
        
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
            "sr_levels": sr_levels,
            "top_support": top_support,
            "top_resistance": top_resistance,
            "strongest_support": strongest_support,
            "strongest_resistance": strongest_resistance,
            "current_price": current_price,
            "spread_pct": spread_pct,
            "liquidity_score": liquidity_score,
            "net_pressure": net_pressure,
            "pressure_ratio": pressure_ratio,
            "funding_direction": funding_direction,
            "funding_strength": funding_strength,
            "market_condition": market_condition,
            "risk_level": risk_level
        }
    
    def _score_strategy(self, strategy_name: str, data: Dict[str, Any]) -> tuple:
        """Score a strategy based on all available market data"""
        score = 0.0
        factors = []
        
        if strategy_name == "scalping":
            score, factors = self._score_scalping(data)
        elif strategy_name == "spike_hunting":
            score, factors = self._score_spike_hunting(data)
        elif strategy_name == "trend_following":
            score, factors = self._score_trend_following(data)
        elif strategy_name == "breakout":
            score, factors = self._score_breakout(data)
        elif strategy_name == "range_trading":
            score, factors = self._score_range_trading(data)
        elif strategy_name == "low_volatility_range":
            score, factors = self._score_low_volatility_range(data)
        elif strategy_name == "high_volatility":
            score, factors = self._score_high_volatility(data)
        else:  # standard
            score, factors = self._score_standard(data)
        
        return score, factors
    
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
        rsi = data["rsi_value"]
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
        spread = data["spread_pct"]
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
        if -0.1 <= data["rsi_momentum"] <= 0.2:
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
        vol_5m = data["volatility_5m"]
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
        
        # S/R: Strong resistance for spike targets (20 points)
        if data["strongest_resistance"] > 0 and len(data["top_resistance"]) > 0:
            score += 20.0
            factors.append("Strong resistance levels identified")
        else:
            score -= 10.0
            factors.append("No strong resistance levels")
        
        # Market condition: Acceptable risk (10 points)
        if data["risk_level"] in ["LOW", "MEDIUM"]:
            score += 10.0
            factors.append(f"{data['risk_level']} risk")
        else:
            score -= 5.0
            factors.append(f"{data['risk_level']} risk")
        
        return max(0.0, score), factors
    
    def _score_trend_following(self, data: Dict[str, Any]) -> tuple:
        """Score trend following - requires strong trend + funding alignment + volume"""
        score = 0.0
        factors = []
        
        # Trend: Strong trend required (30 points)
        if data["trend_direction"] in ["BULLISH", "BEARISH"]:
            score += 20.0
            factors.append(f"{data['trend_direction']} trend")
            # Trend strength bonus
            if data["trend_strength"] > 0.7:
                score += 10.0
                factors.append(f"Strong trend (strength: {data['trend_strength']:.2f})")
            elif data["trend_strength"] > 0.5:
                score += 5.0
                factors.append(f"Moderate trend (strength: {data['trend_strength']:.2f})")
            else:
                score -= 5.0
                factors.append(f"Weak trend (strength: {data['trend_strength']:.2f})")
        else:
            score -= 25.0
            factors.append(f"{data['trend_direction']} trend (no trend)")
        
        # Funding: Alignment with trend (25 points)
        funding_dir = data["funding_direction"]
        if data["trend_direction"] == "BULLISH" and funding_dir == "INCREASING":
            score += 25.0
            factors.append("Funding aligns with bullish trend")
        elif data["trend_direction"] == "BEARISH" and funding_dir == "DECREASING":
            score += 25.0
            factors.append("Funding aligns with bearish trend")
        elif funding_dir == "STABLE":
            score += 10.0
            factors.append("Stable funding")
        else:
            score -= 15.0
            factors.append(f"Funding misaligned ({funding_dir})")
        
        # Volume: High volume confirms trend (20 points)
        vol_cat = data["volume_category"]
        if vol_cat in ["HIGH", "VERY_HIGH", "EXTREME"]:
            score += 20.0
            factors.append(f"{vol_cat} volume confirms trend")
        elif vol_cat == "NORMAL":
            score += 10.0
            factors.append("Normal volume")
        else:
            score -= 10.0
            factors.append(f"{vol_cat} volume (weak)")
        
        # Volatility: Moderate to high (15 points)
        if data["volatility_category"] in ["MODERATE", "HIGH"]:
            score += 15.0
            factors.append(f"{data['volatility_category']} volatility")
        elif data["volatility_category"] == "EXTREME":
            score -= 10.0
            factors.append("Extreme volatility (too risky)")
        else:
            score += 5.0
            factors.append(f"{data['volatility_category']} volatility (low)")
        
        # RSI momentum: Aligned with trend (10 points)
        if (data["trend_direction"] == "BULLISH" and data["rsi_momentum"] > 0) or \
           (data["trend_direction"] == "BEARISH" and data["rsi_momentum"] < 0):
            score += 10.0
            factors.append("RSI momentum aligned")
        else:
            score -= 5.0
            factors.append("RSI momentum misaligned")
        
        return max(0.0, score), factors
    
    def _score_breakout(self, data: Dict[str, Any]) -> tuple:
        """Score breakout - requires S/R proximity + pressure + volatility"""
        score = 0.0
        factors = []
        
        # S/R: Need strong levels near price (30 points)
        price = data["current_price"]
        if price > 0:
            support_dist = abs(price - data["strongest_support"]) / price if data["strongest_support"] > 0 else 1.0
            resistance_dist = abs(data["strongest_resistance"] - price) / price if data["strongest_resistance"] > 0 else 1.0
            min_dist = min(support_dist, resistance_dist)
            
            if min_dist < 0.01:  # Within 1%
                score += 30.0
                factors.append(f"Strong S/R level near price ({min_dist*100:.2f}%)")
            elif min_dist < 0.02:  # Within 2%
                score += 15.0
                factors.append(f"S/R level nearby ({min_dist*100:.2f}%)")
            else:
                score -= 10.0
                factors.append("No nearby S/R levels")
        else:
            score -= 15.0
            factors.append("Price data unavailable")
        
        # Pressure: Strong directional pressure (25 points)
        net_pressure = data["net_pressure"]
        if abs(net_pressure) > 0.3:
            score += 25.0
            factors.append(f"Strong pressure ({net_pressure:+.2f})")
        elif abs(net_pressure) > 0.1:
            score += 10.0
            factors.append(f"Moderate pressure ({net_pressure:+.2f})")
        else:
            score -= 10.0
            factors.append("Weak pressure")
        
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
        """Score range trading - requires S/R levels + sideways trend"""
        score = 0.0
        factors = []
        
        # S/R: Strong levels required (40 points)
        if len(data["top_support"]) >= 2 and len(data["top_resistance"]) >= 2:
            score += 40.0
            factors.append("Strong S/R levels identified")
        elif len(data["top_support"]) >= 1 and len(data["top_resistance"]) >= 1:
            score += 20.0
            factors.append("Some S/R levels")
        else:
            score -= 30.0
            factors.append("No S/R levels (critical)")
        
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
        """Score low volatility range - requires LOW volatility + S/R + sideways"""
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
        
        # S/R: Need levels (20 points)
        if len(data["top_support"]) >= 1 and len(data["top_resistance"]) >= 1:
            score += 20.0
            factors.append("S/R levels identified")
        else:
            score -= 15.0
            factors.append("No S/R levels")
        
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
        elif data["trend_strength"] < 0.5:
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
        """Score standard strategy - fallback for balanced conditions"""
        score = 50.0  # Base score (always available)
        factors = ["Standard fallback strategy"]
        
        # Bonus for balanced conditions
        if data["volatility_category"] == "MODERATE":
            score += 10.0
            factors.append("Moderate volatility")
        
        if data["volume_category"] in ["NORMAL", "HIGH"]:
            score += 10.0
            factors.append(f"{data['volume_category']} volume")
        
        return score, factors
    
    def _calculate_confidence(self, strategy_scores: Dict[str, Dict], best_strategy: str, data: Dict[str, Any]) -> float:
        """Calculate dynamic confidence based on score quality and data completeness"""
        best_score = strategy_scores[best_strategy]["score"]
        
        # Get 2nd best score
        sorted_scores = sorted(strategy_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        second_score = sorted_scores[1][1]["score"] if len(sorted_scores) > 1 else 0.0
        
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
        if data["rsi_value"] is None or data["rsi_value"] <= 0:
            missing_critical.append("rsi")
            data_quality -= 0.05
        
        data_quality = max(0.0, data_quality)
        
        # Total confidence
        total_confidence = score_confidence + gap_confidence + data_quality
        total_confidence = min(0.95, max(0.1, total_confidence))  # Clamp between 0.1 and 0.95
        
        if missing_critical:
            logger.debug(f"⚠️ Missing critical data: {missing_critical} (confidence penalty)")
        
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
        return self.strategy_configs.get(strategy_name, self.strategy_configs["standard"]).copy()
    
    
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
        if hasattr(self, '_last_market_data'):
            volatility_5m = self._last_market_data.get("volatility_5m", 0.0)
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
            self.current_strategy_config = self.strategy_configs.get(new_strategy, self.strategy_configs["standard"])
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
        return descriptions.get(strategy_name, "Unknown strategy")
    
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
            if not hasattr(self, 'pending_strategy_outcomes'):
                self.pending_strategy_outcomes = []
            
            self.pending_strategy_outcomes.append(selection_record)
            
            # Keep only recent records
            if len(self.pending_strategy_outcomes) > 100:
                self.pending_strategy_outcomes = self.pending_strategy_outcomes[-100:]
            
            logger.debug(f"📊 Strategy selection recorded: {strategy} (confidence: {recommendation.confidence:.3f})")
            
        except Exception as e:
            logger.error(f"❌ Strategy selection recording failed: {e}")
    
    def record_strategy_outcome(self, strategy: str, outcome: Dict[str, Any]) -> None:
        """Record the outcome of a strategy for ML learning"""
        try:
            
            # Find the most recent selection for this strategy
            if hasattr(self, 'pending_strategy_outcomes'):
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
            profit = outcome.get("profit", 0.0)
            success = outcome.get("success", profit > 0)
            
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
            from core.session.session_manager import session_manager
            
            # Update session data with new strategy
            if hasattr(session_manager, 'current_session_data') and session_manager.current_session_data:
                session_manager.current_session_data["strategy"] = new_strategy
                
                # Sync updated session data to dashboard
                # Get dashboard service and update
                from core.services.system_initializer import get_system_initializer
                system_initializer = get_system_initializer()
                dashboard_service = system_initializer.singleton_systems.get("dashboard_service")
                if dashboard_service:
                    dashboard_service.update_session_data(session_manager.current_session_data)
                    logger.info(f"🔄 Strategy switched to: {new_strategy}")
                
                logger.info(f"📊 Dashboard notified of strategy change: {new_strategy}")
            
        except Exception as e:
            logger.error(f"❌ Failed to notify session of strategy change: {e}")
    
