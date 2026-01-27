# HyperLBot - Complete Workflow & Architecture
**Purpose:** Comprehensive architecture documentation for AI-to-AI communication  
**Date:** 2026-01-27  
**Status:** Production-ready trading bot

---

## 🎯 SYSTEM OVERVIEW

**HyperLBot** is a real-time cryptocurrency trading bot that:
- Analyzes market data from multiple sources (Hyperliquid, Binance, external APIs)
- Generates trading predictions based on technical analysis
- Manages risk with dynamic position sizing
- Operates in paper trading mode (simulated execution)

**Core Principle:** **NO FALLBACKS** - All data must be present and valid, or the system fails fast with clear errors.

---

## 🏗️ ARCHITECTURE OVERVIEW

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM INITIALIZATION                    │
│  (SystemInitializer) - One-time setup on bot start          │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
       ┌───────▼────────┐            ┌────────▼─────────┐
       │ Market Data    │            │   Dashboard      │
       │   Service      │            │    Service       │
       │ (Unified data) │◄──────────┤ (WebSocket UI)   │
       └───────┬────────┘            └──────────────────┘
               │
       ┌───────▼────────────────────────────────────────┐
       │         Analysis Modules (Cached)              │
       ├────────────────────────────────────────────────┤
       │ • RSI Calculator      • Volume Analyzer        │
       │ • Volatility Tracker  • S/R Detector           │
       │ • Trend Analyzer      • Pattern Recognition    │
       │ • Market Conditions   • Pressure Analysis      │
       └────────────────────────────────────────────────┘
               │
       ┌───────▼────────┐
       │  Prediction    │
       │    Engine      │
       │ (Entry setup)  │
       └────────────────┘
