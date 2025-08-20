import os
from dotenv import load_dotenv

load_dotenv()

class TradingConfig:
    """Configuration class for the Hyperliquid trading bot"""
    
    def __init__(self):
        # API Configuration
        self.HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"
        
        # Wallet Authentication (set these in .env file)
        self.WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "")
        self.WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "")
        
        # Trading Parameters
        self.SYMBOL = os.getenv("SYMBOL", "BTC")
        self.LEVERAGE = int(os.getenv("LEVERAGE", "1"))
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.getenv("LOG_FILE", "trading.log")

# Global config instance
config = TradingConfig()
