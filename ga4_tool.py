from mcp.server.fastmcp import FastMCP
from services.supabase_client import get_user_tokens
from services.ga4_client import run_dynamic_report
from utils.token_handler import check_and_refresh_token
from utils.ga4_query_parser import parse_user_query, GA4_COMPAT
from datetime import datetime, timezone
from services.nlp_service import analyze_question
from services.mapping_service import map_intent, validate_mapping
from services.payload_builder import build_payload
from services.formatter import format_response
import logging
import json

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    logger.info(f"[MCP] === DÉBUT get_ga4_report ===")
    logger.info(f"[MCP] userId: {userId}")
    logger.info(f"[MCP] ga4PropertyId: {ga4PropertyId}")
    logger.info(f"[MCP] metrics: {metrics}")
    logger.info(f"[MCP] dimensions: {dimensions}")
    logger.info(f"[MCP] date_range: {date_range}")
    logger.info(f"[MCP] filters: {filters}")
    logger.info(f"[MCP] limit: {limit}")
    
    if not userId or not ga4PropertyId or not metrics:
        logger.error("[MCP] Paramètres manquants")
        return {"error": "userId, ga4PropertyId et metrics sont obligatoires"}

    # Validation stricte de compatibilité metrics/dimensions
    main_metric = metrics[0] if metrics else None
    if main_metric and main_metric in GA4_COMPAT:
        allowed_dims = GA4_COMPAT[main_metric]
        before = list(dimensions)
        dimensions = [d for d in dimensions if d in allowed_dims]
        if before != dimensions:
            logger.warning(f"[MCP] Dimensions nettoyées pour compatibilité avec {main_metric}: {before} -> {dimensions}")

    tokens = get_user_tokens(userId)
    if not tokens:
        logger.error(f"[MCP] Aucun token trouvé pour l'utilisateur {userId}")
        return {"error": f"Aucun token trouvé pour l'utilisateur {userId}"}
    try:
        tokens = await check_and_refresh_token(userId, tokens)
        logger.info(f"[MCP] Tokens rafraîchis avec succès")
    except Exception as e:
        logger.error(f"[MCP] Erreur lors du rafraîchissement du token: {str(e)}")
        return {"error": f"Erreur lors du rafraîchissement du token: {str(e)}"}

    try:
        logger.info(f"[MCP] Appel à run_dynamic_report...")
        result = await run_dynamic_report(
            tokens["access_token"],
            ga4PropertyId,
            metrics,
            dimensions or [],
            date_range or {"start_date": "30daysAgo", "end_date": "today"},
            filters or {},
            limit
        )
        logger.info(f"[MCP] ✅ Résultat obtenu avec succès - {len(result)} entrées")
        return {"message": "Résultat GA4 dynamique", "data": result}
    except Exception as e:
        logger.error(f"[MCP] ❌ Erreur GA4: {str(e)}")
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
    logger.info(f"[MCP] === DÉBUT ask_ga4_report ===")
    logger.info(f"[MCP] userId: {userId}")
    logger.info(f"[MCP] ga4PropertyId: {ga4PropertyId}")
    logger.info(f"[MCP] question: {question}")
    
    if not userId or not ga4PropertyId or not question:
        logger.error("[MCP] Paramètres manquants")
        return {"error": "userId, ga4PropertyId et question sont obligatoires"}

    # 1. Analyse la question
    logger.info(f"[MCP] Analyse de la question...")
    params = parse_user_query(question)
    metrics = params["metrics"]
    dimensions = params["dimensions"]
    date_range = params["date_range"]
    filters = params["filters"]
    suggestion = params.get("suggestion")
    limit = params.get("limit") or 100
    llm_needed = params.get("llm_needed", False)
    
    logger.info(f"[MCP] Paramètres extraits:")
    logger.info(f"[MCP]   - metrics: {metrics}")
    logger.info(f"[MCP]   - dimensions: {dimensions}")
    logger.info(f"[MCP]   - date_range: {date_range}")
    logger.info(f"[MCP]   - filters: {filters}")
    logger.info(f"[MCP]   - limit: {limit}")
    logger.info(f"[MCP]   - suggestion: {suggestion}")
    logger.info(f"[MCP]   - llm_needed: {llm_needed}")

    # Validation stricte de compatibilité metrics/dimensions
    main_metric = metrics[0] if metrics else None
    if main_metric and main_metric in GA4_COMPAT:
        allowed_dims = GA4_COMPAT[main_metric]
        before = list(dimensions)
        dimensions = [d for d in dimensions if d in allowed_dims]
        if before != dimensions:
            logger.warning(f"[MCP] Dimensions nettoyées pour compatibilité avec {main_metric}: {before} -> {dimensions}")

    # Log de la date système réelle
    logger.info(f"[MCP] Date système actuelle : {datetime.now(timezone.utc)}")

    def is_future_date(date_str):
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return date > now
        except Exception:
            return False
    def today_str():
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Si la date de fin est dans le futur, on la ramène à aujourd'hui
    if is_future_date(date_range["end_date"]):
        old_end = date_range["end_date"]
        date_range["end_date"] = today_str()
        logger.warning(f"[MCP] Date de fin dans le futur ({old_end}), ramenée à aujourd'hui ({date_range['end_date']})")
    # Si la date de début est dans le futur, on retourne une erreur explicite
    if is_future_date(date_range["start_date"]):
        logger.error(f"[MCP] La période demandée commence dans le futur")
        return {"error": "La période demandée commence dans le futur. Merci de choisir une période antérieure ou actuelle."}

    # 2. Récupère les tokens utilisateur
    logger.info(f"[MCP] Récupération des tokens utilisateur...")
    tokens = get_user_tokens(userId)
    if not tokens:
        logger.error(f"[MCP] Aucun token trouvé pour l'utilisateur {userId}")
        return {"error": f"Aucun token trouvé pour l'utilisateur {userId}"}
    try:
        tokens = await check_and_refresh_token(userId, tokens)
        logger.info(f"[MCP] Tokens rafraîchis avec succès")
    except Exception as e:
        logger.error(f"[MCP] Erreur lors du rafraîchissement du token: {str(e)}")
        return {"error": f"Erreur lors du rafraîchissement du token: {str(e)}"}

    # 3. Appelle GA4 dynamiquement
    try:
        logger.info(f"[MCP] Appel à run_dynamic_report...")
        result = await run_dynamic_report(
            tokens["access_token"],
            ga4PropertyId,
            metrics,
            dimensions,
            date_range,
            filters,
            limit
        )
        logger.info(f"[MCP] ✅ Résultat obtenu avec succès - {len(result)} entrées")
        return {
            "message": f"Résultat pour la question : {question}",
            "params": {**params, "dimensions": dimensions},
            "data": result,
            "suggestion": suggestion,
            "llm_needed": llm_needed
        }
    except Exception as e:
        logger.error(f"[MCP] ❌ Erreur GA4: {str(e)}")
        return {"error": f"Erreur GA4: {str(e)}"}

