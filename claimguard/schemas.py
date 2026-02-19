from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal, Any

DocType = Literal["feuille_soins", "facture", "ordonnance"]
Decision = Literal["ACCEPT", "REVIEW"]
Severity = Literal["low", "medium", "high", "blocker"]

class DocumentInput(BaseModel):
    doc_type: DocType
    path: str

class ExtractedField(BaseModel):
    value: Optional[str] = None
    confidence: float = 0.0
    source: Optional[str] = None

class DocExtraction(BaseModel):
    doc_type: DocType
    raw_text: str
    fields: Dict[str, ExtractedField] = Field(default_factory=dict)

    @field_validator("fields", mode="before")
    @classmethod
    def coerce_fields(cls, v):
        """
        Accepte:
        - dict[str, ExtractedField]
        - dict[str, dict]  (ex: {"value": "...", "confidence": 0.7, ...})
        - dict[str, str]   (legacy)
        et convertit tout en ExtractedField
        """
        if not v:
            return {}
        if not isinstance(v, dict):
            return {}

        out: Dict[str, ExtractedField] = {}
        for k, val in v.items():
            if isinstance(val, ExtractedField):
                out[k] = val
            elif isinstance(val, dict):
                out[k] = ExtractedField(**val)
            else:
                out[k] = ExtractedField(value=str(val), confidence=0.0, source="legacy")
        return out

class Finding(BaseModel):
    code: str
    message: str
    severity: Severity
    weight: float
    details: Dict[str, Any] = Field(default_factory=dict)

class CaseResult(BaseModel):
    case_id: str
    documents: List[DocExtraction]
    findings: List[Finding]
    score: float
    decision: Decision