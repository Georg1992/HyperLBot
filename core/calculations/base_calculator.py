import time
from typing import Dict, Any, Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from core.services.centralized_cache import CentralizedCache

class BaseCalculator:
    """Base class for all calculators to provide common functionality and ensure DRY principles"""

    def __init__(self, symbol: str = "BTC", cache: Optional["CentralizedCache"] = None):
        self.symbol = symbol
        if cache is None:
            from core.services.centralized_cache import get_global_centralized_cache
            self._cache = get_global_centralized_cache()
        else:
            self._cache = cache
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
