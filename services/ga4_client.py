from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Metric, RunReportRequest
)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import httpx
from utils.ga4_query_parser import parse_user_query
from services.supabase_client import get_user_tokens
from utils.token_handler import check_and_refresh_token


async def get_session_count(access_token: str, property_id: str):
    # Prepare credentials from access token
    credentials = Credentials(
        token=access_token,
        refresh_token=None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=None,
        client_secret=None,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )

    # Build GA4 API client
    client = BetaAnalyticsDataClient(credentials=credentials)

    # Create report request
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")]
    )

    response = client.run_report(request)
    
    # Extract session count from the first row
    if response.rows:
        return {
            "metric": "sessions_last_30_days",
            "value": response.rows[0].metric_values[0].value
        }
    else:
        return {
            "metric": "sessions_last_30_days",
            "value": "0"
        }

async def get_sessions_by_country(access_token: str, property_id: str):
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    body = {
        "dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "country"}],
        "metrics": [{"name": "sessions"}],
        "limit": 10
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()

    result = [
        {
            "country": row["dimensionValues"][0]["value"],
            "sessions": row["metricValues"][0]["value"]
        }
        for row in data.get("rows", [])
    ]

    return result

async def run_dynamic_report(access_token: str, property_id: str, metrics: list, dimensions: list, date_range: dict, filters: dict = {}, limit: int = 100):
    """
    Exécute une requête dynamique sur l'API GA4 avec métriques, dimensions, plage de dates et filtres personnalisés.
    """
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    body = {
        "dateRanges": [{
            "startDate": date_range.get("start_date", "30daysAgo"),
            "endDate": date_range.get("end_date", "today")
        }],
        "metrics": [{"name": m} for m in metrics],
        "dimensions": [{"name": d} for d in dimensions] if dimensions else [],
        "limit": limit
    }
    if filters:
        # Construction simple: chaque filtre = stringFilter (égalité)
        body["dimensionFilter"] = {
            "andGroup": {
                "expressions": [
                    {"filter": {"fieldName": k, "stringFilter": {"value": v}}}
                    for k, v in filters.items()
                ]
            }
        }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
    # Extraction des résultats
    rows = data.get("rows", [])
    dimension_headers = [d["name"] for d in data.get("dimensionHeaders", [])]
    metric_headers = [m["name"] for m in data.get("metricHeaders", [])]
    result = []
    for row in rows:
        entry = {}
        for i, dim in enumerate(dimension_headers):
            entry[dim] = row["dimensionValues"][i]["value"]
        for j, met in enumerate(metric_headers):
            entry[met] = row["metricValues"][j]["value"]
        result.append(entry)
    return result
