"""
Volatility Clock implementation for Gold Trading App.
Shows hourly volatility patterns in a 24-hour clock format.
"""
import datetime as dt
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import time
from gold import config
from gold.azure import load_csv
from functools import lru_cache

# Use st.cache_data for faster loading with Streamlit's caching
@st.cache_data(ttl=3600)
def load_hourly_data(start_date, end_date):
    """
    Load hourly data for the volatility clock.
    
    Args:
        start_date: Start date for analysis
        end_date: End date for analysis
        
    Returns:
        DataFrame with hourly data
    """
    try:
        # Ensure dates are datetime.date objects
        if isinstance(start_date, str):
            start_date = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = dt.datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Convert date objects to timestamp strings for filtering
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
            
        # Use the 1h timeframe file
        # Load the hourly data
        start_time = time.time()
        df = load_csv(config.TIMEFRAME_FILES["h1"])
        load_time = time.time() - start_time
        
        if df is None or df.empty:
            return None
        
        # Make sure the DataFrame has the correct columns
        required_cols = ["Date", "Open", "High", "Low", "Close"]
        for col in required_cols:
            if col not in df.columns:
                st.error(f"Required column {col} not found in hourly data.")
                return None
        
        # Convert dates with explicit format to avoid warnings
        start_time = time.time()
        
        # Check if Date column is already datetime type
        if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
            # First try common formats to avoid falling back to slow dateutil
            try:
                # Try ISO format first
                df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    # Try another common format
                    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y %H:%M:%S")
                except ValueError:
                    # Fall back to automatic parsing if needed
                    df["Date"] = pd.to_datetime(df["Date"])
        
        # Filter by date range
        df = df[(df["Date"] >= start_ts) & (df["Date"] <= end_ts)]
        filter_time = time.time() - start_time
        
        if df.empty:
            return None
        
        # Debug timing information
        # st.write(f"Data loaded in {load_time:.2f}s, filtered in {filter_time:.2f}s")
        
        return df
    
    except Exception as e:
        st.error(f"Error loading hourly data: {str(e)}")
        return None

@st.cache_data(ttl=3600)
def calculate_hourly_metrics(df):
    """
    Calculate hourly metrics for gold data including volatility, returns, and probabilities.
    
    Args:
        df: DataFrame with hourly gold data
        
    Returns:
        DataFrame with hourly metrics
    """
    if df is None or df.empty:
        return None
    
    start_time = time.time()
    
    # Convert strings with commas to float - only if needed
    for col in ["Open", "High", "Low", "Close"]:
        if df[col].dtype == object:
            df[col] = df[col].str.replace(',', '').astype(float)
    
    # Extract hour from datetime
    df["Hour"] = df["Date"].dt.hour
    
    # Use vectorized operations for better performance
    # Calculate ATR as high-low
    df["ATR"] = df["High"] - df["Low"]
    
    # Calculate returns (Close to Open) and ensure numeric values
    df["Return"] = ((df["Close"] - df["Open"]) / df["Open"]) * 100
    # Ensure Return column is numeric with no NaN values
    df["Return"] = pd.to_numeric(df["Return"], errors='coerce').fillna(0)
    
    # Calculate win/loss flag (1 for green, 0 for red)
    df["Flag"] = (df["Close"] > df["Open"]).astype(int) * 100  # Multiply by 100 to get percentage
    
    # Calculate statistics by hour - use optimized groupby
    # Define the aggregations as a dictionary for more efficient processing
    agg_dict = {
        "ATR": ["mean", "median", "max", "min", "count"],
        "Return": ["mean"],
        "Flag": ["mean"]
    }
    
    # Apply the aggregations
    hourly_stats = df.groupby("Hour").agg(agg_dict)
    
    # Flatten the multi-index columns
    hourly_stats.columns = [f"{col}_{agg}" for col, agg in hourly_stats.columns]
    
    # Reset index to make Hour a column
    hourly_stats = hourly_stats.reset_index()
    
    # Rename columns for consistency with the rest of the code
    hourly_stats = hourly_stats.rename(columns={
        "ATR_mean": "ATR_Mean",
        "ATR_median": "ATR_Median",
        "ATR_max": "ATR_Max",
        "ATR_min": "ATR_Min",
        "Return_mean": "Avg_Return",  # This is critical for the Avg_Return metric to work
        "Flag_mean": "Green_Prob",
        "ATR_count": "Day_Count"
    })
    
    # Extra check to ensure Avg_Return exists and has proper values
    if "Avg_Return" not in hourly_stats.columns and "Return_mean" in hourly_stats.columns:
        hourly_stats["Avg_Return"] = hourly_stats["Return_mean"]
    
    # Ensure all numeric columns have proper values
    for col in hourly_stats.columns:
        if col != "Hour" and pd.api.types.is_numeric_dtype(hourly_stats[col]):
            hourly_stats[col] = pd.to_numeric(hourly_stats[col], errors='coerce').fillna(0)
    
    # Add Red_Prob as complement of Green_Prob
    hourly_stats["Red_Prob"] = 100 - hourly_stats["Green_Prob"]
    
    # Ensure we have all 24 hours (0-23) - more efficiently with reindex
    all_hours = pd.DataFrame({"Hour": range(24)})
    hourly_stats = pd.merge(all_hours, hourly_stats, on="Hour", how="left").fillna(0)
    
    calc_time = time.time() - start_time
    # st.write(f"Metrics calculated in {calc_time:.2f}s")
    
    return hourly_stats

