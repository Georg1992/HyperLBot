#!/usr/bin/env python3
"""
Trading Execution Module
Contains trade execution and position management methods extracted from hybrid_paper_trading_bot.py
"""

import time
import json
from typing import Dict, Any, List, Optional
from loguru import logger

from core.constants import constants, MagicNumbers, trading_constants, time_constants

class TradingExecution:
    """Trading execution and position management methods"""
    
    def __init__(self, bot_instance):
        """Initialize with reference to main bot instance"""
        self.bot = bot_instance
        self.magic_numbers = MagicNumbers()
    
    def place_paper_trade(self, side: str, size: float = trading_constants.DEFAULT_POSITION_SIZE, leverage: int = trading_constants.DEFAULT_LEVERAGE, signal_data: Dict = None) -> bool:
        """Place a PREDICTIVE paper trade using predicted entry points and time-based order management"""
        try:
            hyperliquid_price = self.bot.get_hyperliquid_price()
            if not hyperliquid_price:
                return False
            
            # Use optimal parameters from variability analysis if available
            if signal_data and "optimal_params" in signal_data:
                optimal_params = signal_data["optimal_params"]
                size = optimal_params["position_size"]
                leverage = optimal_params["leverage"]
            
            # Ensure leverage doesn't exceed Hyperliquid limit
            leverage = min(leverage, self.bot.leverage_settings["max_leverage"])
            
            # Use PREDICTED entry price from signal data
            if signal_data and "entry_price" in signal_data:
                predicted_entry_price = signal_data["entry_price"]
                entry_timeframe = signal_data.get("entry_timeframe", 20)  # minutes
                prediction_type = signal_data.get("prediction_type", "UNKNOWN")
                prediction_confidence = signal_data.get("prediction_confidence", self.magic_numbers.DEFAULT_CONFIDENCE)
                
                logger.info(f"🔮 Placing PREDICTIVE {side} LIMIT trade:")
                logger.info(f"   Prediction Type: {prediction_type}")
                logger.info(f"   Predicted Entry: ${predicted_entry_price:,.2f}")
                logger.info(f"   Current Price: ${hyperliquid_price:,.2f}")
                logger.info(f"   Confidence: {prediction_confidence*100:.1f}%")
                logger.info(f"   Expected Timeframe: {entry_timeframe} minutes")
                
                # Use predicted entry price as limit price
                limit_price = predicted_entry_price
            else:
                # Fallback to smart limit price calculation
                limit_price = self._calculate_smart_limit_price(side, hyperliquid_price)
                entry_timeframe = 20
                prediction_type = "SMART_LIMIT"
                prediction_confidence = self.magic_numbers.DEFAULT_CONFIDENCE
                
                logger.info(f"📝 Placing HYBRID PAPER {side} LIMIT trade:")
                logger.info(f"   Hyperliquid Price: ${hyperliquid_price:,.2f}")
                logger.info(f"   Limit Price: ${limit_price:,.2f}")
            
            # Calculate position value in USD
            position_value_usd = size * limit_price
            
            logger.info(f"   Size: {size} BTC (${position_value_usd:,.2f})")
            logger.info(f"   Leverage: {leverage}x")
            logger.info(f"   Required Margin: ${position_value_usd/leverage:.2f}")
            logger.info(f"   Paper Balance: ${self.bot.paper_balance:.2f}")
            logger.info(f"   Order Type: LIMIT (Lower fees than MARKET!)")
            
            # Update simulator with real order book data
            try:
                orderbook = self.bot.hyperliquid_api.get_orderbook("BTC")
                if orderbook and not orderbook.get('error'):
                    self.bot.hyperliquid_simulator.update_order_book(orderbook)
            
            except Exception as e:
                logger.warning(f"⚠️ Could not update simulator order book: {e}")
            
            # Use enhanced Hyperliquid simulator for realistic order execution
            execution_result = self.bot.hyperliquid_simulator.simulate_order_execution(
                order_type="LIMIT",
                side=side,
                size=size,
                price=limit_price,
                leverage=leverage
            )
            
            if not execution_result.get("success", False):
                error_msg = f"Paper trade failed: {execution_result.get('error', 'Unknown error')}"
                logger.error(f"❌ {error_msg}")
                
                # Log error to JSON file
                self.bot.trading_logger.log_error({
                    "error_type": "trade_execution_failed",
                    "message": error_msg,
                    "trade_id": f"hybrid_trade_{len(self.bot.trade_history) + 1}",
                    "side": side,
                    "size": size,
                    "leverage": leverage,
                    "paper_balance": self.bot.paper_balance,
                    "required_margin": size * hyperliquid_price / leverage
                })
                return False
            
            # Create position record with prediction data and market analysis
            position = {
                "trade_id": f"hybrid_trade_{len(self.bot.trade_history) + 1}",
                "side": side,
                "entry_price": execution_result.get("execution_price", limit_price),
                "limit_price": limit_price,
                "size": size,
                "leverage": leverage,
                "entry_time": time.time(),
                "entry_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "fees": execution_result.get("fees", {"fee_amount": 0, "fee_type": "maker"}),
                "signal_data": signal_data,
                "target_price": hyperliquid_price * self.magic_numbers.PROFIT_TARGET_MULTIPLIER if side == "BUY" else hyperliquid_price * self.magic_numbers.STOP_LOSS_MULTIPLIER,  # 2% target
                "stop_price": hyperliquid_price * self.magic_numbers.STOP_LOSS_MULTIPLIER if side == "BUY" else hyperliquid_price * self.magic_numbers.PROFIT_TARGET_MULTIPLIER,  # 2% stop
                "current_stop_loss": hyperliquid_price * self.magic_numbers.STOP_LOSS_MULTIPLIER if side == "BUY" else hyperliquid_price * self.magic_numbers.PROFIT_TARGET_MULTIPLIER,
                "status": "OPEN",
                "order_type": "PREDICTIVE_LIMIT",
                "prediction_type": prediction_type,
                "prediction_confidence": prediction_confidence,
                "entry_timeframe": entry_timeframe,
                "time_to_execution": execution_result.get("time_to_execution", 0),
                "order_status": execution_result.get("order_status", "FILLED"),
                "original_market_analysis": self.bot.yahoo_analysis.copy(),  # Store original analysis for comparison
                "quality_evaluation": signal_data.get("quality_evaluation", {}),
                "stop_adjustment_count": 0,
                "partial_closes": [],
                "current_pnl_pct": 0.0,
                # Win-back metadata
                "is_winback_trade": signal_data.get("is_winback_trade", False),
                "winback_data": signal_data.get("winback_data", {}),
                "defensive_mode": signal_data.get("defensive_mode", False),
                "strategy": self.bot.strategy_name
            }
            
            # Add to open positions
            self.bot.open_positions.append(position)
            
            # Update account manager with open positions
            try:
                from core.account_manager import account_manager
                account_manager.update_open_positions(self.bot.open_positions)
                # Updated account manager with open positions
            except Exception as e:
                logger.error(f"❌ Failed to update account manager: {e}")
            
            # Save positions using trade state manager
            from core.trade_state_manager import trade_state_manager
            trade_state_manager.save_open_positions(self.bot.open_positions)
            
            # Prepare trade data for logging
            trade_data = {
                "timestamp": time.time(),
                "datetime": time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "trade_id": position["trade_id"],
                "side": side,
                "price": execution_result.get("execution_price", limit_price),
                "limit_price": limit_price,
                "size": size,
                "leverage": leverage,
                "order_type": "LIMIT",
                "fees": execution_result.get("fees", {"fee_amount": 0, "fee_type": "maker"}),
                "price_improvement": execution_result.get("slippage", 0),
                "signal_data": signal_data,
                "order_result": {"status": "ok", "paper_trade": True, "hybrid": True, "limit_order": True},
                "hyperliquid_price": hyperliquid_price,
                "support": signal_data.get("support_5m") if signal_data else None,
                "resistance": signal_data.get("resistance_5m") if signal_data else None,
                "trend_5m": signal_data.get("trend_5m") if signal_data else None,
                "trend_1h": signal_data.get("trend_1h") if signal_data else None,
                "variability_score": None,  # Variability analysis is handled separately
                "market_condition": None,  # Market condition is available in enhanced_analysis
                "signal_reason": signal_data.get("reason") if signal_data else None,
                "profit_target": position["target_price"],
                "stop_loss": position["stop_price"],
                "risk_level": "STANDARD",  # Risk level is determined by variability analyzer separately
                "strategy": self.bot.strategy_name
            }
            
            # Log the trade
            self.bot.trading_logger.log_trade(trade_data)
            
            # Add trade to session manager
            if hasattr(self.bot, 'session_manager'):
                self.bot.session_manager.add_session_trade(trade_data)
            
            # Trade and balance updates handled by AccountManager (SimpleRTM integration)
            
            self.bot.trade_history.append(trade_data)
            self.bot.fee_manager.record_trade_fees(trade_data)
            self.bot.last_trade_time = time.time()
            
            if prediction_type != "SMART_LIMIT":
                logger.success(f"✅ PREDICTIVE {side} LIMIT trade placed successfully!")
                logger.info(f"   Prediction Type: {prediction_type}")
                logger.info(f"   Prediction Confidence: {prediction_confidence:.1f}%")
                logger.info(f"   Predicted Entry: ${limit_price:,.2f}")
                logger.info(f"   Actual Execution: ${execution_result.get('execution_price', limit_price):,.2f}")
                logger.info(f"   Entry Timeframe: {entry_timeframe} minutes")
            else:
                logger.success(f"✅ HYBRID PAPER {side} LIMIT trade placed successfully!")
                logger.info(f"   Limit Price: ${limit_price:,.2f}")
                logger.info(f"   Execution Price: ${execution_result.get('execution_price', limit_price):,.2f}")
            
            logger.info(f"   Position Value: ${position_value_usd:,.2f}")
            logger.info(f"   Slippage: {execution_result.get('slippage', 0)*100:.3f}%")
            logger.info(f"   Fees: ${execution_result.get('fees', {}).get('fee_amount', 0):.4f} ({execution_result.get('fees', {}).get('fee_type', 'maker')})")
            logger.info(f"   Remaining Balance: ${self.bot.paper_balance:.2f}")
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Failed to place hybrid paper trade: {e}")
            self.bot.trading_logger.log_error({
                "type": "hybrid_paper_trade_error",
                "message": str(e),
                "details": {
                    "side": side,
                    "size": size,
                    "leverage": leverage,
                    "signal_data": signal_data
                }
            })
            return False
    
    def _calculate_smart_limit_price(self, side: str, current_price: float) -> float:
        """Calculate smart limit price based on side and current price"""
        if side == "BUY":
            # For buy orders, set limit slightly below current price
            return current_price * trading_constants.BUY_PRICE_ADJUSTMENT  # 0.1% below current price
        else:
            # For sell orders, set limit slightly above current price
            return current_price * trading_constants.SELL_PRICE_ADJUSTMENT  # 0.1% above current price
    
    def _validate_trade_risk(self, side: str, size: float, current_price: float, signal_data: Dict = None) -> bool:
        """Validate trade risk parameters"""
        try:
            # Check minimum position size
            if size < self.magic_numbers.MIN_POSITION_SIZE:
                logger.warning(f"⚠️ Position size too small: {size} < {self.magic_numbers.MIN_POSITION_SIZE}")
                return False
            
            # Check maximum position size
            if size > self.magic_numbers.MAX_POSITION_SIZE:
                logger.warning(f"⚠️ Position size too large: {size} > {self.magic_numbers.MAX_POSITION_SIZE}")
                return False
            
            # Check signal confidence if available
            if signal_data:
                confidence = signal_data.get("confidence", 0)
                if confidence < self.magic_numbers.MIN_SIGNAL_CONFIDENCE:
                    logger.warning(f"⚠️ Signal confidence too low: {confidence:.2f} < {self.magic_numbers.MIN_SIGNAL_CONFIDENCE}")
                    return False
            
            # Check if we have too many open positions
            if len(self.bot.open_positions) >= self.magic_numbers.MAX_OPEN_POSITIONS:
                logger.warning(f"⚠️ Too many open positions: {len(self.bot.open_positions)} >= {self.magic_numbers.MAX_OPEN_POSITIONS}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Risk validation failed: {e}")
            return False
    
    def close_paper_position(self, position: Dict, exit_reason: str, exit_price: float):
        """Close a paper trading position using enhanced Hyperliquid simulator"""
        try:
            entry_price = position["entry_price"]
            side = position["side"]
            size = position["size"]
            leverage = position["leverage"]
            
            # Update simulator with real order book data
            try:
                orderbook = self.bot.hyperliquid_api.get_orderbook("BTC")
                if orderbook and not orderbook.get('error'):
                    self.bot.hyperliquid_simulator.update_order_book(orderbook)
            
            except Exception as e:
                logger.warning(f"⚠️ Could not update simulator order book: {e}")
            
            # Use enhanced Hyperliquid simulator for realistic exit execution
            exit_side = "SELL" if side == "BUY" else "BUY"  # Opposite of entry
            execution_result = self.bot.hyperliquid_simulator.simulate_order_execution(
                order_type="MARKET",  # Market order for exit
                side=exit_side,
                size=size,
                leverage=leverage
            )
            
            if not execution_result.get("success", False):
                logger.error(f"❌ Position close failed: {execution_result.get('error', 'Unknown error')}")
                return False
            
            # Use execution price from simulator or fallback to provided exit price
            actual_exit_price = execution_result.get("execution_price", exit_price)
            
            # Calculate P&L
            if side == "BUY":
                price_change = (actual_exit_price - entry_price) / entry_price
            else:
                price_change = (entry_price - actual_exit_price) / entry_price
            
            # Apply leverage
            pnl_pct = price_change * leverage
            pnl_amount = size * entry_price * leverage * pnl_pct
            
            # Calculate fees using simulator results
            exit_fees = execution_result.get("fees", {"fee_amount": 0, "fee_type": "taker"})
            exit_fee_amount = exit_fees.get("fee_amount", 0) if isinstance(exit_fees, dict) else exit_fees
            
            # Handle entry fees from position
            entry_fees = position.get("fees", {})
            if isinstance(entry_fees, dict):
                entry_fee_amount = entry_fees.get("fee_amount", 0)
            else:
                entry_fee_amount = entry_fees or 0.0
            
            total_fees = entry_fee_amount + exit_fee_amount
            
            # Net P&L
            net_pnl = pnl_amount - total_fees
            
            # Update balance
            self.bot.paper_balance += net_pnl
            
            # Update account manager if available
            if self.bot.account_manager and self.bot.account_manager.account_data:
                self.bot.account_manager.update_balance(self.bot.paper_balance, net_pnl)
            
            # Update session manager with new balance
            if hasattr(self.bot, 'session_manager'):
                self.bot.session_manager.update_session_balance(self.bot.paper_balance, f"Position closed: {exit_reason}")
            
            # Update current balance in session metadata for dashboard
            self.bot.trading_logger.update_current_balance(self.bot.paper_balance)
            
            # Update position
            position.update({
                "exit_price": actual_exit_price,
                "exit_time": time.time(),
                "exit_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_reason": exit_reason,
                "pnl_pct": pnl_pct,
                "pnl_amount": pnl_amount,
                "total_fees": total_fees,
                "net_pnl": net_pnl,
                "status": "CLOSED",
                "was_profitable": net_pnl > 0,
                "execution_result": execution_result
            })
            
            # Move to closed positions
            self.bot.open_positions.remove(position)
            self.bot.closed_positions.append(position)
            
            # Update trade result in logger
            trade_result = {
                "trade_id": position["trade_id"],
                "side": position["side"],
                "entry_price": position["entry_price"],
                "exit_price": actual_exit_price,
                "size": position["size"],
                "leverage": position["leverage"],
                "confidence": position.get("confidence", 0),
                "profit_loss": pnl_amount,
                "profit_loss_pct": pnl_pct,
                "fees_paid": total_fees,
                "net_profit_loss": net_pnl,
                "pnl": net_pnl,
                "pnl_pct": pnl_pct,
                "entry_time": position["entry_time"],
                "exit_time": position["exit_time"],
                "holding_time": position["exit_time"] - position["entry_time"],
                "exit_reason": exit_reason,
                "was_profitable": net_pnl > 0,
                "balance_after": self.bot.paper_balance,
                "is_winback_trade": position.get("is_winback_trade", False),
                "winback_data": position.get("winback_data", {}),
                "timestamp": time.time(),
                "strategy": position.get("strategy", self.bot.strategy_name),
                "execution_result": execution_result
            }
            
            # Update account manager with open positions
            try:
                from core.account_manager import account_manager
                account_manager.update_open_positions(self.bot.open_positions)
                account_manager.add_trade(trade_result)
                # Updated account manager: position closed
            except Exception as e:
                logger.error(f"❌ Failed to update account manager on position close: {e}")
            
            # Close position using trade state manager
            entry_amount = size * entry_price
            exit_data = {
                "exit_price": actual_exit_price,
                "exit_time": time.time(),
                "exit_reason": exit_reason,
                "pnl": net_pnl,
                "pnl_pct": (net_pnl / entry_amount) * 100 if entry_amount > 0 else 0,
                "fees": exit_fee_amount
            }
            
            # Use trade state manager to close position
            from core.trade_state_manager import trade_state_manager
            trade_state_manager.close_position(position["trade_id"], exit_data)
            
            self.bot.trading_logger.update_trade_result(position["trade_id"], trade_result)
            
            # Trade result logged above
            
            # Trade and balance updates handled by AccountManager (SimpleRTM integration)
            
            # Calculate position value in USD
            position_value_usd = size * entry_price
            
            logger.info(f"📊 Position closed: {position['trade_id']}")
            logger.info(f"   {side} {size} BTC (${position_value_usd:,.2f}) @ ${entry_price:,.2f} → ${actual_exit_price:,.2f}")
            logger.info(f"   P&L: {pnl_pct*100:.2f}% (${pnl_amount:.4f})")
            logger.info(f"   Net P&L: ${net_pnl:.4f} (fees: ${total_fees:.4f})")
            logger.info(f"   Slippage: {execution_result.get('slippage', 0)*100:.3f}%")
            logger.info(f"   Reason: {exit_reason}")
            logger.info(f"   Paper Balance: ${self.bot.paper_balance:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Position closure failed: {e}")
            return False
    
    def check_position_exits(self, hyperliquid_price: float, current_analysis: Dict[str, Any] = None):
        """Advanced position management with dynamic stops and intelligent exits"""
        positions_to_close = []
        positions_to_adjust = []
        
        for position in self.bot.open_positions:
            entry_price = position["entry_price"]
            side = position["side"]
            target_price = position["target_price"]
            stop_price = position.get("current_stop_loss", position["stop_price"])
            
            # Update current P&L for position
            if side == "BUY":
                current_pnl_pct = (hyperliquid_price - entry_price) / entry_price
            else:
                current_pnl_pct = (entry_price - hyperliquid_price) / entry_price
            
            position["current_pnl_pct"] = current_pnl_pct
            
            # 1. CHECK FOR TARGET HIT
            if target_price:
                if (side == "BUY" and hyperliquid_price >= target_price) or (side == "SELL" and hyperliquid_price <= target_price):
                    positions_to_close.append((position, "TARGET_HIT", target_price))
                    continue
            
            # 2. CHECK FOR STOP LOSS
            if stop_price:
                if (side == "BUY" and hyperliquid_price <= stop_price) or (side == "SELL" and hyperliquid_price >= stop_price):
                    positions_to_close.append((position, "STOP_LOSS", stop_price))
                    continue
            
            # 3. CHECK FOR PARTIAL CLOSE OPPORTUNITIES
            if current_analysis:
                partial_close_decision = self.bot.trade_manager.should_partial_close(position, hyperliquid_price)
                if partial_close_decision["should_partial_close"]:
                    logger.info(f"💰 Partial close opportunity: {partial_close_decision['reason']}")
                    # Implement partial close logic
                    self._execute_partial_close(position, partial_close_decision, hyperliquid_price)
                    continue  # Skip other checks after partial close
            
            # 4. CHECK FOR SCALING OPPORTUNITIES
            if current_analysis:
                scale_decision = self.bot.trade_manager.should_scale_in_position(position, hyperliquid_price, current_analysis)
                if scale_decision["should_scale"]:
                    logger.info(f"📈 Scaling opportunity: {scale_decision['reason']}")
                    # Implement scaling logic
                    self._execute_scale_in(position, scale_decision, hyperliquid_price)
                    continue  # Skip other checks after scaling
            
            # 5. CHECK FOR EMERGENCY CLOSE
            if current_analysis:
                emergency_decision = self.bot.trade_manager.should_emergency_close(position, hyperliquid_price, current_analysis)
                if emergency_decision["should_emergency_close"]:
                    positions_to_close.append((position, "EMERGENCY_CLOSE", hyperliquid_price))
                    logger.warning(f"🚨 Emergency close: {emergency_decision['reason']}")
                    continue
            
            # 5. CHECK FOR DYNAMIC STOP ADJUSTMENT
            if current_analysis:
                stop_adjustment = self.bot.trade_manager.calculate_dynamic_stops(position, hyperliquid_price, current_analysis)
                if stop_adjustment["should_adjust"]:
                    positions_to_adjust.append((position, stop_adjustment))
                
                # Enhanced market condition tracking
                original_analysis = position.get("original_market_analysis", {})
                if original_analysis:
                    condition_change = self.bot.trade_manager._analyze_condition_change(original_analysis, current_analysis)
                    if condition_change["favorable"]:
                        logger.info(f"📈 Market conditions improved for {position['trade_id']}: {condition_change['reason']}")
                    elif not condition_change["favorable"] and condition_change["confidence"] > self.magic_numbers.HIGH_CONFIDENCE_THRESHOLD:
                        logger.warning(f"📉 Market conditions deteriorated for {position['trade_id']}: {condition_change['reason']}")
            
            # 6. CHECK POSITION HEAT
            heat_analysis = self.bot.trade_manager.calculate_position_heat(position, hyperliquid_price)
            if heat_analysis["heat_level"] == "CRITICAL":
                logger.warning(f"🔥 CRITICAL position heat: {heat_analysis['heat_pct']*100:.1f}% - {position['trade_id']}")
            elif heat_analysis["heat_level"] == "HIGH":
                logger.info(f"⚠️ HIGH position heat: {heat_analysis['heat_pct']*100:.1f}% - {position['trade_id']}")
            
            # 7. CHECK FOR TIME-BASED EXIT (1 hour max)
            if time.time() - position["entry_time"] > time_constants.SECONDS_IN_HOUR:  # 1 hour
                positions_to_close.append((position, "TIME_EXIT", hyperliquid_price))
                continue
        
        # Apply stop adjustments
        for position, adjustment_result in positions_to_adjust:
            updated_position = self.bot.trade_manager.update_position_with_adjustment(position, adjustment_result)
            # Update position in our list
            position_index = next((i for i, p in enumerate(self.bot.open_positions) if p["trade_id"] == position["trade_id"]), None)
            if position_index is not None:
                self.bot.open_positions[position_index] = updated_position
        
        # Close positions
        for position, exit_reason, exit_price in positions_to_close:
            self.close_paper_position(position, exit_reason, exit_price)
    
    def _execute_partial_close(self, position: Dict, partial_close_decision: Dict, current_price: float):
        """Execute partial close of position"""
        try:
            # Simple partial close implementation
            close_percentage = partial_close_decision.get("close_percentage", self.magic_numbers.PARTIAL_CLOSE_MULTIPLIER)
            close_size = position["size"] * close_percentage
            
            logger.info(f"💰 Partial close: {close_percentage*100:.1f}% of position {position['trade_id']}")
            logger.info(f"   Close size: {close_size} BTC")
            logger.info(f"   Reason: {partial_close_decision.get('reason', 'Unknown')}")
            
            # Update position size
            position["size"] -= close_size
            position["partial_closes"].append({
                "size": close_size,
                "price": current_price,
                "timestamp": time.time(),
                "reason": partial_close_decision.get("reason", "Unknown")
            })
            
            # Log partial close
            self.bot._update_simple_rtm_activity(f"💰 Partial close: {close_percentage*100:.1f}% of {position['trade_id']}", "INFO")
            
        except Exception as e:
            logger.error(f"❌ Failed to execute partial close: {e}")

    def _execute_scale_in(self, position: Dict, scale_decision: Dict, current_price: float):
        """Execute scale-in to position"""
        try:
            # Simple scale-in implementation
            scale_size = scale_decision.get("scale_size", position["size"] * self.magic_numbers.SCALE_SIZE_MULTIPLIER)
            scale_price = current_price
            
            logger.info(f"📈 Scale-in: {scale_size} BTC to position {position['trade_id']}")
            logger.info(f"   Scale price: ${scale_price:,.2f}")
            logger.info(f"   Reason: {scale_decision.get('reason', 'Unknown')}")
            
            # Update position (simple average price calculation)
            total_size = position["size"] + scale_size
            total_value = (position["size"] * position["entry_price"]) + (scale_size * scale_price)
            new_entry_price = total_value / total_size if total_size > 0 else position["entry_price"]
            
            position["size"] = total_size
            position["entry_price"] = new_entry_price
            
            # Log scale-in
            self.bot._update_simple_rtm_activity(f"📈 Scale-in: {scale_size} BTC to {position['trade_id']}", "INFO")
            
        except Exception as e:
            logger.error(f"❌ Failed to execute scale-in: {e}")

    def _evaluate_position_exit(self, position: Dict, current_price: float, current_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate whether a position should be exited"""
        try:
            entry_price = position["entry_price"]
            side = position["side"]
            entry_time = position["entry_time"]
            signal_data = position.get("signal_data", {})
            
            # Calculate current PnL
            if side == "BUY":
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
            else:  # SELL
                pnl_percentage = ((entry_price - current_price) / entry_price) * 100
            
            # Time-based exit (if position is too old)
            position_age = time.time() - entry_time
            if position_age > self.magic_numbers.MAX_POSITION_AGE:
                return {
                    "should_exit": True,
                    "reason": "Time limit exceeded",
                    "exit_price": current_price
                }
            
            # Stop loss check
            if pnl_percentage <= -self.magic_numbers.STOP_LOSS_PERCENTAGE:
                return {
                    "should_exit": True,
                    "reason": "Stop loss triggered",
                    "exit_price": current_price
                }
            
            # Take profit check
            if pnl_percentage >= self.magic_numbers.TAKE_PROFIT_PERCENTAGE:
                return {
                    "should_exit": True,
                    "reason": "Take profit reached",
                    "exit_price": current_price
                }
            
            # Signal-based exit (if signal data is available)
            if signal_data and current_analysis:
                signal_type = signal_data.get("type", "")
                current_trend = current_analysis.get("trend_5m", {}).get("direction", "UNKNOWN")
                
                # Exit if trend has reversed
                if signal_type == "BREAKOUT_ABOVE" and current_trend == "DOWNTREND":
                    return {
                        "should_exit": True,
                        "reason": "Trend reversal detected",
                        "exit_price": current_price
                    }
                elif signal_type == "BREAKOUT_BELOW" and current_trend == "UPTREND":
                    return {
                        "should_exit": True,
                        "reason": "Trend reversal detected",
                        "exit_price": current_price
                    }
            
            # No exit needed
            return {
                "should_exit": False,
                "reason": "Position performing as expected",
                "exit_price": current_price
            }
            
        except Exception as e:
            logger.error(f"Position exit evaluation failed: {e}")
            return {
                "should_exit": False,
                "reason": f"Evaluation error: {str(e)}",
                "exit_price": current_price
            }
    
    def _save_positions(self):
        """Save open positions to file"""
        try:
            with open(constants.POSITIONS_FILE, 'w') as f:
                json.dump(self.bot.open_positions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save positions: {e}")
    
    def _load_positions(self) -> List[Dict[str, Any]]:
        """Load open positions from file"""
        try:
            with open(constants.POSITIONS_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        except Exception as e:
            logger.error(f"Failed to load positions: {e}")
            return []
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get list of open positions"""
        return [pos for pos in self.bot.open_positions if pos["status"] == "OPEN"]
    
    def calculate_portfolio_pnl(self) -> Dict[str, Any]:
        """Calculate total portfolio PnL"""
        try:
            total_pnl = 0.0
            total_pnl_percentage = 0.0
            open_positions = self.get_open_positions()
            
            for position in open_positions:
                entry_price = position["entry_price"]
                current_price = self.bot.get_hyperliquid_price() or entry_price
                size = position["size"]
                
                if position["side"] == "BUY":
                    pnl = (current_price - entry_price) * size
                    pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                else:  # SELL
                    pnl = (entry_price - current_price) * size
                    pnl_percentage = ((entry_price - current_price) / entry_price) * 100
                
                total_pnl += pnl
                total_pnl_percentage += pnl_percentage
            
            return {
                "total_pnl": total_pnl,
                "total_pnl_percentage": total_pnl_percentage,
                "open_positions_count": len(open_positions),
                "portfolio_value": sum(pos["position_value_usd"] for pos in open_positions)
            }
            
        except Exception as e:
            logger.error(f"Portfolio PnL calculation failed: {e}")
            return {
                "total_pnl": 0.0,
                "total_pnl_percentage": 0.0,
                "open_positions_count": 0,
                "portfolio_value": 0.0
            }
