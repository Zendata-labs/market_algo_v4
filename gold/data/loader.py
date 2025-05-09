"""
Data loading and preparation utilities.
This module centralizes data loading functions used across the application.
"""
import pandas as pd
import streamlit as st
from gold.azure import load_csv
from gold import config

@st.cache_data(show_spinner=False)
def load_chart_data(file_key):
    """
    Load chart data with caching for better performance.
    
    Args:
        file_key: The key for the data file to load
        
    Returns:
        DataFrame with chart data
    """
    df = load_csv(file_key)
    return df

@st.cache_data(show_spinner=False)
def load_profile_data(profile_key, start_date, end_date, view_mode="daily", filter_type="All"):
    """
    Load and prepare data for a specific profile.
    
    Args:
        profile_key: The key of the profile (month, day_of_week, etc.)
        start_date: Start date for filtering
        end_date: End date for filtering
        view_mode: View mode for session profile ("daily" or "combined")
        filter_type: Filter type for session profile ("All", "Green Days", "Red Days")
        
    Returns:
        DataFrame with profile data
    """
    from gold.profiles import BUILDERS
    
    # Get the appropriate data file for this profile
    blob_key = config.PROFILE_SOURCE[profile_key]
    blob = config.TIMEFRAME_FILES[blob_key]
    
    # Load raw data
    raw = fetch_data(blob)
    build = BUILDERS[profile_key]
    
    # Special handling for session profile
    if profile_key == "session":
        # Call build with view mode parameter
        df = build(raw, pd.Timestamp(start_date), pd.Timestamp(end_date), view=view_mode)
        
        # Apply filter for combined view if needed
        if view_mode == "combined" and filter_type != "All":
            if filter_type == "Green Days":
                # Filter to only include data from days with positive returns
                green_days = raw[raw["Close"] > raw["Open"]].copy()
                if not green_days.empty:
                    df = build(green_days, pd.Timestamp(start_date), pd.Timestamp(end_date), view=view_mode)
            elif filter_type == "Red Days":
                # Filter to only include data from days with negative returns
                red_days = raw[raw["Close"] < raw["Open"]].copy()
                if not red_days.empty:
                    df = build(red_days, pd.Timestamp(start_date), pd.Timestamp(end_date), view=view_mode)
    else:
        # Standard build for other profiles
        df = build(raw, pd.Timestamp(start_date), pd.Timestamp(end_date))
    
    return df

@st.cache_data(show_spinner=False)
def fetch_data(blob_key):
    """
    Fetch and preprocess raw OHLC data.
    
    Args:
        blob_key: The key for the data file to load
        
    Returns:
        DataFrame with preprocessed data
    """
    df = load_csv(blob_key)[["Date","Open","High","Low","Close"]].copy()
    # strip thousands separator before numeric cast
    for col in ["Open","High","Low","Close"]:
        df[col] = df[col].astype(str).str.replace(",", "").astype(float)
    
    # First try to parse date with common formats to avoid warning
    try:
        # Try M/D/YYYY format (e.g., 3/19/2025)
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="raise")
    except ValueError:
        try:
            # Try YYYY-MM-DD format
            df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="raise")
        except ValueError:
            # As a fallback, let pandas infer the format
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    return df.dropna()
