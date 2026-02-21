import json
import re
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

# 1. Initialisation de Llama 3 via LangChain et Ollama
# On met la 'temperature' à 0 pour qu'il soit précis et factuel (pas créatif)
llm = OllamaLLM(model="llama3", temperature=0.0)

def extract_entities(text: str) -> dict:
    """
    Extrait les informations clés du texte OCR en utilisant l'intelligence de Llama 3.
    """
    # Si le texte est vide (ex: image blanche), on renvoie un dictionnaire vide
    if not text or not text.strip():
        return {}

    # 2. Le Prompt : On explique très clairement à l'IA ce qu'elle doit faire
    prompt_template = """
    Tu es un assistant expert en extraction de données médicales au Maroc (dossiers AMO/CNSS).
    Voici le texte brut extrait d'un document (ordonnance, facture, ou feuille de soins) par un OCR. 
    Le texte contient des fautes d'orthographe et de mise en page.

    --- TEXTE OCR ---
    {texte_ocr}
    -----------------

    TÂCHE :
    Extrais les informations suivantes et renvoie-les STRICTEMENT au format JSON. Ne dis rien d'autre, juste le JSON.
    - "patient_name" : Le nom et prénom du patient. Corrige les fautes évidentes (ex: 'Ee' -> 'El'). Enlève les 'Mme', 'Dr', 'Patient'.
    - "doctor_name" : Le nom du médecin ou de la pharmacie.
    - "date" : La date du document.
    - "amount" : Le montant total à payer (uniquement les chiffres, ex: "189.00").
    - "social_number" : Le numéro d'immatriculation CNSS (généralement 9 chiffres), si présent.
    - "medications" : Une liste contenant les noms des médicaments (ex: ["XILOIAL", "Doliprane"]), si présent.

    RÈGLE ABSOLUE : Si une information est introuvable, mets `null` (ou `[]` pour les médicaments). Ne rajoute aucun commentaire.

    RÉPONSE JSON :
    """

    # 3. Création de la requête
    prompt = PromptTemplate.from_template(prompt_template)
    requete_finale = prompt.format(texte_ocr=text)

    try:
        # 4. Appel à Llama 3 (C'est ici que la magie opère !)
        print("🧠 Llama 3 analyse le texte...")
        reponse_ia = llm.invoke(requete_finale)
        
        # 5. Nettoyage : On s'assure de ne récupérer que la partie JSON de sa réponse
        match = re.search(r'\{.*\}', reponse_ia, re.DOTALL)
        if match:
            json_str = match.group(0)
            donnees_extraites = json.loads(json_str)
            return donnees_extraites
        else:
            print("⚠️ Llama 3 n'a pas renvoyé un format JSON valide.")
            return {}
            
    except Exception as e:
        print(f"❌ Erreur lors de l'appel à Llama 3 : {e}")
        return {}