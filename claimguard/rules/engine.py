"""Moteur de règles + cross-check robuste (tolère OCR faible CNSS)."""

from __future__ import annotations
import difflib
import re
from typing import Dict, List, Optional


# ===== Required fields par type (selon ton cahier) =====
REQUIRED_BY_DOC = {
    "facture": ["facture_no", "patient_name", "total", "medicines"],
    "ordonnance": ["doctor_name", "patient_name", "medicines"],
    "feuille_cnss": ["beneficiary_name", "cin"],  # fees_amount peut être illisible => non bloquant strict
}

# mots à ignorer dans noms
STOP_WORDS = {
    "de", "du", "des", "la", "le", "les", "et", "a", "à", "d", "l",
    "mr", "mme", "madame", "monsieur", "dr", "docteur",
    "beneficiaire", "soins", "nom", "prenom", "prénom",
}

def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def _norm_name(s: Optional[str]) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-zà-ÿ'\- ]", " ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    toks = [t for t in s.split() if t and t not in STOP_WORDS and len(t) >= 2]
    return " ".join(toks)


def _name_quality(s: Optional[str]) -> float:
    """
    Score simple 0..1:
    - doit avoir >= 2 tokens alpha
    - doit avoir assez de lettres
    - pénalise pattern "E ID..." etc
    """
    raw = (s or "").strip()
    n = _norm_name(raw)
    toks = n.split()
    if len(toks) < 2:
        return 0.0
    letters = sum(ch.isalpha() for ch in n)
    if letters < 8:
        return 0.2
    # pénalise si ça ressemble à bruit OCR "e idci si ..."
    if raw.lower().startswith(("e id", "e...id", "e idci", "e idossi")):
        return 0.25
    lettres_isolees = sum(1 for t in toks if len(t) == 1)
    if lettres_isolees >= 2:
        return 0.3
    return 0.9


def _med_overlap(m1: List[str], m2: List[str]) -> float:
    a = {_norm_name(x) for x in (m1 or []) if _norm_name(x)}
    b = {_norm_name(x) for x in (m2 or []) if _norm_name(x)}
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / max(1, union)


def apply_rules(doc_type: str, fields: Dict) -> List[str]:
    anomalies: List[str] = []
    req = REQUIRED_BY_DOC.get(doc_type, [])

    if doc_type in ["ordonnance", "feuille_cnss"]:
        specialite = fields.get("doctor_specialty")
        inpe = fields.get("doctor_inpe")
        
        if not specialite and not inpe:
            anomalies.append(f"{doc_type}: Cachet du médecin introuvable (Spécialité et INPE manquants)")
        
        # 2. Si on a la spécialité mais pas d'INPE du tout
        elif not inpe:
            # On ne met l'anomalie que si c'est VRAIMENT vide. 
            # Si Gemini a mis "PRESENT", cette condition ne sera pas remplie.
            anomalies.append(f"{doc_type}: Attention, numéro INPE introuvable dans le cachet")

    for f in req:
        val = fields.get(f)
        if f == "medicines":
            if not val or not isinstance(val, list) or len(val) == 0:
                anomalies.append(f"{doc_type}: medicines manquant")
        else:
            if not val or (isinstance(val, str) and not val.strip()):
                anomalies.append(f"{doc_type}: {f} manquant")

    # CNSS: fees non bloquant
    if doc_type == "feuille_cnss":
        if not fields.get("fees_amount"):
            anomalies.append("feuille_cnss: fees_amount manquant (OCR faible possible)")

        # beneficiary faible -> warning
        if _name_quality(fields.get("beneficiary_name")) < 0.6:
            anomalies.append("feuille_cnss: beneficiary_name faible/garbage (OCR faible)")

    return anomalies


