# ml/app/features.py
# Helpers for feature extraction used by both training and serving.

from typing import Iterable
from sklearn.feature_extraction.text import TfidfVectorizer
import os
import joblib

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

def build_vectorizer(corpus: Iterable[str], max_features: int = 5000):
    """
    Create and fit a TF-IDF vectorizer on the given corpus.
    Return the fitted vectorizer.
    """
    vec = TfidfVectorizer(max_features=max_features, ngram_range=(1,2), analyzer='word')
    vec.fit(corpus)
    return vec

def save_vectorizer(vec, fname='vectorizer.pkl'):
    os.makedirs(MODEL_DIR, exist_ok=True)
    path = os.path.join(MODEL_DIR, fname)
    joblib.dump(vec, path)
    return path

def load_vectorizer(fname='vectorizer.pkl'):
    path = os.path.join(MODEL_DIR, fname)
    if not os.path.exists(path):
        return None
    return joblib.load(path)

def transform_texts(vec, texts):
    return vec.transform(texts)
