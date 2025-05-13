"""
Composite Average implementation for Gold Trading App.
This module handles the calculation of composite averages for different profile types.
"""
import pandas as pd
import numpy as np
import datetime as dt

# Define the composite average periods for each profile type
COMPOSITE_PERIODS = {
    "decennial": {
        "10 Years": 10,           # 10 years (Decade Cycle)
        "20 Years": 20,          # 20 years (2 cycles)
        "30 Years": 30,          # 30 years (3 cycles)
        "50 Years": 50,          # 50 years (5 cycles)
        "100 Years": 100         # 100+ years
    },
    "presidential": {
        "4 Years": 4,            # 4 years (1 full presidential cycle)
        "8 Years": 8,            # 8 years (2 cycles)
        "12 Years": 12,          # 12 years (3 cycles)
        "20 Years": 20,          # 20 years (5 cycles)
        "40 Years": 40           # 40+ years
    },
    "quarter": {
        "1 Year": 1,             # 1 year (4 quarters)
        "3 Years": 3,            # 3 years (12 quarters)
        "5 Years": 5,            # 5 years (20 quarters)
        "10 Years": 10,          # 10 years (40 quarters)
        "20 Years": 20           # 20+ years
    },
    "month": {
        "1 Year": 1,             # 1 year (12 months)
        "3 Years": 3,            # 3 years (36 months)
        "5 Years": 5,            # 5 years (60 months)
        "10 Years": 10,          # 10 years (120 months)
        "15 Years": 15           # 15+ years (180+ months)
    },
    "week_of_year": {
        "1 Year": 1,             # 1 year (52 weeks)
        "3 Years": 3,            # 3 years (156 weeks)
        "5 Years": 5,            # 5 years (260 weeks)
        "10 Years": 10,          # 10 years (520 weeks)
        "20 Years": 20           # 20+ years (1040+ weeks)
    },
    "week_of_month": {
        "1 Month": 1,            # 1 month (4-5 weeks)
        "3 Months": 3,           # 1 quarter (3 months)
        "6 Months": 6,           # Half year (6 months)
        "12 Months": 12,         # 1 year (12 months)
        "36 Months": 36          # 3 years (36 months)
    },
    "day_of_week": {
        "1 Week": 1,             # 1 week (7 days)
        "4 Weeks": 4,            # 1 month (4 weeks)
        "12 Weeks": 12,          # 1 quarter (12 weeks)
        "52 Weeks": 52,          # 1 year (52 weeks)
        "156 Weeks": 156         # 3 years (156 weeks)
    },
    "session": {
        "1 Week": 1,             # 1 week (5 trading days)
        "4 Weeks": 4,            # 1 month (4 weeks)
        "12 Weeks": 12,          # 1 quarter (12 weeks)
        "52 Weeks": 52,          # 1 year (52 weeks)
        "156 Weeks": 156         # 3 years (156 weeks)
    }
}

def get_composite_periods(profile_key):
    """Get the available composite average periods for a profile type"""
    if profile_key in COMPOSITE_PERIODS:
        return COMPOSITE_PERIODS[profile_key]
    # Default to monthly profile periods if profile_key not found
    return COMPOSITE_PERIODS["month"]

def calculate_composite_average(df, profile_key, composite_type, label_column, metric_columns):
    """
    Calculate the composite average for a specific profile and timeframe.
    
    Args:
        df: DataFrame with historical data
        profile_key: The profile type (month, day_of_week, etc.)
        composite_type: The composite average type (Min Cycle, Short-term Avg, etc.)
        label_column: The column name for the cycle point (Month, DayOfWeek, etc.)
        metric_columns: List of columns to calculate averages for (AvgReturn, AvgRange, etc.)
        
    Returns:
        DataFrame with the composite averages
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Get the periods for this profile type
    periods = get_composite_periods(profile_key)
    
    # If asking for current cycle (Min Cycle) or invalid type, return the original data
    if composite_type not in periods or composite_type == "Min Cycle":
        return df
    
    # Get the number of periods to average
    n_periods = periods[composite_type]
    
    # Make a copy to avoid modifying the original
    result_df = df.copy()
    
    # Group by the label column and calculate averages
    grouped = df.groupby(label_column)
    
    # Calculate for each metric column
    for col in metric_columns:
        if col in df.columns:
            # Get the average for this metric
            result_df[col] = grouped[col].transform(lambda x: x.tail(n_periods).mean())
    
    # Return the result with one row per unique label
    return result_df.drop_duplicates(label_column)

def get_composite_description(profile_key, composite_type):
    """
    Get a description of what the composite average represents.
    
    Args:
        profile_key: The profile type (month, day_of_week, etc.)
        composite_type: The composite average type (now using numerical format like "1 Year", "3 Years", etc.)
        
    Returns:
        String description of the composite average with additional context
    """
    periods = get_composite_periods(profile_key)
    
    if composite_type not in periods:
        return "Current data (no averaging)"
    
    # Get the number of periods
    n_periods = periods[composite_type]
    
    # The composite_type itself now contains the primary period info (e.g., "10 Years")
    # But we'll add additional context for clarity
    
    # Create description based on profile type to provide additional context
    if profile_key == "decennial":
        cycles = n_periods // 10
        return f"{composite_type} ({cycles} decade cycles)"
    elif profile_key == "presidential":
        cycles = n_periods // 4
        return f"{composite_type} ({cycles} presidential cycles)"
    elif profile_key == "quarter":
        quarters = n_periods * 4
        return f"{composite_type} ({quarters} quarters)"
    elif profile_key == "month":
        months = n_periods * 12
        return f"{composite_type} ({months} months)"
    elif profile_key == "week_of_year":
        weeks = n_periods * 52
        return f"{composite_type} ({weeks} weeks)"
    elif profile_key == "week_of_month":
        # For week_of_month, the periods are already in months
        if "Month" in composite_type:
            return composite_type  # Already clear enough
        else:
            # This would be a case like "3 Years" which is clear enough
            return composite_type
    elif profile_key == "day_of_week":
        # For day_of_week, the periods are already in weeks
        if "Week" in composite_type:
            return composite_type  # Already clear enough
        else:
            # This would be a case like "1 Year" which is 52 weeks
            return composite_type
    elif profile_key == "session":
        # For session, the periods are already in weeks
        if "Week" in composite_type:
            trading_days = n_periods * 5
            return f"{composite_type} ({trading_days} trading days)"
        else:
            return composite_type
    else:
        return composite_type  # Default to just showing the composite type itself
