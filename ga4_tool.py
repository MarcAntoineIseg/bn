from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import run_dynamic_report
from utils.token_handler import check_and_refresh_token
from utils.ga4_query_parser import parse_user_query

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
        result = await run_dynamic_report(
            tokens["access_token"],
            ga4PropertyId,
            metrics,
            dimensions or [],
            date_range or {"start_date": "30daysAgo", "end_date": "today"},
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
    if not userId or not ga4PropertyId or not question:
        return {"error": "userId, ga4PropertyId et question sont obligatoires"}

    # 1. Analyse la question
    params = parse_user_query(question)
    metrics = params["metrics"]
    dimensions = params["dimensions"]
    date_range = params["date_range"]
    filters = params["filters"]
    suggestion = params.get("suggestion")

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
            filters
        )
        return {
            "message": f"Résultat pour la question : {question}",
            "params": params,
            "data": result,
            "suggestion": suggestion
        }
    except Exception as e:
        return {"error": f"Erreur GA4: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="sse")
