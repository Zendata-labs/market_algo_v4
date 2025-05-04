"""
Presidential cycle profile UI components.
"""
import streamlit as st
import datetime as dt
import pandas as pd
from . import config

def presidential_date_ui(preset_options, default_preset_index, min_days):
    """
    Specialized UI for presidential cycle profile (4-year periods).
    """
    # Add a custom option to the presets
    all_options = preset_options + ["Custom Range"]
    
    # Show presidential cycle presets as a dropdown
    preset = st.sidebar.selectbox("Presidential Cycles", all_options, default_preset_index)
    
    # Default values
    if preset == "Custom Range":
        # Custom range selected, use reasonable defaults
        s_def = dt.date(config.last_election_year - 4, 1, 1)
        e_def = dt.date(config.complete_year, 12, 31)
    else:
        # Get date range from the selected preset
        s_def, e_def = config.PROFILE_PRESETS["presidential"][preset]
    
    # Calculate last valid election year cycle - use complete_year (not partial current year)
    last_election_year = config.complete_year
    while (last_election_year % 4) != 0 or last_election_year > config.complete_year:
        last_election_year -= 1
    
    # Get the list of presidential cycle years (going backward in steps of 4)
    # Use complete_year instead of current_year to avoid partial years
    valid_years = [year for year in range(1976, config.complete_year + 1, 4)]
    valid_years.append(1974)  # Add the initial data year
    valid_years.sort()  # Sort in ascending order
    
    # Check if user wants to use a custom date range
    custom_range = st.sidebar.checkbox("Custom Date Range", value=(preset == "Custom Range"))
    
    if custom_range:
        # Show simplified date selection UI with dropdowns for election years
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            # Find closest match to the default start year
            start_year_index = 0
            for i, year in enumerate(valid_years):
                if year <= s_def.year:
                    start_year_index = i
            
            start_year = st.selectbox("Start Election Year", 
                                     valid_years, 
                                     index=start_year_index)
    
        # Filter end years to be after start_year and no greater than complete_year
        valid_end_years = [y for y in valid_years if y > start_year and y <= config.complete_year]
        if not valid_end_years:  # If no valid end years, just use complete_year
            valid_end_years = [config.complete_year]
        
        with col2:
            # Find closest match to the default end year
            end_year_index = 0
            for i, year in enumerate(valid_end_years):
                if year <= e_def.year:
                    end_year_index = i
                    
            end_year = st.selectbox("End Election Year", 
                                   valid_end_years,
                                   index=min(end_year_index, len(valid_end_years)-1))
        
        # Create date objects (full year range)
        start = dt.date(start_year, 1, 1)
        end = dt.date(end_year, 12, 31)
        
        # Display the selected date range info
        st.sidebar.info(f"Selected period: {start_year} to {end_year} (complete election cycles)")
    else:
        # Use the preset dates
        start = s_def
        end = e_def
        # Display the selected preset info
        st.sidebar.info(f"Using preset: {preset}")
    
    # Validate date range
    if custom_range:
        date_range_years = end_year - start_year
        if date_range_years < 4:
            st.sidebar.warning("⚠️ Date range is less than 4 years. Presidential cycle analysis may not be meaningful.")
    else:
        date_range_years = (end.year - start.year) + ((end.month - start.month) / 12)
        if date_range_years < 4:
            st.sidebar.warning("⚠️ Date range is less than 4 years. Presidential cycle analysis may not be meaningful.")
    
    # Display a note about what presidential cycle means
    with st.sidebar.expander("What is a presidential cycle?"):
        st.markdown("""
        The presidential cycle refers to patterns in financial markets that correspond 
        to the 4-year U.S. presidential election cycle:
        - Year 1: Post-election year
        - Year 2: Midterm year
        - Year 3: Pre-election year
        - Year 4: Election year
        
        Each phase might show different market behaviors as government policy and 
        political considerations shift throughout the cycle.
        """)
    
    # Add note about cutoff date
    st.sidebar.markdown(f"_Data available through {config.cutoff_date.strftime('%b %d, %Y')}_")
    
    return start, end
