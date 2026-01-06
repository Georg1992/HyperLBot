#!/usr/bin/env python3
"""
Initialize Candle Storage Database
Downloads 5 years of historical 5m candles into SQLite database
Can be run separately from bot runs
"""

import sys
import os

# Setup Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger
from core.services.candle_storage import CandleStorage


def main():
    """Initialize candle storage database with 5 years of historical data"""
    try:
        logger.info("📥 Initializing candle storage database with 5 years of historical data...")
        
        # Create candle storage instance
        storage = CandleStorage(symbol="BTC")
        
        # Check if database already has data
        candle_count = storage.get_candle_count()
        if candle_count > 0:
            logger.info(f"✅ Database already initialized with {candle_count} candles")
            logger.info("💡 To reinitialize, delete the database file first: data/candles_5m_btc.db")
            return
        
        # Initialize with 5 years of historical data
        storage.initialize_with_historical_data(years=5.0)
        
        # Verify initialization
        final_count = storage.get_candle_count()
        if final_count > 0:
            logger.info(f"✅ Successfully initialized database with {final_count} candles")
        else:
            logger.error("❌ Database initialization completed but no candles found")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Initialization interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to initialize candle storage: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

