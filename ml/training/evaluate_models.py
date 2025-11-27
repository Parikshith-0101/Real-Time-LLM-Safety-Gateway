import numpy as np
from sklearn.metrics import f1_score, roc_auc_score
from ml.inference.predict_lightgbm import LightGBMInference


"""
Post-training evaluation script.
Computes ROC-AUC and F1 for each of the four LightGBM classifiers
using a held-out validation set returned by the training pipeline.
"""


def evaluate(X_valid, y_valid_dict, model_dir="ml/models"):
    """
    X_valid: numpy array of shape (N, D)
    y_valid_dict: {
        "malicious": y_mal_valid,
        "persona": y_per_valid,
        "infoleak": y_inf_valid,
        "codeexec": y_cod_valid
    }
    """

    inf = LightGBMInference(model_dir=model_dir)
    results = {}

    for name, y_true in y_valid_dict.items():
        loader = inf.models[name]

        # Predict probability for each feature vector
        preds = loader.predict_proba(X_valid)
        # Handle both scalar and array outputs
        if isinstance(preds, np.ndarray) and preds.ndim > 1:
            preds = preds[:, 1]

        # F1 SCORE (safe)
        f1 = f1_score(y_true, preds >= 0.5, zero_division=0)

        # ROC-AUC (safe)
        if len(np.unique(y_true)) == 1:
            roc = None  # cannot compute ROC-AUC
        else:
            roc = roc_auc_score(y_true, preds)

        results[name] = {"f1": f1, "roc_auc": roc}

    return results


if __name__ == "__main__":
    print("This script is intended to be imported by the training pipeline.")
    print("Call evaluate(X_valid, y_valid_dict) after generating validation splits.")
