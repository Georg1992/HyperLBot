#!/usr/bin/env python3
"""
Simple HyperLBot Dashboard
Updates data on demand instead of background threads
"""

import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify
from loguru import logger

app = Flask(__name__)

class SimpleBotDashboard:
    def __init__(self):
        # Use standardized log directory
        self.log_dir = "trading_logs"
        
    def get_session_data(self):
        """Get session data from logs"""
        try:
            if not os.path.exists(self.log_dir):
                logger.warning("Log directory does not exist")
                return {}
                
            session_files = [f for f in os.listdir(self.log_dir) if f.startswith("session_metadata_")]
            if not session_files:
                logger.warning("No session metadata files found")
                return {}
                
            latest_session = max(session_files)
            session_path = os.path.join(self.log_dir, latest_session)
            
            with open(session_path, 'r') as f:
                session_data = json.load(f)
                logger.info(f"Session data loaded: {session_data.get('session_id', 'Unknown')}")
                return session_data
                
        except Exception as e:
            logger.error(f"Error reading session data: {e}")
            return {}
    
    def get_market_status(self):
        """Get market status from analysis logs"""
        try:
            analysis_dir = os.path.join(self.log_dir, "analysis")
            
            if not os.path.exists(analysis_dir):
                logger.warning("Analysis directory does not exist")
                return {
                    "current_price": 0.0,
                    "trend": "UNKNOWN",
                    "market_condition": "UNKNOWN",
                    "last_update": "Never"
                }
            
            analysis_files = [f for f in os.listdir(analysis_dir) if f.endswith('.json')]
            if not analysis_files:
                logger.warning("No analysis files found")
                return {
                    "current_price": 0.0,
                    "trend": "UNKNOWN",
                    "market_condition": "UNKNOWN",
                    "last_update": "Never"
                }
            
            latest_analysis = max(analysis_files)
            analysis_path = os.path.join(analysis_dir, latest_analysis)
            
            with open(analysis_path, 'r') as f:
                analysis_data = json.load(f)
                if analysis_data and len(analysis_data) > 0:
                    # Find the latest entry with actual market data (check both hybrid_analysis_update and prediction_analysis)
                    latest_market = None
                    latest_prediction = None
                    
                    for entry in reversed(analysis_data):
                        if entry.get("analysis_type") == "hybrid_analysis_update" and entry.get("trend_analysis"):
                            if not latest_market:
                                latest_market = entry
                            # Prioritize entries with volume_data
                            elif entry.get("volume_data") and not latest_market.get("volume_data"):
                                latest_market = entry
                        if entry.get("analysis_type") == "prediction_analysis" and entry.get("has_prediction") and not latest_prediction:
                            latest_prediction = entry
                     
                    # Also look for entries with volume_data specifically
                    latest_volume_entry = None
                    for entry in reversed(analysis_data):
                        if entry.get("volume_data"):
                            latest_volume_entry = entry
                            break
                    
                    # Use market data entry for basic info, prediction entry for RSI/volume
                    base_entry = latest_market or latest_prediction
                    
                    if base_entry:
                        # Basic market data
                        trend_analysis = base_entry.get("trend_analysis", {})
                        current_price = base_entry.get("hyperliquid_price", 0.0)
                        trend = trend_analysis.get("trend", "UNKNOWN")
                        market_condition = base_entry.get("market_condition", "UNKNOWN")
                        last_update = base_entry.get("datetime", "Never")
                        
                        # Get price information
                        hyperliquid_price = base_entry.get("hyperliquid_price", 0.0)
                        yahoo_last_close = base_entry.get("yahoo_last_close", 0.0)
                        price_diff_pct = base_entry.get("price_difference_pct", 0.0)
                        price_diff_amount = base_entry.get("price_difference_amount", 0.0)
                        data_source = base_entry.get("data_source", "Unknown")
                        
                        # Get live RSI and volume data using our new integration
                        rsi_data = None
                        volume_data = None
                        orderbook_imbalance = None
                        
                        try:
                            # Import and get live data
                            from core.config import TradingConfig
                            from core.hyperliquid_api import HyperliquidAPI
                            
                            config = TradingConfig()
                            api = HyperliquidAPI(config.WALLET_ADDRESS, config.WALLET_PRIVATE_KEY)
                            
                            # Get REAL-TIME price from Hyperliquid (not from logs)
                            try:
                                real_time_price = api.get_current_price("BTC")
                                if real_time_price:
                                    # Use real-time price instead of log price
                                    current_price = real_time_price
                                    hyperliquid_price = real_time_price
                                    
                                    logger.info(f"📈 Real-time Hyperliquid price: ${real_time_price:,.2f}")
                                else:
                                    logger.warning("Could not get real-time price from Hyperliquid")
                            except Exception as price_error:
                                logger.warning(f"Could not get real-time price: {price_error}")
                                # Fallback to log price
                            
                                                       # Get RSI and volume from bot's cached data (updated every 5 seconds)
                           # This is more efficient than fetching Yahoo data every 2 seconds
                            if latest_prediction and latest_prediction.get("best_prediction"):
                                best_pred = latest_prediction["best_prediction"]
                                rsi_data = best_pred.get("rsi_context", 0)
                                
                                # ENHANCED: Get volume data with spike detection
                                volume_data_obj = best_pred.get("volume_data", {})
                                volume_data = volume_data_obj.get("current_volume", 0)
                                volume_category = volume_data_obj.get("volume_category", "UNKNOWN")
                                has_spike = volume_data_obj.get("has_spike", False)
                                spike_severity = volume_data_obj.get("spike_severity", "NORMAL")
                                is_immediate_spike = volume_data_obj.get("is_immediate_spike", False)
                                spike_reason = volume_data_obj.get("spike_reason", "")
                                volume_source = volume_data_obj.get("volume_source", "unknown")
                                
                                # ENHANCED: Handle volume display with fallback
                                if volume_data == 0 and volume_source == "no_data":
                                    # Try to get volume from other sources
                                    try:
                                        from data.yahoo_data_fetcher import YahooDataFetcher
                                        fetcher = YahooDataFetcher()
                                        realtime_volume = fetcher.get_realtime_volume("BTC")
                                        if "error" not in realtime_volume:
                                            volume_data = realtime_volume.get("estimated_current_volume", 0)
                                            volume_source = realtime_volume.get("volume_source", "fallback")
                                            has_spike = realtime_volume.get("is_immediate_spike", False)
                                            spike_reason = realtime_volume.get("spike_reason", "")
                                    except Exception as e:
                                        logger.warning(f"Volume fallback failed: {e}")
                                
                                orderbook_imbalance = best_pred.get("orderbook_imbalance", 0)
                                
                                logger.info(f"📊 Using cached data - Volume: {volume_data:.1f}, RSI: {rsi_data:.1f}, Source: {volume_source}")
                            else:
                                 # Check if volume data is available in any entry
                                 if latest_volume_entry and latest_volume_entry.get("volume_data"):
                                     volume_info = latest_volume_entry.get("volume_data", {})
                                     volume_data = volume_info.get("current_volume", 0)
                                     volume_category = volume_info.get("volume_category", "UNKNOWN")
                                     has_spike = volume_info.get("has_spike", False)
                                     spike_severity = volume_info.get("spike_severity", "NORMAL")
                                     is_immediate_spike = volume_info.get("is_immediate_spike", False)
                                     spike_reason = volume_info.get("spike_reason", "")
                                     volume_source = volume_info.get("volume_source", "hybrid_analysis")
                                     
                                     logger.info(f"📊 Using volume data from {latest_volume_entry.get('analysis_type', 'unknown')} - Volume: {volume_data:.1f}, RSI: {rsi_data:.1f}, Source: {volume_source}")
                                 elif latest_market and latest_market.get("volume_data"):
                                     volume_info = latest_market.get("volume_data", {})
                                     volume_data = volume_info.get("current_volume", 0)
                                     volume_category = volume_info.get("volume_category", "UNKNOWN")
                                     has_spike = volume_info.get("has_spike", False)
                                     spike_severity = volume_info.get("spike_severity", "NORMAL")
                                     is_immediate_spike = volume_info.get("is_immediate_spike", False)
                                     spike_reason = volume_info.get("spike_reason", "")
                                     volume_source = volume_info.get("volume_source", "hybrid_analysis")
                                     
                                     logger.info(f"📊 Using hybrid analysis data - Volume: {volume_data:.1f}, RSI: {rsi_data:.1f}, Source: {volume_source}")
                                 else:
                                    # Fallback to Yahoo data if no cached data available
                                    from data.yahoo_data_fetcher import YahooDataFetcher
                                    fetcher = YahooDataFetcher()
                                    logger.debug("📊 Fetching Yahoo data as fallback...")
                                    candles = fetcher.get_klines("BTC", "5m", 30)
                                    
                                    if candles and len(candles) >= 25:
                                        rsi_result = api.calculate_rsi_from_yahoo_data(candles, periods=20)
                                        rsi_data = rsi_result.get("rsi", 0)
                                        
                                        volume_result = api.get_current_5m_volume("BTC")
                                        volume_data = volume_result.get("current_volume", 0)
                                        volume_category = volume_result.get("volume_category", "UNKNOWN")
                                        has_spike = volume_result.get("has_spike", False)
                                        spike_severity = volume_result.get("spike_severity", "NORMAL")
                                        is_immediate_spike = volume_result.get("is_immediate_spike", False)
                                        spike_reason = volume_result.get("spike_reason", "")
                                        volume_source = volume_result.get("volume_source", "fallback")
                                        
                                        indicators = api.get_current_market_indicators("BTC")
                                        orderbook_imbalance = 0
                                        if indicators and "liquidity_metrics" in indicators:
                                            liquidity = indicators["liquidity_metrics"]
                                            orderbook_imbalance = liquidity.get("depth_imbalance", 0)
                                        
                                        logger.info(f"📊 Fallback data - Volume: {volume_data:.1f}, RSI: {rsi_data:.1f}")
                                    else:
                                        rsi_data = 0
                                        volume_data = 0
                                        volume_category = "UNKNOWN"
                                        has_spike = False
                                        spike_severity = "NORMAL"
                                        is_immediate_spike = False
                                        spike_reason = ""
                                        volume_source = "no_data"
                                        orderbook_imbalance = 0
                                        logger.warning("Insufficient candle data for fallback calculation")
                                    
                        except Exception as e:
                            logger.warning(f"Could not get live market data: {e}")
                            # Fallback to log data
                            if latest_prediction and latest_prediction.get("best_prediction"):
                                best_pred = latest_prediction["best_prediction"]
                                rsi_data = best_pred.get("rsi_context")
                                
                                # Get volume data from prediction's volume_data field
                                volume_info = best_pred.get("volume_data", {})
                                volume_data = volume_info.get("current_volume", 0)
                                volume_category = volume_info.get("volume_category", "UNKNOWN")
                                has_spike = volume_info.get("has_spike", False)
                                spike_severity = volume_info.get("spike_severity", "NORMAL")
                                is_immediate_spike = volume_info.get("is_immediate_spike", False)
                                spike_reason = volume_info.get("spike_reason", "")
                                volume_source = volume_info.get("volume_source", "log_fallback")
                                # NEW: Real-time volume data fields (fallback)
                                cumulative_5m_volume = volume_info.get("cumulative_5m_volume", 0)
                                volume_trend = volume_info.get("volume_trend", "UNKNOWN")
                                sources_used = volume_info.get("sources_used", [])
                                
                                orderbook_imbalance = best_pred.get("orderbook_imbalance")
                            elif latest_market and latest_market.get("volume_data"):
                                # Fallback to volume data from hybrid_analysis_update entries
                                volume_info = latest_market.get("volume_data", {})
                                volume_data = volume_info.get("current_volume", 0)
                                volume_category = volume_info.get("volume_category", "UNKNOWN")
                                has_spike = volume_info.get("has_spike", False)
                                spike_severity = volume_info.get("spike_severity", "NORMAL")
                                is_immediate_spike = volume_info.get("is_immediate_spike", False)
                                spike_reason = volume_info.get("spike_reason", "")
                                volume_source = volume_info.get("volume_source", "hybrid_analysis_fallback")
                                # NEW: Real-time volume data fields (fallback)
                                cumulative_5m_volume = volume_info.get("cumulative_5m_volume", 0)
                                volume_trend = volume_info.get("volume_trend", "UNKNOWN")
                                sources_used = volume_info.get("sources_used", [])
                                
                                logger.info(f"📊 Using hybrid analysis fallback - Volume: {volume_data:.1f}, Source: {volume_source}")
                            else:
                                # Final fallback - no volume data available
                                volume_data = 0
                                volume_category = "UNKNOWN"
                                has_spike = False
                                spike_severity = "NORMAL"
                                is_immediate_spike = False
                                spike_reason = ""
                                volume_source = "no_data"
                                # NEW: Real-time volume data fields (final fallback)
                                cumulative_5m_volume = 0
                                volume_trend = "UNKNOWN"
                                sources_used = []
                                logger.warning("No volume data available in any log entries")
                        
                        # Update last_update to reflect real-time data
                        last_update = datetime.now().isoformat()
                        
                        logger.info(f"Market data: ${current_price} - {trend} - {market_condition} - RSI: {rsi_data} - Volume: {volume_data}")
                        
                        return {
                            "current_price": current_price,
                            "trend": trend,
                            "market_condition": market_condition,
                            "last_update": last_update,
                            "hyperliquid_price": hyperliquid_price,
                            "yahoo_last_close": yahoo_last_close,
                            "price_difference_pct": price_diff_pct,
                            "price_difference_amount": price_diff_amount,
                            "data_source": data_source,
                            "rsi": rsi_data,
                            "volume_depth": volume_data,
                            "orderbook_imbalance": orderbook_imbalance,
                            # ENHANCED: Volume spike detection data
                            "volume_category": volume_category,
                            "has_volume_spike": has_spike,
                            "spike_severity": spike_severity,
                            "is_immediate_spike": is_immediate_spike,
                            "spike_reason": spike_reason,
                            "volume_source": volume_source,
                            # NEW: Real-time volume data fields
                            "cumulative_5m_volume": cumulative_5m_volume if 'cumulative_5m_volume' in locals() else 0,
                            "volume_trend": volume_trend if 'volume_trend' in locals() else "UNKNOWN",
                            "sources_used": sources_used if 'sources_used' in locals() else []
                        }
                    else:
                        logger.warning("No valid market data found in analysis")
                        
        except Exception as e:
            logger.error(f"Error reading market status: {e}")
            
        return {
            "current_price": 0.0,
            "trend": "UNKNOWN",
            "market_condition": "UNKNOWN",
            "last_update": "Never"
        }
    
    def get_latest_logs(self):
        """Get latest logs from all log files"""
        try:
            logs = []
            
            # Check trades
            trades_dir = os.path.join(self.log_dir, "trades")
            if os.path.exists(trades_dir):
                trade_files = [f for f in os.listdir(trades_dir) if f.endswith('.json')]
                if trade_files:
                    latest_trades = max(trade_files)
                    trades_path = os.path.join(trades_dir, latest_trades)
                    with open(trades_path, 'r') as f:
                        trades = json.load(f)
                        if trades:
                            logs.extend(trades[-5:])  # Last 5 trades
            
            # Check signals
            signals_dir = os.path.join(self.log_dir, "signals")
            if os.path.exists(signals_dir):
                signal_files = [f for f in os.listdir(signals_dir) if f.endswith('.json')]
                if signal_files:
                    latest_signals = max(signal_files)
                    signals_path = os.path.join(signals_dir, latest_signals)
                    with open(signals_path, 'r') as f:
                        signals = json.load(f)
                        if signals:
                            logs.extend(signals[-3:])  # Last 3 signals
                            
            return logs
                            
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return []
    
    def get_trade_summary(self):
        """Get trading summary"""
        try:
            # Get session data to show actual balance
            session_data = self.get_session_data()
            initial_balance = session_data.get("initial_balance", 1000.0)
            
            # For now, return default values with actual balance
            # This could be enhanced to calculate from actual trade data
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "current_balance": initial_balance
            }
        except Exception as e:
            logger.error(f"Error getting trade summary: {e}")
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "current_balance": 1000.0
            }
    
    def get_latest_predictions(self):
        """Get latest predictions from analysis logs"""
        try:
            analysis_dir = os.path.join(self.log_dir, "analysis")
            
            if not os.path.exists(analysis_dir):
                return []
            
            analysis_files = [f for f in os.listdir(analysis_dir) if f.endswith('.json')]
            if not analysis_files:
                return []
            
            latest_analysis = max(analysis_files)
            analysis_path = os.path.join(analysis_dir, latest_analysis)
            
            with open(analysis_path, 'r') as f:
                analysis_data = json.load(f)
                if analysis_data and len(analysis_data) > 0:
                    # Find the latest entry with predictions
                    latest = None
                    for entry in reversed(analysis_data):
                        if entry.get("analysis_type") == "prediction_analysis" and entry.get("has_prediction"):
                            latest = entry
                            break
                    
                    if latest and latest.get("has_prediction"):
                        # Only return the best prediction (highest confidence)
                        if latest.get("best_prediction"):
                            return [latest.get("best_prediction")]
                        # Fallback to first prediction if best_prediction not available
                        elif latest.get("all_predictions"):
                            all_predictions = latest.get("all_predictions", [])
                            if all_predictions:
                                # Select the prediction with highest confidence
                                best_prediction = max(all_predictions, key=lambda x: x.get("confidence", 0))
                                return [best_prediction]
            
            return []
            
        except Exception as e:
            logger.error(f"Error reading predictions: {e}")
            return []
    
    def get_orderbook_data(self):
        """Get current orderbook data for display"""
        try:
            # We need to import the trading bot to access Hyperliquid API
            from strategies.hybrid_paper_trading_bot import YahooHyperliquidPaperTradingBot
            from core.config import TradingConfig
            
            config = TradingConfig()
            from core.hyperliquid_api import HyperliquidAPI
            api = HyperliquidAPI(config.WALLET_ADDRESS, config.WALLET_PRIVATE_KEY)
            
            market_data = api.get_market_data("BTC")
            
            if market_data and 'levels' in market_data:
                bids = market_data['levels'][0][:15]  # Top 15 bid levels
                asks = market_data['levels'][1][:15]  # Top 15 ask levels
                
                # Calculate running totals
                bid_total = 0
                ask_total = 0
                
                processed_bids = []
                for bid in bids:
                    bid_total += float(bid['sz'])
                    processed_bids.append({
                        'price': float(bid['px']),
                        'size': float(bid['sz']),
                        'total': bid_total
                    })
                
                processed_asks = []
                for ask in asks:
                    ask_total += float(ask['sz'])
                    processed_asks.append({
                        'price': float(ask['px']),
                        'size': float(ask['sz']),
                        'total': ask_total
                    })
                
                # Calculate spread
                best_bid = float(bids[0]['px']) if bids else 0
                best_ask = float(asks[0]['px']) if asks else 0
                spread = best_ask - best_bid
                spread_pct = (spread / best_ask * 100) if best_ask > 0 else 0
                
                return {
                    "bids": processed_bids,
                    "asks": processed_asks,
                    "spread": spread,
                    "spread_pct": spread_pct,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "timestamp": time.time()
                }
            else:
                return {"error": "No orderbook data available"}
                
        except Exception as e:
            logger.error(f"Error getting orderbook data: {e}")
            return {"error": str(e)}

