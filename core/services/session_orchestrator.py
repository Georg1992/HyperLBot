#!/usr/bin/env python3
"""
Session Orchestrator Service  
Handles trading session lifecycle and main trading loop
Single Responsibility: Session coordination and trading loop
"""

import time
from typing import Dict, Any, Optional
from loguru import logger
from core.session.session_manager import SessionManager

class SessionOrchestrator:
    """Session orchestration service - handles trading loop and lifecycle"""
    
    def __init__(self, config, initial_balance: float):
        self.config = config
        self.initial_balance = initial_balance
        self.session_manager = None
        self.weekly_trend_analysis = {}
        
        logger.info("🔄 Session Orchestrator initialized - Trading loop coordination")
    
    def run_paper_trading_session(self, check_interval: int,
                                 system_initializer, market_data_service, trading_engine, dashboard_service, strategy_manager=None) -> Dict[str, Any]:
        """Run the main paper trading session"""
        try:
            # 1. Initialize system
            init_result = system_initializer.initialize_system(market_data_service)
            if not init_result["success"]:
                logger.error("❌ System initialization failed")
                return {"success": False, "error": "System initialization failed"}
            
            hyperliquid_api = init_result["hyperliquid_api"]
            
            # 2. Get weekly context
            logger.info("📅 Getting weekly trend analysis for session context...")
            weekly_analysis = market_data_service.get_weekly_trend_analysis()
            
            if "error" not in weekly_analysis:
                self.weekly_trend_analysis = weekly_analysis
                logger.success("✅ Weekly trend analysis loaded successfully!")
            else:
                logger.warning("⚠️ Could not get weekly trend analysis, proceeding without it")
            
            # 3. Start session
            self._start_session(dashboard_service, market_data_service)
            
            # 4. Main monitoring loop
            return self._main_trading_loop(check_interval, hyperliquid_api,
                                         market_data_service, trading_engine, dashboard_service, strategy_manager)
            
        except Exception as e:
            logger.error(f"❌ Trading session failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _start_session(self, dashboard_service, market_data_service):
        """Start trading session"""
        try:
            # Clear dashboard cache
            from core.dashboard.dashboard_data_manager import simple_rtm
            simple_rtm.clear_presentation_data()
            logger.info("🧹 Dashboard cache cleared - Fresh session data")
            
            # Start session  
            from core.session.session_manager import session_manager
            self.session_manager = session_manager  # Use singleton instance
            logger.info("✅ SessionManager initialized")
            
            # COMPUTE HISTORICAL CONTEXT for session (business logic data)
            logger.info("🚀 Starting historical context computation...")
            self._compute_and_store_historical_context()
            
            # Wait a moment for computation to complete
            time.sleep(1)
            
            # Verify historical context was computed successfully
            if not self.session_manager.has_historical_context():
                logger.warning("⚠️ Historical context computation failed - retrying once...")
                # Retry once with a small delay
                time.sleep(3)
                self._compute_and_store_historical_context()
                
                if not self.session_manager.has_historical_context():
                    logger.error("❌ Historical context computation failed after retry - continuing with degraded functionality")
                else:
                    logger.success("✅ Historical context ready after retry")
            else:
                logger.success("✅ Historical context ready for market conditions analysis")
            
            # Create initial heartbeat
            dashboard_service.create_initial_heartbeat(self.session_manager, "standard", self.initial_balance)
            
            # Start session
            session_id = self.session_manager.start_session(
                session_id=f"bot_session_{int(time.time())}",
                strategy="standard",
                initial_balance=self.initial_balance
            )
            
            # Log session start
            dashboard_service.update_rtm_activity(
                f"🚀 Trading bot started with ${self.initial_balance:.2f} initial balance", 
                "SUCCESS"
            )
            
            logger.success("🔥 Session started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start session: {e}")
    
    def _compute_and_store_historical_context(self):
        """Compute historical context once per session and store in SessionManager"""
        try:
            logger.info("📊 Computing session historical context (6.5 weeks analysis)...")
            
            # Import historical analyzer
            from core.analysis.historical.session_context_analyzer import SessionContextAnalyzer
            from core.external.yahoo_api import YahooAPI
            
            # Get historical data for context analysis
            yahoo_fetcher = YahooAPI()
            logger.info("📊 Fetching daily candles (45 days)...")
            candles_1d = yahoo_fetcher.get_klines("BTC-USD", "1d", 45)  # 6.5 weeks
            logger.info(f"📊 Daily candles: {len(candles_1d) if candles_1d else 0} candles")
            
            logger.info("📊 Fetching hourly candles (84 hours)...")
            candles_1h = yahoo_fetcher.get_klines("BTC-USD", "1h", 84)  # 3.5 days  
            logger.info(f"📊 Hourly candles: {len(candles_1h) if candles_1h else 0} candles")
            
            logger.info("📊 Fetching 5-minute candles (30 candles)...")
            candles_5m = yahoo_fetcher.get_klines("BTC-USD", "5m", 30)  # 2.5 hours
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
            from core.session.session_manager import session_manager
            session_manager.set_historical_context(historical_context)
            
            logger.success("✅ Session historical context computed and stored")
            logger.info(f"✅ Market regime: {historical_context.get('market_regime', {}).get('regime', 'UNKNOWN')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to compute historical context: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            # Continue session without historical context (degraded but functional)
    
    def _generate_initial_market_analysis(self, market_data_service, dashboard_service, strategy_name="standard"):
        """Generate initial market analysis and candle data for dashboard display"""
        try:
            logger.info(f"🎯 Generating initial market analysis with {strategy_name} strategy...")
            
            # Get current market data
            current_price = market_data_service.get_hyperliquid_price()
            if not current_price:
                logger.warning("⚠️ Cannot generate initial market analysis - no price data")
                return
            
            # Get market analysis
            yahoo_analysis = market_data_service.get_yahoo_analysis(current_price, strategy_name)
            if not yahoo_analysis or "error" in yahoo_analysis:
                logger.warning("⚠️ Cannot generate initial market analysis - no market analysis")
                return
            
            # Build market data for prediction engine - USE REAL-TIME RSI (same as dashboard)
            from core.market_data_manager import global_rsi_calculator
            # Use real-time RSI value (same as dashboard) instead of stale cached data
            if global_rsi_calculator.rsi_initialized:
                rsi_value = global_rsi_calculator.current_rsi
                rsi_data = {"rsi": rsi_value, "rsi_trend": "NEUTRAL", "rsi_signal": "NEUTRAL"}
            else:
                # Fallback: Use Yahoo if real-time not initialized yet
                rsi_data = global_rsi_calculator.get_current_rsi_data()
            
            # MARKET CONDITIONS ANALYSIS for session prediction
            from strategies.market_conditions_analyzer import global_conditions_analyzer
            
            market_data = {
                "current_price": current_price,
                "rsi_5m": rsi_data.get("rsi", yahoo_analysis.get("rsi_5m", 50.0)),
                "rsi": rsi_data.get("rsi", yahoo_analysis.get("rsi_5m", 50.0)),  # Keep both for compatibility
                "trend_5m": yahoo_analysis.get("trend_5m", {}),
                "trend": yahoo_analysis.get("trend_5m", {}).get("direction", "NEUTRAL"),  # Keep both for compatibility
                "volatility_5m": yahoo_analysis.get("volatility_5m", 0.0),
                "volatility_5m_category": yahoo_analysis.get("volatility_5m_category", "MODERATE"),
                "volatility_category": yahoo_analysis.get("volatility_5m_category", "MODERATE"),  # Keep both for compatibility
                "volume_5m": yahoo_analysis.get("volume_5m", 0.0),
                "volume_category": yahoo_analysis.get("volume_category", "UNKNOWN"),
                "pressure": yahoo_analysis.get("pressure", "NEUTRAL"),
                "pressure_strength": yahoo_analysis.get("pressure_strength", 0.0)
            }
            
            # Initialize market analysis engine for future candle prediction
            from core.engines.prediction_engine import PredictionEngine
            from core.session.session_manager import session_manager
            strategy_config = self.config.STRATEGY_CONFIGS.get(strategy_name, self.config.STRATEGY_CONFIGS["standard"])
            
            # Store prediction engine as instance variable for market analysis
            self.prediction_engine = PredictionEngine()
            
            # Initialize reactive engine for emergency execution
            from core.engines.reactive_engine import ReactiveEngine
            self.reactive_engine = ReactiveEngine()
            
            # Analyze market for future candle prediction
            market_analysis = self.prediction_engine.analyze_market_for_prediction(current_price, market_data)
            
            if not market_analysis:
                logger.error("❌ Failed to analyze market for prediction: No analysis returned")
                return None
            
            # Generate candle data for visualization
            candle_data = self.prediction_engine.generate_candle_data(current_price, market_data)
            
            if not candle_data:
                candle_data = {"historical": [], "predicted": []}
            
            # Store market analysis for dashboard display
            from core.dashboard.dashboard_data_manager import simple_rtm
            
            signal_data = {
                "type": "MARKET_ANALYSIS",
                "market_regime": market_analysis.get("market_regime", "UNKNOWN"),
                "prediction_readiness": market_analysis.get("prediction_readiness", {}),
                "reasoning": f"Market analysis: {market_analysis.get('market_regime', 'UNKNOWN')} regime",
                "rsi": market_analysis.get("rsi", 50.0),
                "trend": market_analysis.get("trend", "NEUTRAL"),
                "volatility_category": market_analysis.get("volatility_category", "MODERATE"),
                "volume_category": market_analysis.get("volume_category", "NORMAL"),
                "strategy_used": strategy_name,  # Include strategy information
                "candleData": candle_data,  # Add candle data for dashboard
                "analysis_data": {
                    "analysis_type": market_analysis.get("analysis_type", "MARKET_ANALYSIS"),
                    "session_strategy": strategy_name,
                    "market_analysis": market_analysis,
                    "timestamp": market_analysis.get("timestamp", 0)
                }
            }
            
            simple_rtm.add_signal(signal_data)
            
            # ANALYZE & STORE MARKET CONDITIONS for dashboard display
            from core.session.session_manager import session_manager
            market_conditions_data = global_conditions_analyzer.analyze_trading_conditions(
                market_data=market_data, 
                historical_context=session_manager.get_historical_context()
            )
            
            # Store market conditions in RTM for dashboard
            simple_rtm.update_market({
                "market_conditions": {
                    "is_tradable": market_conditions_data["is_tradable"],
                    "condition": market_conditions_data["condition"], 
                    "risk_level": market_conditions_data["risk_level"],
                    "main_reasons": market_conditions_data["reasons"][:3],
                    "confidence": market_conditions_data["confidence"],
                    # Include whale analytics and news sentiment data
                    "whale_analytics": market_conditions_data.get("whale_analytics"),
                    "news_sentiment": market_conditions_data.get("news_sentiment"),
                    "sentiment_data": market_conditions_data.get("sentiment_data")
                }
            })
            
            # Log initial analysis
            dashboard_service.update_rtm_activity(
                f"🎯 Initial market analysis: {market_analysis.get('market_regime', 'UNKNOWN')} regime, "
                f"RSI: {market_analysis.get('rsi', 50.0):.1f}, Trend: {market_analysis.get('trend', 'NEUTRAL')}",
                "INFO"
            )
            
            logger.success("✅ Initial market analysis generated and stored for dashboard")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate initial market analysis: {e}")
            # Continue session without initial analysis (degraded but functional)
    
    
    def _main_trading_loop(self, check_interval: int, hyperliquid_api,
                          market_data_service, trading_engine, dashboard_service, strategy_manager=None) -> Dict[str, Any]:
        """Main monitoring loop - simplified for candle data display"""
        initial_analysis_generated = False
        
        logger.info(f"🔄 Starting continuous monitoring loop (interval: {check_interval}s)")
        
        # Continuous loop - no trading logic to interfere
        while True:
            try:
                # Update session time
                if self.session_manager:
                    self.session_manager.update_session_time_if_active()
                
                # Get current price
                hyperliquid_price = market_data_service.get_hyperliquid_price()
                if not hyperliquid_price:
                    logger.warning("⚠️ Could not get Hyperliquid price, retrying...")
                    time.sleep(check_interval)
                    continue
                
                # Strategy detection and update (if StrategyManager available)
                current_strategy = "standard"  # Default fallback
                
                # Get market analysis
                yahoo_analysis = market_data_service.get_yahoo_analysis(hyperliquid_price, current_strategy)
                if not yahoo_analysis:
                    logger.warning("⚠️ Could not get market analysis, retrying...")
                    time.sleep(check_interval)
                    continue
                
                if strategy_manager:
                    # Build market data for strategy detection
                    market_data = yahoo_analysis.copy()
                    market_data["current_price"] = hyperliquid_price
                    market_data["timestamp"] = time.time()
                    
                    # Detect optimal strategy
                    optimal_strategy = strategy_manager.detect_optimal_strategy(market_data)
                    current_strategy = optimal_strategy
                
                # Update dashboard with current market data (CRITICAL for candle display)
                self._update_dashboard_market_data(hyperliquid_price, yahoo_analysis, market_data_service, dashboard_service, current_strategy)
                
                # Generate initial market analysis AFTER strategy is determined (only once)
                if not initial_analysis_generated and strategy_manager:
                    self._generate_initial_market_analysis(market_data_service, dashboard_service, current_strategy)
                    initial_analysis_generated = True
                
                # Update heartbeat with current strategy
                dashboard_service.update_heartbeat(self.session_manager, current_strategy, self.initial_balance)
                
                # Simple monitoring log
                dashboard_service.update_rtm_activity(
                    f"📊 Monitoring: ${hyperliquid_price:.2f}, RSI: {yahoo_analysis.get('rsi_5m', 50.0):.1f}, Strategy: {current_strategy}", 
                    "INFO"
                )
                
                # Wait for next iteration
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Keyboard interrupt - stopping monitoring loop")
                break
            except Exception as e:
                logger.error(f"❌ Monitoring loop error: {e}")
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
            dashboard_service.update_rtm_activity("🏁 Trading session closed gracefully", "SUCCESS")
            
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
    
    def _update_dashboard_market_data(self, hyperliquid_price: float, yahoo_analysis: Dict[str, Any], 
                                     market_data_service, dashboard_service, strategy_name: str = "standard"):
        """Update dashboard with current market data (CRITICAL for dashboard display)"""
        try:
            # Get real-time RSI (corrected by Yahoo at regular intervals for scalping accuracy)
            from core.market_data_manager import global_rsi_calculator
            if global_rsi_calculator.rsi_initialized:
                rsi_value = global_rsi_calculator.current_rsi
            else:
                # Fallback: Use Yahoo if real-time not initialized yet
                rsi_value = yahoo_analysis.get("rsi_5m", 50.0)
            
            # Get Hyperliquid market data (volume, pressure) + 5-minute volatility 
            from core.market_data_manager import market_data_manager
            hyperliquid_data = market_data_manager.get_hyperliquid_data(market_data_service.hyperliquid_api, "BTC")
            volume_data = hyperliquid_data.get("volume_data", {})
            pressure_data = hyperliquid_data.get("pressure_data", {})
            
            # Get 5-minute volatility from Hyperliquid REAL-TIME data (not stale Yahoo data)
            try:
                # Fetch real-time Hyperliquid candles for accurate volatility calculation
                hyperliquid_candles = market_data_service.hyperliquid_api.get_historical_candles("BTC", "5m", 12)
                
                if hyperliquid_candles and len(hyperliquid_candles) >= 3:
                    # Use REAL Hyperliquid data for volatility calculation
                    volatility_5m_data = market_data_manager.get_hyperliquid_volatility_analysis(
                        hyperliquid_candles, "BTC", strategy_name
                    )
                    logger.info(f"📊 Using Hyperliquid volatility: {volatility_5m_data.get('volatility_5m_category', 'UNKNOWN')}")
                else:
                    # Fallback to Yahoo data if Hyperliquid fails
                    logger.warning("⚠️ Hyperliquid candles unavailable, falling back to Yahoo volatility")
                    volatility_5m_data = {
                        "volatility_5m": yahoo_analysis.get("volatility_5m", 0.0),
                        "volatility_category": yahoo_analysis.get("volatility_5m_category", "UNKNOWN"),
                        "volatility_trend": yahoo_analysis.get("volatility_5m_trend", "UNKNOWN"),
                        "data_source": "yahoo_fallback"
                    }
            except Exception as e:
                logger.error(f"❌ Hyperliquid volatility calculation failed: {e}")
                # Fallback to Yahoo data
                volatility_5m_data = {
                    "volatility_5m": yahoo_analysis.get("volatility_5m", 0.0),
                    "volatility_category": yahoo_analysis.get("volatility_5m_category", "UNKNOWN"),
                    "volatility_trend": yahoo_analysis.get("volatility_5m_trend", "UNKNOWN"),
                    "data_source": "yahoo_error_fallback"
                }
            
            # Prepare market data for dashboard (EXACT field names expected by HTML template)
            market_data = {
                "current_price": hyperliquid_price,
                "rsi": rsi_value,
                "rsi_trend": "NEUTRAL",  # Simple RSI trend (can be enhanced later)
                
                # Trading Volume: Real-time volume from Binance WebSocket
                "trading_volume_btc": volume_data.get("real_time_volume_btc", volume_data.get("current_volume_btc", 0)),
                "trading_volume_category": volume_data.get("volume_category", "NO_DATA"),
                "volume_spike_detected": volume_data.get("volume_spike_detected", False),
                "volume_ratio": volume_data.get("volume_ratio", 1.0),
                "current_volume_usd": volume_data.get("real_time_volume_usd", volume_data.get("current_volume_usd", 0)),
                "volume_per_minute": volume_data.get("volume_per_minute", 0),
                "volume_per_second": volume_data.get("volume_per_second", 0),
                "trade_count_per_minute": volume_data.get("trade_count_per_minute", 0),
                "data_source": volume_data.get("data_source", "unknown"),
                
                # Secondary: Yahoo volume momentum (5m trading activity)
                "volume_momentum": yahoo_analysis.get("volume_5m_momentum", {}),
                "volume_spike": yahoo_analysis.get("volume_5m_spike", {}),
                "relative_volume": yahoo_analysis.get("relative_volume_5m", 1.0),
                
                # FIX: Dashboard expects 'trend_analysis.overall_trend' structure
                "trend_analysis": {
                    "overall_trend": yahoo_analysis.get("trend_5m", {}).get("trend", "NEUTRAL"),
                    "trend_5m": yahoo_analysis.get("trend_5m", {}).get("trend", "NEUTRAL"),
                    "trend_1h": yahoo_analysis.get("trend_1h", {}).get("trend", "NEUTRAL"),
                    "alignment_score": 0.5  # Default alignment score
                },
                
                # FIX: Dashboard expects 'pressure' object
                "pressure": pressure_data,
                
                # FIX: Use 5-minute candle volatility (aligned with bot's trading timeframe)
                "volatility_5m": volatility_5m_data.get("volatility_5m", 0.0),
                "volatility_category": volatility_5m_data.get("volatility_category", "NORMAL"),
                "volatility_trend": volatility_5m_data.get("volatility_trend", "NEUTRAL"),
                
                "timestamp": time.time(),
                "data_source": "clean_architecture_services"
            }
            
            # CONTINUOUS MARKET CONDITIONS ANALYSIS (update dashboard with tradability)
            from strategies.market_conditions_analyzer import global_conditions_analyzer
            
            market_conditions_input = {
                "current_price": hyperliquid_price,
                "rsi": rsi_value,
                "trend": yahoo_analysis.get("trend_5m", {}).get("trend", "NEUTRAL"),
                "volatility_5m": volatility_5m_data.get("volatility_5m", 0.0),
                "volatility_category": volatility_5m_data.get("volatility_category", "MODERATE"),
                "volume_category": volume_data.get("volume_category", "NO_DATA"),
                "timestamp": time.time()
            }
            
            # Get historical context with logging - use singleton directly
            from core.session.session_manager import session_manager
            historical_context = {}
            if session_manager:
                historical_context = session_manager.get_historical_context()
                if not session_manager.has_historical_context():
                    logger.warning("⚠️ Market conditions analysis running without historical context")
                else:
                    logger.debug("📊 Market conditions analysis using historical context")
            else:
                logger.warning("⚠️ No SessionManager available for historical context")
            
            conditions_analysis = global_conditions_analyzer.analyze_trading_conditions(
                market_data=market_conditions_input,
                historical_context=historical_context
            )
            
            # Add market conditions to market data for dashboard
            market_data["market_conditions"] = {
                "is_tradable": conditions_analysis["is_tradable"],
                "condition": conditions_analysis["condition"], 
                "risk_level": conditions_analysis["risk_level"],
                "main_reasons": conditions_analysis["reasons"][:3],
                "confidence": conditions_analysis["confidence"],
                # Include whale analytics and news sentiment data
                "whale_analytics": conditions_analysis.get("whale_analytics"),
                "news_sentiment": conditions_analysis.get("news_sentiment"),
                "sentiment_data": conditions_analysis.get("sentiment_data")
            }
            
            # Update dashboard with market data
            dashboard_service.update_rtm_market(market_data)
            
            # Also update data status
            data_status = market_data_service.get_data_update_status()
            dashboard_service.update_rtm_data_status(data_status)
            
            logger.debug(f"📊 Dashboard updated: ${hyperliquid_price:.2f}, RSI: {rsi_value:.1f}, Volume: {volume_data.get('real_time_volume_btc', volume_data.get('current_volume_btc', 0)):.1f} BTC/min, Spike: {volume_data.get('volume_spike_detected', False)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update dashboard market data: {e}")
            # Continue trading even if dashboard update fails
    
    # _calculate_5m_volatility() removed - calculation logic moved to MarketDataManager (proper responsibility)