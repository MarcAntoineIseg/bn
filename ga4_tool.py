from fastapi import APIRouter
from services.supabase_client import get_user_tokens
from services.ga4_client import run_dynamic_report
from utils.token_handler import check_and_refresh_token
from utils.ga4_query_parser import parse_user_query
from fastapi import Body

router = APIRouter()

@router.post("/get_ga4_report")
async def get_ga4_report(
    userId: str = Body(...),
    ga4PropertyId: str = Body(...),
    metrics: list = Body(...),
    dimensions: list = Body([]),
    date_range: dict = Body(None),
    filters: dict = Body(None),
    limit: int = Body(100)
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

    if date_range is None:
        date_range = {"start_date": "30daysAgo", "end_date": "today"}
    if filters is None:
        filters = {}
    if dimensions is None:
        dimensions = []

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
        return {"message": "Résultat GA4 dynamique", "data": result}
    except Exception as e:
        return {"error": f"Erreur GA4: {str(e)}"}

@router.post("/ask_ga4_report")
async def ask_ga4_report(
    userId: str = Body(...),
    ga4PropertyId: str = Body(...),
    question: str = Body(...)
) -> dict:
    """
    Analyse la question utilisateur, déduit metrics/dimensions/date_range/filters, exécute la requête GA4 et retourne la réponse.
    Gère aussi les questions comparatives (deux périodes).
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
    comparative = params.get("comparative")

    if date_range is None:
        date_range = {"start_date": "30daysAgo", "end_date": "today"}
    if filters is None:
        filters = {}
    if dimensions is None:
        dimensions = []

    # 2. Récupère les tokens utilisateur
    tokens = get_user_tokens(userId)
    if not tokens:
        return {"error": f"Aucun token trouvé pour l'utilisateur {userId}"}
    try:
        tokens = await check_and_refresh_token(userId, tokens)
    except Exception as e:
        return {"error": f"Erreur lors du rafraîchissement du token: {str(e)}"}

    # 3. Si question comparative, exécute deux requêtes et calcule l'évolution
    if comparative and comparative.get("period1") and comparative.get("period2"):
        try:
            result1 = await run_dynamic_report(
                tokens["access_token"],
                ga4PropertyId,
                metrics,
                dimensions,
                comparative["period1"],
                filters,
                limit
            )
            result2 = await run_dynamic_report(
                tokens["access_token"],
                ga4PropertyId,
                metrics,
                dimensions,
                comparative["period2"],
                filters,
                limit
            )
            # Calcul de l'évolution sur la première metric
            def extract_value(res):
                if res and isinstance(res, list) and len(res) > 0 and metrics[0] in res[0]:
                    try:
                        return float(res[0][metrics[0]])
                    except Exception:
                        return None
                return None
            v1 = extract_value(result1)
            v2 = extract_value(result2)
            evolution = None
            evolution_pct = None
            if v1 is not None and v2 is not None and v2 != 0:
                evolution = v1 - v2
                evolution_pct = ((v1 - v2) / v2) * 100
            return {
                "message": f"Comparaison entre deux périodes : {comparative['period1']} vs {comparative['period2']}",
                "params": params,
                "data_period1": result1,
                "data_period2": result2,
                "evolution": evolution,
                "evolution_pct": evolution_pct,
                "suggestion": suggestion,
                "llm_needed": llm_needed
            }
        except Exception as e:
            return {"error": f"Erreur GA4 comparative: {str(e)}"}

    # 4. Sinon, requête simple
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
        return {
            "message": f"Résultat pour la question : {question}",
            "params": params,
            "data": result,
            "suggestion": suggestion,
            "llm_needed": llm_needed
        }
    except Exception as e:
        return {"error": f"Erreur GA4: {str(e)}"}
