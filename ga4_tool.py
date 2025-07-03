from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import get_session_count
from utils.token_handler import check_and_refresh_token
import asyncio

mcp = FastMCP("GA4SessionTool",host="0.0.0.0",port=8000)

@mcp.tool()
async def get_sessions(userId: str, googleAnalyticsData: dict) -> dict:
    """Fetch GA4 session count for the last 30 days."""
    if not userId or not googleAnalyticsData:
        return {"error": "Missing userId or googleAnalyticsData"}

    property_id = googleAnalyticsData.get("selectedProperty", {}).get("id")
    if not property_id:
        return {"error": "Missing GA4 property ID"}

    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": "No credentials found for this user"}

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
