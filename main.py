#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HyperLBot - Main Entry Point
Hybrid trading bot combining market analysis with Hyperliquid execution
"""

import sys
import os

# Setup Python path first - before any other imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir

# Add project root to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import threading
import time
import webbrowser
import subprocess
import signal
import atexit
from loguru import logger

# Import core module to setup paths
from config.config import config
from core.constants import constants
from core.instance_manager import instance_manager, check_single_instance

# Global variables to track active instances for graceful shutdown
active_bot_instance = None
dashboard_started_this_session = False

def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals"""
    logger.info("🛑 Shutting down...")
    
    if active_bot_instance:
        try:
            active_bot_instance.close_session()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    sys.exit(0)

def cleanup_on_exit():
    """Cleanup function called on normal exit"""
    if active_bot_instance:
        try:
            active_bot_instance.close_session()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

# Register cleanup function
atexit.register(cleanup_on_exit)

def check_and_install_dependencies():
    """Check and automatically install missing dependencies"""
    required_modules = [
        'flask', 'flask_socketio', 'yfinance', 'requests', 'pandas', 
        'numpy', 'loguru', 'python-dotenv', 'httpx', 'aiohttp'
    ]
    
    missing_modules = []
    
    # Check each module
    for module in required_modules:
        try:
            if module == 'flask_socketio':
                import flask_socketio
            elif module == 'python-dotenv':
                import dotenv
            else:
                __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    # Install missing modules
    if missing_modules:
        logger.info(f"Installing {len(missing_modules)} missing dependencies...")
        
        for module in missing_modules:
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", module, 
                    "--break-system-packages", "--quiet"
                ])
            except subprocess.CalledProcessError:
                logger.error(f"Failed to install {module}")
                return False
        
        logger.info("Dependencies installed successfully!")
        return True
    
    return True

def start_dashboard():
    """Start the real-time dashboard in a background thread"""
    global dashboard_started_this_session
    
    try:
        from web_dashboard import create_dashboard, EventDrivenTradingDashboard
        
        # Check if dashboard is already running
        if EventDrivenTradingDashboard.is_dashboard_running(
            host=constants.DEFAULT_DASHBOARD_HOST, 
            port=constants.DEFAULT_DASHBOARD_PORT
        ):
            logger.info("Dashboard already running - connecting to it")
            return True
        
        if dashboard_started_this_session:
            return True
        
        logger.info("Starting dashboard...")
        
        def run_dashboard():
            try:
                dashboard = create_dashboard()
                dashboard.run(
                    host=constants.DEFAULT_DASHBOARD_HOST, 
                    port=constants.DEFAULT_DASHBOARD_PORT, 
                    debug=False
                )
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
        
        # Start dashboard in background thread
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()
        
        # Wait for dashboard to start
        time.sleep(1)
        
        if EventDrivenTradingDashboard.wait_for_dashboard(
            host=constants.DEFAULT_DASHBOARD_HOST, 
            port=constants.DEFAULT_DASHBOARD_PORT, 
            timeout=10
        ):
            logger.info("Dashboard started successfully!")
            try:
                webbrowser.open(f'http://{constants.DEFAULT_DASHBOARD_HOST}:{constants.DEFAULT_DASHBOARD_PORT}')
            except Exception as e:
                logger.warning(f"Could not open browser: {e}")
            dashboard_started_this_session = True
        else:
            logger.warning("Dashboard may not have started properly")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        return False

