#!/usr/bin/env python3
"""
Prediction-Based Trade Executor
Executes limit orders based on AI predictions with strategy-specific confidence thresholds
Now integrated with proper order lifecycle management
"""

import time
from typing import Dict, Any, Optional
from loguru import logger
from dataclasses import dataclass
from core.execution.order_lifecycle_manager import get_global_order_lifecycle_manager
# REMOVED: prediction_state_manager import - not needed for single prediction system


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
            min_confidence=0.50,  # 50% - USER SPECIFIED (minimum for execution)
            optimal_confidence=0.70,  # 70% - Ideal
            max_position_size=0.020,  # 0.020 BTC (~$2,400) - Adjusted for 20% position size
            min_ev_percent=0.05,  # 0.05% - FIXED: Match Probability Engine threshold
            require_bayesian=True,  # Must have Bayesian confirmation
            calibration_weight=0.8  # Heavily trust calibration
        ),
        "standard": StrategyThresholds(
            min_confidence=0.65,  # 65% - Moderate confidence
            optimal_confidence=0.75,  # 75% - Ideal
            max_position_size=0.01,  # 0.01 BTC (~$1,200) - Medium positions
            min_ev_percent=0.10,  # 0.10% - FIXED: Reasonable for standard strategy
            require_bayesian=True,  # Must have Bayesian confirmation
            calibration_weight=0.9  # Trust calibration heavily
        ),
        "range_trading": StrategyThresholds(
            min_confidence=0.52,  # 52% - USER SPECIFIED (mean reversion)
            optimal_confidence=0.65,  # 65% - Ideal
            max_position_size=0.015,  # 0.015 BTC (~$1,800) - Larger positions
            min_ev_percent=0.05,  # 0.05% - FIXED: Match Probability Engine threshold
            require_bayesian=False,  # S/R levels are primary
            calibration_weight=0.7  # Moderate calibration trust
        ),
        "trend_following": StrategyThresholds(
            min_confidence=0.60,  # 60% - USER SPECIFIED (trend confirmation)
            optimal_confidence=0.75,  # 75% - Ideal
            max_position_size=0.02,  # 0.02 BTC (~$2,400) - Large positions
            min_ev_percent=0.15,  # 0.15% - FIXED: Reasonable for trend following
            require_bayesian=True,  # Multi-signal confirmation
            calibration_weight=0.85  # High calibration trust
        ),
        "breakout": StrategyThresholds(
            min_confidence=0.58,  # 58% - USER SPECIFIED (extreme volatility)
            optimal_confidence=0.70,  # 70% - Ideal
            max_position_size=0.008,  # 0.008 BTC (~$960) - Medium-small
            min_ev_percent=0.20,  # 0.20% - FIXED: Reasonable for breakouts
            require_bayesian=True,  # Must confirm with multiple signals
            calibration_weight=0.9  # Trust calibration
        ),
        "low_volatility_range": StrategyThresholds(
            min_confidence=0.50,  # 50% - USER SPECIFIED (minimum for execution)
            optimal_confidence=0.65,  # 65% - Ideal
            max_position_size=0.012,  # 0.012 BTC (~$1,440) - Medium positions
            min_ev_percent=0.05,  # 0.05% - FIXED: Match Probability Engine threshold
            require_bayesian=False,  # S/R levels are primary in low volatility
            calibration_weight=0.6  # Lower calibration trust in low volatility
        ),
        "high_volatility": StrategyThresholds(
            min_confidence=0.55,  # 55% - USER SPECIFIED (high volatility)
            optimal_confidence=0.70,  # 70% - Ideal
            max_position_size=0.010,  # 0.010 BTC (~$1,200) - Adjusted for 10% position size
            min_ev_percent=0.12,  # 0.12% - FIXED: Reasonable for high volatility
            require_bayesian=True,  # Need confirmation in high volatility
            calibration_weight=0.8  # High calibration trust
        ),
        "spike_hunting": StrategyThresholds(
            min_confidence=0.70,  # 70% - USER SPECIFIED (high risk strategy)
            optimal_confidence=0.80,  # 80% - Ideal
            max_position_size=0.015,  # 0.015 BTC (~$1,800) - Adjusted for 15% position size
            min_ev_percent=0.25,  # 0.25% - FIXED: Reasonable for spike hunting
            require_bayesian=True,  # Must confirm with multiple signals
            calibration_weight=0.9  # Trust calibration heavily
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
                logger.error(f"❌ Unknown strategy: {strategy}. Available strategies: {list(self.STRATEGY_THRESHOLDS.keys())}")
                return {
                    "should_execute": False,
                    "reason": f"Unknown strategy: {strategy}",
                    "checks_passed": [],
                    "checks_failed": [f"❌ Unknown strategy: {strategy}"]
                }
            
            checks_passed = []
            checks_failed = []
            
            # Validate thresholds object
            if not hasattr(thresholds, 'min_confidence') or thresholds.min_confidence is None:
                logger.error(f"❌ Thresholds object is invalid: {thresholds}")
                return {
                    "should_execute": False,
                    "reason": "Invalid thresholds object",
                    "checks_passed": [],
                    "checks_failed": ["❌ Invalid thresholds object"]
                }
            
            # 1. CHECK: Confidence threshold (Bayesian fusion of main + additional signals)
            main_confidence = prediction.get("confidence", 0) or 0
            bayesian_confidence = prediction.get("bayesian_confidence", 0) or 0
            
            if main_confidence is None or main_confidence <= 0:
                logger.error(f"❌ Main confidence is None or invalid in prediction: {prediction}")
                main_confidence = 0.0
            
            # Apply Bayesian fusion if available
            if bayesian_confidence > 0:
                # Weighted combination: 70% main + 30% bayesian
                # This gives more weight to our comprehensive analysis while incorporating additional validation
                confidence = (main_confidence * 0.7) + (bayesian_confidence * 0.3)
                logger.debug(f"🔍 Bayesian Fusion: main={main_confidence:.1%} + bayesian={bayesian_confidence:.1%} = {confidence:.1%}")
            else:
                # Use main confidence if no Bayesian data available
                confidence = main_confidence
                logger.debug(f"🔍 Confidence: {confidence:.1%} (no Bayesian fusion available)")
            
            # FIXED: Strategy-specific confidence handling
            # Range trading strategies can work with lower confidence due to mean reversion nature
            if strategy == "range_trading":
                # Range trading is more forgiving - allow slightly lower confidence
                effective_threshold = thresholds.min_confidence * 0.95  # 5% tolerance
                if confidence >= effective_threshold:
                    checks_passed.append(f"✅ Range trading confidence {confidence:.1%} >= {effective_threshold:.1%}")
                else:
                    checks_failed.append(f"❌ Range trading confidence {confidence:.1%} < {effective_threshold:.1%}")
            else:
                # Standard threshold for other strategies
                if confidence >= thresholds.min_confidence:
                    checks_passed.append(f"✅ Confidence {confidence:.1%} >= {thresholds.min_confidence:.1%}")
                else:
                    checks_failed.append(f"❌ Confidence {confidence:.1%} < {thresholds.min_confidence:.1%}")
            
            # Debug: Log final confidence
            logger.debug(f"🔍 Final Confidence: {confidence:.1%} (threshold: {thresholds.min_confidence:.1%})")
            
            # 3. CHECK: Rate limiting
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
            entry_price = prediction.get("entry_price", 120000)
            if entry_price is None:
                logger.error(f"❌ Entry price is None in prediction: {prediction}")
                entry_price = 120000  # Default fallback
            
            min_balance_required = thresholds.max_position_size * entry_price * 0.1  # 10% margin
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
            
            # Get EV score from prediction
            ev_percent = prediction.get("expected_value", 0.0) or 0.0
            
            return {
                "should_execute": should_execute,
                "reason": "All checks passed" if should_execute else f"{len(checks_failed)} checks failed",
                "checks_passed": checks_passed,
                "checks_failed": checks_failed,
                "confidence_score": confidence,
                "ev_score": ev_percent,
                "position_size": self._calculate_position_size(prediction, thresholds, confidence)
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
            
            # Handle None values
            if kelly_position_dollars is None:
                logger.warning(f"⚠️ Kelly position dollars is None - using default")
                kelly_position_dollars = 500
            if entry_price is None:
                logger.warning(f"⚠️ Entry price is None in position sizing - using default")
                entry_price = 120000
            
            kelly_position_btc = kelly_position_dollars / entry_price
            
            # Cap at strategy max
            position_size = min(kelly_position_btc, thresholds.max_position_size)
            
            # Scale by confidence (if above optimal, use full Kelly, otherwise scale down)
            if confidence is not None and confidence < thresholds.optimal_confidence:
                confidence_ratio = confidence / thresholds.optimal_confidence
                position_size *= confidence_ratio
            elif confidence is None:
                logger.warning(f"⚠️ Confidence is None in position sizing - using default scaling")
                position_size *= 0.5  # Default 50% scaling when confidence is None
            
            # Minimum position size: 0.001 BTC (~$120)
            position_size = max(0.001, position_size)
            
            return round(position_size, 4)
            
        except Exception as e:
            logger.error(f"❌ Position size calculation failed: {e}")
            return 0.001  # Minimum safe position
    
    def execute_prediction(self, prediction: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        """
        Execute limit order based on prediction using proper order lifecycle
        
        Args:
            prediction: Prediction dict from RealtimePredictionEngine
            strategy: Current trading strategy
            
        Returns:
            Execution result
        """
        try:
            # Get lifecycle managers
            lifecycle_manager = get_global_order_lifecycle_manager()
            
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
            
            # Extract prediction parameters
            direction = prediction["direction"]
            side = "BUY" if direction == "LONG" else "SELL"
            entry_price = prediction["entry_price"]
            position_size = decision["position_size"]
            current_price = prediction.get("current_price", entry_price)
            
            # Check if we can place order in this direction
            if not lifecycle_manager.can_place_order(side):
                logger.warning(f"🚫 Cannot place {side} order: conflicting active orders/positions")
                return {
                    "success": False,
                    "reason": f"Conflicting {side} order/position active",
                    "checks_failed": [f"❌ Conflicting {side} order/position active"]
                }
            
            # FIXED: Use existing prediction instead of creating new one
            # The prediction executor should execute the existing singleton prediction
            # Generate a unique ID for this execution attempt
            prediction_id = f"exec_{int(time.time() * 1000)}"
            
            logger.debug(f"🔄 Executing existing prediction: {prediction_id}")
            
            # Place limit order through lifecycle manager
            order_id = lifecycle_manager.place_limit_order(prediction, current_price)
            if not order_id:
                logger.error(f"❌ Failed to place limit order")
                return {
                    "success": False,
                    "reason": "Order placement failed",
                    "checks_failed": ["❌ Order placement failed"]
                }
            
            # Order placed successfully
            
            logger.info(f"🎯 LIMIT ORDER PLACED: {side} {position_size} BTC @ ${entry_price:,.2f}")
            logger.info(f"   Prediction ID: {prediction_id}")
            logger.info(f"   Order ID: {order_id}")
            logger.info(f"   Current Price: ${current_price:,.2f}")
            logger.info(f"   Strategy: {strategy}")
            logger.info(f"   Confidence: {prediction.get('confidence', 0):.1%}")
            
            # Add to dashboard (PENDING status)
            try:
                from core.services.dashboard_service import DashboardService
                dashboard = DashboardService.get_global_instance()
                if dashboard:
                    trade_display = {
                        "type": "LIMIT",
                        "side": side,
                        "status": "PENDING",
                        "entry_price": entry_price,
                        "size": position_size,
                        "stop_loss": prediction.get("stop_loss"),
                        "take_profit": prediction.get("take_profit"),
                        "confidence": prediction.get("calibrated_confidence", 0),
                        "expected_value": prediction.get("expected_value", 0),
                        "strategy": strategy,
                        "bayesian_confidence": prediction.get("bayesian_confidence"),
                        "kelly_position_pct": prediction.get("kelly_position_pct"),
                        "prediction_id": prediction_id,
                        "order_id": order_id,
                        "timestamp": time.time()
                    }
                    dashboard.add_trade(trade_display)
                    logger.debug("📊 Pending order added to dashboard")
            except Exception as e:
                logger.warning(f"⚠️ Could not add pending order to dashboard: {e}")
            
            return {
                "success": True,
                "side": side,
                "entry_price": entry_price,
                "size": position_size,
                "confidence": prediction.get("calibrated_confidence", 0),
                "expected_value": prediction.get("expected_value", 0),
                "prediction_id": prediction_id,
                "order_id": order_id,
                "status": "PENDING"
            }
            
        except Exception as e:
            logger.error(f"❌ Prediction execution failed: {e}")
            return {
                "success": False,
                "reason": f"Execution error: {e}",
                "checks_failed": [f"❌ Execution error: {e}"]
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