```

---

## 🔄 COMPLETE WORKFLOW

### PHASE 1: SYSTEM INITIALIZATION (One-Time, on Bot Start)

**Entry Point:** `main.py` → `run_paper_trading()`

**Steps:**

1. **SystemInitializer.initialize_system()**
   - Initialize APIs (Hyperliquid, Binance, external)
   - Initialize WebSocket connections
   - Create singleton services (MarketDataService, DashboardService, SessionOrchestrator)
   - Register analysis modules with MarketDataService
   - Initialize database (SQLite with WAL mode)
   - Health check

2. **SessionManager.start_session()**
   - Create trading session
   - Load or create simulated account
   - Initialize balance tracking

3. **Start Dashboard**
   - Launch Flask web server
   - Start WebSocket server for real-time updates
   - Open browser to dashboard

**Result:** All systems initialized and ready

---

### PHASE 2: MAIN DATA LOOP (Continuous, Every 5 Seconds)

**Location:** `SessionOrchestrator._main_data_loop()`

**Loop Frequency:** Every `check_interval` seconds (default: 5s)

#### **ITERATION WORKFLOW:**

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN DATA LOOP ITERATION                 │
└─────────────────────────────────────────────────────────────┘

STEP 1: Candle Boundary Detection
├─ Check if new 5-minute candle closed (00, 05, 10, 15, etc.)
├─ If yes:
│  ├─ Update candle storage database
│  ├─ Invalidate pattern/trend caches
│  └─ Recalculate RSI baseline
└─ Continue

STEP 2: Fetch ALL Raw API Data (Parallel)
├─ RawDataFetcher.fetch_all_raw_data()
├─ Parallel execution (ThreadPoolExecutor, 8 workers):
│  ├─ price: WebSocket current price
│  ├─ orderbook: WebSocket/API orderbook
│  ├─ funding: API funding rate
│  ├─ fear_greed: External API (cached 10min)
│  ├─ whale: External API (cached 5min)
│  ├─ news: RSS feeds (cached 5min)
│  └─ cross_asset: Yahoo Finance (cached 5min)
└─ All data mandatory (NO FALLBACKS) - raises if any fails

STEP 3: Trigger Analysis Modules
├─ SessionOrchestrator._trigger_analysis_modules()
├─ Store raw_data in MarketDataService
├─ Determine which modules need updates (TTL-based)
├─ Call analysis module getters via MarketDataService:
│  ├─ get_rsi_analysis()
│  ├─ get_volatility_analysis()
│  ├─ get_trend_analysis()
│  ├─ get_support_resistance_analysis()
│  ├─ get_volume_analysis()
│  ├─ get_pressure_analysis()
│  ├─ get_pattern_analysis()
│  ├─ get_market_conditions_analysis(raw_data)
│  ├─ get_funding_analysis(raw_data)
│  ├─ get_orderbook_analysis()
│  ├─ get_cross_asset_analysis(raw_data)
│  └─ get_iv_squeeze_analysis()
└─ All modules use pre-fetched raw_data (no redundant API calls)

STEP 4: Assemble Unified Market Data
├─ MarketDataService.get_unified_analysis_data()
├─ Combines all analysis results into single dict:
│  ├─ Core: current_price, timestamp, strategy
│  ├─ Technical: rsi, trend, volatility, volume, pressure
│  ├─ S/R: support_resistance (all levels, strategy-independent)
│  ├─ Patterns: pattern recognition results
│  ├─ Market: market_conditions, funding_analysis
│  └─ External: cross_asset_analysis, orderbook_analysis
└─ Strategy is None at this point (determined later)

STEP 5: Strategy Detection
├─ StrategyDetector.detect_and_update_strategy()
├─ StrategyManager.detect_optimal_strategy(unified_data)
├─ Scores all strategies based on:
│  ├─ Volatility category
│  ├─ Trend direction (multi-timeframe)
│  ├─ Volume category
│  ├─ RSI value
│  ├─ Pressure direction
│  ├─ Market conditions
│  └─ Pattern signals
├─ Selects best strategy (highest score)
└─ Updates unified_data["strategy"]

STEP 6: Filter S/R Levels (Strategy-Aware)
├─ StrategyDetector.filter_sr_levels_for_dashboard()
├─ SRLevelFilter.filter_levels_for_strategy()
├─ Applies strategy-specific filters:
│  ├─ max_levels_per_side (scalping=1, standard=2, swing=3)
│  ├─ max_distance_pct (scalping=0.5%, swing=5%)
│  └─ min_level_distance_pct (prevents clustering)
└─ Updates unified_data["support_resistance"] with filtered levels

STEP 7: Generate Prediction
├─ PredictionEngine.generate_prediction(unified_data, strategy)
├─ Strategy-specific prediction method (e.g., _predict_scalping)
├─ Sequential decision flow:
│  │
│  ├─ STEP 7a: Determine Direction
│  │  ├─ _score_direction(unified_data, strategy)
│  │  ├─ Scores LONG vs SHORT using strategy weights:
│  │  │  ├─ trend (multi-timeframe)
│  │  │  ├─ rsi (oversold/overbought)
│  │  │  ├─ pressure (buy/sell pressure)
│  │  │  ├─ sr_proximity (distance to S/R)
│  │  │  ├─ patterns (pattern signals)
│  │  │  ├─ volume (volume trends)
│  │  │  ├─ market_conditions (sentiment)
│  │  │  └─ cross_asset (correlation)
│  │  ├─ Calculates long_score and short_score
│  │  ├─ Checks min_score_diff threshold
│  │  └─ Returns direction (LONG/SHORT) or None if too weak
│  │
│  ├─ STEP 7b: Generate Entry Setups (for selected direction)
│  │  ├─ _generate_setups_for_direction()
│  │  ├─ Finds all S/R levels for direction
│  │  ├─ Generates 4 entry candidates per level:
│  │  │  ├─ Entry at level (0.0×ATR offset)
│  │  │  ├─ Entry inside level (0.3×ATR offset)
│  │  │  ├─ Entry inside level (0.5×ATR offset)
│  │  │  └─ Entry near level (1.0×ATR offset)
│  │  ├─ Scores each entry candidate:
│  │  │  ├─ level_strength (30%): S/R power
│  │  │  ├─ entry_quality (40%): proximity to level
│  │  │  └─ fill_probability (30%): distance from current
│  │  └─ Returns list of scored setups
│  │
│  ├─ STEP 7c: Select Best Entry Setup
│  │  ├─ Selects highest entry_score setup
│  │  └─ Extracts entry_price, entry_reasoning
│  │
│  ├─ STEP 7d: Calculate Stop Loss & Take Profit
│  │  ├─ _calculate_stop_and_target()
│  │  ├─ Stop Loss:
│  │  │  ├─ Finds strongest S/R level opposite direction
│  │  │  ├─ Applies round number avoidance ($90K, $95K offsets)
│  │  │  ├─ Applies risk constraint (max % from entry)
│  │  │  └─ Selects best stop (S/R constraint vs risk constraint)
│  │  ├─ Take Profit:
│  │  │  ├─ Finds strongest S/R level in direction
│  │  │  ├─ Applies ATR cushion (0.25-1.0×ATR before level)
│  │  │  └─ Validates R:R ratio (guideline, not hard filter)
│  │  └─ Calculates risk_reward_ratio
│  │
│  └─ STEP 7e: Calculate Confidence (PLACEHOLDER)
│     ├─ _calculate_prediction_confidence()
│     ├─ Currently returns None (not implemented)
│     └─ Will use: setup_data, unified_data, strategy
│
└─ Returns TradingPrediction or None

STEP 8: Calculate Position Size
├─ PositionSizeCalculator.calculate_position_size()
├─ Inputs:
│  ├─ balance: Current account balance
│  ├─ base_position_size_pct: From strategy config
│  ├─ risk_reward_ratio: From prediction
│  ├─ leverage: Trading leverage (default: 40x)
│  ├─ entry_price, stop_loss, direction
│  └─ confidence: Optional (for future confidence-based sizing)
├─ Calculations:
│  ├─ R:R multiplier (0.5x - 1.5x based on R:R)
│  ├─ Liquidation safety factor (0.3x - 1.0x based on SL distance to liquidation)
│  ├─ Confidence multiplier (1.0x placeholder, will be implemented)
│  └─ Final size: balance × base_pct × rr_mult × liq_safety × conf_mult × leverage / entry_price
└─ Returns position_size_btc and position_value_usd

STEP 9: Process Momentum Signals (Reactive Engine)
├─ MomentumProcessor.process_momentum_signals()
├─ ReactiveEngine.detect_momentum_breakouts()
├─ Detects high-confidence momentum signals
├─ Places market orders immediately (not limit orders)
└─ Separate from prediction engine (different execution style)

STEP 10: Update Dashboard
├─ DashboardUpdater.update_dashboard_with_unified_data()
├─ Adds prediction to unified_data
├─ Writes to dashboard_data.json
├─ WebSocket broadcasts to connected clients
└─ Dashboard displays real-time updates

STEP 11: Sleep & Repeat
└─ time.sleep(check_interval) → Back to STEP 1
```

