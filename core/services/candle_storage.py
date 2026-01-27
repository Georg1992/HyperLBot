#!/usr/bin/env python3
"""
Candle Storage Service
Persistent storage for 5m candles with rolling 5-year window
"""

import os
import sqlite3
import time
import threading
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger


class CandleStorage:
    """
    Persistent storage for 5m candles with rolling 5-year window
    
    Features:
    - SQLite database for efficient storage and queries
    - Rolling 5-year window (auto-cleanup of old data)
    - Startup backfill (fills missing candles on bot start)
    - Continuous updates (appends new candles every 5 minutes)
    - Fast local queries (no API calls needed)
    """
    
    def __init__(self, symbol: str = "BTC", data_dir: str = "data"):
        """
        Initialize candle storage
        
        Args:
            symbol: Trading symbol (default: "BTC")
            data_dir: Directory for data files (default: "data")
        """
        self.symbol = symbol
        self.data_dir = data_dir
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Database file path
        self.db_path = os.path.join(data_dir, f"candles_5m_{symbol.lower()}.db")
        
        # Thread safety lock for database operations
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"💾 Candle Storage initialized: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections - ensures proper cleanup
        
        CRITICAL FIX: Proper transaction management with rollback on errors.
        Only commits if no exception occurred.
        
        Usage:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # ... operations ...
                # Auto-commits on successful exit, rolls back on exception
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like row access
            # Enable WAL mode for better concurrency (fixes issue #5)
            conn.execute("PRAGMA journal_mode=WAL;")
            yield conn
            # Only commit if no exception occurred
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """
        Initialize SQLite database with schema
        
        CRITICAL FIX: Enables WAL mode for better concurrency (fixes issue #5).
        WAL mode allows concurrent reads while writes are in progress.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # CRITICAL: Enable WAL mode for better concurrency
                # This allows concurrent reads while writes are in progress
                # Fixes the blocking issue where ML training was disabled
                cursor.execute("PRAGMA journal_mode=WAL;")
                # Set synchronous mode to NORMAL for better performance with WAL
                cursor.execute("PRAGMA synchronous=NORMAL;")
                # Increase cache size for better performance
                cursor.execute("PRAGMA cache_size=-64000;")  # 64MB cache
                
                # Create candles table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS candles_5m (
                        timestamp REAL PRIMARY KEY,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume REAL NOT NULL,
                        trades_count INTEGER DEFAULT 0
                    )
                """)
                
                # Create index on timestamp for fast queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON candles_5m(timestamp)
                """)
                
                # Create indexes on low and high for price range queries (smart S/R detection)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_low 
                    ON candles_5m(low)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_high 
                    ON candles_5m(high)
                """)
                
                logger.info("✅ Database initialized with WAL mode (concurrent read/write enabled)")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize candle storage database: {e}")
            raise
    
    def get_last_timestamp(self) -> Optional[float]:
        """
        Get the timestamp of the last stored candle
        
        Returns:
            Timestamp of last candle, or None if database is empty
            
        Raises:
            Exception: If database operation fails (NO FALLBACKS)
        """
        with self._lock:  # Thread-safe
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT MAX(timestamp) FROM candles_5m")
                    result = cursor.fetchone()
                    return result[0] if result and result[0] else None
                    
            except Exception as e:
                logger.error(f"❌ Failed to get last timestamp: {e}")
                raise  # NO FALLBACKS - raise instead of returning None
    
    def get_first_timestamp(self) -> Optional[float]:
        """
        Get the timestamp of the first stored candle
        
        Returns:
            Timestamp of first candle, or None if database is empty
            
        Raises:
            Exception: If database operation fails (NO FALLBACKS)
        """
        with self._lock:  # Thread-safe
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT MIN(timestamp) FROM candles_5m")
                    result = cursor.fetchone()
                    return result[0] if result and result[0] else None
                    
            except Exception as e:
                logger.error(f"❌ Failed to get first timestamp: {e}")
                raise  # NO FALLBACKS - raise instead of returning None
    
    def insert_candles(self, candles: List[Dict[str, Any]]):
        """
        Insert candles into database (with conflict handling - replace if exists)
        
        CRITICAL FIX: Uses explicit transaction for atomic batch operations.
        All candles are inserted atomically - if any fails, entire batch is rolled back.
        
        Args:
            candles: List of candle dictionaries with timestamp, open, high, low, close, volume
            
        Raises:
            Exception: If database operation fails (NO FALLBACKS)
        """
        if not candles:
            return
        
        with self._lock:  # Thread-safe
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # CRITICAL: Begin explicit transaction for atomic batch insert
                    # This ensures all candles are inserted atomically
                    # If any candle insert fails, entire batch is rolled back
                    cursor.execute("BEGIN TRANSACTION")
                    
                    try:
                        for candle in candles:
                            cursor.execute("""
                                INSERT OR REPLACE INTO candles_5m 
                                (timestamp, open, high, low, close, volume, trades_count)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                candle['timestamp'] if 'timestamp' in candle else 0,
                                candle['open'] if 'open' in candle else 0,
                                candle['high'] if 'high' in candle else 0,
                                candle['low'] if 'low' in candle else 0,
                                candle['close'] if 'close' in candle else 0,
                                candle['volume'] if 'volume' in candle else 0,
                                candle['trades_count'] if 'trades_count' in candle else 0
                            ))
                        
                        # Commit transaction only after all inserts succeed
                        conn.commit()
                        logger.debug(f"💾 Inserted {len(candles)} candles into storage (atomic transaction)")
                        
                    except Exception as e:
                        # Rollback transaction on any error
                        conn.rollback()
                        logger.error(f"❌ Failed to insert candles batch - transaction rolled back: {e}")
                        raise
                
            except Exception as e:
                logger.error(f"❌ Failed to insert candles: {e}")
                raise
    
    def get_candles_by_count(self, count: int) -> List[Dict[str, Any]]:
        """
        Get the last N candles from database
        
        Args:
            count: Number of candles to retrieve
            
        Returns:
            List of candle dictionaries, sorted by timestamp (oldest first)
            
        Raises:
            Exception: If database operation fails (NO FALLBACKS)
        """
        with self._lock:  # Thread-safe
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT timestamp, open, high, low, close, volume, trades_count
                        FROM candles_5m
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (count,))
                    
                    rows = cursor.fetchall()
                    
                    # Convert rows to dictionaries (oldest first)
                    candles = [dict(row) for row in reversed(rows)]
                    return candles
                    
            except Exception as e:
                logger.error(f"❌ Failed to get candles by count: {e}")
                raise  # NO FALLBACKS - raise instead of returning empty list
    
    def get_candles_by_range(self, start_timestamp: float, end_timestamp: float) -> List[Dict[str, Any]]:
        """
        Get candles within a timestamp range
        
        Args:
            start_timestamp: Start timestamp (inclusive)
            end_timestamp: End timestamp (inclusive)
            
        Returns:
            List of candle dictionaries, sorted by timestamp (oldest first)
            
        Raises:
            Exception: If database operation fails (NO FALLBACKS)
        """
        with self._lock:  # Thread-safe
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT timestamp, open, high, low, close, volume, trades_count
                        FROM candles_5m
                        WHERE timestamp >= ? AND timestamp <= ?
                        ORDER BY timestamp ASC
                    """, (start_timestamp, end_timestamp))
                    
                    rows = cursor.fetchall()
                    
                    # Convert rows to dictionaries
                    candles = [dict(row) for row in rows]
                    return candles
                    
            except Exception as e:
                logger.error(f"❌ Failed to get candles by range: {e}")
                raise  # NO FALLBACKS - raise instead of returning empty list
    
    def get_candles_by_price_range(self, min_price: float, max_price: float, 
                                   max_candles: int = 50000,
                                   min_timestamp: float = None) -> List[Dict[str, Any]]:
        """
        Get candles that have lows/highs within a price range AND time range (smart query for S/R detection)
        This is much more efficient than fetching all candles and filtering
        
        Args:
            min_price: Minimum price (for support levels, this is liquidation price)
            max_price: Maximum price (for support levels, this is current price)
            max_candles: Maximum number of candles to return (default: 50,000)
            min_timestamp: Optional minimum timestamp (seconds) - only return candles after this time
            
        Returns:
            List of candle dictionaries where:
            - low <= max_price AND high >= min_price (price range overlap)
            - timestamp >= min_timestamp (if provided)
            sorted by timestamp (oldest first)
            
        Raises:
            Exception: If database operation fails (NO FALLBACKS)
        """
        with self._lock:  # Thread-safe
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Query candles where the price range overlaps with our target range
                    # A candle is relevant if: low <= max_price AND high >= min_price
                    # Also filter by time if min_timestamp is provided
                    if min_timestamp is not None:
                        cursor.execute("""
                            SELECT timestamp, open, high, low, close, volume, trades_count
                            FROM candles_5m
                            WHERE low <= ? AND high >= ? AND timestamp >= ?
                            ORDER BY timestamp DESC
                            LIMIT ?
                        """, (max_price, min_price, min_timestamp, max_candles))
                    else:
                        cursor.execute("""
                            SELECT timestamp, open, high, low, close, volume, trades_count
                            FROM candles_5m
                            WHERE low <= ? AND high >= ?
                            ORDER BY timestamp DESC
                            LIMIT ?
                        """, (max_price, min_price, max_candles))
                    
                    rows = cursor.fetchall()
                    
                    # Convert rows to dictionaries and reverse to get oldest first
                    candles = [dict(row) for row in reversed(rows)]
                    
                    # Only log if significant number found (reduce noise)
                    if len(candles) > 1000:
                        if min_timestamp is not None:
                            logger.debug(f"🔍 Smart query (price + time): Found {len(candles)} candles in price range ${min_price:.2f}-${max_price:.2f}")
                        else:
                            logger.debug(f"🔍 Price range query: Found {len(candles)} candles in price range ${min_price:.2f}-${max_price:.2f}")
                    
                    return candles
                    
            except Exception as e:
                logger.error(f"❌ Failed to get candles by price range: {e}")
                raise  # NO FALLBACKS - raise instead of returning empty list
    
    def cleanup_old_candles(self, years: float = 5.0):
        """
        Remove candles older than specified years (rolling window)
        
        Args:
            years: Number of years to keep (default: 5.0)
            
        Raises:
            Exception: If database operation fails (NO FALLBACKS)
        """
        with self._lock:  # Thread-safe
            try:
                current_time = time.time()
                cutoff_timestamp = current_time - (years * 365 * 24 * 3600)  # 5 years ago
                
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM candles_5m WHERE timestamp < ?", (cutoff_timestamp,))
                    deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    logger.info(f"🧹 Cleaned up {deleted_count} candles older than {years} years")
                
            except Exception as e:
                logger.error(f"❌ Failed to cleanup old candles: {e}")
                raise
    
    def get_candle_count(self) -> int:
        """
        Get total number of candles in database
        
        Returns:
            Number of candles
            
        Raises:
            Exception: If database operation fails (NO FALLBACKS)
        """
        with self._lock:  # Thread-safe
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM candles_5m")
                    count = cursor.fetchone()[0]
                    return count
                    
            except Exception as e:
                logger.error(f"❌ Failed to get candle count: {e}")
                raise  # NO FALLBACKS - raise instead of returning 0
    
    def initialize_with_historical_data(self, years: float = 5.0):
        """
        Initialize database with historical 5m candles (download 5 years)
        Uses batch fetching to get around API limits
        
        Args:
            years: Number of years of historical data to download (default: 5.0)
        """
        try:
            # Check if database already has data
            candle_count = self.get_candle_count()
            if candle_count > 0:
                logger.info(f"💾 Candle storage already initialized with {candle_count} candles")
                return
            
            logger.info(f"📥 Initializing candle storage with {years} years of historical data...")
            
            # Calculate time range
            current_time = time.time()
            start_time = current_time - (years * 365 * 24 * 3600)  # 5 years ago
            
            # Fetch in batches (API limit is ~5000 candles per request)
            # Each batch = ~17 days of 5m candles (5000 candles / 288 candles per day)
            candles_per_day = 24 * 60 / 5  # 288 candles per day
            candles_per_batch = 5000  # Safe limit based on API response
            days_per_batch = candles_per_batch / candles_per_day  # ~17.4 days per batch
            
            total_days = years * 365
            num_batches = int((total_days / days_per_batch) + 1)  # Round up
            
            logger.info(f"📥 Fetching {total_days:.0f} days of data in {num_batches} batches (~{days_per_batch:.1f} days per batch)...")
            logger.info("📊 Using Hyperliquid API for initial historical data fetch...")
            
            all_candles = []
            from core.api.hyperliquid_api import get_hyperliquid_api
            hyperliquid_api = get_hyperliquid_api()
            
            # Fetch batches from oldest to newest
            for batch_num in range(num_batches):
                # Calculate batch time range
                batch_start_time = start_time + (batch_num * days_per_batch * 24 * 3600)
                batch_end_time = min(
                    start_time + ((batch_num + 1) * days_per_batch * 24 * 3600),
                    current_time
                )
                
                # Calculate how many candles in this batch
                batch_days = (batch_end_time - batch_start_time) / (24 * 3600)
                batch_candle_count = int(batch_days * candles_per_day)
                
                logger.info(f"📥 Batch {batch_num + 1}/{num_batches}: Fetching {batch_candle_count} candles from {datetime.fromtimestamp(batch_start_time).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(batch_end_time).strftime('%Y-%m-%d')}...")
                
                # Fetch candles for this time range using Hyperliquid API
                batch_candles = self._fetch_candles_from_hyperliquid(
                    hyperliquid_api, batch_start_time, batch_end_time
                )
                
                if batch_candles:
                    all_candles.extend(batch_candles)
                    logger.info(f"✅ Batch {batch_num + 1}/{num_batches}: Fetched {len(batch_candles)} candles (total: {len(all_candles)})")
                else:
                    logger.warning(f"⚠️ Batch {batch_num + 1}/{num_batches}: No candles returned")
                
                # Small delay to avoid rate limits
                time.sleep(0.2)
            
            if not all_candles:
                logger.error("❌ Failed to download any historical candles")
                return
            
            # Sort candles by timestamp (oldest first) and remove duplicates
            all_candles.sort(key=lambda x: x['timestamp'] if 'timestamp' in x else 0)
            
            # Remove duplicates (same timestamp)
            seen_timestamps = set()
            unique_candles = []
            for candle in all_candles:
                ts = candle['timestamp'] if 'timestamp' in candle else 0
                if ts not in seen_timestamps:
                    seen_timestamps.add(ts)
                    unique_candles.append(candle)
            
            # Filter to exact time range (remove any outside 5 years)
            cutoff_timestamp = current_time - (years * 365 * 24 * 3600)
            filtered_candles = [c for c in unique_candles if 'timestamp' in c and cutoff_timestamp <= c['timestamp'] <= current_time]
            
            # Insert into database
            self.insert_candles(filtered_candles)
            
            # Cleanup any older data
            self.cleanup_old_candles(years)
            
            logger.info(f"✅ Candle storage initialized with {len(filtered_candles)} candles ({years} years)")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize candle storage with historical data: {e}")
            raise
    
    def _fetch_candles_from_hyperliquid(self, hyperliquid_api, start_timestamp: float, end_timestamp: float) -> List[Dict[str, Any]]:
        """
        Fetch candles for a specific time range using Hyperliquid API
        
        Args:
            hyperliquid_api: HyperliquidAPI instance
            start_timestamp: Start timestamp (seconds)
            end_timestamp: End timestamp (seconds)
            
        Returns:
            List of candle dictionaries
        """
        try:
            # Convert timestamps to milliseconds for Hyperliquid API
            start_time_ms = int(start_timestamp * 1000)
            end_time_ms = int(end_timestamp * 1000)
            
            # Hyperliquid API endpoint for historical data
            url = f"{hyperliquid_api.base_url}/info"
            
            # Request payload for historical candles
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": self.symbol,
                    "interval": "5m",
                    "startTime": start_time_ms,
                    "endTime": end_time_ms
                }
            }
            
            response = hyperliquid_api.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list) or len(data) == 0:
                logger.warning(f"⚠️ No candles returned from Hyperliquid for range {start_timestamp} to {end_timestamp}")
                return []
            
            # Convert Hyperliquid format to our format
            candles = []
            for candle in data:
                formatted_candle = {
                    "open": float(candle["o"]) if "o" in candle else 0.0,
                    "high": float(candle["h"]) if "h" in candle else 0.0,
                    "low": float(candle["l"]) if "l" in candle else 0.0,
                    "close": float(candle["c"]) if "c" in candle else 0.0,
                    "volume": float(candle["v"]) if "v" in candle else 0.0,
                    "timestamp": int(candle["t"]) // 1000 if "t" in candle else int(time.time()),  # Convert ms to seconds
                    "trades_count": 0  # Hyperliquid doesn't provide trades count in candle data
                }
                candles.append(formatted_candle)
            
            # Sort by timestamp (oldest first)
            candles.sort(key=lambda x: x['timestamp'] if 'timestamp' in x else 0)
            
            return candles
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch candles from Hyperliquid: {e}")
            return []
    
    def backfill_missing_candles(self):
        """
        Fill missing candles on startup (from last stored candle to current time)
        """
        try:
            last_timestamp = self.get_last_timestamp()
            current_time = time.time()
            
            if last_timestamp is None:
                # Database is empty, initialize with historical data
                logger.info("💾 Database is empty, initializing with historical data...")
                self.initialize_with_historical_data()
                return
            
            # Calculate how many 5-minute intervals are missing
            # 5 minutes = 300 seconds
            time_gap = current_time - last_timestamp
            missing_intervals = int(time_gap / 300)  # Number of 5-minute candles missing
            
            if missing_intervals <= 0:
                logger.debug("💾 Candle storage is up to date")
                return
            
            logger.info(f"📥 Backfilling {missing_intervals} missing candles (from {datetime.fromtimestamp(last_timestamp)} to {datetime.fromtimestamp(current_time)})...")
            
            # Fetch missing candles from API (fetch enough to cover the gap)
            from core.api.hyperliquid_api import get_hyperliquid_api
            hyperliquid_api = get_hyperliquid_api()
            
            # Fetch slightly more than needed to ensure we get all missing candles
            fetch_count = min(missing_intervals + 100, 10000)  # API limit is typically 10000
            candles = hyperliquid_api.get_historical_candles(self.symbol, "5m", fetch_count)
            
            if not candles:
                logger.warning("⚠️ Failed to download missing candles")
                return
            
            # Filter out ongoing candles - only use completed candles
            current_time = time.time()
            current_5m_start = (int(current_time) // 300) * 300  # Round to 5-minute boundary
            completed_candles = [c for c in candles if 'timestamp' in c and c['timestamp'] < current_5m_start]
            
            # Sort candles by timestamp (oldest first)
            completed_candles.sort(key=lambda x: x['timestamp'] if 'timestamp' in x else 0)
            
            # Filter to only new candles (after last_timestamp)
            new_candles = [c for c in completed_candles if 'timestamp' in c and c['timestamp'] > last_timestamp]
            
            # Insert into database
            if new_candles:
                self.insert_candles(new_candles)
                
                # Cleanup old candles (rolling 5-year window)
                self.cleanup_old_candles(5.0)
                
                logger.info(f"✅ Backfilled {len(new_candles)} candles")
            else:
                logger.debug("💾 No new candles to backfill")
            
        except Exception as e:
            logger.error(f"❌ Failed to backfill missing candles: {e}")
            raise
    
    def update_with_latest_candle(self):
        """
        Update storage with the latest completed 5m candle
        Called exactly at 5-minute boundaries (00, 05, 10, 15, etc.) while bot is running
        """
        try:
            from datetime import datetime
            current_utc = datetime.utcnow()
            minute = current_utc.minute
            second = current_utc.second
            
            # Verify we're at exact 5-minute boundary (00, 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
            # Candles should appear at these exact UTC times
            expected_minute = (minute // 5) * 5
            is_at_boundary = (minute % 5 == 0) and (second < 10)  # Within 10 seconds of boundary
            
            # Log exact timing with boundary verification
            boundary_status = "✅ AT BOUNDARY" if is_at_boundary else f"⚠️ NOT AT BOUNDARY (expected: {expected_minute:02d}:00, actual: {minute:02d}:{second:02d})"
            logger.info(f"🕐 Candle storage update: {current_utc.strftime('%H:%M:%S')} UTC - {boundary_status}")
            
            # Get the latest candle from API
            from core.api.hyperliquid_api import get_hyperliquid_api
            hyperliquid_api = get_hyperliquid_api()
            
            # Fetch multiple candles to ensure we get the last COMPLETED one (not ongoing)
            # Fetch 5 candles to be safe, then filter out ongoing ones
            candles = hyperliquid_api.get_historical_candles(self.symbol, "5m", 5)
            
            if not candles or len(candles) == 0:
                logger.warning("⚠️ No latest candle available for update")
                return
            
            # Filter out ongoing candles - a candle is "ongoing" if its timestamp matches the current 5-minute boundary
            # and it's less than 5 minutes old (not yet completed)
            current_time = time.time()
            current_5m_start = (int(current_time) // 300) * 300  # Round to 5-minute boundary
            
            # Find the last COMPLETED candle (timestamp < current_5m_start)
            completed_candles = [c for c in candles if 'timestamp' in c and c['timestamp'] < current_5m_start]
            
            if not completed_candles:
                logger.debug(f"💾 No completed candles yet (current 5m start: {datetime.fromtimestamp(current_5m_start).strftime('%H:%M:%S')})")
                return
            
            # Get the most recent completed candle
            latest_candle = max(completed_candles, key=lambda x: x['timestamp'] if 'timestamp' in x else 0)
            latest_timestamp = latest_candle['timestamp'] if 'timestamp' in latest_candle else 0
            latest_datetime = datetime.fromtimestamp(latest_timestamp)
            
            # Check if this candle is already in storage
            last_stored_timestamp = self.get_last_timestamp()
            
            if last_stored_timestamp is not None and latest_timestamp <= last_stored_timestamp:
                # Latest candle is already stored, nothing to update
                logger.debug(f"💾 Latest candle already stored (timestamp: {latest_timestamp}, datetime: {latest_datetime.strftime('%H:%M:%S')})")
                return
            
            # Insert the new candle
            self.insert_candles([latest_candle])
            
            # Cleanup old candles (rolling 5-year window)
            self.cleanup_old_candles(5.0)
            
            candle_close = latest_candle['close'] if 'close' in latest_candle else 0
            logger.info(f"✅ New candle added to database: timestamp={latest_timestamp}, datetime={latest_datetime.strftime('%Y-%m-%d %H:%M:%S')} UTC, price=${candle_close:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update with latest candle: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

