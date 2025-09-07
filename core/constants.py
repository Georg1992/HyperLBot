#!/usr/bin/env python3
"""
Trading Bot Constants
Centralized location for system constants, hardcoded values, and magic numbers

Note: User-configurable parameters (like balance, leverage, etc.) are now in config/config.py
This file contains only non-configurable system constants and magic numbers.
"""

import os

class TradingConstants:
    """All trading-related constants in one place"""
    
    # Default Values (non-configurable constants only)
    DEFAULT_BTC_PRICE = 97500.0
    
    # Dashboard defaults - these are used throughout the codebase for consistency
    DEFAULT_DASHBOARD_HOST = "0.0.0.0"
    DEFAULT_DASHBOARD_PORT = 5002
    
    # Time Intervals (seconds) - these are system constants, not user configurable
    MIN_TRADE_INTERVAL = 300  # 5 minutes
    SIGNAL_COOLDOWN = 300     # 5 minutes
    PRICE_DIFFERENCE_ALERT_COOLDOWN = 300  # 5 minutes
    
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
    
    # Note: Configurable values like LEVERAGE, MAX_POSITION_SIZE, DASHBOARD_PORT, etc. 
    # are now defined in config/config.py for environment variable support
    
    # Dashboard Update Intervals
    DASHBOARD_UPDATE_INTERVAL = 2    # seconds
    FORCE_UPDATE_INTERVAL = 10       # seconds
    
    # Volume and Market Data
    BASE_VOLUME = 2500000000  # 2.5B baseline volume
    BUSINESS_HOURS_MULTIPLIER = 1.2
    OFF_HOURS_MULTIPLIER = 0.8
    
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
    
    # Price multipliers
    PROFIT_TARGET_MULTIPLIER = 1.02  # 2% profit target
    STOP_LOSS_MULTIPLIER = 0.98      # 2% stop loss
    PARTIAL_CLOSE_MULTIPLIER = 0.5   # 50% partial close
    SCALE_SIZE_MULTIPLIER = 0.5      # 50% scale size
    
    # Imbalance thresholds
    ORDERBOOK_IMBALANCE_THRESHOLD = 0.3  # 30% imbalance
    
    # Market pressure thresholds
    PRESSURE_STRONG_THRESHOLD = 0.25     # 25% imbalance for strong pressure
    PRESSURE_MODERATE_THRESHOLD = 0.1    # 10% imbalance for moderate pressure
    PRESSURE_DEPTH_REFERENCE = 20.0      # 20 BTC reference for confidence calculation
    PRESSURE_MAX_STRENGTH = 0.95         # Maximum pressure strength
    PRESSURE_MIN_STRENGTH = 0.1          # Minimum pressure strength
    PRESSURE_HIGH_CONCENTRATION = 0.8    # High depth concentration threshold
    PRESSURE_LOW_CONCENTRATION = 0.6     # Low depth concentration threshold
    
    # Orderbook depth thresholds (BTC amounts) - REALISTIC Bitcoin market levels
    ORDERBOOK_DEPTH_EXTREMELY_HIGH = 50.0   # 50+ BTC depth (very high for Bitcoin)
    ORDERBOOK_DEPTH_VERY_HIGH = 30.0        # 30-50 BTC depth
    ORDERBOOK_DEPTH_HIGH = 20.0             # 20-30 BTC depth  
    ORDERBOOK_DEPTH_ABOVE_AVERAGE = 15.0    # 15-20 BTC depth
    ORDERBOOK_DEPTH_NORMAL = 10.0           # 10-15 BTC depth
    ORDERBOOK_DEPTH_BELOW_AVERAGE = 7.0     # 7-10 BTC depth
    ORDERBOOK_DEPTH_LOW = 5.0               # 5-7 BTC depth
    
    # Price fallbacks
    FALLBACK_BTC_PRICE = 50000.0
    FALLBACK_BALANCE = 100.0
    
    # Position size defaults
    DEFAULT_POSITION_SIZE_BTC = 0.001
    DEFAULT_POSITION_SIZE_USD = 50.0
    
    # Test values
    TEST_BALANCE = 100.0
    TEST_BTC_PRICE = 45000.0
    
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

class DataFetchingConstants:
    """Data fetching and update interval constants"""
    
    # Yahoo Finance Update Intervals (seconds)
    YAHOO_UPDATE_INTERVAL = 300      # 5 minutes for full analysis
    HOURLY_UPDATE_INTERVAL = 900     # 15 minutes for 1h candles
    DAILY_UPDATE_INTERVAL = 3600     # 1 hour for daily candles
    # RSI_UPDATE_INTERVAL removed - now real-time with Yahoo corrections
    
    # Cache Durations
    YAHOO_CACHE_DURATION = 5         # 5 seconds cache for ultra-frequent updates
    MARKET_DATA_CACHE_DURATION = 5   # 5 seconds for real-time data
    INDICATOR_CACHE_DURATION = 60    # 1 minute for calculated indicators
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


