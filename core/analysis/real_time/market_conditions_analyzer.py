#!/usr/bin/env python3
"""
Market Conditions Analyzer
==========================
Determines when market conditions are suitable/unsuitable for trading

PURPOSE: Identify untradable conditions to avoid losses and false signals
FOCUS: Multiple condition checks (volatility, volume, trend, RSI zones)
INTEGRATION: Used by TradingEngine before making any trading decisions

ARCHITECTURE: Follows SOLID principles with dependency injection
"""

from typing import Dict, Any, Tuple, Protocol
from loguru import logger
from .condition_analyzers import (
    VolatilityConditionAnalyzer, 
    VolumeConditionAnalyzer,
    SentimentConditionAnalyzer,
    WhaleConditionAnalyzer,
    RSIConditionAnalyzer
)


class DataProvider(Protocol):
    """Protocol for data providers to ensure dependency inversion"""
    def get_current_price(self) -> float: ...
    def get_volatility_data(self) -> Dict[str, Any]: ...
    def get_sentiment_data(self) -> Dict[str, Any]: ...
    def get_whale_data(self) -> Dict[str, Any]: ...
    def get_news_data(self) -> Dict[str, Any]: ...


class MarketConditionsAnalyzer:
    """
    Analyzes market conditions to determine trading suitability.
    
    Follows SOLID principles:
    - SRP: Single responsibility for market condition analysis
    - OCP: Open for extension via strategy pattern
    - LSP: Substitutable with other condition analyzers
    - ISP: Focused interface for condition analysis
    - DIP: Depends on abstractions (DataProvider) not concretions
    """
    
    def __init__(self, data_provider: DataProvider = None):
        self.name = "MarketConditionsAnalyzer"
        self._data_provider = data_provider
        
        # Initialize specialized condition analyzers (SRP compliance)
        self.volatility_analyzer = VolatilityConditionAnalyzer()
        self.volume_analyzer = VolumeConditionAnalyzer()
        self.sentiment_analyzer = SentimentConditionAnalyzer()
        self.whale_analyzer = WhaleConditionAnalyzer()
        self.rsi_analyzer = RSIConditionAnalyzer()
        
        logger.info("🔍 Market Conditions Analyzer initialized - Clean architecture with SRP compliance")
    
    def analyze_trading_conditions(self, market_data: Dict[str, Any], 
                                 historical_context: Dict[str, Any] = None, 
                                 candles_1d=None) -> Dict[str, Any]:
        """
        Analyze market conditions for trading suitability.
        
        Args:
            market_data: Current market data
            historical_context: Historical context data
            candles_1d: Daily candles for trend analysis
            
        Returns:
            Dict with condition analysis results
        """
        try:
            # Extract market data (NO FALLBACKS - unified_data must provide all required keys)
            current_price = market_data["current_price"]
            rsi = market_data["rsi"]
            trend = market_data["trend"]
            volatility_5m = market_data["volatility_5m"]
            volatility_category = market_data["volatility_category"]
            volume_category = market_data["volume_category"]
            
            # Run all condition analyses
            analyses = self._run_condition_analyses(
                current_price, rsi, trend, volatility_5m, 
                volatility_category, volume_category, 
                historical_context, candles_1d
            )
            
            # Determine overall conditions
            overall_analysis = self._determine_overall_conditions(analyses)
            
            # Build result
            result = self._build_analysis_result(overall_analysis, analyses, market_data)
            
            # Log significant changes
            self._log_condition_changes(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Market conditions analysis failed: {e}")
            return self._create_error_result(market_data)
    
    def _run_condition_analyses(self, current_price: float, rsi: float, trend: str,
                               volatility_5m: float, volatility_category: str, 
                               volume_category: str, historical_context: Dict[str, Any],
                               candles_1d) -> Dict[str, Any]:
        """Run all condition analyses - follows SRP"""
        return {
            "volatility": self.volatility_analyzer.analyze_volatility_conditions(volatility_5m, volatility_category),
            "volume": self.volume_analyzer.analyze_volume_conditions(volume_category),
            "sentiment": self.sentiment_analyzer.analyze_sentiment_conditions(),
            "whale": self.whale_analyzer.analyze_whale_conditions(),
            "news": self._analyze_rss_news_conditions(),
            "rsi": self.rsi_analyzer.analyze_rsi_conditions(rsi),
            "trend": self._analyze_trend_conditions(trend),
            "historical": self._analyze_historical_context(historical_context, current_price),
            "market_status": self._analyze_7day_market_trend(current_price, candles_1d)
        }
    
    def _determine_overall_conditions(self, analyses: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall conditions from individual analyses - follows SRP"""
        # Collect all factors
        all_factors = []
        risk_factors = []
        positive_factors = []
        
        for analysis_name, analysis in analyses.items():
            if analysis_name == "market_status":
                continue  # Skip market status, it's informational
                
            all_factors.extend(analysis["factors"])  # Required (NO FALLBACKS)
            risk_factors.extend(analysis["risk_factors"])  # Required (NO FALLBACKS)
            positive_factors.extend(analysis["positive_factors"])  # Required (NO FALLBACKS)
        
        # Determine condition based on factors
        total_risk_score = len(risk_factors)
        total_positive_score = len(positive_factors)
        
        condition = "FAIR"  # Default
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
            condition = "GOOD"
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
        
        return {
            "condition": condition,
            "risk_level": risk_level,
            "confidence": confidence,
            "all_factors": all_factors,
            "risk_factors": risk_factors,
            "positive_factors": positive_factors
        }
    
    def _build_analysis_result(self, overall_analysis: Dict[str, Any], 
                             analyses: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build the final analysis result - follows SRP"""
        result = {
            "condition": overall_analysis["condition"],
            "reasons": overall_analysis["all_factors"],
            "risk_level": overall_analysis["risk_level"],
            "confidence": overall_analysis["confidence"],
            "risk_factors": overall_analysis["risk_factors"],
            "positive_factors": overall_analysis["positive_factors"],
            "analysis_timestamp": market_data["timestamp"],  # Required (NO FALLBACKS)
            "market_status": analyses["market_status"]["market_status"]
        }
        
        # Add optional data if available
        if "sentiment_data" in analyses["sentiment"]:
            result["sentiment_data"] = analyses["sentiment"]["sentiment_data"]
        
        if "whale_data" in analyses["whale"]:
            result["whale_analytics"] = analyses["whale"]["whale_data"]
        
        if "news_data" in analyses["news"]:
            result["news_sentiment"] = analyses["news"]["news_data"]
        
        return result
    
    def _log_condition_changes(self, result: Dict[str, Any]) -> None:
        """Log significant condition changes - follows SRP"""
        condition = result["condition"]  # Required (NO FALLBACKS)
        positive_factors = result["positive_factors"]  # Required (NO FALLBACKS)
        risk_factors = result["risk_factors"]  # Required (NO FALLBACKS)
        
        if condition == "EXCELLENT":
            factors_text = ', '.join(positive_factors[:2]) if positive_factors else 'No factors'
            logger.success(f"🎯 EXCELLENT market conditions: {factors_text}")
        elif condition == "POOR":
            factors_text = ', '.join(risk_factors[:2]) if risk_factors else 'No factors'
            logger.warning(f"⚠️ POOR market conditions: {factors_text}")
    
    def _create_error_result(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create error result - follows SRP"""
        return {
            "condition": "POOR",
            "reasons": ["Analysis failed"],
            "risk_level": "HIGH",
            "confidence": 0.3,
            "risk_factors": ["Analysis error"],
            "positive_factors": [],
            "analysis_timestamp": market_data["timestamp"],  # Required (NO FALLBACKS)
            "market_status": "NEUTRAL"
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
        
        # Check market regime from historical analysis (NO FALLBACKS)
        market_regime = historical_context["market_regime"]
        regime = market_regime["regime"]
        
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
            
        # Check proximity to major support/resistance levels (NO FALLBACKS)
        major_levels = historical_context["major_levels"]
        support_levels = major_levels["support"]
        resistance_levels = major_levels["resistance"]
        
        if support_levels or resistance_levels:
            all_levels = support_levels + resistance_levels
            nearest_level = min(all_levels, key=lambda x: abs(current_price - x))
            distance_pct = abs(current_price - nearest_level) / current_price
            
            # Calculate dynamic proximity threshold based on market volatility
            dynamic_threshold = self._calculate_dynamic_sr_proximity_threshold()
            
            if distance_pct < dynamic_threshold:
                factors.append(f"Near major S/R level - breakout/bounce potential (within {dynamic_threshold*100:.1f}%)")
            
        return {
            "factors": factors,
            "risk": risk_level,
            "risk_factors": risk_factors,
            "positive": regime in ["TRENDING_UP", "TRENDING_DOWN", "HIGH_VOLATILITY"],
            "positive_factors": []
        }
    
    
    
    def get_condition_summary(self, analysis: Dict[str, Any]) -> str:
        """Generate user-friendly summary of market conditions"""
        condition = analysis["condition"]  # Required (NO FALLBACKS)
        main_risks = analysis["risk_factors"][:2]  # Top 2 risk factors (NO FALLBACKS)
        main_positives = analysis["positive_factors"][:2]  # Top 2 positive factors (NO FALLBACKS)
        
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
    
    
    def _analyze_sentiment_conditions(self) -> Dict[str, Any]:
        """
        Analyze Fear & Greed sentiment conditions for trading decisions
        
        Returns:
            Dict containing sentiment factors, risk factors, and positive factors
        """
        try:
            # Get sentiment data from existing calculation modules
            from core.external.fear_greed_api import get_global_fear_greed_api
            fear_greed_api = get_global_fear_greed_api()
            
            fear_greed_data = fear_greed_api.get_fear_greed_index()
            
            if not fear_greed_data or "error" in fear_greed_data:
                return {
                    "factors": ["Sentiment data unavailable"],
                    "risk_factors": [],
                    "positive_factors": [],
                    "risk": 0,
                    "positive": False
                }
            
            sentiment_signals = fear_greed_data["sentiment_signals"]  # Required (NO FALLBACKS)
            index_value = fear_greed_data["index_value"]  # Required (NO FALLBACKS)
            classification = fear_greed_data["classification"]  # Required (NO FALLBACKS)
            
            factors = []
            risk_factors = []
            positive_factors = []
            risk_level = 0
            is_positive = False
            
            # Analyze sentiment zones (NO FALLBACKS)
            sentiment_zone = sentiment_signals["sentiment_zone"]
            trading_bias = sentiment_signals["trading_bias"]
            extreme_condition = sentiment_signals["extreme_condition"]
            reversal_imminent = sentiment_signals["reversal_imminent"]
            
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
                reversal_prob = sentiment_signals["reversal_probability"]  # Required (NO FALLBACKS)
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
            confidence_boost = sentiment_signals["confidence_boost"]  # Required (NO FALLBACKS)
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
            # Get whale analytics data from existing calculation modules
            from core.calculations.whale_analysis_calculator import create_whale_analysis_calculator
            
            whale_calculator = create_whale_analysis_calculator()
            
            # Get whale analysis from the calculator
            whale_analysis = whale_calculator.get_latest_analysis()
            
            if not whale_analysis or "error" in whale_analysis:
                return {
                    "factors": ["Whale analytics unavailable"],
                    "risk_factors": [],
                    "positive_factors": [],
                    "risk": 0,
                    "positive": False
                }
            
            whale_activity = whale_analysis["whale_activity"]  # Required (NO FALLBACKS)
            exchange_flows = whale_analysis["exchange_flows"]  # Required (NO FALLBACKS)
            sentiment = whale_analysis["sentiment"]  # Required (NO FALLBACKS)
            
            factors = []
            risk_factors = []
            positive_factors = []
            risk_level = 0
            is_positive = False
            
            # Analyze whale activity (NO FALLBACKS)
            whale_count = whale_activity["whale_count"]
            activity_level = whale_activity["activity_level"]
            total_volume_usd = whale_activity["total_volume_usd"]
            
            factors.append(f"Whale Activity: {whale_count} whales ({activity_level})")
            factors.append(f"Whale Volume: ${total_volume_usd:,.0f}")
            
            # Analyze exchange flows (NO FALLBACKS)
            flow_direction = exchange_flows["flow_direction"]
            net_flow = exchange_flows["net_flow"]
            
            factors.append(f"Exchange Flow: {flow_direction} (${net_flow:,.0f})")
            
            # Analyze sentiment (NO FALLBACKS)
            sentiment_class = sentiment["classification"]
            confidence = sentiment["confidence"]
            
            factors.append(f"Whale Sentiment: {sentiment_class} ({confidence})")
            
            # Determine risk and positive factors (whale-specific)
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
                "whale_data": whale_analysis
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
            # Get news sentiment data from existing calculation modules
            from core.external.rss_news_api import get_global_rss_news_api
            rss_news_api = get_global_rss_news_api()
            
            news_data = rss_news_api.get_news_sentiment()
            
            if not news_data or "error" in news_data:
                return {
                    "factors": ["News sentiment unavailable"],
                    "risk_factors": [],
                    "positive_factors": [],
                    "risk": 0,
                    "positive": False
                }
            
            sentiment = news_data["sentiment"]  # Required (NO FALLBACKS)
            impact = news_data["impact"]  # Required (NO FALLBACKS)
            trading_signals = news_data["trading_signals"]  # Required (NO FALLBACKS)
            
            factors = []
            risk_factors = []
            positive_factors = []
            risk_level = 0
            is_positive = False
            
            # Analyze sentiment (NO FALLBACKS)
            sentiment_class = sentiment["classification"]
            confidence = sentiment["confidence"]
            bullish_count = sentiment["bullish_count"]
            bearish_count = sentiment["bearish_count"]
            total_news = sentiment["total_news"]
            
            factors.append(f"News Sentiment: {sentiment_class} ({confidence})")
            factors.append(f"News Count: {bullish_count}B/{bearish_count}BE/{total_news} total")
            
            # Analyze impact (NO FALLBACKS)
            impact_level = impact["impact_level"]
            high_impact_count = impact["high_impact_count"]
            
            factors.append(f"News Impact: {impact_level} ({high_impact_count} high impact)")
            
            # Analyze trading signals (NO FALLBACKS)
            trading_bias = trading_signals["trading_bias"]
            market_impact = trading_signals["market_impact"]
            
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
            market_data_service = system_initializer.singleton_systems["market_data_service"]  # Required (NO FALLBACKS)
            hyperliquid_api = get_hyperliquid_api()
            
            # Use passed data or return neutral status
            if candles_1d is None:
                logger.warning("⚠️ No 1d candles provided for market trend analysis")
                return {
                    "factors": ["No 1d candles available for trend analysis"],
                    "market_status": "NEUTRAL"
                }
            
            if not candles_1d or len(candles_1d) < 7:
                logger.error(f"❌ CRITICAL: Insufficient 7-day data for market status analysis - API returned {len(candles_1d) if candles_1d else 0} candles")
                logger.error(f"❌ Expected at least 7 days of 1d candles, got: {candles_1d}")
                raise ValueError("Insufficient 7-day data - API must provide at least 7 days of 1d candles")
            
            # CRITICAL FIX: Use exactly the last 7 candles (not all returned candles)
            # The API returns more than 7 candles, so we need to take the last 7
            last_7_candles = candles_1d[-7:] if len(candles_1d) >= 7 else candles_1d
            
            # Removed excessive day-by-day logging - only log summary
            logger.debug(f"📊 Analyzing 7-day trend from {len(candles_1d)} available candles")
            
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
            
            # Calculate dynamic thresholds based on current volatility
            dynamic_thresholds = self._calculate_dynamic_trend_thresholds()
            
            strong_bullish_threshold = dynamic_thresholds['strong_bullish']
            moderate_bullish_threshold = dynamic_thresholds['moderate_bullish']
            strong_bearish_threshold = dynamic_thresholds['strong_bearish']
            moderate_bearish_threshold = dynamic_thresholds['moderate_bearish']
            high_volatility_threshold = dynamic_thresholds['high_volatility']
            low_volatility_threshold = dynamic_thresholds['low_volatility']
            
            # Determine market status based on dynamic thresholds
            if price_change_pct > strong_bullish_threshold:
                market_status = "BULLISH"
                factors = [f"Strong 7-day uptrend: +{price_change_pct:.1f}% (threshold: {strong_bullish_threshold:.1f}%)"]
            elif price_change_pct > moderate_bullish_threshold:
                market_status = "BULLISH"
                factors = [f"Moderate 7-day uptrend: +{price_change_pct:.1f}% (threshold: {moderate_bullish_threshold:.1f}%)"]
            elif price_change_pct < strong_bearish_threshold:
                market_status = "BEARISH"
                factors = [f"Strong 7-day downtrend: {price_change_pct:.1f}% (threshold: {strong_bearish_threshold:.1f}%)"]
            elif price_change_pct < moderate_bearish_threshold:
                market_status = "BEARISH"
                factors = [f"Moderate 7-day downtrend: {price_change_pct:.1f}% (threshold: {moderate_bearish_threshold:.1f}%)"]
            else:  # Neutral trend
                market_status = "NEUTRAL"
                factors = [f"Neutral 7-day trend: {price_change_pct:+.1f}% (range: {moderate_bearish_threshold:.1f}% to {moderate_bullish_threshold:.1f}%)"]
            
            # Add volatility context using dynamic thresholds
            if range_pct > high_volatility_threshold:
                factors.append(f"High volatility: {range_pct:.1f}% range (threshold: {high_volatility_threshold:.1f}%)")
            elif range_pct < low_volatility_threshold:
                factors.append(f"Low volatility: {range_pct:.1f}% range (threshold: {low_volatility_threshold:.1f}%)")
            else:  # Normal volatility
                factors.append(f"Normal volatility: {range_pct:.1f}% range")
            
            # Add price context
            factors.append(f"7-day range: ${min_low:,.0f} - ${max_high:,.0f}")
            factors.append(f"Current: ${current_price:,.0f}")
            
            # Log at INFO level when status is BULLISH or BEARISH (significant), DEBUG for NEUTRAL
            if market_status in ["BULLISH", "BEARISH"]:
                logger.info(f"📊 7-day market status: {market_status} ({price_change_pct:+.1f}%, range: {range_pct:.1f}%, thresholds: moderate={moderate_bullish_threshold:.1f}%/{moderate_bearish_threshold:.1f}%, strong={strong_bullish_threshold:.1f}%/{strong_bearish_threshold:.1f}%)")
            else:
                logger.debug(f"📊 7-day market status: {market_status} ({price_change_pct:+.1f}%, {range_pct:.1f}% range)")
            
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
    
    def _calculate_dynamic_rsi_thresholds(self) -> Dict[str, float]:
        """Calculate dynamic RSI thresholds based on market conditions"""
        try:
            # Get volatility data from existing calculation modules
            volatility_data = self._get_volatility_data()
            volatility_5m = volatility_data["volatility_5m"]  # Required (NO FALLBACKS)
            volatility_category = volatility_data["volatility_category"]  # Required (NO FALLBACKS)
            
            # Base thresholds (standard RSI levels)
            base_neutral_low = 45.0
            base_neutral_high = 55.0
            base_oversold = 35.0
            base_overbought = 60.0
            base_extreme_oversold = 25.0
            base_extreme_overbought = 75.0
            
            # Adjust thresholds based on volatility
            volatility_adjustment = 0.0
            if volatility_category == "VERY_LOW":
                volatility_adjustment = -5.0  # Tighter thresholds in low volatility
            elif volatility_category == "LOW":
                volatility_adjustment = -2.5
            elif volatility_category == "HIGH":
                volatility_adjustment = 2.5  # Wider thresholds in high volatility
            elif volatility_category == "EXTREME":
                volatility_adjustment = 5.0  # Much wider thresholds in extreme volatility
            
            # Apply volatility adjustment
            neutral_low = max(30.0, min(60.0, base_neutral_low + volatility_adjustment))
            neutral_high = max(40.0, min(70.0, base_neutral_high + volatility_adjustment))
            oversold = max(20.0, min(45.0, base_oversold + volatility_adjustment))
            overbought = max(55.0, min(80.0, base_overbought + volatility_adjustment))
            extreme_oversold = max(15.0, min(35.0, base_extreme_oversold + volatility_adjustment))
            extreme_overbought = max(65.0, min(85.0, base_extreme_overbought + volatility_adjustment))
            
            return {
                'neutral_low': neutral_low,
                'neutral_high': neutral_high,
                'oversold': oversold,
                'overbought': overbought,
                'extreme_oversold': extreme_oversold,
                'extreme_overbought': extreme_overbought,
                'volatility_category': volatility_category,
                'volatility_5m': volatility_5m,
                'adjustment': volatility_adjustment,
                'data_source': 'dynamic_volatility_based'
            }
            
        except Exception as e:
            logger.error(f"❌ Dynamic RSI threshold calculation failed: {e}")
            # NO FALLBACKS - Raise error instead of returning default values
            raise ValueError(f"Dynamic RSI threshold calculation failed - NO FALLBACKS: {e}")
    
    def _calculate_dynamic_trend_thresholds(self) -> Dict[str, float]:
        """Calculate dynamic trend thresholds based on current market volatility"""
        try:
            # Get volatility data from existing calculation modules
            volatility_data = self._get_volatility_data()
            current_volatility = volatility_data["volatility_5m"]  # Required (NO FALLBACKS)
            
            # Base thresholds (standard levels)
            base_strong_bullish = 5.0
            base_moderate_bullish = 2.0
            base_strong_bearish = -5.0
            base_moderate_bearish = -2.0
            base_high_volatility = 15.0
            base_low_volatility = 5.0
            
            # Adjust thresholds based on current volatility
            # Higher volatility = wider thresholds, lower volatility = tighter thresholds
            volatility_factor = current_volatility / 10.0  # Normalize to 0-1 range
            volatility_factor = max(0.5, min(2.0, volatility_factor))  # Clamp between 0.5x and 2.0x
            
            # Apply volatility adjustment
            strong_bullish = base_strong_bullish * volatility_factor
            moderate_bullish = base_moderate_bullish * volatility_factor
            strong_bearish = base_strong_bearish * volatility_factor
            moderate_bearish = base_moderate_bearish * volatility_factor
            high_volatility = base_high_volatility * volatility_factor
            low_volatility = base_low_volatility * volatility_factor
            
            return {
                'strong_bullish': strong_bullish,
                'moderate_bullish': moderate_bullish,
                'strong_bearish': strong_bearish,
                'moderate_bearish': moderate_bearish,
                'high_volatility': high_volatility,
                'low_volatility': low_volatility,
                'volatility_factor': volatility_factor,
                'current_volatility': current_volatility,
                'data_source': 'dynamic_volatility_based'
            }
            
        except Exception as e:
            logger.error(f"❌ Dynamic trend threshold calculation failed: {e}")
            # NO FALLBACKS - Raise error instead of returning default values
            raise ValueError(f"Dynamic trend threshold calculation failed - NO FALLBACKS: {e}")
    
    def _calculate_dynamic_sr_proximity_threshold(self) -> float:
        """Calculate dynamic S/R proximity threshold based on market volatility"""
        try:
            # Get volatility data from existing calculation modules
            volatility_data = self._get_volatility_data()
            volatility_5m = volatility_data["volatility_5m"]  # Required (NO FALLBACKS)
            volatility_category = volatility_data["volatility_category"]  # Required (NO FALLBACKS)
            
            # Base threshold (0.5%)
            base_threshold = 0.005
            
            # Adjust threshold based on volatility
            # Higher volatility = wider threshold, lower volatility = tighter threshold
            if volatility_category == "VERY_LOW":
                volatility_multiplier = 0.5  # Tighter threshold in low volatility
            elif volatility_category == "LOW":
                volatility_multiplier = 0.7
            elif volatility_category == "MODERATE":
                volatility_multiplier = 1.0  # Standard threshold
            elif volatility_category == "HIGH":
                volatility_multiplier = 1.5  # Wider threshold in high volatility
            elif volatility_category == "EXTREME":
                volatility_multiplier = 2.0  # Much wider threshold in extreme volatility
            else:
                volatility_multiplier = 1.0
            
            # Apply volatility adjustment
            dynamic_threshold = base_threshold * volatility_multiplier
            
            # Ensure reasonable bounds (0.1% to 2.0%)
            dynamic_threshold = max(0.001, min(0.02, dynamic_threshold))
            
            return dynamic_threshold
            
        except Exception as e:
            logger.error(f"❌ Dynamic S/R proximity threshold calculation failed: {e}")
            # NO FALLBACKS - Raise error instead of returning default value
            raise ValueError(f"Dynamic S/R proximity threshold calculation failed - NO FALLBACKS: {e}")
    
    def _get_volatility_data(self) -> Dict[str, Any]:
        """Get volatility data from existing calculation modules - follows DRY"""
        from core.calculations.volatility_calculator import create_volatility_calculator
        volatility_calculator = create_volatility_calculator("BTC")
        return volatility_calculator.get_latest_analysis()

# Global instance for consistent conditions analysis across the system
# Factory function for backward compatibility
def create_market_conditions_analyzer(data_provider: DataProvider = None) -> MarketConditionsAnalyzer:
    """
    Factory function to create MarketConditionsAnalyzer with dependency injection
    
    Args:
        data_provider: DataProvider instance (optional)
    
    Returns:
        Configured MarketConditionsAnalyzer instance
    """
    return MarketConditionsAnalyzer(data_provider=data_provider)

# Global instance for backward compatibility
global_conditions_analyzer = create_market_conditions_analyzer()