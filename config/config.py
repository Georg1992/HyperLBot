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
    
    # Trading Parameters - Optimized for 40x leverage
    SYMBOL = os.getenv("SYMBOL", "BTC")
    LEVERAGE = int(os.getenv("LEVERAGE", "40"))  # 40x leverage default
    
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
    
    # Risk Management - Optimized for 40x leverage
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.5"))  # 50% max (increased for 40x)
    MIN_PROFIT_TARGET = float(os.getenv("MIN_PROFIT_TARGET", "0.002"))  # 0.2% (lower for 40x)
    MAX_STOP_LOSS = float(os.getenv("MAX_STOP_LOSS", "0.008"))  # 0.8% (tighter for 40x)
    
    # Support/Resistance Scoring
    SR_PROXIMITY_DECAY_K = float(os.getenv("SR_PROXIMITY_DECAY_K", "2.0"))  # k in exp(-distance/(k*ATR))
    
    # Strategy Configurations
    STRATEGY_CONFIGS = {
    "standard": {
        "min_range_percentage": 0.002,  # 0.2% minimum range
        "volatility_threshold": "medium",
        "confidence_threshold": 0.65,  # 65% confidence minimum (USER SPECIFIED)
        "min_interval": 30,  # seconds between trades
        "max_leverage": 40,
        "profit_target": 0.008,  # 0.8% profit target
        "stop_loss": 0.004,  # 0.4% stop loss
        "position_size": 0.1  # 10% of balance
    },
    "range_trading": {
        "min_range_percentage": 0.001,  # 0.1% minimum range
        "volatility_threshold": ["low", "very_low", "moderate"],  # Range trading works in various conditions
        "confidence_threshold": 0.52,  # 52% confidence minimum (USER SPECIFIED)
        "min_interval": 60,  # 1 minute between trades
        "max_leverage": 40,
        "profit_target": 0.005,  # 0.5% profit target
        "stop_loss": 0.0025,  # 0.25% stop loss
        "position_size": 0.15,  # 15% of balance
        "range_detection_periods": 15,  # Look back 15 candles for range
        "range_tolerance": 0.0008,  # 0.08% tolerance for range boundaries
        "bounce_threshold": 0.0003,  # 0.03% minimum bounce to trade
        "max_range_width": 0.008,  # 0.8% maximum range width
        "require_range_confirmation": True,
        "support_resistance_required": True,
        "description": "General range trading strategy for sideways markets"
    },
    "breakout": {
        "confidence_threshold": 0.58,  # 58% confidence minimum for extreme volatility
        "min_interval": 45,  # 45 seconds between trades
        "max_leverage": 40,
        "profit_target": 0.012,  # 1.2% profit target (higher for breakouts)
        "stop_loss": 0.006,  # 0.6% stop loss (tighter for extreme volatility)
        "position_size": 0.12,  # 12% of balance
        "volatility_threshold": ["high", "extreme"],  # Only for high/extreme volatility
        "trend_required": True,  # Breakouts need trend confirmation
        "volume_confirmation": True,  # Volume must confirm breakout
        "breakout_threshold": 0.003,  # 0.3% minimum breakout from S/R levels
        "description": "Breakout strategy for extreme volatility markets"
    },
    "low_volatility_range": {
        "min_range_percentage": 0.0003,  # 0.03% minimum range (very tight)
        "volatility_threshold": ["low", "very_low"],  # Handles both LOW and VERY_LOW
        "confidence_threshold": 0.50,  # 50% confidence minimum (CORRECTED - minimum for execution)
        "min_interval": 30,  # 30 seconds between trades (frequent)
        "max_leverage": 40,  # Increased leverage for high-leverage trading
        "profit_target": 0.003,  # 0.3% profit target (small moves)
        "stop_loss": 0.0015,  # 0.15% stop loss (tight stops)
        "position_size": 0.25,  # 25% of balance (larger size for small moves)
        "range_detection_periods": 20,  # Look back 20 candles for range
        "range_tolerance": 0.0005,  # 0.05% tolerance for range boundaries
        "bounce_threshold": 0.0002,  # 0.02% minimum bounce to trade
        "max_range_width": 0.005,  # 0.5% maximum range width
        "require_range_confirmation": True,
        "support_resistance_required": True,
        "description": "Optimized for LOW and VERY_LOW volatility conditions with range detection"
    },
    "high_volatility": {
        "min_range_percentage": 0.005,  # 0.5% minimum range
        "volatility_threshold": "high",
        "confidence_threshold": 0.55,  # 55% confidence minimum (CORRECTED)
        "min_interval": 60,
        "max_leverage": 40,  # FIXED: Match global limit
        "profit_target": 0.015,  # 1.5% profit target (adjusted for 40x)
        "stop_loss": 0.008,  # 0.8% stop loss (adjusted for 40x)
        "position_size": 0.10  # 10% of balance (adjusted for 40x)
    },
    "spike_hunting": {
        "min_range_percentage": 0.008,  # 0.8% minimum range
        "volatility_threshold": "extreme",
        "confidence_threshold": 0.70,  # 70% confidence minimum (CORRECTED - high risk strategy)
        "min_interval": 1800,  # 30 minutes between trades
        "max_leverage": 40,
        "profit_target": 0.020,  # 2.0% profit target (safer for 40x)
        "stop_loss": 0.010,  # 1.0% stop loss (safer for 40x)
        "position_size": 0.15,  # 15% of balance (SAFER: 15% x 40x = 600% exposure)
        "volume_spike_required": True,
        "min_spike_severity": "HIGH",
        "require_momentum_alignment": True
    },
    "trend_following": {
        "min_range_percentage": 0.003,  # 0.3% minimum range
        "volatility_threshold": "moderate",
        "confidence_threshold": 0.60,  # 60% confidence minimum (CORRECTED)
        "min_interval": 120,  # 2 minutes between trades
        "max_leverage": 35,
        "profit_target": 0.012,  # 1.2% profit target
        "stop_loss": 0.006,  # 0.6% stop loss
        "position_size": 0.15,  # 15% of balance
        "trend_confirmation_required": True,
        "min_trend_strength": "STRONG",
        "momentum_alignment_required": True,
        "description": "Optimized for strong trending markets with momentum confirmation"
    },
    "scalping": {
        "min_range_percentage": 0.0005,  # 0.05% minimum range (very tight)
        "volatility_threshold": ["moderate", "high"],  # Needs some volatility for opportunities
        "confidence_threshold": 0.50,  # 50% confidence minimum (CORRECTED - minimum for execution)
        "min_interval": 30,  # 30 seconds between trades (SAFER: avoid rate limits)
        "max_leverage": 40,  # FIXED: Match global limit
        "profit_target": 0.003,  # 0.3% profit target (adjusted for 40x)
        "stop_loss": 0.002,  # 0.2% stop loss (adjusted for 40x)
        "position_size": 0.20,  # 20% of balance (SAFER: 20% x 40x = 800% exposure)
        "require_high_liquidity": True,  # Need tight spreads
        "require_low_slippage": True,  # Minimize execution costs
        "max_hold_time_seconds": 300,  # 5 minutes max hold time
        "volume_spike_required": False,  # Don't need volume spikes for scalping
        "rsi_range": [30, 70],  # Avoid extreme RSI zones
        "spread_threshold": 0.0001,  # Max spread of 0.01%
        "description": "High-frequency scalping for small, quick profits with tight risk management"
    },
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
