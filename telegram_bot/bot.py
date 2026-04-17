"""
FitFinder AI — Telegram Bot

Lets users search by photo directly in Telegram.
Photos are forwarded to the API Gateway, results returned as inline cards.

Commands:
  /start       — welcome + instructions
  /cart        — view saved cart items
  /clear_cart  — empty the cart
  /help        — usage tips

Photo handler:
  Upload any clothing photo → get top 5 results with Buy Now and Add to Cart buttons.

Usage:
  Set TELEGRAM_BOT_TOKEN in .env, then run:
    python telegram_bot/bot.py
"""

import base64
import logging
import os
import sys

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import TELEGRAM_BOT_TOKEN, API_GATEWAY_PORT

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In Docker the gateway is reachable via its service name.
# Set API_GATEWAY_URL=http://api-gateway:5000 in the container environment.
API_BASE = os.getenv("API_GATEWAY_URL", f"http://localhost:{API_GATEWAY_PORT}")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_key(user_id: int) -> str:
    return str(user_id)


def _store_products(context: ContextTypes.DEFAULT_TYPE, user_id: int, products: list):
    """Persist last search results in user_data for Add-to-Cart callbacks."""
    if "products" not in context.user_data:
        context.user_data["products"] = {}
    context.user_data["products"][_user_key(user_id)] = products


def _get_product(context: ContextTypes.DEFAULT_TYPE, user_id: int, idx: int):
    prods = (context.user_data.get("products") or {}).get(_user_key(user_id), [])
    return prods[idx] if 0 <= idx < len(prods) else None


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*FitFinder AI* — Smart Shopping PA\n\n"
        "Send me a photo of any clothing item and I'll find the best deals across "
        "Shopee, Lazada, Google Shopping, and more.\n\n"
        "Commands:\n"
        "/cart — view your saved cart\n"
        "/clear\\_cart — empty the cart\n"
        "/help — tips for best results",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Tips for best results:*\n\n"
        "• Use a clear photo with the item on a plain background\n"
        "• One item per photo works best\n"
        "• Good lighting helps the AI identify colours accurately\n\n"
        "*Buttons on each result:*\n"
        "🔗 *Buy Now* — opens the product page directly\n"
        "➕ *Add to Cart* — saves the item to your cart\n\n"
        "All prices are shown in SGD.",
        parse_mode="Markdown",
    )


async def cmd_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    try:
        r = requests.get(f"{API_BASE}/api/cart/{user_id}", timeout=5)
        data = r.json()
    except Exception as exc:
        await update.message.reply_text(f"Could not reach cart service: {exc}")
        return

    items = data.get("items", [])
    if not items:
        await update.message.reply_text(
            "Your cart is empty.\n\nSend a photo to start searching!"
        )
        return

    lines = ["*Your Cart*\n"]
    for i, item in enumerate(items, 1):
        lines.append(
            f"{i}. *{item['title'][:60]}*\n"
            f"   S${item['price_sgd']:.2f} · {item.get('store_name', '')}"
        )
    lines.append(f"\n*Total: S${data.get('total_sgd', 0):.2f}*")

    # Build "Open" buttons for items that have a URL
    keyboard = []
    for item in items:
        if item.get("purchase_url"):
            keyboard.append(
                [InlineKeyboardButton(
                    f"Buy: {item['title'][:30]}...",
                    url=item["purchase_url"],
                )]
            )

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def cmd_clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    try:
        requests.delete(f"{API_BASE}/api/cart/{user_id}", timeout=5)
        await update.message.reply_text("Cart cleared.")
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download the photo, send to /api/search, display top results."""
    user_id = update.effective_user.id
    status = await update.message.reply_text("Analysing image, searching platforms…")

    try:
        # Telegram provides multiple resolutions; use the largest
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image_b64 = base64.b64encode(photo_bytes).decode("utf-8")

        r = requests.post(
            f"{API_BASE}/api/search",
            json={"image_base64": image_b64, "user_id": str(user_id), "max_results": 5},
            timeout=70,
        )
        result = r.json()
    except Exception as exc:
        await status.edit_text(f"Search failed: {exc}")
        return

    await status.delete()

    if not result.get("success"):
        await update.message.reply_text(
            f"Search error: {result.get('error', 'Unknown error')}"
        )
        return

    products = result.get("products", [])
    if not products:
        await update.message.reply_text(
            "No products found — try a clearer photo or different angle."
        )
        return

    # Store products for Add-to-Cart callbacks
    _store_products(context, user_id, products)

    # Show AI analysis summary
    analysis = result.get("analysis") or {}
    summary = (
        f"AI identified: *{(analysis.get('type') or '').title()}*"
        f" · {analysis.get('color', '')} · {(analysis.get('style') or '').title()}"
    )
    await update.message.reply_text(summary, parse_mode="Markdown")

    # Send each product as a separate message
    for idx, p in enumerate(products[:5]):
        title = p.get("title", "Unknown")[:80]
        store = p.get("store_name", "")
        platform = p.get("platform", "")
        price = p.get("price_sgd", 0)
        rating = p.get("rating")
        label = p.get("recommendation_label", "")
        score = p.get("recommendation_score", 0)

        rating_str = f"⭐ {rating:.1f}" if rating else ""
        text = (
            f"*{title}*\n"
            f"{store} · {platform}\n"
            f"S${price:.2f}  {rating_str}\n"
            f"_{label}_ · match {score:.0%}"
        )

        keyboard = [[]]
        if p.get("purchase_url"):
            keyboard[0].append(
                InlineKeyboardButton("🔗 Buy Now", url=p["purchase_url"])
            )
        keyboard[0].append(
            InlineKeyboardButton("➕ Add to Cart", callback_data=f"cart|{idx}")
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        if p.get("image_url"):
            try:
                await update.message.reply_photo(
                    photo=p["image_url"],
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
                continue
            except Exception:
                pass  # fall back to text message if image fails

        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=reply_markup
        )

    await update.message.reply_text(
        f"Found {len(products)} results total.  Use /cart to view saved items."
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("cart|"):
        return

    user_id = query.from_user.id
    idx = int(query.data.split("|")[1])
    product = _get_product(context, user_id, idx)

    if not product:
        await query.answer("Product data expired — search again.", show_alert=True)
        return

    try:
        r = requests.post(
            f"{API_BASE}/api/cart/add",
            json={"user_id": str(user_id), "product": product},
            timeout=5,
        )
        if r.ok:
            title = product.get("title", "Item")[:40]
            await query.answer(f"Added: {title}", show_alert=False)
        else:
            await query.answer("Failed to add to cart.", show_alert=True)
    except Exception as exc:
        await query.answer(f"Error: {exc}", show_alert=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("[TelegramBot] TELEGRAM_BOT_TOKEN not set in .env — bot will not start.")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("cart", cmd_cart))
    app.add_handler(CommandHandler("clear_cart", cmd_clear_cart))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("[TelegramBot] Running (polling)…")
    app.run_polling()


if __name__ == "__main__":
    main()
