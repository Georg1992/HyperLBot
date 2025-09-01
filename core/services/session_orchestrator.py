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
    
    def run_paper_trading_session(self, max_trades: int, check_interval: int,
                                 system_initializer, market_data_service, trading_engine, dashboard_service) -> Dict[str, Any]:
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
            self._start_session(dashboard_service)
            
            # 4. Main trading loop
            return self._main_trading_loop(max_trades, check_interval, hyperliquid_api,
                                         market_data_service, trading_engine, dashboard_service)
            
        except Exception as e:
            logger.error(f"❌ Trading session failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _start_session(self, dashboard_service):
        """Start trading session"""
        try:
            # Clear dashboard cache
            dashboard_service.rtm_updater.clear_rtm_cache()
            logger.info("🧹 Dashboard cache cleared - Fresh session data")
            
            # Start session
            self.session_manager = SessionManager()
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
            dashboard_service.update_rtm_activity(
                f"🚀 Trading bot started - standard strategy with ${self.initial_balance:.2f} initial balance", 
                "SUCCESS"
            )
            
            logger.success("🔥 Session started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start session: {e}")
    
    def _main_trading_loop(self, max_trades: int, check_interval: int, hyperliquid_api,
                          market_data_service, trading_engine, dashboard_service) -> Dict[str, Any]:
        """Main trading loop"""
        trades_placed = 0
        
        logger.info(f"🔄 Starting main trading loop (max_trades: {max_trades}, interval: {check_interval}s)")
        
        while trades_placed < max_trades:
            try:
                # Update heartbeat
                dashboard_service.update_heartbeat(self.session_manager, "standard", self.initial_balance)
                
                # Update session time
                if self.session_manager:
                    self.session_manager.update_session_time_if_active()
                
                # Get current price
                hyperliquid_price = market_data_service.get_hyperliquid_price()
                if not hyperliquid_price:
                    logger.warning("⚠️ Could not get Hyperliquid price, retrying...")
                    time.sleep(check_interval)
                    continue
                
                # Get market analysis
                yahoo_analysis = market_data_service.get_yahoo_analysis(hyperliquid_price)
                if not yahoo_analysis:
                    logger.warning("⚠️ Could not get market analysis, retrying...")
                    time.sleep(check_interval)
                    continue
                
                # Update dashboard with current market data (CRITICAL - was missing!)
                self._update_dashboard_market_data(hyperliquid_price, yahoo_analysis, market_data_service, dashboard_service)
                
                # Check for trading signal
                signal = trading_engine.should_trade(hyperliquid_price, yahoo_analysis, hyperliquid_api)
                
                if signal["should_trade"]:
                    # Place trade
                    success = trading_engine.place_paper_trade(
                        signal["side"], 
                        signal.get("size", 0.001), 
                        signal.get("leverage", 30),
                        signal
                    )
                    
                    if success:
                        trades_placed += 1
                        dashboard_service.update_rtm_activity(
                            f"🚀 {signal['side']} trade placed #{trades_placed}", 
                            "SUCCESS"
                        )
                        logger.success(f"✅ Trade #{trades_placed} placed: {signal['side']}")
                    else:
                        dashboard_service.update_rtm_activity("❌ Trade placement failed", "ERROR")
                else:
                    # Log no-trade reason
                    dashboard_service.update_rtm_activity(f"📊 No trade: {signal['reason']}", "INFO")
                
                # Check position exits
                trading_engine.check_position_exits(hyperliquid_price)
                
                # Generate predictions for dashboard (PASS prediction_engine!)
                dashboard_service.generate_and_log_prediction(
                    hyperliquid_price, yahoo_analysis, 
                    prediction_engine=trading_engine.prediction_engine, 
                    strategy_name="standard"
                )
                
                # Wait for next iteration
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Keyboard interrupt - stopping trading loop")
                break
            except Exception as e:
                logger.error(f"❌ Trading loop error: {e}")
                time.sleep(check_interval)
        
        # End session
        self._end_session(dashboard_service)
        
        return {
            "success": True,
            "trades_placed": trades_placed,
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
                                     market_data_service, dashboard_service):
        """Update dashboard with current market data (CRITICAL for dashboard display)"""
        try:
            # Get RSI data
            rsi_data = market_data_service.get_yahoo_baseline_rsi_data(hyperliquid_price)
            rsi_value = rsi_data.get("rsi", 50.0)
            
            # Get Hyperliquid market data (volume, pressure) + 5-minute volatility 
            from core.market_data_manager import market_data_manager
            hyperliquid_data = market_data_manager.get_hyperliquid_data(market_data_service.hyperliquid_api, "BTC")
            volume_data = hyperliquid_data.get("volume_data", {})
            pressure_data = hyperliquid_data.get("pressure_data", {})
            
            # Get 5-minute volatility from yahoo_analysis (already calculated by MarketDataManager)
            volatility_5m_value = yahoo_analysis.get("volatility_5m", 0.0)
            volatility_5m_data = market_data_service.categorize_5m_volatility_for_trading(volatility_5m_value)
            
            # Prepare market data for dashboard (EXACT field names expected by HTML template)
            market_data = {
                "current_price": hyperliquid_price,
                "rsi": rsi_value,
                "rsi_trend": rsi_data.get("rsi_trend", "NEUTRAL"),
                
                # FIX: Dashboard expects 'volume_depth' field (use correct analyzer field!)
                "volume_depth": volume_data.get("volume_depth", 0),
                "volume_category": volume_data.get("volume_category", "NORMAL"),
                "order_flow": volume_data.get("order_flow", "NEUTRAL"),
                "depth_analysis": volume_data.get("depth_analysis", "UNKNOWN"),
                
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
            
            # Update dashboard with market data
            dashboard_service.update_rtm_market(market_data)
            
            # Also update data status
            data_status = market_data_service.get_data_update_status()
            dashboard_service.update_rtm_data_status(data_status)
            
            logger.debug(f"📊 Dashboard updated: ${hyperliquid_price:.2f}, RSI: {rsi_value:.1f}, Volume: {volume_data.get('volume_depth', 0):.1f} BTC")
            
        except Exception as e:
            logger.error(f"❌ Failed to update dashboard market data: {e}")
            # Continue trading even if dashboard update fails
    
    def _calculate_5m_volatility(self, market_data_service) -> Dict[str, Any]:
        """Calculate 5-minute volatility using centralized VolatilityCalculator (eliminates redundancy)"""
        try:
            # Get recent 5-minute candles (last 25 candles = ~2 hours)
            candles_5m = market_data_service.historical_data_coordinator.yahoo_fetcher.get_klines("BTC-USD", "5m", 25)
            
            if not candles_5m or len(candles_5m) < 10:
                return {"volatility_5m": 0.0, "volatility_category": "UNKNOWN", "volatility_trend": "UNKNOWN"}
            
            # Use centralized VolatilityCalculator (eliminates duplicate calculation)
            from core.market_data_manager import market_data_manager
            volatility_5m = market_data_manager.calculate_volatility(candles_5m[-20:], 20)  # Last 20 periods
            
            # Categorize based on 5-minute trading relevance
            if volatility_5m > 0.015:      # > 1.5%
                category = "EXTREME"
                trend = "VOLATILE"
            elif volatility_5m > 0.008:    # > 0.8%  
                category = "HIGH"
                trend = "ACTIVE"
            elif volatility_5m > 0.004:    # > 0.4%
                category = "MODERATE" 
                trend = "NORMAL"
            elif volatility_5m > 0.002:    # > 0.2%
                category = "LOW"
                trend = "QUIET"
            else:                          # < 0.2%
                category = "VERY_LOW"
                trend = "BORING"
            
            logger.debug(f"📊 5m Volatility: {volatility_5m:.6f} ({volatility_5m*100:.4f}%) → {category}")
            
            return {
                "volatility_5m": volatility_5m,
                "volatility_category": category,
                "volatility_trend": trend,
                "calculation_method": "centralized_volatility_calculator",
                "timeframe": "5_minutes",
                "data_source": "yahoo_5m_candles_via_manager"
            }
            
        except Exception as e:
            logger.error(f"❌ 5m volatility calculation failed: {e}")
            return {"volatility_5m": 0.0, "volatility_category": "ERROR", "volatility_trend": "ERROR"}