#!/usr/bin/env python3
"""
Order Book Analyzer Module
Analyzes order book data for market microstructure insights
"""

import time
from typing import Dict, Any, List, Optional, Tuple, Callable
from loguru import logger

# Factory function for dependency injection
def create_orderbook_analyzer() -> 'OrderBookAnalyzer':
    """
    Factory function to create OrderBookAnalyzer with dependency injection
    
    Returns:
        Configured OrderBookAnalyzer instance
    """
    return OrderBookAnalyzer()

# Deprecated global instance functions removed - use create_orderbook_analyzer() instead

class OrderBookAnalyzer:
    """Analyzes order book data for market microstructure insights"""
    
    def __init__(self):
        logger.info("📊 Order Book Analyzer initialized")
    
    def analyze_orderbook(self, orderbook_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Analyze order book data for market insights
        
        Args:
            orderbook_data: Raw order book data from Hyperliquid API
            current_price: Current market price for reference
            
        Returns:
            Dictionary with order book analysis
        """
        try:
            if not orderbook_data:
                raise Exception("No orderbook data provided")
            
            # Extract bids and asks from order book - handle ANY format
            bids = []
            asks = []
            
            
            if isinstance(orderbook_data, list):
                if len(orderbook_data) == 2:
                    # Format: [bids_list, asks_list]
                    bids = orderbook_data[0][:10] if orderbook_data[0] else []
                    asks = orderbook_data[1][:10] if orderbook_data[1] else []
                else:
                    # Format: [level1, level2, ...] - need to separate by side
                    for level in orderbook_data:
                        if isinstance(level, dict):
                            if 'side' in level and level['side'] == 'B':
                                bids.append(level)
                            elif 'side' in level and level['side'] == 'A':
                                asks.append(level)
                    bids = bids[:10]
                    asks = asks[:10]
            elif isinstance(orderbook_data, dict):
                # Format: {"levels": [bids_list, asks_list]}
                levels = orderbook_data['levels'] if 'levels' in orderbook_data else []
                if len(levels) == 2:
                    # Hyperliquid format: levels[0] = bids, levels[1] = asks
                    bids = levels[0][:10] if levels[0] else []
                    asks = levels[1][:10] if levels[1] else []
                else:
                    # Legacy format: levels with side field
                    for level in levels:
                        if isinstance(level, dict):
                            if 'side' in level and level['side'] == 'B':
                                bids.append(level)
                            elif 'side' in level and level['side'] == 'A':
                                asks.append(level)
                    bids = bids[:10]
                    asks = asks[:10]
            else:
                raise Exception(f"Unexpected orderbook data format: {type(orderbook_data)}")
            
            if not bids or not asks:
                raise Exception(f"Insufficient orderbook data - found {len(bids)} bids, {len(asks)} asks")
            
            
            # Calculate key metrics
            analysis = {
                "bid_ask_spread": self._calculate_spread(bids, asks, current_price),
                "order_imbalance": self._calculate_imbalance(bids, asks),
                "liquidity_depth": self._calculate_liquidity_depth(bids, asks),
                "market_pressure": self._calculate_market_pressure(bids, asks, current_price),
                "support_resistance_strength": self._calculate_sr_strength(bids, asks, current_price),
                "timestamp": time.time(),
                "data_source": "hyperliquid_orderbook"
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Order book analysis failed: {e}")
            raise Exception(f"Order book analysis failed: {e}")
    
    def _calculate_spread(self, bids: List[Dict], asks: List[Dict], current_price: float) -> Dict[str, Any]:
        """Calculate bid-ask spread metrics"""
        try:
            if not bids or not asks:
                return {"absolute": 0.0, "percentage": 0.0, "category": "UNKNOWN"}
            
            # Extract prices from Hyperliquid format: {"px": "117200.0", "sz": "5.77662", "n": 11}
            best_bid = float(bids[0]['px']) if bids and 'px' in bids[0] else 0.0
            best_ask = float(asks[0]['px']) if asks and 'px' in asks[0] else 0.0
            
            if best_bid == 0 or best_ask == 0:
                return {"absolute": 0.0, "percentage": 0.0, "category": "UNKNOWN"}
            
            absolute_spread = best_ask - best_bid
            if current_price <= 0:
                raise Exception(f"Invalid current price for spread calculation: {current_price}")
            percentage_spread = (absolute_spread / current_price) * 100
            
            # Categorize spread
            if percentage_spread < 0.01:  # < 0.01%
                category = "TIGHT"
            elif percentage_spread < 0.05:  # < 0.05%
                category = "NORMAL"
            elif percentage_spread < 0.1:  # < 0.1%
                category = "WIDE"
            else:
                category = "VERY_WIDE"
            
            return {
                "absolute": round(absolute_spread, 2),
                "percentage": round(percentage_spread, 4),
                "category": category,
                "best_bid": best_bid,
                "best_ask": best_ask
            }
            
        except Exception as e:
            logger.error(f"❌ Spread calculation failed: {e}")
            return {"absolute": 0.0, "percentage": 0.0, "category": "ERROR"}
    
    def _calculate_imbalance(self, bids: List[Dict], asks: List[Dict]) -> Dict[str, Any]:
        """Calculate order book imbalance (buying vs selling pressure)"""
        try:
            if not bids or not asks:
                return {"ratio": 1.0, "category": "BALANCED", "bias": 0.0}
            
            # Calculate total size on each side
            total_bid_size = sum(float(bid['sz']) if 'sz' in bid else 0.0 for bid in bids)
            total_ask_size = sum(float(ask['sz']) if 'sz' in ask else 0.0 for ask in asks)
            
            if total_bid_size == 0 and total_ask_size == 0:
                return {"ratio": 1.0, "category": "BALANCED", "bias": 0.0}
            
            # Calculate imbalance ratio
            if total_ask_size == 0:
                ratio = 10.0  # Max ratio when no asks
            else:
                ratio = total_bid_size / total_ask_size
            
            # Calculate bias (-1 to 1, where -1 is heavy selling, +1 is heavy buying)
            total_size = total_bid_size + total_ask_size
            bias = (total_bid_size - total_ask_size) / total_size if total_size > 0 else 0.0
            
            # Categorize imbalance
            if ratio > 2.0:
                category = "HEAVY_BUYING"
            elif ratio > 1.5:
                category = "BUYING_BIAS"
            elif ratio > 0.67:  # 1/1.5
                category = "BALANCED"
            elif ratio > 0.5:  # 1/2
                category = "SELLING_BIAS"
            else:
                category = "HEAVY_SELLING"
            
            return {
                "ratio": round(ratio, 2),
                "category": category,
                "bias": round(bias, 3),
                "total_bid_size": round(total_bid_size, 2),
                "total_ask_size": round(total_ask_size, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Imbalance calculation failed: {e}")
            return {"ratio": 1.0, "category": "ERROR", "bias": 0.0}
    
    def _calculate_liquidity_depth(self, bids: List[Dict], asks: List[Dict]) -> Dict[str, Any]:
        """Calculate liquidity depth at different price levels"""
        try:
            if not bids or not asks:
                return {"depth_score": 0.0, "category": "LOW", "levels_analyzed": 0}
            
            # Analyze depth at different levels
            bid_levels = len(bids)
            ask_levels = len(asks)
            total_levels = bid_levels + ask_levels
            
            # Calculate average size per level
            avg_bid_size = sum(float(bid['sz']) if 'sz' in bid else 0.0 for bid in bids) / bid_levels if bid_levels > 0 else 0
            avg_ask_size = sum(float(ask['sz']) if 'sz' in ask else 0.0 for ask in asks) / ask_levels if ask_levels > 0 else 0
            avg_size = (avg_bid_size + avg_ask_size) / 2
            
            # Calculate depth score (0-100)
            depth_score = min(100, (total_levels * 5) + (avg_size * 10))
            
            # Categorize depth
            if depth_score > 80:
                category = "VERY_HIGH"
            elif depth_score > 60:
                category = "HIGH"
            elif depth_score > 40:
                category = "MEDIUM"
            elif depth_score > 20:
                category = "LOW"
            else:
                category = "VERY_LOW"
            
            return {
                "depth_score": round(depth_score, 1),
                "category": category,
                "levels_analyzed": total_levels,
                "avg_size_per_level": round(avg_size, 2),
                "bid_levels": bid_levels,
                "ask_levels": ask_levels
            }
            
        except Exception as e:
            logger.error(f"❌ Liquidity depth calculation failed: {e}")
            return {"depth_score": 0.0, "category": "ERROR", "levels_analyzed": 0}
    
    def _calculate_market_pressure(self, bids: List[Dict], asks: List[Dict], current_price: float) -> Dict[str, Any]:
        """Calculate market pressure based on order book dynamics"""
        try:
            if not bids or not asks:
                return {"pressure": 0.0, "direction": "NEUTRAL", "strength": "WEAK"}
            
            # Calculate pressure from top 3 levels on each side
            top_bids = bids[:3]
            top_asks = asks[:3]
            
            # Weighted pressure calculation (closer to market = higher weight)
            bid_pressure = 0.0
            ask_pressure = 0.0
            
            for i, bid in enumerate(top_bids):
                weight = 3 - i  # 3, 2, 1 weights
                size = float(bid['sz']) if 'sz' in bid else 0.0
                bid_pressure += size * weight
            
            for i, ask in enumerate(top_asks):
                weight = 3 - i  # 3, 2, 1 weights
                size = float(ask['sz']) if 'sz' in ask else 0.0
                ask_pressure += size * weight
            
            # Calculate net pressure
            total_pressure = bid_pressure + ask_pressure
            if total_pressure == 0:
                return {"pressure": 0.0, "direction": "NEUTRAL", "strength": "WEAK"}
            
            net_pressure = (bid_pressure - ask_pressure) / total_pressure
            
            # Determine direction and strength
            if net_pressure > 0.3:
                direction = "BUYING"
                strength = "STRONG" if net_pressure > 0.6 else "MODERATE"
            elif net_pressure < -0.3:
                direction = "SELLING"
                strength = "STRONG" if net_pressure < -0.6 else "MODERATE"
            else:
                direction = "NEUTRAL"
                strength = "WEAK"
            
            return {
                "pressure": round(net_pressure, 3),
                "direction": direction,
                "strength": strength,
                "bid_pressure": round(bid_pressure, 2),
                "ask_pressure": round(ask_pressure, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Market pressure calculation failed: {e}")
            return {"pressure": 0.0, "direction": "ERROR", "strength": "WEAK"}
    
    def _calculate_sr_strength(self, bids: List[Dict], asks: List[Dict], current_price: float) -> Dict[str, Any]:
        """Calculate support/resistance strength from order book"""
        try:
            if not bids or not asks:
                return {"support_strength": 0.0, "resistance_strength": 0.0, "category": "WEAK"}
            
            if current_price <= 0:
                raise Exception(f"Invalid current price for S/R strength calculation: {current_price}")
            
            # Calculate support strength (bids below current price)
            support_strength = 0.0
            for bid in bids:
                bid_price = float(bid['px']) if 'px' in bid else 0.0
                if bid_price < current_price:
                    size = float(bid['sz']) if 'sz' in bid else 0.0
                    # Weight by proximity to current price
                    proximity_weight = (current_price - bid_price) / current_price
                    support_strength += size * (1 - proximity_weight)
            
            # Calculate resistance strength (asks above current price)
            resistance_strength = 0.0
            for ask in asks:
                ask_price = float(ask['px']) if 'px' in ask else 0.0
                if ask_price > current_price:
                    size = float(ask['sz']) if 'sz' in ask else 0.0
                    # Weight by proximity to current price
                    proximity_weight = (ask_price - current_price) / current_price
                    resistance_strength += size * (1 - proximity_weight)
            
            # Determine overall strength category
            total_strength = support_strength + resistance_strength
            if total_strength > 100:
                category = "VERY_STRONG"
            elif total_strength > 50:
                category = "STRONG"
            elif total_strength > 20:
                category = "MODERATE"
            else:
                category = "WEAK"
            
            return {
                "support_strength": round(support_strength, 2),
                "resistance_strength": round(resistance_strength, 2),
                "category": category,
                "total_strength": round(total_strength, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Support/resistance strength calculation failed: {e}")
            return {"support_strength": 0.0, "resistance_strength": 0.0, "category": "ERROR"}
    
