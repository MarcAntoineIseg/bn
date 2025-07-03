from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import get_session_count
from utils.token_handler import check_and_refresh_token
import asyncio

mcp = FastMCP("GA4SessionTool", host="0.0.0.0", port=8000, debug=True)

@mcp.tool()
async def get_sessions(userId: str = None, ga4PropertyId: str = None, webhookData: dict = None) -> dict:
    """
    Fetch GA4 session count for the last 30 days.
    
    Args:
        userId (str, optional): The user's unique identifier
        ga4PropertyId (str, optional): The Google Analytics 4 property ID
        webhookData (dict, optional): Complete webhook data containing userId and GA4 info
    
    Returns:
        dict: Session count data or error message
    """
    
    # Try to extract data from webhookData if provided
    if webhookData and isinstance(webhookData, dict):
        if not userId:
            userId = webhookData.get('userId')
        if not ga4PropertyId:
            ga4_data = webhookData.get('googleAnalyticsData', {})
            selected_property = ga4_data.get('selectedProperty', {})
            ga4PropertyId = selected_property.get('id')
    
    # Validate required parameters
    if not userId:
        return {"error": "Missing userId - please provide user ID or webhook data"}
    
    if not ga4PropertyId:
        return {"error": "Missing ga4PropertyId - please provide GA4 property ID or webhook data"}
    
    # Create googleAnalyticsData structure
    googleAnalyticsData = {
        "selectedProperty": {
            "id": ga4PropertyId
        }
    }
    
    # Get user tokens from Supabase
    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": f"No credentials found for userId: {userId}"}
    
    # Refresh tokens if needed
    try:
        tokens = await check_and_refresh_token(userId, tokens)
    except Exception as e:
        return {"error": f"Token refresh failed: {str(e)}"}
    
    # Get session count from GA4
    try:
        result = await get_session_count(tokens["access_token"], ga4PropertyId)
        if result["value"] == "0":
            return {"message": "No sessions found", "data": result}
        return {"message": "Session count retrieved", "data": result}
    except Exception as e:
        return {"error": f"Google Analytics API error: {str(e)}"}

# Alternative: Simple tool that works with individual parameters
@mcp.tool()
async def get_sessions_simple(userId: str, ga4PropertyId: str) -> dict:
    """
    Fetch GA4 session count for the last 30 days.
    
    Args:
        userId (str): User ID: a164089e-e8a6-423f-a29e-e129b38bd851
        ga4PropertyId (str): GA4 Property ID: 391870620
    
    Returns:
        dict: Session count data or error message
    """
    
    # Validate required parameters
    if not userId:
        return {"error": "Missing userId parameter"}
    
    if not ga4PropertyId:
        return {"error": "Missing ga4PropertyId parameter"}
    
    # Get user tokens from Supabase
    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": f"No credentials found for userId: {userId}"}
    
    # Refresh tokens if needed
    try:
        tokens = await check_and_refresh_token(userId, tokens)
    except Exception as e:
        return {"error": f"Token refresh failed: {str(e)}"}
    
    # Get session count from GA4
    try:
        result = await get_session_count(tokens["access_token"], ga4PropertyId)
        if result["value"] == "0":
            return {"message": "No sessions found", "data": result}
        return {"message": "Session count retrieved", "data": result}
    except Exception as e:
        return {"error": f"Google Analytics API error: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="sse")
