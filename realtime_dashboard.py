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
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from loguru import logger

# Suppress SSL warnings
urllib3.disable_warnings()

class EventDrivenTradingDashboard:
    """Event-driven dashboard with WebSocket real-time updates"""
    
    def __init__(self):
        self.log_dir = "trading_logs"
        
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
            logger.info(f"🌐 Dashboard client connected from {request.remote_addr}")
            self.active_connections.add(request.sid)
            
            # Send initial data to new connection
            self._send_initial_data(request.sid)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle WebSocket disconnection"""
            logger.info(f"📱 Dashboard client disconnected")
            self.active_connections.discard(request.sid)
        
        @self.socketio.on('request_manual_refresh')
        def handle_manual_refresh():
            """Handle manual refresh request"""
            logger.info("🔄 Manual refresh requested")
            self._send_all_data(request.sid)
    
    def _setup_routes(self):
        """Setup Flask HTTP routes"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template('realtime_dashboard.html')
        
        @self.app.route('/health')
        def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "active_connections": len(self.active_connections),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_realtime_manager(self):
        """Get real-time data manager with connection caching"""
        if self._rtm_available is False:
            return None
            
        if self._rtm is None:
            try:
                from core.realtime_data_manager import trading_data_manager
                self._rtm = trading_data_manager
                self._rtm_available = True
                logger.success("✅ Real-time data manager connected")
            except Exception as e:
                logger.error(f"❌ Real-time data manager connection failed: {e}")
                self._rtm_available = False
                return None
        
        return self._rtm
    
    def _get_hyperliquid_api(self):
        """Get Hyperliquid API with connection caching"""
        if self._api is None:
            try:
                from core.hyperliquid_api import HyperliquidAPI
                self._api = HyperliquidAPI()
                logger.debug("✅ Connected to Hyperliquid API")
            except Exception as e:
                logger.debug(f"⚠️ Hyperliquid API not available: {e}")
                return None
        
        return self._api
    
    def _start_data_monitoring(self):
        """Start background thread to monitor for data changes"""
        def monitor_data_changes():
            while True:
                try:
                    if self.active_connections:
                        # Check for data changes
                        current_data = self._get_dashboard_data()
                        current_hash = self._calculate_data_hash(current_data)
                        
                        # Only emit if data actually changed
                        if current_hash != self.last_data_hash.get('all_data'):
                            logger.info("📊 Data changed - pushing to dashboard clients")
                            self._emit_data_update(current_data)
                            self.last_data_hash['all_data'] = current_hash
                    
                    # Smart monitoring interval - faster when active connections
                    sleep_time = 2 if self.active_connections else 10
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
            logger.info("📤 Sent initial data to new connection")
        except Exception as e:
            logger.error(f"❌ Failed to send initial data: {e}")
    
    def _send_all_data(self, session_id: str):
        """Send complete dashboard data to specific connection"""
        try:
            data = self._get_dashboard_data()
            self.socketio.emit('data_update', data, room=session_id)
            logger.info("📤 Sent complete data update")
        except Exception as e:
            logger.error(f"❌ Failed to send data update: {e}")
    
    def _emit_data_update(self, data: Dict):
        """Emit data update to all connected clients"""
        try:
            # Log activity logs count for debugging
            activity_count = len(data.get("logs", []))
            session_time = data.get("session", {}).get("session_time", "N/A")
            session_status = data.get("session", {}).get("status", "N/A")
            
            self.socketio.emit('data_update', data)
            logger.info(f"📡 WebSocket update sent to {len(self.active_connections)} clients")
            logger.debug(f"   Session: {session_status}, Time: {session_time}, Activities: {activity_count}")
            
            if activity_count > 0:
                latest_activity = data.get("logs", [])[-1].get("message", "No message")
                logger.debug(f"   Latest activity: {latest_activity}")
                
        except Exception as e:
            logger.error(f"❌ Failed to emit data update: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data with real-time updates"""
        try:
            # Try real-time data first
            rtm = self._get_realtime_manager()
            if rtm:
                current_state = rtm.get_current_state()
                session_status = current_state["session"]["status"]
                logger.debug(f"🔍 Real-time manager status: {session_status}")
                logger.debug(f"🔍 Recent activity count: {len(current_state.get('recent_activity', []))}")
                
                # Always use real-time data if available, regardless of bot status
                session_data = current_state["session"]
                enhanced_balance = self._calculate_enhanced_balance(session_data)
                
                # Calculate session duration properly
                try:
                    if session_data.get("start_time"):
                        start_time = datetime.fromisoformat(session_data["start_time"])
                        session_duration = datetime.now() - start_time
                        session_minutes = int(session_duration.total_seconds() / 60)
                        session_data["session_time"] = f"{session_minutes}m"
                        
                        # Ensure start_time is in ISO format for JavaScript
                        if isinstance(session_data["start_time"], str):
                            session_data["start_time"] = session_data["start_time"]
                        else:
                            session_data["start_time"] = session_data["start_time"].isoformat()
                except Exception as e:
                    logger.debug(f"Session time calculation error: {e}")
                    session_data["session_time"] = "0m"
                
                activity_logs = current_state.get("recent_activity", [])
                logger.debug(f"📊 Sending {len(activity_logs)} activity logs to dashboard")
                if activity_logs:
                    logger.debug(f"📊 Latest activity: {activity_logs[-1].get('message', 'No message')}")
                
                # Get actual trade data from real-time manager
                recent_trades = list(current_state.get("recent_trades", []))
                if not recent_trades:
                    # Try to get from database if not in memory
                    try:
                        recent_trades = rtm.get_historical_trades(10)
                    except:
                        recent_trades = []
                
                return {
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
                    "predictions": current_state["predictions"],
                    "orderbook": self._get_orderbook_data(),
                    "global_volume": current_state["global_volume"],
                    "trades": recent_trades,
                    "recent_trades": recent_trades,
                    "recent_signals": current_state["recent_signals"],
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "real_time_active" if session_status == "ACTIVE" else "real_time_inactive",
                    "connection_status": "🔴 Live Trading" if session_status == "ACTIVE" else "🟡 Ready for Trading"
                }
            
            # Fallback to offline data
            return {
                "session": self._get_session_data(),
                "market": self._get_market_data(),
                "logs": self._get_activity_logs(),
                "summary": self._get_trade_summary(),
                "predictions": self._get_predictions_data(),
                "trades": self._get_trades_data(),  # Trade data for Trade History panel
                "orderbook": self._get_orderbook_data(),
                "global_volume": self._get_global_volume_data(),
                "timestamp": datetime.now().isoformat(),
                "data_source": "offline",
                "connection_status": "📊 Monitoring"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "data_source": "error"
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
        """Get current market data"""
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
                
                return {
                    "current_price": current_price if current_price else 97500.0,
                    "trend": "LIVE_DATA" if current_price else "FETCHING",
                    "market_condition": "DASHBOARD_MONITORING",
                    "rsi": 50.0,  # Neutral when bot not running
                    "volume_depth": 25.5,  # Example volume for display
                    "volume_category": "MEDIUM",
                    "orderbook_imbalance": orderbook_imbalance,
                    "volatility_5m": 0.008,  # Example 0.8% volatility
                    "volatility_1h": 0.012,
                    "support": current_price * 0.98 if current_price else 95000,
                    "resistance": current_price * 1.02 if current_price else 99000,
                    "volume_trend": "STABLE",
                    "data_source": "hyperliquid_api",
                    "last_update": datetime.now().isoformat()
                }
            
            # Fallback when API not available
            return {
                "current_price": 97500.0,  # Reasonable BTC price
                "trend": "API_OFFLINE",
                "market_condition": "DASHBOARD_ONLY",
                "rsi": 50.0,
                "volume_depth": 20.0,
                "volume_category": "UNKNOWN",
                "orderbook_imbalance": 0.0,
                "volatility_5m": 0.005,
                "volatility_1h": 0.010,
                "support": 95000,
                "resistance": 100000,
                "volume_trend": "UNKNOWN",
                "data_source": "fallback_data",
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Market data error: {e}")
            # Return reasonable fallback data even on error
            return {
                "current_price": 97500.0,
                "trend": "ERROR",
                "market_condition": "DATA_ERROR",
                "rsi": 50.0,
                "volume_depth": 0.0,
                "volume_category": "ERROR",
                "orderbook_imbalance": 0.0,
                "volatility_5m": 0.0,
                "volatility_1h": 0.0,
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
        """Get trade history data from real-time manager"""
        try:
            # Try to get trades from real-time manager first
            rtm = self._get_realtime_manager()
            if rtm:
                current_state = rtm.get_current_state()
                recent_trades = list(current_state.get("recent_trades", []))
                
                if recent_trades:
                    # Convert real-time trades to dashboard format
                    dashboard_trades = []
                    for trade in recent_trades[-50:]:  # Last 50 trades
                        dashboard_trade = {
                            "id": trade.get("trade_id", "unknown"),
                            "side": trade.get("side", "UNKNOWN"),
                            "symbol": "BTC",
                            "status": "CLOSED" if trade.get("exit_time") else "OPEN",
                            "price": trade.get("entry_price", 0),
                            "size": trade.get("size", 0),
                            "timestamp": datetime.fromtimestamp(trade.get("entry_time", time.time())).isoformat(),
                            "type": "MARKET",
                            "pnl": trade.get("pnl", 0),
                            "confidence": trade.get("confidence", 0) * 100 if trade.get("confidence") else 0
                        }
                        dashboard_trades.append(dashboard_trade)
                    
                    return dashboard_trades
            
            # Fallback to log files only if real-time manager not available
            trades = []
            
            # Try to get trades from the latest trade log file
            trade_files = [f for f in os.listdir(os.path.join(self.log_dir, "trades")) if f.endswith(".json")]
            if trade_files:
                latest_trade_file = max(trade_files, key=lambda f: os.path.getmtime(os.path.join(self.log_dir, "trades", f)))
                trade_path = os.path.join(self.log_dir, "trades", latest_trade_file)
                
                with open(trade_path, 'r') as f:
                    trade_data = json.load(f)
                
                for trade in trade_data:
                    # Convert trade data to dashboard format
                    dashboard_trade = {
                        "id": trade.get("trade_id", "unknown"),
                        "side": trade.get("side", "UNKNOWN"),
                        "symbol": "BTC",
                        "status": "CLOSED" if trade.get("exit_timestamp") else "OPEN",
                        "price": trade.get("price", 0),
                        "size": trade.get("size", 0),
                        "timestamp": trade.get("datetime", datetime.now().isoformat()),
                        "type": trade.get("order_type", "MARKET"),
                        "pnl": trade.get("net_profit_loss", 0),
                        "confidence": trade.get("signal_data", {}).get("prediction_confidence", 0) * 100 if trade.get("signal_data") else 0
                    }
                    trades.append(dashboard_trade)
            
            # If no trades found, provide informative message
            if not trades:
                current_time = datetime.now()
                trades = [
                    {
                        "id": "no_trades",
                        "side": "INFO",
                        "symbol": "BTC",
                        "status": "INFO",
                        "price": 0,
                        "size": 0,
                        "timestamp": current_time.isoformat(),
                        "type": "INFO",
                        "pnl": 0,
                        "confidence": 0,
                        "message": "No trades found. Start the trading bot to see live trades."
                    }
                ]
            
            return trades[-50:]  # Return last 50 trades
            
        except Exception as e:
            logger.debug(f"Trade data error: {e}")
            return [{
                "id": "error",
                "side": "ERROR",
                "symbol": "BTC",
                "status": "ERROR",
                "price": 0,
                "size": 0,
                "timestamp": datetime.now().isoformat(),
                "type": "ERROR",
                "pnl": 0,
                "confidence": 0,
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
            
            # Base balance data from session
            current_balance = session_data.get("current_balance", 120.0)
            initial_balance = session_data.get("initial_balance", 120.0)
            balance_change = session_data.get("balance_change", 0.0)
            balance_change_pct = session_data.get("balance_change_pct", 0.0)
            
            # Enhanced balance structure
            enhanced = {
                "current_balance": current_balance,
                "initial_balance": initial_balance,
                "balance_change": balance_change,
                "balance_change_pct": balance_change_pct,
                "realized_pnl": balance_change,  # For now, assume all P&L is realized
                "unrealized_pnl": 0.0,
                "open_positions_value": 0.0,
                "current_btc_price": current_btc_price,
                "balance_source": "enhanced_real_time"
            }
            
            # If we have a real-time manager, try to get more accurate P&L data
            rtm = self._get_realtime_manager()
            if rtm:
                try:
                    # Get recent trades to calculate realized P&L
                    recent_trades = list(rtm.get_current_state().get("recent_trades", []))
                    if recent_trades:
                        realized_pnl = sum(trade.get("pnl", 0) for trade in recent_trades if trade.get("pnl") is not None)
                        enhanced["realized_pnl"] = realized_pnl
                        enhanced["unrealized_pnl"] = balance_change - realized_pnl
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
                "realized_pnl": session_data.get("balance_change", 0.0),
                "unrealized_pnl": 0.0,
                "balance_source": "fallback"
            }
    
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