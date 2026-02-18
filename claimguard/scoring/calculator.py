"""Scoring simple basé sur le nombre d'anomalies."""

def compute_score(anomalies: list) -> float:
    """Retourne un score entre 0.0 (mauvais) et 1.0 (parfait).

    Plus il y a d'anomalies, plus le score est bas. Méthode stub.
    """
    if not anomalies:
        return 1.0
    return max(0.0, 1.0 - len(anomalies) * 0.1)
