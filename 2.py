import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytz
import re  # Import regex module

# Function to fetch the last modification time of the StkSum file
def get_file_modification_time(file_path):
    if os.path.exists(file_path):
        # Get the last modified time in UTC
        mod_time = os.path.getmtime(file_path)
        mod_datetime_utc = datetime.utcfromtimestamp(mod_time)

        # Convert the UTC time to Indian Standard Time (UTC+5:30)
        ist_timezone = pytz.timezone('Asia/Kolkata')
        mod_datetime_ist = mod_datetime_utc.replace(tzinfo=pytz.utc).astimezone(ist_timezone)

        # Format the IST time to the required format
        return mod_datetime_ist.strftime('%d-%m-%Y %H:%M')
    else:
        return "File not found"

# Load the StkSum file, skipping the first 8 rows and without headers
stk_sum_file_path = 'StkSum_new.xlsx'
stk_sum_df = pd.read_excel(stk_sum_file_path, skiprows=8, header=None, names=['ITEM NO.', 'QUANTITY'])

# Load the rate list file, skipping the first 5 rows
rate_file_path = 'rate list merged.xlsx'
rate_df = pd.read_excel(rate_file_path, skiprows=5, header=None, names=['ITEM NO.', 'RATE'])

# Load the condition file, skipping the first row
condition_list_file_path = '1112.xlsx'
condition_df = pd.read_excel(condition_list_file_path, skiprows=1, header=None, names=['ITEM NO.', 'CONDITION'])

# Load the alternative file, skipping the first row
alternative_list_file_path = 'STOCK ALTERNATION LIST.xlsx'
alternative_df = pd.read_excel(alternative_list_file_path, skiprows=1, header=None, names=['ITEM NO.', 'ALT1', 'ALT2', 'ALT3'])

# Function to standardize column names
def standardize_column_names(df):
    df.columns = df.columns.str.strip().str.upper()
    return df

# Standardize columns in all DataFrames
stk_sum_df = standardize_column_names(stk_sum_df)
rate_df = standardize_column_names(rate_df)
condition_df = standardize_column_names(condition_df)
alternative_df = standardize_column_names(alternative_df)

# Verify 'ITEM NO.' column exists in all DataFrames
for df_name, df in [('stk_sum_df', stk_sum_df), ('rate_df', rate_df), ('condition_df', condition_df), ('alternative_df', alternative_df)]:
    if 'ITEM NO.' not in df.columns:
        st.error(f"'ITEM NO.' column not found in {df_name} with columns: {df.columns.tolist()}")
        st.stop()

# Display last updated time based on file modification time
last_update = get_file_modification_time(stk_sum_file_path)

# Ensure 'ITEM NO.' columns are strings in all DataFrames
for df in [stk_sum_df, rate_df, condition_df, alternative_df]:
    df['ITEM NO.'] = df['ITEM NO.'].astype(str)

# Function to process ITEM NO.
def process_item_no(item_no):
    if isinstance(item_no, str):
        item_no = item_no.strip().upper()
        parts = item_no.split()
        return parts[0] if parts else item_no
    else:
        return str(item_no).strip().upper()

# Apply processing to 'ITEM NO.' in all DataFrames
for df in [stk_sum_df, rate_df, condition_df, alternative_df]:
    df['ITEM NO.'] = df['ITEM NO.'].apply(process_item_no)

# Clean the 'QUANTITY' column by removing non-numeric characters
def clean_quantity(qty):
    if isinstance(qty, str):
        qty = qty.strip()
        match = re.match(r'([\d\.\-]+)', qty)
        if match:
            return float(match.group(1))
    return pd.to_numeric(qty, errors='coerce')

stk_sum_df['QUANTITY'] = stk_sum_df['QUANTITY'].apply(clean_quantity) * 100

# Merge the cleaned StkSum data with Condition data
master_df = pd.merge(stk_sum_df, condition_df, on='ITEM NO.', how='left')

# Merge the result with the alternative list
master_df = pd.merge(master_df, alternative_df, on='ITEM NO.', how='left')

# Merge with the rate data
master_df = pd.merge(master_df, rate_df[['ITEM NO.', 'RATE']], on='ITEM NO.', how='left')

# Convert alternatives to string and handle NaN values by replacing them with empty strings
for col in ['ALT1', 'ALT2', 'ALT3']:
    if col in master_df.columns:
        master_df[col] = master_df[col].apply(lambda x: str(x).strip() if pd.notna(x) and x != '' else '')
    else:
        master_df[col] = ''

# The rest of your Streamlit code goes here...

# Text input for ITEM NO. with placeholder
item_no = st.text_input('', placeholder='🔍 कृपया आइटम नंबर यहां डालें')

# Function to get stock status
def get_stock_status(quantity, condition_value):
    if pd.isna(quantity) or quantity <= 0:
        return 'Out of Stock'
    elif pd.isna(condition_value):
        return 'In Stock'
    elif quantity > condition_value:
        return 'In Stock'
    else:
        return 'Low Stock'

# Process the user input
if item_no:
    item_no_processed = process_item_no(item_no)
    item_row = master_df[master_df['ITEM NO.'] == item_no_processed]

    if not item_row.empty:
        # Extract data and display
        quantity = item_row['QUANTITY'].values[0]
        condition_value = item_row['CONDITION'].values[0] if 'CONDITION' in item_row.columns else None
        rate = item_row['RATE'].values[0] if 'RATE' in item_row.columns else None
        alt1 = item_row['ALT1'].values[0] if 'ALT1' in item_row.columns else ''
        alt2 = item_row['ALT2'].values[0] if 'ALT2' in item_row.columns else ''
        alt3 = item_row['ALT3'].values[0] if 'ALT3' in item_row.columns else ''

        stock_status = get_stock_status(quantity, condition_value)

        # Display stock status and other information
        # ...

    else:
        st.markdown('<p class="result">आइटम नंबर उपलब्ध नहीं है</p>', unsafe_allow_html=True)
        stock_status = 'Out of Stock'
        alt1 = alt2 = alt3 = ''
