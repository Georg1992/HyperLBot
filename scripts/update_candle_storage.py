#!/usr/bin/env python3
"""
Update Candle Storage Database
Backfills missing candles from the last stored candle to current time
Can be run periodically to keep the database up to date
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
from datetime import datetime


def main():
    """Update candle storage database by backfilling missing candles"""
    try:
        logger.info("🔄 Updating candle storage database...")
        
        # Create candle storage instance
        storage = CandleStorage(symbol="BTC")
        
        # Check if database has data
        candle_count = storage.get_candle_count()
        if candle_count == 0:
            logger.error("❌ Database is empty - run 'python scripts/init_candle_storage.py' first to initialize with 5 years of data")
            sys.exit(1)
        
        # Get current database status
        first_timestamp = storage.get_first_timestamp()
        last_timestamp = storage.get_last_timestamp()
        
        if first_timestamp:
            first_date = datetime.fromtimestamp(first_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"📊 Database first candle: {first_date}")
        
        if last_timestamp:
            last_date = datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"📊 Database last candle: {last_date}")
            logger.info(f"📊 Total candles in database: {candle_count:,}")
        
        # Backfill missing candles
        logger.info("📥 Backfilling missing candles...")
        storage.backfill_missing_candles()
        
        # Get updated status
        updated_count = storage.get_candle_count()
        updated_last_timestamp = storage.get_last_timestamp()
        
        if updated_last_timestamp:
            updated_last_date = datetime.fromtimestamp(updated_last_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"✅ Database updated successfully")
            logger.info(f"📊 New total candles: {updated_count:,}")
            logger.info(f"📊 New last candle: {updated_last_date}")
            
            if updated_count > candle_count:
                new_candles = updated_count - candle_count
                logger.info(f"✅ Added {new_candles:,} new candles")
            else:
                logger.info("💡 Database was already up to date")
        else:
            logger.error("❌ Failed to get updated database status")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Update interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to update candle storage: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

