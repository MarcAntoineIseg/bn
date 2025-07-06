import re
from datetime import datetime, timedelta
from utils.ga4_schema import get_all_metrics, get_all_dimensions, is_valid_metric, is_valid_dimension
from utils.ga4_intents import detect_intent
import dateparser

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
            print(f"[GA4 MCP] Dimensions nettoyées pour compatibilité avec l'intention {intent}: {before} -> {dimensions}")
        # Cas particulier : top page unique
        if intent == "page_views" and ("top 1" in query or "page la plus vue" in query or "plus vue" in query):
            metrics = ["screenPageViews"]
            dimensions = ["pagePath"]
            limit = 1
            print("[GA4 MCP] Forçage mapping pour 'page la plus vue' : screenPageViews + pagePath, limit=1")
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
        # --- DÉTECTION AUTOMATIQUE DE PÉRIODE AVEC DATEPARSER ---
        # Recherche d'expressions de dates dans la question (français)
        date_matches = dateparser.search.search_dates(query, languages=['fr'])
        start_date, end_date = None, None
        if date_matches:
            # Si deux dates trouvées, on prend la première comme début, la deuxième comme fin
            if len(date_matches) >= 2:
                start_date = date_matches[0][1].date()
                end_date = date_matches[1][1].date()
            # Si une seule date trouvée
            elif len(date_matches) == 1:
                # Si la question contient 'depuis', on prend cette date comme début, fin = aujourd'hui
                if 'depuis' in query or 'à partir du' in query or 'à partir de' in query:
                    start_date = date_matches[0][1].date()
                    end_date = datetime.utcnow().date()
                # Sinon, on prend la date trouvée comme début ET fin
                else:
                    start_date = date_matches[0][1].date()
                    end_date = date_matches[0][1].date()
            # On formate les dates
            if start_date and end_date:
                date_range = {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }
                print(f"[GA4 MCP] Période détectée automatiquement par dateparser : {date_range}")
            else:
                # fallback manuel si parsing incomplet
                date_range = None
        # --- DÉTECTION PÉRIODE "30 DERNIERS JOURS" ---
        if not date_range:
            if (
                "30 derniers jours" in query
                or "trente derniers jours" in query
                or re.search(r"30 ?jours", query)
            ):
                end_date = datetime.utcnow().date()
                start_date = end_date - timedelta(days=29)
                date_range = {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }
            else:
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
        # Nettoyage : pour les questions top pages, ne garder que pagePath
        if any(kw in query for kw in ["top", "pages", "plus vues", "meilleures pages", "page la plus visitée"]):
            if "pagePath" in dimensions:
                dimensions = ["pagePath"]
    # --- Validation de compatibilité metrics/dimensions ---
    main_metric = metrics[0] if metrics else None
    if main_metric and main_metric in GA4_COMPAT:
        compatible_dims = GA4_COMPAT[main_metric]
        before = list(dimensions)
        dimensions = [d for d in dimensions if d in compatible_dims]
        if before != dimensions:
            print(f"[GA4 MCP] Dimensions nettoyées pour compatibilité avec {main_metric}: {before} -> {dimensions}")
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