"""Fonctions de base pour l'OCR (EasyOCR/Opencv)."""

import easyocr
from pdf2image import convert_from_path
from PIL import Image
import os

reader = easyocr.Reader(["fr"], gpu=False)


def extract_text(file_path: str) -> str:
    """Extrait le texte brut d'un fichier image ou PDF.

    Args:
        file_path: chemin vers le document.

    Returns:
        Chaîne de caractères contenant le texte détecté.
    """
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    if ext in [".png", ".jpg", ".jpeg", ".tiff"]:
        result = reader.readtext(file_path, detail=0)
        text = "\n".join(result)
    elif ext == ".pdf":
        pages = convert_from_path(file_path)
        for page in pages:
            result = reader.readtext(np.array(page), detail=0)
            text += "\n".join(result) + "\n"
    else:
        raise ValueError(f"Type de fichier non supporté: {ext}")
    return text
