#!/usr/bin/env python3
"""
Trading Execution Wrapper
Thin wrapper around HyperLiquidSimulator for executing trades.
All trading logic is handled by the simulator to match real Hyperliquid API behavior.
"""

from typing import Dict, Any, Optional
from loguru import logger


class TradingExecutionWrapper:
    """Thin wrapper for trade execution - delegates all logic to HyperLiquidSimulator"""
    
    def __init__(self, hyperliquid_simulator, account_manager=None, session_manager=None):
        """
        Initialize trading execution wrapper
        
        Args:
            hyperliquid_simulator: HyperLiquidSimulator instance
            account_manager: SimulatedAccountManager instance (for syncing)
            session_manager: SessionManager instance (for syncing)
        """
        self.simulator = hyperliquid_simulator
        self.account_manager = account_manager
        self.session_manager = session_manager
        
        logger.info("🎯 Trading Execution Wrapper initialized")
    
    def place_paper_trade(self, side: str, size: float, leverage: int = 30, 
                         signal_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Place a paper trade using the HyperLiquid simulator
        
        Args:
            side: BUY or SELL
            size: Position size in BTC
            leverage: Leverage multiplier
            signal_data: Trading signal metadata (strategy, confidence, SL/TP, etc.)
        
        Returns:
            True if trade placed successfully, False otherwise
        """
        try:
            # Extract metadata from signal_data
            signal_data = signal_data or {}
            stop_loss = signal_data.get("stop_loss")
            take_profit = signal_data.get("take_profit")
            
            # Prepare metadata for position tracking
            metadata = {
                "strategy": signal_data.get("strategy", "unknown"),
                "confidence": signal_data.get("confidence", 0),
                "expected_value": signal_data.get("expected_value", 0),
                "bayesian_confidence": signal_data.get("bayesian_confidence"),
                "reasoning": signal_data.get("reasoning", [])
            }
            
            # Get current market price for limit order
            from core.services.system_initializer import get_system_initializer
            system_initializer = get_system_initializer()
            market_data_service = system_initializer.singleton_systems.get("market_data_service")
            
            if not market_data_service:
                logger.error("❌ Market data service not available")
                return False
            
            current_price = market_data_service.get_hyperliquid_price()
            if not current_price:
                logger.error("❌ Current price not available")
                return False
            
            # Calculate limit price (slightly better than market)
            if side == "BUY":
                limit_price = current_price * 0.999  # 0.1% below market
            else:
                limit_price = current_price * 1.001  # 0.1% above market
            
            # Update simulator orderbook
            orderbook = market_data_service.get_orderbook("BTC")
            if orderbook and not orderbook.get('error'):
                self.simulator.update_order_book(orderbook)
            
            # Place order through simulator
            result = self.simulator.place_order(
                order_type="LIMIT",
                side=side,
                size=size,
                price=limit_price,
                leverage=leverage,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata=metadata
            )
            
            if not result.get("success"):
                logger.error(f"❌ Order failed: {result.get('error', 'Unknown error')}")
                return False
            
            # Sync account state
            self._sync_account_state()
            
            # Log success
            position = result.get("position", {})
            logger.success(f"✅ {side} LIMIT order placed: {size} BTC @ ${limit_price:,.2f}")
            logger.info(f"   Trade ID: {position.get('trade_id', 'N/A')}")
            logger.info(f"   Leverage: {leverage}x")
            logger.info(f"   Stop Loss: ${stop_loss:,.2f}" if stop_loss else "   No Stop Loss")
            logger.info(f"   Take Profit: ${take_profit:,.2f}" if take_profit else "   No Take Profit")
            logger.info(f"   Fees: ${result['fees']['fee_amount']:.4f} ({result['fees']['fee_type']})")
            logger.info(f"   Balance: ${result.get('account_balance', 0):,.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Trade placement failed: {e}")
            return False
    
    def close_paper_position(self, position: Dict[str, Any], exit_reason: str, exit_price: float) -> bool:
        """
        Close a paper position
        
        Args:
            position: Position dict with trade_id
            exit_reason: Reason for closing
            exit_price: Exit price
        
        Returns:
            True if closed successfully, False otherwise
        """
        try:
            trade_id = position.get("trade_id")
            if not trade_id:
                logger.error("❌ No trade_id in position")
                return False
            
            # Close position through simulator
            result = self.simulator.close_position(
                trade_id=trade_id,
                exit_price=exit_price,
                exit_reason=exit_reason
            )
            
            if not result.get("success"):
                logger.error(f"❌ Position close failed: {result.get('error', 'Unknown error')}")
                return False
            
            # Sync account state
            self._sync_account_state()
            
            # Log success
            pnl = result.get("pnl", {})
            logger.success(f"✅ Position closed: {trade_id}")
            logger.info(f"   Exit Price: ${exit_price:,.2f}")
            logger.info(f"   P&L: {pnl.get('pnl_pct', 0)*100:.2f}% (${pnl.get('net_pnl', 0):.4f})")
            logger.info(f"   Reason: {exit_reason}")
            logger.info(f"   Balance: ${result.get('account_balance', 0):,.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Position close failed: {e}")
            return False
    
    def check_position_exits(self, current_price: float):
        """
        Check all open positions for stop loss / take profit triggers
        
        Args:
            current_price: Current market price
        """
        try:
            # Check SL/TP through simulator
            closed_positions = self.simulator.check_stop_loss_take_profit(current_price)
            
            if closed_positions:
                logger.info(f"🎯 {len(closed_positions)} position(s) closed automatically")
                for pos in closed_positions:
                    logger.info(f"   {pos['trade_id']}: {pos['exit_reason']}")
                
                # Sync account state
                self._sync_account_state()
            
            # Check liquidation risk
            liquidated = self.simulator.check_liquidation_risk(current_price)
            
            if liquidated:
                logger.warning(f"🚨 {len(liquidated)} position(s) liquidated!")
                for pos in liquidated:
                    logger.warning(f"   {pos['trade_id']}: LIQUIDATION")
                
                # Sync account state
                self._sync_account_state()
                
        except Exception as e:
            logger.error(f"❌ Position exit check failed: {e}")
    
    def get_open_positions(self):
        """Get all open positions from simulator"""
        return self.simulator.get_open_positions()
    
    def _sync_account_state(self):
        """Sync account state from simulator to account manager and session manager"""
        try:
            account_state = self.simulator.get_account_state()
            
            # Sync to account manager
            if self.account_manager and hasattr(self.account_manager, 'account_data'):
                self.account_manager.account_data["current_balance"] = account_state["balance"]
                self.account_manager.account_data["total_pnl"] = account_state["realized_pnl"]
                self.account_manager.account_data["total_trades"] = account_state["total_trades"]
                self.account_manager.account_data["winning_trades"] = account_state["winning_trades"]
                self.account_manager.account_data["losing_trades"] = account_state["losing_trades"]
                self.account_manager.save_account()
            
            # Sync to session manager
            if self.session_manager and hasattr(self.session_manager, 'current_session_data'):
                self.session_manager.update_session_balance(
                    account_state["balance"],
                    f"Synced from simulator"
                )
            
        except Exception as e:
            logger.warning(f"⚠️ Account state sync failed: {e}")

