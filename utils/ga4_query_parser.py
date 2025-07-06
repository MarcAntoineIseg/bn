import re
from datetime import datetime, timedelta
from utils.ga4_schema import get_all_metrics, get_all_dimensions, is_valid_metric, is_valid_dimension
from utils.ga4_intents import detect_intent
import calendar

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
    "moyenne": "average",
    "moyen": "average",
    "en moyenne": "average",
    "moyennement": "average",
    "temps": "averageSessionDuration",
    "durée": "averageSessionDuration",
    "longtemps": "averageSessionDuration",
    "passe le plus de temps": "averageSessionDuration",
    "taux de conversion": "userConversionRate",
    "conversion rate": "userConversionRate",
    "mobile vs desktop": "deviceCategory",
    "desktop vs mobile": "deviceCategory",
    # Dimensions
    "pays": "country",
    "pays d'origine": "country",
    "country": "country",
    "ville": "city",
    "city": "city",
    "source": "source",
    "sources": "source",
    "canal": "sessionDefaultChannelGroup",
    "canaux": "sessionDefaultChannelGroup",
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
    "origine": "source",
    "acquisition": "sessionDefaultChannelGroup",
    "medium": "medium",
    "jour de la semaine": "dayOfWeekName",
    "meilleurs jours": "dayOfWeekName",
    "lundi": "dayOfWeekName",
    "mardi": "dayOfWeekName",
    "mercredi": "dayOfWeekName",
    "jeudi": "dayOfWeekName",
    "vendredi": "dayOfWeekName",
    "samedi": "dayOfWeekName",
    "dimanche": "dayOfWeekName",
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
    {
        "keywords": ["moyenne", "moyen", "en moyenne", "moyennement", "average"],
        "metrics": ["sessions", "averageSessionDuration"],
        "dimensions": ["date"],
        "suggestion": "Voici les données avec les moyennes calculées."
    },
    {
        "keywords": ["canal", "canaux", "source", "origine", "acquisition", "channel", "medium"],
        "dimensions": ["sessionDefaultChannelGroup", "source", "medium"],
        "suggestion": "Voici la répartition par canal/source d'acquisition."
    },
    {
        "keywords": ["temps", "durée", "longtemps", "passe le plus de temps", "temps moyen", "durée moyenne"],
        "metrics": ["averageSessionDuration"],
        "dimensions": ["pagePath"],
        "suggestion": "Voici la durée moyenne des sessions par page."
    },
    {
        "keywords": ["taux de conversion", "conversion rate", "mobile vs desktop", "desktop vs mobile", "taux conversion", "conversion mobile", "conversion desktop"],
        "metrics": ["userConversionRate"],
        "dimensions": ["deviceCategory"],
        "suggestion": "Voici le taux de conversion par device (mobile vs desktop)."
    },
    {
        "keywords": ["jour de la semaine", "meilleurs jours", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
        "dimensions": ["dayOfWeekName"],
        "suggestion": "Voici la répartition par jour de la semaine."
    },
    # ... à enrichir selon les besoins
]

# Mapping minimal de compatibilité metrics/dimensions GA4 (à enrichir selon la doc officielle)
GA4_COMPAT = {
    "screenPageViews": ["pagePath", "pageTitle", "country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"],
    "sessions": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source", "pagePath", "dayOfWeekName"],
    "totalUsers": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source", "pagePath"],
    "bounceRate": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source", "pagePath"],
    "averageSessionDuration": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source", "pagePath"],
    "conversions": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source", "pagePath", "medium"],
    "userConversionRate": ["deviceCategory", "country", "date", "sessionDefaultChannelGroup", "source", "pagePath"],
    # ... à enrichir pour chaque metric clé
}

