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
        "Min Cycle": 10,           # 10 years (Decade Cycle)
        "Short-term Avg": 20,      # 20 years (2 cycles)
        "Mid-term Avg": 30,        # 30 years (3 cycles)
        "Long-term Avg": 50,       # 50 years (5 cycles)
        "Multi-year Avg": 100      # 100+ years
    },
    "presidential": {
        "Min Cycle": 4,            # 4 years (1 full presidential cycle)
        "Short-term Avg": 8,       # 8 years (2 cycles)
        "Mid-term Avg": 12,        # 12 years (3 cycles)
        "Long-term Avg": 20,       # 20 years (5 cycles)
        "Multi-year Avg": 40       # 40+ years
    },
    "quarter": {
        "Min Cycle": 1,            # 1 year (4 quarters)
        "Short-term Avg": 3,       # 3 years (12 quarters)
        "Mid-term Avg": 5,         # 5 years (20 quarters)
        "Long-term Avg": 10,       # 10 years (40 quarters)
        "Multi-year Avg": 20       # 20+ years
    },
    "month": {
        "Min Cycle": 1,            # 1 year
        "Short-term Avg": 3,       # 3 years
        "Mid-term Avg": 5,         # 5 years
        "Long-term Avg": 10,       # 10 years
        "Multi-year Avg": 15       # 15+ years
    },
    "week_of_year": {
        "Min Cycle": 1,            # 1 year (52 weeks)
        "Short-term Avg": 3,       # 3 years (156 weeks)
        "Mid-term Avg": 5,         # 5 years (260 weeks)
        "Long-term Avg": 10,       # 10 years (520 weeks)
        "Multi-year Avg": 20       # 20+ years
    },
    "week_of_month": {
        "Min Cycle": 1,            # 1 month
        "Short-term Avg": 3,       # 1 quarter (3m)
        "Mid-term Avg": 6,         # 6 months
        "Long-term Avg": 12,       # 1 year (12m)
        "Multi-year Avg": 36       # 3-5 years
    },
    "day_of_week": {
        "Min Cycle": 1,            # 1 week
        "Short-term Avg": 4,       # 1 month (4w)
        "Mid-term Avg": 13,        # 1 quarter (13w)
        "Long-term Avg": 52,       # 1 year (52w)
        "Multi-year Avg": 156      # 3+ years
    },
    "session": {
        "Min Cycle": 1,            # 1 day
        "Short-term Avg": 5,       # 1 week (5d)
        "Mid-term Avg": 20,        # 1 month (20d)
        "Long-term Avg": 60,       # 3 months (60d)
        "Multi-year Avg": 250      # 1 year (250d)
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
        composite_type: The composite average type (Min Cycle, Short-term Avg, etc.)
        
    Returns:
        String description of the composite average
    """
    periods = get_composite_periods(profile_key)
    
    if composite_type not in periods:
        return "Current data (no averaging)"
    
    # Get the number of periods
    n_periods = periods[composite_type]
    
    # Create description based on profile type
    if profile_key == "decennial":
        return f"{composite_type}: {n_periods} years"
    elif profile_key == "presidential":
        cycles = n_periods // 4
        return f"{composite_type}: {n_periods} years ({cycles} presidential cycles)"
    elif profile_key == "quarter":
        years = n_periods
        return f"{composite_type}: {n_periods} years ({years * 4} quarters)"
    elif profile_key == "month":
        return f"{composite_type}: {n_periods} years ({n_periods * 12} months)"
    elif profile_key == "week_of_year":
        return f"{composite_type}: {n_periods} years ({n_periods * 52} weeks)"
    elif profile_key == "week_of_month":
        if n_periods < 12:
            return f"{composite_type}: {n_periods} months"
        else:
            years = n_periods // 12
            months = n_periods % 12
            if months == 0:
                return f"{composite_type}: {years} years"
            else:
                return f"{composite_type}: {years} years and {months} months"
    elif profile_key == "day_of_week":
        if n_periods < 52:
            return f"{composite_type}: {n_periods} weeks"
        else:
            years = n_periods // 52
            weeks = n_periods % 52
            if weeks == 0:
                return f"{composite_type}: {years} years"
            else:
                return f"{composite_type}: {years} years and {weeks} weeks"
    elif profile_key == "session":
        if n_periods < 20:
            return f"{composite_type}: {n_periods} trading days"
        elif n_periods < 60:
            return f"{composite_type}: {n_periods} trading days (~{n_periods//20} months)"
        else:
            return f"{composite_type}: {n_periods} trading days (~{n_periods//250} years)"
    
    # Default description
    return f"{composite_type}: {n_periods} periods"
