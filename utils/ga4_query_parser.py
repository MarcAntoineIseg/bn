import re
from datetime import datetime, timedelta

def parse_user_query(query: str):
    """
    Parse une question utilisateur en français pour extraire metrics, dimensions, date_range et filters.
    Retourne un dictionnaire prêt à être utilisé pour get_ga4_report.
    """
    query = query.lower()
    metrics = []
    dimensions = []
    filters = {}
    date_range = {"start_date": "30daysAgo", "end_date": "today"}

    # Métriques
    if "session" in query:
        metrics.append("sessions")
    if "utilisateur" in query or "user" in query:
        metrics.append("totalUsers")
    if "revenu" in query:
        metrics.append("totalRevenue")
    if "conversion" in query:
        metrics.append("conversions")
    # Ajoute d'autres règles selon les besoins

    # Dimensions
    if "par pays" in query or "country" in query or "france" in query:
        dimensions.append("country")
    if "par date" in query or "jour" in query or "date" in query:
        dimensions.append("date")
    if "ville" in query or "city" in query:
        dimensions.append("city")
    # Ajoute d'autres règles selon les besoins

    # Filtres
    if "france" in query:
        filters["country"] = "France"
    if "mobile" in query:
        filters["deviceCategory"] = "mobile"
    # Ajoute d'autres règles selon les besoins

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
    # Ajoute d'autres règles selon les besoins

    # Valeurs par défaut si rien trouvé
    if not metrics:
        metrics = ["sessions"]
    return {
        "metrics": metrics,
        "dimensions": dimensions,
        "date_range": date_range,
        "filters": filters
    } 