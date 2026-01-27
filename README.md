# HyperLBot

Algorithmic trading system for Hyperliquid perpetual futures with real-time market analysis and multi-strategy execution.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Architecture](#architecture)
- [Documentation](#documentation)

---

## Features

### Core Functionality

- **Real-Time Data Processing** - WebSocket-based market data streams
- **Multi-Strategy Engine** - 9 trading strategies with dynamic selection
- **Support/Resistance Detection** - Multi-timeframe S/R identification with psychological levels
- **Candle Database** - SQLite storage with rolling 5-year window
- **Risk Management** - Liquidation safety scoring and position sizing for 40x leverage
- **Live Dashboard** - WebSocket dashboard with real-time market indicators
- **Paper Trading** - Simulation with fees, slippage, and liquidation mechanics

### Technical Implementation

- **NO FALLBACKS Policy** - Fail-fast error handling
- **Centralized Caching** - TTL-based cache with strategy-aware invalidation
- **Deterministic Calculations** - Epsilon-based float comparisons for reproducibility
- **Modular Architecture** - SOLID principles, singleton patterns

---

## Installation

### Prerequisites

- Python 3.8+
- Internet connection

### Setup

```bash
# Clone repository
git clone <repository-url>
cd HyperLBot

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SYMBOL` | Trading symbol | `BTC` |
| `LEVERAGE` | Leverage multiplier | `40` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `WALLET_ADDRESS` | Hyperliquid wallet | - |
| `WALLET_PRIVATE_KEY` | Wallet private key | - |

### Strategy Configuration

Strategies configured in `config/config.py`:

- `max_levels_per_side` - Number of S/R levels
- `max_distance_pct` - Maximum distance from current price
- `risk_reward_min` - Minimum R:R ratio
- `position_size` - Position size percentage
- `confidence_threshold` - Minimum confidence to execute

**Available Strategies:**
- `scalping` - 1.5:1 R:R
- `standard` - 2.0:1 R:R
- `trend_following` - 2.0:1 R:R
- `breakout` - 2.0:1 R:R
- `range_trading` - 1.2:1 R:R
- `low_volatility_range` - 1.2:1 R:R
- `high_volatility` - 2.0:1 R:R
- `spike_hunting` - 2.5:1 R:R

---

## Usage

### Paper Trading

```bash
python main.py
# Select: 1. Paper Trading
```

- Default balance: $120
- Includes fees, slippage, liquidation mechanics
- Trade history persisted

### Dashboard

```bash
python main.py
# Select: 3. Start Dashboard Only
```

Access at `http://localhost:5002`

- Real-time market data
- Strategy selection
- Trading signals
- Performance metrics

---

## Architecture

### System Design

```
┌─────────────────────────────────────────┐
│      Session Orchestrator               │
│   (Coordinates all components)          │
└──────────┬──────────────────┬───────────┘
           │                  │
    ┌──────▼──────┐    ┌──────▼──────┐
    │ Market Data │    │  Dashboard  │
    │   Service   │    │   Service   │
    └──────┬──────┘    └─────────────┘
           │
    ┌──────▼──────────────┐
    │  Candle Storage     │◄───┐
    │  (SQLite Database)  │    │ (writes)
    │  Rolling 5-Year    │    │
    └──────┬──────────────┘    │
           │ (reads)            │
    ┌──────▼──────────────────────┐
    │   Analysis Modules          │
    │  (RSI, Volatility, S/R,     │
    │   Volume, Trends, Patterns)  │
    └──────┬──────────────────────┘
           │
    ┌──────▼──────┐
    │ Prediction  │
    │   Engine    │
    └─────────────┘
```

### Components

- **Session Orchestrator** - Coordinates system components
- **Market Data Service** - Unified data provider with caching
- **Candle Storage** - SQLite database with rolling 5-year window
- **Strategy Manager** - Dynamic strategy selection with tie-breaking
- **Prediction Engine** - Entry setup generation with multi-factor scoring
- **Position Sizer** - Risk-adjusted position sizing
- **Dashboard Service** - WebSocket-based UI

### Candle Database

SQLite storage for 5-minute candles:

- Rolling 5-year window (~525,600 candles)
- Auto-cleanup of data older than 5 years
- Startup backfill of missing candles
- Continuous updates every 5 minutes
- Aggregates to 15m, 1h, 1d timeframes
- WAL mode for concurrent reads/writes

Used for:
- S/R level detection (5 years historical)
- Volume percentile calculations (7-day window)
- Trend analysis
- Reduces API dependency

### Design Principles

1. **NO FALLBACKS** - Required data must be present; fail fast on errors
2. **Single Responsibility** - Each module has one clear purpose
3. **Centralized Caching** - TTL-based caching prevents redundant calculations
4. **Event-Driven** - WebSocket-based real-time data flow
5. **Deterministic** - All calculations are reproducible

---

## Documentation

- **[Architecture & Workflow](BOT_WORKFLOW_AND_ARCHITECTURE.md)** - System architecture and data flow
- **[ML Integration Evaluation](ML_INTEGRATION_EVALUATION.md)** - ML readiness assessment
- **[ML Readiness Summary](ML_READINESS_SUMMARY.md)** - ML integration status
- **[Strategy Tie-Breaking](STRATEGY_TIE_BREAKING_FIX.md)** - Implementation details
- **[Config & Dead Code Audit](CONFIG_AND_DEAD_CODE_AUDIT.md)** - Code quality report

Reference documentation in `.ai/` directory.

---

## License

Educational and personal use only. Trading involves financial risk.
