#!/usr/bin/env python3
"""
Volatility Calculator Module
Centralized volatility calculations from different data sources
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from core.constants import VariabilityConstants

# Singleton pattern implementation
_global_volatility_calculator = None

def get_global_volatility_calculator() -> 'VolatilityCalculator':
    """Get the global VolatilityCalculator singleton instance"""
    global _global_volatility_calculator
    if _global_volatility_calculator is None:
        _global_volatility_calculator = VolatilityCalculator()
    return _global_volatility_calculator

class VolatilityCalculator:
    """Centralized volatility calculation system"""
    
    def __init__(self):
        logger.info("📊 Volatility Calculator initialized")
    
    def calculate_candle_volatility(self, candles: List[Dict], timeframe: str = "5m", strategy: str = "standard") -> Dict[str, Any]:
        """Calculate strategy-dependent volatility from candle data"""
        try:
            if len(candles) < 1:  # Allow single candle for current candle priority
                logger.warning(f"⚠️ Not enough candles for volatility calculation: {len(candles)} < 1")
                raise Exception(f"Insufficient candles for volatility calculation: {len(candles)} < 1")
            
            # Strategy-specific time periods (in minutes)
            strategy_periods_minutes = {
                "scalping": 5,        # 5 minutes (1 × 5m candle)
                "standard": 15,       # 15 minutes (3 × 5m candles) 
                "range_trading": 60,  # 1 hour (12 × 5m candles)
                "breakout": 10,      # 10 minutes (2 × 5m candles)
                "trend_following": 120, # 2 hours (24 × 5m candles)
                "low_volatility_range": 75, # 1.25 hours (15 × 5m candles)
                "high_volatility": 15   # 15 minutes (3 × 5m candles)
            }
            
            # Get strategy-specific period in minutes
            period_minutes = strategy_periods_minutes.get(strategy, 15)  # Default to 15 minutes for standard
            period_candles = max(1, period_minutes // 5)  # Convert minutes to 5m candles
            
            # Use the most recent candles for the calculated period
            recent_candles = candles[-period_candles:] if len(candles) >= period_candles else candles
            actual_period_candles = len(recent_candles)
            actual_period_minutes = actual_period_candles * 5
            
            # Strategy-specific volatility thresholds (adjusted for timeframe)
            strategy_thresholds = {
                "scalping": {      # 5min - very sensitive
                    "LOW": 0.0008,      # 0.08%
                    "MODERATE": 0.0015,  # 0.15%
                    "HIGH": 0.0025,     # 0.25%
                    "EXTREME": 0.0040   # 0.40%
                },
                "standard": {      # 15min - balanced
                    "LOW": 0.0015,      # 0.15%
                    "MODERATE": 0.0030,  # 0.30%
                    "HIGH": 0.0040,     # 0.40%
                    "EXTREME": 0.0080   # 0.80%
                },
                "range_trading": { # 60min - less sensitive
                    "LOW": 0.0020,      # 0.20%
                    "MODERATE": 0.0040,  # 0.40%
                    "HIGH": 0.0060,     # 0.60%
                    "EXTREME": 0.0120   # 1.20%
                },
                "breakout": {      # 10min - sensitive
                    "LOW": 0.0010,      # 0.10%
                    "MODERATE": 0.0020,  # 0.20%
                    "HIGH": 0.0030,     # 0.30%
                    "EXTREME": 0.0050   # 0.50%
                },
                "trend_following": { # 120min - least sensitive
                    "LOW": 0.0030,      # 0.30%
                    "MODERATE": 0.0060,  # 0.60%
                    "HIGH": 0.0100,     # 1.00%
                    "EXTREME": 0.0200   # 2.00%
                },
                "low_volatility_range": { # 75min - moderate sensitivity
                    "LOW": 0.0025,      # 0.25%
                    "MODERATE": 0.0050,  # 0.50%
                    "HIGH": 0.0080,     # 0.80%
                    "EXTREME": 0.0150   # 1.50%
                },
                "high_volatility": { # 15min - balanced
                    "LOW": 0.0015,      # 0.15%
                    "MODERATE": 0.0030,  # 0.30%
                    "HIGH": 0.0040,     # 0.40%
                    "EXTREME": 0.0080   # 0.80%
                }
            }
            
            # Get strategy-specific thresholds
            thresholds = strategy_thresholds.get(strategy, strategy_thresholds["standard"])
            
            logger.debug(f"📊 Volatility calculation: {strategy} strategy using {actual_period_candles} candles ({actual_period_minutes} minutes)")
            logger.debug(f"📊 Strategy thresholds: LOW={thresholds['LOW']:.4f}, MODERATE={thresholds['MODERATE']:.4f}, HIGH={thresholds['HIGH']:.4f}, EXTREME={thresholds['EXTREME']:.4f}")
            
            # Method 1: Calculate overall price movement across all candles (captures big moves)
            if len(recent_candles) >= 2:
                # Calculate total price range across all candles
                all_highs = [candle["high"] for candle in recent_candles if candle["high"] > 0]
                all_lows = [candle["low"] for candle in recent_candles if candle["low"] > 0]
                
                if all_highs and all_lows:
                    max_high = max(all_highs)
                    min_low = min(all_lows)
                    total_range = max_high - min_low
                    avg_price = sum(candle["close"] for candle in recent_candles if candle["close"] > 0) / len([c for c in recent_candles if c["close"] > 0])
                    
                    if avg_price > 0:
                        overall_volatility = total_range / avg_price
                        logger.debug(f"🔍 Overall price movement: ${min_low:.2f} - ${max_high:.2f} = ${total_range:.2f} ({overall_volatility*100:.4f}%)")
                    else:
                        overall_volatility = 0.0
                else:
                    overall_volatility = 0.0
            else:
                overall_volatility = 0.0
            
            # Method 2: Weighted recent candle volatilities (most reactive to current market)
            weighted_volatilities = []
            total_weight = 0
            
            for i, candle in enumerate(recent_candles):
                if candle["close"] > 0 and candle["high"] > 0 and candle["low"] > 0:
                    range_vol = (candle["high"] - candle["low"]) / candle["close"]
                    # Give exponentially more weight to recent candles (much more aggressive for big moves)
                    weight = (i + 1) ** 2.5  # Much more aggressive weighting to capture recent big moves
                    weighted_volatilities.append(range_vol * weight)
                    total_weight += weight
            
            if weighted_volatilities and total_weight > 0:
                # Calculate weighted average (most recent candles have much higher impact)
                weighted_avg_volatility = sum(weighted_volatilities) / total_weight
            
                # CRITICAL: Use MAXIMUM volatility from recent candles to capture big moves immediately
                max_volatility = max(weighted_volatilities) / max(weight for weight in [(i + 1) ** 2.5 for i in range(len(recent_candles))])
                
                # CURRENT CANDLE PRIORITY: Give 95% weight to the most recent candle (current ongoing candle)
                if len(recent_candles) >= 1:
                    current_candle_range = (recent_candles[-1]["high"] - recent_candles[-1]["low"]) / recent_candles[-1]["close"]
                    # Use 95% current candle + 5% historical average for maximum sensitivity to recent moves
                    primary_volatility = (current_candle_range * 0.95) + (weighted_avg_volatility * 0.05)
                    logger.debug(f"🔍 Current candle priority: current_range={current_candle_range:.6f} ({current_candle_range*100:.4f}%), weighted_avg={weighted_avg_volatility:.6f}, final={primary_volatility:.6f} ({primary_volatility*100:.4f}%)")
                else:
                    # Fallback to maximum approach
                    primary_volatility = max(weighted_avg_volatility, max_volatility)
                
                # PRIORITY: Use the higher of current or overall volatility to capture market conditions
                # Don't ignore historical extremes - they represent actual market volatility
                if overall_volatility > primary_volatility:
                    # Use overall volatility if it's higher (captures the full range of recent price action)
                    primary_volatility = overall_volatility
                    logger.debug(f"🔍 Using overall volatility (higher): {primary_volatility:.6f} ({primary_volatility*100:.4f}%) - captures full price range")
                else:
                    # Use current volatility if it's higher (recent large moves)
                    logger.debug(f"🔍 Using current volatility (higher): {primary_volatility:.6f} ({primary_volatility*100:.4f}%) - captures recent moves")
                
                logger.debug(f"🔍 Final volatility: {primary_volatility:.6f} ({primary_volatility*100:.4f}%) - overall={overall_volatility:.6f}, individual={primary_volatility:.6f}")
            else:
                # Fallback to overall volatility only
                primary_volatility = overall_volatility
                
                # If overall volatility is high enough, return it immediately
                if overall_volatility > 0.003:  # Above HIGH threshold
                    logger.debug(f"🔍 Overall volatility is HIGH/EXTREME, returning immediately: {primary_volatility:.6f} ({primary_volatility*100:.4f}%)")
                    return {
                        "volatility": round(primary_volatility, 6),
                        "period_minutes": actual_period_minutes,
                        "period_candles": actual_period_candles,
                        "strategy": strategy,
                        "timeframe": timeframe
                    }
                
                logger.debug(f"🔍 Volatility calculation: {len(recent_candles)} candles, weighted_avg={weighted_avg_volatility:.6f} ({weighted_avg_volatility*100:.4f}%), max={max_volatility:.6f} ({max_volatility*100:.4f}%), using={primary_volatility:.6f} ({primary_volatility*100:.4f}%)")
                
                # Method 2: Recent price momentum (captures directional movement)
                if len(recent_candles) >= 3:
                    recent_momentum = 0
                    for i in range(1, len(recent_candles)):
                        if recent_candles[i-1]["close"] > 0:
                            momentum = abs(recent_candles[i]["close"] - recent_candles[i-1]["close"]) / recent_candles[i-1]["close"]
                            # Give much more weight to recent momentum (capture big moves immediately)
                            weight = (len(recent_candles) - i) ** 2.0
                            recent_momentum += momentum * weight
                    
                    # Average momentum with weight
                    momentum_weight = sum((len(recent_candles) - i) ** 2.0 for i in range(1, len(recent_candles)))
                    if momentum_weight > 0:
                        recent_momentum = recent_momentum / momentum_weight
                        
                        # Use the HIGHER of primary volatility or combined volatility to capture big moves
                        combined_volatility = (weighted_avg_volatility * 0.7) + (recent_momentum * 0.3)
                        final_volatility = max(primary_volatility, combined_volatility)
                        logger.debug(f"🔍 Combined volatility: {combined_volatility:.6f} ({combined_volatility*100:.4f}%) - momentum={recent_momentum:.6f}")
                        logger.debug(f"🔍 Final volatility: {final_volatility:.6f} ({final_volatility*100:.4f}%) - using max of primary and combined")
                        return {
                            "volatility": round(final_volatility, 6),
                            "period_minutes": actual_period_minutes,
                            "period_candles": actual_period_candles,
                            "strategy": strategy,
                            "timeframe": timeframe
                        }
                
                return {
                    "volatility": round(primary_volatility, 6),
                    "period_minutes": actual_period_minutes,
                    "period_candles": actual_period_candles,
                    "strategy": strategy,
                    "timeframe": timeframe
                }
            
            # FIXED: Don't fall through to fallback if we already calculated volatility
            # The fallback calculation was overriding the correct volatility calculation
            if overall_volatility > 0:
                logger.debug(f"🔍 No weighted volatilities calculated, using overall volatility: {overall_volatility:.6f}")
                return {
                    "volatility": round(overall_volatility, 6),
                    "period_minutes": actual_period_minutes,
                    "period_candles": actual_period_candles,
                    "strategy": strategy,
                    "timeframe": timeframe
                }
            else:
                # For single candle or when overall volatility is 0, use the current candle range
                if len(candles) >= 1:
                    current_candle = candles[-1]
                    current_range = (current_candle["high"] - current_candle["low"]) / current_candle["close"]
                    logger.debug(f"🔍 Single candle or zero overall volatility, using current range: {current_range:.6f}")
                    return {
                        "volatility": round(current_range, 6),
                        "period_minutes": actual_period_minutes,
                        "period_candles": actual_period_candles,
                        "strategy": strategy,
                        "timeframe": timeframe
                    }
                else:
                    logger.debug(f"🔍 No candles available, returning 0")
                    return {
                        "volatility": 0.0,
                        "period_minutes": actual_period_minutes,
                        "period_candles": actual_period_candles,
                        "strategy": strategy,
                        "timeframe": timeframe
                    }
            
        except Exception as e:
            logger.error(f"❌ Candle volatility calculation failed: {e}")
            raise Exception(f"Volatility calculation failed: {e}")
    
    # Eliminated: calculate_volatility_5m, calculate_volatility_1h, calculate_volatility_1d
    
    
    def detect_volatility_change(self, candles: List[Dict], timeframe: str = "5m") -> Dict[str, Any]:
        """Detect immediate volatility changes using only the most recent candles"""
        try:
            if len(candles) < 4:
                return {
                    "change_detected": False,
                    "change_magnitude": 0.0,
                    "change_direction": "NONE",
                    "current_volatility": 0.0,
                    "previous_volatility": 0.0,
                    "urgency": "NONE"
                }
            
            # Use only the last 2 candles for immediate change detection
            current_candle = candles[-1]
            previous_candle = candles[-2]
            
            # Calculate volatility for current candle (range-based)
            current_range = (current_candle["high"] - current_candle["low"]) / current_candle["close"]
            previous_range = (previous_candle["high"] - previous_candle["low"]) / previous_candle["close"]
            
            # Calculate change magnitude
            if previous_range > 0:
                change_magnitude = (current_range - previous_range) / previous_range
            else:
                change_magnitude = 0.0
            
            # Determine change direction
            if change_magnitude > 0.5:  # 50% increase
                change_direction = "SPIKE_UP"
                urgency = "HIGH"
            elif change_magnitude > 0.2:  # 20% increase
                change_direction = "INCREASING"
                urgency = "MEDIUM"
            elif change_magnitude < -0.5:  # 50% decrease
                change_direction = "SPIKE_DOWN"
                urgency = "HIGH"
            elif change_magnitude < -0.2:  # 20% decrease
                change_direction = "DECREASING"
                urgency = "MEDIUM"
            else:
                change_direction = "STABLE"
                urgency = "LOW"
            
            # Check for extreme volatility - ULTRA SENSITIVE for current candle
            if current_range > 0.003:  # >0.3% range in single candle (ultra sensitive for current candle)
                change_direction = "EXTREME_SPIKE"
                urgency = "CRITICAL"
            elif current_range > 0.001:  # >0.1% range in single candle (moderate sensitivity)
                change_direction = "SIGNIFICANT_MOVE"
                urgency = "HIGH"
            
            logger.debug(f"🔍 Volatility change: {change_direction} ({change_magnitude*100:.1f}%) - urgency: {urgency}")
            
            return {
                "change_detected": abs(change_magnitude) > 0.1,  # 10% change threshold
                "change_magnitude": change_magnitude,
                "change_direction": change_direction,
                "current_volatility": current_range,
                "previous_volatility": previous_range,
                "urgency": urgency
            }
            
        except Exception as e:
            logger.error(f"❌ Volatility change detection failed: {e}")
            return {
                "change_detected": False,
                "change_magnitude": 0.0,
                "change_direction": "ERROR",
                "current_volatility": 0.0,
                "previous_volatility": 0.0,
                "urgency": "NONE"
            }

    def categorize_volatility_for_trading(self, volatility: float, timeframe: str = "5m", strategy: str = "standard") -> tuple:
        """Categorize volatility for trading decisions using strategy-specific thresholds"""
        try:
            # Strategy-specific volatility thresholds (same as in calculate_candle_volatility)
            strategy_thresholds = {
                "scalping": {      # 5min - very sensitive
                    "LOW": 0.0008,      # 0.08%
                    "MODERATE": 0.0015,  # 0.15%
                    "HIGH": 0.0025,     # 0.25%
                    "EXTREME": 0.0040   # 0.40%
                },
                "standard": {      # 15min - balanced
                    "LOW": 0.0015,      # 0.15%
                    "MODERATE": 0.0030,  # 0.30%
                    "HIGH": 0.0040,     # 0.40%
                    "EXTREME": 0.0080   # 0.80%
                },
                "range_trading": { # 60min - less sensitive
                    "LOW": 0.0020,      # 0.20%
                    "MODERATE": 0.0040,  # 0.40%
                    "HIGH": 0.0060,     # 0.60%
                    "EXTREME": 0.0120   # 1.20%
                },
                "breakout": {      # 10min - sensitive
                    "LOW": 0.0010,      # 0.10%
                    "MODERATE": 0.0020,  # 0.20%
                    "HIGH": 0.0030,     # 0.30%
                    "EXTREME": 0.0050   # 0.50%
                },
                "trend_following": { # 120min - least sensitive
                    "LOW": 0.0030,      # 0.30%
                    "MODERATE": 0.0060,  # 0.60%
                    "HIGH": 0.0100,     # 1.00%
                    "EXTREME": 0.0200   # 2.00%
                },
                "low_volatility_range": { # 75min - moderate sensitivity
                    "LOW": 0.0025,      # 0.25%
                    "MODERATE": 0.0050,  # 0.50%
                    "HIGH": 0.0080,     # 0.80%
                    "EXTREME": 0.0150   # 1.50%
                },
                "high_volatility": { # 15min - balanced
                    "LOW": 0.0015,      # 0.15%
                    "MODERATE": 0.0030,  # 0.30%
                    "HIGH": 0.0040,     # 0.40%
                    "EXTREME": 0.0080   # 0.80%
                }
            }
            
            # Get strategy-specific thresholds
            thresholds = strategy_thresholds.get(strategy, strategy_thresholds["standard"])
            
            logger.debug(f"🔍 Categorizing volatility {volatility:.6f} ({volatility*100:.4f}%) for {strategy} strategy")
            logger.debug(f"🔍 Strategy thresholds: LOW={thresholds['LOW']:.4f}, MODERATE={thresholds['MODERATE']:.4f}, HIGH={thresholds['HIGH']:.4f}, EXTREME={thresholds['EXTREME']:.4f}")
            
            logger.debug(f"🔍 Categorizing {timeframe} volatility: {volatility:.6f} ({volatility*100:.4f}%)")
            
            # Use timeframe-specific thresholds
            if timeframe == "1m":
                # 1-minute thresholds (more sensitive for scalping)
                if volatility >= 0.0050:  # 0.50% (extreme 1m movement)
                    category = "EXTREME"
                    trend = "VOLATILE"
                elif volatility >= 0.0025:  # 0.25% (high 1m activity)
                    category = "HIGH"
                    trend = "ACTIVE"
                elif volatility >= 0.0010:  # 0.10% (moderate 1m movement)
                    category = "MODERATE"
                    trend = "NORMAL"
                elif volatility >= 0.0003:  # 0.03% (low 1m movement)
                    category = "LOW"
                    trend = "QUIET"
                else:  # < 0.03% (very low 1m movement)
                    category = "VERY_LOW"
                    trend = "BORING"
            elif timeframe == "5m":
                # 5-minute thresholds (using strategy-specific thresholds)
                if volatility >= thresholds["EXTREME"]:
                    category = "EXTREME"
                    trend = "VOLATILE"
                elif volatility >= thresholds["HIGH"]:
                    category = "HIGH"
                    trend = "ACTIVE"
                elif volatility >= thresholds["MODERATE"]:
                    category = "MODERATE" 
                    trend = "NORMAL"
                elif volatility >= thresholds["LOW"]:
                    category = "LOW"
                    trend = "QUIET"
                else:  # < LOW threshold
                    category = "VERY_LOW"
                    trend = "BORING"
            elif timeframe == "1h":
                # 1-hour thresholds (trend confirmation)
                if volatility >= 0.0200:  # 2.00% (extreme 1h movement)
                    category = "EXTREME"
                    trend = "VOLATILE"
                elif volatility >= 0.0100:  # 1.00% (high 1h activity)
                    category = "HIGH"
                    trend = "ACTIVE"
                elif volatility >= 0.0050:  # 0.50% (moderate 1h movement)
                    category = "MODERATE"
                    trend = "NORMAL"
                elif volatility >= 0.0025:  # 0.25% (low 1h movement)
                    category = "LOW"
                    trend = "QUIET"
                else:  # < 0.20% (very low 1h movement)
                    category = "VERY_LOW"
                    trend = "BORING"
            elif timeframe == "1d":
                # Daily thresholds (market context)
                if volatility >= 0.0800:  # 8.00% (extreme daily movement)
                    category = "EXTREME"
                    trend = "VOLATILE"
                elif volatility >= 0.0400:  # 4.00% (high daily activity)
                    category = "HIGH"
                    trend = "ACTIVE"
                elif volatility >= 0.0200:  # 2.00% (moderate daily movement)
                    category = "MODERATE"
                    trend = "NORMAL"
                elif volatility >= 0.0100:  # 1.00% (low daily movement)
                    category = "LOW"
                    trend = "QUIET"
                else:  # < 1.00% (very low daily movement)
                    category = "VERY_LOW"
                    trend = "BORING"
            else:
                # Default to 5m thresholds with strategy
                return self.categorize_volatility_for_trading(volatility, "5m", strategy)
            
            logger.debug(f"🔍 {timeframe} volatility categorized as: {category} ({trend})")
            
            return category, trend
            
        except Exception as e:
            logger.error(f"❌ {timeframe} volatility categorization failed: {e}")
            return "ERROR", "ERROR"
    
    
    
    
