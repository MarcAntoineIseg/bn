import re
from datetime import datetime, timedelta
from utils.ga4_schema import get_all_metrics, get_all_dimensions, is_valid_metric, is_valid_dimension
from utils.ga4_intents import detect_intent
import logging
from dateutil.relativedelta import relativedelta

# Dictionnaire de synonymes/traductions pour metrics et dimensions GA4
SYNONYMS = {
    # Metrics
    "utilisateur": "totalUsers",
    "utilisateurs": "totalUsers",
    "users": "totalUsers",
    "sessions": "sessions",
    "session": "sessions",
    "revenu": "totalRevenue",
    "recette": "totalRevenue",
    "conversion": "conversions",
    "conversions": "conversions",
    "pages vues": "screenPageViews",
    "page vue": "screenPageViews",
    "page": "pagePath",
    "pages": "pagePath",
    "taux de rebond": "bounceRate",
    "rebond": "bounceRate",
    "durée moyenne": "averageSessionDuration",
    "temps moyen": "averageSessionDuration",
    # Dimensions
    "pays": "country",
    "pays d'origine": "country",
    "country": "country",
    "ville": "city",
    "city": "city",
    "source": "source",
    "sources": "source",
    "canal": "sessionDefaultChannelGroup",
    "canal par défaut": "sessionDefaultChannelGroup",
    "channel": "sessionDefaultChannelGroup",
    "date": "date",
    "jour": "date",
    "appareil": "deviceCategory",
    "mobile": "deviceCategory",
    "desktop": "deviceCategory",
    "ordinateur": "deviceCategory",
    "genre": "userGender",
    "sexe": "userGender",
    "âge": "userAgeBracket",
    "age": "userAgeBracket",
    # ... à enrichir selon les besoins
}

# Recettes intelligentes pour questions fréquentes
SMART_RULES = [
    {
        "keywords": ["âge", "age", "moyenne d'âge", "âge moyen"],
        "dimensions": ["userAgeBracket"],
        "suggestion": "La moyenne d'âge n'est pas disponible, mais voici la répartition par tranche d'âge."
    },
    {
        "keywords": ["genre", "sexe"],
        "dimensions": ["userGender"],
        "suggestion": "La répartition par genre est disponible via la dimension 'userGender'."
    },
    {
        "keywords": ["appareil", "device", "mobile", "desktop", "ordinateur"],
        "dimensions": ["deviceCategory"],
        "suggestion": "Voici la répartition par type d'appareil (mobile, desktop, etc.)."
    },
    {
        "keywords": ["source", "trafic", "acquisition", "canal", "channel"],
        "dimensions": ["source", "sessionDefaultChannelGroup"],
        "suggestion": "Voici la répartition par source ou canal d'acquisition."
    },
    {
        "keywords": ["taux de rebond", "rebond", "bounce rate"],
        "metrics": ["bounceRate"],
        "suggestion": None
    },
    {
        "keywords": ["durée moyenne", "temps moyen", "average session duration"],
        "metrics": ["averageSessionDuration"],
        "suggestion": None
    },
    {
        "keywords": ["page", "pages", "plus vues", "top pages", "meilleures pages", "page la plus visitée", "top 10", "top 5", "top dix", "top cinq"],
        "metrics": ["screenPageViews"],
        "dimensions": ["pagePath"],
        "suggestion": "Voici le classement des pages les plus vues."
    },
    # ... à enrichir selon les besoins
]

# Mapping minimal de compatibilité metrics/dimensions GA4 (à enrichir selon la doc officielle)
GA4_COMPAT = {
    "screenPageViews": ["pagePath", "pageTitle", "country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"],
    "sessions": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"],
    "totalUsers": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"],
    "bounceRate": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"],
    "averageSessionDuration": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"],
    # ... à enrichir pour chaque metric clé
}

def extract_date_range(query):
    """
    Extrait la période demandée dans la question utilisateur.
    Gère : 'en 2024', 'le mois dernier', 'cette semaine', 'aujourd'hui', etc.
    Fallback : toute la période GA4.
    """
    today = datetime.utcnow().date()
    # Par défaut : toute la période GA4
    start_date = "2005-01-01"
    end_date = today.strftime("%Y-%m-%d")
    # Année précise
    match = re.search(r'en (20\d{2})', query)
    if match:
        year = int(match.group(1))
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
    elif "le mois dernier" in query:
        first = today.replace(day=1) - relativedelta(months=1)
        start_date = first.strftime("%Y-%m-01")
        end_date = (first + relativedelta(day=31)).strftime("%Y-%m-%d")
    elif "cette semaine" in query:
        start_date = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif "aujourd'hui" in query:
        start_date = end_date = today.strftime("%Y-%m-%d")
    # ... autres patterns à enrichir
    return {"start_date": start_date, "end_date": end_date}

# Placeholder pour le LLM fallback
def fallback_llm(query):
    logging.info(f"[GA4 MCP] Fallback LLM activé pour la question : {query}")
    return {
        "metrics": [],
        "dimensions": [],
        "date_range": extract_date_range(query),
        "filters": {},
        "limit": None,
        "suggestion": "Je n'ai pas compris la question, pouvez-vous la reformuler ?"
    }

