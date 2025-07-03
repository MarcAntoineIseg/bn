from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import get_session_count
from utils.token_handler import check_and_refresh_token
import asyncio
import json

mcp = FastMCP("GA4SessionTool", host="0.0.0.0", port=8000, debug=True)

@mcp.tool()
async def get_sessions(**kwargs) -> dict:
    """
    Fetch GA4 session count for the last 30 days.
    This debug version accepts any parameters to see what n8n sends.
    """
    # Log everything we receive
    debug_info = {
        "received_kwargs": kwargs,
        "kwargs_keys": list(kwargs.keys()),
        "kwargs_types": {k: type(v).__name__ for k, v in kwargs.items()}
    }
    
    print(f"DEBUG: Received from n8n: {json.dumps(debug_info, indent=2)}")
    
    # Try to extract userId and googleAnalyticsData from whatever n8n sends
    userId = None
    googleAnalyticsData = None
    
    # Check common ways n8n might pass data
    if 'userId' in kwargs:
        userId = kwargs['userId']
    elif 'user_id' in kwargs:
        userId = kwargs['user_id']
    elif 'id' in kwargs:
        userId = kwargs['id']
    
    if 'googleAnalyticsData' in kwargs:
        googleAnalyticsData = kwargs['googleAnalyticsData']
    elif 'google_analytics_data' in kwargs:
        googleAnalyticsData = kwargs['google_analytics_data']
    elif 'analyticsData' in kwargs:
        googleAnalyticsData = kwargs['analyticsData']
    elif 'data' in kwargs:
        googleAnalyticsData = kwargs['data']
    
    # Return debug info for now
    return {
        "debug": True,
        "message": "Debug mode - showing what n8n sent",
        "received_data": debug_info,
        "extracted_userId": userId,
        "extracted_googleAnalyticsData": googleAnalyticsData
    }

@mcp.tool()
async def get_sessions_working(userId: str, googleAnalyticsData: dict) -> dict:
    """
    The actual working version - use this once we know the parameter names.
    """
    if not userId:
        return {"error": "Missing userId"}
    if not googleAnalyticsData:
        return {"error": "Missing googleAnalyticsData"}
    
    property_id = googleAnalyticsData.get("selectedProperty", {}).get("id")
    if not property_id:
        return {"error": "Missing GA4 property ID in googleAnalyticsData.selectedProperty.id"}
    
    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": "No credentials found for this userId"}
    
    try:
        tokens = await check_and_refresh_token(userId, tokens)
    except Exception as e:
        return {"error": f"Token refresh failed: {str(e)}"}
    
    try:
        result = await get_session_count(tokens["access_token"], property_id)
        if result["value"] == "0":
            return {"message": "No sessions found", "data": result}
        return {"message": "Session count retrieved", "data": result}
    except Exception as e:
        return {"error": f"Google Analytics API error: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="sse")
