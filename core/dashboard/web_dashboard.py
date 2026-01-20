#!/usr/bin/env python3
"""
Real-Time Event-Driven Trading Dashboard
WebSocket-based architecture for instant updates without polling
"""

import json
import time
import threading
import socket
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import urllib3
from flask import Flask, render_template, request, make_response
from flask_socketio import SocketIO, emit
from loguru import logger

# Import constants only
from core.constants import constants, magic_numbers

# Suppress SSL warnings
urllib3.disable_warnings()

class EventDrivenTradingDashboard:
    """Event-driven dashboard with WebSocket real-time updates"""
    
    _global_instance = None
    
    def __init__(self):
        self.log_dir = constants.LOG_DIR
        
        # Flask app with SocketIO
        self.app = Flask(__name__, template_folder='templates')
        self.app.config['SECRET_KEY'] = 'trading_dashboard_secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        
        # Active connections tracking
        self.active_connections = set()
        
        # Data change tracking for smart updates
        self.last_data_hash = {}
        
        # DashboardService is the single source of truth
        
        # Force update counter for reliability
        self.force_update_counter = 0
        self.last_update_cycle = 0
        self._last_cleanup_time = 0
        
        # Setup WebSocket event handlers
        self._setup_websocket_handlers()
        
        # Setup Flask routes
        self._setup_routes()
        
        # Start background data monitoring
        self._start_data_monitoring()
        
        # Set global instance for instant updates
        EventDrivenTradingDashboard._global_instance = self
        
        logger.info("🚀 Event-Driven Trading Dashboard initialized with WebSocket support")
    
    @classmethod
    def get_global_instance(cls):
        """Get global dashboard instance for instant updates"""
        return cls._global_instance
    
    @staticmethod
    def is_dashboard_running(host='localhost', port=5002, log_detection=True) -> bool:
        """Check if dashboard is already running and accessible"""
        # Try multiple host addresses since dashboard binds to 0.0.0.0
        test_hosts = ['localhost', '127.0.0.1', '0.0.0.0']
        
        for test_host in test_hosts:
            try:
                # Try to connect to the dashboard health endpoint
                response = requests.get(f'http://{test_host}:{port}/health', timeout=2)
                if response.status_code == 200:
                    if log_detection:
                        logger.info(f"✅ Dashboard already running on {test_host}:{port}")
                    return True
            except requests.exceptions.RequestException:
                continue
        
        try:
            # Fallback: check if port is in use
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                logger.info(f"⚠️ Port {port} is in use, but dashboard may not be responding")
                return True
        except Exception as e:
            # Port check failed, assume not running
            logger.debug(f"Port check failed: {e}")
        
        return False
    
    @staticmethod
    def wait_for_dashboard(host='localhost', port=5002, timeout=10) -> bool:
        """Wait for dashboard to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Don't log detection here - this is just waiting for the new dashboard to start
            if EventDrivenTradingDashboard.is_dashboard_running(host, port, log_detection=False):
                return True
            time.sleep(magic_numbers.DASHBOARD_SLEEP_INTERVAL)
        return False
    
    @staticmethod
    def has_active_browser_connections(host='localhost', port=5002) -> bool:
        """Check if there are active browser connections to the dashboard"""
        try:
            # Try to get the health endpoint which includes active connections
            response = requests.get(f'http://{host}:{port}/health', timeout=2)
            if response.status_code == 200:
                health_data = response.json()
                active_connections = health_data['active_connections'] if 'active_connections' in health_data else 0
                logger.info(f"📊 Dashboard has {active_connections} active browser connections")
                return active_connections > 0
        except requests.exceptions.RequestException as e:
            logger.debug(f"Dashboard health check failed: {e}")
        return False
    
    def _setup_websocket_handlers(self):
        """Setup WebSocket connection handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle new WebSocket connection"""
            logger.info(f"🌐 Client connected ({len(self.active_connections) + 1} active)")
            self.active_connections.add(request.sid)
            
            # Clear cached data and send initial data
            self.last_data_hash.clear()
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
                "timestamp": datetime.now().isoformat(),
                "dashboard_url": f"http://{constants.DEFAULT_DASHBOARD_HOST}:{constants.DEFAULT_DASHBOARD_PORT}",
                "connection_status": "connected" if self.active_connections else "waiting_for_connections"
            }
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            "active_connections": len(self.active_connections),
            "has_browser_connections": len(self.active_connections) > 0,
            "last_update": datetime.now().isoformat(),
            "dashboard_url": f"http://{constants.DEFAULT_DASHBOARD_HOST}:{constants.DEFAULT_DASHBOARD_PORT}"
        }
    
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
                        if current_hash != (self.last_data_hash['all_data'] if 'all_data' in self.last_data_hash else None) or force_update:
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
            market_data = data['market'] if 'market' in data else {}
            trend_analysis = market_data['trend_analysis'] if 'trend_analysis' in market_data else {}
            session_data = data['session'] if 'session' in data else {}
            rsi_data = market_data['rsi'] if 'rsi' in market_data else {}
            
            hash_data = {
                'price': market_data['current_price'] if 'current_price' in market_data else 0,
                'rsi': rsi_data['rsi'] if 'rsi' in rsi_data else 0,
                'overall_trend': trend_analysis['overall_trend'] if 'overall_trend' in trend_analysis else None,
                'trading_volume_btc': market_data['trading_volume_btc'] if 'trading_volume_btc' in market_data else 0,
                'trading_volume_category': market_data['trading_volume_category'] if 'trading_volume_category' in market_data else None,
                'volatility_5m': market_data['volatility_5m'] if 'volatility_5m' in market_data else 0,
                'volatility_5m_category': market_data['volatility_5m_category'] if 'volatility_5m_category' in market_data else None,
                'pressure': market_data['pressure'] if 'pressure' in market_data else None,
                'pressure_confidence': market_data['pressure_confidence'] if 'pressure_confidence' in market_data else 0,
                'key_levels': len(market_data['key_levels']) if 'key_levels' in market_data else 0,
                'patterns': bool(market_data['patterns']) if 'patterns' in market_data else False,
                'balance': session_data['current_balance'] if 'current_balance' in session_data else 0,
                'trades': session_data['total_trades'] if 'total_trades' in session_data else 0,
                'session_id': session_data['session_id'] if 'session_id' in session_data else '',
                'status': session_data['status'] if 'status' in session_data else '',
                'session_time': session_data['session_time'] if 'session_time' in session_data else '0m',
                'timestamp': data['timestamp'] if 'timestamp' in data else ''
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
    
    def force_data_update(self):
        """Force immediate data update emission"""
        try:
            data = self._get_dashboard_data()
            self._emit_data_update(data)
            # Removed excessive debug log for force data update
        except Exception as e:
            logger.error(f"❌ Failed to force data update: {e}")
    
    def _get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data from DashboardService - NEW ARCHITECTURE"""
        try:
            # Use new factory function architecture instead of singleton pattern
            from core.services.dashboard_service import create_dashboard_service
            dashboard_service = create_dashboard_service()
            
            if not dashboard_service:
                logger.error("❌ Dashboard service not available")
                return self._get_error_data("Dashboard service not available")
            
            # Check for stale sessions and auto-cleanup
            current_time = time.time()
            if current_time - self._last_cleanup_time > 30:
                self._last_cleanup_time = current_time
            
            # Get ALL data from DashboardService - SINGLE SOURCE OF TRUTH
            dashboard_data = dashboard_service.get_data()
            
            # Dashboard ONLY displays data - NO calculations
            session_data = dashboard_data["session"] if "session" in dashboard_data else {}
            
            # Dashboard fetches its own chart data (frontend responsibility)
            candle_data = self._get_chart_data()
            
            # Extract AI system status and ML performance from market data
            market_data_dict = dashboard_data.get("market", {})
            ai_system_status = market_data_dict.get("ai_system_status", {})
            # Check both top-level and market dict for ml_performance
            ml_performance = dashboard_data.get("ml_performance") or market_data_dict.get("ml_performance", {})
            
            # Get prediction - CHECK MULTIPLE SOURCES (top-level, market.prediction, market.predictions list)
            prediction = None
            if "prediction" in dashboard_data and dashboard_data["prediction"]:
                prediction = dashboard_data["prediction"]
                pred_dir = prediction.get("direction", "N/A")
                pred_conf = prediction.get("confidence", "N/A")
                logger.info(f"📡 ✅ FOUND PREDICTION (top-level): dir={pred_dir} conf={pred_conf}")
            elif "prediction" in market_data_dict and market_data_dict["prediction"]:
                prediction = market_data_dict["prediction"]
                pred_dir = prediction.get("direction", "N/A")
                pred_conf = prediction.get("confidence", "N/A")
                logger.info(f"📡 ✅ FOUND PREDICTION (market_data_dict): dir={pred_dir} conf={pred_conf}")
            else:
                predictions_list = market_data_dict.get("predictions", [])
                if predictions_list:
                    prediction = predictions_list[-1]
                    pred_dir = prediction.get("direction", "N/A")
                    pred_conf = prediction.get("confidence", "N/A")
                    logger.info(f"📡 ✅ FOUND PREDICTION (predictions list): dir={pred_dir} conf={pred_conf}")
            
            # Format data for dashboard - DashboardService ONLY
            dashboard_data = {
                "session": {
                    "session_id": session_data.get("session_id", "no_session"),
                    "status": session_data.get("status", "INACTIVE"),
                    "strategy": session_data.get("strategy", "standard"),
                    "session_time": session_data.get("session_time", "0m"),  # Pre-calculated by SessionManager
                    "start_time": session_data.get("start_time"),
                    "current_balance": session_data.get("current_balance", 0.0),
                    "initial_balance": session_data.get("initial_balance", 0.0),
                    "total_pnl": session_data.get("total_pnl", 0.0),
                    "win_rate": session_data.get("win_rate", 0.0),
                    "total_trades": session_data.get("total_trades", 0)
                },
                "market": market_data_dict,
                "ai_system_status": ai_system_status,  # Add AI system status
                "ml_performance": ml_performance,  # Add ML performance data
                "logs": dashboard_data.get("logs", []),
                "predictions": [prediction] if prediction else [],  # Always a list for compatibility
                "prediction": prediction,  # Top-level prediction (single object) - THIS IS WHAT UI READS
                "trades": dashboard_data.get("trades", []),  # Includes pending orders, open positions, closed trades
                "orderbook": {"bids": [], "asks": []},
                "candleData": candle_data,  # Add candle data to dashboard data
                "timestamp": dashboard_data.get("timestamp", ""),
                "data_source": "DashboardService - Single Source of Truth",
                "connection_status": "✅ Connected"
            }
            
            # Dashboard data logging removed - was spamming every 2 seconds
            return dashboard_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data: {e}")
            return {
                "session": {
                    "session_id": "error",
                    "status": "ERROR", 
                    "session_time": "0s",
                    "error": str(e)
                },
                "market": {"error": str(e)},
                "logs": [],
                "predictions": [],
                "trades": [],
                "orderbook": {"error": str(e)},
                "timestamp": datetime.now().isoformat(),
                "data_source": "error",
                "connection_status": "❌ Error"
            }
    
    def _get_chart_data(self) -> Dict[str, Any]:
        """Dashboard fetches its own chart data (frontend responsibility)"""
        try:
            from core.services.historical_data_service import create_historical_data_service
            from core.services.system_initializer import get_system_initializer
            
            # Get market data service from system initializer (it has the APIs)
            system_initializer = get_system_initializer()
            market_data_service = system_initializer.singleton_systems.get("market_data_service")
            
            if not market_data_service:
                logger.error("❌ Market data service not available for chart data")
                return {}
            
            # Get current price from market data service
            current_price = market_data_service.get_current_price()
            if not current_price or current_price <= 0:
                logger.warning("⚠️ No current price available, using default")
                current_price = 50000.0
            
            # Use new factory function for historical data service
            historical_service = create_historical_data_service()
            
            # Get pattern data from MarketDataService to include in chart
            pattern_data = market_data_service.get_pattern_analysis() if market_data_service else {}
            
            # NO FALLBACKS - prepare_chart_data raises on error
            chart_data = historical_service.prepare_chart_data(current_price, pattern_data)
            return chart_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get chart data: {e}")
            # Re-raise to fail fast - NO FALLBACKS
            raise
    
    def _get_error_data(self, error_message: str) -> Dict[str, Any]:
        """Get error data structure for dashboard"""
        return {
            "session": {
                "session_id": "error",
                "status": "ERROR", 
                "session_time": "0s",
                "error": error_message
            },
            "market": {"error": error_message},
            "logs": [],
            "predictions": [],
            "trades": [],
            "orderbook": {"error": error_message},
            "global_volume": {"error": error_message},
            "timestamp": datetime.now().isoformat(),
            "data_source": "error",
            "connection_status": "❌ Error"
        }
    
    
    def run(self, host='0.0.0.0', port=5002, debug=False):
        """Run the event-driven dashboard"""
        try:
            logger.info(f"🚀 Starting Event-Driven Dashboard on http://{host}:{port}")
            logger.info("✅ WebSocket real-time updates enabled")
            logger.info("✅ DashboardService - Single source of truth")
            
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=debug,
                allow_unsafe_werkzeug=True
            )
        except OSError as e:
            if "Address already in use" in str(e):
                logger.warning(f"⚠️ Port {port} is already in use. Dashboard may already be running.")
                logger.info(f"💡 Dashboard should be available at: http://{host}:{port}")
                logger.info("💡 If you need to restart, please stop the existing dashboard first.")
            else:
                raise e

def create_dashboard():
    """Factory function to create dashboard instance"""
    return EventDrivenTradingDashboard()

if __name__ == '__main__':
    dashboard = create_dashboard()
    dashboard.run(debug=True)