# HyperLBot

> Production-grade algorithmic trading system for cryptocurrency perpetual futures with real-time market analysis, multi-strategy execution, and sophisticated risk management.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

HyperLBot is a high-performance trading system designed for Hyperliquid perpetual futures. It processes real-time market data with sub-second latency to generate trading signals using multi-timeframe analysis, support/resistance detection, and dynamic strategy selection.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Performance](#performance)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Core Capabilities

- **Real-Time Analysis** - WebSocket-based data streams with <100ms processing latency
- **Multi-Strategy Engine** - 9 trading strategies with dynamic selection and explicit tie-breaking
- **Advanced S/R Detection** - Multi-timeframe support/resistance identification with psychological levels
- **Candle Database** - SQLite database with rolling 5-year window for efficient historical analysis
- **Risk Management** - Liquidation safety scoring, position sizing, and stop-loss optimization for 40x leverage
- **Live Dashboard** - Real-time WebSocket dashboard with market indicators and trade signals
- **Paper Trading** - Realistic simulation with fees, slippage, and liquidation mechanics

### Technical Highlights

- **NO FALLBACKS Policy** - Fail-fast design ensures data integrity and production reliability
- **75% Performance Improvement** - Optimized caching and centralized data coordination
- **Deterministic Calculations** - Epsilon-based comparisons for ML-ready reproducibility
- **Clean Architecture** - SOLID principles, singleton patterns, and modular design
- **Rolling Window Database** - Automatic cleanup maintains 5-year historical window for optimal performance

---

## Quick Start

```bash
# Clone repository
git clone <repository-url>
cd HyperLBot

# Install dependencies
pip install -r requirements.txt

# Run paper trading
python main.py
# Select option 1: Paper Trading

# Access dashboard
# Open http://localhost:5002 in your browser
```

**That's it!** The bot will start analyzing market data and generating trading signals.

---

## Installation

### Prerequisites

- Python 3.8 or higher
- Internet connection for market data
- Windows, Linux, or macOS

### Step-by-Step Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd HyperLBot
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment** (optional)
   ```bash
   cp env_example.txt .env
   # Edit .env with your settings
   ```

5. **Verify installation**
   ```bash
   python main.py
   ```

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SYMBOL` | Trading symbol | `BTC` | No |
| `LEVERAGE` | Leverage multiplier | `40` | No |
| `LOG_LEVEL` | Logging verbosity | `INFO` | No |
| `WALLET_ADDRESS` | Hyperliquid wallet | - | For live trading |
| `WALLET_PRIVATE_KEY` | Wallet private key | - | For live trading |

### Strategy Configuration

Strategies are configured in `config/config.py`. Each strategy includes:

- `max_levels_per_side` - Number of S/R levels to consider
- `max_distance_pct` - Maximum distance from current price
- `risk_reward_min` - Minimum risk:reward ratio
- `position_size` - Position size as percentage of balance
- `confidence_threshold` - Minimum confidence to execute

**Available Strategies:**
- `scalping` - High-frequency, tight stops (1.5:1 R:R)
- `standard` - Balanced approach (2.0:1 R:R)
- `trend_following` - Momentum-based (2.0:1 R:R)
- `breakout` - Volatility plays (2.0:1 R:R)
- `range_trading` - Sideways markets (1.2:1 R:R)
- `low_volatility_range` - Tight ranges (1.2:1 R:R)
- `high_volatility` - Extreme moves (2.0:1 R:R)
- `spike_hunting` - Reversal plays (2.5:1 R:R)

See `config/config.py` for complete configuration options.

---

## Usage

### Paper Trading Mode

Paper trading simulates real trading with a virtual balance:

```bash
python main.py
# Select: 1. Paper Trading (Testing Mode)
```

**Features:**
- Default balance: $120 (configurable)
- Realistic fees and slippage
- Liquidation mechanics
- Trade history persistence

### Dashboard Mode

Launch the web dashboard for real-time monitoring:

```bash
python main.py
# Select: 3. Start Dashboard Only
```

**Dashboard URL:** `http://localhost:5002`

**Features:**
- Real-time market data
- Strategy selection display
- Trading signals with confidence scores
- Performance metrics
- Activity logs

### Real Trading

⚠️ **Currently disabled for safety.** Real trading requires:
- Valid wallet credentials
- Thorough testing in paper mode
- Understanding of risks

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
           │
    ┌──────▼──────────────┐
    │  Candle Storage     │
    │  (SQLite Database)  │
    │  Rolling 5-Year    │
    │  Window            │
    └─────────────────────┘
```

### Data Storage

**Candle Database** - SQLite-based persistent storage for 5-minute candles:

- **Rolling Window** - Automatically maintains 5-year historical window (~525,600 candles)
- **Auto-Cleanup** - Removes data older than 5 years to keep database size optimal
- **Startup Backfill** - Automatically fills missing candles on bot initialization
- **Continuous Updates** - Appends new candles every 5 minutes at candle boundaries
- **Fast Local Queries** - No API calls needed for historical data
- **Multi-Timeframe Support** - Aggregates 5m candles to 15m, 1h, and 1d timeframes
- **Thread-Safe** - WAL mode enables concurrent reads during writes

**Benefits:**
- Efficient S/R level detection using 5 years of historical data
- Fast volume percentile calculations (7-day rolling window)
- Reliable trend analysis with extensive historical context
- Reduced API dependency for historical analysis

### Key Components

- **Session Orchestrator** - Main coordinator for all system components
- **Market Data Service** - Unified data provider with caching
- **Candle Storage** - SQLite database with rolling 5-year window for historical analysis
- **Strategy Manager** - Dynamic strategy selection with tie-breaking
- **Prediction Engine** - Entry setup generation with multi-factor scoring
- **Position Sizer** - Risk-adjusted position sizing
- **Dashboard Service** - WebSocket-based real-time UI

### Design Principles

1. **NO FALLBACKS** - Required data must be present; fail fast on errors
2. **Single Responsibility** - Each module has one clear purpose
3. **Centralized Caching** - TTL-based caching prevents redundant calculations
4. **Event-Driven** - WebSocket-based real-time data flow
5. **Deterministic** - All calculations are reproducible for ML integration

For detailed architecture documentation, see [`BOT_WORKFLOW_AND_ARCHITECTURE.md`](BOT_WORKFLOW_AND_ARCHITECTURE.md).

---

## Documentation

### Essential Guides

- **[Architecture & Workflow](BOT_WORKFLOW_AND_ARCHITECTURE.md)** - Complete system architecture and data flow
- **[ML Integration Evaluation](ML_INTEGRATION_EVALUATION.md)** - Comprehensive ML readiness assessment
- **[ML Readiness Summary](ML_READINESS_SUMMARY.md)** - Quick reference for ML integration status

### Technical Documentation

- **[Strategy Tie-Breaking](STRATEGY_TIE_BREAKING_FIX.md)** - Implementation details
- **[Config & Dead Code Audit](CONFIG_AND_DEAD_CODE_AUDIT.md)** - Code quality report
- **[Dead Code Removal](DEAD_CODE_REMOVAL_COMPLETE.md)** - Cleanup summary

### Reference Documentation

See `.ai/` directory for:
- Architecture assumptions
- SOLID principles audit
- Performance analysis
- IV Squeeze analysis

---

## Performance

### System Metrics

- **Data Processing Latency**: <100ms
- **WebSocket Update Frequency**: 1-2 seconds
- **Cache Hit Rate**: ~85%
- **Redundant Calculations**: Reduced by 75%
- **Database Efficiency**: Rolling 5-year window keeps database size optimal (~525,600 candles)

### Trading Performance

*Performance varies by market conditions and strategy*

- **Strategies**: 9 strategies with dynamic selection
- **Risk-Reward**: 1.2:1 to 2.5:1 (strategy-dependent)
- **Position Sizing**: 1-2% of balance per trade
- **Leverage**: Optimized for 40x (configurable)

### Research-Backed Features

The system incorporates findings from:
- Academic research on S/R level profitability (MDPI 2025)
- Industry analysis of Hyperliquid liquidation cascades
- Professional BTC perpetual futures best practices

Key improvements:
- Entry offset logic (0.3-0.5× ATR inside S/R zone)
- Liquidation safety buffer zones
- Spread cost integration
- Psychological level integration
- S/R wick filtering

---

## Contributing

This is a personal project, but feedback and suggestions are welcome.

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Quality

- Follow PEP 8 style guidelines
- Maintain NO FALLBACKS policy
- Add tests for new features
- Update documentation

---

## License

This project is for educational and personal use. Trading involves significant financial risk.

**⚠️ Risk Disclaimer:**
- Cryptocurrency trading involves substantial risk
- Past performance does not guarantee future results
- Test thoroughly in paper trading mode
- Never trade with funds you cannot afford to lose
- Monitor positions actively

---

## Resources

- [Hyperliquid Exchange](https://app.hyperliquid.xyz/)
- [Hyperliquid Documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/)
- [Python Documentation](https://docs.python.org/)
- [WebSocket Protocol](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

---

## Recent Updates

**2026-01-27**
- ✅ ML integration evaluation completed
- ✅ Strategy selection tie-breaking implemented
- ✅ Determinism verification completed
- ✅ Dead code removal (609 lines)
- ✅ Config cleanup (all hardcoded values moved to config)

**Status:** System ready for ML-based confidence calculation integration.

---

**Built with clean architecture, production-grade code quality, and a focus on reliability over convenience.**
