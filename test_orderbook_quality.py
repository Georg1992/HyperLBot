#!/usr/bin/env python3
"""
Orderbook Quality Analysis
Test the depth and quality of orderbook data from Hyperliquid API
"""

import sys
import os
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_orderbook_quality():
    """Analyze the quality and depth of Hyperliquid orderbook data"""
    try:
        logger.info("🔍 Testing Hyperliquid Orderbook Data Quality")
        
        from core.hyperliquid_api import HyperliquidAPI
        
        api = HyperliquidAPI()
        market_data = api.get_market_data("BTC")
        
        if not market_data or 'levels' not in market_data:
            logger.error("❌ Failed to get orderbook data")
            return False
        
        bids = market_data['levels'][0] if len(market_data['levels']) > 0 else []
        asks = market_data['levels'][1] if len(market_data['levels']) > 1 else []
        
        logger.info(f"📊 ORDERBOOK ANALYSIS:")
        logger.info(f"   Bid Levels Available: {len(bids)}")
        logger.info(f"   Ask Levels Available: {len(asks)}")
        
        if len(bids) == 0 or len(asks) == 0:
            logger.error("❌ No orderbook levels available")
            return False
        
        # Show top 10 levels
        logger.info(f"\n🟢 TOP 10 BIDS:")
        for i, bid in enumerate(bids[:10]):
            price = float(bid['px'])
            size = float(bid['sz'])
            usd_value = price * size
            logger.info(f"   Level {i+1}: ${price:,.2f} | {size:.4f} BTC | ${usd_value:,.0f} USD")
        
        logger.info(f"\n🔴 TOP 10 ASKS:")
        for i, ask in enumerate(asks[:10]):
            price = float(ask['px'])
            size = float(ask['sz'])
            usd_value = price * size
            logger.info(f"   Level {i+1}: ${price:,.2f} | {size:.4f} BTC | ${usd_value:,.0f} USD")
        
        # Calculate depth analysis
        if len(bids) >= 10 and len(asks) >= 10:
            bid_depth_1 = sum(float(bids[i]['sz']) for i in range(1))
            bid_depth_5 = sum(float(bids[i]['sz']) for i in range(5))
            bid_depth_10 = sum(float(bids[i]['sz']) for i in range(10))
            
            ask_depth_1 = sum(float(asks[i]['sz']) for i in range(1))
            ask_depth_5 = sum(float(asks[i]['sz']) for i in range(5))
            ask_depth_10 = sum(float(asks[i]['sz']) for i in range(10))
            
            logger.info(f"\n📈 DEPTH ANALYSIS:")
            logger.info(f"   Bid Depth (Top 1): {bid_depth_1:.4f} BTC")
            logger.info(f"   Bid Depth (Top 5): {bid_depth_5:.4f} BTC")
            logger.info(f"   Bid Depth (Top 10): {bid_depth_10:.4f} BTC")
            logger.info(f"   Ask Depth (Top 1): {ask_depth_1:.4f} BTC")
            logger.info(f"   Ask Depth (Top 5): {ask_depth_5:.4f} BTC")
            logger.info(f"   Ask Depth (Top 10): {ask_depth_10:.4f} BTC")
            
            # Total liquidity
            total_bid_liquidity = bid_depth_10
            total_ask_liquidity = ask_depth_10
            total_liquidity = total_bid_liquidity + total_ask_liquidity
            
            logger.info(f"\n💰 LIQUIDITY SUMMARY:")
            logger.info(f"   Total Bid Liquidity (Top 10): {total_bid_liquidity:.4f} BTC")
            logger.info(f"   Total Ask Liquidity (Top 10): {total_ask_liquidity:.4f} BTC")
            logger.info(f"   Combined Liquidity: {total_liquidity:.4f} BTC")
            
            # Imbalance calculation
            if total_liquidity > 0:
                imbalance = ((total_bid_liquidity - total_ask_liquidity) / total_liquidity) * 100
                logger.info(f"   Orderbook Imbalance: {imbalance:+.2f}% ({'BUY PRESSURE' if imbalance > 0 else 'SELL PRESSURE'})")
        
        # Price spreads
        best_bid = float(bids[0]['px'])
        best_ask = float(asks[0]['px'])
        spread = best_ask - best_bid
        spread_pct = (spread / best_bid) * 100
        
        logger.info(f"\n📊 SPREAD ANALYSIS:")
        logger.info(f"   Best Bid: ${best_bid:,.2f}")
        logger.info(f"   Best Ask: ${best_ask:,.2f}")
        logger.info(f"   Bid-Ask Spread: ${spread:.2f} ({spread_pct:.4f}%)")
        
        if len(bids) >= 5 and len(asks) >= 5:
            bid_5_price = float(bids[4]['px'])
            ask_5_price = float(asks[4]['px'])
            depth_spread_5 = ask_5_price - bid_5_price
            depth_spread_5_pct = (depth_spread_5 / best_bid) * 100
            
            logger.info(f"   Level 5 Bid: ${bid_5_price:,.2f}")
            logger.info(f"   Level 5 Ask: ${ask_5_price:,.2f}")
            logger.info(f"   Level 5 Spread: ${depth_spread_5:.2f} ({depth_spread_5_pct:.4f}%)")
        
        # Price impact analysis
        if len(bids) >= 10 and len(asks) >= 10:
            logger.info(f"\n💥 PRICE IMPACT ANALYSIS:")
            
            # Calculate how much BTC you could buy/sell at different impact levels
            cumulative_bid_size = 0
            cumulative_ask_size = 0
            
            for i in range(min(10, len(bids))):
                cumulative_bid_size += float(bids[i]['sz'])
                price_impact = ((best_bid - float(bids[i]['px'])) / best_bid) * 100
                logger.info(f"   Sell {cumulative_bid_size:.4f} BTC: {price_impact:.3f}% impact (down to ${float(bids[i]['px']):,.2f})")
                if i >= 2:  # Only show first 3 levels for brevity
                    break
            
            logger.info(f"")
            for i in range(min(10, len(asks))):
                cumulative_ask_size += float(asks[i]['sz'])
                price_impact = ((float(asks[i]['px']) - best_ask) / best_ask) * 100
                logger.info(f"   Buy {cumulative_ask_size:.4f} BTC: {price_impact:.3f}% impact (up to ${float(asks[i]['px']):,.2f})")
                if i >= 2:  # Only show first 3 levels for brevity
                    break
        
        logger.info(f"\n✅ TOTAL LEVELS AVAILABLE: Bids={len(bids)}, Asks={len(asks)}")
        
        # Quality assessment
        assess_orderbook_quality(len(bids), len(asks), spread_pct, total_liquidity if 'total_liquidity' in locals() else 0)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Orderbook analysis failed: {e}")
        return False

