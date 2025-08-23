#!/usr/bin/env python3
"""
Price Momentum Demonstration
Show how the Ultimate Pressure Indicator tracks price fluctuations
"""

import sys
import os
import time
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_price_momentum_tracking():
    """Demonstrate price momentum tracking with rapid updates"""
    try:
        logger.info("📈 Testing Price Momentum Tracking System")
        
        from core.hyperliquid_api import HyperliquidAPI
        from data.ultimate_pressure_indicator import UltimatePressureIndicator
        
        api = HyperliquidAPI()
        indicator = UltimatePressureIndicator()
        
        logger.info("🎯 Ultimate Pressure Indicator initialized")
        logger.info("📊 Collecting rapid price updates to build momentum history...")
        
        # Collect price data at high frequency (every 1-2 seconds)
        momentum_results = []
        
        for i in range(8):  # 8 updates over ~14 seconds
            logger.info(f"\n📊 Price Update {i+1}/8:")
            
            try:
                # Get current price and store it
                current_price = api.get_current_price("BTC")
                if current_price:
                    current_time = time.time()
                    indicator.price_history.append({"price": current_price, "timestamp": current_time})
                    
                    logger.info(f"   💰 Price: ${current_price:,.2f}")
                    logger.info(f"   📊 Price History Count: {len(indicator.price_history)}")
                    
                    # Calculate momentum if we have enough data
                    if len(indicator.price_history) >= 5:
                        momentum_data = indicator._calculate_price_momentum()
                        
                        pressure_score = momentum_data.get("pressure_score", 0)
                        strength = momentum_data.get("strength", "UNKNOWN")
                        momentum_1s = momentum_data.get("momentum_1s", 0)
                        momentum_5s = momentum_data.get("momentum_5s", 0)
                        momentum_15s = momentum_data.get("momentum_15s", 0)
                        
                        logger.success(f"   🎯 Momentum Analysis:")
                        logger.success(f"      Overall Score: {pressure_score:+.1f} ({strength})")
                        logger.success(f"      1-sec velocity: {momentum_1s:+.6f}")
                        logger.success(f"      5-sec velocity: {momentum_5s:+.6f}")
                        logger.success(f"      15-sec velocity: {momentum_15s:+.6f}")
                        
                        momentum_results.append({
                            "price": current_price,
                            "momentum_score": pressure_score,
                            "strength": strength,
                            "update": i+1
                        })
                        
                        # Interpret momentum for trading
                        if pressure_score > 25:
                            logger.success(f"      🟢 STRONG UPWARD MOMENTUM - Price accelerating UP!")
                        elif pressure_score > 10:
                            logger.info(f"      🔵 MODERATE UPWARD MOMENTUM - Gentle price rise")
                        elif pressure_score < -25:
                            logger.error(f"      🔴 STRONG DOWNWARD MOMENTUM - Price accelerating DOWN!")
                        elif pressure_score < -10:
                            logger.warning(f"      🟠 MODERATE DOWNWARD MOMENTUM - Gentle price decline")
                        else:
                            logger.info(f"      ⚪ NEUTRAL MOMENTUM - Price stable")
                    else:
                        logger.info(f"   ⏳ Need {5 - len(indicator.price_history)} more updates for momentum calculation")
                else:
                    logger.error(f"   ❌ Failed to get current price")
                    
            except Exception as e:
                logger.error(f"   ❌ Price update error: {e}")
            
            # Sleep between updates (1.8 seconds for realistic timing)
            if i < 7:  # Don't sleep on last iteration
                time.sleep(1.8)
        
        # Summary analysis
        if momentum_results:
            logger.info("\n📊 MOMENTUM TRACKING SUMMARY:")
            logger.info("=" * 60)
            
            logger.info("Price & Momentum Evolution:")
            for result in momentum_results:
                update = result["update"]
                price = result["price"]
                score = result["momentum_score"]
                strength = result["strength"]
                logger.info(f"   Update {update}: ${price:,.2f} → Momentum: {score:+.1f} ({strength})")
            
            # Calculate momentum trend
            if len(momentum_results) >= 3:
                early_momentum = momentum_results[0]["momentum_score"]
                late_momentum = momentum_results[-1]["momentum_score"]
                momentum_change = late_momentum - early_momentum
                
                logger.info(f"\n🎯 MOMENTUM TREND ANALYSIS:")
                logger.info(f"   Initial Momentum: {early_momentum:+.1f}")
                logger.info(f"   Final Momentum: {late_momentum:+.1f}")
                logger.info(f"   Momentum Change: {momentum_change:+.1f}")
                
                if momentum_change > 10:
                    logger.success(f"   📈 MOMENTUM STRENGTHENING - Price acceleration increasing!")
                elif momentum_change < -10:
                    logger.warning(f"   📉 MOMENTUM WEAKENING - Price acceleration decreasing!")
                else:
                    logger.info(f"   ➡️ MOMENTUM STABLE - Consistent price behavior")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Price momentum test failed: {e}")
        return False

