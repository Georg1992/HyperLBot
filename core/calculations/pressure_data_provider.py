#!/usr/bin/env python3
"""
Pressure Data Provider Module
Provides orderbook data and basic pressure calculations for the PressureCalculator
"""

import time
from typing import Dict, List, Any, Tuple
from loguru import logger


class PressureDataProvider:
    """
    Provides orderbook data and basic pressure calculations.
    Encapsulates data access and basic data processing for pressure analysis.
    """
    
    def __init__(self, symbol: str = "BTC"):
        self.symbol = symbol
        logger.debug(f"📊 PressureDataProvider initialized for {symbol}")
    
    def fetch_orderbook_data(self, orderbook_analyzer) -> Dict[str, Any]:
        """
        Fetch orderbook data from orderbook analyzer.
        
        Args:
            orderbook_analyzer: OrderBookAnalyzer instance
        
        Returns:
            Dictionary with orderbook data
        """
        try:
            if not orderbook_analyzer:
                raise ValueError("Orderbook analyzer not available")
            
            # Get orderbook data
            orderbook_data = orderbook_analyzer.get_latest_analysis()
            
            if not orderbook_data:
                return {"bids": [], "asks": [], "timestamp": time.time()}
            
            bids = orderbook_data.get("bids", [])
            asks = orderbook_data.get("asks", [])
            
            return {
                "bids": bids,
                "asks": asks,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch orderbook data: {e}")
            raise ValueError(f"Orderbook data fetching failed: {e}")
    
    def calculate_depth_metrics(self, bids: List[Dict], asks: List[Dict]) -> Dict[str, Any]:
        """
        Calculate basic depth metrics from orderbook data.
        
        Args:
            bids: List of bid levels
            asks: List of ask levels
        
        Returns:
            Dictionary with depth metrics
        """
        try:
            if not bids or not asks:
                return {
                    "bid_depth_5": 0.0,
                    "ask_depth_5": 0.0,
                    "bid_depth_10": 0.0,
                    "ask_depth_10": 0.0,
                    "total_depth_5": 0.0,
                    "total_depth_10": 0.0
                }
            
            # Calculate depth for top 5 levels
            bid_depth_5 = sum(float(level.get('sz', 0)) for level in bids[:5])
            ask_depth_5 = sum(float(level.get('sz', 0)) for level in asks[:5])
            
            # Calculate depth for top 10 levels
            bid_depth_10 = sum(float(level.get('sz', 0)) for level in bids[:10])
            ask_depth_10 = sum(float(level.get('sz', 0)) for level in asks[:10])
            
            total_depth_5 = bid_depth_5 + ask_depth_5
            total_depth_10 = bid_depth_10 + ask_depth_10
            
            return {
                "bid_depth_5": bid_depth_5,
                "ask_depth_5": ask_depth_5,
                "bid_depth_10": bid_depth_10,
                "ask_depth_10": ask_depth_10,
                "total_depth_5": total_depth_5,
                "total_depth_10": total_depth_10
            }
            
        except Exception as e:
            logger.error(f"❌ Depth metrics calculation failed: {e}")
            return {
                "bid_depth_5": 0.0,
                "ask_depth_5": 0.0,
                "bid_depth_10": 0.0,
                "ask_depth_10": 0.0,
                "total_depth_5": 0.0,
                "total_depth_10": 0.0
            }
    
    def calculate_pressure_ratios(self, depth_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate pressure ratios from depth metrics.
        
        Args:
            depth_metrics: Dictionary with depth metrics
        
        Returns:
            Dictionary with pressure ratios
        """
        try:
            total_depth_5 = depth_metrics.get("total_depth_5", 0.0)
            bid_depth_5 = depth_metrics.get("bid_depth_5", 0.0)
            ask_depth_5 = depth_metrics.get("ask_depth_5", 0.0)
            total_depth_10 = depth_metrics.get("total_depth_10", 0.0)
            
            if total_depth_5 == 0:
                return {
                    "bid_pressure_ratio": 0.5,
                    "ask_pressure_ratio": 0.5,
                    "pressure_imbalance": 0.0,
                    "depth_concentration": 1.0
                }
            
            # Calculate pressure ratios
            bid_pressure_ratio = bid_depth_5 / total_depth_5
            ask_pressure_ratio = ask_depth_5 / total_depth_5
            pressure_imbalance = bid_pressure_ratio - ask_pressure_ratio
            
            # Calculate depth concentration
            depth_concentration = total_depth_5 / total_depth_10 if total_depth_10 > 0 else 1.0
            
            return {
                "bid_pressure_ratio": bid_pressure_ratio,
                "ask_pressure_ratio": ask_pressure_ratio,
                "pressure_imbalance": pressure_imbalance,
                "depth_concentration": depth_concentration
            }
            
        except Exception as e:
            logger.error(f"❌ Pressure ratios calculation failed: {e}")
            return {
                "bid_pressure_ratio": 0.5,
                "ask_pressure_ratio": 0.5,
                "pressure_imbalance": 0.0,
                "depth_concentration": 1.0
            }
    
    def invalidate_cache(self):
        """Invalidate any cached pressure data"""
        try:
            from core.services.centralized_cache import get_global_centralized_cache
            cache = get_global_centralized_cache()
            cache.invalidate_pattern("pressure_*")
            logger.debug("📊 PressureDataProvider cache invalidated")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate pressure cache: {e}")
