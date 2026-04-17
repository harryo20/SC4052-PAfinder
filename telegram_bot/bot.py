
import asyncio
import base64
import json
import logging
import os
import sys

import anthropic
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import TELEGRAM_BOT_TOKEN, API_GATEWAY_PORT, CLAUDE_API_KEY, CLAUDE_MODEL
from telegram_bot.price_monitor import (
    init_db,
    save_watched_item,
    get_watched_items,
    deactivate_watched_item,
    get_item_by_id,
    get_scheduler,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

API_BASE = os.getenv("API_GATEWAY_URL", f"http://localhost:{API_GATEWAY_PORT}")
_claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

_sessions: dict = {}


def _get_session(user_id: str) -> dict:
    if user_id not in _sessions:
        _sessions[user_id] = {
            "conversation_history": [],
            "last_search_results": [],
            "last_image_analysis": None,
            "last_image_b64": None,
            "filters": {},
        }
    return _sessions[user_id]


def _build_system_prompt(session: dict) -> str:
    results = session["last_search_results"]
    results_summary = "\n".join(
        f"  {i+1}. {(p.get('title') or '?')[:50]} — "
        f"S${p.get('price_sgd', 0):.0f} on {p.get('platform', '')}"
        for i, p in enumerate(results[:5])
    ) or "  None yet"

    return f"""You are PAFinder, a friendly personal shopping assistant on Telegram for Singapore shoppers.
You help users find clothing and products across Shopee SG, Lazada SG, and Google Shopping.

Personality: friendly and casual, like a knowledgeable friend. Occasionally use light Singlish (lah, can, lor) but don't overdo it.

Current session context:
- Last identified item: {session.get("last_image_analysis") or "Nothing searched yet"}
- Last search results (these are the numbered items the user refers to):
{results_summary}
- Active filters: {json.dumps(session.get("filters", {}))}

Based on the user's message, return a JSON object with this exact structure:
{{
  "action": one of [
    "add_to_cart",       // user wants to save an item
    "view_cart",         // user wants to see their cart
    "remove_from_cart",  // user wants to remove an item from cart
    "clear_cart",        // user wants to empty the cart
    "watch_price",       // user wants to track price drops on an item
    "list_watched",      // user wants to see what items they're tracking
    "search_cheaper",    // find cheaper alternatives to last results
    "search_specific",   // search with new / different keywords
    "filter_results",    // filter last results by budget / platform / brand
    "show_results",      // re-display the last search results
    "refine_search",     // search again with a style or attribute change
    "chitchat"           // greeting, question, help, or anything else
  ],
  "parameters": {{
    // add_to_cart:       {{"item_number": 1–5 or null (default first)}}
    // remove_from_cart:  {{"item_number": 1–5}}
    // watch_price:       {{"item_number": 1–5 or null (default first)}}
    // search_cheaper:    {{"max_price": number or null}}
    // search_specific:   {{"keywords": "string"}}
    // filter_results:    {{"budget_max": number or null, "platform": "string or null", "brand": "string or null"}}
    // refine_search:     {{"modification": "string describing the change"}}
    // chitchat:          {{"reply": "your friendly response as PAFinder"}}
    // all others:        {{}}
  }}
}}

Return ONLY valid JSON — no explanation, no markdown fences.

Examples:
"find something cheaper"    → {{"action":"search_cheaper","parameters":{{}}}}
"add the first one"         → {{"action":"add_to_cart","parameters":{{"item_number":1}}}}
"add number 3 to my cart"   → {{"action":"add_to_cart","parameters":{{"item_number":3}}}}
"only show Shopee"          → {{"action":"filter_results","parameters":{{"platform":"Shopee"}}}}
"budget under $50"          → {{"action":"filter_results","parameters":{{"budget_max":50}}}}
"search for Nike instead"   → {{"action":"search_specific","parameters":{{"keywords":"Nike"}}}}
"make it more streetwear"   → {{"action":"refine_search","parameters":{{"modification":"streetwear style"}}}}
"what's in my cart?"        → {{"action":"view_cart","parameters":{{}}}}
"clear my cart"             → {{"action":"clear_cart","parameters":{{}}}}
"remove item 2"             → {{"action":"remove_from_cart","parameters":{{"item_number":2}}}}
"watch this / alert me if price drops" → {{"action":"watch_price","parameters":{{"item_number":1}}}}
"track item 3"              → {{"action":"watch_price","parameters":{{"item_number":3}}}}
"what are you watching?"    → {{"action":"list_watched","parameters":{{}}}}
"hi!"                       → {{"action":"chitchat","parameters":{{"reply":"Hey! Send me a photo of any clothing item and I'll hunt down the best prices 👀"}}}}
"""


def _call_claude_intent(user_message: str, session: dict) -> dict:
    """Synchronous Claude call — run via asyncio.to_thread to avoid blocking."""
    recent_history = session["conversation_history"][-10:]
    try:
        resp = _claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            system=_build_system_prompt(session),
            messages=recent_history,
        )
        return json.loads(resp.content[0].text.strip())
    except Exception as exc:
        logger.warning(f"Claude intent parse failed: {exc}")
        return {
            "action": "chitchat",
            "parameters": {
                "reply": "Sorry, didn't quite catch that — try sending a photo or describing what you're looking for!"
            },
        }


