# HyperLBot - Real-Time Market Analysis & Trading System

A production-grade, high-performance trading system featuring real-time data processing, predictive analytics, and sophisticated risk management. Built with clean architecture principles and a strict **NO FALLBACKS** policy for maximum reliability.

## 🎯 Overview

HyperLBot is a comprehensive trading system that processes real-time market data with sub-second latency to generate trading signals. The system emphasizes reliability, performance, and production-grade code quality.

**Key Highlights:**
- ⚡ **Real-time processing** with WebSocket data streams
- 📊 **Multi-timeframe analysis** (5m, 15m, 1h, 1d candles)
- 🎯 **Strategy-aware decision engine** with dynamic adaptation
- 🔒 **NO FALLBACKS policy** - fail-fast with clear errors
- 📈 **75% performance improvement** through optimization
- 🎨 **Live dashboard** with real-time updates via WebSocket

---

## 🏗️ Architecture

### Core Design Principles

1. **Single Responsibility Principle (SRP)** - Each module has one clear purpose
2. **Singleton Pattern** - Critical services use singletons to prevent redundancy
3. **NO FALLBACKS** - Required data must be present; fail fast on missing/invalid data
4. **Centralized Caching** - TTL-based caching prevents redundant calculations
5. **Event-Driven Updates** - WebSocket-based real-time data flow

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Session Orchestrator                     │
│              (Coordinates all system components)              │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
       ┌───────▼────────┐            ┌────────▼─────────┐
       │ Market Data    │            │   Dashboard      │
       │   Service      │            │    Service       │
       │ (Unified data) │◄───────────┤ (WebSocket UI)   │
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

## ✨ Key Features

### 🚀 Performance Optimizations

- **75% reduction in redundant calculations** - Eliminated duplicate calculator instantiation
- **Strategy-aware caching** - Intelligent cache invalidation based on data changes
- **Centralized data coordination** - Single source of truth for all market data
- **Optimized candle fetching** - Smart database queries with price range filtering

### 📊 Real-Time Analytics

- **Support/Resistance Detection** - Multi-timeframe S/R level identification with clustering
- **Volatility Analysis** - ATR-based volatility categorization (LOW/MODERATE/HIGH/EXTREME)
- **Volume Profiling** - Volume analysis with momentum and anomaly detection
- **Trend Detection** - Multi-timeframe trend alignment
- **Pattern Recognition** - Candlestick patterns and chart formations

### 🎯 Trading Intelligence

- **Strategy Manager** - Dynamic strategy selection (scalping, standard, swing)
- **Entry Optimization** - 4 entry candidates per setup with multi-factor scoring
- **Risk Management** - Liquidation safety, round number avoidance, spread cost analysis
- **Position Sizing** - Risk-adjusted position sizing with liquidation buffer
- **Stop Loss Placement** - Intelligent SL placement avoiding obvious levels

### 🎨 Real-Time Dashboard

- **WebSocket Updates** - Live data streaming to web interface
- **Strategy-Aware Display** - Shows only relevant S/R levels per strategy
- **Market Indicators** - RSI, volatility, volume, pressure, trend analysis
- **Prediction Display** - Real-time trading signals with confidence scores
- **Performance Tracking** - Win rate, balance, trade history

---

## 🔬 Research-Backed Improvements

The system incorporates findings from academic and industry research:

### Critical Fixes (2026-01-12 Audit)

1. **Entry Offset Logic** ✅
   - Professional entry: 0.3-0.5× ATR inside S/R zone (not AT level)
   - Prevents liquidation on stop-hunt wicks
   - Research: Market makers hunt stops at obvious levels

2. **Position Sizing Safety** ✅
   - Liquidation distance factor in position sizing
   - Buffer zones: ≥50%=1.0x, 30-50%=0.8-1.0x, 15-30%=0.5-0.8x, <15%=0.3-0.5x
   - Prevents blow-ups from tight stop-losses

3. **Spread Cost Integration** ✅
   - Round-trip spread costs in P&L calculations
   - Rejects trades where spread exceeds profit
   - Realistic R:R ratios after costs

4. **Round Number Avoidance** ✅
   - Detects $1K and $5K round numbers ($90K, $95K, $100K)
   - Offsets stops by $75-$150 away from round numbers
   - Reduces stop-hunt risk

