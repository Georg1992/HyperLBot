#!/usr/bin/env python3
"""
Complete diagnostic script to trace data flow from bot to dashboard
"""

from loguru import logger
import time
import json

def test_complete_data_flow():
    """Test complete data flow from real-time manager to dashboard"""
    logger.info("🔍 COMPLETE DASHBOARD DATA FLOW DIAGNOSTIC")
    logger.info("=" * 60)
    
    try:
        # Step 1: Check real-time data manager
        logger.info("📊 STEP 1: Testing Real-Time Data Manager")
        from core.realtime_data_manager import trading_data_manager
        
        # Start a test session
        session_id = trading_data_manager.start_session("diagnostic", 120.0, "debug_test")
        logger.success(f"✅ Session started: {session_id}")
        
        # Add test data to RTM
        trading_data_manager.add_activity({
            "source": "diagnostic",
            "message": "🔍 Diagnostic test activity - this should appear in dashboard",
            "level": "INFO"
        })
        
        trading_data_manager.update_market_data({
            "current_price": 97500.0,
            "trend": "BULLISH",
            "rsi": 65.0,
            "volume_depth": 1500000.0
        })
        
        trading_data_manager.update_predictions([{
            "prediction_type": "DIAGNOSTIC_TEST",
            "direction": "UP",
            "confidence": 85.0,
            "timestamp": time.time(),
            "reasoning": "Diagnostic test prediction"
        }])
        
        logger.success("✅ Test data added to RTM")
        
        # Step 2: Check RTM data retrieval
        logger.info("📊 STEP 2: Testing RTM Data Retrieval")
        current_state = trading_data_manager.get_current_state()
        
        session_info = current_state["session"]
        activity_count = len(current_state.get("recent_activity", []))
        predictions_count = len(current_state.get("predictions", []))
        market_data = current_state.get("market", {})
        
        logger.info(f"📊 Session: {session_info['session_id']} - Status: {session_info['status']}")
        logger.info(f"📊 Activities: {activity_count}")
        logger.info(f"📊 Predictions: {predictions_count}")
        logger.info(f"📊 Market Data: Price=${market_data.get('current_price', 'N/A')}, RSI={market_data.get('rsi', 'N/A')}")
        
        if activity_count > 0:
            latest_activity = current_state["recent_activity"][-1]
            logger.info(f"📊 Latest Activity: {latest_activity.get('message', 'No message')}")
        
        # Step 3: Test Dashboard Data Method
        logger.info("📊 STEP 3: Testing Dashboard Data Method")
        from realtime_dashboard import create_dashboard
        
        dashboard = create_dashboard()
        logger.success("✅ Dashboard instance created")
        
        dashboard_data = dashboard._get_dashboard_data()
        
        dash_session = dashboard_data.get("session", {})
        dash_logs = dashboard_data.get("logs", [])
        dash_predictions = dashboard_data.get("predictions", [])
        dash_market = dashboard_data.get("market", {})
        
        logger.info(f"📊 Dashboard Session: {dash_session.get('session_id', 'N/A')} - Status: {dash_session.get('status', 'N/A')}")
        logger.info(f"📊 Dashboard Logs: {len(dash_logs)} entries")
        logger.info(f"📊 Dashboard Predictions: {len(dash_predictions)} entries")
        logger.info(f"📊 Dashboard Market: Price=${dash_market.get('current_price', 'N/A')}")
        
        if len(dash_logs) > 0:
            logger.info(f"📊 Dashboard Latest Log: {dash_logs[-1].get('message', 'No message')}")
        else:
            logger.error("❌ Dashboard has NO activity logs!")
            
        # Step 4: Check if data matches
        logger.info("📊 STEP 4: Data Consistency Check")
        
        rtm_session_id = session_info.get("session_id", "")
        dash_session_id = dash_session.get("session_id", "")
        
        if rtm_session_id == dash_session_id:
            logger.success(f"✅ Session IDs match: {rtm_session_id}")
        else:
            logger.error(f"❌ Session ID mismatch! RTM: {rtm_session_id}, Dashboard: {dash_session_id}")
            
        if activity_count == len(dash_logs):
            logger.success(f"✅ Activity counts match: {activity_count}")
        else:
            logger.error(f"❌ Activity count mismatch! RTM: {activity_count}, Dashboard: {len(dash_logs)}")
            
        if predictions_count == len(dash_predictions):
            logger.success(f"✅ Prediction counts match: {predictions_count}")
        else:
            logger.error(f"❌ Prediction count mismatch! RTM: {predictions_count}, Dashboard: {len(dash_predictions)}")
        
        # Step 5: Test WebSocket emission (simulation)
        logger.info("📊 STEP 5: Testing WebSocket Data Preparation")
        
        # Simulate what gets sent via WebSocket
        websocket_data = {
            "session": dash_session,
            "logs": dash_logs,
            "predictions": dash_predictions,
            "market": dash_market,
            "timestamp": dashboard_data.get("timestamp"),
            "data_source": dashboard_data.get("data_source"),
            "connection_status": dashboard_data.get("connection_status")
        }
        
        logger.info(f"📊 WebSocket data ready:")
        logger.info(f"   Session Status: {websocket_data['session'].get('status', 'N/A')}")
        logger.info(f"   Session Time: {websocket_data['session'].get('session_time', 'N/A')}")
        logger.info(f"   Logs Count: {len(websocket_data['logs'])}")
        logger.info(f"   Predictions Count: {len(websocket_data['predictions'])}")
        logger.info(f"   Data Source: {websocket_data.get('data_source', 'N/A')}")
        logger.info(f"   Connection Status: {websocket_data.get('connection_status', 'N/A')}")
        
        # Step 6: Detailed JSON output for debugging
        logger.info("📊 STEP 6: Detailed Data Dump")
        
        logger.info("🔍 FULL SESSION DATA:")
        logger.info(json.dumps(dash_session, indent=2, default=str))
        
        logger.info("🔍 FULL LOGS DATA:")
        logger.info(json.dumps(dash_logs, indent=2, default=str))
        
        logger.info("🔍 FULL PREDICTIONS DATA:")
        logger.info(json.dumps(dash_predictions, indent=2, default=str))
        
        # End session
        trading_data_manager.end_session()
        logger.info("🏁 Diagnostic session ended")
        
        # Final summary
        logger.info("📊 DIAGNOSTIC SUMMARY:")
        logger.info("=" * 60)
        
        if activity_count > 0 and len(dash_logs) > 0:
            logger.success("✅ Real-time activity data is flowing correctly")
        else:
            logger.error("❌ Real-time activity data is NOT flowing")
            
        if predictions_count > 0 and len(dash_predictions) > 0:
            logger.success("✅ Predictions data is flowing correctly")
        else:
            logger.error("❌ Predictions data is NOT flowing")
            
        if dash_market.get("current_price"):
            logger.success("✅ Market data is flowing correctly")
        else:
            logger.error("❌ Market data is NOT flowing")
        
    except Exception as e:
        logger.error(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complete_data_flow()