---

## 📊 DATA FLOW DETAILS

### Raw Data → Analysis → Prediction Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    RAW DATA FETCHING                        │
│  (Parallel, ThreadPoolExecutor, 8 workers)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Hyperliquid WebSocket ──┐                                 │
│  Hyperliquid API ────────┼─→ price, orderbook, funding    │
│  Binance API ─────────────┤                                 │
│  Fear & Greed API ────────┤                                 │
│  Whale Analytics API ─────┼─→ fear_greed, whale, news,     │
│  RSS News API ────────────┤    cross_asset                  │
│  Yahoo Finance API ───────┘                                 │
│                                                              │
│  Result: raw_data dict with all API responses               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              ANALYSIS MODULE PROCESSING                     │
│  (Sequential, TTL-based caching, strategy-independent)      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  raw_data ──→ MarketDataService.set_raw_data()             │
│                                                              │
│  Analysis Modules (called via MarketDataService):           │
│  ├─ RSI Calculator: raw_data not needed (uses WebSocket)    │
│  ├─ Volatility Calculator: Uses historical candles          │
│  ├─ Trend Calculator: Uses historical candles              │
│  ├─ S/R Calculator: Uses historical candles + current_price│
│  ├─ Volume Calculator: Uses WebSocket trades + historical  │
│  ├─ Pressure Calculator: Uses orderbook from raw_data      │
│  ├─ Pattern Recognition: Uses historical candles            │
│  ├─ Market Conditions: Uses raw_data (fear_greed, whale)   │
│  ├─ Funding Rate: Uses raw_data["funding"]                 │
│  ├─ Orderbook Analysis: Uses raw_data["orderbook"]          │
│  ├─ Cross Asset: Uses raw_data["cross_asset"]               │
│  └─ IV Squeeze: Uses historical candles                    │
│                                                              │
│  Result: Each module returns analysis dict                  │
│  Caching: CentralizedCache with TTL policies                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              UNIFIED DATA ASSEMBLY                          │
│  (Strategy-independent, all analysis combined)             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  MarketDataService.get_unified_analysis_data()              │
│                                                              │
│  unified_data = {                                           │
│    "current_price": float,                                  │
│    "timestamp": float,                                      │
│    "strategy": None,  # Set later                           │
│    "rsi": {...},                                            │
│    "trend": {...},                                          │
│    "volatility": {...},                                     │
│    "volume": {...},                                         │
│    "pressure": {...},                                       │
│    "support_resistance": {...},  # ALL levels               │
│    "patterns": {...},                                       │
│    "market_conditions": {...},                              │
│    "funding_analysis": {...},                               │
│    "orderbook_analysis": {...},                             │
│    "cross_asset_analysis": {...},                           │
│    "iv_squeeze": {...}                                      │
│  }                                                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              STRATEGY DETECTION                              │
│  (Uses unified_data, independent of S/R)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  StrategyManager.detect_optimal_strategy(unified_data)      │
│                                                              │
│  Scores all strategies using:                                │
│  ├─ volatility_category                                     │
│  ├─ trend_direction (multi-timeframe)                       │
│  ├─ volume_category                                         │
│  ├─ rsi_value                                               │
│  ├─ pressure direction                                      │
│  ├─ market_conditions                                        │
│  └─ pattern signals                                         │
│                                                              │
│  Selects best strategy (highest score)                      │
│  Updates unified_data["strategy"]                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              S/R LEVEL FILTERING                             │
│  (Strategy-aware, filters unified_data["support_resistance"])│
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  SRLevelFilter.filter_levels_for_strategy()                  │
│                                                              │
│  Applies strategy-specific filters:                          │
│  ├─ max_levels_per_side (scalping=1, standard=2, swing=3)   │
│  ├─ max_distance_pct (scalping=0.5%, swing=5%)               │
│  └─ min_level_distance_pct (prevents clustering)            │
│                                                              │
│  Updates unified_data["support_resistance"] with filtered   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              PREDICTION GENERATION                           │
│  (Strategy-aware, uses filtered S/R levels)                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PredictionEngine.generate_prediction(unified_data, strategy)│
│                                                              │
│  1. Score Direction (LONG vs SHORT)                         │
│  2. Generate Entry Setups (for selected direction)          │
│  3. Select Best Entry Setup                                 │
│  4. Calculate Stop Loss & Take Profit                      │
│  5. Calculate Confidence (placeholder)                    │
│                                                              │
│  Returns TradingPrediction or None                          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              POSITION SIZING                                 │
│  (Uses prediction R:R, leverage, confidence)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PositionSizeCalculator.calculate_position_size()            │
│                                                              │
│  Calculates:                                                 │
│  ├─ R:R multiplier (0.5x - 1.5x)                           │
│  ├─ Liquidation safety factor (0.3x - 1.0x)                 │
│  ├─ Confidence multiplier (1.0x placeholder)                │
│  └─ Final position size in BTC                              │
│                                                              │
│  Returns position_size_btc, position_value_usd              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              DASHBOARD UPDATE                                │
│  (Real-time WebSocket broadcast)                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  unified_data["prediction"] = TradingPrediction              │
│  DashboardService.write_dashboard_data()                    │
│  WebSocket.broadcast() → Frontend updates                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 KEY DESIGN PATTERNS

