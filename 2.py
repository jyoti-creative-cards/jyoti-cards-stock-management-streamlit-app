import streamlit as st
import pandas as pd
import os
from datetime import datetime
import requests
import pytz

# Load the StkSum file (now only 'ITEM NO.' and 'Quantity')
stk_sum_file_path = 'StkSum_new.xlsx'
stk_sum_df = pd.read_excel(stk_sum_file_path)

# Load the rate list file
rate_file_path = 'rate list merged.xlsx'
rate_df = pd.read_excel(rate_file_path)

# Load the 1112 (condition) file
condition_list_file_path = '1112.xlsx'
condition_df = pd.read_excel(condition_list_file_path)

# Load the ALTERNATE file
alternative_list_file_path = 'ALTERNATE LIST 10 SEPT.xlsx'
alternative_df = pd.read_excel(alternative_list_file_path)

# Step 1: Clean the StkSum data
# Assuming that actual data starts from row 9 (skip first 8 rows)
stk_sum_cleaned = stk_sum_df.iloc[8:].reset_index(drop=True)
stk_sum_cleaned.columns = ['ITEM NO.', 'Quantity']  # Adjusted columns

# Clean the rate_df data (skip the first 4 rows)
rate_df_cleaned = rate_df.iloc[3:].reset_index(drop=True)
rate_df_cleaned.columns = ['ITEM NO.', 'Rate']

# Now ensure ITEM NO. columns are strings in all dataframes
# Convert 'ITEM NO.' to string in cleaned dataframes
stk_sum_cleaned['ITEM NO.'] = stk_sum_cleaned['ITEM NO.'].astype(str)
rate_df_cleaned['ITEM NO.'] = rate_df_cleaned['ITEM NO.'].astype(str)

condition_df['ITEM NO.'] = condition_df['ITEM NO.'].astype(str)
alternative_df['ITEM NO.'] = alternative_df['ITEM NO.'].astype(str)

# Process the ITEM NO. column in stk_sum_cleaned (extract the numeric part)
stk_sum_cleaned['ITEM NO.'] = stk_sum_cleaned['ITEM NO.'].apply(lambda x: x.split()[0] if isinstance(x, str) and x.split()[0].isdigit() else x)
rate_df_cleaned['ITEM NO.'] = rate_df_cleaned['ITEM NO.'].apply(lambda x: x.split()[0] if isinstance(x, str) and x.split()[0].isdigit() else x)

# Step 2: Multiply the 'Quantity' by 100
stk_sum_cleaned['Quantity'] = pd.to_numeric(stk_sum_cleaned['Quantity'], errors='coerce') * 100

# Step 3: Merge the cleaned StkSum data with Condition data
master_df = pd.merge(stk_sum_cleaned, condition_df, on='ITEM NO.', how='left')

# Step 4: Merge the result with the alternative list
master_df = pd.merge(master_df, alternative_df, on='ITEM NO.', how='left')

# Step 5: Merge with the rate data
master_df = pd.merge(master_df, rate_df_cleaned[['ITEM NO.', 'Rate']], on='ITEM NO.', how='left')

# Convert alternatives to string and handle NaN values by replacing them with empty strings
for col in ['Alt1', 'Alt2', 'Alt3']:
    master_df[col] = master_df[col].apply(lambda x: str(int(float(x))) if pd.notna(x) and x != '' else '')

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

# Fetch last update time from GitHub and convert to Indian Standard Time
def get_last_update_time():
    repo_url = 'https://api.github.com/repos/jyoti-creative-cards/jyoti-cards-stock-management-streamlit-app/commits'
    response = requests.get(repo_url)

    if response.status_code == 200:
        # Get the latest commit
        latest_commit = response.json()[0]
        commit_time = latest_commit['commit']['committer']['date']
        # Convert the UTC time to a datetime object
        commit_time_utc = datetime.strptime(commit_time, '%Y-%m-%dT%H:%M:%SZ')

        # Convert the UTC time to Indian Standard Time (UTC+5:30)
        ist_timezone = pytz.timezone('Asia/Kolkata')
        commit_time_ist = commit_time_utc.replace(tzinfo=pytz.utc).astimezone(ist_timezone)

        # Format the IST time to the required format
        return commit_time_ist.strftime('%d-%m-%Y %H:%M')
    else:
        return "Unable to fetch update time"

