from typing import List, Tuple
from claimguard.schemas import Finding, Decision

# Tu peux bouger ça dans configs/config.py si tu veux
ACCEPT_THRESHOLD = 85.0

def score_case(findings: List[Finding]) -> Tuple[float, Decision]:
    """
    Score 0..100.
    On soustrait weight*100 pour chaque finding.
    Décision: ACCEPT si score >= seuil ET aucun blocker.
    """
    penalty = 0.0
    has_blocker = False

    for f in findings or []:
        penalty += max(0.0, float(f.weight)) * 100.0
        if f.severity == "blocker":
            has_blocker = True

    score = max(0.0, 100.0 - penalty)
    decision: Decision = "ACCEPT" if (score >= ACCEPT_THRESHOLD and not has_blocker) else "REVIEW"
    return score, decision