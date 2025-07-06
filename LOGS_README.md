# Système de Logs - GA4 MCP

## Vue d'ensemble

Le système de logs de l'application GA4 MCP permet de tracer en détail tous les appels à l'API Google Analytics 4, les requêtes MCP, et les appels API REST.

## Configuration

### Fichiers de logs

- **Console** : Tous les logs sont affichés dans la console
- **Fichier** : Les logs sont sauvegardés dans `logs/ga4_mcp.log`

### Niveaux de logs

- `DEBUG` : Informations détaillées pour le débogage
- `INFO` : Informations générales (par défaut)
- `WARNING` : Avertissements
- `ERROR` : Erreurs
- `CRITICAL` : Erreurs critiques

## Types de logs

### 1. Logs API GA4 (`[GA4 API]`)

Tracent tous les appels à l'API Google Analytics 4 :

```
[GA4 API] === DÉBUT run_dynamic_report ===
[GA4 API] Property ID: 123456789
[GA4 API] Metrics: ['sessions', 'users']
[GA4 API] Dimensions: ['country', 'city']
[GA4 API] Date range: {'start_date': '2024-01-01', 'end_date': '2024-01-31'}
[GA4 API] Filters: {}
[GA4 API] Limit: 100
[GA4 API] URL complète: https://analyticsdata.googleapis.com/v1beta/properties/123456789:runReport
[GA4 API] Headers: {'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'}
[GA4 API] Body complet: {
  "dateRanges": [{"startDate": "2024-01-01", "endDate": "2024-01-31"}],
  "metrics": [{"name": "sessions"}, {"name": "users"}],
  "dimensions": [{"name": "country"}, {"name": "city"}],
  "limit": 100
}
[GA4 API] Envoi de la requête...
[GA4 API] Status code reçu: 200
[GA4 API] ✅ Réponse JSON reçue
[GA4 API] Nombre de lignes dans la réponse: 50
[GA4 API] Dimension headers: ['country', 'city']
[GA4 API] Metric headers: ['sessions', 'users']
[GA4 API] Première ligne de données: {...}
[GA4 API] === FIN run_dynamic_report ===
[GA4 API] Nombre total d'entrées retournées: 50
```

### 2. Logs MCP (`[MCP]`)

Tracent les appels aux outils MCP :

```
[MCP] === DÉBUT ask_ga4_report ===
[MCP] userId: user123
[MCP] ga4PropertyId: 123456789
[MCP] question: Combien de sessions par pays ce mois-ci ?
[MCP] Analyse de la question...
[MCP] Paramètres extraits:
[MCP]   - metrics: ['sessions']
[MCP]   - dimensions: ['country']
[MCP]   - date_range: {'start_date': '2024-01-01', 'end_date': '2024-01-31'}
[MCP]   - filters: {}
[MCP]   - limit: 100
[MCP]   - suggestion: None
[MCP]   - llm_needed: False
[MCP] Date système actuelle : 2024-01-15 10:30:00+00:00
[MCP] Récupération des tokens utilisateur...
[MCP] ✅ Tokens rafraîchis avec succès
[MCP] Appel à run_dynamic_report...
[MCP] ✅ Résultat obtenu avec succès - 50 entrées
```

### 3. Logs API REST (`[REST API]`)

Tracent les appels à l'API REST :

```
[REST API] === DÉBUT query_ga4 ===
[REST API] userId: user123
[REST API] ga4PropertyId: 123456789
[REST API] metrics: ['sessions', 'users']
[REST API] dimensions: ['country']
[REST API] date_range: {'start_date': '2024-01-01', 'end_date': '2024-01-31'}
[REST API] filters: {}
[REST API] limit: 100
[REST API] Validation des métriques et dimensions...
[REST API] ✅ Validation réussie
[REST API] Récupération des tokens utilisateur...
[REST API] ✅ Tokens rafraîchis avec succès
[REST API] Appel à run_dynamic_report...
[REST API] ✅ Résultat obtenu avec succès - 50 entrées
```

## Utilisation

### Dans le code

```python
from utils.logger_config import get_api_logger, get_mcp_logger, get_rest_logger

# Logger API GA4
api_logger = get_api_logger()
api_logger.info("Message d'information")
api_logger.error("Message d'erreur")

# Logger MCP
mcp_logger = get_mcp_logger()
mcp_logger.info("Message MCP")

# Logger REST
rest_logger = get_rest_logger()
rest_logger.info("Message REST")
```

### Fonctions de log standardisées

```python
from utils.logger_config import log_api_call, log_api_response

# Log d'un appel API
log_api_call(logger, "/v1beta/properties/123:runReport", "POST", 
             property_id="123", metrics=["sessions"])

# Log d'une réponse API
log_api_response(logger, 200, {"data": "success"})
log_api_response(logger, 400, error="Invalid request")
```

## Sécurité

- Les tokens d'accès sont masqués dans les logs (seuls les 20 premiers caractères sont affichés)
- Les informations sensibles ne sont pas loggées

## Surveillance

### Vérifier les logs en temps réel

```bash
# Suivre les logs en temps réel
tail -f logs/ga4_mcp.log

# Filtrer les erreurs
grep "ERROR" logs/ga4_mcp.log

# Filtrer les appels API
grep "\[GA4 API\]" logs/ga4_mcp.log
```

### Rotation des logs

Les logs peuvent être configurés pour la rotation automatique en modifiant `utils/logger_config.py`.

## Dépannage

### Problèmes courants

1. **Logs vides** : Vérifier les permissions du dossier `logs/`
2. **Logs trop verbeux** : Réduire le niveau de log à `WARNING`
3. **Fichier de log trop volumineux** : Activer la rotation des logs

### Test des logs

```bash
python test_logs.py
```

## Configuration avancée

Pour personnaliser la configuration des logs, modifiez `utils/logger_config.py` :

```python
# Logger avec niveau DEBUG et rotation
logger = setup_logger(
    name="ga4_debug",
    level="DEBUG",
    log_to_file=True,
    log_file="logs/ga4_debug.log"
)
``` 