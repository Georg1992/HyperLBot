#!/usr/bin/env python3
"""
Feature Engineering for ML Models
=================================
Transforms raw market data into ML-ready features
"""

# import time  # Removed unused import
import numpy as np
# import pandas as pd  # Removed unused import
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger

class FeatureEngineer:
    """Engineers features from raw market data for ML models"""
    
    def __init__(self):
        self.feature_names = []
        self.feature_stats = {}
        
        logger.info("🔧 Feature Engineer initialized")
    
    def extract_ml_features(self, market_data: Dict[str, Any], signals: Dict[str, Any] = None) -> np.ndarray:
        """
        Extract and engineer features from market data and signals
        
        Args:
            market_data: Raw market data from MarketDataManager
            signals: Optional signal data (deprecated, kept for backward compatibility)
            
        Returns:
            numpy array of engineered features
        """
        try:
            # Debug logging for market data
            logger.debug(f"🔧 Feature extraction - market_data keys: {list(market_data.keys())}")
            logger.debug(f"🔧 Feature extraction - signals type: {type(signals)}, keys: {list(signals.keys()) if signals else 'None'}")
            
            features = []
            feature_names = []
            
            # 1. Price-based features
            price_features, price_names = self._extract_price_features(market_data)
            features.extend(price_features)
            feature_names.extend(price_names)
            
            # 2. Technical indicator features
            technical_features, technical_names = self._extract_technical_features(market_data)
            features.extend(technical_features)
            feature_names.extend(technical_names)
            
            # 3. Volume features
            volume_features, volume_names = self._extract_volume_features(market_data)
            features.extend(volume_features)
            feature_names.extend(volume_names)
            
            # 4. Volatility features
            volatility_features, volatility_names = self._extract_volatility_features(market_data)
            features.extend(volatility_features)
            feature_names.extend(volatility_names)
            
            # 5. Pattern features
            pattern_features, pattern_names = self._extract_pattern_features(market_data)
            features.extend(pattern_features)
            feature_names.extend(pattern_names)
            
            # 6. Order book features
            orderbook_features, orderbook_names = self._extract_orderbook_features(market_data)
            features.extend(orderbook_features)
            feature_names.extend(orderbook_names)
            
            # 7. Cross-asset features
            cross_asset_features, cross_asset_names = self._extract_cross_asset_features(market_data)
            features.extend(cross_asset_features)
            feature_names.extend(cross_asset_names)
            
            # 8. On-chain features
            onchain_features, onchain_names = self._extract_onchain_features(market_data)
            features.extend(onchain_features)
            feature_names.extend(onchain_names)
            
            # 9. Signal features
            if signals:
                signal_features, signal_names = self._extract_signal_features(signals)
                features.extend(signal_features)
                feature_names.extend(signal_names)
            
            # 10. Derived features
            derived_features, derived_names = self._create_derived_features(features, feature_names)
            features.extend(derived_features)
            feature_names.extend(derived_names)
            
            # Store feature names for reference
            self.feature_names = feature_names
            
            # Filter out non-numeric features before numpy conversion
            numeric_features = []
            numeric_names = []
            for i, feature in enumerate(features):
                if isinstance(feature, (int, float)) and not np.isnan(feature):
                    numeric_features.append(feature)
                    numeric_names.append(feature_names[i])
                else:
                    logger.debug(f"🔧 Skipping non-numeric feature: {feature_names[i]} = {feature}")
            
            # Convert to numpy array
            feature_array = np.array(numeric_features, dtype=np.float32)
            
            # Handle NaN values
            feature_array = np.nan_to_num(feature_array, nan=0.0, posinf=1.0, neginf=-1.0)
            
            logger.debug(f"🔧 Extracted {len(feature_array)} features for ML")
            if len(feature_array) == 0:
                logger.warning(f"⚠️ No numeric features extracted! Total features: {len(features)}, Numeric features: {len(numeric_features)}")
                logger.warning(f"⚠️ Feature types: {[type(f) for f in features[:10]]}")
            
            return feature_array
            
        except Exception as e:
            logger.error(f"❌ Feature extraction failed: {e}")
            return np.array([])
    
    def _extract_price_features(self, market_data: Dict[str, Any]) -> Tuple[List[float], List[str]]:
        """Extract price-based features"""
        features = []
        names = []
        
        current_price = market_data.get("current_price", 0.0)
        
        # Basic price features
        features.append(current_price)
        names.append("current_price")
        
        # Price normalization (log scale)
        if current_price > 0:
            features.append(np.log(current_price))
            names.append("log_price")
        
        # Support/Resistance features
        support_resistance = market_data.get("support_resistance", {})
        strongest_support = support_resistance.get("strongest_support", 0.0)
        strongest_resistance = support_resistance.get("strongest_resistance", 0.0)
        
        if strongest_support > 0:
            features.append((current_price - strongest_support) / strongest_support)
            names.append("support_distance_ratio")
        else:
            features.append(0.0)
            names.append("support_distance_ratio")
        
        if strongest_resistance > 0:
            features.append((strongest_resistance - current_price) / current_price)
            names.append("resistance_distance_ratio")
        else:
            features.append(0.0)
            names.append("resistance_distance_ratio")
        
        return features, names
    
    def _extract_technical_features(self, market_data: Dict[str, Any]) -> Tuple[List[float], List[str]]:
        """Extract technical indicator features"""
        features = []
        names = []
        
        # RSI features
        rsi = market_data.get("rsi", 50.0)
        features.append(rsi)
        names.append("rsi")
        
        # RSI normalized (0-1 scale)
        features.append(rsi / 100.0)
        names.append("rsi_normalized")
        
        # RSI momentum (distance from 50)
        features.append(abs(rsi - 50.0) / 50.0)
        names.append("rsi_momentum")
        
        # Trend features
        trend_analysis = market_data.get("trend_analysis", {})
        trend_5m = trend_analysis.get("trend_5m", "NEUTRAL")
        trend_1h = trend_analysis.get("trend_1h", "NEUTRAL")
        
        # Encode trends as numbers
        trend_encoding = {"BULLISH": 1.0, "NEUTRAL": 0.0, "BEARISH": -1.0}
        features.append(trend_encoding.get(trend_5m, 0.0))
        names.append("trend_5m_encoded")
        
        features.append(trend_encoding.get(trend_1h, 0.0))
        names.append("trend_1h_encoded")
        
        # Trend alignment
        if trend_5m == trend_1h:
            features.append(1.0)  # Aligned
        else:
            features.append(0.0)  # Not aligned
        names.append("trend_alignment")
        
        return features, names
    
    def _extract_volume_features(self, market_data: Dict[str, Any]) -> Tuple[List[float], List[str]]:
        """Extract volume-based features"""
        features = []
        names = []
        
        # Volume data
        volume_data = market_data.get("volume_data", {})
        volume_btc = volume_data.get("current_volume_btc", 0.0)
        volume_usd = volume_data.get("current_volume_usd", 0.0)
        
        features.append(volume_btc)
        names.append("volume_btc")
        
        features.append(volume_usd)
        names.append("volume_usd")
        
        # Volume ratio
        volume_ratio = volume_data.get("volume_ratio", 1.0)
        features.append(volume_ratio)
        names.append("volume_ratio")
        
        # Volume spike detection
        volume_spike = volume_data.get("volume_spike_detected", False)
        features.append(1.0 if volume_spike else 0.0)
        names.append("volume_spike")
        
        # Volume category encoding
        volume_category = market_data.get("volume_category", "NORMAL")
        volume_categories = {
            "VERY_LOW": 0.0, "LOW": 0.2, "NORMAL": 0.4, "ABOVE_AVERAGE": 0.6,
            "HIGH": 0.8, "VERY_HIGH": 0.9, "EXTREMELY_HIGH": 1.0
        }
        features.append(volume_categories.get(volume_category, 0.4))
        names.append("volume_category_encoded")
        
        return features, names
    
    def _extract_volatility_features(self, market_data: Dict[str, Any]) -> Tuple[List[float], List[str]]:
        """Extract volatility features"""
        features = []
        names = []
        
        # Multi-timeframe volatility
        volatility_1m = market_data.get("volatility_1m", 0.0)
        volatility_5m = market_data.get("volatility_5m", 0.0)
        volatility_1h = market_data.get("volatility_1h", 0.0)
        volatility_1d = market_data.get("volatility_1d", 0.0)
        
        features.extend([volatility_1m, volatility_5m, volatility_1h, volatility_1d])
        names.extend(["volatility_1m", "volatility_5m", "volatility_1h", "volatility_1d"])
        
        # Volatility ratios
        if volatility_5m > 0:
            features.append(volatility_1m / volatility_5m)
            names.append("volatility_1m_5m_ratio")
        else:
            features.append(0.0)
            names.append("volatility_1m_5m_ratio")
        
        if volatility_1h > 0:
            features.append(volatility_5m / volatility_1h)
            names.append("volatility_5m_1h_ratio")
        else:
            features.append(0.0)
            names.append("volatility_5m_1h_ratio")
        
        # Volatility category encoding
        volatility_category = market_data.get("volatility_5m_category", "NORMAL")
        volatility_categories = {
            "VERY_LOW": 0.0, "LOW": 0.2, "NORMAL": 0.4, "HIGH": 0.6, "VERY_HIGH": 0.8
        }
        features.append(volatility_categories.get(volatility_category, 0.4))
        names.append("volatility_category_encoded")
        
        return features, names
    
    def _extract_pattern_features(self, market_data: Dict[str, Any]) -> Tuple[List[float], List[str]]:
        """Extract pattern recognition features"""
        features = []
        names = []
        
        pattern_analysis = market_data.get("pattern_analysis", {})
        
        # Overall pattern confidence
        overall_confidence = pattern_analysis.get("overall_confidence", 0.0)
        features.append(overall_confidence)
        names.append("pattern_confidence")
        
        # Pattern count
        pattern_count = pattern_analysis.get("pattern_count", 0)
        features.append(float(pattern_count))
        names.append("pattern_count")
        
        # Market setup
        market_setup = pattern_analysis.get("market_setup", {})
        setup_type = market_setup.get("setup", "UNKNOWN")
        
        setup_encoding = {
            "BULLISH_SETUP": 1.0, "NEUTRAL_SETUP": 0.0, "BEARISH_SETUP": -1.0, "UNKNOWN": 0.0
        }
        features.append(setup_encoding.get(setup_type, 0.0))
        names.append("market_setup_encoded")
        
        # Pattern counts by type
        bullish_patterns = market_setup.get("bullish_patterns", 0)
        bearish_patterns = market_setup.get("bearish_patterns", 0)
        
        features.extend([float(bullish_patterns), float(bearish_patterns)])
        names.extend(["bullish_patterns", "bearish_patterns"])
        
        # Pattern balance
        total_patterns = bullish_patterns + bearish_patterns
        if total_patterns > 0:
            features.append((bullish_patterns - bearish_patterns) / total_patterns)
        else:
            features.append(0.0)
        names.append("pattern_balance")
        
        return features, names
    
    def _extract_orderbook_features(self, market_data: Dict[str, Any]) -> Tuple[List[float], List[str]]:
        """Extract order book features"""
        features = []
        names = []
        
        orderbook_analysis = market_data.get("orderbook_analysis", {})
        
        # Imbalance ratio
        imbalance_ratio = orderbook_analysis.get("imbalance_ratio", 0.5)
        features.append(imbalance_ratio)
        names.append("orderbook_imbalance")
        
        # Bid-ask spread
        bid_ask_spread = orderbook_analysis.get("bid_ask_spread", 0.0)
        features.append(bid_ask_spread)
        names.append("bid_ask_spread")
        
        # Liquidity depth
        liquidity_depth = orderbook_analysis.get("liquidity_depth", 0.0)
        features.append(liquidity_depth)
        names.append("liquidity_depth")
        
        # Order flow
        order_flow = orderbook_analysis.get("order_flow", "NEUTRAL")
        flow_encoding = {"BUY": 1.0, "NEUTRAL": 0.0, "SELL": -1.0}
        features.append(flow_encoding.get(order_flow, 0.0))
        names.append("order_flow_encoded")
        
        return features, names
    
    def _extract_cross_asset_features(self, market_data: Dict[str, Any]) -> Tuple[List[float], List[str]]:
        """Extract cross-asset correlation features"""
        features = []
        names = []
        
        cross_asset_analysis = market_data.get("cross_asset_analysis", {})
        
        # Overall correlation
        overall_correlation = cross_asset_analysis.get("overall_correlation", 0.0)
        features.append(overall_correlation)
        names.append("cross_asset_correlation")
        
        # Individual correlations
        dxy_correlation = cross_asset_analysis.get("dxy_correlation", 0.0)
        gold_correlation = cross_asset_analysis.get("gold_correlation", 0.0)
        stock_correlation = cross_asset_analysis.get("stock_correlation", 0.0)
        
        features.extend([dxy_correlation, gold_correlation, stock_correlation])
        names.extend(["dxy_correlation", "gold_correlation", "stock_correlation"])
        
        return features, names
    
    def _extract_onchain_features(self, market_data: Dict[str, Any]) -> Tuple[List[float], List[str]]:
        """Extract on-chain features"""
        features = []
        names = []
        
        onchain_analysis = market_data.get("onchain_analysis", {})
        
        # Sentiment score
        sentiment_score = onchain_analysis.get("sentiment_score", 0.0)
        features.append(sentiment_score)
        names.append("onchain_sentiment")
        
        # Exchange flows
        exchange_flows = onchain_analysis.get("exchange_flows", {})
        inflow = exchange_flows.get("inflow", 0.0)
        outflow = exchange_flows.get("outflow", 0.0)
        
        features.extend([inflow, outflow])
        names.extend(["exchange_inflow", "exchange_outflow"])
        
        # Net flow
        if inflow + outflow > 0:
            features.append((inflow - outflow) / (inflow + outflow))
        else:
            features.append(0.0)
        names.append("net_exchange_flow")
        
        return features, names
    
    def _extract_signal_features(self, signals: Dict[str, Any]) -> Tuple[List[float], List[str]]:
        """Extract signal-based features"""
        features = []
        names = []
        
        # Signal consensus
        signal_consensus = signals.get("signal_consensus", 0.0)
        features.append(signal_consensus)
        names.append("signal_consensus")
        
        # Average confidence
        average_confidence = signals.get("average_confidence", 0.0)
        features.append(average_confidence)
        names.append("average_confidence")
        
        # Signal directions
        signal_directions = signals.get("signal_directions", {})
        buy_signals = signal_directions.get("BUY", 0)
        sell_signals = signal_directions.get("SELL", 0)
        neutral_signals = signal_directions.get("NEUTRAL", 0)
        
        total_signals = buy_signals + sell_signals + neutral_signals
        if total_signals > 0:
            features.append((buy_signals - sell_signals) / total_signals)
        else:
            features.append(0.0)
        names.append("signal_direction_balance")
        
        return features, names
    
    def _create_derived_features(self, features: List[float], names: List[str]) -> Tuple[List[float], List[str]]:
        """Create derived features from existing features"""
        derived_features = []
        derived_names = []
        
        if len(features) < 2:
            return derived_features, derived_names
        
        # Filter out non-numeric features
        numeric_features = []
        numeric_names = []
        for i, feature in enumerate(features):
            if isinstance(feature, (int, float)) and not np.isnan(feature):
                numeric_features.append(feature)
                numeric_names.append(names[i])
        
        if len(numeric_features) < 2:
            return derived_features, derived_names
        
        # Create feature combinations
        feature_array = np.array(numeric_features)
        
        # Feature interactions (if we have enough features)
        if len(numeric_features) >= 5:
            # RSI * Volatility interaction (if both exist)
            rsi_idx = next((i for i, name in enumerate(numeric_names) if "rsi" in name.lower()), None)
            vol_idx = next((i for i, name in enumerate(numeric_names) if "volatility_5m" in name.lower()), None)
            
            if rsi_idx is not None and vol_idx is not None:
                interaction = numeric_features[rsi_idx] * numeric_features[vol_idx]
                derived_features.append(interaction)
                derived_names.append("rsi_volatility_interaction")
        
        # Feature statistics
        if len(numeric_features) > 0:
            derived_features.extend([
                np.mean(feature_array),
                np.std(feature_array),
                np.max(feature_array),
                np.min(feature_array)
            ])
            derived_names.extend([
                "feature_mean", "feature_std", "feature_max", "feature_min"
            ])
        
        return derived_features, derived_names
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        return self.feature_names.copy()
    
    def get_feature_importance(self, model, feature_names: List[str] = None) -> Dict[str, float]:
        """Get feature importance from trained model"""
        if not hasattr(model, 'feature_importances_'):
            return {}
        
        names = feature_names or self.feature_names
        if len(names) != len(model.feature_importances_):
            logger.warning("⚠️ Feature names length doesn't match model features")
            return {}
        
        return dict(zip(names, model.feature_importances_))

# Global feature engineer instance
global_feature_engineer = FeatureEngineer()
