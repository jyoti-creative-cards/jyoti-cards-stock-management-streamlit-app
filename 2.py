import streamlit as st
import pandas as pd
import os

# Load the master dataframe from the CSV file
master_df = pd.read_csv('master_df.csv', dtype=str)

# Ensure that 'ITEM NO.' is a string without any decimal points
master_df['ITEM NO.'] = master_df['ITEM NO.'].str.strip()
master_df['ITEM NO.'] = master_df['ITEM NO.'].str.replace(r'\.0$', '', regex=True)

# Convert 'Quantity', 'Rate', and 'CONDITION' to numeric, handling NaN values
master_df['Quantity'] = pd.to_numeric(master_df['Quantity'], errors='coerce')
master_df['Rate'] = pd.to_numeric(master_df['Rate'], errors='coerce')
master_df['CONDITION'] = pd.to_numeric(master_df['CONDITION'], errors='coerce')

# Handle 'Alt1', 'Alt2', 'Alt3' columns
for col in ['Alt1', 'Alt2', 'Alt3']:
    master_df[col] = master_df[col].str.strip()
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

# You can update this with the actual last update time if needed
st.markdown(f'<p class="last-updated">Last Updated: {pd.to_datetime("today").strftime("%d-%m-%Y %H:%M")}</p>', unsafe_allow_html=True)

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
            st.markdown('<div style="background-color:#f8d7da; padding:10px; border-radius:5px;"><p style="color:#721c24;">यह आइटम स्टॉक में नहीं है, कृपया इसे मिलते जुलते आइटम नीचे देखें</p></div>', unsafe_allow_html=True)
        elif stock_status == 'In Stock':
            st.markdown('<div style="background-color:#d4edda; padding:10px; border-radius:5px;"><p style="color:#155724;">यह आइटम स्टॉक में है</p></div>', unsafe_allow_html=True)
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
        
        # Only display alternatives when low stock or out of stock
        if stock_status in ['Out of Stock', 'Low Stock']:
            st.markdown("<h2>विकल्प</h2>", unsafe_allow_html=True)
            for alt_item in [alt1, alt2, alt3]:
                if alt_item and alt_item.strip() != '':
                    alt_item = alt_item.strip()
                    # Remove any decimal point if present
                    alt_item = alt_item.replace('.0', '')
                    alt_row = master_df[master_df['ITEM NO.'] == alt_item]
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
