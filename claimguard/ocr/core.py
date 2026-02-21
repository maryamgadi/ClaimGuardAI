"""Fonctions de base pour l'OCR (EasyOCR/Opencv)."""

import easyocr
from pdf2image import convert_from_path
from PIL import Image
import os
import numpy as np

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
        # pdf2image requires Poppler tools (pdftoppm/pdfinfo).  On Windows
        # they are not installed by pip.  The user can put the bin directory
        # on PATH or set the POPPLER_PATH environment variable.  If pdfinfo is
        # missing the underlying library will raise PDFInfoNotInstalledError
        # with a hint; we'll let it bubble up but document the requirement.
        poppler_path = os.environ.get("POPPLER_PATH")
        if poppler_path:
            pages = convert_from_path(file_path, poppler_path=poppler_path)
        else:
            pages = convert_from_path(file_path)
        for page in pages:
            # EasyOCR expects a filepath, bytes or numpy array; pdf2image
            # returns PIL Image objects so convert accordingly.
            img_arr = np.array(page)
            result = reader.readtext(img_arr, detail=0)
            text += "\n".join(result) + "\n"
    else:
        raise ValueError(f"Type de fichier non supporté: {ext}")
    print(f"\n--- 🔍 TEXTE BRUT LU PAR L'OCR POUR LE FICHIER : {file_path} ---")
    print(text)
    print("---------------------------------------------------\n")
    return text
