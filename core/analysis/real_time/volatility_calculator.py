#!/usr/bin/env python3
"""
Volatility Calculator Module
Centralized volatility calculations from different data sources
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from core.constants import VariabilityConstants


class VolatilityCalculator:
    """Centralized volatility calculation system"""
    
    def __init__(self):
        logger.info("📊 Volatility Calculator initialized")
    
    def calculate_candle_volatility(self, candles: List[Dict], timeframe: str = "5m") -> float:
        """Calculate volatility from candle data using HIGHLY REACTIVE method for real-time trading"""
        try:
            if len(candles) < 1:  # Allow single candle for current candle priority
                logger.warning(f"⚠️ Not enough candles for volatility calculation: {len(candles)} < 1")
                raise Exception(f"Insufficient candles for volatility calculation: {len(candles)} < 1")
            
            # Use the most recent 8 candles for better volatility detection (captures recent big moves)
            recent_candles = candles[-8:] if len(candles) >= 8 else candles
            
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
                
                # CURRENT CANDLE PRIORITY: Give 80% weight to the most recent candle (current ongoing candle)
                if len(recent_candles) >= 1:
                    current_candle_range = (recent_candles[-1]["high"] - recent_candles[-1]["low"]) / recent_candles[-1]["close"]
                    # Use 80% current candle + 20% historical average for maximum sensitivity
                    primary_volatility = (current_candle_range * 0.8) + (weighted_avg_volatility * 0.2)
                    logger.debug(f"🔍 Current candle priority: current_range={current_candle_range:.6f} ({current_candle_range*100:.4f}%), weighted_avg={weighted_avg_volatility:.6f}, final={primary_volatility:.6f} ({primary_volatility*100:.4f}%)")
                else:
                    # Fallback to maximum approach
                    primary_volatility = max(weighted_avg_volatility, max_volatility)
                
                # COMBINE: Use the HIGHER of overall movement or individual candle analysis
                primary_volatility = max(primary_volatility, overall_volatility)
                logger.debug(f"🔍 Combined volatility: {primary_volatility:.6f} ({primary_volatility*100:.4f}%) - overall={overall_volatility:.6f}, individual={primary_volatility:.6f}")
                
                # PRIORITY: If overall volatility is significantly higher, use it as the primary measure
                if overall_volatility > primary_volatility * 1.5:  # Overall is 50% higher
                    primary_volatility = overall_volatility
                    logger.debug(f"🔍 Using overall volatility as primary: {primary_volatility:.6f} ({primary_volatility*100:.4f}%)")
                    
                    # If overall volatility is high enough, return it immediately (no need for momentum calculation)
                    if overall_volatility > 0.003:  # Above HIGH threshold
                        logger.debug(f"🔍 Overall volatility is HIGH/EXTREME, returning immediately: {primary_volatility:.6f} ({primary_volatility*100:.4f}%)")
                        return round(primary_volatility, 6)
                else:
                    # Even if not significantly higher, check if overall volatility is high enough
                    if overall_volatility > 0.003:  # Above HIGH threshold
                        primary_volatility = overall_volatility
                        logger.debug(f"🔍 Overall volatility is HIGH/EXTREME, using as primary: {primary_volatility:.6f} ({primary_volatility*100:.4f}%)")
                        return round(primary_volatility, 6)
            else:
                # Fallback to overall volatility only
                primary_volatility = overall_volatility
                
                # If overall volatility is high enough, return it immediately
                if overall_volatility > 0.003:  # Above HIGH threshold
                    logger.debug(f"🔍 Overall volatility is HIGH/EXTREME, returning immediately: {primary_volatility:.6f} ({primary_volatility*100:.4f}%)")
                    return round(primary_volatility, 6)
                
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
                        return round(final_volatility, 6)
                
                return round(primary_volatility, 6)
            
            # Fallback: Calculate returns from close prices (original method)
            returns = []
            for i in range(1, len(candles)):
                if candles[i-1]["close"] > 0:
                    ret = (candles[i]["close"] - candles[i-1]["close"]) / candles[i-1]["close"]
                    returns.append(abs(ret))
            
            if not returns:
                raise Exception("No returns calculated for volatility analysis")
            
            # Use median for returns too (robust against outliers)
            returns.sort()
            n = len(returns)
            if n % 2 == 0:
                median_returns = (returns[n//2 - 1] + returns[n//2]) / 2
            else:
                median_returns = returns[n//2]
            
            return round(median_returns, 6)
            
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

    def categorize_volatility_for_trading(self, volatility: float, timeframe: str = "5m") -> tuple:
        """Categorize volatility for trading decisions using timeframe-specific thresholds"""
        try:
            # Import centralized constants for consistency
            # VariabilityConstants already imported at top
            
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
                # 5-minute thresholds (updated for realistic Bitcoin volatility)
                if volatility >= VariabilityConstants.VOLATILITY_5M_EXTREME:  # >= 0.50% (extreme 5m movement)
                    category = "EXTREME"
                    trend = "VOLATILE"
                elif volatility >= VariabilityConstants.VOLATILITY_5M_HIGH:    # >= 0.30% (high 5m activity)
                    category = "HIGH"
                    trend = "ACTIVE"
                elif volatility >= VariabilityConstants.VOLATILITY_5M_MODERATE:  # >= 0.15% (moderate 5m movement)
                    category = "MODERATE" 
                    trend = "NORMAL"
                elif volatility >= VariabilityConstants.VOLATILITY_5M_LOW:     # >= 0.06% (low 5m movement)
                    category = "LOW"
                    trend = "QUIET"
                elif volatility >= VariabilityConstants.VOLATILITY_5M_VERY_LOW: # >= 0.03% (very low 5m movement)
                    category = "LOW"
                    trend = "QUIET"
                else:                                                              # < 0.03% (extremely low 5m movement)
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
                # Default to 5m thresholds
                return self.categorize_volatility_for_trading(volatility, "5m")
            
            logger.debug(f"🔍 {timeframe} volatility categorized as: {category} ({trend})")
            
            return category, trend
            
        except Exception as e:
            logger.error(f"❌ {timeframe} volatility categorization failed: {e}")
            return "ERROR", "ERROR"
    
    
    
    
