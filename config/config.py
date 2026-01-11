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
    
    # Universal Support/Resistance Scoring Configuration
    # All strategies use the same scoring weights - SR levels are objective market features
    # Strategy only affects SELECTION (max_levels_per_side, max_distance_pct, min_level_distance_pct)
    SR_SCORING_WEIGHTS = {
        "proximity": 0.15,  # Distance from current price - closer = higher score (part of reversal probability)
        "touch": 0.50,      # Touch count - more touches = stronger level (primary factor)
        "reversal_probability": 0.20,  # Historical reversal rate from actual data (secondary factor)
        "recency": 0.10,    # Time since last touch - recent = higher score
        "volume": 0.05      # Volume at level - higher = more liquidity
    }
    SR_PROXIMITY_DECAY_K = float(os.getenv("SR_PROXIMITY_DECAY_K", "0.15"))  # k in exp(-distance/(k*ATR)) - universal decay factor
    
    # Strategy-Based Support/Resistance Level Selection
    # Each strategy has different needs for S/R level selection:
    # - max_levels_per_side: How many levels to return (scalping=1, swing=3-5, standard=2)
    # - min_level_distance_pct: Minimum distance between levels (0.1% = $100 at $100k)
    # - max_distance_pct: Maximum distance from current price (based on expected price movement in strategy timeframe)
    #   Justification: Scalping (5-15min) expects ~0.3% movement, Swing (1-7 days) expects ~5% movement
    # 
    # NOTE: SR scoring is UNIVERSAL - all levels scored the same way (touch, reversal_probability, recency, volume, proximity)
    # Strategy only affects SELECTION (how many levels, max distance, min distance between levels)
    SR_LEVEL_SELECTION = {
        "scalping": {
            "max_levels_per_side": 1,  # Only need closest level for quick trades
            "min_level_distance_pct": 0.0005,  # 0.05% minimum distance between levels
            "max_distance_pct": 0.005  # 0.5% max distance - justified: scalping timeframe (5-15min) expects ~0.3% price movement
        },
        "swing_trading": {
            "max_levels_per_side": 3,  # Need multiple levels for swing targets
            "min_level_distance_pct": 0.002,  # 0.2% minimum distance between levels
            "max_distance_pct": 0.05  # 5% max distance - justified: swing timeframe (1-7 days) expects ~5% price movement
        },
        "trend_following": {
            "max_levels_per_side": 2,  # Need support/resistance for trend confirmation
            "min_level_distance_pct": 0.0015,  # 0.15% minimum distance between levels
            "max_distance_pct": 0.03  # 3% max distance - justified: trend following timeframe (hours-days) expects ~3% movement
        },
        "breakout": {
            "max_levels_per_side": 2,  # Need levels to break through
            "min_level_distance_pct": 0.001,  # 0.1% minimum distance between levels
            "max_distance_pct": 0.02  # 2% max distance - justified: breakout timeframe (hours) expects ~2% movement
        },
        "range_trading": {
            "max_levels_per_side": 2,  # Need range boundaries
            "min_level_distance_pct": 0.001,  # 0.1% minimum distance between levels
            "max_distance_pct": 0.02  # 2% max distance - justified: range trading timeframe (hours) expects ~2% movement
        },
        "low_volatility_range": {
            "max_levels_per_side": 2,  # Need tight range boundaries
            "min_level_distance_pct": 0.0008,  # 0.08% minimum distance between levels (tighter)
            "max_distance_pct": 0.01  # 1% max distance - justified: low volatility range timeframe (hours) expects ~1% movement
        },
        "high_volatility": {
            "max_levels_per_side": 2,  # Need strong levels for volatile markets
            "min_level_distance_pct": 0.002,  # 0.2% minimum distance between levels
            "max_distance_pct": 0.08  # 8% max distance - justified: high volatility timeframe (hours-days) expects ~8% movement
        },
        "spike_hunting": {
            "max_levels_per_side": 1,  # Only need strongest level for spike targets
            "min_level_distance_pct": 0.003,  # 0.3% minimum distance between levels
            "max_distance_pct": 0.10  # 10% max distance - justified: spike hunting timeframe (days) expects ~10% movement
        },
        "standard": {  # Default behavior (current implementation)
            "max_levels_per_side": 2,
            "min_level_distance_pct": 0.001,  # 0.1% minimum distance between levels
            "max_distance_pct": 0.03  # 3% max distance - justified: standard timeframe (hours-days) expects ~3% movement
        }
    }
    
    # Strategy Configurations
    STRATEGY_CONFIGS = {
    "standard": {
        "min_range_percentage": 0.002,  # 0.2% minimum range
        "volatility_threshold": "medium",
        "confidence_threshold": 0.65,  # 65% confidence minimum (USER SPECIFIED)
        "min_interval": 30,  # seconds between trades
        "max_leverage": 40,
        "profit_target": 0.012,  # 1.2% profit target
        "stop_loss": 0.008,  # 0.8% stop loss (adjusted for 40x leverage - too tight stops get hit by normal volatility)
        "position_size": 0.1,  # 10% of balance
        "direction_weights": {
            "rsi": 0.25,
            "trend": 0.25,
            "support_resistance": 0.20,
            "pressure": 0.15,
            "patterns": 0.10,
            "volume": 0.05,
            "funding": 0.05
        },
        "min_score_diff": 10.0  # Minimum score difference to make direction decision
    },
    "range_trading": {
        "min_range_percentage": 0.001,  # 0.1% minimum range
        "volatility_threshold": ["low", "very_low", "moderate"],  # Range trading works in various conditions
        "confidence_threshold": 0.52,  # 52% confidence minimum (USER SPECIFIED)
        "min_interval": 60,  # 1 minute between trades
        "max_leverage": 40,
        "profit_target": 0.007,  # 0.7% profit target
        "stop_loss": 0.005,  # 0.5% stop loss (adjusted for 40x leverage)
        "position_size": 0.15,  # 15% of balance
        "range_detection_periods": 15,  # Look back 15 candles for range
        "range_tolerance": 0.0008,  # 0.08% tolerance for range boundaries
        "bounce_threshold": 0.0003,  # 0.03% minimum bounce to trade
        "max_range_width": 0.008,  # 0.8% maximum range width
        "require_range_confirmation": True,
        "support_resistance_required": True,
        "description": "General range trading strategy for sideways markets",
        "direction_weights": {
            "support_resistance": 0.40,  # Very high weight - S/R is everything in range trading
            "rsi": 0.25,  # High weight - RSI for oversold/overbought at range boundaries
            "pressure": 0.15,  # Medium weight - Pressure at boundaries
            "trend": 0.10,  # Low weight - Trend less important in ranges
            "patterns": 0.05,  # Low weight - Patterns less relevant
            "volume": 0.05,  # Low weight - Volume confirmation
            "funding": 0.00  # No weight - Funding irrelevant
        },
        "min_score_diff": 12.0  # Higher threshold for range trading (need clear signals)
    },
    "breakout": {
        "confidence_threshold": 0.58,  # 58% confidence minimum for extreme volatility
        "min_interval": 45,  # 45 seconds between trades
        "max_leverage": 40,
        "profit_target": 0.018,  # 1.8% profit target (higher for breakouts)
        "stop_loss": 0.012,  # 1.2% stop loss (adjusted for 40x leverage and extreme volatility)
        "position_size": 0.12,  # 12% of balance
        "volatility_threshold": ["high", "extreme"],  # Only for high/extreme volatility
        "trend_required": True,  # Breakouts need trend confirmation
        "volume_confirmation": True,  # Volume must confirm breakout
        "breakout_threshold": 0.003,  # 0.3% minimum breakout from S/R levels
        "description": "Breakout strategy for extreme volatility markets",
        "direction_weights": {
            "patterns": 0.30,  # Very high weight - Breakout patterns are key
            "volume": 0.25,  # High weight - Volume must confirm breakout
            "trend": 0.20,  # High weight - Trend direction matters
            "support_resistance": 0.15,  # Medium weight - Breakout from S/R levels
            "pressure": 0.05,  # Low weight - Pressure less important
            "rsi": 0.05,  # Low weight - RSI less relevant for breakouts
            "funding": 0.00  # No weight - Funding irrelevant
        },
        "min_score_diff": 10.0
    },
    "low_volatility_range": {
        "min_range_percentage": 0.0003,  # 0.03% minimum range (very tight)
        "volatility_threshold": ["low", "very_low"],  # Handles both LOW and VERY_LOW
        "confidence_threshold": 0.50,  # 50% confidence minimum (CORRECTED - minimum for execution)
        "min_interval": 30,  # 30 seconds between trades (frequent)
        "max_leverage": 40,  # Increased leverage for high-leverage trading
        "profit_target": 0.005,  # 0.5% profit target (small moves)
        "stop_loss": 0.004,  # 0.4% stop loss (adjusted for 40x leverage - even low vol needs wider stops)
        "position_size": 0.25,  # 25% of balance (larger size for small moves)
        "range_detection_periods": 20,  # Look back 20 candles for range
        "range_tolerance": 0.0005,  # 0.05% tolerance for range boundaries
        "bounce_threshold": 0.0002,  # 0.02% minimum bounce to trade
        "max_range_width": 0.005,  # 0.5% maximum range width
        "require_range_confirmation": True,
        "support_resistance_required": True,
        "description": "Optimized for LOW and VERY_LOW volatility conditions with range detection",
        "direction_weights": {
            "support_resistance": 0.45,  # Very high weight - S/R critical in tight ranges
            "rsi": 0.30,  # High weight - RSI for oversold/overbought
            "pressure": 0.15,  # Medium weight - Pressure at boundaries
            "trend": 0.05,  # Low weight - Trend less relevant in tight ranges
            "patterns": 0.03,  # Very low weight
            "volume": 0.02,  # Very low weight
            "funding": 0.00  # No weight
        },
        "min_score_diff": 10.0
    },
    "high_volatility": {
        "min_range_percentage": 0.005,  # 0.5% minimum range
        "volatility_threshold": "high",
        "confidence_threshold": 0.55,  # 55% confidence minimum (CORRECTED)
        "min_interval": 60,
        "max_leverage": 40,  # FIXED: Match global limit
        "profit_target": 0.020,  # 2.0% profit target (adjusted for 40x)
        "stop_loss": 0.013,  # 1.3% stop loss (adjusted for 40x leverage and high volatility)
        "position_size": 0.10,  # 10% of balance (adjusted for 40x)
        "direction_weights": {
            "trend": 0.30,  # High weight - Follow the trend in volatile markets
            "pressure": 0.25,  # High weight - Pressure shows momentum
            "volume": 0.20,  # High weight - Volume confirms moves
            "rsi": 0.15,  # Medium weight - RSI for extremes
            "support_resistance": 0.05,  # Low weight - S/R less reliable in high vol
            "patterns": 0.05,  # Low weight
            "funding": 0.00  # No weight
        },
        "min_score_diff": 12.0
    },
    "spike_hunting": {
        "min_range_percentage": 0.008,  # 0.8% minimum range
        "volatility_threshold": "extreme",
        "confidence_threshold": 0.70,  # 70% confidence minimum (CORRECTED - high risk strategy)
        "min_interval": 1800,  # 30 minutes between trades
        "max_leverage": 40,
        "profit_target": 0.025,  # 2.5% profit target (adjusted for 40x)
        "stop_loss": 0.015,  # 1.5% stop loss (adjusted for 40x leverage and extreme volatility)
        "position_size": 0.15,  # 15% of balance (SAFER: 15% x 40x = 600% exposure)
        "volume_spike_required": True,
        "min_spike_severity": "HIGH",
        "require_momentum_alignment": True,
        "direction_weights": {
            "volume": 0.40,  # Very high weight - Volume spikes are key
            "pressure": 0.30,  # High weight - Extreme pressure
            "trend": 0.15,  # Medium weight - Trend alignment
            "rsi": 0.10,  # Low weight - RSI extremes
            "patterns": 0.05,  # Low weight
            "support_resistance": 0.00,  # No weight - S/R irrelevant for spikes
            "funding": 0.00  # No weight
        },
        "min_score_diff": 20.0  # Very high threshold - need extreme signals
    },
    "trend_following": {
        "min_range_percentage": 0.003,  # 0.3% minimum range
        "volatility_threshold": "moderate",
        "confidence_threshold": 0.60,  # 60% confidence minimum (CORRECTED)
        "min_interval": 120,  # 2 minutes between trades
        "max_leverage": 35,
        "profit_target": 0.018,  # 1.8% profit target
        "stop_loss": 0.010,  # 1.0% stop loss (adjusted for 40x leverage)
        "position_size": 0.15,  # 15% of balance
        "trend_confirmation_required": True,
        "min_trend_strength": "STRONG",
        "momentum_alignment_required": True,
        "description": "Optimized for strong trending markets with momentum confirmation",
        "direction_weights": {
            "trend": 0.45,  # Very high weight - Trend is everything
            "rsi": 0.20,  # Medium weight - RSI for entry timing
            "support_resistance": 0.15,  # Medium weight - S/R for entry points
            "pressure": 0.10,  # Low weight - Pressure confirmation
            "patterns": 0.05,  # Low weight - Patterns less important
            "volume": 0.05,  # Low weight - Volume confirmation
            "funding": 0.00  # No weight - Funding irrelevant
        },
        "min_score_diff": 15.0  # Higher threshold - need strong trend confirmation
    },
    "scalping": {
        "min_range_percentage": 0.0005,  # 0.05% minimum range (very tight)
        "volatility_threshold": ["moderate", "high"],  # Needs some volatility for opportunities
        "confidence_threshold": 0.50,  # 50% confidence minimum (CORRECTED - minimum for execution)
        "min_interval": 30,  # 30 seconds between trades (SAFER: avoid rate limits)
        "max_leverage": 40,  # FIXED: Match global limit
        "profit_target": 0.006,  # 0.6% profit target (adjusted for 40x)
        "stop_loss": 0.005,  # 0.5% stop loss (adjusted for 40x leverage - scalping still needs wider stops)
        "position_size": 0.20,  # 20% of balance (SAFER: 20% x 40x = 800% exposure)
        "require_high_liquidity": True,  # Need tight spreads
        "require_low_slippage": True,  # Minimize execution costs
        "max_hold_time_seconds": 300,  # 5 minutes max hold time
        "volume_spike_required": False,  # Don't need volume spikes for scalping
        "rsi_range": [30, 70],  # Avoid extreme RSI zones
        "spread_threshold": 0.0001,  # Max spread of 0.01%
        "description": "High-frequency scalping for small, quick profits with tight risk management",
        "direction_weights": {
            "rsi": 0.35,  # High weight - RSI is critical for scalping
            "pressure": 0.30,  # High weight - Orderbook pressure is key
            "support_resistance": 0.15,  # Medium weight - S/R for entry/exit
            "trend": 0.10,  # Low weight - Short-term, trend less important
            "patterns": 0.05,  # Low weight - Patterns too slow for scalping
            "volume": 0.05,  # Low weight - Volume confirmation
            "funding": 0.00  # No weight - Funding irrelevant for scalping
        },
        "min_score_diff": 8.0  # Lower threshold for faster decisions
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
