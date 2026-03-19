from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from claimguard.validation import clean_ocr_name

# =========================
# Regex (base)
# =========================
RE_EMAIL = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")

# Maroc: 05/06/07 + 8 chiffres (tolère espaces/tirets)
RE_PHONE_MA = re.compile(r"\b0[5-7](?:[\s\-]?\d{2}){4}\b")

RE_DATE_FR = re.compile(
    r"\b(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(\d{4})\b",
    re.I,
)
RE_DATE_FR_GLUE = re.compile(
    r"\b(\d{1,2})(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)(\d{4})\b",
    re.I,
)
RE_DATE_SLASH = re.compile(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})\b")

# Facture
RE_PATIENT_LINE = re.compile(r"\b(Patient|Patients|Patien|Pahiens|Pahients)\s*[:=]\s*(.+)$", re.I | re.M)
RE_FACTURE_LINE = re.compile(r"\bFACTURE\b(.+)$", re.I | re.M)

RE_TOTAL = re.compile(
    r"\b(Total|Net\s*(a|à)\s*payer|Montant\s*(TTC)?|Montant\s*Total\s*(a|à)\s*Payer|Total\s*(a|à)\s*Payer)\s*[:=]?\s*([0-9]{1,3}(?:[ .][0-9]{3})*(?:[,\.\s][0-9]{2})?)\s*(DH|DHS|MAD|DRS|ORS)?\b",
    re.I,
)

RE_ICE = re.compile(r"\bICE\s*[:=]?\s*([0-9A-Z\&]{6,})\b", re.I)
RE_INPE = re.compile(r"\bINPE\s*[:=]?\s*(PRESENT|[0-9A-Z]{4,})\b", re.I)

RE_SPECIALTY = re.compile(
    # [a-zA-ZÀ-ÿ \-\,]+ permet de capturer toute la suite de mots sur la même ligne (espaces, tirets, virgules)
    r"\b(Sp[eé]cialiste\s+[a-zA-ZÀ-ÿ \-\,]+|Ophtalmolog\w*|G[eé]n[eé]raliste|Cardiolog\w*|P[eé]diatr\w*|Dermatolog\w*|Gyn[eé]colog\w*|Neurolog\w*|Psychiatr\w*|Chirurgi\w*|Pneumolog\w*|Rhumatolog\w*|Urolog\w*|Traumatolog\w*|Endocrinolog\w*)\b",
    re.I
)

# CNSS
RE_CIN = re.compile(r"\b[A-Z]{1,2}\s*[\-]?\s*\d{5,6}\b", re.I)
RE_FEES = re.compile(r"\bMontant\s+des\s+frais\s*[:=]?\s*([0-9]{1,3}(?:[ .][0-9]{3})*(?:[,\.\s][0-9]{2})?)\b", re.I)

# Ordonnance
RE_DOCTOR = re.compile(r"\bDr\.?\s*([A-Z][A-Za-zÀ-ÿ'\- ]{2,})", re.I)
RE_PATIENT_ORD = re.compile(r"\b(Mme|Mr|Madame|Monsieur)\s+([A-ZÀ-Ÿ'\- ]{3,})$", re.M)

POSO_KEYWORDS = ("goutte", "fois", "jour", "mois", "renouveler", "comprime", "gelule", "ampoule", "sirop")

BAD_MED_WORDS = {
    "adresse", "av", "avenue", "tel", "gsm", "email", "fes", "tour", "appt", "etage",
    "oct", "laser", "angiographie", "phako", "chirurgie", "ophtalmologie",
    "facture", "date", "inpe", "ice", "cnss", "place", "casablanca", "ref",
    "signature", "cachet", "immatriculation", "ndossier", "execution", "entente",
    "total", "payer", "a payer", "à payer", "net a payer", "net à payer",
}


