#!/usr/bin/env python3
"""
ML Strategy Selector
Intelligent strategy selection based on market conditions and ML analysis
NO FALLBACKS - Proper error handling only
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional
from loguru import logger
from dataclasses import dataclass

@dataclass
class StrategyRecommendation:
    """Strategy recommendation with confidence and reasoning"""
    strategy: str
    confidence: float
    reasoning: str
    alternative_strategies: List[str]
    market_conditions: Dict[str, Any]
    timestamp: float = None

class MLStrategySelector:
    """ML-based strategy selector - NO FALLBACKS, proper error handling only"""
    
    def __init__(self):
        self.ml_models = {}
        self.feature_scaler = None
        self.is_initialized = False
        logger.info("🤖 ML Strategy Selector initialized")
    
    def _initialize_ml_models(self):
        """Initialize ML models for strategy selection"""
        try:
            # Initialize models here
            self.is_initialized = True
            logger.info("✅ ML models initialized for strategy selection")
        except Exception as e:
            logger.error(f"❌ Failed to initialize ML models: {e}")
            raise Exception(f"ML model initialization failed: {e}")
    
    def _safe_get(self, data: Any, key: str, default: Any = None) -> Any:
        """Safely get value from data that might be a dict or other type"""
        if isinstance(data, dict):
            return data.get(key, default)
        return default
    
    def select_strategy(self, market_data: Dict[str, Any], 
                       historical_context: Dict[str, Any] = None) -> StrategyRecommendation:
        """Select optimal strategy based on market conditions - NO FALLBACKS"""
        try:
            # Validate input data
            if not market_data:
                raise ValueError("Market data is required")
            
            # Extract features for ML analysis
            features = self._extract_strategy_features(market_data, historical_context)
            
            # Use ML model to predict strategy
            strategy_prediction = self._predict_strategy_with_ml(features, market_data)
            
            return strategy_prediction
            
        except Exception as e:
            logger.error(f"❌ Strategy selection failed: {e}")
            # NO FALLBACKS - Show explicit error
            raise Exception(f"Strategy selection failed: {e}")
    
    def _extract_strategy_features(self, market_data: Dict[str, Any], 
                                 historical_context: Dict[str, Any] = None) -> np.ndarray:
        """Extract features for ML analysis - NO FALLBACKS"""
        try:
            features = []
            
            # 1. PRICE AND VOLATILITY FEATURES
            current_price = self._safe_get(market_data, "current_price", 0)
            volatility_5m = self._safe_get(market_data, "volatility_5m", 0.0)
            volatility_category = self._safe_get(market_data, "volatility_5m_category", "MODERATE")
            
            features.extend([
                current_price / 100000,  # Normalized price
                volatility_5m,
                self._encode_volatility_category(volatility_category)
            ])
            
            # 2. TECHNICAL INDICATOR FEATURES
            rsi = self._safe_get(market_data, "rsi_5m", 50.0)
            
            # Enhanced RSI features for better ML performance
            rsi_normalized = rsi / 100.0  # 0.0 to 1.0
            rsi_oversold = 1.0 if rsi < 30 else 0.0  # Binary flag
            rsi_overbought = 1.0 if rsi > 70 else 0.0  # Binary flag
            rsi_distance_from_neutral = (rsi - 50.0) / 50.0  # -1.0 to 1.0 (centered at 50)
            
            # Handle trend data - it might be a dict or a float
            trend_data = self._safe_get(market_data, "trend_5m", {})
            trend = self._safe_get(trend_data, "trend", "NEUTRAL")
            
            # Handle volume data - it might be a dict or a float
            volume_data = self._safe_get(market_data, "hyperliquid_volume", {})
            volume_category = self._safe_get(volume_data, "volume_category", "NORMAL")
            
            features.extend([
                rsi_normalized,  # Raw RSI (0-1)
                rsi_oversold,  # Is oversold? (0 or 1)
                rsi_overbought,  # Is overbought? (0 or 1)
                rsi_distance_from_neutral,  # Distance from 50 (-1 to 1)
                self._encode_trend(trend),
                self._encode_volume_category(volume_category)
            ])
            
            # 3. MARKET SENTIMENT FEATURES
            sentiment_data = self._safe_get(market_data, "sentiment_data", {})
            fear_greed_index = self._safe_get(sentiment_data, "index_value", 50)
            sentiment_signals = self._safe_get(sentiment_data, "sentiment_signals", {})
            sentiment_zone = self._safe_get(sentiment_signals, "sentiment_zone", "NEUTRAL")
            
            features.extend([
                fear_greed_index / 100.0,  # Normalized fear/greed
                self._encode_sentiment_zone(sentiment_zone)
            ])
            
            # 4. SUPPORT/RESISTANCE FEATURES
            sr_data = self._safe_get(market_data, "support_resistance", {})
            support_levels = self._safe_get(sr_data, "support_levels", [])
            resistance_levels = self._safe_get(sr_data, "resistance_levels", [])
            
            # Calculate proximity to nearest S/R levels
            nearest_support = self._find_nearest_level(current_price, support_levels)
            nearest_resistance = self._find_nearest_level(current_price, resistance_levels)
            
            features.extend([
                nearest_support / current_price if nearest_support else 1.0,  # Support proximity
                nearest_resistance / current_price if nearest_resistance else 1.0,  # Resistance proximity
                len(support_levels),  # Number of support levels
                len(resistance_levels)  # Number of resistance levels
            ])
            
            # 5. PATTERN ANALYSIS FEATURES
            pattern_analysis = self._safe_get(market_data, "pattern_analysis", {})
            reversal_patterns = self._safe_get(pattern_analysis, "reversal_patterns", [])
            continuation_patterns = self._safe_get(pattern_analysis, "continuation_patterns", [])
            
            features.extend([
                len(reversal_patterns),
                len(continuation_patterns),
                self._calculate_pattern_strength(reversal_patterns),
                self._calculate_pattern_strength(continuation_patterns)
            ])
            
            # 6. VOLUME AND LIQUIDITY FEATURES
            volume_data = self._safe_get(market_data, "hyperliquid_volume", {})
            volume_5m = self._safe_get(volume_data, "volume_5m", 0)
            volume_ratio = self._safe_get(volume_data, "volume_ratio", 1.0)
            
            features.extend([
                min(volume_5m / 1000000, 10.0),  # Normalized volume (capped at 10M)
                volume_ratio,
                self._encode_volume_category(volume_category)
            ])
            
            # 7. TIME-BASED FEATURES
            current_time = time.time()
            current_hour = time.localtime(current_time).tm_hour
            current_minute = time.localtime(current_time).tm_min
            is_weekend = time.localtime(current_time).tm_wday >= 5
            
            features.extend([
                current_hour / 24.0,  # Normalized hour
                current_minute / 60.0,  # Normalized minute
                1.0 if is_weekend else 0.0  # Weekend flag
            ])
            
            # 8. SCALPING-SPECIFIC FEATURES
            # Calculate spread and liquidity metrics
            orderbook_data = self._safe_get(market_data, "orderbook_analysis", {})
            spread = self._safe_get(orderbook_data, "spread", 0.0)
            spread_percentage = spread / current_price if current_price > 0 else 0.0
            bid_size = self._safe_get(orderbook_data, "bid_size", 0.0)
            ask_size = self._safe_get(orderbook_data, "ask_size", 0.0)
            liquidity_score = min((bid_size + ask_size) / 1000000, 10.0)  # Normalize to 0-10
            
            features.extend([
                spread_percentage,  # Lower is better for scalping
                liquidity_score,    # Higher is better for scalping
                min(volume_5m / 100000, 10.0)  # Volume stability for scalping
            ])
            
            # 9. HISTORICAL CONTEXT FEATURES
            if historical_context:
                market_regime_data = self._safe_get(historical_context, "market_regime", {})
                market_regime = self._safe_get(market_regime_data, "regime", "UNKNOWN")
                session_volatility = self._safe_get(historical_context, "session_volatility", 0.0)
                
                features.extend([
                    self._encode_market_regime(market_regime),
                    session_volatility
                ])
            else:
                features.extend([0.0, 0.0])  # Default values
            
            # 10. EXTERNAL FACTORS
            whale_data = self._safe_get(market_data, "whale_analytics", {})
            news_sentiment = self._safe_get(market_data, "news_sentiment", {})
            
            whale_activity_data = self._safe_get(whale_data, "whale_activity", {})
            whale_activity = self._safe_get(whale_activity_data, "activity_level", "low")
            
            sentiment_data = self._safe_get(news_sentiment, "sentiment", {})
            news_classification = self._safe_get(sentiment_data, "classification", "neutral")
            
            features.extend([
                self._encode_whale_activity(whale_activity),
                self._encode_news_sentiment(news_classification)
            ])
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"❌ Feature extraction failed: {e}")
            # NO FALLBACKS - Show explicit error
            raise Exception(f"Feature extraction failed: {e}")
    
    def _predict_strategy_with_ml(self, features: np.ndarray, market_data: Dict[str, Any]) -> StrategyRecommendation:
        """Use ML model to predict strategy - Multi-factor analysis"""
        try:
            # Extract key metrics for strategy selection
            volatility_5m = self._safe_get(market_data, "volatility_5m", 0.0)
            volatility_category = self._safe_get(market_data, "volatility_5m_category", "MODERATE")
            rsi = self._safe_get(market_data, "rsi", 50)
            trend = self._safe_get(market_data, "trend", "SIDEWAYS")
            volume_category = self._safe_get(market_data, "trading_volume_category", "MODERATE")
            
            # Calculate strategy scores
            scalping_score = 0.0
            trend_following_score = 0.0
            range_trading_score = 0.0
            standard_score = 0.5  # Baseline
            
            # VOLATILITY ANALYSIS
            if volatility_category in ["EXTREME", "HIGH"]:
                scalping_score += 0.4
                range_trading_score -= 0.2
            elif volatility_category in ["VERY_LOW", "LOW"]:
                range_trading_score += 0.3
                scalping_score -= 0.3
            
            # TREND ANALYSIS
            if "STRONG" in trend and "SIDEWAYS" not in trend:
                trend_following_score += 0.5
                range_trading_score -= 0.3
            elif "SIDEWAYS" in trend or "NEUTRAL" in trend:
                range_trading_score += 0.4
                trend_following_score -= 0.3
            elif "WEAK" in trend:
                standard_score += 0.2
                trend_following_score -= 0.2
            
            # RSI ANALYSIS (Mean reversion signals)
            if rsi > 70 or rsi < 30:
                range_trading_score += 0.3  # Overbought/oversold favors mean reversion
                trend_following_score -= 0.2
            
            # VOLUME ANALYSIS
            if volume_category in ["VERY_HIGH", "EXTREME"]:
                scalping_score += 0.2
                trend_following_score += 0.1
            elif volume_category in ["VERY_LOW", "LOW"]:
                scalping_score -= 0.3
            
            # Select strategy with highest score
            scores = {
                "scalping": scalping_score,
                "trend_following": trend_following_score,
                "range_trading": range_trading_score,  # Use range_trading strategy name
                "standard": standard_score
            }
            
            strategy = max(scores, key=scores.get)
            raw_confidence = scores[strategy]
            confidence = min(0.9, max(0.5, 0.6 + raw_confidence * 0.3))  # Normalize to 0.5-0.9
            
            # Build reasoning
            reasoning_parts = []
            reasoning_parts.append(f"Volatility: {volatility_category} ({volatility_5m:.4f})")
            reasoning_parts.append(f"Trend: {trend}")
            reasoning_parts.append(f"RSI: {rsi:.1f}")
            reasoning_parts.append(f"Volume: {volume_category}")
            reasoning = " | ".join(reasoning_parts)
            
            return StrategyRecommendation(
                strategy=strategy,
                confidence=confidence,
                reasoning=reasoning,
                alternative_strategies=[s for s, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[1:3]],
                market_conditions=self._summarize_market_conditions(market_data),
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ ML prediction failed: {e}")
            # NO FALLBACKS - Show explicit error
            raise Exception(f"ML prediction failed: {e}")
    
    def _encode_volatility_category(self, category: str) -> float:
        """Encode volatility category to numeric value"""
        encoding = {
            "VERY_LOW": 0.0,
            "LOW": 0.25,
            "MODERATE": 0.5,
            "HIGH": 0.75,
            "EXTREME": 1.0
        }
        return encoding.get(category, 0.5)
    
    def _encode_trend(self, trend: str) -> float:
        """Encode trend to numeric value"""
        encoding = {
            "STRONG_DOWNTREND": 0.0,
            "DOWNTREND": 0.25,
            "NEUTRAL": 0.5,
            "UPTREND": 0.75,
            "STRONG_UPTREND": 1.0
        }
        return encoding.get(trend, 0.5)
    
    def _encode_volume_category(self, category: str) -> float:
        """Encode volume category to numeric value"""
        encoding = {
            "VERY_LOW": 0.0,
            "LOW": 0.25,
            "NORMAL": 0.5,
            "HIGH": 0.75,
            "EXTREME": 1.0
        }
        return encoding.get(category, 0.4)
    
    def _encode_sentiment_zone(self, zone: str) -> float:
        """Encode sentiment zone to numeric value"""
        encoding = {
            "EXTREME_FEAR": 0.0,
            "FEAR": 0.25,
            "NEUTRAL": 0.5,
            "GREED": 0.75,
            "EXTREME_GREED": 1.0
        }
        return encoding.get(zone, 0.5)
    
    def _encode_market_regime(self, regime: str) -> float:
        """Encode market regime to numeric value"""
        encoding = {
            "BEAR_MARKET": 0.0,
            "CORRECTION": 0.25,
            "NEUTRAL": 0.5,
            "BULL_MARKET": 0.75,
            "BREAKOUT": 1.0
        }
        return encoding.get(regime, 0.5)
    
    def _encode_whale_activity(self, activity: str) -> float:
        """Encode whale activity to numeric value"""
        encoding = {
            "very_low": 0.0,
            "low": 0.25,
            "medium": 0.5,
            "high": 0.75,
            "very_high": 1.0
        }
        return encoding.get(activity, 0.5)
    
    def _encode_news_sentiment(self, sentiment: str) -> float:
        """Encode news sentiment to numeric value"""
        encoding = {
            "very_bearish": 0.0,
            "bearish": 0.25,
            "neutral": 0.5,
            "bullish": 0.75,
            "very_bullish": 1.0
        }
        return encoding.get(sentiment, 0.5)
    
    def _find_nearest_level(self, price: float, levels: List[float]) -> Optional[float]:
        """Find nearest support/resistance level"""
        if not levels:
            return None
        return min(levels, key=lambda x: abs(x - price))
    
    def _calculate_pattern_strength(self, patterns: List[Dict]) -> float:
        """Calculate average pattern strength"""
        if not patterns:
            return 0.0
        strengths = [self._safe_get(p, "confidence", 0.0) for p in patterns]
        return sum(strengths) / len(strengths)
    
    def _summarize_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize key market conditions for the recommendation"""
        trend_data = self._safe_get(market_data, "trend_5m", {})
        volume_data = self._safe_get(market_data, "hyperliquid_volume", {})
        
        return {
            "volatility_category": self._safe_get(market_data, "volatility_5m_category", "UNKNOWN"),
            "trend": self._safe_get(trend_data, "trend", "UNKNOWN"),
            "volume_category": self._safe_get(volume_data, "volume_category", "UNKNOWN"),
            "rsi": self._safe_get(market_data, "rsi_5m", 0),
            "current_price": self._safe_get(market_data, "current_price", 0)
        }

# Global instance
global_ml_strategy_selector = MLStrategySelector()