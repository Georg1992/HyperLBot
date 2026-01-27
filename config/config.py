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
    
    # Risk Calculation Constants (ADDED 2026-01-12 - Audit Fix)
    # Previously hardcoded throughout codebase, now centralized
    LIQUIDATION_SAFETY_BUFFER_PCT = 0.005  # 0.5% buffer before liquidation triggers stop
    ATR_BASE_MULTIPLIER = 2.0  # Base stop distance: 2.0×ATR (covers ~95% of normal moves)
    NOISE_BUFFER_ATR_MULTIPLIER = 0.25  # Noise buffer for level breaks: 0.25×ATR
    DEFAULT_SPREAD_PCT = 0.01
    
    # ATR Calculation Minimums
    ATR_MIN_PCT = 0.0005  # 0.05% of price as minimum ATR
    ATR_ABSOLUTE_MIN = 0.1  # Absolute minimum ATR value
    
    # Position Sizing Defaults
    DEFAULT_POSITION_SIZE_PCT = 0.02  # Default 2% position size  # Default spread if orderbook unavailable: 0.01% (typical BTC perp)
    
    # Round Number Avoidance (ADDED 2026-01-12 - Audit Fix)
    # Stop hunting prevention by offsetting stops from psychological levels
    ROUND_NUMBER_CONFIG = {
        "major_threshold_usd": 100.0,  # Within $100 of $5K round = VERY DANGEROUS
        "minor_threshold_usd": 150.0,  # Within $150 of $1K round = DANGEROUS
        "major_offset_usd": 150.0,     # Offset $150 for major levels ($90K, $95K, etc)
        "minor_offset_usd": 75.0       # Offset $75 for minor levels ($91K, $92K, etc)
    }
    
    # Trading Signal Thresholds (ADDED 2026-01-12 - Audit Fix)
    # Quality gates for signal execution and strategy validation
    MIN_MOMENTUM_CONFIDENCE = 65.0  # Minimum confidence % for momentum signals (reactive_engine)
    MIN_LIQUIDITY_SCORE = 0.5       # Minimum liquidity depth score for scalping (0.0-1.0)
    
    # Strategy Scoring Thresholds
    FUNDING_RATE_CHANGE_THRESHOLDS = {
        "significant_increase": 0.0001,   # 0.01% increase = significant
        "significant_decrease": -0.0001,  # -0.01% decrease = significant
        "very_stable": 0.00005            # <0.005% change = very stable
    }
    
    VOLUME_TREND_STRENGTH_THRESHOLDS = {
        "very_strong": 0.7,   # >0.7 = very strong volume trend
        "moderate": 0.5,       # >0.5 = moderate volume trend
        "weak": 0.3            # <0.3 = weak volume trend
    }
    
    # Volume Scoring Configuration
    VOLUME_CONFIRMATION_BONUS_MULTIPLIER = 1.2  # 20% bonus for high volume with strong trend
    LOW_VOLUME_PENALTY = 20.0  # Penalty for low volume (reduces confidence)
    VOLUME_ANOMALY_PENALTY = 15.0  # Penalty when volume anomaly detected (reversal risk)
    
    # Factor Synergy Configuration
    SYNERGY_BONUSES = {
        "rsi_trend_alignment": 25.0,  # RSI oversold/overbought + trend alignment
        "momentum_building": 15.0,    # RSI recovering/declining + trend alignment
        "factor_conflict": 10.0       # Penalty when factors conflict (e.g., RSI oversold + bearish trend)
    }
    
    # Entry Price Calculation Configuration
    ENTRY_FILL_DECAY_FACTOR = 3.0  # Exponential decay factor for fill probability (higher = slower decay)
    LIQUIDATION_SAFETY_MIDPOINT_PCT = 0.015  # 1.5% - inflection point for sigmoid curve
    LIQUIDATION_SAFETY_STEEPNESS = 0.1  # Controls sigmoid curve steepness (higher = steeper)
    
    VOLATILITY_THRESHOLDS = {
        "high": 0.03,    # >3% = high volatility
        "moderate": 0.01  # >1% = moderate volatility
    }
    
    # Universal Support/Resistance Power Configuration
    # Power = pure level strength (inherent quality, not contextual)
    # Only includes: touch count, volume, reversal_probability
    # Contextual factors (proximity, recency) are used in direction/entry calculations, not level power
    SR_POWER_WEIGHTS = {
        "touch": 0.60,      # Touch count - more touches = stronger level (primary factor)
        "reversal_probability": 0.30,  # Historical reversal rate from actual data (secondary factor)
        "volume": 0.10      # Volume at level - higher = more liquidity
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
    
    # ADAPTIVE TP CONFIGURATION (Market Structure Based)
    # TP placed at strongest S/R level (prioritizing level power over R:R)
    # min_rr/max_rr are GUIDELINES for mathematical fallback, not hard filters
    # Actual R:R achieved determines position sizing (see RR_POSITION_MULTIPLIERS)
    TP_ADAPTIVE_CONFIG = {
        "scalping": {
            "min_rr": 1.5,              # Minimum risk:reward ratio
            "max_rr": 3.0,              # Maximum risk:reward ratio
            "cushion_atr": 0.25,        # Cushion before level (in ATR)
            "max_distance_atr": 3.0     # Max distance to level (in ATR)
        },
        "low_volatility_range": {
            "min_rr": 1.2,              # Lower min for tight range trading (smaller but frequent profits)
            "max_rr": 3.0,
            "cushion_atr": 0.25,
            "max_distance_atr": 5.0
        },
        "standard": {
            "min_rr": 1.5,
            "max_rr": 4.0,
            "cushion_atr": 0.5,
            "max_distance_atr": 8.0
        },
        "range_trading": {
            "min_rr": 1.2,              # Lower min for range trading (take profit at range boundaries)
            "max_rr": 3.0,
            "cushion_atr": 0.25,
            "max_distance_atr": 5.0
        },
        "breakout": {
            "min_rr": 2.0,              # Higher risk needs more reward
            "max_rr": 5.0,
            "cushion_atr": 0.75,        # Larger cushion for volatile breakouts
            "max_distance_atr": 12.0
        },
        "spike_hunting": {
            "min_rr": 2.5,              # High risk strategy
            "max_rr": 5.0,
            "cushion_atr": 1.0,         # Large cushion for extreme volatility
            "max_distance_atr": 20.0
        },
        "trend_following": {
            "min_rr": 2.0,
            "max_rr": 5.0,
            "cushion_atr": 0.5,
            "max_distance_atr": 20.0
        },
        "high_volatility": {
            "min_rr": 2.0,
            "max_rr": 5.0,
            "cushion_atr": 1.0,
            "max_distance_atr": 15.0
        },
        "comprehensive_analysis": {  # Not used for trading
            "min_rr": 1.5,
            "max_rr": 5.0,
            "cushion_atr": 0.5,
            "max_distance_atr": 10.0
        }
    }
    
    # R:R-Based Position Sizing Multipliers
    # Base position_size (in strategy configs) is scaled by R:R achieved
    # This ensures we trade SMALLER on low R:R, BIGGER on high R:R
    RR_POSITION_MULTIPLIERS = {
        "min_rr": 0.8,           # R:R < 0.8 is dangerous
        "low_rr": 1.2,           # R:R 0.8-1.5: acceptable but small (0.5x-0.8x size)
        "good_rr": 1.5,          # R:R 1.5-2.5: good (1.0x size)
        "excellent_rr": 2.5,     # R:R 2.5+: excellent (1.2x-1.5x size)
        "max_multiplier": 1.5,   # Never exceed 1.5x base position size
        "min_multiplier": 0.5    # Never go below 0.5x base position size
    }
    
    # S/R LEVEL SCORING WEIGHTS (Strategy-Aware)
    # How to prioritize different factors when scoring S/R levels
    SR_LEVEL_SCORING_WEIGHTS = {
        "low_volatility_range": {
            "power": 0.15,        # Low - strength less important in tight ranges
            "proximity": 0.45,    # HIGH - need closest levels for precise entries
            "recency": 0.25,      # High - recent boundaries are active
            "mtf": 0.10,          # Medium - confirmation helpful
            "touches": 0.03,      # Low - less important
            "cluster": 0.02       # Low - less important
        },
        "range_trading": {
            "power": 0.20,        # Moderate
            "proximity": 0.40,    # High - need nearby boundaries
            "recency": 0.20,      # High - active ranges
            "mtf": 0.12,          # Medium
            "touches": 0.05,      # Low
            "cluster": 0.03       # Low
        },
        "spike_hunting": {
            "power": 0.60,        # VERY HIGH - only strongest levels
            "proximity": 0.05,    # Very low - distance doesn't matter
            "recency": 0.05,      # Very low - old strong levels still relevant
            "mtf": 0.20,          # High - confirmation critical
            "touches": 0.07,      # Medium - well-tested important
            "cluster": 0.03       # Low
        },
        "breakout": {
            "power": 0.35,        # High - need strong levels to break
            "proximity": 0.30,    # High - need nearby targets
            "recency": 0.15,      # Medium
            "mtf": 0.12,          # Medium
            "touches": 0.05,      # Low
            "cluster": 0.03       # Low
        },
        "trend_following": {
            "power": 0.35,        # High
            "proximity": 0.25,    # Medium
            "recency": 0.15,      # Medium
            "mtf": 0.15,          # Medium
            "touches": 0.06,      # Medium
            "cluster": 0.04       # Low
        },
        "high_volatility": {
            "power": 0.40,        # High - need strong levels in volatility
            "proximity": 0.20,    # Medium
            "recency": 0.15,      # Medium
            "mtf": 0.15,          # Medium
            "touches": 0.06,      # Medium
            "cluster": 0.04       # Low
        },
        "scalping": {
            "power": 0.25,        # Medium
            "proximity": 0.35,    # High - need close quick entries
            "recency": 0.25,      # High - very recent activity
            "mtf": 0.08,          # Low - less relevant for scalping
            "touches": 0.04,      # Low
            "cluster": 0.03       # Low
        },
        "standard": {
            "power": 0.30,        # Balanced
            "proximity": 0.25,    # Balanced
            "recency": 0.20,      # Balanced
            "mtf": 0.15,          # Balanced
            "touches": 0.05,      # Balanced
            "cluster": 0.05       # Balanced
        }
    }
    
    # Strategy Configurations
    STRATEGY_CONFIGS = {
    # COMPREHENSIVE ANALYSIS MODE - Strategy-independent market analysis
    # Used during analysis phase to find ALL significant levels
    # NOT a tradeable strategy - purely for objective market structure detection
    "comprehensive_analysis": {
        "min_power_threshold": 0.0,  # No power filtering during analysis (find ALL levels)
        "min_range_percentage": 0.001,  # Very permissive
        "volatility_threshold": "any",
        "confidence_threshold": 0.0,  # No confidence filtering during analysis
        "min_interval": 0,
        "max_leverage": 40,
        "profit_target": 0.015,  # Not used (analysis only)
        "stop_loss": 0.010,  # Not used (analysis only)
        "position_size": 0.0,  # Not used (analysis only)
        "direction_weights": {
            "trend": 0.24,
            "rsi": 0.22,
            "pressure": 0.20,
            "sr_proximity": 0.16,
            "patterns": 0.12,
            "volume": 0.06
        },
        "min_score_diff": 0.0,  # No filtering during analysis
        # Comprehensive proximity/recency - accept all levels
        "proximity_config": {
            "close_atr": 10.0,      # Very permissive
            "medium_atr": 20.0,
            "far_atr": 30.0
        },
        "recency_config": {
            "very_recent_hours": 168.0,   # 1 week
            "recent_hours": 720.0,        # 1 month
            "old_hours": 8760.0           # 1 year (very permissive)
        },
        "entry_proximity_config": {
            "optimal_atr": 5.0,      # Not used (analysis only)
            "acceptable_atr": 10.0,
            "too_far_atr": 20.0
        },
        "entry_candidate_weights": {
            "level_strength": 0.33,    # Equal weights (analysis only)
            "entry_quality": 0.33,
            "fill_probability": 0.34
        },
        "description": "Comprehensive market analysis mode - finds ALL significant levels"
    },
    "standard": {
        "min_power_threshold": 30.0,  # Minimum level power (0-100) - balanced quality gate
        "min_range_percentage": 0.002,  # 0.2% minimum range
        "volatility_threshold": "medium",
        "confidence_threshold": 0.65,  # 65% confidence minimum (USER SPECIFIED)
        "min_interval": 30,  # seconds between trades
        "max_leverage": 40,
        "profit_target": 0.012,  # 1.2% profit target
        "stop_loss": 0.008,  # 0.8% stop loss (adjusted for 40x leverage - too tight stops get hit by normal volatility)
        "position_size": 0.1,  # 10% of balance
        "direction_weights": {
            "trend": 0.28,
            "rsi": 0.24,
            "pressure": 0.20,
            "sr_proximity": 0.15,
            "patterns": 0.08,
            "volume": 0.05
        },
        "min_score_diff": 10.0,  # Minimum score difference to make direction decision
        # Proximity/Recency configuration for contextual factors
        "proximity_config": {
            "close_atr": 2.0,      # Full weight within 2xATR
            "medium_atr": 4.0,     # Reduced weight at 4xATR
            "far_atr": 6.0         # Further reduction at 6xATR
        },
        "recency_config": {
            "very_recent_hours": 24.0,   # Full weight < 24h
            "recent_hours": 72.0,        # Reduced weight < 72h (3 days)
            "old_hours": 168.0           # Further reduction < 168h (1 week)
        },
        "entry_proximity_config": {
            "optimal_atr": 0.5,      # Optimal entry distance
            "acceptable_atr": 1.25,  # Acceptable entry distance
            "too_far_atr": 2.0       # Too far from level
        },
        "entry_candidate_weights": {
            "level_strength": 0.30,    # Prefer stronger levels (moderate)
            "entry_quality": 0.40,     # Proximity to level (balanced)
            "fill_probability": 0.30   # Distance from current (moderate)
        }
    },
    "range_trading": {
        "min_power_threshold": 30.0,  # Raised from 25.0 - need better quality for lower R:R (1.2)
        "min_range_percentage": 0.001,  # 0.1% minimum range
        "volatility_threshold": ["low", "very_low", "moderate"],  # Range trading works in various conditions
        "confidence_threshold": 0.60,  # Raised from 0.52 - higher confidence for lower R:R (1.2)
        "min_interval": 60,  # 1 minute between trades
        "max_leverage": 40,
        "profit_target": 0.007,  # 0.7% profit target
        "stop_loss": 0.005,  # 0.5% stop loss (adjusted for 40x leverage)
        "position_size": 0.12,  # Reduced from 0.15 - smaller size for lower R:R (1.2)
        "range_detection_periods": 15,  # Look back 15 candles for range
        "range_tolerance": 0.0008,  # 0.08% tolerance for range boundaries
        "bounce_threshold": 0.0003,  # 0.03% minimum bounce to trade
        "max_range_width": 0.008,  # 0.8% maximum range width
        "require_range_confirmation": True,
        "support_resistance_required": True,
        "description": "General range trading strategy for sideways markets",
        "direction_weights": {
            "rsi": 0.38,
            "pressure": 0.25,
            "sr_proximity": 0.20,
            "trend": 0.10,
            "patterns": 0.05,
            "volume": 0.02
        },
        "min_score_diff": 15.0,  # Raised from 12.0 - need clear directional edge for lower R:R (1.2)
        "proximity_config": {
            "close_atr": 1.5,      # Tighter for range trading (recent boundaries matter)
            "medium_atr": 3.0,
            "far_atr": 5.0
        },
        "recency_config": {
            "very_recent_hours": 12.0,   # Range boundaries must be recent
            "recent_hours": 48.0,
            "old_hours": 120.0
        },
        "entry_proximity_config": {
            "optimal_atr": 0.3,      # Tighter for range trading
            "acceptable_atr": 0.8,
            "too_far_atr": 1.5
        },
        "entry_candidate_weights": {
            "level_strength": 0.25,    # Moderate strength preference
            "entry_quality": 0.45,     # High precision (tight range)
            "fill_probability": 0.30   # Moderate fill priority
        }
    },
    "breakout": {
        "min_power_threshold": 40.0,  # High threshold - need strong levels to break through
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
            "volume": 0.32,
            "patterns": 0.28,
            "trend": 0.18,
            "sr_proximity": 0.12,
            "pressure": 0.08,
            "rsi": 0.02
        },
        "min_score_diff": 10.0,
        "proximity_config": {
            "close_atr": 4.0,      # Wider tolerance for breakouts (can break from distance)
            "medium_atr": 8.0,
            "far_atr": 12.0
        },
        "recency_config": {
            "very_recent_hours": 48.0,   # Older levels can still break
            "recent_hours": 168.0,
            "old_hours": 336.0
        },
        "entry_proximity_config": {
            "optimal_atr": 1.0,      # Wider for breakouts
            "acceptable_atr": 2.5,
            "too_far_atr": 4.0
        },
        "entry_candidate_weights": {
            "level_strength": 0.40,    # High strength (strong breakout levels)
            "entry_quality": 0.25,     # Lower precision (momentum-driven)
            "fill_probability": 0.35   # High fill (need to catch move)
        }
    },
    "low_volatility_range": {
        "min_power_threshold": 25.0,  # Raised from 20.0 - need better quality levels for lower R:R (1.2)
        "min_range_percentage": 0.0003,  # 0.03% minimum range (very tight)
        "volatility_threshold": ["low", "very_low"],  # Handles both LOW and VERY_LOW
        "confidence_threshold": 0.60,  # Raised from 0.50 - need higher confidence for lower R:R (1.2)
        "min_interval": 30,  # 30 seconds between trades (frequent)
        "max_leverage": 40,  # Increased leverage for high-leverage trading
        "profit_target": 0.005,  # 0.5% profit target (small moves)
        "stop_loss": 0.004,  # 0.4% stop loss (adjusted for 40x leverage - even low vol needs wider stops)
        "position_size": 0.20,  # Reduced from 0.25 - smaller size for lower R:R (1.2) trades
        "range_detection_periods": 20,  # Look back 20 candles for range
        "range_tolerance": 0.0005,  # 0.05% tolerance for range boundaries
        "bounce_threshold": 0.0002,  # 0.02% minimum bounce to trade
        "max_range_width": 0.005,  # 0.5% maximum range width
        "require_range_confirmation": True,
        "support_resistance_required": True,
        "description": "Optimized for LOW and VERY_LOW volatility conditions with range detection",
        "direction_weights": {
            "rsi": 0.40,
            "pressure": 0.28,
            "sr_proximity": 0.22,
            "trend": 0.06,
            "patterns": 0.03,
            "volume": 0.01
        },
        "min_score_diff": 15.0,  # Raised from 10.0 - need clearer directional edge for lower R:R (1.2)
        "proximity_config": {
            "close_atr": 1.0,      # Very tight for low volatility ranges
            "medium_atr": 2.0,
            "far_atr": 3.5
        },
        "recency_config": {
            "very_recent_hours": 6.0,    # Very recent boundaries only
            "recent_hours": 24.0,
            "old_hours": 72.0
        },
        "entry_proximity_config": {
            "optimal_atr": 0.2,      # Very tight for low volatility
            "acceptable_atr": 0.6,
            "too_far_atr": 1.2
        },
        "entry_candidate_weights": {
            "level_strength": 0.25,    # Moderate strength
            "entry_quality": 0.50,     # Highest precision (tight ranges)
            "fill_probability": 0.25   # Lower fill priority (patient)
        }
    },
    "high_volatility": {
        "min_power_threshold": 35.0,  # Medium-high - need decent strength in volatile markets
        "min_range_percentage": 0.005,  # 0.5% minimum range
        "volatility_threshold": "high",
        "confidence_threshold": 0.55,  # 55% confidence minimum (CORRECTED)
        "min_interval": 60,
        "max_leverage": 40,  # FIXED: Match global limit
        "profit_target": 0.020,  # 2.0% profit target (adjusted for 40x)
        "stop_loss": 0.013,  # 1.3% stop loss (adjusted for 40x leverage and high volatility)
        "position_size": 0.10,  # 10% of balance (adjusted for 40x)
        "direction_weights": {
            "trend": 0.32,
            "pressure": 0.28,
            "volume": 0.20,
            "sr_proximity": 0.10,
            "rsi": 0.08,
            "patterns": 0.02
        },
        "min_score_diff": 12.0,
        "proximity_config": {
            "close_atr": 3.0,      # Wider for high volatility
            "medium_atr": 6.0,
            "far_atr": 10.0
        },
        "recency_config": {
            "very_recent_hours": 36.0,   # Moderate recency
            "recent_hours": 96.0,
            "old_hours": 240.0
        },
        "entry_proximity_config": {
            "optimal_atr": 0.8,      # Wider for high volatility
            "acceptable_atr": 2.0,
            "too_far_atr": 3.5
        },
        "entry_candidate_weights": {
            "level_strength": 0.40,    # High strength (need strong levels in volatility)
            "entry_quality": 0.25,     # Lower precision (fast-moving)
            "fill_probability": 0.35   # High fill (catch volatile moves)
        }
    },
    "spike_hunting": {
        "min_power_threshold": 50.0,  # Very high - only strongest levels for spike reversals
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
            "volume": 0.42,
            "pressure": 0.35,
            "sr_proximity": 0.12,
            "trend": 0.06,
            "rsi": 0.03,
            "patterns": 0.02
        },
        "min_score_diff": 20.0,  # Very high threshold - need extreme signals
        "proximity_config": {
            "close_atr": 5.0,      # Very wide for spike hunting
            "medium_atr": 10.0,
            "far_atr": 15.0
        },
        "recency_config": {
            "very_recent_hours": 72.0,   # Older levels can spike
            "recent_hours": 240.0,
            "old_hours": 720.0
        },
        "entry_proximity_config": {
            "optimal_atr": 1.5,      # Wide for spikes
            "acceptable_atr": 3.5,
            "too_far_atr": 6.0
        },
        "entry_candidate_weights": {
            "level_strength": 0.50,    # Highest strength (only strongest levels)
            "entry_quality": 0.30,     # Moderate precision
            "fill_probability": 0.20   # Lowest fill priority (very patient)
        }
    },
    "trend_following": {
        "min_power_threshold": 35.0,  # Medium-high - need good quality levels for entries
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
            "trend": 0.50,
            "rsi": 0.18,
            "pressure": 0.14,
            "sr_proximity": 0.10,
            "volume": 0.05,
            "patterns": 0.03
        },
        "min_score_diff": 15.0,  # Higher threshold - need strong trend confirmation
        "proximity_config": {
            "close_atr": 3.0,      # Moderate for trend following
            "medium_atr": 6.0,
            "far_atr": 9.0
        },
        "recency_config": {
            "very_recent_hours": 48.0,   # Trend levels can be older
            "recent_hours": 168.0,
            "old_hours": 336.0
        },
        "entry_proximity_config": {
            "optimal_atr": 0.7,      # Moderate for trend following
            "acceptable_atr": 1.8,
            "too_far_atr": 3.0
        },
        "entry_candidate_weights": {
            "level_strength": 0.40,    # High strength (trend + strong level)
            "entry_quality": 0.35,     # Good precision
            "fill_probability": 0.25   # Lower fill (patient with trend)
        }
    },
    "scalping": {
        "min_power_threshold": 25.0,  # Lower - quick entries, less strict on quality
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
            "rsi": 0.36,
            "pressure": 0.36,
            "sr_proximity": 0.16,
            "trend": 0.08,
            "patterns": 0.03,
            "volume": 0.01
        },
        "min_score_diff": 8.0,  # Lower threshold for faster decisions
        "proximity_config": {
            "close_atr": 1.0,      # Very tight for scalping (must be immediate)
            "medium_atr": 2.0,
            "far_atr": 3.0
        },
        "recency_config": {
            "very_recent_hours": 2.0,    # Very recent only for scalping
            "recent_hours": 12.0,
            "old_hours": 48.0
        },
        "entry_proximity_config": {
            "optimal_atr": 0.2,      # Very tight for scalping
            "acceptable_atr": 0.5,
            "too_far_atr": 1.0
        },
        "entry_candidate_weights": {
            "level_strength": 0.20,    # Lowest strength (speed over quality)
            "entry_quality": 0.30,     # Lower precision (fast fills)
            "fill_probability": 0.50   # Highest fill (immediate execution)
        }
    },
    }
    
    # Default strategy
    DEFAULT_STRATEGY = "standard"
    
    # Entry vs Direction Scoring Balance
    # How to weight entry quality vs direction strength in final setup score
    ENTRY_DIRECTION_WEIGHTS = {
        "entry": 0.5,      # 50% - Entry quality (proximity, level strength)
        "direction": 0.5   # 50% - Direction strength (trend, RSI, pressure)
    }
    
    # ATR Multipliers for Distance Thresholds
    # Used throughout the system for proximity, fill probability, and scoring
    ATR_MULTIPLIERS = {
        "too_close": 0.25,      # Within 0.25×ATR = too close to current price
        "optimal": 1.25,        # Within 1.25×ATR = optimal entry distance
        "moderate": 2.5,        # Within 2.5×ATR = moderate entry distance
        "far": 5.0,             # Within 5.0×ATR = far but acceptable
        "touch_tolerance": 0.5, # Within 0.5×ATR = consider level "touched"
        "dedup_cluster": 0.125, # 0.125×ATR for clustering deduplication
        "dedup_final": 1.5,     # 1.5×ATR for final deduplication
        "near_threshold": 2.5,  # 2.5×ATR = "near" distance for scoring
        "significant_diff": 1.25, # 1.25×ATR = significant price difference
        "cluster_tolerance": 0.25  # 0.25×ATR for clustering tolerance (levels within 25% of ATR are same cluster)
    }
    
    # Support/Resistance Calculation Parameters
    SR_LIQUIDATION_EXPANSION_FACTOR = 3.0  # 3x expansion for S/R discovery (expands liquidation range for level detection)
    
    # S/R Level Strength by Timeframe (for daily/weekly/monthly peaks)
    SR_STRENGTH_DAILY = 80.0   # Daily peaks are strong (major daily extremes)
    SR_STRENGTH_WEEKLY = 90.0  # Weekly peaks are very strong (major weekly extremes)
    SR_STRENGTH_MONTHLY = 100.0  # Monthly peaks are maximum strength (major monthly extremes)
    
    # Pressure Calculation Parameters
    PRESSURE_EMA_ALPHA = 0.4  # EMA smoothing factor (α = 2/(N+1) where N=4 → α=0.4 for ~4-period EMA)
    
    # Entry Quality Scoring Multipliers
    # Bonuses and penalties for entry offset quality
    ENTRY_QUALITY_MULTIPLIERS = {
        "optimal_bonus": 1.1,      # 10% bonus for optimal entry offset (0.2-0.5×ATR)
        "neutral": 1.0,            # No bonus/penalty for at-level entries
        "small_penalty": 0.95,     # 5% penalty for acceptable but suboptimal
        "medium_penalty": 0.8,     # 20% penalty for poor entry distance
        "large_penalty": 0.6       # 40% penalty for very poor entries
    }
    
    # Confidence and Score Thresholds
    # Used for filtering predictions and strategy selection
    CONFIDENCE_THRESHOLDS = {
        "min_prediction": 0.5,     # Minimum confidence to generate prediction
        "high": 0.7,               # High confidence threshold
        "medium": 0.5,             # Medium confidence threshold
        "low": 0.3,                # Low confidence threshold
        "min_score_log": 70.0      # Minimum total score to log setup details
    }
    
    # Spread Cost Thresholds (as decimal percentages)
    # Used for cost filtering and strategy scoring
    SPREAD_THRESHOLDS = {
        "excellent": 0.0001,   # <0.01% - Excellent spread
        "good": 0.0005,        # <0.05% - Good spread
        "acceptable": 0.001,   # <0.1% - Acceptable spread
        "poor": 0.005,         # <0.5% - Poor spread (warning)
        "max_acceptable": 0.01 # <1.0% - Maximum acceptable spread
    }
    
    # Alignment Factors for Contextual Direction Scoring
    # Applied when S/R level aligns/conflicts with direction
    ALIGNMENT_FACTORS = {
        "boost": 1.2,    # 20% boost for good alignment
        "penalty": 0.6,  # 40% penalty for conflict
        "neutral": 1.0   # No adjustment
    }
    
    # Volatility Adjustment Multipliers
    # How to adjust thresholds based on volatility category
    VOLATILITY_ADJUSTMENTS = {
        "low": 0.5,      # Tighter thresholds in low volatility
        "normal": 1.0,   # Standard thresholds
        "high": 1.5,     # Wider thresholds in high volatility
        "extreme_moderate": 2.5,  # Much wider in extreme volatility
        "extreme_wide": 5.0       # Very wide in extreme volatility
    }
    
    # Timeframe Weights per Strategy
    # Different strategies care about different timeframes for trend analysis
    STRATEGY_TIMEFRAME_WEIGHTS = {
        "scalping": {
            "trend_15m": 0.50,  # 50% - Most important for scalping
            "trend_1h": 0.30,   # 30% - Medium importance
            "trend_4h": 0.15,   # 15% - Low importance
            "trend_24h": 0.05   # 5% - Minimal importance
        },
        "swing_trading": {
            "trend_15m": 0.10,  # 10% - Less important
            "trend_1h": 0.25,   # 25% - Medium importance
            "trend_4h": 0.35,   # 35% - High importance
            "trend_24h": 0.30   # 30% - High importance
        },
        "trend_following": {
            "trend_15m": 0.15,  # 15% - Low importance
            "trend_1h": 0.25,   # 25% - Medium importance
            "trend_4h": 0.30,   # 30% - High importance
            "trend_24h": 0.30   # 30% - High importance
        },
        "range_trading": {
            "trend_15m": 0.20,  # 20% - Low importance (ranges are medium-term)
            "trend_1h": 0.40,   # 40% - High importance
            "trend_4h": 0.30,   # 30% - Medium importance
            "trend_24h": 0.10   # 10% - Low importance
        },
        "breakout": {
            "trend_15m": 0.25,  # 25% - Medium importance
            "trend_1h": 0.35,   # 35% - High importance
            "trend_4h": 0.30,   # 30% - High importance
            "trend_24h": 0.10   # 10% - Low importance
        },
        "low_volatility_range": {
            "trend_15m": 0.30,  # 30% - Medium importance
            "trend_1h": 0.40,   # 40% - High importance
            "trend_4h": 0.20,   # 20% - Medium importance
            "trend_24h": 0.10   # 10% - Low importance
        },
        "high_volatility": {
            "trend_15m": 0.20,  # 20% - Low importance
            "trend_1h": 0.30,   # 30% - Medium importance
            "trend_4h": 0.30,   # 30% - Medium importance
            "trend_24h": 0.20   # 20% - Medium importance
        },
        "spike_hunting": {
            "trend_15m": 0.40,  # 40% - High importance (spikes are short-term)
            "trend_1h": 0.35,   # 35% - High importance
            "trend_4h": 0.20,   # 20% - Medium importance
            "trend_24h": 0.05   # 5% - Low importance
        },
        "standard": {
            "trend_15m": 0.20,  # 20% - Balanced approach
            "trend_1h": 0.30,   # 30% - Primary timeframe
            "trend_4h": 0.30,   # 30% - Primary timeframe
            "trend_24h": 0.20   # 20% - Secondary timeframe
        }
    }
    
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
