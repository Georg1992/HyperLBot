#!/usr/bin/env python3
"""
Enhanced Pressure Calculator - Refactored Version
Modular architecture with dependency injection and optimized performance
"""

import time
from collections import deque
from typing import Dict, List, Any, Optional
from loguru import logger

# Import modular components
from .pressure_data_provider import PressureDataProvider
from .pressure_analyzer import PressureAnalyzer
from .pressure_classifier import PressureClassifier


class PressureCalculator:
    """
    Professional-grade Pressure Calculator with EMA smoothing and deeper depth analysis.
    
    Based on professional HFT implementations:
    - EMA smoothing (3-5 period) to reduce noise from transient orders
    - Deeper orderbook levels (10-15) for more reliable signals
    - Statistical normalization for better signal quality
    
    Refactored to use dependency injection for better testability and maintainability.
    Delegates responsibilities to specialized components.
    """
    
    def __init__(self, symbol: str = "BTC",
                 data_provider: Optional[PressureDataProvider] = None,
                 analyzer: Optional[PressureAnalyzer] = None,
                 classifier: Optional[PressureClassifier] = None):
        """
        Initialize the professional-grade Pressure Calculator
        
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
        
        # Professional-grade: EMA smoothing for noise reduction
        # Store pressure history for EMA calculation (5 periods for 3-5 period EMA)
        from config.config import TradingConfig
        self._pressure_history = deque(maxlen=5)  # Store last 5 pressure imbalances
        self._ema_alpha = TradingConfig.PRESSURE_EMA_ALPHA  # EMA smoothing factor from config
        self._ema_pressure = None  # Current EMA value
        
        logger.info(f"📊 Professional Pressure Calculator initialized for {symbol} - EMA smoothing + deeper depth")
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        """
        Get latest pressure analysis using the refactored modular system - NO FALLBACKS
        
        Returns:
            Pressure analysis dictionary
        
        Raises:
            ValueError: If orderbook data is not available or invalid
        """
        try:
            # Get orderbook data from HyperliquidAPI - NO FALLBACKS
            from core.api.hyperliquid_api import get_hyperliquid_api
            api = get_hyperliquid_api()
            
            if not api:
                raise ValueError("HyperliquidAPI not available for pressure calculation - NO FALLBACKS")
            
            # Get orderbook data - NO FALLBACKS
            orderbook_data = api.get_orderbook(self.symbol)
            
            if not orderbook_data or 'levels' not in orderbook_data:
                raise ValueError("No orderbook data available for pressure calculation - NO FALLBACKS")
            
            # Extract bids and asks from orderbook
            # Hyperliquid orderbook format: levels is a list of [bids, asks]
            levels = orderbook_data['levels'] if 'levels' in orderbook_data else []
            if len(levels) < 2:
                raise ValueError("Invalid orderbook structure - expected [bids, asks] - NO FALLBACKS")
            
            bids = levels[0]  # First element is bids
            asks = levels[1]  # Second element is asks
            
            if not bids or not asks:
                raise ValueError("Insufficient orderbook data for pressure calculation - NO FALLBACKS")
            
            # Calculate pressure using the modular system - NO FALLBACKS
            return self.calculate_orderbook_pressure(bids, asks)
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest pressure analysis: {e}")
            raise
    
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
                raise ValueError("No orderbook data available for pressure calculation - NO FALLBACKS")
            
            # 1. Calculate depth metrics via data provider - PROFESSIONAL: Use deeper levels (10-15)
            depth_metrics = self._data_provider.calculate_depth_metrics(bids, asks)
            
            # Use deeper depth (10 levels) for more reliable signals (professional practice) - NO FALLBACKS
            if ("total_depth_10" not in depth_metrics or depth_metrics["total_depth_10"] == 0.0):
                raise ValueError("No orderbook depth_10 available for pressure calculation - NO FALLBACKS (required for professional-grade analysis)")
            
            # 2. Calculate pressure ratios via data provider (using deeper depth)
            pressure_ratios = self._data_provider.calculate_pressure_ratios(depth_metrics)
            
            # 3. PROFESSIONAL: Apply EMA smoothing to reduce noise
            raw_pressure_imbalance = pressure_ratios["pressure_imbalance"] if "pressure_imbalance" in pressure_ratios else 0.0
            
            # Add to history
            self._pressure_history.append(raw_pressure_imbalance)
            
            # Calculate EMA (Exponential Moving Average)
            if self._ema_pressure is None:
                # Initialize EMA with first value (simple average if multiple values)
                if len(self._pressure_history) > 1:
                    self._ema_pressure = sum(self._pressure_history) / len(self._pressure_history)
                else:
                    self._ema_pressure = raw_pressure_imbalance
            else:
                # EMA formula: EMA = α × current_value + (1 - α) × previous_EMA
                self._ema_pressure = (self._ema_alpha * raw_pressure_imbalance) + ((1 - self._ema_alpha) * self._ema_pressure)
            
            # Use smoothed pressure for analysis (professional practice)
            pressure_imbalance = self._ema_pressure
            depth_concentration = pressure_ratios["depth_concentration"] if "depth_concentration" in pressure_ratios else 1.0
            
            # 4. Analyze pressure direction and strength via analyzer (using smoothed value)
            direction, strength = self._analyzer.categorize_pressure_direction(
                pressure_imbalance,
                depth_concentration
            )
            
            # 5. Calculate confidence via analyzer (using deeper depth for better reliability)
            confidence = self._analyzer.calculate_pressure_confidence(
                depth_metrics["total_depth_10"],
                pressure_imbalance  # Use smoothed pressure
            )
            
            # 6. Determine trend via analyzer (using smoothed pressure)
            trend = self._analyzer.determine_pressure_trend(
                pressure_imbalance,  # Use smoothed pressure
                depth_concentration
            )
            
            # 7. Classify pressure level via classifier
            classification = self._classifier.classify_pressure_level(direction, strength, confidence)
            
            # 8. Determine trading implications via classifier
            implications = self._classifier.determine_trading_implications(classification, trend)
            
            # 9. Get recommendations via classifier
            recommendations = self._classifier.get_pressure_recommendations(classification, implications)
            
            # 10. Format results (use smoothed pressure for net_pressure)
            # Calculate pressure_ratio for strategy_manager (bid_pressure_ratio / ask_pressure_ratio)
            # Recalculate ratios using smoothed pressure for consistency
            total_depth = depth_metrics["total_depth_10"]
            bid_depth = depth_metrics["bid_depth_10"]
            ask_depth = depth_metrics["ask_depth_10"]
            
            if total_depth > 0:
                bid_pressure_ratio = bid_depth / total_depth
                ask_pressure_ratio = ask_depth / total_depth
                pressure_ratio = bid_pressure_ratio / ask_pressure_ratio if ask_pressure_ratio > 0 else 1.0
            else:
                pressure_ratio = 1.0
            
            result = {
                "direction": direction,
                "confidence": confidence,
                "strength": strength,
                "trend": trend,
                "net_pressure": pressure_imbalance,  # Use smoothed EMA pressure (professional practice)
                "pressure_ratio": pressure_ratio,  # Used by strategy_manager
                "raw_pressure": raw_pressure_imbalance,  # Keep raw for debugging/comparison
                "ema_pressure": self._ema_pressure,  # EMA value for transparency
                "data_source": "live_orderbook_calculation_ema_smoothed",
                "timestamp": time.time()
            }
            
            logger.debug(f"📊 Pressure (EMA smoothed): {direction} (raw: {raw_pressure_imbalance:.3f}, EMA: {self._ema_pressure:.3f}, strength: {strength:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Orderbook pressure calculation failed: {e}")
            raise  # NO FALLBACKS - calculation failure should raise, not return error dict
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create a consistent error result dictionary"""
        return {
            "direction": "ERROR",
            "confidence": 0.0,
            "strength": 0.0,
            "trend": "UNKNOWN",
            "pressure_ratio": 1.0,
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
