#!/usr/bin/env python3
"""
Test script for HyperLBot Dashboard
"""

import requests
import json
from loguru import logger

def test_dashboard():
    """Test the dashboard endpoints"""
    base_url = "http://localhost:5000"
    
    try:
        # Test main page
        logger.info("Testing main dashboard page...")
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            logger.success("✅ Main dashboard page is working")
        else:
            logger.error(f"❌ Main page failed: {response.status_code}")
            
        # Test API status
        logger.info("Testing API status endpoint...")
        response = requests.get(f"{base_url}/api/status")
        if response.status_code == 200:
            data = response.json()
            logger.success("✅ API status endpoint is working")
            logger.info(f"📊 Session data: {len(data.get('session', {}))} fields")
            logger.info(f"📈 Market data: {len(data.get('market', {}))} fields")
            logger.info(f"📝 Log entries: {len(data.get('logs', []))} entries")
            logger.info(f"💰 Summary data: {len(data.get('summary', {}))} fields")
        else:
            logger.error(f"❌ API status failed: {response.status_code}")
            
        # Test logs endpoint
        logger.info("Testing logs endpoint...")
        response = requests.get(f"{base_url}/api/logs")
        if response.status_code == 200:
            data = response.json()
            logger.success("✅ Logs endpoint is working")
            logger.info(f"📝 Found {len(data)} log entries")
        else:
            logger.error(f"❌ Logs endpoint failed: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to dashboard. Is it running?")
        logger.info("💡 Start the dashboard with: python launch_dashboard.py")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_dashboard()