# Display last updated time
last_update = get_last_update_time()
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
        image_path = os.path.join('OLD ITEMS PHOTOS', f'{item_no}.{ext}')
        if os.path.exists(image_path):
            return image_path
    return None

# Check if the user has entered an item number
if item_no:
    # Remove any leading/trailing whitespace
    item_no = item_no.strip()
    # Check if ITEM NO. exists in master data
    item_row = master_df[master_df['ITEM NO.'] == item_no]

    if not item_row.empty:
        quantity = item_row['Quantity'].values[0]
        condition_value = item_row['Condition'].values[0]
        rate = item_row['Rate'].values[0]
        alt1 = item_row['Alt1'].values[0]
        alt2 = item_row['Alt2'].values[0]
        alt3 = item_row['Alt3'].values[0]

        stock_status = get_stock_status(quantity, condition_value)

        # Display stock status in colored box with Hindi messages
        if stock_status == 'Out of Stock':
            st.markdown('<div style="background-color:#f8d7da; padding:10px; border-radius:5px;"><p style="color:#721c24;">यह आइटम स्टॉक में नहीं है, कृपया पुष्टि करने के लिए गोदाम में संपर्क करें</p></div>', unsafe_allow_html=True)
        elif stock_status == 'In Stock':
            st.markdown('<div style="background-color:#d4edda; padding:10px; border-radius:5px;"><p style="color:#155724;">यह आइटम स्टॉक में है, कृपया ऑर्डर बुक करने के लिए गोदाम में संपर्क करें</p></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background-color:#fff3cd; padding:10px; border-radius:5px;"><p style="color:#856404;">यह आइटम का स्टॉक कम है, कृपया अधिक जानकारी के लिए गोदाम में संपर्क करें</p></div>', unsafe_allow_html=True)

        # Display rate
        formatted_rate = "{:.2f}".format(rate) if pd.notna(rate) else "N/A"
        st.markdown(f'<p class="result">रेट: {formatted_rate}</p>', unsafe_allow_html=True)

        # Display image
        image_path = get_image_path(item_no)
        if image_path:
            st.image(image_path, caption=f'Image of {item_no}', use_column_width=True)
        else:
            st.markdown('<p class="result">इस आइटम नंबर के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="result">आइटम नंबर उपलब्ध नहीं है</p>', unsafe_allow_html=True)
        stock_status = 'Out of Stock'

    # Only display alternatives when low stock or out of stock
    if stock_status in ['Out of Stock', 'Low Stock']:
        st.markdown("<h2>विकल्प</h2>", unsafe_allow_html=True)

        for alt_item in [alt1, alt2, alt3]:
            if alt_item and alt_item.strip() != '':
                alt_row = master_df[master_df['ITEM NO.'] == alt_item]
                if not alt_row.empty:
                    alt_quantity = alt_row['Quantity'].values[0]
                    alt_condition_value = alt_row['Condition'].values[0]
                    alt_rate = alt_row['Rate'].values[0]
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

                        st.markdown(f'<p class="result">वैकल्पिक आइटम: {alt_item}, रेट: {formatted_alt_rate}, स्टॉक स्थिति: {alt_status_message}</p>', unsafe_allow_html=True)
                        alt_image_path = get_image_path(alt_item)
                        if alt_image_path:
                            st.image(alt_image_path, caption=f'Image of {alt_item}', use_column_width=True)
                        else:
                            st.markdown(f'<p class="result">{alt_item} के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
else:
    # Optional: Display a message prompting the user to enter an item number
    st.markdown('<p class="result">कृपया एक आइटम नंबर दर्ज करें</p>', unsafe_allow_html=True)

# Footer
st.markdown('<p class="footer">Powered by Jyoti Cards</p>', unsafe_allow_html=True)
