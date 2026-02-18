"""Paramètres de configuration de l'application."""

import os

OCR_LANG = os.getenv("OCR_LANG", "fr")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# chemin vers un dossier temporaire, etc.
TMP_DIR = os.getenv("TMP_DIR", "/tmp")
