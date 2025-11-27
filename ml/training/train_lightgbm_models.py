import argparse
import os
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import joblib
from tqdm import tqdm
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

    print(f"[+] Processing {len(df)} prompts...")
    for _, record in tqdm(df.iterrows(), total=len(df), desc="Extracting segments", unit="prompt"):
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
# 2. HYPERPARAMETER TUNING (OPTIONAL)
# ============================================================

DEFAULT_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "num_leaves": 64,
}

# Grid search space for optional tuning
HYPERPARAM_GRID = {
    "n_estimators": [200, 300, 400],
    "learning_rate": [0.01, 0.05, 0.1],
    "num_leaves": [32, 64, 128],
}


# ============================================================
# 3. SAFE LIGHTGBM TRAINING (v4 COMPATIBLE)
# ============================================================

def train_lightgbm_model(X: np.ndarray, y: List[int], hyperparams: Dict = None) -> LGBMClassifier:
    y = np.array(y, dtype=np.int8)

    X_train, X_valid, y_train, y_valid = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=True
    )

    # Use provided hyperparams or fall back to defaults
    params = hyperparams if hyperparams else DEFAULT_PARAMS

    model = LGBMClassifier(
        boosting_type="gbdt",
        objective="binary",
        n_estimators=params["n_estimators"],
        learning_rate=params["learning_rate"],
        num_leaves=params["num_leaves"],
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
# 4. MAIN WORKFLOW
# ============================================================

def main(models_dir: str, use_default_params: bool = True) -> None:
    extractor = FeatureExtractor()
    X, y_mal, y_per, y_inf, y_cod = extract_segments(extractor)

    expected_dim = extractor.hash_size + 8 + 6 + 4
    assert X.ndim == 2
    assert X.shape[1] == expected_dim
    print(f"[+] Feature dimension validated: {X.shape[1]}")

    X, y_mal, y_per, y_inf, y_cod = shuffle(
        X, y_mal, y_per, y_inf, y_cod, random_state=42
    )

    # Use default hyperparameters (or modify HYPERPARAM_GRID for grid search)
    hyperparams = DEFAULT_PARAMS if use_default_params else None
    print(f"[+] Training with params: {hyperparams or 'default'}")

    models = {
        "malicious": train_lightgbm_model(X, y_mal, hyperparams),
        "persona": train_lightgbm_model(X, y_per, hyperparams),
        "infoleak": train_lightgbm_model(X, y_inf, hyperparams),
        "codeexec": train_lightgbm_model(X, y_cod, hyperparams),
    }

    for name, model in models.items():
        save_path = os.path.join(models_dir, MODEL_FILENAMES[name])
        save_model(model, save_path)
        print(f"[+] Saved {name} model to {save_path}")
    
    print("[✓] Training complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models_dir", default="ml/models")
    parser.add_argument("--use_default_params", action="store_true", default=True,
                        help="Use default hyperparameters (set to False for grid search)")
    args = parser.parse_args()
    main(args.models_dir, args.use_default_params)
