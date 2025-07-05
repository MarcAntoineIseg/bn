import json
import os

# Chemins vers les fichiers JSON
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_PATH = os.path.join(BASE_DIR, 'ga4_metrics_json.json')
DIMENSIONS_PATH = os.path.join(BASE_DIR, 'ga4_dimensions_json.json')

# Chargement des métriques
try:
    with open(METRICS_PATH, 'r') as f:
        METRICS_SCHEMA = json.load(f)
except FileNotFoundError:
    METRICS_SCHEMA = {}

# Chargement des dimensions
try:
    with open(DIMENSIONS_PATH, 'r') as f:
        DIMENSIONS_SCHEMA = json.load(f)
except FileNotFoundError:
    DIMENSIONS_SCHEMA = {}

def get_all_metrics():
    """Retourne la liste de toutes les métriques disponibles."""
    metrics = []
    for group in METRICS_SCHEMA.values():
        metrics.extend(group.keys())
    return metrics

def get_all_dimensions():
    """Retourne la liste de toutes les dimensions disponibles."""
    dimensions = []
    for group in DIMENSIONS_SCHEMA.values():
        dimensions.extend(group.keys())
    return dimensions

def is_valid_metric(metric):
    return metric in get_all_metrics()

def is_valid_dimension(dimension):
    return dimension in get_all_dimensions()

def describe_metric(metric):
    for group in METRICS_SCHEMA.values():
        if metric in group:
            return group[metric]
    return None

def describe_dimension(dimension):
    for group in DIMENSIONS_SCHEMA.values():
        if dimension in group:
            return group[dimension]
    return None 