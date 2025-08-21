#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HyperLBot - Main Entry Point
Hybrid trading bot combining Binance analysis with Hyperliquid execution
"""

import sys
import os
from loguru import logger

# Import core module to setup paths
import core

def main():
    """Main entry point with simplified menu"""
    logger.info("HyperLBot - Hybrid Trading Bot")
    logger.info("=" * 50)
    
    while True:
        print("\nHyperLBot Menu:")
        print("1. Paper Trading (Testing Mode)")
        print("2. Real Trading (Production Mode)")
        print("3. Exit")
        print("=" * 30)
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            run_paper_trading()
        elif choice == "2":
            run_real_trading()
        elif choice == "3":
            logger.info("Goodbye!")
            break
        else:
            logger.warning("Invalid choice. Please enter 1-3.")

def run_paper_trading():
    """Run the hybrid paper trading bot for testing"""
    try:
        from hybrid_paper_trading_bot import HybridPaperTradingBot
        
        logger.info("Starting Paper Trading Bot (Testing Mode)...")
        logger.info("This mode uses simulated trading - no real money involved")
        
        # Get user input for key parameters
        print("\nPaper Trading Configuration:")
        initial_balance = float(input("Enter initial balance (default 120.0): ") or "120.0")
        max_trades = int(input("Enter max trades (default 10): ") or "10")
        check_interval = 10  # Fixed at 10 seconds for optimal responsiveness
        
        # Auto-strategy detection enabled
        selected_strategy = "standard"  # Starting strategy, will auto-switch based on market conditions
        
        print(f"\n✅ Configuration Set:")
        print(f"  💰 Initial Balance: ${initial_balance:.2f}")
        print(f"  📊 Max Trades: {max_trades} (safety limit)")
        print(f"  ⏱️  Check Interval: {check_interval} seconds (fixed - optimal speed)")
        print(f"  🎯 Strategy: Auto-Detection (Standard → Low/High Volatility)")
        print(f"  🐋 Whale Analytics: Enabled (BlockCypher integration)")
        print(f"  🔒 Mode: Paper Trading (no real money)")
        
        # Initialize and run the bot with selected strategy
        bot = HybridPaperTradingBot(initial_balance=initial_balance, strategy_name=selected_strategy)
        
        if bot.connect():
            logger.info(f"Connected successfully! Starting paper trading...")
            logger.info(f"   Initial Balance: ${initial_balance:.2f}")
            logger.info(f"   Max Trades: {max_trades}")
            logger.info(f"   Check Interval: {check_interval} seconds")
            
            bot.run_hybrid_paper_trading(max_trades=max_trades, check_interval=check_interval)
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