def cross_check(ord_fields: Dict, fac_fields: Dict, feu_fields: Dict) -> List[str]:
    anomalies: List[str] = []

    # ==========================================
    # 1. PATIENT NAME cross-check
    # ==========================================
    ord_p = _norm_name(ord_fields.get("patient_name"))
    fac_p = _norm_name(fac_fields.get("patient_name"))
    feu_b = _norm_name(feu_fields.get("beneficiary_name"))

    # ref = facture si dispo sinon ordonnance
    ref = fac_p or ord_p

    # facture vs ordonnance (doit matcher à 80%)
    if fac_p and ord_p and _similar(fac_p, ord_p) < 0.80:
        anomalies.append(f"MISMATCH_PATIENT_FACTURE_ORDONNANCE: '{fac_fields.get('patient_name')}' != '{ord_fields.get('patient_name')}'")

    # CNSS beneficiary: seulement si qualité OCR OK
    feu_q = _name_quality(feu_fields.get("beneficiary_name"))
    if ref and feu_b:
        if feu_q >= 0.6:
            if _similar(ref, feu_b) < 0.75:
                anomalies.append(f"MISMATCH_PATIENT_CNSS: '{ref}' != '{feu_fields.get('beneficiary_name')}'")
        else:
            anomalies.append("CNSS_BENEFICIARY_WEAK: skip patient cross-check (OCR faible)")

    # ==========================================
    # 2. AMOUNT cross-check
    # ==========================================
    fac_total = fac_fields.get("total")
    feu_fees = feu_fields.get("fees_amount")

    if fac_total is not None and feu_fees is not None:
        try:
            # Tolérance de 0.5 Dirhams
            if abs(float(fac_total) - float(feu_fees)) > 0.5:
                anomalies.append(f"MISMATCH_AMOUNT_FACTURE_CNSS: {fac_total} != {feu_fees}")
        except:
            anomalies.append("INVALID_AMOUNT_FORMAT")

    else:
        # pas de montant CNSS => pas de mismatch, juste warning
        if feu_fees is None:
            anomalies.append("CNSS_FEES_MISSING: skip amount cross-check (OCR faible)")

    # ==========================================
    # 3. MEDICINES cross-check 
    # ==========================================
    overlap = _med_overlap(fac_fields.get("medicines") or [], ord_fields.get("medicines") or [])
    if overlap == 0.0 and (fac_fields.get("medicines") and ord_fields.get("medicines")):
        anomalies.append(f"MISMATCH_MEDICINES_FACTURE_ORDONNANCE: {fac_fields.get('medicines')} vs {ord_fields.get('medicines')}")

    # ==========================================
    # 4. DOCTOR / CACHET cross-check (Nouveau !)
    # ==========================================
    ord_inpe = ord_fields.get("doctor_inpe")
    feu_inpe = feu_fields.get("doctor_inpe")
    
    # Vérification stricte de l'INPE s'il est trouvé sur les deux
    if ord_inpe and feu_inpe:
        if ord_inpe != feu_inpe:
            anomalies.append(f"MISMATCH_DOCTOR_INPE: Ordonnance ({ord_inpe}) != CNSS ({feu_inpe})")
            
    # Sinon, vérification souple du nom du médecin
    else:
        ord_doc = _norm_name(ord_fields.get("doctor_name"))
        feu_doc = _norm_name(feu_fields.get("doctor_name"))
        
        if ord_doc and feu_doc:
            if _similar(ord_doc, feu_doc) < 0.70:
                anomalies.append(f"MISMATCH_DOCTOR_NAME: '{ord_fields.get('doctor_name')}' != '{feu_fields.get('doctor_name')}'")

    return anomalies
def evaluate_dossier(doc_anomalies: Dict[str, List[str]], cross_anomalies: List[str]) -> Dict[str, Any]:
    all_anomalies = []
    for anomalies in doc_anomalies.values():
        all_anomalies.extend(anomalies)
    all_anomalies.extend(cross_anomalies)

    if not all_anomalies:
        return {
            "decision": "approuvé",
            "score": 1.0,
            "reason": "Dossier parfaitement valide."
        }

    mots_cles_avertissement = ["faible", "weak", "missing", "attention", "skip"]
    erreurs_critiques = []
    avertissements = []

    for anomalie in all_anomalies:
        if any(mot in anomalie.lower() for mot in mots_cles_avertissement):
            avertissements.append(anomalie)
        else:
            erreurs_critiques.append(anomalie)

    if erreurs_critiques:
        return {
            "decision": "rejeté",
            "score": 0.0,
            "reason": f"Rejet automatique : {len(erreurs_critiques)} erreur(s) critique(s)."
        }

    score = 1.0 - (len(avertissements) * 0.15)
    
    if score >= 0.70:
        return {
            "decision": "approuvé",
            "score": round(score, 2),
            "reason": "Dossier approuvé avec données partielles."
        }
    else:
        return {
            "decision": "rejeté",
            "score": round(max(0.0, score), 2),
            "reason": "Rejet automatique : Qualité globale insuffisante."
        }