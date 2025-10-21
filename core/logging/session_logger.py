#!/usr/bin/env python3
"""
Session Logger
Handles comprehensive logging infrastructure for trading sessions
Single Responsibility: Logging configuration and management
"""

import os
import sys
from datetime import datetime
from loguru import logger

class SessionLogger:
    """Manages session logging infrastructure"""
    
    def __init__(self):
        self.log_file = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup comprehensive logging infrastructure"""
        # Create logs/sessions directory if it doesn't exist
        os.makedirs("logs/sessions", exist_ok=True)
        
        # Generate session log filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/sessions/bot_session_{timestamp}.log"
        
        # Remove default handler and add custom ones
        logger.remove()
        
        # Add console handler
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"
        )
        
        # Add file handler for session logs
        logger.add(
            self.log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="100 MB",
            retention="3 sessions"  # Keep only last 3 sessions
        )
        
        # Log startup message
        logger.info(f"🚀 Starting HyperLBot with logging to: {self.log_file}")
    
    def get_log_file(self):
        """Get current log file path"""
        return self.log_file
    
    def log_session_end(self):
        """Log session end message"""
        logger.info(f"📄 Session log saved to: logs/sessions/")

# Global session logger instance
_session_logger = None

def get_session_logger():
    """Get global session logger instance"""
    global _session_logger
    if _session_logger is None:
        _session_logger = SessionLogger()
    return _session_logger
