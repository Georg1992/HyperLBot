#!/usr/bin/env python3
"""
Test Volatility Detection System
Verifies that the bot can properly detect high volatility market conditions
"""

import statistics

def test_volatility_detection():
    """Test volatility detection with various market scenarios"""
    print("🔍 Testing Volatility Detection System")
    print("=" * 60)
    
    # Test 1: High Volatility Market Simulation
    print("🧪 Test 1: High Volatility Market (Recent Hours)")
    
    # Simulate high volatility BTC market - realistic high vol scenario
    # Price swings of 0.3-0.8% per 5-minute period
    base_price = 113000
    high_vol_prices = [
        113000,  # Start
        113300,  # +0.27%
        113100,  # -0.18%
        113500,  # +0.35%
        112900,  # -0.53%
        113200,  # +0.27%
        113700,  # +0.44%
        113200,  # -0.44%
        113600,  # +0.35%
        112800,  # -0.70%
        113100,  # +0.27%
        113800,  # +0.62%
        113300,  # -0.44%
        113900,  # +0.53%
        113400,  # -0.44%
        113000,  # -0.35%
        113500,  # +0.44%
        112700,  # -0.70%
        113200,  # +0.44%
        113600   # +0.35%
    ]
    
    # Convert to candle format
    high_vol_candles = []
    for i, price in enumerate(high_vol_prices):
        candle = {
            "close": price,
            "open": price - (20 if i > 0 else 0),
            "high": price + 50,
            "low": price - 80,
            "volume": 2000 + (i * 100)  # High volume
        }
        high_vol_candles.append(candle)
    
    # Test current volatility calculation (20-period average)
    def calculate_current_volatility(candles, periods=20):
        """Current volatility calculation method"""
        if len(candles) < periods:
            return 0
        
        recent_candles = candles[-periods:]
        returns = []
        
        for i in range(1, len(recent_candles)):
            prev_close = recent_candles[i-1]["close"]
            curr_close = recent_candles[i]["close"]
            ret = abs((curr_close - prev_close) / prev_close)
            returns.append(ret)
        
        return statistics.mean(returns) if returns else 0
    
    # Test enhanced volatility calculation (more responsive)
    def calculate_enhanced_volatility(candles, periods=20):
        """Enhanced volatility calculation with recent bias"""
        if len(candles) < periods:
            return 0
        
        recent_candles = candles[-periods:]
        returns = []
        
        for i in range(1, len(recent_candles)):
            prev_close = recent_candles[i-1]["close"]
            curr_close = recent_candles[i]["close"]
            ret = abs((curr_close - prev_close) / prev_close)
            returns.append(ret)
        
        if not returns:
            return 0
        
        # Weight recent returns more heavily
        weighted_returns = []
        for i, ret in enumerate(returns):
            weight = 1.0 + (i / len(returns)) * 0.5  # Recent returns get 50% more weight
            weighted_returns.append(ret * weight)
        
        # Also calculate recent volatility (last 5 periods only)
        recent_volatility = statistics.mean(returns[-5:]) if len(returns) >= 5 else statistics.mean(returns)
        overall_volatility = statistics.mean(weighted_returns)
        
        # Use the higher of recent or overall volatility to catch spikes
        return max(recent_volatility, overall_volatility)
    
    # Test both methods
    current_vol = calculate_current_volatility(high_vol_candles, 20)
    enhanced_vol = calculate_enhanced_volatility(high_vol_candles, 20)
    recent_vol = calculate_current_volatility(high_vol_candles, 5)  # Last 5 periods only
    
    print(f"📊 High Volatility Market Analysis:")
    print(f"   Current Method (20-period avg): {current_vol*100:.3f}%")
    print(f"   Enhanced Method (weighted): {enhanced_vol*100:.3f}%")
    print(f"   Recent Only (5-period): {recent_vol*100:.3f}%")
    
    # Test current thresholds
    print(f"\n🎯 Threshold Analysis:")
    print(f"   Current HIGH_VOLATILITY threshold: 2.000% (0.02)")
    print(f"   Current strategy high_vol threshold: 0.500% (0.005)")
    print(f"   Current LOW_VOLATILITY threshold: 0.500% (0.005)")
    print(f"   Current strategy low_vol threshold: 0.100% (0.001)")
    
    # Check what strategy would be selected
    def test_strategy_selection(volatility_5m, volatility_1h, market_condition):
        """Test strategy selection logic"""
        range_percentage = 0.008  # Assume 0.8% range
        
        if market_condition == "LOW_VOLATILITY" or volatility_5m < 0.001 or range_percentage < 0.003:
            return "low_volatility"
        elif market_condition == "HIGH_VOLATILITY" or volatility_5m > 0.005 or volatility_1h > 0.01 or range_percentage > 0.01:
            return "high_volatility"
        else:
            return "standard"
    
    # Test market condition determination
    def test_market_condition(volatility):
        """Test market condition determination"""
        if volatility > 0.02:  # 2% volatility
            return "HIGH_VOLATILITY"
        elif volatility < 0.005:  # 0.5% volatility
            return "LOW_VOLATILITY"
        else:
            return "NORMAL"
    
    current_condition = test_market_condition(current_vol)
    enhanced_condition = test_market_condition(enhanced_vol)
    recent_condition = test_market_condition(recent_vol)
    
    current_strategy = test_strategy_selection(current_vol, current_vol, current_condition)
    enhanced_strategy = test_strategy_selection(enhanced_vol, enhanced_vol, enhanced_condition)
    recent_strategy = test_strategy_selection(recent_vol, recent_vol, recent_condition)
    
    print(f"\n📈 Strategy Selection Results:")
    print(f"   Current Method: {current_condition} → {current_strategy}")
    print(f"   Enhanced Method: {enhanced_condition} → {enhanced_strategy}")
    print(f"   Recent Method: {recent_condition} → {recent_strategy}")
    
    # Test 2: Low Volatility Market
    print(f"\n🧪 Test 2: Low Volatility Market (Sideways)")
    
    # Simulate low volatility (sideways market)
    low_vol_prices = []
    base = 113000
    for i in range(20):
        # Small random movements ±0.05%
        variation = (i % 5 - 2) * 0.0005 * base  # ±0.05% variation
        price = base + variation
        low_vol_prices.append(price)
    
    low_vol_candles = []
    for i, price in enumerate(low_vol_prices):
        candle = {
            "close": price,
            "open": price + (i % 3 - 1) * 10,
            "high": price + 30,
            "low": price - 30,
            "volume": 800
        }
        low_vol_candles.append(candle)
    
    low_vol_current = calculate_current_volatility(low_vol_candles, 20)
    low_vol_enhanced = calculate_enhanced_volatility(low_vol_candles, 20)
    
    print(f"📊 Low Volatility Market Analysis:")
    print(f"   Current Method: {low_vol_current*100:.3f}%")
    print(f"   Enhanced Method: {low_vol_enhanced*100:.3f}%")
    
    low_condition = test_market_condition(low_vol_current)
    low_strategy = test_strategy_selection(low_vol_current, low_vol_current, low_condition)
    
    print(f"   Market Condition: {low_condition}")
    print(f"   Strategy Selected: {low_strategy}")
    
    # Recommendations
    print(f"\n🎯 ANALYSIS RESULTS:")
    if current_vol < 0.005 and recent_vol > 0.003:
        print("❌ PROBLEM DETECTED: Recent high volatility NOT detected by current method!")
        print("   Issue: 20-period averaging smooths out recent volatility spikes")
        print("   Solution: Use shorter periods or weighted recent volatility")
    
    if current_condition != "HIGH_VOLATILITY" and recent_condition == "HIGH_VOLATILITY":
        print("❌ STRATEGY MISMATCH: Recent high volatility not triggering correct strategy")
        print("   Current thresholds too high for crypto volatility")
    
    print(f"\n💡 RECOMMENDED FIXES:")
    print("1. Lower HIGH_VOLATILITY threshold from 2.0% to 0.8%")
    print("2. Lower high_vol strategy threshold from 0.5% to 0.3%")
    print("3. Add recent volatility bias (weight last 5 periods more)")
    print("4. Use real-time volatility calculation from Hyperliquid orderbook")

if __name__ == "__main__":
    test_volatility_detection()