"""
Date selection UI components for different profile types.
This module provides specialized date selection interfaces for each profile type.
"""
import streamlit as st
import pandas as pd
import datetime as dt
from . import config

# Import the extracted UI components
from .day_of_week_ui import day_of_week_date_ui
from .decennial_ui import decennial_date_ui
from .presidential_ui import presidential_date_ui
from .quarter_ui import quarter_date_ui

def get_date_range_for_profile(profile_key):
    """
    Display profile-specific date range selectors and return the selected start and end dates.
    
    Args:
        profile_key: The key of the profile (decennial, presidential, etc.)
    
    Returns:
        tuple: (start_date, end_date) as datetime.date objects
    """
    # Use the appropriate preset options for this profile
    preset_options = list(config.PROFILE_PRESETS[profile_key].keys())
    default_preset = config.PROFILE_DEFAULT_PRESET[profile_key]
    default_preset_index = preset_options.index(default_preset) if default_preset in preset_options else 0
    
    # Get minimum required period in days for this profile
    min_days = config.PROFILE_MIN_PERIODS[profile_key]
    
    # Profile display name for better UI
    profile_display = config.PROFILE_DISPLAY_NAMES[profile_key]
    
    # Add header with profile name
    st.sidebar.markdown(f"### {profile_display} Date Range")
    
    if profile_key == "decennial":
        return decennial_date_ui(preset_options, default_preset_index, min_days)
    elif profile_key == "presidential":
        return presidential_date_ui(preset_options, default_preset_index, min_days)
    elif profile_key == "quarter":
        return quarter_date_ui(preset_options, default_preset_index, min_days)
    elif profile_key == "month":
        return _month_date_ui(preset_options, default_preset_index, min_days)
    elif profile_key == "week_of_year":
        return _week_of_year_date_ui(preset_options, default_preset_index, min_days)
    elif profile_key == "week_of_month":
        return _week_of_month_date_ui(preset_options, default_preset_index, min_days)
    elif profile_key == "day_of_week":
        return day_of_week_date_ui(preset_options, default_preset_index, min_days)
    else:  # session or fallback
        return _standard_date_ui(preset_options, default_preset_index, min_days)

def _month_date_ui(preset_options, default_preset_index, min_days):
    """
    Specialized UI for monthly profile (12 months of the year).
    """
    # Show month presets as a dropdown
    preset = st.sidebar.selectbox("Year Periods", preset_options, default_preset_index)
    
    # Get date range from the selected preset
    s_def, e_def = config.PROFILE_PRESETS["month"][preset]
    
    # Custom date range option
    custom_range = st.sidebar.checkbox("Custom year range")
    
    if custom_range:
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            start_year = st.number_input("Start Year", min_value=1974, 
                                        max_value=config.current_year, 
                                        value=s_def.year)
        with col2:
            end_year = st.number_input("End Year", min_value=start_year, 
                                     max_value=config.current_year, 
                                     value=min(start_year+5, config.current_year))
        
        # Create date objects (full years)
        start = pd.Timestamp(year=start_year, month=1, day=1).date()
        end = pd.Timestamp(year=end_year, month=12, day=31).date()
    else:
        start, end = s_def, e_def
    
    # Display the selected date range info
    date_range_years = (end.year - start.year) + ((end.month - start.month) / 12)
    st.sidebar.info(f"Selected period: {start.strftime('%b %Y')} to {end.strftime('%b %Y')} " +
                   f"({date_range_years:.1f} years)")
    
    # Validate date range
    if date_range_years < 1:
        st.sidebar.warning("⚠️ Date range is less than 1 year. Monthly analysis requires at least a full year.")
    
    return start, end

