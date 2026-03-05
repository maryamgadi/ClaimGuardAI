from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple
import re


# =========================
# Normalisation / Similarité
# =========================

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    repl = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u",
        "ç": "c",
        "'": " ", "’": " ",
        "-": " ", "_": " ",
        ".": " ", ",": " ",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return " ".join(s.split())


def _tokenize_name(s: str) -> List[str]:
    toks = [t for t in _norm(s).split() if len(t) >= 2]
    stop = {"mme", "mr", "madame", "monsieur", "m", "mlle", "dr", "docteur", "pr"}
    return [t for t in toks if t not in stop]


def name_similarity(a: str, b: str) -> float:
    ta = _tokenize_name(a)
    tb = _tokenize_name(b)
    if not ta or not tb:
        return 0.0
    sa = " ".join(ta)
    sb = " ".join(tb)
    ratio = SequenceMatcher(None, sa, sb).ratio()
    set_a, set_b = set(ta), set(tb)
    jacc = len(set_a & set_b) / max(1, len(set_a | set_b))
    return 0.6 * ratio + 0.4 * jacc


def med_similarity(a: str, b: str) -> float:
    a = _norm(a)
    b = _norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def best_med_match(meds_a: List[str], meds_b: List[str]) -> float:
    if not meds_a or not meds_b:
        return 0.0
    best = 0.0
    for x in meds_a:
        for y in meds_b:
            best = max(best, med_similarity(str(x), str(y)))
    return best


def money_close(a: Any, b: Any, rel_tol: float = 0.02) -> Optional[bool]:
    """
    Retour:
      - True/False si les deux montants existent
      - None si un des montants est manquant/inparsable (=> ne pas déclencher mismatch dur)
    """
    def to_float(x):
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return float(s)
        except:
            return None

    fa = to_float(a)
    fb = to_float(b)
    if fa is None or fb is None:
        return None

    abs_tol = 0.5
    rel = rel_tol * max(abs(fa), abs(fb))
    return abs(fa - fb) <= max(abs_tol, rel)


# =========================
# Robustness CNSS (qualité champs)
# =========================

_CIN_RE = re.compile(r"\b[A-Z]{1,2}[0-9]{5,6}\b")


def cnss_name_quality(name: Any) -> float:
    """
    0..1 : estime si c'est un vrai nom ou bruit OCR.
    """
    raw = str(name or "").strip()
    n = _norm(raw)
    toks = [t for t in n.split() if len(t) >= 2]
    if len(toks) < 2:
        return 0.0
    letters = sum(ch.isalpha() for ch in n)
    if letters < 8:
        return 0.25
    # patterns bruit fréquents (comme ton "E IDci si ...")
    if raw.lower().startswith(("e id", "e...id", "e idci", "e idossi", "e...idossi")):
        return 0.25
    return 0.9


def cin_valid(x: Any) -> bool:
    """
    CIN attendu: 1-2 lettres + 5-6 chiffres.
    Si OCR renvoie "31" ou vide => False.
    """
    s = str(x or "").strip().upper()
    if not s:
        return False
    return bool(_CIN_RE.search(s))


# =========================
# Doc type detection
# =========================

def detect_doc_type(cleaned_text: str) -> Optional[str]:
    t = (cleaned_text or "").lower()

    if ("feuille de soins" in t) or ("cnss" in t and "soins" in t):
        return "feuille_cnss"
    if "beneficiaire de soins" in t or "montant des frais" in t:
        return "feuille_cnss"

    if "facture" in t and ("total" in t or "montant" in t or "designation" in t or "qte" in t):
        return "facture"
    if "pharmacie" in t and "facture" in t:
        return "facture"

    if ("dr" in t or "docteur" in t) and ("goutte" in t or "fois" in t or "jour" in t or "mois" in t or "renouveler" in t):
        return "ordonnance"
    if "ordonnance" in t:
        return "ordonnance"

    return None


# =========================
# Required fields + doc scoring
# =========================

REQUIRED_BY_DOC: Dict[str, List[str]] = {
    "facture": ["facture_no", "patient_name", "total", "medicines"],
    # NOTE: fees_amount reste requis sur le papier, mais si OCR CNSS est faible, on flag MISSING sans forcer mismatch
    "feuille_cnss": ["beneficiary_name", "cin", "fees_amount"],
    "ordonnance": ["doctor_name", "patient_name", "medicines"],
}

WEIGHTS: Dict[str, int] = {
    "facture_no": 15,
    "patient_name": 25,
    "total": 25,
    "medicines": 35,

    "beneficiary_name": 35,
    "cin": 35,
    "fees_amount": 30,

    "doctor_name": 35,
}


def _has_value(fields: Dict[str, Any], k: str, doc_type: str) -> bool:
    if k == "medicines":
        meds = fields.get("medicines") or []
        return isinstance(meds, list) and len([m for m in meds if str(m).strip()]) > 0

    v = fields.get(k)

    # CIN: validation stricte
    if doc_type == "feuille_cnss" and k == "cin":
        return cin_valid(v)

    # beneficiary_name: si garbage => considéré manquant
    if doc_type == "feuille_cnss" and k == "beneficiary_name":
        return cnss_name_quality(v) >= 0.6

    return v is not None and str(v).strip() != ""


