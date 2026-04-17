"""
Recommendation Service — Port 5004

Ranks normalised products using a weighted score that combines item similarity,
price fit against user budget, brand preferences, and product rating.
Optionally applies hard filters (max price, min rating, platform whitelist).

Endpoints:
  POST /api/recommend  — rank products, return top-N with scores
  GET  /health         — service health check

CE/CZ4052 Cloud Computing — PA-as-a-Service
"""

import os
import sys

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import RECOMMENDATION_SERVICE_PORT, PREFERENCE_SERVICE_URL, TOP_RECOMMENDATIONS

app = Flask(__name__)
CORS(app)


# ── User preference fetch ─────────────────────────────────────────────────────

def _fetch_preferences(user_id: str) -> dict:
    """Call the User Preference Service via REST to get stored preferences."""
    try:
        resp = requests.get(
            f"{PREFERENCE_SERVICE_URL}/api/preferences/{user_id}",
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("data", {})
    except Exception:
        pass
    return {}


# ── Scoring ───────────────────────────────────────────────────────────────────

def _score(product: dict, prefs: dict) -> float:
    """
    Weighted recommendation score (0–1):
      40% — item similarity to query
      30% — price alignment with user budget
      20% — brand preference match
      10% — product rating
    """
    # Similarity
    sim_score = product.get("similarity", 0.5)

    # Price fit
    price = product.get("price_sgd", 0)
    avg_budget = prefs.get("avg_budget_sgd") or 0
    max_budget = prefs.get("max_budget_sgd") or 0

    if avg_budget > 0:
        ratio = price / avg_budget
        if ratio <= 1.2:
            price_score = max(0.3, 1.0 - abs(ratio - 1.0) * 0.5)
        else:
            price_score = max(0.1, 1.0 - (ratio - 1.2) * 0.3)
    elif max_budget > 0 and price > max_budget:
        price_score = 0.2
    else:
        price_score = 0.7  # no preference set

    # Brand match
    preferred_brands = [b.lower() for b in prefs.get("preferred_brands", [])]
    title_lower = (product.get("title") or "").lower()
    store_lower = (product.get("store_name") or "").lower()

    if preferred_brands:
        match = any(b in title_lower or b in store_lower for b in preferred_brands)
        brand_score = 1.0 if match else 0.5
    else:
        brand_score = 0.7

    # Rating
    rating = product.get("rating")
    rating_score = min(1.0, rating / 5.0) if rating and rating > 0 else 0.6

    final = (
        sim_score   * 0.40
        + price_score * 0.30
        + brand_score * 0.20
        + rating_score * 0.10
    )
    return round(final, 4)


def _label(score: float) -> str:
    if score >= 0.80:
        return "Best Match"
    if score >= 0.65:
        return "Great Value"
    if score >= 0.50:
        return "Similar Style"
    return "Alternative"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "recommendation", "port": RECOMMENDATION_SERVICE_PORT})


@app.route("/api/recommend", methods=["POST"])
def recommend():
    """
    Rank products using user preferences and return top-N recommendations.

    Request JSON:
      {
        "products":  [...normalised products from price-comparison service...],
        "user_id":   "shopper_01",
        "top_n":     10,
        "filters": {
          "max_price_sgd": 100,
          "min_rating":    3.5,
          "platforms":     ["Google Shopping"]
        }
      }

    Returns top-N ranked products enriched with recommendation_score and label.
    """
    body = request.get_json()
    if not body:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    products: list = body.get("products", [])
    user_id: str = body.get("user_id", "default")
    top_n: int = body.get("top_n", TOP_RECOMMENDATIONS)
    filters: dict = body.get("filters", {})

    if not products:
        return jsonify({"success": True, "data": [], "count": 0})

    # Fetch user preferences via REST call to preference service
    prefs = _fetch_preferences(user_id)

    # Hard filters
    max_price = filters.get("max_price_sgd") or prefs.get("max_budget_sgd")
    min_rating = filters.get("min_rating")
    platform_whitelist = filters.get("platforms", [])

    filtered = [
        p for p in products
        if (not max_price or p.get("price_sgd", 0) <= max_price)
        and (not min_rating or not p.get("rating") or p["rating"] >= min_rating)
        and (not platform_whitelist or p.get("platform") in platform_whitelist)
    ]

    # Fall back to unfiltered list if all products were removed
    if not filtered:
        filtered = products

    # Score and rank
    scored = sorted(
        [{**p, "recommendation_score": _score(p, prefs)} for p in filtered],
        key=lambda x: x["recommendation_score"],
        reverse=True,
    )

    top = scored[:top_n]
    for p in top:
        p["recommendation_label"] = _label(p["recommendation_score"])

    return jsonify({
        "success": True,
        "data": top,
        "count": len(top),
        "user_id": user_id,
        "preferences_applied": bool(prefs),
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("RECOMMENDATION_SERVICE_PORT", RECOMMENDATION_SERVICE_PORT))
    print(f"[Recommendation Service] Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
