"""
Composite Average visualization for Gold Trading App.
This module implements the dedicated composite average view that shows
all timeframes for a profile with the same metric.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime as dt

from gold.composite_avg import (
    calculate_composite_average, 
    get_composite_periods, 
    get_composite_description
)
from gold.profile_utils import create_ordered_profile_df

def render_composite_averages(profile_df, profile_key, metric, x_column, start_date, end_date):
    """
    Render the composite averages for all timeframes of a single profile.
    
    Args:
        profile_df: DataFrame with profile data
        profile_key: The profile type (month, day_of_week, etc.)
        metric: The metric to display (Average Return, ATR points, etc.)
        x_column: The column to use for the x-axis
        start_date: The start date of the data
        end_date: The end date of the data
    """
    # Header with profile information
    profile_name = profile_key.replace('_', ' ').title()
    st.header(f"Composite Averages: {profile_name}")
    
    # Add date range information
    date_format = "%b %d, %Y"
    date_range_text = f"Data from {start_date.strftime(date_format)} to {end_date.strftime(date_format)}"
    st.markdown(f"<p style='color: gray;'>{date_range_text}</p>", unsafe_allow_html=True)
    
    # Informational box explaining composite averages
    with st.expander("ℹ️ About Composite Averages", expanded=False):
        st.markdown("""
        A **composite average** is the average value of a metric at the same point within a repeating time cycle, 
        calculated across multiple instances of that cycle.
        
        For example, for a monthly profile, the "Short-term Avg" shows the average performance of each month
        over the past 3 years, while the "Long-term Avg" shows the average over 10 years.
        
        This helps identify which patterns are consistent across different timeframes and which might be
        more recent phenomena.
        """)
    
    # Get composite periods for this profile
    periods = get_composite_periods(profile_key)
    
    # Show one visualization per composite period
    for period_type in periods.keys():
        # Get description for this period
        description = get_composite_description(profile_key, period_type)
        
        # Create a section for this period
        st.markdown(f"## {period_type}")
        st.markdown(f"<p style='color: gray; margin-bottom: 20px;'>{description}</p>", unsafe_allow_html=True)
        
        # Define metric columns to average
        metric_columns = ["AvgReturn", "AvgRange", "ProbGreen", "ProbRed"]
        
        # Make a copy of the data to avoid modifying the original
        period_df = profile_df.copy()
        
        # Calculate the composite average for this period
        if period_type != "Min Cycle":  # Min Cycle is the current data, no averaging needed
            period_df = calculate_composite_average(period_df, profile_key, period_type, x_column, metric_columns)
        
        # Sort by natural order for the profile type
        period_df = create_ordered_profile_df(period_df, profile_key, "daily")
        
        # Create visualization based on selected metric
        if metric == "Average Return":
            period_df["col"] = period_df["AvgReturn"].gt(0).map({True:"green", False:"red"})
            fig = px.bar(period_df, x=x_column, y="AvgReturn", color="col",
                       color_discrete_map="identity", height=400)
            fig.update_layout(yaxis_title="Average Return (%)")
        elif metric == "ATR points":
            q = period_df["AvgRange"].quantile([0, .33, .66, 1]).values
            period_df["band"] = period_df["AvgRange"].apply(
                lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
            fig = px.bar(period_df, x=x_column, y="AvgRange", color="band",
                       color_discrete_map={"Low":"green","Avg":"orange","High":"red"}, height=400)
            fig.update_layout(yaxis_title="ATR (points)")
        else:  # Probability
            fig = px.bar(period_df, x=x_column, y=["ProbGreen","ProbRed"], barmode="group",
                       color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
            fig.update_layout(yaxis_title="Probability (%)")
        
        # Finalize chart layout
        fig.update_layout(
            xaxis_title="",
            margin=dict(l=0, r=0, t=0, b=0),
        )
        
        # Display the chart with a unique key
        # Create a unique key based on period type and metric
        chart_key = f"composite_view_{profile_key}_{period_type}_{metric}".replace(" ", "_").lower()
        st.plotly_chart(fig, use_container_width=True, key=chart_key)
        
        # Add separator between periods
        if period_type != list(periods.keys())[-1]:
            st.markdown("---")

def render_all_profiles_composite(df_dict, metric):
    """
    Render composite averages for all profile types.
    
    Args:
        df_dict: Dictionary of DataFrames for each profile type
        metric: The metric to display (Average Return, ATR points, etc.)
    """
    st.header("Composite Averages: All Profiles")
    
    # Create tabs for each profile type
    profile_tabs = st.tabs([
        "Monthly (Year)",
        "Weekly (Year)", 
        "Weekly (Month)", 
        "Daily (Week)",
        "Session (Day)",
        "Quarterly",
        "Presidential",
        "Decennial"
    ])
    
    # Map tab indices to profile keys
    profile_map = {
        0: "month",
        1: "week_of_year",
        2: "week_of_month",
        3: "day_of_week",
        4: "session",
        5: "quarter",
        6: "presidential",
        7: "decennial"
    }
    
    # Set default dates (use the maximum range)
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(days=365*20)  # 20 years
    
    # Render each profile tab
    for i, tab in enumerate(profile_tabs):
        with tab:
            profile_key = profile_map[i]
            
            # Get the data for this profile
            if profile_key in df_dict and df_dict[profile_key] is not None:
                profile_df = df_dict[profile_key]
                
                # Determine x-axis column
                x_column = "Label" if "Label" in profile_df.columns else "Month"
                
                # Render composite averages for this profile
                render_composite_averages(profile_df, profile_key, metric, x_column, start_date, end_date)
            else:
                st.warning(f"No data available for {profile_key} profile.")
