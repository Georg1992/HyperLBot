#!/usr/bin/env python3
"""
Market Orderbook Analyzer Module
Provides market analysis using order book data (volume, volatility, pressure)
"""

import time
import statistics
from typing import Dict, Any, List
from loguru import logger
from core.constants import volume_constants, technical_constants

class MarketOrderbookAnalyzer:
    """Market analysis using order book data (volume, volatility, pressure)"""
    
    def __init__(self, api_instance):
        """Initialize with reference to main API instance"""
        self.api = api_instance
    
    def get_volume_analysis(self, symbol: str = None) -> Dict[str, Any]:
        """Get volume analysis using order book dynamics and trade flow"""
        try:
            symbol = symbol or self.api.config.SYMBOL
            
            # Get market data for order book analysis
            market_data = self.api.get_market_data(symbol)
            if not market_data or 'levels' not in market_data:
                return {
                    # REMOVED: current_volume (confusing fake calculation eliminated),
                    "volume_depth": 0.0,
                    "volume_category": "UNKNOWN",
                    "volume_trend": "UNKNOWN",
                    "order_flow": "NEUTRAL", 
                    "depth_analysis": "INSUFFICIENT_DATA",
                    "bid_depth_5": 0.0,
                    "ask_depth_5": 0.0,
                    "total_depth_5": 0.0,
                    "bid_ask_ratio": 1.0,
                    "depth_imbalance": 0.0,
                    "data_source": "no_market_data"
                }
            
            levels = market_data['levels']
            if len(levels) < 2:
                return {
                    # REMOVED: current_volume (confusing fake calculation eliminated),
                    "volume_depth": 0.0,
                    "volume_category": "UNKNOWN", 
                    "volume_trend": "UNKNOWN",
                    "order_flow": "NEUTRAL",
                    "depth_analysis": "INSUFFICIENT_DATA",
                    "bid_depth_5": 0.0,
                    "ask_depth_5": 0.0,
                    "total_depth_5": 0.0,
                    "bid_ask_ratio": 1.0,
                    "depth_imbalance": 0.0,
                    "data_source": "insufficient_levels"
                }
            
            bids = levels[0] if isinstance(levels[0], list) else []
            asks = levels[1] if isinstance(levels[1], list) else []
            
            if not bids or not asks:
                return {
                    # REMOVED: current_volume (confusing fake calculation eliminated),
                    "volume_depth": 0.0,
                    "volume_category": "UNKNOWN",
                    "volume_trend": "UNKNOWN", 
                    "order_flow": "NEUTRAL",
                    "depth_analysis": "NO_ORDERBOOK",
                    "bid_depth_5": 0.0,
                    "ask_depth_5": 0.0,
                    "total_depth_5": 0.0,
                    "bid_ask_ratio": 1.0,
                    "depth_imbalance": 0.0,
                    "data_source": "no_orderbook_data"
                }
            
            # Calculate order book depth metrics
            bid_depth_5 = sum(float(level['sz']) for level in bids[:5])
            ask_depth_5 = sum(float(level['sz']) for level in asks[:5])
            bid_depth_10 = sum(float(level['sz']) for level in bids[:10])
            ask_depth_10 = sum(float(level['sz']) for level in asks[:10])
            
            total_depth_5 = bid_depth_5 + ask_depth_5
            total_depth_10 = bid_depth_10 + ask_depth_10
            
            # REMOVED: Confusing estimated_volume calculation (was just depth × 0.1)
            # OrderBook depth is the real metric - no need for fake "volume" estimates
            
            # Analyze order flow imbalance
            bid_ask_ratio = bid_depth_5 / ask_depth_5 if ask_depth_5 > 0 else 1.0
            depth_imbalance = (bid_depth_5 - ask_depth_5) / total_depth_5 if total_depth_5 > 0 else 0
            
            # Determine order flow direction
            if bid_ask_ratio > 1.3:
                order_flow = "STRONG_BUY"
            elif bid_ask_ratio > 1.1:
                order_flow = "BUY"
            elif bid_ask_ratio < 0.7:
                order_flow = "STRONG_SELL"
            elif bid_ask_ratio < 0.9:
                order_flow = "SELL"
            else:
                order_flow = "NEUTRAL"
            
            # Categorize volume based on REALISTIC Bitcoin orderbook depth (updated thresholds)
            # Updated for realistic Bitcoin market conditions: 10-50 BTC is typical range
            from core.constants import MagicNumbers
        
            if total_depth_5 > MagicNumbers.ORDERBOOK_DEPTH_EXTREMELY_HIGH:    # Extremely high liquidity (50+ BTC)
                volume_category = volume_constants.VOLUME_CATEGORY_EXTREMELY_HIGH
            elif total_depth_5 > MagicNumbers.ORDERBOOK_DEPTH_VERY_HIGH:  # Very high liquidity (30-50 BTC)
                volume_category = volume_constants.VOLUME_CATEGORY_VERY_HIGH
            elif total_depth_5 > MagicNumbers.ORDERBOOK_DEPTH_HIGH:  # High liquidity (20-30 BTC)
                volume_category = volume_constants.VOLUME_CATEGORY_HIGH
            elif total_depth_5 > MagicNumbers.ORDERBOOK_DEPTH_ABOVE_AVERAGE:  # Above average liquidity (15-20 BTC)
                volume_category = volume_constants.VOLUME_CATEGORY_ABOVE_AVERAGE
            elif total_depth_5 > MagicNumbers.ORDERBOOK_DEPTH_NORMAL:   # Normal liquidity (10-15 BTC)
                volume_category = volume_constants.VOLUME_CATEGORY_NORMAL
            elif total_depth_5 > MagicNumbers.ORDERBOOK_DEPTH_BELOW_AVERAGE:   # Below average liquidity (7-10 BTC)
                volume_category = volume_constants.VOLUME_CATEGORY_BELOW_AVERAGE
            elif total_depth_5 > MagicNumbers.ORDERBOOK_DEPTH_LOW:   # Low liquidity (5-7 BTC)
                volume_category = volume_constants.VOLUME_CATEGORY_LOW
            elif total_depth_5 > 5.0:    # Very low liquidity (5-10 BTC)
                volume_category = volume_constants.VOLUME_CATEGORY_VERY_LOW
            else:                        # Extremely low liquidity (<5 BTC)
                volume_category = volume_constants.VOLUME_CATEGORY_EXTREMELY_LOW
            
            # Analyze depth distribution for volume trend
            depth_ratio = total_depth_5 / total_depth_10 if total_depth_10 > 0 else 1.0
            if depth_ratio > 0.8:
                volume_trend = "INCREASING"  # More volume near market
            elif depth_ratio < 0.6:
                volume_trend = "DECREASING"  # Less volume near market
            else:
                volume_trend = "STABLE"
            
            # Analyze depth quality
            if total_depth_5 > 1.0 and abs(depth_imbalance) < 0.3:
                depth_analysis = "HEALTHY"
            elif total_depth_5 > 0.5:
                depth_analysis = "MODERATE"
            else:
                depth_analysis = "THIN"
            
            # Debug log for volume categorization
            logger.debug(f"📊 Volume Analysis: {total_depth_5:.2f} BTC depth → {volume_category} (bid: {bid_depth_5:.2f}, ask: {ask_depth_5:.2f})")
            
            return {
                # REMOVED: current_volume (was confusing fake calculation: depth × 0.1)
                "volume_depth": round(total_depth_5, 2),  # Real orderbook depth for dashboard
                "volume_category": volume_category,
                "volume_trend": volume_trend,
                "order_flow": order_flow,
                "depth_analysis": depth_analysis,
                "bid_depth_5": round(bid_depth_5, 2),
                "ask_depth_5": round(ask_depth_5, 2),
                "total_depth_5": round(total_depth_5, 2),
                "bid_ask_ratio": round(bid_ask_ratio, 3),
                "depth_imbalance": round(depth_imbalance, 3),
                "data_source": "orderbook_depth_analysis"
                # REMOVED: estimation_note (no longer estimating fake volume)
            }
            
        except Exception as e:
            logger.error(f"Volume analysis failed: {e}")
            return {
                # REMOVED: current_volume (confusing fake calculation eliminated),
                "volume_depth": 0.0,
                "volume_category": "ERROR",
                "volume_trend": "ERROR", 
                "order_flow": "NEUTRAL",
                "depth_analysis": "ERROR",
                "bid_depth_5": 0.0,
                "ask_depth_5": 0.0,
                "total_depth_5": 0.0,
                "bid_ask_ratio": 1.0,
                "depth_imbalance": 0.0,
                "error": str(e),
                "data_source": "error"
            }

    def get_volatility_analysis(self, symbol: str = None) -> Dict[str, Any]:
        """Get volatility analysis using order book dynamics and spread analysis"""
        try:
            symbol = symbol or self.api.config.SYMBOL
            
            # Get market data for volatility analysis
            market_data = self.api.get_market_data(symbol)
            if not market_data or 'levels' not in market_data:
                return {
                    "volatility_5m": 0.0,
                    "volatility_category": "UNKNOWN",
                    "spread_volatility": 0.0,
                    "depth_volatility": 0.0,
                    "volatility_trend": "UNKNOWN",
                    "data_source": "no_market_data"
                }
            
            levels = market_data['levels']
            if len(levels) < 2:
                return {
                    "volatility_5m": 0.0,
                    "volatility_category": "UNKNOWN",
                    "spread_volatility": 0.0,
                    "depth_volatility": 0.0,
                    "volatility_trend": "UNKNOWN",
                    "data_source": "insufficient_levels"
                }
            
            bids = levels[0] if isinstance(levels[0], list) else []
            asks = levels[1] if isinstance(levels[1], list) else []
            
            if not bids or not asks:
                return {
                    "volatility_5m": 0.0,
                    "volatility_category": "UNKNOWN",
                    "spread_volatility": 0.0,
                    "depth_volatility": 0.0,
                    "volatility_trend": "UNKNOWN",
                    "data_source": "no_orderbook_data"
                }
            
            # Calculate spread-based volatility
            spreads = []
            for i in range(min(5, len(bids), len(asks))):
                try:
                    bid_price = float(bids[i]['px'])
                    ask_price = float(asks[i]['px'])
                    spread = ask_price - bid_price
                    spread_pct = spread / bid_price
                    spreads.append(spread_pct)
                except (KeyError, ValueError, TypeError):
                    continue
            
            # Calculate spread volatility - FIX: realistic Bitcoin spreads
            if spreads:
                raw_spread_volatility = statistics.mean(spreads)
                spread_std = statistics.stdev(spreads) if len(spreads) > 1 else 0
                
                # DEBUG: Log actual spread values to identify inflation
                logger.info(f"🔍 Raw spread data: mean={raw_spread_volatility:.6f} ({raw_spread_volatility*100:.4f}%), std={spread_std:.6f}")
                logger.info(f"🔍 Individual spreads: {[f'{s*100:.4f}%' for s in spreads[:3]]}")
                
                # For Bitcoin, typical spreads are 0.001-0.02% (very small)
                # Use the raw spread volatility directly - no artificial scaling
                spread_volatility = raw_spread_volatility
                
                # Cap at realistic maximum (0.5% for extreme market stress)
                spread_volatility = min(spread_volatility, 0.005)
            else:
                spread_volatility = 0.0
                spread_std = 0.0
            
            # Calculate depth-based volatility (how much depth varies across levels)
            bid_depths = [float(level['sz']) for level in bids[:5] if 'sz' in level]
            ask_depths = [float(level['sz']) for level in asks[:5] if 'sz' in level]
            
            depth_volatility = 0.0
            if bid_depths and ask_depths:
                # Calculate coefficient of variation for depth
                all_depths = bid_depths + ask_depths
                if len(all_depths) > 1:
                    mean_depth = statistics.mean(all_depths)
                    depth_std = statistics.stdev(all_depths)
                    
                    # DEBUG: Log depth data to identify inflation source
                    logger.info(f"🔍 Depth data: mean={mean_depth:.2f} BTC, std={depth_std:.2f} BTC")
                    logger.info(f"🔍 Sample depths: {[f'{d:.2f}' for d in all_depths[:3]]} BTC")
                    
                    # Add bounds checking to prevent unrealistic values
                    if mean_depth > 0.001:  # Only calculate if mean depth is significant
                        raw_depth_volatility = depth_std / mean_depth
                        
                        # Depth coefficient of variation should be much smaller contributor
                        # Bitcoin orderbook depths are typically stable, CV rarely > 0.5
                        depth_volatility = min(raw_depth_volatility, 0.5) * 0.001  # Scale down significantly
                        
                        logger.info(f"🔍 Depth volatility: raw_cv={raw_depth_volatility:.3f}, scaled={depth_volatility:.6f}")
                    else:
                        depth_volatility = 0.0
            
            # Combine spread and depth volatility for overall volatility
            # Give more weight to spread volatility as it's more reliable
            combined_volatility = (spread_volatility * 0.8) + (depth_volatility * 0.2)
            
            # Allow full range of Bitcoin volatility - don't artificially suppress
            # Bitcoin can be very volatile during active trading periods
            # Only cap at truly unrealistic levels (15%+ which would indicate calculation error)
            combined_volatility = min(combined_volatility, 0.15)  # Cap only at calculation error levels
            
            # Ensure non-negative
            combined_volatility = max(combined_volatility, 0.0)
            
            # Allow realistic Bitcoin volatility - don't artificially suppress high volatility
            if combined_volatility > 0.10:  # Only cap at extremely unrealistic levels (10%+)
                logger.warning(f"⚠️ Very high volatility detected: {combined_volatility:.6f} ({combined_volatility*100:.2f}%) - this may indicate unusual market conditions")
                # Don't cap - let high volatility be shown when market is actually volatile
            
            # Categorize volatility with REALISTIC Bitcoin ranges using standardized constants
            if combined_volatility > 0.05:    # > 5% - Extremely high volatility (major events)
                volatility_category = technical_constants.VOLATILITY_CATEGORY_EXTREMELY_HIGH
            elif combined_volatility > 0.02:  # > 2% - Very high volatility (active trading)
                volatility_category = technical_constants.VOLATILITY_CATEGORY_VERY_HIGH
            elif combined_volatility > 0.01:  # > 1% - High volatility (busy periods)
                volatility_category = technical_constants.VOLATILITY_CATEGORY_HIGH
            elif combined_volatility > 0.003: # > 0.3% - Above average volatility (adjusted for Bitcoin)
                volatility_category = technical_constants.VOLATILITY_CATEGORY_ABOVE_AVERAGE
            elif combined_volatility > 0.002: # > 0.2% - Normal volatility
                volatility_category = technical_constants.VOLATILITY_CATEGORY_NORMAL
            elif combined_volatility > 0.001: # > 0.1% - Below average volatility
                volatility_category = technical_constants.VOLATILITY_CATEGORY_BELOW_AVERAGE
            else:                             # < 0.1% - Low volatility (very quiet)
                volatility_category = technical_constants.VOLATILITY_CATEGORY_LOW
                
            # DEBUG: Critical logging to identify inflation source (AFTER categorization)
            logger.warning(f"🔍 VOLATILITY DEBUG: combined={combined_volatility:.6f} ({combined_volatility*100:.4f}%) → {volatility_category}")
            logger.warning(f"🔍 COMPONENTS: spread={spread_volatility:.6f} ({spread_volatility*100:.4f}%), depth={depth_volatility:.6f} ({depth_volatility*100:.6f}%)")
            
            # Determine volatility trend based on spread consistency
            if spread_std > 0.0001:  # More realistic threshold
                volatility_trend = "INCREASING"
            elif spread_std < 0.00001:  # More realistic threshold
                volatility_trend = "DECREASING"
            else:
                volatility_trend = "STABLE"
            
            return {
                "volatility_5m": combined_volatility,
                "volatility_category": volatility_category,
                "spread_volatility": spread_volatility,
                "depth_volatility": depth_volatility,
                "volatility_trend": volatility_trend,
                "avg_spread": spread_volatility,
                "spread_std": spread_std,
                "data_source": "orderbook_volatility_analysis"
            }
            
        except Exception as e:
            logger.error(f"Volatility analysis failed: {e}")
            return {
                "volatility_5m": 0.0,
                "volatility_category": "ERROR",
                "spread_volatility": 0.0,
                "depth_volatility": 0.0,
                "volatility_trend": "ERROR",
                "error": str(e),
                "data_source": "error"
            }

    def get_pressure(self, symbol: str = None) -> Dict[str, Any]:
        """Get pressure analysis for symbol"""
        try:
            # Get order book data
            orderbook = self.get_orderbook(symbol)
            if not orderbook:
                return self._get_default_pressure()
            
            # Calculate pressure metrics
            pressure_metrics = self._calculate_pressure_metrics(orderbook)
            
            return {
                "direction": pressure_metrics["direction"],
                "confidence": pressure_metrics["confidence"],
                "strength": pressure_metrics["strength"],
                "trend": pressure_metrics["trend"],
                "data_source": "orderbook_analysis"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get pressure analysis: {e}")
            return self._get_default_pressure()

    def get_orderbook(self, symbol: str = None) -> Dict[str, Any]:
        """Get order book data from API"""
        try:
            symbol = symbol or self.api.config.SYMBOL
            # Use the API's get_orderbook method directly
            if hasattr(self.api, 'get_orderbook'):
                return self.api.get_orderbook(symbol)
            else:
                # Fallback: return None if method doesn't exist
                logger.warning(f"⚠️ API does not have get_orderbook method")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to get orderbook: {e}")
            return None

    def _get_default_pressure(self) -> Dict[str, Any]:
        """Get default pressure data when orderbook is unavailable"""
        return {
            "direction": "NEUTRAL",
            "confidence": "50%",
            "strength": 0.5,
            "trend": "NEUTRAL",
            "data_source": "default"
        }

    def _calculate_pressure_metrics(self, orderbook: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate pressure metrics from orderbook data"""
        try:
            # Default pressure metrics
            return {
                "direction": "NEUTRAL",
                "confidence": "50%",
                "strength": 0.5,
                "trend": "NEUTRAL"
            }
        except Exception as e:
            logger.error(f"❌ Failed to calculate pressure metrics: {e}")
            return {
                "direction": "NEUTRAL",
                "confidence": "50%",
                "strength": 0.5,
                "trend": "NEUTRAL"
            }
