from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# CIN marocain souvent: 1-2 lettres + 5-6 chiffres
RE_CIN = re.compile(r"\b([A-Z]{1,2}\s*[\-]?\s*\d{5,6})\b", re.I)

# Montant (tolère "2112" mauvais => on filtrera)
RE_MONEY = re.compile(r"\b(\d{1,3}(?:[ .]\d{3})*(?:[,\.\s]\d{2})?)\b")

def _norm_spaces(s: str) -> str:
    s = (s or "").replace("\n", " ")
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

def _only_letters_spaces(s: str) -> str:
    s = re.sub(r"[^A-Za-zÀ-ÿ'\- ]", " ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

def _to_gray_and_clean(img: np.ndarray) -> np.ndarray:
    # img BGR ou RGB -> gray
    if img.ndim == 3:
        # assume BGR from cv2 (most likely)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # léger denoise + threshold adaptatif (CNSS a beaucoup de traits)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    th = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 7
    )
    return th

def _crop_rel(img: np.ndarray, box: Tuple[float, float, float, float]) -> np.ndarray:
    """
    box = (x1,y1,x2,y2) en ratios 0..1
    """
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    xa = max(0, int(x1 * w)); ya = max(0, int(y1 * h))
    xb = min(w, int(x2 * w)); yb = min(h, int(y2 * h))
    if xb <= xa or yb <= ya:
        return img
    return img[ya:yb, xa:xb].copy()

def _ocr_lines(ocr, img: np.ndarray) -> List[str]:
    """
    ocr = PaddleOCR instance
    retourne une liste de lignes reconnues (text only)
    """
    # PaddleOCR attend RGB souvent, mais il accepte aussi ndarray
    # On convertit en RGB propre:
    if img.ndim == 3:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    else:
        rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    res = ocr.ocr(rgb, cls=True) or []
    out: List[str] = []
    for block in res:
        if not block:
            continue
        for item in block:
            try:
                text = item[1][0]
            except Exception:
                continue
            text = _norm_spaces(text)
            if text:
                out.append(text)
    return out

def _best_name_candidate(lines: List[str]) -> Optional[str]:
    # on garde lignes qui ressemblent à un nom (lettres majoritaires)
    cands: List[str] = []
    for ln in lines:
        if len(ln) < 4:
            continue
        # enlever les tirets de cases
        if re.fullmatch(r"[_\-\s]+", ln):
            continue
        letters = sum(ch.isalpha() for ch in ln)
        if letters < 6:
            continue
        if letters / max(1, len(ln)) < 0.50:
            continue
        c = _only_letters_spaces(ln)
        # doit contenir au moins 2 mots
        if len(c.split()) >= 2:
            cands.append(c)

    if not cands:
        return None

    # choisir le plus "long" (souvent nom complet)
    cands.sort(key=lambda s: (len(s), len(s.split())), reverse=True)
    return cands[0]

def _extract_cin(lines: List[str]) -> Optional[str]:
    txt = " ".join(lines)
    m = RE_CIN.search(txt)
    if not m:
        return None
    cin = m.group(1).upper()
    cin = re.sub(r"\s+", "", cin)
    cin = cin.replace("-", "")
    return cin

def _extract_fees_amount(lines: List[str]) -> Optional[float]:
    """
    CNSS a parfois "2112" (nombre de pièces jointes) qui pollue.
    On cherche un montant plausible:
    - préfère valeurs avec virgule/point (centimes)
    - sinon plus grand nombre raisonnable
    """
    # extraire tous les nombres
    nums: List[str] = []
    for ln in lines:
        for m in RE_MONEY.finditer(ln):
            nums.append(m.group(1))

    if not nums:
        return None

    def to_float(s: str) -> Optional[float]:
        s2 = s.replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return float(s2)
        except:
            return None

    vals: List[float] = []
    with_cents: List[float] = []

    for s in nums:
        v = to_float(s)
        if v is None:
            continue
        # ignore tout petit bruit
        if v <= 0:
            continue
        # filtre anti "2112" (souvent pièces jointes). On l'écarte si aucun centimes.
        if int(v) == 2112 and ("," not in s and "." not in s):
            continue
        vals.append(v)
        if ("," in s) or (re.search(r"\.\d{2}\b", s) is not None):
            with_cents.append(v)

    if with_cents:
        # prend le plus grand avec centimes
        return float(sorted(with_cents)[-1])

    if not vals:
        return None

    # prend le plus grand plausible
    vals.sort()
    return float(vals[-1])

def extract_cnss_fields_from_image(ocr, image_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Retourne dict: beneficiary_name, cin, fees_amount (si trouvés)
    IMPORTANT: nécessite une image CNSS page entière.
    """
    img = image_bgr
    if img is None or img.size == 0:
        return {}

    # Pré-traitement global (améliore cases)
    cleaned = _to_gray_and_clean(img)
    cleaned_bgr = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)

    # ZONES (ratios) — ajustables selon ton rendu PyMuPDF
    # Si ton rendu change (dpi), ratios restent stables.
    Z_BENEF = (0.08, 0.38, 0.92, 0.55)  # zone "Bénéficiaire de soins" / "Nom et prénom"
    Z_CIN   = (0.55, 0.52, 0.92, 0.62)  # zone "N°CIN"
    Z_FEES  = (0.10, 0.30, 0.55, 0.40)  # zone "Montant des frais" (souvent à gauche)

    benef_img = _crop_rel(cleaned_bgr, Z_BENEF)
    cin_img   = _crop_rel(cleaned_bgr, Z_CIN)
    fees_img  = _crop_rel(cleaned_bgr, Z_FEES)

    benef_lines = _ocr_lines(ocr, benef_img)
    cin_lines   = _ocr_lines(ocr, cin_img)
    fees_lines  = _ocr_lines(ocr, fees_img)

    out: Dict[str, Any] = {}

    name = _best_name_candidate(benef_lines)
    if name:
        out["beneficiary_name"] = name

    cin = _extract_cin(cin_lines + benef_lines)
    if cin:
        out["cin"] = cin

    fees = _extract_fees_amount(fees_lines)
    if fees is not None:
        out["fees_amount"] = round(float(fees), 2)

    # debug utile si tu veux voir ce que l'OCR a lu
    out["_debug"] = {
        "benef_lines": benef_lines[:10],
        "cin_lines": cin_lines[:10],
        "fees_lines": fees_lines[:10],
    }

    return out