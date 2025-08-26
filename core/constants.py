#!/usr/bin/env python3
"""
Trading Bot Constants
Centralized location for all hardcoded values and magic numbers
"""

import os

class TradingConstants:
    """All trading-related constants in one place"""
    
    # Default Values
    DEFAULT_BTC_PRICE = 97500.0
    DEFAULT_INITIAL_BALANCE = 120.0
    DEFAULT_DASHBOARD_PORT = 5002
    DEFAULT_DASHBOARD_HOST = "0.0.0.0"
    
    # Time Intervals (seconds)
    DEFAULT_CHECK_INTERVAL = 5
    MIN_TRADE_INTERVAL = 300  # 5 minutes
    SIGNAL_COOLDOWN = 300     # 5 minutes
    PRICE_DIFFERENCE_ALERT_COOLDOWN = 300  # 5 minutes
    
    # Risk Management
    DEFAULT_LEVERAGE = 30
    MAX_POSITION_SIZE = 0.4    # 40%
    MIN_PROFIT_TARGET = 0.005  # 0.5%
    MAX_STOP_LOSS = 0.015      # 1.5%
    
    # Price Monitoring
    PRICE_DIFFERENCE_THRESHOLD = 0.002  # 0.2%
    
    # Session Management
    MAX_SESSIONS_TO_KEEP = 3
    SESSION_TIMEOUT = 1800  # 30 minutes
    
    # File Paths
    LOCK_FILE = "data/temp/bot_instance.lock"
    RTM_STATE_FILE = "data/cache/rtm_state.json"
    POSITIONS_FILE = "data/open_positions.json"
    SIMULATED_ACCOUNT_FILE = "data/sessions/simulated_account.json"
    
    # Log Configuration
    DEFAULT_LOG_LEVEL = "INFO"
    LOG_DIR = "trading_logs"
    
    # API Configuration
    HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"
    
    # Strategy Defaults
    DEFAULT_STRATEGY = "standard"
    DEFAULT_MAX_TRADES = 10
    
    # Dashboard Update Intervals
    DASHBOARD_UPDATE_INTERVAL = 2    # seconds
    FORCE_UPDATE_INTERVAL = 10       # seconds
    
    # Volume and Market Data
    BASE_VOLUME = 2500000000  # 2.5B baseline volume
    BUSINESS_HOURS_MULTIPLIER = 1.2
    OFF_HOURS_MULTIPLIER = 0.8
    
    # RSI and Technical Indicators
    DEFAULT_RSI = 50.0
    NEUTRAL_RSI_THRESHOLD = 50.0
    
    # Confidence Thresholds
    MIN_CONFIDENCE_THRESHOLD = 0.3
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    ULTRA_CONFIDENCE_THRESHOLD = 0.9
    
    # Position Sizes by Confidence
    LOW_CONFIDENCE_POSITION = 0.08   # 8%
    MEDIUM_CONFIDENCE_POSITION = 0.12  # 12%
    HIGH_CONFIDENCE_POSITION = 0.20   # 20%
    ULTRA_CONFIDENCE_POSITION = 0.40  # 40%
    
    # Volatility Ranges
    LOW_VOLATILITY_THRESHOLD = 0.005
    MEDIUM_VOLATILITY_THRESHOLD = 0.008
    HIGH_VOLATILITY_THRESHOLD = 0.015
    
    # Connection Timeouts
    API_TIMEOUT = 30
    CONNECTION_RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5
    
    # Balance Calculation
    REAL_BALANCE_UPDATE_INTERVAL = 60  # 1 minute
    SIMULATED_BALANCE_UPDATE_INTERVAL = 5  # 5 seconds


class StrategyConstants:
    """Strategy-specific constants"""
    
    STANDARD_STRATEGY = {
        "min_range_percentage": 0.002,
        "volatility_threshold": "medium",
        "confidence_threshold": 0.3,
        "min_interval": 30,
        "max_leverage": 40,
        "profit_target": 0.008,
        "stop_loss": 0.004,
        "position_size": 0.1
    }
    
    LOW_VOLATILITY_STRATEGY = {
        "min_range_percentage": 0.0005,
        "volatility_threshold": "low",
        "confidence_threshold": 0.05,
        "min_interval": 60,
        "max_leverage": 30,
        "profit_target": 0.005,
        "stop_loss": 0.002,
        "position_size": 0.2
    }
    
    HIGH_VOLATILITY_STRATEGY = {
        "min_range_percentage": 0.005,
        "volatility_threshold": "high",
        "confidence_threshold": 0.5,
        "min_interval": 60,
        "max_leverage": 50,
        "profit_target": 0.02,
        "stop_loss": 0.01,
        "position_size": 0.08
    }


