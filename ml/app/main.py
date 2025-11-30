# ml/app/main.py
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# model_loader provides init_safety_gateway() and get_safety_gateway()
from model_loader import get_safety_gateway, init_safety_gateway, ModelNotLoadedError

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

# Initialize SafetyGateway eagerly (Flask 3 removed before_first_request)
try:
    init_safety_gateway(models_dir=MODELS_DIR, log_path=LOG_PATH)
    logger.info(f"SafetyGateway initialized models_dir={MODELS_DIR}")
except Exception as e:
    # Log but don't crash the app — get_safety_gateway() will raise later if not ready
    logger.exception("SafetyGateway init failed at startup: %s", e)


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
        # Models not loaded yet but the service is alive
        return jsonify({"status": "ok", "models_loaded": False, "models_dir": MODELS_DIR}), 200
    except Exception:
        logger.exception("Health check failed")
        return jsonify({"status": "error"}), 500


@app.post("/predict")
def predict():
    """
    POST /predict
    Body JSON: { "prompt": "some text" }
    Returns:
      {
        "simple_scores": {...},
        "meta": {...},
        "correlation_id": "<if provided>"
      }
    """
    body = request.get_json(force=True, silent=True)
    if not body or "prompt" not in body:
        return jsonify({"error": "missing_prompt"}), 400

    prompt = body.get("prompt") or ""
    if not isinstance(prompt, str):
        prompt = str(prompt)

    correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id")

    # Ensure SafetyGateway is available (try lazy init as fallback)
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

    # Run prediction
    try:
        simple_scores, meta = sg.predict(prompt)
        resp = {"simple_scores": simple_scores, "meta": meta}
        if correlation_id:
            resp["correlation_id"] = correlation_id
        return jsonify(resp), 200
    except Exception as e:
        logger.exception("Prediction failed: %s", e)
        return jsonify({"error": "prediction_failed", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info(f"Starting ML inference service on {host}:{port} (models_dir={MODELS_DIR})")
    app.run(host=host, port=port, debug=False)
