from claimguard.nlp import extract_entities


def test_extract_entities_empty():
    result = extract_entities("")
    assert isinstance(result, dict)
    assert result == {}


def test_extract_entities_ssn():
    text = "Le numéro est 123-45-6789."  # format american pour exemple
    result = extract_entities(text)
    assert result.get("social_number") == "123-45-6789"
