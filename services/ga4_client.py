from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Metric, RunReportRequest
)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import httpx
import json
import logging
from utils.ga4_query_parser import parse_user_query
from services.supabase_client import get_user_tokens
from utils.token_handler import check_and_refresh_token

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_session_count(access_token: str, property_id: str):
    logger.info(f"[GA4 API] Début get_session_count - Property ID: {property_id}")
    
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

    logger.info(f"[GA4 API] Requête envoyée: {request}")
    
    response = client.run_report(request)
    
    logger.info(f"[GA4 API] Réponse reçue - Nombre de lignes: {len(response.rows) if response.rows else 0}")
    
    # Extract session count from the first row
    if response.rows:
        result = {
            "metric": "sessions_last_30_days",
            "value": response.rows[0].metric_values[0].value
        }
        logger.info(f"[GA4 API] Résultat extrait: {result}")
        return result
    else:
        result = {
            "metric": "sessions_last_30_days",
            "value": "0"
        }
        logger.info(f"[GA4 API] Aucune donnée trouvée, retour: {result}")
        return result

async def get_sessions_by_country(access_token: str, property_id: str):
    logger.info(f"[GA4 API] Début get_sessions_by_country - Property ID: {property_id}")
    
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    
    headers = {
        "Authorization": f"Bearer {access_token[:20]}..."  # Log partiel du token pour la sécurité
    }

    body = {
        "dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "country"}],
        "metrics": [{"name": "sessions"}],
        "limit": 10
    }

    logger.info(f"[GA4 API] URL: {url}")
    logger.info(f"[GA4 API] Headers: {headers}")
    logger.info(f"[GA4 API] Body: {json.dumps(body, indent=2)}")

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        logger.info(f"[GA4 API] Status code: {response.status_code}")
        logger.info(f"[GA4 API] Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            logger.error(f"[GA4 API] Erreur HTTP: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        data = response.json()
        logger.info(f"[GA4 API] Réponse JSON: {json.dumps(data, indent=2)}")

    result = [
        {
            "country": row["dimensionValues"][0]["value"],
            "sessions": row["metricValues"][0]["value"]
        }
        for row in data.get("rows", [])
    ]

    logger.info(f"[GA4 API] Résultat final: {result}")
    return result

async def run_dynamic_report(access_token: str, property_id: str, metrics: list, dimensions: list, date_range: dict, filters: dict = {}, limit: int = 100):
    """
    Exécute une requête dynamique sur l'API GA4 avec métriques, dimensions, plage de dates et filtres personnalisés.
    """
    logger.info(f"[GA4 API] === DÉBUT run_dynamic_report ===")
    logger.info(f"[GA4 API] Property ID: {property_id}")
    logger.info(f"[GA4 API] Metrics: {metrics}")
    logger.info(f"[GA4 API] Dimensions: {dimensions}")
    logger.info(f"[GA4 API] Date range: {date_range}")
    logger.info(f"[GA4 API] Filters: {filters}")
    logger.info(f"[GA4 API] Limit: {limit}")
    
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    headers = {
        "Authorization": f"Bearer {access_token[:20]}..."  # Log partiel du token pour la sécurité
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
    
    logger.info(f"[GA4 API] URL complète: {url}")
    logger.info(f"[GA4 API] Headers: {headers}")
    logger.info(f"[GA4 API] Body complet: {json.dumps(body, indent=2)}")
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"[GA4 API] Envoi de la requête...")
            response = await client.post(url, headers=headers, json=body)
            
            logger.info(f"[GA4 API] Status code reçu: {response.status_code}")
            logger.info(f"[GA4 API] Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"[GA4 API] ❌ ERREUR HTTP {response.status_code}")
                logger.error(f"[GA4 API] Response text: {response.text}")
                response.raise_for_status()
            
            data = response.json()
            logger.info(f"[GA4 API] ✅ Réponse JSON reçue")
            logger.info(f"[GA4 API] Nombre de lignes dans la réponse: {len(data.get('rows', []))}")
            logger.info(f"[GA4 API] Dimension headers: {[d['name'] for d in data.get('dimensionHeaders', [])]}")
            logger.info(f"[GA4 API] Metric headers: {[m['name'] for m in data.get('metricHeaders', [])]}")
            
            # Log des premières lignes pour debug
            rows = data.get("rows", [])
            if rows:
                logger.info(f"[GA4 API] Première ligne de données: {rows[0]}")
                if len(rows) > 1:
                    logger.info(f"[GA4 API] Dernière ligne de données: {rows[-1]}")
            
    except Exception as e:
        logger.error(f"[GA4 API] ❌ Exception lors de l'appel API: {str(e)}")
        raise
    
    # Extraction des résultats
    rows = data.get("rows", [])
    dimension_headers = [d["name"] for d in data.get("dimensionHeaders", [])]
    metric_headers = [m["name"] for m in data.get("metricHeaders", [])]
    
    logger.info(f"[GA4 API] Extraction des données...")
    logger.info(f"[GA4 API] Dimension headers: {dimension_headers}")
    logger.info(f"[GA4 API] Metric headers: {metric_headers}")
    
    result = []
    for i, row in enumerate(rows):
        entry = {}
        for j, dim in enumerate(dimension_headers):
            entry[dim] = row["dimensionValues"][j]["value"]
        for k, met in enumerate(metric_headers):
            entry[met] = row["metricValues"][k]["value"]
        result.append(entry)
        
        # Log des premières entrées pour debug
        if i < 3:
            logger.info(f"[GA4 API] Entrée {i+1}: {entry}")
    
    logger.info(f"[GA4 API] === FIN run_dynamic_report ===")
    logger.info(f"[GA4 API] Nombre total d'entrées retournées: {len(result)}")
    
    return result
