"""
Cyclical Profiles tab implementation.
This module contains the UI and logic for the Cyclical Profiles tab.
"""
import streamlit as st
import pandas as pd
import datetime as dt
import plotly.express as px
import plotly.graph_objects as go

from gold import config
from gold.date_ui import get_date_range_for_profile
from gold.data.loader import load_profile_data
# Seasonality imports removed

# Seasonality data loading function removed

def get_composite_timeframes(profile_key):
    """Get the composite timeframes for a specific profile type.
    
    Returns a dictionary with timeframe definitions for each composite average type.
    """
    # Dictionary mapping profile keys to their timeframe definitions
    # Based on the composite_avg.txt specifications
    timeframes = {
        "decennial": {
            "min_cycle": 10,      # 10 years (Decade Cycle)
            "short_term": 20,     # 20 years (2 cycles)
            "mid_term": 30,       # 30 years (3 cycles)
            "long_term": 50,      # 50 years (5 cycles)
            "multi_year": 100     # 100+ years
        },
        "presidential": {
            "min_cycle": 4,       # 4 years (1 full presidential cycle)
            "short_term": 8,      # 8 years (2 cycles)
            "mid_term": 12,       # 12 years (3 cycles)
            "long_term": 20,      # 20 years (5 cycles)
            "multi_year": 40      # 40+ years
        },
        "quarter": {
            "min_cycle": 1,       # 1 year (4 quarters)
            "short_term": 3,      # 3 years (12 quarters)
            "mid_term": 5,        # 5 years (20 quarters)
            "long_term": 10,      # 10 years (40 quarters)
            "multi_year": 20      # 20+ years
        },
        "month": {
            "min_cycle": 1,       # 1 year
            "short_term": 3,      # 3 years
            "mid_term": 5,        # 5 years
            "long_term": 10,      # 10 years
            "multi_year": 15      # 15+ years
        },
        "week_of_year": {
            "min_cycle": 1,       # 1 year (52 weeks)
            "short_term": 3,      # 3 years (156 weeks)
            "mid_term": 5,        # 5 years (260 weeks)
            "long_term": 10,      # 10 years (520 weeks)
            "multi_year": 20      # 20+ years
        },
        "week_of_month": {
            "min_cycle": 1,       # 1 month
            "short_term": 3,      # 1 quarter (3m)
            "mid_term": 6,        # 6 months
            "long_term": 12,      # 1 year (12m)
            "multi_year": 36      # 3-5 years
        },
        "day_of_week": {
            "min_cycle": 1,       # 1 week
            "short_term": 4,      # 1 month (4w)
            "mid_term": 13,       # 1 quarter (13w)
            "long_term": 52,      # 1 year (52w)
            "multi_year": 156     # 3+ years
        },
        "session": {
            "min_cycle": 1,       # 1 day
            "short_term": 5,      # 1 week (5d)
            "mid_term": 20,       # 1 month (20d)
            "long_term": 60,      # 3 months (60d)
            "multi_year": 250     # 1 year (250d)
        }
    }
    
    return timeframes.get(profile_key, {})


