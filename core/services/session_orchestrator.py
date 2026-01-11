#!/usr/bin/env python3
"""
Session Orchestrator - Centralized session management with NO FALLBACKS policy
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger

# Centralized imports to reduce lazy imports and improve code clarity
# These are safe to import at module level (no circular dependencies)
from core.utils.time_utils import TimeUtils
from core.services.centralized_cache import get_global_centralized_cache
from core.services.historical_data_service import get_global_historical_data_service


class SessionOrchestrator:
    """Centralized session orchestrator with NO FALLBACKS policy"""

    def __init__(self, config, initial_balance: float = None):
        self.config = config
        self.initial_balance = initial_balance
        self.session_manager = None
        self.strategy_manager = None
        self.prediction_engine = None
        self._last_price = None
        self._last_5m_boundary = None
        self._last_orderbook = None
        self._last_update_times = {}

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
            
            # Track last training check (check every hour)
            last_training_check_time = time.time()
            training_check_interval = 3600  # 1 hour
            
            # Track last 5-minute candle boundary for pattern detection optimization
            if self._last_5m_boundary is None:
                current_5m_start = TimeUtils.get_5m_candle_start_time()
                self._last_5m_boundary = current_5m_start

            while True:
                try:
                    current_time = time.time()
                    current_5m_start = TimeUtils.get_5m_candle_start_time()
                    
                    # Detect new 5-minute candle close (boundary change) - EXACT UTC TIMING
                    # Candles are tied to global UTC time and appear at 00, 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55 minutes
                    new_candle_closed = False
                    if self._last_5m_boundary is not None and current_5m_start != self._last_5m_boundary:
                        new_candle_closed = True
                        boundary_utc = datetime.utcfromtimestamp(current_5m_start)
                        logger.info(f"🕐 New 5-minute candle boundary detected: {boundary_utc.strftime('%H:%M:%S')} UTC - updating database and invalidating caches")
                        
                        # Update candle storage IMMEDIATELY when boundary changes (exact 5-minute intervals: 00, 05, 10, 15, etc.)
                        try:
                            historical_service = get_global_historical_data_service()
                            if historical_service._candle_storage:
                                historical_service._candle_storage.update_with_latest_candle()
                                logger.info(f"✅ Candle storage updated at exact 5-minute boundary")
                                
                                # Invalidate chart cache to force dashboard refresh with new candle
                                cache = get_global_centralized_cache()
                                cache.invalidate(pattern="historical_candles")
                                cache.invalidate(pattern="candles_5m")
                                logger.debug(f"🔄 Chart cache invalidated for new candle - dashboard will refresh")
                        except Exception as e:
                            logger.error(f"❌ Failed to update candle storage at boundary: {e}")
                        
                        # Invalidate pattern cache when new candle closes
                        cache = get_global_centralized_cache()
                        cache.invalidate(pattern="pattern_recognition")
                        cache.invalidate(pattern="patterns")
                        
                        # Recalculate RSI baseline at exact candle boundary (same time as candles reset)
                        try:
                            # Fetch fresh 5m candles for RSI baseline recalculation
                            historical_service = get_global_historical_data_service()
                            candles_5m = historical_service.get_5m_candles("BTC", 30)  # Need at least 15 for RSI(14)
                            
                            # Use MarketDataService method (SRP: MarketDataService coordinates RSI)
                            if market_data_service:
                                market_data_service.recalculate_rsi_baseline(candles_5m)
                        except Exception as e:
                            logger.error(f"❌ Failed to recalculate RSI baseline at boundary: {e}")
                        
                        self._last_5m_boundary = current_5m_start
                        last_candle_update_time = current_time  # Reset timer
                    
                    # Safety check: Update candle storage if boundary detection somehow failed (clock drift protection)
                    # This should rarely trigger if boundary detection works correctly
                    # NO FALLBACKS - This is a safety mechanism, not a business logic fallback
                    # Only check if last_candle_update_time is valid (not 0.0) to avoid false warnings on first run
                    elif last_candle_update_time > 0.0 and current_time - last_candle_update_time >= 310:  # 5 minutes 10 seconds (slightly longer than 5 min)
                        try:
                            logger.warning(f"⚠️ Candle update missed boundary - updating now (elapsed: {current_time - last_candle_update_time:.0f}s)")
                            historical_service = get_global_historical_data_service()
                            if historical_service._candle_storage:
                                historical_service._candle_storage.update_with_latest_candle()
                                last_candle_update_time = current_time
                        except Exception as e:
                            logger.error(f"❌ Failed to update candle storage (safety check): {e}")
                    
                    # Get current market data from MarketDataService
                    current_price = market_data_service.get_current_price()
                    if not current_price or current_price <= 0:
                        logger.warning("⚠️ Invalid current price, skipping iteration")
                        time.sleep(check_interval)
                        continue

                    # Get orderbook data
                    orderbook_data = market_data_service.get_market_data()

                    # Prepare unified market data (triggers all analysis modules)
                    unified_data = self._prepare_unified_market_data(
                        orderbook_data, current_price, market_data_service, strategy
                    )

                    # Detect and update strategy AFTER all analysis modules are complete
                    # This ensures we have the most up-to-date market data for strategy selection
                    current_strategy = self._detect_and_update_strategy(
                        unified_data, dashboard_service
                    )
                    
                    # Update unified data with new strategy if it changed
                    if current_strategy != strategy:
                        unified_data["strategy"] = current_strategy
                        logger.info(f"🔄 Strategy updated in unified data: {strategy} → {current_strategy}")

                    # Generate prediction
                    try:
                        prediction = self.prediction_engine.generate_prediction(unified_data, current_strategy)
                        if prediction:
                            unified_data["prediction"] = {
                                "direction": prediction.direction,
                                "entry_price": prediction.entry_price,
                                "stop_loss": prediction.stop_loss,
                                "take_profit": prediction.take_profit,
                                "confidence": prediction.confidence,  # Already 0-100 percentage
                                "reasoning": prediction.reasoning,
                                "strategy": prediction.strategy,
                                "timestamp": prediction.timestamp,
                                "status": "READY"
                            }
                        else:
                            unified_data["prediction"] = None
                    except Exception as e:
                        logger.error(f"❌ Prediction generation failed: {e}")
                        unified_data["prediction"] = None
                    
                    # ML training DISABLED - removed periodic check
                    
                    # Update dashboard with unified market data (includes prediction)
                    self._update_dashboard_with_unified_data(
                        unified_data, dashboard_service
                    )

                    # Update order lifecycle

                    # Update session time
                    if self.session_manager:
                        self.session_manager._update_session_time()

                    # Update strategy for next iteration
                    strategy = current_strategy

                    # Historical data is managed by HistoricalDataService - single source of truth

                    # Sleep before next iteration
                    time.sleep(check_interval)

                except Exception as e:
                    logger.error(f"❌ Data loop iteration failed: {e}")
                    time.sleep(check_interval)
                    continue

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
        
        # Module update intervals are now handled by CentralizedCache
        # No need for duplicate definitions here
        
        # Price change threshold for price-sensitive modules
        price_change_threshold = 0.001  # 0.1%
        
        # Track price changes
        if self._last_price is None:
            self._last_price = current_price
            # Initialize 5-minute boundary tracking
            self._last_5m_boundary = TimeUtils.get_5m_candle_start_time()
            # Force update all modules on first run (excluding those handled by MarketDataService)
            return [m for m in analysis_modules.keys() if m not in modules_handled_by_market_data_service]
        
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
                cache = get_global_centralized_cache()
                cache.invalidate(pattern="pattern_recognition")
                cache.invalidate(pattern="patterns")
                self._last_5m_boundary = current_5m_start
        else:
            self._last_5m_boundary = current_5m_start
        
        for module_name, module_instance in analysis_modules.items():
            # Skip modules handled directly by MarketDataService
            if module_name in modules_handled_by_market_data_service:
                continue
            
            # Check if module should be updated
            should_update = False
            
            # Check time interval using CentralizedCache intervals
            last_update = self._last_update_times.get(module_name, 0)
            # Get interval from CentralizedCache singleton
            cache = get_global_centralized_cache()
            interval = cache._get_ttl_policy(module_name)  # Get TTL policy for module
            
            if current_time - last_update >= interval:
                should_update = True
            
            # Pattern recognition: trigger on new 5-minute candle close (optimized)
            if module_name == "pattern_recognition" and new_candle_closed:
                should_update = True
                logger.debug(f"🕐 Pattern recognition triggered by new 5m candle close")
            
            # Check price change for price-sensitive modules
            price_sensitive_modules = ['rsi_calculator', 'support_resistance']
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
        if self._last_orderbook is None:
            self._last_orderbook = orderbook_data
            return True
        
        # Simple comparison - could be enhanced with more sophisticated change detection
        current_bids = orderbook_data.get('bids', [])
        current_asks = orderbook_data.get('asks', [])
        last_bids = self._last_orderbook.get('bids', [])
        last_asks = self._last_orderbook.get('asks', [])
        
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
        strategy: str,
    ) -> Dict[str, Any]:
        """Prepare unified market data for analysis"""
        try:
            # Trigger analysis modules to calculate and send data to MarketDataService
            self._trigger_analysis_modules(
                market_data_service, current_price, orderbook_data
            )

            # Small delay to ensure all analysis modules complete their calculations
            # This prevents strategy selection from using stale data
            time.sleep(0.1)  # 100ms delay for analysis completion

            # Get comprehensive analysis data from MarketDataService (includes prediction data)
            analysis_data = market_data_service.get_dashboard_data(strategy)
            
            # Log if analysis_data is empty
            if not analysis_data or len(analysis_data) == 0:
                logger.error(f"❌ analysis_data is EMPTY from get_dashboard_data!")
            else:
                logger.debug(f"📊 Got {len(analysis_data)} keys from get_dashboard_data: {list(analysis_data.keys())[:10]}...")

            # Remove non-serializable objects for dashboard compatibility
            if "raw_data_access" in analysis_data:
                del analysis_data["raw_data_access"]

            # Get session data
            session_data = self._get_session_data()

            # Get trading data
            trading_data = self._get_trading_data()

            # ML training DISABLED
            ml_performance_data = {}
            
            # Prepare unified data with analysis data
            unified_data = {
                "timestamp": time.time(),
                "current_price": current_price,
                "strategy": strategy,
                "orderbook_data": orderbook_data,  # Level 2 orderbook with bids/asks
                "session_data": session_data,
                "trading_data": trading_data,
                "ml_data": {},
                "ml_performance": ml_performance_data,
                # Include all analysis data
                **analysis_data,
            }

            return unified_data

        except Exception as e:
            logger.error(f"❌ Unified market data preparation failed: {e}")
            raise

    def _trigger_analysis_modules(
        self, market_data_service, current_price: float, orderbook_data: Dict[str, Any]
    ) -> None:
        """
        Trigger analysis modules via MarketDataService - SRP compliant
        
        MarketDataService is the single coordinator for all analysis modules.
        This method only determines which modules need updates and delegates to MarketDataService.
        """
        try:
            # Get analysis modules from MarketDataService to determine what needs updating
            analysis_modules = getattr(market_data_service, "_analysis_modules", {})
            # Removed excessive debug logging

            # Check which modules actually need updates
            modules_to_update = self._get_modules_needing_update(
                analysis_modules, current_price, orderbook_data
            )
            
            if not modules_to_update:
                # Removed excessive debug logging
                return

            # Removed excessive debug logging

            # Map module names to MarketDataService get methods
            module_to_getter = {
                "rsi_calculator": lambda: market_data_service.get_rsi_analysis(),
                "volatility": lambda: market_data_service.get_volatility_analysis("standard"),
                "trend": lambda: market_data_service.get_trend_analysis("standard"),
                "support_resistance": lambda: market_data_service.get_support_resistance_analysis("standard"),
                "volume": lambda: market_data_service.get_volume_analysis(),
                "pressure": lambda: market_data_service.get_pressure_analysis(),
                "pattern_recognition": lambda: market_data_service.get_pattern_analysis(),
                "market_conditions": lambda: market_data_service.get_market_conditions_analysis(),
                "cross_asset_correlation_analyzer": lambda: market_data_service.get_cross_asset_analysis(),
            }

            # Update modules via MarketDataService (SRP: MarketDataService coordinates all module access)
            for module_name in modules_to_update:
                try:
                    # Removed excessive debug logging
                    
                    # Get analysis via MarketDataService (single source of truth)
                    getter = module_to_getter.get(module_name)
                    if getter:
                        analysis_result = getter()
                        # MarketDataService already stores the result via its get_* methods
                        # Removed excessive debug logging

                except Exception as e:
                    logger.warning(f"⚠️ Failed to update {module_name} via MarketDataService: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Failed to update analysis modules with live data: {e}")

    def _get_session_data(self) -> Dict[str, Any]:
        """Get session data"""
        try:
            if not self.session_manager:
                raise ValueError("Session manager not available - NO FALLBACKS")
            
            session_data = self.session_manager.current_session_data
            return {
                "session_id": session_data.get("session_id", "unknown"),
                "start_time": session_data.get("start_time", 0.0),
                "current_balance": session_data.get("current_balance", 0.0),
                "session_start_time": session_data.get("start_time", 0.0),
                "session_time": session_data.get("session_time", "0s"),
                "status": session_data.get("status", "INACTIVE"),
                "strategy": session_data.get("strategy", "standard"),
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

    def _detect_and_update_strategy(
        self, unified_data: Dict[str, Any], dashboard_service
    ) -> str:
        """Detect and update strategy based on market conditions using unified data"""
        try:
            if self.strategy_manager:
                current_strategy = unified_data.get("strategy", "standard")

                # Detect optimal strategy using comprehensive unified data
                new_strategy = self.strategy_manager.detect_optimal_strategy(unified_data)

                if new_strategy != current_strategy:
                    logger.info(
                        f"🎯 Strategy updated: {current_strategy} → {new_strategy}"
                    )
                    logger.info(f"   📊 Market conditions: volatility={unified_data.get('volatility_category', 'UNKNOWN')}, trend={unified_data.get('trend', {}).get('direction', 'UNKNOWN')}")
                    
                    # Update session manager with new strategy
                    if self.session_manager and self.session_manager.current_session_data:
                        self.session_manager.current_session_data["strategy"] = new_strategy
                        logger.debug(f"📊 Session manager strategy updated to: {new_strategy}")
                    
                    return new_strategy
                else:
                    logger.debug(f"🎯 Strategy unchanged: {current_strategy}")
                    # Even if unchanged, ensure session manager has the correct strategy
                    if self.session_manager:
                        if self.session_manager.current_session_data.get("strategy") != current_strategy:
                            self.session_manager.current_session_data["strategy"] = current_strategy
                            logger.debug(f"📊 Session manager strategy synced to: {current_strategy}")
                    return current_strategy
            else:
                logger.warning(
                    "⚠️ Strategy Manager not available - using default strategy"
                )
                return unified_data.get("strategy", "standard")

        except Exception as e:
            logger.warning(f"⚠️ Strategy detection failed: {e}")
            return unified_data.get("strategy", "standard")


    def _end_session(self):
        """End trading session"""
        try:
            if self.session_manager:
                self.session_manager.end_session()
                logger.info("✅ Session ended successfully")
        except Exception as e:
            logger.error(f"❌ Session end failed: {e}")

    def _update_dashboard_with_unified_data(
        self, unified_data: Dict[str, Any], dashboard_service
    ):
        """Update dashboard with unified market data and session data"""
        try:
            # Update market data with analysis data (includes strategy in unified_data)
            dashboard_service.update_market_data(unified_data)
            
            # Update session data from SessionManager (ensure strategy is synced)
            if self.session_manager:
                session_data = self.session_manager.get_current_session_data()
                # Ensure session data has the latest strategy from unified_data
                if "strategy" in unified_data:
                    session_data["strategy"] = unified_data["strategy"]
                    if self.session_manager:
                        self.session_manager.current_session_data["strategy"] = unified_data["strategy"]
                dashboard_service.update_session_data(session_data)

        except Exception as e:
            logger.error(f"❌ Dashboard update failed: {e}")
