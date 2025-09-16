import streamlit as st
import pandas as pd
import os
import datetime
import pytz
import base64
import re

# ---------- Page + Theme ----------
st.set_page_config(page_title="Jyoti Cards Stock", layout="centered")

# ---------- Constants ----------
tz = pytz.timezone('Asia/Kolkata')
stk_sum_file = 'StkSum_new.xlsx'
rate_list_file = 'rate list merged.xlsx'
alternate_list_file = 'STOCK ALTERNATION LIST.xlsx'
condition_file = '1112.xlsx'
phone_number = "07312456565"
logo_path = 'static/jyoti logo-1.png'
call_icon_url = 'static/call_icon.png'

# ---------- Helpers ----------
def safe_file_mtime(path: str) -> datetime.datetime | None:
    try:
        ts = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(ts, tz)
    except Exception:
        return None

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
    return d.lstrip('0') or d  # if all zeros, keep as-is

def get_image_path(item_no: str) -> str | None:
    """
    Robust image finder:
    1) Try static/{item_no}.{ext} (jpg/jpeg/png)
    2) Recursively search under static/ and match by digits of item_no
       so files like 'item_012345 Front.JPG' or 'images/12345.png' will match '12345'.
    Returns the first best match found.
    """
    if not item_no:
        return None

    want = _digits(item_no)
    if not want:
        return None

    # 1) Direct exact paths in root 'static'
    for ext in ['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG']:
        p = os.path.join('static', f'{item_no}.{ext}')
        if os.path.exists(p):
            return p

    # 2) Recursive search
    exts = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    best = None
    best_score = (999, 999999)  # (match_score, path_length)

    for root, _, files in os.walk('static'):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext not in exts:
                continue
            full = os.path.join(root, fname)
            name_no_ext = os.path.splitext(fname)[0]
            name_digits = _digits(name_no_ext)

            # Scoring: lower is better
            # 0: digits match AND stem equals item_no exactly
            # 1: digits match
            # 2: want digits is substring of full filename digits
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
    """
    Out of Stock: quantity is NaN or 0
    In Stock    : condition is NaN OR quantity > condition
    Low Stock   : otherwise (quantity <= condition and quantity > 0)
    """
    if pd.isna(quantity) or quantity == 0:
        return 'Out of Stock'
    if pd.isna(condition_value):
        return 'In Stock'
    return 'In Stock' if quantity > condition_value else 'Low Stock'

@st.cache_data(show_spinner=False)
def load_frames():
    # StkSum A,C (0,2)
    df_stk_sum = pd.read_excel(stk_sum_file, usecols=[0, 2])
    df_stk_sum = df_stk_sum.iloc[7:].reset_index(drop=True)
    df_stk_sum.columns = ['ITEM NO.', 'Quantity']
    df_stk_sum['ITEM NO.'] = df_stk_sum['ITEM NO.'].apply(as_clean_item_no)
    df_stk_sum['Quantity'] = (
        df_stk_sum['Quantity'].astype(str)
        .str.replace(' pcs', '', regex=False)
    )
    df_stk_sum['Quantity'] = pd.to_numeric(df_stk_sum['Quantity'], errors='coerce').fillna(0) * 100
    df_stk_sum['Quantity'] = df_stk_sum['Quantity'].astype(int)

    # Rate list
    df_rate_list = pd.read_excel(rate_list_file)
    df_rate_list = df_rate_list.iloc[3:].reset_index(drop=True)
    df_rate_list.columns = ['ITEM NO.', 'Rate']
    df_rate_list['ITEM NO.'] = df_rate_list['ITEM NO.'].apply(as_clean_item_no)
    df_rate_list['Rate'] = pd.to_numeric(df_rate_list['Rate'], errors='coerce').fillna(0.0)

    # Alternate list
    df_alt = pd.read_excel(alternate_list_file)
    # Expecting columns: ITEM NO., Alt1, Alt2, Alt3
    expected_cols = ['ITEM NO.', 'Alt1', 'Alt2', 'Alt3']
    missing = [c for c in expected_cols if c not in df_alt.columns]
    if missing:
        # try to coerce to expected naming if possible
        df_alt = df_alt.rename(columns={df_alt.columns[0]: 'ITEM NO.'})
        # ensure missing alts exist
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

    return df_stk_sum, df_rate_list, df_alt, df_condition