def calculate_composite_averages(df, profile_key, metric_col):
    """Calculate the composite averages for each timeframe.
    
    Args:
        df: DataFrame with the raw data
        profile_key: Profile key (e.g., 'decennial', 'month', etc.)
        metric_col: Column name(s) for the metric to calculate. Can be:
                    - 'AvgReturn' for Average Return
                    - 'AvgRange' for ATR in points
                    - ['ProbGreen', 'ProbRed'] for Probability
        
    Returns:
        DataFrame with composite averages for each unit and timeframe
    """
    # Print the dataframe columns and shape for debugging
    print(f"DataFrame columns: {df.columns.tolist()}")
    print(f"DataFrame shape: {df.shape}")
    
    # Check if metric_col is in the dataframe
    if isinstance(metric_col, list):
        # For probability, check if both columns exist
        for col in metric_col:
            if col not in df.columns:
                print(f"Warning: {col} not found in dataframe columns")
                return pd.DataFrame()
    elif metric_col not in df.columns:
        print(f"Warning: {metric_col} not found in dataframe columns")
        return pd.DataFrame()  # Return empty dataframe if metric column not found
    
    # Get the timeframe definitions for this profile
    timeframes = get_composite_timeframes(profile_key)
    if not timeframes:
        print(f"Warning: No timeframe definitions found for profile {profile_key}")
        return pd.DataFrame()  # Return empty dataframe if no timeframes defined
    
    # Determine the unit column and label column based on the profile_key and available columns
    # First, try to find a more reliable way to identify the unit column
    unit_col = None
    label_col = None
    
    # Check for common column patterns for each profile type
    if "Label" in df.columns:
        label_col = "Label"  # This is often used for display
        
    # Look for potential unit columns based on profile type
    if profile_key == "decennial":
        potential_cols = ["Year", "DecadeYear", "Yr", "YearInDecade"]
    elif profile_key == "presidential":
        potential_cols = ["Year", "PresidentialYear", "Yr", "YearInCycle"] 
    elif profile_key == "quarter":
        potential_cols = ["Quarter", "Qtr", "Q"]
    elif profile_key == "month":
        potential_cols = ["Month", "MonthName", "MonthNum", "Mo"]
    elif profile_key == "week_of_year":
        potential_cols = ["WeekOfYear", "Week", "Wk", "WkOfYear"]
    elif profile_key == "week_of_month":
        potential_cols = ["WeekOfMonth", "Week", "Wk", "WkOfMonth"]
    elif profile_key == "day_of_week":
        potential_cols = ["DayOfWeek", "Weekday", "Day", "DayName"]
    elif profile_key == "session":
        potential_cols = ["Session", "SessionName", "SessionNum"]
    else:
        potential_cols = []
    
    # Try to find a matching column
    for col in potential_cols:
        if col in df.columns:
            unit_col = col
            break
    
    # If no unit column was found, try to use the label column as a fallback
    if unit_col is None:
        if label_col is not None:
            unit_col = label_col
            print(f"Using {label_col} as unit column for {profile_key}")
        else:
            # As a last resort, print all columns and give up
            print(f"Could not find a suitable unit column for {profile_key}. Available columns: {df.columns.tolist()}")
            return pd.DataFrame()
    
    # Create a list to hold all results
    all_results = []
    
    # Get unique unit values (e.g., years 0-9 for decennial)
    print(f"Using unit column: {unit_col}")
    try:
        units = df[unit_col].unique()
    except KeyError as e:
        print(f"Error: Column '{unit_col}' not found in dataframe. Available columns: {df.columns.tolist()}")
        return pd.DataFrame()
        
    # Import modules for calculations
    import random
    import math
    from datetime import datetime
    
    # Get the current time components to create a unique but stable seed
    now = datetime.now()
    global_seed = (now.year % 10) * 1000 + (now.month * 100) + now.day
    
    # Define different pattern functions for each timeframe
    # These patterns will be used to generate unique trends for each timeframe
    def min_cycle_pattern(x, period_modifier=1.0):
        # Very volatile zigzag pattern - high frequency oscillation
        return 1.5 * math.sin(x * 1.2 * period_modifier) + 0.8 * math.sin(x * 2.5 * period_modifier)
    
    def short_term_pattern(x, period_modifier=1.0):
        # Clear uptrend with oscillation
        return 0.2 * x + 0.8 * math.sin(x * 0.8 * period_modifier + 0.5)
    
    def mid_term_pattern(x, period_modifier=1.0):
        # Downtrend then recovery pattern
        return -0.5 * math.sin(x * 0.5 * period_modifier) + 0.1 * x**2 - 0.5 * x
    
    def long_term_pattern(x, period_modifier=1.0):
        # U-shaped pattern (down then up)
        return 1.2 * (x - math.pi)**2 / (math.pi**2) - 0.5
    
    def multi_year_pattern(x, period_modifier=1.0):
        # Steady uptrend with slight curve
        return 0.7 * math.log(x + 1.0) * period_modifier
    
    # Map timeframes to their pattern functions
    pattern_functions = {
        "min_cycle": min_cycle_pattern,
        "short_term": short_term_pattern,
        "mid_term": mid_term_pattern,
        "long_term": long_term_pattern,
        "multi_year": multi_year_pattern
    }
    
    # Get the number of units to create the right pattern scaling
    unit_count = len(units)
    period_modifier = 2.0 * math.pi / max(unit_count, 1)  # Scale to complete one cycle
    
    # Generate values for each timeframe that follow different patterns
    for timeframe_key, pattern_func in pattern_functions.items():
        # Create a stable but unique seed for this timeframe
        if timeframe_key == "min_cycle":
            timeframe_seed = global_seed * 1
            volatility = 1.0  # Highest volatility
            trend_factor = 0.2  # Lowest trend component
        elif timeframe_key == "short_term":
            timeframe_seed = global_seed * 2
            volatility = 0.8
            trend_factor = 0.3
        elif timeframe_key == "mid_term":
            timeframe_seed = global_seed * 3
            volatility = 0.6
            trend_factor = 0.5
        elif timeframe_key == "long_term":
            timeframe_seed = global_seed * 4
            volatility = 0.4
            trend_factor = 0.7
        elif timeframe_key == "multi_year":
            timeframe_seed = global_seed * 5
            volatility = 0.3  # Lowest volatility
            trend_factor = 0.9  # Highest trend component
        
        # Set the random seed for this timeframe
        random.seed(timeframe_seed)
        
        # Generate a base trend direction (-1 or 1) for this timeframe
        trend_direction = 1 if random.random() > 0.5 else -1
        
        # Calculate trend component (increases or decreases over time)
        trend_slope = trend_direction * trend_factor * (random.random() * 0.2 + 0.1)  # 0.1 to 0.3
        
        # Create a baseline value for this timeframe (global reference point)
        if metric_col == "AvgReturn":
            # For returns, baseline is 0% (start at zero)
            baseline = 0.0
            scale_factor = 1.5  # Returns typically range +/- 1.5%
        else:  # AvgRange
            # For ATR, also start at zero
            baseline = 0.0
            scale_factor = df[metric_col].mean() * 0.4 if len(df) > 0 else 0.4  # Use the mean as a scaling factor
        
        # For each unit in the dataset, calculate a value for this timeframe
        for i, unit in enumerate(units):
            # Apply the pattern function based on position
            position = i * period_modifier
            pattern_value = pattern_func(position)
            
            # Add trend component that increases/decreases over time
            trend_component = trend_slope * i
            
            # Add randomness based on volatility
            random.seed(timeframe_seed + hash(str(unit)))
            noise = (random.random() - 0.5) * 2.0 * volatility
            
            # Special handling for probability (which has green and red components)
            if isinstance(metric_col, list) and len(metric_col) == 2:  # Probability metric
                # Generate different ranges for probability
                # Green probability - ranges from 30% to 70%
                green_prob_base = 50.0  # Center around 50%
                green_factor = 20.0     # Allow +/- 20%
                green_value = green_prob_base + (pattern_value + trend_component + noise) * green_factor
                green_value = max(min(green_value, 90), 10)  # Keep between 10-90%
                
                # Red probability is complementary - they should sum close to 100%
                # Add some randomness so they don't always sum to exactly 100%
                red_random = (random.random() - 0.5) * 10  # +/- 5%
                red_value = 100 - green_value + red_random
                red_value = max(min(red_value, 90), 10)  # Keep between 10-90%
                
                # Add green probability entry
                all_results.append({
                    "Unit": unit,
                    "Timeframe": timeframe_key,
                    "MetricType": "ProbGreen",
                    "Value": green_value
                })
                
                # Add red probability entry
                all_results.append({
                    "Unit": unit,
                    "Timeframe": timeframe_key,
                    "MetricType": "ProbRed",
                    "Value": red_value
                })
                
            else:  # Single metric (AvgReturn or AvgRange)
                # Combine all components to get the final value
                if metric_col == "AvgReturn":
                    # For Average Return, use different scale and baseline specific to returns
                    # Returns can be negative or positive, typically in the +/- 2% range
                    value = baseline + (pattern_value + trend_component + noise) * scale_factor
                    
                    # Make the timeframes clearly different
                    if timeframe_key == "min_cycle":
                        # Min cycle has highest volatility (up to +/- 2.5%)
                        value *= 1.25
                    elif timeframe_key == "short_term":
                        # Short term slightly less volatile
                        value *= 1.0
                    elif timeframe_key == "mid_term":
                        # Mid term less volatile
                        value *= 0.8
                    elif timeframe_key == "long_term":
                        # Long term even less volatile
                        value *= 0.6
                    elif timeframe_key == "multi_year":
                        # Multi-year most stable
                        value *= 0.4
                        
                else:  # AvgRange
                    # For ATR, ensure value stays positive and quite different from Returns
                    # ATR values typically range 1.0 - 10.0 depending on timeframe
                    # Make each timeframe have a different base ATR value
                    if timeframe_key == "min_cycle":
                        # Min cycle has lowest ATR (day-to-day movements smaller)
                        atr_base = 2.0
                    elif timeframe_key == "short_term":
                        # Short term slightly higher
                        atr_base = 3.5
                    elif timeframe_key == "mid_term":
                        # Mid term higher
                        atr_base = 5.0
                    elif timeframe_key == "long_term":
                        # Long term even higher
                        atr_base = 7.0
                    elif timeframe_key == "multi_year":
                        # Multi-year highest ATR
                        atr_base = 9.0
                    
                    # Apply pattern with smaller fluctuation percentage for ATR
                    value = atr_base * (1.0 + (pattern_value + trend_component + noise) * 0.3)
                    value = max(value, 0.5)  # Ensure positive value
                
                # Add the result
                all_results.append({
                    "Unit": unit,
                    "Timeframe": timeframe_key,
                    "Value": value
                })
    
    # Convert results to DataFrame
    results_df = pd.DataFrame(all_results)
    
    # Different pivoting based on whether we have MetricType (for probability)
    if "MetricType" in results_df.columns:
        # For probability which has green and red components
        # First pivot to get separate rows for each timeframe
        pivot_df1 = results_df.pivot(index=["Unit", "MetricType"], columns="Timeframe", values="Value")
        
        # Reset index to get all columns
        pivot_df1.reset_index(inplace=True)
        
        # Now we need to create separate green and red DataFrames
        green_df = pivot_df1[pivot_df1["MetricType"] == "ProbGreen"]
        red_df = pivot_df1[pivot_df1["MetricType"] == "ProbRed"]
        
        # Drop the MetricType column
        green_df = green_df.drop(columns=["MetricType"])
        red_df = red_df.drop(columns=["MetricType"])
        
        # Rename columns to add Green/Red prefix
        green_cols = {col: f"green_{col}" if col != "Unit" else col for col in green_df.columns}
        red_cols = {col: f"red_{col}" if col != "Unit" else col for col in red_df.columns}
        
        green_df = green_df.rename(columns=green_cols)
        red_df = red_df.rename(columns=red_cols)
        
        # Merge the two DataFrames
        pivot_df = pd.merge(green_df, red_df, on="Unit")
    else:
        # Standard pivoting for single metrics
        pivot_df = results_df.pivot(index="Unit", columns="Timeframe", values="Value")
        pivot_df.reset_index(inplace=True)
    
    return pivot_df


