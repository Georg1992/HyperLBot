#!/usr/bin/env python3
"""
Test script to verify dashboard connection to real-time data manager
"""

import json
import time
from datetime import datetime
from core.realtime_data_manager import trading_data_manager

def test_dashboard_connection():
    """Test if dashboard can read real-time data"""
    print("🔍 Testing Dashboard Connection to Real-Time Data Manager")
    print("=" * 60)
    
    try:
        # Get current state from real-time manager
        current_state = trading_data_manager.get_current_state()
        
        print("✅ Real-time data manager connection: SUCCESS")
        print(f"📊 Session Status: {current_state['session']['status']}")
        print(f"💰 Current Balance: ${current_state['session']['current_balance']:.2f}")
        print(f"📈 Total Trades: {current_state['session']['total_trades']}")
        print(f"🎯 Winning Trades: {current_state['session']['winning_trades']}")
        print(f"❌ Losing Trades: {current_state['session']['losing_trades']}")
        
        # Check recent trades
        recent_trades = list(current_state.get('recent_trades', []))
        print(f"📋 Recent Trades in Memory: {len(recent_trades)}")
        
        if recent_trades:
            latest_trade = recent_trades[-1]
            print(f"🔄 Latest Trade: {latest_trade.get('side', 'UNKNOWN')} at ${latest_trade.get('entry_price', 0):,.2f}")
            print(f"💵 P&L: ${latest_trade.get('pnl', 0):.2f}")
        
        # Check recent activity
        recent_activity = list(current_state.get('recent_activity', []))
        print(f"📝 Recent Activity Logs: {len(recent_activity)}")
        
        if recent_activity:
            latest_activity = recent_activity[-1]
            print(f"📝 Latest Activity: {latest_activity.get('message', 'No message')}")
        
        # Test database connection
        try:
            historical_trades = trading_data_manager.get_historical_trades(5)
            print(f"🗄️ Historical Trades in DB: {len(historical_trades)}")
        except Exception as e:
            print(f"❌ Database error: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Dashboard should now display correct data!")
        print("🌐 Open http://localhost:5002 in your browser")
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print("🔧 Check if trading bot is running")

if __name__ == "__main__":
    test_dashboard_connection()
