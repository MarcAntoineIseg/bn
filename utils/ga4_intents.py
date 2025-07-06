GA4_INTENTS = {
    "page_views": {
        "keywords": ["page vue", "pages vues", "top pages", "meilleures pages", "page la plus visitée", "plus vues"],
        "metrics": ["screenPageViews"],
        "dimensions": ["pagePath", "pageTitle", "country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"]
    },
    "active_users": {
        "keywords": ["utilisateur actif", "utilisateurs actifs", "active users", "utilisateurs", "users"],
        "metrics": ["activeUsers"],
        "dimensions": ["date", "country", "deviceCategory", "sessionDefaultChannelGroup", "source"]
    },
    "bounce_rate": {
        "keywords": ["taux de rebond", "bounce rate", "rebond"],
        "metrics": ["bounceRate"],
        "dimensions": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"]
    },
    "session_duration": {
        "keywords": ["durée moyenne", "temps moyen", "average session duration", "durée session"],
        "metrics": ["averageSessionDuration"],
        "dimensions": ["country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"]
    },
    "conversions": {
        "keywords": ["conversion", "conversions", "event", "événement", "achats", "transactions"],
        "metrics": ["conversions"],
        "dimensions": ["eventName", "country", "date", "deviceCategory", "sessionDefaultChannelGroup", "source"]
    },
    # ... à enrichir selon les besoins
}

def detect_intent(query):
    for intent, config in GA4_INTENTS.items():
        if any(kw in query for kw in config["keywords"]):
            return intent, config
    return None, None 