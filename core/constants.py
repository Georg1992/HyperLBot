#!/usr/bin/env python3
"""
Trading Bot Constants
Centralized location for system constants, hardcoded values, and magic numbers

Note: User-configurable parameters (like balance, leverage, etc.) are now in config/config.py
This file contains only non-configurable system constants and magic numbers.
"""


class TradingConstants:
    """All trading-related constants in one place"""
    
    
    # Dashboard defaults - these are used throughout the codebase for consistency
    DEFAULT_DASHBOARD_HOST = "0.0.0.0"
    DEFAULT_DASHBOARD_PORT = 5002
    
    # Time Intervals (seconds) - these are system constants, not user configurable
    MIN_TRADE_INTERVAL = 300  # 5 minutes
    SIGNAL_COOLDOWN = 300     # 5 minutes
    PRICE_DIFFERENCE_ALERT_COOLDOWN = 300  # 5 minutes
    CANDLE_UPDATE_TIMEOUT = 310  # 5 minutes 10 seconds (slightly longer than 5 min candle interval)
    # ANALYSIS_COMPLETION_DELAY removed - analysis modules are synchronous, no delay needed
    
    # Price Monitoring
    PRICE_DIFFERENCE_THRESHOLD = 0.002  # 0.2%
    PRICE_CHANGE_THRESHOLD = 0.001  # 0.1% threshold for price change detection
    
    # Session Management
    MAX_SESSIONS_TO_KEEP = 3
    SESSION_TIMEOUT = 1800  # 30 minutes
    
    # File Paths
    LOCK_FILE = "data/temp/bot_instance.lock"
    DASHBOARD_STATE_FILE = "data/cache/dashboard_state.json"
    SIMULATED_ACCOUNT_FILE = "data/accounts/simulated_account.json"
    
    # Log Configuration
    DEFAULT_LOG_LEVEL = "INFO"
    LOG_DIR = "logs"
    
    # Note: Configurable values like LEVERAGE, MAX_POSITION_SIZE, DASHBOARD_PORT, etc. 
    # are now defined in config/config.py for environment variable support
    
    # Dashboard Update Intervals
    DASHBOARD_UPDATE_INTERVAL = 2    # seconds
    FORCE_UPDATE_INTERVAL = 10       # seconds
    PRICE_UPDATE_INTERVAL = 0.1      # 100ms for real-time price updates
    RSI_DASHBOARD_UPDATE_INTERVAL = 0.5  # 500ms for RSI dashboard updates (prevent spam)
    RSI_CHANGE_THRESHOLD = 0.1       # RSI must change by at least 0.1 to trigger update
    
    # Confidence Thresholds
    MIN_CONFIDENCE_THRESHOLD = 0.3
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    ULTRA_CONFIDENCE_THRESHOLD = 0.9
    
    # Position Sizes by Confidence
    LOW_CONFIDENCE_POSITION = 0.08   # 8%
    MEDIUM_CONFIDENCE_POSITION = 0.12  # 12%
    HIGH_CONFIDENCE_POSITION = 0.20   # 20%
    ULTRA_CONFIDENCE_POSITION = 0.40  # 40%
    
    # Connection Timeouts
    API_TIMEOUT = 30
    CONNECTION_RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5
    
    # Balance Calculation
    REAL_BALANCE_UPDATE_INTERVAL = 60  # 1 minute
    SIMULATED_BALANCE_UPDATE_INTERVAL = 5  # 5 seconds


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
    
    # Market pressure thresholds - MORE STRICT to avoid noise
    PRESSURE_STRONG_THRESHOLD = 0.4      # 40% imbalance for strong pressure (was 25%)
    PRESSURE_MODERATE_THRESHOLD = 0.2    # 20% imbalance for moderate pressure (was 10%)
    PRESSURE_DEPTH_REFERENCE = 20.0      # 20 BTC reference for confidence calculation
    PRESSURE_MAX_STRENGTH = 0.95         # Maximum pressure strength
    PRESSURE_MIN_STRENGTH = 0.1          # Minimum pressure strength
    PRESSURE_HIGH_CONCENTRATION = 0.8    # High depth concentration threshold
    PRESSURE_LOW_CONCENTRATION = 0.6     # Low depth concentration threshold
    
    
    
    # Time intervals
    DASHBOARD_SLEEP_INTERVAL = 0.5   # 0.5 seconds
    
    # Confidence thresholds (using TradingConstants values)
    # MIN_CONFIDENCE_THRESHOLD = 0.1  # Duplicate - use TradingConstants.MIN_CONFIDENCE_THRESHOLD
    # CONFIDENCE_THRESHOLD_LOW = 0.3  # Duplicate - use TradingConstants.MIN_CONFIDENCE_THRESHOLD

