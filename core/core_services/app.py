# core/core_services/app.py
import importlib
import unicodedata
import re
import os
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, request, jsonify

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("core_service")

# Ensure project root (parent of 'core' folder) is on sys.path so `import core.*` works.
# This tries to find a sibling 'core' directory upward from this file.
HERE = Path(__file__).resolve().parent  # core/core_services
# If this file is at project-root/core/core_services/, then project root is HERE.parent.parent
# We'll search upwards up to 4 levels to locate the directory that contains 'core' as a sibling.
found_root = None
p = HERE
for _ in range(4):
    possible = p.parent  # directory above current
    if (possible / "core").exists():
        found_root = possible
        break
    p = possible

if found_root:
    sys.path.insert(0, str(found_root))
    logger.info(f"Added project root to PYTHONPATH: {found_root}")
else:
    # Last-resort: add HERE.parent (which is the folder containing this file's 'core' sibling)
    # This helps when running from repo root or when core is in the same folder level.
    alt = HERE.parent
    if (alt / "normalization").exists() or (alt / "segmentation").exists():
        sys.path.insert(0, str(alt))
        logger.info(f"Added {alt} to PYTHONPATH as fallback")
    else:
        logger.warning(
            "Could not automatically find project root containing 'core'. "
            "If imports fail, set PYTHONPATH or run from repo root."
        )

def try_import(module_path: str):
    try:
        return importlib.import_module(module_path)
    except Exception as e:
        logger.warning(f"Could not import {module_path}: {e}")
        return None

# Try to import normalization & segmentation modules.
# Note: with the sys.path fix above these imports should resolve to your core package.
norm_mod = try_import("core.normalization.normalizer") or try_import("core.normalization") or try_import("core.norm")
seg_mod = try_import("core.segmentation.segmenter") or try_import("core.segmentation") or try_import("core.segment")

app = Flask(__name__)

# Normalizer caller (best-effort)
def call_normalizer(text: str) -> str:
    if not text:
        return ""
    candidates = [
        "normalize_text", "normalizeText", "normalize", "clean", "nfkc_normalize", "normalize_text_fn"
    ]
    if norm_mod:
        for name in candidates:
            fn = getattr(norm_mod, name, None)
            if callable(fn):
                try:
                    res = fn(text)
                    if isinstance(res, str):
                        return res
                except Exception:
                    logger.exception(f"normalizer function {name} failed")
        # try class-based normalizer
        for attr in dir(norm_mod):
            obj = getattr(norm_mod, attr)
            if callable(obj) and attr[0].isupper():
                try:
                    inst = obj()
                    if hasattr(inst, "normalize") and callable(inst.normalize):
                        res = inst.normalize(text)
                        if isinstance(res, str):
                            return res
                except Exception:
                    continue
    # fallback: Unicode NFKC + strip zero-width
    s = unicodedata.normalize("NFKC", text)
    s = re.sub(r'[\u200B-\u200D\uFEFF]', '', s)
    return s

# Segmenter caller (best-effort)
def call_segmenter(text: str) -> List[Dict[str, Any]]:
    default = [{"id": 1, "type": "text", "text": text}]
    if not text:
        return []
    if seg_mod:
        candidates = ["segment_text", "segmentText", "segment", "segmenter", "split_segments"]
        for name in candidates:
            fn = getattr(seg_mod, name, None)
            if callable(fn):
                try:
                    segs = fn(text)
                    normalized = []
                    if isinstance(segs, (list, tuple)):
                        for i, s in enumerate(segs):
                            if isinstance(s, dict) and "text" in s:
                                normalized.append({
                                    "id": s.get("id", i+1),
                                    "type": s.get("type", "text"),
                                    "text": s.get("text", "")
                                })
                            elif isinstance(s, str):
                                normalized.append({"id": i+1, "type": "text", "text": s})
                            else:
                                txt = getattr(s, "text", None) or getattr(s, "content", None) or str(s)
                                ttype = getattr(s, "type", "text")
                                normalized.append({"id": i+1, "type": ttype, "text": txt})
                        return normalized
                except Exception:
                    logger.exception(f"segmenter '{name}' raised an exception")
    # fallback: split by blank lines
    parts = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    if not parts:
        return default
    return [{"id": i+1, "type": "text", "text": p} for i, p in enumerate(parts)]

# Detection helpers
BASE64_RE = re.compile(r"[A-Za-z0-9+/=]{40,}")
HEX_RE = re.compile(r"\b0x[0-9a-fA-F]{8,}\b")
URL_RE = re.compile(r'\bhttps?://\S+')
EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')

def detect_high_entropy(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    flags = {"highEntropySegments": []}
    for s in segments:
        if BASE64_RE.search(s.get("text", "")):
            flags["highEntropySegments"].append(s.get("id"))
    return flags

def detect_encodings(text: str) -> List[str]:
    encs = []
    if HEX_RE.search(text):
        encs.append("hex-like")
    if BASE64_RE.search(text):
        encs.append("base64-like")
    return encs

def tag_origin(text: str) -> List[str]:
    tags = []
    if URL_RE.search(text):
        tags.append("contains_url")
    if EMAIL_RE.search(text):
        tags.append("contains_email")
    return tags

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "normalizer_available": bool(norm_mod),
        "segmenter_available": bool(seg_mod)
    }), 200

@app.route("/process", methods=["POST"])
def process():
    corr = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id") or "none"
    logger.info(f"process:start correlation={corr}")
    body = request.get_json(silent=True)
    if not body or "prompt" not in body:
        return jsonify({"error": "missing_prompt"}), 400
    prompt = body.get("prompt", "")
    if not isinstance(prompt, str) or prompt.strip() == "":
        return jsonify({"error": "invalid_prompt"}), 400

    # 1) normalization
    try:
        cleaned = call_normalizer(prompt)
    except Exception:
        logger.exception("normalization failed, applying fallback")
        cleaned = unicodedata.normalize("NFKC", prompt)
        cleaned = re.sub(r'[\u200B-\u200D\uFEFF]', '', cleaned)

    # 2) segmentation
    try:
        segments = call_segmenter(cleaned)
    except Exception:
        logger.exception("segmentation failed, applying fallback split")
        parts = [p.strip() for p in re.split(r'\n{2,}', cleaned) if p.strip()]
        segments = [{"id": i+1, "type": "text", "text": p} for i, p in enumerate(parts)] if parts else [{"id":1,"type":"text","text":cleaned}]

    # 3) flags
    flags = detect_high_entropy(segments)
    encs = detect_encodings(cleaned)
    if encs:
        flags["encodings"] = encs
    origins = tag_origin(cleaned)
    if origins:
        flags["originTags"] = origins

    resp = {
        "cleanedPrompt": cleaned,
        "segments": segments,
        "flags": flags
    }
    logger.info(f"process:done correlation={corr} segments={len(segments)} flags={flags}")
    return jsonify(resp), 200

if __name__ == "__main__":
    # default port 5000 (matches docker-compose convention)
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)
