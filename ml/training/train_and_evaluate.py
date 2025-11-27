import os
import sys
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple

from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.utils import shuffle
from lightgbm import LGBMClassifier
import lightgbm as lgb

# Fix import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from core.segmentation import Segmenter
from ml.feature_extraction.extractor import FeatureExtractor


# ---------------------------
# LABEL MAPPING
# ---------------------------

LABEL_MAPPING = {
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


# ---------------------------
# 1. LOAD DATASET → SEGMENTS → FEATURES
# ---------------------------

def load_and_process_dataset(extractor: FeatureExtractor, dataset_path="dataset"):
    segmenter = Segmenter()

    X = []
    y_mal, y_per, y_inf, y_cod = [], [], [], []

    train_df = pd.read_csv(os.path.join(dataset_path, "malicious_llm_prompts_train.csv"))
    val_df = pd.read_csv(os.path.join(dataset_path, "malicious_llm_prompts_validation.csv"))
    test_df = pd.read_csv(os.path.join(dataset_path, "malicious_llm_prompts_test.csv"))

    all_data = pd.concat([train_df, val_df, test_df], ignore_index=True)
    print(f"[+] Loaded {len(all_data)} total records from CSV files")

    for _, row in all_data.iterrows():
        prompt = row.get("prompt")
        attack_type = row.get("attack_type")

        if pd.isna(attack_type) or attack_type == "":
            label_tuple = (0, 0, 0, 0)  # benign
        elif attack_type not in LABEL_MAPPING:
            continue
        else:
            label_tuple = LABEL_MAPPING[attack_type]

        try:
            segments = segmenter.segment(prompt)
        except Exception:
            continue

        for seg in segments:
            vec = extractor.build_feature_vector(seg)
            X.append(vec)
            y_mal.append(label_tuple[0])
            y_per.append(label_tuple[1])
            y_inf.append(label_tuple[2])
            y_cod.append(label_tuple[3])

    X = np.stack(X).astype(np.float32)
    return (
        X,
        np.array(y_mal, dtype=np.int8),
        np.array(y_per, dtype=np.int8),
        np.array(y_inf, dtype=np.int8),
        np.array(y_cod, dtype=np.int8),
    )


# ---------------------------
# 2. TRAIN ONE LIGHTGBM MODEL (VERSION SAFE)
# ---------------------------

def train_binary_lightgbm(X_train, X_valid, y_train, y_valid):
    model = LGBMClassifier(
        boosting_type="gbdt",
        objective="binary",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=64,
        n_jobs=-1,
        verbose=-1,
    )

    # LightGBM 4.x early stopping fix
    try:
        model.set_params(early_stopping_round=50)
        model.fit(
            X_train, y_train,
            eval_set=[(X_valid, y_valid)],
            eval_metric="binary_logloss"
        )
    except TypeError:
        # Older LightGBM fallback
        model.fit(
            X_train, y_train,
            eval_set=[(X_valid, y_valid)],
            eval_metric="binary_logloss",
            early_stopping_rounds=50
        )

    return model


# ---------------------------
# 3. SAFE EVALUATION (No ROC Crash)
# ---------------------------

def evaluate_model(model, X_valid, y_valid):
    preds = model.predict_proba(X_valid)[:, 1]

    f1 = f1_score(y_valid, preds >= 0.5, zero_division=0)

    # Avoid ROC error when only one class appears
    if len(np.unique(y_valid)) == 1:
        roc = None
    else:
        roc = roc_auc_score(y_valid, preds)

    return f1, roc


# ---------------------------
# 4. K-FOLD CV (SAFE)
# ---------------------------

def perform_kfold_cross_validation(X, y, n_splits=5):
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

    fold_scores = []
    fold_models = []

    for fold, (train_idx, val_idx) in enumerate(kf.split(X)):
        print(f"  Training fold {fold + 1}/{n_splits}...")

        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = train_binary_lightgbm(X_train, X_val, y_train, y_val)
        f1, roc = evaluate_model(model, X_val, y_val)

        fold_scores.append({"f1": f1, "roc": roc})
        fold_models.append(model)

        roc_display = f"{roc:.4f}" if roc is not None else "N/A"
        print(f"    F1: {f1:.4f}, ROC: {roc_display}")

    return fold_scores, fold_models


# ---------------------------
# 5. MAIN WORKFLOW
# ---------------------------

def main(models_dir="ml/models", use_kfold=True, k_folds=5):
    os.makedirs(models_dir, exist_ok=True)

    extractor = FeatureExtractor()

    print("[1] Loading and processing dataset from CSV files...")
    X, y_mal, y_per, y_inf, y_cod = load_and_process_dataset(extractor)

    print(f"[+] Total segments = {len(X)}")
    expected_dim = extractor.hash_size + 8 + 6 + 4
    assert X.shape[1] == expected_dim, f"Feature dim mismatch: {X.shape[1]} vs {expected_dim}"

    X, y_mal, y_per, y_inf, y_cod = shuffle(X, y_mal, y_per, y_inf, y_cod, random_state=42)

    if use_kfold:
        print(f"\n[2] Performing {k_folds}-fold cross-validation...")
        print("----------------------------")

        label_dicts = {
            "malicious": y_mal,
            "persona": y_per,
            "infoleak": y_inf,
            "codeexec": y_cod
        }

        final_models = {}

        for label_name, y in label_dicts.items():
            print(f"\nCross-validating {label_name} classifier:")

            fold_scores, fold_models = perform_kfold_cross_validation(X, y, n_splits=k_folds)

            valid_rocs = [s["roc"] for s in fold_scores if s["roc"] is not None]
            avg_roc = np.mean(valid_rocs) if valid_rocs else None
            std_roc = np.std(valid_rocs) if valid_rocs else None

            avg_f1 = np.mean([s["f1"] for s in fold_scores])
            std_f1 = np.std([s["f1"] for s in fold_scores])

            roc_display = f"{avg_roc:.4f}" if avg_roc is not None else "N/A"

            print(f"\n{label_name.upper()} Summary:")
            print(f"  Average F1: {avg_f1:.4f} ± {std_f1:.4f}")
            print(f"  Average ROC: {roc_display}")

            # Save last fold model
            model = fold_models[-1]
            save_path = os.path.join(models_dir, MODEL_FILENAMES[label_name])
            model.booster_.save_model(save_path)
            print(f"[+] Saved {label_name} model to {save_path}")

    print("\n[✓] Training + Evaluation complete.")


if __name__ == "__main__":
    main(use_kfold=True, k_folds=5)
