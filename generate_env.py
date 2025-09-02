#!/usr/bin/env python3
"""
Environment File Generator
=========================
Creates a complete .env file from env_example.txt template if .env doesn't exist.

USAGE: python generate_env.py
SAFE: Only creates .env if it doesn't already exist
"""

import os
import shutil
from pathlib import Path
from loguru import logger

def generate_env_file():
    """Generate .env file from template if it doesn't exist"""
    
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    env_example = project_root / "env_example.txt"
    
    # Check if .env already exists
    if env_file.exists():
        logger.info("✅ .env file already exists - no action needed")
        logger.info(f"📍 Location: {env_file}")
        return
    
    # Check if template exists
    if not env_example.exists():
        logger.error("❌ env_example.txt template not found!")
        logger.error("📍 Cannot generate .env without template")
        return
    
    try:
        # Copy template to .env
        shutil.copy2(env_example, env_file)
        
        logger.success("✅ .env file created from template!")
        logger.info(f"📍 Generated: {env_file}")
        logger.info(f"📋 Template: {env_example}")
        
        logger.warning("⚠️ IMPORTANT: Configure your settings in .env:")
        logger.warning("   🔐 Add wallet credentials (for production)")
        logger.warning("   ⚙️ Adjust trading parameters as needed")
        logger.warning("   🎯 Set TRADING_MODE (paper/production)")
        
    except Exception as e:
        logger.error(f"❌ Error generating .env file: {e}")

if __name__ == "__main__":
    # Setup minimal logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO"
    )
    
    generate_env_file()