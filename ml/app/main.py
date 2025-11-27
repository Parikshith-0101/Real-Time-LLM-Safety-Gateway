# ml/app/main.py
from flask import Flask, request, jsonify
from typing import Any, Dict
import model_loader
import os

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    ready = model_loader.load_artifacts()
    return jsonify({"status": "ok", "model_ready": bool(ready)}), 200

@app.route("/predict", methods=["POST"])
def predict():
    """
    Expected JSON body:
    {
      "prompt": "text",
      "segments": [ { "id": 1, "type": "text", "text": "..." }, ... ]  # optional
    }
    Response:
    { "score": 0.85, "labels": { "jailbreak": true } }
    """
    data = request.get_json(force=True, silent=True)
    if not data or "prompt" not in data:
        return jsonify({"error": "invalid_request", "message": "missing 'prompt' in body"}), 400

    prompt = data.get("prompt", "")
    segments = data.get("segments", None)

    try:
        score, labels = model_loader.predict_proba_and_labels(prompt, segments)
        # Ensure JSON-serializable simple types
        return jsonify({"score": float(score), "labels": labels}), 200
    except Exception as e:
        # In production, log exception with proper logger
        return jsonify({"error": "server_error", "message": str(e)}), 500

if __name__ == "__main__":
    # Development only: run Flask's built-in server
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
