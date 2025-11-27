import os
from typing import Dict

import lightgbm as lgb
import numpy as np

from ml.feature_extraction.extractor import FeatureExtractor

MODEL_FILENAMES = {
    "malicious_score": "malicious_lgbm.txt",
    "persona_switch_score": "persona_lgbm.txt",
    "info_leak_score": "infoleak_lgbm.txt",
    "code_exec_score": "codeexec_lgbm.txt",
}


class _BoosterWrapper:
    """Wrapper to expose predict_proba-like behaviour for LightGBM boosters."""

    def __init__(self, model_path: str) -> None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        self.booster = lgb.Booster(model_file=model_path)

    def predict_proba(self, vectors: np.ndarray) -> np.ndarray:
        probs = self.booster.predict(vectors, raw_score=False)
        probs = np.asarray(probs, dtype=np.float32)
        if probs.ndim == 1:
            probs = probs.reshape(-1, 1)
        positive = probs[:, 0]
        negative = 1.0 - positive
        return np.stack([negative, positive], axis=1)


class LightGBMInference:
    """Loads LightGBM boosters and provides probability scores for segments."""

    def __init__(self, models_dir: str = "ml/models", hash_size: int = 20000) -> None:
        self.extractor = FeatureExtractor(hash_size=hash_size)
        self.models: Dict[str, _BoosterWrapper] = {}

        for score_key, filename in MODEL_FILENAMES.items():
            model_path = os.path.join(models_dir, filename)
            self.models[score_key] = _BoosterWrapper(model_path)

    def predict_scores(self, segment) -> Dict[str, float]:
        vector = self.extractor.build_feature_vector(segment).reshape(1, -1)
        scores = {}
        for score_key, booster in self.models.items():
            prob = booster.predict_proba(vector)[0][1]
            scores[score_key] = float(prob)
        return scores

