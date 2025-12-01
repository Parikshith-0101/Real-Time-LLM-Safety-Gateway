# ml/app/main.py
"""
ML inference + agent service (Flask).
This version ensures model loader (which fixes sys.path) is invoked BEFORE importing
the agent orchestrator so ml.agentic.* imports succeed.
"""
import os
import sys
import logging
import traceback
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml_service")

app = Flask(__name__)
CORS(app)  # allow all origins for dev; restrict in production

# Configuration (can be overridden via env)
MODELS_DIR = os.environ.get(
    "MODELS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models")),
)
LOG_PATH = os.environ.get(
    "SG_LOG_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs", "safety_gateway.log")),
)

# ---- model loader: ensure project path & init SafetyGateway early ----
# Import model_loader first because it adjusts sys.path (repo-root) so ml.* imports work.
try:
    # model_loader provides init_safety_gateway() and get_safety_gateway()
    from model_loader import get_safety_gateway, init_safety_gateway, ModelNotLoadedError
    # attempt eager init so that repo-root adjustments happen early
    try:
        init_safety_gateway(models_dir=MODELS_DIR, log_path=LOG_PATH)
        logger.info(f"SafetyGateway initialized (models_dir={MODELS_DIR})")
    except Exception as e:
        # log but continue — get_safety_gateway() will try lazy-init later if needed
        logger.exception("SafetyGateway init at startup failed: %s", e)
except Exception:
    # If model_loader import failed, we still continue but subsequent code may handle it.
    logger.exception("Failed to import model_loader. Agent imports may fail until sys.path fixed.")


# ---- Now import orchestrator (after attempting model_loader/init) ----
# We'll import the orchestrator but guard and log full tracebacks on failure.
SafetyOrchestrator = None
try:
    # Ensure repo root is on sys.path as a final safety (search upward for repo root)
    HERE = Path(__file__).resolve().parent  # ml/app
    repo_root = None
    p = HERE
    for _ in range(6):
        candidate = p.parent
        if (candidate / "ml").exists() and (candidate / "core").exists():
            repo_root = candidate
            break
        p = candidate
    if repo_root:
        repo_root_str = str(repo_root)
        if repo_root_str not in sys.path:
            sys.path.insert(0, repo_root_str)
            logger.info("Added repo root to sys.path: %s", repo_root_str)
    else:
        fallback = str(HERE.parent)
        if fallback not in sys.path:
            sys.path.insert(0, fallback)
            logger.warning("Could not find repo root; added fallback to sys.path: %s", fallback)

    # Attempt import
    from ml.agentic.orchestrator import SafetyOrchestrator as _SafetyOrchClass
    logger.info("Imported ml.agentic.orchestrator class")

    # Smoke-instantiation test (optional): try to instantiate once to surface init errors early
    try:
        _ = _SafetyOrchClass()
        logger.info("SafetyOrchestrator smoke-instantiation succeeded")
        SafetyOrchestrator = _SafetyOrchClass
        del _
    except Exception:
        # Keep the class (import succeeded) but log instantiation traceback
        SafetyOrchestrator = _SafetyOrchClass
        logger.exception("SafetyOrchestrator imported but instantiation failed during smoke test")
        logger.error("Instantiation traceback:\n%s", traceback.format_exc())
except Exception:
    SafetyOrchestrator = None
    logger.exception("SafetyOrchestrator import failed; /agent will return conservative fallback")
    logger.error("Full import traceback:\n%s", traceback.format_exc())


# Provide a helper for lazy initialization (used by /agent)
_ORCH_SINGLETON = None
def get_orchestrator():
    """
    Return a SafetyOrchestrator instance, or None if unavailable.
    Attempts lazy instantiation and logs full traceback on failure.
    """
    global _ORCH_SINGLETON
    if _ORCH_SINGLETON is not None:
        return _ORCH_SINGLETON

    if SafetyOrchestrator is None:
        logger.warning("SafetyOrchestrator class not available for lazy init.")
        return None

    try:
        _ORCH_SINGLETON = SafetyOrchestrator()
        logger.info("SafetyOrchestrator lazy-initialized successfully")
        return _ORCH_SINGLETON
    except Exception as e:
        logger.exception("Lazy init of SafetyOrchestrator failed: %s", e)
        logger.error("Lazy init traceback:\n%s", traceback.format_exc())
        _ORCH_SINGLETON = None
        return None


