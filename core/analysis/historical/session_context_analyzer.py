#!/usr/bin/env python3
"""
Session Context Analyzer
=======================
Analyzes 6.5 weeks of historical data to provide strategic context for the trading session.

RESPONSIBILITY (SRP): Historical market context analysis for session-level strategy decisions
COMPUTED: Once per session during initialization (expensive operation)
USED BY: TradingEngine, strategies for better decision making
"""

import time
import statistics
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger
from datetime import datetime, timedelta


class SessionContextAnalyzer:
    """Analyzes long-term historical data to provide strategic context for the session"""
    
    def __init__(self):
        logger.info("📊 Session Context Analyzer initialized - Long-term historical analysis")
    
    def analyze_session_context(self, candles_1d: List[Dict], candles_1h: List[Dict], candles_5m: List[Dict]) -> Dict[str, Any]:
        """
        Analyze 6.5 weeks of historical data to provide strategic session context
        
        INPUT: 45×1d, 84×1h, 30×5m candles (6.5 weeks of data)
        OUTPUT: Strategic context for session-level decisions
        """
        try:
            logger.info("🔍 Computing session historical context (6.5 weeks analysis)...")
            
            if not candles_1d or len(candles_1d) < 30:
                logger.warning("⚠️ Insufficient daily data for historical context")
                raise Exception("Insufficient daily data for historical context")
            
            # 1. MAJOR SUPPORT/RESISTANCE LEVELS (Critical for range trading)
            major_levels = self._identify_major_levels(candles_1d, candles_1h, candles_5m)
            
            # 2. VOLATILITY REGIME ANALYSIS 
            volatility_regime = self._analyze_volatility_regime(candles_1d, candles_1h)
            
            # 3. MARKET REGIME IDENTIFICATION
            market_regime = self._identify_market_regime(candles_1d, candles_1h)
            
            # 4. RANGE ANALYSIS (BTC loves to range!)
            range_analysis = self._analyze_historical_ranges(candles_1d, candles_1h)
            
            # 5. STRATEGY RECOMMENDATIONS
            strategy_recommendations = self._recommend_strategies(
                major_levels, volatility_regime, market_regime, range_analysis
            )
            
            # 6. RISK CONTEXT
            risk_context = self._analyze_risk_context(candles_1d)
            
            # Compile comprehensive session context
            session_context = {
                "analysis_timestamp": time.time(),
                "analysis_datetime": datetime.now().isoformat(),
                "data_period": "6.5_weeks",
                "data_summary": {
                    "daily_candles": len(candles_1d),
                    "hourly_candles": len(candles_1h),
                    "5m_candles": len(candles_5m)
                },
                "major_levels": major_levels,
                "volatility_regime": volatility_regime,
                "market_regime": market_regime,
                "range_analysis": range_analysis,
                "strategy_recommendations": strategy_recommendations,
                "risk_context": risk_context,
                "session_strategy_guidance": self._generate_session_guidance(
                    major_levels, market_regime, range_analysis
                )
            }
            
            logger.success(f"✅ Session context computed: {market_regime['regime']} regime, {len(major_levels['support'])} S/R levels")
            return session_context
            
        except Exception as e:
            logger.error(f"❌ Session context analysis failed: {e}")
            raise Exception(f"Session context analysis failed: {e}")
    
    def _identify_major_levels(self, candles_1d: List[Dict], candles_1h: List[Dict], candles_5m: List[Dict] = None) -> Dict[str, Any]:
        """Identify major support/resistance levels from historical data using multi-factor detection"""
        try:
            # Use the SupportResistanceCalculator for level detection
            from core.analysis.real_time.support_resistance_calculator import SupportResistanceCalculator
            sr_calculator = SupportResistanceCalculator()
            
            # 1. DAILY LEVELS (Major long-term support/resistance)
            daily_levels = sr_calculator.identify_key_levels(candles_1d, min_touches=2) if candles_1d else {"key_levels": [], "strongest_support": 0.0, "strongest_resistance": 0.0}
            
            # 2. HOURLY LEVELS (Medium-term levels like $116,650-116,750)
            hourly_levels = sr_calculator.identify_key_levels(candles_1h, min_touches=3) if candles_1h and len(candles_1h) >= 20 else {"key_levels": [], "strongest_support": 0.0, "strongest_resistance": 0.0}
            
            # 3. 5-MINUTE RANGE LEVELS (Short-term for range trading)
            range_levels = self._identify_5m_range_levels(candles_5m) if candles_5m else {"support": [], "resistance": []}
            
            # Combine all levels with priority weighting
            all_key_levels = []
            
            # Add daily levels (highest priority)
            for level in daily_levels.get("key_levels", []):
                level["priority"] = "daily"
                level["timeframe"] = "1d"
                all_key_levels.append(level)
            
            # Add hourly levels (medium priority) - these should catch $116,650-116,750
            for level in hourly_levels.get("key_levels", []):
                level["priority"] = "hourly"
                level["timeframe"] = "1h"
                all_key_levels.append(level)
            
            # Add 5m range levels (lowest priority)
            for level in range_levels.get("support", []):
                all_key_levels.append({"level": level, "type": "support", "touches": 2, "priority": "5m", "timeframe": "5m"})
            for level in range_levels.get("resistance", []):
                all_key_levels.append({"level": level, "type": "resistance", "touches": 2, "priority": "5m", "timeframe": "5m"})
            
            # Sort by strength (touches) and priority
            all_key_levels.sort(key=lambda x: (x.get("touches", 0), x.get("priority", "5m")), reverse=True)
            
            # Separate support and resistance
            support_levels = [lvl for lvl in all_key_levels if lvl["type"] == "support"]
            resistance_levels = [lvl for lvl in all_key_levels if lvl["type"] == "resistance"]
            
            # Get strongest levels
            strongest_support = support_levels[0]["level"] if support_levels else 0.0
            strongest_resistance = resistance_levels[0]["level"] if resistance_levels else 0.0
            
            # Get current range from daily data
            daily_highs = [candle["high"] for candle in candles_1d] if candles_1d else []
            daily_lows = [candle["low"] for candle in candles_1d] if candles_1d else []
            
            return {
                "support": [lvl["level"] for lvl in support_levels[:5]],  # Top 5 support levels
                "resistance": [lvl["level"] for lvl in resistance_levels[:5]],  # Top 5 resistance levels
                "key_levels": all_key_levels[:10],  # Top 10 key levels with metadata
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "current_range": {
                    "low": min(daily_lows[-7:]) if daily_lows else 0,  # Last week's low
                    "high": max(daily_highs[-7:]) if daily_highs else 0  # Last week's high
                },
                "range_levels": range_levels,  # 5-minute range levels for range trading
                "analysis_confidence": min(1.0, len(candles_1d) / 30) if candles_1d else 0.0,  # More data = higher confidence
                "timeframes_analyzed": {
                    "daily": len(candles_1d) if candles_1d else 0,
                    "hourly": len(candles_1h) if candles_1h else 0,
                    "5min": len(candles_5m) if candles_5m else 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Major levels identification failed: {e}")
            return {"support": [], "resistance": [], "current_range": {"low": 0, "high": 0}, "analysis_confidence": 0.0}
    
    def _identify_5m_range_levels(self, candles_5m: List[Dict]) -> Dict[str, Any]:
        """Identify support/resistance levels from 5-minute data for range trading"""
        try:
            if not candles_5m or len(candles_5m) < 20:
                return {"support": [], "resistance": []}
            
            # Get recent 5-minute data (last 4 hours = 48 candles)
            recent_candles = candles_5m[-48:] if len(candles_5m) >= 48 else candles_5m
            
            # Extract price levels
            highs = [candle["high"] for candle in recent_candles]
            lows = [candle["low"] for candle in recent_candles]
            
            # Find the current range (min/max of recent data)
            range_low = min(lows)
            range_high = max(highs)
            range_width = range_high - range_low
            
            # Get current price for level classification
            current_price = recent_candles[-1]["close"]
            
            # Remove the restrictive range condition - Bitcoin naturally has >1% ranges
            # This was preventing detection of valid support/resistance levels
            
            # Find levels that have been tested multiple times
            support_levels = []
            resistance_levels = []
            
            # PRECISE: Use clustering approach for exact level detection
            from core.analysis.real_time.support_resistance_calculator import SupportResistanceCalculator
            sr_calculator = SupportResistanceCalculator()
            
            # Calculate precise levels using the new method structure
            price_range = max(highs) - min(lows)
            level_tolerance = price_range * 0.001  # 0.1% tolerance for precision
            
            # Use the simple identify_key_levels method
            sr_result = sr_calculator.identify_key_levels(recent_candles, min_touches=2)
            support_levels_data = [level for level in sr_result.get("key_levels", []) if level["type"] == "support"]
            resistance_levels_data = [level for level in sr_result.get("key_levels", []) if level["type"] == "resistance"]
            
            # Combine the results
            precise_levels = support_levels_data + resistance_levels_data
            
            # Extract support and resistance levels
            for level_data in precise_levels:
                level = level_data["level"]
                if level_data["type"] == "support":
                    support_levels.append(level)
                elif level_data["type"] == "resistance":
                    resistance_levels.append(level)
            
            # Sort and limit to most relevant levels
            support_levels = sorted(list(set(support_levels)), reverse=True)[:3]
            resistance_levels = sorted(list(set(resistance_levels)))[:3]
            
            logger.info(f"🎯 5m Range Levels: Support={support_levels}, Resistance={resistance_levels}")
            logger.info(f"   Current Price: {current_price}, Range: {range_low}-{range_high} (width: {range_width:.2f})")
            logger.info(f"   Valid Resistance: {[level for level in resistance_levels if level > current_price]}")
            
            return {
                "support": support_levels,
                "resistance": resistance_levels
            }
            
        except Exception as e:
            logger.error(f"❌ 5m range levels identification failed: {e}")
            return {"support": [], "resistance": []}
    
    def _analyze_volatility_regime(self, candles_1d: List[Dict], candles_1h: List[Dict]) -> Dict[str, Any]:
        """Analyze historical volatility patterns to understand current regime"""
        try:
            # Use centralized MarketDataManager for consistent volatility calculation
            from core.market_data_manager import market_data_manager
            
            if not candles_1d or len(candles_1d) < 2:
                return {"regime": "UNKNOWN", "confidence": 0.0}
            
            # Calculate daily volatility using the same method as VolatilityCalculator
            avg_volatility = market_data_manager.calculate_volatility(candles_1d, len(candles_1d))
            recent_volatility = market_data_manager.calculate_volatility(candles_1d[-7:], 7) if len(candles_1d) >= 7 else avg_volatility
            
            # Volatility regime classification using centralized constants (adjusted for daily timeframe)
            from core.constants import VariabilityConstants
            
            # Convert 5m thresholds to daily thresholds (multiply by ~20 for daily timeframe)
            daily_very_low = VariabilityConstants.VOLATILITY_5M_VERY_LOW * 20  # 0.1% * 20 = 2%
            daily_low = VariabilityConstants.VOLATILITY_5M_LOW * 20            # 0.25% * 20 = 5%
            daily_moderate = VariabilityConstants.VOLATILITY_5M_MODERATE * 20  # 0.5% * 20 = 10%
            
            if avg_volatility < daily_very_low:  # <2% daily moves
                regime = "LOW_VOLATILITY"
                characteristics = "Ranging, consolidation periods"
            elif avg_volatility < daily_low:  # <5% daily moves
                regime = "MODERATE_VOLATILITY"
                characteristics = "Normal trading activity"
            else:  # >5% daily moves
                regime = "HIGH_VOLATILITY"
                characteristics = "Active trending or major events"
            
            return {
                "regime": regime,
                "average_volatility": avg_volatility,
                "recent_volatility": recent_volatility,
                "characteristics": characteristics,
                "confidence": 0.8  # High confidence with 6.5 weeks data
            }
            
        except Exception as e:
            logger.error(f"❌ Volatility regime analysis failed: {e}")
            return {"regime": "UNKNOWN", "confidence": 0.0}
    
    def _identify_market_regime(self, candles_1d: List[Dict], candles_1h: List[Dict]) -> Dict[str, Any]:
        """Identify current market regime (RANGING/TRENDING/TRANSITIONAL)"""
        try:
            # Analyze recent price action for regime identification
            recent_closes = [candle["close"] for candle in candles_1d[-14:]]  # Last 2 weeks
            
            if len(recent_closes) < 7:
                return {"regime": "UNKNOWN", "confidence": 0.0}
            
            price_range_pct = (max(recent_closes) - min(recent_closes)) / min(recent_closes)
            
            # Simple regime identification
            if price_range_pct < 0.1:  # <10% range over 2 weeks
                regime = "TIGHT_RANGING"
                description = "Price consolidating in tight range"
            elif price_range_pct < 0.2:  # <20% range over 2 weeks  
                regime = "RANGING"
                description = "Price trading in established range"
            else:  # >20% range
                regime = "TRENDING"
                description = "Price showing directional movement"
            
            return {
                "regime": regime,
                "description": description,
                "price_range_pct": price_range_pct,
                "confidence": 0.7
            }
            
        except Exception as e:
            logger.error(f"❌ Market regime identification failed: {e}")
            return {"regime": "UNKNOWN", "confidence": 0.0}
    
    def _analyze_historical_ranges(self, candles_1d: List[Dict], candles_1h: List[Dict]) -> Dict[str, Any]:
        """Analyze historical ranging behavior for range trading strategy"""
        try:
            if not candles_1d or len(candles_1d) < 7:
                return {"ranges": [], "avg_range_duration": 0, "range_success_rate": 0.0}
            
            # Analyze recent daily ranges
            ranges = []
            current_range_start = 0
            current_range_high = candles_1d[0]["high"]
            current_range_low = candles_1d[0]["low"]
            
            for i, candle in enumerate(candles_1d[1:], 1):
                # Check if price broke out of current range
                if candle["high"] > current_range_high * 1.02 or candle["low"] < current_range_low * 0.98:
                    # Range ended, record it
                    range_duration = i - current_range_start
                    range_size = (current_range_high - current_range_low) / current_range_low
                    
                    ranges.append({
                        "start_index": current_range_start,
                        "end_index": i,
                        "duration_days": range_duration,
                        "high": current_range_high,
                        "low": current_range_low,
                        "size_pct": range_size * 100,
                        "breakout_direction": "up" if candle["high"] > current_range_high * 1.02 else "down"
                    })
                    
                    # Start new range
                    current_range_start = i
                    current_range_high = candle["high"]
                    current_range_low = candle["low"]
                else:
                    # Update current range
                    current_range_high = max(current_range_high, candle["high"])
                    current_range_low = min(current_range_low, candle["low"])
            
            # Add the last range if it exists
            if current_range_start < len(candles_1d) - 1:
                range_duration = len(candles_1d) - 1 - current_range_start
                range_size = (current_range_high - current_range_low) / current_range_low
                ranges.append({
                    "start_index": current_range_start,
                    "end_index": len(candles_1d) - 1,
                    "duration_days": range_duration,
                    "high": current_range_high,
                    "low": current_range_low,
                    "size_pct": range_size * 100,
                    "breakout_direction": "ongoing"
                })
            
            # Calculate statistics
            avg_duration = sum(r["duration_days"] for r in ranges) / len(ranges) if ranges else 0
            avg_size = sum(r["size_pct"] for r in ranges) / len(ranges) if ranges else 0
            
            # Calculate success rate (ranges that held for at least 3 days)
            successful_ranges = [r for r in ranges if r["duration_days"] >= 3]
            success_rate = len(successful_ranges) / len(ranges) if ranges else 0.0
            
            return {
                "ranges": ranges[-5:],  # Last 5 ranges
                "avg_range_duration": avg_duration,
                "avg_range_size_pct": avg_size,
                "range_success_rate": success_rate,
                "total_ranges_analyzed": len(ranges),
                "analysis_ready": True
            }
            
        except Exception as e:
            logger.error(f"❌ Range analysis failed: {e}")
            return {"ranges": [], "avg_range_duration": 0, "range_success_rate": 0.0, "analysis_ready": False}
    
    def _recommend_strategies(self, major_levels: Dict, volatility_regime: Dict, 
                            market_regime: Dict, range_analysis: Dict) -> Dict[str, Any]:
        """Recommend optimal strategies based on historical context"""
        try:
            recommendations = {
                "primary": "standard",
                "secondary": "low_volatility_range", 
                "avoid": [],
                "reasoning": "Default recommendations"
            }
            
            # Strategy recommendations based on analysis
            if market_regime.get("regime") in ["RANGING", "TIGHT_RANGING"]:
                recommendations["primary"] = "low_volatility_range"
                recommendations["secondary"] = "scalping"  # Use scalping as secondary strategy
                recommendations["reasoning"] = f"Market in {market_regime.get('regime')} phase"
            
            if volatility_regime.get("regime") == "LOW_VOLATILITY":
                recommendations["avoid"].append("spike_hunting")
                recommendations["reasoning"] += " - Low volatility unsuitable for spike hunting"
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Strategy recommendation failed: {e}")
            return {"primary": "standard", "secondary": "low_volatility_range", "avoid": []}
    
    def _analyze_risk_context(self, candles_1d: List[Dict]) -> Dict[str, Any]:
        """Analyze historical risk patterns for position sizing and risk management"""
        try:
            # Calculate maximum drawdowns and recovery patterns
            closes = [candle["close"] for candle in candles_1d]
            
            if len(closes) < 7:
                return {"max_drawdown_pct": 0.0, "analysis_ready": False}
            
            # Simple max drawdown calculation
            max_drawdown = 0.0
            peak = closes[0]
            
            for price in closes:
                if price > peak:
                    peak = price
                else:
                    drawdown = (peak - price) / peak
                    max_drawdown = max(max_drawdown, drawdown)
            
            return {
                "max_drawdown_pct": max_drawdown,
                "recent_volatility": statistics.stdev(closes[-7:]) / statistics.median(closes[-7:]),
                "analysis_ready": True
            }
            
        except Exception as e:
            logger.error(f"❌ Risk context analysis failed: {e}")
            return {"analysis_ready": False}
    
    def _generate_session_guidance(self, major_levels: Dict, market_regime: Dict, range_analysis: Dict) -> Dict[str, Any]:
        """Generate session-specific trading guidance"""
        try:
            return {
                "session_focus": market_regime.get("regime", "STANDARD"),
                "key_levels_to_watch": major_levels.get("support", [])[:3] + major_levels.get("resistance", [])[:3],
                "optimal_timeframes": ["5m", "1h"] if market_regime.get("regime") == "RANGING" else ["5m"],
                "guidance_ready": True
            }
        except Exception as e:
            logger.error(f"❌ Session guidance generation failed: {e}")
            return {"guidance_ready": False}
    
    def _group_nearby_levels(self, levels: List[float], proximity_pct: float = 0.01) -> List[float]:
        """Group price levels that are within proximity_pct of each other"""
        try:
            if not levels:
                return []
            
            sorted_levels = sorted(levels)
            groups = []
            current_group = [sorted_levels[0]]
            
            for level in sorted_levels[1:]:
                # Check if level is within proximity of current group
                group_avg = statistics.median(current_group)
                if abs(level - group_avg) / group_avg <= proximity_pct:
                    current_group.append(level)
                else:
                    # Finalize current group and start new one
                    if len(current_group) >= 2:  # Only keep levels touched multiple times
                        groups.append(statistics.median(current_group))
                    current_group = [level]
            
            # Don't forget the last group
            if len(current_group) >= 2:
                groups.append(statistics.median(current_group))
            
            return groups
            
        except Exception as e:
            logger.error(f"❌ Level grouping failed: {e}")
            return []
    
