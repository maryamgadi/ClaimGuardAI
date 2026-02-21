# ClaimGuardAI

ClaimGuardAI est un moteur intelligent de validation automatique des dossiers d’assurance maladie (AMO) pour la CNSS. Il analyse et croise les documents soumis, extrait les informations clés via OCR et NLP, applique des règles métier et génère un score de confiance pour chaque dossier.

## Objectifs

1. **Validation automatique** des dossiers avec un score élevé.
2. **Détection d’anomalies** et signalement des fraudes ou erreurs.
3. **Réduction du temps de traitement** et amélioration de la précision.
4. **Solution scalable et sécurisée**.

## Architecture proposée

La structure du projet est organisée en plusieurs composants modulaires : OCR, NLP, règles métier, scoring, et interface (API/CLI). Cela facilite les tests, la maintenance et permet de remplacer ou d’améliorer des sous-projets indépendamment.

```
ClaimGuardAI/
├── claimguard/              # package principal
│   ├── ocr/                 # fonctions d’extraction de texte (EasyOCR, OpenCV,…)
│   │   └── __init__.py
│   ├── nlp/                 # pré‑traitement et extraction d’entités
│   │   └── __init__.py
│   ├── rules/               # moteur de règles métier
│   │   └── __init__.py
│   ├── scoring/             # calcul et normalisation des scores de confiance
│   │   └── __init__.py
│   ├── api/                 # serveur (FastAPI, Flask) ou CLI
│   │   └── __init__.py
│   ├── __init__.py
│   └── validation.py        # orchestrateur principal
├── configs/                 # fichiers de configuration (YAML/JSON/DOTENV)
│   └── config.py
├── tests/                   # tests unitaires et d’intégration
│   ├── test_ocr.py
│   ├── test_nlp.py
│   └── ...
├── logs/                    # répertoire déjà existant pour les sorties de journalisation
├── requirements.txt
└── README.md
```

Chaque sous-module contiendra des classes et fonctions dédiées :
- **ocr** : wrapper sur EasyOCR, opencv et pdf2image pour convertir des PDF en texte
- **nlp** : nettoyage, tokenisation, extraction des champs (nom, n° de sécurité, dates, montants)
- **rules** : définition de règles dynamiques (ex. champs obligatoires, contrôles de cohérence)
- **scoring** : pondération des signalements et génération d’un score de confiance global
- **api** : point d’entrée exposant une API REST ou interface en ligne de commande

## Prochaines étapes

1. Implémenter des squelettes de classes dans chaque package.
2. Ajouter des tests unitaires simples dans `tests/`.
3. Configurer la journalisation dans `logs/`.
4. Documenter les règles et la structure des données dans `configs/`.
> **Note** : pour traiter des PDF, `pdf2image` nécessite les utilitaires
> Poppler (`pdftoppm`, `pdfinfo`). Sur Windows téléchargez un binaire et soit
> ajoutez le dossier `bin` de Poppler à votre `PATH`, soit définissez
> `POPPLER_PATH` vers ce dossier avant de démarrer le serveur (p. ex.
> `setx POPPLER_PATH C:\poppler\bin`).
### Validation de dossiers

Le module `claimguard.validation` fournit deux points d'entrée :

* `validate_document(file_path)` traite un seul fichier (image ou PDF) et
  renvoie les entités extraites, les anomalies détectées et un score.
* `validate_claim(ordonnance, facture, feuille)` prend en charge un dossier
  complet composé d'une ordonnance, d'une facture et d'une feuille de soin.
  Chaque document est analysé séparément puis un **cross‑checking** est
  effectué (vérification des numéros de sécurité sociale, etc.).
  Le résultat inclut les anomalies spécifiques à chaque document ainsi que
  celles issues du croisement.

L'API FastAPI expose désormais deux routes :

```python
@app.post("/validate")          # valide un seul fichier
@app.post("/validate-claim")    # reçoit les trois fichiers et effectue
                                # l'extraction + cross‑checking
```

### Exécuter manuellement sur des fichiers locaux

Pour tester avec vos propres documents sans passer par l'API, un petit
outil en ligne de commande est fourni :

```bash
# depuis la racine du projet (environnement activé)
python -m claimguard.cli ./ordonnance.pdf ./facture.pdf ./feuille.pdf
```

L'application renvoie un JSON contenant les entités pour chaque document,
les anomalies détectées, le score de cohérence, et la `decision` finale
("validé_et_remboursé" ou "rejeté").

> Vous pouvez naturellement appeler `validate_claim()` depuis n'importe
> quel script Python avec des chemins vers vos propres fichiers.

> L'architecture reste évolutive : vous pouvez rajouter un module `ml/` si vous entraînez un modèle, ou `data/` pour stocker des exemples.
