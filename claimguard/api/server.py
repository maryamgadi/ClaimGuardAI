# claimguard/api/server.py
from fastapi import FastAPI, UploadFile, File, Query
import os
import tempfile
from typing import Any, Dict
from claimguard.rules.engine import apply_rules, cross_check, evaluate_dossier
from claimguard.validation import validate_case as validate_claim_fn
from claimguard.ocr.core import extract_text, extract_text_gemini
from claimguard.nlp.pipeline import extract_entities
from rapidfuzz import process, fuzz

def _suffix(filename: str, default: str = ".bin") -> str:
    ext = os.path.splitext(filename or "")[1]
    return ext if ext else default


async def _save_upload_to_tmp(u: UploadFile) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=_suffix(u.filename)) as tmp:
        content = await u.read()
        tmp.write(content)
        return tmp.name


def _safe_remove(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(title="ClaimGuardAI")

    @app.get("/")
    def root():
        return {"ok": True, "service": "ClaimGuardAI", "docs": "/docs"}

    # ---------- 1 doc ----------
    @app.post("/validate")
    async def validate(file: UploadFile = File(...), debug: bool = Query(False)):
        tmp_path = await _save_upload_to_tmp(file)
        try:
            result = validate_document(tmp_path)

            if debug:
                raw = extract_text(tmp_path) or ""
                ent = extract_entities(raw, doc_type="single")
                result["debug"] = {
                    "raw": {"ocr_length": len(raw), "ocr_preview": raw[:2000]},
                    "clean": {"length": len(ent["cleaned_text"]), "preview": ent["cleaned_text"][:2000]},
                    "fields": ent["fields"],
                    "stats": ent["stats"],
                }

            return result
        finally:
            _safe_remove(tmp_path)

    # ---------- 3 docs ----------
    @app.post("/validate-claim")
    async def validate_claim_route(
        ordonnance: UploadFile = File(...),
        facture: UploadFile = File(...),
        feuille: UploadFile = File(...),
        debug: bool = Query(False),
    ):
        o_path = f_path = s_path = None
        try:
            o_path = await _save_upload_to_tmp(ordonnance)
            f_path = await _save_upload_to_tmp(facture)
            s_path = await _save_upload_to_tmp(feuille)

            result = validate_claim_fn(o_path, f_path, s_path)
            
            if debug:
                t_o = extract_text(o_path) or ""
                t_f = extract_text(f_path) or ""
                t_s = extract_text(s_path) or ""  # PDF OK (core.py le rend en image)

                e_o = extract_entities(t_o, "ordonnance")
                e_f = extract_entities(t_f, "facture")
                e_s = extract_entities(t_s, "feuille")

                result["debug"] = {
                    "ordonnance": {
                        "raw": {"length": len(t_o), "preview": t_o[:2000]},
                        "clean": {"length": len(e_o["cleaned_text"]), "preview": e_o["cleaned_text"][:2000]},
                        "fields": e_o["fields"],
                    },
                    "facture": {
                        "raw": {"length": len(t_f), "preview": t_f[:2000]},
                        "clean": {"length": len(e_f["cleaned_text"]), "preview": e_f["cleaned_text"][:2000]},
                        "fields": e_f["fields"],
                    },
                    "feuille": {
                        "raw": {"length": len(t_s), "preview": t_s[:2000]},
                        "clean": {"length": len(e_s["cleaned_text"]), "preview": e_s["cleaned_text"][:2000]},
                        "fields": e_s["fields"],
                    },
                }

            return result
        finally:
            _safe_remove(o_path)
            _safe_remove(f_path)
            _safe_remove(s_path)

    # ---------- debug OCR (1 doc) ----------
    @app.post("/debug/ocr")
    async def debug_ocr(file: UploadFile = File(...)) -> Dict[str, Any]:
        tmp_path = await _save_upload_to_tmp(file)
        try:
            raw = extract_text(tmp_path) or ""
            ent = extract_entities(raw, doc_type="single")
            return {
                "raw": {"length": len(raw), "preview": raw[:2000]},
                "clean": {"length": len(ent["cleaned_text"]), "preview": ent["cleaned_text"][:2000]},
                "fields": ent["fields"],
                "stats": ent["stats"],
            }
        finally:
            _safe_remove(tmp_path)

    # ---------- debug OCR (3 docs) ----------
    @app.post("/debug/claim-ocr")
    async def debug_claim_ocr(
        ordonnance: UploadFile = File(...),
        facture: UploadFile = File(...),
        feuille: UploadFile = File(...),
        ):
        o_path = f_path = s_path = None
        try:
            o_path = await _save_upload_to_tmp(ordonnance)
            f_path = await _save_upload_to_tmp(facture)
            s_path = await _save_upload_to_tmp(feuille)
            # 1. Lecture Ordonnance (Référence)
            t_o = extract_text(o_path) or ""
            e_o = extract_entities(t_o, "ordonnance")
            nom_ref = e_o["fields"].get("patient_name", "Inconnu")
            doc_ref = e_o["fields"].get("doctor_name", "Inconnu")
            
            # 2. Lecture Facture
            t_f = extract_text(f_path) or ""
            e_f = extract_entities(t_f, "facture")
            
            # 3. Lecture CNSS avec Gemini (Passage du contexte)
            t_s = extract_text_gemini(s_path, context_patient=nom_ref, context_doctor=doc_ref)
            e_s = extract_entities(t_s, "feuille_cnss")

            # 🌟 NOUVEAU : Correction intelligente (Fuzzy Matching)
            # On compare le nom trouvé par Gemini avec le nom de l'ordonnance
            nom_gemini = e_s["fields"].get("beneficiary_name", "")
            if nom_gemini and nom_ref != "Inconnu":
                # Si la ressemblance est > 70%, on force le nom propre de l'ordonnance
                if fuzz.ratio(nom_gemini.upper(), nom_ref.upper()) > 70:
                    print(f"✅ Correction Patient : {nom_gemini} -> {nom_ref}")
                    e_s["fields"]["beneficiary_name"] = nom_ref

            # Pareil pour le médecin
            doc_gemini = e_s["fields"].get("doctor_name", "")
            if doc_gemini and doc_ref != "Inconnu":
                if fuzz.ratio(doc_gemini.upper(), doc_ref.upper()) > 70:
                    print(f"✅ Correction Médecin : {doc_gemini} -> {doc_ref}")
                    e_s["fields"]["doctor_name"] = doc_ref
                    
            # 4. Vérification des anomalies avec les données corrigées
            doc_anomalies = {
                "ordonnance": apply_rules("ordonnance", e_o["fields"]),
                "facture": apply_rules("facture", e_f["fields"]),
                "feuille_cnss": apply_rules("feuille_cnss", e_s["fields"])
            }
        
            cross_anomalies = cross_check(e_o["fields"], e_f["fields"], e_s["fields"])
            verdict = evaluate_dossier(doc_anomalies, cross_anomalies)
            return {
                
                "ordonnance": {"fields": e_o["fields"], "anomalies": doc_anomalies["ordonnance"]},
                "facture": {"fields": e_f["fields"], "anomalies": doc_anomalies["facture"]},
                "feuille": {
                    "raw_gemini": t_s, 
                    "fields": e_s["fields"], 
                     "anomalies": doc_anomalies["feuille_cnss"]
                },
                "cross_anomalies": cross_anomalies,
                "verdict": verdict["decision"],
                "score_confiance": verdict["score"],
                "raison": verdict["reason"]
            }
        finally:
            _safe_remove(o_path)
            _safe_remove(f_path)
            _safe_remove(s_path)
    return app


app = create_app()