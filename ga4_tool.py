from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import run_dynamic_report
from utils.token_handler import check_and_refresh_token
from utils.ga4_query_parser import parse_user_query
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("GA4DynamicTool", host="0.0.0.0", port=8000, debug=True)

@mcp.tool()
async def get_ga4_report(
    userId: str,
    ga4PropertyId: str,
    metrics: list,
    dimensions: list = [],
    date_range: dict = None,
    filters: dict = None,
    limit: int = 100
) -> dict:
    """
    Récupère dynamiquement n'importe quel rapport GA4 selon les paramètres fournis.
    """
    if not userId or not ga4PropertyId or not metrics:
        return {"error": "userId, ga4PropertyId et metrics sont obligatoires"}

    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": f"Aucun token trouvé pour l'utilisateur {userId}"}
    try:
        tokens = await check_and_refresh_token(userId, tokens)
    except Exception as e:
        return {"error": f"Erreur lors du rafraîchissement du token: {str(e)}"}

    try:
        default_date_range = {"start_date": "30daysAgo", "end_date": "today"}
        result = await run_dynamic_report(
            tokens["access_token"],
            ga4PropertyId,
            metrics,
            dimensions or [],
            date_range or default_date_range,
            filters or {},
            limit
        )
        return {"message": "Résultat GA4 dynamique", "data": result}
    except Exception as e:
        return {"error": f"Erreur GA4: {str(e)}"}

@mcp.tool()
async def ask_ga4_report(
    userId: str,
    ga4PropertyId: str,
    question: str
) -> dict:
    """
    Analyse la question utilisateur, déduit metrics/dimensions/date_range/filters, exécute la requête GA4 et retourne la réponse.
    """
    try:
        if not userId or not ga4PropertyId or not question:
            return {"error": "userId, ga4PropertyId et question sont obligatoires"}

        # 1. Analyse la question
        logger.info(f"Analyzing question: {question}")
        params = parse_user_query(question)
        logger.info(f"Parsed params: {params}")
        
        metrics = params["metrics"]
        dimensions = params["dimensions"]
        date_range = params["date_range"]
        filters = params["filters"]
        suggestion = params.get("suggestion")
        limit = params.get("limit") or 100
        llm_needed = params.get("llm_needed", False)

        # 2. Récupère les tokens utilisateur
        tokens = get_user_tokens(userId)
        if not tokens:
            return {"error": f"Aucun token trouvé pour l'utilisateur {userId}"}
        try:
            tokens = await check_and_refresh_token(userId, tokens)
        except Exception as e:
            return {"error": f"Erreur lors du rafraîchissement du token: {str(e)}"}

        # 3. Appelle GA4 dynamiquement
        try:
            result = await run_dynamic_report(
                tokens["access_token"],
                ga4PropertyId,
                metrics,
                dimensions,
                date_range,
                filters,
                limit
            )
            
            # Gestion de la nouvelle structure de réponse
            if isinstance(result, dict) and "detailed_data" in result:
                # Nouvelle structure avec total et données détaillées
                return {
                    "message": f"Résultat pour la question : {question}",
                    "params": params,
                    "total": result.get("total"),
                    "detailed_data": result.get("detailed_data", []),
                    "suggestion": suggestion,
                    "llm_needed": llm_needed
                }
            else:
                # Ancienne structure (compatibilité)
                return {
                    "message": f"Résultat pour la question : {question}",
                    "params": params,
                    "data": result,
                    "suggestion": suggestion,
                    "llm_needed": llm_needed
                }
        except Exception as e:
            logger.error(f"GA4 API Error: {str(e)}")
            return {"error": f"Erreur GA4: {str(e)}"}
            
    except Exception as e:
        import traceback
        logger.error(f"Unexpected error in ask_ga4_report: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": f"Erreur inattendue: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="sse")