PAID_CHANNELS = [
    "Paid Search", "Paid Social", "Paid Shopping", "Paid Video", "Paid Other", "Paid Display", "Paid Affiliate", "Paid Discovery", "Paid"  # pour matcher large
]

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
        # Prend le mois précédent complet
        today = datetime.today()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        return {"start_date": first_day_last_month.strftime('%Y-%m-%d'), "end_date": last_day_last_month.strftime('%Y-%m-%d')}
    elif "année dernière" in query or "l'année dernière" in query:
        year = datetime.today().year - 1
        return {"start_date": f"{year}-01-01", "end_date": f"{year}-12-31"}
    
    # Détection des mois spécifiques
    month_patterns = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"
    }
    
    current_year = datetime.now().year
    for month_name, month_num in month_patterns.items():
        if month_name in query:
            # Cherche l'année dans la question
            year_match = re.search(r'(\d{4})', query)
            year = int(year_match.group(1)) if year_match else current_year
            # Trouve le dernier jour du mois
            last_day = calendar.monthrange(year, int(month_num))[1]
            return {
                "start_date": f"{year}-{month_num}-01",
                "end_date": f"{year}-{month_num}-{last_day:02d}"
            }
    
    # Détection "X derniers mois"
    match = re.search(r'(\d+) derniers mois', query)
    if match:
        nb_months = int(match.group(1))
        today = datetime.today()
        # 1er jour du mois il y a nb_months
        first_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        for _ in range(nb_months-1):
            first_month = (first_month - timedelta(days=1)).replace(day=1)
        start_date = first_month.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        return {"start_date": start_date, "end_date": end_date}
    
    # Par défaut : depuis le début de GA4 (14 août 2015)
    return {"start_date": "2015-08-14", "end_date": "today"}

def adapt_metrics_for_average(query: str, metrics: list) -> list:
    """
    Adapte les métriques pour calculer des moyennes quand demandé.
    """
    query = query.lower()
    average_keywords = ["moyenne", "moyen", "en moyenne", "moyennement", "average"]
    
    if any(keyword in query for keyword in average_keywords):
        adapted_metrics = []
        for metric in metrics:
            if metric == "sessions":
                # Pour les sessions, on garde sessions mais on ajoute averageSessionDuration
                adapted_metrics.extend(["sessions", "averageSessionDuration"])
            elif metric == "totalUsers":
                # Pour les utilisateurs, on garde totalUsers et on ajoute averageSessionDuration
                adapted_metrics.extend(["totalUsers", "averageSessionDuration"])
            elif metric == "screenPageViews":
                # Pour les pages vues, on garde screenPageViews et on ajoute averageSessionDuration
                adapted_metrics.extend(["screenPageViews", "averageSessionDuration"])
            else:
                adapted_metrics.append(metric)
        
        # Supprimer les doublons
        return list(dict.fromkeys(adapted_metrics))
    
    return metrics

