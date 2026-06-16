# Backend image for Hugging Face Spaces (Docker SDK).
# Serves the FastAPI app (backend.main:app) on port 7860 — the port HF Spaces
# expects (see app_port in README.md frontmatter).
FROM python:3.12-slim

# HF Spaces runs the container as a non-root user (uid 1000).
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN chown -R user:user /app
USER user

# Install Python deps first for better layer caching.
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Backend source only (frontend is deployed separately on Netlify).
COPY --chown=user:user backend ./backend

EXPOSE 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
