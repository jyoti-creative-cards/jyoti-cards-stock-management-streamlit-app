import streamlit as st
import pandas as pd
import os
from datetime import datetime
import requests
import pytz

# Load the StkSum file
stk_sum_file_path = 'StkSum jyoti (1).xlsx'
stk_sum_df = pd.read_excel(stk_sum_file_path)

# Load the 1112 (condition) file
condition_list_file_path = '1112.xlsx'
condition_df = pd.read_excel(condition_list_file_path)

# Load the ALTERNATE file
alternative_list_file_path = 'ALTERNATE LIST 10 SEPT.xlsx'
alternative_df = pd.read_excel(alternative_list_file_path)

# Ensure ITEM NO. columns are strings in condition and alternative dataframes
condition_df['ITEM NO.'] = condition_df['ITEM NO.'].astype(str)
alternative_df['ITEM NO.'] = alternative_df['ITEM NO.'].astype(str)

# Step 1: Clean the StkSum data
stk_sum_cleaned = stk_sum_df.iloc[8:].reset_index(drop=True)
stk_sum_cleaned.columns = ['ITEM NO.', 'Quantity', 'Rate', 'Value']  # Renaming the columns

# Now convert ITEM NO. to string in stk_sum_cleaned
stk_sum_cleaned['ITEM NO.'] = stk_sum_cleaned['ITEM NO.'].astype(str)

# Process the ITEM NO. column (extract the numeric part)
stk_sum_cleaned['ITEM NO.'] = stk_sum_cleaned['ITEM NO.'].apply(lambda x: x.split()[0] if isinstance(x, str) and x.split()[0].isdigit() else x)

# Step 2: Multiply the 'Quantity' by 100
stk_sum_cleaned['Quantity'] = pd.to_numeric(stk_sum_cleaned['Quantity'], errors='coerce') * 100

# Step 4: Merge the cleaned StkSum data with Condition data
master_df_cleaned = pd.merge(stk_sum_cleaned, condition_df, on='ITEM NO.', how='left')

# Step 5: Merge the result with the alternative list
master_df_cleaned = pd.merge(master_df_cleaned, alternative_df, on='ITEM NO.', how='left')

# Convert alternatives to string and handle NaN values by replacing them with empty strings
for col in ['Alt1', 'Alt2', 'Alt3']:
    master_df_cleaned[col] = master_df_cleaned[col].apply(lambda x: str(int(float(x))) if pd.notna(x) else '')

master_df = master_df_cleaned

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
    /* Paste your existing CSS here */
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
    /* ... rest of your CSS ... */
    </style>
    """,
    unsafe_allow_html=True
)

# Display the logo in the top-right corner using the CSS class
logo_base64 = get_base64_image(logo_path)
st.markdown(f'<img src="data:image/png;base64,{logo_base64}" class="logo">', unsafe_allow_html=True)

# Display Offer of the Day with a star image (no changes needed)

# Fetch last update time from GitHub and convert to Indian Standard Time (no changes needed)

# Display last updated time (no changes needed)

# Get the list of ITEM NO. values and add an empty option
item_no_list = [''] + master_df['ITEM NO.'].tolist()

# Streamlit app header
st.markdown('<h1 class="title">Jyoti Cards Stock Status</h1>', unsafe_allow_html=True)

# Dropdown for ITEM NO.
item_no = st.selectbox('Select ITEM NO.', item_no_list, index=0)

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
        image_path = os.path.join('OLD ITEMS PHOTOS', f'{item_no}.{ext}')
        if os.path.exists(image_path):
            return image_path
    return None

if item_no:
    # Check if ITEM NO. exists in cleaned data
    item_row = master_df[master_df['ITEM NO.'] == item_no]

    if not item_row.empty:
        quantity = item_row['Quantity'].values[0]
        condition_value = item_row['Condition'].values[0]
        rate = item_row['Rate'].values[0]
        alt1 = item_row['Alt1'].values[0]
        alt2 = item_row['Alt2'].values[0]
        alt3 = item_row['Alt3'].values[0]

        stock_status = get_stock_status(quantity, condition_value)

        # Display stock status
        if stock_status == 'Out of Stock':
            st.markdown('<p class="highlight-red">यह आइटम स्टॉक में नहीं है, कृपया पुष्टि करने के लिए गोदाम में संपर्क करें</p>', unsafe_allow_html=True)
        elif stock_status == 'In Stock':
            st.markdown('<p class="highlight-green">यह आइटम स्टॉक में है, कृपया ऑर्डर बुक करने के लिए गोदाम में संपर्क करें</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="highlight-yellow">यह आइटम का स्टॉक कम है, कृपया अधिक जानकारी के लिए गोदाम में संपर्क करें</p>', unsafe_allow_html=True)

        # Display rate
        formatted_rate = "{:.2f}".format(rate) if rate is not None else "N/A"
        st.markdown(f'<p class="result">Rate: {formatted_rate}</p>', unsafe_allow_html=True)

        # Display image
        image_path = get_image_path(item_no)
        if image_path:
            st.image(image_path, caption=f'Image of {item_no}', use_column_width=True)
        else:
            st.markdown('<p class="result">No image available for this ITEM NO.</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="result">ITEM NO. not available</p>', unsafe_allow_html=True)
        stock_status = 'Out of Stock'

    # Only display alternatives when low stock or out of stock
    if stock_status in ['Out of Stock', 'Low Stock']:
        st.markdown("<h2>Alternatives</h2>", unsafe_allow_html=True)

        for alt_item in [alt1, alt2, alt3]:
            if alt_item and alt_item.strip() != '':
                alt_row = master_df[master_df['ITEM NO.'] == alt_item]
                if not alt_row.empty:
                    alt_quantity = alt_row['Quantity'].values[0]
                    alt_condition_value = alt_row['Condition'].values[0]
                    alt_rate = alt_row['Rate'].values[0]
                    formatted_alt_rate = "{:.2f}".format(alt_rate) if alt_rate is not None else "N/A"

                    alt_stock_status = get_stock_status(alt_quantity, alt_condition_value)

                    if alt_stock_status == 'Out of Stock':
                        continue  # Skip alternatives that are out of stock
                    else:
                        st.markdown(f'<p class="result">Alternative Item: {alt_item}, Rate: {formatted_alt_rate}, Stock Status: {alt_stock_status}</p>', unsafe_allow_html=True)
                        alt_image_path = get_image_path(alt_item)
                        if alt_image_path:
                            st.image(alt_image_path, caption=f'Image of {alt_item}', use_column_width=True)
                        else:
                            st.markdown(f'<p class="result">No image available for {alt_item}</p>', unsafe_allow_html=True)

# Footer
st.markdown('<p class="footer">Powered by Jyoti Cards</p>', unsafe_allow_html=True)
