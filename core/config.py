import os
from dotenv import load_dotenv

load_dotenv()

class TradingConfig:
    """Configuration for trading parameters"""
    
    # Wallet Configuration
    WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "0x60c0478b4E1cf66484EA83F133b94B35C046909b")
    WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "your_private_key_here")
    
    # Trading Parameters
    SYMBOL = os.getenv("SYMBOL", "BTC")
    LEVERAGE = int(os.getenv("LEVERAGE", "30"))
    
    # API Configuration
    HYPERLIQUID_API_URL = os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "trading.log")
    
    # Strategy Configurations
    STRATEGY_CONFIGS = {
        "standard": {
            "min_range_percentage": 0.002,  # 0.2% minimum range
            "volatility_threshold": "medium",
            "confidence_threshold": 0.3,
            "min_interval": 30,  # seconds between trades
            "max_leverage": 40,
            "profit_target": 0.01,  # 1% profit target
            "stop_loss": 0.005,  # 0.5% stop loss
            "position_size": 0.1  # 10% of balance
        },
        "low_volatility": {
            "min_range_percentage": 0.001,  # 0.1% minimum range (more sensitive)
            "volatility_threshold": "low",
            "confidence_threshold": 0.1,  # Lower confidence requirement
            "min_interval": 15,  # Faster trading
            "max_leverage": 30,  # Slightly lower leverage for safety
            "profit_target": 0.005,  # 0.5% profit target (smaller moves)
            "stop_loss": 0.003,  # 0.3% stop loss (tighter)
            "position_size": 0.15  # 15% of balance (larger positions for smaller moves)
        },
        "high_volatility": {
            "min_range_percentage": 0.005,  # 0.5% minimum range
            "volatility_threshold": "high",
            "confidence_threshold": 0.5,  # Higher confidence requirement
            "min_interval": 60,  # Slower trading
            "max_leverage": 50,
            "profit_target": 0.02,  # 2% profit target
            "stop_loss": 0.01,  # 1% stop loss
            "position_size": 0.08  # 8% of balance
        }
    }
    
    # Default strategy
    DEFAULT_STRATEGY = "standard"
    
    # Whale Analytics Configuration
    WHALE_ANALYTICS_ENABLED = True  # Set to True to enable whale tracking
    WHALE_CONFIRMATION_THRESHOLD = 0.7  # Confidence threshold for blocking trades

# Global config instance
config = TradingConfig()