def parse_user_query(query: str):
    """
    Parse une question utilisateur pour extraire metrics, dimensions, date_range, filters, limit, suggestion, llm_needed.
    Utilise d'abord le router d'intention (GA4_INTENTS), puis fallback dynamique.
    Nettoie strictement les dimensions pour ne garder que celles compatibles avec la metric principale.
    """
    query = query.lower()
    filters = {}
    suggestion = None
    limit = None
    llm_needed = False

    all_metrics = get_all_metrics()
    all_dimensions = get_all_dimensions()

    logging.info(f"[GA4 MCP] Question utilisateur : {query}")
    # 1. Router d'intention (mapping expert)
    intent, config = detect_intent(query)
    if config:
        metrics = list(config["metrics"])
        # Dimensions : si la question précise une dimension compatible, on la garde, sinon on prend la principale
        dimensions = []
        for d in config["dimensions"]:
            if d in query:
                dimensions.append(d)
        if not dimensions:
            # fallback : dimension principale (ex : pagePath pour page views)
            dimensions = [config["dimensions"][0]]
        date_range = dict(config["default_time_range"])
        # Gestion du limit (top N)
        match = re.search(r'top ?(\d+)', query)
        if match:
            limit = int(match.group(1))
        elif "top cinq" in query:
            limit = 5
        elif "top dix" in query:
            limit = 10
        elif any(kw in query for kw in ["top", "meilleurs", "plus vues", "plus visités", "plus visitées"]):
            limit = 10
        # Filtres simples
        if "france" in query:
            filters["country"] = "France"
        if "mobile" in query:
            filters["deviceCategory"] = "mobile"
        if "desktop" in query or "ordinateur" in query:
            filters["deviceCategory"] = "desktop"
        # Suggestion
        suggestion = f"Intent détecté : {intent}."
        # Nettoyage strict : ne garder que les dimensions compatibles
        allowed_dims = set(config["dimensions"])
        before = list(dimensions)
        dimensions = [d for d in dimensions if d in allowed_dims]
        if before != dimensions:
            logging.info(f"[GA4 MCP] Dimensions nettoyées pour compatibilité avec l'intention {intent}: {before} -> {dimensions}")
        # Cas particulier : top page unique
        if intent == "page_views" and ("top 1" in query or "page la plus vue" in query or "plus vue" in query):
            metrics = ["screenPageViews"]
            dimensions = ["pagePath"]
            limit = 1
            logging.info("[GA4 MCP] Forçage mapping pour 'page la plus vue' : screenPageViews + pagePath, limit=1")
        logging.info(f"[GA4 MCP] Intention détectée : {intent}, metrics={metrics}, dimensions={dimensions}, date_range={date_range}, limit={limit}, filters={filters}")
        # Nettoyage strict : ne garder que les dimensions compatibles
        if metrics and metrics[0] in GA4_COMPAT:
            before = list(dimensions)
            dimensions = [d for d in dimensions if d in GA4_COMPAT[metrics[0]]]
            if before != dimensions:
                logging.info(f"[GA4 MCP] Dimensions nettoyées pour compatibilité avec la metric {metrics[0]} : {before} -> {dimensions}")
    else:
        # 2. Fallback dynamique (ancien code)
        metrics = []
        dimensions = []
        # Matching via synonymes/traductions
        for word, ga4_name in SYNONYMS.items():
            if word in query:
                if ga4_name in all_metrics and ga4_name not in metrics:
                    metrics.append(ga4_name)
                if ga4_name in all_dimensions and ga4_name not in dimensions:
                    dimensions.append(ga4_name)
        # Matching dynamique sur les metrics
        for metric in all_metrics:
            if metric.lower() in query and metric not in metrics:
                metrics.append(metric)
        # Matching dynamique sur les dimensions
        for dimension in all_dimensions:
            if dimension.lower() in query and dimension not in dimensions:
                dimensions.append(dimension)
        # Par défaut : toute la période GA4
        date_range = {"start_date": "2005-01-01", "end_date": "today"}
        # Gestion du limit (top N)
        match = re.search(r'top ?(\d+)', query)
        if match:
            limit = int(match.group(1))
        elif "top cinq" in query:
            limit = 5
        elif "top dix" in query:
            limit = 10
        elif any(kw in query for kw in ["top", "meilleurs", "plus vues", "plus visités", "plus visitées"]):
            limit = 10
        # Filtres simples
        if "france" in query:
            filters["country"] = "France"
        if "mobile" in query:
            filters["deviceCategory"] = "mobile"
        if "desktop" in query or "ordinateur" in query:
            filters["deviceCategory"] = "desktop"
        # Suggestion
        suggestion = "Aucune intention explicite détectée, fallback dynamique."
        # Valeur par défaut si aucune metric trouvée
        if not metrics:
            metrics = ["sessions"]
        # Extraction de la période
        date_range = extract_date_range(query)
        # Ajout automatique de la dimension 'month' si la question parle de mois
        if any(kw in query for kw in ["par mois", "mois", "mensuel", "mois où", "mois avec", "mois le plus", "mois ayant"]):
            if "month" in all_dimensions and "month" not in dimensions:
                dimensions.append("month")
            elif "date" in all_dimensions and "date" not in dimensions:
                dimensions.append("date")
        # Nettoyage strict : ne garder que les dimensions compatibles
        if metrics and metrics[0] in GA4_COMPAT:
            before = list(dimensions)
            dimensions = [d for d in dimensions if d in GA4_COMPAT[metrics[0]]]
            if before != dimensions:
                logging.info(f"[GA4 MCP] Dimensions nettoyées pour compatibilité avec la metric {metrics[0]} : {before} -> {dimensions}")
        if not metrics:
            logging.warning(f"[GA4 MCP] Aucune metric trouvée, fallback LLM.")
            return fallback_llm(query)
    # Si la question est trop complexe ou ne matche rien, indiquer qu'un LLM est nécessaire
    if not metrics and not dimensions:
        llm_needed = True
        suggestion = "Je n'ai pas compris la question, peux-tu la reformuler ou préciser ce que tu veux savoir ?"
    return {
        "metrics": metrics,
        "dimensions": dimensions,
        "date_range": date_range,
        "filters": filters,
        "limit": limit,
        "suggestion": suggestion,
        "llm_needed": llm_needed
    } 