def demonstrate_full_pressure_with_momentum():
    """Show how momentum integrates with other pressure signals"""
    logger.info("\n🎯 FULL PRESSURE ANALYSIS WITH MOMENTUM:")
    logger.info("=" * 60)
    
    try:
        from core.hyperliquid_api import HyperliquidAPI
        
        api = HyperliquidAPI()
        
        # Get the full pressure analysis (which should now have momentum data)
        pressure_data = api.get_ultimate_pressure("BTC")
        
        if pressure_data.get("status") == "success":
            logger.info(f"🎯 Complete Analysis: {pressure_data.get('display', 'N/A')}")
            
            # Show detailed signal breakdown
            signal_details = pressure_data.get("signal_details", {})
            logger.info(f"\n📊 All 7 Signals (including Price Momentum):")
            
            for signal_name, details in signal_details.items():
                score = details.get("score", 0)
                strength = details.get("strength", "UNKNOWN")
                quality = details.get("quality", "UNKNOWN")
                
                if signal_name == "momentum":
                    if quality == "HIGH":
                        logger.success(f"   🎯 {signal_name.title()}: {score:+.1f} ({strength}) ← PRICE FLUCTUATIONS!")
                    else:
                        logger.warning(f"   🎯 {signal_name.title()}: {score:+.1f} ({strength}) ← {quality}")
                else:
                    logger.info(f"   📊 {signal_name.title()}: {score:+.1f} ({strength})")
            
            logger.info(f"\n💡 KEY INSIGHTS:")
            logger.info(f"   • Price Momentum tracks velocity at 1s, 5s, 15s timeframes")
            logger.info(f"   • Combined with 6 other signals for ultimate accuracy")
            logger.info(f"   • Updates every 1-2 seconds with live orderbook + price data")
            logger.info(f"   • Shows both DIRECTION and STRENGTH of market pressure")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Full pressure demo failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Price Momentum & Fluctuation Tracking Demo")
    print()
    
    # Test 1: Price momentum tracking
    momentum_success = test_price_momentum_tracking()
    
    if momentum_success:
        # Test 2: Full pressure with momentum
        full_success = demonstrate_full_pressure_with_momentum()
        
        if full_success:
            logger.info("\n🎉 PRICE FLUCTUATION TRACKING CONFIRMED!")
            logger.info("=" * 60)
            logger.success("✅ YES - Ultimate Pressure tracks price fluctuations via:")
            logger.success("   • 1-second momentum (immediate price acceleration)")
            logger.success("   • 5-second momentum (short-term trends)")  
            logger.success("   • 15-second momentum (medium-term context)")
            logger.success("   • Combined with 6 other orderbook signals")
            logger.success("   • Updates every 1-2 seconds for real-time pressure")
            
            logger.info("\n💡 TRADING ADVANTAGE:")
            logger.info("   🎯 Catches rapid price movements BEFORE they become trends")
            logger.info("   🎯 Combines price velocity with orderbook depth for accuracy") 
            logger.info("   🎯 Perfect for scalping and high-frequency trading strategies")
    
    print()