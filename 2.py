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

# Step 1: Clean the StkSum data
stk_sum_cleaned = stk_sum_df.iloc[8:].reset_index(drop=True)
stk_sum_cleaned.columns = ['ITEM NO.', 'Quantity', 'Rate', 'Value']  # Renaming the columns

# Process the ITEM NO. column (extract the numeric part)
stk_sum_cleaned['ITEM NO.'] = stk_sum_cleaned['ITEM NO.'].apply(lambda x: x.split()[0] if isinstance(x, str) and x.split()[0].isdigit() else x)

# Step 2: Multiply the 'Quantity' by 100
stk_sum_cleaned['Quantity'] = pd.to_numeric(stk_sum_cleaned['Quantity'], errors='coerce') * 100

# Step 3: Clean the ITEM NO. columns in the other two dataframes
condition_df['ITEM NO.'] = condition_df['ITEM NO.'].apply(lambda x: x.split()[0] if isinstance(x, str) and x.split()[0].isdigit() else x)
alternative_df['ITEM NO.'] = alternative_df['ITEM NO.'].astype(str)

# Step 4: Merge the cleaned StkSum data with Condition data
master_df_cleaned = pd.merge(stk_sum_cleaned, condition_df, on='ITEM NO.', how='left')

# Step 5: Merge the result with the alternative list
master_df_cleaned = pd.merge(master_df_cleaned, alternative_df, on='ITEM NO.', how='left')

# Convert alternatives to string and handle NaN values by replacing them with empty strings
master_df_cleaned['Alt1'] = master_df_cleaned['Alt1'].apply(lambda x: str(int(x)) if pd.notna(x) else '')
master_df_cleaned['Alt2'] = master_df_cleaned['Alt2'].apply(lambda x: str(int(x)) if pd.notna(x) else '')
master_df_cleaned['Alt3'] = master_df_cleaned['Alt3'].apply(lambda x: str(int(x)) if pd.notna(x) else '')
master_df = master_df_cleaned 

logo_path = 'jyoti logo-1.png'

