#!/usr/bin/env python3
"""
Confidence Calculator - Data-Driven Confidence Calculation
Uses optimized factors and thresholds from historical performance analysis
"""

import time
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger
from core.ml.confidence_optimizer import get_global_confidence_optimizer, TradeRecord, ConfidenceFactor


@dataclass
class ConfidenceCalculation:
    """Result of confidence calculation with detailed breakdown"""
    final_confidence: float
    base_confidence: float
    factor_contributions: Dict[str, float]
    reasoning: List[str]
    optimization_used: bool = False


class ConfidenceCalculator:
    """
    Data-driven confidence calculator that uses optimized factors
    
    Features:
    1. Uses ML-optimized weights and thresholds
    2. Adapts to market conditions
    3. Learns from trade outcomes
    4. Provides detailed reasoning
    """
    
    def __init__(self):
        self.optimizer = get_global_confidence_optimizer()
        self.last_optimization = 0
        self.optimization_interval = 3600  # 1 hour
        
        logger.info("🎯 Confidence Calculator initialized")
    
    def calculate_confidence(self, direction: str, score: float, 
                           market_data: Dict[str, Any]) -> ConfidenceCalculation:
        """
        Calculate confidence using optimized factors and thresholds
        
        Args:
            direction: "LONG" or "SHORT"
            score: Raw prediction score (-1.0 to 1.0)
            market_data: Market data dictionary
            
        Returns:
            ConfidenceCalculation with detailed breakdown
        """
        try:
            # Check if we need to re-optimize
            if self._should_reoptimize():
                self._trigger_optimization()
            
            # Get optimized factors
            factors = self.optimizer.get_optimized_factors()
            
            # Calculate base confidence
            base_confidence = self._calculate_base_confidence(score)
            
            # Apply optimized factors
            factor_contributions = {}
            reasoning = []
            final_confidence = base_confidence
            
            # Process each factor
            for factor_name, factor in factors.items():
                if not factor.is_active:
                    continue
                
                contribution = self._apply_factor(
                    factor, direction, market_data, factor_contributions
                )
                
                if contribution != 0:
                    factor_contributions[factor_name] = contribution
                    final_confidence += contribution
                    
                    # Add reasoning
                    if contribution > 0:
                        reasoning.append(f"✅ {factor_name}: +{contribution:.1%}")
                    else:
                        reasoning.append(f"❌ {factor_name}: {contribution:.1%}")
            
            # Apply bounds
            final_confidence = max(0.10, min(1.0, final_confidence))
            
            # Log calculation
            logger.debug(f"📊 Confidence: {base_confidence:.1%} → {final_confidence:.1%}")
            
            return ConfidenceCalculation(
                final_confidence=final_confidence,
                base_confidence=base_confidence,
                factor_contributions=factor_contributions,
                reasoning=reasoning,
                optimization_used=True
            )
            
        except Exception as e:
            logger.error(f"❌ Confidence calculation failed: {e}")
            # Fallback to simple calculation
            return self._fallback_calculation(direction, score, market_data)
    
    def _calculate_base_confidence(self, score: float) -> float:
        """Calculate base confidence from score using optimized formula"""
        import math
        
        # Optimized sigmoid function
        # Formula: C_base = max(0.20, 0.30 + 0.50 * tanh(2 * |score|))
        base_confidence = max(0.20, 0.30 + 0.50 * math.tanh(2 * abs(score)))
        
        return base_confidence
    
    def _apply_factor(self, factor: ConfidenceFactor, direction: str, 
                     market_data: Dict[str, Any]) -> float:
        """Apply a single factor with optimized parameters"""
        
        # Get factor-specific logic
        if factor.name == "expected_value":
            return self._apply_expected_value_factor(factor, market_data)
        elif factor.name == "rsi_signal":
            return self._apply_rsi_factor(factor, direction, market_data)
        elif factor.name == "volume_confirmation":
            return self._apply_volume_factor(factor, market_data)
        elif factor.name == "pressure_momentum":
            return self._apply_pressure_factor(factor, direction, market_data)
        elif factor.name == "pattern_confirmation":
            return self._apply_pattern_factor(factor, direction, market_data)
        elif factor.name == "trend_alignment":
            return self._apply_trend_factor(factor, direction, market_data)
        elif factor.name == "sr_proximity":
            return self._apply_sr_factor(factor, direction, market_data)
        elif factor.name == "market_quality":
            return self._apply_market_quality_factor(factor, market_data)
        elif factor.name == "sentiment_alignment":
            return self._apply_sentiment_factor(factor, direction, market_data)
        elif factor.name == "funding_alignment":
            return self._apply_funding_factor(factor, direction, market_data)
        elif factor.name == "poc_proximity":
            return self._apply_poc_factor(factor, market_data)
        elif factor.name == "cross_asset_correlation":
            return self._apply_correlation_factor(factor, direction, market_data)
        elif factor.name == "volatility_penalty":
            return self._apply_volatility_penalty(factor, market_data)
        else:
            return 0.0
    
    def _apply_expected_value_factor(self, factor: ConfidenceFactor, market_data: Dict[str, Any]) -> float:
        """Apply expected value factor with optimized thresholds"""
        ev_percent = market_data.get("expected_value", 0.0) or 0.0
        
        if ev_percent > factor.threshold:
            return factor.boost_value
        elif ev_percent < -factor.threshold:
            return factor.penalty_value
        else:
            return 0.0
    
    def _apply_rsi_factor(self, factor: ConfidenceFactor, direction: str, market_data: Dict[str, Any]) -> float:
        """Apply RSI factor with optimized thresholds"""
        rsi = market_data.get("rsi", 50)
        
        if direction == "LONG" and rsi < factor.threshold:
            return factor.boost_value
        elif direction == "SHORT" and rsi > (100 - factor.threshold):
            return factor.boost_value
        else:
            return 0.0
    
    def _apply_volume_factor(self, factor: ConfidenceFactor, market_data: Dict[str, Any]) -> float:
        """Apply enhanced volume confirmation factor with momentum analysis"""
        volume_category = market_data.get("volume_category", "NORMAL")
        volume_momentum = market_data.get("volume_momentum", 0.0)
        volume_trend_strength = market_data.get("volume_trend_strength", 0.0)
        
        # Base volume impact
        base_impact = 0.0
        if volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            base_impact = factor.boost_value
        elif volume_category in ["LOW", "VERY_LOW"]:
            base_impact = factor.penalty_value
        
        # Momentum bonus/penalty
        momentum_bonus = 0.0
        if volume_momentum > 0.2 and volume_trend_strength > 0.5:  # Strong upward momentum
            momentum_bonus = factor.boost_value * 0.5  # 50% bonus
        elif volume_momentum < -0.2 and volume_trend_strength > 0.5:  # Strong downward momentum
            momentum_bonus = factor.penalty_value * 0.5  # 50% penalty
        
        return base_impact + momentum_bonus
    
    def _apply_pressure_factor(self, factor: ConfidenceFactor, direction: str, market_data: Dict[str, Any]) -> float:
        """Apply orderbook pressure factor"""
        pressure = market_data.get("pressure_data", {}).get("direction", "NEUTRAL")
        volume_category = market_data.get("volume_category", "NORMAL")
        
        # Only apply with high volume
        if volume_category not in ["HIGH", "VERY_HIGH", "EXTREME"]:
            return 0.0
        
        if direction == "LONG" and pressure in ["BUY", "STRONG_BUY"]:
            return factor.boost_value
        elif direction == "SHORT" and pressure in ["SELL", "STRONG_SELL"]:
            return factor.boost_value
        elif direction == "LONG" and pressure in ["SELL", "STRONG_SELL"]:
            return factor.penalty_value
        elif direction == "SHORT" and pressure in ["BUY", "STRONG_BUY"]:
            return factor.penalty_value
        else:
            return 0.0
    
    def _apply_pattern_factor(self, factor: ConfidenceFactor, direction: str, market_data: Dict[str, Any]) -> float:
        """Apply pattern confirmation factor"""
        pattern_setup = market_data.get("pattern_analysis", {}).get("market_setup", {}).get("setup", "")
        
        if direction == "LONG" and "BULLISH" in pattern_setup:
            return factor.boost_value
        elif direction == "SHORT" and "BEARISH" in pattern_setup:
            return factor.boost_value
        else:
            return 0.0
    
    def _apply_trend_factor(self, factor: ConfidenceFactor, direction: str, market_data: Dict[str, Any]) -> float:
        """Apply trend alignment factor"""
        market_status = market_data.get("market_conditions_analysis", {}).get("market_status", "NEUTRAL")
        
        if direction == "LONG" and market_status == "BULLISH":
            return factor.boost_value
        elif direction == "SHORT" and market_status == "BEARISH":
            return factor.boost_value
        elif direction == "LONG" and market_status == "BEARISH":
            return factor.penalty_value
        elif direction == "SHORT" and market_status == "BULLISH":
            return factor.penalty_value
        else:
            return 0.0
    
    def _apply_sr_factor(self, factor: ConfidenceFactor, direction: str, market_data: Dict[str, Any]) -> float:
        """Apply support/resistance proximity factor"""
        current_price = market_data.get("current_price", 0)
        support_resistance = market_data.get("support_resistance", {})
        
        if direction == "LONG":
            nearest_support = support_resistance.get("nearest_support", {}).get("price", 0)
            if nearest_support and current_price:
                distance_pct = abs(current_price - nearest_support) / current_price
                if distance_pct < factor.threshold:
                    return factor.boost_value
        elif direction == "SHORT":
            nearest_resistance = support_resistance.get("nearest_resistance", {}).get("price", 0)
            if nearest_resistance and current_price:
                distance_pct = abs(current_price - nearest_resistance) / current_price
                if distance_pct < factor.threshold:
                    return factor.boost_value
        
        return 0.0
    
    def _apply_market_quality_factor(self, factor: ConfidenceFactor, market_data: Dict[str, Any]) -> float:
        """Apply market quality factor"""
        market_quality = market_data.get("market_conditions_analysis", {}).get("market_quality", "UNKNOWN")
        
        if market_quality == "EXCELLENT":
            return factor.boost_value
        elif market_quality == "GOOD":
            return factor.boost_value * 0.5
        elif market_quality == "POOR":
            return factor.penalty_value
        else:
            return 0.0
    
    def _apply_sentiment_factor(self, factor: ConfidenceFactor, direction: str, market_data: Dict[str, Any]) -> float:
        """Apply sentiment alignment factor"""
        sentiment = market_data.get("market_conditions_analysis", {}).get("sentiment", "NEUTRAL")
        
        if direction == "LONG" and sentiment in ["GREED", "EXTREME_GREED"]:
            return factor.boost_value
        elif direction == "SHORT" and sentiment in ["FEAR", "EXTREME_FEAR"]:
            return factor.boost_value
        else:
            return 0.0
    
    def _apply_funding_factor(self, factor: ConfidenceFactor, direction: str, market_data: Dict[str, Any]) -> float:
        """Apply funding rate alignment factor"""
        funding_analysis = market_data.get("funding_analysis", {})
        funding_sentiment = funding_analysis.get("sentiment", "NEUTRAL")
        
        if funding_sentiment != "NEUTRAL":
            if direction == "LONG" and funding_sentiment == "BULLISH":
                return factor.boost_value
            elif direction == "SHORT" and funding_sentiment == "BEARISH":
                return factor.boost_value
        
        return 0.0
    
    
    def _apply_poc_factor(self, factor: ConfidenceFactor, market_data: Dict[str, Any]) -> float:
        """Apply price of control proximity factor"""
        volume_profile = market_data.get("volume_profile_analysis", {})
        poc_distance = volume_profile.get("poc_distance_pct", 0.0) if volume_profile else 0.0
        
        if isinstance(poc_distance, (int, float)) and poc_distance and abs(poc_distance) < factor.threshold:
            return factor.boost_value
        else:
            return 0.0
    
    def _apply_correlation_factor(self, factor: ConfidenceFactor, direction: str, market_data: Dict[str, Any]) -> float:
        """Apply cross-asset correlation factor"""
        cross_asset = market_data.get("cross_asset_analysis", {})
        dxy_corr = cross_asset.get("dxy_correlation", 0)
        
        if isinstance(dxy_corr, (int, float)):
            if direction == "LONG" and dxy_corr < -factor.threshold:
                return factor.boost_value
            elif direction == "SHORT" and dxy_corr > factor.threshold:
                return factor.boost_value
        
        return 0.0
    
    def _apply_volatility_penalty(self, factor: ConfidenceFactor, market_data: Dict[str, Any]) -> float:
        """Apply volatility penalty factor"""
        volatility_category = market_data.get("volatility_category", "MODERATE")
        
        if volatility_category == "EXTREME":
            return factor.penalty_value
        elif volatility_category == "HIGH":
            return factor.penalty_value * 0.5
        else:
            return 0.0
    
    def _should_reoptimize(self) -> bool:
        """Check if we should trigger re-optimization"""
        current_time = time.time()
        return (current_time - self.last_optimization) > self.optimization_interval
    
    def _trigger_optimization(self) -> None:
        """Trigger confidence optimization"""
        try:
            logger.info("🔄 Triggering confidence optimization...")
            self.optimizer.optimize_confidence_calculation()
            self.last_optimization = time.time()
            logger.success("✅ Confidence optimization completed")
        except Exception as e:
            logger.error(f"❌ Confidence optimization failed: {e}")
    
    def _fallback_calculation(self, direction: str, score: float, market_data: Dict[str, Any]) -> ConfidenceCalculation:
        """Fallback confidence calculation when optimization fails"""
        import math
        
        # Simple fallback calculation
        base_confidence = max(0.20, 0.30 + 0.50 * math.tanh(2 * abs(score)))
        
        # Basic factors
        rsi = market_data.get("rsi", 50)
        rsi_boost = 0.0
        if direction == "LONG" and rsi < 30:
            rsi_boost = 0.15
        elif direction == "SHORT" and rsi > 70:
            rsi_boost = 0.15
        
        final_confidence = base_confidence + rsi_boost
        final_confidence = max(0.10, min(1.0, final_confidence))
        
        return ConfidenceCalculation(
            final_confidence=final_confidence,
            base_confidence=base_confidence,
            factor_contributions={"rsi_signal": rsi_boost},
            reasoning=[f"Fallback calculation: RSI {rsi_boost:.1%}"],
            optimization_used=False
        )
    
    def record_trade_outcome(self, trade_record: TradeRecord) -> None:
        """Record trade outcome for future optimization"""
        self.optimizer.add_trade_record(trade_record)
    
    def get_optimal_threshold(self) -> float:
        """Get optimal confidence threshold"""
        return self.optimizer.get_optimal_threshold()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return self.optimizer.get_performance_summary()


# Global calculator instance
_global_confidence_calculator = None

def get_global_confidence_calculator() -> ConfidenceCalculator:
    """Get global confidence calculator singleton"""
    global _global_confidence_calculator
    if _global_confidence_calculator is None:
        _global_confidence_calculator = ConfidenceCalculator()
    return _global_confidence_calculator
