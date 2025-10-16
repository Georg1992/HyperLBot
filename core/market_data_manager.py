#!/usr/bin/env python3
"""
Market Data Manager - Clean Version
Centralized market data manager with NO DUPLICATES and NO FALLBACKS
Uses MarketDataService as single source of truth
"""

import time
import threading
from typing import Dict, Any, Optional, List
from loguru import logger

# Import singleton getters for calculators
from core.analysis.real_time.volume_calculator import get_global_volume_calculator
from core.analysis.real_time.volume_profile_analyzer import get_global_volume_profile_analyzer
from core.analysis.real_time.support_resistance_calculator import get_global_support_resistance_calculator
from core.analysis.real_time.volatility_calculator import get_global_volatility_calculator
from core.analysis.real_time.pressure_calculator import get_global_pressure_calculator
from core.analysis.real_time.orderbook_analyzer import get_global_orderbook_analyzer
from core.analysis.real_time.funding_rate_analyzer import get_global_funding_rate_analyzer
from core.analysis.real_time.cross_asset_correlation_analyzer import get_global_cross_asset_correlation_analyzer
# On-Chain Data analyzer removed - no free APIs available
from core.analysis.real_time.pattern_recognition_engine import get_global_pattern_recognition_engine

class MarketDataManager:
    """Centralized market data manager - NO DUPLICATES, NO FALLBACKS"""
    
    def __init__(self):
        # Cache for market data to avoid redundant API calls
        self._market_data_cache = {}
        self._cache_timestamps = {}
        self._cache_duration = 30  # 30 seconds cache
        
        # S/R level tracking for smart recalculation
        self._last_sr_levels = {
            "strongest_support": 0.0,
            "strongest_resistance": 0.0,
            "last_calculated_price": 0.0,
            "last_calculated_time": 0.0
        }
        
        logger.info("📊 Market Data Manager initialized - Centralized data management with smart S/R caching")
    
    def _should_recalculate_sr_levels(self, current_price: float) -> tuple[bool, str]:
        """
        Check if S/R levels need recalculation based on price movement and level breaks.
        
        Returns:
            tuple: (should_recalculate: bool, reason: str)
        """
        import time
        
        current_time = time.time()
        last_price = self._last_sr_levels["last_calculated_price"]
        last_support = self._last_sr_levels["strongest_support"]
        last_resistance = self._last_sr_levels["strongest_resistance"]
        last_time = self._last_sr_levels["last_calculated_time"]
        
        # Always recalculate if this is the first time
        if last_price == 0.0:
            return True, "first calculation"
        
        # Check if any level was broken
        support_broken = last_support > 0 and current_price < last_support
        resistance_broken = last_resistance > 0 and current_price > last_resistance
        
        # Also recalculate if we had no resistance before but now we need it
        if last_resistance == 0.0 and current_price > 0:
            return True, "no resistance found previously, need recalculation"
        
        if support_broken:
            # Invalidate cache immediately when support is broken
            self._last_sr_levels = {
                "strongest_support": 0.0,
                "strongest_resistance": 0.0,
                "last_calculated_price": 0.0,
                "last_calculated_time": 0
            }
            return True, f"support broken (${last_support:.2f} -> ${current_price:.2f})"
        if resistance_broken:
            # Invalidate cache immediately when resistance is broken
            self._last_sr_levels = {
                "strongest_support": 0.0,
                "strongest_resistance": 0.0,
                "last_calculated_price": 0.0,
                "last_calculated_time": 0
            }
            return True, f"resistance broken (${last_resistance:.2f} -> ${current_price:.2f})"
        
        # Check if price moved significantly (5% change)
        if last_price > 0:
            price_change_pct = abs(current_price - last_price) / last_price
            if price_change_pct > 0.05:  # 5% threshold
                return True, f"significant price movement ({price_change_pct:.1%})"
        
        # Check if it's been too long since last calculation (5 minutes)
        if current_time - last_time > 300:  # 5 minutes
            return True, "time threshold exceeded"
        
        # No need to recalculate
        return False, "levels still valid"
    
    def _update_sr_cache(self, support: float, resistance: float, current_price: float):
        """Update the S/R level cache with new values."""
        import time
        
        self._last_sr_levels = {
            "strongest_support": support,
            "strongest_resistance": resistance,
            "last_calculated_price": current_price,
            "last_calculated_time": time.time()
        }
    
    def invalidate_sr_cache(self):
        """Force S/R recalculation by invalidating the cache."""
        self._last_sr_levels = {
            "strongest_support": 0.0,
            "strongest_resistance": 0.0,
            "last_calculated_price": 0.0,
            "last_calculated_time": 0.0
        }
        logger.info("🔄 S/R cache invalidated - will recalculate on next request")
    
    def get_historical_candles(self, symbol: str = "BTC", interval: str = "5m", limit: int = 20, force_refresh: bool = False, include_ongoing: bool = True) -> List[Dict[str, Any]]:
        """
        Get historical candles with simple 20-candle rolling window
        NO DUPLICATES - delegates to MarketDataService
        """
        try:
            # Get MarketDataService from SystemInitializer
            from core.services.system_initializer import get_system_initializer
            system_initializer = get_system_initializer()
            market_data_service = system_initializer.singleton_systems.get("market_data_service")
            
            if not market_data_service:
                raise ValueError("MarketDataService not available")
            
            # Delegate to MarketDataService (no duplicates)
            return market_data_service.get_historical_candles(symbol, interval, limit)
            
        except Exception as e:
            logger.error(f"❌ Failed to get historical candles: {e}")
            raise ValueError(f"Historical candles failed - NO FALLBACKS: {e}")
    
    def get_ongoing_candle(self) -> Optional[Dict[str, Any]]:
        """Get the current ongoing candle (for layering with 1st prediction)"""
        try:
            # Get MarketDataService from SystemInitializer
            from core.services.system_initializer import get_system_initializer
            system_initializer = get_system_initializer()
            market_data_service = system_initializer.singleton_systems.get("market_data_service")
            
            if not market_data_service:
                raise ValueError("MarketDataService not available")
            
            # Delegate to MarketDataService (no duplicates)
            return market_data_service.get_ongoing_candle("BTC", "5m")
            
        except Exception as e:
            logger.error(f"❌ Failed to get ongoing candle: {e}")
            raise ValueError(f"Ongoing candle failed - NO FALLBACKS: {e}")
    
    def get_hyperliquid_data(self, market_data_service, symbol: str = "BTC") -> Dict[str, Any]:
        """Get all Hyperliquid data through MarketDataService - NO DUPLICATES"""
        try:
            # Get all data from MarketDataService (single source of truth)
            all_data = market_data_service.get_all_market_data(symbol)
            
            if "error" in all_data:
                raise ValueError(all_data["error"])
            
            # Extract data from response
            market_data = all_data.get("market_data", {})
            current_price = all_data.get("current_price")
            recent_trades = all_data.get("recent_trades", [])
            funding_rate = all_data.get("funding_rate", {})
            candles_5m = all_data.get("candles", {}).get("5m", [])
            
            # Fetch additional candle timeframes for S/R calculation
            candles_1h = market_data_service.get_historical_candles("BTC", "1h", 48)
            candles_1d = market_data_service.get_historical_candles("BTC", "1d", 7)
            
            # Use calculators for analysis (clean architecture)
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
                        
                        # Initialize volume data
                        volume_data = {"data_source": "hyperliquid"}
                        
                        # Use PressureCalculator for pressure analysis
                        pressure_data = get_global_pressure_calculator().calculate_orderbook_pressure(bids, asks)
                        pressure_data["data_source"] = "hyperliquid_orderbook"
                        
                        # Calculate current price from orderbook data
                        if current_price <= 0 and bids and asks and 'px' in bids[0] and 'px' in asks[0]:
                            best_bid = float(bids[0]['px'])
                            best_ask = float(asks[0]['px'])
                            current_price = (best_bid + best_ask) / 2
                        
                        # Use OrderBookAnalyzer for comprehensive order book analysis
                        orderbook_analysis = get_global_orderbook_analyzer().analyze_orderbook(market_data, current_price)
                        
                        # Analyze funding rate data (from MarketDataService) - OPTIONAL
                        try:
                            funding_analysis = get_global_funding_rate_analyzer().analyze_funding_rate(funding_rate)
                        except Exception as e:
                            logger.warning(f"⚠️ Funding rate analysis skipped - real data not available: {e}")
                            funding_analysis = {"error": "Real funding rate data not available", "data_source": "skipped"}
                        
                        # Analyze volume profile from recent trades (from MarketDataService)
                        if recent_trades and isinstance(recent_trades, list):
                            volume_profile_analysis = get_global_volume_profile_analyzer().analyze_volume_profile(recent_trades, current_price)
                        else:
                            raise ValueError("Insufficient recent trades for volume profile analysis")
                        
                        # Analyze cross-asset correlations for broader market context (OPTIONAL)
                        try:
                            cross_asset_analysis = get_global_cross_asset_correlation_analyzer().analyze_cross_asset_correlations(current_price)
                        except Exception as e:
                            logger.warning(f"⚠️ Cross-asset analysis skipped - real data not available: {e}")
                            cross_asset_analysis = {"error": "Real cross-asset data not available", "data_source": "skipped"}
                        
                        # On-Chain Data feature removed - no free APIs provide required metrics
                        onchain_analysis = {"error": "On-Chain data feature removed - no free APIs available", "data_source": "removed"}
                        
                        # Analyze trading patterns for market setups (from MarketDataService)
                        if candles_5m and len(candles_5m) >= 10:
                            pattern_analysis = get_global_pattern_recognition_engine().analyze_patterns(candles_5m)
                        else:
                            raise ValueError("Insufficient candle data for pattern analysis")
                        
                        # SMART S/R CALCULATION - Only recalculate when needed
                        current_price = candles_5m[-1].get("close", 0) if candles_5m else 0
                        
                        # Check if S/R levels need recalculation
                        should_recalc, recalc_reason = self._should_recalculate_sr_levels(current_price)
                        
                        if should_recalc:
                            logger.info(f"🔄 S/R recalculation triggered: {recalc_reason}")
                            
                            # Calculate support/resistance levels using SupportResistanceCalculator
                            from core.analysis.real_time.support_resistance_calculator import get_global_support_resistance_calculator
                            sr_calculator = get_global_support_resistance_calculator()
                            
                            # First try with 5m candles
                            support_resistance_data = sr_calculator.calculate_multi_timeframe_levels(
                                current_price, market_data_service, candles_5m, candles_1h, candles_1d
                            )
                            strongest_support = support_resistance_data.get("strongest_support", 0)
                            strongest_resistance = support_resistance_data.get("strongest_resistance", 0)
                            
                            needs_deeper_data = False
                            reason = []
                            
                            # Check if support is broken (price below support or no support found)
                            if current_price > 0 and (strongest_support == 0 or strongest_support >= current_price):
                                needs_deeper_data = True
                                reason.append("support broken/missing")
                                logger.warning(f"🔍 SUPPORT BROKEN: Current=${current_price:.2f}, Support=${strongest_support:.2f} (Support >= Price: {strongest_support >= current_price})")
                            
                            # Check if resistance is broken (price above resistance or no resistance found)
                            if current_price > 0 and (strongest_resistance == 0 or strongest_resistance <= current_price):
                                needs_deeper_data = True
                                reason.append("resistance broken/missing")
                                logger.warning(f"🔍 RESISTANCE BROKEN: Current=${current_price:.2f}, Resistance=${strongest_resistance:.2f} (Resistance <= Price: {strongest_resistance <= current_price})")
                            
                            # Fetch deeper historical data if needed
                            if needs_deeper_data:
                                logger.warning(f"⚠️ S/R recalculation needed ({', '.join(reason)}) - fetching 1h historical candles")
                                # Fetch more historical data (1h candles for deeper history)
                                candles_1h = market_data_service.get_historical_candles("BTC", "1h", 48)  # 48 hours
                                if candles_1h and len(candles_1h) >= 10:
                                    support_resistance_data = sr_calculator.identify_key_levels(candles_1h)
                                    new_support = support_resistance_data.get('strongest_support', 0)
                                    new_resistance = support_resistance_data.get('strongest_resistance', 0)
                                    logger.success(f"✅ S/R RECALCULATED from 1h data: Support=${new_support:,.2f}, Resistance=${new_resistance:,.2f}")
                                    logger.info(f"   📊 New support below current price: {new_support < current_price}")
                                    logger.info(f"   📊 New resistance above current price: {new_resistance > current_price}")
                                else:
                                    logger.error(f"❌ Failed to get sufficient 1h candles for S/R recalculation: {len(candles_1h) if candles_1h else 0} candles")
                            
                            # Update S/R cache with new values
                            self._update_sr_cache(strongest_support, strongest_resistance, current_price)
                            logger.info(f"💾 S/R levels cached: Support=${strongest_support:.2f}, Resistance=${strongest_resistance:.2f}")
                        
                        else:
                            # Use cached S/R levels
                            strongest_support = self._last_sr_levels["strongest_support"]
                            strongest_resistance = self._last_sr_levels["strongest_resistance"]
                            support_resistance_data = {
                                "strongest_support": strongest_support,
                                "strongest_resistance": strongest_resistance,
                                "key_levels": []  # Could cache this too if needed
                            }
                            logger.debug(f"📋 Using cached S/R levels: Support=${strongest_support:.2f}, Resistance=${strongest_resistance:.2f}")
                    else:
                        raise ValueError("Insufficient orderbook data")
                else:
                    raise ValueError("Insufficient market data levels")
            else:
                raise ValueError("No market data available")
            
            # Get volume data from MarketDataService (no duplicates)
            if candles_5m and len(candles_5m) >= 3:
                # Calculate average volume per minute from recent 5m candles
                recent_volumes = [candle.get('volume', 0) for candle in candles_5m[-3:]]
                avg_5m_volume = sum(recent_volumes) / len(recent_volumes)
                volume_per_minute = avg_5m_volume / 5  # Convert 5m volume to per minute
                volume_per_second = volume_per_minute / 60
                
                # Calculate volume category using VolumeCalculator
                volume_spike_result = get_global_volume_calculator().detect_volume_spike_from_binance(volume_per_minute, [])
                
                # Update volume data with Hyperliquid candle data
                volume_data.update({
                    "current_volume_btc": volume_per_minute,
                    "current_volume_usd": volume_per_minute * current_price,
                    "real_time_volume_btc": volume_per_minute,
                    "real_time_volume_usd": volume_per_minute * current_price,
                    "volume_per_minute": volume_per_minute,
                    "volume_per_second": volume_per_second,
                    "trade_count_per_minute": 0,  # Not available from candles
                    "volume_spike_detected": volume_spike_result.get('volume_spike_detected', False),
                    "volume_ratio": volume_spike_result.get('volume_ratio', 1.0),
                    "volume_category": volume_spike_result.get('volume_category'),
                    "data_source": "hyperliquid_candles",
                    "timestamp": time.time()
                })
            else:
                raise ValueError("Insufficient candle data for volume calculation")
            
            # Calculate volatility analysis
            volatility_analysis = self.get_hyperliquid_volatility_analysis(candles_5m, symbol, "standard")
            
            # Return comprehensive data (no fallbacks)
            return {
                "volume_data": volume_data,
                "pressure_data": pressure_data,
                "orderbook_analysis": orderbook_analysis,
                "funding_analysis": funding_analysis,
                "volume_profile_analysis": volume_profile_analysis,
                "cross_asset_analysis": cross_asset_analysis,
                "onchain_analysis": onchain_analysis,
                "pattern_analysis": pattern_analysis,
                "support_resistance": support_resistance_data,
                "volatility_analysis": volatility_analysis,
                "current_price": current_price,
                "timestamp": time.time()
            }
            
            # Add external API data using Yahoo Finance
            try:
                # Get Fear & Greed data
                from core.external.fear_greed_api import get_global_fear_greed_api
                fear_greed_api = get_global_fear_greed_api()
                sentiment_data = fear_greed_api.get_fear_greed_index()
                result["sentiment_data"] = sentiment_data
            except Exception as e:
                logger.warning(f"⚠️ Fear & Greed data skipped: {e}")
                result["sentiment_data"] = {"error": "Fear & Greed data not available", "data_source": "failed"}
            
            try:
                # Get News Sentiment data
                from core.external.rss_news_api import get_global_rss_news_api
                rss_news_api = get_global_rss_news_api()
                news_sentiment = rss_news_api.get_news_sentiment()
                result["news_sentiment"] = news_sentiment
            except Exception as e:
                logger.warning(f"⚠️ News Sentiment data skipped: {e}")
                result["news_sentiment"] = {"error": "News Sentiment data not available", "data_source": "failed"}
            
            try:
                # Get Whale Analytics data (COMPLETELY FREE)
                from core.external.whale_analytics_api import get_global_whale_analytics_api
                whale_analytics_api = get_global_whale_analytics_api()
                whale_analytics = whale_analytics_api.get_whale_analytics()
                result["whale_analytics"] = whale_analytics
            except Exception as e:
                logger.warning(f"⚠️ Whale Analytics data skipped: {e}")
                result["whale_analytics"] = {"error": "Whale Analytics data not available", "data_source": "failed"}
            
            return result
            
        except Exception as e:
            logger.error(f"❌ MarketDataManager failed: {e}")
            raise ValueError(f"MarketDataManager failed - NO FALLBACKS: {e}")
    
    def get_hyperliquid_volatility_analysis(self, hyperliquid_candles: List[Dict], symbol: str = "BTC", strategy_name: str = "standard") -> Dict[str, Any]:
        """
        Get multi-timeframe volatility analysis from Hyperliquid candle data (REAL-TIME DATA)
        This method uses actual market data instead of stale data
        """
        try:
            if not hyperliquid_candles or len(hyperliquid_candles) < 3:
                raise ValueError("Insufficient candle data for volatility analysis")
            
            # Calculate volatility using centralized volatility calculator (SINGLE SOURCE OF TRUTH)
            volatility_calculator = get_global_volatility_calculator()
            
            # Get current strategy for strategy-dependent volatility calculation
            from core.services.strategy_manager import get_global_strategy_manager
            strategy_manager = get_global_strategy_manager()
            current_strategy = strategy_manager.get_current_strategy() if strategy_manager else "standard"
            
            volatility_result = volatility_calculator.calculate_candle_volatility(hyperliquid_candles, "5m", current_strategy)
            volatility_5m = volatility_result.get("volatility", 0.0)
            volatility_5m_category, volatility_5m_trend = volatility_calculator.categorize_volatility_for_trading(volatility_5m, "5m")
            
            return {
                "volatility_5m": volatility_5m,
                "volatility_5m_category": volatility_5m_category,
                "volatility_5m_trend": volatility_5m_trend,
                "volatility_5m_period_minutes": volatility_result.get("period_minutes", 30),
                "volatility_5m_period_candles": volatility_result.get("period_candles", 6),
                "volatility_5m_strategy": volatility_result.get("strategy", current_strategy),
                "data_source": "hyperliquid_candles",
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Volatility analysis failed: {e}")
            raise ValueError(f"Volatility analysis failed - NO FALLBACKS: {e}")
    
    
    def clear_cache(self):
        """Clear all cached data"""
        self._market_data_cache.clear()
        self._cache_timestamps.clear()
        logger.info("🧹 MarketDataManager cache cleared - will get fresh data")
        logger.info("🧹 MarketDataManager indicator cache cleared")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get simplified cache status for monitoring"""
        return {
            "cached_items": len(self._market_data_cache),
            "cache_duration": self._cache_duration,
            "last_clear": max(self._cache_timestamps.values()) if self._cache_timestamps else 0
        }

# Singleton pattern for MarketDataManager
_global_market_data_manager: Optional[MarketDataManager] = None
_market_data_manager_lock = threading.Lock()

def get_global_market_data_manager() -> MarketDataManager:
    """Get the global MarketDataManager singleton instance"""
    global _global_market_data_manager
    with _market_data_manager_lock:
        if _global_market_data_manager is None:
            _global_market_data_manager = MarketDataManager()
        return _global_market_data_manager

# Backward compatibility
def market_data_manager():
    return get_global_market_data_manager()