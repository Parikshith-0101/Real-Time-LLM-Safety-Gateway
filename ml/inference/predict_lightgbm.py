import os
from typing import Dict

import joblib
import lightgbm as lgb
import numpy as np

from core.segmentation import Segmenter
from ml.feature_extraction.extractor import FeatureExtractor

MODEL_FILENAMES = {
    "malicious": "malicious_lgbm.txt",
    "persona": "persona_lgbm.txt",
    "infoleak": "infoleak_lgbm.txt",
    "codeexec": "codeexec_lgbm.txt",
}


class _ModelLoader:
    """Robust loader that tries .txt booster first, then .pkl full model."""

    def __init__(self, model_path):
        self._is_booster = False
        self.booster = None
        self.model = None

        # try .txt booster
        if os.path.exists(model_path):
            try:
                self.booster = lgb.Booster(model_file=model_path)
                self._is_booster = True
                return
            except Exception:
                pass

        # fallback .pkl
        pkl_path = model_path.replace(".txt", ".pkl")
        if os.path.exists(pkl_path):
            self.model = joblib.load(pkl_path)
            self._is_booster = False
        else:
            raise FileNotFoundError(f"Neither {model_path} nor {pkl_path} found.")

    def predict_proba(self, X):
        """Return probability predictions (simplified scalar output per sample)."""
        if self._is_booster:
            return self.booster.predict(X)
        else:
            return self.model.predict_proba(X)[:, 1]


class LightGBMInference:
    """Loads LightGBM models (booster or full) and provides segment-level scoring."""

    def __init__(self, models_dir: str = "ml/models", hash_size: int = 20000) -> None:
        self.extractor = FeatureExtractor(hash_size=hash_size)
        self.segmenter = Segmenter()
        self.models: Dict[str, _ModelLoader] = {}

        for key, filename in MODEL_FILENAMES.items():
            path = os.path.join(models_dir, filename)
            self.models[key] = _ModelLoader(path)

    def predict_scores(self, segment) -> Dict[str, float]:
        """Predict scores for a single segment across all 4 models."""
        vec = self.extractor.build_feature_vector(segment).reshape(1, -1)
        scores = {}
        for key, loader in self.models.items():
            scores[key] = float(loader.predict_proba(vec))
        return scores

    def predict_tuple(self, prompt: str):
        """
        Main inference API: segment prompt, run all models, return max scores.
        Returns (malicious_score, persona_score, infoleak_score, codeexec_score).
        """
        try:
            segments = self.segmenter.segment(prompt)
        except Exception:
            return (0.0, 0.0, 0.0, 0.0)

        best = {"malicious": 0.0, "persona": 0.0, "infoleak": 0.0, "codeexec": 0.0}

        for s in segments:
            sc = self.predict_scores(s)
            # MAX aggregation across segments
            for k in best:
                if sc[k] > best[k]:
                    best[k] = sc[k]

        return (
            best["malicious"],
            best["persona"],
            best["infoleak"],
            best["codeexec"],
        )

