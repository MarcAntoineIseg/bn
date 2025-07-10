from fastmcp import FastMCP
from models import GA4QueryInput, BasicQueryInput
from ga4_service import get_ga4_data, list_ga4_dimensions, list_ga4_metrics
from utils import get_date_suggestions
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP("GA4 Analytics MCP Server")

@mcp.tool()
async def query_ga4_data(input: GA4QueryInput) -> dict:
    """
    Query Google Analytics 4 data with specific dimensions and metrics.
    
    This function retrieves GA4 data for a specific user and date range.
    
    Common GA4 dimensions include:
    - date: The date of the session
    - country: The country of the user
    - city: The city of the user
    - deviceCategory: The device category (desktop, mobile, tablet)
    - pagePath: The page path
    - source: The traffic source
    - medium: The traffic medium
    - campaign: The campaign name
    
    Common GA4 metrics include:
    - sessions: Number of sessions
    - users: Number of users
    - pageviews: Number of pageviews
    - bounceRate: Bounce rate percentage
    - sessionDuration: Average session duration
    - conversions: Number of conversions
    - revenue: Revenue amount
    
    Example usage:
    - For daily sessions: dimensions=["date"], metrics=["sessions"]
    - For traffic by country: dimensions=["country"], metrics=["users", "sessions"]
    - For page performance: dimensions=["pagePath"], metrics=["pageviews", "users"]
    """
    try:
        logger.info(f"Querying GA4 data for user: {input.user_id}")
        logger.info(f"Dimensions: {input.dimensions}, Metrics: {input.metrics}")
        logger.info(f"Date range: {input.start_date} to {input.end_date}")
        
        result = await get_ga4_data(input)
        
        logger.info(f"Query result success: {result.get('success', False)}")
        if not result.get('success', False):
            logger.error(f"Query failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in query_ga4_data: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": f"Tool execution error: {str(e)}",
            "data": [],
            "rowCount": 0
        }

@mcp.tool()
async def get_available_dimensions(input: BasicQueryInput) -> dict:
    """
    List all available GA4 dimensions for the user's property.
    
    This helps you understand what dimensions are available for analysis.
    Dimensions are attributes of your data (like date, country, page path, etc.).
    
    Use this when you need to know what dimensions you can use in your queries.
    """
    try:
        logger.info(f"Getting available dimensions for user: {input.user_id}")
        result = await list_ga4_dimensions(input)
        logger.info(f"Dimensions query success: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Error in get_available_dimensions: {str(e)}")
        return {
            "success": False,
            "error": f"Tool execution error: {str(e)}",
            "dimensions": [],
            "count": 0
        }

@mcp.tool()
async def get_available_metrics(input: BasicQueryInput) -> dict:
    """
    List all available GA4 metrics for the user's property.
    
    This helps you understand what metrics are available for analysis.
    Metrics are quantitative measurements (like sessions, users, pageviews, etc.).
    
    Use this when you need to know what metrics you can use in your queries.
    """
    try:
        logger.info(f"Getting available metrics for user: {input.user_id}")
        result = await list_ga4_metrics(input)
        logger.info(f"Metrics query success: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Error in get_available_metrics: {str(e)}")
        return {
            "success": False,
            "error": f"Tool execution error: {str(e)}",
            "metrics": [],
            "count": 0
        }

@mcp.tool()
async def get_common_date_ranges() -> dict:
    """
    Get common date range suggestions for GA4 queries.
    
    This provides pre-calculated date ranges that are commonly used in analytics.
    Use this to help convert relative date expressions into specific dates.
    """
    try:
        logger.info("Getting common date ranges")
        result = get_date_suggestions()
        logger.info("Date ranges retrieved successfully")
        return result
    except Exception as e:
        logger.error(f"Error in get_common_date_ranges: {str(e)}")
        return {
            "success": False,
            "error": f"Tool execution error: {str(e)}",
            "dateRanges": {},
            "currentDate": None
        }

if __name__ == "__main__":
    print("Starting GA4 MCP Server for N8N AI Agent...")
    print("Available tools:")
    print("1. query_ga4_data - Query GA4 data with specific parameters")
    print("2. get_available_dimensions - List available dimensions")
    print("3. get_available_metrics - List available metrics")
    print("4. get_common_date_ranges - Get common date range suggestions")
    print("Server ready for AI agent integration!")
    
    # Use SSE transport for MCP server
    mcp.run(transport="sse", host="0.0.0.0", port=8000)