def _week_of_year_date_ui(preset_options, default_preset_index, min_days):
    """
    Specialized UI for week of year profile (52 weeks).
    """
    # Show week presets as a dropdown
    preset = st.sidebar.selectbox("Year Periods", preset_options, default_preset_index)
    
    # Get date range from the selected preset
    s_def, e_def = config.PROFILE_PRESETS["week_of_year"][preset]
    
    # Custom date range option
    custom_range = st.sidebar.checkbox("Custom year range")
    
    if custom_range:
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            start_year = st.number_input("Start Year", min_value=1974, 
                                        max_value=config.current_year, 
                                        value=s_def.year)
        with col2:
            end_year = st.number_input("End Year", min_value=start_year, 
                                     max_value=config.current_year, 
                                     value=min(start_year+2, config.current_year))
        
        # Create date objects (full years)
        start = pd.Timestamp(year=start_year, month=1, day=1).date()
        end = pd.Timestamp(year=end_year, month=12, day=31).date()
    else:
        start, end = s_def, e_def
    
    # Display the selected date range info
    date_range_years = (end.year - start.year) + ((end.month - start.month) / 12)
    st.sidebar.info(f"Selected period: {start.strftime('%b %Y')} to {end.strftime('%b %Y')} " +
                   f"({date_range_years:.1f} years)")
    
    # Validate date range
    if date_range_years < 1:
        st.sidebar.warning("⚠️ Date range is less than 1 year. Week of year analysis requires at least a full year.")
    
    return start, end

def _week_of_month_date_ui(preset_options, default_preset_index, min_days):
    """
    Specialized UI for week of month profile (4-5 weeks).
    """
    # Show month presets as a dropdown
    preset = st.sidebar.selectbox("Month Periods", preset_options, default_preset_index)
    
    # Get date range from the selected preset
    s_def, e_def = config.PROFILE_PRESETS["week_of_month"][preset]
    
    # Custom date range option with month selection
    custom_range = st.sidebar.checkbox("Custom month range")
    
    if custom_range:
        col1, col2 = st.sidebar.columns(2)
        
        # Month selection
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        with col1:
            start_year = st.selectbox("Start Year", 
                                    range(1974, config.current_year+1), 
                                    index=config.current_year-1974)
            start_month = st.selectbox("Start Month", range(1, 13), 
                                     index=0, 
                                     format_func=lambda x: months[x-1])
        
        with col2:
            end_year = st.selectbox("End Year", 
                                  range(start_year, config.current_year+1), 
                                  index=0)
            
            if end_year == start_year:
                end_month = st.selectbox("End Month", range(start_month, 13), 
                                       index=0, 
                                       format_func=lambda x: months[x-1])
            else:
                end_month = st.selectbox("End Month", range(1, 13), 
                                       index=11, 
                                       format_func=lambda x: months[x-1])
        
        # Create date objects (full months)
        start = pd.Timestamp(year=start_year, month=start_month, day=1).date()
        
        # Last day of end month
        next_month = end_month + 1 if end_month < 12 else 1
        next_year = end_year if end_month < 12 else end_year + 1
        end = (pd.Timestamp(year=next_year, month=next_month, day=1) - 
              pd.Timedelta(days=1)).date()
    else:
        start, end = s_def, e_def
    
    # Display the selected date range info
    months_diff = (end.year - start.year) * 12 + (end.month - start.month) + 1
    st.sidebar.info(f"Selected period: {start.strftime('%b %Y')} to {end.strftime('%b %Y')} " +
                   f"({months_diff} months)")
    
    # Validate date range
    if months_diff < 1:
        st.sidebar.warning("⚠️ Date range must include at least one full month.")
    
    return start, end

# Day of week UI has been moved to day_of_week_ui.py

def _standard_date_ui(preset_options, default_preset_index, min_days):
    """
    Standard date UI for profiles that don't require special treatment.
    """
    # Show standard presets
    preset = st.sidebar.selectbox("Preset", preset_options, default_preset_index)
    
    # Get the preset dates
    s_def, e_def = config.STANDARD_PRESETS[preset]
    
    # Standard date pickers
    start = st.sidebar.date_input("Start", s_def, format="MM/DD/YYYY")
    end = st.sidebar.date_input("End", e_def, format="MM/DD/YYYY")
    
    # Validate date range
    if start > end:
        st.error("Start date after End date!")
        start, end = end, start
    
    # Check minimum period
    if (end - start).days < min_days:
        st.sidebar.warning(f"⚠️ Short date range may not provide meaningful results. " +
                          f"Consider using at least {min_days} days.")
    
    return start, end
