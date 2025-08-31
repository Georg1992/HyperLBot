import os
from dotenv import load_dotenv

load_dotenv()

class TradingConfig:
    """
    Centralized Configuration for Trading Parameters
    
    This is the single source of truth for all configurable trading parameters.
    Environment variables take precedence over defaults.
    
    Note: System constants (timeouts, intervals, etc.) remain in core/constants.py
    """
    
    # Wallet Configuration - No defaults for security
    WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
    WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
    
    # Trading Parameters
    SYMBOL = os.getenv("SYMBOL", "BTC")
    LEVERAGE = int(os.getenv("LEVERAGE", "30"))
    
    # API Configuration
    HYPERLIQUID_API_URL = os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "trading.log")
    
    # Dashboard Configuration
    DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5002"))
    
    # General Trading Settings
    DEFAULT_INITIAL_BALANCE = float(os.getenv("DEFAULT_INITIAL_BALANCE", "120.0"))
    DEFAULT_MAX_TRADES = int(os.getenv("DEFAULT_MAX_TRADES", "10"))
    DEFAULT_CHECK_INTERVAL = int(os.getenv("DEFAULT_CHECK_INTERVAL", "5"))
    
    # Risk Management
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.4"))  # 40% max
    MIN_PROFIT_TARGET = float(os.getenv("MIN_PROFIT_TARGET", "0.005"))  # 0.5%
    MAX_STOP_LOSS = float(os.getenv("MAX_STOP_LOSS", "0.015"))  # 1.5%
    
    # Strategy Configurations
    STRATEGY_CONFIGS = {
        "standard": {
            "min_range_percentage": 0.002,  # 0.2% minimum range
            "volatility_threshold": "medium",
            "confidence_threshold": 0.3,
            "min_interval": 30,  # seconds between trades
            "max_leverage": 40,
            "profit_target": 0.008,  # 0.8% profit target
            "stop_loss": 0.004,  # 0.4% stop loss
            "position_size": 0.1  # 10% of balance
        },
        "low_volatility": {
            "min_range_percentage": 0.0005,  # 0.05% minimum range
            "volatility_threshold": "low",
            "confidence_threshold": 0.05,
            "min_interval": 60,
            "max_leverage": 30,
            "profit_target": 0.005,  # 0.5% profit target
            "stop_loss": 0.002,  # 0.2% stop loss
            "position_size": 0.2  # 20% of balance
        },
        "high_volatility": {
            "min_range_percentage": 0.005,  # 0.5% minimum range
            "volatility_threshold": "high",
            "confidence_threshold": 0.5,
            "min_interval": 60,
            "max_leverage": 50,
            "profit_target": 0.02,  # 2% profit target
            "stop_loss": 0.01,  # 1% stop loss
            "position_size": 0.08  # 8% of balance
        },
        "spike_hunting": {
            "min_range_percentage": 0.008,  # 0.8% minimum range
            "volatility_threshold": "extreme",
            "confidence_threshold": 0.75,
            "min_interval": 1800,  # 30 minutes between trades
            "max_leverage": 40,
            "profit_target": 0.035,  # 3.5% profit target
            "stop_loss": 0.015,  # 1.5% stop loss
            "position_size": 0.40,  # 40% of balance
            "volume_spike_required": True,
            "min_spike_severity": "HIGH",
            "require_momentum_alignment": True
        }
    }
    
    # Default strategy
    DEFAULT_STRATEGY = "standard"
    
    # Whale Analytics Configuration
    WHALE_ANALYTICS_ENABLED = bool(os.getenv("WHALE_ANALYTICS_ENABLED", "True").lower() == "true")
    WHALE_CONFIRMATION_THRESHOLD = float(os.getenv("WHALE_CONFIRMATION_THRESHOLD", "0.7"))
    
    @classmethod
    def validate_config(cls):
        """Validate critical configuration values"""
        errors = []
        
        # Check for required environment variables in production mode
        if not cls.WALLET_ADDRESS and os.getenv("TRADING_MODE") == "production":
            errors.append("WALLET_ADDRESS is required for production mode")
        
        if not cls.WALLET_PRIVATE_KEY and os.getenv("TRADING_MODE") == "production":
            errors.append("WALLET_PRIVATE_KEY is required for production mode")
        
        # Validate strategy configurations
        for strategy_name, config in cls.STRATEGY_CONFIGS.items():
            if config["position_size"] > cls.MAX_POSITION_SIZE:
                errors.append(f"Strategy '{strategy_name}' position size exceeds maximum")
                
        return errors

# Global config instance
config = TradingConfig()
