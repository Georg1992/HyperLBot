#!/usr/bin/env python3
"""
AI Execution Layer
=================
Executes predictions/reactions as limit/market orders and manages ongoing trades.
Can also discard bad predictions based on real-time conditions.
"""

import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
from enum import Enum

class OrderType(Enum):
    LIMIT = "limit"
    MARKET = "market"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class TradeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    STOPPED = "stopped"

@dataclass
class Order:
    """Trading order"""
    order_id: str
    symbol: str
    direction: str  # "BUY" or "SELL"
    order_type: OrderType
    price: float
    size_btc: float
    size_usd: float
    status: OrderStatus
    timestamp: float
    strategy: str
    prediction_id: Optional[str] = None
    reactive_trade_id: Optional[str] = None

@dataclass
class Trade:
    """Active trade"""
    trade_id: str
    order_id: str
    symbol: str
    direction: str
    entry_price: float
    size_btc: float
    size_usd: float
    stop_loss: float
    target_price: float
    leverage: float
    status: TradeStatus
    strategy: str
    prediction_id: Optional[str] = None
    reactive_trade_id: Optional[str] = None
    entry_time: float = 0.0
    exit_time: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None

class ExecutionLayer:
    """
    Execution Layer - Order Management and Trade Lifecycle
    
    Responsibilities:
    1. Execute predictions as limit/market orders
    2. Manage ongoing trades (monitor stops/targets)
    3. Discard bad predictions based on real-time conditions
    4. Track trade performance and P&L
    5. Risk management and position sizing
    """
    
    def __init__(self):
        self.active_orders: Dict[str, Order] = {}
        self.active_trades: Dict[str, Trade] = {}
        self.order_history: List[Order] = []
        self.trade_history: List[Trade] = []
        
        # Trading control
        self.trading_enabled = False  # DISABLED by default - requires explicit enable
        
        # Strategy-specific execution thresholds (minimum confidence to execute)
        # AI generates predictions with REAL probability to win
        # Different strategies have different risk tolerance
        self.strategy_execution_thresholds = {
            "scalping": 0.55,      # 55% - faster execution, more opportunities
            "standard": 0.60,       # 60% - balanced approach
            "trend": 0.65,          # 65% - more selective, higher quality
            "high_vol": 0.50,       # 50% - volatile conditions, lower threshold
            "liquidation_hunting": 0.70,  # 70% - high risk strategy, very selective
            "default": 0.60        # 60% - fallback execution threshold
        }
        self.min_confidence_threshold = 0.7  # Legacy - will be overridden by strategy-specific
        
        # Intelligent prediction monitoring
        self.monitored_predictions: Dict[str, Dict[str, Any]] = {}  # Track predictions being monitored
        self.prediction_monitoring_enabled = True  # Enable intelligent monitoring
        self.max_monitoring_time = 300  # 5 minutes max monitoring time
        self.confidence_boost_threshold = 0.02  # 2% price movement toward entry boosts confidence
        
        
        # Risk management
        self.max_concurrent_trades = 3
        self.max_position_size_usd = 1000.0  # $1000 max position
        self.max_daily_loss = 50.0  # $50 max daily loss
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        logger.info("⚡ AI Execution Layer initialized")
    
    def execute_prediction(self, prediction: Dict[str, Any], current_price: float, 
                          market_data: Dict[str, Any]) -> Optional[Order]:
        """
        Execute a prediction as a trading order
        
        Args:
            prediction: Prediction from analysis layer
            current_price: Current market price
            market_data: Current market data
            
        Returns:
            Order object if executed, None if rejected
        """
        try:
            # Check if trading is enabled
            if not self.trading_enabled:
                logger.info(f"📊 Trading disabled - prediction not executed (confidence: {prediction.get('confidence', 0.0):.2f})")
                return None
            
            # Validate prediction before execution
            if not self._validate_prediction(prediction, current_price, market_data):
                logger.warning(f"⚠️ Prediction validation failed - not executing")
                return None
            
            # Check risk limits
            if not self._check_risk_limits(prediction):
                logger.warning(f"⚠️ Risk limits exceeded - not executing")
                return None
            
            # Determine order type
            order_type = self._determine_order_type(prediction, current_price)
            
            # Create order
            order = self._create_order(prediction, order_type, current_price)
            
            # Execute order (simulated for now)
            if self._execute_order(order):
                self.active_orders[order.order_id] = order
                logger.info(f"⚡ Order executed: {order.direction} {order.size_btc:.6f} BTC at ${order.price:.2f}")
                return order
            else:
                logger.warning(f"⚠️ Order execution failed")
                return None
                
        except Exception as e:
            logger.error(f"❌ Prediction execution failed: {e}")
            return None
    
    def execute_reactive_trade(self, reactive_trade: Dict[str, Any], current_price: float) -> Optional[Order]:
        """
        Execute a reactive trade as a market order
        
        Args:
            reactive_trade: Reactive trade from analysis layer
            current_price: Current market price
            
        Returns:
            Order object if executed, None if rejected
        """
        try:
            # Reactive trades are always market orders for speed
            order_type = OrderType.MARKET
            
            # Create order
            order = self._create_reactive_order(reactive_trade, order_type, current_price)
            
            # Execute immediately (market order)
            if self._execute_order(order):
                self.active_orders[order.order_id] = order
                logger.info(f"⚡ Reactive order executed: {order.direction} {order.size_btc:.6f} BTC at ${order.price:.2f}")
                return order
            else:
                logger.warning(f"⚠️ Reactive order execution failed")
                return None
                
        except Exception as e:
            logger.error(f"❌ Reactive trade execution failed: {e}")
            return None
    
    def monitor_trades(self, current_price: float, market_data: Dict[str, Any]):
        """
        Monitor active trades for stop loss and target hits
        
        Args:
            current_price: Current market price
            market_data: Current market data
        """
        try:
            trades_to_close = []
            
            for trade_id, trade in self.active_trades.items():
                should_close, reason = self._check_trade_exit_conditions(trade, current_price, market_data)
                
                if should_close:
                    trades_to_close.append((trade_id, reason))
            
            # Close trades that hit exit conditions
            for trade_id, reason in trades_to_close:
                self._close_trade(trade_id, current_price, reason)
                
        except Exception as e:
            logger.error(f"❌ Trade monitoring failed: {e}")
    
    def discard_bad_predictions(self, predictions: List[Dict[str, Any]], 
                              current_price: float, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Intelligently monitor predictions instead of immediately discarding them
        
        Args:
            predictions: List of predictions to filter
            current_price: Current market price
            market_data: Current market data
            
        Returns:
            List of valid predictions ready for execution
        """
        try:
            if not self.prediction_monitoring_enabled:
                # Fallback to old behavior if monitoring disabled
                return self._filter_predictions_old_way(predictions, current_price, market_data)
            
            valid_predictions = []
            
            for prediction in predictions:
                prediction_id = prediction.get("prediction_id", f"pred_{int(time.time())}")
                
                # Check if this prediction is already being monitored
                if prediction_id in self.monitored_predictions:
                    # Update existing monitored prediction
                    self._update_monitored_prediction(prediction_id, current_price, market_data)
                    
                    # Check if it's now ready for execution
                    if self._is_prediction_ready_for_execution(prediction_id):
                        valid_predictions.append(self.monitored_predictions[prediction_id])
                        logger.info(f"🎯 Monitored prediction ready for execution: {prediction_id}")
                    else:
                        logger.debug(f"👀 Continuing to monitor prediction: {prediction_id}")
                else:
                    # Start monitoring this prediction
                    if self._should_start_monitoring(prediction, current_price, market_data):
                        self._start_monitoring_prediction(prediction, current_price)
                        logger.info(f"👀 Started monitoring prediction: {prediction_id} (confidence: {prediction.get('confidence', 0):.2f})")
                    else:
                        # Immediate execution if high confidence
                        if self._validate_prediction(prediction, current_price, market_data):
                            valid_predictions.append(prediction)
                            logger.info(f"⚡ Immediate execution: {prediction_id}")
            
            # Clean up expired monitored predictions
            self._cleanup_expired_predictions()
            
            return valid_predictions
            
        except Exception as e:
            logger.error(f"❌ Intelligent prediction monitoring failed: {e}")
            return self._filter_predictions_old_way(predictions, current_price, market_data)
    
    def _validate_prediction(self, prediction: Dict[str, Any], current_price: float, 
                           market_data: Dict[str, Any]) -> bool:
        """Validate prediction before execution"""
        try:
            # Check if prediction has required fields
            required_fields = ["direction", "entry_price", "size_btc", "stop_loss", "target_price"]
            for field in required_fields:
                if field not in prediction:
                    logger.warning(f"⚠️ Prediction missing required field: {field}")
                    return False
            
            # Check if entry price is reasonable
            entry_price = prediction["entry_price"]
            if entry_price <= 0 or abs(entry_price - current_price) / current_price > 0.05:  # 5% max deviation
                logger.warning(f"⚠️ Entry price unreasonable: ${entry_price:.2f} vs current ${current_price:.2f}")
                return False
            
            # Check if stop loss and target are reasonable
            stop_loss = prediction["stop_loss"]
            target_price = prediction["target_price"]
            direction = prediction["direction"]
            
            if direction == "BUY":
                if stop_loss >= entry_price or target_price <= entry_price:
                    logger.warning(f"⚠️ Invalid BUY levels: entry=${entry_price:.2f}, stop=${stop_loss:.2f}, target=${target_price:.2f}")
                    return False
            elif direction == "SELL":
                if stop_loss <= entry_price or target_price >= entry_price:
                    logger.warning(f"⚠️ Invalid SELL levels: entry=${entry_price:.2f}, stop=${stop_loss:.2f}, target=${target_price:.2f}")
                    return False
            
            # Check strategy-specific confidence threshold
            confidence = prediction.get("confidence", 0.0)
            strategy = prediction.get("strategy", "default")
            strategy_threshold = self.get_strategy_execution_threshold(strategy)
            
            if confidence < strategy_threshold:
                logger.warning(f"⚠️ Low win probability prediction: {confidence:.2f} < {strategy_threshold:.1f} ({strategy_threshold*100:.0f}% win rate) for {strategy}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Prediction validation error: {e}")
            return False
    
    def _check_risk_limits(self, prediction: Dict[str, Any]) -> bool:
        """Check if prediction violates risk limits"""
        try:
            # Check position size
            size_usd = prediction.get("size_usd", 0)
            if size_usd > self.max_position_size_usd:
                logger.warning(f"⚠️ Position size too large: ${size_usd:.2f} > ${self.max_position_size_usd:.2f}")
                return False
            
            # Check concurrent trades limit
            if len(self.active_trades) >= self.max_concurrent_trades:
                logger.warning(f"⚠️ Too many concurrent trades: {len(self.active_trades)} >= {self.max_concurrent_trades}")
                return False
            
            # Check daily loss limit
            if self.daily_pnl < -self.max_daily_loss:
                logger.warning(f"⚠️ Daily loss limit exceeded: ${self.daily_pnl:.2f} < -${self.max_daily_loss:.2f}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Risk limit check error: {e}")
            return False
    
    def _determine_order_type(self, prediction: Dict[str, Any], current_price: float) -> OrderType:
        """Determine whether to use limit or market order"""
        try:
            entry_price = prediction["entry_price"]
            direction = prediction["direction"]
            
            # Use limit order if entry price is different from current price
            if abs(entry_price - current_price) / current_price > 0.001:  # 0.1% difference
                return OrderType.LIMIT
            else:
                return OrderType.MARKET
                
        except Exception as e:
            logger.error(f"❌ Order type determination error: {e}")
            return OrderType.MARKET
    
    def _create_order(self, prediction: Dict[str, Any], order_type: OrderType, current_price: float) -> Order:
        """Create order from prediction"""
        try:
            order_id = str(uuid.uuid4())
            
            # Determine execution price
            if order_type == OrderType.MARKET:
                price = current_price
            else:
                price = prediction["entry_price"]
            
            return Order(
                order_id=order_id,
                symbol="BTC",
                direction=prediction["direction"],
                order_type=order_type,
                price=price,
                size_btc=prediction["size_btc"],
                size_usd=prediction["size_usd"],
                status=OrderStatus.PENDING,
                timestamp=time.time(),
                strategy=prediction.get("strategy", "unknown"),
                prediction_id=prediction.get("prediction_id")
            )
            
        except Exception as e:
            logger.error(f"❌ Order creation error: {e}")
            raise
    
    def _create_reactive_order(self, reactive_trade: Dict[str, Any], order_type: OrderType, current_price: float) -> Order:
        """Create order from reactive trade"""
        try:
            order_id = str(uuid.uuid4())
            
            return Order(
                order_id=order_id,
                symbol="BTC",
                direction=reactive_trade["direction"],
                order_type=order_type,
                price=current_price,  # Market order at current price
                size_btc=reactive_trade["size_btc"],
                size_usd=reactive_trade["size_usd"],
                status=OrderStatus.PENDING,
                timestamp=time.time(),
                strategy="reactive",
                reactive_trade_id=reactive_trade.get("trade_id")
            )
            
        except Exception as e:
            logger.error(f"❌ Reactive order creation error: {e}")
            raise
    
    def _execute_order(self, order: Order) -> bool:
        """Execute order (simulated for now)"""
        try:
            # Simulate order execution
            # In real implementation, this would call the exchange API
            
            # Simulate immediate fill for market orders
            if order.order_type == OrderType.MARKET:
                order.status = OrderStatus.FILLED
                
                # Create trade from filled order
                self._create_trade_from_order(order)
                
                logger.info(f"⚡ Market order filled: {order.direction} {order.size_btc:.6f} BTC at ${order.price:.2f}")
                return True
            
            # For limit orders, add to pending orders (would be filled later)
            else:
                order.status = OrderStatus.PENDING
                logger.info(f"⚡ Limit order placed: {order.direction} {order.size_btc:.6f} BTC at ${order.price:.2f}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Order execution error: {e}")
            return False
    
    def _create_trade_from_order(self, order: Order):
        """Create trade from filled order"""
        try:
            trade_id = str(uuid.uuid4())
            
            # Get prediction data for stop loss and target
            prediction_data = self._get_prediction_data(order.prediction_id)
            reactive_data = self._get_reactive_data(order.reactive_trade_id)
            
            if prediction_data:
                stop_loss = prediction_data.get("stop_loss", order.price * 0.99)
                target_price = prediction_data.get("target_price", order.price * 1.01)
                leverage = prediction_data.get("leverage", 20.0)
            elif reactive_data:
                stop_loss = reactive_data.get("stop_loss", order.price * 0.98)
                target_price = reactive_data.get("target_price", order.price * 1.02)
                leverage = 40.0  # Higher leverage for reactive trades
            else:
                # Default values
                stop_loss = order.price * 0.99
                target_price = order.price * 1.01
                leverage = 20.0
            
            trade = Trade(
                trade_id=trade_id,
                order_id=order.order_id,
                symbol=order.symbol,
                direction=order.direction,
                entry_price=order.price,
                size_btc=order.size_btc,
                size_usd=order.size_usd,
                stop_loss=stop_loss,
                target_price=target_price,
                leverage=leverage,
                status=TradeStatus.OPEN,
                strategy=order.strategy,
                prediction_id=order.prediction_id,
                reactive_trade_id=order.reactive_trade_id,
                entry_time=time.time()
            )
            
            self.active_trades[trade_id] = trade
            logger.info(f"⚡ Trade opened: {trade.direction} {trade.size_btc:.6f} BTC at ${trade.entry_price:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Trade creation error: {e}")
    
    def _get_prediction_data(self, prediction_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get prediction data by ID (placeholder)"""
        # In real implementation, this would retrieve from prediction manager
        return None
    
    def _get_reactive_data(self, reactive_trade_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get reactive trade data by ID (placeholder)"""
        # In real implementation, this would retrieve from reactive engine
        return None
    
    def _check_trade_exit_conditions(self, trade: Trade, current_price: float, 
                                   market_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if trade should be closed"""
        try:
            # Check stop loss
            if trade.direction == "BUY":
                if current_price <= trade.stop_loss:
                    return True, "stop_loss"
            else:  # SELL
                if current_price >= trade.stop_loss:
                    return True, "stop_loss"
            
            # Check target
            if trade.direction == "BUY":
                if current_price >= trade.target_price:
                    return True, "target"
            else:  # SELL
                if current_price <= trade.target_price:
                    return True, "target"
            
            # Check time-based exit (optional)
            trade_age = time.time() - trade.entry_time
            if trade_age > 3600:  # 1 hour max trade duration
                return True, "timeout"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"❌ Trade exit condition check error: {e}")
            return False, ""
    
    def _close_trade(self, trade_id: str, exit_price: float, reason: str):
        """Close a trade"""
        try:
            if trade_id not in self.active_trades:
                logger.warning(f"⚠️ Trade {trade_id} not found in active trades")
                return
            
            trade = self.active_trades[trade_id]
            trade.status = TradeStatus.CLOSED
            trade.exit_time = time.time()
            trade.exit_price = exit_price
            
            # Calculate P&L
            if trade.direction == "BUY":
                pnl = (exit_price - trade.entry_price) * trade.size_btc
            else:  # SELL
                pnl = (trade.entry_price - exit_price) * trade.size_btc
            
            trade.pnl = pnl
            self.daily_pnl += pnl
            
            # Update statistics
            self.total_trades += 1
            if pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            # Move to history
            self.trade_history.append(trade)
            del self.active_trades[trade_id]
            
            logger.info(f"⚡ Trade closed: {trade.direction} {trade.size_btc:.6f} BTC "
                       f"at ${exit_price:.2f} (P&L: ${pnl:.2f}, reason: {reason})")
            
        except Exception as e:
            logger.error(f"❌ Trade close error: {e}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        try:
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            return {
                "active_orders": len(self.active_orders),
                "active_trades": len(self.active_trades),
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": win_rate,
                "daily_pnl": self.daily_pnl,
                "max_concurrent_trades": self.max_concurrent_trades
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get execution stats: {e}")
            return {}
    
    def sync_trades_to_rtm(self):
        """Sync AI execution layer trades to RTM for dashboard display"""
        try:
            from core.dashboard.dashboard_data_manager import simple_rtm
            
            # Convert AI execution layer trades to RTM format
            for trade_id, trade in self.active_trades.items():
                trade_data = {
                    "trade_id": trade_id,
                    "side": trade.direction,
                    "size_btc": trade.size_btc,
                    "entry_price": trade.entry_price,
                    "current_price": trade.entry_price,  # Will be updated by market data
                    "pnl": 0.0,  # Will be calculated
                    "status": "OPEN",
                    "entry_time": trade.entry_time,
                    "strategy": "AI_EXECUTION",
                    "prediction_id": trade.prediction_id,
                    "reactive_trade_id": trade.reactive_trade_id,
                    "stop_loss": getattr(trade, 'stop_loss', None),
                    "take_profit": getattr(trade, 'take_profit', None),
                    "leverage": getattr(trade, 'leverage', 1),
                    "was_profitable": False,  # Will be updated when closed
                    "exit_price": None,
                    "exit_time": None,
                    "exit_reason": None
                }
                
                # Add to RTM (this will update existing or add new)
                simple_rtm.add_trade(trade_data)
            
            logger.debug(f"🔄 Synced {len(self.active_trades)} AI trades to RTM")
            
        except Exception as e:
            logger.error(f"❌ Failed to sync AI trades to RTM: {e}")
    
    def enable_trading(self):
        """Enable AI trading execution"""
        self.trading_enabled = True
        logger.info("✅ AI trading execution ENABLED")
    
    def disable_trading(self):
        """Disable AI trading execution"""
        self.trading_enabled = False
        logger.info("❌ AI trading execution DISABLED")
    
    def get_strategy_execution_threshold(self, strategy: str) -> float:
        """Get strategy-specific execution threshold (minimum confidence to execute)"""
        return self.strategy_execution_thresholds.get(strategy.lower(), self.strategy_execution_thresholds["default"])
    
    def set_confidence_threshold(self, threshold: float):
        """Set minimum confidence threshold for trade execution"""
        if 0.0 <= threshold <= 1.0:
            self.min_confidence_threshold = threshold
            logger.info(f"🎯 Win probability threshold set to {threshold:.1f} ({threshold*100:.0f}%)")
        else:
            logger.error(f"❌ Invalid confidence threshold: {threshold} (must be 0.0-1.0)")
    
    def set_strategy_confidence_threshold(self, strategy: str, threshold: float):
        """Set confidence threshold for specific strategy"""
        if 0.0 <= threshold <= 1.0:
            self.strategy_confidence_thresholds[strategy.lower()] = threshold
            logger.info(f"🎯 {strategy} confidence threshold set to {threshold:.1f} ({threshold*100:.0f}%)")
        else:
            logger.error(f"❌ Invalid confidence threshold: {threshold} (must be 0.0-1.0)")
    
    def _filter_predictions_old_way(self, predictions: List[Dict[str, Any]], current_price: float, 
                                   market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Old prediction filtering method (fallback)"""
        try:
            valid_predictions = []
            for prediction in predictions:
                if self._validate_prediction(prediction, current_price, market_data):
                    valid_predictions.append(prediction)
                else:
                    logger.debug(f"🗑️ Discarded bad prediction: {prediction.get('direction', 'UNKNOWN')}")
            return valid_predictions
        except Exception as e:
            logger.error(f"❌ Old prediction filtering failed: {e}")
            return predictions
    
    def _should_start_monitoring(self, prediction: Dict[str, Any], current_price: float, 
                                market_data: Dict[str, Any]) -> bool:
        """Determine if a prediction should be monitored instead of executed immediately"""
        try:
            confidence = prediction.get("confidence", 0.0)
            entry_price = prediction.get("entry_price", 0)
            direction = prediction.get("direction", "HOLD")
            
            # Don't monitor if confidence is too low (below 20%)
            if confidence < 0.2:
                return False
            
            # Don't monitor if entry price is too far from current price (>3%)
            price_deviation = abs(entry_price - current_price) / current_price
            if price_deviation > 0.03:
                return False
            
            # Don't monitor if we already have too many predictions being monitored
            if len(self.monitored_predictions) >= 5:
                return False
            
            # Monitor if confidence is below execution threshold but above monitoring threshold
            return confidence < self.min_confidence_threshold and confidence >= 0.2
            
        except Exception as e:
            logger.error(f"❌ Failed to determine monitoring decision: {e}")
            return False
    
    def _start_monitoring_prediction(self, prediction: Dict[str, Any], current_price: float):
        """Start monitoring a prediction"""
        try:
            prediction_id = prediction.get("prediction_id", f"pred_{int(time.time())}")
            
            # Add monitoring metadata
            monitored_prediction = prediction.copy()
            monitored_prediction.update({
                "monitoring_start_time": time.time(),
                "initial_price": current_price,
                "initial_confidence": prediction.get("confidence", 0.0),
                "monitoring_status": "ACTIVE",
                "confidence_history": [prediction.get("confidence", 0.0)],
                "price_history": [current_price],
                "last_update": time.time()
            })
            
            self.monitored_predictions[prediction_id] = monitored_prediction
            logger.info(f"👀 Started monitoring prediction {prediction_id}: {prediction.get('direction')} at ${prediction.get('entry_price', 0):.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring prediction: {e}")
    
    def _update_monitored_prediction(self, prediction_id: str, current_price: float, market_data: Dict[str, Any]):
        """Update a monitored prediction with current market data"""
        try:
            if prediction_id not in self.monitored_predictions:
                return
            
            prediction = self.monitored_predictions[prediction_id]
            entry_price = prediction.get("entry_price", 0)
            direction = prediction.get("direction", "HOLD")
            initial_confidence = prediction.get("initial_confidence", 0.0)
            
            # Calculate price movement toward entry
            if direction == "BUY":
                price_movement = (entry_price - current_price) / entry_price  # Positive = moving toward entry
            else:  # SELL
                price_movement = (current_price - entry_price) / entry_price  # Positive = moving toward entry
            
            # Update confidence based on market movement
            new_confidence = self._calculate_updated_confidence(prediction, current_price, price_movement)
            
            # Update prediction data
            prediction.update({
                "confidence": new_confidence,
                "price_history": prediction.get("price_history", []) + [current_price],
                "confidence_history": prediction.get("confidence_history", []) + [new_confidence],
                "last_update": time.time(),
                "price_movement": price_movement
            })
            
            logger.debug(f"📊 Updated monitored prediction {prediction_id}: confidence {new_confidence:.3f}, movement {price_movement:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update monitored prediction: {e}")
    
    def _calculate_updated_confidence(self, prediction: Dict[str, Any], current_price: float, 
                                    price_movement: float) -> float:
        """Calculate updated confidence based on market movement"""
        try:
            initial_confidence = prediction.get("initial_confidence", 0.0)
            entry_price = prediction.get("entry_price", 0)
            direction = prediction.get("direction", "HOLD")
            
            # Base confidence boost for moving toward entry price
            if price_movement > 0:  # Moving toward entry
                confidence_boost = min(price_movement * 2, 0.2)  # Max 20% boost
            else:  # Moving away from entry
                confidence_penalty = min(abs(price_movement) * 1.5, 0.3)  # Max 30% penalty
                confidence_boost = -confidence_penalty
            
            # Time decay - reduce confidence over time
            monitoring_time = time.time() - prediction.get("monitoring_start_time", time.time())
            time_decay = min(monitoring_time / 300, 0.1)  # Max 10% decay over 5 minutes
            
            # Calculate new confidence
            new_confidence = initial_confidence + confidence_boost - time_decay
            new_confidence = max(0.0, min(1.0, new_confidence))  # Clamp to 0-1
            
            return new_confidence
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate updated confidence: {e}")
            return prediction.get("confidence", 0.0)
    
    def _is_prediction_ready_for_execution(self, prediction_id: str) -> bool:
        """Check if a monitored prediction is ready for execution"""
        try:
            if prediction_id not in self.monitored_predictions:
                return False
            
            prediction = self.monitored_predictions[prediction_id]
            confidence = prediction.get("confidence", 0.0)
            price_movement = prediction.get("price_movement", 0.0)
            monitoring_time = time.time() - prediction.get("monitoring_start_time", time.time())
            
            # Ready for execution if:
            # 1. Confidence reached threshold, OR
            # 2. Price moved significantly toward entry (1%+), OR
            # 3. Monitoring time exceeded and still reasonable confidence
            
            if confidence >= self.min_confidence_threshold:
                return True
            
            if abs(price_movement) >= 0.01:  # 1% movement toward entry
                return True
            
            if monitoring_time >= 60 and confidence >= 0.4:  # 1 minute + 40% confidence
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to check execution readiness: {e}")
            return False
    
    def _cleanup_expired_predictions(self):
        """Remove expired monitored predictions"""
        try:
            current_time = time.time()
            expired_predictions = []
            
            for prediction_id, prediction in self.monitored_predictions.items():
                monitoring_time = current_time - prediction.get("monitoring_start_time", current_time)
                
                # Remove if monitoring time exceeded or confidence too low
                if (monitoring_time > self.max_monitoring_time or 
                    prediction.get("confidence", 0.0) < 0.1):
                    expired_predictions.append(prediction_id)
            
            for prediction_id in expired_predictions:
                prediction = self.monitored_predictions.pop(prediction_id, {})
                logger.info(f"🗑️ Expired monitored prediction: {prediction_id} (confidence: {prediction.get('confidence', 0):.2f})")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired predictions: {e}")

# Global instance
global_execution_layer = ExecutionLayer()
