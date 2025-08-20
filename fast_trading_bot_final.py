#!/usr/bin/env python3
"""
Fast Trading Bot for Hyperliquid - FINAL VERSION
Executes quick trades with high leverage and proper order signing
"""

import time
import json
from typing import Dict, Any, Optional
from loguru import logger
from hyperliquid_api import HyperliquidAPI
from config import TradingConfig

class FastTradingBot:
    def __init__(self):
        self.config = TradingConfig()
        self.api = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to Hyperliquid API"""
        try:
            logger.info("🔌 Connecting to Hyperliquid...")
            
            # Check if wallet credentials are set
            if not self.config.WALLET_ADDRESS or not self.config.WALLET_PRIVATE_KEY:
                logger.error("Wallet credentials not found. Please set WALLET_ADDRESS and WALLET_PRIVATE_KEY in .env file")
                return False
            
            # Initialize API client
            self.api = HyperliquidAPI(self.config.WALLET_ADDRESS, self.config.WALLET_PRIVATE_KEY)
            
            # Test connection by getting account info
            account_info = self.api.get_account_info()
            logger.success(f"✅ Successfully connected to Hyperliquid!")
            
            # Display account balance
            if 'data' in account_info and 'marginSummary' in account_info['data']:
                margin = account_info['data']['marginSummary']
                account_value = margin.get('accountValue', 0)
                logger.info(f"💰 Account Value: ${account_value:.2f} USD")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def get_current_price(self, symbol: str = "BTC") -> Optional[float]:
        """Get current market price for a symbol"""
        try:
            # Get order book data to calculate current price
            market_data = self.api.get_market_data(symbol)
            
            if market_data and 'levels' in market_data and len(market_data['levels']) >= 2:
                # Get best bid and ask
                bids = market_data['levels'][0]  # First level is bids
                asks = market_data['levels'][1]  # Second level is asks
                
                if bids and asks:
                    best_bid = float(bids[0]['px'])
                    best_ask = float(asks[0]['px'])
                    mid_price = (best_bid + best_ask) / 2
                    logger.info(f"📊 Current {symbol} mid-price: ${mid_price:,.2f} (Bid: ${best_bid:,.2f}, Ask: ${best_ask:,.2f})")
                    return mid_price
                else:
                    logger.error(f"❌ No bid/ask data found for {symbol}")
            else:
                logger.error(f"❌ Invalid market data structure for {symbol}")
            
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get {symbol} price: {e}")
            return None
    
    def place_limit_sell_order(self, symbol: str = "BTC", size: float = 0.001, leverage: int = 30) -> bool:
        """Place a limit sell order at current market price with specified leverage"""
        try:
            # Get current price
            current_price = self.get_current_price(symbol)
            if not current_price:
                logger.error("❌ Could not get current price")
                return False
            
            # Calculate order parameters
            limit_price = current_price  # Sell at current market price
            side = "B"  # B for sell (Hyperliquid uses B for sell, A for buy)
            
            logger.info(f"🚀 Placing limit sell order:")
            logger.info(f"   Symbol: {symbol}")
            logger.info(f"   Size: {size}")
            logger.info(f"   Price: ${limit_price:,.2f}")
            logger.info(f"   Leverage: {leverage}x")
            logger.info(f"   Side: Sell (B)")
            
            # Place the order with proper signing
            order_result = self.api.place_order(
                symbol=symbol,
                side=side,
                size=size,
                price=limit_price,
                order_type="Limit",
                leverage=leverage
            )
            
            if order_result and 'status' in order_result and order_result['status'] == 'ok':
                logger.success(f"✅ Limit sell order placed successfully!")
                logger.info(f"   Order ID: {order_result.get('response', {}).get('data', {}).get('hash', 'N/A')}")
                return True
            else:
                logger.error(f"❌ Order placement failed: {order_result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to place limit sell order: {e}")
            return False
    
    def place_market_sell_order(self, symbol: str = "BTC", size: float = 0.001, leverage: int = 30) -> bool:
        """Place a market sell order with specified leverage"""
        try:
            side = "B"  # B for sell (Hyperliquid uses B for sell, A for buy)
            
            logger.info(f"🚀 Placing market sell order:")
            logger.info(f"   Symbol: {symbol}")
            logger.info(f"   Size: {size}")
            logger.info(f"   Leverage: {leverage}x")
            logger.info(f"   Side: Sell (B)")
            
            # Place the order with proper signing
            order_result = self.api.place_order(
                symbol=symbol,
                side=side,
                size=size,
                order_type="Market",
                leverage=leverage
            )
            
            if order_result and 'status' in order_result and order_result['status'] == 'ok':
                logger.success(f"✅ Market sell order placed successfully!")
                logger.info(f"   Order ID: {order_result.get('response', {}).get('data', {}).get('hash', 'N/A')}")
                return True
            else:
                logger.error(f"❌ Order placement failed: {order_result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to place market sell order: {e}")
            return False
    
    def execute_fast_trades(self, symbol: str = "BTC", trade_count: int = 2, size: float = 0.001, leverage: int = 30, order_type: str = "LIMIT"):
        """Execute multiple fast sell trades"""
        if not self.connected:
            logger.error("❌ Not connected to Hyperliquid")
            return
        
        logger.info(f"🚀 Starting fast SELL trading session:")
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Trade Count: {trade_count}")
        logger.info(f"   Size per trade: {size}")
        logger.info(f"   Leverage: {leverage}x")
        logger.info(f"   Order Type: {order_type}")
        logger.info(f"   Side: SELL ONLY")
        logger.info("=" * 50)
        
        successful_trades = 0
        
        for i in range(trade_count):
            logger.info(f"📈 Sell Trade {i+1}/{trade_count}")
            
            # Place sell order based on type
            if order_type.upper() == "LIMIT":
                success = self.place_limit_sell_order(symbol, size, leverage)
            else:
                success = self.place_market_sell_order(symbol, size, leverage)
            
            if success:
                successful_trades += 1
                logger.info(f"   ✅ Sell order {i+1} placed successfully")
            else:
                logger.error(f"   ❌ Sell order {i+1} failed")
            
            # Delay between trades
            if i < trade_count - 1:
                time.sleep(2)
        
        logger.info("=" * 50)
        logger.success(f"🎯 Fast SELL trading session completed!")
        logger.info(f"   Successful sell orders: {successful_trades}/{trade_count}")
        
        # Show final account status
        try:
            account_info = self.api.get_account_info()
            if 'data' in account_info and 'marginSummary' in account_info['data']:
                margin = account_info['data']['marginSummary']
                account_value = margin.get('accountValue', 0)
                logger.info(f"💰 Final Account Value: ${account_value:.2f} USD")
        except Exception as e:
            logger.error(f"❌ Could not get final account status: {e}")

def main():
    """Main function to run the fast trading bot"""
    logger.info("🤖 Hyperliquid Fast Trading Bot - FINAL VERSION")
    logger.info("🔐 Order signing enabled")
    
    # Initialize bot
    bot = FastTradingBot()
    
    # Connect to Hyperliquid
    if not bot.connect():
        logger.error("❌ Failed to connect to Hyperliquid")
        return
    
    # Execute fast sell trades
    # Parameters: symbol, trade_count, size_per_trade, leverage, order_type
    bot.execute_fast_trades(
        symbol="BTC",
        trade_count=2,      # Number of sell orders
        size=0.001,         # Size in BTC (very small for testing)
        leverage=30,        # 30x leverage as requested
        order_type="LIMIT"  # LIMIT or MARKET
    )

if __name__ == "__main__":
    main()
