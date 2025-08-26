#!/usr/bin/env python3
"""
Yahoo Finance + Hyperliquid Paper Trading Bot
Uses Yahoo Finance for historical market data analysis and Hyperliquid API for real-time trading execution
"""

import time
import json
import random
import statistics
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger
import urllib3

# Disable SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from core.hyperliquid_api import HyperliquidAPI
from data.yahoo_data_fetcher import YahooDataFetcher
from core.config import TradingConfig
from core.constants import constants, strategy_constants, ui_constants, magic_numbers
from core.trade_state_manager import trade_state_manager
from strategies.fee_manager import FeeManager
from strategies.variability_analyzer import VariabilityAnalyzer
from core.trading_logger import TradingLogger
from strategies.prediction_engine import PredictionEngine
from strategies.trade_manager import TradeManager

class YahooHyperliquidPaperTradingBot:
    def __init__(self, initial_balance: float = None, strategy_name: str = None, balance_mode: str = "simulated"):
        self.config = TradingConfig()
        self.strategy_name = strategy_name or constants.DEFAULT_STRATEGY
        self.strategy_config = self.config.STRATEGY_CONFIGS.get(self.strategy_name, strategy_constants.STANDARD_STRATEGY)
        self.hyperliquid_api = None
        self.yahoo_fetcher = YahooDataFetcher()
        self.connected = False
        self.balance_mode = balance_mode  # "real" or "simulated"
        
        # Paper trading state
        self.paper_balance = initial_balance or constants.DEFAULT_INITIAL_BALANCE
        self.initial_balance = self.paper_balance
        self.open_positions = []
        self.closed_positions = []
        self.trade_history = []
        
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
        
        # Initialize account manager
        try:
            from core.account_manager import account_manager
            self.account_manager = account_manager
            logger.success("💰 Account Manager initialized")
        except ImportError as e:
            logger.warning(f"Account manager not available: {e}")
            self.account_manager = None
        
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
        logger.info(f"📊 Hybrid Paper Trading Bot initialized with ${initial_balance_safe:.2f} balance")
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
            from core.hyperliquid_websocket import start_websocket
            
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
            
            # Get volume data from order book analysis
            try:
                volume_data = self.hyperliquid_api.get_volume_analysis("BTC")
                volume_depth = volume_data.get("current_volume", 0.0)
                volume_category = volume_data.get("volume_category", "UNKNOWN")
                order_flow = volume_data.get("order_flow", "NEUTRAL")
                depth_analysis = volume_data.get("depth_analysis", "UNKNOWN")
        
            except Exception as e:
                volume_depth = 0.0
                volume_category = "UNKNOWN"
                order_flow = "NEUTRAL"
                depth_analysis = "UNKNOWN"
            
            # RSI calculation is handled by the main loop every 3 seconds
            # This prevents conflicts and ensures consistent RSI updates
            rsi_value = None  # Will be updated by main loop
            trend_value = "SIDEWAYS"  # Will be updated by main loop
            
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
                test_candles = self.yahoo_fetcher.get_klines("BTC", "5m", 5)
                if test_candles and len(test_candles) > 0:
                    logger.success(f"✅ Yahoo Finance API connected - {len(test_candles)} candles")
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
    
    def _load_existing_positions(self):
        """Load existing open positions from previous sessions"""
        try:
            # Check for open positions file
            positions_file = "data/open_positions.json"
            if os.path.exists(positions_file):
                with open(positions_file, 'r') as f:
                    saved_positions = json.load(f)
                
                # Filter positions that are still open
                current_time = time.time()
                for position in saved_positions:
                    if position.get("status") == "OPEN":
                        # Check if position is still valid (not too old)
                        entry_time = position.get("entry_time", 0)
                        if current_time - entry_time < 86400:  # 24 hours
                            self.open_positions.append(position)
                            logger.info(f"📈 Loaded existing position: {position.get('trade_id')} - {position.get('side')} {position.get('size')} @ ${position.get('entry_price'):,.2f}")
                        else:
                            # Close old positions
                            position["status"] = "CLOSED"
                            position["close_reason"] = "session_timeout"
                            self.closed_positions.append(position)
                            logger.info(f"🔒 Closed old position: {position.get('trade_id')} - session timeout")
                
                logger.info(f"📊 Loaded {len(self.open_positions)} existing open positions")
        except Exception as e:
            logger.warning(f"⚠️ Could not load existing positions: {e}")
    
    def _save_positions(self):
        """Save current positions to file"""
        try:
            all_positions = self.open_positions + self.closed_positions
            with open("data/open_positions.json", 'w') as f:
                json.dump(all_positions, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Could not save positions: {e}")
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get list of open positions for trade manager"""
        return self.open_positions
    
    def connect(self) -> bool:
        """Connect to Hyperliquid API"""
        try:
            logger.info("🔌 Connecting to Hyperliquid...")
            
            # Test Yahoo Finance connection
            if not self.yahoo_fetcher.test_connection():
                logger.error("❌ Failed to connect to Yahoo Finance")
                return False
            
            # Initialize Hyperliquid API for market data only (no account access needed)
            self.hyperliquid_api = HyperliquidAPI()
            
            # Initialize enhanced Hyperliquid simulator
            from core.hyperliquid_simulator import hyperliquid_simulator
            self.hyperliquid_simulator = hyperliquid_simulator
            
            # Test market data connection
            try:
                current_price = self.hyperliquid_api.get_current_price("BTC")
                if current_price:
                    logger.success(f"✅ Successfully connected to Hyperliquid API!")
                    logger.info(f"📊 Current BTC Price: ${current_price:,.2f} USD")
                    logger.info(f"📊 Paper Trading Balance: ${self.paper_balance:.2f} USD")
                else:
                    logger.warning("⚠️ Could not get current price from Hyperliquid API")
            except Exception as e:
                logger.error(f"❌ Hyperliquid API connection failed: {e}")
                return False
            
            # Paper trading mode - no real account access needed
            logger.info("🎮 Paper trading mode - using simulated balance and positions")
            
            # Load account data if available
            if self.account_manager and self.account_manager.account_data:
                account_data = self.account_manager.account_data
                # Update paper balance with account data
                old_balance = self.paper_balance
                self.paper_balance = account_data["current_balance"]
                self.initial_balance = account_data["initial_balance"]
                logger.info(f"📊 Loaded account data: Balance ${old_balance:.2f} → ${self.paper_balance:.2f}, {account_data['total_trades']} total trades")
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
                            logger.info(f"📊 Direct account load: Balance ${old_balance:.2f} → ${self.paper_balance:.2f}, {account_data['total_trades']} total trades")
                except Exception as e:
                    logger.error(f"❌ Failed to load account data directly: {e}")
            
            # Balance and position updates handled by AccountManager (SimpleRTM integration)
            logger.info("🎮 AccountManager handles balance and position updates")
            
            logger.info("📊 No real positions/orders loaded - clean simulated environment")
            logger.info(f"🎮 Using simulated balance: ${self.paper_balance:.2f}")
            
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
    
    def get_optimized_rsi_data(self, hyperliquid_price: float) -> Dict[str, Any]:
        """Get hybrid RSI data for enhanced profitability"""
        hybrid_analysis = self.yahoo_fetcher.get_hybrid_rsi_analysis("BTC", hyperliquid_price)
        return {
            "rsi": hybrid_analysis.get("rsi_value", None),
            "rsi_trend": hybrid_analysis.get("rsi_trend", "NEUTRAL"),
            "rsi_signal": hybrid_analysis.get("advanced_signal", "NEUTRAL"),
            "momentum": hybrid_analysis.get("momentum", "NEUTRAL"),
            "confidence": hybrid_analysis.get("confidence", magic_numbers.DEFAULT_CONFIDENCE)
        }
    def get_yahoo_analysis(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get optimized market analysis from Yahoo Finance with periodic updates"""
        try:
            # Use optimized data manager with periodic updates
            analysis = self.yahoo_fetcher.get_optimized_market_analysis("BTC", hyperliquid_price=hyperliquid_price)
            
            if "error" not in analysis:
                logger.info(f"📊 Yahoo Finance analysis: ${analysis['current_price']:,.2f} - {analysis['market_condition']}")
                return analysis
            else:
                logger.error(f"❌ Yahoo Finance analysis failed: {analysis['error']}")
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
        
        # Get optimized RSI data (with periodic updates)
        hybrid_rsi_analysis = self.yahoo_fetcher.get_hybrid_rsi_analysis("BTC", hyperliquid_price)
        
        # Update variability analyzer
        real_volume = volume_data.get("current_volume", 100)
        self.variability_analyzer.add_price_data(hyperliquid_price, volume=real_volume)
        
        logger.info(f"📊 Hybrid RSI: {hybrid_rsi_analysis.get('rsi_value', 'N/A')} | Signal: {hybrid_rsi_analysis.get('advanced_signal', 'N/A')} | Confidence: {hybrid_rsi_analysis.get('confidence', 0)*100:.1f}%")
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
            "reason": f"HYBRID: {hybrid_rsi_analysis.get('advanced_signal', 'UNKNOWN')} - {entry_analysis['reason']}",
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
            "rsi_value": hybrid_rsi_analysis.get("rsi_value"),
            "momentum": hybrid_rsi_analysis.get("momentum"),
            "advanced_signal": hybrid_rsi_analysis.get("advanced_signal")
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
    

    def _build_price_prediction(self, yahoo_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Build price prediction using PredictionEngine"""
        return self.prediction_engine.build_price_prediction(yahoo_analysis, current_price, self.strategy_name)
    def _analyze_entry_point(self, prediction_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Analyze entry point using PredictionEngine"""
        return self.prediction_engine.analyze_entry_point(prediction_analysis, current_price)
    def _is_prediction_valid(self, prediction: Dict[str, Any], current_price: float) -> bool:
        """Simple prediction validation"""
        return prediction.get("confidence", 0) > magic_numbers.DEFAULT_CONFIDENCE and prediction.get("has_prediction", False)
    def _calculate_prediction_win_probability(self, prediction: Dict[str, Any], prediction_analysis: Dict[str, Any]) -> float:
        """Get win probability from prediction engine"""
        return self.prediction_engine.calculate_win_probability(prediction, prediction_analysis)

    def place_paper_trade(self, side: str, size: float = 0.001, leverage: int = 30, signal_data: Dict = None) -> bool:
        """Place a PREDICTIVE paper trade using predicted entry points and time-based order management"""
        try:
            hyperliquid_price = self.get_hyperliquid_price()
            if not hyperliquid_price:
                return False
            
            # Use optimal parameters from variability analysis if available
            if signal_data and "optimal_params" in signal_data:
                optimal_params = signal_data["optimal_params"]
                size = optimal_params["position_size"]
                leverage = optimal_params["leverage"]
            
            # Ensure leverage doesn't exceed Hyperliquid limit
            leverage = min(leverage, self.leverage_settings["max_leverage"])
            
            # Use PREDICTED entry price from signal data
            if signal_data and "entry_price" in signal_data:
                predicted_entry_price = signal_data["entry_price"]
                entry_timeframe = signal_data.get("entry_timeframe", 20)  # minutes
                prediction_type = signal_data.get("prediction_type", "UNKNOWN")
                prediction_confidence = signal_data.get("prediction_confidence", magic_numbers.DEFAULT_CONFIDENCE)
                
                logger.info(f"🔮 Placing PREDICTIVE {side} LIMIT trade:")
                logger.info(f"   Prediction Type: {prediction_type}")
                logger.info(f"   Predicted Entry: ${predicted_entry_price:,.2f}")
                logger.info(f"   Current Price: ${hyperliquid_price:,.2f}")
                logger.info(f"   Confidence: {prediction_confidence*100:.1f}%")
                logger.info(f"   Expected Timeframe: {entry_timeframe} minutes")
                
                # Use predicted entry price as limit price
                limit_price = predicted_entry_price
            else:
                # Fallback to smart limit price calculation
                limit_price = self._calculate_smart_limit_price(side, hyperliquid_price)
                entry_timeframe = 20
                prediction_type = "SMART_LIMIT"
                prediction_confidence = magic_numbers.DEFAULT_CONFIDENCE
                
                logger.info(f"📝 Placing HYBRID PAPER {side} LIMIT trade:")
                logger.info(f"   Hyperliquid Price: ${hyperliquid_price:,.2f}")
                logger.info(f"   Limit Price: ${limit_price:,.2f}")
            
            # Calculate position value in USD
            position_value_usd = size * limit_price
            
            logger.info(f"   Size: {size} BTC (${position_value_usd:,.2f})")
            logger.info(f"   Leverage: {leverage}x")
            logger.info(f"   Required Margin: ${position_value_usd/leverage:.2f}")
            logger.info(f"   Paper Balance: ${self.paper_balance:.2f}")
            logger.info(f"   Order Type: LIMIT (Lower fees than MARKET!)")
            
            # Update simulator with real order book data
            try:
                orderbook = self.hyperliquid_api.get_orderbook("BTC")
                if orderbook and not orderbook.get('error'):
                    self.hyperliquid_simulator.update_order_book(orderbook)
            
            except Exception as e:
                logger.warning(f"⚠️ Could not update simulator order book: {e}")
            
            # Use enhanced Hyperliquid simulator for realistic order execution
            execution_result = self.hyperliquid_simulator.simulate_order_execution(
                order_type="LIMIT",
                side=side,
                size=size,
                price=limit_price,
                leverage=leverage
            )
            
            if not execution_result.get("success", False):
                error_msg = f"Paper trade failed: {execution_result.get('error', 'Unknown error')}"
                logger.error(f"❌ {error_msg}")
                
                # Log error to JSON file
                self.trading_logger.log_error({
                    "error_type": "trade_execution_failed",
                    "message": error_msg,
                    "trade_id": f"hybrid_trade_{len(self.trade_history) + 1}",
                    "side": side,
                    "size": size,
                    "leverage": leverage,
                    "paper_balance": self.paper_balance,
                    "required_margin": size * hyperliquid_price / leverage
                })
                return False
            
            # Create position record with prediction data and market analysis
            position = {
                "trade_id": f"hybrid_trade_{len(self.trade_history) + 1}",
                "side": side,
                "entry_price": execution_result.get("execution_price", limit_price),
                "limit_price": limit_price,
                "size": size,
                "leverage": leverage,
                "entry_time": time.time(),
                "entry_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "fees": execution_result.get("fees", {"fee_amount": 0, "fee_type": "maker"}),
                "signal_data": signal_data,
                            "target_price": hyperliquid_price * magic_numbers.PROFIT_TARGET_MULTIPLIER if side == "BUY" else hyperliquid_price * magic_numbers.STOP_LOSS_MULTIPLIER,  # 2% target
            "stop_price": hyperliquid_price * magic_numbers.STOP_LOSS_MULTIPLIER if side == "BUY" else hyperliquid_price * magic_numbers.PROFIT_TARGET_MULTIPLIER,  # 2% stop
            "current_stop_loss": hyperliquid_price * magic_numbers.STOP_LOSS_MULTIPLIER if side == "BUY" else hyperliquid_price * magic_numbers.PROFIT_TARGET_MULTIPLIER,
                "status": "OPEN",
                "order_type": "PREDICTIVE_LIMIT",
                "prediction_type": prediction_type,
                "prediction_confidence": prediction_confidence,
                "entry_timeframe": entry_timeframe,
                "time_to_execution": execution_result.get("time_to_execution", 0),
                "order_status": execution_result.get("order_status", "FILLED"),
                "original_market_analysis": self.yahoo_analysis.copy(),  # Store original analysis for comparison
                "quality_evaluation": signal_data.get("quality_evaluation", {}),
                "stop_adjustment_count": 0,
                "partial_closes": [],
                "current_pnl_pct": 0.0,
                # Win-back metadata
                "is_winback_trade": signal_data.get("is_winback_trade", False),
                "winback_data": signal_data.get("winback_data", {}),
                "defensive_mode": signal_data.get("defensive_mode", False),
                "strategy": self.strategy_name
            }
            
            # Add to open positions
            self.open_positions.append(position)
            
            # Update account manager with open positions
            try:
                from core.account_manager import account_manager
                account_manager.update_open_positions(self.open_positions)
                # Updated account manager with open positions
            except Exception as e:
                logger.error(f"❌ Failed to update account manager: {e}")
            
            # Save positions using trade state manager
            trade_state_manager.save_open_positions(self.open_positions)
            
            # Prepare trade data for logging
            trade_data = {
                "timestamp": time.time(),
                "datetime": time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "trade_id": position["trade_id"],
                "side": side,
                "price": execution_result.get("execution_price", limit_price),
                "limit_price": limit_price,
                "size": size,
                "leverage": leverage,
                "order_type": "LIMIT",
                "fees": execution_result.get("fees", {"fee_amount": 0, "fee_type": "maker"}),
                "price_improvement": execution_result.get("slippage", 0),
                "signal_data": signal_data,
                "order_result": {"status": "ok", "paper_trade": True, "hybrid": True, "limit_order": True},
                "hyperliquid_price": hyperliquid_price,
                "support": signal_data.get("support_5m") if signal_data else None,
                "resistance": signal_data.get("resistance_5m") if signal_data else None,
                "trend_5m": signal_data.get("trend_5m") if signal_data else None,
                "trend_1h": signal_data.get("trend_1h") if signal_data else None,
                "variability_score": None,  # Variability analysis is handled separately
                "market_condition": None,  # Market condition is available in enhanced_analysis
                "signal_reason": signal_data.get("reason") if signal_data else None,
                "profit_target": position["target_price"],
                "stop_loss": position["stop_price"],
                "risk_level": "STANDARD",  # Risk level is determined by variability analyzer separately
                "strategy": self.strategy_name
            }
            
            # Log the trade
            self.trading_logger.log_trade(trade_data)
            
            # Add trade to session manager
            if hasattr(self, 'session_manager'):
                self.session_manager.add_session_trade(trade_data)
            
            # Trade and balance updates handled by AccountManager (SimpleRTM integration)
            
            self.trade_history.append(trade_data)
            self.fee_manager.record_trade_fees(trade_data)
            self.last_trade_time = time.time()
            
            if prediction_type != "SMART_LIMIT":
                logger.success(f"✅ PREDICTIVE {side} LIMIT trade placed successfully!")
                logger.info(f"   Prediction Type: {prediction_type}")
                logger.info(f"   Prediction Confidence: {prediction_confidence:.1f}%")
                logger.info(f"   Predicted Entry: ${limit_price:,.2f}")
                logger.info(f"   Actual Execution: ${execution_result.get('execution_price', limit_price):,.2f}")
                logger.info(f"   Entry Timeframe: {entry_timeframe} minutes")
            else:
                logger.success(f"✅ HYBRID PAPER {side} LIMIT trade placed successfully!")
                logger.info(f"   Limit Price: ${limit_price:,.2f}")
                logger.info(f"   Execution Price: ${execution_result.get('execution_price', limit_price):,.2f}")
            
            logger.info(f"   Position Value: ${position_value_usd:,.2f}")
            logger.info(f"   Slippage: {execution_result.get('slippage', 0)*100:.3f}%")
            logger.info(f"   Fees: ${execution_result.get('fees', {}).get('fee_amount', 0):.4f} ({execution_result.get('fees', {}).get('fee_type', 'maker')})")
            logger.info(f"   Remaining Balance: ${self.paper_balance:.2f}")
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Failed to place hybrid paper trade: {e}")
            self.trading_logger.log_error({
                "type": "hybrid_paper_trade_error",
                "message": str(e),
                "details": {
                    "side": side,
                    "size": size,
                    "leverage": leverage,
                    "signal_data": signal_data
                }
            })
            return False
    
    def check_position_exits(self, hyperliquid_price: float, current_analysis: Dict[str, Any] = None):
        """Advanced position management with dynamic stops and intelligent exits"""
        positions_to_close = []
        positions_to_adjust = []
        
        for position in self.open_positions:
            entry_price = position["entry_price"]
            side = position["side"]
            target_price = position["target_price"]
            stop_price = position.get("current_stop_loss", position["stop_price"])
            
            # Update current P&L for position
            if side == "BUY":
                current_pnl_pct = (hyperliquid_price - entry_price) / entry_price
            else:
                current_pnl_pct = (entry_price - hyperliquid_price) / entry_price
            
            position["current_pnl_pct"] = current_pnl_pct
            
            # 1. CHECK FOR TARGET HIT
            if target_price:
                if (side == "BUY" and hyperliquid_price >= target_price) or (side == "SELL" and hyperliquid_price <= target_price):
                    positions_to_close.append((position, "TARGET_HIT", target_price))
                    continue
            
            # 2. CHECK FOR STOP LOSS
            if stop_price:
                if (side == "BUY" and hyperliquid_price <= stop_price) or (side == "SELL" and hyperliquid_price >= stop_price):
                    positions_to_close.append((position, "STOP_LOSS", stop_price))
                    continue
            
            # 3. CHECK FOR PARTIAL CLOSE OPPORTUNITIES
            if current_analysis:
                partial_close_decision = self.trade_manager.should_partial_close(position, hyperliquid_price)
                if partial_close_decision["should_partial_close"]:
                    logger.info(f"💰 Partial close opportunity: {partial_close_decision['reason']}")
                    # Implement partial close logic
                    self._execute_partial_close(position, partial_close_decision, hyperliquid_price)
                    continue  # Skip other checks after partial close
            
            # 4. CHECK FOR SCALING OPPORTUNITIES
            if current_analysis:
                scale_decision = self.trade_manager.should_scale_in_position(position, hyperliquid_price, current_analysis)
                if scale_decision["should_scale"]:
                    logger.info(f"📈 Scaling opportunity: {scale_decision['reason']}")
                    # Implement scaling logic
                    self._execute_scale_in(position, scale_decision, hyperliquid_price)
                    continue  # Skip other checks after scaling
            
            # 5. CHECK FOR EMERGENCY CLOSE
            if current_analysis:
                emergency_decision = self.trade_manager.should_emergency_close(position, hyperliquid_price, current_analysis)
                if emergency_decision["should_emergency_close"]:
                    positions_to_close.append((position, "EMERGENCY_CLOSE", hyperliquid_price))
                    logger.warning(f"🚨 Emergency close: {emergency_decision['reason']}")
                    continue
            
            # 5. CHECK FOR DYNAMIC STOP ADJUSTMENT
            if current_analysis:
                stop_adjustment = self.trade_manager.calculate_dynamic_stops(position, hyperliquid_price, current_analysis)
                if stop_adjustment["should_adjust"]:
                    positions_to_adjust.append((position, stop_adjustment))
                
                # Enhanced market condition tracking
                original_analysis = position.get("original_market_analysis", {})
                if original_analysis:
                    condition_change = self.trade_manager._analyze_condition_change(original_analysis, current_analysis)
                    if condition_change["favorable"]:
                        logger.info(f"📈 Market conditions improved for {position['trade_id']}: {condition_change['reason']}")
                    elif not condition_change["favorable"] and condition_change["confidence"] > magic_numbers.HIGH_CONFIDENCE_THRESHOLD:
                        logger.warning(f"📉 Market conditions deteriorated for {position['trade_id']}: {condition_change['reason']}")
            
            # 6. CHECK POSITION HEAT
            heat_analysis = self.trade_manager.calculate_position_heat(position, hyperliquid_price)
            if heat_analysis["heat_level"] == "CRITICAL":
                logger.warning(f"🔥 CRITICAL position heat: {heat_analysis['heat_pct']*100:.1f}% - {position['trade_id']}")
            elif heat_analysis["heat_level"] == "HIGH":
                logger.info(f"⚠️ HIGH position heat: {heat_analysis['heat_pct']*100:.1f}% - {position['trade_id']}")
            
            # 7. CHECK FOR TIME-BASED EXIT (1 hour max)
            if time.time() - position["entry_time"] > 3600:  # 1 hour
                positions_to_close.append((position, "TIME_EXIT", hyperliquid_price))
                continue
        
        # Apply stop adjustments
        for position, adjustment_result in positions_to_adjust:
            updated_position = self.trade_manager.update_position_with_adjustment(position, adjustment_result)
            # Update position in our list
            position_index = next((i for i, p in enumerate(self.open_positions) if p["trade_id"] == position["trade_id"]), None)
            if position_index is not None:
                self.open_positions[position_index] = updated_position
        
        # Close positions
        for position, exit_reason, exit_price in positions_to_close:
            self.close_paper_position(position, exit_reason, exit_price)
    
    def close_paper_position(self, position: Dict, exit_reason: str, exit_price: float):
        """Close a paper trading position using enhanced Hyperliquid simulator"""
        entry_price = position["entry_price"]
        side = position["side"]
        size = position["size"]
        leverage = position["leverage"]
        
        # Update simulator with real order book data
        try:
            orderbook = self.hyperliquid_api.get_orderbook("BTC")
            if orderbook and not orderbook.get('error'):
                self.hyperliquid_simulator.update_order_book(orderbook)
        
        except Exception as e:
            logger.warning(f"⚠️ Could not update simulator order book: {e}")
        
        # Use enhanced Hyperliquid simulator for realistic exit execution
        exit_side = "SELL" if side == "BUY" else "BUY"  # Opposite of entry
        execution_result = self.hyperliquid_simulator.simulate_order_execution(
            order_type="MARKET",  # Market order for exit
            side=exit_side,
            size=size,
            leverage=leverage
        )
        
        if not execution_result.get("success", False):
            logger.error(f"❌ Position close failed: {execution_result.get('error', 'Unknown error')}")
            return False
        
        # Use execution price from simulator or fallback to provided exit price
        actual_exit_price = execution_result.get("execution_price", exit_price)
        
        # Calculate P&L
        if side == "BUY":
            price_change = (actual_exit_price - entry_price) / entry_price
        else:
            price_change = (entry_price - actual_exit_price) / entry_price
        
        # Apply leverage
        pnl_pct = price_change * leverage
        pnl_amount = size * entry_price * leverage * pnl_pct
        
        # Calculate fees using simulator results
        exit_fees = execution_result.get("fees", {"fee_amount": 0, "fee_type": "taker"})
        exit_fee_amount = exit_fees.get("fee_amount", 0) if isinstance(exit_fees, dict) else exit_fees
        
        # Handle entry fees from position
        entry_fees = position.get("fees", {})
        if isinstance(entry_fees, dict):
            entry_fee_amount = entry_fees.get("fee_amount", 0)
        else:
            entry_fee_amount = entry_fees or 0.0
        
        total_fees = entry_fee_amount + exit_fee_amount
        
        # Net P&L
        net_pnl = pnl_amount - total_fees
        
        # Update balance
        self.paper_balance += net_pnl
        
        # Update account manager if available
        if self.account_manager and self.account_manager.account_data:
            self.account_manager.update_balance(self.paper_balance, net_pnl)
        
        # Update session manager with new balance
        if hasattr(self, 'session_manager'):
            self.session_manager.update_session_balance(self.paper_balance, f"Position closed: {exit_reason}")
        
        # Update current balance in session metadata for dashboard
        self.trading_logger.update_current_balance(self.paper_balance)
        
        # Update position
        position.update({
            "exit_price": actual_exit_price,
            "exit_time": time.time(),
            "exit_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_reason": exit_reason,
            "pnl_pct": pnl_pct,
            "pnl_amount": pnl_amount,
            "total_fees": total_fees,
            "net_pnl": net_pnl,
            "status": "CLOSED",
            "was_profitable": net_pnl > 0,
            "execution_result": execution_result
        })
        
        # Move to closed positions
        self.open_positions.remove(position)
        self.closed_positions.append(position)
        
        # Update trade result in logger
        trade_result = {
            "trade_id": position["trade_id"],
            "side": position["side"],
            "entry_price": position["entry_price"],
            "exit_price": actual_exit_price,
            "size": position["size"],
            "leverage": position["leverage"],
            "confidence": position.get("confidence", 0),
            "profit_loss": pnl_amount,
            "profit_loss_pct": pnl_pct,
            "fees_paid": total_fees,
            "net_profit_loss": net_pnl,
            "pnl": net_pnl,
            "pnl_pct": pnl_pct,
            "entry_time": position["entry_time"],
            "exit_time": position["exit_time"],
            "holding_time": position["exit_time"] - position["entry_time"],
            "exit_reason": exit_reason,
            "was_profitable": net_pnl > 0,
            "balance_after": self.paper_balance,
            "is_winback_trade": position.get("is_winback_trade", False),
            "winback_data": position.get("winback_data", {}),
            "timestamp": time.time(),
            "strategy": position.get("strategy", self.strategy_name),
            "execution_result": execution_result
        }
        
        # Update account manager with open positions
        try:
            from core.account_manager import account_manager
            account_manager.update_open_positions(self.open_positions)
            account_manager.add_trade(trade_result)
            # Updated account manager: position closed
        except Exception as e:
            logger.error(f"❌ Failed to update account manager on position close: {e}")
        
        # Close position using trade state manager
        entry_amount = size * entry_price
        exit_data = {
            "exit_price": actual_exit_price,
            "exit_time": time.time(),
            "exit_reason": exit_reason,
            "pnl": net_pnl,
            "pnl_pct": (net_pnl / entry_amount) * 100 if entry_amount > 0 else 0,
            "fees": exit_fee_amount
        }
        
        # Use trade state manager to close position
        from core.trade_state_manager import trade_state_manager
        trade_state_manager.close_position(position["trade_id"], exit_data)
        
        self.trading_logger.update_trade_result(position["trade_id"], trade_result)
        
        # Trade result logged above
        
        # Trade and balance updates handled by AccountManager (SimpleRTM integration)
        
        # Calculate position value in USD
        position_value_usd = size * entry_price
        
        logger.info(f"📊 Position closed: {position['trade_id']}")
        logger.info(f"   {side} {size} BTC (${position_value_usd:,.2f}) @ ${entry_price:,.2f} → ${actual_exit_price:,.2f}")
        logger.info(f"   P&L: {pnl_pct*100:.2f}% (${pnl_amount:.4f})")
        logger.info(f"   Net P&L: ${net_pnl:.4f} (fees: ${total_fees:.4f})")
        logger.info(f"   Slippage: {execution_result.get('slippage', 0)*100:.3f}%")
        logger.info(f"   Reason: {exit_reason}")
        logger.info(f"   Paper Balance: ${self.paper_balance:.2f}")
    
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
        
        # Start session with SimpleRTM integration
        try:
            from core.session.session_manager import SessionManager
            from core.data.simple_rtm import simple_rtm
            
            # CLEAR PRESENTATION DATA BEFORE STARTING NEW SESSION
            simple_rtm.clear_presentation_data()
            logger.info("🧹 SimpleRTM presentation data cleared - Fresh session data")
            
            # Start session via SessionManager (which updates SimpleRTM)
            self.session_manager = SessionManager()
            session_id = self.session_manager.start_session(
                session_id=f"bot_session_{int(time.time())}",
                strategy=self.strategy_name,
                initial_balance=self.initial_balance
            )
            
            # Session and account data are managed by SessionManager and AccountManager
            # SimpleRTM will read from them automatically
            
            # Add initial activity log to SimpleRTM
            self._update_simple_rtm_activity(f"🚀 Trading bot started - {self.strategy_name} strategy with ${self.initial_balance:.2f} initial balance", "SUCCESS")
            
            logger.success("🔥 SimpleRTM integration active - Dashboard connection established")
            logger.info(f"   📊 Dashboard will receive live predictions and market data")
            
        except Exception as e:
            logger.error(f"❌ Failed to start session with SimpleRTM: {e}")
            logger.warning("⚠️ Dashboard will show offline data only")
        
        # Advanced monitoring systems removed for simplicity
        
        logger.info("=" * 50)
        
        trades_placed = 0
        
        while trades_placed < max_trades:
            try:
                current_time = time.time()
                
                # Test SimpleRTM activity at loop start
                self._update_simple_rtm_activity("🔄 Main trading loop iteration", "INFO")
                
                # Update Hyperliquid price data frequently
                hyperliquid_price = self.get_hyperliquid_price()
                if not hyperliquid_price:
                    logger.warning("⚠️ Could not get Hyperliquid price, retrying...")
                    time.sleep(check_interval)
                    continue
                
                # Get current Hyperliquid volume/liquidity data
                volume_data = self.hyperliquid_api.get_volume_analysis("BTC")
                if volume_data and "depth_imbalance" in volume_data:
                    imbalance = volume_data.get("depth_imbalance", 0)
                    total_depth = volume_data.get("total_depth_5", 0)
                    
                    # Log significant market conditions
                    if abs(imbalance) > magic_numbers.ORDERBOOK_IMBALANCE_THRESHOLD:  # > 30% imbalance
                        direction = "DOWNTREND (Heavy Selling)" if imbalance < -magic_numbers.ORDERBOOK_IMBALANCE_THRESHOLD else "UPTREND (Heavy Buying)"
                        logger.warning(f"🚨 SIGNIFICANT ORDERBOOK IMBALANCE: {direction} ({imbalance*100:+.1f}%)")
                        logger.warning(f"   Total Depth: {total_depth:.2f} BTC, Bid: {volume_data.get('bid_depth_5', 0):.2f} BTC, Ask: {volume_data.get('ask_depth_5', 0):.2f} BTC")
                    
                    # Store for analysis
                    self.hyperliquid_volume_data = volume_data
                else:
                    self.hyperliquid_volume_data = None
                
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
        
        # End SimpleRTM session
        try:
            self._update_simple_rtm_activity("🏁 Trading session completed", "SUCCESS")
            logger.info("📊 SimpleRTM session ended")
        except Exception as e:
            # Could not end SimpleRTM session
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
            
            # Advanced monitoring systems cleanup removed for simplicity
            
            # End SimpleRTM session
            try:
                self._update_simple_rtm_activity("🏁 Trading session closed gracefully", "SUCCESS")
                logger.info("📊 SimpleRTM session ended")
            except Exception as e:
                logger.debug(f"❌ Could not end SimpleRTM session: {e}")
            
            # Update final balance
            if self.trading_logger:
                self.trading_logger.update_current_balance(self.paper_balance)
            
            logger.success(f"✅ Trading session closed gracefully!")
            logger.info(f"   Final Balance: ${self.paper_balance:.2f}")
            logger.info(f"   Total P&L: ${self.paper_balance - self.initial_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Error during graceful session closure: {e}")
    
    def _update_simple_rtm_market(self, market_data: Dict[str, Any]):
        """Update SimpleRTM with market data"""
        try:
            from core.data.simple_rtm import simple_rtm
            simple_rtm.update_market(market_data)
            current_price = market_data.get('current_price', 0) or 0
            # SimpleRTM market updated
        except Exception as e:
            # Could not update SimpleRTM market
            pass
    
    def _update_simple_rtm_data_status(self, data_status: Dict[str, Any]):
        """Update SimpleRTM data status"""
        try:
            from core.data.simple_rtm import simple_rtm
            simple_rtm.update_data_status(data_status)
        except Exception as e:
            # Could not update SimpleRTM data status
            pass
    
    def _update_simple_rtm_activity(self, message: str, level: str = "INFO"):
        """Update SimpleRTM with activity"""
        try:
            from core.data.simple_rtm import simple_rtm
            simple_rtm.add_activity(message, level, "bot")
            # SimpleRTM activity added
        except Exception as e:
            # Could not update SimpleRTM activity
            pass
    
    def _update_simple_rtm_signal(self, signal_data: Dict[str, Any]):
        """Update SimpleRTM with signal"""
        try:
            from core.data.simple_rtm import simple_rtm
            simple_rtm.add_signal(signal_data)
            # SimpleRTM signal added
        except Exception as e:
            # Could not update SimpleRTM signal
            pass

    def get_weekly_trend_analysis(self) -> Dict[str, Any]:
        """Get weekly trend analysis from Yahoo Finance"""
        try:
            # Get weekly data from Yahoo Finance
            weekly_data = self.yahoo_fetcher.get_klines("BTC", "1d", 7)
            if not weekly_data or len(weekly_data) < 2:
                return {"error": "Insufficient weekly data"}
            
            # Calculate weekly trend
            first_price = weekly_data[0].get("close", 0)
            last_price = weekly_data[-1].get("close", 0)
            weekly_change = ((last_price - first_price) / first_price) * 100 if first_price > 0 else 0
            
            # Determine trend direction
            if weekly_change > 2:
                trend = "UPTREND"
            elif weekly_change < -2:
                trend = "DOWNTREND"
            else:
                trend = "SIDEWAYS"
            
            return {
                "weekly_trend": trend,
                "weekly_change_pct": weekly_change,
                "first_price": first_price,
                "last_price": last_price,
                "data_points": len(weekly_data)
            }
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

    def _execute_partial_close(self, position: Dict, partial_close_decision: Dict, current_price: float):
        """Execute partial close of position"""
        try:
            # Simple partial close implementation
            close_percentage = partial_close_decision.get("close_percentage", magic_numbers.PARTIAL_CLOSE_MULTIPLIER)
            close_size = position["size"] * close_percentage
            
            logger.info(f"💰 Partial close: {close_percentage*100:.1f}% of position {position['trade_id']}")
            logger.info(f"   Close size: {close_size} BTC")
            logger.info(f"   Reason: {partial_close_decision.get('reason', 'Unknown')}")
            
            # Update position size
            position["size"] -= close_size
            position["partial_closes"].append({
                "size": close_size,
                "price": current_price,
                "timestamp": time.time(),
                "reason": partial_close_decision.get("reason", "Unknown")
            })
            
            # Log partial close
            self._update_simple_rtm_activity(f"💰 Partial close: {close_percentage*100:.1f}% of {position['trade_id']}", "INFO")
            
        except Exception as e:
            logger.error(f"❌ Failed to execute partial close: {e}")

    def _execute_scale_in(self, position: Dict, scale_decision: Dict, current_price: float):
        """Execute scale-in to position"""
        try:
            # Simple scale-in implementation
            scale_size = scale_decision.get("scale_size", position["size"] * magic_numbers.SCALE_SIZE_MULTIPLIER)
            scale_price = current_price
            
            logger.info(f"📈 Scale-in: {scale_size} BTC to position {position['trade_id']}")
            logger.info(f"   Scale price: ${scale_price:,.2f}")
            logger.info(f"   Reason: {scale_decision.get('reason', 'Unknown')}")
            
            # Update position (simple average price calculation)
            total_size = position["size"] + scale_size
            total_value = (position["size"] * position["entry_price"]) + (scale_size * scale_price)
            new_entry_price = total_value / total_size if total_size > 0 else position["entry_price"]
            
            position["size"] = total_size
            position["entry_price"] = new_entry_price
            
            # Log scale-in
            self._update_simple_rtm_activity(f"📈 Scale-in: {scale_size} BTC to {position['trade_id']}", "INFO")
            
        except Exception as e:
            logger.error(f"❌ Failed to execute scale-in: {e}")

    def _update_market_data_centralized(self, current_price: float, force_update: bool = False):
        """Centralized market data update with optimized periodic updates"""
        try:
            
            # Get advanced data from Yahoo Finance (with periodic updates)
            hybrid_rsi_analysis = self.yahoo_fetcher.get_hybrid_rsi_analysis("BTC", current_price)
            
            # Get advanced trend analysis using trend manager
            from core.trend_manager import trend_manager
            candles_1m = self.yahoo_fetcher.get_1m_klines("BTC", 10)
            candles_5m = self.yahoo_fetcher.get_5m_klines("BTC", 10)
            candles_1h = self.yahoo_fetcher.get_1h_klines("BTC", 10)
            
            if candles_1m and candles_5m and candles_1h:
                trend_data = trend_manager.get_multi_timeframe_trend(candles_1m, candles_5m, candles_1h)
                trend_value = trend_data.get("overall_trend", "UNKNOWN")
                logger.info(f"📊 Trend Analysis: {trend_data.get('overall_trend', 'UNKNOWN')} | Alignment: {trend_data.get('alignment_score', 0)*100:.1f}%")
            else:
                trend_data = {"overall_trend": "UNKNOWN", "alignment_score": 0}
                trend_value = "UNKNOWN"
                logger.warning(f"⚠️ Missing candle data: 1m={len(candles_1m) if candles_1m else 0}, 5m={len(candles_5m) if candles_5m else 0}, 1h={len(candles_1h) if candles_1h else 0}")
            
            rsi_value = hybrid_rsi_analysis.get("rsi_value", None)
            
            # Get real-time data from Hyperliquid API using centralized manager
            from core.market_data_manager import market_data_manager
            hyperliquid_data = market_data_manager.get_hyperliquid_data(self.hyperliquid_api, "BTC")
            
            volume_data = hyperliquid_data.get("volume_data", {})
            volatility_data = hyperliquid_data.get("volatility_data", {})
            ultimate_pressure_data = hyperliquid_data.get("ultimate_pressure_data", {})
            
            # Prepare market data with proper fallbacks
            market_data = {
                "current_price": current_price,
                "trend": trend_value,
                "rsi": rsi_value,
                "volume_depth": volume_data.get("volume_depth", 0.0) if volume_data else 0.0,
                "volume_category": volume_data.get("volume_category", "UNKNOWN") if volume_data else "UNKNOWN",
                "order_flow": volume_data.get("order_flow", "NEUTRAL") if volume_data else "NEUTRAL",
                "depth_analysis": volume_data.get("depth_analysis", "UNKNOWN") if volume_data else "UNKNOWN",
                "volatility_5m": volatility_data.get("volatility_5m", 0.0) if volatility_data else 0.0,
                "volatility_category": volatility_data.get("volatility_category", "UNKNOWN") if volatility_data else "UNKNOWN",
                "volatility_trend": volatility_data.get("volatility_trend", "UNKNOWN") if volatility_data else "UNKNOWN",
                "spread_volatility": volatility_data.get("spread_volatility", 0.0) if volatility_data else 0.0,
                "ultimate_pressure": {
                    "direction": ultimate_pressure_data.get("direction", "NEUTRAL") if ultimate_pressure_data else "NEUTRAL",
                    "confidence": ultimate_pressure_data.get("confidence", "50%") if ultimate_pressure_data else "50%",
                    "strength": ultimate_pressure_data.get("strength", magic_numbers.DEFAULT_STRENGTH) if ultimate_pressure_data else magic_numbers.DEFAULT_STRENGTH,
                    "trend": ultimate_pressure_data.get("trend", "NEUTRAL") if ultimate_pressure_data else "NEUTRAL"
                },
                "trend_analysis": trend_data
            }
            
            # Debug log the trend data being sent
            logger.info(f"📊 Sending to SimpleRTM - Overall Trend: {trend_data.get('overall_trend', 'UNKNOWN')} | Alignment: {trend_data.get('alignment_score', 0)*100:.1f}%")
            
            # Update SimpleRTM with centralized data
            self._update_simple_rtm_market(market_data)
            
            # Update data status for monitoring
            try:
                data_status = self.get_data_update_status()
                self._update_simple_rtm_data_status(data_status)
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
            return self.yahoo_fetcher.get_update_status()
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
