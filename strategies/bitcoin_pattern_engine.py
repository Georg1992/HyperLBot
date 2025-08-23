#!/usr/bin/env python3
"""
Bitcoin-Specific Pattern Recognition Engine
Specialized patterns that work uniquely well for Bitcoin trading
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class PatternSignal:
    """Bitcoin pattern signal with confidence and timing"""
    pattern_name: str
    signal_type: str  # BUY, SELL, HOLD
    confidence: float
    timeframe: str
    reason: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: float = 0.15

class BitcoinPatternEngine:
    """Advanced Bitcoin-specific pattern recognition for maximum profitability"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        
        # Bitcoin-specific pattern library
        self.btc_patterns = {
            # Price action patterns
            "btc_whale_accumulation": self._detect_whale_accumulation,
            "btc_retail_panic": self._detect_retail_panic,
            "btc_institutional_entry": self._detect_institutional_entry,
            "btc_weekend_dip": self._detect_weekend_dip,
            "btc_asia_pump": self._detect_asia_pump,
            "btc_us_session_reversal": self._detect_us_session_reversal,
            
            # Volume-based patterns
            "btc_low_volume_breakout": self._detect_low_volume_breakout,
            "btc_high_volume_exhaustion": self._detect_high_volume_exhaustion,
            "btc_accumulation_phase": self._detect_accumulation_phase,
            "btc_distribution_phase": self._detect_distribution_phase,
            
            # Volatility patterns
            "btc_volatility_compression": self._detect_volatility_compression,
            "btc_volatility_expansion": self._detect_volatility_expansion,
            "btc_squeeze_breakout": self._detect_squeeze_breakout,
            
            # Psychological levels
            "btc_round_number_rejection": self._detect_round_number_rejection,
            "btc_fibonacci_bounce": self._detect_fibonacci_bounce,
            "btc_previous_ath_test": self._detect_ath_test,
            
            # Market structure patterns
            "btc_higher_lows": self._detect_higher_lows,
            "btc_lower_highs": self._detect_lower_highs,
            "btc_range_bound": self._detect_range_bound,
            "btc_trend_continuation": self._detect_trend_continuation,
            
            # News-driven patterns
            "btc_pre_news_positioning": self._detect_pre_news_positioning,
            "btc_post_news_reversion": self._detect_post_news_reversion,
            
            # Bitcoin-specific behaviors
            "btc_halving_cycle": self._detect_halving_cycle_pattern,
            "btc_mining_difficulty": self._detect_mining_difficulty_pattern,
            "btc_fear_greed_extreme": self._detect_fear_greed_extreme,
            "btc_on_chain_divergence": self._detect_on_chain_divergence
        }
        
        # Pattern confidence weights (based on historical BTC performance)
        self.pattern_weights = {
            "btc_whale_accumulation": 0.9,
            "btc_institutional_entry": 0.85,
            "btc_volatility_compression": 0.8,
            "btc_fibonacci_bounce": 0.75,
            "btc_weekend_dip": 0.7,
            "btc_squeeze_breakout": 0.9,
            "btc_higher_lows": 0.8,
            "btc_halving_cycle": 0.95,
            "btc_fear_greed_extreme": 0.85
        }
        
        # Historical price tracking for pattern recognition
        self.price_history = deque(maxlen=1000)
        self.volume_history = deque(maxlen=1000) 
        self.volatility_history = deque(maxlen=200)
        
        # Bitcoin-specific levels
        self.psychological_levels = [
            100000, 110000, 115000, 120000, 125000, 130000, 140000, 150000,
            200000, 250000, 300000, 500000, 1000000  # Future levels
        ]
        
        logger.info("🧠 Bitcoin-Specific Pattern Engine initialized")
    
    def analyze_bitcoin_patterns(self, market_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Comprehensive Bitcoin pattern analysis"""
        try:
            # Update historical data
            self._update_history(market_data, current_price)
            
            # Detect all Bitcoin-specific patterns
            detected_patterns = []
            pattern_signals = []
            
            for pattern_name, pattern_func in self.btc_patterns.items():
                try:
                    pattern_result = pattern_func(market_data, current_price)
                    if pattern_result and pattern_result.confidence > 0.3:
                        detected_patterns.append(pattern_name)
                        pattern_signals.append(pattern_result)
                        logger.info(f"🎯 Bitcoin Pattern: {pattern_name} - {pattern_result.signal_type} ({pattern_result.confidence:.1%})")
                except Exception as e:
                    logger.debug(f"Pattern detection error for {pattern_name}: {e}")
            
            # Combine patterns into unified signal
            combined_signal = self._combine_bitcoin_patterns(pattern_signals, current_price)
            
            return {
                "detected_patterns": detected_patterns,
                "pattern_signals": [vars(p) for p in pattern_signals],
                "combined_signal": combined_signal,
                "pattern_count": len(detected_patterns),
                "max_confidence": max([p.confidence for p in pattern_signals], default=0),
                "bullish_patterns": len([p for p in pattern_signals if p.signal_type == "BUY"]),
                "bearish_patterns": len([p for p in pattern_signals if p.signal_type == "SELL"])
            }
            
        except Exception as e:
            logger.error(f"Bitcoin pattern analysis error: {e}")
            return {"detected_patterns": [], "pattern_signals": [], "combined_signal": None}
    
    def _update_history(self, market_data: Dict[str, Any], current_price: float):
        """Update historical data for pattern recognition"""
        timestamp = time.time()
        
        self.price_history.append({
            "timestamp": timestamp,
            "price": current_price,
            "hour": datetime.now().hour,
            "weekday": datetime.now().weekday()
        })
        
        volume = market_data.get("volume", 0)
        self.volume_history.append({
            "timestamp": timestamp,
            "volume": volume,
            "price": current_price
        })
        
        volatility = market_data.get("volatility_5m", 0.002)
        self.volatility_history.append({
            "timestamp": timestamp,
            "volatility": volatility
        })
    
    # ========== BITCOIN-SPECIFIC PATTERN IMPLEMENTATIONS ==========
    
    def _detect_whale_accumulation(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect whale accumulation pattern - BTC bought in large volumes at support"""
        candles = market_data.get("candles_5m", [])
        if len(candles) < 20:
            return None
        
        recent_candles = candles[-20:]
        volumes = [c["volume"] for c in recent_candles]
        closes = [c["close"] for c in recent_candles]
        
        # High volume + price holding steady/rising = accumulation
        avg_volume = np.mean(volumes)
        recent_volume = np.mean(volumes[-5:])
        volume_surge = recent_volume > avg_volume * 1.5
        
        # Price consolidation
        price_stability = np.std(closes[-10:]) / np.mean(closes[-10:]) < 0.01
        
        # Recent buying pressure (more green candles)
        green_candles = sum(1 for c in recent_candles[-10:] if c["close"] > c["open"])
        buying_pressure = green_candles >= 6
        
        if volume_surge and price_stability and buying_pressure:
            return PatternSignal(
                pattern_name="btc_whale_accumulation",
                signal_type="BUY",
                confidence=0.8,
                timeframe="5m",
                reason="High volume accumulation at current levels - whale buying detected",
                target_price=current_price * 1.03,
                stop_loss=current_price * 0.985,
                position_size=0.25
            )
        return None
    
    def _detect_retail_panic(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect retail panic selling - opportunity for contrarian entry"""
        candles = market_data.get("candles_5m", [])
        if len(candles) < 15:
            return None
        
        recent_candles = candles[-15:]
        
        # Sharp price drop with high volume
        price_drop = (recent_candles[-1]["close"] - recent_candles[-10]["close"]) / recent_candles[-10]["close"]
        volume_spike = recent_candles[-1]["volume"] > np.mean([c["volume"] for c in recent_candles[:-1]]) * 2
        
        # Multiple red candles in a row
        red_streak = 0
        for candle in reversed(recent_candles[-8:]):
            if candle["close"] < candle["open"]:
                red_streak += 1
            else:
                break
        
        if price_drop < -0.02 and volume_spike and red_streak >= 4:
            return PatternSignal(
                pattern_name="btc_retail_panic",
                signal_type="BUY",
                confidence=0.75,
                timeframe="5m",
                reason="Retail panic selling - contrarian buy opportunity",
                target_price=current_price * 1.025,
                stop_loss=current_price * 0.97,
                position_size=0.3
            )
        return None
    
    def _detect_institutional_entry(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect institutional buying patterns - steady accumulation"""
        candles = market_data.get("candles_5m", [])
        if len(candles) < 30:
            return None
        
        recent_candles = candles[-30:]
        volumes = [c["volume"] for c in recent_candles]
        closes = [c["close"] for c in recent_candles]
        
        # Consistent volume above average
        avg_volume = np.mean(volumes)
        consistent_volume = sum(1 for v in volumes[-15:] if v > avg_volume * 0.8) >= 10
        
        # Gradual price increase (not parabolic)
        price_trend = np.polyfit(range(len(closes)), closes, 1)[0]
        gradual_rise = 0 < price_trend < current_price * 0.001  # Steady but not explosive
        
        # Low volatility during accumulation
        volatility = np.std(closes[-15:]) / np.mean(closes[-15:])
        low_volatility = volatility < 0.015
        
        if consistent_volume and gradual_rise and low_volatility:
            return PatternSignal(
                pattern_name="btc_institutional_entry",
                signal_type="BUY",
                confidence=0.85,
                timeframe="5m",
                reason="Institutional accumulation pattern - smart money entry",
                target_price=current_price * 1.04,
                stop_loss=current_price * 0.98,
                position_size=0.35
            )
        return None
    
    def _detect_weekend_dip(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect Bitcoin weekend dip pattern - traditional weakness on weekends"""
        current_time = datetime.now()
        
        # Check if it's weekend (Saturday or Sunday)
        is_weekend = current_time.weekday() >= 5
        if not is_weekend:
            return None
        
        candles = market_data.get("candles_1h", [])
        if len(candles) < 24:
            return None
        
        # Check for price weakness during weekend
        last_24h = candles[-24:]
        price_change = (last_24h[-1]["close"] - last_24h[0]["close"]) / last_24h[0]["close"]
        
        # Lower volume during weekend
        volumes = [c["volume"] for c in last_24h]
        avg_volume = np.mean(volumes)
        recent_volume = np.mean(volumes[-6:])  # Last 6 hours
        low_volume = recent_volume < avg_volume * 0.7
        
        if price_change < -0.01 and low_volume:
            return PatternSignal(
                pattern_name="btc_weekend_dip",
                signal_type="BUY",
                confidence=0.7,
                timeframe="1h",
                reason="Traditional weekend weakness - buy the dip",
                target_price=current_price * 1.02,
                stop_loss=current_price * 0.985,
                position_size=0.2
            )
        return None
    
    def _detect_volatility_compression(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect volatility compression before major move"""
        if len(self.volatility_history) < 50:
            return None
        
        recent_volatility = [v["volatility"] for v in list(self.volatility_history)[-20:]]
        historical_volatility = [v["volatility"] for v in list(self.volatility_history)[-50:-20]]
        
        current_vol = np.mean(recent_volatility)
        historical_vol = np.mean(historical_volatility)
        
        # Volatility compression (current much lower than historical)
        compression_ratio = current_vol / historical_vol
        
        candles = market_data.get("candles_5m", [])
        if len(candles) >= 20:
            # Price range tightening
            recent_ranges = [(c["high"] - c["low"]) / c["close"] for c in candles[-10:]]
            avg_range = np.mean(recent_ranges)
            range_compression = avg_range < 0.005  # Very tight ranges
        else:
            range_compression = False
        
        if compression_ratio < 0.6 and range_compression:
            return PatternSignal(
                pattern_name="btc_volatility_compression",
                signal_type="HOLD",  # Wait for direction
                confidence=0.8,
                timeframe="5m",
                reason="Volatility compression - major move incoming",
                position_size=0.4  # Large position when direction confirms
            )
        return None
    
    def _detect_squeeze_breakout(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect breakout from volatility squeeze"""
        candles = market_data.get("candles_5m", [])
        if len(candles) < 30:
            return None
        
        recent_candles = candles[-30:]
        
        # Calculate Bollinger Band squeeze
        closes = [c["close"] for c in recent_candles]
        sma_20 = np.mean(closes[-20:])
        std_20 = np.std(closes[-20:])
        
        upper_bb = sma_20 + (2 * std_20)
        lower_bb = sma_20 - (2 * std_20)
        bb_width = (upper_bb - lower_bb) / sma_20
        
        # Keltner Channel
        high_low_range = np.mean([(c["high"] - c["low"]) for c in recent_candles[-20:]])
        upper_kc = sma_20 + (2 * high_low_range)
        lower_kc = sma_20 - (2 * high_low_range)
        
        # Squeeze condition: BB inside KC
        squeeze = upper_bb < upper_kc and lower_bb > lower_kc
        
        # Breakout condition
        recent_price_move = abs(current_price - sma_20) / sma_20
        volume_confirmation = recent_candles[-1]["volume"] > np.mean([c["volume"] for c in recent_candles[:-1]]) * 1.3
        
        if squeeze and recent_price_move > 0.008 and volume_confirmation:
            signal_type = "BUY" if current_price > sma_20 else "SELL"
            return PatternSignal(
                pattern_name="btc_squeeze_breakout",
                signal_type=signal_type,
                confidence=0.9,
                timeframe="5m",
                reason="Breakout from volatility squeeze with volume",
                target_price=current_price * (1.03 if signal_type == "BUY" else 0.97),
                stop_loss=current_price * (0.985 if signal_type == "BUY" else 1.015),
                position_size=0.4
            )
        return None
    
    def _detect_round_number_rejection(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect rejection at psychological round numbers"""
        # Find nearest psychological level
        nearest_level = min(self.psychological_levels, key=lambda x: abs(x - current_price))
        distance_to_level = abs(current_price - nearest_level) / current_price
        
        # Only trigger if very close to round number
        if distance_to_level > 0.02:
            return None
        
        candles = market_data.get("candles_5m", [])
        if len(candles) < 10:
            return None
        
        recent_candles = candles[-10:]
        
        # Check for rejection (wick above/below level)
        if current_price < nearest_level:
            # Test from below
            resistance_test = any(c["high"] >= nearest_level * 0.999 and c["close"] < nearest_level * 0.995 
                                for c in recent_candles[-5:])
            if resistance_test:
                return PatternSignal(
                    pattern_name="btc_round_number_rejection",
                    signal_type="SELL",
                    confidence=0.65,
                    timeframe="5m",
                    reason=f"Rejection at ${nearest_level:,.0f} psychological resistance",
                    target_price=current_price * 0.98,
                    stop_loss=nearest_level * 1.005,
                    position_size=0.25
                )
        else:
            # Test from above
            support_test = any(c["low"] <= nearest_level * 1.001 and c["close"] > nearest_level * 1.005 
                             for c in recent_candles[-5:])
            if support_test:
                return PatternSignal(
                    pattern_name="btc_round_number_rejection",
                    signal_type="BUY",
                    confidence=0.65,
                    timeframe="5m",
                    reason=f"Bounce from ${nearest_level:,.0f} psychological support",
                    target_price=current_price * 1.02,
                    stop_loss=nearest_level * 0.995,
                    position_size=0.25
                )
        return None
    
    def _detect_higher_lows(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect higher lows pattern (bullish structure)"""
        candles = market_data.get("candles_1h", [])
        if len(candles) < 20:
            return None
        
        # Find swing lows in recent data
        lows = []
        for i in range(2, len(candles) - 2):
            if (candles[i]["low"] < candles[i-1]["low"] and 
                candles[i]["low"] < candles[i+1]["low"] and
                candles[i]["low"] < candles[i-2]["low"] and
                candles[i]["low"] < candles[i+2]["low"]):
                lows.append((i, candles[i]["low"]))
        
        # Need at least 3 swing lows
        if len(lows) >= 3:
            # Check if lows are ascending
            recent_lows = sorted(lows[-3:], key=lambda x: x[0])  # Sort by time
            if (recent_lows[1][1] > recent_lows[0][1] and 
                recent_lows[2][1] > recent_lows[1][1]):
                
                return PatternSignal(
                    pattern_name="btc_higher_lows",
                    signal_type="BUY",
                    confidence=0.8,
                    timeframe="1h",
                    reason="Bullish structure - higher lows pattern confirmed",
                    target_price=current_price * 1.04,
                    stop_loss=recent_lows[-1][1] * 0.995,
                    position_size=0.3
                )
        return None
    
    def _detect_halving_cycle_pattern(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect Bitcoin halving cycle patterns (simplified for demonstration)"""
        # This would need actual halving dates and historical analysis
        # For demonstration, using a simplified version
        
        current_time = datetime.now()
        
        # Simplified: assume we're in post-halving accumulation phase
        # Real implementation would check actual halving dates and cycle position
        
        # Mock halving cycle analysis
        days_since_last_halving = 500  # Example
        
        if 300 < days_since_last_halving < 800:  # Accumulation phase
            return PatternSignal(
                pattern_name="btc_halving_cycle",
                signal_type="BUY",
                confidence=0.95,
                timeframe="1d",
                reason="Post-halving accumulation phase - historical cycle bullish",
                target_price=current_price * 1.5,  # Cycle target
                stop_loss=current_price * 0.8,
                position_size=0.4
            )
        return None
    
    def _detect_fear_greed_extreme(self, market_data: Dict[str, Any], current_price: float) -> Optional[PatternSignal]:
        """Detect extreme fear/greed for contrarian signals"""
        # This would integrate with Fear & Greed Index API
        # For demonstration, using price volatility as proxy
        
        if len(self.volatility_history) < 20:
            return None
        
        recent_vol = np.mean([v["volatility"] for v in list(self.volatility_history)[-5:]])
        
        # Extreme volatility often correlates with fear
        if recent_vol > 0.015:  # High volatility = fear
            return PatternSignal(
                pattern_name="btc_fear_greed_extreme",
                signal_type="BUY",
                confidence=0.85,
                timeframe="5m",
                reason="Extreme fear conditions - contrarian buy signal",
                target_price=current_price * 1.03,
                stop_loss=current_price * 0.975,
                position_size=0.35
            )
        elif recent_vol < 0.003:  # Low volatility = complacency
            return PatternSignal(
                pattern_name="btc_fear_greed_extreme",
                signal_type="SELL",
                confidence=0.7,
                timeframe="5m",
                reason="Extreme greed/complacency - prepare for volatility",
                target_price=current_price * 0.98,
                stop_loss=current_price * 1.02,
                position_size=0.2
            )
        return None
    
    # Placeholder implementations for other patterns
    def _detect_asia_pump(self, market_data, current_price): return None
    def _detect_us_session_reversal(self, market_data, current_price): return None
    def _detect_low_volume_breakout(self, market_data, current_price): return None
    def _detect_high_volume_exhaustion(self, market_data, current_price): return None
    def _detect_accumulation_phase(self, market_data, current_price): return None
    def _detect_distribution_phase(self, market_data, current_price): return None
    def _detect_volatility_expansion(self, market_data, current_price): return None
    def _detect_fibonacci_bounce(self, market_data, current_price): return None
    def _detect_ath_test(self, market_data, current_price): return None
    def _detect_lower_highs(self, market_data, current_price): return None
    def _detect_range_bound(self, market_data, current_price): return None
    def _detect_trend_continuation(self, market_data, current_price): return None
    def _detect_pre_news_positioning(self, market_data, current_price): return None
    def _detect_post_news_reversion(self, market_data, current_price): return None
    def _detect_mining_difficulty_pattern(self, market_data, current_price): return None
    def _detect_on_chain_divergence(self, market_data, current_price): return None
    
    def _combine_bitcoin_patterns(self, pattern_signals: List[PatternSignal], current_price: float) -> Optional[Dict[str, Any]]:
        """Combine multiple Bitcoin pattern signals into unified trading decision"""
        if not pattern_signals:
            return None
        
        # Separate by signal type
        buy_signals = [p for p in pattern_signals if p.signal_type == "BUY"]
        sell_signals = [p for p in pattern_signals if p.signal_type == "SELL"]
        hold_signals = [p for p in pattern_signals if p.signal_type == "HOLD"]
        
        # Calculate weighted confidence for each direction
        buy_confidence = sum(p.confidence * self.pattern_weights.get(p.pattern_name, 0.5) for p in buy_signals)
        sell_confidence = sum(p.confidence * self.pattern_weights.get(p.pattern_name, 0.5) for p in sell_signals)
        
        # Determine dominant signal
        if buy_confidence > sell_confidence and buy_confidence > 1.0:
            # Strong buy signal
            strongest_buy = max(buy_signals, key=lambda x: x.confidence)
            return {
                "signal": "BUY",
                "confidence": min(0.95, buy_confidence),
                "reason": f"Bitcoin patterns favor buying: {strongest_buy.reason}",
                "target_price": strongest_buy.target_price,
                "stop_loss": strongest_buy.stop_loss,
                "position_size": min(0.5, sum(p.position_size for p in buy_signals) / len(buy_signals)),
                "supporting_patterns": [p.pattern_name for p in buy_signals]
            }
        elif sell_confidence > buy_confidence and sell_confidence > 1.0:
            # Strong sell signal
            strongest_sell = max(sell_signals, key=lambda x: x.confidence)
            return {
                "signal": "SELL",
                "confidence": min(0.95, sell_confidence),
                "reason": f"Bitcoin patterns favor selling: {strongest_sell.reason}",
                "target_price": strongest_sell.target_price,
                "stop_loss": strongest_sell.stop_loss,
                "position_size": min(0.5, sum(p.position_size for p in sell_signals) / len(sell_signals)),
                "supporting_patterns": [p.pattern_name for p in sell_signals]
            }
        elif hold_signals:
            # Hold/wait signal
            return {
                "signal": "HOLD",
                "confidence": max(p.confidence for p in hold_signals),
                "reason": "Bitcoin patterns suggest waiting for clearer direction",
                "supporting_patterns": [p.pattern_name for p in hold_signals]
            }
        
        return None