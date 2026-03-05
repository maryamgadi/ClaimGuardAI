"""Scoring simple basé sur le nombre d'anomalies."""

from __future__ import annotations

from typing import List, Dict, Any

from claimguard.rules.engine import run_engine


def compute_score(anomalies: list) -> float:
    """Retourne un score entre 0.0 (mauvais) et 1.0 (parfait)."""
    if not anomalies:
        return 1.0
    return max(0.0, 1.0 - len(anomalies) * 0.1)


def compute_claim_score(all_anomalies: List[str], doc_scores: List[float]) -> float:
    """
    Combine:
      - pénalité anomalies (via compute_score)
      - scores documents (0..100)
    Retour: score final 0..1
    """
    anomaly_score = compute_score(all_anomalies)

    if not doc_scores:
        docs_score = 0.0
    else:
        docs_score = sum(max(0.0, min(100.0, float(s))) for s in doc_scores) / (100.0 * len(doc_scores))

    final = 0.6 * docs_score + 0.4 * anomaly_score
    return max(0.0, min(1.0, final))


def decision_from(claim_score: float, anomalies: List[str], threshold: float = 0.90) -> str:
    """
    ACCEPT si score >= threshold et pas d'anomalies critiques, sinon REVIEW
    """
    critical_keywords = ("FRAUDE", "MISMATCH", "INCOHERENCE", "INVALID", "REJET", "MISSING_")
    has_critical = any(any(k in (a or "").upper() for k in critical_keywords) for a in (anomalies or []))

    if claim_score >= threshold and not has_critical:
        return "ACCEPT"
    return "REVIEW"


def run_scoring(extractions: List[Dict[str, Any]], threshold: float = 0.90) -> Dict[str, Any]:
    """
    Appel unique: anomalies + score + décision.
    extractions = sorties de extract_entities(...)
    """
    report = run_engine(extractions)

    anomalies = report.get("anomalies", []) or []
    doc_scores = report.get("doc_scores", []) or []

    claim_score = compute_claim_score(anomalies, doc_scores)
    dec = decision_from(claim_score, anomalies, threshold=threshold)

    return {
        "decision": dec,
        "claim_score": round(float(claim_score), 4),
        "anomalies": anomalies,
        "doc_scores": doc_scores,
    }