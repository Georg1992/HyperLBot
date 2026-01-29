#!/usr/bin/env python3
"""
Enhanced Volatility Calculator - Refactored Version
Modular architecture with dependency injection and optimized performance
"""

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
        Get latest volatility analysis using the refactored modular system - NO FALLBACKS
        
        Returns:
            Volatility analysis dictionary
        
        Raises:
            ValueError: If candle data is not available or insufficient
        """
        try:
            # Fetch candle data via data provider - NO FALLBACKS
            candles = self._data_provider.fetch_candle_data("5m", 30)
            
            if not candles or len(candles) < 1:
                raise ValueError("No candle data available for volatility analysis - NO FALLBACKS")
            
            # Calculate volatility using modular components - NO FALLBACKS
            return self.calculate_candle_volatility(candles, "5m", "standard")
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest volatility analysis: {e}")
            raise
    
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
                raise ValueError(f"Insufficient candles for volatility calculation: {len(candles)} < 1 - NO FALLBACKS")
            
            # 1. Get basic volatility from data provider - NO FALLBACKS
            # Use 15 minutes (3 candles) - balanced: responsive but not too noisy
            basic_vol_data = self._data_provider.calculate_basic_volatility(candles, 15)
            
            # 2. Calculate weighted volatility from analyzer
            weighted_vol_data = self._analyzer.calculate_weighted_volatility(candles)
            
            basic_vol = basic_vol_data["volatility"] if "volatility" in basic_vol_data else 0.0
            weighted_vol = weighted_vol_data["weighted_volatility"] if "weighted_volatility" in weighted_vol_data else 0.0
            current_vol = weighted_vol_data["current_volatility"] if "current_volatility" in weighted_vol_data else 0.0

            # 3. Detect volatility spikes (relative + absolute)
            spike_data = self._analyzer.detect_volatility_spikes(
                current_vol, weighted_vol, basic_vol
            )
            is_spike = spike_data["is_spike"]
            spike_intensity = spike_data["spike_intensity"]

            # 4. Adaptive blending -> primary volatility
            primary_volatility, baseline, ratio = self._analyzer.calculate_primary_volatility(
                basic_vol, weighted_vol, current_vol, is_spike, spike_intensity
            )

            # 5. Classify volatility level
            classification = self._classifier.classify_volatility_level(primary_volatility)
            volatility_level = classification["level"] if "level" in classification else "UNKNOWN"

            if is_spike:
                logger.debug(
                    f"📊 Volatility spike: current={current_vol:.6f} weighted={weighted_vol:.6f} "
                    f"basic={basic_vol:.6f} baseline={baseline:.6f} ratio={ratio:.2f} "
                    f"intensity={spike_intensity} primary={primary_volatility:.6f}"
                )

            # 6. Output – same keys; no unused debug fields (baseline/ratio removed per audit)
            result = {
                "volatility": primary_volatility,
                "volatility_5m": primary_volatility,
                "volatility_percentage": primary_volatility * 100,
                "level": volatility_level,
                "category": volatility_level,
                "volatility_category": volatility_level,
                "spike_intensity": spike_intensity,
            }
            
            logger.info(f"📊 Volatility analysis complete: {volatility_level} ({primary_volatility*100:.4f}%)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation failed: {e}")
            raise  # NO FALLBACKS - calculation failure should raise, not return error dict
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create volatility-specific error result"""
        base_result = super()._create_error_result(error_message)
        return {
            **base_result,
            "volatility": 0.0,
            "volatility_5m": 0.0,
            "volatility_percentage": 0.0,
            "level": "ERROR",
            "category": "ERROR",
            "volatility_category": "ERROR"
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
