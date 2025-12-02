import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
# from zoneinfo import ZoneInfo # Not needed for Shopping List

# -----------------------
# CONFIG
# -----------------------
# TIMEZONE = ZoneInfo("America/New_York") # Not needed
DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "shopping_list.csv" # Renamed data file
# EVENT_FILE = DATA_DIR / "event_date.txt" # Removed
# EVENT_LOCATION_FILE = DATA_DIR / "event_location.txt" # Removed
DATA_DIR.mkdir(exist_ok=True)

# -----------------------
# PAGE SETUP
# -----------------------
st.set_page_config(page_title="🛒 Shopping List", layout="centered")

# -----------------------
# STYLES (Kept styling for layout)
# -----------------------
st.markdown("""
<style>
h1 { font-size: 32px !important; text-align: center; }
h2 { font-size: 28px !important; text-align: center; }
p, div, label, .stMarkdown { font-size: 18px !important; line-height: 1.6; }

/* General button style (kept original) */
.stButton>button {
    border-radius: 12px; 
    font-size: 16px; 
    font-weight: 500; 
    transition: all 0.2s ease;
    padding: 6px 12px;
}

/* --- MOBILE SPECIFIC OVERRIDES --- */
@media (max-width: 480px) {
    /* 1. Target ALL buttons on small screens and reduce padding */
    .stButton>button {
        padding: 4px 6px !important; 
        font-size: 14px; 
        line-height: 1;
        min-width: unset;
    }
    
    /* 2. TARGET COLUMN SPACING: Set horizontal padding of columns to zero */
    /* This class targets the internal Streamlit column container */
    .st-emotion-cache-18ni7ap { 
        padding-left: 0px !important;
        padding-right: 0px !important;
    }

    .player-row { flex-direction: row; gap: 6px; padding: 10px 2px; }
    .player-name { font-size: 16px; }
    .toggle-btn { font-size: 14px; min-width: 120px; padding: 5px 8px; }
}
</style>
""", unsafe_allow_html=True)

# -----------------------
# Track active tab in session state
# -----------------------
tabs = ["📝 List", "🔒 Admin"] # Updated tab names
selected_tab = st.session_state.get("selected_tab", tabs[0])
selected_tab = st.radio("Navigation", tabs, horizontal=True, label_visibility="collapsed")

# Detect tab switch
previous_tab = st.session_state.get("previous_tab", None)
if previous_tab != selected_tab:
    st.session_state["previous_tab"] = selected_tab
    # Refresh list page when switching back
    if selected_tab == "📝 List":
        st.rerun()

st.session_state["selected_tab"] = selected_tab

# =====================================================
# TAB 1 — SHOPPING LIST PAGE
# =====================================================
if selected_tab == "📝 List":
    st.markdown(f"<h1>🛒 My Shopping List</h1>", unsafe_allow_html=True)
    # st.markdown(f"<p>Event date: <b>{EVENT_DATE_STR}</b></p>", unsafe_allow_html=True) # Removed
    # st.markdown(f"<p>Event location: <b>{EVENT_LOCATION}</b></p>", unsafe_allow_html=True) # Removed

    # Load data
    if DATA_FILE.exists() and DATA_FILE.stat().st_size > 0:
        try:
            df = pd.read_csv(DATA_FILE)
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(columns=["timestamp", "item", "purchased"]) # Updated column name
    else:
        df = pd.DataFrame(columns=["timestamp", "item", "purchased"]) # Updated column name

    # Ensure proper dtypes
    if "purchased" in df.columns:
        df["purchased"] = df["purchased"].astype(bool) # Updated column name

    # Input field for adding a new item
    st.subheader("Add an Item") # Updated heading

    # --- ADDED autocomplete="off" HERE ---
    new_item = st.text_input("Enter the item to purchase", autocomplete="off") 
    # -------------------------------------
 
    if st.button("Add Item"): # Updated button label
        new_item = new_item.strip()
        if not new_item:
            st.warning("Please enter a valid item name.")
        elif new_item in df["item"].values: # Updated column name
            st.warning("That item is already on the list.")
        else:
            new_row = {"timestamp": datetime.now(), "item": new_item, "purchased": False} # Updated column name
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"'{new_item}' added to the list.")
            st.rerun()

    # Display item list in a responsive, mobile-friendly layout
    if not df.empty:
    st.markdown("---")
    st.subheader("Item Status") # Updated heading

    # Instruction text
    st.markdown("<p style='font-size:16px; color:gray;'>Click the item's emoji status to toggle the purchase status.</p>", unsafe_allow_html=True)

    # Handle clicks from query parameters
    query_params = st.query_params
    clicked_item_id = query_params.get("toggle", None)
    
    if clicked_item_id and clicked_item_id.isdigit():
        clicked_idx = int(clicked_item_id)
        if 0 <= clicked_idx < len(df):
            # Toggle the 'purchased' status
            df.loc[clicked_idx, "purchased"] = not df.loc[clicked_idx, "purchased"]
            df.to_csv(DATA_FILE, index=False)
            
            # Clear the query param and Rerun to show the update
            st.query_params.clear() 
            st.rerun()

    # Build Header Row (Simpler Header)
    st.markdown("<div style='display: flex; font-weight: bold; margin-bottom: 5px;'>Status / Item</div>", unsafe_allow_html=True)
    st.markdown("---")

    # Sort to show "Not Purchased" items first, then "Purchased"
    df = df.reset_index(drop=True).sort_values(by="purchased")

    for idx, row in df.iterrows():
        item_name = row["item"]
        purchased = row["purchased"]

        # 1. Determine the status emoji and background color
        status_emoji = "✅" if purchased else "🛒"
        status_color = "#f0f2f6" if purchased else "white" # light gray or white background

        # 2. Create the URL link to self, passing the index to toggle
        toggle_url = st.query_params.to_dict()
        toggle_url['toggle'] = str(idx) # Index is now the key to toggle
        
        # 3. Use an <a> tag (link) wrapped around the content
        # We style the whole row using display: flex to keep it tight
        # The 'text-decoration: none' ensures the item name doesn't have a blue link underline
        item_html = f"""
        <div style='background-color: {status_color}; padding: 8px; margin-bottom: 5px; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>
            <a href='?toggle={idx}' style='display: flex; align-items: center; text-decoration: none; color: inherit;'>
                <span style='font-size: 20px; flex-shrink: 0; margin-right: 10px;'>{status_emoji}</span>
                <span style='font-size: 14px; color: #333; {"text-decoration: line-through; color: #888;" if purchased else ""};'>
                    {item_name}
                </span>
            </a>
        </div>
        """
        st.markdown(item_html, unsafe_allow_html=True)

# =====================================================
# TAB 2 — ADMIN PAGE
# =====================================================
elif selected_tab == "🔒 Admin":
    st.markdown("<h1>🔒 Admin Page</h1>", unsafe_allow_html=True)
    st.write("Enter admin name to access controls:")
    admin_name = st.text_input("Admin name")

    if admin_name.strip().lower() == "becky":
        st.success("Welcome, Becky! 👋")

        # Clear purchased items
        st.subheader("🗑 Clear Purchased Items")
        if st.button("Remove Purchased Items"):
            df_active = df[df['purchased'] == False]
            df_active.to_csv(DATA_FILE, index=False)
            st.success("Purchased items removed from the list.")
            st.rerun()

        # Reset signups
        st.subheader("🧹 Reset Entire List")
        if st.button("Clear ALL items"):
            DATA_FILE.write_text("")  # wipe file
            st.success("The entire shopping list has been cleared!")
            st.rerun()
    elif admin_name:
        st.error("Access denied.")
