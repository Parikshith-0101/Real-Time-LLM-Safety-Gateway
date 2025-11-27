import os
import sys
import numpy as np
import pandas as pd
import joblib
from typing import List, Dict, Tuple
from tqdm import tqdm

from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.utils import shuffle
from lightgbm import LGBMClassifier
import lightgbm as lgb

# Fix import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from core.segmentation import Segmenter
from ml.feature_extraction.extractor import FeatureExtractor
from ml.training.label_utils import normalize_attack_type, LABEL_MAPPING
from ml.inference.predict_lightgbm import LightGBMInference


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

    for _, row in tqdm(all_data.iterrows(), total=len(all_data), desc="Processing dataset", unit="prompt"):
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
# 4. STRATIFIED K-FOLD (HANDLES CLASS IMBALANCE)
# ============================================================

def perform_kfold_cross_validation(X, y, n_splits=5):
    # StratifiedKFold maintains class distribution across folds
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    fold_scores = []
    fold_models = []
    
    # Calculate class distribution for info logging
    unique, counts = np.unique(y, return_counts=True)
    class_dist = {str(unique[i]): counts[i] for i in range(len(unique))}
    print(f"    Class distribution: {class_dist}")

    for i, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        print(f"  Fold {i+1}/{n_splits}")

        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        # Verify stratification preserved in fold
        fold_dist = {str(np.unique(y_train)[i]): np.sum(y_train == np.unique(y_train)[i]) for i in range(len(np.unique(y_train)))}
        print(f"    Fold class distribution: {fold_dist}")

        model = train_binary_lightgbm(X_train, X_val, y_train, y_val)
        f1, roc = evaluate_model(model, X_val, y_val)

        fold_scores.append({"f1": f1, "roc": roc})
        fold_models.append(model)

        roc_display = f"{roc:.4f}" if roc is not None else "N/A"
        print(f"    F1: {f1:.4f}, ROC: {roc_display}")

    return fold_scores, fold_models



# ============================================================
# 5. MAIN WORKFLOW (WITH STRATIFIED K-FOLD)
# ============================================================

def main(models_dir="ml/models", use_kfold=True, k_folds=5):
    """
    Train and evaluate LightGBM models using Stratified K-Fold cross-validation.
    
    Stratified K-Fold maintains class distribution across folds, preventing
    class imbalance issues in small folds (improvement over regular K-Fold).
    """
    os.makedirs(models_dir, exist_ok=True)

    extractor = FeatureExtractor()

    print("[1] Loading dataset...")
    X, y_mal, y_per, y_inf, y_cod = load_and_process_dataset(extractor)

    print("[2] Splitting dataset into TRAIN (80%) and TEST (10%) and VALIDATION via KFold (10%)...")

    (
        X_train, X_test,
        y_mal_train, y_mal_test,
        y_per_train, y_per_test,
        y_inf_train, y_inf_test,
        y_cod_train, y_cod_test
    ) = train_test_split(
        X, y_mal, y_per, y_inf, y_cod,
        test_size=0.10,
        random_state=42,
        stratify=y_mal          # primary stratification based on malicious label
    )

    # Replace X and labels for KFold
    X = X_train
    y_mal = y_mal_train
    y_per = y_per_train
    y_inf = y_inf_train
    y_cod = y_cod_train

    print(f"[3] Total TRAIN segments (after split): {len(X)}")
    print(f"    TEST segments: {len(X_test)}")
    expected_dim = extractor.hash_size + 8 + 6 + 4
    assert X.shape[1] == expected_dim, f"Feature vector mismatch: {X.shape[1]} vs {expected_dim}"
    print(f"[+] Feature dimension validated: {X.shape[1]}")
    print(f"[+] Using Stratified K-Fold with {k_folds} splits to prevent class imbalance in folds")

    X, y_mal, y_per, y_inf, y_cod = shuffle(X, y_mal, y_per, y_inf, y_cod, random_state=42)

    label_sets = {
        "malicious": y_mal,
        "persona": y_per,
        "infoleak": y_inf,
        "codeexec": y_cod
    }
    
    print(f"[4] Using fixed hyperparameters: n_estimators=300, learning_rate=0.05, num_leaves=64")
    print(f"    (For tuning, modify train_lightgbm_models.py HYPERPARAM_GRID or use grid search)\n")

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

    print("\n[FINAL TEST EVALUATION]")
    print("[*] Loading saved models for real test-set scoring...")

    inference = LightGBMInference(models_dir=models_dir)

    TEST_LABEL_SETS = {
        "malicious": y_mal_test,
        "persona":   y_per_test,
        "infoleak":  y_inf_test,
        "codeexec":  y_cod_test,
    }

    # Reshape X_test if needed
    X_test_array = X_test

    for name, y_test in TEST_LABEL_SETS.items():
        print(f"\n--- TEST RESULTS: {name.upper()} ---")

        preds = []
        for i in range(len(X_test_array)):
            p = inference.models[name].predict_proba(
                X_test_array[i].reshape(1, -1)
            )
            preds.append(p)

        preds = np.array(preds).reshape(-1)

        test_f1 = f1_score(y_test, preds >= 0.5, zero_division=0)

        if len(np.unique(y_test)) == 1:
            test_roc = None
            roc_display = "N/A (single class in test)"
        else:
            test_roc = roc_auc_score(y_test, preds)
            roc_display = f"{test_roc:.4f}"

        print(f"TEST F1 : {test_f1:.4f}")
        print(f"TEST ROC: {roc_display}")

    print("\n[✓] True Test Evaluation complete.")
    print("[✓] Training and Evaluation Pipeline Complete (80/10/10 split).")



if __name__ == "__main__":
    main(use_kfold=True, k_folds=5)
