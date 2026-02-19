from __future__ import annotations

from typing import List, Dict, Optional
from claimguard.schemas import DocExtraction, Finding
from configs.config import WEIGHTS

REQUIRED_FIELDS = {
    "feuille_soins": ["cin", "immatriculation_cnss", "nom_assure", "date_soins", "montant_total"],
    "facture": ["date_facture", "montant_total", "acquittee"],
    "ordonnance": ["date_ordonnance", "signature_medecin"],
}

ALL_DOCS = ["feuille_soins", "facture", "ordonnance"]


def _get_field(doc: DocExtraction, name: str) -> Optional[str]:
    f = doc.fields.get(name)
    if not f:
        return None
    return f.value


def _to_float(x) -> Optional[float]:
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None


def run_rules(extractions: List[DocExtraction]) -> List[Finding]:
    findings: List[Finding] = []

    # Index docs by type
    docs: Dict[str, DocExtraction] = {d.doc_type: d for d in extractions}

    # Missing docs
    for doc_type in ALL_DOCS:
        if doc_type not in docs:
            findings.append(
                Finding(
                    code="MISSING_DOC",
                    message=f"Document manquant: {doc_type}",
                    severity="blocker",
                    weight=WEIGHTS["MISSING_DOC"],
                    details={"doc_type": doc_type},
                )
            )

    # Required fields per doc
    for doc_type, req in REQUIRED_FIELDS.items():
        doc = docs.get(doc_type)
        if not doc:
            continue
        for field in req:
            v = _get_field(doc, field)
            if v is None or str(v).strip() == "":
                findings.append(
                    Finding(
                        code="MISSING_REQUIRED_FIELD",
                        message=f"Champ obligatoire manquant: {field} ({doc_type})",
                        severity="high",
                        weight=WEIGHTS["MISSING_REQUIRED_FIELD"],
                        details={"doc_type": doc_type, "field": field},
                    )
                )

    # Facture acquittée
    fact = docs.get("facture")
    if fact:
        acquit = (_get_field(fact, "acquittee") or "").strip().lower()
        if acquit in ["no", "non", "false", "0"]:
            findings.append(
                Finding(
                    code="FACTURE_NOT_ACQUITTED",
                    message="Facture non acquittée (pas de mention payé/acquittée)",
                    severity="blocker",
                    weight=WEIGHTS["FACTURE_NOT_ACQUITTED"],
                    details={},
                )
            )

    # Cross-check: amounts (feuille vs facture) -> compare float
    feuille = docs.get("feuille_soins")
    if feuille and fact:
        a1 = _to_float(_get_field(feuille, "montant_total"))
        a2 = _to_float(_get_field(fact, "montant_total"))
        if a1 is not None and a2 is not None and abs(a1 - a2) > 0.01:
            findings.append(
                Finding(
                    code="AMOUNT_MISMATCH",
                    message="Montant total incohérent entre feuille de soins et facture",
                    severity="high",
                    weight=WEIGHTS["AMOUNT_MISMATCH"],
                    details={"feuille": str(a1), "facture": str(a2)},
                )
            )

    # Cross-check: name match (normalize)
    if feuille and fact:
        n1 = (_get_field(feuille, "nom_assure") or "").strip().upper()
        n2 = (_get_field(fact, "nom_assure") or "").strip().upper()
        if n1 and n2 and n1 != n2:
            findings.append(
                Finding(
                    code="NAME_MISMATCH",
                    message="Nom incohérent entre documents",
                    severity="high",
                    weight=WEIGHTS["NAME_MISMATCH"],
                    details={"feuille": n1, "facture": n2},
                )
            )

    return findings