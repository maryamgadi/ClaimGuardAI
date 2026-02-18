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

> L'architecture reste évolutive : vous pouvez rajouter un module `ml/` si vous entraînez un modèle, ou `data/` pour stocker des exemples.
