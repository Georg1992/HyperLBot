#!/usr/bin/env python3
"""
Future Candle Prediction Engine
===============================
Clean prediction engine ready for future candle modeling.
Removed all old trading signal logic - now focused on market analysis for candle prediction.

PURPOSE: Analyze market data to prepare for future candle prediction
FUTURE: Will implement 2-3 future candle prediction (1m or 5m depending on strategy)
"""

import time
from typing import Dict, Any, Optional, List
from loguru import logger


class PredictionEngine:
    """
    Future Candle Prediction Engine
    
    Current: Market data analysis and preparation
    Future: Will predict 2-3 future candles based on current market state
    """
    
    def __init__(self):
        # Simple tracking
        self.last_analysis = None
        self.last_update_time = 0
        
        logger.info("🎯 Future Candle Prediction Engine initialized - Ready for candle modeling")
    
    def analyze_market_for_prediction(self, current_price: float, market_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze market data to prepare for future candle prediction
        
        Args:
            current_price: Current market price
            market_data: Additional market data (RSI, trends, volume, etc.)
            
        Returns:
            Dict with market analysis data or None
        """
        try:
            market_data = market_data or {}
            
            # Extract key market indicators
            rsi = market_data.get("rsi", 50.0)
            trend = market_data.get("trend", "NEUTRAL")
            volatility_category = market_data.get("volatility_category", "MODERATE")
            volume_category = market_data.get("volume_category", "NORMAL")
            
            # Analyze market conditions for prediction
            market_analysis = {
                "current_price": current_price,
                "rsi": rsi,
                "trend": trend,
                "volatility_category": volatility_category,
                "volume_category": volume_category,
                "market_regime": self._determine_market_regime(rsi, trend, volatility_category, volume_category),
                "prediction_readiness": self._assess_prediction_readiness(market_data),
                "timestamp": time.time(),
                "analysis_type": "MARKET_ANALYSIS"
            }
            
            # Update tracking
            self.last_analysis = market_analysis
            self.last_update_time = time.time()
            
            logger.debug(f"🎯 Market analysis: {market_analysis['market_regime']} regime, RSI: {rsi:.1f}")
            return market_analysis
            
        except Exception as e:
            logger.error(f"❌ Market analysis failed: {e}")
            return None
    
    def _determine_market_regime(self, rsi: float, trend: str, volatility_category: str, volume_category: str) -> str:
        """
        Determine current market regime for prediction context
        
        Returns:
            Market regime string (e.g., "BULLISH_CONSOLIDATION", "BEARISH_BREAKOUT", etc.)
        """
        try:
            # RSI-based regime
            if rsi < 30:
                rsi_regime = "OVERSOLD"
            elif rsi > 70:
                rsi_regime = "OVERBOUGHT"
            elif 40 <= rsi <= 60:
                rsi_regime = "NEUTRAL"
            else:
                rsi_regime = "MOMENTUM"
            
            # Trend-based regime
            if trend in ["STRONG_UPTREND", "UPTREND"]:
                trend_regime = "BULLISH"
            elif trend in ["STRONG_DOWNTREND", "DOWNTREND"]:
                trend_regime = "BEARISH"
            else:
                trend_regime = "SIDEWAYS"
            
            # Volatility-based regime
            if volatility_category in ["HIGH", "VERY_HIGH"]:
                vol_regime = "VOLATILE"
            elif volatility_category in ["LOW", "VERY_LOW"]:
                vol_regime = "STABLE"
            else:
                vol_regime = "MODERATE"
            
            # Volume-based regime
            if volume_category in ["HIGH", "VERY_HIGH", "EXTREMELY_HIGH"]:
                vol_flow = "HIGH_VOLUME"
            elif volume_category in ["LOW", "VERY_LOW", "BELOW_AVERAGE"]:
                vol_flow = "LOW_VOLUME"
            else:
                vol_flow = "NORMAL_VOLUME"
            
            # Combine regimes
            if trend_regime == "BULLISH" and rsi_regime == "OVERSOLD":
                return "BULLISH_REVERSAL_SETUP"
            elif trend_regime == "BEARISH" and rsi_regime == "OVERBOUGHT":
                return "BEARISH_REVERSAL_SETUP"
            elif trend_regime == "BULLISH" and vol_regime == "VOLATILE":
                return "BULLISH_BREAKOUT"
            elif trend_regime == "BEARISH" and vol_regime == "VOLATILE":
                return "BEARISH_BREAKOUT"
            elif trend_regime == "SIDEWAYS" and vol_flow == "HIGH_VOLUME":
                return "CONSOLIDATION_BREAKOUT_PENDING"
            elif trend_regime == "SIDEWAYS" and vol_flow == "LOW_VOLUME":
                return "CONSOLIDATION_CONTINUATION"
            else:
                return f"{trend_regime}_{vol_regime}_{vol_flow}"
                
        except Exception as e:
            logger.error(f"❌ Market regime determination failed: {e}")
            return "UNKNOWN"
    
    def _assess_prediction_readiness(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess if market data is sufficient for reliable prediction
        
        Returns:
            Dict with readiness assessment
        """
        try:
            readiness = {
                "data_quality": "GOOD",
                "missing_indicators": [],
                "confidence_factors": [],
                "ready_for_prediction": True
            }
            
            # Check for essential data
            required_fields = ["rsi", "trend", "volatility_category", "volume_category"]
            for field in required_fields:
                if field not in market_data or market_data[field] is None:
                    readiness["missing_indicators"].append(field)
                    readiness["ready_for_prediction"] = False
            
            # Assess confidence factors
            if market_data.get("rsi") and 20 <= market_data["rsi"] <= 80:
                readiness["confidence_factors"].append("RSI_IN_RANGE")
            
            if market_data.get("trend") and market_data["trend"] != "UNKNOWN":
                readiness["confidence_factors"].append("TREND_DETECTED")
            
            if market_data.get("volume_category") and market_data["volume_category"] != "NO_DATA":
                readiness["confidence_factors"].append("VOLUME_DATA_AVAILABLE")
            
            # Overall assessment
            if len(readiness["missing_indicators"]) > 0:
                readiness["data_quality"] = "POOR"
            elif len(readiness["confidence_factors"]) >= 3:
                readiness["data_quality"] = "EXCELLENT"
            elif len(readiness["confidence_factors"]) >= 2:
                readiness["data_quality"] = "GOOD"
            else:
                readiness["data_quality"] = "FAIR"
            
            return readiness
            
        except Exception as e:
            logger.error(f"❌ Prediction readiness assessment failed: {e}")
            return {
                "data_quality": "POOR",
                "missing_indicators": ["ASSESSMENT_FAILED"],
                "confidence_factors": [],
                "ready_for_prediction": False
            }
    
    def generate_historical_candles(self, current_price: float, market_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get last 12 real historical candles from Hyperliquid API
        
        Args:
            current_price: Current market price
            market_data: Additional market data
            
        Returns:
            List of 12 real historical candle dictionaries
        """
        try:
            # Try to get real data from Hyperliquid first
            from core.api.hyperliquid_api import HyperliquidAPI
            
            # Get real historical data from Hyperliquid
            # Use 5m candles for better trend analysis
            interval = "5m"  # 5-minute candles
            
            logger.info(f"🕯️ Starting candle generation for price: ${current_price:.2f}")
            
            # Create Hyperliquid API instance
            hyperliquid_api = HyperliquidAPI()
            
            # Fetch last 12 candles from Hyperliquid
            logger.info(f"🕯️ Calling Hyperliquid API for {interval} candles...")
            candles = hyperliquid_api.get_historical_candles(
                symbol="BTC",
                interval=interval,
                limit=12
            )
            
            logger.info(f"🕯️ Hyperliquid API returned: {len(candles) if candles else 0} candles")
            
            if not candles or len(candles) < 12:
                logger.error(f"❌ Insufficient data from Hyperliquid: {len(candles) if candles else 0} candles (need 12)")
                raise Exception(f"Hyperliquid API returned insufficient data: {len(candles) if candles else 0} candles")
            
            # Hyperliquid API already returns candles in our format
            formatted_candles = candles
            
            logger.info(f"✅ Fetched {len(formatted_candles)} real Hyperliquid candles, price range: ${min(c['low'] for c in formatted_candles):.2f} - ${max(c['high'] for c in formatted_candles):.2f}")
            return formatted_candles
            
        except Exception as e:
            logger.error(f"❌ Candle generation failed: {e}")
            raise Exception(f"Failed to generate real candle data: {e}")
    
    def _generate_fallback_candles(self, current_price: float) -> List[Dict[str, Any]]:
        """Generate realistic fallback candles with proper OHLC patterns"""
        try:
            import random
            candles = []
            current_time = time.time()
            
            # Start from current price and create realistic 5-minute movements
            base_price = current_price
            
            for i in range(12):
                candle_time = current_time - ((11 - i) * 300)  # 5 minute intervals (300 seconds), chronological order
                
                # Create realistic price movement patterns
                if i == 0:
                    # First candle starts from current price
                    open_price = base_price
                else:
                    # Open from previous close
                    open_price = candles[-1]["close"]
                
                # Generate realistic 5-minute price movements (0.05% to 0.3% range)
                price_change_pct = random.uniform(-0.003, 0.003)  # -0.3% to +0.3% for 5m candles
                close_price = open_price * (1 + price_change_pct)
                
                # Generate realistic high/low with proper wicks (smaller for 5m candles)
                body_size = abs(close_price - open_price)
                wick_size = body_size * random.uniform(0.3, 1.5)  # Smaller wicks for 5m candles
                
                high_price = max(open_price, close_price) + wick_size
                low_price = min(open_price, close_price) - wick_size
                
                # Generate realistic volume for 5-minute periods (0.1 to 1.5 BTC)
                volume = random.uniform(0.1, 1.5)
                
                # Add some volume spikes occasionally
                if random.random() < 0.15:  # 15% chance of volume spike
                    volume *= random.uniform(1.5, 3.0)
                
                candle = {
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": round(volume, 2),
                    "timestamp": int(candle_time)
                }
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            logger.error(f"❌ Fallback candle generation failed: {e}")
            return []
    
    def get_last_analysis(self) -> Optional[Dict[str, Any]]:
        """Get the last market analysis"""
        return self.last_analysis
    
    def is_analysis_fresh(self, max_age_seconds: int = 60) -> bool:
        """Check if the last analysis is still fresh"""
        if not self.last_analysis:
            return False
        return (time.time() - self.last_update_time) <= max_age_seconds
    
    def generate_candle_data(self, current_price: float, market_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Generate historical candle data for visualization (no predictions yet)
        
        Args:
            current_price: Current market price
            market_data: Additional market data (RSI, trends, volume, etc.)
            
        Returns:
            Dict with historical candle data or None
        """
        try:
            market_data = market_data or {}
            
            # Generate historical candles (last 12) - REAL DATA ONLY
            historical_candles = self.generate_historical_candles(current_price, market_data)
            
            # For now, no predicted candles - just empty array
            predicted_candles = []
            
            candle_data = {
                "historical": historical_candles,
                "predicted": predicted_candles,
                "timestamp": time.time(),
                "data_source": "hyperliquid_api"
            }
            
            return candle_data
            
        except Exception as e:
            logger.error(f"❌ Candle data generation failed: {e}")
            # Return empty data instead of None to prevent dashboard crashes
            return {
                "historical": [],
                "predicted": [],
                "timestamp": time.time(),
                "data_source": "error",
                "error": str(e)
            }
    
    def _generate_historical_candles(self, current_price: float, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate last 12 historical candles"""
        try:
            candles = []
            base_time = time.time() - (12 * 60)  # 12 minutes ago
            
            # Get market indicators for realistic candle generation
            rsi = market_data.get("rsi", 50.0)
            trend = market_data.get("trend", "NEUTRAL")
            volatility_category = market_data.get("volatility_category", "MODERATE")
            
            # Calculate volatility factor
            volatility_factor = self._get_volatility_factor(volatility_category)
            
            # Generate 12 candles with realistic price movements
            for i in range(12):
                candle_time = base_time + (i * 60)  # Each candle is 1 minute
                
                # Calculate price movement based on trend and RSI
                if i == 0:
                    # First candle starts from a base price
                    base_candle_price = current_price * 0.98  # Start slightly below current
                else:
                    # Subsequent candles build on previous close
                    base_candle_price = candles[-1]["close"]
                
                # Generate OHLC based on market conditions
                open_price = base_candle_price
                close_price = self._calculate_close_price(open_price, rsi, trend, volatility_factor)
                high_price = max(open_price, close_price) + (volatility_factor * open_price * 0.001)
                low_price = min(open_price, close_price) - (volatility_factor * open_price * 0.001)
                
                # Generate volume based on volatility
                volume = self._calculate_volume(volatility_factor, rsi)
                
                candle = {
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": round(volume, 2),
                    "timestamp": candle_time
                }
                
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            logger.error(f"❌ Historical candle generation failed: {e}")
            return []
    
    def _generate_predicted_candles(self, current_price: float, market_data: Dict[str, Any], historical_candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate next 3 predicted candles"""
        try:
            if not historical_candles:
                return []
            
            predicted_candles = []
            last_candle = historical_candles[-1]
            base_time = time.time()
            
            # Get market indicators for prediction
            rsi = market_data.get("rsi", 50.0)
            trend = market_data.get("trend", "NEUTRAL")
            volatility_category = market_data.get("volatility_category", "MODERATE")
            market_regime = market_data.get("market_regime", "UNKNOWN")
            
            # Calculate volatility factor
            volatility_factor = self._get_volatility_factor(volatility_category)
            
            # Generate 3 predicted candles
            for i in range(3):
                candle_time = base_time + ((i + 1) * 60)  # Future minutes
                
                if i == 0:
                    # First predicted candle starts from last historical close
                    open_price = last_candle["close"]
                else:
                    # Subsequent candles build on previous predicted close
                    open_price = predicted_candles[-1]["close"]
                
                # Predict close price based on market regime and trend
                close_price = self._predict_close_price(open_price, rsi, trend, market_regime, volatility_factor, i)
                high_price = max(open_price, close_price) + (volatility_factor * open_price * 0.002)
                low_price = min(open_price, close_price) - (volatility_factor * open_price * 0.002)
                
                # Predict volume (usually higher for predicted candles)
                volume = self._calculate_volume(volatility_factor, rsi) * 1.2
                
                candle = {
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": round(volume, 2),
                    "timestamp": candle_time
                }
                
                predicted_candles.append(candle)
            
            return predicted_candles
            
        except Exception as e:
            logger.error(f"❌ Predicted candle generation failed: {e}")
            return []
    
    def _get_volatility_factor(self, volatility_category: str) -> float:
        """Get volatility factor based on category"""
        volatility_map = {
            "VERY_LOW": 0.3,
            "LOW": 0.5,
            "MODERATE": 1.0,
            "HIGH": 1.5,
            "VERY_HIGH": 2.0,
            "EXTREMELY_HIGH": 3.0
        }
        return volatility_map.get(volatility_category, 1.0)
    
    def _calculate_close_price(self, open_price: float, rsi: float, trend: str, volatility_factor: float) -> float:
        """Calculate realistic close price based on market conditions"""
        try:
            # Base movement based on RSI
            if rsi < 30:  # Oversold - likely to bounce up
                base_movement = 0.002  # 0.2% up
            elif rsi > 70:  # Overbought - likely to pull back
                base_movement = -0.002  # 0.2% down
            else:  # Neutral RSI
                base_movement = 0.0005  # Small movement
            
            # Adjust for trend
            if "UPTREND" in trend.upper():
                base_movement += 0.001  # More bullish
            elif "DOWNTREND" in trend.upper():
                base_movement -= 0.001  # More bearish
            
            # Apply volatility
            movement = base_movement * volatility_factor
            
            # Add some randomness
            import random
            random_factor = random.uniform(-0.5, 0.5) * volatility_factor * 0.001
            movement += random_factor
            
            return open_price * (1 + movement)
            
        except Exception as e:
            logger.error(f"❌ Close price calculation failed: {e}")
            return open_price
    
    def _predict_close_price(self, open_price: float, rsi: float, trend: str, market_regime: str, volatility_factor: float, candle_index: int) -> float:
        """Predict close price for future candles"""
        try:
            # Base prediction on market regime
            if "BULLISH" in market_regime.upper():
                base_movement = 0.003  # 0.3% up
            elif "BEARISH" in market_regime.upper():
                base_movement = -0.003  # 0.3% down
            elif "REVERSAL" in market_regime.upper():
                # Reversal setup - predict opposite movement
                if rsi < 30:  # Oversold reversal
                    base_movement = 0.004  # Strong up
                elif rsi > 70:  # Overbought reversal
                    base_movement = -0.004  # Strong down
                else:
                    base_movement = 0.001  # Small movement
            else:
                base_movement = 0.001  # Neutral
            
            # Adjust for trend strength
            if "STRONG" in trend.upper():
                base_movement *= 1.5
            
            # Apply volatility
            movement = base_movement * volatility_factor
            
            # Add some randomness for realism
            import random
            random_factor = random.uniform(-0.3, 0.3) * volatility_factor * 0.001
            movement += random_factor
            
            return open_price * (1 + movement)
            
        except Exception as e:
            logger.error(f"❌ Close price prediction failed: {e}")
            return open_price
    
    def _calculate_volume(self, volatility_factor: float, rsi: float) -> float:
        """Calculate realistic volume based on market conditions"""
        try:
            # Base volume
            base_volume = 1.0  # 1 BTC base volume
            
            # Adjust for volatility
            volume = base_volume * volatility_factor
            
            # Adjust for RSI extremes (higher volume during extremes)
            if rsi < 25 or rsi > 75:
                volume *= 1.5  # 50% more volume during extremes
            
            # Add some randomness
            import random
            random_factor = random.uniform(0.7, 1.3)
            volume *= random_factor
            
            return max(volume, 0.1)  # Minimum volume
            
        except Exception as e:
            logger.error(f"❌ Volume calculation failed: {e}")
            return 1.0


# Note: No global instance - each component should create its own instance