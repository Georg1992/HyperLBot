#!/usr/bin/env python3
"""
Comprehensive fix for dashboard issues
"""

import json
import os
import time
from datetime import datetime
from core.realtime_data_manager import trading_data_manager

def fix_dashboard_issues():
    """Comprehensive fix for dashboard display issues"""
    print("🔧 Fixing Dashboard Issues")
    print("=" * 60)
    
    try:
        # Clear existing data and start fresh
        trading_data_manager.clear_all_data()
        print("🧹 Cleared existing real-time data")
        
        # Read latest session metadata
        log_dir = "trading_logs"
        session_files = [f for f in os.listdir(log_dir) if f.startswith("session_metadata_") and f.endswith(".json")]
        
        if not session_files:
            print("❌ No session metadata files found")
            return
        
        latest_session = max(session_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)))
        session_path = os.path.join(log_dir, latest_session)
        
        with open(session_path, 'r') as f:
            session_data = json.load(f)
        
        print(f"📊 Loading session: {session_data['session_id']}")
        print(f"💰 Balance: ${session_data['current_balance']:.2f}")
        print(f"📈 Change: ${session_data['balance_change']:.2f} ({session_data['balance_change_pct']:.2f}%)")
        
        # Start fresh session
        trading_data_manager.start_session(
            strategy=session_data['strategy'],
            initial_balance=session_data['initial_balance'],
            bot_version=session_data['bot_version']
        )
        
        # Update balance
        trading_data_manager.update_balance(
            session_data['current_balance'],
            f"Loaded from session {session_data['session_id']}"
        )
        
        # Load trade data
        trade_files = [f for f in os.listdir(os.path.join(log_dir, "trades")) if f.endswith(".json")]
        if trade_files:
            latest_trade_file = max(trade_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, "trades", f)))
            trade_path = os.path.join(log_dir, "trades", latest_trade_file)
            
            with open(trade_path, 'r') as f:
                trades_data = json.load(f)
            
            print(f"📋 Loading {len(trades_data)} trades")
            
            for trade in trades_data:
                # Create trade record
                trade_record = {
                    "trade_id": trade.get("trade_id"),
                    "side": trade.get("side"),
                    "entry_price": trade.get("price"),
                    "exit_price": trade.get("exit_price"),
                    "size": trade.get("size"),
                    "leverage": trade.get("leverage"),
                    "net_profit_loss": trade.get("net_profit_loss", 0),
                    "profit_loss_pct": trade.get("profit_loss_pct", 0),
                    "prediction_confidence": trade.get("signal_data", {}).get("prediction_confidence", 0),
                    "entry_time": trade.get("timestamp"),
                    "exit_time": trade.get("exit_timestamp"),
                    "holding_time": trade.get("holding_time", 0),
                    "exit_reason": trade.get("exit_reason", "UNKNOWN"),
                    "was_profitable": trade.get("was_profitable", False)
                }
                
                # Add trade directly to memory (bypass database to avoid conflicts)
                with trading_data_manager.data_lock:
                    trade_record_memory = {
                        "trade_id": trade_record["trade_id"],
                        "side": trade_record["side"],
                        "entry_price": trade_record["entry_price"],
                        "exit_price": trade_record["exit_price"],
                        "size": trade_record["size"],
                        "leverage": trade_record["leverage"],
                        "pnl": trade_record["net_profit_loss"],
                        "pnl_pct": trade_record["profit_loss_pct"],
                        "confidence": trade_record["prediction_confidence"],
                        "entry_time": trade_record["entry_time"],
                        "exit_time": trade_record["exit_time"],
                        "holding_time": trade_record["holding_time"],
                        "exit_reason": trade_record["exit_reason"],
                        "was_profitable": trade_record["was_profitable"],
                        "timestamp": time.time()
                    }
                    
                    trading_data_manager.recent_trades.append(trade_record_memory)
                    
                    # Update session statistics
                    session = trading_data_manager.current_state["session"]
                    session["total_trades"] += 1
                    if trade_record["was_profitable"]:
                        session["winning_trades"] += 1
                    else:
                        session["losing_trades"] += 1
                
                print(f"✅ Loaded trade: {trade_record['side']} at ${trade_record['entry_price']:,.2f}")
        
        # Add activity logs
        trading_data_manager.add_activity({
            "type": "SYSTEM",
            "message": f"Dashboard data loaded from session {session_data['session_id']}",
            "timestamp": time.time(),
            "level": "INFO"
        })
        
        trading_data_manager.add_activity({
            "type": "TRADE",
            "message": f"Loaded {len(trades_data)} trades from session",
            "timestamp": time.time(),
            "level": "INFO"
        })
        
        # Verify the fix
        current_state = trading_data_manager.get_current_state()
        print("\n" + "=" * 60)
        print("✅ Dashboard fix completed!")
        print(f"📊 Session Status: {current_state['session']['status']}")
        print(f"💰 Current Balance: ${current_state['session']['current_balance']:.2f}")
        print(f"📈 Total Trades: {current_state['session']['total_trades']}")
        print(f"🎯 Winning Trades: {current_state['session']['winning_trades']}")
        print(f"❌ Losing Trades: {current_state['session']['losing_trades']}")
        print(f"📋 Recent Trades in Memory: {len(current_state.get('recent_trades', []))}")
        print(f"📝 Activity Logs: {len(current_state.get('recent_activity', []))}")
        
        print("\n🌐 Refresh http://localhost:5002 to see the fixed dashboard!")
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_dashboard_issues()
