#!/usr/bin/env python3
"""
Market Analysis Package
=======================

This package provides comprehensive market analysis capabilities with clear separation
between real-time and historical analysis:

REAL-TIME ANALYSIS (core/analysis/real_time/):
- orderbook_data_fetcher.py: Fetches orderbook data from Hyperliquid API
- volatility_calculator.py: Real-time volatility calculations
- volume_calculator.py: Volume analysis calculations
- pressure_calculator.py: Market pressure calculations
- rsi_calculator.py: RSI calculations
- support_resistance_calculator.py: Support/resistance calculations
- trend_calculator.py: Trend analysis calculations

HISTORICAL ANALYSIS (core/analysis/historical/):
- historical_data_coordinator.py: Historical data coordination and analysis
- variability_analyzer.py: Historical variability analysis from candle data

DATA SOURCES:
- Real-time: Hyperliquid API, live orderbooks
- Historical: Yahoo Finance, historical candlesticks
"""

# Lazy imports to prevent circular dependencies
# Use direct imports in code instead of importing everything in __init__.py

# For backwards compatibility, import only essential real-time modules
# that don't have circular dependencies
from .real_time import VolatilityCalculator

# Historical modules should be imported directly where needed to avoid
# circular dependency chains (MarketDataAnalyzer → YahooDataFetcher)

__all__ = [
    # Real-time analysis (safe imports)
    'VolatilityCalculator',
    
    # Historical analysis - import directly where needed to avoid circular dependencies
    # e.g. from core.analysis.historical.historical_data_coordinator import MarketDataAnalyzer
]
