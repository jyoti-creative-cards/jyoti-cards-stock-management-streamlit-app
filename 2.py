import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytz

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

# Load and standardize the StkSum file
stk_sum_file_path = 'StkSum_new.xlsx'

# Adjust skiprows and header based on where your headers and data start
# Let's assume headers are on row 9 (index 8) and data starts on the next row
stk_sum_df = pd.read_excel(stk_sum_file_path, skiprows=7, header=1)

# Verify the columns
st.write("stk_sum_df columns:", stk_sum_df.columns.tolist())

# Load and standardize the rate list file
rate_file_path = 'rate list merged.xlsx'
# Adjust skiprows and header as needed
rate_df = pd.read_excel(rate_file_path, skiprows=3)
rate_df = rate_df.reset_index(drop=True)
rate_df.columns = ['ITEM NO.', 'Rate']

# Verify the columns
st.write("rate_df columns:", rate_df.columns.tolist())

# Load and standardize the condition file
condition_list_file_path = '1112.xlsx'
condition_df = pd.read_excel(condition_list_file_path)

# Load and standardize the alternative file
alternative_list_file_path = 'STOCK ALTERNATION LIST.xlsx'
alternative_df = pd.read_excel(alternative_list_file_path)

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

# Proceed with cleaning the data
stk_sum_cleaned = stk_sum_df.copy()

rate_df_cleaned = rate_df.copy()

# Ensure 'ITEM NO.' columns are strings in all DataFrames
for df in [stk_sum_cleaned, rate_df_cleaned, condition_df, alternative_df]:
    df['ITEM NO.'] = df['ITEM NO.'].astype(str)

# Function to process ITEM NO.
def process_item_no(item_no):
    if isinstance(item_no, str):
        parts = item_no.strip().split()
        return parts[0] if parts else item_no
    else:
        return str(item_no).strip()

# Apply processing to 'ITEM NO.' in all DataFrames
for df in [stk_sum_cleaned, rate_df_cleaned, condition_df, alternative_df]:
    df['ITEM NO.'] = df['ITEM NO.'].apply(process_item_no)

# Step 2: Multiply the 'Quantity' by 100
stk_sum_cleaned['Quantity'] = pd.to_numeric(stk_sum_cleaned['Quantity'], errors='coerce') * 100

# Step 3: Merge the cleaned StkSum data with Condition data
master_df = pd.merge(stk_sum_cleaned, condition_df, on='ITEM NO.', how='left')

# Step 4: Merge the result with the alternative list
master_df = pd.merge(master_df, alternative_df, on='ITEM NO.', how='left')

# Step 5: Merge with the rate data
master_df = pd.merge(master_df, rate_df_cleaned[['ITEM NO.', 'Rate']], on='ITEM NO.', how='left')

# Convert alternatives to string and handle NaN values by replacing them with empty strings
for col in ['ALT1', 'ALT2', 'ALT3']:
    if col in master_df.columns:
        master_df[col] = master_df[col].apply(lambda x: str(x).strip() if pd.notna(x) and x != '' else '')
    else:
        master_df[col] = ''

# Serve local static images from the 'static' folder
logo_path = 'static/jyoti logo-1.png'
call_icon_url = 'static/call_icon.png'

