# HyperLBot - Advanced Hybrid Trading Bot

A sophisticated cryptocurrency trading bot that combines Binance candlestick analysis with Hyperliquid execution for optimal trading performance.

## 🚀 Features

- **Hybrid Analysis**: Combines Binance candlestick data with Hyperliquid market execution
- **Advanced Strategy**: Multi-timeframe analysis with variability theory optimization
- **Paper Trading**: Safe testing environment with realistic simulation
- **Comprehensive Logging**: Detailed trade analysis and performance tracking
- **Fee Management**: Smart fee calculation and profitability analysis
- **Risk Management**: Built-in position sizing and stop-loss mechanisms
- **Weekly Trend Context**: Incorporates broader market trends for better decisions

## 📋 Prerequisites

- Python 3.8 or higher
- Hyperliquid account with wallet credentials
- Internet connection for API access

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Georg1992/HyperLBot.git
   cd HyperLBot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp env_example.txt .env
   ```
   
   Edit `.env` file with your credentials:
   ```env
   WALLET_ADDRESS=your_wallet_address_here
   WALLET_PRIVATE_KEY=your_private_key_here
   SYMBOL=BTC
   LEVERAGE=30
   LOG_LEVEL=INFO
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WALLET_ADDRESS` | Your Hyperliquid wallet address | Required |
| `WALLET_PRIVATE_KEY` | Your wallet private key | Required |
| `SYMBOL` | Trading symbol | BTC |
| `LEVERAGE` | Default leverage | 30 |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FILE` | Log file name | trading.log |

### Trading Parameters

The bot uses sophisticated parameters that adapt to market conditions:

- **Position Sizing**: Dynamic based on volatility and variability analysis
- **Leverage**: 20x-40x (respects Hyperliquid limits)
- **Profit Targets**: 0.3%-0.5% depending on market conditions
- **Stop Losses**: 0.15%-0.25% with risk management

## 🎯 Usage

### Quick Start

Run the main interface:
```bash
python main.py
```

This provides a menu-driven interface to:
1. Run Hybrid Paper Trading Bot
2. Test External Data Fetcher
3. Test Fee Manager
4. Test Variability Analyzer
5. Test Trading Logger

### Running Individual Components

#### Paper Trading Bot
```python
from strategies.hybrid_paper_trading_bot import HybridPaperTradingBot

bot = HybridPaperTradingBot(initial_balance=120.0)
if bot.connect():
    bot.run_hybrid_paper_trading(max_trades=5, check_interval=30)
```

#### Market Analysis
```python
from data.external_data_fetcher import ExternalDataFetcher

fetcher = ExternalDataFetcher()
analysis = fetcher.get_market_analysis("BTCUSDT")
```

#### Fee Analysis
```python
from strategies.fee_manager import FeeManager

fee_manager = FeeManager()
fees = fee_manager.calculate_order_fees(0.001, 50000, "LIMIT")
```

## 📊 Strategy Overview

### Hybrid Analysis Approach

1. **Binance Data**: Fetches candlestick data for technical analysis
2. **Hyperliquid Execution**: Uses real market data for execution prices
3. **Multi-timeframe**: Combines 5-minute and 1-hour analysis
4. **Weekly Context**: Incorporates broader market trends

### Trading Logic

- **Breakout Strategy**: Trades breakouts above resistance/below support
- **Mean Reversion**: Trades reversions from support/resistance levels
- **1-Hour Confirmation**: Requires 1-hour trend alignment
- **Weekly Context**: Avoids trades against strong weekly trends

### Risk Management

- **Dynamic Position Sizing**: Based on market volatility
- **Fee-Aware Trading**: Only trades profitable after fees
- **Stop Losses**: Automatic position management
- **Time-Based Exits**: Maximum 1-hour holding time

## 📈 Performance Tracking

The bot includes comprehensive logging and analysis:

- **Trade Logs**: Complete trade history with entry/exit details
- **Performance Metrics**: Win rate, profit factor, drawdown analysis
- **Strategy Insights**: Best/worst performing conditions
- **Fee Analysis**: Impact of fees on profitability
- **CSV Export**: Data export for external analysis

## 🔍 Project Structure

```
HyperLBot/
├── main.py                          # Main entry point
├── requirements.txt                 # Python dependencies
├── env_example.txt                  # Environment template
├── README.md                        # This file
├── core/                           # Core functionality
│   ├── __init__.py
│   ├── config.py                   # Configuration management
│   ├── hyperliquid_api.py          # Hyperliquid API client
│   └── trading_logger.py           # Comprehensive logging
├── data/                           # Data handling
│   ├── __init__.py
│   └── external_data_fetcher.py    # Binance data fetcher
├── strategies/                     # Trading strategies
│   ├── __init__.py
│   ├── hybrid_paper_trading_bot.py # Main trading bot
│   ├── fee_manager.py              # Fee calculations
│   └── variability_analyzer.py     # Market variability analysis
└── docs/                          # Documentation
    └── README.md                   # Legacy documentation
```

## ⚠️ Important Warnings

### Risk Disclaimer

- **Cryptocurrency trading involves substantial risk of loss**
- **Only trade with money you can afford to lose**
- **Test thoroughly with paper trading before live trading**
- **Monitor your positions regularly**
- **Keep your wallet credentials secure**

### Security Notes

- Never share your private keys
- Use environment variables for sensitive data
- Regularly update dependencies
- Monitor for suspicious activity

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **API Connection**: Check internet connection and API credentials
3. **Wallet Issues**: Verify wallet address and private key format
4. **Permission Errors**: Ensure write permissions for log directories

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=DEBUG` in your `.env` file.

## 📝 Logging

The bot creates detailed logs in the following structure:

```
trading_logs/
├── trades/          # Trade records
├── market_data/     # Market data points
├── signals/         # Trading signals
├── analysis/        # Technical analysis
├── performance/     # Performance metrics
├── errors/          # Error logs
└── csv_exports/     # CSV data exports
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is for educational purposes. Use at your own risk.

## 🔗 Links

- [Hyperliquid](https://app.hyperliquid.xyz/)
- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)
- [Python Documentation](https://docs.python.org/)

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error details
3. Create an issue on GitHub

---

**Remember**: This is educational software. Always test thoroughly and trade responsibly!
