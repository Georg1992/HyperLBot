#!/usr/bin/env python3
"""
Monte Carlo Risk Simulator Module
Simulates thousands of trade sequences to assess risk and expected outcomes
"""

import random
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class SimulationResult:
    """Result of a Monte Carlo simulation"""
    num_simulations: int
    num_trades_per_sim: int
    starting_capital: float
    
    # Final balance statistics
    final_balances: List[float]
    mean_final_balance: float
    median_final_balance: float
    std_dev_final_balance: float
    min_final_balance: float
    max_final_balance: float
    
    # Return statistics
    mean_return_pct: float
    median_return_pct: float
    percentile_5: float  # 5th percentile (bad outcome)
    percentile_25: float
    percentile_75: float
    percentile_95: float  # 95th percentile (good outcome)
    
    # Risk metrics
    max_drawdown: float  # Worst peak-to-trough decline
    avg_drawdown: float
    probability_of_profit: float  # P(ending balance > starting capital)
    probability_of_ruin: float  # P(losing > 50% of capital)
    
    # Drawdown details
    worst_drawdown_sequence: List[float]  # Equity curve of worst simulation
    best_sequence: List[float]  # Equity curve of best simulation
    median_sequence: List[float]  # Equity curve of median simulation
    
    # Win/loss statistics
    avg_win_rate: float
    avg_total_pnl: float


@dataclass
class RiskMetrics:
    """Risk assessment metrics for a trading strategy"""
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float  # Return / Max Drawdown
    expectancy: float  # Average $ per trade
    risk_of_ruin: float  # Probability of losing 50%+ capital


