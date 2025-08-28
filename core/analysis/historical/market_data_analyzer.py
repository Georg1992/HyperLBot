#!/usr/bin/env python3
"""
Market Data Analyzer Module
Handles market data analysis and RSI calculations
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger
from core.constants import magic_numbers
from data.yahoo_data_fetcher import YahooDataFetcher

class MarketDataAnalyzer:
    """Handles market data analysis and RSI calculations"""
    
    def __init__(self):
        self.yahoo_fetcher = YahooDataFetcher()
        logger.info("📊 Market Data Analyzer initialized")
    
    def get_optimized_rsi_data(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get historical RSI data from Yahoo Finance candles (not real-time)"""
        try:
            # Calculate RSI from Yahoo Finance historical data (proper historical analysis)
            candles_5m = self.get_5m_candles("BTC", 50)  # Get enough data for RSI calculation
            
            if not candles_5m or len(candles_5m) < 15:
                logger.warning("⚠️ Insufficient Yahoo candle data for RSI calculation")
                return self._get_default_rsi_data(hyperliquid_price, "insufficient_data")
            
            # Calculate RSI from Yahoo closing prices
            rsi_data = self._calculate_historical_rsi(candles_5m)
            
            # Transform the data structure to match what the bot expects
            transformed_data = {
                "rsi_value": rsi_data.get("rsi"),  # Historical Yahoo RSI
                "trend": rsi_data.get("trend", "NEUTRAL"),
                "advanced_signal": rsi_data.get("signal", "NEUTRAL"),
                "momentum": "NEUTRAL",  # Default momentum
                "confidence": 0.5,  # Default confidence
                "hyperliquid_price": hyperliquid_price,
                "price_context": "yahoo_historical"  # Always historical for this analyzer
            }
            
            # Calculate confidence based on RSI value
            rsi_value = rsi_data.get("rsi")
            if rsi_value is not None:
                if rsi_value < 30 or rsi_value > 70:
                    transformed_data["confidence"] = 0.8  # High confidence for extreme values
                elif rsi_value < 40 or rsi_value > 60:
                    transformed_data["confidence"] = 0.6  # Medium confidence for moderate values
                else:
                    transformed_data["confidence"] = 0.4  # Low confidence for neutral values
                
                # Determine momentum based on RSI trend
                if rsi_value > 70:
                    transformed_data["momentum"] = "OVERBOUGHT"
                elif rsi_value < 30:
                    transformed_data["momentum"] = "OVERSOLD"
                elif rsi_value > 60:
                    transformed_data["momentum"] = "BULLISH"
                elif rsi_value < 40:
                    transformed_data["momentum"] = "BEARISH"
                else:
                    transformed_data["momentum"] = "NEUTRAL"
            
            return transformed_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get optimized RSI data: {e}")
            return {
                "rsi_value": 50.0,  # Default RSI value
                "trend": "NEUTRAL",
                "advanced_signal": "NEUTRAL",
                "momentum": "NEUTRAL",
                "confidence": 0.5,
                "hyperliquid_price": hyperliquid_price,
                "price_context": "error",
                "error": str(e)
            }
    
    def get_yahoo_analysis(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get comprehensive Yahoo Finance market analysis"""
        try:
            # Get market analysis from Yahoo fetcher
            analysis = self.yahoo_fetcher.get_optimized_market_analysis("BTC", hyperliquid_price)
            
            # Add Hyperliquid price context
            if hyperliquid_price and hyperliquid_price > 0:
                analysis["hyperliquid_price"] = hyperliquid_price
                analysis["price_context"] = "hyperliquid_real_time"
                
                # Calculate price difference
                yahoo_price = analysis.get("current_price", 0)
                if yahoo_price > 0:
                    price_diff = abs(hyperliquid_price - yahoo_price)
                    price_diff_pct = (price_diff / yahoo_price) * 100
                    analysis["price_difference"] = {
                        "absolute": price_diff,
                        "percentage": price_diff_pct,
                        "yahoo_price": yahoo_price,
                        "hyperliquid_price": hyperliquid_price
                    }
            else:
                analysis["price_context"] = "yahoo_historical"
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo analysis: {e}")
            return {
                "error": str(e),
                "price_context": "error",
                "hyperliquid_price": hyperliquid_price
            }
    
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
