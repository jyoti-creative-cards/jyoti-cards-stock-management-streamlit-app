import streamlit as st
import pandas as pd
import os

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
    .call-button {
        display: inline-block;
        font-size: 1.25em;
        font-weight: bold;
        color: #ffffff;
        background-color: #007bff;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        margin-top: 10px;
        text-decoration: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Add a static box in the middle of the screen
st.markdown('<div class="static-box">Offer of the Day - 5% off</div>', unsafe_allow_html=True)

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

phone_number = "07312456565"
call_button = f'<a href="tel:{phone_number}" class="call-button">Call</a>'

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

    # Display call button
    st.markdown(f'{call_button}', unsafe_allow_html=True)

else:
    st.markdown('<p class="result">Please select an ITEM NO.</p>', unsafe_allow_html=True)

# Footer
st.markdown('<p class="footer">Powered by Jyoti Cards</p>', unsafe_allow_html=True)
