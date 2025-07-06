"""
Service PayloadBuilder : construction dynamique du payload GA4 à partir du mapping validé.
"""

from datetime import datetime, timedelta

def build_payload(mapping: dict) -> dict:
    """
    Construit dynamiquement le payload pour l'API GA4 à partir du mapping validé.
    Gère le tri, le top N, les filtres, la période, etc.
    """
    metrics = mapping.get("metrics", [])
    dimensions = mapping.get("dimensions", [])
    date_range = mapping.get("date_range", {})
    filters = mapping.get("filters", {})
    top_n = mapping.get("top_n", 100)
    
    # Validation et valeurs par défaut
    if not metrics:
        metrics = ["sessions"]
    
    # Si pas de dimensions, ajouter la dimension date par défaut
    if not dimensions:
        dimensions = ["date"]
    
    # Validation de la période
    if not date_range or not date_range.get("start_date") or not date_range.get("end_date"):
        # Période par défaut : 30 derniers jours
        today = datetime.now()
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        date_range = {
            "start_date": start_date,
            "end_date": end_date
        }
    
    # Validation du limit
    if not top_n or top_n <= 0:
        top_n = 100
    elif top_n > 1000:  # Limite GA4
        top_n = 1000
    
    payload = {
        "metrics": metrics,
        "dimensions": dimensions,
        "date_range": date_range,
        "filters": filters,
        "limit": top_n
    }
    
    return payload 