def assess_orderbook_quality(bid_levels, ask_levels, spread_pct, total_liquidity):
    """Assess the quality of orderbook data for analytics"""
    logger.info(f"\n🎯 ORDERBOOK QUALITY ASSESSMENT:")
    logger.info("=" * 60)
    
    # Level depth assessment
    if bid_levels >= 20 and ask_levels >= 20:
        logger.success("✅ EXCELLENT depth: 20+ levels for sophisticated analytics")
        depth_score = "EXCELLENT"
    elif bid_levels >= 10 and ask_levels >= 10:
        logger.success("✅ GOOD depth: 10+ levels for professional analytics")
        depth_score = "GOOD"
    elif bid_levels >= 5 and ask_levels >= 5:
        logger.warning("⚠️ ADEQUATE depth: 5+ levels for basic analytics")
        depth_score = "ADEQUATE"
    else:
        logger.error("❌ POOR depth: <5 levels insufficient for analytics")
        depth_score = "POOR"
    
    # Spread assessment (for BTC)
    if spread_pct < 0.01:  # <0.01%
        logger.success("✅ EXCELLENT spread: <0.01% (very tight)")
        spread_score = "EXCELLENT"
    elif spread_pct < 0.05:  # <0.05%
        logger.success("✅ GOOD spread: <0.05% (tight)")
        spread_score = "GOOD"
    elif spread_pct < 0.1:  # <0.1%
        logger.warning("⚠️ ADEQUATE spread: <0.1% (reasonable)")
        spread_score = "ADEQUATE"
    else:
        logger.error("❌ POOR spread: >0.1% (too wide)")
        spread_score = "POOR"
    
    # Liquidity assessment
    if total_liquidity > 10:  # >10 BTC
        logger.success("✅ EXCELLENT liquidity: >10 BTC (deep market)")
        liquidity_score = "EXCELLENT"
    elif total_liquidity > 5:  # >5 BTC
        logger.success("✅ GOOD liquidity: >5 BTC (adequate depth)")
        liquidity_score = "GOOD"
    elif total_liquidity > 1:  # >1 BTC
        logger.warning("⚠️ ADEQUATE liquidity: >1 BTC (limited depth)")
        liquidity_score = "ADEQUATE"
    else:
        logger.error("❌ POOR liquidity: <1 BTC (shallow market)")
        liquidity_score = "POOR"
    
    # Overall assessment
    scores = [depth_score, spread_score, liquidity_score]
    excellent_count = scores.count("EXCELLENT")
    good_count = scores.count("GOOD")
    adequate_count = scores.count("ADEQUATE")
    poor_count = scores.count("POOR")
    
    logger.info(f"\n🏆 OVERALL QUALITY RATING:")
    logger.info("=" * 60)
    
    if excellent_count >= 2:
        logger.success("🏆 EXCELLENT - Perfect for institutional-grade analytics")
        logger.success("   ✅ Suitable for:")
        logger.success("      • High-frequency trading algorithms")
        logger.success("      • Sophisticated orderbook imbalance analysis")
        logger.success("      • Precise liquidity absorption tracking")
        logger.success("      • Multi-level depth-weighted calculations")
        logger.success("      • Professional market making strategies")
    elif good_count >= 2 or (excellent_count >= 1 and adequate_count <= 1):
        logger.success("🥇 GOOD - Suitable for professional analytics")
        logger.success("   ✅ Suitable for:")
        logger.success("      • Professional trading algorithms")
        logger.success("      • Multi-level orderbook analysis")
        logger.success("      • Reliable pressure indicator calculations")
        logger.success("      • Most institutional trading strategies")
    elif adequate_count >= 2 or poor_count == 0:
        logger.warning("🥉 ADEQUATE - Basic analytics possible")
        logger.warning("   ⚠️ Limited to:")
        logger.warning("      • Basic orderbook imbalance")
        logger.warning("      • Simple pressure indicators")
        logger.warning("      • Conservative trading strategies")
    else:
        logger.error("❌ POOR - Insufficient for reliable analytics")
        logger.error("   ❌ Problems:")
        logger.error("      • Unreliable pressure calculations")
        logger.error("      • Limited market depth visibility")
        logger.error("      • High slippage risk")
    
    return scores

if __name__ == "__main__":
    logger.info("🚀 Hyperliquid Orderbook Quality Analysis")
    print()
    
    success = analyze_orderbook_quality()
    
    if success:
        logger.info("\n💡 RECOMMENDATION:")
        logger.info("=" * 60)
        logger.info("Based on the analysis above, determine if Hyperliquid provides")
        logger.info("sufficient orderbook depth for your Ultimate Pressure Indicator")
        logger.info("and professional trading analytics.")
    
    print()