### 1. **NO FALLBACKS Policy**
- **Principle:** All required data must be present, or system fails fast
- **Implementation:** Direct dict access (`data["key"]`), not `.get()` with defaults
- **Rationale:** Prevents silent data corruption, ensures reliability

### 2. **Strategy-Independent Analysis**
- **Principle:** Analysis modules don't know about trading strategies
- **Implementation:** All analysis done before strategy detection
- **Benefit:** No circular dependencies, clean separation

### 3. **Dependency Injection**
- **Principle:** Dependencies passed as parameters, not global singletons
- **Implementation:** Factory functions, constructor injection
- **Benefit:** Testable, maintainable, follows SOLID principles

### 4. **Centralized Caching**
- **Principle:** Single cache system with TTL policies
- **Implementation:** `CentralizedCache` with module-specific TTLs
- **Benefit:** Prevents redundant calculations, consistent invalidation

### 5. **Sequential Decision Flow**
- **Principle:** Direction → Entry → Stop/Target (in that order)
- **Implementation:** Prediction engine follows strict sequence
- **Benefit:** Clear logic, easier to debug and maintain

---

## 📦 CORE COMPONENTS

### **SessionOrchestrator**
- **Responsibility:** Main loop coordination
- **Key Methods:**
  - `run_paper_trading_session()` - Entry point
  - `_main_data_loop()` - Main iteration loop
  - `_prepare_market_data_iteration()` - Data preparation
  - `_process_strategy_and_prediction()` - Strategy & prediction

