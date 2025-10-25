"""
Yahoo Finance API Service - Reimplemented with proper architecture
Provides DXY, Gold, and Stock market data for cross-asset correlation analysis
"""

import yfinance as yf
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

class YahooFinanceAPI:
    """Yahoo Finance API service for cross-asset data"""
    
    def __init__(self):
        """Initialize Yahoo Finance API service"""
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Minimum 1 second between requests
        
        # Data symbols (updated 2025-10-12: DX-Y.NYB and GC=F delisted, using UUP and GLD instead)
        self.symbols = {
            'dxy': 'UUP',       # DXY (US Dollar Index) - Invesco DB USD Index Bullish Fund ETF
            'gold': 'GLD',      # Gold - SPDR Gold Shares ETF (GC=F delisted)
            'spy': 'SPY',       # S&P 500 ETF
            'qqq': 'QQQ',       # NASDAQ ETF
            'dow': 'DIA',       # Dow Jones ETF
            'vix': '^VIX',       # VIX (Fear & Greed proxy) - original symbol
            'btc': 'BTC-USD',   # Bitcoin
            'eth': 'ETH-USD',   # Ethereum
            'gld': 'GLD',       # Gold ETF (same as gold)
            'slv': 'SLV'        # Silver ETF
        }
        
        logger.info("📊 Yahoo Finance API initialized")
    
    def _rate_limit(self):
        """Implement rate limiting to avoid API abuse"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if still valid"""
        return self._cache.get(key)
    
    def _set_cached_data(self, key: str, data: Dict[str, Any]):
        """Cache data with timestamp"""
        self._cache.set(key, data, ttl=300)  # 5 minutes cache
    
    def _fetch_yahoo_data(self, symbol: str, period: str = "5d") -> Optional[Dict[str, Any]]:
        """Fetch data from Yahoo Finance with error handling"""
        try:
            self._rate_limit()
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                logger.warning(f"⚠️ No data returned for {symbol}")
                return None
            
            # Get the latest data
            latest = hist.iloc[-1]
            previous = hist.iloc[-2] if len(hist) > 1 else latest
            
            # Calculate change over the period (not just daily)
            period_change = float((latest['Close'] - previous['Close']) / previous['Close'] * 100)
            daily_change = float((latest['Close'] - latest['Open']) / latest['Open'] * 100)
            
            # Get additional info
            info = ticker.info
            
            return {
                'symbol': symbol,
                'price': float(latest['Close']),
                'open': float(latest['Open']),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'volume': int(latest['Volume']),
                'change': float(latest['Close'] - latest['Open']),
                'change_percent': period_change,  # Use period change instead of daily
                'daily_change_percent': daily_change,  # Keep daily change for reference
                'timestamp': time.time(),
                'data_source': 'yahoo_finance',
                'name': info.get('longName', symbol),
                'currency': info.get('currency', 'USD'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'beta': info.get('beta', 0),
                'period_days': len(hist)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch Yahoo Finance data for {symbol}: {e}")
            return None
    
    def get_dxy_data(self) -> Dict[str, Any]:
        """Get DXY (US Dollar Index) data"""
        try:
            cache_key = "dxy_data"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                logger.debug("📊 Using cached DXY data")
                return cached_data
            
            logger.info("📊 Fetching fresh DXY data from Yahoo Finance")
            data = self._fetch_yahoo_data(self.symbols['dxy'])
            
            if data:
                self._set_cached_data(cache_key, data)
                logger.info(f"✅ DXY data fetched: ${data['price']:.2f} ({data['change_percent']:+.2f}%)")
                return data
            else:
                raise ValueError("No DXY data available from Yahoo Finance")
                
        except Exception as e:
            logger.error(f"❌ Failed to get DXY data: {e}")
            raise ValueError(f"DXY data fetch failed: {e}")
    
    def get_gold_data(self) -> Dict[str, Any]:
        """Get Gold price data"""
        try:
            cache_key = "gold_data"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                logger.debug("📊 Using cached Gold data")
                return cached_data
            
            logger.info("📊 Fetching fresh Gold data from Yahoo Finance")
            data = self._fetch_yahoo_data(self.symbols['gold'])
            
            if data:
                self._set_cached_data(cache_key, data)
                logger.info(f"✅ Gold data fetched: ${data['price']:.2f} ({data['change_percent']:+.2f}%)")
                return data
            else:
                raise ValueError("No Gold data available from Yahoo Finance")
                
        except Exception as e:
            logger.error(f"❌ Failed to get Gold data: {e}")
            raise ValueError(f"Gold data fetch failed: {e}")
    
    def get_stock_indices_data(self) -> Dict[str, Any]:
        """Get major stock indices data"""
        try:
            cache_key = "stock_indices_data"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                logger.debug("📊 Using cached Stock indices data")
                return cached_data
            
            logger.info("📊 Fetching fresh Stock indices data from Yahoo Finance")
            
            # Fetch multiple indices
            indices_data = {}
            
            for name, symbol in [('spy', 'SPY'), ('qqq', 'QQQ'), ('dow', 'DIA')]:
                data = self._fetch_yahoo_data(symbol)
                if data:
                    indices_data[name] = data
            
            if indices_data:
                # Calculate composite metrics
                composite_data = {
                    'indices': indices_data,
                    'composite_change': sum(data['change_percent'] for data in indices_data.values()) / len(indices_data),
                    'composite_price': sum(data['price'] for data in indices_data.values()) / len(indices_data),
                    'timestamp': time.time(),
                    'data_source': 'yahoo_finance',
                    'count': len(indices_data)
                }
                
                self._set_cached_data(cache_key, composite_data)
                logger.info(f"✅ Stock indices data fetched: {len(indices_data)} indices, composite change: {composite_data['composite_change']:+.2f}%")
                return composite_data
            else:
                raise ValueError("No Stock indices data available from Yahoo Finance")
                
        except Exception as e:
            logger.error(f"❌ Failed to get Stock indices data: {e}")
            raise ValueError(f"Stock indices data fetch failed: {e}")
    
    def get_all_cross_asset_data(self) -> Dict[str, Any]:
        """Get all cross-asset data in one call"""
        try:
            logger.info("📊 Fetching all cross-asset data from Yahoo Finance")
            
            dxy_data = self.get_dxy_data()
            gold_data = self.get_gold_data()
            stock_data = self.get_stock_indices_data()
            
            return {
                'dxy': dxy_data,
                'gold': gold_data,
                'stocks': stock_data,
                'timestamp': time.time(),
                'data_source': 'yahoo_finance',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get all cross-asset data: {e}")
            raise ValueError(f"Cross-asset data fetch failed: {e}")
    
    def get_fear_greed_data(self) -> Dict[str, Any]:
        """Get Fear & Greed Index using VIX as proxy"""
        try:
            cache_key = "fear_greed_data"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                logger.debug("📊 Using cached Fear & Greed data")
                return cached_data
            
            logger.info("📊 Fetching Fear & Greed data from Yahoo Finance (VIX proxy)")
            vix_data = self._fetch_yahoo_data(self.symbols['vix'])
            
            if vix_data:
                # Convert VIX to Fear & Greed scale (0-100)
                vix_value = vix_data['price']
                # VIX typically ranges 10-80, map to 0-100 Fear & Greed scale
                fear_greed_value = max(0, min(100, 100 - ((vix_value - 10) / 70 * 100)))
                
                # Determine sentiment
                if fear_greed_value >= 75:
                    sentiment = "EXTREME_GREED"
                elif fear_greed_value >= 55:
                    sentiment = "GREED"
                elif fear_greed_value >= 45:
                    sentiment = "NEUTRAL"
                elif fear_greed_value >= 25:
                    sentiment = "FEAR"
                else:
                    sentiment = "EXTREME_FEAR"
                
                fear_greed_data = {
                    'index_value': int(fear_greed_value),
                    'sentiment': sentiment,
                    'vix_value': vix_value,
                    'timestamp': time.time(),
                    'data_source': 'yahoo_finance_vix',
                    'confidence': 0.8,  # VIX is a good proxy but not perfect
                    'sentiment_signals': {
                        'market_volatility': 'HIGH' if vix_value > 30 else 'NORMAL',
                        'risk_appetite': 'LOW' if vix_value > 25 else 'NORMAL',
                        'trading_bias': 'DEFENSIVE' if vix_value > 30 else 'NORMAL'
                    }
                }
                
                self._set_cached_data(cache_key, fear_greed_data)
                logger.info(f"✅ Fear & Greed data fetched: {sentiment} ({fear_greed_value:.0f}/100)")
                return fear_greed_data
            else:
                raise ValueError("No VIX data available from Yahoo Finance")
                
        except Exception as e:
            logger.error(f"❌ Failed to get Fear & Greed data: {e}")
            raise ValueError(f"Fear & Greed data fetch failed: {e}")
    
    def test_connection(self) -> bool:
        """Test Yahoo Finance API connection"""
        try:
            logger.info("🔍 Testing Yahoo Finance API connection...")
            
            # Test with a simple request
            test_data = self._fetch_yahoo_data('SPY', '1d')
            
            if test_data and 'price' in test_data:
                logger.info("✅ Yahoo Finance API connection successful")
                return True
            else:
                logger.error("❌ Yahoo Finance API connection failed - no data returned")
                return False
                
        except Exception as e:
            logger.error(f"❌ Yahoo Finance API connection test failed: {e}")
            return False

# Global instance for singleton pattern
_yahoo_finance_api_instance = None
_yahoo_finance_api_lock = threading.Lock()

def get_global_yahoo_finance_api() -> YahooFinanceAPI:
    """Get global Yahoo Finance API instance (singleton)"""
    global _yahoo_finance_api_instance
    
    if _yahoo_finance_api_instance is None:
        with _yahoo_finance_api_lock:
            if _yahoo_finance_api_instance is None:
                _yahoo_finance_api_instance = YahooFinanceAPI()
                logger.info("🌐 Global Yahoo Finance API instance created")
    
    return _yahoo_finance_api_instance