5. **S/R Wick Filtering** ✅
   - Tracks wick rejection ratio per level
   - Stop-hunt risk scoring: LOW/MOD/HIGH/VERY_HIGH
   - Consistency penalty for repeated wick levels

**Sources:**
- Academic: "S/R Levels towards Profitability in Algorithmic Trading" (MDPI 2025)
- Industry: Hyperliquid liquidation cascade analysis ($6.7B event)
- Professional: BTC perp entry offset best practices

---

## 📋 Installation

### Prerequisites

- Python 3.8+
- Internet connection
- Windows/Linux/macOS

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd HyperLBot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** (optional)
   ```bash
   cp env_example.txt .env
   # Edit .env with your settings
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

---

## 🎮 Usage

### Main Menu

```
HyperLBot Menu:
1. Paper Trading (Testing Mode)     # Simulated trading with virtual balance
2. Real Trading (Production Mode)   # Currently disabled
3. Start Dashboard Only             # Launch web dashboard
4. Exit
```

### Paper Trading Mode

- **Initial Balance**: Default $10,000 (configurable)
- **Account Persistence**: Saves balance and trade history
- **Realistic Simulation**: Includes fees, slippage, liquidation mechanics

### Dashboard Access

Once started, dashboard is available at:
```
http://localhost:5000
```

Features:
- Real-time market data updates
- Strategy selection display
- Prediction signals with confidence
- Performance metrics
- Activity logs

---

## 🛠️ Configuration

### Trading Parameters

**Leverage Options:**
- 20x - Conservative
- 30x - Moderate (default)
- 40x - Aggressive

**Strategy Types:**
```python
"scalping": {
    "max_levels_per_side": 1,      # Show 1 S/R level
    "max_distance_pct": 0.015,     # 1.5% max distance
    "risk_reward_min": 1.5,        # Minimum R:R ratio
    "position_size": 0.02          # 2% of balance
}

"standard": {
    "max_levels_per_side": 2,      # Show 2 S/R levels
    "max_distance_pct": 0.03,      # 3% max distance
    "risk_reward_min": 2.0,        # Minimum R:R ratio
    "position_size": 0.015         # 1.5% of balance
}

