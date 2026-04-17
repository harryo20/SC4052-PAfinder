
import io
import os

import requests
import streamlit as st
from PIL import Image

API_GATEWAY = os.getenv("API_GATEWAY_URL", "http://localhost:5000")

st.set_page_config(
    page_title="FitFinder AI — Smart Shopping PA",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main-title  { font-size:2.4rem; font-weight:700; text-align:center; color:#1a1a2e; }
.sub-title   { font-size:1.05rem; text-align:center; color:#666; margin-bottom:1.5rem; }
.analysis-box{
    background:#f0f7ff; border-left:4px solid #3498db;
    padding:.9rem 1rem; border-radius:0 8px 8px 0; margin:1rem 0;
}
.badge       { display:inline-block; padding:2px 9px; border-radius:12px;
               font-size:.75rem; font-weight:600; margin-right:4px; }
.b-best      { background:#27ae60; color:#fff; }
.b-great     { background:#2980b9; color:#fff; }
.b-similar   { background:#e67e22; color:#fff; }
.b-alt       { background:#95a5a6; color:#fff; }
.b-sg        { background:#c0392b; color:#fff; }
.price       { font-size:1.35rem; font-weight:700; color:#c0392b; }
</style>
""", unsafe_allow_html=True)


def _get(path: str, **kw):
    try:
        r = requests.get(f"{API_GATEWAY}{path}", timeout=6, **kw)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def _cart_get(user_id: str) -> dict:
    return _get(f"/api/cart/{user_id}")


def _cart_add(user_id: str, product: dict) -> bool:
    try:
        r = requests.post(
            f"{API_GATEWAY}/api/cart/add",
            json={"user_id": user_id, "product": product},
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def _cart_remove(item_id: int) -> bool:
    try:
        r = requests.delete(f"{API_GATEWAY}/api/cart/item/{item_id}", timeout=5)
        return r.ok
    except Exception:
        return False


def _cart_clear(user_id: str) -> bool:
    try:
        r = requests.delete(f"{API_GATEWAY}/api/cart/{user_id}", timeout=5)
        return r.ok
    except Exception:
        return False


def _post_search(image_bytes: bytes, user_id: str, keywords: str,
                 max_results: int, sort_by: str, max_price: float | None):
    files = {"image": ("product.jpg", io.BytesIO(image_bytes), "image/jpeg")}
    data  = {"user_id": user_id, "keywords": keywords,
             "max_results": str(max_results), "sort_by": sort_by}
    if max_price:
        data["max_price_sgd"] = str(max_price)
    r = requests.post(f"{API_GATEWAY}/api/search", files=files, data=data, timeout=70)
    try:
        return r.json()
    except Exception:
        r.raise_for_status()
        raise


_BADGE_CLASS = {
    "Best Match":   "b-best",
    "Great Value":  "b-great",
    "Similar Style":"b-similar",
    "Alternative":  "b-alt",
}


def _badge(label: str) -> str:
    cls = _BADGE_CLASS.get(label, "b-alt")
    return f'<span class="badge {cls}">{label}</span>'


def _render_product(p: dict, user_id: str = "default"):
    """Render a single product card."""
    with st.container():
        img_col, info_col = st.columns([1, 3], gap="medium")

        with img_col:
            if p.get("image_url"):
                try:
                    st.image(p["image_url"], width=130)
                except Exception:
                    st.markdown("🖼️")
            else:
                st.markdown("🖼️")

        with info_col:
            label = p.get("recommendation_label", "Alternative")
            sg_tag = ' <span class="badge b-sg">🇸🇬 SG</span>' if p.get("is_singapore") else ""
            st.markdown(
                f'{_badge(label)}{sg_tag}'
                f'<br><strong style="font-size:1rem">{p["title"]}</strong>'
                f'<br><span style="color:#666;font-size:.88rem">'
                f'{p["store_name"]} &middot; {p["platform"]}</span>'
                f'<br><span class="price">S${p["price_sgd"]:.2f}</span>',
                unsafe_allow_html=True,
            )

            extras = []
            if p.get("rating"):
                rev = f" ({p['review_count']} reviews)" if p.get("review_count") else ""
                extras.append(f"⭐ {p['rating']:.1f}{rev}")
            if p.get("shipping"):
                extras.append(f"🚚 {p['shipping']}")
            if extras:
                st.caption("  ·  ".join(extras))

            score = p.get("recommendation_score", 0)
            st.progress(score, text=f"Match: {score:.0%}")

            btn_col, cart_col = st.columns([1, 1])
            with btn_col:
                if p.get("purchase_url"):
                    st.link_button("🛒 Buy Now", p["purchase_url"])
            with cart_col:
                cart_key = f"cart_{p.get('id', hash(p['title']))}"
                if st.button("➕ Add to Cart", key=cart_key):
                    if _cart_add(user_id, p):
                        st.success("Added!")
                        st.rerun()
                    else:
                        st.error("Cart unavailable")
        st.divider()


with st.sidebar:
    st.markdown("### 👤 User")
    user_id = st.text_input("User ID", value="shopper_01",
                            help="Unique ID — personalises recommendations over time")
    st.divider()

    st.markdown("### 🔍 Search Options")
    max_results = st.slider("Max results", 5, 20, 10)
    sort_by = st.selectbox(
        "Sort by",
        ["similarity", "price", "rating"],
        format_func=lambda x: {"similarity": "Best Match", "price": "Lowest Price",
                                "rating": "Top Rated"}[x],
    )
    max_price = st.number_input("Max budget (SGD)", min_value=0.0, value=0.0, step=10.0,
                                help="0 = no limit")
    st.divider()

    st.markdown("### 📊 Your Stats")
    stats_data = _get(f"/api/stats/{user_id}").get("data", {})
    if stats_data.get("total_searches", 0):
        st.metric("Searches", stats_data["total_searches"])
        if stats_data.get("avg_price_sgd"):
            st.metric("Avg spend", f"S${stats_data['avg_price_sgd']:.0f}")
        for b in (stats_data.get("top_brands") or [])[:3]:
            st.caption(f"• {b['brand']} ({b['count']}×)")
    else:
        st.info("Upload an image to get started!")
    st.divider()

    st.markdown("### 🛒 Cart")
    cart_data = _cart_get(user_id)
    cart_count = cart_data.get("count", 0)
    cart_total = cart_data.get("total_sgd", 0.0)
    if cart_count:
        st.markdown(f"**{cart_count} item(s)** · S${cart_total:.2f}")
        with st.expander("View cart"):
            for item in cart_data.get("items", []):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{item['title'][:40]}**")
                    st.caption(f"{item.get('store_name','')} · S${item['price_sgd']:.2f}")
                    if item.get("purchase_url"):
                        st.link_button("Buy Now", item["purchase_url"], use_container_width=True)
                with c2:
                    if st.button("✕", key=f"rm_{item['id']}"):
                        _cart_remove(item["id"])
                        st.rerun()
                st.divider()
            if st.button("🗑 Clear cart", use_container_width=True):
                _cart_clear(user_id)
                st.rerun()
    else:
        st.caption("Cart is empty")
    st.divider()

    st.markdown("### ⚙️ Service Health")
    if st.button("Check services"):
        status = _get("/api/services/status")
        for name, info in (status.get("services") or {}).items():
            if info.get("status") == "ok":
                st.success(f"✅ {name}")
            else:
                st.error(f"❌ {name}")

    st.caption("CE/CZ4052 Cloud Computing  |  PA-as-a-Service Demo")


st.markdown('<div class="main-title">🛍️ FitFinder AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Personal Shopping Assistant · Find the best deals in Singapore</div>',
    unsafe_allow_html=True,
)

tab_search, tab_history, tab_prefs = st.tabs(["🔍 Find Items", "📜 History", "⚙️ Preferences"])


with tab_search:
    left, right = st.columns(2, gap="large")

    with left:
        st.subheader("📸 Upload a product photo")
        uploaded = st.file_uploader(
            "Drag & drop or click to upload",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
        if uploaded:
            st.image(Image.open(uploaded), caption="Uploaded image", use_container_width=True)

    with right:
        st.subheader("🔤 Refine your search")
        keywords = st.text_input(
            "Extra keywords (optional)",
            placeholder="e.g. 'Nike', 'slim fit under $50'",
        )
        st.markdown("""
        **Tips for Singapore shoppers**
        - Photos work best with a clear, single item on a plain background
        - All prices are displayed in **SGD**
        - Results prioritise Shopee SG, Lazada SG, Zalora, and Qoo10
        - Add brand names to the keywords field for more precise results
        """)
        go = st.button(
            "🔍  Find This Item",
            disabled=(uploaded is None),
            use_container_width=True,
            type="primary",
        )

    if go and uploaded:
        with st.spinner("🤖 Analysing image · Searching platforms · Comparing prices…"):
            try:
                result = _post_search(
                    image_bytes=uploaded.getvalue(),
                    user_id=user_id,
                    keywords=keywords,
                    max_results=max_results,
                    sort_by=sort_by,
                    max_price=max_price if max_price > 0 else None,
                )
                st.session_state["last_result"] = result
            except requests.exceptions.ConnectionError:
                st.error(
                    "❌ Cannot reach the API Gateway.  "
                    "Run `python start_all.py` (or `python start_all.py --mock` for demo mode)."
                )
                st.session_state["last_result"] = None
            except Exception as exc:
                st.error(f"❌ Search failed: {exc}")
                st.session_state["last_result"] = None

    if st.session_state.get("last_result"):
        result = st.session_state["last_result"]

        if result.get("success"):
            analysis = result.get("analysis", {})

            brand_str =f"Brand: **{analysis['brand']}**" if analysis.get("brand") else "No brand detected"
            st.markdown(
                f'<div class="analysis-box">'
                f'<strong>🤖 AI identified:</strong> '
                f'<strong>{(analysis.get("type") or "").title()}</strong> &mdash; '
                f'{analysis.get("color", "")} &middot; {(analysis.get("style") or "").title()}'
                f' &middot; {brand_str}<br>'
                f'<em>{analysis.get("description", "")}</em><br>'
                f'<span style="color:#888">Confidence: {analysis.get("confidence", 0):.0%}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            s = result.get("stats", {})
            if s:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Results found",  s.get("total_products", 0))
                c2.metric("Lowest price",  f"S${s.get('min_price_sgd', 0):.0f}")
                c3.metric("Average price", f"S${s.get('avg_price_sgd', 0):.0f}")
                c4.metric("Platforms",     len(s.get("platforms", [])))

            st.divider()
            products = result.get("products", [])
            if products:
                st.subheader(f"🛒 Top {len(products)} Recommendations")
                for p in products:
                    _render_product(p, user_id)
            else:
                st.warning("No products found. Try a clearer image or different keywords.")

        elif result.get("error"):
            st.error(f"Search error: {result['error']}")


with tab_history:
    st.subheader("📜 Recent Searches")
    history = _get(f"/api/history/{user_id}?limit=15").get("data", [])

    if history:
        for item in history:
            date = (item.get("searched_at") or "")[:10]
            with st.expander(f"🔍 {item.get('query', '—')}  ·  {date}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Type:** {item.get('item_type') or '—'}")
                    st.markdown(f"**Colour:** {item.get('item_color') or '—'}")
                    st.markdown(f"**Style:** {item.get('item_style') or '—'}")
                with c2:
                    st.markdown(f"**Brand:** {item.get('item_brand') or 'Not detected'}")
                    st.markdown(f"**Results:** {item.get('result_count', 0)}")
                    price = item.get("top_result_price_sgd")
                    if price:
                        st.markdown(f"**Top price:** S${price:.2f}")
    else:
        st.info("No history yet — upload an image to start searching!")


with tab_prefs:
    st.subheader("⚙️ Shopping Preferences")
    st.info(
        "Preferences are learned automatically from your search history, "
        "or set them manually below for immediate effect."
    )

    prefs = _get(f"/api/preferences/{user_id}").get("data", {})

    with st.form("prefs_form"):
        col1, col2 = st.columns(2)

        with col1:
            budget_val = float(prefs.get("max_budget_sgd") or 0)
            new_budget = st.number_input(
                "Maximum budget (SGD)",
                min_value=0.0, value=budget_val, step=10.0,
                help="Products above this price rank lower",
            )
            brands_str = ", ".join(prefs.get("preferred_brands") or [])
            new_brands = st.text_input(
                "Preferred brands (comma-separated)",
                value=brands_str,
                placeholder="Nike, Uniqlo, Zara",
            )

        with col2:
            style_options = ["casual", "formal", "sporty", "streetwear",
                             "business", "minimalist", "luxury", "vintage"]
            current_styles = [s for s in (prefs.get("preferred_styles") or []) if s in style_options]
            new_styles = st.multiselect("Preferred styles", style_options, default=current_styles)

            size_top = (prefs.get("size_info") or {}).get("top", "")
            size_bottom = (prefs.get("size_info") or {}).get("bottom", "")
            new_size_top    = st.text_input("Top size (e.g. M, L, XL)", value=size_top)
            new_size_bottom = st.text_input("Bottom size (e.g. 30x32)", value=size_bottom)

        if st.form_submit_button("💾 Save Preferences", type="primary"):
            try:
                payload = {
                    "max_budget_sgd":   new_budget if new_budget > 0 else None,
                    "preferred_brands": [b.strip() for b in new_brands.split(",") if b.strip()],
                    "preferred_styles": new_styles,
                    "size_info": {k: v for k, v in
                                  [("top", new_size_top), ("bottom", new_size_bottom)] if v},
                }
                r = requests.put(
                    f"{API_GATEWAY}/api/preferences/{user_id}",
                    json=payload, timeout=5,
                )
                if r.status_code == 200:
                    st.success("✅ Preferences saved!")
                    st.rerun()
                else:
                    st.error("Failed to save preferences.")
            except Exception as exc:
                st.error(f"Error: {exc}")

    if prefs.get("avg_budget_sgd"):
        st.divider()
        st.markdown("**📈 Learned from your search history:**")
        st.markdown(f"- Estimated budget range: up to **S${prefs['avg_budget_sgd']:.0f}**")
        if prefs.get("preferred_brands"):
            st.markdown(f"- Favourite brands: **{', '.join(prefs['preferred_brands'][:5])}**")
        if prefs.get("preferred_styles"):
            st.markdown(f"- Common styles: **{', '.join(prefs['preferred_styles'][:3])}**")
