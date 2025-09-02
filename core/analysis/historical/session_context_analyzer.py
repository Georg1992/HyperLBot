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
from typing import Dict, Any, List, Tuple
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
                return self._get_default_context()
            
            # 1. MAJOR SUPPORT/RESISTANCE LEVELS (Critical for range trading)
            major_levels = self._identify_major_levels(candles_1d, candles_1h)
            
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
            return self._get_default_context()
    
    def _identify_major_levels(self, candles_1d: List[Dict], candles_1h: List[Dict]) -> Dict[str, Any]:
        """Identify major support/resistance levels from historical data"""
        try:
            # Get significant price levels from daily data
            daily_highs = [candle["high"] for candle in candles_1d]
            daily_lows = [candle["low"] for candle in candles_1d]
            
            # Find recurring levels (simplified approach)
            all_levels = daily_highs + daily_lows
            
            # Group levels by proximity (within 1% of each other)
            level_groups = self._group_nearby_levels(all_levels, proximity_pct=0.01)
            
            # Get strongest levels (most touches)
            major_resistance = sorted([level for level in level_groups if level > statistics.median(all_levels)])[:5]
            major_support = sorted([level for level in level_groups if level < statistics.median(all_levels)], reverse=True)[:5]
            
            return {
                "support": major_support,
                "resistance": major_resistance,
                "current_range": {
                    "low": min(daily_lows[-7:]),  # Last week's low
                    "high": max(daily_highs[-7:])  # Last week's high
                },
                "analysis_confidence": min(1.0, len(candles_1d) / 30)  # More data = higher confidence
            }
            
        except Exception as e:
            logger.error(f"❌ Major levels identification failed: {e}")
            return {"support": [], "resistance": [], "current_range": {"low": 0, "high": 0}, "analysis_confidence": 0.0}
    
    def _analyze_volatility_regime(self, candles_1d: List[Dict], candles_1h: List[Dict]) -> Dict[str, Any]:
        """Analyze historical volatility patterns to understand current regime"""
        try:
            # Calculate daily volatility for regime assessment
            daily_changes = []
            for i in range(1, len(candles_1d)):
                change_pct = abs(candles_1d[i]["close"] - candles_1d[i-1]["close"]) / candles_1d[i-1]["close"]
                daily_changes.append(change_pct)
            
            if not daily_changes:
                return {"regime": "UNKNOWN", "confidence": 0.0}
            
            avg_volatility = statistics.median(daily_changes)
            recent_volatility = statistics.median(daily_changes[-7:]) if len(daily_changes) >= 7 else avg_volatility
            
            # Volatility regime classification
            if avg_volatility < 0.02:  # <2% daily moves
                regime = "LOW_VOLATILITY"
                characteristics = "Ranging, consolidation periods"
            elif avg_volatility < 0.05:  # <5% daily moves
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
            # TODO: Implement sophisticated range analysis
            # - Identify historical ranges and their duration
            # - Success rate of range trading
            # - Typical range sizes
            # - Breakout patterns
            
            return {
                "typical_range_size_pct": 0.05,  # Placeholder: 5% typical ranges
                "range_success_rate": 0.65,      # Placeholder: 65% range trading success
                "average_range_duration": 7,     # Placeholder: 7 days average
                "analysis_ready": False          # TODO: Complete implementation
            }
            
        except Exception as e:
            logger.error(f"❌ Range analysis failed: {e}")
            return {"analysis_ready": False}
    
    def _recommend_strategies(self, major_levels: Dict, volatility_regime: Dict, 
                            market_regime: Dict, range_analysis: Dict) -> Dict[str, Any]:
        """Recommend optimal strategies based on historical context"""
        try:
            recommendations = {
                "primary": "standard",
                "secondary": "low_volatility", 
                "avoid": [],
                "reasoning": "Default recommendations"
            }
            
            # Strategy recommendations based on analysis
            if market_regime.get("regime") in ["RANGING", "TIGHT_RANGING"]:
                recommendations["primary"] = "range_trading"  # TODO: Implement
                recommendations["secondary"] = "micro_scalping"  # TODO: Implement
                recommendations["reasoning"] = f"Market in {market_regime.get('regime')} phase"
            
            if volatility_regime.get("regime") == "LOW_VOLATILITY":
                recommendations["avoid"].append("spike_hunting")
                recommendations["reasoning"] += " - Low volatility unsuitable for spike hunting"
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Strategy recommendation failed: {e}")
            return {"primary": "standard", "secondary": "low_volatility", "avoid": []}
    
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
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Get default context when analysis fails"""
        return {
            "analysis_timestamp": time.time(),
            "analysis_datetime": datetime.now().isoformat(),
            "data_period": "insufficient",
            "major_levels": {"support": [], "resistance": [], "analysis_confidence": 0.0},
            "volatility_regime": {"regime": "UNKNOWN", "confidence": 0.0},
            "market_regime": {"regime": "UNKNOWN", "confidence": 0.0},
            "range_analysis": {"analysis_ready": False},
            "strategy_recommendations": {"primary": "standard", "secondary": "low_volatility", "avoid": []},
            "risk_context": {"analysis_ready": False},
            "session_strategy_guidance": {"guidance_ready": False},
            "analysis_status": "FAILED"
        }