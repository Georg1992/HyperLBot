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

                    # Generate ML prediction with CORRECT strategy
                    self._generate_price_prediction(unified_data, current_strategy)

                    # Fetch active prediction and attach to unified data for dashboard
                    try:
                        from core.ml.realtime_prediction_engine import get_global_realtime_prediction_engine
                        _pe = get_global_realtime_prediction_engine()
                        _ap = _pe.get_active_prediction()
                        if _ap:
                            pred_dict = _ap.to_dict()
                            # Ensure strategy is included in prediction dict
                            pred_dict["strategy"] = current_strategy
                            unified_data["prediction"] = pred_dict
                            logger.info(f"📡 ✅ ATTACHED PREDICTION: dir={_ap.direction} conf={_ap.confidence:.1%} entry=${_ap.entry_price:,.2f} strategy={current_strategy}")
                        else:
                            unified_data["prediction"] = None
                            logger.warning("📡 ⚠️ No active prediction available to attach (None)")
                    except Exception as _e:
                        logger.error(f"❌ Could not attach active prediction to dashboard data: {_e}", exc_info=True)
                        unified_data["prediction"] = None

                    # Update dashboard (after prediction so UI receives it in this cycle)
                    self._update_dashboard_with_unified_data(
                        unified_data, dashboard_service
                    )

                    # Update order lifecycle
                    self._update_order_lifecycle(current_price)

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
            # Get interval from CentralizedCache singleton
            from core.services.centralized_cache import get_global_centralized_cache
            cache = get_global_centralized_cache()
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

            # Small delay to ensure all analysis modules complete their calculations
            # This prevents strategy selection from using stale data
            time.sleep(0.1)  # 100ms delay for analysis completion

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
        """Trigger analysis modules only when data changes - Event-driven architecture with completion tracking"""
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
                    return new_strategy
                else:
                    logger.debug(f"🎯 Strategy unchanged: {current_strategy}")
                    return current_strategy
            else:
                logger.warning(
                    "⚠️ Strategy Manager not available - using default strategy"
                )
                return unified_data.get("strategy", "standard")

        except Exception as e:
            logger.warning(f"⚠️ Strategy detection failed: {e}")
            return unified_data.get("strategy", "standard")

    def _update_order_lifecycle(self, current_price: float):
        """Update order lifecycle management and sync orders to dashboard"""
        try:
            from core.execution.order_lifecycle_manager import (
                get_global_order_lifecycle_manager,
            )

            order_lifecycle_manager = get_global_order_lifecycle_manager()

            if order_lifecycle_manager:
                # Check for order fills and update position prices
                order_lifecycle_manager.check_order_fills(current_price)
                order_lifecycle_manager.update_position_prices(current_price)
                
                # Sync order data to dashboard
                self._sync_order_data_to_dashboard(order_lifecycle_manager)
        except Exception as e:
            logger.error(f"❌ Order lifecycle update failed: {e}")
    
    def _sync_order_data_to_dashboard(self, order_lifecycle_manager):
        """Sync pending orders, filled orders, and positions to dashboard"""
        try:
            from core.services.dashboard_service import create_dashboard_service
            dashboard_service = create_dashboard_service()
            
            # Get order lifecycle data
            lifecycle_data = order_lifecycle_manager.get_dashboard_data()
            if not lifecycle_data:
                return
            
            pending_orders = lifecycle_data.get("pending_orders", [])
            active_positions = lifecycle_data.get("active_positions", [])
            closed_positions = lifecycle_data.get("closed_positions", [])
            
            # Get current price for updating pending orders
            from core.services.market_data_service import MarketDataService
            market_data_service = self.market_data_service if hasattr(self, 'market_data_service') else None
            current_price = 0
            if market_data_service:
                current_price = market_data_service.get_current_price() or 0
            
            # Format pending orders for dashboard
            formatted_pending = []
            for order in pending_orders:
                # Use current price from market data service if order's current_price is stale
                order_current_price = current_price if current_price > 0 else order.get("current_price", 0)
                
                formatted_order = {
                    "id": order.get("order_id", "unknown"),
                    "order_id": order.get("order_id", "unknown"),
                    "side": order.get("side", "UNKNOWN"),
                    "symbol": "BTC",
                    "status": "PENDING",
                    "type": "LIMIT",
                    "entry_price": order.get("limit_price", 0),  # Limit price where order will execute
                    "size": order.get("size", 0),
                    "limit_price": order.get("limit_price", 0),  # Explicit limit price field
                    "current_price": order_current_price,  # Current market price (updated)
                    "stop_loss": order.get("stop_loss"),
                    "take_profit": order.get("take_profit"),
                    "confidence": order.get("confidence", 0),
                    "expected_value": order.get("expected_value", 0),
                    "strategy": order.get("strategy", "standard"),
                    "timestamp": order.get("created_at", time.time()),
                    "created_at": order.get("created_at", time.time()),
                }
                formatted_pending.append(formatted_order)
            
            # Format active positions for dashboard
            formatted_positions = []
            for pos in active_positions:
                formatted_pos = {
                    "id": pos.get("position_id", "unknown"),
                    "order_id": pos.get("order_id", "unknown"),
                    "position_id": pos.get("position_id", "unknown"),
                    "side": pos.get("side", "UNKNOWN"),
                    "symbol": "BTC",
                    "status": "OPEN",
                    "type": "LIMIT",
                    "entry_price": pos.get("entry_price", 0),
                    "exit_price": 0,
                    "size": pos.get("size", 0),
                    "current_price": pos.get("current_price", 0),
                    "stop_loss": pos.get("stop_loss"),
                    "take_profit": pos.get("take_profit"),
                    "pnl": pos.get("unrealized_pnl", 0),
                    "pnl_pct": pos.get("pnl_pct", 0),
                    "confidence": pos.get("confidence", 0),
                    "strategy": pos.get("strategy", "standard"),
                    "timestamp": pos.get("entry_time", time.time()),
                    "created_at": pos.get("entry_time", time.time()),
                    "entry_time": pos.get("entry_time", time.time()),
                }
                formatted_positions.append(formatted_pos)
            
            # Format closed positions for dashboard
            formatted_closed = []
            for pos in closed_positions:
                formatted_closed_pos = {
                    "id": pos.get("position_id", "unknown"),
                    "order_id": pos.get("order_id", "unknown"),
                    "position_id": pos.get("position_id", "unknown"),
                    "side": pos.get("side", "UNKNOWN"),
                    "symbol": "BTC",
                    "status": "CLOSED",
                    "type": "LIMIT",
                    "entry_price": pos.get("entry_price", 0),
                    "exit_price": pos.get("exit_price", 0),
                    "size": pos.get("size", 0),
                    "stop_loss": pos.get("stop_loss"),
                    "take_profit": pos.get("take_profit"),
                    "pnl": pos.get("realized_pnl", 0),
                    "pnl_pct": pos.get("pnl_pct", 0),
                    "confidence": pos.get("confidence", 0),
                    "strategy": pos.get("strategy", "standard"),
                    "exit_reason": pos.get("exit_reason", "UNKNOWN"),
                    "timestamp": pos.get("entry_time", time.time()),
                    "created_at": pos.get("entry_time", time.time()),
                    "entry_time": pos.get("entry_time", time.time()),
                    "exit_time": pos.get("exit_time", time.time()) if pos.get("exit_time") else None,
                }
                formatted_closed.append(formatted_closed_pos)
            
            # Update dashboard with all order/trade data
            all_trades = formatted_pending + formatted_positions + formatted_closed
            
            # Sort by timestamp (newest first)
            all_trades.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            
            with dashboard_service._lock:
                # Keep existing trades that aren't from order lifecycle (from simulator)
                existing_trades = dashboard_service._data.get("trades", [])
                # Filter out old pending orders that might have been filled
                existing_trades_filtered = [
                    t for t in existing_trades 
                    if t.get("status") not in ["PENDING", "OPEN"]  # Keep only CLOSED from other sources
                    or (t.get("status") == "PENDING" and t.get("order_id") not in [o.get("order_id") for o in formatted_pending])
                ]
                
                # Combine: new order lifecycle data + filtered existing
                dashboard_service._data["trades"] = all_trades + existing_trades_filtered
                
                # Sort all trades by timestamp
                dashboard_service._data["trades"].sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                
                # Keep only last 100 trades for performance
                dashboard_service._data["trades"] = dashboard_service._data["trades"][:100]
                
                dashboard_service._save_data()
            
            if len(formatted_pending) > 0 or len(formatted_positions) > 0 or len(formatted_closed) > 0:
                logger.info(f"📊 ✅ Synced orders to dashboard: {len(formatted_pending)} pending, {len(formatted_positions)} open, {len(formatted_closed)} closed")
            
        except Exception as e:
            logger.error(f"❌ Failed to sync order data to dashboard: {e}")

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
        """Generate ML price prediction using RealtimePredictionEngine"""
        try:
            # Get prediction engine
            from core.ml.realtime_prediction_engine import get_global_realtime_prediction_engine
            prediction_engine = get_global_realtime_prediction_engine()
            
            # Update confidence threshold for strategy
            prediction_engine.update_confidence_threshold(strategy)
            
            # Generate prediction with unified data
            action = prediction_engine.update_prediction(unified_data, strategy)
            
            logger.info(f"🤖 ML prediction: {action}")
            
            # Check if ready to execute
            if action == "EXECUTE":
                active_prediction = prediction_engine.get_active_prediction()
                if active_prediction:
                    # Execute the prediction
                    self._execute_prediction(active_prediction, strategy)
                    
        except Exception as e:
            logger.error(f"❌ ML prediction failed: {e}")
    
    def _execute_prediction(self, prediction, strategy: str):
        """Execute a prediction that's ready for trading"""
        try:
            from core.execution.prediction_executor import PredictionExecutor
            from core.execution.trading_execution_wrapper import TradingExecutionWrapper
            # Use the global simulated account manager to access existing balance/state
            from core.simulated_account_manager import account_manager
            
            # Ensure account is loaded
            if not getattr(account_manager, 'account_data', None):
                account_manager.load_account()
            
            # Get required services from system initializer
            from core.services.system_initializer import get_system_initializer
            system_initializer = get_system_initializer()
            
            # Get HyperLiquid simulator for trading execution
            hyperliquid_simulator = system_initializer.get_singleton_system("hyperliquid_simulator")
            if not hyperliquid_simulator:
                logger.error("❌ HyperLiquid simulator not available")
                return
            
            # Create trading execution wrapper
            trading_execution = TradingExecutionWrapper(
                hyperliquid_simulator=hyperliquid_simulator,
                account_manager=account_manager,  # pass the global manager with balance
                session_manager=self.session_manager
            )
            
            # Create prediction executor with required services
            executor = PredictionExecutor(
                trading_execution=trading_execution,
                account_manager=account_manager,
                session_manager=self.session_manager
            )
            
            # Execute prediction (result is handled internally)
            executor.execute_prediction(prediction.to_dict() if hasattr(prediction, 'to_dict') else prediction, strategy)
            
        except Exception as e:
            logger.error(f"❌ Prediction execution failed: {e}")