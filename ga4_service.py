from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric, GetMetadataRequest, FilterExpression, Filter
from models import GA4QueryInput, BasicQueryInput
from database import get_user_credentials
from auth import always_refresh_user_tokens
import logging
import traceback

logger = logging.getLogger(__name__)

def parse_simple_filters(filter_dict: dict) -> FilterExpression:
    """
    Converts a dict like {"field_name": "value"} to a GA4 FilterExpression
    """
    expressions = []
    for key, value in filter_dict.items():
        expressions.append(
            FilterExpression(
                filter=Filter(
                    field_name=key,
                    string_filter=Filter.StringFilter(value=value)
                )
            )
        )
    
    if len(expressions) == 1:
        return expressions[0]
    
    return FilterExpression(
        and_group={"expressions": expressions}
    )

def build_filter_expression(filters: dict) -> FilterExpression | None:
    """
    Build a proper FilterExpression from the input filters
    """
    if not filters:
        return None
    
    # Check if it's already a properly structured filter expression
    if "dimension_filter" in filters:
        # Handle the nested structure from your query
        filter_config = filters["dimension_filter"]
        if "filter" in filter_config:
            filter_def = filter_config["filter"]
            return FilterExpression(
                filter=Filter(
                    field_name=filter_def["field_name"],
                    string_filter=Filter.StringFilter(value=filter_def["string_filter"]["value"])
                )
            )
    
    # Handle direct filter specification
    if "filter" in filters:
        filter_def = filters["filter"]
        return FilterExpression(
            filter=Filter(
                field_name=filter_def["field_name"],
                string_filter=Filter.StringFilter(value=filter_def["string_filter"]["value"])
            )
        )
    
    # Handle simple key-value filters
    return parse_simple_filters(filters)

async def get_ga4_data(input: GA4QueryInput) -> dict:
    """
    Query Google Analytics 4 data with specific dimensions and metrics.
    """
    try:
        logger.info(f"Starting GA4 data query for user: {input.user_id}")
        
        # Get user credentials
        try:
            refresh_token, property_id = get_user_credentials(input.user_id)
            logger.info(f"Retrieved credentials for user {input.user_id}, property: {property_id}")
        except Exception as e:
            logger.error(f"Failed to get user credentials: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to retrieve user credentials: {str(e)}",
                "data": [],
                "rowCount": 0
            }
        
        # Override property ID if provided
        if input.property_id:
            property_id = input.property_id
            logger.info(f"Using override property ID: {property_id}")
        
        # Refresh tokens
        try:
            creds = always_refresh_user_tokens(refresh_token)
            logger.info("Successfully refreshed user tokens")
        except Exception as e:
            logger.error(f"Failed to refresh tokens: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to refresh authentication tokens: {str(e)}",
                "data": [],
                "rowCount": 0
            }
        
        # Create GA4 client
        try:
            client = BetaAnalyticsDataClient(credentials=creds)
            logger.info("Created GA4 client successfully")
        except Exception as e:
            logger.error(f"Failed to create GA4 client: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create GA4 client: {str(e)}",
                "data": [],
                "rowCount": 0
            }
        
        # Validate inputs
        if not input.dimensions and not input.metrics:
            return {
                "success": False,
                "error": "At least one dimension or metric must be specified",
                "data": [],
                "rowCount": 0
            }
        
        # Build the request
        try:
            dimensions = [Dimension(name=d) for d in input.dimensions]
            
            # Handle granularity as a dimension if provided and not already in dimensions
            if input.granularity and input.granularity not in input.dimensions:
                granularity_map = {
                    "daily": "date",
                    "weekly": "week",
                    "monthly": "month"
                }
                gran_dim = granularity_map.get(input.granularity.lower(), input.granularity)
                if gran_dim not in [d.name for d in dimensions]:
                    dimensions.append(Dimension(name=gran_dim))

            # Build filters properly
            dimension_filter = None
            if input.filters:
                try:
                    dimension_filter = build_filter_expression(input.filters)
                    logger.info(f"Built dimension filter: {dimension_filter}")
                except Exception as e:
                    logger.error(f"Failed to parse filters: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Invalid filters format: {str(e)}",
                        "data": [],
                        "rowCount": 0
                    }

            # Build order_bys
            order_bys = []
            if input.order_by:
                for order in input.order_by:
                    if "metric" in order:
                        from google.analytics.data_v1beta.types import OrderBy
                        order_bys.append(OrderBy(
                            metric=OrderBy.MetricOrderBy(metric_name=order["metric"]["metric_name"]),
                            desc=order.get("desc", False)
                        ))
                    elif "dimension" in order:
                        from google.analytics.data_v1beta.types import OrderBy
                        order_bys.append(OrderBy(
                            dimension=OrderBy.DimensionOrderBy(dimension_name=order["dimension"]["dimension_name"]),
                            desc=order.get("desc", False)
                        ))

            request = RunReportRequest(
                property=f"properties/{property_id}",
                dimensions=dimensions,
                metrics=[Metric(name=m) for m in input.metrics],
                date_ranges=[DateRange(start_date=input.start_date, end_date=input.end_date)],
                limit=input.limit,
                currency_code=input.currency_code if input.currency_code else None,
                keep_empty_rows=input.include_empty_rows if input.include_empty_rows is not None else None,
                dimension_filter=dimension_filter,
                order_bys=order_bys if order_bys else None
            )
            
            logger.info(f"Built request - Property: {property_id}, Dimensions: {[d.name for d in dimensions]}, Metrics: {input.metrics}")
            
        except Exception as e:
            logger.error(f"Failed to build request: {str(e)}")
            logger.error(f"Request build traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Failed to build GA4 request: {str(e)}",
                "data": [],
                "rowCount": 0
            }
        
        # Execute the request
        try:
            logger.info("Executing GA4 request...")
            response = client.run_report(request)
            logger.info(f"GA4 request completed successfully, got {len(response.rows)} rows")
        except Exception as e:
            logger.error(f"GA4 API request failed: {str(e)}")
            logger.error(f"API request traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"GA4 API request failed: {str(e)}",
                "data": [],
                "rowCount": 0
            }
        
        # Convert response to readable format
        try:
            rows = []
            total_sessions = 0  # Track total for aggregation
            
            for row in response.rows:
                row_data = {}
                # Add dimensions
                for i, dim_value in enumerate(row.dimension_values):
                    dim_name = response.dimension_headers[i].name
                    row_data[dim_name] = dim_value.value
                
                # Add metrics
                for i, metric_value in enumerate(row.metric_values):
                    metric_name = response.metric_headers[i].name
                    value = metric_value.value
                    row_data[metric_name] = value
                    
                    # Sum sessions for total calculation
                    if metric_name == "sessions":
                        try:
                            total_sessions += int(value)
                        except (ValueError, TypeError):
                            pass
                
                rows.append(row_data)
            
            logger.info(f"Successfully processed {len(rows)} rows, total sessions: {total_sessions}")
            
            return {
                "success": True,
                "data": rows,
                "rowCount": len(rows),
                "totalSessions": total_sessions,  # Add total for verification
                "dimensions": input.dimensions,
                "metrics": input.metrics,
                "dateRange": f"{input.start_date} to {input.end_date}",
                "propertyId": property_id
            }
        except Exception as e:
            logger.error(f"Failed to process response: {str(e)}")
            logger.error(f"Response processing traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Failed to process GA4 response: {str(e)}",
                "data": [],
                "rowCount": 0
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in get_ga4_data: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "data": [],
            "rowCount": 0
        }

