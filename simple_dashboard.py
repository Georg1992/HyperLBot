#!/usr/bin/env python3
"""
Simple HyperLBot Dashboard
Updates data on demand instead of background threads
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, jsonify
from loguru import logger

app = Flask(__name__)

class SimpleBotDashboard:
    def __init__(self):
        # Check for both old and new log directory names
        if os.path.exists("yahoo_hyperliquid_paper_trading_logs"):
            self.log_dir = "yahoo_hyperliquid_paper_trading_logs"
        elif os.path.exists("hybrid_paper_trading_logs"):
            self.log_dir = "hybrid_paper_trading_logs"
        else:
            self.log_dir = "yahoo_hyperliquid_paper_trading_logs"  # Default to new name
        
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
                    # Find the latest entry with actual market data (not strategy_switch)
                    latest = None
                    for entry in reversed(analysis_data):
                        if entry.get("analysis_type") == "hybrid_analysis_update" and entry.get("trend_analysis"):
                            latest = entry
                            break
                    
                    if latest:
                        trend_analysis = latest.get("trend_analysis", {})
                        current_price = latest.get("hyperliquid_price", 0.0)  # Use hyperliquid_price directly
                        trend = trend_analysis.get("trend", "UNKNOWN")
                        market_condition = latest.get("market_condition", "UNKNOWN")
                        last_update = latest.get("datetime", "Never")
                        
                        # Get price information from new architecture
                        hyperliquid_price = latest.get("hyperliquid_price", 0.0)
                        yahoo_last_close = latest.get("yahoo_last_close", 0.0)
                        price_diff_pct = latest.get("price_difference_pct", 0.0)
                        price_diff_amount = latest.get("price_difference_amount", 0.0)
                        data_source = latest.get("data_source", "Unknown")
                        
                        logger.info(f"Market data: ${current_price} - {trend} - {market_condition}")
                        
                        return {
                            "current_price": current_price,
                            "trend": trend,
                            "market_condition": market_condition,
                            "last_update": last_update,
                            "hyperliquid_price": hyperliquid_price,
                            "yahoo_last_close": yahoo_last_close,
                            "price_difference_pct": price_diff_pct,
                            "price_difference_amount": price_diff_amount,
                            "data_source": data_source
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
                        # Check for all_predictions first, then fall back to best_prediction
                        if latest.get("all_predictions"):
                            return latest.get("all_predictions", [])
                        elif latest.get("best_prediction"):
                            return [latest.get("best_prediction")]
            
            return []
            
        except Exception as e:
            logger.error(f"Error reading predictions: {e}")
            return []

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
        
        return jsonify({
            "session": session_data,
            "market": market_status,
            "logs": latest_logs,
            "summary": trade_summary,
            "predictions": latest_predictions,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in status API: {e}")
        return jsonify({"error": str(e)}), 500

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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Yahoo + Hyperliquid Trading Bot Dashboard</h1>
            <p>Real-time trading bot monitoring (Hyperliquid Price + Yahoo Analysis)</p>
                         <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
             <div id="update-indicator" style="margin-top: 10px; font-size: 12px; color: #4CAF50;">🔄 Auto-updating every 1 second</div>
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
                <h3>📈 Trading Summary</h3>
                <div id="trading-summary">
                    <p>Loading...</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>🎯 Live Trading Predictions</h3>
            <div id="predictions-panel">
                <p>Loading predictions...</p>
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
                    
                    // Show last update time
                    if (indicator) {
                        const now = new Date().toLocaleTimeString();
                        indicator.innerHTML = `✅ Last updated: ${now} (Auto-refresh every 1s)`;
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
                
                
                
                                 div.innerHTML = `
                     <p><strong>Current Price (Hyperliquid):</strong> <span class="price ${trendClass}">$${market.hyperliquid_price ? market.hyperliquid_price.toLocaleString() : 'N/A'}</span></p>
                     <p><strong>Yahoo Last Close:</strong> $${market.yahoo_last_close ? market.yahoo_last_close.toLocaleString() : 'N/A'}</p>
                     <p><strong>Price Diff:</strong> $${market.price_difference_amount ? market.price_difference_amount.toLocaleString() : 'N/A'} (${market.price_difference_pct ? market.price_difference_pct.toFixed(3) : 'N/A'}%)</p>
                     <p><strong>Trend:</strong> <span class="${trendClass}">${market.trend}</span></p>
                     <p><strong>Condition:</strong> ${market.market_condition}</p>
                     <p><strong>Updated:</strong> ${new Date(market.last_update).toLocaleString()}</p>
                     <p><strong>Data Source:</strong> ${market.data_source || 'Hyperliquid + Yahoo'}</p>
                     <p><small>Real-time price from Hyperliquid, Historical analysis from Yahoo Finance</small></p>
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
                
                predictions.forEach((pred, index) => {
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
                                <p><strong>Confidence:</strong> ${(pred.confidence * 100).toFixed(1)}%</p>
                                <p><strong>Timeframe:</strong> ${pred.timeframe || 'N/A'} min</p>
                                <p><strong>Reason:</strong> ${pred.reason || 'N/A'}</p>
                                ${pred.support ? `<p><strong>Support:</strong> $${pred.support.toLocaleString()}</p>` : ''}
                                ${pred.resistance ? `<p><strong>Resistance:</strong> $${pred.resistance.toLocaleString()}</p>` : ''}
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                div.innerHTML = html;
            } else {
                div.innerHTML = '<p>No active predictions</p>';
            }
        }
        
        // Auto-refresh every 1 second for ultra-fast real-time updates
        setInterval(refreshData, 1000);
        
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
    logger.info("📊 Dashboard will be available at: http://localhost:5000")
    logger.info("🔄 Auto-refreshing every 1 second for ultra-fast real-time updates")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
