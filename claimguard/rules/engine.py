"""Implémentation minimaliste du moteur de règles."""

import difflib
# Champs qui doivent être présents et non vides dans une feuille de soin
REQUIRED_FIELDS = [
    "patient_name",
    "doctor_name",
    "date",
    "amount",
    "medications",
]


def apply_rules(entities: dict) -> list:
    """Évalue les règles métier sur un ensemble d'entités extraites.

    Retourne une liste d'anomalies détectées (vide si tout va bien).
    """
    anomalies = []
    for field in REQUIRED_FIELDS:
        if not entities.get(field):
            anomalies.append(f"{field} manquant ou vide")

    # vérification spécifique: si on a des médicaments, s'assurer qu'ils
    # sont remboursables via la liste
    meds = entities.get("medications")
    if meds:
        from claimguard.data.druglist import is_reimbursable

        for med in meds:
            if not is_reimbursable(med):
                anomalies.append(f"médicament non remboursable: {med}")

    # d'autres règles peuvent être ajoutées dynamiquement
    return anomalies


def cross_check(entities: list) -> list:
    """
    Croise les données entre les 3 documents.
    On s'attend à recevoir une liste stricte : [Ordonnance, Facture, Feuille de Soins]
    """
    anomalies = []
    
    # Sécurité : vérifier qu'on a bien les 3 documents
    if len(entities) != 3:
        return ["Il manque des documents pour faire le croisement."]

    ord_data = entities[0]  # Les données de l'ordonnance
    fac_data = entities[1]  # Les données de la facture
    feu_data = entities[2]  # Les données de la feuille de soins

    # --- 1. VÉRIFICATION DU PATIENT (Doit être présent sur les 3 documents) ---
    patients = [
        ord_data.get("patient_name"), 
        fac_data.get("patient_name"), 
        feu_data.get("patient_name")
    ]
    
    # On filtre les valeurs vides et on met en minuscules pour comparer
    patients_valides = [str(p).lower().strip() for p in patients if p and str(p).lower() != "null"]
    
    if len(patients_valides) < 3:
        anomalies.append("nom de patient manquant dans un des documents")
    else:
        # Si on n'a pas exactement le même nom partout (Attention, l'idéal ici serait 
        # d'utiliser un fuzzy matching (similarité) au lieu de l'égalité stricte)
        if len(set(patients_valides)) > 1:
            anomalies.append(f"noms de patients trop différents : {patients}")

    # --- 2. VÉRIFICATION DU MÉDECIN (Ordonnance VS Feuille de Soins UNIQUEMENT) ---
    # On IGNORE volontairement fac_data.get("doctor_name") car c'est la pharmacie !
    doc_ord = ord_data.get("doctor_name")
    doc_feu = feu_data.get("doctor_name")
    
    if doc_ord and doc_feu and str(doc_ord).lower() != "null" and str(doc_feu).lower() != "null":
        # On compare en minuscules pour éviter les fausses alertes
        if str(doc_ord).lower().strip() != str(doc_feu).lower().strip():
            anomalies.append(f"médecins trop différents : ['{doc_ord}', '{doc_feu}']")

    return anomalies
