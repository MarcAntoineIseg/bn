"""
Service PayloadBuilder : construction dynamique du payload GA4 à partir du mapping validé.
"""

def build_payload(mapping: dict) -> dict:
    """
    Construit dynamiquement le payload pour l'API GA4 à partir du mapping validé.
    Gère le tri, le top N, les filtres, la période, etc.
    """
    # Exemple de logique :
    payload = {
        "metrics": mapping.get("metrics", []),
        "dimensions": mapping.get("dimensions", []),
        "date_range": mapping.get("date_range", {}),
        "filters": mapping.get("filters", {}),
        "limit": mapping.get("top_n", 100)
    }
    return payload 