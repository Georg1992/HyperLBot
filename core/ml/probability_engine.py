#!/usr/bin/env python3
"""
Advanced Probability Engine
Implements proper probability theory for trading predictions
"""

import numpy as np
from scipy import stats
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class ProbabilityDistribution:
    """Probability distribution for signal confidence"""
    mean: float
    std: float
    distribution_type: str  # 'normal', 'beta', 'gamma'
    confidence_interval: Tuple[float, float]


class ProbabilityEngine:
    """
    Advanced probability engine using statistical theory
    """
    
    def __init__(self):
        self.signal_histories: Dict[str, List[float]] = {}
        self.win_rate_models: Dict[str, Any] = {}
        
        logger.info("📊 Advanced Probability Engine initialized")
    
    def calculate_bayesian_confidence(self, signals: Dict[str, Any], 
                                   market_data: Dict[str, Any]) -> float:
        """
        Calculate confidence using Bayesian inference
        """
        try:
            # Prior probability (base win rate)
            prior = self._get_prior_probability(signals, market_data)
            
            # Likelihood from current signals
            likelihood = self._calculate_likelihood(signals, market_data)
            
            # Evidence (normalization factor)
            evidence = self._calculate_evidence(signals, market_data)
            
            # Bayesian update: P(H|E) = P(E|H) * P(H) / P(E)
            posterior = (likelihood * prior) / evidence if evidence > 0 else prior
            
            # Apply confidence bounds
            posterior = max(0.1, min(0.95, posterior))
            
            logger.debug(f"🧠 Bayesian confidence: prior={prior:.3f}, "
                        f"likelihood={likelihood:.3f}, evidence={evidence:.3f}, "
                        f"posterior={posterior:.3f}")
            
            return posterior
            
        except Exception as e:
            logger.error(f"❌ Bayesian confidence calculation failed: {e}")
            return 0.5
    
    def calculate_beta_distribution_confidence(self, signal_name: str, 
                                            successes: int, trials: int) -> float:
        """
        Calculate confidence using Beta distribution for win rates
        """
        try:
            if trials == 0:
                return 0.5
            
            # Beta distribution parameters
            alpha = successes + 1  # Prior: Beta(1,1) = Uniform
            beta = trials - successes + 1
            
            # Calculate expected value (mean of Beta distribution)
            expected_win_rate = alpha / (alpha + beta)
            
            # Calculate confidence interval
            confidence_interval = stats.beta.interval(0.95, alpha, beta)
            
            logger.debug(f"📈 Beta distribution for {signal_name}: "
                        f"α={alpha}, β={beta}, E[win_rate]={expected_win_rate:.3f}, "
                        f"CI={confidence_interval}")
            
            return expected_win_rate
            
        except Exception as e:
            logger.error(f"❌ Beta distribution calculation failed: {e}")
            return 0.5
    
    def calculate_monte_carlo_confidence(self, signals: Dict[str, Any], 
                                       market_data: Dict[str, Any], 
                                       n_simulations: int = 10000) -> float:
        """
        Calculate confidence using Monte Carlo simulation
        """
        try:
            # Extract signal strengths and weights
            signal_strengths = []
            signal_weights = []
            
            for signal_name, signal_data in signals.items():
                if isinstance(signal_data, dict):
                    strength = signal_data.get("confidence", 0.5)
                    weight = signal_data.get("weight", 0.1)
                    signal_strengths.append(strength)
                    signal_weights.append(weight)
            
            if not signal_strengths:
                return 0.5
            
            # Normalize weights
            total_weight = sum(signal_weights)
            if total_weight > 0:
                signal_weights = [w / total_weight for w in signal_weights]
            
            # Monte Carlo simulation
            wins = 0
            for _ in range(n_simulations):
                # Sample from each signal's distribution
                combined_strength = 0
                for strength, weight in zip(signal_strengths, signal_weights):
                    # Add noise to simulate uncertainty
                    noise = np.random.normal(0, 0.1)
                    sampled_strength = max(0, min(1, strength + noise))
                    combined_strength += sampled_strength * weight
                
                # Determine if this simulation would win
                if combined_strength > 0.5:  # Threshold for win
                    wins += 1
            
            # Calculate win probability
            win_probability = wins / n_simulations
            
            logger.debug(f"🎲 Monte Carlo simulation: {wins}/{n_simulations} wins, "
                        f"probability={win_probability:.3f}")
            
            return win_probability
            
        except Exception as e:
            logger.error(f"❌ Monte Carlo simulation failed: {e}")
            return 0.5
    
    def calculate_ensemble_confidence(self, signals: Dict[str, Any], 
                                   market_data: Dict[str, Any]) -> float:
        """
        Calculate confidence using ensemble of probability methods
        """
        try:
            # Get confidence from different methods
            bayesian_conf = self.calculate_bayesian_confidence(signals, market_data)
            monte_carlo_conf = self.calculate_monte_carlo_confidence(signals, market_data)
            
            # Simple ensemble (could be improved with weighted voting)
            ensemble_conf = (bayesian_conf + monte_carlo_conf) / 2
            
            # Apply market condition adjustments
            market_adjustment = self._get_market_adjustment(market_data)
            final_conf = ensemble_conf * market_adjustment
            
            # Ensure bounds
            final_conf = max(0.1, min(0.95, final_conf))
            
            logger.debug(f"🎯 Ensemble confidence: bayesian={bayesian_conf:.3f}, "
                        f"monte_carlo={monte_carlo_conf:.3f}, "
                        f"market_adj={market_adjustment:.3f}, "
                        f"final={final_conf:.3f}")
            
            return final_conf
            
        except Exception as e:
            logger.error(f"❌ Ensemble confidence calculation failed: {e}")
            return 0.5
    
    def _get_prior_probability(self, signals: Dict[str, Any], 
                             market_data: Dict[str, Any]) -> float:
        """Get prior probability based on historical data"""
        try:
            # Base prior from market conditions
            volatility = market_data.get("volatility_5m", 0.001)
            if volatility < 0.0005:
                return 0.6  # Higher confidence in low vol
            elif volatility > 0.003:
                return 0.4  # Lower confidence in high vol
            else:
                return 0.5  # Neutral prior
                
        except Exception as e:
            logger.error(f"❌ Prior probability calculation failed: {e}")
            return 0.5
    
    def _calculate_likelihood(self, signals: Dict[str, Any], 
                            market_data: Dict[str, Any]) -> float:
        """Calculate likelihood from current signals"""
        try:
            if not signals:
                return 0.5
            
            # Calculate weighted average of signal confidences
            total_weight = 0
            weighted_confidence = 0
            
            for signal_name, signal_data in signals.items():
                if isinstance(signal_data, dict):
                    confidence = signal_data.get("confidence", 0.5)
                    weight = signal_data.get("weight", 0.1)
                    weighted_confidence += confidence * weight
                    total_weight += weight
            
            if total_weight > 0:
                return weighted_confidence / total_weight
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"❌ Likelihood calculation failed: {e}")
            return 0.5
    
    def _calculate_evidence(self, signals: Dict[str, Any], 
                          market_data: Dict[str, Any]) -> float:
        """Calculate evidence (normalization factor)"""
        try:
            # Simple evidence calculation based on signal count and strength
            signal_count = len(signals)
            if signal_count == 0:
                return 1.0
            
            # More signals = higher evidence
            evidence = 1.0 + (signal_count * 0.1)
            
            return min(2.0, evidence)  # Cap at 2.0
            
        except Exception as e:
            logger.error(f"❌ Evidence calculation failed: {e}")
            return 1.0
    
    def _get_market_adjustment(self, market_data: Dict[str, Any]) -> float:
        """Get market condition adjustment factor"""
        try:
            adjustment = 1.0
            
            # Volatility adjustment
            volatility = market_data.get("volatility_5m", 0.001)
            if volatility < 0.0005:
                adjustment *= 1.1  # Boost confidence in low vol
            elif volatility > 0.003:
                adjustment *= 0.9   # Reduce confidence in high vol
            
            # Volume adjustment
            volume = market_data.get("trading_volume_btc", 0)
            if volume > 100:  # High volume
                adjustment *= 1.05
            elif volume < 10:  # Low volume
                adjustment *= 0.95
            
            return adjustment
            
        except Exception as e:
            logger.error(f"❌ Market adjustment calculation failed: {e}")
            return 1.0
    
    def update_signal_performance(self, signal_name: str, success: bool):
        """Update signal performance history for Bayesian learning"""
        try:
            if signal_name not in self.signal_histories:
                self.signal_histories[signal_name] = []
            
            # Add performance data
            self.signal_histories[signal_name].append(1.0 if success else 0.0)
            
            # Keep only recent history (last 1000 observations)
            if len(self.signal_histories[signal_name]) > 1000:
                self.signal_histories[signal_name] = self.signal_histories[signal_name][-1000:]
            
            logger.debug(f"📊 Updated {signal_name} performance: "
                        f"{len(self.signal_histories[signal_name])} observations")
            
        except Exception as e:
            logger.error(f"❌ Signal performance update failed: {e}")
    
    def get_signal_statistics(self, signal_name: str) -> Dict[str, float]:
        """Get statistical summary for a signal"""
        try:
            if signal_name not in self.signal_histories:
                return {"mean": 0.5, "std": 0.1, "count": 0}
            
            history = self.signal_histories[signal_name]
            if not history:
                return {"mean": 0.5, "std": 0.1, "count": 0}
            
            mean = np.mean(history)
            std = np.std(history)
            count = len(history)
            
            return {
                "mean": mean,
                "std": std,
                "count": count,
                "confidence_interval": (mean - 1.96*std, mean + 1.96*std)
            }
            
        except Exception as e:
            logger.error(f"❌ Signal statistics calculation failed: {e}")
            return {"mean": 0.5, "std": 0.1, "count": 0}


# Global instance
global_probability_engine = ProbabilityEngine()
