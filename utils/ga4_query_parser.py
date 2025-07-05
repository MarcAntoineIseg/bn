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

# Mois français pour extraction
MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]
MONTHS_EN = [
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"
]

# Détection de question comparative
def is_comparative_question(query):
    return any(x in query for x in ["par rapport à", "vs", "comparé à", "avant", "après", "évolution entre", "évolution de", "différence entre"])

# Extraction de deux périodes (mois) dans la question
# Retourne deux dicts date_range si trouvé, sinon None

def extract_periods(query):
    # Recherche deux mois (français ou anglais) dans la question
    months = MONTHS_FR + MONTHS_EN
    found = []
    for m in months:
        if m in query:
            found.append(m)
    if len(found) >= 2:
        # On prend les deux premiers mois trouvés
        now = datetime.now()
        year = now.year
        def month_to_num(m):
            if m in MONTHS_FR:
                return MONTHS_FR.index(m) + 1
            else:
                return MONTHS_EN.index(m) + 1
        m1, m2 = found[0], found[1]
        d1 = {"start_date": f"{year}-{month_to_num(m1):02d}-01", "end_date": f"{year}-{month_to_num(m1):02d}-{last_day_of_month(year, month_to_num(m1))}"}
        d2 = {"start_date": f"{year}-{month_to_num(m2):02d}-01", "end_date": f"{year}-{month_to_num(m2):02d}-{last_day_of_month(year, month_to_num(m2))}"}
        return d1, d2
    return None, None

def last_day_of_month(year, month):
    if month == 12:
        return 31
    return (datetime(year, month+1, 1) - timedelta(days=1)).day

def parse_user_query(query: str):
    """
    Parse une question utilisateur pour extraire metrics, dimensions, date_range, filters, limit, suggestion, llm_needed, comparative.
    Utilise d'abord le router d'intention (GA4_INTENTS), puis fallback dynamique.
    Si question comparative, retourne comparative avec les deux périodes à interroger.
    """
    query = query.lower()
    filters = {}
    suggestion = None
    limit = None
    llm_needed = False
    comparative = None

    all_metrics = get_all_metrics()
    all_dimensions = get_all_dimensions()

    # 0. Détection question comparative
    if is_comparative_question(query):
        d1, d2 = extract_periods(query)
        if d1 and d2:
            comparative = {"period1": d1, "period2": d2}
            suggestion = f"Comparaison détectée entre {d1} et {d2}."

    # 1. Router d'intention (mapping expert)
    intent, config = detect_intent(query)
    if config:
        metrics = list(config["metrics"])
        dimensions = []
        for d in config["dimensions"]:
            if d in query:
                dimensions.append(d)
        if not dimensions:
            dimensions = [config["dimensions"][0]]
        date_range = dict(config["default_time_range"])
        match = re.search(r'top ?(\d+)', query)
        if match:
            limit = int(match.group(1))
        elif "top cinq" in query:
            limit = 5
        elif "top dix" in query:
            limit = 10
        elif any(kw in query for kw in ["top", "meilleurs", "plus vues", "plus visités", "plus visitées"]):
            limit = 10
        if "france" in query:
            filters["country"] = "France"
        if "mobile" in query:
            filters["deviceCategory"] = "mobile"
        if "desktop" in query or "ordinateur" in query:
            filters["deviceCategory"] = "desktop"
        if not suggestion:
            suggestion = f"Intent détecté : {intent}."
    else:
        metrics = []
        dimensions = []
        for word, ga4_name in SYNONYMS.items():
            if word in query:
                if ga4_name in all_metrics and ga4_name not in metrics:
                    metrics.append(ga4_name)
                if ga4_name in all_dimensions and ga4_name not in dimensions:
                    dimensions.append(ga4_name)
        for metric in all_metrics:
            if metric.lower() in query and metric not in metrics:
                metrics.append(metric)
        for dimension in all_dimensions:
            if dimension.lower() in query and dimension not in dimensions:
                dimensions.append(dimension)
        date_range = {"start_date": "2005-01-01", "end_date": "today"}
        match = re.search(r'top ?(\d+)', query)
        if match:
            limit = int(match.group(1))
        elif "top cinq" in query:
            limit = 5
        elif "top dix" in query:
            limit = 10
        elif any(kw in query for kw in ["top", "meilleurs", "plus vues", "plus visités", "plus visitées"]):
            limit = 10
        if "france" in query:
            filters["country"] = "France"
        if "mobile" in query:
            filters["deviceCategory"] = "mobile"
        if "desktop" in query or "ordinateur" in query:
            filters["deviceCategory"] = "desktop"
        if not suggestion:
            suggestion = "Aucune intention explicite détectée, fallback dynamique."
        if not metrics:
            metrics = ["sessions"]
        if any(kw in query for kw in ["top", "pages", "plus vues", "meilleures pages", "page la plus visitée"]):
            if "pagePath" in dimensions:
                dimensions = ["pagePath"]
    main_metric = metrics[0] if metrics else None
    if main_metric and main_metric in GA4_COMPAT:
        compatible_dims = GA4_COMPAT[main_metric]
        before = list(dimensions)
        dimensions = [d for d in dimensions if d in compatible_dims]
        if before != dimensions:
            print(f"[GA4 MCP] Dimensions nettoyées pour compatibilité avec {main_metric}: {before} -> {dimensions}")
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
        "llm_needed": llm_needed,
        "comparative": comparative
    } 