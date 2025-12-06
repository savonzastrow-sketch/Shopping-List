import streamlit as st
import pandas as pd
from datetime import datetime
import json
from io import StringIO

# NEW Imports for Google Sheets/Gspread
import gspread
from gspread_dataframe import set_with_dataframe, get_dataframe

# -----------------------
# CONFIG
# -----------------------
# NOTE: We only need the file name now, as gspread uses the name to find the sheet
SHOPPING_FILE_NAME = "shopping_list_data" # Using a sheet name instead of a file/CSV name
# We no longer need FOLDER_ID or DELEGATED_EMAIL for gspread service account access.

# Define Categories and Stores
CATEGORIES = ["Vegetables", "Beverages", "Meat/Dairy", "Frozen", "Dry Goods"]
STORES = ["Costco", "Trader Joe's", "Whole Foods", "Other"] 

# -----------------------
# PAGE SETUP
# -----------------------
st.set_page_config(page_title="🛒 Shopping List", layout="centered")


# ----------------------------------------------------------------------------------
# GOOGLE SPREADSHEETS FUNCTIONS (Using Gspread)
# ----------------------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    """Authenticates using Service Account JSON from Streamlit Secrets."""
    
    # 1. Get the Service Account info from Streamlit secrets
    # Uses the service account info you already configured
    info = st.secrets["gcp_service_account"]
    
    # 2. Authenticate and return the gspread client
    client = gspread.service_account_from_dict(info)
    return client

def get_or_create_worksheet(client):
    """Opens the shopping list sheet or creates a new one."""
    
    try:
        # Try to open the sheet by its exact name
        spreadsheet = client.open(SHOPPING_FILE_NAME)
        # We will use the first worksheet (default)
        worksheet = spreadsheet.sheet1
        
    except gspread.SpreadsheetNotFound:
        # Sheet does not exist, create it
        spreadsheet = client.create(SHOPPING_FILE_NAME)
        # NOTE: You will need to manually 'share' this new sheet with the service account email 
        # (client_email from your secrets) the first time it is created.
        worksheet = spreadsheet.sheet1
        
    return worksheet


def load_data():
    """Loads data from Google Sheet and ensures necessary columns exist."""
    
    # 1. Get Gspread Client and Worksheet
    client = get_gspread_client()
    worksheet = get_or_create_worksheet(client)
    
    # 2. Define expected columns
    default_cols = ["timestamp", "item", "purchased", "category", "store"]
    
    # 3. Read content from the sheet using gspread-dataframe
    try:
        df = get_dataframe(worksheet, evaluate_formulas=True, header=1)
        
        # If the sheet is completely empty (no data or header), df might be empty/non-existent
        if df.empty or 'item' not in df.columns:
            df = pd.DataFrame(columns=default_cols)
            # Create a header row on the sheet if it was empty
            if worksheet.row_count < 1:
                worksheet.append_row(default_cols)
            
    except Exception:
        # Handle errors during read (e.g., sheet entirely empty)
        df = pd.DataFrame(columns=default_cols)
        
    # 4. Post-load processing (Ensure columns and dtypes)
    for col in default_cols:
        if col not in df.columns:
            df[col] = 'Uncategorized' if col == 'category' else ('Other' if col == 'store' else None)
            
    if "purchased" in df.columns:
        df["purchased"] = df["purchased"].astype(bool)
        
    # Store the worksheet object in session state for saving
    st.session_state['worksheet'] = worksheet
    
    return df

def save_data(df):
    """Saves the DataFrame content back to Google Sheet."""
    
    worksheet = st.session_state['worksheet']
    
    # Use gspread-dataframe to write the entire dataframe back to the sheet
    set_with_dataframe(worksheet, df, include_index=False, row=1, col=1)


# -----------------------
# STYLES (Includes JavaScript for faster internal rerun)
# -----------------------
st.markdown("""
<style>
h1 { font-size: 32px !important; text-align: center; }
h2 { font-size: 28px !important; text-align: center; }
p, div, label, .stMarkdown { font-size: 18px !important; line-height: 1.6; }

/* General button style (Kept for other buttons) */
.stButton>button {
    border-radius: 12px; font-size: 16px; font-weight: 500; transition: all 0.2s ease; padding: 6px 12px;
}

/* Hide the main Streamlit element padding on small screens for max space */
@media (max-width: 480px) {
    /* Target main content padding */
    .st-emotion-cache-1pxx0nch { 
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
}

/* CRITICAL JS SNIPPET: 
This script ensures that when a link with '?toggle=' or '?delete=' is clicked, 
it updates the URL but does NOT trigger a full browser navigation/refresh, 
allowing Streamlit to handle the update faster.
*/
<script>
    document.addEventListener('DOMContentLoaded', () => {
        document.body.addEventListener('click', (e) => {
            if (e.target.tagName === 'A' && (e.target.href.includes('?toggle=') || e.target.href.includes('?delete='))) {
                e.preventDefault();
                history.pushState(null, '', e.target.href);
                window.location.reload(true);
            }
        });
    });
</script>

</style>
""", unsafe_allow_html=True)


