#!/usr/bin/env python3
"""
Single Instance Manager
Ensures only one bot instance runs at a time
"""

import os
import sys
import time
import psutil
from typing import Optional, Dict, Any
from loguru import logger
from core.constants import constants


class SingleInstanceManager:
    """Manages single bot instance with PID-based locking"""
    
    def __init__(self, lock_file: str = None):
        self.lock_file = lock_file or constants.LOCK_FILE
        self.lock_acquired = False
        self.current_pid = os.getpid()
        
    def acquire_lock(self) -> bool:
        """Acquire the instance lock"""
        try:
            # Check if lock file exists
            if os.path.exists(self.lock_file):
                # Read existing lock data
                lock_data = self._read_lock_file()
                if lock_data:
                    existing_pid = lock_data.get("pid")
                    if existing_pid and self._is_process_running(existing_pid):
                        # Another instance is still running
                        logger.error(f"❌ Another bot instance is already running (PID: {existing_pid})")
                        logger.error(f"   Lock file: {os.path.abspath(self.lock_file)}")
                        logger.error(f"   Started: {lock_data.get('start_time', 'Unknown')}")
                        logger.error(f"   Strategy: {lock_data.get('strategy', 'Unknown')}")
                        return False
                    else:
                        # Stale lock file - remove it
                        logger.warning(f"⚠️ Removing stale lock file (PID {existing_pid} not running)")
                        self._remove_lock_file()
            
            # Create new lock file
            lock_data = {
                "pid": self.current_pid,
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "strategy": "unknown",  # Will be updated later
                "initial_balance": 0.0,
                "lock_file": os.path.abspath(self.lock_file)
            }
            
            self._write_lock_file(lock_data)
            self.lock_acquired = True
            
            logger.success(f"✅ Bot instance lock acquired (PID: {self.current_pid})")
            logger.info(f"   Lock file: {os.path.abspath(self.lock_file)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to acquire instance lock: {e}")
            return False
    
    def release_lock(self) -> bool:
        """Release the instance lock"""
        try:
            if self.lock_acquired and os.path.exists(self.lock_file):
                # Verify this is our lock file
                lock_data = self._read_lock_file()
                if lock_data and lock_data.get("pid") == self.current_pid:
                    self._remove_lock_file()
                    self.lock_acquired = False
                    logger.success("✅ Bot instance lock released")
                    return True
                else:
                    logger.warning("⚠️ Lock file doesn't belong to this instance")
                    return False
            
            return True  # No lock to release
            
        except Exception as e:
            logger.error(f"❌ Failed to release instance lock: {e}")
            return False
    
    def update_lock_info(self, strategy: str = None, initial_balance: float = None):
        """Update lock file with additional information"""
        try:
            if self.lock_acquired and os.path.exists(self.lock_file):
                lock_data = self._read_lock_file()
                if lock_data and lock_data.get("pid") == self.current_pid:
                    if strategy:
                        lock_data["strategy"] = strategy
                    if initial_balance is not None:
                        lock_data["initial_balance"] = initial_balance
                    
                    self._write_lock_file(lock_data)
                    logger.debug(f"🔄 Updated lock info: strategy={strategy}, balance={initial_balance}")
                    
        except Exception as e:
            logger.debug(f"Could not update lock info: {e}")
    
    def get_running_instance_info(self) -> Optional[Dict[str, Any]]:
        """Get information about currently running instance"""
        try:
            if os.path.exists(self.lock_file):
                lock_data = self._read_lock_file()
                if lock_data:
                    pid = lock_data.get("pid")
                    if pid and self._is_process_running(pid):
                        # Add process information
                        try:
                            process = psutil.Process(pid)
                            lock_data["process_name"] = process.name()
                            lock_data["memory_usage"] = process.memory_info().rss / 1024 / 1024  # MB
                            lock_data["cpu_percent"] = process.cpu_percent()
                            lock_data["status"] = "RUNNING"
                        except psutil.NoSuchProcess:
                            lock_data["status"] = "NOT_FOUND"
                        
                        return lock_data
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting running instance info: {e}")
            return None
    
    def _read_lock_file(self) -> Optional[Dict[str, Any]]:
        """Read lock file data"""
        try:
            with open(self.lock_file, 'r') as f:
                import json
                return json.load(f)
        except Exception:
            return None
    
    def _write_lock_file(self, data: Dict[str, Any]):
        """Write lock file data"""
        with open(self.lock_file, 'w') as f:
            import json
            json.dump(data, f, indent=2)
    
    def _remove_lock_file(self):
        """Remove lock file"""
        try:
            os.remove(self.lock_file)
        except FileNotFoundError:
            pass  # Already removed
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if process with given PID is running"""
        try:
            return psutil.pid_exists(pid)
        except Exception:
            # Fallback method for systems without psutil
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
    
    def __enter__(self):
        """Context manager entry"""
        if self.acquire_lock():
            return self
        else:
            sys.exit(1)  # Exit if cannot acquire lock
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release_lock()


# Global instance manager for easy import
instance_manager = SingleInstanceManager()


def check_single_instance() -> bool:
    """Quick check if another instance is running"""
    temp_manager = SingleInstanceManager()
    running_info = temp_manager.get_running_instance_info()
    
    if running_info:
        logger.error("❌ Another bot instance is already running:")
        logger.error(f"   PID: {running_info.get('pid')}")
        logger.error(f"   Started: {running_info.get('start_time')}")
        logger.error(f"   Strategy: {running_info.get('strategy')}")
        logger.error(f"   Balance: ${running_info.get('initial_balance', 0):.2f}")
        logger.error("   Please stop the existing instance first.")
        return False
    
    return True


def force_cleanup_lock():
    """Force cleanup of stale lock files (use with caution)"""
    temp_manager = SingleInstanceManager()
    if os.path.exists(temp_manager.lock_file):
        temp_manager._remove_lock_file()
        logger.warning("⚠️ Forced cleanup of lock file")
    else:
        logger.info("✅ No lock file to cleanup")