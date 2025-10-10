#!/usr/bin/env python3
"""
Probability Engine Module
Applies probability theory to trading decisions for optimal risk/reward
"""

from typing import Dict, Any, Optional, Tuple
from loguru import logger
from dataclasses import dataclass


@dataclass
class ExpectedValue:
    """Expected value calculation result"""
    ev_percent: float  # Expected value as percentage
    ev_dollars: float  # Expected value in dollars
    win_probability: float
    loss_probability: float
    expected_gain: float  # Expected gain if win
    expected_loss: float  # Expected loss if lose
    risk_reward_ratio: float
    should_trade: bool
    reasoning: str


class ProbabilityEngine:
    """Applies probability theory to trading decisions"""
    
    def __init__(self, min_ev_threshold: float = 0.0005):
        """
        Initialize Probability Engine - Optimized for 40x leverage trading
        
        Args:
            min_ev_threshold: Minimum EV (as %) to consider trading (default 0.05% for 40x leverage)
        """
        self.min_ev_threshold = min_ev_threshold
        logger.info(f"🎲 Probability Engine initialized - Min EV threshold: {min_ev_threshold:.2%} (40x leverage optimized)")
    
    def calculate_expected_value(
        self,
        confidence: float,
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        position_size: float = 1000.0
    ) -> ExpectedValue:
        """
        Calculate Expected Value for a trade
        
        Formula: EV = (Win_Prob × Win_Amount) - (Loss_Prob × Loss_Amount)
        
        Args:
            confidence: Win probability (0-1)
            entry_price: Entry price
            take_profit: Take profit price
            stop_loss: Stop loss price
            position_size: Position size in dollars
            
        Returns:
            ExpectedValue object with detailed calculation
        """
        try:
            # Validate inputs
            if not all([confidence, entry_price, take_profit, stop_loss, position_size]):
                logger.warning("⚠️ Missing required inputs for EV calculation")
                return self._create_invalid_ev("Missing required inputs")
            
            if confidence < 0 or confidence > 1:
                logger.warning(f"⚠️ Invalid confidence: {confidence}")
                return self._create_invalid_ev(f"Invalid confidence: {confidence}")
            
            # Probabilities
            win_probability = confidence
            loss_probability = 1 - confidence
            
            # Calculate gain/loss amounts (as percentage of entry)
            if entry_price > 0:
                gain_pct = abs(take_profit - entry_price) / entry_price
                loss_pct = abs(entry_price - stop_loss) / entry_price
            else:
                logger.warning("⚠️ Invalid entry price")
                return self._create_invalid_ev("Invalid entry price")
            
            # Expected gain/loss in dollars
            expected_gain = gain_pct * position_size
            expected_loss = loss_pct * position_size
            
            # Risk/Reward Ratio
            if loss_pct > 0:
                risk_reward_ratio = gain_pct / loss_pct
            else:
                risk_reward_ratio = float('inf')
            
            # Expected Value calculation
            ev_dollars = (win_probability * expected_gain) - (loss_probability * expected_loss)
            ev_percent = ev_dollars / position_size
            
            # Trading decision
            should_trade = ev_percent >= self.min_ev_threshold
            
            # Reasoning
            reasoning = self._generate_ev_reasoning(
                ev_percent=ev_percent,
                win_probability=win_probability,
                risk_reward_ratio=risk_reward_ratio,
                should_trade=should_trade
            )
            
            logger.info(f"🎲 EV Calculation: {ev_percent:.2%} | R:R={risk_reward_ratio:.2f} | Trade: {should_trade}")
            
            return ExpectedValue(
                ev_percent=ev_percent,
                ev_dollars=ev_dollars,
                win_probability=win_probability,
                loss_probability=loss_probability,
                expected_gain=expected_gain,
                expected_loss=expected_loss,
                risk_reward_ratio=risk_reward_ratio,
                should_trade=should_trade,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"❌ EV calculation failed: {e}")
            return self._create_invalid_ev(f"Calculation error: {e}")
    
    def _generate_ev_reasoning(
        self,
        ev_percent: float,
        win_probability: float,
        risk_reward_ratio: float,
        should_trade: bool
    ) -> str:
        """Generate human-readable reasoning for EV decision"""
        reasoning_parts = []
        
        # EV interpretation
        if ev_percent >= 0.02:
            reasoning_parts.append(f"🟢 Excellent EV: +{ev_percent:.2%} per trade")
        elif ev_percent >= 0.01:
            reasoning_parts.append(f"🟢 Good EV: +{ev_percent:.2%} per trade")
        elif ev_percent >= 0.005:
            reasoning_parts.append(f"🟡 Acceptable EV: +{ev_percent:.2%} per trade")
        elif ev_percent >= 0:
            reasoning_parts.append(f"🟡 Marginal EV: +{ev_percent:.2%} per trade")
        else:
            reasoning_parts.append(f"🔴 Negative EV: {ev_percent:.2%} per trade")
        
        # Win probability interpretation
        if win_probability >= 0.80:
            reasoning_parts.append(f"High win probability: {win_probability:.1%}")
        elif win_probability >= 0.65:
            reasoning_parts.append(f"Good win probability: {win_probability:.1%}")
        elif win_probability >= 0.50:
            reasoning_parts.append(f"Fair win probability: {win_probability:.1%}")
        else:
            reasoning_parts.append(f"Low win probability: {win_probability:.1%}")
        
        # Risk/Reward interpretation
        if risk_reward_ratio >= 3.0:
            reasoning_parts.append(f"Excellent R:R ratio: {risk_reward_ratio:.2f}")
        elif risk_reward_ratio >= 2.0:
            reasoning_parts.append(f"Good R:R ratio: {risk_reward_ratio:.2f}")
        elif risk_reward_ratio >= 1.5:
            reasoning_parts.append(f"Acceptable R:R ratio: {risk_reward_ratio:.2f}")
        else:
            reasoning_parts.append(f"Poor R:R ratio: {risk_reward_ratio:.2f}")
        
        # Trading recommendation
        if should_trade:
            if ev_percent >= 0.015:
                reasoning_parts.append("✅ STRONG TRADE - High positive EV")
            else:
                reasoning_parts.append("✅ TRADE - Positive EV above threshold")
        else:
            if ev_percent < 0:
                reasoning_parts.append("❌ NO TRADE - Negative expected value")
            else:
                reasoning_parts.append(f"❌ NO TRADE - EV below minimum threshold ({self.min_ev_threshold:.2%})")
        
        return " | ".join(reasoning_parts)
    
    def _create_invalid_ev(self, reason: str) -> ExpectedValue:
        """Create an invalid EV result"""
        return ExpectedValue(
            ev_percent=0.0,
            ev_dollars=0.0,
            win_probability=0.0,
            loss_probability=1.0,
            expected_gain=0.0,
            expected_loss=0.0,
            risk_reward_ratio=0.0,
            should_trade=False,
            reasoning=f"❌ Invalid calculation: {reason}"
        )
    
    def calculate_breakeven_win_rate(self, risk_reward_ratio: float) -> float:
        """
        Calculate the minimum win rate needed to break even
        
        Formula: Breakeven = Loss / (Win + Loss) = 1 / (1 + R:R)
        
        Args:
            risk_reward_ratio: Risk/Reward ratio (Reward/Risk)
            
        Returns:
            Breakeven win rate (0-1)
        """
        if risk_reward_ratio <= 0:
            return 1.0  # Need 100% win rate with 0 reward
        
        breakeven = 1 / (1 + risk_reward_ratio)
        return breakeven
    
    def calculate_edge(self, win_probability: float, risk_reward_ratio: float) -> float:
        """
        Calculate edge over breakeven
        
        Edge = Actual Win Rate - Breakeven Win Rate
        
        Positive edge = Profitable system
        
        Args:
            win_probability: Actual win probability
            risk_reward_ratio: Risk/Reward ratio
            
        Returns:
            Edge as decimal (e.g., 0.15 = 15% edge)
        """
        breakeven = self.calculate_breakeven_win_rate(risk_reward_ratio)
        edge = win_probability - breakeven
        return edge
    
    def compare_trade_scenarios(
        self,
        scenarios: Dict[str, Dict[str, float]],
        position_size: float = 1000.0
    ) -> Dict[str, ExpectedValue]:
        """
        Compare multiple trade scenarios and rank by EV
        
        Args:
            scenarios: Dict of {name: {confidence, entry, tp, sl}}
            position_size: Position size for comparison
            
        Returns:
            Dict of {name: ExpectedValue} sorted by EV (best first)
        """
        results = {}
        
        for name, params in scenarios.items():
            ev = self.calculate_expected_value(
                confidence=params.get("confidence", 0),
                entry_price=params.get("entry_price", 0),
                take_profit=params.get("take_profit", 0),
                stop_loss=params.get("stop_loss", 0),
                position_size=position_size
            )
            results[name] = ev
        
        # Sort by EV (highest first)
        sorted_results = dict(sorted(
            results.items(),
            key=lambda x: x[1].ev_percent,
            reverse=True
        ))
        
        logger.info(f"🎲 Compared {len(scenarios)} scenarios - Best: {list(sorted_results.keys())[0]}")
        
        return sorted_results
    
    def calculate_kelly_position_size(
        self,
        confidence: float,
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        total_capital: float,
        kelly_fraction: float = 0.25,
        max_position_pct: float = 0.10
    ) -> Dict[str, Any]:
        """
        Calculate optimal position size using Kelly Criterion
        
        Kelly Formula: f* = (p × b - q) / b
        where:
            f* = fraction of capital to bet
            p = probability of winning
            q = probability of losing (1-p)
            b = win/loss ratio (reward/risk)
        
        Args:
            confidence: Win probability (0-1)
            entry_price: Entry price
            take_profit: Take profit price
            stop_loss: Stop loss price
            total_capital: Total available capital
            kelly_fraction: Fraction of full Kelly to use (0.25 = quarter Kelly, safer)
            max_position_pct: Maximum position as % of capital (safety cap)
            
        Returns:
            Dict with position size details
        """
        try:
            # Calculate win/loss amounts (as percentage)
            if entry_price > 0:
                win_pct = abs(take_profit - entry_price) / entry_price
                loss_pct = abs(entry_price - stop_loss) / entry_price
            else:
                logger.warning("⚠️ Invalid entry price for Kelly calculation")
                return self._create_zero_position("Invalid entry price")
            
            if loss_pct == 0:
                logger.warning("⚠️ Zero risk (no stop loss) - Kelly undefined")
                return self._create_zero_position("Zero risk - undefined Kelly")
            
            # Kelly parameters
            win_probability = confidence
            loss_probability = 1 - confidence
            win_loss_ratio = win_pct / loss_pct  # b in Kelly formula
            
            # Full Kelly calculation
            kelly_pct = (win_probability * win_loss_ratio - loss_probability) / win_loss_ratio
            
            # Apply fractional Kelly (safer)
            fractional_kelly_pct = kelly_pct * kelly_fraction
            
            # Apply maximum position size cap
            final_kelly_pct = max(0, min(fractional_kelly_pct, max_position_pct))
            
            # Calculate position size in dollars
            position_size = total_capital * final_kelly_pct
            
            # Calculate breakeven win rate
            breakeven_win_rate = self.calculate_breakeven_win_rate(win_loss_ratio)
            edge = self.calculate_edge(win_probability, win_loss_ratio)
            
            # Recommendation
            if kelly_pct < 0:
                recommendation = "❌ NO TRADE - Negative Kelly (negative edge)"
                should_trade = False
            elif final_kelly_pct == 0:
                recommendation = "❌ NO TRADE - Position size too small"
                should_trade = False
            elif edge < 0.05:
                recommendation = "⚠️ CAUTION - Low edge, consider skipping"
                should_trade = False
            elif final_kelly_pct >= max_position_pct:
                recommendation = f"✅ TRADE - Max position ({max_position_pct:.1%}) - Strong signal"
                should_trade = True
            elif final_kelly_pct >= 0.05:
                recommendation = f"✅ TRADE - {final_kelly_pct:.1%} position"
                should_trade = True
            else:
                recommendation = f"⚠️ SMALL POSITION - {final_kelly_pct:.1%} (low confidence or poor R:R)"
                should_trade = True
            
            result = {
                "position_size_dollars": round(position_size, 2),
                "position_size_pct": round(final_kelly_pct, 4),
                "full_kelly_pct": round(kelly_pct, 4),
                "fractional_kelly_pct": round(fractional_kelly_pct, 4),
                "kelly_fraction_used": kelly_fraction,
                "max_position_cap": max_position_pct,
                "win_probability": win_probability,
                "win_loss_ratio": round(win_loss_ratio, 2),
                "breakeven_win_rate": round(breakeven_win_rate, 4),
                "edge": round(edge, 4),
                "recommendation": recommendation,
                "should_trade": should_trade,
                "capped_by_max": final_kelly_pct == max_position_pct
            }
            
            logger.info(f"💰 Kelly Position: ${position_size:,.2f} ({final_kelly_pct:.2%} of ${total_capital:,.2f}) | Edge: {edge:+.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Kelly calculation failed: {e}")
            return self._create_zero_position(f"Calculation error: {e}")
    
    def _create_zero_position(self, reason: str) -> Dict[str, Any]:
        """Create a zero position result"""
        return {
            "position_size_dollars": 0.0,
            "position_size_pct": 0.0,
            "full_kelly_pct": 0.0,
            "fractional_kelly_pct": 0.0,
            "kelly_fraction_used": 0.0,
            "max_position_cap": 0.0,
            "win_probability": 0.0,
            "win_loss_ratio": 0.0,
            "breakeven_win_rate": 1.0,
            "edge": 0.0,
            "recommendation": f"❌ NO POSITION - {reason}",
            "should_trade": False,
            "capped_by_max": False
        }


# Global singleton instance
_global_probability_engine = None


def get_global_probability_engine() -> ProbabilityEngine:
    """Get the global ProbabilityEngine singleton instance"""
    global _global_probability_engine
    if _global_probability_engine is None:
        _global_probability_engine = ProbabilityEngine()
    return _global_probability_engine
