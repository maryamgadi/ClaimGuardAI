"""Un serveur FastAPI minimal pour exposer la validation de dossiers."""

from fastapi import FastAPI, UploadFile, File
from claimguard.ocr import extract_text
from claimguard.nlp import extract_entities
from claimguard.rules import apply_rules
from claimguard.scoring import compute_score
import os
from groq import Groq # You will need to pip install groq
from dotenv import load_dotenv

load_dotenv()

def clean_text_with_llm(messy_text: str) -> dict: # On change le retour en dictionnaire
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = (f"Extrais les informations suivantes de cette ordonnance sous forme de JSON uniquement. "
              f"Champs : patient_name, date, drugs (liste), doctor_name.\n"
              f"Texte : {messy_text}")

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"}, # Force le format JSON
        messages=[{"role": "user", "content": prompt}]
    )
    import json
    return json.loads(completion.choices[0].message.content)

def create_app() -> FastAPI:
    app = FastAPI(title="ClaimGuardAI")

    @app.post("/validate")
    async def validate(file: UploadFile = File(...)):
        data = await file.read()
        # pour l'instant, on écrit dans un fichier temporaire
        temp_path = file.filename
        with open(temp_path, "wb") as f:
            f.write(data)

        # 2. OCR Step
        raw_text = extract_text(temp_path)

        # 3. LLM Step - L'IA extrait TOUT d'un coup
        # On renomme la variable pour plus de clarté
        extracted_data = clean_text_with_llm(raw_text)

        # 4. On utilise directement ces données pour les règles
        # Plus besoin d'appeler extract_entities(cleaned_text) qui cause l'erreur
        anomalies = apply_rules(extracted_data)
        score = compute_score(anomalies)

        return {
            "entities": extracted_data, # Vos infos (nom, date, médicaments) sont ici !
            "anomalies": anomalies,
            "score": score,
            "raw_ocr": raw_text
        }
    return app