# ---- Flask endpoints ----
@app.get("/health")
def health():
    """
    Simple health endpoint.
    Returns models_loaded flag and models_dir for debugging.
    """
    try:
        sg = get_safety_gateway()
        info = {
            "status": "ok",
            "models_loaded": True,
            "models_dir": getattr(sg.inference, "models_dir", MODELS_DIR),
        }
        return jsonify(info), 200
    except ModelNotLoadedError:
        return jsonify({"status": "ok", "models_loaded": False, "models_dir": MODELS_DIR}), 200
    except Exception:
        logger.exception("Health check failed")
        return jsonify({"status": "error"}), 500


@app.post("/predict")
def predict():
    """
    POST /predict
    Body JSON: { "prompt": "some text" }
    Returns ML model scores and meta.
    """
    body = request.get_json(force=True, silent=True)
    if not body or "prompt" not in body:
        return jsonify({"error": "missing_prompt"}), 400

    prompt = body.get("prompt") or ""
    if not isinstance(prompt, str):
        prompt = str(prompt)

    correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id")

    # Ensure SafetyGateway is available (lazy init)
    try:
        sg = get_safety_gateway()
    except ModelNotLoadedError:
        try:
            init_safety_gateway(models_dir=MODELS_DIR, log_path=LOG_PATH)
            sg = get_safety_gateway()
        except Exception as e:
            logger.exception("Model not loaded and lazy init failed: %s", e)
            return jsonify({"error": "models_not_loaded"}), 503
    except Exception as e:
        logger.exception("Unexpected error retrieving SafetyGateway: %s", e)
        return jsonify({"error": "models_error", "message": str(e)}), 500

    try:
        simple_scores, meta = sg.predict(prompt)
        resp = {"simple_scores": simple_scores, "meta": meta}
        if correlation_id:
            resp["correlation_id"] = correlation_id
        return jsonify(resp), 200
    except Exception as e:
        logger.exception("Prediction failed: %s", e)
        return jsonify({"error": "prediction_failed", "message": str(e)}), 500


def map_orchestrator_to_agent_json(result_obj, original_prompt):
    """
    Normalize orchestrator result into agent JSON schema:
    {verdict: 'allow'|'sanitize', sanitized_prompt: str, explanation: str, confidence: float}
    """
    action = result_obj.get("action") or result_obj.get("final_action") or "allow"
    safe_prompt = result_obj.get("safe_prompt") or result_obj.get("sanitized_prompt") or original_prompt
    reason = result_obj.get("reason") or result_obj.get("explanation") or ""
    scores = result_obj.get("scores") or {}

    # confidence: use max ML score if present
    confidence = 0.0
    try:
        if isinstance(scores, dict) and scores:
            confidence = float(max(scores.values()))
        else:
            confidence = float(result_obj.get("confidence", 0.0) or 0.0)
    except Exception:
        confidence = 0.0

    if action == "allow":
        verdict = "allow"
        sanitized_prompt = original_prompt
    elif action == "sanitize":
        verdict = "sanitize"
        sanitized_prompt = safe_prompt
    else:
        # map any other action to sanitize conservatively
        verdict = "sanitize"
        if safe_prompt and safe_prompt != original_prompt:
            sanitized_prompt = safe_prompt
        else:
            sanitized_prompt = (
                "This prompt has been safely transformed to remove potentially harmful content. "
                "Ask for defensive or educational guidance about the topic instead."
            )
            reason = (reason + f" (mapped from {action})").strip()
        if action == "user_review":
            confidence = min(confidence or 0.6, 0.6)
        elif action == "block":
            confidence = max(confidence or 0.9, 0.9)

    confidence = max(0.0, min(1.0, float(confidence)))
    return {
        "verdict": verdict,
        "sanitized_prompt": sanitized_prompt,
        "explanation": reason,
        "confidence": confidence,
    }


