#!/usr/bin/env python3
"""
RSI Console Logging Test
=======================
Logs RSI accuracy test results to console for analysis.

USAGE: python3 test_rsi_console_log.py
THEN: Copy console output and send to assistant for analysis
"""

import time
import sys
import os
from datetime import datetime

# Setup Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.external.yahoo_data_fetcher import YahooDataFetcher
from core.market_data_manager import global_rsi_calculator
from core.api.hyperliquid_api import HyperliquidAPI

def test_rsi_with_console_logging():
    """RSI accuracy test with detailed console logging"""
    
    print("=" * 80)
    print("🔬 RSI REAL-TIME ACCURACY TEST - CONSOLE LOG")
    print("=" * 80)
    print(f"🕒 Test started at: {datetime.now().strftime('%H:%M:%S')}")
    print("🎯 Goal: Test if real-time RSI stays close to Yahoo validation")
    print("")
    
    # Initialize with provided credentials
    wallet_address = "0x60c0478b4E1cf66484EA83F133b94B35C046909b"
    wallet_private_key = "0xda1675b78a6131184a48989469913c3d54ffa58d4f39fbbb51684ed12d9e531"
    
    yahoo_fetcher = YahooDataFetcher()
    hyperliquid_api = HyperliquidAPI(wallet_address, wallet_private_key)
    
    try:
        # STEP 1: Yahoo baseline
        print("📊 STEP 1: Get Yahoo RSI baseline")
        print("-" * 50)
        
        candles = yahoo_fetcher.get_klines("BTC-USD", "5m", 30)
        if not candles or len(candles) < 15:
            print("❌ ERROR: Not enough Yahoo data for RSI calculation")
            return False
        
        yahoo_rsi_1 = global_rsi_calculator.calculate_yahoo_baseline_rsi(candles)
        yahoo_price_1 = candles[-1]["close"]
        test_start_time = time.time()
        
        print(f"✅ Yahoo RSI baseline: {yahoo_rsi_1:.4f}")
        print(f"📈 Yahoo price: ${yahoo_price_1:,.2f}")
        print(f"🕒 Baseline time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        print("")
        
        # STEP 2: Real-time tracking for 60 seconds
        print("📊 STEP 2: Real-time RSI updates (60 seconds with Hyperliquid)")
        print("-" * 50)
        print("Format: [Time] Price | RSI | Price_Change% | RSI_Change")
        print("")
        
        price_updates = 0
        last_logged_rsi = yahoo_rsi_1
        
        while time.time() - test_start_time < 60:
            try:
                # Get Hyperliquid price
                market_data = hyperliquid_api.get_market_data("BTC")
                
                if market_data and "price" in market_data:
                    current_price = market_data["price"]
                    price_updates += 1
                    
                    # Update real-time RSI
                    rsi_data = global_rsi_calculator.update_realtime_rsi(current_price)
                    current_rsi = rsi_data.get("rsi", yahoo_rsi_1)
                    
                    elapsed = time.time() - test_start_time
                    price_change_pct = ((current_price - yahoo_price_1) / yahoo_price_1) * 100
                    rsi_change = current_rsi - yahoo_rsi_1
                    rsi_tick_change = current_rsi - last_logged_rsi
                    
                    print(f"[{elapsed:5.1f}s] ${current_price:8,.2f} | {current_rsi:7.4f} | {price_change_pct:+6.3f}% | {rsi_change:+6.3f} | tick:{rsi_tick_change:+.3f}")
                    
                    last_logged_rsi = current_rsi
                    time.sleep(3)  # 3-second intervals
                else:
                    elapsed = time.time() - test_start_time
                    print(f"[{elapsed:5.1f}s] ❌ No Hyperliquid price data")
                    time.sleep(1)
                    
            except Exception as e:
                elapsed = time.time() - test_start_time
                print(f"[{elapsed:5.1f}s] ❌ Hyperliquid error: {e}")
                time.sleep(2)
        
        print("")
        
        # STEP 3: Final validation
        print("📊 STEP 3: Fresh Yahoo RSI validation")
        print("-" * 50)
        
        final_rsi_data = global_rsi_calculator.get_current_rsi_data()
        final_realtime_rsi = final_rsi_data.get("rsi", 0.0)
        
        # Get fresh Yahoo data
        fresh_candles = yahoo_fetcher.get_klines("BTC-USD", "5m", 30)
        
        if fresh_candles and len(fresh_candles) >= 15:
            from core.market_data_manager import market_data_manager
            yahoo_rsi_2 = market_data_manager.calculate_rsi_from_candles(fresh_candles)
            yahoo_price_2 = fresh_candles[-1]["close"]
            
            print(f"🔬 Final real-time RSI: {final_realtime_rsi:.4f}")
            print(f"📊 Fresh Yahoo RSI: {yahoo_rsi_2:.4f}")
            print(f"📈 Fresh Yahoo price: ${yahoo_price_2:,.2f}")
            print(f"⚡ Total Hyperliquid updates: {price_updates}")
            print("")
            
            # CRITICAL VALIDATION
            accuracy_gap = abs(final_realtime_rsi - yahoo_rsi_2)
            price_difference = abs(yahoo_price_1 - yahoo_price_2)
            
            print("=" * 80)
            print("🎯 CRITICAL VALIDATION RESULTS")
            print("=" * 80)
            print(f"📊 Initial Yahoo RSI:  {yahoo_rsi_1:.4f}")
            print(f"🔬 Final real-time RSI: {final_realtime_rsi:.4f}")
            print(f"📊 Final Yahoo RSI:    {yahoo_rsi_2:.4f}")
            print(f"📉 RSI accuracy gap:    {accuracy_gap:.4f} points")
            print(f"💰 Yahoo price change:  ${price_difference:.2f}")
            print(f"⚡ Hyperliquid updates:  {price_updates}")
            print("")
            
            # Accuracy rating
            if price_updates >= 5:  # Only rate if we got real updates
                if accuracy_gap <= 0.5:
                    rating = "PERFECT"
                elif accuracy_gap <= 1.0:
                    rating = "EXCELLENT"
                elif accuracy_gap <= 2.0:
                    rating = "GOOD"
                elif accuracy_gap <= 5.0:
                    rating = "ACCEPTABLE"
                else:
                    rating = "POOR"
                
                print(f"⭐ ACCURACY RATING: {rating}")
                print(f"🎯 Scalping ready: {'YES' if accuracy_gap <= 2.0 else 'NEEDS IMPROVEMENT'}")
            else:
                print("❌ INSUFFICIENT DATA: Not enough Hyperliquid updates to validate")
                rating = "NO_DATA"
            
            print("")
            print("=" * 80)
            print("📋 COPY THIS OUTPUT AND SEND TO ASSISTANT FOR ANALYSIS")
            print("=" * 80)
            
            return True
        else:
            print("❌ ERROR: Could not get fresh Yahoo data for validation")
            return False
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting RSI accuracy test...")
    print("💡 This will take ~60 seconds to complete")
    print("")
    
    if test_rsi_with_console_logging():
        print("\n✅ Test completed - copy output above for analysis")
    else:
        print("\n❌ Test failed - check error messages")