class DataFetchingConstants:
    """Data fetching and update interval constants"""
    
    HOURLY_UPDATE_INTERVAL = 900     # 15 minutes for 1h candles
    DAILY_UPDATE_INTERVAL = 3600     # 1 hour for daily candles
    # RSI_UPDATE_INTERVAL removed - now real-time with Hyperliquid corrections
    
    # Cache Durations
    HYPERLIQUID_CACHE_DURATION = 5   # 5 seconds cache for ultra-frequent updates
    MARKET_DATA_CACHE_DURATION = 5   # 5 seconds for real-time data
    INDICATOR_CACHE_DURATION = 5     # 5 seconds for calculated indicators (temporarily reduced for trend fix testing)
    TREND_CACHE_DURATION = 30        # 30 seconds for trend data
    
    # Data Periods
    RSI_CANDLES_COUNT = 30           # 30 candles for 14-period RSI + buffer
    DAILY_CANDLES_COUNT = 30         # 30 days of daily data
    INTRADAY_CANDLES_COUNT = 30      # 30 candles for intraday analysis
    
    # Time Conversions
    MILLISECONDS_IN_SECOND = 1000
    SECONDS_IN_MINUTE = 60
    SECONDS_IN_HOUR = 3600
    SECONDS_IN_DAY = 86400
    
    # Candle Time Adjustments
    CANDLE_CLOSE_OFFSET = 59999      # Add 59.999 seconds to close time


# VolumeConstants class removed - using CoinGecko volume data instead


class TechnicalAnalysisConstants:
    """Technical analysis thresholds and parameters"""
    
    # RSI Thresholds
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_NEUTRAL = 50
    RSI_BULLISH = 60        # Above neutral, trending up
    RSI_BEARISH = 40        # Below neutral, trending down
    
    # Trend Strength Thresholds
    TREND_STRENGTH_HIGH = 0.01       # 1% strength
    TREND_STRENGTH_MEDIUM = 0.005    # 0.5% strength
    TREND_STRENGTH_LOW = 0.001       # 0.1% strength
    
    # Price Change Thresholds
    PRICE_CHANGE_SIGNIFICANT = 0.001 # 0.1% significant change
    PRICE_CHANGE_MINOR = 0.0005      # 0.05% minor change
    
    # Momentum Thresholds
    MOMENTUM_ACCELERATION_THRESHOLD = 0.001  # 0.1% acceleration
    MOMENTUM_DECELERATION_THRESHOLD = -0.001 # -0.1% deceleration
    
    # Support/Resistance
    SUPPORT_RESISTANCE_NEAR = 0.01   # Within 1% of S/R level
    
    # Volatility Caps
    VOLATILITY_MAX_CAP = 0.1         # 10% max volatility
    VOLATILITY_DEPTH_CAP = 0.5       # 50% max depth volatility
    
    # Spread Analysis
    SPREAD_SIGNIFICANT = 0.001       # 0.1% significant spread
    DEPTH_SIGNIFICANT = 0.001        # 0.1% significant depth
    
    # Volatility Categories (separate from volume categories)
    VOLATILITY_CATEGORY_EXTREMELY_HIGH = "EXTREMELY_HIGH"
    VOLATILITY_CATEGORY_VERY_HIGH = "VERY_HIGH"
    VOLATILITY_CATEGORY_HIGH = "HIGH"
    VOLATILITY_CATEGORY_ABOVE_AVERAGE = "ABOVE_AVERAGE"
    VOLATILITY_CATEGORY_NORMAL = "NORMAL"
    VOLATILITY_CATEGORY_BELOW_AVERAGE = "BELOW_AVERAGE"
    VOLATILITY_CATEGORY_LOW = "LOW"


