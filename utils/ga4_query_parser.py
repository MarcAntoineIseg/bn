import re
from datetime import datetime, timedelta
from utils.ga4_schema import get_all_metrics, get_all_dimensions

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

def parse_user_query(query: str):
    """
    Parse une question utilisateur pour extraire metrics, dimensions, date_range, filters, limit, suggestion, llm_needed.
    Gère le top N, les recettes, les synonymes, et détecte les cas complexes.
    """
    query = query.lower()
    metrics = []
    dimensions = []
    filters = {}
    date_range = {"start_date": "30daysAgo", "end_date": "today"}
    suggestion = None
    limit = None
    llm_needed = False

    all_metrics = get_all_metrics()
    all_dimensions = get_all_dimensions()

    # 1. Règles intelligentes (recettes)
    for rule in SMART_RULES:
        if any(kw in query for kw in rule.get("keywords", [])):
            for dim in rule.get("dimensions", []):
                if dim in all_dimensions and dim not in dimensions:
                    dimensions.append(dim)
            for met in rule.get("metrics", []):
                if met in all_metrics and met not in metrics:
                    metrics.append(met)
            if rule.get("suggestion"):
                suggestion = rule["suggestion"]

    # 2. Matching via synonymes/traductions
    for word, ga4_name in SYNONYMS.items():
        if word in query:
            if ga4_name in all_metrics and ga4_name not in metrics:
                metrics.append(ga4_name)
            if ga4_name in all_dimensions and ga4_name not in dimensions:
                dimensions.append(ga4_name)

    # 3. Matching dynamique sur les metrics
    for metric in all_metrics:
        if metric.lower() in query and metric not in metrics:
            metrics.append(metric)

    # 4. Matching dynamique sur les dimensions
    for dimension in all_dimensions:
        if dimension.lower() in query and dimension not in dimensions:
            dimensions.append(dimension)

    # 5. Gestion du top N (top 5, top 10, etc.)
    match = re.search(r'top ?(\d+)', query)
    if match:
        limit = int(match.group(1))
    elif "top cinq" in query:
        limit = 5
    elif "top dix" in query:
        limit = 10
    elif any(kw in query for kw in ["top", "meilleurs", "plus vues", "plus visités", "plus visitées"]):
        limit = 10

    # Filtres simples (exemple)
    if "france" in query:
        filters["country"] = "France"
    if "mobile" in query:
        filters["deviceCategory"] = "mobile"
    if "desktop" in query or "ordinateur" in query:
        filters["deviceCategory"] = "desktop"

    # Plage de dates
    if "semaine dernière" in query:
        today = datetime.today()
        last_week = today - timedelta(days=7)
        date_range = {
            "start_date": last_week.strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d")
        }
    elif "mois dernier" in query:
        today = datetime.today()
        first_day_this_month = today.replace(day=1)
        last_month_end = first_day_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        date_range = {
            "start_date": last_month_start.strftime("%Y-%m-%d"),
            "end_date": last_month_end.strftime("%Y-%m-%d")
        }

    # Valeur par défaut si aucune metric trouvée
    if not metrics:
        metrics = ["sessions"]

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