"""Un serveur FastAPI minimal pour exposer la validation de dossiers."""

from fastapi import FastAPI, UploadFile, File
from claimguard.ocr import extract_text
from claimguard.nlp import extract_entities
from claimguard.rules import apply_rules
from claimguard.scoring import compute_score


def create_app() -> FastAPI:
    app = FastAPI(title="ClaimGuardAI")

    @app.post("/validate")
    async def validate(file: UploadFile = File(...)):
        # backward‑compatible single‑file endpoint
        data = await file.read()
        temp_path = "/tmp/" + file.filename
        with open(temp_path, "wb") as f:
            f.write(data)
        text = extract_text(temp_path)
        print("\n--- 🔍 TEXTE BRUT VU PAR L'OCR ---")
        print(text)
        print("----------------------------------\n")
        entities = extract_entities(text)
        anomalies = apply_rules(entities)
        score = compute_score(anomalies)
        return {"entities": entities, "anomalies": anomalies, "score": score}

    @app.post("/validate-claim")
    async def validate_claim(
        ordonnance: UploadFile = File(...),
        facture: UploadFile = File(...),
        feuille: UploadFile = File(...),
    ):
        # lit chaque fichier en mémoire puis on réécrit temporairement
        paths = {}
        for name, upload in [("ordonnance", ordonnance), ("facture", facture), ("feuille", feuille)]:
            data = await upload.read()
            temp_path = "temp_" + upload.filename
            with open(temp_path, "wb") as f:
                f.write(data)
            paths[name] = temp_path

        from claimguard.validation import validate_claim as validate_fn
        result = validate_fn(paths["ordonnance"], paths["facture"], paths["feuille"])
        return result

    return app
