
import pandas as pd

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



master_df_cleaned.to_excel('master_df.xlsx')
