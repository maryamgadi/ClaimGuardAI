"""Exemple basique de pipeline d'entraînement.

Ce module ne fait que montrer la structure : charge un jeu de données CSV, effectue
un pré‑traitement, entraîne un modèle (scikit-learn) et le sérialise.
"""

import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib

MODEL_DIR = os.getenv("MODEL_DIR", "models")


def train_model(csv_path: str, label_column: str, text_column: str, output_name: str):
    """Entraîne un modèle simple à partir d'un CSV annoté.

    Args:
        csv_path: chemin vers le fichier CSV contenant les exemples.
        label_column: nom de la colonne de vérité terrain.
        text_column: nom de la colonne de texte.
        output_name: nom du fichier de sortie (.joblib) dans le dossier MODEL_DIR.
    """
    df = pd.read_csv(csv_path)
    if label_column not in df or text_column not in df:
        raise ValueError("colonnes manquantes dans le CSV")

    X = df[text_column].astype(str)
    y = df[label_column]

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer()),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    pipeline.fit(X, y)

    os.makedirs(MODEL_DIR, exist_ok=True)
    dest = os.path.join(MODEL_DIR, output_name)
    joblib.dump(pipeline, dest)
    return dest


def load_model(name: str):
    """Charge un modèle entraîné depuis le répertoire local."""
    path = os.path.join(MODEL_DIR, name)
    return joblib.load(path)
