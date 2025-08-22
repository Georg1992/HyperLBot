#!/usr/bin/env python3
"""
Multi-Source Volume Spike Detector
Uses multiple free APIs to detect volume spikes and cross-validate data
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
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.yahoo_data_fetcher import YahooDataFetcher
from data.volume_spike_detector import VolumeSpikeDetector

class MultiSourceVolumeDetector:
    """
    Detects volume spikes using multiple free APIs for cross-validation
    """
    
    def __init__(self):
        self.yahoo_detector = VolumeSpikeDetector()
        self.cache = {}
        self.cache_duration = 5  # 5 seconds cache
        
        # Free API endpoints
        self.apis = {
            "coinbase": {
                "url": "https://api.coinbase.com/v2/products/BTC-USD/stats",
                "free": True,
                "rate_limit": "10 requests per second"
            },
            "binance": {
                "url": "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
                "free": True,
                "rate_limit": "1200 requests per minute"
            },
            "cryptocompare": {
                "url": "https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=1",
                "free": True,
                "rate_limit": "100,000 requests per month"
            },
            "coingecko": {
                "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_vol=true",
                "free": True,
                "rate_limit": "50 calls per minute"
            }
        }
        
        logger.info("🌐 Multi-Source Volume Detector initialized")
    
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
    
    def get_coinbase_volume(self) -> Dict[str, Any]:
        """Get volume data from Coinbase API"""
        try:
            cache_key = "coinbase_volume"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            response = requests.get(self.apis["coinbase"]["url"], timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                volume_data = {
                    "source": "coinbase",
                    "volume_24h": float(data.get("stats", {}).get("volume", 0)),
                    "volume_30d": float(data.get("stats", {}).get("volume_30d", 0)),
                    "timestamp": time.time(),
                    "status": "success"
                }
                
                self._cache_data(cache_key, volume_data)
                return volume_data
            else:
                return {
                    "source": "coinbase",
                    "error": f"HTTP {response.status_code}",
                    "status": "error"
                }
                
        except Exception as e:
            logger.error(f"Coinbase API error: {e}")
            return {
                "source": "coinbase",
                "error": str(e),
                "status": "error"
            }
    
    def get_binance_volume(self) -> Dict[str, Any]:
        """Get volume data from Binance API"""
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
                    "count_24h": int(data.get("count", 0)),
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
        """Get recent volume data from CryptoCompare API"""
        try:
            cache_key = "cryptocompare_volume"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            response = requests.get(self.apis["cryptocompare"]["url"], timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("Response") == "Success" and data.get("Data", {}).get("Data"):
                    latest_candle = data["Data"]["Data"][-1]
                    
                    volume_data = {
                        "source": "cryptocompare",
                        "volume_1m": float(latest_candle.get("volumeto", 0)),
                        "volume_from_1m": float(latest_candle.get("volumefrom", 0)),
                        "close_price": float(latest_candle.get("close", 0)),
                        "timestamp": latest_candle.get("time", 0),
                        "status": "success"
                    }
                    
                    self._cache_data(cache_key, volume_data)
                    return volume_data
                else:
                    return {
                        "source": "cryptocompare",
                        "error": "No data available",
                        "status": "error"
                    }
            else:
                return {
                    "source": "cryptocompare",
                    "error": f"HTTP {response.status_code}",
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
        """Get volume data from CoinGecko API"""
        try:
            cache_key = "coingecko_volume"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            response = requests.get(self.apis["coingecko"]["url"], timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                bitcoin_data = data.get("bitcoin", {})
                if bitcoin_data:
                    volume_data = {
                        "source": "coingecko",
                        "volume_24h": float(bitcoin_data.get("usd_24h_vol", 0)),
                        "current_price": float(bitcoin_data.get("usd", 0)),
                        "timestamp": time.time(),
                        "status": "success"
                    }
                    
                    self._cache_data(cache_key, volume_data)
                    return volume_data
                else:
                    return {
                        "source": "coingecko",
                        "error": "No bitcoin data available",
                        "status": "error"
                    }
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
    
    def get_all_volume_sources(self) -> Dict[str, Any]:
        """Get volume data from all available sources"""
        try:
            # Get data from all APIs
            coinbase_data = self.get_coinbase_volume()
            binance_data = self.get_binance_volume()
            cryptocompare_data = self.get_cryptocompare_volume()
            coingecko_data = self.get_coingecko_volume()
            
            # Get Yahoo data
            yahoo_data = self.yahoo_detector.get_comprehensive_volume_analysis("BTC")
            
            all_sources = {
                "timestamp": time.time(),
                "sources": {
                    "yahoo": yahoo_data,
                    "coinbase": coinbase_data,
                    "binance": binance_data,
                    "cryptocompare": cryptocompare_data,
                    "coingecko": coingecko_data
                },
                "summary": self._analyze_multi_source_data(yahoo_data, coinbase_data, binance_data, cryptocompare_data, coingecko_data)
            }
            
            return all_sources
            
        except Exception as e:
            logger.error(f"Error getting multi-source volume data: {e}")
            return {
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _analyze_multi_source_data(self, yahoo_data: Dict, coinbase_data: Dict, binance_data: Dict, cryptocompare_data: Dict, coingecko_data: Dict) -> Dict[str, Any]:
        """Analyze and cross-validate data from multiple sources"""
        try:
            summary = {
                "total_sources": 5,
                "successful_sources": 0,
                "volume_spike_detected": False,
                "spike_confidence": 0,
                "volume_consensus": "UNKNOWN",
                "data_quality": "UNKNOWN"
            }
            
            # Count successful sources
            successful_sources = []
            if yahoo_data and "error" not in yahoo_data:
                successful_sources.append("yahoo")
            if coinbase_data and coinbase_data.get("status") == "success":
                successful_sources.append("coinbase")
            if binance_data and binance_data.get("status") == "success":
                successful_sources.append("binance")
            if cryptocompare_data and cryptocompare_data.get("status") == "success":
                successful_sources.append("cryptocompare")
            if coingecko_data and coingecko_data.get("status") == "success":
                successful_sources.append("coingecko")
            
            summary["successful_sources"] = len(successful_sources)
            
            # Analyze volume spike detection
            spike_detections = []
            
            # Yahoo spike detection
            if yahoo_data and "error" not in yahoo_data:
                spike_analysis = yahoo_data.get("spike_analysis", {})
                if spike_analysis.get("is_spike", False):
                    spike_detections.append({
                        "source": "yahoo",
                        "severity": spike_analysis.get("spike_severity", "UNKNOWN"),
                        "ratio": spike_analysis.get("spike_ratio_mean", 0)
                    })
            
            # Analyze other sources for volume anomalies
            volume_data = []
            
            if coinbase_data and coinbase_data.get("status") == "success":
                volume_data.append({
                    "source": "coinbase",
                    "volume": coinbase_data.get("volume_24h", 0)
                })
            
            if binance_data and binance_data.get("status") == "success":
                volume_data.append({
                    "source": "binance",
                    "volume": binance_data.get("volume_24h", 0)
                })
            
            if coingecko_data and coingecko_data.get("status") == "success":
                volume_data.append({
                    "source": "coingecko",
                    "volume": coingecko_data.get("volume_24h", 0)
                })
            
            # Determine volume consensus
            if len(volume_data) >= 2:
                volumes = [v["volume"] for v in volume_data if v["volume"] > 0]
                if volumes:
                    avg_volume = statistics.mean(volumes)
                    volume_variance = statistics.stdev(volumes) if len(volumes) > 1 else 0
                    
                    if volume_variance > 0:
                        cv = volume_variance / avg_volume  # Coefficient of variation
                        if cv < 0.1:
                            summary["volume_consensus"] = "HIGH"
                        elif cv < 0.2:
                            summary["volume_consensus"] = "MEDIUM"
                        else:
                            summary["volume_consensus"] = "LOW"
                    else:
                        summary["volume_consensus"] = "HIGH"
            
            # Determine overall spike detection
            if spike_detections:
                summary["volume_spike_detected"] = True
                summary["spike_confidence"] = len(spike_detections) / summary["total_sources"]
                
                # Log spike detection
                for spike in spike_detections:
                    logger.warning(f"🚨 VOLUME SPIKE DETECTED by {spike['source']}: {spike['severity']} ({spike['ratio']:.1f}x)")
            
            # Determine data quality
            success_rate = summary["successful_sources"] / summary["total_sources"]
            if success_rate >= 0.8:
                summary["data_quality"] = "EXCELLENT"
            elif success_rate >= 0.6:
                summary["data_quality"] = "GOOD"
            elif success_rate >= 0.4:
                summary["data_quality"] = "FAIR"
            else:
                summary["data_quality"] = "POOR"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error analyzing multi-source data: {e}")
            return {
                "error": str(e),
                "total_sources": 5,
                "successful_sources": 0,
                "volume_spike_detected": False,
                "spike_confidence": 0,
                "volume_consensus": "UNKNOWN",
                "data_quality": "UNKNOWN"
            }
    
    def get_enhanced_volume_analysis(self) -> Dict[str, Any]:
        """Get enhanced volume analysis with multi-source validation"""
        try:
            # Get all source data
            multi_source_data = self.get_all_volume_sources()
            
            if "error" in multi_source_data:
                return multi_source_data
            
            # Get Yahoo analysis as primary source
            yahoo_analysis = multi_source_data["sources"]["yahoo"]
            summary = multi_source_data["summary"]
            
            # Enhance Yahoo analysis with multi-source validation
            enhanced_analysis = {
                "timestamp": time.time(),
                "primary_source": "yahoo_finance",
                "validation_sources": summary["successful_sources"] - 1,  # Exclude Yahoo
                "data_quality": summary["data_quality"],
                "volume_consensus": summary["volume_consensus"],
                "yahoo_analysis": yahoo_analysis,
                "multi_source_summary": summary,
                "all_sources": multi_source_data["sources"],
                "enhanced_confidence": self._calculate_enhanced_confidence(yahoo_analysis, summary)
            }
            
            # Log enhanced spike detection
            if summary["volume_spike_detected"]:
                confidence = enhanced_analysis["enhanced_confidence"]
                logger.warning(f"🚨 ENHANCED VOLUME SPIKE DETECTED! Confidence: {confidence:.1%}")
                logger.warning(f"   Sources: {summary['successful_sources']}/{summary['total_sources']}")
                logger.warning(f"   Data Quality: {summary['data_quality']}")
                logger.warning(f"   Volume Consensus: {summary['volume_consensus']}")
            
            return enhanced_analysis
            
        except Exception as e:
            logger.error(f"Error in enhanced volume analysis: {e}")
            return {
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _calculate_enhanced_confidence(self, yahoo_analysis: Dict, summary: Dict) -> float:
        """Calculate enhanced confidence based on multi-source validation"""
        try:
            base_confidence = 0.5  # Base confidence for single source
            
            # Yahoo spike detection confidence
            if yahoo_analysis and "error" not in yahoo_analysis:
                spike_analysis = yahoo_analysis.get("spike_analysis", {})
                if spike_analysis.get("is_spike", False):
                    base_confidence = 0.7  # Higher base confidence for detected spike
            
            # Multi-source validation bonus
            source_bonus = (summary["successful_sources"] - 1) * 0.05  # 5% per additional source
            
            # Data quality bonus
            quality_bonus = 0
            if summary["data_quality"] == "EXCELLENT":
                quality_bonus = 0.15
            elif summary["data_quality"] == "GOOD":
                quality_bonus = 0.10
            elif summary["data_quality"] == "FAIR":
                quality_bonus = 0.05
            
            # Volume consensus bonus
            consensus_bonus = 0
            if summary["volume_consensus"] == "HIGH":
                consensus_bonus = 0.10
            elif summary["volume_consensus"] == "MEDIUM":
                consensus_bonus = 0.05
            
            enhanced_confidence = min(1.0, base_confidence + source_bonus + quality_bonus + consensus_bonus)
            
            return enhanced_confidence
            
        except Exception as e:
            logger.error(f"Error calculating enhanced confidence: {e}")
            return 0.5


def main():
    """Test the multi-source volume detector"""
    logger.info("🔍 Testing Multi-Source Volume Detector")
    logger.info("=" * 60)
    
    detector = MultiSourceVolumeDetector()
    
    # Test individual APIs
    logger.info("📊 Testing individual APIs...")
    
    coinbase_data = detector.get_coinbase_volume()
    logger.info(f"Coinbase: {coinbase_data.get('status', 'error')}")
    
    binance_data = detector.get_binance_volume()
    logger.info(f"Binance: {binance_data.get('status', 'error')}")
    
    cryptocompare_data = detector.get_cryptocompare_volume()
    logger.info(f"CryptoCompare: {cryptocompare_data.get('status', 'error')}")
    
    coingecko_data = detector.get_coingecko_volume()
    logger.info(f"CoinGecko: {coingecko_data.get('status', 'error')}")
    
    # Test enhanced analysis
    logger.info("\n📈 Testing enhanced volume analysis...")
    enhanced_analysis = detector.get_enhanced_volume_analysis()
    
    if "error" not in enhanced_analysis:
        summary = enhanced_analysis["multi_source_summary"]
        logger.success("✅ Enhanced analysis successful!")
        logger.info(f"Successful sources: {summary['successful_sources']}/{summary['total_sources']}")
        logger.info(f"Data quality: {summary['data_quality']}")
        logger.info(f"Volume consensus: {summary['volume_consensus']}")
        logger.info(f"Volume spike detected: {summary['volume_spike_detected']}")
        logger.info(f"Enhanced confidence: {enhanced_analysis['enhanced_confidence']:.1%}")
    else:
        logger.error(f"❌ Enhanced analysis failed: {enhanced_analysis['error']}")


if __name__ == "__main__":
    main()
