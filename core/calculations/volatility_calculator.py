#!/usr/bin/env python3
"""
Enhanced Volatility Calculator - Refactored Version
Modular architecture with dependency injection and optimized performance
"""

import time
from typing import Dict, List, Any, Optional
from loguru import logger

# Import modular components
from .volatility_data_provider import VolatilityDataProvider
from .volatility_analyzer import VolatilityAnalyzer
from .volatility_classifier import VolatilityClassifier
from .base_calculator import BaseCalculator


class VolatilityCalculator(BaseCalculator):
    """
    Enhanced Volatility Calculator with modular architecture.
    
    Refactored to use dependency injection for better testability and maintainability.
    Delegates responsibilities to specialized components.
    """
    
    def __init__(self, symbol: str = "BTC",
                 data_provider: Optional[VolatilityDataProvider] = None,
                 analyzer: Optional[VolatilityAnalyzer] = None,
                 classifier: Optional[VolatilityClassifier] = None):
        """
        Initialize the refactored Volatility Calculator
        
        Args:
            symbol: Trading symbol (default: "BTC")
            data_provider: VolatilityDataProvider instance (injected dependency)
            analyzer: VolatilityAnalyzer instance (injected dependency)
            classifier: VolatilityClassifier instance (injected dependency)
        """
        # Initialize base class
        super().__init__(symbol)
        
        # Dependency injection with defaults
        self._data_provider = data_provider or VolatilityDataProvider(symbol)
        self._analyzer = analyzer or VolatilityAnalyzer()
        self._classifier = classifier or VolatilityClassifier()
        
        logger.info(f"📊 Refactored Volatility Calculator initialized for {symbol} - Modular architecture")
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        """
        Get latest volatility analysis using the refactored modular system
        
        Returns:
            Volatility analysis dictionary
        """
        try:
            # Fetch candle data via data provider
            candles = self._data_provider.fetch_candle_data("5m", 30)
            
            if not candles or len(candles) < 1:
                logger.warning("⚠️ No candle data available for volatility analysis")
                return self._create_error_result("No candle data available")
            
            # Calculate volatility using modular components
            return self.calculate_candle_volatility(candles, "5m", "standard")
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest volatility analysis: {e}")
            return self._create_error_result(str(e))
    
    def calculate_candle_volatility(self, candles: List[Dict], timeframe: str = "5m", strategy: str = "standard") -> Dict[str, Any]:
        """
        Calculate volatility using the refactored modular system
        
        Args:
            candles: List of candle dictionaries
            timeframe: Timeframe of the candles
            strategy: Trading strategy (for compatibility)
        
        Returns:
            Volatility analysis dictionary
        """
        try:
            if len(candles) < 1:
                logger.warning(f"⚠️ Not enough candles for volatility calculation: {len(candles)} < 1")
                return self._create_error_result(f"Insufficient candles: {len(candles)} < 1")
            
            # 1. Get basic volatility from data provider
            basic_vol_data = self._data_provider.calculate_basic_volatility(candles, 15)
            
            # 2. Calculate weighted volatility from analyzer
            weighted_vol_data = self._analyzer.calculate_weighted_volatility(candles)
            
            # 3. Detect volatility spikes
            current_vol = weighted_vol_data.get("current_volatility", 0.0)
            spike_data = self._analyzer.detect_volatility_spikes(current_vol, 0.01)
            
            # 4. Calculate primary volatility
            primary_volatility = self._analyzer.calculate_primary_volatility(
                basic_vol_data.get("volatility", 0.0),
                weighted_vol_data.get("weighted_volatility", 0.0),
                current_vol,
                spike_data.get("is_spike", False)
            )
            
            # 5. Classify volatility level
            classification = self._classifier.classify_volatility_level(primary_volatility)
            
            # 6. Determine trading suitability
            suitability = self._classifier.determine_trading_suitability(
                primary_volatility, 
                classification.get("level", "UNKNOWN")
            )
            
            # 7. Get recommendations
            recommendations = self._classifier.get_volatility_recommendations(
                primary_volatility,
                classification.get("level", "UNKNOWN")
            )
            
            # 8. Format results
            result = {
                "volatility": primary_volatility,
                "volatility_percentage": primary_volatility * 100,
                "level": classification.get("level", "UNKNOWN"),
                "description": classification.get("description", ""),
                "suitable_for_trading": suitability.get("suitable_for_trading", False),
                "risk_level": suitability.get("risk_level", "UNKNOWN"),
                "recommendations": recommendations.get("recommendations", []),
                "analysis_details": {
                    "basic_volatility": basic_vol_data.get("volatility", 0.0),
                    "weighted_volatility": weighted_vol_data.get("weighted_volatility", 0.0),
                    "current_volatility": current_vol,
                    "is_spike": spike_data.get("is_spike", False),
                    "spike_intensity": spike_data.get("spike_intensity", "NONE"),
                    "price_range": basic_vol_data.get("range", 0.0),
                    "avg_price": basic_vol_data.get("avg_price", 0.0),
                    "candle_count": basic_vol_data.get("candle_count", 0)
                },
                "thresholds": classification.get("thresholds", {}),
                "timestamp": time.time(),
                "timeframe": timeframe,
                "strategy": strategy
            }
            
            logger.info(f"📊 Volatility analysis complete: {classification.get('level', 'UNKNOWN')} ({primary_volatility*100:.4f}%)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation failed: {e}")
            return self._create_error_result(str(e))
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create volatility-specific error result"""
        base_result = super()._create_error_result(error_message)
        return {
            **base_result,
            "volatility": 0.0,
            "volatility_percentage": 0.0,
            "level": "ERROR",
            "description": f"Calculation failed: {error_message}",
            "suitable_for_trading": False,
            "risk_level": "UNKNOWN",
            "recommendations": ["Analysis failed - use caution"],
            "analysis_details": {},
            "thresholds": {}
        }
    
    def invalidate_cache(self):
        """Clear all cached volatility data to force fresh calculation"""
        try:
            self._cache.invalidate_pattern("volatility_*")
            self._data_provider.invalidate_cache()
            logger.info("📊 Volatility cache invalidated - next calculation will be fresh")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate volatility cache: {e}")


# Factory function for backward compatibility
def create_volatility_calculator(symbol: str = "BTC") -> VolatilityCalculator:
    """
    Factory function to create VolatilityCalculator with dependency injection
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Configured VolatilityCalculator instance
    """
    return VolatilityCalculator(symbol=symbol)
