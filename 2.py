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
rate_df_cleaned = rate_df.iloc[4:].reset_index(drop=True)
rate_df_cleaned.columns = ['ITEM NO.', 'Rate']

# Now ensure ITEM NO. columns are strings in all dataframes
# Convert 'ITEM NO.' to string in cleaned dataframes
stk_sum_cleaned['ITEM NO.'] = stk_sum_cleaned['ITEM NO.'].astype(str)
rate_df_cleaned['ITEM NO.'] = rate_df_cleaned['ITEM NO.'].astype(str)
condition_df['ITEM NO.'] = condition_df['ITEM NO.'].astype(str)
alternative_df['ITEM NO.'] = alternative_df['ITEM NO.'].astype(str)

# Process the ITEM NO. column (extract the numeric part)
stk_sum_cleaned['ITEM NO.'] = stk_sum_cleaned['ITEM NO.'].apply(lambda x: x.split()[0] if isinstance(x, str) and x.split()[0].isdigit() else x)

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

# Rest of your code...
# (Your Streamlit app code for displaying data and handling user input)