### **MarketDataService**
- **Responsibility:** Coordinate all analysis modules
- **Key Methods:**
  - `get_unified_analysis_data()` - Assemble all analysis
  - `get_rsi_analysis()`, `get_volatility_analysis()`, etc. - Module getters
  - `register_analysis_module()` - Register analysis modules

### **RawDataFetcher**
- **Responsibility:** Fetch all raw API data in parallel
- **Key Methods:**
  - `fetch_all_raw_data()` - Parallel fetch of all APIs
  - Returns dict with price, orderbook, funding, external APIs

### **StrategyManager**
- **Responsibility:** Detect optimal trading strategy
- **Key Methods:**
  - `detect_optimal_strategy()` - Score and select best strategy
  - Uses volatility, trend, volume, RSI, pressure, patterns

### **PredictionEngine**
- **Responsibility:** Generate trading predictions
- **Key Methods:**
  - `generate_prediction()` - Main entry point
  - `_score_direction()` - Determine LONG vs SHORT
  - `_generate_setups_for_direction()` - Generate entry setups
  - `_calculate_stop_and_target()` - Risk management
  - `_calculate_prediction_confidence()` - Confidence (placeholder)

### **PositionSizeCalculator**
- **Responsibility:** Calculate position sizes
- **Key Methods:**
  - `calculate_position_size()` - Main calculation
  - `calculate_rr_multiplier()` - R:R-based scaling
  - Considers: balance, R:R, leverage, liquidation safety, confidence

---

## 🔄 CRITICAL PATHS

### **Price Update Path (Real-Time)**
```
WebSocket Price Update
  → HyperliquidWebSocket._process_trades_update()
  → Price cache updated (thread-safe)
  → Callbacks invoked (RSI, Dashboard)
  → RSI recalculated immediately
  → Dashboard updated via WebSocket
```

