#!/usr/bin/env python3
"""
Log Cleanup Script for HyperLBot
Cleans up old trading sessions, keeping only the last 3 sessions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.trading_logger import TradingLogger
from loguru import logger

def cleanup_logs(keep_sessions: int = 3):
    """Clean up old trading logs"""
    try:
        logger.info("🧹 Starting manual log cleanup...")
        
        # Create a temporary logger instance to access cleanup method
        temp_logger = TradingLogger("trading_logs")
        
        # Run cleanup
        temp_logger.cleanup_old_sessions(keep_sessions=keep_sessions)
        
        logger.info("✅ Manual log cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during manual log cleanup: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up old trading logs")
    parser.add_argument("--keep", type=int, default=3, help="Number of recent sessions to keep (default: 3)")
    
    args = parser.parse_args()
    
    logger.info(f"🧹 HyperLBot Log Cleanup Tool")
    logger.info(f"📁 Will keep the last {args.keep} sessions")
    
    success = cleanup_logs(keep_sessions=args.keep)
    
    if success:
        logger.info("🎉 Cleanup completed successfully!")
    else:
        logger.error("💥 Cleanup failed!")
        sys.exit(1)
