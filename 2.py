import streamlit as st
import pandas as pd
import os
import datetime
import pytz
import base64
import re
from urllib.parse import quote

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
stk_sum_file = 'data/website stock.xlsx'
alternate_list_file = 'data/ALTER LIST 2026.xlsx'
condition_file = 'data/PORTAL MINIMUM STOCK.xlsx'
phone_number = "07312506986"
whatsapp_phone = "919516789702"
logo_path = 'images/jyoti logo-1.png'
call_icon_url = 'images/call_icon.png'
MASTER_DF_OUT = 'data/master_df.xlsx'

# ====== OFFER BANNER ======
OFFER_ENABLED = True
OFFER_TEXT = "🎉 New arrivals now available"

# ---------- Initialize Session State ----------
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'show_success' not in st.session_state:
    st.session_state.show_success = None

# ---------- Helper Functions ----------
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
    if pd.isna(x):
        return ""
    s = str(x).strip()
    m = re.search(r'(\d+)', s)
    if not m:
        return ""
    return m.group(1)

def _digits(s: str) -> str:
    d = "".join(ch for ch in str(s) if ch.isdigit())
    return d.lstrip('0') or d

@st.cache_data(ttl=3600)
def get_image_path(item_no: str) -> str | None:
    """Cached image path lookup for better performance"""
    if not item_no:
        return None
    want = _digits(item_no)
    if not want:
        return None
    # 1) direct lookup
    for ext in ['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG']:
        p = os.path.join('images', f'{item_no}.{ext}')
        if os.path.exists(p):
            return p
    # 2) recursive search
    exts = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    best, best_score = None, (999, 999999)
    for root, _, files in os.walk('images'):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext not in exts:
                continue
            full = os.path.join(root, fname)
            name_no_ext = os.path.splitext(fname)[0]
            name_digits = _digits(name_no_ext)
            score = None
            if name_digits == want and name_no_ext == item_no: score = 0
            elif name_digits == want: score = 1
            elif want and want in _digits(fname): score = 2
            if score is not None:
                cand = (score, len(full))
                if cand < best_score:
                    best_score, best = cand, full
    return best

def get_stock_status(quantity, condition_value):
    """Return stock status with percentage"""
    if pd.isna(quantity) or quantity <= 0:
        return 'Out of Stock', 0
    if pd.isna(condition_value):
        return 'In Stock', 100
    percentage = min(100, int((quantity / condition_value) * 100))
    if quantity > condition_value:
        return 'In Stock', percentage
    else:
        return 'Low Stock', percentage


# ---------- Data Pipeline ----------
@st.cache_data(show_spinner=False, ttl=0)
def build_master_df(_stk_m, _alt_m, _cond_m):
    """Build master dataframe with caching for performance"""
    # Website Stock
    df_stk_sum = pd.read_excel(stk_sum_file, usecols=[0, 2])
    df_stk_sum = df_stk_sum.iloc[8:].reset_index(drop=True)  # Data starts from row 8
    df_stk_sum.columns = ['ITEM NO.', 'Quantity']
    df_stk_sum['ITEM NO.'] = df_stk_sum['ITEM NO.'].apply(as_clean_item_no)
    df_stk_sum['Quantity'] = df_stk_sum['Quantity'].astype(str).str.replace(' pcs', '', regex=False)
    df_stk_sum['Quantity'] = pd.to_numeric(df_stk_sum['Quantity'], errors='coerce').fillna(0) * 100
    df_stk_sum['Quantity'] = df_stk_sum['Quantity'].astype(int)

    # Alternates
    df_alt = pd.read_excel(alternate_list_file)
    df_alt = df_alt.iloc[3:].reset_index(drop=True)
    df_alt.columns = ['S.NO.', 'ITEM NO.', 'Alt1', 'Alt2', 'Alt3']
    df_alt = df_alt[['ITEM NO.', 'Alt1', 'Alt2', 'Alt3']]
    df_alt['ITEM NO.'] = df_alt['ITEM NO.'].apply(as_clean_item_no)
    for c in ['Alt1', 'Alt2', 'Alt3']:
        df_alt[c] = df_alt[c].apply(as_clean_item_no)

    # Conditions
    df_condition = pd.read_excel(condition_file, usecols=[1, 3])
    df_condition.columns = ['ITEM NO.', 'CONDITION']
    df_condition['ITEM NO.'] = df_condition['ITEM NO.'].apply(as_clean_item_no)
    df_condition['CONDITION'] = pd.to_numeric(df_condition['CONDITION'], errors='coerce')

    # Merge
    keys = set(df_stk_sum['ITEM NO.'].tolist()) | set(df_alt['ITEM NO.'].tolist()) | set(df_condition['ITEM NO.'].tolist())
    base = pd.DataFrame({'ITEM NO.': sorted(k for k in keys if k)})

    master = (base
        .merge(df_stk_sum[['ITEM NO.', 'Quantity']], on='ITEM NO.', how='left')
        .merge(df_alt, on='ITEM NO.', how='left')
        .merge(df_condition, on='ITEM NO.', how='left'))

    master['Quantity'] = pd.to_numeric(master['Quantity'], errors='coerce').fillna(0).astype(int)
    master['CONDITION'] = pd.to_numeric(master['CONDITION'], errors='coerce')
    for c in ['Alt1', 'Alt2', 'Alt3']:
        master[c] = master[c].fillna("").astype(str)

    try:
        master.to_excel(MASTER_DF_OUT, index=False)
    except Exception:
        pass

    return master

