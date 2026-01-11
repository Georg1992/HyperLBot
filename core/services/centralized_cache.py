#!/usr/bin/env python3
"""
Centralized Cache System
========================
Unified caching system for the entire trading bot to eliminate cache chaos
and provide single source of truth for all cached data.
"""

import time
import threading
from typing import Dict, Any, Optional
from loguru import logger

# Singleton pattern implementation
_global_centralized_cache = None

def get_global_centralized_cache() -> 'CentralizedCache':
    """Get the global CentralizedCache singleton instance"""
    global _global_centralized_cache
    if _global_centralized_cache is None:
        _global_centralized_cache = CentralizedCache()
    return _global_centralized_cache

class CentralizedCache:
    """
    Centralized caching system for the entire trading bot.
    Replaces all individual caching implementations with a unified system.
    """
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
        self._ttl_policies = {}
        self._lock = threading.RLock()
        
        # Cache performance tracking
        self._hit_count = 0
        self._miss_count = 0
        self._access_times = {}  # Track when keys were last accessed
        
        # Default TTL policies for different data types
        self._default_ttl_policies = {
            # Market data - frequent updates
            "current_price": 5,           # 5 seconds
            "volume": 30,                 # 30 seconds
            "volatility": 60,             # 1 minute
            "trend": 60,                  # 1 minute
            "rsi": 60,                     # 1 minute
            "pressure": 60,               # 1 minute
            
            # Analysis data - moderate updates
            "support_resistance": 300,    # 5 minutes
            "patterns": 300,              # 5 minutes (matches 5m candle closes)
            "pattern_recognition": 300,   # 5 minutes (matches 5m candle closes)
            "market_conditions": 300,     # 5 minutes
            "cross_asset_analysis": 60,  # 1 minute
            "funding_analysis": 300,      # 5 minutes
            "orderbook_analysis": 60,     # 1 minute
            
            # Historical data - long cache (data doesn't change)
            "historical_candles": 1800,    # 30 minutes
            "candles_5m": 1800,           # 30 minutes
            "candles_15m": 1800,          # 30 minutes
            "candles_1h": 1800,           # 30 minutes
            "candles_1d": 3600,          # 1 hour
            
            # External API data - longer cache
            "whale_analytics": 300,       # 5 minutes
            "fear_greed": 600,            # 10 minutes
            "news_sentiment": 300,        # 5 minutes
            "yahoo_finance": 300,         # 5 minutes
            "blockcypher": 300,           # 5 minutes
            
            # Session data - persistent
            "session_data": 3600,         # 1 hour
            "dashboard_data": 30,         # 30 seconds
        }
        
        logger.info("🗄️ Centralized Cache System initialized")
    
    def get(self, key: str, force_fresh: bool = False) -> Optional[Any]:
        """
        Get data from cache if valid
        
        Args:
            key: Cache key
            force_fresh: If True, bypass cache and return None
            
        Returns:
            Cached data if valid, None if expired or not found
        """
        try:
            with self._lock:
                if force_fresh:
                    return None
                
                if key not in self._cache:
                    self._miss_count += 1
                    return None
                
                # Check if cache is still valid
                if not self._is_valid(key):
                    # Auto-cleanup expired entries
                    self._remove(key)
                    self._miss_count += 1
                    return None
                
                # Track hit and access time
                self._hit_count += 1
                self._access_times[key] = time.time()
                # Removed excessive debug logging for cache hits
                return self._cache[key]
                
        except Exception as e:
            logger.error(f"❌ Cache get failed for {key}: {e}")
            return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """
        Store data in cache
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (uses policy default if None)
            
        Returns:
            True if stored successfully
        """
        try:
            with self._lock:
                # Use provided TTL or policy default
                cache_ttl = ttl if ttl is not None else self._get_ttl_policy(key)
                
                self._cache[key] = data
                self._timestamps[key] = time.time()
                self._ttl_policies[key] = cache_ttl
                
                # Only log cache sets for important keys to reduce noise
                if any(important_key in key for important_key in ['support_resistance', 'pattern_recognition', 'whale_analytics']):
                    logger.debug(f"🗄️ Cache SET: {key} (TTL: {cache_ttl}s)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Cache set failed for {key}: {e}")
            return False
    
    def invalidate(self, key: Optional[str] = None, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries
        
        Args:
            key: Specific key to invalidate
            pattern: Regex pattern to match keys (e.g., "support_resistance.*")
            
        Returns:
            Number of entries invalidated
        """
        try:
            with self._lock:
                if key:
                    # Invalidate specific key
                    if key in self._cache:
                        self._remove(key)
                        logger.info(f"🗑️ Invalidated cache key: {key}")
                        return 1
                    return 0
                
                elif pattern:
                    # Invalidate keys matching pattern
                    import re
                    pattern_re = re.compile(pattern)
                    invalidated = 0
                    
                    keys_to_remove = [k for k in self._cache.keys() if pattern_re.match(k)]
                    for k in keys_to_remove:
                        self._remove(k)
                        invalidated += 1
                    
                    logger.info(f"🗑️ Invalidated {invalidated} cache keys matching pattern: {pattern}")
                    return invalidated
                
                else:
                    # Invalidate all
                    count = len(self._cache)
                    self._cache.clear()
                    self._timestamps.clear()
                    self._ttl_policies.clear()
                    logger.info(f"🗑️ Invalidated all cache entries ({count} entries)")
                    return count
                    
        except Exception as e:
            logger.error(f"❌ Cache invalidation failed: {e}")
            return 0
    
    def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None, force_fresh: bool = False) -> Any:
        """
        Get from cache or compute and store using factory function
        
        Args:
            key: Cache key
            factory_func: Function to compute data if not cached
            ttl: Time to live in seconds
            force_fresh: If True, bypass cache and recompute
            
        Returns:
            Cached or computed data
        """
        try:
            # Try to get from cache first
            if not force_fresh:
                cached_data = self.get(key)
                if cached_data is not None:
                    return cached_data
            
            # Compute fresh data
            # Removed excessive debug logging for cache misses
            fresh_data = factory_func()
            
            # Store in cache
            self.set(key, fresh_data, ttl)
            
            return fresh_data
            
        except Exception as e:
            logger.error(f"❌ Cache get_or_set failed for {key}: {e}")
            raise
    
    def _is_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache or key not in self._timestamps:
            return False
        
        ttl = self._ttl_policies.get(key, self._get_ttl_policy(key))
        age = time.time() - self._timestamps[key]
        
        return age < ttl
    
    def _get_ttl_policy(self, key: str) -> int:
        """Get TTL policy for a key"""
        # Check for exact key match first
        if key in self._default_ttl_policies:
            return self._default_ttl_policies[key]
        
        # Check for pattern matches
        for pattern, ttl in self._default_ttl_policies.items():
            if pattern in key or key.startswith(pattern):
                return ttl
        
        # Default fallback
        return 300  # 5 minutes
    
    def _remove(self, key: str):
        """Remove key from all cache structures"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        self._ttl_policies.pop(key, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            with self._lock:
                current_time = time.time()
                valid_entries = 0
                expired_entries = 0
                
                for key in self._cache.keys():
                    if self._is_valid(key):
                        valid_entries += 1
                    else:
                        expired_entries += 1
                
                total_requests = self._hit_count + self._miss_count
                hit_rate = (self._hit_count / total_requests * 100) if total_requests > 0 else 0
                
                return {
                    "total_entries": len(self._cache),
                    "valid_entries": valid_entries,
                    "expired_entries": expired_entries,
                    "cache_keys": list(self._cache.keys()),
                    "memory_usage_mb": self._estimate_memory_usage(),
                    "oldest_entry_age": self._get_oldest_entry_age(),
                    "newest_entry_age": self._get_newest_entry_age(),
                    "hit_count": self._hit_count,
                    "miss_count": self._miss_count,
                    "hit_rate_percent": hit_rate,
                    "total_requests": total_requests
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
            return {}
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB"""
        try:
            import sys
            total_size = 0
            for key, value in self._cache.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)
            return total_size / (1024 * 1024)  # Convert to MB
        except:
            return 0.0
    
    def _get_oldest_entry_age(self) -> float:
        """Get age of oldest cache entry in seconds"""
        if not self._timestamps:
            return 0.0
        
        current_time = time.time()
        oldest_timestamp = min(self._timestamps.values())
        return current_time - oldest_timestamp
    
    def _get_newest_entry_age(self) -> float:
        """Get age of newest cache entry in seconds"""
        if not self._timestamps:
            return 0.0
        
        current_time = time.time()
        newest_timestamp = max(self._timestamps.values())
        return current_time - newest_timestamp
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        try:
            with self._lock:
                expired_keys = [key for key in self._cache.keys() if not self._is_valid(key)]
                
                for key in expired_keys:
                    self._remove(key)
                
                if expired_keys:
                    logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
                
                return len(expired_keys)
                
        except Exception as e:
            logger.error(f"❌ Cache cleanup failed: {e}")
            return 0
    
    def force_sr_recalculation(self):
        """Force S/R recalculation by clearing all S/R related caches"""
        try:
            # Clear all S/R related cache entries
            sr_patterns = [
                "support_resistance",
                "sr_",
                "strongest_support",
                "strongest_resistance",
                "key_levels"
            ]
            
            total_invalidated = 0
            for pattern in sr_patterns:
                count = self.invalidate(pattern=f".*{pattern}.*")
                total_invalidated += count
            
            logger.info(f"🗑️ FORCED S/R recalculation - cleared {total_invalidated} cache entries")
            
        except Exception as e:
            logger.error(f"❌ Failed to force S/R recalculation: {e}")
