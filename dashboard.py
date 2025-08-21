#!/usr/bin/env python3
"""
HyperLBot Dashboard
Simple web interface to track bot session in real-time
"""

import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify
import threading
from loguru import logger

app = Flask(__name__)

class BotDashboard:
    def __init__(self):
        self.session_data = {}
        self.latest_logs = []
        self.trade_summary = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "current_balance": 0.0
        }
        self.market_status = {
            "current_price": 0.0,
            "trend": "UNKNOWN",
            "market_condition": "UNKNOWN",
            "last_update": "Never"
        }
        
    def update_session_data(self):
        """Update session data from logs"""
        try:
            # Find latest session metadata
            log_dir = "hybrid_paper_trading_logs"
            if not os.path.exists(log_dir):
                logger.warning(f"Log directory {log_dir} does not exist")
                return
                
            session_files = [f for f in os.listdir(log_dir) if f.startswith("session_metadata_")]
            if not session_files:
                logger.warning("No session metadata files found")
                return
                
            latest_session = max(session_files)
            session_path = os.path.join(log_dir, latest_session)
            
            with open(session_path, 'r') as f:
                self.session_data = json.load(f)
                logger.info(f"Updated session data from {latest_session}")
                
        except Exception as e:
            logger.error(f"Error updating session data: {e}")
            # Set default session data if file reading fails
            self.session_data = {
                "session_id": "Unknown",
                "start_time": datetime.now().isoformat(),
                "strategy": "Unknown",
                "initial_balance": 0.0
            }
    
    def update_latest_logs(self):
        """Update latest logs from all log files"""
        try:
            log_dir = "hybrid_paper_trading_logs"
            if not os.path.exists(log_dir):
                return
                
            self.latest_logs = []
            
            # Check trades
            trades_dir = os.path.join(log_dir, "trades")
            if os.path.exists(trades_dir):
                trade_files = [f for f in os.listdir(trades_dir) if f.endswith('.json')]
                if trade_files:
                    latest_trades = max(trade_files)
                    trades_path = os.path.join(trades_dir, latest_trades)
                    with open(trades_path, 'r') as f:
                        trades = json.load(f)
                        if trades:
                            self.latest_logs.extend(trades[-5:])  # Last 5 trades
            
            # Check signals
            signals_dir = os.path.join(log_dir, "signals")
            if os.path.exists(signals_dir):
                signal_files = [f for f in os.listdir(signals_dir) if f.endswith('.json')]
                if signal_files:
                    latest_signals = max(signal_files)
                    signals_path = os.path.join(signals_dir, latest_signals)
                    with open(signals_path, 'r') as f:
                        signals = json.load(f)
                        if signals:
                            self.latest_logs.extend(signals[-3:])  # Last 3 signals
                            
        except Exception as e:
            logger.error(f"Error updating logs: {e}")
    
    def update_market_status(self):
        """Update market status from analysis logs"""
        try:
            log_dir = "hybrid_paper_trading_logs"
            analysis_dir = os.path.join(log_dir, "analysis")
            
            if os.path.exists(analysis_dir):
                analysis_files = [f for f in os.listdir(analysis_dir) if f.endswith('.json')]
                if analysis_files:
                    latest_analysis = max(analysis_files)
                    analysis_path = os.path.join(analysis_dir, latest_analysis)
                    
                    with open(analysis_path, 'r') as f:
                        analysis_data = json.load(f)
                        if analysis_data and len(analysis_data) > 0:
                            latest = analysis_data[-1]
                            trend_analysis = latest.get("trend_analysis", {})
                            self.market_status = {
                                "current_price": trend_analysis.get("last_close", 0.0),
                                "trend": trend_analysis.get("trend", "UNKNOWN"),
                                "market_condition": latest.get("market_condition", "UNKNOWN"),
                                "last_update": latest.get("datetime", "Never")
                            }
                            logger.info(f"Updated market status: ${self.market_status['current_price']} - {self.market_status['trend']}")
                            
        except Exception as e:
            logger.error(f"Error updating market status: {e}")

# Global dashboard instance
dashboard = BotDashboard()

def update_dashboard():
    """Background thread to update dashboard data"""
    while True:
        try:
            dashboard.update_session_data()
            dashboard.update_latest_logs()
            dashboard.update_market_status()
            time.sleep(5)  # Update every 5 seconds
        except Exception as e:
            logger.error(f"Dashboard update error: {e}")
            time.sleep(10)

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
        return jsonify({
            "session": dashboard.session_data,
            "market": dashboard.market_status,
            "logs": dashboard.latest_logs,
            "summary": dashboard.trade_summary,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in status API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """API endpoint for latest logs"""
    try:
        return jsonify(dashboard.latest_logs)
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 HyperLBot Dashboard</h1>
            <p>Real-time trading bot monitoring</p>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
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
            <h3>📝 Latest Activity</h3>
            <div id="latest-logs">
                <p>Loading...</p>
            </div>
        </div>
    </div>

    <script>
        function refreshData() {
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
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
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
                    <p><strong>Price:</strong> <span class="price ${trendClass}">$${market.current_price.toLocaleString()}</span></p>
                    <p><strong>Trend:</strong> <span class="${trendClass}">${market.trend}</span></p>
                    <p><strong>Condition:</strong> ${market.market_condition}</p>
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
        
        // Auto-refresh every 10 seconds
        setInterval(refreshData, 10000);
        
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
    
    # Start background update thread
    update_thread = threading.Thread(target=update_dashboard, daemon=True)
    update_thread.start()
    
    logger.info("🚀 Starting HyperLBot Dashboard...")
    logger.info("📊 Dashboard will be available at: http://localhost:5000")
    logger.info("🔄 Auto-refreshing every 10 seconds")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