def score_required_fields(doc_type: str, fields: Dict[str, Any]) -> Tuple[int, List[str]]:
    needed = REQUIRED_BY_DOC.get(doc_type, [])
    if not needed:
        return 0, ["doc_type_unknown"]

    got = 0
    missing: List[str] = []
    max_score = sum(WEIGHTS.get(k, 10) for k in needed) or 1

    for k in needed:
        if _has_value(fields, k, doc_type):
            got += WEIGHTS.get(k, 10)
        else:
            missing.append(k)

    score = int(round((got / max_score) * 100))
    return score, missing


# =========================
# Cross-check => anomalies
# =========================

def cross_check_to_anomalies(
    facture: Optional[Dict[str, Any]],
    feuille_cnss: Optional[Dict[str, Any]],
    ordonnance: Optional[Dict[str, Any]],
) -> Tuple[List[str], Dict[str, Any]]:

    anomalies: List[str] = []
    metrics: Dict[str, Any] = {}

    f = (facture or {}).get("fields") or {}
    c = (feuille_cnss or {}).get("fields") or {}
    o = (ordonnance or {}).get("fields") or {}

    # ---- Facture <-> CNSS ----
    if facture and feuille_cnss:
        q = cnss_name_quality(c.get("beneficiary_name"))
        metrics["cnss_name_quality"] = round(float(q), 3)

        if q < 0.6:
            anomalies.append("CNSS_NAME_WEAK")  # on ne fait pas mismatch nom
        else:
            sim = name_similarity(str(f.get("patient_name") or ""), str(c.get("beneficiary_name") or ""))
            metrics["facture_vs_cnss_name_sim"] = round(sim, 3)
            if sim < 0.70:
                anomalies.append("MISMATCH_NAME_FACTURE_CNSS")

        ok_amt = money_close(f.get("total"), c.get("fees_amount"), rel_tol=0.02)
        metrics["facture_vs_cnss_amount_match"] = None if ok_amt is None else bool(ok_amt)
        if ok_amt is None:
            anomalies.append("CNSS_FEES_MISSING")  # pas de mismatch dur
        elif not ok_amt:
            anomalies.append("MISMATCH_AMOUNT_FACTURE_CNSS")

    # ---- Facture <-> Ordonnance ----
    if facture and ordonnance:
        sim = name_similarity(str(f.get("patient_name") or ""), str(o.get("patient_name") or ""))
        metrics["facture_vs_ord_patient_sim"] = round(sim, 3)
        if sim < 0.70:
            anomalies.append("MISMATCH_NAME_FACTURE_ORD")

        m_sim = best_med_match(f.get("medicines") or [], o.get("medicines") or [])
        metrics["facture_vs_ord_med_sim"] = round(m_sim, 3)
        if m_sim < 0.75:
            anomalies.append("MISMATCH_MED_FACTURE_ORD")

    # ---- CNSS <-> Ordonnance ----
    if feuille_cnss and ordonnance:
        q = cnss_name_quality(c.get("beneficiary_name"))
        if q < 0.6:
            anomalies.append("CNSS_NAME_WEAK_SKIP_CNSS_ORD")
        else:
            sim = name_similarity(str(c.get("beneficiary_name") or ""), str(o.get("patient_name") or ""))
            metrics["cnss_vs_ord_name_sim"] = round(sim, 3)
            if sim < 0.70:
                anomalies.append("MISMATCH_NAME_CNSS_ORD")

    return anomalies, metrics


# =========================
# Main entrypoint
# =========================

def validate_case(extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
    # doc_type fallback
    for d in extractions:
        if not d.get("doc_type"):
            d["doc_type"] = detect_doc_type(d.get("cleaned_text", ""))

    # pick docs
    facture = next((d for d in extractions if d.get("doc_type") == "facture"), None)
    cnss = next((d for d in extractions if d.get("doc_type") == "feuille_cnss"), None)
    ordonnance = next((d for d in extractions if d.get("doc_type") == "ordonnance"), None)

    # per-doc scores + required anomalies
    documents: List[Dict[str, Any]] = []
    doc_scores: List[int] = []
    anomalies: List[str] = []

    for d in extractions:
        dt = d.get("doc_type") or "unknown"
        fields = d.get("fields") or {}
        s, missing = score_required_fields(dt, fields)

        documents.append({
            "doc_type": dt,
            "score_required": s,   # 0..100
            "missing": missing,
            "fields": fields,
        })

        if dt in REQUIRED_BY_DOC:
            doc_scores.append(s)
            for m in missing:
                anomalies.append(f"MISSING_{dt.upper()}_{m.upper()}")

    # cross-check anomalies
    cross_anoms, metrics = cross_check_to_anomalies(facture, cnss, ordonnance)
    anomalies.extend(cross_anoms)

    return {
        "documents": documents,
        "doc_scores": doc_scores,      # List[int] 0..100
        "anomalies": sorted(list(set(anomalies))),
        "metrics": metrics,
        "has_all_docs": bool(facture and cnss and ordonnance),
    }