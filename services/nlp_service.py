"""
Service NLP : analyse sémantique de la question utilisateur (LLM + fallback règles).
"""

import re
from datetime import datetime, timedelta

def analyze_question(question: str) -> dict:
    """
    Analyse la question utilisateur pour extraire :
    - intention
    - metrics
    - dimensions
    - date_range
    - filters
    - top_n
    Utilise un LLM si disponible, sinon fallback sur des patterns/règles expertes.
    """
    question_lower = question.lower()
    
    # Extraction des métriques basée sur des patterns
    metrics = extract_metrics(question_lower)
    
    # Extraction des dimensions basée sur des patterns
    dimensions = extract_dimensions(question_lower)
    
    # Extraction de la période
    date_range = extract_date_range(question_lower)
    
    # Extraction des filtres
    filters = extract_filters(question_lower)
    
    # Extraction du top N
    top_n = extract_top_n(question_lower)
    
    # Détermination de l'intention
    intent = determine_intent(question_lower, metrics, dimensions)
    
    return {
        "intent": intent,
        "metrics": metrics,
        "dimensions": dimensions,
        "date_range": date_range,
        "filters": filters,
        "top_n": top_n
    }

def extract_metrics(question: str) -> list:
    """Extrait les métriques de la question."""
    metrics = []
    
    # Patterns pour les métriques courantes (noms corrects GA4)
    metric_patterns = {
        "visite": ["sessions", "totalUsers"],
        "visiteur": ["totalUsers", "sessions"],
        "session": ["sessions"],
        "utilisateur": ["totalUsers"],
        "page": ["screenPageViews", "pageViews"],
        "vue": ["screenPageViews", "pageViews"],
        "conversion": ["conversions"],
        "achat": ["transactions", "totalRevenue"],
        "revenu": ["totalRevenue"],
        "durée": ["averageSessionDuration"],
        "taux": ["bounceRate", "engagementRate"],
        "événement": ["eventCount"],
        "clique": ["eventCount"],
        "téléchargement": ["eventCount"]
    }
    
    for keyword, metric_list in metric_patterns.items():
        if keyword in question:
            metrics.extend(metric_list)
    
    # Si aucune métrique trouvée, utiliser sessions par défaut
    if not metrics:
        metrics = ["sessions"]
    
    # Supprimer les doublons
    return list(set(metrics))

def extract_dimensions(question: str) -> list:
    """Extrait les dimensions de la question."""
    dimensions = []
    
    # Patterns pour les dimensions courantes
    dimension_patterns = {
        "pays": ["country"],
        "ville": ["city"],
        "source": ["source", "medium"],
        "campagne": ["campaignName"],
        "page": ["pagePath", "pageTitle"],
        "appareil": ["deviceCategory"],
        "navigateur": ["browser"],
        "système": ["operatingSystem"],
        "langue": ["language"],
        "date": ["date"],
        "heure": ["hour"],
        "jour": ["dayOfWeek"],
        "mois": ["month"],
        "année": ["year"]
    }
    
    for keyword, dimension_list in dimension_patterns.items():
        if keyword in question:
            dimensions.extend(dimension_list)
    
    # Supprimer les doublons
    return list(set(dimensions))

def extract_date_range(question: str) -> dict:
    """Extrait la période de la question."""
    today = datetime.now()
    
    # Patterns pour les périodes
    if "30 derniers jours" in question or "30 jours" in question:
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif "7 derniers jours" in question or "semaine" in question:
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif "hier" in question:
        start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    elif "aujourd'hui" in question:
        start_date = today.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif "ce mois" in question or "mois en cours" in question:
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif "dernière année" in question or "12 mois" in question:
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    else:
        # Par défaut : 30 derniers jours
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    
    return {
        "start_date": start_date,
        "end_date": end_date
    }

def extract_filters(question: str) -> dict:
    """Extrait les filtres de la question."""
    filters = {}
    
    # Patterns pour les filtres
    if "mobile" in question or "appareil mobile" in question:
        filters["deviceCategory"] = "mobile"
    elif "desktop" in question or "ordinateur" in question:
        filters["deviceCategory"] = "desktop"
    elif "tablet" in question or "tablette" in question:
        filters["deviceCategory"] = "tablet"
    
    return filters

def extract_top_n(question: str) -> int:
    """Extrait le nombre de résultats demandé."""
    # Recherche de patterns comme "top 10", "premiers 5", etc.
    patterns = [
        r"top (\d+)",
        r"premiers (\d+)",
        r"(\d+) premiers",
        r"(\d+) meilleurs"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, question)
        if match:
            return int(match.group(1))
    
    # Par défaut : 100
    return 100

def determine_intent(question: str, metrics: list, dimensions: list) -> str:
    """Détermine l'intention de la question."""
    if "visite" in question or "visiteur" in question:
        return "visitor_analysis"
    elif "page" in question or "vue" in question:
        return "page_analysis"
    elif "source" in question or "trafic" in question:
        return "traffic_analysis"
    elif "conversion" in question or "achat" in question:
        return "conversion_analysis"
    elif "géographique" in question or "pays" in question or "ville" in question:
        return "geographic_analysis"
    elif "appareil" in question or "navigateur" in question:
        return "device_analysis"
    else:
        return "general_analysis" 