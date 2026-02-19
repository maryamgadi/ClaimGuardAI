import os
import cv2
import easyocr
from pdf2image import convert_from_path
from configs.config import PDF_DPI

# Initialise le reader une seule fois
reader = easyocr.Reader(["fr", "en"], gpu=False)


def ocr_document(file_path: str) -> str:
    """
    OCR robuste pour PDF et images.
    - PDF -> convertit en images
    - Image -> lecture OpenCV sécurisée
    """

    ext = os.path.splitext(file_path)[1].lower()

    # ---- CAS PDF ----
    if ext == ".pdf":
        pages = convert_from_path(file_path, dpi=PDF_DPI)
        full_text = []

        for page in pages:
            img = cv2.cvtColor(
                cv2.imread(page.filename) if hasattr(page, "filename") else cv2.cvtColor(
                    cv2.imdecode(
                        cv2.imencode(".png", page)[1], cv2.IMREAD_COLOR
                    ), cv2.COLOR_BGR2RGB
                ),
                cv2.COLOR_BGR2RGB
            )

            if img is None:
                raise ValueError(f"Cannot read converted PDF page: {file_path}")

            lines = reader.readtext(img, detail=0)
            full_text.extend(lines)

        return "\n".join(full_text)

    # ---- CAS IMAGE ----
    img = cv2.imread(file_path)

    if img is None:
        raise ValueError(f"Cannot read image file: {file_path}")

    lines = reader.readtext(img, detail=0)
    return "\n".join(lines)
