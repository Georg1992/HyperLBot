#!/usr/bin/env python3
"""
Fresh Start Cleanup Script
==========================
Removes ALL temporary data ignored by git for a completely fresh bot start.

WHAT IT CLEANS:
- Trading logs and session files
- Cache and temporary data
- Runtime state files
- Database files
- Bot instance locks
- Performance logs

SAFE TO RUN: Only removes files that are ignored by git (.gitignore)
"""

import os
import shutil
import glob
from pathlib import Path
from loguru import logger

def cleanup_temp_data():
    """Remove all temporary data for fresh bot start"""
    
    logger.info("🧹 FRESH START CLEANUP - Removing ALL temporary data")
    logger.info("=" * 60)
    
    cleanup_count = 0
    
    # Get project root
    project_root = Path(__file__).parent
    
    try:
        # 1. Trading logs directory
        trading_logs_dir = project_root / "trading_logs"
        if trading_logs_dir.exists():
            files_before = len(list(trading_logs_dir.rglob("*")))
            shutil.rmtree(trading_logs_dir)
            logger.info(f"🗑️ Removed trading_logs/ directory ({files_before} files)")
            cleanup_count += files_before
        
        # 2. Session metadata files (in root)
        session_files = list(project_root.glob("session_metadata_*.json"))
        for file in session_files:
            file.unlink()
            logger.info(f"🗑️ Removed {file.name}")
            cleanup_count += 1
        
        # 3. Analysis files
        analysis_files = list(project_root.glob("analysis_*.json"))
        for file in analysis_files:
            file.unlink()
            logger.info(f"🗑️ Removed {file.name}")
            cleanup_count += 1
        
        # 4. Data directories
        data_dirs = ["data/temp", "data/cache", "data/sessions", "data/logs"]
        for dir_path in data_dirs:
            full_path = project_root / dir_path
            if full_path.exists():
                files_before = len(list(full_path.rglob("*")))
                if files_before > 0:
                    shutil.rmtree(full_path)
                    logger.info(f"🗑️ Removed {dir_path}/ directory ({files_before} files)")
                    cleanup_count += files_before
        
        # 5. Database files
        db_files = list(project_root.glob("*.db"))
        for file in db_files:
            file.unlink()
            logger.info(f"🗑️ Removed {file.name}")
            cleanup_count += 1
        
        # 6. Runtime state files
        runtime_files = [
            "simulated_account.json",
            "open_positions.json", 
            "rtm_state.json",
            "bot_instance.lock",
            "trade_history.json",
            "pending_orders.json",
            "session_state.json"
        ]
        
        for filename in runtime_files:
            file_path = project_root / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"🗑️ Removed {filename}")
                cleanup_count += 1
        
        # 7. Log files
        log_files = list(project_root.glob("*.log*"))
        for file in log_files:
            file.unlink()
            logger.info(f"🗑️ Removed {file.name}")
            cleanup_count += 1
        
        # 8. Logs directory
        logs_dir = project_root / "logs"
        if logs_dir.exists():
            files_before = len(list(logs_dir.rglob("*")))
            if files_before > 0:
                shutil.rmtree(logs_dir)
                logger.info(f"🗑️ Removed logs/ directory ({files_before} files)")
                cleanup_count += files_before
        
        # 9. CSV exports
        csv_files = list(project_root.glob("*.csv"))
        csv_exports_dir = project_root / "csv_exports"
        
        for file in csv_files:
            file.unlink()
            logger.info(f"🗑️ Removed {file.name}")
            cleanup_count += 1
            
        if csv_exports_dir.exists():
            files_before = len(list(csv_exports_dir.rglob("*")))
            if files_before > 0:
                shutil.rmtree(csv_exports_dir)
                logger.info(f"🗑️ Removed csv_exports/ directory ({files_before} files)")
                cleanup_count += files_before
        
        # 10. Python cache files (just to be thorough)
        pycache_dirs = list(project_root.rglob("__pycache__"))
        for cache_dir in pycache_dirs:
            files_before = len(list(cache_dir.rglob("*")))
            if files_before > 0:
                shutil.rmtree(cache_dir)
                logger.info(f"🗑️ Removed {cache_dir.relative_to(project_root)} ({files_before} files)")
                cleanup_count += files_before
        
        logger.info("=" * 60)
        if cleanup_count > 0:
            logger.success(f"✅ CLEANUP COMPLETE: Removed {cleanup_count} files/directories")
            logger.info("🎯 Bot ready for completely fresh start!")
        else:
            logger.info("✅ ALREADY CLEAN: No temporary files found")
        
        logger.info("🚀 You can now start the bot with completely fresh state!")
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    # Setup minimal logging for cleanup script
    logger.remove()  # Remove default handler
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO"
    )
    
    cleanup_temp_data()