"""
Service Mapping : mapping expert et validation de compatibilité metrics/dimensions.
"""

from utils.ga4_schema import is_valid_metric, is_valid_dimension, get_all_metrics, get_all_dimensions
from utils.ga4_query_parser import GA4_COMPAT

def map_intent(nlp_result: dict) -> dict:
    """
    Mappe l'intention détectée vers des metrics/dimensions GA4 valides.
    Peut enrichir ou corriger les résultats du NLP.
    """
    intent = nlp_result.get("intent", "general_analysis")
    metrics = nlp_result.get("metrics", [])
    dimensions = nlp_result.get("dimensions", [])
    
    # Enrichissement basé sur l'intention
    enriched_metrics = enrich_metrics_by_intent(intent, metrics)
    enriched_dimensions = enrich_dimensions_by_intent(intent, dimensions)
    
    return {
        **nlp_result,
        "metrics": enriched_metrics,
        "dimensions": enriched_dimensions
    }

def validate_mapping(mapping: dict) -> dict:
    """
    Valide la compatibilité metrics/dimensions (GA4_COMPAT).
    Retourne un dict :
      - is_valid (bool)
      - error (str, optionnel)
      - suggestion (str, optionnel)
      - mapping enrichi
    """
    metrics = mapping.get("metrics", [])
    dimensions = mapping.get("dimensions", [])
    
    # Validation des métriques
    invalid_metrics = [m for m in metrics if not is_valid_metric(m)]
    if invalid_metrics:
        return {
            "is_valid": False,
            "error": f"Métriques invalides : {invalid_metrics}",
            "suggestion": f"Métriques valides disponibles : {get_all_metrics()[:10]}..."
        }
    
    # Validation des dimensions
    invalid_dimensions = [d for d in dimensions if not is_valid_dimension(d)]
    if invalid_dimensions:
        return {
            "is_valid": False,
            "error": f"Dimensions invalides : {invalid_dimensions}",
            "suggestion": f"Dimensions valides disponibles : {get_all_dimensions()[:10]}..."
        }
    
    # Validation de compatibilité metrics/dimensions
    if metrics and dimensions:
        main_metric = metrics[0]
        if main_metric in GA4_COMPAT:
            allowed_dims = GA4_COMPAT[main_metric]
            incompatible_dims = [d for d in dimensions if d not in allowed_dims]
            if incompatible_dims:
                # Filtrer les dimensions incompatibles
                compatible_dims = [d for d in dimensions if d in allowed_dims]
                return {
                    "is_valid": True,
                    "warning": f"Dimensions incompatibles filtrées : {incompatible_dims}",
                    "suggestion": f"Dimensions compatibles avec {main_metric} : {allowed_dims[:10]}...",
                    **mapping,
                    "dimensions": compatible_dims
                }
    
    # Validation de la période
    date_range = mapping.get("date_range", {})
    if not date_range or not date_range.get("start_date") or not date_range.get("end_date"):
        return {
            "is_valid": False,
            "error": "Période manquante ou invalide",
            "suggestion": "Spécifiez une période valide (ex: '30 derniers jours', 'ce mois')"
        }
    
    return {
        "is_valid": True,
        **mapping
    }

def enrich_metrics_by_intent(intent: str, metrics: list) -> list:
    """Enrichit les métriques selon l'intention."""
    if not metrics:
        # Métriques par défaut selon l'intention (noms corrects GA4)
        default_metrics = {
            "visitor_analysis": ["sessions", "totalUsers"],
            "page_analysis": ["screenPageViews", "pageViews"],
            "traffic_analysis": ["sessions", "totalUsers"],
            "conversion_analysis": ["conversions", "transactions"],
            "geographic_analysis": ["sessions", "totalUsers"],
            "device_analysis": ["sessions", "totalUsers"],
            "general_analysis": ["sessions"]
        }
        return default_metrics.get(intent, ["sessions"])
    
    return metrics

def enrich_dimensions_by_intent(intent: str, dimensions: list) -> list:
    """Enrichit les dimensions selon l'intention."""
    if not dimensions:
        # Dimensions par défaut selon l'intention
        default_dimensions = {
            "visitor_analysis": ["date"],
            "page_analysis": ["pagePath", "pageTitle"],
            "traffic_analysis": ["source", "medium"],
            "conversion_analysis": ["date"],
            "geographic_analysis": ["country", "city"],
            "device_analysis": ["deviceCategory", "browser"],
            "general_analysis": ["date"]
        }
        return default_dimensions.get(intent, ["date"])
    
    return dimensions 