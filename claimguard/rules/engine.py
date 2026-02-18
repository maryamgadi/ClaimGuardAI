"""Implémentation minimaliste du moteur de règles."""


def apply_rules(entities: dict) -> list:
    """Évalue les règles métier sur un ensemble d'entités extraites.

    Retourne une liste d'anomalies détectées (vide si tout va bien).
    """
    anomalies = []
    if "social_number" not in entities:
        anomalies.append("numéro de sécurité sociale manquant")
    # d'autres règles peuvent être ajoutées dynamiquement
    return anomalies
