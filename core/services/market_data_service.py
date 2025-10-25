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
        
        # Legacy update schedules (for backward compatibility)
        self._update_schedules = {
            "volatility": 60,      # 1 minute
            "trend": 60,           # 1 minute  
            "support_resistance": 300,  # 5 minutes
            "rsi": 60,             # 1 minute
            "volume": 30,          # 30 seconds
            "market_conditions": 300,  # 5 minutes
            "cross_asset_correlation_analyzer": 300,  # 5 minutes
        }
        
        # Analysis module references (will be set by SystemInitializer)
        self._analysis_modules = {}
        
        # Real-time price streaming (single source of truth)
        self._current_price = None
        self._price_timestamp = 0
        self._price_update_interval = 0.1  # 100ms for real-time updates
        
        logger.info("📊 Processed Data Coordinator initialized - New architecture")
    
    # ==================================================================================
    # ANALYSIS MODULE COORDINATION - Register and manage analysis modules
    # ==================================================================================
    
    def register_analysis_module(self, module_name: str, module_instance: Any) -> None:
        """Register an analysis module for data coordination"""
        self._analysis_modules[module_name] = module_instance
        
        # Set raw data sources for modules that need them
        if hasattr(module_instance, 'set_raw_data_sources'):
            module_instance.set_raw_data_sources(self.hyperliquid_api, self.hyperliquid_websocket)
            logger.debug(f"📊 Set raw data sources for: {module_name}")
        
        logger.debug(f"📊 Registered analysis module: {module_name}")
    
    def _is_data_valid(self, data_type: str) -> bool:
        """Check if processed data is still valid based on schedule"""
        # Data validity is now handled by centralized cache TTL
        return True
    
    def _store_processed_data(self, data_type: str, data: Any) -> None:
        """Store processed data from analysis modules"""
        self._cache.set(data_type, data)
        logger.debug(f"📊 Stored processed data: {data_type}")
    
    def _get_processed_data(self, data_type: str) -> Any:
        """Get processed data if valid"""
        return self._cache.get(data_type)
    
    # ==================================================================================
    # PROCESSED DATA COORDINATION - Coordinate analysis from modules
    # ==================================================================================
    
    def update_analysis_data(self, data_type: str, analysis_data: Any) -> None:
        """Receive processed analysis data from analysis modules"""
        self._store_processed_data(data_type, analysis_data)
        logger.debug(f"📊 Updated {data_type} analysis data")
    
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
                # Analysis module will process raw data and call update_analysis_data
                return self._analysis_modules["volatility"].get_latest_analysis()
            
            logger.warning("⚠️ No volatility analysis module registered")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get volatility analysis: {e}")
            return {}
    
    def get_trend_analysis(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get trend analysis from TrendCalculator"""
        try:
            trend_data = self._get_processed_data("trend")
            if trend_data:
                return trend_data
            
            if "trend" in self._analysis_modules:
                logger.info("📊 Triggering trend analysis...")
                return self._analysis_modules["trend"].get_latest_analysis(strategy)
            
            logger.warning("⚠️ No trend analysis module registered")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get trend analysis: {e}")
            return {}
    
    def get_support_resistance_analysis(self) -> Dict[str, Any]:
        """Get S/R analysis from SupportResistanceCalculator"""
        try:
            sr_data = self._get_processed_data("support_resistance")
            if sr_data:
                return sr_data
            
            if "support_resistance" in self._analysis_modules:
                logger.info("📊 Triggering S/R analysis...")
                # Get current price for S/R calculation
                current_price = None
                if self.hyperliquid_websocket:
                    current_price = self.hyperliquid_websocket.get_current_price()
                elif self.hyperliquid_api:
                    current_price = self.hyperliquid_api.get_current_price("BTC")
                
                return self._analysis_modules["support_resistance"].get_latest_analysis(current_price)
            
            logger.warning("⚠️ No S/R analysis module registered")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get S/R analysis: {e}")
            return {}
    
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
                # RSI module will process raw data and call update_analysis_data
                rsi_result = self._analysis_modules["rsi_calculator"].get_latest_analysis()
                return rsi_result
            
            logger.warning("⚠️ No RSI analysis module registered")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get RSI analysis: {e}")
            return {}
    
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
                return volume_calculator.get_latest_analysis(
                    hyperliquid_websocket=self.hyperliquid_websocket
                )
            
            logger.warning("⚠️ No volume calculator registered")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get volume analysis: {e}")
            return {}
    
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
                return cross_asset_analyzer.analyze_cross_asset_correlations(self._current_price or 110000.0)
            
            logger.warning("⚠️ No cross asset correlation analyzer registered")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get cross asset analysis: {e}")
            return {}
    
    # ==================================================================================
    # UNIFIED PROCESSED DATA PACKAGES - Pre-processed data for consumers
    # ==================================================================================
    
    def get_unified_analysis_data(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get comprehensive real-time market data structure with all components"""
        try:
            logger.info("📊 Coordinating unified analysis data...")
            
            # Get current price (single source of truth)
            current_price = self.get_current_price()
            
            # Update RSI with current price for real-time calculation
            if current_price and "rsi_calculator" in self._analysis_modules:
                rsi_calculator = self._analysis_modules["rsi_calculator"]
                rsi_calculator.update_realtime_rsi(current_price)
            
            # Get all processed analysis data
            unified_data = {
                # Core market data
                "current_price": current_price,
                "timestamp": time.time(),
                "strategy": strategy,
                
                # Technical Analysis Components
                "rsi": self.get_rsi_analysis(),
                "trend": self.get_trend_analysis(strategy),
                "volatility": self.get_volatility_analysis(strategy),
                "volume": self.get_volume_analysis(),
                "support_resistance": self.get_support_resistance_analysis(),
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
            
            logger.info("📊 Unified analysis data coordinated")
            return unified_data
            
        except Exception as e:
            logger.error(f"❌ Failed to coordinate unified analysis data: {e}")
            return {}
    
    # ==================================================================================
    # ADDITIONAL ANALYSIS METHODS - Missing components for comprehensive data structure
    # ==================================================================================
    
    def get_pressure_analysis(self) -> Dict[str, Any]:
        """Get pressure analysis data - use the pressure calculator's get_latest_analysis method"""
        try:
            if "pressure" in self._analysis_modules:
                pressure_calculator = self._analysis_modules["pressure"]
                # Use the pressure calculator's get_latest_analysis method which handles orderbook retrieval correctly
                if hasattr(pressure_calculator, 'get_latest_analysis'):
                    pressure_result = pressure_calculator.get_latest_analysis()
                    return pressure_result
                else:
                    logger.warning("⚠️ Pressure calculator does not have get_latest_analysis method")
                    return {}
            else:
                logger.warning("⚠️ No pressure analysis module registered")
                return {}
        except Exception as e:
            logger.error(f"❌ Failed to get pressure analysis: {e}")
            return {}
    
    def get_pattern_analysis(self) -> Dict[str, Any]:
        """Get pattern recognition analysis data"""
        try:
            if "pattern_recognition" in self._analysis_modules:
                pattern_engine = self._analysis_modules["pattern_recognition"]
                # Get recent candles for pattern analysis
                from core.services.historical_data_service import get_global_historical_data_service
                historical_service = get_global_historical_data_service()
                candles = historical_service.get_5m_candles("BTC", 20)
                if candles:
                    return pattern_engine.analyze_patterns(candles)
                logger.warning("⚠️ No candle data available for pattern analysis")
                return {}
            else:
                logger.warning("⚠️ No pattern recognition module registered")
                return {}
        except Exception as e:
            logger.error(f"❌ Failed to get pattern analysis: {e}")
            return {}
    
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
                        "volatility_5m": self.get_volatility_analysis("standard").get("volatility_5m", 0.0),
                        "volatility_category": self.get_volatility_analysis("standard").get("volatility_5m_category", "MODERATE"),
                        "volume_category": self.get_volume_analysis().get("hyperliquid_5m", {}).get("volume_category", "MODERATE")
                    }
                    # Get 1d candles for market trend analysis - request more to ensure we have enough
                    from core.services.historical_data_service import get_global_historical_data_service
                    historical_service = get_global_historical_data_service()
                    candles_1d = historical_service.get_1d_candles("BTC", 30)  # Request 30 days to ensure we have at least 7
                    
                    return conditions_analyzer.analyze_trading_conditions(market_data, candles_1d=candles_1d)
                logger.warning("⚠️ No current price available for market conditions analysis")
                return {}
            else:
                logger.warning("⚠️ No market conditions module registered")
                return {}
        except Exception as e:
            logger.error(f"❌ Failed to get market conditions analysis: {e}")
            return {}
    
    def get_funding_analysis(self) -> Dict[str, Any]:
        """Get funding rate analysis data"""
        try:
            if "funding_rate" in self._analysis_modules:
                funding_analyzer = self._analysis_modules["funding_rate"]
                # Get funding rate data from API
                if self.hyperliquid_api:
                    funding_data = self.hyperliquid_api.get_funding_rate("BTC")
                    if funding_data:
                        return funding_analyzer.analyze_funding_rate(funding_data)
                logger.warning("⚠️ No funding rate data available")
                return {}
            else:
                logger.warning("⚠️ No funding rate module registered")
                return {}
        except Exception as e:
            logger.error(f"❌ Failed to get funding analysis: {e}")
            return {}
    
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
                    return analysis_result
                
                logger.warning("⚠️ No orderbook data available for analysis")
                return {}
            else:
                logger.warning("⚠️ No orderbook module registered")
                return {}
        except Exception as e:
            logger.error(f"❌ Failed to get orderbook analysis: {e}")
            return {}
    
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
            return [], []
    
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
                
                # Technical Analysis (Primary Components)
                "rsi": {
                    "value": market_data["rsi"]["rsi"],
                    "category": market_data["rsi"]["category"],
                    "signal": market_data["rsi"]["signal"],
                    "timestamp": market_data["rsi"]["timestamp"]
                },
                
                "trend": {
                    "direction": market_data["trend"]["direction"],
                    "strength": market_data["trend"]["strength"],
                    "timeframes": market_data["trend"]["timeframes"],
                    "consensus": market_data["trend"]["consensus"],
                    "timestamp": market_data["trend"]["timestamp"]
                },
                
                "volume": {
                    "hyperliquid_5m": market_data["volume"]["hyperliquid_5m"],
                    "binance_global": market_data["volume"]["binance_global"],
                    "total_volume_btc": market_data["volume"]["hyperliquid_5m"]["current_volume_btc"],
                    "volume_category": market_data["volume"]["hyperliquid_5m"]["volume_category"],
                    "timestamp": market_data["volume"]["timestamp"]
                },
                
                "volatility": {
                    "current": market_data["volatility"]["volatility_5m"],
                    "category": market_data["volatility"]["volatility_5m_category"],
                    "change_detection": market_data["volatility"]["change_detection"],
                    "multi_timeframe": {
                        "1m": market_data["volatility"]["volatility_1m"],
                        "5m": market_data["volatility"]["volatility_5m"],
                        "1h": market_data["volatility"]["volatility_1h"],
                        "1d": market_data["volatility"]["volatility_1d"]
                    },
                    "timestamp": market_data["volatility"]["timestamp"]
                },
                
                "pressure": {
                    "buy_pressure": market_data["pressure"]["buy_pressure"],
                    "sell_pressure": market_data["pressure"]["sell_pressure"],
                    "net_pressure": market_data["pressure"]["net_pressure"],
                    "pressure_ratio": market_data["pressure"]["pressure_ratio"],
                    "timestamp": market_data["pressure"]["timestamp"]
                },
                
                "support_resistance": {
                    "support_levels": market_data["support_resistance"]["support_levels"],
                    "resistance_levels": market_data["support_resistance"]["resistance_levels"],
                    "strongest_support": market_data["support_resistance"]["strongest_support"],
                    "strongest_resistance": market_data["support_resistance"]["strongest_resistance"],
                    "levels_count": market_data["support_resistance"]["levels_count"],
                    "timestamp": market_data["support_resistance"]["timestamp"]
                },
                
                "patterns": {
                    "active_patterns": market_data["patterns"]["active_patterns"],
                    "pattern_signals": market_data["patterns"]["pattern_signals"],
                    "confidence_scores": market_data["patterns"]["confidence_scores"],
                    "timestamp": market_data["patterns"]["timestamp"]
                },
                
                # Additional market context
                "market_conditions": market_data["market_conditions"],
                "funding_analysis": market_data["funding_analysis"],
                "orderbook_analysis": market_data["orderbook_analysis"],
                
                # Data quality indicators
                "data_quality": {
                    "all_components_available": all([
                        market_data.get("rsi"),
                        market_data.get("trend"),
                        market_data.get("volume"),
                        market_data.get("volatility"),
                        market_data.get("support_resistance")
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
    
    def get_prediction_data(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get optimized data package for prediction engine with clean metric mapping"""
        try:
            # Get unified analysis data
            analysis_data = self.get_unified_analysis_data(strategy)
            
            # Clean metric mapping for prediction engine
            prediction_data = {
                # Core data
                "current_price": analysis_data.get("current_price", 0),
                "timestamp": analysis_data.get("timestamp", time.time()),
                "strategy": strategy,
                
                # RSI - extract number and category
                "rsi": analysis_data.get("rsi", {}).get("rsi", 50),
                "rsi_category": analysis_data.get("rsi", {}).get("category", "NEUTRAL"),
                
                # Volume - extract category
                "volume_category": analysis_data.get("volume", {}).get("category", "MODERATE"),
                "volume_5m": analysis_data.get("volume", {}).get("volume_5m", 0),
                
                # Trend - extract direction and create trend_5m structure
                "trend": analysis_data.get("trend", {}).get("direction", "SIDEWAYS"),
                "trend_5m": {
                    "trend_short": analysis_data.get("trend", {}).get("timeframes", {}).get("short", "SIDEWAYS"),
                    "trend_medium": analysis_data.get("trend", {}).get("timeframes", {}).get("medium", "SIDEWAYS"),
                    "trend_long": analysis_data.get("trend", {}).get("timeframes", {}).get("long", "SIDEWAYS")
                },
                
                # Volatility - extract category
                "volatility_category": analysis_data.get("volatility", {}).get("category", "MODERATE"),
                "volatility_5m": analysis_data.get("volatility", {}).get("volatility_5m", 0),
                
                # Support/Resistance - pass full data
                "support_resistance": analysis_data.get("support_resistance", {}),
                
                # Pressure - pass full data
                "pressure_data": analysis_data.get("pressure", {}),
                
                # Pattern analysis - pass full data
                "pattern_analysis": analysis_data.get("patterns", {}),
                
                # Volume profile - pass full data
                "volume_profile_analysis": analysis_data.get("volume_profile", {}),
                
                # Funding analysis - pass full data
                "funding_analysis": analysis_data.get("funding_analysis", {}),
                
                # Cross-asset analysis - pass full data
                "cross_asset_analysis": analysis_data.get("cross_asset_analysis", {}),
                
                # Market conditions - pass full data
                "market_conditions_analysis": analysis_data.get("market_conditions", {}),
                
                # Orderbook analysis - pass full data
                "orderbook_analysis": analysis_data.get("orderbook_analysis", {}),
                
                # Raw data access for prediction engine
                "raw_data_access": {
                    "hyperliquid_api": self.hyperliquid_api,
                    "hyperliquid_websocket": self.hyperliquid_websocket,
                    "binance_api": self.binance_api
                }
            }
            
            logger.debug(f"📊 Prediction data prepared with {len(prediction_data)} metrics")
            return prediction_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get prediction data: {e}")
            return {}
    
    def get_dashboard_data(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get optimized data package for dashboard UI"""
        try:
            # Get unified analysis data
            analysis_data = self.get_unified_analysis_data(strategy)
            
            # Add dashboard-specific data
            dashboard_data = {
                **analysis_data,
                "dashboard_ready": True,
                "last_update": time.time()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data: {e}")
            return {}
    
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
            return {}
    
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
                    # Try to get status from module if it has a status method
                    if hasattr(module_instance, 'get_status'):
                        module_status[module_name] = module_instance.get_status()
                    else:
                        module_status[module_name] = {"status": "registered", "type": type(module_instance).__name__}
                except Exception as e:
                    module_status[module_name] = {"status": "error", "error": str(e)}
            
            return {
                "total_modules": len(self._analysis_modules),
                "module_status": module_status
            }
        except Exception as e:
            logger.error(f"❌ Failed to get analysis module status: {e}")
            return {}
    
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
                
                # Update price from WebSocket (real-time)
                if self.hyperliquid_websocket:
                    new_price = self.hyperliquid_websocket.get_current_price()
                    if new_price is not None:
                        self._current_price = new_price
                        self._price_timestamp = current_time
                        logger.debug(f"📊 Real-time price updated: ${self._current_price:.2f}")
                elif self.hyperliquid_api:
                    # Fallback to API if WebSocket not available
                    new_price = self.hyperliquid_api.get_current_price("BTC")
                    if new_price is not None:
                        self._current_price = new_price
                        self._price_timestamp = current_time
                        logger.debug(f"📊 Price updated from API: ${self._current_price:.2f}")
            
            return self._current_price
            
        except Exception as e:
            logger.error(f"❌ Failed to get current price: {e}")
            raise Exception(f"Current price unavailable - NO FALLBACKS: {e}")
    
    def update_current_price(self) -> Optional[float]:
        """Force update current price from WebSocket (for real-time streaming)"""
        try:
            if self.hyperliquid_websocket:
                new_price = self.hyperliquid_websocket.get_current_price()
                if new_price is not None:
                    self._current_price = new_price
                    self._price_timestamp = time.time()
                    return new_price
            return self._current_price
        except Exception as e:
            logger.error(f"❌ Failed to update current price: {e}")
            return self._current_price
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get market data from API"""
        try:
            if self.hyperliquid_api:
                return self.hyperliquid_api.get_market_data("BTC")
            return {}
        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            return {}
    
# Global instance
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
    logger.info("📊 Global MarketDataService instance set")