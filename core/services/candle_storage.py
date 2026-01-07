#!/usr/bin/env python3
"""
Candle Storage Service
Persistent storage for 5m candles with rolling 5-year window
"""

import os
import sqlite3
import time
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
        
        # Initialize database
        self._init_database()
        
        logger.info(f"💾 Candle Storage initialized: {self.db_path}")
    
    def _init_database(self):
        """Initialize SQLite database with schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
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
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize candle storage database: {e}")
            raise
    
    def get_last_timestamp(self) -> Optional[float]:
        """
        Get the timestamp of the last stored candle
        
        Returns:
            Timestamp of last candle, or None if database is empty
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT MAX(timestamp) FROM candles_5m")
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] if result and result[0] else None
            
        except Exception as e:
            logger.error(f"❌ Failed to get last timestamp: {e}")
            return None
    
    def get_first_timestamp(self) -> Optional[float]:
        """
        Get the timestamp of the first stored candle
        
        Returns:
            Timestamp of first candle, or None if database is empty
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT MIN(timestamp) FROM candles_5m")
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] if result and result[0] else None
            
        except Exception as e:
            logger.error(f"❌ Failed to get first timestamp: {e}")
            return None
    
    def insert_candles(self, candles: List[Dict[str, Any]]):
        """
        Insert candles into database (with conflict handling - replace if exists)
        
        Args:
            candles: List of candle dictionaries with timestamp, open, high, low, close, volume
        """
        if not candles:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for candle in candles:
                cursor.execute("""
                    INSERT OR REPLACE INTO candles_5m 
                    (timestamp, open, high, low, close, volume, trades_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    candle.get('timestamp', 0),
                    candle.get('open', 0),
                    candle.get('high', 0),
                    candle.get('low', 0),
                    candle.get('close', 0),
                    candle.get('volume', 0),
                    candle.get('trades_count', 0)
                ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"💾 Inserted {len(candles)} candles into storage")
            
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
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, open, high, low, close, volume, trades_count
                FROM candles_5m
                ORDER BY timestamp DESC
                LIMIT ?
            """, (count,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to dictionaries (oldest first)
            candles = [dict(row) for row in reversed(rows)]
            
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to get candles by count: {e}")
            return []
    
    def get_candles_by_range(self, start_timestamp: float, end_timestamp: float) -> List[Dict[str, Any]]:
        """
        Get candles within a timestamp range
        
        Args:
            start_timestamp: Start timestamp (inclusive)
            end_timestamp: End timestamp (inclusive)
            
        Returns:
            List of candle dictionaries, sorted by timestamp (oldest first)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, open, high, low, close, volume, trades_count
                FROM candles_5m
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            """, (start_timestamp, end_timestamp))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to dictionaries
            candles = [dict(row) for row in rows]
            
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to get candles by range: {e}")
            return []
    
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
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
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
            conn.close()
            
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
            return []
    
    def cleanup_old_candles(self, years: float = 5.0):
        """
        Remove candles older than specified years (rolling window)
        
        Args:
            years: Number of years to keep (default: 5.0)
        """
        try:
            current_time = time.time()
            cutoff_timestamp = current_time - (years * 365 * 24 * 3600)  # 5 years ago
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM candles_5m WHERE timestamp < ?", (cutoff_timestamp,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
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
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM candles_5m")
            count = cursor.fetchone()[0]
            
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"❌ Failed to get candle count: {e}")
            return 0
    
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
            all_candles.sort(key=lambda x: x.get('timestamp', 0))
            
            # Remove duplicates (same timestamp)
            seen_timestamps = set()
            unique_candles = []
            for candle in all_candles:
                ts = candle.get('timestamp', 0)
                if ts not in seen_timestamps:
                    seen_timestamps.add(ts)
                    unique_candles.append(candle)
            
            # Filter to exact time range (remove any outside 5 years)
            cutoff_timestamp = current_time - (years * 365 * 24 * 3600)
            filtered_candles = [c for c in unique_candles if cutoff_timestamp <= c.get('timestamp', 0) <= current_time]
            
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
                    "open": float(candle.get("o", "0")),
                    "high": float(candle.get("h", "0")),
                    "low": float(candle.get("l", "0")),
                    "close": float(candle.get("c", "0")),
                    "volume": float(candle.get("v", "0")),
                    "timestamp": int(candle.get("t", time.time() * 1000)) // 1000,  # Convert ms to seconds
                    "trades_count": 0  # Hyperliquid doesn't provide trades count in candle data
                }
                candles.append(formatted_candle)
            
            # Sort by timestamp (oldest first)
            candles.sort(key=lambda x: x.get('timestamp', 0))
            
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
            completed_candles = [c for c in candles if c.get('timestamp', 0) < current_5m_start]
            
            # Sort candles by timestamp (oldest first)
            completed_candles.sort(key=lambda x: x.get('timestamp', 0))
            
            # Filter to only new candles (after last_timestamp)
            new_candles = [c for c in completed_candles if c.get('timestamp', 0) > last_timestamp]
            
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
            completed_candles = [c for c in candles if c.get('timestamp', 0) < current_5m_start]
            
            if not completed_candles:
                logger.debug(f"💾 No completed candles yet (current 5m start: {datetime.fromtimestamp(current_5m_start).strftime('%H:%M:%S')})")
                return
            
            # Get the most recent completed candle
            latest_candle = max(completed_candles, key=lambda x: x.get('timestamp', 0))
            latest_timestamp = latest_candle.get('timestamp', 0)
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
            
            logger.info(f"✅ New candle added to database: timestamp={latest_timestamp}, datetime={latest_datetime.strftime('%Y-%m-%d %H:%M:%S')} UTC, price=${latest_candle.get('close', 0):.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update with latest candle: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

