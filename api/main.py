"""
API Gateway — Port 5000

Unified REST interface consumed by the Streamlit frontend and any external client.
Proxies preference/history calls to the User Preference Service and delegates
full searches to the ShoppingAgent orchestrator.

Endpoints:
  POST /api/search                — full PA workflow (image upload)
  GET  /api/history/<user_id>     — search history
  GET  /api/preferences/<user_id> — user preferences
  PUT  /api/preferences/<user_id> — update preferences
  POST /api/save-item             — save product to wishlist
  GET  /api/stats/<user_id>       — shopping analytics
  GET  /api/services/status       — microservice health dashboard
  GET  /health                    — gateway health check

CE/CZ4052 Cloud Computing — PA-as-a-Service
"""

import base64
import os
import sys

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import (
    API_GATEWAY_PORT,
    IMAGE_SERVICE_URL,
    SEARCH_SERVICE_URL,
    COMPARISON_SERVICE_URL,
    RECOMMENDATION_SERVICE_URL,
    PREFERENCE_SERVICE_URL,
    CART_SERVICE_URL,
)
from agents.shopping_agent import ShoppingAgent

app = Flask(__name__)
CORS(app)

_agent = ShoppingAgent()

_SERVICE_HEALTH_URLS = {
    "image-recognition": f"{IMAGE_SERVICE_URL}/health",
    "product-search":    f"{SEARCH_SERVICE_URL}/health",
    "price-comparison":  f"{COMPARISON_SERVICE_URL}/health",
    "recommendation":    f"{RECOMMENDATION_SERVICE_URL}/health",
    "user-preference":   f"{PREFERENCE_SERVICE_URL}/health",
    "cart":              f"{CART_SERVICE_URL}/health",
}


# ── Gateway health ────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "api-gateway", "port": API_GATEWAY_PORT})


@app.route("/api/services/status", methods=["GET"])
def services_status():
    """Ping every downstream service and report health."""
    statuses = {}
    for name, url in _SERVICE_HEALTH_URLS.items():
        try:
            r = requests.get(url, timeout=3)
            statuses[name] = {"status": "ok" if r.status_code == 200 else "error"}
        except Exception as exc:
            statuses[name] = {"status": "offline", "error": str(exc)}

    all_ok = all(s["status"] == "ok" for s in statuses.values())
    return jsonify({"all_healthy": all_ok, "services": statuses})


# ── Main search ───────────────────────────────────────────────────────────────

@app.route("/api/search", methods=["POST"])
def search():
    """
    Full shopping PA workflow triggered by an image upload.

    Accepts multipart/form-data:
      image           — product image file  (required)
      user_id         — user identifier     (default: 'default')
      keywords        — extra search terms  (optional)
      max_results     — int, default 10
      sort_by         — similarity | price | rating
      max_price_sgd   — float, optional budget cap

    Also accepts application/json with the same fields plus 'image_base64'.
    """
    user_id     = "default"
    keywords    = ""
    max_results = 10
    sort_by     = "similarity"
    max_price   = None
    image_base64 = None

    if request.content_type and "multipart" in request.content_type:
        if "image" not in request.files:
            return jsonify({"success": False, "error": "image file required"}), 400
        raw = request.files["image"].read()
        image_base64 = base64.b64encode(raw).decode("utf-8")
        user_id     = request.form.get("user_id", user_id)
        keywords    = request.form.get("keywords", keywords)
        max_results = int(request.form.get("max_results", max_results))
        sort_by     = request.form.get("sort_by", sort_by)
        max_price   = request.form.get("max_price_sgd", type=float)

    elif request.is_json:
        body        = request.get_json() or {}
        image_base64 = body.get("image_base64")
        user_id     = body.get("user_id", user_id)
        keywords    = body.get("keywords", keywords)
        max_results = body.get("max_results", max_results)
        sort_by     = body.get("sort_by", sort_by)
        max_price   = body.get("max_price_sgd")

    if not image_base64:
        return jsonify({"success": False, "error": "image_base64 or image file required"}), 400

    filters = {}
    if max_price:
        filters["max_price_sgd"] = max_price

    try:
        result = _agent.process_shopping_request(
            image_base64=image_base64,
            user_id=user_id,
            additional_keywords=keywords,
            max_results=max_results,
            sort_by=sort_by,
            filters=filters,
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify(result), (200 if result["success"] else 500)


# ── Preference & history proxies ──────────────────────────────────────────────

@app.route("/api/history/<user_id>", methods=["GET"])
def get_history(user_id: str):
    limit = request.args.get("limit", 20)
    try:
        r = requests.get(f"{PREFERENCE_SERVICE_URL}/api/history/{user_id}?limit={limit}", timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/preferences/<user_id>", methods=["GET"])
def get_preferences(user_id: str):
    try:
        r = requests.get(f"{PREFERENCE_SERVICE_URL}/api/preferences/{user_id}", timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/preferences/<user_id>", methods=["PUT"])
def update_preferences(user_id: str):
    try:
        r = requests.put(
            f"{PREFERENCE_SERVICE_URL}/api/preferences/{user_id}",
            json=request.get_json(),
            timeout=5,
        )
        return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/save-item", methods=["POST"])
def save_item():
    try:
        r = requests.post(
            f"{PREFERENCE_SERVICE_URL}/api/saved-items",
            json=request.get_json(),
            timeout=5,
        )
        return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/stats/<user_id>", methods=["GET"])
def get_stats(user_id: str):
    try:
        r = requests.get(f"{PREFERENCE_SERVICE_URL}/api/stats/{user_id}", timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ── Cart proxies ──────────────────────────────────────────────────────────────

@app.route("/api/cart/add", methods=["POST"])
def cart_add():
    try:
        r = requests.post(f"{CART_SERVICE_URL}/api/cart/add", json=request.get_json(), timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/cart/<user_id>", methods=["GET"])
def cart_get(user_id: str):
    try:
        r = requests.get(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/cart/item/<int:item_id>", methods=["DELETE"])
def cart_remove_item(item_id: int):
    try:
        r = requests.delete(f"{CART_SERVICE_URL}/api/cart/item/{item_id}", timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/cart/<user_id>", methods=["DELETE"])
def cart_clear(user_id: str):
    try:
        r = requests.delete(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("API_GATEWAY_PORT", API_GATEWAY_PORT))
    print(f"[API Gateway] Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
