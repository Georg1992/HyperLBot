#!/usr/bin/env python3
"""
Centralized Market Data Manager
Eliminates redundant calculations and provides single source of truth for all market data
"""

import time
from typing import Dict, List, Any, Optional
from loguru import logger
from core.analysis.real_time.volatility_calculator import VolatilityCalculator
from core.analysis.real_time.volume_calculator import VolumeCalculator
from core.analysis.real_time.pressure_calculator import PressureCalculator
from core.analysis.real_time.rsi_calculator import RSICalculator
from core.analysis.real_time.support_resistance_calculator import SupportResistanceCalculator
from core.analysis.real_time.trend_calculator import TrendCalculator
from core.analysis.real_time.orderbook_analyzer import OrderBookAnalyzer
from core.analysis.real_time.funding_rate_analyzer import FundingRateAnalyzer
from core.analysis.real_time.volume_profile_analyzer import VolumeProfileAnalyzer

from core.constants import technical_constants

# Global RSI calculator instance (single source of truth for RSI)
global_rsi_calculator = RSICalculator()

class MarketDataManager:
    """Centralized market data manager to eliminate redundant calculations"""
    
    def __init__(self):
        # Cache for market data to avoid redundant API calls
        self._market_data_cache = {}
        self._cache_timestamps = {}
        self._cache_duration = 5  # 5 seconds cache for real-time data
        
        # Cache for calculated indicators
        self._indicator_cache = {}
        self._indicator_timestamps = {}
        self._indicator_cache_duration = 60  # 1 minute for calculated indicators
        
        # Volume history tracking for noise reduction and relative analysis
        self._volume_history = []  # List of (timestamp, depth, price) tuples
        self._max_volume_history = 100  # Keep last 100 volume readings
        
        # Rolling window for historical candles (keep last 12)
        self._candle_buffer = []
        self._max_candles = 12
        
        # Initialize all calculators (consistent pattern)
        self.volatility_calculator = VolatilityCalculator()
        self.volume_calculator = VolumeCalculator()
        self.pressure_calculator = PressureCalculator()
        self.support_resistance_calculator = SupportResistanceCalculator()
        self.trend_calculator = TrendCalculator()
        self.orderbook_analyzer = OrderBookAnalyzer()
        self.funding_rate_analyzer = FundingRateAnalyzer()
        self.volume_profile_analyzer = VolumeProfileAnalyzer()
        # RSI calculator moved to global singleton to prevent multiple instances
        
        logger.info("📊 Market Data Manager initialized - Centralized data management with volume history tracking")
    
    def get_historical_candles(self, symbol: str = "BTC", interval: str = "5m", limit: int = 12, force_refresh: bool = False, include_ongoing: bool = True) -> List[Dict[str, Any]]:
        """
        Get historical candles with simple 12-candle rolling window
        
        Simple approach:
        - Always show exactly 12 candles: 11 historical + 1 current ongoing
        - Remove oldest candle when new one completes
        
        Args:
            symbol: Trading symbol (default: BTC)
            interval: Candle interval (default: 5m)
            limit: Number of candles to return (default: 12)
            force_refresh: Force refresh from API (default: False)
            include_ongoing: Include current ongoing candle (default: True)
            
        Returns:
            List of exactly 12 candle dictionaries: 11 historical + 1 ongoing
        """
        try:
            # Check if we have recent data and don't need to refresh
            if not force_refresh and self._candle_buffer and len(self._candle_buffer) >= limit:
                # Check if the latest candle is recent (within last 5 minutes for 5m candles)
                latest_candle_time = self._candle_buffer[-1].get('timestamp', 0)
                current_time = time.time()
                time_diff = current_time - latest_candle_time
                
                # For 5m candles, only refresh if more than 4 minutes have passed
                if interval == "5m" and time_diff < 240:  # 4 minutes
                    # logger.debug(f"🕯️ Using cached candles (age: {time_diff:.0f}s)")
                    return self._candle_buffer
            
            from core.api.hyperliquid_api import HyperliquidAPI
            
            # Create Hyperliquid API instance
            hyperliquid_api = HyperliquidAPI()
            
            # Fetch latest candles from Hyperliquid (get enough for 12-candle window)
            logger.info(f"🕯️ Fetching {interval} candles for {symbol}...")
            new_candles = hyperliquid_api.get_historical_candles(
                symbol=symbol,
                interval=interval,
                limit=12  # Get exactly 12 candles
            )
            
            if not new_candles or len(new_candles) < 12:
                logger.error(f"❌ Insufficient data from Hyperliquid: {len(new_candles) if new_candles else 0} candles (need 12)")
                raise Exception(f"Hyperliquid API returned insufficient data: {len(new_candles) if new_candles else 0} candles")
            
            # Simple 12-candle rolling window: always return exactly 12 candles
            latest_candles = new_candles[-12:]
            logger.info(f"🕯️ Simple rolling window: {len(latest_candles)} candles")
            
            # Mark the last candle as ongoing if it's the current incomplete candle
            if latest_candles:
                current_time = time.time()
                interval_seconds = 300 if interval == "5m" else 60  # 5m = 300s, 1m = 60s
                last_candle_time = latest_candles[-1].get('timestamp', 0)
                time_since_last = current_time - last_candle_time
                
                # If last candle is very recent (within 5 minutes for 5m candles), mark as ongoing
                if time_since_last < interval_seconds:
                    latest_candles[-1]['is_ongoing'] = True
                    logger.debug(f"🕯️ Marked last candle as ongoing (age: {time_since_last:.0f}s)")
            
            # Update our buffer with the latest candles
            self._candle_buffer = latest_candles
            
            logger.info(f"✅ Growing window updated: {len(self._candle_buffer)} candles, price range: ${min(c['low'] for c in self._candle_buffer):.2f} - ${max(c['high'] for c in self._candle_buffer):.2f}")
            return self._candle_buffer
            
        except Exception as e:
            logger.error(f"❌ Historical candle fetch failed: {e}")
            raise Exception(f"Failed to fetch historical candle data: {e}")
    
    def get_ongoing_candle(self) -> Optional[Dict[str, Any]]:
        """Get the current ongoing candle (for layering with 1st prediction)"""
        return getattr(self, '_ongoing_candle', None)
    
    def _update_volume_history(self, timestamp: float, depth: float, price: float):
        """Update volume history for noise reduction and relative analysis"""
        try:
            # Add new entry
            self._volume_history.append((timestamp, depth, price))
            
            # Remove old entries (keep only recent ones)
            if len(self._volume_history) > self._max_volume_history:
                self._volume_history = self._volume_history[-self._max_volume_history:]
                
        except Exception as e:
            logger.warning(f"Volume history update failed: {e}")
    
    def _get_cached_data(self, key: str, cache_duration: int) -> Optional[Dict]:
        """Get cached data if still valid"""
        if key in self._market_data_cache:
            timestamp = self._cache_timestamps.get(key, 0)
            if time.time() - timestamp < cache_duration:
                return self._market_data_cache[key]
        return None
    
    def _cache_data(self, key: str, data: Dict, cache_duration: int):
        """Cache data with timestamp"""
        self._market_data_cache[key] = data
        self._cache_timestamps[key] = time.time()
    
    def get_hyperliquid_data(self, hyperliquid_api, symbol: str = "BTC") -> Dict[str, Any]:
        """Get all Hyperliquid data with caching to avoid redundant API calls"""
        # Check if hyperliquid_api is None - show explicit error instead of crashing
        if hyperliquid_api is None:
            logger.error(f"❌ HyperliquidAPI is None - cannot fetch data for {symbol}")
            return {
                "volume_data": {},
                # volatility_data removed - using 5m candle volatility instead of orderbook volatility
                "pressure_data": {},
                "current_price": None,
                "timestamp": time.time(),
                "error": "HyperliquidAPI not initialized"
            }
        
        cache_key = f"hyperliquid_{symbol}"
        cached_data = self._get_cached_data(cache_key, self._cache_duration)
        
        if cached_data:
            return cached_data
        
        try:
            # Get raw orderbook data and use calculators for analysis (clean architecture)
            market_data = hyperliquid_api.get_market_data(symbol)
            
            # Note: Recent trades removed - using CoinGecko for accurate volume data
            
            # Use VolumeCalculator and PressureCalculator for orderbook analysis (clean architecture)
            if market_data and 'levels' in market_data:
                levels = market_data['levels']
                if len(levels) >= 2:
                    bids = levels[0] if isinstance(levels[0], list) else []
                    asks = levels[1] if isinstance(levels[1], list) else []
                    
                    if bids and asks:
                        # Calculate orderbook depths
                        bid_depth_5 = sum(float(level['sz']) for level in bids[:5])
                        ask_depth_5 = sum(float(level['sz']) for level in asks[:5])
                        total_depth_5 = bid_depth_5 + ask_depth_5
                        
                        # Update volume history for noise reduction
                        current_time = time.time()
                        current_price = market_data.get('markPrice', 0) if 'markPrice' in market_data else 0
                        self._update_volume_history(current_time, total_depth_5, current_price)
                        
                        # Get historical depths for smoothing
                        historical_depths = [entry[1] for entry in self._volume_history[-20:]]  # Last 20 readings
                        historical_prices = [entry[2] for entry in self._volume_history[-20:]]
                        
                        # Initialize volume data - will be populated by CoinGecko volume calculation below
                        volume_data = {"data_source": "coingecko"}
                        
                        # Use PressureCalculator for pressure analysis (proper delegation)
                        pressure_data = self.pressure_calculator.calculate_orderbook_pressure(bids, asks)
                        pressure_data["data_source"] = "hyperliquid_orderbook"
                        
                        # Use OrderBookAnalyzer for comprehensive order book analysis
                        current_price = market_data.get('markPrice', 0) if 'markPrice' in market_data else 0
                        orderbook_analysis = self.orderbook_analyzer.analyze_orderbook(market_data, current_price)
                        
                        # Get and analyze funding rate data
                        funding_data = hyperliquid_api.get_funding_rate(symbol)
                        funding_analysis = self.funding_rate_analyzer.analyze_funding_rate(funding_data)
                        
                        # Get and analyze volume profile from recent trades
                        trades_data = hyperliquid_api.get_recent_trades(symbol, limit=100)
                        if trades_data and isinstance(trades_data, list):
                            volume_profile_analysis = self.volume_profile_analyzer.analyze_volume_profile(trades_data, current_price)
                        else:
                            volume_profile_analysis = self._get_default_volume_profile_analysis()
                    else:
                        volume_data = self._get_default_volume_data()
                        pressure_data = self._get_default_pressure_data()
                        orderbook_analysis = self._get_default_orderbook_analysis()
                        funding_analysis = self._get_default_funding_analysis()
                        volume_profile_analysis = self._get_default_volume_profile_analysis()
                else:
                    volume_data = self._get_default_volume_data()
                    pressure_data = self._get_default_pressure_data()
                    orderbook_analysis = self._get_default_orderbook_analysis()
                    funding_analysis = self._get_default_funding_analysis()
                    volume_profile_analysis = self._get_default_volume_profile_analysis()
            else:
                volume_data = self._get_default_volume_data()
                pressure_data = self._get_default_pressure_data()
                orderbook_analysis = self._get_default_orderbook_analysis()
                funding_analysis = self._get_default_funding_analysis()
                volume_profile_analysis = self._get_default_volume_profile_analysis()
            
            # Get volume data from Hyperliquid candles (more reliable than Binance WebSocket)
            try:
                # Check cache for volume data (cache for 30 seconds)
                volume_cache_key = f"volume_data_{symbol}"
                cached_volume = self._get_cached_data(volume_cache_key, 30)
                
                if cached_volume:
                    volume_data = cached_volume
                else:
                    # Get recent candles to calculate volume per minute
                    candles = hyperliquid_api.get_historical_candles(symbol, "5m", 5)
                    if candles and len(candles) >= 3:
                        # Calculate average volume per minute from recent 5m candles
                        recent_volumes = [candle.get('volume', 0) for candle in candles[-3:]]
                        avg_5m_volume = sum(recent_volumes) / len(recent_volumes)
                        volume_per_minute = avg_5m_volume / 5  # Convert 5m volume to per minute
                        volume_per_second = volume_per_minute / 60
                        
                        # Calculate volume category using VolumeCalculator
                        volume_spike_result = self.volume_calculator.detect_volume_spike_from_binance(volume_per_minute, [])
                        
                        # Update volume data with Hyperliquid candle data
                        volume_data.update({
                            "current_volume_btc": volume_per_minute,
                            "current_volume_usd": volume_per_minute * market_data.get('markPrice', 0),
                            "real_time_volume_btc": volume_per_minute,
                            "real_time_volume_usd": volume_per_minute * market_data.get('markPrice', 0),
                            "volume_per_minute": volume_per_minute,
                            "volume_per_second": volume_per_second,
                            "trade_count_per_minute": 0,  # Not available from candles
                            "volume_spike_detected": volume_spike_result.get('volume_spike_detected', False),
                            "volume_ratio": volume_spike_result.get('volume_ratio', 1.0),
                            "volume_category": volume_spike_result.get('volume_category', 'UNKNOWN'),
                            "data_source": "hyperliquid_candles",
                            "timestamp": time.time()
                        })
                        
                        # Cache the volume data
                        self._cache_data(volume_cache_key, volume_data, 30)  # 30 second cache
                        
                        # logger.info(f"📊 Hyperliquid volume: {volume_per_minute:.1f} BTC/min → {volume_spike_result.get('volume_category', 'UNKNOWN')}")  # Dashboard shows this
                    else:
                        logger.warning("⚠️ Not enough Hyperliquid candles for volume calculation")
                    
            except Exception as e:
                logger.warning(f"⚠️ Hyperliquid volume calculation failed: {e}")
                
                # Fallback to Binance WebSocket if Hyperliquid fails
                try:
                    if not hasattr(self, 'binance_api'):
                        from core.external.binance_api import binance_api
                        self.binance_api = binance_api
                    
                    real_time_volume = self.binance_api.get_real_time_volume()
                    current_volume_btc = real_time_volume.get('current_volume_btc', 0)
                    volume_spike_result = self.volume_calculator.detect_volume_spike_from_binance(current_volume_btc, [])
                    
                    volume_data.update({
                        "current_volume_btc": current_volume_btc,
                        "real_time_volume_btc": current_volume_btc,
                        "volume_per_minute": current_volume_btc,
                        "volume_spike_detected": real_time_volume.get('volume_spike_detected', False),
                        "volume_ratio": real_time_volume.get('volume_ratio', 1.0),
                        "volume_category": volume_spike_result.get('volume_category', 'UNKNOWN'),
                        "data_source": "binance_fallback"
                    })
                    
                    logger.debug(f"Binance fallback volume: {current_volume_btc:.1f} BTC/min")
                except Exception as e2:
                    logger.error(f"❌ Both Hyperliquid and Binance volume failed: {e2}")
                # Continue with orderbook data (fallback for scalping)
            
            result = {
                "volume_data": volume_data,
                # volatility_data removed - using 5m candle volatility instead of orderbook volatility
                "pressure_data": pressure_data,
                "orderbook_analysis": orderbook_analysis if 'orderbook_analysis' in locals() else self._get_default_orderbook_analysis(),
                "funding_analysis": funding_analysis if 'funding_analysis' in locals() else self._get_default_funding_analysis(),
                "volume_profile_analysis": volume_profile_analysis if 'volume_profile_analysis' in locals() else self._get_default_volume_profile_analysis(),
                "timestamp": time.time()
            }
            
            # Cache the result
            self._cache_data(cache_key, result, self._cache_duration)
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid data: {e}")
            return {
                "volume_data": self._get_default_volume_data(),
                "pressure_data": self._get_default_pressure_data(),
                "orderbook_analysis": self._get_default_orderbook_analysis(),
                "funding_analysis": self._get_default_funding_analysis(),
                "volume_profile_analysis": self._get_default_volume_profile_analysis(),
                "current_price": None,
                "timestamp": time.time()
            }
    
    def _get_default_volume_data(self) -> Dict[str, Any]:
        """Get default volume data when CoinGecko is unavailable"""
        return {
            "current_volume_usd": 0,
            "current_volume_btc": 0,
            "volume_spike_detected": False,
            "volume_ratio": 1.0,
            "volume_category": "UNKNOWN",
            "data_source": "default"
        }
    
    def _get_default_pressure_data(self) -> Dict[str, Any]:
        """Get default pressure data when orderbook is unavailable"""
        return self.pressure_calculator._get_default_pressure()
    
    def _get_default_orderbook_analysis(self) -> Dict[str, Any]:
        """Get default order book analysis when data is unavailable"""
        return {
            "bid_ask_spread": {"absolute": 0.0, "percentage": 0.0, "category": "UNKNOWN"},
            "order_imbalance": {"ratio": 1.0, "category": "BALANCED", "bias": 0.0},
            "liquidity_depth": {"depth_score": 0.0, "category": "LOW", "levels_analyzed": 0},
            "market_pressure": {"pressure": 0.0, "direction": "NEUTRAL", "strength": "WEAK"},
            "support_resistance_strength": {"support_strength": 0.0, "resistance_strength": 0.0, "category": "WEAK"},
            "timestamp": time.time(),
            "data_source": "default_fallback"
        }
    
    def _get_default_funding_analysis(self) -> Dict[str, Any]:
        """Get default funding rate analysis when data is unavailable"""
        return {
            "current_funding_rate": 0.0,
            "current_funding_rate_pct": 0.0,
            "funding_trend": {"trend": "UNKNOWN", "direction": "NEUTRAL", "strength": 0.0},
            "funding_sentiment": {"sentiment": "UNKNOWN", "description": "No data", "risk_level": "UNKNOWN"},
            "extreme_funding_detection": {"is_extreme": False, "extreme_type": "NORMAL", "description": "No data"},
            "funding_volatility": {"volatility": 0.0, "category": "UNKNOWN"},
            "next_funding_time": 0,
            "data_source": "default_fallback",
            "timestamp": time.time()
        }
    
    def _get_default_volume_profile_analysis(self) -> Dict[str, Any]:
        """Get default volume profile analysis when data is unavailable"""
        return {
            "trade_size_distribution": {"distribution": "UNKNOWN", "categories": {}},
            "trade_flow_analysis": {"flow": "UNKNOWN", "direction": "NEUTRAL", "strength": "WEAK"},
            "volume_weighted_price": {"vwap": 0.0, "deviation": 0.0, "category": "UNKNOWN"},
            "large_trade_detection": {"large_trades": [], "count": 0, "impact": "UNKNOWN"},
            "trade_frequency_analysis": {"frequency": "UNKNOWN", "pattern": "UNKNOWN"},
            "market_microstructure": {"microstructure": "UNKNOWN", "characteristics": []},
            "timestamp": time.time(),
            "data_source": "default_fallback"
        }
    
    def calculate_trend(self, candles: List[Dict], timeframe: str = "5m", strategy_name: str = "standard") -> Dict[str, Any]:
        """Calculate strategy-specific trend using TrendCalculator (SRP - delegate to calculator)"""
        cache_key = f"trend_{timeframe}_{strategy_name}_{hash(str(candles[-10:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        # Delegate to TrendCalculator with strategy-specific parameters (ALL calculation logic in calculator)
        result = self.trend_calculator.calculate_trend(candles, timeframe, strategy_name)
        self._cache_data(cache_key, result, self._indicator_cache_duration)
        return result
    
    
    def calculate_volatility(self, candles: List[Dict], periods: int = 6) -> float:
        """Calculate volatility using VolatilityCalculator (SRP - delegate to calculator)"""
        cache_key = f"volatility_{periods}_{hash(str(candles[-periods:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            # Delegate directly to VolatilityCalculator (handles minimum candle requirements internally)
            result = self.volatility_calculator.calculate_candle_volatility(candles, "5m")
            self._cache_data(cache_key, result, self._indicator_cache_duration)
            return result
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation failed: {e}")
            return 0.0
    
    def calculate_support_resistance(self, candles: List[Dict], lookback: int = 20) -> Dict[str, float]:
        """Calculate support/resistance using SupportResistanceCalculator (SRP - delegate to calculator)"""
        cache_key = f"support_resistance_{lookback}_{hash(str(candles[-lookback:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        # Delegate to SupportResistanceCalculator (ALL calculation logic in calculator)
        result = self.support_resistance_calculator.calculate_support_resistance(candles, lookback)
        self._cache_data(cache_key, result, self._indicator_cache_duration)
        return result
    
