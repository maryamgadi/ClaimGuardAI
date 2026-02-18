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
        data = await file.read()
        # pour l'instant, on écrit dans un fichier temporaire
        temp_path = "/tmp/" + file.filename
        with open(temp_path, "wb") as f:
            f.write(data)
        text = extract_text(temp_path)
        entities = extract_entities(text)
        anomalies = apply_rules(entities)
        score = compute_score(anomalies)
        return {"entities": entities, "anomalies": anomalies, "score": score}

    return app
