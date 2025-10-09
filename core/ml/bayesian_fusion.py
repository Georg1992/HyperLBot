#!/usr/bin/env python3
"""
Bayesian Signal Fusion Module
Combines multiple independent signals using Bayes' theorem for probabilistic inference
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import math
from loguru import logger


@dataclass
class Signal:
    """Individual trading signal with probability"""
    name: str
    probability: float  # P(signal | bullish) - likelihood of this signal given bullish outcome
    confidence: float  # How reliable is this signal (0-1)
    evidence: str  # Description of the evidence


@dataclass
class FusedProbability:
    """Result of Bayesian signal fusion"""
    prior_probability: float
    posterior_probability: float
    signals_used: List[str]
    signal_contributions: List[Tuple[str, float]]  # (signal_name, probability_contribution)
    reasoning: str
    confidence: float  # Overall confidence in the fused probability


class BayesianFusion:
    """Combines multiple signals using Bayesian inference"""
    
    def __init__(self, base_rate: float = 0.50):
        """
        Initialize Bayesian Fusion
        
        Args:
            base_rate: Prior probability (base rate) before considering signals
        """
        self.base_rate = base_rate
        logger.info(f"🧮 Bayesian Fusion initialized - Base rate: {base_rate:.1%}")
    
    def fuse_signals(
        self,
        signals: List[Signal],
        direction: str = "LONG"
    ) -> FusedProbability:
        """
        Fuse multiple independent signals using Bayes' theorem
        
        Uses sequential Bayesian updating:
        P(H|E1,E2,...,En) ∝ P(H) × P(E1|H) × P(E2|H) × ... × P(En|H)
        
        Args:
            signals: List of Signal objects
            direction: "LONG" or "SHORT"
            
        Returns:
            FusedProbability with combined probability estimate
        """
        if not signals:
            return FusedProbability(
                prior_probability=self.base_rate,
                posterior_probability=self.base_rate,
                signals_used=[],
                signal_contributions=[],
                reasoning="No signals provided - using base rate",
                confidence=0.0
            )
        
        # Start with prior (base rate)
        prior = self.base_rate
        
        # Sequential Bayesian updating
        # Convert to log-odds for numerical stability
        log_odds_prior = self._probability_to_log_odds(prior)
        log_odds_current = log_odds_prior
        
        signal_contributions = []
        signals_used = []
        reasoning_parts = []
        
        for signal in signals:
            # Apply signal with confidence weighting
            weighted_prob = self._apply_confidence_weighting(signal.probability, signal.confidence)
            
            # Convert signal probability to likelihood ratio
            likelihood_ratio = weighted_prob / (1 - weighted_prob) if weighted_prob < 1.0 else 10.0
            
            # Update log-odds
            log_odds_new = log_odds_current + math.log(likelihood_ratio)
            
            # Calculate contribution of this signal
            prob_before = self._log_odds_to_probability(log_odds_current)
            prob_after = self._log_odds_to_probability(log_odds_new)
            contribution = prob_after - prob_before
            
            signal_contributions.append((signal.name, contribution))
            signals_used.append(signal.name)
            reasoning_parts.append(f"{signal.name}: {signal.evidence} ({contribution:+.1%})")
            
            log_odds_current = log_odds_new
        
        # Convert back to probability
        posterior = self._log_odds_to_probability(log_odds_current)
        
        # Overall confidence is average of signal confidences
        overall_confidence = sum(s.confidence for s in signals) / len(signals) if signals else 0.0
        
        reasoning = f"Prior: {prior:.1%} → Posterior: {posterior:.1%} | " + " | ".join(reasoning_parts)
        
        logger.info(f"🧮 Bayesian Fusion: {prior:.1%} → {posterior:.1%} using {len(signals)} signals")
        
        return FusedProbability(
            prior_probability=prior,
            posterior_probability=posterior,
            signals_used=signals_used,
            signal_contributions=signal_contributions,
            reasoning=reasoning,
            confidence=overall_confidence
        )
    
    def _apply_confidence_weighting(self, probability: float, confidence: float) -> float:
        """
        Apply confidence weighting to a probability
        
        Low confidence → pull probability toward 0.5 (neutral)
        High confidence → keep probability as is
        """
        # Interpolate between 0.5 (no confidence) and probability (full confidence)
        weighted = 0.5 + (probability - 0.5) * confidence
        return max(0.01, min(0.99, weighted))  # Clamp to avoid extreme values
    
    def _probability_to_log_odds(self, probability: float) -> float:
        """Convert probability to log-odds for numerical stability"""
        # Clamp probability to avoid log(0)
        p = max(0.001, min(0.999, probability))
        return math.log(p / (1 - p))
    
    def _log_odds_to_probability(self, log_odds: float) -> float:
        """Convert log-odds back to probability"""
        # Clamp log-odds to prevent overflow
        lo = max(-10, min(10, log_odds))
        odds = math.exp(lo)
        return odds / (1 + odds)
    
    def calculate_signal_from_metric(
        self,
        metric_name: str,
        metric_value: Any,
        metric_type: str,
        direction: str = "LONG"
    ) -> Optional[Signal]:
        """
        Convert a market metric into a Bayesian signal
        
        Args:
            metric_name: Name of the metric (e.g., "RSI", "Volume")
            metric_value: Current value of the metric
            metric_type: Type of metric for interpretation
            direction: Trade direction
            
        Returns:
            Signal object or None if metric not applicable
        """
        try:
            if metric_type == "RSI":
                return self._rsi_to_signal(metric_name, metric_value, direction)
            elif metric_type == "VOLUME":
                return self._volume_to_signal(metric_name, metric_value, direction)
            elif metric_type == "TREND":
                return self._trend_to_signal(metric_name, metric_value, direction)
            elif metric_type == "PATTERN":
                return self._pattern_to_signal(metric_name, metric_value, direction)
            elif metric_type == "SUPPORT_RESISTANCE":
                return self._sr_to_signal(metric_name, metric_value, direction)
            else:
                return None
        except Exception as e:
            logger.warning(f"⚠️ Failed to convert {metric_name} to signal: {e}")
            return None
    
    def _rsi_to_signal(self, name: str, rsi: float, direction: str) -> Optional[Signal]:
        """Convert RSI to a Bayesian signal"""
        if direction == "LONG":
            if rsi < 30:
                # Oversold - strong bullish signal
                probability = 0.75
                confidence = 0.85
                evidence = f"RSI {rsi:.0f} oversold"
            elif rsi < 40:
                # Approaching oversold
                probability = 0.65
                confidence = 0.70
                evidence = f"RSI {rsi:.0f} below 40"
            elif rsi > 70:
                # Overbought - bearish for LONG
                probability = 0.35
                confidence = 0.70
                evidence = f"RSI {rsi:.0f} overbought"
            else:
                # Neutral
                probability = 0.50
                confidence = 0.40
                evidence = f"RSI {rsi:.0f} neutral"
        else:  # SHORT
            if rsi > 70:
                # Overbought - strong bearish signal
                probability = 0.75
                confidence = 0.85
                evidence = f"RSI {rsi:.0f} overbought"
            elif rsi > 60:
                # Approaching overbought
                probability = 0.65
                confidence = 0.70
                evidence = f"RSI {rsi:.0f} above 60"
            elif rsi < 30:
                # Oversold - bullish, bad for SHORT
                probability = 0.35
                confidence = 0.70
                evidence = f"RSI {rsi:.0f} oversold"
            else:
                # Neutral
                probability = 0.50
                confidence = 0.40
                evidence = f"RSI {rsi:.0f} neutral"
        
        return Signal(
            name=name,
            probability=probability,
            confidence=confidence,
            evidence=evidence
        )
    
    def _volume_to_signal(self, name: str, volume_category: str, direction: str) -> Optional[Signal]:
        """Convert volume to a Bayesian signal"""
        volume_map = {
            "EXTREME": (0.70, 0.90, "extreme volume"),
            "VERY_HIGH": (0.65, 0.85, "very high volume"),
            "HIGH": (0.60, 0.75, "high volume"),
            "MODERATE": (0.55, 0.60, "moderate volume"),
            "LOW": (0.45, 0.50, "low volume"),
            "VERY_LOW": (0.40, 0.40, "very low volume"),
        }
        
        if volume_category in volume_map:
            prob, conf, desc = volume_map[volume_category]
            return Signal(
                name=name,
                probability=prob,
                confidence=conf,
                evidence=desc
            )
        
        return None
    
    def _trend_to_signal(self, name: str, trend: str, direction: str) -> Optional[Signal]:
        """Convert trend to a Bayesian signal"""
        if direction == "LONG":
            trend_map = {
                "STRONG_UPTREND": (0.80, 0.90),
                "UPTREND": (0.70, 0.80),
                "WEAK_UPTREND": (0.60, 0.65),
                "SIDEWAYS": (0.50, 0.50),
                "WEAK_DOWNTREND": (0.40, 0.65),
                "DOWNTREND": (0.30, 0.80),
                "STRONG_DOWNTREND": (0.20, 0.90),
            }
        else:  # SHORT
            trend_map = {
                "STRONG_DOWNTREND": (0.80, 0.90),
                "DOWNTREND": (0.70, 0.80),
                "WEAK_DOWNTREND": (0.60, 0.65),
                "SIDEWAYS": (0.50, 0.50),
                "WEAK_UPTREND": (0.40, 0.65),
                "UPTREND": (0.30, 0.80),
                "STRONG_UPTREND": (0.20, 0.90),
            }
        
        if trend in trend_map:
            prob, conf = trend_map[trend]
            return Signal(
                name=name,
                probability=prob,
                confidence=conf,
                evidence=f"Trend: {trend}"
            )
        
        return None
    
    def _pattern_to_signal(self, name: str, pattern_data: Dict[str, Any], direction: str) -> Optional[Signal]:
        """Convert pattern to a Bayesian signal"""
        pattern_direction = pattern_data.get("direction", "NEUTRAL")
        pattern_confidence = pattern_data.get("confidence", 0.5)
        pattern_name = pattern_data.get("pattern", "UNKNOWN")
        
        # Check if pattern direction aligns with trade direction
        if (direction == "LONG" and pattern_direction == "BULLISH") or \
           (direction == "SHORT" and pattern_direction == "BEARISH"):
            # Aligned
            probability = 0.5 + (pattern_confidence * 0.3)  # 0.5 to 0.8
            confidence = pattern_confidence
            evidence = f"{pattern_name} {pattern_direction}"
        elif pattern_direction == "NEUTRAL":
            # Neutral pattern
            probability = 0.50
            confidence = 0.40
            evidence = f"{pattern_name} neutral"
        else:
            # Opposing
            probability = 0.5 - (pattern_confidence * 0.2)  # 0.3 to 0.5
            confidence = pattern_confidence * 0.7
            evidence = f"{pattern_name} {pattern_direction} (opposing)"
        
        return Signal(
            name=name,
            probability=probability,
            confidence=confidence,
            evidence=evidence
        )
    
    def _sr_to_signal(self, name: str, sr_data: Dict[str, Any], direction: str) -> Optional[Signal]:
        """Convert support/resistance proximity to a Bayesian signal"""
        position_in_range = sr_data.get("position_in_range", 0.5)
        
        if direction == "LONG":
            # Near support (0-0.3) = bullish
            # Near resistance (0.7-1.0) = bearish
            if position_in_range < 0.15:
                probability = 0.75
                confidence = 0.85
                evidence = "Very near support"
            elif position_in_range < 0.30:
                probability = 0.65
                confidence = 0.75
                evidence = "Approaching support"
            elif position_in_range > 0.85:
                probability = 0.30
                confidence = 0.80
                evidence = "Very near resistance"
            elif position_in_range > 0.70:
                probability = 0.40
                confidence = 0.70
                evidence = "Approaching resistance"
            else:
                probability = 0.50
                confidence = 0.50
                evidence = "Mid-range"
        else:  # SHORT
            # Near resistance = bearish (good for SHORT)
            if position_in_range > 0.85:
                probability = 0.75
                confidence = 0.85
                evidence = "Very near resistance"
            elif position_in_range > 0.70:
                probability = 0.65
                confidence = 0.75
                evidence = "Approaching resistance"
            elif position_in_range < 0.15:
                probability = 0.30
                confidence = 0.80
                evidence = "Very near support"
            elif position_in_range < 0.30:
                probability = 0.40
                confidence = 0.70
                evidence = "Approaching support"
            else:
                probability = 0.50
                confidence = 0.50
                evidence = "Mid-range"
        
        return Signal(
            name=name,
            probability=probability,
            confidence=confidence,
            evidence=evidence
        )


# Global singleton instance
_global_bayesian_fusion = None


def get_global_bayesian_fusion() -> BayesianFusion:
    """Get the global BayesianFusion singleton instance"""
    global _global_bayesian_fusion
    if _global_bayesian_fusion is None:
        _global_bayesian_fusion = BayesianFusion()
    return _global_bayesian_fusion

