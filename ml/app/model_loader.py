# ml/app/model_loader.py
import os
import sys
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ml_model_loader")
logger.setLevel(logging.INFO)

_SG = None  # module-level singleton for SafetyGateway

class ModelNotLoadedError(RuntimeError):
    pass

def _ensure_import_path():
    """
    Ensure parent repo root is on sys.path so imports like ml.inference.safety_gateway and core.* work.
    This function searches upward from this file to find the repo root (which should contain 'core' and 'ml').
    """
    here = Path(__file__).resolve().parent  # ml/app
    p = here
    for _ in range(5):
        if (p / "core").exists() or (p / "ml").exists():
            root = p
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
                logger.info("Added project root to sys.path: %s", root)
            return
        p = p.parent
    # fallback: add parent of this folder
    fallback = here.parent
    if str(fallback) not in sys.path:
        sys.path.insert(0, str(fallback))
        logger.info("Added fallback path to sys.path: %s", fallback)

def init_safety_gateway(models_dir: Optional[str] = None, log_path: Optional[str] = None):
    """
    Initialize the SafetyGateway singleton. Safe to call multiple times.
    """
    global _SG
    if _SG is not None:
        return _SG

    _ensure_import_path()

    try:
        # local import after path fix
        from ml.inference.safety_gateway import SafetyGateway
    except Exception as e:
        logger.exception("Failed to import SafetyGateway: %s", e)
        raise

    models_dir = models_dir or os.environ.get("MODELS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models")))
    log_path = log_path or os.environ.get("SG_LOG_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs", "safety_gateway.log")))

    # instantiate SafetyGateway
    try:
        sg = SafetyGateway(models_dir=models_dir, log_path=log_path)
    except Exception as e:
        logger.exception("Failed to instantiate SafetyGateway: %s", e)
        raise

    _SG = sg
    logger.info("SafetyGateway initialized with models_dir=%s", models_dir)
    return _SG

def get_safety_gateway():
    """
    Return the already-initialized SafetyGateway instance, or raise ModelNotLoadedError.
    """
    global _SG
    if _SG is None:
        raise ModelNotLoadedError("SafetyGateway not initialized. Call init_safety_gateway() first.")
    return _SG
