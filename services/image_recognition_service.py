"""
Image Recognition Service — Port 5001

Analyzes uploaded product images using Claude claude-sonnet-4-6 Vision API
and returns structured clothing/product features.

Endpoints:
  POST /api/analyze  — accept image file or base64, return product description
  GET  /health       — service health check

Part of the FitFinder AI PA-as-a-Service microservices architecture.
CE/CZ4052 Cloud Computing — Topic 2: Personal Assistant-as-a-Service
"""

import base64
import io
import json
import os
import sys

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image

# Ensure project root is on the path so sibling packages resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import IMAGE_SERVICE_PORT, USE_MOCK_DATA
from utils.api_clients import ClaudeClient

app = Flask(__name__)
CORS(app)

_claude = ClaudeClient()

# ── Mock data for development / demo without API keys ─────────────────────────
MOCK_ANALYSIS = {
    "type": "shirt",
    "color": "Blue",
    "colors": ["Blue", "White"],
    "style": "casual",
    "brand": None,
    "description": "A casual blue and white striped cotton shirt with a relaxed fit",
    "search_terms": ["blue striped shirt", "casual cotton shirt", "men striped shirt"],
    "material": "cotton",
    "gender": "unisex",
    "confidence": 0.92,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resize_image(image_bytes: bytes, max_dimension: int = 1024) -> bytes:
    """Downscale image so the longest side ≤ max_dimension, keep aspect ratio."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > max_dimension:
        ratio = max_dimension / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _detect_media_type(filename: str) -> str:
    ext = (filename or "").lower().rsplit(".", 1)[-1]
    return {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "gif": "image/gif", "webp": "image/webp",
    }.get(ext, "image/jpeg")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "image-recognition", "port": IMAGE_SERVICE_PORT})


@app.route("/api/analyze", methods=["POST"])
def analyze_image():
    """
    Identify a clothing/product item from an uploaded image.

    Accepts (one of):
      • multipart/form-data  with field 'image' (file upload)
      • application/json     with field 'image_base64' (base64 string)
                             and optional 'media_type'

    Returns:
      {
        "success": true,
        "data": {
          "type": "shirt",
          "color": "Blue",
          "colors": ["Blue", "White"],
          "style": "casual",
          "brand": null,
          "description": "...",
          "search_terms": [...],
          "material": "cotton",
          "gender": "unisex",
          "confidence": 0.92
        }
      }
    """
    if USE_MOCK_DATA:
        return jsonify({"success": True, "data": MOCK_ANALYSIS})

    try:
        image_base64 = None
        media_type = "image/jpeg"

        if "image" in request.files:
            file = request.files["image"]
            raw = file.read()
            raw = _resize_image(raw)
            image_base64 = base64.b64encode(raw).decode("utf-8")
            media_type = _detect_media_type(file.filename or "")

        elif request.is_json:
            body = request.get_json()
            image_base64 = body.get("image_base64")
            media_type = body.get("media_type", "image/jpeg")

        if not image_base64:
            return jsonify({
                "success": False,
                "error": "No image provided. Send multipart 'image' file or JSON 'image_base64'.",
            }), 400

        analysis = _claude.analyze_clothing_image(image_base64, media_type)
        return jsonify({"success": True, "data": analysis})

    except json.JSONDecodeError as exc:
        return jsonify({"success": False, "error": f"Failed to parse AI response: {exc}"}), 500
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("IMAGE_SERVICE_PORT", IMAGE_SERVICE_PORT))
    print(f"[Image Recognition Service] Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
