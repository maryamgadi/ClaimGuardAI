import os

# OCR
OCR_LANGS = os.getenv("OCR_LANGS", "fr").split(",")
OCR_GPU = os.getenv("OCR_GPU", "0") == "1"
PDF_DPI = int(os.getenv("PDF_DPI", "300"))
POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\poppler\Library\bin")


# Temp storage (Windows-friendly)
TMP_DIR = os.getenv("TMP_DIR", os.path.join(os.getcwd(), "tmp_uploads"))

# Decision thresholds
ACCEPT_SCORE_THRESHOLD = float(os.getenv("ACCEPT_SCORE_THRESHOLD", "85"))

# Weights (0..1, will be converted to 0..100 score)
WEIGHTS = {
    "MISSING_REQUIRED_FIELD": 0.10,
    "DATE_ORDER_INVALID": 0.15,
    "AMOUNT_MISMATCH": 0.20,
    "NAME_MISMATCH": 0.20,
    "FACTURE_NOT_ACQUITTED": 0.25,
    "MISSING_DOC": 0.25,
}
