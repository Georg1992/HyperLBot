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
            
            # Get strategy-specific volatility parameters
            strategy_params = self._get_strategy_volatility_params(strategy)
            period_minutes = strategy_params.get("primary_minutes", 15)
            period_candles = max(1, period_minutes // 5)  # Convert minutes to 5m candles
            
            # Use the most recent candles for the calculated period
            recent_candles = candles[-period_candles:] if len(candles) >= period_candles else candles
            actual_period_candles = len(recent_candles)
            actual_period_minutes = actual_period_candles * 5
            
            # Get strategy-specific thresholds from centralized method
            thresholds = strategy_params.get("thresholds", {
                "LOW": 0.0015, "MODERATE": 0.0030, "HIGH": 0.0040, "EXTREME": 0.0080
            })
            
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
                    
                    # REAL-TIME SPIKE DETECTION: If current candle shows significant volatility, prioritize it
                    if current_candle_range > 0.01:  # 1% range in single candle = significant spike
                        # Use 98% current candle + 2% historical for maximum spike sensitivity
                        primary_volatility = (current_candle_range * 0.98) + (weighted_avg_volatility * 0.02)
                        logger.debug(f"🚨 SPIKE DETECTED: current_range={current_candle_range:.6f} ({current_candle_range*100:.4f}%) - prioritizing spike over average")
                    else:
                        # Use 95% current candle + 5% historical average for normal sensitivity
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
                # Add categorization
                category, trend = self.categorize_volatility_for_trading(overall_volatility, timeframe, strategy)
                return {
                    "volatility": round(overall_volatility, 6),
                    "period_minutes": actual_period_minutes,
                    "period_candles": actual_period_candles,
                    "strategy": strategy,
                    "timeframe": timeframe,
                    "category": category,
                    "trend": trend
                }
            else:
                # For single candle or when overall volatility is 0, use the current candle range
                if len(candles) >= 1:
                    current_candle = candles[-1]
                    current_range = (current_candle["high"] - current_candle["low"]) / current_candle["close"]
                    logger.debug(f"🔍 Single candle or zero overall volatility, using current range: {current_range:.6f}")
                    # Add categorization
                    category, trend = self.categorize_volatility_for_trading(current_range, timeframe, strategy)
                    return {
                        "volatility": round(current_range, 6),
                        "period_minutes": actual_period_minutes,
                        "period_candles": actual_period_candles,
                        "strategy": strategy,
                        "timeframe": timeframe,
                        "category": category,
                        "trend": trend
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
    
    def get_multi_timeframe_volatility(self, candles_1m: List[Dict], candles_5m: List[Dict], 
                                     candles_1h: List[Dict], candles_1d: List[Dict], 
                                     strategy: str = "standard") -> Dict[str, Any]:
        """
        Calculate volatility for multiple timeframes in one call
        
        Args:
            candles_1m: 1-minute candles
            candles_5m: 5-minute candles  
            candles_1h: 1-hour candles
            candles_1d: 1-day candles
            strategy: Strategy name for calculations
            
        Returns:
            Dict with volatility data for all timeframes
        """
        try:
            # Default fallback structure
            default_volatility = {
                "volatility": 0.0, 
                "period_minutes": 0, 
                "period_candles": 0, 
                "strategy": strategy, 
                "timeframe": "unknown"
            }
            
            # Calculate 1m volatility
            volatility_1m = default_volatility.copy()
            volatility_1m.update({"period_minutes": 1, "timeframe": "1m"})
            if candles_1m and len(candles_1m) >= 1:
                try:
                    volatility_1m = self.calculate_candle_volatility(candles_1m, "1m", strategy)
                except Exception as e:
                    logger.warning(f"⚠️ 1m volatility calculation failed: {e}")
            
            # Calculate 1h volatility  
            volatility_1h = default_volatility.copy()
            volatility_1h.update({"period_minutes": 60, "timeframe": "1h"})
            if candles_1h and len(candles_1h) >= 1:
                try:
                    volatility_1h = self.calculate_candle_volatility(candles_1h, "1h", strategy)
                except Exception as e:
                    logger.warning(f"⚠️ 1h volatility calculation failed: {e}")
            
            # Calculate 1d volatility
            volatility_1d = default_volatility.copy() 
            volatility_1d.update({"period_minutes": 1440, "timeframe": "1d"})
            if candles_1d and len(candles_1d) >= 1:
                try:
                    volatility_1d = self.calculate_candle_volatility(candles_1d, "1d", strategy)
                except Exception as e:
                    logger.warning(f"⚠️ 1d volatility calculation failed: {e}")
            
            return {
                "volatility_1m": volatility_1m,
                "volatility_1h": volatility_1h, 
                "volatility_1d": volatility_1d,
                "strategy": strategy,
                "calculated_timeframes": ["1m", "1h", "1d"]
            }
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe volatility calculation failed: {e}")
            # Return safe defaults
            return {
                "volatility_1m": default_volatility,
                "volatility_1h": default_volatility,
                "volatility_1d": default_volatility,
                "strategy": strategy,
                "error": str(e)
            }
    
    # Eliminated: calculate_volatility_5m, calculate_volatility_1h, calculate_volatility_1d
    
    
    def detect_volatility_change(self, candles: List[Dict], timeframe: str = "5m") -> Dict[str, Any]:
        """Detect volatility changes using a more robust multi-candle approach"""
        try:
            if len(candles) < 6:  # Need at least 6 candles for proper analysis
                return {
                    "change_detected": False,
                    "change_magnitude": 0.0,
                    "change_direction": "NONE",
                    "current_volatility": 0.0,
                    "previous_volatility": 0.0,
                    "urgency": "NONE"
                }
            
            # Use last 3 candles for current period and previous 3 for comparison
            current_period = candles[-3:]  # Last 3 candles (15 minutes)
            previous_period = candles[-6:-3]  # Previous 3 candles (15 minutes)
            
            # Calculate volatility for both periods using weighted candle ranges
            current_volatility = self._calculate_period_volatility(current_period)
            previous_volatility = self._calculate_period_volatility(previous_period)
            
            # Calculate change magnitude
            if previous_volatility > 0:
                change_magnitude = (current_volatility - previous_volatility) / previous_volatility
            else:
                change_magnitude = 0.0
            
            # Determine change direction with more realistic thresholds
            if change_magnitude > 1.0:  # 100% increase (doubled volatility)
                change_direction = "SPIKE_UP"
                urgency = "HIGH"
            elif change_magnitude > 0.5:  # 50% increase
                change_direction = "INCREASING"
                urgency = "MEDIUM"
            elif change_magnitude < -0.7:  # 70% decrease (significant drop)
                change_direction = "SPIKE_DOWN"
                urgency = "HIGH"
            elif change_magnitude < -0.3:  # 30% decrease
                change_direction = "DECREASING"
                urgency = "MEDIUM"
            else:
                change_direction = "STABLE"
                urgency = "LOW"
            
            # Check for extreme volatility - ULTRA SENSITIVE for current candle
            if current_volatility > 0.003:  # >0.3% volatility in current period (ultra sensitive)
                change_direction = "EXTREME_SPIKE"
                urgency = "CRITICAL"
            elif current_volatility > 0.001:  # >0.1% volatility in current period (moderate sensitivity)
                change_direction = "SIGNIFICANT_MOVE"
                urgency = "HIGH"
            
            logger.debug(f"🔍 Volatility change: {change_direction} ({change_magnitude*100:.1f}%) - urgency: {urgency}")
            
            return {
                "change_detected": abs(change_magnitude) > 0.1,  # 10% change threshold
                "change_magnitude": change_magnitude,
                "change_direction": change_direction,
                "current_volatility": current_volatility,
                "previous_volatility": previous_volatility,
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
            # Get strategy-specific thresholds from centralized method (removes duplicate code)
            strategy_volatility_params = self._get_strategy_volatility_params(strategy)
            thresholds = strategy_volatility_params.get("thresholds", {
                "LOW": 0.0015, "MODERATE": 0.0030, "HIGH": 0.0040, "EXTREME": 0.0080
            })
            
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
    
    def _get_strategy_volatility_params(self, strategy_name: str) -> Dict[str, Any]:
        """Get strategy-specific volatility calculation parameters with multi-timeframe support"""
        strategy_params = {
            "scalping": {
                "primary_minutes": 5,      # 5 min - ultra-fast reaction
                "confirmation_minutes": 10, # 10 min - volatility confirmation
                "reaction_minutes": 3,     # 3 min - immediate entry
                "thresholds": {"LOW": 0.005, "MODERATE": 0.015, "HIGH": 0.030, "EXTREME": 0.060}  # Scalping needs sensitivity
            },
            "standard": {
                "primary_minutes": 15,     # 15 min - balanced approach
                "confirmation_minutes": 30, # 30 min - volatility confirmation
                "reaction_minutes": 8,     # 8 min - entry timing
                "thresholds": {"LOW": 0.003, "MODERATE": 0.010, "HIGH": 0.020, "EXTREME": 0.050}  # Very sensitive BTC thresholds
            },
            "range_trading": {
                "primary_minutes": 60,     # 60 min - stable range volatility
                "confirmation_minutes": 120, # 120 min - range confirmation
                "reaction_minutes": 20,    # 20 min - range entry timing
                "thresholds": {"LOW": 0.008, "MODERATE": 0.020, "HIGH": 0.040, "EXTREME": 0.080}  # Range trading needs lower thresholds
            },
            "breakout": {
                "primary_minutes": 10,     # 10 min - breakout volatility
                "confirmation_minutes": 20, # 20 min - breakout confirmation
                "reaction_minutes": 5,     # 5 min - immediate entry
                "thresholds": {"LOW": 0.015, "MODERATE": 0.030, "HIGH": 0.060, "EXTREME": 0.120}  # Breakout expects higher volatility
            },
            "trend_following": {
                "primary_minutes": 90,     # 90 min - trend volatility
                "confirmation_minutes": 180, # 180 min - long-term confirmation
                "reaction_minutes": 30,    # 30 min - trend entry timing
                "thresholds": {"LOW": 0.012, "MODERATE": 0.030, "HIGH": 0.060, "EXTREME": 0.120}  # Trend following tolerates higher volatility
            },
            "spike_hunting": {
                "primary_minutes": 3,      # 3 min - ultra-fast spikes
                "confirmation_minutes": 8, # 8 min - spike confirmation
                "reaction_minutes": 2,     # 2 min - immediate entry
                "thresholds": {"LOW": 0.020, "MODERATE": 0.050, "HIGH": 0.100, "EXTREME": 0.200}  # Spike hunting expects extreme volatility
            },
            "low_volatility_range": {
                "primary_minutes": 75,     # 75 min - stable range detection
                "confirmation_minutes": 150, # 150 min - range confirmation
                "reaction_minutes": 25,    # 25 min - range entry timing
                "thresholds": {"LOW": 0.003, "MODERATE": 0.008, "HIGH": 0.015, "EXTREME": 0.030}  # Low volatility strategy needs tight thresholds
            },
            "high_volatility": {
                "primary_minutes": 15,     # 15 min - volatility smoothing
                "confirmation_minutes": 40, # 40 min - volatility confirmation
                "reaction_minutes": 8,     # 8 min - volatility entry timing
                "thresholds": {"LOW": 0.025, "MODERATE": 0.050, "HIGH": 0.100, "EXTREME": 0.200}  # High volatility strategy expects big moves
            }
        }
        
        return strategy_params.get(strategy_name, strategy_params["standard"])
    
    def calculate_multi_timeframe_volatility_for_strategy(self, candles_5m: List[Dict], 
                                                        strategy: str = "standard") -> Dict[str, Any]:
        """
        Calculate volatility using strategy-specific multi-timeframe approach
        
        Args:
            candles_5m: 5-minute candles for analysis
            strategy: Strategy name for period selection
            
        Returns:
            Dict with primary, confirmation, and reaction volatility plus metadata
        """
        try:
            if len(candles_5m) < 2:
                return {
                    "primary_volatility": 0.0,
                    "primary_category": "ERROR",
                    "volatility_consensus": "ERROR",
                    "strategy": strategy,
                    "error": "Insufficient data"
                }
            
            # Get strategy-specific parameters
            params = self._get_strategy_volatility_params(strategy)
            
            # Calculate volatility for each timeframe using different periods of 5m candles
            primary_period = max(1, params["primary_minutes"] // 5)
            confirmation_period = max(1, params["confirmation_minutes"] // 5)
            reaction_period = max(1, params["reaction_minutes"] // 5)
            
            primary_volatility = self._calculate_volatility_for_period(
                candles_5m, primary_period, params["thresholds"], "primary"
            )
            confirmation_volatility = self._calculate_volatility_for_period(
                candles_5m, confirmation_period, params["thresholds"], "confirmation"
            )
            reaction_volatility = self._calculate_volatility_for_period(
                candles_5m, reaction_period, params["thresholds"], "reaction"
            )
            
            # Determine volatility consensus
            volatility_consensus = self._determine_volatility_consensus(
                primary_volatility, confirmation_volatility, reaction_volatility
            )
            
            return {
                "primary_volatility": primary_volatility["volatility"],
                "primary_category": primary_volatility["category"],
                "primary_period": f"{params['primary_minutes']}min",
                
                "confirmation_volatility": confirmation_volatility["volatility"],
                "confirmation_category": confirmation_volatility["category"],
                "confirmation_period": f"{params['confirmation_minutes']}min",
                
                "reaction_volatility": reaction_volatility["volatility"],
                "reaction_category": reaction_volatility["category"],
                "reaction_period": f"{params['reaction_minutes']}min",
                
                "volatility_consensus": volatility_consensus,
                "strategy": strategy,
                "periods_used": {
                    "primary": f"{params['primary_minutes']} minutes",
                    "confirmation": f"{params['confirmation_minutes']} minutes",
                    "reaction": f"{params['reaction_minutes']} minutes"
                },
                "data_source": f"multi_timeframe_volatility_{strategy}"
            }
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe volatility calculation failed: {e}")
            return {
                "primary_volatility": 0.0,
                "primary_category": "ERROR",
                "volatility_consensus": "ERROR",
                "strategy": strategy,
                "error": str(e)
            }
    
    def _calculate_volatility_for_period(self, candles: List[Dict], period: int, 
                                       thresholds: Dict[str, float], timeframe_name: str) -> Dict[str, Any]:
        """Calculate volatility for a specific period"""
        try:
            # Use the most recent candles for the period
            period_candles = candles[-period:] if len(candles) >= period else candles
            
            if len(period_candles) < 1:
                return {"volatility": 0.0, "category": "ERROR"}
            
            # Calculate volatility using the same method as main function
            if len(period_candles) >= 2:
                all_highs = [c["high"] for c in period_candles if c["high"] > 0]
                all_lows = [c["low"] for c in period_candles if c["low"] > 0]
                
                if all_highs and all_lows:
                    max_high = max(all_highs)
                    min_low = min(all_lows)
                    total_range = max_high - min_low
                    avg_price = sum(c["close"] for c in period_candles if c["close"] > 0) / len([c for c in period_candles if c["close"] > 0])
                    
                    if avg_price > 0:
                        volatility = total_range / avg_price
                    else:
                        volatility = 0.0
                else:
                    volatility = 0.0
            else:
                volatility = 0.0
            
            # Categorize volatility
            if volatility >= thresholds["EXTREME"]:
                category = "EXTREME"
            elif volatility >= thresholds["HIGH"]:
                category = "HIGH"
            elif volatility >= thresholds["MODERATE"]:
                category = "MODERATE"
            elif volatility >= thresholds["LOW"]:
                category = "LOW"
            else:
                category = "VERY_LOW"
            
            return {
                "volatility": round(volatility, 6),
                "category": category,
                "period_candles": len(period_candles),
                "timeframe_name": timeframe_name
            }
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation for {timeframe_name} failed: {e}")
            return {"volatility": 0.0, "category": "ERROR"}
    
    def _determine_volatility_consensus(self, primary: Dict, confirmation: Dict, reaction: Dict) -> str:
        """Determine overall volatility consensus from multiple timeframes"""
        try:
            categories = [primary["category"], confirmation["category"], reaction["category"]]
            
            # Count volatility levels
            high_count = categories.count("HIGH") + categories.count("EXTREME")
            low_count = categories.count("LOW") + categories.count("VERY_LOW")
            moderate_count = categories.count("MODERATE")
            
            # Determine consensus
            if high_count >= 2:
                return "HIGH_VOLATILITY_CONSENSUS"
            elif low_count >= 2:
                return "LOW_VOLATILITY_CONSENSUS"
            elif moderate_count >= 2:
                return "MODERATE_VOLATILITY_CONSENSUS"
            else:
                return "MIXED_VOLATILITY"
                
        except Exception as e:
            logger.error(f"❌ Volatility consensus calculation failed: {e}")
            return "ERROR"
    
    def get_volatility_alerts(self, volatility_change_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate volatility alerts based on change detection
        
        Args:
            volatility_change_data: Result from detect_volatility_change()
            
        Returns:
            List of alert dictionaries for dashboard/logging
        """
        try:
            alerts = []
            
            if not volatility_change_data.get("change_detected", False):
                return alerts
            
            change_direction = volatility_change_data.get("change_direction", "NONE")
            change_magnitude = volatility_change_data.get("change_magnitude", 0.0)
            urgency = volatility_change_data.get("urgency", "LOW")
            current_volatility = volatility_change_data.get("current_volatility", 0.0)
            
            # Create alerts based on urgency
            if urgency in ["HIGH", "CRITICAL"]:
                alerts.append({
                    "type": "VOLATILITY_CHANGE",
                    "message": f"🚨 Volatility {change_direction}: {change_magnitude:+.1%}",
                    "urgency": urgency,
                    "details": {
                        "direction": change_direction,
                        "magnitude": change_magnitude,
                        "current_volatility": current_volatility,
                        "previous_volatility": volatility_change_data.get("previous_volatility", 0.0)
                    }
                })
            
            # Add specific alerts for extreme cases
            if change_direction == "EXTREME_SPIKE":
                alerts.append({
                    "type": "EXTREME_VOLATILITY",
                    "message": f"⚡ EXTREME volatility spike detected: {current_volatility*100:.2f}%",
                    "urgency": "CRITICAL",
                    "action_suggested": "Consider spike_hunting strategy"
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"❌ Volatility alert generation failed: {e}")
            return []
    
    def should_suggest_strategy_change(self, volatility_change_data: Dict[str, Any], 
                                     current_strategy: str) -> Optional[Dict[str, Any]]:
        """
        Determine if volatility change should suggest strategy switch
        
        Args:
            volatility_change_data: Result from detect_volatility_change()
            current_strategy: Current active strategy
            
        Returns:
            Dict with strategy suggestion or None
        """
        try:
            if not volatility_change_data.get("change_detected", False):
                return None
            
            change_direction = volatility_change_data.get("change_direction", "NONE")
            urgency = volatility_change_data.get("urgency", "LOW")
            
            # Suggest spike hunting for extreme volatility
            if urgency == "CRITICAL" and change_direction in ["EXTREME_SPIKE", "SPIKE_UP"]:
                if current_strategy != "spike_hunting":
                    return {
                        "suggested_strategy": "spike_hunting",
                        "reason": f"Extreme volatility detected ({change_direction})",
                        "confidence": 0.8,
                        "urgency": urgency
                    }
            
            # Suggest high volatility strategy for significant spikes
            elif urgency == "HIGH" and change_direction in ["SPIKE_UP", "SPIKE_DOWN"]:
                if current_strategy not in ["spike_hunting", "high_volatility"]:
                    return {
                        "suggested_strategy": "high_volatility",
                        "reason": f"High volatility detected ({change_direction})",
                        "confidence": 0.6,
                        "urgency": urgency
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Strategy suggestion evaluation failed: {e}")
            return None
    
    def _calculate_period_volatility(self, candles: List[Dict]) -> float:
        """Calculate volatility for a period of candles using weighted ranges"""
        try:
            if not candles or len(candles) == 0:
                return 0.0
            
            # Calculate weighted volatility with emphasis on recent candles
            weighted_ranges = []
            total_weight = 0
            
            for i, candle in enumerate(candles):
                if candle["close"] > 0 and candle["high"] > 0 and candle["low"] > 0:
                    range_vol = (candle["high"] - candle["low"]) / candle["close"]
                    # Give more weight to recent candles
                    weight = (i + 1) ** 1.5
                    weighted_ranges.append(range_vol * weight)
                    total_weight += weight
            
            if weighted_ranges and total_weight > 0:
                return sum(weighted_ranges) / total_weight
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"❌ Period volatility calculation failed: {e}")
            return 0.0
    
    
    
