"""
Service Formatter : formatage de la réponse utilisateur (tableau, suggestion, erreur, etc.).
"""

def format_response(data=None, mapping=None, error=None, suggestion=None) -> dict:
    """
    Formate la réponse pour l'utilisateur :
    - data (résultat GA4)
    - mapping utilisé
    - erreur éventuelle
    - suggestion éventuelle
    """
    if error:
        return {"error": error, "suggestion": suggestion}
    return {
        "data": data,
        "mapping": mapping,
        "suggestion": suggestion
    } 