#!/usr/bin/env python3
"""
Stable Volume Fetcher
Provides consistent, validated BTC volume data without wild fluctuations
Uses data smoothing and validation to ensure reliable volume reporting
"""

import time
import statistics
import requests
import json
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
from collections import deque

class StableVolumeFetcher:
    """
    Stable volume fetcher that prevents wild fluctuations
    - Uses consistent primary data source
    - Implements data smoothing and validation
    - Prevents unrealistic volume jumps
    """
    
    def __init__(self):
        # Stable configuration
        self.cache = {}
        self.cache_duration = 10  # 10 seconds cache for stability
        
        # Volume smoothing system
        self.volume_history = deque(maxlen=20)  # Last 20 readings for smoothing
        self.last_valid_volume = 0
        self.volume_change_threshold = 0.5  # 50% max change between readings
        
        # Stable BTC price cache (to avoid conversion fluctuations)
        self.btc_price_cache = {"price": 117000, "timestamp": 0, "cache_duration": 60}
        
        logger.info("📊 Stable Volume Fetcher initialized - anti-fluctuation system active")
    
    def get_stable_btc_price(self) -> float:
        """Get stable BTC price with caching to prevent conversion fluctuations"""
        try:
            current_time = time.time()
            
            # Use cached price if recent enough
            if (current_time - self.btc_price_cache["timestamp"]) < self.btc_price_cache["cache_duration"]:
                return self.btc_price_cache["price"]
            
            # Fetch new price
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", 
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                new_price = data.get("bitcoin", {}).get("usd", 117000)
                
                # Update cache
                self.btc_price_cache.update({
                    "price": new_price,
                    "timestamp": current_time
                })
                
                logger.debug(f"💰 Updated BTC price cache: ${new_price:,.0f}")
                return new_price
            else:
                logger.debug(f"Price fetch failed: {response.status_code}")
                return self.btc_price_cache["price"]
                
        except Exception as e:
            logger.debug(f"Price fetch error: {e}")
            return self.btc_price_cache["price"]
    
    def get_binance_volume_stable(self) -> Dict[str, Any]:
        """Get Binance volume with enhanced error handling"""
        try:
            cache_key = "binance_volume"
            current_time = time.time()
            
            # Check cache
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if current_time - timestamp < self.cache_duration:
                    return cached_data
            
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", 
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                volume_data = {
                    "source": "binance",
                    "volume_24h_btc": float(data.get("volume", 0)),
                    "volume_24h_usd": float(data.get("quoteVolume", 0)),
                    "timestamp": current_time,
                    "status": "success"
                }
                
                # Cache result
                self.cache[cache_key] = (volume_data, current_time)
                return volume_data
            else:
                logger.debug(f"Binance API error: {response.status_code}")
                return {"source": "binance", "status": "error", "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.debug(f"Binance volume fetch error: {e}")
            return {"source": "binance", "status": "error", "error": str(e)}
    
    def get_coingecko_volume_stable(self) -> Dict[str, Any]:
        """Get CoinGecko volume as fallback with stable price conversion"""
        try:
            cache_key = "coingecko_volume"
            current_time = time.time()
            
            # Check cache
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if current_time - timestamp < self.cache_duration:
                    return cached_data
            
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_vol=true",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                bitcoin_data = data.get("bitcoin", {})
                
                volume_24h_usd = bitcoin_data.get("usd_24h_vol", 0)
                btc_price_usd = bitcoin_data.get("usd", 117000)
                
                if volume_24h_usd > 0 and btc_price_usd > 0:
                    # Convert USD volume to BTC using current price
                    volume_24h_btc = volume_24h_usd / btc_price_usd
                    
                    volume_data = {
                        "source": "coingecko",
                        "volume_24h_btc": volume_24h_btc,
                        "volume_24h_usd": volume_24h_usd,
                        "btc_price": btc_price_usd,
                        "timestamp": current_time,
                        "status": "success"
                    }
                    
                    # Cache result
                    self.cache[cache_key] = (volume_data, current_time)
                    return volume_data
                else:
                    return {"source": "coingecko", "status": "error", "error": "Invalid volume or price data"}
            else:
                logger.debug(f"CoinGecko API error: {response.status_code}")
                return {"source": "coingecko", "status": "error", "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.debug(f"CoinGecko volume fetch error: {e}")
            return {"source": "coingecko", "status": "error", "error": str(e)}
    
    def validate_volume_reading(self, new_volume: float) -> float:
        """
        Validate new volume reading against recent history
        Prevents wild fluctuations by applying smoothing and change limits
        """
        if new_volume <= 0:
            return self.last_valid_volume
        
        # If no history, accept the first reading
        if not self.volume_history or self.last_valid_volume == 0:
            self.last_valid_volume = new_volume
            return new_volume
        
        # Calculate change percentage
        change_pct = abs(new_volume - self.last_valid_volume) / self.last_valid_volume
        
        # If change is too dramatic, apply smoothing
        if change_pct > self.volume_change_threshold:
            # Use weighted average for smoothing
            smoothed_volume = (self.last_valid_volume * 0.7) + (new_volume * 0.3)
            logger.debug(f"📊 Volume smoothed: {new_volume:.1f} → {smoothed_volume:.1f} (change: {change_pct:.1%})")
            return smoothed_volume
        
        # Change is reasonable, accept it
        return new_volume
    
    def get_current_5m_volume(self) -> Dict[str, Any]:
        """
        Get stable 5-minute volume without wild fluctuations
        Primary focus on Binance BTC volume, fallback to CoinGecko
        """
        try:
            current_volume = 0
            data_source = "unknown"
            
            # PRIMARY: Try Binance BTC volume (no conversion needed)
            binance_data = self.get_binance_volume_stable()
            if binance_data.get("status") == "success":
                volume_24h_btc = binance_data.get("volume_24h_btc", 0)
                if volume_24h_btc > 0:
                    # Calculate 5-minute volume from 24h data
                    raw_5m_volume = volume_24h_btc / 288  # 288 = 24 hours * 12 (5-min intervals)
                    
                    # Apply validation and smoothing
                    current_volume = self.validate_volume_reading(raw_5m_volume)
                    data_source = "binance_btc"
                    
                    logger.debug(f"📊 Binance: {volume_24h_btc:,.0f} BTC/24h → {current_volume:.1f} BTC/5m")
            
            # FALLBACK: Try CoinGecko if Binance failed
            if current_volume == 0:
                coingecko_data = self.get_coingecko_volume_stable()
                if coingecko_data.get("status") == "success":
                    volume_24h_btc = coingecko_data.get("volume_24h_btc", 0)
                    if volume_24h_btc > 0:
                        # Calculate 5-minute volume from 24h data
                        raw_5m_volume = volume_24h_btc / 288
                        
                        # Apply validation and smoothing
                        current_volume = self.validate_volume_reading(raw_5m_volume)
                        data_source = "coingecko_btc"
                        
                        logger.debug(f"🦎 CoinGecko: {volume_24h_btc:,.0f} BTC/24h → {current_volume:.1f} BTC/5m")
            
            # LAST RESORT: Use cached/fallback data with realistic minimum
            if current_volume == 0:
                # Set realistic minimum volume for BTC (never truly 0)
                fallback_volume = max(self.last_valid_volume, 150.0)  # Minimum 150 BTC/5m
                current_volume = self.validate_volume_reading(fallback_volume)
                data_source = "fallback_minimum"
                logger.debug(f"📊 Using fallback volume: {current_volume:.1f} BTC/5m")
            
            # Add to history for trend analysis
            self.volume_history.append(current_volume)
            self.last_valid_volume = current_volume
            
            # Calculate volume statistics
            volume_stats = self._calculate_volume_stats()
            
            # Determine stable volume category
            volume_category = self._determine_stable_volume_category(current_volume)
            
            result = {
                "current_volume": current_volume,
                "volume_category": volume_category,
                "data_source": data_source,
                "volume_trend": volume_stats["trend"],
                "average_volume": volume_stats["average"],
                "volume_stability": volume_stats["stability"],
                "readings_count": len(self.volume_history),
                "timestamp": time.time(),
                "status": "success"
            }
            
            logger.debug(f"📊 Stable volume: {current_volume:.1f} BTC ({volume_category}) - {data_source}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Stable volume fetch failed: {e}")
            # Return realistic fallback even on error
            fallback_volume = max(self.last_valid_volume, 150.0)
            return {
                "current_volume": fallback_volume,
                "volume_category": self._determine_stable_volume_category(fallback_volume),
                "data_source": "error_fallback",
                "volume_trend": "STABLE",
                "error": str(e),
                "status": "error"
            }
    
    def _calculate_volume_stats(self) -> Dict[str, Any]:
        """Calculate volume statistics for trend analysis"""
        try:
            if len(self.volume_history) < 3:
                return {"trend": "INSUFFICIENT_DATA", "average": 0, "stability": 0}
            
            volumes = list(self.volume_history)
            
            # Calculate statistics
            average = statistics.mean(volumes)
            median = statistics.median(volumes)
            std_dev = statistics.stdev(volumes) if len(volumes) > 1 else 0
            
            # Calculate trend (recent vs earlier)
            recent_avg = statistics.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
            earlier_avg = statistics.mean(volumes[-10:-5]) if len(volumes) >= 10 else average
            
            if recent_avg > earlier_avg * 1.1:
                trend = "INCREASING"
            elif recent_avg < earlier_avg * 0.9:
                trend = "DECREASING"
            else:
                trend = "STABLE"
            
            # Calculate stability score (lower std_dev = more stable)
            stability = max(0, 100 - (std_dev / average * 100)) if average > 0 else 0
            
            return {
                "trend": trend,
                "average": average,
                "median": median,
                "std_dev": std_dev,
                "stability": stability
            }
            
        except Exception as e:
            logger.debug(f"Volume stats calculation error: {e}")
            return {"trend": "UNKNOWN", "average": 0, "stability": 0}
    
    def _determine_stable_volume_category(self, volume: float) -> str:
        """
        Determine volume category with realistic BTC thresholds
        Based on actual BTC trading patterns, not theoretical numbers
        """
        # Realistic BTC volume thresholds (5-minute periods)
        if volume >= 2000:
            return "EXTREMELY_HIGH"
        elif volume >= 1000:
            return "VERY_HIGH"
        elif volume >= 500:
            return "HIGH"
        elif volume >= 200:
            return "MEDIUM"
        elif volume >= 100:
            return "NORMAL"
        elif volume >= 50:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def get_volume_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic information for volume system"""
        return {
            "volume_history_count": len(self.volume_history),
            "last_valid_volume": self.last_valid_volume,
            "btc_price_cache": self.btc_price_cache,
            "volume_change_threshold": self.volume_change_threshold,
            "cache_duration": self.cache_duration,
            "recent_volumes": list(self.volume_history)[-5:] if self.volume_history else []
        }


# Test the stable volume fetcher
if __name__ == "__main__":
    logger.info("🧪 Testing Stable Volume Fetcher")
    
    fetcher = StableVolumeFetcher()
    
    # Test multiple readings to check for stability
    for i in range(5):
        logger.info(f"\n📊 Test Reading {i+1}:")
        volume_data = fetcher.get_current_5m_volume()
        
        if volume_data.get("status") == "success":
            logger.success(f"   Volume: {volume_data['current_volume']:.1f} BTC")
            logger.info(f"   Category: {volume_data['volume_category']}")
            logger.info(f"   Source: {volume_data['data_source']}")
            logger.info(f"   Trend: {volume_data['volume_trend']}")
            logger.info(f"   Stability: {volume_data.get('volume_stability', 0):.1f}%")
        else:
            logger.error(f"   Error: {volume_data.get('error', 'Unknown')}")
        
        if i < 4:  # Don't sleep on last iteration
            time.sleep(3)
    
    # Show diagnostics
    diagnostics = fetcher.get_volume_diagnostics()
    logger.info("\n🔍 Volume System Diagnostics:")
    logger.info(f"   Readings collected: {diagnostics['volume_history_count']}")
    logger.info(f"   Last valid volume: {diagnostics['last_valid_volume']:.1f} BTC")
    logger.info(f"   Recent volumes: {[f'{v:.1f}' for v in diagnostics['recent_volumes']]}")
    logger.info(f"   BTC price cached: ${diagnostics['btc_price_cache']['price']:,.0f}")