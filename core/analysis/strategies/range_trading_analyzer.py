#!/usr/bin/env python3
"""
Range Trading Analyzer
=====================
Analyzes historical data to identify range trading opportunities and patterns.

RESPONSIBILITY (SRP): Range trading strategy analysis and recommendations
USED BY: Range trading strategies, StrategyManager for range trading decisions
"""

import time
import statistics
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class RangeTradingAnalyzer:
    """Analyzes historical data for range trading opportunities"""
    
    def __init__(self):
        logger.info("📊 Range Trading Analyzer initialized")
    
    def analyze_historical_ranges(self, candles_1d: List[Dict], candles_1h: List[Dict]) -> Dict[str, Any]:
        """
        Analyze historical data for range trading patterns
        
        INPUT: Daily and hourly candles (6.5 weeks of data)
        OUTPUT: Range trading analysis and recommendations
        """
        try:
            logger.info("🔍 Analyzing historical ranges for range trading...")
            
            if not candles_1d or len(candles_1d) < 30:
                logger.warning("⚠️ Insufficient daily data for range analysis")
                return self._get_default_range_analysis()
            
            # 1. RANGE DETECTION (Identify range-bound periods)
            range_periods = self._detect_range_periods(candles_1d, candles_1h)
            
            # 2. RANGE CHARACTERISTICS (Analyze range properties)
            range_characteristics = self._analyze_range_characteristics(range_periods)
            
            # 3. RANGE TRADING OPPORTUNITIES (Identify profitable ranges)
            trading_opportunities = self._identify_trading_opportunities(range_periods)
            
            # 4. RANGE STRATEGY RECOMMENDATIONS
            strategy_recommendations = self._recommend_range_strategies(
                range_characteristics, trading_opportunities
            )
            
            # Compile range analysis
            range_analysis = {
                "analysis_timestamp": time.time(),
                "data_period": f"{len(candles_1d)}_days",
                "range_periods": range_periods,
                "range_characteristics": range_characteristics,
                "trading_opportunities": trading_opportunities,
                "strategy_recommendations": strategy_recommendations,
                "range_trading_score": self._calculate_range_trading_score(range_characteristics)
            }
            
            logger.success("✅ Range analysis completed")
            return range_analysis
            
        except Exception as e:
            logger.error(f"❌ Range analysis failed: {e}")
            return self._get_default_range_analysis()
    
    def _detect_range_periods(self, candles_1d: List[Dict], candles_1h: List[Dict]) -> List[Dict[str, Any]]:
        """Detect range-bound periods in historical data"""
        range_periods = []
        
        # Analyze daily candles for range patterns
        for i in range(7, len(candles_1d)):  # Look at 7-day windows
            window = candles_1d[i-7:i]
            if self._is_range_period(window):
                range_period = {
                    "start_date": window[0].get("timestamp", 0),
                    "end_date": window[-1].get("timestamp", 0),
                    "duration_days": 7,
                    "high": max(c.get("high", 0) for c in window),
                    "low": min(c.get("low", 0) for c in window),
                    "range_size": self._calculate_range_size(window),
                    "volatility": self._calculate_period_volatility(window)
                }
                range_periods.append(range_period)
        
        return range_periods
    
    def _is_range_period(self, candles: List[Dict]) -> bool:
        """Determine if a period is range-bound"""
        if len(candles) < 5:
            return False
        
        # Calculate price range
        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]
        
        max_high = max(highs)
        min_low = min(lows)
        range_size = (max_high - min_low) / min_low if min_low > 0 else 0
        
        # Range criteria: small price movement, no clear trend
        return range_size < 0.05  # Less than 5% range over the period
    
    def _calculate_range_size(self, candles: List[Dict]) -> float:
        """Calculate the size of a range as percentage"""
        if not candles:
            return 0.0
        
        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]
        
        max_high = max(highs)
        min_low = min(lows)
        
        return (max_high - min_low) / min_low if min_low > 0 else 0.0
    
    def _calculate_period_volatility(self, candles: List[Dict]) -> float:
        """Calculate volatility for a period using centralized VolatilityCalculator"""
        if len(candles) < 2:
            return 0.0
        
        # Use centralized VolatilityCalculator (SINGLE SOURCE OF TRUTH)
        from core.calculations.volatility_calculator import create_volatility_calculator
        volatility_calculator = create_volatility_calculator("BTC")
        result = volatility_calculator.calculate_candle_volatility(candles, "5m", "standard")
        return result.get("volatility", 0.0) if isinstance(result, dict) else result
    
    def _analyze_range_characteristics(self, range_periods: List[Dict]) -> Dict[str, Any]:
        """Analyze characteristics of detected ranges"""
        if not range_periods:
            return {"total_ranges": 0, "avg_duration": 0, "avg_range_size": 0}
        
        durations = [r["duration_days"] for r in range_periods]
        range_sizes = [r["range_size"] for r in range_periods]
        volatilities = [r["volatility"] for r in range_periods]
        
        return {
            "total_ranges": len(range_periods),
            "avg_duration": statistics.mean(durations),
            "avg_range_size": statistics.mean(range_sizes),
            "avg_volatility": statistics.mean(volatilities),
            "range_frequency": len(range_periods) / 30,  # Ranges per month
            "most_common_duration": max(set(durations), key=durations.count) if durations else 0
        }
    
    def _identify_trading_opportunities(self, range_periods: List[Dict]) -> List[Dict[str, Any]]:
        """Identify profitable range trading opportunities"""
        opportunities = []
        
        for period in range_periods:
            # Score opportunity based on range characteristics
            score = self._score_range_opportunity(period)
            
            if score > 0.6:  # High-quality range
                opportunity = {
                    "period": period,
                    "score": score,
                    "profit_potential": period["range_size"] * 0.5,  # Estimate 50% of range as profit
                    "risk_level": "LOW" if period["volatility"] < 0.02 else "MEDIUM",
                    "recommended_strategy": "range_trading" if period["volatility"] < 0.02 else "low_volatility_range"
                }
                opportunities.append(opportunity)
        
        return opportunities
    
    def _score_range_opportunity(self, period: Dict) -> float:
        """Score a range period for trading opportunity"""
        score = 0.0
        
        # Duration score (7-14 days is optimal)
        duration = period["duration_days"]
        if 7 <= duration <= 14:
            score += 0.3
        elif 5 <= duration <= 21:
            score += 0.2
        
        # Range size score (2-5% is optimal)
        range_size = period["range_size"]
        if 0.02 <= range_size <= 0.05:
            score += 0.4
        elif 0.01 <= range_size <= 0.08:
            score += 0.2
        
        # Volatility score (low volatility is better for ranges)
        volatility = period["volatility"]
        if volatility < 0.02:
            score += 0.3
        elif volatility < 0.03:
            score += 0.2
        
        return min(score, 1.0)
    
    def _recommend_range_strategies(self, characteristics: Dict, opportunities: List[Dict]) -> Dict[str, Any]:
        """Recommend range trading strategies based on analysis"""
        recommendations = {
            "primary_strategy": "standard",
            "alternative_strategies": [],
            "confidence": 0.5
        }
        
        if characteristics["total_ranges"] > 5:  # Many ranges detected
            recommendations["primary_strategy"] = "range_trading"
            recommendations["confidence"] = 0.8
        elif characteristics["avg_volatility"] < 0.02:  # Low volatility
            recommendations["primary_strategy"] = "low_volatility_range"
            recommendations["confidence"] = 0.7
        
        # Add alternative strategies
        if characteristics["range_frequency"] > 0.3:  # High range frequency
            recommendations["alternative_strategies"].append("range_trading")
        
        return recommendations
    
    def _calculate_range_trading_score(self, characteristics: Dict) -> float:
        """Calculate overall range trading suitability score"""
        score = 0.0
        
        # Range frequency score
        if characteristics["range_frequency"] > 0.5:
            score += 0.4
        elif characteristics["range_frequency"] > 0.3:
            score += 0.2
        
        # Volatility score (lower is better for ranges)
        if characteristics["avg_volatility"] < 0.02:
            score += 0.3
        elif characteristics["avg_volatility"] < 0.03:
            score += 0.2
        
        # Duration score (7-14 days is optimal)
        avg_duration = characteristics["avg_duration"]
        if 7 <= avg_duration <= 14:
            score += 0.3
        elif 5 <= avg_duration <= 21:
            score += 0.2
        
        return min(score, 1.0)
    
    def _get_default_range_analysis(self) -> Dict[str, Any]:
        """Return default range analysis when data is insufficient"""
        return {
            "analysis_timestamp": time.time(),
            "data_period": "insufficient",
            "range_periods": [],
            "range_characteristics": {"total_ranges": 0, "avg_duration": 0, "avg_range_size": 0},
            "trading_opportunities": [],
            "strategy_recommendations": {"primary_strategy": "standard", "confidence": 0.5},
            "range_trading_score": 0.0
        }


# Global instance
_global_range_trading_analyzer = None

def get_global_range_trading_analyzer() -> RangeTradingAnalyzer:
    """Get the global RangeTradingAnalyzer singleton instance"""
    global _global_range_trading_analyzer
    if _global_range_trading_analyzer is None:
        _global_range_trading_analyzer = RangeTradingAnalyzer()
    return _global_range_trading_analyzer
