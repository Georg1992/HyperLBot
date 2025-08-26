#!/usr/bin/env python3
"""
Test script for Hyperliquid WebSocket implementation
"""

import time
import signal
import sys
from loguru import logger
from core.hyperliquid_websocket import start_websocket, stop_websocket

def signal_handler(signum, frame):
    """Handle shutdown signal"""
    logger.info("🛑 Shutdown signal received, stopping WebSocket...")
    stop_websocket()
    sys.exit(0)

def test_websocket():
    """Test WebSocket connection and price streaming"""
    try:
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("🚀 Starting WebSocket test...")
        
        # Start WebSocket connection
        websocket = start_websocket("BTC")
        
        # Wait for connection to establish
        logger.info("⏳ Waiting for WebSocket connection...")
        time.sleep(5)
        
        if websocket.is_connected():
            logger.success("✅ WebSocket connected successfully!")
            
            # Monitor price updates for 30 seconds
            logger.info("📡 Monitoring price updates for 30 seconds...")
            start_time = time.time()
            
            while time.time() - start_time < 30:
                price_data = websocket.get_price_data()
                
                if price_data["current_price"] > 0:
                    logger.info(f"💰 Price: ${price_data['current_price']:,.2f} | "
                              f"Bid: ${price_data['bid']:,.2f} | "
                              f"Ask: ${price_data['ask']:,.2f} | "
                              f"Status: {price_data['connection_status']}")
                else:
                    logger.warning("⚠️ No price data yet...")
                
                time.sleep(2)
            
            logger.success("✅ WebSocket test completed successfully!")
            
        else:
            logger.error("❌ WebSocket connection failed")
            
    except KeyboardInterrupt:
        logger.info("🛑 WebSocket test interrupted by user")
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")
    finally:
        stop_websocket()

if __name__ == "__main__":
    test_websocket()