def get_top_hours(hourly_stats, metric="ATR_Mean", top_n=5, largest=True):
    """
    Get the top N hours based on the selected metric.
    
    Args:
        hourly_stats: DataFrame with hourly metrics
        metric: Metric to sort by (ATR_Mean, Avg_Return, Green_Prob, Red_Prob)
        top_n: Number of hours to return
        largest: If True, return highest values, otherwise lowest values
        
    Returns:
        List of hour indices (0-23)
    """
    if hourly_stats is None or hourly_stats.empty:
        return []
    
    sorted_hours = hourly_stats.sort_values(metric, ascending=not largest)
    return sorted_hours.head(top_n)["Hour"].tolist()

def render_volatility_clock(start_date, end_date, metric="ATR_Mean", filter_option="all"):
    """
    Render the volatility clock visualization with the selected metric.
    
    Args:
        start_date: Start date for analysis
        end_date: End date for analysis
        metric: Metric to display (ATR_Mean, Avg_Return, Green_Prob)
        filter_option: 'all', 'top5', or 'bottom5'
        
    Returns:
        Plotly figure object
    """
    # Load data and calculate metrics
    df = load_hourly_data(start_date, end_date)
    
    if df is None or df.empty:
        st.warning("No hourly data available for the selected date range.")
        return None
    
    hourly_stats = calculate_hourly_metrics(df)
    
    # Get top/bottom hours based on the selected metric
    highlight_hours = []
    if filter_option == "top5":
        highlight_hours = get_top_hours(hourly_stats, metric=metric, top_n=5, largest=True)
    elif filter_option == "bottom5":
        highlight_hours = get_top_hours(hourly_stats, metric=metric, top_n=5, largest=False)
    
    # Prepare data for visualization
    if filter_option != "all" and highlight_hours:
        plot_data = hourly_stats[hourly_stats["Hour"].isin(highlight_hours)]
    else:
        plot_data = hourly_stats
    
    # Verify all metrics exist in the dataframe and silently fallback if needed
    available_metrics = list(hourly_stats.columns)
    if metric not in available_metrics:
        # Metric not found, fallback to ATR_Mean
        metric = "ATR_Mean"  # Fallback to a metric we know exists
    
    # Configure visualization based on metric
    # First, determine which internal metric to use based on what was selected
    display_metric = metric  # What to show in the UI
    data_metric = metric     # Which column to use for data
    
    # If the metric from the UI is a display name, map it to our internal name
    if metric == "ATR" or metric == "ATR (points)":
        data_metric = "ATR_Mean"
    elif metric == "Avg Return" or metric == "Average Return":
        data_metric = "Avg_Return"
    elif metric == "Probability" or metric == "Win Probability":
        data_metric = "Green_Prob"
    
    # Now set the chart properties based on the mapped metric
    if data_metric == "ATR_Mean" or metric == "ATR_Mean":
        y_title = "ATR (points)"
        hover_format = "Avg ATR: %{y:.2f} points<br>"
        chart_title = f"Hourly Volatility (ATR): {start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
        # Create color mapping based on ATR values
        q = hourly_stats[data_metric].quantile([0, .33, .66, 1]).values
        plot_data["color"] = plot_data[data_metric].apply(
            lambda v: "Low" if v <= q[1] else "Medium" if v <= q[2] else "High"
        )
        color_map = {"Low": "green", "Medium": "orange", "High": "red"}
    elif data_metric == "Avg_Return" or metric == "Avg_Return":
        y_title = "Average Return (%)"
        hover_format = "Avg Return: %{y:.2f}%<br>"
        chart_title = f"Hourly Average Returns: {start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
        # Color based on positive/negative returns
        plot_data["color"] = plot_data[data_metric].apply(
            lambda v: "Positive" if v > 0 else "Negative"
        )
        color_map = {"Positive": "green", "Negative": "red"}
    elif data_metric == "Green_Prob" or metric == "Green_Prob":
        y_title = "Probability (%)"
        hover_format = "Green Probability: %{y:.1f}%<br>"
        chart_title = f"Hourly Win Probability: {start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
        # Create color gradient based on probability
        q = hourly_stats[data_metric].quantile([0, .33, .66, 1]).values
        plot_data["color"] = plot_data[data_metric].apply(
            lambda v: "Low" if v <= q[1] else "Medium" if v <= q[2] else "High"
        )
        # Use a more distinct color scheme for probability
        color_map = {"Low": "red", "Medium": "#fca103", "High": "green"}

    # Verify that the data_metric is in the data and fix if needed (silently)
    if data_metric not in plot_data.columns:
        # If Avg_Return is not found but Return_mean is available, use it
        if data_metric == "Avg_Return" and "Return_mean" in plot_data.columns:
            plot_data["Avg_Return"] = plot_data["Return_mean"]
        # If we still don't have the metric, fallback to ATR_Mean
        elif "ATR_Mean" in plot_data.columns:
            data_metric = "ATR_Mean"
    
    # Make sure all numeric columns are properly formatted
    for col in plot_data.columns:
        if col != "Hour" and col != "color" and pd.api.types.is_numeric_dtype(plot_data[col]):
            # Convert to numeric and handle NaN values
            plot_data[col] = pd.to_numeric(plot_data[col], errors='coerce').fillna(0)
    
    # Create the visualization
    fig = px.bar(
        plot_data, 
        x="Hour", 
        y=data_metric,  # Use data_metric for the actual data column
        color="color",
        color_discrete_map=color_map,
        labels={
            "Hour": "Hour of Day (ET)",
            data_metric: y_title  # Map the internal column name to the display title
        },
        title=chart_title,  # Use chart_title which was set earlier based on the metric
        height=500
    )
    
    # Create AM/PM hour labels
    hour_labels = [f"{h%12 or 12} {'AM' if h<12 else 'PM'}" for h in range(24)]
    
    # Update layout for better appearance
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=list(range(24)),
            ticktext=hour_labels,
            tickangle=45
        ),
        plot_bgcolor="rgba(0,0,0,0.05)",
        yaxis_title=y_title,
        xaxis_title="Hour (ET)",
    )
    
    # Add trading session background zones with bolder colors and clearer borders
    # Asia session (approximately 7 PM ET to 2 AM ET)
    asia_color = "rgba(135, 206, 250, 0.3)"  # Bolder light blue
    london_color = "rgba(152, 251, 152, 0.3)"  # Bolder light green
    ny_color = "rgba(255, 182, 193, 0.3)"  # Bolder light pink
    
    # Create session shapes with borders
    # Asia session (7 PM to 2 AM ET)
    fig.add_vrect(
        x0=19, x1=24,  # 7 PM to midnight
        fillcolor=asia_color,
        line_width=1,
        line_color="rgba(135, 206, 250, 0.8)",
        layer="below",
    )
    fig.add_vrect(
        x0=0, x1=2,  # midnight to 2 AM
        fillcolor=asia_color,
        line_width=1,
        line_color="rgba(135, 206, 250, 0.8)",
        layer="below",
    )
    
    # London session (3 AM ET to 11 AM ET)
    fig.add_vrect(
        x0=3, x1=11,
        fillcolor=london_color,
        line_width=1,
        line_color="rgba(152, 251, 152, 0.8)",
        layer="below",
    )
    
    # NY session (8 AM ET to 5 PM ET)
    fig.add_vrect(
        x0=8, x1=17,
        fillcolor=ny_color,
        line_width=1,
        line_color="rgba(255, 182, 193, 0.8)",
        layer="below",
    )
    
    # Create custom shapes for session labels that work well in both light and dark modes
    # Add trading session names directly on the chart as rectangular shapes with text
    # Asia Session label (centered at the top)
    fig.add_shape(
        type="rect",
        x0=19, x1=24,
        y0=0.87, y1=0.97,
        xref="x", yref="paper",
        fillcolor="rgba(50, 100, 255, 0.2)",
        line=dict(color="rgba(50, 100, 255, 0.7)", width=2),
        layer="above"
    )
    
    fig.add_annotation(
        x=21.5,
        y=0.92,
        text="ASIA",
        showarrow=False,
        font=dict(size=10, color="white", family="Arial Black"),
        xref="x", yref="paper",
        bgcolor="rgba(0, 0, 0, 0)",  # Transparent background
    )
    
    # Asia Session early hours
    fig.add_shape(
        type="rect",
        x0=0, x1=2,
        y0=0.87, y1=0.97,
        xref="x", yref="paper",
        fillcolor="rgba(50, 100, 255, 0.2)",
        line=dict(color="rgba(50, 100, 255, 0.7)", width=2),
        layer="above"
    )
    
    # London Session label
    fig.add_shape(
        type="rect",
        x0=3, x1=11,
        y0=0.87, y1=0.97,
        xref="x", yref="paper",
        fillcolor="rgba(50, 200, 50, 0.2)",
        line=dict(color="rgba(50, 200, 50, 0.7)", width=2),
        layer="above"
    )
    
    fig.add_annotation(
        x=7,
        y=0.92,
        text="LONDON",
        showarrow=False,
        font=dict(size=10, color="white", family="Arial Black"),
        xref="x", yref="paper",
        bgcolor="rgba(0, 0, 0, 0)",  # Transparent background
    )
    
    # New York Session label
    fig.add_shape(
        type="rect",
        x0=8, x1=17,
        y0=0.87, y1=0.97,
        xref="x", yref="paper",
        fillcolor="rgba(255, 50, 100, 0.2)",
        line=dict(color="rgba(255, 50, 100, 0.7)", width=2),
        layer="above"
    )
    
    fig.add_annotation(
        x=12.5,
        y=0.92,
        text="NEW YORK",
        showarrow=False,
        font=dict(size=10, color="white", family="Arial Black"),
        xref="x", yref="paper",
        bgcolor="rgba(0, 0, 0, 0)",  # Transparent background
    )
    
    # Add a legend to the chart itself instead of below it
    # Create a shape for the legend box in the top right corner
    fig.add_shape(
        type="rect",
        x0=0.72, x1=0.98,  # Positioned near the right side of the chart
        y0=0.02, y1=0.18,  # Positioned near the bottom of the chart
        xref="paper", yref="paper",
        fillcolor="rgba(0, 0, 0, 0.6)",  # Semi-transparent black for better contrast in any mode
        line=dict(color="rgba(255, 255, 255, 0.7)", width=1),
        layer="above"
    )
    
    # Add title for the legend
    fig.add_annotation(
        x=0.85,
        y=0.15,
        text="<b>TRADING SESSIONS</b>",
        showarrow=False,
        font=dict(size=9, color="white"),
        xref="paper", yref="paper",
        align="center",
    )
    
    # Add legend entries
    asia_color = "rgba(50, 100, 255, 1.0)"  # Bright blue
    london_color = "rgba(50, 200, 50, 1.0)"  # Bright green
    ny_color = "rgba(255, 50, 100, 1.0)"  # Bright pink
    
    # Asia Session entry
    fig.add_annotation(
        x=0.75,
        y=0.11,
        text="<span style='color:" + asia_color + "'>■</span> Asia (7PM-2AM)",
        showarrow=False,
        font=dict(size=8, color="white"),
        xref="paper", yref="paper",
        align="left",
    )
    
    # London Session entry
    fig.add_annotation(
        x=0.75,
        y=0.07,
        text="<span style='color:" + london_color + "'>■</span> London (3AM-11AM)",
        showarrow=False,
        font=dict(size=8, color="white"),
        xref="paper", yref="paper",
        align="left",
    )
    
    # New York Session entry
    fig.add_annotation(
        x=0.75,
        y=0.03,
        text="<span style='color:" + ny_color + "'>■</span> New York (8AM-5PM)",
        showarrow=False,
        font=dict(size=8, color="white"),
        xref="paper", yref="paper",
        align="left",
    )
    
    # Add hover information
    fig.update_traces(
        hovertemplate="<b>Hour: %{x}:00 ET</b><br>" +
                      hover_format +
                      "Sample size: %{customdata[0]} days<extra></extra>",
        customdata=plot_data[["Day_Count"]]
    )
    
    # Add markers for top 5 hours if all hours are shown
    if filter_option == "all":
        top_hours = get_top_hours(hourly_stats, metric=metric, top_n=5, largest=True)
        for hour in top_hours:
            if hour in hourly_stats["Hour"].values:
                row = hourly_stats[hourly_stats["Hour"] == hour].iloc[0]
                fig.add_annotation(
                    x=hour,
                    y=row[metric],
                    text="★",
                    showarrow=False,
                    font=dict(size=20, color="black"),
                    yshift=10
                )
    
    return fig