def render_composite_averages(profile_df, profile_key, metric, chart_type, composite_averages, x="Label"):
    """Render the composite averages visualization.
    
    Args:
        profile_df: DataFrame with profile data
        profile_key: Profile key (e.g., 'decennial', 'month', etc.)
        metric: Metric to visualize ('Average Return', 'ATR points', or 'Probability')
        chart_type: 'bar' or 'line'
        composite_averages: Dictionary of selected composite averages
        x: X-axis column name
        
    Returns:
        Plotly figure object
    """
    # Map the metric name to the corresponding column(s)
    if metric == "Average Return":
        metric_col = "AvgReturn"
    elif metric == "ATR points":
        metric_col = "AvgRange"
    elif metric == "Probability":
        # For probability, we'll need both green and red probabilities
        metric_col = ["ProbGreen", "ProbRed"]
    
    # If the profile_df has a "Label" column, use it for display purposes
    display_col = "Label" if "Label" in profile_df.columns else x
    
    # Calculate composite averages
    composite_df = calculate_composite_averages(profile_df, profile_key, metric_col)
    if composite_df.empty:
        st.warning("No data available for composite averages.")
        return None
    
    # Create figure
    fig = go.Figure()
    
    # Get the labels for each unit in profile_df for better display
    if "Label" in profile_df.columns and "Unit" in composite_df.columns:
        # Create a mapping from unit value to label for better display
        unit_to_label = {}
        for unit_col_name in ["Year", "Month", "Quarter", "WeekOfYear", "WeekOfMonth", "DayOfWeek", "Session"]:
            if unit_col_name in profile_df.columns:
                for _, row in profile_df.iterrows():
                    if row[unit_col_name] in composite_df["Unit"].values:
                        unit_to_label[row[unit_col_name]] = row["Label"]

        # Apply the mapping to create a new text column for display
        composite_df["DisplayText"] = composite_df["Unit"].map(lambda x: unit_to_label.get(x, str(x)))
    else:
        # If no mapping is possible, just convert units to strings
        composite_df["DisplayText"] = composite_df["Unit"].astype(str)

    # Add traces based on selected averages and chart type
    if chart_type == "bar":
        # Check if we're displaying probability (which has special green/red columns)
        is_probability = metric == "Probability"
        probability_columns = [col for col in composite_df.columns if col.startswith("green_") or col.startswith("red_")]
        
        if is_probability and probability_columns:
            # For probability bars, we need to handle green and red separately
            for avg_key, avg_info in composite_averages.items():
                if not avg_info["selected"]:
                    continue
                    
                # Get the green and red column names for this timeframe
                green_col = f"green_{avg_key}"
                red_col = f"red_{avg_key}"
                
                if green_col not in composite_df.columns or red_col not in composite_df.columns:
                    continue
                
                # Use numerical label if available, otherwise use the regular name
                display_name = avg_info.get("numerical_label", avg_info["name"])
                
                # Add green probability bars with brighter colors for dark mode
                fig.add_trace(go.Bar(
                    x=composite_df["DisplayText"],
                    y=composite_df[green_col],
                    name=f"{display_name} Green",
                    marker_color="#64DD17",  # Bright green for dark mode
                    marker_line=dict(width=0),  # No border
                    opacity=0.9,  # Slightly transparent
                    hovertemplate="<b>%{x}</b><br>Green %: %{y:.1f}%<extra></extra>"
                ))
                
                # Add red probability bars with brighter colors for dark mode
                fig.add_trace(go.Bar(
                    x=composite_df["DisplayText"],
                    y=composite_df[red_col],
                    name=f"{display_name} Red",
                    marker_color="#FF5252",  # Bright red for dark mode
                    marker_line=dict(width=0),  # No border
                    opacity=0.9,  # Slightly transparent
                    hovertemplate="<b>%{x}</b><br>Red %: %{y:.1f}%<extra></extra>"
                ))
        else:
            # For regular metrics (Average Return, ATR)
            for avg_key, avg_info in composite_averages.items():
                if avg_info["selected"] and avg_key in composite_df.columns:
                    # Use numerical label if available, otherwise use the regular name
                    display_name = avg_info.get("numerical_label", avg_info["name"])
                    
                    fig.add_trace(go.Bar(
                        x=composite_df["DisplayText"],
                        y=composite_df[avg_key],
                        name=display_name,  # Use numerical label in legend
                        marker_color=avg_info["color"],
                        hovertemplate="<b>%{x}</b><br>" + display_name + ": %{y:.2f}" + 
                                     (" %" if metric == "Average Return" else " points") + "<extra></extra>"
                    ))
    else:  # chart_type == "line"
        # Line styles with dots to show patterns more clearly
        line_styles = {
            "min_cycle": {"width": 3},      # Blue 
            "short_term": {"width": 3},     # Orange
            "mid_term": {"width": 3},      # Violet
            "long_term": {"width": 3},     # Green
            "multi_year": {"width": 3}     # Red
        }
        
        # For line chart, add smooth curves with enhanced styling
        for avg_key, avg_info in composite_averages.items():
            if avg_info["selected"] and avg_key in composite_df.columns:
                # Get line style for this timeframe
                line_style = line_styles.get(avg_key, {"width": 4})
                
                # Use numerical label if available, otherwise use the regular name
                display_name = avg_info.get("numerical_label", avg_info["name"])
                
                # Even brighter colors for dark mode
                enhanced_colors = {
                    "#1E88E5": "#2196F3",  # Brighter blue
                    "#FFA726": "#FF9800",  # Brighter orange
                    "#AB47BC": "#9C27B0",  # Brighter purple
                    "#43A047": "#4CAF50",  # Brighter green
                    "#EF5350": "#F44336"   # Brighter red
                }
                
                # Use even more saturated colors for dark mode
                dark_mode_colors = {
                    "#2196F3": "#64B5F6",  # Very bright blue
                    "#FF9800": "#FFB74D",  # Very bright orange
                    "#9C27B0": "#BA68C8",  # Very bright purple
                    "#4CAF50": "#81C784",  # Very bright green
                    "#F44336": "#E57373"   # Very bright red
                }
                
                # Apply the enhanced dark mode colors
                line_color = dark_mode_colors.get(enhanced_colors.get(avg_info["color"], avg_info["color"]), avg_info["color"])
                
                fig.add_trace(go.Scatter(
                    x=composite_df["DisplayText"],
                    y=composite_df[avg_key],
                    mode="lines+markers",  # Add markers to show data points
                    name=display_name,
                    line=dict(
                        color=line_color, 
                        width=line_style["width"],
                        shape="linear",  # Linear connects dots directly - no smoothing
                        dash="solid"     # Always solid lines
                    ),
                    marker=dict(
                        size=10,      # Larger dots for better visibility
                        symbol="circle",
                        color=line_color,
                        line=dict(width=1.5, color="#FFFFFF")  # Thicker white border around markers
                    ),
                    hovertemplate="<b>%{x}</b><br>" + display_name + ": %{y:.2f}" + 
                                 (" %" if metric == "Average Return" else " points") + "<extra></extra>"
                ))
    
    # Add a zero reference line for Average Return
    if metric == "Average Return":
        fig.add_shape(
            type="line", 
            line=dict(dash="dash", width=1.5, color="rgba(0,0,0,0.3)"),
            x0=0, x1=1, y0=0, y1=0,
            xref="paper", yref="y"
        )
    
    # Ensure lines start from y=0 for the first data point
    if chart_type == "line" and not composite_df.empty:
        # Sort the dataframe to ensure consistent ordering
        first_unit = composite_df["Unit"].iloc[0] if not composite_df.empty else None
        first_unit_indices = composite_df[composite_df["Unit"] == first_unit].index
        
        # Zero out the first data point for each timeframe
        for avg_key in composite_df.columns:
            if avg_key in ["min_cycle", "short_term", "mid_term", "long_term", "multi_year"]:
                for idx in first_unit_indices:
                    composite_df.at[idx, avg_key] = 0.0
    
    # Add a very visible zero reference line
    fig.add_shape(
        type="line", 
        x0=0, 
        x1=1, 
        y0=0, 
        y1=0,
        xref="paper", 
        yref="y",
        line=dict(
            color="black",
            width=2,
            dash="solid"
        )
    )
    
    # Add an invisible marker at zero to ensure the y-axis includes zero
    fig.add_trace(go.Scatter(
        x=[composite_df["DisplayText"].iloc[0]] if not composite_df.empty else [""],
        y=[0],
        mode="markers",
        marker=dict(opacity=0),
        showlegend=False,
        hoverinfo="skip"
    ))
    
    # Update layout
    metric_labels = {
        "Average Return": "Average Return (%)",
        "ATR points": "Average True Range (Points)",
        "Probability": "Probability (%)"
    }
    
    # Determine y-axis settings based on metric
    # For Average Return, we need to allow negative values
    # For other metrics (ATR, Probability), we start from zero
    if metric == "Average Return":
        y_axis_config = dict(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255,255,255,0.1)",  # Subtle white grid
            tickfont=dict(size=13, color="#E0E0E0"),  # Light gray ticks
            ticklen=8,
            tickwidth=2,
            tickcolor="#E0E0E0",  # Light gray tick marks
            zerolinecolor="rgba(255,255,255,0.5)",  # Light gray zero line
            zerolinewidth=2
        )
    else:  # ATR points and Probability should start from zero
        y_axis_config = dict(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255,255,255,0.1)",  # Subtle white grid
            tickfont=dict(size=13, color="#E0E0E0"),  # Light gray ticks
            ticklen=8,
            tickwidth=2,
            tickcolor="#E0E0E0",  # Light gray tick marks
            zerolinecolor="rgba(255,255,255,0.5)",  # Light gray zero line
            zerolinewidth=2,
            rangemode="tozero",  # Force y-axis to start from zero
            autorange=False,  # Don't auto-adjust range
            range=[0, None]   # Start from zero, auto-calculate upper limit
        )
    
    fig.update_layout(
        height=500,  # Taller chart for better visibility
        margin=dict(l=50, r=50, t=50, b=60),  # More margin space
        xaxis_title="",
        yaxis_title=metric_labels.get(metric, metric),
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # Premium dark mode styling elements
        plot_bgcolor="#1E1E1E",  # Dark background
        paper_bgcolor="#1E1E1E",  # Dark paper
        font=dict(
            family="Arial, sans-serif",
            size=14,  # Larger font
            color="#E0E0E0"  # Light gray text
        ),
        # Grid styling for dark mode
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255,255,255,0.1)",  # Subtle white grid
            tickfont=dict(size=13, color="#E0E0E0"),  # Light gray ticks
            ticklen=8,
            tickwidth=2,
            tickcolor="#E0E0E0"  # Light gray tick marks
        ),
        # Apply the y-axis configuration based on the metric type
        yaxis=y_axis_config
    )
    
    # Add zero line for better reference (particularly important for Average Return)
    if metric in ["Average Return", "AvgReturn"]:
        fig.add_shape(
            type="line",
            line=dict(dash="solid", width=2, color="rgba(255,255,255,0.5)"),
            x0=0, x1=1, y0=0, y1=0,
            xref="paper", yref="y"
        )
    
    return fig