def validate_metrics_and_dimensions(metrics, dimensions):
    """
    Pour chaque métrique, ne garde que les dimensions compatibles. Si aucune dimension n'est compatible, ne force plus de fallback sur une dimension par défaut (total global si aucune dimension explicite).
    Retourne (metrics_valid, dimensions_valid, suggestions)
    """
    suggestions = []
    metrics_valid = []
    dimensions_valid = []
    for metric in metrics:
        if metric in GA4_COMPAT:
            dims_ok = [d for d in dimensions if d in GA4_COMPAT[metric]]
            if dims_ok:
                metrics_valid.append(metric)
                dimensions_valid += dims_ok
        else:
            # Si la métrique n'est pas dans le mapping, on la garde sans validation
            metrics_valid.append(metric)
    # Nettoyage doublons
    dimensions_valid = list(dict.fromkeys(dimensions_valid))
    metrics_valid = list(dict.fromkeys(metrics_valid))
    return metrics_valid, dimensions_valid, suggestions

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
        # Adaptation pour les moyennes
        metrics = adapt_metrics_for_average(query, metrics)
        
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
        # Si aucune date n'est détectée, utilise depuis le début de GA4 (2015-08-14)
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
        
        # Adaptation pour les moyennes
        metrics = adapt_metrics_for_average(query, metrics)
        
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
    metrics, dimensions, suggestions = validate_metrics_and_dimensions(metrics, dimensions)
    if suggestions: suggestion = (suggestion or "") + " " + " ".join(suggestions)
    # --- Règles métier supplémentaires ---
    # 1. Détection évolution (par mois)
    if any(kw in query for kw in ["évolution", "par mois", "mois", "mensuel", "mois par mois"]):
        if "month" not in dimensions:
            dimensions.append("month")
    # 2. Détection organique
    if any(kw in query for kw in ["organique", "seo", "organic"]):
        filters["sessionDefaultChannelGroup"] = "Organic Search"
    # 3. Détection paid
    if any(kw in query for kw in ["paid", "payant", "sea", "ads", "adwords", "sponsored", "cpc"]):
        filters["sessionDefaultChannelGroup"] = PAID_CHANNELS
    # Nettoyage : si filtre paid, transformer en filtre OR sur tous les paid
    if isinstance(filters.get("sessionDefaultChannelGroup"), list):
        # On construit un filtre OR GA4
        paid_values = filters["sessionDefaultChannelGroup"]
        filters["sessionDefaultChannelGroup"] = {"inListFilter": {"values": paid_values}}
    # Si la question contient canal/source/acquisition, prioriser cette dimension
    canal_keywords = ["canal", "canaux", "source", "origine", "acquisition", "channel", "medium"]
    if any(kw in query for kw in canal_keywords):
        # On force la dimension principale canal/source
        for dim in ["sessionDefaultChannelGroup", "source", "medium"]:
            if dim in dimensions:
                # On met la dimension canal/source en premier
                dimensions = [dim] + [d for d in dimensions if d != dim]
                break
        else:
            # Si aucune dimension canal/source n'est détectée, on l'ajoute
            dimensions = ["sessionDefaultChannelGroup"] + dimensions
    # Ajout dans parse_user_query (avant le return)
    duration_keywords = ["temps", "durée", "longtemps", "passe le plus de temps", "temps moyen", "durée moyenne"]
    if any(kw in query for kw in duration_keywords):
        # On force la métrique averageSessionDuration en priorité
        if "averageSessionDuration" not in metrics:
            metrics = ["averageSessionDuration"] + metrics
        else:
            # On met averageSessionDuration en premier
            metrics = [m for m in metrics if m != "averageSessionDuration"]
            metrics = ["averageSessionDuration"] + metrics
    # Ajout dans parse_user_query (avant le return)
    conversion_keywords = ["taux de conversion", "conversion rate", "mobile vs desktop", "desktop vs mobile", "taux conversion", "conversion mobile", "conversion desktop"]
    if any(kw in query for kw in conversion_keywords):
        # On force la métrique userConversionRate et la dimension deviceCategory
        if "userConversionRate" not in metrics:
            metrics = ["userConversionRate"] + metrics
        else:
            metrics = [m for m in metrics if m != "userConversionRate"]
            metrics = ["userConversionRate"] + metrics
        if "deviceCategory" not in dimensions:
            dimensions = ["deviceCategory"] + dimensions
        else:
            dimensions = [d for d in dimensions if d != "deviceCategory"]
            dimensions = ["deviceCategory"] + dimensions
        # On retire tout filtre sur deviceCategory pour permettre la comparaison
        if "deviceCategory" in filters:
            del filters["deviceCategory"]
    # Ajout dans parse_user_query (avant le return)
    dayofweek_keywords = ["jour de la semaine", "meilleurs jours", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    if any(kw in query for kw in dayofweek_keywords):
        if "dayOfWeekName" not in dimensions:
            dimensions = ["dayOfWeekName"] + dimensions
        else:
            dimensions = [d for d in dimensions if d != "dayOfWeekName"]
            dimensions = ["dayOfWeekName"] + dimensions
    return {
        "metrics": metrics,
        "dimensions": dimensions,
        "date_range": date_range,
        "filters": filters,
        "limit": limit,
        "suggestion": suggestion,
        "llm_needed": llm_needed
    } 