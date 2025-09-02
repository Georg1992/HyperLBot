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
import core
from config.config import config
from core.constants import constants
from core.instance_manager import instance_manager, check_single_instance

# Global variables to track active instances for graceful shutdown
active_bot_instance = None
dashboard_started_this_session = False

def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals"""
    logger.warning(f"🛑 Received signal {signum} - Initiating graceful shutdown...")
    
    if active_bot_instance:
        try:
            logger.info("🔄 Closing active trading session...")
            active_bot_instance.close_session()
            logger.success("✅ Trading session closed gracefully")
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
    
    # Session cleanup handled by SimpleRTM
    logger.info("🔄 Session cleanup completed")
    
    logger.info("👋 Goodbye!")
    sys.exit(0)

def cleanup_on_exit():
    """Cleanup function called on normal exit"""
    if active_bot_instance:
        try:
            active_bot_instance.close_session()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

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
    global dashboard_started_this_session
    
    try:
        from web_dashboard import create_dashboard, EventDrivenTradingDashboard
        
        # DEBUG: Show current flag state
        logger.info(f"🐛 DEBUG: dashboard_started_this_session = {dashboard_started_this_session}")
        
        # Check if dashboard is already running (thorough check)
        logger.info("🔍 Checking for existing dashboard...")
        if EventDrivenTradingDashboard.is_dashboard_running(
            host=constants.DEFAULT_DASHBOARD_HOST, 
            port=constants.DEFAULT_DASHBOARD_PORT
        ):
            logger.success("✅ Existing dashboard detected - connecting to it!")
            logger.info(f"🌐 Dashboard URL: http://{constants.DEFAULT_DASHBOARD_HOST}:{constants.DEFAULT_DASHBOARD_PORT}")
            logger.info("🔗 Bot will use existing dashboard (no new instance created)")
            logger.info("🚫 No browser opening (preventing conflicts)")
            
            # DON'T set flag here - this is connecting to existing, not starting new
            logger.info("🐛 DEBUG: Found existing dashboard, returning without setting flag")
            return True
        
        logger.info("🐛 DEBUG: No existing dashboard found")
        
        # Check if we already started dashboard this session (prevents duplicate NEW dashboards)
        if dashboard_started_this_session:
            logger.info("✅ Dashboard already started this session - reusing")
            logger.info("🐛 DEBUG: Flag was True, reusing existing")
            return True
        
        logger.info("🐛 DEBUG: Flag is False, proceeding to start new dashboard")
        
        logger.info("🚀 Starting new dashboard instance...")
        
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
        
        # Wait for dashboard to become available
        logger.info("⏳ Waiting for new dashboard to start...")
        if EventDrivenTradingDashboard.wait_for_dashboard(
            host=constants.DEFAULT_DASHBOARD_HOST, 
            port=constants.DEFAULT_DASHBOARD_PORT, 
            timeout=10
        ):
            logger.success("✅ New dashboard started successfully!")
            logger.info(f"🌐 Dashboard URL: http://{constants.DEFAULT_DASHBOARD_HOST}:{constants.DEFAULT_DASHBOARD_PORT}")
            logger.info("💡 Please open the URL in your browser to view the dashboard")
            logger.info("🚫 Auto-browser disabled (preventing conflicts with existing browser instances)")
            
            dashboard_started_this_session = True  # Mark as started this session
            logger.info("🐛 DEBUG: Set flag to True after successful dashboard start")
        else:
            logger.warning("⚠️ Dashboard may not have started properly")
            logger.info(f"💡 Please check if dashboard is available at: http://{constants.DEFAULT_DASHBOARD_HOST}:{constants.DEFAULT_DASHBOARD_PORT}")
            logger.info("🐛 DEBUG: Dashboard failed to start, flag remains False")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        return False

def main():
    """Main entry point with simplified menu"""
    global dashboard_started_this_session
    
    # Reset dashboard flag on fresh start (prevents persistence from previous runs)
    dashboard_started_this_session = False
    logger.info("🐛 DEBUG: Reset dashboard_started_this_session to False on main() start")
    
    logger.info("HyperLBot - Hybrid Trading Bot")
    logger.info("=" * 50)
    
    # Check for existing instance first
    if not check_single_instance():
        return
    
    # Validate configuration
    config_errors = config.validate_config()
    if config_errors:
        logger.warning("Configuration warnings:")
        for error in config_errors:
            logger.warning(f"  - {error}")
    
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
            # Ensure .env file exists before starting dashboard
            logger.info("🔧 Validating configuration...")
            from core.services.system_initializer import SystemInitializer
            temp_initializer = SystemInitializer(config)
            temp_initializer._ensure_env_file()  # Interactive .env setup if missing
            
            logger.info("Starting Dashboard Only...")
            if start_dashboard():
                logger.info("✅ Real-time dashboard started successfully!")
                logger.info("💡 Keep this terminal open to run the dashboard")
                logger.info(f"🌐 Real-time dashboard is available at: http://localhost:{constants.DEFAULT_DASHBOARD_PORT}")
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
    global active_bot_instance
    
    # FIRST: Ensure .env file exists and validate credentials BEFORE any initialization
    logger.info("🔧 Validating configuration...")
    from core.services.system_initializer import SystemInitializer
    temp_initializer = SystemInitializer(config)
    temp_initializer._ensure_env_file()  # Interactive .env setup if missing
    
    # Reload config after potential .env creation
    from dotenv import load_dotenv
    load_dotenv(override=True)  # Reload environment variables
    
    logger.info("✅ Configuration validated - proceeding with bot initialization")
    
    # Acquire instance lock
    with instance_manager:
        try:
            from core.bot.trading_orchestrator import YahooHyperliquidPaperTradingBot
            from core.simulated_account_manager import account_manager
            
            logger.info("Starting Paper Trading Bot (Testing Mode)...")
            logger.info("This mode uses simulated trading - no real money involved")
            
            # Simulated Account Management
            print(f"\n[GAME] Simulated Account Management:")
            
            initial_balance = None
            
            # Check if account exists
            if account_manager.account_exists():
                # Load existing account
                account_data = account_manager.load_account()
                if account_data:
                    summary = account_manager.get_account_summary()
                    print(f"[CHART] Existing Account Found:")
                    print(f"   Account ID: {summary['account_id']}")
                    print(f"   Current Balance: ${summary['current_balance']:.2f}")
                    print(f"   Total Trades: {summary['total_trades']}")
                    print(f"   Win Rate: {summary['win_rate']:.1f}%")
                    print(f"   Open Positions: {summary['open_positions_count']}")
                    print(f"   Created: {summary['created_at'][:10]}")
                    
                    # Ask user what to do
                    while True:
                        choice = input("\nChoose action:\n1. Continue with existing account\n2. Create new account (reset)\nEnter choice (1-2): ").strip()
                        
                        if choice == "1":
                            initial_balance = account_data["current_balance"]
                            logger.info(f"[GAME] Continuing with existing account: ${initial_balance:.2f}")
                            break
                        elif choice == "2":
                            if account_manager.reset_account():
                                # Create new account
                                new_balance = float(input(f"Enter initial balance for new account (default {config.DEFAULT_INITIAL_BALANCE}): ") or str(config.DEFAULT_INITIAL_BALANCE))
                                account_data = account_manager.create_account(new_balance)
                                initial_balance = new_balance
                                logger.info(f"[GAME] Created new account: ${initial_balance:.2f}")
                                break
                            else:
                                logger.error("❌ Failed to reset account")
                                return
                        else:
                            print("Invalid choice. Please enter 1 or 2.")
                else:
                    logger.error("❌ Failed to load existing account")
                    return
            else:
                # Create new account
                print("📝 No existing account found. Creating new simulated account...")
                new_balance = float(input(f"Enter initial balance (default {config.DEFAULT_INITIAL_BALANCE}): ") or str(config.DEFAULT_INITIAL_BALANCE))
                account_data = account_manager.create_account(new_balance)
                initial_balance = new_balance
                logger.info(f"[GAME] Created new account: ${initial_balance:.2f}")
            
            # Get user input for trading parameters
            print(f"\nPaper Trading Configuration:")
            print(f"💰 Balance: ${initial_balance:.2f} (simulated)")
            max_trades = int(input(f"Enter max trades (default {config.DEFAULT_MAX_TRADES}): ") or str(config.DEFAULT_MAX_TRADES))
            check_interval = config.DEFAULT_CHECK_INTERVAL  # Fixed for responsiveness
            
            # Use default strategy
            selected_strategy = config.DEFAULT_STRATEGY
            
            # Update instance lock with strategy info
            instance_manager.update_lock_info(selected_strategy, initial_balance)
            
            logger.info(f"Configuration: Balance=${initial_balance:.2f}, Max Trades={max_trades}, Strategy={selected_strategy}")
            
            # Start the bot with dashboard
            logger.info("Starting dashboard...")
            if start_dashboard():
                logger.info("✅ Dashboard started successfully!")
            
            # Initialize and run the bot
            bot = YahooHyperliquidPaperTradingBot(
                initial_balance=initial_balance,
                strategy_name=selected_strategy,
                balance_mode="simulated"
            )
            
            # Set global bot instance for graceful shutdown
            active_bot_instance = bot
            
            logger.info("🚀 Starting paper trading bot...")
            logger.info("💡 Press Ctrl+C to stop the bot gracefully")
            
            # Connect to Hyperliquid for market data only
            logger.info("🔗 Connecting to Hyperliquid API for market data...")
            if not bot.connect():
                logger.error("❌ Failed to connect to Hyperliquid API")
                return
            logger.success("✅ Connected to Hyperliquid API (market data only)")
            
            bot.run_yahoo_hyperliquid_paper_trading(
                max_trades=max_trades,
                check_interval=check_interval
            )
            
        except Exception as e:
            logger.error(f"Error in paper trading: {e}")
            input("Press Enter to continue...")
        finally:
            # Clear global bot instance
            active_bot_instance = None

def run_real_trading():
    """Run the Hyperliquid real trading bot for production"""
    logger.error("❌ REAL TRADING NOT IMPLEMENTED YET")
    logger.warning("This feature is currently under development.")
    logger.info("💡 Use Paper Trading mode (option 1) for testing strategies safely.")
    logger.info("📧 Contact the developer for real trading implementation timeline.")
    
    # Offer to run paper trading instead
    while True:
        choice = input("\nWould you like to run Paper Trading instead? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            logger.info("🔄 Redirecting to Paper Trading mode...")
            run_paper_trading()
            break
        elif choice in ['n', 'no']:
            logger.info("Returning to main menu.")
            break
        else:
            logger.warning("Please enter 'y' or 'n'")

if __name__ == "__main__":
    main()
