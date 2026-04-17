# ── FitFinder AI — Dockerfile ──────────────────────────────────────────────────
# Single image shared by every microservice.
# docker-compose.yml selects the entry-point per service via `command:`.
#
# Build:  docker build -t fitfinder-ai .
# Run:    docker-compose up

FROM python:3.12-slim

WORKDIR /app

# Runtime libraries required by Pillow (JPEG/PNG decoding)
# libgl1-mesa-glx was removed in Debian Bookworm — not needed; Pillow uses libjpeg/libpng directly
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        libpng16-16 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer-cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project source
COPY . .

# Ensure database directory exists so SQLite can write to it
RUN mkdir -p database

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default entry-point — overridden per service in docker-compose.yml
CMD ["python", "api/main.py"]
