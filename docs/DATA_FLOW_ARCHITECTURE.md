# Data Flow Architecture

## Core Principle: RTM and Dashboard are NEVER sources of data

### Data Flow Direction
```
SOURCE SYSTEMS → RTM → DASHBOARD
```

**NEVER:**
```
RTM → SOURCE SYSTEMS (WRONG!)
DASHBOARD → SOURCE SYSTEMS (WRONG!)
```

### Source Systems (Sources of Truth)

#### 1. SessionManager
- **Responsibility**: Session lifecycle and state management
- **Data**: Session ID, status, start/end times, strategy, duration
- **Methods**: `start_session()`, `end_session()`, `get_current_session_data()`
- **Location**: `core/session/session_manager.py`

#### 2. AccountManager  
- **Responsibility**: Account balance and trade statistics
- **Data**: Current balance, initial balance, total PnL, win rate, trade counts
- **Methods**: `update_balance()`, `get_account_summary()`
- **Location**: `core/account_manager.py`

#### 3. Trading Bot (HybridPaperTradingBot)
- **Responsibility**: Market data and trading logic
- **Data**: Current price, RSI, volume, volatility, market analysis
- **Methods**: `_update_market_data_centralized()`, `_update_simple_rtm_activity()`
- **Location**: `strategies/hybrid_paper_trading_bot.py`

### Presentation Layer (RTM)

#### SimpleRTM
- **Responsibility**: Data aggregation and presentation
- **Data Flow**: READ-ONLY from source systems
- **Methods**: 
  - `get_session_data()` → reads from SessionManager
  - `get_account_data()` → reads from AccountManager  
  - `get_dashboard_data()` → aggregates all data for dashboard
- **Location**: `core/data/simple_rtm.py`

### Frontend Layer (Dashboard)

#### RealtimeDashboard
- **Responsibility**: Web interface for monitoring
- **Data Flow**: READ-ONLY from RTM
- **Methods**: `_get_dashboard_data()` → reads from SimpleRTM
- **Location**: `realtime_dashboard.py`

## Correct Data Update Flow

### 1. Session Updates
```
Bot calls session_manager.start_session() 
→ SessionManager updates internal state
→ SimpleRTM.get_session_data() reads from SessionManager
→ Dashboard displays updated session status
```

### 2. Balance Updates  
```
Bot calls account_manager.update_balance()
→ AccountManager updates internal state
→ SimpleRTM.get_account_data() reads from AccountManager
→ Dashboard displays updated balance
```

### 3. Market Data Updates
```
Bot calls simple_rtm.update_market()
→ SimpleRTM stores market data
→ Dashboard displays updated market data
```

### 4. Activity Logging
```
Bot calls simple_rtm.add_activity()
→ SimpleRTM stores activity log
→ Dashboard displays activity log
```

## Forbidden Patterns

### ❌ WRONG - Reading from RTM in source systems
```python
# SessionManager should NEVER do this:
session_data = simple_rtm.get_dashboard_data()["session"]
```

### ❌ WRONG - Dashboard updating source systems
```python
# Dashboard should NEVER do this:
session_manager.start_session()
```

### ✅ CORRECT - Source systems updating their own state
```python
# SessionManager updates its own state:
self.current_session_data = {...}
```

### ✅ CORRECT - RTM reading from source systems
```python
# SimpleRTM reads from SessionManager:
session_data = session_manager.get_current_session_data()
```

## Data Ownership

| Data Type | Owner | RTM Role | Dashboard Role |
|-----------|-------|----------|----------------|
| Session Status | SessionManager | Read | Display |
| Account Balance | AccountManager | Read | Display |
| Market Data | Trading Bot | Store & Read | Display |
| Activity Logs | SimpleRTM | Store & Read | Display |
| Trade History | SimpleRTM | Store & Read | Display |

## Benefits of This Architecture

1. **Single Source of Truth**: Each data type has one authoritative source
2. **No Circular Dependencies**: Data flows in one direction only
3. **Clear Separation of Concerns**: Each system has a specific responsibility
4. **Easy Debugging**: Data issues can be traced to specific source systems
5. **Scalable**: New data types can be added without affecting existing systems
