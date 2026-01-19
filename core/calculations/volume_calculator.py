#!/usr/bin/env python3
"""
Volume Calculator - Clean Architecture
Simple, working implementation with factory function
"""

import time
from typing import Dict, List, Any, Optional
from loguru import logger
from .base_calculator import BaseCalculator
from .volume_data_provider import VolumeDataProvider
from .volume_analyzer import VolumeAnalyzer
from .volume_classifier import VolumeClassifier


class VolumeCalculator(BaseCalculator):
    """
    Volume Calculator - Clean, working implementation
    """
    
    def __init__(self, symbol: str = "BTC",
                 data_provider: Optional[VolumeDataProvider] = None,
                 analyzer: Optional[VolumeAnalyzer] = None,
                 classifier: Optional[VolumeClassifier] = None):
        """
        Initialize Volume Calculator
        
        Args:
            symbol: Trading symbol (default: "BTC")
            data_provider: VolumeDataProvider instance (injected dependency)
            analyzer: VolumeAnalyzer instance (injected dependency)
            classifier: VolumeClassifier instance (injected dependency)
        """
        # Initialize base class
        super().__init__(symbol)
        
        # Dependency injection with defaults
        self._data_provider = data_provider or VolumeDataProvider(symbol)
        self._analyzer = analyzer or VolumeAnalyzer()
        self._classifier = classifier or VolumeClassifier()
        
        logger.info(f"📊 Volume Calculator initialized for {symbol}")
    
    def get_latest_analysis(self, hyperliquid_websocket=None) -> Dict[str, Any]:
        """
        Get latest volume analysis with websocket access - NO FALLBACKS
        
        Args:
            hyperliquid_websocket: HyperliquidWebSocket instance (optional)
        
        Returns:
            Volume analysis dictionary
        
        Raises:
            ValueError: If websocket is not available or calculation fails
        """
        try:
            # Use provided websocket or get from system initializer
            if not hyperliquid_websocket:
                from core.services.system_initializer import get_system_initializer
                system_initializer = get_system_initializer()
                market_data_service = system_initializer.singleton_systems.get("market_data_service")
                
                if not market_data_service or not market_data_service.hyperliquid_websocket:
                    raise ValueError("Hyperliquid WebSocket not available for volume calculation - NO FALLBACKS")
                
                hyperliquid_websocket = market_data_service.hyperliquid_websocket
            
            # Use the websocket for volume calculation - NO FALLBACKS
            return self.calculate_hyperliquid_5m_volume(hyperliquid_websocket)
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest volume analysis: {e}")
            raise
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result with volume-specific structure"""
        base_result = super()._create_error_result(error_message)
        return {
            **base_result,
            "current_5m_volume": 0.0,
            "volume_category": "ERROR",
            "volume_momentum": {"momentum": 0.0, "trend": "UNKNOWN"},
            "volume_trend_strength": 0.0,
            "relative_volume": 0.0,
            "volume_anomaly": {"is_anomaly": False, "severity": "NORMAL"},
            "volume_implications": {"implications": [], "trading_suitable": False, "risk_level": "UNKNOWN"},
            "volume_recommendations": ["Volume analysis failed - use caution"],
            "data_source": "error"
        }
    
    def calculate_hyperliquid_5m_volume(self, hyperliquid_websocket) -> Dict[str, Any]:
        """
        Calculate enhanced 5m volume using the refactored modular system
        
        Args:
            hyperliquid_websocket: HyperliquidWebSocket instance
        
        Returns:
            Dictionary with enhanced 5m volume analysis
        """
        try:
            if not hyperliquid_websocket:
                raise ValueError("Hyperliquid WebSocket not available")
            
            # 1. Fetch volume data via data provider - NO FALLBACKS
            volume_data = self._data_provider.fetch_hyperliquid_volume_data(hyperliquid_websocket)
            raw_trades = volume_data.get("raw_trades", [])
            
            if not raw_trades:
                raise ValueError("No raw trades available for volume calculation - NO FALLBACKS")
            
            # 2. Calculate 5m volume via data provider
            current_time = time.time()
            volume_calc = self._data_provider.calculate_5m_volume(raw_trades, current_time)
            current_5m_volume = volume_calc.get("current_5m_volume", 0.0)
            
            # 3. Get volume history for analysis (REQUIRED - no fallbacks)
            volume_history = self._data_provider.get_volume_history(10)
            
            # 4. Calculate volume momentum via analyzer
            momentum = self._analyzer.calculate_volume_momentum(volume_history)
            
            # 5. Calculate volume trend strength via analyzer
            trend_strength = self._analyzer.calculate_volume_trend_strength(volume_history)
            
            # 6. Calculate relative volume via analyzer (for reference, not used in categorization)
            relative_volume = self._analyzer.calculate_relative_volume(current_5m_volume, volume_history)
            
            # 7. Detect volume anomalies via analyzer
            anomaly = self._analyzer.detect_volume_anomalies(current_5m_volume, volume_history)
            
            # 8. Categorize volume via classifier (percentile-based method - solid implementation, no fallbacks)
            categorization = self._classifier.categorize_volume(current_5m_volume, relative_volume, volume_history)
            
            # 9. Determine implications via classifier
            implications = self._classifier.determine_volume_implications(
                categorization.get("level", "UNKNOWN"),
                momentum,
                anomaly
            )
            
            # 10. Get recommendations via classifier
            recommendations = self._classifier.get_volume_recommendations(
                categorization.get("level", "UNKNOWN"),
                momentum,
                anomaly
            )
            
            # 11. Format results
            volume_level = categorization.get("level", "UNKNOWN")
            result = {
                "current_5m_volume": current_5m_volume,
                "volume_category": volume_level,
                "category": volume_level,  # Alias for momentum_detector compatibility (NO FALLBACKS)
                "volume_5m": current_5m_volume,  # Alias for compatibility (NO FALLBACKS)
                "percentile": categorization.get("percentile", 50.0),  # Add percentile for momentum_detector (NO FALLBACKS)
                "volume_momentum": momentum,
                "volume_trend_strength": trend_strength,
                "relative_volume": relative_volume,
                "volume_anomaly": anomaly,
                "volume_implications": implications,
                "volume_recommendations": recommendations,
                "data_source": "hyperliquid_5m",
                "timestamp": current_time,
                "analysis_details": {
                    "trade_count": volume_calc.get("trade_count", 0),
                    "reset_time": volume_calc.get("reset_time", 0),
                    "time_window": volume_calc.get("time_window", "5m"),
                    "historical_volumes": volume_history
                }
            }
            
            logger.info(f"📊 Volume analysis complete: {categorization.get('level', 'UNKNOWN')} ({current_5m_volume:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Hyperliquid 5m volume calculation failed: {e}")
            raise  # NO FALLBACKS - calculation failure should raise, not return error dict
    
    
    def invalidate_cache(self):
        """Clear all cached volume data to force fresh calculation"""
        try:
            self._cache.invalidate_pattern("volume_*")
            self._data_provider.invalidate_cache()
            logger.info("📊 Volume cache invalidated - next calculation will be fresh")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate volume cache: {e}")


# Factory function for backward compatibility
def create_volume_calculator(symbol: str = "BTC") -> VolumeCalculator:
    """
    Factory function to create VolumeCalculator with dependency injection
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Configured VolumeCalculator instance
    """
    return VolumeCalculator(symbol=symbol)
