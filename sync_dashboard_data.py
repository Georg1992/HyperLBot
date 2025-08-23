#!/usr/bin/env python3
"""
Script to sync real-time data manager with latest session data
"""

import json
import os
import time
from datetime import datetime
from core.realtime_data_manager import trading_data_manager

def sync_dashboard_data():
    """Sync real-time data manager with latest session and trade data"""
    print("🔄 Syncing Dashboard Data with Latest Session Information")
    print("=" * 60)
    
    try:
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
        
        print(f"📊 Latest Session: {session_data['session_id']}")
        print(f"💰 Current Balance: ${session_data['current_balance']:.2f}")
        print(f"📈 Balance Change: ${session_data['balance_change']:.2f} ({session_data['balance_change_pct']:.2f}%)")
        
        # Start session in real-time manager
        trading_data_manager.start_session(
            strategy=session_data['strategy'],
            initial_balance=session_data['initial_balance'],
            bot_version=session_data['bot_version']
        )
        
        # Update balance
        trading_data_manager.update_balance(
            session_data['current_balance'],
            f"Synced from session {session_data['session_id']}"
        )
        
        # Read and sync trade data
        trade_files = [f for f in os.listdir(os.path.join(log_dir, "trades")) if f.endswith(".json")]
        if trade_files:
            latest_trade_file = max(trade_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, "trades", f)))
            trade_path = os.path.join(log_dir, "trades", latest_trade_file)
            
            with open(trade_path, 'r') as f:
                trades_data = json.load(f)
            
            print(f"📋 Found {len(trades_data)} trades to sync")
            
            for trade in trades_data:
                # Convert to real-time manager format
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
                
                # Add trade to real-time manager
                trading_data_manager.add_trade(trade_record)
                print(f"✅ Synced trade: {trade_record['side']} at ${trade_record['entry_price']:,.2f}")
        
        # Read and sync signal data
        signal_files = [f for f in os.listdir(os.path.join(log_dir, "signals")) if f.endswith(".json")]
        if signal_files:
            latest_signal_file = max(signal_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, "signals", f)))
            signal_path = os.path.join(log_dir, "signals", latest_signal_file)
            
            with open(signal_path, 'r') as f:
                signals_data = json.load(f)
            
            print(f"📡 Found {len(signals_data)} signals to sync")
            
            for signal in signals_data:
                signal_record = {
                    "type": "TRADING_SIGNAL",
                    "side": signal.get("side"),
                    "entry_price": signal.get("current_price"),
                    "confidence": signal.get("confidence", 0),
                    "timeframe": 300,  # 5 minutes
                    "reason": signal.get("reason", "")
                }
                
                trading_data_manager.add_trading_signal(signal_record)
        
        # Add activity log
        trading_data_manager.add_activity({
            "type": "SYNC",
            "message": f"Dashboard data synced from session {session_data['session_id']}",
            "timestamp": time.time(),
            "level": "INFO"
        })
        
        print("\n" + "=" * 60)
        print("✅ Dashboard data sync completed!")
        print("🌐 Refresh http://localhost:5002 to see updated data")
        
        # Show current state
        current_state = trading_data_manager.get_current_state()
        print(f"📊 Session Status: {current_state['session']['status']}")
        print(f"💰 Balance: ${current_state['session']['current_balance']:.2f}")
        print(f"📈 Total Trades: {current_state['session']['total_trades']}")
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")

if __name__ == "__main__":
    sync_dashboard_data()
