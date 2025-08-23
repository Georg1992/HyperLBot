#!/usr/bin/env python3
"""
Progressive Data Accumulator
Intelligently accumulates historical data over time for improved predictions
Balances memory efficiency with comprehensive historical context
"""

import time
import json
import sqlite3
import threading
from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime, timedelta
from collections import deque
import os

class ProgressiveDataAccumulator:
    """
    Progressive data accumulator for building comprehensive historical datasets
    - Accumulates data over time instead of discarding it
    - Uses intelligent storage strategies (memory + database)
    - Provides larger datasets for machine learning
    - Manages memory efficiently with tiered storage
    """
    
    def __init__(self, db_path: str = "historical_trading_data.db"):
        self.db_path = db_path
        self.cache_lock = threading.Lock()
        
        # MEMORY BUFFERS (for fastest access - recent data)
        self.memory_buffers = {
            "1m": deque(maxlen=480),    # 8 hours in memory
            "5m": deque(maxlen=576),    # 48 hours in memory  
            "1h": deque(maxlen=720),    # 30 days in memory
            "1d": deque(maxlen=365)     # 1 year in memory
        }
        
        # DATABASE STORAGE (for long-term accumulation)
        self.db_storage_limits = {
            "1m": 30 * 24 * 60,        # 30 days of 1m data
            "5m": 90 * 24 * 12,        # 90 days of 5m data
            "1h": 365 * 24,            # 1 year of 1h data  
            "1d": 5 * 365              # 5 years of 1d data
        }
        
        # Performance tracking
        self.total_candles_accumulated = 0
        self.session_start_time = time.time()
        self.data_quality_score = 0.0
        
        # Initialize database
        self._initialize_database()
        
        logger.info("📈 Progressive Data Accumulator initialized")
        logger.info(f"   Memory buffers: {self._get_memory_buffer_summary()}")
        logger.info(f"   Database limits: {self._get_db_limits_summary()}")
    
    def _initialize_database(self):
        """Initialize SQLite database for long-term storage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create tables for each timeframe
                for timeframe in ["1m", "5m", "1h", "1d"]:
                    cursor.execute(f'''
                        CREATE TABLE IF NOT EXISTS candles_{timeframe} (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            open_time INTEGER UNIQUE,
                            open REAL,
                            high REAL,
                            low REAL,
                            close REAL,
                            volume REAL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    # Create index for fast queries
                    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_candles_{timeframe}_time ON candles_{timeframe}(open_time)')
                
                conn.commit()
                logger.success("📊 Historical database initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
    
    def add_candles(self, timeframe: str, new_candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add new candles to both memory and database storage
        Returns statistics about the accumulation
        """
        if not new_candles:
            return {"added": 0, "total_memory": 0, "total_db": 0}
        
        added_count = 0
        
        try:
            with self.cache_lock:
                # Add to memory buffer first (fastest access)
                for candle in new_candles:
                    # Check if we already have this candle in memory
                    if not self._candle_exists_in_memory(timeframe, candle["open_time"]):
                        self.memory_buffers[timeframe].append(candle)
                        added_count += 1
                
                # Add to database for long-term storage
                db_added = self._add_candles_to_database(timeframe, new_candles)
                
                # Update statistics
                self.total_candles_accumulated += added_count
                self._update_data_quality_score(timeframe)
                
                # Get current counts
                memory_count = len(self.memory_buffers[timeframe])
                db_count = self._get_database_count(timeframe)
                
                if added_count > 0:
                    logger.info(f"📈 Added {added_count} new {timeframe} candles")
                    logger.info(f"   Memory: {memory_count} candles ({self._format_time_span(timeframe, memory_count)})")
                    logger.info(f"   Database: {db_count} candles ({self._format_time_span(timeframe, db_count)})")
                
                return {
                    "added": added_count,
                    "total_memory": memory_count,
                    "total_db": db_count,
                    "db_added": db_added,
                    "data_quality": self.data_quality_score
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to add candles: {e}")
            return {"added": 0, "total_memory": 0, "total_db": 0, "error": str(e)}
    
    def get_candles(self, timeframe: str, count: int = None, include_database: bool = True) -> List[Dict[str, Any]]:
        """
        Get candles with intelligent memory + database retrieval
        Returns larger datasets for better predictions
        """
        try:
            with self.cache_lock:
                # Start with memory buffer (most recent data)
                memory_candles = list(self.memory_buffers.get(timeframe, []))
                
                if not include_database or (count and len(memory_candles) >= count):
                    # Return only memory data if sufficient or database not requested
                    return memory_candles[-count:] if count else memory_candles
                
                # Need more data - fetch from database
                needed_count = (count - len(memory_candles)) if count else 1000
                db_candles = self._get_candles_from_database(timeframe, needed_count)
                
                # Combine database + memory (chronological order)
                all_candles = db_candles + memory_candles
                
                # Remove duplicates while preserving order
                seen_times = set()
                unique_candles = []
                for candle in all_candles:
                    open_time = candle["open_time"]
                    if open_time not in seen_times:
                        seen_times.add(open_time)
                        unique_candles.append(candle)
                
                # Sort by open_time and return requested count
                unique_candles.sort(key=lambda x: x["open_time"])
                return unique_candles[-count:] if count else unique_candles
                
        except Exception as e:
            logger.error(f"❌ Failed to get candles: {e}")
            return []
    
    def get_comprehensive_dataset(self, timeframe: str) -> Dict[str, Any]:
        """
        Get comprehensive dataset statistics for machine learning
        """
        try:
            memory_count = len(self.memory_buffers.get(timeframe, []))
            db_count = self._get_database_count(timeframe)
            total_count = memory_count + db_count
            
            # Calculate time span coverage
            if total_count > 0:
                time_span_hours = self._calculate_time_span_hours(timeframe, total_count)
                time_span_days = time_span_hours / 24
            else:
                time_span_hours = 0
                time_span_days = 0
            
            return {
                "timeframe": timeframe,
                "total_candles": total_count,
                "memory_candles": memory_count,
                "database_candles": db_count,
                "time_span_hours": time_span_hours,
                "time_span_days": time_span_days,
                "data_quality_score": self.data_quality_score,
                "ml_readiness": "EXCELLENT" if total_count > 1000 else "GOOD" if total_count > 500 else "BASIC",
                "prediction_capability": "ADVANCED" if time_span_days > 30 else "INTERMEDIATE" if time_span_days > 7 else "BASIC"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get dataset stats: {e}")
            return {"error": str(e)}
    
    def _add_candles_to_database(self, timeframe: str, candles: List[Dict[str, Any]]) -> int:
        """Add candles to database with duplicate prevention"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                added_count = 0
                
                for candle in candles:
                    try:
                        cursor.execute(f'''
                            INSERT OR IGNORE INTO candles_{timeframe} 
                            (open_time, open, high, low, close, volume)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            candle["open_time"],
                            candle["open"],
                            candle["high"], 
                            candle["low"],
                            candle["close"],
                            candle["volume"]
                        ))
                        
                        if cursor.rowcount > 0:
                            added_count += 1
                            
                    except Exception as e:
                        logger.debug(f"Failed to insert candle: {e}")
                
                conn.commit()
                
                # Clean up old data if over limit
                self._cleanup_old_database_data(timeframe, cursor)
                
                return added_count
                
        except Exception as e:
            logger.error(f"❌ Database insert failed: {e}")
            return 0
    
    def _get_candles_from_database(self, timeframe: str, count: int) -> List[Dict[str, Any]]:
        """Retrieve candles from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    SELECT open_time, open, high, low, close, volume
                    FROM candles_{timeframe}
                    ORDER BY open_time DESC
                    LIMIT ?
                ''', (count,))
                
                rows = cursor.fetchall()
                
                candles = []
                for row in rows:
                    candles.append({
                        "open_time": row[0],
                        "open": row[1],
                        "high": row[2],
                        "low": row[3],
                        "close": row[4],
                        "volume": row[5]
                    })
                
                # Reverse to get chronological order
                return list(reversed(candles))
                
        except Exception as e:
            logger.error(f"❌ Database query failed: {e}")
            return []
    
    def _get_database_count(self, timeframe: str) -> int:
        """Get count of candles in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'SELECT COUNT(*) FROM candles_{timeframe}')
                return cursor.fetchone()[0]
        except:
            return 0
    
    def _cleanup_old_database_data(self, timeframe: str, cursor):
        """Remove old data if over storage limit"""
        try:
            limit = self.db_storage_limits.get(timeframe, 10000)
            cursor.execute(f'''
                DELETE FROM candles_{timeframe} 
                WHERE open_time NOT IN (
                    SELECT open_time FROM candles_{timeframe}
                    ORDER BY open_time DESC
                    LIMIT ?
                )
            ''', (limit,))
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")
    
    def _candle_exists_in_memory(self, timeframe: str, open_time: int) -> bool:
        """Check if candle already exists in memory buffer"""
        buffer = self.memory_buffers.get(timeframe, [])
        return any(candle["open_time"] == open_time for candle in buffer)
    
    def _update_data_quality_score(self, timeframe: str):
        """Update data quality score based on accumulated data"""
        try:
            total_candles = sum(len(buffer) for buffer in self.memory_buffers.values())
            db_candles = sum(self._get_database_count(tf) for tf in ["1m", "5m", "1h", "1d"])
            
            # Calculate quality score (0-100)
            total_data_points = total_candles + db_candles
            if total_data_points > 10000:
                self.data_quality_score = 100.0
            elif total_data_points > 5000:
                self.data_quality_score = 90.0
            elif total_data_points > 1000:
                self.data_quality_score = 75.0
            elif total_data_points > 500:
                self.data_quality_score = 60.0
            else:
                self.data_quality_score = min(total_data_points / 500 * 60, 60.0)
                
        except Exception as e:
            logger.debug(f"Quality score update failed: {e}")
    
    def _format_time_span(self, timeframe: str, count: int) -> str:
        """Format time span for display"""
        try:
            hours = self._calculate_time_span_hours(timeframe, count)
            if hours < 24:
                return f"{hours:.1f} hours"
            else:
                days = hours / 24
                if days < 7:
                    return f"{days:.1f} days"
                else:
                    weeks = days / 7
                    return f"{weeks:.1f} weeks"
        except:
            return f"{count} candles"
    
    def _calculate_time_span_hours(self, timeframe: str, count: int) -> float:
        """Calculate time span in hours"""
        if timeframe == "1m":
            return count / 60
        elif timeframe == "5m":
            return count / 12
        elif timeframe == "1h":
            return count
        elif timeframe == "1d":
            return count * 24
        return 0
    
    def _get_memory_buffer_summary(self) -> str:
        """Get memory buffer summary"""
        summaries = []
        for tf, buffer in self.memory_buffers.items():
            summaries.append(f"{tf}: {buffer.maxlen}")
        return ", ".join(summaries)
    
    def _get_db_limits_summary(self) -> str:
        """Get database limits summary"""
        summaries = []
        for tf, limit in self.db_storage_limits.items():
            summaries.append(f"{tf}: {limit}")
        return ", ".join(summaries)
    
    def get_accumulation_stats(self) -> Dict[str, Any]:
        """Get comprehensive accumulation statistics"""
        try:
            runtime_hours = (time.time() - self.session_start_time) / 3600
            
            stats = {
                "runtime_hours": runtime_hours,
                "total_accumulated": self.total_candles_accumulated,
                "data_quality_score": self.data_quality_score,
                "timeframe_stats": {}
            }
            
            for timeframe in ["1m", "5m", "1h", "1d"]:
                stats["timeframe_stats"][timeframe] = self.get_comprehensive_dataset(timeframe)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {"error": str(e)}