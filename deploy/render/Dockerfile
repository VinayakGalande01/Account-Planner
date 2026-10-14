# Render (free web service, 512 MB RAM, 0.1 CPU) image for the APEX backend.
# Lite mode: no PyTorch or ChromaDB. FastEmbed runs the same all-MiniLM-L6-v2 model on ONNX,
# and activity search uses in-memory vectors rebuilt at startup.
# Build context is backend/ (see render.yaml). The full image is still backend/Dockerfile.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FASTEMBED_CACHE_PATH=/app/.cache/fastembed \
    EMBEDDINGS_BACKEND=fastembed \
    DISABLE_CHROMA=true
WORKDIR /app

COPY requirements-lite.txt .
RUN pip install --no-cache-dir -r requirements-lite.txt

# Bake the embedding model into the image so a cold start downloads nothing.
COPY embeddings.py .
RUN python -c "from embeddings import get_embedding_model; assert get_embedding_model() is not None"

COPY . .

ENV PORT=10000
EXPOSE 10000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
