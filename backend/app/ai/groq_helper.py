import logging
from groq import Groq
from app.config import settings

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "llama-3.2-3b-preview",
]


def call_groq_chat_completion(client: Groq, messages: list, **kwargs):
    """
    Executes a Groq chat completion. If the requested model is decommissioned
    or 404 not found, automatically falls back to alternative active models.
    """
    models_to_try = []
    if settings.groq_model:
        models_to_try.append(settings.groq_model)

    for m in FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model_id in models_to_try:
        try:
            logger.info(f"Calling Groq completion with model: {model_id}")
            call_kwargs = dict(kwargs)
            call_kwargs["model"] = model_id
            call_kwargs["messages"] = messages
            return client.chat.completions.create(**call_kwargs)
        except Exception as e:
            err_str = str(e).lower()
            if (
                "model_not_found" in err_str
                or "does not exist" in err_str
                or "decommissioned" in err_str
                or "404" in err_str
            ):
                logger.warning(f"Groq model '{model_id}' unavailable: {e}. Trying fallback...")
                last_error = e
                continue
            raise e

    if last_error:
        raise last_error
    raise RuntimeError("All Groq candidate models failed.")
