"""Orchestrateur principal : transforme un document en score/diagnostic."""

from claimguard.ocr import extract_text
from claimguard.nlp import extract_entities
from claimguard.rules import apply_rules
from claimguard.scoring import compute_score


def validate_document(file_path: str) -> dict:
    """Exécute l'ensemble du pipeline sur un fichier physique.

    Retourne un dictionnaire comportant les entités extraites, les anomalies
    et le score global.
    """
    text = extract_text(file_path)
    entities = extract_entities(text)
    anomalies = apply_rules(entities)
    score = compute_score(anomalies)
    return {"entities": entities, "anomalies": anomalies, "score": score}
