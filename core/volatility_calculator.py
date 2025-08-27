#!/usr/bin/env python3
"""
Volatility Calculator Module
Centralized volatility calculations from different data sources
"""

import statistics
from typing import Dict, Any, List, Optional
from loguru import logger


class VolatilityCalculator:
    """Centralized volatility calculation system"""
    
    def __init__(self):
        logger.info("📊 Volatility Calculator initialized")
    
    def calculate_candle_volatility(self, candles: List[Dict], timeframe: str = "5m") -> float:
        """Calculate volatility from candle data (Yahoo Finance style)"""
        try:
            if len(candles) < 10:
                return self._get_default_volatility(timeframe)
            
            # Calculate returns from close prices
            returns = []
            for i in range(1, len(candles)):
                if candles[i-1]["close"] > 0:
                    ret = (candles[i]["close"] - candles[i-1]["close"]) / candles[i-1]["close"]
                    returns.append(abs(ret))
            
            if not returns:
                return self._get_default_volatility(timeframe)
            
            # Calculate average volatility
            volatility = sum(returns) / len(returns)
            return round(volatility, 6)
            
        except Exception as e:
            logger.warning(f"Candle volatility calculation failed: {e}")
            return self._get_default_volatility(timeframe)
    
    def calculate_volatility_5m(self, candles_5m: List[Dict]) -> float:
        """Calculate 5-minute volatility from candles"""
        return self.calculate_candle_volatility(candles_5m, "5m")
    
    def calculate_volatility_1h(self, candles_1h: List[Dict]) -> float:
        """Calculate 1-hour volatility from candles"""
        return self.calculate_candle_volatility(candles_1h, "1h")
    
    def calculate_volatility_1d(self, candles_1d: List[Dict]) -> float:
        """Calculate 1-day volatility from candles"""
        return self.calculate_candle_volatility(candles_1d, "1d")
    
    def calculate_orderbook_volatility(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate volatility from orderbook data (Hyperliquid style)"""
        try:
            # Extract orderbook data
            bids = orderbook_data.get("bids", [])
            asks = orderbook_data.get("asks", [])
            
            if not bids or not asks:
                return self._get_default_orderbook_volatility()
            
            # Calculate spreads
            spreads = []
            for i in range(min(len(bids), len(asks))):
                spread = (asks[i][0] - bids[i][0]) / bids[i][0]
                spreads.append(spread)
            
            if not spreads:
                return self._get_default_orderbook_volatility()
            
            # Calculate spread volatility
            spread_volatility = statistics.mean(spreads)
            
            # Calculate depth volatility (how much depth varies across levels)
            bid_depths = [bid[1] for bid in bids[:10]]  # First 10 levels
            ask_depths = [ask[1] for ask in asks[:10]]
            
            depth_volatility = 0.0
            if bid_depths and ask_depths:
                all_depths = bid_depths + ask_depths
                mean_depth = statistics.mean(all_depths)
                if mean_depth > 0:
                    depth_std = statistics.stdev(all_depths) if len(all_depths) > 1 else 0
                    depth_volatility = depth_std / mean_depth
                    depth_volatility = min(depth_volatility, 0.5)  # Cap at 50%
            
            # Combine spread and depth volatility
            combined_volatility = (spread_volatility * 0.6) + (depth_volatility * 0.4)
            combined_volatility = min(combined_volatility, 0.1)  # Cap at 10%
            combined_volatility = max(combined_volatility, 0.0)
            
            # Categorize volatility
            if combined_volatility > 0.005:  # 0.5%
                volatility_category = "HIGH"
            elif combined_volatility > 0.002:  # 0.2%
                volatility_category = "MEDIUM"
            else:
                volatility_category = "LOW"
            
            # Determine volatility trend
            if len(spreads) >= 3:
                recent_spreads = spreads[-3:]
                if recent_spreads[-1] > recent_spreads[0] * 1.1:
                    volatility_trend = "INCREASING"
                elif recent_spreads[-1] < recent_spreads[0] * 0.9:
                    volatility_trend = "DECREASING"
                else:
                    volatility_trend = "STABLE"
            else:
                volatility_trend = "UNKNOWN"
            
            return {
                "volatility_5m": combined_volatility,
                "volatility_category": volatility_category,
                "spread_volatility": spread_volatility,
                "depth_volatility": depth_volatility,
                "volatility_trend": volatility_trend,
                "avg_spread": spread_volatility,
                "data_source": "orderbook_volatility_analysis"
            }
            
        except Exception as e:
            logger.error(f"Orderbook volatility calculation failed: {e}")
            return self._get_default_orderbook_volatility()
    
    def calculate_price_acceleration(self, candles: List[Dict]) -> float:
        """Calculate price acceleration (rate of change of price changes)"""
        try:
            if len(candles) < 4:
                return 0.0
            
            # Calculate price changes
            prices = [candle["close"] for candle in candles[-4:]]
            price_changes = []
            
            for i in range(1, len(prices)):
                change = (prices[i] - prices[i-1]) / prices[i-1]
                price_changes.append(change)
            
            # Calculate acceleration (change in rate of change)
            if len(price_changes) >= 2:
                acceleration = abs(price_changes[-1] - price_changes[-2])
                return acceleration
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Price acceleration calculation failed: {e}")
            return 0.0
    
    def calculate_momentum_volatility(self, candles: List[Dict]) -> Dict[str, Any]:
        """Calculate momentum-based volatility indicators"""
        try:
            if len(candles) < 5:
                return {"momentum_volatility": 0.0, "momentum_strength": 0.0}
            
            # Calculate recent momentum
            recent_prices = [candle["close"] for candle in candles[-5:]]
            recent_volumes = [candle["volume"] for candle in candles[-5:]]
            
            # Calculate price momentum
            price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            # Calculate volume momentum
            avg_volume = sum(recent_volumes[:-1]) / len(recent_volumes[:-1])
            current_volume = recent_volumes[-1]
            volume_surge = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Calculate momentum volatility
            momentum_volatility = abs(price_momentum) * volume_surge
            momentum_strength = min(1.0, abs(price_momentum) * 100 + (volume_surge - 1.0) * 0.5)
            
            return {
                "momentum_volatility": momentum_volatility,
                "momentum_strength": momentum_strength,
                "price_momentum": price_momentum,
                "volume_surge": volume_surge
            }
            
        except Exception as e:
            logger.error(f"Momentum volatility calculation failed: {e}")
            return {"momentum_volatility": 0.0, "momentum_strength": 0.0}
    
    def _get_default_volatility(self, timeframe: str) -> float:
        """Get default volatility values for different timeframes"""
        defaults = {
            "1m": 0.002,
            "5m": 0.003,
            "1h": 0.005,
            "1d": 0.008
        }
        return defaults.get(timeframe, 0.003)
    
    def _get_default_orderbook_volatility(self) -> Dict[str, Any]:
        """Get default orderbook volatility structure"""
        return {
            "volatility_5m": 0.0,
            "volatility_category": "UNKNOWN",
            "spread_volatility": 0.0,
            "depth_volatility": 0.0,
            "volatility_trend": "UNKNOWN",
            "avg_spread": 0.0,
            "data_source": "orderbook_volatility_analysis"
        }
