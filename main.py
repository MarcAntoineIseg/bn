from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from ga4_tool import mcp
from services.supabase_client import get_user_tokens
from utils.token_handler import check_and_refresh_token
from services.ga4_client import run_dynamic_report
from utils.ga4_schema import is_valid_metric, is_valid_dimension, get_all_metrics, get_all_dimensions
from utils.ga4_query_parser import parse_user_query
import logging
import json

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get MCP's ASGI-compatible app
mcp_app = mcp.http_app(path="/mcp")

# Create FastAPI and mount MCP under "/mcp-server"
app = FastAPI(lifespan=mcp_app.lifespan)  # ⚠️ VERY IMPORTANT
app.mount("/mcp-server", mcp_app)

class QueryRequest(BaseModel):
    userId: str
    ga4PropertyId: str
    metrics: List[str]
    dimensions: Optional[List[str]] = []
    date_range: Dict[str, str]  # {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
    filters: Optional[Dict[str, str]] = None
    limit: Optional[int] = 100

@app.post("/query")
async def query_ga4(request: QueryRequest):
    logger.info(f"[REST API] === DÉBUT query_ga4 ===")
    logger.info(f"[REST API] userId: {request.userId}")
    logger.info(f"[REST API] ga4PropertyId: {request.ga4PropertyId}")
    logger.info(f"[REST API] metrics: {request.metrics}")
    logger.info(f"[REST API] dimensions: {request.dimensions}")
    logger.info(f"[REST API] date_range: {request.date_range}")
    logger.info(f"[REST API] filters: {request.filters}")
    logger.info(f"[REST API] limit: {request.limit}")
    
    # Validation des métriques et dimensions
    logger.info(f"[REST API] Validation des métriques et dimensions...")
    for m in request.metrics:
        if not is_valid_metric(m):
            logger.error(f"[REST API] Métrique inconnue: {m}")
            raise HTTPException(status_code=400, detail=f"Métrique inconnue: {m}")
    for d in request.dimensions or []:
        if not is_valid_dimension(d):
            logger.error(f"[REST API] Dimension inconnue: {d}")
            raise HTTPException(status_code=400, detail=f"Dimension inconnue: {d}")
    
    logger.info(f"[REST API] ✅ Validation réussie")

    # Récupération des tokens utilisateur
    logger.info(f"[REST API] Récupération des tokens utilisateur...")
    tokens = get_user_tokens(request.userId)
    if not tokens:
        logger.error(f"[REST API] Aucun token trouvé pour l'utilisateur {request.userId}")
        raise HTTPException(status_code=401, detail=f"Aucun token trouvé pour l'utilisateur {request.userId}")
    try:
        tokens = await check_and_refresh_token(request.userId, tokens)
        logger.info(f"[REST API] ✅ Tokens rafraîchis avec succès")
    except Exception as e:
        logger.error(f"[REST API] ❌ Erreur lors du rafraîchissement du token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Erreur lors du rafraîchissement du token: {str(e)}")

    # Appel dynamique GA4
    try:
        logger.info(f"[REST API] Appel à run_dynamic_report...")
        result = await run_dynamic_report(
            tokens["access_token"],
            request.ga4PropertyId,
            request.metrics,
            request.dimensions or [],
            request.date_range,
            request.filters or {},
            request.limit or 100
        )
        logger.info(f"[REST API] ✅ Résultat obtenu avec succès - {len(result)} entrées")
        return {"message": "Résultat GA4 dynamique", "data": result}
    except Exception as e:
        logger.error(f"[REST API] ❌ Erreur GA4: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur GA4: {str(e)}")

# --- NOUVEAUX ENDPOINTS EXPERTS ---

@app.get("/catalog")
def get_catalog():
    """Retourne toutes les metrics et dimensions disponibles dans le MCP."""
    logger.info(f"[REST API] === DÉBUT get_catalog ===")
    metrics = get_all_metrics()
    dimensions = get_all_dimensions()
    logger.info(f"[REST API] Nombre de métriques: {len(metrics)}")
    logger.info(f"[REST API] Nombre de dimensions: {len(dimensions)}")
    logger.info(f"[REST API] === FIN get_catalog ===")
    return {
        "metrics": metrics,
        "dimensions": dimensions
    }

class ExplainRequest(BaseModel):
    question: str

@app.post("/explain")
def explain_question(req: ExplainRequest):
    """Analyse une question utilisateur et retourne le mapping généré (metrics, dimensions, date_range, filters, limit, suggestion, llm_needed)."""
    logger.info(f"[REST API] === DÉBUT explain_question ===")
    logger.info(f"[REST API] question: {req.question}")
    
    mapping = parse_user_query(req.question)
    logger.info(f"[REST API] Mapping généré: {json.dumps(mapping, indent=2)}")
    logger.info(f"[REST API] === FIN explain_question ===")
    return mapping