# -----------------------
# APP START
# -----------------------

st.markdown(f"<h1>🛒 Shopping List</h1>", unsafe_allow_html=True)

# Load data uses the new Gspread function
df = load_data() 

# =====================================================
# ADD ITEM FORM (Outside of tabs so it's always visible)
# =====================================================
st.subheader("Add an Item")

# --- Store Selection ---
new_store = st.selectbox(
    "Select Store",
    STORES,
    index=None,
    placeholder="Choose a store..."
)

# --- Category Selection ---
new_category = st.selectbox(
    "Select Category", 
    CATEGORIES,
    index=None,
    placeholder="Choose a category..."
)
new_item = st.text_input("Enter the item to purchase", autocomplete="off") 

if st.button("Add Item"):
    new_item = new_item.strip()
    
    if not new_store:
        st.warning("Please select a store.")
    elif not new_category:
        st.warning("Please select a category.")
    elif not new_item:
        st.warning("Please enter a valid item name.")
    elif new_item in df["item"].values:
        st.warning("That item is already on the list.")
    else:
        # Save the new item with both category and store
        new_row = {
            "timestamp": datetime.now(), 
            "item": new_item, 
            "purchased": False, 
            "category": new_category,
            "store": new_store
        } 
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df) # UPDATED TO SAVE VIA GSPREAD
        st.success(f"'{new_item}' added to the list for {new_store} under '{new_category}'.")
        st.rerun()

st.markdown("---")
st.subheader("Items by Store")

# =====================================================
# STORE TABS NAVIGATION
# =====================================================

# Create the tabs dynamically
store_tabs = st.tabs(STORES)

# Loop through the store tabs to display the filtered list in each one
for store_name, store_tab in zip(STORES, store_tabs):
    with store_tab:
        
        # Filter the main DataFrame for the current store
        df_store = df[df['store'] == store_name]
        
        if df_store.empty:
            st.info(f"The list for **{store_name}** is empty. Add items above!")
            continue

        # Group and Sort Items: Group by category, then sort by purchased status within each group
        df_grouped = df_store.sort_values(by=["category", "purchased"])
        
        # Unique categories in the list
        for category, group_df in df_grouped.groupby("category"):
            # Uses the margin fix you added earlier
            st.markdown(f"**<span style='font-size: 20px; color: #1f77b4; margin-bottom: 0px !important;'>{category}</span>**", unsafe_allow_html=True)
                       
            for idx, row in group_df.iterrows():
                item_name = row["item"]
                purchased = row["purchased"]

                # 1. Determine the status emoji and style (color only)
                status_emoji = "✅" if purchased else "🛒"
                status_style = "color: #888;" if purchased else "color: #000;"
                
                # 2. Link for the status emoji (to toggle purchase)
                toggle_link = f"<a href='?toggle={idx}' target='_self' style='text-decoration: none; font-size: 18px; flex-shrink: 0; margin-right: 10px; {status_style}'>{status_emoji}</a>"
                
                # 3. Link for the delete emoji (to delete the item)
                delete_link = f"<a href='?delete={idx}' target='_self' style='text-decoration: none; font-size: 18px; flex-shrink: 0; color: #f00;'>🗑️</a>"

                # 4. Item Name display (no link)
                item_name_display = f"<span style='font-size: 14px; flex-grow: 1; {status_style}'>{item_name}</span>"

                # 5. Assemble the entire row in a single Markdown block using flexbox
                item_html = f"""
                <div style='display: flex; align-items: center; justify-content: space-between; padding: 8px 5px; margin-bottom: 3px; border-bottom: 1px solid #eee; min-height: 40px;'>
                    <div style='display: flex; align-items: center; flex-grow: 1; min-width: 1px;'>
                        {toggle_link}
                        {item_name_display}
                    </div>
                    {delete_link}
                </div>
                """
                st.markdown(item_html, unsafe_allow_html=True)
                
# ----------------------------------------------------
# FINAL CORE LOGIC BLOCK (MUST be placed at the very end of the script)
# This handles the clicks generated by the links in the loops above
# ----------------------------------------------------
query_params = st.query_params

# Check for toggle click
toggle_id = query_params.get("toggle", None)
if toggle_id and toggle_id.isdigit():
    clicked_idx = int(toggle_id)
    if clicked_idx in df.index:
        df.loc[clicked_idx, "purchased"] = not df.loc[clicked_idx, "purchased"]
        save_data(df) # SAVING VIA GSPREAD
        st.query_params.clear() 
        st.rerun()

# Check for delete click
delete_id = query_params.get("delete", None)
if delete_id and delete_id.isdigit():
    clicked_idx = int(delete_id)
    if clicked_idx in df.index:
        df = df.drop(clicked_idx)
        save_data(df) # SAVING VIA GSPREAD
        st.query_params.clear() 
        st.rerun()
