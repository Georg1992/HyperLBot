#!/usr/bin/env python3
"""
Real-Time BTC Volume Fetcher
Provides actual real-time BTC trading volume data from multiple sources
Similar to Hyperliquid's 5-minute volume display but using real trading data
"""

import time
import statistics
import requests
import json
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class RealtimeVolumeFetcher:
    """
    Fetches real-time BTC trading volume from multiple sources
    Provides current 5-minute volume similar to Hyperliquid display
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 3  # 3 seconds cache for real-time updates
        
        # Real-time volume APIs
        self.apis = {
            "binance": {
                "url": "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
                "free": True,
                "rate_limit": "1200 requests per minute"
            },
            "cryptocompare": {
                "url": "https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=5",
                "free": True,
                "rate_limit": "100,000 requests per month"
            },
            "coingecko": {
                "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_vol=true",
                "free": True,
                "rate_limit": "50 calls per minute"
            }
        }
        
        # Volume history for 5-minute calculation
        self.volume_history = []
        self.last_5m_reset = time.time()
        
        logger.info("📊 Real-Time Volume Fetcher initialized")
    
    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """Get cached data if still valid"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_duration:
                return data
        return None
    
    def _cache_data(self, key: str, data: Dict):
        """Cache data with timestamp"""
        self.cache[key] = (data, time.time())
    
    def get_binance_volume(self) -> Dict[str, Any]:
        """Get real-time volume from Binance"""
        try:
            cache_key = "binance_volume"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            response = requests.get(self.apis["binance"]["url"], timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                volume_data = {
                    "source": "binance",
                    "volume_24h": float(data.get("volume", 0)),
                    "quote_volume_24h": float(data.get("quoteVolume", 0)),
                    "timestamp": time.time(),
                    "status": "success"
                }
                
                self._cache_data(cache_key, volume_data)
                return volume_data
            else:
                return {
                    "source": "binance",
                    "error": f"HTTP {response.status_code}",
                    "status": "error"
                }
                
        except Exception as e:
            logger.error(f"Binance API error: {e}")
            return {
                "source": "binance",
                "error": str(e),
                "status": "error"
            }
    
    def get_cryptocompare_volume(self) -> Dict[str, Any]:
        """Get recent volume from CryptoCompare"""
        try:
            cache_key = "cryptocompare_volume"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            response = requests.get(self.apis["cryptocompare"]["url"], timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("Response") == "Success" and data.get("Data", {}).get("Data"):
                    candles = data["Data"]["Data"]
                    if len(candles) >= 5:
                        # Calculate 5-minute volume from recent candles
                        recent_volume = sum([candle.get("volumeto", 0) for candle in candles[-5:]])
                        current_volume = candles[-1].get("volumeto", 0) if candles else 0
                        
                        volume_data = {
                            "source": "cryptocompare",
                            "volume_5m": recent_volume,
                            "current_volume": current_volume,
                            "timestamp": time.time(),
                            "status": "success"
                        }
                        
                        self._cache_data(cache_key, volume_data)
                        return volume_data
            
            return {
                "source": "cryptocompare",
                "error": "No data available",
                "status": "error"
            }
                
        except Exception as e:
            logger.error(f"CryptoCompare API error: {e}")
            return {
                "source": "cryptocompare",
                "error": str(e),
                "status": "error"
            }
    
    def get_coingecko_volume(self) -> Dict[str, Any]:
        """Get volume from CoinGecko"""
        try:
            cache_key = "coingecko_volume"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            response = requests.get(self.apis["coingecko"]["url"], timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                volume_data = {
                    "source": "coingecko",
                    "volume_24h": float(data.get("bitcoin", {}).get("usd_24h_vol", 0)),
                    "timestamp": time.time(),
                    "status": "success"
                }
                
                self._cache_data(cache_key, volume_data)
                return volume_data
            else:
                return {
                    "source": "coingecko",
                    "error": f"HTTP {response.status_code}",
                    "status": "error"
                }
                
        except Exception as e:
            logger.error(f"CoinGecko API error: {e}")
            return {
                "source": "coingecko",
                "error": str(e),
                "status": "error"
            }
    
    def get_current_5m_volume(self) -> Dict[str, Any]:
        """
        Get current 5-minute volume similar to Hyperliquid display
        Returns volume that resets every 5 minutes
        """
        try:
            current_time = time.time()
            
            # Check if we need to reset 5-minute window
            if current_time - self.last_5m_reset >= 300:  # 5 minutes
                self.volume_history = []
                self.last_5m_reset = current_time
                logger.debug("🔄 Resetting 5-minute volume window")
            
            # Get volume from multiple sources
            binance_data = self.get_binance_volume()
            cryptocompare_data = self.get_cryptocompare_volume()
            coingecko_data = self.get_coingecko_volume()
            
            # Calculate current 5-minute volume
            current_volume = 0
            volume_sources = []
            
            if binance_data.get("status") == "success":
                # Estimate current 5-minute volume from 24h volume
                volume_24h = binance_data.get("volume_24h", 0)
                estimated_5m_volume = (volume_24h / 24 / 60 / 12)  # 24h / 24 hours / 60 minutes / 12 (5-min intervals)
                current_volume = estimated_5m_volume
                volume_sources.append(("binance", estimated_5m_volume))
            
            if cryptocompare_data.get("status") == "success":
                cryptocompare_volume = cryptocompare_data.get("current_volume", 0)
                if cryptocompare_volume > 0:
                    current_volume = cryptocompare_volume  # Use CryptoCompare as primary source
                    volume_sources.append(("cryptocompare", cryptocompare_volume))
            
            if coingecko_data.get("status") == "success":
                coingecko_volume = coingecko_data.get("volume_24h", 0)
                estimated_5m_volume = (coingecko_volume / 24 / 60 / 12)
                volume_sources.append(("coingecko", estimated_5m_volume))
            
            # Add to history for tracking
            if current_volume > 0:
                self.volume_history.append({
                    "volume": current_volume,
                    "timestamp": current_time,
                    "sources": volume_sources
                })
            
            # Keep only last 5 minutes of history
            cutoff_time = current_time - 300
            self.volume_history = [entry for entry in self.volume_history if entry["timestamp"] > cutoff_time]
            
            # Calculate 5-minute cumulative volume
            cumulative_5m_volume = sum([entry["volume"] for entry in self.volume_history])
            
            # Determine volume category based on Hyperliquid-like ranges
            volume_category = self._determine_volume_category(cumulative_5m_volume)
            
            # Check for volume spikes
            has_spike = False
            spike_severity = "NORMAL"
            if len(self.volume_history) >= 2:
                recent_volumes = [entry["volume"] for entry in self.volume_history[-2:]]
                avg_volume = statistics.mean(recent_volumes)
                if current_volume > avg_volume * 2:  # 2x average
                    has_spike = True
                    if current_volume > avg_volume * 5:
                        spike_severity = "EXTREMELY_HIGH"
                    elif current_volume > avg_volume * 3:
                        spike_severity = "HIGH"
                    else:
                        spike_severity = "MODERATE"
            
            result = {
                "current_volume": current_volume,
                "cumulative_5m_volume": cumulative_5m_volume,
                "volume_category": volume_category,
                "has_spike": has_spike,
                "spike_severity": spike_severity,
                "volume_trend": self._determine_volume_trend(),
                "sources_used": [source[0] for source in volume_sources],
                "timestamp": current_time,
                "time_since_reset": current_time - self.last_5m_reset,
                "status": "success"
            }
            
            logger.debug(f"📊 Real-time volume: {current_volume:.1f} BTC (5m cumulative: {cumulative_5m_volume:.1f}) - {volume_category}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting current 5m volume: {e}")
            return {
                "current_volume": 0,
                "cumulative_5m_volume": 0,
                "volume_category": "UNKNOWN",
                "has_spike": False,
                "spike_severity": "NORMAL",
                "volume_trend": "UNKNOWN",
                "sources_used": [],
                "timestamp": time.time(),
                "time_since_reset": 0,
                "status": "error",
                "error": str(e)
            }
    
    def _determine_volume_category(self, volume: float) -> str:
        """Determine volume category based on Hyperliquid-like ranges"""
        if volume >= 4000:
            return "CRAZY_HIGH"
        elif volume >= 1000:
            return "HIGH"
        elif volume >= 500:
            return "MODERATE"
        elif volume >= 100:
            return "NORMAL"
        elif volume >= 50:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _determine_volume_trend(self) -> str:
        """Determine volume trend based on recent history"""
        if len(self.volume_history) < 3:
            return "UNKNOWN"
        
        recent_volumes = [entry["volume"] for entry in self.volume_history[-3:]]
        
        if len(recent_volumes) >= 2:
            if recent_volumes[-1] > recent_volumes[-2] * 1.2:
                return "INCREASING"
            elif recent_volumes[-1] < recent_volumes[-2] * 0.8:
                return "DECREASING"
            else:
                return "STABLE"
        
        return "UNKNOWN"


def main():
    """Test the real-time volume fetcher"""
    logger.info("🔍 Testing Real-Time Volume Fetcher")
    logger.info("=" * 60)
    
    fetcher = RealtimeVolumeFetcher()
    
    # Test individual APIs
    logger.info("📊 Testing individual APIs...")
    
    binance_data = fetcher.get_binance_volume()
    logger.info(f"Binance: {binance_data.get('status', 'error')} - Volume: {binance_data.get('volume_24h', 0):.1f}")
    
    cryptocompare_data = fetcher.get_cryptocompare_volume()
    logger.info(f"CryptoCompare: {cryptocompare_data.get('status', 'error')} - Current: {cryptocompare_data.get('current_volume', 0):.1f}")
    
    coingecko_data = fetcher.get_coingecko_volume()
    logger.info(f"CoinGecko: {coingecko_data.get('status', 'error')} - Volume: {coingecko_data.get('volume_24h', 0):.1f}")
    
    # Test current 5m volume
    logger.info("\n📈 Testing current 5m volume...")
    for i in range(3):
        volume_data = fetcher.get_current_5m_volume()
        
        if volume_data.get("status") == "success":
            logger.success(f"✅ 5m Volume Update {i+1}:")
            logger.info(f"   Current Volume: {volume_data['current_volume']:.1f} BTC")
            logger.info(f"   Cumulative 5m: {volume_data['cumulative_5m_volume']:.1f} BTC")
            logger.info(f"   Category: {volume_data['volume_category']}")
            logger.info(f"   Trend: {volume_data['volume_trend']}")
            logger.info(f"   Sources: {', '.join(volume_data['sources_used'])}")
            logger.info(f"   Has Spike: {volume_data['has_spike']} ({volume_data['spike_severity']})")
        else:
            logger.error(f"❌ Volume update {i+1} failed: {volume_data.get('error', 'Unknown error')}")
        
        if i < 2:  # Don't sleep after last iteration
            time.sleep(2)


if __name__ == "__main__":
    main()
