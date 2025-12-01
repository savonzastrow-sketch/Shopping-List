import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo

# -----------------------
# CONFIG
# -----------------------
TIMEZONE = ZoneInfo("America/New_York")
DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "availability.csv"
EVENT_FILE = DATA_DIR / "event_date.txt"
EVENT_LOCATION_FILE = DATA_DIR / "event_location.txt"
DATA_DIR.mkdir(exist_ok=True)

# -----------------------
# Load or initialize event date & location
# -----------------------
if EVENT_FILE.exists():
    EVENT_DATE_STR = EVENT_FILE.read_text().strip()
else:
    EVENT_DATE_STR = "Friday, November 14, 2025"
    EVENT_FILE.write_text(EVENT_DATE_STR)

if EVENT_LOCATION_FILE.exists():
    EVENT_LOCATION = EVENT_LOCATION_FILE.read_text().strip()
else:
    EVENT_LOCATION = "TBD"
    EVENT_LOCATION_FILE.write_text(EVENT_LOCATION)

# -----------------------
# PAGE SETUP
# -----------------------
st.set_page_config(page_title="🀄 Mahjong Sign-up", layout="centered")

# -----------------------
# STYLES
# -----------------------
st.markdown("""
    <style>
    h1 { font-size: 32px !important; text-align: center; }
    h2 { font-size: 28px !important; text-align: center; }
    p, div, label, .stMarkdown { font-size: 18px !important; line-height: 1.6; }
    .stButton>button {
        border-radius: 12px;
        font-size: 16px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------
# Track active tab in session state
# -----------------------
tabs = ["📋 Sign-up", "🔒 Admin"]
selected_tab = st.session_state.get("selected_tab", tabs[0])
selected_tab = st.radio("Navigation", tabs, horizontal=True, label_visibility="collapsed")

# Detect tab switch
previous_tab = st.session_state.get("previous_tab", None)
if previous_tab != selected_tab:
    st.session_state["previous_tab"] = selected_tab
    # Refresh sign-up page when switching back
    if selected_tab == "📋 Sign-up":
        st.rerun()

st.session_state["selected_tab"] = selected_tab

# =====================================================
# TAB 1 — SIGN-UP PAGE
# =====================================================
if selected_tab == "📋 Sign-up":
    st.markdown(f"<h1>🀄 Mahjong - Sign-up</h1>", unsafe_allow_html=True)
    st.markdown(f"<p>Event date: <b>{EVENT_DATE_STR}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p>Event location: <b>{EVENT_LOCATION}</b></p>", unsafe_allow_html=True)

    # Load data
    if DATA_FILE.exists() and DATA_FILE.stat().st_size > 0:
        try:
            df = pd.read_csv(DATA_FILE)
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(columns=["timestamp", "name", "available"])
    else:
        df = pd.DataFrame(columns=["timestamp", "name", "available"])

    # Ensure proper dtypes
    if "available" in df.columns:
        df["available"] = df["available"].astype(bool)

    # Input field for adding a new player
    st.subheader("Add a Player")
    new_name = st.text_input("Enter your name")

    if st.button("Add Name"):
        new_name = new_name.strip()
        if not new_name:
            st.warning("Please enter a valid name.")
        elif new_name in df["name"].values:
            st.warning("That name is already on the list.")
        else:
            new_row = {"timestamp": datetime.now(), "name": new_name, "available": False}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"{new_name} added to the list.")
            st.rerun()

    # Display player list in a responsive, mobile-friendly layout
    if not df.empty:
        st.markdown("---")
        st.subheader("Player Availability")

        # Instruction text
        st.markdown(
            "<p style='font-size:16px; color:gray;'>Please click the button below to indicate if you are available.</p>",
            unsafe_allow_html=True
        )

        # Add CSS for layout and button styles
        st.markdown("""
            <style>
            .player-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #eee;
                padding: 8px 4px;
            }
            .player-name {
                font-weight: 600;
                font-size: 18px;
                flex: 1;
            }
            .toggle-btn {
                border: none;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 15px;
                font-weight: 600;
                cursor: pointer;
                transition: 0.2s;
                min-width: 140px;
                text-align: center;
            }
            .toggle-btn.green {
                background-color: #22c55e;
                color: white;
            }
            .toggle-btn.gray {
                background-color: #d3d3d3;
                color: #333;
            }
            @media (max-width: 480px) {
                .player-row {
                    flex-direction: row;
                    gap: 6px;
                    padding: 10px 2px;
                }
                .player-name {
                    font-size: 16px;
                }
                .toggle-btn {
                    font-size: 14px;
                    min-width: 120px;
                    padding: 5px 8px;
                }
            }
            </style>
        """, unsafe_allow_html=True)

        # Build each row
        for idx, row in df.iterrows():
            name = row["name"]
            available = row["available"]

            col1, col2 = st.columns([2, 2])
            with col1:
                st.markdown(f"<div class='player-name'>{name}</div>", unsafe_allow_html=True)
            with col2:
                if available:
                    if st.button("😄 Available", key=f"toggle_{idx}", help="Click to mark unavailable"):
                        df.loc[idx, "available"] = False
                        df.to_csv(DATA_FILE, index=False)
                        st.rerun()
                else:
                    if st.button("🙁 Not Available", key=f"toggle_{idx}", help="Click to mark available"):
                        df.loc[idx, "available"] = True
                        df.to_csv(DATA_FILE, index=False)
                        st.rerun()

# =====================================================
# TAB 2 — ADMIN PAGE
# =====================================================
elif selected_tab == "🔒 Admin":
    st.markdown("<h1>🔒 Admin Page</h1>", unsafe_allow_html=True)
    st.write("Enter admin name to access controls:")
    
    admin_name = st.text_input("Admin name")
    if admin_name.strip().lower() == "becky":
        st.success("Welcome, Becky! 👋")

        # Change event date
        st.subheader("🗓 Change Event Date")
        new_date = st.date_input("Select new date", value=date.today())
        if st.button("Save New Date"):
            pretty_date = new_date.strftime("%A, %B %d, %Y")
            EVENT_FILE.write_text(pretty_date)
            st.success(f"Event date updated to {pretty_date}")

        # Change event location
        st.subheader("📍 Change Event Location")
        new_location = st.text_input("Enter new event location", value=EVENT_LOCATION)
        if st.button("Save New Location"):
            EVENT_LOCATION_FILE.write_text(new_location.strip())
            st.success(f"Event location updated to {new_location}")
        
      # Reset signups
        st.subheader("🧹 Reset Sign-ups")
        if st.button("Clear all sign-ups"):
            DATA_FILE.write_text("")  # wipe file
            st.success("All sign-ups cleared!")

    elif admin_name:
        st.error("Access denied.")
