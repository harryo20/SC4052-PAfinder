Youtube Demo
https://youtu.be/3PPkCiNMWIw 

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
CLAUDE_API_KEY=...          
SERP_API_KEY=...                   
RAPIDAPI_KEY=...                  
```

### 3. Start Everything

```bash
# For telegram bot version
python start_all.py

# Demo / development mode — no keys required
python start_all.py --mock
```

open **http://localhost:8501** 



## APIs Integrated

| API | Purpose | Docs |
|-----|---------|------|
| **Anthropic Claude claude-sonnet-4-6 Vision** 
| **SerpAPI — Google Shopping** 
| **RapidAPI — Real-Time Product Search**
| **ExchangeRate-API** 

