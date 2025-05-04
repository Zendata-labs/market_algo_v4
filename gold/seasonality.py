"""
Seasonality analysis module for gold market data.
Provides functions to calculate and visualize seasonal patterns across different timeframes.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime as dt
from datetime import datetime, timedelta
import calendar

def calculate_seasonality(df, years_back=10, return_type="open-close", cutoff_date=None):
    """
    Calculate seasonality data across years.
    
    Args:
        df: DataFrame with OHLC data
        years_back: Number of years to look back
        return_type: Method to calculate returns ('open-close' or 'close-close')
        cutoff_date: Optional, the maximum date to include (defaults to today)
    
    Returns:
        DataFrame with seasonality data
    """
    # Ensure datetime format and numeric columns
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    
    # Convert price columns to numeric
    for col in ["Open", "High", "Low", "Close"]:
        if col in df.columns:
            # Remove any commas and convert to float
            if df[col].dtype == object:  # String or mixed type
                df[col] = df[col].astype(str).str.replace(',', '').astype(float)
    
    # Apply cutoff date if provided
    if cutoff_date is not None:
        # Make sure cutoff_date is a pandas Timestamp
        if not isinstance(cutoff_date, pd.Timestamp):
            if isinstance(cutoff_date, str):
                cutoff_dt = pd.Timestamp(cutoff_date)
            elif isinstance(cutoff_date, dt.date):
                cutoff_dt = pd.Timestamp(cutoff_date.year, cutoff_date.month, cutoff_date.day)
            else:
                # Try direct conversion
                cutoff_dt = pd.Timestamp(cutoff_date)
        else:
            cutoff_dt = cutoff_date
            
        # Filter the dataframe
        df = df[df["Date"] <= cutoff_dt]
    
    # Use the complete_year from config if possible
    try:
        from gold import config
        complete_year = getattr(config, 'complete_year', datetime.now().year)
    except (ImportError, AttributeError):
        complete_year = datetime.now().year
        
    # Filter to required years
    start_year = complete_year - years_back
    df = df[df["Date"].dt.year >= start_year]
    
    # Calculate returns based on method
    if return_type == "open-close":
        # Intraday return (open to close)
        df["Return"] = ((df["Close"] - df["Open"]) / df["Open"]) * 100
    else:  # close-close
        # Daily return (close to previous close)
        df["Return"] = df["Close"].pct_change() * 100
    
    # Create date features
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Day"] = df["Date"].dt.day
    df["DayOfYear"] = df["Date"].dt.dayofyear
    
    # For leap years, adjust day of year after Feb 28
    leap_year_adjustment = ((df["Date"].dt.is_leap_year) & 
                           (df["Date"].dt.dayofyear > 59))
    df.loc[leap_year_adjustment, "DayOfYear"] -= 1

    return df

def generate_cumulative_returns(df, years_list=[5, 10, 15]):
    """
    Generate cumulative returns for different year ranges.
    
    Args:
        df: DataFrame with return data
        years_list: List of year ranges to calculate
    
    Returns:
        Dictionary of DataFrames with cumulative returns for each year range
    """
    results = {}
    
    # Use the complete_year from config if possible
    try:
        from gold import config
        complete_year = getattr(config, 'complete_year', datetime.now().year)
    except (ImportError, AttributeError):
        complete_year = datetime.now().year
    
    for years in years_list:
        # Filter data for the specific year range
        year_cutoff = complete_year - years
        year_data = df[df["Year"] >= year_cutoff].copy()
        
        # Calculate the average return for each day of year
        avg_returns = year_data.groupby("DayOfYear")["Return"].mean().reset_index()
        
        # Calculate cumulative return
        avg_returns["CumulativeReturn"] = avg_returns["Return"].cumsum()
        
        # Add to results
        results[f"{years}YR"] = avg_returns
    
    # Add current year data
    current_year_data = df[df["Year"] == complete_year].copy()
    if not current_year_data.empty:
        current_year_data = current_year_data.sort_values("DayOfYear")
        current_year_data["CumulativeReturn"] = current_year_data["Return"].cumsum()
        results["YTD"] = current_year_data
    
    return results

def plot_seasonality(return_data, title="Gold Seasonality"):
    """
    Create a seasonality plot with multiple timeframes.
    
    Args:
        return_data: Dictionary of DataFrames with cumulative returns
        title: Chart title
    
    Returns:
        Plotly figure
    """
    # Create figure
    fig = go.Figure()
    
    # Month positions for markers (mid-month positions)
    month_positions = [15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345]
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    # Set default colors for better visibility
    colors = {
        "5YR": "#1E88E5",  # Blue
        "10YR": "#00C853",  # Green
        "15YR": "#FFC107",  # Gold/yellow
        "YTD": "#E91E63"    # Pink/red
    }
    
    # Track min/max for dynamic y-axis scaling
    all_values = []
    
    # Add data series
    for key, df in return_data.items():
        if key == "YTD":
            name = "Year to Date"
            line_width = 3
        else:
            name = f"{key[:-2]} Year Average"
            line_width = 2
        
        # Collect values for scaling
        all_values.extend(df["CumulativeReturn"].tolist())
            
        fig.add_trace(
            go.Scatter(
                x=df["DayOfYear"],
                y=df["CumulativeReturn"],
                mode="lines",
                name=name,
                line=dict(
                    width=line_width,
                    color=colors.get(key, None)
                )
            )
        )
    
    # Calculate dynamic y-axis range
    if all_values:
        min_val = min(all_values)
        max_val = max(all_values)
        # Ensure there's always at least a 1% range for visibility
        value_range = max(1, max_val - min_val)
        # Add 20% padding to the range
        padding = value_range * 0.2
        ymin = min_val - padding
        ymax = max_val + padding
    else:
        # Default fallback if no data
        ymin, ymax = -1, 1
        
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="Cumulative Return (%)",
        xaxis=dict(
            tickmode="array",
            tickvals=month_positions,
            ticktext=month_names,
            tickangle=0,
            gridcolor="rgba(120, 120, 120, 0.2)",
        ),
        yaxis=dict(
            ticksuffix="%",
            gridcolor="rgba(120, 120, 120, 0.2)",
            zeroline=True,
            zerolinecolor="rgba(120, 120, 120, 0.4)",
            zerolinewidth=1,
            range=[ymin, ymax]  # Set the dynamic range
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=80, b=10)
    )
    
    # Add annotations to highlight important periods
    # Get current y-axis range to position the annotations
    y_range = ymax - ymin
    annotation_y = ymax - (y_range * 0.05)  # Position near the top
    
    # Add month separators (thin vertical lines)
    for month_pos in [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]:
        fig.add_shape(
            type="line",
            x0=month_pos, x1=month_pos,
            y0=ymin, y1=ymax,
            line=dict(color="rgba(150, 150, 150, 0.3)", width=1, dash="dot")
        )
    
    return fig
