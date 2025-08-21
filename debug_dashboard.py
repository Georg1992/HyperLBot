#!/usr/bin/env python3
"""
Debug version of HyperLBot Dashboard
"""

import os
import json
from datetime import datetime
from loguru import logger

def debug_session_data():
    """Debug session data reading"""
    try:
        log_dir = "hybrid_paper_trading_logs"
        logger.info(f"Checking log directory: {log_dir}")
        logger.info(f"Directory exists: {os.path.exists(log_dir)}")
        
        if os.path.exists(log_dir):
            files = os.listdir(log_dir)
            logger.info(f"Files in directory: {files}")
            
            session_files = [f for f in files if f.startswith("session_metadata_")]
            logger.info(f"Session files found: {session_files}")
            
            if session_files:
                latest_session = max(session_files)
                logger.info(f"Latest session file: {latest_session}")
                
                session_path = os.path.join(log_dir, latest_session)
                logger.info(f"Session path: {session_path}")
                
                with open(session_path, 'r') as f:
                    session_data = json.load(f)
                    logger.info(f"Session data: {session_data}")
                    
    except Exception as e:
        logger.error(f"Error in debug_session_data: {e}")

def debug_market_data():
    """Debug market data reading"""
    try:
        log_dir = "hybrid_paper_trading_logs"
        analysis_dir = os.path.join(log_dir, "analysis")
        logger.info(f"Analysis directory: {analysis_dir}")
        logger.info(f"Directory exists: {os.path.exists(analysis_dir)}")
        
        if os.path.exists(analysis_dir):
            files = os.listdir(analysis_dir)
            logger.info(f"Analysis files: {files}")
            
            analysis_files = [f for f in files if f.endswith('.json')]
            if analysis_files:
                latest_analysis = max(analysis_files)
                logger.info(f"Latest analysis file: {latest_analysis}")
                
                analysis_path = os.path.join(analysis_dir, latest_analysis)
                with open(analysis_path, 'r') as f:
                    analysis_data = json.load(f)
                    logger.info(f"Analysis data length: {len(analysis_data)}")
                    
                    if analysis_data:
                        latest = analysis_data[-1]
                        logger.info(f"Latest analysis entry: {latest}")
                        
                        trend_analysis = latest.get("trend_analysis", {})
                        logger.info(f"Trend analysis: {trend_analysis}")
                        
    except Exception as e:
        logger.error(f"Error in debug_market_data: {e}")

if __name__ == "__main__":
    logger.info("🔍 Debugging dashboard data reading...")
    debug_session_data()
    debug_market_data()
