# Simulated Account Management System

## Overview

The HyperLBot now includes a comprehensive simulated account management system that allows users to create, manage, and reset simulated trading accounts. This system provides persistent account data across sessions, similar to how a real trading account would function.

## Features

### 🎮 Account Creation & Management
- **First Launch**: Bot prompts for initial balance to create a new simulated account
- **Subsequent Launches**: Bot detects existing account and offers options to continue or reset
- **Single Account**: Only one simulated account can exist at any time
- **Persistent Data**: Account data persists between sessions

### 💰 Balance Tracking
- **Initial Balance**: Set by user on first launch
- **Current Balance**: Updated in real-time during trading
- **P&L Tracking**: Realized and unrealized profit/loss tracking
- **Balance History**: Complete balance change history

### 📊 Trade Management
- **Trade Recording**: All trades are recorded with detailed information
- **Trade History**: Complete history of all trades with timestamps
- **Win/Loss Tracking**: Automatic tracking of winning and losing trades
- **P&L Calculation**: Detailed profit/loss calculations per trade

### 📈 Session Management
- **Session Tracking**: Each trading session is recorded
- **Session History**: Complete history of all sessions
- **Performance Metrics**: Session-level performance tracking
- **Balance Changes**: Track balance changes per session

## File Structure

### Core Files
- `core/account_manager.py` - Main account management module
- `simulated_account.json` - Persistent account data storage

### Integration Points
- `main.py` - Account creation/loading prompts
- `core/realtime_data_manager.py` - Account data integration
- `strategies/hybrid_paper_trading_bot.py` - Trading integration

## Usage

### First Launch
When launching the bot for the first time:

```
🎮 Simulated Account Management:
No existing account found.

Enter initial balance for new account (default 120.0): 1000
✅ Created new simulated account with balance: $1000.00
```

### Subsequent Launches
When an account already exists:

```
🎮 Simulated Account Management:
✅ Loaded existing simulated account (Balance: $1000.00)
📊 Existing Account Found:
   Account ID: sim_account_1234567890
   Current Balance: $1000.00
   Total Trades: 5
   Win Rate: 80.0%
   Open Positions: 0
   Created: 2025-08-23

Choose action:
1. Continue with existing account
2. Create new account (reset)
Enter choice (1-2): 1
```

### Account Reset
When choosing to create a new account:

```
✅ Existing account deleted - ready for new account creation
Enter initial balance for new account (default 120.0): 2000
✅ Created new simulated account with balance: $2000.00
```

## Account Data Structure

The account data is stored in `simulated_account.json` with the following structure:

```json
{
  "account_id": "sim_account_1234567890",
  "created_at": "2025-08-23T21:13:01.352264",
  "last_updated": "2025-08-23T21:13:52.936517",
  "initial_balance": 1111.0,
  "current_balance": 1131.64,
  "total_deposits": 1111.0,
  "total_withdrawals": 0.0,
  "total_trades": 1,
  "winning_trades": 1,
  "losing_trades": 0,
  "total_pnl": 20.64,
  "realized_pnl": 20.67,
  "unrealized_pnl": -0.03,
  "open_positions": [],
  "trade_history": [...],
  "session_history": [...],
  "account_status": "active"
}
```

## Trade Recording

Each trade is recorded with comprehensive details:

```json
{
  "trade_id": "hybrid_trade_1",
  "side": "SELL",
  "entry_price": 115257.55,
  "exit_price": 115234.50,
  "size": 0.001,
  "leverage": 30,
  "pnl": 20.67,
  "pnl_pct": 0.6,
  "confidence": 35.3,
  "entry_time": 1755972830.1976352,
  "exit_time": 1755972830.1976352,
  "holding_time": 27.24,
  "exit_reason": "GRACEFUL_SHUTDOWN",
  "was_profitable": true,
  "is_winback_trade": false,
  "timestamp": "2025-08-23T21:13:50.200635"
}
```

## Session Tracking

Each trading session is tracked with performance metrics:

```json
{
  "session_id": "session_1755972790",
  "strategy": "standard",
  "initial_balance": 1111.0,
  "start_time": "2025-08-23T21:13:10.722040",
  "end_time": "2025-08-23T21:13:52.936517",
  "final_balance": 1131.64,
  "total_trades": 1,
  "winning_trades": 1,
  "losing_trades": 0,
  "balance_change": 20.64,
  "timestamp": "2025-08-23T21:13:52.936517"
}
```

## Integration Points

### Main Application (`main.py`)
- Handles account creation/loading prompts
- Integrates account manager with bot initialization
- Provides user interface for account management

### Real-time Data Manager (`core/realtime_data_manager.py`)
- Integrates with account manager for balance updates
- Records trades to account history
- Updates session information

### Trading Bot (`strategies/hybrid_paper_trading_bot.py`)
- Updates account balance on trade execution
- Records trade details to account manager
- Integrates account data with trading decisions

## Benefits

### 🎯 User Experience
- **Persistent Progress**: Trading progress is saved between sessions
- **Account Reset**: Easy reset functionality for testing different strategies
- **Clear Interface**: Simple prompts for account management

### 📊 Data Management
- **Comprehensive Tracking**: Complete trade and session history
- **Performance Analytics**: Detailed performance metrics
- **Data Persistence**: Reliable data storage across sessions

### 🔧 Technical Benefits
- **Modular Design**: Clean separation of account management logic
- **Easy Integration**: Seamless integration with existing trading systems
- **Extensible**: Easy to add new account features

## Future Enhancements

### Potential Features
- **Multiple Accounts**: Support for multiple simulated accounts
- **Account Import/Export**: Ability to import/export account data
- **Advanced Analytics**: More detailed performance analytics
- **Account Templates**: Pre-configured account templates
- **Backup/Restore**: Account backup and restore functionality

### Technical Improvements
- **Database Storage**: Move from JSON to SQLite for better performance
- **Real-time Sync**: Real-time account data synchronization
- **API Integration**: REST API for account management
- **Web Interface**: Web-based account management interface

## Conclusion

The simulated account management system provides a robust foundation for paper trading with persistent data across sessions. It offers users a realistic trading experience while maintaining the safety of simulated trading. The system is designed to be user-friendly, comprehensive, and easily extensible for future enhancements.
