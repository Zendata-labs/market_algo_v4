"""
Decennial cycle profile UI components.
"""
import streamlit as st
import datetime as dt
import pandas as pd
from . import config

def decennial_date_ui(preset_options, default_preset_index, min_days):
    """
    Specialized UI for decennial profile (10-year periods).
    """
    # Add a custom option to the presets
    all_options = preset_options + ["Custom Range"]
    
    # Show decade presets as a dropdown
    preset = st.sidebar.selectbox("10-Year Periods", all_options, default_preset_index)
    
    # Default values
    if preset == "Custom Range":
        # Custom range selected, use reasonable defaults
        s_def = dt.date(config.complete_year - 10, 1, 1)
        e_def = dt.date(config.complete_year, 12, 31)
    else:
        # Get date range from the selected preset
        s_def, e_def = config.PROFILE_PRESETS["decennial"][preset]
    
    # Show simplified date selection UI for decennial with step=10 years
    custom_range = st.sidebar.checkbox("Custom Date Range", value=(preset == "Custom Range"))
    
    if custom_range:
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            # Ensure start_year is within valid range
            start_year_default = min(s_def.year, config.complete_year-10)
            start_year = st.number_input("Start Year", min_value=1974, 
                                        max_value=config.complete_year-1, 
                                        value=start_year_default, step=10)
        with col2:
            # Make sure end_year doesn't exceed complete_year
            end_year = st.number_input("End Year", min_value=start_year+1, 
                                    max_value=config.complete_year, 
                                    value=min(e_def.year, config.complete_year), step=10)
    
        # Create date objects from the selected years (full year ranges)
        start = pd.Timestamp(year=start_year, month=1, day=1).date()
        end = pd.Timestamp(year=end_year, month=12, day=31).date()
        # Display the selected date range info
        st.sidebar.info(f"Selected period: {start_year} to {end_year} (full years)")
        
        # Validate date range for decennial when using custom range
        date_range_years = end_year - start_year
        if date_range_years < 10:
            st.sidebar.warning("⚠️ Date range is less than 10 years. Decennial analysis may not be meaningful.")
    else:
        # Use the preset dates
        start = s_def
        end = e_def
        # Display the selected preset info
        st.sidebar.info(f"Using preset: {preset}")
        
        # Validate date range for preset
        date_range_years = end.year - start.year
        if date_range_years < 10:
            st.sidebar.warning("⚠️ Date range is less than 10 years. Decennial analysis may not be meaningful.")
    
    # Display a note about what decennial cycle means
    with st.sidebar.expander("What is a decennial cycle?"):
        st.markdown("""
        The decennial cycle refers to patterns that repeat every decade (10 years). 
        In the decennial analysis, years are grouped by their last digit (year % 10):
        - Years ending in 0 (2020, 2010...)
        - Years ending in 1 (2021, 2011...)
        - And so on...
        
        A full decennial analysis requires at least one complete 10-year cycle, 
        preferably multiple cycles for pattern confirmation.
        """)
    
    # Add note about cutoff date
    st.sidebar.markdown(f"_Data available through {config.cutoff_date.strftime('%b %d, %Y')}_")
    
    return start, end
