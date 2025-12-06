import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import json # New Import for handling secrets
from io import StringIO # New Import for handling CSV string

# New Imports for Google Drive
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# -----------------------
# CONFIG
# -----------------------
# **REPLACE THIS WITH YOUR TARGET GOOGLE DRIVE FOLDER ID**
SHOPPING_FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID" 
SHOPPING_FILE_NAME = "shopping_list.csv" # The file name on Drive

# Define Categories and Stores
CATEGORIES = ["Vegetables", "Beverages", "Meat/Dairy", "Frozen", "Dry Goods"]
STORES = ["Costco", "Trader Joe's", "Whole Foods", "Other"] 

# -----------------------
# PAGE SETUP
# -----------------------
st.set_page_config(page_title="🛒 Shopping List", layout="centered")


# -----------------------
# GOOGLE DRIVE FUNCTIONS
# -----------------------
@st.cache_resource
def get_drive_service():
    """Authenticates and returns the GoogleDrive service object using Streamlit Secrets."""
    
    # 1. Get the Service Account info from Streamlit secrets
    # The secrets are stored under the [gcp_service_account] key in the TOML file (as seen on the screen)
    # We must construct a dictionary containing the secret values
    
    # Use st.secrets to securely access the credentials
    info = {
        "type": "service_account",
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        # The private_key must be handled carefully: it's stored in Streamlit secrets 
        # as a multi-line string with escaped newlines.
        "private_key": st.secrets["gcp_service_account"]["private_key"].replace('\\n', '\n'),
        "token_uri": "https://oauth2.googleapis.com/token"
    }
    
    # 2. Configure PyDrive2 to use the JSON content directly
    gauth = GoogleAuth()
    
    # Configure settings to use the JSON content
    gauth.settings = {
        "client_config": {
            "service_account": {
                "credential_file_content": json.dumps(info)
            }
        }
    }
    
    # 3. Authenticate and return service
    gauth.ServiceAuth()
    return GoogleDrive(gauth)


def read_shopping_file(drive):
    """Reads the shopping list CSV file from Drive."""
    # 1. Find the file in the specific folder
    file_list = drive.ListFile({
        'q': f"'{SHOPPING_FOLDER_ID}' in parents and title = '{SHOPPING_FILE_NAME}' and trashed=false"
    }).GetList()

    if not file_list:
        # File doesn't exist, return None
        return None, None 

    # 2. Get the content
    file = file_list[0]
    file_id = file['id']
    content = file.GetContentString(encoding='utf-8')
    
    return content, file_id

def write_shopping_file(drive, content, file_id=None):
    """Writes content to the shopping list file on Drive."""
    if file_id:
        # Update existing file
        file = drive.CreateFile({'id': file_id})
    else:
        # Create new file
        file = drive.CreateFile({
            'title': SHOPPING_FILE_NAME, 
            'parents': [{'id': SHOPPING_FOLDER_ID}],
            'mimeType': 'text/csv'
        })
    
    file.SetContentString(content)
    file.Upload()
    return file['id']


# -----------------------
# DATA LOADING FUNCTION (Google Drive Version)
# -----------------------
def load_data():
    """Loads CSV from Google Drive and ensures necessary columns exist."""
    
    # 1. Get Drive Service
    drive = get_drive_service()
    
    # 2. Define expected columns
    default_cols = ["timestamp", "item", "purchased", "category", "store"]
    
    # 3. Read content from Drive
    content, file_id = read_shopping_file(drive)
    
    if content:
        # Read the content string into a DataFrame
        df = pd.read_csv(StringIO(content))
        
        # Store the file_id in session state for later updates
        st.session_state['shopping_file_id'] = file_id
    else:
        # File does not exist, create a new empty DataFrame
        df = pd.DataFrame(columns=default_cols)
        st.session_state['shopping_file_id'] = None # No ID yet

    # 4. Post-load processing (Ensure columns and dtypes)
    for col in default_cols:
        if col not in df.columns:
            df[col] = 'Uncategorized' if col == 'category' else ('Other' if col == 'store' else None)
            
    if "purchased" in df.columns:
        df["purchased"] = df["purchased"].astype(bool)
        
    return df

# -----------------------
# DATA SAVING FUNCTION
# -----------------------
def save_data(df):
    """Saves the DataFrame content to Google Drive."""
    # 1. Get Drive Service and File ID
    drive = get_drive_service()
    file_id = st.session_state.get('shopping_file_id')
    
    # 2. Convert DataFrame to CSV string
    csv_string = df.to_csv(index=False)
    
    # 3. Write to Drive and update File ID
    new_file_id = write_shopping_file(drive, csv_string, file_id)
    st.session_state['shopping_file_id'] = new_file_id


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
        save_data(df) # UPDATED TO SAVE TO DRIVE
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
        save_data(df) # UPDATED TO SAVE TO DRIVE
        st.query_params.clear() 
        st.rerun()

# Check for delete click
delete_id = query_params.get("delete", None)
if delete_id and delete_id.isdigit():
    clicked_idx = int(delete_id)
    if clicked_idx in df.index:
        df = df.drop(clicked_idx)
        save_data(df) # UPDATED TO SAVE TO DRIVE
        st.query_params.clear() 
        st.rerun()
