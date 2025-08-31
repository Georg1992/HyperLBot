#!/usr/bin/env python3
"""
Market Data Analyzer Module
Handles market data analysis and RSI calculations
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger
from core.constants import magic_numbers
from core.external.yahoo_data_fetcher import yahoo_data_fetcher
from core.external.yahoo_volume_analyzer import volume_analyzer
from core.external.yahoo_momentum_analyzer import momentum_analyzer
from core.analysis.session.session_historical_data_manager import session_historical_data_manager

class MarketDataAnalyzer:
    """Handles market data analysis and RSI calculations with session context"""
    
    def __init__(self):
        # Use global instances to eliminate duplicate objects and ensure consistency
        self.yahoo_fetcher = yahoo_data_fetcher
        self.volume_analyzer = volume_analyzer
        self.momentum_analyzer = momentum_analyzer
        self.session_manager = session_historical_data_manager
        logger.info("📊 Market Data Analyzer initialized with global shared instances")
    
    def get_current_price(self) -> Optional[float]:
        """Get current price from Yahoo Finance (historical context only)"""
        try:
            # Get the most recent 5-minute candle
            candles = self.get_5m_candles("BTC", 1)
            if candles and len(candles) > 0:
                return candles[0]['close']
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get current price: {e}")
            return None
    
    def _calculate_sma(self, candles: List[Dict], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(candles) < period:
            return 0.0
        
        prices = [c['close'] for c in candles[-period:]]
        return sum(prices) / len(prices)
    
    def _determine_market_condition(self, sma_5m: float, sma_20m: float, current_price: float) -> str:
        """Determine market condition based on moving averages and current price"""
        if sma_5m == 0 or sma_20m == 0:
            return "NEUTRAL"
        
        if current_price > sma_5m > sma_20m:
            return "BULLISH"
        elif current_price < sma_5m < sma_20m:
            return "BEARISH"
        elif sma_5m > sma_20m:
            return "BULLISH"
        elif sma_5m < sma_20m:
            return "BEARISH"
        else:
            return "SIDEWAYS"
    
    def get_yahoo_analysis(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get comprehensive Yahoo Finance market analysis"""
        try:
            # Get current market data
            current_price = self.get_current_price()
            if not current_price:
                return {"error": "No current price available"}
            
            # Get 5-minute candles for analysis
            candles_5m = self.get_5m_candles("BTC", 20)
            if not candles_5m:
                return {"error": "No 5-minute candle data available"}
            
            # Calculate basic indicators
            sma_5m = self._calculate_sma(candles_5m, 5)
            sma_20m = self._calculate_sma(candles_5m, 20)
            
            # Determine market condition
            market_condition = self._determine_market_condition(sma_5m, sma_20m, current_price)
            
            # Get volume analysis
            volume_data = self.volume_analyzer.analyze_volume_data(candles_5m)
            
            # Get momentum analysis
            momentum_data = self.momentum_analyzer.analyze_momentum(candles_5m)
            
            return {
                "current_price": current_price,
                "market_condition": market_condition,
                "sma_5m": sma_5m,
                "sma_20m": sma_20m,
                "volume_analysis": volume_data,
                "momentum_analysis": momentum_data,
                "data_source": "yahoo_finance",
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo analysis: {e}")
            return {"error": str(e)}
    
    def get_candles(self, symbol: str, interval: str, count: int) -> List[Dict[str, Any]]:
        """Get candles for any timeframe"""
        try:
            return self.yahoo_fetcher.get_klines(symbol, interval, count)
        except Exception as e:
            logger.error(f"❌ Failed to get {interval} candles: {e}")
            return []
    
    def get_1m_candles(self, symbol: str = "BTC", count: int = 10) -> List[Dict[str, Any]]:
        """Get 1-minute candles"""
        return self.get_candles(symbol, "1m", count)
    
    def get_5m_candles(self, symbol: str = "BTC", count: int = 10) -> List[Dict[str, Any]]:
        """Get 5-minute candles"""
        return self.get_candles(symbol, "5m", count)
    
    def get_1h_candles(self, symbol: str = "BTC", count: int = 10) -> List[Dict[str, Any]]:
        """Get 1-hour candles"""
        return self.get_candles(symbol, "1h", count)
    
    def get_1d_candles(self, symbol: str = "BTC", count: int = 10) -> List[Dict[str, Any]]:
        """Get 1-day candles"""
        return self.get_candles(symbol, "1d", count)
    
    def test_connection(self) -> bool:
        """Test Yahoo Finance connection"""
        try:
            test_candles = self.get_5m_candles("BTC", 5)
            return test_candles and len(test_candles) > 0
        except Exception as e:
            logger.error(f"❌ Yahoo Finance connection test failed: {e}")
            return False
    
    def get_weekly_trend_analysis(self) -> Dict[str, Any]:
        """Get weekly trend analysis for long-term context"""
        try:
            # Get daily candles for weekly analysis
            candles_1d = self.get_1d_candles("BTC", 30)
            
            if not candles_1d or len(candles_1d) < 7:
                return {
                    "error": "Insufficient daily data for weekly analysis",
                    "weekly_trend": "UNKNOWN"
                }
            
            # Calculate weekly trend
            recent_week = candles_1d[-7:]
            week_start = recent_week[0]["close"]
            week_end = recent_week[-1]["close"]
            
            if week_start > 0:
                weekly_change = (week_end - week_start) / week_start
                weekly_change_pct = weekly_change * 100
                
                # Determine trend
                if weekly_change > 0.02:  # > 2%
                    weekly_trend = "STRONG_UPTREND"
                elif weekly_change > 0.005:  # > 0.5%
                    weekly_trend = "UPTREND"
                elif weekly_change < -0.02:  # < -2%
                    weekly_trend = "STRONG_DOWNTREND"
                elif weekly_change < -0.005:  # < -0.5%
                    weekly_trend = "DOWNTREND"
                else:
                    weekly_trend = "SIDEWAYS"
                
                # Calculate volatility
                weekly_highs = [c["high"] for c in recent_week]
                weekly_lows = [c["low"] for c in recent_week]
                avg_range = sum([h - l for h, l in zip(weekly_highs, weekly_lows)]) / len(recent_week)
                avg_range_pct = (avg_range / week_start) * 100
                
                return {
                    "weekly_trend": weekly_trend,
                    "weekly_change": weekly_change,
                    "weekly_change_pct": weekly_change_pct,
                    "week_start_price": week_start,
                    "week_end_price": week_end,
                    "avg_daily_range": avg_range,
                    "avg_daily_range_pct": avg_range_pct,
                    "analysis_period": "7_days",
                    "data_points": len(recent_week)
                }
            else:
                return {
                    "error": "Invalid price data",
                    "weekly_trend": "UNKNOWN"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get weekly trend analysis: {e}")
            return {
                "error": str(e),
                "weekly_trend": "UNKNOWN"
            }
    
    def analyze_entry_point(self, prediction_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Analyze entry point for trading decisions"""
        try:
            prediction = prediction_analysis.get("best_prediction", {})
            
            # Check if prediction is valid
            if not prediction.get("has_prediction", False):
                return {
                    "should_enter": False,
                    "reason": "No valid prediction available",
                    "confidence": 0.0
                }
            
            # Check confidence threshold
            confidence = prediction.get("confidence", 0.0)
            if confidence < magic_numbers.DEFAULT_CONFIDENCE:
                return {
                    "should_enter": False,
                    "reason": f"Confidence too low: {confidence:.1%} < {magic_numbers.DEFAULT_CONFIDENCE:.1%}",
                    "confidence": confidence
                }
            
            # Check entry price validation
            entry_price = prediction.get("entry_price", 0)
            if entry_price <= 0:
                return {
                    "should_enter": False,
                    "reason": "Invalid entry price",
                    "confidence": confidence
                }
            
            # Check if current price is near entry price
            price_diff = abs(current_price - entry_price) / current_price
            if price_diff > 0.01:  # More than 1% away from entry
                return {
                    "should_enter": False,
                    "reason": f"Price too far from entry: {price_diff:.1%} difference",
                    "confidence": confidence,
                    "entry_price": entry_price,
                    "current_price": current_price
                }
            
            return {
                "should_enter": True,
                "reason": "Valid entry conditions met",
                "confidence": confidence,
                "entry_price": entry_price,
                "side": prediction.get("side", "UNKNOWN"),
                "target_price": prediction.get("target_price", 0),
                "stop_price": prediction.get("stop_price", 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze entry point: {e}")
            return {
                "should_enter": False,
                "reason": f"Entry analysis failed: {str(e)}",
                "confidence": 0.0
            }
    
    def calculate_prediction_win_probability(self, prediction: Dict[str, Any], prediction_analysis: Dict[str, Any]) -> float:
        """Calculate win probability for a prediction"""
        try:
            # Base probability from confidence
            base_prob = prediction.get("confidence", 0.0)
            
            # Adjust based on market conditions
            market_condition = prediction_analysis.get("market_condition", "UNKNOWN")
            if market_condition == "TRENDING":
                base_prob *= 1.1  # 10% boost in trending markets
            elif market_condition == "CHOPPY":
                base_prob *= 0.9  # 10% reduction in choppy markets
            
            # Adjust based on volatility
            volatility = prediction_analysis.get("volatility_5m", 0.0)
            if volatility > 0.01:  # High volatility
                base_prob *= 0.95  # 5% reduction for high volatility
            elif volatility < 0.002:  # Low volatility
                base_prob *= 1.05  # 5% boost for low volatility
            
            # Cap probability
            return min(base_prob, 0.95)  # Cap at 95%
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate win probability: {e}")
            return 0.5  # Default 50% probability
    
    def get_update_status(self) -> Dict[str, Any]:
        """Get update status for dashboard"""
        try:
            # Get status from yahoo fetcher
            return self.yahoo_fetcher.get_update_status()
        except Exception as e:
            logger.error(f"❌ Failed to get update status: {e}")
            return {
                "last_update": time.time(),
                "status": "ERROR",
                "error": str(e)
            }
    
    def start_session_tracking(self, start_price: float):
        """Start session tracking for analysis"""
        self.session_manager.start_session(start_price)
        logger.info(f"🚀 Session tracking started at ${start_price:.2f}")
    
    def add_session_data_point(self, price: float, volume: float, rsi: float, volatility: float):
        """Add real-time data point to session tracking"""
        self.session_manager.add_data_point(price, volume, rsi, volatility)
    
    def get_session_analysis(self) -> Dict[str, Any]:
        """Get session-specific analysis for predictions"""
        return self.session_manager.get_session_context()
    
    def get_analysis(self, current_price: float, volume: float, rsi: float, volatility: float) -> Dict[str, Any]:
        """Get analysis combining Yahoo and session data"""
        try:
            # Add to session tracking
            self.add_session_data_point(current_price, volume, rsi, volatility)
            
            # Get Yahoo analysis
            yahoo_analysis = self.get_yahoo_analysis(current_price)
            
            # Get session context
            session_context = self.get_session_analysis()
            
            # Build analysis with exact fields prediction engine needs
            analysis = {
                # Core fields required by prediction engine
                "current_price": current_price,
                "rsi": rsi,  # Use the actual RSI value passed in
                "trend": self._get_trend(yahoo_analysis, session_context),
                "volume_category": self._get_volume_category(yahoo_analysis, session_context),
                "volatility_5m": volatility,  # Use the actual volatility value passed in
                
                # Additional context fields
                "session_context": session_context,
                "yahoo_context": {
                    "market_condition": yahoo_analysis.get("market_condition", "NEUTRAL"),
                    "last_update": yahoo_analysis.get("timestamp", 0)
                },
                "analysis_type": "hybrid",
                "data_source": "yahoo_finance + session_tracking",
                "timestamp": time.time()
            }
            
            # Add Yahoo fields if available
            if "error" not in yahoo_analysis:
                analysis.update({
                    "market_condition": yahoo_analysis.get("market_condition", "NEUTRAL"),
                    "sma_5m": yahoo_analysis.get("sma_5m", 0),
                    "sma_20m": yahoo_analysis.get("sma_20m", 0),
                    "volume_analysis": yahoo_analysis.get("volume_analysis", {}),
                    "momentum_analysis": yahoo_analysis.get("momentum_analysis", {})
                })
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get analysis: {e}")
            # Return fallback with required fields
            return {
                "current_price": current_price,
                "rsi": rsi,
                "trend": "NEUTRAL",
                "volume_category": "NORMAL",
                "volatility_5m": volatility,
                "market_condition": "NEUTRAL",
                "analysis_type": "fallback",
                "data_source": "fallback",
                "timestamp": time.time()
            }
    
    def _get_trend(self, yahoo_analysis: Dict[str, Any], session_context: Dict[str, Any]) -> str:
        """Get trend combining Yahoo and session data"""
        try:
            # Use session trend if available and session is mature
            if session_context.get("data_points", 0) >= 20:
                session_trend = session_context.get("session_trend", "NEUTRAL")
                if session_trend != "UNKNOWN":
                    return session_trend
            
            # Fall back to Yahoo trend
            return yahoo_analysis.get("market_condition", "NEUTRAL")
            
        except Exception as e:
            logger.error(f"❌ Failed to get trend: {e}")
            return "NEUTRAL"
    
    def _get_volume_category(self, yahoo_analysis: Dict[str, Any], session_context: Dict[str, Any]) -> str:
        """Get volume category combining Yahoo and session data"""
        try:
            # Use session volume trend if available
            if session_context.get("data_points", 0) >= 10:
                session_volume_trend = session_context.get("session_volume_trend", "STABLE")
                return self._categorize_session_volume(session_volume_trend)
            
            # Fall back to Yahoo volume analysis
            yahoo_volume = yahoo_analysis.get("volume_analysis", {}).get("volume_category", "NORMAL")
            return yahoo_volume
            
        except Exception as e:
            logger.error(f"❌ Failed to get volume category: {e}")
            return "NORMAL"
    
    def _categorize_session_volume(self, volume_trend: str) -> str:
        """Categorize session volume trend into volume category"""
        if volume_trend == "INCREASING":
            return "HIGH"
        elif volume_trend == "DECREASING":
            return "LOW"
        else:
            return "NORMAL"
    
    def end_session_tracking(self):
        """End session tracking"""
        self.session_manager.end_session()
        logger.info("🛑 Session tracking ended")
