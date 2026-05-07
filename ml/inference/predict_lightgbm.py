import os
from typing import Dict

import logging
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
    """Strict LightGBM loader that only accepts valid save_model() .txt boosters.

    Requirements:
    - Log the exact path being loaded
    - Validate first line to resemble a LightGBM text model (e.g., contains 'tree' or 'Tree=')
    - Do NOT fallback to pickle or other formats
    """

    def __init__(self, model_path):
        self.booster = None
        self.model_path = model_path
        self.logger = logging.getLogger("lightgbm_loader")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Enforce .txt extension
        if not model_path.lower().endswith('.txt'):
            raise RuntimeError(
                f"Invalid model file extension for LightGBM Booster: {model_path}. Expected a .txt saved via Booster.save_model()"
            )

        # Lightweight validation of model file header (first ~5 lines)
        try:
            with open(model_path, "r", encoding="utf-8", errors="ignore") as f:
                head = [next(f, "").strip() for _ in range(5)]
        except Exception as e:
            raise RuntimeError(f"Failed to read model file: {model_path}; error: {e}")

        header_blob = "\n".join([h for h in head if h])
        tokens = ["tree", "Tree=0", "num_leaves"]
        if not header_blob or not any(tok.lower() in header_blob.lower() for tok in tokens):
            raise RuntimeError(
                "Invalid LightGBM model file: not a saved tree model. "
                "Expected text model saved via booster.save_model(). "
                f"Checked first 5 lines for one of {tokens}. Path: {model_path}"
            )

        # Log and attempt to load strictly via Booster
        self.logger.info(f"Loading LightGBM Booster from: {model_path}")
        try:
            self.booster = lgb.Booster(model_file=model_path)
        except Exception as e:
            # Surface clear message to caller without LightGBM internal spam
            raise RuntimeError(
                "LightGBM failed to load model file. Ensure it was saved via Booster.save_model('*.txt'). "
                f"Path: {model_path}; error: {e}"
            )

    def predict_proba(self, X):
        """Return probability predictions (simplified scalar output per sample)."""
        return self.booster.predict(X)


class LightGBMInference:
    """Loads LightGBM models (strict LightGBM .txt boosters) and provides segment-level scoring."""

    def __init__(self, models_dir: str = "ml/models", hash_size: int = 20000) -> None:
        self.models_dir = models_dir
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

