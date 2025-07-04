from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import (
    get_session_count,
    run_report,  # outil générique pour runReport
)
from utils.token_handler import check_and_refresh_token
import asyncio

mcp = FastMCP("GA4FullToolset", host="0.0.0.0", port=8000, debug=True)

async def _prepare_tokens(userId):
    tokens = get_user_tokens(userId)
    if not tokens:
        raise ValueError(f"No credentials found for userId: {userId}")
    return await check_and_refresh_token(userId, tokens)

def _make_date_ranges(startDate, endDate):
    return [{"startDate": startDate, "endDate": endDate}]

def _prop_str(ga4PropertyId):
    return f"properties/{ga4PropertyId}"

@mcp.tool()
async def get_sessions(userId: str = None, ga4PropertyId: str = None, webhookData: dict = None) -> dict:
    # … (votre code existant) …

@mcp.tool()
async def get_sessions_simple(userId: str, ga4PropertyId: str) -> dict:
    # … (votre code existant) …

# ——————————————————————————————————————————————
# Nouveaux outils GA4
# ——————————————————————————————————————————————

@mcp.tool()
async def get_page_views(
    userId: str,
    ga4PropertyId: str,
    startDate: str,
    endDate: str,
    dimensions: list[str] = None
) -> dict:
    """
    Récupère les page views (screenPageViews) pour une plage de dates.
    dimensions par défaut ["pagePath"].
    """
    if not userId or not ga4PropertyId:
        return {"error": "userId et ga4PropertyId requis"}
    if not startDate or not endDate:
        return {"error": "startDate et endDate requis au format YYYY-MM-DD"}

    dimensions = dimensions or ["pagePath"]
    try:
        tokens = await _prepare_tokens(userId)
        date_ranges = _make_date_ranges(startDate, endDate)
        response = await run_report(
            tokens["access_token"],
            _prop_str(ga4PropertyId),
            date_ranges,
            [{"name": d} for d in dimensions],
            [{"name": "screenPageViews"}]
        )
        return {"message": "Page views récupérées", "data": response}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_active_users(
    userId: str,
    ga4PropertyId: str,
    startDate: str,
    endDate: str
) -> dict:
    """
    Récupère activeUsers et newUsers par date.
    """
    if not all([userId, ga4PropertyId, startDate, endDate]):
        return {"error": "userId, ga4PropertyId, startDate et endDate requis"}

    try:
        tokens = await _prepare_tokens(userId)
        date_ranges = _make_date_ranges(startDate, endDate)
        response = await run_report(
            tokens["access_token"],
            _prop_str(ga4PropertyId),
            date_ranges,
            [{"name": "date"}],
            [{"name": "activeUsers"}, {"name": "newUsers"}]
        )
        return {"message": "Active users récupérés", "data": response}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_events(
    userId: str,
    ga4PropertyId: str,
    startDate: str,
    endDate: str,
    eventName: str = None
) -> dict:
    """
    Récupère eventCount pour chaque eventName et date.
    Si eventName est fourni, filtre sur cet événement.
    """
    if not all([userId, ga4PropertyId, startDate, endDate]):
        return {"error": "userId, ga4PropertyId, startDate et endDate requis"}

    try:
        tokens = await _prepare_tokens(userId)
        date_ranges = _make_date_ranges(startDate, endDate)
        dim_filter = None
        if eventName:
            dim_filter = {
                "filter": {
                    "fieldName": "eventName",
                    "stringFilter": {"value": eventName}
                }
            }
        response = await run_report(
            tokens["access_token"],
            _prop_str(ga4PropertyId),
            date_ranges,
            [{"name": "eventName"}, {"name": "date"}],
            [{"name": "eventCount"}],
            dimension_filter=dim_filter
        )
        return {"message": "Events récupérés", "data": response}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_user_behavior(
    userId: str,
    ga4PropertyId: str,
    startDate: str,
    endDate: str
) -> dict:
    """
    Récupère averageSessionDuration, bounceRate et sessionsPerUser par date.
    """
    if not all([userId, ga4PropertyId, startDate, endDate]):
        return {"error": "userId, ga4PropertyId, startDate et endDate requis"}

    try:
        tokens = await _prepare_tokens(userId)
        date_ranges = _make_date_ranges(startDate, endDate)
        response = await run_report(
            tokens["access_token"],
            _prop_str(ga4PropertyId),
            date_ranges,
            [{"name": "date"}],
            [
                {"name": "averageSessionDuration"},
                {"name": "bounceRate"},
                {"name": "sessionsPerUser"}
            ]
        )
        return {"message": "User behavior récupéré", "data": response}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run(transport="sse")
