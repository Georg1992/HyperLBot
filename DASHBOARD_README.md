# 🤖 HyperLBot Dashboard

A simple web-based dashboard to monitor your HyperLBot trading session in real-time.

## 🚀 Quick Start

### Option 1: Auto-Launch with Bot (Recommended)
```bash
python main.py
```
Then choose option 1 (Paper Trading) - dashboard opens automatically!

### Option 2: Dashboard Only
```bash
python main.py
```
Then choose option 3 (Start Dashboard Only)

### Option 3: Manual Launcher
```bash
python launch_dashboard.py
```

### Option 4: Direct Launch
```bash
python simple_dashboard.py
```

## 🚀 Auto-Launch Feature

The dashboard now **automatically opens** when you start the bot!

### **What happens:**
1. **Start the bot**: `python main.py` → Choose option 1 (Paper Trading)
2. **Dashboard starts**: Automatically in background
3. **Browser opens**: Dashboard appears in your default browser
4. **Real-time monitoring**: Watch your bot performance live!

### **No manual setup required** - just start the bot and the dashboard is ready!

## 📊 Dashboard Features

### **Real-time Monitoring**
- **Session Status**: Shows if bot is running, session ID, start time
- **Market Status**: Current price, trend, market condition
- **Trading Summary**: Total trades, wins/losses, P&L, current balance
- **Latest Activity**: Recent trades and signals

### **Auto-refresh**
- Dashboard updates automatically every 10 seconds
- Manual refresh button available
- Real-time data from bot logs

### **Visual Indicators**
- 🟢 **Green**: Running/Positive
- 🔴 **Red**: Stopped/Negative  
- 🟡 **Orange**: Warning/Neutral

## 🌐 Access

Once running, open your browser and go to:
```
http://localhost:5001
```

## 📱 Features

### **Session Status Card**
- Bot running status
- Session ID and start time
- Strategy being used
- Initial balance

### **Market Status Card**
- Current BTC price
- Market trend (UP/DOWN/NEUTRAL)
- Market condition
- Last update time

### **Trading Summary Card**
- Total number of trades
- Winning vs losing trades
- Total profit/loss
- Current account balance

### **Latest Activity**
- Recent trades with details
- Trading signals
- Timestamps for all activities

## 🔧 Technical Details

- **Framework**: Flask (Python web framework)
- **Updates**: Every 5 seconds in background
- **Port**: 5001 (configurable)
- **Data Source**: Bot log files in `hybrid_paper_trading_logs/`

## 🛠️ Troubleshooting

### **Dashboard won't start**
```bash
pip install flask>=2.3.0
```

### **No data showing**
- Make sure the bot is running
- Check that log files exist in `hybrid_paper_trading_logs/`
- Verify bot has generated some activity

### **Port already in use**
- Change port in `simple_dashboard.py` line: `app.run(port=5002)`
- Or kill process using port 5001

## 📈 Usage Tips

1. **Keep dashboard open** while bot is running
2. **Monitor trends** in market status
3. **Watch for new trades** in latest activity
4. **Check session status** to ensure bot is running
5. **Use refresh button** for immediate updates

## 🎯 Perfect for
- **Real-time monitoring** of bot performance
- **Quick status checks** without digging through logs
- **Visual tracking** of trading activity
- **Remote monitoring** (accessible from any device on network)
