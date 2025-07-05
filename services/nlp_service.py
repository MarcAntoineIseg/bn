"""
Service NLP : analyse sémantique de la question utilisateur (LLM + fallback règles).
"""

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
    # --- Exemple de logique ---
    # 1. Tenter d'utiliser un LLM (OpenAI, Gemini, etc.)
    # 2. Si le LLM échoue, fallback sur des patterns/règles
    # (À implémenter selon ton stack)
    return {
        "intent": None,
        "metrics": [],
        "dimensions": [],
        "date_range": {},
        "filters": {},
        "top_n": None
    } 