# Function to encode images to base64
def get_base64_image(image_path):
    import base64
    with open(image_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Custom CSS for styling
st.markdown(
    f"""
    <style>
    .main {{
        background-color: #ffffff;
    }}
    .stApp {{
        background-color: #ffffff;
    }}
    .title {{
        font-size: 2.2em;
        color: #4e8cff;
        font-weight: bold;
        text-align: center;
        margin-top: 1em;
    }}
    /* Add any additional CSS styling here */
    </style>
    """,
    unsafe_allow_html=True
)

# Display the logo in the top-right corner using the CSS class
logo_base64 = get_base64_image(logo_path)
st.markdown(f'<img src="data:image/png;base64,{logo_base64}" class="logo">', unsafe_allow_html=True)

st.markdown(f'<p class="last-updated">Last Updated: {last_update}</p>', unsafe_allow_html=True)

# Streamlit app header
st.markdown('<h1 class="title">Jyoti Cards Stock Status</h1>', unsafe_allow_html=True)

# Call button with a call icon
call_icon_base64 = get_base64_image(call_icon_url)
phone_number = "07312456565"
call_button = f'''
<a href="tel:{phone_number}" class="call-link">
    <img src="data:image/png;base64,{call_icon_base64}" width="24" height="24" alt="Call Icon">
    Call
</a>
'''
st.markdown(call_button, unsafe_allow_html=True)

# Text input for ITEM NO. with placeholder
item_no = st.text_input('', placeholder='🔍 कृपया आइटम नंबर यहां डालें')

# Function to get stock status
def get_stock_status(quantity, condition_value):
    if pd.isna(quantity) or quantity == 0:
        return 'Out of Stock'
    elif pd.isna(condition_value):
        return 'In Stock'
    elif quantity > condition_value:
        return 'In Stock'
    else:
        return 'Low Stock'

# Function to get image path
def get_image_path(item_no):
    for ext in ['jpeg', 'jpg']:
        image_path = os.path.join('static', f'{item_no}.{ext}')
        if os.path.exists(image_path):
            return image_path
    return None

# Check if the user has entered an item number
if item_no:
    # Remove any leading/trailing whitespace
    item_no = item_no.strip()
    # Process the item_no to match the format in master_df
    item_no_processed = process_item_no(item_no)
    # Check if ITEM NO. exists in master data
    item_row = master_df[master_df['ITEM NO.'] == item_no_processed]

    if not item_row.empty:
        quantity = item_row['Quantity'].values[0]
        condition_value = item_row['CONDITION'].values[0] if 'CONDITION' in item_row.columns else None
        rate = item_row['Rate'].values[0] if 'Rate' in item_row.columns else None
        alt1 = item_row['ALT1'].values[0] if 'ALT1' in item_row.columns else ''
        alt2 = item_row['ALT2'].values[0] if 'ALT2' in item_row.columns else ''
        alt3 = item_row['ALT3'].values[0] if 'ALT3' in item_row.columns else ''

        stock_status = get_stock_status(quantity, condition_value)

        # Display stock status in colored box with Hindi messages
        if stock_status == 'Out of Stock':
            st.markdown('<div style="background-color:#f8d7da; padding:10px; border-radius:5px;"><p style="color:#721c24;">यह आइटम स्टॉक में नहीं है, कृपया इसे मिलते जुलते आइटम नीचे देखें</p></div>', unsafe_allow_html=True)
        elif stock_status == 'In Stock':
            st.markdown('<div style="background-color:#d4edda; padding:10px; border-radius:5px;"><p style="color:#155724;">यह आइटम स्टॉक में है</p></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background-color:#fff3cd; padding:10px; border-radius:5px;"><p style="color:#856404;">यह आइटम का स्टॉक कम है, कृपया अधिक जानकारी के लिए गोदाम में संपर्क करें</p></div>', unsafe_allow_html=True)

        # Display rate
        formatted_rate = "{:.2f}".format(rate) if pd.notna(rate) else "N/A"
        st.markdown(f'<p class="result">रेट: {formatted_rate}</p>', unsafe_allow_html=True)

        # Display image
        image_path = get_image_path(item_no_processed)
        if image_path:
            st.image(image_path, caption=f'Image of {item_no_processed}', use_column_width=True)
        else:
            st.markdown('<p class="result">इस आइटम नंबर के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="result">आइटम नंबर उपलब्ध नहीं है</p>', unsafe_allow_html=True)
        stock_status = 'Out of Stock'
        # Since the item is not found, set alt1, alt2, alt3 to empty
        alt1 = alt2 = alt3 = ''

    # Only display alternatives when low stock or out of stock
    if stock_status in ['Out of Stock', 'Low Stock']:
        st.markdown("<h2>विकल्प</h2>", unsafe_allow_html=True)

        for alt_item in [alt1, alt2, alt3]:
            if alt_item and alt_item.strip() != '':
                alt_item_processed = process_item_no(alt_item)
                alt_row = master_df[master_df['ITEM NO.'] == alt_item_processed]
                if not alt_row.empty:
                    alt_quantity = alt_row['Quantity'].values[0]
                    alt_condition_value = alt_row['CONDITION'].values[0] if 'CONDITION' in alt_row.columns else None
                    alt_rate = alt_row['Rate'].values[0] if 'Rate' in alt_row.columns else None
                    formatted_alt_rate = "{:.2f}".format(alt_rate) if pd.notna(alt_rate) else "N/A"

                    alt_stock_status = get_stock_status(alt_quantity, alt_condition_value)

                    if alt_stock_status == 'Out of Stock':
                        continue  # Skip alternatives that are out of stock
                    else:
                        # Display alternative stock status in Hindi
                        if alt_stock_status == 'In Stock':
                            alt_status_message = 'स्टॉक में उपलब्ध'
                        else:
                            alt_status_message = 'स्टॉक कम है'

                        st.markdown(f'<p class="result">वैकल्पिक आइटम: {alt_item_processed}, रेट: {formatted_alt_rate}, स्टॉक स्थिति: {alt_status_message}</p>', unsafe_allow_html=True)
                        alt_image_path = get_image_path(alt_item_processed)
                        if alt_image_path:
                            st.image(alt_image_path, caption=f'Image of {alt_item_processed}', use_column_width=True)
                        else:
                            st.markdown(f'<p class="result">{alt_item_processed} के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p class="result">वैकल्पिक आइटम {alt_item_processed} उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
else:
    # Optional: Display a message prompting the user to enter an item number
    st.markdown('<p class="result">कृपया एक आइटम नंबर दर्ज करें</p>', unsafe_allow_html=True)

# Footer
st.markdown('<p class="footer">Powered by Jyoti Cards</p>', unsafe_allow_html=True)
