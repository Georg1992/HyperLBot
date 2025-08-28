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

# Import real-time analysis modules
from .real_time import MarketOrderbookAnalyzer, VolatilityCalculator

# Import historical analysis modules  
from .historical import MarketDataAnalyzer, VariabilityAnalyzer

__all__ = [
    # Real-time analysis
    'MarketOrderbookAnalyzer',
    'VolatilityCalculator',
    
    # Historical analysis
    'MarketDataAnalyzer', 
    'VariabilityAnalyzer'
]
