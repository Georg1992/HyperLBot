#!/usr/bin/env python3
"""
Session Orchestrator Service  
Handles trading session lifecycle and main trading loop
Single Responsibility: Session coordination and trading loop
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger
# SessionManager will be imported lazily when needed

# Import volatility calculator for multi-timeframe analysis
from core.analysis.real_time.volatility_calculator import get_global_volatility_calculator

class SessionOrchestrator:
    """Session orchestration service - handles trading loop and lifecycle"""
    
    def __init__(self, config, initial_balance: float):
        self.config = config
        self.initial_balance = initial_balance
        self.session_manager = None
        self.weekly_trend_analysis = {}
        
        # Strategy Manager for dynamic strategy selection
        self.strategy_manager = None
        self._strategy_manager_initialized = False
        
        # Price prediction
        self.current_prediction = None
        
        # Market opening service for dashboard display
        try:
            from core.services.market_opening_service import global_market_opening_service
            self.market_opening_service = global_market_opening_service
            logger.info("🌍 Market opening service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Market opening service initialization failed: {e}")
            self.market_opening_service = None
        
        logger.info("🔄 Session Orchestrator initialized - Strategy-driven trading loop")
    
    def _ensure_strategy_manager_initialized(self, system_initializer):
        """Ensure Strategy Manager is initialized (lazy initialization)"""
        if not self._strategy_manager_initialized:
            try:
                # Try to get from system initializer singleton
                self.strategy_manager = system_initializer.get_singleton_system("strategy_manager")
                if not self.strategy_manager:
                    # Fallback: create new instance
                    from core.services.strategy_manager import StrategyManager
                    self.strategy_manager = StrategyManager(self.config)
                    logger.info("🎯 Strategy Manager created (new instance)")
                else:
                    logger.info("🎯 Strategy Manager initialized (singleton)")
                
                self._strategy_manager_initialized = True
            except Exception as e:
                logger.error(f"❌ Failed to initialize Strategy Manager: {e}")
                self.strategy_manager = None
        
        return self.strategy_manager
    
    def run_paper_trading_session(self, check_interval: int,
                                 system_initializer, market_data_service, trading_engine, dashboard_service, strategy_manager=None) -> Dict[str, Any]:
        """Run the main paper trading session with ultra-consistent phases"""
        try:
            # PHASE 1: Systems should already be initialized by TradingFacade
            logger.info("🔧 PHASE 1: Systems already initialized by TradingFacade")
            
            # Use the system_initializer passed from TradingFacade (not create a new one)
            phase_initializer = system_initializer
            
            # Verify analysis phase is ready (systems should already be initialized)
            if not phase_initializer.is_analysis_ready():
                logger.error("❌ System not ready for analysis phase")
                return {"success": False, "error": "System not ready for analysis"}
            
            # Get Hyperliquid API from the initialized system
            hyperliquid_api = phase_initializer.get_singleton_system("hyperliquid_api")
            if not hyperliquid_api:
                logger.error("❌ Hyperliquid API not available")
                return {"success": False, "error": "Hyperliquid API not available"}
            
            logger.success("✅ PHASE 1 COMPLETE: All systems initialized and ready for analysis")
            
            # PHASE 2: Start session (session manager, clear data, heartbeat)
            logger.info("🚀 PHASE 2: Starting session...")
            self._start_session(dashboard_service, market_data_service)
            logger.success("✅ PHASE 2 COMPLETE: Session started")
            
            # PHASE 3: Load historic data and verify all data is being received properly
            logger.info("📊 PHASE 3: Loading historical data and verifying data flow...")
            self._load_and_verify_historical_data(hyperliquid_api, market_data_service)
            logger.success("✅ PHASE 3 COMPLETE: Historical data loaded and verified")
            
            # PHASE 4: Start data collection and dashboard updates (no trading)
            logger.info("📊 PHASE 4: Starting data collection and dashboard updates...")
            return self._main_data_loop(check_interval, hyperliquid_api,
                                       market_data_service, dashboard_service)
            
        except Exception as e:
            logger.error(f"❌ Trading session failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _start_session(self, dashboard_service, market_data_service):
        """Start trading session (PHASE 2: Session-specific logic only)"""
        try:
            # Clear dashboard cache
            dashboard_service.clear_presentation_data()
            logger.info("🧹 Dashboard cache cleared - Fresh session data")
            
            # Start session  
            from core.session.session_manager import get_global_session_manager
            self.session_manager = get_global_session_manager()  # Use singleton instance
            logger.info("✅ SessionManager initialized")
            
            # Register session manager in singleton systems for PredictionExecutor access
            from core.services.system_initializer import get_system_initializer
            system_init = get_system_initializer()
            system_init.singleton_systems["session_manager"] = self.session_manager
            
            # Update trading execution wrapper with session manager
            trading_execution = system_init.singleton_systems.get("trading_execution")
            if trading_execution and hasattr(trading_execution, 'session_manager'):
                trading_execution.session_manager = self.session_manager
                logger.info("✅ Trading execution wrapper updated with session manager")
            
            # Create initial heartbeat
            dashboard_service.create_initial_heartbeat(self.session_manager, "standard", self.initial_balance)
            
            # Start session
            session_id = self.session_manager.start_session(
                session_id=f"bot_session_{int(time.time())}",
                strategy="standard",
                initial_balance=self.initial_balance
            )
            
            # Log session start
            dashboard_service.add_activity(
                f"🚀 Trading bot started with ${self.initial_balance:.2f} initial balance", 
                "SUCCESS"
            )
            
            logger.success("🔥 Session started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start session: {e}")
    
    def _load_and_verify_historical_data(self, hyperliquid_api, market_data_service):
        """Load and verify all historical data (PHASE 3: Historical data loading and verification)"""
        try:
            # 3.1: Historical data verification (using centralized trend calculation)
            logger.info("📅 Verifying historical data availability...")
            
            # 3.2: Compute and store historical context
            logger.info("📊 Computing session historical context (6.5 weeks analysis)...")
            self._compute_and_store_historical_context(market_data_service)
            
            # Wait a moment for computation to complete
            time.sleep(1)
            
            # 3.3: Verify historical context was computed successfully
            if not self.session_manager.has_historical_context():
                logger.warning("⚠️ Historical context computation failed - retrying once...")
                # Retry once with a small delay
                time.sleep(3)
                self._compute_and_store_historical_context(market_data_service)
                
                if not self.session_manager.has_historical_context():
                    logger.error("❌ Historical context computation failed after retry - continuing with degraded functionality")
                else:
                    logger.success("✅ Historical context ready after retry")
            else:
                logger.success("✅ Historical context ready for market conditions analysis")
            
            # 3.4: Verify data flow is working
            logger.info("🔍 Verifying data flow...")
            self._verify_data_flow(hyperliquid_api, market_data_service)
            
        except Exception as e:
            logger.error(f"❌ Failed to load historical data: {e}")
            raise
    
    def _verify_data_flow(self, hyperliquid_api, market_data_service):
        """Verify that all data sources are working properly"""
        try:
            # Test MarketDataService - single source of truth
            logger.info("🔍 Testing MarketDataService data flow...")
            market_data = market_data_service.get_market_data("BTC")
            
            if "error" in market_data:
                raise ValueError(f"MarketDataService error: {market_data['error']}")
            
            # Check for orderbook data (l2Book endpoint returns levels, not markPrice)
            if 'levels' not in market_data:
                raise ValueError(f"MarketDataService missing levels in response: {list(market_data.keys())}")
            
            # Verify we can get current price from the data
            current_price = market_data_service.get_hyperliquid_price()
            if not current_price or current_price <= 0:
                raise ValueError("MarketDataService unable to provide current price")
            
            logger.success(f"✅ MarketDataService data flow verified - Price: ${current_price:.2f}")
            logger.success("✅ MarketDataService ready")
            
            # Volume will be verified in trading loop after WebSocket accumulates data
            logger.info("📊 Volume data will be verified in trading loop (WebSocket needs time to accumulate)")
            logger.success("✅ Volume data will be ready")
            
            logger.success("✅ All data flows verified successfully")
            
        except Exception as e:
            logger.error(f"❌ Data flow verification failed: {e}")
            raise
    
    def _compute_and_store_historical_context(self, market_data_service):
        """Compute historical context once per session and store in SessionManager"""
        try:
            logger.info("📊 Computing session historical context (6.5 weeks analysis)...")
            
            # Import historical analyzer
            from core.analysis.historical.session_context_analyzer import SessionContextAnalyzer
            from core.api.hyperliquid_api import get_hyperliquid_api
            
            # Get Hyperliquid API instance
            hyperliquid_api = get_hyperliquid_api()
            
            # Get historical data for context analysis from MarketDataService (single source of truth)
            logger.info("📊 Getting historical candle data from MarketDataService...")
            candles_1d = market_data_service.get_historical_candles("BTC", "1d", 45)
            candles_1h = market_data_service.get_historical_candles("BTC", "1h", 84)  
            candles_5m = market_data_service.get_historical_candles("BTC", "5m", 30)
            
            logger.info(f"📊 Daily candles: {len(candles_1d) if candles_1d else 0} candles")
            logger.info(f"📊 Hourly candles: {len(candles_1h) if candles_1h else 0} candles")
            logger.info(f"📊 5-minute candles: {len(candles_5m) if candles_5m else 0} candles")
            
            # Validate data before analysis
            if not candles_1d or not candles_1h or not candles_5m:
                logger.error("❌ Historical data fetching failed - missing candle data")
                logger.error(f"   Daily: {len(candles_1d) if candles_1d else 0}, Hourly: {len(candles_1h) if candles_1h else 0}, 5m: {len(candles_5m) if candles_5m else 0}")
                return
            
            # Analyze historical context
            logger.info("📊 Analyzing historical context...")
            context_analyzer = SessionContextAnalyzer()
            historical_context = context_analyzer.analyze_session_context(candles_1d, candles_1h, candles_5m)
            
            # Store in SessionManager (business logic layer) - use singleton
            from core.session.session_manager import get_global_session_manager
            session_manager = get_global_session_manager()
            session_manager.set_historical_context(historical_context)
            
            logger.success("✅ Session historical context computed and stored")
            logger.info(f"✅ Market regime: {historical_context.get('market_regime', {}).get('regime', 'UNKNOWN')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to compute historical context: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            # Continue session without historical context (degraded but functional)
    
    def _prepare_unified_market_data(self, market_data: Dict[str, Any], current_price: float, market_data_service=None, strategy: str = "standard") -> Dict[str, Any]:
        """Prepare unified market data structure for both Signal Aggregator and Dashboard - SINGLE DATA SOURCE"""
        try:
            logger.debug(f"🔍 _prepare_unified_market_data called with market_data_service: {type(market_data_service)}")
            # SINGLE DATA SOURCE: Use only MarketDataService data
            # No more MarketDataManager calls - MarketDataService is the single source of truth
            
            # Extract all data from the single market_data source
            # Get data from hyperliquid_data (which contains all the market data)
            hyperliquid_data = market_data.get("hyperliquid_data", {})
            volume_data = hyperliquid_data.get("volume_data", {})
            binance_volume_data = hyperliquid_data.get("binance_volume_data", {})
            orderbook = hyperliquid_data.get("orderbook", {})
            
            # OPTIMIZED CACHING: All requests will be served from the same cached data
            # MarketDataService now fetches maximum needed and slices automatically
            # Each request below will use the centralized cache - no redundant API calls
            
            # Get candle data for all timeframes (from centralized cache)
            candles_5m_for_rsi = market_data_service.get_historical_candles("BTC", "5m", 50)  # For RSI calculation (reduced to match Hyperliquid)
            candles_5m = market_data_service.get_historical_candles("BTC", "5m", 10)          # For general analysis (reduced for faster volatility response)
            candles_5m_for_sr = market_data_service.get_historical_candles("BTC", "5m", 200)  # For S/R calculation (increased for better support detection)
            candles_1m = market_data_service.get_historical_candles("BTC", "1m", 20)
            candles_1h = market_data_service.get_historical_candles("BTC", "1h", 24)
            candles_1d = market_data_service.get_historical_candles("BTC", "1d", 7)
            
            logger.debug(f"📊 Candles from cache: 5m_RSI={len(candles_5m_for_rsi)}, 5m_general={len(candles_5m)}, 5m_SR={len(candles_5m_for_sr)}, 1m={len(candles_1m)}, 1h={len(candles_1h)}, 1d={len(candles_1d)}")

            # RSI calculation using centralized candle data
            from core.analysis.real_time.rsi_calculator import get_global_rsi_calculator
            rsi_calculator = get_global_rsi_calculator()
            
            try:
                # REAL-TIME RSI 14 CALCULATION - Updates with current price like Hyperliquid
                # 1. Calculate baseline from completed candles
                baseline_rsi = rsi_calculator.calculate_hyperliquid_baseline_rsi(candles_5m_for_rsi, periods=14)
                
                # 2. Update RSI in real-time with current price (like Hyperliquid does)
                rsi_data = rsi_calculator.update_realtime_rsi(current_price)
                current_rsi = rsi_data.get("rsi", baseline_rsi)
                logger.debug(f"📊 Real-time RSI 14: {current_rsi:.2f} (baseline: {baseline_rsi:.2f})")
            except Exception as e:
                logger.warning(f"⚠️ RSI calculation failed: {e}")
                current_rsi = None
            
            # Get trend from the trend calculator singleton (single source)
            from core.analysis.real_time.trend_calculator import get_global_trend_calculator
            trend_calculator = get_global_trend_calculator()
            
            try:
                if len(candles_5m) >= 3:
                    # Use strategy-specific multi-timeframe trend calculation
                    trend_5m = trend_calculator.calculate_multi_timeframe_trend(candles_5m, strategy)
                    current_trend = trend_5m.get("trend_consensus", "SIDEWAYS")
                    logger.debug(f"📊 Multi-timeframe trend for {strategy}: {current_trend}")
                else:
                    trend_5m = {"trend_consensus": "SIDEWAYS", "error": "Insufficient data"}
                    current_trend = "SIDEWAYS"
                    logger.warning(f"⚠️ Not enough candles for trend calculation: {len(candles_5m)} < 3")
            except Exception as e:
                logger.warning(f"⚠️ Multi-timeframe trend calculation failed: {e}")
                trend_5m = {"trend_consensus": "SIDEWAYS", "error": str(e)}
                current_trend = "SIDEWAYS"
            
            # FIXED: Use volatility data from hyperliquid_analysis (single source of truth)
            # The volatility data is calculated in market_data_manager and passed through hyperliquid_analysis
            hyperliquid_analysis = market_data.get("hyperliquid_analysis", {})
            volatility_analysis = hyperliquid_analysis.get("volatility_analysis", {})
            volatility_5m = volatility_analysis.get("volatility_5m", 0.0)
            volatility_5m_category = volatility_analysis.get("volatility_5m_category", "UNKNOWN")
            volatility_5m_trend = volatility_analysis.get("volatility_5m_trend", "UNKNOWN")
            volatility_5m_period_minutes = volatility_analysis.get("volatility_5m_period_minutes", 15)
            volatility_5m_period_candles = volatility_analysis.get("volatility_5m_period_candles", 3)
            volatility_5m_strategy = volatility_analysis.get("volatility_5m_strategy", "standard")
            
            logger.debug(f"📊 Using volatility from hyperliquid_analysis: {volatility_5m:.6f} ({volatility_5m_category})")
            
            # Get support/resistance from hyperliquid_data (already recalculated by market_data_manager)
            support_resistance = hyperliquid_data.get("support_resistance", {})
            
            # If no S/R data available, fallback to direct calculation using centralized cache
            if not support_resistance:
                from core.analysis.real_time.support_resistance_calculator import get_global_support_resistance_calculator
                sr_calculator = get_global_support_resistance_calculator()
                
                try:
                    # Use centralized cache (100 candles) for better S/R analysis
                    # This will use the same cached data as all other requests
                    if candles_5m_for_sr and len(candles_5m_for_sr) >= 20:
                        # Use provided market data service
                        if market_data_service is None:
                            logger.error("❌ CRITICAL: No market data service provided for S/R calculation - NO FALLBACKS")
                            raise ValueError("Market data service is None - NO FALLBACKS")
                        else:
                            logger.debug(f"🔍 Market data service available: {type(market_data_service)}")
                            support_resistance = sr_calculator.calculate_multi_timeframe_levels(
                                current_price, market_data_service, candles_5m_for_sr, candles_1h, candles_1d
                            )
                        logger.debug(f"📊 S/R calculated with {len(candles_5m_for_sr)} candles from centralized cache")
                    else:
                        support_resistance = {}
                        logger.warning(f"⚠️ Insufficient candle data for S/R calculation ({len(candles_5m_for_sr) if candles_5m_for_sr else 0} candles)")
                except Exception as e:
                    logger.warning(f"⚠️ Support/Resistance calculation failed: {e}")
                    support_resistance = {}
            
            # Get pressure data from the pressure calculator singleton (single source)
            from core.analysis.real_time.pressure_calculator import get_global_pressure_calculator
            pressure_calculator = get_global_pressure_calculator()
            
            try:
                # Get orderbook data from hyperliquid_data for pressure calculation
                orderbook = hyperliquid_data.get("orderbook", {})
                
                # Handle different orderbook formats
                if "levels" in orderbook and orderbook["levels"]:
                    # Hyperliquid format: levels = [bids, asks]
                    levels = orderbook["levels"]
                    if len(levels) >= 2:
                        bids = levels[0]  # First array is bids
                        asks = levels[1]  # Second array is asks
                    else:
                        bids = []
                        asks = []
                else:
                    # Standard format: bids/asks arrays
                    bids = orderbook.get("bids", [])
                    asks = orderbook.get("asks", [])
                
                if bids and asks:
                    pressure_data = pressure_calculator.calculate_orderbook_pressure(bids, asks)
                    # Ensure all required fields are present
                    if "strength" not in pressure_data:
                        pressure_data["strength"] = abs(pressure_data.get("confidence", 0.0))
                    if "trend" not in pressure_data:
                        pressure_data["trend"] = pressure_data.get("direction", "NEUTRAL")
                    logger.debug(f"🔍 Pressure result: {pressure_data}")
                else:
                    logger.warning(f"⚠️ No orderbook data: bids={len(bids) if bids else 0}, asks={len(asks) if asks else 0}")
                    pressure_data = {"direction": "NEUTRAL", "confidence": 0.0, "strength": 0.0, "trend": "NEUTRAL"}
            except Exception as e:
                logger.warning(f"⚠️ Pressure calculation failed: {e}")
                pressure_data = {"direction": "NEUTRAL", "confidence": 0.0, "strength": 0.0, "trend": "NEUTRAL"}
            
            # Get pattern analysis from the pattern recognition engine singleton (single source)
            from core.analysis.real_time.pattern_recognition_engine import get_global_pattern_recognition_engine
            pattern_engine = get_global_pattern_recognition_engine()
            
            try:
                pattern_analysis = pattern_engine.analyze_patterns(candles_5m) if len(candles_5m) >= 1 else {}
            except Exception as e:
                logger.warning(f"⚠️ Pattern analysis failed: {e}")
                pattern_analysis = {}
            
            # Get volume profile analysis from the volume profile analyzer singleton (single source)
            from core.analysis.real_time.volume_profile_analyzer import get_global_volume_profile_analyzer
            volume_profile_analyzer = get_global_volume_profile_analyzer()
            
            try:
                volume_profile_analysis = volume_profile_analyzer.analyze_volume_profile(candles_5m, current_price) if len(candles_5m) >= 1 else {}
            except Exception as e:
                logger.warning(f"⚠️ Volume profile analysis failed: {e}")
                volume_profile_analysis = {}
            
            # Get bounce validation from the bounce validator singleton (single source)
            # REMOVED: BounceValidator doesn't have a simple validate_bounce method
            
            # Get cross-asset correlation from the cross-asset correlation analyzer singleton (single source)
            # OPTIONAL: Skip cross-asset analysis if not available (don't block main data flow)
            cross_asset_analysis = {}
            try:
                from core.analysis.real_time.cross_asset_correlation_analyzer import get_global_cross_asset_correlation_analyzer
                cross_asset_analyzer = get_global_cross_asset_correlation_analyzer()
                cross_asset_analysis = cross_asset_analyzer.analyze_cross_asset_correlations(current_price) if current_price else {}
            except Exception as e:
                logger.warning(f"⚠️ Cross-asset correlation analysis skipped - real data not available: {e}")
                cross_asset_analysis = {"error": "Real cross-asset data not available", "data_source": "skipped"}
            
            # Get funding rate analysis from the funding rate analyzer singleton (single source)
            # OPTIONAL: Skip funding rate analysis if not available (don't block main data flow)
            funding_analysis = {}
            try:
                from core.analysis.real_time.funding_rate_analyzer import get_global_funding_rate_analyzer
                funding_rate_analyzer = get_global_funding_rate_analyzer()
                
                # Get funding data from market data
                funding_data = market_data.get("hyperliquid_data", {}).get("funding_rate", {})
                if funding_data:
                    funding_analysis = funding_rate_analyzer.analyze_funding_rate(funding_data)
                else:
                    funding_analysis = {"error": "No funding rate data available", "data_source": "skipped"}
            except Exception as e:
                logger.warning(f"⚠️ Funding rate analysis skipped - real data not available: {e}")
                funding_analysis = {"error": "Real funding rate data not available", "data_source": "skipped"}
            
            # On-Chain Data & Psychological Levels features removed - not implemented
            
            # Get market conditions from the market conditions analyzer singleton (single source)
            from core.analysis.real_time.market_conditions_analyzer import global_conditions_analyzer
            
            try:
                market_conditions_analysis = global_conditions_analyzer.analyze_trading_conditions(market_data, candles_1d=candles_1d) if market_data else {}
            except Exception as e:
                logger.warning(f"⚠️ Market conditions analysis failed: {e}")
                market_conditions_analysis = {}
            
            # Chart data is handled by dashboard/frontend - not part of trading logic
            # Dashboard will fetch its own chart data when needed
            
            # Get multi-timeframe volatility data for dashboard compatibility
            multi_volatility_data = get_global_volatility_calculator().calculate_multi_timeframe_volatility_for_strategy(candles_5m, strategy)
            
            # Create unified data structure that both Signal Aggregator and Dashboard can use
            unified_data = {
                # Core price data
                "current_price": current_price,
                
                # RSI data (RSI 14 only)
                "rsi": current_rsi,
                
                # RSI analysis data (from RSI calculator)
                "rsi_analysis": rsi_data if 'rsi_data' in locals() else {},
                
                # Trend data (from single trend calculator source with strategy-specific periods)
                "trend": current_trend,
                "trend_5m": trend_5m,
                "trend_periods_display": trend_5m.get("periods_used", {}) if isinstance(trend_5m, dict) else {},
                
                # Dashboard-compatible trend fields with strategy periods
                "trends": {
                    "trend_short": trend_5m.get("reaction_trend", "SIDEWAYS") if isinstance(trend_5m, dict) else "SIDEWAYS",
                    "trend_medium": trend_5m.get("primary_trend", "SIDEWAYS") if isinstance(trend_5m, dict) else "SIDEWAYS", 
                    "trend_long": trend_5m.get("confirmation_trend", "SIDEWAYS") if isinstance(trend_5m, dict) else "SIDEWAYS",
                    "periods": trend_5m.get("periods_used", {}) if isinstance(trend_5m, dict) else {}
                },
                
                # Multi-timeframe trend data - NOT CALCULATED (removed duplicates)
                # "trend_1m": hyperliquid_analysis.get("trend_1m", {}),  # NOT CALCULATED
                # "trend_1h": hyperliquid_analysis.get("trend_1h", {}),  # NOT CALCULATED  
                # "trend_1d": hyperliquid_analysis.get("trend_1d", {}),  # NOT CALCULATED
                
                # Volatility trend data
                "volatility_5m_trend": volatility_5m_trend,
                
                # Additional trend data from market data manager
                "trend_analysis": hyperliquid_analysis.get("trend_analysis", {}),
                "pattern_analysis": hyperliquid_analysis.get("pattern_analysis", {}),
                "market_conditions": hyperliquid_analysis.get("market_conditions", {}),
                
                # Volatility data (from single volatility calculator source)
                "volatility_5m": volatility_5m,
                "volatility_category": volatility_5m_category,  # Fixed: strategy manager expects 'volatility_category'
                "volatility_5m_category": volatility_5m_category,  # Keep for backward compatibility
                "volatility_5m_trend": volatility_5m_trend,
                
                # Multi-timeframe volatility (calculated in VolatilityCalculator - SRP compliant)
                **multi_volatility_data,
                
                # Dashboard-compatible volatility period fields
                "volatility_5m_period_minutes": multi_volatility_data.get("primary_period", "15min").replace("min", ""),
                "volatility_5m_period_candles": int(multi_volatility_data.get("primary_period", "15min").replace("min", "")) // 5,
                "volatility_strategy": strategy,
                
                # Real-time volatility change detection (for immediate alerts and strategy switching)
                "volatility_change_detection": get_global_volatility_calculator().detect_volatility_change(candles_5m, "5m") if len(candles_5m) >= 4 else {"change_detected": False, "change_direction": "NONE"},
                
                # Multi-timeframe volatility data
                "volatility_1m": get_global_volatility_calculator().calculate_candle_volatility(candles_1m, "1m", "standard") if len(candles_1m) >= 1 else {"volatility": 0.0, "period_minutes": 1, "period_candles": 1, "strategy": "standard", "timeframe": "1m"},
                "volatility_1h": get_global_volatility_calculator().calculate_candle_volatility(candles_1h, "1h", "standard") if len(candles_1h) >= 1 else {"volatility": 0.0, "period_minutes": 60, "period_candles": 1, "strategy": "standard", "timeframe": "1h"},
                "volatility_1d": get_global_volatility_calculator().calculate_candle_volatility(candles_1d, "1d", "standard") if len(candles_1d) >= 1 else {"volatility": 0.0, "period_minutes": 1440, "period_candles": 1, "strategy": "standard", "timeframe": "1d"},
                
                # Volume data (from single MarketDataService source)
                "volume_data": volume_data,
                "volume_category": volume_data.get("volume_category"),
                
                # Binance global volume data
                "binance_volume_data": binance_volume_data,
                
            # Analysis data (from single calculator sources)
            "pressure_data": pressure_data,  # Calculated by pressure calculator
            "orderbook_analysis": orderbook,
            "funding_analysis": funding_analysis,  # Calculated by funding rate analyzer
            "pattern_analysis": pattern_analysis,  # Calculated by pattern recognition engine
            "volume_profile_analysis": volume_profile_analysis,  # Calculated by volume profile analyzer
            "cross_asset_analysis": cross_asset_analysis,  # Calculated by cross-asset analyzer
            "market_conditions_analysis": market_conditions_analysis,  # Calculated by market conditions analyzer
            "support_resistance": support_resistance,
            
                # Chart data removed - dashboard handles its own chart data
                
                # Time snapshot (using TimeUtils - SRP compliant)
                "timestamp": time.time(),
                "time_snapshot": self._create_time_snapshot()
            }
            
            # Store for both Signal Aggregator and Dashboard access
            self.unified_market_data = unified_data
            
            logger.debug(f"📊 Unified market data prepared: RSI={unified_data.get('rsi')}, Trend={unified_data.get('trend')}")
            
            return unified_data
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare unified market data: {e}")
            return {}
    
    def _create_time_snapshot(self) -> Dict[str, Any]:
        """Create time snapshot using TimeUtils"""
        from core.utils.time_utils import create_time_snapshot
        session_start_time = getattr(self, 'session_start_time', None)
        return create_time_snapshot(session_start_time)
    
    def _handle_volatility_changes(self, unified_data: Dict[str, Any], dashboard_service):
        """Handle real-time volatility changes - PROPER SRP: Orchestration only"""
        try:
            volatility_change = unified_data.get("volatility_change_detection", {})
            
            if volatility_change.get("change_detected", False):
                # Log volatility change (orchestration responsibility)
                change_direction = volatility_change.get("change_direction", "NONE")
                change_magnitude = volatility_change.get("change_magnitude", 0.0)
                urgency = volatility_change.get("urgency", "LOW")
                
                logger.warning(f"🚨 VOLATILITY CHANGE DETECTED: {change_direction} ({change_magnitude:+.1%}) - Urgency: {urgency}")
                
                # DELEGATE to VolatilityCalculator for alerts (SRP compliant)
                volatility_calculator = get_global_volatility_calculator()
                alerts = volatility_calculator.get_volatility_alerts(volatility_change)
                
                # Process alerts (orchestration responsibility)
                for alert in alerts:
                    dashboard_service.add_activity(alert["message"], "WARNING" if alert["urgency"] in ["HIGH", "CRITICAL"] else "INFO")
                    
                    # Trigger immediate update for critical alerts
                    if alert["urgency"] == "CRITICAL":
                        dashboard_service._trigger_websocket_emission()
                        logger.info("⚡ Triggered immediate dashboard update for critical volatility change")
                
                # DELEGATE to VolatilityCalculator for strategy suggestions (SRP compliant)
                current_strategy = unified_data.get("current_strategy", "standard")
                strategy_suggestion = volatility_calculator.should_suggest_strategy_change(volatility_change, current_strategy)
                
                # Process strategy suggestion (orchestration responsibility)
                if strategy_suggestion:
                    suggestion_message = f"💡 {strategy_suggestion['reason']} - {strategy_suggestion['suggested_strategy']} recommended"
                    dashboard_service.add_activity(suggestion_message, "INFO")
                    logger.warning(f"💡 STRATEGY SUGGESTION: {strategy_suggestion['suggested_strategy']} ({strategy_suggestion['confidence']:.1%} confidence)")
                
        except Exception as e:
            logger.error(f"❌ Volatility change orchestration failed: {e}")
    
    def _update_dashboard_with_unified_data(self, unified_data: Dict[str, Any], dashboard_service):
        """Update dashboard using unified market data structure"""
        try:
            # Import volume calculator for categorization
            from core.analysis.real_time.volume_calculator import get_global_volume_calculator
            volume_calculator = get_global_volume_calculator()
            
            # Extract dashboard-specific data from unified structure
            # Map unified data to dashboard-expected field names
            dashboard_market_data = {
                "price": unified_data.get("current_price"),
                "current_price": unified_data.get("current_price"),
                "rsi": unified_data.get("rsi"),
                
                # Debug: Log RSI values being sent to dashboard
                "debug_rsi_source": "unified_data",
                "debug_rsi_value": unified_data.get("rsi"),
                
                # Dashboard expects trend_analysis.overall_trend for Overall Trend
                "trend_analysis": {
                    "overall_trend": unified_data.get("trend"),
                    "trend_5m": unified_data.get("trend_5m")
                },
                
                # TRENDS SECTION - Trend calculator values only
                "trends": {
                    "trend": unified_data.get("trend_5m", {}).get("trend", "UNKNOWN"),
                    "trend_short": unified_data.get("trend_5m", {}).get("trend_short", "UNKNOWN"),
                    "trend_medium": unified_data.get("trend_5m", {}).get("trend_medium", "UNKNOWN")
                },
                
                # Debug: Log trends data being sent to dashboard
                "debug_trends": {
                    "trend_5m_data": unified_data.get("trend_5m", {}),
                    "trends_section": {
                        "trend": unified_data.get("trend_5m", {}).get("trend", "UNKNOWN"),
                        "trend_short": unified_data.get("trend_5m", {}).get("trend_short", "UNKNOWN"),
                        "trend_medium": unified_data.get("trend_5m", {}).get("trend_medium", "UNKNOWN")
                    }
                },
                
                # Dashboard expects trading_volume_btc for Trading Volume (Hyperliquid 5m volume)
                "trading_volume_btc": unified_data.get("volume_data", {}).get("current_volume_btc", 0) or unified_data.get("volume_data", {}).get("real_time_volume_btc", 0),
                "trading_volume_category": unified_data.get("volume_data", {}).get("volume_category") or unified_data.get("volume_category"),
                "data_source": unified_data.get("volume_data", {}).get("data_source", "hyperliquid_candles"),
                
                # Binance global volume data
                "global_volume_btc_per_min": unified_data.get("binance_volume_data", {}).get("current_volume_btc", 0.0),
                "global_volume_category": volume_calculator.categorize_global_volume(unified_data.get("binance_volume_data", {}).get("current_volume_btc", 0.0)),
                "global_volume_source": "binance_websocket",
                
                "volatility_5m": unified_data.get("volatility_5m"),
                "volatility_5m_category": unified_data.get("volatility_5m_category"),
                "volume_data": unified_data.get("volume_data", {}),
                "pressure_data": unified_data.get("pressure_data", {}),
                "orderbook_analysis": unified_data.get("orderbook_analysis", {}),
                "pattern_analysis": unified_data.get("pattern_analysis", {}),
                "support_resistance": unified_data.get("support_resistance", {}),
                "time_snapshot": unified_data.get("time_snapshot", {}),
                "timestamp": unified_data.get("timestamp"),
                
                # Additional singleton metrics for dashboard
                "volume_profile_analysis": unified_data.get("volume_profile_analysis", {}),
                "cross_asset_analysis": unified_data.get("cross_asset_analysis", {}),
                "funding_analysis": unified_data.get("funding_analysis", {}),
                "onchain_analysis": unified_data.get("onchain_analysis", {}),
                "bounce_analysis": unified_data.get("bounce_analysis", {}),
                "psychological_analysis": unified_data.get("psychological_analysis", {}),
                "market_conditions_analysis": unified_data.get("market_conditions_analysis", {}),
                
                # CRITICAL FIX: JavaScript looks for "market_conditions" NOT "market_conditions_analysis"
                "market_conditions": unified_data.get("market_conditions_analysis", {}),
                
                # Strategy-specific period information for dashboard display
                "strategy_periods": {
                    "trend": unified_data.get("trend_periods_display", {}),
                    "volatility": unified_data.get("periods_used", {}),
                    "strategy": unified_data.get("current_strategy", "standard")
                },
                
                # Chart data
                "chart_data": unified_data.get("chart_data", {}),
                "candles": unified_data.get("candles", {}),
                
                # Dashboard expects these specific field names
                "support_levels": unified_data.get("support_levels", []),
                "resistance_levels": unified_data.get("resistance_levels", []),
                "key_levels": unified_data.get("support_resistance", {}).get("key_levels", []),
                "support_resistance": unified_data.get("support_resistance", {}),
                "patterns": unified_data.get("pattern_analysis", {}).get("patterns", {}),
                "overall_confidence": unified_data.get("pattern_analysis", {}).get("overall_confidence", 0.0),
                "market_setup": unified_data.get("pattern_analysis", {}).get("market_setup", {}),
                
                # Add pressure data for dashboard display - use default values if pressure_data is empty
                "pressure": unified_data.get("pressure_data", {}).get("direction", "NEUTRAL"),
                "pressure_confidence": unified_data.get("pressure_data", {}).get("confidence", 0.0),
                
                # Add direct trend field for dashboard
                "trend": unified_data.get("trend"),
                "volume_category": unified_data.get("volume_category")
            }
            
            # Update dashboard with unified data
            dashboard_service.update_market_data(dashboard_market_data)
            
            current_price = unified_data.get('current_price', 0)
            rsi_value = unified_data.get('rsi')
            price_display = f"${current_price:,.2f}" if current_price else "N/A"
            rsi_display = f"{rsi_value:.1f}" if rsi_value is not None else "N/A"
            logger.debug(f"📊 Dashboard updated with unified data: Price={price_display}, RSI={rsi_display}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update dashboard with unified data: {e}")
    
    def _generate_price_prediction(self, unified_data: Dict[str, Any], strategy: str):
        """Update singleton prediction based on real-time market conditions"""
        try:
            from core.ml.realtime_prediction_engine import get_global_realtime_prediction_engine
            
            prediction_engine = get_global_realtime_prediction_engine()
            
            # Update singleton prediction with current market data
            action = prediction_engine.update_prediction(unified_data, strategy)
            
            # Get the active prediction (singleton)
            active_prediction = prediction_engine.get_active_prediction()
            
            if action == "EXECUTE":
                # Ready to execute!
                logger.success(f"🔮 EXECUTE: {active_prediction.direction} @ ${active_prediction.entry_price:,.2f}")
                logger.success(f"   Confidence: {active_prediction.confidence:.1%} ✅")
                logger.info(f"   Stop Loss: ${active_prediction.stop_loss:,.2f} | Take Profit: ${active_prediction.take_profit:,.2f}")
                
                # Store for trading engine
                self.current_prediction = active_prediction
                
                # Update dashboard
                self._update_dashboard_with_prediction(active_prediction)
                
                # Execute limit order via PredictionExecutor
                try:
                    from core.execution.prediction_executor import get_global_prediction_executor
                    from core.services.system_initializer import get_system_initializer
                    
                    system_initializer = get_system_initializer()
                    trading_execution = system_initializer.singleton_systems.get("trading_execution")
                    account_manager = system_initializer.singleton_systems.get("account_manager")
                    session_manager_inst = system_initializer.singleton_systems.get("session_manager")
                    
                    if all([trading_execution, account_manager, session_manager_inst]):
                        executor = get_global_prediction_executor(trading_execution, account_manager, session_manager_inst)
                        
                        # Execute prediction - convert dataclass to dict
                        from dataclasses import asdict
                        prediction_dict = asdict(active_prediction)
                        result = executor.execute_prediction(prediction_dict, strategy)
                        
                        if result.get("success"):
                            logger.success(f"✅ Trade executed successfully!")
                            prediction_engine.clear_prediction()  # Clear after successful execution
                            self.current_prediction = None
                        else:
                            logger.warning(f"⚠️ Trade execution declined: {result.get('reason')}")
                    else:
                        logger.error("❌ Required services not available for trade execution")
                        logger.debug(f"   trading_execution: {trading_execution is not None}")
                        logger.debug(f"   account_manager: {account_manager is not None}")
                        logger.debug(f"   session_manager_inst: {session_manager_inst is not None}")
                        logger.debug(f"   Available singletons: {list(system_initializer.singleton_systems.keys())}")
                        
                except Exception as e:
                    logger.error(f"❌ Trade execution error: {e}")
                
            elif action == "CREATED":
                # New prediction created
                logger.info(f"🎯 NEW prediction: {active_prediction.direction} @ ${active_prediction.entry_price:,.2f} ({active_prediction.confidence:.1%})")
                self.current_prediction = active_prediction
                self._update_dashboard_with_prediction(active_prediction)
                
            elif action == "UPDATED":
                # Prediction fields updated
                logger.debug(f"🔄 Prediction updated: {active_prediction.direction} @ ${active_prediction.entry_price:,.2f} ({active_prediction.confidence:.1%})")
                self.current_prediction = active_prediction
                self._update_dashboard_with_prediction(active_prediction)
                
            elif action == "CANCELLED":
                # Prediction cancelled
                logger.warning(f"❌ Prediction cancelled")
                self.current_prediction = None
                
            elif action == "NO_SIGNAL":
                # No clear signal
                logger.debug("📊 No clear signal - waiting for market conditions")
                self.current_prediction = None
                
            else:  # NO_CHANGE
                # Market hasn't changed significantly - skip update
                pass
            
        except Exception as e:
            logger.error(f"❌ Failed to update prediction: {e}")
            self.current_prediction = None
    
    def _update_dashboard_with_prediction(self, prediction):
        """Update dashboard with prediction data"""
        try:
            from core.services.dashboard_service import DashboardService
            dashboard_service = DashboardService.get_global_instance()
            
            if dashboard_service:
                dashboard_service.add_prediction(prediction.to_dict())
                logger.debug("📊 Dashboard updated with prediction")
                
        except Exception as e:
            logger.debug(f"⚠️ Could not update dashboard with prediction: {e}")
    
    def _detect_and_update_strategy(self, unified_data: Dict[str, Any], dashboard_service) -> str:
        """
        Detect optimal strategy based on current market conditions and historical data
        Uses ML Strategy Selector with fallback to rule-based selection
        """
        try:
            # Ensure Strategy Manager is initialized
            if not self.strategy_manager:
                from core.services.system_initializer import get_system_initializer
                system_initializer = get_system_initializer()
                self._ensure_strategy_manager_initialized(system_initializer)
            
            if not self.strategy_manager:
                logger.warning("⚠️ Strategy Manager not available - using default strategy")
                return "standard"
            
            # Get historical context from session manager
            historical_context = None
            if self.session_manager and hasattr(self.session_manager, 'get_historical_context'):
                historical_context = self.session_manager.get_historical_context()
            
            # Detect optimal strategy using ML
            optimal_strategy = self.strategy_manager.detect_optimal_strategy(
                market_data=unified_data
            )
            
            # Update session manager with new strategy
            if self.session_manager and hasattr(self.session_manager, 'current_session_data'):
                if self.session_manager.current_session_data:
                    self.session_manager.current_session_data["strategy"] = optimal_strategy
            
            return optimal_strategy
            
        except Exception as e:
            logger.error(f"❌ Strategy detection failed: {e}")
            return "standard"  # Fallback to standard strategy
    
    def _main_data_loop(self, check_interval: int, hyperliquid_api,
                       market_data_service, dashboard_service) -> Dict[str, Any]:
        """Main data collection and dashboard update loop (no trading)"""
        logger.debug(f"🔍 _main_data_loop called with market_data_service: {type(market_data_service)}")
        last_loop_time = 0
        min_loop_interval = 0.5  # Minimum 0.5 seconds between loop iterations for more responsive RSI
        last_5m_boundary = None  # Track 5-minute boundaries for immediate updates
        last_ongoing_candle = None  # Track the last ongoing candle to convert it to historical
        
        logger.info(f"🔄 Starting data collection loop (interval: {check_interval}s)")
        
        while True:
            try:
                # Update session time
                if self.session_manager:
                    self.session_manager.update_session_time_if_active()
                
                # Check for timeframe boundary changes (for immediate candle updates and cache invalidation)
                current_time = time.time()
                import datetime as dt
                current_dt = dt.datetime.fromtimestamp(current_time, tz=dt.timezone.utc)
                
                # Track multiple boundaries
                current_5m_boundary = (current_dt.minute // 5) * 5
                current_hour = current_dt.hour
                current_day = current_dt.day
                
                # Detect 5-minute boundary change
                boundary_changed_5m = False
                boundary_changed_1h = False
                boundary_changed_1d = False
                
                if last_5m_boundary is not None and current_5m_boundary != last_5m_boundary:
                    boundary_changed_5m = True
                    logger.info(f"🕐 5-minute boundary reached: {last_5m_boundary:02d}:00 -> {current_5m_boundary:02d}:00 UTC - Volume reset and new candle!")
                
                # Check for hourly boundary (at :00 of each hour)
                if hasattr(self, 'last_hour') and self.last_hour != current_hour and current_dt.minute == 0:
                    boundary_changed_1h = True
                    logger.info(f"🕐 Hourly boundary reached: {self.last_hour:02d}:00 -> {current_hour:02d}:00 UTC - New hourly candle!")
                
                # Check for daily boundary (at 00:00 UTC)
                if hasattr(self, 'last_day') and self.last_day != current_day and current_hour == 0 and current_dt.minute == 0:
                    boundary_changed_1d = True
                    logger.info(f"🕐 Daily boundary reached - New daily candle!")
                
                last_5m_boundary = current_5m_boundary
                self.last_hour = current_hour
                self.last_day = current_day
                
                # Get current price
                hyperliquid_price = market_data_service.get_hyperliquid_price()
                if not hyperliquid_price:
                    logger.warning("⚠️ Could not get Hyperliquid price, retrying...")
                    time.sleep(check_interval)
                    continue
                
                # Get market data (single source of truth)
                market_data = self._get_market_data(hyperliquid_price, market_data_service)
                if not market_data:
                    logger.warning("⚠️ Could not get market data, retrying...")
                    time.sleep(check_interval)
                    continue
                
                # STRATEGY SELECTION: Detect optimal strategy FIRST (needed for data preparation)
                # Use basic market data for strategy detection
                basic_strategy_data = {
                    "current_price": hyperliquid_price,
                    "rsi": market_data.get("rsi", 50),
                    "volatility_5m": market_data.get("hyperliquid_analysis", {}).get("volatility_analysis", {}).get("volatility_5m", 0.01),
                    "volatility_category": market_data.get("hyperliquid_analysis", {}).get("volatility_analysis", {}).get("volatility_5m_category", "MODERATE"),
                    "volume_category": market_data.get("hyperliquid_data", {}).get("volume_data", {}).get("volume_category", "MODERATE")
                }
                current_strategy = self._detect_and_update_strategy(basic_strategy_data, dashboard_service)
                
                # Prepare unified market data using current strategy for calculations
                unified_data = self._prepare_unified_market_data(market_data, hyperliquid_price, market_data_service, current_strategy)
                unified_data["current_strategy"] = current_strategy
                
                # Check for real-time volatility changes (immediate alerts and strategy switching)
                self._handle_volatility_changes(unified_data, dashboard_service)
                
                # Update dashboard with unified data
                self._update_dashboard_with_unified_data(unified_data, dashboard_service)
                
                # Handle candle boundary changes and cache invalidation
                if boundary_changed_5m:
                    logger.info("🔄 Forcing immediate dashboard update due to 5-minute boundary change")
                    
                    # INVALIDATE 5m CANDLE CACHE - New candle period started
                    market_data_service.invalidate_candle_cache("BTC", "5m")
                    logger.info("🗑️ Invalidated 5m candle cache - Next request will fetch fresh data with completed candle")
                    
                    # Also invalidate S/R cache since new 5m candle might change levels
                    from core.market_data_manager import get_global_market_data_manager
                    market_data_manager = get_global_market_data_manager()
                    market_data_manager.invalidate_sr_cache()
                    logger.info("🗑️ Invalidated S/R cache - New 5m candle may change support/resistance levels")
                    
                    # Also invalidate 1m cache as it should update every 5 minutes
                    market_data_service.invalidate_candle_cache("BTC", "1m")
                    
                    # Clear old trades from WebSocket cache to ensure clean volume reset
                    if market_data_service.hyperliquid_websocket:
                        from core.utils.time_utils import get_5m_candle_start_time
                        cutoff_timestamp = get_5m_candle_start_time(current_time)
                        market_data_service.hyperliquid_websocket.clear_old_trades(cutoff_timestamp)
                    
                    # Trigger additional WebSocket emission for immediate update
                    dashboard_service._trigger_websocket_emission()
                
                # Handle hourly boundary
                if boundary_changed_1h:
                    logger.info("🔄 Hourly boundary detected - Invalidating 1h candle cache")
                    market_data_service.invalidate_candle_cache("BTC", "1h")
                    logger.info("🗑️ Invalidated 1h candle cache - Next request will fetch fresh hourly data")
                
                # Handle daily boundary
                if boundary_changed_1d:
                    logger.info("🔄 Daily boundary detected - Invalidating 1d candle cache")
                    market_data_service.invalidate_candle_cache("BTC", "1d")
                    logger.info("🗑️ Invalidated 1d candle cache - Next request will fetch fresh daily data")
                
                # Generate price prediction
                self._generate_price_prediction(unified_data, current_strategy)
                
                # Update order lifecycle (check fills, update positions, etc.)
                self._update_order_lifecycle(hyperliquid_price)
                
                # Simple monitoring log - use real-time RSI from unified data
                rsi_value = market_data.get('rsi')
                rsi_display = f"{rsi_value:.1f}" if rsi_value is not None else "Loading"
                
                dashboard_service.add_activity(
                    f"📊 Data: ${hyperliquid_price:.2f}, RSI: {rsi_display}", 
                    "INFO"
                )
                
                # Performance throttling - ensure minimum interval between loops
                current_time = time.time()
                elapsed = current_time - last_loop_time
                if elapsed < min_loop_interval:
                    sleep_time = min_loop_interval - elapsed
                    logger.debug(f"⏱️ Throttling loop - sleeping {sleep_time:.2f}s to prevent spam")
                    time.sleep(sleep_time)
                last_loop_time = time.time()
                
                # Wait for next iteration
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Keyboard interrupt - stopping trading loop")
                break
            except Exception as e:
                logger.error(f"❌ Trading loop error: {e}")
                # NO FALLBACKS - Critical errors must stop the system
                if "NO FALLBACKS" in str(e) or "Volume data" in str(e):
                    logger.error(f"❌ CRITICAL ERROR - Stopping trading loop: {e}")
                    break
                time.sleep(check_interval)
        
        # End session only on keyboard interrupt
        self._end_session(dashboard_service)
        
        return {
            "success": True,
            "trades_placed": 0,
            "signals_prepared": 0,
            "session_complete": True
        }
    
    def _end_session(self, dashboard_service):
        """End trading session gracefully"""
        try:
            # End session
            if self.session_manager:
                self.session_manager.end_session()
                logger.info("📅 SessionManager session ended")
            
            # Cleanup heartbeat
            dashboard_service.cleanup_heartbeat()
            
            # Log session end
            dashboard_service.add_activity("🏁 Trading session closed gracefully", "SUCCESS")
            
            logger.success("✅ Session ended gracefully")
            
        except Exception as e:
            logger.error(f"❌ Error ending session: {e}")
    
    def _check_for_ongoing_session(self) -> Optional[Dict]:
        """Check for ongoing sessions"""
        try:
            if self.session_manager:
                return self.session_manager.get_current_session_info()
            return None
        except Exception as e:
            logger.error(f"❌ Failed to check for ongoing session: {e}")
            return None
    
    def _build_complete_market_data(self, hyperliquid_data: Dict[str, Any], 
                                   hyperliquid_price: float, hyperliquid_analysis: Dict[str, Any], 
                                   hyperliquid_api=None, strategy_name: str = "standard", 
                                   conditions_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build complete market data structure for AI system with all required fields"""
        try:
            # Start with hyperliquid data
            complete_data = hyperliquid_data.copy()
            
            # Add missing fields that strategy selector expects
            complete_data.update({
                # Price data
                "current_price": hyperliquid_price,
                
                # Technical indicators - RSI is already set correctly in unified_data, don't overwrite
                
                # Volatility data - use correct nested structure
                "volatility_5m": hyperliquid_analysis.get("volatility_analysis", {}).get("volatility_5m", 0.001),
                "volatility_5m_category": hyperliquid_analysis.get("volatility_analysis", {}).get("volatility_5m_category", "LOW"),
                "volatility_5m_trend": hyperliquid_analysis.get("volatility_analysis", {}).get("volatility_5m_trend"),
                
                # Trend data (only from actual trend calculator)
                "trend_5m": trend_5m,  # Use actual calculated trend
                "trend_analysis": {
                    "overall_trend": current_trend,
                    "trend_5m": current_trend,
                    "alignment_score": 0.5
                },
                
                # Volume data
                "hyperliquid_volume": hyperliquid_data.get("volume_data", {}),
                
                # Sentiment data - Using Yahoo Finance
                "sentiment_data": hyperliquid_analysis.get("sentiment_data", {}),
                
                # External data - Using Yahoo Finance
                "whale_analytics": hyperliquid_analysis.get("whale_analytics", {}),
                "news_sentiment": hyperliquid_analysis.get("news_sentiment", {}),
                
                # Support/Resistance data - use cached data from main loop
                "support_resistance": {"key_levels": []},  # Will be populated by main loop
                
                # Volatility change detection
                "volatility_change": {
                    "change_detected": False,
                    "change_direction": "STABLE",
                    "urgency": "LOW"
                },
                
                # Market conditions (required by analysis layer)
                "market_conditions": {
                    "condition": "FAIR",
                    "risk_level": "MODERATE", 
                    "market_status": hyperliquid_analysis.get("trend_5m", {}).get("trend")
                }
            })
            
            return complete_data
            
        except Exception as e:
            logger.error(f"❌ Failed to build complete market data: {e}")
            # Return minimal data structure
            return {
                "current_price": hyperliquid_price,
                # RSI is already set correctly in unified_data, don't overwrite
                "volatility_5m": hyperliquid_analysis.get("volatility_analysis", {}).get("volatility_5m"),
                "volatility_5m_category": hyperliquid_analysis.get("volatility_analysis", {}).get("volatility_5m_category"),
                "trend_5m": hyperliquid_analysis.get("trend_5m"),
                "hyperliquid_volume": {},
                "sentiment_data": {},
                "whale_analytics": {},
                "news_sentiment": {},
                "support_resistance": {"key_levels": []},
                "volatility_change": {"error": "Real volatility change not implemented - NO FALLBACKS", "data_source": "failed"},
                "market_conditions": {
                    "error": "Real market conditions not implemented - NO FALLBACKS",
                    "data_source": "failed"
                }
            }
    
    def _get_market_data(self, current_price: float, market_data_service) -> Dict[str, Any]:
        """Get all market data once - single source of truth (delegates to proper services)"""
        try:
            logger.debug(f"🔍 _get_market_data called with market_data_service: {type(market_data_service)}")
            
            # DELEGATE: Get market analysis from MarketDataService
            hyperliquid_analysis = market_data_service.get_hyperliquid_analysis(current_price)
            if not hyperliquid_analysis or "error" in hyperliquid_analysis:
                return None
            
            # DELEGATE: Get ALL market data from MarketDataService (includes orderbook)
            hyperliquid_data = market_data_service.get_all_market_data("BTC")
            if not hyperliquid_data or "error" in hyperliquid_data:
                return None
            
            # Fetch 1d candles for market conditions analyzer
            candles_1d = market_data_service.get_historical_candles("BTC", "1d", 7)
            
            # DELEGATE: Get market conditions from MarketConditionsAnalyzer
            from core.analysis.real_time.market_conditions_analyzer import global_conditions_analyzer
            market_conditions = global_conditions_analyzer.analyze_trading_conditions(
                hyperliquid_analysis, hyperliquid_data, candles_1d
            )
            # Market conditions calculated successfully
            
            # Combine all data into single source of truth
            return {
                "hyperliquid_analysis": hyperliquid_analysis,
                "hyperliquid_data": hyperliquid_data,
                "market_conditions": market_conditions,
                "current_price": current_price,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            return None

    # REMOVED: _should_generate_new_prediction - not needed in single prediction system
    
    def _calculate_real_time_support_resistance(self, hyperliquid_api, current_price: float, strategy_name: str, market_data_service=None) -> Dict[str, Any]:
        """
        Calculate real-time support/resistance levels.
        
        REFACTORED: This method now delegates to SupportResistanceCalculator.calculate_multi_timeframe_levels()
        All logic for multi-timeframe analysis, caching, and expansion is now in the calculator.
        """
        try:
            from core.analysis.real_time.support_resistance_calculator import get_global_support_resistance_calculator
            sr_calculator = get_global_support_resistance_calculator()
            
            # All orchestration logic moved to calculator
            return sr_calculator.calculate_multi_timeframe_levels(current_price, market_data_service)
            
        except Exception as e:
            logger.error(f"❌ Real-time support/resistance calculation failed: {e}")
            # NO FALLBACKS - raise the exception
            raise Exception(f"Support/resistance calculation failed: {e}")
    
    def _update_order_lifecycle(self, current_price: float):
        """
        Update order lifecycle - check fills, update positions, handle closures
        
        Args:
            current_price: Current market price for order fill checks
        """
        try:
            # Get lifecycle managers
            from core.execution.order_lifecycle_manager import get_global_order_lifecycle_manager
            from core.execution.prediction_state_manager import get_global_prediction_state_manager
            from core.services.dashboard_service import DashboardService
            
            lifecycle_manager = get_global_order_lifecycle_manager()
            state_manager = get_global_prediction_state_manager()
            dashboard = DashboardService.get_global_instance()
            
            # Check for order fills
            filled_orders = lifecycle_manager.check_order_fills(current_price)
            
            # Handle filled orders
            for order_id in filled_orders:
                try:
                    # Get order data
                    order = lifecycle_manager.filled_orders.get(order_id)
                    if not order:
                        continue
                    
                    # Find corresponding prediction
                    prediction = state_manager.get_prediction_by_order_id(order_id)
                    if prediction:
                        # Create position
                        position_id = f"pos_{order_id.split('_')[-1]}"
                        state_manager.fill_order(prediction.prediction_id, position_id)
                        
                        # Update dashboard with FILLED status
                        if dashboard:
                            trade_display = {
                                "type": "LIMIT",
                                "side": order.side,
                                "status": "FILLED",
                                "entry_price": order.filled_price,
                                "size": order.size,
                                "stop_loss": order.stop_loss,
                                "take_profit": order.take_profit,
                                "confidence": order.confidence,
                                "expected_value": order.expected_value,
                                "strategy": order.strategy,
                                "prediction_id": prediction.prediction_id,
                                "order_id": order_id,
                                "position_id": position_id,
                                "timestamp": order.filled_at
                            }
                            dashboard.add_trade(trade_display)
                            
                        logger.info(f"✅ ORDER FILLED: {order.side} {order.size} BTC @ ${order.filled_price:,.2f}")
                        
                except Exception as e:
                    logger.error(f"❌ Error handling filled order {order_id}: {e}")
            
            # Update position prices and check for exits
            closed_positions = lifecycle_manager.update_position_prices(current_price)
            
            # Handle closed positions
            for position_id in closed_positions:
                try:
                    # Find the position in closed positions
                    closed_position = None
                    for pos in lifecycle_manager.closed_positions:
                        if pos.position_id == position_id:
                            closed_position = pos
                        break
                    
                    if not closed_position:
                        continue
                    
                    # Find corresponding prediction
                    prediction = state_manager.get_prediction_by_position_id(position_id)
                    if prediction:
                        # Complete the prediction
                        state_manager.complete_prediction(
                            prediction.prediction_id,
                            closed_position.unrealized_pnl,
                            closed_position.exit_reason
                        )
                        
                        # Update dashboard with CLOSED status
                        if dashboard:
                            trade_display = {
                                "type": "LIMIT",
                                "side": closed_position.side,
                                "status": "CLOSED",
                                "entry_price": closed_position.entry_price,
                                "exit_price": closed_position.exit_price,
                                "size": closed_position.size,
                                "pnl": closed_position.unrealized_pnl,
                                "exit_reason": closed_position.exit_reason,
                                "strategy": closed_position.strategy,
                                "prediction_id": prediction.prediction_id,
                                "position_id": position_id,
                                "timestamp": closed_position.closed_at
                            }
                            dashboard.add_trade(trade_display)
                            
                        logger.info(f"🏁 POSITION CLOSED: {closed_position.side} {closed_position.size} BTC @ ${closed_position.exit_price:,.2f} (P&L: ${closed_position.unrealized_pnl:,.2f})")
                        
                except Exception as e:
                    logger.error(f"❌ Error handling closed position {position_id}: {e}")
            
            # Update dashboard with current order/position data from simulator
            if dashboard:
                # Get data from HyperliquidSimulator (single source of truth for positions)
                from core.services.system_initializer import get_system_initializer
                system_initializer = get_system_initializer()
                simulator = system_initializer.singleton_systems.get("hyperliquid_simulator")
                
                if simulator:
                    logger.debug(f"🔍 Using simulator for trade data")
                    # Get all positions from simulator
                    open_positions = simulator.get_open_positions()
                    closed_positions = simulator.get_closed_positions(limit=100)
                    account_state = simulator.get_account_state()
                    logger.debug(f"🔍 Simulator data: {len(open_positions)} open, {len(closed_positions)} closed")
                    
                    # Convert simulator positions to dashboard format
                    all_trades = []
                    
                    # Add open positions
                    for position in open_positions:
                        trade_data = {
                            "type": "LIMIT",
                            "side": position.get("side", "BUY"),
                            "status": "OPEN",
                            "entry_price": position.get("entry_price", 0),
                            "size": position.get("size", 0),
                            "leverage": position.get("leverage", 40),
                            "stop_loss": position.get("stop_loss"),
                            "take_profit": position.get("take_profit"),
                            "trade_id": position.get("trade_id", ""),
                            "position_id": position.get("trade_id", ""),  # Use trade_id as position_id
                            "timestamp": position.get("entry_time", time.time()),
                            "strategy": position.get("strategy", "standard"),
                            "confidence": position.get("confidence", 0.0),
                            "pnl": "N/A",  # Will be calculated by dashboard
                            "entry_time": position.get("entry_time", time.time())
                        }
                        all_trades.append(trade_data)
                    
                    # Add closed positions
                    for position in closed_positions:
                        trade_data = {
                            "type": "LIMIT",
                            "side": position.get("side", "BUY"),
                            "status": "CLOSED",
                            "entry_price": position.get("entry_price", 0),
                            "exit_price": position.get("exit_price", 0),
                            "size": position.get("size", 0),
                            "leverage": position.get("leverage", 40),
                            "stop_loss": position.get("stop_loss"),
                            "take_profit": position.get("take_profit"),
                            "trade_id": position.get("trade_id", ""),
                            "position_id": position.get("trade_id", ""),  # Use trade_id as position_id
                            "timestamp": position.get("exit_time", time.time()),
                            "strategy": position.get("strategy", "standard"),
                            "confidence": position.get("confidence", 0.0),
                            "pnl": position.get("net_pnl", 0.0),
                            "exit_reason": position.get("exit_reason", "MANUAL"),
                            "entry_time": position.get("entry_time", time.time()),
                            "exit_time": position.get("exit_time", time.time())
                        }
                        all_trades.append(trade_data)
                    
                    # Update dashboard trade history with simulator data
                    dashboard.update_trade_history(all_trades)
                    
                    # Sync account manager with simulator data
                    from core.simulated_account_manager import account_manager
                    if account_manager.account_data:
                        # Update account balance and stats from simulator
                        account_manager.account_data["current_balance"] = account_state.get("balance", 0)
                        account_manager.account_data["total_trades"] = account_state.get("total_trades", 0)
                        account_manager.account_data["winning_trades"] = account_state.get("winning_trades", 0)
                        account_manager.account_data["losing_trades"] = account_state.get("losing_trades", 0)
                        account_manager.account_data["realized_pnl"] = account_state.get("realized_pnl", 0)
                        account_manager.account_data["unrealized_pnl"] = account_state.get("unrealized_pnl", 0)
                        account_manager.account_data["total_pnl"] = account_state.get("realized_pnl", 0)
                        
                        # Update open positions from simulator
                        account_manager.account_data["open_positions"] = open_positions
                        
                        # Update trade history from simulator closed positions
                        simulator_trades = []
                        for position in closed_positions:
                            trade_record = {
                                "trade_id": position.get("trade_id", ""),
                                "side": position.get("side", "BUY"),
                                "entry_price": position.get("entry_price", 0),
                                "exit_price": position.get("exit_price", 0),
                                "size": position.get("size", 0),
                                "leverage": position.get("leverage", 40),
                                "pnl": position.get("net_pnl", 0.0),
                                "pnl_pct": position.get("pnl_pct", 0.0) * 100,  # Convert to percentage
                                "exit_reason": position.get("exit_reason", "MANUAL"),
                                "entry_time": position.get("entry_time", time.time()),
                                "exit_time": position.get("exit_time", time.time()),
                                "strategy": position.get("strategy", "standard"),
                                "fees": position.get("fees", {}).get("fee_amount", 0.0) if isinstance(position.get("fees"), dict) else 0.0,
                                "was_profitable": position.get("was_profitable", False)
                            }
                            simulator_trades.append(trade_record)
                        
                        # Update trade history with simulator trades (keep last 100)
                        account_manager.account_data["trade_history"] = simulator_trades[-100:]
                        
                        # Save account data
                        account_manager.save_account()
                        
                        logger.debug(f"📊 Account manager synced with simulator: {len(simulator_trades)} trades, Balance: ${account_state.get('balance', 0):,.2f}")
                    
                    # Also sync account data to dashboard
                    dashboard.sync_from_account_manager({
                        "balance": account_state.get("balance", 0),
                        "equity": account_state.get("equity", 0),
                        "unrealized_pnl": account_state.get("unrealized_pnl", 0),
                        "realized_pnl": account_state.get("realized_pnl", 0),
                        "open_positions_count": account_state.get("open_positions_count", 0),
                        "total_trades": account_state.get("total_trades", 0),
                        "win_rate": account_state.get("win_rate", 0),
                        "winning_trades": account_state.get("winning_trades", 0),
                        "losing_trades": account_state.get("losing_trades", 0)
                    })
                    
            else:
                    # Fallback to lifecycle manager if simulator not available
                    lifecycle_data = lifecycle_manager.get_dashboard_data()
                    state_data = state_manager.get_dashboard_data()
                    
                    # Combine all trades for dashboard
                    all_trades = []
                    all_trades.extend(lifecycle_data.get("pending_orders", []))
                    all_trades.extend(lifecycle_data.get("filled_orders", []))  # ADDED: Include filled orders
                    all_trades.extend(lifecycle_data.get("active_positions", []))
                    all_trades.extend(lifecycle_data.get("closed_positions", []))
                    
                    # Update dashboard trade history
                    dashboard.update_trade_history(all_trades)
            
        except Exception as e:
            logger.error(f"❌ Order lifecycle update failed: {e}")
    
    