# CLEANED: RSI wrapper methods removed - use global_rsi_calculator directly (SRP)
# All RSI calculations now happen in RSICalculator (single responsibility)

    # _categorize_5m_volatility_for_trading() moved to VolatilityCalculator (proper volatility logic location)

    def get_hyperliquid_volatility_analysis(self, hyperliquid_candles: List[Dict], symbol: str = "BTC", strategy_name: str = "standard") -> Dict[str, Any]:
        """
        Get multi-timeframe volatility analysis from Hyperliquid candle data (REAL-TIME DATA)
        This method uses actual market data instead of stale Yahoo data
        """
        try:
            if not hyperliquid_candles or len(hyperliquid_candles) < 3:
                logger.warning("⚠️ Not enough Hyperliquid candles for volatility analysis")
                return self._get_default_volatility_analysis("hyperliquid_insufficient_data")
            
            # Calculate volatility from REAL Hyperliquid data
            volatility_5m = self.calculate_volatility(hyperliquid_candles)
            volatility_5m_category, volatility_5m_trend = self.volatility_calculator.categorize_volatility_for_trading(volatility_5m, "5m")
            
            logger.info(f"📊 Hyperliquid 5m volatility: {volatility_5m:.6f} ({volatility_5m*100:.4f}%) → {volatility_5m_category}")
            
            return {
                "volatility_5m": volatility_5m,
                "volatility_5m_category": volatility_5m_category,
                "volatility_5m_trend": volatility_5m_trend,
                "data_source": "hyperliquid_real_time"
            }
            
        except Exception as e:
            logger.error(f"❌ Hyperliquid volatility analysis failed: {e}")
            return self._get_default_volatility_analysis("hyperliquid_error")
    
    def get_multi_timeframe_volatility_analysis(self, hyperliquid_api, symbol: str = "BTC", strategy_name: str = "standard") -> Dict[str, Any]:
        """
        Get comprehensive multi-timeframe volatility analysis from Hyperliquid data
        Calculates 1m, 5m, 1h, and 1d volatility for complete market context
        CACHED to avoid excessive API calls
        """
        try:
            # Check cache first (cache for 2 minutes to avoid excessive API calls)
            cache_key = f"multi_volatility_{symbol}_{strategy_name}"
            cached_result = self._get_cached_data(cache_key, 120)  # 2 minute cache
            
            if cached_result:
                return cached_result
            
            # Fetch candles for all timeframes (only when cache expires)
            candles_1m = hyperliquid_api.get_historical_candles(symbol, "1m", 20)  # 20 minutes
            candles_5m = hyperliquid_api.get_historical_candles(symbol, "5m", 12)  # 1 hour
            candles_1h = hyperliquid_api.get_historical_candles(symbol, "1h", 24)  # 1 day
            candles_1d = hyperliquid_api.get_historical_candles(symbol, "1d", 7)   # 1 week
            
            volatility_analysis = {
                "data_source": "hyperliquid_multi_timeframe",
                "timestamp": time.time()
            }
            
            # Calculate 1-minute volatility (for scalping)
            if candles_1m and len(candles_1m) >= 3:
                volatility_1m = self.calculate_volatility(candles_1m)
                volatility_1m_category, volatility_1m_trend = self.volatility_calculator.categorize_volatility_for_trading(volatility_1m, "1m")
                volatility_analysis.update({
                    "volatility_1m": volatility_1m,
                    "volatility_1m_category": volatility_1m_category,
                    "volatility_1m_trend": volatility_1m_trend
                })
                # logger.debug(f"📊 1m volatility: {volatility_1m:.6f} ({volatility_1m*100:.4f}%) → {volatility_1m_category}")
            else:
                volatility_analysis.update(self._get_default_timeframe_volatility("1m"))
            
            # Calculate 5-minute volatility (for position management)
            if candles_5m and len(candles_5m) >= 3:
                volatility_5m = self.calculate_volatility(candles_5m)
                volatility_5m_category, volatility_5m_trend = self.volatility_calculator.categorize_volatility_for_trading(volatility_5m, "5m")
                volatility_analysis.update({
                    "volatility_5m": volatility_5m,
                    "volatility_5m_category": volatility_5m_category,
                    "volatility_5m_trend": volatility_5m_trend
                })
                # logger.info(f"📊 5m volatility: {volatility_5m:.6f} ({volatility_5m*100:.4f}%) → {volatility_5m_category}")  # Dashboard shows this
            else:
                volatility_analysis.update(self._get_default_timeframe_volatility("5m"))
            
            # Calculate 1-hour volatility (for trend confirmation)
            if candles_1h and len(candles_1h) >= 3:
                volatility_1h = self.calculate_volatility(candles_1h)
                volatility_1h_category, volatility_1h_trend = self.volatility_calculator.categorize_volatility_for_trading(volatility_1h, "1h")
                volatility_analysis.update({
                    "volatility_1h": volatility_1h,
                    "volatility_1h_category": volatility_1h_category,
                    "volatility_1h_trend": volatility_1h_trend
                })
                # logger.debug(f"📊 1h volatility: {volatility_1h:.6f} ({volatility_1h*100:.4f}%) → {volatility_1h_category}")
            else:
                volatility_analysis.update(self._get_default_timeframe_volatility("1h"))
            
            # Calculate daily volatility (for market context)
            if candles_1d and len(candles_1d) >= 3:
                volatility_1d = self.calculate_volatility(candles_1d)
                volatility_1d_category, volatility_1d_trend = self.volatility_calculator.categorize_volatility_for_trading(volatility_1d, "1d")
                volatility_analysis.update({
                    "volatility_1d": volatility_1d,
                    "volatility_1d_category": volatility_1d_category,
                    "volatility_1d_trend": volatility_1d_trend
                })
                # logger.debug(f"📊 1d volatility: {volatility_1d:.6f} ({volatility_1d*100:.4f}%) → {volatility_1d_category}")
            else:
                volatility_analysis.update(self._get_default_timeframe_volatility("1d"))
            
            # Cache the result to avoid excessive API calls
            self._cache_data(cache_key, volatility_analysis, 120)  # 2 minute cache
            
            return volatility_analysis
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe volatility analysis failed: {e}")
            return self._get_default_volatility_analysis("hyperliquid_error")
    
    def _get_default_volatility_analysis(self, data_source: str) -> Dict[str, Any]:
        """Get default volatility analysis when data is unavailable"""
        return {
            "volatility_5m": 0.0,
            "volatility_5m_category": "UNKNOWN",
            "volatility_5m_trend": "UNKNOWN",
            "data_source": data_source
        }
    
    def _get_default_timeframe_volatility(self, timeframe: str) -> Dict[str, Any]:
        """Get default volatility data for a specific timeframe"""
        return {
            f"volatility_{timeframe}": 0.0,
            f"volatility_{timeframe}_category": "UNKNOWN",
            f"volatility_{timeframe}_trend": "UNKNOWN"
        }

    def get_yahoo_data_with_analysis(self, yahoo_fetcher, symbol: str = "BTC", hyperliquid_price: float = None, strategy_name: str = "standard") -> Dict[str, Any]:
        """
        Get Yahoo data with centralized analysis calculations
        This method consolidates Yahoo data fetching with MarketDataManager calculations
        Eliminates circular dependency by having MarketDataManager orchestrate the process
        """
        cache_key = f"yahoo_analysis_{symbol}_{int(time.time() / 300)}"  # 5-minute cache
        cached_result = self._get_cached_data(cache_key, self._cache_duration)
        
        if cached_result:
            return cached_result
            
        try:
            # Get raw candle data from Yahoo (no calculations)
            candles_1m = yahoo_fetcher.get_klines(f"{symbol}-USD", "1m", 120)  
            candles_5m = yahoo_fetcher.get_klines(f"{symbol}-USD", "5m", 30)  # 30 candles for proper RSI calculation
            candles_1h = yahoo_fetcher.get_klines(f"{symbol}-USD", "1h", 84)
            candles_1d = yahoo_fetcher.get_klines(f"{symbol}-USD", "1d", 45)
            
            # Consolidated Yahoo fetch logging (single clean message)
            logger.info(f"📊 Yahoo data: {len(candles_1m)}×1m, {len(candles_5m)}×5m, {len(candles_1h)}×1h, {len(candles_1d)}×1d candles retrieved")
            
            if not candles_5m:
                return {"error": "No Yahoo candle data available"}
                
            # Do all calculations centrally here instead of in YahooDataFetcher
            current_price = hyperliquid_price or candles_5m[-1]["close"]
            
            # Calculate indicators using centralized methods
            support_resistance_5m = self.calculate_support_resistance(candles_5m)
            support_resistance_1h = self.calculate_support_resistance(candles_1h) if candles_1h else {"support": 0, "resistance": 0}
            support_resistance_1d = self.calculate_support_resistance(candles_1d) if candles_1d else {"support": 0, "resistance": 0}
            
            volatility_5m = self.calculate_volatility(candles_5m)
            volatility_1h = self.calculate_volatility(candles_1h) if candles_1h else 0.0
            volatility_1d = self.calculate_volatility(candles_1d) if candles_1d else 0.0
            
            # Add 5-minute trading categorization (use VolatilityCalculator for volatility expertise)
            volatility_5m_category, volatility_5m_trend = self.volatility_calculator.categorize_5m_volatility_for_trading(volatility_5m)
            
            # Get strategy-specific trend analysis using TrendCalculator (proper delegation)
            trend_5m = self.calculate_trend(candles_5m, "5m", strategy_name) if candles_5m else {"trend": "NEUTRAL"}
            trend_1h = self.calculate_trend(candles_1h, "1h", strategy_name) if candles_1h else {"trend": "NEUTRAL"}
            
            # Calculate RSI from Yahoo 5m candles (using global RSICalculator directly)
            rsi_5m = global_rsi_calculator.calculate_standalone_rsi(candles_5m)
            # logger.debug(f"📊 Yahoo analysis RSI calculated: {rsi_5m:.2f} from 5m candles")
            
            # Volume analysis now handled by CoinGecko - Yahoo volume methods removed
            volumes_5m = [candle["volume"] for candle in candles_5m if "volume" in candle]
            if volumes_5m:
                current_volume_5m = volumes_5m[-1]
                volume_momentum_5m = self.volume_calculator.calculate_volume_momentum(volumes_5m)
                relative_volume_5m = self.volume_calculator.calculate_relative_volume(current_volume_5m, volumes_5m)
                # Yahoo volume categorization removed - using CoinGecko volume data instead
                volume_analysis_5m = {"current_volume": current_volume_5m, "volume_category": "YAHOO_DATA", "volume_trend": "UNKNOWN", "data_source": "yahoo"}
                volume_spike_5m = {"has_spike": False, "spike_magnitude": 1.0, "spike_type": "NORMAL"}
            else:
                volume_analysis_5m = {"current_volume": 0, "volume_category": "UNKNOWN", "volume_trend": "UNKNOWN", "data_source": "no_data"}
                volume_momentum_5m = {"momentum": 0.0, "acceleration": 0.0, "trend": "UNKNOWN"}
                volume_spike_5m = {"has_spike": False, "spike_magnitude": 1.0, "spike_type": "NORMAL"}
                relative_volume_5m = 1.0
            
            # Build consolidated analysis
            analysis = {
                "timestamp": time.time(),
                "symbol": symbol,
                "current_price": current_price,
                "yahoo_last_close": candles_5m[-1]["close"],
                
                # Raw candle data
                "candles_1m": candles_1m or [],
                "candles_5m": candles_5m or [],
                "candles_1h": candles_1h or [],
                "candles_1d": candles_1d or [],
                
                # Calculated indicators (centralized)
                "support_resistance_5m": support_resistance_5m,
                "support_resistance_1h": support_resistance_1h,
                "support_resistance_1d": support_resistance_1d,
                "volatility_5m": volatility_5m,
                "volatility_5m_category": volatility_5m_category,
                "volatility_5m_trend": volatility_5m_trend,
                "volatility_1h": volatility_1h,
                "volatility_1d": volatility_1d,
                "trend_5m": trend_5m,
                "trend_1h": trend_1h,
                "rsi_5m": rsi_5m,
                
                # Volume analysis (using VolumeCalculator - proper delegation)
                "volume_5m_analysis": volume_analysis_5m,
                "volume_5m_momentum": volume_momentum_5m,
                "volume_5m_spike": volume_spike_5m,
                "relative_volume_5m": relative_volume_5m,
                
                "data_source": "centralized_market_data_manager"
            }
            
            # Cache result and return
            self._cache_data(cache_key, analysis, self._cache_duration)
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo data with analysis: {e}")
            return {"error": str(e)}

    def clear_cache(self, cache_type: str = "all"):
        """Clear cache to force fresh data (useful when constants change)"""
        if cache_type in ["all", "market_data"]:
            self._market_data_cache.clear()
            self._cache_timestamps.clear()
            logger.info("🧹 MarketDataManager cache cleared - will get fresh data")
        
        if cache_type in ["all", "indicators"]:
            self._indicator_cache.clear()
            self._indicator_timestamps.clear()
            logger.info("🧹 MarketDataManager indicator cache cleared")

    def get_cache_status(self) -> Dict[str, Any]:
        """Get simplified cache status for monitoring"""
        return {
            "market_data_entries": len(self._market_data_cache),
            "indicator_entries": len(self._indicator_cache),
            "total_entries": len(self._market_data_cache) + len(self._indicator_cache),
            "cache_age_range": f"{min(time.time() - t for t in self._cache_timestamps.values()):.1f}-{max(time.time() - t for t in self._cache_timestamps.values()):.1f}s" if self._cache_timestamps else "empty"
        }

# Global instances
market_data_manager = MarketDataManager()
# Note: global_rsi_calculator is defined above for single source of truth
