# FitFinder AI — Personal Shopping Assistant-as-a-Service

> **CE/CZ4052 Cloud Computing — Topic 2: Personal Assistant-as-a-Service**
>
> A smart shopping PA that takes a photo of any clothing or product, identifies it with AI vision, searches multiple e-commerce platforms simultaneously, converts prices to SGD, and learns your shopping preferences over time.

---

## Architecture Overview

The system is decomposed into **independent microservices** that communicate exclusively via **RESTful HTTP API calls** — no direct function imports between services.

```
┌─────────────────────────────────────────────────────────────────┐
│                       Streamlit Frontend                         │
│                       localhost:8501                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP POST /api/search
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway  :5000                           │
│   /api/search  /api/history  /api/preferences  /api/stats       │
└────┬─────────────────────────────────────────────────────────────┘
     │ ShoppingAgent orchestrates via sequential REST calls
     │
     │  1. POST :5001/api/analyze     ──► Image Recognition Service
     │  2. POST :5002/api/search      ──► Product Search Service
     │  3. POST :5003/api/compare     ──► Price Comparison Service
     │  4. POST :5004/api/recommend   ──► Recommendation Service
     │  5. POST :5005/api/history     ──► User Preference Service
     │
     └──────────── all via HTTP requests.post() / requests.get() ──
```

### Services

| Port | Service | Responsibility |
|------|---------|----------------|
| 5001 | **Image Recognition** | Sends image to Claude claude-sonnet-4-6 Vision API; returns structured product features |
| 5002 | **Product Search** | Queries SerpAPI (Google Shopping) + RapidAPI **in parallel**; returns raw multi-platform results |
| 5003 | **Price Comparison** | Normalises results to a common schema; converts all prices to SGD; deduplicates |
| 5004 | **Recommendation** | Scores products using similarity × price-fit × brand preference × rating |
| 5005 | **User Preference** | SQLite-backed store; saves search history; auto-learns brand/style/budget patterns |
| 5000 | **API Gateway** | Unified entry-point for the frontend; proxies preference calls; drives the agent |

---

## Project Structure

```
FitFinderAI/
├── services/
│   ├── image_recognition_service.py   # Port 5001 — Claude Vision API
│   ├── product_search_service.py      # Port 5002 — SerpAPI + RapidAPI (parallel)
│   ├── price_comparison_service.py    # Port 5003 — normalise + SGD conversion
│   ├── recommendation_service.py      # Port 5004 — preference-weighted ranking
│   └── user_preference_service.py     # Port 5005 — SQLite history & preferences
├── agents/
│   └── shopping_agent.py              # Orchestrator — calls each service via HTTP
├── api/
│   └── main.py                        # API Gateway — Port 5000
├── frontend/
│   └── app.py                         # Streamlit UI — Port 8501
├── utils/
│   ├── config.py                      # Environment config
│   └── api_clients.py                 # Claude, SerpAPI, RapidAPI, ExchangeRate wrappers
├── database/
│   └── preferences.db                 # SQLite (auto-created on first run)
├── tests/
│   └── test_apis.py                   # pytest integration tests (hits live services)
├── start_all.py                       # One-command launcher
├── requirements.txt
├── .env.example                       # Copy to .env and add API keys
└── README.md
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- pip

```bash
cd FitFinderAI
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env`:

```env
CLAUDE_API_KEY=sk-ant-...          # https://console.anthropic.com
SERP_API_KEY=...                   # https://serpapi.com  (100 free/month)
RAPIDAPI_KEY=...                   # https://rapidapi.com  (optional)
```

### 3. Start Everything

```bash
# With real API keys
python start_all.py

# Demo / development mode — no keys required
python start_all.py --mock
```

Then open **http://localhost:8501** in your browser.

### 4. Start Services Individually (for demo/presentation)

Open one terminal per service to show true independent processes:

```bash
# Terminal 1
python services/image_recognition_service.py   # :5001

# Terminal 2
python services/product_search_service.py      # :5002

# Terminal 3
python services/price_comparison_service.py    # :5003

# Terminal 4
python services/recommendation_service.py      # :5004

# Terminal 5
python services/user_preference_service.py     # :5005

# Terminal 6
python api/main.py                             # :5000

