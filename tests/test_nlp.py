from claimguard.nlp import extract_entities


def test_extract_entities_empty():
    result = extract_entities("")
    assert isinstance(result, dict)
    assert result == {}




def test_extract_entities_ssn():
    text = "Le numéro est 123-45-6789."  # format american pour exemple
    result = extract_entities(text)
    assert result.get("social_number") == "123-45-6789"


def test_extract_entities_multiple_fields():
    text = (
        "Nom: Dupont Jean\n"
        "Médecin: Martin Paul\n"
        "Date 05/04/2021\n"
        "Montant 123.45€\n"
        "Médicaments: Aspirine, Paracétamol"
    )
    result = extract_entities(text)
    assert result.get("patient_name") == "Dupont Jean"
    assert result.get("doctor_name") == "Martin Paul"
    assert result.get("date") == "05/04/2021"
    assert result.get("amount").startswith("123")
    assert "Aspirine" in result.get("medications")
    assert "Paracétamol" in result.get("medications")


def test_extract_entities_patient_label_variants():
    text = (
        "Patient : Legrand Marie\n"
        "Médecin - Dubois\n"
        "Date: 12/12/2022\n"
        "Total: 50"  # montant sans symbole
    )
    result = extract_entities(text)
    assert result.get("patient_name") == "Legrand Marie"
    assert result.get("doctor_name") == "Dubois"
    assert result.get("amount") == "50"