# Global dashboard instance
dashboard = SimpleBotDashboard()

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        return f"""
        <html>
        <head><title>HyperLBot Dashboard</title></head>
        <body>
            <h1>🤖 HyperLBot Dashboard</h1>
            <p>Error loading dashboard: {e}</p>
            <p>Please check the console for more details.</p>
        </body>
        </html>
        """

@app.route('/api/status')
def get_status():
    """API endpoint for dashboard data"""
    try:
        session_data = dashboard.get_session_data()
        market_status = dashboard.get_market_status()
        latest_logs = dashboard.get_latest_logs()
        trade_summary = dashboard.get_trade_summary()
        latest_predictions = dashboard.get_latest_predictions()
        orderbook_data = dashboard.get_orderbook_data()
        
        return jsonify({
            "session": session_data,
            "market": market_status,
            "logs": latest_logs,
            "summary": trade_summary,
            "predictions": latest_predictions,
            "orderbook": orderbook_data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in status API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/data')
def get_data():
    """API endpoint for dashboard data (alias for status)"""
    return get_status()

@app.route('/api/logs')
def get_logs():
    """API endpoint for latest logs"""
    try:
        return jsonify(dashboard.get_latest_logs())
    except Exception as e:
        logger.error(f"Error in logs API: {e}")
        return jsonify({"error": str(e)}), 500

def create_template():
    """Create the HTML template file"""
    try:
        # Create templates directory
        os.makedirs('templates', exist_ok=True)
        
        # Create the HTML template
        html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HyperLBot Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #ffffff;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: #2d2d2d;
            border-radius: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: #2d2d2d;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #4CAF50;
        }
        .card h3 {
            margin-top: 0;
            color: #4CAF50;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background: #4CAF50; }
        .status-stopped { background: #f44336; }
        .status-warning { background: #ff9800; }
        .log-entry {
            background: #1a1a1a;
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 3px solid #4CAF50;
            font-family: monospace;
            font-size: 12px;
        }
        .trade-entry {
            border-left-color: #2196F3;
        }
        .signal-entry {
            border-left-color: #FF9800;
        }
        .refresh-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px 0;
        }
        .refresh-btn:hover {
            background: #45a049;
        }
        .price {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }
        .trend-up { color: #4CAF50; }
        .trend-down { color: #f44336; }
        .trend-neutral { color: #ff9800; }
        .warning { color: #ff9800; font-weight: bold; }
        
        /* Predictions Panel Styles */
        .predictions-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .prediction-card {
            background: #1a1a1a;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #4CAF50;
            font-family: monospace;
            font-size: 12px;
        }
        .prediction-buy {
            border-left-color: #4CAF50;
        }
        .prediction-sell {
            border-left-color: #f44336;
        }
        .high-confidence {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
        }
        .medium-confidence {
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            box-shadow: 0 2px 8px rgba(255, 152, 0, 0.3);
        }
        .low-confidence {
            background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%);
            box-shadow: 0 2px 8px rgba(244, 67, 54, 0.3);
        }
        .prediction-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #333;
        }
        .prediction-type {
            font-weight: bold;
            color: #4CAF50;
            font-size: 11px;
            text-transform: uppercase;
        }
        .prediction-side {
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            text-transform: uppercase;
        }
        .prediction-buy .prediction-side {
            background: #4CAF50;
            color: white;
        }
        .prediction-sell .prediction-side {
            background: #f44336;
            color: white;
        }
        .prediction-details p {
            margin: 5px 0;
            line-height: 1.4;
        }
        .prediction-details strong {
            color: #4CAF50;
        }
        
        /* Market Indicators - RSI and Volume Display */
        .market-indicator {
            background: rgba(76, 175, 80, 0.1);
            border-radius: 6px;
            padding: 8px;
            margin: 8px 0;
            border-left: 3px solid #4CAF50;
        }
        
        .rsi-indicator {
            border-left-color: #2196F3;
            background: rgba(33, 150, 243, 0.1);
        }
        
        .volume-indicator {
            border-left-color: #FF9800;
            background: rgba(255, 152, 0, 0.1);
        }
        
        /* RSI Status Colors */
        .rsi-value.overbought {
            color: #f44336;
            font-weight: bold;
            font-size: 14px;
        }
        
        .rsi-value.oversold {
            color: #4CAF50;
            font-weight: bold;
            font-size: 14px;
        }
        
        .rsi-value.neutral {
            color: #2196F3;
            font-weight: bold;
            font-size: 14px;
        }
        
        .rsi-status {
            font-size: 11px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 3px;
            margin-left: 5px;
        }
        
        .rsi-status.overbought {
            background: #f44336;
            color: white;
        }
        
        .rsi-status.oversold {
            background: #4CAF50;
            color: white;
        }
        
        .rsi-status.neutral {
            background: #2196F3;
            color: white;
        }
        
        /* Volume/Order Flow Colors */
        .volume-value {
            color: #FF9800;
            font-weight: bold;
            font-size: 14px;
        }
        
        /* Volume Spike Indicators */
        .volume-value.volume-spike {
            color: #e74c3c;
            animation: pulse 1s infinite;
        }
        
        .spike-indicator {
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 8px;
            font-size: 0.8em;
        }
        
        .spike-indicator.high {
            background-color: #e74c3c;
            color: white;
        }
        
        .spike-indicator.extreme {
            background-color: #8e44ad;
            color: white;
            animation: pulse 0.5s infinite;
        }
        
        .spike-indicator.moderate {
            background-color: #f39c12;
            color: white;
        }
        
                 .spike-indicator.mild {
             background-color: #f1c40f;
             color: #2c3e50;
         }
         
         .spike-indicator.normal {
             background-color: #27ae60;
             color: white;
         }
        
        .immediate-spike {
            background-color: #e67e22;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 4px;
            font-size: 0.7em;
            font-weight: bold;
        }
        
        .spike-reason {
            background-color: #ecf0f1;
            padding: 8px;
            border-radius: 4px;
            margin: 5px 0;
            font-size: 0.9em;
            border-left: 3px solid #e74c3c;
        }
        
        .volume-category {
            color: #7f8c8d;
            font-size: 0.8em;
            margin-left: 8px;
        }
        
        .volume-source {
            color: #95a5a6;
            font-size: 0.7em;
            margin-top: 5px;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .order-flow.bullish {
            color: #4CAF50;
            font-weight: bold;
        }
        
        .order-flow.bearish {
            color: #f44336;
            font-weight: bold;
        }
        
        .order-flow.neutral {
            color: #2196F3;
            font-weight: bold;
        }
        
        /* Orderbook Panel Styles */
        .orderbook-container {
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
            background: #1a1a1a;
            border-radius: 6px;
            overflow: hidden;
        }
        
        .orderbook-header {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            background: #2d2d2d;
            padding: 8px;
            font-weight: bold;
            color: #4CAF50;
            text-align: center;
            border-bottom: 1px solid #333;
        }
        
        .orderbook-table {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .orderbook-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            padding: 3px 8px;
            text-align: right;
            border-bottom: 1px solid #333333;
        }
        
        .orderbook-row:hover {
            background: rgba(76, 175, 80, 0.1);
        }
        
        .bid-row {
            background: rgba(76, 175, 80, 0.05);
        }
        
        .ask-row {
            background: rgba(244, 67, 54, 0.05);
        }
        
        .bid-price {
            color: #4CAF50;
            font-weight: bold;
        }
        
        .ask-price {
            color: #f44336;
            font-weight: bold;
        }
        
        .orderbook-size {
            color: #ffffff;
        }
        
        .orderbook-total {
            color: #cccccc;
            font-size: 10px;
        }
        
        .spread-info {
            background: #2d2d2d;
            padding: 8px;
            text-align: center;
            border-top: 1px solid #333;
            border-bottom: 1px solid #333;
            color: #FF9800;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Yahoo + Hyperliquid Trading Bot Dashboard</h1>
            <p>Real-time trading bot monitoring (Hyperliquid Price + Yahoo Analysis)</p>
                         <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
             <div id="update-indicator" style="margin-top: 10px; font-size: 12px; color: #4CAF50;">🔄 Auto-updating every 2 seconds (Yahoo candlestick data)</div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>📊 Session Status</h3>
                <div id="session-status">
                    <p><span class="status-indicator status-running"></span>Loading...</p>
                </div>
            </div>
            
            <div class="card">
                <h3>💰 Market Status</h3>
                <div id="market-status">
                    <p>Loading...</p>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 Live Orderbook</h3>
                <div id="orderbook-panel">
                    <p>Loading orderbook...</p>
                </div>
            </div>
        </div>
        
        <!-- Main Content Area with Predictions and Trading Summary Side by Side -->
        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 20px;">
                         <div class="card">
                 <h3>🎯 Best Trading Prediction (Highest Confidence)</h3>
                 <div id="predictions-panel">
                     <p>Loading best prediction...</p>
                 </div>
             </div>
            
            <div class="card">
                <h3>📈 Trading Summary</h3>
                <div id="trading-summary">
                    <p>Loading...</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>📝 Latest Activity</h3>
            <div id="latest-logs">
                <p>Loading...</p>
            </div>
        </div>
    </div>

    <script>
        function refreshData() {
            // Show updating indicator
            const indicator = document.getElementById('update-indicator');
            if (indicator) {
                indicator.innerHTML = '⏳ Updating...';
                indicator.style.color = '#ff9800';
            }
            
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('API Error:', data.error);
                        return;
                    }
                    updateSessionStatus(data.session);
                    updateMarketStatus(data.market);
                    updateTradingSummary(data.summary);
                    updateLatestLogs(data.logs);
                    updatePredictionsPanel(data.predictions);
                    updateOrderbook(data.orderbook);
                    
                    // Show last update time
                    if (indicator) {
                        const now = new Date().toLocaleTimeString();
                                                 indicator.innerHTML = `✅ Last updated: ${now} (Auto-refresh every 2s)`;
                        indicator.style.color = '#4CAF50';
                    }
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                    if (indicator) {
                        indicator.innerHTML = '❌ Update failed';
                        indicator.style.color = '#f44336';
                    }
                });
        }
        
        function updateSessionStatus(session) {
            const div = document.getElementById('session-status');
            if (session && session.session_id) {
                div.innerHTML = `
                    <p><span class="status-indicator status-running"></span>Running</p>
                    <p><strong>Session:</strong> ${session.session_id}</p>
                    <p><strong>Started:</strong> ${new Date(session.start_time).toLocaleString()}</p>
                    <p><strong>Strategy:</strong> ${session.strategy}</p>
                    <p><strong>Balance:</strong> $${session.initial_balance}</p>
                `;
            } else {
                div.innerHTML = '<p><span class="status-indicator status-stopped"></span>No active session</p>';
            }
        }
        
        function updateMarketStatus(market) {
            const div = document.getElementById('market-status');
            if (market && market.current_price) {
                const trendClass = market.trend === 'UP' ? 'trend-up' : 
                                 market.trend === 'DOWN' ? 'trend-down' : 'trend-neutral';
                
                // Debug RSI and Volume values
                console.log('Market data:', market);
                console.log('RSI value:', market.rsi, 'Type:', typeof market.rsi);
                console.log('Volume value:', market.volume_depth, 'Type:', typeof market.volume_depth);
                
                const rsiValue = market.rsi !== undefined && market.rsi !== null ? market.rsi.toFixed(1) : 'N/A';
                const volumeValue = market.volume_depth !== undefined && market.volume_depth !== null ? market.volume_depth.toFixed(1) : 'N/A';
                const flowValue = market.orderbook_imbalance !== undefined && market.orderbook_imbalance !== null ? (market.orderbook_imbalance * 100).toFixed(1) : 'N/A';
                
                // ENHANCED: Volume spike detection
                const hasVolumeSpike = market.has_volume_spike || false;
                const spikeSeverity = market.spike_severity || 'NORMAL';
                const isImmediateSpike = market.is_immediate_spike || false;
                const spikeReason = market.spike_reason || '';
                const volumeSource = market.volume_source || 'unknown';
                const volumeCategory = market.volume_category || 'UNKNOWN';
                const cumulativeVolume = market.cumulative_5m_volume !== undefined ? market.cumulative_5m_volume.toFixed(1) : 'N/A';
                const volumeTrend = market.volume_trend || 'UNKNOWN';
                const volumeSources = market.sources_used ? market.sources_used.join(', ') : 'unknown';
                
                div.innerHTML = `
                     <p><strong>Current Price:</strong> <span class="price ${trendClass}">$${market.hyperliquid_price ? market.hyperliquid_price.toLocaleString() : 'N/A'}</span></p>
                     <p><strong>Trend:</strong> <span class="${trendClass}">${market.trend}</span></p>
                     <p><strong>Condition:</strong> ${market.market_condition}</p>
                     
                     <!-- RSI - Fixed Display -->
                     <div class="market-indicator rsi-indicator" style="margin: 15px 0;">
                         <p><strong>📊 RSI:</strong> 
                         <span class="rsi-value ${market.rsi > 70 ? 'overbought' : market.rsi < 30 ? 'oversold' : 'neutral'}">${rsiValue}</span>
                         ${market.rsi > 70 ? '<span class="rsi-status overbought">🔴 OVERBOUGHT</span>' : market.rsi < 30 ? '<span class="rsi-status oversold">🟢 OVERSOLD</span>' : '<span class="rsi-status neutral">⚪ NEUTRAL</span>'}
                         </p>
                     </div>
                     
                                           <!-- Volume - Enhanced Display with Real-Time Data -->
                      <div class="market-indicator volume-indicator" style="margin: 15px 0;">
                          <p><strong>📈 Real-Time Volume:</strong> 
                          <span class="volume-value ${hasVolumeSpike ? 'volume-spike' : ''}">${volumeValue}</span>
                          <span class="volume-category">(${volumeCategory})</span>
                          <span class="spike-indicator ${hasVolumeSpike ? spikeSeverity.toLowerCase() : 'normal'}">${hasVolumeSpike ? `🚨 ${spikeSeverity} SPIKE` : '📊 NORMAL'}</span>
                          ${isImmediateSpike ? `<span class="immediate-spike">⚡ IMMEDIATE</span>` : ''}
                          </p>
                          <p><strong>📊 5m Cumulative:</strong> <span class="cumulative-volume">${cumulativeVolume}</span> BTC</p>
                          <p><strong>🔄 Trend:</strong> <span class="volume-trend">${volumeTrend}</span></p>
                          <p><strong>🌐 Sources:</strong> <span class="volume-sources">${volumeSources}</span></p>
                          ${hasVolumeSpike ? `<p class="spike-reason"><strong>Spike Reason:</strong> ${spikeReason}</p>` : ''}
                         <p><strong>📊 Order Flow:</strong> 
                         <span class="order-flow ${market.orderbook_imbalance > 0.1 ? 'bullish' : market.orderbook_imbalance < -0.1 ? 'bearish' : 'neutral'}">${flowValue}%</span>
                         ${market.orderbook_imbalance > 0.1 ? '🟢 BUY PRESSURE' : market.orderbook_imbalance < -0.1 ? '🔴 SELL PRESSURE' : '⚪ BALANCED'}
                         </p>
                         <p class="volume-source"><small>Source: ${volumeSource}</small></p>
                     </div>
                     
                     <p><strong>Updated:</strong> ${new Date(market.last_update).toLocaleString()}</p>
                 `;
            } else {
                div.innerHTML = '<p>No market data available</p>';
            }
        }
        
        function updateTradingSummary(summary) {
            const div = document.getElementById('trading-summary');
            div.innerHTML = `
                <p><strong>Total Trades:</strong> ${summary.total_trades}</p>
                <p><strong>Winning:</strong> ${summary.winning_trades}</p>
                <p><strong>Losing:</strong> ${summary.losing_trades}</p>
                <p><strong>Total P&L:</strong> $${summary.total_pnl.toFixed(2)}</p>
                <p><strong>Current Balance:</strong> $${summary.current_balance.toFixed(2)}</p>
            `;
        }
        
        function updateLatestLogs(logs) {
            const div = document.getElementById('latest-logs');
            if (logs && logs.length > 0) {
                let html = '';
                logs.slice(-10).reverse().forEach(log => {
                    const timestamp = log.datetime ? new Date(log.datetime).toLocaleString() : 'Unknown';
                    const type = log.trade_id ? 'trade-entry' : 'signal-entry';
                    const content = log.trade_id ? 
                        `Trade ${log.trade_id}: ${log.side} $${log.price?.toLocaleString() || 'N/A'}` :
                        `Signal: ${log.reason || 'N/A'}`;
                    
                    html += `<div class="log-entry ${type}">
                        <strong>${timestamp}</strong><br>
                        ${content}
                    </div>`;
                });
                div.innerHTML = html;
            } else {
                div.innerHTML = '<p>No recent activity</p>';
            }
        }
        
                 function updatePredictionsPanel(predictions) {
             const div = document.getElementById('predictions-panel');
             if (predictions && predictions.length > 0) {
                 let html = '<div class="predictions-container">';
                 
                 // Show only the best prediction (should be only one now)
                 const pred = predictions[0];
                 if (pred) {
                    const sideClass = pred.side === 'BUY' ? 'prediction-buy' : 'prediction-sell';
                    const confidenceClass = pred.confidence > 0.7 ? 'high-confidence' : 
                                          pred.confidence > 0.5 ? 'medium-confidence' : 'low-confidence';
                    
                                         html += `
                         <div class="prediction-card ${sideClass} ${confidenceClass}">
                             <div class="prediction-header">
                                 <span class="prediction-type">${pred.type || 'UNKNOWN'}</span>
                                 <span class="prediction-side">${pred.side}</span>
                             </div>
                             <div class="prediction-details">
                                 <p><strong>Entry Price:</strong> $${pred.entry_price?.toLocaleString() || 'N/A'}</p>
                                 <p><strong>Current Price:</strong> $${pred.current_price?.toLocaleString() || 'N/A'}</p>
                                 <p><strong>Confidence:</strong> ${(pred.confidence * 100).toFixed(1)}%</p>
                                 <p><strong>Timeframe:</strong> ${pred.timeframe || 'N/A'} min</p>
                                 <p><strong>Reason:</strong> ${pred.reason || 'N/A'}</p>
                                 ${pred.support ? `<p><strong>Support:</strong> $${pred.support.toLocaleString()}</p>` : ''}
                                 ${pred.resistance ? `<p><strong>Resistance:</strong> $${pred.resistance.toLocaleString()}</p>` : ''}
                                 ${pred.prediction_datetime ? `<p><strong>Generated:</strong> ${pred.prediction_datetime}</p>` : ''}
                             </div>
                         </div>
                     `;
                 }
                 
                 html += '</div>';
                 div.innerHTML = html;
             } else {
                 div.innerHTML = '<p>No active predictions</p>';
             }
        }
        
        function updateOrderbook(orderbook) {
            const div = document.getElementById('orderbook-panel');
            if (orderbook && !orderbook.error && orderbook.asks && orderbook.bids) {
                let html = `
                    <div class="orderbook-container">
                        <div class="orderbook-header">
                            <div>Price</div>
                            <div>Size (BTC)</div>
                            <div>Total (BTC)</div>
                        </div>
                        <div class="orderbook-table">
                `;
                
                // Show asks (sells) in reverse order (highest first)
                const asksToShow = orderbook.asks.slice(0, 8).reverse();
                asksToShow.forEach(ask => {
                    html += `
                        <div class="orderbook-row ask-row">
                            <div class="ask-price">${ask.price.toLocaleString()}</div>
                            <div class="orderbook-size">${ask.size.toFixed(4)}</div>
                            <div class="orderbook-total">${ask.total.toFixed(2)}</div>
                        </div>
                    `;
                });
                
                // Spread information
                html += `
                    <div class="spread-info">
                        Spread: $${orderbook.spread.toFixed(2)} (${orderbook.spread_pct.toFixed(3)}%)
                    </div>
                `;
                
                // Show bids (buys) in normal order (highest first)
                const bidsToShow = orderbook.bids.slice(0, 8);
                bidsToShow.forEach(bid => {
                    html += `
                        <div class="orderbook-row bid-row">
                            <div class="bid-price">${bid.price.toLocaleString()}</div>
                            <div class="orderbook-size">${bid.size.toFixed(4)}</div>
                            <div class="orderbook-total">${bid.total.toFixed(2)}</div>
                        </div>
                    `;
                });
                
                html += `
                        </div>
                    </div>
                `;
                
                div.innerHTML = html;
            } else {
                div.innerHTML = '<p>No orderbook data available</p>';
            }
        }
        
        // Auto-refresh every 2 seconds for frequent Yahoo candlestick updates
        setInterval(refreshData, 2000);
        
        // Initial load
        refreshData();
    </script>
</body>
</html>
        '''
        
        with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
            f.write(html_template)
            
        logger.info("✅ HTML template created successfully")
        
    except Exception as e:
        logger.error(f"Error creating template: {e}")

if __name__ == '__main__':
    # Create the template
    create_template()
    
    logger.info("🚀 Starting Simple HyperLBot Dashboard...")
    logger.info("📊 Dashboard will be available at: http://localhost:5001")
    logger.info("🔄 Auto-refreshing every 2 seconds for frequent Yahoo candlestick updates")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
