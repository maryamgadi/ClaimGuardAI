import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException

from configs.config import TMP_DIR
from claimguard.schemas import DocumentInput
from claimguard.main import validate_case


def create_app() -> FastAPI:
    app = FastAPI(title="ClaimGuardAI-clean")
    @app.get("/")
    def root():
        return {"status": "ok", "message": "Go to /docs to test"}

    os.makedirs(TMP_DIR, exist_ok=True)

    async def _save(upload: UploadFile) -> str:
        filename = upload.filename or "file"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"]:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

        path = os.path.join(TMP_DIR, f"{uuid.uuid4()}{ext}")
        data = await upload.read()
        with open(path, "wb") as f:
            f.write(data)
        return path

    @app.post("/validate")
    async def validate(
        feuille_soins: UploadFile = File(...),
        facture: UploadFile = File(...),
        ordonnance: UploadFile = File(...),
    ):
        fs_path = await _save(feuille_soins)
        fa_path = await _save(facture)
        or_path = await _save(ordonnance)

        docs = [
            DocumentInput(doc_type="feuille_soins", path=fs_path),
            DocumentInput(doc_type="facture", path=fa_path),
            DocumentInput(doc_type="ordonnance", path=or_path),
        ]
        result = validate_case(docs)
        return result.model_dump()

    return app


app = create_app()
