# Analysis Architecture

## Overview

The analysis system is clearly separated into **Real-Time** and **Historical** analysis modules, each with distinct purposes and data sources.

## Directory Structure

```
core/analysis/
├── __init__.py                    # Main analysis package
├── real_time/                     # REAL-TIME ANALYSIS
│   ├── __init__.py               # Real-time module definitions
│   ├── orderbook_analyzer.py     # Live orderbook analysis
│   └── volatility_calculator.py  # Real-time volatility calculations
└── historical/                    # HISTORICAL ANALYSIS
    ├── __init__.py               # Historical module definitions
    ├── market_data_analyzer.py   # Historical market data analysis
    └── market_volatility_analyzer.py # Historical volatility analysis
```

## Real-Time Analysis (`core/analysis/real_time/`)

**Purpose**: Instant analysis for live trading decisions using current market data.

### Modules:

#### 1. `orderbook_analyzer.py`
- **Data Source**: Live orderbook data from Hyperliquid API
- **Analysis Types**:
  - Volume analysis (order book depth)
  - Volatility analysis (spread and depth volatility)
  - Pressure analysis (buy/sell pressure from order book)
- **Use Case**: Real-time trading decisions, instant market assessment

#### 2. `volatility_calculator.py`
- **Data Source**: Live market data, orderbook data
- **Analysis Types**:
  - Candle-based volatility (from live candles)
  - Orderbook volatility (delegates to orderbook analyzer)
  - Price acceleration
  - Momentum volatility
- **Use Case**: Real-time volatility assessment for risk management

### Data Sources:
- **Hyperliquid API**: Live orderbook, real-time prices
- **WebSocket feeds**: Ultra-low latency price updates
- **Live market data**: Current bid/ask spreads, depth

## Historical Analysis (`core/analysis/historical/`)

**Purpose**: Analysis of historical data for trend identification and backtesting.

### Modules:

#### 1. `market_data_analyzer.py`
- **Data Source**: Hyperliquid historical data
- **Analysis Types**:
  - RSI calculations
  - Historical market analysis
  - Price trend analysis
- **Use Case**: Technical analysis, trend identification, backtesting

#### 2. `market_volatility_analyzer.py`
- **Data Source**: Historical candlestick data
- **Analysis Types**:
  - Historical volatility patterns
  - Market variability analysis
  - Long-term volatility trends
- **Use Case**: Historical pattern recognition, volatility forecasting

### Data Sources:
- **Yahoo Finance**: Historical candlestick data
- **Historical databases**: Stored market data
- **Backtest data**: Simulated historical scenarios

## Key Differences

| Aspect | Real-Time Analysis | Historical Analysis |
|--------|-------------------|-------------------|
| **Data Source** | Live APIs, WebSockets | Historical databases, Yahoo Finance |
| **Latency** | Milliseconds | Minutes to hours |
| **Purpose** | Live trading decisions | Trend analysis, backtesting |
| **Update Frequency** | Continuous | Periodic (1min-1hour) |
| **Accuracy** | Current market state | Historical patterns |

## Usage Examples

### Real-Time Analysis
```python
from core.analysis.real_time import MarketOrderbookAnalyzer, VolatilityCalculator

# Live orderbook analysis
analyzer = MarketOrderbookAnalyzer(api_instance)
volume_analysis = analyzer.get_volume_analysis()
volatility_analysis = analyzer.get_volatility_analysis()

# Real-time volatility
vol_calc = VolatilityCalculator()
live_volatility = vol_calc.calculate_orderbook_volatility(orderbook_data)
```

### Historical Analysis
```python
from core.analysis.historical import MarketDataAnalyzer, VariabilityAnalyzer

# Historical RSI analysis
hist_analyzer = MarketDataAnalyzer()
rsi_data = hist_analyzer.get_optimized_rsi_data(hyperliquid_price)

# Historical volatility patterns
var_analyzer = VariabilityAnalyzer()
historical_volatility = var_analyzer.analyze_historical_volatility(candles)
```

## Integration

The two analysis types work together:
- **Historical analysis** provides context and patterns
- **Real-time analysis** provides current market state
- **Combined** they enable informed trading decisions

## Benefits of This Architecture

1. **Clear Separation**: No confusion about data sources or purposes
2. **Maintainability**: Each module has a single responsibility
3. **Performance**: Real-time modules optimized for speed
4. **Flexibility**: Can use either or both analysis types
5. **Scalability**: Easy to add new analysis modules to either category
