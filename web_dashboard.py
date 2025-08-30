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
import socket
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import urllib3
from flask import Flask, render_template, request, make_response
from flask_socketio import SocketIO, emit
from loguru import logger

# Import constants only
from core.constants import constants, magic_numbers, ui_constants

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
        
        # SimpleRTM is the single source of truth
        
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
    
    @staticmethod
    def is_dashboard_running(host='localhost', port=5002) -> bool:
        """Check if dashboard is already running and accessible"""
        # Try multiple host addresses since dashboard binds to 0.0.0.0
        test_hosts = ['localhost', '127.0.0.1', '0.0.0.0']
        
        for test_host in test_hosts:
            try:
                # Try to connect to the dashboard health endpoint
                response = requests.get(f'http://{test_host}:{port}/health', timeout=2)
                if response.status_code == 200:
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
        except Exception:
            # Port check failed, assume not running
            pass
        
        return False
    
    @staticmethod
    def wait_for_dashboard(host='localhost', port=5002, timeout=10) -> bool:
        """Wait for dashboard to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if EventDrivenTradingDashboard.is_dashboard_running(host, port):
                return True
            time.sleep(magic_numbers.DASHBOARD_SLEEP_INTERVAL)
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
                "timestamp": datetime.now().isoformat()
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
                'volume_category': data.get('market', {}).get('volume_category', 'UNKNOWN'),
                'balance': data.get('session', {}).get('current_balance', 0),
                'trades': data.get('session', {}).get('total_trades', 0),
                'session_id': data.get('session', {}).get('session_id', ''),
                'status': data.get('session', {}).get('status', ''),
                'session_time': data.get('session', {}).get('session_time', '0m'),
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
        """Get dashboard data from SimpleRTM - SINGLE SOURCE OF TRUTH"""
        try:
            # Use the global RTM instance - SINGLE SOURCE OF TRUTH
            from core.data.real_time_manager import simple_rtm
            
            # Check for stale sessions and auto-cleanup (less aggressive)
            # Only cleanup every 30 seconds to avoid interfering with fresh sessions
            if not hasattr(self, '_last_cleanup_time'):
                self._last_cleanup_time = 0
            
            current_time = time.time()
            if current_time - self._last_cleanup_time > 30:  # 30 second interval
                simple_rtm.auto_cleanup_stale_sessions()
                self._last_cleanup_time = current_time
            
            # Get ALL data from SimpleRTM - SINGLE SOURCE OF TRUTH
            rtm_data = simple_rtm.get_data()
            
            # Dashboard ONLY displays data - NO calculations
            session_data = rtm_data.get("session", {})
            
            # Format data for dashboard - RTM ONLY
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
                "market": rtm_data.get("market", {}),
                "logs": rtm_data.get("logs", []),
                "predictions": rtm_data.get("predictions", []),
                "trades": rtm_data.get("trades", []),
                "orderbook": {"bids": [], "asks": []},
                "global_volume": {"volume": 0.0},
                "timestamp": rtm_data.get("timestamp", ""),
                "data_source": "SimpleRTM - Single Source of Truth",
                "connection_status": "✅ Connected"
            }
            
            logger.debug(f"✅ Dashboard data from RTM - Balance: ${dashboard_data['session']['current_balance']:.2f}, Session: {dashboard_data['session']['session_id']}")
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
                "global_volume": {"error": str(e)},
                "timestamp": datetime.now().isoformat(),
                "data_source": "error",
                "connection_status": "❌ Error"
            }
    
    def run(self, host='0.0.0.0', port=5002, debug=False):
        """Run the event-driven dashboard"""
        try:
            logger.info(f"🚀 Starting Event-Driven Dashboard on http://{host}:{port}")
            logger.info("✅ WebSocket real-time updates enabled")
            logger.info("✅ SimpleRTM - Single source of truth")
            
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