@app.post("/agent")
def run_agent():
    """
    POST /agent
    Body: { "prompt": "<text>" }
    Returns: single JSON object following agent schema:
      { "verdict": "allow"|"sanitize", "sanitized_prompt": str, "explanation": str, "confidence": float }
    """
    body = request.get_json(force=True, silent=True)
    if not body or "prompt" not in body:
        return jsonify({"error": "missing_prompt"}), 400

    prompt = body.get("prompt") or ""
    if not isinstance(prompt, str):
        prompt = str(prompt)

    # 1) Get ML scores & meta from SafetyGateway (lazy init if needed)
    try:
        sg = get_safety_gateway()
    except ModelNotLoadedError:
        try:
            init_safety_gateway(models_dir=MODELS_DIR, log_path=LOG_PATH)
            sg = get_safety_gateway()
        except Exception as e:
            logger.exception("Model not loaded and lazy init failed: %s", e)
            fallback = {
                "verdict": "sanitize",
                "sanitized_prompt": "This prompt has been safely transformed to avoid harmful content.",
                "explanation": "Models not loaded; conservative sanitized fallback returned.",
                "confidence": 0.5,
            }
            return jsonify(fallback), 503
    except Exception as e:
        logger.exception("Unexpected error retrieving SafetyGateway: %s", e)
        fallback = {
            "verdict": "sanitize",
            "sanitized_prompt": "This prompt has been safely transformed to avoid harmful content.",
            "explanation": "Models not available; conservative sanitized fallback returned.",
            "confidence": 0.5,
        }
        return jsonify(fallback), 500

    try:
        simple_scores, meta = sg.predict(prompt)
    except Exception as e:
        logger.exception("SafetyGateway prediction failed: %s", e)
        fallback = {
            "verdict": "sanitize",
            "sanitized_prompt": "This prompt has been safely transformed to avoid harmful content.",
            "explanation": "Prediction failed; conservative sanitized fallback returned.",
            "confidence": 0.5,
        }
        return jsonify(fallback), 500

    # Build orchestrator inputs
    category = None
    segment_score_map = {}
    segment_texts = []
    if isinstance(meta, dict):
        category = meta.get("category")
        if "segment_score_map" in meta and isinstance(meta["segment_score_map"], dict):
            segment_score_map = meta["segment_score_map"]
            segment_texts = list(segment_score_map.keys())
        elif "segment_scores" in meta and isinstance(meta["segment_scores"], list):
            segment_texts = meta.get("segment_texts", []) or []
            segment_score_map = {}
        else:
            segment_score_map = {}
            segment_texts = []

    # 2) Run orchestrator (lazy via get_orchestrator)
    orch = get_orchestrator()
    if orch is None:
        logger.warning("Orchestrator not available; returning conservative sanitize fallback")
        fallback = {
            "verdict": "sanitize",
            "sanitized_prompt": "This prompt has been safely transformed to avoid harmful content.",
            "explanation": "Orchestrator unavailable; conservative sanitized fallback returned.",
            "confidence": max(0.0, min(1.0, float(max(simple_scores.values()) if simple_scores else 0.5))),
        }
        return jsonify(fallback), 200

    try:
        orchestrator_result = orch.run(
            prompt=prompt,
            scores=simple_scores,
            category=category or "",
            segment_score_map=segment_score_map,
            segment_texts=segment_texts,
        )
    except Exception as e:
        logger.exception("Orchestrator run failed: %s", e)
        fallback = {
            "verdict": "sanitize",
            "sanitized_prompt": "This prompt has been safely transformed to avoid harmful content.",
            "explanation": "Orchestrator failure; conservative sanitized fallback returned.",
            "confidence": max(0.0, min(1.0, float(max(simple_scores.values()) if simple_scores else 0.5))),
        }
        return jsonify(fallback), 500

    # 3) Map orchestrator output to agent JSON schema
    try:
        agent_json = map_orchestrator_to_agent_json(orchestrator_result, prompt)
        return jsonify(agent_json), 200
    except Exception as e:
        logger.exception("Mapping orchestrator result failed: %s", e)
        fallback = {
            "verdict": "sanitize",
            "sanitized_prompt": "This prompt has been safely transformed to avoid harmful content.",
            "explanation": "Result mapping failed; conservative sanitized fallback returned.",
            "confidence": max(0.0, min(1.0, float(max(simple_scores.values()) if simple_scores else 0.5))),
        }
        return jsonify(fallback), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info(f"Starting ML inference & agent service on {host}:{port} (models_dir={MODELS_DIR})")
    app.run(host=host, port=port, debug=False)
