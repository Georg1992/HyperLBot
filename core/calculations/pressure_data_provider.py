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
            
            bids = orderbook_data["bids"] if "bids" in orderbook_data else []
            asks = orderbook_data["asks"] if "asks" in orderbook_data else []
            
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
                    "bid_depth_15": 0.0,
                    "ask_depth_15": 0.0,
                    "total_depth_5": 0.0,
                    "total_depth_10": 0.0,
                    "total_depth_15": 0.0
                }
            
            # PROFESSIONAL: Use deeper levels (10-15) for more reliable signals
            # Research shows deeper levels reduce noise from spoofing and transient orders
            # Calculate depth for top 5 levels (backward compatibility)
            bid_depth_5 = sum(float(level['sz']) if 'sz' in level else 0 for level in bids[:5])
            ask_depth_5 = sum(float(level['sz']) if 'sz' in level else 0 for level in asks[:5])
            
            # Calculate depth for top 10 levels (primary - more reliable)
            bid_depth_10 = sum(float(level['sz']) if 'sz' in level else 0 for level in bids[:10])
            ask_depth_10 = sum(float(level['sz']) if 'sz' in level else 0 for level in asks[:10])
            
            # Calculate depth for top 15 levels (for depth concentration calculation)
            bid_depth_15 = sum(float(level['sz']) if 'sz' in level else 0 for level in bids[:15])
            ask_depth_15 = sum(float(level['sz']) if 'sz' in level else 0 for level in asks[:15])
            
            total_depth_5 = bid_depth_5 + ask_depth_5
            total_depth_10 = bid_depth_10 + ask_depth_10
            total_depth_15 = bid_depth_15 + ask_depth_15
            
            return {
                "bid_depth_5": bid_depth_5,
                "ask_depth_5": ask_depth_5,
                "bid_depth_10": bid_depth_10,
                "ask_depth_10": ask_depth_10,
                "bid_depth_15": bid_depth_15,
                "ask_depth_15": ask_depth_15,
                "total_depth_5": total_depth_5,
                "total_depth_10": total_depth_10,
                "total_depth_15": total_depth_15
            }
            
        except Exception as e:
            logger.error(f"❌ Depth metrics calculation failed: {e}")
            return {
                "bid_depth_5": 0.0,
                "ask_depth_5": 0.0,
                "bid_depth_10": 0.0,
                "ask_depth_10": 0.0,
                "bid_depth_15": 0.0,
                "ask_depth_15": 0.0,
                "total_depth_5": 0.0,
                "total_depth_10": 0.0,
                "total_depth_15": 0.0
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
            # PROFESSIONAL: Use deeper depth (10 levels) as primary - NO FALLBACKS
            total_depth_10 = depth_metrics["total_depth_10"]
            bid_depth_10 = depth_metrics["bid_depth_10"]
            ask_depth_10 = depth_metrics["ask_depth_10"]
            total_depth_15 = depth_metrics["total_depth_15"]
            
            if total_depth_10 == 0:
                return {
                    "bid_pressure_ratio": 0.5,
                    "ask_pressure_ratio": 0.5,
                    "pressure_imbalance": 0.0,
                    "depth_concentration": 1.0
                }
            
            # Calculate pressure ratios using deeper depth (more reliable)
            bid_pressure_ratio = bid_depth_10 / total_depth_10
            ask_pressure_ratio = ask_depth_10 / total_depth_10
            pressure_imbalance = bid_pressure_ratio - ask_pressure_ratio
            
            # Calculate depth concentration (10 vs 15 levels for better signal quality)
            depth_concentration = total_depth_10 / total_depth_15 if total_depth_15 > 0 else 1.0
            
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
    
    def invalidate_cache(self, cache=None):
        """
        Invalidate any cached pressure data
        
        Args:
            cache: CentralizedCache instance (optional, falls back to global singleton)
        """
        try:
            if cache is None:
                from core.services.centralized_cache import get_global_centralized_cache
                cache = get_global_centralized_cache()
            cache.invalidate_pattern("pressure_*")
            logger.debug("📊 PressureDataProvider cache invalidated")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate pressure cache: {e}")