### **Candle Boundary Path (Every 5 Minutes)**
```
5-Minute Boundary Detected (00, 05, 10, 15, etc.)
  → CandleStorage.update_with_latest_candle()
  → Database updated (atomic transaction)
  → Pattern cache invalidated
  → Trend cache invalidated
  → RSI baseline recalculated
```

### **Prediction Generation Path (Every 5 Seconds)**
```
Main Loop Iteration
  → Fetch raw data (parallel)
  → Trigger analysis modules
  → Assemble unified data
  → Detect strategy
  → Filter S/R levels
  → Generate prediction
  → Calculate position size
  → Update dashboard
```

---

## 🎯 DECISION POINTS

### **Strategy Selection**
- **Input:** Market conditions (volatility, trend, volume, RSI, pressure)
- **Output:** Strategy name (scalping, standard, swing, etc.)
- **Logic:** Scores all strategies, selects highest
- **Frequency:** Every loop iteration (5 seconds)

### **Direction Determination**
- **Input:** Unified market data, strategy config
- **Output:** LONG, SHORT, or None
- **Logic:** Weighted scoring of 8 factors
- **Threshold:** min_score_diff (strategy-specific)

### **Entry Setup Selection**
- **Input:** Direction, S/R levels, current price
- **Output:** Best entry setup (price, score, reasoning)
- **Logic:** Generates 4 candidates per level, scores, selects best
- **Factors:** Level strength (30%), entry quality (40%), fill probability (30%)

### **Stop Loss Selection**
- **Input:** Entry price, direction, S/R levels
- **Output:** Stop loss price
- **Logic:** Strongest opposite S/R level, with round number avoidance
- **Constraints:** Max risk % from entry, liquidation safety

### **Take Profit Selection**
- **Input:** Entry price, direction, S/R levels, ATR
- **Output:** Take profit price
- **Logic:** Strongest same-direction S/R level, with ATR cushion
- **Validation:** R:R ratio (guideline, not hard filter)

---

## 📊 DATA STRUCTURES

### **TradingPrediction**
```python
@dataclass
class TradingPrediction:
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: Optional[float]  # 0.0-100.0, None if not implemented
    reasoning: str
    strategy: str
    timestamp: float
    risk_reward_ratio: float
    position_size_btc: Optional[float]
    position_size_usd: Optional[float]
```

### **Unified Data Structure**
```python
unified_data = {
    # Core
    "current_price": float,
    "timestamp": float,
    "strategy": str,  # Set after strategy detection
    
    # Technical Analysis
    "rsi": {...},
    "trend": {...},
    "volatility": {...},
    "volume": {...},
    "pressure": {...},
    "support_resistance": {...},  # Filtered by strategy
    "patterns": {...},
    
    # Market Context
    "market_conditions": {...},
    "funding_analysis": {...},
    "orderbook_analysis": {...},
    "cross_asset_analysis": {...},
    "iv_squeeze": {...},
    
    # Trading
    "prediction": TradingPrediction or None,
    "session_data": {...},
    "trading_data": {...}
}
```

---

## 🔒 THREAD SAFETY

### **Single-Threaded Core**
- Main loop runs in single thread
- Trading logic is sequential
- No race conditions in core logic

### **Multi-Threaded Components**
- **WebSocket:** Separate thread for data reception
- **Dashboard:** Separate thread for Flask server
- **Raw Data Fetching:** ThreadPoolExecutor (8 workers) for parallel API calls

### **Synchronization**
- **Price Cache:** `threading.RLock()` for thread-safe updates
- **Database:** SQLite with WAL mode (concurrent reads)
- **Cache:** `threading.RLock()` for cache operations

---

## 🗄️ DATA PERSISTENCE

### **SQLite Database**
- **File:** `data/candles_5m_btc.db`
- **Schema:** 5-minute candles (timestamp, OHLCV)
- **Features:**
  - WAL mode (concurrent reads/writes)
  - Atomic transactions
  - Rolling 5-year window
  - Indexed for fast queries

