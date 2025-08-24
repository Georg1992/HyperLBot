#!/usr/bin/env python3
"""
Ultimate Buy/Sell Pressure Indicator
Combines multiple high-frequency, accurate signals to show real-time market pressure
Updates every 1-2 seconds with professional-grade accuracy
"""

import time
import statistics
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
from loguru import logger
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class UltimatePressureIndicator:
    """
    Ultimate indicator combining 7 different pressure signals:
    1. Enhanced Orderbook Imbalance (multiple levels)
    2. Price Momentum (velocity over 1-5 seconds)
    3. Bid-Ask Spread Analysis (tightening/widening)
    4. Microprice (weighted by orderbook size)
    5. Cumulative Volume Delta (CVD) - buy vs sell accumulation
    6. Depth-Weighted Pressure (proximity-based)
    7. Liquidity Absorption Rate (how fast levels disappear)
    """
    
    def __init__(self):
        # High-frequency price tracking
        self.price_history = deque(maxlen=30)  # Last 30 price updates (~30-60 seconds)
        self.orderbook_history = deque(maxlen=20)  # Last 20 orderbook snapshots
        self.spread_history = deque(maxlen=15)  # Last 15 spread readings
        self.microprice_history = deque(maxlen=25)  # Last 25 microprice readings
        
        # CVD (Cumulative Volume Delta) tracking
        self.cumulative_buy_volume = 0.0
        self.cumulative_sell_volume = 0.0
        self.cvd_history = deque(maxlen=100)  # CVD over time
        
        # Liquidity absorption tracking
        self.previous_orderbook_levels = {}
        
        # Combined pressure score history
        self.pressure_scores = deque(maxlen=50)  # Last 50 pressure readings
        
        logger.info("🎯 Ultimate Pressure Indicator initialized - 7 signal fusion system")
    
    def analyze_ultimate_pressure(self, api) -> Dict[str, Any]:
        """
        Generate ultimate buy/sell pressure reading from multiple signals
        Returns comprehensive pressure analysis with high accuracy
        """
        try:
            # Get current market data with timeout protection
            current_time = time.time()
            
            # Try to get market data with error handling
            try:
                market_data = api.get_market_data("BTC")
                current_price = api.get_current_price("BTC")
            except Exception as e:
                logger.debug(f"Market data API call failed: {e}")
                return {
                    "status": "error", 
                    "error": f"API call failed: {str(e)[:100]}",
                    "direction": "NEUTRAL",
                    "confidence": "0%",
                    "combined_score": 0
                }
            
            if not market_data or not current_price:
                logger.debug("No market data or price available")
                return {
                    "status": "error", 
                    "error": "No market data available",
                    "direction": "NEUTRAL",
                    "confidence": "0%",
                    "combined_score": 0
                }
            
            # Store current data
            self.price_history.append({"price": current_price, "timestamp": current_time})
            
            # Extract orderbook with safer parsing
            try:
                levels = market_data.get('levels', [[], []])
                if len(levels) >= 2:
                    bids = levels[0] if levels[0] else []
                    asks = levels[1] if levels[1] else []
                else:
                    bids, asks = [], []
            except (IndexError, TypeError, KeyError) as e:
                logger.debug(f"Orderbook data parsing failed: {e}")
                return {
                    "status": "error", 
                    "error": "Invalid orderbook format",
                    "direction": "NEUTRAL",
                    "confidence": "0%",
                    "combined_score": 0
                }
            
            if not bids or not asks:
                logger.debug("Empty orderbook data")
                return {
                    "status": "error", 
                    "error": "No orderbook data",
                    "direction": "NEUTRAL", 
                    "confidence": "0%",
                    "combined_score": 0
                }
            
            # 1. ENHANCED ORDERBOOK IMBALANCE (Multiple Levels)
            orderbook_pressure = self._calculate_enhanced_orderbook_imbalance(bids, asks)
            
            # 2. PRICE MOMENTUM (1-5 second velocity)
            momentum_pressure = self._calculate_price_momentum()
            
            # 3. BID-ASK SPREAD ANALYSIS
            spread_pressure = self._calculate_spread_pressure(bids, asks, current_price)
            
            # 4. MICROPRICE (Size-weighted price)
            microprice_pressure = self._calculate_microprice_pressure(bids, asks)
            
            # 5. CUMULATIVE VOLUME DELTA (CVD)
            cvd_pressure = self._calculate_cvd_pressure(bids, asks)
            
            # 6. DEPTH-WEIGHTED PRESSURE (Proximity-based)
            depth_pressure = self._calculate_depth_weighted_pressure(bids, asks, current_price)
            
            # 7. LIQUIDITY ABSORPTION RATE
            absorption_pressure = self._calculate_liquidity_absorption(bids, asks)
            
            # COMBINE ALL SIGNALS INTO ULTIMATE PRESSURE SCORE
            ultimate_score = self._fuse_all_pressure_signals({
                "orderbook": orderbook_pressure,
                "momentum": momentum_pressure,
                "spread": spread_pressure,
                "microprice": microprice_pressure,
                "cvd": cvd_pressure,
                "depth": depth_pressure,
                "absorption": absorption_pressure
            })
            
            # Store for trend analysis
            self.pressure_scores.append({
                "score": ultimate_score["combined_score"],
                "direction": ultimate_score["direction"],
                "timestamp": current_time
            })
            
            # Add trend analysis
            pressure_trend = self._analyze_pressure_trend()
            ultimate_score["trend"] = pressure_trend
            ultimate_score["status"] = "success"
            ultimate_score["timestamp"] = current_time
            
            logger.debug(f"🎯 Ultimate Pressure: {ultimate_score['direction']} ({ultimate_score['combined_score']:.1f}) - {ultimate_score['confidence']}")
            
            return ultimate_score
            
        except Exception as e:
            logger.error(f"❌ Ultimate pressure analysis failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _calculate_enhanced_orderbook_imbalance(self, bids: List, asks: List) -> Dict[str, Any]:
        """Calculate orderbook imbalance across multiple levels with decay"""
        try:
            # Calculate weighted imbalance (closer levels have more weight)
            weights = [1.0, 0.8, 0.6, 0.4, 0.3, 0.2, 0.15, 0.1, 0.08, 0.05]  # Top 10 levels
            
            total_weighted_bid = 0
            total_weighted_ask = 0
            
            for i, weight in enumerate(weights):
                if i < len(bids):
                    bid_size = float(bids[i]['sz'])
                    total_weighted_bid += bid_size * weight
                
                if i < len(asks):
                    ask_size = float(asks[i]['sz'])
                    total_weighted_ask += ask_size * weight
            
            total_weighted = total_weighted_bid + total_weighted_ask
            
            if total_weighted > 0:
                imbalance = (total_weighted_bid - total_weighted_ask) / total_weighted
                
                # Convert to pressure score (-100 to +100)
                pressure_score = imbalance * 100
                
                # Determine strength
                if abs(pressure_score) > 60:
                    strength = "EXTREME"
                elif abs(pressure_score) > 40:
                    strength = "STRONG"
                elif abs(pressure_score) > 20:
                    strength = "MODERATE"
                elif abs(pressure_score) > 10:
                    strength = "WEAK"
                else:
                    strength = "NEUTRAL"
                
                return {
                    "pressure_score": pressure_score,
                    "strength": strength,
                    "bid_depth": total_weighted_bid,
                    "ask_depth": total_weighted_ask,
                    "signal_quality": "HIGH"
                }
            else:
                return {"pressure_score": 0, "strength": "NEUTRAL", "signal_quality": "LOW"}
                
        except Exception as e:
            logger.debug(f"Orderbook imbalance calculation error: {e}")
            return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
    
    def _calculate_price_momentum(self) -> Dict[str, Any]:
        """Calculate price momentum over multiple timeframes"""
        try:
            if len(self.price_history) < 5:
                return {"pressure_score": 0, "strength": "INSUFFICIENT_DATA", "signal_quality": "LOW"}
            
            prices = [p["price"] for p in self.price_history]
            times = [p["timestamp"] for p in self.price_history]
            
            # Calculate momentum over different timeframes
            momentum_1s = self._calculate_momentum_timeframe(prices, times, 1)   # 1 second
            momentum_5s = self._calculate_momentum_timeframe(prices, times, 5)   # 5 seconds
            momentum_15s = self._calculate_momentum_timeframe(prices, times, 15) # 15 seconds
            
            # Weight shorter timeframes more heavily for immediate pressure
            combined_momentum = (momentum_1s * 0.5) + (momentum_5s * 0.3) + (momentum_15s * 0.2)
            
            # Convert to pressure score
            pressure_score = combined_momentum * 1000  # Amplify for visibility
            pressure_score = max(-100, min(100, pressure_score))  # Clamp to range
            
            # Determine strength
            if abs(pressure_score) > 50:
                strength = "STRONG"
            elif abs(pressure_score) > 25:
                strength = "MODERATE" 
            elif abs(pressure_score) > 10:
                strength = "WEAK"
            else:
                strength = "NEUTRAL"
            
            return {
                "pressure_score": pressure_score,
                "strength": strength,
                "momentum_1s": momentum_1s,
                "momentum_5s": momentum_5s,
                "momentum_15s": momentum_15s,
                "signal_quality": "HIGH"
            }
            
        except Exception as e:
            logger.debug(f"Price momentum calculation error: {e}")
            return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
    
    def _calculate_momentum_timeframe(self, prices: List[float], times: List[float], timeframe_seconds: int) -> float:
        """Calculate momentum over specific timeframe"""
        try:
            current_time = times[-1]
            target_time = current_time - timeframe_seconds
            
            # Find prices within timeframe
            timeframe_data = [(p, t) for p, t in zip(prices, times) if t >= target_time]
            
            if len(timeframe_data) < 2:
                return 0.0
            
            # Calculate price change rate
            start_price = timeframe_data[0][0]
            end_price = timeframe_data[-1][0]
            time_diff = timeframe_data[-1][1] - timeframe_data[0][1]
            
            if time_diff > 0 and start_price > 0:
                momentum = (end_price - start_price) / start_price / time_diff
                return momentum
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    def _calculate_spread_pressure(self, bids: List, asks: List, current_price: float) -> Dict[str, Any]:
        """Analyze bid-ask spread for pressure signals"""
        try:
            if not bids or not asks:
                return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
            
            best_bid = float(bids[0]['px'])
            best_ask = float(asks[0]['px'])
            spread = best_ask - best_bid
            spread_pct = (spread / current_price) * 100 if current_price > 0 else 0
            
            # Store spread history
            self.spread_history.append({
                "spread": spread,
                "spread_pct": spread_pct,
                "timestamp": time.time()
            })
            
            # Analyze spread trend
            if len(self.spread_history) >= 5:
                recent_spreads = [s["spread_pct"] for s in list(self.spread_history)[-5:]]
                spread_trend = recent_spreads[-1] - recent_spreads[0]
                
                # Tightening spread = increasing pressure, widening = decreasing pressure
                pressure_score = -spread_trend * 50  # Invert and amplify
                pressure_score = max(-100, min(100, pressure_score))
                
                if abs(pressure_score) > 40:
                    strength = "STRONG"
                elif abs(pressure_score) > 20:
                    strength = "MODERATE"
                elif abs(pressure_score) > 10:
                    strength = "WEAK"
                else:
                    strength = "NEUTRAL"
                
                return {
                    "pressure_score": pressure_score,
                    "strength": strength,
                    "spread_pct": spread_pct,
                    "spread_trend": spread_trend,
                    "signal_quality": "HIGH"
                }
            else:
                return {"pressure_score": 0, "strength": "INSUFFICIENT_DATA", "signal_quality": "LOW"}
                
        except Exception as e:
            logger.debug(f"Spread pressure calculation error: {e}")
            return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
    
    def _calculate_microprice_pressure(self, bids: List, asks: List) -> Dict[str, Any]:
        """Calculate microprice (size-weighted price) pressure"""
        try:
            if not bids or not asks:
                return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
            
            # Calculate microprice (weighted by top level sizes)
            best_bid_price = float(bids[0]['px'])
            best_ask_price = float(asks[0]['px'])
            best_bid_size = float(bids[0]['sz'])
            best_ask_size = float(asks[0]['sz'])
            
            total_size = best_bid_size + best_ask_size
            
            if total_size > 0:
                microprice = (best_bid_price * best_ask_size + best_ask_price * best_bid_size) / total_size
                mid_price = (best_bid_price + best_ask_price) / 2
                
                # Store microprice history
                self.microprice_history.append({
                    "microprice": microprice,
                    "mid_price": mid_price,
                    "timestamp": time.time()
                })
                
                # Analyze microprice vs mid_price bias
                price_bias = (microprice - mid_price) / mid_price if mid_price > 0 else 0
                
                # Microprice above mid = buy pressure, below = sell pressure
                pressure_score = price_bias * 10000  # Amplify the signal
                pressure_score = max(-100, min(100, pressure_score))
                
                if abs(pressure_score) > 30:
                    strength = "STRONG"
                elif abs(pressure_score) > 15:
                    strength = "MODERATE"
                elif abs(pressure_score) > 5:
                    strength = "WEAK"
                else:
                    strength = "NEUTRAL"
                
                return {
                    "pressure_score": pressure_score,
                    "strength": strength,
                    "microprice": microprice,
                    "mid_price": mid_price,
                    "price_bias": price_bias,
                    "signal_quality": "HIGH"
                }
            else:
                return {"pressure_score": 0, "strength": "NEUTRAL", "signal_quality": "LOW"}
                
        except Exception as e:
            logger.debug(f"Microprice calculation error: {e}")
            return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
    
    def _calculate_cvd_pressure(self, bids: List, asks: List) -> Dict[str, Any]:
        """Calculate Cumulative Volume Delta pressure"""
        try:
            # Estimate buy/sell volume from orderbook changes
            # (This is a simplified approach - ideally we'd use actual trade data)
            
            current_bid_volume = sum(float(level['sz']) for level in bids[:5])
            current_ask_volume = sum(float(level['sz']) for level in asks[:5])
            
            # Update cumulative volumes (simplified estimation)
            volume_imbalance = current_bid_volume - current_ask_volume
            
            # Add to cumulative delta
            if volume_imbalance > 0:
                self.cumulative_buy_volume += abs(volume_imbalance) * 0.1  # Scale factor
            else:
                self.cumulative_sell_volume += abs(volume_imbalance) * 0.1
            
            # Calculate CVD
            total_volume = self.cumulative_buy_volume + self.cumulative_sell_volume
            
            if total_volume > 0:
                cvd_ratio = (self.cumulative_buy_volume - self.cumulative_sell_volume) / total_volume
                pressure_score = cvd_ratio * 100
                
                # Store CVD history
                self.cvd_history.append({
                    "cvd_ratio": cvd_ratio,
                    "buy_volume": self.cumulative_buy_volume,
                    "sell_volume": self.cumulative_sell_volume,
                    "timestamp": time.time()
                })
                
                if abs(pressure_score) > 40:
                    strength = "STRONG"
                elif abs(pressure_score) > 20:
                    strength = "MODERATE"
                elif abs(pressure_score) > 10:
                    strength = "WEAK"
                else:
                    strength = "NEUTRAL"
                
                return {
                    "pressure_score": pressure_score,
                    "strength": strength,
                    "cvd_ratio": cvd_ratio,
                    "buy_volume": self.cumulative_buy_volume,
                    "sell_volume": self.cumulative_sell_volume,
                    "signal_quality": "MEDIUM"  # Estimated data
                }
            else:
                return {"pressure_score": 0, "strength": "NEUTRAL", "signal_quality": "LOW"}
                
        except Exception as e:
            logger.debug(f"CVD calculation error: {e}")
            return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
    
    def _calculate_depth_weighted_pressure(self, bids: List, asks: List, current_price: float) -> Dict[str, Any]:
        """Calculate pressure weighted by proximity to current price"""
        try:
            if not bids or not asks or current_price <= 0:
                return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
            
            weighted_bid_pressure = 0
            weighted_ask_pressure = 0
            
            # Weight levels by their proximity to current price
            for i, bid in enumerate(bids[:10]):
                bid_price = float(bid['px'])
                bid_size = float(bid['sz'])
                distance_from_price = abs(current_price - bid_price) / current_price
                weight = 1 / (1 + distance_from_price * 10)  # Closer = higher weight
                weighted_bid_pressure += bid_size * weight
            
            for i, ask in enumerate(asks[:10]):
                ask_price = float(ask['px'])
                ask_size = float(ask['sz'])
                distance_from_price = abs(ask_price - current_price) / current_price
                weight = 1 / (1 + distance_from_price * 10)  # Closer = higher weight
                weighted_ask_pressure += ask_size * weight
            
            total_weighted = weighted_bid_pressure + weighted_ask_pressure
            
            if total_weighted > 0:
                pressure_ratio = (weighted_bid_pressure - weighted_ask_pressure) / total_weighted
                pressure_score = pressure_ratio * 100
                
                if abs(pressure_score) > 50:
                    strength = "STRONG"
                elif abs(pressure_score) > 25:
                    strength = "MODERATE"
                elif abs(pressure_score) > 10:
                    strength = "WEAK"
                else:
                    strength = "NEUTRAL"
                
                return {
                    "pressure_score": pressure_score,
                    "strength": strength,
                    "weighted_bid": weighted_bid_pressure,
                    "weighted_ask": weighted_ask_pressure,
                    "signal_quality": "HIGH"
                }
            else:
                return {"pressure_score": 0, "strength": "NEUTRAL", "signal_quality": "LOW"}
                
        except Exception as e:
            logger.debug(f"Depth-weighted pressure calculation error: {e}")
            return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
    
    def _calculate_liquidity_absorption(self, bids: List, asks: List) -> Dict[str, Any]:
        """Calculate how fast liquidity is being absorbed"""
        try:
            # Compare current orderbook with previous
            current_orderbook = {
                "bids": [(float(b['px']), float(b['sz'])) for b in bids[:5]],
                "asks": [(float(a['px']), float(a['sz'])) for a in asks[:5]]
            }
            
            self.orderbook_history.append({
                "orderbook": current_orderbook,
                "timestamp": time.time()
            })
            
            if len(self.orderbook_history) < 2:
                return {"pressure_score": 0, "strength": "INSUFFICIENT_DATA", "signal_quality": "LOW"}
            
            # Calculate liquidity change
            prev_orderbook = self.orderbook_history[-2]["orderbook"]
            
            # Measure size changes at similar price levels
            bid_absorption = self._measure_level_absorption(
                prev_orderbook["bids"], current_orderbook["bids"]
            )
            ask_absorption = self._measure_level_absorption(
                prev_orderbook["asks"], current_orderbook["asks"]
            )
            
            # Higher bid absorption = buy pressure, higher ask absorption = sell pressure
            net_absorption = bid_absorption - ask_absorption
            pressure_score = net_absorption * 50  # Amplify signal
            pressure_score = max(-100, min(100, pressure_score))
            
            if abs(pressure_score) > 30:
                strength = "STRONG"
            elif abs(pressure_score) > 15:
                strength = "MODERATE"
            elif abs(pressure_score) > 5:
                strength = "WEAK"
            else:
                strength = "NEUTRAL"
            
            return {
                "pressure_score": pressure_score,
                "strength": strength,
                "bid_absorption": bid_absorption,
                "ask_absorption": ask_absorption,
                "signal_quality": "HIGH"
            }
            
        except Exception as e:
            logger.debug(f"Liquidity absorption calculation error: {e}")
            return {"pressure_score": 0, "strength": "ERROR", "signal_quality": "ERROR"}
    
    def _measure_level_absorption(self, prev_levels: List[Tuple], curr_levels: List[Tuple]) -> float:
        """Measure how much size was absorbed at similar price levels"""
        try:
            absorption = 0.0
            
            for prev_price, prev_size in prev_levels:
                # Find similar price level in current orderbook
                for curr_price, curr_size in curr_levels:
                    if abs(curr_price - prev_price) / prev_price < 0.001:  # Within 0.1%
                        size_change = prev_size - curr_size
                        if size_change > 0:  # Size decreased = absorption
                            absorption += size_change
                        break
            
            return absorption
            
        except Exception:
            return 0.0
    
    def _fuse_all_pressure_signals(self, signals: Dict[str, Dict]) -> Dict[str, Any]:
        """Fuse all 7 pressure signals into ultimate score"""
        try:
            # Weight each signal based on reliability and importance
            weights = {
                "orderbook": 0.25,    # Highest weight - most reliable
                "momentum": 0.20,     # High weight - immediate signal
                "microprice": 0.15,   # Medium weight - sophisticated signal
                "depth": 0.15,        # Medium weight - proximity matters
                "absorption": 0.10,   # Medium weight - liquidity flow
                "spread": 0.10,       # Lower weight - supporting signal
                "cvd": 0.05          # Lowest weight - estimated data
            }
            
            total_score = 0.0
            total_weight = 0.0
            signal_details = {}
            confidence_factors = []
            
            for signal_name, weight in weights.items():
                signal_data = signals.get(signal_name, {})
                pressure_score = signal_data.get("pressure_score", 0)
                signal_quality = signal_data.get("signal_quality", "LOW")
                
                # Adjust weight based on signal quality
                quality_multiplier = {
                    "HIGH": 1.0,
                    "MEDIUM": 0.7,
                    "LOW": 0.3,
                    "ERROR": 0.0
                }.get(signal_quality, 0.0)
                
                effective_weight = weight * quality_multiplier
                total_score += pressure_score * effective_weight
                total_weight += effective_weight
                
                signal_details[signal_name] = {
                    "score": pressure_score,
                    "strength": signal_data.get("strength", "UNKNOWN"),
                    "weight": effective_weight,
                    "quality": signal_quality
                }
                
                if quality_multiplier > 0:
                    confidence_factors.append(quality_multiplier)
            
            # Calculate final combined score
            combined_score = total_score / total_weight if total_weight > 0 else 0
            
            # Determine direction and confidence
            if combined_score > 15:
                direction = "STRONG_BUY"
                direction_emoji = "🟢"
            elif combined_score > 5:
                direction = "BUY"
                direction_emoji = "🔵"
            elif combined_score < -15:
                direction = "STRONG_SELL"
                direction_emoji = "🔴"
            elif combined_score < -5:
                direction = "SELL"
                direction_emoji = "🟠"
            else:
                direction = "NEUTRAL"
                direction_emoji = "⚪"
            
            # Calculate confidence
            avg_quality = statistics.mean(confidence_factors) if confidence_factors else 0
            confidence = f"{avg_quality * 100:.0f}%"
            
            return {
                "combined_score": combined_score,
                "direction": direction,
                "direction_emoji": direction_emoji,
                "confidence": confidence,
                "signal_details": signal_details,
                "total_weight": total_weight,
                "active_signals": len([s for s in signal_details.values() if s["quality"] != "ERROR"])
            }
            
        except Exception as e:
            logger.error(f"Signal fusion error: {e}")
            return {
                "combined_score": 0,
                "direction": "ERROR",
                "direction_emoji": "❌",
                "confidence": "0%",
                "error": str(e)
            }
    
    def _analyze_pressure_trend(self) -> Dict[str, Any]:
        """Analyze pressure trend over recent history"""
        try:
            if len(self.pressure_scores) < 5:
                return {"trend": "INSUFFICIENT_DATA", "trend_strength": 0}
            
            recent_scores = [p["score"] for p in list(self.pressure_scores)[-10:]]
            
            # Calculate trend
            if len(recent_scores) >= 5:
                early_avg = statistics.mean(recent_scores[:5])
                late_avg = statistics.mean(recent_scores[-5:])
                
                trend_change = late_avg - early_avg
                
                if trend_change > 10:
                    trend = "STRENGTHENING"
                elif trend_change < -10:
                    trend = "WEAKENING"
                elif abs(trend_change) < 3:
                    trend = "STABLE"
                else:
                    trend = "FLUCTUATING"
                
                return {
                    "trend": trend,
                    "trend_strength": abs(trend_change),
                    "trend_change": trend_change,
                    "readings_count": len(self.pressure_scores)
                }
            else:
                return {"trend": "INSUFFICIENT_DATA", "trend_strength": 0}
                
        except Exception as e:
            logger.debug(f"Pressure trend analysis error: {e}")
            return {"trend": "ERROR", "trend_strength": 0}
    
    def get_summary_display(self, pressure_data: Dict[str, Any]) -> str:
        """Get a beautiful summary display for the pressure indicator"""
        if pressure_data.get("status") != "success":
            return "❌ Pressure analysis unavailable"
        
        emoji = pressure_data.get("direction_emoji", "⚪")
        direction = pressure_data.get("direction", "UNKNOWN")
        score = pressure_data.get("combined_score", 0)
        confidence = pressure_data.get("confidence", "0%")
        trend = pressure_data.get("trend", {}).get("trend", "UNKNOWN")
        active_signals = pressure_data.get("active_signals", 0)
        
        return f"{emoji} {direction} ({score:+.1f}) | Confidence: {confidence} | Trend: {trend} | Signals: {active_signals}/7"


# Test the Ultimate Pressure Indicator
if __name__ == "__main__":
    logger.info("🎯 Testing Ultimate Pressure Indicator")
    
    # Import HyperliquidAPI for testing
    from core.hyperliquid_api import HyperliquidAPI
    
    try:
        api = HyperliquidAPI()
        indicator = UltimatePressureIndicator()
        
        logger.info("📊 Running pressure analysis tests...")
        
        for i in range(3):
            logger.info(f"\n🎯 Pressure Test {i+1}/3:")
            
            pressure_data = indicator.analyze_ultimate_pressure(api)
            
            if pressure_data.get("status") == "success":
                summary = indicator.get_summary_display(pressure_data)
                logger.success(f"   {summary}")
                
                # Show detailed breakdown
                logger.info(f"   Combined Score: {pressure_data['combined_score']:.1f}")
                logger.info(f"   Active Signals: {pressure_data['active_signals']}/7")
                
                # Show individual signal strengths
                signal_details = pressure_data.get("signal_details", {})
                for signal_name, details in signal_details.items():
                    if details["quality"] != "ERROR":
                        logger.info(f"     {signal_name.title()}: {details['score']:.1f} ({details['strength']})")
            else:
                logger.error(f"   Error: {pressure_data.get('error', 'Unknown error')}")
            
            if i < 2:  # Don't sleep on last iteration
                time.sleep(3)
        
        logger.success("🎉 Ultimate Pressure Indicator test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")