def volatility_clock_ui(metric="ATR_Mean"):
    """
    Create the UI for the volatility clock feature.
    
    Args:
        metric: Default metric to display
        
    Returns:
        start_date, end_date, metric, and filter_option
    """
    st.markdown("## Hourly Analysis by Time of Day")
    st.markdown("""
    Analyze gold's hourly patterns across a 24-hour cycle.
    See which hours of the day have specific characteristics based on the selected metric.
    """)
    
    # Set the cutoff date to March 17, 2025
    h1_cutoff_date = dt.date(2025, 3, 17)
    
    # Date range selection
    st.sidebar.markdown("### Date Range Selection")
    
    # Get today's date for creating descriptive preset options
    today = dt.date.today() 
    yesterday = today - dt.timedelta(days=1)
    three_days_ago = today - dt.timedelta(days=3)
    week_ago = today - dt.timedelta(days=7)
    two_weeks_ago = today - dt.timedelta(days=14)
    thirty_days_ago = today - dt.timedelta(days=30)
    ninety_days_ago = today - dt.timedelta(days=90)
    six_months_ago = today - dt.timedelta(days=180)
    one_year_ago = today - dt.timedelta(days=365)
    
    # Format dates for display
    date_format = "%b %d, %Y"  # Example: May 09, 2025
    
    # Expanded preset date ranges with more options and actual date ranges
    preset_options = [
        f"Today ({today.strftime(date_format)})",
        f"Yesterday ({yesterday.strftime(date_format)})", 
        f"Last 3 Days ({three_days_ago.strftime(date_format)} - {today.strftime(date_format)})",
        f"Last Week ({week_ago.strftime(date_format)} - {today.strftime(date_format)})",
        f"Last 2 Weeks ({two_weeks_ago.strftime(date_format)} - {today.strftime(date_format)})",
        f"Last 30 Days ({thirty_days_ago.strftime(date_format)} - {today.strftime(date_format)})",
        f"Last 90 Days ({ninety_days_ago.strftime(date_format)} - {today.strftime(date_format)})",
        f"Last 6 Months ({six_months_ago.strftime(date_format)} - {today.strftime(date_format)})",
        f"Last 1 Year ({one_year_ago.strftime(date_format)} - {today.strftime(date_format)})",
        "Custom Range"
    ]
    
    # Create a mapping of display options to internal values for processing
    preset_mapping = {
        preset_options[0]: "Today",
        preset_options[1]: "Yesterday",
        preset_options[2]: "Last 3 Days",
        preset_options[3]: "Last Week",
        preset_options[4]: "Last 2 Weeks",
        preset_options[5]: "Last 30 Days",
        preset_options[6]: "Last 90 Days",
        preset_options[7]: "Last 6 Months",
        preset_options[8]: "Last 1 Year",
        preset_options[9]: "Custom Range"
    }
    
    selected_preset_display = st.sidebar.selectbox(
        "Select date range:",
        options=preset_options,
        index=4  # Default to Last 2 Weeks
    )
    
    # Get the internal value for the selected preset
    preset = preset_mapping[selected_preset_display]
    
    # Process the selected preset
    if preset == "Today":
        start_date = h1_cutoff_date
        end_date = h1_cutoff_date
    elif preset == "Yesterday":
        start_date = h1_cutoff_date - dt.timedelta(days=1)
        end_date = h1_cutoff_date - dt.timedelta(days=1)
    elif preset == "Last 3 Days":
        start_date = h1_cutoff_date - dt.timedelta(days=3)
        end_date = h1_cutoff_date
    elif preset == "Last Week":
        start_date = h1_cutoff_date - dt.timedelta(days=7)
        end_date = h1_cutoff_date
    elif preset == "Last 2 Weeks":
        start_date = h1_cutoff_date - dt.timedelta(days=14)
        end_date = h1_cutoff_date
    elif preset == "Last 30 Days":
        start_date = h1_cutoff_date - dt.timedelta(days=30)
        end_date = h1_cutoff_date
    elif preset == "Last 90 Days":
        start_date = h1_cutoff_date - dt.timedelta(days=90)
        end_date = h1_cutoff_date
    elif preset == "Last 6 Months":
        start_date = h1_cutoff_date - dt.timedelta(days=180)
        end_date = h1_cutoff_date
    elif preset == "Last 1 Year":
        start_date = h1_cutoff_date - dt.timedelta(days=365)
        end_date = h1_cutoff_date
    else:  # Custom Range
        st.sidebar.markdown("""<div style='background-color:rgba(0,0,0,0.05); padding:15px; border-radius:5px; margin-bottom:15px;'>
                          <p style='margin:0; font-weight:bold;'>📅 Custom Date Range</p>
                          </div>""", unsafe_allow_html=True)
        
        # Start date selection with separate year, month, day controls
        st.sidebar.markdown("#### Start Date")
        
        # Get default values (90 days ago)
        default_start = h1_cutoff_date - dt.timedelta(days=90)
        
        # Create three columns for year, month, day selection for start date
        s_year_col, s_month_col, s_day_col = st.sidebar.columns(3)
        
        # Years dropdown (limited to reasonable range for data)
        available_years = list(range(2000, h1_cutoff_date.year + 1))
        with s_year_col:
            start_year = st.selectbox(
                "Year",
                available_years,
                index=available_years.index(default_start.year) if default_start.year in available_years else len(available_years)-1,
                key="start_year"
            )
        
        # Months dropdown
        months = [(1, "Jan"), (2, "Feb"), (3, "Mar"), (4, "Apr"), (5, "May"), (6, "Jun"), 
                 (7, "Jul"), (8, "Aug"), (9, "Sep"), (10, "Oct"), (11, "Nov"), (12, "Dec")]
        with s_month_col:
            start_month = st.selectbox(
                "Month",
                options=[m[0] for m in months],
                format_func=lambda x: months[x-1][1],
                index=default_start.month-1,
                key="start_month"
            )
        
        # Days dropdown (adjusts based on month)
        max_day = 31  # Default
        if start_month in [4, 6, 9, 11]:
            max_day = 30
        elif start_month == 2:
            # Check for leap year
            if (start_year % 4 == 0 and start_year % 100 != 0) or (start_year % 400 == 0):
                max_day = 29
            else:
                max_day = 28
        
        with s_day_col:
            start_day = st.selectbox(
                "Day",
                range(1, max_day + 1),
                index=min(default_start.day - 1, max_day - 1),
                key="start_day"
            )
        
        # Combine selected values into a date object
        start_date = dt.date(start_year, start_month, start_day)
        
        # End date selection
        st.sidebar.markdown("#### End Date")
        
        # Create three columns for year, month, day selection for end date
        e_year_col, e_month_col, e_day_col = st.sidebar.columns(3)
        
        with e_year_col:
            end_year = st.selectbox(
                "Year",
                available_years,
                index=available_years.index(h1_cutoff_date.year) if h1_cutoff_date.year in available_years else len(available_years)-1,
                key="end_year"
            )
        
        with e_month_col:
            end_month = st.selectbox(
                "Month",
                options=[m[0] for m in months],
                format_func=lambda x: months[x-1][1],
                index=h1_cutoff_date.month-1,
                key="end_month"
            )
        
        # Days dropdown for end date
        max_day = 31  # Default
        if end_month in [4, 6, 9, 11]:
            max_day = 30
        elif end_month == 2:
            # Check for leap year
            if (end_year % 4 == 0 and end_year % 100 != 0) or (end_year % 400 == 0):
                max_day = 29
            else:
                max_day = 28
        
        with e_day_col:
            end_day = st.selectbox(
                "Day",
                range(1, max_day + 1),
                index=min(h1_cutoff_date.day - 1, max_day - 1),
                key="end_day"
            )
        
        # Combine selected values into a date object
        end_date = dt.date(end_year, end_month, end_day)
        
        # Ensure end_date is not before start_date
        if end_date < start_date:
            st.sidebar.warning("End date cannot be before start date. Adjusting to start date.")
            end_date = start_date
    
    # Display selected range info
    days_in_range = (end_date - start_date).days
    st.sidebar.info(f"Selected period: {days_in_range} days")
    
    # Use the provided metric from the main UI
    metric_key = metric
    
    # Filtering options
    st.sidebar.markdown("### Display Options")
    
    # Adjust filter labels based on selected metric
    if metric_key == "ATR_Mean":
        filter_labels = ["Show All Hours", "Top 5 Most Volatile", "Top 5 Least Volatile"]
    elif metric_key == "Avg_Return":
        filter_labels = ["Show All Hours", "Top 5 Highest Returns", "Top 5 Lowest Returns"]
    else:  # Green_Prob
        filter_labels = ["Show All Hours", "Top 5 Highest Probability", "Top 5 Lowest Probability"]
    
    filter_option = st.sidebar.radio(
        f"Filter Hours ({metric_key.replace('_', ' ')})",
        filter_labels,
        index=0
    )
    
    # Convert filter option to internal code
    if filter_option.startswith("Top 5 Most") or filter_option.startswith("Top 5 Highest"):
        filter_code = "top5"
    elif filter_option.startswith("Top 5 Least") or filter_option.startswith("Top 5 Lowest"):
        filter_code = "bottom5"
    else:
        filter_code = "all"
    
    return start_date, end_date, metric_key, filter_code

