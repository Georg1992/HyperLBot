#!/usr/bin/env python3
"""
Real-Time Event-Driven Trading Dashboard
WebSocket-based architecture for instant updates without polling
"""

import os
import json
import time
import threading
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
                from core.realtime_data_manager import RealTimeTradingDataManager
                self._rtm = RealTimeTradingDataManager()
                self._rtm_available = True
                logger.debug("✅ Connected to Real-Time Data Manager")
            except Exception as e:
                logger.debug(f"⚠️ RTM not available: {e}")
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
                        current_data = self._get_all_dashboard_data()
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
            data = self._get_all_dashboard_data()
            self.socketio.emit('initial_data', data, room=session_id)
            logger.info("📤 Sent initial data to new connection")
        except Exception as e:
            logger.error(f"❌ Failed to send initial data: {e}")
    
    def _send_all_data(self, session_id: str):
        """Send complete dashboard data to specific connection"""
        try:
            data = self._get_all_dashboard_data()
            self.socketio.emit('data_update', data, room=session_id)
            logger.info("📤 Sent complete data update")
        except Exception as e:
            logger.error(f"❌ Failed to send data update: {e}")
    
    def _emit_data_update(self, data: Dict):
        """Emit data update to all connected clients"""
        try:
            self.socketio.emit('data_update', data)
            logger.debug(f"📡 Pushed update to {len(self.active_connections)} clients")
        except Exception as e:
            logger.error(f"❌ Failed to emit data update: {e}")
    
    def _get_all_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        try:
            # Try real-time data first
            rtm = self._get_realtime_manager()
            if rtm:
                current_state = rtm.get_current_state()
                if current_state["session"]["status"] == "ACTIVE":
                    return {
                        "session": current_state["session"],
                        "market": current_state["market"],
                        "logs": current_state["recent_activity"],
                        "summary": {
                            "total_trades": current_state["session"]["total_trades"],
                            "winning_trades": current_state["session"]["winning_trades"],
                            "losing_trades": current_state["session"]["losing_trades"],
                            "current_balance": current_state["session"]["current_balance"],
                            "initial_balance": current_state["session"]["initial_balance"],
                            "balance_change": current_state["session"]["balance_change"],
                            "balance_change_pct": current_state["session"]["balance_change_pct"],
                            "balance_source": "real_time"
                        },
                        "predictions": current_state["predictions"],
                        "orderbook": self._get_orderbook_data(),
                        "global_volume": current_state["global_volume"],
                        "recent_trades": current_state["recent_trades"],
                        "recent_signals": current_state["recent_signals"],
                        "timestamp": datetime.now().isoformat(),
                        "data_source": "real_time",
                        "connection_status": "🔴 Live Trading"
                    }
            
            # Fallback to offline data
            return {
                "session": self._get_session_data(),
                "market": self._get_market_data(),
                "logs": self._get_activity_logs(),
                "summary": self._get_trade_summary(),
                "predictions": self._get_predictions_data(),
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
        """Get session data from logs"""
        try:
            session_files = [f for f in os.listdir(self.log_dir) if f.startswith("session_") and f.endswith(".json")]
            
            if not session_files:
                return {
                    "session_id": "no_sessions_yet", 
                    "status": "WAITING", 
                    "strategy": "No bot started yet",
                    "started_at": "",
                    "current_balance": 0,
                    "initial_balance": 0
                }
            
            latest_session = max(session_files)
            session_path = os.path.join(self.log_dir, latest_session)
            
            with open(session_path, 'r') as f:
                session_data = json.load(f)
                session_data["status"] = "STOPPED"
                return session_data
                
        except Exception as e:
            logger.debug(f"Session data error: {e}")
            return {
                "session_id": "error_session", 
                "status": "ERROR", 
                "strategy": "Error loading session"
            }
    
    def _get_market_data(self) -> Dict[str, Any]:
        """Get current market data"""
        try:
            api = self._get_hyperliquid_api()
            if api:
                # Get live market data
                current_price = api.get_current_price("BTC")
                orderbook = api.get_orderbook("BTC")
                
                return {
                    "current_price": current_price,
                    "trend": "LIVE_FETCH",
                    "market_condition": "MONITORING",
                    "rsi": 50.0,  # Default - real RSI comes from bot
                    "volume_depth": 0.0,  # Default - real volume comes from bot
                    "orderbook_imbalance": 0.0,
                    "volatility_5m": 0.0,
                    "volatility_1h": 0.0,
                    "support": 0,
                    "resistance": 0,
                    "volume_category": "MONITORING",
                    "volume_trend": "LIVE",
                    "data_source": "hyperliquid_live",
                    "last_update": datetime.now().isoformat()
                }
            
            # Fallback to default values
            return {
                "current_price": 0,
                "trend": "OFFLINE",
                "market_condition": "UNKNOWN",
                "rsi": 50.0,
                "volume_depth": 0.0,
                "data_source": "offline"
            }
            
        except Exception as e:
            logger.debug(f"Market data error: {e}")
            return {"error": str(e), "data_source": "error"}
    
    def _get_activity_logs(self) -> List[Dict]:
        """Get recent activity logs"""
        try:
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
                                    "source": log_file
                                })
            
            return logs[-20:]  # Return last 20 log entries
            
        except Exception as e:
            logger.debug(f"Activity logs error: {e}")
            return [{"message": f"Error loading logs: {e}", "timestamp": datetime.now().isoformat()}]
    
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
        """Get predictions data"""
        return []
    
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
        return {
            "total_volume": 0,
            "exchanges": [],
            "last_update": datetime.now().isoformat()
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

# Create dashboard instance
dashboard = EventDrivenTradingDashboard()
app = dashboard.app
socketio = dashboard.socketio

if __name__ == '__main__':
    dashboard.run(debug=True)