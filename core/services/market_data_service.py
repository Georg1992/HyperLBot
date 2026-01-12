#!/usr/bin/env python3
"""
Market Data Service - Processed Data Coordinator Architecture
Single Responsibility: Coordinate processed analysis data from analysis modules
New Flow: Raw Data → Analysis Modules → MarketDataService → SessionOrchestrator
"""

import time
from typing import Dict, Any, Optional, List
from loguru import logger

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
        
        # Real-time price streaming (single source of truth)
        self._current_price = None
        self._price_timestamp = 0
        self._price_update_interval = 0.1  # 100ms for real-time updates
        
        # RSI update throttling for dashboard (prevent spam from rapid price changes)
        self._last_rsi_dashboard_update = 0
        self._rsi_dashboard_update_interval = 0.5  # Update dashboard at most every 500ms
        
        # Register WebSocket callback to update RSI immediately when price changes
        if self.hyperliquid_websocket:
            self.hyperliquid_websocket.add_price_callback(self._on_websocket_price_update)
            logger.debug("📊 Registered WebSocket price callback for real-time RSI updates")
        
        logger.info("📊 Processed Data Coordinator initialized - New architecture")
    
    # ==================================================================================
    # ANALYSIS MODULE COORDINATION - Register and manage analysis modules
    # ==================================================================================
    
    def register_analysis_module(self, module_name: str, module_instance: Any) -> None:
        """Register an analysis module for data coordination"""
        self._analysis_modules[module_name] = module_instance
        
        # Removed excessive debug logging for module registration
    
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
    
    def get_volatility_analysis(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get volatility analysis from VolatilityCalculator"""
        try:
            # Check if we have valid processed data
            volatility_data = self._get_processed_data("volatility")
            if volatility_data:
                return volatility_data
            
            # If no valid data, trigger analysis module to process
            if "volatility" in self._analysis_modules:
                logger.info("📊 Triggering volatility analysis...")
                volatility_result = self._analysis_modules["volatility"].get_latest_analysis()
                # Store result for future use
                self.update_analysis_data("volatility", volatility_result)
                return volatility_result
            
            raise ValueError("No volatility analysis module registered")
            
        except Exception as e:
            logger.error(f"❌ Failed to get volatility analysis: {e}")
            raise
    
    def get_trend_analysis(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get trend analysis from TrendCalculator with proper mapping"""
        try:
            # Check cache for already-mapped trend data
            trend_data = self._get_processed_data("trend")
            if trend_data:
                # Cache stores mapped data, check if it has UNKNOWN values
                if isinstance(trend_data, dict) and "detailed_timeframes" in trend_data:
                    # Check if all timeframes are UNKNOWN - if so, invalidate cache and recalculate
                    timeframes = trend_data.get("detailed_timeframes", {})
                    all_unknown = all(
                        timeframes.get(key, "UNKNOWN") == "UNKNOWN" 
                        for key in ["trend_15m", "trend_1h", "trend_4h", "trend_24h"]
                    )
                    if all_unknown:
                        logger.warning("⚠️ Cached trend data has all UNKNOWN values - invalidating cache and recalculating")
                        self._cache.invalidate("trend")
                        trend_data = None
                    else:
                        # Already mapped with valid data, return as-is
                        return trend_data
                elif isinstance(trend_data, dict):
                    # Raw data from cache (shouldn't happen, but handle it)
                    return self._map_trend_data(trend_data)
            
            # No valid cached data - fetch fresh trend data
            if "trend" in self._analysis_modules:
                logger.info("📊 Triggering trend analysis...")
                raw_trend_data = self._analysis_modules["trend"].get_latest_analysis(strategy)
                mapped_trend = self._map_trend_data(raw_trend_data)
                # Store mapped result for future use
                self.update_analysis_data("trend", mapped_trend)
                return mapped_trend
            
            raise ValueError("No trend analysis module registered")
            
        except Exception as e:
            logger.error(f"❌ Failed to get trend analysis: {e}")
            raise
    
    def _map_trend_data(self, raw_trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map trend calculator output to unified format - NO FALLBACKS"""
        try:
            if not raw_trend_data or not isinstance(raw_trend_data, dict):
                raise ValueError(f"Invalid raw_trend_data: expected dict, got {type(raw_trend_data)} - NO FALLBACKS")
            
            # Extract all timeframe trends
            trend_15m = raw_trend_data.get("trend_15m", "UNKNOWN")
            trend_1h = raw_trend_data.get("trend_1h", "UNKNOWN")
            trend_4h = raw_trend_data.get("trend_4h", "UNKNOWN")
            trend_24h = raw_trend_data.get("trend_24h", "UNKNOWN")
            
            # Use 1h as primary for strategy decisions, but preserve all timeframes
            primary_trend = trend_1h
            mapped_direction = self._map_trend_to_direction(primary_trend)
            
            # Create unified trend structure with ALL timeframes
            mapped_trend = {
                "direction": mapped_direction,
                "strength": self._map_trend_to_strength(primary_trend),
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
                "timestamp": raw_trend_data.get("timestamp", time.time()),
                "data_type": "trend"
            }
            
            # Log trend mapping only if there are issues (not UNKNOWN)
            if primary_trend != "UNKNOWN":
                logger.debug(f"📊 Trend mapped: {primary_trend} → {mapped_direction}")
            return mapped_trend
            
        except Exception as e:
            logger.error(f"❌ Trend mapping failed: {e}")
            raise
    
    def _map_trend_to_direction(self, trend: str) -> str:
        """Map detailed trend to simple direction for strategy manager"""
        if not trend or trend == "UNKNOWN" or trend is None:
            return "UNKNOWN"
            
        trend_mapping = {
            "STRONG_UPTREND": "BULLISH",
            "UPTREND": "BULLISH", 
            "WEAK_UPTREND": "BULLISH",
            "STRONG_DOWNTREND": "BEARISH",
            "DOWNTREND": "BEARISH",
            "WEAK_DOWNTREND": "BEARISH",
            "SIDEWAYS": "SIDEWAYS"
        }
        return trend_mapping.get(trend, "UNKNOWN")
    
    def _map_trend_to_strength(self, trend: str) -> str:
        """Map detailed trend to strength level"""
        if not trend or trend == "UNKNOWN" or trend is None:
            return "UNKNOWN"
            
        strength_mapping = {
            "STRONG_UPTREND": "STRONG",
            "STRONG_DOWNTREND": "STRONG",
            "UPTREND": "MODERATE",
            "DOWNTREND": "MODERATE", 
            "WEAK_UPTREND": "WEAK",
            "WEAK_DOWNTREND": "WEAK",
            "SIDEWAYS": "NEUTRAL"
        }
        return strength_mapping.get(trend, "UNKNOWN")
    
    def get_support_resistance_analysis(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get S/R analysis from SupportResistanceCalculator
        
        Args:
            strategy: Trading strategy name (default: "standard")
        """
        try:
            # Use strategy-aware cache key
            cache_key = f"support_resistance_{strategy}"
            sr_data = self._cache.get(cache_key)
            if sr_data:
                return sr_data
            
            if "support_resistance" in self._analysis_modules:
                logger.info(f"📊 Triggering S/R analysis (strategy: {strategy})...")
                # Get current price for S/R calculation
                current_price = None
                if self.hyperliquid_websocket:
                    current_price = self.hyperliquid_websocket.get_current_price()
                elif self.hyperliquid_api:
                    current_price = self.hyperliquid_api.get_current_price("BTC")
                
                if not current_price or current_price <= 0:
                    raise ValueError("No valid current price for S/R analysis")
                
                # Pass strategy to SR calculator
                sr_calculator = self._analysis_modules["support_resistance"]
                # NO FALLBACKS - assume calculate_multi_timeframe_levels exists
                result = sr_calculator.calculate_multi_timeframe_levels(current_price, strategy=strategy)
                # Cache with strategy-aware key
                self._cache.set(cache_key, result, ttl=300)
                # Also store via MarketDataService for consistency
                self.update_analysis_data("support_resistance", result)
                return result
            
            raise ValueError("No S/R analysis module registered")
            
        except Exception as e:
            logger.error(f"❌ Failed to get S/R analysis: {e}")
            raise
    
    def get_rsi_analysis(self) -> Dict[str, Any]:
        """Get RSI analysis from RSICalculator"""
        try:
            # Check if we have valid processed data
            rsi_data = self._get_processed_data("rsi")
            if rsi_data:
                return rsi_data
            
            # If no valid data, trigger RSI calculation
            if "rsi_calculator" in self._analysis_modules:
                logger.info("📊 Triggering RSI analysis...")
                rsi_result = self._analysis_modules["rsi_calculator"].get_latest_analysis()
                # Store result for future use
                self.update_analysis_data("rsi", rsi_result)
                return rsi_result
            
            raise ValueError("No RSI analysis module registered")
            
        except Exception as e:
            logger.error(f"❌ Failed to get RSI analysis: {e}")
            raise
    
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
        """Get volume analysis from VolumeCalculator"""
        try:
            # Check if we have valid processed data
            volume_data = self._get_processed_data("volume")
            if volume_data:
                return volume_data
            
            # If no valid data, trigger volume calculation
            if "volume" in self._analysis_modules:
                logger.info("📊 Triggering volume analysis...")
                volume_calculator = self._analysis_modules["volume"]
                volume_result = volume_calculator.get_latest_analysis(
                    hyperliquid_websocket=self.hyperliquid_websocket
                )
                # Store result for future use
                self.update_analysis_data("volume", volume_result)
                return volume_result
            
            raise ValueError("No volume calculator registered")
            
        except Exception as e:
            logger.error(f"❌ Failed to get volume analysis: {e}")
            raise
    
    def get_cross_asset_analysis(self) -> Dict[str, Any]:
        """Get cross asset correlation analysis"""
        try:
            # Check if we have valid processed data
            cross_asset_data = self._get_processed_data("cross_asset_correlation_analyzer")
            if cross_asset_data:
                return cross_asset_data
            
            # If no valid data, trigger cross asset analysis
            if "cross_asset_correlation_analyzer" in self._analysis_modules:
                logger.info("📊 Triggering cross asset correlation analysis...")
                cross_asset_analyzer = self._analysis_modules["cross_asset_correlation_analyzer"]
                current_price = self.get_current_price() or 110000.0
                cross_asset_result = cross_asset_analyzer.analyze_cross_asset_correlations(current_price)
                # Store result for future use
                self.update_analysis_data("cross_asset_correlation_analyzer", cross_asset_result)
                return cross_asset_result
            
            raise ValueError("No cross asset correlation analyzer registered")
            
        except Exception as e:
            logger.error(f"❌ Failed to get cross asset analysis: {e}")
            raise
    
    # ==================================================================================
    # UNIFIED PROCESSED DATA PACKAGES - Pre-processed data for consumers
    # ==================================================================================
    
    def get_unified_analysis_data(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get comprehensive real-time market data structure with all components"""
        try:
            logger.debug("📊 Coordinating unified analysis data...")
            
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
                        candles_5m = historical_service.get_5m_candles("BTC", 30)
                        if candles_5m and len(candles_5m) >= 15:
                            rsi_calculator.calculate_hyperliquid_baseline_rsi(candles_5m)
                            logger.debug("📊 RSI calculator initialized with baseline data")
                        else:
                            logger.warning("⚠️ RSI Calculator - insufficient historical data, using defaults")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to initialize RSI: {e}")
                # RSI updates happen via WebSocket callback only - NO FALLBACKS
            
            # Get all processed analysis data
            rsi_data = self.get_rsi_analysis()
            trend_data = self.get_trend_analysis(strategy)
            volatility_data = self.get_volatility_analysis(strategy)
            volume_data = self.get_volume_analysis()
            
            unified_data = {
                # Core market data
                "current_price": current_price,
                "timestamp": time.time(),
                "strategy": strategy,
                
                # Flattened data for strategy selection (single source of truth)
                "trend_direction": trend_data.get("direction", "SIDEWAYS"),
                "volatility_5m": volatility_data.get("volatility_percentage", 0) / 100.0,
                "volatility_category": volatility_data.get("level", "MODERATE"),
                "volume_category": volume_data.get("hyperliquid_5m", {}).get("volume_category", "MODERATE"),
                "rsi_value": rsi_data.get("rsi", 50.0),
                
                # Technical Analysis Components (keep original nested structure for other uses)
                "rsi": rsi_data,
                "trend": trend_data,
                "volatility": volatility_data,
                "volume": volume_data,
                "support_resistance": self.get_support_resistance_analysis(strategy),
                "pressure": self.get_pressure_analysis(),
                "patterns": self.get_pattern_analysis(),
                
                # Market conditions and sentiment
                "market_conditions": self.get_market_conditions_analysis(),
                "cross_asset_analysis": self.get_cross_asset_analysis(),
                "funding_analysis": self.get_funding_analysis(),
                "orderbook_analysis": self.get_orderbook_analysis(),
                
                # Raw data access for additional processing
                "raw_data_access": {
                    "hyperliquid_api": self.hyperliquid_api,
                    "hyperliquid_websocket": self.hyperliquid_websocket,
                    "binance_api": self.binance_api
                }
            }
            
            # Add any additional analysis modules
            for module_name, module_instance in self._analysis_modules.items():
                if module_name not in ["volatility", "trend", "support_resistance"]:
                    try:
                        analysis_data = self._get_processed_data(module_name)
                        if analysis_data:
                            unified_data[module_name] = analysis_data
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to get {module_name} analysis: {e}")
            
            logger.debug(f"📊 Unified analysis data coordinated: {len(unified_data)} keys")
            return unified_data
            
        except Exception as e:
            logger.error(f"❌ Failed to coordinate unified analysis data: {e}")
            raise
    
    # ==================================================================================
    # ADDITIONAL ANALYSIS METHODS - Missing components for comprehensive data structure
    # ==================================================================================
    
    def get_pressure_analysis(self) -> Dict[str, Any]:
        """Get pressure analysis data - use the pressure calculator's get_latest_analysis method"""
        try:
            if "pressure" in self._analysis_modules:
                pressure_calculator = self._analysis_modules["pressure"]
                # NO FALLBACKS - assume get_latest_analysis exists
                pressure_result = pressure_calculator.get_latest_analysis()
                # Store result for future use
                self.update_analysis_data("pressure", pressure_result)
                return pressure_result
            else:
                raise ValueError("No pressure analysis module registered")
        except Exception as e:
            logger.error(f"❌ Failed to get pressure analysis: {e}")
            raise
    
    def get_pattern_analysis(self) -> Dict[str, Any]:
        """Get pattern recognition analysis data with centralized caching"""
        try:
            if "pattern_recognition" in self._analysis_modules:
                # Use centralized cache for pattern analysis
                from core.services.centralized_cache import get_global_centralized_cache
                cache = get_global_centralized_cache()
                
                # Check cache first - use cache if valid (pattern expiration is handled in analysis, not cache invalidation)
                cache_key = "pattern_recognition_analysis"
                cached_data = cache.get(cache_key)
                
                if cached_data:
                    # Cache hit - use cached data (patterns expiration is handled by pattern engine, not cache)
                    patterns_count = 0
                    if isinstance(cached_data, dict):
                        flat_patterns = cached_data.get("patterns", [])
                        nested_patterns = cached_data.get("patterns_nested", {})
                        if isinstance(flat_patterns, list):
                            patterns_count += len(flat_patterns)
                        if isinstance(nested_patterns, dict):
                            for category, pattern_list in nested_patterns.items():
                                if isinstance(pattern_list, list):
                                    patterns_count += len(pattern_list)
                    # Removed excessive debug log for cached pattern analysis
                    return cached_data
                
                # Cache miss or invalid - perform fresh analysis
                logger.info("📊 Performing fresh pattern analysis...")
                pattern_engine = self._analysis_modules["pattern_recognition"]
                # Get recent candles for pattern analysis (50 candles for detection)
                from core.services.historical_data_service import create_historical_data_service
                historical_service = create_historical_data_service()
                candles = historical_service.get_5m_candles("BTC", 50)  # 50 candles for pattern detection
                if candles:
                    logger.info(f"📊 Analyzing {len(candles)} candles for patterns...")
                    analysis_result = pattern_engine.analyze_patterns(candles)
                    
                    # Log pattern detection results
                    patterns_count = len(analysis_result.get("patterns", []))
                    nested = analysis_result.get("patterns_nested", {})
                    nested_count = sum(len(v) if isinstance(v, list) else 0 for v in nested.values())
                    logger.info(f"📊 Pattern analysis complete: {patterns_count} flat patterns, {nested_count} nested patterns")
                    
                    # Store in centralized cache
                    cache.set(cache_key, analysis_result)
                    # Also store via MarketDataService for consistency
                    self.update_analysis_data("pattern_recognition", analysis_result)
                    return analysis_result
                raise ValueError("No candle data available for pattern analysis")
            else:
                raise ValueError("No pattern recognition module registered")
        except Exception as e:
            logger.error(f"❌ Failed to get pattern analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def get_market_conditions_analysis(self) -> Dict[str, Any]:
        """Get market conditions analysis data"""
        try:
            if "market_conditions" in self._analysis_modules:
                conditions_analyzer = self._analysis_modules["market_conditions"]
                # Get current market data for conditions analysis
                current_price = self.get_current_price()
                if current_price:
                    market_data = {
                        "current_price": current_price,
                        "rsi": self.get_rsi_analysis().get("rsi", 50.0),
                        "trend": self.get_trend_analysis("standard").get("direction", "SIDEWAYS"),
                        "volatility_5m": self.get_volatility_analysis("standard").get("volatility_percentage", 0.0) / 100.0,
                        "volatility_category": self.get_volatility_analysis("standard").get("level", "MODERATE"),
                        "volume_category": self.get_volume_analysis().get("hyperliquid_5m", {}).get("volume_category", "MODERATE")
                    }
                    # Get 1d candles for market trend analysis - request more to ensure we have enough
                    from core.services.historical_data_service import create_historical_data_service
                    historical_service = create_historical_data_service()
                    candles_1d = historical_service.get_1d_candles("BTC", 30)  # Request 30 days to ensure we have at least 7
                    
                    conditions_result = conditions_analyzer.analyze_trading_conditions(market_data, candles_1d=candles_1d)
                    # Store result for future use
                    self.update_analysis_data("market_conditions", conditions_result)
                    return conditions_result
                raise ValueError("No current price available for market conditions analysis")
            else:
                raise ValueError("No market conditions module registered")
        except Exception as e:
            logger.error(f"❌ Failed to get market conditions analysis: {e}")
            raise
    
    def get_funding_analysis(self) -> Dict[str, Any]:
        """Get funding rate analysis data"""
        try:
            if "funding_rate" in self._analysis_modules:
                funding_analyzer = self._analysis_modules["funding_rate"]
                # Get funding rate data from API
                if self.hyperliquid_api:
                    funding_data = self.hyperliquid_api.get_funding_rate("BTC")
                    if funding_data:
                        funding_result = funding_analyzer.analyze_funding_rate(funding_data)
                        # Store result for future use
                        self.update_analysis_data("funding_rate", funding_result)
                        return funding_result
                raise ValueError("No funding rate data available")
            else:
                raise ValueError("No funding rate module registered")
        except Exception as e:
            logger.error(f"❌ Failed to get funding analysis: {e}")
            raise
    
    def get_orderbook_analysis(self) -> Dict[str, Any]:
        """Get orderbook analysis data"""
        try:
            if "orderbook" in self._analysis_modules:
                orderbook_analyzer = self._analysis_modules["orderbook"]
                # Get orderbook data for analysis
                orderbook_data = None
                
                # Get orderbook data - NO FALLBACKS
                if not self.hyperliquid_websocket:
                    raise Exception("Hyperliquid WebSocket not available - NO FALLBACKS")
                
                orderbook_data = self.hyperliquid_websocket.get_orderbook_data()
                if not orderbook_data:
                    raise Exception("No orderbook data available - NO FALLBACKS")
                
                current_price = self.get_current_price()
                if orderbook_data and current_price:
                    analysis_result = orderbook_analyzer.analyze_orderbook(orderbook_data, current_price)
                    # Add raw bids/asks to the result for other modules to use
                    bids, asks = self._extract_bids_asks(orderbook_data)
                    analysis_result['bids'] = bids
                    analysis_result['asks'] = asks
                    # Store result for future use
                    self.update_analysis_data("orderbook", analysis_result)
                    return analysis_result
                
                raise ValueError("No orderbook data available for analysis")
            else:
                raise ValueError("No orderbook module registered")
        except Exception as e:
            logger.error(f"❌ Failed to get orderbook analysis: {e}")
            raise
    
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
                            if level.get('side') == 'B':
                                bids.append(level)
                            elif level.get('side') == 'A':
                                asks.append(level)
            elif isinstance(orderbook_data, dict):
                # Check for 'levels' key (WebSocket format: {'levels': [[bids], [asks]]})
                if 'levels' in orderbook_data and isinstance(orderbook_data['levels'], list) and len(orderbook_data['levels']) == 2:
                    bids = orderbook_data['levels'][0] if orderbook_data['levels'][0] else []
                    asks = orderbook_data['levels'][1] if orderbook_data['levels'][1] else []
                # Format: {"bids": [...], "asks": [...]}
                elif 'bids' in orderbook_data and 'asks' in orderbook_data:
                    bids = orderbook_data.get('bids', [])
                    asks = orderbook_data.get('asks', [])
            
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
            market_data = self.get_unified_analysis_data(strategy)
            
            # Structure the data for easy consumption
            real_time_data = {
                # Core market info
                "timestamp": market_data.get("timestamp", time.time()),
                "current_price": market_data.get("current_price", 0.0),
                "strategy": market_data.get("strategy", strategy),
                
                # Technical Analysis (Primary Components) - Handle missing modules gracefully
                "rsi": market_data.get("rsi", {
                    "value": 0.0,
                    "category": "unknown",
                    "signal": "neutral",
                    "timestamp": time.time()
                }),
                
                "trend": market_data.get("trend", {
                    "direction": "neutral",
                    "strength": 0.0,
                    "timeframes": {},
                    "consensus": "neutral",
                    "timestamp": time.time()
                }),
                
                "volume": market_data.get("volume", {
                    "hyperliquid_5m": {"current_volume_btc": 0.0, "volume_category": "unknown"},
                    "binance_global": {"current_volume_btc": 0.0, "volume_category": "unknown"},
                    "total_volume_btc": 0.0,
                    "volume_category": "unknown",
                    "timestamp": time.time()
                }),
                
                "volatility": market_data.get("volatility", {
                    "current": 0.0,
                    "category": "unknown",
                    "change_detection": {"status": "unknown"},
                    "multi_timeframe": {
                        "1m": 0.0,
                        "5m": 0.0,
                        "1h": 0.0,
                        "1d": 0.0
                    },
                    "timestamp": time.time()
                }),
                
                # Dashboard-specific volatility fields
                "volatility_5m": market_data.get("volatility_5m", 0.0),
                "volatility_category": market_data.get("volatility_category", "UNKNOWN"),
                
                "pressure": market_data.get("pressure", {
                    "buy_pressure": 0.0,
                    "sell_pressure": 0.0,
                    "net_pressure": 0.0,
                    "pressure_ratio": 0.0,
                    "timestamp": time.time()
                }),
                
                "support_resistance": self._prepare_sr_data_for_dashboard(
                    market_data.get("support_resistance", {}),
                    market_data.get("current_price", 0.0)
                ),
                
                "patterns": market_data.get("patterns", {
                    "active_patterns": [],
                    "pattern_signals": [],
                    "confidence_scores": [],
                    "timestamp": time.time()
                }),
                
                # Additional market context
                "market_conditions": market_data.get("market_conditions", {}),
                "funding_analysis": market_data.get("funding_analysis", {}),
                "orderbook_analysis": market_data.get("orderbook_analysis", {}),
                
                # Data quality indicators
                "data_quality": {
                    "all_components_available": all([
                        market_data.get("rsi"),
                        market_data.get("trend"),
                        market_data.get("volume"),
                        market_data.get("volatility"),
                        market_data.get("support_resistance", {}).get("status") == "ok"
                    ]),
                    "last_update": time.time(),
                    "update_frequency": "real-time"
                }
            }
            
            logger.info("📊 Real-time market data structure prepared successfully")
            return real_time_data
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare real-time market data structure: {e}")
            return {
                "error": str(e),
                "timestamp": time.time(),
                "data_quality": {"all_components_available": False}
            }
    
    def get_dashboard_data(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get optimized data package for dashboard UI with prediction data"""
        try:
            # Get unified analysis data
            analysis_data = self.get_unified_analysis_data(strategy)
            
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
            
            logger.debug(f"📊 Dashboard data prepared with prediction: {prediction_result is not None}")
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
                    logger.debug(f"📊 Real-time price updated: ${self._current_price:.2f}")
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
        """Callback for WebSocket price updates - update RSI immediately"""
        try:
            new_price = price_data.get("current_price")
            if new_price and new_price > 0:
                # Update internal price cache
                self._current_price = new_price
                self._price_timestamp = time.time()
                # Update RSI immediately
                self._update_rsi_with_price(new_price)
        except Exception as e:
            # Don't log errors here to avoid spam
            pass
    
    def _update_rsi_with_price(self, new_price: float):
        """Update RSI immediately when price changes (called from price updates)"""
        try:
            if "rsi_calculator" in self._analysis_modules:
                rsi_calculator = self._analysis_modules["rsi_calculator"]
                # Only update if RSI is already initialized
                if rsi_calculator.rsi_initialized:
                    old_rsi = rsi_calculator.current_rsi
                    rsi_calculator.update_realtime_rsi(new_price)
                    new_rsi = rsi_calculator.current_rsi
                    
                    # Trigger instant dashboard update if RSI changed significantly (throttled)
                    if abs(new_rsi - old_rsi) >= 0.1:  # Only if RSI changed by at least 0.1
                        self._trigger_instant_rsi_dashboard_update()
        except Exception as e:
            # Don't log errors here to avoid spam - RSI update failures are non-critical
            pass
    
    def _trigger_instant_rsi_dashboard_update(self):
        """Trigger instant dashboard update for RSI changes (throttled to prevent spam)"""
        try:
            current_time = time.time()
            # Throttle: Update dashboard at most every 500ms
            if current_time - self._last_rsi_dashboard_update >= self._rsi_dashboard_update_interval:
                self._last_rsi_dashboard_update = current_time
                
                # Get dashboard instance and trigger immediate update
                try:
                    from core.dashboard.web_dashboard import EventDrivenTradingDashboard
                    dashboard = EventDrivenTradingDashboard.get_global_instance()
                    if dashboard:
                        dashboard.force_data_update()
                        # Removed excessive debug log for instant RSI update trigger
                except Exception as e:
                    # Dashboard might not be initialized yet - that's okay
                    pass
        except Exception as e:
            # Don't log errors here to avoid spam
            pass
    
    def _prepare_sr_data_for_dashboard(self, sr_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Prepare S/R data for dashboard with pre-filtered levels
        
        Uses SRLevelFilter to provide filtered levels for display, reducing frontend filtering logic.
        
        Args:
            sr_data: Raw S/R data from calculator
            current_price: Current market price
            
        Returns:
            Formatted S/R data with filtered levels for dashboard
        """
        try:
            from core.calculations.sr_level_filter import SRLevelFilter
            
            all_levels = sr_data.get("levels", [])
            metadata = sr_data.get("metadata", {})
            
            # Filter levels for dashboard display (top 2)
            level_filter = SRLevelFilter()
            filtered_levels = level_filter.filter_for_display(
                all_levels=all_levels,
                current_price=current_price,
                max_levels=2
            )
            
            return {
                "status": sr_data.get("status", "ok"),
                "levels": all_levels,  # Still provide all levels for flexibility
                "key_levels": all_levels,  # Alias for backward compatibility
                "top_2_support": filtered_levels["support"],  # Pre-filtered for dashboard
                "top_2_resistance": filtered_levels["resistance"],  # Pre-filtered for dashboard
                "metadata": metadata,
                "strongest_support": metadata.get("strongest_support", 0),
                "strongest_resistance": metadata.get("strongest_resistance", 0),
                "support_score": metadata.get("support_score", 0),
                "resistance_score": metadata.get("resistance_score", 0),
                "levels_count": metadata.get("total_levels", 0),
                "timestamp": metadata.get("timestamp", time.time())
            }
        except Exception as e:
            logger.error(f"❌ Failed to prepare S/R data for dashboard: {e}")
            # Return safe fallback
            return {
                "status": "error",
                "levels": [],
                "key_levels": [],
                "top_2_support": [],
                "top_2_resistance": [],
                "metadata": {},
                "strongest_support": 0,
                "strongest_resistance": 0,
                "support_score": 0,
                "resistance_score": 0,
                "levels_count": 0,
                "timestamp": time.time()
            }
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get market data from API"""
        try:
            if not self.hyperliquid_api:
                raise ValueError("Hyperliquid API not available - NO FALLBACKS")
            return self.hyperliquid_api.get_market_data("BTC")
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