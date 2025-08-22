#!/usr/bin/env python3
"""
Yahoo Finance Data Fetcher for Historical BTC/USD Data
Provides real historical candlestick data that aligns with Hyperliquid BTC/USD perpetuals
NOTE: This fetcher is for HISTORICAL DATA ONLY. Real-time pricing should come from Hyperliquid.
"""

import time
import json
import yfinance as yf
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import sys
import os
import statistics

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class YahooDataFetcher:
    """
    Yahoo Finance data fetcher for BTC/USD historical data
    Provides real historical candlestick data aligned with Hyperliquid BTC/USD perpetuals
    NOTE: For real-time pricing, use Hyperliquid API exclusively
    """
    
    def __init__(self):
        self.symbol = "BTC-USD"
        self.cache = {}
        self.cache_duration = 5  # 5 seconds cache for ultra-frequent updates
        
        logger.info("🔗 Yahoo Finance Data Fetcher initialized for BTC-USD (HISTORICAL DATA ONLY)")
        logger.info("📊 Real-time pricing should come from Hyperliquid API")
    
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
    
    def _convert_yf_to_standard(self, yf_data) -> List[Dict[str, Any]]:
        """Convert yfinance DataFrame to standard candlestick format"""
        if yf_data.empty:
            return []
        
        candles = []
        for index, row in yf_data.iterrows():
            candle = {
                "open_time": int(index.timestamp() * 1000),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": float(row['Volume']) if 'Volume' in row else 0,
                "close_time": int(index.timestamp() * 1000),
                "quote_asset_volume": float(row['Volume']) if 'Volume' in row else 0,
                "number_of_trades": 0,
                "taker_buy_base_asset_volume": 0,
                "taker_buy_quote_asset_volume": 0
            }
            candles.append(candle)
        
        return candles
    
    def get_klines(self, symbol: str = "BTC", interval: str = "5m", limit: int = 100) -> List[Dict[str, Any]]:
        """Get candlestick data from Yahoo Finance"""
        try:
            cache_key = f"klines_{symbol}_{interval}_{limit}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Convert interval to Yahoo Finance format
            interval_map = {
                "1m": "1m",
                "5m": "5m", 
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d"
            }
            
            yf_interval = interval_map.get(interval, "5m")
            
            # Calculate period based on interval and limit
            # Use more generous periods that were working before
            if interval == "1m":
                period = "7d"  # 7 days for 1m data
            elif interval == "5m":
                period = "60d"  # 60 days for 5m data
            elif interval == "15m":
                period = "90d"  # 90 days for 15m data
            elif interval == "30m":
                period = "180d"  # 180 days for 30m data
            elif interval == "1h":
                period = "1y"  # 1 year for 1h data
            elif interval == "4h":
                period = "2y"  # 2 years for 4h data
            elif interval == "1d":
                period = "5y"  # 5 years for 1d data
            else:
                period = "60d"  # Default to 60 days
            
            # Get data from Yahoo Finance
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period=period, interval=yf_interval)
            
            if data.empty:
                logger.warning(f"⚠️ No data received from Yahoo Finance for {symbol} {interval}")
                return []
            
            # Convert to standard format
            candles = self._convert_yf_to_standard(data)
            
            # Limit to requested number of candles (most recent)
            if len(candles) > limit:
                candles = candles[-limit:]
            
            # Cache the result
            self._cache_data(cache_key, candles)
            
            logger.info(f"✅ Retrieved {len(candles)} {interval} candles from Yahoo Finance")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to get {interval} klines from Yahoo Finance: {e}")
            return []
    
    def get_5m_klines(self, symbol: str = "BTC", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 5-minute candlestick data from Yahoo Finance"""
        return self.get_klines(symbol, "5m", limit)
    
    def get_1m_klines(self, symbol: str = "BTC", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 1-minute candlestick data from Yahoo Finance"""
        return self.get_klines(symbol, "1m", limit)
    
    def get_1h_klines(self, symbol: str = "BTC", limit: int = 100) -> List[Dict[str, Any]]:
        """Get 1-hour candlestick data from Yahoo Finance"""
        return self.get_klines(symbol, "1h", limit)
    
    # REMOVED: get_current_price method - Real-time pricing should come from Hyperliquid
    
    def get_ticker_data(self, symbol: str = "BTC") -> Optional[Dict[str, Any]]:
        """Get ticker-like data from Yahoo Finance (historical context only)"""
        try:
            cache_key = f"ticker_{symbol}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            
            # Use previous close as reference (not current price)
            previous_close = info.get('previousClose', 0)
            
            ticker_data = {
                "symbol": symbol,
                "priceChange": 0,  # No real-time price change
                "priceChangePercent": 0,  # No real-time price change
                "lastPrice": previous_close,  # Use previous close for historical context
                "volume": info.get('regularMarketVolume', 0),
                "quoteVolume": info.get('regularMarketVolume', 0) * previous_close,
                "count": 0  # Not provided by Yahoo Finance
            }
            
            self._cache_data(cache_key, ticker_data)
            return ticker_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get ticker data from Yahoo Finance: {e}")
            return None
    
    def calculate_support_resistance(self, candles: List[Dict[str, Any]], lookback: int = 20) -> Dict[str, float]:
        """Calculate support and resistance levels from candlestick data"""
        if len(candles) < lookback:
            return {"support": 0, "resistance": 0, "range": 0}
        
        recent_candles = candles[-lookback:]
        highs = [candle["high"] for candle in recent_candles]
        lows = [candle["low"] for candle in recent_candles]
        
        resistance = max(highs)
        support = min(lows)
        range_size = resistance - support
        
        return {
            "support": support,
            "resistance": resistance,
            "range": range_size
        }
    
    def calculate_trend(self, candles: List[Dict[str, Any]], periods: int = 5) -> Dict[str, Any]:
        """Calculate trend direction and strength with enhanced neutral market handling"""
        if len(candles) < periods:
            return {"trend": "INSUFFICIENT_DATA", "strength": 0, "direction": 0, "raw_change": 0}
        
        recent_candles = candles[-periods:]
        closes = [candle["close"] for candle in recent_candles]
        
        # Calculate trend direction
        first_close = closes[0]
        last_close = closes[-1]
        price_change = (last_close - first_close) / first_close
        
        # Enhanced trend detection with multiple thresholds
        if price_change > 0.003:  # 0.3% strong uptrend
            trend = "STRONG_UP"
            strength = min(abs(price_change), 0.1)  # Cap at 10%
        elif price_change > 0.001:  # 0.1% uptrend
            trend = "UP"
            strength = min(abs(price_change), 0.1)
        elif price_change > 0.0002:  # 0.02% weak uptrend
            trend = "WEAK_UP"  # Still bullish but very weak
            strength = min(abs(price_change), 0.1)
        elif price_change < -0.003:  # 0.3% strong downtrend
            trend = "STRONG_DOWN"
            strength = min(abs(price_change), 0.1)
        elif price_change < -0.001:  # 0.1% downtrend
            trend = "DOWN"
            strength = min(abs(price_change), 0.1)
        elif price_change < -0.0002:  # 0.02% weak downtrend
            trend = "WEAK_DOWN"  # Still bearish but very weak
            strength = min(abs(price_change), 0.1)
        else:
            # True sideways market - very small movement
            trend = "SIDEWAYS"
            strength = 0.01  # Give small strength to indicate market is active
        
        # Calculate additional trend confidence metrics
        highs = [candle["high"] for candle in recent_candles]
        lows = [candle["low"] for candle in recent_candles]
        
        # Check for consistent direction (higher highs/higher lows for uptrend)
        direction_consistency = 0
        if len(closes) >= 3:
            ups = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
            downs = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i-1])
            total_moves = ups + downs
            if total_moves > 0:
                direction_consistency = max(ups, downs) / total_moves
        
        # Enhanced strength calculation considering consistency
        if direction_consistency > 0.7:  # 70%+ moves in same direction
            strength = min(strength * 1.3, 0.1)  # Boost strength for consistent trends
        
        return {
            "trend": trend,
            "strength": strength,
            "direction": price_change,
            "raw_change": price_change,
            "direction_consistency": direction_consistency,
            "periods_analyzed": periods,
            "trend_quality": "HIGH" if direction_consistency > 0.7 else "MEDIUM" if direction_consistency > 0.5 else "LOW"
        }
    
    def calculate_volatility(self, candles: List[Dict[str, Any]], periods: int = 20) -> float:
        """Calculate price volatility"""
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
    
    def get_market_analysis(self, symbol: str = "BTC", hyperliquid_price: float = None) -> Dict[str, Any]:
        """
        Get comprehensive market analysis from Yahoo Finance (HISTORICAL DATA ONLY)
        NOTE: hyperliquid_price parameter should be provided for current price context
        """
        try:
            # Get different timeframe data - COMPLETE optimal multi-timeframe configuration
            candles_1m = self.get_1m_klines(symbol, 120)  # 2 hours of 1m data for immediate momentum
            candles_5m = self.get_5m_klines(symbol, 60)   # 5 hours of 5m data (core prediction analysis)
            candles_1h = self.get_1h_klines(symbol, 84)   # 3.5 days of 1h data (daily trend context)
            candles_1d = self.get_klines(symbol, "1d", 45) # 6 weeks of 1d data (weekly/monthly trend context)
            ticker = self.get_ticker_data(symbol)
            
            if not candles_5m or not candles_1h or not candles_1d:
                return {"error": "Could not fetch candlestick data from Yahoo Finance"}
            
            # Get Yahoo Finance historical close price for comparison
            yahoo_last_close = candles_5m[-1]["close"] if candles_5m else 0
            
            # Use Hyperliquid price if provided, otherwise use last close from historical data
            if hyperliquid_price is not None:
                current_price = hyperliquid_price
                logger.info(f"📊 Using Hyperliquid price: ${current_price:,.2f}")
                
                # Calculate price difference between Hyperliquid and Yahoo Finance
                price_difference = abs(hyperliquid_price - yahoo_last_close)
                price_difference_pct = (price_difference / yahoo_last_close * 100) if yahoo_last_close > 0 else 0
                
                logger.info(f"📊 Yahoo last close: ${yahoo_last_close:,.2f}")
                logger.info(f"📊 Price difference: ${price_difference:,.2f} ({price_difference_pct:.3f}%)")
            else:
                # Fallback to last close price from historical data
                current_price = yahoo_last_close
                price_difference = 0
                price_difference_pct = 0
                logger.warning(f"⚠️ No Hyperliquid price provided, using last close: ${current_price:,.2f}")
            
            # Calculate indicators using Yahoo Finance historical data
            support_resistance_5m = self.calculate_support_resistance(candles_5m)
            support_resistance_1h = self.calculate_support_resistance(candles_1h)
            
            # Multi-timeframe trend analysis - COMPLETE coverage
            trend_5m = self.calculate_trend(candles_5m)   # Short-term trend (5 hours)
            trend_1h = self.calculate_trend(candles_1h)   # Daily trend (3.5 days)
            trend_1d = self.calculate_trend(candles_1d)   # Weekly/monthly trend (6 weeks)
            
            # Multi-timeframe volatility analysis
            volatility_5m = self.calculate_volatility(candles_5m)
            volatility_1h = self.calculate_volatility(candles_1h)
            volatility_1d = self.calculate_volatility(candles_1d)
            
            # Daily support/resistance for major levels
            support_resistance_1d = self.calculate_support_resistance(candles_1d)
            
            analysis = {
                "timestamp": time.time(),
                "symbol": symbol,
                "current_price": current_price,  # Hyperliquid price for trading
                "yahoo_last_close": yahoo_last_close,  # Yahoo Finance historical close
                "price_difference": price_difference,  # Absolute difference
                "price_difference_pct": price_difference_pct,  # Percentage difference
                "candles_1m": candles_1m,  # Full 120 1-min candles (2 hours)
                "candles_5m": candles_5m,  # Full 60 5-min candles (5 hours)
                "candles_1h": candles_1h,  # Full 84 1-hour candles (3.5 days)
                "candles_1d": candles_1d,  # Full 45 daily candles (6 weeks)
                "support_resistance_5m": support_resistance_5m,
                "support_resistance_1h": support_resistance_1h,
                "support_resistance_1d": support_resistance_1d,  # Major weekly/monthly levels
                "trend_5m": trend_5m,     # Short-term trend (5h)
                "trend_1h": trend_1h,     # Daily trend (3.5d)
                "trend_1d": trend_1d,     # Weekly/monthly trend (6w)
                "volatility_5m": volatility_5m,
                "volatility_1h": volatility_1h,
                "volatility_1d": volatility_1d,
                "ticker": ticker,
                "market_condition": self._determine_market_condition(trend_5m, trend_1h, volatility_5m),
                "data_source": "Yahoo Finance (Historical) + Hyperliquid (Real-time Price)"
            }
            
            logger.success(f"✅ Yahoo Finance market analysis completed for {symbol}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in Yahoo Finance market analysis: {e}")
            return {"error": str(e)}
    
    def _determine_market_condition(self, trend_5m: Dict, trend_1h: Dict, volatility: float) -> str:
        """Determine overall market condition"""
        # High volatility
        if volatility > 0.02:  # 2% volatility
            return "HIGH_VOLATILITY"
        
        # Strong trends
        if trend_5m["strength"] > 0.01 and trend_1h["strength"] > 0.005:
            if trend_5m["trend"] == trend_1h["trend"]:
                return "STRONG_TREND"
            else:
                return "MIXED_SIGNALS"
        
        # Low volatility
        if volatility < 0.005:  # 0.5% volatility
            return "LOW_VOLATILITY"
        
        return "NORMAL"
    
    def test_connection(self) -> bool:
        """Test connection to Yahoo Finance (historical data only)"""
        try:
            # Test with historical data instead of current price
            candles = self.get_5m_klines("BTC", 10)
            if candles and len(candles) > 0:
                logger.success("✅ Yahoo Finance connection successful (historical data)")
                return True
            else:
                logger.error("❌ Yahoo Finance connection failed - no historical data")
                return False
        except Exception as e:
            logger.error(f"❌ Yahoo Finance connection error: {e}")
            return False

    def get_current_5m_volume(self, symbol: str = None) -> Dict[str, Any]:
        """Get current 5-minute volume statistics with multi-source spike detection"""
        try:
            symbol = symbol or "BTC-USD"
            
            # Import multi-source volume detector
            try:
                from data.multi_source_volume_detector import MultiSourceVolumeDetector
                multi_source_detector = MultiSourceVolumeDetector()
                
                # Get enhanced volume analysis with multi-source validation
                enhanced_analysis = multi_source_detector.get_enhanced_volume_analysis()
                
                if "error" not in enhanced_analysis:
                    # Extract data from enhanced analysis - yahoo_analysis is already flattened
                    yahoo_analysis = enhanced_analysis.get("yahoo_analysis", {})
                    multi_source_summary = enhanced_analysis.get("multi_source_summary", {})
                    
                    # Get current volume and scale it
                    current_volume = yahoo_analysis.get("current_volume", 0)
                    scale_factor = 0.00001  # Scale down to match Hyperliquid ranges
                    scaled_current_volume = current_volume * scale_factor
                    
                    # Get baseline for average calculation
                    baseline = yahoo_analysis.get("baseline_mean", 0)
                    scaled_avg_volume = baseline * scale_factor if baseline else 0
                    
                    # Determine volume category based on spike severity and multi-source validation
                    spike_severity = yahoo_analysis.get("spike_severity", "NORMAL")
                    enhanced_confidence = enhanced_analysis.get("enhanced_confidence", 0)
                    
                    if spike_severity == "EXTREME" and enhanced_confidence > 0.7:
                        volume_category = "CRAZY_HIGH"
                    elif spike_severity == "HIGH" and enhanced_confidence > 0.6:
                        volume_category = "VERY_HIGH"
                    elif spike_severity == "MODERATE" and enhanced_confidence > 0.5:
                        volume_category = "HIGH"
                    elif spike_severity == "MILD" and enhanced_confidence > 0.4:
                        volume_category = "NORMAL"
                    else:
                        # Fallback to traditional categorization
                        if scaled_current_volume >= 4000:
                            volume_category = "CRAZY_HIGH"
                        elif scaled_current_volume >= 1000:
                            volume_category = "VERY_HIGH"
                        elif scaled_current_volume >= 500:
                            volume_category = "HIGH"
                        elif scaled_current_volume >= 100:
                            volume_category = "NORMAL"
                        elif scaled_current_volume >= 50:
                            volume_category = "LOW"
                        elif scaled_current_volume >= 10:
                            volume_category = "VERY_LOW"
                        else:
                            volume_category = "EXTREMELY_LOW"
                    
                    # Get volume trend from trend analysis
                    volume_trend = yahoo_analysis.get("volume_trend", "UNKNOWN")
                    
                    # Enhanced volume data with multi-source validation
                    enhanced_volume_data = {
                        "current_volume": scaled_current_volume,
                        "volume_category": volume_category,
                        "avg_volume": scaled_avg_volume,
                        "volume_trend": volume_trend,
                        "data_source": "multi_source_validation",
                        "raw_volume": current_volume,
                        "scale_factor": scale_factor,
                        # Spike detection data - extract from flattened yahoo_analysis
                        "has_spike": yahoo_analysis.get("has_spike", False),
                        "spike_severity": spike_severity,
                        "is_immediate_spike": yahoo_analysis.get("is_immediate_spike", False),
                        "spike_reason": yahoo_analysis.get("spike_reason", ""),
                        "spike_ratio": yahoo_analysis.get("spike_ratio_mean", 0),
                        "spike_description": yahoo_analysis.get("spike_description", ""),
                        "percentile_alerts": yahoo_analysis.get("percentile_alerts", []),
                        "volume_acceleration": yahoo_analysis.get("volume_acceleration", 0),
                        # Real-time volume data - extract from flattened yahoo_analysis
                        "period_progress": yahoo_analysis.get("period_progress", 0),
                        "current_5m_period": yahoo_analysis.get("current_5m_period", ""),
                        "completed_volume": yahoo_analysis.get("completed_volume", 0),
                        "current_minute_volume": yahoo_analysis.get("current_minute_volume", 0),
                        "volume_source": yahoo_analysis.get("volume_source", "multi_source"),
                        # Multi-source validation data
                        "enhanced_confidence": enhanced_confidence,
                        "validation_sources": enhanced_analysis.get("validation_sources", 0),
                        "data_quality": multi_source_summary.get("data_quality", "UNKNOWN"),
                        "volume_consensus": multi_source_summary.get("volume_consensus", "UNKNOWN"),
                        "successful_sources": multi_source_summary.get("successful_sources", 0),
                        "total_sources": multi_source_summary.get("total_sources", 0)
                    }
                    
                    return enhanced_volume_data
                    
            except ImportError:
                logger.warning("Multi-source volume detector not available, falling back to single-source analysis")
                
                # Fallback to single-source volume spike detector
                try:
                    from data.volume_spike_detector import VolumeSpikeDetector
                    spike_detector = VolumeSpikeDetector()
                    
                    # Get comprehensive volume analysis including spike detection
                    volume_analysis = spike_detector.get_comprehensive_volume_analysis(symbol)
                    
                    if "error" not in volume_analysis:
                        # Extract data from comprehensive analysis - volume_analysis is already flattened
                        current_volume = volume_analysis.get("current_volume", 0)
                        scale_factor = 0.00001  # Scale down to match Hyperliquid ranges
                        scaled_current_volume = current_volume * scale_factor
                        
                        # Get baseline for average calculation
                        baseline = spike_detector.get_volume_baseline(symbol)
                        if "error" not in baseline:
                            scaled_avg_volume = baseline.get("mean_volume", 0) * scale_factor
                        else:
                            scaled_avg_volume = 0
                        
                        # Determine volume category based on spike severity
                        spike_severity = volume_analysis.get("spike_severity", "NORMAL")
                        if spike_severity == "EXTREME":
                            volume_category = "CRAZY_HIGH"
                        elif spike_severity == "HIGH":
                            volume_category = "VERY_HIGH"
                        elif spike_severity == "MODERATE":
                            volume_category = "HIGH"
                        elif spike_severity == "MILD":
                            volume_category = "NORMAL"
                        else:
                            # Fallback to traditional categorization
                            if scaled_current_volume >= 4000:
                                volume_category = "CRAZY_HIGH"
                            elif scaled_current_volume >= 1000:
                                volume_category = "VERY_HIGH"
                            elif scaled_current_volume >= 500:
                                volume_category = "HIGH"
                            elif scaled_current_volume >= 100:
                                volume_category = "NORMAL"
                            elif scaled_current_volume >= 50:
                                volume_category = "LOW"
                            elif scaled_current_volume >= 10:
                                volume_category = "VERY_LOW"
                            else:
                                volume_category = "EXTREMELY_LOW"
                        
                        # Get volume trend from trend analysis
                        volume_trend = volume_analysis.get("volume_trend", "UNKNOWN")
                        
                        # Enhanced volume data with spike information
                        enhanced_volume_data = {
                            "current_volume": scaled_current_volume,
                            "volume_category": volume_category,
                            "avg_volume": scaled_avg_volume,
                            "volume_trend": volume_trend,
                            "data_source": "yahoo_finance_1m_spike_detection",
                            "raw_volume": current_volume,
                            "scale_factor": scale_factor,
                            # Spike detection data - extract from flattened volume_analysis
                            "has_spike": volume_analysis.get("has_spike", False),
                            "spike_severity": spike_severity,
                            "is_immediate_spike": volume_analysis.get("is_immediate_spike", False),
                            "spike_reason": volume_analysis.get("spike_reason", ""),
                            "spike_ratio": volume_analysis.get("spike_ratio_mean", 0),
                            "spike_description": volume_analysis.get("spike_description", ""),
                            "percentile_alerts": volume_analysis.get("percentile_alerts", []),
                            "volume_acceleration": volume_analysis.get("volume_acceleration", 0),
                            # Real-time volume data - extract from flattened volume_analysis
                            "period_progress": volume_analysis.get("period_progress", 0),
                            "current_5m_period": volume_analysis.get("current_5m_period", ""),
                            "completed_volume": volume_analysis.get("completed_volume", 0),
                            "current_minute_volume": volume_analysis.get("current_minute_volume", 0),
                            "volume_source": volume_analysis.get("volume_source", "yahoo_finance")
                        }
                        
                        return enhanced_volume_data
                        
                except ImportError:
                    logger.warning("Volume spike detector not available, falling back to basic volume analysis")
            
            # Fallback to original method if spike detector is not available
            candles_5m = self.get_5m_klines(symbol, limit=10)
            if not candles_5m:
                logger.warning(f"No 5m candle data available for {symbol}")
                return {
                    "current_volume": 0,
                    "volume_category": "ERROR",
                    "avg_volume": 0,
                    "volume_trend": "ERROR",
                    "error": "No candle data available",
                    "data_source": "yahoo_finance"
                }
            
            # Extract volume data from candles
            volumes = [candle.get("volume", 0) for candle in candles_5m]
            
            # Use most recent completed candle (not the current incomplete one)
            if len(volumes) >= 2 and volumes[-1] == 0:
                current_volume = volumes[-2]  # Use previous completed candle
                logger.info("Using previous completed candle for volume (current candle incomplete)")
            else:
                current_volume = volumes[-1] if volumes else 0
            
            # Calculate average volume from recent candles
            recent_volumes = volumes[-5:]  # Last 5 candles
            avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
            
            # Use actual Yahoo volume (no scaling to match Hyperliquid)
            current_volume = current_volume
            avg_volume = avg_volume
            
            # Categorize volume based on actual Yahoo Finance ranges (more realistic for BTC)
            if current_volume >= 500000:  # 500K+
                volume_category = "EXTREMELY_HIGH"
            elif current_volume >= 200000:  # 200K+
                volume_category = "VERY_HIGH"
            elif current_volume >= 100000:  # 100K+
                volume_category = "HIGH"
            elif current_volume >= 50000:  # 50K+
                volume_category = "ABOVE_AVERAGE"
            elif current_volume >= 20000:  # 20K+
                volume_category = "NORMAL"
            elif current_volume >= 10000:  # 10K+
                volume_category = "BELOW_AVERAGE"
            elif current_volume >= 5000:  # 5K+
                volume_category = "LOW"
            elif current_volume >= 2000:  # 2K+
                volume_category = "VERY_LOW"
            else:
                volume_category = "EXTREMELY_LOW"
            
            # Determine volume trend
            if len(volumes) >= 3:
                recent_avg = sum(volumes[-3:]) / 3
                older_avg = sum(volumes[-6:-3]) / 3 if len(volumes) >= 6 else recent_avg
                
                if recent_avg > older_avg * 1.1:
                    volume_trend = "INCREASING"
                elif recent_avg < older_avg * 0.9:
                    volume_trend = "DECREASING"
                else:
                    volume_trend = "STABLE"
            else:
                volume_trend = "UNKNOWN"
            
            return {
                "current_volume": current_volume,
                "volume_category": volume_category,
                "avg_volume": avg_volume,
                "volume_trend": volume_trend,
                "recent_volumes": recent_volumes,
                "data_source": "yahoo_finance",
                # Add basic spike detection fields for dashboard compatibility
                "has_spike": False,
                "spike_severity": "NORMAL",
                "is_immediate_spike": False,
                "spike_reason": "",
                "volume_source": "yahoo_finance_basic"
            }
            
        except Exception as e:
            logger.error(f"Failed to get current 5m volume: {e}")
            return {
                "current_volume": 0,
                "volume_category": "ERROR",
                "avg_volume": 0,
                "volume_trend": "ERROR",
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    
    def get_market_summary(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get market summary including day high/low, averages, and trends"""
        try:
            cache_key = f"summary_{symbol}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Get daily data for summary
            daily_candles = self.get_klines(symbol, "1d", 30)
            if not daily_candles:
                return {
                    "error": "No daily data available",
                    "data_source": "yahoo_finance"
                }
            
            # Get 5m data for intraday analysis
            intraday_candles = self.get_klines(symbol, "5m", 30)
            
            # Calculate daily statistics
            today_candle = daily_candles[-1] if daily_candles else None
            yesterday_candle = daily_candles[-2] if len(daily_candles) > 1 else None
            
            # Calculate moving averages
            closes = [c["close"] for c in daily_candles]
            ma_20 = sum(closes[-20:]) / min(20, len(closes)) if closes else 0
            ma_50 = sum(closes[-50:]) / min(50, len(closes)) if closes else 0
            
            # Calculate intraday range
            if intraday_candles:
                intraday_high = max(c["high"] for c in intraday_candles)
                intraday_low = min(c["low"] for c in intraday_candles)
                intraday_range = intraday_high - intraday_low
                intraday_range_pct = (intraday_range / intraday_low) * 100 if intraday_low > 0 else 0
            else:
                intraday_high = intraday_low = intraday_range = intraday_range_pct = 0
            
            summary = {
                "current_price": today_candle["close"] if today_candle else 0,
                "day_open": today_candle["open"] if today_candle else 0,
                "day_high": today_candle["high"] if today_candle else 0,
                "day_low": today_candle["low"] if today_candle else 0,
                "previous_close": yesterday_candle["close"] if yesterday_candle else 0,
                "day_change": (today_candle["close"] - yesterday_candle["close"]) if today_candle and yesterday_candle else 0,
                "day_change_pct": ((today_candle["close"] - yesterday_candle["close"]) / yesterday_candle["close"] * 100) if today_candle and yesterday_candle and yesterday_candle["close"] > 0 else 0,
                "ma_20": ma_20,
                "ma_50": ma_50,
                "intraday_high": intraday_high,
                "intraday_low": intraday_low,
                "intraday_range": intraday_range,
                "intraday_range_pct": intraday_range_pct,
                "data_source": "yahoo_finance",
                "update_frequency": "5_seconds"
            }
            
            # Cache the summary
            self._cache_data(cache_key, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get market summary: {e}")
            return {
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    
    def get_realtime_volume(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get real-time volume by aggregating 1-minute candles for the current 5-minute period"""
        try:
            cache_key = f"realtime_volume_{symbol}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Get 1-minute candles for the last hour (to cover current 5m period)
            candles_1m = self.get_klines(symbol, "1m", 60)
            if not candles_1m:
                return {
                    "error": "No 1-minute data available",
                    "data_source": "yahoo_finance"
                }
            
            # Get current 5-minute candle for reference
            candles_5m = self.get_klines(symbol, "5m", 10)
            current_5m = candles_5m[-1] if candles_5m else None
            
            # Calculate current 5-minute period boundaries
            now = datetime.now()
            current_minute = now.minute
            period_start_minute = (current_minute // 5) * 5  # Round down to nearest 5-minute mark
            
            # Create period boundaries
            period_start = now.replace(minute=period_start_minute, second=0, microsecond=0)
            period_end = period_start + timedelta(minutes=5)
            
            # Filter 1-minute candles for current 5-minute period
            period_candles = []
            total_volume = 0
            completed_volume = 0
            
            for candle in candles_1m:
                candle_time = datetime.fromtimestamp(candle["open_time"] / 1000)
                
                # Check if candle is within current 5-minute period
                if period_start <= candle_time < period_end:
                    period_candles.append(candle)
                    total_volume += candle["volume"]
                    
                    # If candle is completed (not current minute), add to completed volume
                    if candle_time < now.replace(second=0, microsecond=0):
                        completed_volume += candle["volume"]
            
            # Calculate volume metrics
            current_minute_volume = 0
            if period_candles:
                # Get current minute's volume (if available)
                current_minute_candles = [c for c in period_candles 
                                        if datetime.fromtimestamp(c["open_time"] / 1000).minute == current_minute]
                if current_minute_candles:
                    current_minute_volume = current_minute_candles[0]["volume"]
            
            # Calculate time progress in current 5-minute period
            time_elapsed = (now - period_start).total_seconds()
            period_progress = min(time_elapsed / 300, 1.0)  # 300 seconds = 5 minutes
            
            # ENHANCED: Real-time volume estimation for immediate spike detection
            estimated_current_volume = completed_volume
            
            # Strategy 1: Use current minute volume if available (most recent data)
            if current_minute_volume > 0:
                estimated_current_volume += current_minute_volume
                volume_source = "current_minute"
            # Strategy 2: Use previous 5-minute volume as baseline if current is 0
            elif completed_volume == 0 and len(candles_5m) >= 2:
                previous_5m_volume = candles_5m[-2]["volume"] if candles_5m[-2]["volume"] > 0 else 0
                # Estimate based on time progress and previous volume
                estimated_current_volume = previous_5m_volume * (period_progress / 1.0)
                volume_source = "previous_5m_estimate"
            # Strategy 3: Use recent 1-minute candles average as baseline
            elif completed_volume == 0 and len(candles_1m) >= 5:
                recent_volumes = [c["volume"] for c in candles_1m[-5:] if c["volume"] > 0]
                if recent_volumes:
                    avg_recent_volume = sum(recent_volumes) / len(recent_volumes)
                    estimated_current_volume = avg_recent_volume * period_progress
                    volume_source = "recent_1m_average"
                else:
                    volume_source = "no_data"
            else:
                volume_source = "no_data"
            
            # ENHANCED: Volume acceleration detection for immediate spike alerts
            volume_acceleration = 0
            if len(candles_1m) >= 10:
                # Compare last 3 minutes vs previous 3 minutes
                recent_3m_volume = sum([c["volume"] for c in candles_1m[-3:] if c["volume"] > 0])
                previous_3m_volume = sum([c["volume"] for c in candles_1m[-6:-3] if c["volume"] > 0])
                
                if previous_3m_volume > 0:
                    volume_acceleration = (recent_3m_volume - previous_3m_volume) / previous_3m_volume
            
            # ENHANCED: Immediate spike detection based on acceleration
            is_immediate_spike = False
            spike_reason = ""
            if volume_acceleration > 2.0:  # 200% increase
                is_immediate_spike = True
                spike_reason = f"VOLUME ACCELERATION: {volume_acceleration*100:.0f}% increase in last 3 minutes"
            elif estimated_current_volume > 0 and len(candles_1m) >= 20:
                # Compare against recent average
                recent_avg = sum([c["volume"] for c in candles_1m[-20:] if c["volume"] > 0]) / 20
                if recent_avg > 0 and estimated_current_volume > recent_avg * 3:  # 300% of average
                    is_immediate_spike = True
                    spike_reason = f"VOLUME SPIKE: {estimated_current_volume:.0f} vs avg {recent_avg:.0f}"
            
            volume_data = {
                "current_5m_period": period_start.strftime("%H:%M"),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "period_progress": round(period_progress * 100, 1),  # Percentage
                "total_volume": total_volume,
                "completed_volume": completed_volume,
                "current_minute_volume": current_minute_volume,
                "estimated_current_volume": estimated_current_volume,
                "candles_in_period": len(period_candles),
                "yahoo_5m_volume": current_5m["volume"] if current_5m else 0,
                "data_source": "yahoo_finance_1m_aggregation",
                "update_frequency": "5_seconds",
                # ENHANCED: Real-time spike detection data
                "volume_source": volume_source,
                "volume_acceleration": volume_acceleration,
                "is_immediate_spike": is_immediate_spike,
                "spike_reason": spike_reason,
                "recent_3m_volume": sum([c["volume"] for c in candles_1m[-3:] if c["volume"] > 0]),
                "previous_3m_volume": sum([c["volume"] for c in candles_1m[-6:-3] if c["volume"] > 0]) if len(candles_1m) >= 6 else 0
            }
            
            # Cache for 5 seconds
            self._cache_data(cache_key, volume_data)
            
            # Log immediate spike detection
            if is_immediate_spike:
                logger.warning(f"🚨 IMMEDIATE VOLUME SPIKE DETECTED: {spike_reason}")
                logger.warning(f"   Current: {estimated_current_volume:.0f}, Source: {volume_source}")
            
            logger.info(f"📊 Real-time volume: {estimated_current_volume:.0f} (progress: {volume_data['period_progress']}%, source: {volume_source})")
            return volume_data
            
        except Exception as e:
            logger.error(f"Failed to get real-time volume: {e}")
            return {
                "error": str(e),
                "data_source": "yahoo_finance"
            }


def main():
    """Test the Yahoo Finance data fetcher"""
    logger.info("🔍 Testing Yahoo Finance Data Fetcher (HISTORICAL DATA ONLY)")
    logger.info("=" * 60)
    
    fetcher = YahooDataFetcher()
    
    # Test connection
    if not fetcher.test_connection():
        logger.error("❌ Cannot connect to Yahoo Finance")
        return
    
    # Test market analysis with mock Hyperliquid price
    logger.info("📊 Getting market analysis...")
    mock_hyperliquid_price = 45000.0  # Mock price for testing
    analysis = fetcher.get_market_analysis("BTC", hyperliquid_price=mock_hyperliquid_price)
    
    if "error" not in analysis:
        logger.success("✅ Market analysis successful!")
        logger.info(f"Current Price (Hyperliquid): ${analysis['current_price']:,.2f}")
        logger.info(f"5m Trend: {analysis['trend_5m']['trend']} ({analysis['trend_5m']['strength']*100:.2f}%)")
        logger.info(f"1h Trend: {analysis['trend_1h']['trend']} ({analysis['trend_1h']['strength']*100:.2f}%)")
        logger.info(f"5m Support: ${analysis['support_resistance_5m']['support']:,.2f}")
        logger.info(f"5m Resistance: ${analysis['support_resistance_5m']['resistance']:,.2f}")
        logger.info(f"Market Condition: {analysis['market_condition']}")
        logger.info(f"Data Source: {analysis['data_source']}")
        logger.info(f"5m Candles: {len(analysis['candles_5m'])}")
        logger.info(f"1h Candles: {len(analysis['candles_1h'])}")
    else:
        logger.error(f"❌ Market analysis failed: {analysis['error']}")


if __name__ == "__main__":
    main()
