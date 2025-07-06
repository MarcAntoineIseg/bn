#!/usr/bin/env python3
"""
Script de test pour vérifier que le pipeline NLP fonctionne correctement.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.nlp_service import analyze_question
from services.mapping_service import map_intent, validate_mapping
from services.payload_builder import build_payload
import json

def test_pipeline():
    """Test du pipeline complet avec la question problématique."""
    
    question = "nombre de visite sur mon site les 30 derniers jours"
    print(f"=== TEST DU PIPELINE NLP ===")
    print(f"Question: {question}")
    print()
    
    # 1. Analyse NLP
    print("1. Analyse NLP:")
    nlp_result = analyze_question(question)
    print(json.dumps(nlp_result, indent=2, ensure_ascii=False))
    print()
    
    # 2. Mapping
    print("2. Mapping:")
    mapping = map_intent(nlp_result)
    print(json.dumps(mapping, indent=2, ensure_ascii=False))
    print()
    
    # 3. Validation
    print("3. Validation:")
    validation = validate_mapping(mapping)
    print(json.dumps(validation, indent=2, ensure_ascii=False))
    print()
    
    # 4. Construction du payload
    if validation.get("is_valid", False):
        print("4. Construction du payload:")
        payload = build_payload(validation)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("4. ❌ Mapping invalide, pas de payload construit")
        print(f"Erreur: {validation.get('error')}")
        print(f"Suggestion: {validation.get('suggestion')}")
    
    print("=== FIN DU TEST ===")

if __name__ == "__main__":
    test_pipeline() 