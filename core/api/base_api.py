#!/usr/bin/env python3
"""
Base API Class - Common functionality for all API classes
"""

import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger

class BaseAPI(ABC):
    """Base class for all API implementations"""
    
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HyperLBot/1.0',
            'Accept': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """Test API connection - common implementation for all APIs"""
        try:
            # Use the health check endpoint if available, otherwise use base URL
            health_url = getattr(self, 'health_endpoint', self.base_url)
            response = self.session.get(health_url, timeout=self.timeout)
            
            if response.status_code == 200:
                logger.debug(f"✅ {self.__class__.__name__} connection test successful")
                return True
            else:
                logger.warning(f"⚠️ {self.__class__.__name__} connection test failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ {self.__class__.__name__} connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ {self.__class__.__name__} connection test error: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if API is connected - common implementation"""
        return self.test_connection()
    
    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """Abstract method for getting data - must be implemented by subclasses"""
        pass
