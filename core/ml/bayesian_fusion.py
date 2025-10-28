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
        
        Low confidence → reduce the signal strength but don't pull to 0.5
        High confidence → keep probability as is
        """
        # FIXED: Don't pull toward 0.5, instead scale the deviation from 0.5
        # This preserves the signal direction while reducing its strength based on confidence
        if probability == 0.5:
            return 0.5  # Neutral stays neutral
        
        # Calculate how far from neutral (0.5) the signal is
        deviation = probability - 0.5
        
        # Scale the deviation by confidence, but don't pull toward 0.5
        # Low confidence reduces signal strength, high confidence preserves it
        scaled_deviation = deviation * confidence
        
        # Apply the scaled deviation
        weighted = 0.5 + scaled_deviation
        
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
            elif metric_type == "VOLATILITY":
                return self._volatility_to_signal(metric_name, metric_value, direction)
            elif metric_type == "PRESSURE":
                return self._pressure_to_signal(metric_name, metric_value, direction)
            elif metric_type == "VOLUME_PROFILE":
                return self._volume_profile_to_signal(metric_name, metric_value, direction)
            elif metric_type == "FUNDING_RATE":
                return self._funding_rate_to_signal(metric_name, metric_value, direction)
            elif metric_type == "CROSS_ASSET":
                return self._cross_asset_to_signal(metric_name, metric_value, direction)
            elif metric_type == "MARKET_CONDITIONS":
                return self._market_conditions_to_signal(metric_name, metric_value, direction)
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
                # Neutral - return None to exclude from Bayesian fusion
                # Neutral signals don't provide useful information for trading decisions
                return None
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
                # Neutral - return None to exclude from Bayesian fusion
                # Neutral signals don't provide useful information for trading decisions
                return None
        
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
        """Convert trend to a Bayesian signal - conservative for limit orders"""
        
        # Determine timeframe from signal name
        is_5m_trend = name == "Trend_5m"  # Exact match to avoid substring issues
        is_short_term = "15m" in name
        is_medium_term = "1h" in name or "4h" in name
        is_long_term = "24h" in name
        
        # EXCLUDE 5-minute trends - too noisy for limit orders
        # But allow 15m trends with reduced weight
        if is_5m_trend:
            return None
        
        # For limit orders, we want to be much more conservative with trend signals
        # Short-term trends should have minimal impact, medium-term trends moderate impact
        
        if direction == "LONG":
            if is_short_term:
                # Short-term trends: very conservative for limit orders
                trend_map = {
                    "STRONG_UPTREND": (0.55, 0.60),  # Reduced from 0.80
                    "UPTREND": (0.52, 0.55),         # Reduced from 0.70
                    "WEAK_UPTREND": (0.51, 0.50),    # Reduced from 0.60
                    "SIDEWAYS": None,                # Exclude
                    "WEAK_DOWNTREND": (0.49, 0.50),  # Much less bearish
                    "DOWNTREND": (0.47, 0.55),        # Much less bearish
                    "STRONG_DOWNTREND": (0.45, 0.60), # Much less bearish
                }
            elif is_medium_term:
                # Medium-term trends: moderate impact
                trend_map = {
                    "STRONG_UPTREND": (0.65, 0.70),  # Reduced from 0.80
                    "UPTREND": (0.60, 0.65),         # Reduced from 0.70
                    "WEAK_UPTREND": (0.55, 0.55),    # Reduced from 0.60
                    "SIDEWAYS": None,                # Exclude
                    "WEAK_DOWNTREND": (0.45, 0.60),  # Less bearish
                    "DOWNTREND": (0.40, 0.65),       # Less bearish
                    "STRONG_DOWNTREND": (0.35, 0.70), # Less bearish
                }
            elif is_long_term:
                # Long-term trends: higher impact for limit orders
                trend_map = {
                    "STRONG_UPTREND": (0.70, 0.75),  # Higher confidence for long-term
                    "UPTREND": (0.65, 0.70),         # Higher confidence for long-term
                    "WEAK_UPTREND": (0.58, 0.60),    # Higher confidence for long-term
                    "SIDEWAYS": None,                # Exclude
                    "WEAK_DOWNTREND": (0.42, 0.60),  # Less bearish
                    "DOWNTREND": (0.35, 0.70),       # Less bearish
                    "STRONG_DOWNTREND": (0.30, 0.75), # Less bearish
                }
            else:
                # Default (shouldn't happen with proper naming)
                trend_map = {
                    "STRONG_UPTREND": (0.60, 0.65),
                    "UPTREND": (0.55, 0.60),
                    "WEAK_UPTREND": (0.52, 0.55),
                    "SIDEWAYS": None,
                    "WEAK_DOWNTREND": (0.48, 0.55),
                    "DOWNTREND": (0.45, 0.60),
                    "STRONG_DOWNTREND": (0.40, 0.65),
                }
        else:  # SHORT
            if is_short_term:
                # Short-term trends: very conservative for limit orders
                trend_map = {
                    "STRONG_DOWNTREND": (0.55, 0.60),  # Reduced from 0.80
                    "DOWNTREND": (0.52, 0.55),         # Reduced from 0.70
                    "WEAK_DOWNTREND": (0.51, 0.50),    # Reduced from 0.60
                    "SIDEWAYS": None,                 # Exclude
                    "WEAK_UPTREND": (0.49, 0.50),     # Much less bearish
                    "UPTREND": (0.47, 0.55),          # Much less bearish
                    "STRONG_UPTREND": (0.45, 0.60),   # Much less bearish
                }
            elif is_medium_term:
                # Medium-term trends: moderate impact
                trend_map = {
                    "STRONG_DOWNTREND": (0.65, 0.70),  # Reduced from 0.80
                    "DOWNTREND": (0.60, 0.65),         # Reduced from 0.70
                    "WEAK_DOWNTREND": (0.55, 0.55),    # Reduced from 0.60
                    "SIDEWAYS": None,                 # Exclude
                    "WEAK_UPTREND": (0.45, 0.60),     # Less bearish
                    "UPTREND": (0.40, 0.65),           # Less bearish
                    "STRONG_UPTREND": (0.35, 0.70),   # Less bearish
                }
            elif is_long_term:
                # Long-term trends: higher impact for limit orders
                trend_map = {
                    "STRONG_DOWNTREND": (0.70, 0.75),  # Higher confidence for long-term
                    "DOWNTREND": (0.65, 0.70),         # Higher confidence for long-term
                    "WEAK_DOWNTREND": (0.58, 0.60),    # Higher confidence for long-term
                    "SIDEWAYS": None,                 # Exclude
                    "WEAK_UPTREND": (0.42, 0.60),     # Less bearish
                    "UPTREND": (0.35, 0.70),           # Less bearish
                    "STRONG_UPTREND": (0.30, 0.75),   # Less bearish
                }
            else:
                # Default (shouldn't happen with proper naming)
                trend_map = {
                    "STRONG_DOWNTREND": (0.60, 0.65),
                    "DOWNTREND": (0.55, 0.60),
                    "WEAK_DOWNTREND": (0.52, 0.55),
                    "SIDEWAYS": None,
                    "WEAK_UPTREND": (0.48, 0.55),
                    "UPTREND": (0.45, 0.60),
                    "STRONG_UPTREND": (0.40, 0.65),
                }
        
        if trend in trend_map:
            prob_conf = trend_map[trend]
            
            # Exclude SIDEWAYS trends
            if prob_conf is None:
                return None
                
            prob, conf = prob_conf
            return Signal(
                name=name,
                probability=prob,
                confidence=conf,
                evidence=f"Trend: {trend} ({'24h' if '24h' in name else '4h' if '4h' in name else '1h' if '1h' in name else '15m' if '15m' in name else 'unknown'})"
            )
        
        return None
    
    def _pattern_to_signal(self, name: str, pattern_data: Dict[str, Any], direction: str) -> Optional[Signal]:
        """Convert pattern to a Bayesian signal"""
        try:
            # Handle actual pattern data structure
            patterns = pattern_data.get("patterns", {})
            market_setup = pattern_data.get("market_setup", {})
            overall_confidence = pattern_data.get("overall_confidence", 0.5)
            
            # Check market setup first
            setup = market_setup.get("setup", "NEUTRAL")
            setup_strength = market_setup.get("strength", "MODERATE")
            
            if setup == "NEUTRAL":
                # Provide neutral signal with low confidence
                return Signal(
                    name=name,
                    probability=0.50,
                    confidence=0.25,
                    evidence="Pattern: Neutral setup"
                )
            
            # Determine pattern direction from setup
            if setup in ["BULLISH_SETUP", "BULLISH"]:
                pattern_direction = "BULLISH"
            elif setup in ["BEARISH_SETUP", "BEARISH"]:
                pattern_direction = "BEARISH"
            else:
                return None
            
            # Check if pattern direction aligns with trade direction
            if (direction == "LONG" and pattern_direction == "BULLISH") or \
               (direction == "SHORT" and pattern_direction == "BEARISH"):
                # Aligned
                probability = 0.5 + (overall_confidence * 0.3)  # 0.5 to 0.8
                confidence = overall_confidence
                evidence = f"Pattern {setup} ({setup_strength})"
            else:
                # Opposing
                probability = 0.5 - (overall_confidence * 0.2)  # 0.3 to 0.5
                confidence = overall_confidence * 0.7
                evidence = f"Pattern {setup} (opposing)"
            
            return Signal(
                name=name,
                probability=probability,
                confidence=confidence,
                evidence=evidence
            )
        except Exception as e:
            logger.debug(f"⚠️ Pattern signal conversion failed: {e}")
            return None
    
    def _sr_to_signal(self, name: str, sr_data: Dict[str, Any], direction: str) -> Optional[Signal]:
        """Convert support/resistance proximity to a Bayesian signal"""
        try:
            # Handle actual S/R data structure
            strongest_support = sr_data.get("strongest_support")
            strongest_resistance = sr_data.get("strongest_resistance")
            current_price = sr_data.get("current_price")
            
            if not all([strongest_support, strongest_resistance, current_price]):
                return None
            
            # Calculate position in range
            range_size = strongest_resistance - strongest_support
            if range_size <= 0:
                return None
            
            position_in_range = (current_price - strongest_support) / range_size
            
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
                    # Mid-range - provide neutral signal with low confidence
                    probability = 0.50
                    confidence = 0.30
                    evidence = "Mid-range between S/R levels"
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
                    # Mid-range - provide neutral signal with low confidence
                    probability = 0.50
                    confidence = 0.30
                    evidence = "Mid-range between S/R levels"
            
            return Signal(
                name=name,
                probability=probability,
                confidence=confidence,
                evidence=evidence
            )
        except Exception as e:
            logger.debug(f"⚠️ S/R signal conversion failed: {e}")
            return None
    
    def _volatility_to_signal(self, name: str, volatility_category: str, direction: str) -> Optional[Signal]:
        """Convert volatility category to a Bayesian signal"""
        volatility_map = {
            "LOW": (0.60, 0.70, "low volatility"),
            "MODERATE": (0.50, 0.50, "moderate volatility"),
            "HIGH": (0.40, 0.60, "high volatility"),
            "EXTREME": (0.30, 0.50, "extreme volatility")
        }
        
        if volatility_category in volatility_map:
            prob, conf, evidence = volatility_map[volatility_category]
            return Signal(
                name=name,
                probability=prob,
                confidence=conf,
                evidence=evidence
            )
        return None
    
    def _pressure_to_signal(self, name: str, pressure_data: dict, direction: str) -> Optional[Signal]:
        """Convert pressure data to a Bayesian signal"""
        if not pressure_data or "direction" not in pressure_data:
            return None
        
        pressure_direction = pressure_data.get("direction", "NEUTRAL")
        confidence = pressure_data.get("confidence", 0.0)
        
        if pressure_direction == "NEUTRAL":
            return None
        
        if direction == "LONG":
            if pressure_direction == "BULLISH":
                probability = 0.65 + (confidence * 0.2)  # 0.65 to 0.85
            else:  # BEARISH
                probability = 0.35 - (confidence * 0.2)  # 0.15 to 0.35
        else:  # SHORT
            if pressure_direction == "BEARISH":
                probability = 0.65 + (confidence * 0.2)  # 0.65 to 0.85
            else:  # BULLISH
                probability = 0.35 - (confidence * 0.2)  # 0.15 to 0.35
        
        return Signal(
            name=name,
            probability=probability,
            confidence=confidence,
            evidence=f"Pressure: {pressure_direction}"
        )
    
    def _volume_profile_to_signal(self, name: str, volume_profile_data: dict, direction: str) -> Optional[Signal]:
        """Convert volume profile data to a Bayesian signal"""
        try:
            if not volume_profile_data:
                return None
            
            # Handle actual volume profile data structure
            trade_flow = volume_profile_data.get("trade_flow_analysis", {})
            flow_direction = trade_flow.get("direction", "NEUTRAL")
            flow_strength = trade_flow.get("strength", 0.0)
            
            # Include neutral signals with very low confidence
            if flow_direction == "NEUTRAL":
                # Provide neutral signal with low confidence
                return Signal(
                    name=name,
                    probability=0.50,
                    confidence=0.20,
                    evidence="Volume Profile: Neutral flow"
                )
            
            if flow_strength < 0.3:
                # Provide weak signal with low confidence
                confidence = flow_strength * 0.5  # Scale down confidence
                return Signal(
                    name=name,
                    probability=0.50,
                    confidence=confidence,
                    evidence=f"Weak volume flow: {flow_direction}"
                )
            
            # Determine signal direction
            if flow_direction in ["BULLISH", "BUY"]:
                signal = "BULLISH"
            elif flow_direction in ["BEARISH", "SELL"]:
                signal = "BEARISH"
            else:
                return None
            
            confidence = min(0.8, flow_strength)  # Cap confidence at 0.8
            
            if direction == "LONG":
                if signal == "BULLISH":
                    probability = 0.60 + (confidence * 0.3)  # 0.60 to 0.90
                else:  # BEARISH
                    probability = 0.40 - (confidence * 0.3)  # 0.10 to 0.40
            else:  # SHORT
                if signal == "BEARISH":
                    probability = 0.60 + (confidence * 0.3)  # 0.60 to 0.90
                else:  # BULLISH
                    probability = 0.40 - (confidence * 0.3)  # 0.10 to 0.40
            
            return Signal(
                name=name,
                probability=probability,
                confidence=confidence,
                evidence=f"Volume Profile: {signal}"
            )
        except Exception as e:
            logger.debug(f"⚠️ Volume Profile signal conversion failed: {e}")
            return None
    
    def _funding_rate_to_signal(self, name: str, funding_data: dict, direction: str) -> Optional[Signal]:
        """Convert funding rate data to a Bayesian signal"""
        try:
            if not funding_data:
                return None
            
            # Handle actual funding rate data structure
            rate = funding_data.get("current_funding_rate", 0.0)
            confidence = 0.60  # Moderate confidence for funding rate
            
            if direction == "LONG":
                if rate < -0.01:  # Negative funding (bullish for longs)
                    probability = 0.65
                    evidence = f"Negative funding rate: {rate:.4f}"
                elif rate > 0.01:  # Positive funding (bearish for longs)
                    probability = 0.35
                    evidence = f"Positive funding rate: {rate:.4f}"
                else:
                    return None  # Neutral funding
            else:  # SHORT
                if rate > 0.01:  # Positive funding (bullish for shorts)
                    probability = 0.65
                    evidence = f"Positive funding rate: {rate:.4f}"
                elif rate < -0.01:  # Negative funding (bearish for shorts)
                    probability = 0.35
                    evidence = f"Negative funding rate: {rate:.4f}"
                else:
                    return None  # Neutral funding
            
            return Signal(
                name=name,
                probability=probability,
                confidence=confidence,
                evidence=evidence
            )
        except Exception as e:
            logger.debug(f"⚠️ Funding rate signal conversion failed: {e}")
            return None
    
    def _cross_asset_to_signal(self, name: str, cross_asset_data: dict, direction: str) -> Optional[Signal]:
        """Convert cross-asset correlation data to a Bayesian signal"""
        try:
            if not cross_asset_data:
                return None
            
            # Handle actual cross-asset data structure
            market_regime = cross_asset_data.get("market_regime", {})
            regime = market_regime.get("regime", "NEUTRAL")
            regime_confidence = market_regime.get("confidence", 0.5)
            
            if regime == "NEUTRAL":
                return None
            
            # Determine signal direction from regime
            if regime in ["BULLISH", "RISK_ON"]:
                signal_direction = "BULLISH"
            elif regime in ["BEARISH", "RISK_OFF"]:
                signal_direction = "BEARISH"
            else:
                return None
            
            confidence = regime_confidence
            
            if direction == "LONG":
                if signal_direction == "BULLISH":
                    probability = 0.60 + (confidence * 0.2)  # 0.60 to 0.80
                    evidence = f"Cross-asset regime: {regime}"
                else:  # BEARISH
                    probability = 0.40 - (confidence * 0.2)  # 0.20 to 0.40
                    evidence = f"Cross-asset regime: {regime} (opposing)"
            else:  # SHORT
                if signal_direction == "BEARISH":
                    probability = 0.60 + (confidence * 0.2)  # 0.60 to 0.80
                    evidence = f"Cross-asset regime: {regime}"
                else:  # BULLISH
                    probability = 0.40 - (confidence * 0.2)  # 0.20 to 0.40
                    evidence = f"Cross-asset regime: {regime} (opposing)"
            
            return Signal(
                name=name,
                probability=probability,
                confidence=confidence,
                evidence=evidence
            )
        except Exception as e:
            logger.debug(f"⚠️ Cross-asset signal conversion failed: {e}")
            return None
    
    def _market_conditions_to_signal(self, name: str, market_conditions_data: dict, direction: str) -> Optional[Signal]:
        """Convert market conditions data to a Bayesian signal - VERY CONSERVATIVE"""
        try:
            if not market_conditions_data:
                return None
            
            # Handle actual market conditions data structure
            condition = market_conditions_data.get("condition", "NEUTRAL")
            confidence = market_conditions_data.get("confidence", 0.7)
            
            if condition == "NEUTRAL":
                return None
            
            # Use VERY conservative probabilities for market conditions (supporting signal only)
            if direction == "LONG":
                if condition == "GOOD":
                    probability = 0.52 + (confidence * 0.03)  # 0.52 to 0.55 (very conservative)
                    evidence = f"Good market conditions (supporting)"
                elif condition == "POOR":
                    probability = 0.48 - (confidence * 0.03)  # 0.45 to 0.48 (very conservative)
                    evidence = f"Poor market conditions (supporting)"
                else:
                    return None
            else:  # SHORT
                if condition == "POOR":
                    probability = 0.52 + (confidence * 0.03)  # 0.52 to 0.55 (very conservative)
                    evidence = f"Poor market conditions (supporting)"
                elif condition == "GOOD":
                    probability = 0.48 - (confidence * 0.03)  # 0.45 to 0.48 (very conservative)
                    evidence = f"Good market conditions (supporting)"
                else:
                    return None
            
            return Signal(
                name=name,
                probability=probability,
                confidence=min(0.4, confidence * 0.5),  # Cap confidence at 40% and reduce by 50%
                evidence=evidence
            )
        except Exception as e:
            logger.debug(f"⚠️ Market conditions signal conversion failed: {e}")
            return None


# Global singleton instance
_global_bayesian_fusion = None


def get_global_bayesian_fusion() -> BayesianFusion:
    """Get the global BayesianFusion singleton instance"""
    global _global_bayesian_fusion
    if _global_bayesian_fusion is None:
        _global_bayesian_fusion = BayesianFusion()
    return _global_bayesian_fusion

