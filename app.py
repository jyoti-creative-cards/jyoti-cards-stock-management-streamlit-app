import streamlit as st
import os
import datetime
import pytz
import base64
import re
import sqlite3
import json
import urllib.request
import urllib.error
from typing import Optional
from urllib.parse import quote
from sqlalchemy import create_engine, text

# ---------- Page + Theme ----------
st.set_page_config(
    page_title="Jyoti Cards Stock",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "Jyoti Cards Stock Management System - 2026"
    }
)

# ---------- Constants ----------
tz = pytz.timezone('Asia/Kolkata')
DEFAULT_DB_PATHS = [
    os.environ.get("DB_PATH", ""),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "ops.db"),
    "/data/ops.db",
]
DB_PATH = next((p for p in DEFAULT_DB_PATHS if p and os.path.exists(p)), "/data/ops.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
phone_number = "07312506986"
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "").strip()
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID", "").strip()
META_API_VERSION = os.environ.get("META_API_VERSION", "v25.0").strip() or "v25.0"


def _normalize_wa_number(raw: str) -> str:
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10:
        return f"91{digits}"
    return digits


@st.cache_data(ttl=600)
def _resolve_meta_whatsapp_number(meta_phone_number_id: str, meta_access_token: str, meta_api_version: str) -> str:
    if not meta_phone_number_id or not meta_access_token:
        return ""
    url = f"https://graph.facebook.com/{meta_api_version}/{meta_phone_number_id}?fields=display_phone_number"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {meta_access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return _normalize_wa_number(payload.get("display_phone_number", ""))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return ""


# Use Meta phone-number-id bound WhatsApp number for customer chat links.
_meta_wa_number = _resolve_meta_whatsapp_number(META_PHONE_NUMBER_ID, META_ACCESS_TOKEN, META_API_VERSION)
_wa_default = (
    _meta_wa_number
    or _normalize_wa_number(os.environ.get("WA_ORDER_PHONE", ""))
    or _normalize_wa_number(os.environ.get("BUSINESS_WHATSAPP_NUMBER", ""))
    or "918952839355"
)
whatsapp_phone = _wa_default
wa_order_phone = _wa_default
logo_path = 'images/jyoti logo-1.png'

# ====== OFFER BANNER ======
OFFER_ENABLED = True
OFFER_TEXT = "🎉 New arrivals now available"

# ---------- Initialize Session State ----------
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'show_success' not in st.session_state:
    st.session_state.show_success = None

# ---------- Helper Functions ----------
def db_mtime() -> Optional[datetime.datetime]:
    if DATABASE_URL:
        return datetime.datetime.now(tz)
    try:
        ts = os.path.getmtime(DB_PATH)
        return datetime.datetime.fromtimestamp(ts, tz)
    except Exception:
        return None

def db_signature() -> tuple[float, int]:
    if DATABASE_URL:
        now = datetime.datetime.now(tz)
        return (float(int(now.timestamp() // 60)), 1)
    try:
        stt = os.stat(DB_PATH)
        return (stt.st_mtime, stt.st_size)
    except Exception:
        return (0.0, 0)

def get_base64_image(image_path: str) -> Optional[str]:
    if not os.path.exists(image_path):
        return None
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def as_clean_item_no(x) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    if not s:
        return ""
    m = re.search(r'(\d+)', s)
    if not m:
        return s
    return m.group(1)

def _digits(s: str) -> str:
    d = "".join(ch for ch in str(s) if ch.isdigit())
    return d.lstrip('0') or d

@st.cache_data(ttl=3600)
def get_image_path(item_no: str) -> Optional[str]:
    """Primary: images/{sku}.jpeg; fallback: recursive search by digits."""
    if not item_no:
        return None
    # 1) direct lookup per spec
    primary = os.path.join('images', f'{item_no}.jpeg')
    if os.path.exists(primary):
        return primary
    for ext in ['jpg', 'png', 'JPG', 'JPEG', 'PNG']:
        p = os.path.join('images', f'{item_no}.{ext}')
        if os.path.exists(p):
            return p
    want = _digits(item_no)
    if not want:
        return None
    exts = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    best, best_score = None, (999, 999999)
    if os.path.isdir('images'):
        for root, _, files in os.walk('images'):
            for fname in files:
                _, ext = os.path.splitext(fname)
                if ext not in exts:
                    continue
                full = os.path.join(root, fname)
                name_no_ext = os.path.splitext(fname)[0]
                name_digits = _digits(name_no_ext)
                score = None
                if name_digits == want and name_no_ext == item_no:
                    score = 0
                elif name_digits == want:
                    score = 1
                elif want and want in _digits(fname):
                    score = 2
                if score is not None:
                    cand = (score, len(full))
                    if cand < best_score:
                        best_score, best = cand, full
    return best

def get_stock_status(quantity, reorder_level):
    """EXACT rules per spec:
    - quantity == 0  -> Out of Stock
    - 0 < qty <= reorder_level -> Low Stock
    - quantity > reorder_level -> In Stock
    """
    try:
        q = int(quantity or 0)
    except Exception:
        q = 0
    try:
        r = int(reorder_level or 0)
    except Exception:
        r = 0
    if q <= 0:
        return 'Out of Stock', 0
    if q <= r:
        pct = min(100, int((q / max(r, 1)) * 100))
        return 'Low Stock', pct
    return 'In Stock', 100

# ---------- SQLite Data Pipeline ----------
@st.cache_data(show_spinner=False)
def load_inventory(_sig):
    """Load product+inventory rows from DB."""
    rows_out = []
    try:
        if DATABASE_URL:
            engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            query = text(
                """
                SELECT p.id,
                       p.sku,
                       p.name,
                       p.website_description AS description,
                       p.image_path,
                       p.category,
                       p.reorder_level,
                       COALESCE(i.quantity_available, 0) AS quantity
                FROM products p
                LEFT JOIN inventory i ON i.product_id = p.id
                WHERE COALESCE(p.active, TRUE) = TRUE
                """
            )
            with engine.connect() as conn:
                for r in conn.execute(query).mappings():
                    rows_out.append(dict(r))
        else:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT p.id,
                       p.sku,
                       p.name,
                       p.website_description AS description,
                       p.image_path,
                       p.category,
                       p.reorder_level,
                       COALESCE(i.quantity_available, 0) AS quantity
                FROM products p
                LEFT JOIN inventory i ON i.product_id = p.id
                WHERE COALESCE(p.active, 1) = 1
            """)
            for r in cur.fetchall():
                rows_out.append(dict(r))
            conn.close()
    except Exception as e:
        st.error(f"⚠️ Database error: {e}")
    return rows_out

def find_by_sku(rows, sku_query):
    """Match by exact SKU (cleaned digits or literal)."""
    if not sku_query:
        return None
    clean = as_clean_item_no(sku_query)
    for r in rows:
        if str(r.get('sku', '')).strip() == sku_query.strip():
            return r
        if as_clean_item_no(r.get('sku')) == clean:
            return r
    return None

def find_by_name(rows, name_query):
    q = (name_query or '').strip().lower()
    if not q:
        return []
    out = []
    for r in rows:
        name = str(r.get('name') or '').lower()
        if q in name:
            out.append(r)
    return out

# ---------- Load Data ----------
with st.spinner('⏳ Loading data...'):
    inv_rows = load_inventory(db_signature())

# ---------- Modern Styling ----------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Inter', 'Segoe UI', sans-serif; }
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .offer {
        margin: 1rem auto; padding: 14px 24px; border-radius: 16px;
        font-weight: 700; text-align: center; max-width: 680px; color: white;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4); font-size: 1.1rem;
        animation: slideDown 0.5s ease-out;
    }
    @keyframes slideDown { from { transform: translateY(-20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    .sticky-top {
        position: sticky; top: 0; z-index: 100; backdrop-filter: blur(10px);
        background: transparent; border-bottom: none; padding: 12px 0; box-shadow: none;
    }
    .title {
        font-size: 2.2em;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; text-align: center; margin: 0.5em 0 0.3em 0; letter-spacing: -0.5px;
    }
    .last-panel {
        margin: 0.3rem auto 0.5rem auto; padding: 6px 16px; border-radius: 999px;
        max-width: 350px; text-align: center; font-weight: 600; font-size: 0.85rem;
        color: #64748b; background: transparent; border: none;
    }
    .search-wrap { max-width: 680px; margin: 1rem auto; }
    .stTextInput input {
        border-radius: 14px !important; border: 2px solid #e2e8f0 !important;
        padding: 16px 20px !important; font-size: 1.1rem !important;
        font-weight: 500 !important; transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important;
    }
    .stTextInput input:focus {
        border-color: #667eea !important;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.2) !important;
        transform: translateY(-2px);
    }
    .success-msg {
        padding: 12px 20px; border-radius: 12px; margin: 1rem auto; max-width: 680px;
        text-align: center; font-weight: 600;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white;
        animation: slideDown 0.3s ease-out; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }
    .card {
        background: white; border-radius: 20px; padding: 24px; margin: 1.5rem auto;
        max-width: 720px; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        animation: fadeIn 0.4s ease-out;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    .item-caption { font-size: 1.1rem; color: #4a5568; font-weight: 600; }
    .status-container { margin: 16px 0; }
    .status-badge {
        display: inline-block; padding: 14px 20px; border-radius: 12px;
        font-weight: 700; font-size: 1rem; margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    .status-in { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; }
    .status-out { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; }
    .status-low {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white;
        animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }
        50% { transform: scale(1.05); box-shadow: 0 8px 24px rgba(245, 158, 11, 0.4); }
    }
    .progress-container {
        width: 100%; height: 8px; background: #e2e8f0;
        border-radius: 10px; overflow: hidden; margin: 8px 0;
    }
    .progress-bar { height: 100%; border-radius: 10px; transition: width 0.5s ease; }
    .progress-in { background: linear-gradient(90deg, #10b981, #059669); }
    .progress-low { background: linear-gradient(90deg, #f59e0b, #d97706); }
    .progress-out { background: linear-gradient(90deg, #ef4444, #dc2626); }
    .img-container {
        border-radius: 16px; overflow: hidden; margin: 20px 0;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    .img-container:hover { transform: scale(1.02); }
    .badge {
        display: inline-block; font-size: 0.8rem; font-weight: 700;
        padding: 4px 10px; border-radius: 8px;
    }
    .badge-in { background: #d1fae5; color: #065f46; }
    .badge-low { background: #fef3c7; color: #92400e; }
    .badge-out { background: #fee2e2; color: #991b1b; }
    .badge-unk { background: #e5e7eb; color: #374151; }
    .sticky-footer {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: rgba(255, 255, 255, 0.98); backdrop-filter: blur(10px);
        border-top: 1px solid rgba(0, 0, 0, 0.1);
        padding: 16px; z-index: 200; box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.05);
    }
    .footer-inner {
        max-width: 820px; margin: 0 auto; display: flex; gap: 12px;
        align-items: center; justify-content: center; flex-wrap: wrap;
    }
    .link-btn {
        display: inline-flex; gap: 8px; align-items: center; justify-content: center;
        text-decoration: none; border-radius: 12px; padding: 14px 24px;
        font-weight: 700; font-size: 1rem; transition: all 0.2s ease;
        min-width: 140px; border: none; position: relative;
    }
    .call-btn {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white;
        box-shadow: 8px 8px 16px rgba(59, 130, 246, 0.3), -8px -8px 16px rgba(255, 255, 255, 0.1);
    }
    .call-btn:hover { transform: translateY(-2px); }
    .wa-btn {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%); color: white;
        box-shadow: 8px 8px 16px rgba(37, 211, 102, 0.3), -8px -8px 16px rgba(255, 255, 255, 0.1);
    }
    .wa-btn:hover { transform: translateY(-2px); }
    .page-bottom-spacer { height: 90px; }
    @media (max-width: 768px) {
        .title { font-size: 1.8em; }
        .card { padding: 20px; margin: 1rem; }
        .status-badge { font-size: 0.95rem; padding: 12px 18px; }
        .link-btn { min-width: 120px; padding: 12px 20px; font-size: 0.95rem; width: 100%; }
        .footer-inner { flex-direction: column; gap: 10px; }
    }
    </style>
""", unsafe_allow_html=True)

# ---------- Success Message ----------
if st.session_state.show_success:
    st.markdown(f'<div class="success-msg">{st.session_state.show_success}</div>', unsafe_allow_html=True)
    st.session_state.show_success = None

# ---------- Offer Banner ----------
if OFFER_ENABLED and OFFER_TEXT:
    st.markdown(f'<div class="offer">{OFFER_TEXT}</div>', unsafe_allow_html=True)

# ---------- Header ----------
st.markdown('<div class="sticky-top">', unsafe_allow_html=True)
st.markdown('<h1 class="title">Jyoti Cards Stock Status</h1>', unsafe_allow_html=True)

last_update_time = db_mtime()
if last_update_time:
    st.markdown(
        f'<div class="last-panel">Last Updated: <b>{last_update_time.strftime("%d-%m-%Y %H:%M")}</b></div>',
        unsafe_allow_html=True
    )

st.markdown('<div class="search-wrap">', unsafe_allow_html=True)

col1, col2 = st.columns([5, 1])
with col1:
    item_no = st.text_input(
        "Search",
        value="",
        placeholder="🔍 आइटम नंबर या नाम यहाँ डालें",
        label_visibility="collapsed",
        key="item_no"
    ).strip().replace(".0", "")

with col2:
    if st.button("🔄", help="Reload data"):
        load_inventory.clear()
        get_image_path.clear()
        st.rerun()

st.markdown('</div></div>', unsafe_allow_html=True)

def render_product_card(product: dict):
    sku = str(product.get('sku') or '').strip()
    name = str(product.get('name') or '').strip()
    description = str(product.get('description') or '').strip()
    quantity = product.get('quantity', 0)
    reorder_level = product.get('reorder_level', 0)
    stock_status, percentage = get_stock_status(quantity, reorder_level)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="item-caption">आइटम नंबर: <b style="font-size: 1.3rem;">{sku}</b></div>',
        unsafe_allow_html=True
    )
    if name:
        st.markdown(f'<div style="color:#1e293b;font-weight:600;margin:6px 0;">{name}</div>', unsafe_allow_html=True)
    if description:
        st.markdown(f'<div style="color:#64748b;font-size:0.95rem;margin-bottom:10px;">{description}</div>', unsafe_allow_html=True)

    st.markdown('<div class="status-container">', unsafe_allow_html=True)
    if stock_status == 'In Stock':
        st.markdown('<div class="status-badge status-in">✅ यह आइटम स्टॉक में उपलब्ध है</div>', unsafe_allow_html=True)
    elif stock_status == 'Out of Stock':
        st.markdown('<div class="status-badge status-out">❌ यह आइटम स्टॉक में उपलब्ध नहीं है</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge status-low">⚠️ यह आइटम कम स्टॉक में है</div>', unsafe_allow_html=True)

    prog_cls = 'progress-in' if stock_status == 'In Stock' else ('progress-low' if stock_status == 'Low Stock' else 'progress-out')
    st.markdown(
        f'<div class="progress-container"><div class="progress-bar {prog_cls}" style="width:{percentage}%;"></div></div>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    img_path = get_image_path(sku)
    if img_path:
        st.markdown('<div class="img-container">', unsafe_allow_html=True)
        st.image(img_path, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<p style="text-align: center; color: #94a3b8; padding: 40px 0;">📷 इस आइटम के लिए कोई छवि उपलब्ध नहीं है</p>',
            unsafe_allow_html=True
        )

    wa_url = f"https://wa.me/{wa_order_phone}?text=" + quote(f"ORDER|SKU:{sku}|QTY:1")
    st.link_button("🛒 Order Now via WhatsApp", wa_url, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Main Content ----------
if item_no:
    clean_item = as_clean_item_no(item_no)

    if clean_item and clean_item not in st.session_state.search_history:
        st.session_state.search_history.insert(0, clean_item)
        st.session_state.search_history = st.session_state.search_history[:5]

    product = find_by_sku(inv_rows, item_no)

    if product:
        render_product_card(product)

        if get_stock_status(product.get('quantity', 0), product.get('reorder_level', 0))[0] in ('Out of Stock', 'Low Stock'):
            category = product.get('category')
            alts = [r for r in inv_rows
                    if r.get('category') == category
                    and r.get('sku') != product.get('sku')
                    and get_stock_status(r.get('quantity', 0), r.get('reorder_level', 0))[0] == 'In Stock']
            if alts:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("<h3 style='margin-top: 0;'>🔄 विकल्प (Alternatives)</h3>", unsafe_allow_html=True)
                for alt in alts[:3]:
                    alt_sku = str(alt.get('sku') or '')
                    alt_name = str(alt.get('name') or '')
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        ap = get_image_path(alt_sku)
                        if ap:
                            st.image(ap, use_container_width=True)
                    with col_b:
                        st.markdown(f"**{alt_sku}** — {alt_name}")
                        st.markdown('<span class="badge badge-in">In Stock</span>', unsafe_allow_html=True)
                        wu = f"https://wa.me/{wa_order_phone}?text=" + quote(f"ORDER|SKU:{alt_sku}|QTY:1")
                        st.link_button("Order Now", wu, key=f"alt_order_{alt_sku}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        by_name = find_by_name(inv_rows, item_no)
        if by_name:
            st.markdown(f'<div class="last-panel">Found {len(by_name)} match(es) by name</div>', unsafe_allow_html=True)
            for p in by_name[:10]:
                render_product_card(p)
        else:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(
                '<p style="text-align: center; color: #ef4444; font-size: 1.1rem; padding: 40px 0;">❌ कोई आइटम नहीं मिला</p>',
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

elif len(st.session_state.search_history) > 0:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3>🕐 हाल ही में खोजे गए आइटम</h3>', unsafe_allow_html=True)
    st.markdown('<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px;">', unsafe_allow_html=True)
    for hist_item in st.session_state.search_history:
        if st.button(f"#{hist_item}", key=f"hist_{hist_item}"):
            st.query_params["item"] = hist_item
            st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown('<div class="sticky-footer">', unsafe_allow_html=True)
st.markdown('<div class="footer-inner">', unsafe_allow_html=True)

call_url = f"tel:{phone_number}"
st.markdown(f'''
    <a href="{call_url}" class="link-btn call-btn">📞 Call</a>
''', unsafe_allow_html=True)

if item_no and item_no.strip():
    clean_item_for_wa = as_clean_item_no(item_no)
    wa_text = f"नमस्ते, मुझे {clean_item_for_wa} बुक करना है, Quantity__"
else:
    wa_text = "नमस्ते, मुझे स्टॉक की जानकारी चाहिए।"

wa_url = f"https://wa.me/{whatsapp_phone}?text={quote(wa_text)}"
st.markdown(f'''
    <a href="{wa_url}" target="_blank" class="link-btn wa-btn">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="white" style="margin-right: 6px;">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
        </svg>
        WhatsApp
    </a>
''', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)
st.markdown('<div class="page-bottom-spacer"></div>', unsafe_allow_html=True)

logo_b64 = get_base64_image(logo_path)
if logo_b64:
    st.markdown('<hr style="opacity:0.2; margin: 20px 0;">', unsafe_allow_html=True)
    st.markdown(
        f'<div style="text-align:center;"><img src="data:image/png;base64,{logo_b64}" style="max-width:200px; width:50%; height:auto; opacity: 0.8;"></div>',
        unsafe_allow_html=True
    )

st.markdown('<p style="text-align:center; color: #94a3b8; font-size: 0.85rem; margin: 20px 0;">Powered by Jyoti Cards © 2026</p>', unsafe_allow_html=True)