class VolumeConstants:
    """Volume analysis constants"""
    
    # Trading volume thresholds (USD/share amounts) - used by YahooDataFetcher
    TRADING_VOLUME_EXTREMELY_HIGH = 500000    # 500K+ trading volume
    TRADING_VOLUME_VERY_HIGH = 200000         # 200K+ trading volume  
    TRADING_VOLUME_HIGH = 100000              # 100K+ trading volume
    TRADING_VOLUME_ABOVE_AVERAGE = 50000      # 50K+ trading volume
    TRADING_VOLUME_NORMAL = 20000             # 20K+ trading volume
    TRADING_VOLUME_BELOW_AVERAGE = 10000      # 10K+ trading volume
    TRADING_VOLUME_LOW = 5000                 # 5K+ trading volume
    TRADING_VOLUME_VERY_LOW = 2000            # 2K+ trading volume
    
    # Volume Multipliers
    VOLUME_SURGE_MULTIPLIER = 3      # 300% of average for surge detection
    VOLUME_DEPTH_ESTIMATE = 0.15     # 15% of depth as recent volume
    
    # Standardized volume categories (used by all components)
    VOLUME_CATEGORY_EXTREMELY_HIGH = "EXTREMELY_HIGH"
    VOLUME_CATEGORY_VERY_HIGH = "VERY_HIGH"
    VOLUME_CATEGORY_HIGH = "HIGH"
    VOLUME_CATEGORY_ABOVE_AVERAGE = "ABOVE_AVERAGE"
    VOLUME_CATEGORY_NORMAL = "NORMAL"
    VOLUME_CATEGORY_BELOW_AVERAGE = "BELOW_AVERAGE"
    VOLUME_CATEGORY_LOW = "LOW"
    VOLUME_CATEGORY_VERY_LOW = "VERY_LOW"
    VOLUME_CATEGORY_EXTREMELY_LOW = "EXTREMELY_LOW"
    VOLUME_CATEGORY_UNKNOWN = "UNKNOWN"


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
    DEFAULT_LEVERAGE = 30            # 30x default leverage
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


class FeeConstants:
    """Fee and cost calculation constants"""
    
    # Fee Rates
    MAKER_FEE = 0.0001               # 0.01% maker fee
    TAKER_FEE = 0.0002               # 0.02% taker fee
    FUNDING_RATE = 0.0001            # 0.01% funding rate
    
    # Order Size Thresholds
    SMALL_ORDER_THRESHOLD = 100      # $100 small order
    MEDIUM_ORDER_THRESHOLD = 1000    # $1000 medium order
    
    # Fee Categories
    SMALL_ORDER_FEE = 0.0001         # 0.01% for orders < $100
    MEDIUM_ORDER_FEE = 0.0002        # 0.02% for orders $100-$1000
    LARGE_ORDER_FEE = 0.0005         # 0.05% for orders > $1000
    
    # Risk Calculations
    LIQUIDATION_RISK_CHANCE = 0.01   # 1% liquidation chance
    OPPORTUNITY_COST_RATE = 0.0001   # 0.01% per hour opportunity cost
    
    # Profit Analysis
    MIN_PROFIT_MARGIN = 0.001        # 0.1% minimum profit margin
    PROFIT_BUFFER = 0.001            # 0.1% profit buffer


class VariabilityConstants:
    """Variability analysis constants"""
    
    # Volatility Thresholds - REALISTIC Bitcoin ranges (DAILY)
    LOW_VOLATILITY = 0.002           # 0.2% - quiet market
    MEDIUM_VOLATILITY = 0.01         # 1.0% - normal Bitcoin trading
    HIGH_VOLATILITY = 0.03           # 3.0% - active Bitcoin trading
    EXTREME_VOLATILITY = 0.08        # 8.0% - very volatile Bitcoin market
    
    # 5-Minute Volatility Thresholds (for real-time trading) - REALISTIC Bitcoin 5m trading thresholds
    # Adjusted for proper ranging market classification
    VOLATILITY_5M_VERY_LOW = 0.001    # 0.1% - tight ranging markets (very small moves)
    VOLATILITY_5M_LOW = 0.0025        # 0.25% - low movement (quiet market, small moves)
    VOLATILITY_5M_MODERATE = 0.005    # 0.5% - moderate movement (normal trading, noticeable moves)
    VOLATILITY_5M_HIGH = 0.008        # 0.8% - high movement (active trading, significant moves)
    VOLATILITY_5M_EXTREME = 0.02      # 2% - extreme movement (volatile market, large moves)
    
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
    
    # Confidence Thresholds
    MIN_CONFIDENCE_THRESHOLD = 0.1   # 10% minimum confidence
    CONFIDENCE_REDUCTION_FACTOR = 0.1 # 10% confidence reduction


class SimulationConstants:
    """Simulation and testing constants"""
    
    # Test Parameters
    TEST_MONITORING_TIME = 30        # 30 seconds monitoring time
    TEST_TIMEOUT = 300               # 5 minutes test timeout
    
    # Simulation Data
    BASE_SIMULATION_PRICE = 50000    # $50,000 base price
    SIMULATION_VOLUME_BASE = 1000    # 1000 base volume
    SIMULATION_VOLUME_VARIANCE = 200 # 200 volume variance
    
    # Test Hosts
    TEST_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
    
    # Data Limits
    MAX_MARKET_DATA_POINTS = 1000    # Limit to last 1000 points


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
volume_constants = VolumeConstants()
technical_constants = TechnicalAnalysisConstants()
trading_constants = TradingExecutionConstants()
fee_constants = FeeConstants()
variability_constants = VariabilityConstants()
simulation_constants = SimulationConstants()
time_constants = TimeConstants()