#!/usr/bin/env python3
"""
Database Manager
Handles all SQLite database operations for trading data persistence
Single Responsibility: Database operations and data persistence
"""

import sqlite3
import time
import threading
from typing import Dict, Any, List, Optional
from loguru import logger


class DatabaseManager:
    """
    Database manager for trading data persistence
    Single Responsibility: All SQLite database operations
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for database connection management"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.db_path = "trading_data.db"
        self.connection_lock = threading.RLock()
        
        # Initialize database
        self._init_database()
        
        logger.success("🗄️ Database Manager initialized")
    
    def _init_database(self):
        """Initialize SQLite database with trading tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create trades table
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
            
            # Create market data table
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
            
            # Create trading signals table
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
            
            # Create trading sessions table
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
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection (thread-safe)"""
        return sqlite3.connect(self.db_path)
    
    # TRADE OPERATIONS
    def save_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Save a trade to database"""
        try:
            with self.connection_lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO trades 
                    (trade_id, side, entry_price, exit_price, size, leverage, pnl, pnl_pct, 
                     confidence, entry_time, exit_time, holding_time, exit_reason, was_profitable, is_winback_trade)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade_data.get("trade_id"),
                    trade_data.get("side"),
                    trade_data.get("entry_price", 0),
                    trade_data.get("exit_price", 0),
                    trade_data.get("size", 0),
                    trade_data.get("leverage", 1),
                    trade_data.get("pnl", 0),
                    trade_data.get("pnl_pct", 0),
                    trade_data.get("confidence", 0),
                    trade_data.get("entry_time", time.time()),
                    trade_data.get("exit_time", time.time()),
                    trade_data.get("holding_time", 0),
                    trade_data.get("exit_reason", "UNKNOWN"),
                    trade_data.get("was_profitable", False),
                    trade_data.get("is_winback_trade", False)
                ))
                
                conn.commit()
                conn.close()
                
                logger.debug(f"💾 Trade saved to database: {trade_data.get('trade_id')}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving trade to database: {e}")
            return False
    
    def get_historical_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical trades from database"""
        try:
            with self.connection_lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM trades 
                    ORDER BY entry_time DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                
                # Get column names
                columns = [description[0] for description in cursor.description]
                
                conn.close()
                
                # Convert to dictionaries
                trades = [dict(zip(columns, row)) for row in rows]
                
                logger.debug(f"📂 Retrieved {len(trades)} historical trades")
                return trades
                
        except Exception as e:
            logger.error(f"Error retrieving historical trades: {e}")
            return []
    
    # SIGNAL OPERATIONS
    def save_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Save a trading signal to database"""
        try:
            with self.connection_lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO trading_signals 
                    (signal_type, side, entry_price, confidence, timeframe, reason, was_executed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal_data.get("signal_type", "UNKNOWN"),
                    signal_data.get("side", "UNKNOWN"),
                    signal_data.get("entry_price", 0),
                    signal_data.get("confidence", 0),
                    signal_data.get("timeframe", 0),
                    signal_data.get("reason", ""),
                    signal_data.get("was_executed", False)
                ))
                
                conn.commit()
                conn.close()
                
                logger.debug(f"💾 Signal saved to database: {signal_data.get('signal_type')}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving signal to database: {e}")
            return False
    
    # SESSION OPERATIONS
    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """Save a trading session to database"""
        try:
            with self.connection_lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO trading_sessions 
                    (session_id, start_time, end_time, strategy, initial_balance, final_balance, 
                     balance_change, balance_change_pct, total_trades, winning_trades, losing_trades, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_data.get("session_id"),
                    session_data.get("start_time"),
                    session_data.get("end_time"),
                    session_data.get("strategy"),
                    session_data.get("initial_balance"),
                    session_data.get("final_balance"),
                    session_data.get("balance_change"),
                    session_data.get("balance_change_pct"),
                    session_data.get("total_trades"),
                    session_data.get("winning_trades"),
                    session_data.get("losing_trades"),
                    session_data.get("status")
                ))
                
                conn.commit()
                conn.close()
                
                logger.debug(f"💾 Session saved to database: {session_data.get('session_id')}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving session to database: {e}")
            return False
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trading sessions"""
        try:
            with self.connection_lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM trading_sessions 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                
                # Get column names
                columns = [description[0] for description in cursor.description]
                
                conn.close()
                
                # Convert to dictionaries
                sessions = [dict(zip(columns, row)) for row in rows]
                
                logger.debug(f"📂 Retrieved {len(sessions)} recent sessions")
                return sessions
                
        except Exception as e:
            logger.error(f"Error retrieving recent sessions: {e}")
            return []
    
    # MARKET DATA OPERATIONS
    def save_market_data_snapshot(self, market_data: Dict[str, Any]) -> bool:
        """Save market data snapshot to database"""
        try:
            with self.connection_lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO market_data 
                    (timestamp, price, trend, market_condition, rsi, volume, 
                     volatility_5m, volatility_1h, orderbook_imbalance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    time.time(),
                    market_data.get("current_price", 0),
                    market_data.get("trend", "UNKNOWN"),
                    market_data.get("market_condition", "UNKNOWN"),
                    market_data.get("rsi", 50.0),
                    market_data.get("volume_depth", 0),
                    market_data.get("volatility_5m", 0),
                    market_data.get("volatility_1h", 0),
                    market_data.get("orderbook_imbalance", 0)
                ))
                
                conn.commit()
                conn.close()
                
                logger.debug("💾 Market data snapshot saved")
                return True
                
        except Exception as e:
            logger.error(f"Error saving market data snapshot: {e}")
            return False
    
    # PERFORMANCE ANALYSIS
    def get_performance_analysis(self, days: int = 7) -> Dict[str, Any]:
        """Get performance analysis for specified period"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            
            with self.connection_lock:
                conn = self._get_connection()
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
            logger.error(f"Error getting performance analysis: {e}")
            return {"period_days": days, "total_trades": 0, "error": str(e)}
    
    # CLEANUP OPERATIONS
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old database records"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 3600)
            
            with self.connection_lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Clean old market data
                cursor.execute('DELETE FROM market_data WHERE timestamp < ?', (cutoff_time,))
                market_deleted = cursor.rowcount
                
                # Clean old signals (keep trades forever for analysis)
                cursor.execute('DELETE FROM trading_signals WHERE created_at < datetime(?, "unixepoch")', (cutoff_time,))
                signals_deleted = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                logger.info(f"🧹 Database cleanup: {market_deleted} market records, {signals_deleted} signals deleted")
                
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
    
    # UTILITY METHODS
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.connection_lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                stats = {}
                
                # Count records in each table
                for table in ['trades', 'trading_signals', 'trading_sessions', 'market_data']:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    stats[f'{table}_count'] = cursor.fetchone()[0]
                
                # Get database file size
                cursor.execute('PRAGMA page_count')
                page_count = cursor.fetchone()[0]
                cursor.execute('PRAGMA page_size')
                page_size = cursor.fetchone()[0]
                stats['database_size_bytes'] = page_count * page_size
                stats['database_size_mb'] = stats['database_size_bytes'] / (1024 * 1024)
                
                conn.close()
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}


# Global instance (singleton)
database_manager = DatabaseManager()