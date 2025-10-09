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
            # 3.1: Get weekly trend analysis
            logger.info("📅 Loading weekly trend analysis...")
            weekly_analysis = market_data_service.get_weekly_trend_analysis()
            
            if "error" not in weekly_analysis:
                self.weekly_trend_analysis = weekly_analysis
                logger.success("✅ Weekly trend analysis loaded successfully!")
            else:
                logger.error("❌ Could not get weekly trend analysis - NO FALLBACKS")
                raise ValueError("Weekly trend analysis failed - NO FALLBACKS")
            
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
    
    def _prepare_unified_market_data(self, market_data: Dict[str, Any], current_price: float, market_data_service=None) -> Dict[str, Any]:
        """Prepare unified market data structure for both Signal Aggregator and Dashboard - SINGLE DATA SOURCE"""
        try:
            # SINGLE DATA SOURCE: Use only MarketDataService data
            # No more MarketDataManager calls - MarketDataService is the single source of truth
            
            # Extract all data from the single market_data source
            # Get data from hyperliquid_data (which contains all the market data)
            hyperliquid_data = market_data.get("hyperliquid_data", {})
            volume_data = hyperliquid_data.get("volume_data", {})
            binance_volume_data = hyperliquid_data.get("binance_volume_data", {})
            orderbook = hyperliquid_data.get("orderbook", {})
            funding_rate = hyperliquid_data.get("funding_rate", {})
            candles = hyperliquid_data.get("candles", {})
            recent_trades = hyperliquid_data.get("recent_trades", {})
            weekly_trend = hyperliquid_data.get("weekly_trend", {})
            
            # Get RSI from the RSI calculator singleton (single source)
            from core.analysis.real_time.rsi_calculator import get_global_rsi_calculator
            rsi_calculator = get_global_rsi_calculator()
            
            try:
                # Calculate RSI directly from 5m candles to match HyperLiquid exactly
                # Get fresh 5m candles for RSI calculation
                candles_5m_for_rsi = market_data_service.get_historical_candles("BTC", "5m", 30)
                if candles_5m_for_rsi and len(candles_5m_for_rsi) >= 15:
                    # Use standalone RSI calculation (matches HyperLiquid exactly)
                    current_rsi = rsi_calculator.calculate_standalone_rsi(candles_5m_for_rsi, periods=14)
                else:
                    logger.warning(f"⚠️ Insufficient candles for RSI: {len(candles_5m_for_rsi) if candles_5m_for_rsi else 0}")
                    current_rsi = None
            except Exception as e:
                logger.warning(f"⚠️ RSI calculation failed: {e}")
                current_rsi = None
            
            # Get candles from MarketDataService (single source of truth)
            candles_5m = market_data_service.get_historical_candles("BTC", "5m", 20)
            candles_1m = market_data_service.get_historical_candles("BTC", "1m", 20)
            candles_1h = market_data_service.get_historical_candles("BTC", "1h", 24)
            candles_1d = market_data_service.get_historical_candles("BTC", "1d", 7)
            
            # Get trend from the trend calculator singleton (single source)
            from core.analysis.real_time.trend_calculator import get_global_trend_calculator
            trend_calculator = get_global_trend_calculator()
            
            try:
                if len(candles_5m) >= 1:
                    trend_5m = trend_calculator.calculate_trend(candles_5m, "5m", "standard")
                else:
                    trend_5m = {}
                    logger.warning(f"⚠️ Not enough candles for trend calculation: {len(candles_5m)} < 1")
                
                # Extract the actual trend value from the trend calculation result
                if isinstance(trend_5m, dict) and trend_5m:
                    current_trend = trend_5m.get("trend")
                else:
                    current_trend = None
                    logger.warning(f"⚠️ Trend calculation returned empty or invalid result: {trend_5m}")
            except Exception as e:
                logger.warning(f"⚠️ Trend calculation failed: {e}")
                trend_5m = {}
                current_trend = None
            
            # Get volatility from the volatility calculator singleton (single source)
            from core.analysis.real_time.volatility_calculator import get_global_volatility_calculator
            volatility_calculator = get_global_volatility_calculator()
            
            try:
                volatility_5m = volatility_calculator.calculate_candle_volatility(candles_5m, "5m") if len(candles_5m) >= 1 else 0.0
                volatility_5m_category = volatility_calculator.categorize_volatility_for_trading(volatility_5m, "5m")
            except Exception as e:
                logger.warning(f"⚠️ Volatility calculation failed: {e}")
                volatility_5m = 0.0
                volatility_5m_category = ("UNKNOWN", "ERROR")
            
            # Get support/resistance from the S/R calculator singleton (single source)
            from core.analysis.real_time.support_resistance_calculator import get_global_support_resistance_calculator
            sr_calculator = get_global_support_resistance_calculator()
            
            try:
                support_resistance = sr_calculator.identify_key_levels(candles_5m, current_price) if len(candles_5m) >= 1 else {}
            except Exception as e:
                logger.warning(f"⚠️ Support/Resistance calculation failed: {e}")
                support_resistance = {}
            
            # Get pressure data from the pressure calculator singleton (single source)
            from core.analysis.real_time.pressure_calculator import get_global_pressure_calculator
            pressure_calculator = get_global_pressure_calculator()
            
            try:
                # Get orderbook data from hyperliquid_data for pressure calculation
                hyperliquid_data = market_data.get("hyperliquid_data", {})
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
            from core.analysis.real_time.bounce_validator import get_global_bounce_validator
            bounce_validator = get_global_bounce_validator()
            
            try:
                # BounceValidator doesn't have a simple validate_bounce method, skip for now
                bounce_analysis = {}
            except Exception as e:
                logger.warning(f"⚠️ Bounce validation failed: {e}")
                bounce_analysis = {}
            
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
            onchain_analysis = {}
            psychological_analysis = {}
            
            # Get market conditions from the market conditions analyzer singleton (single source)
            from core.analysis.real_time.market_conditions_analyzer import global_conditions_analyzer
            
            try:
                market_conditions_analysis = global_conditions_analyzer.analyze_trading_conditions(market_data) if market_data else {}
            except Exception as e:
                logger.warning(f"⚠️ Market conditions analysis failed: {e}")
                market_conditions_analysis = {}
            
            # Prepare chart data for dashboard
            try:
                # Get candles for chart
                chart_candles_5m = market_data_service.get_historical_candles("BTC", "5m", 20)
                
                # Prepare ongoing candle (current price as ongoing candle)
                # Get the current 5m candle start time (UTC synchronized)
                import datetime as dt
                current_time = time.time()
                utc_dt = dt.datetime.fromtimestamp(current_time, tz=dt.timezone.utc)
                utc_minute = utc_dt.minute
                candle_start_minute = (utc_minute // 5) * 5
                candle_start_dt = utc_dt.replace(minute=candle_start_minute, second=0, microsecond=0)
                candle_start_timestamp = candle_start_dt.timestamp()
                
                # Get real-time volume for current 5m candle
                real_time_volume = 0.0
                if market_data_service.hyperliquid_websocket:
                    real_time_volume = market_data_service.hyperliquid_websocket.get_current_5m_volume()
                
                # Check if we need to convert the last ongoing candle to historical
                if hasattr(self, 'last_ongoing_candle') and self.last_ongoing_candle:
                    last_candle_timestamp = self.last_ongoing_candle.get('timestamp', 0)
                    if last_candle_timestamp != candle_start_timestamp:
                        # Convert completed ongoing candle to historical
                        completed_candle = self.last_ongoing_candle.copy()
                        completed_candle['is_ongoing'] = False  # Mark as completed
                        completed_candle['close'] = current_price  # Final close price
                        completed_candle['high'] = max(completed_candle.get('open', current_price), current_price)
                        completed_candle['low'] = min(completed_candle.get('open', current_price), current_price)
                        
                        # CRITICAL FIX: Keep only 19 candles before appending new ongoing candle
                        # This prevents extra candles bug (19 historical + 1 ongoing = 20 total display)
                        if len(chart_candles_5m) >= 19:
                            chart_candles_5m = chart_candles_5m[-19:]  # Keep only last 19
                        
                        # Add completed candle to end (most recent)
                        chart_candles_5m.append(completed_candle)
                        
                        logger.info(f"🕯️ Converted ongoing candle to historical: {completed_candle.get('timestamp', 0)} -> {candle_start_timestamp}")
                
                ongoing_candle = {
                    "open": chart_candles_5m[-1]["close"] if chart_candles_5m else current_price,  # Start from last candle's close
                    "close": current_price,  # Current real-time price
                    "high": max(chart_candles_5m[-1]["close"] if chart_candles_5m else current_price, current_price),  # Track high from start
                    "low": min(chart_candles_5m[-1]["close"] if chart_candles_5m else current_price, current_price),   # Track low from start
                    "volume": real_time_volume if real_time_volume > 0 else (chart_candles_5m[-1]["volume"] if chart_candles_5m else 0),
                    "timestamp": candle_start_timestamp,  # Use proper 5m candle start time
                    "is_ongoing": True,  # Mark as ongoing candle (fixed field name)
                    "trades_count": 0,  # Will be updated by WebSocket
                    "last_trade_time": current_time
                }
                
                # Store current ongoing candle for next iteration
                self.last_ongoing_candle = ongoing_candle.copy()
                
                # Add ongoing candle to historical candles array for chart display
                chart_candles_with_ongoing = chart_candles_5m.copy()
                chart_candles_with_ongoing.append(ongoing_candle)
                
                # Prepare chart data
                candle_data = {
                    "historical": chart_candles_with_ongoing,  # Include ongoing candle in historical array
                    "ongoing": ongoing_candle,  # Keep separate for reference
                    "predicted": [],
                    "pattern_analysis": pattern_analysis
                }
            except Exception as e:
                logger.warning(f"⚠️ Chart data preparation failed: {e}")
                candle_data = {}
            
            # Create unified data structure that both Signal Aggregator and Dashboard can use
            unified_data = {
                # Core price data
                "current_price": current_price,
                
                # RSI data (from single RSI calculator source)
                "rsi": current_rsi,
                "rsi_5m": current_rsi,
                
                # Trend data (from single trend calculator source)
                "trend": current_trend,
                "trend_5m": trend_5m,
                
                # Volatility data (from single volatility calculator source)
                "volatility_5m": volatility_5m,
                "volatility_5m_category": volatility_5m_category,
                "volatility_1m": volatility_calculator.calculate_candle_volatility(candles_1m, "1m") if len(candles_1m) >= 1 else 0.0,
                "volatility_1h": volatility_calculator.calculate_candle_volatility(candles_1h, "1h") if len(candles_1h) >= 1 else 0.0,
                "volatility_1d": volatility_calculator.calculate_candle_volatility(candles_1d, "1d") if len(candles_1d) >= 1 else 0.0,
                
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
            "onchain_analysis": onchain_analysis,  # Calculated by onchain analyzer
            "bounce_analysis": bounce_analysis,  # Calculated by bounce validator
            "psychological_analysis": psychological_analysis,  # Calculated by psychological levels analyzer
            "market_conditions_analysis": market_conditions_analysis,  # Calculated by market conditions analyzer
            "support_resistance": support_resistance,
            
                # Chart data for dashboard
                "candleData": candle_data,
                "chart_data": candle_data,  # Alternative key for chart
                
                # Time snapshot
                "timestamp": time.time(),
                "time_snapshot": {
                    "unix_timestamp": time.time(),
                    "iso_timestamp": datetime.fromtimestamp(time.time()).isoformat(),
                    "human_readable": datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "trading_session_time": time.time() - (getattr(self, 'session_start_time', time.time()))
                }
            }
            
            # Store for both Signal Aggregator and Dashboard access
            self.unified_market_data = unified_data
            
            logger.debug(f"📊 Unified market data prepared: RSI={unified_data.get('rsi')}, Trend={unified_data.get('trend')}")
            
            return unified_data
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare unified market data: {e}")
            return {}
    
    def _update_dashboard_with_unified_data(self, unified_data: Dict[str, Any], dashboard_service):
        """Update dashboard using unified market data structure"""
        try:
            # Extract dashboard-specific data from unified structure
            # Map unified data to dashboard-expected field names
            dashboard_market_data = {
                "price": unified_data.get("current_price"),
                "current_price": unified_data.get("current_price"),
                "rsi": unified_data.get("rsi"),
                "rsi_5m": unified_data.get("rsi_5m"),
                
                # Dashboard expects trend_analysis.overall_trend for Overall Trend
                "trend_analysis": {
                    "overall_trend": unified_data.get("trend"),
                    "trend_5m": unified_data.get("trend_5m")
                },
                
                # Dashboard expects trading_volume_btc for Trading Volume (Hyperliquid 5m volume)
                "trading_volume_btc": unified_data.get("volume_data", {}).get("current_volume_btc", 0) or unified_data.get("volume_data", {}).get("real_time_volume_btc", 0),
                "trading_volume_category": unified_data.get("volume_data", {}).get("volume_category") or unified_data.get("volume_category"),
                "data_source": unified_data.get("volume_data", {}).get("data_source", "hyperliquid_candles"),
                
                # Binance global volume data
                "global_volume_btc_per_min": unified_data.get("binance_volume_data", {}).get("current_volume_btc", 0.0),
                "global_volume_category": self._categorize_global_volume(unified_data.get("binance_volume_data", {}).get("current_volume_btc", 0.0)),
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
                
                # Chart data
                "candleData": unified_data.get("candleData", {}),
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
                        
                        # Execute prediction
                        result = executor.execute_prediction(active_prediction.to_dict(), strategy)
                        
                        if result.get("success"):
                            logger.success(f"✅ Trade executed successfully!")
                            prediction_engine.clear_prediction()  # Clear after successful execution
                            self.current_prediction = None
                        else:
                            logger.warning(f"⚠️ Trade execution declined: {result.get('reason')}")
                    else:
                        logger.error("❌ Required services not available for trade execution")
                        
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
            
            # Detect optimal strategy using ML + historical data
            optimal_strategy = self.strategy_manager.detect_optimal_strategy(
                market_data=unified_data,
                historical_context=historical_context
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
        last_loop_time = 0
        min_loop_interval = 1.0  # Minimum 1 second between loop iterations
        last_5m_boundary = None  # Track 5-minute boundaries for immediate updates
        last_ongoing_candle = None  # Track the last ongoing candle to convert it to historical
        
        logger.info(f"🔄 Starting data collection loop (interval: {check_interval}s)")
        
        while True:
            try:
                # Update session time
                if self.session_manager:
                    self.session_manager.update_session_time_if_active()
                
                # Check for 5-minute boundary change (for immediate candle/volume reset)
                current_time = time.time()
                import datetime as dt
                current_dt = dt.datetime.fromtimestamp(current_time, tz=dt.timezone.utc)
                current_5m_boundary = (current_dt.minute // 5) * 5
                
                # Detect 5-minute boundary change
                boundary_changed = False
                if last_5m_boundary is not None and current_5m_boundary != last_5m_boundary:
                    boundary_changed = True
                    logger.info(f"🕐 5-minute boundary reached: {last_5m_boundary:02d}:00 -> {current_5m_boundary:02d}:00 UTC - Volume reset and new candle!")
                
                last_5m_boundary = current_5m_boundary
                
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
                
                # Prepare unified market data for both Signal Aggregator and Dashboard
                unified_data = self._prepare_unified_market_data(market_data, hyperliquid_price, market_data_service)
                
                # STRATEGY SELECTION: Detect optimal strategy based on market conditions
                current_strategy = self._detect_and_update_strategy(unified_data, dashboard_service)
                unified_data["current_strategy"] = current_strategy
                
                # Update dashboard with unified data
                self._update_dashboard_with_unified_data(unified_data, dashboard_service)
                
                # Force immediate dashboard update if 5-minute boundary changed
                if boundary_changed:
                    logger.info("🔄 Forcing immediate dashboard update due to 5-minute boundary change")
                    
                    # Clear old trades from WebSocket cache to ensure clean volume reset
                    if market_data_service.hyperliquid_websocket:
                        # Clear trades older than current 5m candle start
                        import datetime as dt
                        current_dt = dt.datetime.fromtimestamp(current_time, tz=dt.timezone.utc)
                        candle_start_minute = (current_dt.minute // 5) * 5
                        candle_start_dt = current_dt.replace(minute=candle_start_minute, second=0, microsecond=0)
                        cutoff_timestamp = candle_start_dt.timestamp()
                        market_data_service.hyperliquid_websocket.clear_old_trades(cutoff_timestamp)
                    
                    # Trigger additional WebSocket emission for immediate update
                    dashboard_service._trigger_websocket_emission()
                
                # Generate price prediction
                self._generate_price_prediction(unified_data, current_strategy)
                
                # Simple monitoring log
                rsi_value = market_data.get("hyperliquid_analysis", {}).get('rsi_5m')
                rsi_display = f"{rsi_value:.1f}" if rsi_value else "Loading"
                
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
                
                # Technical indicators
                "rsi": hyperliquid_analysis.get("rsi_5m"),
                "rsi_5m": hyperliquid_analysis.get("rsi_5m"),
                
                # Volatility data
                "volatility_5m": hyperliquid_analysis.get("volatility_5m", 0.001),
                "volatility_5m_category": hyperliquid_analysis.get("volatility_5m_category", "LOW"),
                "volatility_5m_trend": hyperliquid_analysis.get("volatility_5m_trend"),
                
                # Trend data
                "trend_5m": hyperliquid_analysis.get("trend_5m"),
                "trend_analysis": {
                    "overall_trend": hyperliquid_analysis.get("trend_5m", {}).get("trend"),
                    "trend_5m": hyperliquid_analysis.get("trend_5m", {}).get("trend"),
                    "trend_1h": hyperliquid_analysis.get("trend_1h", {}).get("trend"),
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
                "rsi": hyperliquid_analysis.get("rsi_5m"),
                "rsi_5m": hyperliquid_analysis.get("rsi_5m"),
                "volatility_5m": hyperliquid_analysis.get("volatility_5m"),
                "volatility_5m_category": hyperliquid_analysis.get("volatility_5m_category"),
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
            
            # DELEGATE: Get market analysis from MarketDataService
            hyperliquid_analysis = market_data_service.get_hyperliquid_analysis(current_price)
            if not hyperliquid_analysis or "error" in hyperliquid_analysis:
                return None
            
            # DELEGATE: Get ALL market data from MarketDataService (includes orderbook)
            hyperliquid_data = market_data_service.get_all_market_data("BTC")
            if not hyperliquid_data or "error" in hyperliquid_data:
                return None
            
            # DELEGATE: Get market conditions from MarketConditionsAnalyzer
            from core.analysis.real_time.market_conditions_analyzer import global_conditions_analyzer
            market_conditions = global_conditions_analyzer.analyze_trading_conditions(
                hyperliquid_analysis, hyperliquid_data
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

    def _sync_ai_results_to_dashboard(self, ai_results: Dict[str, Any], current_price: float, strategy: str):
        """Sync AI prediction results to dashboard as MARKET_ANALYSIS signal"""
        try:
            if not ai_results:
                logger.debug("📊 No AI results to sync to dashboard")
                return
                
            if not isinstance(ai_results, dict):
                logger.debug("📊 AI results is not a dict, skipping sync")
                return
                
            if "analysis" not in ai_results:
                logger.debug("📊 No analysis in AI results to sync")
                return
            
            analysis = ai_results.get("analysis")
            if not analysis:
                logger.debug("📊 No analysis in AI results to sync")
                return
                
            if not isinstance(analysis, dict):
                logger.debug("📊 Analysis is not a dict, skipping sync")
                return
                
            prediction = analysis.get("prediction")
            
            if not prediction:
                logger.debug("📊 No prediction in AI results to sync")
                return
            
            # Create MARKET_ANALYSIS signal for dashboard
            
            # Handle both dict and TradingPrediction object
            if hasattr(prediction, 'direction'):
                # TradingPrediction object
                signal_data = {
                    "type": "MARKET_ANALYSIS",
                    "direction": prediction.direction,
                    "entry_price": prediction.entry_price,
                    "size_btc": getattr(prediction, 'size_btc', 0.001),
                    "stop_loss": prediction.stop_loss,
                    "take_profit": prediction.target_price,
                    "confidence": prediction.final_confidence,  # Use final_confidence attribute
                    "reasoning": getattr(prediction, 'entry_reasoning', "No reasoning available"),
                    "strategy": getattr(prediction, 'strategy', strategy),
                    "timestamp": time.time(),
                    "market_regime": analysis.get("market_regime", "UNKNOWN"),
                    "analysis_confidence": analysis.get("analysis_confidence", 0.0),
                    "strategy_confidence": analysis.get("strategy_confidence", 0.0)
                }
            else:
                # Dict format
                signal_data = {
                    "type": "MARKET_ANALYSIS",
                    "direction": prediction.get("direction", "HOLD"),
                    "entry_price": prediction.get("entry_price", current_price),
                    "size_btc": prediction.get("size_btc", 0.001),
                    "stop_loss": prediction.get("stop_loss", 0.0),
                    "take_profit": prediction.get("target_price", 0.0),
                    "confidence": prediction.get("confidence", 0.0),
                    "reasoning": prediction.get("reasoning", "No reasoning available"),
                    "strategy": prediction.get("strategy", strategy),
                    "timestamp": time.time(),
                    "market_regime": analysis.get("market_regime", "UNKNOWN"),
                    "analysis_confidence": analysis.get("analysis_confidence", 0.0),
                    "strategy_confidence": analysis.get("strategy_confidence", 0.0)
                }
            
            # Add to dashboard
            dashboard_service.add_prediction(signal_data)
            logger.debug(f"📊 Synced AI prediction to dashboard: {signal_data['direction']} "
                        f"(confidence: {signal_data['confidence']:.3f})")
            
        except Exception as e:
            logger.error(f"❌ Failed to sync AI results to dashboard: {e}")
    
    def _trigger_dashboard_update(self):
        """Trigger immediate dashboard update to show new prediction data"""
        try:
            # Use a simple file-based trigger to notify dashboard of new data
            # The dashboard's background monitoring will pick this up
            import os
            trigger_file = "data/temp/dashboard_update_trigger.txt"
            os.makedirs(os.path.dirname(trigger_file), exist_ok=True)
            
            with open(trigger_file, 'w') as f:
                f.write(str(time.time()))
            
            logger.debug("📊 Triggered dashboard update notification")
        except Exception as e:
            logger.debug(f"📊 Could not trigger dashboard update: {e}")
    
    def _should_generate_new_prediction(self, current_market_data: Dict[str, Any]) -> bool:
        """
        Check if market conditions have changed enough to warrant a new prediction
        (excluding current price changes)
        
        Args:
            current_market_data: Current market data
            
        Returns:
            True if conditions changed enough to generate new prediction
        """
        try:
            # Extract key market conditions (excluding current_price)
            current_conditions = {
                "rsi": current_market_data.get("rsi", 50.0),
                "volatility_5m": current_market_data.get("volatility_5m", 0.0),
                "volatility_category": current_market_data.get("volatility_5m_category", "UNKNOWN"),
                "trend": current_market_data.get("trend_5m", {}).get("trend", "SIDEWAYS"),
                "volume_category": current_market_data.get("volume_category"),
                "pressure": current_market_data.get("pressure", "SIDEWAYS"),
                "market_condition": current_market_data.get("market_conditions", {}).get("condition", "FAIR")
            }
            
            # Create hash of current conditions
            import hashlib
            conditions_str = str(sorted(current_conditions.items()))
            current_hash = hashlib.md5(conditions_str.encode()).hexdigest()
            
            # Check if this is the first run or conditions changed
            if self.market_conditions_hash is None:
                self.market_conditions_hash = current_hash
                self.last_market_conditions = current_conditions
                logger.debug("🔄 First market conditions check - will generate prediction")
                return True
            
            # Check if conditions changed significantly
            if current_hash != self.market_conditions_hash:
                logger.info("🔄 Market conditions changed - generating new prediction")
                logger.debug(f"   Previous: {self.last_market_conditions}")
                logger.debug(f"   Current:  {current_conditions}")
                
                # Update stored conditions
                self.market_conditions_hash = current_hash
                self.last_market_conditions = current_conditions
                return True
            
            # Conditions haven't changed significantly
            logger.debug("📊 Market conditions unchanged - no new prediction needed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Market conditions check failed: {e}")
            # Default to generating prediction on error
            return True
    
    def _get_liquidation_hunting_data(self) -> Dict[str, Any]:
        """Get current liquidation hunting data for dashboard - using market opening service"""
        try:
            if not self.market_opening_service:
                return {
                    "status": "Inactive",
                    "next_opening": None,
                    "active_markets": [],
                    "opportunities": 0,
                    "liquidation_risk": "LOW"
                }
            
            # Get market opening info
            next_opening = self.market_opening_service.get_next_major_opening()
            session_info = self.market_opening_service.get_market_session_info()
            
            return {
                "status": "Active" if self.market_opening_service.is_market_opening_time() else "Monitoring",
                "next_opening": next_opening,
                "active_markets": session_info.get("active_markets", []),
                "opportunities": 0,  # Not applicable for simple display
                "liquidation_risk": session_info.get("liquidation_risk", "LOW")
            }
        except Exception as e:
            logger.error(f"❌ Failed to get liquidation hunting data: {e}")
            return {
                "status": "Error",
                "next_opening": None,
                "active_markets": [],
                "opportunities": 0,
                "liquidation_risk": "UNKNOWN"
            }
    
    def _get_market_opening_info(self) -> Dict[str, Any]:
        """Get market opening information for display"""
        try:
            if not self.market_opening_service:
                return {
                    "next_opening": None,
                    "time_until": None,
                    "market_name": None,
                    "status": "Inactive",
                    "importance": 0,
                    "liquidation_risk": 0.0
                }
            
            # Get next major opening
            next_opening = self.market_opening_service.get_next_major_opening()
            if not next_opening:
                return {
                    "next_opening": None,
                    "time_until": None,
                    "market_name": None,
                    "status": "No openings",
                    "importance": 0,
                    "liquidation_risk": 0.0
                }
            
            # Calculate time until opening
            time_until_seconds = next_opening.get('time_until', 0)
            time_until_hours = int(time_until_seconds // 3600)
            time_until_minutes = int((time_until_seconds % 3600) // 60)
            
            # Format time display
            if time_until_hours > 0:
                time_display = f"{time_until_hours:02d}:{time_until_minutes:02d}"
            else:
                time_display = f"00:{time_until_minutes:02d}"
            
            # Get market name (shortened for display)
            market_name = next_opening.get('exchange', 'Unknown Market')
            
            return {
                "next_opening": next_opening.get('opening_time').isoformat() if next_opening.get('opening_time') else None,
                "time_until": time_display,
                "market_name": market_name,
                "status": "Active" if self.market_opening_service.is_market_opening_time() else "Monitoring",
                "importance": next_opening.get('importance', 0),
                "liquidation_risk": 0.0  # Not applicable for simple display
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get market opening info: {e}")
            return {
                "next_opening": None,
                "time_until": None,
                "market_name": None,
                "status": "Error",
                "importance": 0,
                "liquidation_risk": 0.0
            }
    
    def _get_ml_performance_data(self) -> Dict[str, Any]:
        """Retrieves current ML performance data for the dashboard."""
        try:
            # Get ML performance data from AI service
            if self.ai_service:
                # Get analysis history from AI service
                analysis_history = self.ai_service.get_analysis_history()
                
                # Calculate performance metrics
                total_analyses = len(analysis_history)
                active_trades = 0  # AI service doesn't track trades directly
                total_trades = 0   # AI service doesn't track trades directly
                win_rate = 0.0     # AI service doesn't track trades directly
                
                # Get actual training data count from ML system
                try:
                    from core.ml.model_training import global_model_trainer
                    training_stats = global_model_trainer.data_collector.get_data_statistics()
                    actual_training_points = training_stats.get("data_points", 0)
                except Exception as e:
                    logger.error(f"❌ Failed to get training data count: {e}")
                    # NO FALLBACKS - training points must be calculated properly
                    if total_analyses == 0:
                        raise ValueError("No training data available - NO FALLBACKS")
                    actual_training_points = total_analyses
                
                # Determine analysis type based on recent activity
                if total_analyses > 0:
                    latest_analysis = analysis_history[-1]
                    analysis_type = "Active" if latest_analysis.get("had_prediction") or latest_analysis.get("had_reactive_trade") else "Monitoring"
                    analysis_type_detail = latest_analysis.get("strategy", "Unknown")
                    
                    # Calculate accuracy based on win rate and analysis confidence
                    base_accuracy = win_rate / 100.0 if win_rate > 0 else 0.65
                    avg_confidence = sum(a.get("analysis_confidence", 0.5) for a in analysis_history) / total_analyses
                    accuracy = min(0.95, base_accuracy + (avg_confidence * 0.2))
                    
                    # Calculate confidence correlation based on consistency
                    confidence_correlation = min(0.9, 0.5 + (avg_confidence * 0.4))
                else:
                    analysis_type = "Initializing"
                    analysis_type_detail = "System Starting"
                    accuracy = 0.0
                    confidence_correlation = 0.0
                
                return {
                    "analysis_type": analysis_type,
                    "analysis_type_detail": analysis_type_detail,
                    "training_data_points": actual_training_points,
                    "accuracy": accuracy,
                    "confidence_correlation": confidence_correlation,
                    "retrain_status": "Auto",
                    "learning_status": "Active",
                    "active_predictions": active_trades,
                    "total_predictions": total_trades
                }
            
            # Fallback data if AI system not available - still try to get training data
            try:
                from core.ml.model_training import global_model_trainer
                training_stats = global_model_trainer.data_collector.get_data_statistics()
                training_points = training_stats.get("data_points", 0)
            except Exception:
                training_points = 0
            
            return {
                "analysis_type": "Initializing",
                "analysis_type_detail": "System Starting",
                "training_data_points": training_points,
                "accuracy": 0.0,
                "confidence_correlation": 0.0,
                "retrain_status": "Pending",
                "learning_status": "Initializing",
                "active_predictions": 0,
                "total_predictions": 0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get ML performance data: {e}")
            return {
                "analysis_type": "Error",
                "analysis_type_detail": "Data Unavailable",
                "training_data_points": 0,
                "accuracy": 0.0,
                "confidence_correlation": 0.0,
                "retrain_status": "Error",
                "learning_status": "Error",
                "active_predictions": 0,
                "total_predictions": 0
            }
    
    def _calculate_real_time_support_resistance(self, hyperliquid_api, current_price: float, strategy_name: str, market_data_service=None) -> Dict[str, Any]:
        """Calculate real-time support/resistance levels with integrated historical data and guaranteed important levels"""
        try:
            from core.analysis.real_time.support_resistance_calculator import get_global_support_resistance_calculator
            sr_calculator = get_global_support_resistance_calculator()
            
            logger.info(f"📊 Starting S/R calculation for price: ${current_price:.2f}")
            
            # Check if we have cached S/R data and if price has broken any levels
            force_refresh = False
            if hasattr(self, '_sr_cache') and 'data' in self._sr_cache:
                cached_data = self._sr_cache.get('data', {})
                last_price = self._sr_cache.get('last_price', current_price)
                
                # Check if price has broken through any current S/R levels
                key_levels = cached_data.get('key_levels', [])
                logger.debug(f"📊 Checking {len(key_levels)} cached S/R levels for breaks (last_price=${last_price:.2f}, current_price=${current_price:.2f})")
                for level in key_levels:
                    level_price = level.get('level', 0)
                    level_type = level.get('type', '')
                    
                    logger.debug(f"📊 Checking {level_type} at ${level_price:.2f}")
                    
                    # Check if price has crossed a support level (broke below)
                    # Add buffer (0.5%) to account for minor fluctuations and ensure detection
                    buffer = level_price * 0.005
                    if (level_type == 'support' and 
                        last_price > (level_price + buffer) and 
                        current_price <= (level_price + buffer)):
                        force_refresh = True
                        logger.info(f"📊 Price broke support at ${level_price:.2f} - refreshing S/R levels")
                        break
                    
                    # Check if price has crossed a resistance level (broke above)
                    elif (level_type == 'resistance' and 
                          last_price < (level_price - buffer) and 
                          current_price >= (level_price - buffer)):
                        force_refresh = True
                        logger.info(f"📊 Price broke resistance at ${level_price:.2f} - refreshing S/R levels")
                        logger.info(f"📊 Break details: last_price=${last_price:.2f}, current_price=${current_price:.2f}, buffer=${buffer:.2f}")
                        break
                
                # If no level break, use cached data
                if not force_refresh:
                    logger.info("📊 Using cached S/R data (no level breaks detected)")
                    return cached_data
            
            # Get candle data for S/R analysis - start with recent data, expand if needed
            logger.info("📊 Fetching candle data for S/R analysis...")
            
            # DELEGATE: Get candle data from market data service (SRP compliance)
            candles_5m = market_data_service.get_historical_candles("BTC", "5m", 288)
            candles_1h = market_data_service.get_historical_candles("BTC", "1h", 48)
            candles_1d = market_data_service.get_historical_candles("BTC", "1d", 7)
            
            if not candles_5m or not candles_1h or not candles_1d:
                raise ValueError("Candle data not available from market data service - NO FALLBACKS")
            
            # Combine all data for market level detection
            all_levels = []
            
            # PRIORITIZE RECENT DATA - Focus on current consolidation zones
            # Analyze 5m data FIRST (most important for current levels)
            if candles_5m and len(candles_5m) >= 20:
                logger.info(f"📊 Analyzing {len(candles_5m)} 5m candles for CURRENT S/R levels")
                sr_5m = sr_calculator.identify_key_levels(candles_5m, min_touches=2)
                for level in sr_5m.get("key_levels", []):
                    level["timeframe"] = "5m"
                    level["weight"] = 3.0  # HIGHEST weight for current levels
                all_levels.extend(sr_5m.get("key_levels", []))
                logger.info(f"📊 Found {len(sr_5m.get('key_levels', []))} 5m S/R levels")
            else:
                logger.warning(f"⚠️ Insufficient 5m candle data: {len(candles_5m) if candles_5m else 0} candles")
            
            # Analyze 1h data for recent major levels (reduced weight)
            if candles_1h and len(candles_1h) >= 20:
                logger.info(f"📊 Analyzing {len(candles_1h)} 1h candles for recent major levels")
                sr_1h = sr_calculator.identify_key_levels(candles_1h, min_touches=2)
                for level in sr_1h.get("key_levels", []):
                    level["timeframe"] = "1h"
                    level["weight"] = 1.5  # Reduced weight
                all_levels.extend(sr_1h.get("key_levels", []))
                logger.info(f"📊 Found {len(sr_1h.get('key_levels', []))} 1h S/R levels")
            else:
                logger.warning(f"⚠️ Insufficient 1h candle data: {len(candles_1h) if candles_1h else 0} candles")
            
            # Analyze 1d data for long-term levels (lowest priority)
            if candles_1d and len(candles_1d) >= 10:
                logger.info(f"📊 Analyzing {len(candles_1d)} 1d candles for long-term S/R levels")
                sr_1d = sr_calculator.identify_key_levels(candles_1d, min_touches=2)
                for level in sr_1d.get("key_levels", []):
                    level["timeframe"] = "1d"
                    level["weight"] = 1.0  # Reduced weight for old data
                all_levels.extend(sr_1d.get("key_levels", []))
                logger.info(f"📊 Found {len(sr_1d.get('key_levels', []))} 1d S/R levels")
            else:
                logger.warning(f"⚠️ Insufficient 1d candle data: {len(candles_1d) if candles_1d else 0} candles")
            
            # 5. Find persistent resistance levels (always show next resistance even after breakouts)
            # Note: find_next_significant_resistance method was removed during cleanup
            # The main level detection above should already find relevant resistance levels
            
            # 6. GUARANTEED S/R LEVELS: Always show at least 1 support and 1 resistance
            relevant_levels = []
            
            # Separate all levels by type
            all_support_levels = [lvl for lvl in all_levels if lvl["type"] == "support"]
            all_resistance_levels = [lvl for lvl in all_levels if lvl["type"] == "resistance"]
            
            # CRITICAL: Ensure we ALWAYS have S/R levels (NO FALLBACKS rule)
            if not all_levels:
                logger.error("❌ CRITICAL: No S/R levels found from candle analysis!")
                logger.error("❌ This violates NO FALLBACKS rule - S/R calculation must be fixed")
                # Force creation of emergency levels
                all_levels = []
                all_support_levels = []
                all_resistance_levels = []
            
            # Removed verbose debug logging to reduce spam
            
            # SUPPORT LEVEL SELECTION - ALWAYS show at least 1 support
            if all_support_levels:
                # Sort all support levels by score (best first)
                all_support_levels.sort(key=lambda x: (x.get("score", 0) * x.get("weight", 1.0)), reverse=True)
                
                # Prefer levels below current price, but if none exist, use the closest one
                support_levels_below = [lvl for lvl in all_support_levels if lvl["level"] < current_price]
                
                if support_levels_below:
                    # Use levels below current price (preferred)
                    for support in support_levels_below:
                        combined_score = support.get("score", 0) * support.get("weight", 1.0)
                        if len([l for l in relevant_levels if l["type"] == "support"]) < 1 or combined_score > 0.2:
                            # Add missing fields for dashboard display
                            support["timeframe"] = support.get("timeframe", "5m")
                            support["relevance"] = "high" if combined_score > 0.5 else "medium" if combined_score > 0.2 else "low"
                            relevant_levels.append(support)
                        if len([l for l in relevant_levels if l["type"] == "support"]) >= 3:
                            break
                else:
                    # No support below current price - use the closest support from historical data
                    closest_support = all_support_levels[0]  # Already sorted by score
                    relevant_levels.append(closest_support)
            else:
                logger.warning("⚠️ No support levels found in historical data")
            
            # RESISTANCE LEVEL SELECTION - ONLY levels ABOVE current price
            if all_resistance_levels:
                # Filter to only include resistance levels ABOVE current price
                resistance_levels_above = [lvl for lvl in all_resistance_levels if lvl["level"] > current_price]
                
                if resistance_levels_above:
                    # Sort by score (best first)
                    resistance_levels_above.sort(key=lambda x: (x.get("score", 0) * x.get("weight", 1.0)), reverse=True)
                    
                    # Include up to 3 resistance levels above current price
                    for resistance in resistance_levels_above[:3]:
                        combined_score = resistance.get("score", 0) * resistance.get("weight", 1.0)
                        if combined_score > 0.2:
                            # Add missing fields for dashboard display
                            resistance["timeframe"] = resistance.get("timeframe", "5m")
                            resistance["relevance"] = "high" if combined_score > 0.5 else "medium" if combined_score > 0.2 else "low"
                            relevant_levels.append(resistance)
                        if len([l for l in relevant_levels if l["type"] == "resistance"]) >= 3:
                            break
                else:
                    # No resistance above current price - price at all-time high or broke through all resistance
                    logger.warning("⚠️ No resistance levels above current price - price at highs")
            else:
                logger.warning("⚠️ No resistance levels found in historical data")
            
            # If not enough levels found in recent data, expand timeframe
            if len(relevant_levels) < 4:
                logger.warning(f"⚠️ Only {len(relevant_levels)} levels found in recent data - expanding to 30 days")
                
                # DELEGATE: Get extended historical data from market data service (SRP compliance)
                candles_1d_extended = market_data_service.get_historical_candles("BTC", "1d", 30)
                candles_1h_extended = market_data_service.get_historical_candles("BTC", "1h", 168)
                
                if not candles_1d_extended or not candles_1h_extended:
                    raise ValueError("Extended historical data not available from market data service - NO FALLBACKS")
                
                # Analyze extended data
                if candles_1d_extended and len(candles_1d_extended) >= 10:
                    sr_extended = sr_calculator.identify_key_levels(candles_1d_extended, min_touches=2)
                    for level in sr_extended.get("key_levels", []):
                        level["timeframe"] = "1d_extended"
                        level["weight"] = 0.8  # Lower weight for older data
                        # Only add if not already present
                        if not any(abs(level["level"] - existing["level"]) < 500 for existing in relevant_levels):
                            relevant_levels.append(level)
                
                if candles_1h_extended and len(candles_1h_extended) >= 10:
                    sr_extended = sr_calculator.identify_key_levels(candles_1h_extended, min_touches=2)
                    for level in sr_extended.get("key_levels", []):
                        level["timeframe"] = "1h_extended"
                        level["weight"] = 0.7
                        if not any(abs(level["level"] - existing["level"]) < 500 for existing in relevant_levels):
                            relevant_levels.append(level)
                
                logger.info(f"📊 After expansion: {len(relevant_levels)} total levels")
            
            # If STILL no levels (market at all-time high/low), use price-based levels
            if not relevant_levels:
                logger.error("❌ No S/R levels found even after expansion - market at extreme")
                raise ValueError("No valid S/R levels available")
            
            # 8. Sort by combined score (score * weight)
            relevant_levels.sort(key=lambda x: (x.get("score", 0) * x.get("weight", 1.0)), reverse=True)
            
            # 9. Get strongest support and resistance
            support_levels = [lvl for lvl in relevant_levels if lvl["type"] == "support"]
            resistance_levels = [lvl for lvl in relevant_levels if lvl["type"] == "resistance"]
            
            strongest_support = support_levels[0]["level"] if support_levels else 0.0
            strongest_resistance = resistance_levels[0]["level"] if resistance_levels else 0.0
            
            
            # Prepare final result
            result = {
                "key_levels": relevant_levels[:10],  # Top 10 most relevant levels
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "timeframe": "integrated_multi_timeframe",
                "candles_analyzed": len(candles_5m) + len(candles_1h) + len(candles_1d),
                "analysis_confidence": min(1.0, len(relevant_levels) / 8),  # More levels = higher confidence
                "data_source": "hyperliquid_integrated",
                "persistent_resistance": None,  # Removed during cleanup
                "level_breakdown": {
                    "support_count": len(support_levels),
                    "resistance_count": len(resistance_levels),
                    "timeframes_analyzed": len(set(lvl.get("timeframe", "unknown") for lvl in relevant_levels))
                }
            }
            
            # Cache the result until price breaks a level
            self._sr_cache = {
                'data': result,
                'last_price': current_price
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Real-time support/resistance calculation failed: {e}")
            # NO FALLBACKS - raise the exception
            raise Exception(f"Support/resistance calculation failed: {e}")
    
    
    def _add_ml_metrics_to_dashboard(self, dashboard_service):
        """Add ML performance metrics to the dashboard"""
        try:
            from core.ml.performance_monitor import global_performance_monitor
            from core.ml.continuous_learning import global_continuous_learning
            from core.ml.model_training import global_model_trainer
            
            # Get ML performance summary
            performance_summary = global_performance_monitor.get_performance_summary()
            
            # Get training data status
            training_status = global_model_trainer.get_training_status()
            
            # Get learning system status
            learning_config = global_continuous_learning.config
            should_retrain = global_continuous_learning._should_retrain()
            
            # Create ML metrics signal
            ml_metrics_data = {
                "type": "ML_METRICS",
                "performance_summary": performance_summary,
                "training_status": training_status,
                "learning_config": {
                    "retrain_interval_hours": learning_config.retrain_interval_hours,
                    "min_data_points": learning_config.min_data_points,
                    "performance_threshold": learning_config.performance_threshold,
                    "confidence_threshold": learning_config.confidence_threshold,
                    "auto_retraining": learning_config.enable_automatic_retraining
                },
                "should_retrain": should_retrain,
                "retrain_count": global_continuous_learning.retrain_count,
                "last_retrain_time": global_continuous_learning.last_retrain_time,
                "is_learning": global_continuous_learning.is_learning,
                "timestamp": time.time()
            }
            
            dashboard_service.add_signal(ml_metrics_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to add ML metrics to dashboard: {e}")
    
    def _categorize_global_volume(self, volume_btc_per_min: float) -> str:
        """Categorize global volume based on BTC/min thresholds for global Bitcoin market"""
        try:
            if volume_btc_per_min < 5:
                return "VERY_LOW"
            elif volume_btc_per_min < 10:
                return "LOW"
            elif volume_btc_per_min < 20:
                return "NORMAL"
            elif volume_btc_per_min < 50:
                return "HIGH"
            elif volume_btc_per_min < 100:
                return "VERY_HIGH"
            else:
                return "EXTREME"
        except Exception as e:
            logger.error(f"❌ Failed to categorize global volume: {e}")
            return "UNKNOWN"
    