# ---------- Load Data ----------
with st.spinner('⏳ Loading data...'):
    stk_m = file_mtime_num(stk_sum_file)
    alt_m = file_mtime_num(alternate_list_file)
    cond_m = file_mtime_num(condition_file)
    master_df = build_master_df(stk_m, alt_m, cond_m)
    alt_df = master_df[['ITEM NO.', 'Alt1', 'Alt2', 'Alt3']].copy()

# ---------- Modern Styling ----------
st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    .stApp { 
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Offer Banner */
      .offer {
        margin: 1rem auto;
        padding: 14px 24px;
        border-radius: 16px;
        font-weight: 700;
          text-align: center;
          max-width: 680px;
          color: white;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
        font-size: 1.1rem;
        animation: slideDown 0.5s ease-out;
    }
    
    @keyframes slideDown {
        from { transform: translateY(-20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    /* Sticky Header */
      .sticky-top {
          position: sticky;
          top: 0;
          z-index: 100;
          backdrop-filter: blur(10px);
          background: transparent;
          border-bottom: none;
          padding: 12px 0;
          box-shadow: none;
      }
    
    .title {
        font-size: 2.2em;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        text-align: center;
        margin: 0.5em 0 0.3em 0;
        letter-spacing: -0.5px;
    }

      .last-panel {
          margin: 0.3rem auto 0.5rem auto;
          padding: 6px 16px;
          border-radius: 999px;
          max-width: 350px;
          text-align: center;
          font-weight: 600;
          font-size: 0.85rem;
          color: #64748b;
          background: transparent;
          border: none;
      }
    
    /* Search Input */
      .search-wrap {
          max-width: 680px;
        margin: 1rem auto;
    }
    
    .stTextInput input {
        border-radius: 14px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 16px 20px !important;
        font-size: 1.1rem !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important;
    }
    
    .stTextInput input:focus {
        border-color: #667eea !important;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.2) !important;
        transform: translateY(-2px);
    }
    
    /* Success/Error Messages */
    .success-msg {
        padding: 12px 20px;
        border-radius: 12px;
        margin: 1rem auto;
        max-width: 680px;
        text-align: center;
        font-weight: 600;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        animation: slideDown 0.3s ease-out;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }
    
    /* Result Card */
      .card {
        background: transparent;
        border-radius: 20px;
        padding: 24px;
        margin: 1.5rem auto;
        max-width: 720px;
        box-shadow: none;
        animation: fadeIn 0.4s ease-out;
        border: none;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .item-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        flex-wrap: wrap;
        gap: 10px;
    }
    
    .item-caption {
        font-size: 1.1rem;
        color: #4a5568;
        font-weight: 600;
    }
    
    .action-buttons {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    
    .action-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border-radius: 10px;
        font-size: 0.9rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        border: none;
        text-decoration: none;
        white-space: nowrap;
    }
    
    .share-btn {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.3);
    }
    
    .share-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(37, 211, 102, 0.4);
    }
    
    .compare-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .compare-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
    }
    
    /* Status Badge */
    .status-container {
        margin: 16px 0;
    }
    
    .status-badge {
        display: inline-block;
        padding: 14px 20px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .status-in {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
    }
    
    .status-out {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
    }
    
    .status-low {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
    }
    
    /* Progress Bar */
    .progress-container {
        width: 100%;
        height: 8px;
        background: #e2e8f0;
        border-radius: 10px;
        overflow: hidden;
        margin: 8px 0;
    }
    
    .progress-bar {
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    
    .progress-in { background: linear-gradient(90deg, #10b981, #059669); }
    .progress-low { background: linear-gradient(90deg, #f59e0b, #d97706); }
    .progress-out { background: linear-gradient(90deg, #ef4444, #dc2626); }
    
    /* Image Container */
    .img-container {
          border-radius: 16px;
        overflow: hidden;
        margin: 20px 0;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    
    .img-container:hover {
        transform: scale(1.02);
    }
    
    /* Alternatives Grid */
      .alt-grid {
          display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-top: 20px;
    }
    
    @media (max-width: 768px) {
        .alt-grid {
            grid-template-columns: 1fr;
        }
    }
    
      .alt-card {
        background: white;
        border-radius: 16px;
          overflow: hidden;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .alt-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }
    
    .alt-card img {
        width: 100%;
        height: auto;
        display: block;
    }
    
    .alt-body {
        padding: 12px;
    }
    
    .badge {
        display: inline-block;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 8px;
    }
    
    .badge-in { background: #d1fae5; color: #065f46; }
    .badge-low { background: #fef3c7; color: #92400e; }
    .badge-out { background: #fee2e2; color: #991b1b; }
    .badge-unk { background: #e5e7eb; color: #374151; }
    
    /* Compare Section */
    .compare-section {
        background: white;
        border-radius: 20px;
        padding: 24px;
        margin: 1.5rem auto;
        max-width: 100%;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1);
    }
    
    .compare-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-top: 16px;
    }
    
    .compare-item {
        background: #f8fafc;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        border: 2px solid #e2e8f0;
    }
    
    /* Footer */
      .sticky-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(10px);
        border-top: 1px solid rgba(0, 0, 0, 0.1);
        padding: 16px;
        z-index: 200;
        box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.05);
    }
    
    .footer-inner {
        max-width: 820px;
        margin: 0 auto;
        display: flex;
        gap: 12px;
        align-items: center;
        justify-content: center;
        flex-wrap: wrap;
    }
    
    .link-btn {
        display: inline-flex;
        gap: 8px;
        align-items: center;
        justify-content: center;
        text-decoration: none;
        border-radius: 12px;
        padding: 14px 24px;
        font-weight: 700;
        font-size: 1rem;
        transition: all 0.2s ease;
        min-width: 140px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .call-btn {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
    }
    
    .call-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
    }
    
    .wa-btn {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white;
    }
    
    .wa-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(37, 211, 102, 0.4);
    }
    
    .page-bottom-spacer {
        height: 90px;
    }
    
    /* Mobile Optimizations */
    @media (max-width: 768px) {
        .title {
            font-size: 1.8em;
        }
        
        .card {
            padding: 20px;
            margin: 1rem;
        }
        
        .status-badge {
            font-size: 0.95rem;
            padding: 12px 18px;
        }
        
        .link-btn {
            min-width: 120px;
            padding: 12px 20px;
            font-size: 0.95rem;
        }
        
        .action-btn {
            font-size: 0.85rem;
            padding: 7px 14px;
        }
        
      .footer-inner {
            flex-direction: column;
            gap: 10px;
        }
        
        .link-btn {
            width: 100%;
        }
    }
    
    /* Loading Animation */
    .loading {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(102, 126, 234, 0.3);
        border-radius: 50%;
        border-top-color: #667eea;
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
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

last_update_time = safe_file_mtime(stk_sum_file)
if last_update_time:
    st.markdown(
        f'<div class="last-panel">Last Updated: <b>{last_update_time.strftime("%d-%m-%Y %H:%M")}</b></div>',
        unsafe_allow_html=True
    )

st.markdown('<div class="search-wrap">', unsafe_allow_html=True)

# Search with reload button
col1, col2 = st.columns([5, 1])
with col1:
    item_no = st.text_input(
        "Search",
        value="",
        placeholder="🔍 कृपया आइटम नंबर यहाँ डालें",
        label_visibility="collapsed",
        key="item_no"
    ).strip().replace(".0", "")

with col2:
    if st.button("🔄", help="Reload data"):
        build_master_df.clear()
        get_image_path.clear()
        st.rerun()

st.markdown('</div></div>', unsafe_allow_html=True)

# ---------- Main Content ----------
if item_no:
    clean_item = as_clean_item_no(item_no)
    
    # Add to search history
    if clean_item and clean_item not in st.session_state.search_history:
        st.session_state.search_history.insert(0, clean_item)
        st.session_state.search_history = st.session_state.search_history[:5]  # Keep last 5
    
    item_row = master_df[master_df['ITEM NO.'] == clean_item]

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if not item_row.empty:
        quantity = pd.to_numeric(item_row['Quantity'].values[0], errors='coerce')
        condition_value = pd.to_numeric(item_row['CONDITION'].values[0], errors='coerce') if 'CONDITION' in item_row.columns else float('nan')
        stock_status, percentage = get_stock_status(quantity, condition_value)
        
        # Item Header
        st.markdown(f'<div class="item-caption">आइटम नंबर: <b style="font-size: 1.3rem;">{clean_item}</b></div>', unsafe_allow_html=True)
        
        # Status Badge
        st.markdown('<div class="status-container">', unsafe_allow_html=True)
        
        if stock_status == 'In Stock':
            st.markdown('<div class="status-badge status-in">✅ यह आइटम स्टॉक में उपलब्ध है</div>', unsafe_allow_html=True)
        elif stock_status == 'Out of Stock':
            st.markdown('<div class="status-badge status-out">❌ यह आइटम स्टॉक में उपलब्ध नहीं है</div>', unsafe_allow_html=True)
        else:  # Low Stock
            st.markdown('<div class="status-badge status-low">⚠️ यह आइटम कम स्टॉक में है</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Image
        img_path = get_image_path(clean_item)
        if img_path:
            st.markdown('<div class="img-container">', unsafe_allow_html=True)
            st.image(img_path, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="text-align: center; color: #94a3b8; padding: 40px 0;">📷 इस आइटम के लिए कोई छवि उपलब्ध नहीं है</p>', unsafe_allow_html=True)
        
        # Alternatives (only when out of stock)
        if pd.notna(quantity) and int(quantity) == 0:
            alt_row = alt_df[alt_df['ITEM NO.'] == clean_item]
            if not alt_row.empty:
                alts = [as_clean_item_no(alt_row.iloc[0].get(f'Alt{i}', '')) for i in [1, 2, 3]]
                alts = [a for a in alts if a]
                if alts:
                    st.markdown("<h3 style='margin-top: 30px;'>🔄 विकल्प</h3>", unsafe_allow_html=True)
                    st.markdown('<div class="alt-grid">', unsafe_allow_html=True)
                    
                    for alt_item in alts[:3]:
                        alt_master_row = master_df[master_df['ITEM NO.'] == alt_item]
                        alt_img = get_image_path(alt_item)

                        if alt_master_row.empty and not alt_img:
                            continue

                        if not alt_master_row.empty:
                            alt_qty = pd.to_numeric(alt_master_row['Quantity'].values[0], errors='coerce')
                            alt_cond = pd.to_numeric(alt_master_row['CONDITION'].values[0], errors='coerce') if 'CONDITION' in alt_master_row.columns else float('nan')
                            alt_status, _ = get_stock_status(alt_qty, alt_cond)
                            
                            if alt_status == 'In Stock':
                                badge_html = '<span class="badge badge-in">In Stock</span>'
                            elif alt_status == 'Low Stock':
                                badge_html = '<span class="badge badge-low">Low Stock</span>'
                            else:
                                badge_html = '<span class="badge badge-out">Out of Stock</span>'
                        else:
                            badge_html = '<span class="badge badge-unk">Unknown</span>'

                        st.markdown('<div class="alt-card">', unsafe_allow_html=True)
                        if alt_img:
                            st.image(alt_img, use_container_width=True)
                        else:
                            st.markdown('<div style="height: 200px; display: flex; align-items: center; justify-content: center; background: #f1f5f9; color: #94a3b8;">No Image</div>', unsafe_allow_html=True)
                        
                        st.markdown(f'''
                            <div class="alt-body">
                                <div style="display: flex; align-items: center; justify-content: space-between;">
                                    <div style="font-weight: 700; font-size: 1.1rem; color: #1e293b;">{alt_item}</div>
                                    {badge_html}
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="text-align: center; color: #ef4444; font-size: 1.1rem; padding: 40px 0;">❌ मुख्य आइटम उपलब्ध नहीं है</p>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Search History
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

# Call Button
call_url = f"tel:{phone_number}"
st.markdown(f'''
    <a href="{call_url}" class="link-btn call-btn">
        📞 Call
    </a>
''', unsafe_allow_html=True)

# WhatsApp Button with icon - context-aware message
if item_no and item_no.strip():
    clean_item_for_wa = as_clean_item_no(item_no)
    wa_text = f"नमस्ते, मुझे {clean_item_for_wa} बुक करना है, कृपया इतनी क्वांटिटी बुक करें __"
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

# Logo
logo_b64 = get_base64_image(logo_path)
if logo_b64:
    st.markdown('<hr style="opacity:0.2; margin: 20px 0;">', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{logo_b64}" style="max-width:200px; width:50%; height:auto; opacity: 0.8;"></div>', unsafe_allow_html=True)

st.markdown('<p style="text-align:center; color: #94a3b8; font-size: 0.85rem; margin: 20px 0;">Powered by Jyoti Cards © 2026</p>', unsafe_allow_html=True)
