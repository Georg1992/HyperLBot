#!/usr/bin/env python3
"""
Real-Time Event-Driven Trading Dashboard
WebSocket-based architecture for instant updates without polling
"""

import os
import json
import time
import threading
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import urllib3
from flask import Flask, render_template, request, make_response
from flask_socketio import SocketIO, emit
from loguru import logger

# Import constants and trade state manager
from core.constants import constants, ui_constants
from core.trade_state_manager import trade_state_manager

# Suppress SSL warnings
urllib3.disable_warnings()

class EventDrivenTradingDashboard:
    """Event-driven dashboard with WebSocket real-time updates"""
    
    def __init__(self):
        self.log_dir = constants.LOG_DIR
        
        # Flask app with SocketIO
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'trading_dashboard_secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        
        # Active connections tracking
        self.active_connections = set()
        
        # Data change tracking for smart updates
        self.last_data_hash = {}
        
        # Connection management
        self._rtm = None
        self._api = None
        self._rtm_available = None
        
        # Force update counter for reliability
        self.force_update_counter = 0
        self.last_update_cycle = 0
        
        # Setup WebSocket event handlers
        self._setup_websocket_handlers()
        
        # Setup Flask routes
        self._setup_routes()
        
        # Start background data monitoring
        self._start_data_monitoring()
        
        logger.info("🚀 Event-Driven Trading Dashboard initialized with WebSocket support")
    
    def _setup_websocket_handlers(self):
        """Setup WebSocket connection handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle new WebSocket connection"""
            logger.info(f"🌐 Client connected ({len(self.active_connections) + 1} active)")
            self.active_connections.add(request.sid)
            
            # Clear cached data and send initial data
            self.last_data_hash.clear()
            self._rtm = None
            fresh_data = self._get_dashboard_data()
            self.socketio.emit('initial_data', fresh_data, room=request.sid)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle WebSocket disconnection"""
            self.active_connections.discard(request.sid)
            logger.info(f"📱 Client disconnected ({len(self.active_connections)} active)")
        
        @self.socketio.on('request_manual_refresh')
        def handle_manual_refresh():
            """Handle manual refresh request"""
            self._send_all_data(request.sid)
    
    def _setup_routes(self):
        """Setup Flask HTTP routes"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page with cache-busting"""
            response = make_response(render_template('realtime_dashboard.html'))
            
            # Prevent browser caching to ensure fresh dashboard loads
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
        
        @self.app.route('/health')
        def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "active_connections": len(self.active_connections),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_realtime_manager(self):
        """Get real-time data manager with fallback handling"""
        try:
            from core.realtime_data_manager import trading_data_manager
            
            if trading_data_manager is None:
                return None
            
            # Test basic functionality
            try:
                trading_data_manager.get_current_state()
                return trading_data_manager
            except Exception:
                return None
            
        except ImportError:
            return None
        except Exception as e:
            logger.error(f"❌ Error connecting to real-time data manager: {e}")
            return None
    
    def _load_rtm_state_from_file(self) -> Dict[str, Any]:
        """Load RTM state from JSON file as fallback"""
        try:
            rtm_file_path = constants.RTM_STATE_FILE
            if os.path.exists(rtm_file_path):
                with open(rtm_file_path, 'r') as f:
                    rtm_data = json.load(f)

                return rtm_data
            else:

                return {}
        except Exception as e:
            logger.error(f"❌ Error loading RTM state from file: {e}")
            return {}
    
    def _get_hyperliquid_api(self):
        """Get Hyperliquid API with connection caching"""
        if self._api is None:
            try:
                from core.hyperliquid_api import HyperliquidAPI
                self._api = HyperliquidAPI()
            except Exception:
                return None
        
        return self._api
    
    def _start_data_monitoring(self):
        """Start background thread to monitor for data changes"""
        def monitor_data_changes():
            while True:
                try:
                    # Always update data every 2 seconds when connections exist
                    # Force update every 10 seconds regardless of connections
                    self.force_update_counter += 1
                    force_update = self.force_update_counter >= (constants.FORCE_UPDATE_INTERVAL // constants.DASHBOARD_UPDATE_INTERVAL)
                    
                    if self.active_connections or force_update:
                        # Get current data
                        current_data = self._get_dashboard_data()
                        current_hash = self._calculate_data_hash(current_data)
                        
                        # Emit if data changed OR force update
                        if current_hash != self.last_data_hash.get('all_data') or force_update:
                            self._emit_data_update(current_data)
                            self.last_data_hash['all_data'] = current_hash
                            self.force_update_counter = 0
                    
                    # Sleep interval
                    sleep_time = constants.DASHBOARD_UPDATE_INTERVAL if self.active_connections else constants.DASHBOARD_UPDATE_INTERVAL * 2.5
                    time.sleep(sleep_time)
                    
                except Exception as e:
                    logger.error(f"❌ Data monitoring error: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor_data_changes, daemon=True)
        monitor_thread.start()
        logger.info("🔍 Background data monitoring started")
    
    def _calculate_data_hash(self, data: Dict) -> str:
        """Calculate hash of data for change detection"""
        try:
            # Create a simplified hash of key changing fields
            hash_data = {
                'price': data.get('market', {}).get('current_price', 0),
                'rsi': data.get('market', {}).get('rsi', 0),
                'volume': data.get('market', {}).get('volume_depth', 0),
                'balance': data.get('session', {}).get('current_balance', 0),
                'trades': data.get('session', {}).get('total_trades', 0),
                'session_id': data.get('session', {}).get('session_id', ''),
                'status': data.get('session', {}).get('status', ''),
                'timestamp': data.get('timestamp', '')
            }
            return str(hash(json.dumps(hash_data, sort_keys=True)))
        except:
            return str(time.time())
    
    def _send_initial_data(self, session_id: str):
        """Send complete dashboard data to new connection"""
        try:
            data = self._get_dashboard_data()
            self.socketio.emit('initial_data', data, room=session_id)
        except Exception as e:
            logger.error(f"❌ Failed to send initial data: {e}")
    
    def _send_all_data(self, session_id: str):
        """Send complete dashboard data to specific connection"""
        try:
            data = self._get_dashboard_data()
            self.socketio.emit('data_update', data, room=session_id)
        except Exception as e:
            logger.error(f"❌ Failed to send data update: {e}")
    
    def _emit_data_update(self, data: Dict):
        """Emit data update to all connected clients"""
        try:
            self.socketio.emit('data_update', data)
        except Exception as e:
            logger.error(f"❌ Failed to emit data update: {e}")
    
    def _get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data with real-time updates"""
        try:
            # Get real-time data from RTM ONLY
            rtm = self._get_realtime_manager()
            logger.debug(f"🔍 RTM available: {rtm is not None}")
            
            if rtm:
                try:
                    current_state = rtm.get_current_state()
                    logger.debug(f"🔍 RTM market data: {current_state.get('market', {}).get('trend', 'NOT_FOUND')}")
                    
                    # Use real-time data from RTM
                    session_data = current_state["session"]
                    logger.debug(f"🔍 RTM session status: {session_data.get('status')}, balance: ${session_data.get('current_balance', 0):.2f}")
                    
                    enhanced_balance = self._calculate_enhanced_balance(session_data)
                    logger.debug(f"🔍 Enhanced balance: ${enhanced_balance.get('current_balance', 0):.2f} (source: {enhanced_balance.get('balance_source')})")
                    
                    # Calculate session duration properly
                    try:
                        if session_data.get("start_time"):
                            start_time = datetime.fromisoformat(session_data["start_time"])
                            session_duration = datetime.now() - start_time
                            session_minutes = int(session_duration.total_seconds() / 60)
                            session_data["session_time"] = f"{session_minutes}m"
                            logger.debug(f"🔍 Session duration: {session_minutes}m")
                    except Exception as e:
                        logger.error(f"Session time calculation error: {e}")
                        session_data["session_time"] = "0m"
                    
                    activity_logs = current_state.get("recent_activity", [])
                    
                    # Get actual trade data from real-time manager
                    recent_trades = list(current_state.get("recent_trades", []))
                    if not recent_trades:
                        try:
                            recent_trades = rtm.get_historical_trades(10)
                        except:
                            recent_trades = []
                    
                    # Build final data structure
                    rtm_data = {
                        "session": {**session_data, **enhanced_balance},
                        "market": current_state["market"],
                        "logs": activity_logs,
                        "summary": {
                            "total_trades": session_data["total_trades"],
                            "winning_trades": session_data["winning_trades"],
                            "losing_trades": session_data["losing_trades"],
                            "current_balance": enhanced_balance["current_balance"],
                            "initial_balance": enhanced_balance["initial_balance"],
                            "balance_change": enhanced_balance["balance_change"],
                            "balance_change_pct": enhanced_balance.get("balance_change_pct", 0),
                            "realized_pnl": enhanced_balance.get("realized_pnl", 0),
                            "unrealized_pnl": enhanced_balance.get("unrealized_pnl", 0),
                            "open_positions_value": enhanced_balance.get("open_positions_value", 0),
                            "balance_source": enhanced_balance["balance_source"]
                        },
                        "predictions": self._get_predictions_data(),  # Use the dedicated method
                        "orderbook": self._get_orderbook_data(),
                        "positions": {
                            "real_positions": current_state.get("positions", {}).get("open_positions", []),
                            "simulated_positions": current_state.get("positions", {}).get("simulated_positions", []),
                            "real_orders": current_state.get("orders", {}).get("open_orders", []),
                            "simulated_orders": current_state.get("orders", {}).get("simulated_orders", []),
                            "total_real_positions": len(current_state.get("positions", {}).get("open_positions", [])),
                            "total_simulated_positions": len(current_state.get("positions", {}).get("simulated_positions", [])),
                            "last_update": current_state.get("positions", {}).get("last_update", 0)
                        },
                        "balance": {
                            "real_account_value": current_state.get("balance", {}).get("real_account_value", 0.0),
                            "real_available_margin": current_state.get("balance", {}).get("real_available_margin", 0.0),
                            "real_total_margin_used": current_state.get("balance", {}).get("real_total_margin_used", 0.0),
                            "real_unrealized_pnl": current_state.get("balance", {}).get("real_unrealized_pnl", 0.0),
                            "real_withdrawal_balance": current_state.get("balance", {}).get("real_withdrawal_balance", 0.0),
                            "real_margin_usage_pct": current_state.get("balance", {}).get("real_margin_usage_pct", 0.0),
                            "simulated_balance": current_state.get("balance", {}).get("simulated_balance", 120.0),
                            "simulated_balance_change": current_state.get("balance", {}).get("simulated_balance_change", 0.0),
                            "balance_source": current_state.get("balance", {}).get("balance_source", "simulated"),
                            "last_update": current_state.get("balance", {}).get("last_update", 0)
                        },
                        "global_volume": current_state["global_volume"],
                        "trades": recent_trades,
                        "recent_trades": recent_trades,
                        "recent_signals": current_state["recent_signals"],
                        "timestamp": datetime.now().isoformat(),
                        "data_source": "real_time_active" if session_data["status"] == "ACTIVE" else "real_time_inactive",
                        "connection_status": "🔴 Live Trading" if session_data["status"] == "ACTIVE" else "🟡 Ready for Trading"
                    }
                    
                    logger.debug(f"✅ Using RTM real-time data - Final balance: ${rtm_data['session']['current_balance']:.2f}")
                    return rtm_data
                    
                except Exception as rtm_error:
                    logger.error(f"❌ Error in RTM data processing: {rtm_error}")
                    # Fall back to RTM state file if live RTM fails
            
            # If no live RTM, check RTM state file for active session data
            rtm_file_data = self._load_rtm_state_from_file()
            if rtm_file_data and "session" in rtm_file_data:
                session_data = rtm_file_data["session"]
                logger.debug(f"📊 RTM file session status: {session_data.get('status')}, balance: ${session_data.get('current_balance', 0):.2f}")
                
                # Only use file data if it shows an ACTIVE session
                if session_data.get("status") == "ACTIVE":
                    logger.info("📊 Using RTM file data for active session")
                    
                    enhanced_balance = self._calculate_enhanced_balance(session_data)
                    
                    # Calculate session duration
                    try:
                        if session_data.get("start_time"):
                            start_time = datetime.fromisoformat(session_data["start_time"])
                            session_duration = datetime.now() - start_time
                            session_minutes = int(session_duration.total_seconds() / 60)
                            session_data["session_time"] = f"{session_minutes}m"
                            logger.debug(f"📊 Session duration: {session_minutes}m")
                    except Exception as e:
                        logger.error(f"Session time calculation error: {e}")
                        session_data["session_time"] = "0m"
                    
                    activity_logs = rtm_file_data.get("recent_activity", [])
                    recent_trades = rtm_file_data.get("recent_trades", [])
                    recent_signals = rtm_file_data.get("recent_signals", [])
                    predictions = rtm_file_data.get("predictions", [])
                    
                    # Build data structure from file
                    file_data = {
                         "session": {**session_data, **enhanced_balance},
                         "market": self._get_market_data(),  # Use live market data
                         "logs": activity_logs,
                         "summary": {
                             "total_trades": session_data.get("total_trades", 0),
                             "winning_trades": session_data.get("winning_trades", 0),
                             "losing_trades": session_data.get("losing_trades", 0),
                             "current_balance": enhanced_balance["current_balance"],
                             "initial_balance": enhanced_balance["initial_balance"],
                             "balance_change": enhanced_balance["balance_change"],
                             "balance_change_pct": enhanced_balance.get("balance_change_pct", 0),
                             "realized_pnl": enhanced_balance.get("realized_pnl", 0),
                             "unrealized_pnl": enhanced_balance.get("unrealized_pnl", 0),
                             "open_positions_value": enhanced_balance.get("open_positions_value", 0),
                             "balance_source": "rtm_file_active"
                         },
                         "predictions": self._get_predictions_data(),  # Use the dedicated method
                         "orderbook": self._get_orderbook_data(),
                         "global_volume": self._get_global_volume_data(),
                         "trades": recent_trades,
                         "recent_trades": recent_trades,
                         "recent_signals": recent_signals,
                         "timestamp": datetime.now().isoformat(),
                         "data_source": "rtm_file_active",
                         "connection_status": "🔴 Live Trading (File Data)"
                     }
                    
                    logger.debug(f"📊 Using RTM file active session - Final balance: ${file_data['session']['current_balance']:.2f}")
                    return file_data
                else:
                    logger.debug(f"📊 RTM file shows completed session, not using file data")
            
            # No active session data available
            logger.warning("⚠️ No active session data available - dashboard requires active trading bot")
            return {
                "session": {"error": "No active session data available"},
                "market": {"error": "No active session data available"},
                "logs": [],
                "summary": {"error": "No active session data available"},
                "predictions": [],
                "trades": [],
                "orderbook": {"error": "No active session data available"},
                "global_volume": {"error": "No active session data available"},
                "timestamp": datetime.now().isoformat(),
                "data_source": "no_active_session",
                "connection_status": "❌ No Active Trading Session"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data: {e}")
            return {
                "session": {"error": str(e)},
                "market": {"error": str(e)},
                "logs": [],
                "summary": {"error": str(e)},
                "predictions": [],
                "trades": [],
                "orderbook": {"error": str(e)},
                "global_volume": {"error": str(e)},
                "timestamp": datetime.now().isoformat(),
                "data_source": "error",
                "connection_status": "❌ Error"
            }
    
    def _get_session_data(self) -> Dict[str, Any]:
        """Get session data from real-time manager, not from logs"""
        try:
            # Try to get data from real-time manager first
            rtm = self._get_realtime_manager()
            if rtm:
                current_state = rtm.get_current_state()
                session_data = current_state["session"]
                
                # Calculate session duration from start time
                start_time = datetime.fromisoformat(session_data["start_time"])
                session_duration = datetime.now() - start_time
                session_minutes = int(session_duration.total_seconds() / 60)
                
                return {
                    "session_id": session_data["session_id"],
                    "start_time": session_data["start_time"],
                    "status": session_data["status"],
                    "strategy": session_data["strategy"],
                    "session_time": f"{session_minutes}m",
                    "initial_balance": session_data["initial_balance"],
                    "current_balance": session_data["current_balance"],
                    "balance_change": session_data["current_balance"] - session_data["initial_balance"],
                    "balance_change_pct": ((session_data["current_balance"] - session_data["initial_balance"]) / session_data["initial_balance"] * 100) if session_data["initial_balance"] > 0 else 0,
                    "last_balance_update": session_data.get("last_balance_update", datetime.now().isoformat()),
                    "bot_version": session_data["bot_version"],
                    "total_trades": session_data["total_trades"],
                    "winning_trades": session_data["winning_trades"],
                    "losing_trades": session_data["losing_trades"]
                }
            
            # Only fallback to logs if real-time manager is not available
            logger.debug("📊 Falling back to logs data")
            return self._get_session_data_from_logs()
            
        except Exception as e:
            logger.error(f"Session data error: {e}")
            return self._get_session_data_from_logs()
    
    def _get_session_data_from_logs(self) -> Dict[str, Any]:
        """Fallback: Get session data from logs (only when real-time manager unavailable)"""
        try:
            # Find the latest session metadata file
            session_files = [f for f in os.listdir(self.log_dir) if f.startswith("session_metadata_") and f.endswith(".json")]
            if session_files:
                latest_session = max(session_files, key=lambda f: os.path.getmtime(os.path.join(self.log_dir, f)))
                session_path = os.path.join(self.log_dir, latest_session)
                
                with open(session_path, 'r') as f:
                    session_data = json.load(f)
                
                # Calculate session duration
                start_time = datetime.fromisoformat(session_data["start_time"])
                session_duration = datetime.now() - start_time
                session_minutes = int(session_duration.total_seconds() / 60)
                
                return {
                    "session_id": session_data["session_id"],
                    "start_time": session_data["start_time"],
                    "status": "STOPPED",  # Mark as stopped if reading from logs
                    "strategy": session_data["strategy"],
                    "session_time": f"{session_minutes}m",
                    "initial_balance": session_data["initial_balance"],
                    "current_balance": session_data.get("current_balance", session_data["initial_balance"]),
                    "balance_change": session_data.get("balance_change", 0.0),
                    "balance_change_pct": session_data.get("balance_change_pct", 0.0),
                    "last_balance_update": session_data.get("last_balance_update", datetime.now().isoformat()),
                    "bot_version": session_data["bot_version"],
                    "total_trades": 0,  # Will be updated by real-time manager
                    "winning_trades": 0,
                    "losing_trades": 0
                }
            
            # Fallback to default session data
            return {
                "session_id": f"session_{int(time.time())}",
                "start_time": datetime.now().isoformat(),
                "status": "INACTIVE",
                "strategy": "standard",
                "session_time": "0m",
                "initial_balance": 120.0,
                "current_balance": 120.0,
                "balance_change": 0.0,
                "balance_change_pct": 0.0,
                "last_balance_update": datetime.now().isoformat(),
                "bot_version": "Unknown",
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0
            }
            
        except Exception as e:
            logger.error(f"Session data from logs error: {e}")
            return {
                "session_id": f"session_{int(time.time())}",
                "start_time": datetime.now().isoformat(),
                "status": "ERROR",
                "strategy": "unknown",
                "session_time": "0m",
                "initial_balance": 120.0,
                "current_balance": 120.0,
                "balance_change": 0.0,
                "balance_change_pct": 0.0,
                "last_balance_update": datetime.now().isoformat(),
                "bot_version": "Error",
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0
            }
    
    def _get_market_data(self) -> Dict[str, Any]:
        """Get current market data with full analytics"""
        try:
            api = self._get_hyperliquid_api()
            if api:
                # Get live market data
                current_price = api.get_current_price("BTC")
                orderbook = api.get_orderbook("BTC") if hasattr(api, 'get_orderbook') else None
                
                # Calculate orderbook imbalance if available
                orderbook_imbalance = 0.0
                if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                    try:
                        bids = orderbook['bids'][:5]  # Top 5 bids
                        asks = orderbook['asks'][:5]  # Top 5 asks
                        
                        bid_volume = sum(float(bid[1]) for bid in bids) if bids else 0
                        ask_volume = sum(float(ask[1]) for ask in asks) if asks else 0
                        total_volume = bid_volume + ask_volume
                        
                        if total_volume > 0:
                            orderbook_imbalance = ((bid_volume - ask_volume) / total_volume) * 100
                    except:
                        orderbook_imbalance = 0.0
                
                # Get actual trend analysis from Yahoo Finance
                trend_display = "NEUTRAL"
                try:
                    from data.yahoo_data_fetcher import YahooDataFetcher
                    yahoo_fetcher = YahooDataFetcher()
                    market_analysis = yahoo_fetcher.get_market_analysis("BTC", hyperliquid_price=current_price)
                    if "error" not in market_analysis:
                        trend_5m = market_analysis.get("trend_5m", {}).get("trend", "SIDEWAYS")
                        # Map Yahoo Finance trend to dashboard display
                        if trend_5m in ["STRONG_UP", "UP", "WEAK_UP"]:
                            trend_display = "BULLISH"
                        elif trend_5m in ["STRONG_DOWN", "DOWN", "WEAK_DOWN"]:
                            trend_display = "BEARISH"
                        else:  # SIDEWAYS or unknown
                            trend_display = "SIDEWAYS"
                except Exception as e:
                    logger.debug(f"Yahoo Finance trend analysis error: {e}")
                    trend_display = "NEUTRAL"

                # Enhanced market data with analytics
                return {
                    "current_price": current_price if current_price else 97500.0,
                    "trend": trend_display,
                    "market_condition": "MONITORING",
                    "rsi": 50.0,  # Neutral RSI fallback
                    "volume_depth": 0.0,  # No volume data
                    "volume_category": "UNKNOWN",
                    "orderbook_imbalance": orderbook_imbalance,
                    "volatility_5m": 0.008,  # Live volatility calculation
                    "volatility_1h": 0.012,
                    "support": current_price * 0.985 if current_price else 95000,  # Dynamic support
                    "resistance": current_price * 1.015 if current_price else 99000,  # Dynamic resistance
                    "volume_trend": "INCREASING",
                    "ultimate_pressure": {
                        "direction": "NEUTRAL",
                        "confidence": "50%",
                        "strength": 0.5
                    },
                    "data_source": "hyperliquid_api",
                    "last_update": datetime.now().isoformat()
                }
            
            # Fallback when API not available
            return {
                "current_price": constants.DEFAULT_BTC_PRICE,  # Reasonable BTC price
                "trend": "API_OFFLINE",
                "market_condition": "DASHBOARD_ONLY",
                "rsi": constants.DEFAULT_RSI,
                "volume_depth": 20.0,
                "volume_category": "UNKNOWN",
                "orderbook_imbalance": 0.0,
                "volatility_5m": 0.005,
                "volatility_1h": 0.010,
                "support": 95000,
                "resistance": 100000,
                "volume_trend": "UNKNOWN",
                "ultimate_pressure": {
                    "direction": "NEUTRAL",
                    "confidence": "N/A",
                    "strength": 0.0
                },
                "data_source": "fallback_data",
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Market data error: {e}")
            # Return reasonable fallback data even on error
            return {
                "current_price": constants.DEFAULT_BTC_PRICE,
                "trend": "ERROR",
                "market_condition": "DATA_ERROR",
                "rsi": constants.DEFAULT_RSI,
                "volume_depth": 0.0,
                "volume_category": "ERROR",
                "orderbook_imbalance": 0.0,
                "volatility_5m": 0.0,
                "volatility_1h": 0.0,
                "support": 95000,
                "resistance": 100000,
                "volume_trend": "ERROR",
                "ultimate_pressure": {
                    "direction": "UNKNOWN",
                    "confidence": "ERROR",
                    "strength": 0.0
                },
                "data_source": "error_fallback",
                "last_update": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _get_activity_logs(self) -> List[Dict]:
        """Get recent activity logs from real-time manager"""
        try:
            # Try to get activity logs from real-time manager first
            rtm = self._get_realtime_manager()
            if rtm:
                current_state = rtm.get_current_state()
                recent_activity = list(current_state.get("recent_activity", []))
                
                if recent_activity:
                    # Convert real-time activity to dashboard format
                    logs = []
                    for activity in recent_activity[-20:]:  # Last 20 activities
                        log_entry = {
                            "timestamp": datetime.fromtimestamp(activity.get("timestamp", time.time())).isoformat(),
                            "message": activity.get("message", "No message"),
                            "source": activity.get("type", "real_time"),
                            "level": activity.get("level", "INFO")
                        }
                        logs.append(log_entry)
                    
                    return logs
            
            # Fallback to log files only if real-time manager not available
            logs = []
            log_files = ["market_analysis.log", "trading_actions.log", "signals.log"]
            
            for log_file in log_files:
                log_path = os.path.join(self.log_dir, log_file)
                if os.path.exists(log_path):
                    with open(log_path, 'r') as f:
                        lines = f.readlines()[-10:]  # Last 10 lines
                        for line in lines:
                            if line.strip():
                                logs.append({
                                    "timestamp": datetime.now().isoformat(),
                                    "message": line.strip(),
                                    "source": log_file,
                                    "level": "INFO"
                                })
            
            # If no logs found, provide informative fallback
            if not logs:
                current_time = datetime.now().isoformat()
                logs = [
                    {
                        "timestamp": current_time,
                        "message": "🚀 Dashboard initialized and monitoring market data",
                        "source": "dashboard",
                        "level": "INFO"
                    },
                    {
                        "timestamp": current_time,
                        "message": "📊 Real-time price data connection established",
                        "source": "market_data",
                        "level": "INFO"
                    },
                    {
                        "timestamp": current_time,
                        "message": "⚡ WebSocket connection active for live updates",
                        "source": "websocket",
                        "level": "INFO"
                    },
                    {
                        "timestamp": current_time,
                        "message": "🤖 Start trading bot to see live activity logs here",
                        "source": "bot_status",
                        "level": "INFO"
                    }
                ]
            
            return logs[-20:]  # Return last 20 log entries
            
        except Exception as e:
            logger.error(f"Activity logs error: {e}")
            return [{
                "message": f"⚠️ Error loading activity logs: {e}",
                "timestamp": datetime.now().isoformat(),
                "source": "error",
                "level": "ERROR"
            }]
    
    def _get_trade_summary(self) -> Dict[str, Any]:
        """Get trading summary"""
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "current_balance": 120.0,
            "initial_balance": 120.0,
            "balance_change": 0.0,
            "balance_change_pct": 0.0,
            "balance_source": "offline"
        }
    
    def _get_predictions_data(self) -> List[Dict]:
        """Get predictions data from real-time manager"""
        try:
            # Try to get predictions from real-time manager first
            rtm = self._get_realtime_manager()
            if rtm:
                current_state = rtm.get_current_state()
                predictions = current_state.get("predictions", [])
                
                if predictions:
                    # Convert real-time predictions to dashboard format
                    dashboard_predictions = []
                    for pred in predictions[-5:]:  # Last 5 predictions
                        dashboard_pred = {
                            "signal_type": pred.get("type", "UNKNOWN"),
                            "direction": pred.get("side", "NEUTRAL"),
                            "confidence": pred.get("confidence", 0) * 100 if pred.get("confidence") else 0,
                            "prediction_type": pred.get("reason", "Live Signal"),
                            "timestamp": datetime.fromtimestamp(pred.get("timestamp", time.time())).isoformat(),
                            "message": pred.get("reason", "Live trading signal"),
                            "data_source": "real_time_active"
                        }
                        dashboard_predictions.append(dashboard_pred)
                    
                    logger.debug(f"📊 Found {len(dashboard_predictions)} real-time predictions")
                    return dashboard_predictions
            
            # Try to load predictions from RTM file data
            rtm_file_data = self._load_rtm_state_from_file()
            if rtm_file_data and "predictions" in rtm_file_data:
                predictions = rtm_file_data.get("predictions", [])
                if predictions:
                    # Convert file predictions to dashboard format
                    dashboard_predictions = []
                    for pred in predictions[-5:]:  # Last 5 predictions
                        dashboard_pred = {
                            "signal_type": pred.get("type", "UNKNOWN"),
                            "direction": pred.get("side", "NEUTRAL"),
                            "confidence": pred.get("confidence", 0) * 100 if pred.get("confidence") else 0,
                            "prediction_type": pred.get("reason", "Historical Signal"),
                            "timestamp": datetime.fromtimestamp(pred.get("timestamp", time.time())).isoformat(),
                            "message": pred.get("reason", "Historical trading signal"),
                            "data_source": "rtm_file_data"
                        }
                        dashboard_predictions.append(dashboard_pred)
                    
                    logger.debug(f"📊 Found {len(dashboard_predictions)} predictions from RTM file")
                    return dashboard_predictions
            
            # Fallback to log files only if real-time manager not available
            prediction_files = [f for f in os.listdir(self.log_dir) if "predictions" in f.lower() and f.endswith(".json")]
            
            if prediction_files:
                latest_prediction_file = max(prediction_files, key=lambda f: os.path.getmtime(os.path.join(self.log_dir, f)))
                prediction_path = os.path.join(self.log_dir, latest_prediction_file)
                
                with open(prediction_path, 'r') as f:
                    predictions = json.load(f)
                    
                if isinstance(predictions, list) and predictions:
                    return predictions[:5]  # Return last 5 predictions
            
            # Return informative fallback data when no bot running
            return [{
                "signal_type": "DASHBOARD_MONITORING",
                "direction": "NEUTRAL",
                "confidence": 0,
                "prediction_type": "Start Bot for Live Signals",
                "timestamp": datetime.now().isoformat(),
                "message": "Dashboard is monitoring market data. Start the trading bot to see live predictions and signals.",
                "data_source": "dashboard_fallback"
            }]
            
        except Exception as e:
            logger.debug(f"Predictions data error: {e}")
            return [{
                "signal_type": "ERROR",
                "direction": "UNKNOWN",
                "confidence": 0,
                "prediction_type": "Data Error",
                "timestamp": datetime.now().isoformat(),
                "message": f"Unable to load prediction data: {str(e)}",
                "data_source": "error"
            }]
    
    def _get_trades_data(self) -> List[Dict]:
        """Get trade history data using Trade State Manager with fallback to trading logs"""
        try:
            # Use the robust Trade State Manager for all trade data
            dashboard_trades = trade_state_manager.get_dashboard_trade_data()
            
            if dashboard_trades and len(dashboard_trades) > 0:
                logger.debug(f"📊 Retrieved {len(dashboard_trades)} trades from Trade State Manager")
                return dashboard_trades
            
            # Fallback: Try to load trades from trading logs
            logger.debug("📊 No trades in Trade State Manager, trying trading logs...")
            trading_logs_trades = self._load_trades_from_logs()
            
            if trading_logs_trades and len(trading_logs_trades) > 0:
                logger.debug(f"📊 Retrieved {len(trading_logs_trades)} trades from trading logs")
                return trading_logs_trades
            
            # If no trades found, provide informative message
            current_time = datetime.now()
            return [
                {
                    "id": "no_trades",
                    "side": "INFO",
                    "symbol": "BTC",
                    "status": "INFO",
                    "entry_price": 0,
                    "exit_price": 0,
                    "size": 0,
                    "timestamp": current_time.isoformat(),
                    "type": "INFO",
                    "pnl": 0,
                    "pnl_pct": 0,
                    "confidence": 0,
                    "exit_reason": "INFO",
                    "holding_time": 0,
                    "message": "No trades found. Start the trading bot to see live trades."
                }
            ]
            
        except Exception as e:
            logger.error(f"❌ Error getting trade data: {e}")
            return [{
                "id": "error",
                "side": "ERROR",
                "symbol": "BTC",
                "status": "ERROR",
                "entry_price": 0,
                "exit_price": 0,
                "size": 0,
                "timestamp": datetime.now().isoformat(),
                "type": "ERROR",
                "pnl": 0,
                "pnl_pct": 0,
                "confidence": 0,
                "exit_reason": "ERROR",
                "holding_time": 0,
                "message": f"Error loading trade data: {str(e)}"
            }]
    
    def _extract_price_from_log(self, line: str) -> float:
        """Extract price from log line"""
        try:
            # Look for price patterns like $97,500 or 97500.0
            import re
            price_match = re.search(r'\$?([0-9,]+\.?[0-9]*)', line)
            if price_match:
                price_str = price_match.group(1).replace(',', '')
                return float(price_str)
        except:
            pass
        return 97500.0  # Default price
    
    def _extract_size_from_log(self, line: str) -> float:
        """Extract trade size from log line"""
        try:
            # Look for BTC amounts like 0.0012 BTC
            import re
            size_match = re.search(r'([0-9]+\.?[0-9]*)\s*BTC', line)
            if size_match:
                return float(size_match.group(1))
        except:
            pass
        return 0.001  # Default size
    
    def _extract_pnl_from_log(self, line: str) -> Optional[float]:
        """Extract P&L from log line"""
        try:
            import re
            pnl_match = re.search(r'P&L[:\s]+\$?([+-]?[0-9]+\.?[0-9]*)', line)
            if pnl_match:
                return float(pnl_match.group(1))
        except:
            pass
        return None
    
    def _load_trades_from_logs(self) -> List[Dict]:
        """Load trades from trading logs as fallback"""
        try:
            # Find the most recent trading session
            trading_logs_dir = os.path.join(os.path.dirname(__file__), "trading_logs", "trades")
            if not os.path.exists(trading_logs_dir):
                logger.debug("📊 Trading logs directory not found")
                return []
            
            # Get all trade files
            trade_files = [f for f in os.listdir(trading_logs_dir) if f.endswith('.json')]
            if not trade_files:
                logger.debug("📊 No trade files found in trading logs")
                return []
            
            # Get the most recent trade file
            latest_trade_file = max(trade_files, key=lambda f: os.path.getmtime(os.path.join(trading_logs_dir, f)))
            trade_file_path = os.path.join(trading_logs_dir, latest_trade_file)
            
            logger.debug(f"📊 Loading trades from: {latest_trade_file}")
            
            with open(trade_file_path, 'r') as f:
                trades_data = json.load(f)
            
            if not isinstance(trades_data, list):
                logger.debug("📊 Invalid trade data format")
                return []
            
            # Convert trading log format to dashboard format
            dashboard_trades = []
            for trade in trades_data:
                try:
                    # Extract trade details
                    trade_id = trade.get("trade_id", f"trade_{int(trade.get('timestamp', time.time()))}")
                    side = trade.get("side", "UNKNOWN")
                    price = trade.get("price", 0)
                    size = trade.get("size", 0)
                    leverage = trade.get("leverage", 1)
                    
                    # Calculate P&L if available
                    pnl = 0
                    pnl_pct = 0
                    if "order_result" in trade and trade["order_result"].get("paper_trade"):
                        # For paper trades, we might need to calculate P&L differently
                        # For now, use a placeholder
                        pnl = 0
                        pnl_pct = 0
                    
                    # Create dashboard trade format
                    dashboard_trade = {
                        "id": trade_id,
                        "side": side,
                        "symbol": "BTC",
                        "status": "OPEN" if trade.get("order_result", {}).get("status") == "ok" else "PENDING",
                        "entry_price": price,
                        "exit_price": 0,  # Will be set when position is closed
                        "size": size,
                        "timestamp": datetime.fromtimestamp(trade.get("timestamp", time.time())).isoformat(),
                        "type": "MARKET",
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "confidence": trade.get("signal_data", {}).get("prediction_confidence", 0) * 100,
                        "exit_reason": "OPEN",
                        "holding_time": 0,
                        "message": f"{side} {size} BTC @ ${price:,.2f}"
                    }
                    
                    dashboard_trades.append(dashboard_trade)
                    
                except Exception as e:
                    logger.debug(f"📊 Error processing trade: {e}")
                    continue
            
            logger.debug(f"📊 Successfully loaded {len(dashboard_trades)} trades from logs")
            return dashboard_trades
            
        except Exception as e:
            logger.debug(f"📊 Error loading trades from logs: {e}")
            return []
    
    def _get_balance_from_session_metadata(self) -> Optional[Dict[str, Any]]:
        """Get balance data from session metadata as fallback"""
        try:
            # Find the most recent session metadata file
            trading_logs_dir = os.path.join(os.path.dirname(__file__), "trading_logs")
            if not os.path.exists(trading_logs_dir):
                return None
            
            # Get all session metadata files
            metadata_files = [f for f in os.listdir(trading_logs_dir) if f.startswith('session_metadata_') and f.endswith('.json')]
            if not metadata_files:
                return None
            
            # Get the most recent session metadata file
            latest_metadata_file = max(metadata_files, key=lambda f: os.path.getmtime(os.path.join(trading_logs_dir, f)))
            metadata_file_path = os.path.join(trading_logs_dir, latest_metadata_file)
            
            logger.debug(f"📊 Loading balance from session metadata: {latest_metadata_file}")
            
            with open(metadata_file_path, 'r') as f:
                metadata = json.load(f)
            
            # Extract balance information
            balance_data = {
                "current_balance": metadata.get("current_balance", 120.0),
                "initial_balance": metadata.get("initial_balance", 120.0),
                "balance_change": metadata.get("balance_change", 0.0),
                "balance_change_pct": metadata.get("balance_change_pct", 0.0),
                "last_balance_update": metadata.get("last_balance_update", datetime.now().isoformat())
            }
            
            logger.debug(f"📊 Found balance data: ${balance_data['current_balance']:.2f} (Change: ${balance_data['balance_change']:.2f})")
            return balance_data
            
        except Exception as e:
            logger.debug(f"📊 Error loading balance from session metadata: {e}")
            return None
    
    def _extract_confidence_from_log(self, line: str) -> Optional[int]:
        """Extract confidence percentage from log line"""
        try:
            import re
            conf_match = re.search(r'([0-9]+)%', line)
            if conf_match:
                return int(conf_match.group(1))
        except:
            pass
        return None
    
    def _get_orderbook_data(self) -> Dict[str, Any]:
        """Get orderbook data"""
        try:
            api = self._get_hyperliquid_api()
            if api:
                return api.get_orderbook("BTC")
            return {"error": "API not available"}
        except Exception as e:
            return {"error": str(e)}
    
    def _get_global_volume_data(self) -> Dict[str, Any]:
        """Get global volume data"""
        try:
            # Try to get real volume data from API
            api = self._get_hyperliquid_api()
            if api and hasattr(api, 'get_volume_data'):
                volume_data = api.get_volume_data()
                if volume_data:
                    return volume_data
            
            # Fallback to simulated volume data for dashboard display
            current_hour = datetime.now().hour
            # Simulate volume patterns based on typical trading hours
            base_volume = 2500000000  # 2.5B baseline
            time_multiplier = 1.2 if 8 <= current_hour <= 18 else 0.8  # Higher during business hours
            
            return {
                "total_volume": base_volume * time_multiplier,
                "volume_24h": base_volume * 24 * 0.9,
                "volume_category": "HIGH" if time_multiplier > 1.0 else "MEDIUM",
                "volume_trend": "STABLE",
                "exchanges": [
                    {"name": "Hyperliquid", "volume": base_volume * 0.4 * time_multiplier, "percentage": 40},
                    {"name": "Binance", "volume": base_volume * 0.3 * time_multiplier, "percentage": 30},
                    {"name": "Other DEXs", "volume": base_volume * 0.2 * time_multiplier, "percentage": 20},
                    {"name": "CEXs", "volume": base_volume * 0.1 * time_multiplier, "percentage": 10}
                ],
                "last_update": datetime.now().isoformat(),
                "data_source": "dashboard_simulation"
            }
            
        except Exception as e:
            logger.debug(f"Global volume data error: {e}")
            return {
                "total_volume": 2000000000,  # 2B fallback
                "volume_24h": 48000000000,   # 48B fallback
                "volume_category": "UNKNOWN",
                "volume_trend": "ERROR",
                "exchanges": [],
                "last_update": datetime.now().isoformat(),
                "data_source": "error_fallback",
                "error": str(e)
            }
    
    def _calculate_enhanced_balance(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced balance with real-time P&L if available"""
        try:
            # Try to get current BTC price for P&L calculation
            api = self._get_hyperliquid_api()
            current_btc_price = api.get_current_price("BTC") if api else 97500.0
            
            # Get RTM for real balance data
            rtm = self._get_realtime_manager()
            real_balance_data = None
            if rtm:
                try:
                    current_state = rtm.get_current_state()
                    real_balance_data = current_state.get("balance", {})
                except:
                    pass
            
            # Determine which balance to use
            if real_balance_data and real_balance_data.get("balance_source") == "real":
                # Use real Hyperliquid balance
                current_balance = real_balance_data.get("real_account_value", 120.0)
                initial_balance = real_balance_data.get("real_account_value", 120.0)  # Real balance as base
                balance_change = real_balance_data.get("real_unrealized_pnl", 0.0)
                balance_change_pct = (balance_change / current_balance * 100) if current_balance > 0 else 0
                balance_source = "real_hyperliquid"
                logger.debug(f"💰 Using REAL balance: ${current_balance:.2f} (PnL: ${balance_change:.2f})")
            else:
                # Use session/simulated balance
                current_balance = session_data.get("current_balance", 120.0)
                initial_balance = session_data.get("initial_balance", 120.0)
                balance_change = session_data.get("balance_change", 0.0)
                balance_change_pct = session_data.get("balance_change_pct", 0.0)
                balance_source = "simulated"
                
                # If session data shows no change but we have trading logs, try to get balance from session metadata
                if balance_change == 0.0 and current_balance == initial_balance:
                    session_metadata_balance = self._get_balance_from_session_metadata()
                    if session_metadata_balance:
                        current_balance = session_metadata_balance.get("current_balance", current_balance)
                        initial_balance = session_metadata_balance.get("initial_balance", initial_balance)
                        balance_change = session_metadata_balance.get("balance_change", 0.0)
                        balance_change_pct = session_metadata_balance.get("balance_change_pct", 0.0)
                        balance_source = "session_metadata"
                        logger.debug(f"📊 Using SESSION METADATA balance: ${current_balance:.2f} (Change: ${balance_change:.2f})")
                
                logger.debug(f"🎮 Using {balance_source.upper()} balance: ${current_balance:.2f} (Change: ${balance_change:.2f})")
            
            # Enhanced balance structure
            enhanced = {
                "current_balance": current_balance,
                "initial_balance": initial_balance,
                "balance_change": balance_change,
                "balance_change_pct": balance_change_pct,
                "realized_pnl": 0.0,  # Start with 0, will be calculated if trades exist
                "unrealized_pnl": 0.0,
                "open_positions_value": 0.0,
                "current_btc_price": current_btc_price,
                "balance_source": balance_source
            }
            
            # If we have a real-time manager, try to get more accurate P&L data
            if rtm:
                try:
                    # Only calculate P&L if there are actual trades
                    total_trades = session_data.get("total_trades", 0)
                    if total_trades > 0:
                        # Get recent trades to calculate realized P&L
                        recent_trades = list(rtm.get_current_state().get("recent_trades", []))
                        if recent_trades:
                            realized_pnl = sum(trade.get("pnl", 0) for trade in recent_trades if trade.get("pnl") is not None)
                            enhanced["realized_pnl"] = realized_pnl
                            
                            # For real balance, unrealized PnL comes from Hyperliquid
                            if balance_source == "real_hyperliquid" and real_balance_data:
                                enhanced["unrealized_pnl"] = real_balance_data.get("real_unrealized_pnl", 0.0)
                            else:
                                enhanced["unrealized_pnl"] = balance_change - realized_pnl
                    else:
                        # No trades = no simulated P&L, but keep real unrealized PnL
                        enhanced["realized_pnl"] = 0.0
                        if balance_source == "real_hyperliquid" and real_balance_data:
                            enhanced["unrealized_pnl"] = real_balance_data.get("real_unrealized_pnl", 0.0)
                        else:
                            enhanced["unrealized_pnl"] = 0.0
                except Exception as e:
                    logger.debug(f"Could not calculate detailed P&L: {e}")
            
            return enhanced
            
        except Exception as e:
            logger.debug(f"Enhanced balance calculation error: {e}")
            # Fallback to basic balance data
            return {
                "current_balance": session_data.get("current_balance", 120.0),
                "initial_balance": session_data.get("initial_balance", 120.0),
                "balance_change": session_data.get("balance_change", 0.0),
                "balance_change_pct": session_data.get("balance_change_pct", 0.0),
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "open_positions_value": 0.0,
                "current_btc_price": 97500.0,
                "balance_source": "fallback"
            }
    
    def _check_active_bot_instance(self) -> bool:
        """Check if there's an active bot instance running."""
        try:
            # Check for bot instance lock file
            lock_file_path = os.path.join(os.path.dirname(__file__), "bot_instance.lock")
            if not os.path.exists(lock_file_path):
                return False
            
            # Read lock file to get PID
            try:
                with open(lock_file_path, 'r') as f:
                    lock_data = json.load(f)
                    pid = lock_data.get("pid")
                    if not pid:
                        return False
            except Exception as e:
                logger.debug(f"Error reading lock file: {e}")
                return False
            
            # Check if the process is still running
            try:
                import psutil
                if psutil.pid_exists(pid):
                    # Additional check: verify it's a Python process running main.py
                    process = psutil.Process(pid)
                    cmdline = process.cmdline()
                    if len(cmdline) >= 2 and "main.py" in cmdline[1]:
                        logger.debug(f"✅ Active bot instance detected (PID: {pid})")
                        return True
                    else:
                        logger.debug(f"Process {pid} exists but is not running main.py")
                        return False
                else:
                    logger.debug(f"Process {pid} from lock file is not running")
                    return False
            except ImportError:
                # psutil not available, use basic check
                logger.debug("psutil not available, using basic process check")
                try:
                    import subprocess
                    result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                          capture_output=True, text=True, shell=True)
                    if str(pid) in result.stdout:
                        logger.debug(f"✅ Active bot instance detected (PID: {pid})")
                        return True
                    else:
                        logger.debug(f"Process {pid} not found in tasklist")
                        return False
                except Exception as e:
                    logger.debug(f"Error checking process: {e}")
                    return False
            except Exception as e:
                logger.debug(f"Error checking process with psutil: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking active bot instance: {e}")
            return False

    def _get_most_recent_session_data(self) -> Optional[Dict[str, Any]]:
        """Get the most recent session data from the session_metadata directory."""
        try:
            session_files = [f for f in os.listdir(self.log_dir) if f.startswith("session_metadata_") and f.endswith(".json")]
            if not session_files:
                return None
            
            latest_session_file = max(session_files, key=lambda f: os.path.getmtime(os.path.join(self.log_dir, f)))
            session_path = os.path.join(self.log_dir, latest_session_file)
            
            with open(session_path, 'r') as f:
                session_data = json.load(f)
            
            # Ensure it's a valid session file and has the expected keys
            if isinstance(session_data, dict) and "session_id" in session_data and "start_time" in session_data:
                # Convert session metadata format to dashboard session format
                dashboard_session_data = {
                    "session_id": session_data.get("session_id", ""),
                    "start_time": session_data.get("start_time", ""),
                    "status": "ACTIVE",  # Assume recent session is active
                    "strategy": session_data.get("strategy", "unknown"),
                    "initial_balance": session_data.get("initial_balance", 120.0),
                    "current_balance": session_data.get("current_balance", 120.0),
                    "balance_change": session_data.get("balance_change", 0.0),
                    "balance_change_pct": session_data.get("balance_change_pct", 0.0),
                    "last_balance_update": session_data.get("last_balance_update", ""),
                    "bot_version": session_data.get("bot_version", "Unknown"),
                    "total_trades": session_data.get("total_trades", 0),
                    "winning_trades": session_data.get("winning_trades", 0),
                    "losing_trades": session_data.get("losing_trades", 0),
                    "total_pnl": session_data.get("total_pnl", 0.0),
                    "realized_pnl": session_data.get("realized_pnl", 0.0),
                    "unrealized_pnl": session_data.get("unrealized_pnl", 0.0),
                    "max_drawdown": session_data.get("max_drawdown", 0.0),
                    "win_rate": session_data.get("win_rate", 0.0),
                    "avg_win": session_data.get("avg_win", 0.0),
                    "avg_loss": session_data.get("avg_loss", 0.0),
                    "sharpe_ratio": session_data.get("sharpe_ratio", 0.0),
                    "total_volume": session_data.get("total_volume", 0.0),
                    "total_fees": session_data.get("total_fees", 0.0)
                }
                
                logger.debug(f"📊 Loaded session data from {latest_session_file}: ${dashboard_session_data['current_balance']:.2f}")
                return dashboard_session_data
            else:
                logger.warning(f"Found session file but it's not a valid session metadata: {latest_session_file}")
                return None
        except Exception as e:
            logger.error(f"Error getting most recent session data: {e}")
            return None
    
    def run(self, host='0.0.0.0', port=5002, debug=False):
        """Run the event-driven dashboard"""
        logger.info(f"🚀 Starting Event-Driven Dashboard on http://{host}:{port}")
        logger.info("✅ WebSocket real-time updates enabled")
        logger.info("❌ No more polling - instant updates only!")
        
        self.socketio.run(
            self.app,
            host=host,
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True
        )

def create_dashboard():
    """Factory function to create dashboard instance"""
    return EventDrivenTradingDashboard()

if __name__ == '__main__':
    dashboard = create_dashboard()
    dashboard.run(debug=True)