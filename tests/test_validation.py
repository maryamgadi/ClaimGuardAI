import re

from claimguard.rules.engine import cross_check
from claimguard.validation import validate_claim


def test_cross_check_all_same():
    entities = [
        {"patient_name": "Jean Dupont", "doctor_name": "Martin"},
        {"patient_name": "Jean Dupont", "doctor_name": "Martin"},
        {"patient_name": "Jean Dupont", "doctor_name": "Martin"},
    ]
    assert cross_check(entities) == []


def test_cross_check_missing():
    entities = [
        {"patient_name": "Jean Dupont"},
        {},
        {"patient_name": "Jean Dupont"},
    ]
    anomalies = cross_check(entities)
    assert "manquant" in anomalies[0]


def test_cross_check_mismatch():
    entities = [
        {"patient_name": "Jean Dupont"},
        {"patient_name": "Jean Durand"},
        {"patient_name": "Jean Dupont"},
    ]
    anomalies = cross_check(entities)
    assert "différents" in anomalies[0]


def test_validate_claim_pipeline(tmp_path, monkeypatch):
    # patch extraction + nlp to produce predictable entities
    def fake_extract(path):
        # return predictable text containing patient, doctor, amount, meds
        name = "Jean Dupont" if "ordonnance" in path or "facture" in path else "Jean Durand"
        return (
            f"Nom: {name}\n"
            "Médecin: Martin Paul\n"
            "Date: 01/01/2022\n"
            "Montant: 42€\n"
            "Médicaments: Aspirine"
        )

    # ensure we override the function used by validation.validate_document
    monkeypatch.setattr("claimguard.validation.extract_text", fake_extract)
    monkeypatch.setattr("claimguard.ocr.core.extract_text", fake_extract)
    # we don't need to monkeypatch NLP now, real pipeline will handle fields

    # make medication list reimbursable so rule passes
    monkeypatch.setattr("claimguard.data.druglist.load_med_list", lambda path=None: {"aspirine"})
    # create dummy files
    files = {}
    for name in ("ordonnance", "facture", "feuille"):
        path = tmp_path / f"{name}.txt"
        path.write_text("dummy")
        files[name] = str(path)

    result = validate_claim(files['ordonnance'], files['facture'], files['feuille'])
    # cross mismatch expected because feuille has different patient name
    assert result['cross_anomalies'], "expected cross anomalies for mismatched name"
    assert 'documents' in result
    assert 'ordonnance' in result['documents']
    assert result['decision'] == "rejeté"

    # now simulate all docs matching to get a positive decision
    def fake_extract2(path):
        return (
            "Nom: Jean Dupont\n"
            "Médecin: Martin Paul\n"
            "Date: 01/01/2022\n"
            "Montant: 42€\n"
            "Médicaments: Aspirine"
        )
    monkeypatch.setattr("claimguard.validation.extract_text", fake_extract2)
    monkeypatch.setattr("claimguard.ocr.core.extract_text", fake_extract2)
    result2 = validate_claim(files['ordonnance'], files['facture'], files['feuille'])
    assert result2['cross_anomalies'] == []
    assert result2['decision'] == "validé_et_remboursé"


def test_cli_invocation(tmp_path, monkeypatch):
    # reuse same fake extraction as earlier
    def fake_extract(path):
        return (
            "Nom: Jean Dupont\n"
            "Médecin: Martin Paul\n"
            "Date: 01/01/2022\n"
            "Montant: 42€\n"
            "Médicaments: Aspirine"
        )

    monkeypatch.setattr("claimguard.validation.extract_text", fake_extract)
    monkeypatch.setattr("claimguard.ocr.core.extract_text", fake_extract)
    monkeypatch.setattr("claimguard.data.druglist.load_med_list", lambda path=None: {"aspirine"})

    files = {}
    for name in ("ordonnance", "facture", "feuille"):
        path = tmp_path / f"{name}.txt"
        path.write_text("dummy")
        files[name] = str(path)

    # invoke the CLI via subprocess to mimic real usage
    import subprocess, sys, json

    result = subprocess.run(
        [sys.executable, "-m", "claimguard.cli", files['ordonnance'], files['facture'], files['feuille']],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    output = result.stdout
    data = json.loads(output)
    assert data['decision'] in ("validé_et_remboursé", "rejeté")
