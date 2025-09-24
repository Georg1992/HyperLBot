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
from core.session.session_manager import SessionManager

class SessionOrchestrator:
    """Session orchestration service - handles trading loop and lifecycle"""
    
    def __init__(self, config, initial_balance: float):
        self.config = config
        self.initial_balance = initial_balance
        self.session_manager = None
        self.weekly_trend_analysis = {}
        
        # Initialize unified AI system
        try:
            from core.ai import global_unified_ai_system
            self.ai_system = global_unified_ai_system
            logger.info("🤖 Unified AI system initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize AI system: {e}")
            self.ai_system = None
        
        # Initialize liquidation hunting system
        try:
            from core.strategies.liquidation_hunting import global_liquidation_hunter
            self.liquidation_hunter = global_liquidation_hunter
            self.liquidation_hunter.start_monitoring()
            logger.info("🎯 Liquidation hunting system initialized and monitoring started")
        except Exception as e:
            logger.warning(f"⚠️ Liquidation hunting initialization failed: {e}")
            self.liquidation_hunter = None
        
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
            
            # Get comprehensive Hyperliquid data for ML-ready market analysis
            from core.market_data_manager import market_data_manager
            hyperliquid_data = market_data_manager.get_hyperliquid_data(market_data_service.hyperliquid_api, "BTC")
            
            # Get multi-timeframe volatility analysis
            try:
                multi_timeframe_volatility = market_data_manager.get_multi_timeframe_volatility_analysis(
                    market_data_service.hyperliquid_api, "BTC", strategy_name
                )
            except Exception as e:
                logger.warning(f"⚠️ Multi-timeframe volatility failed in initial analysis: {e}")
                multi_timeframe_volatility = {
                    "volatility_5m": 0.0,
                    "volatility_5m_category": "UNKNOWN",
                    "volatility_1m": 0.0,
                    "volatility_1h": 0.0,
                    "volatility_1d": 0.0,
                    "data_source": "fallback"
                }
            
            # COMPREHENSIVE MARKET DATA for ML implementation
            market_data = {
                # Core price and technical data
                "current_price": current_price,
                "rsi_5m": rsi_data.get("rsi", yahoo_analysis.get("rsi_5m", 50.0)),
                "rsi": rsi_data.get("rsi", yahoo_analysis.get("rsi_5m", 50.0)),  # Keep both for compatibility
                "trend_5m": yahoo_analysis.get("trend_5m", {}),
                "trend": yahoo_analysis.get("trend_5m", {}).get("direction", "NEUTRAL"),  # Keep both for compatibility
                
                # Multi-timeframe volatility data
                "volatility_5m": multi_timeframe_volatility.get("volatility_5m", 0.0),
                "volatility_5m_category": multi_timeframe_volatility.get("volatility_5m_category", "UNKNOWN"),
                "volatility_1m": multi_timeframe_volatility.get("volatility_1m", 0.0),
                "volatility_1h": multi_timeframe_volatility.get("volatility_1h", 0.0),
                "volatility_1d": multi_timeframe_volatility.get("volatility_1d", 0.0),
                "volatility_category": multi_timeframe_volatility.get("volatility_5m_category", "UNKNOWN"),
                
                # Volume data
                "volume_5m": yahoo_analysis.get("volume_5m", 0.0),
                "volume_category": yahoo_analysis.get("volume_category", "UNKNOWN"),
                "volume_data": hyperliquid_data.get("volume_data", {}),
                
                # Pressure and order book data
                "pressure": yahoo_analysis.get("pressure", "NEUTRAL"),
                "pressure_strength": yahoo_analysis.get("pressure_strength", 0.0),
                "pressure_data": hyperliquid_data.get("pressure_data", {}),
                
                # Market analysis data for ML
                "orderbook_analysis": hyperliquid_data.get("orderbook_analysis", {}),
                "funding_analysis": hyperliquid_data.get("funding_analysis", {}),
                "volume_profile_analysis": hyperliquid_data.get("volume_profile_analysis", {}),
                "cross_asset_analysis": hyperliquid_data.get("cross_asset_analysis", {}),
                "onchain_analysis": hyperliquid_data.get("onchain_analysis", {}),
                "pattern_analysis": hyperliquid_data.get("pattern_analysis", {}),
                
                # Timestamp and data source
                "timestamp": time.time(),
                "data_source": "comprehensive_ml_ready"
            }
            
            # Reactive engine functionality now integrated into AI execution layer
            self.reactive_engine = None
            
            # Market analysis removed - to be redesigned
            
            # Generate basic candle data for visualization (simplified)
            candle_data = {
                "current_price": current_price,
                "timestamp": time.time(),
                "data_source": "simplified"
            }
            
            # Store market analysis for dashboard display
            from core.dashboard.dashboard_data_manager import simple_rtm
            
            signal_data = {
                "type": "MARKET_ANALYSIS",
                "market_regime": "UNKNOWN",
                "prediction_readiness": {},
                "reasoning": "Market analysis: UNKNOWN regime",
                "rsi": 50.0,
                "trend": "NEUTRAL",
                "volatility_category": "MODERATE",
                "volume_category": "NORMAL",
                "strategy_used": strategy_name,  # Include strategy information
                "candleData": candle_data,  # Add candle data for dashboard
                "ml_predictions": {
                    "trading_prediction": {},
                    "analysis_type": "TRADITIONAL_FALLBACK",
                    "confidence": 0.0
                },
                "analysis_data": {
                    "analysis_type": "MARKET_ANALYSIS",
                    "session_strategy": strategy_name,
                    "market_analysis": {},
                    "timestamp": time.time()
                }
            }
            
            simple_rtm.add_prediction(signal_data)
            
            # Add ML performance metrics to dashboard
            self._add_ml_metrics_to_dashboard()
            
            # ANALYZE & STORE MARKET CONDITIONS for dashboard display
            from core.session.session_manager import session_manager
            market_conditions_data = global_conditions_analyzer.analyze_trading_conditions(
                market_data=market_data, 
                historical_context=session_manager.get_historical_context()
            )
            
            # Get support/resistance levels from historical analysis (computed once at startup)
            from core.session.session_manager import session_manager
            historical_context = session_manager.get_historical_context()
            major_levels = historical_context.get("major_levels", {}) if historical_context else {}
            
            # Format support/resistance data for dashboard
            support_resistance_data = {
                "key_levels": major_levels.get("key_levels", []),
                "strongest_support": major_levels.get("strongest_support", 0.0),
                "strongest_resistance": major_levels.get("strongest_resistance", 0.0),
                "timeframe": "historical",
                "candles_analyzed": major_levels.get("timeframes_analyzed", {}).get("hourly", 0),
                "analysis_confidence": major_levels.get("analysis_confidence", 0.0)
            }
            
            # Store market conditions in RTM for dashboard
            simple_rtm.update_market({
                "market_conditions": {
                    "condition": market_conditions_data["condition"],
                    "risk_level": market_conditions_data["risk_level"],
                    "reasons": market_conditions_data.get("reasons", []),  # Use 'reasons' instead of 'factors'
                    "positive_factors": market_conditions_data.get("positive_factors", []),
                    "risk_factors": market_conditions_data.get("risk_factors", []),
                    "market_status": market_conditions_data.get("market_status", "NEUTRAL")  # Add 7-day market status
                },
                "support_resistance": support_resistance_data  # Add support/resistance levels
            })
            
            # Log initial analysis
            dashboard_service.update_rtm_activity(
                f"🎯 Initial market analysis: {yahoo_analysis.get('market_regime', 'UNKNOWN')} regime, "
                f"RSI: {rsi_data.get('rsi', 50.0):.1f}, Trend: {yahoo_analysis.get('trend', 'NEUTRAL')}",
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
    
    def _build_complete_market_data(self, hyperliquid_data: Dict[str, Any], 
                                   hyperliquid_price: float, yahoo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Build complete market data structure for AI system with all required fields"""
        try:
            # Start with hyperliquid data
            complete_data = hyperliquid_data.copy()
            
            # Add missing fields that strategy selector expects
            complete_data.update({
                # Price data
                "current_price": hyperliquid_price,
                
                # Technical indicators
                "rsi": yahoo_analysis.get("rsi_5m", 50.0),
                "rsi_5m": yahoo_analysis.get("rsi_5m", 50.0),
                
                # Volatility data
                "volatility_5m": yahoo_analysis.get("volatility_5m", 0.001),
                "volatility_5m_category": yahoo_analysis.get("volatility_5m_category", "LOW"),
                "volatility_5m_trend": yahoo_analysis.get("volatility_5m_trend", "NEUTRAL"),
                
                # Trend data
                "trend_5m": yahoo_analysis.get("trend_5m", {"trend": "NEUTRAL", "strength": 0.5}),
                "trend_analysis": yahoo_analysis.get("trend_analysis", {"overall_trend": "NEUTRAL", "alignment_score": 0.5}),
                
                # Volume data
                "hyperliquid_volume": hyperliquid_data.get("volume_data", {}),
                
                # Sentiment data
                "sentiment_data": yahoo_analysis.get("sentiment_data", {"index_value": 50, "sentiment_signals": {}}),
                
                # External data
                "whale_analytics": yahoo_analysis.get("whale_analytics", {"whale_activity": {"activity_level": "low"}}),
                "news_sentiment": yahoo_analysis.get("news_sentiment", {"sentiment": {"classification": "neutral"}}),
                
                # Support/Resistance data
                "support_resistance": yahoo_analysis.get("support_resistance", {"key_levels": []}),
                
                # Volatility change detection
                "volatility_change": {
                    "change_detected": False,
                    "change_direction": "STABLE",
                    "urgency": "LOW"
                }
            })
            
            return complete_data
            
        except Exception as e:
            logger.error(f"❌ Failed to build complete market data: {e}")
            # Return minimal data structure
            return {
                "current_price": hyperliquid_price,
                "rsi": 50.0,
                "rsi_5m": 50.0,
                "volatility_5m": 0.001,
                "volatility_5m_category": "LOW",
                "trend_5m": {"trend": "NEUTRAL", "strength": 0.5},
                "hyperliquid_volume": {},
                "sentiment_data": {"index_value": 50, "sentiment_signals": {}},
                "whale_analytics": {"whale_activity": {"activity_level": "low"}},
                "news_sentiment": {"sentiment": {"classification": "neutral"}},
                "support_resistance": {"key_levels": []},
                "volatility_change": {"change_detected": False, "change_direction": "STABLE", "urgency": "LOW"}
            }
    
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
            pattern_analysis = hyperliquid_data.get("pattern_analysis", {})
            
            # Generate clean ML predictions and reactive trades
            current_prediction = None
            reactive_trade = None
            
            if self.ai_system:
                try:
                    # Build complete market data structure for AI system
                    complete_market_data = self._build_complete_market_data(hyperliquid_data, hyperliquid_price, yahoo_analysis)
                    
                    # Ensure AI system is initialized (only once per session)
                    if not hasattr(self, '_ai_system_initialized') or not self._ai_system_initialized:
                        logger.info("🔧 Initializing AI system (first time)...")
                        readiness = self.ai_system.initialize_system(complete_market_data)
                        if not readiness.is_ready:
                            logger.warning(f"⚠️ AI system initialization failed: {len(readiness.errors)} errors")
                            current_prediction = None
                        else:
                            logger.success("✅ AI system initialized successfully")
                            self._ai_system_initialized = True
                    
                    # Use unified AI system for analysis and trading
                    ai_results = self.ai_system.analyze_and_trade(hyperliquid_price, complete_market_data)
                    
                    if "error" not in ai_results:
                        # Extract prediction from AI results
                        analysis = ai_results.get("analysis", {})
                        execution = ai_results.get("execution", {})
                        adaptive_analysis = ai_results.get("adaptive_analysis", {})
                        adaptive_execution = ai_results.get("adaptive_execution", {})
                        
                        # Set current prediction for dashboard display
                        if analysis.get("strategy"):
                            # Get actual prediction from AI results if available
                            ai_prediction = ai_results.get("analysis", {}).get("prediction")
                            ai_reactive = ai_results.get("analysis", {}).get("reactive_trade")
                            
                            if ai_reactive:
                                # Use reactive trade data
                                current_prediction = {
                                    "direction": ai_reactive.get("direction", "BUY"),
                                    "confidence": ai_reactive.get("confidence", 0.8),
                                    "strategy": "reactive",
                                    "reasoning": ai_reactive.get("reasoning", "Reactive trade"),
                                    "timestamp": ai_reactive.get("timestamp", time.time()),
                                    "is_reactive": True,
                                    "urgency": ai_reactive.get("urgency", "HIGH")
                                }
                            elif ai_prediction:
                                # Use regular prediction data (now includes current prediction even if discarded)
                                current_prediction = {
                                    "direction": ai_prediction.get("direction", "HOLD"),
                                    "confidence": ai_prediction.get("confidence", 0.0),
                                    "strategy": ai_prediction.get("strategy", analysis.get("strategy", "unknown")),
                                    "reasoning": ai_prediction.get("reasoning", "AI prediction"),
                                    "timestamp": ai_prediction.get("timestamp", time.time()),
                                    "entry_price": ai_prediction.get("entry_price", 0),
                                    "size_btc": ai_prediction.get("size_btc", 0),
                                    "stop_loss": ai_prediction.get("stop_loss", 0),
                                    "target_price": ai_prediction.get("target_price", 0),
                                    "is_discarded": ai_prediction.get("is_discarded", False)
                                }
                            else:
                                # Fallback to analysis data
                                current_prediction = {
                                    "direction": "HOLD",
                                    "confidence": analysis.get("analysis_confidence", 0.3),
                                    "strategy": analysis.get("strategy", "unknown"),
                                    "reasoning": analysis.get("reasoning", "AI analysis - no trade"),
                                    "timestamp": time.time()
                                }
                            
                            logger.info(f"🤖 AI analysis: {analysis['strategy']} strategy "
                                       f"(confidence: {analysis['analysis_confidence']:.2f})")
                            
                            if execution.get("reactive_trades", 0) > 0:
                                logger.info(f"⚡ Reactive trades executed: {execution['reactive_trades']}")
                            if execution.get("predictions_executed", 0) > 0:
                                logger.info(f"🎯 Predictions executed: {execution['predictions_executed']}")
                    else:
                        logger.warning(f"⚠️ AI analysis failed: {ai_results.get('error')}")
                        current_prediction = None
                            
                except Exception as e:
                    logger.warning(f"⚠️ AI analysis failed: {e}")
                    current_prediction = None
            else:
                logger.warning("⚠️ AI system not available")
                current_prediction = None
            
            # Get multi-timeframe volatility from Hyperliquid REAL-TIME data
            try:
                # Get comprehensive multi-timeframe volatility analysis
                multi_timeframe_volatility = market_data_manager.get_multi_timeframe_volatility_analysis(
                    market_data_service.hyperliquid_api, "BTC", strategy_name
                )
                
                # Log the primary 5m volatility for monitoring
                if "volatility_5m" in multi_timeframe_volatility:
                    # logger.info(f"📊 Multi-timeframe volatility: 5m={multi_timeframe_volatility['volatility_5m']:.6f} ({multi_timeframe_volatility['volatility_5m']*100:.4f}%) → {multi_timeframe_volatility['volatility_5m_category']}")
                    pass  # Placeholder for future logging
                
                # Log other timeframes if available
                for timeframe in ["1m", "1h", "1d"]:
                    vol_key = f"volatility_{timeframe}"
                    if vol_key in multi_timeframe_volatility:
                        # logger.debug(f"📊 {timeframe} volatility: {multi_timeframe_volatility[vol_key]:.6f} ({multi_timeframe_volatility[vol_key]*100:.4f}%) → {multi_timeframe_volatility.get(f'{vol_key}_category', 'UNKNOWN')}")
                        pass  # Placeholder for future debug logging
                
                volatility_5m_data = multi_timeframe_volatility
                
            except Exception as e:
                # Fallback to Yahoo data if Hyperliquid fails
                logger.warning(f"⚠️ Multi-timeframe volatility failed: {e}, falling back to Yahoo volatility")
            volatility_5m_data = {
                "volatility_5m": yahoo_analysis.get("volatility_5m", 0.0),
                    "volatility_5m_category": yahoo_analysis.get("volatility_5m_category", "UNKNOWN"),
                    "volatility_5m_trend": yahoo_analysis.get("volatility_5m_trend", "UNKNOWN"),
                    "data_source": "yahoo_fallback"
            }
            
            # Prepare market data for dashboard (EXACT field names expected by HTML template)
            market_data = {
                "current_price": hyperliquid_price,
                "rsi": rsi_value,
                "rsi_trend": "NEUTRAL",  # Simple RSI trend
                
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
                "volatility_5m_category": volatility_5m_data.get("volatility_5m_category", "NORMAL"),
                "volatility_5m_trend": volatility_5m_data.get("volatility_5m_trend", "NEUTRAL"),
                
                # Add multi-timeframe volatility data for dashboard
                "volatility_1m": volatility_5m_data.get("volatility_1m", 0.0),
                "volatility_1m_category": volatility_5m_data.get("volatility_1m_category", "NORMAL"),
                "volatility_1m_trend": volatility_5m_data.get("volatility_1m_trend", "NEUTRAL"),
                "volatility_1h": volatility_5m_data.get("volatility_1h", 0.0),
                "volatility_1h_category": volatility_5m_data.get("volatility_1h_category", "NORMAL"),
                "volatility_1h_trend": volatility_5m_data.get("volatility_1h_trend", "NEUTRAL"),
                "volatility_1d": volatility_5m_data.get("volatility_1d", 0.0),
                "volatility_1d_category": volatility_5m_data.get("volatility_1d_category", "NORMAL"),
                "volatility_1d_trend": volatility_5m_data.get("volatility_1d_trend", "NEUTRAL"),
                
                "timestamp": time.time(),
                "data_source": volume_data.get("data_source", "hyperliquid_candles")
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
            
            # REAL-TIME SUPPORT/RESISTANCE DETECTION (update every 5 seconds)
            # Ensure current price is valid before S/R analysis
            if not hyperliquid_price or hyperliquid_price <= 0:
                logger.error(f"❌ Invalid current price for S/R analysis: {hyperliquid_price}")
                raise ValueError(f"Invalid current price: {hyperliquid_price}")
            
            logger.info(f"📊 S/R Analysis: Current price = ${hyperliquid_price:.2f}")
            real_time_sr_data = self._calculate_real_time_support_resistance(
                market_data_service.hyperliquid_api, hyperliquid_price, strategy_name
            )
            
            # Add market conditions to market data for dashboard
            market_data["market_conditions"] = {
                "condition": conditions_analysis["condition"], 
                "risk_level": conditions_analysis["risk_level"],
                "main_reasons": conditions_analysis["reasons"][:3],
                "market_status": conditions_analysis.get("market_status", "NEUTRAL"),
                # Include whale analytics and news sentiment data
                "whale_analytics": conditions_analysis.get("whale_analytics"),
                "news_sentiment": conditions_analysis.get("news_sentiment"),
                "sentiment_data": conditions_analysis.get("sentiment_data")
            }
            
            # Add pattern analysis data to market data for chart visualization (MUST be before candle data generation)
            market_data["pattern_analysis"] = pattern_analysis
            
            # Add current candle data for chart display
            try:
                # Get current 5m candles for chart (force refresh every 30 seconds for real-time updates)
                current_time = time.time()
                force_refresh = not hasattr(self, '_last_candle_refresh') or (current_time - self._last_candle_refresh) > 30
                current_candles = market_data_manager.get_historical_candles("BTC", "5m", 20, force_refresh=force_refresh)
                
                if force_refresh:
                    self._last_candle_refresh = current_time
                if current_candles:
                    # Update ongoing candle with real-time price for live updates
                    # The ongoing candle is now included in current_candles array (marked with is_ongoing: true)
                    ongoing_candle = None
                    if current_candles:
                        last_candle = current_candles[-1]
                        if last_candle.get('is_ongoing', False) and hyperliquid_price:
                            # Update the ongoing candle with real-time price
                            last_candle["close"] = hyperliquid_price
                            # Also update high/low if current price exceeds them
                            if hyperliquid_price > last_candle.get("high", 0):
                                last_candle["high"] = hyperliquid_price
                            if hyperliquid_price < last_candle.get("low", 0) or last_candle.get("low", 0) == 0:
                                last_candle["low"] = hyperliquid_price
                            ongoing_candle = last_candle
                    
                    # Generate candle data structure for dashboard (simple 20-candle approach)
                    pattern_analysis_data = market_data.get("pattern_analysis", {})
                    logger.info(f"📊 Pattern analysis in market_data: {len(pattern_analysis_data.get('patterns', {}).get('reversal_patterns', []))} reversal, {len(pattern_analysis_data.get('patterns', {}).get('continuation_patterns', []))} continuation patterns")
                    
                    # CRITICAL: Ensure pattern analysis is not empty
                    if not pattern_analysis_data or not pattern_analysis_data.get('patterns'):
                        logger.warning("⚠️ Pattern analysis in market_data is empty, using default")
                        from core.market_data_manager import market_data_manager
                        pattern_analysis_data = market_data_manager._get_default_pattern_analysis()
                        logger.info(f"📊 Using default pattern analysis: {list(pattern_analysis_data.keys())}")
                    
                    candle_data = {
                        "historical": current_candles,  # Exactly 20 candles (19 historical + 1 ongoing)
                        "ongoing": ongoing_candle,      # Ongoing candle (same as last in historical)
                        "predicted": [],  # No predicted candles - using trade predictions instead
                        "pattern_analysis": pattern_analysis_data  # Include pattern data for chart overlay
                    }
                    market_data["candleData"] = candle_data
                    
                    # Debug: Log final candle data pattern analysis
                    final_candle_pattern_analysis = candle_data.get("pattern_analysis", {})
                    logger.info(f"📊 Final candle data pattern analysis: {len(final_candle_pattern_analysis.get('patterns', {}).get('reversal_patterns', []))} reversal, {len(final_candle_pattern_analysis.get('patterns', {}).get('continuation_patterns', []))} continuation patterns")
                    
                    # Debug: Log candle data structure
                    # logger.info(f"🕯️ Simple 20-candle window: {len(current_candles)} candles, ongoing: {ongoing_candle is not None}")
                    if ongoing_candle:
                        # logger.info(f"🕯️ Ongoing candle: O=${ongoing_candle.get('open', 0):.2f} C=${ongoing_candle.get('close', 0):.2f}")
                        pass  # Placeholder for future logging
                    
                    # Debug: Log candle data details
                    latest_candle = current_candles[-1] if current_candles else None
                    if latest_candle:
                        latest_time = latest_candle.get('timestamp', 0)
                        latest_close = latest_candle.get('close', 0)
                        # logger.info(f"📊 Updated candle data: {len(current_candles)} candles, latest: ${latest_close:.2f} at {latest_time}")
                    else:
                        logger.debug(f"📊 Added {len(current_candles)} candles to dashboard data")
            except Exception as e:
                logger.warning(f"⚠️ Failed to add candle data to dashboard: {e}")
            
            # Add real-time support/resistance data to market data
            market_data["support_resistance"] = real_time_sr_data
            
            # Add clean ML prediction to market data
            if current_prediction:
                market_data["ml_prediction"] = current_prediction
                logger.debug(f"🎯 Added ML prediction to market data: {current_prediction['direction']} "
                           f"(confidence: {current_prediction['confidence']:.2f})")
            else:
                market_data["ml_prediction"] = None
            
            # Debug: Log volatility data being sent
            # logger.info(f"📊 Sending volatility data to dashboard: 5m={market_data.get('volatility_5m', 0):.6f} ({market_data.get('volatility_5m_category', 'UNKNOWN')})")
            
            # Add liquidation hunting data to market data
            liquidation_data = self._get_liquidation_hunting_data()
            market_data["liquidation_hunting"] = liquidation_data
            
            # Add ML performance data to market data
            ml_performance_data = self._get_ml_performance_data()
            market_data["ml_performance"] = ml_performance_data
            
            # Add AI system status data
            if self.ai_system:
                ai_system_status = self.ai_system.get_system_status()
                # Format AI system status for dashboard display
                formatted_ai_status = {
                    "is_ready": ai_system_status.get("initialization", {}).get("is_ready", False),
                    "data_sources_ready": f"{ai_system_status.get('initialization', {}).get('available_sources', 0)}/{ai_system_status.get('initialization', {}).get('data_sources', 0)}",
                    "active_trades": ai_system_status.get("execution", {}).get("active_trades", 0),
                    "total_trades": ai_system_status.get("execution", {}).get("total_trades", 0),
                    "win_rate": f"{ai_system_status.get('execution', {}).get('win_rate', 0.0):.1f}%",
                    "daily_pnl": f"${ai_system_status.get('execution', {}).get('daily_pnl', 0.0):.2f}",
                    "initialization": ai_system_status.get("initialization", {}),
                    "execution": ai_system_status.get("execution", {}),
                    "analysis": ai_system_status.get("analysis", {})
                }
                market_data["ai_system_status"] = formatted_ai_status
                
                # Add adaptive analysis data to market data
                if adaptive_analysis:
                    market_data["adaptive_analysis"] = adaptive_analysis
                    logger.debug(f"🧠 Added adaptive analysis data to market data: {len(adaptive_analysis.get('new_predictions', []))} new, {len(adaptive_analysis.get('adapted_predictions', []))} adapted")
                
                # CRITICAL: Sync AI execution layer trades to RTM for dashboard display
                try:
                    self.ai_system.execution_layer.sync_trades_to_rtm()
                    logger.debug(f"🔄 Synced AI execution layer trades to RTM")
                except Exception as e:
                    logger.error(f"❌ Failed to sync AI trades to RTM: {e}")
            
            # Update dashboard with market data
            dashboard_service.update_rtm_market(market_data)
            
            # Also update data status
            data_status = market_data_service.get_data_update_status()
            dashboard_service.update_rtm_data_status(data_status)
            
            # logger.debug(f"📊 Dashboard updated: ${hyperliquid_price:.2f}, RSI: {rsi_value:.1f}, Volume: {volume_data.get('real_time_volume_btc', volume_data.get('current_volume_btc', 0)):.1f} BTC/min, Spike: {volume_data.get('volume_spike_detected', False)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update dashboard market data: {e}")
            # Continue trading even if dashboard update fails
    
    def _get_liquidation_hunting_data(self) -> Dict[str, Any]:
        """Get current liquidation hunting data for dashboard"""
        try:
            if not self.liquidation_hunter:
                return {
                    "status": "Inactive",
                    "next_opening": None,
                    "active_markets": [],
                    "opportunities": 0
                }
            
            # Get current opportunities
            opportunities = self.liquidation_hunter.get_current_opportunities()
            
            # Get next major opening
            next_opening = self.liquidation_hunter.get_next_major_opening()
            
            # Get market session info
            session_info = self.liquidation_hunter.get_market_session_info()
            
            # Convert datetime to string for JSON serialization
            if next_opening and 'opening_time' in next_opening:
                next_opening_copy = next_opening.copy()
                if isinstance(next_opening_copy.get('opening_time'), datetime):
                    next_opening_copy['opening_time'] = next_opening_copy['opening_time'].isoformat()
                next_opening = next_opening_copy
            
            return {
                "status": "Active" if self.liquidation_hunter.is_liquidation_hunting_time() else "Monitoring",
                "next_opening": next_opening,
                "active_markets": session_info.get("active_markets", []),
                "opportunities": len(opportunities),
                "session_overlap": session_info.get("session_overlap", False),
                "liquidation_risk": session_info.get("liquidation_risk", "MODERATE")
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get liquidation hunting data: {e}")
            return {
                "status": "Error",
                "next_opening": None,
                "active_markets": [],
                "opportunities": 0
            }
    
    def _get_ml_performance_data(self) -> Dict[str, Any]:
        """Retrieves current ML performance data for the dashboard."""
        try:
            # Get ML performance data from AI system
            if self.ai_system:
                # Get execution stats from AI system
                execution_stats = self.ai_system.get_execution_stats()
                
                # Get analysis history for performance metrics
                analysis_history = self.ai_system.get_recent_analysis(10)
                
                # Calculate performance metrics
                total_analyses = len(analysis_history)
                active_trades = execution_stats.get("active_trades", 0)
                total_trades = execution_stats.get("total_trades", 0)
                win_rate = execution_stats.get("win_rate", 0)
                
                # Get actual training data count from ML system
                try:
                    from core.ml.model_training import global_model_trainer
                    training_stats = global_model_trainer.data_collector.get_data_statistics()
                    actual_training_points = training_stats.get("data_points", 0)
                except Exception as e:
                    logger.error(f"❌ Failed to get training data count: {e}")
                    actual_training_points = total_analyses  # Fallback to analysis count
                
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
                fallback_training_points = training_stats.get("data_points", 0)
            except Exception:
                fallback_training_points = 0
            
            return {
                "analysis_type": "Initializing",
                "analysis_type_detail": "System Starting",
                "training_data_points": fallback_training_points,
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
    
    def _calculate_real_time_support_resistance(self, hyperliquid_api, current_price: float, strategy_name: str) -> Dict[str, Any]:
        """Calculate real-time support/resistance levels with integrated historical data and guaranteed important levels"""
        try:
            from core.analysis.real_time.support_resistance_calculator import SupportResistanceCalculator
            sr_calculator = SupportResistanceCalculator()
            
            # Get comprehensive candle data for S/R analysis
            # 24h of 1h data (major levels) + 6h of 5m data (recent precise levels)
            candles_1h = hyperliquid_api.get_historical_candles("BTC", "1h", 24)   # Last 24 hours (major S/R levels)
            candles_5m = hyperliquid_api.get_historical_candles("BTC", "5m", 72)   # Last 6 hours (recent precise levels)
            
            # Combine all data for comprehensive level detection
            all_levels = []
            
            # Analyze 1h data for major levels
            if candles_1h and len(candles_1h) >= 10:
                sr_1h = sr_calculator.identify_key_levels(candles_1h, min_touches=2)
                for level in sr_1h.get("key_levels", []):
                    level["timeframe"] = "1h"
                    level["weight"] = 1.0
                all_levels.extend(sr_1h.get("key_levels", []))
            
            # Analyze 5m data for recent levels  
            if candles_5m and len(candles_5m) >= 10:
                sr_5m = sr_calculator.identify_key_levels(candles_5m, min_touches=2)
                for level in sr_5m.get("key_levels", []):
                    level["timeframe"] = "5m"
                    level["weight"] = 0.8
                all_levels.extend(sr_5m.get("key_levels", []))
            
            # 5. Find persistent resistance levels (always show next resistance even after breakouts)
            # Note: find_next_significant_resistance method was removed during cleanup
            # The main level detection above should already find relevant resistance levels
            
            # 6. Filtering: Always show important levels for trading decisions
            relevant_levels = []
            
            # Get all support levels below current price
            support_levels_below = [lvl for lvl in all_levels if lvl["type"] == "support" and lvl["level"] < current_price]
            # Get all resistance levels above current price
            resistance_levels_above = [lvl for lvl in all_levels if lvl["type"] == "resistance" and lvl["level"] > current_price]
            
            # Enhanced debug logging to understand the filtering
            logger.info(f"📊 S/R Filtering: Current price: ${current_price:.2f}")
            logger.info(f"📊 Total levels found: {len(all_levels)}")
            logger.info(f"📊 Support levels below price: {len(support_levels_below)}")
            logger.info(f"📊 Resistance levels above price: {len(resistance_levels_above)}")
            
            # Log all levels found for debugging
            all_support_levels = [lvl for lvl in all_levels if lvl["type"] == "support"]
            all_resistance_levels = [lvl for lvl in all_levels if lvl["type"] == "resistance"]
            
            logger.info(f"📊 All support levels found ({len(all_support_levels)}):")
            for sup in all_support_levels:
                below_current = sup['level'] < current_price
                logger.info(f"   Support: ${sup['level']:.2f} (below current: {below_current}, score: {sup.get('score', 0):.1f})")
            
            logger.info(f"📊 All resistance levels found ({len(all_resistance_levels)}):")
            for res in all_resistance_levels:
                above_current = res['level'] > current_price
                logger.info(f"   Resistance: ${res['level']:.2f} (above current: {above_current}, score: {res.get('score', 0):.1f})")
            
            # Support level selection - ALWAYS show at least 1 support level
            if support_levels_below:
                # Sort by combined score (score * weight)
                support_levels_below.sort(key=lambda x: (x.get("score", 0) * x.get("weight", 1.0)), reverse=True)
                
                # ALWAYS include at least 1 support level, up to 3 if they have decent scores
                for support in support_levels_below:
                    combined_score = support.get("score", 0) * support.get("weight", 1.0)
                    if len([l for l in relevant_levels if l["type"] == "support"]) < 1 or combined_score > 0.2:
                        relevant_levels.append(support)
                    if len([l for l in relevant_levels if l["type"] == "support"]) >= 3:
                        break
            else:
                logger.warning("⚠️ No support levels found - S/R detection needs improvement")
            
            # Resistance level selection - ALWAYS show resistance levels
            if resistance_levels_above:
                # Sort by combined score (score * weight)
                resistance_levels_above.sort(key=lambda x: (x.get("score", 0) * x.get("weight", 1.0)), reverse=True)
                
                # ALWAYS include at least 2 resistance levels, up to 5 if they have decent scores
                for resistance in resistance_levels_above:
                    combined_score = resistance.get("score", 0) * resistance.get("weight", 1.0)
                    if len([l for l in relevant_levels if l["type"] == "resistance"]) < 2 or combined_score > 0.2:
                        relevant_levels.append(resistance)
                    if len([l for l in relevant_levels if l["type"] == "resistance"]) >= 5:
                        break
                
                # Note: persistent_resistance logic was removed during cleanup
            
            # No emergency levels - let the AI work with real data only
            
            # 8. Sort by combined score (score * weight)
            relevant_levels.sort(key=lambda x: (x.get("score", 0) * x.get("weight", 1.0)), reverse=True)
            
            # 9. Get strongest support and resistance
            support_levels = [lvl for lvl in relevant_levels if lvl["type"] == "support"]
            resistance_levels = [lvl for lvl in relevant_levels if lvl["type"] == "resistance"]
            
            strongest_support = support_levels[0]["level"] if support_levels else 0.0
            strongest_resistance = resistance_levels[0]["level"] if resistance_levels else 0.0
            
            # Debug logging
            logger.info(f"📊 Support/Resistance Analysis Complete:")
            logger.info(f"   📊 Total levels detected: {len(all_levels)}")
            logger.info(f"   📊 Support levels below price: {len(support_levels_below)}")
            logger.info(f"   📊 Resistance levels above price: {len(resistance_levels_above)}")
            logger.info(f"   📊 Final relevant levels: {len(relevant_levels)}")
            
            if support_levels:
                logger.info(f"   📊 Support levels: {[(s['level'], f'score:{s.get('score', 0):.1f}', s['timeframe']) for s in support_levels[:3]]}")
            else:
                logger.warning(f"   ⚠️ No support levels found! Current price: ${current_price:.2f}")
            
            if resistance_levels:
                logger.info(f"   📊 Resistance levels: {[(r['level'], f'score:{r.get('score', 0):.1f}', r['timeframe']) for r in resistance_levels[:3]]}")
            else:
                logger.warning(f"   ⚠️ No resistance levels found! Current price: ${current_price:.2f}")
            
            return {
                "key_levels": relevant_levels[:10],  # Top 10 most relevant levels
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "timeframe": "integrated_multi_timeframe",
                "candles_analyzed": len(candles_5m) + len(candles_1h),
                "analysis_confidence": min(1.0, len(relevant_levels) / 8),  # More levels = higher confidence
                "data_source": "hyperliquid_integrated",
                "persistent_resistance": None,  # Removed during cleanup
                "level_breakdown": {
                    "support_count": len(support_levels),
                    "resistance_count": len(resistance_levels),
                    "timeframes_analyzed": len(set(lvl.get("timeframe", "unknown") for lvl in relevant_levels))
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Real-time support/resistance calculation failed: {e}")
            # NO FALLBACKS - raise the exception
            raise Exception(f"Support/resistance calculation failed: {e}")
    
    
    def _add_ml_metrics_to_dashboard(self):
        """Add ML performance metrics to the dashboard"""
        try:
            from core.ml.performance_monitor import global_performance_monitor
            from core.ml.continuous_learning import global_continuous_learning
            from core.ml.model_training import global_model_trainer
            from core.dashboard.dashboard_data_manager import simple_rtm
            
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
            
            simple_rtm.add_signal(ml_metrics_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to add ML metrics to dashboard: {e}")
    
    
