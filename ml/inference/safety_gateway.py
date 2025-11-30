# ml/inference/safety_gateway.py
"""
Safety Gateway inference module.

Class: SafetyGateway
API:
    sg = SafetyGateway(models_dir="ml/models", log_path="ml/logs/safety_gateway.log")
    simple_scores, meta = sg.predict(prompt)

Returns:
    simple_scores: {"malicious": x, "persona": y, "infoleak": z, "codeexec": w}

    meta: {
        "scores": {...},                 # same as simple_scores (float)
        "max_score": float,              # highest score among four
        "category": str,                 # name of highest-scoring dimension
        "segment_scores": [...],         # list of per-segment dicts
        "segment_score_map": {           # NEW — mapping segment_text → score_tuple
            "segment text": (m,p,i,c)
        }
    }

Notes:
- Aggregation: MAX across segments (per-dimension).
- No rule engine applied here: module only returns model scores.
"""

import os
import json
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, List, Tuple

# Local imports (assumes these modules exist and were patched earlier)
from core.segmentation import Segmenter
from ml.feature_extraction.extractor import FeatureExtractor
from ml.inference.predict_lightgbm import LightGBMInference


class SafetyGateway:
    """
    SafetyGateway loads the LightGBM inference models and exposes a realtime
    API to predict per-prompt safety scores.

    Usage:
        sg = SafetyGateway(models_dir="ml/models")
        simple_scores, meta = sg.predict("user supplied prompt")
    """

    def __init__(
        self,
        models_dir: str = "ml/models",
        log_path: str = "ml/logs/safety_gateway.log",
        max_log_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 5,
    ):
        # Initialize segmentation and extractor
        self.segmenter = Segmenter()
        self.extractor = FeatureExtractor()  # keep defaults to preserve hash_size

        # Load inference models
        self.inference = LightGBMInference(models_dir=models_dir)

        # Model keys expected (must match LightGBMInference)
        self._keys = ["malicious", "persona", "infoleak", "codeexec"]

        # Initialize logger (structured JSON lines)
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        self.logger = logging.getLogger("safety_gateway")
        self.logger.setLevel(logging.INFO)

        # Avoid duplicate handlers if re-initialized
        if not any(isinstance(h, RotatingFileHandler)
                   and getattr(h, "baseFilename", "") == os.path.abspath(log_path)
                   for h in self.logger.handlers):
            handler = RotatingFileHandler(log_path, maxBytes=max_log_bytes,
                                          backupCount=backup_count, encoding="utf-8")
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)

    def _segment_texts(self, prompt: str) -> List[Any]:
        """
        Segment the prompt and return raw segment objects (Segmenter specific).
        """
        try:
            segments = self.segmenter.segment(prompt)
        except Exception:
            # Fallback: single segment
            segments = [prompt]
        return segments

    def _predict_segment_scores(self, segment) -> Dict[str, float]:
        """
        Predict scores for a single segment.
        """
        scores = self.inference.predict_scores(segment)
        return {k: float(scores.get(k, 0.0)) for k in self._keys}

    def _aggregate_max(self, segment_scores: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Aggregate segment-level scores using MAX for each dimension.
        """
        agg = {k: 0.0 for k in self._keys}
        for sc in segment_scores:
            for k in self._keys:
                v = float(sc.get(k, 0.0))
                if v > agg[k]:
                    agg[k] = v
        return agg

    def predict_scores_for_prompt(self, prompt: str) -> Tuple[Dict[str, float], List[Dict[str, float]], List[str]]:
        """
        Returns aggregated (per-prompt) scores, per-segment score dicts, and the
        list of segment text strings.
        """
        segments = self._segment_texts(prompt)
        seg_scores = [self._predict_segment_scores(seg) for seg in segments]
        agg = self._aggregate_max(seg_scores)
        return agg, seg_scores, segments

    def _build_simple_and_meta(
        self,
        agg: Dict[str, float],
        seg_scores: List[Dict[str, float]],
        segment_texts: List[str],
    ):
        """
        Build:
        - simple_scores: {"malicious": x, ...}
        - meta: extended data including segment_score_map
        """
        simple_scores = {k: float(agg[k]) for k in self._keys}

        # Determine top category
        max_key = max(simple_scores, key=lambda k: simple_scores[k])
        max_score = float(simple_scores[max_key])

        # Build segment_text → score_tuple map
        segment_score_map = {}
        for text, sc in zip(segment_texts, seg_scores):
            segment_score_map[text] = (
                float(sc["malicious"]),
                float(sc["persona"]),
                float(sc["infoleak"]),
                float(sc["codeexec"]),
            )

        meta = {
            "scores": simple_scores,
            "max_score": max_score,
            "category": max_key,
            "segment_scores": seg_scores,
            "segment_score_map": segment_score_map,   # NEW FIELD
        }

        return simple_scores, meta

    def _log_result(self, prompt: str, segments: List[str], simple_scores, meta):
        """
        Structured JSON log line.
        """
        record = {
            "ts": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "prompt": prompt,
            "segments": segments,
            "tags": [],
            "simple_scores": simple_scores,
            "meta": meta,
        }
        try:
            self.logger.info(json.dumps(record, ensure_ascii=False))
        except Exception:
            pass

    def predict(self, prompt: str) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """
        Main API.
        """
        if not isinstance(prompt, str):
            prompt = str(prompt)

        raw_segments = self._segment_texts(prompt)

        try:
            segment_texts = [getattr(s, "text", str(s)) for s in raw_segments]
        except Exception:
            segment_texts = [str(s) for s in raw_segments]

        agg, seg_scores, segments = self.predict_scores_for_prompt(prompt)

        simple_scores, meta = self._build_simple_and_meta(agg, seg_scores, segment_texts)

        try:
            self._log_result(prompt, segment_texts, simple_scores, meta)
        except Exception:
            pass

        return simple_scores, meta


def predict_prompt_tuple(prompt: str, models_dir: str = "ml/models"):
    sg = SafetyGateway(models_dir=models_dir)
    return sg.predict(prompt)
