"""
Time Matrix analysis module for gold market data.

This module provides functions for mapping high/low timestamps across different timeframes
and visualizing candlestick patterns with various aggregation levels.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime as dt

def prepare_data(df, timeframe="daily"):
    """
    Prepare data for time matrix analysis.
    
    Args:
        df: DataFrame with OHLC data
        timeframe: The timeframe of the data (hourly, daily, weekly, monthly)
    
    Returns:
        Prepared DataFrame with additional indicators
    """
    df = df.copy()
    
    # Ensure Date column is datetime
    df["Date"] = pd.to_datetime(df["Date"])
    
    # Ensure numeric columns
    for col in ["Open", "High", "Low", "Close"]:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(',', '').astype(float)
    
    # Add candle color
    df["Color"] = np.where(df["Close"] >= df["Open"], "green", "red")
    
    # Add day of week, hour information
    df["DayOfWeek"] = df["Date"].dt.dayofweek
    
    # Try to add hour if it exists in the data
    try:
        df["Hour"] = df["Date"].dt.hour
    except:
        pass
    
    # Add month
    df["Month"] = df["Date"].dt.month
    df["Year"] = df["Date"].dt.year
    
    # Add week number
    df["Week"] = df["Date"].dt.isocalendar().week
    
    return df

def create_timestamp_matrix(df, source_timeframe, target_timeframe):
    """
    Create a timestamp matrix showing when highs and lows occur.
    
    Args:
        df: Prepared DataFrame with OHLC data
        source_timeframe: The timeframe to analyze (monthly, weekly, daily)
        target_timeframe: The timeframe to use for mapping (weekly, daily, hourly)
    
    Returns:
        DataFrame with timestamp matrix data
    """
    result_df = df.copy()
    
    # Group by the source timeframe
    if source_timeframe == "monthly":
        groupby_cols = ["Year", "Month"]
    elif source_timeframe == "weekly":
        groupby_cols = ["Year", "Week"]
    elif source_timeframe == "daily":
        groupby_cols = ["Year", "Month", "Date"]
    else:
        raise ValueError(f"Unsupported source timeframe: {source_timeframe}")
    
    # Calculate high and low for each group
    agg_dict = {
        "High": "max",
        "Low": "min"
    }
    
    # Get high and low points
    agg_data = result_df.groupby(groupby_cols).agg(agg_dict).reset_index()
    
    # For each high and low, find when they occurred within the period
    high_timestamps = []
    low_timestamps = []
    
    for _, row in agg_data.iterrows():
        if source_timeframe == "monthly":
            period_data = result_df[(result_df["Year"] == row["Year"]) & 
                                   (result_df["Month"] == row["Month"])]
        elif source_timeframe == "weekly":
            period_data = result_df[(result_df["Year"] == row["Year"]) & 
                                   (result_df["Week"] == row["Week"])]
        elif source_timeframe == "daily":
            period_data = result_df[result_df["Date"].dt.date == row["Date"].date()]
            
        # Find the high timestamp
        high_row = period_data[period_data["High"] == row["High"]].iloc[0]
        low_row = period_data[period_data["Low"] == row["Low"]].iloc[0]
        
        # Extract timestamp information based on target timeframe
        if target_timeframe == "weekly":
            high_timestamp = high_row["DayOfWeek"]
            low_timestamp = low_row["DayOfWeek"]
            high_label = ["Mon", "Tue", "Wed", "Thu", "Fri"][high_timestamp] if high_timestamp < 5 else "Weekend"
            low_label = ["Mon", "Tue", "Wed", "Thu", "Fri"][low_timestamp] if low_timestamp < 5 else "Weekend"
        elif target_timeframe == "daily":
            # Use hours of day divided into segments
            if "Hour" in high_row:
                high_timestamp = high_row["Hour"]
                low_timestamp = low_row["Hour"]
                # Create 8 3-hour segments 
                high_segment = high_timestamp // 3
                low_segment = low_timestamp // 3
                high_label = f"{high_segment*3}-{high_segment*3+3}"
                low_label = f"{low_segment*3}-{low_segment*3+3}"
            else:
                # Fallback if hour not available
                high_timestamp = high_row["DayOfWeek"]
                low_timestamp = low_row["DayOfWeek"]
                high_label = ["Mon", "Tue", "Wed", "Thu", "Fri"][high_timestamp] if high_timestamp < 5 else "Weekend"
                low_label = ["Mon", "Tue", "Wed", "Thu", "Fri"][low_timestamp] if low_timestamp < 5 else "Weekend"
        elif target_timeframe == "hourly":
            if "Hour" in high_row:
                high_timestamp = high_row["Hour"]
                low_timestamp = low_row["Hour"]
                high_label = f"{high_timestamp}:00"
                low_label = f"{low_timestamp}:00"
            else:
                # Fallback 
                high_timestamp = 0
                low_timestamp = 0
                high_label = "N/A"
                low_label = "N/A"
        
        high_timestamps.append({
            "Year": row["Year"],
            "Period": row["Month"] if source_timeframe == "monthly" else row["Week"],
            "Timestamp": high_timestamp,
            "Label": high_label,
            "Price": row["High"],
            "Type": "High"
        })
        
        low_timestamps.append({
            "Year": row["Year"],
            "Period": row["Month"] if source_timeframe == "monthly" else row["Week"],
            "Timestamp": low_timestamp,
            "Label": low_label,
            "Price": row["Low"],
            "Type": "Low"
        })
    
    # Combine high and low data
    result = pd.DataFrame(high_timestamps + low_timestamps)
    
    return result

def plot_time_matrix(timestamp_data, title="Time Matrix Analysis"):
    """
    Plot time matrix visualization.
    
    Args:
        timestamp_data: DataFrame with timestamp matrix data
        title: Plot title
    
    Returns:
        Plotly figure object
    """
    # Create separate dataframes for highs and lows
    highs = timestamp_data[timestamp_data["Type"] == "High"]
    lows = timestamp_data[timestamp_data["Type"] == "Low"]
    
    # Get unique labels ordered correctly
    if "Label" in timestamp_data.columns:
        # For weekdays, use specific order
        if any(label in ["Mon", "Tue", "Wed", "Thu", "Fri"] for label in timestamp_data["Label"]):
            all_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Weekend"]
        # For hours, order numerically
        elif any(":" in label for label in timestamp_data["Label"]):
            all_labels = sorted(timestamp_data["Label"].unique(), 
                              key=lambda x: int(x.split(":")[0]) if ":" in x else 0)
        # For segments, order numerically
        elif any("-" in label for label in timestamp_data["Label"]):
            all_labels = sorted(timestamp_data["Label"].unique(),
                              key=lambda x: int(x.split("-")[0]) if "-" in x else 0)
        else:
            all_labels = sorted(timestamp_data["Label"].unique())
    else:
        all_labels = sorted(timestamp_data["Timestamp"].unique())
    
    # Create figure with two subplots
    fig = make_subplots(rows=2, cols=1, 
                       subplot_titles=["High Timestamps", "Low Timestamps"],
                       shared_xaxes=True,
                       vertical_spacing=0.1)
    
    # Count occurrences for each label
    high_counts = highs["Label"].value_counts().reindex(all_labels).fillna(0)
    low_counts = lows["Label"].value_counts().reindex(all_labels).fillna(0)
    
    # Add bars for highs
    fig.add_trace(
        go.Bar(
            x=high_counts.index,
            y=high_counts.values,
            name="Highs",
            marker_color="#00C853"  # Green
        ),
        row=1, col=1
    )
    
    # Add bars for lows
    fig.add_trace(
        go.Bar(
            x=low_counts.index,
            y=low_counts.values,
            name="Lows",
            marker_color="#E91E63"  # Red/Pink
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title=title,
        height=600,
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=10, r=10, t=80, b=20)
    )
    
    # Update axes
    fig.update_xaxes(title_text="Time Period", row=2, col=1)
    fig.update_yaxes(title_text="Frequency", row=1, col=1)
    fig.update_yaxes(title_text="Frequency", row=2, col=1)
    
    return fig

def plot_scatter_matrix(timestamp_data, scatter_type="day", title="Timestamp Scatter Analysis"):
    """
    Create scatter plots for time matrix analysis.
    
    Args:
        timestamp_data: DataFrame with timestamp data
        scatter_type: Type of scatter plot (day, week, month)
        title: Plot title
    
    Returns:
        Plotly figure object
    """
    # Create figure
    fig = go.Figure()
    
    # Split by high/low
    highs = timestamp_data[timestamp_data["Type"] == "High"]
    lows = timestamp_data[timestamp_data["Type"] == "Low"]
    
    # Create scatter plots
    fig.add_trace(
        go.Scatter(
            x=highs["Period"],
            y=highs["Timestamp"],
            mode="markers",
            name="Highs",
            marker=dict(
                color="#00C853",  # Green
                size=10,
                symbol="circle"
            ),
            hovertemplate="Period: %{x}<br>Time: %{text}<br>Price: %{customdata}",
            text=highs["Label"],
            customdata=highs["Price"]
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=lows["Period"],
            y=lows["Timestamp"],
            mode="markers",
            name="Lows",
            marker=dict(
                color="#E91E63",  # Red/Pink
                size=10,
                symbol="circle-open"
            ),
            hovertemplate="Period: %{x}<br>Time: %{text}<br>Price: %{customdata}",
            text=lows["Label"],
            customdata=lows["Price"]
        )
    )
    
    # Customize based on scatter type
    if scatter_type == "day":
        period_label = "Day"
        time_label = "Hour"
    elif scatter_type == "week":
        period_label = "Week"
        time_label = "Day"
    elif scatter_type == "month":
        period_label = "Month"
        time_label = "Week"
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title=period_label,
        yaxis_title=time_label,
        height=500,
        template="plotly_dark",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=10, r=10, t=80, b=40)
    )
    
    return fig

def create_split_candle_chart(df, title="Split Candles Analysis"):
    """
    Create a candlestick chart separating green and red candles.
    
    Args:
        df: DataFrame with OHLC data and Color column
        title: Chart title
    
    Returns:
        Plotly figure object
    """
    # Create subplots
    fig = make_subplots(rows=2, cols=1, 
                       subplot_titles=["Green Candles", "Red Candles"],
                       shared_xaxes=True, 
                       vertical_spacing=0.05,
                       row_heights=[0.5, 0.5])
    
    # Filter green and red candles
    green_candles = df[df["Color"] == "green"]
    red_candles = df[df["Color"] == "red"]
    
    # Add green candles trace
    fig.add_trace(
        go.Candlestick(
            x=green_candles["Date"],
            open=green_candles["Open"],
            high=green_candles["High"],
            low=green_candles["Low"],
            close=green_candles["Close"],
            increasing_line_color="#00C853",
            decreasing_line_color="#00C853",
            name="Green",
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Add red candles trace
    fig.add_trace(
        go.Candlestick(
            x=red_candles["Date"],
            open=red_candles["Open"],
            high=red_candles["High"],
            low=red_candles["Low"],
            close=red_candles["Close"],
            increasing_line_color="#E91E63",
            decreasing_line_color="#E91E63",
            name="Red",
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
        height=800,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=80, b=20)
    )
    
    # Update Y-axis labels
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Price", row=2, col=1)
    
    return fig
