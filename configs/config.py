"""Paramètres de configuration de l'application."""

import os

OCR_LANG = os.getenv("OCR_LANG", "fr")
# backend may be "easyocr" or "paddle"; default is the original easyocr
OCR_BACKEND = os.getenv("OCR_BACKEND", "easyocr").lower()

# global debug flag; prints extra information when True
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# chemin vers un dossier temporaire, etc.
TMP_DIR = os.getenv("TMP_DIR", "/tmp")