# Custom CSS for styling
st.markdown(
    """
    <style>
    .main {
        background-color: #ffffff;
    }
    .stApp {
        background-color: #ffffff;
    }
    .title {
        font-size: 2.5em;
        color: #4e8cff;
        font-weight: bold;
        text-align: center;
        margin-top: 0;
        padding-top: 0;
    }
    .input {
        font-size: 1.25em;
        color: #333;
    }
    .result {
        font-size: 1.25em;
        color: #333;
        font-weight: bold;
        text-align: center;
    }
    .footer {
        font-size: 1em;
        color: #888;
        text-align: center;
        margin-top: 2em;
    }
    .highlight-green {
        font-size: 1.25em;
        font-weight: bold;
        color: #ffffff;
        background-color: #28a745;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        margin-top: 1em;
    }
    .highlight-yellow {
        font-size: 1.25em;
        font-weight: bold;
        color: #ffffff;
        background-color: #ffc107;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        margin-top: 1em;
    }
    .highlight-red {
        font-size: 1.25em;
        font-weight: bold;
        color: #ffffff;
        background-color: #dc3545;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        margin-top: 1em;
    }
    .static-box {
        font-size: 1.25em;
        font-weight: bold;
        background-color: #f1f1f1;
        text-align: center;
        padding: 10px;
        border-radius: 5px;
        margin-top: 2em;
    }
    .call-link {
        display: inline-flex;
        align-items: center;
        font-size: 1.25em;
        font-weight: bold;
        color: #007bff;
        text-decoration: none;
        transition: color 0.3s ease;
    }
    .call-link:hover {
        color: #0056b3;
    }
    .call-link img {
        margin-right: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Add a static box in the middle of the screen
st.markdown('<div class="static-box">Offer of the Day - 5% off</div>', unsafe_allow_html=True)

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

# Load the alternative list data
master_data = 'master_df.xlsx'
master_df = pd.read_excel(master_data)

# Get the list of ITEM NO. values and add an empty option
item_no_list = [''] + master_df['ITEM NO.'].tolist()

# Streamlit app
st.image(logo_path, width=200)  # Display the logo
st.markdown('<h1 class="title">Jyoti Cards Stock Status</h1>', unsafe_allow_html=True)

# Dropdown for ITEM NO.
item_no = st.selectbox('Select ITEM NO.', item_no_list, index=0)

# Call button with a call icon (without the big blue box)
phone_number = "07312456565"
call_icon_url = "https://www.iconpacks.net/icons/2/free-phone-icon-2798-thumb.png"  # URL for the call icon

call_button = f'''
<a href="tel:{phone_number}" class="call-link">
    <img src="{call_icon_url}" width="24" height="24" alt="Call Icon">
    Call
</a>
'''
st.markdown(call_button, unsafe_allow_html=True)

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
    else:
        st.markdown('<p class="result">ITEM NO. not available</p>', unsafe_allow_html=True)
        quantity = None
        condition_value = None
        rate = None
        alt1 = None
        alt2 = None
        alt3 = None

    # Display stock status
    if quantity is None or quantity == 0:
        st.markdown('<p class="highlight-red">यह आइटम स्टॉक में नहीं है, कृपया पुष्टि करने के लिए गोदाम में संपर्क करें</p>', unsafe_allow_html=True)

    elif condition_value is not None and quantity > condition_value:
        st.markdown('<p class="highlight-green">यह आइटम स्टॉक में है, कृपया ऑर्डर बुक करने के लिए गोदाम में संपर्क करें</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="highlight-yellow">यह आइटम का स्टॉक कम है, कृपया अधिक जानकारी के लिए गोदाम में संपर्क करें</p>', unsafe_allow_html=True)

    # Display rate formatted to two decimal places and image of the selected item
    if rate is not None:
        formatted_rate = "{:.2f}".format(rate)
    else:
        formatted_rate = "N/A"

    st.markdown(f'<p class="result">Rate: {formatted_rate}</p>', unsafe_allow_html=True)

    image_path_jpeg = os.path.join('OLD ITEMS PHOTOS', f'{item_no}.jpeg')  # Adjust the file extension as needed
    if os.path.exists(image_path_jpeg):
        st.image(image_path_jpeg, caption=f'Image of {item_no}', use_column_width=True)
    else:
        st.markdown('<p class="result">No image available for this ITEM NO.</p>', unsafe_allow_html=True)

    # Only display alternatives when low stock or out of stock
    if quantity is None or quantity == 0 or (condition_value is not None and quantity <= condition_value):
        st.markdown("<h2>Alternatives</h2>", unsafe_allow_html=True)

        # Iterate over the alternative item numbers (Alt1, Alt2, Alt3)
        for alt_item in [alt1, alt2, alt3]:
            if pd.notna(alt_item):  # Check if alternative exists
                # Fetch details for the alternative item (Alt1, Alt2, or Alt3)
                alt_row = master_df[master_df['ITEM NO.'] == alt_item]
                if not alt_row.empty:
                    alt_rate = alt_row['Rate'].values[0]
                    formatted_alt_rate = "{:.2f}".format(alt_rate) if alt_rate is not None else "N/A"

                    # Display the alternative item number and rate
                    st.markdown(f'<p class="result">Alternative Item: {alt_item}, Rate: {formatted_alt_rate}</p>', unsafe_allow_html=True)

                    # Display image for this alternative item if available
                    alt_image_path = os.path.join('OLD ITEMS PHOTOS', f'{alt_item}.jpeg')
                    if os.path.exists(alt_image_path):
                        st.image(alt_image_path, caption=f'Image of {alt_item}', use_column_width=True)
                    else:
                        st.markdown(f'<p class="result">No image available for {alt_item}</p>', unsafe_allow_html=True)

# Footer
st.markdown('<p class="footer">Powered by Jyoti Cards</p>', unsafe_allow_html=True)
