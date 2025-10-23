#!/usr/bin/env python3
"""
Historical Analysis Modules
===========================

This package contains modules for historical market analysis using historical data:

- historical_data_coordinator.py: Historical market data coordination and analysis
- variability_analyzer.py: Historical variability analysis from candle data

These modules work with historical data from sources like Hyperliquid
and provide analysis for backtesting and trend identification.
"""

# Lazy imports to prevent circular dependencies
# Use direct imports in code instead of importing everything in __init__.py

__all__ = ['MarketDataAnalyzer', 'VariabilityAnalyzer']
