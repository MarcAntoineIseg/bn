import re
from datetime import datetime, timedelta
from utils.ga4_schema import get_all_metrics, get_all_dimensions, is_valid_metric, is_valid_dimension
from utils.ga4_intents import detect_intent

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

def detect_date_range(query: str) -> dict:
    """
    Détecte la plage de dates dans la question utilisateur.
    Retourne un dict avec start_date et end_date.
    """
    query = query.lower()
    
    # Détection des plages relatives
    if "30 derniers jours" in query or "30 jours" in query:
        return {"start_date": "30daysAgo", "end_date": "today"}
    elif "7 derniers jours" in query or "semaine dernière" in query or "cette semaine" in query:
        return {"start_date": "7daysAgo", "end_date": "today"}
    elif "hier" in query:
        return {"start_date": "yesterday", "end_date": "yesterday"}
    elif "aujourd'hui" in query or "ce jour" in query:
        return {"start_date": "today", "end_date": "today"}
    elif "mois dernier" in query or "le mois dernier" in query:
        return {"start_date": "30daysAgo", "end_date": "today"}
    elif "année dernière" in query or "l'année dernière" in query:
        return {"start_date": "365daysAgo", "end_date": "today"}
    
    # Par défaut : 30 derniers jours
    return {"start_date": "30daysAgo", "end_date": "today"}

def parse_user_query(query: str):
    """
    Parse une question utilisateur pour extraire metrics, dimensions, date_range, filters, limit, suggestion, llm_needed.
    Utilise d'abord le router d'intention (GA4_INTENTS), puis fallback dynamique.
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
        # Détection intelligente de la plage de dates
        detected_range = detect_date_range(query)
        date_range = detected_range if detected_range != {"start_date": "30daysAgo", "end_date": "today"} else dict(config["default_time_range"])
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
        # Détection intelligente de la plage de dates
        date_range = detect_date_range(query)
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