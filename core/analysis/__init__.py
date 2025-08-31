#!/usr/bin/env python3
"""
Market Analysis Package
=======================

This package provides comprehensive market analysis capabilities with clear separation
between real-time and historical analysis:

REAL-TIME ANALYSIS (core/analysis/real_time/):
- orderbook_analyzer.py: Live orderbook analysis for instant trading decisions
- volatility_calculator.py: Real-time volatility calculations from live data

HISTORICAL ANALYSIS (core/analysis/historical/):
- market_data_analyzer.py: Historical data analysis and RSI calculations
- market_volatility_analyzer.py: Historical volatility analysis from candle data

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
    # e.g. from core.analysis.historical.market_data_analyzer import MarketDataAnalyzer
]
