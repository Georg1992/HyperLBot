#!/usr/bin/env python3
"""
Test MarketDataService trend dataflow
Verifies that get_trend_analysis() and get_unified_analysis_data() work correctly
"""

import sys
import os
import time
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

# Setup Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger
from core.services.market_data_service import MarketDataService


class MockTrendCalculator:
    """Mock trend calculator that returns valid trend data"""
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        """Return valid trend analysis structure"""
        return {
            "trend_15m": "UPTREND",
            "trend_1h": "UPTREND",
            "trend_4h": "UPTREND",
            "trend_24h": "UPTREND",
            "details": {
                "15m": {"trend": "UPTREND", "strength": 0.75},
                "1h": {"trend": "UPTREND", "strength": 0.80},
                "4h": {"trend": "UPTREND", "strength": 0.85},
                "24h": {"trend": "UPTREND", "strength": 0.90}
            },
            "timestamp": time.time(),
            "data_type": "trend"
        }


class MockRSICalculator:
    """Mock RSI calculator"""
    
    def __init__(self):
        self.rsi_initialized = True  # Pretend it's initialized
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        return {"rsi": 55.0, "timestamp": time.time()}


class MockVolatilityCalculator:
    """Mock volatility calculator"""
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        return {
            "volatility_percentage": 2.5,
            "level": "MODERATE",
            "timestamp": time.time()
        }


class MockVolumeClassifier:
    """Mock volume classifier"""
    
    def get_latest_analysis(self, **kwargs) -> Dict[str, Any]:
        return {
            "volume_category": "NORMAL",
            "percentile": 50.0,
            "timestamp": time.time()
        }


class MockSupportResistanceCalculator:
    """Mock S/R calculator"""
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        return {
            "support_levels": [],
            "resistance_levels": [],
            "timestamp": time.time()
        }


class MockPressureCalculator:
    """Mock pressure calculator"""
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        return {
            "buy_pressure": 0.5,
            "sell_pressure": 0.5,
            "timestamp": time.time()
        }


class MockPatternAnalyzer:
    """Mock pattern analyzer"""
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        return {
            "patterns": [],
            "timestamp": time.time()
        }


class MockMarketConditionsAnalyzer:
    """Mock market conditions analyzer"""
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        return {
            "condition": "NORMAL",
            "timestamp": time.time()
        }


class MockFundingRateAnalyzer:
    """Mock funding rate analyzer"""
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        return {
            "funding_rate": 0.01,
            "rate_change": 0.0,
            "timestamp": time.time()
        }


class MockOrderbookAnalyzer:
    """Mock orderbook analyzer"""
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        return {
            "bid_ask_spread": 0.1,
            "timestamp": time.time()
        }


class MockCrossAssetAnalyzer:
    """Mock cross asset analyzer"""
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        return {
            "correlation": 0.5,
            "timestamp": time.time()
        }


def create_mock_market_data_service() -> MarketDataService:
    """Create MarketDataService with mocked dependencies"""
    mock_api = Mock()
    mock_websocket = Mock()
    
    service = MarketDataService(
        hyperliquid_api=mock_api,
        hyperliquid_websocket=mock_websocket,
        binance_api=None,
        binance_websocket=None
    )
    
    # Register all analysis modules
    service.register_analysis_module("trend", MockTrendCalculator())
    service.register_analysis_module("rsi_calculator", MockRSICalculator())
    service.register_analysis_module("volatility", MockVolatilityCalculator())
    service.register_analysis_module("volume", MockVolumeClassifier())
    service.register_analysis_module("support_resistance", MockSupportResistanceCalculator())
    service.register_analysis_module("pressure", MockPressureCalculator())
    service.register_analysis_module("patterns", MockPatternAnalyzer())
    service.register_analysis_module("market_conditions", MockMarketConditionsAnalyzer())
    service.register_analysis_module("funding_rate", MockFundingRateAnalyzer())
    service.register_analysis_module("orderbook", MockOrderbookAnalyzer())
    service.register_analysis_module("cross_asset_analysis", MockCrossAssetAnalyzer())
    
    # Set current price
    service._current_price = 50000.0
    service._price_timestamp = time.time()
    
    return service


