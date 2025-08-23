#!/usr/bin/env python3
"""
Real-Time Trading Data Manager
Professional in-memory data store for instant bot-dashboard communication
Eliminates slow log file reading and provides true real-time trading data
"""

import time
import json
import sqlite3
import threading
from typing import Dict, Any, List, Optional, Callable
from loguru import logger
from collections import deque
from datetime import datetime
import os

class RealTimeTradingDataManager:
    """
    Professional real-time data manager for trading bot
    Provides instant access to current trading state without file I/O
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for shared state across bot and dashboard"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.data_lock = threading.Lock()
        
        # Real-time trading state
        self.current_state = {
            "session": {
                "session_id": f"session_{int(time.time())}",
                "start_time": datetime.now().isoformat(),
                "status": "INACTIVE",
                "strategy": "standard",
                "initial_balance": 120.0,
                "current_balance": 120.0,
                "balance_change": 0.0,
                "balance_change_pct": 0.0,
                "last_balance_update": datetime.now().isoformat(),
                "bot_version": "Advanced Trading Bot v4.0",
                "open_positions_count": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0
            },
            "market": {
                "current_price": 0.0,
                "trend": "UNKNOWN",
                "market_condition": "UNKNOWN",
                "last_update": datetime.now().isoformat(),
                "rsi": 50.0,
                "volume_depth": 0.0,
                "orderbook_imbalance": 0.0,
                "volatility_5m": 0.0,
                "volatility_1h": 0.0,
                "support": 0.0,
                "resistance": 0.0,
                "volume_category": "UNKNOWN",
                "volume_trend": "UNKNOWN",
                "data_source": "none"
            },
            "predictions": [],
            "global_volume": {
                "global_volume_per_second": 0.0,
                "status": "unavailable",
                "last_update": 0
            },
            "blockchain_sentiment": {
                "overall_sentiment": "UNKNOWN",
                "confidence": 0.0,
                "last_update": 0
            }
        }
        
        # Historical data (in-memory for speed)
        self.MAX_TRADES = 100
        self.MAX_SIGNALS = 50
        self.MAX_ACTIVITY = 50
        
        self.recent_trades = deque(maxlen=self.MAX_TRADES)  # Last 100 trades
        self.recent_signals = deque(maxlen=self.MAX_SIGNALS)   # Last 50 signals
        self.recent_activity = deque(maxlen=self.MAX_ACTIVITY)  # Last 50 activities
        self.open_positions = []
        

        
        # Performance metrics
        self.performance_metrics = {
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "last_updated": time.time()
        }
        
        # SQLite database for persistence
        self.db_path = "trading_data.db"
        self._init_database()
        
        # WebSocket subscribers for real-time updates
        self.subscribers = []
        
        logger.success("🔥 Real-Time Trading Data Manager initialized")
    
    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    side TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    size REAL,
                    leverage INTEGER,
                    pnl REAL,
                    pnl_pct REAL,
                    confidence REAL,
                    entry_time REAL,
                    exit_time REAL,
                    holding_time REAL,
                    exit_reason TEXT,
                    was_profitable BOOLEAN,
                    is_winback_trade BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    price REAL,
                    trend TEXT,
                    market_condition TEXT,
                    rsi REAL,
                    volume REAL,
                    volatility_5m REAL,
                    volatility_1h REAL,
                    orderbook_imbalance REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_type TEXT,
                    side TEXT,
                    entry_price REAL,
                    confidence REAL,
                    timeframe INTEGER,
                    reason TEXT,
                    was_executed BOOLEAN DEFAULT FALSE,
                    execution_result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    start_time TEXT,
                    end_time TEXT,
                    strategy TEXT,
                    initial_balance REAL,
                    final_balance REAL,
                    balance_change REAL,
                    balance_change_pct REAL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(entry_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_timestamp ON market_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_time ON trading_signals(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_id ON trading_sessions(session_id)')
            
            conn.commit()
            conn.close()
            
            logger.success("✅ SQLite database initialized with trading tables")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    # SESSION MANAGEMENT
    def start_session(self, strategy: str, initial_balance: float, bot_version: str = "Advanced Bot"):
        """Start a new trading session"""
        with self.data_lock:
            # Check if there's an existing active session and close it properly
            if self.current_state["session"].get("status") == "ACTIVE":
                logger.warning(f"🔄 Found existing active session: {self.current_state['session'].get('session_id', 'unknown')}")
                logger.info("🔄 Closing previous session before starting new one...")
                self._close_existing_session()
            
            # Also check for orphaned sessions in the database and close them
            self._close_orphaned_sessions()
            
            session_id = f"session_{int(time.time())}"
            self.current_state["session"].update({
                "session_id": session_id,
                "start_time": datetime.now().isoformat(),
                "status": "ACTIVE",
                "strategy": strategy,
                "initial_balance": initial_balance,
                "current_balance": initial_balance,
                "balance_change": 0.0,
                "balance_change_pct": 0.0,
                "last_balance_update": datetime.now().isoformat(),
                "bot_version": bot_version,
                "open_positions_count": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0
            })
            
            logger.success(f"🚀 Trading session started: {session_id}")
            self._notify_subscribers("session_started", self.current_state["session"])
    
    def _close_existing_session(self):
        """Close existing session properly"""
        try:
            # Mark session as completed
            self.current_state["session"]["status"] = "COMPLETED"
            self.current_state["session"]["end_time"] = datetime.now().isoformat()
            
            # Calculate final session statistics
            if "start_time" in self.current_state["session"]:
                start_time = datetime.fromisoformat(self.current_state["session"]["start_time"])
                end_time = datetime.now()
                duration = end_time - start_time
                self.current_state["session"]["duration_minutes"] = round(duration.total_seconds() / 60, 2)
            
            # Save session data to database for historical tracking
            self._save_session_to_database()
            
            # Clear real-time data for fresh start
            self.recent_activity.clear()
            self.recent_signals.clear()
            self.recent_trades.clear()
            
            # Clear predictions for fresh start
            self.current_state["predictions"] = []
            
            logger.info(f"✅ Previous session closed: {self.current_state['session'].get('session_id', 'unknown')}")
            logger.info(f"   Duration: {self.current_state['session'].get('duration_minutes', 0):.1f} minutes")
            logger.info(f"   Final Balance: ${self.current_state['session'].get('current_balance', 0):.2f}")
            
            # Notify subscribers
            self._notify_subscribers("session_ended", self.current_state["session"])
            
        except Exception as e:
            logger.error(f"Error closing existing session: {e}")
    
    def _save_session_to_database(self):
        """Save completed session data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session_data = self.current_state["session"]
            
            cursor.execute('''
                INSERT INTO trading_sessions 
                (session_id, start_time, end_time, strategy, initial_balance, final_balance, 
                 balance_change, balance_change_pct, total_trades, winning_trades, losing_trades, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_data.get("session_id"),
                session_data.get("start_time"),
                session_data.get("end_time"),
                session_data.get("strategy"),
                session_data.get("initial_balance"),
                session_data.get("current_balance"),
                session_data.get("balance_change"),
                session_data.get("balance_change_pct"),
                session_data.get("total_trades"),
                session_data.get("winning_trades"),
                session_data.get("losing_trades"),
                session_data.get("status")
            ))
            
            conn.commit()
            conn.close()
            logger.debug("Session data saved to database")
            
        except Exception as e:
            logger.error(f"Error saving session to database: {e}")
    
    def _close_orphaned_sessions(self):
        """Close any orphaned sessions that were not properly ended"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find sessions that are marked as active but haven't been updated recently
            cursor.execute('''
                SELECT session_id, start_time, strategy 
                FROM trading_sessions 
                WHERE status = 'ACTIVE' 
                AND start_time < datetime('now', '-1 hour')
            ''')
            
            orphaned_sessions = cursor.fetchall()
            
            if orphaned_sessions:
                logger.warning(f"🔄 Found {len(orphaned_sessions)} orphaned sessions, closing them...")
                
                for session_id, start_time, strategy in orphaned_sessions:
                    cursor.execute('''
                        UPDATE trading_sessions 
                        SET status = 'ORPHANED', end_time = datetime('now')
                        WHERE session_id = ?
                    ''', (session_id,))
                    
                    logger.info(f"   Closed orphaned session: {session_id} ({strategy})")
                
                conn.commit()
                logger.success(f"✅ Closed {len(orphaned_sessions)} orphaned sessions")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error closing orphaned sessions: {e}")
    
    def end_session(self):
        """End current trading session"""
        with self.data_lock:
            self.current_state["session"]["status"] = "COMPLETED"
            
            logger.info("🏁 Trading session ended")
            self._notify_subscribers("session_ended", self.current_state["session"])
            
            # Save to file for cross-process sharing
            self._save_to_json_file()
    
    def update_balance(self, new_balance: float, reason: str = "Trade execution"):
        """Update current balance in real-time"""
        with self.data_lock:
            old_balance = self.current_state["session"]["current_balance"]
            initial_balance = self.current_state["session"]["initial_balance"]
            
            self.current_state["session"]["current_balance"] = new_balance
            self.current_state["session"]["balance_change"] = new_balance - initial_balance
            self.current_state["session"]["balance_change_pct"] = ((new_balance - initial_balance) / initial_balance) * 100
            self.current_state["session"]["last_balance_update"] = datetime.now().isoformat()
            
            balance_change = new_balance - old_balance
            logger.info(f"💰 Balance updated: ${old_balance:.2f} → ${new_balance:.2f} ({balance_change:+.2f}) - {reason}")
            
            self._notify_subscribers("balance_updated", {
                "new_balance": new_balance,
                "balance_change": balance_change,
                "reason": reason
            })
    
    # MARKET DATA MANAGEMENT
    def update_market_data(self, market_data: Dict[str, Any]):
        """Update real-time market data"""
        with self.data_lock:
            self.current_state["market"].update({
                "current_price": market_data.get("current_price", 0),
                "trend": market_data.get("trend", "UNKNOWN"),
                "market_condition": market_data.get("market_condition", "UNKNOWN"),
                "last_update": datetime.now().isoformat(),
                "rsi": market_data.get("rsi", 50.0),  # Use RSI calculated by bot
                "volume_depth": market_data.get("volume_depth", 0.0),
                "orderbook_imbalance": market_data.get("orderbook_imbalance", 0.0),
                "volatility_5m": market_data.get("volatility_5m", 0.0),
                "volatility_1h": market_data.get("volatility_1h", 0.0),
                "support": market_data.get("support", 0.0),
                "resistance": market_data.get("resistance", 0.0),
                "volume_category": market_data.get("volume_category", "UNKNOWN"),
                "volume_trend": market_data.get("volume_trend", "UNKNOWN"),
                "data_source": market_data.get("data_source", "bot")
            })
            
            # Store in database for historical analysis
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO market_data 
                    (timestamp, price, trend, market_condition, rsi, volume, volatility_5m, volatility_1h, orderbook_imbalance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    time.time(), market_data.get("current_price", 0), market_data.get("trend", "UNKNOWN"),
                    market_data.get("market_condition", "UNKNOWN"), market_data.get("rsi", 50.0),
                    market_data.get("volume_depth", 0.0), market_data.get("volatility_5m", 0.0),
                    market_data.get("volatility_1h", 0.0), market_data.get("orderbook_imbalance", 0.0)
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug(f"Market data storage error: {e}")
            
            self._notify_subscribers("market_updated", self.current_state["market"])
    
    def update_global_volume(self, volume_data: Dict[str, Any]):
        """Update global volume data"""
        with self.data_lock:
            self.current_state["global_volume"] = {
                "global_volume_per_second": volume_data.get("global_volume_per_second", 0.0),
                "volume_by_exchange": volume_data.get("volume_by_exchange", {}),
                "coverage_ratio": volume_data.get("coverage_ratio", 0.0),
                "successful_exchanges": volume_data.get("successful_exchanges", 0),
                "total_exchanges": volume_data.get("total_exchanges", 6),
                "status": volume_data.get("status", "unavailable"),
                "last_update": time.time()
            }
            
            self._notify_subscribers("global_volume_updated", self.current_state["global_volume"])
    
    def update_blockchain_sentiment(self, sentiment_data: Dict[str, Any]):
        """Update blockchain sentiment data"""
        with self.data_lock:
            self.current_state["blockchain_sentiment"] = {
                "overall_sentiment": sentiment_data.get("overall_sentiment", "UNKNOWN"),
                "confidence": sentiment_data.get("confidence", 0.0),
                "indicators": sentiment_data.get("indicators", {}),
                "last_update": time.time()
            }
            
            self._notify_subscribers("blockchain_sentiment_updated", self.current_state["blockchain_sentiment"])
    
    # TRADE MANAGEMENT
    def add_trade(self, trade_data: Dict[str, Any]):
        """Add a new trade to real-time data"""
        with self.data_lock:
            # Add to recent trades
            trade_record = {
                "trade_id": trade_data.get("trade_id"),
                "side": trade_data.get("side"),
                "entry_price": trade_data.get("entry_price", 0),
                "exit_price": trade_data.get("exit_price", 0),
                "size": trade_data.get("size", 0),
                "leverage": trade_data.get("leverage", 1),
                "pnl": trade_data.get("net_profit_loss", 0),
                "pnl_pct": trade_data.get("profit_loss_pct", 0),
                "confidence": trade_data.get("prediction_confidence", 0),
                "entry_time": trade_data.get("entry_time", time.time()),
                "exit_time": trade_data.get("exit_time", time.time()),
                "holding_time": trade_data.get("holding_time", 0),
                "exit_reason": trade_data.get("exit_reason", "UNKNOWN"),
                "was_profitable": trade_data.get("was_profitable", False),
                "is_winback_trade": trade_data.get("is_winback_trade", False),
                "timestamp": time.time()
            }
            
            self.recent_trades.append(trade_record)
            
            # Update session statistics
            session = self.current_state["session"]
            session["total_trades"] += 1
            if trade_record["was_profitable"]:
                session["winning_trades"] += 1
            else:
                session["losing_trades"] += 1
            
            # Store in database
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trades 
                    (trade_id, side, entry_price, exit_price, size, leverage, pnl, pnl_pct, 
                     confidence, entry_time, exit_time, holding_time, exit_reason, was_profitable, is_winback_trade)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade_record["trade_id"], trade_record["side"], trade_record["entry_price"],
                    trade_record["exit_price"], trade_record["size"], trade_record["leverage"],
                    trade_record["pnl"], trade_record["pnl_pct"], trade_record["confidence"],
                    trade_record["entry_time"], trade_record["exit_time"], trade_record["holding_time"],
                    trade_record["exit_reason"], trade_record["was_profitable"], trade_record["is_winback_trade"]
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Trade storage error: {e}")
            
            logger.success(f"📊 Trade recorded: {trade_record['side']} {trade_record['pnl']:+.2f} ({trade_record['pnl_pct']*100:+.1f}%)")
            self._notify_subscribers("trade_added", trade_record)
    
    def add_trading_signal(self, signal_data: Dict[str, Any]):
        """Add a new trading signal"""
        with self.data_lock:
            signal_record = {
                "signal_type": signal_data.get("type", "UNKNOWN"),
                "side": signal_data.get("side", "UNKNOWN"),
                "entry_price": signal_data.get("entry_price", 0),
                "confidence": signal_data.get("confidence", 0),
                "timeframe": signal_data.get("timeframe", 0),
                "reason": signal_data.get("reason", ""),
                "was_executed": False,
                "timestamp": time.time()
            }
            
            self.recent_signals.append(signal_record)
            
            # Store in database
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trading_signals 
                    (signal_type, side, entry_price, confidence, timeframe, reason, was_executed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal_record["signal_type"], signal_record["side"], signal_record["entry_price"],
                    signal_record["confidence"], signal_record["timeframe"], signal_record["reason"],
                    signal_record["was_executed"]
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug(f"Signal storage error: {e}")
            
            logger.info(f"🎯 Signal recorded: {signal_record['signal_type']} {signal_record['side']} @ {signal_record['confidence']:.1%}")
            self._notify_subscribers("signal_added", signal_record)
            # Save to file for cross-process sharing
            self._save_to_json_file()
    
    def add_activity(self, activity_data: Dict[str, Any]):
        """Add general bot activity"""
        with self.data_lock:
            activity_record = {
                "type": activity_data.get("type", "activity"),
                "message": activity_data.get("message", ""),
                "level": activity_data.get("level", "INFO"),
                "timestamp": time.time(),
                "datetime": datetime.now().isoformat()
            }
            
            self.recent_activity.append(activity_record)
            logger.debug(f"📊 RTM: Activity added - {activity_record['message']} (total: {len(self.recent_activity)})")
            self._notify_subscribers("activity_added", activity_record)
            # Save to file for cross-process sharing
            self._save_to_json_file()
    
    def update_predictions(self, predictions_data: List[Dict[str, Any]]):
        """Update current trading predictions"""
        with self.data_lock:
            self.current_state["predictions"] = predictions_data
            self._notify_subscribers("predictions_updated", predictions_data)
            # Save to file for cross-process sharing
            self._save_to_json_file()
    
    def update_open_positions(self, positions: List[Dict[str, Any]]):
        """Update open positions"""
        with self.data_lock:
            self.open_positions = positions
            self.current_state["session"]["open_positions_count"] = len(positions)
            self._notify_subscribers("positions_updated", positions)
    
    # DATA ACCESS METHODS
    def get_current_state(self) -> Dict[str, Any]:
        """Get complete current state for dashboard"""
        with self.data_lock:
            # Calculate performance metrics
            self._update_performance_metrics()
            
            # Try to load from file for cross-process sharing
            self._load_from_json_file()
            
            return {
                "session": self.current_state["session"].copy(),
                "market": self.current_state["market"].copy(),
                "predictions": self.current_state["predictions"].copy(),
                "global_volume": self.current_state["global_volume"].copy(),
                "blockchain_sentiment": self.current_state["blockchain_sentiment"].copy(),
                "performance": self.performance_metrics.copy(),
                "recent_trades": list(self.recent_trades)[-10:],  # Last 10 trades
                "recent_signals": list(self.recent_signals)[-8:],   # Last 8 signals
                "recent_activity": list(self.recent_activity)[-5:], # Last 5 activities
                "open_positions": self.open_positions.copy(),
                "timestamp": time.time()
            }
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get current session data"""
        with self.data_lock:
            return self.current_state["session"].copy()
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get current market data"""
        with self.data_lock:
            return self.current_state["market"].copy()
    
    def get_recent_trades(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades"""
        with self.data_lock:
            return list(self.recent_trades)[-count:]
    
    def get_recent_signals(self, count: int = 8) -> List[Dict[str, Any]]:
        """Get recent signals"""
        with self.data_lock:
            return list(self.recent_signals)[-count:]
    
    def get_recent_activity(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent activity"""
        with self.data_lock:
            return list(self.recent_activity)[-count:]
    
    def _update_performance_metrics(self):
        """Update performance metrics from recent trades"""
        if len(self.recent_trades) == 0:
            return
        
        trades = list(self.recent_trades)
        profitable_trades = [t for t in trades if t["was_profitable"]]
        losing_trades = [t for t in trades if not t["was_profitable"]]
        
        self.performance_metrics.update({
            "total_pnl": sum(t["pnl"] for t in trades),
            "win_rate": len(profitable_trades) / len(trades) if trades else 0.0,
            "avg_win": sum(t["pnl"] for t in profitable_trades) / len(profitable_trades) if profitable_trades else 0.0,
            "avg_loss": sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0.0,
            "last_updated": time.time()
        })
        
        # Calculate profit factor
        
        # Save to JSON file for cross-process sharing
        self._save_to_json_file()
        total_wins = sum(t["pnl"] for t in profitable_trades)
        total_losses = abs(sum(t["pnl"] for t in losing_trades))
        self.performance_metrics["profit_factor"] = total_wins / total_losses if total_losses > 0 else float('inf')
    
    # WEBSOCKET SUBSCRIBER MANAGEMENT
    def subscribe_to_updates(self, callback: Callable):
        """Subscribe to real-time updates"""
        self.subscribers.append(callback)
        logger.info(f"📡 New subscriber added - {len(self.subscribers)} total")
    
    def unsubscribe_from_updates(self, callback: Callable):
        """Unsubscribe from updates"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"📡 Subscriber removed - {len(self.subscribers)} total")
    
    def _notify_subscribers(self, event_type: str, data: Any):
        """Notify all subscribers of data updates"""
        for callback in self.subscribers[:]:  # Copy list to avoid modification during iteration
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Subscriber notification error: {e}")
                # Remove broken subscribers
                if callback in self.subscribers:
                    self.subscribers.remove(callback)
    
    # DATABASE QUERIES
    def get_historical_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical trades from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM trades 
                ORDER BY entry_time DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Historical trades query error: {e}")
            return []
    
    def get_performance_analysis(self, days: int = 7) -> Dict[str, Any]:
        """Get performance analysis for specified period"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get trades in period
            cursor.execute('''
                SELECT pnl, pnl_pct, was_profitable, holding_time, size, leverage
                FROM trades 
                WHERE entry_time > ?
                ORDER BY entry_time DESC
            ''', (cutoff_time,))
            
            trades = cursor.fetchall()
            conn.close()
            
            if not trades:
                return {"period_days": days, "total_trades": 0}
            
            # Calculate metrics
            total_trades = len(trades)
            profitable = [t for t in trades if t[2]]  # was_profitable is index 2
            
            return {
                "period_days": days,
                "total_trades": total_trades,
                "winning_trades": len(profitable),
                "losing_trades": total_trades - len(profitable),
                "win_rate": len(profitable) / total_trades,
                "total_pnl": sum(t[0] for t in trades),  # pnl is index 0
                "avg_pnl_pct": sum(t[1] for t in trades) / total_trades,  # pnl_pct is index 1
                "avg_holding_time": sum(t[3] for t in trades) / total_trades,  # holding_time is index 3
                "avg_size": sum(t[4] for t in trades) / total_trades,  # size is index 4
                "avg_leverage": sum(t[5] for t in trades) / total_trades  # leverage is index 5
            }
            
        except Exception as e:
            logger.error(f"Performance analysis error: {e}")
            return {"period_days": days, "total_trades": 0, "error": str(e)}
    


    # FILE SHARING METHODS (for cross-process communication)
    def _save_to_json_file(self):
        """Save current state to JSON file for cross-process sharing"""
        try:
            # Create a simplified state for file sharing
            file_state = {
                "session": self.current_state["session"],
                "predictions": self.current_state["predictions"],
                "recent_activity": list(self.recent_activity),
                "recent_signals": list(self.recent_signals),
                "recent_trades": list(self.recent_trades),
                "last_update": time.time()
            }
            
            # Save to JSON file
            json_file_path = os.path.join(os.path.dirname(__file__), "..", "rtm_state.json")
            with open(json_file_path, 'w') as f:
                json.dump(file_state, f, indent=2, default=str)
                
        except Exception as e:
            logger.debug(f"Error saving to JSON file: {e}")
    
    def _load_from_json_file(self):
        """Load state from JSON file for cross-process sharing"""
        try:
            json_file_path = os.path.join(os.path.dirname(__file__), "..", "rtm_state.json")
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r') as f:
                    file_state = json.load(f)
                
                # Update current state with file data
                if file_state.get("session"):
                    self.current_state["session"].update(file_state["session"])
                
                # Load predictions
                if file_state.get("predictions"):
                    self.current_state["predictions"] = file_state["predictions"]
                
                # Load activity
                if file_state.get("recent_activity"):
                    self.recent_activity = deque(file_state["recent_activity"], maxlen=self.MAX_ACTIVITY)
                
                # Load signals
                if file_state.get("recent_signals"):
                    self.recent_signals = deque(file_state["recent_signals"], maxlen=self.MAX_SIGNALS)
                
                # Load recent trades
                if file_state.get("recent_trades"):
                    self.recent_trades = deque(file_state["recent_trades"], maxlen=self.MAX_TRADES)
                    
                logger.debug(f"Loaded state from JSON file: {len(file_state.get('predictions', []))} predictions, {len(file_state.get('recent_activity', []))} activities")
                
        except Exception as e:
            logger.debug(f"Error loading from JSON file: {e}")

    # UTILITY METHODS
    def clear_all_data(self):
        """Clear all in-memory data (for testing)"""
        with self.data_lock:
            self.recent_trades.clear()
            self.recent_signals.clear()
            self.recent_activity.clear()
            self.open_positions.clear()
            
            # Reset session
            self.current_state["session"]["status"] = "INACTIVE"
            self.current_state["session"]["total_trades"] = 0
            self.current_state["session"]["winning_trades"] = 0
            self.current_state["session"]["losing_trades"] = 0
            
            logger.warning("🧹 All real-time data cleared")
    
    def export_to_json(self, filepath: str):
        """Export current state to JSON file"""
        try:
            state = self.get_current_state()
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            logger.success(f"📁 State exported to {filepath}")
        except Exception as e:
            logger.error(f"Export error: {e}")


# Global instance (singleton)
trading_data_manager = RealTimeTradingDataManager()