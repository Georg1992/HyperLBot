#!/usr/bin/env python3
"""
Optimized Trading Bot Dashboard - Professional & Clean
High-performance real-time trading dashboard with intelligent caching
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import urllib3
from flask import Flask, render_template, jsonify
from loguru import logger

# Suppress SSL warnings
urllib3.disable_warnings()

class OptimizedTradingDashboard:
    """Optimized dashboard with intelligent caching and clean architecture"""
    
    def __init__(self):
        self.log_dir = "trading_logs"
        
        # Professional caching system
        self._cache = {}
        self._cache_timeout = {
            "session": 10,     # Session data: 10 seconds
            "market": 5,       # Market data: 5 seconds  
            "orderbook": 2,    # Orderbook: 2 seconds (fast updates)
            "logs": 15,        # Logs: 15 seconds
            "predictions": 8,  # Predictions: 8 seconds
            "global_volume": 12 # Global volume: 12 seconds
        }
        
        # Connection management
        self._rtm = None  # Real-time data manager instance
        self._api = None  # Hyperliquid API instance
        self._rtm_available = None  # Cache availability check
        

        
        logger.info("🚀 Optimized Trading Dashboard initialized")
    
    def _get_realtime_manager(self):
        """Get real-time data manager with connection caching"""
        if self._rtm_available is False:
            return None
            
        if self._rtm is None:
            try:
                from core.realtime_data_manager import trading_data_manager
                self._rtm = trading_data_manager
                self._rtm_available = True
                logger.debug("✅ Real-time data manager connected")
            except ImportError:
                self._rtm_available = False
                logger.debug("❌ Real-time data manager not available")
                return None
        
        return self._rtm
    
    def _get_hyperliquid_api(self):
        """Get Hyperliquid API with connection caching"""
        if self._api is None:
            try:
                from core.hyperliquid_api import HyperliquidAPI
                self._api = HyperliquidAPI()
                logger.debug("✅ Hyperliquid API connected")
            except Exception as e:
                logger.debug(f"❌ Hyperliquid API connection failed: {e}")
                return None
        return self._api
    
    def _get_cached_or_fetch(self, cache_key: str, fetch_function) -> Any:
        """Intelligent caching system"""
        current_time = time.time()
        timeout = self._cache_timeout.get(cache_key, 10)
        
        # Check cache
        if cache_key in self._cache:
            cached_data, cache_time = self._cache[cache_key]
            if current_time - cache_time < timeout:
                logger.debug(f"💾 Using cached {cache_key} data")
                return cached_data
        
        # Fetch new data
        try:
            fresh_data = fetch_function()
            self._cache[cache_key] = (fresh_data, current_time)
            logger.debug(f"🔄 Cached fresh {cache_key} data")
            return fresh_data
        except Exception as e:
            logger.error(f"❌ Failed to fetch {cache_key}: {e}")
            # Return cached data if available, even if stale
            if cache_key in self._cache:
                cached_data, _ = self._cache[cache_key]
                logger.warning(f"⚠️ Using stale {cache_key} data due to fetch error")
                return cached_data
            return None
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get session data with caching"""
        def _fetch_session():
            # Try real-time manager first
            rtm = self._get_realtime_manager()
            if rtm:
                session_data = rtm.get_session_data()
                if session_data["status"] == "ACTIVE":
                    return session_data
            
            # Try log files
            if not os.path.exists(self.log_dir):
                return {"session_id": "no_sessions_yet", "status": "WAITING", "strategy": "No bot started yet"}
                
            session_files = [f for f in os.listdir(self.log_dir) if f.startswith("session_metadata_")]
            if not session_files:
                return {"session_id": "no_sessions_yet", "status": "WAITING", "strategy": "No bot started yet"}
                
            latest_session = max(session_files)
            session_path = os.path.join(self.log_dir, latest_session)
            
            with open(session_path, 'r') as f:
                session_data = json.load(f)
                session_data["status"] = "STOPPED"  # Mark as stopped since bot isn't running
                return session_data
        
        return self._get_cached_or_fetch("session", _fetch_session) or {
            "session_id": "error_session", "status": "ERROR", "strategy": "Error loading session"
        }
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get market data with caching"""
        def _fetch_market():
            # Try real-time manager first
            rtm = self._get_realtime_manager()
            if rtm:
                market_data = rtm.get_market_data()
                # Check if data is REAL (not placeholder defaults)
                if (market_data.get("last_update") and 
                    market_data.get("data_source") != "none" and
                    market_data.get("current_price", 0) > 0 and
                    market_data.get("rsi", 50) != 50.0):
                    logger.info("🔴 Using real-time trading data (verified as fresh)")
                    return market_data
                else:
                    logger.info("⚠️ RTM data is stale/placeholder - using live API calculation")
            
            # Try live price fetch with REAL RSI and volume calculations
            api = self._get_hyperliquid_api()
            if api:
                current_price = api.get_current_price("BTC")
                if current_price > 0:
                    # Calculate REAL RSI from Yahoo Finance data
                    real_rsi = 50.0  # Default fallback
                    real_volume = 0.0
                    volume_category = "OFFLINE"
                    orderbook_imbalance = 0.0
                    
                    try:
                        # Calculate IMMEDIATE accurate RSI using Yahoo historical + Hyperliquid current
                        from data.yahoo_data_fetcher import YahooDataFetcher
                        yahoo_fetcher = YahooDataFetcher()
                        
                        # Get recent 20 candles from Yahoo Finance
                        yahoo_candles = yahoo_fetcher.get_klines("BTC", "5m", 20)
                        if yahoo_candles and len(yahoo_candles) >= 15:
                            # Extract historical closes + add current Hyperliquid price
                            closes = [float(candle["close"]) for candle in yahoo_candles[-14:]]  # Last 14 historical
                            closes.append(current_price)  # Add current Hyperliquid price as latest
                            
                            # Calculate immediate accurate RSI
                            real_rsi = self._calculate_rsi_from_trades(closes, periods=14)
                            logger.info(f"🎯 IMMEDIATE accurate RSI: {real_rsi:.1f} (Yahoo historical + Hyperliquid current)")
                        
                        # Get REAL orderbook imbalance
                        market_data = api.get_market_data("BTC")
                        if market_data and "levels" in market_data:
                            bids = market_data['levels'][0][:10] if market_data['levels'][0] else []
                            asks = market_data['levels'][1][:10] if market_data['levels'][1] else []
                            
                            total_bid_volume = sum(float(bid['sz']) for bid in bids)
                            total_ask_volume = sum(float(ask['sz']) for ask in asks)
                            
                            if total_bid_volume + total_ask_volume > 0:
                                orderbook_imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
                                logger.info(f"📊 Calculated real orderbook imbalance: {orderbook_imbalance:.3f}")
                        
                        # Get REAL volume data  
                        volume_result = api.get_current_5m_volume("BTC")
                        if volume_result and not volume_result.get("error"):
                            real_volume = volume_result.get("current_volume", 0.0)
                            volume_category = volume_result.get("volume_category", "UNKNOWN")
                            logger.info(f"📈 Calculated real volume: {real_volume:.1f} BTC ({volume_category})")
                        
                    except Exception as e:
                        logger.debug(f"Real data calculation failed: {e}")
                    
                    return {
                        "current_price": current_price,
                        "hyperliquid_price": current_price,
                        "trend": "LIVE_FETCH",
                        "market_condition": "BOT_OFFLINE",
                        "last_update": datetime.now().isoformat(),
                        "rsi": real_rsi,  # REAL RSI calculation
                        "volume_depth": real_volume,  # REAL volume
                        "orderbook_imbalance": orderbook_imbalance,  # REAL imbalance
                        "volatility_5m": 0.0,
                        "volatility_1h": 0.0,
                        "support": 0.0,
                        "resistance": 0.0,
                        "volume_category": volume_category,
                        "volume_trend": "OFFLINE",
                        "data_source": "live_fetch_with_calculations"
                    }
            
            # Try analysis files
            if os.path.exists(self.log_dir):
                analysis_files = [f for f in os.listdir(self.log_dir) if f.startswith("analysis_")]
                if analysis_files:
                    latest_analysis = max(analysis_files)
                    analysis_path = os.path.join(self.log_dir, latest_analysis)
                    
                    with open(analysis_path, 'r') as f:
                        return json.load(f)
            
            # Final fallback
            return {
                "current_price": 0.0,
                "hyperliquid_price": 0.0,
                "trend": "OFFLINE",
                "market_condition": "BOT_NOT_RUNNING",
                "last_update": datetime.now().isoformat(),
                "data_source": "offline_status"
            }
        
        return self._get_cached_or_fetch("market", _fetch_market) or {
            "current_price": 0.0, "trend": "ERROR", "market_condition": "ERROR", "data_source": "error_fallback"
        }
    
    def get_orderbook_data(self) -> Dict[str, Any]:
        """Get orderbook with caching"""
        def _fetch_orderbook():
            api = self._get_hyperliquid_api()
            if api:
                orderbook = api.get_orderbook("BTC")  # Only takes symbol parameter
                if orderbook and not orderbook.get("error"):
                    return orderbook
            return {"error": "Orderbook unavailable"}
        
        return self._get_cached_or_fetch("orderbook", _fetch_orderbook) or {"error": "API unavailable"}
    
    def get_global_volume_data(self) -> Dict[str, Any]:
        """Get global volume with caching"""
        def _fetch_volume():
            # Try real-time manager first
            rtm = self._get_realtime_manager()
            if rtm:
                volume_data = rtm.get_current_state()["global_volume"]
                if volume_data["status"] != "unavailable":
                    return volume_data
            
            # Try live global volume
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
        
        return self._get_cached_or_fetch("global_volume", _fetch_volume) or {"error": "Volume fetch failed"}
    
    def get_predictions_data(self) -> List[Dict[str, Any]]:
        """Get predictions with caching"""
        def _fetch_predictions():
            rtm = self._get_realtime_manager()
            if rtm:
                predictions = rtm.get_current_state()["predictions"]
                if predictions:
                    return predictions
            return []
        
        return self._get_cached_or_fetch("predictions", _fetch_predictions) or []
    
    def get_activity_logs(self) -> List[Dict[str, Any]]:
        """Get activity logs with caching"""
        def _fetch_logs():
            rtm = self._get_realtime_manager()
            if rtm:
                activity = rtm.get_recent_activity(10)
                if activity:
                    return activity
            
            # Try log files
            if not os.path.exists(self.log_dir):
                return [{"datetime": datetime.now().isoformat(), "reason": "No logs - bot never started"}]
            
            log_files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
            if not log_files:
                return [{"datetime": datetime.now().isoformat(), "reason": "No activity logs found"}]
            
            latest_log = max(log_files, key=lambda f: os.path.getmtime(os.path.join(self.log_dir, f)))
            log_path = os.path.join(self.log_dir, latest_log)
            
            logs = []
            with open(log_path, 'r') as f:
                lines = f.readlines()[-20:]
                for line in lines:
                    if line.strip():
                        logs.append({"datetime": datetime.now().isoformat(), "reason": line.strip()})
            
            return logs[-10:] if logs else [{"datetime": datetime.now().isoformat(), "reason": "No recent activity"}]
        
        return self._get_cached_or_fetch("logs", _fetch_logs) or [{"datetime": datetime.now().isoformat(), "reason": "Error loading logs"}]
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """Get trading summary (from session data)"""
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
    

    
    def _calculate_rsi_from_trades(self, price_samples: List[float], periods: int = 14) -> float:
        """Calculate RSI from Hyperliquid trade-based price samples"""
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
            
            logger.debug(f"🎯 Trade-based RSI: {periods}-period, RSI={rsi:.1f}")
            return max(0.0, min(100.0, rsi))  # Clamp to 0-100
            
        except Exception as e:
            logger.error(f"❌ Trade-based RSI calculation error: {e}")
            return 50.0

    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        logger.info("🧹 Dashboard cache cleared")

# Global dashboard instance
dashboard = OptimizedTradingDashboard()

# Flask app with error handling
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False  # Preserve JSON key order

@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler"""
    logger.error(f"Dashboard error: {e}")
    return jsonify({"error": f"Dashboard error: {str(e)}"}), 500

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """Optimized status API - single comprehensive endpoint"""
    try:
        # Try real-time data first (most efficient)
        rtm = dashboard._get_realtime_manager()
        if rtm:
            current_state = rtm.get_current_state()
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
        
        # Bot offline - optimized data gathering
        session_data = dashboard.get_session_data()
        market_data = dashboard.get_market_data()
        
        return jsonify({
            "session": session_data,
            "market": market_data,
            "logs": dashboard.get_activity_logs(),
            "summary": dashboard.get_trade_summary(),
            "predictions": dashboard.get_predictions_data(),
            "orderbook": dashboard.get_orderbook_data(),
            "global_volume": dashboard.get_global_volume_data(),
            "timestamp": datetime.now().isoformat(),
            "data_source": "offline_optimized"
        })
        
    except Exception as e:
        logger.error(f"❌ Status API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/trades')
def get_trades():
    """Latest trades API"""
    try:
        rtm = dashboard._get_realtime_manager()
        if rtm:
            trades = rtm.get_recent_trades(10)
            if trades:
                return jsonify(trades)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/signals')
def get_signals():
    """Latest signals API"""
    try:
        rtm = dashboard._get_realtime_manager()
        if rtm:
            signals = rtm.get_recent_signals(8)
            if signals:
                return jsonify(signals)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    rtm = dashboard._get_realtime_manager()
    api = dashboard._get_hyperliquid_api()
    
    return jsonify({
        "status": "healthy",
        "realtime_manager": "connected" if rtm else "unavailable",
        "hyperliquid_api": "connected" if api else "unavailable",
        "cache_entries": len(dashboard._cache),
        "uptime": time.time(),
        "version": "Optimized Dashboard v1.0"
    })

@app.route('/api/cache/clear')
def clear_cache():
    """Clear dashboard cache"""
    dashboard.clear_cache()
    return jsonify({"message": "Cache cleared successfully"})

if __name__ == '__main__':
    logger.info("🚀 Starting Optimized Trading Bot Dashboard")
    logger.info("🌐 Available at: http://localhost:5000")
    logger.info("🎯 Endpoints: /api/status, /api/trades, /api/signals, /api/health")
    logger.info("💾 Intelligent caching: session(10s), market(5s), orderbook(2s)")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
