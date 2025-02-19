import streamlit as st
import pandas as pd
import os
import datetime

# File paths
stk_sum_file = 'StkSum_new.xlsx'
rate_list_file = 'rate list merged.xlsx'
alternate_list_file = 'STOCK ALTERNATION LIST.xlsx'
condition_file = '1112.xlsx'

# Load and process the data to regenerate the master_df on every app run
def generate_master_df():
    global stk_sum_file, rate_list_file, alternate_list_file, condition_file
    # Load and process Stk Sum (Stock Summary) sheet
    df_stk_sum = pd.read_excel(stk_sum_file, usecols=[0, 1])
    df_stk_sum = df_stk_sum.iloc[7:].reset_index(drop=True)
   

    # Rename the columns to 'ITEM NO.' and 'Quantity'
    df_stk_sum.columns = ['ITEM NO.', 'Quantity']
    df_stk_sum.columns = ['ITEM NO.', 'Quantity']
    df_stk_sum['ITEM NO.'] = df_stk_sum['ITEM NO.'].str.extract(r'(\d{4})')
    df_stk_sum['Quantity'] = df_stk_sum['Quantity'].astype(str).str.replace(' pcs', '').astype(float) * 100
    df_stk_sum['Quantity'] = df_stk_sum['Quantity'].fillna(0).astype(int)

    # Load and process Rate List sheet
    df_rate_list = pd.read_excel(rate_list_file)
    df_rate_list = df_rate_list.iloc[3:].reset_index(drop=True)
    df_rate_list.columns = ['ITEM NO.', 'Rate']
    df_rate_list['ITEM NO.'] = df_rate_list['ITEM NO.'].str.extract(r'(\d{4})')
    df_rate_list['Rate'] = pd.to_numeric(df_rate_list['Rate'], errors='coerce').fillna(0).astype(float)

    # Load and process Alternate List sheet
    df_alternate = pd.read_excel(alternate_list_file)
    df_alternate = df_alternate[['ITEM NO.', 'Alt1', 'Alt2', 'Alt3']]
    df_alternate['ITEM NO.'] = df_alternate['ITEM NO.'].astype(str)
    df_alternate[['Alt1', 'Alt2', 'Alt3']] = df_alternate[['Alt1', 'Alt2', 'Alt3']].astype(str)

    # Load and process Condition sheet
    df_condition = pd.read_excel(condition_file)
    df_condition.columns = ['ITEM NO.', 'CONDITION']
    df_condition['ITEM NO.'] = df_condition['ITEM NO.'].astype(str)
    df_condition['ITEM NO.'] = df_condition['ITEM NO.'].str.extract(r'(\d{4})')
    df_condition['CONDITION'] = pd.to_numeric(df_condition['CONDITION'], errors='coerce').fillna(0)

    # Merge all datasets into one master dataframe
    master_df = df_stk_sum.merge(df_rate_list, on='ITEM NO.', how='left') \
                          .merge(df_alternate, on='ITEM NO.', how='left') \
                          .merge(df_condition, on='ITEM NO.', how='left')

    # Fill NaN values for missing data
    master_df.fillna({
        'Quantity': 'Not Available', 
        'Rate': 'Not Available', 
        'Alt1': 'None', 
        'Alt2': 'None', 
        'Alt3': 'None', 
        'CONDITION': 'Not Available'
    }, inplace=True)

    return master_df

# Regenerate master_df on app run
master_df = generate_master_df()

# Get the last modified time of 'stk_sum_file'
modification_time = os.path.getmtime(stk_sum_file)
last_update_time = datetime.datetime.fromtimestamp(modification_time)

# Ensure that 'ITEM NO.' is a string without any decimal points
master_df['ITEM NO.'] = master_df['ITEM NO.'].str.strip()
master_df['ITEM NO.'] = master_df['ITEM NO.'].str.replace(r'\.0$', '', regex=True)

# Convert 'Quantity', 'Rate', and 'CONDITION' to numeric, handling NaN values
master_df['Quantity'] = pd.to_numeric(master_df['Quantity'], errors='coerce')
master_df['Rate'] = pd.to_numeric(master_df['Rate'], errors='coerce')
master_df['CONDITION'] = pd.to_numeric(master_df['CONDITION'], errors='coerce')

# Handle 'Alt1', 'Alt2', 'Alt3' columns
for col in ['Alt1', 'Alt2', 'Alt3']:
    master_df[col] = master_df[col].astype(str).str.strip()
    master_df[col] = master_df[col].replace(['nan', 'None', 'NaN'], '')
    master_df[col] = master_df[col].str.replace(r'\.0$', '', regex=True)


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
    for ext in ['jpeg', 'jpg', 'png']:
        image_path = os.path.join('static', f'{item_no}.{ext}')
        if os.path.exists(image_path):
            return image_path
    return None

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

