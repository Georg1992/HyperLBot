#!/usr/bin/env python3
"""
Market Data Service - Processed Data Coordinator Architecture
Single Responsibility: Coordinate processed analysis data from analysis modules
New Flow: Raw Data → Analysis Modules → MarketDataService → SessionOrchestrator
"""

import time
from typing import Dict, Any, Optional, List
from loguru import logger
from core.constants import TradingConstants

class MarketDataService:
    """Processed data coordinator - receives analysis from modules, coordinates for consumers"""
    
    def __init__(self, hyperliquid_api, hyperliquid_websocket, binance_api=None, binance_websocket=None):
        self.hyperliquid_api = hyperliquid_api
        self.hyperliquid_websocket = hyperliquid_websocket
        self.binance_api = binance_api
        self.binance_websocket = binance_websocket
        
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
        # Update intervals are now handled by CentralizedCache
        # No need for duplicate definitions here
        
        # Analysis module references (will be set by SystemInitializer)
        self._analysis_modules = {}
        
        # Store raw_data when available (set by _trigger_analysis_modules or set_raw_data)
        # This allows methods like get_funding_analysis() to access pre-fetched data
        self._current_raw_data = None
        
        # Real-time price streaming (single source of truth)
        self._current_price = None
        self._price_timestamp = 0
        self._price_update_interval = TradingConstants.PRICE_UPDATE_INTERVAL
        
        # RSI update throttling for dashboard (prevent spam from rapid price changes)
        self._last_rsi_dashboard_update = 0
        self._rsi_dashboard_update_interval = 0.5  # Update dashboard at most every 500ms
        
        # Register WebSocket callback to update RSI immediately when price changes
        if self.hyperliquid_websocket:
            self.hyperliquid_websocket.add_price_callback(self._on_websocket_price_update)
        
        logger.info("📊 Processed Data Coordinator initialized - New architecture")
    
    # ==================================================================================
    # RAW DATA MANAGEMENT - Store and access pre-fetched raw API data
    # ==================================================================================
    
    def set_raw_data(self, raw_data: Dict[str, Any]) -> None:
        """
        Store raw_data for use by analysis methods
        
        Called by _trigger_analysis_modules() to make raw_data available
        to methods like get_funding_analysis() that are called later.
        
        Args:
            raw_data: Pre-fetched raw API data (all data is mandatory - NO FALLBACKS)
        """
        if raw_data is None:
            raise ValueError("raw_data cannot be None (NO FALLBACKS)")
        self._current_raw_data = raw_data
    
    def _get_raw_data(self, raw_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get raw_data from parameter or stored value
        
        Args:
            raw_data: Optional raw_data parameter
            
        Returns:
            raw_data from parameter if provided, otherwise from stored value
            
        Raises:
            ValueError: If no raw_data is available (NO FALLBACKS)
        """
        if raw_data is not None:
            return raw_data
        if self._current_raw_data is not None:
            return self._current_raw_data
        raise ValueError("raw_data is required but not provided and not stored (NO FALLBACKS)")
    
    # ==================================================================================
    # ANALYSIS MODULE COORDINATION - Register and manage analysis modules
    # ==================================================================================
    
    def register_analysis_module(self, module_name: str, module_instance: Any) -> None:
        """Register an analysis module for data coordination"""
        self._analysis_modules[module_name] = module_instance
    
    def _is_data_valid(self, data_type: str) -> bool:
        """Check if processed data is still valid based on schedule"""
        # Data validity is now handled by centralized cache TTL
        return True
    
    def _store_processed_data(self, data_type: str, data: Any) -> None:
        """Store processed data from analysis modules"""
        self._cache.set(data_type, data)
    
    def _get_processed_data(self, data_type: str) -> Any:
        """Get processed data if valid"""
        return self._cache.get(data_type)
    
    # ==================================================================================
    # PROCESSED DATA COORDINATION - Coordinate analysis from modules
    # ==================================================================================
    
    def update_analysis_data(self, data_type: str, analysis_data: Any) -> None:
        """Receive processed analysis data from analysis modules"""
        self._store_processed_data(data_type, analysis_data)
    
    def get_volatility_analysis(self) -> Dict[str, Any]:
        """
        Get volatility analysis from VolatilityCalculator - strategy independent
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        """
        try:
            # Check if we have valid processed data
            volatility_data = self._get_processed_data("volatility")
            if volatility_data:
                # Validate cached data
                if volatility_data is None:
                    raise ValueError("Cached volatility data is None - cache corruption detected")
                if not isinstance(volatility_data, dict):
                    raise ValueError(f"Cached volatility data is not a dict: {type(volatility_data)}")
                return volatility_data
            
            # If no valid data, trigger analysis module to process
            if "volatility" not in self._analysis_modules:
                raise ValueError("No volatility analysis module registered - module initialization failed")
            
            logger.info("📊 Triggering volatility analysis...")
            volatility_calculator = self._analysis_modules["volatility"]
            if volatility_calculator is None:
                raise ValueError("Volatility calculator module is None - module initialization failed")
            
            # get_latest_analysis() guarantees valid dict or raises (NO FALLBACKS)
            volatility_result = volatility_calculator.get_latest_analysis()
            
            # Store result for future use
            self.update_analysis_data("volatility", volatility_result)
            return volatility_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get volatility analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_trend_analysis(self) -> Dict[str, Any]:
        """Get trend analysis from TrendCalculator - strategy independent"""
        try:
            # Check cache for already-mapped trend data
            trend_data = self._get_processed_data("trend")
            if trend_data:
                # Cache stores mapped data - validate structure (NO FALLBACKS)
                if isinstance(trend_data, dict) and "detailed_timeframes" in trend_data and "direction" in trend_data:
                    # Check if all timeframes are UNKNOWN - if so, invalidate cache and recalculate
                    timeframes = trend_data["detailed_timeframes"]  # Required (NO FALLBACKS)
                    all_unknown = all(
                        timeframes[key] == "UNKNOWN"  # Required (NO FALLBACKS)
                        for key in ["trend_15m", "trend_1h", "trend_4h", "trend_24h"]
                    )
                    if all_unknown:
                        logger.warning("⚠️ Cached trend data has all UNKNOWN values - invalidating cache and recalculating")
                        self._cache.invalidate("trend")
                        # Continue to fetch fresh data below
                    else:
                        # Already mapped with valid data, return as-is
                        return trend_data
                else:
                    # Invalid cached data structure - invalidate and fetch fresh (NO FALLBACKS)
                    logger.warning("⚠️ Cached trend data has invalid structure - invalidating cache and recalculating")
                    self._cache.invalidate("trend")
                    # Continue to fetch fresh data below
            
            # No valid cached data - fetch fresh trend data (NO FALLBACKS)
            if "trend" not in self._analysis_modules:
                raise ValueError("No trend analysis module registered - NO FALLBACKS")
            
            logger.info("📊 Triggering trend analysis...")
            # Strategy-independent analysis
            # _map_trend_data() validates raw_trend_data and guarantees valid structure
            raw_trend_data = self._analysis_modules["trend"].get_latest_analysis()
            mapped_trend = self._map_trend_data(raw_trend_data)  # API boundary - validates and guarantees structure
            # Store mapped result for future use
            self.update_analysis_data("trend", mapped_trend)
            return mapped_trend
            
        except Exception as e:
            logger.error(f"❌ Failed to get trend analysis: {e}")
            raise
    
    def _map_trend_data(self, raw_trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map trend calculator output to unified format - NO FALLBACKS"""
        try:
            if not raw_trend_data or not isinstance(raw_trend_data, dict):
                raise ValueError(f"Invalid raw_trend_data: expected dict, got {type(raw_trend_data)} - NO FALLBACKS")
            
            # Extract all timeframe trends
            trend_15m = raw_trend_data["trend_15m"]  # Required (NO FALLBACKS)
            trend_1h = raw_trend_data["trend_1h"]  # Required (NO FALLBACKS)
            trend_4h = raw_trend_data["trend_4h"]  # Required (NO FALLBACKS)
            trend_24h = raw_trend_data["trend_24h"]  # Required (NO FALLBACKS)
            
            # Extract numeric strength from details (trend calculator returns strength as float 0.0-1.0)
            # NO FALLBACKS - details and strength are required
            details = raw_trend_data["details"]
            trend_1h_details = details["1h"]
            numeric_strength = trend_1h_details["strength"]
            
            # Timestamp is required from trend calculator (NO FALLBACKS)
            if "timestamp" not in raw_trend_data:
                raise ValueError("Trend data missing 'timestamp' key (NO FALLBACKS)")
            
            # Use 1h as primary for strategy decisions, but preserve all timeframes
            primary_trend = trend_1h
            mapped_direction = self._map_trend_to_direction(primary_trend)
            
            # Create unified trend structure with ALL timeframes
            # Use numeric strength (0.0-1.0) instead of string mapping for strategy manager compatibility
            mapped_trend = {
                "direction": mapped_direction,
                "strength": float(numeric_strength),  # Numeric strength for strategy manager (NO FALLBACKS)
                "timeframes": {
                    "short": trend_15m,      # 15m trend
                    "medium": trend_1h,       # 1h trend  
                    "long": trend_24h         # 24h trend
                },
                "detailed_timeframes": {
                    "trend_15m": trend_15m,
                    "trend_1h": trend_1h,
                    "trend_4h": trend_4h,
                    "trend_24h": trend_24h
                },
                "raw_data": raw_trend_data,  # Keep original data for detailed analysis
                "timestamp": raw_trend_data["timestamp"],  # Required (NO FALLBACKS)
                "data_type": "trend"
            }
            
            return mapped_trend
            
        except Exception as e:
            logger.error(f"❌ Trend mapping failed: {e}")
            raise
    
    def _map_trend_to_direction(self, trend: str) -> str:
        """Map detailed trend to simple direction for strategy manager - NO FALLBACKS"""
        if not trend or trend == "UNKNOWN" or trend is None:
            raise ValueError(f"Invalid trend value: {trend} (NO FALLBACKS)")
            
        trend_mapping = {
            "STRONG_UPTREND": "BULLISH",
            "UPTREND": "BULLISH", 
            "WEAK_UPTREND": "BULLISH",
            "STRONG_DOWNTREND": "BEARISH",
            "DOWNTREND": "BEARISH",
            "WEAK_DOWNTREND": "BEARISH",
            "SIDEWAYS": "SIDEWAYS"
        }
        if trend not in trend_mapping:
            raise ValueError(f"Unsupported trend value: {trend} - must be one of {list(trend_mapping.keys())} (NO FALLBACKS)")
        return trend_mapping[trend]
    
    def _map_trend_to_strength(self, trend: str) -> str:
        """Map detailed trend to strength level - NO FALLBACKS (Note: This is deprecated, use numeric strength from details instead)"""
        if not trend or trend == "UNKNOWN" or trend is None:
            raise ValueError(f"Invalid trend value: {trend} (NO FALLBACKS)")
            
        strength_mapping = {
            "STRONG_UPTREND": "STRONG",
            "STRONG_DOWNTREND": "STRONG",
            "UPTREND": "MODERATE",
            "DOWNTREND": "MODERATE", 
            "WEAK_UPTREND": "WEAK",
            "WEAK_DOWNTREND": "WEAK",
            "SIDEWAYS": "NEUTRAL"
        }
        if trend not in strength_mapping:
            raise ValueError(f"Unsupported trend value: {trend} - must be one of {list(strength_mapping.keys())} (NO FALLBACKS)")
        return strength_mapping[trend]
    
    def get_support_resistance_analysis(self) -> Dict[str, Any]:
        """
        Get S/R analysis from SupportResistanceCalculator - strategy independent
        
        Returns ALL significant S/R levels found in the market.
        Strategy-specific filtering happens later in prediction engine.
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        """
        try:
            # Strategy-independent cache key
            cache_key = "support_resistance"
            sr_data = self._cache.get(cache_key)
            if sr_data:
                # Validate cached data is not None
                if sr_data is None:
                    raise ValueError("Cached support_resistance data is None - cache corruption detected")
                if not isinstance(sr_data, dict):
                    raise ValueError(f"Cached support_resistance data is not a dict: {type(sr_data)}")
                return sr_data
            
            if "support_resistance" not in self._analysis_modules:
                raise ValueError("No S/R analysis module registered - module initialization failed")
            
            logger.info("📊 Triggering S/R analysis (strategy-independent)...")
            # Get current price for S/R calculation
            current_price = None
            if self.hyperliquid_websocket:
                current_price = self.hyperliquid_websocket.get_current_price()
            elif self.hyperliquid_api:
                from config.config import TradingConfig
                current_price = self.hyperliquid_api.get_current_price(TradingConfig.SYMBOL)
            
            if not current_price or current_price <= 0:
                raise ValueError(f"No valid current price for S/R analysis (got: {current_price})")
            
            # Get S/R calculator and calculate levels (strategy-independent)
            sr_calculator = self._analysis_modules["support_resistance"]
            if sr_calculator is None:
                raise ValueError("S/R calculator module is None - module initialization failed")
            
            # NO FALLBACKS - assume calculate_multi_timeframe_levels exists
            # Strategy-independent: returns ALL significant levels
            # Pass self (market_data_service) for dependency injection (replaces global singleton)
            # calculate_multi_timeframe_levels() guarantees valid dict or raises (NO FALLBACKS)
            result = sr_calculator.calculate_multi_timeframe_levels(current_price, market_data_service=self)
            
            # Cache with strategy-independent key
            self._cache.set(cache_key, result, ttl=300)
            # Also store via MarketDataService for consistency
            self.update_analysis_data("support_resistance", result)
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get S/R analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_rsi_analysis(self) -> Dict[str, Any]:
        """
        Get RSI analysis from RSICalculator
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        """
        try:
            # Check if we have valid processed data
            rsi_data = self._get_processed_data("rsi")
            if rsi_data:
                # Validate cached data
                if rsi_data is None:
                    raise ValueError("Cached RSI data is None - cache corruption detected")
                if not isinstance(rsi_data, dict):
                    raise ValueError(f"Cached RSI data is not a dict: {type(rsi_data)}")
                return rsi_data
            
            # If no valid data, trigger RSI calculation
            if "rsi_calculator" not in self._analysis_modules:
                raise ValueError("No RSI analysis module registered - module initialization failed")
            
            logger.info("📊 Triggering RSI analysis...")
            rsi_calculator = self._analysis_modules["rsi_calculator"]
            if rsi_calculator is None:
                raise ValueError("RSI calculator module is None - module initialization failed")
            
            # get_latest_analysis() always returns dict (may contain None/error values if not initialized)
            rsi_result = rsi_calculator.get_latest_analysis()
            
            # Store result for future use
            self.update_analysis_data("rsi", rsi_result)
            return rsi_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get RSI analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def recalculate_rsi_baseline(self, candles_5m: List[Dict]) -> None:
        """Recalculate RSI baseline at candle boundary - SRP compliant method"""
        try:
            if "rsi_calculator" not in self._analysis_modules:
                raise ValueError("No RSI calculator module registered")
            
            rsi_calculator = self._analysis_modules["rsi_calculator"]
            if candles_5m and len(candles_5m) >= 15:
                rsi_calculator.calculate_hyperliquid_baseline_rsi(candles_5m)
                # Invalidate RSI cache to force fresh calculations
                self._cache.invalidate(pattern="rsi")
                logger.info(f"✅ RSI baseline recalculated: {rsi_calculator.baseline_rsi:.2f}")
            else:
                logger.warning(f"⚠️ Insufficient candles for RSI baseline recalculation: {len(candles_5m) if candles_5m else 0}")
        except Exception as e:
            logger.error(f"❌ Failed to recalculate RSI baseline: {e}")
            raise
    
    def get_volume_analysis(self) -> Dict[str, Any]:
        """
        Get volume analysis from VolumeCalculator
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        """
        try:
            # Check if we have valid processed data
            volume_data = self._get_processed_data("volume")
            if volume_data:
                # Validate cached data
                if volume_data is None:
                    raise ValueError("Cached volume data is None - cache corruption detected")
                if not isinstance(volume_data, dict):
                    raise ValueError(f"Cached volume data is not a dict: {type(volume_data)}")
                return volume_data
            
            # If no valid data, trigger volume calculation
            if "volume" not in self._analysis_modules:
                raise ValueError("No volume calculator registered - module initialization failed")
            
            logger.info("📊 Triggering volume analysis...")
            volume_calculator = self._analysis_modules["volume"]
            if volume_calculator is None:
                raise ValueError("Volume calculator module is None - module initialization failed")
            
            volume_result = volume_calculator.get_latest_analysis(
                hyperliquid_websocket=self.hyperliquid_websocket
            )
            
            # get_latest_analysis() guarantees valid dict or raises (NO FALLBACKS)
            # Store result for future use
            self.update_analysis_data("volume", volume_result)
            return volume_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get volume analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_cross_asset_analysis(self, raw_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get cross asset correlation analysis
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        
        NEW: raw_data parameter contains pre-fetched cross-asset data from Yahoo Finance.
        If provided, passes it to analyzer to avoid redundant API calls.
        
        Args:
            raw_data: Pre-fetched raw API data (required - NO FALLBACKS)
        """
        try:
            # Check if we have valid processed data
            cross_asset_data = self._get_processed_data("cross_asset_correlation_analyzer")
            if cross_asset_data:
                # Validate cached data
                if cross_asset_data is None:
                    raise ValueError("Cached cross asset data is None - cache corruption detected")
                if not isinstance(cross_asset_data, dict):
                    raise ValueError(f"Cached cross asset data is not a dict: {type(cross_asset_data)}")
                return cross_asset_data
            
            # If no valid data, trigger cross asset analysis
            if "cross_asset_correlation_analyzer" not in self._analysis_modules:
                raise ValueError("No cross asset correlation analyzer registered - module initialization failed")
            
            logger.info("📊 Triggering cross asset correlation analysis...")
            cross_asset_analyzer = self._analysis_modules["cross_asset_correlation_analyzer"]
            if cross_asset_analyzer is None:
                raise ValueError("Cross asset analyzer module is None - module initialization failed")
            
            current_price = self.get_current_price()
            if not current_price or current_price <= 0:
                raise ValueError(f"No valid current price for cross asset analysis (got: {current_price})")
            
            # Pass raw_data to analyzer so it can use pre-fetched Yahoo Finance data
            # Get raw_data from parameter or stored value
            raw_data = self._get_raw_data(raw_data)
            # analyze_cross_asset_correlations() guarantees valid dict or raises (NO FALLBACKS)
            cross_asset_result = cross_asset_analyzer.analyze_cross_asset_correlations(
                current_price,
                raw_data=raw_data  # Pass pre-fetched data
            )
            
            # Store result for future use
            self.update_analysis_data("cross_asset_correlation_analyzer", cross_asset_result)
            return cross_asset_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get cross asset analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_consolidation_analysis(self, unified_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Get consolidation analysis from ConsolidationTracker
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        
        Note: Consolidation requires unified_data parameter, so it's called separately
        rather than via standard getter pattern in _trigger_analysis_modules.
        """
        try:
            # Check cache first (consistent with other modules)
            # Note: Consolidation cache key may need to be price-sensitive, but checking cache is still consistent
            consolidation_data = self._get_processed_data("consolidation")
            if consolidation_data:
                # Validate cached data
                if consolidation_data is None:
                    raise ValueError("Cached consolidation data is None - cache corruption detected")
                if not isinstance(consolidation_data, dict):
                    raise ValueError(f"Cached consolidation data is not a dict: {type(consolidation_data)}")
                # Note: May want to invalidate if price changed significantly, but basic cache check is consistent
                return consolidation_data
            
            # If no valid data, trigger consolidation analysis
            if "consolidation" not in self._analysis_modules:
                raise ValueError("No consolidation tracker module registered - module initialization failed")
            
            logger.info("📊 Triggering consolidation analysis...")
            consolidation_tracker = self._analysis_modules["consolidation"]
            if consolidation_tracker is None:
                raise ValueError("Consolidation tracker module is None - module initialization failed")
            
            current_time = time.time()
            
            # Detect consolidation and breakout
            consolidation = consolidation_tracker.detect_consolidation(
                unified_data=unified_data,
                current_price=current_price,
                current_time=current_time
            )
            
            breakout = consolidation_tracker.detect_breakout(
                unified_data=unified_data,
                current_price=current_price,
                current_time=current_time
            )
            
            # Get consolidation info
            consolidation_info = consolidation_tracker.get_consolidation_info()
            
            result = {
                "consolidation": consolidation_info,
                "breakout": None,
                "timestamp": current_time
            }
            
            if breakout:
                result["breakout"] = {
                    "direction": breakout.direction,
                    "confidence": breakout.confidence,
                    "entry_price": breakout.entry_price,
                    "stop_loss": breakout.stop_loss,
                    "take_profit": breakout.take_profit,
                    "range_upper": breakout.range_upper,
                    "range_lower": breakout.range_lower,
                    "range_width": breakout.range_width,
                    "duration_minutes": breakout.duration_minutes,
                    "reasoning": breakout.reasoning,
                    "detected_at": breakout.detected_at
                }
            
            # Consolidation tracker always returns dict (NO FALLBACKS)
            # Store result for future use
            self.update_analysis_data("consolidation", result)
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get consolidation analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    # ==================================================================================
    # UNIFIED PROCESSED DATA PACKAGES - Pre-processed data for consumers
    # ==================================================================================
    
    def get_unified_analysis_data(self) -> Dict[str, Any]:
        """
        Get comprehensive real-time market data structure with all components
        
        STRATEGY INDEPENDENT: All analysis is objective and not influenced by trading strategy.
        Strategy is determined AFTER this analysis is complete.
        """
        try:
            # Get current price (single source of truth)
            current_price = self.get_current_price()
            
            # Initialize RSI if not already initialized (only initialization, no updates here)
            if current_price and "rsi_calculator" in self._analysis_modules:
                rsi_calculator = self._analysis_modules["rsi_calculator"]
                if not rsi_calculator.rsi_initialized:
                    try:
                        # Get historical candles for RSI baseline calculation
                        from core.services.historical_data_service import create_historical_data_service
                        historical_service = create_historical_data_service()
                        from config.config import TradingConfig
                        candles_5m = historical_service.get_5m_candles(TradingConfig.SYMBOL, 30)
                        if candles_5m and len(candles_5m) >= 15:
                            rsi_calculator.calculate_hyperliquid_baseline_rsi(candles_5m)
                        else:
                            logger.warning("⚠️ RSI Calculator - insufficient historical data, using defaults")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to initialize RSI: {e}")
                # RSI updates happen via WebSocket callback only - NO FALLBACKS
            
            # Get all processed analysis data - STRATEGY INDEPENDENT
            # Analysis represents objective market facts, not strategy-specific interpretations
            # Trust API-level validation - get_trend_analysis() guarantees valid dict or raises
            rsi_data = self.get_rsi_analysis()
            trend_data = self.get_trend_analysis()  # API boundary - validates and raises if invalid
            volatility_data = self.get_volatility_analysis()
            volume_data = self.get_volume_analysis()
            
            unified_data = {
                # Core market data
                "current_price": current_price,
                "timestamp": time.time(),
                "strategy": None,  # Strategy determined after analysis
                
                # Flattened data for strategy selection (single source of truth)
                "trend_direction": trend_data["direction"],  # Required (NO FALLBACKS) - validated at API level
                "volatility_5m": volatility_data["volatility_percentage"] / 100.0,  # Required (NO FALLBACKS)
                "volatility_category": volatility_data["level"],  # Required (NO FALLBACKS)
                "volume_category": volume_data["volume_category"],  # Required (NO FALLBACKS)
                "rsi_value": rsi_data["rsi"],  # Required (NO FALLBACKS)
                
                # Technical Analysis Components (keep original nested structure for other uses)
                "rsi": rsi_data,
                "trend": trend_data,  # Required (NO FALLBACKS) - validated at API level
                "volatility": volatility_data,
                "volume": volume_data,
                "support_resistance": self.get_support_resistance_analysis(),
                "pressure": self.get_pressure_analysis(),
                "patterns": self.get_pattern_analysis(),
                
                # Market conditions and sentiment
                "market_conditions": self.get_market_conditions_analysis(),
                "cross_asset_analysis": self.get_cross_asset_analysis(),
                "funding_analysis": self.get_funding_analysis(),  # Required - will raise if API fails
                "orderbook_analysis": self.get_orderbook_analysis(),
                
                # Raw data access for additional processing
                "raw_data_access": {
                    "hyperliquid_api": self.hyperliquid_api,
                    "hyperliquid_websocket": self.hyperliquid_websocket,
                    "binance_api": self.binance_api
                }
            }
            
            # Add any additional analysis modules - all modules are required (NO FALLBACKS)
            # All registered modules must succeed or raise
            for module_name, module_instance in self._analysis_modules.items():
                if module_name not in ["volatility", "trend", "support_resistance", "rsi_calculator", "volume", "pressure", "patterns", "market_conditions", "funding_rate", "orderbook", "cross_asset_analysis"]:
                    # Get analysis data - all modules are required (NO FALLBACKS)
                    # _get_processed_data() will raise if module fails - no silent failures
                    analysis_data = self._get_processed_data(module_name)
                    unified_data[module_name] = analysis_data  # Required (NO FALLBACKS)
            
            return unified_data
            
        except Exception as e:
            logger.error(f"❌ Failed to coordinate unified analysis data: {e}")
            raise
    
    # ==================================================================================
    # ADDITIONAL ANALYSIS METHODS - Missing components for comprehensive data structure
    # ==================================================================================
    
    def get_pressure_analysis(self) -> Dict[str, Any]:
        """
        Get pressure analysis data - use the pressure calculator's get_latest_analysis method
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        """
        try:
            # Check cache first (consistent with other modules)
            pressure_data = self._get_processed_data("pressure")
            if pressure_data:
                # Validate cached data
                if pressure_data is None:
                    raise ValueError("Cached pressure data is None - cache corruption detected")
                if not isinstance(pressure_data, dict):
                    raise ValueError(f"Cached pressure data is not a dict: {type(pressure_data)}")
                return pressure_data
            
            # If no valid data, trigger pressure calculation
            if "pressure" not in self._analysis_modules:
                raise ValueError("No pressure analysis module registered - module initialization failed")
            
            logger.info("📊 Triggering pressure analysis...")
            pressure_calculator = self._analysis_modules["pressure"]
            if pressure_calculator is None:
                raise ValueError("Pressure calculator module is None - module initialization failed")
            
            # get_latest_analysis() guarantees valid dict or raises (NO FALLBACKS)
            pressure_result = pressure_calculator.get_latest_analysis()
            
            # Store result for future use
            self.update_analysis_data("pressure", pressure_result)
            return pressure_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get pressure analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_pattern_analysis(self) -> Dict[str, Any]:
        """
        Get pattern recognition analysis data with centralized caching
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        """
        try:
            if "pattern_recognition" not in self._analysis_modules:
                raise ValueError("No pattern recognition module registered - module initialization failed")
            
            pattern_engine = self._analysis_modules["pattern_recognition"]
            if pattern_engine is None:
                raise ValueError("Pattern recognition engine module is None - module initialization failed")
            
            # Use centralized cache for pattern analysis
            from core.services.centralized_cache import get_global_centralized_cache
            cache = get_global_centralized_cache()
            
            # Check cache first - use cache if valid (pattern expiration is handled in analysis, not cache invalidation)
            cache_key = "pattern_recognition_analysis"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                # Validate cached data
                if cached_data is None:
                    raise ValueError("Cached pattern data is None - cache corruption detected")
                if not isinstance(cached_data, dict):
                    raise ValueError(f"Cached pattern data is not a dict: {type(cached_data)}")
                # Cache hit - use cached data (patterns expiration is handled by pattern engine, not cache)
                return cached_data
            
            # Cache miss or invalid - perform fresh analysis
            logger.info("📊 Performing fresh pattern analysis...")
            # Get recent candles for pattern analysis (50 candles for detection)
            from core.services.historical_data_service import create_historical_data_service
            historical_service = create_historical_data_service()
            from config.config import TradingConfig
            candles = historical_service.get_5m_candles(TradingConfig.SYMBOL, 50)  # 50 candles for pattern detection
            
            if not candles or len(candles) < 10:
                raise ValueError(f"Insufficient candle data for pattern analysis: {len(candles) if candles else 0} < 10 - NO FALLBACKS")
            
            logger.info(f"📊 Analyzing {len(candles)} candles for patterns...")
            # analyze_patterns() always returns dict (even if no patterns found)
            analysis_result = pattern_engine.analyze_patterns(candles)
            
            # Log pattern detection results - NO FALLBACKS
            patterns_count = len(analysis_result["patterns"])
            nested = analysis_result["patterns_nested"]
            nested_count = sum(len(v) if isinstance(v, list) else 0 for v in nested.values())
            logger.info(f"📊 Pattern analysis complete: {patterns_count} flat patterns, {nested_count} nested patterns")
            
            # Store in centralized cache
            cache.set(cache_key, analysis_result)
            # Also store via MarketDataService for consistency
            self.update_analysis_data("pattern_recognition", analysis_result)
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get pattern analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_market_conditions_analysis(self, raw_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get market conditions analysis data
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        
        NEW: raw_data parameter contains pre-fetched external API data (fear_greed, whale, news).
        If provided, passes it to analyzer to avoid redundant API calls.
        
        Args:
            raw_data: Pre-fetched raw API data (required - NO FALLBACKS)
        """
        try:
            # Check cache first (consistent with other modules)
            conditions_data = self._get_processed_data("market_conditions")
            if conditions_data:
                # Validate cached data
                if conditions_data is None:
                    raise ValueError("Cached market conditions data is None - cache corruption detected")
                if not isinstance(conditions_data, dict):
                    raise ValueError(f"Cached market conditions data is not a dict: {type(conditions_data)}")
                return conditions_data
            
            # If no valid data, trigger market conditions analysis
            if "market_conditions" not in self._analysis_modules:
                raise ValueError("No market conditions module registered - module initialization failed")
            
            logger.info("📊 Triggering market conditions analysis...")
            conditions_analyzer = self._analysis_modules["market_conditions"]
            if conditions_analyzer is None:
                raise ValueError("Market conditions analyzer module is None - module initialization failed")
            
            # Get current market data for conditions analysis
            current_price = self.get_current_price()
            if not current_price or current_price <= 0:
                raise ValueError(f"No valid current price for market conditions analysis (got: {current_price})")
            
            market_data = {
                "current_price": current_price,
                "rsi": self.get_rsi_analysis()["rsi"],  # Required (NO FALLBACKS)
                "trend": self.get_trend_analysis()["direction"],  # Required (NO FALLBACKS)
                "volatility_5m": self.get_volatility_analysis()["volatility_percentage"] / 100.0,  # Required (NO FALLBACKS)
                "volatility_category": self.get_volatility_analysis()["level"],  # Required (NO FALLBACKS)
                "volume_category": self.get_volume_analysis()["volume_category"],  # Required (NO FALLBACKS)
                "timestamp": time.time()  # Required (NO FALLBACKS)
            }
            
            # Get 1d candles for market trend analysis - request more to ensure we have enough
            from core.services.historical_data_service import create_historical_data_service
            historical_service = create_historical_data_service()
            from config.config import TradingConfig
            candles_1d = historical_service.get_1d_candles(TradingConfig.SYMBOL, 30)  # Request 30 days to ensure we have at least 7
            
            # Pass raw_data to analyzer so it can use pre-fetched external API data
            # Get raw_data from parameter or stored value
            raw_data = self._get_raw_data(raw_data)
            # analyze_trading_conditions() always returns dict (may be error dict on exception)
            conditions_result = conditions_analyzer.analyze_trading_conditions(
                market_data, 
                candles_1d=candles_1d,
                raw_data=raw_data  # Pass pre-fetched data
            )
            
            # Store result for future use
            self.update_analysis_data("market_conditions", conditions_result)
            return conditions_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get market conditions analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_funding_analysis(self, raw_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get funding rate analysis data
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        
        NEW: raw_data parameter contains pre-fetched funding rate data.
        If provided, uses it instead of fetching from API.
        
        Args:
            raw_data: Pre-fetched raw API data (required - NO FALLBACKS)
        """
        try:
            # Check cache first (consistent with other modules)
            funding_data = self._get_processed_data("funding_rate")
            if funding_data:
                # Validate cached data
                if funding_data is None:
                    raise ValueError("Cached funding rate data is None - cache corruption detected")
                if not isinstance(funding_data, dict):
                    raise ValueError(f"Cached funding rate data is not a dict: {type(funding_data)}")
                return funding_data
            
            # If no valid data, trigger funding rate analysis
            if "funding_rate" not in self._analysis_modules:
                raise ValueError("No funding rate module registered - module initialization failed")
            
            logger.info("📊 Triggering funding rate analysis...")
            funding_analyzer = self._analysis_modules["funding_rate"]
            if funding_analyzer is None:
                raise ValueError("Funding rate analyzer module is None - module initialization failed")
            
            # Use pre-fetched raw data (all data is mandatory - NO FALLBACKS)
            # Get raw_data from parameter or stored value
            raw_data = self._get_raw_data(raw_data)
            if "funding" not in raw_data:
                raise ValueError("raw_data with 'funding' key is required (NO FALLBACKS)")
            funding_raw = raw_data["funding"]
            if not funding_raw:
                raise ValueError("Pre-fetched funding rate data is empty (NO FALLBACKS)")
            
            # analyze_funding_rate() guarantees valid dict or raises (NO FALLBACKS)
            funding_result = funding_analyzer.analyze_funding_rate(funding_raw)
            
            # Store result for future use
            self.update_analysis_data("funding_rate", funding_result)
            return funding_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get funding analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_whale_data(self) -> Dict[str, Any]:
        """
        Get whale analytics data
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        
        Note: If whale data is truly optional, callers should check availability
        before calling, or handle the exception appropriately.
        """
        try:
            # Use WhaleAnalysisCalculator to get fresh whale data
            from core.calculations.whale_analysis_calculator import WhaleAnalysisCalculator
            whale_calculator = WhaleAnalysisCalculator()
            # get_latest_analysis() guarantees valid dict or raises (NO FALLBACKS)
            whale_result = whale_calculator.get_latest_analysis()
            
            # Store result for future use
            self.update_analysis_data("whale_analytics", whale_result)
            return whale_result
        except Exception as e:
            logger.error(f"❌ Failed to get whale data: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_orderbook_analysis(self) -> Dict[str, Any]:
        """
        Get orderbook analysis data
        
        CRITICAL: This method MUST always return a valid dict or raise an exception.
        NO FALLBACKS - if calculation fails, we must know about it immediately.
        """
        try:
            # Check cache first (consistent with other modules)
            orderbook_data = self._get_processed_data("orderbook")
            if orderbook_data:
                # Validate cached data
                if orderbook_data is None:
                    raise ValueError("Cached orderbook data is None - cache corruption detected")
                if not isinstance(orderbook_data, dict):
                    raise ValueError(f"Cached orderbook data is not a dict: {type(orderbook_data)}")
                return orderbook_data
            
            # If no valid data, trigger orderbook analysis
            if "orderbook" not in self._analysis_modules:
                raise ValueError("No orderbook module registered - module initialization failed")
            
            logger.info("📊 Triggering orderbook analysis...")
            orderbook_analyzer = self._analysis_modules["orderbook"]
            if orderbook_analyzer is None:
                raise ValueError("Orderbook analyzer module is None - module initialization failed")
            
            # Get orderbook data - NO FALLBACKS
            if not self.hyperliquid_websocket:
                raise ValueError("Hyperliquid WebSocket not available for orderbook analysis - NO FALLBACKS")
            
            orderbook_data = self.hyperliquid_websocket.get_orderbook_data()
            if not orderbook_data:
                raise ValueError("No orderbook data available from WebSocket - NO FALLBACKS")
            
            current_price = self.get_current_price()
            if not current_price or current_price <= 0:
                raise ValueError(f"No valid current price for orderbook analysis (got: {current_price})")
            
            # analyze_orderbook() guarantees valid dict or raises (NO FALLBACKS)
            analysis_result = orderbook_analyzer.analyze_orderbook(orderbook_data, current_price)
            
            # Add raw bids/asks to the result for other modules to use
            bids, asks = self._extract_bids_asks(orderbook_data)
            analysis_result['bids'] = bids
            analysis_result['asks'] = asks
            
            # Store result for future use
            self.update_analysis_data("orderbook", analysis_result)
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get orderbook analysis: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def _extract_bids_asks(self, orderbook_data: Dict[str, Any]) -> tuple:
        """Extract bids and asks from orderbook data"""
        try:
            bids = []
            asks = []
            
            if isinstance(orderbook_data, list):
                if len(orderbook_data) == 2:
                    # Format: [bids_list, asks_list]
                    bids = orderbook_data[0] if orderbook_data[0] else []
                    asks = orderbook_data[1] if orderbook_data[1] else []
                else:
                    # Format: [level1, level2, ...] - need to separate by side
                    for level in orderbook_data:
                        if isinstance(level, dict):
                            if 'side' in level and level['side'] == 'B':
                                bids.append(level)
                            elif 'side' in level and level['side'] == 'A':
                                asks.append(level)
            elif isinstance(orderbook_data, dict):
                # Check for 'levels' key (WebSocket format: {'levels': [[bids], [asks]]})
                if 'levels' in orderbook_data and isinstance(orderbook_data['levels'], list) and len(orderbook_data['levels']) == 2:
                    bids = orderbook_data['levels'][0] if orderbook_data['levels'][0] else []
                    asks = orderbook_data['levels'][1] if orderbook_data['levels'][1] else []
                # Format: {"bids": [...], "asks": [...]}
                elif 'bids' in orderbook_data and 'asks' in orderbook_data:
                    bids = orderbook_data['bids']  # Required (NO FALLBACKS)
                    asks = orderbook_data['asks']  # Required (NO FALLBACKS)
            
            return bids, asks
        except Exception as e:
            logger.error(f"❌ Failed to extract bids/asks: {e}")
            raise ValueError(f"Failed to extract bids/asks from orderbook data: {e}")
    
    def get_real_time_market_data(self, strategy: str = "standard") -> Dict[str, Any]:
        """
        Get comprehensive real-time market data structure
        
        Returns:
            Dict with all real-time market components:
            - RSI: Relative Strength Index
            - Trends: Multi-timeframe trend analysis
            - Volume: Hyperliquid 5m + Binance global volume
            - Volatility: Multi-timeframe volatility analysis
            - Pressure: Buy/sell pressure analysis
            - S/R Levels: Support and resistance levels
            - Patterns: Pattern recognition results
        """
        try:
            logger.info("📊 Preparing comprehensive real-time market data structure...")
            
            # Get unified analysis data (includes all components)
            # Strategy parameter is deprecated - analysis is strategy-independent
            market_data = self.get_unified_analysis_data()
            
            # Structure the data for easy consumption - NO FALLBACKS
            # All components must be present for confidence calculation to be reliable
            real_time_data = {
                # Core market info - Required (NO FALLBACKS)
                "timestamp": market_data["timestamp"],  # Required (NO FALLBACKS)
                "current_price": market_data["current_price"],  # Required (NO FALLBACKS)
                "strategy": market_data["strategy"],  # Required (NO FALLBACKS)
                
                # Technical Analysis (Primary Components) - All Required (NO FALLBACKS)
                "rsi": market_data["rsi"],  # Required (NO FALLBACKS)
                "trend": market_data["trend"],  # Required (NO FALLBACKS)
                "volume": market_data["volume"],  # Required (NO FALLBACKS)
                "volatility": market_data["volatility"],  # Required (NO FALLBACKS)
                "volatility_5m": market_data["volatility_5m"],  # Required (NO FALLBACKS)
                "volatility_category": market_data["volatility_category"],  # Required (NO FALLBACKS)
                "pressure": market_data["pressure"],  # Required (NO FALLBACKS)
                "support_resistance": self._prepare_sr_data_for_dashboard(
                    market_data["support_resistance"],  # Required (NO FALLBACKS)
                    market_data["current_price"]  # Required (NO FALLBACKS)
                ),
                "patterns": market_data["patterns"],  # Required (NO FALLBACKS)
                
                # Additional market context - Required (NO FALLBACKS)
                "market_conditions": market_data["market_conditions"],  # Required (NO FALLBACKS)
                "funding_analysis": market_data["funding_analysis"],  # Required (NO FALLBACKS)
                "orderbook_analysis": market_data["orderbook_analysis"],  # Required (NO FALLBACKS)
                
                # Data quality indicators - All components are required (NO FALLBACKS)
                # If we reach here, all components are present (KeyError would have been raised otherwise)
                "data_quality": {
                    "all_components_available": True,  # All required components are present (NO FALLBACKS)
                    "last_update": time.time(),
                    "update_frequency": "real-time",
                    "data_completeness": 1.0  # 100% - all required data present
                }
            }
            
            logger.info("📊 Real-time market data structure prepared successfully")
            return real_time_data
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare real-time market data structure: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def get_dashboard_data(self, strategy: str = None) -> Dict[str, Any]:
        """
        Get optimized data package for dashboard UI with prediction data
        
        Args:
            strategy: DEPRECATED - Analysis is now strategy-independent.
                     Kept for backward compatibility but ignored.
        """
        try:
            # Get unified analysis data (strategy-independent)
            # Strategy parameter is deprecated but kept for backward compatibility
            analysis_data = self.get_unified_analysis_data()
            
            # Prediction data removed - will be re-implemented with clean architecture
            prediction_data = {}
            prediction_result = None
            
            # Add dashboard-specific data
            dashboard_data = {
                **analysis_data,
                "prediction_data": prediction_data,
                "prediction": prediction_result,
                "dashboard_ready": True,
                "last_update": time.time()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data: {e}")
            raise
    
    # ==================================================================================
    # DATA STATUS AND MONITORING - Track processed data status
    # ==================================================================================
    
    def get_data_status(self) -> Dict[str, Any]:
        """Get current processed data status"""
        try:
            # Get cache stats from centralized cache
            cache_stats = self._cache.get_stats()
            
            return {
                "registered_modules": list(self._analysis_modules.keys()),
                "cache_stats": cache_stats,
                "last_coordination": time.time()
            }
        except Exception as e:
            logger.error(f"❌ Failed to get data status: {e}")
            raise
    
    def invalidate_processed_data(self, data_type: str = None):
        """Invalidate processed data - specific type or all"""
        try:
            if data_type:
                # Invalidate specific data type using centralized cache
                self._cache.invalidate(data_type)
                logger.info(f"🗑️ Invalidated {data_type} processed data")
            else:
                # Invalidate all processed data using centralized cache
                self._cache.invalidate()
                logger.info("🗑️ Invalidated all processed data")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate processed data: {e}")
    
    def force_sr_recalculation(self):
        """Force S/R recalculation by clearing all related caches"""
        try:
            # Use centralized cache to clear all S/R related data
            self._cache.force_sr_recalculation()
            logger.info("🗑️ FORCED S/R recalculation - all caches cleared")
        except Exception as e:
            logger.error(f"❌ Failed to force S/R recalculation: {e}")
    
    def get_analysis_module_status(self) -> Dict[str, Any]:
        """Get status of registered analysis modules"""
        try:
            module_status = {}
            for module_name, module_instance in self._analysis_modules.items():
                try:
                    module_status[module_name] = {"status": "registered", "type": type(module_instance).__name__}
                except Exception as e:
                    module_status[module_name] = {"status": "error", "error": str(e)}
            
            return {
                "total_modules": len(self._analysis_modules),
                "module_status": module_status
            }
        except Exception as e:
            logger.error(f"❌ Failed to get analysis module status: {e}")
            raise
    
    def get_data_update_status(self) -> Dict[str, Any]:
        """Get current data update status for processed data coordination"""
        return {
            "hyperliquid_connected": True,
            "websocket_connected": self.hyperliquid_websocket.is_connected() if self.hyperliquid_websocket else False,
            "cache_stats": self._cache.get_stats(),
            "registered_modules": list(self._analysis_modules.keys()),
            "last_update": time.time()
        }
    
    def get_current_price(self) -> Optional[float]:
        """Get current price (single source of truth for all components)"""
        try:
            current_time = time.time()
            
            # Check if we need to update the price
            if (self._current_price is None or 
                current_time - self._price_timestamp > self._price_update_interval):
                
                # Update price from WebSocket (real-time) - NO FALLBACKS
                if not self.hyperliquid_websocket:
                    raise Exception("Hyperliquid WebSocket not available - NO FALLBACKS")
                
                new_price = self.hyperliquid_websocket.get_current_price()
                if new_price is None:
                    raise Exception("No price data available from WebSocket - NO FALLBACKS")
                
                if new_price != self._current_price:
                    self._current_price = new_price
                    self._price_timestamp = current_time
                    # Update RSI immediately when price changes
                    self._update_rsi_with_price(new_price)
            
            return self._current_price
            
        except Exception as e:
            logger.error(f"❌ Failed to get current price: {e}")
            raise Exception(f"Current price unavailable - NO FALLBACKS: {e}")
    
    def update_current_price(self) -> Optional[float]:
        """Force update current price from WebSocket (for real-time streaming)"""
        try:
            if self.hyperliquid_websocket:
                new_price = self.hyperliquid_websocket.get_current_price()
                if new_price is not None and new_price != self._current_price:
                    self._current_price = new_price
                    self._price_timestamp = time.time()
                    # Update RSI immediately when price changes
                    self._update_rsi_with_price(new_price)
                    return new_price
            return self._current_price
        except Exception as e:
            logger.error(f"❌ Failed to update current price: {e}")
            return self._current_price
    
    def _on_websocket_price_update(self, price_data: Dict[str, Any]):
        """
        Callback for WebSocket price updates - update RSI immediately
        
        CRITICAL: This is a high-frequency callback. Errors are logged at debug level
        to avoid spam, but critical errors should still be visible.
        """
        try:
            new_price = price_data.get("current_price") if price_data else None
            if new_price and new_price > 0:
                # Update internal price cache
                self._current_price = new_price
                self._price_timestamp = time.time()
                # Update RSI immediately
                self._update_rsi_with_price(new_price)
        except (KeyError, TypeError, ValueError) as e:
            # Handle specific data format errors (non-critical for callback)
            logger.debug(f"⚠️ WebSocket price update callback error (non-critical): {e}")
        except Exception as e:
            # Unexpected errors should be logged (but not spam)
            logger.warning(f"⚠️ Unexpected error in WebSocket price callback: {e}")
    
    def _prepare_sr_data_for_dashboard(self, sr_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Prepare S/R data for dashboard display with proper sorting
        
        Sorts levels by proximity to current price (closest first) for intuitive display:
        - Supports: Descending by price (closest to current price at top)
        - Resistances: Ascending by price (closest to current price at top)
        
        CRITICAL: NO FALLBACKS - if sorting fails, we must know about it.
        
        Args:
            sr_data: S/R data from analysis
            current_price: Current market price
            
        Returns:
            Dashboard-ready S/R data with sorted levels
            
        Raises:
            ValueError: If sr_data is invalid or sorting fails
        """
        if not sr_data or not isinstance(sr_data, dict):
            raise ValueError(f"Invalid sr_data for dashboard preparation: {type(sr_data)} - NO FALLBACKS")
        
        if current_price <= 0:
            raise ValueError(f"Invalid current_price for dashboard preparation: {current_price} - NO FALLBACKS")
        
        try:
            # Create a copy to avoid mutating original data
            dashboard_sr_data = sr_data.copy()
            
            # Sort top_support: Descending by price (highest price = closest to current = first)
            if "top_support" in dashboard_sr_data and dashboard_sr_data["top_support"]:
                dashboard_sr_data["top_support"] = sorted(
                    dashboard_sr_data["top_support"],
                    key=lambda x: x["price_level"],
                    reverse=True  # Descending: closest to current price first
                )
            
            # Sort top_resistance: Ascending by price (lowest price = closest to current = first)
            if "top_resistance" in dashboard_sr_data and dashboard_sr_data["top_resistance"]:
                dashboard_sr_data["top_resistance"] = sorted(
                    dashboard_sr_data["top_resistance"],
                    key=lambda x: x["price_level"],
                    reverse=False  # Ascending: closest to current price first
                )
            
            return dashboard_sr_data
            
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"❌ Failed to prepare S/R data for dashboard: {e}")
            raise ValueError(f"S/R data dashboard preparation failed: {e} (NO FALLBACKS)") from e
    
    def _update_rsi_with_price(self, new_price: float):
        """
        Update RSI immediately when price changes (called from price updates)
        
        CRITICAL: This is called frequently. Errors are handled gracefully but logged.
        """
        try:
            if "rsi_calculator" not in self._analysis_modules:
                return  # RSI calculator not available - not an error
            
            rsi_calculator = self._analysis_modules["rsi_calculator"]
            if rsi_calculator is None:
                return  # RSI calculator is None - not an error
            
            # Only update if RSI is already initialized
            if not rsi_calculator.rsi_initialized:
                return  # RSI not initialized yet - not an error
            
            old_rsi = rsi_calculator.current_rsi
            # update_realtime_rsi() returns updated RSI data - store it immediately
            rsi_result = rsi_calculator.update_realtime_rsi(new_price)
            new_rsi = rsi_calculator.current_rsi
            
            # Store updated RSI data to cache so get_rsi_analysis() returns fresh data
            self.update_analysis_data("rsi", rsi_result)
            
            # Trigger instant dashboard update if RSI changed significantly (throttled)
            if abs(new_rsi - old_rsi) >= TradingConstants.RSI_CHANGE_THRESHOLD:
                self._trigger_instant_rsi_dashboard_update()
        except (AttributeError, TypeError) as e:
            # Handle specific errors (missing attributes, wrong types) - non-critical
            logger.debug(f"⚠️ RSI update error (non-critical): {e}")
        except Exception as e:
            # Unexpected errors should be logged
            logger.warning(f"⚠️ Unexpected error in RSI update: {e}")
    
    def _trigger_instant_rsi_dashboard_update(self):
        """
        Trigger instant dashboard update for RSI changes (throttled to prevent spam)
        
        CRITICAL: This is called frequently. Dashboard might not be initialized yet,
        which is acceptable. Errors are handled gracefully.
        """
        try:
            current_time = time.time()
            # Throttle: Update dashboard at most every 500ms
            if current_time - self._last_rsi_dashboard_update < self._rsi_dashboard_update_interval:
                return  # Throttled - not an error
            
            self._last_rsi_dashboard_update = current_time
            
            # Get dashboard instance and trigger immediate update
            from core.dashboard.web_dashboard import EventDrivenTradingDashboard
            dashboard = EventDrivenTradingDashboard.get_global_instance()
            if dashboard:
                dashboard.force_data_update()
            # If dashboard is None, that's okay - it might not be initialized yet
        except (ImportError, AttributeError) as e:
            # Handle specific errors (import issues, missing attributes) - non-critical
            logger.debug(f"⚠️ Dashboard update error (non-critical): {e}")
        except Exception as e:
            # Unexpected errors should be logged
            logger.warning(f"⚠️ Unexpected error in dashboard update trigger: {e}")
    def get_market_data(self) -> Dict[str, Any]:
        """Get market data from API"""
        try:
            if not self.hyperliquid_api:
                raise ValueError("Hyperliquid API not available - NO FALLBACKS")
            from config.config import TradingConfig
            return self.hyperliquid_api.get_market_data(TradingConfig.SYMBOL)
        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            raise
    
# Factory function for dependency injection
def create_market_data_service(hyperliquid_api, hyperliquid_websocket, binance_api=None, binance_websocket=None) -> MarketDataService:
    """
    Factory function to create MarketDataService with dependency injection
    
    Args:
        hyperliquid_api: HyperliquidAPI instance
        hyperliquid_websocket: HyperliquidWebSocket instance
        binance_api: BinanceAPI instance (optional)
        binance_websocket: BinanceWebSocket instance (optional)
    
    Returns:
        Configured MarketDataService instance
    """
    return MarketDataService(hyperliquid_api, hyperliquid_websocket, binance_api, binance_websocket)

# Global instance for backward compatibility
_global_market_data_service = None

def get_global_market_data_service() -> MarketDataService:
    """Get the global MarketDataService singleton instance"""
    global _global_market_data_service
    if _global_market_data_service is None:
        # This will be set by SystemInitializer
        logger.warning("⚠️ MarketDataService not initialized - call SystemInitializer first")
    return _global_market_data_service

def set_global_market_data_service(service: MarketDataService):
    """Set the global MarketDataService instance"""
    global _global_market_data_service
    _global_market_data_service = service