### **JSON Files**
- **Account:** `data/accounts/simulated_account.json`
- **Dashboard:** `data/temp/dashboard_data.json`
- **Heartbeat:** `data/temp/bot_heartbeat.json`

---

## 🎨 DASHBOARD ARCHITECTURE

### **Backend (Flask + SocketIO)**
- **File:** `core/dashboard/web_dashboard.py`
- **Features:**
  - REST API for initial data load
  - WebSocket for real-time updates
  - Broadcasts unified_data to all clients

### **Frontend (HTML + JavaScript)**
- **File:** `core/dashboard/templates/realtime_dashboard.html`
- **Features:**
  - Real-time price updates
  - Strategy display
  - Prediction visualization
  - Performance metrics
  - Activity logs

---

## ⚙️ CONFIGURATION

### **TradingConfig** (`config/config.py`)
- **Strategy Configs:** Per-strategy parameters (position_size, risk_reward_min, etc.)
- **Risk Management:** MAX_POSITION_SIZE, MIN_PROFIT_TARGET, MAX_STOP_LOSS
- **S/R Configuration:** Level selection, scoring weights, proximity decay
- **ATR Multipliers:** Distance thresholds for various operations

### **Environment Variables**
- `SYMBOL`: Trading symbol (default: BTC)
- `LEVERAGE`: Trading leverage (default: 40)
- `DEFAULT_INITIAL_BALANCE`: Starting balance (default: 120.0)
- `DEFAULT_CHECK_INTERVAL`: Loop interval in seconds (default: 5)

---

## 🚨 ERROR HANDLING

### **NO FALLBACKS Policy**
- **Principle:** Fail fast with clear errors
- **Implementation:** Direct dict access, raises KeyError/ValueError
- **Rationale:** Prevents silent data corruption

### **Error Propagation**
- Critical errors propagate and stop the bot
- Non-critical errors logged but don't stop execution
- Callback errors tracked and failing callbacks removed

### **Logging Levels**
- **ERROR:** All errors (propagate or handle)
- **WARNING:** Important anomalies
- **INFO:** Critical state changes
- **DEBUG:** Detailed debugging (disabled in production)

---

## 🔍 KEY ALGORITHMS

### **Direction Scoring**
- Weighted combination of 8 factors
- Strategy-specific weights
- Multi-timeframe trend analysis
- Score difference threshold

### **Entry Setup Generation**
- 4 entry candidates per S/R level
- ATR-based offsets (0.0, 0.3, 0.5, 1.0×ATR)
- Multi-factor scoring (strength, quality, fill probability)
- Best setup selection

### **Stop Loss Calculation**
- Finds strongest opposite S/R level
- Applies round number avoidance ($75-$150 offsets)
- Applies risk constraint (max % from entry)
- Selects best stop (S/R vs risk constraint)

### **Position Sizing**
- Base size from strategy config
- R:R multiplier (0.5x - 1.5x)
- Liquidation safety factor (0.3x - 1.0x)
- Confidence multiplier (1.0x placeholder)
- Final: balance × base_pct × multipliers × leverage / entry_price

---

## 📈 PERFORMANCE CHARACTERISTICS

### **Loop Frequency**
- **Main Loop:** Every 5 seconds (configurable)
- **Candle Updates:** Every 5 minutes (at boundaries)
- **WebSocket Updates:** Real-time (as data arrives)

### **Caching Strategy**
- **Price:** 5 seconds TTL
- **RSI, Volatility, Trend:** 60 seconds TTL
- **S/R Levels:** 180 seconds TTL (3 minutes)
- **Patterns:** 300 seconds TTL (5 minutes, matches candle timeframe)
- **External APIs:** 300-600 seconds TTL (5-10 minutes)

### **Database Operations**
- **Reads:** Fast (indexed queries)
- **Writes:** Atomic transactions (batch inserts)
- **Concurrency:** WAL mode enables concurrent reads

---

## 🎯 CURRENT STATUS

