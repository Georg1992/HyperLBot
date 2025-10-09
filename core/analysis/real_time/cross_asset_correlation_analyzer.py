#!/usr/bin/env python3
"""
Cross-Asset Correlation Analyzer Module
Analyzes correlations with DXY, Gold, and Stock indices for market context
"""

import time
# import requests  # Removed unused import
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger

# Singleton pattern implementation
_global_cross_asset_correlation_analyzer = None

def get_global_cross_asset_correlation_analyzer() -> 'CrossAssetCorrelationAnalyzer':
    """Get the global CrossAssetCorrelationAnalyzer singleton instance"""
    global _global_cross_asset_correlation_analyzer
    if _global_cross_asset_correlation_analyzer is None:
        _global_cross_asset_correlation_analyzer = CrossAssetCorrelationAnalyzer()
    return _global_cross_asset_correlation_analyzer

class CrossAssetCorrelationAnalyzer:
    """Analyzes cross-asset correlations for broader market context"""
    
    def __init__(self):
        # Cache for external data to avoid excessive API calls
        self._data_cache = {}
        self._cache_timestamps = {}
        self._cache_duration = 300  # 5 minutes cache for external data
        
        # Correlation history for trend analysis
        self._correlation_history = []
        self._max_history = 50  # Keep last 50 correlation readings
        
        logger.info("📊 Cross-Asset Correlation Analyzer initialized")
    
    def analyze_cross_asset_correlations(self, btc_price: float) -> Dict[str, Any]:
        """
        Analyze cross-asset correlations for market context
        
        Args:
            btc_price: Current Bitcoin price for correlation calculations
            
        Returns:
            Dictionary with cross-asset correlation analysis
        """
        try:
            # Get external market data
            dxy_data = self._get_dxy_data()
            gold_data = self._get_gold_data()
            stock_data = self._get_stock_indices_data()
            
            # Calculate correlations
            analysis = {
                "dxy_correlation": self._analyze_dxy_correlation(dxy_data, btc_price),
                "gold_correlation": self._analyze_gold_correlation(gold_data, btc_price),
                "stock_correlation": self._analyze_stock_correlation(stock_data, btc_price),
                "market_regime": self._determine_cross_asset_regime(dxy_data, gold_data, stock_data),
                "risk_sentiment": self._analyze_risk_sentiment(dxy_data, gold_data, stock_data),
                "correlation_trends": self._analyze_correlation_trends(),
                "timestamp": time.time(),
                "data_source": "external_apis"
            }
            
            # Update correlation history
            self._update_correlation_history(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Cross-asset correlation analysis failed: {e}")
            raise Exception(f"Cross-asset correlation analysis failed: {e}")
    
    def _get_dxy_data(self) -> Dict[str, Any]:
        """Get DXY (Dollar Index) data"""
        try:
            cache_key = "dxy_data"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Use Yahoo Finance API for DXY data
            from core.external.yahoo_finance_api import get_global_yahoo_finance_api
            yahoo_api = get_global_yahoo_finance_api()
            
            dxy_data = yahoo_api.get_dxy_data()
            
            # Cache the data
            self._cache_data(cache_key, dxy_data)
            
            return dxy_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get DXY data: {e}")
            raise ValueError(f"DXY data fetch failed - NO FALLBACKS: {e}")
    
    def _get_gold_data(self) -> Dict[str, Any]:
        """Get Gold price data"""
        try:
            cache_key = "gold_data"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Use Yahoo Finance API for Gold data
            from core.external.yahoo_finance_api import get_global_yahoo_finance_api
            yahoo_api = get_global_yahoo_finance_api()
            
            gold_data = yahoo_api.get_gold_data()
            
            # Cache the data
            self._cache_data(cache_key, gold_data)
            
            return gold_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get Gold data: {e}")
            raise ValueError(f"Gold data fetch failed - NO FALLBACKS: {e}")
    
    def _get_stock_indices_data(self) -> Dict[str, Any]:
        """Get major stock indices data"""
        try:
            cache_key = "stock_indices_data"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Use Yahoo Finance API for Stock indices data
            from core.external.yahoo_finance_api import get_global_yahoo_finance_api
            yahoo_api = get_global_yahoo_finance_api()
            
            stock_data = yahoo_api.get_stock_indices_data()
            
            # Cache the data
            self._cache_data(cache_key, stock_data)
            
            return stock_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get stock indices data: {e}")
            raise ValueError(f"Stock data fetch failed - NO FALLBACKS: {e}")
    
    def _analyze_dxy_correlation(self, dxy_data: Dict[str, Any], btc_price: float) -> Dict[str, Any]:
        """Analyze DXY correlation with Bitcoin"""
        try:
            if not dxy_data or dxy_data.get("price", 0) == 0:
                return {"correlation": 0.0, "strength": "UNKNOWN", "interpretation": "No DXY data"}
            
            dxy_price = dxy_data["price"]
            dxy_change = dxy_data.get("change_percent", 0)
            
            # Historical correlation: DXY and BTC typically have negative correlation
            # Strong DXY (dollar strength) usually correlates with weaker BTC
            base_correlation = -0.6  # Historical negative correlation
            
            # Adjust correlation based on current trends
            if dxy_change > 0.5:  # Strong DXY increase
                correlation_strength = "STRONG_NEGATIVE"
                interpretation = "Strong dollar strength - bearish for BTC"
            elif dxy_change > 0.1:  # Moderate DXY increase
                correlation_strength = "MODERATE_NEGATIVE"
                interpretation = "Dollar strengthening - slightly bearish for BTC"
            elif dxy_change < -0.5:  # Strong DXY decrease
                correlation_strength = "STRONG_POSITIVE"
                interpretation = "Dollar weakening - bullish for BTC"
            elif dxy_change < -0.1:  # Moderate DXY decrease
                correlation_strength = "MODERATE_POSITIVE"
                interpretation = "Dollar weakening - slightly bullish for BTC"
            else:
                correlation_strength = "NEUTRAL"
                interpretation = "DXY stable - neutral for BTC"
            
            return {
                "correlation": base_correlation,
                "strength": correlation_strength,
                "interpretation": interpretation,
                "dxy_price": dxy_price,
                "dxy_change_pct": dxy_change,
                "dxy_trend": dxy_data.get("trend", "UNKNOWN")
            }
            
        except Exception as e:
            logger.error(f"❌ DXY correlation analysis failed: {e}")
            return {"correlation": 0.0, "strength": "ERROR", "interpretation": "Analysis failed"}
    
    def _analyze_gold_correlation(self, gold_data: Dict[str, Any], btc_price: float) -> Dict[str, Any]:
        """Analyze Gold correlation with Bitcoin"""
        try:
            if not gold_data or gold_data.get("price", 0) == 0:
                return {"correlation": 0.0, "strength": "UNKNOWN", "interpretation": "No Gold data"}
            
            gold_price = gold_data["price"]
            gold_change = gold_data.get("change_percent", 0)
            
            # Historical correlation: Gold and BTC have positive correlation (both safe havens)
            base_correlation = 0.4  # Historical positive correlation
            
            # Adjust correlation based on current trends
            if gold_change > 1.0:  # Strong Gold increase
                correlation_strength = "STRONG_POSITIVE"
                interpretation = "Gold rally - bullish for BTC (safe haven demand)"
            elif gold_change > 0.2:  # Moderate Gold increase
                correlation_strength = "MODERATE_POSITIVE"
                interpretation = "Gold strength - slightly bullish for BTC"
            elif gold_change < -1.0:  # Strong Gold decrease
                correlation_strength = "STRONG_NEGATIVE"
                interpretation = "Gold weakness - bearish for BTC (risk-off sentiment)"
            elif gold_change < -0.2:  # Moderate Gold decrease
                correlation_strength = "MODERATE_NEGATIVE"
                interpretation = "Gold weakness - slightly bearish for BTC"
            else:
                correlation_strength = "NEUTRAL"
                interpretation = "Gold stable - neutral for BTC"
            
            return {
                "correlation": base_correlation,
                "strength": correlation_strength,
                "interpretation": interpretation,
                "gold_price": gold_price,
                "gold_change_pct": gold_change,
                "gold_trend": gold_data.get("trend", "UNKNOWN")
            }
            
        except Exception as e:
            logger.error(f"❌ Gold correlation analysis failed: {e}")
            return {"correlation": 0.0, "strength": "ERROR", "interpretation": "Analysis failed"}
    
    def _analyze_stock_correlation(self, stock_data: Dict[str, Any], btc_price: float) -> Dict[str, Any]:
        """Analyze stock market correlation with Bitcoin"""
        try:
            if not stock_data or not stock_data.get("indices"):
                return {"correlation": 0.0, "strength": "UNKNOWN", "interpretation": "No stock data"}
            
            # Use composite data from Yahoo Finance
            composite_change = stock_data.get("composite_change", 0)
            composite_price = stock_data.get("composite_price", 0)
            indices_data = stock_data.get("indices", {})
            
            # Calculate average stock market performance
            changes = []
            trends = []
            
            for index_name, index_data in indices_data.items():
                if index_data:
                    changes.append(index_data.get("change_percent", 0))
                    trends.append("UNKNOWN")  # Yahoo Finance doesn't provide trend
            
            if not changes:
                return {"correlation": 0.0, "strength": "UNKNOWN", "interpretation": "No valid stock data"}
            
            avg_change = sum(changes) / len(changes)
            
            # Historical correlation: Stocks and BTC have moderate positive correlation
            base_correlation = 0.3  # Historical positive correlation
            
            # Adjust correlation based on current trends
            if avg_change > 1.0:  # Strong stock rally
                correlation_strength = "STRONG_POSITIVE"
                interpretation = "Stock rally - bullish for BTC (risk-on sentiment)"
            elif avg_change > 0.2:  # Moderate stock increase
                correlation_strength = "MODERATE_POSITIVE"
                interpretation = "Stock strength - slightly bullish for BTC"
            elif avg_change < -1.0:  # Strong stock decline
                correlation_strength = "STRONG_NEGATIVE"
                interpretation = "Stock selloff - bearish for BTC (risk-off sentiment)"
            elif avg_change < -0.2:  # Moderate stock decline
                correlation_strength = "MODERATE_NEGATIVE"
                interpretation = "Stock weakness - slightly bearish for BTC"
            else:
                correlation_strength = "NEUTRAL"
                interpretation = "Stocks stable - neutral for BTC"
            
            return {
                "correlation": base_correlation,
                "strength": correlation_strength,
                "interpretation": interpretation,
                "avg_stock_change_pct": avg_change,
                "stock_trends": trends,
                "indices_data": indices_data
            }
            
        except Exception as e:
            logger.error(f"❌ Stock correlation analysis failed: {e}")
            return {"correlation": 0.0, "strength": "ERROR", "interpretation": "Analysis failed"}
    
    def _determine_cross_asset_regime(self, dxy_data: Dict[str, Any], gold_data: Dict[str, Any], stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall market regime based on cross-asset analysis"""
        try:
            # Analyze each asset's trend
            dxy_trend = dxy_data.get("trend", "UNKNOWN")
            gold_trend = gold_data.get("trend", "UNKNOWN")
            
            # Get stock trend
            stock_trends = []
            for index in ["sp500", "nasdaq", "dow"]:
                if index in stock_data and stock_data[index]:
                    stock_trends.append(stock_data[index].get("trend", "UNKNOWN"))
            
            # Determine market regime
            if dxy_trend in ["STRONG_UP", "UP"] and gold_trend in ["STRONG_DOWN", "DOWN"] and any("DOWN" in t for t in stock_trends):
                regime = "RISK_OFF"
                description = "Dollar strength, Gold weakness, Stock decline - Risk-off environment"
                btc_outlook = "BEARISH"
            elif dxy_trend in ["STRONG_DOWN", "DOWN"] and gold_trend in ["STRONG_UP", "UP"] and any("UP" in t for t in stock_trends):
                regime = "RISK_ON"
                description = "Dollar weakness, Gold strength, Stock rally - Risk-on environment"
                btc_outlook = "BULLISH"
            elif dxy_trend in ["SIDEWAYS", "WEAK_UP", "WEAK_DOWN"] and gold_trend in ["SIDEWAYS", "WEAK_UP", "WEAK_DOWN"]:
                regime = "NEUTRAL"
                description = "Mixed signals across assets - Neutral environment"
                btc_outlook = "NEUTRAL"
            else:
                regime = "MIXED"
                description = "Conflicting signals across assets - Mixed environment"
                btc_outlook = "UNCERTAIN"
            
            return {
                "regime": regime,
                "description": description,
                "btc_outlook": btc_outlook,
                "confidence": 0.7 if regime in ["RISK_OFF", "RISK_ON"] else 0.5,
                "factors": {
                    "dxy_trend": dxy_trend,
                    "gold_trend": gold_trend,
                    "stock_trends": stock_trends
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Market regime determination failed: {e}")
            return {"regime": "UNKNOWN", "description": "Analysis failed", "btc_outlook": "UNCERTAIN"}
    
    def _analyze_risk_sentiment(self, dxy_data: Dict[str, Any], gold_data: Dict[str, Any], stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall risk sentiment"""
        try:
            # Collect risk indicators
            risk_indicators = []
            
            # DXY as risk indicator (strong DXY = risk-off)
            dxy_change = dxy_data.get("change_24h_pct", 0)
            if dxy_change > 0.5:
                risk_indicators.append("DOLLAR_STRENGTH")
            elif dxy_change < -0.5:
                risk_indicators.append("DOLLAR_WEAKNESS")
            
            # Gold as safe haven indicator
            gold_change = gold_data.get("change_24h_pct", 0)
            if gold_change > 1.0:
                risk_indicators.append("SAFE_HAVEN_DEMAND")
            elif gold_change < -1.0:
                risk_indicators.append("RISK_TAKING")
            
            # Stock market as risk indicator
            stock_changes = []
            for index in ["sp500", "nasdaq", "dow"]:
                if index in stock_data and stock_data[index]:
                    stock_changes.append(stock_data[index].get("change_24h_pct", 0))
            
            if stock_changes:
                avg_stock_change = sum(stock_changes) / len(stock_changes)
                if avg_stock_change > 1.0:
                    risk_indicators.append("STOCK_RALLY")
                elif avg_stock_change < -1.0:
                    risk_indicators.append("STOCK_SELLOFF")
            
            # Determine overall risk sentiment
            risk_off_indicators = ["DOLLAR_STRENGTH", "SAFE_HAVEN_DEMAND", "STOCK_SELLOFF"]
            risk_on_indicators = ["DOLLAR_WEAKNESS", "RISK_TAKING", "STOCK_RALLY"]
            
            risk_off_count = sum(1 for indicator in risk_indicators if indicator in risk_off_indicators)
            risk_on_count = sum(1 for indicator in risk_indicators if indicator in risk_on_indicators)
            
            if risk_off_count > risk_on_count:
                sentiment = "RISK_OFF"
                strength = "STRONG" if risk_off_count >= 2 else "MODERATE"
            elif risk_on_count > risk_off_count:
                sentiment = "RISK_ON"
                strength = "STRONG" if risk_on_count >= 2 else "MODERATE"
            else:
                sentiment = "NEUTRAL"
                strength = "WEAK"
            
            return {
                "sentiment": sentiment,
                "strength": strength,
                "indicators": risk_indicators,
                "risk_off_count": risk_off_count,
                "risk_on_count": risk_on_count,
                "btc_implication": "BEARISH" if sentiment == "RISK_OFF" else "BULLISH" if sentiment == "RISK_ON" else "NEUTRAL"
            }
            
        except Exception as e:
            logger.error(f"❌ Risk sentiment analysis failed: {e}")
            return {"sentiment": "UNKNOWN", "strength": "WEAK", "indicators": [], "btc_implication": "UNCERTAIN"}
    
    def _analyze_correlation_trends(self) -> Dict[str, Any]:
        """Analyze correlation trends over time"""
        try:
            if len(self._correlation_history) < 5:
                return {"trend": "INSUFFICIENT_DATA", "direction": "UNKNOWN"}
            
            # Get recent correlations
            recent_correlations = self._correlation_history[-10:]
            
            # Analyze trend direction
            dxy_correlations = [c.get("dxy_correlation", {}).get("correlation", 0) for c in recent_correlations]
            gold_correlations = [c.get("gold_correlation", {}).get("correlation", 0) for c in recent_correlations]
            stock_correlations = [c.get("stock_correlation", {}).get("correlation", 0) for c in recent_correlations]
            
            # Calculate trend direction
            dxy_trend = "STABLE"
            if len(dxy_correlations) >= 2:
                if dxy_correlations[-1] > dxy_correlations[0] + 0.1:
                    dxy_trend = "INCREASING"
                elif dxy_correlations[-1] < dxy_correlations[0] - 0.1:
                    dxy_trend = "DECREASING"
            
            return {
                "trend": "ANALYZED",
                "dxy_trend": dxy_trend,
                "data_points": len(recent_correlations),
                "recent_dxy_correlation": dxy_correlations[-1] if dxy_correlations else 0,
                "recent_gold_correlation": gold_correlations[-1] if gold_correlations else 0,
                "recent_stock_correlation": stock_correlations[-1] if stock_correlations else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Correlation trend analysis failed: {e}")
            return {"trend": "ERROR", "direction": "UNKNOWN"}
    
    def _update_correlation_history(self, analysis: Dict[str, Any]):
        """Update correlation history for trend analysis"""
        try:
            self._correlation_history.append(analysis)
            
            # Keep only recent history
            if len(self._correlation_history) > self._max_history:
                self._correlation_history = self._correlation_history[-self._max_history:]
                
        except Exception as e:
            logger.error(f"❌ Failed to update correlation history: {e}")
    
    def _get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if still valid"""
        if key in self._data_cache and key in self._cache_timestamps:
            if time.time() - self._cache_timestamps[key] < self._cache_duration:
                return self._data_cache[key]
        return None
    
    def _cache_data(self, key: str, data: Dict[str, Any]):
        """Cache data with timestamp"""
        self._data_cache[key] = data
        self._cache_timestamps[key] = time.time()
    