def main():
    """Main entry point with simplified menu"""
    global dashboard_started_this_session
    
    dashboard_started_this_session = False
    
    logger.info("HyperLBot - Trading Bot")
    
    # Check for existing instance first
    if not check_single_instance():
        return
    
    # Check and install dependencies
    if not check_and_install_dependencies():
        logger.error("Failed to install required dependencies")
        return
    
    while True:
        print("\nHyperLBot Menu:")
        print("1. Paper Trading (Testing Mode)")
        print("2. Real Trading (Production Mode)")
        print("3. Start Dashboard Only")
        print("4. Exit")
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == "1":
            run_paper_trading()
        elif choice == "2":
            run_real_trading()
        elif choice == "3":
            from core.services.system_initializer import SystemInitializer
            temp_initializer = SystemInitializer(config)
            temp_initializer._ensure_env_file()
            
            if start_dashboard():
                logger.info("Dashboard started successfully!")
                input("Press Enter to stop the dashboard...")
            else:
                logger.error("Failed to start dashboard")
        elif choice == "4":
            break
        else:
            print("Invalid choice. Please enter 1-4.")

def run_paper_trading():
    """Run the Hyperliquid paper trading bot for testing"""
    global active_bot_instance
    
    # Ensure .env file exists
    from core.services.system_initializer import SystemInitializer
    temp_initializer = SystemInitializer(config)
    temp_initializer._ensure_env_file()
    
    # Reload config after potential .env creation
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # Acquire instance lock
    with instance_manager:
        try:
            from core.bot.trading_orchestrator import YahooHyperliquidPaperTradingBot
            from core.simulated_account_manager import account_manager
            
            logger.info("Starting Paper Trading Bot...")
            
            # Simulated Account Management
            initial_balance = None
            
            if account_manager.account_exists():
                account_data = account_manager.load_account()
                if account_data:
                    summary = account_manager.get_account_summary()
                    print(f"\nExisting Account Found:")
                    print(f"   Balance: ${summary['current_balance']:.2f}")
                    print(f"   Trades: {summary['total_trades']}")
                    print(f"   Win Rate: {summary['win_rate']:.1f}%")
                    
                    choice = input("\n1. Continue with existing account\n2. Create new account\nChoice (1-2): ").strip()
                    
                    if choice == "1":
                        initial_balance = account_data["current_balance"]
                    elif choice == "2":
                        if account_manager.reset_account():
                            new_balance = float(input(f"Enter initial balance (default {config.DEFAULT_INITIAL_BALANCE}): ") or str(config.DEFAULT_INITIAL_BALANCE))
                            account_data = account_manager.create_account(new_balance)
                            initial_balance = new_balance
                        else:
                            logger.error("Failed to reset account")
                            return
                    else:
                        print("Invalid choice")
                        return
                else:
                    logger.error("Failed to load existing account")
                    return
            else:
                new_balance = float(input(f"Enter initial balance (default {config.DEFAULT_INITIAL_BALANCE}): ") or str(config.DEFAULT_INITIAL_BALANCE))
                account_data = account_manager.create_account(new_balance)
                initial_balance = new_balance
            
            print(f"\nConfiguration:")
            print(f"💰 Balance: ${initial_balance:.2f} (simulated)")
            
            # Start dashboard
            if start_dashboard():
                logger.info("Dashboard started successfully!")
            
            # Initialize and run the bot
            bot = YahooHyperliquidPaperTradingBot(
                initial_balance=initial_balance,
                strategy_name=config.DEFAULT_STRATEGY,
                balance_mode="simulated"
            )
            
            active_bot_instance = bot
            
            logger.info("Starting bot...")
            logger.info("Press Ctrl+C to stop")
            
            # Connect to Hyperliquid
            if not bot.connect():
                logger.error("Failed to connect to Hyperliquid API")
                return
            
            bot.run_yahoo_hyperliquid_paper_trading(
                check_interval=config.DEFAULT_CHECK_INTERVAL
            )
            
        except Exception as e:
            logger.error(f"Error in paper trading: {e}")
            input("Press Enter to continue...")
        finally:
            active_bot_instance = None

def run_real_trading():
    """Run the Hyperliquid real trading bot for production"""
    logger.error("Real trading not implemented yet")
    logger.info("Use Paper Trading mode for testing strategies safely")
    
    choice = input("\nRun Paper Trading instead? (y/n): ").strip().lower()
    if choice in ['y', 'yes']:
        run_paper_trading()

if __name__ == "__main__":
    main()
