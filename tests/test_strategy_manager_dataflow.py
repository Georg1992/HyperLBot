#!/usr/bin/env python3
"""
Test StrategyManager data extraction
Verifies that _extract_market_data() correctly handles trend data from MarketDataService
"""

import sys
import os
import time
from unittest.mock import Mock
from typing import Dict, Any

# Setup Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger
from core.services.strategy_manager import StrategyManager


def create_valid_market_data() -> Dict[str, Any]:
    """Create valid market_data dict that matches MarketDataService output"""
    return {
        # Core market data
        "current_price": 50000.0,
        "timestamp": time.time(),
        
        # Flattened data
        "volatility_category": "MODERATE",
        "trend_direction": "BULLISH",
        "volume_category": "NORMAL",
        "volatility_5m": 0.025,
        "rsi_value": 55.0,
        
        # Nested data
        "trend": {
            "direction": "BULLISH",
            "strength": 0.80,
            "timeframes": {
                "short": "BULLISH",
                "medium": "BULLISH",
                "long": "BULLISH"
            },
            "detailed_timeframes": {
                "trend_15m": "BULLISH",
                "trend_1h": "BULLISH",
                "trend_4h": "BULLISH",
                "trend_24h": "BULLISH"
            },
            "raw_data": {},
            "timestamp": time.time()
        },
        "rsi": {
            "rsi": 55.0,
            "rsi_trend": "NEUTRAL",
            "rsi_signal": "NEUTRAL",
            "rsi_momentum": 0.0,
            "timestamp": time.time()
        },
        "volatility": {
            "volatility_percentage": 2.5,
            "level": "MODERATE",
            "timestamp": time.time()
        },
        "volume": {
            "volume_category": "NORMAL",
            "percentile": 50.0,
            "timestamp": time.time()
        },
        "support_resistance": {
            "support_levels": [],
            "resistance_levels": [],
            "timestamp": time.time()
        },
        "orderbook_analysis": {
            "bid_ask_spread": {
                "percentage": 0.1,
                "absolute": 5.0
            },
            "timestamp": time.time()
        },
        "pressure": {
            "buy_pressure": 0.5,
            "sell_pressure": 0.5,
            "timestamp": time.time()
        },
        "funding_analysis": {
            "funding_rate": 0.01,
            "rate_change": 0.0,
            "timestamp": time.time()
        },
        "market_conditions": {
            "condition": "NORMAL",
            "timestamp": time.time()
        }
    }


def test_extract_market_data_with_valid_trend():
    """Test that _extract_market_data() correctly extracts trend data"""
    logger.info("🧪 Testing _extract_market_data() with valid trend data...")
    
    # Create StrategyManager (needs minimal setup)
    strategy_manager = StrategyManager()
    
    # Create valid market_data
    market_data = create_valid_market_data()
    
    # Extract market data
    extracted = strategy_manager._extract_market_data(market_data)
    
    # Verify trend data was extracted
    assert "trend_15m" in extracted, "extracted data must have 'trend_15m'"
    assert "trend_1h" in extracted, "extracted data must have 'trend_1h'"
    
    logger.info("✅ _extract_market_data() correctly extracts trend data")


def test_extract_market_data_raises_on_missing_trend():
    """Test that _extract_market_data() raises KeyError when 'trend' key is missing"""
    logger.info("🧪 Testing _extract_market_data() raises on missing 'trend' key...")
    
    # Create StrategyManager
    strategy_manager = StrategyManager()
    
    # Create market_data without 'trend' key
    market_data = create_valid_market_data()
    del market_data["trend"]
    
    # Should raise KeyError
    try:
        strategy_manager._extract_market_data(market_data)
        assert False, "_extract_market_data() should raise KeyError when 'trend' is missing"
    except KeyError as e:
        assert "trend" in str(e), f"KeyError should mention 'trend', but got: {e}"
        logger.info("✅ _extract_market_data() correctly raises KeyError on missing 'trend'")
    except Exception as e:
        assert False, f"_extract_market_data() should raise KeyError, but raised {type(e).__name__}: {e}"


def test_extract_market_data_raises_on_missing_detailed_timeframes():
    """Test that _extract_market_data() raises KeyError when 'detailed_timeframes' is missing"""
    logger.info("🧪 Testing _extract_market_data() raises on missing 'detailed_timeframes'...")
    
    # Create StrategyManager
    strategy_manager = StrategyManager()
    
    # Create market_data with trend but without detailed_timeframes
    market_data = create_valid_market_data()
    market_data["trend"] = {
        "direction": "BULLISH",
        "strength": 0.80
        # Missing detailed_timeframes
    }
    
    # Should raise KeyError
    try:
        strategy_manager._extract_market_data(market_data)
        assert False, "_extract_market_data() should raise KeyError when 'detailed_timeframes' is missing"
    except KeyError as e:
        assert "detailed_timeframes" in str(e), f"KeyError should mention 'detailed_timeframes', but got: {e}"
        logger.info("✅ _extract_market_data() correctly raises KeyError on missing 'detailed_timeframes'")
    except Exception as e:
        assert False, f"_extract_market_data() should raise KeyError, but raised {type(e).__name__}: {e}"


def test_integration_market_data_service_to_strategy_manager():
    """Integration test: MarketDataService -> StrategyManager dataflow"""
    logger.info("🧪 Testing integration: MarketDataService -> StrategyManager...")
    
    # Import here to avoid circular dependencies
    from tests.test_market_data_service_trend import create_mock_market_data_service
    
    # Create MarketDataService
    market_data_service = create_mock_market_data_service()
    
    # Get unified analysis data
    unified_data = market_data_service.get_unified_analysis_data()
    
    # Verify 'trend' key exists
    assert "trend" in unified_data, "unified_data from MarketDataService must have 'trend' key"
    
    # Create StrategyManager
    strategy_manager = StrategyManager()
    
    # Extract market data (should not raise)
    try:
        extracted = strategy_manager._extract_market_data(unified_data)
        logger.info("✅ Integration test passed: MarketDataService -> StrategyManager")
    except KeyError as e:
        logger.error(f"❌ Integration test failed: KeyError when extracting market data: {e}")
        logger.error(f"   unified_data keys: {list(unified_data.keys())}")
        if "trend" in unified_data:
            logger.error(f"   trend keys: {list(unified_data['trend'].keys())}")
        raise
    except Exception as e:
        logger.error(f"❌ Integration test failed: Unexpected error: {e}")
        raise


if __name__ == "__main__":
    logger.info("🧪 Running StrategyManager dataflow tests...")
    
    try:
        test_extract_market_data_with_valid_trend()
        test_extract_market_data_raises_on_missing_trend()
        test_extract_market_data_raises_on_missing_detailed_timeframes()
        test_integration_market_data_service_to_strategy_manager()
        
        logger.info("✅ All StrategyManager dataflow tests passed!")
    except AssertionError as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
