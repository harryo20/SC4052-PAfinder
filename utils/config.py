import os
from dotenv import load_dotenv

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
SERP_API_KEY = os.getenv("SERP_API_KEY", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY", "")

IMAGE_SERVICE_PORT = int(os.getenv("IMAGE_SERVICE_PORT", "5001"))
SEARCH_SERVICE_PORT = int(os.getenv("SEARCH_SERVICE_PORT", "5002"))
COMPARISON_SERVICE_PORT = int(os.getenv("COMPARISON_SERVICE_PORT", "5003"))
RECOMMENDATION_SERVICE_PORT = int(os.getenv("RECOMMENDATION_SERVICE_PORT", "5004"))
PREFERENCE_SERVICE_PORT = int(os.getenv("PREFERENCE_SERVICE_PORT", "5005"))
CART_SERVICE_PORT = int(os.getenv("CART_SERVICE_PORT", "5006"))
API_GATEWAY_PORT = int(os.getenv("API_GATEWAY_PORT", "5000"))

IMAGE_SERVICE_URL        = os.getenv("IMAGE_SERVICE_URL",        f"http://localhost:{IMAGE_SERVICE_PORT}")
SEARCH_SERVICE_URL       = os.getenv("SEARCH_SERVICE_URL",       f"http://localhost:{SEARCH_SERVICE_PORT}")
COMPARISON_SERVICE_URL   = os.getenv("COMPARISON_SERVICE_URL",   f"http://localhost:{COMPARISON_SERVICE_PORT}")
RECOMMENDATION_SERVICE_URL = os.getenv("RECOMMENDATION_SERVICE_URL", f"http://localhost:{RECOMMENDATION_SERVICE_PORT}")
PREFERENCE_SERVICE_URL   = os.getenv("PREFERENCE_SERVICE_URL",   f"http://localhost:{PREFERENCE_SERVICE_PORT}")
CART_SERVICE_URL         = os.getenv("CART_SERVICE_URL",         f"http://localhost:{CART_SERVICE_PORT}")

CLAUDE_MODEL = "claude-sonnet-4-6"

SERP_API_BASE_URL = "https://serpapi.com/search.json"
EXCHANGE_RATE_BASE_URL = "https://api.exchangerate-api.com/v4/latest"

RAPIDAPI_HOST = "real-time-product-search.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

DATABASE_PATH = os.getenv("DATABASE_PATH", "database/preferences.db")
CART_DB_PATH = os.getenv("CART_DB_PATH", "database/carts.db")

MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "20"))
TOP_RECOMMENDATIONS = int(os.getenv("TOP_RECOMMENDATIONS", "10"))
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
DEFAULT_CURRENCY = "SGD"
