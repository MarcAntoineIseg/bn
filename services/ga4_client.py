from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Metric, RunReportRequest
)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import httpx
import logging
from utils.ga4_query_parser import parse_user_query
from services.supabase_client import get_user_tokens
from utils.token_handler import check_and_refresh_token

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

async def run_dynamic_report(access_token: str, property_id: str, metrics: list, dimensions: list, date_range: dict, filters: dict = None, limit: int = 100):
    """
    Exécute une requête dynamique sur l'API GA4 avec métriques, dimensions, plage de dates et filtres personnalisés.
    """
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Si on a des dimensions (ex: date), on fait aussi une requête pour le total
    include_total = len(dimensions) > 0
    
    # Requête principale avec dimensions
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
    
    # Log de la requête pour debug
    logger.info(f"GA4 Request URL: {url}")
    logger.info(f"GA4 Request Body: {body}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        
        # Log de la réponse pour debug
        logger.info(f"GA4 Response Status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"GA4 Response Error: {response.text}")
        
        response.raise_for_status()
        data = response.json()
    
    # Extraction des résultats détaillés
    rows = data.get("rows", [])
    dimension_headers = [d["name"] for d in data.get("dimensionHeaders", [])]
    metric_headers = [m["name"] for m in data.get("metricHeaders", [])]
    detailed_result = []
    for row in rows:
        entry = {}
        for i, dim in enumerate(dimension_headers):
            entry[dim] = row["dimensionValues"][i]["value"]
        for j, met in enumerate(metric_headers):
            entry[met] = row["metricValues"][j]["value"]
        detailed_result.append(entry)
    
    # Si on a des dimensions, on récupère aussi le total
    total_result = None
    if include_total:
        # Requête pour le total (sans dimensions)
        total_body = {
            "dateRanges": [{
                "startDate": date_range.get("start_date", "30daysAgo"),
                "endDate": date_range.get("end_date", "today")
            }],
            "metrics": [{"name": m} for m in metrics]
        }
        if filters:
            total_body["dimensionFilter"] = body["dimensionFilter"]
        
        logger.info(f"GA4 Total Request Body: {total_body}")
        
        total_response = await client.post(url, headers=headers, json=total_body)
        if total_response.status_code == 200:
            total_data = total_response.json()
            total_rows = total_data.get("rows", [])
            if total_rows:
                total_result = {}
                for j, met in enumerate(metric_headers):
                    total_result[met] = total_rows[0]["metricValues"][j]["value"]
    
    # Retourne les résultats avec le total si disponible
    result = {
        "detailed_data": detailed_result,
        "total": total_result
    }
    
    return result


