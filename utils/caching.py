"""Intelligent caching for expensive operations.

Provides LRU caching for SHAP explanations and predictions.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import numpy as np


def hash_array(arr: np.ndarray) -> str:
    """Create hash of numpy array for caching.
    
    Args:
        arr: Numpy array to hash.
        
    Returns:
        Hash string.
    """
    return hashlib.md5(arr.tobytes()).hexdigest()


def hash_dict(d: dict[str, Any]) -> str:
    """Create hash of dictionary for caching.
    
    Args:
        d: Dictionary to hash.
        
    Returns:
        Hash string.
    """
    json_str = json.dumps(d, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()


class DiskCache:
    """Disk-based cache for large objects."""
    
    def __init__(self, cache_dir: str = ".cache"):
        """Initialize disk cache.
        
        Args:
            cache_dir: Directory for cache files.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key.
            
        Returns:
            Cached value or None if not found.
        """
        cache_file = self.cache_dir / f"{key}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key.
            value: Value to cache.
        """
        cache_file = self.cache_dir / f"{key}.pkl"
        
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(value, f)
        except Exception:
            pass  # Silently fail on cache write errors
    
    def clear(self) -> None:
        """Clear all cache files."""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()


# Global cache instance
_global_cache: Optional[DiskCache] = None


def get_cache() -> DiskCache:
    """Get or create global cache instance.
    
    Returns:
        Global DiskCache instance.
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = DiskCache()
    return _global_cache


def cached_shap_explanation(func):
    """Decorator for caching SHAP explanations.
    
    Usage:
        @cached_shap_explanation
        def compute_shap(X):
            # expensive SHAP computation
            return shap_values
    """
    cache = get_cache()
    
    def wrapper(X: np.ndarray, *args, **kwargs):
        # Create cache key from input
        key = f"shap_{hash_array(X)}"
        
        # Try to get from cache
        cached_result = cache.get(key)
        if cached_result is not None:
            return cached_result
        
        # Compute and cache
        result = func(X, *args, **kwargs)
        cache.set(key, result)
        
        return result
    
    return wrapper