# Terminal 7
streamlit run frontend/app.py                  # :8501
```

### 5. Run Tests

```bash
# Start services first (--mock mode works fine)
python start_all.py --mock &
sleep 5
pytest tests/ -v
```

---

## API Reference

### Image Recognition — POST :5001/api/analyze

```bash
curl -X POST http://localhost:5001/api/analyze \
     -F "image=@shirt.jpg"
```

```json
{
  "success": true,
  "data": {
    "type": "shirt",
    "color": "Blue",
    "colors": ["Blue", "White"],
    "style": "casual",
    "brand": null,
    "description": "A casual blue and white striped cotton shirt",
    "search_terms": ["blue striped shirt", "casual cotton shirt"],
    "material": "cotton",
    "gender": "unisex",
    "confidence": 0.92
  }
}
```

### Product Search — POST :5002/api/search

```bash
curl -X POST http://localhost:5002/api/search \
     -H "Content-Type: application/json" \
     -d '{"description": "blue striped casual shirt", "max_results": 10}'
```

### Price Comparison — POST :5003/api/compare

```bash
curl -X POST http://localhost:5003/api/compare \
     -H "Content-Type: application/json" \
     -d '{"raw_results": {...}, "query_terms": ["blue", "shirt"], "sort_by": "similarity"}'
```

### Recommendation — POST :5004/api/recommend

```bash
curl -X POST http://localhost:5004/api/recommend \
     -H "Content-Type: application/json" \
     -d '{"products": [...], "user_id": "shopper_01", "top_n": 10}'
```

### User Preference — GET/PUT :5005/api/preferences/\<user_id\>

```bash
# Get preferences
curl http://localhost:5005/api/preferences/shopper_01

# Update preferences
curl -X PUT http://localhost:5005/api/preferences/shopper_01 \
     -H "Content-Type: application/json" \
     -d '{"max_budget_sgd": 80, "preferred_brands": ["Nike", "Uniqlo"]}'
```

### User Preference — POST :5005/api/history

```bash
curl -X POST http://localhost:5005/api/history \
     -H "Content-Type: application/json" \
     -d '{"user_id": "shopper_01", "query": "blue shirt", "item_type": "shirt", "top_result_price_sgd": 34.90}'
```

---

## APIs Integrated

| API | Purpose | Docs |
|-----|---------|------|
| **Anthropic Claude claude-sonnet-4-6 Vision** | Product identification from photos | console.anthropic.com |
| **SerpAPI — Google Shopping** | Primary e-commerce search (Singapore-localised) | serpapi.com |
| **RapidAPI — Real-Time Product Search** | Secondary platform coverage | rapidapi.com |
| **ExchangeRate-API** | USD/CNY/MYR → SGD conversion | exchangerate-api.com |

---

## PA Evolution — Preference Learning

After each search the User Preference Service automatically:

1. Counts brand mentions across search history → updates `preferred_brands`
2. Counts style patterns → updates `preferred_styles`
3. Computes average `top_result_price_sgd` → feeds into `avg_budget_sgd`
4. The Recommendation Service uses these signals to re-rank future results

Users can also set explicit preferences via the Preferences tab in the UI or via `PUT /api/preferences/<user_id>`.

---

## Singapore Context

- All prices displayed and compared in **SGD**
- Google Shopping queries are localised with `gl=sg` (Singapore)
- Singapore platforms (Shopee SG, Lazada SG, Zalora, Qoo10) receive a relevance boost in similarity scoring
- Currency conversion handles SGD, USD, CNY, MYR, AUD, GBP, EUR, JPY, HKD

---

## Evaluation Alignment

| Criterion | Implementation |
|-----------|---------------|
| **Architecture (30%)** | 5 independent Flask services on separate ports; all communication via `requests.post/get` HTTP calls |
| **API Integration (30%)** | Claude Vision + SerpAPI + RapidAPI + ExchangeRate-API; parallel search with `concurrent.futures` |
| **AI Agent Logic (20%)** | `ShoppingAgent` orchestrates 5-step pipeline; structured extraction + ranking |
| **User Experience (10%)** | Streamlit UI with image upload, price stats, Buy Now links, dark/light mode |
| **PA Characteristics (10%)** | SQLite history + auto-learned brand/style/budget preferences that evolve over sessions |
