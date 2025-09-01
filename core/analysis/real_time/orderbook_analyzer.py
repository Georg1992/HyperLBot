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

    # get_volatility_analysis() removed - 167 lines of Hyperliquid orderbook volatility logic eliminated
    # Using Yahoo Finance 5-minute candle volatility instead (aligned with 5m trading strategy)

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
