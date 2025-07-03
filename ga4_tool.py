from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import get_session_count
from utils.token_handler import check_and_refresh_token
import asyncio
import json
import os

mcp = FastMCP("GA4SessionTool", host="0.0.0.0", port=8000, debug=True)

@mcp.tool()
async def get_sessions(kwargs: str = "") -> dict:
    """
    Fetch GA4 session count for the last 30 days.
    
    This tool expects to receive user context and analytics data from n8n workflow.
    The data should be available through n8n's workflow context or environment variables.
    """
    
    # Since n8n is sending empty kwargs, we need to get data from other sources
    # Let's try multiple approaches to get the required data
    
    # Approach 1: Try to parse kwargs if it contains JSON
    userId = None
    googleAnalyticsData = None
    
    if kwargs and kwargs.strip():
        try:
            data = json.loads(kwargs)
            userId = data.get('userId')
            googleAnalyticsData = data.get('googleAnalyticsData')
        except:
            pass
    
    # Approach 2: Check environment variables (n8n might set these)
    if not userId:
        userId = os.environ.get('N8N_USER_ID') or os.environ.get('USER_ID') or os.environ.get('USERID')
    
    # Approach 3: Use a hardcoded test user ID for now (REMOVE THIS IN PRODUCTION)
    if not userId:
        # You need to replace this with actual user identification logic
        userId = "test_user_id"  # TEMPORARY - replace with actual logic
    
    # Approach 4: Try to get GA4 property from environment or config
    if not googleAnalyticsData:
        property_id = os.environ.get('GA4_PROPERTY_ID')
        if property_id:
            googleAnalyticsData = {
                "selectedProperty": {
                    "id": property_id
                }
            }
    
    # If still no data, return instructions for setup
    if not userId or not googleAnalyticsData:
        return {
            "error": "Missing required data",
            "instructions": {
                "message": "Please provide userId and googleAnalyticsData",
                "received_kwargs": kwargs,
                "solutions": [
                    "Set N8N_USER_ID environment variable",
                    "Set GA4_PROPERTY_ID environment variable", 
                    "Or modify the n8n workflow to pass data correctly"
                ]
            }
        }
    
    # Extract property ID
    property_id = googleAnalyticsData.get("selectedProperty", {}).get("id")
    if not property_id:
        return {"error": "Missing GA4 property ID in googleAnalyticsData.selectedProperty.id"}
    
    # Get user tokens
    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": f"No credentials found for userId: {userId}"}
    
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

# Alternative tool that expects n8n to pass data differently
@mcp.tool()
async def get_sessions_with_params(userId: str, propertyId: str) -> dict:
    """
    Fetch GA4 session count with explicit parameters.
    
    Args:
        userId: User identifier for token lookup
        propertyId: GA4 property ID (e.g., "123456789")
    """
    if not userId:
        return {"error": "Missing userId parameter"}
    if not propertyId:
        return {"error": "Missing propertyId parameter"}
    
    # Create googleAnalyticsData structure
    googleAnalyticsData = {
        "selectedProperty": {
            "id": propertyId
        }
    }
    
    # Get user tokens
    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": f"No credentials found for userId: {userId}"}
    
    try:
        tokens = await check_and_refresh_token(userId, tokens)
    except Exception as e:
        return {"error": f"Token refresh failed: {str(e)}"}
    
    try:
        result = await get_session_count(tokens["access_token"], propertyId)
        if result["value"] == "0":
            return {"message": "No sessions found", "data": result}
        return {"message": "Session count retrieved", "data": result}
    except Exception as e:
        return {"error": f"Google Analytics API error: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="sse")
