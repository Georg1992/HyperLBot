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
                 classifier: Optional[PressureClassifier] = None,
                 cache=None,
                 strategy: str = "standard"):
        """
        Initialize the professional-grade Pressure Calculator with adaptive EMA
        
        Args:
            symbol: Trading symbol (default: "BTC")
            data_provider: PressureDataProvider instance (injected dependency)
            analyzer: PressureAnalyzer instance (injected dependency)
            classifier: PressureClassifier instance (injected dependency)
            cache: CentralizedCache instance (optional, falls back to global singleton)
            strategy: Current trading strategy (for adaptive EMA)
        """
        # Dependency injection with defaults
        self.symbol = symbol
        self._data_provider = data_provider or PressureDataProvider(symbol)
        self._analyzer = analyzer or PressureAnalyzer()
        self._classifier = classifier or PressureClassifier()
        self._strategy = strategy
        
        # Dependency injection for cache (DIP compliance)
        # Fallback to global singleton for backward compatibility
        if cache is None:
            from core.services.centralized_cache import get_global_centralized_cache
            self._cache = get_global_centralized_cache()
        else:
            self._cache = cache
        
        # IMPROVEMENT 1: Adaptive EMA smoothing per strategy
        # Faster EMA for scalping/high-volatility (needs real-time signals)
        # Slower EMA for trend-following/low-volatility (needs stability)
        from config.config import TradingConfig
        self._pressure_history = deque(maxlen=5)  # Store last 5 pressure imbalances
        strategy_alpha = TradingConfig.PRESSURE_EMA_ALPHA_BY_STRATEGY.get(
            strategy, 
            TradingConfig.PRESSURE_EMA_ALPHA
        )
        self._ema_alpha = strategy_alpha  # Strategy-specific EMA alpha
        self._ema_pressure = None  # Current EMA value
        
        logger.info(f"📊 Professional Pressure Calculator initialized for {symbol} (strategy: {strategy}) - Adaptive EMA α={self._ema_alpha:.2f}")
    
    def update_strategy(self, strategy: str) -> None:
        """
        Update strategy for adaptive EMA smoothing (called when strategy changes)
        
        Args:
            strategy: New trading strategy
        """
        from config.config import TradingConfig
        old_strategy = self._strategy
        self._strategy = strategy
        
        # Update EMA alpha for new strategy
        strategy_alpha = TradingConfig.PRESSURE_EMA_ALPHA_BY_STRATEGY.get(
            strategy, 
            TradingConfig.PRESSURE_EMA_ALPHA
        )
        
        if strategy_alpha != self._ema_alpha:
            self._ema_alpha = strategy_alpha
            logger.debug(f"📊 Pressure EMA updated: {old_strategy} (α={self._ema_alpha:.2f}) → {strategy} (α={strategy_alpha:.2f})")
    
    def get_latest_analysis(self, unified_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get latest pressure analysis using the refactored modular system - NO FALLBACKS
        
        Args:
            unified_data: Optional unified market data for dynamic thresholds (volatility, depth)
        
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
            
            # Get unified_data from cache if not provided (for dynamic thresholds)
            if unified_data is None:
                try:
                    if self._cache:
                        unified_data = self._cache.get("unified_analysis_data")
                except:
                    pass  # Unified data not available - use static thresholds
            
            # Calculate pressure using the modular system - NO FALLBACKS
            return self.calculate_orderbook_pressure(bids, asks, unified_data=unified_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest pressure analysis: {e}")
            raise
    
    def calculate_orderbook_pressure(self, bids: List[Dict], asks: List[Dict], 
                                     unified_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate market pressure using the refactored modular system with improvements
        
        Args:
            bids: List of bid levels
            asks: List of ask levels
            unified_data: Optional unified market data for dynamic thresholds (volatility, depth)
        
        Returns:
            Dictionary with pressure analysis
        """
        try:
            if not bids or not asks:
                raise ValueError("No orderbook data available for pressure calculation - NO FALLBACKS")
            
            from config.config import TradingConfig
            
            # 1. Calculate depth metrics via data provider - PROFESSIONAL: Use deeper levels (10-15)
            depth_metrics = self._data_provider.calculate_depth_metrics(bids, asks)
            
            # IMPROVEMENT 2: Minimum depth filter - ignore thin orderbooks (prevents noise)
            total_depth_10 = depth_metrics.get("total_depth_10", 0.0)
            if TradingConfig.PRESSURE_MIN_DEPTH_ENABLED:
                min_depth = TradingConfig.PRESSURE_MIN_DEPTH_THRESHOLD
                if total_depth_10 < min_depth:
                    logger.debug(f"⏭️ Pressure calculation skipped: thin orderbook (depth: {total_depth_10:.2f} BTC < {min_depth:.2f} BTC)")
                    # Return neutral pressure for thin orderbooks
                    return {
                        "direction": "NEUTRAL",
                        "confidence": 0.0,
                        "strength": 0.5,
                        "trend": "NEUTRAL",
                        "net_pressure": 0.0,
                        "pressure_ratio": 1.0,
                        "raw_pressure": 0.0,
                        "ema_pressure": self._ema_pressure if self._ema_pressure is not None else 0.0,
                        "data_source": "thin_orderbook_skipped",
                        "timestamp": time.time(),
                        "depth_filtered": True
                    }
            
            # Use deeper depth (10 levels) for more reliable signals (professional practice) - NO FALLBACKS
            if total_depth_10 == 0.0:
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
            
            # IMPROVEMENT 3: Dynamic thresholds based on volatility and depth
            # Adjust thresholds based on market conditions for better signal quality
            strong_threshold = TradingConfig.PRESSURE_BASE_STRONG_THRESHOLD
            moderate_threshold = TradingConfig.PRESSURE_BASE_MODERATE_THRESHOLD
            
            if TradingConfig.PRESSURE_DYNAMIC_THRESHOLDS_ENABLED and unified_data:
                # IMPROVEMENT 3: Dynamic thresholds based on volatility and depth
                # Higher volatility = wider thresholds (more noise, need stronger signals)
                # Higher depth = tighter thresholds (more reliable, can use tighter filters)
                
                # Extract volatility_5m (absolute value in USD, not percentage)
                volatility_5m = 0.0
                if "support_resistance" in unified_data:
                    sr_metadata = unified_data["support_resistance"].get("metadata", {})
                    volatility_5m = sr_metadata.get("volatility_5m", 0.0)
                
                # Get current price for volatility percentage calculation
                current_price = unified_data.get("current_price", 0.0)
                volatility_pct = (volatility_5m / current_price) if current_price > 0 else 0.0
                
                # Adjust based on volatility percentage (higher vol % = wider thresholds)
                # Example: 0.5% volatility → 0.5 * 0.1 = 0.05 adjustment (5% wider)
                vol_adjustment = volatility_pct * TradingConfig.PRESSURE_VOLATILITY_ADJUSTMENT_FACTOR
                
                # Adjust based on depth (higher depth = tighter thresholds, more reliable)
                # Example: 50 BTC depth → (50/100) * 0.05 = 0.025 adjustment (2.5% tighter)
                depth_adjustment = (total_depth_10 / 100.0) * TradingConfig.PRESSURE_DEPTH_ADJUSTMENT_FACTOR
                
                # Net adjustment: volatility widens thresholds, depth tightens them
                net_adjustment = vol_adjustment - depth_adjustment
                
                # Apply adjustments with bounds protection
                strong_threshold = max(
                    TradingConfig.PRESSURE_THRESHOLD_MIN,
                    min(TradingConfig.PRESSURE_THRESHOLD_MAX, strong_threshold + net_adjustment)
                )
                moderate_threshold = max(
                    TradingConfig.PRESSURE_THRESHOLD_MIN * 0.5,
                    min(TradingConfig.PRESSURE_THRESHOLD_MAX * 0.5, moderate_threshold + net_adjustment * 0.5)
                )
                
                logger.debug(
                    f"📊 Dynamic thresholds: vol={volatility_pct:.4f}%, depth={total_depth_10:.2f} BTC, "
                    f"adjustment={net_adjustment:.4f}, strong={strong_threshold:.3f}, moderate={moderate_threshold:.3f}"
                )
            
            # 4. Analyze pressure direction and strength via analyzer (using smoothed value and dynamic thresholds)
            direction, strength = self._analyzer.categorize_pressure_direction(
                pressure_imbalance,
                depth_concentration,
                strong_threshold=strong_threshold,
                moderate_threshold=moderate_threshold
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
                "ema_alpha": self._ema_alpha,  # EMA alpha used (for transparency)
                "total_depth_10": total_depth_10,  # Depth for validation
                "data_source": "live_orderbook_calculation_adaptive_ema",
                "timestamp": time.time()
            }
            
            logger.debug(
                f"📊 Pressure (adaptive EMA α={self._ema_alpha:.2f}): {direction} "
                f"(raw: {raw_pressure_imbalance:.3f}, EMA: {self._ema_pressure:.3f}, strength: {strength:.3f}, depth: {total_depth_10:.2f} BTC)"
            )
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
def create_pressure_calculator(symbol: str = "BTC", strategy: str = "standard") -> PressureCalculator:
    """
    Factory function to create PressureCalculator with dependency injection and adaptive EMA
    
    Args:
        symbol: Trading symbol
        strategy: Initial trading strategy (for adaptive EMA)
    
    Returns:
        Configured PressureCalculator instance
    """
    return PressureCalculator(symbol=symbol, strategy=strategy)
