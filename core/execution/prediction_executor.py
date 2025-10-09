#!/usr/bin/env python3
"""
Prediction-Based Trade Executor
Executes limit orders based on AI predictions with strategy-specific confidence thresholds
"""

from typing import Dict, Any, Optional
from loguru import logger
from dataclasses import dataclass


@dataclass
class StrategyThresholds:
    """Confidence thresholds for a specific strategy"""
    min_confidence: float  # Minimum to consider trading
    optimal_confidence: float  # Ideal confidence for execution
    max_position_size: float  # Maximum position size in BTC
    min_ev_percent: float  # Minimum Expected Value %
    require_bayesian: bool  # Require Bayesian fusion confidence
    calibration_weight: float  # How much to weight calibrated confidence (0-1)


class PredictionExecutor:
    """Executes trades based on AI predictions with strategy-specific logic"""
    
    # Strategy-specific confidence thresholds
    STRATEGY_THRESHOLDS = {
        "scalping": StrategyThresholds(
            min_confidence=0.70,  # 70% - High confidence needed for quick trades
            optimal_confidence=0.80,  # 80% - Ideal
            max_position_size=0.005,  # 0.005 BTC (~$600) - Small positions
            min_ev_percent=0.3,  # 0.3% - Quick gains
            require_bayesian=True,  # Must have Bayesian confirmation
            calibration_weight=0.8  # Heavily trust calibration
        ),
        "standard": StrategyThresholds(
            min_confidence=0.65,  # 65% - Moderate confidence
            optimal_confidence=0.75,  # 75% - Ideal
            max_position_size=0.01,  # 0.01 BTC (~$1,200) - Medium positions
            min_ev_percent=0.5,  # 0.5% - Balanced risk/reward
            require_bayesian=True,  # Must have Bayesian confirmation
            calibration_weight=0.9  # Trust calibration heavily
        ),
        "range_trading": StrategyThresholds(
            min_confidence=0.60,  # 60% - Lower confidence OK (defined ranges)
            optimal_confidence=0.70,  # 70% - Ideal
            max_position_size=0.015,  # 0.015 BTC (~$1,800) - Larger positions
            min_ev_percent=0.4,  # 0.4% - Quick range profits
            require_bayesian=False,  # S/R levels are primary
            calibration_weight=0.7  # Moderate calibration trust
        ),
        "trend_following": StrategyThresholds(
            min_confidence=0.65,  # 65% - Need trend confirmation
            optimal_confidence=0.75,  # 75% - Ideal
            max_position_size=0.02,  # 0.02 BTC (~$2,400) - Large positions
            min_ev_percent=0.8,  # 0.8% - Larger trends = bigger targets
            require_bayesian=True,  # Multi-signal confirmation
            calibration_weight=0.85  # High calibration trust
        ),
        "breakout": StrategyThresholds(
            min_confidence=0.72,  # 72% - High confidence for breakouts
            optimal_confidence=0.82,  # 82% - Ideal
            max_position_size=0.008,  # 0.008 BTC (~$960) - Medium-small
            min_ev_percent=1.0,  # 1.0% - Breakouts need bigger targets
            require_bayesian=True,  # Must confirm with multiple signals
            calibration_weight=0.9  # Trust calibration
        ),
    }
    
    def __init__(self, trading_execution, account_manager, session_manager):
        """
        Initialize prediction executor
        
        Args:
            trading_execution: TradingExecution instance for placing orders
            account_manager: AccountManager instance for balance checks
            session_manager: SessionManager instance for tracking
        """
        self.trading_execution = trading_execution
        self.account_manager = account_manager
        self.session_manager = session_manager
        
        # Execution tracking
        self.executions_today = 0
        self.last_execution_time = 0
        self.consecutive_losses = 0
        self.max_daily_executions = 50  # Safety limit
        self.min_time_between_trades = 180  # 3 minutes minimum
        
        logger.info("🎯 Prediction Executor initialized with strategy-based thresholds")
        self._log_strategy_thresholds()
    
    def _log_strategy_thresholds(self):
        """Log all strategy thresholds for transparency"""
        logger.info("📊 Strategy Confidence Thresholds:")
        for strategy, thresholds in self.STRATEGY_THRESHOLDS.items():
            logger.info(f"   {strategy.upper()}:")
            logger.info(f"      Min Confidence: {thresholds.min_confidence:.1%}")
            logger.info(f"      Optimal Confidence: {thresholds.optimal_confidence:.1%}")
            logger.info(f"      Max Position: {thresholds.max_position_size} BTC")
            logger.info(f"      Min EV: {thresholds.min_ev_percent:+.1%}")
            logger.info(f"      Require Bayesian: {thresholds.require_bayesian}")
    
    def should_execute(self, prediction: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        """
        Determine if prediction meets execution criteria
        
        Args:
            prediction: Prediction dict from RealtimePredictionEngine
            strategy: Current trading strategy
            
        Returns:
            Dict with decision and reasoning
        """
        try:
            # Get strategy thresholds
            thresholds = self.STRATEGY_THRESHOLDS.get(strategy)
            if not thresholds:
                return {
                    "should_execute": False,
                    "reason": f"Unknown strategy: {strategy}",
                    "checks_passed": []
                }
            
            checks_passed = []
            checks_failed = []
            
            # 1. CHECK: Confidence threshold
            calibrated_conf = prediction.get("calibrated_confidence", prediction.get("confidence", 0))
            if calibrated_conf >= thresholds.min_confidence:
                checks_passed.append(f"✅ Confidence {calibrated_conf:.1%} >= {thresholds.min_confidence:.1%}")
            else:
                checks_failed.append(f"❌ Confidence {calibrated_conf:.1%} < {thresholds.min_confidence:.1%}")
            
            # 2. CHECK: Expected Value
            ev_percent = prediction.get("expected_value", 0)
            should_trade_ev = prediction.get("should_trade_ev", False)
            if should_trade_ev and ev_percent >= thresholds.min_ev_percent:
                checks_passed.append(f"✅ EV {ev_percent:+.2%} >= {thresholds.min_ev_percent:+.2%}")
            else:
                checks_failed.append(f"❌ EV {ev_percent:+.2%} < {thresholds.min_ev_percent:+.2%} or negative")
            
            # 3. CHECK: Bayesian fusion (if required)
            if thresholds.require_bayesian:
                bayesian_conf = prediction.get("bayesian_confidence")
                if bayesian_conf and bayesian_conf >= thresholds.min_confidence:
                    checks_passed.append(f"✅ Bayesian {bayesian_conf:.1%} >= {thresholds.min_confidence:.1%}")
                else:
                    checks_failed.append(f"❌ Bayesian not available or below threshold")
            else:
                checks_passed.append("✅ Bayesian not required for this strategy")
            
            # 4. CHECK: Rate limiting
            import time
            time_since_last = time.time() - self.last_execution_time
            if time_since_last >= self.min_time_between_trades:
                checks_passed.append(f"✅ Time since last trade: {time_since_last:.0f}s >= {self.min_time_between_trades}s")
            else:
                checks_failed.append(f"❌ Too soon: {time_since_last:.0f}s < {self.min_time_between_trades}s")
            
            # 5. CHECK: Daily execution limit
            if self.executions_today < self.max_daily_executions:
                checks_passed.append(f"✅ Daily executions: {self.executions_today}/{self.max_daily_executions}")
            else:
                checks_failed.append(f"❌ Daily limit reached: {self.executions_today}/{self.max_daily_executions}")
            
            # 6. CHECK: Balance available
            balance = self.account_manager.get_account_balance() if self.account_manager else 0
            min_balance_required = thresholds.max_position_size * prediction.get("entry_price", 120000) * 0.1  # 10% margin
            if balance >= min_balance_required:
                checks_passed.append(f"✅ Balance ${balance:.2f} >= ${min_balance_required:.2f}")
            else:
                checks_failed.append(f"❌ Insufficient balance: ${balance:.2f} < ${min_balance_required:.2f}")
            
            # 7. CHECK: Direction is not NEUTRAL
            direction = prediction.get("direction", "NEUTRAL")
            if direction in ["LONG", "SHORT"]:
                checks_passed.append(f"✅ Direction: {direction}")
            else:
                checks_failed.append(f"❌ Direction is NEUTRAL")
            
            # Decision: ALL checks must pass
            should_execute = len(checks_failed) == 0
            
            return {
                "should_execute": should_execute,
                "reason": "All checks passed" if should_execute else f"{len(checks_failed)} checks failed",
                "checks_passed": checks_passed,
                "checks_failed": checks_failed,
                "confidence_score": calibrated_conf,
                "ev_score": ev_percent,
                "position_size": self._calculate_position_size(prediction, thresholds, calibrated_conf)
            }
            
        except Exception as e:
            logger.error(f"❌ Execution check failed: {e}")
            return {
                "should_execute": False,
                "reason": f"Error: {e}",
                "checks_passed": [],
                "checks_failed": [f"❌ Exception: {e}"]
            }
    
    def _calculate_position_size(self, prediction: Dict[str, Any], thresholds: StrategyThresholds, confidence: float) -> float:
        """
        Calculate optimal position size based on confidence and Kelly
        
        Returns:
            Position size in BTC
        """
        try:
            # Get Kelly position size (already calculated)
            kelly_position_pct = prediction.get("kelly_position_pct", 0.05)  # Default 5%
            kelly_position_dollars = prediction.get("kelly_position_dollars", 500)
            
            # Convert to BTC
            entry_price = prediction.get("entry_price", 120000)
            kelly_position_btc = kelly_position_dollars / entry_price
            
            # Cap at strategy max
            position_size = min(kelly_position_btc, thresholds.max_position_size)
            
            # Scale by confidence (if above optimal, use full Kelly, otherwise scale down)
            if confidence < thresholds.optimal_confidence:
                confidence_ratio = confidence / thresholds.optimal_confidence
                position_size *= confidence_ratio
            
            # Minimum position size: 0.001 BTC (~$120)
            position_size = max(0.001, position_size)
            
            return round(position_size, 4)
            
        except Exception as e:
            logger.error(f"❌ Position size calculation failed: {e}")
            return 0.001  # Minimum safe position
    
    def execute_prediction(self, prediction: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        """
        Execute limit order based on prediction
        
        Args:
            prediction: Prediction dict from RealtimePredictionEngine
            strategy: Current trading strategy
            
        Returns:
            Execution result
        """
        try:
            # Check if should execute
            decision = self.should_execute(prediction, strategy)
            
            if not decision["should_execute"]:
                logger.info(f"🚫 Prediction NOT executed: {decision['reason']}")
                for check in decision["checks_failed"]:
                    logger.info(f"   {check}")
                return {
                    "success": False,
                    "reason": decision["reason"],
                    "checks_failed": decision["checks_failed"]
                }
            
            # Log decision
            logger.success(f"✅ Prediction APPROVED for execution:")
            for check in decision["checks_passed"]:
                logger.info(f"   {check}")
            
            # Execute limit order
            direction = prediction["direction"]
            side = "BUY" if direction == "LONG" else "SELL"
            entry_price = prediction["entry_price"]
            position_size = decision["position_size"]
            
            # Prepare signal data
            signal_data = {
                "strategy": strategy,
                "confidence": prediction.get("calibrated_confidence", prediction.get("confidence", 0)),
                "expected_value": prediction.get("expected_value", 0),
                "bayesian_confidence": prediction.get("bayesian_confidence"),
                "stop_loss": prediction.get("stop_loss"),
                "take_profit": prediction.get("take_profit"),
                "reasoning": prediction.get("reasoning", []),
                "kelly_position_pct": prediction.get("kelly_position_pct"),
            }
            
            logger.info(f"🎯 EXECUTING {side} LIMIT ORDER:")
            logger.info(f"   Entry: ${entry_price:,.2f}")
            logger.info(f"   Size: {position_size} BTC")
            logger.info(f"   Stop Loss: ${prediction.get('stop_loss', 0):,.2f}")
            logger.info(f"   Take Profit: ${prediction.get('take_profit', 0):,.2f}")
            logger.info(f"   Confidence: {prediction.get('calibrated_confidence', 0):.1%}")
            logger.info(f"   Expected Value: {prediction.get('expected_value', 0):+.2%}")
            
            # Place the trade
            import time
            success = self.trading_execution.place_paper_trade(
                side=side,
                size=position_size,
                leverage=30,  # Default leverage
                signal_data=signal_data
            )
            
            if success:
                self.last_execution_time = time.time()
                self.executions_today += 1
                self.consecutive_losses = 0  # Reset on successful execution
                
                logger.success(f"✅ Limit order executed successfully!")
                
                # Add trade to dashboard
                try:
                    from core.services.dashboard_service import DashboardService
                    dashboard = DashboardService.get_global_instance()
                    if dashboard:
                        trade_display = {
                            "type": "LIMIT",
                            "side": side,
                            "status": "OPEN",
                            "entry_price": entry_price,
                            "size": position_size,
                            "stop_loss": prediction.get("stop_loss"),
                            "take_profit": prediction.get("take_profit"),
                            "confidence": prediction.get("calibrated_confidence", 0),
                            "expected_value": prediction.get("expected_value", 0),
                            "strategy": strategy,
                            "bayesian_confidence": prediction.get("bayesian_confidence"),
                            "kelly_position_pct": prediction.get("kelly_position_pct"),
                            "timestamp": time.time()
                        }
                        dashboard.add_trade(trade_display)
                        logger.debug("📊 Trade added to dashboard")
                except Exception as e:
                    logger.warning(f"⚠️ Could not add trade to dashboard: {e}")
                
                return {
                    "success": True,
                    "side": side,
                    "entry_price": entry_price,
                    "size": position_size,
                    "confidence": prediction.get("calibrated_confidence", 0),
                    "expected_value": prediction.get("expected_value", 0)
                }
            else:
                logger.error(f"❌ Limit order execution failed")
                return {
                    "success": False,
                    "reason": "Trade execution failed"
                }
                
        except Exception as e:
            logger.error(f"❌ Prediction execution error: {e}")
            return {
                "success": False,
                "reason": f"Error: {e}"
            }


# Global singleton
_global_prediction_executor = None


def get_global_prediction_executor(trading_execution=None, account_manager=None, session_manager=None) -> PredictionExecutor:
    """Get the global PredictionExecutor singleton instance"""
    global _global_prediction_executor
    if _global_prediction_executor is None:
        if not all([trading_execution, account_manager, session_manager]):
            raise ValueError("First initialization requires trading_execution, account_manager, and session_manager")
        _global_prediction_executor = PredictionExecutor(trading_execution, account_manager, session_manager)
    return _global_prediction_executor

