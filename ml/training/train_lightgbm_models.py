import argparse
import os
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import joblib
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
from lightgbm import LGBMClassifier

from core.segmentation import Segmenter
from ml.feature_extraction.extractor import FeatureExtractor
from ml.training.label_utils import normalize_attack_type, LABEL_MAPPING

MODEL_FILENAMES = {
    "malicious": "malicious_lgbm.txt",
    "persona": "persona_lgbm.txt",
    "infoleak": "infoleak_lgbm.txt",
    "codeexec": "codeexec_lgbm.txt",
}


# ============================================================
# 1. DATASET → SEGMENTS → FEATURES
# ============================================================

def extract_segments(feature_extractor: FeatureExtractor):
    df = pd.read_csv("ml/datasets/clean_llm_dataset.csv")
    segmenter = Segmenter()

    feature_vectors = []
    y_mal, y_per, y_inf, y_cod = [], [], [], []

    for _, record in df.iterrows():
        prompt = record.get("prompt")

        if not prompt:
            continue

        # NEW FIX: canonical label lookup
        canonical = normalize_attack_type(record.get("attack_type"))
        label_tuple = LABEL_MAPPING[canonical]

        try:
            segments = segmenter.segment(prompt)
        except Exception:
            continue

        for seg in segments:
            vec = feature_extractor.build_feature_vector(seg)
            feature_vectors.append(vec)
            y_mal.append(label_tuple[0])
            y_per.append(label_tuple[1])
            y_inf.append(label_tuple[2])
            y_cod.append(label_tuple[3])

    if not feature_vectors:
        raise RuntimeError("No feature vectors were generated from the dataset.")

    X = np.stack(feature_vectors).astype(np.float32)
    return X, y_mal, y_per, y_inf, y_cod


# ============================================================
# 2. SAFE LIGHTGBM TRAINING (v4 COMPATIBLE)
# ============================================================

def train_lightgbm_model(X: np.ndarray, y: List[int]) -> LGBMClassifier:
    y = np.array(y, dtype=np.int8)

    X_train, X_valid, y_train, y_valid = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=True
    )

    model = LGBMClassifier(
        boosting_type="gbdt",
        objective="binary",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=64,
        n_jobs=-1,
        verbose=-1,
    )

    # NEW FIX: LightGBM v4 safe early stopping
    model.set_params(early_stopping_round=50)

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_valid, y_valid)],
        eval_metric="binary_logloss"
    )

    return model


def save_model(model: LGBMClassifier, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    txt_path = output_path
    pkl_path = txt_path.replace(".txt", ".pkl")
    if hasattr(model, "booster_") and model.booster_ is not None:
        model.booster_.save_model(txt_path)
    joblib.dump(model, pkl_path)


# ============================================================
# 3. MAIN WORKFLOW
# ============================================================

def main(models_dir: str) -> None:
    extractor = FeatureExtractor()
    X, y_mal, y_per, y_inf, y_cod = extract_segments(extractor)

    expected_dim = extractor.hash_size + 8 + 6 + 4
    assert X.ndim == 2
    assert X.shape[1] == expected_dim

    X, y_mal, y_per, y_inf, y_cod = shuffle(
        X, y_mal, y_per, y_inf, y_cod, random_state=42
    )

    models = {
        "malicious": train_lightgbm_model(X, y_mal),
        "persona": train_lightgbm_model(X, y_per),
        "infoleak": train_lightgbm_model(X, y_inf),
        "codeexec": train_lightgbm_model(X, y_cod),
    }

    for name, model in models.items():
        save_path = os.path.join(models_dir, MODEL_FILENAMES[name])
        save_model(model, save_path)
        print(f"[+] Saved {name} model to {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models_dir", default="ml/models")
    args = parser.parse_args()
    main(args.models_dir)
