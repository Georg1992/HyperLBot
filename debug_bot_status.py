#!/usr/bin/env python3
"""
Bot Status Debugger
==================
Quick diagnostic to check what's happening with the bot and RSI updates.
"""

import time
import sys
import os

# Setup Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def diagnose_bot_status():
    """Diagnose what's happening with bot and RSI updates"""
    
    print("🔍 BOT STATUS DIAGNOSTIC")
    print("=" * 50)
    
    try:
        from core.dashboard.dashboard_data_manager import simple_rtm
        from core.market_data_manager import global_rsi_calculator
        
        # Check dashboard data
        print("📊 DASHBOARD DATA:")
        data = simple_rtm.get_market_data()
        for key, value in data.items():
            print(f"   {key}: {value}")
        print("")
        
        # Check RSI calculator state
        print("🔬 RSI CALCULATOR STATE:")
        print(f"   Initialized: {global_rsi_calculator.rsi_initialized}")
        print(f"   Current RSI: {global_rsi_calculator.current_rsi}")
        print(f"   Baseline RSI: {global_rsi_calculator.baseline_rsi}")
        print(f"   Last price: {global_rsi_calculator.last_price}")
        print("")
        
        # Check for 5 seconds if data changes
        print("⏱️ CHECKING FOR UPDATES (5 seconds):")
        initial_rsi = data.get("rsi", 0)
        initial_price = data.get("current_price", 0)
        
        for i in range(5):
            time.sleep(1)
            current_data = simple_rtm.get_market_data()
            current_rsi = current_data.get("rsi", 0)
            current_price = current_data.get("current_price", 0)
            
            if current_rsi != initial_rsi or current_price != initial_price:
                print(f"   Update detected: RSI {current_rsi}, Price ${current_price:,.2f}")
            else:
                print(f"   No change: RSI {current_rsi}, Price ${current_price:,.2f}")
        
        print("")
        print("🎯 DIAGNOSIS:")
        if data.get("current_price", 0) > 0:
            print("   ✅ Dashboard has market data")
        else:
            print("   ❌ Dashboard missing market data")
            
        if global_rsi_calculator.rsi_initialized:
            print("   ✅ RSI calculator initialized")
        else:
            print("   ❌ RSI calculator not initialized")
            
        session_status = data.get("session", {}).get("status", "unknown")
        print(f"   📊 Session status: {session_status}")
        
        if session_status == "ACTIVE":
            print("   ✅ Bot session is ACTIVE")
        else:
            print("   ❌ Bot session is NOT ACTIVE - may be why no updates")
            
    except Exception as e:
        print(f"❌ Diagnostic error: {e}")

if __name__ == "__main__":
    diagnose_bot_status()