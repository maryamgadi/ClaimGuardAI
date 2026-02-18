"""Pipeline NLP basique pour l'extraction de champs clés."""

import re


def extract_entities(text: str) -> dict:
    """Retourne un dictionnaire de champs extraits à partir du texte.

    Les expressions régulières sont provisoires et doivent être
    ajustées selon le format réel des documents.
    """
    entities = {}
    # exemple de regex pour numéro de sécurité sociale
    ssn_match = re.search(r"\b\d{3}-\d{2}-\d{4}\b", text)
    if ssn_match:
        entities["social_number"] = ssn_match.group(0)
    # autres champs : dates, montants, noms, etc.
    return entities
