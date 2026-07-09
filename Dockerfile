# =============================================================================
# 🐳 TUBBY APP · DOCKERFILE
# =============================================================================
# Builds the Flask backend.
#
# System packages included:
#   - tesseract-ocr   → required by pytesseract
#   - poppler-utils   → required by pdf2image
#   - libmysqlclient-dev / pkg-config → required by mysql-connector-python
# =============================================================================

FROM python:3.12-slim

# --- system dependencies ------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
        default-libmysqlclient-dev \
        pkg-config \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies (cached layer) --------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- application code --------------------------------------------------------
COPY . .

# --- runtime defaults (overridable via env / docker-compose) -----------------
ENV HOST=0.0.0.0
ENV PORT=5000

EXPOSE 5000

# Use python app.py so HOST/PORT env vars are respected.
# For production swap to: gunicorn -w 3 "app:app"
CMD ["python", "app.py"]
