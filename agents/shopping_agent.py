"""
Shopping Agent — Main AI orchestrator for FitFinder PA-as-a-Service.

Implements the full shopping workflow by making sequential REST API calls
to each independent microservice.  No direct Python imports of service code —
every step communicates via HTTP, demonstrating true microservices architecture.

Workflow:
  1. POST http://localhost:5001/api/analyze       — Image Recognition Service
  2. POST http://localhost:5002/api/search        — Product Search Service
  3. POST http://localhost:5003/api/compare       — Price Comparison Service
  4. POST http://localhost:5004/api/recommend     — Recommendation Service
  5. POST http://localhost:5005/api/history       — User Preference Service

CE/CZ4052 Cloud Computing — Topic 2: Personal Assistant-as-a-Service
"""

import base64
import os
import sys
from typing import Optional

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import (
    IMAGE_SERVICE_URL,
    SEARCH_SERVICE_URL,
    COMPARISON_SERVICE_URL,
    RECOMMENDATION_SERVICE_URL,
    PREFERENCE_SERVICE_URL,
)


class ShoppingAgent:
    """
    Stateless agent that orchestrates the PA workflow via REST calls.
    Instantiate once and call process_shopping_request() for each search.
    """

    def __init__(self):
        self._urls = {
            "image":      IMAGE_SERVICE_URL,
            "search":     SEARCH_SERVICE_URL,
            "comparison": COMPARISON_SERVICE_URL,
            "recommend":  RECOMMENDATION_SERVICE_URL,
            "preference": PREFERENCE_SERVICE_URL,
        }

    # ── Public entry point ────────────────────────────────────────────────────

    def process_shopping_request(
        self,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        user_id: str = "default",
        additional_keywords: str = "",
        max_results: int = 10,
        sort_by: str = "similarity",
        filters: Optional[dict] = None,
    ) -> dict:
        """
        End-to-end shopping PA workflow.

        Provide either image_path (local file) or image_base64 (pre-encoded).

        Returns:
          {
            "success":  bool,
            "user_id":  str,
            "analysis": { type, color, style, brand, description, ... },
            "products": [ ...top recommendations with scores... ],
            "stats":    { min/max/avg price, platform list, ... },
            "error":    str | None
          }
        """
        result: dict = {
            "success": False,
            "user_id": user_id,
            "analysis": None,
            "products": [],
            "stats": {},
            "error": None,
        }

        # ── Step 1: Image Recognition ─────────────────────────────────────────
        self._log("Step 1/5 -> Image Recognition Service (port 5001)")
        analysis, img_error = self._call_image_recognition(image_path, image_base64)
        if not analysis:
            result["error"] = img_error or "Image recognition failed. Is the service running?"
            return result
        result["analysis"] = analysis
        self._log(f"  Identified: {analysis.get('type')} / {analysis.get('color')} / {analysis.get('style')}")

        # ── Step 2: Product Search ────────────────────────────────────────────
        self._log("Step 2/5 -> Product Search Service (port 5002)")
        description = analysis.get("description") or (
            f"{analysis.get('color', '')} {analysis.get('type', '')}".strip()
        )
        raw_results = self._call_product_search(
            description=description,
            search_terms=analysis.get("search_terms", []),
            additional_keywords=additional_keywords,
            max_results=max_results * 2,
        )
        if not raw_results:
            result["error"] = "No products found across platforms."
            return result
        total_raw = sum(len(v) for v in raw_results.values())
        self._log(f"  Found {total_raw} raw results across {len(raw_results)} platforms")

        # ── Step 3: Price Comparison ──────────────────────────────────────────
        self._log("Step 3/5 -> Price Comparison Service (port 5003)")
        query_terms = analysis.get("search_terms", []) + [
            analysis.get("type", ""), analysis.get("color", "")
        ]
        compared = self._call_price_comparison(raw_results, query_terms, sort_by)
        if not compared:
            result["error"] = "Price comparison service failed."
            return result
        result["stats"] = compared.get("stats", {})
        self._log(f"  Normalised {len(compared.get('data', []))} products -> SGD")

        # ── Step 4: Recommendation ────────────────────────────────────────────
        self._log("Step 4/5 -> Recommendation Service (port 5004)")
        recommendations = self._call_recommendation(
            products=compared.get("data", []),
            user_id=user_id,
            top_n=max_results,
            filters=filters or {},
        )
        result["products"] = recommendations
        self._log(f"  Selected top {len(recommendations)} recommendations")

        # ── Step 5: Save to history ───────────────────────────────────────────
        self._log("Step 5/5 -> User Preference Service (port 5005)")
        top = recommendations[0] if recommendations else {}
        self._save_history(
            user_id=user_id,
            query=description,
            analysis=analysis,
            result_count=len(recommendations),
            top_product=top,
        )

        result["success"] = True
        return result

    # ── Private: REST API calls ───────────────────────────────────────────────

    def _call_image_recognition(
        self, image_path: Optional[str], image_base64: Optional[str]
    ) -> tuple:
        """REST POST -> /api/analyze on the Image Recognition Service.

        Returns (analysis_dict, error_str).  One will always be None.
        """
        try:
            url = f"{self._urls['image']}/api/analyze"
            if image_path:
                with open(image_path, "rb") as fh:
                    resp = requests.post(
                        url,
                        files={"image": (os.path.basename(image_path), fh, "image/jpeg")},
                        timeout=35,
                    )
            elif image_base64:
                resp = requests.post(url, json={"image_base64": image_base64}, timeout=35)
            else:
                return None, "No image provided"

            try:
                data = resp.json()
            except Exception:
                resp.raise_for_status()
                return None, f"Image service returned status {resp.status_code}"

            if data.get("success"):
                return data.get("data"), None
            error = data.get("error", f"Image service error (HTTP {resp.status_code})")
            self._log(f"  [ERROR] Image recognition: {error}")
            return None, error
        except Exception as exc:
            self._log(f"  [ERROR] Image recognition: {exc}")
            return None, str(exc)

    def _call_product_search(
        self,
        description: str,
        search_terms: list,
        additional_keywords: str,
        max_results: int,
    ) -> Optional[dict]:
        """REST POST → /api/search on the Product Search Service."""
        try:
            resp = requests.post(
                f"{self._urls['search']}/api/search",
                json={
                    "description": description,
                    "search_terms": search_terms,
                    "additional_keywords": additional_keywords,
                    "max_results": max_results,
                },
                timeout=35,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data") if data.get("success") else None
        except Exception as exc:
            self._log(f"  [ERROR] Product search: {exc}")
            return None

    def _call_price_comparison(
        self, raw_results: dict, query_terms: list, sort_by: str
    ) -> Optional[dict]:
        """REST POST → /api/compare on the Price Comparison Service."""
        try:
            resp = requests.post(
                f"{self._urls['comparison']}/api/compare",
                json={
                    "raw_results": raw_results,
                    "query_terms": query_terms,
                    "sort_by": sort_by,
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if data.get("success") else None
        except Exception as exc:
            self._log(f"  [ERROR] Price comparison: {exc}")
            return None

    def _call_recommendation(
        self, products: list, user_id: str, top_n: int, filters: dict
    ) -> list:
        """REST POST → /api/recommend on the Recommendation Service."""
        try:
            resp = requests.post(
                f"{self._urls['recommend']}/api/recommend",
                json={
                    "products": products,
                    "user_id": user_id,
                    "top_n": top_n,
                    "filters": filters,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if data.get("success") else products[:top_n]
        except Exception as exc:
            self._log(f"  [ERROR] Recommendation: {exc}")
            return products[:top_n]

    def _save_history(
        self,
        user_id: str,
        query: str,
        analysis: dict,
        result_count: int,
        top_product: dict,
    ):
        """REST POST → /api/history on the User Preference Service."""
        try:
            requests.post(
                f"{self._urls['preference']}/api/history",
                json={
                    "user_id": user_id,
                    "query": query,
                    "image_description": analysis.get("description", ""),
                    "item_type": analysis.get("type"),
                    "item_color": analysis.get("color"),
                    "item_style": analysis.get("style"),
                    "item_brand": analysis.get("brand"),
                    "result_count": result_count,
                    "top_result_price_sgd": top_product.get("price_sgd"),
                    "top_result_title": top_product.get("title"),
                },
                timeout=5,
            )
        except Exception as exc:
            self._log(f"  [WARN] Could not save history: {exc}")

    @staticmethod
    def _log(msg: str):
        print(f"[ShoppingAgent] {msg}")


# ── Standalone CLI usage ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys as _sys

    if len(_sys.argv) < 2:
        print("Usage: python agents/shopping_agent.py <image_path> [user_id] [extra_keywords]")
        _sys.exit(1)

    img   = _sys.argv[1]
    uid   = _sys.argv[2] if len(_sys.argv) > 2 else "demo_user"
    kw    = _sys.argv[3] if len(_sys.argv) > 3 else ""

    print("\n" + "=" * 60)
    print("FitFinder AI — Shopping Agent (CLI)")
    print(f"Image  : {img}")
    print(f"User   : {uid}")
    print(f"Keywords: {kw or '(none)'}")
    print("=" * 60)

    agent  = ShoppingAgent()
    result = agent.process_shopping_request(image_path=img, user_id=uid, additional_keywords=kw)

    if result["success"]:
        analysis = result["analysis"]
        print(f"\nIdentified: {analysis.get('type')} — {analysis.get('description')}")
        print(f"\nTop {len(result['products'])} Recommendations:")
        print("-" * 60)
        for i, p in enumerate(result["products"], 1):
            print(f"{i:>2}. {p['title']}")
            print(f"    {p['store_name']} ({p['platform']})  S${p['price_sgd']:.2f}")
            print(f"    {p.get('recommendation_label', '')}  score={p.get('recommendation_score', 0):.2f}")
            print(f"    {p['purchase_url']}")
    else:
        print(f"\nFailed: {result['error']}")
