#!/usr/bin/env python3
"""
Yahoo Finance + Hyperliquid Paper Trading Bot
Uses Yahoo Finance for historical market data analysis and Hyperliquid API for real-time trading execution
"""

import time
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger
import urllib3

# Disable SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from core.api.hyperliquid_api import HyperliquidAPI
from config.config import TradingConfig
from core.constants import constants, strategy_constants, ui_constants, magic_numbers
from core.state.trade_state_manager import trade_state_manager
from core.execution.fee_manager import FeeManager
from core.analysis.historical.market_volatility_analyzer import VariabilityAnalyzer
from core.logging.trading_logger import TradingLogger
from strategies.prediction_engine import PredictionEngine
from core.execution.trade_manager import TradeManager
from core.execution.trading_execution import TradingExecution
from core.analysis.historical.market_data_analyzer import MarketDataAnalyzer
from core.data.real_time_data_updater import RTMUpdater
from core.management.position_manager import PositionManager

class YahooHyperliquidPaperTradingBot:
    def __init__(self, initial_balance: float = None, strategy_name: str = None, balance_mode: str = "simulated"):
        self.config = TradingConfig()
        self.strategy_name = strategy_name or constants.DEFAULT_STRATEGY
        self.strategy_config = self.config.STRATEGY_CONFIGS.get(self.strategy_name, strategy_constants.STANDARD_STRATEGY)
        self.hyperliquid_api = None
        self.connected = False
        self.balance_mode = balance_mode  # "real" or "simulated"
        
        # Paper trading state
        self.paper_balance = initial_balance or constants.DEFAULT_INITIAL_BALANCE
        self.initial_balance = self.paper_balance
        self.open_positions = []
        self.closed_positions = []
        self.trade_history = []
        
        # Bot heartbeat tracking
        self.heartbeat_file = os.path.join("data", "temp", "bot_heartbeat.json")
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30  # Update heartbeat every 30 seconds
        
        # Initialize current account ID
        self.current_account_id = None
        
        # Load existing open positions from previous sessions
        self.open_positions = trade_state_manager.load_open_positions()
        
        # Clean up any phantom trades from previous sessions
        trade_state_manager.cleanup_phantom_trades()
        
        # Market data storage
        self.yahoo_analysis = {}
        self.weekly_trend_analysis = {}
        self.hyperliquid_price = 0
        self.last_trade_time = 0
        self.min_interval = constants.MIN_TRADE_INTERVAL
        
        # Signal deduplication
        self.last_signal_reason = ""
        self.last_signal_price = 0
        self.last_signal_time = 0
        self.signal_cooldown = constants.SIGNAL_COOLDOWN
        
        # Price difference monitoring
        self.price_difference_threshold = constants.PRICE_DIFFERENCE_THRESHOLD
        self.last_price_difference_alert = 0
        self.price_difference_alert_cooldown = constants.PRICE_DIFFERENCE_ALERT_COOLDOWN
        
        # Analysis components
        self.fee_manager = FeeManager()
        self.variability_analyzer = VariabilityAnalyzer(lookback_periods=100)
        self.trading_logger = TradingLogger(constants.LOG_DIR)
        
        # Clean up old sessions
        self.trading_logger.cleanup_old_sessions(keep_sessions=constants.MAX_SESSIONS_TO_KEEP)
        
        # Prediction engine
        self.prediction_engine = PredictionEngine(self.strategy_config)
        
        # Advanced trade manager
        self.trade_manager = TradeManager(self.strategy_config)
        
        # Trading execution module
        self.trading_execution = TradingExecution(self)
        
        # Initialize account manager
        try:
            from core.account_manager import account_manager
            self.account_manager = account_manager
            logger.success("💰 Account Manager initialized")
        except ImportError as e:
            logger.warning(f"Account manager not available: {e}")
            self.account_manager = None
        
        # Initialize new modules
        self.market_data_analyzer = MarketDataAnalyzer()
        self.rtm_updater = RTMUpdater()
        self.position_manager = PositionManager(self)
        logger.info("🔄 New modules initialized: MarketDataAnalyzer, RTMUpdater, PositionManager")
        
        # Initialize WebSocket for real-time price streaming
        self._initialize_websocket()
        
        # TEST API CONNECTIONS AND COMPLETE INITIALIZATION
        self._test_api_connections()
        
        # Override trade manager's get_open_positions method
        self.trade_manager.get_open_positions = self.get_open_positions
        
        # Simple candle management
        self.candles_1m_buffer = []   # Rolling buffer of 120 most recent 1m candles (2h)
        self.candles_5m_buffer = []   # Rolling buffer of 60 most recent 5m candles (5h) 
        self.candles_1h_buffer = []   # Rolling buffer of 84 most recent 1h candles (3.5d)
        self.candles_1d_buffer = []   # Rolling buffer of 45 most recent 1d candles (6w)
        self.initial_analysis_complete = False
        self.market_structure = {}  # Store analyzed market structure
        
        # Multi-timeframe analysis configuration
        self.OPTIMAL_CANDLE_COUNTS = {
            "1m": 120,  # 2 hours - immediate momentum
            "5m": 60,   # 5 hours - core prediction analysis
            "1h": 84,   # 3.5 days - daily trend context
            "1d": 45    # 6 weeks - weekly/monthly trend context
        }
        
        # Leverage settings (respecting Hyperliquid 40x limit)
        self.leverage_settings = {
            "base_leverage": 30,
            "max_leverage": 40,  # Hyperliquid limit
            "min_leverage": 20,
            "cascade_leverage": 40,
            "momentum_leverage": 38
        }
        
        # Update session metadata with initial balance
        self.trading_logger.update_initial_balance(initial_balance)
        
        initial_balance_safe = initial_balance or 0.0
        logger.info(f"[CHART] Hybrid Paper Trading Bot initialized with ${initial_balance_safe:.2f} balance")
        # Whale integration removed during cleanup
        logger.info("🐋 Whale analytics integration disabled (removed)")
        
        # Ensure account manager is available
        self._ensure_account_manager()
        
        # Get current account ID for trade linking
        self._set_current_account_id()
    
    def _ensure_account_manager(self):
        """Ensure account manager is properly initialized"""
        if not hasattr(self, 'account_manager') or self.account_manager is None:
            try:
                from core.account_manager import account_manager
                self.account_manager = account_manager
                # Account manager initialized
            except ImportError as e:
                logger.warning(f"⚠️ Account manager not available: {e}")
                self.account_manager = None
    
    def _set_current_account_id(self):
        """Set current account ID for trade linking"""
        try:
            if self.account_manager and self.account_manager.account_data:
                self.current_account_id = self.account_manager.account_data.get("account_id")
                logger.info(f"🔗 Linked to account: {self.current_account_id}")
            else:
                # Generate default account ID if no account manager
                self.current_account_id = f"bot_account_{int(time.time())}"
                logger.warning(f"⚠️ No account data found, using default: {self.current_account_id}")
        except Exception as e:
            logger.error(f"❌ Error setting account ID: {e}")
            self.current_account_id = "unknown_account"
    
    def _initialize_websocket(self):
        """Initialize WebSocket for real-time price updates"""
        try:
            from core.api.hyperliquid_websocket import start_websocket
            
            logger.info("🚀 Initializing Hyperliquid WebSocket for real-time price updates...")
            
            # Start WebSocket connection
            self.websocket = start_websocket("BTC")
            
            # Wait a moment for connection to establish
            import time
            time.sleep(2)
            
            if self.websocket.is_connected():
                logger.success("✅ Hyperliquid WebSocket connected - Real-time price updates active")
                
                # Add price update callback for dashboard
                self.websocket.add_price_callback(self._on_price_update)
                
            else:
                logger.warning("⚠️ WebSocket connection failed, will use HTTP API")
                
        except ImportError:
            logger.warning("⚠️ WebSocket module not available, using HTTP API only")
        except Exception as e:
            logger.error(f"❌ WebSocket initialization failed: {e}")
    
    def _on_price_update(self, price_data: Dict[str, Any]):
        """Callback for WebSocket price updates"""
        try:
            # Calculate real market data instead of using defaults
            current_price = price_data["current_price"]
            
            # Update RSI calculator with real-time price (SINGLE UPDATE PER CYCLE)
            from core.analysis.real_time.rsi_calculator import real_time_rsi_calculator
            
            # Initialize RSI calculator if needed
            if not real_time_rsi_calculator.is_initialized:
                real_time_rsi_calculator.initialize_with_yahoo_data()
            
            # Add the current price to RSI calculator ONCE per cycle
            real_time_rsi_calculator.add_price(current_price)
            
            # Get volume data from order book analysis (real-time via WebSocket)
            try:
                volume_data = self.hyperliquid_api.get_volume_analysis("BTC")
                volume_depth = volume_data.get("current_volume", 0.0)
                volume_category = volume_data.get("volume_category", "UNKNOWN")
                order_flow = volume_data.get("order_flow", "NEUTRAL")
                depth_analysis = volume_data.get("depth_analysis", "UNKNOWN")
                
                # Cache volume data for main trading loop
                self.hyperliquid_volume_data = volume_data
        
            except Exception as e:
                volume_depth = 0.0
                volume_category = "UNKNOWN"
                order_flow = "NEUTRAL"
                depth_analysis = "UNKNOWN"
                self.hyperliquid_volume_data = None
            
            # RSI calculation is now handled in real-time with each price update
            rsi_data = real_time_rsi_calculator.calculate_rsi()
            rsi_value = rsi_data.get("rsi")
            trend_value = rsi_data.get("trend", "NEUTRAL")
            
            # Get volatility data from order book analysis
            try:
                volatility_data = self.hyperliquid_api.get_volatility_analysis("BTC")
                volatility_5m = volatility_data.get("volatility_5m", 0.0)
                volatility_category = volatility_data.get("volatility_category", "UNKNOWN")
                volatility_trend = volatility_data.get("volatility_trend", "UNKNOWN")
                spread_volatility = volatility_data.get("spread_volatility", 0.0)
        
            except Exception as e:
                volatility_5m = 0.0
                volatility_category = "UNKNOWN"
                volatility_trend = "UNKNOWN"
                spread_volatility = 0.0
            
            # Get ultimate pressure from order book analysis
            try:
                ultimate_pressure = self.hyperliquid_api.get_ultimate_pressure("BTC")
                pressure_direction = ultimate_pressure.get("direction", "NEUTRAL")
                pressure_confidence = ultimate_pressure.get("confidence", "50%")
                pressure_strength = ultimate_pressure.get("strength", magic_numbers.DEFAULT_STRENGTH)
                pressure_trend = ultimate_pressure.get("trend", "NEUTRAL")
        
            except Exception as e:
                pressure_direction = "NEUTRAL"
                pressure_confidence = "50%"
                pressure_strength = magic_numbers.DEFAULT_STRENGTH
                pressure_trend = "NEUTRAL"
            
            # Use centralized market data update - SINGLE SOURCE OF TRUTH
            self._update_market_data_centralized(current_price)
            
            # Real-time price update processed
            
        except Exception as e:
            logger.error(f"❌ Error in price update callback: {e}")
    
    def _test_api_connections(self):
        """Test API connections and set connected status"""
        try:
            logger.info("🔗 Testing API connections...")
            
            # Initialize Hyperliquid API
            self.hyperliquid_api = HyperliquidAPI()
            
            # Test Hyperliquid connection
            current_price = self.hyperliquid_api.get_current_price("BTC")
            if current_price and current_price > 0:
                current_price_safe = current_price or 0
                logger.success(f"✅ Hyperliquid API connected - BTC: ${current_price_safe:,.2f}")
                hyperliquid_ok = True
            else:
                logger.error("❌ Hyperliquid API connection failed")
                hyperliquid_ok = False
            
            # Test Yahoo Finance connection
            try:
                if self.market_data_analyzer.test_connection():
                    logger.success("✅ Yahoo Finance API connected")
                    yahoo_ok = True
                else:
                    logger.error("❌ Yahoo Finance API connection failed")
                    yahoo_ok = False
            except Exception as e:
                logger.error(f"❌ Yahoo Finance API error: {e}")
                yahoo_ok = False
            
            # Set connection status
            if hyperliquid_ok and yahoo_ok:
                self.connected = True
                logger.success("🚀 ALL APIs CONNECTED - Bot ready to trade!")
            else:
                self.connected = False
                logger.error("❌ API connection failed - Bot cannot trade")
                if not hyperliquid_ok:
                    logger.error("   • Hyperliquid API: Failed")
                if not yahoo_ok:
                    logger.error("   • Yahoo Finance API: Failed")
            
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            self.connected = False
    

    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get list of open positions for trade manager"""
        return self.trading_execution.get_open_positions()
    
    def connect(self) -> bool:
        """Connect to Hyperliquid API"""
        try:
            logger.info("🔌 Connecting to Hyperliquid...")
            
            # Test Yahoo Finance connection
            if not self.market_data_analyzer.test_connection():
                logger.error("❌ Failed to connect to Yahoo Finance")
                return False
            
            # Initialize Hyperliquid API for market data only (no account access needed)
            self.hyperliquid_api = HyperliquidAPI()
            
            # Initialize enhanced Hyperliquid simulator
            from core.api.hyperliquid_simulator import hyperliquid_simulator
            self.hyperliquid_simulator = hyperliquid_simulator
            
            # Test market data connection
            try:
                current_price = self.hyperliquid_api.get_current_price("BTC")
                if current_price:
                    logger.success(f"✅ Successfully connected to Hyperliquid API!")
                    logger.info(f"[CHART] Current BTC Price: ${current_price:,.2f} USD")
                    logger.info(f"[CHART] Paper Trading Balance: ${self.paper_balance:.2f} USD")
                else:
                    logger.warning("⚠️ Could not get current price from Hyperliquid API")
            except Exception as e:
                logger.error(f"❌ Hyperliquid API connection failed: {e}")
                return False
            
            # Paper trading mode - no real account access needed
            logger.info("[GAME] Paper trading mode - using simulated balance and positions")
            
            # Load account data if available
            if self.account_manager and self.account_manager.account_data:
                account_data = self.account_manager.account_data
                # Update paper balance with account data
                old_balance = self.paper_balance
                self.paper_balance = account_data["current_balance"]
                self.initial_balance = account_data["initial_balance"]
                logger.info(f"[CHART] Loaded account data: Balance ${old_balance:.2f} → ${self.paper_balance:.2f}, {account_data['total_trades']} total trades")
            else:
                logger.warning(f"⚠️ No account manager data available. Using initial balance: ${self.paper_balance:.2f}")
                # Try to load account data directly
                try:
                    from core.account_manager import account_manager
                    if account_manager.account_exists():
                        account_data = account_manager.load_account()
                        if account_data:
                            old_balance = self.paper_balance
                            self.paper_balance = account_data["current_balance"]
                            self.initial_balance = account_data["initial_balance"]
                            logger.info(f"[CHART] Direct account load: Balance ${old_balance:.2f} → ${self.paper_balance:.2f}, {account_data['total_trades']} total trades")
                except Exception as e:
                    logger.error(f"❌ Failed to load account data directly: {e}")
            
            # Balance and position updates handled by AccountManager (SimpleRTM integration)
            logger.info("[GAME] AccountManager handles balance and position updates")
            
            logger.info("[CHART] No real positions/orders loaded - clean simulated environment")
            logger.info(f"[GAME] Using simulated balance: ${self.paper_balance:.2f}")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            self.trading_logger.log_error({
                "type": "connection_error",
                "message": str(e),
                "details": {"account_info": account_info if 'account_info' in locals() else None}
            })
            return False
    
    def get_optimized_rsi_data(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get real-time RSI data from already-updated calculator (NO DUPLICATE UPDATES)"""
        from core.analysis.real_time.rsi_calculator import real_time_rsi_calculator
        
        # NO PRICE UPDATE HERE - RSI already updated in price callback
        # Just get the current cached RSI data
        rsi_data = real_time_rsi_calculator.calculate_rsi()
        
        return {
            "rsi": rsi_data.get("rsi", None),
            "rsi_trend": rsi_data.get("trend", "NEUTRAL"),
            "rsi_signal": rsi_data.get("signal", "NEUTRAL"),
            "momentum": rsi_data.get("trend", "NEUTRAL"),  # Use trend as momentum
            "confidence": 0.8 if rsi_data.get("rsi") is not None else magic_numbers.DEFAULT_CONFIDENCE
        }
    def get_yahoo_analysis(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get optimized market analysis from Yahoo Finance with periodic updates"""
        try:
            # Use market data analyzer
            analysis = self.market_data_analyzer.get_yahoo_analysis(hyperliquid_price)
            
            if "error" not in analysis:
                logger.info(f"[CHART] Yahoo Finance analysis: ${analysis.get('current_price', 0):,.2f} - {analysis.get('market_condition', 'UNKNOWN')}")
                return analysis
            else:
                logger.error(f"❌ Yahoo Finance analysis failed: {analysis.get('error', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo Finance analysis: {e}")
            return {}
    
    def get_hyperliquid_price(self) -> Optional[float]:
        """Get current price from Hyperliquid"""
        try:
            # Use centralized market data manager
            from core.market_data_manager import market_data_manager
            hyperliquid_data = market_data_manager.get_hyperliquid_data(self.hyperliquid_api, "BTC")
            mid_price = hyperliquid_data.get("current_price")
            
            if mid_price:
                # Update variability analyzer with new price data
                volume_data = hyperliquid_data.get("volume_data", {})
                real_volume = volume_data.get("current_volume", 100)  # Fallback to 100 if no data
                
                self.variability_analyzer.add_price_data(mid_price, volume=real_volume)
                
                return mid_price
            
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid price: {e}")
            return None
    
    def should_trade(self, hyperliquid_price: float, yahoo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """ULTIMATE INTELLIGENT TRADING: Master Fusion Engine analyzes ALL available intelligence"""
        if not yahoo_analysis or "error" in yahoo_analysis:
            return {"should_trade": False, "reason": "No market analysis available"}
        
        # 1. DETECT STRATEGY AND MARKET CONDITIONS
        current_strategy = self._auto_detect_strategy(yahoo_analysis, hyperliquid_price)
        if current_strategy != self.strategy_name:
            logger.info(f"🔄 Auto-switching strategy: {self.strategy_name} → {current_strategy}")
            self.strategy_name = current_strategy
            self.strategy_config = self.config.STRATEGY_CONFIGS.get(current_strategy, self.config.STRATEGY_CONFIGS["standard"])
        
        # 2. CHECK TIME INTERVAL
        current_time = time.time()
        min_interval = self.strategy_config["min_interval"]
        if current_time - self.last_trade_time < min_interval:
            return {"should_trade": False, "reason": f"Too soon since last trade (need {min_interval}s)"}
        
        # 3. GATHER ALL MARKET INTELLIGENCE
        # Get real-time Hyperliquid data using centralized manager
        from core.market_data_manager import market_data_manager
        hyperliquid_data = market_data_manager.get_hyperliquid_data(self.hyperliquid_api, "BTC")
        
        volume_data = hyperliquid_data.get("volume_data", {})
        volatility_data = hyperliquid_data.get("volatility_data", {})
        pressure_data = hyperliquid_data.get("ultimate_pressure_data", {})
        
        # Get optimized RSI data (already updated in price callback)
        hybrid_rsi_analysis = self.get_optimized_rsi_data()
        
        # Update variability analyzer
        real_volume = volume_data.get("current_volume", 100)
        self.variability_analyzer.add_price_data(hyperliquid_price, volume=real_volume)
        
        logger.info(f"📊 Real-time RSI: {hybrid_rsi_analysis.get('rsi', 'N/A')} | Signal: {hybrid_rsi_analysis.get('rsi_signal', 'N/A')} | Confidence: {hybrid_rsi_analysis.get('confidence', 0)*100:.1f}%")
        logger.info(f"📊 Momentum: {hybrid_rsi_analysis.get('momentum', 'N/A')} | Volume: {volume_data.get('current_volume', 0):.1f} BTC ({volume_data.get('volume_category', 'UNKNOWN')})")
        
        # 4. BUILD COMPREHENSIVE ENHANCED ANALYSIS
        enhanced_analysis = yahoo_analysis.copy()
        enhanced_analysis["hyperliquid_volume"] = volume_data
        enhanced_analysis["hyperliquid_volatility"] = volatility_data
        enhanced_analysis["hyperliquid_pressure"] = pressure_data
        enhanced_analysis["hybrid_rsi_analysis"] = hybrid_rsi_analysis
        enhanced_analysis["timestamp"] = current_time
        
        # Enhanced analysis components removed for simplicity
        
        # Get traditional prediction for fallback
        prediction_analysis = self.prediction_engine.build_price_prediction(enhanced_analysis, hyperliquid_price, self.strategy_name)
        enhanced_analysis["prediction_analysis"] = prediction_analysis
        logger.info(f"🔮 PREDICTION ENGINE: Generated analysis with keys: {list(prediction_analysis.keys()) if prediction_analysis else 'None'}")
        
        # 5. PREDICTION ENGINE ANALYSIS
        logger.info(f"🔍 TRADITIONAL SYSTEM: Checking prediction analysis - has_prediction: {prediction_analysis.get('has_prediction', False)}")
        if not prediction_analysis.get("has_prediction", False):
            return {
                "should_trade": False,
                "reason": f"No valid prediction: {prediction_analysis.get('reason', 'Unknown')}"
            }
        
        # Traditional entry analysis
        entry_analysis = self._analyze_entry_point(prediction_analysis, hyperliquid_price)
        if not entry_analysis["should_place_order"]:
            return {
                "should_trade": False,
                "reason": f"Entry analysis failed: {entry_analysis['reason']}"
            }
        
        # Traditional variability check
        variability_decision = self.variability_analyzer.should_trade_based_on_variability(entry_analysis["variability_threshold"])
        if not variability_decision["should_trade"]:
            return {
                "should_trade": False, 
                "reason": f"Variability analysis: {variability_decision['reason']}"
            }
        
        # Build traditional signal
        signal_data = {
            "should_trade": True,
            "side": entry_analysis["side"],
            "reason": f"RSI: {hybrid_rsi_analysis.get('rsi_signal', 'UNKNOWN')} - {entry_analysis['reason']}",
            "target": entry_analysis["target_price"],
            "stop": entry_analysis["stop_price"],
            "entry_price": entry_analysis["entry_price"],
            "current_price": hyperliquid_price,  # Add current price for logging
            "prediction_confidence": entry_analysis["confidence"],
            "hybrid_confidence": hybrid_rsi_analysis.get("confidence", magic_numbers.DEFAULT_CONFIDENCE),
            "optimal_params": variability_decision["optimal_trading_params"],
            "strategy_name": self.strategy_name,
            # Add market analysis data for logging (using correct field names from Yahoo analysis)
            "support_5m": enhanced_analysis.get("support_resistance_5m", {}).get("support"),
            "resistance_5m": enhanced_analysis.get("support_resistance_5m", {}).get("resistance"),
            "trend_5m": enhanced_analysis.get("trend_5m", {}).get("trend"),
            "trend_1h": enhanced_analysis.get("trend_1h", {}).get("trend"),
            "volatility_5m": enhanced_analysis.get("volatility_5m"),
            "market_condition": enhanced_analysis.get("market_condition"),
            "rsi_value": hybrid_rsi_analysis.get("rsi"),
            "momentum": hybrid_rsi_analysis.get("momentum"),
            "rsi_signal": hybrid_rsi_analysis.get("rsi_signal")
        }
        
        # Traditional quality check
        trade_decision = self.trade_manager.should_place_trade(
            signal_data, yahoo_analysis, hyperliquid_price, self.open_positions
        )
        
        if not trade_decision["should_place"]:
            return {
                "should_trade": False,
                "reason": f"Trade quality check failed: {trade_decision['reason']}"
            }
        
        # Log traditional signal
        self.trading_logger.log_signal(signal_data)
        
        # Update SimpleRTM with traditional prediction
        try:
            # Update SimpleRTM with signal
            hybrid_confidence = hybrid_rsi_analysis.get("confidence", magic_numbers.DEFAULT_CONFIDENCE)
            self._update_simple_rtm_signal({
                "type": signal_data["side"],
                "side": signal_data["side"],
                "confidence": int(hybrid_confidence * 100),
                "reason": signal_data["reason"],
                "timestamp": time.time()
            })
            
            # Update SimpleRTM with activity
            self._update_simple_rtm_activity(f"🔮 Hybrid prediction: {signal_data['side']} signal with {hybrid_confidence*100:.1f}% confidence", "INFO")
            
            logger.info(f"📊 HYBRID PREDICTION sent to SimpleRTM: {signal_data['side']} - {hybrid_confidence*100:.1f}% confidence")
        except Exception as e:
            # Could not update SimpleRTM with prediction
            pass
        
        self.last_signal_reason = signal_data["reason"]
        self.last_signal_price = hyperliquid_price
        self.last_signal_time = current_time
        
        return signal_data
    
    def check_position_exits(self, hyperliquid_price: float, current_analysis: Dict[str, Any] = None):
        """Check positions for exit conditions"""
        self.trading_execution.check_position_exits(hyperliquid_price, current_analysis)
    
    def place_paper_trade(self, side: str, size: float = 0.001, leverage: int = 30, signal_data: Dict = None) -> bool:
        """Place a paper trade"""
        return self.trading_execution.place_paper_trade(side, size, leverage, signal_data)
    
    def close_paper_position(self, position: Dict, exit_reason: str, exit_price: float):
        """Close a paper position"""
        self.trading_execution.close_paper_position(position, exit_reason, exit_price)
    
    def _analyze_entry_point(self, prediction_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Analyze entry point using prediction engine"""
        return self.prediction_engine.analyze_entry_point(prediction_analysis, current_price)
    
    def _build_price_prediction(self, yahoo_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Build price prediction using prediction engine"""
        return self.prediction_engine.build_price_prediction(yahoo_analysis, current_price, self.strategy_name)
    
    def _is_prediction_valid(self, prediction: Dict[str, Any], current_price: float) -> bool:
        """Simple prediction validation"""
        return prediction.get("confidence", 0) > magic_numbers.DEFAULT_CONFIDENCE and prediction.get("has_prediction", False)
    
    def _calculate_prediction_win_probability(self, prediction: Dict[str, Any], prediction_analysis: Dict[str, Any]) -> float:
        """Get win probability from prediction engine"""
        return self.prediction_engine.calculate_win_probability(prediction, prediction_analysis)
    
    def run_yahoo_hyperliquid_paper_trading(self, max_trades: int = 10, check_interval: int = 5):
        """Run the Hyperliquid paper trading bot"""
        if not self.connected:
            logger.error("❌ Not connected to APIs")
            return
        
        # Get weekly trend analysis before starting
        logger.info("📅 Getting weekly trend analysis for session context...")
        weekly_analysis = self.get_weekly_trend_analysis()
        
        if "error" not in weekly_analysis:
            self.weekly_trend_analysis = weekly_analysis
            logger.success("✅ Weekly trend analysis loaded successfully!")
        else:
            logger.warning("⚠️ Could not get weekly trend analysis, proceeding without it")
            self.weekly_trend_analysis = {}
        
        logger.info(f"🤖 Starting Yahoo + Hyperliquid Paper Trading Bot")
        logger.info(f"   Initial Balance: ${self.initial_balance:.2f}")
        logger.info(f"   Max Trades: {max_trades}")
        logger.info(f"   Check Interval: {check_interval} seconds (FAST REACTION MODE)")
        logger.info(f"   Max Leverage: {self.leverage_settings['max_leverage']}x")
        logger.info(f"   Data Sources: Yahoo Finance (Historical) + Hyperliquid (Real-time Price)")
        logger.info(f"   Analysis Frequency: Real-time updates (ULTRA-FAST)")
        logger.info(f"   Strategy: Auto-Detection (Standard/Low/High Volatility)")
        logger.info(f"   Weekly Context: {self.weekly_trend_analysis.get('weekly_trend', 'UNKNOWN')} ({self.weekly_trend_analysis.get('weekly_change_pct', 0):.2f}%)")
        logger.info(f"   Logging: Comprehensive Yahoo + Hyperliquid paper trading logs enabled")
        
        # Start session with RTM integration
        try:
            from core.session.session_manager import SessionManager
            
            # Clear RTM cache before starting new session
            self.rtm_updater.clear_rtm_cache()
            logger.info("🧹 RTM cache cleared - Fresh session data")
            
            # Check for ongoing sessions before starting new one
            logger.info("🔍 Checking for ongoing sessions...")
            ongoing_session = self._check_for_ongoing_session()
            if ongoing_session:
                logger.warning(f"⚠️ Found ongoing session: {ongoing_session['session_id']}")
                logger.info(f"   Status: {ongoing_session['status']}")
                logger.info(f"   Balance: ${ongoing_session['current_balance']:.2f}")
                logger.info("🔄 Will start new session and overwrite existing data...")
            
            # Start session via SessionManager
            self.session_manager = SessionManager()
            
            # SessionManager will handle cleanup internally
            logger.info("✅ SessionManager initialized")
            
            # Create initial heartbeat immediately so dashboard knows bot is running
            self._create_initial_heartbeat()
            
            session_id = self.session_manager.start_session(
                session_id=f"bot_session_{int(time.time())}",
                strategy=self.strategy_name,
                initial_balance=self.initial_balance
            )
            
            # Session and account data are managed by SessionManager and AccountManager
            # RTM will read from them automatically
            
            # Add initial activity log
            self._update_simple_rtm_activity(f"🚀 Trading bot started - {self.strategy_name} strategy with ${self.initial_balance:.2f} initial balance", "SUCCESS")
            
            logger.success("🔥 RTM integration active - Dashboard connection established")
            logger.info(f"   📊 Dashboard will receive live predictions and market data")
            
        except Exception as e:
            logger.error(f"❌ Failed to start session with RTM: {e}")
            logger.warning("⚠️ Dashboard will show offline data only")
        
        # Advanced monitoring systems removed for simplicity
        
        logger.info("=" * 50)
        
        trades_placed = 0
        
        while trades_placed < max_trades:
            try:
                current_time = time.time()
                
                # Update bot heartbeat
                self._update_heartbeat()
                
                # Update session time periodically
                if hasattr(self, 'session_manager') and self.session_manager:
                    self.session_manager.update_session_time_if_active()
                
                # Test SimpleRTM activity at loop start
                self._update_simple_rtm_activity("🔄 Main trading loop iteration", "INFO")
                
                # Update Hyperliquid price data frequently
                hyperliquid_price = self.get_hyperliquid_price()
                if not hyperliquid_price:
                    logger.warning("⚠️ Could not get Hyperliquid price, retrying...")
                    time.sleep(check_interval)
                    continue
                
                # Volume data is already updated via WebSocket callback (_on_price_update)
                # Use cached volume data to avoid duplicate API calls
                if hasattr(self, 'hyperliquid_volume_data') and self.hyperliquid_volume_data:
                    volume_data = self.hyperliquid_volume_data
                    imbalance = volume_data.get("depth_imbalance", 0)
                    total_depth = volume_data.get("total_depth_5", 0)
                    
                    # Log significant market conditions
                    if abs(imbalance) > magic_numbers.ORDERBOOK_IMBALANCE_THRESHOLD:  # > 30% imbalance
                        direction = "DOWNTREND (Heavy Selling)" if imbalance < -magic_numbers.ORDERBOOK_IMBALANCE_THRESHOLD else "UPTREND (Heavy Buying)"
                        logger.warning(f"🚨 SIGNIFICANT ORDERBOOK IMBALANCE: {direction} ({imbalance*100:+.1f}%)")
                        logger.warning(f"   Total Depth: {total_depth:.2f} BTC, Bid: {volume_data.get('bid_depth_5', 0):.2f} BTC, Ask: {volume_data.get('ask_depth_5', 0):.2f} BTC")
                else:
                    # Fallback: get volume data if not available from WebSocket
                    volume_data = self.hyperliquid_api.get_volume_analysis("BTC")
                    self.hyperliquid_volume_data = volume_data
                
                # Check for position exits with advanced management
                self._update_simple_rtm_activity("🔍 Checking position exits", "INFO")
                self.check_position_exits(hyperliquid_price, self.yahoo_analysis)
                
                # Update market data for dashboard (optimized with periodic updates)
                self._update_simple_rtm_activity("📊 Fetching optimized market data", "INFO")
                
                # Get optimized market analysis with periodic updates
                try:
                    yahoo_analysis = self.get_yahoo_analysis(hyperliquid_price=hyperliquid_price)
                    if yahoo_analysis:
                        self.yahoo_analysis = yahoo_analysis
                        self._update_simple_rtm_activity("✅ Optimized market data updated", "SUCCESS")
                        
                        # Log market data for dashboard
                        self.trading_logger.log_analysis({
                            "type": "optimized_analysis_update",
                            "timeframe": "5m",
                            "support_resistance": yahoo_analysis.get("support_resistance_5m", {}),
                            "trend_analysis": yahoo_analysis.get("trend_5m", {}),
                            "market_condition": yahoo_analysis.get("market_condition", "UNKNOWN"),
                            "hyperliquid_price": hyperliquid_price,
                            "yahoo_last_close": yahoo_analysis.get("yahoo_last_close", hyperliquid_price),
                            "price_difference_pct": yahoo_analysis.get("price_difference_pct", 0.0),
                            "price_difference_amount": yahoo_analysis.get("price_difference", 0.0),
                            "data_source": "Yahoo Finance (Optimized) + Hyperliquid (Real-time Price)"
                        })
                        
                        # Update centralized market data
                        self._update_market_data_centralized(hyperliquid_price)
                    else:
                        # No Yahoo analysis available, using fallback
                        self._update_market_data_centralized(hyperliquid_price)
                except Exception as e:
                    # Optimized market data update failed
                    self._update_market_data_centralized(hyperliquid_price)
                
                # Check for signals
                if not self.yahoo_analysis or not self.yahoo_analysis.get("market_condition"):
                    logger.warning("⚠️ Could not get Yahoo analysis, retrying...")
                    time.sleep(check_interval)
                    continue
                
                logger.info(f"🔍 SIGNAL CHECK: Starting signal analysis at ${hyperliquid_price:.2f}")
                
                # Update SimpleRTM with analysis activity
                try:
                    self._update_simple_rtm_activity(f"🔍 Analyzing market conditions at ${hyperliquid_price:.2f}", "INFO")
                except Exception as e:
                    # Could not log activity to SimpleRTM
                    pass
                
                # Enhanced analysis with Yahoo and Hyperliquid data
                enhanced_analysis = self.yahoo_analysis.copy()
                
                # Using simplified analysis with Yahoo + Hyperliquid data only
                
                # Analyze market using enhanced data (Yahoo historical + Hyperliquid real-time)
                self._update_simple_rtm_activity("🧠 Running market analysis", "INFO")
                signal = self.should_trade(hyperliquid_price, enhanced_analysis)
                    
                logger.info(f"🎯 SIGNAL RESULT: {signal.get('should_trade', False)} | Reason: {signal.get('reason', 'Unknown')}")
                
                # Always update dashboard with prediction status, even if no trade signal
                if not signal["should_trade"]:
                    no_signal_prediction = {
                        "type": "ANALYSIS",
                        "side": "HOLD",
                        "confidence": 0,
                        "reason": signal.get("reason", "No clear signal"),
                        "entry_price": hyperliquid_price,
                        "timestamp": time.time(),
                        "market_condition": enhanced_analysis.get("market_condition", "UNKNOWN"),
                        "analysis_active": True
                    }
                    # Update SimpleRTM with no-signal prediction
                    self._update_simple_rtm_signal({
                        "type": "HOLD",
                        "side": "HOLD",
                        "confidence": 0,
                        "reason": signal.get("reason", "No clear signal"),
                        "timestamp": time.time()
                    })
                    
                    # Add analysis activity to SimpleRTM
                    self._update_simple_rtm_activity(f"📊 Analysis complete: {signal.get('reason', 'No clear signal')[:80]}{'...' if len(signal.get('reason', '')) > 80 else ''}", "INFO")
            
                
                if signal["should_trade"]:
                    # Calculate position value from signal data
                    signal_size = signal.get("optimal_params", {}).get("position_size", 0.00035)
                    position_value_usd = signal_size * hyperliquid_price
                    
                    logger.info(f"📊 Signal detected: {signal['reason']}")
                    logger.info(f"   Current Price (Hyperliquid): ${hyperliquid_price:,.2f}")
                    
                    logger.info(f"   Action: {signal['side']}")
                    logger.info(f"   Position Size: {signal_size} BTC (${position_value_usd:,.2f})")
                    
                    # Log quality evaluation
                    quality_eval = signal.get("quality_evaluation", {})
                    if quality_eval:
                        logger.info(f"   Quality: {quality_eval.get('quality_rating', 'UNKNOWN')} ({quality_eval.get('quality_score', 0):.2f})")
                        logger.info(f"   Confidence: {quality_eval.get('confidence_level', 'UNKNOWN')}")
                    
                    # Update SimpleRTM with signal activity
                    self._update_simple_rtm_activity(f"🚀 {signal['side']} signal: {signal['reason'][:50]}{'...' if len(signal['reason']) > 50 else ''}", "SUCCESS")
                    
                    # Place the paper trade
                    self._update_simple_rtm_activity(f"💰 Placing {signal['side']} trade", "INFO")
                    if self.place_paper_trade(signal['side'], signal_data=signal):
                        trades_placed += 1
                        logger.info(f"   Paper Trade {trades_placed}/{max_trades} completed")
                        self._update_simple_rtm_activity(f"✅ Trade {trades_placed}/{max_trades} completed", "SUCCESS")
                        
                        # Log portfolio risk after trade
                        if self.open_positions:
                            portfolio_risk = self.trade_manager.calculate_portfolio_risk(self.open_positions, hyperliquid_price)
                            logger.info(f"📊 Portfolio Risk: {portfolio_risk['risk_level']} (Total Risk: {portfolio_risk['total_risk']*100:.1f}%)")
                            
                            # Enhanced portfolio monitoring
                            if portfolio_risk['risk_level'] == 'HIGH':
                                logger.warning(f"🚨 HIGH PORTFOLIO RISK: {portfolio_risk['total_risk']*100:.1f}% max loss potential")
                                logger.warning(f"   Max Drawdown: ${portfolio_risk['max_drawdown']:.2f}")
                                logger.warning(f"   Correlation Risk: {portfolio_risk['correlation_risk']:.2f}")
                                logger.warning(f"   Concentration Risk: {portfolio_risk['concentration_risk']:.2f}")
                            elif portfolio_risk['risk_level'] == 'MEDIUM':
                                logger.info(f"⚠️ MEDIUM PORTFOLIO RISK: {portfolio_risk['total_risk']*100:.1f}% max loss potential")
                            else:
                                logger.info(f"✅ LOW PORTFOLIO RISK: {portfolio_risk['total_risk']*100:.1f}% max loss potential")
                    else:
                        logger.error("   Hybrid paper trade placement failed")
                        self._update_simple_rtm_activity("❌ Trade placement failed", "ERROR")
                
                else:
                    logger.info(f"⏳ No signal: {signal['reason']}")
                    self._update_simple_rtm_activity(f"⏳ No trading signal: {signal['reason'][:50]}{'...' if len(signal['reason']) > 50 else ''}", "INFO")
                
                # Signal check completed
                
                # Wait before next check
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in Yahoo + Hyperliquid paper trading loop: {e}")
                self.trading_logger.log_error({
                    "type": "yahoo_hyperliquid_paper_trading_loop_error",
                    "message": str(e),
                    "details": {"trades_placed": trades_placed, "max_trades": max_trades}
                })
                time.sleep(check_interval)
        
        # Close any remaining open positions
        hyperliquid_price = self.get_hyperliquid_price()
        if hyperliquid_price:
            for position in self.open_positions[:]:  # Copy list to avoid modification during iteration
                self.close_paper_position(position, "SESSION_END", hyperliquid_price)
        
        logger.info("=" * 50)
        # Advanced monitoring systems removed for simplicity
        
        # End RTM session
        try:
            self._update_simple_rtm_activity("🏁 Trading session completed", "SUCCESS")
            logger.info("📊 RTM session ended")
        except Exception as e:
            logger.error(f"❌ Could not end RTM session: {e}")
            pass
        
        # Performance tracking simplified
        
        logger.success(f"🎯 Yahoo + Hyperliquid Paper Trading session completed!")
        logger.info(f"   Total trades placed: {trades_placed}")
        logger.info(f"   Final Balance: ${self.paper_balance:.2f}")
        logger.info(f"   Total P&L: ${self.paper_balance - self.initial_balance:.2f}")
        logger.info(f"   Return: {((self.paper_balance - self.initial_balance) / self.initial_balance * 100):.2f}%")
        
        # Generate comprehensive trading report
        trading_report = self.trading_logger.generate_trading_report()
        logger.info(f"📊 Yahoo + Hyperliquid Paper Trading Report Generated:")
        logger.info(f"   Session ID: {trading_report['session_info']['session_id']}")
        logger.info(f"   Total Trades: {trading_report['trade_analysis']['total_trades']}")
        logger.info(f"   Win Rate: {trading_report['trade_analysis']['win_rate']}")
        logger.info(f"   Net Profit: {trading_report['trade_analysis']['net_profit']}")
        logger.info(f"   Total Fees: {trading_report['trade_analysis']['total_fees']}")
        
        # Show strategy insights
        insights = self.trading_logger.get_strategy_insights()
        if insights["recommendations"]:
            logger.info(f"💡 Strategy Recommendations:")
            for rec in insights["recommendations"]:
                logger.info(f"   • {rec}")
        
        # Export data to CSV for external analysis
        self.trading_logger.export_to_csv()
    
    def _check_for_ongoing_session(self) -> Optional[Dict]:
        """Check if there's an ongoing session in RTM"""
        try:
            from core.data.real_time_manager import simple_rtm
            rtm_data = simple_rtm.get_data()
            rtm_session = rtm_data.get("session", {})
            
            # Check for any existing session (ACTIVE or COMPLETED) that needs cleanup
            if rtm_session.get("session_id") != "no_session" and rtm_session.get("session_id"):
                return {
                    "session_id": rtm_session.get("session_id"),
                    "status": rtm_session.get("status"),
                    "current_balance": rtm_session.get("current_balance", 0.0),
                    "strategy": rtm_session.get("strategy", "unknown"),
                    "start_time": rtm_session.get("start_time")
                }
            return None
            
        except Exception as e:
            logger.error(f"Error checking for ongoing session: {e}")
            return None

    def _sanitize_volatility(self, volatility_value: float) -> float:
        """Sanitize volatility values to prevent inflation bugs - defensive measure"""
        try:
            if volatility_value is None or volatility_value <= 0:
                return 0.0
            
            # CRITICAL: Cap volatility at realistic Bitcoin levels
            # For a quiet Bitcoin market, 5-minute volatility should be 0.0001-0.01%
            if volatility_value > 0.01:  # > 1% is very high for 5-minute Bitcoin
                logger.error(f"🚨 VOLATILITY INFLATION DETECTED: {volatility_value:.6f} ({volatility_value*100:.4f}%) - capping at realistic level")
                return min(volatility_value, 0.005)  # Cap at 0.5% for active market
            elif volatility_value > 0.005:  # > 0.5% is high for 5-minute Bitcoin
                logger.warning(f"⚠️ High volatility: {volatility_value:.6f} ({volatility_value*100:.4f}%) - monitoring for inflation")
                
            return volatility_value
            
        except Exception as e:
            logger.error(f"Error sanitizing volatility: {e}")
            return 0.0

    def _write_heartbeat(self, is_initial: bool = False):
        """Write heartbeat file - consolidated logic"""
        try:
            current_time = time.time()
            heartbeat_data = {
                "bot_running": True,
                "last_heartbeat": current_time,
                "session_id": getattr(self, 'session_manager', None) and self.session_manager.current_session_id,
                "strategy": self.strategy_name,
                "balance": self.paper_balance
            }
            
            # Ensure temp directory exists
            os.makedirs(os.path.dirname(self.heartbeat_file), exist_ok=True)
            
            with open(self.heartbeat_file, 'w') as f:
                json.dump(heartbeat_data, f, indent=2)
            
            self.last_heartbeat = current_time
            
            if is_initial:
                logger.info("💓 Initial bot heartbeat created")
            else:
                logger.debug("💓 Bot heartbeat updated")
                
        except Exception as e:
            logger.error(f"❌ Could not {'create' if is_initial else 'update'} heartbeat: {e}")

    def _create_initial_heartbeat(self):
        """Create initial heartbeat file immediately when bot starts"""
        self._write_heartbeat(is_initial=True)

    def _update_heartbeat(self):
        """Update bot heartbeat to indicate it's still running"""
        current_time = time.time()
        if current_time - self.last_heartbeat >= self.heartbeat_interval:
            self._write_heartbeat(is_initial=False)
    
    def _cleanup_heartbeat(self):
        """Clean up heartbeat file when bot stops"""
        try:
            if os.path.exists(self.heartbeat_file):
                os.remove(self.heartbeat_file)
                logger.debug("🧹 Bot heartbeat cleaned up")
        except Exception as e:
            logger.error(f"❌ Could not cleanup heartbeat: {e}")

    def close_session(self):
        """Close the current trading session gracefully"""
        try:
            logger.info("🔄 Closing trading session gracefully...")
            
            # Stop WebSocket
            try:
                if hasattr(self, 'websocket') and self.websocket:
                    self.websocket.stop()
                    logger.info("🔌 WebSocket stopped")
            except Exception as e:
                # Could not stop WebSocket
                pass
            
            # Close any remaining open positions
            hyperliquid_price = self.get_hyperliquid_price()
            if hyperliquid_price:
                for position in self.open_positions[:]:  # Copy list to avoid modification during iteration
                    self.close_paper_position(position, "GRACEFUL_SHUTDOWN", hyperliquid_price)
            
            # End session via SessionManager
            try:
                if hasattr(self, 'session_manager') and self.session_manager:
                    self.session_manager.end_session()
                    logger.info("📅 SessionManager session ended")
                else:
                    logger.warning("⚠️ No SessionManager available for session cleanup")
            except Exception as e:
                logger.error(f"❌ Could not end SessionManager session: {e}")
            
            # End RTM session
            try:
                self._update_simple_rtm_activity("🏁 Trading session closed gracefully", "SUCCESS")
                logger.info("📊 RTM session ended")
            except Exception as e:
                logger.debug(f"❌ Could not end RTM session: {e}")
            
            # Update final balance
            if self.trading_logger:
                self.trading_logger.update_current_balance(self.paper_balance)
            
            # Cleanup heartbeat
            self._cleanup_heartbeat()
            
            logger.success(f"✅ Trading session closed gracefully!")
            logger.info(f"   Final Balance: ${self.paper_balance:.2f}")
            logger.info(f"   Total P&L: ${self.paper_balance - self.initial_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Error during graceful session closure: {e}")
    
    def _update_simple_rtm_market(self, market_data: Dict[str, Any]):
        """Update SimpleRTM with market data"""
        try:
            self.rtm_updater.update_simple_rtm_market_data(market_data)
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM market: {e}")
            pass
    
    def _update_simple_rtm_data_status(self, data_status: Dict[str, Any]):
        """Update SimpleRTM data status"""
        try:
            self.rtm_updater.update_simple_rtm_analysis_data(data_status)
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM data status: {e}")
            pass
    
    def _update_simple_rtm_activity(self, message: str, level: str = "INFO"):
        """Update SimpleRTM with activity"""
        try:
            # Actually update SimpleRTM with activity
            from core.data.real_time_manager import simple_rtm
            simple_rtm.add_activity(message, level, "bot")
            logger.info(f"📊 RTM Activity: {message}")
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM activity: {e}")
            pass
    
    def _update_simple_rtm_signal(self, signal_data: Dict[str, Any]):
        """Update SimpleRTM with signal"""
        try:
            self.rtm_updater.update_simple_rtm_prediction_data({"best_prediction": signal_data})
        except Exception as e:
            logger.error(f"❌ Could not update SimpleRTM signal: {e}")
            pass

    def get_weekly_trend_analysis(self) -> Dict[str, Any]:
        """Get weekly trend analysis from Yahoo Finance"""
        try:
            return self.market_data_analyzer.get_weekly_trend_analysis()
        except Exception as e:
            logger.error(f"❌ Failed to get weekly trend analysis: {e}")
            return {"error": str(e)}

    def _calculate_smart_limit_price(self, side: str, current_price: float) -> float:
        """Calculate smart limit price based on side and current price"""
        try:
            # Simple smart limit calculation
            if side == "BUY":
                # Buy slightly below current price for better fill
                return current_price * 0.9995  # 0.05% below (keeping this as it's very specific)
            else:
                # Sell slightly above current price for better fill
                return current_price * 1.0005  # 0.05% above
        except Exception as e:
            logger.error(f"❌ Failed to calculate smart limit price: {e}")
            return current_price

    def _auto_detect_strategy(self, yahoo_analysis: Dict[str, Any], current_price: float) -> str:
        """Auto-detect strategy based on market conditions"""
        try:
            # Simple strategy detection based on volatility
            volatility_5m = yahoo_analysis.get("volatility_5m", 0.0)
            
            if volatility_5m > 0.05:  # High volatility
                return "high_volatility"
            elif volatility_5m < 0.02:  # Low volatility
                return "low_volatility"
            else:
                return "standard"  # Default strategy
        except Exception as e:
            logger.error(f"❌ Failed to auto-detect strategy: {e}")
            return "standard"  # Fallback to standard



    def _update_market_data_centralized(self, current_price: float, force_update: bool = False):
        """Centralized market data update with optimized periodic updates"""
        try:
            
            # Get advanced RSI data (already updated with current price)
            hybrid_rsi_analysis = self.get_optimized_rsi_data()
            
            # Get advanced trend analysis using trend manager
            from core.analysis.trend_manager import trend_manager
            candles_1m = self.market_data_analyzer.get_1m_candles("BTC", 10)
            candles_5m = self.market_data_analyzer.get_5m_candles("BTC", 10)
            candles_1h = self.market_data_analyzer.get_1h_candles("BTC", 10)
            
            if candles_1m and candles_5m and candles_1h:
                trend_data = trend_manager.get_multi_timeframe_trend(candles_1m, candles_5m, candles_1h)
                trend_value = trend_data.get("overall_trend", "UNKNOWN")
                logger.info(f"📊 Trend Analysis: {trend_data.get('overall_trend', 'UNKNOWN')} | Alignment: {trend_data.get('alignment_score', 0)*100:.1f}%")
            else:
                trend_data = {"overall_trend": "UNKNOWN", "alignment_score": 0}
                trend_value = "UNKNOWN"
                logger.warning(f"⚠️ Missing candle data: 1m={len(candles_1m) if candles_1m else 0}, 5m={len(candles_5m) if candles_5m else 0}, 1h={len(candles_1h) if candles_1h else 0}")
            
            rsi_value = hybrid_rsi_analysis.get("rsi", None)
            
            # Get real-time data from Hyperliquid API using centralized manager
            from core.market_data_manager import market_data_manager
            hyperliquid_data = market_data_manager.get_hyperliquid_data(self.hyperliquid_api, "BTC")
            
            # Extract data with cleaner fallback pattern
            volume_data = hyperliquid_data.get("volume_data") or {}
            volatility_data = hyperliquid_data.get("volatility_data") or {}
            ultimate_pressure_data = hyperliquid_data.get("ultimate_pressure_data") or {}
            
            # Prepare market data with simplified extraction
            market_data = {
                "current_price": current_price,
                "trend": trend_value,
                "rsi": rsi_value,
                "volume_depth": volume_data.get("volume_depth", 0.0),
                "volume_category": volume_data.get("volume_category", "UNKNOWN"),
                "order_flow": volume_data.get("order_flow", "NEUTRAL"),
                "depth_analysis": volume_data.get("depth_analysis", "UNKNOWN"),
                "volatility_5m": self._sanitize_volatility(volatility_data.get("volatility_5m", 0.0)),
                "volatility_category": volatility_data.get("volatility_category", "UNKNOWN"),
                "volatility_trend": volatility_data.get("volatility_trend", "UNKNOWN"),
                "spread_volatility": self._sanitize_volatility(volatility_data.get("spread_volatility", 0.0)),
                "ultimate_pressure": {
                    "direction": ultimate_pressure_data.get("direction", "NEUTRAL"),
                    "confidence": ultimate_pressure_data.get("confidence", "50%"),
                    "strength": ultimate_pressure_data.get("strength", magic_numbers.DEFAULT_STRENGTH),
                    "trend": ultimate_pressure_data.get("trend", "NEUTRAL")
                },
                "trend_analysis": trend_data
            }
            
            # Debug log the trend data being sent
            logger.info(f"📊 Sending to SimpleRTM - Overall Trend: {trend_data.get('overall_trend', 'UNKNOWN')} | Alignment: {trend_data.get('alignment_score', 0)*100:.1f}%")
            
            # Update SimpleRTM with centralized data
            self._update_simple_rtm_market(market_data)
            
            # Update data status for monitoring
            try:
                # Pass market_data instead of data_status to get RSI values
                self._update_simple_rtm_data_status(market_data)
            except Exception as e:
                # Failed to update data status
                pass
            
            # Log successful update
            rsi_display = f"{rsi_value:.1f}" if rsi_value is not None else "N/A"
    
            
        except Exception as e:
            logger.error(f"❌ Optimized market update failed: {e}")
    
    def get_data_update_status(self) -> Dict[str, Any]:
        """Get status of all data updates for monitoring"""
        try:
            return self.market_data_analyzer.get_update_status()
        except Exception as e:
            logger.error(f"❌ Failed to get data update status: {e}")
            return {}




def main():
    """Main function to run the Yahoo + Hyperliquid paper trading bot"""
    logger.info("🚀 Yahoo + Hyperliquid Paper Trading Bot Starting...")
    
    # Initialize Yahoo + Hyperliquid paper trading bot with $120 starting balance
    bot = YahooHyperliquidPaperTradingBot(initial_balance=120.0)
    
    # Connect to Hyperliquid
    if not bot.connect():
        logger.error("❌ Failed to connect to Hyperliquid API")
        return
    
    # Run Yahoo + Hyperliquid paper trading
    # Parameters: max_trades, check_interval_seconds
    bot.run_yahoo_hyperliquid_paper_trading(
        max_trades=5,      # Place 5 trades maximum
        check_interval=5  # Check every 5 seconds for ultra-fast reaction
    )

if __name__ == "__main__":
    main()