def _format_results(products: list, header: str) -> str:
    if not products:
        return "Couldn't find anything — try different keywords or a clearer photo."
    lines = [header, ""]
    for i, p in enumerate(products[:5], 1):
        title = (p.get("title") or "Unknown")[:50]
        price = p.get("price_sgd", 0)
        platform = p.get("platform", "")
        rating = p.get("rating")
        url = p.get("purchase_url", "")
        rating_str = f"⭐ {rating:.1f}" if rating else ""
        line = f"*{i}. {title}*\n💰 S${price:.0f}  {rating_str}  🏪 {platform}"
        if url:
            line += f"\n[Buy Now]({url})"
        lines.append(line)
        lines.append("")
    return "\n".join(lines)


def _api_search(image_b64: str, user_id: str, additional_keywords: str = "") -> dict:
    try:
        r = requests.post(
            f"{API_BASE}/api/search",
            json={
                "image_base64": image_b64,
                "user_id": user_id,
                "additional_keywords": additional_keywords,
                "max_results": 5,
            },
            timeout=70,
        )
        return r.json()
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _cart_add(user_id: str, product: dict) -> bool:
    try:
        r = requests.post(
            f"{API_BASE}/api/cart/add",
            json={"user_id": user_id, "product": product},
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def _cart_get(user_id: str) -> dict:
    try:
        r = requests.get(f"{API_BASE}/api/cart/{user_id}", timeout=5)
        return r.json()
    except Exception:
        return {"items": [], "total_sgd": 0}


def _cart_clear(user_id: str) -> bool:
    try:
        r = requests.delete(f"{API_BASE}/api/cart/{user_id}", timeout=5)
        return r.ok
    except Exception:
        return False


async def _execute_action(action: dict, session: dict, user_id: str) -> str:
    act = action.get("action", "chitchat")
    params = action.get("parameters", {})

    if act == "chitchat":
        return params.get("reply", "Send me a photo to start searching! 📸")

    if act == "view_cart":
        data = _cart_get(user_id)
        items = data.get("items", [])
        if not items:
            return "Your cart is empty! Send me a photo of something you want to find 🛍️"
        lines = ["🛒 *Your Cart*\n"]
        for i, item in enumerate(items, 1):
            lines.append(
                f"{i}. *{(item.get('title') or '')[:50]}*\n"
                f"   💰 S${item.get('price_sgd', 0):.2f} · {item.get('platform', '')}"
            )
        lines.append(f"\n*Total: S${data.get('total_sgd', 0):.2f}*")
        return "\n".join(lines)

    if act == "clear_cart":
        _cart_clear(user_id)
        return "Cart cleared! 🗑️"

    if act == "watch_price":
        results = session.get("last_search_results", [])
        if not results:
            return "Send me a photo first so I know what to watch! 📸"
        idx = max(0, (params.get("item_number") or 1) - 1)
        idx = min(idx, len(results) - 1)
        item = results[idx]
        search_query = session.get("last_image_analysis", "")
        await asyncio.to_thread(save_watched_item, user_id, item, search_query)
        title = (item.get("title") or "Item")[:50]
        price = item.get("price_sgd", 0)
        platform = item.get("platform", "")
        return (
            f"👀 Watching *{title}*\n"
            f"📍 {platform} · Current price: S${price:.2f}\n\n"
            "I'll message you the moment the price drops! 🔔"
        )

    if act == "list_watched":
        items = await asyncio.to_thread(get_watched_items, user_id)
        if not items:
            return "You're not watching any items yet! Say _'watch this'_ after a search to track price drops 👀"
        lines = ["👀 *Items I'm watching for you:*\n"]
        for it in items:
            change = it["original_price"] - it["last_seen_price"]
            indicator = f"📉 S${change:.2f} cheaper!" if change > 0 else "→ No change yet"
            lines.append(
                f"• *{it['product_name'][:40]}*\n"
                f"  {it['platform']} | S${it['last_seen_price']:.2f} {indicator}"
            )
        lines.append("\n_I check prices every 4 hours and message you when they drop!_")
        return "\n".join(lines)

    if act == "remove_from_cart":
        data = _cart_get(user_id)
        items = data.get("items", [])
        idx = params.get("item_number", 1) - 1
        if 0 <= idx < len(items):
            item = items[idx]
            try:
                requests.delete(f"{API_BASE}/api/cart/item/{item['id']}", timeout=5)
                return f"Removed *{(item.get('title') or '')[:40]}* from your cart."
            except Exception:
                return "Couldn't remove that item — try again."
        return "That item number isn't in your cart!"

    if act == "add_to_cart":
        results = session.get("last_search_results", [])
        if not results:
            return "No results to add yet — send a photo first! 📸"
        idx = max(0, (params.get("item_number") or 1) - 1)
        idx = min(idx, len(results) - 1)
        product = results[idx]
        if _cart_add(user_id, product):
            title = (product.get("title") or "Item")[:40]
            price = product.get("price_sgd", 0)
            platform = product.get("platform", "")
            return (
                f"✅ Added to cart!\n*{title}*\n"
                f"💰 S${price:.2f} — {platform}\n\n"
                "Say _'show cart'_ to see everything."
            )
        return "Couldn't add to cart — try again."

    if act == "show_results":
        results = session.get("last_search_results", [])
        if not results:
            return "No results yet — send me a photo! 📸"
        return _format_results(results, "Here are your results:")

    if act == "filter_results":
        results = session.get("last_search_results", [])
        if not results:
            return "Nothing to filter — send me a photo first!"
        filtered = list(results)
        budget = params.get("budget_max")
        brand = params.get("brand")
        platform = params.get("platform")
        if budget:
            filtered = [p for p in filtered if p.get("price_sgd", 9999) <= budget]
            session["filters"]["budget_max"] = budget
        if brand:
            filtered = [p for p in filtered if brand.lower() in (p.get("title") or "").lower()]
            session["filters"]["brand"] = brand
        if platform:
            filtered = [p for p in filtered if platform.lower() in (p.get("platform") or "").lower()]
            session["filters"]["platform"] = platform
        if not filtered:
            return "No results match that filter — try relaxing the criteria?"
        session["last_search_results"] = filtered
        return _format_results(filtered, "Filtered results:")

    if act in ("search_cheaper", "search_specific", "refine_search"):
        if not session.get("last_image_b64"):
            return "Eh, send me a photo first lah, then I can search from there! 📸"

        if act == "search_cheaper":
            results = session.get("last_search_results", [])
            max_price = params.get("max_price")
            if not max_price and results:
                cheapest = min(p.get("price_sgd", 9999) for p in results)
                max_price = cheapest * 0.8
            keywords = f"affordable budget under {max_price:.0f} SGD" if max_price else "affordable budget"
            header = f"Cheaper alternatives{f' under S${max_price:.0f}' if max_price else ''}:"

        elif act == "search_specific":
            keywords = params.get("keywords", "")
            header = f"Searching with: *{keywords}*"

        else:  # refine_search
            keywords = params.get("modification", "")
            header = f"Refined: *{keywords}*"

        data = await asyncio.to_thread(
            _api_search, session["last_image_b64"], user_id, keywords
        )
        if not data.get("success"):
            return f"Search failed: {data.get('error', 'try again')}."
        products = data.get("products", [])

        if act == "search_cheaper" and max_price:
            products = [p for p in products if p.get("price_sgd", 9999) <= max_price]

        if not products:
            return "Couldn't find matching results — try different keywords."
        session["last_search_results"] = products
        session["filters"] = {}
        return _format_results(products, header)

    return "Not sure what to do — try sending a photo! 📸"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*FitFinder AI* — Your Shopping PA 🛍️\n\n"
        "Send me a photo of any clothing item and I'll find the best deals "
        "across Shopee, Lazada, and more.\n\n"
        "After a search you can just talk naturally:\n"
        "• _'find something cheaper'_\n"
        "• _'add the first one to my cart'_\n"
        "• _'only show Shopee results'_\n"
        "• _'make it more streetwear'_\n"
        "• _'what's in my cart?'_\n\n"
        "No commands needed — just chat!",
        parse_mode="Markdown",
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Natural language → Claude intent → execute action."""
    user_id = str(update.effective_user.id)
    user_message = update.message.text
    session = _get_session(user_id)

    session["conversation_history"].append({"role": "user", "content": user_message})

    await context.bot.send_chat_action(update.effective_chat.id, action="typing")

    action = await asyncio.to_thread(_call_claude_intent, user_message, session)
    response_text = await _execute_action(action, session, user_id)

    session["conversation_history"].append({"role": "assistant", "content": response_text})
    if len(session["conversation_history"]) > 20:  # stay within token budget
        session["conversation_history"] = session["conversation_history"][-20:]

    await update.message.reply_text(
        response_text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download photo → full search pipeline → display cards → update session."""
    user_id = str(update.effective_user.id)
    session = _get_session(user_id)

    status = await update.message.reply_text("Analysing image, searching platforms…")

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image_b64 = base64.b64encode(photo_bytes).decode("utf-8")

        r = requests.post(
            f"{API_BASE}/api/search",
            json={"image_base64": image_b64, "user_id": user_id, "max_results": 5},
            timeout=70,
        )
        result = r.json()
    except Exception as exc:
        await status.edit_text(f"Search failed: {exc}")
        return

    await status.delete()

    if not result.get("success"):
        await update.message.reply_text(f"Search error: {result.get('error', 'Unknown error')}")
        return

    products = result.get("products", [])
    if not products:
        await update.message.reply_text("No products found — try a clearer photo or different angle.")
        return

    analysis = result.get("analysis") or {}
    item_desc = (
        analysis.get("description")
        or f"{analysis.get('color', '')} {analysis.get('type', '')}".strip()
        or "this item"
    )
    session["last_search_results"] = products
    session["last_image_b64"] = image_b64
    session["last_image_analysis"] = item_desc
    session["filters"] = {}
    session["conversation_history"].append({
        "role": "user",
        "content": f"[User sent a photo — identified as: {item_desc}]",
    })

    # Summary header
    color = analysis.get("color", "")
    style = (analysis.get("style") or "").title()
    summary = f"Found: *{item_desc.title()}*" + (f" · {color} · {style}" if color or style else "")
    await update.message.reply_text(summary, parse_mode="Markdown")

    # Product cards
    for idx, p in enumerate(products[:5]):
        title = (p.get("title") or "Unknown")[:80]
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
            keyboard[0].append(InlineKeyboardButton("🔗 Buy Now", url=p["purchase_url"]))
        keyboard[0].append(InlineKeyboardButton("➕ Add to Cart", callback_data=f"cart|{idx}"))
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
                pass
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    session["conversation_history"].append({
        "role": "assistant",
        "content": f"Showed {len(products)} results.",
    })


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline Add to Cart button presses."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("cart|"):
        return

    user_id = str(query.from_user.id)
    session = _get_session(user_id)
    idx = int(query.data.split("|")[1])
    results = session.get("last_search_results", [])
    product = results[idx] if 0 <= idx < len(results) else None

    if not product:
        await query.answer("Product data expired — search again.", show_alert=True)
        return

    if _cart_add(user_id, product):
        title = (product.get("title") or "Item")[:40]
        await query.answer(f"Added: {title}", show_alert=False)
    else:
        await query.answer("Failed to add to cart.", show_alert=True)


async def handle_alert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses from proactive price-drop alert messages."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|", 1)
    if len(parts) != 2:
        return
    action_type, raw_id = parts

    try:
        item_id = int(raw_id)
    except ValueError:
        return

    if action_type == "alert_cart":
        item = await asyncio.to_thread(get_item_by_id, item_id)
        if not item:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("Couldn't find that item — it may have been removed.")
            return
        # Build a minimal product dict compatible with the cart API
        product = {
            "title": item["product_name"],
            "platform": item["platform"],
            "purchase_url": item["product_url"],
            "price_sgd": item["last_seen_price"],
        }
        user_id = str(query.from_user.id)
        if _cart_add(user_id, product):
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                f"Added *{item['product_name'][:50]}* to your cart at S${item['last_seen_price']:.2f} 🛒",
                parse_mode="Markdown",
            )
        else:
            await query.message.reply_text("Couldn't add to cart — try again.")

    elif action_type == "alert_stop":
        await asyncio.to_thread(deactivate_watched_item, item_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Got it, stopped watching that item 👍")


async def _post_init(application: Application) -> None:
    init_db()
    scheduler = get_scheduler(application.bot)
    scheduler.start()
    logger.info("Price monitor started — checks every 4 hours, first run in 30 s")


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("[TelegramBot] TELEGRAM_BOT_TOKEN not set — bot will not start.")
        return

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_alert_callback, pattern="^alert_"))  # must be before catch-all
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("[TelegramBot] Running (polling)…")
    app.run_polling()


if __name__ == "__main__":
    main()
