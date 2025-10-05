#!/usr/bin/env python3
"""
External API Clients Module
Contains all external API clients for data fetching
"""

# Lazy imports to prevent circular dependencies
# Use direct imports in code instead of importing everything in __init__.py

__all__ = [
    'BinanceAPI',
    'binance_api',
    'FearGreedAPI', 
    'WhaleAnalyticsAPI', 
    'RSSNewsAPI',
]