# Update the Last Updated time display
st.markdown(
    f'<p class="last-updated">Last Updated: {last_update_time.strftime("%d-%m-%Y %H:%M")}</p>',
    unsafe_allow_html=True
)

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

# Check if the user has entered an item number
if item_no:
    # Remove any leading/trailing whitespace
    item_no = item_no.strip()
    # Remove any decimal point if present
    item_no = item_no.replace('.0', '')
    print("Item number entered:", item_no)
    
    # Check if ITEM NO. exists in master data
    item_row = master_df[master_df['ITEM NO.'] == item_no]
    
    if not item_row.empty:
        quantity = item_row['Quantity'].values[0]
        condition_value = item_row['CONDITION'].values[0] if 'CONDITION' in item_row.columns else None
        rate = item_row['Rate'].values[0] if 'Rate' in item_row.columns else None
        alt1 = item_row['Alt1'].values[0] if 'Alt1' in item_row.columns else ''
        alt2 = item_row['Alt2'].values[0] if 'Alt2' in item_row.columns else ''
        alt3 = item_row['Alt3'].values[0] if 'Alt3' in item_row.columns else ''
        
        stock_status = get_stock_status(quantity, condition_value)
        
        # Display stock status in colored box with Hindi messages
        if stock_status == 'Out of Stock':
            st.markdown('<div style="background-color:#f8d7da; padding:10px; border-radius:5px;"><p style="color:#721c24;">यह आइटम का स्टॉक कम है, कृपया शिग्र गोदाम पर बुक करें</p></div>', unsafe_allow_html=True)
       # Adjusted 'In Stock' message
        elif stock_status == 'In Stock':
            st.markdown(
                '''
                <div style="background-color:#d4edda; padding:10px; border-radius:5px;">
                    <p style="color:#155724;">
                        यह आइटम स्टॉक में है,<br>(कृपया गोदाम पर बुकिंग के लिए कॉल करें)
                    </p>
                </div>
                ''', 
                unsafe_allow_html=True
            )
        else:
            st.markdown('<div style="background-color:#fff3cd; padding:10px; border-radius:5px;"><p style="color:#856404;">यह आइटम का स्टॉक कम है, कृपया शिग्र गोदाम पर बुक करें</p></div>', unsafe_allow_html=True)
        
        # Display rate
        formatted_rate = "{:.2f}".format(rate) if pd.notna(rate) else "N/A"
        st.markdown(f'<p class="result">रेट: {formatted_rate}</p>', unsafe_allow_html=True)
        
        # Display image
        image_path = get_image_path(item_no)
        if image_path:
            st.image(image_path, caption=f'Image of {item_no}', use_column_width=True)
        else:
            st.markdown('<p class="result">इस आइटम नंबर के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
        
        # Always display alternatives
        st.markdown("<h2>विकल्प</h2>", unsafe_allow_html=True)
        for alt_item in [alt1, alt2, alt3]:
            # Ensure alt_item is a string and not NaN
            alt_item = '' if pd.isna(alt_item) else str(alt_item).strip()
            if alt_item != '' and alt_item.lower() != 'nan':
                # Remove any decimal point if present
                alt_item = alt_item.replace('.0', '')
                alt_row = master_df[master_df['ITEM NO.'] == alt_item]
                if not alt_row.empty:
                    alt_quantity = alt_row['Quantity'].values[0]
                    alt_condition_value = alt_row['CONDITION'].values[0] if 'CONDITION' in alt_row.columns else None
                    alt_rate = alt_row['Rate'].values[0] if 'Rate' in alt_row.columns else None
                    formatted_alt_rate = "{:.2f}".format(alt_rate) if pd.notna(alt_rate) else "N/A"
                    
                    alt_stock_status = get_stock_status(alt_quantity, alt_condition_value)
                    
                    # Display alternative stock status in Hindi
                    if alt_stock_status == 'In Stock':
                        alt_status_message = 'स्टॉक में उपलब्ध'
                    elif alt_stock_status == 'Low Stock':
                        alt_status_message = 'स्टॉक कम है'
                    else:
                        alt_status_message = 'स्टॉक कम है'
                    
                    st.markdown(f'<p class="result">वैकल्पिक आइटम: {alt_item}, रेट: {formatted_alt_rate}, स्टॉक स्थिति: {alt_status_message}</p>', unsafe_allow_html=True)
                    alt_image_path = get_image_path(alt_item)
                    if alt_image_path:
                        st.image(alt_image_path, caption=f'Image of {alt_item}', use_column_width=True)
                    else:
                        st.markdown(f'<p class="result">{alt_item} के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p class="result">वैकल्पिक आइटम {alt_item} उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="result">आइटम नंबर उपलब्ध नहीं है</p>', unsafe_allow_html=True)
else:
    st.markdown('<p class="result">कृपया एक आइटम नंबर दर्ज करें</p>', unsafe_allow_html=True)

# Footer
st.markdown('<p class="footer">Powered by Jyoti Cards</p>', unsafe_allow_html=True)
