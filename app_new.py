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
from gold.data.loader import load_profile_data, fetch_data
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

    # Chart type selection for all profiles
    chart_type = "bar"  # Default to bar chart
    view_type = "standard"
    
    # Show chart type options for all profiles
    st.sidebar.markdown("---")
    
    # Add view mode selector for normal vs composite averages
    view_mode = st.sidebar.radio(
        "View Mode",
        ["Standard", "Composite Averages"],
        horizontal=True
    )
    
    # Chart type selector
    chart_type = st.sidebar.radio(
        "Chart Type",
        ["Bar Chart", "Line Chart"],
        horizontal=True
    )
    
    # Add composite average checkboxes when composite view is selected
    composite_averages = {}
    if view_mode == "Composite Averages":
        st.sidebar.markdown("### Select Averages")
        # Create a horizontal layout for checkboxes
        cols = st.sidebar.columns(5)
        
        # Define the numerical names for each timeframe based on profile type
        timeframe_labels = {}
        
        if profile_key == "decennial":
            timeframe_labels = {
                "min_cycle": "10Y",
                "short_term": "20Y",
                "mid_term": "30Y", 
                "long_term": "50Y",
                "multi_year": "100Y+"
            }
        elif profile_key == "presidential":
            timeframe_labels = {
                "min_cycle": "4Y",
                "short_term": "8Y",
                "mid_term": "12Y", 
                "long_term": "20Y",
                "multi_year": "40Y+"
            }
        elif profile_key == "quarter":
            timeframe_labels = {
                "min_cycle": "1Y",
                "short_term": "3Y",
                "mid_term": "5Y", 
                "long_term": "10Y",
                "multi_year": "20Y+"
            }
        elif profile_key == "month":
            timeframe_labels = {
                "min_cycle": "1Y",
                "short_term": "3Y",
                "mid_term": "5Y", 
                "long_term": "10Y",
                "multi_year": "15Y+"
            }
        elif profile_key == "week_of_year":
            timeframe_labels = {
                "min_cycle": "1Y",
                "short_term": "3Y",
                "mid_term": "5Y", 
                "long_term": "10Y",
                "multi_year": "20Y+"
            }
        elif profile_key == "week_of_month":
            timeframe_labels = {
                "min_cycle": "1M",
                "short_term": "3M",
                "mid_term": "6M", 
                "long_term": "12M",
                "multi_year": "36M+"
            }
        elif profile_key == "day_of_week":
            timeframe_labels = {
                "min_cycle": "1W",
                "short_term": "4W",
                "mid_term": "13W", 
                "long_term": "52W",
                "multi_year": "156W+"
            }
        elif profile_key == "session":
            timeframe_labels = {
                "min_cycle": "1D",
                "short_term": "5D",
                "mid_term": "20D", 
                "long_term": "60D",
                "multi_year": "250D+"
            }
        
        # Define the averages with their colors
        averages_config = [
            {"key": "min_cycle", "color": "#1E88E5"},  # blue
            {"key": "short_term", "color": "#FFA726"},  # orange
            {"key": "mid_term", "color": "#AB47BC"},  # violet
            {"key": "long_term", "color": "#43A047"},  # green
            {"key": "multi_year", "color": "#EF5350"}   # red
        ]
        
        # Create a checkbox for each average in the corresponding column
        for i, avg in enumerate(averages_config):
            # Get the numerical label for this timeframe
            numerical_label = timeframe_labels.get(avg["key"], avg["key"])
            # Get the original descriptive name as well
            original_name = {
                "min_cycle": "Min Cycle", 
                "short_term": "Short-term Avg", 
                "mid_term": "Mid-term Avg", 
                "long_term": "Long-term Avg",
                "multi_year": "Multi-year Avg"
            }.get(avg["key"], avg["key"])
            
            with cols[i]:
                composite_averages[avg["key"]] = {
                    "selected": st.checkbox(numerical_label, value=True),
                    "color": avg["color"],
                    "name": original_name,  # Keep original name for tooltips/legends
                    "numerical_label": numerical_label  # Add the numerical label
                }
    chart_type = "bar" if chart_type == "Bar Chart" else "line"
    is_composite = view_mode == "Composite Averages"
    
    # Special handling for day_of_week profile
    if profile_key == "day_of_week":
        # Daily profile specific options
        st.sidebar.markdown("### View Options")
        view_options = ["Standard View", "Hour Volatility Clock"]
        view_selection = st.sidebar.selectbox("Display Type", view_options, index=0)
        view_type = "volatility_clock" if view_selection == "Hour Volatility Clock" else "standard"
    
    # Initialize year_controls as an empty dict for all profiles
    year_controls = {}

    # Metrics selection with different options based on chart type and view mode
    metric = "Average Return"
    
    # For line charts, only show Average Return and ATR options
    if chart_type == "line":
        # Line charts never show Probability regardless of view mode
        metric = st.sidebar.radio("Metric", 
                    ["Average Return", "ATR points"], 0)
    else:  # Bar chart mode
        # For bar charts, show all three metrics including Probability
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
        "profile_key": profile_key,
        "metric": metric,
        "chart_type": chart_type,
        "view_type": view_type,
        "session_view_mode": session_view_mode,
        "session_filter": session_filter,
        "year_controls": year_controls,
        "is_composite": is_composite,
        "composite_averages": composite_averages
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
    view_type=controls['view_type'],
    is_composite=controls['is_composite'],
    composite_averages=controls['composite_averages']
)
render_candle_charts_tab(tab3, load_csv)

# Display footer information
st.sidebar.markdown("---")
st.sidebar.caption("© Gold Market Analysis 2025")
