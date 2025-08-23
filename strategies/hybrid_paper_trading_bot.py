#!/usr/bin/env python3
"""
Yahoo Finance + Hyperliquid Paper Trading Bot
Uses Yahoo Finance for historical market data analysis and Hyperliquid API for real-time trading execution
"""

import time
import json
import random
import statistics
from typing import Dict, Any, Optional, List
from loguru import logger
import sys
import os
import urllib3

# Disable SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hyperliquid_api import HyperliquidAPI
from data.yahoo_data_fetcher import YahooDataFetcher
from core.config import TradingConfig
from strategies.fee_manager import FeeManager
from strategies.variability_analyzer import VariabilityAnalyzer
from core.trading_logger import TradingLogger
from strategies.whale_integration import WhaleIntegration, integrate_whale_analytics_into_signal
from strategies.prediction_engine import PredictionEngine
from strategies.trade_manager import TradeManager

class YahooHyperliquidPaperTradingBot:
    def __init__(self, initial_balance: float = 120.0, strategy_name: str = "standard"):
        self.config = TradingConfig()
        self.strategy_name = strategy_name
        self.strategy_config = self.config.STRATEGY_CONFIGS.get(strategy_name, self.config.STRATEGY_CONFIGS["standard"])
        self.hyperliquid_api = None
        self.yahoo_fetcher = YahooDataFetcher()
        self.connected = False
        
        # Initialize advanced system attributes (will be set to proper instances or None)
        self.smart_data_cache = None
        self.trading_data_manager = None
        self.dynamic_stop_manager = None
        self.global_volume_aggregator = None
        self.blockchain_analyzer = None
        self.win_back_engine = None
        self.loss_pattern_analyzer = None
        
        # Paper trading state
        self.paper_balance = initial_balance
        self.initial_balance = initial_balance
        self.open_positions = []
        self.closed_positions = []
        self.trade_history = []
        
        # Load existing open positions from previous sessions
        self._load_existing_positions()
        
        # Market data storage
        self.binance_analysis = {}
        self.weekly_trend_analysis = {}
        self.hyperliquid_price = 0
        self.last_trade_time = 0
        self.min_interval = 300  # 5 minutes in seconds
        
        # Signal deduplication
        self.last_signal_reason = ""
        self.last_signal_price = 0
        self.last_signal_time = 0
        self.signal_cooldown = 300  # 5 minutes between similar signals
        
        # Price difference monitoring
        self.price_difference_threshold = 0.002  # 0.2% threshold for price difference alerts
        self.last_price_difference_alert = 0
        self.price_difference_alert_cooldown = 300  # 5 minutes between alerts
        
        # Analysis components
        self.fee_manager = FeeManager()
        self.variability_analyzer = VariabilityAnalyzer(lookback_periods=100)
        self.trading_logger = TradingLogger("trading_logs")
        
        # Clean up old sessions - keep only last 3 sessions
        self.trading_logger.cleanup_old_sessions(keep_sessions=3)
        
        # Whale analytics integration
        self.whale_integration = WhaleIntegration(enabled=self.config.WHALE_ANALYTICS_ENABLED)
        
        # Prediction engine
        self.prediction_engine = PredictionEngine(self.strategy_config)
        
        # Advanced trade manager
        self.trade_manager = TradeManager(self.strategy_config)
        
        # Initialize advanced trading systems
        try:
            from strategies.dynamic_stop_manager import DynamicStopManager, GlobalVolumeAggregator, BlockchainDataAnalyzer
            from strategies.win_back_engine import WinBackEngine, LossPatternAnalyzer
            from core.realtime_data_manager import trading_data_manager
            from core.smart_data_cache import SmartDataCache
            
            self.dynamic_stop_manager = DynamicStopManager(self.strategy_config)
            self.global_volume_aggregator = GlobalVolumeAggregator()
            self.blockchain_analyzer = BlockchainDataAnalyzer()
            self.win_back_engine = WinBackEngine(self.strategy_config)
            self.loss_pattern_analyzer = LossPatternAnalyzer()
            
            # Professional data management
            self.trading_data_manager = trading_data_manager
            # Note: SmartDataCache will be initialized AFTER API connection test
            
            # INITIALIZE ULTIMATE INTELLIGENCE SYSTEMS
            try:
                from strategies.ml_prediction_engine import MLPredictionEngine
                from strategies.bitcoin_pattern_engine import BitcoinPatternEngine
                from strategies.master_fusion_engine import MasterFusionEngine
                
                self.ml_engine = MLPredictionEngine(self.strategy_config)
                self.btc_pattern_engine = BitcoinPatternEngine(self.strategy_config)
                self.master_fusion_engine = MasterFusionEngine(self.strategy_config)
                
                # Connect all engines to the master fusion engine
                self.master_fusion_engine.initialize_engines({
                    "ml_engine": self.ml_engine,
                    "btc_pattern_engine": self.btc_pattern_engine,
                    "prediction_engine": self.prediction_engine,
                    "variability_analyzer": self.variability_analyzer,
                    "trade_manager": self.trade_manager,
                    "whale_integration": self.whale_integration
                })
                
                logger.success("🧠 ULTIMATE INTELLIGENCE SYSTEMS ACTIVATED:")
                logger.success("   🤖 ML Prediction Engine - Advanced machine learning models")
                logger.success("   🏗️ Bitcoin Pattern Engine - BTC-specific pattern recognition")
                logger.success("   🧠 Master Fusion Engine - Ultimate trading intelligence")
                logger.info(f"   DEBUG: Fusion Engine initialized: {self.master_fusion_engine is not None}")
                
            except ImportError as e:
                logger.warning(f"Ultimate intelligence systems not available: {e}")
                self.ml_engine = None
                self.btc_pattern_engine = None
                self.master_fusion_engine = None
                
            # Initialize Real-Time P&L Tracker
            try:
                from strategies.realtime_pnl_tracker import RealTimePnLTracker
                self.pnl_tracker = RealTimePnLTracker(initial_balance=self.paper_balance)
                logger.success("💰 Real-Time P&L Tracker activated")
            except ImportError as e:
                logger.warning(f"Real-Time P&L Tracker not available: {e}")
                self.pnl_tracker = None
                
            # Initialize Active Position Manager
            try:
                from strategies.active_position_manager import ActivePositionManager
                self.active_position_manager = ActivePositionManager()
                # Inject dependencies
                self.active_position_manager.inject_dependencies(
                    pnl_tracker=self.pnl_tracker,
                    hyperliquid_api=self.hyperliquid_api,
                    prediction_engines={"master_fusion": self.master_fusion_engine}
                )
                self.active_position_manager.start_monitoring()
                logger.success("🤖 Active Position Manager activated - Intelligent trade monitoring active")
            except ImportError as e:
                logger.warning(f"Active Position Manager not available: {e}")
                self.active_position_manager = None
            
            logger.success("🔥 All advanced systems initialized: Dynamic stops + Global volume + Blockchain + Win-back + Real-time data + ULTIMATE INTELLIGENCE")
        except ImportError as e:
            logger.warning(f"Advanced systems not available: {e}")
            self.dynamic_stop_manager = None
            self.global_volume_aggregator = None
            self.blockchain_analyzer = None
            self.win_back_engine = None
            self.loss_pattern_analyzer = None
            self.trading_data_manager = None
            self.smart_data_cache = None  # Ensure attribute exists
            self.ml_engine = None
            self.btc_pattern_engine = None
            self.master_fusion_engine = None
            self.pnl_tracker = None
            self.active_position_manager = None
        
        # TEST API CONNECTIONS AND COMPLETE INITIALIZATION
        self._test_api_connections()
        
        # Override trade manager's get_open_positions method
        self.trade_manager.get_open_positions = self.get_open_positions
        
        # Enhanced analysis frequency - Optimized for rolling candle updates
        self.price_update_interval = 2  # Update price every 2 seconds for ultra-fast reaction
        self.market_analysis_interval = 10  # Market analysis every 10 seconds
        self.signal_check_interval = 5  # Check for signals every 5 seconds for faster reaction
        self.candle_update_interval = 5   # Update 5m candles every 5 seconds for ultra-frequent analysis
        self.hourly_analysis_interval = 3600  # Update 1h candles every hour
        
        # RSI update optimization - Update more frequently for better accuracy
        self.rsi_update_interval = 5  # Update RSI every 5 seconds for ultra-frequent accuracy
        self.last_rsi_update = 0
        self.cached_rsi_data = None
        self.cached_rsi_timestamp = 0
        
        # Enhanced candle management - COMPLETE multi-timeframe configuration
        self.candles_1m_buffer = []   # Rolling buffer of 120 most recent 1m candles (2h)
        self.candles_5m_buffer = []   # Rolling buffer of 60 most recent 5m candles (5h) 
        self.candles_1h_buffer = []   # Rolling buffer of 84 most recent 1h candles (3.5d)
        self.candles_1d_buffer = []   # Rolling buffer of 45 most recent 1d candles (6w)
        self.last_candle_1m_time = 0
        self.last_candle_5m_time = 0
        self.last_candle_1h_time = 0
        self.last_candle_1d_time = 0
        self.initial_analysis_complete = False
        self.market_structure = {}  # Store analyzed market structure
        
        # Multi-timeframe analysis configuration
        self.OPTIMAL_CANDLE_COUNTS = {
            "1m": 120,  # 2 hours - immediate momentum
            "5m": 60,   # 5 hours - core prediction analysis
            "1h": 84,   # 3.5 days - daily trend context
            "1d": 45    # 6 weeks - weekly/monthly trend context
        }
        
        self.last_price_update = 0
        self.last_market_analysis = 0
        self.last_signal_check = 0
        self.last_candle_update = 0
        self.last_hourly_analysis = 0
        self.last_market_update = 0
        
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
        
        logger.info(f"📊 Hybrid Paper Trading Bot initialized with ${initial_balance:.2f} balance")
        if self.whale_integration.is_available():
            logger.info("🐋 Whale analytics integration enabled")
        else:
            logger.info("🐋 Whale analytics integration disabled")
    
    def _test_api_connections(self):
        """Test API connections and set connected status"""
        try:
            logger.info("🔗 Testing API connections...")
            
            # Initialize Hyperliquid API
            self.hyperliquid_api = HyperliquidAPI()
            
            # Test Hyperliquid connection
            current_price = self.hyperliquid_api.get_current_price("BTC")
            if current_price and current_price > 0:
                logger.success(f"✅ Hyperliquid API connected - BTC: ${current_price:,.2f}")
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
                
                # Initialize SmartDataCache now that APIs are connected
                if hasattr(self, 'smart_data_cache'):  # Only if advanced systems are available
                    try:
                        from core.smart_data_cache import SmartDataCache
                        self.smart_data_cache = SmartDataCache(self.yahoo_fetcher, self.hyperliquid_api)
                        logger.success("✅ SmartDataCache initialized with connected APIs")
                    except Exception as e:
                        logger.error(f"SmartDataCache initialization failed: {e}")
                        self.smart_data_cache = None
                else:
                    logger.info("🔧 Advanced systems disabled - SmartDataCache not available")
                
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
            positions_file = "open_positions.json"
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
            with open("open_positions.json", 'w') as f:
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
            
            # Test Hyperliquid connection
            if not self.config.WALLET_ADDRESS or not self.config.WALLET_PRIVATE_KEY:
                logger.error("❌ Wallet credentials not found")
                return False
            
            self.hyperliquid_api = HyperliquidAPI(self.config.WALLET_ADDRESS, self.config.WALLET_PRIVATE_KEY)
            account_info = self.hyperliquid_api.get_account_info()
            logger.success(f"✅ Successfully connected to Hyperliquid API!")
            
            if 'data' in account_info and 'marginSummary' in account_info['data']:
                margin = account_info['data']['marginSummary']
                account_value = margin.get('accountValue', 0)
                logger.info(f"💰 Real Account Value: ${account_value:.2f} USD")
                logger.info(f"📊 Paper Trading Balance: ${self.paper_balance:.2f} USD")
            
            # 🚀 FETCH REAL POSITIONS AND ORDERS FOR REALISTIC SIMULATION
            logger.info("🔍 Fetching real account state for simulation base...")
            
            # Get real open positions
            real_positions = self.hyperliquid_api.get_open_positions()
            if self.trading_data_manager:
                self.trading_data_manager.update_real_positions(real_positions)
            
            # Get real open orders
            real_orders = self.hyperliquid_api.get_open_orders()
            if self.trading_data_manager:
                self.trading_data_manager.update_real_orders(real_orders)
            
            # Log summary
            if real_positions:
                logger.success(f"📊 Found {len(real_positions)} real positions - will factor into simulation")
                total_real_pnl = sum(pos.get('unrealized_pnl', 0) for pos in real_positions)
                logger.info(f"💹 Total real position PnL: ${total_real_pnl:.2f}")
            else:
                logger.info("📊 No real positions found - clean slate for simulation")
            
            if real_orders:
                logger.success(f"📋 Found {len(real_orders)} real orders - will track alongside simulation")
            else:
                logger.info("📋 No real orders found")
            
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
    
    def get_weekly_trend_analysis(self) -> Dict[str, Any]:
        """Get weekly trend analysis for overall market context"""
        try:
            logger.info("📅 Analyzing weekly trend for overall market context...")
            
            # Get 1-week candlestick data (7 days * 24 hours = 168 candles)
            weekly_candles = self.yahoo_fetcher.get_1h_klines("BTC", 168)
            
            if not weekly_candles or len(weekly_candles) < 24:
                logger.error("❌ Insufficient weekly data for trend analysis")
                return {"error": "Insufficient weekly data"}
            
            # Calculate weekly trend
            week_start_price = weekly_candles[0]["close"]
            week_end_price = weekly_candles[-1]["close"]
            weekly_change = (week_end_price - week_start_price) / week_start_price
            
            # Calculate weekly volatility
            weekly_returns = []
            for i in range(1, len(weekly_candles)):
                prev_close = weekly_candles[i-1]["close"]
                curr_close = weekly_candles[i]["close"]
                ret = (curr_close - prev_close) / prev_close
                weekly_returns.append(ret)
            
            weekly_volatility = statistics.stdev(weekly_returns) if len(weekly_returns) > 1 else 0
            
            # Find weekly high and low
            weekly_high = max([candle["high"] for candle in weekly_candles])
            weekly_low = min([candle["low"] for candle in weekly_candles])
            weekly_range = weekly_high - weekly_low
            
            # Determine weekly trend strength
            if weekly_change > 0.05:  # 5% weekly gain
                weekly_trend = "STRONG_BULL"
                trend_strength = "VERY_STRONG"
            elif weekly_change > 0.02:  # 2% weekly gain
                weekly_trend = "BULL"
                trend_strength = "STRONG"
            elif weekly_change > 0.005:  # 0.5% weekly gain
                weekly_trend = "WEAK_BULL"
                trend_strength = "WEAK"
            elif weekly_change < -0.05:  # 5% weekly loss
                weekly_trend = "STRONG_BEAR"
                trend_strength = "VERY_STRONG"
            elif weekly_change < -0.02:  # 2% weekly loss
                weekly_trend = "BEAR"
                trend_strength = "STRONG"
            elif weekly_change < -0.005:  # 0.5% weekly loss
                weekly_trend = "WEAK_BEAR"
                trend_strength = "WEAK"
            else:
                weekly_trend = "SIDEWAYS"
                trend_strength = "NEUTRAL"
            
            # Calculate momentum indicators
            recent_candles = weekly_candles[-24:]  # Last 24 hours
            recent_change = (recent_candles[-1]["close"] - recent_candles[0]["close"]) / recent_candles[0]["close"]
            
            # Determine if recent momentum aligns with weekly trend
            momentum_alignment = "ALIGNED"
            if (weekly_trend in ["BULL", "STRONG_BULL", "WEAK_BULL"] and recent_change < -0.01) or \
               (weekly_trend in ["BEAR", "STRONG_BEAR", "WEAK_BEAR"] and recent_change > 0.01):
                momentum_alignment = "DIVERGING"
            
            weekly_analysis = {
                "weekly_trend": weekly_trend,
                "trend_strength": trend_strength,
                "weekly_change_pct": weekly_change * 100,
                "weekly_volatility": weekly_volatility,
                "weekly_high": weekly_high,
                "weekly_low": weekly_low,
                "weekly_range": weekly_range,
                "week_start_price": week_start_price,
                "week_end_price": week_end_price,
                "recent_24h_change": recent_change * 100,
                "momentum_alignment": momentum_alignment,
                "candles_analyzed": len(weekly_candles),
                "analysis_timestamp": time.time()
            }
            
            logger.success(f"✅ Weekly trend analysis completed:")
            logger.info(f"   Weekly Trend: {weekly_trend} ({weekly_change*100:.2f}%)")
            logger.info(f"   Trend Strength: {trend_strength}")
            logger.info(f"   Weekly Range: ${weekly_low:,.2f} - ${weekly_high:,.2f}")
            logger.info(f"   Recent 24h: {recent_change*100:.2f}% ({momentum_alignment})")
            
            return weekly_analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get weekly trend analysis: {e}")
            return {"error": str(e)}
    
    def get_optimized_rsi_data(self, hyperliquid_price: float) -> Dict[str, Any]:
        """Get optimized RSI data with smart caching and frequent updates"""
        current_time = time.time()
        
        # Check if we need to update RSI (every 30 seconds)
        if (current_time - self.last_rsi_update >= self.rsi_update_interval or 
            self.cached_rsi_data is None):
            
            try:
                logger.debug("🔄 Updating RSI data (30-second interval)")
                
                # Get fresh Yahoo data for RSI calculation
                candles_5m = self.yahoo_fetcher.get_klines("BTC", "5m", 30)
                
                if candles_5m and len(candles_5m) >= 25:
                    # Calculate RSI using our optimized method
                    rsi_result = self.hyperliquid_api.calculate_rsi_from_yahoo_data(candles_5m, periods=20)
                    
                    # Cache the result with timestamp
                    self.cached_rsi_data = rsi_result
                    self.cached_rsi_timestamp = current_time
                    self.last_rsi_update = current_time
                    
                    logger.debug(f"📊 RSI updated: {rsi_result.get('rsi', 50):.1f} (20-period)")
                    
                else:
                    logger.warning("⚠️ Insufficient candle data for RSI calculation")
                    # Use cached data if available, otherwise return default
                    if self.cached_rsi_data:
                        logger.info(f"📊 Using cached RSI: {self.cached_rsi_data.get('rsi', 50):.1f}")
                    else:
                        self.cached_rsi_data = {"rsi": 50.0, "calculation_method": "default"}
                        
            except Exception as e:
                logger.error(f"❌ Error updating RSI data: {e}")
                # Use cached data if available, otherwise return default
                if self.cached_rsi_data:
                    logger.info(f"📊 Using cached RSI due to error: {self.cached_rsi_data.get('rsi', 50):.1f}")
                else:
                    self.cached_rsi_data = {"rsi": 50.0, "calculation_method": "error_fallback"}
        
        return self.cached_rsi_data or {"rsi": 50.0, "calculation_method": "fallback"}
    
    def _build_5m_prices_from_hyperliquid_trades(self, trade_history: List[Dict[str, Any]]) -> List[float]:
        """Build 5-minute price samples from Hyperliquid trade history"""
        try:
            if not trade_history:
                return []
            
            import time
            
            # Group trades by 5-minute intervals
            current_time = time.time() * 1000  # Convert to milliseconds for comparison
            price_samples = []
            
            # Create buckets for the last 6 hours (14 periods, expanded for low trade frequency)
            available_trades_timespan = 6 * 60  # 6 hours in minutes
            bucket_size_minutes = available_trades_timespan // 14  # ~25 minutes per period
            
            for i in range(14):
                bucket_end = current_time - (i * bucket_size_minutes * 60 * 1000)  # Convert to ms
                bucket_start = bucket_end - (bucket_size_minutes * 60 * 1000)
                
                # Find trades in this 5-minute window
                bucket_trades = []
                for trade in trade_history:
                    try:
                        # Hyperliquid timestamps are in milliseconds
                        trade_time = float(trade.get('time', trade.get('timestamp', 0)))
                        if bucket_start <= trade_time <= bucket_end:
                            bucket_trades.append(float(trade.get('px', trade.get('price', 0))))
                    except (ValueError, TypeError):
                        continue
                
                # Use average price of trades in this bucket (approximates 5m close)
                if bucket_trades:
                    avg_price = sum(bucket_trades) / len(bucket_trades)
                    price_samples.append(avg_price)
                elif price_samples:  # Use last known price if no trades in bucket
                    price_samples.append(price_samples[-1])
            
            # Reverse to get chronological order (oldest first)
            price_samples.reverse()
            logger.debug(f"🔧 Built {len(price_samples)} price samples from {len(trade_history)} trades")
            return price_samples
            
        except Exception as e:
            logger.error(f"❌ Error building Hyperliquid price samples: {e}")
            return []
    
    def _calculate_rsi_from_price_samples(self, price_samples: List[float], periods: int = 14) -> float:
        """Calculate RSI from price samples (standard RSI formula)"""
        try:
            if len(price_samples) < periods + 1:
                return 50.0
                
            # Calculate price changes
            gains = []
            losses = []
            
            for i in range(1, len(price_samples)):
                change = price_samples[i] - price_samples[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(-change)
            
            if len(gains) < periods:
                return 50.0
                
            # Calculate RSI using standard formula
            avg_gain = sum(gains[-periods:]) / periods
            avg_loss = sum(losses[-periods:]) / periods
            
            if avg_loss == 0:
                return 100.0  # All gains, no losses
                
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            logger.debug(f"🎯 RSI calculation: {periods}-period, {len(price_samples)} samples, RSI={rsi:.1f}")
            return max(0.0, min(100.0, rsi))  # Clamp to 0-100
            
        except Exception as e:
            logger.error(f"❌ RSI calculation error: {e}")
            return 50.0
    
    def get_yahoo_analysis(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get comprehensive market analysis from Yahoo Finance (HISTORICAL DATA ONLY)"""
        try:
            # Pass Hyperliquid price to Yahoo analysis for current price context
            analysis = self.yahoo_fetcher.get_market_analysis("BTC", hyperliquid_price=hyperliquid_price)
            
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
            mid_price = self.hyperliquid_api.get_current_price("BTC")
            
            if mid_price:
                # Update variability analyzer with new price data
                current_time = time.time()
                if current_time - self.last_price_update >= self.price_update_interval:
                    # Get real volume data from Hyperliquid 5m candles
                    volume_data = self.hyperliquid_api.get_current_5m_volume("BTC")
                    real_volume = volume_data.get("current_volume", 100)  # Fallback to 100 if no data
                    
                    self.variability_analyzer.add_price_data(mid_price, volume=real_volume)
                    self.last_price_update = current_time
                
                return mid_price
            
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid price: {e}")
            return None
    
    def should_trade(self, hyperliquid_price: float, binance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """ULTIMATE INTELLIGENT TRADING: Master Fusion Engine analyzes ALL available intelligence"""
        if not binance_analysis or "error" in binance_analysis:
            return {"should_trade": False, "reason": "No market analysis available"}
        
        # 1. DETECT STRATEGY AND MARKET CONDITIONS
        current_strategy = self._auto_detect_strategy(binance_analysis, hyperliquid_price)
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
        # Get real-time Hyperliquid data
        hyperliquid_indicators = self.hyperliquid_api.get_current_market_indicators("BTC")
        volume_data = self.hyperliquid_api.get_current_5m_volume("BTC")
        
        # Calculate enhanced RSI
        candles_5m = binance_analysis.get("candles_5m", [])
        proper_rsi = self.hyperliquid_api.calculate_rsi_from_yahoo_data(candles_5m, periods=21)
        
        # Update variability analyzer
        real_volume = volume_data.get("current_volume", 100)
        self.variability_analyzer.add_price_data(hyperliquid_price, volume=real_volume)
        
        logger.info(f"📊 Enhanced RSI: {proper_rsi.get('rsi', 50):.1f} (21-period for crypto accuracy)")
        logger.info(f"📊 Volume: {volume_data.get('current_volume', 0):.1f} BTC ({volume_data.get('volume_category', 'UNKNOWN')})")
        
        # 4. BUILD COMPREHENSIVE ENHANCED ANALYSIS
        enhanced_analysis = binance_analysis.copy()
        enhanced_analysis["hyperliquid_volume"] = hyperliquid_indicators
        enhanced_analysis["hyperliquid_rsi"] = proper_rsi
        enhanced_analysis["hyperliquid_5m_volume"] = volume_data
        enhanced_analysis["timestamp"] = current_time
        
        # Add Ultimate Pressure Indicator
        try:
            ultimate_pressure = self.hyperliquid_api.get_ultimate_pressure("BTC")
            enhanced_analysis["ultimate_pressure"] = ultimate_pressure
        except Exception as e:
            logger.debug(f"Ultimate pressure error: {e}")
        
        # Add Whale Analytics (if available)
        if self.whale_integration:
            try:
                whale_analysis = self.whale_integration.analyze_whale_impact(enhanced_analysis, hyperliquid_price)
                enhanced_analysis["whale_analysis"] = whale_analysis
            except Exception as e:
                logger.debug(f"Whale analytics error: {e}")
        
        # Add Global Volume (if available)
        if self.global_volume_aggregator:
            try:
                global_volume = self.global_volume_aggregator.get_realtime_global_volume()
                enhanced_analysis["global_volume"] = global_volume
            except Exception as e:
                logger.debug(f"Global volume error: {e}")
        
        # Add Blockchain Data (if available)
        if self.blockchain_analyzer:
            try:
                blockchain_data = self.blockchain_analyzer.get_latest_sentiment()
                enhanced_analysis["blockchain_data"] = blockchain_data
            except Exception as e:
                logger.debug(f"Blockchain data error: {e}")
        
        # Get traditional prediction for fallback
        prediction_analysis = self.prediction_engine.build_price_prediction(enhanced_analysis, hyperliquid_price, self.strategy_name)
        enhanced_analysis["prediction_analysis"] = prediction_analysis
        logger.info(f"🔮 PREDICTION ENGINE: Generated analysis with keys: {list(prediction_analysis.keys()) if prediction_analysis else 'None'}")
        
        # 5. 🧠 MASTER FUSION ENGINE - ULTIMATE INTELLIGENCE ANALYSIS
        if self.master_fusion_engine:
            logger.info("🧠 Activating Master Fusion Engine for ultimate trading intelligence...")
            
            try:
                # Generate ultimate signal using ALL available intelligence
                fusion_signal = self.master_fusion_engine.generate_ultimate_signal(
                    binance_analysis, hyperliquid_price, enhanced_analysis
                )
                
                logger.info(f"🔬 FUSION ENGINE RESULT: Signal={fusion_signal is not None}")
                if fusion_signal:
                    logger.info(f"   Signal: {fusion_signal.signal} | Confidence: {fusion_signal.confidence:.1%}")
                
                if fusion_signal:
                    # Convert fusion signal to bot format
                    signal_data = {
                        "should_trade": True,
                        "side": fusion_signal.signal,
                        "reason": fusion_signal.reason,
                        "target": fusion_signal.target_price,
                        "stop": fusion_signal.stop_loss,
                        "entry_price": fusion_signal.entry_price,
                        "entry_timeframe": fusion_signal.timeframe,
                        "prediction_confidence": fusion_signal.confidence,
                        "position_size_pct": fusion_signal.position_size,
                        "fusion_score": fusion_signal.fusion_score,
                        "supporting_factors": fusion_signal.supporting_factors,
                        "risk_score": fusion_signal.risk_score,
                        "profit_potential": fusion_signal.profit_potential,
                        "optimal_params": {
                            "position_size": self.paper_balance * fusion_signal.position_size / hyperliquid_price,
                            "leverage": min(self.strategy_config["max_leverage"], 30)
                        },
                        "fusion_analysis": True,
                        "binance_analysis": binance_analysis,
                        "enhanced_analysis": enhanced_analysis,
                        "hyperliquid_price": hyperliquid_price,
                        "strategy_name": self.strategy_name
                    }
                    
                    # Apply win-back enhancements if active
                    if self.win_back_engine:
                        winback_requirements = self.win_back_engine.get_winback_signal_requirements()
                        if winback_requirements.get("active", False):
                            logger.info(f"🎯 Win-back active - enhancing fusion signal...")
                            # Enhance position size for win-back
                            current_position = signal_data["position_size_pct"]
                            enhanced_position = min(0.6, current_position * 1.3)  # 30% boost, max 60%
                            signal_data["position_size_pct"] = enhanced_position
                            signal_data["optimal_params"]["position_size"] = self.paper_balance * enhanced_position / hyperliquid_price
                            signal_data["winback_enhanced"] = True
                    
                    # Record in real-time data manager
                    if self.trading_data_manager:
                        fusion_prediction = {
                            "type": "FUSION",
                            "side": fusion_signal.signal,
                            "confidence": fusion_signal.confidence,
                            "fusion_score": fusion_signal.fusion_score
                        }
                        self.trading_data_manager.add_trading_signal(fusion_prediction)
                        self.trading_data_manager.update_predictions([fusion_prediction])
                        
                        # Add fusion prediction activity
                        self.trading_data_manager.add_activity({
                            "timestamp": time.time(),
                            "message": f"🧠 Fusion prediction: {fusion_signal.signal} signal with {fusion_signal.confidence*100:.1f}% confidence",
                            "type": "fusion_prediction",
                            "level": "INFO"
                        })
                    
                    # Log fusion analysis
                    self.trading_logger.log_analysis({
                        "type": "fusion_analysis",
                        "timestamp": current_time,
                        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "fusion_signal": fusion_signal.signal,
                        "fusion_confidence": fusion_signal.confidence,
                        "fusion_score": fusion_signal.fusion_score,
                        "supporting_factors": fusion_signal.supporting_factors,
                        "position_size": fusion_signal.position_size,
                        "hyperliquid_price": hyperliquid_price,
                        "strategy_name": self.strategy_name
                    })
                    
                    # Log the fusion signal
                    self.trading_logger.log_signal(signal_data)
                    
                    # Update signal memory
                    self.last_signal_reason = signal_data["reason"]
                    self.last_signal_price = hyperliquid_price
                    self.last_signal_time = current_time
                    
                    logger.success(f"🚀 FUSION SIGNAL GENERATED: {fusion_signal.signal} - {fusion_signal.confidence:.1%} confidence")
                    return signal_data
                    
                else:
                    logger.info("🤔 Master Fusion Engine: No clear trading opportunity")
            
            except Exception as e:
                logger.error(f"Master Fusion Engine error: {e}")
                logger.info("⚠️ Falling back to traditional prediction system")
        else:
            logger.info("⚠️ Master Fusion Engine not available - using traditional prediction system")
        
        # 6. FALLBACK TO TRADITIONAL SYSTEM (if fusion not available or no signal)
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
            "reason": f"TRADITIONAL: {entry_analysis['prediction_type']} - {entry_analysis['reason']}",
            "target": entry_analysis["target_price"],
            "stop": entry_analysis["stop_price"],
            "entry_price": entry_analysis["entry_price"],
            "prediction_confidence": entry_analysis["confidence"],
            "optimal_params": variability_decision["optimal_trading_params"],
            "strategy_name": self.strategy_name
        }
        
        # Traditional quality check
        trade_decision = self.trade_manager.should_place_trade(
            signal_data, binance_analysis, hyperliquid_price, self.open_positions
        )
        
        if not trade_decision["should_place"]:
            return {
                "should_trade": False,
                "reason": f"Trade quality check failed: {trade_decision['reason']}"
            }
        
        # Log traditional signal
        self.trading_logger.log_signal(signal_data)
        
        # Update real-time data manager with traditional prediction
        if self.trading_data_manager:
            traditional_prediction = {
                "type": "TRADITIONAL",
                "side": signal_data["side"],
                "confidence": signal_data.get("prediction_confidence", 0),
                "reason": signal_data["reason"],
                "entry_price": signal_data.get("entry_price", hyperliquid_price),
                "target": signal_data.get("target", hyperliquid_price),
                "timestamp": time.time()
            }
            self.trading_data_manager.add_trading_signal(traditional_prediction)
            self.trading_data_manager.update_predictions([traditional_prediction])
            logger.info(f"📊 TRADITIONAL PREDICTION sent to dashboard: {signal_data['side']} - {signal_data.get('prediction_confidence', 0)*100:.1f}% confidence")
            
            # Also add prediction activity
            self.trading_data_manager.add_activity({
                "timestamp": time.time(),
                "message": f"🔮 Traditional prediction: {signal_data['side']} signal with {signal_data.get('prediction_confidence', 0)*100:.1f}% confidence",
                "type": "prediction",
                "level": "INFO"
            })
        
        self.last_signal_reason = signal_data["reason"]
        self.last_signal_price = hyperliquid_price
        self.last_signal_time = current_time
        
        return signal_data
    
    def _apply_weekly_trend_context(self, current_price: float, support: float, resistance: float) -> Dict[str, Any]:
        """Apply weekly trend context to trading decisions"""
        if not self.weekly_trend_analysis or "error" in self.weekly_trend_analysis:
            return {"should_proceed": True, "reason": "No weekly analysis available"}
        
        weekly_trend = self.weekly_trend_analysis.get("weekly_trend", "UNKNOWN")
        trend_strength = self.weekly_trend_analysis.get("trend_strength", "NEUTRAL")
        weekly_high = self.weekly_trend_analysis.get("weekly_high", 0)
        weekly_low = self.weekly_trend_analysis.get("weekly_low", 0)
        momentum_alignment = self.weekly_trend_analysis.get("momentum_alignment", "UNKNOWN")
        
        # Strong weekly trends should influence trading direction
        if trend_strength in ["VERY_STRONG", "STRONG"]:
            if weekly_trend in ["STRONG_BULL", "BULL"]:
                # In strong bull market, prefer long trades and avoid shorting near weekly high
                if current_price > weekly_high * 0.995:  # Near weekly high
                    return {
                        "should_proceed": False,
                        "reason": "Strong bull market - avoiding shorts near weekly high"
                    }
                # Prefer long trades in bull market
                return {
                    "should_proceed": True,
                    "reason": "Strong bull market - favoring long positions",
                    "preferred_direction": "BUY"
                }
            
            elif weekly_trend in ["STRONG_BEAR", "BEAR"]:
                # In strong bear market, prefer short trades and avoid longing near weekly low
                if current_price < weekly_low * 1.005:  # Near weekly low
                    return {
                        "should_proceed": False,
                        "reason": "Strong bear market - avoiding longs near weekly low"
                    }
                # Prefer short trades in bear market
                return {
                    "should_proceed": True,
                    "reason": "Strong bear market - favoring short positions",
                    "preferred_direction": "SELL"
                }
        
        # Check for momentum divergence
        if momentum_alignment == "DIVERGING":
            if weekly_trend in ["BULL", "STRONG_BULL"] and current_price < support * 0.998:
                return {
                    "should_proceed": False,
                    "reason": "Bull market momentum diverging - avoiding shorts"
                }
            elif weekly_trend in ["BEAR", "STRONG_BEAR"] and current_price > resistance * 1.002:
                return {
                    "should_proceed": False,
                    "reason": "Bear market momentum diverging - avoiding longs"
                }
        
        # Weekly range considerations
        weekly_range = weekly_high - weekly_low
        current_position_in_range = (current_price - weekly_low) / weekly_range if weekly_range > 0 else 0.5
        
        # Avoid trades at extreme ends of weekly range unless strong signals
        if current_position_in_range > 0.95:  # Near weekly high
            return {
                "should_proceed": True,
                "reason": "Near weekly high - cautious trading",
                "risk_level": "HIGH"
            }
        elif current_position_in_range < 0.05:  # Near weekly low
            return {
                "should_proceed": True,
                "reason": "Near weekly low - cautious trading",
                "risk_level": "HIGH"
            }
        
        return {
            "should_proceed": True,
            "reason": "Weekly trend context allows trading",
            "risk_level": "NORMAL"
        }
    
    def _auto_detect_strategy(self, binance_analysis: Dict[str, Any], current_price: float) -> str:
        """Auto-detect market volatility and return appropriate strategy"""
        try:
            # Get market condition from Binance analysis
            market_condition = binance_analysis.get("market_condition", "UNKNOWN")
            
            # Get volatility indicators
            candles_5m = binance_analysis.get("candles_5m", [])
            candles_1h = binance_analysis.get("candles_1h", [])
            
            if len(candles_5m) < 10 or len(candles_1h) < 10:
                return self.strategy_name  # Keep current strategy if insufficient data
            
            # Calculate 5-minute volatility
            prices_5m = [candle["close"] for candle in candles_5m[-20:]]  # Last 20 candles
            returns_5m = []
            for i in range(1, len(prices_5m)):
                ret = abs((prices_5m[i] - prices_5m[i-1]) / prices_5m[i-1])
                returns_5m.append(ret)
            
            volatility_5m = statistics.mean(returns_5m) if returns_5m else 0
            
            # Calculate 1-hour volatility
            prices_1h = [candle["close"] for candle in candles_1h[-24:]]  # Last 24 candles
            returns_1h = []
            for i in range(1, len(prices_1h)):
                ret = abs((prices_1h[i] - prices_1h[i-1]) / prices_1h[i-1])
                returns_1h.append(ret)
            
            volatility_1h = statistics.mean(returns_1h) if returns_1h else 0
            
            # Get range size
            support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
            range_size = support_resistance_5m.get("range", 0)
            range_percentage = (range_size / current_price) if current_price > 0 else 0
            
            # Enhanced strategy selection logic with crypto-appropriate thresholds
            if market_condition == "LOW_VOLATILITY" or volatility_5m < 0.0015 or range_percentage < 0.002:
                # Low volatility conditions (tightened thresholds)
                logger.info(f"📊 Low volatility detected: 5m={volatility_5m*100:.3f}%, 1h={volatility_1h*100:.3f}%, range={range_percentage*100:.2f}%")
                return "low_volatility"
            
            elif market_condition in ["HIGH_VOLATILITY", "ELEVATED_VOLATILITY"] or volatility_5m > 0.003 or volatility_1h > 0.006 or range_percentage > 0.008:
                # High volatility conditions (much more sensitive)
                logger.info(f"📊 High volatility detected: 5m={volatility_5m*100:.3f}%, 1h={volatility_1h*100:.3f}%, range={range_percentage*100:.2f}%, condition={market_condition}")
                return "high_volatility"
            
            else:
                # Medium volatility conditions
                logger.info(f"📊 Medium volatility detected: 5m={volatility_5m*100:.3f}%, 1h={volatility_1h*100:.3f}%, range={range_percentage*100:.2f}%")
                return "standard"
                
        except Exception as e:
            logger.error(f"❌ Error in auto-strategy detection: {e}")
            return self.strategy_name  # Keep current strategy on error
    
    def _get_volatility_5m(self, binance_analysis: Dict[str, Any]) -> float:
        """Extract 5-minute volatility from analysis with enhanced recent sensitivity"""
        try:
            # Use the enhanced volatility from Yahoo analysis if available
            if "volatility_5m" in binance_analysis:
                return binance_analysis["volatility_5m"]
            
            # Fallback to manual calculation with enhanced sensitivity
            candles_5m = binance_analysis.get("candles_5m", [])
            if len(candles_5m) < 10:
                return 0.0
            
            # Use shorter lookback for more responsive volatility
            lookback_periods = min(15, len(candles_5m))
            prices_5m = [candle["close"] for candle in candles_5m[-lookback_periods:]]
            returns_5m = []
            
            for i in range(1, len(prices_5m)):
                ret = abs((prices_5m[i] - prices_5m[i-1]) / prices_5m[i-1])
                returns_5m.append(ret)
            
            if not returns_5m:
                return 0.0
            
            # Enhanced calculation with recent bias
            baseline_vol = statistics.mean(returns_5m)
            recent_vol = statistics.mean(returns_5m[-5:]) if len(returns_5m) >= 5 else baseline_vol
            
            # Boost if recent volatility is higher (catch volatility spikes)
            if recent_vol > baseline_vol * 1.3:
                enhanced_vol = baseline_vol * 0.6 + recent_vol * 0.4
                logger.info(f"📈 Enhanced volatility: baseline={baseline_vol*100:.3f}%, recent={recent_vol*100:.3f}%, final={enhanced_vol*100:.3f}%")
            else:
                enhanced_vol = baseline_vol * 0.8 + recent_vol * 0.2
            
            return enhanced_vol
            
        except Exception as e:
            logger.error(f"Error calculating enhanced 5m volatility: {e}")
            return 0.0
    
    def _get_volatility_1h(self, binance_analysis: Dict[str, Any]) -> float:
        """Extract 1-hour volatility from analysis with enhanced recent sensitivity"""
        try:
            # Use the enhanced volatility from Yahoo analysis if available
            if "volatility_1h" in binance_analysis:
                return binance_analysis["volatility_1h"]
            
            # Fallback to manual calculation with enhanced sensitivity
            candles_1h = binance_analysis.get("candles_1h", [])
            if len(candles_1h) < 10:
                return 0.0
            
            # Use shorter lookback for more responsive volatility
            lookback_periods = min(18, len(candles_1h))
            prices_1h = [candle["close"] for candle in candles_1h[-lookback_periods:]]
            returns_1h = []
            
            for i in range(1, len(prices_1h)):
                ret = abs((prices_1h[i] - prices_1h[i-1]) / prices_1h[i-1])
                returns_1h.append(ret)
            
            if not returns_1h:
                return 0.0
            
            # Enhanced calculation with recent bias 
            baseline_vol = statistics.mean(returns_1h)
            recent_vol = statistics.mean(returns_1h[-4:]) if len(returns_1h) >= 4 else baseline_vol
            
            # Weight recent volatility for spike detection
            if recent_vol > baseline_vol * 1.3:
                enhanced_vol = baseline_vol * 0.6 + recent_vol * 0.4
            else:
                enhanced_vol = baseline_vol * 0.8 + recent_vol * 0.2
            
            return enhanced_vol
            
        except Exception as e:
            logger.error(f"Error calculating enhanced 1h volatility: {e}")
            return 0.0
    
    def _get_range_percentage(self, binance_analysis: Dict[str, Any], current_price: float) -> float:
        """Extract range percentage from analysis"""
        try:
            support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
            range_size = support_resistance_5m.get("range", 0)
            return (range_size / current_price) if current_price > 0 else 0.0
        except:
            return 0.0
    
    def _calculate_dynamic_position_size(self, variability_analysis: Dict[str, Any], binance_analysis: Dict[str, Any], 
                                       current_price: float, support: float, resistance: float) -> float:
        """Calculate dynamic position size based on risk assessment and win probability"""
        
        # Base position size from strategy config
        base_position_size = self.strategy_config["position_size"]
        
        # 1. VARIABILITY SCORE FACTOR (0.5x - 2.0x)
        variability_score = variability_analysis.get("current_variability_score", 0.5)
        if variability_score > 0.8:
            variability_multiplier = 2.0  # High variability = optimal conditions
        elif variability_score > 0.6:
            variability_multiplier = 1.5  # Good variability
        elif variability_score > 0.4:
            variability_multiplier = 1.0  # Standard variability
        else:
            variability_multiplier = 0.5  # Low variability = poor conditions
        
        # 2. MARKET CONDITION FACTOR (0.7x - 1.3x)
        market_condition = binance_analysis.get("market_condition", "UNKNOWN")
        if market_condition == "LOW_VOLATILITY_CHOPPY":
            market_multiplier = 0.7  # Reduce size in choppy markets
        elif market_condition in ["MEDIUM_VOLATILITY_OPTIMAL", "HIGH_VOLATILITY_OPTIMAL"]:
            market_multiplier = 1.3  # Increase size in optimal conditions
        elif market_condition in ["EXTREME_VOLATILITY_RISKY", "EXTREME_VOLATILITY_AVOID"]:
            market_multiplier = 0.5  # Significantly reduce in extreme volatility
        else:
            market_multiplier = 1.0  # Standard conditions
        
        # 3. TREND ALIGNMENT FACTOR (0.8x - 1.4x)
        trend_5m = binance_analysis.get("trend_5m", {}).get("trend", "UNKNOWN")
        trend_1h = binance_analysis.get("trend_1h", {}).get("trend", "UNKNOWN")
        trend_strength_1h = binance_analysis.get("trend_1h", {}).get("strength", 0)
        
        # Check if trends align with our signal direction
        trend_alignment = 1.0
        if trend_1h == "UP" and trend_5m == "UP":
            trend_alignment = 1.4  # Strong bullish alignment
        elif trend_1h == "DOWN" and trend_5m == "DOWN":
            trend_alignment = 1.4  # Strong bearish alignment
        elif trend_1h == "UP" or trend_5m == "UP":
            trend_alignment = 1.2  # Partial bullish alignment
        elif trend_1h == "DOWN" or trend_5m == "DOWN":
            trend_alignment = 1.2  # Partial bearish alignment
        elif trend_strength_1h < 0.3:
            trend_alignment = 0.8  # Weak trends
        
        # 4. SUPPORT/RESISTANCE PROXIMITY FACTOR (0.6x - 1.2x)
        range_size = resistance - support
        if range_size > 0:
            # Calculate how close we are to support/resistance
            distance_to_support = abs(current_price - support) / range_size
            distance_to_resistance = abs(current_price - resistance) / range_size
            
            # If very close to support/resistance, reduce position size
            if distance_to_support < 0.1 or distance_to_resistance < 0.1:
                proximity_multiplier = 0.6  # Too close to key levels
            elif distance_to_support < 0.2 or distance_to_resistance < 0.2:
                proximity_multiplier = 0.8  # Close to key levels
            else:
                proximity_multiplier = 1.2  # Good distance from key levels
        else:
            proximity_multiplier = 1.0
        
        # 5. WEEKLY TREND CONTEXT FACTOR (0.7x - 1.3x)
        weekly_context = self._apply_weekly_trend_context(current_price, support, resistance)
        if weekly_context.get("risk_level") == "HIGH":
            weekly_multiplier = 0.7  # High risk weekly context
        elif weekly_context.get("preferred_direction") in ["BUY", "SELL"]:
            weekly_multiplier = 1.3  # Weekly trend supports our direction
        else:
            weekly_multiplier = 1.0  # Neutral weekly context
        
        # 6. VOLATILITY STRATEGY FACTOR (0.8x - 1.5x)
        if self.strategy_name == "low_volatility":
            strategy_multiplier = 1.5  # Low volatility = safer, can use larger positions
        elif self.strategy_name == "high_volatility":
            strategy_multiplier = 0.8  # High volatility = riskier, use smaller positions
        else:
            strategy_multiplier = 1.0  # Standard volatility
        
        # 7. WIN PROBABILITY FACTOR (0.5x - 2.0x)
        win_probability = self._calculate_win_probability(
            variability_analysis, binance_analysis, current_price, support, resistance
        )
        
        if win_probability > 0.8:
            probability_multiplier = 2.0  # Very high win probability
        elif win_probability > 0.7:
            probability_multiplier = 1.5  # High win probability
        elif win_probability > 0.6:
            probability_multiplier = 1.2  # Good win probability
        elif win_probability > 0.5:
            probability_multiplier = 1.0  # Average win probability
        else:
            probability_multiplier = 0.5  # Low win probability
        
        # Calculate final position size
        final_position_size = base_position_size * \
                             variability_multiplier * \
                             market_multiplier * \
                             trend_alignment * \
                             proximity_multiplier * \
                             weekly_multiplier * \
                             strategy_multiplier * \
                             probability_multiplier
        
        # Apply limits
        min_position_size = 0.05   # Minimum 5% of balance
        max_position_size = 0.80   # Maximum 80% of balance (as requested)
        
        final_position_size = max(min_position_size, min(max_position_size, final_position_size))
        
        # Log the position sizing calculation
        logger.info(f"🎯 Dynamic Position Sizing:")
        logger.info(f"   Base Size: {base_position_size*100:.1f}%")
        logger.info(f"   Variability: {variability_multiplier:.1f}x (score: {variability_score:.3f})")
        logger.info(f"   Market: {market_multiplier:.1f}x ({market_condition})")
        logger.info(f"   Trend: {trend_alignment:.1f}x (5m: {trend_5m}, 1h: {trend_1h})")
        logger.info(f"   Proximity: {proximity_multiplier:.1f}x")
        logger.info(f"   Weekly: {weekly_multiplier:.1f}x")
        logger.info(f"   Strategy: {strategy_multiplier:.1f}x ({self.strategy_name})")
        logger.info(f"   Win Probability: {probability_multiplier:.1f}x ({win_probability*100:.1f}%)")
        logger.info(f"   Final Size: {final_position_size*100:.1f}% (${self.paper_balance * final_position_size:.2f})")
        
        return final_position_size
    
    def _build_price_prediction(self, binance_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Build price prediction and identify potential entry points"""
        try:
            # Extract data from Binance analysis
            candles_5m = binance_analysis.get("candles_5m", [])
            candles_1h = binance_analysis.get("candles_1h", [])
            trend_5m = binance_analysis.get("trend_5m", {})
            trend_1h = binance_analysis.get("trend_1h", {})
            support_resistance_5m = binance_analysis.get("support_resistance_5m", {})
            
            if len(candles_5m) < 10 or len(candles_1h) < 10:
                return {"has_prediction": False, "reason": "Insufficient candlestick data"}
            
            support_5m = support_resistance_5m.get("support", 0)
            resistance_5m = support_resistance_5m.get("resistance", 0)
            range_size_5m = support_resistance_5m.get("range", 0)
            
            # Minimum range requirement
            min_range_percentage = self.strategy_config["min_range_percentage"]
            if range_size_5m < current_price * min_range_percentage:
                return {"has_prediction": False, "reason": f"Range too small (need {min_range_percentage*100:.1f}%, have {range_size_5m/current_price*100:.1f}%)"}
            
            # Calculate volatility for prediction confidence
            volatility_5m = self._get_volatility_5m(binance_analysis)
            volatility_1h = self._get_volatility_1h(binance_analysis)
            
            # Build predictions based on market conditions
            predictions = []
            
            # 1. BREAKOUT PREDICTIONS
            if current_price > resistance_5m * 0.998:  # Near resistance
                # Predict potential breakout above resistance
                breakout_prediction = {
                    "type": "BREAKOUT_ABOVE",
                    "entry_price": resistance_5m * 1.0005,  # Slightly above resistance
                    "side": "BUY",
                    "confidence": self._calculate_breakout_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                    "reason": f"Potential breakout above ${resistance_5m:,.2f}",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(breakout_prediction)
            
            elif current_price < support_5m * 1.002:  # Near support
                # Predict potential breakout below support
                breakout_prediction = {
                    "type": "BREAKOUT_BELOW",
                    "entry_price": support_5m * 0.9995,  # Slightly below support
                    "side": "SELL",
                    "confidence": self._calculate_breakout_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_breakout_timeframe(volatility_5m, range_size_5m),
                    "reason": f"Potential breakout below ${support_5m:,.2f}",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(breakout_prediction)
            
            # 2. REVERSION PREDICTIONS
            if current_price > resistance_5m * 0.999:  # Very near resistance
                # Predict potential reversion from resistance
                reversion_prediction = {
                    "type": "REVERSION_FROM_RESISTANCE",
                    "entry_price": resistance_5m * 0.9995,  # Slightly below resistance
                    "side": "SELL",
                    "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_reversion_timeframe(volatility_5m),
                    "reason": f"Potential reversion from ${resistance_5m:,.2f}",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(reversion_prediction)
            
            elif current_price < support_5m * 1.001:  # Very near support
                # Predict potential reversion from support
                reversion_prediction = {
                    "type": "REVERSION_FROM_SUPPORT",
                    "entry_price": support_5m * 1.0005,  # Slightly above support
                    "side": "BUY",
                    "confidence": self._calculate_reversion_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_reversion_timeframe(volatility_5m),
                    "reason": f"Potential reversion from ${support_5m:,.2f}",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(reversion_prediction)
            
            # 3. MOMENTUM PREDICTIONS
            if trend_1h.get("trend") == "UP" and trend_5m.get("trend") == "UP":
                # Strong upward momentum
                momentum_prediction = {
                    "type": "MOMENTUM_UP",
                    "entry_price": current_price * 1.0005,  # Slightly above current
                    "side": "BUY",
                    "confidence": self._calculate_momentum_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_momentum_timeframe(volatility_5m),
                    "reason": "Strong upward momentum",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(momentum_prediction)
            
            elif trend_1h.get("trend") == "DOWN" and trend_5m.get("trend") == "DOWN":
                # Strong downward momentum
                momentum_prediction = {
                    "type": "MOMENTUM_DOWN",
                    "entry_price": current_price * 0.9995,  # Slightly below current
                    "side": "SELL",
                    "confidence": self._calculate_momentum_confidence(trend_1h, trend_5m, volatility_5m),
                    "timeframe": self._calculate_momentum_timeframe(volatility_5m),
                    "reason": "Strong downward momentum",
                    "support": support_5m,
                    "resistance": resistance_5m
                }
                predictions.append(momentum_prediction)
            
            # Select best prediction
            if predictions:
                # Sort by confidence and select the best
                predictions.sort(key=lambda x: x["confidence"], reverse=True)
                best_prediction = predictions[0]
                
                logger.info(f"🔮 Price Prediction Built:")
                logger.info(f"   Type: {best_prediction['type']}")
                logger.info(f"   Entry Price: ${best_prediction['entry_price']:,.2f}")
                logger.info(f"   Side: {best_prediction['side']}")
                logger.info(f"   Confidence: {best_prediction['confidence']:.1f}%")
                logger.info(f"   Timeframe: {best_prediction['timeframe']} minutes")
                logger.info(f"   Reason: {best_prediction['reason']}")
                
                return {
                    "has_prediction": True,
                    "best_prediction": best_prediction,
                    "all_predictions": predictions,
                    "volatility_5m": volatility_5m,
                    "volatility_1h": volatility_1h,
                    "range_size": range_size_5m
                }
            else:
                return {"has_prediction": False, "reason": "No valid predictions found"}
                
        except Exception as e:
            logger.error(f"❌ Error building price prediction: {e}")
            return {"has_prediction": False, "reason": f"Prediction error: {e}"}
    
    def _analyze_entry_point(self, prediction_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Analyze entry point and determine if order should be placed"""
        try:
            predictions = prediction_analysis.get("all_predictions", [])
            if not predictions:
                return {
                    "should_place_order": False,
                    "reason": "No predictions available",
                    "variability_threshold": 0.5
                }
            
            # Get real-time Hyperliquid price for accurate stop loss calculation
            hyperliquid_price = self.get_hyperliquid_price()
            if not hyperliquid_price:
                return {
                    "should_place_order": False,
                    "reason": "Cannot get real-time Hyperliquid price for stop loss calculation",
                    "variability_threshold": 0.5
                }
            
            # Analyze both BUY and SELL opportunities
            buy_opportunities = []
            sell_opportunities = []
            
            for prediction in predictions:
                # Calculate realistic entry price based on Hyperliquid market price
                if prediction["side"] == "BUY":
                    # For BUY: entry should be at or below current Hyperliquid price
                    if prediction["type"] == "BREAKOUT_ABOVE":
                        # Wait for breakout confirmation - entry at Hyperliquid price
                        entry_price = hyperliquid_price
                    elif prediction["type"] == "REVERSION_FROM_SUPPORT":
                        # Buy near support - wait for price to reach support level
                        # Check execution timing from prediction engine
                        execution_timing = prediction.get("execution_timing", "IMMEDIATE")
                        
                        if execution_timing == "WAIT_FOR_SUPPORT":
                            # Price not at support yet - skip this opportunity
                            logger.info(f"⏳ REVERSION_FROM_SUPPORT: Waiting for price to reach support ${prediction['support']:,.2f} (current: ${hyperliquid_price:,.2f})")
                            continue
                        elif execution_timing == "IMMEDIATE" or hyperliquid_price <= prediction["support"] * 1.002:
                            # Price is at support or within 0.2% - proceed with entry
                            entry_price = hyperliquid_price
                            logger.info(f"✅ REVERSION_FROM_SUPPORT: Price ${hyperliquid_price:,.2f} at support ${prediction['support']:,.2f} - proceeding with entry")
                        else:
                            # Price not at support yet - skip this opportunity
                            logger.info(f"⏳ REVERSION_FROM_SUPPORT: Price ${hyperliquid_price:,.2f} not at support ${prediction['support']:,.2f} - waiting")
                            continue
                    elif prediction["type"] == "MOMENTUM_UP":
                        # Buy on momentum - entry at Hyperliquid price
                        entry_price = hyperliquid_price
                    else:
                        # Default: entry at Hyperliquid price
                        entry_price = hyperliquid_price
                    
                    # Calculate realistic targets using Hyperliquid price for accuracy
                    target_distance = min(0.005, self.strategy_config["profit_target"])  # Max 0.5% target (increased from 0.2%)
                    stop_distance = min(0.002, self.strategy_config["stop_loss"])  # Max 0.2% stop (increased from 0.1%)
                    
                    target_price = entry_price * (1 + target_distance)
                    stop_price = entry_price * (1 - stop_distance)
                    
                    buy_opportunities.append({
                        "prediction": prediction,
                        "entry_price": entry_price,
                        "target_price": target_price,
                        "stop_price": stop_price,
                        "risk_reward": (target_price - entry_price) / (entry_price - stop_price) if entry_price > stop_price else 0
                    })
                    
                else:  # SELL
                    # For SELL: entry should be at or above current Hyperliquid price
                    if prediction["type"] == "BREAKOUT_BELOW":
                        # Wait for breakdown confirmation - entry at Hyperliquid price
                        entry_price = hyperliquid_price
                    elif prediction["type"] == "REVERSION_FROM_RESISTANCE":
                        # Sell near resistance - wait for price to reach resistance level
                        # Check execution timing from prediction engine
                        execution_timing = prediction.get("execution_timing", "IMMEDIATE")
                        
                        if execution_timing == "WAIT_FOR_RESISTANCE":
                            # Price not at resistance yet - skip this opportunity
                            logger.info(f"⏳ REVERSION_FROM_RESISTANCE: Waiting for price to reach resistance ${prediction['resistance']:,.2f} (current: ${hyperliquid_price:,.2f})")
                            continue
                        elif execution_timing == "IMMEDIATE" or hyperliquid_price >= prediction["resistance"] * 0.998:
                            # Price is at resistance or within 0.2% - proceed with entry
                            entry_price = hyperliquid_price
                            logger.info(f"✅ REVERSION_FROM_RESISTANCE: Price ${hyperliquid_price:,.2f} at resistance ${prediction['resistance']:,.2f} - proceeding with entry")
                        else:
                            # Price not at resistance yet - skip this opportunity
                            logger.info(f"⏳ REVERSION_FROM_RESISTANCE: Price ${hyperliquid_price:,.2f} not at resistance ${prediction['resistance']:,.2f} - waiting")
                            continue
                    elif prediction["type"] == "MOMENTUM_DOWN":
                        # Sell on momentum - entry at Hyperliquid price
                        entry_price = hyperliquid_price
                    else:
                        # Default: entry at Hyperliquid price
                        entry_price = hyperliquid_price
                    
                    # Calculate realistic targets using Hyperliquid price for accuracy
                    target_distance = min(0.005, self.strategy_config["profit_target"])  # Max 0.5% target (increased from 0.2%)
                    stop_distance = min(0.002, self.strategy_config["stop_loss"])  # Max 0.2% stop (increased from 0.1%)
                    
                    target_price = entry_price * (1 - target_distance)
                    stop_price = entry_price * (1 + stop_distance)
                    
                    sell_opportunities.append({
                        "prediction": prediction,
                        "entry_price": entry_price,
                        "target_price": target_price,
                        "stop_price": stop_price,
                        "risk_reward": (entry_price - target_price) / (stop_price - entry_price) if stop_price > entry_price else 0
                    })
            
            # Choose the best opportunity
            best_opportunity = None
            best_score = 0
            
            for opportunity in buy_opportunities + sell_opportunities:
                prediction = opportunity["prediction"]
                
                # Calculate win probability
                win_probability = self._calculate_prediction_win_probability(prediction, prediction_analysis)
                
                # Check minimum confidence - made more lenient for better prediction acceptance
                min_confidence = 0.35  # Reduced from 0.45 to 0.35 (35%) for more trades
                if prediction["confidence"] < min_confidence:
                    continue
                
                # Check profitability
                profitability = self.fee_manager.is_trade_profitable(
                    opportunity["entry_price"], 
                    opportunity["target_price"], 
                    0.001, 
                    30,
                    prediction["side"]
                )
                
                if not profitability["is_profitable"]:
                    continue
                
                # Calculate opportunity score
                score = (
                    prediction["confidence"] * 0.4 +
                    win_probability * 0.3 +
                    opportunity["risk_reward"] * 0.2 +
                    profitability["profit_margin"] * 0.1
                )
                
                if score > best_score:
                    best_score = score
                    best_opportunity = opportunity
            
            if not best_opportunity:
                return {
                    "should_place_order": False,
                    "reason": "No profitable opportunities found",
                    "variability_threshold": 0.5
                }
            
            # Determine variability threshold based on strategy
            if self.strategy_name == "low_volatility":
                variability_threshold = 0.2
            elif self.strategy_name == "high_volatility":
                variability_threshold = 0.6
            else:
                variability_threshold = 0.5
            
            prediction = best_opportunity["prediction"]
            win_probability = self._calculate_prediction_win_probability(prediction, prediction_analysis)
            profitability = self.fee_manager.is_trade_profitable(
                best_opportunity["entry_price"], 
                best_opportunity["target_price"], 
                0.001, 
                30,
                prediction["side"]
            )
            
            # Log the entry analysis with price comparison
            yahoo_price = current_price  # Yahoo analysis price
            hyperliquid_exec_price = best_opportunity['entry_price']  # Hyperliquid execution price
            price_diff = abs(hyperliquid_exec_price - yahoo_price)
            price_diff_pct = (price_diff / yahoo_price) * 100
            
            logger.info(f"🎯 Entry Point Analysis:")
            logger.info(f"   Prediction Type: {prediction['type']}")
            logger.info(f"   Side: {prediction['side']}")
            logger.info(f"   Yahoo Analysis Price: ${yahoo_price:,.2f}")
            logger.info(f"   Hyperliquid Exec Price: ${hyperliquid_exec_price:,.2f}")
            logger.info(f"   Price Alignment: ${price_diff:,.2f} ({price_diff_pct:.3f}%)")
            logger.info(f"   Target Price: ${best_opportunity['target_price']:,.2f}")
            logger.info(f"   Stop Price: ${best_opportunity['stop_price']:,.2f}")
            logger.info(f"   Risk/Reward: {best_opportunity['risk_reward']:.2f}:1")
            logger.info(f"   Win Probability: {win_probability:.1f}%")
            logger.info(f"   Confidence: {prediction['confidence']*100:.1f}%")
            logger.info(f"   Profitability: {profitability['profit_margin']:.2f}% margin")
            
            return {
                "should_place_order": True,
                "side": prediction["side"],
                "entry_price": best_opportunity["entry_price"],
                "target_price": best_opportunity["target_price"],
                "stop_price": best_opportunity["stop_price"],
                "prediction_type": prediction["type"],
                "confidence": prediction["confidence"],
                "win_probability": win_probability,
                "entry_timeframe": prediction["timeframe"],
                "reason": prediction["reason"],
                "support": prediction["support"],
                "resistance": prediction["resistance"],
                "variability_threshold": variability_threshold,
                "profitability": profitability,
                "risk_reward": best_opportunity["risk_reward"]
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing entry point: {e}")
            return {
                "should_place_order": False,
                "reason": f"Entry analysis error: {e}",
                "variability_threshold": 0.5
            }
    
    def _calculate_breakout_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float) -> float:
        """Calculate confidence for breakout predictions"""
        base_confidence = 0.5
        
        # Trend alignment bonus
        if trend_1h.get("trend") == trend_5m.get("trend"):
            base_confidence += 0.2
        
        # Trend strength bonus
        trend_strength = trend_1h.get("strength", 0.5)
        base_confidence += trend_strength * 0.1
        
        # Volatility adjustment
        if volatility < 0.002:  # Low volatility = more predictable
            base_confidence += 0.1
        elif volatility > 0.005:  # High volatility = less predictable
            base_confidence -= 0.1
        
        return min(0.95, max(0.1, base_confidence))
    
    def _calculate_reversion_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float) -> float:
        """Calculate confidence for reversion predictions"""
        base_confidence = 0.4  # Lower base for reversions
        
        # Trend divergence bonus (reversion more likely when trends diverge)
        if trend_1h.get("trend") != trend_5m.get("trend"):
            base_confidence += 0.15
        
        # Volatility adjustment
        if volatility < 0.002:  # Low volatility = more predictable reversions
            base_confidence += 0.1
        elif volatility > 0.005:  # High volatility = less predictable
            base_confidence -= 0.1
        
        return min(0.9, max(0.1, base_confidence))
    
    def _calculate_momentum_confidence(self, trend_1h: Dict, trend_5m: Dict, volatility: float) -> float:
        """Calculate confidence for momentum predictions"""
        base_confidence = 0.6  # Higher base for momentum
        
        # Strong trend alignment
        if trend_1h.get("trend") == trend_5m.get("trend"):
            base_confidence += 0.2
        
        # Trend strength bonus
        trend_strength = trend_1h.get("strength", 0.5)
        base_confidence += trend_strength * 0.15
        
        # Volatility adjustment
        if volatility < 0.003:  # Moderate volatility = good for momentum
            base_confidence += 0.1
        elif volatility > 0.006:  # High volatility = less predictable
            base_confidence -= 0.1
        
        return min(0.95, max(0.1, base_confidence))
    
    def _calculate_breakout_timeframe(self, volatility: float, range_size: float) -> int:
        """Calculate expected timeframe for breakout"""
        # Base timeframe: 15-30 minutes
        base_timeframe = 20
        
        # Adjust based on volatility
        if volatility < 0.002:
            base_timeframe += 10  # Slower in low volatility
        elif volatility > 0.005:
            base_timeframe -= 5   # Faster in high volatility
        
        # Adjust based on range size
        range_percentage = range_size / 114000  # Assuming current BTC price
        if range_percentage < 0.005:  # Small range
            base_timeframe += 5
        elif range_percentage > 0.01:  # Large range
            base_timeframe -= 5
        
        return max(10, min(60, base_timeframe))  # Between 10-60 minutes
    
    def _calculate_reversion_timeframe(self, volatility: float) -> int:
        """Calculate expected timeframe for reversion"""
        # Reversions typically happen faster than breakouts
        base_timeframe = 15
        
        # Adjust based on volatility
        if volatility < 0.002:
            base_timeframe += 5
        elif volatility > 0.005:
            base_timeframe -= 3
        
        return max(8, min(45, base_timeframe))  # Between 8-45 minutes
    
    def _calculate_momentum_timeframe(self, volatility: float) -> int:
        """Calculate expected timeframe for momentum continuation"""
        # Momentum trades can be faster
        base_timeframe = 12
        
        # Adjust based on volatility
        if volatility < 0.002:
            base_timeframe += 3
        elif volatility > 0.005:
            base_timeframe -= 2
        
        return max(5, min(30, base_timeframe))  # Between 5-30 minutes
    
    def _is_prediction_valid(self, prediction: Dict[str, Any], current_price: float) -> bool:
        """Check if prediction is still valid given current price"""
        entry_price = prediction["entry_price"]
        price_diff = abs(current_price - entry_price) / current_price
        
        # Prediction is valid if price is within 0.5% of entry
        return price_diff < 0.005
    
    def _calculate_prediction_win_probability(self, prediction: Dict[str, Any], prediction_analysis: Dict[str, Any]) -> float:
        """Calculate win probability for a prediction"""
        # Ensure confidence is in decimal format (0.0 to 1.0)
        base_probability = prediction["confidence"]
        if base_probability > 1.0:  # If it's already a percentage, convert to decimal
            base_probability = base_probability / 100.0
        
        # Adjust based on volatility
        volatility_5m = prediction_analysis.get("volatility_5m", 0.003)
        if volatility_5m < 0.002:
            base_probability += 0.05  # More predictable in low volatility
        elif volatility_5m > 0.005:
            base_probability -= 0.05  # Less predictable in high volatility
        
        # Adjust based on range size
        range_size = prediction_analysis.get("range_size", 0)
        if range_size > 0:
            range_percentage = range_size / 114000
            if range_percentage > 0.01:  # Large range
                base_probability += 0.03
            elif range_percentage < 0.005:  # Small range
                base_probability -= 0.02
        
        return min(0.95, max(0.1, base_probability))
    
    def _calculate_smart_limit_price(self, side: str, current_price: float) -> float:
        """Calculate smart limit price for better execution than market price"""
        try:
            # Get market data for spread analysis
            market_data = self.hyperliquid_api.get_market_data("BTC")
            
            if market_data and 'levels' in market_data and len(market_data['levels']) >= 2:
                bids = market_data['levels'][0]
                asks = market_data['levels'][1]
                
                if bids and asks:
                    best_bid = float(bids[0]['px'])
                    best_ask = float(asks[0]['px'])
                    spread = best_ask - best_bid
                    
                    # Calculate smart limit price
                    if side == "BUY":
                        # For BUY orders, place limit slightly below current ask for better fill
                        limit_price = best_ask - (spread * 0.1)  # 10% of spread below ask
                    else:
                        # For SELL orders, place limit slightly above current bid for better fill
                        limit_price = best_bid + (spread * 0.1)  # 10% of spread above bid
                    
                    # Ensure limit price is reasonable
                    if side == "BUY" and limit_price > current_price:
                        limit_price = current_price * 0.9995  # Slightly below current price
                    elif side == "SELL" and limit_price < current_price:
                        limit_price = current_price * 1.0005  # Slightly above current price
                    
                    return limit_price
            
            # Fallback: use current price with small adjustment
            if side == "BUY":
                return current_price * 0.9995  # Slightly below current price
            else:
                return current_price * 1.0005  # Slightly above current price
                
        except Exception as e:
            logger.warning(f"Could not calculate smart limit price: {e}")
            # Fallback to current price
            return current_price
    
    def simulate_predictive_limit_order_execution(self, side: str, size: float, limit_price: float, 
                                                current_price: float, leverage: int, entry_timeframe: int, 
                                                signal_data: Dict = None) -> Dict[str, Any]:
        """Simulate predictive limit order execution with time-based order management"""
        try:
            # Calculate order expiry time
            order_placement_time = time.time()
            order_expiry_time = order_placement_time + (entry_timeframe * 60)  # Convert minutes to seconds
            
            # Simulate order monitoring and execution
            execution_price = None
            execution_time = None
            order_status = "PENDING"
            
            # Simulate price movement towards limit price
            if side == "BUY":
                # For BUY orders, price needs to drop to or below limit price
                if current_price <= limit_price:
                    # Immediate execution if price is already at/below limit
                    execution_price = min(limit_price, current_price * 0.9998)
                    execution_time = order_placement_time + 5  # 5 seconds later
                    order_status = "FILLED"
                else:
                    # Simulate price movement towards limit
                    price_gap = current_price - limit_price
                    time_to_fill = min(entry_timeframe * 60 * 0.7, price_gap / 0.001)  # 70% of timeframe or price-based
                    
                    if time_to_fill <= entry_timeframe * 60:
                        execution_price = limit_price * 0.9999  # Slightly better than limit
                        execution_time = order_placement_time + time_to_fill
                        order_status = "FILLED"
                    else:
                        # Order expires
                        order_status = "EXPIRED"
            else:
                # For SELL orders, price needs to rise to or above limit price
                if current_price >= limit_price:
                    # Immediate execution if price is already at/above limit
                    execution_price = max(limit_price, current_price * 1.0002)
                    execution_time = order_placement_time + 5  # 5 seconds later
                    order_status = "FILLED"
                else:
                    # Simulate price movement towards limit
                    price_gap = limit_price - current_price
                    time_to_fill = min(entry_timeframe * 60 * 0.7, price_gap / 0.001)  # 70% of timeframe or price-based
                    
                    if time_to_fill <= entry_timeframe * 60:
                        execution_price = limit_price * 1.0001  # Slightly better than limit
                        execution_time = order_placement_time + time_to_fill
                        order_status = "FILLED"
                    else:
                        # Order expires
                        order_status = "EXPIRED"
            
            if order_status == "EXPIRED":
                logger.warning(f"⏰ Order EXPIRED: Price didn't reach limit within {entry_timeframe} minutes")
                return {
                    "success": False,
                    "error": f"Order expired - price didn't reach ${limit_price:,.2f} within {entry_timeframe} minutes",
                    "order_status": order_status,
                    "limit_price": limit_price,
                    "current_price": current_price,
                    "entry_timeframe": entry_timeframe
                }
            
            # Calculate fees using Hyperliquid LIMIT order fee structure
            fees = self.fee_manager.calculate_order_fees(size, execution_price, "LIMIT")
            
            # Calculate position value and required margin
            position_value = size * execution_price
            required_margin = position_value / leverage
            
            # Check if we have enough balance for margin + fees
            total_required = required_margin + fees["total_cost"]
            if total_required > self.paper_balance:
                return {
                    "success": False,
                    "error": "Insufficient balance for position"
                }
            
            # Calculate target and stop prices based on strategy
            if side == "BUY":
                target_price = execution_price * (1 + self.strategy_config["profit_target"])
                stop_price = execution_price * (1 - self.strategy_config["stop_loss"])
            else:
                target_price = execution_price * (1 - self.strategy_config["profit_target"])
                stop_price = execution_price * (1 + self.strategy_config["stop_loss"])
            
            # Deduct fees from balance
            self.paper_balance -= fees["total_cost"]
            
            # Update current balance in session metadata for dashboard
            self.trading_logger.update_current_balance(self.paper_balance)
            
            # Calculate time to execution
            time_to_execution = execution_time - order_placement_time if execution_time else 0
            
            logger.info(f"✅ Predictive Order {order_status}:")
            logger.info(f"   Limit Price: ${limit_price:,.2f}")
            logger.info(f"   Execution Price: ${execution_price:,.2f}")
            logger.info(f"   Time to Execution: {time_to_execution:.1f} seconds")
            logger.info(f"   Price Improvement: ${abs(current_price - execution_price):,.2f}")
            
            return {
                "success": True,
                "execution_price": execution_price,
                "limit_price": limit_price,
                "price_improvement": abs(current_price - execution_price),
                "fees": fees,
                "position_value": position_value,
                "target_price": target_price,
                "stop_price": stop_price,
                "remaining_balance": self.paper_balance,
                "order_status": order_status,
                "execution_time": execution_time,
                "time_to_execution": time_to_execution,
                "entry_timeframe": entry_timeframe
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Predictive limit order simulation failed: {e}"
            }
    
    def simulate_limit_order_execution(self, side: str, size: float, limit_price: float, current_price: float, leverage: int) -> Dict[str, Any]:
        """Simulate limit order execution with better pricing than market orders"""
        try:
            # Limit orders typically get better execution than market orders
            # Simulate execution at or better than limit price
            if side == "BUY":
                # For BUY limit orders, we might get filled at limit price or better
                execution_price = min(limit_price, current_price * 0.9998)  # Slightly better than limit
            else:
                # For SELL limit orders, we might get filled at limit price or better
                execution_price = max(limit_price, current_price * 1.0002)  # Slightly better than limit
            
            # Calculate fees using Hyperliquid LIMIT order fee structure (much lower than market)
            fees = self.fee_manager.calculate_order_fees(size, execution_price, "LIMIT")
            
            # Calculate position value and required margin
            position_value = size * execution_price
            required_margin = position_value / leverage
            
            # Check if we have enough balance for margin + fees
            total_required = required_margin + fees["total_cost"]
            if total_required > self.paper_balance:
                return {
                    "success": False,
                    "error": "Insufficient balance for position"
                }
            
            # Calculate target and stop prices based on strategy
            if side == "BUY":
                target_price = execution_price * (1 + self.strategy_config["profit_target"])
                stop_price = execution_price * (1 - self.strategy_config["stop_loss"])
            else:
                target_price = execution_price * (1 - self.strategy_config["profit_target"])
                stop_price = execution_price * (1 + self.strategy_config["stop_loss"])
            
            # Deduct fees from balance
            self.paper_balance -= fees["total_cost"]
            
            # Update current balance in session metadata for dashboard
            self.trading_logger.update_current_balance(self.paper_balance)
            
            return {
                "success": True,
                "execution_price": execution_price,
                "limit_price": limit_price,
                "price_improvement": abs(current_price - execution_price),
                "fees": fees,
                "position_value": position_value,
                "target_price": target_price,
                "stop_price": stop_price,
                "remaining_balance": self.paper_balance
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Limit order simulation failed: {e}"
            }
    
    def _calculate_win_probability(self, variability_analysis: Dict[str, Any], binance_analysis: Dict[str, Any],
                                 current_price: float, support: float, resistance: float) -> float:
        """Calculate win probability based on multiple factors"""
        
        # Base probability starts at 50%
        base_probability = 0.5
        
        # 1. VARIABILITY SCORE CONTRIBUTION (0-20%)
        variability_score = variability_analysis.get("current_variability_score", 0.5)
        variability_contribution = variability_score * 0.2  # Up to 20% contribution
        
        # 2. TREND STRENGTH CONTRIBUTION (0-15%)
        trend_1h = binance_analysis.get("trend_1h", {})
        trend_strength = trend_1h.get("strength", 0.5)
        trend_contribution = trend_strength * 0.15  # Up to 15% contribution
        
        # 3. MARKET CONDITION CONTRIBUTION (0-10%)
        market_condition = binance_analysis.get("market_condition", "UNKNOWN")
        if market_condition in ["MEDIUM_VOLATILITY_OPTIMAL", "HIGH_VOLATILITY_OPTIMAL"]:
            market_contribution = 0.10  # Optimal conditions
        elif market_condition == "LOW_VOLATILITY_CHOPPY":
            market_contribution = 0.05  # Choppy conditions
        elif market_condition in ["EXTREME_VOLATILITY_RISKY", "EXTREME_VOLATILITY_AVOID"]:
            market_contribution = 0.02  # Risky conditions
        else:
            market_contribution = 0.07  # Standard conditions
        
        # 4. SUPPORT/RESISTANCE QUALITY CONTRIBUTION (0-10%)
        range_size = resistance - support
        if range_size > 0:
            range_percentage = range_size / current_price
            if range_percentage > 0.01:  # Good range (>1%)
                range_contribution = 0.10
            elif range_percentage > 0.005:  # Decent range (>0.5%)
                range_contribution = 0.07
            else:
                range_contribution = 0.03  # Small range
        else:
            range_contribution = 0.05
        
        # 5. WEEKLY TREND ALIGNMENT CONTRIBUTION (0-10%)
        weekly_context = self._apply_weekly_trend_context(current_price, support, resistance)
        if weekly_context.get("preferred_direction") in ["BUY", "SELL"]:
            weekly_contribution = 0.10  # Weekly trend supports our direction
        elif weekly_context.get("risk_level") == "HIGH":
            weekly_contribution = 0.03  # High risk weekly context
        else:
            weekly_contribution = 0.07  # Neutral weekly context
        
        # 6. VOLATILITY STRATEGY CONTRIBUTION (0-5%)
        if self.strategy_name == "low_volatility":
            strategy_contribution = 0.05  # Low volatility = more predictable
        elif self.strategy_name == "high_volatility":
            strategy_contribution = 0.02  # High volatility = less predictable
        else:
            strategy_contribution = 0.04  # Standard volatility
        
        # 7. PRICE POSITION CONTRIBUTION (0-10%)
        # Check if price is in a good position relative to support/resistance
        if range_size > 0:
            price_position = (current_price - support) / range_size
            if 0.2 < price_position < 0.8:  # Price in middle range
                position_contribution = 0.10
            elif 0.1 < price_position < 0.9:  # Price in good range
                position_contribution = 0.07
            else:
                position_contribution = 0.03  # Price at extremes
        else:
            position_contribution = 0.05
        
        # Calculate total probability
        total_probability = base_probability + \
                          variability_contribution + \
                          trend_contribution + \
                          market_contribution + \
                          range_contribution + \
                          weekly_contribution + \
                          strategy_contribution + \
                          position_contribution
        
        # Ensure probability is between 0.1 and 0.95
        total_probability = max(0.1, min(0.95, total_probability))
        
        return total_probability
    
    def simulate_trade_execution(self, side: str, size: float, price: float, leverage: int) -> Dict[str, Any]:
        """Simulate trade execution with realistic Hyperliquid slippage and fees"""
        # Get Hyperliquid order book for realistic slippage
        try:
            market_data = self.hyperliquid_api.get_market_data("BTC")
            if market_data and 'levels' in market_data and len(market_data['levels']) >= 2:
                bids = market_data['levels'][0]
                asks = market_data['levels'][1]
                
                if bids and asks:
                    best_bid = float(bids[0]['px'])
                    best_ask = float(asks[0]['px'])
                    spread = best_ask - best_bid
                    
                    # Calculate realistic slippage based on order book depth
                    if side == "BUY":
                        execution_price = best_ask + (spread * 0.1)  # Slight slippage for buy
                    else:
                        execution_price = best_bid - (spread * 0.1)  # Slight slippage for sell
                else:
                    # Fallback slippage
                    slippage = random.uniform(0.0001, 0.0005)
                    if side == "BUY":
                        execution_price = price * (1 + slippage)
                    else:
                        execution_price = price * (1 - slippage)
            else:
                # Fallback slippage
                slippage = random.uniform(0.0001, 0.0005)
                if side == "BUY":
                    execution_price = price * (1 + slippage)
                else:
                    execution_price = price * (1 - slippage)
        except:
            # Fallback slippage
            slippage = random.uniform(0.0001, 0.0005)
            if side == "BUY":
                execution_price = price * (1 + slippage)
            else:
                execution_price = price * (1 - slippage)
        
        # Calculate fees using Hyperliquid fee structure
        fees = self.fee_manager.calculate_order_fees(size, execution_price, "LIMIT")
        
        # Calculate position value and required margin
        position_value = size * execution_price
        required_margin = position_value / leverage
        
        # Check if we have enough balance for margin + fees
        total_required = required_margin + fees["total_cost"]
        if total_required > self.paper_balance:
            return {
                "success": False,
                "error": "Insufficient balance for position"
            }
        
        # Deduct fees from balance
        self.paper_balance -= fees["total_cost"]
        
        # Update current balance in session metadata for dashboard
        self.trading_logger.update_current_balance(self.paper_balance)
        
        return {
            "success": True,
            "execution_price": execution_price,
            "slippage": abs(execution_price - price) / price,
            "fees": fees,
            "position_value": position_value,
            "remaining_balance": self.paper_balance
        }
    
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
                prediction_confidence = signal_data.get("prediction_confidence", 0.5)
                
                logger.info(f"🔮 Placing PREDICTIVE {side} LIMIT trade:")
                logger.info(f"   Prediction Type: {prediction_type}")
                logger.info(f"   Predicted Entry: ${predicted_entry_price:,.2f}")
                logger.info(f"   Current Price: ${hyperliquid_price:,.2f}")
                logger.info(f"   Confidence: {prediction_confidence:.1f}%")
                logger.info(f"   Expected Timeframe: {entry_timeframe} minutes")
                
                # Use predicted entry price as limit price
                limit_price = predicted_entry_price
            else:
                # Fallback to smart limit price calculation
                limit_price = self._calculate_smart_limit_price(side, hyperliquid_price)
                entry_timeframe = 20
                prediction_type = "SMART_LIMIT"
                prediction_confidence = 0.5
                
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
            
            # Simulate LIMIT order execution with time-based management
            execution_result = self.simulate_predictive_limit_order_execution(
                side, size, limit_price, hyperliquid_price, leverage, entry_timeframe, signal_data
            )
            
            if not execution_result["success"]:
                error_msg = f"Paper trade failed: {execution_result['error']}"
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
                "entry_price": execution_result["execution_price"],
                "limit_price": execution_result["limit_price"],
                "size": size,
                "leverage": leverage,
                "entry_time": time.time(),
                "entry_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "fees": execution_result["fees"],
                "signal_data": signal_data,
                "target_price": execution_result["target_price"],
                "stop_price": execution_result["stop_price"],
                "current_stop_loss": execution_result["stop_price"],  # Initialize dynamic stop
                "status": "OPEN",
                "order_type": "PREDICTIVE_LIMIT",
                "prediction_type": prediction_type,
                "prediction_confidence": prediction_confidence,
                "entry_timeframe": entry_timeframe,
                "time_to_execution": execution_result.get("time_to_execution", 0),
                "order_status": execution_result.get("order_status", "FILLED"),
                "original_market_analysis": self.binance_analysis.copy(),  # Store original analysis for comparison
                "quality_evaluation": signal_data.get("quality_evaluation", {}),
                "stop_adjustment_count": 0,
                "partial_closes": [],
                "current_pnl_pct": 0.0,
                # Win-back metadata
                "is_winback_trade": signal_data.get("is_winback_trade", False),
                "winback_data": signal_data.get("winback_data", {}),
                "defensive_mode": signal_data.get("defensive_mode", False)
            }
            
            # Add to open positions
            self.open_positions.append(position)
            
            # Save positions to file
            self._save_positions()
            
            # Prepare trade data for logging
            trade_data = {
                "trade_id": position["trade_id"],
                "side": side,
                "price": execution_result["execution_price"],
                "limit_price": execution_result["limit_price"],
                "size": size,
                "leverage": leverage,
                "order_type": "LIMIT",
                "fees": execution_result["fees"],
                "price_improvement": execution_result["price_improvement"],
                "signal_data": signal_data,
                "order_result": {"status": "ok", "paper_trade": True, "hybrid": True, "limit_order": True},
                "hyperliquid_price": hyperliquid_price,
                "support": signal_data.get("support_5m") if signal_data else None,
                "resistance": signal_data.get("resistance_5m") if signal_data else None,
                "trend_5m": signal_data.get("trend_5m") if signal_data else None,
                "trend_1h": signal_data.get("trend_1h") if signal_data else None,
                "variability_score": signal_data.get("variability_analysis", {}).get("current_variability_score") if signal_data else None,
                "market_condition": signal_data.get("binance_analysis", {}).get("market_condition") if signal_data else None,
                "signal_reason": signal_data.get("reason") if signal_data else None,
                "profit_target": execution_result["target_price"],
                "stop_loss": execution_result["stop_price"],
                "risk_level": signal_data.get("variability_analysis", {}).get("risk_level") if signal_data else "STANDARD"
            }
            
            # Log the trade
            self.trading_logger.log_trade(trade_data)
            
            self.trade_history.append(trade_data)
            self.fee_manager.record_trade_fees(trade_data)
            self.last_trade_time = time.time()
            
            if prediction_type != "SMART_LIMIT":
                logger.success(f"✅ PREDICTIVE {side} LIMIT trade placed successfully!")
                logger.info(f"   Prediction Type: {prediction_type}")
                logger.info(f"   Prediction Confidence: {prediction_confidence:.1f}%")
                logger.info(f"   Predicted Entry: ${execution_result['limit_price']:,.2f}")
                logger.info(f"   Actual Execution: ${execution_result['execution_price']:,.2f}")
                logger.info(f"   Time to Execution: {execution_result.get('time_to_execution', 0):.1f}s")
                logger.info(f"   Entry Timeframe: {entry_timeframe} minutes")
            else:
                logger.success(f"✅ HYBRID PAPER {side} LIMIT trade placed successfully!")
                logger.info(f"   Limit Price: ${execution_result['limit_price']:,.2f}")
                logger.info(f"   Execution Price: ${execution_result['execution_price']:,.2f}")
            
            logger.info(f"   Position Value: ${execution_result['position_value']:,.2f}")
            logger.info(f"   Price Improvement: ${execution_result['price_improvement']:,.2f}")
            logger.info(f"   Fees: ${execution_result['fees']['total_cost']:.4f} (LIMIT ORDER - MUCH LOWER!)")
            logger.info(f"   Remaining Balance: ${execution_result['remaining_balance']:.2f}")
            
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
                    elif not condition_change["favorable"] and condition_change["confidence"] > 0.7:
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
    
    def _execute_partial_close(self, position: Dict[str, Any], partial_close_decision: Dict[str, Any], current_price: float):
        """Execute partial close of a position"""
        try:
            close_size = partial_close_decision["close_size"]
            close_pct = partial_close_decision["close_pct"]
            target_level = partial_close_decision["target_level"]
            
            # Calculate P&L for the closed portion
            entry_price = position["entry_price"]
            side = position["side"]
            
            if side == "BUY":
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            # Apply leverage
            leverage = position["leverage"]
            pnl_amount = close_size * entry_price * leverage * pnl_pct
            
            # Calculate fees
            exit_fees = self.fee_manager.calculate_order_fees(close_size, current_price, "LIMIT")
            
            # Net P&L for partial close
            net_pnl = pnl_amount - exit_fees["total_cost"]
            
            # Update balance
            self.paper_balance += net_pnl
            
            # Update current balance in session metadata for dashboard
            self.trading_logger.update_current_balance(self.paper_balance)
            
            # Update position size
            position["size"] -= close_size
            
            # Record partial close
            partial_close_record = {
                "timestamp": time.time(),
                "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "close_size": close_size,
                "close_pct": close_pct,
                "close_price": current_price,
                "target_level": target_level,
                "pnl_pct": pnl_pct,
                "pnl_amount": pnl_amount,
                "net_pnl": net_pnl,
                "fees": exit_fees
            }
            
            position["partial_closes"].append(partial_close_record)
            
            # Log the partial close
            logger.success(f"💰 Partial close executed: {target_level}")
            logger.info(f"   Closed: {close_size} BTC ({close_pct*100:.0f}% of position)")
            logger.info(f"   Price: ${current_price:,.2f}")
            logger.info(f"   P&L: {pnl_pct*100:.2f}% (${net_pnl:.4f})")
            logger.info(f"   Remaining size: {position['size']} BTC")
            logger.info(f"   Paper Balance: ${self.paper_balance:.2f}")
            
            # Save updated positions
            self._save_positions()
            
        except Exception as e:
            logger.error(f"❌ Error executing partial close: {e}")
            self.trading_logger.log_error({
                "type": "partial_close_error",
                "message": str(e),
                "position_id": position.get("trade_id"),
                "partial_close_decision": partial_close_decision
            })
    
    def _execute_scale_in(self, position: Dict[str, Any], scale_decision: Dict[str, Any], current_price: float):
        """Execute scaling into an existing position"""
        try:
            scale_size = scale_decision["scale_size"]
            scale_price = scale_decision["scale_price"]
            
            # Check if we have enough balance for the scale-in
            position_value = scale_size * scale_price
            leverage = position["leverage"]
            required_margin = position_value / leverage
            
            # Calculate fees
            fees = self.fee_manager.calculate_order_fees(scale_size, scale_price, "LIMIT")
            total_required = required_margin + fees["total_cost"]
            
            if total_required > self.paper_balance:
                logger.warning(f"⚠️ Insufficient balance for scale-in: need ${total_required:.2f}, have ${self.paper_balance:.2f}")
                return
            
            # Deduct fees from balance
            self.paper_balance -= fees["total_cost"]
            
            # Update current balance in session metadata for dashboard
            self.trading_logger.update_current_balance(self.paper_balance)
            
            # Update position with scaled-in size
            original_size = position["size"]
            position["size"] += scale_size
            
            # Calculate new average entry price
            original_value = original_size * position["entry_price"]
            scale_value = scale_size * scale_price
            total_value = original_value + scale_value
            new_avg_entry = total_value / position["size"]
            
            # Update position entry price to weighted average
            position["entry_price"] = new_avg_entry
            
            # Record scale-in
            scale_record = {
                "timestamp": time.time(),
                "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "scale_size": scale_size,
                "scale_price": scale_price,
                "original_size": original_size,
                "new_size": position["size"],
                "original_entry": position["entry_price"],
                "new_avg_entry": new_avg_entry,
                "fees": fees
            }
            
            if "scale_ins" not in position:
                position["scale_ins"] = []
            position["scale_ins"].append(scale_record)
            
            # Log the scale-in
            logger.success(f"📈 Scale-in executed successfully")
            logger.info(f"   Added: {scale_size} BTC at ${scale_price:,.2f}")
            logger.info(f"   New total size: {position['size']} BTC")
            logger.info(f"   New avg entry: ${new_avg_entry:,.2f}")
            logger.info(f"   Fees: ${fees['total_cost']:.4f}")
            logger.info(f"   Remaining balance: ${self.paper_balance:.2f}")
            
            # Save updated positions
            self._save_positions()
            
        except Exception as e:
            logger.error(f"❌ Error executing scale-in: {e}")
            self.trading_logger.log_error({
                "type": "scale_in_error",
                "message": str(e),
                "position_id": position.get("trade_id"),
                "scale_decision": scale_decision
            })
    
    def close_paper_position(self, position: Dict, exit_reason: str, exit_price: float):
        """Close a paper trading position"""
        entry_price = position["entry_price"]
        side = position["side"]
        size = position["size"]
        leverage = position["leverage"]
        
        # Calculate P&L
        if side == "BUY":
            price_change = (exit_price - entry_price) / entry_price
        else:
            price_change = (entry_price - exit_price) / entry_price
        
        # Apply leverage
        pnl_pct = price_change * leverage
        pnl_amount = size * entry_price * leverage * pnl_pct
        
        # Calculate fees
        exit_fees = self.fee_manager.calculate_order_fees(size, exit_price, "LIMIT")
        total_fees = position["fees"]["total_cost"] + exit_fees["total_cost"]
        
        # Net P&L
        net_pnl = pnl_amount - total_fees
        
        # Update balance
        self.paper_balance += net_pnl
        
        # Update current balance in session metadata for dashboard
        self.trading_logger.update_current_balance(self.paper_balance)
        
        # Update position
        position.update({
            "exit_price": exit_price,
            "exit_time": time.time(),
            "exit_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_reason": exit_reason,
            "pnl_pct": pnl_pct,
            "pnl_amount": pnl_amount,
            "total_fees": total_fees,
            "net_pnl": net_pnl,
            "status": "CLOSED",
            "was_profitable": net_pnl > 0
        })
        
        # Move to closed positions
        self.open_positions.remove(position)
        self.closed_positions.append(position)
        
        # Save updated positions
        self._save_positions()
        
        # Update trade result in logger
        trade_result = {
            "trade_id": position["trade_id"],
            "exit_price": exit_price,
            "profit_loss": pnl_amount,
            "profit_loss_pct": pnl_pct,
            "fees_paid": total_fees,
            "net_profit_loss": net_pnl,
            "holding_time": position["exit_time"] - position["entry_time"],
            "exit_reason": exit_reason,
            "was_profitable": net_pnl > 0,
            "balance_after": self.paper_balance,
            "is_winback_trade": position.get("is_winback_trade", False),
            "winback_data": position.get("winback_data", {})
        }
        
        self.trading_logger.update_trade_result(position["trade_id"], trade_result)
        
        # Register with win-back engine
        if self.win_back_engine:
            if net_pnl < 0:  # This was a loss
                self.win_back_engine.register_loss(trade_result)
            elif trade_result.get("is_winback_trade", False):  # This was a win-back trade
                self.win_back_engine.register_winback_result(trade_result)
        
        # Register with real-time data manager for instant dashboard updates
        if self.trading_data_manager:
            self.trading_data_manager.add_trade(trade_result)
            # Update balance in real-time
            self.trading_data_manager.update_balance(self.paper_balance, f"Trade closed: {exit_reason}")
        
        # Calculate position value in USD
        position_value_usd = size * entry_price
        
        logger.info(f"📊 Position closed: {position['trade_id']}")
        logger.info(f"   {side} {size} BTC (${position_value_usd:,.2f}) @ ${entry_price:,.2f} → ${exit_price:,.2f}")
        logger.info(f"   P&L: {pnl_pct*100:.2f}% (${pnl_amount:.4f})")
        logger.info(f"   Net P&L: ${net_pnl:.4f} (fees: ${total_fees:.4f})")
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
        logger.info(f"   Analysis Frequency: Price every {self.price_update_interval}s, Signals every {self.signal_check_interval}s (ULTRA-FAST)")
        logger.info(f"   Strategy: Auto-Detection (Standard/Low/High Volatility)")
        logger.info(f"   Weekly Context: {self.weekly_trend_analysis.get('weekly_trend', 'UNKNOWN')} ({self.weekly_trend_analysis.get('weekly_change_pct', 0):.2f}%)")
        logger.info(f"   Whale Analytics: {'Enabled' if self.whale_integration.is_available() else 'Disabled'}")
        logger.info(f"   Logging: Comprehensive Yahoo + Hyperliquid paper trading logs enabled")
        
        # Initialize professional data systems
        if self.smart_data_cache:
            logger.info("📚 INITIALIZING SMART DATA CACHE - This happens once per session...")
            if self.smart_data_cache.initialize_historical_data("BTC"):
                logger.success("✅ Historical data loaded - Ready for incremental updates")
            else:
                logger.error("❌ Failed to initialize data cache")
        
        if self.trading_data_manager:
            session_id = self.trading_data_manager.start_session(
                strategy=self.strategy_name
            )
            logger.success("🔥 Real-time data manager active - Dashboard connection established")
            logger.info(f"   📊 Dashboard will receive live predictions and market data")
            
            # Add initial activity log
            self.trading_data_manager.add_activity({
                "timestamp": time.time(),
                "message": f"🚀 Trading bot started - {self.strategy_name} strategy with ${self.initial_balance:.2f} initial balance",
                "type": "startup",
                "level": "SUCCESS"
            })
        else:
            logger.warning("⚠️ Real-time data manager not available - Dashboard will show offline data only")
        
        # Start advanced monitoring systems
        if self.dynamic_stop_manager:
            self.dynamic_stop_manager.start_monitoring(self)
            logger.info(f"🛡️ Dynamic stop monitoring: Every 3 seconds with volatility awareness")
        
        if self.global_volume_aggregator:
            logger.info(f"🌍 Global volume tracking: Real-time aggregation from 6 exchanges")
        
        if self.blockchain_analyzer:
            logger.info(f"⛓️ Blockchain analytics: On-chain sentiment and network activity")
        
        if self.win_back_engine:
            logger.info(f"🔥 Win-back engine: Smart revenge trading after losses (1.8x position boost)")
        
        logger.info("=" * 50)
        
        trades_placed = 0
        
        while trades_placed < max_trades:
            try:
                current_time = time.time()
                
                # Update Hyperliquid price data frequently
                hyperliquid_price = self.get_hyperliquid_price()
                if not hyperliquid_price:
                    logger.warning("⚠️ Could not get Hyperliquid price, retrying...")
                    time.sleep(check_interval)
                    continue
                
                # Get current Hyperliquid volume/liquidity data
                hyperliquid_indicators = self.hyperliquid_api.get_current_market_indicators("BTC")
                if hyperliquid_indicators and "liquidity_metrics" in hyperliquid_indicators:
                    liquidity = hyperliquid_indicators["liquidity_metrics"]
                    imbalance = liquidity.get("depth_imbalance", 0)
                    total_depth = liquidity.get("total_depth", 0)
                    
                    # Log significant market conditions
                    if abs(imbalance) > 0.3:  # > 30% imbalance
                        direction = "BEARISH (Heavy Selling)" if imbalance < -0.3 else "BULLISH (Heavy Buying)"
                        logger.warning(f"🚨 SIGNIFICANT ORDERBOOK IMBALANCE: {direction} ({imbalance*100:+.1f}%)")
                        logger.warning(f"   Total Depth: {total_depth:.2f} BTC, Bid: {liquidity.get('bid_depth', 0):.2f} BTC, Ask: {liquidity.get('ask_depth', 0):.2f} BTC")
                    
                    # Store for analysis
                    self.hyperliquid_volume_data = hyperliquid_indicators
                else:
                    self.hyperliquid_volume_data = None
                
                # Check for position exits with advanced management
                self.check_position_exits(hyperliquid_price, self.binance_analysis)
                
                # Update market data for dashboard (every 10 seconds)
                if current_time - self.last_market_update >= 10:
                    # Use smart cache for efficient data updates
                    if self.smart_data_cache:
                        # Only fetch NEW candles (usually 0-1 new candles)
                        cache_update = self.smart_data_cache.update_latest_candles("BTC")
                        if cache_update["success"]:
                            # Get analysis from cached data (no API calls)
                            yahoo_analysis = self.smart_data_cache.get_market_analysis("BTC", hyperliquid_price)
                            if yahoo_analysis:
                                self.binance_analysis = yahoo_analysis
                                self.last_market_update = current_time
                                
                                # Update real-time data manager with REAL calculated values
                                if self.trading_data_manager:
                                    # Calculate IMMEDIATE accurate RSI using Smart Cache + Hyperliquid current price
                                    real_rsi = 50.0  # Default
                                    try:
                                        if self.smart_data_cache and self.smart_data_cache.cache_initialized:
                                            # Get MORE historical candles for BETTER initial accuracy
                                            cached_candles = self.smart_data_cache.get_candles("5m", 50)  # 50 candles for stability
                                            if cached_candles and len(cached_candles) >= 30:
                                                # Extract closes + add current Hyperliquid price
                                                closes = [float(candle["close"]) for candle in cached_candles[-30:]]  # Use 30 historical points
                                                closes.append(hyperliquid_price)  # Add current price as latest data point
                                                
                                                # Calculate CRYPTO-OPTIMIZED RSI (21-period for better crypto accuracy)
                                                real_rsi = self._calculate_rsi_from_price_samples(closes, periods=21)
                                                logger.info(f"🎯 ENHANCED RSI: {real_rsi:.1f} (21-period, 31 data points for crypto accuracy)")
                                            elif cached_candles and len(cached_candles) >= 14:
                                                # Fallback to standard 14-period if insufficient data
                                                closes = [float(candle["close"]) for candle in cached_candles[-14:]]
                                                closes.append(hyperliquid_price)
                                                real_rsi = self._calculate_rsi_from_price_samples(closes, periods=14)
                                                logger.info(f"📊 STANDARD RSI: {real_rsi:.1f} (14-period fallback)")
                                            else:
                                                logger.warning(f"Insufficient cached candles: {len(cached_candles) if cached_candles else 0}")
                                        else:
                                            # Fallback to cached calculation
                                            real_rsi = self.cached_rsi_data.get("rsi", 50.0) if hasattr(self, 'cached_rsi_data') and self.cached_rsi_data else 50.0
                                            logger.info(f"📊 Fallback RSI: {real_rsi:.1f}")
                                    except Exception as e:
                                        logger.debug(f"Immediate RSI calculation failed: {e}")
                                        real_rsi = self.cached_rsi_data.get("rsi", 50.0) if hasattr(self, 'cached_rsi_data') and self.cached_rsi_data else 50.0
                                    
                                    # Get REAL volume from direct API call
                                    try:
                                        volume_result = self.hyperliquid_api.get_current_5m_volume("BTC")
                                        real_volume = volume_result.get("current_volume", 0.0)
                                        volume_category = volume_result.get("volume_category", "UNKNOWN")
                                        logger.debug(f"📊 Direct volume fetch: {real_volume:.1f} BTC ({volume_category})")
                                    except Exception as e:
                                        logger.debug(f"Volume fetch failed: {e}")
                                        real_volume = 0.0
                                        volume_category = "FETCH_ERROR"
                                    
                                    # Get REAL orderbook imbalance from market data
                                    try:
                                        market_data = self.hyperliquid_api.get_market_data("BTC")
                                        if market_data and "levels" in market_data:
                                            bids = market_data['levels'][0][:10] if market_data['levels'][0] else []
                                            asks = market_data['levels'][1][:10] if market_data['levels'][1] else []
                                            
                                            total_bid_volume = sum(float(bid['sz']) for bid in bids)
                                            total_ask_volume = sum(float(ask['sz']) for ask in asks)
                                            
                                            if total_bid_volume + total_ask_volume > 0:
                                                real_imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume) * 100
                                            else:
                                                real_imbalance = 0.0
                                            logger.debug(f"📊 Direct orderbook imbalance: {real_imbalance:.1f}%")
                                        else:
                                            real_imbalance = 0.0
                                    except Exception as e:
                                        logger.debug(f"Orderbook imbalance calc failed: {e}")
                                        real_imbalance = 0.0
                                    
                                    logger.info(f"📊 Updating dashboard: RSI={real_rsi:.1f}, Volume={real_volume:.1f} BTC ({volume_category}), Imbalance={real_imbalance:.3f}")
                                    
                                    self.trading_data_manager.update_market_data({
                                        "current_price": hyperliquid_price,
                                        "trend": yahoo_analysis.get("trend_5m", {}).get("trend", "UNKNOWN"),
                                        "market_condition": yahoo_analysis.get("market_condition", "UNKNOWN"),
                                        "rsi": real_rsi,  # REAL RSI from calculations
                                        "volume_depth": real_volume,  # REAL volume from analysis
                                        "orderbook_imbalance": real_imbalance,  # REAL imbalance
                                        "volatility_5m": yahoo_analysis.get("volatility_5m", 0.0),
                                        "volatility_1h": yahoo_analysis.get("volatility_1h", 0.0),
                                        "support": yahoo_analysis.get("support_resistance_5m", {}).get("support", 0),
                                        "resistance": yahoo_analysis.get("support_resistance_5m", {}).get("resistance", 0),
                                        "volume_category": volume_category,
                                        "volume_trend": "CALCULATED",  # Using smart cache data
                                        "data_source": "smart_cache_real_values"
                                    })
                                
                                logger.info(f"💾 Smart cache update: {cache_update.get('api_calls_saved', 0)} API calls saved")
                    else:
                        # Fallback to old method if smart cache not available
                        yahoo_analysis = self.get_yahoo_analysis(hyperliquid_price=hyperliquid_price)
                        if yahoo_analysis:
                            self.binance_analysis = yahoo_analysis
                            self.last_market_update = current_time
                        
                        # Log market data for dashboard (Hyperliquid price + Yahoo historical comparison)
                        self.trading_logger.log_analysis({
                            "type": "hybrid_analysis_update",
                            "timeframe": "5m",
                            "support_resistance": yahoo_analysis.get("support_resistance_5m", {}),
                            "trend_analysis": yahoo_analysis.get("trend_5m", {}),
                            "market_condition": yahoo_analysis.get("market_condition", "UNKNOWN"),
                            "hyperliquid_price": hyperliquid_price,
                            "yahoo_last_close": yahoo_analysis.get("yahoo_last_close", hyperliquid_price),
                            "price_difference_pct": yahoo_analysis.get("price_difference_pct", 0.0),
                            "price_difference_amount": yahoo_analysis.get("price_difference", 0.0),
                            "data_source": "Yahoo Finance (Historical) + Hyperliquid (Real-time Price)"
                        })
                
                # Update Yahoo analysis periodically (every 30 seconds)
                if current_time - self.last_candle_update >= self.candle_update_interval:
                    yahoo_analysis = self.get_yahoo_analysis(hyperliquid_price=hyperliquid_price)
                    if yahoo_analysis:
                        self.binance_analysis = yahoo_analysis  # Keep variable name for compatibility
                        self.last_candle_update = current_time
                        
                        # Log analysis (Hyperliquid price + Yahoo historical comparison)
                        self.trading_logger.log_analysis({
                            "type": "hybrid_analysis_update",
                            "timeframe": "5m",
                            "support_resistance": yahoo_analysis.get("support_resistance_5m", {}),
                            "trend_analysis": yahoo_analysis.get("trend_5m", {}),
                            "market_condition": yahoo_analysis.get("market_condition", "UNKNOWN"),
                            "hyperliquid_price": hyperliquid_price,
                            "yahoo_last_close": yahoo_analysis.get("yahoo_last_close", hyperliquid_price),
                            "price_difference_pct": yahoo_analysis.get("price_difference_pct", 0.0),
                            "price_difference_amount": yahoo_analysis.get("price_difference", 0.0),
                            "data_source": "Yahoo Finance (Historical) + Hyperliquid (Real-time Price)"
                        })
                
                # Check for signals periodically
                if current_time - self.last_signal_check >= self.signal_check_interval:
                    if not self.binance_analysis or not self.binance_analysis.get("market_condition"):
                        logger.warning("⚠️ Could not get Yahoo analysis, retrying...")
                        time.sleep(check_interval)
                        continue
                    
                    logger.info(f"🔍 SIGNAL CHECK: Starting signal analysis at ${hyperliquid_price:.2f}")
                    
                    # Update dashboard with analysis activity
                    if self.trading_data_manager:
                        activity_data = {
                            "timestamp": current_time,
                            "message": f"🔍 Analyzing market conditions at ${hyperliquid_price:.2f}",
                            "type": "analysis",
                            "level": "INFO"
                        }
                        self.trading_data_manager.add_activity(activity_data)
                        logger.debug(f"📊 Activity logged to dashboard: {activity_data['message']}")
                    else:
                        logger.warning("⚠️ Trading data manager not available - activity not logged to dashboard")
                    
                    # Enhanced analysis with global volume and blockchain data
                    enhanced_analysis = self.binance_analysis.copy()
                    
                    # Add global volume data
                    if self.global_volume_aggregator:
                        global_volume_data = self.global_volume_aggregator.get_realtime_global_volume()
                        enhanced_analysis["global_volume"] = global_volume_data
                        if global_volume_data.get("status") == "success":
                            logger.info(f"🌍 Global Volume: {global_volume_data['global_volume_per_second']:.1f} BTC/sec")
                    
                    # Add blockchain sentiment
                    if self.blockchain_analyzer:
                        blockchain_data = self.blockchain_analyzer.get_onchain_sentiment()
                        enhanced_analysis["blockchain_sentiment"] = blockchain_data
                        if blockchain_data.get("confidence", 0) > 0.5:
                            sentiment = blockchain_data["overall_sentiment"]
                            logger.info(f"⛓️ On-chain Sentiment: {sentiment}")
                    
                    # Analyze market using enhanced data (Yahoo historical + Hyperliquid real-time + Global volume + Blockchain)
                    signal = self.should_trade(hyperliquid_price, enhanced_analysis)
                    
                    logger.info(f"🎯 SIGNAL RESULT: {signal.get('should_trade', False)} | Reason: {signal.get('reason', 'Unknown')}")
                    
                    # Always update dashboard with prediction status, even if no trade signal
                    if self.trading_data_manager and not signal["should_trade"]:
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
                        self.trading_data_manager.update_predictions([no_signal_prediction])
                        
                        # Add analysis activity
                        self.trading_data_manager.add_activity({
                            "timestamp": time.time(),
                            "message": f"📊 Analysis complete: {signal.get('reason', 'No clear signal')[:80]}{'...' if len(signal.get('reason', '')) > 80 else ''}",
                            "type": "analysis",
                            "level": "INFO"
                        })
                        logger.debug(f"📊 NO-SIGNAL status sent to dashboard: {signal.get('reason', 'Unknown')}")
                    
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
                        
                        # Update dashboard with signal activity
                        if self.trading_data_manager:
                            confidence_pct = quality_eval.get('confidence_level', 'Unknown') if quality_eval else 'Unknown'
                            self.trading_data_manager.add_activity({
                                "timestamp": current_time,
                                "message": f"🚀 {signal['side']} signal: {signal['reason'][:50]}{'...' if len(signal['reason']) > 50 else ''}",
                                "type": "signal",
                                "level": "SUCCESS"
                            })
                        
                        # Place the paper trade
                        if self.place_paper_trade(signal['side'], signal_data=signal):
                            trades_placed += 1
                            logger.info(f"   Paper Trade {trades_placed}/{max_trades} completed")
                            
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
                    
                    else:
                        logger.info(f"⏳ No signal: {signal['reason']}")
                    
                    self.last_signal_check = current_time
                
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
        # Stop advanced monitoring systems
        if self.dynamic_stop_manager:
            self.dynamic_stop_manager.stop_monitoring()
            logger.info("🛡️ Dynamic stop monitoring stopped")
        
        # End real-time session
        if self.trading_data_manager:
            self.trading_data_manager.end_session()
            logger.info("📊 Real-time data session ended")
        
        # Show smart cache performance
        if self.smart_data_cache:
            cache_perf = self.smart_data_cache.get_cache_performance()
            logger.info(f"💾 Smart Cache Performance:")
            logger.info(f"   API calls saved: {cache_perf['total_api_calls_saved']}")
            logger.info(f"   Cache hit ratio: {cache_perf['cache_hit_ratio']:.1%}")
            logger.info(f"   Initialization time: {cache_perf['initialization_time']:.2f}s")
        
        # Show win-back performance
        if self.win_back_engine:
            winback_stats = self.win_back_engine.get_winback_status()
            if winback_stats["stats"]["attempts"] > 0:
                success_rate = winback_stats["stats"]["success_rate"] * 100
                total_recovered = winback_stats["stats"]["total_recovered"]
                logger.info(f"🔥 Win-Back Performance: {success_rate:.1f}% success rate")
                logger.info(f"   Total Recovered: ${total_recovered:.2f}")
                logger.info(f"   Attempts: {winback_stats['stats']['attempts']}")
            else:
                logger.info("🔥 Win-Back Engine: No recovery attempts needed this session")
        
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
            
            # Close any remaining open positions
            hyperliquid_price = self.get_hyperliquid_price()
            if hyperliquid_price:
                for position in self.open_positions[:]:  # Copy list to avoid modification during iteration
                    self.close_paper_position(position, "GRACEFUL_SHUTDOWN", hyperliquid_price)
            
            # Stop advanced monitoring systems
            if self.dynamic_stop_manager:
                self.dynamic_stop_manager.stop_monitoring()
                logger.info("🛡️ Dynamic stop monitoring stopped")
            
            # End real-time session
            if self.trading_data_manager:
                self.trading_data_manager.end_session()
                logger.info("📊 Real-time data session ended")
            
            # Update final balance
            if self.trading_logger:
                self.trading_logger.update_current_balance(self.paper_balance)
            
            logger.success(f"✅ Trading session closed gracefully!")
            logger.info(f"   Final Balance: ${self.paper_balance:.2f}")
            logger.info(f"   Total P&L: ${self.paper_balance - self.initial_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Error during graceful session closure: {e}")


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
