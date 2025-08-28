#!/usr/bin/env python3
"""
Market Orderbook Analyzer Module
Provides market analysis using order book data (volume, volatility, pressure)
"""

import time
import statistics
from typing import Dict, Any, List
from loguru import logger

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
                    "current_volume": 0.0,
                    "volume_category": "UNKNOWN",
                    "volume_trend": "UNKNOWN",
                    "order_flow": "NEUTRAL",
                    "depth_analysis": "INSUFFICIENT_DATA",
                    "data_source": "no_market_data"
                }
            
            levels = market_data['levels']
            if len(levels) < 2:
                return {
                    "current_volume": 0.0,
                    "volume_category": "UNKNOWN", 
                    "volume_trend": "UNKNOWN",
                    "order_flow": "NEUTRAL",
                    "depth_analysis": "INSUFFICIENT_DATA",
                    "data_source": "insufficient_levels"
                }
            
            bids = levels[0] if isinstance(levels[0], list) else []
            asks = levels[1] if isinstance(levels[1], list) else []
            
            if not bids or not asks:
                return {
                    "current_volume": 0.0,
                    "volume_category": "UNKNOWN",
                    "volume_trend": "UNKNOWN", 
                    "order_flow": "NEUTRAL",
                    "depth_analysis": "NO_ORDERBOOK",
                    "data_source": "no_orderbook_data"
                }
            
            # Calculate order book depth metrics
            bid_depth_5 = sum(float(level['sz']) for level in bids[:5])
            ask_depth_5 = sum(float(level['sz']) for level in asks[:5])
            bid_depth_10 = sum(float(level['sz']) for level in bids[:10])
            ask_depth_10 = sum(float(level['sz']) for level in asks[:10])
            
            total_depth_5 = bid_depth_5 + ask_depth_5
            total_depth_10 = bid_depth_10 + ask_depth_10
            
            # Calculate volume from order book depth (more accurate than trade history)
            # Use depth as a proxy for recent trading activity
            estimated_volume = total_depth_5 * 0.15  # 15% of depth as recent volume
            
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
            
            # Categorize volume based on depth
            if total_depth_5 > 2.0:
                volume_category = "HIGH"
            elif total_depth_5 > 0.5:
                volume_category = "MEDIUM"
            else:
                volume_category = "LOW"
            
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
            
            return {
                "current_volume": estimated_volume,
                "volume_category": volume_category,
                "volume_trend": volume_trend,
                "order_flow": order_flow,
                "depth_analysis": depth_analysis,
                "bid_depth_5": bid_depth_5,
                "ask_depth_5": ask_depth_5,
                "total_depth_5": total_depth_5,
                "bid_ask_ratio": bid_ask_ratio,
                "depth_imbalance": depth_imbalance,
                "data_source": "orderbook_depth_analysis"
            }
            
        except Exception as e:
            logger.error(f"Volume analysis failed: {e}")
            return {
                "current_volume": 0.0,
                "volume_category": "ERROR",
                "volume_trend": "ERROR",
                "order_flow": "NEUTRAL",
                "depth_analysis": "ERROR",
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
            
            # Calculate spread volatility - normalize to realistic ranges
            if spreads:
                spread_volatility = statistics.mean(spreads)
                spread_std = statistics.stdev(spreads) if len(spreads) > 1 else 0
                # Normalize spread volatility to realistic ranges (typical spreads are 0.0001-0.001)
                # Scale down by 100 to get more reasonable volatility values
                spread_volatility = min(spread_volatility * 100, 0.01)  # Cap at 1%
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
                    # Add bounds checking to prevent unrealistic values
                    if mean_depth > 0.001:  # Only calculate if mean depth is significant
                        depth_volatility = depth_std / mean_depth
                        # Cap depth volatility at much more reasonable levels (max 0.1 = 10%)
                        depth_volatility = min(depth_volatility, 0.1)
                        # Scale down depth volatility as it's typically much smaller than spread volatility
                        depth_volatility = depth_volatility * 0.1  # Scale down by 10x
                    else:
                        depth_volatility = 0.0
            
            # Combine spread and depth volatility for overall volatility
            # Give more weight to spread volatility as it's more reliable
            combined_volatility = (spread_volatility * 0.8) + (depth_volatility * 0.2)
            
            # Add bounds checking to ensure realistic volatility values
            # Cap at 0.01 (1%) which is high for crypto markets
            combined_volatility = min(combined_volatility, 0.01)
            
            # Ensure non-negative
            combined_volatility = max(combined_volatility, 0.0)
            
            # Debug logging for volatility components
            if combined_volatility > 0.005:  # Log if volatility is unusually high (0.5%)
                logger.debug(f"⚠️ High volatility detected: {combined_volatility:.4f} (spread: {spread_volatility:.4f}, depth: {depth_volatility:.4f})")
            
            # Categorize volatility
            if combined_volatility > 0.003:  # 0.3%
                volatility_category = "HIGH"
            elif combined_volatility > 0.001:  # 0.1%
                volatility_category = "MEDIUM"
            else:
                volatility_category = "LOW"
            
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

    def get_ultimate_pressure(self, symbol: str = None) -> Dict[str, Any]:
        """Get ultimate pressure analysis using advanced order book metrics"""
        try:
            symbol = symbol or self.api.config.SYMBOL
            
            # Get market data for pressure analysis
            market_data = self.api.get_market_data(symbol)
            if not market_data or 'levels' not in market_data:
                return {
                    "direction": "NEUTRAL",
                    "pressure_score": 0.5,
                    "confidence": "0%",
                    "strength": 0.5,
                    "trend": "UNKNOWN",
                    "status": "no_market_data"
                }
            
            levels = market_data['levels']
            if len(levels) < 2:
                return {
                    "direction": "NEUTRAL", 
                    "pressure_score": 0.5,
                    "confidence": "0%",
                    "strength": 0.5,
                    "trend": "UNKNOWN",
                    "status": "insufficient_data"
                }
            
            bids = levels[0] if isinstance(levels[0], list) else []
            asks = levels[1] if isinstance(levels[1], list) else []
            
            if not bids or not asks:
                return {
                    "direction": "NEUTRAL",
                    "pressure_score": 0.5, 
                    "confidence": "0%",
                    "strength": 0.5,
                    "trend": "UNKNOWN",
                    "status": "no_orderbook_data"
                }
            
            # Calculate weighted pressure metrics
            bid_pressure = 0.0
            ask_pressure = 0.0
            
            # Weight closer levels more heavily (inverse distance weighting)
            for i, level in enumerate(bids[:10]):
                try:
                    size = float(level['sz'])
                    weight = 1.0 / (i + 1)  # Level 0 gets weight 1, level 1 gets weight 0.5, etc.
                    bid_pressure += size * weight
                except (KeyError, ValueError, TypeError):
                    continue
            
            for i, level in enumerate(asks[:10]):
                try:
                    size = float(level['sz'])
                    weight = 1.0 / (i + 1)
                    ask_pressure += size * weight
                except (KeyError, ValueError, TypeError):
                    continue
            
            total_pressure = bid_pressure + ask_pressure
            if total_pressure == 0:
                return {
                    "direction": "NEUTRAL",
                    "pressure_score": 0.5,
                    "confidence": "0%",
                    "strength": 0.5,
                    "trend": "UNKNOWN",
                    "status": "no_volume"
                }
            
            # Calculate weighted pressure score
            pressure_score = bid_pressure / total_pressure
            
            # Calculate pressure strength (how much total pressure exists)
            pressure_strength = min(1.0, total_pressure / 10.0)  # Normalize to 0-1
            
            # Determine direction with enhanced thresholds
            if pressure_score > 0.65:
                direction = "BUY"
                confidence = min(95, int(pressure_score * 100))
            elif pressure_score < 0.35:
                direction = "SELL"
                confidence = min(95, int((1 - pressure_score) * 100))
            else:
                direction = "NEUTRAL"
                confidence = 50
            
            # Determine trend with more granular levels
            if pressure_score > 0.75:
                trend = "VERY_STRONG_BUY"
            elif pressure_score > 0.6:
                trend = "STRONG_BUY"
            elif pressure_score > 0.55:
                trend = "BUY"
            elif pressure_score < 0.25:
                trend = "VERY_STRONG_SELL"
            elif pressure_score < 0.4:
                trend = "STRONG_SELL"
            elif pressure_score < 0.45:
                trend = "SELL"
            else:
                trend = "NEUTRAL"
            
            return {
                "direction": direction,
                "pressure_score": pressure_score,
                "confidence": f"{confidence}%",
                "strength": pressure_strength,
                "trend": trend,
                "bid_pressure": bid_pressure,
                "ask_pressure": ask_pressure,
                "total_pressure": total_pressure,
                "status": "success",
                "data_source": "enhanced_orderbook_analysis"
            }
                
        except Exception as e:
            logger.error(f"❌ Ultimate pressure analysis failed: {e}")
            return {
                "direction": "ERROR",
                "pressure_score": 0.5,
                "confidence": "0%",
                "strength": 0.5,
                "status": "error",
                "error": str(e)
            }
