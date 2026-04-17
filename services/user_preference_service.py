"""
User Preference Service — Port 5005

Stores and evolves a user's shopping habits in SQLite.
Automatically learns brand/style/budget patterns from search history
and surfaces them as personalised filters for the Recommendation Service.

Endpoints:
  GET    /api/preferences/<user_id>   — fetch preferences (+ computed avg_budget)
  PUT    /api/preferences/<user_id>   — create / update preferences
  POST   /api/history                 — save a completed search
  GET    /api/history/<user_id>       — retrieve recent searches
  DELETE /api/history/<user_id>       — clear all history
  GET    /api/stats/<user_id>         — shopping analytics
  POST   /api/saved-items             — save a product for later
  GET    /api/saved-items/<user_id>   — list saved products
  GET    /health                      — health check

CE/CZ4052 Cloud Computing — PA-as-a-Service
"""

import json
import os
import sqlite3
import sys
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import PREFERENCE_SERVICE_PORT, DATABASE_PATH

app = Flask(__name__)
CORS(app)


# ── Database helpers ──────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS search_history (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             TEXT NOT NULL,
            query               TEXT NOT NULL,
            image_description   TEXT,
            item_type           TEXT,
            item_color          TEXT,
            item_style          TEXT,
            item_brand          TEXT,
            result_count        INTEGER DEFAULT 0,
            top_result_price_sgd REAL,
            top_result_title    TEXT,
            searched_at         TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id             TEXT PRIMARY KEY,
            max_budget_sgd      REAL,
            preferred_brands    TEXT DEFAULT '[]',
            preferred_styles    TEXT DEFAULT '[]',
            preferred_platforms TEXT DEFAULT '[]',
            size_info           TEXT DEFAULT '{}',
            updated_at          TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS saved_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            product_title   TEXT NOT NULL,
            product_url     TEXT NOT NULL,
            store_name      TEXT,
            price_sgd       REAL,
            image_url       TEXT,
            notes           TEXT,
            saved_at        TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_search_user ON search_history(user_id);
        CREATE INDEX IF NOT EXISTS idx_saved_user  ON saved_items(user_id);
    """)
    conn.commit()
    conn.close()


_init_db()


# ── Preference auto-learning ──────────────────────────────────────────────────

def _auto_learn(conn: sqlite3.Connection, user_id: str):
    """
    After each new search, re-derive preferred brands/styles and estimated
    budget from the full history and persist them as learned preferences.
    Only updates auto-learned fields — user-set max_budget_sgd is preserved.
    """
    brands = [
        r["item_brand"] for r in conn.execute(
            """SELECT item_brand, COUNT(*) c FROM search_history
               WHERE user_id=? AND item_brand IS NOT NULL AND item_brand!=''
               GROUP BY item_brand ORDER BY c DESC LIMIT 5""",
            (user_id,),
        ).fetchall()
    ]
    styles = [
        r["item_style"] for r in conn.execute(
            """SELECT item_style, COUNT(*) c FROM search_history
               WHERE user_id=? AND item_style IS NOT NULL AND item_style!=''
               GROUP BY item_style ORDER BY c DESC LIMIT 3""",
            (user_id,),
        ).fetchall()
    ]

    budget_row = conn.execute(
        """SELECT AVG(top_result_price_sgd) avg, MAX(top_result_price_sgd) mx
           FROM search_history
           WHERE user_id=? AND top_result_price_sgd IS NOT NULL""",
        (user_id,),
    ).fetchone()

    existing = conn.execute(
        "SELECT max_budget_sgd, preferred_platforms, size_info FROM user_preferences WHERE user_id=?",
        (user_id,),
    ).fetchone()

    user_max = existing["max_budget_sgd"] if existing else None
    platforms = (existing["preferred_platforms"] if existing else "[]")
    size_info = (existing["size_info"] if existing else "{}")

    # Only fill max_budget_sgd from history if the user never set one
    learned_max = None
    if budget_row and budget_row["avg"]:
        learned_max = round(budget_row["avg"] * 1.3, 2)

    now = datetime.utcnow().isoformat()
    conn.execute(
        """INSERT INTO user_preferences
           (user_id, max_budget_sgd, preferred_brands, preferred_styles,
            preferred_platforms, size_info, updated_at)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
             preferred_brands   = excluded.preferred_brands,
             preferred_styles   = excluded.preferred_styles,
             max_budget_sgd     = COALESCE(user_preferences.max_budget_sgd, excluded.max_budget_sgd),
             updated_at         = excluded.updated_at""",
        (
            user_id,
            user_max if user_max is not None else learned_max,
            json.dumps(brands),
            json.dumps(styles),
            platforms,
            size_info,
            now,
        ),
    )
    conn.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "user-preference", "port": PREFERENCE_SERVICE_PORT})


# ── Preferences ───────────────────────────────────────────────────────────────

@app.route("/api/preferences/<user_id>", methods=["GET"])
def get_preferences(user_id: str):
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id=?", (user_id,)
        ).fetchone()

        if row:
            data = dict(row)
            data["preferred_brands"] = json.loads(data["preferred_brands"])
            data["preferred_styles"] = json.loads(data["preferred_styles"])
            data["preferred_platforms"] = json.loads(data["preferred_platforms"])
            data["size_info"] = json.loads(data["size_info"])
        else:
            data = {
                "user_id": user_id,
                "max_budget_sgd": None,
                "preferred_brands": [],
                "preferred_styles": [],
                "preferred_platforms": [],
                "size_info": {},
            }

        # Compute avg_budget_sgd from history for the recommender
        avg_row = conn.execute(
            """SELECT AVG(top_result_price_sgd) avg FROM search_history
               WHERE user_id=? AND top_result_price_sgd IS NOT NULL""",
            (user_id,),
        ).fetchone()
        data["avg_budget_sgd"] = round(avg_row["avg"], 2) if avg_row and avg_row["avg"] else data.get("max_budget_sgd")

        return jsonify({"success": True, "data": data})
    finally:
        conn.close()


@app.route("/api/preferences/<user_id>", methods=["PUT"])
def update_preferences(user_id: str):
    body = request.get_json()
    if not body:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    conn = _get_db()
    try:
        existing = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id=?", (user_id,)
        ).fetchone()

        if existing:
            ex = dict(existing)
            brands   = json.loads(ex["preferred_brands"])
            styles   = json.loads(ex["preferred_styles"])
            platforms= json.loads(ex["preferred_platforms"])
            sizes    = json.loads(ex["size_info"])
            budget   = ex["max_budget_sgd"]
        else:
            brands = styles = platforms = []
            sizes  = {}
            budget = None

        if "max_budget_sgd" in body:
            budget = body["max_budget_sgd"]
        if "preferred_brands" in body:
            brands = body["preferred_brands"]
        if "preferred_styles" in body:
            styles = body["preferred_styles"]
        if "preferred_platforms" in body:
            platforms = body["preferred_platforms"]
        if "size_info" in body:
            sizes.update(body["size_info"])

        now = datetime.utcnow().isoformat()
        conn.execute(
            """INSERT INTO user_preferences
               (user_id, max_budget_sgd, preferred_brands, preferred_styles,
                preferred_platforms, size_info, updated_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 max_budget_sgd      = excluded.max_budget_sgd,
                 preferred_brands    = excluded.preferred_brands,
                 preferred_styles    = excluded.preferred_styles,
                 preferred_platforms = excluded.preferred_platforms,
                 size_info           = excluded.size_info,
                 updated_at          = excluded.updated_at""",
            (user_id, budget, json.dumps(brands), json.dumps(styles),
             json.dumps(platforms), json.dumps(sizes), now),
        )
        conn.commit()
        return jsonify({"success": True, "message": "Preferences updated"})
    finally:
        conn.close()


# ── Search history ────────────────────────────────────────────────────────────

@app.route("/api/history", methods=["POST"])
def save_search():
    body = request.get_json()
    if not body:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    user_id = body.get("user_id", "default")
    conn = _get_db()
    try:
        conn.execute(
            """INSERT INTO search_history
               (user_id, query, image_description, item_type, item_color,
                item_style, item_brand, result_count, top_result_price_sgd,
                top_result_title, searched_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                user_id,
                body.get("query", ""),
                body.get("image_description"),
                body.get("item_type"),
                body.get("item_color"),
                body.get("item_style"),
                body.get("item_brand"),
                body.get("result_count", 0),
                body.get("top_result_price_sgd"),
                body.get("top_result_title"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        _auto_learn(conn, user_id)
        return jsonify({"success": True, "message": "Search saved"})
    finally:
        conn.close()


@app.route("/api/history/<user_id>", methods=["GET"])
def get_history(user_id: str):
    limit = request.args.get("limit", 20, type=int)
    conn = _get_db()
    try:
        rows = conn.execute(
            """SELECT * FROM search_history WHERE user_id=?
               ORDER BY searched_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return jsonify({"success": True, "data": [dict(r) for r in rows], "count": len(rows)})
    finally:
        conn.close()


@app.route("/api/history/<user_id>", methods=["DELETE"])
def clear_history(user_id: str):
    conn = _get_db()
    try:
        conn.execute("DELETE FROM search_history WHERE user_id=?", (user_id,))
        conn.commit()
        return jsonify({"success": True, "message": "History cleared"})
    finally:
        conn.close()


# ── Stats / analytics ─────────────────────────────────────────────────────────

@app.route("/api/stats/<user_id>", methods=["GET"])
def get_stats(user_id: str):
    conn = _get_db()
    try:
        total = conn.execute(
            "SELECT COUNT(*) c FROM search_history WHERE user_id=?", (user_id,)
        ).fetchone()["c"]

        budget = conn.execute(
            """SELECT AVG(top_result_price_sgd) avg,
                      MIN(top_result_price_sgd) mn,
                      MAX(top_result_price_sgd) mx
               FROM search_history WHERE user_id=? AND top_result_price_sgd IS NOT NULL""",
            (user_id,),
        ).fetchone()

        types = conn.execute(
            """SELECT item_type, COUNT(*) c FROM search_history
               WHERE user_id=? AND item_type IS NOT NULL
               GROUP BY item_type ORDER BY c DESC LIMIT 5""",
            (user_id,),
        ).fetchall()

        brands = conn.execute(
            """SELECT item_brand, COUNT(*) c FROM search_history
               WHERE user_id=? AND item_brand IS NOT NULL AND item_brand!=''
               GROUP BY item_brand ORDER BY c DESC LIMIT 5""",
            (user_id,),
        ).fetchall()

        return jsonify({
            "success": True,
            "data": {
                "total_searches": total,
                "avg_price_sgd":   round(budget["avg"], 2) if budget and budget["avg"] else None,
                "price_range_sgd": {
                    "min": budget["mn"] if budget else None,
                    "max": budget["mx"] if budget else None,
                },
                "top_item_types": [{"type": r["item_type"], "count": r["c"]} for r in types],
                "top_brands":     [{"brand": r["item_brand"], "count": r["c"]} for r in brands],
            },
        })
    finally:
        conn.close()


# ── Saved items ───────────────────────────────────────────────────────────────

@app.route("/api/saved-items", methods=["POST"])
def save_item():
    body = request.get_json()
    if not body:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    conn = _get_db()
    try:
        conn.execute(
            """INSERT INTO saved_items
               (user_id, product_title, product_url, store_name, price_sgd, image_url, notes, saved_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                body.get("user_id", "default"),
                body.get("product_title", ""),
                body.get("product_url", ""),
                body.get("store_name"),
                body.get("price_sgd"),
                body.get("image_url"),
                body.get("notes"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return jsonify({"success": True, "message": "Item saved"})
    finally:
        conn.close()


@app.route("/api/saved-items/<user_id>", methods=["GET"])
def get_saved_items(user_id: str):
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM saved_items WHERE user_id=? ORDER BY saved_at DESC",
            (user_id,),
        ).fetchall()
        return jsonify({"success": True, "data": [dict(r) for r in rows]})
    finally:
        conn.close()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PREFERENCE_SERVICE_PORT", PREFERENCE_SERVICE_PORT))
    print(f"[User Preference Service] Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