@st.cache_data(show_spinner=False)
def build_master_df():
    df_stk_sum, df_rate_list, df_alt, df_condition = load_frames()
    master = (
        df_stk_sum
        .merge(df_rate_list, on='ITEM NO.', how='left')
        .merge(df_alt, on='ITEM NO.', how='left')
        .merge(df_condition, on='ITEM NO.', how='left')
    )
    # Clean types
    master['Rate'] = pd.to_numeric(master['Rate'], errors='coerce')
    master['CONDITION'] = pd.to_numeric(master['CONDITION'], errors='coerce')
    for c in ['Alt1', 'Alt2', 'Alt3']:
        master[c] = master[c].fillna("").astype(str)
    return master

# ---------- Data ----------
master_df = build_master_df()
_, _, alt_df, _ = load_frames()  # for quick alt lookups without re-reading files

# ---------- Styling ----------
st.markdown(
    """
    <style>
    .main { background-color: #ffffff; }
    .stApp { background-color: #ffffff; }
    .title { font-size: 2.2em; color: #4e8cff; font-weight: 600; text-align: center; margin-top: 0.4em; }
    .last-updated { text-align:center; color:#555; margin-top: 0.25rem; }
    .result { font-size: 1.05rem; }
    .call-link { display:inline-flex; gap:8px; align-items:center; text-decoration:none; border:1px solid #ddd; border-radius:10px; padding:6px 10px; }
    footer { visibility: hidden; } /* hide default Streamlit footer */
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- TOP: Search Input FIRST ----------
item_no = st.text_input('🔍 कृपया आइटम नंबर यहां डालें', value="", placeholder="उदा. 12345").strip().replace('.0', '')

# ---------- Title + Last Updated ----------
last_update_time = safe_file_mtime(stk_sum_file)
st.markdown('<h1 class="title">Jyoti Cards Stock Status</h1>', unsafe_allow_html=True)
if last_update_time:
    st.markdown(
        f'<p class="last-updated">Last Updated: {last_update_time.strftime("%d-%m-%Y %H:%M")}</p>',
        unsafe_allow_html=True
    )

# ---------- Optional Call Button ----------
if os.path.exists(call_icon_url):
    call_icon_base64 = get_base64_image(call_icon_url)
    if call_icon_base64:
        st.markdown(
            f'''
            <a href="tel:{phone_number}" class="call-link">
                <img src="data:image/png;base64,{call_icon_base64}" width="20" height="20" alt="Call Icon">Call
            </a>
            ''',
            unsafe_allow_html=True
        )

# ---------- Main Logic ----------
if item_no:
    clean_item = as_clean_item_no(item_no)
    st.write("Item number entered:", clean_item)

    item_row = master_df[master_df['ITEM NO.'] == clean_item]
    if not item_row.empty:
        quantity = pd.to_numeric(item_row['Quantity'].values[0], errors='coerce')
        condition_value = pd.to_numeric(item_row['CONDITION'].values[0], errors='coerce') if 'CONDITION' in item_row.columns else float('nan')
        rate = pd.to_numeric(item_row['Rate'].values[0], errors='coerce') if 'Rate' in item_row.columns else float('nan')

        stock_status = get_stock_status(quantity, condition_value)

        # Status banners
        if stock_status == 'In Stock':
            st.markdown(
                '<div style="background-color:#d4edda; padding:10px; border-radius:8px;">'
                '<p style="color:#155724; margin:0;">यह आइटम स्टॉक में है (कृपया गोदाम पर बुकिंग के लिए कॉल करें)</p></div>',
                unsafe_allow_html=True
            )
        elif stock_status == 'Out of Stock':
            st.markdown(
                '<div style="background-color:#f8d7da; padding:10px; border-radius:8px;">'
                '<p style="color:#721c24; margin:0;">यह आइटम स्टॉक में <b>उपलब्ध नहीं</b> है। नीचे दिए गए विकल्प देखें।</p></div>',
                unsafe_allow_html=True
            )
        else:  # Low Stock
            st.markdown(
                '<div style="background-color:#fff3cd; padding:10px; border-radius:8px;">'
                '<p style="color:#856404; margin:0;">यह आइटम का स्टॉक <b>कम</b> है, कृपया शीघ्र गोदाम पर बुक करें।</p></div>',
                unsafe_allow_html=True
            )

        # Rate
        formatted_rate = "N/A" if pd.isna(rate) else f"{rate:.2f}"
        st.markdown(f'<p class="result"><b>रेट:</b> {formatted_rate}</p>', unsafe_allow_html=True)

        # Main image
        img_path = get_image_path(clean_item)
        if img_path:
            st.image(img_path, caption=f'Image of {clean_item}', use_container_width=True)
        else:
            st.markdown('<p class="result">इस आइटम नंबर के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)

        # ---------- Alternatives: ONLY when Out of Stock ----------
        if stock_status == 'Out of Stock':
            st.markdown("<h2>विकल्प</h2>", unsafe_allow_html=True)

            alt_row = alt_df[alt_df['ITEM NO.'] == clean_item]
            if not alt_row.empty:
                alt_candidates = [
                    as_clean_item_no(alt_row.iloc[0].get('Alt1', '')),
                    as_clean_item_no(alt_row.iloc[0].get('Alt2', '')),
                    as_clean_item_no(alt_row.iloc[0].get('Alt3', '')),
                ]
                # Filter empties and duplicates and remove same as main item
                seen = set([clean_item])
                alt_candidates = [a for a in alt_candidates if a and a not in seen and not (a in seen or seen.add(a))]

                if alt_candidates:
                    for alt_item in alt_candidates:
                        alt_master_row = master_df[master_df['ITEM NO.'] == alt_item]
                        if not alt_master_row.empty:
                            alt_qty = pd.to_numeric(alt_master_row['Quantity'].values[0], errors='coerce')
                            alt_cond = pd.to_numeric(alt_master_row['CONDITION'].values[0], errors='coerce') if 'CONDITION' in alt_master_row.columns else float('nan')
                            alt_status = get_stock_status(alt_qty, alt_cond)
                            alt_rate = pd.to_numeric(alt_master_row['Rate'].values[0], errors='coerce')
                            formatted_alt_rate = "N/A" if pd.isna(alt_rate) else f"{alt_rate:.2f}"

                            if alt_status == 'In Stock':
                                st.markdown(
                                    f'<p class="result">वैकल्पिक आइटम: <b>{alt_item}</b>, रेट: {formatted_alt_rate}, स्टॉक स्थिति: <b>स्टॉक में उपलब्ध</b></p>',
                                    unsafe_allow_html=True
                                )
                                alt_img = get_image_path(alt_item)
                                if alt_img:
                                    st.image(alt_img, caption=f'Image of {alt_item}', use_container_width=True)
                                else:
                                    st.markdown(f'<p class="result">{alt_item} के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
                            else:
                                st.markdown(
                                    f'<p class="result">वैकल्पिक आइटम: <b>{alt_item}</b> स्टॉक में उपलब्ध नहीं है।</p>',
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
else:
    st.markdown('<p class="result">कृपया एक आइटम नंबर दर्ज करें</p>', unsafe_allow_html=True)

# ---------- BOTTOM: Logo at the end ----------
logo_b64 = get_base64_image(logo_path)
if logo_b64:
    st.markdown('<hr style="opacity:0.2;">', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{logo_b64}" style="max-width:240px;"></div>', unsafe_allow_html=True)

st.markdown('<p class="result" style="text-align:center; opacity:0.7;">Powered by Jyoti Cards</p>', unsafe_allow_html=True)
