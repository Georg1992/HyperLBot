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

# Initialize session logging
from core.logging.session_logger import get_session_logger
session_logger = get_session_logger()

# Import core module to setup paths
from config.config import config
from core.constants import constants
from core.instance_manager import instance_manager, check_single_instance

# Global variables to track active instances for graceful shutdown
active_session_orchestrator = None
dashboard_started_this_session = False

def shutdown_handler(signum, frame):
    """Handle Ctrl+C and other termination signals"""
    logger.info("🛑 Shutting down...")
    
    if active_session_orchestrator:
        try:
            # Get dashboard service for cleanup
            from core.services.system_initializer import get_system_initializer
            system_initializer = get_system_initializer()
            dashboard_service = system_initializer.singleton_systems.get("dashboard_service")
            if dashboard_service:
                dashboard_service.cleanup_heartbeat()
                logger.info("🏁 Trading session closed gracefully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    # Log session end
    session_logger.log_session_end()
    
    sys.exit(0)

def cleanup_on_exit():
    """Cleanup function called on normal exit"""
    if active_session_orchestrator:
        try:
            # Get dashboard service for cleanup
            from core.services.system_initializer import get_system_initializer
            system_initializer = get_system_initializer()
            dashboard_service = system_initializer.singleton_systems.get("dashboard_service")
            if dashboard_service:
                dashboard_service.cleanup_heartbeat()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

# Register signal handlers
signal.signal(signal.SIGINT, shutdown_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, shutdown_handler)  # Termination signal

# Register cleanup function
atexit.register(cleanup_on_exit)

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
            from core.services.system_initializer import get_system_initializer
            temp_initializer = get_system_initializer()
            temp_initializer._ensure_env_file()
            
            if start_dashboard():
                input("Press Enter to stop the dashboard...")
            else:
                logger.error("Failed to start dashboard")
        elif choice == "4":
            break
        else:
            logger.warning("Invalid menu choice entered")
            print("Invalid choice. Please enter 1-4.")

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
        from core.dashboard.web_dashboard import create_dashboard, EventDrivenTradingDashboard
        
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


def run_paper_trading():
    """Run the Hyperliquid paper trading bot for testing"""
    global active_session_orchestrator
    
    # Ensure .env file exists
    from core.services.system_initializer import get_system_initializer
    temp_initializer = get_system_initializer()
    temp_initializer._ensure_env_file()
    
    # Reload config after potential .env creation
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # Acquire instance lock
    with instance_manager:
        try:
            from core.services.system_initializer import get_system_initializer
            from core.simulated_account_manager import account_manager
            
            logger.info("Starting Paper Trading Bot...")
            
            # Simulated Account Management
            initial_balance = None
            
            if account_manager.account_exists():
                account_data = account_manager.load_account()
                if account_data:
                    summary = account_manager.get_account_summary()
                    logger.info(f"Existing Account Found: Balance=${summary['current_balance']:.2f}, Trades={summary['total_trades']}, Win Rate={summary['win_rate']:.1f}%")
                    print("\nExisting Account Found:")
                    print(f"   Balance: ${summary['current_balance']:.2f}")
                    print(f"   Trades: {summary['total_trades']}")
                    print(f"   Win Rate: {summary['win_rate']:.1f}%")
                    
                    # Check if running in background mode (no stdin available)
                    import sys
                    if not sys.stdin.isatty():
                        # Running in background mode - automatically use existing account
                        logger.info("🤖 Background mode detected - using existing account automatically")
                        initial_balance = account_data["current_balance"]
                    else:
                        # Interactive mode - ask user for choice
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
                            logger.warning("Invalid account choice entered")
                            print("Invalid choice")
                            return
                else:
                    logger.error("Failed to load existing account")
                    return
            else:
                # Check if running in background mode
                import sys
                if not sys.stdin.isatty():
                    # Running in background mode - use default balance
                    logger.info("🤖 Background mode detected - creating new account with default balance")
                    new_balance = config.DEFAULT_INITIAL_BALANCE
                else:
                    # Interactive mode - ask user for balance
                    new_balance = float(input(f"Enter initial balance (default {config.DEFAULT_INITIAL_BALANCE}): ") or str(config.DEFAULT_INITIAL_BALANCE))
                account_data = account_manager.create_account(new_balance)
                initial_balance = new_balance
            
            logger.info(f"Paper Trading Configuration: Balance=${initial_balance:.2f} (simulated)")
            print("\nConfiguration:")
            print(f"Balance: ${initial_balance:.2f} (simulated)")
            
            # Initialize system and get services (using singletons)
            system_initializer = get_system_initializer()
            init_result = system_initializer.initialize_system(initial_balance)
            if not init_result.get("success"):
                logger.error(f"Failed to initialize system: {init_result.get('error', 'Unknown error')}")
                return
            
            # Get services from system initializer (all singletons)
            market_data_service = system_initializer.singleton_systems.get("market_data_service")
            dashboard_service = system_initializer.singleton_systems.get("dashboard_service")
            session_orchestrator = system_initializer.singleton_systems.get("session_orchestrator")
            
            if not all([market_data_service, dashboard_service, session_orchestrator]):
                logger.error("Failed to get required services")
                return
            
            logger.info("Starting bot...")
            logger.info("Press Ctrl+C to stop")
            
            # Start dashboard after system is initialized
            start_dashboard()
            
            # Set active session orchestrator for shutdown handling
            global active_session_orchestrator
            active_session_orchestrator = session_orchestrator
            
            # Run paper trading session directly (no facade needed)
            try:
                session_orchestrator.run_paper_trading_session(
                    config.DEFAULT_CHECK_INTERVAL,
                    market_data_service, dashboard_service, "standard"
                )
            except KeyboardInterrupt:
                logger.info("🛑 KeyboardInterrupt received - shutting down...")
                raise
            
        except Exception as e:
            logger.error(f"Error in paper trading: {e}")
            input("Press Enter to continue...")
        finally:
            active_session_orchestrator = None

def run_real_trading():
    """Run the Hyperliquid real trading bot for production"""
    logger.error("Real trading not implemented yet")
    logger.info("Use Paper Trading mode for testing strategies safely")
    
    choice = input("\nRun Paper Trading instead? (y/n): ").strip().lower()
    if choice in ['y', 'yes']:
        run_paper_trading()

if __name__ == "__main__":
    main()
