from claimguard.rules import apply_rules


def test_apply_rules_missing_fields():
    anomalies = apply_rules({})
    # should report that at least one required field is missing
    assert len(anomalies) >= 1


def test_apply_rules_ok(monkeypatch):
    # ensure all medications are considered reimbursable for this test
    monkeypatch.setattr("claimguard.data.druglist.load_med_list", lambda path=None: {"ibuprofene"})
    anomalies = apply_rules({
        "patient_name": "Doe John",
        "doctor_name": "Martin Paul",
        "date": "01/01/2020",
        "amount": "100.00",
        "medications": ["ibuprofene"]
    })
    assert anomalies == []


def test_apply_rules_some_missing():
    # missing doctor_name and medications
    entities = {"patient_name": "Foo Bar", "date": "02/02/2022", "amount": "50"}
    anomalies = apply_rules(entities)
    # at least one of the required fields should be reported
    assert any(f in a for a in anomalies for f in ["doctor_name", "medications"])


def test_apply_rules_unreimbursable(monkeypatch):
    # make the drug list empty so any med is non-remboursable
    monkeypatch.setattr("claimguard.data.druglist.load_med_list", lambda path=None: set())
    entities = {
        "patient_name": "Foo Bar",
        "doctor_name": "Dr Who",
        "date": "02/02/2022",
        "amount": "50",
        "medications": ["nonremb"]
    }
    anomalies = apply_rules(entities)
    assert any("non remboursable" in a for a in anomalies)
