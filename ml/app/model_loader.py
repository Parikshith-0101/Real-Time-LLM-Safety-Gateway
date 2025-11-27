# ml/app/model_loader.py
# Loads the model and vectorizer from disk and exposes a predict function.
import os
import joblib
import numpy as np
from typing import List, Tuple, Dict

THIS_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(THIS_DIR, '..', 'models')

MODEL_PATH = os.path.join(MODEL_DIR, 'model.pkl')
VECT_PATH = os.path.join(MODEL_DIR, 'vectorizer.pkl')

# lazy-loaded artifacts
_model = None
_vectorizer = None

def load_artifacts():
    """
    Loads artifacts into module-level variables.
    Returns True if both model and vectorizer are present.
    """
    global _model, _vectorizer
    if _model is None:
        if os.path.exists(MODEL_PATH):
            _model = joblib.load(MODEL_PATH)
    if _vectorizer is None:
        if os.path.exists(VECT_PATH):
            _vectorizer = joblib.load(VECT_PATH)
    return _model is not None and _vectorizer is not None

def predict_proba_and_labels(prompt: str, segments: List[dict] = None) -> Tuple[float, Dict]:
    """
    Return (score, labels) where score is [0.0,1.0] indicating risk/jailbreak probability.
    If artifacts are missing, fall back to heuristic prediction.
    """
    ready = load_artifacts()
    text = prompt or ""
    labels = {}

    if ready:
        # Combine prompt and segments for context if segments provided
        if segments:
            seg_text = " ".join([s.get('text', '') for s in segments])
            text_input = text + " " + seg_text
        else:
            text_input = text

        X = _vectorizer.transform([text_input])
        # Prefer predict_proba; fallback to decision_function -> sigmoid
        try:
            probs = _model.predict_proba(X)
            score = float(probs[0][1])
        except Exception:
            try:
                df = _model.decision_function(X)
                score = float(1 / (1 + np.exp(-df[0])))
            except Exception:
                score = 0.5

        labels['jailbreak'] = bool(score >= 0.7)
        labels['sensitive'] = bool('password' in text.lower() or 'api_key' in text.lower())

        return score, labels

    # fallback heuristics if no artifacts
    txt = text.lower()
    if "ignore previous instructions" in txt or "reveal system prompt" in txt or "bypass" in txt:
        return 0.95, {"jailbreak": True}
    if "password" in txt or "api_key" in txt or "api-key" in txt:
        return 0.9, {"sensitive": True}
    return 0.3, {"jailbreak": False}
