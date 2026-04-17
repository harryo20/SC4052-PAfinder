#!/usr/bin/env python3
"""
start_all.py — Launch every FitFinder AI microservice + Streamlit frontend.

Usage:
  python start_all.py           # real API mode (requires .env keys)
  python start_all.py --mock    # mock-data mode — no API keys needed
  python start_all.py --help    # show this message

Services started:
  Port 5001  Image Recognition Service
  Port 5002  Product Search Service
  Port 5003  Price Comparison Service
  Port 5004  Recommendation Service
  Port 5005  User Preference Service
  Port 5000  API Gateway
  Port 8501  Streamlit Frontend  (opens in browser automatically)
"""

import atexit
import os
import subprocess
import sys
import time

from dotenv import load_dotenv
load_dotenv()

SERVICES = [
    ("Image Recognition",  "services/image_recognition_service.py",  5001),
    ("Product Search",     "services/product_search_service.py",      5002),
    ("Price Comparison",   "services/price_comparison_service.py",    5003),
    ("Recommendation",     "services/recommendation_service.py",      5004),
    ("User Preference",    "services/user_preference_service.py",     5005),
    ("Cart",               "services/cart_service.py",                5006),
    ("API Gateway",        "api/main.py",                              5000),
]

_procs: list = []


def _cleanup():
    print("\n[shutdown] Stopping all services …")
    for p in _procs:
        try:
            p.terminate()
        except Exception:
            pass
    for p in _procs:
        try:
            p.wait(timeout=5)
        except Exception:
            pass
    print("[shutdown] Done.")


atexit.register(_cleanup)


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return

    mock = "--mock" in sys.argv
    env  = os.environ.copy()
    if mock:
        env["USE_MOCK_DATA"] = "true"

    print()
    print("=" * 62)
    print("  FitFinder AI — PA-as-a-Service  (CE/CZ4052 Cloud Computing)")
    if mock:
        print("  Mode: MOCK DATA  (no API keys required)")
    print("=" * 62)
    print()

    # Start all back-end microservices
    for name, script, port in SERVICES:
        if not os.path.exists(script):
            print(f"  [SKIP] {script} not found")
            continue
        proc = subprocess.Popen(
            [sys.executable, script],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _procs.append(proc)
        print(f"  ✓  {name:<30}  http://localhost:{port}")
        time.sleep(0.4)         # slight stagger to avoid port race

    print()
    print("  Waiting for services to initialise …")
    time.sleep(3)

    # Start Streamlit
    frontend = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "frontend/app.py",
            "--server.port", "8501",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        env=env,
    )
    _procs.append(frontend)
    print(f"  ✓  {'Streamlit Frontend':<30}  http://localhost:8501")

    # Start Telegram bot only if token is configured
    tg_token = env.get("TELEGRAM_BOT_TOKEN", "")
    if tg_token and tg_token != "your_telegram_bot_token_here":
        tg_proc = subprocess.Popen(
            [sys.executable, "telegram_bot/bot.py"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _procs.append(tg_proc)
        print(f"  ✓  {'Telegram Bot':<30}  (polling)")
    else:
        print(f"  -  {'Telegram Bot':<30}  (skipped — no TELEGRAM_BOT_TOKEN)")

    print()
    print("=" * 62)
    print("  All services running!")
    print()
    print("  Web:      http://localhost:8501")
    print("  API:      http://localhost:5000/health")
    print("  Services: http://localhost:5000/api/services/status")
    print()
    print("  Press Ctrl+C to stop everything.")
    print("=" * 62)
    print()

    try:
        frontend.wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
