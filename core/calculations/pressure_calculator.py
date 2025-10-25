#!/usr/bin/env python3
"""
Enhanced Pressure Calculator - Refactored Version
Modular architecture with dependency injection and optimized performance
"""

import time
from typing import Dict, List, Any, Optional
from loguru import logger

# Import modular components
from .pressure_data_provider import PressureDataProvider
from .pressure_analyzer import PressureAnalyzer
from .pressure_classifier import PressureClassifier


class PressureCalculator:
    """
    Enhanced Pressure Calculator with modular architecture.
    
    Refactored to use dependency injection for better testability and maintainability.
    Delegates responsibilities to specialized components.
    """
    
    def __init__(self, symbol: str = "BTC",
                 data_provider: Optional[PressureDataProvider] = None,
                 analyzer: Optional[PressureAnalyzer] = None,
                 classifier: Optional[PressureClassifier] = None):
        """
        Initialize the refactored Pressure Calculator
        
        Args:
            symbol: Trading symbol (default: "BTC")
            data_provider: PressureDataProvider instance (injected dependency)
            analyzer: PressureAnalyzer instance (injected dependency)
            classifier: PressureClassifier instance (injected dependency)
        """
        # Dependency injection with defaults
        self.symbol = symbol
        self._data_provider = data_provider or PressureDataProvider(symbol)
        self._analyzer = analyzer or PressureAnalyzer()
        self._classifier = classifier or PressureClassifier()
        
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
        logger.info(f"📊 Refactored Pressure Calculator initialized for {symbol} - Modular architecture")
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        """
        Get latest pressure analysis using the refactored modular system
        
        Returns:
            Pressure analysis dictionary
        """
        try:
            # Get orderbook data from HyperliquidAPI
            from core.api.hyperliquid_api import get_hyperliquid_api
            api = get_hyperliquid_api()
            
            if not api:
                logger.warning("⚠️ HyperliquidAPI not available for pressure calculation")
                return self._create_error_result("HyperliquidAPI not available")
            
            # Get orderbook data
            orderbook_data = api.get_orderbook(self.symbol)
            
            if not orderbook_data or 'levels' not in orderbook_data:
                logger.warning("⚠️ No orderbook data available for pressure calculation")
                return self._create_error_result("No orderbook data available")
            
            # Extract bids and asks from orderbook
            # Hyperliquid orderbook format: levels is a list of [bids, asks]
            levels = orderbook_data.get('levels', [])
            if len(levels) >= 2:
                bids = levels[0]  # First element is bids
                asks = levels[1]  # Second element is asks
            else:
                logger.warning("⚠️ Invalid orderbook structure - expected [bids, asks]")
                return self._create_error_result("Invalid orderbook structure")
            
            if not bids or not asks:
                logger.warning("⚠️ Insufficient orderbook data for pressure calculation")
                return self._create_error_result("Insufficient orderbook data")
            
            # Calculate pressure using the modular system
            return self.calculate_orderbook_pressure(bids, asks)
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest pressure analysis: {e}")
            return self._create_error_result(str(e))
    
    def calculate_orderbook_pressure(self, bids: List[Dict], asks: List[Dict]) -> Dict[str, Any]:
        """
        Calculate market pressure using the refactored modular system
        
        Args:
            bids: List of bid levels
            asks: List of ask levels
        
        Returns:
            Dictionary with pressure analysis
        """
        try:
            if not bids or not asks:
                logger.error("❌ No orderbook data available for pressure calculation")
                return self._create_error_result("No orderbook data available")
            
            # 1. Calculate depth metrics via data provider
            depth_metrics = self._data_provider.calculate_depth_metrics(bids, asks)
            
            if depth_metrics.get("total_depth_5", 0.0) == 0:
                logger.error("❌ No orderbook depth available for pressure calculation")
                return self._create_error_result("No orderbook depth available")
            
            # 2. Calculate pressure ratios via data provider
            pressure_ratios = self._data_provider.calculate_pressure_ratios(depth_metrics)
            
            # 3. Analyze pressure direction and strength via analyzer
            direction, strength = self._analyzer.categorize_pressure_direction(
                pressure_ratios.get("pressure_imbalance", 0.0),
                pressure_ratios.get("depth_concentration", 1.0)
            )
            
            # 4. Calculate confidence via analyzer
            confidence = self._analyzer.calculate_pressure_confidence(
                depth_metrics.get("total_depth_5", 0.0),
                pressure_ratios.get("pressure_imbalance", 0.0)
            )
            
            # 5. Determine trend via analyzer
            trend = self._analyzer.determine_pressure_trend(
                pressure_ratios.get("pressure_imbalance", 0.0),
                pressure_ratios.get("depth_concentration", 1.0)
            )
            
            # 6. Classify pressure level via classifier
            classification = self._classifier.classify_pressure_level(direction, strength, confidence)
            
            # 7. Determine trading implications via classifier
            implications = self._classifier.determine_trading_implications(classification, trend)
            
            # 8. Get recommendations via classifier
            recommendations = self._classifier.get_pressure_recommendations(classification, implications)
            
            # 9. Format results
            result = {
                "direction": direction,
                "confidence": confidence,
                "strength": strength,
                "trend": trend,
                "pressure_classification": classification,
                "trading_implications": implications,
                "recommendations": recommendations,
                "analysis_details": {
                    "bid_pressure_ratio": pressure_ratios.get("bid_pressure_ratio", 0.5),
                    "ask_pressure_ratio": pressure_ratios.get("ask_pressure_ratio", 0.5),
                    "pressure_imbalance": pressure_ratios.get("pressure_imbalance", 0.0),
                    "depth_concentration": pressure_ratios.get("depth_concentration", 1.0),
                    "bid_depth_5": depth_metrics.get("bid_depth_5", 0.0),
                    "ask_depth_5": depth_metrics.get("ask_depth_5", 0.0),
                    "total_depth_5": depth_metrics.get("total_depth_5", 0.0)
                },
                "data_source": "live_orderbook_calculation",
                "timestamp": time.time()
            }
            
            logger.info(f"📊 Pressure analysis complete: {direction} (strength: {strength:.3f}, confidence: {confidence:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Orderbook pressure calculation failed: {e}")
            return self._create_error_result(str(e))
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create a consistent error result dictionary"""
        return {
            "direction": "ERROR",
            "confidence": 0.0,
            "strength": 0.0,
            "trend": "UNKNOWN",
            "pressure_classification": {"level": "ERROR", "description": "Analysis failed"},
            "trading_implications": {"implications": ["Analysis failed"], "risk_level": "UNKNOWN"},
            "recommendations": {"recommendations": ["Use caution"], "recommendation_count": 1},
            "analysis_details": {},
            "data_source": "error",
            "timestamp": time.time(),
            "error": error_message
        }
    
    def invalidate_cache(self):
        """Clear all cached pressure data to force fresh calculation"""
        try:
            self._cache.invalidate_pattern("pressure_*")
            self._data_provider.invalidate_cache()
            logger.info("📊 Pressure cache invalidated - next calculation will be fresh")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate pressure cache: {e}")


# Factory function for backward compatibility
def create_pressure_calculator(symbol: str = "BTC") -> PressureCalculator:
    """
    Factory function to create PressureCalculator with dependency injection
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Configured PressureCalculator instance
    """
    return PressureCalculator(symbol=symbol)
