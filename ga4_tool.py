from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import run_dynamic_report
from utils.token_handler import check_and_refresh_token
from utils.ga4_query_parser import parse_user_query, GA4_COMPAT
from datetime import datetime, timezone

mcp = FastMCP("GA4DynamicTool", host="0.0.0.0", port=8000, debug=True)

@mcp.tool()
async def get_ga4_report(
    userId: str,
    ga4PropertyId: str,
    metrics: list,
    dimensions: list = [],
    date_range: dict = {},
    filters: dict = {},
    limit: int = 100
) -> dict:
    """
    Récupère dynamiquement n'importe quel rapport GA4 selon les paramètres fournis.
    """
    if not userId or not ga4PropertyId or not metrics:
        return {"error": "userId, ga4PropertyId et metrics sont obligatoires"}

    # Validation stricte de compatibilité metrics/dimensions
    main_metric = metrics[0] if metrics else None
    if main_metric and main_metric in GA4_COMPAT:
        allowed_dims = GA4_COMPAT[main_metric]
        before = list(dimensions)
        dimensions = [d for d in dimensions if d in allowed_dims]
        if before != dimensions:
            print(f"[GA4 MCP] Dimensions nettoyées pour compatibilité avec {main_metric}: {before} -> {dimensions}")
 
    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": f"Aucun token trouvé pour l'utilisateur {userId}"}
    try:
        tokens = await check_and_refresh_token(userId, tokens)
    except Exception as e:
        return {"error": f"Erreur lors du rafraîchissement du token: {str(e)}"}

    print(f"[GA4 MCP] 🚀 Appel de get_ga4_report avec:")
    print(f"   - Property ID: {ga4PropertyId}")
    print(f"   - Métriques: {metrics}")
    print(f"   - Dimensions: {dimensions or []}")
    print(f"   - Date range: {date_range or {'start_date': '30daysAgo', 'end_date': 'today'}}")
    print(f"   - Filtres: {filters or {}}")
    print(f"   - Limite: {limit}")
    
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
        print(f"[GA4 MCP] ✅ Succès - {len(result)} lignes retournées")
        return {"message": "Résultat GA4 dynamique", "data": result}
    except Exception as e:
        print(f"[GA4 MCP] ❌ Erreur lors de l'appel GA4: {type(e).__name__}: {str(e)}")
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
    limit = params.get("limit") or 100
    llm_needed = params.get("llm_needed", False)

    # Validation stricte de compatibilité metrics/dimensions
    main_metric = metrics[0] if metrics else None
    if main_metric and main_metric in GA4_COMPAT:
        allowed_dims = GA4_COMPAT[main_metric]
        before = list(dimensions)
        dimensions = [d for d in dimensions if d in allowed_dims]
        if before != dimensions:
            print(f"[GA4 MCP] Dimensions nettoyées pour compatibilité avec {main_metric}: {before} -> {dimensions}")

    # Log de la date système réelle
    print("[GA4 MCP] Date système actuelle :", datetime.now(timezone.utc))

    # Contrôle explicite sur les dates (UTC)
    def is_future_date(date_str):
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return date > now
        except Exception:
            return False
    if is_future_date(date_range["start_date"]) or is_future_date(date_range["end_date"]):
        return {"error": "La période demandée est dans le futur. Merci de choisir une période antérieure ou actuelle."}
    
    # 2. Récupère les tokens utilisateur
    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": f"Aucun token trouvé pour l'utilisateur {userId}"}
    try:
        tokens = await check_and_refresh_token(userId, tokens)
    except Exception as e:
        return {"error": f"Erreur lors du rafraîchissement du token: {str(e)}"}
    
    # 3. Appelle GA4 dynamiquement
    print(f"[GA4 MCP] 🚀 Appel de run_dynamic_report avec:")
    print(f"   - Property ID: {ga4PropertyId}")
    print(f"   - Métriques: {metrics}")
    print(f"   - Dimensions: {dimensions}")
    print(f"   - Date range: {date_range}")
    print(f"   - Filtres: {filters}")
    print(f"   - Limite: {limit}")
    
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
        print(f"[GA4 MCP] ✅ Succès - {len(result)} lignes retournées")
        return {
            "message": f"Résultat pour la question : {question}",
            "params": {**params, "dimensions": dimensions},
            "data": result,
            "suggestion": suggestion,
            "llm_needed": llm_needed
        }
    except Exception as e:
        print(f"[GA4 MCP] ❌ Erreur lors de l'appel GA4: {type(e).__name__}: {str(e)}")
        return {"error": f"Erreur GA4: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="sse")