class UIConstants:
    """UI and Dashboard constants"""
    
    # Status Icons
    STATUS_ACTIVE = "🔴 Live Trading"
    STATUS_READY = "🟡 Ready for Trading"
    STATUS_STOPPED = "⚫ Stopped"
    STATUS_ERROR = "❌ Error"
    STATUS_MONITORING = "📊 Monitoring"
    
    # Trade Types
    TRADE_TYPE_BUY = "BUY"
    TRADE_TYPE_SELL = "SELL"
    TRADE_TYPE_MARKET = "MARKET"
    TRADE_TYPE_LIMIT = "LIMIT"
    
    # Connection Status
    CONNECTION_LIVE = "🔴 Live Trading"
    CONNECTION_READY = "🟡 Ready for Trading"
    CONNECTION_LAST_SESSION = "📊 Last Session Data"
    CONNECTION_MONITORING = "📊 Monitoring"
    
    # Volume Categories
    VOLUME_HIGH = "HIGH"
    VOLUME_MEDIUM = "MEDIUM"
    VOLUME_LOW = "LOW"
    VOLUME_UNKNOWN = "UNKNOWN"
    
    # Trend Indicators (New System)
    TREND_STRONG_UPTREND = "STRONG_UPTREND"
    TREND_STRONG_DOWNTREND = "STRONG_DOWNTREND"
    TREND_UPTREND = "UPTREND"
    TREND_DOWNTREND = "DOWNTREND"
    TREND_WEAK_UPTREND = "WEAK_UPTREND"
    TREND_WEAK_DOWNTREND = "WEAK_DOWNTREND"
    TREND_MIXED = "MIXED"
    TREND_SIDEWAYS = "SIDEWAYS"
    TREND_UNKNOWN = "UNKNOWN"


# Global constants instance for easy import
constants = TradingConstants()
strategy_constants = StrategyConstants()
ui_constants = UIConstants()

# Common Magic Numbers (extracted from codebase)
class MagicNumbers:
    """Common magic numbers used throughout the codebase"""
    
    # Default confidence values
    DEFAULT_CONFIDENCE = 0.5
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    ULTRA_CONFIDENCE_THRESHOLD = 0.9
    
    # Default strength values
    DEFAULT_STRENGTH = 0.5
    HIGH_STRENGTH_THRESHOLD = 0.7
    LOW_STRENGTH_THRESHOLD = 0.3
    
    # Default win probability
    DEFAULT_WIN_PROBABILITY = 0.5
    HIGH_WIN_PROBABILITY = 0.95
    
    # Price multipliers
    PROFIT_TARGET_MULTIPLIER = 1.02  # 2% profit target
    STOP_LOSS_MULTIPLIER = 0.98      # 2% stop loss
    PARTIAL_CLOSE_MULTIPLIER = 0.5   # 50% partial close
    SCALE_SIZE_MULTIPLIER = 0.5      # 50% scale size
    
    # Imbalance thresholds
    ORDERBOOK_IMBALANCE_THRESHOLD = 0.3  # 30% imbalance
    
    # Volatility thresholds
    LOW_VOLATILITY_CAP = 0.001       # 0.1%
    MEDIUM_VOLATILITY_CAP = 0.003    # 0.3%
    HIGH_VOLATILITY_CAP = 0.015      # 1.5%
    
    # Strength caps
    MAX_STRENGTH_CAP = 0.1           # 10% max strength
    
    # Time intervals
    DASHBOARD_SLEEP_INTERVAL = 0.5   # 0.5 seconds
    
    # Risk management
    MIN_PROFIT_MARGIN = 0.001        # 0.1% minimum profit margin
    CHANGE_THRESHOLD = 0.001         # 0.1% change threshold
    
    # Position sizing
    BASE_POSITION_SIZE = 0.10        # 10% base position
    BASE_PROFIT_TARGET = 0.003       # 0.3% base profit target
    BASE_STOP_LOSS = 0.0015          # 0.15% base stop loss
    
    # Multipliers
    POSITION_MULTIPLIER_LOW = 0.5
    POSITION_MULTIPLIER_MED = 0.7
    LEVERAGE_MULTIPLIER = 0.9
    
    # Heat thresholds
    HEAT_THRESHOLD_ULTRA = 0.9
    HEAT_THRESHOLD_HIGH = 0.7
    HEAT_THRESHOLD_MED = 0.5
    HEAT_THRESHOLD_LOW = 0.3
    
    # Close percentages
    CLOSE_PERCENTAGE_HALF = 0.50
    CLOSE_PERCENTAGE_THREE_QUARTERS = 0.75
    
    # Correlation risk
    CORRELATION_RISK_SINGLE = 1.0
    CORRELATION_RISK_MIXED = 0.5
    
    # Variability thresholds
    VARIABILITY_LOW = 0.3
    VARIABILITY_MEDIUM = 0.7
    VARIABILITY_OPTIMAL = 0.7
    VARIABILITY_GOOD = 0.5
    
    # Confidence thresholds
    MIN_CONFIDENCE_THRESHOLD = 0.1
    CONFIDENCE_THRESHOLD_LOW = 0.3

# Global magic numbers instance
magic_numbers = MagicNumbers()