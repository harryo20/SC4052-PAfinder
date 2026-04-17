
import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

_DB_PATH = os.getenv("WATCHED_DB_PATH", os.path.join("database", "watched_items.db"))
_API_BASE = os.getenv("API_GATEWAY_URL", "http://localhost:5000")


def init_db():
    os.makedirs(os.path.dirname(_DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watched_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT    NOT NULL,
            product_name    TEXT    NOT NULL,
            platform        TEXT    NOT NULL,
            product_url     TEXT    NOT NULL,
            original_price  REAL    NOT NULL,
            last_seen_price REAL    NOT NULL,
            search_query    TEXT,
            alert_threshold REAL    DEFAULT 0.05,
            added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checked    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active       INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def save_watched_item(user_id: str, item: dict, search_query: str):
    price = item.get("price_sgd", 0)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        INSERT INTO watched_items
            (user_id, product_name, platform, product_url,
             original_price, last_seen_price, search_query)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        (item.get("title") or "Unknown")[:100],
        item.get("platform", ""),
        item.get("purchase_url", ""),
        price,
        price,
        search_query,
    ))
    conn.commit()
    conn.close()


def get_watched_items(user_id: str) -> list[dict]:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, product_name, platform, original_price, last_seen_price, last_checked
        FROM watched_items
        WHERE user_id = ? AND is_active = 1
        ORDER BY added_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def deactivate_watched_item(item_id: int):
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("UPDATE watched_items SET is_active = 0 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def get_item_by_id(item_id: int) -> dict | None:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM watched_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _fetch_current_price(product_name: str, platform: str, search_query: str) -> float | None:
    """
    Re-search the product by text via /api/search-text and return the current
    best-match price. Requires a text-only search endpoint on the API gateway.
    Returns None gracefully if the endpoint is unavailable.
    """
    try:
        resp = requests.post(
            f"{_API_BASE}/api/search-text",
            json={"query": search_query or product_name, "platform": platform},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        products = resp.json().get("products", [])
        # Prefer same-platform results; fall back to cheapest overall
        same_platform = [
            p for p in products
            if platform.lower() in (p.get("platform") or "").lower()
        ]
        candidates = same_platform or products
        if candidates:
            return min(p.get("price_sgd", 9999) for p in candidates)
        return None
    except Exception as exc:
        logger.debug(f"Price fetch skipped for '{product_name}': {exc}")
        return None


async def check_price_drops(bot: Bot):
    """Fetch current prices for all active watched items and alert on drops."""
    logger.info("Running price drop check...")

    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    items = [dict(r) for r in conn.execute("""
        SELECT id, user_id, product_name, platform, product_url,
               original_price, last_seen_price, search_query, alert_threshold
        FROM watched_items WHERE is_active = 1
    """).fetchall()]
    conn.close()

    for item in items:
        try:
            current_price = await asyncio.to_thread(
                _fetch_current_price,
                item["product_name"],
                item["platform"],
                item["search_query"] or "",
            )
            if current_price is None:
                continue

            # Update last-seen price and timestamp
            upd = sqlite3.connect(_DB_PATH)
            upd.execute(
                "UPDATE watched_items SET last_checked = CURRENT_TIMESTAMP, last_seen_price = ? WHERE id = ?",
                (current_price, item["id"]),
            )
            upd.commit()
            upd.close()

            last_price = item["last_seen_price"]
            drop = last_price - current_price
            drop_pct = drop / last_price if last_price > 0 else 0

            if drop_pct >= item["alert_threshold"] and drop > 0:
                await _send_price_alert(bot, item, current_price, drop, drop_pct)

        except Exception as exc:
            logger.error(f"Error checking item {item['id']}: {exc}")


async def _send_price_alert(
    bot: Bot, item: dict, new_price: float, drop: float, drop_pct: float
):
    old_price = item["last_seen_price"]
    saved_vs_orig = item["original_price"] - new_price

    msg = (
        f"🔥 *Price Drop Alert!*\n\n"
        f"*{item['product_name'][:60]}*\n"
        f"📍 {item['platform']}\n\n"
        f"~~SGD {old_price:.2f}~~ → *SGD {new_price:.2f}*\n"
        f"💰 That's {int(drop_pct * 100)}% off (save SGD {drop:.2f})!\n"
    )
    if saved_vs_orig > 0:
        msg += f"_(SGD {saved_vs_orig:.2f} cheaper than when you saved it)_\n"
    if item["product_url"]:
        msg += f"\n[View on {item['platform']}]({item['product_url']})"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Add to Cart", callback_data=f"alert_cart|{item['id']}"),
        InlineKeyboardButton("🔕 Stop Watching", callback_data=f"alert_stop|{item['id']}"),
    ]])

    try:
        await bot.send_message(
            chat_id=item["user_id"],
            text=msg,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=False,
        )
        logger.info(f"Alert sent to {item['user_id']} for item {item['id']}")
    except Exception as exc:
        logger.error(f"Failed to send alert to {item['user_id']}: {exc}")


def get_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    # Main 4-hour recurring job
    scheduler.add_job(
        check_price_drops,
        trigger="interval",
        hours=4,
        args=[bot],
        id="price_monitor",
        name="Price Drop Monitor",
        misfire_grace_time=300,
    )
    # Startup run 30 s after launch so the first check doesn't wait 4 hours
    scheduler.add_job(
        check_price_drops,
        trigger="date",
        run_date=datetime.now() + timedelta(seconds=30),
        args=[bot],
        id="price_monitor_startup",
    )
    return scheduler
