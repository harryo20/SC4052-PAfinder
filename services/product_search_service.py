"""
Product Search Service — Port 5002

Queries multiple e-commerce platforms in parallel and returns raw results.
Uses SerpAPI (Google Shopping) as the primary source and RapidAPI as secondary.

Endpoints:
  POST /api/search  — search across platforms, return aggregated raw results
  GET  /health      — service health check

CE/CZ4052 Cloud Computing — PA-as-a-Service
"""

import concurrent.futures
import os
import sys

from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import SEARCH_SERVICE_PORT, USE_MOCK_DATA, MAX_SEARCH_RESULTS
from utils.api_clients import SerpAPIClient, RapidAPIShoppingClient

app = Flask(__name__)
CORS(app)

_serp = SerpAPIClient()
_rapid = RapidAPIShoppingClient()

# ── Mock data ─────────────────────────────────────────────────────────────────
MOCK_RESULTS = {
    "google_shopping": [
        {
            "platform": "google_shopping",
            "title": "Blue Striped Cotton Casual Shirt – Men's",
            "source": "Uniqlo SG",
            "price": "S$29.90",
            "extracted_price": 29.90,
            "currency": "SGD",
            "link": "https://uniqlo.com/sg/example",
            "thumbnail": "https://via.placeholder.com/150",
            "rating": 4.5,
            "reviews": 234,
            "delivery": "Free shipping over S$50",
        },
        {
            "platform": "google_shopping",
            "title": "Men's Casual Striped Shirt Blue/White",
            "source": "H&M",
            "price": "S$24.99",
            "extracted_price": 24.99,
            "currency": "SGD",
            "link": "https://hm.com/sg/example",
            "thumbnail": "https://via.placeholder.com/150",
            "rating": 4.1,
            "reviews": 89,
            "delivery": "S$4.99 shipping",
        },
        {
            "platform": "google_shopping",
            "title": "Striped Button-Down Shirt Classic Fit",
            "source": "Zalora SG",
            "price": "S$39.90",
            "extracted_price": 39.90,
            "currency": "SGD",
            "link": "https://zalora.com.sg/example",
            "thumbnail": "https://via.placeholder.com/150",
            "rating": 4.3,
            "reviews": 112,
            "delivery": "Free returns",
        },
    ],
    "google_shopping_affordable": [
        {
            "platform": "google_shopping_affordable",
            "title": "Affordable Striped Shirt Blue Cotton",
            "source": "Shopee SG",
            "price": "S$12.90",
            "extracted_price": 12.90,
            "currency": "SGD",
            "link": "https://shopee.sg/example",
            "thumbnail": "https://via.placeholder.com/150",
            "rating": 3.9,
            "reviews": 560,
            "delivery": "Free shipping",
        },
    ],
    "rapidapi": [
        {
            "platform": "rapidapi",
            "title": "Striped Oxford Shirt – Casual Style",
            "source": "ASOS",
            "price": "S$49.90",
            "extracted_price": 49.90,
            "currency": "SGD",
            "link": "https://asos.com/example",
            "thumbnail": "https://via.placeholder.com/150",
            "rating": 4.3,
            "reviews": 156,
        },
    ],
}


# ── Per-platform search helpers ───────────────────────────────────────────────

def _search_google_shopping(query: str, num: int) -> list:
    """Google Shopping via SerpAPI, localised for Singapore."""
    try:
        results = _serp.search_google_shopping(f"{query} Singapore", country="sg", num=num)
        return [{"platform": "google_shopping", **r} for r in results]
    except Exception as exc:
        print(f"[ProductSearch] Google Shopping error: {exc}")
        return []


def _search_google_shopping_affordable(query: str, num: int) -> list:
    """Google Shopping with 'affordable' prefix for cheaper alternatives."""
    try:
        results = _serp.search_google_shopping(f"affordable {query}", country="sg", num=num)
        return [{"platform": "google_shopping_affordable", **r} for r in results]
    except Exception as exc:
        print(f"[ProductSearch] Google Shopping affordable error: {exc}")
        return []


def _search_rapidapi(query: str, num: int) -> list:
    """RapidAPI Real-Time Product Search."""
    try:
        raw = _rapid.search_products(query, country="sg", num=num)
        normalized = []
        for r in raw:
            normalized.append({
                "platform": "rapidapi",
                "title": r.get("product_title") or r.get("title", ""),
                "source": r.get("store_name") or r.get("source", "Online Store"),
                "price": r.get("product_price") or r.get("price", ""),
                "extracted_price": _safe_float(r.get("product_price") or r.get("price", 0)),
                "currency": r.get("currency", "USD"),
                "link": r.get("product_page_url") or r.get("link", ""),
                "thumbnail": r.get("product_photo") or r.get("thumbnail", ""),
                "rating": r.get("product_star_rating") or r.get("rating"),
                "reviews": r.get("product_num_ratings") or r.get("reviews"),
            })
        return normalized
    except Exception as exc:
        print(f"[ProductSearch] RapidAPI error: {exc}")
        return []


def _safe_float(value) -> float:
    try:
        return float(str(value).replace("S$", "").replace("$", "").replace(",", "").strip() or 0)
    except (ValueError, TypeError):
        return 0.0


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "product-search", "port": SEARCH_SERVICE_PORT})


@app.route("/api/search", methods=["POST"])
def search_products():
    """
    Search multiple e-commerce platforms for a described product.

    Request JSON:
      {
        "description":          "blue striped casual shirt",
        "search_terms":         ["blue shirt", "striped shirt"],
        "additional_keywords":  "slim fit",
        "max_results":          20
      }

    Returns aggregated raw results keyed by platform.
    """
    if USE_MOCK_DATA:
        total = sum(len(v) for v in MOCK_RESULTS.values())
        return jsonify({"success": True, "data": MOCK_RESULTS, "total": total, "query": "mock"})

    body = request.get_json()
    if not body:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    description = body.get("description", "")
    additional = body.get("additional_keywords", "")
    max_results = body.get("max_results", MAX_SEARCH_RESULTS)

    query = " ".join(filter(None, [description, additional])).strip()
    if not query:
        return jsonify({"success": False, "error": "'description' is required"}), 400

    half = max(5, max_results // 2)

    # Search all platforms in parallel — true concurrent HTTP calls
    all_results: dict = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            "google_shopping":           pool.submit(_search_google_shopping, query, max_results),
            "google_shopping_affordable": pool.submit(_search_google_shopping_affordable, query, half),
            "rapidapi":                  pool.submit(_search_rapidapi, query, half),
        }
        for platform, future in futures.items():
            try:
                all_results[platform] = future.result(timeout=28)
            except Exception as exc:
                print(f"[ProductSearch] Timeout/error for {platform}: {exc}")
                all_results[platform] = []

    total = sum(len(v) for v in all_results.values())
    return jsonify({"success": True, "data": all_results, "total": total, "query": query})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("SEARCH_SERVICE_PORT", SEARCH_SERVICE_PORT))
    print(f"[Product Search Service] Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
