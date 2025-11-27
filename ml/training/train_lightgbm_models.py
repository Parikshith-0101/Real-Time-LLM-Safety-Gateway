import argparse
import os
from typing import Dict, List, Tuple

import numpy as np
from sklearn.utils import shuffle
from datasets import load_dataset
from lightgbm import LGBMClassifier

from core.segmentation import Segmenter
from ml.feature_extraction.extractor import FeatureExtractor


LABEL_MAPPING: Dict[str, Tuple[int, int, int, int]] = {
    "Prompt Injection": (1, 0, 0, 0),
    "Jailbreaking": (1, 0, 0, 0),
    "Malware Generation": (1, 0, 0, 0),
    "Illegal Activity": (1, 0, 0, 0),
    "Hate Speech / Toxicity": (1, 0, 0, 0),
    "Phishing": (1, 0, 0, 0),
    "Social Engineering": (1, 0, 1, 0),
    "Roleplay / Persona Injection": (1, 1, 0, 0),
    "Developer Mode / Ignore Instructions": (1, 1, 0, 0),
    "Prompt Leakage / System Prompt Extraction": (0, 0, 1, 0),
    "Data Exfiltration / PII Leakage": (0, 0, 1, 0),
    "SQL Injection": (0, 0, 0, 1),
    "Malicious Code Injection": (0, 0, 0, 1),
    "OS Command Execution (RCE)": (0, 0, 0, 1),
}

MODEL_FILENAMES = {
    "malicious": "malicious_lgbm.txt",
    "persona": "persona_lgbm.txt",
    "infoleak": "infoleak_lgbm.txt",
    "codeexec": "codeexec_lgbm.txt",
}


def extract_segments(feature_extractor: FeatureExtractor) -> Tuple[np.ndarray, List[int], List[int], List[int], List[int]]:
    dataset = load_dataset("codesagar/malicious-llm-prompts")
    segmenter = Segmenter()

    feature_vectors: List[np.ndarray] = []
    y_malicious: List[int] = []
    y_persona: List[int] = []
    y_infoleak: List[int] = []
    y_codeexec: List[int] = []

    for split_name, split in dataset.items():
        for record in split:
            prompt = record.get("prompt")
            attack_type = record.get("attack_type")

            if not prompt or attack_type not in LABEL_MAPPING:
                continue

            label_tuple = LABEL_MAPPING[attack_type]
            try:
                segments = segmenter.segment(prompt)
            except Exception:
                continue

            for segment in segments:
                vector = feature_extractor.build_feature_vector(segment)
                feature_vectors.append(vector)
                y_malicious.append(label_tuple[0])
                y_persona.append(label_tuple[1])
                y_infoleak.append(label_tuple[2])
                y_codeexec.append(label_tuple[3])

    if not feature_vectors:
        raise RuntimeError("No feature vectors were generated from the dataset.")

    X = np.stack(feature_vectors).astype(np.float32)
    return X, y_malicious, y_persona, y_infoleak, y_codeexec


def train_lightgbm_model(X: np.ndarray, y: List[int]) -> LGBMClassifier:
    from sklearn.model_selection import train_test_split

    y = np.array(y, dtype=np.int8)

    # 80/20 validation split
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

    model.fit(
        X_train, y_train,
        eval_set=[(X_valid, y_valid)],
        eval_metric="binary_logloss",
        early_stopping_rounds=50
    )

    return model


def save_model(model: LGBMClassifier, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model.booster_.save_model(output_path)


def main(models_dir: str) -> None:
    extractor = FeatureExtractor()
    X, y_malicious, y_persona, y_infoleak, y_codeexec = extract_segments(extractor)

    # --- Feature dimension consistency check ---
    expected_dim = extractor.hash_size + 8 + 6 + 4  # hash + stats + flags + type
    assert X.ndim == 2, f"Feature matrix must be 2D, got shape {X.shape}"
    assert X.shape[1] == expected_dim, (
        f"Feature dimension mismatch: got {X.shape[1]}, expected {expected_dim}"
    )

    # --- Shuffle dataset to avoid label block ordering ---
    from sklearn.utils import shuffle

    X, y_malicious, y_persona, y_infoleak, y_codeexec = shuffle(
        X, y_malicious, y_persona, y_infoleak, y_codeexec,
        random_state=42
    )

    models = {
        "malicious": train_lightgbm_model(X, y_malicious),
        "persona": train_lightgbm_model(X, y_persona),
        "infoleak": train_lightgbm_model(X, y_infoleak),
        "codeexec": train_lightgbm_model(X, y_codeexec),
    }

    for name, model in models.items():
        filename = MODEL_FILENAMES[name]
        save_path = os.path.join(models_dir, filename)
        save_model(model, save_path)
        print(f"[+] Saved {name} model to {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train LightGBM models for LLM Safety Gateway.")
    parser.add_argument("--models_dir", default="ml/models", help="Directory to store trained LightGBM models.")
    args = parser.parse_args()
    main(args.models_dir)

