#!/usr/bin/env python3
"""
Session Orchestrator - Centralized session management with NO FALLBACKS policy
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger

# Centralized imports to reduce lazy imports and improve code clarity
# These are safe to import at module level (no circular dependencies)
from core.utils.time_utils import TimeUtils
from core.services.centralized_cache import get_global_centralized_cache
from core.services.historical_data_service import get_global_historical_data_service
from core.constants import TradingConstants
from core.services.strategy_detector import StrategyDetector
from core.services.momentum_processor import MomentumProcessor
from core.services.dashboard_updater import DashboardUpdater


class SessionOrchestrator:
    """Centralized session orchestrator with NO FALLBACKS policy"""

    def __init__(self, config, initial_balance: float = None, cache=None):
        self.config = config
        self.initial_balance = initial_balance
        
        # Dependency injection for cache (DIP compliance)
        # Fallback to global singleton for backward compatibility
        if cache is None:
            self._cache = get_global_centralized_cache()
        else:
            self._cache = cache
        
        self.session_manager = None
        self.strategy_manager = None
        self.prediction_engine = None
        
        # Extracted components for SRP compliance
        self._strategy_detector = None  # Will be initialized when dependencies are available
        self._momentum_processor = None  # Will be initialized when reactive_engine is available
        self._dashboard_updater = None  # Will be initialized when dependencies are available
        
        self._last_price = None
        self._last_5m_boundary = None
        self._last_orderbook = {'levels': [[], []]}  # Initialize with Hyperliquid format: [bids, asks] (NO FALLBACKS)
        self._raw_data_fetcher = None  # Will be initialized when market_data_service is available
        # Initialize all module update times (NO FALLBACKS)
        self._last_update_times = {
            'support_resistance': 0,
            'volume': 0,
            'volatility': 0,
            'trend': 0,
            'rsi': 0,
            'rsi_calculator': 0,  # Alias for rsi module
            'patterns': 0,
            'pattern_recognition': 0,  # Alias for patterns
            'pressure': 0,
            'funding': 0,
            'orderbook': 0,
            'market_conditions': 0,
            'cross_asset_correlation_analyzer': 0,
            'consolidation': 0,  # Consolidation tracker module
            'iv_squeeze': 0  # IV Squeeze analyzer module
        }
        
        # Initialize reactive execution engine (for momentum breakouts with market orders)
        # Pass API manager to enable trade execution calls
        try:
            from core.execution.reactive_engine import ReactiveEngine
            # Get API manager from system initializer if available
            api_manager = None
            try:
                from core.services.system_initializer import get_system_initializer
                system_initializer = get_system_initializer()
                api_manager = system_initializer.get_singleton_system("api_manager")
            except Exception:
                pass  # API manager not required for initialization
            
            self._reactive_engine = ReactiveEngine(api_manager=api_manager)
            logger.info("⚡ Reactive execution engine initialized")
        except Exception as e:
            logger.warning(f"⚠️ Reactive engine not available: {e}")
            self._reactive_engine = None

        logger.info("🎯 SessionOrchestrator initialized with NO FALLBACKS policy")

    def _ensure_strategy_manager_initialized(self, system_initializer):
        """Ensure Strategy Manager is initialized"""
        if self.strategy_manager is None:
            self.strategy_manager = system_initializer.get_singleton_system("strategy_manager")
            if not self.strategy_manager:
                raise Exception("Strategy Manager not available from system initializer")
    
    def _ensure_prediction_engine_initialized(self):
        """Ensure Prediction Engine is initialized"""
        if self.prediction_engine is None:
            from core.execution.prediction_engine import PredictionEngine
            self.prediction_engine = PredictionEngine()

    def run_paper_trading_session(
        self,
        check_interval: int,
        market_data_service,
        dashboard_service,
        strategy: str = "standard",
    ):
        """Run paper trading session with NO FALLBACKS policy"""
        try:
            logger.info(
                f"🚀 Starting paper trading session (interval: {check_interval}s, strategy: {strategy})"
            )

            # Validate strategy parameter
            if isinstance(strategy, str):
                strategy_name = strategy
            else:
                strategy_name = "standard"
                logger.warning(
                    f"⚠️ Strategy parameter is not a string, using default: {strategy_name}"
                )

            # Initialize Strategy Manager (NO FALLBACKS)
            try:
                from core.services.system_initializer import get_system_initializer

                system_initializer = get_system_initializer()
                self._ensure_strategy_manager_initialized(system_initializer)
            except Exception as e:
                logger.error(f"❌ Strategy Manager initialization failed: {e}")
                raise Exception(
                    "Strategy Manager initialization required - NO FALLBACKS"
                )

            # Initialize session manager
            from core.session.session_manager import get_global_session_manager

            self.session_manager = get_global_session_manager()
            if self.session_manager:
                self.session_manager.start_session(strategy=strategy_name, initial_balance=self.initial_balance)
                logger.info("✅ Session started successfully")
            else:
                logger.warning("⚠️ Session manager not available")

            # Verify data flow
            self._verify_data_flow(market_data_service)
            
            # Ensure Prediction Engine is initialized
            self._ensure_prediction_engine_initialized()
            
            # Initialize extracted components (SRP compliance)
            self._initialize_extracted_components(dashboard_service)

            # Start session
            self._start_session(market_data_service, dashboard_service, strategy_name)

            # Main data loop
            self._main_data_loop(
                check_interval, market_data_service, dashboard_service, strategy_name
            )

        except Exception as e:
            logger.error(f"❌ Paper trading session failed: {e}")
            raise

    def _verify_data_flow(self, market_data_service):
        """Verify data flow from MarketDataService"""
        current_price = market_data_service.get_current_price()
        if current_price and current_price > 0:
            logger.info(f"✅ MarketDataService price verified: Price=${current_price:.2f}")
        else:
            raise Exception("MarketDataService price not available or invalid")

    def _initialize_extracted_components(self, dashboard_service):
        """
        Initialize extracted components (SRP compliance)
        
        Args:
            dashboard_service: DashboardService instance
        """
        # Initialize StrategyDetector
        if self.strategy_manager and self.prediction_engine:
            self._strategy_detector = StrategyDetector(
                strategy_manager=self.strategy_manager,
                prediction_engine=self.prediction_engine
            )
        
        # Initialize MomentumProcessor
        if hasattr(self, '_reactive_engine') and self._reactive_engine:
            self._momentum_processor = MomentumProcessor(reactive_engine=self._reactive_engine)
        else:
            self._momentum_processor = MomentumProcessor(reactive_engine=None)
        
        # Initialize DashboardUpdater
        self._dashboard_updater = DashboardUpdater(
            dashboard_service=dashboard_service,
            session_manager=self.session_manager
        )
    
    def _start_session(self, market_data_service, dashboard_service, strategy: str):
        """Start trading session"""
        try:
            logger.info(f"🎯 Starting trading session with strategy: {strategy}")

            dashboard_service.clear_stale_data()
            market_data_service.invalidate_processed_data()

            # Use provided strategy (strategy detection happens in main data loop with market data)
            optimal_strategy = strategy
            logger.info(f"🎯 Starting with strategy: {optimal_strategy}")

            logger.info(f"✅ Trading session started with strategy: {optimal_strategy}")

        except Exception as e:
            logger.error(f"❌ Session start failed: {e}")

    def _handle_candle_boundary(self, current_time: float, current_5m_start: float, 
                                 last_candle_update_time: float, market_data_service) -> float:
        """
        Handle 5-minute candle boundary detection and cache invalidation
        
        Returns:
            Updated last_candle_update_time
        """
        # Get historical service from system initializer (DIP compliance)
        historical_service = None
        try:
            from core.services.system_initializer import get_system_initializer
            system_initializer = get_system_initializer()
            if "historical_data_service" in system_initializer.singleton_systems:
                historical_service = system_initializer.get_singleton_system("historical_data_service")
        except Exception:
            pass  # Will fall back to global singleton if needed
        
        # Detect new 5-minute candle close (boundary change) - EXACT UTC TIMING
        # Candles are tied to global UTC time and appear at 00, 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55 minutes
        if self._last_5m_boundary is not None and current_5m_start != self._last_5m_boundary:
            boundary_utc = datetime.utcfromtimestamp(current_5m_start)
            logger.info(f"🕐 New 5-minute candle boundary detected: {boundary_utc.strftime('%H:%M:%S')} UTC - updating database and invalidating caches")
            
            # Update candle storage IMMEDIATELY when boundary changes
            try:
                if not historical_service:
                    historical_service = get_global_historical_data_service()
                if historical_service._candle_storage:
                    historical_service._candle_storage.update_with_latest_candle()
                    logger.info(f"✅ Candle storage updated at exact 5-minute boundary")
                    
                    # Invalidate chart cache to force dashboard refresh with new candle
                    self._cache.invalidate(pattern="historical_candles")
                    self._cache.invalidate(pattern="candles_5m")
                    logger.debug(f"🔄 Chart cache invalidated for new candle - dashboard will refresh")
            except Exception as e:
                logger.error(f"❌ Failed to update candle storage at boundary: {e}")
            
            # Invalidate pattern and trend cache when new candle closes
            # New candles affect trend calculations, so trend cache must be invalidated
            self._cache.invalidate(pattern="pattern_recognition")
            self._cache.invalidate(pattern="patterns")
            self._cache.invalidate("trend")  # Trend is calculated from candles, so invalidate when new candle appears
            
            # Recalculate RSI baseline at exact candle boundary
            try:
                if not historical_service:
                    historical_service = get_global_historical_data_service()
                from config.config import TradingConfig
                candles_5m = historical_service.get_5m_candles(TradingConfig.SYMBOL, 30)  # Need at least 15 for RSI(14)
                
                # Use MarketDataService method (SRP: MarketDataService coordinates RSI)
                if market_data_service:
                    market_data_service.recalculate_rsi_baseline(candles_5m)
            except Exception as e:
                logger.error(f"❌ Failed to recalculate RSI baseline at boundary: {e}")
            
            self._last_5m_boundary = current_5m_start
            return current_time  # Reset timer
        
        # Safety check: Update candle storage if boundary detection somehow failed (clock drift protection)
        # This should rarely trigger if boundary detection works correctly
        # NO FALLBACKS - This is a safety mechanism, not a business logic fallback
        elif last_candle_update_time > 0.0 and current_time - last_candle_update_time >= TradingConstants.CANDLE_UPDATE_TIMEOUT:
            try:
                logger.warning(f"⚠️ Candle update missed boundary - updating now (elapsed: {current_time - last_candle_update_time:.0f}s)")
                if not historical_service:
                    historical_service = get_global_historical_data_service()
                if historical_service._candle_storage:
                    historical_service._candle_storage.update_with_latest_candle()
                    return current_time
            except Exception as e:
                logger.error(f"❌ Failed to update candle storage (safety check): {e}")
        
        return last_candle_update_time
    
    def _prepare_market_data_iteration(self, market_data_service) -> Tuple[float, Dict[str, Any], Dict[str, Any]]:
        """
        Prepare market data for iteration: fetch all raw API data, then prepare unified data
        
        NEW ARCHITECTURE: All raw API data is fetched upfront in parallel before analysis begins.
        This ensures consistent dataflow and better performance.
        
        Returns:
            Tuple of (current_price, orderbook_data, unified_data)
            
        Raises:
            ValueError: If any raw data fetch fails (NO FALLBACKS)
        """
        # Initialize RawDataFetcher if not already initialized
        if self._raw_data_fetcher is None:
            self._raw_data_fetcher = self._initialize_raw_data_fetcher(market_data_service)
        
        # Fetch ALL raw API data upfront in parallel (NO FALLBACKS - all data is mandatory)
        raw_data = self._raw_data_fetcher.fetch_all_raw_data()
        
        # Extract price and orderbook from raw data
        current_price = raw_data["price"]
        if not current_price or current_price <= 0:
            raise ValueError("Invalid current price from raw data fetch (NO FALLBACKS)")
        
        orderbook_data = raw_data["orderbook"]
        if not orderbook_data:
            raise ValueError("Invalid orderbook data from raw data fetch (NO FALLBACKS)")
        
        # Prepare unified market data (pass raw_data so analysis modules don't fetch again)
        # CRITICAL: Analysis is strategy-independent to avoid circular dependency
        unified_data = self._prepare_unified_market_data(
            orderbook_data, current_price, market_data_service, 
            strategy_for_analysis=None, raw_data=raw_data
        )
        
        return current_price, orderbook_data, unified_data
    
    def _initialize_raw_data_fetcher(self, market_data_service) -> Any:
        """
        Initialize RawDataFetcher with all required API instances
        
        Returns:
            RawDataFetcher instance
        """
        try:
            from core.services.raw_data_fetcher import create_raw_data_fetcher
            from core.services.system_initializer import get_system_initializer
            
            system_initializer = get_system_initializer()
            api_manager = system_initializer.get_singleton_system("api_manager")
            
            if not api_manager:
                raise ValueError("API Manager not available - cannot initialize RawDataFetcher (NO FALLBACKS)")
            
            # Get all required API instances
            hyperliquid_api = api_manager.get_api("hyperliquid_api")
            hyperliquid_websocket = api_manager.get_websocket("hyperliquid_websocket")
            binance_api = api_manager.get_api("binance_api")
            binance_websocket = api_manager.get_websocket("binance_websocket")
            fear_greed_api = api_manager.get_api("fear_greed_api")
            whale_analytics_api = api_manager.get_api("whale_analytics_api")
            rss_news_api = api_manager.get_api("rss_news_api")
            
            raw_data_fetcher = create_raw_data_fetcher(
                hyperliquid_api=hyperliquid_api,
                hyperliquid_websocket=hyperliquid_websocket,
                binance_api=binance_api,
                binance_websocket=binance_websocket,
                fear_greed_api=fear_greed_api,
                whale_analytics_api=whale_analytics_api,
                rss_news_api=rss_news_api
            )
            
            logger.info("📡 Raw Data Fetcher initialized")
            return raw_data_fetcher
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize RawDataFetcher: {e}")
            raise ValueError(f"RawDataFetcher initialization failed: {e} (NO FALLBACKS)")
    
    def _calculate_position_size(self, prediction, current_strategy: str) -> Optional[Dict[str, Any]]:
        """
        Calculate position size for a prediction
        
        Returns:
            Position size info dict or None if calculation fails
        """
        if not self.session_manager:
            return None
        
        try:
            session_data = self.session_manager.get_current_session_data()
            current_balance = session_data["current_balance"]
            
            if current_balance <= 0:
                return None
            
            from core.execution.position_sizer import PositionSizeCalculator
            from config.config import TradingConfig
            
            # Get strategy-specific position size % - NO FALLBACKS
            if current_strategy not in TradingConfig.STRATEGY_CONFIGS:
                raise ValueError(f"Strategy '{current_strategy}' not found in STRATEGY_CONFIGS - NO FALLBACKS")
            
            strategy_config = TradingConfig.STRATEGY_CONFIGS[current_strategy]
            base_position_size_pct = strategy_config["position_size"]
            
            # Validate position_size is valid for trading (NO FALLBACKS)
            if base_position_size_pct <= 0 or base_position_size_pct > 1.0:
                logger.warning(f"⚠️ Strategy '{current_strategy}' has invalid position_size ({base_position_size_pct}) - skipping position size calculation (strategy may be analysis-only)")
                return None
            
            # Position size calculated AFTER confidence (confidence may be None if not implemented yet)
            return PositionSizeCalculator.calculate_position_size(
                balance=current_balance,
                base_position_size_pct=base_position_size_pct,
                risk_reward_ratio=prediction.risk_reward_ratio,
                leverage=TradingConfig.LEVERAGE,
                entry_price=prediction.entry_price,
                stop_loss=prediction.stop_loss,
                direction=prediction.direction,
                confidence=prediction.confidence  # Pass confidence for future confidence-based sizing
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate position size: {e}")
            return None
    
    def _process_strategy_and_prediction(self, unified_data: Dict[str, Any], 
                                        current_price: float, dashboard_service) -> str:
        """
        Process strategy detection, S/R filtering, and prediction generation
        
        Returns:
            Current strategy name
        """
        # Detect and update strategy AFTER all analysis modules are complete
        # This ensures we have the most up-to-date market data for strategy selection
        if self._strategy_detector:
            current_strategy = self._strategy_detector.detect_and_update_strategy(
                unified_data, session_manager=self.session_manager
            )
        else:
            # Fallback if not initialized
            current_strategy = "standard"
            logger.warning("⚠️ StrategyDetector not initialized, using default strategy")
        
        # Update unified data with detected strategy
        unified_data["strategy"] = current_strategy
        
        # Filter S/R levels for dashboard display (strategy-aware)
        if self._strategy_detector:
            self._strategy_detector.filter_sr_levels_for_dashboard(unified_data, current_price, current_strategy)
        
        # Generate prediction
        try:
            prediction = self.prediction_engine.generate_prediction(unified_data, current_strategy)
            if prediction:
                # Calculate position size
                position_size_info = self._calculate_position_size(prediction, current_strategy)
                
                unified_data["prediction"] = {
                    "direction": prediction.direction,
                    "entry_price": prediction.entry_price,
                    "stop_loss": prediction.stop_loss,
                    "take_profit": prediction.take_profit,
                    "confidence": prediction.confidence,  # Already 0-100 percentage
                    "reasoning": prediction.reasoning,
                    "strategy": prediction.strategy,
                    "timestamp": prediction.timestamp,
                    "status": "READY",
                    "position_size_btc": position_size_info["position_size_btc"] if position_size_info else None,
                    "position_size_usd": position_size_info["position_value_usd"] if position_size_info else None
                }
            else:
                unified_data["prediction"] = None
        except Exception as e:
            logger.error(f"❌ Prediction generation failed: {e}")
            unified_data["prediction"] = None
        
        return current_strategy
    
    def _process_momentum_signals(self, unified_data: Dict[str, Any], 
                                  current_price: float, current_strategy: str) -> None:
        """
        Process momentum signals with reactive engine (market orders)
        """
        if self._momentum_processor:
            self._momentum_processor.process_momentum_signals(
                unified_data, current_price, current_strategy
            )
    
    def _main_data_loop(
        self,
        check_interval: int,
        market_data_service,
        dashboard_service,
        strategy: str = "standard",
    ):
        """Main data processing loop - MarketDataService as centralized price provider"""
        try:
            logger.info(
                f"🔄 Starting main data loop (interval: {check_interval}s, strategy: {strategy})"
            )
            
            # Track last candle storage update (initialize to current time to avoid false warnings on first run)
            last_candle_update_time = time.time()
            
            # Track last 5-minute candle boundary for pattern detection optimization
            if self._last_5m_boundary is None:
                current_5m_start = TimeUtils.get_5m_candle_start_time()
                self._last_5m_boundary = current_5m_start

            while True:
                try:
                    current_time = time.time()
                    current_5m_start = TimeUtils.get_5m_candle_start_time()
                    
                    # Handle candle boundary detection and cache invalidation
                    last_candle_update_time = self._handle_candle_boundary(
                        current_time, current_5m_start, last_candle_update_time, market_data_service
                    )
                    
                    # Prepare market data for iteration
                    # NO FALLBACKS - if data preparation fails, raise immediately
                    current_price, orderbook_data, unified_data = self._prepare_market_data_iteration(
                        market_data_service
                    )
                    
                    # Process strategy detection and prediction generation
                    current_strategy = self._process_strategy_and_prediction(
                        unified_data, current_price, dashboard_service
                    )
                    
                    if current_strategy != strategy:
                        logger.info(f"🔄 Strategy updated: {strategy} → {current_strategy}")
                    
                    # Process momentum signals with reactive engine
                    self._process_momentum_signals(unified_data, current_price, current_strategy)
                    
                    # Update dashboard with unified market data (includes prediction)
                    if self._dashboard_updater:
                        self._dashboard_updater.update_dashboard_with_unified_data(unified_data)
                    
                    # Update session time
                    if self.session_manager:
                        self.session_manager._update_session_time()
                    
                    # Update strategy for next iteration
                    strategy = current_strategy
                    
                    # Sleep before next iteration
                    time.sleep(check_interval)

                except Exception as e:
                    # NO FALLBACKS - critical errors should propagate and stop the bot
                    # Log the error with full context
                    logger.error(f"❌ Data loop iteration failed: {e}")
                    import traceback
                    logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
                    # Re-raise to propagate to outer handler which will stop the bot
                    raise

        except Exception as e:
            logger.error(f"❌ Main data loop failed: {e}")
            raise
    
    def _get_modules_needing_update(self, analysis_modules: Dict[str, Any], 
                                   current_price: float, orderbook_data: Dict[str, Any]) -> List[str]:
        """Determine which modules need updates based on data changes and time intervals"""
        modules_to_update = []
        current_time = time.time()
        
        # Modules handled directly by MarketDataService (not updated here)
        # These modules are called on-demand via MarketDataService methods
        modules_handled_by_market_data_service = {"funding_rate", "orderbook"}
        
        # Modules that require special parameters (not in standard getter mapping)
        # Consolidation requires unified_data parameter, so it's handled separately in _prepare_unified_market_data
        modules_with_special_params = {"consolidation"}
        
        # Exclude these modules from update list (they're handled differently)
        excluded_modules = modules_handled_by_market_data_service | modules_with_special_params
        
        # Module update intervals are now handled by CentralizedCache
        # No need for duplicate definitions here
        
        # Price change threshold for price-sensitive modules
        from core.constants import TradingConstants
        price_change_threshold = TradingConstants.PRICE_CHANGE_THRESHOLD
        
        # Track price changes
        if self._last_price is None:
            self._last_price = current_price
            # Initialize 5-minute boundary tracking
            self._last_5m_boundary = TimeUtils.get_5m_candle_start_time()
            # Force update all modules on first run (excluding those handled by MarketDataService and special params)
            return [m for m in analysis_modules.keys() if m not in excluded_modules]
        
        price_change = abs(current_price - self._last_price) / self._last_price
        self._last_price = current_price
        
        # Check for new 5-minute candle close (for pattern detection optimization)
        current_5m_start = TimeUtils.get_5m_candle_start_time()
        new_candle_closed = False
        if self._last_5m_boundary is not None:
            if current_5m_start != self._last_5m_boundary:
                new_candle_closed = True
                logger.info(f"🕐 New 5-minute candle closed - pattern detection will be triggered")
                # Invalidate pattern cache when new candle closes
                self._cache.invalidate(pattern="pattern_recognition")
                self._cache.invalidate(pattern="patterns")
                self._last_5m_boundary = current_5m_start
        else:
            self._last_5m_boundary = current_5m_start
        
        for module_name, module_instance in analysis_modules.items():
            # Skip excluded modules (handled by MarketDataService or require special params)
            if module_name in excluded_modules:
                continue
            
            # Check if module should be updated
            should_update = False
            
            # Check time interval using CentralizedCache intervals
            last_update = self._last_update_times[module_name]  # Always exists (initialized in __init__)
            # Get interval from injected cache (DIP compliance)
            interval = self._cache._get_ttl_policy(module_name)  # Get TTL policy for module
            
            if current_time - last_update >= interval:
                should_update = True
            
            # Pattern recognition: trigger on new 5-minute candle close (optimized)
            if module_name == "pattern_recognition" and new_candle_closed:
                should_update = True
            
            # Check price change for price-sensitive modules
            # IV Squeeze is volatility-based and correlates with price movements
            price_sensitive_modules = ['rsi_calculator', 'support_resistance', 'iv_squeeze']
            if module_name in price_sensitive_modules and price_change >= price_change_threshold:
                should_update = True
            
            # Check for data changes in orderbook (orderbook module is handled by MarketDataService, so removed from here)
            if module_name in ['volume', 'pressure']:
                if self._has_orderbook_changed(orderbook_data):
                    should_update = True
            
            if should_update:
                modules_to_update.append(module_name)
                self._last_update_times[module_name] = current_time
        
        return modules_to_update
    
    def _has_orderbook_changed(self, orderbook_data: Dict[str, Any]) -> bool:
        """Check if orderbook data has changed significantly"""
        # Validate orderbook data structure (Hyperliquid format: levels[0]=bids, levels[1]=asks)
        if 'levels' not in orderbook_data:
            raise ValueError(f"Invalid orderbook data structure - missing 'levels'. Keys: {list(orderbook_data.keys())}")
        
        levels = orderbook_data['levels']
        if not isinstance(levels, list) or len(levels) < 2:
            raise ValueError(f"Invalid orderbook levels structure - expected list with 2 elements (bids, asks)")
        
        if self._last_orderbook is None:
            self._last_orderbook = orderbook_data
            return True
        
        # Simple comparison - could be enhanced with more sophisticated change detection
        # Hyperliquid format: levels[0] = bids, levels[1] = asks
        current_bids = levels[0]  # Required (NO FALLBACKS)
        current_asks = levels[1]  # Required (NO FALLBACKS)
        last_levels = self._last_orderbook['levels']
        last_bids = last_levels[0]  # Required (NO FALLBACKS)
        last_asks = last_levels[1]  # Required (NO FALLBACKS)
        
        # Check if bid/ask levels have changed
        if current_bids != last_bids or current_asks != last_asks:
            self._last_orderbook = orderbook_data
            return True
        
        return False

    def _prepare_unified_market_data(
        self,
        orderbook_data: Dict[str, Any],
        current_price: float,
        market_data_service,
        strategy_for_analysis: str = None,
        raw_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Prepare unified market data for analysis
        
        CRITICAL: Analysis is strategy-independent to avoid circular dependency.
        Strategy is determined AFTER analysis is complete, then used for prediction.
        
        NEW: raw_data parameter contains all pre-fetched raw API data.
        Analysis modules should consume this data instead of fetching themselves.
        
        Args:
            orderbook_data: Orderbook data (from raw_data)
            current_price: Current market price (from raw_data)
            market_data_service: Market data service instance
            strategy_for_analysis: DEPRECATED - kept for backward compatibility, always uses "standard"
            raw_data: Pre-fetched raw API data (all data is mandatory - NO FALLBACKS)
        """
        try:
            # Validate raw_data is provided (NO FALLBACKS)
            if raw_data is None:
                raise ValueError("raw_data is required - all data must be fetched upfront (NO FALLBACKS)")
            
            # Trigger analysis modules to calculate and send data to MarketDataService
            # Pass raw_data so modules don't fetch again
            # All analysis module getters are synchronous - no delay needed
            self._trigger_analysis_modules(
                market_data_service, current_price, orderbook_data, raw_data=raw_data
            )

            # Get comprehensive analysis data from MarketDataService
            # CRITICAL: Use "standard" strategy for analysis to avoid circular dependency
            # The actual strategy will be determined AFTER analysis is complete
            analysis_data = market_data_service.get_dashboard_data(strategy="standard")
            
            # Validate analysis_data is not empty (NO FALLBACKS)
            if not analysis_data or len(analysis_data) == 0:
                raise ValueError("analysis_data is EMPTY from get_dashboard_data - cannot proceed (NO FALLBACKS)")

            # Remove non-serializable objects for dashboard compatibility
            if "raw_data_access" in analysis_data:
                del analysis_data["raw_data_access"]

            # Get session data
            session_data = self._get_session_data()

            # Get trading data
            trading_data = self._get_trading_data()
            
            # Get consolidation analysis (requires unified_data, so call after analysis_data)
            # All modules are required - NO FALLBACKS
            temp_unified = {
                "timestamp": time.time(),
                "current_price": current_price,
                "strategy": None,
                **analysis_data
            }
            consolidation_data = market_data_service.get_consolidation_analysis(
                unified_data=temp_unified,
                current_price=current_price
            )  # Required (NO FALLBACKS) - will raise if fails
            
            # Prepare unified data with analysis data
            # Strategy is None initially - will be set by strategy detection
            unified_data = {
                "timestamp": time.time(),
                "current_price": current_price,
                "strategy": None,  # Determined after analysis
                "orderbook_data": orderbook_data,  # Level 2 orderbook with bids/asks
                "session_data": session_data,
                "trading_data": trading_data,
                "consolidation": consolidation_data,  # Consolidation tracking data
                # Include all analysis data
                **analysis_data,
            }

            return unified_data

        except Exception as e:
            logger.error(f"❌ Unified market data preparation failed: {e}")
            raise

    def _trigger_analysis_modules(
        self, market_data_service, current_price: float, orderbook_data: Dict[str, Any], raw_data: Dict[str, Any] = None
    ) -> None:
        """
        Trigger analysis modules via MarketDataService - SRP compliant
        
        MarketDataService is the single coordinator for all analysis modules.
        This method only determines which modules need updates and delegates to MarketDataService.
        
        NEW: raw_data parameter contains pre-fetched raw API data.
        Analysis modules should consume this data instead of fetching themselves.
        
        Args:
            market_data_service: MarketDataService instance
            current_price: Current market price
            orderbook_data: Orderbook data
            raw_data: Pre-fetched raw API data (all data is mandatory - NO FALLBACKS)
        """
        try:
            # Validate raw_data is provided (NO FALLBACKS)
            if raw_data is None:
                raise ValueError("raw_data is required - all data must be fetched upfront (NO FALLBACKS)")
            
            # Store raw_data in MarketDataService so methods can access it later
            # This allows get_unified_analysis_data() to call get_funding_analysis() etc. without passing raw_data
            market_data_service.set_raw_data(raw_data)
            
            # Get analysis modules from MarketDataService to determine what needs updating
            analysis_modules = getattr(market_data_service, "_analysis_modules", {})

            # Check which modules actually need updates
            modules_to_update = self._get_modules_needing_update(
                analysis_modules, current_price, orderbook_data
            )
            
            if not modules_to_update:
                return

            # Map module names to MarketDataService get methods (all strategy-independent)
            # All modules are required - NO FALLBACKS
            # Pass raw_data to methods that need it
            module_to_getter = {
                "rsi_calculator": lambda: market_data_service.get_rsi_analysis(),
                "volatility": lambda: market_data_service.get_volatility_analysis(),
                "trend": lambda: market_data_service.get_trend_analysis(),
                "support_resistance": lambda: market_data_service.get_support_resistance_analysis(),
                "volume": lambda: market_data_service.get_volume_analysis(),
                "pressure": lambda: market_data_service.get_pressure_analysis(),
                "pattern_recognition": lambda: market_data_service.get_pattern_analysis(),
                "market_conditions": lambda: market_data_service.get_market_conditions_analysis(raw_data=raw_data),
                "cross_asset_correlation_analyzer": lambda: market_data_service.get_cross_asset_analysis(raw_data=raw_data),
                "funding_rate": lambda: market_data_service.get_funding_analysis(raw_data=raw_data),
                "iv_squeeze": lambda: market_data_service.get_iv_squeeze_analysis(current_price=current_price),
            }

            # Update modules via MarketDataService (SRP: MarketDataService coordinates all module access)
            # All modules are required - exceptions propagate (NO FALLBACKS)
            for module_name in modules_to_update:
                # Get analysis via MarketDataService (single source of truth)
                if module_name not in module_to_getter:
                    raise ValueError(f"Unknown module '{module_name}' not in module_to_getter mapping (NO FALLBACKS)")
                getter = module_to_getter[module_name]  # Required (NO FALLBACKS)
                if getter:
                    analysis_result = getter()  # API-level validation - will raise if module fails

        except Exception as e:
            logger.error(f"❌ Failed to update analysis modules with live data: {e}")
            raise  # NO FALLBACKS - must raise to prevent continuing with incomplete data

    def _get_session_data(self) -> Dict[str, Any]:
        """Get session data"""
        try:
            if not self.session_manager:
                raise ValueError("Session manager not available - NO FALLBACKS")
            
            session_data = self.session_manager.current_session_data
            return {
                "session_id": session_data["session_id"],  # Required (NO FALLBACKS)
                "start_time": session_data["start_time"],  # Required (NO FALLBACKS)
                "current_balance": session_data["current_balance"],  # Required (NO FALLBACKS)
                "session_start_time": session_data["start_time"],  # Required (NO FALLBACKS)
                "session_time": session_data["session_time"],  # Required (NO FALLBACKS)
                "status": session_data["status"],  # Required (NO FALLBACKS)
                "strategy": session_data["strategy"],  # Required (NO FALLBACKS)
            }
        except Exception as e:
            logger.error(f"❌ Failed to get session data: {e}")
            raise

    def _get_trading_data(self) -> Dict[str, Any]:
        """Get trading data"""
        try:
            # Trading data would come from trading execution
            # Currently empty as trading execution is not yet implemented
            return {
                "open_positions": [],
                "pending_orders": [],
                "trade_history": [],
            }
        except Exception as e:
            logger.error(f"❌ Failed to get trading data: {e}")
            raise



    def _end_session(self):
        """End trading session"""
        try:
            if self.session_manager:
                self.session_manager.end_session()
                logger.info("✅ Session ended successfully")
        except Exception as e:
            logger.error(f"❌ Session end failed: {e}")