def display_volatility_clock(default_metric="ATR_Mean"):
    """Main function to display the volatility clock analysis
    
    Args:
        default_metric: Default metric to display (passed from main app)
    """
    # Force correct mapping of display names to internal metrics
    if default_metric == "Average Return" or default_metric == "Avg Return":  
        default_metric = "Avg_Return"
    elif default_metric == "ATR" or default_metric == "ATR (points)":  
        default_metric = "ATR_Mean"
    elif default_metric == "Probability" or default_metric == "Win Probability":  
        default_metric = "Green_Prob"
    
    # Ensure the default metric is one of our supported ones
    valid_metrics = ["ATR_Mean", "Avg_Return", "Green_Prob"]
    if default_metric not in valid_metrics:
        default_metric = "ATR_Mean"
            
    # Get UI selections with our verified metric
    start_date, end_date, metric, filter_option = volatility_clock_ui(default_metric)
    
    # Set spinner text based on the selected metric
    if metric == "ATR_Mean":
        spinner_text = "Calculating hourly volatility patterns..."
    elif metric == "Avg_Return":
        spinner_text = "Calculating hourly return patterns..."
    elif metric == "Green_Prob":
        spinner_text = "Calculating hourly probability patterns..."
    else:
        spinner_text = "Calculating hourly patterns..."
    
    # Render the visualization with the metric from the main app
    with st.spinner(spinner_text):
        fig = render_volatility_clock(start_date, end_date, metric, filter_option)
    
    if fig:
        st.plotly_chart(fig, use_container_width=True)
        
        # Additional insights section with better styling
        insights_title = "Hourly Insights"
        if metric == "ATR_Mean":
            insights_title = "Volatility Insights"
            insight_color = "#e63946"  # Red for volatility
        elif metric == "Avg_Return":
            insights_title = "Return Insights"
            insight_color = "#2a9d8f"  # Green-blue for returns
        elif metric == "Green_Prob":
            insights_title = "Probability Insights"
            insight_color = "#4361ee"  # Blue for probability
        
        # Create a styled header with a colored banner
        st.markdown(f"""
        <div style="background-color:{insight_color}; padding: 10px; border-radius: 10px; margin-top: 20px;">
            <h3 style="color:white; margin:0;">{insights_title}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Load data for insights
        df = load_hourly_data(start_date, end_date)
        if df is not None and not df.empty:
            hourly_stats = calculate_hourly_metrics(df)
            
            # Add a brief description of what the insights mean
            if metric == "ATR_Mean":
                st.markdown("""<div style='margin-top:10px; margin-bottom:20px;'>
                Discover which hours of the day typically exhibit the highest and lowest volatility, 
                measured as the average range between high and low prices during each hour.
                </div>""", unsafe_allow_html=True)
            elif metric == "Avg_Return":
                st.markdown("""<div style='margin-top:10px; margin-bottom:20px;'>
                See which hours typically generate the best and worst returns, indicating when 
                price movements tend to be most favorable or unfavorable.
                </div>""", unsafe_allow_html=True)
            elif metric == "Green_Prob":
                st.markdown("""<div style='margin-top:10px; margin-bottom:20px;'>
                Explore which hours have the highest and lowest probability of closing higher than they opened, 
                showing when gold tends to rise or fall.
                </div>""", unsafe_allow_html=True)
            
            # Create a more visually appealing container for the insights
            st.markdown("""<div style='background-color:rgba(0,0,0,0.05); padding:20px; border-radius:10px;'>""", unsafe_allow_html=True)
            
            # Show insights in columns
            col1, col2 = st.columns(2)
            
            # Adjust column titles based on metric
            if metric == "ATR_Mean":
                col1_title = "Most Volatile Hours"
                col2_title = "Least Volatile Hours"
                value_format = "{:.2f} points"
                icon1 = "🔥"  # Fire for high volatility
                icon2 = "❄️"  # Snowflake for low volatility
            elif metric == "Avg_Return":
                col1_title = "Best Performing Hours"
                col2_title = "Worst Performing Hours"
                value_format = "{:.2f}%"
                icon1 = "📈"  # Chart up for best performance
                icon2 = "📉"  # Chart down for worst performance
            elif metric == "Green_Prob":
                col1_title = "Highest Probability Hours"
                col2_title = "Lowest Probability Hours"
                value_format = "{:.1f}%"
                icon1 = "🎯"  # Target for high probability
                icon2 = "🎲"  # Dice for low probability
            
            with col1:
                st.markdown(f"#### {icon1} {col1_title}")
                top_hours = get_top_hours(hourly_stats, metric=metric, top_n=5, largest=True)
                top_data = hourly_stats[hourly_stats["Hour"].isin(top_hours)].sort_values(metric, ascending=False)
                
                # Create a more visually appealing list
                for i, (_, row) in enumerate(top_data.iterrows()):
                    hour_text = f"{int(row['Hour']):02d}:00 ET"
                    value_text = value_format.format(row[metric])
                    # Format each entry with number, colored hour, value and sample size
                    st.markdown(f"""<div style='display:flex; align-items:center; margin-bottom:10px;'>
                        <div style='background-color:{insight_color}; color:white; border-radius:50%; width:25px; height:25px; 
                             display:flex; align-items:center; justify-content:center; margin-right:10px;'>{i+1}</div>
                        <div><strong style='font-size:16px;'>{hour_text}</strong> &nbsp; 
                             <span style='color:{insight_color}; font-weight:bold;'>{value_text}</span> 
                             <span style='color:gray; font-size:12px;'>(from {int(row['Day_Count'])} days)</span></div>
                    </div>""", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"#### {icon2} {col2_title}")
                bottom_hours = get_top_hours(hourly_stats, metric=metric, top_n=5, largest=False)
                bottom_data = hourly_stats[hourly_stats["Hour"].isin(bottom_hours)].sort_values(metric)
                
                # Create a more visually appealing list
                for i, (_, row) in enumerate(bottom_data.iterrows()):
                    hour_text = f"{int(row['Hour']):02d}:00 ET"
                    value_text = value_format.format(row[metric])
                    # Format each entry with number, colored hour, value and sample size
                    st.markdown(f"""<div style='display:flex; align-items:center; margin-bottom:10px;'>
                        <div style='background-color:{insight_color}; color:white; border-radius:50%; width:25px; height:25px; 
                             display:flex; align-items:center; justify-content:center; margin-right:10px;'>{i+1}</div>
                        <div><strong style='font-size:16px;'>{hour_text}</strong> &nbsp; 
                             <span style='color:{insight_color}; font-weight:bold;'>{value_text}</span> 
                             <span style='color:gray; font-size:12px;'>(from {int(row['Day_Count'])} days)</span></div>
                    </div>""", unsafe_allow_html=True)
            
            # Close the container div
            st.markdown("""</div>""", unsafe_allow_html=True)
            
            # Add correlation analysis for conditional relationships with better styling
            st.markdown(f"""
            <div style="background-color:{insight_color}; padding: 10px; border-radius: 10px; margin-top: 30px; margin-bottom: 15px;">
                <h3 style="color:white; margin:0;">Conditional Relationships</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Add an explanatory box with an icon for the correlation analysis
            st.markdown(f"""
            <div style="background-color:rgba(0,0,0,0.05); padding:15px; border-radius:10px; margin-bottom:20px;">
                <p style="margin:0;"><span style="font-size:20px;">⚡</span> <strong>What this shows:</strong> This analysis reveals hidden connections between different hours of the day.</p>
                <p style="margin-top:10px;">When one hour behaves in a certain way, another hour may show the opposite pattern. These relationships can help identify predictable market behavior cycles.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Ensure all columns needed for correlation analysis exist
            try:
                # Recalculate basic metrics if they don't already exist in the dataframe
                if "ATR" not in df.columns:
                    df["ATR"] = df["High"] - df["Low"]
                
                if "Return" not in df.columns:
                    df["Return"] = ((df["Close"] - df["Open"]) / df["Open"]) * 100
                
                if "Flag" not in df.columns:
                    df["Flag"] = (df["Close"] > df["Open"]).astype(int) * 100
                
                # Extract hour from datetime if needed
                if "Hour" not in df.columns:
                    df["Hour"] = df["Date"].dt.hour
                
                # Determine which column to use for correlation
                if metric == "ATR_Mean":
                    pivot_col = "ATR" 
                elif metric == "Avg_Return":
                    pivot_col = "Return"
                elif metric == "Green_Prob":
                    pivot_col = "Flag"
                else:
                    pivot_col = "ATR"  # Default fallback
                
                # Calculate correlation matrix for selected metric by hour
                hour_corr = pd.pivot_table(
                    df, 
                    values=pivot_col, 
                    index=df['Date'].dt.date, 
                    columns='Hour', 
                    aggfunc='mean'
                ).corr()
            except Exception as e:
                st.warning(f"Unable to calculate hour correlations: {str(e)}")
                hour_corr = None
            
            # Only process correlations if we have valid data
            if hour_corr is not None:
                # Find strongest negative correlations (inverse relationships)
                corr_threshold = -0.3  # Adjust as needed
                strong_neg_corr = []
                
                try:
                    for h1 in range(24):
                        for h2 in range(24):
                            if h1 != h2 and h1 in hour_corr.columns and h2 in hour_corr.columns:
                                corr_val = hour_corr.loc[h1, h2]
                                if corr_val < corr_threshold:
                                    strong_neg_corr.append((h1, h2, corr_val))
                    
                    # Show strongest negative correlations (inverse relationships) with better styling
                    if strong_neg_corr:
                        # Create a visually appealing container
                        st.markdown("""<div style='background-color:rgba(0,0,0,0.05); padding:20px; border-radius:10px;'>""", unsafe_allow_html=True)
                        
                        # Sort by correlation strength (most negative first)
                        strong_neg_corr.sort(key=lambda x: x[2])
                        
                        # Add a title based on what we're showing
                        if metric == "ATR_Mean":
                            relationship_title = "Top Volatility Relationships"
                        elif metric == "Avg_Return":
                            relationship_title = "Top Return Relationships"
                        elif metric == "Green_Prob":
                            relationship_title = "Top Probability Relationships"
                        else:
                            relationship_title = "Top Relationships"
                            
                        st.markdown(f"<h4 style='margin-top:0;'>{relationship_title}</h4>", unsafe_allow_html=True)
                        
                        # Create formatted cards for each relationship
                        for i, (h1, h2, corr) in enumerate(strong_neg_corr[:5]):
                            # Format the correlation text based on the metric
                            if metric == "ATR_Mean":
                                relationship_text = f"When **{h1:02d}:00 ET** is less volatile, **{h2:02d}:00 ET** tends to be more volatile"
                            elif metric == "Avg_Return":
                                relationship_text = f"When **{h1:02d}:00 ET** has lower returns, **{h2:02d}:00 ET** tends to have higher returns"
                            elif metric == "Green_Prob":
                                relationship_text = f"When **{h1:02d}:00 ET** has a lower probability of green, **{h2:02d}:00 ET** tends to have a higher probability"
                            
                            # Calculate the strength percentage (0 to -1 scale, converted to 0-100%)
                            strength_pct = min(100, int(abs(corr) * 100))
                            
                            # Create a card with relationship info and a progress bar
                            st.markdown(f"""
                            <div style='display:flex; align-items:center; margin-bottom:15px;'>
                                <div style='background-color:{insight_color}; color:white; border-radius:50%; width:25px; height:25px; 
                                     display:flex; align-items:center; justify-content:center; margin-right:10px;'>{i+1}</div>
                                <div style='flex-grow:1;'>
                                    <div>{relationship_text}</div>
                                    <div style='display:flex; align-items:center; margin-top:5px;'>
                                        <div style='width:100px; font-size:12px; color:gray;'>Strength: {strength_pct}%</div>
                                        <div style='flex-grow:1; background-color:rgba(0,0,0,0.1); height:8px; border-radius:4px;'>
                                            <div style='width:{strength_pct}%; background-color:{insight_color}; height:8px; border-radius:4px;'></div>
                                        </div>
                                        <div style='width:80px; font-size:12px; color:gray; text-align:right;'>corr: {corr:.2f}</div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        st.markdown("""</div>""", unsafe_allow_html=True)
                    else:
                        st.info("No significant inverse relationships found in the selected date range.")
                        
                        # Offer some reasons why no relationships were found
                        st.markdown("""
                        <div style='font-size:12px; color:gray; margin-top:10px;'>
                        This could be due to:
                        <ul>
                            <li>Too short of a date range</li>
                            <li>Unusual market conditions during this period</li>
                            <li>Insufficient data for statistical significance</li>
                        </ul>
                        Try selecting a different date range or metric.
                        </div>
                        """, unsafe_allow_html=True)
                except Exception as e:
                    st.warning(f"Error analyzing correlations: {str(e)}")
            else:
                st.markdown("Correlation analysis not available for the selected date range.")
                
            # Add a note about what the correlation means
            st.caption("Note: Correlations below -0.3 indicate potential inverse relationships between hours. The stronger the negative correlation, the more reliable the pattern.")

