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

def extract_cnss_fields_from_image(image_bgr: np.ndarray, ocr_engine) -> Dict[str, Any]:
    # 1. Validation
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("Image provided to cnss_zones is empty.")

    # 2. Zone Definitions
    Z_BENEF = (0.449, 0.620, 0.476, 0.884)
    Z_CIN   = (0.495, 0.642, 0.520, 0.742)

    # 3. Helper to ensure we return a string, not a list
    def _force_string(ocr_output) -> str:
        # If ocr_output is a list of strings, join them with a space
        if isinstance(ocr_output, list):
            return " ".join([str(x) for x in ocr_output]).strip()
        return str(ocr_output or "").strip()

    # 4. Extract segments
    fields = {}
    benef_raw = _ocr_lines(ocr_engine, _crop_rel(image_bgr, Z_BENEF))
    cin_raw   = _ocr_lines(ocr_engine, _crop_rel(image_bgr, Z_CIN))

    # 5. Assign as strings (FIXES the 'list' attribute error)
    fields["beneficiary_name"] = _force_string(benef_raw)
    fields["cin"] = _force_string(cin_raw)

    return fields



import fitz  # PyMuPDF
import numpy as np
import cv2


def pdf_page_to_image(pdf_path, page_num=0, dpi=300):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))

    # Convert pixmap to numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    # Convert RGBA to BGR for OpenCV
    return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
"""
pdf_path = r"C:\ Users\HP\Downloads\fichier amo.pdf"
img = pdf_page_to_image(pdf_path, page_num=0) # page_num is 0-indexed (0 is the first page)

# 2. Save the image to your Downloads folder so you can see it
cv2.imwrite(r"C:\ Users\HP\Downloads\temp_cnss_page.png", img)

print("Image saved successfully to C:\ Users\HP\Downloads\ temp_cnss_page.png")

pdf_path = r"C:\ Users\HP\Downloads\fichier amo.pdf"
img = pdf_page_to_image(pdf_path, page_num=0) # page_num is 0-indexed (0 is the first page)

# 2. Save the image to your Downloads folder so you can see it
cv2.imwrite(r"C:\ Users\HP\Downloads\temp_cnss_page1.png", img)

print("Image saved successfully to C:\ Users\HP\Downloads\ temp_cnss_page1.png")
"""
import cv2

"""
def calibrate_zone(image_path):
    # 1. Load original image
    img_original = cv2.imread(image_path)
    orig_h, orig_w = img_original.shape[:2]

    # 2. Resize for display (scale down to 1200px width for visibility)
    display_width = 1200
    scale = display_width / orig_w
    display_h = int(orig_h * scale)
    img_display = cv2.resize(img_original, (display_width, display_h))

    # 3. Select ROI on the scaled image
    # Note: selectROI returns (x, y, w, h) based on the image passed to it
    roi = cv2.selectROI("Calibrate - Press ENTER to confirm", img_display, fromCenter=False, showCrosshair=True)
    x, y, w, h = roi

    cv2.destroyAllWindows()

    # 4. Map coordinates back to original image size
    # If the user pressed ESC (roi is 0,0,0,0), exit
    if w == 0 or h == 0:
        print("Selection cancelled.")
        return

    orig_x = int(x / scale)
    orig_y = int(y / scale)
    orig_w_roi = int(w / scale)
    orig_h_roi = int(h / scale)

    # 5. Calculate ratios
    y_min, x_min = orig_y / orig_h, orig_x / orig_w
    y_max, x_max = (orig_y + orig_h_roi) / orig_h, (orig_x + orig_w_roi) / orig_w

    print(f"NEW ZONE: ({y_min:.3f}, {x_min:.3f}, {y_max:.3f}, {x_max:.3f})")
    print(f"Paste this into your cnss_zones.py layout.")


# Usage:
calibrate_zone(r"C:\ Users\HP\Downloads\ temp_cnss_page.png")
"""
def extract_from_pdf(pdf_path, ocr_engine):
    # 1. Render PDF to Image
    img = pdf_page_to_image(pdf_path)

    # 2. Call your existing zone logic
    return extract_cnss_fields_from_image(img, ocr_engine)


def _to_gray_and_clean(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img

    # Augmente le contraste pour faire ressortir l'encre
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)

    # Seuil adaptatif : rend le fond blanc et l'encre noire
    cleaned = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return cleaned