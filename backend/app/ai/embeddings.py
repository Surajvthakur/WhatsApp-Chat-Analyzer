import urllib.request
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

_model_verified = False

def ensure_model_exists() -> bool:
    """
    Checks if the configured Ollama embedding model exists, and pulls it if it doesn't.
    Can be run synchronously (during request) or in a background thread on startup.
    """
    global _model_verified
    if _model_verified:
        return True
        
    model_name = settings.embedding_model
    ollama_url = settings.ollama_url
    
    # 1. Check if model is already pulled
    try:
        req = urllib.request.Request(
            f"{ollama_url}/api/show",
            data=json.dumps({"name": model_name}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                logger.info(f"Ollama model '{model_name}' is already available.")
                _model_verified = True
                return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.info(f"Ollama model '{model_name}' not found. Attempting to pull...")
        else:
            logger.warning(f"Ollama model check failed with status code {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.warning(f"Could not connect to Ollama at {ollama_url} to check model: {e}")
        # We will try to pull anyway, or just return False and let the call attempt fail gracefully.
        return False
        
    # 2. Pull the model if not found
    try:
        logger.info(f"Pulling model '{model_name}' from Ollama registry. This might take a few moments...")
        req = urllib.request.Request(
            f"{ollama_url}/api/pull",
            data=json.dumps({"name": model_name, "model": model_name, "stream": False}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=300) as response:  # 5 minutes timeout for pulling
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("status") == "success":
                logger.info(f"Successfully pulled '{model_name}' model.")
                _model_verified = True
                return True
            else:
                logger.warning(f"Ollama pull returned unexpected response status: {res_data}")
    except Exception as e:
        logger.error(f"Failed to pull model '{model_name}' from Ollama: {e}")
        
    return False

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings for a list of text strings by offloading to the Ollama service.
    """
    if not texts:
        return []
        
    ensure_model_exists()
    
    model_name = settings.embedding_model
    ollama_url = settings.ollama_url
    
    try:
        req = urllib.request.Request(
            f"{ollama_url}/api/embed",
            data=json.dumps({"model": model_name, "input": texts}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if "embeddings" in res_data:
                return res_data["embeddings"]
            else:
                raise ValueError("Response JSON did not contain 'embeddings' key.")
    except Exception as e:
        logger.error(f"Ollama /api/embed failed: {e}")
        # Return fallback zero vectors of correct dimension to keep app functional
        return [[0.0] * settings.embedding_dimension for _ in texts]
