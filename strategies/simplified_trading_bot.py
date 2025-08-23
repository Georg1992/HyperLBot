#!/usr/bin/env python3
"""
Simplified Trading Bot
Clean, maintainable architecture without overengineering
"""

import time
import json
import statistics
from typing import Dict, Any, Optional, List
from loguru import logger
import sys
import os

# Import core modules
from core.hyperliquid_api import HyperliquidAPI
from data.yahoo_data_fetcher import YahooDataFetcher
from core.config import TradingConfig
from core.constants import constants, strategy_constants
from core.instance_manager import instance_manager
from strategies.fee_manager import FeeManager
from strategies.prediction_engine import PredictionEngine
from core.trading_logger import TradingLogger
from core.account_manager import account_manager


class SimplifiedTradingBot:
    """Simplified trading bot with clean architecture"""
    
    def __init__(self, initial_balance: float = None, strategy_name: str = None, balance_mode: str = "simulated"):
        """Initialize the simplified trading bot"""
        self.config = TradingConfig()
        self.strategy_name = strategy_name or constants.DEFAULT_STRATEGY
        self.strategy_config = self.config.STRATEGY_CONFIGS.get(self.strategy_name, strategy_constants.STANDARD_STRATEGY)
        
        # Core components
        self.hyperliquid_api = None
        self.yahoo_fetcher = YahooDataFetcher()
        self.connected = False
        self.balance_mode = balance_mode
        
        # Trading state
        self.paper_balance = initial_balance or constants.DEFAULT_INITIAL_BALANCE
        self.initial_balance = self.paper_balance
        self.open_positions = []
        self.closed_positions = []
        self.trade_history = []
        
        # Load existing positions
        self._load_existing_positions()
        
        # Market data storage
        self.binance_analysis = {}
        self.weekly_trend_analysis = {}
        self.hyperliquid_price = 0
        self.last_trade_time = 0
        self.min_interval = constants.MIN_TRADE_INTERVAL
        
        # Signal deduplication
        self.last_signal_reason = ""
        self.last_signal_price = 0
        self.last_signal_time = 0
        self.signal_cooldown = constants.SIGNAL_COOLDOWN
        
        # Price monitoring
        self.price_difference_threshold = constants.PRICE_DIFFERENCE_THRESHOLD
        self.last_price_difference_alert = 0
        self.price_difference_alert_cooldown = constants.PRICE_DIFFERENCE_ALERT_COOLDOWN
        
        # Essential components only
        self.fee_manager = FeeManager()
        self.prediction_engine = PredictionEngine(self.strategy_config)
        self.trading_logger = TradingLogger(constants.LOG_DIR)
        
        # Clean up old sessions
        self.trading_logger.cleanup_old_sessions(keep_sessions=constants.MAX_SESSIONS_TO_KEEP)
        
        # Initialize real-time data manager
        self._initialize_data_manager()
        
        logger.info(f"🤖 Simplified Trading Bot initialized")
        logger.info(f"   Strategy: {self.strategy_name}")
        logger.info(f"   Initial Balance: ${self.paper_balance:.2f}")
        logger.info(f"   Balance Mode: {self.balance_mode}")
    
    def _initialize_data_manager(self):
        """Initialize real-time data manager"""
        try:
            from core.realtime_data_manager import trading_data_manager
            self.trading_data_manager = trading_data_manager
            
            # Start new session
            if self.trading_data_manager:
                session_data = {
                    "strategy": self.strategy_name,
                    "initial_balance": self.paper_balance,
                    "balance_mode": self.balance_mode
                }
                self.trading_data_manager.start_session(session_data)
                logger.success("✅ Real-time data manager initialized")
            else:
                logger.warning("⚠️ Real-time data manager not available")
                self.trading_data_manager = None
                
        except ImportError:
            logger.warning("⚠️ Real-time data manager module not found")
            self.trading_data_manager = None
        except Exception as e:
            logger.error(f"❌ Error initializing data manager: {e}")
            self.trading_data_manager = None
    
    def _load_existing_positions(self):
        """Load existing positions from file"""
        try:
            if os.path.exists(constants.POSITIONS_FILE):
                with open(constants.POSITIONS_FILE, 'r') as f:
                    data = json.load(f)
                    self.open_positions = data.get("open_positions", [])
                    self.closed_positions = data.get("closed_positions", [])
                    
                if self.open_positions:
                    logger.info(f"📂 Loaded {len(self.open_positions)} existing open positions")
                    
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
            self.open_positions = []
            self.closed_positions = []
    
    def _save_positions(self):
        """Save positions to file"""
        try:
            data = {
                "open_positions": self.open_positions,
                "closed_positions": self.closed_positions,
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(constants.POSITIONS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
    
    def connect(self) -> bool:
        """Connect to Hyperliquid API"""
        try:
            self.hyperliquid_api = HyperliquidAPI()
            
            # Test connection
            current_price = self.hyperliquid_api.get_current_price("BTC")
            if current_price and current_price > 0:
                self.connected = True
                logger.success(f"✅ Connected to Hyperliquid API - BTC price: ${current_price:,.2f}")
                return True
            else:
                logger.error("❌ Failed to get valid price data from Hyperliquid")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Hyperliquid API: {e}")
            return False
    
    def get_market_analysis(self) -> Dict[str, Any]:
        """Get comprehensive market analysis"""
        try:
            # Get Hyperliquid price
            if self.connected and self.hyperliquid_api:
                self.hyperliquid_price = self.hyperliquid_api.get_current_price("BTC")
            else:
                self.hyperliquid_price = constants.DEFAULT_BTC_PRICE
            
            # Get Yahoo Finance analysis
            self.binance_analysis = self.yahoo_fetcher.get_market_analysis("BTC", hyperliquid_price=self.hyperliquid_price)
            
            # Update real-time data manager
            if self.trading_data_manager:
                self.trading_data_manager.update_market_data({
                    "current_price": self.hyperliquid_price,
                    "yahoo_analysis": self.binance_analysis,
                    "timestamp": time.time()
                })
            
            return self.binance_analysis
            
        except Exception as e:
            logger.error(f"Error getting market analysis: {e}")
            return {"error": str(e)}
    
    def generate_trading_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate trading signal based on market analysis"""
        try:
            if "error" in market_data:
                return None
            
            # Generate prediction
            prediction = self.prediction_engine.build_price_prediction(
                market_data, 
                self.hyperliquid_price, 
                self.strategy_name
            )
            
            if not prediction.get("has_prediction", False):
                return None
            
            # Check signal cooldown
            current_time = time.time()
            if current_time - self.last_signal_time < self.signal_cooldown:
                return None
            
            # Convert prediction to trading signal
            signal = {
                "type": prediction.get("prediction_type", "UNKNOWN"),
                "side": prediction.get("side", "NEUTRAL"),
                "confidence": prediction.get("confidence", 0),
                "entry_price": self.hyperliquid_price,
                "position_size": self._calculate_position_size(prediction.get("confidence", 0)),
                "stop_loss": self._calculate_stop_loss(prediction),
                "take_profit": self._calculate_take_profit(prediction),
                "reason": prediction.get("reason", "Market analysis"),
                "timestamp": current_time
            }
            
            # Update signal tracking
            self.last_signal_time = current_time
            self.last_signal_reason = signal["reason"]
            self.last_signal_price = self.hyperliquid_price
            
            # Update real-time data manager
            if self.trading_data_manager:
                self.trading_data_manager.add_signal(signal)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating trading signal: {e}")
            return None
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Calculate position size based on confidence"""
        base_size = self.strategy_config.get("position_size", 0.1)
        
        if confidence >= constants.ULTRA_CONFIDENCE_THRESHOLD:
            return min(constants.ULTRA_CONFIDENCE_POSITION, base_size * 2.0)
        elif confidence >= constants.HIGH_CONFIDENCE_THRESHOLD:
            return min(constants.HIGH_CONFIDENCE_POSITION, base_size * 1.5)
        elif confidence >= constants.MIN_CONFIDENCE_THRESHOLD:
            return min(constants.MEDIUM_CONFIDENCE_POSITION, base_size)
        else:
            return constants.LOW_CONFIDENCE_POSITION
    
    def _calculate_stop_loss(self, prediction: Dict[str, Any]) -> float:
        """Calculate stop loss price"""
        side = prediction.get("side", "BUY")
        stop_loss_pct = self.strategy_config.get("stop_loss", 0.004)
        
        if side == "BUY":
            return self.hyperliquid_price * (1 - stop_loss_pct)
        else:
            return self.hyperliquid_price * (1 + stop_loss_pct)
    
    def _calculate_take_profit(self, prediction: Dict[str, Any]) -> float:
        """Calculate take profit price"""
        side = prediction.get("side", "BUY")
        profit_target_pct = self.strategy_config.get("profit_target", 0.008)
        
        if side == "BUY":
            return self.hyperliquid_price * (1 + profit_target_pct)
        else:
            return self.hyperliquid_price * (1 - profit_target_pct)
    
    def execute_trade(self, signal: Dict[str, Any]) -> bool:
        """Execute a trade based on signal"""
        try:
            # For paper trading, simulate the trade
            trade_id = f"trade_{int(time.time())}"
            
            trade = {
                "trade_id": trade_id,
                "side": signal["side"],
                "symbol": "BTC",
                "entry_price": signal["entry_price"],
                "size": signal["position_size"],
                "stop_loss": signal["stop_loss"],
                "take_profit": signal["take_profit"],
                "entry_time": time.time(),
                "status": "OPEN",
                "reason": signal["reason"],
                "confidence": signal["confidence"]
            }
            
            # Add to open positions
            self.open_positions.append(trade)
            self._save_positions()
            
            # Update balance (subtract fees)
            trading_fees = self.fee_manager.calculate_trading_fees(
                signal["entry_price"], 
                signal["position_size"]
            )
            self.paper_balance -= trading_fees["total_fees"]
            
            # Update real-time data manager
            if self.trading_data_manager:
                self.trading_data_manager.add_trade(trade)
                self.trading_data_manager.update_balance(self.paper_balance)
            
            # Log the trade
            self.trading_logger.log_trade_execution(trade)
            
            logger.success(f"✅ Trade executed: {signal['side']} BTC at ${signal['entry_price']:.2f}")
            logger.info(f"   Position size: {signal['position_size']:.1%}")
            logger.info(f"   Stop loss: ${signal['stop_loss']:.2f}")
            logger.info(f"   Take profit: ${signal['take_profit']:.2f}")
            logger.info(f"   Confidence: {signal['confidence']:.1%}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    def check_open_positions(self):
        """Check and update open positions"""
        if not self.open_positions:
            return
        
        current_price = self.hyperliquid_price
        positions_to_close = []
        
        for position in self.open_positions:
            try:
                # Check stop loss and take profit
                should_close = False
                exit_reason = ""
                
                if position["side"] == "BUY":
                    if current_price <= position["stop_loss"]:
                        should_close = True
                        exit_reason = "STOP_LOSS"
                    elif current_price >= position["take_profit"]:
                        should_close = True
                        exit_reason = "TAKE_PROFIT"
                else:  # SELL
                    if current_price >= position["stop_loss"]:
                        should_close = True
                        exit_reason = "STOP_LOSS"
                    elif current_price <= position["take_profit"]:
                        should_close = True
                        exit_reason = "TAKE_PROFIT"
                
                if should_close:
                    positions_to_close.append((position, exit_reason))
                    
            except Exception as e:
                logger.error(f"Error checking position {position.get('trade_id', 'unknown')}: {e}")
        
        # Close positions
        for position, exit_reason in positions_to_close:
            self._close_position(position, exit_reason)
    
    def _close_position(self, position: Dict[str, Any], exit_reason: str):
        """Close a position"""
        try:
            current_price = self.hyperliquid_price
            
            # Calculate P&L
            entry_price = position["entry_price"]
            position_size = position["size"]
            
            if position["side"] == "BUY":
                pnl = (current_price - entry_price) * position_size * self.paper_balance
            else:  # SELL
                pnl = (entry_price - current_price) * position_size * self.paper_balance
            
            # Calculate fees
            exit_fees = self.fee_manager.calculate_trading_fees(current_price, position_size)
            net_pnl = pnl - exit_fees["total_fees"]
            
            # Update position
            position.update({
                "exit_price": current_price,
                "exit_time": time.time(),
                "exit_reason": exit_reason,
                "pnl": net_pnl,
                "pnl_pct": (net_pnl / (entry_price * position_size * self.paper_balance)) * 100,
                "status": "CLOSED"
            })
            
            # Update balance
            self.paper_balance += net_pnl
            
            # Move to closed positions
            self.closed_positions.append(position)
            self.open_positions.remove(position)
            self._save_positions()
            
            # Update real-time data manager
            if self.trading_data_manager:
                self.trading_data_manager.close_trade(position)
                self.trading_data_manager.update_balance(self.paper_balance)
            
            # Log the closure
            self.trading_logger.log_trade_exit(position)
            
            pnl_symbol = "📈" if net_pnl > 0 else "📉"
            logger.info(f"{pnl_symbol} Position closed: {exit_reason}")
            logger.info(f"   Trade ID: {position['trade_id']}")
            logger.info(f"   Entry: ${entry_price:.2f} → Exit: ${current_price:.2f}")
            logger.info(f"   P&L: ${net_pnl:.2f} ({position['pnl_pct']:.2f}%)")
            logger.info(f"   New balance: ${self.paper_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    def run_trading_session(self, max_trades: int = None, check_interval: int = None):
        """Run the main trading session"""
        max_trades = max_trades or constants.DEFAULT_MAX_TRADES
        check_interval = check_interval or constants.DEFAULT_CHECK_INTERVAL
        
        logger.info(f"🚀 Starting trading session")
        logger.info(f"   Max trades: {max_trades}")
        logger.info(f"   Check interval: {check_interval}s")
        logger.info(f"   Strategy: {self.strategy_name}")
        
        trades_executed = 0
        session_start_time = time.time()
        
        try:
            while trades_executed < max_trades:
                cycle_start = time.time()
                
                # Get market analysis
                market_data = self.get_market_analysis()
                
                # Check existing positions
                self.check_open_positions()
                
                # Generate new signal if we have room for more trades
                if len(self.open_positions) < 3:  # Max 3 concurrent positions
                    signal = self.generate_trading_signal(market_data)
                    
                    if signal and signal["side"] in ["BUY", "SELL"]:
                        if self.execute_trade(signal):
                            trades_executed += 1
                            
                            # Update instance lock with progress
                            instance_manager.update_lock_info(
                                self.strategy_name, 
                                self.paper_balance
                            )
                
                # Calculate sleep time
                cycle_time = time.time() - cycle_start
                sleep_time = max(0, check_interval - cycle_time)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("🛑 Trading session interrupted by user")
        except Exception as e:
            logger.error(f"❌ Error in trading session: {e}")
        finally:
            self.close_session()
    
    def close_session(self):
        """Close the trading session"""
        try:
            # Close any remaining open positions
            for position in self.open_positions[:]:
                self._close_position(position, "SESSION_END")
            
            # Save final state
            self._save_positions()
            
            # End data manager session
            if self.trading_data_manager:
                self.trading_data_manager.end_session()
            
            # Final statistics
            total_trades = len(self.closed_positions)
            winning_trades = sum(1 for t in self.closed_positions if t.get("pnl", 0) > 0)
            total_pnl = sum(t.get("pnl", 0) for t in self.closed_positions)
            
            logger.info(f"📊 Session Summary:")
            logger.info(f"   Total trades: {total_trades}")
            logger.info(f"   Winning trades: {winning_trades}")
            logger.info(f"   Win rate: {(winning_trades/total_trades*100):.1f}%" if total_trades > 0 else "   Win rate: 0%")
            logger.info(f"   Total P&L: ${total_pnl:.2f}")
            logger.info(f"   Final balance: ${self.paper_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Error closing session: {e}")