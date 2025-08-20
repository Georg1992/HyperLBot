# HyperLBot - Simple Hyperliquid Trading Interface

A simple Python interface to connect to your Hyperliquid account and execute trades.

## Features

- **Connect to Hyperliquid**: Authenticate with your API credentials
- **Get Account Balance**: View your account information and balances
- **Get Market Prices**: Check current prices for any symbol
- **Place Market Orders**: Execute immediate trades at market price
- **Place Limit Orders**: Set orders at specific price levels
- **View Positions**: Check your current open positions
- **View Open Orders**: See your pending orders

## Installation

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
   copy env_example.txt .env
   ```
   
   Edit `.env` file with your Hyperliquid API credentials:
   ```
   API_KEY=your_hyperliquid_api_key_here
   API_SECRET=your_hyperliquid_api_secret_here
   ```

## Getting API Credentials

1. Go to [Hyperliquid](https://app.hyperliquid.xyz/)
2. Create an account and complete KYC
3. Navigate to API settings
4. Generate API key and secret
5. Add the credentials to your `.env` file

## Usage

Run the trading interface:
```bash
python main.py
```

The interface will present you with a menu to:
1. Get Account Balance
2. Get Market Price
3. Place Market Order
4. Place Limit Order
5. Get Positions
6. Get Open Orders
7. Exit

## Example Usage

```
Hyperliquid Trading Interface
==================================================
1. Get Account Balance
2. Get Market Price
3. Place Market Order
4. Place Limit Order
5. Get Positions
6. Get Open Orders
7. Exit
==================================================
Enter your choice (1-7): 2

Enter symbol (default: BTC): BTC
Current BTC price: $43,250.00
```

## Safety Features

- **Interactive Confirmation**: All trades require manual confirmation
- **Error Handling**: Comprehensive error handling and logging
- **Input Validation**: Validates all user inputs before execution

## Important Warnings

⚠️ **Trading cryptocurrencies involves significant risk of loss**

- Only trade with money you can afford to lose
- Test with small amounts first
- Monitor your trades regularly
- Keep your API credentials secure

## Project Structure

```
HyperLBot/
├── main.py               # Main trading interface
├── hyperliquid_api.py    # Hyperliquid API client
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── env_example.txt       # Environment variables template
└── README.md            # This file
```

## Disclaimer

This trading interface is provided as-is for educational purposes. Trading cryptocurrencies involves substantial risk of loss. The authors are not responsible for any financial losses incurred from using this software. Always test thoroughly with small amounts before using real money.

## License

This project is for educational purposes. Use at your own risk.
