import time
from typing import Dict, Any
from loguru import logger
from core.services.centralized_cache import get_global_centralized_cache

class BaseCalculator:
    """Base class for all calculators to provide common functionality and ensure DRY principles"""

    def __init__(self, symbol: str = "BTC"):
        self.symbol = symbol
        self._cache = get_global_centralized_cache()
        logger.debug(f"BaseCalculator initialized for {symbol}")

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Create a consistent error result dictionary for all calculators.
        This method can be overridden by subclasses to add specific fields.
        """
        return {
            "status": "error",
            "message": error_message,
            "timestamp": time.time(),
            "symbol": self.symbol
        }
