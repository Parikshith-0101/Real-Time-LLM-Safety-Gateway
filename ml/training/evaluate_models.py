import numpy as np
from sklearn.metrics import f1_score, roc_auc_score
from ml.inference.predict_lightgbm import LightGBMInference
from core.segmentation import Segmenter

"""
Post-training evaluation script.
Computes ROC-AUC and F1 for each of the four LightGBM classifiers
using a held-out validation set supplied by the training script.
"""


def evaluate(model_paths, X_valid, y_valid_dict):
    inf = LightGBMInference()
    segmenter = Segmenter()

    results = {}

    for name, scores_true in y_valid_dict.items():
        preds = []

        # Predict probability score for each sample
        for vector in X_valid:
            dummy_segment = type("Seg", (), {"text": "", "type": "sentence"})()
            setattr(dummy_segment, "text", "")
            setattr(dummy_segment, "type", "sentence")
            dummy_segment.feature_vector = vector

            # Bypass segmentation and use precomputed vector
            score = inf.models[name].predict_proba(vector.reshape(1, -1))[0][1]
            preds.append(score)

        preds = np.array(preds)

        results[name] = {
            "roc_auc": roc_auc_score(scores_true, preds),
            "f1": f1_score(scores_true, preds >= 0.5),
        }

    return results


if __name__ == "__main__":
    print("This script expects evaluation to be called with validation data.")
    print("It is imported and executed by the training phase after splitting.")

