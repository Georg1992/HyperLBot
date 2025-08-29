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
        """Calculate volatility from orderbook data using MarketOrderbookAnalyzer"""
        try:
            # Import MarketOrderbookAnalyzer to avoid circular imports
            from core.analysis.real_time.orderbook_analyzer import MarketOrderbookAnalyzer
            
            # Create a mock API instance for the analysis
            class MockAPI:
                def __init__(self, orderbook_data):
                    self.orderbook_data = orderbook_data
                    self.config = type('Config', (), {'SYMBOL': 'BTC'})()
                
                def get_market_data(self, symbol):
                    return {
                        'levels': [
                            [{'px': str(bid[0]), 'sz': str(bid[1])} for bid in orderbook_data.get('bids', [])],
                            [{'px': str(ask[0]), 'sz': str(ask[1])} for ask in orderbook_data.get('asks', [])]
                        ]
                    }
            
            # Use MarketOrderbookAnalyzer for the calculation
            mock_api = MockAPI(orderbook_data)
            analyzer = MarketOrderbookAnalyzer(mock_api)
            return analyzer.get_volatility_analysis()
            
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
            
            # Calculate momentum volatility - FIX: prevent volume surge inflation
            # Cap volume surge impact to prevent artificial volatility inflation
            volume_surge_capped = min(volume_surge, 3.0)  # Cap at 3x normal volume
            momentum_volatility = abs(price_momentum) * min(volume_surge_capped, 2.0)  # Further cap momentum impact
            
            # Cap momentum volatility at realistic levels for Bitcoin
            momentum_volatility = min(momentum_volatility, 0.02)  # Max 2% momentum volatility
            
            momentum_strength = min(1.0, abs(price_momentum) * 100 + (volume_surge - 1.0) * 0.5)
            
            # DEBUG: Log momentum volatility calculation
            logger.info(f"🔍 Momentum calc: price_momentum={price_momentum:.6f}, volume_surge={volume_surge:.2f}, result={momentum_volatility:.6f}")
            
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
        """Get default volatility values for different timeframes - REALISTIC Bitcoin ranges"""
        defaults = {
            "1m": 0.0005,    # 0.05% - very quiet Bitcoin 1-min
            "5m": 0.001,     # 0.1% - quiet Bitcoin 5-min  
            "1h": 0.002,     # 0.2% - normal Bitcoin 1-hour
            "1d": 0.005      # 0.5% - normal Bitcoin daily
        }
        return defaults.get(timeframe, 0.001)
    
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
