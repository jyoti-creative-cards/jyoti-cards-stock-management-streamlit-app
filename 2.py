import streamlit as st
import pandas as pd
import os
import datetime
import pytz

tz = pytz.timezone('Asia/Kolkata') 
#modification_time = os.path.getmtime(stk_sum_file)


st.markdown(
    f'Last Updated: {last_update_time.strftime("%d-%m-%Y %H:%M")}'
)
# File paths
stk_sum_file = 'StkSum_new.xlsx'
rate_list_file = 'rate list merged.xlsx'
alternate_list_file = 'STOCK ALTERNATION LIST.xlsx'
condition_file = '1112.xlsx'

# Use the file's modification time as the "Last Updated" time
modification_time = os.path.getmtime(stk_sum_file)
last_update_time = datetime.datetime.fromtimestamp(modification_time, tz)
#last_update_time = datetime.datetime.fromtimestamp(modification_time)

def generate_master_df():
    # Load and process Stock Summary (StkSum) sheet using columns A and C (indexes 0 and 2)
    df_stk_sum = pd.read_excel(stk_sum_file, usecols=[0, 2])
    df_stk_sum = df_stk_sum.iloc[7:].reset_index(drop=True)
    df_stk_sum.columns = ['ITEM NO.', 'Quantity']
    # Extract digits and trim any extra spaces
    df_stk_sum['ITEM NO.'] = df_stk_sum['ITEM NO.'].astype(str).str.extract(r'(\d+)', expand=False).str.strip()
    df_stk_sum['Quantity'] = (df_stk_sum['Quantity'].astype(str)
                              .str.replace(' pcs', '')
                              .astype(float) * 100)
    df_stk_sum['Quantity'] = df_stk_sum['Quantity'].fillna(0).astype(int)

    # Load and process Rate List sheet
    df_rate_list = pd.read_excel(rate_list_file)
    df_rate_list = df_rate_list.iloc[3:].reset_index(drop=True)
    df_rate_list.columns = ['ITEM NO.', 'Rate']
    df_rate_list['ITEM NO.'] = df_rate_list['ITEM NO.'].astype(str).str.extract(r'(\d+)', expand=False).str.strip()
    df_rate_list['Rate'] = pd.to_numeric(df_rate_list['Rate'], errors='coerce').fillna(0).astype(float)

    # Load and process Alternate List sheet
    df_alternate = pd.read_excel(alternate_list_file)
    df_alternate = df_alternate[['ITEM NO.', 'Alt1', 'Alt2', 'Alt3']]
    df_alternate['ITEM NO.'] = df_alternate['ITEM NO.'].astype(str).str.extract(r'(\d+)', expand=False).str.strip()
    df_alternate[['Alt1', 'Alt2', 'Alt3']] = df_alternate[['Alt1', 'Alt2', 'Alt3']].astype(str)

    # Load and process Condition sheet
    df_condition = pd.read_excel(condition_file)
    df_condition.columns = ['ITEM NO.', 'CONDITION']
    df_condition['ITEM NO.'] = df_condition['ITEM NO.'].astype(str)\
                                               .str.extract(r'(\d+)', expand=False)\
                                               .str.strip()
    df_condition['CONDITION'] = pd.to_numeric(df_condition['CONDITION'], errors='coerce').fillna(0)

    # Merge all datasets into one master dataframe
    master_df = df_stk_sum.merge(df_rate_list, on='ITEM NO.', how='left') \
                          .merge(df_alternate, on='ITEM NO.', how='left') \
                          .merge(df_condition, on='ITEM NO.', how='left')

    master_df.fillna({
        'Quantity': 'Not Available', 
        'Rate': 'Not Available', 
        'Alt1': 'None', 
        'Alt2': 'None', 
        'Alt3': 'None', 
        'CONDITION': 'Not Available'
    }, inplace=True)

    return master_df

master_df = generate_master_df()

# Clean up fields in master_df
master_df['ITEM NO.'] = master_df['ITEM NO.'].str.strip().str.replace(r'\.0$', '', regex=True)
master_df['Quantity'] = pd.to_numeric(master_df['Quantity'], errors='coerce')
master_df['Rate'] = pd.to_numeric(master_df['Rate'], errors='coerce')
master_df['CONDITION'] = pd.to_numeric(master_df['CONDITION'], errors='coerce')
for col in ['Alt1', 'Alt2', 'Alt3']:
    master_df[col] = master_df[col].astype(str).str.strip()
    master_df[col] = master_df[col].replace(['nan', 'None', 'NaN'], '')
    master_df[col] = master_df[col].str.replace(r'\.0$', '', regex=True)

# Helper function to determine stock status
def get_stock_status(quantity, condition_value):
    if pd.isna(quantity) or quantity == 0:
        return 'Out of Stock'
    elif pd.isna(condition_value):
        return 'In Stock'
    elif quantity > condition_value:
        return 'In Stock'
    else:
        return 'Low Stock'

# Helper function to get image path
def get_image_path(item_no):
    for ext in ['jpeg', 'jpg', 'png']:
        image_path = os.path.join('static', f'{item_no}.{ext}')
        if os.path.exists(image_path):
            return image_path
    return None

