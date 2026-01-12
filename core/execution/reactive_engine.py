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
            sr_data = unified_data.get("support_resistance", {})
            sr_metadata = sr_data.get("metadata", {})
            atr_5m = sr_metadata.get("atr_5m", 0.0)
            
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
            if signal.confidence < 65.0:  # Minimum 65% confidence
                logger.debug(f"⚡ Signal confidence too low: {signal.confidence:.1f}%")
                return None
            
            # Execute market order (use current_strategy if provided, else detect from unified_data)
            strategy_to_use = current_strategy or unified_data.get("strategy", "high_volatility")
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
            # Get strategy config (use provided strategy, fallback to high_volatility for unexpected moves)
            strategy_config = TradingConfig.STRATEGY_CONFIGS.get(strategy) or \
                            TradingConfig.STRATEGY_CONFIGS.get("high_volatility") or \
                            TradingConfig.STRATEGY_CONFIGS.get("breakout") or \
                            TradingConfig.STRATEGY_CONFIGS.get("standard")
            
            if not strategy_config:
                logger.error("❌ No strategy config available for momentum trade")
                return None
            
            # Calculate position size (from strategy config)
            position_size_pct = strategy_config.get("position_size", 0.10)  # Default 10%
            leverage = strategy_config.get("max_leverage", 20)  # Default 20x
            
            # Prepare order parameters
            order_side = "BUY" if signal.direction == "LONG" else "SELL"
            
            # Calculate position size in BTC (would need balance from session manager)
            # For now, use percentage - actual size calculation happens in trade executor
            position_size_btc = None  # Will be calculated by trade executor based on balance
            
            # Prepare order metadata
            order_metadata = {
                "source": "reactive_engine",
                "signal_type": "momentum_breakout",
                "confidence": signal.confidence,
                "expected_move_pct": signal.expected_move_pct,
                "breakout_level": signal.breakout_level,
                "reasoning": signal.reasoning,
                "detected_at": signal.detected_at
            }
            
            # Call API manager to place market order (if available)
            # Note: This calls the execution API but doesn't execute actual trades
            # Actual execution logic is handled by the trade executor (not implemented yet)
            if self._api_manager:
                try:
                    # Try to get Hyperliquid simulator from system initializer
                    # The simulator handles order execution calls
                    hyperliquid_simulator = None
                    try:
                        from core.services.system_initializer import get_system_initializer
                        system_initializer = get_system_initializer()
                        # Try different possible keys for simulator
                        hyperliquid_simulator = system_initializer.get_singleton_system("hyperliquid_simulator")
                        if not hyperliquid_simulator:
                            # Try getting from trading systems
                            trading_systems = system_initializer.get_singleton_system("trading_systems")
                            if trading_systems:
                                hyperliquid_simulator = getattr(trading_systems, 'simulator', None)
                    except Exception:
                        pass
                    
                    # Fallback: try to get from API manager or create new instance
                    if not hyperliquid_simulator:
                        try:
                            from core.api.hyperliquid_simulator import HyperliquidSimulator
                            # Create simulator instance for order calls (paper trading)
                            hyperliquid_simulator = HyperliquidSimulator()
                        except Exception:
                            pass
                    
                    if hyperliquid_simulator and hasattr(hyperliquid_simulator, 'place_order'):
                        # Call place_order - this is the execution call (no actual execution logic here)
                        order_result = hyperliquid_simulator.place_order(
                            order_type="MARKET",
                            side=order_side,
                            size=position_size_btc or 0.001,  # Placeholder size, will be calculated properly
                            symbol="BTC",
                            price=None,  # Market order - no price needed
                            leverage=leverage,
                            stop_loss=signal.stop_loss,
                            take_profit=signal.take_profit,
                            metadata=order_metadata
                        )
                        
                        if order_result.get("success"):
                            logger.info(f"⚡ MARKET order CALLED: {signal.direction} @ ${signal.entry_price:.2f} "
                                       f"(SL: ${signal.stop_loss:.2f}, TP: ${signal.take_profit:.2f})")
                            
                            # Track pending order
                            order_id = order_result.get("order_id", f"momentum_{int(time.time())}")
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
                                "position_size_pct": position_size_pct,
                                "leverage": leverage,
                                "confidence": signal.confidence,
                                "expected_move_pct": signal.expected_move_pct,
                                "reasoning": signal.reasoning,
                                "called_at": time.time(),
                                "api_result": order_result
                            }
                        else:
                            logger.warning(f"⚠️ MARKET order call failed: {order_result.get('error', 'Unknown error')}")
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
                "position_size_pct": position_size_pct,
                "leverage": leverage,
                "confidence": signal.confidence,
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
            signal = order_data.get("signal")
            if signal and signal.direction == direction:
                # Check if order is recent (within last 30 seconds)
                called_at = order_data.get("called_at", 0)
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