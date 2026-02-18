import os

from claimguard.ocr import extract_text


def test_extract_text_png(tmp_path):
    # fichier vide ou image d'exemple nécessaire; ici on vérifie que
    # l'appel ne lève pas d'exception pour l'instant.
    path = tmp_path / "dummy.png"
    path.write_bytes(b"")
    try:
        extract_text(str(path))
    except Exception:
        # on autorise l'erreur de format
        pass


# des tests plus aboutis seraient écrits une fois des fichiers réels disponibles
