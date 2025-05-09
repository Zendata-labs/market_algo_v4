"""
Utility functions for profile data manipulation.
"""
import pandas as pd

def create_ordered_profile_df(profile_df, profile_key, session_view_mode):
    """
    Create a profile dataframe in the natural order for the profile type.
    
    Args:
        profile_df: DataFrame with profile data
        profile_key: The profile type (month, day_of_week, etc.)
        session_view_mode: The view mode for session profiles (daily or combined)
        
    Returns:
        DataFrame sorted in the natural order for the profile type
    """
    if profile_df is None or profile_df.empty:
        return pd.DataFrame()
    
    order_map = {}
    
    # Create a copy to avoid modifying the original
    ordered_df = profile_df.copy()
    
    # Define natural order based on profile type
    if profile_key == "month":
        # Jan-Dec
        order_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }
        if "Label" in ordered_df.columns:
            ordered_df["Sort"] = ordered_df["Label"].map(order_map)
    elif profile_key == "week_of_year":
        # Week 1-52
        if "Label" in ordered_df.columns:
            ordered_df["Sort"] = ordered_df["Label"].str.extract(r'(\d+)').astype(int)
    elif profile_key == "week_of_month":
        # Week 1-5
        if "Label" in ordered_df.columns:
            ordered_df["Sort"] = ordered_df["Label"].str.extract(r'(\d+)').astype(int)
    elif profile_key == "day_of_week":
        # Mon-Fri
        order_map = {
            "Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7
        }
        if "Label" in ordered_df.columns:
            ordered_df["Sort"] = ordered_df["Label"].map(order_map)
    elif profile_key == "session":
        if session_view_mode == "daily":
            # For sessions, we need to handle the day + session combination
            if "DayLabel" in ordered_df.columns and "SessionLabel" in ordered_df.columns:
                day_order = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5}
                session_order = {"London": 1, "NY": 2, "Asian": 3}
                
                ordered_df["DaySort"] = ordered_df["DayLabel"].map(day_order)
                ordered_df["SessionSort"] = ordered_df["SessionLabel"].map(session_order)
                ordered_df["Sort"] = ordered_df["DaySort"] * 10 + ordered_df["SessionSort"]
        else:
            # For the combined view, just sort by session
            if "Session" in ordered_df.columns:
                session_order = {"London": 1, "NY": 2, "Asian": 3}
                ordered_df["Sort"] = ordered_df["Session"].map(session_order)
    elif profile_key == "quarter":
        # Q1-Q4
        if "Label" in ordered_df.columns:
            ordered_df["Sort"] = ordered_df["Label"].str.extract(r'(\d+)').astype(int)
    elif profile_key == "presidential":
        # Year 1-4
        if "Label" in ordered_df.columns:
            ordered_df["Sort"] = ordered_df["Label"].str.extract(r'(\d+)').astype(int)
    elif profile_key == "decennial":
        # Years 0-9
        if "Label" in ordered_df.columns:
            ordered_df["Sort"] = ordered_df["Label"].str.extract(r'(\d+)').astype(int)
    
    # Sort by the created sort column if it exists
    if "Sort" in ordered_df.columns:
        ordered_df = ordered_df.sort_values("Sort")
        ordered_df = ordered_df.drop("Sort", axis=1)
    
    return ordered_df
