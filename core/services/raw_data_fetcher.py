#!/usr/bin/env python3
"""
Raw Data Fetcher - Unified data fetching layer
Fetches ALL raw API data upfront in parallel before analysis begins

Single Responsibility: Fetch all raw external API data
NO FALLBACKS: All data is mandatory - if any API fails, raise immediately
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional
from loguru import logger
from config.config import TradingConfig


class RawDataFetcher:
    """
    Unified data fetching service that fetches all raw API data in parallel
    
    All data is MANDATORY - NO FALLBACKS policy enforced.
    If any API fails, the entire fetch operation raises.
    """
    
    def __init__(
        self,
        hyperliquid_api,
        hyperliquid_websocket,
        binance_api=None,
        binance_websocket=None,
        fear_greed_api=None,
        whale_analytics_api=None,
        rss_news_api=None
    ):
        """
        Initialize RawDataFetcher with all API instances
        
        Args:
            hyperliquid_api: HyperliquidAPI instance (required)
            hyperliquid_websocket: HyperliquidWebSocket instance (required)
            binance_api: BinanceAPI instance (optional, for volume data)
            binance_websocket: BinanceWebSocket instance (optional)
            fear_greed_api: FearGreedAPI instance (required)
            whale_analytics_api: WhaleAnalyticsAPI instance (required)
            rss_news_api: RSSNewsAPI instance (required)
        """
        self.hyperliquid_api = hyperliquid_api
        self.hyperliquid_websocket = hyperliquid_websocket
        self.binance_api = binance_api
        self.binance_websocket = binance_websocket
        self.fear_greed_api = fear_greed_api
        self.whale_analytics_api = whale_analytics_api
        self.rss_news_api = rss_news_api
        
        # Validate required APIs
        if not self.hyperliquid_api:
            raise ValueError("HyperliquidAPI is required (NO FALLBACKS)")
        if not self.hyperliquid_websocket:
            raise ValueError("HyperliquidWebSocket is required (NO FALLBACKS)")
        if not self.fear_greed_api:
            raise ValueError("FearGreedAPI is required (NO FALLBACKS)")
        if not self.whale_analytics_api:
            raise ValueError("WhaleAnalyticsAPI is required (NO FALLBACKS)")
        if not self.rss_news_api:
            raise ValueError("RSSNewsAPI is required (NO FALLBACKS)")
        
        logger.info("📡 Raw Data Fetcher initialized - All data is mandatory (NO FALLBACKS)")
    
    def fetch_all_raw_data(self) -> Dict[str, Any]:
        """
        Fetch ALL raw API data in parallel
        
        Architecture:
        - API methods handle their own caching via CentralizedCache.get_or_set()
        - RawDataFetcher orchestrates fetching - Single Responsibility Principle
        - Caching logic is centralized in API methods - DRY principle
        
        LIVE DATA (always fetched, never cached):
        - price: From WebSocket live stream (real-time updates)
        - orderbook: From WebSocket/API (real-time updates)
        - funding: From API (changes every 8 hours, but fetched every iteration for accuracy)
        
        CACHED DATA (API methods respect TTLs from CentralizedCache):
        - fear_greed: 10 min TTL (600s) - handled by FearGreedAPI.get_fear_greed_index()
        - whale: 5 min TTL (300s) - handled by WhaleAnalyticsAPI.get_processed_whale_data()
        - news: 5 min TTL (300s) - handled by RSSNewsAPI.get_news_sentiment()
        - cross_asset: 5 min TTL (300s) - handled by YahooFinanceAPI methods
        
        All data is MANDATORY - if any fetch fails, raises immediately (NO FALLBACKS)
        
        Returns:
            Dict containing all raw API data:
            - price: Current price (float)
            - orderbook: Orderbook data (dict)
            - funding: Funding rate data (dict)
            - fear_greed: Fear & Greed Index data (dict)
            - whale: Processed whale data (dict with whale_activity, exchange_flows, sentiment)
            - news: RSS news sentiment data (dict)
            - cross_asset: Cross-asset correlation data (dict)
        
        Raises:
            ValueError: If any required API fetch fails
        """
        try:
            logger.debug("📡 Starting parallel fetch of all raw API data...")
            start_time = time.time()
            
            # Fetch all data in parallel using ThreadPoolExecutor
            # API methods handle caching internally via get_or_set pattern
            with ThreadPoolExecutor(max_workers=8) as executor:
                # Submit all fetch tasks
                futures = {
                    "price": executor.submit(self._fetch_price),
                    "orderbook": executor.submit(self._fetch_orderbook),
                    "funding": executor.submit(self._fetch_funding),
                    "fear_greed": executor.submit(self._fetch_fear_greed),
                    "whale": executor.submit(self._fetch_whale),
                    "news": executor.submit(self._fetch_news),
                    "cross_asset": executor.submit(self._fetch_cross_asset),
                }
                
                # Collect results - all are mandatory (NO FALLBACKS)
                raw_data = {}
                errors = {}
                
                for data_type, future in futures.items():
                    try:
                        result = future.result(timeout=30)  # 30 second timeout per API
                        if result is None:
                            raise ValueError(f"{data_type} fetch returned None (NO FALLBACKS)")
                        raw_data[data_type] = result
                    except Exception as e:
                        errors[data_type] = str(e)
                        logger.error(f"❌ Failed to fetch {data_type}: {e}")
                
                # If any fetch failed, raise immediately (NO FALLBACKS)
                if errors:
                    error_msg = f"Raw data fetch failed for: {', '.join(errors.keys())} (NO FALLBACKS)"
                    logger.error(f"❌ {error_msg}")
                    for data_type, error in errors.items():
                        logger.error(f"   - {data_type}: {error}")
                    raise ValueError(error_msg)
            
            elapsed = time.time() - start_time
            logger.debug(f"✅ All raw API data fetched in {elapsed:.2f}s")
            
            return raw_data
            
        except Exception as e:
            logger.error(f"❌ Raw data fetch operation failed: {e}")
            raise
    
    def _fetch_price(self) -> float:
        """Fetch current price from WebSocket or API"""
        try:
            # Try WebSocket first (fastest, real-time)
            if self.hyperliquid_websocket:
                price = self.hyperliquid_websocket.get_current_price()
                if price and price > 0:
                    return price
            
            # Fallback to API if WebSocket not available
            if self.hyperliquid_api:
                price = self.hyperliquid_api.get_current_price(TradingConfig.SYMBOL)
                if price and price > 0:
                    return price
            
            raise ValueError("No valid price available from WebSocket or API (NO FALLBACKS)")
            
        except Exception as e:
            logger.error(f"❌ Price fetch failed: {e}")
            raise ValueError(f"Price fetch failed: {e} (NO FALLBACKS)")
    
    def _fetch_orderbook(self) -> Dict[str, Any]:
        """Fetch orderbook data from Hyperliquid API"""
        try:
            if not self.hyperliquid_api:
                raise ValueError("HyperliquidAPI not available (NO FALLBACKS)")
            
            orderbook = self.hyperliquid_api.get_market_data(TradingConfig.SYMBOL)
            if not orderbook:
                raise ValueError("Orderbook data is empty (NO FALLBACKS)")
            
            return orderbook
            
        except Exception as e:
            logger.error(f"❌ Orderbook fetch failed: {e}")
            raise ValueError(f"Orderbook fetch failed: {e} (NO FALLBACKS)")
    
    def _fetch_funding(self) -> Dict[str, Any]:
        """Fetch funding rate from Hyperliquid API"""
        try:
            if not self.hyperliquid_api:
                raise ValueError("HyperliquidAPI not available for funding rate (NO FALLBACKS)")
            
            funding = self.hyperliquid_api.get_funding_rate(TradingConfig.SYMBOL)
            if not funding:
                raise ValueError("Funding rate data is empty (NO FALLBACKS)")
            
            return funding
            
        except Exception as e:
            logger.error(f"❌ Funding rate fetch failed: {e}")
            raise ValueError(f"Funding rate fetch failed: {e} (NO FALLBACKS)")
    
    def _fetch_fear_greed(self) -> Dict[str, Any]:
        """Fetch Fear & Greed Index from external API"""
        try:
            if not self.fear_greed_api:
                raise ValueError("FearGreedAPI not available (NO FALLBACKS)")
            
            fear_greed = self.fear_greed_api.get_fear_greed_index()
            if not fear_greed:
                raise ValueError("Fear & Greed data is empty (NO FALLBACKS)")
            
            # Validate required keys (API returns 'sentiment', not 'classification')
            required_keys = ["index_value", "sentiment", "sentiment_signals"]
            for key in required_keys:
                if key not in fear_greed:
                    raise ValueError(f"Fear & Greed data missing required key: {key} (NO FALLBACKS)")
            
            return fear_greed
            
        except Exception as e:
            logger.error(f"❌ Fear & Greed fetch failed: {e}")
            raise ValueError(f"Fear & Greed fetch failed: {e} (NO FALLBACKS)")
    
    def _fetch_whale(self) -> Dict[str, Any]:
        """
        Fetch processed whale data from BlockCypher API
        
        Returns processed whale data in format expected by analyzers:
        - whale_activity: {whale_count, activity_level, ...}
        - exchange_flows: {flow_direction, ...}
        - sentiment: {classification, ...}
        """
        try:
            if not self.whale_analytics_api:
                raise ValueError("WhaleAnalyticsAPI not available (NO FALLBACKS)")
            
            # Get processed whale data (includes analysis structure)
            whale_data = self.whale_analytics_api.get_processed_whale_data()
            if whale_data is None:
                raise ValueError("Processed whale data is None (NO FALLBACKS)")
            
            # Validate required structure (NO FALLBACKS)
            required_keys = ["whale_activity", "exchange_flows", "sentiment"]
            for key in required_keys:
                if key not in whale_data:
                    raise ValueError(f"Whale data missing required key: {key} (NO FALLBACKS)")
            
            return whale_data
            
        except Exception as e:
            logger.error(f"❌ Whale data fetch failed: {e}")
            raise ValueError(f"Whale data fetch failed: {e} (NO FALLBACKS)")
    
    def _fetch_news(self) -> Dict[str, Any]:
        """Fetch RSS news sentiment from external APIs"""
        try:
            if not self.rss_news_api:
                raise ValueError("RSSNewsAPI not available (NO FALLBACKS)")
            
            news = self.rss_news_api.get_news_sentiment()
            if not news:
                raise ValueError("News sentiment data is empty (NO FALLBACKS)")
            
            # Validate required keys
            required_keys = ["sentiment", "impact", "trading_signals"]
            for key in required_keys:
                if key not in news:
                    raise ValueError(f"News data missing required key: {key} (NO FALLBACKS)")
            
            return news
            
        except Exception as e:
            logger.error(f"❌ News sentiment fetch failed: {e}")
            raise ValueError(f"News sentiment fetch failed: {e} (NO FALLBACKS)")
    
    def _fetch_cross_asset(self) -> Dict[str, Any]:
        """Fetch cross-asset correlation data from Yahoo Finance API"""
        try:
            from core.external.yahoo_finance_api import get_global_yahoo_finance_api
            yahoo_api = get_global_yahoo_finance_api()
            
            # Fetch all cross-asset data
            cross_asset = {
                "dxy": yahoo_api.get_dxy_data(),
                "gold": yahoo_api.get_gold_data(),
                "stocks": yahoo_api.get_stock_indices_data(),
                "timestamp": time.time(),
                "data_source": "yahoo_finance"
            }
            
            # Validate all data is present
            if not cross_asset["dxy"]:
                raise ValueError("DXY data is empty (NO FALLBACKS)")
            if not cross_asset["gold"]:
                raise ValueError("Gold data is empty (NO FALLBACKS)")
            if not cross_asset["stocks"]:
                raise ValueError("Stock indices data is empty (NO FALLBACKS)")
            
            return cross_asset
            
        except Exception as e:
            logger.error(f"❌ Cross-asset data fetch failed: {e}")
            raise ValueError(f"Cross-asset data fetch failed: {e} (NO FALLBACKS)")


# Factory function for dependency injection
def create_raw_data_fetcher(
    hyperliquid_api,
    hyperliquid_websocket,
    binance_api=None,
    binance_websocket=None,
    fear_greed_api=None,
    whale_analytics_api=None,
    rss_news_api=None
) -> RawDataFetcher:
    """
    Factory function to create RawDataFetcher with dependency injection
    
    Args:
        hyperliquid_api: HyperliquidAPI instance (required)
        hyperliquid_websocket: HyperliquidWebSocket instance (required)
        binance_api: BinanceAPI instance (optional)
        binance_websocket: BinanceWebSocket instance (optional)
        fear_greed_api: FearGreedAPI instance (required)
        whale_analytics_api: WhaleAnalyticsAPI instance (required)
        rss_news_api: RSSNewsAPI instance (required)
    
    Returns:
        RawDataFetcher instance
    """
    return RawDataFetcher(
        hyperliquid_api=hyperliquid_api,
        hyperliquid_websocket=hyperliquid_websocket,
        binance_api=binance_api,
        binance_websocket=binance_websocket,
        fear_greed_api=fear_greed_api,
        whale_analytics_api=whale_analytics_api,
        rss_news_api=rss_news_api
    )
