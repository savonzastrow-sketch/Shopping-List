import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
# from zoneinfo import ZoneInfo # Not needed for Shopping List

# -----------------------
# CONFIG
# -----------------------
DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "shopping_list.csv" 
DATA_DIR.mkdir(exist_ok=True)

# Define Categories
CATEGORIES = ["Vegetables", "Beverages", "Meat/Dairy", "Frozen", "Dry Goods"]

# -----------------------
# PAGE SETUP
# -----------------------
st.set_page_config(page_title="🛒 Shopping List", layout="centered")

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

/* CRITICAL JS SNIPPET (must be run as unsafe_allow_html=True): 
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
# Track active tab in session state
# -----------------------
tabs = ["📝 List"] 

# -----------------------
# DATA LOADING FUNCTION
# -----------------------
def load_data():
    """Loads CSV and ensures necessary columns exist."""
    default_cols = ["timestamp", "item", "purchased", "category"]
    
    if DATA_FILE.exists() and DATA_FILE.stat().st_size > 0:
        try:
            df = pd.read_csv(DATA_FILE)
            # Ensure 'category' column exists for older files
            if 'category' not in df.columns:
                df['category'] = 'Uncategorized' 
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(columns=default_cols)
    else:
        df = pd.DataFrame(columns=default_cols)
    
    # Ensure proper dtypes
    if "purchased" in df.columns:
        df["purchased"] = df["purchased"].astype(bool)
        
    return df


# =====================================================
# TAB 1 — SHOPPING LIST PAGE
# =====================================================
if selected_tab == "📝 List":
    st.markdown(f"<h1>🛒 My Shopping List</h1>", unsafe_allow_html=True)
    
    df = load_data()

    # ----------------------------------------------------
    # ADD ITEM FORM
    # ----------------------------------------------------
    st.subheader("Add an Item")

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
        
        if not new_category:
            st.warning("Please select a category.")
        elif not new_item:
            st.warning("Please enter a valid item name.")
        elif new_item in df["item"].values:
            st.warning("That item is already on the list.")
        else:
            new_row = {
                "timestamp": datetime.now(), 
                "item": new_item, 
                "purchased": False, 
                "category": new_category
            } 
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"'{new_item}' added to the list under '{new_category}'.")
            st.rerun()

    # ----------------------------------------------------
    # DISPLAY ITEM LIST (Category Grouping & Clickable Markdown Hack)
    # ----------------------------------------------------
    if not df.empty:
        st.markdown("---")
        st.subheader("Item Status")

        st.markdown("<p style='font-size:16px; color:gray;'>Click the status or trash can icon to interact.</p>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # CORE LOGIC: Handle clicks from query parameters (FAST RERUN)
        # ----------------------------------------------------
        query_params = st.query_params
        
        # Check for toggle click
        toggle_id = query_params.get("toggle", None)
        if toggle_id and toggle_id.isdigit():
            clicked_idx = int(toggle_id)
            if clicked_idx in df.index:
                df.loc[clicked_idx, "purchased"] = not df.loc[clicked_idx, "purchased"]
                df.to_csv(DATA_FILE, index=False)
                st.query_params.clear() 
                st.rerun()

        # Check for delete click
        delete_id = query_params.get("delete", None)
        if delete_id and delete_id.isdigit():
            clicked_idx = int(delete_id)
            if clicked_idx in df.index:
                df = df.drop(clicked_idx)
                df.to_csv(DATA_FILE, index=False)
                st.query_params.clear() 
                st.rerun()

        # Group and Sort Items: Group by category, then sort by purchased status within each group
        df_grouped = df.sort_values(by=["category", "purchased"])
        
        # Unique categories in the list
        for category, group_df in df_grouped.groupby("category"):
            st.markdown(f"**<span style='font-size: 20px; color: #1f77b4;'>{category}</span>**", unsafe_allow_html=True)
                        
            for idx, row in group_df.iterrows():
                item_name = row["item"]
                purchased = row["purchased"]

                # 1. Determine the status emoji and style (color only)
                status_emoji = "✅" if purchased else "🛒"
                status_style = "color: #888;" if purchased else "color: #000;"
                
                # 2. Link for the status emoji (to toggle purchase)
                toggle_link = f"<a href='?toggle={idx}' style='text-decoration: none; font-size: 18px; flex-shrink: 0; margin-right: 10px; {status_style}'>{status_emoji}</a>"
                
                # 3. Link for the delete emoji (to delete the item)
                delete_link = f"<a href='?delete={idx}' style='text-decoration: none; font-size: 18px; flex-shrink: 0; color: #f00;'>🗑️</a>"

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