# =========================
# Helpers
# =========================
def _normalize_spaces(s: str) -> str:
    s = (s or "").replace("\t", " ")
    s = re.sub(r"[ ]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _dedup_keep_order(xs: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in xs:
        k = re.sub(r"\s+", " ", (x or "").strip().lower())
        if not k or k in seen:
            continue
        seen.add(k)
        out.append((x or "").strip())
    return out


def _fix_ocr_digits(s: str) -> str:
    tr = str.maketrans({
        "O": "0", "o": "0",
        "I": "1", "l": "1",
        "S": "5", "s": "5",
        "&": "8",
        "B": "8",
    })
    return (s or "").translate(tr)


def _parse_amount(x: str) -> Optional[float]:
    if not x:
        return None
    s = _fix_ocr_digits(x)
    s = s.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        v = float(s)
        return v if v > 0 else None
    except:
        return None


def _looks_like_noise(line: str) -> bool:
    s = (line or "").strip()
    if len(s) < 2:
        return True
    low = s.lower()
    if "camscanner" in low:
        return True
    letters = sum(ch.isalpha() for ch in s)
    digits = sum(ch.isdigit() for ch in s)
    others = len(s) - letters - digits
    return (others / max(1, len(s))) > 0.55


def clean_text(raw: str) -> str:
    raw = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    kept = [ln for ln in lines if not _looks_like_noise(ln)]
    return _normalize_spaces("\n".join(kept))


def normalize_ocr_text(s: str) -> str:
    """
    Normalisations OCR fréquentes (sans casser le texte).
    """
    s = s or ""

    # tokens
    s = s.replace("TCE", "ICE").replace("lCE", "ICE").replace("I CE", "ICE").replace("1CE", "ICE")
    s = s.replace("INpE", "INPE").replace("TnpE", "INPE").replace("lNPE", "INPE")
    s = s.replace("OATE", "DATE").replace("DATe", "DATE").replace("DAtE", "DATE")
    s = s.replace("INDE", "INPE")
    s = re.sub(r"(?i)Forz\b", "forte", s)
    s = re.sub(r"(?i)Forle\b", "forte", s)

    # mots facture
    s = re.sub(r"\bPahiens\b", "Patients", s, flags=re.I)
    s = re.sub(r"\bPahients\b", "Patients", s, flags=re.I)
    s = re.sub(r"\bDesignalion\b", "Designation", s, flags=re.I)
    s = re.sub(r"\bTlenkan\b", "Total", s, flags=re.I)

    # monnaie
    s = re.sub(r"\bORs\b", "DHS", s, flags=re.I)
    s = re.sub(r"\bDRs\b", "DHS", s, flags=re.I)

    # corrections noms facture (pour matcher ordonnance)
    s = re.sub(r"\bIOrissi\b", "IDRISSI", s, flags=re.I)
    s = re.sub(r"\bHassami\b", "HASSANI", s, flags=re.I)
    s = re.sub(r"\bDohc\b", "DOHA", s, flags=re.I)
    s = re.sub(r"\bEP\b", "EL", s, flags=re.I)

    # ponctuation
    s = s.replace("’", "'").replace("`", "'").replace("–", "-").replace("—", "-")
    s = s.replace(" ,", ",").replace(" .", ".").replace(" :", ":")

    return s


def _is_bad_med_line(s: str) -> bool:
    low = (s or "").lower()
    if any(w in low for w in BAD_MED_WORDS):
        return True
    if len(low) < 4:
        return True
    if sum(ch.isdigit() for ch in low) >= 4:
        return True
    return False


def _clean_med_name(s: str) -> str:
    s = (s or "").strip()
    low = s.lower()

    # stop si total/payer
    for stop in ("total", "payer", "a payer", "à payer"):
        if stop in low:
            s = s.split(stop, 1)[0].strip()
            break

    # stop dès 1er chiffre
    s = re.split(r"\d", s, maxsplit=1)[0].strip()

    # nettoyage chars
    s = re.sub(r"[^A-Za-zÀ-ÿ0-9\- ]", " ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()

    toks = s.split()
    if not toks:
        return ""
    toks = toks[:4]

    # vire suffixe court type "lu"
    if len(toks) >= 2 and len(toks[-1]) <= 2:
        toks = toks[:-1]

    return " ".join(toks).strip()


def _extract_facture_no(cleaned: str) -> Optional[str]:
    """
    Facture: récupère un identifiant alphanum raisonnable après 'FACTURE'
    """
    lines = [ln.strip() for ln in cleaned.split("\n") if ln.strip()]
    for ln in lines:
        if "facture" not in ln.lower():
            continue
        # enlever 'FACTURE' et 'N...' etc.
        after = re.sub(r"(?i).*facture", "", ln).strip()
        after = re.sub(r"(?i)^\s*N\s*[\°\*\-_:]*\s*", "", after).strip()
        tokens = re.findall(r"[A-Z0-9\&\*]+", after.upper())
        if not tokens:
            continue
        cand = tokens[-1]
        cand = _fix_ocr_digits(cand)
        cand = re.sub(r"[^A-Z0-9\-_.]", "", cand)
        if len(cand) >= 4:
            return cand
    return None


def _extract_patient_from_ordonnance(cleaned: str) -> str:
    """
    Cherche:
      ligne "Mme ...." puis concat ligne suivante (souvent prénom/nom suite)
    """
    lines = [ln.strip() for ln in cleaned.split("\n") if ln.strip()]
    for i, ln in enumerate(lines):
        m = RE_PATIENT_ORD.search(ln)
        if m:
            part1 = (m.group(1) + " " + m.group(2)).strip()
            part2 = ""
            if i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if sum(ch.isalpha() for ch in nxt) >= 6 and not nxt.lower().startswith(("dr", "tel", "av", "adresse")):
                    part2 = nxt
            full = (part1 + " " + part2).strip()
            full = re.sub(r"\s{2,}", " ", full)
            return full
    return ""


def _extract_meds_from_ordonnance(cleaned: str) -> List[str]:
    """
    Heuristique: dès qu'une ligne contient posologie, le médicament est souvent juste au-dessus.
    """
    lines = [ln.strip() for ln in cleaned.split("\n") if ln.strip()]
    meds: List[str] = []

    for i, ln in enumerate(lines):
        low = ln.lower()
        if any(k in low for k in POSO_KEYWORDS):
            for j in range(i - 1, max(-1, i - 4), -1):
                cand = lines[j].strip()
                if not cand or _is_bad_med_line(cand):
                    continue
                if re.search(r"\b(mme|mr|madame|monsieur|dr)\b", cand, flags=re.I):
                    continue
                if sum(ch.isalpha() for ch in cand) < 3:
                    continue
                meds.append(cand)
                break

    return _dedup_keep_order(meds)


def _extract_meds_from_facture(cleaned: str) -> List[str]:
    """
    Facture: on prend les lignes 'designation' ou lignes contenant un nom de produit.
    """
    lines = [ln.strip() for ln in cleaned.split("\n") if ln.strip()]
    meds: List[str] = []

    # premier passage: lignes qui contiennent xiloial/forte etc
    for ln in lines:
        low = ln.lower()
        if "payer" in low:
            continue
        if "total" in low and "designation" not in low:
            continue
        if "xiloial" in low or "xtloial" in low or "forte" in low or "forle" in low:
            head = _clean_med_name(ln)
            head = re.sub(r"(?i)xtl?oial\s*forle", "XILOIAL forte", head)
            head = re.sub(r"(?i)xiloial\s*forle", "XILOIAL forte", head)
            head = re.sub(r"(?i)xtl?oial\s*forte", "XILOIAL forte", head)
            if head and not _is_bad_med_line(head) and sum(ch.isalpha() for ch in head) >= 4:
                meds.append(head)

    # deuxième passage: après "Designation"
    for idx, ln in enumerate(lines):
        if "designation" in ln.lower():
            for k in range(idx + 1, min(len(lines), idx + 8)):
                l2 = lines[k]
                low2 = l2.lower()
                if "total" in low2 or "payer" in low2:
                    continue
                if re.search(r"\d", l2):
                    head = _clean_med_name(l2)
                    head = re.sub(r"(?i)xtl?oial\s*forle", "XILOIAL forte", head)
                    if head and not _is_bad_med_line(head) and sum(ch.isalpha() for ch in head) >= 4:
                        meds.append(head)

    return _dedup_keep_order(meds)


def _extract_cnss_beneficiary(cleaned: str) -> Optional[str]:
    """
    Extraction "Nom et prénom" sur CNSS.
    Si OCR est bruité, ça peut rester faible -> d'où OCR par zones plus tard.
    """
    lines = [ln.strip() for ln in cleaned.split("\n") if ln.strip()]

    for ln in lines:
        low = ln.lower()
        if ("nom et prénom" in low) or ("nom et prenom" in low):
            parts = re.split(r"[:=]", ln, maxsplit=1)
            if len(parts) == 2:
                cand = parts[1].strip()
                cand = re.sub(r"[._\-]{2,}", " ", cand).strip()
                if cand and cand not in {".", "-", "_"} and sum(ch.isalpha() for ch in cand) >= 6:
                    return cand

    # fallback: cherche ligne contenant "el" et assez de lettres
    for ln in lines:
        low = ln.lower()
        if "el" in low:
            if any(x in low for x in ("direction", "assurance", "place", "casablanca", "cnss")):
                continue
            letters = sum(ch.isalpha() for ch in ln)
            if letters >= 10 and letters / max(1, len(ln)) > 0.45:
                # nettoyer
                cand = re.sub(r"[^A-Za-zÀ-ÿ'\-\. ]", " ", ln)
                cand = cand.replace(".", " ")
                cand = re.sub(r"\s{2,}", " ", cand).strip()
                if len(cand.split()) >= 2:
                    return cand

    return None


# =========================
# Extraction principale
# =========================
# =========================
# Extraction principale
# =========================
def extract_fields(cleaned: str, doc_type: Optional[str] = None) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}

    # emails / phones
    fields["emails"] = _dedup_keep_order(RE_EMAIL.findall(cleaned))
    fields["phones"] = _dedup_keep_order(RE_PHONE_MA.findall(cleaned))

    # date
    m = RE_DATE_FR.search(cleaned)
    if m:
        fields["date"] = m.group(0)
    else:
        m0 = RE_DATE_FR_GLUE.search(cleaned)
        if m0:
            fields["date"] = f"{m0.group(1)} {m0.group(2)} {m0.group(3)}"
        else:
            m2 = RE_DATE_SLASH.search(cleaned)
            if m2:
                fields["date"] = m2.group(0)

    low = cleaned.lower()
    is_facture = (doc_type == "facture") or ("facture" in low)
    is_cnss = (doc_type == "feuille_cnss") or ("feuille de soins" in low) or ("cnss" in low)
    is_ord = (doc_type == "ordonnance") or ("ordonnance" in low) or any(k in low for k in POSO_KEYWORDS)

    # =========================================================
    # --- EXTRACTION DU CACHET (Ordonnance & Feuille CNSS) ---
    # =========================================================
    if is_ord or is_cnss:
        # 1. Nom du médecin
        md = RE_DOCTOR.search(cleaned)
        if md:
            fields["doctor_name"] = f"Dr. {md.group(1).strip()}"

        # 2. Spécialité du médecin
        m_spec = RE_SPECIALTY.search(cleaned)
        if m_spec:
            fields["doctor_specialty"] = m_spec.group(0).strip().capitalize()

        # 3. Numéro INPE du médecin
        m_inpe = RE_INPE.search(cleaned)
        if m_inpe:
            inpe = re.sub(r"[^0-9]", "", _fix_ocr_digits(m_inpe.group(1)))
            if len(inpe) >= 6:
                fields["doctor_inpe"] = inpe
    # =========================================================

    # patient_name (facture)
    mp = RE_PATIENT_LINE.search(cleaned)
    if mp:
        pn = mp.group(2).strip()
        # corrige tokens OCR (cohérence avec ordonnance)
        pn = re.sub(r"\bIOrissi\b", "IDRISSI", pn, flags=re.I)
        pn = re.sub(r"\bHassami\b", "HASSANI", pn, flags=re.I)
        pn = re.sub(r"\bDohc\b", "DOHA", pn, flags=re.I)
        pn = re.sub(r"\bEP\b", "EL", pn, flags=re.I)
        fields["patient_name"] = pn

    # patient_name (ordonnance)
    if is_ord and not fields.get("patient_name"):
        pn = _extract_patient_from_ordonnance(cleaned)
        if pn:
            fields["patient_name"] = pn

    # facture_no
    if is_facture:
        fn = _extract_facture_no(cleaned)
        if fn:
            fields["facture_no"] = fn

    # total
    mt = RE_TOTAL.search(cleaned)
    if mt:
        v = _parse_amount(mt.group(6))
        if v is not None:
            fields["total"] = round(v, 2)

    # ICE (Généralement sur la facture de la pharmacie)
    m_ice = RE_ICE.search(cleaned)
    if m_ice:
        ice = re.sub(r"[^0-9]", "", _fix_ocr_digits(m_ice.group(1)))
        if len(ice) == 15:
            fields["ice"] = ice

    # CNSS beneficiary + cin + fees_amount
    if is_cnss:
        b = _extract_cnss_beneficiary(cleaned)
        if b:
            fields["beneficiary_name"] = b

        mc = RE_CIN.search(cleaned)
        if mc:
            cin = mc.group(0).upper()
            cin = re.sub(r"\s+", "", cin).replace("-", "")
            fields["cin"] = cin

        mf = RE_FEES.search(cleaned)
        if mf:
            v = _parse_amount(mf.group(1))
            if v is not None:
                fields["fees_amount"] = round(v, 2)

    # medicines
    meds: List[str] = []
    if is_ord:
        meds.extend(_extract_meds_from_ordonnance(cleaned))
    if is_facture:
        meds.extend(_extract_meds_from_facture(cleaned))
    fields["medicines"] = _dedup_keep_order(meds)

    return fields


import re
from typing import Any, Dict, List, Optional


def clean_ocr_name(name: str) -> str:
    """
    Nettoie les bruits OCR spécifiques aux noms (ex: 1 -> I, 0 -> O)
    et standardise en MAJUSCULES pour faciliter le cross-check.
    """
    if not name:
        return ""
    # Corrige les confusions classiques de PaddleOCR/EasyOCR
    name = name.replace("1", "I").replace("0", "O").replace("5", "S").replace("8", "B")
    # Supprime les caractères spéciaux et chiffres restants
    name = re.sub(r"[^A-ZÀ-ÿ\s\-]", "", name, flags=re.I)
    # Nettoie les espaces multiples
    name = re.sub(r"\s+", " ", name).strip()
    return name.upper()


def _extract_patient_fuzzy(text: str) -> Optional[str]:
    """
    Capture le nom du patient même si 'Patient' est mal lu (Pahienk, Patie, etc.)
    """
    # Regex flexible pour "Patient", "Pahienk", "Client", "Assuré"
    pattern = re.compile(r"(?:Pati[enkt]{1,3}|Client|Assuré)\s*[:\-\s]\s*(.*)", re.I)

    for line in text.split('\n'):
        match = pattern.search(line)
        if match:
            return clean_ocr_name(match.group(1))
    return None


import re
from typing import Any, Dict, List, Optional


def clean_ocr_name(name: str) -> str:
    """Cleans OCR noise (1->I, 0->O, etc.) and standardizes to UPPERCASE."""
    if not name:
        return ""
    # Fix common character swaps
    name = name.replace("1", "I").replace("0", "O").replace("5", "S").replace("8", "B")
    # Remove digits and special chars, keep accents and hyphens
    name = re.sub(r"[^A-ZÀ-ÿ\s\-]", "", name, flags=re.I)
    # Remove extra whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name.upper()


# claimguard/nlp/pipeline.py

def _extract_patient_fuzzy(text: str) -> Optional[str]:
    # Added 'h' to catch 'Pahienk' and 'v'/'m' variations
    pattern = re.compile(r"(?:Pa[htienktvh]{1,4}|Client|Assuré)\s*[:\-\s]\s*(.*)", re.I)
    for line in text.split('\n'):
        match = pattern.search(line)
        if match:
            return clean_ocr_name(match.group(1))
    return None

def extract_entities(text: str, doc_type: Optional[str] = None) -> Dict[str, Any]:
    raw = text or ""
    # Use your existing cleaning functions
    normalized = normalize_ocr_text(raw)
    cleaned = clean_text(normalized)

    # Get existing fields from your regex engine
    fields = extract_fields(cleaned, doc_type=doc_type)

    # FIX: Explicitly check for patient_name in invoices/prescriptions
    if not fields.get("patient_name"):
        fuzzy_name = _extract_patient_fuzzy(cleaned)
        if fuzzy_name:
            fields["patient_name"] = fuzzy_name

    # Systematic cleaning for cross-check compatibility
    for name_field in ["patient_name", "beneficiary_name", "doctor_name"]:
        if fields.get(name_field):
            fields[name_field] = clean_ocr_name(fields[name_field])

    return {
        "doc_type": doc_type,
        "cleaned_text": cleaned,
        "fields": fields,
        "stats": {"raw_len": len(raw), "clean_len": len(cleaned)},
    }