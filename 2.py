import streamlit as st
import pandas as pd
import os
import datetime
import pytz
import base64
import re
from pathlib import Path

# ---------- Page Meta ----------
st.set_page_config(page_title="Jyoti Cards — Stock Status", layout="centered")

# ---------- Constants ----------
tz = pytz.timezone('Asia/Kolkata')
stk_sum_file = 'StkSum_new.xlsx'
rate_list_file = 'rate list merged.xlsx'
alternate_list_file = 'STOCK ALTERNATION LIST.xlsx'
condition_file = '1112.xlsx'
phone_number = "07312456565"
logo_path = 'static/jyoti logo-1.png'
call_icon_url = 'static/call_icon.png'

# Optional: quick debug switch (sidebar) to show matched image paths
DEBUG = st.sidebar.checkbox("Debug images", value=False)

# ---------- Small Helpers ----------
def safe_file_mtime(path: str):
    try:
        ts = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(ts, tz)
    except Exception:
        return None

def get_base64_image(image_path: str):
    if not os.path.exists(image_path):
        return None
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def as_clean_item_no(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    m = re.search(r'(\d+)', s)
    return m.group(1) if m else ""

# ---- Robust image finder (recursive, case-insensitive, tolerant names) ----
def _normalize_digits(s: str) -> str:
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits.lstrip('0') or digits

def get_image_path(item_no: str) -> str | None:
    """
    Searches under static/ (recursively) for an image that matches the item number.
    Handles names like:
      - static/12345.jpg
      - static/012345.JPG
      - static/images/12345 front.png
      - static/cards/item_12345-v2.jpeg
    Matching priority:
      0) exact digits match AND filename stem equals raw item_no
      1) exact digits match in filename (ignoring extra text)
      2) item digits appear as substring in full filename
    """
    if not item_no:
        return None

    want_raw = str(item_no).strip()
    want = _normalize_digits(want_raw)
    static_root = Path("static")
    if not static_root.exists():
        return None

    exts = {".jpg", ".jpeg", ".png"}
    candidates = []

    for p in static_root.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in exts:
            continue

        name_no_ext = p.stem  # filename without extension
        digits_in_name = _normalize_digits(name_no_ext)
        score = None

        # Highest priority: digits match AND literal stem equals the raw item_no
        if digits_in_name == want and name_no_ext == want_raw:
            score = 0
        # Next: digits match (ignoring extra text)
        elif digits_in_name == want:
            score = 1
        # Last: digits appear somewhere in the filename
        elif want and want in _normalize_digits(p.name):
            score = 2

        if score is not None:
            candidates.append((score, len(str(p)), str(p)))

    if not candidates:
        return None

    candidates.sort(key=lambda t: (t[0], t[1]))  # best score, then shortest path
    best = candidates[0][2]
    return best

def get_stock_status(quantity, condition_value):
    if pd.isna(quantity) or quantity == 0:
        return 'Out of Stock'
    if pd.isna(condition_value):
        return 'In Stock'
    return 'In Stock' if quantity > condition_value else 'Low Stock'

# ---------- Data Loaders ----------
@st.cache_data(show_spinner=False)
def load_frames():
    # StkSum: A, C -> ITEM NO., Quantity
    df_stk = pd.read_excel(stk_sum_file, usecols=[0, 2])
    df_stk = df_stk.iloc[7:].reset_index(drop=True)
    df_stk.columns = ['ITEM NO.', 'Quantity']
    df_stk['ITEM NO.'] = df_stk['ITEM NO.'].apply(as_clean_item_no)
    df_stk['Quantity'] = (
        df_stk['Quantity'].astype(str).str.replace(' pcs', '', regex=False)
    )
    df_stk['Quantity'] = pd.to_numeric(df_stk['Quantity'], errors='coerce').fillna(0) * 100
    df_stk['Quantity'] = df_stk['Quantity'].astype(int)

    # Rates
    df_rate = pd.read_excel(rate_list_file)
    df_rate = df_rate.iloc[3:].reset_index(drop=True)
    df_rate.columns = ['ITEM NO.', 'Rate']
    df_rate['ITEM NO.'] = df_rate['ITEM NO.'].apply(as_clean_item_no)
    df_rate['Rate'] = pd.to_numeric(df_rate['Rate'], errors='coerce').fillna(0.0)

    # Alternates
    df_alt = pd.read_excel(alternate_list_file)
    if 'ITEM NO.' not in df_alt.columns:
        df_alt = df_alt.rename(columns={df_alt.columns[0]: 'ITEM NO.'})
    for c in ['Alt1', 'Alt2', 'Alt3']:
        if c not in df_alt.columns:
            df_alt[c] = ""
    df_alt['ITEM NO.'] = df_alt['ITEM NO.'].apply(as_clean_item_no)
    for c in ['Alt1', 'Alt2', 'Alt3']:
        df_alt[c] = df_alt[c].apply(as_clean_item_no)

    # Condition
    df_cond = pd.read_excel(condition_file)
    df_cond.columns = ['ITEM NO.', 'CONDITION']
    df_cond['ITEM NO.'] = df_cond['ITEM NO.'].apply(as_clean_item_no)
    df_cond['CONDITION'] = pd.to_numeric(df_cond['CONDITION'], errors='coerce')

    return df_stk, df_rate, df_alt, df_cond

@st.cache_data(show_spinner=False)
def build_master_df():
    df_stk, df_rate, df_alt, df_cond = load_frames()
    master = (
        df_stk
        .merge(df_rate, on='ITEM NO.', how='left')
        .merge(df_alt, on='ITEM NO.', how='left')
        .merge(df_cond, on='ITEM NO.', how='left')
    )
    master['Rate'] = pd.to_numeric(master['Rate'], errors='coerce')
    master['CONDITION'] = pd.to_numeric(master['CONDITION'], errors='coerce')
    for c in ['Alt1', 'Alt2', 'Alt3']:
        master[c] = master[c].fillna("").astype(str)
    return master

master_df = build_master_df()
_, _, alt_df, _ = load_frames()

# ---------- Global Styles ----------
st.markdown(
    """
    <style>
      :root {
        --brand: #2563eb; /* Tailwind blue-600 */
        --brand-ink: #1e293b; /* slate-800 */
        --muted: #64748b; /* slate-500 */
        --card-bg: #ffffff;
        --soft: #f1f5f9; /* slate-100 */
        --success-bg: #ecfdf5; /* emerald-50 */
        --success-ink: #065f46;
        --warn-bg: #fffbeb; /* amber-50 */
        --warn-ink: #92400e;
        --danger-bg: #fef2f2; /* rose-50 */
        --danger-ink: #991b1b;
      }
      .site-wrap {
        max-width: 860px;
        margin: 0 auto;
        padding: 18px 16px 28px;
      }
      .hero {
        text-align: center;
        margin-top: 6px;
        margin-bottom: 6px;
      }
      .hero h1 {
        margin: 0;
        font-weight: 700;
        font-size: 34px;
        letter-spacing: 0.2px;
        color: var(--brand-ink);
      }
      .subtle {
        text-align:center;
        color: var(--muted);
        margin: 6px 0 18px;
        font-size: 14px;
      }
      .card {
        background: var(--card-bg);
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        margin: 10px 0 14px;
      }
      .field-label {
        display: block;
        font-size: 13px;
        color: var(--muted);
        margin-bottom: 6px;
      }
      .status-badge {
        display:inline-block;
        font-size: 12px;
        border-radius: 999px;
        padding: 6px 10px;
        font-weight: 600;
        letter-spacing: 0.3px;
      }
      .in-stock { background: var(--success-bg); color: var(--success-ink); border: 1px solid #bbf7d0; }
      .low-stock { background: var(--warn-bg); color: var(--warn-ink); border: 1px solid #fde68a; }
      .out-stock { background: var(--danger-bg); color: var(--danger-ink); border: 1px solid #fecaca; }
      .call-btn {
        display:inline-flex; align-items:center; gap:10px;
        text-decoration:none;
        border-radius: 12px;
        padding: 10px 14px;
        border: 1px solid #d1d5db;
      }
      .call-btn:hover { background: var(--soft); }
      .footer-note {
        text-align:center; color: var(--muted); font-size: 13px; margin-top: 12px;
      }
      footer {visibility:hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- TOP: Heading ----------
st.markdown('<div class="site-wrap">', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>Jyoti Cards — Stock Status</h1></div>', unsafe_allow_html=True)

# ---------- Last Updated ----------
last_update_time = safe_file_mtime(stk_sum_file)
if last_update_time:
    st.markdown(
        f'<div class="subtle">Last Updated: {last_update_time.strftime("%d-%m-%Y %H:%M")}</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown('<div class="subtle">Last Updated: N/A</div>', unsafe_allow_html=True)

# ---------- Search Bar (card) ----------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<label class="field-label">आइटम नंबर</label>', unsafe_allow_html=True)
    item_no = st.text_input(
        label="",
        placeholder="उदा. 12345",
        label_visibility="collapsed"
    ).strip().replace('.0', '')
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Call Button (separate card) ----------
with st.container():
    st.markdown('<div class="card" style="display:flex;justify-content:center;">', unsafe_allow_html=True)
    call_icon_b64 = get_base64_image(call_icon_url)
    if call_icon_b64:
        st.markdown(
            f'''
            <a href="tel:{phone_number}" class="call-btn">
              <img src="data:image/png;base64,{call_icon_b64}" width="20" height="20" alt="Call">Call Warehouse
            </a>
            ''',
            unsafe_allow_html=True
        )
    else:
        st.link_button("Call Warehouse", f"tel:{phone_number}")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Results ----------
def status_badge_html(status: str) -> str:
    if status == "In Stock":
        return '<span class="status-badge in-stock">IN STOCK</span>'
    if status == "Low Stock":
        return '<span class="status-badge low-stock">LOW STOCK</span>'
    return '<span class="status-badge out-stock">OUT OF STOCK</span>'

if item_no:
    clean_item = as_clean_item_no(item_no)
    item_row = master_df[master_df['ITEM NO.'] == clean_item]

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        if not item_row.empty:
            qty = pd.to_numeric(item_row['Quantity'].values[0], errors='coerce')
            cond = pd.to_numeric(item_row['CONDITION'].values[0], errors='coerce') if 'CONDITION' in item_row.columns else float('nan')
            rate = pd.to_numeric(item_row['Rate'].values[0], errors='coerce') if 'Rate' in item_row.columns else float('nan')
            status = get_stock_status(qty, cond)

            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;gap:10px;'>"
                f"<div><b>Item:</b> {clean_item}</div>"
                f"<div>{status_badge_html(status)}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

            st.markdown("---")
            cols = st.columns([1,1])
            with cols[0]:
                formatted_rate = "N/A" if pd.isna(rate) else f"₹ {rate:.2f}"
                st.markdown(f"**Rate:** {formatted_rate}")
                st.markdown(f"**Quantity:** {0 if pd.isna(qty) else int(qty)}")
                st.markdown(f"**Condition:** {'N/A' if pd.isna(cond) else int(cond)}")

            with cols[1]:
                img_path = get_image_path(clean_item)
                if DEBUG:
                    st.caption(f"Image path (main): {img_path or 'None'}")
                if img_path:
                    st.image(img_path, caption=f'Image • {clean_item}', use_container_width=True)
                else:
                    st.caption("No image available for this item.")

            # Alternatives only when OUT OF STOCK
            if status == "Out of Stock":
                st.markdown("### विकल्प (Alternatives)")
                alt_row = alt_df[alt_df['ITEM NO.'] == clean_item]
                if not alt_row.empty:
                    alt_candidates = [
                        as_clean_item_no(alt_row.iloc[0].get('Alt1', '')),
                        as_clean_item_no(alt_row.iloc[0].get('Alt2', '')),
                        as_clean_item_no(alt_row.iloc[0].get('Alt3', '')),
                    ]
                    # dedupe + remove empties + not same as main
                    seen = {clean_item}
                    alts = [a for a in alt_candidates if a and a not in seen and not (a in seen or seen.add(a))]

                    if alts:
                        for a in alts:
                            alt_master = master_df[master_df['ITEM NO.'] == a]
                            if alt_master.empty:
                                st.write(f"- {a}: सूची में विवरण उपलब्ध नहीं")
                                continue
                            a_qty = pd.to_numeric(alt_master['Quantity'].values[0], errors='coerce')
                            a_cond = pd.to_numeric(alt_master['CONDITION'].values[0], errors='coerce')
                            a_rate = pd.to_numeric(alt_master['Rate'].values[0], errors='coerce')
                            a_status = get_stock_status(a_qty, a_cond)
                            a_rate_fmt = "N/A" if pd.isna(a_rate) else f"₹ {a_rate:.2f}"
                            st.markdown(
                                f"- **{a}** — {status_badge_html(a_status)} • Rate: {a_rate_fmt}",
                                unsafe_allow_html=True
                            )
                            a_img = get_image_path(a)
                            if DEBUG:
                                st.caption(f"Image path (alt {a}): {a_img or 'None'}")
                            if a_img:
                                st.image(a_img, caption=f'Image • {a}', use_container_width=True)
                    else:
                        st.caption("इस आइटम के लिए कोई वैकल्पिक आइटम उपलब्ध नहीं हैं।")
                else:
                    st.caption("इस आइटम के लिए कोई वैकल्पिक सूची उपलब्ध नहीं है।")
        else:
            st.warning("यह आइटम उपलब्ध नहीं है।")
        st.markdown('</div>', unsafe_allow_html=True)

# ---------- Bottom Logo ----------
logo_b64 = get_base64_image(logo_path)
if logo_b64:
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="text-align:center;"><img src="data:image/png;base64,{logo_b64}" style="max-width:220px;opacity:0.95;"></div>',
        unsafe_allow_html=True
    )
st.markdown('<div class="footer-note">Powered by Jyoti Cards</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)  # .site-wrap