class MonteCarloSimulator:
    """Simulates trading outcomes using Monte Carlo methods"""
    
    def __init__(self):
        """Initialize Monte Carlo Simulator"""
        logger.info("🎲 Monte Carlo Simulator initialized")
    
    def simulate_trading_outcomes(
        self,
        win_probability: float,
        win_size_pct: float,
        loss_size_pct: float,
        num_trades: int,
        num_simulations: int = 10000,
        starting_capital: float = 10000.0,
        position_size_pct: float = 0.10
    ) -> SimulationResult:
        """
        Simulate multiple trading sequences
        
        Args:
            win_probability: Probability of winning each trade (0-1)
            win_size_pct: Average win size as % (e.g., 0.02 for 2%)
            loss_size_pct: Average loss size as % (e.g., 0.01 for 1%)
            num_trades: Number of trades per simulation
            num_simulations: Number of simulation runs
            starting_capital: Starting balance
            position_size_pct: Position size as % of capital per trade
            
        Returns:
            SimulationResult with comprehensive statistics
        """
        logger.info(f"🎲 Running {num_simulations} simulations with {num_trades} trades each...")
        
        final_balances = []
        max_drawdowns = []
        equity_curves = []
        win_counts = []
        
        for sim in range(num_simulations):
            balance = starting_capital
            peak_balance = starting_capital
            max_drawdown = 0.0
            equity_curve = [starting_capital]
            wins = 0
            
            for trade in range(num_trades):
                # Determine if trade wins or loses
                won = random.random() < win_probability
                
                # Calculate position size (fixed % of current capital)
                position_size = balance * position_size_pct
                
                if won:
                    # Win: Add win_size_pct × position_size
                    pnl = position_size * win_size_pct
                    balance += pnl
                    wins += 1
                else:
                    # Loss: Subtract loss_size_pct × position_size
                    pnl = -position_size * loss_size_pct
                    balance += pnl
                
                # Track equity curve
                equity_curve.append(balance)
                
                # Update peak and drawdown
                if balance > peak_balance:
                    peak_balance = balance
                
                drawdown = (peak_balance - balance) / peak_balance
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                
                # Stop if ruined (lost 90%+ of capital)
                if balance < starting_capital * 0.1:
                    # Fill rest of curve with final balance
                    equity_curve.extend([balance] * (num_trades - trade))
                    break
            
            final_balances.append(balance)
            max_drawdowns.append(max_drawdown)
            equity_curves.append(equity_curve)
            win_counts.append(wins)
        
        # Calculate statistics
        final_balances_array = np.array(final_balances)
        returns = (final_balances_array - starting_capital) / starting_capital * 100
        
        mean_final = float(np.mean(final_balances_array))
        median_final = float(np.median(final_balances_array))
        std_final = float(np.std(final_balances_array))
        min_final = float(np.min(final_balances_array))
        max_final = float(np.max(final_balances_array))
        
        mean_return = float(np.mean(returns))
        median_return = float(np.median(returns))
        
        # Percentiles
        percentile_5 = float(np.percentile(returns, 5))
        percentile_25 = float(np.percentile(returns, 25))
        percentile_75 = float(np.percentile(returns, 75))
        percentile_95 = float(np.percentile(returns, 95))
        
        # Risk metrics
        max_dd = float(np.mean(max_drawdowns))
        worst_dd = float(np.max(max_drawdowns))
        
        prob_profit = float(np.sum(final_balances_array > starting_capital) / num_simulations)
        prob_ruin = float(np.sum(final_balances_array < starting_capital * 0.5) / num_simulations)
        
        avg_win_rate = float(np.mean(win_counts) / num_trades)
        avg_pnl = mean_final - starting_capital
        
        # Find worst, best, and median equity curves
        worst_idx = np.argmin(final_balances_array)
        best_idx = np.argmax(final_balances_array)
        median_idx = np.argsort(final_balances_array)[len(final_balances_array) // 2]
        
        result = SimulationResult(
            num_simulations=num_simulations,
            num_trades_per_sim=num_trades,
            starting_capital=starting_capital,
            final_balances=final_balances,
            mean_final_balance=mean_final,
            median_final_balance=median_final,
            std_dev_final_balance=std_final,
            min_final_balance=min_final,
            max_final_balance=max_final,
            mean_return_pct=mean_return,
            median_return_pct=median_return,
            percentile_5=percentile_5,
            percentile_25=percentile_25,
            percentile_75=percentile_75,
            percentile_95=percentile_95,
            max_drawdown=worst_dd,
            avg_drawdown=max_dd,
            probability_of_profit=prob_profit,
            probability_of_ruin=prob_ruin,
            worst_drawdown_sequence=equity_curves[worst_idx],
            best_sequence=equity_curves[best_idx],
            median_sequence=equity_curves[median_idx],
            avg_win_rate=avg_win_rate,
            avg_total_pnl=avg_pnl
        )
        
        logger.success(f"✅ Simulation complete: Mean return {mean_return:+.1f}% | "
                      f"P(profit) = {prob_profit:.1%} | Max DD = {worst_dd:.1%}")
        
        return result
    
    def calculate_risk_metrics(
        self,
        sim_result: SimulationResult,
        risk_free_rate: float = 0.0
    ) -> RiskMetrics:
        """
        Calculate advanced risk metrics from simulation
        
        Args:
            sim_result: Simulation result
            risk_free_rate: Risk-free rate for Sharpe calculation (annualized)
            
        Returns:
            RiskMetrics object
        """
        returns = np.array([(b - sim_result.starting_capital) / sim_result.starting_capital 
                           for b in sim_result.final_balances])
        
        # Sharpe Ratio
        if np.std(returns) > 0:
            sharpe = (np.mean(returns) - risk_free_rate) / np.std(returns)
        else:
            sharpe = 0.0
        
        # Sortino Ratio (only penalizes downside volatility)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and np.std(downside_returns) > 0:
            sortino = (np.mean(returns) - risk_free_rate) / np.std(downside_returns)
        else:
            sortino = sharpe  # No downside, use Sharpe
        
        # Calmar Ratio (return / max drawdown)
        if sim_result.max_drawdown > 0:
            calmar = sim_result.mean_return_pct / (sim_result.max_drawdown * 100)
        else:
            calmar = float('inf')
        
        # Expectancy (average $ per trade)
        expectancy = sim_result.avg_total_pnl / sim_result.num_trades_per_sim
        
        return RiskMetrics(
            sharpe_ratio=round(sharpe, 3),
            sortino_ratio=round(sortino, 3),
            max_drawdown_pct=round(sim_result.max_drawdown * 100, 2),
            calmar_ratio=round(calmar, 3),
            expectancy=round(expectancy, 2),
            risk_of_ruin=round(sim_result.probability_of_ruin, 4)
        )
    
    def generate_confidence_intervals(
        self,
        sim_result: SimulationResult
    ) -> Dict[str, Tuple[float, float]]:
        """
        Generate confidence intervals for outcomes
        
        Returns:
            Dict with 68%, 95%, and 99% confidence intervals
        """
        returns = np.array([(b - sim_result.starting_capital) / sim_result.starting_capital * 100
                           for b in sim_result.final_balances])
        
        # 68% confidence interval (1 standard deviation)
        ci_68 = (float(np.percentile(returns, 16)), float(np.percentile(returns, 84)))
        
        # 95% confidence interval (2 standard deviations)
        ci_95 = (float(np.percentile(returns, 2.5)), float(np.percentile(returns, 97.5)))
        
        # 99% confidence interval
        ci_99 = (float(np.percentile(returns, 0.5)), float(np.percentile(returns, 99.5)))
        
        return {
            "68%": ci_68,
            "95%": ci_95,
            "99%": ci_99
        }
    
    def assess_strategy_viability(
        self,
        win_probability: float,
        win_size_pct: float,
        loss_size_pct: float,
        num_trades: int = 100,
        target_return_pct: float = 20.0
    ) -> Dict[str, Any]:
        """
        Quick assessment of strategy viability
        
        Args:
            win_probability: Win probability
            win_size_pct: Average win %
            loss_size_pct: Average loss %
            num_trades: Number of trades to simulate
            target_return_pct: Target return percentage
            
        Returns:
            Dict with viability assessment
        """
        # Run simulation
        sim_result = self.simulate_trading_outcomes(
            win_probability=win_probability,
            win_size_pct=win_size_pct,
            loss_size_pct=loss_size_pct,
            num_trades=num_trades,
            num_simulations=5000,
            starting_capital=10000.0,
            position_size_pct=0.10
        )
        
        risk_metrics = self.calculate_risk_metrics(sim_result)
        
        # Viability criteria
        is_profitable = sim_result.probability_of_profit > 0.60
        is_safe = sim_result.probability_of_ruin < 0.10
        meets_target = sim_result.median_return_pct >= target_return_pct
        acceptable_drawdown = sim_result.max_drawdown < 0.30
        
        viable = is_profitable and is_safe and acceptable_drawdown
        
        if viable and meets_target:
            recommendation = "✅ EXCELLENT - Strategy is viable and meets targets"
        elif viable:
            recommendation = "✅ VIABLE - Strategy is safe but may not meet return targets"
        elif is_profitable and not is_safe:
            recommendation = "⚠️ RISKY - Profitable but high risk of ruin"
        elif not is_profitable:
            recommendation = "❌ NOT VIABLE - Low probability of profit"
        else:
            recommendation = "⚠️ MARGINAL - Review strategy parameters"
        
        return {
            "viable": viable,
            "recommendation": recommendation,
            "probability_of_profit": sim_result.probability_of_profit,
            "probability_of_ruin": sim_result.probability_of_ruin,
            "expected_return_pct": sim_result.median_return_pct,
            "max_drawdown_pct": sim_result.max_drawdown * 100,
            "sharpe_ratio": risk_metrics.sharpe_ratio,
            "meets_target": meets_target,
            "criteria": {
                "profitable": is_profitable,
                "safe": is_safe,
                "meets_target": meets_target,
                "acceptable_drawdown": acceptable_drawdown
            }
        }


# Global singleton instance
_global_monte_carlo_simulator = None


def get_global_monte_carlo_simulator() -> MonteCarloSimulator:
    """Get the global MonteCarloSimulator singleton instance"""
    global _global_monte_carlo_simulator
    if _global_monte_carlo_simulator is None:
        _global_monte_carlo_simulator = MonteCarloSimulator()
    return _global_monte_carlo_simulator

