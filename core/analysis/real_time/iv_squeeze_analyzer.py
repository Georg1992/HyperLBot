#!/usr/bin/env python3
"""
IV Squeeze Analyzer
Detects Implied Volatility (IV) Squeeze conditions using Bollinger Bands and Keltner Channels

IV Squeeze occurs when:
- Lower Bollinger Band is above lower Keltner Channel
- Upper Bollinger Band is below upper Keltner Channel
- This indicates volatility compression (squeeze) before potential breakout

Based on TradingView implementation by Sunil Bhave
"""

from typing import Dict, Any, Optional, List
from loguru import logger


class IVSqueezeAnalyzer:
    """
    Analyzes IV Squeeze conditions using Bollinger Bands and Keltner Channels
    
    Features:
    - Calculates Bollinger Bands (SMA + standard deviation)
    - Calculates Keltner Channels (SMA + ATR)
    - Detects squeeze conditions (BB inside KC)
    - Measures squeeze strength
    - Tracks squeeze duration
    - Detects squeeze release (breakout)
    """
    
    def __init__(self, symbol: str = "BTC"):
        """
        Initialize IV Squeeze Analyzer
        
        Args:
            symbol: Trading symbol (default: "BTC")
        """
        self.symbol = symbol
        
        # Default parameters (matching TradingView script)
        self.bollinger_length = 20
        self.bollinger_deviation = 2.0
        self.keltner_length = 20
        self.keltner_mult = 1.0
        
        # State tracking (all timestamps from data_timestamp, never time.time())
        self._squeeze_start_time: Optional[float] = None
        self._last_squeeze_state = False
        self._last_release_timestamp: Optional[float] = None
        self._squeeze_history: List[Dict[str, Any]] = []
        
        logger.info(f"📊 IV Squeeze Analyzer initialized for {symbol}")
    
    def calculate_bollinger_bands(self, candles: List[Dict], length: int = None, deviation: float = None) -> Dict[str, float]:
        """
        Calculate Bollinger Bands
        
        Args:
            candles: List of candle dictionaries with 'close' key
            length: Period for SMA calculation (default: self.bollinger_length)
            deviation: Standard deviation multiplier (default: self.bollinger_deviation)
        
        Returns:
            Dictionary with 'upper', 'middle' (SMA), 'lower' keys
        
        Raises:
            ValueError: If insufficient candles or invalid data (NO FALLBACKS)
        """
        try:
            length = length or self.bollinger_length
            deviation = deviation or self.bollinger_deviation
            
            if len(candles) < length:
                raise ValueError(f"Insufficient candles for Bollinger Bands: {len(candles)} < {length} (NO FALLBACKS)")
            
            # Extract closes
            closes = [float(candle['close']) for candle in candles[-length:] if 'close' in candle and candle['close'] > 0]
            
            if len(closes) < length:
                raise ValueError(f"Insufficient valid closes for Bollinger Bands: {len(closes)} < {length} (NO FALLBACKS)")
            
            # Calculate SMA (middle band)
            sma = sum(closes) / len(closes)
            
            # Calculate standard deviation
            variance = sum((x - sma) ** 2 for x in closes) / len(closes)
            stdev = variance ** 0.5
            
            # Calculate bands
            upper_bb = sma + (deviation * stdev)
            lower_bb = sma - (deviation * stdev)
            
            return {
                'upper': upper_bb,
                'middle': sma,
                'lower': lower_bb,
                'stdev': stdev
            }
            
        except Exception as e:
            logger.error(f"❌ Bollinger Bands calculation failed: {e}")
            raise  # NO FALLBACKS
    
    def calculate_keltner_channels(self, candles: List[Dict], length: int = None, mult: float = None) -> Dict[str, float]:
        """
        Calculate Keltner Channels using ATR
        
        Args:
            candles: List of candle dictionaries
            length: Period for SMA and ATR calculation (default: self.keltner_length)
            mult: ATR multiplier (default: self.keltner_mult)
        
        Returns:
            Dictionary with 'upper', 'middle' (SMA), 'lower', 'atr' keys
        
        Raises:
            ValueError: If insufficient candles or invalid data (NO FALLBACKS)
        """
        try:
            length = length or self.keltner_length
            mult = mult or self.keltner_mult
            
            if len(candles) < length:
                raise ValueError(f"Insufficient candles for Keltner Channels: {len(candles)} < {length} (NO FALLBACKS)")
            
            # Extract closes for SMA
            closes = [float(candle['close']) for candle in candles[-length:] if 'close' in candle and candle['close'] > 0]
            
            if len(closes) < length:
                raise ValueError(f"Insufficient valid closes for Keltner Channels: {len(closes)} < {length} (NO FALLBACKS)")
            
            # Calculate SMA (middle line)
            sma = sum(closes) / len(closes)
            
            # Calculate ATR (using existing method pattern)
            atr = self._calculate_atr(candles, length)
            
            # Calculate channels
            upper_kc = sma + (mult * atr)
            lower_kc = sma - (mult * atr)
            
            return {
                'upper': upper_kc,
                'middle': sma,
                'lower': lower_kc,
                'atr': atr
            }
            
        except Exception as e:
            logger.error(f"❌ Keltner Channels calculation failed: {e}")
            raise  # NO FALLBACKS
    
    def _calculate_atr(self, candles: List[Dict], period: int) -> float:
        """
        Calculate Average True Range (ATR)
        
        Args:
            candles: List of candle dictionaries
            period: ATR period
        
        Returns:
            ATR value
        """
        try:
            if len(candles) < period + 1:
                # Use minimum ATR fallback (similar to SRDataProvider)
                if candles:
                    price = candles[-1]['close'] if 'close' in candles[-1] else 100.0
                    from config.config import TradingConfig
                    min_atr = max(price * TradingConfig.ATR_MIN_PCT, TradingConfig.ATR_ABSOLUTE_MIN)
                    logger.warning(f"⚠️ Insufficient candles for ATR, using minimum: {min_atr:.2f}")
                    return min_atr
                else:
                    from config.config import TradingConfig
                    return TradingConfig.ATR_ABSOLUTE_MIN
            
            true_ranges = []
            
            for i in range(1, len(candles)):
                prev_close = candles[i-1].get('close', 0)
                high = candles[i].get('high', 0)
                low = candles[i].get('low', 0)
                close = candles[i].get('close', 0)
                
                if prev_close > 0 and high > 0 and low > 0 and close > 0:
                    tr1 = high - low
                    tr2 = abs(high - prev_close)
                    tr3 = abs(low - prev_close)
                    true_range = max(tr1, tr2, tr3)
                    true_ranges.append(true_range)
            
            if len(true_ranges) < period:
                # Use minimum ATR fallback
                if candles:
                    price = candles[-1].get('close', 100.0)
                    from config.config import TradingConfig
                    min_atr = max(price * TradingConfig.ATR_MIN_PCT, TradingConfig.ATR_ABSOLUTE_MIN)
                    logger.warning(f"⚠️ Insufficient true ranges for ATR, using minimum: {min_atr:.2f}")
                    return min_atr
                else:
                    from config.config import TradingConfig
                    return TradingConfig.ATR_ABSOLUTE_MIN
            
            # Calculate ATR using simple moving average of true ranges
            recent_tr = true_ranges[-period:]
            atr = sum(recent_tr) / len(recent_tr)
            
            return atr
            
        except Exception as e:
            logger.error(f"❌ ATR calculation failed: {e}")
            # Fallback to minimum ATR
            from config.config import TradingConfig
            return TradingConfig.ATR_ABSOLUTE_MIN
    
    def detect_squeeze(
        self,
        candles: List[Dict],
        current_price: float = None,
        data_timestamp: float = None,
    ) -> Dict[str, Any]:
        """
        Detect IV Squeeze condition.
        Uses data_timestamp only (no time.time()) for determinism.
        
        Args:
            candles: List of candle dictionaries (need at least max(bollinger_length, keltner_length))
            current_price: Current market price (optional, uses last candle close if not provided)
            data_timestamp: Unix timestamp for this tick (required for determinism; use unified_data["timestamp"])
        
        Returns:
            Dictionary with squeeze analysis:
            - is_squeeze, squeeze_strength, duration_minutes, squeeze_released
            - release_timestamp: set when squeeze_released transitions False→True; else kept from last release
            - bollinger_bands, keltner_channels, current_price, timestamp (= data_timestamp)
        
        Raises:
            ValueError: If insufficient candles or data_timestamp missing (NO FALLBACKS)
        """
        try:
            if data_timestamp is None:
                raise ValueError("data_timestamp is required for IV Squeeze (NO FALLBACKS)")
            current_time = float(data_timestamp)
            if current_price is None:
                if not candles:
                    raise ValueError("No candles provided and no current_price (NO FALLBACKS)")
                current_price = candles[-1].get('close', 0)
                if current_price <= 0:
                    raise ValueError(f"Invalid current_price from candles: {current_price} (NO FALLBACKS)")
            
            bb = self.calculate_bollinger_bands(candles)
            kc = self.calculate_keltner_channels(candles)
            is_squeeze = (bb['lower'] > kc['lower']) and (bb['upper'] < kc['upper'])
            if is_squeeze:
                bb_width = bb['upper'] - bb['lower']
                kc_width = kc['upper'] - kc['lower']
                squeeze_strength = min(1.0, bb_width / kc_width) if kc_width > 0 else 0.0
            else:
                squeeze_strength = 0.0
            
            squeeze_released = False
            release_timestamp: Optional[float] = self._last_release_timestamp
            
            if is_squeeze:
                if not self._last_squeeze_state:
                    self._squeeze_start_time = current_time
                duration_minutes = (current_time - self._squeeze_start_time) / 60.0 if self._squeeze_start_time else 0.0
            else:
                if self._last_squeeze_state:
                    squeeze_released = True
                    release_timestamp = current_time
                    self._last_release_timestamp = current_time
                    duration_minutes = (current_time - self._squeeze_start_time) / 60.0 if self._squeeze_start_time else 0.0
                    logger.info(f"📊 IV Squeeze released after {duration_minutes:.1f} minutes - potential breakout")
                else:
                    duration_minutes = 0.0
                self._squeeze_start_time = None
            
            self._last_squeeze_state = is_squeeze
            
            if len(self._squeeze_history) >= 10:
                self._squeeze_history.pop(0)
            self._squeeze_history.append({
                'timestamp': current_time,
                'is_squeeze': is_squeeze,
                'squeeze_strength': squeeze_strength,
                'duration_minutes': duration_minutes,
                'current_price': current_price,
            })
            
            result = {
                'is_squeeze': is_squeeze,
                'squeeze_strength': squeeze_strength,
                'duration_minutes': duration_minutes if is_squeeze else 0.0,
                'squeeze_released': squeeze_released,
                'release_timestamp': release_timestamp,
                'bollinger_bands': {'upper': bb['upper'], 'middle': bb['middle'], 'lower': bb['lower']},
                'keltner_channels': {'upper': kc['upper'], 'middle': kc['middle'], 'lower': kc['lower']},
                'current_price': current_price,
                'timestamp': current_time,
            }
            if is_squeeze:
                logger.debug(f"📊 IV Squeeze detected: strength={squeeze_strength:.2f}, duration={duration_minutes:.1f}m")
            return result
        except Exception as e:
            logger.error(f"❌ IV Squeeze detection failed: {e}")
            raise
    
    def get_latest_analysis(
        self,
        candles: List[Dict] = None,
        current_price: float = None,
        data_timestamp: float = None,
    ) -> Dict[str, Any]:
        """
        Get latest IV Squeeze analysis.
        data_timestamp required for determinism (use unified_data["timestamp"] or tick timestamp).
        """
        try:
            if candles is None:
                from core.services.historical_data_service import get_global_historical_data_service
                historical_service = get_global_historical_data_service()
                required_candles = max(self.bollinger_length, self.keltner_length) + 5
                candles = historical_service.get_5m_candles(self.symbol, required_candles)
                if not candles or len(candles) < max(self.bollinger_length, self.keltner_length):
                    raise ValueError(
                        f"Insufficient candles for IV Squeeze analysis: {len(candles) if candles else 0} < "
                        f"{max(self.bollinger_length, self.keltner_length)} (NO FALLBACKS)"
                    )
            return self.detect_squeeze(candles, current_price, data_timestamp)
        except Exception as e:
            logger.error(f"❌ Failed to get latest IV Squeeze analysis: {e}")
            raise
