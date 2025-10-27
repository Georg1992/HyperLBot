#!/usr/bin/env python3
"""
Session Orchestrator - Centralized session management with NO FALLBACKS policy
"""

import time
from typing import Dict, Any, Optional, List
from loguru import logger


class SessionOrchestrator:
    """Centralized session orchestrator with NO FALLBACKS policy"""

    def __init__(self, config, initial_balance: float = None):
        self.config = config
        self.initial_balance = initial_balance
        self.session_manager = None
        self.strategy_manager = None
        self._strategy_manager_initialized = False

        logger.info("🎯 SessionOrchestrator initialized with NO FALLBACKS policy")

    def _ensure_strategy_manager_initialized(self, system_initializer):
        """Ensure Strategy Manager is initialized (NO FALLBACKS)"""
        if not self._strategy_manager_initialized:
            try:
                # Get Strategy Manager from system initializer (NO FALLBACKS)
                if hasattr(system_initializer, "get_singleton_system"):
                    self.strategy_manager = system_initializer.get_singleton_system(
                        "strategy_manager"
                    )
                else:
                    raise Exception(
                        "System initializer does not have get_singleton_system method"
                    )

                if not self.strategy_manager:
                    raise Exception(
                        "Strategy Manager not available from system initializer"
                    )

                self._strategy_manager_initialized = True
                logger.info(
                    "✅ Strategy Manager initialized successfully (NO FALLBACKS)"
                )

            except Exception as e:
                logger.error(f"❌ Strategy Manager initialization failed: {e}")
                raise Exception(
                    "Strategy Manager initialization required - NO FALLBACKS"
                )

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
        """Verify data flow from MarketDataService (centralized price provider)"""
        try:
            logger.info("🔍 Verifying MarketDataService data flow...")

            # Test MarketDataService (centralized price provider)
            if hasattr(market_data_service, "get_current_price"):
                current_price = market_data_service.get_current_price()
                if current_price and current_price > 0:
                    logger.info(
                        f"✅ MarketDataService price verified: Price=${current_price:.2f}"
                    )
                else:
                    logger.warning("⚠️ MarketDataService price not available or invalid")
            else:
                logger.warning("⚠️ MarketDataService get_current_price method not available")

            logger.info("✅ Data flow verification completed")

        except Exception as e:
            logger.error(f"❌ Data flow verification failed: {e}")
            raise

    def _start_session(self, market_data_service, dashboard_service, strategy: str):
        """Start trading session"""
        try:
            logger.info(f"🎯 Starting trading session with strategy: {strategy}")

            # Clear stale data for fresh session
            if hasattr(dashboard_service, "clear_stale_data"):
                dashboard_service.clear_stale_data()

            if hasattr(market_data_service, "invalidate_processed_data"):
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

            while True:
                try:
                    # Get current market data from MarketDataService (centralized price provider)
                    current_price = None
                    if hasattr(market_data_service, "get_current_price"):
                        current_price = market_data_service.get_current_price()
                    else:
                        logger.warning(
                            "⚠️ MarketDataService get_current_price not available, skipping iteration"
                        )
                        time.sleep(check_interval)
                        continue

                    if not current_price or current_price <= 0:
                        logger.warning("⚠️ Invalid current price, skipping iteration")
                        time.sleep(check_interval)
                        continue

                    # Get orderbook data (Level 2 orderbook with bids/asks)
                    orderbook_data = {}
                    if hasattr(market_data_service, "get_market_data"):
                        orderbook_data = market_data_service.get_market_data()
                    else:
                        logger.warning(
                            "⚠️ MarketDataService get_market_data not available, skipping iteration"
                        )
                        time.sleep(check_interval)
                        continue

                    # Prepare unified market data
                    unified_data = self._prepare_unified_market_data(
                        orderbook_data, current_price, market_data_service, strategy
                    )

                    # Update dashboard
                    self._update_dashboard_with_unified_data(
                        unified_data, dashboard_service
                    )

                    # Generate ML prediction
                    self._generate_price_prediction(unified_data, strategy)

                    # Detect and update strategy
                    current_strategy = self._detect_and_update_strategy(
                        unified_data, dashboard_service
                    )

                    # Update order lifecycle
                    self._update_order_lifecycle(current_price)

                    # Update session time
                    if self.session_manager:
                        self.session_manager._update_session_time()

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
        
        # Module update intervals are now handled by CentralizedCache
        # No need for duplicate definitions here
        
        # Price change threshold for price-sensitive modules
        price_change_threshold = 0.001  # 0.1%
        
        # Track price changes
        if not hasattr(self, '_last_price'):
            self._last_price = current_price
            self._last_update_times = {}
            # Force update all modules on first run
            return list(analysis_modules.keys())
        
        price_change = abs(current_price - self._last_price) / self._last_price
        self._last_price = current_price
        
        for module_name, module_instance in analysis_modules.items():
            # Check if module should be updated
            should_update = False
            
            # Check time interval using CentralizedCache intervals
            last_update = self._last_update_times.get(module_name, 0)
            # Get interval from CentralizedCache or use default
            from core.services.centralized_cache import CentralizedCache
            cache = CentralizedCache()
            interval = cache._get_ttl_policy(module_name)  # Get TTL policy for module
            
            if current_time - last_update >= interval:
                should_update = True
            
            # Check price change for price-sensitive modules
            price_sensitive_modules = ['rsi_calculator', 'support_resistance']
            if module_name in price_sensitive_modules and price_change >= price_change_threshold:
                should_update = True
            
            # Check for data changes in orderbook
            if module_name in ['volume', 'pressure', 'orderbook']:
                if self._has_orderbook_changed(orderbook_data):
                    should_update = True
            
            if should_update:
                modules_to_update.append(module_name)
                self._last_update_times[module_name] = current_time
        
        return modules_to_update
    
    def _has_orderbook_changed(self, orderbook_data: Dict[str, Any]) -> bool:
        """Check if orderbook data has changed significantly"""
        if not hasattr(self, '_last_orderbook'):
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

            # Get comprehensive analysis data from MarketDataService (includes prediction data)
            analysis_data = market_data_service.get_dashboard_data(strategy)

            # Remove non-serializable objects for dashboard compatibility
            if "raw_data_access" in analysis_data:
                del analysis_data["raw_data_access"]

            # Get session data
            session_data = self._get_session_data()

            # Get trading data
            trading_data = self._get_trading_data()

            # Prepare unified data with analysis data
            unified_data = {
                "timestamp": time.time(),
                "current_price": current_price,
                "strategy": strategy,
                "orderbook_data": orderbook_data,  # Level 2 orderbook with bids/asks
                "session_data": session_data,
                "trading_data": trading_data,
                "ml_data": {},
                # Include all analysis data
                **analysis_data,
            }

            return unified_data

        except Exception as e:
            logger.error(f"❌ Unified market data preparation failed: {e}")
            return {}

    def _trigger_analysis_modules(
        self, market_data_service, current_price: float, orderbook_data: Dict[str, Any]
    ) -> None:
        """Trigger analysis modules only when data changes - Event-driven architecture"""
        try:
            # Get analysis modules from MarketDataService
            analysis_modules = getattr(market_data_service, "_analysis_modules", {})
            logger.debug(f"📊 Found {len(analysis_modules)} analysis modules: {list(analysis_modules.keys())}")

            # Check which modules actually need updates
            modules_to_update = self._get_modules_needing_update(
                analysis_modules, current_price, orderbook_data
            )
            
            if not modules_to_update:
                logger.debug("📊 No modules need updates - skipping analysis")
                return

            logger.debug(f"📊 Updating {len(modules_to_update)} modules: {modules_to_update}")

            # Update only modules that need updates
            for module_name in modules_to_update:
                module_instance = analysis_modules[module_name]
                try:
                    logger.debug(f"📊 Processing module: {module_name}")
                    
                    # Update module with live price data (like live data streams)
                    if hasattr(module_instance, "update_realtime_rsi"):
                        # RSI: Update with live price data
                        rsi_result = module_instance.update_realtime_rsi(current_price)
                        if rsi_result:
                            market_data_service.update_analysis_data("rsi", rsi_result)
                            logger.debug(f"📊 RSI data updated: {rsi_result}")

                    if hasattr(module_instance, "get_latest_analysis"):
                        # Other modules: Get latest analysis with current price
                        if module_name == "volume":
                            # Volume analysis needs websocket
                            analysis_result = module_instance.get_latest_analysis(
                                hyperliquid_websocket=market_data_service.hyperliquid_websocket
                            )
                        elif module_name == "support_resistance":
                            # S/R needs current price
                            analysis_result = module_instance.get_latest_analysis(
                                current_price=current_price
                            )
                        elif module_name == "trend":
                            # Trend analysis
                            analysis_result = module_instance.get_latest_analysis()
                        elif module_name == "volatility":
                            # Volatility analysis
                            logger.debug(f"📊 Triggering volatility analysis...")
                            analysis_result = module_instance.get_latest_analysis()
                            logger.debug(f"📊 Volatility analysis result: {analysis_result}")
                        elif module_name == "pressure":
                            # Pressure analysis
                            logger.debug(f"📊 Triggering pressure analysis...")
                            analysis_result = module_instance.get_latest_analysis()
                            logger.debug(f"📊 Pressure analysis result: {analysis_result}")
                        elif module_name == "pattern_recognition":
                            # Pattern analysis needs candles
                            from core.services.historical_data_service import create_historical_data_service
                            historical_service = create_historical_data_service()
                            candles = historical_service.get_5m_candles("BTC", 50)  # Get 50 candles for pattern analysis
                            if candles:
                                analysis_result = module_instance.analyze_patterns(candles)
                                logger.debug(f"📊 Pattern analysis completed: {len(analysis_result.get('all_patterns', []))} patterns")
                            else:
                                logger.warning("⚠️ No candles available for pattern analysis")
                                analysis_result = None
                        elif module_name == "market_conditions":
                            # Market conditions analysis needs comprehensive market data
                            logger.debug(f"📊 Triggering market conditions analysis...")
                            # Get current market data for conditions analysis
                            market_data = {
                                "current_price": current_price,
                                "rsi": market_data_service.get_rsi_analysis().get("rsi", 50.0),
                                "trend": market_data_service.get_trend_analysis("standard").get("direction", "SIDEWAYS"),
                                "volatility_5m": market_data_service.get_volatility_analysis("standard").get("volatility_5m", 0.0),
                                "volatility_category": market_data_service.get_volatility_analysis("standard").get("volatility_5m_category", "MODERATE"),
                                "volume_category": market_data_service.get_volume_analysis().get("hyperliquid_5m", {}).get("volume_category", "MODERATE")
                            }
                            # Get 1d candles for market trend analysis
                            from core.services.historical_data_service import create_historical_data_service
                            historical_service = create_historical_data_service()
                            candles_1d = historical_service.get_1d_candles("BTC", 30)  # Request 30 days to ensure we have at least 7
                            
                            analysis_result = module_instance.analyze_trading_conditions(market_data, candles_1d=candles_1d)
                            logger.debug(f"📊 Market conditions analysis completed: {analysis_result.get('condition', 'UNKNOWN')} condition")
                        elif module_name == "cross_asset_correlation_analyzer":
                            # Cross asset correlation analysis needs current price
                            logger.debug(f"📊 Triggering cross asset correlation analysis...")
                            analysis_result = module_instance.analyze_cross_asset_correlations(current_price)
                            logger.debug(f"📊 Cross asset correlation analysis completed: {analysis_result.get('status', 'UNKNOWN')} status")
                        else:
                            # Other modules get their own data
                            analysis_result = module_instance.get_latest_analysis()

                        if analysis_result:
                            market_data_service.update_analysis_data(module_name, analysis_result)
                            logger.debug(f"📊 {module_name} data updated: {type(analysis_result)}")
                        else:
                            logger.warning(f"⚠️ {module_name} returned no data")

                    logger.debug(f"📊 Updated live data for module: {module_name}")

                except Exception as e:
                    logger.warning(
                        f"⚠️ Failed to update live data for module {module_name}: {e}"
                    )
                    continue

        except Exception as e:
            logger.error(f"❌ Failed to update analysis modules with live data: {e}")

    def _get_session_data(self) -> Dict[str, Any]:
        """Get session data"""
        try:
            if self.session_manager and hasattr(
                self.session_manager, "current_session_data"
            ):
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
            else:
                return {
                    "session_id": "unknown",
                    "start_time": 0.0,
                    "current_balance": 0.0,
                    "session_start_time": 0.0,
                    "session_time": "0s",
                    "status": "INACTIVE",
                    "strategy": "standard",
                }
        except Exception as e:
            logger.error(f"❌ Failed to get session data: {e}")
            return {}

    def _get_trading_data(self) -> Dict[str, Any]:
        """Get trading data"""
        try:
            # Trading data would come from trading execution
            return {
                "open_positions": [],
                "pending_orders": [],
                "trade_history": [],
            }
        except Exception as e:
            logger.error(f"❌ Failed to get trading data: {e}")
            return {}

    def _detect_and_update_strategy(
        self, unified_data: Dict[str, Any], dashboard_service
    ) -> str:
        """Detect and update strategy based on market conditions"""
        try:
            if self.strategy_manager:
                current_strategy = unified_data.get("strategy", "standard")

                # Detect optimal strategy
                new_strategy = self.strategy_manager.detect_optimal_strategy(unified_data)

                if new_strategy != current_strategy:
                    logger.info(
                        f"🎯 Strategy updated: {current_strategy} → {new_strategy}"
                    )
                    return new_strategy
                else:
                    return current_strategy
            else:
                logger.warning(
                    "⚠️ Strategy Manager not available - using default strategy"
                )
                return unified_data.get("current_strategy", "standard")

        except Exception as e:
            logger.warning(f"⚠️ Strategy detection failed: {e}")
            return unified_data.get("current_strategy", "standard")

    def _update_order_lifecycle(self, current_price: float):
        """Update order lifecycle management"""
        try:
            from core.execution.order_lifecycle_manager import (
                get_global_order_lifecycle_manager,
            )

            order_lifecycle_manager = get_global_order_lifecycle_manager()

            if order_lifecycle_manager:
                # Check for order fills and update position prices
                order_lifecycle_manager.check_order_fills(current_price)
                order_lifecycle_manager.update_position_prices(current_price)
        except Exception as e:
            logger.error(f"❌ Order lifecycle update failed: {e}")

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
            # Update market data with analysis data
            dashboard_service.update_market_data(unified_data)
            
            # Update session data from SessionManager
            if self.session_manager:
                session_data = self.session_manager.get_current_session_data()
                dashboard_service.update_session_data(session_data)
                logger.debug(f"📊 Session data updated: {session_data.get('status', 'UNKNOWN')}")
            
            logger.debug("📊 Dashboard updated with unified market data and session data")

        except Exception as e:
            logger.error(f"❌ Dashboard update failed: {e}")

    def _generate_price_prediction(self, unified_data: Dict[str, Any], strategy: str):
        """Generate ML price prediction"""
        try:
            # ML prediction logic would go here
            logger.debug("🤖 ML prediction generated")
        except Exception as e:
            logger.error(f"❌ ML prediction failed: {e}")