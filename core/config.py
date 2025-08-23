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
            "profit_target": 0.008,  # 0.8% profit target (reduced for more realistic targets)
            "stop_loss": 0.004,  # 0.4% stop loss (reduced for better risk/reward)
            "position_size": 0.1  # 10% of balance
        },
        "low_volatility": {
            "min_range_percentage": 0.0005,  # 0.05% minimum range (very sensitive)
            "volatility_threshold": "low",
            "confidence_threshold": 0.05,  # Very low confidence requirement for active predictions
            "min_interval": 60,  # 1 minute between trades (much faster)
            "max_leverage": 30,  # Slightly lower leverage for safety
            "profit_target": 0.005,  # 0.5% profit target (increased for profitability)
            "stop_loss": 0.002,  # 0.2% stop loss (kept tight)
            "position_size": 0.2  # 20% of balance (larger positions for smaller moves)
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
        },
        "spike_hunting": {
            "min_range_percentage": 0.008,  # 0.8% minimum range - only big moves
            "volatility_threshold": "extreme",
            "confidence_threshold": 0.75,  # Very high confidence requirement
            "min_interval": 1800,  # 30 minutes between trades - selective
            "max_leverage": 40,
            "profit_target": 0.035,  # 3.5% profit target - aim for big wins
            "stop_loss": 0.015,  # 1.5% stop loss - tight but realistic
            "position_size": 0.40,  # 40% of balance - 4x larger positions
            "volume_spike_required": True,  # Only trade on confirmed volume spikes
            "min_spike_severity": "HIGH",  # Require HIGH or EXTREME volume spikes
            "require_momentum_alignment": True  # Multi-timeframe confirmation needed
        }
    }
    
    # Default strategy
    DEFAULT_STRATEGY = "standard"
    
    # Whale Analytics Configuration
    WHALE_ANALYTICS_ENABLED = True  # Set to True to enable whale tracking
    WHALE_CONFIRMATION_THRESHOLD = 0.7  # Confidence threshold for blocking trades

# Global config instance
config = TradingConfig()
