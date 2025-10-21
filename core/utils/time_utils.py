#!/usr/bin/env python3
"""
Time Utilities Module
Centralized time calculations and utilities
Single Responsibility: Time-related calculations
"""

import time
import datetime as dt
from typing import Dict, Any
from loguru import logger


class TimeUtils:
    """Centralized time utilities and calculations"""
    
    @staticmethod
    def get_5m_candle_start_time(current_time: float = None) -> float:
        """
        Get the 5-minute candle start time (UTC synchronized)
        
        Args:
            current_time: Optional timestamp, uses current time if None
            
        Returns:
            Timestamp of current 5m candle start
        """
        if current_time is None:
            current_time = time.time()
            
        utc_dt = dt.datetime.fromtimestamp(current_time, tz=dt.timezone.utc)
        utc_minute = utc_dt.minute
        candle_start_minute = (utc_minute // 5) * 5
        candle_start_dt = utc_dt.replace(minute=candle_start_minute, second=0, microsecond=0)
        return candle_start_dt.timestamp()
    
    @staticmethod
    def get_1h_candle_start_time(current_time: float = None) -> float:
        """
        Get the 1-hour candle start time (UTC synchronized)
        
        Args:
            current_time: Optional timestamp, uses current time if None
            
        Returns:
            Timestamp of current 1h candle start
        """
        if current_time is None:
            current_time = time.time()
            
        utc_dt = dt.datetime.fromtimestamp(current_time, tz=dt.timezone.utc)
        candle_start_dt = utc_dt.replace(minute=0, second=0, microsecond=0)
        return candle_start_dt.timestamp()
    
    @staticmethod
    def get_1d_candle_start_time(current_time: float = None) -> float:
        """
        Get the 1-day candle start time (UTC synchronized)
        
        Args:
            current_time: Optional timestamp, uses current time if None
            
        Returns:
            Timestamp of current 1d candle start
        """
        if current_time is None:
            current_time = time.time()
            
        utc_dt = dt.datetime.fromtimestamp(current_time, tz=dt.timezone.utc)
        candle_start_dt = utc_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return candle_start_dt.timestamp()
    
    @staticmethod
    def create_time_snapshot(session_start_time: float = None) -> Dict[str, Any]:
        """
        Create comprehensive time snapshot for unified data
        
        Args:
            session_start_time: Optional session start time for duration calculation
            
        Returns:
            Dict with time snapshot data
        """
        current_time = time.time()
        
        time_snapshot = {
            "unix_timestamp": current_time,
            "iso_timestamp": dt.datetime.fromtimestamp(current_time).isoformat(),
            "human_readable": dt.datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
        
        # Add session duration if session start time provided
        if session_start_time is not None:
            time_snapshot["trading_session_time"] = current_time - session_start_time
        else:
            time_snapshot["trading_session_time"] = 0.0
            
        return time_snapshot
    
    @staticmethod
    def detect_candle_boundary_changes(last_boundaries: Dict[str, Any], 
                                     current_time: float = None) -> Dict[str, bool]:
        """
        Detect if any candle boundaries have changed
        
        Args:
            last_boundaries: Dict with last known boundary values
            current_time: Optional current time, uses time.time() if None
            
        Returns:
            Dict with boundary change flags
        """
        if current_time is None:
            current_time = time.time()
            
        current_dt = dt.datetime.fromtimestamp(current_time, tz=dt.timezone.utc)
        
        # Calculate current boundaries
        current_5m_boundary = (current_dt.minute // 5) * 5
        current_hour = current_dt.hour
        current_day = current_dt.day
        
        # Check for changes
        changes = {
            "boundary_changed_5m": False,
            "boundary_changed_1h": False,
            "boundary_changed_1d": False
        }
        
        # 5-minute boundary
        if "last_5m_boundary" in last_boundaries:
            if last_boundaries["last_5m_boundary"] != current_5m_boundary:
                changes["boundary_changed_5m"] = True
                logger.info(f"🕐 5-minute boundary reached: {last_boundaries['last_5m_boundary']:02d}:00 -> {current_5m_boundary:02d}:00 UTC")
        
        # Hourly boundary (at :00 of each hour)
        if "last_hour" in last_boundaries:
            if last_boundaries["last_hour"] != current_hour and current_dt.minute == 0:
                changes["boundary_changed_1h"] = True
                logger.info(f"🕐 Hourly boundary reached: {last_boundaries['last_hour']:02d}:00 -> {current_hour:02d}:00 UTC")
        
        # Daily boundary (at 00:00 UTC)
        if "last_day" in last_boundaries:
            if last_boundaries["last_day"] != current_day and current_hour == 0 and current_dt.minute == 0:
                changes["boundary_changed_1d"] = True
                logger.info(f"🕐 Daily boundary reached - New daily candle!")
        
        # Update boundaries for next check
        last_boundaries.update({
            "last_5m_boundary": current_5m_boundary,
            "last_hour": current_hour,
            "last_day": current_day
        })
        
        return changes


# Global instance for convenience
time_utils = TimeUtils()

# Convenience functions for backward compatibility
def get_5m_candle_start_time(current_time: float = None) -> float:
    """Convenience function for 5m candle start time"""
    return TimeUtils.get_5m_candle_start_time(current_time)

def create_time_snapshot(session_start_time: float = None) -> Dict[str, Any]:
    """Convenience function for time snapshot creation"""
    return TimeUtils.create_time_snapshot(session_start_time)
