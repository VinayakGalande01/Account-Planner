"""
EMBEDDING MODEL LOADER (embeddings.py)
One place that loads the all-MiniLM-L6-v2 sentence embedding model used by the
semantic router (intent_classifier.py) and activity search (vector_store.py).

EMBEDDINGS_BACKEND picks the runtime:
  - "sentence-transformers" (default): PyTorch, full mode.
  - "fastembed": ONNX, no PyTorch; used on small hosts (Render free, 512 MB).
  - "none": no embeddings; callers fall back to keyword rules.
Both real backends run the same model, so similarity scores and thresholds match.
"""

import os
import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"
BACKEND = os.getenv("EMBEDDINGS_BACKEND", "sentence-transformers").lower()

_model = None
_load_failed = False


class _FastEmbedModel:
    """Gives FastEmbed the same encode() shape as SentenceTransformer."""

    def __init__(self):
        from fastembed import TextEmbedding
        self._model = TextEmbedding(
            model_name=f"sentence-transformers/{MODEL_NAME}",
            cache_dir=os.getenv("FASTEMBED_CACHE_PATH"),
        )

    def encode(self, texts):
        if isinstance(texts, str):
            return np.array(next(iter(self._model.embed([texts]))))
        return np.array(list(self._model.embed(list(texts))))


def get_embedding_model():
    """Returns the shared model, or None when embeddings are off or unavailable."""
    global _model, _load_failed
    if _model is not None or _load_failed or BACKEND == "none":
        return _model
    try:
        if BACKEND == "fastembed":
            _model = _FastEmbedModel()
        else:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(MODEL_NAME, local_files_only=True)
        print(f"[Embeddings] Loaded {MODEL_NAME} with {BACKEND}.")
    except Exception as e:
        _load_failed = True
        print(f"Warning: embedding model unavailable ({BACKEND}): {e}. Using keyword fallback.")
    return _model
