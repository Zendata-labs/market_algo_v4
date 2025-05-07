"""
Day of week profile UI components.
"""
import streamlit as st
import datetime as dt
import pandas as pd
from . import config

def day_of_week_date_ui(preset_options, default_preset_index, min_days, key_prefix=""):
    """
    Specialized UI for day of week profile (5 trading days).
    
    Args:
        preset_options: List of preset options
        default_preset_index: Default selected index
        min_days: Minimum number of days required
        key_prefix: Prefix for widget keys to ensure uniqueness
    """
    # Add a custom option to the presets
    all_options = preset_options + ["Custom Range"]
    
    # Create unique widget keys using the prefix
    preset_key = f"{key_prefix}_dow_preset_selectbox"
    
    # Show week presets as a dropdown
    preset = st.sidebar.selectbox("Weekly Date Ranges", all_options, default_preset_index, key=preset_key)
    
    # Default values if custom
    if preset == "Custom Range":
        # Use a recent week as default (ending at cutoff date)
        s_def = config.cutoff_date - dt.timedelta(days=7)
        e_def = config.cutoff_date
    else:
        # Get date range from the selected preset
        s_def, e_def = config.PROFILE_PRESETS["day_of_week"][preset]
    
    # Create unique keys for the remaining widgets
    custom_range_key = f"{key_prefix}_dow_custom_range_checkbox"
    weeks_ago_key = f"{key_prefix}_dow_weeks_ago_slider"
    
    # Custom date range option with week selection
    custom_range = st.sidebar.checkbox("Select specific week", value=(preset == "Custom Range"), key=custom_range_key)
    
    if custom_range:
        # Show predefined weekly options for easier selection
        weeks_ago = st.sidebar.slider("Weeks before cutoff date", 0, 52, 1, key=weeks_ago_key)
        
        # Calculate week ending at cutoff
        end_of_week = config.cutoff_date - dt.timedelta(days=weeks_ago*7)
        start_of_week = end_of_week - dt.timedelta(days=6)  # Show Monday-Sunday format
        
        # Display selected week with explicit dates
        selected_week = f"{start_of_week.strftime('%b %d')} to {end_of_week.strftime('%b %d, %Y')}"
        st.sidebar.markdown(f"**Selected week:** {selected_week}")
        
        # Create unique keys for manual override widgets
        manual_override_key = f"{key_prefix}_dow_manual_override_checkbox"
        start_date_key = f"{key_prefix}_dow_start_date_input"
        end_date_key = f"{key_prefix}_dow_end_date_input"
        
        # Allow manual date override if needed
        manual_override = st.sidebar.checkbox("Manual date override", key=manual_override_key)
        if manual_override:
            start = st.sidebar.date_input("Start Date", start_of_week, format="MM/DD/YYYY", 
                                        max_value=config.cutoff_date, key=start_date_key)
            min_end_date = start + dt.timedelta(days=6)  # Ensure at least one week
            end = st.sidebar.date_input("End Date", 
                                      min(config.cutoff_date, min_end_date + dt.timedelta(days=1)), 
                                      min_value=min_end_date,
                                      max_value=config.cutoff_date,
                                      format="MM/DD/YYYY", key=end_date_key)
        else:
            start, end = start_of_week, end_of_week
    else:
        start, end = s_def, e_def
    
    # Display the selected date range info with specific dates
    days_diff = (end - start).days
    whole_weeks = days_diff // 7
    extra_days = days_diff % 7
    
    # Format the info message based on whether it's exactly 1 week or multiple weeks
    if whole_weeks == 1 and extra_days == 0:
        period_text = f"{start.strftime('%A, %b %d')} to {end.strftime('%A, %b %d, %Y')} (1 week)"
    elif whole_weeks >= 1 and extra_days == 0:
        period_text = f"{start.strftime('%b %d, %Y')} to {end.strftime('%b %d, %Y')} ({whole_weeks} weeks)"
    else:
        period_text = f"{start.strftime('%b %d, %Y')} to {end.strftime('%b %d, %Y')} ({whole_weeks} weeks, {extra_days} days)"
    
    st.sidebar.info(f"Analysis period: {period_text}")
    
    # Validate date range
    if days_diff < 7:
        st.sidebar.warning("⚠️ Date range must include at least one full week (7 days).")
    
    # Add note about cutoff date
    st.sidebar.markdown(f"_Data available through {config.cutoff_date.strftime('%b %d, %Y')}_")
    
    return start, end
