import re

def _grab(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None

def extract_fields(text: str, doc_type: str) -> dict:
    """
    Extraction AMO simple mais fiable:
    - toujours chercher 'LABEL : valeur' ou 'LABEL valeur'
    - normaliser montants et dates
    """
    fields = {}

    # -------- commun --------
    nom = _grab(r"(?:Nom\s*(?:Assur[ée]|Patient)\s*:\s*)([A-ZÀ-ÖØ-Ý'\- ]{3,})", text)
    if nom:
        fields["nom_assure"] = nom

    cin = _grab(r"(?:CIN\s*:\s*)([A-Z]{1,2}\d{4,8})", text)
    if cin:
        fields["cin"] = cin

    # Montant : capte 450.00 / 450,00 / 450 DH
    montant = _grab(r"(?:Montant\s*Total\s*:\s*)(\d{1,6}(?:[.,]\d{1,2})?)", text)
    if montant:
        fields["montant_total"] = montant.replace(",", ".")

    # Dates (dd/mm/yyyy)
    date_soins = _grab(r"(?:Date\s*des\s*soins\s*:\s*)(\d{2}/\d{2}/\d{4})", text)
    if date_soins:
        fields["date_soins"] = date_soins

    date_facture = _grab(r"(?:Date\s*Facture\s*:\s*)(\d{2}/\d{2}/\d{4})", text)
    if date_facture:
        fields["date_facture"] = date_facture

    date_ord = _grab(r"(?:Date\s*Ordonnance\s*:\s*)(\d{2}/\d{2}/\d{4})", text)
    if date_ord:
        fields["date_ordonnance"] = date_ord

    # -------- feuille de soins --------
    if doc_type == "feuille_soins":
        imm = _grab(r"(?:Immatriculation\s*CNSS\s*:\s*)(\d{6,12})", text)
        if imm:
            fields["immatriculation_cnss"] = imm

        cachet = re.search(r"(?:Cachet\s*M[ée]decin\s*:\s*)(OUI|YES)", text, re.IGNORECASE)
        if cachet:
            fields["cachet_medecin"] = "yes"

        sign = re.search(r"(?:Signature\s*:\s*)(OUI|YES)", text, re.IGNORECASE)
        if sign:
            fields["signature"] = "yes"

    # -------- facture --------
    if doc_type == "facture":
        acquit = re.search(r"(?:Acquitt[ée]e\s*:\s*)(PAYEE|PAYÉE|OUI|YES)", text, re.IGNORECASE)
        if acquit:
            fields["acquittee"] = "yes"

    # -------- ordonnance --------
    if doc_type == "ordonnance":
        sigmed = re.search(r"(?:Signature\s*M[ée]decin\s*:\s*)(OUI|YES)", text, re.IGNORECASE)
        if sigmed:
            fields["signature_medecin"] = "yes"

    return fields