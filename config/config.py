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
    
    # Universal Support/Resistance Power Configuration
    # Power = pure level strength (inherent quality, not contextual)
    # Only includes: touch count, volume, reversal_probability
    # Contextual factors (proximity, recency) are used in direction/entry calculations, not level power
    SR_POWER_WEIGHTS = {
        "touch": 0.60,      # Touch count - more touches = stronger level (primary factor)
        "reversal_probability": 0.30,  # Historical reversal rate from actual data (secondary factor)
        "volume": 0.10      # Volume at level - higher = more liquidity
    }
    # Backward compatibility alias
    SR_SCORING_WEIGHTS = SR_POWER_WEIGHTS
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
        "min_range_percentage": 0.001,  # Very permissive
        "volatility_threshold": "any",
        "confidence_threshold": 0.0,  # No confidence filtering during analysis
        "min_interval": 0,
        "max_leverage": 40,
        "profit_target": 0.015,  # Not used (analysis only)
        "stop_loss": 0.010,  # Not used (analysis only)
        "position_size": 0.0,  # Not used (analysis only)
        "direction_weights": {  # Not used (analysis only)
            "rsi": 0.20,
            "trend": 0.20,
            "support_resistance": 0.20,
            "pressure": 0.15,
            "patterns": 0.15,
            "volume": 0.05,
            "funding": 0.05
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
        "min_score_diff": 12.0,  # Higher threshold for range trading (need clear signals)
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
        "min_score_diff": 10.0,
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
