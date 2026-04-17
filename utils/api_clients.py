"""
api_clients.py — Thin wrappers around each third-party API.
All network I/O lives here; services import these helpers.
"""

import json
import time
import anthropic
import requests

from utils.config import (
    CLAUDE_API_KEY, SERP_API_KEY, RAPIDAPI_KEY,
    CLAUDE_MODEL,
    SERP_API_BASE_URL, EXCHANGE_RATE_BASE_URL,
    RAPIDAPI_HOST, RAPIDAPI_BASE_URL,
)


# ── Claude Vision ─────────────────────────────────────────────────────────────

class ClaudeClient:
    """Anthropic Claude Vision API — identifies products from images."""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    def analyze_clothing_image(self, image_base64: str, media_type: str = "image/jpeg") -> dict:
        """
        Send an image to Claude Vision and return structured product features.

        Returns dict with keys: type, color, colors, style, brand, description,
        search_terms, material, gender, confidence.
        """
        prompt = (
            "Analyze this clothing or product image and return ONLY a JSON object "
            "(no markdown, no extra text) with these exact keys:\n"
            "{\n"
            '  "type": "one of: shirt|tshirt|pants|jeans|dress|skirt|jacket|coat|hoodie|sweater|shoes|sneakers|boots|bag|hat|accessory|other",\n'
            '  "color": "primary color name",\n'
            '  "colors": ["list", "of", "all", "visible", "colors"],\n'
            '  "style": "one of: casual|formal|sporty|streetwear|business|bohemian|vintage|minimalist|luxury|unknown",\n'
            '  "brand": "brand name if clearly visible, or null",\n'
            '  "description": "one-sentence description of the item",\n'
            '  "search_terms": ["3-6 search keywords to find this item online"],\n'
            '  "material": "detected material if visible, or null",\n'
            '  "gender": "one of: men|women|unisex|unknown",\n'
            '  "confidence": 0.0\n'
            "}\n"
            "Focus on: garment type, colors, cut, material texture, logos, and style."
        )

        message = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )

        text = message.content[0].text.strip()
        # Strip any accidental markdown fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        return json.loads(text)


# ── SerpAPI ───────────────────────────────────────────────────────────────────

class SerpAPIClient:
    """SerpAPI — Google Shopping and eBay search."""

    def search_google_shopping(self, query: str, country: str = "sg", num: int = 20) -> list:
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": SERP_API_KEY,
            "num": num,
            "gl": country,
            "hl": "en",
            "currency": "SGD",
        }
        resp = requests.get(SERP_API_BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json().get("shopping_results", [])

    def search_ebay(self, query: str, num: int = 10) -> list:
        params = {
            "engine": "ebay",
            "_nkw": query,
            "api_key": SERP_API_KEY,
            "num": num,
        }
        try:
            resp = requests.get(SERP_API_BASE_URL, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json().get("organic_results", [])
        except Exception:
            return []


# ── RapidAPI Product Search ───────────────────────────────────────────────────

class RapidAPIShoppingClient:
    """RapidAPI Real-Time Product Search — extra platform coverage."""

    def __init__(self):
        self.headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
        }

    def search_products(self, query: str, country: str = "sg", num: int = 10) -> list:
        url = f"{RAPIDAPI_BASE_URL}/search"
        params = {"q": query, "country": country, "language": "en", "limit": num}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("products", [])
        except Exception:
            return []


# ── Exchange Rate ─────────────────────────────────────────────────────────────

class ExchangeRateClient:
    """
    Converts any currency to SGD.
    Responses are cached in-process for one hour to avoid hitting rate limits.
    """

    _cache: dict = {}
    _cache_time: dict = {}
    _TTL = 3600  # seconds

    # Approximate fallback rates (USD → SGD ~1.35 as of 2025)
    _FALLBACK = {
        "USD": 1.35, "EUR": 1.45, "GBP": 1.70, "AUD": 0.88,
        "CNY": 0.19, "JPY": 0.009, "MYR": 0.30,
        "THB": 0.038, "IDR": 0.000087, "HKD": 0.17,
    }

    def get_rate_to_sgd(self, from_currency: str) -> float:
        from_currency = from_currency.upper()
        if from_currency == "SGD":
            return 1.0

        now = time.time()
        if from_currency in self._cache and now - self._cache_time.get(from_currency, 0) < self._TTL:
            return self._cache[from_currency]

        try:
            resp = requests.get(f"{EXCHANGE_RATE_BASE_URL}/{from_currency}", timeout=10)
            resp.raise_for_status()
            rate = resp.json()["rates"].get("SGD", self._FALLBACK.get(from_currency, 1.35))
            self._cache[from_currency] = rate
            self._cache_time[from_currency] = now
            return rate
        except Exception:
            return self._FALLBACK.get(from_currency, 1.35)

    def convert_to_sgd(self, amount: float, from_currency: str) -> float:
        return round(amount * self.get_rate_to_sgd(from_currency), 2)
