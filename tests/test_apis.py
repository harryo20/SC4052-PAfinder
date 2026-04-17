"""
test_apis.py — Integration tests for FitFinder AI microservices.

These tests hit the running services via HTTP (exactly how they would be
called in production), verifying each REST endpoint independently.

Prerequisites:
  python start_all.py --mock   # starts all services with mock data

Run:
  pytest tests/ -v
  pytest tests/ -v -k "health"   # only health checks
"""

import io
import pytest
import requests
from PIL import Image

BASE = {
    "image":      "http://localhost:5001",
    "search":     "http://localhost:5002",
    "comparison": "http://localhost:5003",
    "recommend":  "http://localhost:5004",
    "preference": "http://localhost:5005",
    "gateway":    "http://localhost:5000",
}

TEST_USER = "pytest_user_001"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _blue_jpeg() -> bytes:
    """Create a tiny JPEG (blue rectangle) for upload tests."""
    img = Image.new("RGB", (80, 80), color=(70, 130, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ── Health checks ─────────────────────────────────────────────────────────────

class TestHealth:
    @pytest.mark.parametrize("service", list(BASE.keys()))
    def test_health(self, service):
        r = requests.get(f"{BASE[service]}/health", timeout=5)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ── Image Recognition Service (5001) ─────────────────────────────────────────

class TestImageRecognition:
    def test_analyze_image_file(self):
        """POST multipart image → structured product description."""
        r = requests.post(
            f"{BASE['image']}/api/analyze",
            files={"image": ("test.jpg", io.BytesIO(_blue_jpeg()), "image/jpeg")},
            timeout=35,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        item = data["data"]
        # Required fields
        for field in ("type", "color", "style", "description", "search_terms", "confidence"):
            assert field in item, f"Missing field: {field}"

    def test_analyze_no_image_returns_400(self):
        r = requests.post(f"{BASE['image']}/api/analyze", json={}, timeout=5)
        assert r.status_code == 400


# ── Product Search Service (5002) ─────────────────────────────────────────────

class TestProductSearch:
    def test_search_returns_platforms(self):
        r = requests.post(
            f"{BASE['search']}/api/search",
            json={"description": "blue casual shirt", "max_results": 5},
            timeout=35,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert isinstance(data["data"], dict)        # keyed by platform name
        assert data["total"] >= 0

    def test_search_missing_description_returns_400(self):
        r = requests.post(f"{BASE['search']}/api/search", json={}, timeout=5)
        assert r.status_code == 400


# ── Price Comparison Service (5003) ──────────────────────────────────────────

_RAW = {
    "google_shopping": [
        {"platform": "google_shopping", "title": "Blue Shirt Uniqlo",
         "source": "Uniqlo SG", "extracted_price": 29.90, "currency": "SGD",
         "link": "https://example.com/1", "thumbnail": "", "rating": 4.5, "reviews": 100},
        {"platform": "google_shopping", "title": "Cheap Striped Shirt",
         "source": "H&M", "extracted_price": 14.99, "currency": "USD",
         "link": "https://example.com/2", "thumbnail": "", "rating": 3.8, "reviews": 55},
    ]
}


class TestPriceComparison:
    def test_compare_normalises_to_sgd(self):
        r = requests.post(
            f"{BASE['comparison']}/api/compare",
            json={"raw_results": _RAW, "query_terms": ["blue", "shirt"], "sort_by": "similarity"},
            timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        for p in data["data"]:
            assert "price_sgd" in p
            assert p["price_sgd"] > 0

    def test_compare_sort_by_price(self):
        r = requests.post(
            f"{BASE['comparison']}/api/compare",
            json={"raw_results": _RAW, "query_terms": ["shirt"], "sort_by": "price"},
            timeout=15,
        )
        prices = [p["price_sgd"] for p in r.json()["data"]]
        assert prices == sorted(prices), "Products not sorted ascending by price"

    def test_compare_stats_present(self):
        r = requests.post(
            f"{BASE['comparison']}/api/compare",
            json={"raw_results": _RAW, "query_terms": ["shirt"], "sort_by": "similarity"},
            timeout=15,
        )
        stats = r.json()["stats"]
        assert stats["total_products"] > 0
        assert "min_price_sgd" in stats and "avg_price_sgd" in stats


# ── Recommendation Service (5004) ────────────────────────────────────────────

_PRODUCTS = [
    {"id": "p1", "title": "Blue Shirt Uniqlo", "price_sgd": 39.90, "store_name": "Uniqlo",
     "platform": "Google Shopping", "image_url": "", "purchase_url": "https://example.com/1",
     "similarity": 0.88, "rating": 4.5, "review_count": 200, "match_type": "similar",
     "is_singapore": True, "shipping": "Free"},
    {"id": "p2", "title": "Cheap Cotton Shirt", "price_sgd": 12.90, "store_name": "H&M",
     "platform": "Google Shopping", "image_url": "", "purchase_url": "https://example.com/2",
     "similarity": 0.65, "rating": 3.6, "review_count": 40, "match_type": "cheaper",
     "is_singapore": False, "shipping": None},
]


class TestRecommendation:
    def test_recommend_returns_scores(self):
        r = requests.post(
            f"{BASE['recommend']}/api/recommend",
            json={"products": _PRODUCTS, "user_id": TEST_USER, "top_n": 5},
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        for p in data["data"]:
            assert "recommendation_score" in p
            assert 0.0 <= p["recommendation_score"] <= 1.0
            assert "recommendation_label" in p

    def test_recommend_price_filter(self):
        r = requests.post(
            f"{BASE['recommend']}/api/recommend",
            json={"products": _PRODUCTS, "user_id": TEST_USER, "top_n": 10,
                  "filters": {"max_price_sgd": 20.0}},
            timeout=10,
        )
        for p in r.json()["data"]:
            assert p["price_sgd"] <= 20.0

    def test_recommend_top_n_respected(self):
        r = requests.post(
            f"{BASE['recommend']}/api/recommend",
            json={"products": _PRODUCTS, "user_id": TEST_USER, "top_n": 1},
            timeout=10,
        )
        assert len(r.json()["data"]) <= 1


# ── User Preference Service (5005) ───────────────────────────────────────────

class TestUserPreference:
    def test_get_prefs_new_user(self):
        r = requests.get(f"{BASE['preference']}/api/preferences/brand_new_user_9999", timeout=5)
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["preferred_brands"] == []
        assert d["preferred_styles"] == []

    def test_set_and_get_prefs(self):
        requests.put(
            f"{BASE['preference']}/api/preferences/{TEST_USER}",
            json={"max_budget_sgd": 80.0, "preferred_brands": ["Nike", "Adidas"],
                  "preferred_styles": ["casual", "sporty"]},
            timeout=5,
        )
        r = requests.get(f"{BASE['preference']}/api/preferences/{TEST_USER}", timeout=5)
        d = r.json()["data"]
        assert d["max_budget_sgd"] == 80.0
        assert "Nike" in d["preferred_brands"]

    def test_save_and_retrieve_history(self):
        requests.post(
            f"{BASE['preference']}/api/history",
            json={"user_id": TEST_USER, "query": "blue casual shirt",
                  "item_type": "shirt", "item_color": "blue",
                  "item_style": "casual", "result_count": 5,
                  "top_result_price_sgd": 34.90},
            timeout=5,
        )
        r = requests.get(f"{BASE['preference']}/api/history/{TEST_USER}", timeout=5)
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_stats_endpoint(self):
        r = requests.get(f"{BASE['preference']}/api/stats/{TEST_USER}", timeout=5)
        assert r.status_code == 200
        d = r.json()["data"]
        assert "total_searches" in d


# ── API Gateway (5000) ────────────────────────────────────────────────────────

class TestAPIGateway:
    def test_services_status(self):
        r = requests.get(f"{BASE['gateway']}/api/services/status", timeout=10)
        assert r.status_code == 200
        assert "services" in r.json()

    def test_gateway_proxies_preferences(self):
        r = requests.get(f"{BASE['gateway']}/api/preferences/{TEST_USER}", timeout=5)
        assert r.status_code == 200

    def test_gateway_proxies_history(self):
        r = requests.get(f"{BASE['gateway']}/api/history/{TEST_USER}", timeout=5)
        assert r.status_code == 200

    def test_search_no_image_returns_400(self):
        r = requests.post(f"{BASE['gateway']}/api/search", json={}, timeout=5)
        assert r.status_code == 400
