#!/usr/bin/env python3
"""
Test Balance Update System
Verifies that balance updates are properly tracked and displayed in dashboard
"""

import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_balance_updates():
    """Test the balance update system"""
    print("🔍 Testing Balance Update System")
    print("=" * 50)
    
    try:
        # Test 1: Create trading logger and test balance updates
        print("🧪 Test 1: Trading Logger Balance Updates")
        
        from core.trading_logger import TradingLogger
        
        # Create test logger
        logger = TradingLogger("test_logs")
        
        # Set initial balance
        initial_balance = 120.0
        logger.update_initial_balance(initial_balance)
        print(f"✅ Set initial balance: ${initial_balance:.2f}")
        
        # Simulate some balance changes
        current_balance = initial_balance
        
        # Simulate trade 1: Lose $5 in fees
        current_balance -= 5.0
        logger.update_current_balance(current_balance)
        print(f"✅ Updated balance after fees: ${current_balance:.2f}")
        
        # Simulate trade 2: Gain $8 profit
        current_balance += 8.0
        logger.update_current_balance(current_balance)
        print(f"✅ Updated balance after profit: ${current_balance:.2f}")
        
        # Simulate trade 3: Lose $12
        current_balance -= 12.0
        logger.update_current_balance(current_balance)
        print(f"✅ Updated balance after loss: ${current_balance:.2f}")
        
        # Check session metadata file
        session_file = f"test_logs/session_metadata_{logger.session_id}.json"
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session_data = json.load(f)
                
            print(f"\n📊 Session Metadata:")
            print(f"   Initial Balance: ${session_data.get('initial_balance', 'N/A')}")
            print(f"   Current Balance: ${session_data.get('current_balance', 'N/A')}")
            print(f"   Balance Change: ${session_data.get('balance_change', 'N/A')}")
            print(f"   Balance Change %: {session_data.get('balance_change_pct', 'N/A'):.2f}%")
            print(f"   Last Update: {session_data.get('last_balance_update', 'N/A')}")
        else:
            print(f"❌ Session metadata file not found: {session_file}")
        
        # Test 2: Dashboard balance reading
        print(f"\n🧪 Test 2: Dashboard Balance Reading")
        
        from simple_dashboard import SimpleBotDashboard
        
        # Create dashboard instance with test logs
        dashboard = SimpleBotDashboard()
        dashboard.log_dir = "test_logs"
        
        # Get trade summary
        trade_summary = dashboard.get_trade_summary()
        
        print(f"📊 Dashboard Balance Data:")
        print(f"   Total Trades: {trade_summary.get('total_trades', 'N/A')}")
        print(f"   Current Balance: ${trade_summary.get('current_balance', 'N/A'):.2f}")
        print(f"   Balance Change: ${trade_summary.get('balance_change', 'N/A'):.2f}")
        print(f"   Balance Source: {trade_summary.get('balance_source', 'N/A')}")
        print(f"   Last Update: {trade_summary.get('last_balance_update', 'N/A')}")
        
        # Test 3: Verify balance accuracy
        print(f"\n🎯 Test 3: Balance Accuracy Verification")
        expected_balance = 120.0 - 5.0 + 8.0 - 12.0  # 111.0
        actual_balance = trade_summary.get('current_balance', 0)
        
        if abs(actual_balance - expected_balance) < 0.01:
            print(f"✅ Balance calculation accurate!")
            print(f"   Expected: ${expected_balance:.2f}")
            print(f"   Actual: ${actual_balance:.2f}")
        else:
            print(f"❌ Balance calculation incorrect!")
            print(f"   Expected: ${expected_balance:.2f}")
            print(f"   Actual: ${actual_balance:.2f}")
        
        # Cleanup test files
        print(f"\n🧹 Cleaning up test files...")
        import shutil
        if os.path.exists("test_logs"):
            shutil.rmtree("test_logs")
            print("✅ Test files cleaned up")
        
        print(f"\n🎉 Balance Update System Test Complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_balance_updates()