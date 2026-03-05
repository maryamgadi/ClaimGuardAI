# template_engine.py
import cv2
import numpy as np
from . import cnss_zones


def process_cnss_form(image_bgr):
    """
    1. Align the image to the master template.
    2. Extract fields using the zones defined in cnss_zones.py.
    """
    # 1. TODO: Add Alignment logic here (from our previous conversation)
    # aligned_img = align_image(image_bgr, master_template_bgr)

    # 2. Extract specific fields
    # We pass the OCR engine to the zones function
    from .core import _ocr_fr
    results = cnss_zones.extract_cnss_fields(image_bgr, ocr=_ocr_fr())

    return results  # Returns a clean dict: {'cin': 'AB12345', 'name': '...'}