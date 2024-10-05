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
search_icon_url = 'static/search_icon.png'  # Add path to your search icon

# Function to encode images to base64
def get_base64_image(image_path):
    import base64
    with open(image_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Encode the images
logo_base64 = get_base64_image(logo_path)
call_icon_base64 = get_base64_image(call_icon_url)
search_icon_base64 = get_base64_image(search_icon_url)

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
    .result {{
        font-size: 1.25em;
        color: #333;
        font-weight: bold;
        text-align: center;
    }}
    .footer {{
        font-size: 1em;
        color: #888;
        text-align: center;
        margin-top: 2em;
    }}
    .highlight-green {{
        font-size: 1.25em;
        font-weight: bold;
        color: #ffffff;
        background-color: #28a745;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        margin-top: 1em;
    }}
    .highlight-yellow {{
        font-size: 1.25em;
        font-weight: bold;
        color: #ffffff;
        background-color: #ffc107;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        margin-top: 1em;
    }}
    .highlight-red {{
        font-size: 1.25em;
        font-weight: bold;
        color: #ffffff;
        background-color: #dc3545;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        margin-top: 1em;
    }}
    .call-link {{
        display: inline-flex;
        align-items: center;
        font-size: 1.25em;
        font-weight: bold;
        color: #007bff;
        text-decoration: none;
        transition: color 0.3s ease;
    }}
    .call-link:hover {{
        color: #0056b3;
    }}
    .call-link img {{
        margin-right: 8px;
    }}
    .last-updated {{
        font-size: 1.5em;
        font-style: italic;
        color: red;
        animation: blink 1.5s infinite;
        text-align: center;
        margin-top: 1em;
    }}
    @keyframes blink {{
        0% {{ color: red; }}
        50% {{ color: orange; }}
        100% {{ color: green; }}
    }}
    /* CSS for positioning the logo in the top-right corner */
    .logo {{
        position: absolute;
        top: 10px;
        right: 10px;
        width: 100px;
    }}
    /* CSS for the search input */
    .search-container {{
        position: relative;
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
        margin-top: 20px;
    }}
    .search-input {{
        width: 100%;
        padding: 10px 10px 10px 40px;
        font-size: 1.25em;
        border: 1px solid #ccc;
        border-radius: 5px;
    }}
    .search-icon {{
        position: absolute;
        top: 50%;
        left: 10px;
        transform: translateY(-50%);
        width: 20px;
        height: 20px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Display the logo in the top-right corner using the CSS class
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

# Get the list of ITEM NO. values (we won't use it since we're using text input)
# item_no_list = [''] + master_df['ITEM NO.'].tolist()

# Streamlit app header
st.markdown('<h1 class="title">Jyoti Cards Stock Status</h1>', unsafe_allow_html=True)

# Call button with a call icon
phone_number = "07312456565"
call_button = f'''
<a href="tel:{phone_number}" class="call-link">
    <img src="data:image/png;base64,{call_icon_base64}" width="24" height="24" alt="Call Icon">
    Call
</a>
'''
st.markdown(call_button, unsafe_allow_html=True)

# Search Input with magnifying glass icon and Hindi placeholder
search_input_html = f'''
<div class="search-container">
    <img src="data:image/png;base64,{search_icon_base64}" class="search-icon">
    <input type="text" id="item_no_input" class="search-input" placeholder="कृपया आइटम नंबर यहां डालें">
</div>
'''

# Include the HTML and JavaScript
st.markdown(search_input_html, unsafe_allow_html=True)

# JavaScript to get the value from the input box
st.components.v1.html(f"""
<script>
    const doc = window.parent.document;
    const input = doc.getElementById('item_no_input');
    input.addEventListener('input', function(){{
        window.parent.postMessage({{type: 'streamlit:setComponentValue', value: input.value}}, '*');
    }});
</script>
""", height=0)

# Get the input value
item_no = st.experimental_get_query_params().get('value', [''])[0]

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
    # Remove any leading/trailing whitespaces
    item_no = item_no.strip()
    
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
