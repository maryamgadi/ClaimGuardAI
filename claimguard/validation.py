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


def validate_claim(ordonnance_path: str, facture_path: str, feuille_path: str) -> dict:
    """Traite un dossier composé de trois documents.

    Chaque document est validé individuellement, puis nous appliquons des
    règles de cohérence (cross‑checking) entre eux.

    Args:
        ordonnance_path: chemin vers l'ordonnance.
        facture_path: chemin vers la facture.
        feuille_path: chemin vers la feuille de soin.

    Returns:
        Un dictionnaire contenant les résultats par document ainsi que les
        anomalies de cohérence et le score global de ces anomalies.
    """
    # valider chaque document séparément
    docs = {
        "ordonnance": validate_document(ordonnance_path),
        "facture": validate_document(facture_path),
        "feuille": validate_document(feuille_path),
    }

    # cross‑checking des entités
    from claimguard.rules.engine import cross_check

    entity_lists = [docs[k]["entities"] for k in ("ordonnance", "facture", "feuille")]
    cross_anomalies = cross_check(entity_lists)
    cross_score = compute_score(cross_anomalies)

    # décision finale : validé si aucune anomalie (documents + cross) sinon rejeté
    all_anomalies = []
    for d in docs.values():
        all_anomalies.extend(d.get("anomalies", []))
    all_anomalies.extend(cross_anomalies)
    decision = "validé_et_remboursé" if not all_anomalies else "rejeté"

    return {
        "documents": docs,
        "cross_anomalies": cross_anomalies,
        "cross_score": cross_score,
        "decision": decision,
    }