def test_get_trend_analysis_returns_valid_structure():
    """Test that get_trend_analysis() returns a valid dict with required keys"""
    logger.info("🧪 Testing get_trend_analysis() returns valid structure...")
    
    service = create_mock_market_data_service()
    
    # Call get_trend_analysis
    trend_data = service.get_trend_analysis()
    
    # Verify structure
    assert isinstance(trend_data, dict), "trend_data must be a dict"
    assert "direction" in trend_data, "trend_data must have 'direction' key"
    assert "strength" in trend_data, "trend_data must have 'strength' key"
    assert "detailed_timeframes" in trend_data, "trend_data must have 'detailed_timeframes' key"
    
    # Verify detailed_timeframes structure
    detailed = trend_data["detailed_timeframes"]
    assert isinstance(detailed, dict), "detailed_timeframes must be a dict"
    assert "trend_15m" in detailed, "detailed_timeframes must have 'trend_15m'"
    assert "trend_1h" in detailed, "detailed_timeframes must have 'trend_1h'"
    assert "trend_4h" in detailed, "detailed_timeframes must have 'trend_4h'"
    assert "trend_24h" in detailed, "detailed_timeframes must have 'trend_24h'"
    
    logger.info("✅ get_trend_analysis() returns valid structure")


def test_get_unified_analysis_data_includes_trend():
    """Test that get_unified_analysis_data() includes 'trend' key"""
    logger.info("🧪 Testing get_unified_analysis_data() includes 'trend' key...")
    
    service = create_mock_market_data_service()
    
    # Call get_unified_analysis_data
    unified_data = service.get_unified_analysis_data()
    
    # Verify 'trend' key exists
    assert "trend" in unified_data, "unified_data must have 'trend' key"
    
    # Verify trend data structure
    trend_data = unified_data["trend"]
    assert isinstance(trend_data, dict), "trend_data must be a dict"
    assert "direction" in trend_data, "trend_data must have 'direction' key"
    assert "detailed_timeframes" in trend_data, "trend_data must have 'detailed_timeframes' key"
    
    # Verify trend_direction is also present (flattened)
    assert "trend_direction" in unified_data, "unified_data must have 'trend_direction' key"
    
    logger.info("✅ get_unified_analysis_data() includes 'trend' key")


def test_get_trend_analysis_raises_on_missing_module():
    """Test that get_trend_analysis() raises when trend module is not registered"""
    logger.info("🧪 Testing get_trend_analysis() raises on missing module...")
    
    service = create_mock_market_data_service()
    
    # Remove trend module
    service._analysis_modules.pop("trend", None)
    
    # Should raise ValueError
    try:
        service.get_trend_analysis()
        assert False, "get_trend_analysis() should raise ValueError when module is missing"
    except ValueError as e:
        assert "No trend analysis module registered" in str(e) or "NO FALLBACKS" in str(e)
        logger.info("✅ get_trend_analysis() correctly raises on missing module")
    except Exception as e:
        assert False, f"get_trend_analysis() should raise ValueError, but raised {type(e).__name__}: {e}"


def test_get_trend_analysis_raises_on_invalid_data():
    """Test that get_trend_analysis() raises when trend calculator returns invalid data"""
    logger.info("🧪 Testing get_trend_analysis() raises on invalid data...")
    
    service = create_mock_market_data_service()
    
    # Replace trend calculator with one that returns invalid data
    class InvalidTrendCalculator:
        def get_latest_analysis(self):
            return {"invalid": "data"}  # Missing required keys
    
    service._analysis_modules["trend"] = InvalidTrendCalculator()
    
    # Should raise KeyError or ValueError
    try:
        service.get_trend_analysis()
        assert False, "get_trend_analysis() should raise when data is invalid"
    except (KeyError, ValueError) as e:
        logger.info(f"✅ get_trend_analysis() correctly raises on invalid data: {e}")
    except Exception as e:
        assert False, f"get_trend_analysis() should raise KeyError or ValueError, but raised {type(e).__name__}: {e}"


def test_get_unified_analysis_data_never_returns_none_trend():
    """Test that get_unified_analysis_data() never has None or missing 'trend' key"""
    logger.info("🧪 Testing get_unified_analysis_data() never returns None trend...")
    
    service = create_mock_market_data_service()
    
    # Call multiple times to test consistency
    for i in range(5):
        unified_data = service.get_unified_analysis_data()
        
        # Verify 'trend' key always exists
        assert "trend" in unified_data, f"unified_data must have 'trend' key (iteration {i})"
        
        # Verify trend is not None
        assert unified_data["trend"] is not None, f"trend must not be None (iteration {i})"
        
        # Verify trend is a dict
        assert isinstance(unified_data["trend"], dict), f"trend must be a dict (iteration {i})"
    
    logger.info("✅ get_unified_analysis_data() consistently includes valid 'trend' key")


if __name__ == "__main__":
    logger.info("🧪 Running MarketDataService trend dataflow tests...")
    
    try:
        test_get_trend_analysis_returns_valid_structure()
        test_get_unified_analysis_data_includes_trend()
        test_get_trend_analysis_raises_on_missing_module()
        test_get_trend_analysis_raises_on_invalid_data()
        test_get_unified_analysis_data_never_returns_none_trend()
        
        logger.info("✅ All MarketDataService trend tests passed!")
    except AssertionError as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
