"""
Gold Cyclical Profiles Application
A streamlit web application for gold market analysis.

This is the main entry point for the application, which has been modularized
for better maintainability and organization.
"""
import streamlit as st
import pandas as pd
import pathlib
import sys
import datetime as dt

# Add project root to path for imports
sys.path.append(str(pathlib.Path(__file__).parent))

# Core imports
from gold import config
from gold.azure import load_csv
from gold.profiles import BUILDERS
from gold.date_ui import get_date_range_for_profile
from gold.data import load_profile_data, fetch_data
from gold.tabs import (
    render_current_market_tab,
    render_cyclical_profiles_tab, 
    render_candle_charts_tab
)

# Configure the Streamlit page
st.set_page_config(page_title="Gold Profiles", layout="wide")
st.title("🥇 Gold Cyclical Profiles")

# Create the top-level tabs
tab1, tab2, tab3 = st.tabs([
    "Current Market Position", 
    "Cyclical Profiles", 
    "Candle Charts"
])

# --- Sidebar controls ----------------------------------------------------
def render_sidebar_controls():
    """Render the main sidebar controls"""
    # Profile selection dropdown with display names
    profile_options = list(config.PROFILE_DISPLAY_NAMES.keys())
    profile_display_names = [config.PROFILE_DISPLAY_NAMES[k] for k in profile_options]
    default_index = 3  # Default to 'month' profile

    profile_display = st.sidebar.selectbox("Profile", profile_display_names, default_index)
    profile_key = profile_options[profile_display_names.index(profile_display)]

    # Chart type selection for monthly and daily profiles
    chart_type = "bar"
    view_type = "standard"
    
    if profile_key in ["month", "day_of_week"]:
        st.sidebar.markdown("---")
        chart_type = st.sidebar.radio(
            "Chart Type",
            ["Bar Chart", "Line Chart"],
            horizontal=True
        )
        chart_type = "bar" if chart_type == "Bar Chart" else "line"
        
        # Year ranges for line chart in monthly profile
        if profile_key == "month" and chart_type == "line":
            st.sidebar.markdown("### Line Chart Options")
            
            # Return calculation method
            st.sidebar.markdown("**Return Calculation:**")
            return_method = st.sidebar.radio(
                "Return Method",  # Added a proper label
                ["Open to Close (Intraday)", "Close to Close (Daily)"],
                horizontal=True,
                label_visibility="collapsed"  # Hide the label but maintain accessibility
            )
            return_method_key = "open-close" if return_method == "Open to Close (Intraday)" else "close-close"
            
            # Year ranges to show
            st.sidebar.markdown("**Show Year Ranges:**")
            show_ytd = st.sidebar.checkbox("Year-to-Date", value=False)
            show_5yr = st.sidebar.checkbox("5-Year Average", value=True)
            show_10yr = st.sidebar.checkbox("10-Year Average", value=True)
            show_15yr = st.sidebar.checkbox("15-Year Average", value=True)
            
            # Store year selections in control dict
            year_controls = {
                'show_ytd': show_ytd,
                'show_5yr': show_5yr,
                'show_10yr': show_10yr,
                'show_15yr': show_15yr,
                'return_method_key': return_method_key
            }
        # Daily profile specific options    
        elif profile_key == "day_of_week":
            st.sidebar.markdown("### View Options")
            view_options = ["Standard View", "Hour Volatility Clock"]
            view_selection = st.sidebar.selectbox("Display Type", view_options, index=0)
            view_type = "volatility_clock" if view_selection == "Hour Volatility Clock" else "standard"
            
            year_controls = {}
        else:
            year_controls = {}
    else:
        year_controls = {}

    # Metrics selection (only show for bar charts)
    metric = "Average Return"
    if chart_type == "bar":
        metric = st.sidebar.radio("Metric", 
                    ["Average Return", "ATR points", "Probability"], 0)

    # Session profile specific options
    session_view_mode = "daily"
    session_filter = "All"

    if profile_key == "session":
        # Add session-specific controls
        session_view_options = ["5-Bar (Weekdays)", "1-Bar (Combined)"]
        session_view_selection = st.sidebar.selectbox("View Mode", session_view_options, 0)
        session_view_mode = "daily" if session_view_selection == session_view_options[0] else "combined"
        
        # For the 1-bar view, add filter for red/green days
        if session_view_mode == "combined":
            session_filter = st.sidebar.radio("Filter by Day Type", ["All", "Green Days", "Red Days"], 0)

    return {
        'profile_key': profile_key,
        'metric': metric,
        'session_view_mode': session_view_mode,
        'session_filter': session_filter,
        'chart_type': chart_type,
        'year_controls': year_controls,
        'view_type': view_type
    }

# Get sidebar controls
controls = render_sidebar_controls()

# We'll get the date range in the tab's render function to avoid duplicate UI
# No need to call get_date_range_for_profile here as it's called in cyclical_profiles.py

# Initialize profile_df as None
# The actual loading will happen in the cyclical_profiles.py with the correct date range
profile_df = None

# Render each tab with the appropriate data and controls
render_current_market_tab(tab1, fetch_data)
render_cyclical_profiles_tab(
    tab2, 
    profile_df, 
    controls['profile_key'], 
    controls['metric'], 
    controls['session_view_mode'], 
    controls['session_filter'],
    chart_type=controls['chart_type'],
    year_controls=controls['year_controls'],
    view_type=controls['view_type']
)
render_candle_charts_tab(tab3, load_csv)

# Display footer information
st.sidebar.markdown("---")
st.sidebar.caption("© Gold Market Analysis 2025")
