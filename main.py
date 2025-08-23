#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HyperLBot - Main Entry Point
Hybrid trading bot combining Binance analysis with Hyperliquid execution
"""

import sys
import os
import threading
import time
import webbrowser
import subprocess
from loguru import logger

# Import core module to setup paths
import core

def check_and_install_dependencies():
    """Check and automatically install missing dependencies"""
    required_modules = [
        'flask',
        'flask_socketio',
        'yfinance',
        'requests',
        'pandas',
        'numpy',
        'loguru',
        'python-dotenv',
        'httpx',
        'aiohttp',
        'scikit-learn',
        'joblib'
    ]
    
    missing_modules = []
    
    # Check each module
    for module in required_modules:
        try:
            if module == 'flask_socketio':
                import flask_socketio
            elif module == 'python-dotenv':
                import dotenv
            elif module == 'scikit-learn':
                import sklearn
            else:
                __import__(module)
            logger.debug(f"✅ {module} - Available")
        except ImportError:
            missing_modules.append(module)
            logger.warning(f"❌ {module} - Missing")
    
    # Install missing modules
    if missing_modules:
        logger.info(f"🔧 Installing {len(missing_modules)} missing dependencies...")
        
        for module in missing_modules:
            try:
                logger.info(f"📦 Installing {module}...")
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", module, 
                    "--break-system-packages", "--quiet"
                ])
                logger.success(f"✅ {module} installed successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Failed to install {module}: {e}")
                return False
        
        logger.success("🎉 All dependencies installed successfully!")
        return True
    else:
        logger.info("✅ All dependencies are already available")
        return True

def start_dashboard():
    """Start the real-time dashboard in a background thread"""
    try:
        # Import real-time dashboard here to avoid circular imports
        from realtime_dashboard import EventDrivenTradingDashboard
        
        def run_dashboard():
            try:
                dashboard = EventDrivenTradingDashboard()
                dashboard.run(host='0.0.0.0', port=5002, debug=False)
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
        
        # Start dashboard in background thread
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()
        
        # Wait a moment for dashboard to start
        time.sleep(2)
        
        # Open browser automatically
        try:
            webbrowser.open('http://localhost:5002')
            logger.info("🌐 Real-time dashboard opened automatically in browser")
        except Exception as e:
            logger.warning(f"Could not open browser automatically: {e}")
            logger.info("💡 Please open http://localhost:5002 manually")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        return False

def main():
    """Main entry point with simplified menu"""
    logger.info("HyperLBot - Hybrid Trading Bot")
    logger.info("=" * 50)
    
    # Check and install dependencies first
    logger.info("🔍 Checking dependencies...")
    if not check_and_install_dependencies():
        logger.error("❌ Failed to install required dependencies. Please check your internet connection.")
        return
    
    while True:
        print("\nHyperLBot Menu:")
        print("1. Paper Trading (Testing Mode)")
        print("2. Real Trading (Production Mode)")
        print("3. Start Dashboard Only")
        print("4. Exit")
        print("=" * 30)
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == "1":
            run_paper_trading()
        elif choice == "2":
            run_real_trading()
        elif choice == "3":
            logger.info("Starting Dashboard Only...")
            if start_dashboard():
                logger.info("✅ Real-time dashboard started successfully!")
                logger.info("💡 Keep this terminal open to run the dashboard")
                logger.info("🌐 Real-time dashboard is available at: http://localhost:5002")
                input("Press Enter to stop the dashboard...")
            else:
                logger.error("❌ Failed to start dashboard")
        elif choice == "4":
            logger.info("Goodbye!")
            break
        else:
            logger.warning("Invalid choice. Please enter 1-4.")

def run_paper_trading():
    """Run the Hyperliquid paper trading bot for testing"""
    try:
        from strategies.hybrid_paper_trading_bot import YahooHyperliquidPaperTradingBot
        
        logger.info("Starting Paper Trading Bot (Testing Mode)...")
        logger.info("This mode uses simulated trading - no real money involved")
        
        # Get user input for key parameters
        print("\nPaper Trading Configuration:")
        initial_balance = float(input("Enter initial balance (default 120.0): ") or "120.0")
        max_trades = int(input("Enter max trades (default 10): ") or "10")
        check_interval = 5  # Fixed at 5 seconds for ultra-fast responsiveness
        
        # Auto-strategy detection enabled
        selected_strategy = "standard"  # Starting strategy, will auto-switch based on market conditions
        
        logger.info(f"Configuration: Balance=${initial_balance}, Max Trades={max_trades}, Strategy={selected_strategy}")
        
        # Start the bot with dashboard
        logger.info("Starting dashboard...")
        if start_dashboard():
            logger.info("✅ Dashboard started successfully!")
        
        # Initialize and run the bot
        bot = YahooHyperliquidPaperTradingBot(
            initial_balance=initial_balance,
            max_trades=max_trades,
            check_interval=check_interval,
            strategy=selected_strategy
        )
        
        logger.info("🚀 Starting paper trading bot...")
        bot.run()
        
    except Exception as e:
        logger.error(f"Error in paper trading: {e}")
        input("Press Enter to continue...")

def run_real_trading():
    """Run the Hyperliquid real trading bot for production"""
    try:
        from strategies.hybrid_paper_trading_bot import YahooHyperliquidPaperTradingBot
        
        logger.warning("REAL TRADING MODE - This involves real money!")
        logger.warning("Make sure you understand the risks before proceeding.")
        
        confirm = input("Type 'YES' to confirm you want to use real money: ").strip().upper()
        if confirm != "YES":
            logger.info("Real trading cancelled.")
            return
        
        # Get user input for key parameters
        print("\nReal Trading Configuration:")
        initial_balance = float(input("Enter initial balance (default 120.0): ") or "120.0")
        max_trades = int(input("Enter max trades (default 5): ") or "5")  # Lower default for real trading
        check_interval = 5
        
        selected_strategy = "standard"
        
        logger.info(f"Real Trading Configuration: Balance=${initial_balance}, Max Trades={max_trades}, Strategy={selected_strategy}")
        
        # Start the bot with dashboard
        logger.info("Starting dashboard...")
        if start_dashboard():
            logger.info("✅ Dashboard started successfully!")
        
        # Initialize and run the bot (modify for real trading when implemented)
        bot = YahooHyperliquidPaperTradingBot(
            initial_balance=initial_balance,
            max_trades=max_trades,
            check_interval=check_interval,
            strategy=selected_strategy
        )
        
        logger.info("🚀 Starting real trading bot...")
        # Note: This would be modified to use real trading when implemented
        logger.warning("Note: Currently running in paper mode - real trading implementation pending")
        bot.run()
        
    except Exception as e:
        logger.error(f"Error in real trading: {e}")
        input("Press Enter to continue...")

if __name__ == "__main__":
    main()
