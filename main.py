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
from loguru import logger

# Import core module to setup paths
import core

def start_dashboard():
    """Start the dashboard in a background thread"""
    try:
        # Import dashboard here to avoid circular imports
        from simple_dashboard import app
        
        def run_dashboard():
            try:
                app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
        
        # Start dashboard in background thread
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()
        
        # Wait a moment for dashboard to start
        time.sleep(2)
        
        # Open browser automatically
        try:
            webbrowser.open('http://localhost:5001')
            logger.info("🌐 Dashboard opened automatically in browser")
        except Exception as e:
            logger.warning(f"Could not open browser automatically: {e}")
            logger.info("💡 Please open http://localhost:5001 manually")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        return False

def main():
    """Main entry point with simplified menu"""
    logger.info("HyperLBot - Hybrid Trading Bot")
    logger.info("=" * 50)
    
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
                logger.info("✅ Dashboard started successfully!")
                logger.info("💡 Keep this terminal open to run the dashboard")
                logger.info("🌐 Dashboard is available at: http://localhost:5001")
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
        
        print(f"\n✅ Configuration Set:")
        print(f"  💰 Initial Balance: ${initial_balance:.2f}")
        print(f"  📊 Max Trades: {max_trades} (safety limit)")
        print(f"  ⏱️  Check Interval: {check_interval} seconds (ULTRA-FAST REACTION MODE)")
        print(f"  🎯 Strategy: Auto-Detection (Standard → Low/High Volatility)")
        print(f"  🐋 Whale Analytics: Enabled (BlockCypher integration)")
        print(f"  🔒 Mode: Paper Trading (no real money)")
        
        # Initialize and run the bot with selected strategy
        bot = YahooHyperliquidPaperTradingBot(initial_balance=initial_balance, strategy_name=selected_strategy)
        
        if bot.connect():
            logger.info(f"Connected successfully! Starting paper trading...")
            logger.info(f"   Initial Balance: ${initial_balance:.2f}")
            logger.info(f"   Max Trades: {max_trades}")
            logger.info(f"   Check Interval: {check_interval} seconds")
            
            # Start dashboard automatically
            logger.info("🚀 Starting dashboard automatically...")
            if start_dashboard():
                logger.info("✅ Dashboard started successfully")
            else:
                logger.warning("⚠️ Dashboard failed to start, but bot will continue")
            
            # Run the bot
            bot.run_yahoo_hyperliquid_paper_trading(max_trades=max_trades, check_interval=check_interval)
        else:
            logger.error("Failed to connect to APIs")
            
    except Exception as e:
        logger.error(f"Error running paper trading: {e}")
        import traceback
        logger.error(f"Full error: {traceback.format_exc()}")

def run_real_trading():
    """Run the real trading bot for production"""
    try:
        logger.info("REAL TRADING MODE - This will use real money!")
        logger.info("Make sure you have tested thoroughly with paper trading first!")
        
        # Double confirmation for safety
        confirm1 = input("Are you sure you want to proceed with REAL trading? (yes/no): ").strip().lower()
        if confirm1 != "yes":
            logger.info("Real trading cancelled by user")
            return
            
        confirm2 = input("Type 'CONFIRM' to proceed with real money trading: ").strip()
        if confirm2 != "CONFIRM":
            logger.info("Real trading cancelled - confirmation not received")
            return
        
        logger.info("REAL TRADING MODE ACTIVATED!")
        logger.info("This will place actual trades with real money!")
        
        # Start dashboard automatically for real trading too
        logger.info("🚀 Starting dashboard automatically...")
        if start_dashboard():
            logger.info("✅ Dashboard started successfully")
        else:
            logger.warning("⚠️ Dashboard failed to start, but bot will continue")
        
        # TODO: Implement real trading bot
        # For now, this is a placeholder
        logger.warning("Real trading mode is not yet implemented")
        logger.info("Please use paper trading mode for now")
        logger.info("Real trading will be implemented after paper trading verification")
        
        # Placeholder for future real trading implementation
        # from strategies.hybrid_real_trading_bot import HybridRealTradingBot
        # bot = HybridRealTradingBot()
        # bot.run_real_trading()
            
    except Exception as e:
        logger.error(f"Error in real trading mode: {e}")

if __name__ == "__main__":
    main()
