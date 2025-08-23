#!/usr/bin/env python3
"""
Quick check of what real-time manager is currently returning
"""

from loguru import logger

def check_current_session():
    """Check what RTM is currently returning"""
    logger.info("🔍 CHECKING CURRENT RTM SESSION STATE")
    logger.info("=" * 50)
    
    try:
        from core.realtime_data_manager import trading_data_manager
        
        # Get current state
        current_state = trading_data_manager.get_current_state()
        session = current_state["session"]
        
        logger.info("📊 CURRENT RTM SESSION:")
        logger.info(f"   Session ID: {session.get('session_id', 'N/A')}")
        logger.info(f"   Status: {session.get('status', 'N/A')}")
        logger.info(f"   Start Time: {session.get('start_time', 'N/A')}")
        logger.info(f"   Strategy: {session.get('strategy', 'N/A')}")
        logger.info(f"   Current Balance: ${session.get('current_balance', 0)}")
        
        # Check activities
        activities = current_state.get("recent_activity", [])
        logger.info(f"📊 ACTIVITIES: {len(activities)} entries")
        if activities:
            latest = activities[-1]
            logger.info(f"   Latest: {latest.get('message', 'No message')}")
        
        # Check predictions  
        predictions = current_state.get("predictions", [])
        logger.info(f"📊 PREDICTIONS: {len(predictions)} entries")
        if predictions:
            latest = predictions[0]
            logger.info(f"   Latest: {latest.get('prediction_type', 'N/A')} - {latest.get('direction', 'N/A')} ({latest.get('confidence', 0)}%)")
        
        # Now test dashboard
        logger.info("📊 TESTING DASHBOARD DATA METHOD:")
        from realtime_dashboard import create_dashboard
        
        dashboard = create_dashboard()
        dashboard_data = dashboard._get_dashboard_data()
        
        dash_session = dashboard_data.get("session", {})
        logger.info(f"📊 DASHBOARD SESSION:")
        logger.info(f"   Session ID: {dash_session.get('session_id', 'N/A')}")
        logger.info(f"   Status: {dash_session.get('status', 'N/A')}")
        logger.info(f"   Session Time: {dash_session.get('session_time', 'N/A')}")
        logger.info(f"   Data Source: {dashboard_data.get('data_source', 'N/A')}")
        logger.info(f"   Connection Status: {dashboard_data.get('connection_status', 'N/A')}")
        
        # Compare
        rtm_session_id = session.get('session_id', '')
        dash_session_id = dash_session.get('session_id', '')
        rtm_status = session.get('status', '')
        dash_status = dash_session.get('status', '')
        
        logger.info("📊 COMPARISON:")
        if rtm_session_id == dash_session_id:
            logger.success(f"✅ Session IDs match: {rtm_session_id}")
        else:
            logger.error(f"❌ Session ID mismatch! RTM: {rtm_session_id} vs Dashboard: {dash_session_id}")
            
        if rtm_status == dash_status:
            logger.success(f"✅ Status match: {rtm_status}")
        else:
            logger.error(f"❌ Status mismatch! RTM: {rtm_status} vs Dashboard: {dash_status}")
            
    except Exception as e:
        logger.error(f"❌ Check failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_current_session()