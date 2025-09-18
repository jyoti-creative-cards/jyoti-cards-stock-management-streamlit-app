import streamlit as st
import pandas as pd
import os
import datetime
import pytz
import base64
import re
from urllib.parse import quote  # for WhatsApp message encoding

# ---------- Page + Theme ----------
st.set_page_config(page_title="Jyoti Cards Stock", layout="centered")

# ---------- Constants ----------
tz = pytz.timezone('Asia/Kolkata')
stk_sum_file = 'StkSum_new.xlsx'                     # Source for ITEM NO. + Qty
rate_list_file = 'rate list merged.xlsx'             # (Kept in pipeline but NOT shown on UI)
alternate_list_file = 'STOCK ALTERNATION LIST.xlsx'  # Source for Alt1/Alt2/Alt3
condition_file = '1112.xlsx'                         # Source for CONDITION
phone_number = "07312456565"                         # Call phone number
whatsapp_phone = "919754656565"                        # WhatsApp phone number (no + or spaces)
logo_path = 'static/jyoti logo-1.png'
call_icon_url = 'static/call_icon.png'
MASTER_DF_OUT = 'master_df.xlsx'                     # Latest merged sheet

# ====== OFFER BANNER SETTINGS (EDIT HERE) ======
OFFER_ENABLED = True
OFFER_TEXT = "Today’s Offer — 5% off"
# ==============================================

# ---------- Helpers ----------
def safe_file_mtime(path: str) -> datetime.datetime | None:
    try:
        ts = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(ts, tz)
    except Exception:
        return None

