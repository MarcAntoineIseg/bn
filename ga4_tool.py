from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import get_session_count
from utils.token_handler import check_and_refresh_token
import asyncio

mcp = FastMCP("GA4SessionTool", host="0.0.0.0", port=8000, debug=True)

@mcp.tool()
async def get_sessions(userId: str, ga4PropertyId: str) -> dict:
    """
    Fetch GA4 session count for the last 30 days.
    
    Args:
        userId (str): The user's unique identifier for token lookup
        ga4PropertyId (str): The Google Analytics 4 property ID (e.g., "123456789")
    
    Returns:
        dict: Session count data or error message
    """
    
    # Validate required parameters
    if not userId:
        return {"error": "Missing userId parameter - please provide your user ID"}
    
    if not ga4PropertyId:
        return {"error": "Missing ga4PropertyId parameter - please provide your GA4 property ID"}
    
    # Create googleAnalyticsData structure from the property ID
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

if __name__ == "__main__":
    mcp.run(transport="sse")