class TradingExecutionConstants:
    """Trading execution parameters"""
    
    # Default Position Parameters
    DEFAULT_POSITION_SIZE = 0.001    # 0.1% default size
    BASE_POSITION_SIZE = 0.10        # 10% base position (moved from MagicNumbers for consistency)
    BASE_PROFIT_TARGET = 0.003       # 0.3% base profit target (moved from MagicNumbers for consistency)
    BASE_STOP_LOSS = 0.0015          # 0.15% base stop loss (moved from MagicNumbers for consistency)
    DEFAULT_LEVERAGE = 40            # 40x leverage (consistent with strategy configs)
    DEFAULT_STOP_DISTANCE = 0.002    # 0.2% stop distance
    DEFAULT_TARGET_DISTANCE = 0.005  # 0.5% target distance
    
    # Price Adjustments
    BUY_PRICE_ADJUSTMENT = 0.999     # 0.1% below current price
    SELL_PRICE_ADJUSTMENT = 1.001    # 0.1% above current price
    
    # Position Management
    MAX_HOLD_TIME = 3600             # 1 hour max hold time
    LOSS_THRESHOLD = 0.01            # 1% loss threshold
    
    # Partial Close Percentages
    PARTIAL_CLOSE_HALF = 0.50        # 50% partial close
    PARTIAL_CLOSE_THREE_QUARTERS = 0.75  # 75% partial close
    
    # Scale In Parameters
    SCALE_IN_SIZE = 0.5              # 50% scale size
    SCALE_IN_MULTIPLIER = 0.5        # 50% scale multiplier


class VariabilityConstants:
    """Variability analysis constants"""
    
    # Volatility Thresholds - REALISTIC Bitcoin ranges (DAILY)
    LOW_VOLATILITY = 0.002           # 0.2% - quiet market
    MEDIUM_VOLATILITY = 0.01         # 1.0% - normal Bitcoin trading
    HIGH_VOLATILITY = 0.03           # 3.0% - active Bitcoin trading
    EXTREME_VOLATILITY = 0.08        # 8.0% - very volatile Bitcoin market
    
    # 5-Minute Volatility Thresholds (for real-time trading) - REALISTIC Bitcoin 5m thresholds
    # UPDATED: Adjusted thresholds based on actual market observations
    VOLATILITY_5M_VERY_LOW = 0.0005    # 0.05% - almost no movement
    VOLATILITY_5M_LOW = 0.0015         # 0.15% - low movement
    VOLATILITY_5M_MODERATE = 0.0030    # 0.30% - moderate movement
    VOLATILITY_5M_HIGH = 0.0040        # 0.40% - high movement (lowered from 0.60%)
    VOLATILITY_5M_EXTREME = 0.0080     # 0.80% - extreme movement (lowered from 1.20%)
    
    # Trading Condition Scores
    OPTIMAL_TRADING_SCORE = 0.7      # 70% score for optimal conditions
    GOOD_TRADING_SCORE = 0.5         # 50% score for good conditions
    POOR_TRADING_SCORE = 0.2         # 20% score for poor conditions
    
    # Score Weights
    VOLATILITY_WEIGHT = 0.4          # 40% weight for volatility
    MOMENTUM_WEIGHT = 0.3            # 30% weight for momentum
    VOLUME_WEIGHT = 0.2              # 20% weight for volume
    PATTERN_WEIGHT = 0.1             # 10% weight for pattern
    
    # Volume Variability
    VOLUME_CV_LOW = 0.3              # Low volume variability
    VOLUME_CV_GOOD = 0.8             # Good volume variability
    VOLUME_CV_OPTIMAL = 1.5          # Optimal volume variability
    
    # Confidence Thresholds (using TradingConstants values)
    # MIN_CONFIDENCE_THRESHOLD = 0.1   # Duplicate - use TradingConstants.MIN_CONFIDENCE_THRESHOLD
    CONFIDENCE_REDUCTION_FACTOR = 0.1 # 10% confidence reduction


class TimeConstants:
    """Time-related constants"""
    
    # Time Units
    SECONDS_IN_MINUTE = 60
    SECONDS_IN_HOUR = 3600
    SECONDS_IN_DAY = 86400
    MINUTES_IN_HOUR = 60
    HOURS_IN_DAY = 24
    
    # Update Intervals
    REAL_BALANCE_UPDATE_INTERVAL = 60 # 1 minute
    SIMULATED_BALANCE_UPDATE_INTERVAL = 5 # 5 seconds
    
    # Cooldown Periods 
    ADJUSTMENT_COOLDOWN = 300        # 5 minutes between adjustments
    


# Global instances for easy import (continued from above)
magic_numbers = MagicNumbers()
data_constants = DataFetchingConstants()
# volume_constants removed - using CoinGecko volume data instead
technical_constants = TechnicalAnalysisConstants()
trading_constants = TradingExecutionConstants()
variability_constants = VariabilityConstants()
time_constants = TimeConstants()
