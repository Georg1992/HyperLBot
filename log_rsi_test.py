#!/usr/bin/env python3
"""
RSI Real-time Accuracy Console Logger
=====================================
Run this WHILE your bot is running to log RSI accuracy data to console.

USAGE: 
1. Start bot: python main.py (Paper Trading)
2. Wait for connection
3. Run this: python3 log_rsi_test.py
4. Copy console output and send to assistant

LOGS: Real-time RSI changes and Yahoo correction accuracy
"""

import time
import sys
import os
from datetime import datetime

# Setup Python path  
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def monitor_rsi_accuracy():
    """Monitor RSI accuracy by watching bot's dashboard data"""
    
    print("=" * 80)
    print("📊 RSI REAL-TIME ACCURACY MONITOR")
    print("=" * 80)
    print(f"🕒 Started at: {datetime.now().strftime('%H:%M:%S')}")
    print("📋 Monitoring bot's real-time RSI vs Yahoo corrections")
    print("⚠️  REQUIREMENT: Your bot must be running with connected APIs")
    print("")
    
    try:
        from core.dashboard.dashboard_data_manager import simple_rtm
        from core.market_data_manager import global_rsi_calculator
        
        # Check if bot is running
        initial_data = simple_rtm.get_market_data()
        if not initial_data or not initial_data.get("current_price"):
            print("❌ ERROR: Bot is not running or no market data")
            print("💡 Start your bot first: python main.py → Paper Trading")
            return False
        
        print("✅ Bot detected - monitoring RSI accuracy")
        print(f"📊 Initial bot RSI: {initial_data.get('rsi', 'N/A')}")
        print(f"📈 Initial price: ${initial_data.get('current_price', 0):,.2f}")
        print("")
        print("📊 MONITORING LOG (Format: [Time] Price | RSI | Source)")
        print("-" * 60)
        
        start_time = time.time()
        last_rsi = initial_data.get('rsi', 0)
        last_price = initial_data.get('current_price', 0)
        update_count = 0
        yahoo_corrections = 0
        
        while time.time() - start_time < 90:  # Monitor for 90 seconds (to catch Yahoo update)
            try:
                current_data = simple_rtm.get_market_data()
                current_price = current_data.get("current_price", 0)
                current_rsi = current_data.get("rsi", 0)
                rsi_source = current_data.get("rsi_source", "unknown")
                
                # Log if price or RSI changed
                if abs(current_price - last_price) > 0.01 or abs(current_rsi - last_rsi) > 0.01:
                    elapsed = time.time() - start_time
                    price_change = current_price - last_price
                    rsi_change = current_rsi - last_rsi
                    
                    # Detect Yahoo correction vs real-time update
                    if "yahoo" in rsi_source.lower() or abs(rsi_change) > 2.0:
                        correction_marker = " 🔬 YAHOO CORRECTION"
                        yahoo_corrections += 1
                    else:
                        correction_marker = " ⚡ REAL-TIME"
                    
                    print(f"[{elapsed:5.1f}s] ${current_price:8,.2f} | RSI: {current_rsi:6.2f} | {rsi_source}{correction_marker}")
                    print(f"         Changes: Price {price_change:+6.2f} | RSI {rsi_change:+5.2f}")
                    
                    last_rsi = current_rsi
                    last_price = current_price
                    update_count += 1
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"[{elapsed:5.1f}s] ❌ Error reading bot data: {e}")
                time.sleep(2)
        
        # Summary
        print("")
        print("=" * 80)
        print("📊 MONITORING SUMMARY")
        print("=" * 80)
        print(f"⏱️ Monitoring time: {time.time() - start_time:.1f} seconds")
        print(f"📊 Total RSI updates: {update_count}")
        print(f"🔬 Yahoo corrections: {yahoo_corrections}")
        print(f"⚡ Real-time updates: {update_count - yahoo_corrections}")
        print("")
        print("📋 ANALYSIS NEEDED:")
        print("   - How many real-time RSI updates between Yahoo corrections?")
        print("   - Do real-time RSI values look smooth and realistic?")
        print("   - Are Yahoo corrections small (good accuracy) or large (poor accuracy)?")
        print("")
        print("=" * 80)
        print("📨 COPY THIS ENTIRE OUTPUT AND SEND TO ASSISTANT")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        print("💡 Make sure your bot is running and connected")
        return False

if __name__ == "__main__":
    print("🚀 Starting RSI accuracy monitor...")
    print("⏱️ Will monitor for 90 seconds to catch Yahoo updates")
    print("")
    
    if monitor_rsi_accuracy():
        print("\n✅ Monitoring completed - copy output for analysis")
    else:
        print("\n❌ Monitoring failed - check bot status")