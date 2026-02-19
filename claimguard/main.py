import uuid
from typing import List

from claimguard.schemas import (
    DocumentInput,
    DocExtraction,
    CaseResult,
    ExtractedField,
)

from claimguard.ocr import ocr_document
from claimguard.extract import extract_fields
from claimguard.rules import run_rules
from claimguard.scoring import score_case


def _wrap_fields(raw_fields: dict, source: str = "ocr_rules", default_conf: float = 0.75) -> dict:
    """Convertit dict[str,str] -> dict[str, ExtractedField]"""
    wrapped = {}
    for k, v in (raw_fields or {}).items():
        wrapped[k] = ExtractedField(
            value=None if v is None else str(v),
            confidence=default_conf,
            source=source,
        )
    return wrapped


def validate_case(docs: List[DocumentInput]) -> CaseResult:
    case_id = str(uuid.uuid4())

    doc_results: List[DocExtraction] = []

    for d in docs:
        raw_text = ocr_document(d.path)

        # dict[str,str]
        raw_fields = extract_fields(raw_text, d.doc_type)

        # dict[str,ExtractedField]
        wrapped = _wrap_fields(raw_fields)

        doc_results.append(
            DocExtraction(
                doc_type=d.doc_type,
                raw_text=raw_text,
                fields=wrapped,
            )
        )

    findings = run_rules(doc_results)
    score, decision = score_case(findings)

    return CaseResult(
        case_id=case_id,
        documents=doc_results,
        findings=findings,
        score=score,
        decision=decision,
    )