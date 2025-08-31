#!/usr/bin/env python3
"""
Test dashboard WebSocket connection and data flow
"""

import time
import json
from core.dashboard.dashboard_data_manager import simple_rtm

def test_dashboard_data_flow():
    """Test if dashboard data is being updated properly"""
    print("🔍 Testing Dashboard Data Flow")
    print("=" * 50)
    
    # Get current SimpleRTM data
    data = simple_rtm.get_data()
    
    print(f"📊 Session Status: {data['session']['status']}")
    print(f"📊 Session ID: {data['session']['session_id']}")
    print(f"📊 Current Balance: ${data['session']['current_balance']:.2f}")
    print(f"📊 Activity Logs: {len(data['logs'])} entries")
    print(f"📊 Predictions: {len(data['predictions'])} entries")
    print(f"📊 Trades: {len(data['trades'])} entries")
    
    if data['logs']:
        print(f"📝 Latest Activity: {data['logs'][-1]['message']}")
        print(f"📝 Activity Time: {data['logs'][-1]['timestamp']}")
    
    if data['predictions']:
        print(f"🎯 Latest Prediction: {data['predictions'][-1]['type']}")
        print(f"🎯 Prediction Time: {data['predictions'][-1]['timestamp']}")
    
    print("\n🔍 Checking for data consistency issues...")
    
    # Check if session data is consistent
    if data['session']['status'] == 'no_session' and len(data['logs']) > 0:
        print("⚠️  WARNING: Session shows 'no_session' but there are activity logs!")
        print("   This suggests the session manager is not properly updating SimpleRTM")
    
    # Check if predictions are all HOLD with 0 confidence
    if data['predictions']:
        all_hold = all(p['type'] == 'HOLD' and p['confidence'] == 0 for p in data['predictions'])
        if all_hold:
            print("⚠️  WARNING: All predictions are HOLD with 0 confidence")
            print("   This suggests the prediction engine is not working properly")
    
    # Check if activity logs are recent
    if data['logs']:
        latest_log_time = data['logs'][-1]['timestamp']
        print(f"📅 Latest log time: {latest_log_time}")
        
        # Parse timestamp and check if it's recent (within last 5 minutes)
        try:
            from datetime import datetime
            log_time = datetime.fromisoformat(latest_log_time.replace('Z', '+00:00'))
            current_time = datetime.now()
            time_diff = (current_time - log_time).total_seconds()
            
            if time_diff > 300:  # 5 minutes
                print(f"⚠️  WARNING: Latest activity is {time_diff/60:.1f} minutes old")
            else:
                print(f"✅ Activity is recent ({time_diff:.1f} seconds ago)")
        except Exception as e:
            print(f"⚠️  Could not parse timestamp: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Dashboard data flow test completed")

if __name__ == "__main__":
    test_dashboard_data_flow()
