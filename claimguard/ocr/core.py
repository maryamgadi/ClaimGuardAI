# claimguard/ocr/core.py
from __future__ import annotations

import os
import re
from typing import List, Tuple, Optional

import numpy as np
import cv2

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

from paddleocr import PaddleOCR


# ---------------------------
# OCR engine (singleton)
# ---------------------------
_OCR_FR: Optional[PaddleOCR] = None


def _ocr_fr() -> PaddleOCR:
    global _OCR_FR
    if _OCR_FR is None:
        # Important: lang="fr" + modèle latin
        _OCR_FR = PaddleOCR(
            lang="fr",
            use_angle_cls=True,
            det_db_thresh=0.2,       
            det_db_box_thresh=0.4,    # Rend la création des boîtes (bounding boxes) plus agressive
            use_dilation=True
          
        )
    return _OCR_FR


# ---------------------------
# Loading / rendering
# ---------------------------
def _read_image_any_path(path: str) -> Optional[np.ndarray]:
    """
    Lecture image robuste (Unicode path) :
    - tente np.fromfile + cv2.imdecode
    - fallback cv2.imread
    """
    try:
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is not None and img.size > 0:
            return img
    except Exception:
        pass

    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is not None and img.size > 0:
        return img
    return None


def _render_pdf_first_page(path: str, zoom: float = 2.0) -> Optional[np.ndarray]:
    """
    Rend la page 1 d'un PDF -> image BGR (OpenCV).
    """
    if fitz is None:
        return None
    try:
        doc = fitz.open(path)
        if doc.page_count < 1:
            return None
        page = doc.load_page(0)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        # PyMuPDF = RGB -> OpenCV BGR
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img
    except Exception:
        return None


def load_document_as_bgr(path: str) -> np.ndarray:
    """
    Retourne une image BGR OpenCV.
    - PDF : rendu page 1
    - Image : lecture directe
    """
    ext = (os.path.splitext(path)[1] or "").lower()

    if ext == ".pdf":
        img = _render_pdf_first_page(path, zoom=2.2)
        if img is None:
            raise ValueError(f"PDF non lisible (PyMuPDF manquant ou PDF invalide): {path}")
        return img

    img = _read_image_any_path(path)
    if img is None:
        raise ValueError(f"Image vide / non lisible: {path}")
    return img


# ---------------------------
# Preprocess
# ---------------------------
def preprocess_bgr(img: np.ndarray) -> np.ndarray:
    """
    Pré-traitement général (pas spécifique à tes docs):
    - grayscale
    - denoise léger
    - contraste (CLAHE)
    """
    if img is None or img.size == 0:
        raise ValueError("preprocess_bgr: image vide")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise léger
    gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # CLAHE contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    return gray


# ---------------------------
# OCR helpers
# ---------------------------
def _box_center_y(box) -> float:
    # box: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    ys = [p[1] for p in box]
    return float(sum(ys) / 4.0)


def _run_ocr_lines(gray: np.ndarray, drop_score: float = 0.55) -> List[Tuple[str, float, float]]:
    """
    Retourne liste de (text, score, y_center) filtrée par score.
    """
    engine = _ocr_fr()

    # PaddleOCR accepte aussi image en ndarray (grayscale OK)
    result = engine.ocr(gray, cls=True)

    # result format: [[ [box, (text, score)], ... ]]
    items: List[Tuple[str, float, float]] = []
    if not result:
        return items

    # PaddleOCR peut renvoyer liste imbriquée
    lines = result[0] if isinstance(result, list) and len(result) > 0 else []
    for line in lines:
        try:
            box = line[0]
            text = line[1][0]
            score = float(line[1][1])
            if text and score >= drop_score:
                y = _box_center_y(box)
                items.append((text, score, y))
        except Exception:
            continue

    # tri vertical
    items.sort(key=lambda x: x[2])
    return items


def _join_lines(lines: List[str]) -> str:
    # nettoyage espaces + sauts de ligne propres
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        ln = re.sub(r"[ \t]{2,}", " ", ln)
        out.append(ln)
    return "\n".join(out).strip()


def extract_text(path: str, drop_score: float = 0.55) -> str:
    """
    Pipeline OCR complet:
    - charge doc (PDF ou image)
    - preprocess
    - OCR (filtré par score)
    - texte final multi-lignes
    """
    img = load_document_as_bgr(path)
    gray = preprocess_bgr(img)

    items = _run_ocr_lines(gray, drop_score=drop_score)
    texts = [t for (t, s, y) in items]
    return _join_lines(texts)