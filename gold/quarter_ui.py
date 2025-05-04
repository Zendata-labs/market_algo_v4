"""
Quarter profile UI components.
"""
import streamlit as st
import datetime as dt
import pandas as pd
from . import config

def quarter_date_ui(preset_options, default_preset_index, min_days):
    """
    Specialized UI for quarterly profile (3-month periods).
    """
    # Add a custom option to the presets
    all_options = preset_options + ["Custom Range"]
    
    # Show quarter presets as a dropdown
    preset = st.sidebar.selectbox("Quarter Periods", all_options, default_preset_index)
    
    # Default values
    if preset == "Custom Range":
        # Custom range selected, use reasonable defaults
        s_def = config.quarter_start(config.last_complete_year, 1)
        e_def = config.quarter_end(config.last_complete_year, 4)
    else:
        # Get date range from the selected preset
        s_def, e_def = config.PROFILE_PRESETS["quarter"][preset]
    
    # Find the most recent complete quarter details
    last_complete_q = config.last_complete_q
    last_complete_q_year = config.last_complete_q_year
    
    # Check if user wants custom date range
    custom_range = st.sidebar.checkbox("Custom Date Range", value=(preset == "Custom Range"))
    
    if custom_range:
        # Only show years up to the year with complete data
        valid_years = list(range(1974, config.last_complete_year + 1))
        default_year_index = valid_years.index(config.last_complete_year) if config.last_complete_year in valid_years else len(valid_years)-1
        
        # Year and quarter selection
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            year = st.selectbox("Year", valid_years, index=default_year_index)
        
        with col2:
            # Calculate which quarters are complete for the selected year
            if year < config.last_complete_year:
                # All quarters are complete for past years
                valid_quarters = [1, 2, 3, 4]
                quarter_labels = [f"Q{q}" for q in valid_quarters]
                default_q_index = 0
            else:  # This is the current year
                valid_quarters = list(range(1, last_complete_q + 1))
                quarter_labels = [f"Q{q}" for q in valid_quarters]
                default_q_index = len(valid_quarters) - 1  # Select most recent by default
            
            # If no complete quarters, fall back to previous year Q4
            if not valid_quarters:
                st.warning("No complete quarters available for the selected year")
                year = year - 1
                valid_quarters = [4]
                quarter_labels = ["Q4"]
                default_q_index = 0
            
            quarter_index = st.selectbox("Quarter", range(len(valid_quarters)), 
                                        index=default_q_index,
                                        format_func=lambda i: quarter_labels[i])
            quarter = valid_quarters[quarter_index]
        
        # Calculate start and end dates based on selected quarter
        start = config.quarter_start(year, quarter)
        end = config.quarter_end(year, quarter)
    else:
        # Use preset dates
        start = s_def
        end = e_def
    
    # Option to expand range (only if using custom range)
    if custom_range:
        expand_range = st.sidebar.checkbox("Include additional quarters")
        
        if expand_range:
            quarters_to_add = st.sidebar.slider("Additional quarters", 1, 20, 3)
            
            # Extend end date by adding quarters
            end_quarter = quarter
            end_year = year
            
            # Only allow expanding into complete quarters
            remaining_quarters = quarters_to_add
            while remaining_quarters > 0:
                end_quarter += 1
                if end_quarter > 4:
                    end_quarter = 1
                    end_year += 1
                
                # Check if this quarter is complete
                if (end_year < config.last_complete_year) or \
                   (end_year == config.last_complete_year and end_quarter <= config.last_complete_q):
                    remaining_quarters -= 1
                else:
                    # Stop at the last complete quarter
                    end_quarter = config.last_complete_q if end_year == config.last_complete_year else 4
                    end_year = config.last_complete_year
                    break
            
            end = config.quarter_end(end_year, end_quarter)
            
            # Display the selected date range info
            st.sidebar.info(f"Selected period: Q{quarter} {year} to Q{end_quarter} {end_year}")
        else:
            # Display single quarter info
            st.sidebar.info(f"Selected period: Q{quarter} {year} (3 months)")
        
        # Add note about complete data
        st.sidebar.markdown(f"_Using complete quarter data through Q{config.last_complete_q} {config.last_complete_q_year}_")
    else:
        # Display preset info
        st.sidebar.info(f"Using preset: {preset}")
    
    # Validate date range
    date_range_days = (end - start).days
    if date_range_days < min_days:
        st.sidebar.warning(f"⚠️ Date range is less than {min_days//30} months. Consider extending for better analysis.")
    
    return start, end