# Helper to encode image to base64
def get_base64_image(image_path):
    import base64
    with open(image_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Custom CSS styling
st.markdown(
    """
    <style>
    .main { background-color: #ffffff; }
    .stApp { background-color: #ffffff; }
    .title { font-size: 2.2em; color: #4e8cff; font-weight: bold; text-align: center; margin-top: 1em; }
    </style>
    """,
    unsafe_allow_html=True
)

# Display logo if exists
logo_path = 'static/jyoti logo-1.png'
if os.path.exists(logo_path):
    logo_base64 = get_base64_image(logo_path)
    st.markdown(f'<img src="data:image/png;base64,{logo_base64}" class="logo">', unsafe_allow_html=True)

# Display the file's last updated time
st.markdown(
    f'<p class="last-updated">Last Updated: {last_update_time.strftime("%d-%m-%Y %H:%M")}</p>',
    unsafe_allow_html=True
)

st.markdown('<h1 class="title">Jyoti Cards Stock Status</h1>', unsafe_allow_html=True)

# Call button with call icon
call_icon_url = 'static/call_icon.png'
if os.path.exists(call_icon_url):
    call_icon_base64 = get_base64_image(call_icon_url)
    phone_number = "07312456565"
    call_button = f'''
    <a href="tel:{phone_number}" class="call-link">
        <img src="data:image/png;base64,{call_icon_base64}" width="24" height="24" alt="Call Icon">
        Call
    </a>
    '''
    st.markdown(call_button, unsafe_allow_html=True)

# Input for item number
item_no = st.text_input('', placeholder='🔍 कृपया आइटम नंबर यहां डालें')

if item_no:
    item_no = item_no.strip().replace('.0', '')
    st.write("Item number entered:", item_no)
    item_row = master_df[master_df['ITEM NO.'] == item_no]
    
    if not item_row.empty:
        # Main item exists: extract values
        quantity = item_row['Quantity'].values[0]
        condition_value = item_row['CONDITION'].values[0] if 'CONDITION' in item_row.columns else None
        rate = item_row['Rate'].values[0] if 'Rate' in item_row.columns else None
        
        # Instead of using merged Alt1, Alt2, Alt3 from master_df, re-read alternate list for alternatives:
        df_alt = pd.read_excel(alternate_list_file)
        df_alt['ITEM NO.'] = df_alt['ITEM NO.'].astype(str).str.extract(r'(\d+)', expand=False).str.strip()
        alt_row = df_alt[df_alt['ITEM NO.'] == item_no]
        
        stock_status = get_stock_status(quantity, condition_value)
        
        if stock_status == 'In Stock':
            st.markdown(
                '<div style="background-color:#d4edda; padding:10px; border-radius:5px;">'
                '<p style="color:#155724;">यह आइटम स्टॉक में है,<br>(कृपया गोदाम पर बुकिंग के लिए कॉल करें)</p></div>',
                unsafe_allow_html=True
            )
        else:
            if stock_status == 'Out of Stock':
                st.markdown(
                    '<div style="background-color:#f8d7da; padding:10px; border-radius:5px;">'
                    '<p style="color:#721c24;">यह आइटम का स्टॉक कम है, कृपया शीघ्र गोदाम पर बुक करें</p></div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div style="background-color:#fff3cd; padding:10px; border-radius:5px;">'
                    '<p style="color:#856404;">यह आइटम का स्टॉक कम है, कृपया शीघ्र गोदाम पर बुक करें</p></div>',
                    unsafe_allow_html=True
                )
        
        formatted_rate = "{:.2f}".format(rate) if pd.notna(rate) else "N/A"
        st.markdown(f'<p class="result">रेट: {formatted_rate}</p>', unsafe_allow_html=True)
        
        # Display main item image
        image_path = get_image_path(item_no)
        if image_path:
            st.image(image_path, caption=f'Image of {item_no}', use_container_width=True)
        else:
            st.markdown('<p class="result">इस आइटम नंबर के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
        
        # Show alternatives only if main item is not in stock and alternative info exists
        if stock_status != 'In Stock':
            st.markdown("<h2>विकल्प</h2>", unsafe_allow_html=True)
            if not alt_row.empty:
                alt1, alt2, alt3 = alt_row.iloc[0][['Alt1', 'Alt2', 'Alt3']]
                for alt_item in [alt1, alt2, alt3]:
                    alt_item = '' if pd.isna(alt_item) else str(alt_item).strip()
                    if alt_item and alt_item.lower() != 'nan':
                        alt_item = alt_item.replace('.0', '')
                        alt_master_row = master_df[master_df['ITEM NO.'] == alt_item]
                        if not alt_master_row.empty:
                            alt_quantity = alt_master_row['Quantity'].values[0]
                            alt_condition_value = alt_master_row['CONDITION'].values[0] if 'CONDITION' in alt_master_row.columns else None
                            alt_stock_status = get_stock_status(alt_quantity, alt_condition_value)
                            if alt_stock_status == 'In Stock':
                                alt_rate = alt_master_row['Rate'].values[0]
                                formatted_alt_rate = "{:.2f}".format(alt_rate) if pd.notna(alt_rate) else "N/A"
                                st.markdown(
                                    f'<p class="result">वैकल्पिक आइटम: {alt_item}, रेट: {formatted_alt_rate}, स्टॉक स्थिति: स्टॉक में उपलब्ध</p>',
                                    unsafe_allow_html=True
                                )
                                alt_image_path = get_image_path(alt_item)
                                if alt_image_path:
                                    st.image(alt_image_path, caption=f'Image of {alt_item}', use_container_width=True)
                                else:
                                    st.markdown(f'<p class="result">{alt_item} के लिए कोई छवि उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<p class="result">वैकल्पिक आइटम: {alt_item} का स्टॉक उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<p class="result">वैकल्पिक आइटम {alt_item} उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p class="result">इस आइटम के लिए कोई वैकल्पिक आइटम उपलब्ध नहीं हैं।</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="result">मुख्य आइटम उपलब्ध नहीं है।</p>', unsafe_allow_html=True)
else:
    st.markdown('<p class="result">कृपया एक आइटम नंबर दर्ज करें</p>', unsafe_allow_html=True)

st.markdown('<p class="footer">Powered by Jyoti Cards</p>', unsafe_allow_html=True)
