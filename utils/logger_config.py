import logging
import sys
from datetime import datetime

def setup_logger(name: str = "ga4_mcp", level: str = "INFO", log_to_file: bool = False, log_file: str = "ga4_mcp.log"):
    """
    Configure un logger centralisé pour l'application GA4 MCP.
    
    Args:
        name: Nom du logger
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Si True, écrit aussi dans un fichier
        log_file: Nom du fichier de log
    """
    
    # Configuration du format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configuration du logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Supprime les handlers existants pour éviter les doublons
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Handler pour la console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler pour le fichier (optionnel)
    if log_to_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str = "ga4_mcp"):
    """Récupère un logger configuré."""
    return logging.getLogger(name)

# Configuration par défaut
DEFAULT_LOGGER = setup_logger(
    name="ga4_mcp",
    level="INFO",
    log_to_file=True,
    log_file="logs/ga4_mcp.log"
)

# Loggers spécialisés
def get_api_logger():
    """Logger pour les appels API GA4."""
    return get_logger("ga4_api")

def get_mcp_logger():
    """Logger pour les outils MCP."""
    return get_logger("ga4_mcp")

def get_rest_logger():
    """Logger pour l'API REST."""
    return get_logger("ga4_rest")

def log_api_call(logger, endpoint: str, method: str = "POST", **kwargs):
    """Log standardisé pour les appels API."""
    logger.info(f"[API CALL] {method} {endpoint}")
    for key, value in kwargs.items():
        if key == "access_token" and value:
            # Masque le token pour la sécurité
            logger.info(f"[API CALL] {key}: {value[:20]}...")
        else:
            logger.info(f"[API CALL] {key}: {value}")

def log_api_response(logger, status_code: int, response_data: dict = None, error: str = None):
    """Log standardisé pour les réponses API."""
    if status_code == 200:
        logger.info(f"[API RESPONSE] ✅ Status: {status_code}")
        if response_data:
            logger.info(f"[API RESPONSE] Data: {response_data}")
    else:
        logger.error(f"[API RESPONSE] ❌ Status: {status_code}")
        if error:
            logger.error(f"[API RESPONSE] Error: {error}") 