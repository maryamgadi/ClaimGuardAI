from claimguard.rules import apply_rules


def test_apply_rules_missing_ssn():
    anomalies = apply_rules({})
    assert "numéro de sécurité sociale manquant" in anomalies


def test_apply_rules_ok():
    anomalies = apply_rules({"social_number": "123"})
    assert anomalies == []
