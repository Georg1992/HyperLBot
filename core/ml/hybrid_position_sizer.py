"""
Hybrid Position Sizing System
Combines Kelly Criterion with Volatility Adjustment for optimal position sizing
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class PositionSizingResult:
    """Result of position sizing calculation"""
    position_size_btc: float
    position_size_usd: float
    kelly_percentage: float
    volatility_adjustment: float
    confidence_multiplier: float
    final_risk_percent: float
    leverage: float
    stop_loss: float
    target_price: float
    risk_reward_ratio: float
    expected_return: float
    max_drawdown_risk: float

class HybridPositionSizer:
    """Hybrid position sizing system combining Kelly Criterion and volatility adjustment"""
    
    def __init__(self):
        self.trade_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}
        self.volatility_history: List[float] = []
        
        # Kelly Criterion parameters
        self.min_kelly_percentage = 0.01  # 1% minimum
        self.max_kelly_percentage = 0.25  # 25% maximum (risk management)
        self.kelly_smoothing_factor = 0.1  # Smoothing for Kelly updates
        
        # Volatility adjustment parameters
        self.base_volatility = 0.02  # 2% base volatility (Bitcoin daily)
        self.volatility_lookback = 20  # 20 periods for volatility calculation
        self.volatility_adjustment_min = 0.3  # 30% minimum adjustment
        self.volatility_adjustment_max = 2.0  # 200% maximum adjustment
        
        # Risk management
        self.max_portfolio_risk = 0.10  # 10% maximum portfolio risk
        self.max_single_position_risk = 0.05  # 5% maximum single position risk
        
        logger.info("🎯 Hybrid Position Sizer initialized")
    
    def calculate_optimal_position_size(self, 
                                      direction: str,
                                      current_price: float,
                                      market_data: Dict[str, Any],
                                      signal_analysis: Dict[str, Any],
                                      account_balance: float,
                                      strategy: str = "scalping") -> PositionSizingResult:
        """
        Calculate optimal position size using hybrid Kelly + Volatility approach
        
        Args:
            direction: BUY or SELL
            current_price: Current market price
            market_data: Current market data
            signal_analysis: Signal analysis results
            account_balance: Available account balance
            strategy: Trading strategy (scalping, trend_following, etc.)
            
        Returns:
            PositionSizingResult with optimal sizing
        """
        try:
            logger.info(f"🎯 Calculating hybrid position size for {strategy} {direction} at ${current_price:.2f}")
            
            # 1. Calculate Kelly Criterion percentage
            kelly_percentage = self._calculate_kelly_percentage(strategy, signal_analysis)
            
            # 2. Calculate volatility adjustment
            volatility_adjustment = self._calculate_volatility_adjustment(market_data, strategy)
            
            # 3. Calculate confidence multiplier
            confidence_multiplier = self._calculate_confidence_multiplier(signal_analysis)
            
            # 4. Calculate base position size
            base_position_size = self._calculate_base_position_size(
                account_balance, kelly_percentage, volatility_adjustment, confidence_multiplier
            )
            
            # 5. Apply risk management constraints
            final_position_size = self._apply_risk_constraints(
                base_position_size, account_balance, current_price
            )
            
            # 6. Calculate trading parameters
            trading_params = self._calculate_trading_parameters(
                direction, current_price, final_position_size, market_data, strategy
            )
            
            # 7. Create result
            result = PositionSizingResult(
                position_size_btc=final_position_size / current_price,
                position_size_usd=final_position_size,
                kelly_percentage=kelly_percentage,
                volatility_adjustment=volatility_adjustment,
                confidence_multiplier=confidence_multiplier,
                final_risk_percent=(final_position_size / account_balance) * 100,
                leverage=trading_params["leverage"],
                stop_loss=trading_params["stop_loss"],
                target_price=trading_params["target_price"],
                risk_reward_ratio=trading_params["risk_reward_ratio"],
                expected_return=trading_params["expected_return"],
                max_drawdown_risk=trading_params["max_drawdown_risk"]
            )
            
            logger.info(f"✅ Hybrid position sizing: {result.position_size_usd:.2f} USD ({result.final_risk_percent:.2f}% risk), "
                       f"Kelly: {kelly_percentage:.3f}, Vol: {volatility_adjustment:.3f}, Conf: {confidence_multiplier:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Hybrid position sizing failed: {e}")
            return self._create_default_result(account_balance, current_price)
    
    def _calculate_kelly_percentage(self, strategy: str, signal_analysis: Dict[str, Any]) -> float:
        """Calculate Kelly Criterion percentage for position sizing"""
        try:
            # Get historical performance for this strategy
            strategy_performance = self._get_strategy_performance(strategy)
            
            if not strategy_performance or len(strategy_performance) < 10:
                # Not enough data - use conservative default
                return 0.02  # 2% default Kelly
            
            # Calculate win rate and average win/loss
            wins = [trade for trade in strategy_performance if trade.get("result", 0) > 0]
            losses = [trade for trade in strategy_performance if trade.get("result", 0) < 0]
            
            if not wins or not losses:
                return 0.02  # Default if no wins/losses
            
            win_rate = len(wins) / len(strategy_performance)
            avg_win = np.mean([trade["result"] for trade in wins])
            avg_loss = abs(np.mean([trade["result"] for trade in losses]))
            
            # Kelly formula: (bp - q) / b
            # where b = odds (avg_win/avg_loss), p = win_rate, q = loss_rate
            if avg_loss == 0:
                return 0.02  # Avoid division by zero
            
            odds = avg_win / avg_loss
            kelly_raw = (odds * win_rate - (1 - win_rate)) / odds
            
            # Apply smoothing and constraints
            kelly_smoothed = max(0, min(kelly_raw, self.max_kelly_percentage))
            kelly_final = max(self.min_kelly_percentage, kelly_smoothed)
            
            logger.debug(f"🎯 Kelly calculation: win_rate={win_rate:.3f}, avg_win={avg_win:.2f}, "
                        f"avg_loss={avg_loss:.2f}, odds={odds:.3f}, kelly={kelly_final:.3f}")
            
            return kelly_final
            
        except Exception as e:
            logger.error(f"❌ Kelly percentage calculation failed: {e}")
            return 0.02  # Default 2%
    
    def _calculate_volatility_adjustment(self, market_data: Dict[str, Any], strategy: str) -> float:
        """Calculate volatility adjustment factor"""
        try:
            # Get current volatility
            current_volatility = market_data.get("volatility_5m", 0.001)
            
            # Update volatility history
            self.volatility_history.append(current_volatility)
            if len(self.volatility_history) > self.volatility_lookback:
                self.volatility_history.pop(0)
            
            # Calculate average volatility
            if len(self.volatility_history) < 5:
                avg_volatility = current_volatility
            else:
                avg_volatility = np.mean(self.volatility_history[-10:])  # Last 10 periods
            
            # Calculate volatility ratio
            volatility_ratio = current_volatility / self.base_volatility
            
            # Strategy-specific volatility adjustments
            if strategy == "scalping":
                # Scalping: prefer lower volatility for tighter stops
                if volatility_ratio < 0.5:  # Very low volatility
                    adjustment = 1.5  # Increase position size
                elif volatility_ratio < 1.0:  # Normal volatility
                    adjustment = 1.0  # Standard size
                elif volatility_ratio < 2.0:  # High volatility
                    adjustment = 0.7  # Reduce size
                else:  # Extreme volatility
                    adjustment = 0.4  # Significantly reduce size
                    
            elif strategy == "trend_following":
                # Trend following: can handle higher volatility
                if volatility_ratio < 0.5:  # Very low volatility
                    adjustment = 1.2  # Slight increase
                elif volatility_ratio < 1.5:  # Normal to high volatility
                    adjustment = 1.0  # Standard size
                elif volatility_ratio < 3.0:  # High volatility
                    adjustment = 0.8  # Slight reduction
                else:  # Extreme volatility
                    adjustment = 0.5  # Reduce size
                    
            else:  # Default strategy
                # Standard adjustment
                adjustment = 1.0 / max(0.5, volatility_ratio)  # Inverse relationship
            
            # Apply constraints
            adjustment = max(self.volatility_adjustment_min, 
                           min(self.volatility_adjustment_max, adjustment))
            
            logger.debug(f"📊 Volatility adjustment: current={current_volatility:.4f}, "
                        f"avg={avg_volatility:.4f}, ratio={volatility_ratio:.3f}, adjustment={adjustment:.3f}")
            
            return adjustment
            
        except Exception as e:
            logger.error(f"❌ Volatility adjustment calculation failed: {e}")
            return 1.0  # Default no adjustment
    
    def _calculate_confidence_multiplier(self, signal_analysis: Dict[str, Any]) -> float:
        """Calculate confidence-based position size multiplier"""
        try:
            confidence = signal_analysis.get("overall_confidence", 0.5)
            
            # Confidence multiplier: 0.3 to 1.0 range
            # Low confidence (0.3) = 0.3x position size
            # High confidence (0.9) = 0.9x position size
            # Very high confidence (1.0) = 1.0x position size
            multiplier = 0.3 + (confidence * 0.7)
            
            # Ensure within bounds
            multiplier = max(0.3, min(1.0, multiplier))
            
            logger.debug(f"🎯 Confidence multiplier: confidence={confidence:.3f}, multiplier={multiplier:.3f}")
            
            return multiplier
            
        except Exception as e:
            logger.error(f"❌ Confidence multiplier calculation failed: {e}")
            return 0.5  # Default 0.5x
    
    def _calculate_base_position_size(self, account_balance: float, kelly_percentage: float, 
                                    volatility_adjustment: float, confidence_multiplier: float) -> float:
        """Calculate base position size using hybrid formula"""
        try:
            # Hybrid formula: Kelly × Volatility × Confidence
            hybrid_percentage = kelly_percentage * volatility_adjustment * confidence_multiplier
            
            # Calculate position size in USD
            position_size_usd = account_balance * hybrid_percentage
            
            logger.debug(f"💰 Base position size: balance={account_balance:.2f}, "
                        f"kelly={kelly_percentage:.3f}, vol={volatility_adjustment:.3f}, "
                        f"conf={confidence_multiplier:.3f}, hybrid={hybrid_percentage:.3f}, "
                        f"size={position_size_usd:.2f}")
            
            return position_size_usd
            
        except Exception as e:
            logger.error(f"❌ Base position size calculation failed: {e}")
            return account_balance * 0.01  # Default 1%
    
    def _apply_risk_constraints(self, base_position_size: float, account_balance: float, 
                              current_price: float) -> float:
        """Apply risk management constraints to position size"""
        try:
            # Maximum single position risk (5% of account)
            max_single_position = account_balance * self.max_single_position_risk
            
            # Maximum portfolio risk (10% of account)
            max_portfolio_position = account_balance * self.max_portfolio_risk
            
            # Apply constraints
            constrained_size = min(base_position_size, max_single_position, max_portfolio_position)
            
            # Minimum position size (0.1% of account)
            min_position = account_balance * 0.001
            final_size = max(constrained_size, min_position)
            
            logger.debug(f"🛡️ Risk constraints: base={base_position_size:.2f}, "
                        f"max_single={max_single_position:.2f}, max_portfolio={max_portfolio_position:.2f}, "
                        f"final={final_size:.2f}")
            
            return final_size
            
        except Exception as e:
            logger.error(f"❌ Risk constraints application failed: {e}")
            return account_balance * 0.01  # Default 1%
    
    def _calculate_trading_parameters(self, direction: str, current_price: float, 
                                   position_size_usd: float, market_data: Dict[str, Any], 
                                   strategy: str) -> Dict[str, Any]:
        """Calculate trading parameters (leverage, stops, targets)"""
        try:
            # Strategy-specific parameters - 40X LEVERAGE OPTIMIZED
            if strategy == "scalping":
                leverage = 40.0
                stop_percent = 0.001  # 0.1% stop (40x leverage optimized)
                target_percent = 0.002  # 0.2% target (2:1 R/R)
            elif strategy == "trend_following":
                leverage = 40.0  # Increased to 40x
                stop_percent = 0.002  # 0.2% stop (40x leverage optimized)
                target_percent = 0.005  # 0.5% target (2.5:1 R/R)
            elif strategy == "range_trading":
                leverage = 40.0
                stop_percent = 0.0015  # 0.15% stop (40x leverage optimized)
                target_percent = 0.003  # 0.3% target (2:1 R/R)
            elif strategy == "low_volatility_range":
                leverage = 40.0
                stop_percent = 0.001  # 0.1% stop (40x leverage optimized)
                target_percent = 0.002  # 0.2% target (2:1 R/R)
            else:
                leverage = 40.0  # All strategies use 40x leverage
                stop_percent = 0.002  # 0.2% stop (40x leverage optimized)
                target_percent = 0.004  # 0.4% target (2:1 R/R)
            
            # Calculate entry price
            entry_price = self._calculate_entry_price(direction, current_price, market_data)
            
            # Calculate stop loss and target
            if direction == "BUY":
                stop_loss = entry_price * (1 - stop_percent)
                target_price = entry_price * (1 + target_percent)
            else:  # SELL
                stop_loss = entry_price * (1 + stop_percent)
                target_price = entry_price * (1 - target_percent)
            
            # Calculate risk/reward ratio
            risk_reward_ratio = target_percent / stop_percent
            
            # Calculate expected return
            position_size_btc = position_size_usd / current_price
            expected_return = position_size_btc * (target_percent * current_price)
            
            # Calculate max drawdown risk
            max_drawdown_risk = (stop_percent * current_price * position_size_btc) / position_size_usd
            
            return {
                "leverage": leverage,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "risk_reward_ratio": risk_reward_ratio,
                "expected_return": expected_return,
                "max_drawdown_risk": max_drawdown_risk
            }
            
        except Exception as e:
            logger.error(f"❌ Trading parameters calculation failed: {e}")
            return {
                "leverage": 25.0,
                "stop_loss": current_price * 0.99,
                "target_price": current_price * 1.01,
                "risk_reward_ratio": 1.0,
                "expected_return": 0.0,
                "max_drawdown_risk": 0.01
            }
    
    def _calculate_entry_price(self, direction: str, current_price: float, 
                            market_data: Dict[str, Any]) -> float:
        """Calculate optimal entry price"""
        try:
            # For now, use current price as entry
            # In the future, this could be optimized based on order book, support/resistance, etc.
            return current_price
            
        except Exception as e:
            logger.error(f"❌ Entry price calculation failed: {e}")
            return current_price
    
    def _get_strategy_performance(self, strategy: str) -> List[Dict[str, Any]]:
        """Get historical performance data for strategy"""
        try:
            # Filter trade history by strategy
            strategy_trades = [trade for trade in self.trade_history 
                             if trade.get("strategy") == strategy]
            
            return strategy_trades
            
        except Exception as e:
            logger.error(f"❌ Strategy performance retrieval failed: {e}")
            return []
    
    def update_trade_result(self, trade_data: Dict[str, Any]):
        """Update trade history with new trade result"""
        try:
            self.trade_history.append(trade_data)
            
            # Keep only last 100 trades for performance calculation
            if len(self.trade_history) > 100:
                self.trade_history = self.trade_history[-100:]
            
            logger.debug(f"📊 Updated trade history: {len(self.trade_history)} trades")
            
        except Exception as e:
            logger.error(f"❌ Trade result update failed: {e}")
    
    def _create_default_result(self, account_balance: float, current_price: float) -> PositionSizingResult:
        """Create default result when calculation fails"""
        return PositionSizingResult(
            position_size_btc=0.001,
            position_size_usd=account_balance * 0.01,
            kelly_percentage=0.02,
            volatility_adjustment=1.0,
            confidence_multiplier=0.5,
            final_risk_percent=1.0,
            leverage=25.0,
            stop_loss=current_price * 0.99,
            target_price=current_price * 1.01,
            risk_reward_ratio=1.0,
            expected_return=0.0,
            max_drawdown_risk=0.01
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for position sizing optimization"""
        try:
            if not self.trade_history:
                return {"message": "No trades recorded yet"}
            
            # Calculate performance metrics
            total_trades = len(self.trade_history)
            winning_trades = [t for t in self.trade_history if t.get("result", 0) > 0]
            losing_trades = [t for t in self.trade_history if t.get("result", 0) < 0]
            
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
            avg_win = np.mean([t["result"] for t in winning_trades]) if winning_trades else 0
            avg_loss = abs(np.mean([t["result"] for t in losing_trades])) if losing_trades else 0
            
            return {
                "total_trades": total_trades,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": avg_win / avg_loss if avg_loss > 0 else 0,
                "kelly_percentage": self._calculate_kelly_percentage("default", {"overall_confidence": 0.5})
            }
            
        except Exception as e:
            logger.error(f"❌ Performance summary failed: {e}")
            return {"error": "Failed to calculate performance summary"}

# Global instance for easy access
hybrid_position_sizer = HybridPositionSizer()