### **✅ Implemented**
- Real-time data fetching and analysis
- Strategy detection and selection
- Prediction generation (direction, entry, stop, target)
- Position sizing (R:R and liquidation-based)
- Dashboard with real-time updates
- Paper trading simulation

### **🚧 Placeholder (Ready for Implementation)**
- **Confidence Calculation:** Method exists, returns None
- **Confidence-Based Position Sizing:** Parameter accepted, multiplier = 1.0

### **❌ Not Implemented**
- Automatic order placement for predictions (limit orders)
- Position exit monitoring in main loop (SL/TP auto-close)
- Real API integration (paper trading only)

---

## 🔗 COMPONENT INTERACTIONS

### **Initialization Sequence**
```
main.py
  → SystemInitializer.initialize_system()
    → Initialize APIs
    → Initialize Services
    → Register Analysis Modules
  → SessionManager.start_session()
  → SessionOrchestrator.run_paper_trading_session()
    → Start Dashboard
    → _main_data_loop()
```

### **Data Flow Sequence (Per Iteration)**
```
SessionOrchestrator._main_data_loop()
  → RawDataFetcher.fetch_all_raw_data() [Parallel]
  → MarketDataService.get_unified_analysis_data()
    → Trigger analysis modules [Sequential]
    → Assemble unified data
  → StrategyManager.detect_optimal_strategy()
  → SRLevelFilter.filter_levels_for_strategy()
  → PredictionEngine.generate_prediction()
  → PositionSizeCalculator.calculate_position_size()
  → DashboardUpdater.update_dashboard_with_unified_data()
```

---

## 📝 KEY DESIGN DECISIONS

### **1. Strategy-Independent Analysis**
- **Decision:** Analysis done before strategy detection
- **Rationale:** Prevents circular dependencies
- **Benefit:** Clean separation, easier to test

### **2. Sequential Prediction Flow**
- **Decision:** Direction → Entry → Stop/Target (in order)
- **Rationale:** Clear logic, easier to debug
- **Benefit:** Predictable behavior

### **3. NO FALLBACKS Policy**
- **Decision:** All data required, fail fast if missing
- **Rationale:** Prevents silent data corruption
- **Benefit:** Reliable, debuggable system

### **4. Centralized Caching**
- **Decision:** Single cache system with TTL policies
- **Rationale:** Prevents redundant calculations
- **Benefit:** Performance optimization, consistency

### **5. Dependency Injection**
- **Decision:** Pass dependencies as parameters
- **Rationale:** Testable, maintainable
- **Benefit:** SOLID compliance, easier testing

---

## 🎓 FOR AI-TO-AI COMMUNICATION

### **Key Concepts to Understand:**

1. **NO FALLBACKS:** System never uses default values - data must be present or error is raised
2. **Strategy-Independent Analysis:** Analysis modules don't know about trading strategies
3. **Sequential Decision Flow:** Direction → Entry → Stop/Target (strict order)
4. **Parallel Data Fetching:** All APIs called in parallel, then analysis is sequential
5. **TTL-Based Caching:** Modules cached with time-to-live, invalidated on data changes
6. **Thread Safety:** Core is single-threaded, WebSocket/Dashboard are multi-threaded
7. **Atomic Transactions:** Database operations are atomic (all-or-nothing)

### **Critical Paths:**
- **Price Updates:** WebSocket → Cache → Callbacks → RSI → Dashboard
- **Candle Boundaries:** Detection → Database Update → Cache Invalidation → RSI Recalc
- **Prediction Generation:** Raw Data → Analysis → Strategy → S/R Filter → Prediction

### **Data Dependencies:**
- **Prediction needs:** All analysis data (rsi, trend, volatility, volume, pressure, s/r, patterns, market_conditions)
- **Strategy needs:** Volatility, trend, volume, RSI, pressure, patterns (NOT S/R)
- **S/R Filter needs:** Strategy config (max_levels, max_distance, min_distance)

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-27  
**Status:** Complete workflow documentation for AI-to-AI communication
