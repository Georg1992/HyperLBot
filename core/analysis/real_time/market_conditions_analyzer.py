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
from core.external.fear_greed_api import fear_greed_api
from core.external.whale_analytics_api import whale_analytics_api
from core.external.rss_news_api import rss_news_api


class MarketConditionsAnalyzer:
    """Analyzes market conditions to determine trading suitability"""
    
    def __init__(self):
        self.name = "MarketConditionsAnalyzer"
        logger.info("🔍 Market Conditions Analyzer initialized - Untradable condition detection")
    
    def analyze_trading_conditions(self, market_data: Dict[str, Any], 
                                 historical_context: Dict[str, Any] = None, candles_1d=None) -> Dict[str, Any]:
        """
        Comprehensive market conditions analysis for trading decisions
        
        RETURNS: {
            "condition": str,  # EXCELLENT, GOOD, FAIR, POOR
            "reasons": [str],  # List of condition factors
            "risk_level": str, # LOW, MODERATE, HIGH, EXTREME
            "confidence": float, # 0.0-1.0 confidence in analysis
            "market_status": str  # BEARISH/NEUTRAL/BULLISH based on 7-day trend
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
            
            # 1. VOLATILITY CONDITIONS (strategy-independent)
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
            
            # 3. FEAR & GREED SENTIMENT CONDITIONS
            sentiment_analysis = self._analyze_sentiment_conditions()
            condition_factors.extend(sentiment_analysis["factors"])
            if sentiment_analysis["risk"] > 0:
                risk_factors.extend(sentiment_analysis["risk_factors"])
            if sentiment_analysis["positive"]:
                positive_factors.extend(sentiment_analysis["positive_factors"])
            
            # 4. WHALE ANALYTICS CONDITIONS
            whale_analysis = self._analyze_whale_conditions()
            condition_factors.extend(whale_analysis["factors"])
            if whale_analysis["risk"] > 0:
                risk_factors.extend(whale_analysis["risk_factors"])
            if whale_analysis["positive"]:
                positive_factors.extend(whale_analysis["positive_factors"])
            
            # 5. RSS NEWS SENTIMENT CONDITIONS
            news_analysis = self._analyze_rss_news_conditions()
            condition_factors.extend(news_analysis["factors"])
            if news_analysis["risk"] > 0:
                risk_factors.extend(news_analysis["risk_factors"])
            if news_analysis["positive"]:
                positive_factors.extend(news_analysis["positive_factors"])
            
            # 6. RSI CONDITIONS (dead zones, extreme conditions)
            rsi_analysis = self._analyze_rsi_conditions(rsi)
            condition_factors.extend(rsi_analysis["factors"])
            if rsi_analysis["risk"] > 0:
                risk_factors.extend(rsi_analysis["risk_factors"])
            if rsi_analysis["positive"]:
                positive_factors.extend(rsi_analysis["positive_factors"])
            
            # Store neutral factors for override logic
            neutral_rsi = rsi_analysis.get("neutral", False)
            neutral_factors = rsi_analysis.get("neutral_factors", [])
            
            # 5. TREND CONDITIONS (strategy-independent)
            trend_analysis = self._analyze_trend_conditions(trend)
            condition_factors.extend(trend_analysis["factors"])
            if trend_analysis["risk"] > 0:
                risk_factors.extend(trend_analysis["risk_factors"])
            if trend_analysis["positive"]:
                positive_factors.extend(trend_analysis["positive_factors"])
            
            # 5. HISTORICAL CONTEXT CONDITIONS
            context_analysis = self._analyze_historical_context(historical_context, current_price)
            condition_factors.extend(context_analysis["factors"])
            if context_analysis["risk"] > 0:
                risk_factors.extend(context_analysis["risk_factors"])
            
            # 6. 7-DAY MARKET TREND STATUS ANALYSIS
            market_status_analysis = self._analyze_7day_market_trend(current_price, candles_1d)
            condition_factors.extend(market_status_analysis["factors"])
            
            # DETERMINE OVERALL CONDITIONS (no tradable/untradable logic)
            overall_analysis = self._determine_overall_conditions(
                risk_factors, positive_factors, condition_factors, 
                neutral_rsi, volume_analysis, trend_analysis, volatility_analysis, market_data
            )
            
            result = {
                "condition": overall_analysis["condition"],
                "reasons": condition_factors,
                "risk_level": overall_analysis["risk_level"], 
                "confidence": overall_analysis["confidence"],
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "analysis_timestamp": market_data.get("timestamp", 0),
                "market_status": market_status_analysis["market_status"]
            }
            
            # Add sentiment data if available
            if sentiment_analysis.get("sentiment_data"):
                result["sentiment_data"] = sentiment_analysis["sentiment_data"]
            
            # Add whale analytics data if available
            if whale_analysis.get("whale_data"):
                result["whale_analytics"] = whale_analysis["whale_data"]
            
            # Add news sentiment data if available
            if news_analysis.get("news_data"):
                result["news_sentiment"] = news_analysis["news_data"]
            
            # Log important condition changes
            if overall_analysis["condition"] == "EXCELLENT":
                logger.success(f"🎯 EXCELLENT market conditions: {', '.join(positive_factors[:2])}")
            elif overall_analysis["condition"] == "POOR":
                logger.warning(f"⚠️ POOR market conditions: {', '.join(risk_factors[:2])}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Market conditions analysis failed: {e}")
            return {
                "condition": "POOR",
                "reasons": [f"Analysis failed: {str(e)}"],
                "risk_level": "HIGH",
                "confidence": 0.3,
                "risk_factors": [f"Analysis error: {str(e)}"],
                "positive_factors": [],
                "analysis_timestamp": market_data.get("timestamp", 0),
                "market_status": "NEUTRAL"
            }
    
    def _analyze_volatility_conditions(self, volatility_5m: float, category: str) -> Dict[str, Any]:
        """Analyze volatility for trading suitability"""
        factors = []
        risk_factors = []
        positive_factors = []
        risk_level = 0
        
        if category == "VERY_LOW":
            factors.append("Very low volatility - range-bound market")
            # Strategy-independent: Very low volatility is generally challenging for most trading
            risk_factors.append("Limited profit potential due to very low volatility")
            risk_level = 2  # Moderate risk - not excellent conditions
            
        elif category == "LOW":
            factors.append("Low volatility - limited opportunities") 
            # Strategy-independent: Low volatility reduces profit potential
            risk_factors.append("Reduced profit potential due to low volatility")
            risk_level = 1  # Low risk but limited opportunities
            
        elif category == "MODERATE":
            factors.append("Moderate volatility - good for trading")
            # FIXED: MODERATE volatility should be considered positive for trading
            positive_factors.append("Stable trading conditions with moderate volatility")
            
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
        positive_factors = []
        risk_level = 0
        
        if volume_category in ["VERY_LOW", "LOW"]:
            factors.append(f"{volume_category.lower().replace('_', ' ').title()} volume - limited liquidity")
            risk_factors.append("Slippage risk due to low liquidity")
            risk_level = 2
            
        elif volume_category == "NORMAL":
            factors.append("Normal volume - adequate liquidity")
            # FIXED: Normal volume should be considered positive for trading
            positive_factors.append("Adequate liquidity for trading")
            
        elif volume_category in ["HIGH", "VERY_HIGH", "EXTREME"]:
            factors.append(f"{volume_category.lower().replace('_', ' ').title()} volume - strong market interest")
            positive_factors = [f"Strong {volume_category.lower().replace('_', ' ')} volume activity"]  # Mark as positive for override
            
        elif volume_category == "ABOVE_AVERAGE":
            factors.append("Above average volume - good liquidity")
            # No positive factors for ABOVE_AVERAGE - only HIGH and above get positive factors
            
        return {
            "factors": factors,
            "risk": risk_level,
            "risk_factors": risk_factors,
            "positive": volume_category in ["HIGH", "VERY_HIGH", "EXTREME"],
            "positive_factors": positive_factors
        }
    
    def _analyze_rsi_conditions(self, rsi: float) -> Dict[str, Any]:
        """Analyze RSI for trading suitability"""
        factors = []
        risk_factors = []
        risk_level = 0
        
        
        if 45 <= rsi <= 55:
            factors.append("RSI in neutral zone - no directional bias (OVERRIDE possible)")
            # RSI neutrality is NO LONGER a blocking risk factor (Option 3: Override)
            risk_level = 0  # Changed from 2 to 0
            
        elif rsi <= 25 or rsi >= 75:
            factors.append(f"RSI extreme zone ({rsi:.1f}) - strong signal")
            # Extreme RSI is ALWAYS a strong trading opportunity, never a risk
            # RSI >85 = perfect short opportunity, RSI <15 = perfect long opportunity
            risk_level = 0  # No risk, just opportunity
            
        elif rsi <= 35:
            factors.append(f"RSI oversold ({rsi:.1f}) - bullish potential")
            
        elif rsi >= 60:
            factors.append(f"RSI overbought ({rsi:.1f}) - bearish potential")
        else:
            factors.append(f"RSI in tradable range ({rsi:.1f})")
            # FIXED: Normal RSI range should be considered positive for trading
            positive_factors.append("RSI in healthy trading range")
            
        return {
            "factors": factors,
            "risk": risk_level,
            "risk_factors": risk_factors,
            "positive": rsi <= 35 or rsi >= 60 or (rsi <= 25 or rsi >= 75),  # Oversold/overbought/extreme are positive signals
            "positive_factors": ["Strong RSI signal"] if (rsi <= 35 or rsi >= 60 or (rsi <= 25 or rsi >= 75)) else [],
            "neutral": 45 <= rsi <= 55,  # Flag neutral zone for override logic
            "neutral_factors": ["RSI neutral zone"] if 45 <= rsi <= 55 else []
        }
    
    def _analyze_trend_conditions(self, trend: str) -> Dict[str, Any]:
        """Analyze trend for trading suitability"""
        factors = []
        risk_factors = []
        positive_factors = []
        risk_level = 0
        
        if trend == "SIDEWAYS":
            factors.append("Sideways trend - range-bound market")
            # Trend is informational only - not a blocking risk factor
            risk_level = 0  # No risk from trend alone
            
        elif trend in ["WEAK_UPTREND", "WEAK_DOWNTREND"]:
            factors.append(f"{trend.replace('_', ' ').lower()} - limited momentum")
            # Trend is informational only - not a blocking risk factor
            risk_level = 0  # No risk from trend alone
            
        elif trend in ["UPTREND", "DOWNTREND"]:
            factors.append(f"{trend.lower()} - good directional momentum")
            positive_factors = [f"Strong {trend.lower()} momentum"]  # Mark as positive for override
            risk_level = 0  # No risk from good trends
            
        elif trend in ["STRONG_UPTREND", "STRONG_DOWNTREND"]:
            factors.append(f"{trend.replace('_', ' ').lower()} - excellent momentum")
            positive_factors = [f"Excellent {trend.replace('_', ' ').lower()} momentum"]  # Mark as positive for override
            risk_level = 0  # No risk from strong trends
            
        else:  # NEUTRAL or unknown
            factors.append("Neutral trend - no clear direction")
            # Trend is informational only - not a blocking risk factor
            risk_level = 0  # No risk from trend alone
            
        return {
            "factors": factors,
            "risk": risk_level,
            "risk_factors": risk_factors,
            "positive": len(positive_factors) > 0,  # Positive if we have any positive factors
            "positive_factors": positive_factors
        }
    
    def _analyze_historical_context(self, historical_context: Dict[str, Any], 
                                  current_price: float) -> Dict[str, Any]:
        """Analyze historical context for trading suitability"""
        factors = []
        risk_factors = []
        risk_level = 0
        
        if not historical_context:
            factors.append("No historical context - limited insight")
            risk_level = 0  # Reduced from 1 - don't block trading for missing historical context
            return {
                "factors": factors,
                "risk": risk_level, 
                "risk_factors": [],  # Removed "Missing historical context" as blocking risk factor
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
    
    def _determine_overall_conditions(self, risk_factors: list, positive_factors: list, 
                                     condition_factors: list, neutral_rsi: bool = False,
                                     volume_analysis: Dict = None, trend_analysis: Dict = None, 
                                     volatility_analysis: Dict = None, market_data: Dict = None) -> Dict[str, Any]:
        """Determine overall market conditions based on factors"""
        
        total_risk_score = len(risk_factors)
        total_positive_score = len(positive_factors)
        
        # FIXED: More balanced condition determination
        # Start with FAIR as default, then adjust based on factors
        condition = "FAIR"
        risk_level = "MODERATE"
        confidence = 0.65
        
        # Positive factors boost condition
        if total_positive_score >= 3:
            condition = "EXCELLENT"
            risk_level = "LOW"
            confidence = 0.85
        elif total_positive_score >= 2:
            condition = "GOOD"
            risk_level = "LOW"
            confidence = 0.75
        elif total_positive_score >= 1:
            condition = "GOOD"  # Changed from FAIR to GOOD for 1+ positive factors
            risk_level = "LOW"
            confidence = 0.70
        
        # Risk factors can downgrade condition
        if total_risk_score >= 3:
            condition = "POOR"
            risk_level = "HIGH"
            confidence = max(0.3, confidence - 0.2)
        elif total_risk_score >= 2:
            if condition == "EXCELLENT":
                condition = "GOOD"
            elif condition == "GOOD":
                condition = "FAIR"
            risk_level = "MODERATE"
            confidence = max(0.4, confidence - 0.1)
        elif total_risk_score >= 1:
            if condition == "EXCELLENT":
                condition = "GOOD"
            risk_level = "MODERATE"
            confidence = max(0.5, confidence - 0.05)
        
        # Adjust for high risk factors
        if total_risk_score >= 3:
            condition = "POOR"
            risk_level = "HIGH"
            confidence = max(0.3, confidence - 0.2)
        elif total_risk_score >= 2:
            risk_level = "MODERATE"
            confidence = max(0.4, confidence - 0.1)
        
        return {
            "condition": condition,
            "risk_level": risk_level,
            "confidence": confidence
        }
    
    
    def get_condition_summary(self, analysis: Dict[str, Any]) -> str:
        """Generate user-friendly summary of market conditions"""
        condition = analysis.get("condition", "UNKNOWN")
        main_risks = analysis.get("risk_factors", [])[:2]  # Top 2 risk factors
        main_positives = analysis.get("positive_factors", [])[:2]  # Top 2 positive factors
        
        if condition == "EXCELLENT":
            return f"Excellent conditions: {', '.join(main_positives)}"
        elif condition == "GOOD":
            return f"Good conditions: {', '.join(main_positives)}"
        elif condition == "FAIR":
            return f"Fair conditions"
        elif condition == "POOR": 
            return f"Poor conditions: {', '.join(main_risks)}"
        else:
            return f"Conditions analysis unavailable"
    
    def _analyze_dead_zone_conditions(self, market_data: Dict[str, Any], volatility_analysis: Dict = None, trend_analysis: Dict = None) -> Dict[str, Any]:
        """Dead zone analysis DISABLED - always returns no dead zone"""
        return {
            "is_dead_zone": False,
            "reason": "Dead zone analysis disabled"
        }
    
    def _get_psychological_levels(self, current_price: float) -> list:
        """Get nearby psychological levels for the current price"""
        try:
            # Major psychological levels (round numbers)
            levels = []
            
            # Get the price range we're in (e.g., 110000-120000)
            price_range_start = int(current_price // 10000) * 10000
            price_range_end = price_range_start + 10000
            
            # Add major levels in this range
            for level in range(price_range_start, price_range_end + 1, 1000):
                levels.append(level)
            
            # Add more granular levels around current price
            current_rounded = int(current_price // 100) * 100
            for offset in [-200, -100, 0, 100, 200]:
                levels.append(current_rounded + offset)
            
            return sorted(list(set(levels)))
            
        except Exception as e:
            logger.error(f"❌ Psychological levels calculation failed: {e}")
            return []
    
    def _is_near_psychological_level(self, current_price: float, psychological_levels: list, tolerance: float = 0.00005) -> str:
        """Check if current price is near a psychological level"""
        try:
            for level in psychological_levels:
                if level == 0:
                    continue
                    
                # Check if price is within tolerance of the psychological level
                price_diff_pct = abs(current_price - level) / level
                if price_diff_pct <= tolerance:
                    return f"${level:,.0f}"
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Psychological level check failed: {e}")
            return None
    
    def _analyze_sentiment_conditions(self) -> Dict[str, Any]:
        """
        Analyze Fear & Greed sentiment conditions for trading decisions
        
        Returns:
            Dict containing sentiment factors, risk factors, and positive factors
        """
        try:
            # Get Fear & Greed data
            from core.external.fear_greed_api import get_global_fear_greed_api
            fear_greed_data = get_global_fear_greed_api().get_fear_greed_index()
            
            if not fear_greed_data or "error" in fear_greed_data:
                return {
                    "factors": ["Sentiment data unavailable"],
                    "risk_factors": [],
                    "positive_factors": [],
                    "risk": 0,
                    "positive": False
                }
            
            sentiment_signals = fear_greed_data.get("sentiment_signals", {})
            index_value = fear_greed_data.get("index_value", 50)
            classification = fear_greed_data.get("classification", "Neutral")
            
            factors = []
            risk_factors = []
            positive_factors = []
            risk_level = 0
            is_positive = False
            
            # Analyze sentiment zones
            sentiment_zone = sentiment_signals.get("sentiment_zone", "NEUTRAL")
            trading_bias = sentiment_signals.get("trading_bias", "NEUTRAL")
            extreme_condition = sentiment_signals.get("extreme_condition", False)
            reversal_imminent = sentiment_signals.get("reversal_imminent", False)
            
            # Add sentiment factors
            factors.append(f"Fear & Greed: {index_value} ({classification})")
            factors.append(f"Sentiment Zone: {sentiment_zone}")
            factors.append(f"Trading Bias: {trading_bias}")
            
            # Analyze extreme conditions
            if extreme_condition:
                if sentiment_zone == "EXTREME_FEAR":
                    factors.append("Extreme Fear - High reversal probability")
                    positive_factors.append("Extreme Fear - Strong buy opportunity")
                    is_positive = True
                elif sentiment_zone == "EXTREME_GREED":
                    factors.append("Extreme Greed - High reversal probability")
                    risk_factors.append("Extreme Greed - High sell risk")
                    risk_level = 2
            
            # Analyze reversal conditions
            if reversal_imminent:
                reversal_prob = sentiment_signals.get("reversal_probability", 0.0)
                factors.append(f"Reversal Imminent - {reversal_prob:.0%} probability")
                
                if sentiment_zone in ["EXTREME_FEAR", "FEAR"]:
                    positive_factors.append("Fear sentiment - Reversal opportunity")
                    is_positive = True
                elif sentiment_zone in ["EXTREME_GREED", "GREED"]:
                    risk_factors.append("Greed sentiment - Reversal risk")
                    risk_level = max(risk_level, 1)
            
            # Analyze trading bias
            if trading_bias == "STRONG_BUY":
                positive_factors.append("Strong buy bias from sentiment")
                is_positive = True
            elif trading_bias == "STRONG_SELL":
                risk_factors.append("Strong sell bias from sentiment")
                risk_level = max(risk_level, 1)
            
            # Add confidence boost information
            confidence_boost = sentiment_signals.get("confidence_boost", 0.0)
            if confidence_boost > 0:
                factors.append(f"Sentiment confidence boost: +{confidence_boost:.1%}")
            
            return {
                "factors": factors,
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "risk": risk_level,
                "positive": is_positive,
                "sentiment_data": fear_greed_data
            }
            
        except Exception as e:
            logger.error(f"❌ Sentiment conditions analysis failed: {e}")
            return {
                "factors": ["Sentiment analysis failed"],
                "risk_factors": [],
                "positive_factors": [],
                "risk": 0,
                "positive": False
            }
    
    def _analyze_whale_conditions(self) -> Dict[str, Any]:
        """
        Analyze whale analytics conditions for trading decisions
        
        Returns:
            Dict containing whale factors, risk factors, and positive factors
        """
        try:
            # Get whale analytics data
            whale_data = whale_analytics_api.get_whale_analytics()
            
            if not whale_data or "error" in whale_data:
                return {
                    "factors": ["Whale analytics unavailable"],
                    "risk_factors": [],
                    "positive_factors": [],
                    "risk": 0,
                    "positive": False
                }
            
            whale_activity = whale_data.get("whale_activity", {})
            exchange_flows = whale_data.get("exchange_flows", {})
            sentiment = whale_data.get("sentiment", {})
            
            factors = []
            risk_factors = []
            positive_factors = []
            risk_level = 0
            is_positive = False
            
            # Analyze whale activity
            whale_count = whale_activity.get("whale_count", 0)
            activity_level = whale_activity.get("activity_level", "low")
            total_volume_usd = whale_activity.get("total_volume_usd", 0)
            
            factors.append(f"Whale Activity: {whale_count} whales ({activity_level})")
            factors.append(f"Whale Volume: ${total_volume_usd:,.0f}")
            
            # Analyze exchange flows
            flow_direction = exchange_flows.get("flow_direction", "neutral")
            net_flow = exchange_flows.get("net_flow", 0)
            
            factors.append(f"Exchange Flow: {flow_direction} (${net_flow:,.0f})")
            
            # Analyze sentiment
            sentiment_class = sentiment.get("classification", "neutral")
            confidence = sentiment.get("confidence", "low")
            
            factors.append(f"Whale Sentiment: {sentiment_class} ({confidence})")
            
            # Determine risk and positive factors
            if sentiment_class == "bearish" and confidence == "high":
                risk_factors.append("High confidence bearish whale sentiment")
                risk_level = 2
            elif sentiment_class == "bearish":
                risk_factors.append("Bearish whale sentiment")
                risk_level = 1
            
            if sentiment_class == "bullish" and confidence == "high":
                positive_factors.append("High confidence bullish whale sentiment")
                is_positive = True
            elif sentiment_class == "bullish":
                positive_factors.append("Bullish whale sentiment")
                is_positive = True
            
            if activity_level in ["high", "very_high"]:
                if sentiment_class == "bullish":
                    positive_factors.append("High whale activity with bullish sentiment")
                    is_positive = True
                elif sentiment_class == "bearish":
                    risk_factors.append("High whale activity with bearish sentiment")
                    risk_level = max(risk_level, 1)
            
            if flow_direction == "strong_outflow":
                risk_factors.append("Strong exchange outflow")
                risk_level = max(risk_level, 1)
            elif flow_direction == "strong_inflow":
                positive_factors.append("Strong exchange inflow")
                is_positive = True
            
            return {
                "factors": factors,
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "risk": risk_level,
                "positive": is_positive,
                "whale_data": whale_data
            }
            
        except Exception as e:
            logger.error(f"❌ Whale conditions analysis failed: {e}")
            return {
                "factors": ["Whale analysis failed"],
                "risk_factors": [],
                "positive_factors": [],
                "risk": 0,
                "positive": False
            }
    
    def _analyze_rss_news_conditions(self) -> Dict[str, Any]:
        """
        Analyze news sentiment conditions for trading decisions
        
        Returns:
            Dict containing news factors, risk factors, and positive factors
        """
        try:
            # Get RSS news sentiment data
            news_data = rss_news_api.get_news_sentiment()
            
            if not news_data or "error" in news_data:
                return {
                    "factors": ["News sentiment unavailable"],
                    "risk_factors": [],
                    "positive_factors": [],
                    "risk": 0,
                    "positive": False
                }
            
            sentiment = news_data.get("sentiment", {})
            impact = news_data.get("impact", {})
            trading_signals = news_data.get("trading_signals", {})
            
            factors = []
            risk_factors = []
            positive_factors = []
            risk_level = 0
            is_positive = False
            
            # Analyze sentiment
            sentiment_class = sentiment.get("classification", "neutral")
            confidence = sentiment.get("confidence", "low")
            bullish_count = sentiment.get("bullish_count", 0)
            bearish_count = sentiment.get("bearish_count", 0)
            total_news = sentiment.get("total_news", 0)
            
            factors.append(f"News Sentiment: {sentiment_class} ({confidence})")
            factors.append(f"News Count: {bullish_count}B/{bearish_count}BE/{total_news} total")
            
            # Analyze impact
            impact_level = impact.get("impact_level", "low")
            high_impact_count = impact.get("high_impact_count", 0)
            
            factors.append(f"News Impact: {impact_level} ({high_impact_count} high impact)")
            
            # Analyze trading signals
            trading_bias = trading_signals.get("trading_bias", "NEUTRAL")
            market_impact = trading_signals.get("market_impact", "low")
            
            factors.append(f"Trading Bias: {trading_bias} ({market_impact} impact)")
            
            # Determine risk and positive factors
            if sentiment_class == "bearish" and confidence == "high" and impact_level == "high":
                risk_factors.append("High impact bearish news sentiment")
                risk_level = 2
            elif sentiment_class == "bearish" and impact_level == "high":
                risk_factors.append("High impact bearish news")
                risk_level = 1
            elif sentiment_class == "bearish":
                risk_factors.append("Bearish news sentiment")
                risk_level = 1
            
            if sentiment_class == "bullish" and confidence == "high" and impact_level == "high":
                positive_factors.append("High impact bullish news sentiment")
                is_positive = True
            elif sentiment_class == "bullish" and impact_level == "high":
                positive_factors.append("High impact bullish news")
                is_positive = True
            elif sentiment_class == "bullish":
                positive_factors.append("Bullish news sentiment")
                is_positive = True
            
            if trading_bias == "STRONG_SELL":
                risk_factors.append("Strong sell bias from news")
                risk_level = max(risk_level, 1)
            elif trading_bias == "STRONG_BUY":
                positive_factors.append("Strong buy bias from news")
                is_positive = True
            
            return {
                "factors": factors,
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "risk": risk_level,
                "positive": is_positive,
                "news_data": news_data
            }
            
        except Exception as e:
            logger.error(f"❌ News conditions analysis failed: {e}")
            return {
                "factors": ["News analysis failed"],
                "risk_factors": [],
                "positive_factors": [],
                "risk": 0,
                "positive": False
            }
    
    def _analyze_7day_market_trend(self, current_price: float, candles_1d=None) -> Dict[str, Any]:
        """
        Analyze 7-day market trend to determine market status (BEARISH/NEUTRAL/BULLISH)
        
        Returns:
            Dict containing market status and factors
        """
        try:
            # Get 7-day historical candles (1d timeframe)
            from core.services.system_initializer import get_system_initializer
            from core.api.hyperliquid_api import get_hyperliquid_api
            
            # Get instances
            system_initializer = get_system_initializer()
            market_data_service = system_initializer.singleton_systems.get("market_data_service")
            hyperliquid_api = get_hyperliquid_api()
            
            # Use passed data or fetch as fallback (1d candles change only once per day)
            if candles_1d is None:
                candles_1d = market_data_service.get_historical_candles("BTC", "1d", 7)
            
            if not candles_1d or len(candles_1d) < 7:
                logger.warning("⚠️ Insufficient 7-day data for market status analysis")
                return {
                    "factors": ["Insufficient 7-day data for trend analysis"],
                    "market_status": "NEUTRAL"
                }
            
            # CRITICAL FIX: Use exactly the last 7 candles (not all returned candles)
            # The API returns more than 7 candles, so we need to take the last 7
            last_7_candles = candles_1d[-7:] if len(candles_1d) >= 7 else candles_1d
            
            logger.info(f"📊 Using last 7 candles from {len(candles_1d)} returned candles")
            for i, candle in enumerate(last_7_candles):
                logger.info(f"  Day {i+1}: Close=${candle['close']:,.2f}")
            
            # Calculate trend from 7-day candles
            start_price = last_7_candles[0]["close"]
            end_price = last_7_candles[-1]["close"]
            price_change = end_price - start_price
            price_change_pct = (price_change / start_price) * 100
            
            # Calculate trend strength
            highs = [candle["high"] for candle in last_7_candles]
            lows = [candle["low"] for candle in last_7_candles]
            max_high = max(highs)
            min_low = min(lows)
            range_pct = ((max_high - min_low) / min_low) * 100
            
            # Determine market status based on price change and volatility
            if price_change_pct > 5.0:  # Strong bullish trend (>5% gain)
                market_status = "BULLISH"
                factors = [f"Strong 7-day uptrend: +{price_change_pct:.1f}%"]
            elif price_change_pct > 2.0:  # Moderate bullish trend (2-5% gain)
                market_status = "BULLISH"
                factors = [f"Moderate 7-day uptrend: +{price_change_pct:.1f}%"]
            elif price_change_pct < -5.0:  # Strong bearish trend (>5% loss)
                market_status = "BEARISH"
                factors = [f"Strong 7-day downtrend: {price_change_pct:.1f}%"]
            elif price_change_pct < -2.0:  # Moderate bearish trend (2-5% loss)
                market_status = "BEARISH"
                factors = [f"Moderate 7-day downtrend: {price_change_pct:.1f}%"]
            else:  # Neutral trend (-2% to +2%)
                market_status = "NEUTRAL"
                factors = [f"Neutral 7-day trend: {price_change_pct:+.1f}%"]
            
            # Add volatility context
            if range_pct > 15.0:  # High volatility
                factors.append(f"High volatility: {range_pct:.1f}% range")
            elif range_pct < 5.0:  # Low volatility
                factors.append(f"Low volatility: {range_pct:.1f}% range")
            else:  # Normal volatility
                factors.append(f"Normal volatility: {range_pct:.1f}% range")
            
            # Add price context
            factors.append(f"7-day range: ${min_low:,.0f} - ${max_high:,.0f}")
            factors.append(f"Current: ${current_price:,.0f}")
            
            logger.info(f"📊 7-day market status: {market_status} ({price_change_pct:+.1f}%, {range_pct:.1f}% range)")
            
            return {
                "factors": factors,
                "market_status": market_status,
                "price_change_pct": price_change_pct,
                "range_pct": range_pct,
                "start_price": start_price,
                "end_price": end_price
            }
            
        except Exception as e:
            logger.error(f"❌ 7-day market trend analysis failed: {e}")
            return {
                "factors": [f"7-day trend analysis failed: {str(e)}"],
                "market_status": "NEUTRAL"
            }

# Global instance for consistent conditions analysis across the system
global_conditions_analyzer = MarketConditionsAnalyzer()