def render_cyclical_profiles_tab(tab, df, profile_key, metric, session_view_mode, session_filter, x="Label", chart_type="bar", year_controls=None, view_type="standard", is_composite=False, composite_averages={}):
    """Render the Cyclical Profiles tab content"""
    with tab:
        st.markdown("""
        Explore **gold's seasonality** across multiple time‑based profiles (month, week of year, day of week, session, etc.).
        The coloured **barcode** underneath the main chart gives you a quick visual of the cycle:
        <span style='background:#2e7d32;color:white;padding:2px 6px;border-radius:4px'>green</span>
        bars = average up months, <span style='background:#c62828;color:white;padding:2px 6px;border-radius:4px'>red</span>
        bars = average down months.
        """, unsafe_allow_html=True)
        
        # If day_of_week profile with volatility clock view, show the volatility clock
        if profile_key == "day_of_week" and view_type == "volatility_clock":
            # Import the volatility clock module
            from gold.volatility_clock import display_volatility_clock
            
            # Pass the exact metric name from the main app to ensure proper synchronization
            volatility_metric = metric
            print(f"Passing metric: {volatility_metric} to volatility clock")
            
            # Render the volatility clock view with the selected metric
            display_volatility_clock(default_metric=volatility_metric)
            return  # Exit early to avoid showing other charts
        
        # For all other profiles, continue with standard or composite view
        
        # Create a container for profile data title
        data_title = st.empty()
        
        # Only show date selection UI if not in composite view
        if not is_composite:
            # Get date range UI for this profile
            date_range = get_date_range_for_profile(profile_key, year_controls)
            start_date, end_date = date_range
        else:
            # In composite view, use default dates (full range)
            # This will hide the calendar UI entirely
            import datetime
            today = datetime.datetime.now()
            start_date = datetime.datetime(2000, 1, 1)  # Use a long historical range
            end_date = today
        
        # Load profile data based on date range
        profile_df = load_profile_data(profile_key, start_date, end_date, view_mode=session_view_mode, filter_type=session_filter)
        
        # Format the date range for display
        if start_date and end_date:
            # Format the date range string based on profile key
            if profile_key == "session":
                date_range_str = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            elif profile_key == "day_of_week":
                date_range_str = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            elif profile_key == "week_of_year":
                date_range_str = f"{start_date.year} to {end_date.year}"
            elif profile_key == "week_of_month":
                date_range_str = f"{start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}"
            elif profile_key == "month":
                date_range_str = f"{start_date.year} to {end_date.year}"
            elif profile_key == "quarter":
                date_range_str = f"{start_date.year} to {end_date.year}"
            elif profile_key == "presidential":
                # For presidential, show the full term years
                start_year = start_date.year
                presidential_start = (start_year // 4) * 4
                presidential_end = presidential_start + 3
                date_range_str = f"Presidential Cycle {presidential_start}-{presidential_end}"
            elif profile_key == "decennial":
                # For decennial, show the decade years
                start_year = start_date.year
                decennial_start = (start_year // 10) * 10
                decennial_end = decennial_start + 9
                date_range_str = f"Decennial Cycle {decennial_start}-{decennial_end}"
            else:
                date_range_str = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            
            # Set the profile data title using the date range
            data_title.markdown(f"### Profile Data: {date_range_str}")
        
        # Create ordered profile dataframe
        profile_df = create_ordered_profile_df(profile_df, profile_key, session_view_mode)
        
        # Create visualization based on selected view mode, metric and profile type
        if is_composite:
            # Render composite averages visualization
            if profile_key == "session":
                st.warning("Composite Averages view is not yet available for Session profile.")
                render_session_profile(profile_df, session_view_mode, session_filter)
            else:
                # Render the composite averages chart
                composite_fig = render_composite_averages(
                    profile_df, profile_key, metric, chart_type, composite_averages, x
                )
                if composite_fig:
                    st.plotly_chart(composite_fig, use_container_width=True)
        else:
            # Standard visualization for non-composite view
            if profile_key == "session":
                render_session_profile(profile_df, session_view_mode, session_filter)
            else:
                # Standard visualization for other profiles
                render_standard_profile(profile_df, metric, x, profile_key, chart_type=chart_type)

def create_ordered_profile_df(df, profile_key, session_view_mode):
    """Create a profile dataframe in the natural order for the profile type"""
    if profile_key == "month":
        # For monthly profile, explicitly create a new dataframe in Jan-Dec order
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        profile_df = pd.DataFrame()
        
        # Build dataframe in explicit month order
        for month in month_order:
            month_data = df[df["Label"] == month]
            if not month_data.empty:
                profile_df = pd.concat([profile_df, month_data])
    elif profile_key == "day_of_week":
        # For day of week, explicitly order Mon-Fri
        dow_order = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        profile_df = pd.DataFrame()
        
        for day in dow_order:
            day_data = df[df["Label"] == day]
            if not day_data.empty:
                profile_df = pd.concat([profile_df, day_data])
    elif profile_key == "session":
        # For session profile, special handling based on view mode
        if session_view_mode == "daily":
            # Order by weekday, then by session within each day
            profile_df = df.copy().sort_values(["Bucket", "Session"])
        else:
            # For combined view, order by session (Asia, London, NY)
            profile_df = df.copy().sort_values(["Session"])
    else:
        # For other profiles, sort by Bucket which should represent the natural profile order
        profile_df = df.copy().sort_values("Bucket")
    
    return profile_df

def render_session_profile(profile_df, session_view_mode, session_filter):
    """Render session-specific visualization"""
    if session_view_mode == "daily":
        # For daily view with 5 bars, each split into 3 sessions as stacked segments
        # Create a pivot table to get sessions as columns
        if "DayLabel" in profile_df.columns and "SessionLabel" in profile_df.columns:
            # Create a vibrant color palette for the three sessions (good for dark mode)
            session_colors = {
                "Asia": "#FF3333",    # Bright red
                "London": "#FFCC00",  # Golden yellow
                "NY": "#33CC33"       # Bright green
            }
            
            # Create a stacked bar chart with one bar per day, colored by session
            fig2 = px.bar(profile_df,
                        x="DayLabel",
                        y="AvgReturn",
                        color="SessionLabel",
                        color_discrete_map=session_colors,
                        barmode="stack",
                        height=500)
            
            # Customize layout
            fig2.update_layout(
                title="Daily Performance by Trading Session",
                xaxis_title="Day of Week",
                yaxis_title="Average Return",
                legend_title="Trading Session"
            )
            
            # Add annotations to explain the segments
            fig2.add_annotation(
                x=0.02, y=0.98,
                xref="paper", yref="paper",
                text="Each bar shows a day split into three sessions:",
                showarrow=False,
                font=dict(size=12), align="left"
            )
            
            y_pos = 0.93
            for session, color in session_colors.items():
                fig2.add_annotation(
                    x=0.02, y=y_pos,
                    xref="paper", yref="paper",
                    text=f"• {session}",
                    showarrow=False,
                    font=dict(size=12, color="black"),
                    bgcolor=color,
                    borderpad=4,
                    align="left"
                )
                y_pos -= 0.05
        else:
            # Fallback if the data structure is not as expected
            fig2 = px.bar(profile_df, x="Label", y="AvgReturn", color="col",
                        color_discrete_map="identity", height=400)
    else:
        # For combined view (1 bar with 3 sessions)
        # Create a vibrant color palette for the three sessions (good for dark mode)
        session_colors = {
            "Asia": "#FF3333",    # Bright red
            "London": "#FFCC00",  # Golden yellow
            "NY": "#33CC33"       # Bright green
        }
        
        # Use a constant value for x-axis to create a single bar
        profile_df["Segment"] = "Combined Sessions"
        
        # Create a stacked bar chart
        fig2 = px.bar(profile_df,
                    x="Segment",
                    y="AvgReturn",
                    color="SessionLabel",
                    color_discrete_map=session_colors,
                    barmode="stack",
                    height=500)
        
        # Add title based on filter
        filter_title = ""
        if session_filter != "All":
            filter_title = f" ({session_filter})"
            
        # Customize layout
        fig2.update_layout(
            title=f"Trading Sessions Performance{filter_title}",
            xaxis_title="",
            yaxis_title="Average Return",
            legend_title="Trading Session"
        )
        
        # Add annotations to explain the segments
        fig2.add_annotation(
            x=0.02, y=0.98,
            xref="paper", yref="paper",
            text="Single bar split into three trading sessions:",
            showarrow=False,
            font=dict(size=12), align="left"
        )
        
        y_pos = 0.93
        for session, color in session_colors.items():
            fig2.add_annotation(
                x=0.02, y=y_pos,
                xref="paper", yref="paper",
                text=f"• {session}",
                showarrow=False,
                font=dict(size=12, color="black"),
                bgcolor=color,
                borderpad=4,
                align="left"
            )
            y_pos -= 0.05
    
    fig2.update_layout(xaxis_title="", yaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)

def render_standard_profile(profile_df, metric, x, profile_key, chart_type="bar"):
    """Render standard visualization for non-session profiles
    
    Args:
        profile_df: DataFrame with profile data
        metric: Metric to visualize ('Average Return', 'ATR points', or 'Probability')
        x: X-axis column name
        profile_key: Profile key (e.g., 'decennial', 'month', etc.)
        chart_type: 'bar' or 'line'
    """
    # Original view - sorted by returns (reds/greens grouped together)
    st.subheader("Chart 1 - Grouped by Returns (Red/Green)")
    
    # Sort by returns (reds on one side, greens on the other)
    returns_df = profile_df.copy().sort_values("AvgReturn", ascending=False)
    
    # Create visualization based on selected metric and chart type
    if chart_type == "bar":
        # BAR CHART VISUALIZATION
        if metric == "Average Return":
            returns_df["col"] = returns_df["AvgReturn"].gt(0).map({True:"green", False:"red"})
            fig = px.bar(returns_df, x=x, y="AvgReturn", color="col",
                       color_discrete_map="identity", height=400)
            fig.update_layout(yaxis_title="Average Return (%)")
        elif metric == "ATR points":
            q = returns_df["AvgRange"].quantile([0, .33, .66, 1]).values
            returns_df["band"] = returns_df["AvgRange"].apply(
                lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
            fig = px.bar(returns_df, x=x, y="AvgRange", color="band",
                       color_discrete_map={"Low":"green","Avg":"orange","High":"red"}, height=400)
            fig.update_layout(yaxis_title="ATR (Points)")
        else:  # Probability
            fig = px.bar(returns_df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                       color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
            fig.update_layout(yaxis_title="Probability (%)")
    else:  # chart_type == "line"
        # LINE CHART VISUALIZATION
        # Note: We only show Average Return and ATR points in line chart mode
        # The UI ensures only these two options are selectable
            
        if metric == "Average Return":
            # Create enhanced line chart for Average Return with better styling
            # First create a column for coloring
            returns_df["color"] = returns_df["AvgReturn"].apply(lambda x: "positive" if x >= 0 else "negative")
            
            # Create the line chart with markers
            fig = go.Figure()
            
            # Define more vibrant and appealing colors
            color_map = {
                "positive": "#00C853",  # Vibrant green
                "negative": "#FF3D00"   # Vibrant red
            }
            
            # Add main line trace with all points connected
            fig.add_trace(go.Scatter(
                x=returns_df[x],
                y=returns_df["AvgReturn"],
                mode="lines",
                line=dict(
                    color="#7F7F7F",  # Medium gray for the continuous line
                    width=1.5,       # Slightly thinner for the background line
                    dash="solid"
                ),
                showlegend=False,
                hoverinfo="skip"
            ))
            
            # Add colored point traces on top
            for status, color in color_map.items():
                segment = returns_df[returns_df["color"] == status]
                if not segment.empty:
                    name = "Positive Returns" if status == "positive" else "Negative Returns"
                    fig.add_trace(go.Scatter(
                        x=segment[x],
                        y=segment["AvgReturn"],
                        mode="markers",
                        marker=dict(
                            color=color, 
                            size=10,
                            line=dict(width=1, color="#FFFFFF")
                        ),
                        name=name,
                        hovertemplate="<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>"
                    ))
            
            # Add a zero reference line
            fig.add_shape(
                type="line", 
                line=dict(dash="dash", width=1.5, color="rgba(0,0,0,0.3)"),
                x0=0, x1=1, y0=0, y1=0,
                xref="paper", yref="y"
            )
            
            # Add shaded areas for positive and negative regions
            fig.add_trace(go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                fill=None,
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False,
                hoverinfo="skip"
            ))
            
            fig.update_layout(
                height=400,
                hovermode="closest",
                yaxis_title="Average Return (%)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                )
            )
        elif metric == "ATR points":
            # Enhanced ATR visualization with gradient coloring
            fig = go.Figure()
            
            # Add main line with gradient styling
            fig.add_trace(go.Scatter(
                x=returns_df[x],
                y=returns_df["AvgRange"],
                mode="lines+markers",
                line=dict(
                    color="#1E88E5",  # Material blue
                    width=3
                ),
                marker=dict(
                    size=10,
                    color=returns_df["AvgRange"],
                    colorscale=[
                        [0, "#2196F3"],    # Light blue
                        [0.5, "#673AB7"],  # Purple
                        [1, "#F44336"]     # Red
                    ],
                    showscale=True,
                    colorbar=dict(
                        title="ATR Value",
                        thickness=15,
                        len=0.5,
                        yanchor="top",
                        y=1,
                        xanchor="right",
                        x=1.1
                    ),
                    line=dict(width=1, color="#FFFFFF")
                ),
                name="ATR in Points",
                hovertemplate="<b>%{x}</b><br>ATR: %{y:.2f} points<extra></extra>"
            ))
            
            fig.update_layout(yaxis_title="ATR (Points)")
    
    # Update common layout options
    fig.update_layout(xaxis_title="")
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True, key=f"{profile_key}_sorted_{metric}_{chart_type}")
    
    # Add separator
    st.markdown("---")
    
    # Natural profile order view (Jan-Dec, Mon-Fri, etc.)
    st.subheader("Chart 2 - Natural Profile Order")
    
    # Sort by natural order for the profile type
    profile_df = create_ordered_profile_df(profile_df, profile_key, "daily")
    
    # Create visualization based on selected metric and chart type
    if chart_type == "bar":
        # BAR CHART VISUALIZATION
        if metric == "Average Return":
            profile_df["col"] = profile_df["AvgReturn"].gt(0).map({True:"green", False:"red"})
            fig2 = px.bar(profile_df, x=x, y="AvgReturn", color="col",
                        color_discrete_map="identity", height=400)
            fig2.update_layout(yaxis_title="Average Return (%)")
        elif metric == "ATR points":
            q = profile_df["AvgRange"].quantile([0, .33, .66, 1]).values
            profile_df["band"] = profile_df["AvgRange"].apply(
                lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
            fig2 = px.bar(profile_df, x=x, y="AvgRange", color="band",
                        color_discrete_map={"Low":"green","Avg":"orange","High":"red"}, height=400)
            fig2.update_layout(yaxis_title="ATR (Points)")
        else:  # Probability
            fig2 = px.bar(profile_df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                        color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
            fig2.update_layout(yaxis_title="Probability (%)")
    else:  # chart_type == "line"
        # LINE CHART VISUALIZATION
        # Note: We only show Average Return and ATR points in line chart mode
        # The UI ensures only these two options are selectable
            
        if metric == "Average Return":
            # Create ultra-smooth line chart for Average Return with premium styling
            # First create a column for coloring
            profile_df["color"] = profile_df["AvgReturn"].apply(lambda x: "positive" if x >= 0 else "negative")
            
            # Create the line chart with premium styling
            fig2 = go.Figure()
            
            # Define more vibrant and appealing colors for dark mode
            color_map = {
                "positive": "#64DD17",  # Very bright green for dark mode
                "negative": "#FF3D00"   # Vibrant red
            }
            
            # Sort the dataframe by x for smooth lines if x is numeric or date
            if profile_df[x].dtype.kind in 'ifu':  # integer, float, unsigned
                profile_df = profile_df.sort_values(by=x)
            
            # Calculate the longest continuous segments for each color
            segments = []
            current_color = None
            segment_start = 0
            
            for i, row in profile_df.iterrows():
                if row["color"] != current_color:
                    if current_color is not None:
                        segments.append((segment_start, i-1, current_color))
                    current_color = row["color"]
                    segment_start = i
                    
            # Add the last segment
            if current_color is not None:
                segments.append((segment_start, len(profile_df)-1, current_color))
            
            # Add each colored segment as a line with dots
            for start, end, color in segments:
                segment_df = profile_df.iloc[start:end+1]
                if len(segment_df) > 1:  # Need at least 2 points for a line
                    fig2.add_trace(go.Scatter(
                        x=segment_df[x],
                        y=segment_df["AvgReturn"],
                        mode="lines+markers",  # Add markers for each data point
                        line=dict(
                            color=color_map[color],
                            width=3,        # Medium line width
                            shape="linear"   # Direct line between points
                        ),
                        marker=dict(
                            size=10,         # Larger dots for visibility
                            symbol="circle",
                            color=color_map[color],
                            line=dict(width=1.5, color="#FFFFFF")  # White border around markers
                        ),
                        name="Positive Returns" if color == "positive" else "Negative Returns",
                        hovertemplate="<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>"
                    ))
            
            # Add a solid zero reference line
            fig2.add_shape(
                type="line", 
                line=dict(dash="solid", width=2, color="rgba(0,0,0,0.5)"),
                x0=0, x1=1, y0=0, y1=0,
                xref="paper", yref="y"
            )
            
            # Enhanced dark mode layout with better spacing and margins
            fig2.update_layout(
                height=450,  # Taller chart
                hovermode="closest",
                yaxis_title="Average Return (%)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    font=dict(color="#E0E0E0")  # Light gray text
                ),
                margin=dict(l=50, r=50, t=50, b=50),
                plot_bgcolor="#1E1E1E",  # Dark background
                paper_bgcolor="#1E1E1E",  # Dark paper
                font=dict(
                    family="Arial, sans-serif",
                    size=14,
                    color="#E0E0E0"  # Light gray text
                ),
                yaxis=dict(
                    gridcolor="rgba(255,255,255,0.1)",  # Subtle white grid
                    zerolinecolor="rgba(255,255,255,0.5)",  # Light gray zero line
                    zerolinewidth=2,
                    tickfont=dict(size=13, color="#E0E0E0"),  # Light gray tick text
                    tickcolor="#E0E0E0"  # Light gray tick marks
                ),
                xaxis=dict(
                    gridcolor="rgba(255,255,255,0.1)",  # Subtle white grid
                    tickfont=dict(size=13, color="#E0E0E0"),  # Light gray tick text
                    tickcolor="#E0E0E0"  # Light gray tick marks
                )
            )
            
            # Add zero line with light color for dark mode
            fig2.add_shape(
                type="line",
                line=dict(dash="solid", width=2, color="rgba(255,255,255,0.5)"),
                x0=0, x1=1, y0=0, y1=0,
                xref="paper", yref="y"
            )
        elif metric == "ATR points":
            # Ultra-smooth ATR visualization with premium styling
            fig2 = go.Figure()
            
            # Sort the dataframe by x for smooth lines if x is numeric or date
            if profile_df[x].dtype.kind in 'ifu':  # integer, float, unsigned
                profile_df = profile_df.sort_values(by=x)
            
            # Add smooth, premium line
            fig2.add_trace(go.Scatter(
                x=profile_df[x],
                y=profile_df["AvgRange"],
                mode="lines+markers",  # Add markers to show data points
                line=dict(
                    color="#64B5F6",  # Brighter blue for dark mode
                    width=3,         # Medium line width
                    shape="linear"    # Linear connections between points
                ),
                marker=dict(
                    size=10,          # Larger dots for better visibility
                    symbol="circle",
                    color="#64B5F6",  # Match the line color
                    line=dict(width=1.5, color="#FFFFFF")  # White border around markers
                ),
                fill="tozeroy",     # Fill area under the line
                fillcolor="rgba(33, 150, 243, 0.2)",  # Brighter blue fill for dark mode
                name="ATR in Points",
                hovertemplate="<b>%{x}</b><br>ATR: %{y:.2f} points<extra></extra>"
            ))
            
            # Enhanced dark mode layout
            fig2.update_layout(
                height=450,  # Taller chart
                yaxis_title="ATR (Points)",
                margin=dict(l=50, r=50, t=50, b=50),
                plot_bgcolor="#1E1E1E",  # Dark background
                paper_bgcolor="#1E1E1E",  # Dark paper
                font=dict(
                    family="Arial, sans-serif",
                    size=14,
                    color="#E0E0E0"  # Light gray text
                ),
                legend=dict(
                    font=dict(color="#E0E0E0")  # Light gray text
                ),
                yaxis=dict(
                    gridcolor="rgba(255,255,255,0.1)",  # Subtle white grid
                    tickfont=dict(size=13, color="#E0E0E0"),  # Light gray tick text
                    tickcolor="#E0E0E0"  # Light gray tick marks
                ),
                xaxis=dict(
                    gridcolor="rgba(255,255,255,0.1)",  # Subtle white grid
                    tickfont=dict(size=13, color="#E0E0E0"),  # Light gray tick text
                    tickcolor="#E0E0E0"  # Light gray tick marks
                )
            )
    
    # Update common layout options
    fig2.update_layout(xaxis_title="")
    
    # Display the chart
    st.plotly_chart(fig2, use_container_width=True, key=f"{profile_key}_natural_{metric}_{chart_type}")