@mcp.tool()
async def ask_ga4_report_ai(
    userId: str,
    ga4PropertyId: str,
    question: str
) -> dict:
    """
    Pipeline MCP AI-powered : analyse, mapping, validation, payload, exécution, formatage.
    """
    logger.info(f"[MCP] === DÉBUT ask_ga4_report_ai ===")
    logger.info(f"[MCP] userId: {userId}")
    logger.info(f"[MCP] ga4PropertyId: {ga4PropertyId}")
    logger.info(f"[MCP] question: {question}")
    
    # 1. Analyse sémantique (LLM ou fallback)
    logger.info(f"[MCP] Étape 1: Analyse sémantique...")
    nlp_result = analyze_question(question)
    logger.info(f"[MCP] NLP result: {json.dumps(nlp_result, indent=2)}")

    # 2. Mapping expert + validation
    logger.info(f"[MCP] Étape 2: Mapping et validation...")
    mapping = map_intent(nlp_result)
    validation = validate_mapping(mapping)
    logger.info(f"[MCP] Mapping validé: {json.dumps(validation, indent=2)}")

    if not validation.get("is_valid", False):
        logger.error(f"[MCP] Mapping invalide: {validation.get('error')}")
        return format_response(error=validation.get("error"), suggestion=validation.get("suggestion"))

    # 3. Construction du payload GA4
    logger.info(f"[MCP] Étape 3: Construction du payload...")
    payload = build_payload(validation)
    logger.info(f"[MCP] Payload GA4: {json.dumps(payload, indent=2)}")

    # 4. Récupération des tokens utilisateur
    logger.info(f"[MCP] Étape 4: Récupération des tokens...")
    tokens = get_user_tokens(userId)
    if not tokens:
        logger.error(f"[MCP] Aucun token trouvé pour l'utilisateur {userId}")
        return format_response(error=f"Aucun token trouvé pour l'utilisateur {userId}")
    try:
        tokens = await check_and_refresh_token(userId, tokens)
        logger.info(f"[MCP] Tokens rafraîchis avec succès")
    except Exception as e:
        logger.error(f"[MCP] Erreur lors du rafraîchissement du token: {str(e)}")
        return format_response(error=f"Erreur lors du rafraîchissement du token: {str(e)}")

    # 5. Appel à GA4
    try:
        logger.info(f"[MCP] Étape 5: Appel à GA4...")
        data = await run_dynamic_report(
            tokens["access_token"],
            ga4PropertyId,
            payload["metrics"],
            payload["dimensions"],
            payload["date_range"],
            payload.get("filters", {}),
            payload.get("limit", 100)
        )
        logger.info(f"[MCP] ✅ Données GA4 reçues - {len(data)} entrées")
    except Exception as e:
        logger.error(f"[MCP] ❌ Erreur GA4: {str(e)}")
        return format_response(error=f"Erreur GA4: {str(e)}")

    # 6. Formatage de la réponse
    logger.info(f"[MCP] Étape 6: Formatage de la réponse...")
    response = format_response(data=data, mapping=validation)
    logger.info(f"[MCP] === FIN ask_ga4_report_ai ===")
    return response

if __name__ == "__main__":
    mcp.run(transport="sse")
