#!/usr/bin/env python3
"""
HyperLBot Dashboard Launcher
Simple script to start the dashboard
"""

import subprocess
import sys
import os
from loguru import logger

def main():
    """Launch the dashboard"""
    logger.info("🚀 Launching HyperLBot Dashboard...")
    
    try:
        # Check if Flask is installed
        import flask
        logger.info("✅ Flask is available")
    except ImportError:
        logger.error("❌ Flask not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask>=2.3.0"])
        logger.info("✅ Flask installed successfully")
    
    # Start the dashboard
    logger.info("📊 Starting dashboard at http://localhost:5001")
    logger.info("🔄 Dashboard will auto-refresh every 10 seconds")
    logger.info("💡 Keep this terminal open to run the dashboard")
    logger.info("🌐 Open your browser and go to: http://localhost:5001")
    
    # Import and run the simple dashboard
    from simple_dashboard import app
    app.run(host='0.0.0.0', port=5001, debug=False)

if __name__ == "__main__":
    main()