async def list_ga4_dimensions(input: BasicQueryInput) -> dict:
    """List all available GA4 dimensions for the user's property."""
    try:
        logger.info(f"Getting dimensions for user: {input.user_id}")
        
        refresh_token, property_id = get_user_credentials(input.user_id)
        creds = always_refresh_user_tokens(refresh_token)
        client = BetaAnalyticsDataClient(credentials=creds)
        
        metadata = client.get_metadata(GetMetadataRequest(name=f"properties/{property_id}/metadata"))
        
        dimensions = []
        for d in metadata.dimensions:
            dimensions.append({
                "name": d.api_name,
                "displayName": d.ui_name,
                "description": d.description
            })
        
        logger.info(f"Retrieved {len(dimensions)} dimensions")
        
        return {
            "success": True,
            "dimensions": dimensions,
            "count": len(dimensions),
            "propertyId": property_id
        }
    except Exception as e:
        logger.error(f"Error in list_ga4_dimensions: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "dimensions": [],
            "count": 0
        }

async def list_ga4_metrics(input: BasicQueryInput) -> dict:
    """List all available GA4 metrics for the user's property."""
    try:
        logger.info(f"Getting metrics for user: {input.user_id}")
        
        refresh_token, property_id = get_user_credentials(input.user_id)
        creds = always_refresh_user_tokens(refresh_token)
        client = BetaAnalyticsDataClient(credentials=creds)
        
        metadata = client.get_metadata(GetMetadataRequest(name=f"properties/{property_id}/metadata"))
        
        metrics = []
        for m in metadata.metrics:
            metrics.append({
                "name": m.api_name,
                "displayName": m.ui_name,
                "description": m.description
            })
        
        logger.info(f"Retrieved {len(metrics)} metrics")
        
        return {
            "success": True,
            "metrics": metrics,
            "count": len(metrics),
            "propertyId": property_id
        }
    except Exception as e:
        logger.error(f"Error in list_ga4_metrics: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "metrics": [],
            "count": 0
        }