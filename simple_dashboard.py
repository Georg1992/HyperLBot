#!/usr/bin/env python3
"""
Simple Trading Bot Dashboard - REAL DATA ONLY
No demo mode - always shows real trading data or proper offline status
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import requests
import urllib3
from flask import Flask, render_template, jsonify
from loguru import logger

# Suppress SSL warnings
urllib3.disable_warnings()

class SimpleBotDashboard:
    """Dashboard for monitoring trading bot - REAL DATA ONLY"""
    
    def __init__(self):
        self.log_dir = "trading_logs"
        self.latest_data_cache = {}
        self.cache_timeout = 5  # Cache for 5 seconds
        logger.info("🖥️ Dashboard initialized - Real data only, no demo mode")
    
    def get_session_data(self):
        """Get session data from logs or real-time manager"""
        try:
            # Try real-time data manager first
            try:
                from core.realtime_data_manager import trading_data_manager
                session_data = trading_data_manager.get_session_data()
                if session_data["status"] == "ACTIVE":
                    logger.info(f"🔴 Using real-time session: {session_data['session_id']}")
                    return session_data
            except ImportError:
                logger.debug("Real-time data manager not available")
            
            # Check for log files
            if not os.path.exists(self.log_dir):
                logger.info("No log directory - bot never started")
                return {"session_id": "no_sessions_yet", "status": "WAITING", "strategy": "No bot started yet"}
                
            session_files = [f for f in os.listdir(self.log_dir) if f.startswith("session_metadata_")]
            if not session_files:
                logger.info("No session files found - bot never started")
                return {"session_id": "no_sessions_yet", "status": "WAITING", "strategy": "No bot started yet"}
                
            latest_session = max(session_files)
            session_path = os.path.join(self.log_dir, latest_session)
            
            with open(session_path, 'r') as f:
                session_data = json.load(f)
                session_data["status"] = "STOPPED"  # Mark as stopped since bot isn't running
                logger.info(f"📄 Using last bot session: {session_data['session_id']}")
                return session_data
                
        except Exception as e:
            logger.error(f"Error reading session data: {e}")
            return {"session_id": "error_session", "status": "ERROR", "strategy": "Error loading session"}
    
    def get_market_status(self):
        """Get real market data - never demo"""
        try:
            # Try real-time data manager first
            try:
                from core.realtime_data_manager import trading_data_manager
                market_data = trading_data_manager.get_market_data()
                if market_data["last_update"]:
                    logger.info(f"🔴 Using real-time market data")
                    return market_data
            except ImportError:
                logger.debug("Real-time data manager not available")
            
            # Try to get live market data directly
            try:
                from core.hyperliquid_api import HyperliquidAPI
                api = HyperliquidAPI()
                current_price = api.get_current_price("BTC")
                
                if current_price > 0:
                    logger.info(f"💰 Fetched live BTC price: ${current_price:,.2f}")
                    return {
                        "current_price": current_price,
                        "hyperliquid_price": current_price,
                        "trend": "LIVE_FETCH",
                        "market_condition": "BOT_OFFLINE",
                        "last_update": datetime.now().isoformat(),
                        "rsi": 50.0,
                        "volume_depth": 0.0,
                        "orderbook_imbalance": 0.0,
                        "volatility_5m": 0.0,
                        "volatility_1h": 0.0,
                        "support": 0.0,
                        "resistance": 0.0,
                        "volume_category": "OFFLINE",
                        "volume_trend": "OFFLINE",
                        "data_source": "live_fetch_offline"
                    }
            except Exception as e:
                logger.debug(f"Live price fetch failed: {e}")
            
            # Check for analysis files in logs
            if os.path.exists(self.log_dir):
                analysis_files = [f for f in os.listdir(self.log_dir) if f.startswith("analysis_")]
                if analysis_files:
                    latest_analysis = max(analysis_files)
                    analysis_path = os.path.join(self.log_dir, latest_analysis)
                    
                    with open(analysis_path, 'r') as f:
                        market_data = json.load(f)
                        logger.info("📄 Using last session market data")
                        return market_data
            
            # Final fallback - offline status (not demo)
            logger.warning("No market data available - bot offline")
            return {
                "current_price": 0.0,
                "hyperliquid_price": 0.0,
                "trend": "OFFLINE",
                "market_condition": "BOT_NOT_RUNNING",
                "last_update": datetime.now().isoformat(),
                "data_source": "offline_status"
            }
            
        except Exception as e:
            logger.error(f"Error reading market status: {e}")
            return {
                "current_price": 0.0,
                "trend": "ERROR",
                "market_condition": "ERROR",
                "data_source": "error_fallback"
            }
    
    def get_latest_logs(self):
        """Get recent activity logs"""
        try:
            # Try real-time data manager
            try:
                from core.realtime_data_manager import trading_data_manager
                activity = trading_data_manager.get_recent_activity(10)
                if activity:
                    logger.info(f"🔴 Using real-time activity logs")
                    return activity
            except ImportError:
                pass
            
            # Check log files
            if not os.path.exists(self.log_dir):
                return [{"datetime": datetime.now().isoformat(), "reason": "No logs - bot never started"}]
            
            log_files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
            if not log_files:
                return [{"datetime": datetime.now().isoformat(), "reason": "No activity logs found"}]
            
            # Get latest log file
            latest_log = max(log_files, key=lambda f: os.path.getmtime(os.path.join(self.log_dir, f)))
            log_path = os.path.join(self.log_dir, latest_log)
            
            logs = []
            with open(log_path, 'r') as f:
                lines = f.readlines()[-20:]  # Last 20 lines
                for line in lines:
                    if line.strip():
                        logs.append({"datetime": datetime.now().isoformat(), "reason": line.strip()})
            
            return logs[-10:] if logs else [{"datetime": datetime.now().isoformat(), "reason": "No recent activity"}]
            
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return [{"datetime": datetime.now().isoformat(), "reason": f"Error loading logs: {e}"}]
    
    def get_trade_summary(self):
        """Get trading summary"""
        try:
            # Try real-time data manager
            try:
                from core.realtime_data_manager import trading_data_manager
                session = trading_data_manager.get_session_data()
                if session["status"] == "ACTIVE":
                    return {
                        "total_trades": session["total_trades"],
                        "winning_trades": session["winning_trades"],
                        "losing_trades": session["losing_trades"],
                        "current_balance": session["current_balance"],
                        "initial_balance": session["initial_balance"],
                        "balance_change": session["balance_change"],
                        "balance_change_pct": session["balance_change_pct"],
                        "balance_source": "real_time"
                    }
            except ImportError:
                pass
            
            # Get from session data
            session_data = self.get_session_data()
            return {
                "total_trades": session_data.get("total_trades", 0),
                "winning_trades": session_data.get("winning_trades", 0),
                "losing_trades": session_data.get("losing_trades", 0),
                "current_balance": session_data.get("current_balance", 120.0),
                "initial_balance": session_data.get("initial_balance", 120.0),
                "balance_change": session_data.get("balance_change", 0.0),
                "balance_change_pct": session_data.get("balance_change_pct", 0.0),
                "balance_source": "session_data"
            }
            
        except Exception as e:
            logger.error(f"Error getting trade summary: {e}")
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "current_balance": 120.0,
                "initial_balance": 120.0,
                "balance_change": 0.0,
                "balance_change_pct": 0.0,
                "balance_source": "error"
            }
    
    def get_latest_predictions(self):
        """Get latest predictions"""
        try:
            # Try real-time data manager
            try:
                from core.realtime_data_manager import trading_data_manager
                predictions = trading_data_manager.get_current_state()["predictions"]
                if predictions:
                    return predictions
            except ImportError:
                pass
            
            # No real predictions available
            return []
            
        except Exception as e:
            logger.error(f"Error getting predictions: {e}")
            return []
    
    def get_orderbook_data(self):
        """Get orderbook data from Hyperliquid"""
        try:
            from core.hyperliquid_api import HyperliquidAPI
            api = HyperliquidAPI()
            orderbook = api.get_orderbook("BTC", 15)
            
            if orderbook and not orderbook.get("error"):
                logger.info("🔴 Retrieved live Hyperliquid orderbook")
                return orderbook
            else:
                logger.warning("No Hyperliquid orderbook data available")
                return {"error": "Orderbook unavailable"}
                
        except Exception as e:
            logger.warning(f"Hyperliquid API unavailable: {e}")
            return {"error": "API unavailable"}
    
    def get_global_volume_data(self):
        """Get global volume data"""
        try:
            # Try real-time data manager
            try:
                from core.realtime_data_manager import trading_data_manager
                volume_data = trading_data_manager.get_current_state()["global_volume"]
                if volume_data["status"] != "unavailable":
                    return volume_data
            except ImportError:
                pass
            
            # Try to get live global volume
            try:
                from strategies.dynamic_stop_manager import GlobalVolumeAggregator
                aggregator = GlobalVolumeAggregator()
                volume_data = aggregator.get_realtime_global_volume()
                if volume_data and volume_data.get("global_volume_per_second", 0) > 0:
                    return volume_data
            except Exception as e:
                logger.debug(f"Global volume fetch failed: {e}")
            
            # Offline fallback
            return {
                "global_volume_per_second": 0.0,
                "volume_by_exchange": {},
                "coverage_ratio": 0.0,
                "successful_exchanges": 0,
                "total_exchanges": 6,
                "last_update": time.time(),
                "status": "offline",
                "data_source": "offline",
                "note": "Start trading bot for live global volume data"
            }
            
        except Exception as e:
            logger.error(f"Error getting global volume: {e}")
            return {"error": str(e)}

# Global dashboard instance
dashboard = SimpleBotDashboard()

# Flask app
app = Flask(__name__)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """API endpoint for dashboard data - REAL DATA ONLY, NO DEMO"""
    try:
        # Try real-time data first
        try:
            from core.realtime_data_manager import trading_data_manager
            current_state = trading_data_manager.get_current_state()
            
            # If bot is active, use real-time data
            if current_state["session"]["status"] == "ACTIVE":
                logger.info("🔴 Using real-time trading data")
                return jsonify({
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
                    "orderbook": dashboard.get_orderbook_data(),
                    "global_volume": current_state["global_volume"],
                    "recent_trades": current_state["recent_trades"],
                    "recent_signals": current_state["recent_signals"],
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "real_time"
                })
        except ImportError:
            logger.debug("Real-time data manager not available")
        
        # Bot is offline - get last session data with live market price
        try:
            from core.hyperliquid_api import HyperliquidAPI
            api = HyperliquidAPI()
            current_price = api.get_current_price("BTC")
            
            if current_price > 0:
                logger.info(f"💰 Fetching live market data for offline dashboard: ${current_price:,.2f}")
                
                live_market_data = {
                    "current_price": current_price,
                    "hyperliquid_price": current_price,
                    "trend": "LIVE_FETCH",
                    "market_condition": "BOT_OFFLINE",
                    "last_update": datetime.now().isoformat(),
                    "rsi": 50.0,
                    "volume_depth": 0.0,
                    "orderbook_imbalance": 0.0,
                    "volatility_5m": 0.0,
                    "volatility_1h": 0.0,
                    "support": 0.0,
                    "resistance": 0.0,
                    "volume_category": "OFFLINE",
                    "volume_trend": "OFFLINE",
                    "data_source": "live_fetch_offline"
                }
                
                # Get last bot session
                session_data = dashboard.get_session_data()
                if session_data.get("session_id") not in ["no_sessions_yet", "error_session"]:
                    session_data["status"] = "STOPPED"
                    session_data["bot_version"] = session_data.get("bot_version", "Trading Bot") + " (Stopped)"
                    logger.info(f"📄 Using last bot session: {session_data['session_id']}")
                
                return jsonify({
                    "session": session_data,
                    "market": live_market_data,
                    "logs": dashboard.get_latest_logs(),
                    "summary": dashboard.get_trade_summary(),
                    "predictions": dashboard.get_latest_predictions(),
                    "orderbook": dashboard.get_orderbook_data(),
                    "global_volume": dashboard.get_global_volume_data(),
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "live_fetch_offline"
                })
                
        except Exception as e:
            logger.warning(f"Live data fetch failed: {e}")
        
        # Final fallback - use log data
        session_data = dashboard.get_session_data()
        market_status = dashboard.get_market_status()
        latest_logs = dashboard.get_latest_logs()
        trade_summary = dashboard.get_trade_summary()
        latest_predictions = dashboard.get_latest_predictions()
        orderbook_data = dashboard.get_orderbook_data()
        global_volume_data = dashboard.get_global_volume_data()
        
        return jsonify({
            "session": session_data,
            "market": market_status,
            "logs": latest_logs,
            "summary": trade_summary,
            "predictions": latest_predictions,
            "orderbook": orderbook_data,
            "global_volume": global_volume_data,
            "timestamp": datetime.now().isoformat(),
            "data_source": "offline_fallback"
        })
    except Exception as e:
        logger.error(f"Error in status API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/trades')
def get_trades():
    """API endpoint for latest trades - real-time when available"""
    try:
        # Try real-time data first
        try:
            from core.realtime_data_manager import trading_data_manager
            trades = trading_data_manager.get_recent_trades(10)
            if trades:
                logger.info(f"🔴 Returning {len(trades)} real-time trades")
                return jsonify(trades)
        except ImportError:
            pass
        
        # No real trades available
        return jsonify([])
    except Exception as e:
        logger.error(f"Error in trades API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/signals')
def get_signals():
    """API endpoint for latest trading signals - real-time when available"""
    try:
        # Try real-time data first
        try:
            from core.realtime_data_manager import trading_data_manager
            signals = trading_data_manager.get_recent_signals(8)
            if signals:
                logger.info(f"🔴 Returning {len(signals)} real-time signals")
                return jsonify(signals)
        except ImportError:
            pass
        
        # No real signals available
        return jsonify([])
    except Exception as e:
        logger.error(f"Error in signals API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """API endpoint for latest activity logs"""
    try:
        return jsonify(dashboard.get_latest_logs())
    except Exception as e:
        logger.error(f"Error in logs API: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("🚀 Starting Trading Bot Dashboard - Real Data Only")
    logger.info("🌐 Dashboard will be available at: http://localhost:5000")
    logger.info("📊 Shows live data when bot running, last session when stopped")
    app.run(debug=False, host='0.0.0.0', port=5000)
