import os
import sys
import pytest

from claimguard import config
from claimguard.ocr import extract_text


def test_extract_text_png(tmp_path, monkeypatch):
    # create an empty file -- we only care that the function dispatches
    path = tmp_path / "dummy.png"
    path.write_bytes(b"")

    # monkeypatch readers to avoid invoking real OCR engines
    # easyocr reader: patch readtext
    class FakeEasy:
        def readtext(self, img, detail=0):
            return ["easy"]

    monkeypatch.setattr("claimguard.ocr.core._easy_reader", FakeEasy())

    # paddle reader: patch ocr method
    class FakePaddle:
        def ocr(self, img, cls=False):
            return [[None, ["paddle", 0.9]]]

    monkeypatch.setattr("claimguard.ocr.core._paddle_reader", FakePaddle())

    # default backend (easyocr)
    monkeypatch.setattr(config, "OCR_BACKEND", "easyocr")
    assert extract_text(str(path)) in ("easy", "")

    # if paddle is available we should be able to switch
    try:
        import paddleocr  # noqa: F401
    except ImportError:
        pytest.skip("paddleocr not installed")

    monkeypatch.setattr(config, "OCR_BACKEND", "paddle")
    text = extract_text(str(path))
    assert "paddle" in text

    # if paddleocr were missing the module would raise when first used
    monkeypatch.setattr(config, "OCR_BACKEND", "paddle")
    # temporarily remove the package, simulate absence
    monkeypatch.setitem(sys.modules, 'paddleocr', None)
    with pytest.raises(ImportError):
        extract_text(str(path))


# des tests plus aboutis seraient écrits une fois des fichiers réels disponibles
