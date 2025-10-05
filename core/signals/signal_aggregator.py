#!/usr/bin/env python3
"""
Signal Aggregator
Combines multiple signal sources with proper weighting and quality assessment
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from .signal_sources import SignalType, SignalSource, global_signal_sources_manager
from core.analysis.real_time.psychological_levels_analyzer import get_global_psychological_levels_analyzer
from core.analysis.real_time.rsi_calculator import get_global_rsi_calculator
from core.analysis.real_time.pressure_calculator import PressureCalculator
from core.analysis.real_time.volume_calculator import VolumeCalculator
from core.external.whale_analytics_api import whale_analytics_api
from core.external.rss_news_api import rss_news_api


@dataclass
class SignalResult:
    """Result of a signal calculation"""
    signal_type: SignalType
    direction: str
    confidence: float
    strength: float
    weight: float
    weighted_confidence: float
    reasoning: str
    data: Dict[str, Any]
    timestamp: float
    error: Optional[str] = None


class SignalAggregator:
    """
    Aggregates signals from multiple sources with proper weighting
    Focuses on the 3 primary signals for now
    """
    
    def __init__(self):
        self.signal_sources_manager = global_signal_sources_manager
        self.pressure_calculator = PressureCalculator()
        self.volume_calculator = VolumeCalculator()
        
        # Cache for signal results
        self._signal_cache = {}
        self._cache_timeout = 30  # 30 seconds cache
        
        # Adaptive signal weights based on performance
        self.adaptive_weights: Dict[str, float] = {}
        self.signal_performance: Dict[str, Dict[str, Any]] = {}
        self.performance_window = 100  # Last 100 signals for performance calculation
        self.weight_adjustment_rate = 0.1  # 10% adjustment per update
        
        # Initialize adaptive weights with base weights
        self._initialize_adaptive_weights()
        
        logger.info("⚖️ Signal Aggregator initialized - Primary signals focus with ML feature extraction")
    
    def _initialize_adaptive_weights(self):
        """Initialize adaptive weights with base signal weights"""
        try:
            for signal_type, source in self.signal_sources_manager.signal_sources.items():
                self.adaptive_weights[signal_type.value] = source.weight
            logger.info("🎯 Adaptive signal weights initialized with base weights")
        except Exception as e:
            logger.error(f"❌ Failed to initialize adaptive weights: {e}")
    
    def update_signal_performance(self, signal_type: str, success: bool, confidence: float):
        """Update signal performance for adaptive weight adjustment"""
        try:
            if signal_type not in self.adaptive_weights:
                return
            
            # Track performance metrics
            if signal_type not in self.signal_performance:
                self.signal_performance[signal_type] = {
                    "total_signals": 0,
                    "successful_signals": 0,
                    "total_confidence": 0.0,
                    "recent_performance": []
                }
            
            perf = self.signal_performance[signal_type]
            perf["total_signals"] += 1
            perf["total_confidence"] += confidence
            
            if success:
                perf["successful_signals"] += 1
            
            # Track recent performance (sliding window)
            perf["recent_performance"].append(success)
            if len(perf["recent_performance"]) > self.performance_window:
                perf["recent_performance"].pop(0)
            
            # Update adaptive weights based on performance
            self._adjust_signal_weight(signal_type)
            
        except Exception as e:
            logger.error(f"❌ Failed to update signal performance: {e}")
    
    def _adjust_signal_weight(self, signal_type: str):
        """Adjust signal weight based on recent performance"""
        try:
            if signal_type not in self.signal_performance:
                return
            
            perf = self.signal_performance[signal_type]
            if len(perf["recent_performance"]) < 10:  # Need minimum data
                return
            
            # Calculate recent success rate
            recent_success_rate = sum(perf["recent_performance"]) / len(perf["recent_performance"])
            
            # Get base weight
            base_weight = self.signal_sources_manager.signal_sources.get(signal_type, {}).get("weight", 0.1)
            
            # Calculate performance adjustment
            if recent_success_rate > 0.6:  # Good performance - increase weight
                adjustment = self.weight_adjustment_rate * (recent_success_rate - 0.5)
                new_weight = min(0.5, self.adaptive_weights[signal_type] + adjustment)
            elif recent_success_rate < 0.4:  # Poor performance - decrease weight
                adjustment = self.weight_adjustment_rate * (0.5 - recent_success_rate)
                new_weight = max(0.01, self.adaptive_weights[signal_type] - adjustment)
            else:  # Neutral performance - slight adjustment toward base
                adjustment = self.weight_adjustment_rate * 0.1 * (base_weight - self.adaptive_weights[signal_type])
                new_weight = self.adaptive_weights[signal_type] + adjustment
            
            # Update adaptive weight
            old_weight = self.adaptive_weights[signal_type]
            self.adaptive_weights[signal_type] = new_weight
            
            logger.debug(f"🎯 {signal_type} weight adjusted: {old_weight:.3f} → {new_weight:.3f} (success rate: {recent_success_rate:.2f})")
            
        except Exception as e:
            logger.error(f"❌ Failed to adjust signal weight: {e}")
    
    def get_adaptive_weight(self, signal_type: str) -> float:
        """Get current adaptive weight for signal type"""
        return self.adaptive_weights.get(signal_type, 0.1)
    
    def _extract_market_components(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize market data components"""
        # Get RSI data from market_data first, fallback to calculator
        rsi = market_data.get("rsi", 50)
        if rsi == 50:  # If not provided in market_data, try calculator
            try:
                rsi_data = get_global_rsi_calculator().get_current_rsi_data()
                rsi = rsi_data.get("rsi", 50)
            except Exception as e:
                logger.warning(f"⚠️ RSI calculator not available: {e}, using fallback RSI=50")
                rsi = 50
        
        # Get trend data
        trend = market_data.get("trend", "NEUTRAL")
        if isinstance(trend, dict):
            trend = trend.get("direction", "NEUTRAL")
        
        # Get multi-timeframe volatility data
        volatility_5m = market_data.get("volatility_5m", 0.0)
        volatility_5m_category = market_data.get("volatility_5m_category", "NORMAL")
        volatility_1m = market_data.get("volatility_1m", 0.0)
        volatility_1h = market_data.get("volatility_1h", 0.0)
        volatility_1d = market_data.get("volatility_1d", 0.0)
        
        # Get volume data
        volume_category = market_data.get("volume_category", "NORMAL")
        volume_data = market_data.get("volume_data", {})
        
        # Get analysis data for ML features
        pattern_analysis = market_data.get("pattern_analysis", {})
        orderbook_analysis = market_data.get("orderbook_analysis", {})
        funding_analysis = market_data.get("funding_analysis", {})
        volume_profile_analysis = market_data.get("volume_profile_analysis", {})
        cross_asset_analysis = market_data.get("cross_asset_analysis", {})
        onchain_analysis = market_data.get("onchain_analysis", {})
        
        return {
            "rsi": rsi,
            "trend": trend,
            "volatility_5m": volatility_5m,
            "volatility_5m_category": volatility_5m_category,
            "volatility_1m": volatility_1m,
            "volatility_1h": volatility_1h,
            "volatility_1d": volatility_1d,
            "volume_category": volume_category,
            "volume_data": volume_data,
            "pattern_analysis": pattern_analysis,
            "orderbook_analysis": orderbook_analysis,
            "funding_analysis": funding_analysis,
            "volume_profile_analysis": volume_profile_analysis,
            "cross_asset_analysis": cross_asset_analysis,
            "onchain_analysis": onchain_analysis
        }
    
    def generate_primary_signals(self, current_price: float, market_data: Dict[str, Any] = None) -> Dict[SignalType, SignalResult]:
        """
        Generate signals from the 3 primary sources:
        1. Market Data (35%)
        2. Psychological Levels (20%) 
        3. Order Book (15%)
        """
        try:
            primary_signals = {}
            market_data = market_data or {}
            
            # 1. Market Data Signal (35% weight)
            market_data_signal = self._generate_market_data_signal(current_price, market_data)
            primary_signals[SignalType.MARKET_DATA] = market_data_signal
            
            # 2. Psychological Levels Signal (20% weight)
            psychological_signal = self._generate_psychological_levels_signal(current_price, market_data)
            primary_signals[SignalType.PSYCHOLOGICAL_LEVELS] = psychological_signal
            
            # 3. Order Book Signal (0% weight - for reactive engine only)
            order_book_signal = self._generate_order_book_signal(current_price, market_data)
            primary_signals[SignalType.ORDER_BOOK] = order_book_signal
            
            # 4. Whale Analytics Signal (10% weight)
            whale_signal = self._generate_whale_analytics_signal(current_price, market_data)
            primary_signals[SignalType.WHALE_ANALYTICS] = whale_signal
            
            # 5. Pattern Analysis Signal (15% weight)
            pattern_signal = self._generate_pattern_analysis_signal(current_price, market_data)
            primary_signals[SignalType.PATTERN_ANALYSIS] = pattern_signal
            
            # 6. RSS News Sentiment Signal (3% weight)
            news_signal = self._generate_rss_news_sentiment_signal(current_price, market_data)
            primary_signals[SignalType.NEWS_SENTIMENT] = news_signal
            
            # 7. Funding Rates Signal (8% weight)
            funding_signal = self._generate_funding_rates_signal(current_price, market_data)
            primary_signals[SignalType.FUNDING_RATES] = funding_signal
            
            # 8. Volume Profile Signal (5% weight)
            volume_profile_signal = self._generate_volume_profile_signal(current_price, market_data)
            primary_signals[SignalType.VOLUME_PROFILE] = volume_profile_signal
            
            # 9. Cross-Asset Signal (4% weight)
            cross_asset_signal = self._generate_cross_asset_signal(current_price, market_data)
            primary_signals[SignalType.CROSS_ASSET] = cross_asset_signal
            
            # 10. On-Chain Signal (3% weight)
            onchain_signal = self._generate_onchain_signal(current_price, market_data)
            primary_signals[SignalType.ONCHAIN_ANALYSIS] = onchain_signal
            
            # Cache the results
            self._signal_cache = {
                "signals": primary_signals,
                "timestamp": time.time(),
                "current_price": current_price
            }
            
            return primary_signals
            
        except Exception as e:
            logger.error(f"❌ Primary signals generation failed: {e}")
            return {}
    
    def extract_ml_features(self, signals: Dict[SignalType, SignalResult], current_price: float, market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract comprehensive ML features from all signals and market data
        This method aggregates all available data for ML model training and prediction
        """
        try:
            ml_features = {
                # Basic market data
                "current_price": current_price,
                "timestamp": time.time(),
                
                # Signal aggregations
                "signal_count": len(signals),
                "total_weighted_confidence": 0.0,
                "signal_directions": {},
                "signal_confidences": {},
                "signal_strengths": {},
                
                # Market data features (from Market Data signal)
                "market_data_features": {},
                
                # Order book features (from Order Book signal)
                "orderbook_features": {},
                
                # Psychological level features (from Psychological Levels signal)
                "psychological_features": {},
                
                # Whale analytics features (from Whale Analytics signal)
                "whale_features": {},
                
                # News sentiment features (from News Sentiment signal)
                "news_features": {},
                
                # Raw market data for additional feature engineering
                "raw_market_data": market_data or {}
            }
            
            # Aggregate signal data
            for signal_type, signal_result in signals.items():
                signal_name = signal_type.value if hasattr(signal_type, 'value') else str(signal_type)
                
                # Aggregate signal directions
                direction = signal_result.direction
                if direction not in ml_features["signal_directions"]:
                    ml_features["signal_directions"][direction] = 0
                ml_features["signal_directions"][direction] += 1
                
                # Aggregate confidences and strengths
                ml_features["signal_confidences"][signal_name] = signal_result.confidence
                ml_features["signal_strengths"][signal_name] = signal_result.strength
                ml_features["total_weighted_confidence"] += signal_result.weighted_confidence
                
                # Extract specific features from each signal type
                if signal_type == SignalType.MARKET_DATA:
                    ml_features["market_data_features"] = signal_result.data
                elif signal_type == SignalType.ORDER_BOOK:
                    ml_features["orderbook_features"] = signal_result.data
                elif signal_type == SignalType.PSYCHOLOGICAL_LEVELS:
                    ml_features["psychological_features"] = signal_result.data
                elif signal_type == SignalType.WHALE_ANALYTICS:
                    ml_features["whale_features"] = signal_result.data
                elif signal_type == SignalType.PATTERN_ANALYSIS:
                    ml_features["pattern_features"] = signal_result.data
                elif signal_type == SignalType.FUNDING_RATES:
                    ml_features["funding_features"] = signal_result.data
                elif signal_type == SignalType.VOLUME_PROFILE:
                    ml_features["volume_profile_features"] = signal_result.data
                elif signal_type == SignalType.CROSS_ASSET:
                    ml_features["cross_asset_features"] = signal_result.data
                elif signal_type == SignalType.ONCHAIN_ANALYSIS:
                    ml_features["onchain_features"] = signal_result.data
                elif signal_type == SignalType.NEWS_SENTIMENT:
                    ml_features["news_features"] = signal_result.data
            
            # Calculate derived features with proper type checking
            ml_features["dominant_direction"] = max(ml_features["signal_directions"], key=ml_features["signal_directions"].get) if ml_features["signal_directions"] else "NEUTRAL"
            ml_features["signal_consensus"] = max(ml_features["signal_directions"].values()) / len(signals) if signals else 0.0
            
            # Safe confidence calculation
            confidence_values = []
            for conf in ml_features["signal_confidences"].values():
                if isinstance(conf, (int, float)):
                    confidence_values.append(conf)
            ml_features["average_confidence"] = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
            
            # Safe strength calculation
            strength_values = []
            for strength in ml_features["signal_strengths"].values():
                if isinstance(strength, (int, float)):
                    strength_values.append(strength)
            ml_features["average_strength"] = sum(strength_values) / len(strength_values) if strength_values else 0.0
            
            # Extract additional features from raw market data
            if market_data:
                # Multi-timeframe volatility features
                ml_features["volatility_features"] = {
                    "volatility_1m": market_data.get("volatility_1m", 0.0),
                    "volatility_5m": market_data.get("volatility_5m", 0.0),
                    "volatility_1h": market_data.get("volatility_1h", 0.0),
                    "volatility_1d": market_data.get("volatility_1d", 0.0),
                    "volatility_5m_category": market_data.get("volatility_5m_category", "NORMAL")
                }
                
                # Volume features
                volume_data = market_data.get("volume_data", {})
                ml_features["volume_features"] = {
                    "volume_category": market_data.get("volume_category", "NORMAL"),
                    "volume_btc": volume_data.get("current_volume_btc", 0.0),
                    "volume_usd": volume_data.get("current_volume_usd", 0.0),
                    "volume_spike_detected": volume_data.get("volume_spike_detected", False),
                    "volume_ratio": volume_data.get("volume_ratio", 1.0)
                }
                
                # Pattern analysis features
                pattern_analysis = market_data.get("pattern_analysis", {})
                ml_features["pattern_features"] = {
                    "overall_confidence": pattern_analysis.get("overall_confidence", 0.0),
                    "pattern_count": pattern_analysis.get("pattern_count", 0),
                    "market_setup": pattern_analysis.get("market_setup", {}).get("setup", "UNKNOWN"),
                    "bullish_patterns": pattern_analysis.get("market_setup", {}).get("bullish_patterns", 0),
                    "bearish_patterns": pattern_analysis.get("market_setup", {}).get("bearish_patterns", 0)
                }
                
                # Support/Resistance features
                support_resistance = market_data.get("support_resistance", {})
                ml_features["support_resistance_features"] = {
                    "strongest_support": support_resistance.get("strongest_support", 0.0),
                    "strongest_resistance": support_resistance.get("strongest_resistance", 0.0),
                    "key_levels_count": len(support_resistance.get("key_levels", [])),
                    "analysis_confidence": support_resistance.get("analysis_confidence", 0.0)
                }
                
                # Analysis features
                ml_features["features"] = {
                    "funding_rate": market_data.get("funding_analysis", {}).get("funding_rate_percentage", 0.0),
                    "cross_asset_correlation": market_data.get("cross_asset_analysis", {}).get("overall_correlation", 0.0),
                    "onchain_sentiment": market_data.get("onchain_analysis", {}).get("sentiment_score", 0.0),
                    "volume_profile_strength": market_data.get("volume_profile_analysis", {}).get("profile_strength", 0.0)
                }
            
            return ml_features
            
        except Exception as e:
            logger.error(f"❌ ML feature extraction failed: {e}")
            return {
                "current_price": current_price,
                "timestamp": time.time(),
                "error": str(e),
                "signal_count": 0,
                "total_weighted_confidence": 0.0
            }
    
    def _generate_market_data_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate Market Data signal (35% weight) - Comprehensive data for ML"""
        try:
            # Extract market data components
            market_components = self._extract_market_components(market_data)
            
            # Calculate signal strength based on multiple factors
            signal_strength = 0.0
            direction = "NEUTRAL"
            reasoning_parts = []
            ml_features = {}
            
            # RSI analysis (25% of signal strength) - More sensitive to near-overbought/oversold
            rsi = market_components["rsi"]
            if rsi < 25:
                signal_strength += 0.25
                direction = "BUY"
                reasoning_parts.append(f"RSI critically oversold ({rsi:.1f})")
            elif rsi < 35:
                signal_strength += 0.15
                if direction == "NEUTRAL":
                    direction = "BUY"
                reasoning_parts.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 75:
                signal_strength += 0.25
                direction = "SELL"
                reasoning_parts.append(f"RSI critically overbought ({rsi:.1f})")
            elif rsi > 65:
                signal_strength += 0.15
                if direction == "NEUTRAL":
                    direction = "SELL"
                reasoning_parts.append(f"RSI overbought ({rsi:.1f})")
            else:
                reasoning_parts.append(f"RSI neutral ({rsi:.1f})")
            
            # Trend analysis (20% of signal strength)
            trend = market_components["trend"]
            if trend == "BULLISH":
                signal_strength += 0.20
                if direction == "NEUTRAL":
                    direction = "BUY"
                reasoning_parts.append("Bullish trend")
            elif trend == "BEARISH":
                signal_strength += 0.20
                if direction == "NEUTRAL":
                    direction = "SELL"
                reasoning_parts.append("Bearish trend")
            else:
                reasoning_parts.append("Neutral trend")
            
            # Multi-timeframe volatility analysis (15% of signal strength)
            volatility_score = 0.0
            volatility_5m_category = market_components["volatility_5m_category"]
            volatility_1m = market_components["volatility_1m"]
            volatility_5m = market_components["volatility_5m"]
            volatility_1h = market_components["volatility_1h"]
            volatility_1d = market_components["volatility_1d"]
            
            if volatility_5m_category in ["HIGH", "VERY_HIGH"]:
                volatility_score += 0.15
                reasoning_parts.append(f"High 5m volatility ({volatility_5m_category})")
            elif volatility_1m > volatility_5m * 1.5:  # Short-term spike
                volatility_score += 0.10
                reasoning_parts.append("Short-term volatility spike")
            elif volatility_1h > volatility_5m * 1.2:  # Medium-term increase
                volatility_score += 0.05
                reasoning_parts.append("Medium-term volatility increase")
            
            signal_strength += volatility_score
            
            # Volume analysis (10% of signal strength)
            volume_category = market_components["volume_category"]
            if volume_category in ["HIGH", "VERY_HIGH", "EXTREMELY_HIGH"]:
                signal_strength += 0.10
                reasoning_parts.append(f"High volume ({volume_category})")
            else:
                reasoning_parts.append(f"Normal volume ({volume_category})")
            
            # Pattern analysis (15% of signal strength) - NEW for ML
            pattern_analysis = market_components["pattern_analysis"]
            pattern_confidence = pattern_analysis.get("overall_confidence", 0.0)
            market_setup = pattern_analysis.get("market_setup", {})
            setup_type = market_setup.get("setup", "UNKNOWN")
            
            if setup_type == "BULLISH" and pattern_confidence > 0.6:
                signal_strength += 0.15
                if direction == "NEUTRAL":
                    direction = "BUY"
                reasoning_parts.append(f"Bullish pattern setup ({pattern_confidence:.2f})")
            elif setup_type == "BEARISH" and pattern_confidence > 0.6:
                signal_strength += 0.15
                if direction == "NEUTRAL":
                    direction = "SELL"
                reasoning_parts.append(f"Bearish pattern setup ({pattern_confidence:.2f})")
            else:
                reasoning_parts.append(f"Neutral patterns ({pattern_confidence:.2f})")
            
            # Order book analysis (10% of signal strength) - NEW for ML
            orderbook_analysis = market_components["orderbook_analysis"]
            orderbook_imbalance = orderbook_analysis.get("imbalance_ratio", 0.5)
            if orderbook_imbalance > 0.6:  # More buy pressure
                signal_strength += 0.10
                if direction == "NEUTRAL":
                    direction = "BUY"
                reasoning_parts.append(f"Buy pressure ({orderbook_imbalance:.2f})")
            elif orderbook_imbalance < 0.4:  # More sell pressure
                signal_strength += 0.10
                if direction == "NEUTRAL":
                    direction = "SELL"
                reasoning_parts.append(f"Sell pressure ({orderbook_imbalance:.2f})")
            else:
                reasoning_parts.append(f"Balanced orderbook ({orderbook_imbalance:.2f})")
            
            # Funding rate analysis (5% of signal strength) - NEW for ML
            funding_analysis = market_components["funding_analysis"]
            funding_rate = funding_analysis.get("funding_rate_percentage", 0.0)
            
            # Get additional analysis data for ML features
            volume_profile_analysis = market_components["volume_profile_analysis"]
            cross_asset_analysis = market_components["cross_asset_analysis"]
            onchain_analysis = market_components["onchain_analysis"]
            if funding_rate > 0.01:  # Positive funding (bullish sentiment)
                signal_strength += 0.05
                reasoning_parts.append(f"Positive funding ({funding_rate:.3f}%)")
            elif funding_rate < -0.01:  # Negative funding (bearish sentiment)
                signal_strength += 0.05
                reasoning_parts.append(f"Negative funding ({funding_rate:.3f}%)")
            else:
                reasoning_parts.append(f"Neutral funding ({funding_rate:.3f}%)")
            
            # Support/Resistance Analysis (35% of signal strength) - MAJOR ENHANCEMENT
            sr_analysis = self._analyze_support_resistance_signals(current_price, market_data)
            signal_strength += sr_analysis["total_strength"]
            reasoning_parts.extend(sr_analysis["reasoning_parts"])
            
            # Update direction based on S/R analysis if stronger than current
            if sr_analysis["strength"] > 0.2:  # Strong S/R signal
                if sr_analysis["direction"] != "NEUTRAL":
                    direction = sr_analysis["direction"]
            
            # IMPROVED CONFIDENCE CALCULATION
            # Base confidence from signal strength
            base_confidence = min(0.95, signal_strength)
            
            # Boost confidence for strong signals
            if signal_strength > 0.6:  # Strong signal
                confidence = min(0.95, base_confidence + 0.2)
            elif signal_strength > 0.4:  # Moderate signal
                confidence = min(0.85, base_confidence + 0.15)
            elif signal_strength > 0.2:  # Weak signal
                confidence = min(0.70, base_confidence + 0.10)
            else:  # Very weak signal
                confidence = min(0.50, base_confidence + 0.05)
            
            # Additional confidence boosts for clear signals
            if rsi < 25 or rsi > 75:  # Extreme RSI
                confidence = min(0.95, confidence + 0.15)
            if volatility_5m_category in ["HIGH", "VERY_HIGH"]:  # High volatility
                confidence = min(0.95, confidence + 0.10)
            if volume_category in ["HIGH", "VERY_HIGH"]:  # High volume
                confidence = min(0.95, confidence + 0.10)
            
            # Ensure minimum confidence for any signal
            confidence = max(0.3, confidence)
            
            # Prepare ML features for future use
            ml_features = {
                "rsi": rsi,
                "trend": trend,
                "volatility_1m": volatility_1m,
                "volatility_5m": volatility_5m,
                "volatility_1h": volatility_1h,
                "volatility_1d": volatility_1d,
                "volatility_5m_category": volatility_5m_category,
                "volume_category": volume_category,
                "pattern_confidence": pattern_confidence,
                "market_setup": setup_type,
                "orderbook_imbalance": orderbook_imbalance,
                "funding_rate": funding_rate,
                "volume_profile": volume_profile_analysis.get("profile_strength", 0.0),
                "cross_asset_correlation": cross_asset_analysis.get("overall_correlation", 0.0),
                "onchain_sentiment": onchain_analysis.get("sentiment_score", 0.0),
                "signal_strength": signal_strength,
                "current_price": current_price
            }
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.MARKET_DATA)
            weight = signal_source.weight if signal_source else 0.35
            
            return SignalResult(
                signal_type=SignalType.MARKET_DATA,
                direction=direction,
                confidence=confidence,
                strength=signal_strength,
                weight=weight,
                weighted_confidence=weight * confidence,
                reasoning=" | ".join(reasoning_parts),
                data=ml_features,  # Data for ML
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ Market Data signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.MARKET_DATA,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.35,
                weighted_confidence=0.0,
                reasoning=f"Market Data signal error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def _generate_psychological_levels_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate Psychological Levels signal (20% weight)"""
        try:
            # Get psychological levels analysis
            psychological_analysis = get_global_psychological_levels_analyzer().calculate_psychological_levels(current_price)
            
            # Generate signal
            signal = get_global_psychological_levels_analyzer().get_psychological_level_signal(current_price, market_data)
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.PSYCHOLOGICAL_LEVELS)
            weight = signal_source.weight if signal_source else 0.20
            
            return SignalResult(
                signal_type=SignalType.PSYCHOLOGICAL_LEVELS,
                direction=signal["direction"],
                confidence=signal["confidence"],
                strength=signal["confidence"],  # Use confidence as strength
                weight=weight,
                weighted_confidence=weight * signal["confidence"],
                reasoning=signal["reasoning"],
                data={
                    "psychological_analysis": psychological_analysis,
                    "trading_bias": signal["trading_bias"],
                    "target_level": signal.get("target_level"),
                    "current_price": current_price
                },
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ Psychological Levels signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.PSYCHOLOGICAL_LEVELS,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.20,
                weighted_confidence=0.0,
                reasoning=f"Psychological Levels signal error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def _generate_order_book_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate Order Book signal (15% weight) - Real order book analysis for ML"""
        try:
            # Get real order book analysis data from market_data
            orderbook_analysis = market_data.get("orderbook_analysis", {})
            pressure_data = market_data.get("pressure_data", {})
            
            # If no real data available, use fallback simulation
            if not orderbook_analysis or not pressure_data:
                # Fallback to simulated data for backward compatibility
                simulated_bids = [
                    {"px": str(int(current_price - 10)), "sz": "5.2"},
                    {"px": str(int(current_price - 20)), "sz": "3.8"},
                    {"px": str(int(current_price - 30)), "sz": "7.1"},
                    {"px": str(int(current_price - 40)), "sz": "4.5"},
                    {"px": str(int(current_price - 50)), "sz": "6.2"}
                ]
                
                simulated_asks = [
                    {"px": str(int(current_price + 10)), "sz": "4.1"},
                    {"px": str(int(current_price + 20)), "sz": "3.2"},
                    {"px": str(int(current_price + 30)), "sz": "5.8"},
                    {"px": str(int(current_price + 40)), "sz": "2.9"},
                    {"px": str(int(current_price + 50)), "sz": "4.7"}
                ]
                
                # Calculate pressure using PressureCalculator
                pressure_data = self.pressure_calculator.calculate_orderbook_pressure(simulated_bids, simulated_asks)
                
                # Calculate volume analysis using VolumeCalculator
                bid_depth = sum(float(level["sz"]) for level in simulated_bids)
                ask_depth = sum(float(level["sz"]) for level in simulated_asks)
                total_depth = bid_depth + ask_depth
                
                # Create volume analysis manually since categorize_orderbook_depth doesn't exist
                volume_analysis = {
                    "order_flow": "NEUTRAL",
                    "total_depth": total_depth,
                    "bid_depth": bid_depth,
                    "ask_depth": ask_depth
                }
                
                # Use fallback data
                orderbook_analysis = {
                    "imbalance_ratio": pressure_data.get("pressure_imbalance", 0.5),
                    "bid_ask_spread": 0.01,  # 1% fallback spread
                    "liquidity_depth": total_depth,
                    "order_flow": volume_analysis.get("order_flow", "NEUTRAL")
                }
            
            # Extract key metrics from real order book analysis with type checking
            imbalance_ratio = orderbook_analysis.get("imbalance_ratio", 0.5)
            bid_ask_spread = orderbook_analysis.get("bid_ask_spread", 0.0)
            liquidity_depth = orderbook_analysis.get("liquidity_depth", 0.0)
            order_flow = orderbook_analysis.get("order_flow", "NEUTRAL")
            
            # Ensure all values are numeric
            if not isinstance(imbalance_ratio, (int, float)):
                imbalance_ratio = 0.5
            if not isinstance(bid_ask_spread, (int, float)):
                bid_ask_spread = 0.0
            if not isinstance(liquidity_depth, (int, float)):
                liquidity_depth = 0.0
            
            # Determine signal direction and confidence based on real data
            direction = "NEUTRAL"
            confidence = 0.5
            strength = 0.5
            reasoning_parts = []
            
            # Imbalance analysis (primary factor)
            if imbalance_ratio > 0.6:  # More buy pressure
                direction = "BUY"
                confidence = min(0.9, 0.5 + (imbalance_ratio - 0.5) * 2)
                strength = confidence
                reasoning_parts.append(f"Buy pressure ({imbalance_ratio:.3f})")
            elif imbalance_ratio < 0.4:  # More sell pressure
                direction = "SELL"
                confidence = min(0.9, 0.5 + (0.5 - imbalance_ratio) * 2)
                strength = confidence
                reasoning_parts.append(f"Sell pressure ({imbalance_ratio:.3f})")
            else:
                reasoning_parts.append(f"Balanced orderbook ({imbalance_ratio:.3f})")
            
            # Spread analysis (secondary factor)
            if bid_ask_spread > 0.02:  # Wide spread (>2%)
                confidence *= 0.8  # Reduce confidence for wide spreads
                reasoning_parts.append(f"Wide spread ({bid_ask_spread:.3f})")
            elif bid_ask_spread < 0.005:  # Tight spread (<0.5%)
                confidence *= 1.1  # Increase confidence for tight spreads
                reasoning_parts.append(f"Tight spread ({bid_ask_spread:.3f})")
            else:
                reasoning_parts.append(f"Normal spread ({bid_ask_spread:.3f})")
            
            # Liquidity analysis (tertiary factor)
            if liquidity_depth > 100:  # High liquidity
                confidence *= 1.05
                reasoning_parts.append(f"High liquidity ({liquidity_depth:.1f})")
            elif liquidity_depth < 20:  # Low liquidity
                confidence *= 0.9
                reasoning_parts.append(f"Low liquidity ({liquidity_depth:.1f})")
            else:
                reasoning_parts.append(f"Normal liquidity ({liquidity_depth:.1f})")
            
            # Order flow confirmation
            if order_flow == "BUY" and direction == "BUY":
                confidence *= 1.1
                reasoning_parts.append("Order flow confirms buy signal")
            elif order_flow == "SELL" and direction == "SELL":
                confidence *= 1.1
                reasoning_parts.append("Order flow confirms sell signal")
            elif order_flow != "NEUTRAL" and direction == "NEUTRAL":
                confidence *= 0.9
                reasoning_parts.append(f"Order flow ({order_flow}) conflicts with neutral signal")
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.ORDER_BOOK)
            weight = signal_source.weight if signal_source else 0.15
            
            # Prepare ML features for order book analysis
            ml_features = {
                "imbalance_ratio": imbalance_ratio,
                "bid_ask_spread": bid_ask_spread,
                "liquidity_depth": liquidity_depth,
                "order_flow": order_flow,
                "pressure_data": pressure_data,
                "orderbook_analysis": orderbook_analysis,
                "current_price": current_price,
                "signal_strength": strength
            }
            
            return SignalResult(
                signal_type=SignalType.ORDER_BOOK,
                direction=direction,
                confidence=min(0.95, confidence),
                strength=strength,
                weight=weight,
                weighted_confidence=weight * confidence,
                reasoning=" | ".join(reasoning_parts),
                data=ml_features,  # Data for ML
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ Order Book signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.ORDER_BOOK,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.15,
                weighted_confidence=0.0,
                reasoning=f"Order Book signal error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def _generate_pattern_analysis_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate Pattern Analysis signal (15% weight) - Comprehensive pattern data for ML"""
        try:
            # Get pattern analysis data from market_data
            pattern_analysis = market_data.get("pattern_analysis", {})
            
            # If no pattern data available, return neutral signal
            if not pattern_analysis:
                return SignalResult(
                    signal_type=SignalType.PATTERN_ANALYSIS,
                    direction="NEUTRAL",
                    confidence=0.0,
                    strength=0.0,
                    weight=0.15,
                    weighted_confidence=0.0,
                    reasoning="Pattern analysis unavailable",
                    data={},
                    timestamp=time.time(),
                    error="No pattern analysis data"
                )
            
            # Extract pattern data
            overall_confidence = pattern_analysis.get("overall_confidence", 0.0)
            pattern_count = pattern_analysis.get("pattern_count", 0)
            market_setup = pattern_analysis.get("market_setup", {})
            setup_type = market_setup.get("setup", "UNKNOWN")
            bullish_patterns = market_setup.get("bullish_patterns", 0)
            bearish_patterns = market_setup.get("bearish_patterns", 0)
            
            # Determine signal direction and confidence based on pattern analysis
            direction = "NEUTRAL"
            confidence = 0.0
            strength = 0.0
            reasoning_parts = []
            
            # Pattern setup analysis (primary factor)
            if setup_type == "BULLISH_SETUP" and overall_confidence > 0.6:
                direction = "BUY"
                confidence = min(0.9, overall_confidence)
                strength = confidence
                reasoning_parts.append(f"Bullish pattern setup ({overall_confidence:.2f})")
            elif setup_type == "BEARISH_SETUP" and overall_confidence > 0.6:
                direction = "SELL"
                confidence = min(0.9, overall_confidence)
                strength = confidence
                reasoning_parts.append(f"Bearish pattern setup ({overall_confidence:.2f})")
            elif setup_type == "NEUTRAL_SETUP":
                direction = "NEUTRAL"
                confidence = 0.3
                strength = 0.3
                reasoning_parts.append(f"Neutral pattern setup ({overall_confidence:.2f})")
            else:
                direction = "NEUTRAL"
                confidence = 0.2
                strength = 0.2
                reasoning_parts.append(f"Unknown pattern setup ({overall_confidence:.2f})")
            
            # Pattern count analysis (secondary factor)
            if pattern_count > 0:
                reasoning_parts.append(f"{pattern_count} patterns detected")
                
                # Adjust confidence based on pattern count
                if pattern_count >= 3:  # Multiple patterns confirm signal
                    confidence = min(0.95, confidence * 1.2)
                    reasoning_parts.append("Multiple patterns confirm signal")
                elif pattern_count == 1:  # Single pattern - moderate confidence
                    confidence = min(0.8, confidence * 0.9)
                    reasoning_parts.append("Single pattern detected")
            else:
                confidence *= 0.5  # Reduce confidence if no patterns
                reasoning_parts.append("No patterns detected")
            
            # Pattern balance analysis (tertiary factor)
            total_patterns = bullish_patterns + bearish_patterns
            if total_patterns > 0:
                pattern_balance = (bullish_patterns - bearish_patterns) / total_patterns
                
                if pattern_balance > 0.5:  # Strong bullish bias
                    if direction == "BUY":
                        confidence = min(0.95, confidence * 1.1)
                    reasoning_parts.append(f"Bullish pattern bias ({bullish_patterns}B/{bearish_patterns}BE)")
                elif pattern_balance < -0.5:  # Strong bearish bias
                    if direction == "SELL":
                        confidence = min(0.95, confidence * 1.1)
                    reasoning_parts.append(f"Bearish pattern bias ({bullish_patterns}B/{bearish_patterns}BE)")
                else:
                    reasoning_parts.append(f"Balanced patterns ({bullish_patterns}B/{bearish_patterns}BE)")
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.PATTERN_ANALYSIS)
            weight = signal_source.weight if signal_source else 0.15
            
            # Prepare ML features for pattern analysis
            ml_features = {
                "overall_confidence": overall_confidence,
                "pattern_count": pattern_count,
                "setup_type": setup_type,
                "bullish_patterns": bullish_patterns,
                "bearish_patterns": bearish_patterns,
                "pattern_balance": (bullish_patterns - bearish_patterns) / max(1, total_patterns),
                "pattern_analysis": pattern_analysis,
                "current_price": current_price,
                "signal_strength": strength
            }
            
            return SignalResult(
                signal_type=SignalType.PATTERN_ANALYSIS,
                direction=direction,
                confidence=min(0.95, confidence),
                strength=strength,
                weight=weight,
                weighted_confidence=weight * confidence,
                reasoning=" | ".join(reasoning_parts),
                data=ml_features,  # Data for ML
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ Pattern Analysis signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.PATTERN_ANALYSIS,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.15,
                weighted_confidence=0.0,
                reasoning=f"Pattern Analysis signal error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def _generate_whale_analytics_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate Whale Analytics signal (10% weight)"""
        try:
            # Get whale analytics data
            whale_data = whale_analytics_api.get_whale_analytics()
            
            if "error" in whale_data:
                return SignalResult(
                    signal_type=SignalType.WHALE_ANALYTICS,
                    direction="NEUTRAL",
                    confidence=0.0,
                    strength=0.0,
                    weight=0.10,
                    weighted_confidence=0.0,
                    reasoning="Whale analytics unavailable",
                    data=whale_data,
                    timestamp=time.time(),
                    error=whale_data.get("error")
                )
            
            # Extract sentiment data
            sentiment = whale_data.get("sentiment", {})
            whale_activity = whale_data.get("whale_activity", {})
            exchange_flows = whale_data.get("exchange_flows", {})
            
            # Determine signal direction and confidence
            sentiment_class = sentiment.get("classification", "neutral")
            sentiment_score = sentiment.get("score", 0.5)
            confidence = sentiment.get("confidence", "low")
            
            # IMPROVED CONFIDENCE CALCULATION
            # Convert sentiment to direction with better confidence
            if sentiment_class == "bullish":
                direction = "BUY"
                confidence_value = 0.8 if confidence == "high" else 0.6  # Increased from 0.7/0.5
            elif sentiment_class == "bearish":
                direction = "SELL"
                confidence_value = 0.8 if confidence == "high" else 0.6  # Increased from 0.7/0.5
            else:
                direction = "NEUTRAL"
                confidence_value = 0.4  # Increased from 0.3
            
            # Adjust confidence based on whale activity
            activity_level = whale_activity.get("activity_level", "low")
            if activity_level in ["high", "very_high"]:
                confidence_value = min(0.9, confidence_value + 0.2)
            elif activity_level == "very_low":
                confidence_value = max(0.1, confidence_value - 0.2)
            
            # Create reasoning
            whale_count = whale_activity.get("whale_count", 0)
            flow_direction = exchange_flows.get("flow_direction", "neutral")
            reasoning = f"Whale sentiment: {sentiment_class} ({confidence}) | {whale_count} whales | Flow: {flow_direction}"
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.WHALE_ANALYTICS)
            weight = signal_source.weight if signal_source else 0.10
            
            return SignalResult(
                signal_type=SignalType.WHALE_ANALYTICS,
                direction=direction,
                confidence=confidence_value,
                strength=confidence_value,
                weight=weight,
                weighted_confidence=weight * confidence_value,
                reasoning=reasoning,
                data={
                    "whale_activity": whale_activity,
                    "exchange_flows": exchange_flows,
                    "sentiment": sentiment,
                    "trading_bias": sentiment.get("trading_bias", "NEUTRAL")
                },
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ Whale analytics signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.WHALE_ANALYTICS,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.10,
                weighted_confidence=0.0,
                reasoning=f"Whale Analytics signal error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def _generate_rss_news_sentiment_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate RSS News Sentiment signal (3% weight)"""
        try:
            # Get RSS news sentiment data
            news_data = rss_news_api.get_news_sentiment()
            
            if not news_data or news_data.get('error'):
                return SignalResult(
                    signal_type=SignalType.NEWS_SENTIMENT,
                    direction="NEUTRAL",
                    confidence=0.0,
                    strength=0.0,
                    weight=0.03,
                    weighted_confidence=0.0,
                    reasoning="RSS news sentiment unavailable",
                    data=news_data,
                    timestamp=time.time(),
                    error=news_data.get("error") if news_data else "No data"
                )
            
            # Extract sentiment data
            sentiment = news_data.get("sentiment", {})
            impact = news_data.get("impact", {})
            trading_signal = news_data.get("trading_signal", {})
            
            # Determine signal direction and confidence
            sentiment_class = sentiment.get("classification", "neutral")
            sentiment_score = sentiment.get("score", 0.0)
            confidence = news_data.get("confidence", 0.1)
            impact_level = impact.get("impact_level", "low")
            
            # Convert sentiment to direction
            if sentiment_class == "bullish":
                direction = "BUY"
            elif sentiment_class == "bearish":
                direction = "SELL"
            else:
                direction = "NEUTRAL"
            
            # Adjust confidence based on impact level and sentiment strength
            confidence_value = confidence
            if impact_level == "high":
                confidence_value = min(0.8, confidence_value + 0.2)
            elif impact_level == "medium":
                confidence_value = min(0.7, confidence_value + 0.1)
            
            # Create reasoning
            bullish_count = sentiment.get("bullish_count", 0)
            bearish_count = sentiment.get("bearish_count", 0)
            articles_analyzed = news_data.get("articles_analyzed", 0)
            sources = news_data.get("sources", [])
            reasoning = f"RSS news: {sentiment_class} ({bullish_count}B/{bearish_count}BE, {articles_analyzed} articles, {len(sources)} sources)"
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.NEWS_SENTIMENT)
            weight = signal_source.weight if signal_source else 0.03
            
            return SignalResult(
                signal_type=SignalType.NEWS_SENTIMENT,
                direction=direction,
                confidence=confidence_value,
                strength=confidence_value,
                weight=weight,
                weighted_confidence=weight * confidence_value,
                reasoning=reasoning,
                data={
                    "sentiment": sentiment,
                    "impact": impact,
                    "trading_signal": trading_signal,
                    "articles_analyzed": articles_analyzed,
                    "sources": sources,
                    "sentiment_score": sentiment_score
                },
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ RSS news sentiment signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.NEWS_SENTIMENT,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.03,
                weighted_confidence=0.0,
                reasoning=f"RSS news sentiment error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def _generate_funding_rates_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate Funding Rates signal (8% weight) - Market bias indicator"""
        try:
            # Get funding analysis data from market_data
            funding_analysis = market_data.get("funding_analysis", {})
            
            if not funding_analysis:
                return SignalResult(
                    signal_type=SignalType.FUNDING_RATES,
                    direction="NEUTRAL",
                    confidence=0.0,
                    strength=0.0,
                    weight=0.08,
                    weighted_confidence=0.0,
                    reasoning="Funding analysis unavailable",
                    data={},
                    timestamp=time.time(),
                    error="No funding analysis data"
                )
            
            # Extract funding data
            funding_rate = funding_analysis.get("funding_rate_percentage", 0.0)
            funding_trend = funding_analysis.get("funding_trend", "NEUTRAL")
            market_bias = funding_analysis.get("market_bias", "NEUTRAL")
            
            # Determine signal direction and confidence based on funding analysis
            direction = "NEUTRAL"
            confidence = 0.0
            strength = 0.0
            reasoning_parts = []
            
            # Funding rate analysis (primary factor)
            if funding_rate > 0.01:  # Positive funding (bullish sentiment)
                direction = "BUY"
                confidence = min(0.8, abs(funding_rate) * 10)  # Scale with funding rate
                strength = confidence
                reasoning_parts.append(f"Positive funding ({funding_rate:.3f}%)")
            elif funding_rate < -0.01:  # Negative funding (bearish sentiment)
                direction = "SELL"
                confidence = min(0.8, abs(funding_rate) * 10)  # Scale with funding rate
                strength = confidence
                reasoning_parts.append(f"Negative funding ({funding_rate:.3f}%)")
            else:
                direction = "NEUTRAL"
                confidence = 0.3
                strength = 0.3
                reasoning_parts.append(f"Neutral funding ({funding_rate:.3f}%)")
            
            # Market bias confirmation
            if market_bias == "BULLISH" and direction == "BUY":
                confidence = min(0.9, confidence * 1.2)
                reasoning_parts.append("Market bias confirms bullish signal")
            elif market_bias == "BEARISH" and direction == "SELL":
                confidence = min(0.9, confidence * 1.2)
                reasoning_parts.append("Market bias confirms bearish signal")
            elif market_bias != "NEUTRAL" and direction == "NEUTRAL":
                confidence *= 0.8
                reasoning_parts.append(f"Market bias ({market_bias}) conflicts with neutral signal")
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.FUNDING_RATES)
            weight = signal_source.weight if signal_source else 0.08
            
            # Prepare ML features for funding analysis
            ml_features = {
                "funding_rate": funding_rate,
                "funding_trend": funding_trend,
                "market_bias": market_bias,
                "funding_analysis": funding_analysis,
                "current_price": current_price,
                "signal_strength": strength
            }
            
            return SignalResult(
                signal_type=SignalType.FUNDING_RATES,
                direction=direction,
                confidence=min(0.95, confidence),
                strength=strength,
                weight=weight,
                weighted_confidence=weight * confidence,
                reasoning=" | ".join(reasoning_parts),
                data=ml_features,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ Funding Rates signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.FUNDING_RATES,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.08,
                weighted_confidence=0.0,
                reasoning=f"Funding Rates signal error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def _generate_volume_profile_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate Volume Profile signal (5% weight) - Trade size distribution"""
        try:
            # Get volume profile analysis data from market_data
            volume_profile_analysis = market_data.get("volume_profile_analysis", {})
            
            if not volume_profile_analysis:
                return SignalResult(
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="NEUTRAL",
                    confidence=0.0,
                    strength=0.0,
                    weight=0.05,
                    weighted_confidence=0.0,
                    reasoning="Volume profile analysis unavailable",
                    data={},
                    timestamp=time.time(),
                    error="No volume profile analysis data"
                )
            
            # Extract volume profile data
            profile_strength = volume_profile_analysis.get("profile_strength", 0.0)
            volume_distribution = volume_profile_analysis.get("volume_distribution", {})
            large_trades_ratio = volume_profile_analysis.get("large_trades_ratio", 0.0)
            
            # Determine signal direction and confidence based on volume profile
            direction = "NEUTRAL"
            confidence = 0.0
            strength = 0.0
            reasoning_parts = []
            
            # Volume profile strength analysis (primary factor)
            if profile_strength > 0.7:  # Strong volume profile
                confidence = min(0.8, profile_strength)
                strength = confidence
                reasoning_parts.append(f"Strong volume profile ({profile_strength:.2f})")
            elif profile_strength > 0.4:  # Moderate volume profile
                confidence = min(0.6, profile_strength)
                strength = confidence
                reasoning_parts.append(f"Moderate volume profile ({profile_strength:.2f})")
            else:
                confidence = 0.3
                strength = 0.3
                reasoning_parts.append(f"Weak volume profile ({profile_strength:.2f})")
            
            # Large trades analysis (secondary factor)
            if large_trades_ratio > 0.3:  # High large trades ratio
                confidence = min(0.9, confidence * 1.3)
                reasoning_parts.append(f"High large trades ratio ({large_trades_ratio:.2f})")
            elif large_trades_ratio < 0.1:  # Low large trades ratio
                confidence *= 0.8
                reasoning_parts.append(f"Low large trades ratio ({large_trades_ratio:.2f})")
            else:
                reasoning_parts.append(f"Normal large trades ratio ({large_trades_ratio:.2f})")
            
            # Volume distribution analysis (tertiary factor)
            if volume_distribution:
                buy_volume = volume_distribution.get("buy_volume", 0.0)
                sell_volume = volume_distribution.get("sell_volume", 0.0)
                total_volume = buy_volume + sell_volume
                
                if total_volume > 0:
                    buy_ratio = buy_volume / total_volume
                    if buy_ratio > 0.6:  # More buy volume
                        direction = "BUY"
                        confidence = min(0.9, confidence * 1.2)
                        reasoning_parts.append(f"Buy volume dominance ({buy_ratio:.2f})")
                    elif buy_ratio < 0.4:  # More sell volume
                        direction = "SELL"
                        confidence = min(0.9, confidence * 1.2)
                        reasoning_parts.append(f"Sell volume dominance ({buy_ratio:.2f})")
                    else:
                        reasoning_parts.append(f"Balanced volume ({buy_ratio:.2f})")
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.VOLUME_PROFILE)
            weight = signal_source.weight if signal_source else 0.05
            
            # Prepare ML features for volume profile analysis
            ml_features = {
                "profile_strength": profile_strength,
                "large_trades_ratio": large_trades_ratio,
                "volume_distribution": volume_distribution,
                "volume_profile_analysis": volume_profile_analysis,
                "current_price": current_price,
                "signal_strength": strength
            }
            
            return SignalResult(
                signal_type=SignalType.VOLUME_PROFILE,
                direction=direction,
                confidence=min(0.95, confidence),
                strength=strength,
                weight=weight,
                weighted_confidence=weight * confidence,
                reasoning=" | ".join(reasoning_parts),
                data=ml_features,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ Volume Profile signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.VOLUME_PROFILE,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.05,
                weighted_confidence=0.0,
                reasoning=f"Volume Profile signal error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def _generate_cross_asset_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate Cross-Asset signal (4% weight) - Market correlations"""
        try:
            # Get cross-asset analysis data from market_data
            cross_asset_analysis = market_data.get("cross_asset_analysis", {})
            
            if not cross_asset_analysis:
                return SignalResult(
                    signal_type=SignalType.CROSS_ASSET,
                    direction="NEUTRAL",
                    confidence=0.0,
                    strength=0.0,
                    weight=0.04,
                    weighted_confidence=0.0,
                    reasoning="Cross-asset analysis unavailable",
                    data={},
                    timestamp=time.time(),
                    error="No cross-asset analysis data"
                )
            
            # Extract cross-asset data with proper type checking
            overall_correlation = cross_asset_analysis.get("overall_correlation", 0.0)
            dxy_correlation = cross_asset_analysis.get("dxy_correlation", 0.0)
            gold_correlation = cross_asset_analysis.get("gold_correlation", 0.0)
            stock_correlation = cross_asset_analysis.get("stock_correlation", 0.0)
            
            # Ensure all correlations are numeric values
            if not isinstance(overall_correlation, (int, float)):
                overall_correlation = 0.0
            if not isinstance(dxy_correlation, (int, float)):
                dxy_correlation = 0.0
            if not isinstance(gold_correlation, (int, float)):
                gold_correlation = 0.0
            if not isinstance(stock_correlation, (int, float)):
                stock_correlation = 0.0
            
            # Determine signal direction and confidence based on cross-asset analysis
            direction = "NEUTRAL"
            confidence = 0.0
            strength = 0.0
            reasoning_parts = []
            
            # Overall correlation analysis (primary factor)
            if abs(overall_correlation) > 0.7:  # Strong correlation
                confidence = min(0.8, abs(overall_correlation))
                strength = confidence
                reasoning_parts.append(f"Strong correlation ({overall_correlation:.2f})")
            elif abs(overall_correlation) > 0.4:  # Moderate correlation
                confidence = min(0.6, abs(overall_correlation))
                strength = confidence
                reasoning_parts.append(f"Moderate correlation ({overall_correlation:.2f})")
            else:
                confidence = 0.3
                strength = 0.3
                reasoning_parts.append(f"Weak correlation ({overall_correlation:.2f})")
            
            # DXY correlation analysis (secondary factor)
            if dxy_correlation < -0.5:  # Strong negative correlation with DXY (bullish for BTC)
                direction = "BUY"
                confidence = min(0.9, confidence * 1.3)
                reasoning_parts.append(f"Strong negative DXY correlation ({dxy_correlation:.2f})")
            elif dxy_correlation > 0.5:  # Strong positive correlation with DXY (bearish for BTC)
                direction = "SELL"
                confidence = min(0.9, confidence * 1.3)
                reasoning_parts.append(f"Strong positive DXY correlation ({dxy_correlation:.2f})")
            else:
                reasoning_parts.append(f"Neutral DXY correlation ({dxy_correlation:.2f})")
            
            # Gold correlation analysis (tertiary factor)
            if gold_correlation > 0.6:  # Strong positive correlation with Gold (bullish)
                if direction == "NEUTRAL":
                    direction = "BUY"
                confidence = min(0.9, confidence * 1.1)
                reasoning_parts.append(f"Strong Gold correlation ({gold_correlation:.2f})")
            elif gold_correlation < -0.6:  # Strong negative correlation with Gold (bearish)
                if direction == "NEUTRAL":
                    direction = "SELL"
                confidence = min(0.9, confidence * 1.1)
                reasoning_parts.append(f"Strong negative Gold correlation ({gold_correlation:.2f})")
            else:
                reasoning_parts.append(f"Neutral Gold correlation ({gold_correlation:.2f})")
            
            # Stock market correlation analysis (quaternary factor)
            if stock_correlation > 0.5:  # Positive correlation with stocks
                reasoning_parts.append(f"Stock market correlation ({stock_correlation:.2f})")
            elif stock_correlation < -0.5:  # Negative correlation with stocks
                reasoning_parts.append(f"Negative stock correlation ({stock_correlation:.2f})")
            else:
                reasoning_parts.append(f"Neutral stock correlation ({stock_correlation:.2f})")
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.CROSS_ASSET)
            weight = signal_source.weight if signal_source else 0.04
            
            # Prepare ML features for cross-asset analysis
            ml_features = {
                "overall_correlation": overall_correlation,
                "dxy_correlation": dxy_correlation,
                "gold_correlation": gold_correlation,
                "stock_correlation": stock_correlation,
                "cross_asset_analysis": cross_asset_analysis,
                "current_price": current_price,
                "signal_strength": strength
            }
            
            return SignalResult(
                signal_type=SignalType.CROSS_ASSET,
                direction=direction,
                confidence=min(0.95, confidence),
                strength=strength,
                weight=weight,
                weighted_confidence=weight * confidence,
                reasoning=" | ".join(reasoning_parts),
                data=ml_features,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ Cross-Asset signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.CROSS_ASSET,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.04,
                weighted_confidence=0.0,
                reasoning=f"Cross-Asset signal error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def _generate_onchain_signal(self, current_price: float, market_data: Dict[str, Any]) -> SignalResult:
        """Generate On-Chain signal (3% weight) - Blockchain data"""
        try:
            # Get on-chain analysis data from market_data
            onchain_analysis = market_data.get("onchain_analysis", {})
            
            if not onchain_analysis:
                return SignalResult(
                    signal_type=SignalType.ONCHAIN_ANALYSIS,
                    direction="NEUTRAL",
                    confidence=0.0,
                    strength=0.0,
                    weight=0.03,
                    weighted_confidence=0.0,
                    reasoning="On-chain analysis unavailable",
                    data={},
                    timestamp=time.time(),
                    error="No on-chain analysis data"
                )
            
            # Extract on-chain data with proper type checking
            sentiment_score = onchain_analysis.get("sentiment_score", 0.0)
            exchange_inflow = onchain_analysis.get("exchange_inflow", 0.0)
            exchange_outflow = onchain_analysis.get("exchange_outflow", 0.0)
            active_addresses = onchain_analysis.get("active_addresses", 0)
            
            # Ensure all values are numeric
            if not isinstance(sentiment_score, (int, float)):
                sentiment_score = 0.0
            if not isinstance(exchange_inflow, (int, float)):
                exchange_inflow = 0.0
            if not isinstance(exchange_outflow, (int, float)):
                exchange_outflow = 0.0
            if not isinstance(active_addresses, (int, float)):
                active_addresses = 0
            
            # Determine signal direction and confidence based on on-chain analysis
            direction = "NEUTRAL"
            confidence = 0.0
            strength = 0.0
            reasoning_parts = []
            
            # Sentiment score analysis (primary factor)
            if sentiment_score > 0.6:  # Bullish sentiment
                direction = "BUY"
                confidence = min(0.8, sentiment_score)
                strength = confidence
                reasoning_parts.append(f"Bullish on-chain sentiment ({sentiment_score:.2f})")
            elif sentiment_score < -0.6:  # Bearish sentiment
                direction = "SELL"
                confidence = min(0.8, abs(sentiment_score))
                strength = confidence
                reasoning_parts.append(f"Bearish on-chain sentiment ({sentiment_score:.2f})")
            else:
                confidence = 0.3
                strength = 0.3
                reasoning_parts.append(f"Neutral on-chain sentiment ({sentiment_score:.2f})")
            
            # Exchange flow analysis (secondary factor)
            net_flow = exchange_outflow - exchange_inflow
            if net_flow > 0:  # Net outflow (bullish - coins leaving exchanges)
                confidence = min(0.9, confidence * 1.2)
                reasoning_parts.append(f"Net exchange outflow ({net_flow:.1f})")
            elif net_flow < 0:  # Net inflow (bearish - coins entering exchanges)
                confidence = min(0.9, confidence * 1.2)
                reasoning_parts.append(f"Net exchange inflow ({net_flow:.1f})")
            else:
                reasoning_parts.append(f"Balanced exchange flow ({net_flow:.1f})")
            
            # Active addresses analysis (tertiary factor)
            if active_addresses > 0:
                if active_addresses > 1000000:  # High activity
                    confidence = min(0.9, confidence * 1.1)
                    reasoning_parts.append(f"High active addresses ({active_addresses:,})")
                elif active_addresses < 500000:  # Low activity
                    confidence *= 0.9
                    reasoning_parts.append(f"Low active addresses ({active_addresses:,})")
                else:
                    reasoning_parts.append(f"Normal active addresses ({active_addresses:,})")
            
            # Get signal source configuration
            signal_source = self.signal_sources_manager.get_signal_source(SignalType.ONCHAIN_ANALYSIS)
            weight = signal_source.weight if signal_source else 0.03
            
            # Prepare ML features for on-chain analysis
            ml_features = {
                "sentiment_score": sentiment_score,
                "exchange_inflow": exchange_inflow,
                "exchange_outflow": exchange_outflow,
                "net_exchange_flow": net_flow,
                "active_addresses": active_addresses,
                "onchain_analysis": onchain_analysis,
                "current_price": current_price,
                "signal_strength": strength
            }
            
            return SignalResult(
                signal_type=SignalType.ONCHAIN_ANALYSIS,
                direction=direction,
                confidence=min(0.95, confidence),
                strength=strength,
                weight=weight,
                weighted_confidence=weight * confidence,
                reasoning=" | ".join(reasoning_parts),
                data=ml_features,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ On-Chain signal generation failed: {e}")
            return SignalResult(
                signal_type=SignalType.ONCHAIN_ANALYSIS,
                direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                weight=0.03,
                weighted_confidence=0.0,
                reasoning=f"On-Chain signal error: {e}",
                data={},
                timestamp=time.time(),
                error=str(e)
            )
    
    def aggregate_signals(self, signals: Dict[SignalType, SignalResult]) -> Dict[str, Any]:
        """
        Aggregate multiple signals into a single trading decision
        
        Args:
            signals: Dictionary of signal results from different sources
            
        Returns:
            Aggregated signal with overall direction, confidence, and quality assessment
        """
        try:
            if not signals:
                return self._get_default_aggregated_signal("No signals available")
            
            # Calculate weighted aggregation
            total_weighted_confidence = 0.0
            total_weight = 0.0
            direction_votes = {"BUY": 0.0, "SELL": 0.0, "NEUTRAL": 0.0}
            signal_components = {}
            errors = []
            
            for signal_type, signal_result in signals.items():
                if signal_result.error:
                    errors.append(f"{signal_type.value}: {signal_result.error}")
                    continue
                
                # Add to weighted confidence
                total_weighted_confidence += signal_result.weighted_confidence
                total_weight += signal_result.weight
                
                # Add to direction votes (weighted)
                direction = signal_result.direction
                if direction in direction_votes:
                    direction_votes[direction] += signal_result.weight
                
                # Store signal component
                signal_components[signal_type.value] = {
                    "direction": signal_result.direction,
                    "confidence": signal_result.confidence,
                    "strength": signal_result.strength,
                    "weight": signal_result.weight,
                    "weighted_confidence": signal_result.weighted_confidence,
                    "reasoning": signal_result.reasoning
                }
            
            # SMART direction determination with market context consideration
            overall_direction, overall_confidence = self._determine_smart_direction(
                direction_votes, signal_components, total_weighted_confidence, total_weight
            )
            
            # Calculate quality metrics
            quality_score = overall_confidence * total_weight  # Quality = confidence * coverage
            signal_strength = self._determine_signal_strength(quality_score, overall_confidence)
            quality_rating = self._determine_quality_rating(quality_score)
            
            # Generate overall reasoning
            overall_reasoning = self._generate_overall_reasoning(signal_components, overall_direction, overall_confidence)
            
            aggregated_signal = {
                "type": "AGGREGATED_PRIMARY_SIGNALS",
                "overall_direction": overall_direction,
                "overall_confidence": overall_confidence,
                "signal_strength": signal_strength,
                "quality_rating": quality_rating,
                "quality_score": quality_score,
                "total_weight": total_weight,
                "weight_coverage": total_weight,  # Should be 0.70 for primary signals
                "direction_votes": direction_votes,
                "signal_components": signal_components,
                "overall_reasoning": overall_reasoning,
                "errors": errors,
                "timestamp": time.time(),
                "recommendation": self._generate_recommendation(quality_rating, overall_direction, overall_confidence)
            }
            
            return aggregated_signal
            
        except Exception as e:
            logger.error(f"❌ Signal aggregation failed: {e}")
            return self._get_default_aggregated_signal(f"Aggregation error: {e}")
    
    def _determine_smart_direction(self, direction_votes: Dict[str, float], signal_components: Dict[str, Any], 
                                 total_weighted_confidence: float, total_weight: float) -> Tuple[str, float]:
        """Smart direction determination considering market context and signal strength"""
        try:
            # Get market data signal for context
            market_data_signal = signal_components.get("market_data", {})
            market_direction = market_data_signal.get("direction", "NEUTRAL")
            market_confidence = market_data_signal.get("confidence", 0.0)
            
            # Check for strong contradictory signals
            buy_votes = direction_votes.get("BUY", 0.0)
            sell_votes = direction_votes.get("SELL", 0.0)
            neutral_votes = direction_votes.get("NEUTRAL", 0.0)
            
            # Calculate vote difference
            vote_difference = abs(buy_votes - sell_votes)
            total_votes = buy_votes + sell_votes + neutral_votes
            
            logger.debug(f"🔍 Smart direction: votes={direction_votes}, difference={vote_difference:.3f}, total={total_votes:.3f}, ratio={vote_difference/total_votes if total_votes > 0 else 0:.3f}")
            
            # If votes are close (within 20% of each other), consider market context
            if total_votes > 0 and vote_difference / total_votes < 0.2:
                # Close vote - use market context to break tie
                if market_direction == "SELL" and market_confidence > 0.6:
                    # Strong sell signal from market data (RSI overbought, etc.)
                    logger.debug(f"🔍 Close vote - using market context: SELL (RSI overbought)")
                    return "SELL", min(0.6, total_weighted_confidence / total_weight if total_weight > 0 else 0.0)
                elif market_direction == "BUY" and market_confidence > 0.6:
                    # Strong buy signal from market data (RSI oversold, etc.)
                    logger.debug(f"🔍 Close vote - using market context: BUY (RSI oversold)")
                    return "BUY", min(0.6, total_weighted_confidence / total_weight if total_weight > 0 else 0.0)
                else:
                    # No strong market context - use NEUTRAL
                    logger.debug(f"🔍 Close vote - no strong market context: NEUTRAL")
                    return "NEUTRAL", 0.3
            
            # Clear winner - use highest weighted vote
            overall_direction = max(direction_votes, key=direction_votes.get)
            overall_confidence = total_weighted_confidence / total_weight if total_weight > 0 else 0.0
            
            logger.debug(f"🔍 Clear winner: {overall_direction} with {overall_confidence:.3f} confidence")
            
            # But reduce confidence if market context strongly contradicts
            if (overall_direction == "BUY" and market_direction == "SELL" and market_confidence > 0.7) or \
               (overall_direction == "SELL" and market_direction == "BUY" and market_confidence > 0.7):
                # Strong contradiction - reduce confidence significantly
                overall_confidence *= 0.5
                logger.debug(f"🔍 Strong contradiction detected - reduced confidence to {overall_confidence:.1%}")
            
            logger.debug(f"🔍 Final result: {overall_direction} with {overall_confidence:.3f} confidence")
            return overall_direction, overall_confidence
            
        except Exception as e:
            logger.error(f"❌ Smart direction determination failed: {e}")
            # Fallback to simple majority
            overall_direction = max(direction_votes, key=direction_votes.get)
            overall_confidence = total_weighted_confidence / total_weight if total_weight > 0 else 0.0
            return overall_direction, overall_confidence
    
    def _determine_signal_strength(self, quality_score: float, confidence: float) -> str:
        """Determine signal strength based on quality score and confidence"""
        if quality_score >= 0.7 and confidence >= 0.8:
            return "VERY_STRONG"
        elif quality_score >= 0.6 and confidence >= 0.7:
            return "STRONG"
        elif quality_score >= 0.4 and confidence >= 0.5:
            return "MODERATE"
        elif quality_score >= 0.2 and confidence >= 0.3:
            return "WEAK"
        else:
            return "VERY_WEAK"
    
    def _determine_quality_rating(self, quality_score: float) -> str:
        """Determine quality rating based on quality score"""
        if quality_score >= 0.8:
            return "EXCELLENT"
        elif quality_score >= 0.6:
            return "GOOD"
        elif quality_score >= 0.4:
            return "FAIR"
        elif quality_score >= 0.2:
            return "POOR"
        else:
            return "VERY_POOR"
    
    def _generate_overall_reasoning(self, signal_components: Dict, overall_direction: str, overall_confidence: float) -> str:
        """Generate detailed overall reasoning for the aggregated signal"""
        reasoning_parts = []
        
        # Count signal directions
        direction_counts = {"BUY": 0, "SELL": 0, "NEUTRAL": 0}
        total_weight = 0
        
        # Add detailed signal analysis
        for signal_type, component in signal_components.items():
            if component["weighted_confidence"] > 0.05:  # Include all meaningful signals
                direction = component["direction"]
                confidence = component["confidence"]
                weight = component["weight"]
                reasoning = component.get("reasoning", "")
                
                # Track direction counts
                if direction in direction_counts:
                    direction_counts[direction] += 1
                
                total_weight += weight
                
                # Format signal contribution
                signal_info = f"{signal_type}: {direction} ({confidence:.1%}, {weight:.1%} weight)"
                if reasoning:
                    signal_info += f" - {reasoning}"
                
                reasoning_parts.append(signal_info)
        
        # Add signal consensus analysis
        if total_weight > 0:
            buy_signals = direction_counts["BUY"]
            sell_signals = direction_counts["SELL"]
            neutral_signals = direction_counts["NEUTRAL"]
            
            if buy_signals > sell_signals and buy_signals > neutral_signals:
                consensus = f"BUY consensus ({buy_signals} signals)"
            elif sell_signals > buy_signals and sell_signals > neutral_signals:
                consensus = f"SELL consensus ({sell_signals} signals)"
            elif neutral_signals > 0:
                consensus = f"Mixed signals (BUY: {buy_signals}, SELL: {sell_signals}, NEUTRAL: {neutral_signals})"
            else:
                consensus = f"Balanced signals (BUY: {buy_signals}, SELL: {sell_signals})"
            
            reasoning_parts.append(f"Signal Consensus: {consensus}")
        
        # Add overall assessment
        reasoning_parts.append(f"Final Decision: {overall_direction} ({overall_confidence:.1%} confidence)")
        
        return " | ".join(reasoning_parts)
    
    def _generate_recommendation(self, quality_rating: str, direction: str, confidence: float) -> str:
        """Generate trading recommendation based on quality and confidence"""
        if quality_rating in ["EXCELLENT", "GOOD"] and confidence >= 0.7:
            return f"Strong {direction.lower()} signal - High confidence trade"
        elif quality_rating in ["GOOD", "FAIR"] and confidence >= 0.5:
            return f"Moderate {direction.lower()} signal - Proceed with caution"
        elif quality_rating == "FAIR" and confidence >= 0.3:
            return f"Weak {direction.lower()} signal - Consider waiting"
        else:
            return "Poor signal quality - Avoid trading"
    
    def _get_default_aggregated_signal(self, error_message: str) -> Dict[str, Any]:
        """Return default aggregated signal when aggregation fails"""
        return {
            "type": "AGGREGATED_PRIMARY_SIGNALS",
            "overall_direction": "NEUTRAL",
            "overall_confidence": 0.0,
            "signal_strength": "VERY_WEAK",
            "quality_rating": "VERY_POOR",
            "quality_score": 0.0,
            "total_weight": 0.0,
            "weight_coverage": 0.0,
            "direction_votes": {"BUY": 0.0, "SELL": 0.0, "NEUTRAL": 0.0},
            "signal_components": {},
            "overall_reasoning": error_message,
            "errors": [error_message],
            "timestamp": time.time(),
            "recommendation": "Signal aggregation failed - Avoid trading"
        }
    
    def get_cached_signals(self) -> Optional[Dict[SignalType, SignalResult]]:
        """Get cached signals if they're still valid"""
        if not self._signal_cache:
            return None
        
        cache_age = time.time() - self._signal_cache.get("timestamp", 0)
        if cache_age > self._cache_timeout:
            return None
        
        return self._signal_cache.get("signals")
    
    def _analyze_support_resistance_signals(self, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze Support/Resistance signals with three components:
        1. S/R Proximity Analysis (10-15% of signal strength)
        2. S/R Breakout Detection (15-20% of signal strength) 
        3. S/R Bounce Validation (10% of signal strength)
        """
        try:
            support_resistance = market_data.get("support_resistance", {})
            key_levels = support_resistance.get("key_levels", [])
            strongest_support = support_resistance.get("strongest_support", 0.0)
            strongest_resistance = support_resistance.get("strongest_resistance", 0.0)
            
            total_strength = 0.0
            reasoning_parts = []
            direction = "NEUTRAL"
            strength = 0.0
            
            if not key_levels and strongest_support == 0.0 and strongest_resistance == 0.0:
                return {
                    "total_strength": 0.0,
                    "strength": 0.0,
                    "direction": "NEUTRAL",
                    "reasoning_parts": ["No S/R levels available"]
                }
            
            # 1. S/R PROXIMITY ANALYSIS (10-15% of signal strength)
            proximity_analysis = self._analyze_sr_proximity(current_price, strongest_support, strongest_resistance, key_levels)
            total_strength += proximity_analysis["strength"]
            reasoning_parts.extend(proximity_analysis["reasoning_parts"])
            
            # 2. S/R BREAKOUT DETECTION (15-20% of signal strength)
            breakout_analysis = self._analyze_sr_breakout(current_price, strongest_support, strongest_resistance, key_levels)
            total_strength += breakout_analysis["strength"]
            reasoning_parts.extend(breakout_analysis["reasoning_parts"])
            
            # 3. S/R BOUNCE VALIDATION (10% of signal strength)
            bounce_analysis = self._analyze_sr_bounce(current_price, strongest_support, strongest_resistance, key_levels)
            total_strength += bounce_analysis["strength"]
            reasoning_parts.extend(bounce_analysis["reasoning_parts"])
            
            # Determine overall direction based on strongest signal
            if proximity_analysis["strength"] > breakout_analysis["strength"] and proximity_analysis["strength"] > bounce_analysis["strength"]:
                direction = proximity_analysis["direction"]
                strength = proximity_analysis["strength"]
            elif breakout_analysis["strength"] > bounce_analysis["strength"]:
                direction = breakout_analysis["direction"]
                strength = breakout_analysis["strength"]
            else:
                direction = bounce_analysis["direction"]
                strength = bounce_analysis["strength"]
            
            return {
                "total_strength": total_strength,
                "strength": strength,
                "direction": direction,
                "reasoning_parts": reasoning_parts
            }
            
        except Exception as e:
            logger.error(f"❌ S/R signal analysis failed: {e}")
            return {
                "total_strength": 0.0,
                "strength": 0.0,
                "direction": "NEUTRAL",
                "reasoning_parts": [f"S/R analysis error: {e}"]
            }
    
    def _analyze_sr_proximity(self, current_price: float, strongest_support: float, strongest_resistance: float, key_levels: List[Dict]) -> Dict[str, Any]:
        """Analyze proximity to support/resistance levels (10-15% of signal strength)"""
        try:
            strength = 0.0
            direction = "NEUTRAL"
            reasoning_parts = []
            
            # Define proximity thresholds
            very_close_threshold = 0.002  # 0.2% - very close
            close_threshold = 0.005       # 0.5% - close
            moderate_threshold = 0.01     # 1.0% - moderate
            
            # Check proximity to strongest support
            if strongest_support > 0:
                support_distance = (current_price - strongest_support) / current_price
                if 0 <= support_distance <= very_close_threshold:
                    strength += 0.15  # Very close to support - strong buy signal
                    direction = "BUY"
                    reasoning_parts.append(f"Very close to support ${strongest_support:,.0f} ({support_distance*100:.1f}%)")
                elif 0 <= support_distance <= close_threshold:
                    strength += 0.12  # Close to support - moderate buy signal
                    if direction == "NEUTRAL":
                        direction = "BUY"
                    reasoning_parts.append(f"Close to support ${strongest_support:,.0f} ({support_distance*100:.1f}%)")
                elif 0 <= support_distance <= moderate_threshold:
                    strength += 0.08  # Moderate proximity to support - weak buy signal
                    if direction == "NEUTRAL":
                        direction = "BUY"
                    reasoning_parts.append(f"Near support ${strongest_support:,.0f} ({support_distance*100:.1f}%)")
            
            # Check proximity to strongest resistance
            if strongest_resistance > 0:
                resistance_distance = (strongest_resistance - current_price) / current_price
                if 0 <= resistance_distance <= very_close_threshold:
                    strength += 0.15  # Very close to resistance - strong sell signal
                    direction = "SELL"
                    reasoning_parts.append(f"Very close to resistance ${strongest_resistance:,.0f} ({resistance_distance*100:.1f}%)")
                elif 0 <= resistance_distance <= close_threshold:
                    strength += 0.12  # Close to resistance - moderate sell signal
                    if direction == "NEUTRAL":
                        direction = "SELL"
                    reasoning_parts.append(f"Close to resistance ${strongest_resistance:,.0f} ({resistance_distance*100:.1f}%)")
                elif 0 <= resistance_distance <= moderate_threshold:
                    strength += 0.08  # Moderate proximity to resistance - weak sell signal
                    if direction == "NEUTRAL":
                        direction = "SELL"
                    reasoning_parts.append(f"Near resistance ${strongest_resistance:,.0f} ({resistance_distance*100:.1f}%)")
            
            # Check proximity to key levels with high intelligence scores
            for level in key_levels:
                if level.get("intelligence_score", 0) > 5.0:  # High-quality level
                    level_price = level["level"]
                    level_distance = abs(current_price - level_price) / current_price
                    
                    if level_distance <= very_close_threshold:
                        if level["type"] == "support":
                            strength += 0.10  # Additional strength for high-quality support
                            if direction == "NEUTRAL":
                                direction = "BUY"
                            reasoning_parts.append(f"Near strong support ${level_price:,.0f} (score: {level['intelligence_score']:.1f})")
                        else:  # resistance
                            strength += 0.10  # Additional strength for high-quality resistance
                            if direction == "NEUTRAL":
                                direction = "SELL"
                            reasoning_parts.append(f"Near strong resistance ${level_price:,.0f} (score: {level['intelligence_score']:.1f})")
            
            return {
                "strength": min(0.15, strength),  # Cap at 15%
                "direction": direction,
                "reasoning_parts": reasoning_parts
            }
            
        except Exception as e:
            logger.error(f"❌ S/R proximity analysis failed: {e}")
            return {"strength": 0.0, "direction": "NEUTRAL", "reasoning_parts": []}
    
    def _analyze_sr_breakout(self, current_price: float, strongest_support: float, strongest_resistance: float, key_levels: List[Dict]) -> Dict[str, Any]:
        """Analyze support/resistance breakouts (15-20% of signal strength)"""
        try:
            strength = 0.0
            direction = "NEUTRAL"
            reasoning_parts = []
            
            # Define breakout thresholds
            breakout_threshold = 0.003  # 0.3% - breakout confirmed
            strong_breakout_threshold = 0.008  # 0.8% - strong breakout
            
            # Check for resistance breakout (bullish)
            if strongest_resistance > 0:
                breakout_distance = (current_price - strongest_resistance) / strongest_resistance
                if breakout_distance >= strong_breakout_threshold:
                    strength += 0.20  # Strong resistance breakout - very bullish
                    direction = "BUY"
                    reasoning_parts.append(f"Strong resistance breakout ${strongest_resistance:,.0f} (+{breakout_distance*100:.1f}%)")
                elif breakout_distance >= breakout_threshold:
                    strength += 0.15  # Resistance breakout - bullish
                    direction = "BUY"
                    reasoning_parts.append(f"Resistance breakout ${strongest_resistance:,.0f} (+{breakout_distance*100:.1f}%)")
            
            # Check for support breakdown (bearish)
            if strongest_support > 0:
                breakdown_distance = (strongest_support - current_price) / strongest_support
                if breakdown_distance >= strong_breakout_threshold:
                    strength += 0.20  # Strong support breakdown - very bearish
                    direction = "SELL"
                    reasoning_parts.append(f"Strong support breakdown ${strongest_support:,.0f} (-{breakdown_distance*100:.1f}%)")
                elif breakdown_distance >= breakout_threshold:
                    strength += 0.15  # Support breakdown - bearish
                    direction = "SELL"
                    reasoning_parts.append(f"Support breakdown ${strongest_support:,.0f} (-{breakdown_distance*100:.1f}%)")
            
            # Check for key level breakouts with high intelligence scores
            for level in key_levels:
                if level.get("intelligence_score", 0) > 7.0:  # Very high-quality level
                    level_price = level["level"]
                    
                    if level["type"] == "resistance":
                        breakout_distance = (current_price - level_price) / level_price
                        if breakout_distance >= breakout_threshold:
                            strength += 0.12  # Additional strength for high-quality resistance breakout
                            if direction == "NEUTRAL":
                                direction = "BUY"
                            reasoning_parts.append(f"Key resistance breakout ${level_price:,.0f} (score: {level['intelligence_score']:.1f})")
                    
                    elif level["type"] == "support":
                        breakdown_distance = (level_price - current_price) / level_price
                        if breakdown_distance >= breakout_threshold:
                            strength += 0.12  # Additional strength for high-quality support breakdown
                            if direction == "NEUTRAL":
                                direction = "SELL"
                            reasoning_parts.append(f"Key support breakdown ${level_price:,.0f} (score: {level['intelligence_score']:.1f})")
            
            return {
                "strength": min(0.20, strength),  # Cap at 20%
                "direction": direction,
                "reasoning_parts": reasoning_parts
            }
            
        except Exception as e:
            logger.error(f"❌ S/R breakout analysis failed: {e}")
            return {"strength": 0.0, "direction": "NEUTRAL", "reasoning_parts": []}
    
    def _analyze_sr_bounce(self, current_price: float, strongest_support: float, strongest_resistance: float, key_levels: List[Dict]) -> Dict[str, Any]:
        """Analyze support/resistance bounces (10% of signal strength)"""
        try:
            strength = 0.0
            direction = "NEUTRAL"
            reasoning_parts = []
            
            # Define bounce thresholds
            bounce_threshold = 0.001  # 0.1% - bounce detected
            strong_bounce_threshold = 0.003  # 0.3% - strong bounce
            
            # Check for support bounce (bullish)
            if strongest_support > 0:
                bounce_distance = (current_price - strongest_support) / strongest_support
                if bounce_distance >= strong_bounce_threshold:
                    strength += 0.10  # Strong support bounce - bullish
                    direction = "BUY"
                    reasoning_parts.append(f"Strong support bounce ${strongest_support:,.0f} (+{bounce_distance*100:.1f}%)")
                elif bounce_distance >= bounce_threshold:
                    strength += 0.08  # Support bounce - moderately bullish
                    if direction == "NEUTRAL":
                        direction = "BUY"
                    reasoning_parts.append(f"Support bounce ${strongest_support:,.0f} (+{bounce_distance*100:.1f}%)")
            
            # Check for resistance rejection (bearish)
            if strongest_resistance > 0:
                rejection_distance = (strongest_resistance - current_price) / strongest_resistance
                if rejection_distance >= strong_bounce_threshold:
                    strength += 0.10  # Strong resistance rejection - bearish
                    direction = "SELL"
                    reasoning_parts.append(f"Strong resistance rejection ${strongest_resistance:,.0f} (-{rejection_distance*100:.1f}%)")
                elif rejection_distance >= bounce_threshold:
                    strength += 0.08  # Resistance rejection - moderately bearish
                    if direction == "NEUTRAL":
                        direction = "SELL"
                    reasoning_parts.append(f"Resistance rejection ${strongest_resistance:,.0f} (-{rejection_distance*100:.1f}%)")
            
            # Check for key level bounces with high touch counts
            for level in key_levels:
                if level.get("touches", 0) >= 3:  # Level with multiple touches
                    level_price = level["level"]
                    level_distance = abs(current_price - level_price) / level_price
                    
                    if level_distance <= 0.002:  # Very close to level
                        if level["type"] == "support" and current_price > level_price:
                            strength += 0.06  # Additional strength for multi-touch support bounce
                            if direction == "NEUTRAL":
                                direction = "BUY"
                            reasoning_parts.append(f"Multi-touch support bounce ${level_price:,.0f} ({level['touches']} touches)")
                        elif level["type"] == "resistance" and current_price < level_price:
                            strength += 0.06  # Additional strength for multi-touch resistance rejection
                            if direction == "NEUTRAL":
                                direction = "SELL"
                            reasoning_parts.append(f"Multi-touch resistance rejection ${level_price:,.0f} ({level['touches']} touches)")
            
            return {
                "strength": min(0.10, strength),  # Cap at 10%
                "direction": direction,
                "reasoning_parts": reasoning_parts
            }
            
        except Exception as e:
            logger.error(f"❌ S/R bounce analysis failed: {e}")
            return {"strength": 0.0, "direction": "NEUTRAL", "reasoning_parts": []}


# Global instance for easy access - lazy initialization
def global_signal_aggregator():
    return SignalAggregator()
