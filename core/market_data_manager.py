#!/usr/bin/env python3
"""
Centralized Market Data Manager
Eliminates redundant calculations and provides single source of truth for all market data
"""

import time
import statistics
from typing import Dict, List, Any, Optional
from loguru import logger
from core.analysis.real_time.volatility_calculator import VolatilityCalculator
from core.analysis.real_time.volume_calculator import VolumeCalculator
from core.analysis.real_time.pressure_calculator import PressureCalculator
from core.analysis.real_time.rsi_calculator import RSICalculator
from core.analysis.real_time.support_resistance_calculator import SupportResistanceCalculator
from core.analysis.real_time.trend_calculator import TrendCalculator

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
        
        # Initialize all calculators (consistent pattern)
        self.volatility_calculator = VolatilityCalculator()
        self.volume_calculator = VolumeCalculator()
        self.pressure_calculator = PressureCalculator()
        self.support_resistance_calculator = SupportResistanceCalculator()
        self.trend_calculator = TrendCalculator()
        # RSI calculator moved to global singleton to prevent multiple instances
        
        logger.info("📊 Market Data Manager initialized - Centralized data management with volume history tracking")
    
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
            
            # Get recent trades for actual trading volume calculation (always try this)
            recent_trades = []
            try:
                recent_trades = hyperliquid_api.get_recent_trades(symbol)
                logger.debug(f"Retrieved {len(recent_trades)} recent trades for trading volume calculation")
            except Exception as e:
                logger.warning(f"Failed to get recent trades: {e}")
                recent_trades = []
            
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
                        
                        # Use VolumeCalculator for volume categorization with historical data
                        volume_data = self.volume_calculator.categorize_orderbook_depth(
                            total_depth_5, bid_depth_5, ask_depth_5, historical_depths
                        )
                        volume_data["data_source"] = "hyperliquid_orderbook"
                        
                        # Add relative volume analysis
                        if len(historical_depths) >= 10:
                            relative_analysis = self.volume_calculator.calculate_relative_volume_analysis(
                                total_depth_5, historical_depths, current_price, historical_prices
                            )
                            volume_data.update(relative_analysis)
                        
                        # Use PressureCalculator for pressure analysis (proper delegation)
                        pressure_data = self.pressure_calculator.calculate_orderbook_pressure(bids, asks)
                        pressure_data["data_source"] = "hyperliquid_orderbook"
                    else:
                        volume_data = self._get_default_volume_data()
                        pressure_data = self._get_default_pressure_data()
                else:
                    volume_data = self._get_default_volume_data()
                    pressure_data = self._get_default_pressure_data()
            else:
                volume_data = self._get_default_volume_data()
                pressure_data = self._get_default_pressure_data()
            
            # Calculate actual trading volume from recent trades (always try this, regardless of orderbook status)
            if recent_trades:
                try:
                    trading_volume_analysis = self.volume_calculator.calculate_trading_volume_from_trades(
                        recent_trades, time_window_minutes=5
                    )
                    volume_data.update(trading_volume_analysis)
                    logger.debug(f"Trading volume calculated: {trading_volume_analysis.get('trading_volume_btc', 0)} BTC")
                except Exception as e:
                    logger.warning(f"Trading volume calculation failed: {e}")
                    # Add error indicators to volume data
                    volume_data.update({
                        "trading_volume_btc": 0.0,
                        "trading_volume_category": "ERROR",
                        "trade_count": 0,
                        "avg_trade_size": 0.0,
                        "time_window_minutes": 5,
                        "data_source": "error"
                    })
            else:
                logger.warning("No recent trades available for volume calculation")
                # Add no data indicators
                volume_data.update({
                    "trading_volume_btc": 0.0,
                    "trading_volume_category": "NO_DATA",
                    "trade_count": 0,
                    "avg_trade_size": 0.0,
                    "time_window_minutes": 5,
                    "data_source": "no_trades"
                })
            
            result = {
                "volume_data": volume_data,
                # volatility_data removed - using 5m candle volatility instead of orderbook volatility
                "pressure_data": pressure_data,
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
                "current_price": None,
                "timestamp": time.time()
            }
    
    def _get_default_volume_data(self) -> Dict[str, Any]:
        """Get default volume data when orderbook is unavailable"""
        return {
            "volume_depth": 0.0,
            "volume_category": "UNKNOWN",
            "bid_depth": 0.0,
            "ask_depth": 0.0,
            "bid_ask_ratio": 1.0,
            "depth_imbalance": 0.0,
            "order_flow": "NEUTRAL",
            "depth_analysis": "NO_DATA",
            "data_source": "default"
        }
    
    def _get_default_pressure_data(self) -> Dict[str, Any]:
        """Get default pressure data when orderbook is unavailable"""
        return self.pressure_calculator._get_default_pressure()
    
    def calculate_trend(self, candles: List[Dict], timeframe: str = "5m") -> Dict[str, Any]:
        """Calculate trend using TrendCalculator (SRP - delegate to calculator)"""
        cache_key = f"trend_{timeframe}_{hash(str(candles[-10:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        # Delegate to TrendCalculator (ALL calculation logic in calculator)
        result = self.trend_calculator.calculate_trend(candles, timeframe)
        self._cache_data(cache_key, result, self._indicator_cache_duration)
        return result
    
    def clear_trend_cache(self):
        """Clear trend calculation cache to force fresh calculations"""
        try:
            # Clear all trend-related cache entries
            keys_to_remove = [key for key in self._cache.keys() if key.startswith("trend_")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"🧹 Cleared {len(keys_to_remove)} trend cache entries")
        except Exception as e:
            logger.error(f"❌ Failed to clear trend cache: {e}")
    
    def calculate_volatility(self, candles: List[Dict], periods: int = 20) -> float:
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

    def get_yahoo_data_with_analysis(self, yahoo_fetcher, symbol: str = "BTC", hyperliquid_price: float = None) -> Dict[str, Any]:
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
            
            # Get trend analysis using TrendCalculator (proper delegation)
            trend_5m = self.calculate_trend(candles_5m, "5m") if candles_5m else {"trend": "NEUTRAL"}
            trend_1h = self.calculate_trend(candles_1h, "1h") if candles_1h else {"trend": "NEUTRAL"}
            
            # Calculate RSI from Yahoo 5m candles (using global RSICalculator directly)
            rsi_5m = global_rsi_calculator.calculate_standalone_rsi(candles_5m)
            logger.debug(f"📊 Yahoo analysis RSI calculated: {rsi_5m:.2f} from 5m candles")
            
            # Calculate volume analysis using VolumeCalculator (proper delegation)
            volumes_5m = [candle["volume"] for candle in candles_5m if "volume" in candle]
            if volumes_5m:
                current_volume_5m = volumes_5m[-1]
                volume_analysis_5m = self.volume_calculator.categorize_yahoo_volume(current_volume_5m, volumes_5m)
                volume_momentum_5m = self.volume_calculator.calculate_volume_momentum(volumes_5m)
                volume_spike_5m = self.volume_calculator.detect_volume_spikes(current_volume_5m, volumes_5m)
                relative_volume_5m = self.volume_calculator.calculate_relative_volume(current_volume_5m, volumes_5m)
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
