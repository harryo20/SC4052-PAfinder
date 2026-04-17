"""
Cart Service — Port 5006

Persists user shopping carts in SQLite.
Each item stores the full product snapshot so cart contents survive service restarts.

Endpoints:
  POST   /api/cart/add              — add a product to a user's cart
  GET    /api/cart/<user_id>        — fetch cart with total
  DELETE /api/cart/item/<item_id>   — remove one item
  DELETE /api/cart/<user_id>        — clear entire cart
  GET    /health

CE/CZ4052 Cloud Computing — PA-as-a-Service
"""

import os
import sqlite3
import sys
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import CART_SERVICE_PORT, CART_DB_PATH

app = Flask(__name__)
CORS(app)


# ── Database ──────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(CART_DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(CART_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cart_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT    NOT NULL,
            title        TEXT    NOT NULL,
            price_sgd    REAL    NOT NULL DEFAULT 0,
            platform     TEXT,
            store_name   TEXT,
            purchase_url TEXT,
            image_url    TEXT,
            added_at     TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cart_user ON cart_items(user_id);
    """)
    conn.commit()
    conn.close()


_init_db()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "cart", "port": CART_SERVICE_PORT})


@app.route("/api/cart/add", methods=["POST"])
def add_item():
    body = request.get_json()
    if not body:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    user_id = body.get("user_id")
    product = body.get("product")
    if not user_id or not product:
        return jsonify({"success": False, "error": "user_id and product required"}), 400

    conn = _get_db()
    try:
        cur = conn.execute(
            """INSERT INTO cart_items
               (user_id, title, price_sgd, platform, store_name, purchase_url, image_url, added_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                user_id,
                product.get("title", "Unknown Product"),
                float(product.get("price_sgd") or 0),
                product.get("platform", ""),
                product.get("store_name", ""),
                product.get("purchase_url", ""),
                product.get("image_url", ""),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return jsonify({"success": True, "item_id": cur.lastrowid})
    finally:
        conn.close()


@app.route("/api/cart/<user_id>", methods=["GET"])
def get_cart(user_id: str):
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM cart_items WHERE user_id=? ORDER BY added_at DESC",
            (user_id,),
        ).fetchall()
        items = [dict(r) for r in rows]
        total = round(sum(r["price_sgd"] for r in items), 2)
        return jsonify({
            "success": True,
            "items": items,
            "count": len(items),
            "total_sgd": total,
        })
    finally:
        conn.close()


@app.route("/api/cart/item/<int:item_id>", methods=["DELETE"])
def remove_item(item_id: int):
    conn = _get_db()
    try:
        conn.execute("DELETE FROM cart_items WHERE id=?", (item_id,))
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/cart/<user_id>", methods=["DELETE"])
def clear_cart(user_id: str):
    conn = _get_db()
    try:
        conn.execute("DELETE FROM cart_items WHERE user_id=?", (user_id,))
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("CART_SERVICE_PORT", CART_SERVICE_PORT))
    print(f"[Cart Service] Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
