#!/usr/bin/env python3
"""
Reactive Execution Engine
Executes MARKET orders immediately when momentum breakouts are detected

Features:
- Real-time momentum monitoring
- Immediate market order execution
- Risk management (stop loss, take profit)
- Position tracking
- Prevents duplicate entries
"""

import time
from typing import Dict, Any, Optional
from loguru import logger
from config.config import TradingConfig

from .momentum_detector import MomentumDetector, MomentumSignal
from .position_sizer import PositionSizeCalculator


class ReactiveEngine:
    """
    Reactive engine that executes market orders on momentum breakouts
    
    Monitors momentum signals and executes trades immediately when detected.
    Works in parallel with the prediction engine (limit orders at S/R levels).
    """
    
    def __init__(self, api_manager=None):
        """
        Initialize reactive engine
        
        Args:
            api_manager: API manager for order execution (optional, for future integration)
        """
        self._momentum_detector = MomentumDetector()
        self._api_manager = api_manager
        self._active_positions: Dict[str, Dict[str, Any]] = {}
        self._last_check_time = 0.0
        self._check_interval = 2.0  # Check every 2 seconds for timely reaction
        self._enabled = True
        self._pending_orders: Dict[str, Dict[str, Any]] = {}  # Track pending market orders
        
        logger.info("⚡ Reactive Execution Engine initialized")
    
    def process_market_data(
        self,
        unified_data: Dict[str, Any],
        current_price: float,
        current_strategy: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process market data and execute trades if momentum detected
        
        Args:
            unified_data: Complete market analysis data
            current_price: Current market price
            
        Returns:
            Execution result if trade executed, None otherwise
        """
        try:
            # Throttle checks (every 2 seconds for timely reaction)
            current_time = time.time()
            if current_time - self._last_check_time < self._check_interval:
                return None
            
            self._last_check_time = current_time
            
            if not self._enabled:
                return None
            
            # Get ATR for calculations
            sr_data = unified_data["support_resistance"]  # Required (NO FALLBACKS)
            sr_metadata = sr_data["metadata"]  # Required (NO FALLBACKS)
            atr_5m = sr_metadata["atr_5m"]  # Required (NO FALLBACKS)
            
            if atr_5m <= 0:
                logger.debug("⚡ ATR unavailable - skipping momentum check")
                return None
            
            # Detect momentum
            signal = self._momentum_detector.detect_momentum(
                unified_data=unified_data,
                current_price=current_price,
                atr_5m=atr_5m
            )
            
            if not signal:
                return None
            
            # Check if we already have a position in this direction
            if self._has_active_position(signal.direction):
                logger.debug(f"⚡ Already have {signal.direction} position - skipping signal")
                return None
            
            # Check confidence threshold (must be high enough)
            # TradingConfig already imported at module level
            min_confidence = TradingConfig.MIN_MOMENTUM_CONFIDENCE
            if signal.confidence < min_confidence:
                logger.debug(f"⚡ Signal confidence too low: {signal.confidence:.1f}% (min: {min_confidence}%)")
                return None
            
            # Execute market order (use current_strategy if provided, else detect from unified_data)
            strategy_to_use = current_strategy or unified_data["strategy"]  # Required (NO FALLBACKS)
            execution_result = self._execute_momentum_trade(signal, current_price, strategy_to_use)
            
            if execution_result:
                logger.info(f"⚡ Momentum trade executed: {signal.direction} @ ${signal.entry_price:.2f} "
                           f"(confidence: {signal.confidence:.1f}%, expected move: {signal.expected_move_pct*100:.2f}%)")
                
                # Track position
                self._active_positions[signal.direction] = {
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "direction": signal.direction,
                    "opened_at": time.time(),
                    "signal": signal
                }
            
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Reactive engine processing failed: {e}")
            return None
    
    def _execute_momentum_trade(
        self,
        signal: MomentumSignal,
        current_price: float,
        strategy: str = "high_volatility"
    ) -> Optional[Dict[str, Any]]:
        """
        Call trade execution API for momentum trade (MARKET order)
        
        This method calls the API manager to place a market order.
        Actual execution logic is handled by the API manager/trade executor.
        
        Args:
            signal: Momentum signal
            current_price: Current market price
            strategy: Current trading strategy (from StrategyManager)
            
        Returns:
            Execution call result (order placed, not necessarily filled)
        """
        try:
            # Get strategy config (use provided strategy)
            if strategy not in TradingConfig.STRATEGY_CONFIGS:
                raise ValueError(f"Unknown strategy: {strategy} - NO FALLBACKS")
            strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]  # Required (NO FALLBACKS)
            
            if not strategy_config:
                logger.error("❌ No strategy config available for momentum trade")
                return None
            
            # Get position sizing parameters from strategy config - NO FALLBACKS
            base_position_size_pct = strategy_config["position_size"]
            
            # Validate position_size is valid for trading (NO FALLBACKS)
            if base_position_size_pct <= 0 or base_position_size_pct > 1.0:
                logger.warning(f"⚠️ Strategy '{strategy}' has invalid position_size ({base_position_size_pct}) - skipping momentum trade (strategy may be analysis-only)")
                return None
            
            leverage = strategy_config["max_leverage"]
            
            # Prepare order parameters
            order_side = "BUY" if signal.direction == "LONG" else "SELL"
            
            # Calculate position size AFTER confidence is available (similar to predictions)
            # Position sizing happens after confidence so confidence can influence position size
            # Signal already has confidence calculated
            current_balance = PositionSizeCalculator.get_balance_from_simulator()
            position_sizing = PositionSizeCalculator.calculate_position_size(
                balance=current_balance,
                base_position_size_pct=base_position_size_pct,
                risk_reward_ratio=signal.risk_reward_ratio,
                leverage=leverage,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,  # REQUIRED for liquidation risk calculation
                direction=signal.direction,  # REQUIRED for liquidation risk calculation
                confidence=signal.confidence  # Pass confidence for future confidence-based sizing (same logic as predictions)
            )
            
            # Extract calculated values
            position_size_btc = position_sizing["position_size_btc"]
            rr_multiplier = position_sizing["rr_multiplier"]
            adjusted_position_size_pct = position_sizing["adjusted_position_size_pct"]
            position_value_usd = position_sizing["position_value_usd"]
            
            # Get hyperliquid simulator for order placement
            # CRITICAL: Simulator is initialized in SystemInitializer (required for balance access)
            hyperliquid_simulator = None
            try:
                from core.services.system_initializer import get_system_initializer
                system_initializer = get_system_initializer()
                # Simulator should be available (initialized in SystemInitializer)
                if "hyperliquid_simulator" in system_initializer.singleton_systems:
                    hyperliquid_simulator = system_initializer.get_singleton_system("hyperliquid_simulator")
                else:
                    logger.warning("⚠️ Hyperliquid simulator not found in singleton systems - order placement will be logged only")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get Hyperliquid simulator: {e} - order placement will be logged only")
                hyperliquid_simulator = None
            
            # Prepare order metadata
            order_metadata = {
                "source": "reactive_engine",
                "signal_type": "momentum_breakout",
                "confidence": signal.confidence,
                "expected_move_pct": signal.expected_move_pct,
                "breakout_level": signal.breakout_level,
                "reasoning": signal.reasoning,
                "detected_at": signal.detected_at,
                "risk_reward_ratio": signal.risk_reward_ratio,
                "base_position_size_pct": base_position_size_pct,
                "rr_multiplier": rr_multiplier,
                "adjusted_position_size_pct": adjusted_position_size_pct,
                "position_size_btc": position_size_btc,
                "balance_at_entry": current_balance
            }
            
            # Call API manager to place market order (if available)
            # Note: This calls the execution API but doesn't execute actual trades
            # Actual execution logic is handled by the trade executor (not implemented yet)
            if self._api_manager:
                try:
                    # Hyperliquid simulator already fetched above
                    if hyperliquid_simulator and hasattr(hyperliquid_simulator, 'place_order'):
                        # Call place_order with proper position size
                        # TradingConfig already imported at module level
                        order_result = hyperliquid_simulator.place_order(
                            order_type="MARKET",
                            side=order_side,
                            size=position_size_btc,  # Calculated based on balance, position_size%, R:R, leverage
                            symbol=TradingConfig.SYMBOL,
                            price=None,  # Market order - no price needed
                            leverage=leverage,
                            stop_loss=signal.stop_loss,
                            take_profit=signal.take_profit,
                            metadata=order_metadata
                        )
                        
                        if "success" in order_result and order_result["success"]:
                            logger.info(f"⚡ MARKET order CALLED: {signal.direction} @ ${signal.entry_price:.2f} "
                                       f"(SL: ${signal.stop_loss:.2f}, TP: ${signal.take_profit:.2f})")
                            
                            # Track pending order
                            order_id = order_result["order_id"]  # Required (NO FALLBACKS)
                            self._pending_orders[order_id] = {
                                "signal": signal,
                                "order_result": order_result,
                                "called_at": time.time()
                            }
                            
                            return {
                                "success": True,
                                "order_called": True,
                                "order_id": order_id,
                                "order_type": "MARKET",
                                "direction": signal.direction,
                                "entry_price": signal.entry_price,
                                "stop_loss": signal.stop_loss,
                                "take_profit": signal.take_profit,
                                "base_position_size_pct": base_position_size_pct,
                                "rr_multiplier": rr_multiplier,
                                "adjusted_position_size_pct": adjusted_position_size_pct,
                                "position_size_btc": position_size_btc,
                                "leverage": leverage,
                                "confidence": signal.confidence,
                                "risk_reward_ratio": signal.risk_reward_ratio,
                                "expected_move_pct": signal.expected_move_pct,
                                "reasoning": signal.reasoning,
                                "called_at": time.time(),
                                "api_result": order_result
                            }
                        else:
                            error_msg = order_result["error"]  # Required (NO FALLBACKS)
                            logger.warning(f"⚠️ MARKET order call failed: {error_msg}")
                            return None
                    else:
                        logger.debug("⚡ API manager available but place_order not accessible - logging order call")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to call API manager for order execution: {e}")
            
            # If API manager not available, log the order call (for testing/development)
            logger.info(f"⚡ MARKET order CALLED (no API manager): {signal.direction} @ ${signal.entry_price:.2f} "
                       f"(SL: ${signal.stop_loss:.2f}, TP: ${signal.take_profit:.2f}, "
                       f"confidence: {signal.confidence:.1f}%)")
            
            # Return order call result (without actual execution)
            return {
                "success": True,
                "order_called": True,
                "order_type": "MARKET",
                "direction": signal.direction,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "base_position_size_pct": base_position_size_pct,
                "rr_multiplier": rr_multiplier,
                "adjusted_position_size_pct": adjusted_position_size_pct,
                "position_size_btc": position_size_btc,
                "leverage": leverage,
                "confidence": signal.confidence,
                "risk_reward_ratio": signal.risk_reward_ratio,
                "expected_move_pct": signal.expected_move_pct,
                "reasoning": signal.reasoning,
                "called_at": time.time(),
                "note": "API manager not available - order call logged only"
            }
            
        except Exception as e:
            logger.error(f"❌ Momentum trade execution call failed: {e}")
            return None
    
    def _has_active_position(self, direction: str) -> bool:
        """Check if we already have an active position in this direction"""
        return direction in self._active_positions
    
    def _has_pending_order(self, direction: str) -> bool:
        """Check if we have a pending order in this direction"""
        for order_id, order_data in self._pending_orders.items():
            signal = order_data["signal"]  # Required (NO FALLBACKS)
            if signal and signal.direction == direction:
                # Check if order is recent (within last 30 seconds)
                called_at = order_data["called_at"]  # Required (NO FALLBACKS)
                if time.time() - called_at < 30:
                    return True
        return False
    
    def close_position(self, direction: str, reason: str = "") -> Optional[Dict[str, Any]]:
        """
        Close an active position
        
        Args:
            direction: Position direction to close ("LONG" or "SHORT")
            reason: Reason for closing
            
        Returns:
            Close result if successful
        """
        if direction not in self._active_positions:
            return None
        
        position = self._active_positions.pop(direction)
        
        logger.info(f"⚡ Position closed: {direction} (reason: {reason})")
        
        return {
            "success": True,
            "direction": direction,
            "closed_at": time.time(),
            "reason": reason
        }
    
    def get_active_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active positions"""
        return self._active_positions.copy()
    
    def enable(self):
        """Enable reactive engine"""
        self._enabled = True
        logger.info("⚡ Reactive engine ENABLED")
    
    def disable(self):
        """Disable reactive engine"""
        self._enabled = False
        logger.info("⚡ Reactive engine DISABLED")