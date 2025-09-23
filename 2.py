import streamlit as st
import pandas as pd
import os
import datetime
import pytz
import base64
import re
from urllib.parse import quote  # WhatsApp message encoding

# ---------- Page + Theme ----------
st.set_page_config(page_title="Jyoti Cards Stock", layout="centered")

# ---------- Constants ----------
tz = pytz.timezone('Asia/Kolkata')
stk_sum_file = 'StkSum_new.xlsx'                     # Source for ITEM NO. + Qty (col C)
rate_list_file = 'rate list merged.xlsx'             # (Merged but not shown on UI)
alternate_list_file = 'STOCK ALTERNATION LIST.xlsx'  # Source for Alt1/Alt2/Alt3
condition_file = '1112.xlsx'                         # Source for CONDITION
phone_number = "07312506986"                         # Call phone number
whatsapp_phone = "919516789702"                      # WhatsApp phone (91 + 10-digit)
logo_path = 'static/jyoti logo-1.png'
call_icon_url = 'static/call_icon.png'
MASTER_DF_OUT = 'master_df.xlsx'                     # Latest merged sheet

# ====== SINGLE OFFER BANNER (EDIT HERE) ======
OFFER_ENABLED = True
OFFER_TEXT = "New arrivals now available"
# OFFER_TEXT = "Special Diwali discount"
# OFFER_TEXT = "Festive combos — order now"

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

def get_image_path(item_no: str) -> str | None:
    if not item_no:
        return None
    want = _digits(item_no)
    if not want:
        return None
    # 1) direct
    for ext in ['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG']:
        p = os.path.join('static', f'{item_no}.{ext}')
        if os.path.exists(p):
            return p
    # 2) recursive
    exts = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    best, best_score = None, (999, 999999)
    for root, _, files in os.walk('static'):
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
    """
    Out of Stock: quantity is NaN or 0
    In Stock    : condition is NaN OR quantity > condition
    Low Stock   : 0 < quantity <= condition
    """
    if pd.isna(quantity) or quantity == 0:
        return 'Out of Stock'
    if pd.isna(condition_value):
        return 'In Stock'
    return 'In Stock' if quantity > condition_value else 'Low Stock'

# ---------- Data pipeline (auto-rebuild when any file changes) ----------
@st.cache_data(show_spinner=False)
def build_master_df(_stk_m, _rate_m, _alt_m, _cond_m):
    # --- StkSum (ITEM NO., Quantity from col C) ---
    df_stk_sum = pd.read_excel(stk_sum_file, usecols=[0, 2])
    df_stk_sum = df_stk_sum.iloc[7:].reset_index(drop=True)
    df_stk_sum.columns = ['ITEM NO.', 'Quantity']
    df_stk_sum['ITEM NO.'] = df_stk_sum['ITEM NO.'].apply(as_clean_item_no)
    df_stk_sum['Quantity'] = df_stk_sum['Quantity'].astype(str).str.replace(' pcs', '', regex=False)
    df_stk_sum['Quantity'] = pd.to_numeric(df_stk_sum['Quantity'], errors='coerce').fillna(0) * 100
    df_stk_sum['Quantity'] = df_stk_sum['Quantity'].astype(int)

    # --- Rate list (kept but not displayed) ---
    df_rate_list = pd.read_excel(rate_list_file)
    df_rate_list = df_rate_list.iloc[3:].reset_index(drop=True)
    df_rate_list.columns = ['ITEM NO.', 'Rate']
    df_rate_list['ITEM NO.'] = df_rate_list['ITEM NO.'].apply(as_clean_item_no)
    df_rate_list['Rate'] = pd.to_numeric(df_rate_list['Rate'], errors='coerce').fillna(0.0)

    # --- Alternate list ---
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

    # --- Condition sheet ---
    df_condition = pd.read_excel(condition_file)
    df_condition.columns = ['ITEM NO.', 'CONDITION']
    df_condition['ITEM NO.'] = df_condition['ITEM NO.'].apply(as_clean_item_no)
    df_condition['CONDITION'] = pd.to_numeric(df_condition['CONDITION'], errors='coerce')

    # ---------- NEW: build a base of all item numbers (union) ----------
    keys = set(df_stk_sum['ITEM NO.'].tolist())
    keys |= set(df_alt['ITEM NO.'].tolist())
    keys |= set(df_condition['ITEM NO.'].tolist())
    base = pd.DataFrame({'ITEM NO.': sorted(k for k in keys if k)})

    # Merge everything ONTO the base so items missing in stock still exist
    master = (
        base
        .merge(df_stk_sum[['ITEM NO.', 'Quantity']], on='ITEM NO.', how='left')
        .merge(df_rate_list, on='ITEM NO.', how='left')
        .merge(df_alt, on='ITEM NO.', how='left')
        .merge(df_condition, on='ITEM NO.', how='left')
    )

    # Types & blanks
    master['Quantity'] = pd.to_numeric(master['Quantity'], errors='coerce').fillna(0).astype(int)
    master['Rate'] = pd.to_numeric(master['Rate'], errors='coerce')  # unused on UI
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

# Small header row with reload
hdr_cols = st.columns([1, 6])
with hdr_cols[0]:
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

      .offer {
          margin: 0.2rem auto 0.5rem auto;
          padding: 10px 16px;
          border-radius: 999px;
          font-weight: 800;
          text-align: center;
          max-width: 680px;
          color: white;
          background: linear-gradient(90deg, #ef4444, #f59e0b, #22c55e, #3b82f6, #a855f7);
          background-size: 300% 300%;
          animation: moveGradient 8s ease infinite;
          box-shadow: 0 6px 16px rgba(0,0,0,0.10);
          letter-spacing: 0.3px;
          font-size: 1.0rem;
      }
      @keyframes moveGradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
      }

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

      .last-panel {
          margin: 0.35rem auto 0.6rem auto;
          padding: 8px 14px;
          border-radius: 999px;
          max-width: 380px;
          text-align: center;
          font-weight: 800;
          color: #0f172a;
          background: linear-gradient(90deg, #e0f2fe, #ecfeff, #e0f2fe);
          box-shadow: 0 0 0 2px #bae6fd inset, 0 6px 16px rgba(59,130,246,0.15);
      }

      .search-wrap { max-width: 680px; margin: 0.2rem auto 0.6rem auto; }

      .card {
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 16px;
          padding: 18px 18px;
          box-shadow: 0 10px 25px rgba(0,0,0,0.06);
      }
      .item-caption { font-size: 0.92rem; color: #475569; margin: 0 0 8px 0; }
      .status-badge {
          border-radius: 12px; padding: 10px 12px; margin-bottom: 12px; font-weight: 700; display: inline-block;
      }
      .status-in  { background-color:#d4edda; color:#155724
          </style>
    """,
    unsafe_allow_html=True
)
