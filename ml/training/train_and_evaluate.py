import os
import sys
import numpy as np
import pandas as pd
import joblib
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
from ml.training.label_utils import normalize_attack_type, LABEL_MAPPING


# ============================================================
# MODEL FILENAMES
# ============================================================

MODEL_FILENAMES = {
    "malicious": "malicious_lgbm.txt",
    "persona": "persona_lgbm.txt",
    "infoleak": "infoleak_lgbm.txt",
    "codeexec": "codeexec_lgbm.txt",
}


def load_and_process_dataset(extractor: FeatureExtractor, dataset_path="ml/datasets/clean_llm_dataset.csv"):
    segmenter = Segmenter()

    X = []
    y_mal, y_per, y_inf, y_cod = [], [], [], []

    all_data = pd.read_csv(dataset_path)
    print(f"[+] Loaded {len(all_data)} rows")

    for _, row in all_data.iterrows():
        prompt = row["prompt"]
        raw_attack = row["attack_type"]

        canonical = normalize_attack_type(raw_attack)
        label_tuple = LABEL_MAPPING[canonical]

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



# ============================================================
# 3. TRAINING + EVALUATION
# ============================================================

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

    # LightGBM v4.x early stopping
    try:
        model.set_params(early_stopping_round=50)
        model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], eval_metric="binary_logloss")
    except TypeError:
        model.fit(
            X_train, y_train,
            eval_set=[(X_valid, y_valid)],
            eval_metric="binary_logloss",
            early_stopping_rounds=50
        )
    return model



def evaluate_model(model, X_valid, y_valid):
    preds = model.predict_proba(X_valid)[:, 1]

    f1 = f1_score(y_valid, preds >= 0.5, zero_division=0)

    if len(np.unique(y_valid)) == 1:
        roc = None
    else:
        roc = roc_auc_score(y_valid, preds)

    return f1, roc



# ============================================================
# 4. K-FOLD
# ============================================================

def perform_kfold_cross_validation(X, y, n_splits=5):
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

    fold_scores = []
    fold_models = []

    for i, (train_idx, val_idx) in enumerate(kf.split(X)):
        print(f"  Fold {i+1}/{n_splits}")

        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = train_binary_lightgbm(X_train, X_val, y_train, y_val)
        f1, roc = evaluate_model(model, X_val, y_val)

        fold_scores.append({"f1": f1, "roc": roc})
        fold_models.append(model)

        roc_display = f"{roc:.4f}" if roc is not None else "N/A"
        print(f"    F1: {f1:.4f}, ROC: {roc_display}")

    return fold_scores, fold_models



# ============================================================
# 5. MAIN WORKFLOW
# ============================================================

def main(models_dir="ml/models", use_kfold=True, k_folds=5):
    os.makedirs(models_dir, exist_ok=True)

    extractor = FeatureExtractor()

    print("[1] Loading dataset...")
    X, y_mal, y_per, y_inf, y_cod = load_and_process_dataset(extractor)

    print(f"[2] Total segments: {len(X)}")
    expected_dim = extractor.hash_size + 8 + 6 + 4
    assert X.shape[1] == expected_dim, f"Feature vector mismatch: {X.shape[1]} vs {expected_dim}"

    X, y_mal, y_per, y_inf, y_cod = shuffle(X, y_mal, y_per, y_inf, y_cod, random_state=42)

    label_sets = {
        "malicious": y_mal,
        "persona": y_per,
        "infoleak": y_inf,
        "codeexec": y_cod
    }

    for name, labels in label_sets.items():
        print(f"\n===== {name.upper()} =====")
        fold_scores, fold_models = perform_kfold_cross_validation(X, labels, n_splits=k_folds)

        # Averages
        avg_f1 = np.mean([s["f1"] for s in fold_scores])
        valid_rocs = [s["roc"] for s in fold_scores if s["roc"] is not None]
        avg_roc = np.mean(valid_rocs) if valid_rocs else None

        print(f"\n{name.upper()} Summary:")
        print(f"  Avg F1 : {avg_f1:.4f}")
        print(f"  Avg ROC: {avg_roc:.4f}" if avg_roc is not None else "  Avg ROC: N/A")

        # Save final fold model (dual format: txt booster + pkl full model)
        best_model = fold_models[-1]
        save_path = os.path.join(models_dir, MODEL_FILENAMES[name])
        txt_path = save_path
        pkl_path = txt_path.replace(".txt", ".pkl")
        if hasattr(best_model, "booster_") and best_model.booster_ is not None:
            best_model.booster_.save_model(txt_path)
        joblib.dump(best_model, pkl_path)
        print(f"[+] Saved model to {txt_path} and {pkl_path}")

    print("\n[✓] Training Complete.")



if __name__ == "__main__":
    main(use_kfold=True, k_folds=5)
