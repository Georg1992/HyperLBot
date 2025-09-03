#!/usr/bin/env python3
"""
Market Conditions Analyzer
==========================
Determines when market conditions are suitable/unsuitable for trading

PURPOSE: Identify untradable conditions to avoid losses and false signals
FOCUS: Multiple condition checks (volatility, volume, trend, RSI zones)
INTEGRATION: Used by TradingEngine before making any trading decisions
"""

from typing import Dict, Any, Tuple
from loguru import logger
from core.constants import technical_constants


class MarketConditionsAnalyzer:
    """Analyzes market conditions to determine trading suitability"""
    
    def __init__(self):
        self.name = "MarketConditionsAnalyzer"
        logger.info("🔍 Market Conditions Analyzer initialized - Untradable condition detection")
    
    def analyze_trading_conditions(self, market_data: Dict[str, Any], 
                                 historical_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive market conditions analysis for trading decisions
        
        RETURNS: {
            "is_tradable": bool,
            "condition": str,  # EXCELLENT, GOOD, POOR, UNTRADABLE
            "reasons": [str],  # List of condition factors
            "risk_level": str, # LOW, MODERATE, HIGH, EXTREME
            "confidence": float # 0.0-1.0 confidence in analysis
        }
        """
        try:
            current_price = market_data.get("current_price", 0)
            rsi = market_data.get("rsi", 50.0)
            trend = market_data.get("trend", "NEUTRAL")
            volatility_5m = market_data.get("volatility_5m", 0.0)
            volatility_category = market_data.get("volatility_category", "MODERATE")
            volume_category = market_data.get("volume_category", "NORMAL")
            
            # Initialize analysis results
            condition_factors = []
            risk_factors = []
            positive_factors = []
            
            # 1. VOLATILITY CONDITIONS
            volatility_analysis = self._analyze_volatility_conditions(volatility_5m, volatility_category)
            condition_factors.extend(volatility_analysis["factors"])
            if volatility_analysis["risk"] > 0:
                risk_factors.extend(volatility_analysis["risk_factors"])
            if volatility_analysis["positive"]:
                positive_factors.extend(volatility_analysis["positive_factors"])
            
            # 2. VOLUME CONDITIONS  
            volume_analysis = self._analyze_volume_conditions(volume_category)
            condition_factors.extend(volume_analysis["factors"])
            if volume_analysis["risk"] > 0:
                risk_factors.extend(volume_analysis["risk_factors"])
            
            # 3. RSI CONDITIONS (dead zones, extreme conditions)
            rsi_analysis = self._analyze_rsi_conditions(rsi)
            condition_factors.extend(rsi_analysis["factors"])
            if rsi_analysis["risk"] > 0:
                risk_factors.extend(rsi_analysis["risk_factors"])
            
            # 4. TREND CONDITIONS
            trend_analysis = self._analyze_trend_conditions(trend)
            condition_factors.extend(trend_analysis["factors"])
            if trend_analysis["risk"] > 0:
                risk_factors.extend(trend_analysis["risk_factors"])
            
            # 5. HISTORICAL CONTEXT CONDITIONS
            context_analysis = self._analyze_historical_context(historical_context, current_price)
            condition_factors.extend(context_analysis["factors"])
            if context_analysis["risk"] > 0:
                risk_factors.extend(context_analysis["risk_factors"])
            
            # DEBUG: Log all analysis results before overall determination
            logger.debug(f"🔍 Analysis Summary: RSI={rsi:.1f}, Trend={trend}, Vol={volatility_category}")
            logger.debug(f"🔍 Total risk factors: {len(risk_factors)} - {risk_factors}")
            logger.debug(f"🔍 Total positive factors: {len(positive_factors)} - {positive_factors}")
            
            # DETERMINE OVERALL TRADABILITY
            overall_analysis = self._determine_overall_tradability(
                risk_factors, positive_factors, condition_factors
            )
            
            result = {
                "is_tradable": overall_analysis["is_tradable"],
                "condition": overall_analysis["condition"],
                "reasons": condition_factors,
                "risk_level": overall_analysis["risk_level"], 
                "confidence": overall_analysis["confidence"],
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "analysis_timestamp": market_data.get("timestamp", 0)
            }
            
            # Log important condition changes with DEBUG details
            if not overall_analysis["is_tradable"]:
                logger.warning(f"🚫 UNTRADABLE CONDITIONS: {overall_analysis['condition']}")
                logger.debug(f"🔍 Risk factors: {risk_factors}")
                logger.debug(f"🔍 All factors: {condition_factors}")
            elif overall_analysis["condition"] == "EXCELLENT":
                logger.success(f"🎯 EXCELLENT trading conditions: {', '.join(positive_factors[:2])}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Market conditions analysis failed: {e}")
            return self._get_default_conditions_analysis()
    
    def _analyze_volatility_conditions(self, volatility_5m: float, category: str) -> Dict[str, Any]:
        """Analyze volatility for trading suitability"""
        factors = []
        risk_factors = []
        positive_factors = []
        risk_level = 0
        
        if category == "VERY_LOW":
            factors.append("Very low volatility - range-bound market")
            risk_factors.append("Insufficient price movement for scalping")
            risk_level = 3  # High risk due to low movement
            
        elif category == "LOW":
            factors.append("Low volatility - limited opportunities") 
            risk_factors.append("Reduced profit potential")
            risk_level = 2
            
        elif category == "MODERATE":
            factors.append("Moderate volatility - good for trading")
            positive_factors.append("Optimal volatility for scalping")
            
        elif category == "HIGH":
            factors.append("High volatility - increased opportunities")
            positive_factors.append("Strong price movements available")
            
        elif category == "EXTREME":
            factors.append("Extreme volatility - high risk/reward")
            risk_factors.append("Unpredictable price swings")
            risk_level = 2
            
        return {
            "factors": factors,
            "risk": risk_level,
            "risk_factors": risk_factors,
            "positive": len(positive_factors) > 0,
            "positive_factors": positive_factors
        }
    
    def _analyze_volume_conditions(self, volume_category: str) -> Dict[str, Any]:
        """Analyze volume for trading suitability"""
        factors = []
        risk_factors = []
        risk_level = 0
        
        if volume_category in ["VERY_LOW", "LOW"]:
            factors.append(f"{volume_category.lower().replace('_', ' ').title()} volume - limited liquidity")
            risk_factors.append("Slippage risk due to low liquidity")
            risk_level = 2
            
        elif volume_category == "NORMAL":
            factors.append("Normal volume - adequate liquidity")
            
        elif volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            factors.append(f"{volume_category.lower().replace('_', ' ').title()} volume - strong market interest")
            
        return {
            "factors": factors,
            "risk": risk_level,
            "risk_factors": risk_factors,
            "positive": volume_category in ["HIGH", "VERY_HIGH"],
            "positive_factors": []
        }
    
    def _analyze_rsi_conditions(self, rsi: float) -> Dict[str, Any]:
        """Analyze RSI for trading suitability"""
        factors = []
        risk_factors = []
        risk_level = 0
        
        # DEBUG: Log RSI analysis for troubleshooting
        logger.debug(f"🔍 RSI Analysis: RSI={rsi:.1f}")
        
        if 45 <= rsi <= 55:
            factors.append("RSI in neutral zone - unclear directional bias")
            risk_factors.append("RSI dead zone - no clear signal")
            risk_level = 2
            logger.debug(f"🔍 RSI: Dead zone detected (45-55 range)")
            
        elif rsi <= 25 or rsi >= 75:
            factors.append(f"RSI extreme zone ({rsi:.1f}) - potential reversal risk")
            risk_factors.append("Extreme RSI - reversal risk")
            risk_level = 1
            logger.debug(f"🔍 RSI: Extreme zone detected (<25 or >75)")
            
        elif rsi <= 35:
            factors.append(f"RSI oversold ({rsi:.1f}) - bullish potential")
            logger.debug(f"🔍 RSI: Oversold condition detected (<=35)")
            
        elif rsi >= 65:
            factors.append(f"RSI overbought ({rsi:.1f}) - bearish potential")
            logger.debug(f"🔍 RSI: Overbought condition detected (>=65)")
        else:
            factors.append(f"RSI in tradable range ({rsi:.1f})")
            logger.debug(f"🔍 RSI: Tradable range (35-65, not 45-55 dead zone)")
            
        return {
            "factors": factors,
            "risk": risk_level,
            "risk_factors": risk_factors,
            "positive": rsi <= 35 or rsi >= 65,  # Oversold/overbought are positive signals
            "positive_factors": ["Strong RSI signal"] if (rsi <= 35 or rsi >= 65) else []
        }
    
    def _analyze_trend_conditions(self, trend: str) -> Dict[str, Any]:
        """Analyze trend for trading suitability"""
        factors = []
        risk_factors = []
        risk_level = 0
        
        if trend == "SIDEWAYS":
            factors.append("Sideways trend - range-bound market")
            risk_factors.append("No clear directional momentum")
            risk_level = 2
            
        elif trend in ["WEAK_UPTREND", "WEAK_DOWNTREND"]:
            factors.append(f"{trend.replace('_', ' ').lower()} - limited momentum")
            risk_factors.append("Weak trend strength")
            risk_level = 1
            
        elif trend in ["UPTREND", "DOWNTREND"]:
            factors.append(f"{trend.lower()} - good directional momentum")
            
        elif trend in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
            factors.append(f"{trend.replace('_', ' ').lower()} - excellent momentum")
            
        else:  # NEUTRAL or unknown
            factors.append("Neutral trend - no clear direction")
            risk_factors.append("Unclear market direction")
            risk_level = 1
            
        return {
            "factors": factors,
            "risk": risk_level,
            "risk_factors": risk_factors,
            "positive": trend in ["UPTREND", "DOWNTREND", "STRONG_UPTREND", "STRONG_DOWNTREND"],
            "positive_factors": []
        }
    
    def _analyze_historical_context(self, historical_context: Dict[str, Any], 
                                  current_price: float) -> Dict[str, Any]:
        """Analyze historical context for trading suitability"""
        factors = []
        risk_factors = []
        risk_level = 0
        
        if not historical_context:
            factors.append("No historical context - limited insight")
            risk_level = 1
            return {
                "factors": factors,
                "risk": risk_level, 
                "risk_factors": ["Missing historical context"],
                "positive": False,
                "positive_factors": []
            }
        
        # Check market regime from historical analysis
        market_regime = historical_context.get("market_regime", {})
        regime = market_regime.get("regime", "UNKNOWN")
        
        if regime == "TIGHT_RANGING":
            factors.append("Historical tight ranging - limited breakouts")
            risk_factors.append("Historically range-bound market")
            risk_level = 2
            
        elif regime == "RANGING":
            factors.append("Historical ranging market - trade the range")
            risk_level = 1
            
        elif regime in ["TRENDING_UP", "TRENDING_DOWN"]:
            factors.append(f"Historical {regime.replace('_', ' ').lower()} - trend trading suitable")
            
        elif regime == "HIGH_VOLATILITY":
            factors.append("Historical high volatility - increased opportunities")
            
        # Check proximity to major support/resistance levels
        major_levels = historical_context.get("major_levels", {})
        support_levels = major_levels.get("support", [])
        resistance_levels = major_levels.get("resistance", [])
        
        if support_levels or resistance_levels:
            all_levels = support_levels + resistance_levels
            nearest_level = min(all_levels, key=lambda x: abs(current_price - x))
            distance_pct = abs(current_price - nearest_level) / current_price
            
            if distance_pct < 0.005:  # Within 0.5% of major level
                factors.append("Near major S/R level - breakout/bounce potential")
            
        return {
            "factors": factors,
            "risk": risk_level,
            "risk_factors": risk_factors,
            "positive": regime in ["TRENDING_UP", "TRENDING_DOWN", "HIGH_VOLATILITY"],
            "positive_factors": []
        }
    
    def _determine_overall_tradability(self, risk_factors: list, positive_factors: list, 
                                     condition_factors: list) -> Dict[str, Any]:
        """Determine overall market tradability"""
        
        total_risk_score = len(risk_factors)
        total_positive_score = len(positive_factors)
        
        # DEBUG: Log tradability decision process
        logger.debug(f"🔍 Tradability Decision: {total_risk_score} risk factors, {total_positive_score} positive factors")
        
        # UNTRADABLE CONDITIONS (high risk, multiple problems)
        if total_risk_score >= 3:
            logger.debug(f"🔍 UNTRADABLE: {total_risk_score} ≥ 3 risk factors")
            return {
                "is_tradable": False,
                "condition": "UNTRADABLE",
                "risk_level": "EXTREME",
                "confidence": 0.9
            }
        
        # POOR CONDITIONS (some risk factors)
        elif total_risk_score >= 2:
            logger.debug(f"🔍 POOR: {total_risk_score} ≥ 2 risk factors")
            return {
                "is_tradable": False,
                "condition": "POOR",
                "risk_level": "HIGH", 
                "confidence": 0.75
            }
        
        # EXCELLENT CONDITIONS (multiple positive factors, low risk)
        elif total_positive_score >= 2 and total_risk_score == 0:
            return {
                "is_tradable": True,
                "condition": "EXCELLENT",
                "risk_level": "LOW",
                "confidence": 0.85
            }
        
        # GOOD CONDITIONS (some positive factors, minimal risk)
        elif total_positive_score >= 1 and total_risk_score <= 1:
            return {
                "is_tradable": True,
                "condition": "GOOD", 
                "risk_level": "MODERATE",
                "confidence": 0.7
            }
        
        # MARGINAL CONDITIONS (neutral, proceed with caution)
        else:
            return {
                "is_tradable": True,  # Allow trading but with lower confidence
                "condition": "MARGINAL",
                "risk_level": "MODERATE",
                "confidence": 0.5
            }
    
    def _get_default_conditions_analysis(self) -> Dict[str, Any]:
        """Default analysis when conditions check fails"""
        return {
            "is_tradable": False,
            "condition": "UNKNOWN",
            "reasons": ["Analysis failed - defaulting to no trading"],
            "risk_level": "EXTREME",
            "confidence": 0.0,
            "risk_factors": ["Analysis error"],
            "positive_factors": [],
            "analysis_timestamp": 0
        }
    
    def get_untradable_condition_summary(self, analysis: Dict[str, Any]) -> str:
        """Generate user-friendly summary of why conditions are untradable"""
        if analysis.get("is_tradable", True):
            return ""
        
        condition = analysis.get("condition", "UNKNOWN")
        main_risks = analysis.get("risk_factors", [])[:2]  # Top 2 risk factors
        
        if condition == "UNTRADABLE":
            return f"Market unsuitable for trading: {', '.join(main_risks)}"
        elif condition == "POOR": 
            return f"Poor trading conditions: {', '.join(main_risks)}"
        else:
            return f"Conditions analysis unavailable"

# Global instance for consistent conditions analysis across the system
global_conditions_analyzer = MarketConditionsAnalyzer()