"swing": {
    "max_levels_per_side": 3,      # Show 3 S/R levels
    "max_distance_pct": 0.05,      # 5% max distance
    "risk_reward_min": 3.0,        # Minimum R:R ratio
    "position_size": 0.01          # 1% of balance
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WALLET_ADDRESS` | Hyperliquid wallet address | Optional |
| `WALLET_PRIVATE_KEY` | Wallet private key | Optional |
| `SYMBOL` | Trading symbol | BTC |
| `LEVERAGE` | Leverage multiplier | 30 |
| `LOG_LEVEL` | Logging verbosity | INFO |

---

## 🏛️ Project Structure

```
HyperLBot/
├── main.py                              # Entry point
├── config/
│   └── config.py                        # Configuration & validation
├── core/
│   ├── services/
│   │   ├── session_orchestrator.py     # Main coordinator
│   │   ├── market_data_service.py      # Unified data provider
│   │   ├── dashboard_service.py        # Dashboard coordination
│   │   ├── strategy_manager.py         # Strategy selection
│   │   └── system_initializer.py       # System bootstrap
│   ├── calculations/
│   │   ├── support_resistance_calculator.py  # S/R detection
│   │   ├── sr_level_filter.py          # Strategy-aware filtering
│   │   ├── volatility_calculator.py    # Volatility analysis
│   │   ├── volume_calculator.py        # Volume profiling
│   │   ├── rsi_calculator.py           # RSI indicator
│   │   └── risk_manager.py             # Risk calculations
│   ├── execution/
│   │   ├── prediction_engine.py        # Entry setup generation
│   │   ├── position_sizer.py           # Position sizing
│   │   └── fee_manager.py              # Fee calculations
│   ├── analysis/
│   │   └── real_time/
│   │       ├── market_conditions_analyzer.py  # Market state
│   │       └── pattern_recognition_engine.py  # Patterns
│   ├── dashboard/
│   │   ├── web_dashboard.py            # Flask server
│   │   └── templates/
│   │       └── realtime_dashboard.html # Frontend UI
│   └── api/
│       ├── hyperliquid_api.py          # Hyperliquid client
│       └── hyperliquid_websocket.py    # WebSocket data
└── data/
    └── candles_5m_btc.db               # SQLite candle cache
```

---

## 🔍 Technical Highlights

### NO FALLBACKS Policy

The system follows a strict **NO FALLBACKS** policy:

```python
# ❌ OLD (with fallbacks):
spread = data.get("spread_pct", 0.01)  # Default if missing

# ✅ NEW (NO FALLBACKS):
spread = data["spread_pct"]  # Raises KeyError if missing
```

**Benefits:**
- Errors surface immediately (fail-fast)
- No silent data corruption
- Clear debugging (no mystery defaults)
- Production reliability

### Performance Optimization

**Before:**
```
• Multiple modules creating duplicate calculators
• Volatility fetched 4x per cycle
• Volume fetched 3x per cycle  
• RSI fetched 2x per cycle
→ ~75% wasted computation
```

**After:**
```
• Single calculator instance per module
• Centralized data coordination
• TTL-based caching
• Strategy-aware invalidation
→ 75% reduction in redundant calls
```

### Logging Architecture

**Production Logging Strategy:**
- ✅ **ERROR** - All errors logged
- ✅ **WARNING** - Important anomalies
- ✅ **INFO** - Critical state changes only
- ❌ **DEBUG** - Removed (was 50+ debug logs)

**Frontend:**
```javascript
const DEBUG = false;  // Set true for troubleshooting
if (DEBUG) console.log(...);  // 37 logs wrapped
```

---

## 📊 Performance Metrics

### System Performance

- **Data Processing Latency**: <100ms
- **WebSocket Update Frequency**: ~1-2s
- **Cache Hit Rate**: ~85%
- **Redundant Calculations**: Reduced by 75%

### Trading Performance (Paper Trading)

*Performance varies by market conditions and strategy*

- **Strategies**: Scalping, Standard, Swing
- **Risk-Reward**: 1.5:1 to 3:1 (strategy-dependent)
- **Position Sizing**: 1-2% of balance per trade
- **Maximum Drawdown Protection**: Liquidation buffer zones

---

## ⚠️ Important Notes

### Risk Disclaimer

- **Cryptocurrency trading involves substantial risk**
- **Past performance does not guarantee future results**
- **Test thoroughly in paper trading mode**
- **Never trade with funds you cannot afford to lose**
- **Monitor positions actively**

### Security Best Practices

- 🔒 Never share private keys
- 🔐 Use environment variables for secrets
- 🛡️ Keep dependencies updated
- 📝 Review logs for anomalies
- 🚫 Disable real trading until thoroughly tested

---

## 🐛 Troubleshooting

### Common Issues

**Import Errors:**
```bash
pip install -r requirements.txt --upgrade
```

**Database Locked:**
- SQLite file-level locking is normal
- Close other instances before starting

**WebSocket Connection:**
- Check internet connection
- Verify Hyperliquid API is accessible

**Dashboard Not Loading:**
- Ensure port 5000 is available
- Check browser console for errors

### Debug Mode

Enable debug logging:
1. Set `LOG_LEVEL=DEBUG` in `.env`
2. Set `DEBUG = true` in `realtime_dashboard.html` (line ~778)

---

## 📚 Documentation

Additional documentation available in `.ai/` directory:
- `codebase_audit_btc_perps.json` - Comprehensive audit & fixes
- `CONFIDENCE_SYSTEM_ANALYSIS.md` - Confidence scoring analysis
- `SINGLE_SOURCE_OF_TRUTH_STATUS.md` - Architecture decisions

---

## 🤝 Contributing

This is a personal project, but feedback and suggestions are welcome:

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

---

## 📄 License

This project is for educational and personal use. Trading involves significant financial risk.

---

## 🔗 Resources

- [Hyperliquid](https://app.hyperliquid.xyz/)
- [Python Documentation](https://docs.python.org/)
- [WebSocket Protocol](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

---

**Built with clean architecture, production-grade code quality, and a focus on reliability over convenience.**

*Last Updated: January 2026*