def file_mtime_num(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0.0

def get_base64_image(image_path: str) -> str | None:
    if not os.path.exists(image_path):
        return None
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def as_clean_item_no(x) -> str:
    """
    Normalize item number to a plain numeric string, stripping any .0, spaces, or text.
    """
    if pd.isna(x):
        return ""
    s = str(x).strip()
    m = re.search(r'(\d+)', s)
    if not m:
        return ""
    return m.group(1)

def _digits(s: str) -> str:
    """Keep only digits and drop leading zeros for robust comparison."""
    d = "".join(ch for ch in str(s) if ch.isdigit())
    return d.lstrip('0') or d

def get_image_path(item_no: str) -> str | None:
    """
    1) Try static/{item_no}.{ext}
    2) Recursively search under static/ and match by digits of item_no.
    """
    if not item_no:
        return None

    want = _digits(item_no)
    if not want:
        return None

    for ext in ['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG']:
        p = os.path.join('static', f'{item_no}.{ext}')
        if os.path.exists(p):
            return p

    exts = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    best = None
    best_score = (999, 999999)

    for root, _, files in os.walk('static'):
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
                cand_score = (score, len(full))
                if cand_score < best_score:
                    best_score = cand_score
                    best = full

    return best

def get_stock_status(quantity, condition_value):
    if pd.isna(quantity) or quantity == 0:
        return 'Out of Stock'
    if pd.isna(condition_value):
        return 'In Stock'
    return 'In Stock' if quantity > condition_value else 'Low Stock'

# ---------- Data pipeline (auto-rebuild when any file changes) ----------
@st.cache_data(show_spinner=False)
def build_master_df(_stk_m, _rate_m, _alt_m, _cond_m):
    # StkSum (ITEM NO., Quantity)
    df_stk_sum = pd.read_excel(stk_sum_file, usecols=[0, 2])
    df_stk_sum = df_stk_sum.iloc[7:].reset_index(drop=True)
    df_stk_sum.columns = ['ITEM NO.', 'Quantity']
    df_stk_sum['ITEM NO.'] = df_stk_sum['ITEM NO.'].apply(as_clean_item_no)
    df_stk_sum['Quantity'] = (
        df_stk_sum['Quantity'].astype(str).str.replace(' pcs', '', regex=False)
    )
    df_stk_sum['Quantity'] = pd.to_numeric(df_stk_sum['Quantity'], errors='coerce').fillna(0) * 100
    df_stk_sum['Quantity'] = df_stk_sum['Quantity'].astype(int)

    # Rate list (kept but not displayed)
    df_rate_list = pd.read_excel(rate_list_file)
    df_rate_list = df_rate_list.iloc[3:].reset_index(drop=True)
    df_rate_list.columns = ['ITEM NO.', 'Rate']
    df_rate_list['ITEM NO.'] = df_rate_list['ITEM NO.'].apply(as_clean_item_no)
    df_rate_list['Rate'] = pd.to_numeric(df_rate_list['Rate'], errors='coerce').fillna(0.0)

    # Alternate list
    df_alt = pd.read_excel(alternate_list_file)
    expected_cols = ['ITEM NO.', 'Alt1', 'Alt2', 'Alt3']
    if any(c not in df_alt.columns for c in expected_cols):
        df_alt = df_alt.rename(columns={df_alt.columns[0]: 'ITEM NO.'})
        for c in ['Alt1', 'Alt2', 'Alt3']:
            if c not in df_alt.columns:
                df_alt[c] = ""
    df_alt['ITEM NO.'] = df_alt['ITEM NO.'].apply(as_clean_item_no)
    for c in ['Alt1', 'Alt2', 'Alt3']:
        df_alt[c] = df_alt[c].apply(as_clean_item_no)

    # Condition sheet
    df_condition = pd.read_excel(condition_file)
    df_condition.columns = ['ITEM NO.', 'CONDITION']
    df_condition['ITEM NO.'] = df_condition['ITEM NO.'].apply(as_clean_item_no)
    df_condition['CONDITION'] = pd.to_numeric(df_condition['CONDITION'], errors='coerce')

    # Merge → master
    master = (
        df_stk_sum
        .merge(df_rate_list, on='ITEM NO.', how='left')   # rate merged but not shown
        .merge(df_alt, on='ITEM NO.', how='left')
        .merge(df_condition, on='ITEM NO.', how='left')
    )

    # Types & blanks
    master['Rate'] = pd.to_numeric(master['Rate'], errors='coerce')
    master['CONDITION'] = pd.to_numeric(master['CONDITION'], errors='coerce')
    for c in ['Alt1', 'Alt2', 'Alt3']:
        if c not in master.columns:
            master[c] = ""
        master[c] = master[c].fillna("").astype(str)

    try:
        master.to_excel(MASTER_DF_OUT, index=False)
    except Exception:
        pass

    return master

# ---------- Compute mtimes & optional Reload ----------
stk_m = file_mtime_num(stk_sum_file)
rate_m = file_mtime_num(rate_list_file)
alt_m  = file_mtime_num(alternate_list_file)
cond_m = file_mtime_num(condition_file)

topbar = st.container()
with topbar:
    cols = st.columns([1, 6])
    with cols[0]:
        if st.button("🔄 Reload data"):
            build_master_df.clear()

# Build master & alt view
master_df = build_master_df(stk_m, rate_m, alt_m, cond_m)
alt_df = master_df[['ITEM NO.', 'Alt1', 'Alt2', 'Alt3']].copy()

# ---------- Styling ----------
st.markdown(
    """
    <style>
      .stApp { background-color: #ffffff; }

      /* Offer banner */
      .offer {
          margin: 0.2rem auto 0.4rem auto;
          padding: 8px 14px;
          border-radius: 999px;
          font-weight: 800;
          text-align: center;
          max-width: 520px;
          color: white;
          background: linear-gradient(90deg, #ef4444, #f59e0b, #22c55e, #3b82f6, #a855f7);
          background-size: 300% 300%;
          animation: moveGradient 6s ease infinite;
          box-shadow: 0 6px 16px rgba(0,0,0,0.10);
          letter-spacing: 0.3px;
      }
      @keyframes moveGradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
      }

      /* Sticky header container */
      .sticky-top {
          position: sticky;
          top: 0;
          z-index: 100;
          backdrop-filter: saturate(180%) blur(6px);
          background: rgba(255,255,255,0.92);
          border-bottom: 1px solid #f1f5f9;
          padding-bottom: 8px;
      }

      .title { font-size: 2.0em; color: #1f3a8a; font-weight: 700; text-align: center; margin: 0.2em 0 0 0; }
      .last-updated { text-align:center; color:#475569; margin: 0 0 0.6rem 0; font-size: 0.92rem; }
      .search-wrap { max-width: 680px; margin: 0.2rem auto 0.6rem auto; }

      .card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px 18px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
      .status-badge { border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; font-weight: 600; }
      .status-in { background-color:#d4edda; color:#155724; }
      .status-out { background-color:#f8d7da; color:#721c24; }
      .status-low { background-color:#fff3cd; color:#856404; }
      .result { font-size: 1.05rem; }

      .cta-row { margin-top: 10px; }
      .call-cta { border: 1px solid #fecaca; background: #fee2e2; color: #991b1b; padding: 10px 14px; border-radius: 12px; display: flex; align-items: center; gap: 12px; justify-content: center; font-weight: 600; }
      .link-btn { display:inline-flex; gap:8px; align-items:center; text-decoration:none; border:1px solid #ddd; border-radius:10px; padding:8px 12px; background:#ffffff; font-weight:600; }
      .wa-btn { border-color:#86efac; }
      .wa-btn:hover { background:#ecfeff; }
      .call-btn:hover { background:#f8fafc; }

      footer { visibility: hidden; } /* hide default Streamlit footer */
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Offer banner (top, not sticky) ----------
if OFFER_ENABLED and OFFER_TEXT:
    st.markdown(f'<div class="offer">{OFFER_TEXT}</div>', unsafe_allow_html=True)

# ---------- Sticky: Heading + Last Updated + Search ----------
st.markdown('<div class="sticky-top">', unsafe_allow_html=True)
st.markdown('<h1 class="title">Jyoti Cards Stock Status</h1>', unsafe_allow_html=True)
last_update_time = safe_file_mtime(stk_sum_file)
if last_update_time:
    st.markdown(
        f'<p class="last-updated">Last Updated: {last_update_time.strftime("%d-%m-%Y %H:%M")}</p>',
        unsafe_allow_html=True
    )
st.markdown('<div class="search-wrap">', unsafe_allow_html=True)
item_no = st.text_input('🔍 कृपया आइटम नंबर यहाँ डालें', value="", placeholder="उदा. 12345").strip().replace('.0', '')
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)  # end sticky

# ---------- Main Output Card ----------
with st.container():
    if item_no:
        clean_item = as_clean_item_no(item_no)
        item_row = master_df[master_df['ITEM NO.'] == clean_item]

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("Item number entered:", clean_item)

        if not item_row.empty:
            quantity = pd.to_numeric(item_row['Quantity'].values[0], errors='coerce')
            condition_value = pd.to_numeric(item_row['CONDITION'].values[0], errors='coerce') if 'CONDITION' in item_row.columns else float('nan')

            stock_status = get_stock_status(quantity, condition_value)

            # STATUS ONLY (no rate)
            if stock_status == 'In Stock':
                st.markdown('<div class="status-badge status-in">यह आइटम स्टॉक में है (कृपया गोदाम पर बुकिंग के लिए कॉल करें)</div>', unsafe_allow_html=True)
            elif stock_status == 'Out of Stock':
                st.markdown('<div class="status-badge status-out">यह आइटम स्टॉक में <b>उपलब्ध नहीं</b> है। नीचे दिए गए विकल्प देखें।</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-badge status-low">यह आइटम का स्टॉक <b>कम</b> है, कृपया शीघ्र गोदाम पर बुक करें।</div>', unsafe_allow_html=True)

            # Image
            img_path = get_image_path(clean_item)
            if img_path:
                st.image(img_path, caption=f'Image of {clean_item}', use_container_width=True)
            else:
                st.markdown('<p class="result">इस आइटम नंबर के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)

            # Alternatives (only for Out of Stock)
            if stock_status == 'Out of Stock':
                st.markdown("<h3>विकल्प</h3>", unsafe_allow_html=True)
                alt_row = alt_df[alt_df['ITEM NO.'] == clean_item]
                if not alt_row.empty:
                    alt_candidates = [
                        as_clean_item_no(alt_row.iloc[0].get('Alt1', '')),
                        as_clean_item_no(alt_row.iloc[0].get('Alt2', '')),
                        as_clean_item_no(alt_row.iloc[0].get('Alt3', '')),
                    ]
                    seen = set([clean_item])
                    alt_candidates = [a for a in alt_candidates if a and a not in seen and not (a in seen or seen.add(a))]

                    if alt_candidates:
                        for alt_item in alt_candidates:
                            alt_master_row = master_df[master_df['ITEM NO.'] == alt_item]
                            if not alt_master_row.empty:
                                alt_qty = pd.to_numeric(alt_master_row['Quantity'].values[0], errors='coerce')
                                alt_cond = pd.to_numeric(alt_master_row['CONDITION'].values[0], errors='coerce') if 'CONDITION' in alt_master_row.columns else float('nan')
                                alt_status = get_stock_status(alt_qty, alt_cond)

                                if alt_status == 'In Stock':
                                    st.markdown(
                                        f'<p class="result">वैकल्पिक आइटम: <b>{alt_item}</b> — <b>स्टॉक में उपलब्ध</b></p>',
                                        unsafe_allow_html=True
                                    )
                                    alt_img = get_image_path(alt_item)
                                    if alt_img:
                                        st.image(alt_img, caption=f'Image of {alt_item}', use_container_width=True)
                                    else:
                                        st.markdown(f'<p class="result">{alt_item} के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
                                else:
                                    st.markdown(
                                        f'<p class="result">वैकल्पिक आइटम: <b>{alt_item}</b> — स्टॉक में उपलब्ध नहीं है।</p>',
                                        unsafe_allow_html=True
                                    )
                            else:
                                st.markdown(f'<p class="result">वैकल्पिक आइटम <b>{alt_item}</b> उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
                    else:
                        st.markdown('<p class="result">इस आइटम के लिए कोई वैकल्पिक आइटम उपलब्ध नहीं हैं।</p>', unsafe_allow_html=True)
                else:
                    st.markdown('<p class="result">इस आइटम के लिए कोई वैकल्पिक सूची उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="result">मुख्य आइटम उपलब्ध नहीं है।</p>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card"><p class="result">कृपया एक आइटम नंबर दर्ज करें</p></div>', unsafe_allow_html=True)

# ---------- Call & WhatsApp section ----------
with st.container():
    st.markdown('<div class="cta-row"></div>', unsafe_allow_html=True)
    call_cols = st.columns([3, 1, 1])  # text | call | whatsapp
    with call_cols[0]:
        st.markdown(
            '<div class="call-cta">📞 ऑर्डर बुक करने या अधिक जानकारी के लिए संपर्क करें</div>',
            unsafe_allow_html=True
        )
    with call_cols[1]:
        # Call button
        if os.path.exists(call_icon_url):
            call_icon_base64 = get_base64_image(call_icon_url)
            if call_icon_base64:
                st.markdown(
                    f'''
                    <div style="display:flex; align-items:center; height:100%; justify-content:center;">
                        <a href="tel:{phone_number}" class="link-btn call-btn">
                            <img src="data:image/png;base64,{call_icon_base64}" width="18" height="18" alt="Call"> Call
                        </a>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
        else:
            st.link_button("Call", f"tel:{phone_number}")

    with call_cols[2]:
        # WhatsApp button (prefilled text in Hindi with item number if available)
        if 'item_no' in locals() and item_no.strip():
            clean_item_for_wa = as_clean_item_no(item_no)
            wa_text = f"नमस्ते, मुझे आइटम {clean_item_for_wa} की अधिक जानकारी चाहिए।"
        else:
            wa_text = "नमस्ते, मुझे स्टॉक की जानकारी चाहिए।"
        wa_url = f"https://wa.me/{whatsapp_phone}?text={quote(wa_text)}"
        st.markdown(
            f'''
            <div style="display:flex; align-items:center; height:100%; justify-content:center;">
                <a href="{wa_url}" target="_blank" class="link-btn wa-btn">💬 WhatsApp</a>
            </div>
            ''',
            unsafe_allow_html=True
        )

# ---------- Bottom: Logo ----------
logo_b64 = get_base64_image(logo_path)
if logo_b64:
    st.markdown('<hr style="opacity:0.2; margin-top:16px;">', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{logo_b64}" style="max-width:220px;"></div>', unsafe_allow_html=True)

st.markdown('<p class="result" style="text-align:center; opacity:0.7;">Powered by Jyoti Cards</p>', unsafe_allow_html=True)
