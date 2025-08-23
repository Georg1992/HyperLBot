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
    LOCK_FILE = "bot_instance.lock"
    RTM_STATE_FILE = "rtm_state.json"
    POSITIONS_FILE = "open_positions.json"
    SIMULATED_ACCOUNT_FILE = "simulated_account.json"
    
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
    
    # Trend Indicators
    TREND_BULLISH = "BULLISH"
    TREND_BEARISH = "BEARISH"
    TREND_SIDEWAYS = "SIDEWAYS"
    TREND_NEUTRAL = "NEUTRAL"


# Global constants instance for easy import
constants = TradingConstants()
strategy_constants = StrategyConstants()
ui_constants = UIConstants()