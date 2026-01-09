#!/usr/bin/env python3
"""
Market Analysis Package
=======================

This package provides comprehensive market analysis capabilities with clear separation
between real-time and historical analysis:

REAL-TIME ANALYSIS (core/analysis/real_time/):
- Real-time analysis modules for market data processing
- Note: Calculators are in core/calculations/, analyzers are here

HISTORICAL ANALYSIS (core/analysis/historical/):
- Historical data coordination is handled by HistoricalDataService

DATA SOURCES:
- Real-time: Hyperliquid API, live orderbooks
- Historical: Hyperliquid, historical candlesticks
"""

# Lazy imports to prevent circular dependencies
# Use direct imports in code instead of importing everything in __init__.py

# Historical modules should be imported directly where needed to avoid
# circular dependency chains (MarketDataAnalyzer → HyperliquidDataFetcher)

__all__ = [
    # Real-time analysis (safe imports)
    'VolatilityCalculator',
    
    # Historical analysis - import directly where needed to avoid circular dependencies
    # e.g. from core.analysis.historical.historical_data_coordinator import MarketDataAnalyzer
]
