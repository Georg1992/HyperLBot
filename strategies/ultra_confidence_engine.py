#!/usr/bin/env python3
"""
Ultra-High Confidence Engine
Identifies perfect trading setups with up to 98% confidence for maximum position sizing
"""

import numpy as np
import time
from typing import Dict, Any, List, Optional
from loguru import logger

class UltraConfidenceEngine:
    """Detect ultra-high confidence trading opportunities for maximum profitability"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        
        # Ultra-high confidence thresholds
        self.ULTRA_CONFIDENCE_REQUIREMENTS = {
            "min_base_confidence": 0.75,      # Base prediction must be 75%+
            "min_pattern_count": 2,           # At least 2 patterns detected
            "min_volume_spike": 2.5,          # 2.5x volume spike required
            "min_trend_alignment": 0.9,       # 90% trend alignment across timeframes
            "max_volatility_for_ultra": 0.008, # Not too volatile (0.8% max)
            "min_volatility_for_ultra": 0.002, # Not too stable (0.2% min)
            "min_rsi_extreme": 15,            # RSI below 15 or above 85
            "max_rsi_extreme": 85,
            "min_orderbook_imbalance": 0.4,   # 40% orderbook imbalance
            "min_whale_confirmation": 0.7     # 70% whale sentiment alignment
        }
        
        # Perfect setup multipliers
        self.PERFECT_SETUP_MULTIPLIERS = {
            "pattern_multiplier": 1.05,       # +5% per additional pattern
            "volume_multiplier": 1.03,        # +3% per 1x volume above 2.5x
            "trend_multiplier": 1.10,         # +10% for perfect trend alignment
            "rsi_extreme_multiplier": 1.08,   # +8% for extreme RSI
            "whale_multiplier": 1.06,         # +6% for whale confirmation
            "timing_multiplier": 1.04,        # +4% for perfect market timing
            "liquidity_multiplier": 1.02      # +2% for high liquidity
        }
        
        # Maximum theoretical confidence
        self.ABSOLUTE_MAX_CONFIDENCE = 0.98  # 98% maximum (leave 2% for black swans)
        
        logger.info("🔥 Ultra-High Confidence Engine initialized - Max confidence: 98%")
    
    def evaluate_ultra_confidence(self, prediction: Dict[str, Any], market_data: Dict[str, Any], 
                                 current_price: float) -> Dict[str, Any]:
        """Evaluate if a prediction qualifies for ultra-high confidence"""
        
        base_confidence = prediction.get("confidence", 0.0)
        
        # First gate: Base confidence must be high enough
        if base_confidence < self.ULTRA_CONFIDENCE_REQUIREMENTS["min_base_confidence"]:
            return {
                "is_ultra_confident": False,
                "ultra_confidence": base_confidence,
                "reason": f"Base confidence too low: {base_confidence:.1%}",
                "max_position_size": self._calculate_standard_position_size(base_confidence)
            }
        
        # Evaluate all ultra-confidence factors
        ultra_factors = self._evaluate_ultra_factors(prediction, market_data, current_price)
        
        # Calculate ultra confidence score
        ultra_confidence = self._calculate_ultra_confidence(base_confidence, ultra_factors)
        
        # Determine if this qualifies as ultra-high confidence
        is_ultra = ultra_factors["qualifying_factors"] >= 5  # Need at least 5 factors
        
        if is_ultra:
            position_size = self._calculate_ultra_position_size(ultra_confidence, ultra_factors)
            logger.warning(f"🔥 ULTRA-HIGH CONFIDENCE DETECTED: {ultra_confidence:.1%}")
            logger.warning(f"   Qualifying factors: {ultra_factors['qualifying_factors']}/8")
            logger.warning(f"   Suggested position size: {position_size:.1%}")
        else:
            position_size = self._calculate_standard_position_size(base_confidence)
        
        return {
            "is_ultra_confident": is_ultra,
            "ultra_confidence": ultra_confidence,
            "base_confidence": base_confidence,
            "qualifying_factors": ultra_factors["qualifying_factors"],
            "ultra_factors": ultra_factors,
            "max_position_size": position_size,
            "confidence_boost": ultra_confidence - base_confidence,
            "reason": self._generate_ultra_reason(ultra_factors, is_ultra)
        }
    
    def _evaluate_ultra_factors(self, prediction: Dict[str, Any], market_data: Dict[str, Any], 
                               current_price: float) -> Dict[str, Any]:
        """Evaluate all factors that contribute to ultra-high confidence"""
        
        factors = {
            "pattern_score": 0.0,
            "volume_score": 0.0,
            "trend_score": 0.0,
            "rsi_score": 0.0,
            "whale_score": 0.0,
            "timing_score": 0.0,
            "liquidity_score": 0.0,
            "volatility_score": 0.0,
            "qualifying_factors": 0
        }
        
        # 1. PATTERN ANALYSIS SCORE
        patterns = prediction.get("patterns_detected", [])
        if len(patterns) >= self.ULTRA_CONFIDENCE_REQUIREMENTS["min_pattern_count"]:
            factors["pattern_score"] = min(1.0, len(patterns) / 4)  # Max score at 4 patterns
            factors["qualifying_factors"] += 1
            logger.info(f"✅ Pattern factor: {len(patterns)} patterns detected")
        
        # 2. VOLUME SPIKE SCORE  
        volume_data = market_data.get("volume_data", {})
        volume_spike_ratio = volume_data.get("spike_ratio_mean", 1.0)
        if volume_spike_ratio >= self.ULTRA_CONFIDENCE_REQUIREMENTS["min_volume_spike"]:
            factors["volume_score"] = min(1.0, (volume_spike_ratio - 2.5) / 2.5)  # Max at 5x
            factors["qualifying_factors"] += 1
            logger.info(f"✅ Volume factor: {volume_spike_ratio:.1f}x spike")
        
        # 3. TREND ALIGNMENT SCORE
        trend_alignment = self._calculate_trend_alignment(market_data)
        if trend_alignment >= self.ULTRA_CONFIDENCE_REQUIREMENTS["min_trend_alignment"]:
            factors["trend_score"] = trend_alignment
            factors["qualifying_factors"] += 1
            logger.info(f"✅ Trend factor: {trend_alignment:.1%} alignment")
        
        # 4. RSI EXTREME SCORE
        rsi = market_data.get("rsi", 50.0)
        if rsi <= self.ULTRA_CONFIDENCE_REQUIREMENTS["min_rsi_extreme"] or \
           rsi >= self.ULTRA_CONFIDENCE_REQUIREMENTS["max_rsi_extreme"]:
            # Distance from center (50) normalized
            rsi_extremeness = max(abs(rsi - 50) - 35, 0) / 15  # Scale 35-50 to 0-1
            factors["rsi_score"] = min(1.0, rsi_extremeness)
            factors["qualifying_factors"] += 1
            logger.info(f"✅ RSI factor: {rsi:.1f} (extreme)")
        
        # 5. WHALE/ORDERBOOK SCORE
        orderbook_imbalance = market_data.get("orderbook_imbalance", 0)
        if abs(orderbook_imbalance) >= self.ULTRA_CONFIDENCE_REQUIREMENTS["min_orderbook_imbalance"]:
            factors["whale_score"] = min(1.0, abs(orderbook_imbalance) / 0.8)  # Max at 80% imbalance
            factors["qualifying_factors"] += 1
            logger.info(f"✅ Orderbook factor: {orderbook_imbalance:.1%} imbalance")
        
        # 6. MARKET TIMING SCORE (based on hour and market conditions)
        timing_score = self._calculate_timing_score()
        if timing_score > 0.7:
            factors["timing_score"] = timing_score
            factors["qualifying_factors"] += 1
            logger.info(f"✅ Timing factor: {timing_score:.1%}")
        
        # 7. LIQUIDITY SCORE
        total_depth = market_data.get("total_depth", 0)
        if total_depth > 50:  # Good liquidity for BTC
            factors["liquidity_score"] = min(1.0, total_depth / 200)  # Max at 200 BTC depth
            factors["qualifying_factors"] += 1
            logger.info(f"✅ Liquidity factor: {total_depth:.1f} BTC depth")
        
        # 8. VOLATILITY SWEET SPOT SCORE
        volatility = market_data.get("volatility_5m", 0)
        if (self.ULTRA_CONFIDENCE_REQUIREMENTS["min_volatility_for_ultra"] <= 
            volatility <= 
            self.ULTRA_CONFIDENCE_REQUIREMENTS["max_volatility_for_ultra"]):
            # Sweet spot scoring - peak at 0.004 (0.4%)
            optimal_vol = 0.004
            vol_distance = abs(volatility - optimal_vol) / optimal_vol
            factors["volatility_score"] = max(0, 1.0 - vol_distance)
            factors["qualifying_factors"] += 1
            logger.info(f"✅ Volatility factor: {volatility:.3f} (optimal range)")
        
        return factors
    
    def _calculate_ultra_confidence(self, base_confidence: float, ultra_factors: Dict[str, Any]) -> float:
        """Calculate final ultra-high confidence score"""
        
        # Start with base confidence
        ultra_confidence = base_confidence
        
        # Apply multiplicative boosts for each qualifying factor
        multipliers = self.PERFECT_SETUP_MULTIPLIERS
        
        if ultra_factors["pattern_score"] > 0:
            pattern_boost = multipliers["pattern_multiplier"] ** ultra_factors["pattern_score"]
            ultra_confidence *= pattern_boost
        
        if ultra_factors["volume_score"] > 0:
            volume_boost = multipliers["volume_multiplier"] ** ultra_factors["volume_score"]
            ultra_confidence *= volume_boost
        
        if ultra_factors["trend_score"] > 0:
            trend_boost = multipliers["trend_multiplier"] ** ultra_factors["trend_score"]
            ultra_confidence *= trend_boost
        
        if ultra_factors["rsi_score"] > 0:
            rsi_boost = multipliers["rsi_extreme_multiplier"] ** ultra_factors["rsi_score"]
            ultra_confidence *= rsi_boost
        
        if ultra_factors["whale_score"] > 0:
            whale_boost = multipliers["whale_multiplier"] ** ultra_factors["whale_score"]
            ultra_confidence *= whale_boost
        
        if ultra_factors["timing_score"] > 0:
            timing_boost = multipliers["timing_multiplier"] ** ultra_factors["timing_score"]
            ultra_confidence *= timing_boost
        
        if ultra_factors["liquidity_score"] > 0:
            liquidity_boost = multipliers["liquidity_multiplier"] ** ultra_factors["liquidity_score"]
            ultra_confidence *= liquidity_boost
        
        # Volatility sweet spot bonus
        if ultra_factors["volatility_score"] > 0:
            vol_boost = 1 + (ultra_factors["volatility_score"] * 0.05)  # Up to 5% boost
            ultra_confidence *= vol_boost
        
        # Cap at absolute maximum
        return min(self.ABSOLUTE_MAX_CONFIDENCE, ultra_confidence)
    
    def _calculate_trend_alignment(self, market_data: Dict[str, Any]) -> float:
        """Calculate multi-timeframe trend alignment score"""
        
        trend_5m = market_data.get("trend_5m", {}).get("trend", "UNKNOWN")
        trend_1h = market_data.get("trend_1h", {}).get("trend", "UNKNOWN")
        trend_1d = market_data.get("trend_1d", {}).get("trend", "UNKNOWN")
        
        # Count aligned trends
        bullish_trends = sum(1 for trend in [trend_5m, trend_1h, trend_1d] 
                           if trend in ["UP", "STRONG_UP"])
        bearish_trends = sum(1 for trend in [trend_5m, trend_1h, trend_1d] 
                           if trend in ["DOWN", "STRONG_DOWN"])
        
        # Perfect alignment = all 3 timeframes agree
        max_alignment = max(bullish_trends, bearish_trends)
        return max_alignment / 3.0
    
    def _calculate_timing_score(self) -> float:
        """Calculate market timing score based on time of day and market conditions"""
        
        current_hour = time.localtime().tm_hour
        
        # High activity hours (better liquidity and volatility)
        high_activity_hours = [0, 1, 8, 9, 16, 17, 22, 23]  # US/EU/Asia opens/closes
        medium_activity_hours = [2, 7, 10, 15, 18, 21]
        
        if current_hour in high_activity_hours:
            return 0.9
        elif current_hour in medium_activity_hours:
            return 0.7
        else:
            return 0.4  # Lower activity periods
    
    def _calculate_ultra_position_size(self, ultra_confidence: float, ultra_factors: Dict[str, Any]) -> float:
        """Calculate position size for ultra-high confidence trades"""
        
        # Base position size scales with confidence
        if ultra_confidence >= 0.95:       # 95%+ confidence
            base_size = 0.60              # 60% of capital (all-in territory)
        elif ultra_confidence >= 0.90:     # 90-95% confidence  
            base_size = 0.45              # 45% of capital
        elif ultra_confidence >= 0.85:     # 85-90% confidence
            base_size = 0.35              # 35% of capital
        else:
            base_size = 0.25              # 25% of capital
        
        # Multiply by quality factors
        qualifying_factors = ultra_factors["qualifying_factors"]
        
        # Factor multiplier: more factors = higher confidence in position size
        factor_multiplier = 1.0 + (qualifying_factors - 5) * 0.05  # +5% per factor above 5
        
        # Volatility adjustment
        volatility_score = ultra_factors.get("volatility_score", 0)
        vol_multiplier = 1.0 + (volatility_score * 0.1)  # Up to +10% for perfect volatility
        
        final_size = base_size * factor_multiplier * vol_multiplier
        
        # Absolute caps for safety
        return min(0.70, max(0.15, final_size))  # 15% to 70% range
    
    def _calculate_standard_position_size(self, confidence: float) -> float:
        """Calculate standard position size for non-ultra trades"""
        
        if confidence >= 0.80:
            return 0.20  # 20% for high confidence
        elif confidence >= 0.65:
            return 0.15  # 15% for medium-high confidence
        elif confidence >= 0.50:
            return 0.12  # 12% for medium confidence
        else:
            return 0.08  # 8% for lower confidence
    
    def _generate_ultra_reason(self, ultra_factors: Dict[str, Any], is_ultra: bool) -> str:
        """Generate explanation for ultra-confidence decision"""
        
        if not is_ultra:
            return f"Not ultra-confident: Only {ultra_factors['qualifying_factors']}/8 factors met"
        
        qualifying = []
        if ultra_factors["pattern_score"] > 0:
            qualifying.append("Multiple patterns")
        if ultra_factors["volume_score"] > 0:
            qualifying.append("High volume spike")
        if ultra_factors["trend_score"] > 0:
            qualifying.append("Trend alignment")
        if ultra_factors["rsi_score"] > 0:
            qualifying.append("Extreme RSI")
        if ultra_factors["whale_score"] > 0:
            qualifying.append("Orderbook imbalance")
        if ultra_factors["timing_score"] > 0:
            qualifying.append("Optimal timing")
        if ultra_factors["liquidity_score"] > 0:
            qualifying.append("High liquidity")
        if ultra_factors["volatility_score"] > 0:
            qualifying.append("Optimal volatility")
        
        return f"Ultra-confident setup: {', '.join(qualifying)}"
    
    def get_confidence_breakdown(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed breakdown of confidence calculation"""
        
        confidence = prediction.get("confidence", 0)
        ultra_data = prediction.get("ultra_confidence_data", {})
        
        return {
            "base_confidence": prediction.get("confidence", 0),
            "ultra_confidence": ultra_data.get("ultra_confidence", confidence),
            "confidence_boost": ultra_data.get("confidence_boost", 0),
            "qualifying_factors": ultra_data.get("qualifying_factors", 0),
            "is_ultra_setup": ultra_data.get("is_ultra_confident", False),
            "recommended_position": ultra_data.get("max_position_size", 0.10),
            "confidence_tier": self._get_confidence_tier(ultra_data.get("ultra_confidence", confidence))
        }
    
    def _get_confidence_tier(self, confidence: float) -> str:
        """Get confidence tier description"""
        
        if confidence >= 0.95:
            return "🔥 ULTRA-MAX (95%+)"
        elif confidence >= 0.90:
            return "🚀 ULTRA-HIGH (90-95%)"
        elif confidence >= 0.85:
            return "⭐ VERY HIGH (85-90%)"
        elif confidence >= 0.75:
            return "✅ HIGH (75-85%)"
        elif confidence >= 0.65:
            return "📊 MEDIUM-HIGH (65-75%)"
        elif confidence >= 0.50:
            return "⚖️ MEDIUM (50-65%)"
        else:
            return "⚠️ LOW (<50%)"