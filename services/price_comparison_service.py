
import os
import re
import sys
from typing import Optional

from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import COMPARISON_SERVICE_PORT, USE_MOCK_DATA
from utils.api_clients import ExchangeRateClient

app = Flask(__name__)
CORS(app)

_fx = ExchangeRateClient()

_SG_PLATFORMS ={"shopee", "lazada", "qoo10", "courts", "harvey norman", "challenger", "zalora", "uniqlo sg"}


def _extract_price(value) -> tuple[float, str]:
    """
    Return (amount_float, currency_code) from a raw price value.
    Handles numeric values and formatted strings like "$29.90", "S$29.90", "29.90 USD".
    """
    if isinstance(value, (int, float)):
        return float(value), "USD"

    s = str(value).strip()
    if not s:
        return 0.0, "USD"

    currency = "USD"
    if "S$" in s or "SGD" in s:
        currency = "SGD"
    elif "£" in s or "GBP" in s:
        currency = "GBP"
    elif "€" in s or "EUR" in s:
        currency = "EUR"
    elif "¥" in s or "CNY" in s or "RMB" in s:
        currency = "CNY"
    elif "RM" in s or "MYR" in s:
        currency = "MYR"
    elif "A$" in s or "AUD" in s:
        currency = "AUD"
    elif "HK$" in s or "HKD" in s:
        currency = "HKD"

    nums = re.findall(r"[\d,]+\.?\d*", s)
    if nums:
        return float(nums[0].replace(",", "")), currency
    return 0.0, "USD"


def _similarity(product: dict, query_terms: list, position: int) -> float:
    """
    Score 0-1 based on query-term matches in title + position in result list.
    Promoted slightly for known Singapore retailers.
    """
    title = (product.get("title") or "").lower()
    source = (product.get("source") or "").lower()

    if not title:
        return 0.5

    hit_count = sum(1 for t in query_terms if t.lower() in title)
    term_score = min(0.9, 0.5 + (hit_count / max(len(query_terms), 1)) * 0.4)
    position_score = max(0.5, 1.0 - position * 0.02)
    score = (term_score + position_score) / 2.0

    if any(sg in source for sg in _SG_PLATFORMS):
        score = min(1.0, score + 0.05)

    return round(score, 3)


_PLATFORM_LABELS = {
    "google_shopping":           "Google Shopping",
    "google_shopping_affordable": "Google Shopping",
    "rapidapi":                  "Online Store",
    "ebay":                      "eBay",
}


def _normalise(raw: dict, query_terms: list, index: int) -> Optional[dict]:
    """Map a raw platform result to the canonical product schema."""
    price_raw = raw.get("extracted_price") or raw.get("price", 0)
    amount, currency = _extract_price(price_raw)
    if amount <= 0:
        return None

    price_sgd = _fx.convert_to_sgd(amount, currency)

    platform_key = raw.get("platform", "unknown")
    platform_label = _PLATFORM_LABELS.get(platform_key, platform_key.replace("_", " ").title())

    rating = raw.get("rating")
    # rating sometimes arrives as "4.5/5" string
    if isinstance(rating, str):
        try:
            rating = float(rating.replace("/5", "").strip())
        except ValueError:
            rating = None

    sim = _similarity(raw, query_terms, index)
    source = raw.get("source", "Online Store")

    return {
        "id": f"{platform_key}_{index}_{abs(hash(raw.get('link', '') + raw.get('title', '')))}",
        "title": raw.get("title", "Unknown Product"),
        "price_sgd": price_sgd,
        "price_original": amount,
        "currency_original": currency,
        "store_name": source,
        "platform": platform_label,
        "image_url": raw.get("thumbnail", ""),
        "purchase_url": raw.get("link", ""),
        "similarity": sim,
        "rating": rating,
        "review_count": raw.get("reviews"),
        "shipping": raw.get("delivery") or raw.get("shipping"),
        "match_type": "exact" if sim >= 0.85 else "similar" if sim >= 0.65 else "cheaper",
        "is_singapore": any(sg in source.lower() for sg in _SG_PLATFORMS),
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "price-comparison", "port": COMPARISON_SERVICE_PORT})


@app.route("/api/compare", methods=["POST"])
def compare_prices():
    """
    Normalise raw multi-platform search results into a common SGD-priced schema.

    Request JSON:
      {
        "raw_results":  { "platform_name": [...raw items...], ... },
        "query_terms":  ["blue", "shirt", "casual"],
        "sort_by":      "similarity" | "price" | "rating"  (default: similarity)
      }

    Returns:
      {
        "success": true,
        "data": [ ...normalised products... ],
        "stats": { total_products, min/max/avg price_sgd, platforms }
      }
    """
    body = request.get_json()
    if not body:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    raw_results: dict = body.get("raw_results", {})
    query_terms: list = body.get("query_terms", [])
    sort_by: str = body.get("sort_by", "similarity")

    normalised: list = []
    global_idx = 0

    for platform, items in raw_results.items():
        for item in items:
            product = _normalise(item, query_terms, global_idx)
            if product:
                normalised.append(product)
            global_idx += 1

    seen: set = set()
    unique: list = []
    for p in normalised:
        key = p["title"].lower()[:50]
        if key not in seen:
            seen.add(key)
            unique.append(p)

    # Sort
    if sort_by == "price":
        unique.sort(key=lambda x: x["price_sgd"])
    elif sort_by == "rating":
        unique.sort(key=lambda x: (x["rating"] or 0), reverse=True)
    else:
        unique.sort(key=lambda x: x["similarity"], reverse=True)

    prices = [p["price_sgd"] for p in unique if p["price_sgd"] > 0]
    stats = {
        "total_products": len(unique),
        "min_price_sgd": round(min(prices), 2) if prices else 0,
        "max_price_sgd": round(max(prices), 2) if prices else 0,
        "avg_price_sgd": round(sum(prices) / len(prices), 2) if prices else 0,
        "platforms": list({p["platform"] for p in unique}),
    }

    return jsonify({"success": True, "data": unique, "stats": stats})


if __name__ == "__main__":
    port = int(os.getenv("COMPARISON_SERVICE_PORT", COMPARISON_SERVICE_PORT))
    print(f"[Price Comparison Service] Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
